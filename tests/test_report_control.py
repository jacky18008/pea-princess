"""Offline hand-authored oracle and hard properties for the controller prototype."""
import copy
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench"))
import report_control as controller


def dispatch(event_id, request_id, session, stage="agent"):
    return {"id": event_id, "type": "dispatch", "request_id": request_id,
            "session": session, "stage": stage}


def event(event_id, kind, request_id, **fields):
    return dict(id=event_id, type=kind, request_id=request_id, **fields)


def replay_events(sessions, events):
    state = controller.initial_state(sessions)
    for item in events:
        state = controller.reduce_event(state, item)
    return state


class IndependentOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(controller.CASES.read_text(encoding="utf-8"))

    def test_twenty_independently_authored_full_reports_and_prefixes(self):
        self.assertEqual(20, len(self.fixture["cases"]))
        self.assertEqual(81, sum(len(c["events"]) for c in self.fixture["cases"]))
        for case in self.fixture["cases"]:
            with self.subTest(trace=case["id"]):
                result = controller.replay(case)
                self.assertTrue(result["pass"], result["failures"])
                self.assertEqual(case["events"], result["original_events"])

    def test_serialized_checkpoint_resume_at_every_boundary_matches_authored_oracle(self):
        # Restoring a checkpoint is distinct from the explicit resume event that
        # acknowledges a provider outage; a restore must not clear its pause.
        for case in self.fixture["cases"]:
            for split in range(len(case["events"]) + 1):
                with self.subTest(trace=case["id"], split=split):
                    state = replay_events(case["sessions"], case["events"][:split])
                    restored = json.loads(json.dumps(state))
                    for item in case["events"][split:]:
                        restored = controller.reduce_event(restored, item)
                    self.assertEqual([], controller._compare(controller.report(restored), case["expected"]))
                    self.assertEqual(case["events"], restored["history"])

    def test_oracle_and_prefix_invariants_detect_a_disabled_pause_guard(self):
        original_reduce = controller.reduce_event

        def broken_reduce(state, item):
            if state["paused"] and item["type"] == "dispatch":
                state = copy.deepcopy(state)
                state["paused"] = False
            return original_reduce(state, item)

        case = self.fixture["cases"][11]
        with mock.patch.object(controller, "reduce_event", side_effect=broken_reduce):
            result = controller.replay(case)
        self.assertFalse(result["pass"])
        self.assertTrue(any("dispatch accepted while paused" in f for f in result["failures"]))
        self.assertTrue(any("scheduled_requests" in f for f in result["failures"]))

    def test_exact_oracle_rejects_unknown_usage_changed_to_zero_and_wrong_field_types(self):
        case = self.fixture["cases"][6]
        for path, replacement in [(('usage', 'total_tokens'), 0),
                                  (('observed_sessions',), True),
                                  (('quality', 'mean_grade'), 0.0)]:
            altered = copy.deepcopy(case)
            target = altered["expected"]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = replacement
            self.assertFalse(controller.replay(altered)["pass"])


class ReducerPropertyTests(unittest.TestCase):
    def test_input_event_and_prior_state_are_immutable(self):
        prior = controller.initial_state(["A"])
        first = dispatch("e1", "r1", "A")
        saved_prior, saved_event = copy.deepcopy(prior), copy.deepcopy(first)
        state = controller.reduce_event(prior, first)
        self.assertEqual(saved_prior, prior)
        self.assertEqual(saved_event, first)
        first["session"] = "changed outside reducer"
        self.assertEqual("A", state["history"][0]["session"])
        state["history"][0]["session"] = "changed inside new state"
        self.assertEqual(saved_prior, prior)

    def test_all_late_usage_permutations_preserve_cost_and_unknown_semantics(self):
        initial = [dispatch("e1", "r1", "A"), dispatch("e2", "r2", "B"),
                   event("e3", "result", "r1", grade=0.2, usage={"input_tokens": 10}),
                   event("e4", "result", "r2", grade=0.8, usage={"output_tokens": 4})]
        late = [event("u1", "usage", "r1", usage={"output_tokens": 2}),
                event("u2", "usage", "r2", usage={"input_tokens": 20}),
                event("u3", "usage", "r1", usage={"cached_input_tokens": 5}),
                event("u4", "usage", "r2", usage={"cached_input_tokens": 0}),
                event("u5", "usage", "r1", usage={"input_tokens": 10})]
        self.assertIsNone(controller.report(replay_events(["A", "B"], initial))["usage"]["total_tokens"])
        for ordering in itertools.permutations(late):
            state = replay_events(["A", "B"], initial + list(ordering))
            report = controller.report(state)
            self.assertEqual({"known_input_tokens": 30, "known_output_tokens": 6,
                              "known_cached_input_tokens": 5, "unknown_input_tokens_requests": 0,
                              "unknown_output_tokens_requests": 0, "unknown_cached_input_tokens_requests": 0,
                              "total_tokens": 36}, report["usage"])
            self.assertEqual(0.5, report["quality"]["mean_grade"])
            self.assertEqual(2, len(report["scheduled_requests"]))

    def test_every_post_error_proposal_is_blocked_until_correct_acknowledgment(self):
        for stage in ("agent", "judge"):
            events = [dispatch("a", "agent", "A")]
            request_id = "agent"
            if stage == "judge":
                events += [event("done", "result", "agent"), dispatch("j", "judge", "A", "judge")]
                request_id = "judge"
            events += [event("outage", "provider_error", request_id)]
            state = replay_events(["A", "B"], events)
            accepted = list(state["requests"])
            self.assertTrue(state["paused"])
            for index in range(6):
                state = controller.reduce_event(state, dispatch("p%d" % index, "blocked%d" % index, "B"))
                self.assertTrue(state["paused"])
                self.assertEqual(accepted, list(state["requests"]))
            self.assertEqual(6, len(state["blocked_dispatches"]))
            state = controller.reduce_event(state, {"id": "resume", "type": "resume", "acknowledge": "outage"})
            state = controller.reduce_event(state, dispatch("allowed", "new", "B"))
            self.assertFalse(state["paused"])
            self.assertIn("new", state["requests"])

    def test_nonprovider_terminal_outcomes_cannot_be_rescheduled_as_provider_retries(self):
        for outcome in ("completed", "abandoned", "timeout", "invalid"):
            state = replay_events(["A"], [dispatch("e1", "r1", "A"),
                event("e2", "result", "r1", outcome=outcome, grade=0), dispatch("e3", "r2", "A")])
            report = controller.report(state)
            self.assertEqual([], report["provider_retry_sessions"])
            self.assertEqual(["r1"], report["scheduled_requests"])
            self.assertEqual(0.0, report["quality"]["mean_grade"])
            self.assertIs(type(report["quality"]["mean_grade"]), float)
            self.assertFalse(report["paused"])

    def test_unknown_or_rejected_requests_cannot_acquire_results_or_cost(self):
        state = replay_events(["A"], [dispatch("e1", "x", "unplanned"),
            event("e2", "provider_error", "x", usage={"input_tokens": 999}),
            event("e3", "result", "never", grade=1, usage={"output_tokens": 999})])
        report = controller.report(state)
        self.assertEqual(0, report["observed_sessions"])
        self.assertEqual(0, report["usage"]["total_tokens"])
        self.assertFalse(report["paused"])
        self.assertEqual(3, len(state["history"]))

    def test_invalid_grades_stay_pending_and_cannot_pollute_quality(self):
        for grade in (True, "0.5", -0.1, 1.1, float("nan"), float("inf")):
            state = replay_events(["A"], [dispatch("e1", "r1", "A"), event("e2", "result", "r1", grade=grade)])
            report = controller.report(state)
            self.assertEqual(0, report["graded_sessions"])
            self.assertEqual(1, report["in_flight_requests"])
            self.assertIsNone(report["quality"]["mean_grade"])

    def test_usage_cannot_replace_known_values_and_invalid_values_stay_unknown(self):
        state = replay_events(["A"], [dispatch("e1", "r1", "A"),
            event("e2", "provider_error", "r1", usage={"input_tokens": 7, "output_tokens": True}),
            event("e3", "usage", "r1", usage={"input_tokens": 100, "output_tokens": -1}),
            event("e4", "usage", "r1", usage={"cached_input_tokens": 0, "output_tokens": 2})])
        report = controller.report(state)
        self.assertEqual(7, report["usage"]["known_input_tokens"])
        self.assertEqual(9, report["usage"]["total_tokens"])
        self.assertEqual(1, report["provider_error_attempts"])
        self.assertEqual(3, len(report["ignored_events"]))

    def test_impossible_cache_subset_rejects_the_new_field_in_either_arrival_order(self):
        first = replay_events(["A"], [dispatch("e1", "r1", "A"),
            event("e2", "result", "r1", usage={"input_tokens": 3, "cached_input_tokens": 4, "output_tokens": 2})])
        self.assertIsNone(first["requests"]["r1"]["usage"]["cached_input_tokens"])
        self.assertEqual(1, controller.report(first)["usage"]["unknown_cached_input_tokens_requests"])
        self.assertEqual("cached_input_exceeds_input_tokens", first["ignored_events"][0]["reason"])
        second = replay_events(["A"], [dispatch("e1", "r1", "A"),
            event("e2", "usage", "r1", usage={"cached_input_tokens": 4}),
            event("e3", "result", "r1", usage={"input_tokens": 3, "output_tokens": 2})])
        self.assertIsNone(second["requests"]["r1"]["usage"]["input_tokens"])
        self.assertIsNone(controller.report(second)["usage"]["total_tokens"])
        self.assertEqual("input_tokens_below_cached_input", second["ignored_events"][0]["reason"])
        recovered = controller.reduce_event(second, event("e4", "usage", "r1", usage={"input_tokens": 5}))
        self.assertEqual(7, controller.report(recovered)["usage"]["total_tokens"])
        self.assertEqual(4, controller.report(recovered)["usage"]["known_cached_input_tokens"])

    def test_invalid_plan_and_missing_event_id_fail_explicitly(self):
        for sessions in (["A", "A"], [""], [None], "A"):
            with self.assertRaises(ValueError):
                controller.initial_state(sessions)
        with self.assertRaises(ValueError):
            controller.reduce_event(controller.initial_state([]), {"type": "resume"})


class ArtifactExperimentTests(unittest.TestCase):
    def test_offline_run_preserves_per_trace_artifacts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "experiment"
            # A controller regression must not quietly turn this experiment live.
            with mock.patch("subprocess.Popen", side_effect=AssertionError("no processes")), \
                    mock.patch("socket.socket", side_effect=AssertionError("no network")):
                manifest = controller.run(controller.CASES, output)
            self.assertEqual(20, manifest["passed"])
            self.assertEqual(81, manifest["events"])
            self.assertEqual(0, manifest["benchmark_model_calls"])
            self.assertEqual(0, manifest["deployments"])
            self.assertEqual(20, len(list((output / "traces").glob("*.json"))))
            for row in manifest["results"]:
                self.assertEqual(row["sha256"], controller.digest(output / row["artifact"]))
                trace = json.loads((output / row["artifact"]).read_text())
                self.assertEqual(row["event_count"] + 1, len(trace["snapshots"]))
                self.assertEqual(row["event_count"], len(trace["original_events"]))
            before = controller.digest(output / "manifest.json")
            with self.assertRaises(FileExistsError):
                controller.run(controller.CASES, output)
            self.assertEqual(before, controller.digest(output / "manifest.json"))


if __name__ == "__main__":
    unittest.main()
