"""Grok probe parser tests; these never dispatch a model."""

import json
import io
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import grok_elastic_probe as probe


CONTROL = Path("/private/tmp/pea-grok-build-cli-v3-20260915")


class StoredTraceTests(unittest.TestCase):
    def test_successful_preflight_has_answer_without_literal_final_event(self):
        stream = CONTROL / "preflight.ndjson"
        if not stream.is_file():
            self.skipTest("private preflight trace is not mounted")
        result = probe.audit(stream)
        self.assertTrue(result["complete_answer"])
        self.assertEqual("end_turn", result["stop_reason"])
        self.assertEqual(7, result["usage_events"])
        self.assertEqual(176719, result["processed_tokens"])
        self.assertEqual(481174800, result["total_cost_usd_ticks"])
        self.assertNotIn("final", result["event_counts"])
        self.assertFalse(result["soft_reached"])

    def test_v4_max_turns_reached_is_failure_even_with_draft_text(self):
        stream = CONTROL / "v4-route-actor-01.ndjson"
        if not stream.is_file():
            self.skipTest("private v4 trace is not mounted")
        result = probe.audit(stream)
        self.assertFalse(result["complete_answer"])
        self.assertEqual("cancelled", result["stop_reason"])
        self.assertEqual(14, result["usage_events"])
        self.assertEqual(643882, result["processed_tokens"])
        self.assertEqual(139873, result["usage_sum"]["input_tokens"])
        self.assertEqual(483968, result["usage_sum"]["cache_read_input_tokens"])
        self.assertEqual(20041, result["usage_sum"]["output_tokens"])
        self.assertEqual(2182718400, result["total_cost_usd_ticks"])
        self.assertEqual(1, result["event_counts"]["max_turns_reached"])
        self.assertTrue(result["soft_reached"])
        self.assertEqual(14, result["soft_snapshot"]["usage_events"])


class SyntheticStreamTests(unittest.TestCase):
    def test_old_text_cannot_substitute_for_empty_terminal_response(self):
        ledger = probe.StreamLedger(soft_turns=2)
        for event in (
            {"type": "text", "data": "Earlier work"},
            {"type": "usage", "usage": {field: 1 for field in probe.FIELDS}},
            {"type": "usage", "usage": {field: 1 for field in probe.FIELDS}},
            {"type": "end", "stopReason": "end_turn", "num_turns": 2},
        ):
            ledger.feed(json.dumps(event))
        result = ledger.report()
        self.assertFalse(result["complete_answer"])
        self.assertEqual(2, result["usage_events"])
        self.assertTrue(result["soft_reached"])

    def test_missing_usage_and_cost_are_unknown(self):
        ledger = probe.StreamLedger(soft_turns=1)
        for event in (
            {"type": "text", "data": "A final answer"},
            {"type": "usage", "usage": {"input_tokens": 10, "output_tokens": 2}},
            {"type": "end", "stopReason": "end_turn", "total_cost_usd_ticks": None},
        ):
            ledger.feed(json.dumps(event))
        result = ledger.report()
        self.assertTrue(result["complete_answer"])
        self.assertIsNone(result["processed_tokens"])
        self.assertIsNone(result["total_cost_usd_ticks"])
        self.assertIn("cache_read_input_tokens", result["missing_usage_fields"])

    def test_inspect_requires_exact_active_skill_path(self):
        expected = Path("/private/tmp/project/.grok/skills/pea-princess/SKILL.md")
        report = {"skills": [{"name": "pea-princess", "source": {
            "type": "project", "path": str(expected)}}]}
        self.assertEqual(str(expected), probe.inspect_skill(report, "pea-princess", expected))
        with self.assertRaisesRegex(ValueError, "differs"):
            probe.inspect_skill(report, "pea-princess", Path("/private/tmp/other/SKILL.md"))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            probe.inspect_skill({"skills": report["skills"] * 2}, "pea-princess", expected)

    def test_run_dispatches_once_with_hard32_and_keeps_soft14_observational(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            project = root / "project"
            skill = project / ".grok/skills/pea-princess/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("synthetic skill", encoding="utf-8")
            prompt = root / "actor.txt"
            prompt.write_text("synthetic actor", encoding="utf-8")
            out = root / "receipt"
            inspect = {"skills": [{"name": "pea-princess", "source": {
                "type": "project", "path": str(skill)}}]}
            lines = [{"type": "usage", "usage": {field: 1 for field in probe.FIELDS}}
                     for _ in range(14)]
            lines.extend([{"type": "text", "data": "A terminal answer"},
                          {"type": "usage", "usage": {field: 1 for field in probe.FIELDS}},
                          {"type": "end", "stopReason": "end_turn", "num_turns": 15}])
            stream = "\n".join(json.dumps(item) for item in lines) + "\n"

            def fake_run(cmd, **_kwargs):
                if cmd[-2:] == ["inspect", "--json"]:
                    return types.SimpleNamespace(returncode=0,
                                                 stdout=json.dumps(inspect), stderr="")
                self.assertEqual("--version", cmd[-1])
                return types.SimpleNamespace(returncode=0, stdout="grok 1.0.30\n", stderr="")

            fake_process = types.SimpleNamespace(pid=1234, stdout=io.StringIO(stream),
                                                 wait=lambda timeout=None: 0,
                                                 poll=lambda: 0)
            argv = ["run", "--project", str(project), "--grok-home", str(root / "home"),
                    "--prompt-file", str(prompt), "--skill-file", str(skill),
                    "--out", str(out)]
            with mock.patch.object(probe.subprocess, "run", side_effect=fake_run), \
                    mock.patch.object(probe.subprocess, "Popen", return_value=fake_process) as launch, \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as diagnostics:
                self.assertEqual(0, probe.main(argv))
            self.assertEqual(1, launch.call_count)
            cmd = launch.call_args.args[0]
            self.assertEqual("32", cmd[cmd.index("--max-turns") + 1])
            self.assertNotIn("--no-auto-update", cmd)
            self.assertTrue(launch.call_args.kwargs["start_new_session"])
            self.assertEqual(1, diagnostics.getvalue().count("soft observation reached"))
            receipt = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(receipt["complete_answer"])
            self.assertTrue(receipt["soft_reached"])
            self.assertEqual(15, receipt["usage_events"])
            self.assertEqual(14, receipt["soft_snapshot"]["usage_events"])
            self.assertEqual("A terminal answer\n", (out / "terminal-answer.txt").read_text())
            self.assertEqual(0o700, out.stat().st_mode & 0o777)

            class SlowStream:
                def __iter__(self):
                    time.sleep(0.04)
                    return iter(())

            timed_process = types.SimpleNamespace(pid=5678, stdout=SlowStream(),
                                                  wait=lambda timeout=None: 143,
                                                  poll=lambda: 143)
            timed_argv = argv[:-1] + [str(root / "timed-receipt"),
                                       "--max-seconds", "0.005"]
            with mock.patch.object(probe.subprocess, "run", side_effect=fake_run), \
                    mock.patch.object(probe.subprocess, "Popen", return_value=timed_process) as timed_launch, \
                    mock.patch.object(probe.os, "killpg") as kill_group, \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(1, probe.main(timed_argv))
            self.assertEqual(1, timed_launch.call_count)
            kill_group.assert_any_call(5678, probe.signal.SIGTERM)
            kill_group.assert_any_call(5678, probe.signal.SIGKILL)
            timed = json.loads((root / "timed-receipt/summary.json").read_text())
            self.assertTrue(timed["deadline_reached"])
            self.assertFalse(timed["complete_answer"])


if __name__ == "__main__":
    unittest.main()
