# -*- coding: utf-8 -*-
"""Guards for the three-host bench: the commands, the sessions, the folder, the page.

Nothing here starts a CLI or reaches a network. Every host call goes through a fake
launcher that records what it was asked to run and hands back the envelope that CLI
prints, so what is checked is exactly the part this tool owns:

1. **The three commands.** Claude gets its session flags and its read-only toolset,
   Codex gets ``codex exec --json`` with the transcript replayed and its AGENTS.md,
   Grok gets a prompt file, its rules and a session id - and on the second turn each
   host resumes instead of introducing itself again.
2. **The sessions persist.** Turn 2 carries turn 1's session id, and Grok's id is the
   one the CLI said it used, not the one the bench guessed.
3. **A pasted attachment lands in every host's folder** under a safe name, and the
   prompt says where it is.
4. **The server binds loopback and nothing else**, serves the page, and refuses a
   request that did not come from that page.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for folder in (os.path.join(ROOT, "tools"), os.path.join(ROOT, "bench")):
    if folder not in sys.path:
        sys.path.insert(0, folder)
import tri_bench                     # noqa: E402
import journeys                      # noqa: E402
import launch                        # noqa: E402

CLAUDE_STDOUT = json.dumps({"type": "result", "result": "claude says hello",
                            "usage": {"input_tokens": 120, "output_tokens": 40},
                            "total_cost_usd": 0.0123})
CODEX_STDOUT = "\n".join([
    json.dumps({"type": "item.started", "item": {"type": "reasoning"}}),
    json.dumps({"type": "item.completed",
                "item": {"type": "agent_message", "text": "codex says hello"}}),
    json.dumps({"type": "turn.completed",
                "usage": {"input_tokens": 200, "output_tokens": 60}}),
])
GROK_SESSION = "11111111-2222-3333-4444-555555555555"
GROK_STDOUT = json.dumps({"text": "grok says hello", "stopReason": "EndTurn",
                          "sessionId": GROK_SESSION, "requestId": "req-1"})


class FakeRunner(object):
    """Stands in for launch.run: records the call, returns that CLI's own envelope."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, cwd, timeout, family, **kwargs):
        self.calls.append({"cmd": list(cmd), "cwd": cwd, "timeout": timeout,
                           "family": family, "kwargs": kwargs})
        if family == "claude":
            return launch.LaunchResult(text="claude says hello",
                                       usage=launch.claude_usage(json.loads(CLAUDE_STDOUT)),
                                       stdout=CLAUDE_STDOUT,
                                       session_id=launch.session_id_in(cmd))
        if family == "codex":
            return launch.LaunchResult(text=CODEX_STDOUT, stdout=CODEX_STDOUT,
                                       usage=launch.usage_from_events(CODEX_STDOUT))
        return launch.LaunchResult(text=GROK_STDOUT, stdout=GROK_STDOUT)

    def of(self, family):
        return [call for call in self.calls if call["family"] == family]

    def cmd(self, family, index=0):
        return self.of(family)[index]["cmd"]


def flag(cmd, name):
    """The value after a flag, or None. Repeated flags are not expected here."""
    return cmd[cmd.index(name) + 1] if name in cmd else None


def wait_idle(bench, seconds=10):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not bench.busy:
            return True
        time.sleep(0.02)
    raise AssertionError("the bench never went idle")


class BenchCase(unittest.TestCase):
    """A bench in a throwaway folder, with a fake launcher and no home sync."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tri-bench-test-")
        self.home = os.path.join(self.root, "grok-home", "pea-princess")
        self.runner = FakeRunner()
        patches = [mock.patch.object(tri_bench, "GROK_HOME_SKILL", self.home),
                   mock.patch.object(journeys, "grok_usage", return_value=None)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(shutil.rmtree, self.root, True)

    def bench(self, **kwargs):
        kwargs.setdefault("sync_grok_home", False)
        kwargs.setdefault("root", os.path.join(self.root, "sessions"))
        kwargs.setdefault("runner", self.runner)
        return tri_bench.Bench(**kwargs).start()

    def send(self, bench, text, attachment=None):
        bench.send(text, attachment)
        wait_idle(bench)


class Commands(BenchCase):
    def test_claude_gets_its_session_flags_and_read_only_tools(self):
        bench = self.bench()
        self.send(bench, "第一題")
        cmd = self.runner.cmd("claude")
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertEqual(flag(cmd, "--output-format"), "json")
        self.assertEqual(flag(cmd, "--session-id"), bench.hosts["claude"]["session_id"])
        self.assertEqual(flag(cmd, "--add-dir"), bench.work("claude"))
        self.assertEqual(flag(cmd, "--tools"), "Read")
        self.assertIn("--strict-mcp-config", cmd)
        self.assertIn("第一題", cmd[-1])
        self.assertIn("SKILL", flag(cmd, "--append-system-prompt"))
        self.assertIn(os.path.join(".claude", "skills", "vet-flat"),
                      flag(cmd, "--append-system-prompt"))

    def test_codex_replays_the_transcript_and_reads_agents_md(self):
        bench = self.bench()
        self.send(bench, "first question")
        self.send(bench, "second question")
        first, second = self.runner.cmd("codex", 0), self.runner.cmd("codex", 1)
        self.assertEqual(first[:2], ["codex", "exec"])
        self.assertEqual(flag(first, "--cd"), bench.work("codex"))
        self.assertEqual(flag(first, "--sandbox"), "read-only")
        self.assertIn("--json", first)
        self.assertNotIn("--resume", second)
        self.assertIn("codex says hello", second[-1])   # no session: the history is replayed
        self.assertIn("second question", second[-1])
        agents = os.path.join(bench.work("codex"), "AGENTS.md")
        with io.open(agents, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("THE SKILL", text)
        self.assertIn(os.path.join(".agents", "skills", "vet-flat"), text)

    def test_grok_gets_a_prompt_file_its_rules_and_a_read_only_sandbox(self):
        bench = self.bench()
        self.send(bench, "我十月到倫敦")
        cmd = self.runner.cmd("grok")
        self.assertEqual(cmd[0], "grok")
        self.assertEqual(flag(cmd, "--cwd"), bench.work("grok"))
        self.assertEqual(flag(cmd, "--output-format"), "json")
        self.assertEqual(flag(cmd, "--sandbox"), "read-only")
        self.assertEqual(flag(cmd, "--tools"), "read_file,grep,list_dir")
        self.assertEqual(flag(cmd, "-m"), journeys.GROK_MODEL)
        self.assertIn("--no-subagents", cmd)
        self.assertIn("--disable-web-search", cmd)
        self.assertIn("SKILL", flag(cmd, "--rules"))
        prompt = flag(cmd, "--prompt-file")
        self.assertTrue(prompt.startswith(bench.dir), prompt)
        with io.open(prompt, encoding="utf-8") as handle:
            self.assertIn("我十月到倫敦", handle.read())

    def test_every_host_is_told_the_same_skill_text(self):
        bench = self.bench()
        self.send(bench, "one question")
        claude = flag(self.runner.cmd("claude"), "--append-system-prompt")
        grok = flag(self.runner.cmd("grok"), "--rules")
        with io.open(os.path.join(bench.work("codex"), "AGENTS.md"), encoding="utf-8") as handle:
            codex = handle.read()
        # The one line that differs is the folder each host expects the skill in.
        heads = {text.split("# How this bench works")[0] for text in (claude, codex, grok)}
        self.assertEqual(len(heads), 1, "the three hosts were given different skill text")


class Sessions(BenchCase):
    def test_turn_two_resumes_turn_one_on_both_hosts_that_can(self):
        bench = self.bench()
        self.send(bench, "first")
        self.send(bench, "second")
        claude_id = bench.hosts["claude"]["session_id"]
        self.assertEqual(flag(self.runner.cmd("claude", 0), "--session-id"), claude_id)
        second = self.runner.cmd("claude", 1)
        self.assertEqual(flag(second, "--resume"), claude_id)
        self.assertNotIn("--session-id", second)
        self.assertIsNone(flag(second, "--append-system-prompt"))
        # Grok reports the id it really used; turn 2 resumes that one.
        self.assertEqual(bench.hosts["grok"]["session_id"], GROK_SESSION)
        self.assertEqual(flag(self.runner.cmd("grok", 1), "--resume"), GROK_SESSION)
        self.assertIsNone(flag(self.runner.cmd("grok", 1), "--rules"))

    def test_the_turn_counter_and_the_cards_follow_the_session(self):
        bench = self.bench()
        self.send(bench, "first")
        self.send(bench, "second")
        for host in tri_bench.HOSTS:
            self.assertEqual(bench.hosts[host]["turn"], 2)
            self.assertEqual([card["turn"] for card in bench.hosts[host]["cards"]], [1, 2])
            self.assertEqual(bench.hosts[host]["cards"][0]["reply"], "%s says hello" % host)
        state = bench.state()
        claude = [h for h in state["hosts"] if h["id"] == "claude"][0]
        self.assertIn("tokens", claude["cards"][0]["usage_line"])
        self.assertIn("$", claude["cards"][0]["usage_line"])

    def test_a_new_session_gives_every_host_a_new_id(self):
        bench = self.bench()
        self.send(bench, "first")
        before = {h: bench.hosts[h]["session_id"] for h in tri_bench.HOSTS}
        bench.new_session()
        self.assertEqual(bench.turn, 0)
        self.assertNotEqual(bench.hosts["claude"]["session_id"], before["claude"])
        self.assertEqual(bench.hosts["codex"]["session_id"], None)
        self.assertEqual(bench.hosts["claude"]["cards"], [])

    def test_every_turn_is_written_to_that_host_s_transcript(self):
        bench = self.bench()
        self.send(bench, "first")
        for host in tri_bench.HOSTS:
            path = os.path.join(bench.dir, host, "transcript.jsonl")
            with io.open(path, encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
            self.assertEqual(rows[0]["event"], "session")
            self.assertEqual(rows[-1]["user"], "first")
            self.assertEqual(rows[-1]["reply"], "%s says hello" % host)
            self.assertIsNone(rows[-1]["error"])

    def test_a_host_that_refuses_shows_what_it_said(self):
        bench = self.bench()
        refusal = json.dumps({"type": "error", "message": "Not signed in. Run `grok login`."})

        def runner(cmd, cwd, timeout, family, **kwargs):
            if family == "grok":
                return launch.LaunchResult(text=refusal, stdout=refusal)
            return self.runner(cmd, cwd, timeout, family, **kwargs)

        bench.runner = runner
        self.send(bench, "first")
        card = bench.hosts["grok"]["cards"][0]
        self.assertEqual(card["reply"], "")
        self.assertIn("grok login", card["error"])
        self.assertEqual(bench.hosts["claude"]["status"], "done")

    def test_a_host_that_breaks_never_blocks_the_others(self):
        bench = self.bench()

        def runner(cmd, cwd, timeout, family, **kwargs):
            if family == "codex":
                raise OSError("codex is not installed on this machine")
            return self.runner(cmd, cwd, timeout, family, **kwargs)

        bench.runner = runner
        self.send(bench, "first")
        self.assertEqual(bench.hosts["codex"]["status"], "error")
        self.assertIn("not installed", bench.hosts["codex"]["cards"][0]["error"])
        self.assertEqual(bench.hosts["claude"]["status"], "done")
        self.assertEqual(bench.hosts["grok"]["cards"][0]["reply"], "grok says hello")


class Attachments(BenchCase):
    def test_a_pasted_page_lands_in_every_host_s_folder(self):
        bench = self.bench()
        self.send(bench, "幫我看這個", {"name": "listing 1.txt",
                                        "text": "rent: 2200 pcm\nfloor area: 41 sqm\n"})
        for host in tri_bench.HOSTS:
            path = os.path.join(bench.work(host), "listing-1.txt")
            self.assertTrue(os.path.isfile(path), path)
            with io.open(path, encoding="utf-8") as handle:
                self.assertIn("2200 pcm", handle.read())
        body = self.runner.cmd("claude")[-1]
        self.assertIn("--- pasted: listing 1.txt", body)
        self.assertIn("listing-1.txt", body)          # and where the host can find it

    def test_a_hostile_attachment_name_cannot_escape_the_folder(self):
        self.assertEqual(tri_bench.safe_name("../../etc/passwd"), "passwd")
        self.assertEqual(tri_bench.safe_name("  "), "pasted.txt")
        self.assertEqual(tri_bench.safe_name("..", fallback="x.txt"), "x.txt")

    def test_nothing_is_written_outside_the_session_folder(self):
        bench = self.bench()
        self.assertRaises(tri_bench.BenchError, bench.owned, os.path.join(ROOT, "SKILL.md"))
        self.assertRaises(tri_bench.BenchError, bench.write_text,
                          os.path.join(bench.dir, "..", "escaped.txt"), "no")
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(bench.dir), "escaped.txt")))


class GrokSkillHome(BenchCase):
    def test_the_pinned_skill_is_synced_into_the_only_place_grok_reads(self):
        bench = self.bench(sync_grok_home=True)
        self.assertTrue(os.path.isfile(os.path.join(self.home, "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.home, tri_bench.GROK_SYNC_MARKER)))
        self.assertTrue(any("~/.grok/skills/pea-princess" in note for note in bench.notes))

    def test_the_copy_is_taken_back_out_when_the_bench_stops(self):
        bench = self.bench(sync_grok_home=True)
        other = self.bench(sync_grok_home=False)
        self.assertFalse(other.unsync_grok())          # not this session's copy to remove
        self.assertTrue(os.path.isdir(self.home))
        self.assertTrue(bench.unsync_grok())
        self.assertFalse(os.path.exists(self.home))
        self.assertFalse(bench.unsync_grok())

    def test_a_folder_the_bench_did_not_make_is_left_alone_and_said_so(self):
        os.makedirs(self.home)
        with io.open(os.path.join(self.home, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write("someone else's skill\n")
        bench = self.bench(sync_grok_home=True)
        with io.open(os.path.join(self.home, "SKILL.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "someone else's skill\n")
        self.assertTrue(any("left alone" in note for note in bench.notes), bench.notes)


class GrokAdapter(unittest.TestCase):
    """The adapter that now lives in bench/journeys.py, read back through its own reply."""

    def test_an_error_envelope_is_a_failure_and_not_an_answer(self):
        # Grok exits 0 and says so on stdout; without this the refusal would be graded.
        refusal = json.dumps({"type": "error", "message": "Not signed in. Run `grok login`."})
        self.assertEqual(journeys.grok_answer(refusal), ("", None))
        self.assertIn("Not signed in", journeys.grok_error(refusal))
        self.assertIsNone(journeys.grok_error(GROK_STDOUT))

    def test_the_envelope_is_read_for_its_text_and_its_session(self):
        self.assertEqual(journeys.grok_answer(GROK_STDOUT), ("grok says hello", None))
        self.assertEqual(journeys.grok_session_id(GROK_STDOUT), GROK_SESSION)
        self.assertEqual(journeys.grok_session_id("not json at all"), None)
        self.assertEqual(journeys.grok_answer("not json at all")[0], "not json at all")

    def test_usage_comes_from_grok_usage_and_an_unreadable_answer_is_unknown(self):
        class Proc(object):
            def __init__(self, out):
                self.out = out

            def communicate(self, timeout=None):
                return self.out, b""

        payload = json.dumps({"input_tokens": 1500, "output_tokens": 300,
                              "total_tokens": 1800, "cost_usd": 0.004}).encode()
        usage = journeys.grok_usage("sid", runner=lambda *a, **k: Proc(payload))
        self.assertEqual(usage["total_tokens"], 1800)
        self.assertEqual(usage["cost_usd"], 0.004)
        self.assertIsNone(journeys.grok_usage("sid", runner=lambda *a, **k: Proc(b"???")))
        self.assertIsNone(journeys.grok_usage(None))

    def test_the_journey_runner_offers_grok_and_builds_the_same_command(self):
        self.assertIn("grok", journeys.AGENTS)
        self.assertEqual(journeys.SKILL_HOME["grok"], os.path.join(".grok", "skills"))
        cmd = journeys.grok_command("/tmp/p.txt", "/tmp/w", "grok-4.6",
                                    session_id="sid", rules="RULES")
        self.assertEqual(flag(cmd, "--session-id"), "sid")
        self.assertEqual(flag(cmd, "--rules"), "RULES")
        resumed = journeys.grok_command("/tmp/p.txt", "/tmp/w", "grok-4.6",
                                        resume="sid", rules="RULES")
        self.assertEqual(flag(resumed, "--resume"), "sid")
        self.assertIsNone(flag(resumed, "--rules"))


class Journeys(BenchCase):
    def test_a_scripted_journey_is_played_and_scored_turn_by_turn(self):
        bench = self.bench()
        label = bench.catalogue[0][0]
        journey = tri_bench.find_journey(label)
        thread = bench.play_journey(label)
        thread.join(30)
        wait_idle(bench)
        self.assertEqual(bench.journey["label"], label)
        self.assertTrue(bench.journey["done"])
        for host in tri_bench.HOSTS:
            cards = bench.hosts[host]["cards"]
            self.assertEqual(len(cards), len(journey["turns"]))
            self.assertIsNotNone(cards[0]["score"])       # the grader ran on every turn
            self.assertTrue(cards[0]["failed"])           # "hello" fails most checks
            self.assertEqual(cards[0]["journey"], label)

    def test_the_select_lists_exactly_what_the_runner_would_run(self):
        bench = self.bench()
        labels = [row[0] for row in bench.catalogue]
        self.assertIn("j1-from-zero-zh", labels)
        self.assertIn("j9-adjust-settings-by-talking#zh", labels)
        self.assertRaises(tri_bench.BenchError, tri_bench.find_journey, "no-such-journey")


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="tri-bench-server-")
        cls.bench = tri_bench.Bench(root=os.path.join(cls.root, "sessions"),
                                    sync_grok_home=False, runner=FakeRunner()).start()
        cls.server = tri_bench.serve(cls.bench, 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.root, ignore_errors=True)

    def get(self, path, headers=None):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        head = {"Host": "127.0.0.1:%d" % self.port}
        head.update(headers or {})
        conn.request("GET", path, headers=head)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
        return response.status, body

    def test_it_binds_loopback_and_nothing_else(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with mock.patch.object(tri_bench, "ThreadingHTTPServer") as made:
            tri_bench.serve(self.bench, 8790)
        self.assertEqual(made.call_args[0][0], ("127.0.0.1", 8790))

    def test_it_serves_the_page_with_no_external_asset(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("Three-host test bench", body)
        for control in ('id="msg"', 'id="cols"', 'id="journey"', 'id="hostrow"',
                        "run journey"):
            self.assertIn(control, body)
        # The three columns are built from /api/state, so the host names are there.
        state = json.loads(self.get("/api/state", {"X-Pea-Client": "tri-bench"})[1])
        self.assertEqual([host["label"] for host in state["hosts"]],
                         ["Claude Code", "Codex", "Grok Build"])
        self.assertNotIn("http://", body.replace("http://127.0.0.1", ""))
        self.assertNotIn("https://", body)
        self.assertNotIn("<script src", body)
        self.assertNotIn("<link", body)

    def test_the_api_answers_the_page_and_refuses_anything_else(self):
        status, body = self.get("/api/state", {"X-Pea-Client": "tri-bench"})
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertEqual([host["id"] for host in state["hosts"]], list(tri_bench.HOSTS))
        self.assertEqual(self.get("/api/state")[0], 403)          # not from the page
        self.assertEqual(self.get("/api/state", {"Host": "pea.example:1"})[0], 403)
        self.assertEqual(self.get("/api/state", {"X-Pea-Client": "tri-bench",
                                                 "Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.get("/nope", {"X-Pea-Client": "tri-bench"})[0], 404)


if __name__ == "__main__":
    unittest.main()
