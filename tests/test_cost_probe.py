"""Offline tests for the bounded reporting-cost pilot; never starts a model CLI."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import cost_probe
from call_control import CallControl, PendingCallError


def row(session, outcome="completed", grade=0.5, failed=(), capped=()):
    return {"session": session, "outcome": outcome, "grade": grade,
            "safety_failed": list(failed), "capped_by": list(capped),
            "run_at": "2026-09-08T00:00:00Z"}


class FactsAndGradeTests(unittest.TestCase):
    def test_provider_error_excluded_even_with_stale_grade_or_safety_flags(self):
        rows = [row("good", grade=0.8),
                row("outage", "provider_error", 0.0,
                    ["viewing_day_warning"], ["provider error"])]
        result = cost_probe.facts("mixed", rows, 3)
        self.assertEqual(1, result["graded_sessions"])
        self.assertEqual(0.8, result["quality"]["mean_grade"])
        self.assertEqual(0, result["quality"]["safety_capped_sessions"])
        self.assertEqual(0, result["safety_misses"]["viewing_day_warning"])
        self.assertEqual(["outage"], result["retry_sessions"])
        self.assertEqual("pause_provider", result["decision"])

    def test_error_only_batch_has_null_quality_and_sorted_retry_ids(self):
        result = cost_probe.facts("outage", [
            row("P5", "provider_error", None, ["verify_before_paying"], ["provider error"]),
            row("P1", "provider_error", None)], 7)
        self.assertEqual(0, result["graded_sessions"])
        self.assertEqual(2, result["provider_error_sessions"])
        self.assertEqual(["P1", "P5"], result["retry_sessions"])
        self.assertTrue(all(v is None for v in result["quality"].values()))
        self.assertTrue(all(v is None for v in result["safety_misses"].values()))
        self.assertEqual("pause_provider", result["decision"])

    def test_bad_quality_abandonment_and_timeout_do_not_request_retry(self):
        rows = [row("A", "abandoned", 0.0), row("T", "timeout", 0.34),
                row("I", "invalid", None)]
        result = cost_probe.facts("diagnostic", rows, 3)
        self.assertEqual([], result["retry_sessions"])
        self.assertEqual("report_results", result["decision"])
        self.assertEqual(2, result["graded_sessions"])
        self.assertEqual("wait", cost_probe.facts("diagnostic", rows, 4)["decision"])

    def test_safety_lines_count_once_per_row_and_caps_once_per_session(self):
        rows = [row("A", failed=["viewing_day_warning"] * 2,
                    capped=["one", "two"]), row("B")]
        result = cost_probe.facts("case", rows, 2)
        self.assertEqual(1, result["safety_misses"]["viewing_day_warning"])
        self.assertEqual(1, result["quality"]["safety_capped_sessions"])
        self.assertEqual(set(cost_probe.OUTCOMES), set(result["outcomes"]))
        self.assertEqual(0, result["outcomes"]["provider_error"])

    def test_four_decimal_rounding_and_unordered_retry_ids_are_accepted(self):
        expected = cost_probe.facts("rounding", [
            row("A", grade=0.3333), row("B", grade=0.6666),
            row("P2", "provider_error", None), row("P1", "provider_error", None)], 4)
        actual = copy.deepcopy(expected)
        actual["quality"]["mean_grade"] = round(actual["quality"]["mean_grade"], 4)
        actual["quality"]["median_grade"] = round(actual["quality"]["median_grade"], 4)
        actual["retry_sessions"].reverse()
        self.assertTrue(cost_probe.grade(actual, expected)["pass"])

    def test_grading_rejects_wrong_facts_nulls_boolean_counts_and_nonfinite(self):
        expected = cost_probe.facts("case", [row("A", grade=0.7)], 1)
        changes = [("observed_sessions", True), ("graded_sessions", 0),
                   ("retry_sessions", ["A"]), ("decision", "wait")]
        for field, value in changes:
            with self.subTest(field=field):
                actual = copy.deepcopy(expected)
                actual[field] = value
                self.assertFalse(cost_probe.grade(actual, expected)["pass"])
        for value in [None, True, float("nan"), float("inf"), 0.7001]:
            with self.subTest(grade=value):
                actual = copy.deepcopy(expected)
                actual["quality"]["mean_grade"] = value
                self.assertFalse(cost_probe.grade(actual, expected)["pass"])
        outage = cost_probe.facts("outage", [row("P1", "provider_error", None)], 1)
        actual = copy.deepcopy(outage)
        actual["quality"]["mean_grade"] = 0
        self.assertFalse(cost_probe.grade(actual, outage)["pass"])


class PreparedPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "pilot"
        self.source = self.root / "source"
        for dataset in cost_probe.BATCHES:
            rows = [row("A"), row("B", "abandoned", 0.34), row("C", "timeout", 0.8889)]
            if dataset.endswith("fix2"):
                rows = [row("P1", "provider_error", None), row("P3", "provider_error", None)]
            cost_probe.write_json(self.source / dataset / "scorecard.json", rows)
        for name in cost_probe.BACKGROUND + cost_probe.RUNNER_SOURCES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Historical design context.", encoding="utf-8")
        for name, value in [("ROOT", self.root), ("SOURCE", self.source)]:
            patcher = mock.patch.object(cost_probe, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        with mock.patch.object(cost_probe.subprocess, "check_output", return_value="test-commit\n"), \
                redirect_stdout(io.StringIO()):
            cost_probe.prepare(self.output)
        self.plan = cost_probe.read_json(self.output / "plan.json")

    def test_prepare_is_offline_bounded_and_alternates_final_arm_order(self):
        jobs = self.plan["jobs"]
        self.assertEqual(10, len(jobs))
        self.assertEqual(["verbose", "compact", "compact", "verbose", "compact", "verbose"],
                         [job["arm"] for job in jobs if job["final"]])
        for job in jobs:
            packet = cost_probe.read_json(self.output / job["packet"])
            self.assertNotIn("decision", packet["deterministically_aggregated_state"])
            if job["arm"] == "compact":
                self.assertEqual([], job["prior_callbacks"])
            else:
                self.assertIn("records", packet)
        for dataset in cost_probe.BATCHES:
            finals = [job for job in jobs if job["dataset"] == dataset and job["final"]]
            states = [cost_probe.read_json(self.output / job["packet"])["deterministically_aggregated_state"]
                      for job in finals]
            self.assertEqual(states[0], states[1])
        with self.assertRaises(ValueError):
            cost_probe.prepare(self.output)

    def fake_process(self, extra_items=(), include_usage=True):
        def start(cmd, stdin, stdout, stderr):
            self.assertEqual("codex", cmd[0])
            self.assertIn("read-only", cmd)
            answer_file = Path(cmd[cmd.index("--output-last-message") + 1])
            expected = cost_probe.read_json(self.output / "expected" / (answer_file.parent.name + ".json"))
            cost_probe.write_json(answer_file, expected)
            events = [{"type": "item.completed", "item": {"type": "reasoning", "text": "report"}},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(expected)}}]
            events.extend({"type": "item.completed", "item": {"type": kind}} for kind in extra_items)
            if include_usage:
                events.append({"type": "turn.completed", "usage": {
                    "input_tokens": 200, "output_tokens": 10, "cached_input_tokens": 100}})
            stdout.write("\n".join(json.dumps(event) for event in events))
            stdout.flush()
            return types.SimpleNamespace(wait=lambda timeout: 0, pid=999999)
        return start

    def measure(self, **kwargs):
        with mock.patch.object(cost_probe.launch, "start_process", side_effect=self.fake_process(**kwargs)) as launch, \
                mock.patch.object(cost_probe.launch, "finish_process"):
            result = cost_probe.measure(self.output, self.plan["jobs"][0], self.plan)
        self.assertEqual(1, launch.call_count)
        return result

    def test_telemetry_counts_cached_tokens_as_subset_and_allows_only_text(self):
        result = self.measure()
        self.assertEqual("complete", result["status"])
        self.assertEqual(210, result["usage"]["total_tokens"])
        self.assertEqual(100, result["usage"]["cached_input_tokens"])
        self.assertEqual([], result["tool_events"])
        self.assertTrue(result["quality"]["pass"])

    def test_command_web_mcp_and_unknown_items_all_invalidate_trial(self):
        result = self.measure(extra_items=["command_execution", "web_search", "mcp_tool_call", "future_tool"])
        self.assertEqual("stopped", result["status"])
        self.assertEqual(4, len(result["tool_events"]))
        self.assertIsNotNone(result["usage"])
        self.assertTrue(result["quality"]["pass"])

    def test_missing_usage_stops_and_resume_never_replays_failed_call(self):
        result = self.measure(include_usage=False)
        self.assertEqual("stopped", result["status"])
        self.assertIsNone(result["usage"])
        with mock.patch.object(cost_probe, "measure") as measure, redirect_stdout(io.StringIO()):
            self.assertEqual(1, cost_probe.run(self.output))
        measure.assert_not_called()
        summary = cost_probe.read_json(self.output / "summary.json")
        self.assertFalse(summary["complete"])
        self.assertIsNone(summary["processed_token_reduction"])
        self.assertEqual(0, summary["arms"]["verbose"]["usage_reported_for_calls"])
        self.assertIsNone(summary["arms"]["verbose"]["usage"])

    def test_changed_evidence_is_rejected_before_any_model_call(self):
        packet = self.output / self.plan["jobs"][0]["packet"]
        packet.write_text("{}", encoding="utf-8")
        with mock.patch.object(cost_probe, "measure") as measure, self.assertRaises(ValueError):
            cost_probe.run(self.output)
        measure.assert_not_called()

    def test_changed_expected_facts_are_rejected_before_any_model_call(self):
        expected = self.output / "expected" / (self.plan["jobs"][0]["id"] + ".json")
        expected.write_text("{}", encoding="utf-8")
        with mock.patch.object(cost_probe, "measure") as measure, self.assertRaises(ValueError):
            cost_probe.run(self.output)
        measure.assert_not_called()

    def test_interrupted_directory_is_preserved_and_not_relaunched(self):
        directory = self.output / "calls" / self.plan["jobs"][0]["id"]
        directory.mkdir(parents=True)
        (directory / "events.jsonl").write_text("partial telemetry", encoding="utf-8")
        with mock.patch.object(cost_probe.subprocess, "Popen") as launch, self.assertRaises(FileExistsError):
            cost_probe.run(self.output)
        launch.assert_not_called()
        self.assertEqual("partial telemetry", (directory / "events.jsonl").read_text(encoding="utf-8"))

    def durable_start(self, **options):
        fake = self.fake_process(**options)
        def start(cmd, stdin, stdout, stderr):
            call_id = Path(cmd[cmd.index("--cd") + 1]).name
            self.assertEqual([call_id], CallControl(self.output / "control", self.plan["planned_call_ids"]).report()["pending_call_ids"])
            return fake(cmd, stdin, stdout, stderr)
        return start

    def test_all_ten_calls_dispatch_before_process_and_replay_without_models(self):
        with mock.patch.object(cost_probe.launch, "start_process", side_effect=self.durable_start()) as start, \
                mock.patch.object(cost_probe.launch, "finish_process"), redirect_stdout(io.StringIO()):
            self.assertEqual(0, cost_probe.run(self.output))
            self.assertEqual(0, cost_probe.run(self.output))
        self.assertEqual(10, start.call_count)
        summary = cost_probe.read_json(self.output / "summary.json")
        self.assertTrue(summary["complete"])
        self.assertEqual(2100, summary["controller"]["usage"]["total_tokens"])
        self.assertTrue(summary["usage_coverage_complete"])
        self.assertEqual([], summary["raw_artifact_integrity_failures"])
        self.assertTrue({"bench/call_control.py", "bench/report_control.py"}.issubset(self.plan["source_sha256"]))
        for path in (self.output / "calls").glob("*/*"):
            self.assertEqual(0, path.stat().st_mode & 0o077)

    def test_failed_telemetry_stops_the_durable_batch_without_retry(self):
        with mock.patch.object(cost_probe.launch, "start_process", side_effect=self.durable_start(include_usage=False)) as start, \
                mock.patch.object(cost_probe.launch, "finish_process"), redirect_stdout(io.StringIO()):
            self.assertEqual(1, cost_probe.run(self.output))
            self.assertEqual(1, cost_probe.run(self.output))
        self.assertEqual(1, start.call_count)
        summary = cost_probe.read_json(self.output / "summary.json")
        self.assertFalse(summary["complete"])
        self.assertTrue(summary["controller"]["paused"])
        self.assertFalse(summary["usage_coverage_complete"])

    def test_missing_raw_result_is_not_replayed_from_checkpoint(self):
        with mock.patch.object(cost_probe.launch, "start_process", side_effect=self.durable_start()) as start, \
                mock.patch.object(cost_probe.launch, "finish_process"), redirect_stdout(io.StringIO()):
            self.assertEqual(0, cost_probe.run(self.output))
            (self.output / "calls" / self.plan["jobs"][0]["id"] / "result.json").unlink()
            with self.assertRaisesRegex(ValueError, "missing its raw result"):
                cost_probe.run(self.output)
        self.assertEqual(10, start.call_count)
        summary = cost_probe.read_json(self.output / "summary.json")
        self.assertFalse(summary["complete"])
        self.assertFalse(summary["usage_coverage_complete"])

    def test_tampered_raw_events_stop_replay_and_invalidate_summary(self):
        with mock.patch.object(cost_probe.launch, "start_process", side_effect=self.durable_start()) as start, \
                mock.patch.object(cost_probe.launch, "finish_process"), redirect_stdout(io.StringIO()):
            self.assertEqual(0, cost_probe.run(self.output))
            (self.output / "calls" / self.plan["jobs"][0]["id"] / "events.jsonl").write_text("changed")
            with self.assertRaisesRegex(ValueError, "artifact differs"):
                cost_probe.run(self.output)
        self.assertEqual(10, start.call_count)
        summary = cost_probe.read_json(self.output / "summary.json")
        self.assertFalse(summary["complete"])
        self.assertEqual(1, len(summary["raw_artifact_integrity_failures"]))

    def test_pending_dispatch_blocks_every_later_call(self):
        control = CallControl(self.output / "control", self.plan["planned_call_ids"])
        control.dispatch(self.plan["planned_call_ids"][0], self.plan["planned_call_ids"][0], "reporter", "report")
        with mock.patch.object(cost_probe.launch, "start_process") as start, redirect_stdout(io.StringIO()), self.assertRaises(PendingCallError):
            cost_probe.run(self.output)
        start.assert_not_called()
        self.assertEqual(1, control.report()["dispatched_calls"])

    def test_budget_stop_does_not_dispatch_a_call(self):
        self.plan["reported_token_stop_threshold"] = 0
        cost_probe.write_json(self.output / "plan.json", self.plan)
        with mock.patch.object(cost_probe.launch, "start_process") as start, redirect_stdout(io.StringIO()):
            self.assertEqual(1, cost_probe.run(self.output))
        start.assert_not_called()
        self.assertEqual(0, CallControl(self.output / "control", self.plan["planned_call_ids"]).report()["dispatched_calls"])


if __name__ == "__main__":
    unittest.main()
