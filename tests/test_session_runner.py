"""Project-state/physical-call integration. All model callbacks are offline fakes."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "skills/vet-flat/scripts")]
import session_runner as runner
import session_hook as hook
from session_state import SessionStore, SessionStateError, ContextOverflow


def provenance(quote="Allow up to 1000 API tokens"):
    return {"actor": "user", "authorized": True, "source_id": "test-user", "quote": quote}


def terminal(amount=20, **changes):
    row = {"id": "answer", "status": "complete", "exit_code": 0,
           "errors": [], "tool_events": [], "malformed_event_lines": 0,
           "terminal_usage_events": 1,
           "direct_terminal_usage": {"input_tokens": amount - 5, "output_tokens": 5,
                                     "cached_input_tokens": 0},
           "answer": "Synthetic response; not a measured model answer."}
    row.update(changes)
    return row


class SessionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = SessionStore(self.root)
        self.store.init("offline-test")
        self.apply({"op": "requirement.add", "id": "dry-ground-floor",
                    "value": "Ground floor allowed", "strength": "conditional",
                    "scope": "candidate-a", "predicate": "Dryness verified at viewing",
                    "provenance": provenance("Ground floor is fine if dry")})
        self.apply({"op": "budget.set", "id": "tokens", "scope": "api_tokens",
                    "limit": 1000, "unit": "tokens", "provenance": provenance()})
        self.apply({"op": "task.add", "id": "check", "title": "Check current evidence",
                    "acceptance": ["Cover the current dryness condition"], "budget_ids": ["tokens"]})
        # Fingerprint is irrelevant to these fake projects; physical-call tests
        # independently exercise source hashing in tests/test_durable_run.py.
        self.source_patch = mock.patch("durable_run.source_fingerprint", return_value={"test.py": "frozen"})
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    def apply(self, event):
        return self.store.apply(event, expected_revision=self.store.show()["revision"])

    def run_step(self, invoke=None, **kwargs):
        values = dict(project=self.root, call_id="step-1", task_id="check", model="test-model",
                      prompt="Review the candidate", token_budget_id="tokens",
                      invoke=invoke or (lambda *_: terminal()))
        values.update(kwargs)
        return runner.run_step(**values)

    def test_full_conditions_precede_callback_and_completion_is_not_automatic(self):
        def invoke(request, folder):
            self.assertIn("Dryness verified at viewing", request["prompt"])
            self.assertIn("candidate-a", request["prompt"])
            self.assertEqual("pending", self.store.show()["dispatches"]["step-1"]["status"])
            self.assertTrue((folder / "manifest.json").is_file())
            return terminal()
        result = self.run_step(invoke)
        self.assertEqual("recorded", result["status"])
        self.assertFalse(result["task_completed"])
        self.assertNotEqual("completed", self.store.show()["tasks"]["check"]["status"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])

    def test_recovery_never_calls_model_or_double_counts_spend(self):
        invoke = mock.Mock(return_value=terminal())
        first = self.run_step(invoke)
        with mock.patch.object(runner, "_codex_invoke", side_effect=AssertionError("no model")):
            second = runner.recover(self.root, "step-1")
            third = runner.recover(self.root, "step-1")
        self.assertEqual(1, invoke.call_count)
        self.assertEqual(first["record_sha256"], second["record_sha256"])
        self.assertEqual(second["record_sha256"], third["record_sha256"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])
        self.assertEqual(1, len(self.store.show()["budgets"]["tokens"]["spends"]))

    def test_new_user_steering_during_call_is_charged_but_result_stays_stale(self):
        def invoke(*_):
            self.apply({"op": "request.capture", "id": "steering",
                        "text": "Actually no ground floors", "source": "test-user"})
            return terminal()
        result = self.run_step(invoke)
        self.assertEqual("stale", result["status"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])
        self.assertEqual("stale", self.store.show()["dispatches"]["step-1"]["status"])

    def test_pending_request_and_paused_task_block_before_callback(self):
        invoke = mock.Mock(return_value=terminal())
        self.apply({"op": "request.capture", "id": "pending", "text": "Budget changed", "source": "user"})
        with self.assertRaises(SessionStateError):
            self.run_step(invoke)
        invoke.assert_not_called()
        self.apply({"op": "request.resolve", "id": "pending", "resolution": "no_change",
                    "note": "Unspecified amount remains an open question"})
        self.apply({"op": "task.update", "id": "check", "changes": {"status": "paused"}})
        with self.assertRaises(SessionStateError):
            self.run_step(invoke)
        invoke.assert_not_called()

    def test_compact_packet_overflow_never_invokes_model(self):
        invoke = mock.Mock(return_value=terminal())
        with self.assertRaises(SessionStateError):
            self.run_step(invoke, max_chars=10)
        invoke.assert_not_called()
        self.assertFalse(self.store.show()["dispatches"])

    def test_large_sources_use_complete_navigation_and_only_explicit_original_spans(self):
        for i in range(9):
            path=self.root/("source-%02d.txt" % i)
            path.write_text('\n'.join("LINE %02d %02d ORIGINAL_%02d %s" %
                                      (i, line, i, 'x'*100)
                                      for line in range(1,41))+'\n')
            self.apply({"op":"document.add","id":"source-%02d" % i,"path":path.name,
                        "line_ranges":[[1,40]],
                        "provenance":{"actor":"source","source_id":path.name,
                                      "quote":"Synthetic saved source"}})
        with self.assertRaises(ContextOverflow):
            self.store.context(max_chars=24000)
        before=self.store.show()
        active={i:r for i,r in before["requirements"].items() if r["status"]=="active"}
        def invoke(request, folder):
            self.assertEqual("navigation",request["packet_kind"])
            self.assertIn("LINE 00 01 ORIGINAL_00",request["prompt"])
            self.assertNotIn("LINE 01 01 ORIGINAL_01",request["prompt"])
            manifest=runner._envelope(folder,"manifest.json")
            self.assertEqual(active,manifest["packet"]["requirements"])
            self.assertEqual(9,len(manifest["packet"]["document_index"]))
            self.assertEqual("navigation",manifest["packet"]["packet_kind"])
            self.assertEqual(runner._digest(manifest["packet"]),request["packet_sha256"])
            self.assertEqual(1,len(request["source_span_refs"]))
            return terminal()
        receipt=self.run_step(invoke,source_spans=[{"document_id":"source-00","start":1,"end":2}])
        self.assertEqual("recorded",receipt["status"])
        self.assertEqual(receipt,runner.recover(self.root,"step-1"))

    def test_source_selection_and_packet_tampering_fail_without_reinterpreting_history(self):
        invoke=mock.Mock(return_value=terminal())
        with self.assertRaises(ValueError):
            self.run_step(invoke,source_spans=[{"document_id":"missing","start":1,"end":1}])
        invoke.assert_not_called()
        self.assertFalse(self.store.show()["dispatches"])
        self.run_step(invoke)
        path=self.root/".pea-state/runs/step-1/manifest.json"
        original=path.read_bytes()
        saved=json.loads(original)
        saved["value"]["packet"]["requirements"]["dry-ground-floor"]["value"]="Tampered value"
        saved["value"]["packet_sha256"]=runner._digest(saved["value"]["packet"])
        saved["value"]["request"]["packet_sha256"]=saved["value"]["packet_sha256"]
        saved["value"]["request_hash"]=runner._digest(saved["value"]["request"])
        saved["sha256"]=runner._digest(saved["value"])
        path.write_text(json.dumps(saved))
        try:
            with self.assertRaises(ValueError):
                runner.recover(self.root,"step-1")
        finally:
            path.write_bytes(original)
        self.assertEqual("recorded",runner.recover(self.root,"step-1")["status"])

    def test_superseded_source_is_retrievable_as_history_but_not_injected_as_current(self):
        old=self.root/"old.txt";old.write_text("Old quote\n")
        new=self.root/"new.txt";new.write_text("New quote\n")
        self.apply({"op":"document.add","id":"old","path":"old.txt","line_ranges":[[1,1]],
                    "provenance":{"actor":"source","source_id":"old","quote":"Old quote"}})
        self.apply({"op":"document.add","id":"new","path":"new.txt","line_ranges":[[1,1]],
                    "supersedes":"old",
                    "provenance":{"actor":"source","source_id":"new","quote":"New quote"}})
        self.assertEqual("Old quote",self.store.retrieve("old",1,1)["text"])
        invoke=mock.Mock(return_value=terminal())
        with self.assertRaises(ValueError):
            self.run_step(invoke,source_spans=[{"document_id":"old","start":1,"end":1}])
        invoke.assert_not_called()
        self.assertFalse(self.store.show()["dispatches"])

    def test_claude_is_paused(self):
        invoke = mock.Mock(return_value=terminal())
        with self.assertRaises(ValueError):
            self.run_step(invoke, model="claude-example")
        invoke.assert_not_called()

    def test_one_call_overshoot_is_recorded_and_next_step_blocked(self):
        self.run_step(lambda *_: terminal(1200))
        budget = self.store.show()["budgets"]["tokens"]
        self.assertEqual(1200, budget["spent"])
        self.assertEqual("paused", budget["status"])
        invoke = mock.Mock(return_value=terminal())
        with self.assertRaises((ValueError, SessionStateError)):
            self.run_step(invoke, call_id="step-2")
        invoke.assert_not_called()

    def test_unknown_usage_is_recorded_and_blocks_future_dispatch(self):
        with self.assertRaises(runner.CallControlError):
            self.run_step(lambda *_: terminal(direct_terminal_usage=None))
        self.assertTrue(self.store.show()["budgets"]["tokens"]["unknown_spend"])
        invoke = mock.Mock(return_value=terminal())
        with self.assertRaises(SessionStateError):
            self.run_step(invoke, call_id="step-2")
        invoke.assert_not_called()

    def test_same_id_and_symlink_output_cannot_redispatch(self):
        self.run_step()
        invoke = mock.Mock(return_value=terminal())
        with self.assertRaises(ValueError):
            self.run_step(invoke)
        invoke.assert_not_called()
        receipt = self.root / ".pea-state/runs/step-1/receipt.json"
        receipt.unlink()
        outside = self.root / "outside.txt"
        outside.write_text("KEEP", encoding="utf-8")
        receipt.symlink_to(outside)
        with self.assertRaises(ValueError):
            runner.recover(self.root, "step-1")
        self.assertEqual("KEEP", outside.read_text())

    def test_manifest_tamper_recovery_rejected(self):
        self.run_step()
        manifest = self.root / ".pea-state/runs/step-1/manifest.json"
        row = json.loads(manifest.read_text())
        row["value"]["request"]["prompt"] = "altered"
        manifest.write_text(json.dumps(row))
        with self.assertRaises(ValueError):
            runner.recover(self.root, "step-1")

    def test_default_text_only_rejects_tool_event_and_keeps_known_usage(self):
        event = {"type": "item.completed", "item": {
            "id": "search-1", "type": "web_search", "status": "completed"}}
        with self.assertRaises(runner.CallControlError):
            self.run_step(lambda *_: terminal(tool_events=[event]))
        folder = self.root / ".pea-state/runs/step-1"
        manifest = runner._envelope(folder, "manifest.json")
        self.assertEqual(2, manifest["version"])
        self.assertEqual("text_only", manifest["tool_policy"])
        self.assertEqual("text_only", manifest["request"]["tool_policy"])
        self.assertEqual(runner._digest(manifest["request"]), manifest["request_hash"])
        self.assertFalse(runner._envelope(folder / "physical", "run.json")["allow_tools"])
        receipt = runner.recover(self.root, "step-1")
        self.assertEqual("failed", receipt["physical_status"])
        self.assertEqual(20, receipt["processed_tokens"])
        self.assertFalse(self.store.show()["budgets"]["tokens"]["unknown_spend"])

    def test_fake_cli_policy_flags_and_live_events_survive_recovery(self):
        for policy, source_status in (("text_only", None), ("live_research", "completed"),
                                      ("live_research", "failed")):
            with self.subTest(policy=policy, source_status=source_status):
                call_id = policy + "-" + (source_status or "plain")
                events = [] if source_status is None else [{"type": "item.completed", "item": {
                    "id": "search-1", "type": "web_search", "status": source_status,
                    "query": "synthetic fixture only"}}]
                raw = "\n".join(json.dumps(event) for event in events + [
                    {"type": "turn.completed", "usage": terminal()["direct_terminal_usage"]}])

                def launch(cmd, cwd, timeout, family, attempts):
                    configs = [cmd[i + 1] for i, arg in enumerate(cmd[:-1]) if arg == "-c"]
                    self.assertIn('web_search="' + ("live" if policy == "live_research" else "disabled") + '"', configs)
                    self.assertIn("project_doc_max_bytes=0", configs)
                    self.assertIn("--ignore-user-config", cmd)
                    self.assertEqual("read-only", cmd[cmd.index("--sandbox") + 1])
                    self.assertEqual("skip_host_skill_discovery", cmd[cmd.index("--enable") + 1])
                    self.assertIn("skills.config=[" + ",".join(
                        "{path=" + json.dumps(str(Path.home() / ".agents/skills" / name)) + ",enabled=false}"
                        for name in ("pea-princess", "vet-flat")) + "]", configs)
                    self.assertEqual(("codex", 1), (family, attempts))
                    Path(cmd[cmd.index("--output-last-message") + 1]).write_text("Synthetic answer")
                    return runner.launch.LaunchResult(stdout=raw, exit_code=0)

                with mock.patch.object(runner.launch, "run", side_effect=launch) as mocked:
                    first = self.run_step(runner._codex_invoke, call_id=call_id, tool_policy=policy)
                mocked.assert_called_once()
                folder = self.root / ".pea-state/runs" / call_id
                manifest = runner._envelope(folder, "manifest.json")
                self.assertEqual((2, policy, policy), (manifest["version"], manifest["tool_policy"],
                                                     manifest["request"]["tool_policy"]))
                self.assertIs(policy == "live_research", runner._envelope(folder / "physical", "run.json")["allow_tools"])
                checkpoint = json.loads((folder / "physical/control/checkpoint.json").read_text())
                record = checkpoint["state"]["calls"]["answer"]["record"]
                self.assertIs(policy == "live_research", checkpoint["state"]["allow_tools"])
                self.assertEqual(events, record["tool_events"])
                self.assertEqual(raw, record["launch_result"]["stdout"])
                self.assertEqual(terminal()["direct_terminal_usage"], record["direct_terminal_usage"])
                revision = self.store.show()["revision"]
                with mock.patch.object(runner.launch, "run", side_effect=AssertionError("no process on recovery")):
                    second = runner.recover(self.root, call_id)
                    third = runner.recover(self.root, call_id)
                self.assertEqual(first, second)
                self.assertEqual(second, third)
                self.assertEqual(revision, self.store.show()["revision"])
                self.assertEqual("complete", first["physical_status"])
                self.assertEqual(20, first["processed_tokens"])
                self.assertEqual(len(events), first["tool_observations"]["event_count"])
                self.assertEqual(int(source_status == "failed"), first["tool_observations"]["explicit_failed_event_count"])
                self.assertFalse(first["tool_observations"]["source_claims_verified"])
        budget = self.store.show()["budgets"]["tokens"]
        self.assertEqual(60, budget["spent"])
        self.assertEqual(3, len(budget["spends"]))
        self.assertFalse(budget["unknown_spend"])

    def test_invalid_tool_policy_is_rejected_before_dispatch(self):
        revision = self.store.show()["revision"]
        invoke = mock.Mock(return_value=terminal())
        for policy in (None, True, "", "live", [], {"live_research": True}):
            with self.subTest(policy=policy):
                with self.assertRaises(ValueError):
                    self.run_step(invoke, tool_policy=policy)
        invoke.assert_not_called()
        self.assertEqual(revision, self.store.show()["revision"])
        self.assertFalse(self.store.show()["dispatches"])
        self.assertFalse((self.root / ".pea-state/runs/step-1").exists())

    def test_rehashed_tool_policy_tampering_is_rejected_by_binding(self):
        self.run_step(tool_policy="live_research")
        folder = self.root / ".pea-state/runs/step-1"
        request_path = next((folder / "physical/requests").glob("*.json"))
        cases = ((folder / "manifest.json", "value", "sha256", "outer"),
                 (folder / "manifest.json", "value", "sha256", "request"),
                 (folder / "manifest.json", "value", "sha256", "both"),
                 (request_path, "value", "sha256", "physical_request"),
                 (folder / "physical/run.json", "value", "sha256", "allow_tools"),
                 (folder / "physical/control/checkpoint.json", "state", "state_sha256", "allow_tools"))
        for path, value_key, hash_key, kind in cases:
            with self.subTest(path=str(path.relative_to(folder)), kind=kind):
                original = path.read_bytes()
                envelope = json.loads(original)
                value = envelope[value_key]
                if kind in ("outer", "both"):
                    value["tool_policy"] = "text_only"
                if kind in ("request", "both", "physical_request"):
                    value["request"]["tool_policy"] = "text_only"
                if kind == "allow_tools":
                    value["allow_tools"] = False
                envelope[hash_key] = runner._digest(value)
                path.write_text(json.dumps(envelope))
                try:
                    with self.assertRaises((ValueError, runner.CallControlError)):
                        runner.recover(self.root, "step-1")
                finally:
                    path.write_bytes(original)
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])
        self.assertEqual("complete", runner.recover(self.root, "step-1")["physical_status"])

    def test_legacy_v1_recovery_accepts_only_absent_tool_policy(self):
        # Build historical evidence in this fresh fake project; never rewrite
        # a SessionStore event or downgrade an already dispatched request.
        packet = self.store.context()
        request = {"model": "test-model", "prompt": "Do not invoke tools. Synthetic legacy request.",
                   "timeout_seconds": 180, "packet_revision": packet["revision"],
                   "packet_event_hash": packet["event_hash"]}
        request_hash = runner._digest(request)
        state = self.apply({"op": "dispatch.start", "id": "legacy", "task_id": "check",
                            "based_on_revision": packet["revision"], "request_hash": request_hash,
                            "budget_ids": ["tokens"]})
        manifest = {"version": 1, "id": "legacy", "task_id": "check", "token_budget_id": "tokens",
                    "request": request, "request_hash": request_hash, "packet": packet,
                    "dispatch_revision": state["revision"]}
        folder = runner._directory(self.root, "legacy", create=True)
        runner._save(folder, "manifest.json", {"value": manifest, "sha256": runner._digest(manifest)})
        control = runner.DurableRun(folder / "physical", ["answer"], {"project_step": request_hash},
                                    max_total_tokens=1000, allow_tools=False, allow_claude=False)
        invoke = mock.Mock(return_value=dict(terminal(), project_request_hash=request_hash))
        control.run_callable("answer", "check", "agent", "project_step", invoke, request=request, family="codex")
        with mock.patch.object(runner, "_codex_invoke", side_effect=AssertionError("legacy recovery is offline")):
            receipt = runner.recover(self.root, "legacy")
        invoke.assert_called_once()
        self.assertEqual((1, "text_only", 20), (receipt["version"], receipt["tool_policy"], receipt["processed_tokens"]))
        for target in (manifest, request):
            with self.subTest(target="outer" if target is manifest else "request"):
                target["tool_policy"] = "text_only"
                runner._save(folder, "manifest.json", {"value": manifest, "sha256": runner._digest(manifest)})
                with self.assertRaises(ValueError):
                    runner.recover(self.root, "legacy")
                del target["tool_policy"]
        runner._save(folder, "manifest.json", {"value": manifest, "sha256": runner._digest(manifest)})
        self.assertEqual(receipt, runner.recover(self.root, "legacy"))

    def record_fact(self):
        self.apply({"op": "fact.record", "id": "latest-fact", "value": "New viewing evidence",
                    "critical": True, "requirement_ids": ["dry-ground-floor"],
                    "provenance": provenance("New evidence arrived")})

    def test_revision_change_before_callback_never_invokes_and_stays_unknown(self):
        invoke = mock.Mock(return_value=terminal())
        original = runner.DurableRun.run_callable

        def changed(control, *args, **kwargs):
            self.record_fact()
            return original(control, *args, **kwargs)

        with mock.patch.object(runner.DurableRun, "run_callable", changed):
            with self.assertRaises(ValueError):
                self.run_step(invoke)
        invoke.assert_not_called()
        state = self.store.show()
        self.assertTrue(state["budgets"]["tokens"]["unknown_spend"])
        self.assertEqual("pending", state["dispatches"]["step-1"]["status"])
        self.assertEqual("stale", runner.recover(self.root, "step-1")["status"])
        # Explicit, evidence-backed reconciliation never rewrites the unknown
        # raw provider telemetry and recovery must not count the cost twice.
        self.apply({"op": "budget.reconcile", "id": "tokens", "dispatch_id": "step-1", "amount": 0,
                    "provenance": provenance("Verified the callback never forwarded a call; actual spend is zero")})
        revision = self.store.show()["revision"]
        receipt = runner.recover(self.root, "step-1")
        self.assertIsNone(receipt["processed_tokens"])
        self.assertEqual(revision, self.store.show()["revision"])
        self.assertFalse(self.store.show()["budgets"]["tokens"]["unknown_spend"])
        with self.assertRaises(SessionStateError):
            self.run_step(invoke, call_id="step-2")
        invoke.assert_not_called()  # Reconciliation does not authorize discard.

    def test_new_fact_during_call_is_charged_but_never_finishes_old_context(self):
        def invoke(*_):
            self.record_fact()
            return terminal()
        receipt = self.run_step(invoke)
        self.assertEqual("stale", receipt["status"])
        self.assertFalse(receipt["current_for_requirements"])
        self.assertEqual("pending", self.store.show()["dispatches"]["step-1"]["status"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])

    def test_completed_result_after_steering_recovers_as_stale(self):
        self.run_step()
        self.record_fact()
        receipt = runner.recover(self.root, "step-1")
        self.assertEqual("stale", receipt["status"])
        self.assertFalse(receipt["current_for_requirements"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])

    def test_stale_failed_and_discarded_results_keep_lifecycle_status(self):
        def invoke(*_):
            self.record_fact()
            return terminal(status="stopped")
        with self.assertRaises(runner.CallControlError):
            self.run_step(invoke)
        receipt = runner.recover(self.root, "step-1")
        self.assertEqual("stale", receipt["status"])
        self.assertEqual("failed", receipt["physical_status"])
        self.apply({"op": "dispatch.discard", "id": "step-1", "process_stopped": True,
                    "usage_accounted": True, "reason": "Reviewed stale offline result",
                    "provenance": provenance("Discard this stopped and fully accounted test call")})
        receipt = runner.recover(self.root, "step-1")
        self.assertEqual("discarded", receipt["status"])
        self.assertFalse(receipt["current_for_requirements"])
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])

    def test_crash_after_spend_recovers_without_double_count_or_false_staleness(self):
        original = SessionStore.apply
        crashed = [False]

        def crash(store, event, *args, **kwargs):
            if event["op"] == "dispatch.finish" and not crashed[0]:
                crashed[0] = True
                raise OSError("synthetic crash after durable cost accounting")
            return original(store, event, *args, **kwargs)

        with mock.patch.object(SessionStore, "apply", crash):
            with self.assertRaises(OSError):
                self.run_step()
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])
        receipt = runner.recover(self.root, "step-1")
        self.assertEqual("recorded", receipt["status"])
        self.assertTrue(receipt["current_for_requirements"])
        self.assertEqual(1, len(self.store.show()["budgets"]["tokens"]["spends"]))

    def test_physical_manifest_or_request_missing_recovery_refuses(self):
        self.run_step()
        physical = self.root / ".pea-state/runs/step-1/physical"
        for path in (physical / "run.json", next((physical / "requests").glob("*.json"))):
            with self.subTest(path=path.name):
                content = path.read_bytes()
                path.unlink()
                with self.assertRaises((ValueError, OSError)):
                    runner.recover(self.root, "step-1")
                path.write_bytes(content)
        self.assertEqual(20, self.store.show()["budgets"]["tokens"]["spent"])

    def test_valid_checkpoint_from_another_request_is_not_accepted(self):
        first = self.run_step()
        self.run_step(lambda *_: terminal(answer="A different request's private answer"),
                      call_id="step-2", prompt="A different bounded step")
        runs = self.root / ".pea-state/runs"
        target = runs / "step-1/physical/control/checkpoint.json"
        target.write_bytes((runs / "step-2/physical/control/checkpoint.json").read_bytes())
        with self.assertRaises(ValueError):
            runner.recover(self.root, "step-1")
        saved = json.loads((runs / "step-1/receipt.json").read_text())
        self.assertEqual(first["answer"], saved["answer"])
        self.assertEqual(40, self.store.show()["budgets"]["tokens"]["spent"])

    def test_physical_lock_symlink_and_fifo_never_opened(self):
        self.run_step()
        lock = self.root / ".pea-state/runs/step-1/physical/control/controller.lock"
        lock.unlink()
        outside = self.root / "outside-lock"
        outside.write_text("KEEP")
        lock.symlink_to(outside)
        with self.assertRaises(ValueError):
            runner.recover(self.root, "step-1")
        self.assertEqual("KEEP", outside.read_text())
        lock.unlink()
        os.mkfifo(lock)
        with self.assertRaises(ValueError):
            runner.recover(self.root, "step-1")

    def test_oversize_checkpoint_refused_before_controller_reads(self):
        self.run_step()
        checkpoint = self.root / ".pea-state/runs/step-1/physical/control/checkpoint.json"
        with checkpoint.open("wb") as output:
            output.truncate(32 * 1024 * 1024 + 1)
        with mock.patch.object(runner, "CallControl", side_effect=AssertionError("must not read")):
            with self.assertRaises(ValueError):
                runner.recover(self.root, "step-1")

    def test_output_artifact_failures_keep_observed_tokens(self):
        for kind in ("missing", "symlink", "oversize", "encoding", "fifo"):
            with self.subTest(kind=kind):
                call_id = "artifact-" + kind

                def launch(cmd, cwd, timeout, family, attempts):
                    self.assertEqual(1, attempts)
                    self.assertEqual("codex", family)
                    self.assertIn("--ignore-user-config", cmd)
                    self.assertIn("--ephemeral", cmd)
                    self.assertIn("--json", cmd)
                    answer = Path(cmd[cmd.index("--output-last-message") + 1])
                    if kind == "symlink":
                        answer.symlink_to(self.root / "outside-answer")
                    elif kind == "oversize":
                        answer.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
                    elif kind == "encoding":
                        answer.write_bytes(b"\xff")
                    elif kind == "fifo":
                        os.mkfifo(answer)
                    event = {"type": "turn.completed", "usage": terminal()["direct_terminal_usage"]}
                    return runner.launch.LaunchResult(stdout=json.dumps(event), exit_code=0)

                with mock.patch.object(runner.launch, "run", side_effect=launch) as mocked:
                    with self.assertRaises(runner.CallControlError):
                        self.run_step(runner._codex_invoke, call_id=call_id)
                mocked.assert_called_once()
                budget = self.store.show()["budgets"]["tokens"]
                self.assertFalse(budget["unknown_spend"])
                self.assertEqual(20, budget["spends"][-1]["amount"])
                receipt = runner.recover(self.root, call_id)
                self.assertEqual("failed", receipt["status"])
                self.assertEqual("", receipt["answer"])

    def test_extra_task_execution_budget_rejected_before_dispatch(self):
        for scope, unit in (("execution_spend", "USD"), ("api_tokens", "tokens")):
            with self.subTest(scope=scope):
                identifier = "other-" + scope
                self.apply({"op": "budget.set", "id": identifier, "scope": scope, "unit": unit,
                            "limit": 100, "provenance": provenance("Also honor this execution budget")})
                self.apply({"op": "task.update", "id": "check", "changes": {"budget_ids": ["tokens", identifier]}})
                invoke = mock.Mock(return_value=terminal())
                with self.assertRaises(ValueError):
                    self.run_step(invoke)
                invoke.assert_not_called()
                self.assertFalse(self.store.show()["dispatches"])

    def test_rental_budget_is_not_charged_as_api_spend(self):
        self.apply({"op": "budget.set", "id": "rent", "scope": "rental", "unit": "GBP/month",
                    "limit": 2000, "provenance": provenance("Monthly rent ceiling is 2000 GBP")})
        self.apply({"op": "task.update", "id": "check", "changes": {"budget_ids": ["tokens", "rent"]}})
        self.run_step()
        self.assertEqual(0, self.store.show()["budgets"]["rent"]["spent"])


class SessionHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = SessionStore(self.root)
        self.store.init("hook-test")

    def test_exact_user_prompt_saved_but_default_output_is_short_pointer(self):
        raw = "  New ceiling: £2,300/month.\nGround floor only if dry.  "
        output = hook.handle({"hook_event_name": "UserPromptSubmit", "prompt": raw}, self.root)
        requests = list(self.store.show()["requests"].values())
        self.assertEqual(raw, requests[0]["text"])
        self.assertEqual("pending", requests[0]["status"])
        self.assertNotIn("2,300", json.dumps(output))
        self.assertLess(len(json.dumps(output)), 1000)

    def test_compact_checkpoint_and_resume_read_latest_state(self):
        hook.handle({"hook_event_name": "UserPromptSubmit", "prompt": "Keep all conditions"}, self.root)
        self.assertEqual({}, hook.handle({"hook_event_name": "PreCompact"}, self.root))
        self.assertTrue(self.store.verify()["checkpoint"]["current"])
        output = hook.handle({"hook_event_name": "SessionStart", "source": "compact"}, self.root,
                             max_chars=24000, inline=True)
        self.assertIn("Keep all conditions", output["hookSpecificOutput"]["additionalContext"])
        self.assertIn("navigation --max-chars 24000.", output["hookSpecificOutput"]["additionalContext"])
        saved=json.loads((self.store.state_root/"checkpoint.json").read_text())
        self.assertEqual("navigation",saved["packet"]["packet_kind"])

    def test_large_project_hook_uses_short_navigation_pointer_and_bounded_checkpoint(self):
        for i in range(9):
            path=self.root/("hook-source-%02d.txt" % i)
            path.write_text('\n'.join("HOOK_EXCERPT_%02d %s" % (i,'z'*130)
                                      for _ in range(40))+'\n')
            state=self.store.show()
            self.store.apply({"op":"document.add","id":"hook-source-%02d" % i,
                              "path":path.name,"line_ranges":[[1,40]],
                              "provenance":{"actor":"source","source_id":path.name,
                                            "quote":"Synthetic source"}},
                             expected_revision=state["revision"])
        with self.assertRaises(ContextOverflow):
            self.store.context(max_chars=24000)
        pointer=hook.handle({"hook_event_name":"SessionStart"},self.root)
        text=pointer["hookSpecificOutput"]["additionalContext"]
        self.assertIn("navigation --max-chars 96000.",text)
        self.assertNotIn("HOOK_EXCERPT_",text)
        self.assertLess(len(text),2500)
        self.assertEqual({},hook.handle({"hook_event_name":"PreCompact"},self.root))
        saved=json.loads((self.store.state_root/"checkpoint.json").read_text())
        self.assertEqual("navigation",saved["packet"]["packet_kind"])
        self.assertEqual(9,len(saved["packet"]["document_index"]))
        self.assertTrue(self.store.verify()["checkpoint"]["current"])
        captured=hook.handle({"hook_event_name":"UserPromptSubmit",
                              "prompt":"PRIVATE_RAW_NEW_REQUEST"},self.root)
        self.assertNotIn("PRIVATE_RAW_NEW_REQUEST",
                         captured["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(1,len(self.store.navigation(96000)["pending_requests"]))

    def test_hook_cwd_cannot_redirect_capture_to_other_project(self):
        hook.handle({"hook_event_name": "UserPromptSubmit", "prompt": "Safe capture", "cwd": "/tmp/attacker"}, self.root)
        self.assertEqual(1, len(self.store.show()["requests"]))

    def hook_main(self, raw, host="codex", extra=()):
        output, errors = io.StringIO(), io.StringIO()
        stdin = io.TextIOWrapper(io.BytesIO(raw))
        with mock.patch.object(sys, "argv", ["session_hook", "--project", str(self.root), "--host", host] + list(extra)), \
                mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", output), \
                mock.patch.object(sys, "stderr", errors):
            status = hook.main()
        return status, json.loads(output.getvalue()), errors.getvalue()

    def test_malformed_or_ambiguous_hook_event_fails_without_echo(self):
        for raw in (b'{"prompt":"PRIVATE_SENTINEL","prompt":"other","hook_event_name":"UserPromptSubmit"}',
                    b'{"prompt":"PRIVATE_SENTINEL","x":NaN,"hook_event_name":"UserPromptSubmit"}',
                    b"PRIVATE_SENTINEL", b"PRIVATE_SENTINEL" + b" " * hook.MAX_INPUT_BYTES):
            with self.subTest(raw_length=len(raw)):
                status, result, errors = self.hook_main(raw)
                self.assertEqual(0, status)  # Codex consumes successful JSON decisions.
                self.assertFalse(result["continue"])
                self.assertNotIn("PRIVATE_SENTINEL", json.dumps(result) + errors)
                self.assertFalse(self.store.show()["requests"])
        status, result, _ = self.hook_main(b"invalid", host="claude")
        self.assertEqual(2, status)
        self.assertFalse(result["continue"])

    def test_context_overflow_saves_capture_but_never_returns_truncated_packet(self):
        raw = json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": "PRIVATE_SENTINEL exact new conditions"}).encode()
        _, result, errors = self.hook_main(raw, extra=("--max-chars", "10", "--inline"))
        self.assertFalse(result["continue"])
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(result) + errors)
        captured = list(self.store.show()["requests"].values())
        self.assertEqual(1, len(captured))
        self.assertEqual("PRIVATE_SENTINEL exact new conditions", captured[0]["text"])


if __name__ == "__main__":
    unittest.main()
