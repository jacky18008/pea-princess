# -*- coding: utf-8 -*-
"""Offline tests for bench/launch.py, the one launcher every bench runner goes through.

No network and no model. Every "agent" here is a two-line python script that exits the
way a provider fails: exit 1 with nothing on either stream, a usage-limit line on stderr,
a run that works on the second attempt. The waits are passed in as zero, so a test that
covers three attempts still finishes in milliseconds.

The failures these tests are written against are real:
  bench/results/docs-ablation/docs-2026-09-07   ten rows, "the agent exited 1: ; no
        answers array in the reply", each graded 0 facts and each averaged in.
  bench/results/personas-2026-09-06             P3-baseline-s1, "turn 2 agent: exited
        1: " after 365 s, written down as a timeout.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")

sys.path.insert(0, BENCH)
import launch  # noqa: E402

NO_WAIT = (0, 0, 0)


def fake_agent(script):
    """A command that behaves like a CLI: this python, that script, nothing else."""
    return [sys.executable, "-c", script]


# Exit 1 and say nothing at all - the exact shape of the docs pilot's ten lost rows.
SILENT_FAILURE = "import sys; sys.exit(1)"
# What a CLI prints when the account, not the service, has run out.
RATE_LIMITED = ("import sys; sys.stderr.write('Error: usage limit reached. "
                "Try again at 3pm.\\n'); sys.exit(1)")
# A reply with a JSON envelope, the way `claude -p --output-format json` answers.
CLAUDE_ENVELOPE = {"type": "result", "result": "五週押金上限。", "num_turns": 2,
                   "total_cost_usd": 0.031,
                   "usage": {"input_tokens": 1200, "output_tokens": 300,
                             "cache_read_input_tokens": 40}}
CODEX_EVENTS = "\n".join([
    "Reading prompt from argv",
    json.dumps({"type": "item.started", "item": {"type": "agent_message"}}),
    "not json at all",
    json.dumps({"type": "turn.completed",
                "usage": {"input_tokens": 900, "cached_input_tokens": 100}}),
    json.dumps({"type": "turn.completed",
                "usage": {"input_tokens": 1500, "output_tokens": 220,
                          "cached_input_tokens": 100}}),
])


def prints(text, code=0, stream="stdout"):
    return ("import sys; sys.%s.write(%r); sys.exit(%d)" % (stream, text, code))


class Recorder(object):
    """A clock that does not tick: it writes down what it was asked to wait for."""

    def __init__(self):
        self.waits = []
        self.lines = []

    def sleep(self, seconds):
        self.waits.append(seconds)

    def echo(self, line):
        self.lines.append(line)


class TestTheRetries(unittest.TestCase):
    def setUp(self):
        self.clock = Recorder()
        self.folder = tempfile.mkdtemp(prefix="vetflat-launch-")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def run_fake(self, script, **kwargs):
        kwargs.setdefault("waits", NO_WAIT)
        kwargs.setdefault("sleep", self.clock.sleep)
        kwargs.setdefault("echo", self.clock.echo)
        return launch.run(fake_agent(script), self.folder, 60, "claude", **kwargs)

    def test_a_silent_exit_one_is_retried_and_ends_as_a_provider_error(self):
        res = self.run_fake(SILENT_FAILURE, attempts=3)
        self.assertTrue(res.provider_error)
        self.assertEqual(3, res.attempts, "the launch was not retried")
        self.assertEqual(1, res.exit_code)
        self.assertEqual(2, len(self.clock.waits), "a pause is missing between attempts")
        note = res.tail_note("the agent ")
        self.assertIn("the agent exited 1", note)
        # The finding from the docs pilot: the CLI exited 1 and said nothing. The row has
        # to say that out loud, or the next reader cannot tell it from a bad flag.
        self.assertIn("stdout tail: (empty)", note)
        self.assertIn("stderr tail: (empty)", note)
        self.assertIn("attempts 3", note)

    def test_a_rate_limit_line_is_retried_and_its_tails_are_kept(self):
        res = self.run_fake(RATE_LIMITED, attempts=3)
        self.assertTrue(res.provider_error)
        self.assertEqual(3, res.attempts)
        self.assertIn("usage limit reached", res.stderr_tail)
        self.assertIn("usage limit reached", res.tail_note())
        self.assertTrue(any("provider" in line for line in self.clock.lines),
                        self.clock.lines)

    def test_a_success_on_the_second_attempt_records_two_attempts(self):
        # Fails once, then answers: the shape of a provider that was briefly busy.
        marker = os.path.join(self.folder, "tried-once")
        script = ("import os, sys\n"
                  "if not os.path.exists(%r):\n"
                  "    open(%r, 'w').close()\n"
                  "    sys.exit(1)\n"
                  "sys.stdout.write(%r)\n" % (marker, marker, json.dumps(CLAUDE_ENVELOPE)))
        res = self.run_fake(script, attempts=3)
        self.assertFalse(res.provider_error)
        self.assertEqual(2, res.attempts)
        self.assertEqual("五週押金上限。", res.text)
        self.assertEqual(1, len(self.clock.waits), "one pause, before the second attempt")

    def test_the_pauses_grow(self):
        self.run_fake(SILENT_FAILURE, attempts=3, waits=(60, 180, 600))
        self.assertEqual([60, 180], self.clock.waits)

    def test_a_first_time_success_is_never_retried(self):
        res = self.run_fake(prints(json.dumps(CLAUDE_ENVELOPE)), attempts=3)
        self.assertFalse(res.provider_error)
        self.assertEqual(1, res.attempts)
        self.assertEqual([], self.clock.waits)
        self.assertIsNone(res.note)
        self.assertEqual(0, res.exit_code)

    def test_an_empty_stdout_with_exit_zero_is_still_a_provider_error(self):
        res = self.run_fake("import sys; sys.exit(0)", attempts=2)
        self.assertTrue(res.provider_error)
        self.assertEqual(2, res.attempts)
        self.assertIn("exited 0 with no output", res.note)

    def test_a_reply_that_mentions_a_rate_is_not_thrown_away(self):
        # The trap in the other direction: a good reply retried three times and paid for
        # three times because the flat's rent was quoted as a "rate".
        reply = json.dumps({"type": "result",
                            "result": "The advertised rate is £2,350 pcm; try again "
                                      "with the deposit figure."})
        res = self.run_fake(prints(reply), attempts=3)
        self.assertFalse(res.provider_error)
        self.assertEqual(1, res.attempts)
        self.assertIn("£2,350", res.text)

    def test_a_stderr_grumble_on_a_run_that_answered_keeps_the_answer_without_a_retry(self):
        script = ("import sys; sys.stderr.write('warning: usage limit approaching, try again later\\n'); "
                  "sys.stdout.write(%r)" % json.dumps(CLAUDE_ENVELOPE))
        res = self.run_fake(script, attempts=2)
        self.assertFalse(res.provider_error, "a run that answered was written off")
        self.assertEqual("五週押金上限。", res.text)
        self.assertIn("warned on stderr", res.note)
        self.assertEqual(1, res.attempts, "a run that answered is never paid for twice")

    def test_the_tails_are_the_last_six_hundred_characters(self):
        noise = "x" * 5000
        script = ("import sys; sys.stdout.write('%s'); sys.stderr.write('%sEND'); "
                  "sys.exit(1)" % (noise, noise))
        res = self.run_fake(script, attempts=1)
        self.assertTrue(res.provider_error)
        self.assertEqual(launch.TAIL_CHARS, len(res.stdout_tail))
        self.assertEqual(launch.TAIL_CHARS, len(res.stderr_tail))
        self.assertTrue(res.stderr_tail.endswith("END"))

    def test_a_timeout_is_a_timeout_and_not_a_provider_error(self):
        res = launch.run(fake_agent("import time; time.sleep(30)"), self.folder, 1,
                         "claude", attempts=3, waits=NO_WAIT, sleep=self.clock.sleep,
                         echo=self.clock.echo)
        self.assertFalse(res.provider_error, "the caller's ceiling is not the provider")
        self.assertEqual("timed out after 1 s", res.note)
        self.assertEqual(1, res.attempts, "a timeout is not retried")

    def test_a_command_that_cannot_start_is_a_configuration_error(self):
        res = launch.run(["vetflat-no-such-binary-ever"], self.folder, 5, "claude",
                         attempts=3, waits=NO_WAIT, sleep=self.clock.sleep,
                         echo=self.clock.echo)
        self.assertFalse(res.provider_error)
        self.assertIn("could not start", res.note)
        self.assertEqual([], self.clock.waits)

    def test_stdin_is_closed_so_a_heredoc_never_reaches_the_prompt(self):
        script = ("import sys, json; "
                  "sys.stdout.write(json.dumps({'result': repr(sys.stdin.read())}))")
        res = self.run_fake(script, attempts=1)
        self.assertEqual("''", res.text, "the child could read something on stdin")

    def test_stdin_is_closed_in_the_source_too(self):
        with io.open(os.path.join(BENCH, "launch.py"), encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("stdin=subprocess.DEVNULL", source)
        self.assertEqual(1, source.count("subprocess.Popen("),
                         "there is more than one launch in the launcher")

    def test_no_permission_bypass_flag_is_added_by_the_launcher(self):
        with io.open(os.path.join(BENCH, "launch.py"), encoding="utf-8") as fh:
            source = fh.read()
        for flag in ("--dangerously-skip-permissions", "--yolo", "--full-auto",
                     "--sandbox danger-full-access", "--bypass"):
            self.assertNotIn(flag, source)


class TestReadingTheReply(unittest.TestCase):
    def test_claude_usage_round_trips(self):
        text, usage = launch.answer(json.dumps(CLAUDE_ENVELOPE), "claude")
        self.assertEqual("五週押金上限。", text)
        self.assertEqual(1200, usage["input_tokens"])
        self.assertEqual(300, usage["output_tokens"])
        self.assertEqual(1540, usage["total_tokens"])
        self.assertEqual(0.031, usage["total_cost_usd"])
        self.assertEqual(2, usage["num_turns"])

    def test_claude_prose_around_the_envelope_still_gives_up_the_answer(self):
        raw = "warming up\n" + json.dumps(CLAUDE_ENVELOPE) + "\ndone\n"
        text, usage = launch.answer(raw, "claude")
        self.assertEqual("五週押金上限。", text)
        self.assertEqual(1540, usage["total_tokens"])

    def test_stdout_that_is_not_json_comes_back_as_itself(self):
        text, usage = launch.answer("no envelope here", "claude")
        self.assertEqual("no envelope here", text)
        self.assertIsNone(usage)

    def test_codex_usage_round_trips_and_the_last_count_wins(self):
        text, usage = launch.answer(CODEX_EVENTS, "codex")
        self.assertEqual(CODEX_EVENTS, text, "codex hands back its own stdout")
        self.assertEqual(1500, usage["input_tokens"])       # cumulative: the last one
        self.assertEqual(220, usage["output_tokens"])
        self.assertEqual(1720, usage["total_tokens"])
        self.assertIn("cached_input_tokens+input_tokens+output_tokens",
                      usage["usage_shapes_seen"])

    def test_codex_cache_and_reasoning_are_subsets_not_extra_tokens(self):
        raw = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 1500, "cached_input_tokens": 1000,
            "cache_write_input_tokens": 200, "output_tokens": 220,
            "reasoning_output_tokens": 180}})
        usage = launch.usage_from_events(raw)
        self.assertEqual(1720, usage["total_tokens"])
        self.assertEqual(1000, usage["cached_input_tokens"])
        self.assertEqual(200, usage["cache_write_input_tokens"])
        self.assertEqual(180, usage["reasoning_output_tokens"])

    def test_codex_terminal_snapshot_wins_over_nested_and_later_records(self):
        # An internal last-request record is not the completed turn's cumulative usage.
        raw = "\n".join([json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 1500, "output_tokens": 220,
            "details": {"usage": {"input_tokens": 90, "output_tokens": 10,
                                  "reasoning_output_tokens": 8, "total_tokens": 100}}}}),
            json.dumps({"type": "debug", "usage": {"input_tokens": 90}})])
        usage = launch.usage_from_events(raw)
        self.assertEqual(1500, usage["input_tokens"])
        self.assertEqual(220, usage["output_tokens"])
        self.assertEqual(1720, usage["total_tokens"])
        self.assertNotIn("reasoning_output_tokens", usage)

    def test_codex_last_snapshot_does_not_inherit_earlier_breakdowns(self):
        raw = "\n".join([
            json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": 900, "output_tokens": 100, "total_tokens": 1000,
                "reasoning_output_tokens": 80}}),
            json.dumps({"type": "turn.completed", "usage": {
                "input_tokens": 1500, "output_tokens": 220}})])
        usage = launch.usage_from_events(raw)
        self.assertEqual(1720, usage["total_tokens"])
        self.assertNotIn("reasoning_output_tokens", usage)

    def test_codex_legacy_nested_usage_keeps_aliases_and_explicit_totals(self):
        raw = json.dumps({"event": {"token_usage": {
            "prompt_tokens": 200, "completion_tokens": 50,
            "cache_read_input_tokens": 100, "reasoning_output_tokens": 40}}})
        usage = launch.usage_from_events(raw)
        self.assertEqual(200, usage["prompt_tokens"])
        self.assertEqual(50, usage["completion_tokens"])
        self.assertEqual(250, usage["total_tokens"])
        explicit = json.dumps({"usage": {"total_tokens": 275}})
        self.assertEqual(275, launch.usage_from_events(explicit)["total_tokens"])

    def test_codex_duplicate_nested_records_are_never_added(self):
        counters = {"input_tokens": 200, "output_tokens": 50,
                    "reasoning_output_tokens": 40}
        raw = json.dumps({"usage": counters, "mirror": {"usage": counters}})
        self.assertEqual(250, launch.usage_from_events(raw)["total_tokens"])
        # Wrappers should not duplicate the one counter object they contain.
        self.assertEqual([counters], launch.walk_usage({"wrapper": counters}))

    def test_codex_reported_zero_usage_has_a_zero_total(self):
        raw = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}})
        self.assertEqual(0, launch.usage_from_events(raw)["total_tokens"])

    def test_an_event_stream_with_no_usage_reports_none(self):
        self.assertIsNone(launch.usage_from_events("no json here\n"))
        self.assertIsNone(launch.usage_from_events(""))

    def test_the_two_parsers_are_the_ones_the_runners_import(self):
        # journeys, personas, docs_bench and run_codex all reach the same code, so a fix
        # to either parser cannot land in one runner and miss the next.
        sys.path.insert(0, os.path.join(BENCH, "ab"))
        import journeys  # noqa: E402
        import run_codex  # noqa: E402
        self.assertEqual(launch.claude_answer(json.dumps(CLAUDE_ENVELOPE)),
                         journeys.claude_answer(json.dumps(CLAUDE_ENVELOPE)))
        self.assertEqual(launch.usage_from_events(CODEX_EVENTS),
                         run_codex.usage_from_events(CODEX_EVENTS))
        self.assertIs(launch.TRANSIENT, journeys.TRANSIENT)


class TestWhatCountsAsAProviderFailure(unittest.TestCase):
    def test_the_words_a_busy_provider_uses(self):
        for line in ("ERROR: Selected model is at capacity.", "HTTP 429 Too Many Requests",
                     "rate_limit_error: overloaded", "Claude usage limit reached",
                     "5-hour limit reached; try again at 3pm", "quota exceeded",
                     "503 Service Temporarily Unavailable"):
            self.assertTrue(launch.provider_language(line), line)

    def test_ordinary_words_are_not_an_outage(self):
        # "generate" and "accurate" carry the letters of "rate"; a reply that uses them
        # must never be retried and paid for twice.
        for line in ("I will generate the report", "the figures are accurate",
                     "SyntaxError in the reply", "corporate landlord", ""):
            self.assertFalse(launch.provider_language(line), line)

    def test_the_three_shapes_of_a_lost_row(self):
        self.assertEqual((True, "the CLI exited 1"),
                         launch.looks_like_provider_failure(1, "some output", ""))
        self.assertEqual((True, "the CLI exited 0 with no output"),
                         launch.looks_like_provider_failure(0, "   ", ""))
        retry, why = launch.looks_like_provider_failure(0, "", "usage limit reached")
        self.assertTrue(retry)
        self.assertIn("stderr", why)
        self.assertEqual((False, None),
                         launch.looks_like_provider_failure(0, "the answer", "usage limit reached"),
                         "a run that answered is kept, whatever stderr says")
        self.assertEqual((False, None),
                         launch.looks_like_provider_failure(0, "the answer", ""))

    def test_a_result_carries_its_defaults(self):
        res = launch.LaunchResult()
        self.assertEqual("", res.text)
        self.assertFalse(res.provider_error)
        self.assertEqual(1, res.attempts)
        self.assertIsNone(res.tail_note())


if __name__ == "__main__":
    unittest.main()


class TestCodexCacheFlags(unittest.TestCase):
    """The workspace-write sandbox gets the fetch cache as an extra writable root."""

    def test_the_flag_names_the_cache_directory(self):
        want = tempfile.mkdtemp(prefix="vetflat-cache-flag-")
        old = os.environ.get("VETFLAT_CACHE")
        os.environ["VETFLAT_CACHE"] = want
        try:
            flags = launch.codex_cache_flags()
        finally:
            if old is None:
                os.environ.pop("VETFLAT_CACHE", None)
            else:
                os.environ["VETFLAT_CACHE"] = old
            shutil.rmtree(want, ignore_errors=True)
        self.assertEqual("-c", flags[0])
        self.assertTrue(flags[1].startswith("sandbox_workspace_write.writable_roots=["))
        self.assertIn(json.dumps(want), flags[1])

    def test_the_default_is_the_home_cache(self):
        old = os.environ.pop("VETFLAT_CACHE", None)
        try:
            self.assertTrue(launch.vetflat_cache_dir().endswith(os.path.join(".cache", "vet-flat")))
        finally:
            if old is not None:
                os.environ["VETFLAT_CACHE"] = old


class TestStderrIsReadOnlyAfterAFailure(unittest.TestCase):
    """A successful reply whose stderr mentions a nightly rate is a reply, not a refusal."""

    def test_a_successful_run_with_rate_on_stderr_is_not_a_provider_failure(self):
        retry, why = launch.looks_like_provider_failure(
            0, '{"reply": "the nightly rate is £95"}', "OpenAI Codex v0.153.4\nmodel: gpt-5.6-terra\nthe rate is fine\n")
        self.assertFalse(retry, why)

    def test_a_failed_run_with_a_rate_limit_on_stderr_is(self):
        retry, why = launch.looks_like_provider_failure(1, "", "error: rate limit reached, try again later")
        self.assertTrue(retry)
        self.assertIn("stderr", why)

    def test_the_word_rate_alone_is_not_provider_language(self):
        self.assertFalse(launch.provider_language("the weekly rate is £480"))
        self.assertTrue(launch.provider_language("You have hit your usage limit"))
        self.assertTrue(launch.provider_language("HTTP 429 Too Many Requests"))


class TestARetryMintsAFreshSessionId(unittest.TestCase):
    """The first attempt registers the Claude session id even when it fails; retrying with
    the same id dies with "Session ID ... is already in use" (seven persona sessions on
    2026-09-07). Each retry gets a new id, and the result says which one was used."""

    def test_the_second_attempt_carries_a_different_id_and_the_result_reports_it(self):
        workdir = tempfile.mkdtemp(prefix="vetflat-session-")
        marker = os.path.join(workdir, "first-attempt-done")
        script = ("import os, sys, json\n"
                  "sid = sys.argv[sys.argv.index('--session-id') + 1]\n"
                  "m = %r\n"
                  "if not os.path.exists(m):\n"
                  "    open(m, 'w').write(sid); sys.stderr.write('Error: rate limit reached\\n'); sys.exit(1)\n"
                  "first = open(m).read()\n"
                  "if sid == first:\n"
                  "    sys.stderr.write('Error: Session ID %%s is already in use.\\n' %% sid); sys.exit(1)\n"
                  "print(json.dumps({'result': 'OK ' + sid, 'session_id': sid}))\n" % marker)
        path = os.path.join(workdir, "fake.py")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(script)
        cmd = [sys.executable, path, "-p", "--session-id", "11111111-1111-1111-1111-111111111111", "--", "hi"]
        res = launch.run(cmd, workdir, 30, "claude", attempts=3, waits=[0, 0], sleep=lambda s: None,
                         echo=lambda line: None)
        self.assertFalse(res.provider_error, res.note)
        self.assertEqual(2, res.attempts)
        self.assertNotEqual("11111111-1111-1111-1111-111111111111", res.session_id)
        self.assertIn(res.session_id, res.text)
        shutil.rmtree(workdir, ignore_errors=True)

    def test_a_command_without_a_session_id_reports_none(self):
        res = launch.run([sys.executable, "-c", "print('{\"result\": \"x\"}')"], tempfile.mkdtemp(), 30, "claude")
        self.assertIsNone(res.session_id)


class TestTheEnvelopesOwnErrorText(unittest.TestCase):
    """Claude Code reports an API failure inside its JSON envelope with exit 1 and an empty
    stderr; the note must carry that message, and the failure must count as the provider's."""

    ENVELOPE = json.dumps({"type": "result", "is_error": True, "result": "API Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)",
                           "usage": {"input_tokens": 0, "output_tokens": 0}, "subagent_stats": {"spawned": 0}})

    def test_the_failure_is_read_as_the_providers(self):
        retry, why = launch.looks_like_provider_failure(1, self.ENVELOPE, "")
        self.assertTrue(retry)
        self.assertIn("ENOTFOUND", why)

    def test_the_note_carries_the_message_not_the_tail(self):
        script = "import sys; sys.stdout.write(%r); sys.exit(1)" % self.ENVELOPE
        res = launch.run([sys.executable, "-c", script], tempfile.mkdtemp(), 30, "claude", attempts=2, waits=[0],
                         sleep=lambda s: None, echo=lambda line: None)
        self.assertTrue(res.provider_error)
        self.assertIn("ENOTFOUND", res.note)
        self.assertNotIn("subagent_stats", res.note)

    def test_a_successful_envelope_reports_no_error(self):
        self.assertIsNone(launch.claude_error(json.dumps({"is_error": False, "result": "OK"})))
