"""No live invocations: persistent adapter boundary tests and saved-run replay."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import call_control

SAVED = ROOT / "bench/results/context-quality-2026-09-08/live-v1"


def record(call_id="c1", input_tokens=10, cached_input_tokens=2, output_tokens=3, **changes):
    value = {"id": call_id, "status": "complete", "exit_code": 0, "timeout": False,
             "errors": [], "tool_events": [], "malformed_event_lines": 0,
             "terminal_usage_events": 1,
             "direct_terminal_usage": {"input_tokens": input_tokens,
                                       "cached_input_tokens": cached_input_tokens,
                                       "output_tokens": output_tokens},
             "answer": {"answer": "saved output"}}
    value.update(changes)
    return value


class CallControlTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "controller"
        self.control = call_control.CallControl(self.path, ["c1", "c2", "c3"])

    def run_call(self, call_id, result, control=None):
        return (control or self.control).run(call_id, "job", "answer", "initial", lambda: result)

    def test_checkpoint_is_committed_before_callback_and_success_is_returned_unchanged(self):
        expected = record()

        def callback():
            restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
            self.assertEqual(["c1"], restored.report()["pending_call_ids"])
            self.assertEqual("pending", restored.report()["calls"][0]["status"])
            return expected

        actual = self.control.run("c1", "job", "answer", "initial", callback)
        self.assertEqual(expected, actual)
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])
        self.assertEqual(1, self.control.report()["completed_calls"])

    def test_duplicate_dispatch_completion_and_restored_run_never_double_count_or_invoke(self):
        first = mock.Mock(return_value=record())
        self.control.run("c1", "job", "answer", "initial", first)
        before = self.control.snapshot()
        self.assertFalse(self.control.dispatch("c1", "job", "answer", "initial"))
        self.control.complete("c1", record())
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        forbidden = mock.Mock(side_effect=AssertionError("completed call must not run"))
        self.assertEqual(record(), restored.run("c1", "job", "answer", "initial", forbidden))
        self.assertEqual(before, restored.snapshot())
        self.assertEqual(1, first.call_count)
        forbidden.assert_not_called()

    def test_metadata_conflict_cannot_reuse_a_completed_request(self):
        self.run_call("c1", record())
        with self.assertRaises(call_control.ConflictingCallError):
            self.control.dispatch("c1", "other-job", "judge", "batch")
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])

    def test_retrieval_phases_and_batched_judge_are_distinct_call_sessions(self):
        for call_id, role, phase in [("c1", "answer", "selection"),
                                     ("c2", "answer", "retrieved"), ("c3", "judge", "batch")]:
            self.control.run(call_id, "same-logical-case", role, phase, lambda c=call_id: record(c))
        state = self.control.snapshot()
        self.assertEqual(["c1", "c2", "c3"], state["reducer_state"]["sessions"])
        self.assertEqual(39, self.control.report()["usage"]["total_tokens"])
        self.assertEqual("report_results", self.control.report()["decision"])
        self.assertEqual(["selection", "retrieved", "batch"], [c["phase"] for c in self.control.report()["calls"]])
        self.assertNotIn("graded_sessions", self.control.report())

    def test_restored_pending_call_blocks_same_or_next_callback(self):
        self.control.dispatch("c1", "job", "answer", "initial")
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        callback = mock.Mock()
        for call_id in ("c1", "c2"):
            with self.assertRaises(call_control.PendingCallError):
                restored.run(call_id, "job", "answer", "initial", callback)
        callback.assert_not_called()
        self.assertIsNone(restored.report()["usage"]["total_tokens"])

    def test_two_instances_reread_the_shared_checkpoint_before_dispatch(self):
        second = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        self.control.dispatch("c1", "job", "answer", "initial")
        with self.assertRaises(call_control.PendingCallError):
            second.dispatch("c2", "job", "answer", "initial")
        self.control.complete("c1", record())
        self.assertTrue(second.dispatch("c2", "job", "answer", "initial"))

    def test_failed_stub_prevents_next_subprocess_callback_and_retains_known_usage(self):
        failed = record(status="stopped", errors=[{"type": "turn.failed", "message": "provider refused"}])
        subprocess_callback = mock.Mock(return_value=failed)
        with self.assertRaises(call_control.CallControlPaused) as raised:
            self.control.run("c1", "job", "answer", "initial", subprocess_callback)
        self.assertEqual("provider_error", raised.exception.failure_kind)
        self.assertEqual(failed, raised.exception.record)
        with self.assertRaises(call_control.CallControlPaused):
            self.control.run("c2", "job", "answer", "initial", subprocess_callback)
        self.assertEqual(1, subprocess_callback.call_count)
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])
        self.assertEqual("pause_calls", self.control.report()["decision"])
        self.assertEqual(1, self.control.report()["failed_calls"])

    def test_restored_pause_still_blocks_new_calls_but_can_return_earlier_success(self):
        self.run_call("c1", record())
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c2", record("c2", status="stopped"))
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        forbidden = mock.Mock(side_effect=AssertionError("no new callback"))
        self.assertEqual(record(), restored.run("c1", "job", "answer", "initial", forbidden))
        with self.assertRaises(call_control.CallControlPaused):
            restored.run("c3", "job", "answer", "initial", forbidden)
        forbidden.assert_not_called()
        self.assertEqual(26, restored.report()["usage"]["total_tokens"])

    def test_missing_direct_usage_stays_unknown_even_when_fallback_claims_tokens(self):
        missing = record(direct_terminal_usage=None, usage={"input_tokens": 999, "output_tokens": 999})
        with self.assertRaises(call_control.CallControlPaused) as raised:
            self.run_call("c1", missing)
        self.assertEqual("invalid_direct_usage", raised.exception.failure_kind)
        usage = self.control.report()["usage"]
        self.assertIsNone(usage["total_tokens"])
        self.assertEqual(0, usage["known_input_tokens"])
        self.assertEqual(1, usage["unknown_input_tokens_requests"])

    def test_partial_direct_usage_keeps_known_failed_attempt_tokens(self):
        partial = record(direct_terminal_usage={"input_tokens": 7, "cached_input_tokens": 0})
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", partial)
        usage = self.control.report()["usage"]
        self.assertEqual(7, usage["known_input_tokens"])
        self.assertEqual(1, usage["unknown_output_tokens_requests"])
        self.assertIsNone(usage["total_tokens"])

    def test_bad_terminal_count_or_usage_is_not_accepted_as_complete(self):
        invalid = [record(terminal_usage_events=True), record(terminal_usage_events=2),
                   record(input_tokens=True), record(output_tokens=-1), record(cached_input_tokens=11)]
        for index, value in enumerate(invalid):
            control = call_control.CallControl(Path(self.directory.name) / ("bad%d" % index), ["c1"])
            with self.subTest(index=index), self.assertRaises(call_control.CallControlPaused):
                self.run_call("c1", value, control)
            self.assertEqual(0, control.report()["completed_calls"])
            self.assertTrue(control.report()["paused"])

    def test_nonfatal_catalog_stderr_does_not_pause_a_successful_call(self):
        warning = "ERROR codex_models_manager::manager: failed to refresh available models: timeout waiting for child process to exit"
        self.run_call("c1", record(stderr=warning))
        self.assertFalse(self.control.report()["paused"])
        self.assertEqual(1, self.control.report()["completed_calls"])

    def test_callback_exception_is_preserved_and_blocks_later_callback(self):
        callback = mock.Mock(side_effect=ValueError("transport unavailable"))
        with self.assertRaisesRegex(ValueError, "transport unavailable"):
            self.control.run("c1", "job", "answer", "initial", callback)
        self.assertEqual("ValueError", self.control.record("c1")["callback_exception"]["type"])
        self.assertIsNone(self.control.report()["usage"]["total_tokens"])
        with self.assertRaises(call_control.CallControlPaused):
            self.control.run("c2", "job", "answer", "initial", callback)
        self.assertEqual(1, callback.call_count)

    def test_exception_attached_record_preserves_known_usage_before_reraise(self):
        error = ValueError("provider failed after writing result")
        error.record = record(status="stopped")
        with self.assertRaises(ValueError):
            self.control.run("c1", "job", "answer", "initial", mock.Mock(side_effect=error))
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])
        self.assertEqual(error.record, self.control.record("c1"))

    def test_original_results_return_values_and_snapshots_cannot_mutate_saved_state(self):
        original = record(); baseline = copy.deepcopy(original)
        returned = self.run_call("c1", original)
        original["answer"]["answer"] = "outside change"
        returned["direct_terminal_usage"]["input_tokens"] = 999
        snapshot = self.control.snapshot(); snapshot["calls"]["c1"]["record"]["answer"] = {}
        self.assertEqual(baseline, self.control.record("c1"))
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])

    def test_different_terminal_callback_is_rejected_without_replacing_first_record(self):
        self.run_call("c1", record())
        before = self.control.snapshot()
        with self.assertRaises(call_control.ConflictingCallError):
            self.control.complete("c1", record(input_tokens=100))
        self.assertEqual(before, self.control.snapshot())

    def test_checkpoint_checksum_and_plan_changes_fail_closed(self):
        with self.assertRaises(call_control.CallControlError):
            call_control.CallControl(self.path, ["c1", "different"])
        path = self.path / "checkpoint.json"
        envelope = json.loads(path.read_text()); envelope["state"]["revision"] = 100
        path.write_text(json.dumps(envelope))
        with self.assertRaises(call_control.CallControlError):
            call_control.CallControl(self.path, ["c1", "c2", "c3"])

    def test_restore_repairs_stale_progress_from_authoritative_checkpoint(self):
        self.run_call("c1", record())
        (self.path / "progress.json").write_text("{}")
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        self.assertEqual(restored.report(), json.loads((self.path / "progress.json").read_text()))

    def test_unplanned_calls_invalid_plans_and_undispatched_results_are_rejected(self):
        with self.assertRaises(ValueError):
            self.control.dispatch("unknown", "job", "answer", "initial")
        with self.assertRaises(call_control.CallControlError):
            self.control.complete("c1", record())
        with self.assertRaises(ValueError):
            call_control.CallControl(Path(self.directory.name) / "string-plan", "c1")
        with self.assertRaises(ValueError):
            call_control.CallControl(Path(self.directory.name) / "duplicate-plan", ["c1", "c1"])

    def test_optional_skip_completes_plan_without_a_call_or_usage(self):
        self.run_call("c1", record())
        self.assertTrue(self.control.skip("c2", "no document request"))
        self.assertTrue(self.control.skip("c3", "optional judge not needed"))
        before = self.control.snapshot()
        self.assertFalse(self.control.skip("c2", "no document request"))
        self.assertEqual(before, self.control.snapshot())
        report = self.control.report()
        self.assertEqual(1, report["dispatched_calls"])
        self.assertEqual(1, report["completed_calls"])
        self.assertEqual(2, report["skipped_calls"])
        self.assertEqual(3, report["completed_or_skipped_calls"])
        self.assertTrue(report["plan_complete"])
        self.assertEqual("report_results", report["decision"])
        self.assertEqual(13, report["usage"]["total_tokens"])
        self.assertEqual(["c1"], list(before["reducer_state"]["requests"]))
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        self.assertEqual(report, restored.report())

    def test_skip_rejects_dispatched_ids_changed_reasons_and_later_dispatch(self):
        self.control.dispatch("c1", "job", "answer", "initial")
        with self.assertRaises(call_control.ConflictingCallError):
            self.control.skip("c1", "cannot erase an invocation")
        self.control.skip("c2", "not requested")
        with self.assertRaises(call_control.ConflictingCallError):
            self.control.skip("c2", "different reason")
        with self.assertRaises(call_control.ConflictingCallError):
            self.control.dispatch("c2", "job", "answer", "retrieved")
        with self.assertRaises(ValueError):
            self.control.skip("not-planned", "unknown")

    def test_two_failures_acknowledge_current_cause_and_preserve_receipts_usage_and_history(self):
        first = record("c1", status="stopped", timeout=True)
        with self.assertRaises(call_control.CallControlPaused) as initial_error:
            self.run_call("c1", first)
        self.assertEqual("c1", initial_error.exception.call_id)
        before = self.control.snapshot()
        old_usage = self.control.report()["usage"]
        reason = "Continue independent original IDs; preserve the failed receipt.\nNo retry."
        self.assertTrue(self.control.acknowledge_failure("c1", reason))
        acknowledged = self.control.snapshot()
        self.assertEqual(before["calls"], acknowledged["calls"])
        self.assertEqual(before["reducer_state"]["requests"], acknowledged["reducer_state"]["requests"])
        self.assertEqual(old_usage, self.control.report()["usage"])
        self.assertEqual(before["revision"] + 1, acknowledged["revision"])
        event = acknowledged["reducer_state"]["history"][-1]
        self.assertEqual(before["reducer_state"]["history"] + [event], acknowledged["reducer_state"]["history"])
        self.assertEqual("resume", event["type"])
        self.assertEqual("terminal/c1", event["acknowledge"])
        self.assertEqual(reason, event["reason"])
        self.assertFalse(event["allow_unknown_usage"])
        self.assertEqual(before["calls"]["c1"]["record_sha256"], event["failed_record_sha256"])
        self.assertFalse(self.control.report()["paused"])

        second = record("c2", input_tokens=20, output_tokens=5, status="stopped")
        with self.assertRaises(call_control.CallControlPaused) as next_error:
            self.run_call("c2", second)
        self.assertEqual("c2", next_error.exception.call_id)
        self.assertEqual(second, next_error.exception.record)
        blocked = mock.Mock()
        with self.assertRaises(call_control.CallControlPaused) as dispatch_error:
            self.control.run("c3", "job", "answer", "initial", blocked)
        blocked.assert_not_called()
        self.assertEqual("c2", dispatch_error.exception.call_id)
        with self.assertRaises(call_control.CallControlError):
            self.control.acknowledge_failure("c1", "Old failure does not acknowledge the new pause")
        second_before = self.control.snapshot()
        second_usage = self.control.report()["usage"]
        self.control.acknowledge_failure("c2", "Acknowledge the second independent failure")
        self.assertEqual(second_before["calls"], self.control.snapshot()["calls"])
        self.assertEqual(second_usage, self.control.report()["usage"])
        self.run_call("c3", record("c3"))
        restored = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        self.assertEqual(first, restored.record("c1"))
        self.assertEqual(second, restored.record("c2"))
        self.assertEqual(51, restored.report()["usage"]["total_tokens"])
        self.assertEqual(2, restored.report()["failed_calls"])
        self.assertEqual(1, restored.report()["completed_calls"])
        self.assertEqual(3, restored.report()["resolved_planned_calls"])
        self.assertFalse(restored.report()["plan_complete"])

    def test_failed_id_is_rejected_before_and_after_acknowledgment_without_overwrite(self):
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", record(status="stopped"))
        forbidden = mock.Mock(side_effect=AssertionError("failed call must never repeat"))
        for acknowledged in (False, True):
            if acknowledged:
                self.control.acknowledge_failure("c1", "Permit only other independent planned calls")
            before = self.control.snapshot()
            with self.assertRaises(call_control.ConflictingCallError):
                self.control.run("c1", "job", "answer", "initial", forbidden)
            self.assertEqual(before, self.control.snapshot())
        forbidden.assert_not_called()
        self.assertEqual(1, self.control.report()["dispatched_calls"])
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])

    def test_unknown_usage_requires_explicit_acknowledgment_and_remains_unknown(self):
        unknown = record(status="stopped", terminal_usage_events=0, direct_terminal_usage=None)
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", unknown)
        before = self.control.snapshot()
        with self.assertRaisesRegex(call_control.CallControlError, "allow_unknown_usage=True"):
            self.control.acknowledge_failure("c1", "Unknown spend is still unresolved")
        self.assertEqual(before, self.control.snapshot())
        self.control.acknowledge_failure("c1", "Operator explicitly accepts unresolved spend for independent work", allow_unknown_usage=True)
        after = self.control.snapshot()
        event = after["reducer_state"]["history"][-1]
        self.assertTrue(event["allow_unknown_usage"])
        self.assertEqual({field: ["c1"] for field in call_control.FIELDS}, event["unknown_usage_call_ids"])
        self.assertEqual(before["calls"], after["calls"])
        self.assertEqual(before["reducer_state"]["requests"], after["reducer_state"]["requests"])
        self.run_call("c2", record("c2"))
        usage = self.control.report()["usage"]
        self.assertIsNone(usage["total_tokens"])
        self.assertEqual(10, usage["known_input_tokens"])
        self.assertEqual(3, usage["known_output_tokens"])
        self.assertEqual(1, usage["unknown_input_tokens_requests"])
        self.assertEqual(unknown, self.control.record("c1"))

    def test_unknown_cache_counter_also_requires_explicit_acknowledgment(self):
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", record(direct_terminal_usage={"input_tokens": 10, "output_tokens": 3}))
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])
        with self.assertRaises(call_control.CallControlError):
            self.control.acknowledge_failure("c1", "Cache portion is unobserved")
        self.control.acknowledge_failure("c1", "Explicitly accept the unknown cache portion", allow_unknown_usage=True)
        event = self.control.snapshot()["reducer_state"]["history"][-1]
        self.assertEqual({"input_tokens": [], "cached_input_tokens": ["c1"], "output_tokens": []}, event["unknown_usage_call_ids"])
        self.assertEqual(13, self.control.report()["usage"]["total_tokens"])

    def test_acknowledgment_rejects_invalid_metadata_stale_cause_and_pending_calls(self):
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", record(status="stopped"))
        for args in (("c1", "", False), ("c1", " ", False), ("c1", "reason", 1),
                     ("", "reason", False), ("c2", "wrong failure", False)):
            before = self.control.snapshot()
            with self.subTest(args=args), self.assertRaises((ValueError, call_control.CallControlError)):
                self.control.acknowledge_failure(*args)
            self.assertEqual(before, self.control.snapshot())
        stale = call_control.CallControl(self.path, ["c1", "c2", "c3"])
        self.control.acknowledge_failure("c1", "One explicit acknowledgment")
        before = self.control.snapshot()
        with self.assertRaises(call_control.CallControlError):
            stale.acknowledge_failure("c1", "One explicit acknowledgment")
        self.assertEqual(before, self.control.snapshot())
        self.control.dispatch("c2", "job", "answer", "initial")
        before = self.control.snapshot()
        with self.assertRaises(call_control.PendingCallError):
            self.control.acknowledge_failure("c1", "Pending work must block acknowledgment", allow_unknown_usage=True)
        self.assertEqual(before, self.control.snapshot())

    def test_acknowledgment_fails_closed_if_reducer_changes_original_usage(self):
        with self.assertRaises(call_control.CallControlPaused):
            self.run_call("c1", record(status="stopped"))
        before = self.control.snapshot()
        real_reduce = call_control.report_control.reduce_event
        def corrupt_reducer(state, event):
            changed = real_reduce(state, event)
            changed["requests"]["c1"]["usage"]["input_tokens"] = 999
            return changed
        with mock.patch.object(call_control.report_control, "reduce_event", side_effect=corrupt_reducer), \
                self.assertRaises(call_control.CallControlError):
            self.control.acknowledge_failure("c1", "The reducer must preserve accounting")
        self.assertEqual(before, self.control.snapshot())


class SavedRunIntegrationTests(unittest.TestCase):
    @unittest.skipUnless((SAVED / "summary.json").exists(), "ignored archived live run is not available")
    def test_all_38_saved_terminal_records_replay_to_independently_audited_total(self):
        rows = [json.loads(p.read_text()) for p in sorted((SAVED / "calls").glob("*/result.json"))]
        self.assertEqual(38, len(rows))
        direct_total = 0
        for row in rows:
            events = [json.loads(line) for line in (SAVED / "calls" / row["id"] / "events.jsonl").read_text().splitlines()]
            terminal = [e for e in events if e["type"] == "turn.completed"]
            self.assertEqual(1, len(terminal))
            self.assertEqual(terminal[0]["usage"], row["direct_terminal_usage"])
            direct_total += terminal[0]["usage"]["input_tokens"] + terminal[0]["usage"]["output_tokens"]
        self.assertEqual(669726, direct_total)
        with tempfile.TemporaryDirectory() as directory:
            control = call_control.CallControl(directory, [r["id"] for r in rows])
            callback = mock.Mock()
            for row in rows:
                parts = row["id"].rsplit("-", 1)
                callback.return_value = row
                control.run(row["id"], parts[0], row["purpose"], parts[1], callback)
            report = control.report()
            self.assertEqual(38, callback.call_count)
            self.assertEqual(38, report["completed_calls"])
            self.assertEqual(669726, report["usage"]["total_tokens"])
            self.assertEqual(639639, report["usage"]["known_input_tokens"])
            self.assertEqual(132352, report["usage"]["known_cached_input_tokens"])
            self.assertEqual(30087, report["usage"]["known_output_tokens"])
            self.assertFalse(report["paused"])
            restored = call_control.CallControl(directory, [r["id"] for r in rows])
            for row in rows:
                parts = row["id"].rsplit("-", 1)
                restored.run(row["id"], parts[0], row["purpose"], parts[1], callback)
            self.assertEqual(38, callback.call_count)
            self.assertEqual(report, restored.report())


if __name__ == "__main__":
    unittest.main()
