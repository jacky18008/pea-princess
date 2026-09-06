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

    def test_a_stderr_grumble_on_a_run_that_answered_keeps_the_answer(self):
        script = ("import sys; sys.stderr.write('warning: try again if this is slow\\n'); "
                  "sys.stdout.write(%r)" % json.dumps(CLAUDE_ENVELOPE))
        res = self.run_fake(script, attempts=2)
        self.assertFalse(res.provider_error, "a run that answered was written off")
        self.assertEqual("五週押金上限。", res.text)
        self.assertIn("warned on stderr", res.note)

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
        retry, why = launch.looks_like_provider_failure(0, "the answer", "usage limit reached")
        self.assertTrue(retry)
        self.assertIn("stderr", why)
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
