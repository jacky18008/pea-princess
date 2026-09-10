"""Offline physical-call boundary, restart, provenance and artifact tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import durable_run as d
import launch
from call_control import CallControlError, CallControlPaused, ConflictingCallError, PendingCallError


def events(usage=None, extra=None):
    usage = usage if usage is not None else {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3}
    return "\n".join(json.dumps(row) for row in (extra or []) + [{"type": "turn.completed", "usage": usage}])


def result(raw=None, **kwargs):
    raw = events() if raw is None else raw
    return launch.LaunchResult(text=raw, stdout=raw, stderr="diagnostic", exit_code=0,
                               attempt_records=[{"attempt": 1, "usage": {}, "timeout": False}], **kwargs)


class DurableRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fingerprints = mock.patch.object(d, "source_fingerprint", return_value={"runner.py": "frozen"})
        self.fingerprints.start()
        self.addCleanup(self.fingerprints.stop)

    def session(self, **kwargs):
        return d.DurableRun(self.root / "run", ["c1", "c2"], {"model": "frozen-model"}, **kwargs)

    def cli(self, session, call_id="c1", command=None, cwd=None):
        return session.run_cli(call_id, "job", "agent", "turn", command or ["codex", "exec", "--model", "frozen-model", "PROMPT"],
                               cwd or self.root, 60, "codex")

    def test_dispatch_precedes_process_and_restart_replays_full_streams(self):
        session = self.session()
        def invoke(*args, **kwargs):
            self.assertEqual(["c1"], session.report()["pending_call_ids"])
            return result()
        with mock.patch.object(launch, "run", side_effect=invoke) as launched:
            first = self.cli(session)
            second = self.cli(self.session())
        self.assertEqual(first, second)
        self.assertEqual(1, launched.call_count)
        self.assertEqual("diagnostic", second.stderr)
        self.assertEqual(events(), second.stdout)
        self.assertEqual(13, session.report()["usage"]["total_tokens"])

    def test_failure_stops_later_calls_after_restart_preserving_known_usage(self):
        failure = result(raw=events(extra=[{"type": "turn.failed", "message": "provider stopped"}]))
        with mock.patch.object(launch, "run", return_value=failure) as launched:
            with self.assertRaises(CallControlPaused):
                self.cli(self.session())
            restored = self.session()
            with self.assertRaises(CallControlPaused):
                self.cli(restored, "c2")
        self.assertEqual(1, launched.call_count)
        self.assertEqual(13, restored.report()["usage"]["total_tokens"])
        self.assertEqual(1, restored.report()["failed_calls"])

    def test_orphan_pending_call_never_retries(self):
        session = self.session()
        session.control.dispatch("c1", "job", "agent", "turn")
        with mock.patch.object(launch, "run") as launched:
            with self.assertRaises(CallControlError):
                self.cli(self.session())
        launched.assert_not_called()

    def test_changed_model_prompt_timeout_config_source_and_tool_policy_refuse_replay(self):
        with mock.patch.object(launch, "run", return_value=result()):
            self.cli(self.session())
        for command in (["codex", "exec", "--model", "changed", "PROMPT"],
                        ["codex", "exec", "--model", "frozen-model", "changed prompt"]):
            with self.subTest(command=command), self.assertRaises(ConflictingCallError):
                self.cli(self.session(), command=command)
        with self.assertRaises(ConflictingCallError):
            d.DurableRun(self.root / "run", ["c1", "c2"], {"model": "changed"})
        with self.assertRaises(ConflictingCallError):
            self.session(allow_tools=True)
        with mock.patch.object(d, "source_fingerprint", return_value={"runner.py": "changed"}):
            with self.assertRaises(ConflictingCallError):
                self.session()

    def test_retry_budget_rejected_before_first_physical_attempt(self):
        with mock.patch.object(launch, "run") as launched, self.assertRaises(ValueError):
            self.session().run_cli("c1", "job", "agent", "turn", ["codex"], self.root, 60, "codex", attempts=2)
        launched.assert_not_called()

    def test_claude_stays_paused_without_explicit_frozen_optin(self):
        with mock.patch.object(launch, "run") as launched, self.assertRaisesRegex(CallControlError, "Claude calls remain paused"):
            self.session().run_cli("c1", "job", "agent", "turn", ["claude", "--model", "sonnet"], self.root, 60, "claude")
        launched.assert_not_called()
        self.assertEqual(0, self.session().report()["dispatched_calls"])

    def test_claude_api_model_is_paused_without_invoking_callback(self):
        callback = mock.Mock()
        with self.assertRaisesRegex(CallControlError, "Claude calls remain paused"):
            self.session().run_api("c1", "job", "agent", "turn", callback, "anthropic/claude-sonnet")
        callback.assert_not_called()

    def test_between_call_budget_keeps_completed_replay_but_blocks_new_call(self):
        with mock.patch.object(launch, "run", return_value=result()) as launched:
            session = self.session(max_total_tokens=10)
            self.cli(session)
            self.cli(self.session(max_total_tokens=10))
            with self.assertRaisesRegex(CallControlPaused, "budget reached"):
                self.cli(session, "c2")
        self.assertEqual(1, launched.call_count)
        self.assertTrue((session.output_dir / "budget-stop.json").exists())

    def test_tool_policy_accepts_tools_only_when_frozen_enabled(self):
        tool = {"type": "item.completed", "item": {"type": "command_execution", "command": "echo ok"}}
        with mock.patch.object(launch, "run", return_value=result(raw=events(extra=[tool]))):
            with self.assertRaises(CallControlPaused) as raised:
                self.cli(self.session())
        self.assertEqual("unexpected_tool_use", raised.exception.failure_kind)
        toolroot = self.root / "tool-run"
        workdir = toolroot / "work"
        workdir.mkdir(parents=True)
        enabled = d.DurableRun(toolroot, ["c1"], {}, allow_tools=True)
        with mock.patch.object(launch, "run", return_value=result(raw=events(extra=[tool]))):
            self.cli(enabled, cwd=workdir)
        self.assertEqual(1, enabled.report()["completed_calls"])

    def test_tool_workdir_must_be_inside_run(self):
        with mock.patch.object(launch, "run") as launched, self.assertRaises(CallControlError):
            self.cli(self.session(allow_tools=True), cwd=self.root)
        launched.assert_not_called()

    def test_completed_replay_restores_tool_side_effects_and_removes_future_files(self):
        session = self.session(allow_tools=True)
        folder = session.output_dir / "work"
        folder.mkdir()
        (folder / "profile.yaml").write_text("original")
        def invoke(*args, **kwargs):
            (folder / "profile.yaml").write_text("after c1")
            return result()
        with mock.patch.object(launch, "run", side_effect=invoke) as launched:
            self.cli(session, cwd=folder)
            (folder / "profile.yaml").write_text("after c2")
            (folder / "future.txt").write_text("created by later turn")
            self.cli(self.session(allow_tools=True), cwd=folder)
        self.assertEqual(1, launched.call_count)
        self.assertEqual("after c1", (folder / "profile.yaml").read_text())
        self.assertFalse((folder / "future.txt").exists())

    def test_symlink_is_rejected_before_call(self):
        session = self.session(allow_tools=True)
        folder = session.output_dir / "work"
        folder.mkdir()
        (folder / "escape").symlink_to(self.root / "elsewhere")
        with mock.patch.object(launch, "run") as launched, self.assertRaises(CallControlError):
            self.cli(session, cwd=folder)
        launched.assert_not_called()

    def test_oversized_postcall_snapshot_retains_usage_and_stops_batch(self):
        session = self.session(allow_tools=True)
        folder = session.output_dir / "work"
        folder.mkdir()
        def invoke(*args, **kwargs):
            (folder / "too-big").write_bytes(b"0123456789")
            return result()
        with mock.patch.object(d, "MAX_SNAPSHOT_BYTES", 5), mock.patch.object(launch, "run", side_effect=invoke):
            with self.assertRaises(CallControlPaused):
                self.cli(session, cwd=folder)
        self.assertEqual(13, session.report()["usage"]["total_tokens"])
        self.assertIn("artifact_error", session.control.record("c1"))

    def test_output_last_message_replayed_to_new_runtime_path(self):
        session = self.session()
        output = self.root / "answer.json"
        command = ["codex", "exec", "--model", "frozen-model", "--output-last-message", str(output), "PROMPT"]
        def invoke(*args, **kwargs):
            output.write_text('{"answer":"saved"}')
            return result()
        with mock.patch.object(launch, "run", side_effect=invoke) as launched:
            self.cli(session, command=command)
            output.unlink()
            target = self.root / "new-answer.json"
            self.cli(self.session(), command=["codex", "exec", "--model", "frozen-model", "--output-last-message", str(target), "PROMPT"])
        self.assertEqual('{"answer":"saved"}', target.read_text())
        self.assertEqual(1, launched.call_count)

    def test_last_message_escape_and_symlink_parent_refuse_before_call(self):
        session = self.session()
        external = self.root.parent / "escaped-output.txt"
        link = self.root / "linked"
        link.symlink_to(self.root, target_is_directory=True)
        for target in (external, link / "output.txt"):
            with self.subTest(target=target), mock.patch.object(launch, "run") as launched:
                with self.assertRaises(CallControlError):
                    self.cli(session, command=["codex", "exec", "--model", "model", "-o", str(target), "prompt"])
                launched.assert_not_called()

    def test_api_exact_tuple_replay_and_partial_usage_fail_closed(self):
        session = self.session()
        expected = ("response", {"prompt_tokens": 10, "completion_tokens": 3,
                                "prompt_tokens_details": {"cached_tokens": 2}}, None)
        callback = mock.Mock(return_value=expected)
        first = session.run_api("c1", "job", "agent", "turn", callback, "api-model", {"prompt": "one"})
        second = self.session().run_api("c1", "job", "agent", "turn", callback, "api-model", {"prompt": "one"})
        self.assertEqual(expected, first)
        self.assertEqual(expected, second)
        self.assertEqual(1, callback.call_count)
        callback.return_value = ("partial", {"prompt_tokens": 7}, "timeout")
        with self.assertRaises(CallControlPaused):
            session.run_api("c2", "job", "agent", "turn", callback, "api-model")
        self.assertEqual(17, session.report()["usage"]["known_input_tokens"])
        self.assertIsNone(session.report()["usage"]["total_tokens"])

    def test_api_missing_cache_is_unknown_not_zero_and_no_secret_key_saved(self):
        session = self.session()
        with self.assertRaises(CallControlPaused):
            session.run_api("c1", "job", "agent", "turn", lambda: ("answer", {
                "prompt_tokens": 7, "completion_tokens": 2}, None), "api-model", {"endpoint": "https://example.test"})
        report = session.report()
        self.assertEqual(7, report["usage"]["known_input_tokens"])
        self.assertEqual(1, report["usage"]["unknown_cached_input_tokens_requests"])
        self.assertEqual(1, report["failed_calls"])


    def test_lost_checkpoint_or_manifest_never_initializes_a_fresh_paid_run(self):
        with mock.patch.object(launch, "run", return_value=result()) as launched:
            session = self.session()
            self.cli(session)
            (session.output_dir / "control" / "checkpoint.json").unlink()
            with self.assertRaisesRegex(CallControlError, "do not redispatch"):
                self.session()
        self.assertEqual(1, launched.call_count)

    def test_missing_request_manifest_blocks_completed_replay(self):
        with mock.patch.object(launch, "run", return_value=result()) as launched:
            session = self.session()
            self.cli(session)
            next((session.output_dir / "requests").glob("*.json")).unlink()
            with self.assertRaisesRegex(CallControlError, "request manifest"):
                self.cli(self.session())
        self.assertEqual(1, launched.call_count)

    def test_in_process_source_changes_block_new_call_and_completed_replay(self):
        session = self.session()
        with mock.patch.object(launch, "run", return_value=result()) as launched:
            self.cli(session)
            with mock.patch.object(d, "source_fingerprint", return_value={"runner.py": "changed"}):
                for call_id in ("c1", "c2"):
                    with self.assertRaisesRegex(ConflictingCallError, "source changed"):
                        self.cli(session, call_id)
        self.assertEqual(1, launched.call_count)

    def test_in_process_selected_external_input_change_blocks_dispatch(self):
        fixture = self.root / "fixture.txt"
        fixture.write_text("original")
        session = d.DurableRun(self.root / "run", ["c1", "c2"], {"input_sha256": {
            str(fixture): d.hashlib.sha256(fixture.read_bytes()).hexdigest()}})
        fixture.write_text("changed")
        with mock.patch.object(launch, "run") as launched, self.assertRaisesRegex(ConflictingCallError, "input changed"):
            self.cli(session)
        launched.assert_not_called()

    def test_no_explicit_model_refuses_before_call(self):
        with mock.patch.object(launch, "run") as launched, self.assertRaisesRegex(ValueError, "explicit model"):
            self.cli(self.session(), command=["codex", "exec", "prompt"])
        launched.assert_not_called()

    def test_nonfinite_counter_is_saved_as_failed_with_original_raw_evidence(self):
        session = self.session()
        raw = events({"input_tokens": float("nan"), "cached_input_tokens": 0, "output_tokens": 3})
        with mock.patch.object(launch, "run", return_value=result(raw=raw)), self.assertRaises(CallControlPaused):
            self.cli(session)
        saved = session.control.record("c1")
        self.assertIn("NaN", saved["launch_result"]["stdout"])
        self.assertIsNone(saved["direct_terminal_usage"]["input_tokens"])
        self.assertEqual(1, session.report()["failed_calls"])


class DirectTelemetryTests(unittest.TestCase):
    def feature_warning(self, message=None, **item_fields):
        return {"type":"item.completed", "item":dict({"id":"item_0", "type":"error",
            "message":message or "Under-development features enabled: skip_host_skill_discovery. "
                "Under-development features are incomplete and may behave unpredictably. "
                "To suppress this warning, set `suppress_unstable_features_warning = true` "
                "in /home/example/.codex/config.toml."}, **item_fields)}

    def test_known_startup_warning_is_retained_without_becoming_a_tool(self):
        warning=self.feature_warning()
        raw=events(extra=[{"type":"thread.started","thread_id":"t"},warning,
                          {"type":"turn.started"}])
        record=d.cli_record("c",result(raw=raw),"codex")
        self.assertIsNone(d.failure_kind(record))
        self.assertEqual([warning],record["diagnostic_events"])
        self.assertEqual([],record["tool_events"]);self.assertEqual([],record["errors"])
        self.assertEqual(raw,record["launch_result"]["stdout"])
        self.assertEqual({"input_tokens":10,"cached_input_tokens":2,"output_tokens":3},record["direct_terminal_usage"])

    def test_warning_does_not_hide_real_or_unknown_tools(self):
        for kind in ("web_search","command_execution","new_future_tool","error"):
            with self.subTest(kind=kind):
                tool={"type":"item.completed","item":{"id":"item_1","type":kind,"message":"other event"}}
                record=d.cli_record("c",result(raw=events(extra=[
                    {"type":"thread.started"},self.feature_warning(),{"type":"turn.started"},tool])),"codex")
                self.assertEqual("unexpected_tool_use",d.failure_kind(record))
                self.assertEqual([tool],record["tool_events"])
                self.assertEqual([self.feature_warning()],record["diagnostic_events"])

    def test_warning_recognition_is_exact_and_only_before_the_turn(self):
        known=self.feature_warning()["item"]["message"]
        variants=[self.feature_warning(message="unrecognized error"),
                  self.feature_warning(message=known.replace("skip_host_skill_discovery.","other_feature.")),
                  self.feature_warning(message=known.replace("skip_host_skill_discovery.","skip_host_skill_discovery, other_feature.")),
                  self.feature_warning(message=known+" Additional error."),
                  self.feature_warning(message=known.replace("/home/example/.codex/config.toml","relative/config.toml")),
                  self.feature_warning(command="unexpected command"),
                  self.feature_warning(id=""),
                  dict(self.feature_warning(),type="item.started")]
        sequences=[[{"type":"thread.started"},variant] for variant in variants]
        sequences += [[{"type":"thread.started"},{"type":"turn.started"},self.feature_warning()],
                      [self.feature_warning()]]
        for sequence in sequences:
            with self.subTest(sequence=sequence):
                record=d.cli_record("c",result(raw=events(extra=sequence)),"codex")
                self.assertEqual("unexpected_tool_use",d.failure_kind(record))
                self.assertEqual([],record["diagnostic_events"])

    def test_startup_diagnostic_does_not_hide_top_level_error_or_missing_usage(self):
        warning=self.feature_warning()
        record=d.cli_record("c",result(raw=events(extra=[{"type":"thread.started"},warning,
            {"type":"error","message":warning["item"]["message"]}])),"codex")
        self.assertEqual("provider_error",d.failure_kind(record))
        self.assertEqual([warning],record["diagnostic_events"])
        raw='\n'.join(json.dumps(e) for e in [{"type":"thread.started"},warning])
        self.assertEqual("invalid_direct_usage",d.failure_kind(d.cli_record("c",result(raw=raw),"codex")))

    def test_codex_multiple_terminals_or_malformed_stdout_are_not_valid_direct_usage(self):
        for raw in (events() + "\n" + events(), "not-json\n" + events()):
            record = d.cli_record("c", result(raw=raw), "codex")
            self.assertIsNotNone(d.failure_kind(record))

    def test_claude_input_includes_read_and_creation_cache_once(self):
        raw = json.dumps({"type": "result", "result": "ok", "usage": {
            "input_tokens": 10, "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 20, "output_tokens": 3}})
        record = d.cli_record("c", result(raw=raw), "claude")
        self.assertEqual({"input_tokens": 130, "cached_input_tokens": 100, "output_tokens": 3}, record["direct_terminal_usage"])
        self.assertIsNone(d.failure_kind(record))

    def test_missing_claude_creation_count_does_not_claim_complete_total(self):
        raw = json.dumps({"result": "ok", "usage": {"input_tokens": 10,
            "cache_read_input_tokens": 100, "output_tokens": 3}})
        record = d.cli_record("c", result(raw=raw), "claude")
        self.assertEqual({"cached_input_tokens": 100, "output_tokens": 3}, record["direct_terminal_usage"])
        self.assertEqual("invalid_direct_usage", d.failure_kind(record))

    def test_inconsistent_totals_aliases_and_cache_details_are_rejected(self):
        for usage in (
                {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3, "total_tokens": 999},
                {"input_tokens": 10, "prompt_tokens": 11, "cached_input_tokens": 2, "output_tokens": 3},
                {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3,
                 "prompt_tokens_details": {"cached_tokens": 3}},
                {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3,
                 "cache_read_input_tokens": 3}):
            with self.subTest(usage=usage):
                record = d.cli_record("c", result(raw=events(usage)), "codex")
                self.assertEqual("invalid_direct_usage", d.failure_kind(record))

    def test_unknown_codex_item_is_unexpected_tool_use_under_default_policy(self):
        record = d.cli_record("c", result(raw=events(extra=[{
            "type": "item.completed", "item": {"type": "new_future_tool"}}])), "codex")
        self.assertEqual("unexpected_tool_use", d.failure_kind(record))
        self.assertIsNone(d.failure_kind(record, allow_tools=True))

    def test_launch_captures_complete_stream_even_when_tail_is_truncated(self):
        raw = events(extra=[{"type": "item.completed", "item": {"type": "agent_message", "text": "x" * 1000}}])
        res = launch.run([sys.executable, "-c", "print(" + repr(raw) + ")"], str(Path.cwd()), 5, "codex")
        self.assertGreater(len(res.stdout), launch.TAIL_CHARS)
        self.assertEqual(13, sum(d.cli_record("c", res, "codex")["direct_terminal_usage"][k] for k in ("input_tokens", "output_tokens")))


if __name__ == "__main__":
    unittest.main()
