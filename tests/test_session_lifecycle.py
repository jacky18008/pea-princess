"""Real offline lifecycle storage experiments; never call a model or a provider."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("session_lifecycle_scenarios", ROOT / "evals/session_harness/run_scenarios.py")
SCENARIOS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCENARIOS)


class LifecycleExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="test-lifecycle-")
        cls.project = Path(cls.temporary.name)
        # Enforce the experiment's offline boundary, without replacing storage,
        # state transitions, integrity validation or recovery with mocks.
        with patch("subprocess.Popen", side_effect=AssertionError("process launch forbidden")), \
             patch("socket.socket", side_effect=AssertionError("network forbidden")), \
             patch("os.system", side_effect=AssertionError("shell forbidden")):
            cls.report = SCENARIOS.run_scenarios(cls.project)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_full_fixture_survives_every_fresh_store_restart(self):
        report = self.report
        self.assertTrue(report["ok"], json.dumps(report["summary"]))
        self.assertEqual(12, len(report["checkpoints"]))
        self.assertEqual(401, report["summary"]["durable_resume"]["checks"])
        for checkpoint in report["checkpoints"]:
            with self.subTest(checkpoint=checkpoint["id"]):
                self.assertEqual([], checkpoint["durable_errors"])

    def test_adversarial_cases_pass_real_rejection_and_integrity_checks(self):
        expected = {
            "stale-writer-rejected", "stale-decision-rejected", "every-active-requirement-covered",
            "conditional-pass-requires-predicate-evidence", "unknown-hard-condition-cannot-pass",
            "source-bound-quote-must-be-verbatim", "raw-document-hash-and-exact-retrieval",
            "damaged-source-snapshot-rejected", "source-supersession-invalidates-dependent-work",
            "pending-request-blocks-dispatch", "pause-persists-through-steering",
            "mid-call-steering-rejects-stale-result", "unsettled-stale-call-blocks-next-dispatch",
            "unknown-usage-is-not-zero", "overspend-prevents-followup",
            "housing-budget-cannot-become-api-credit", "small-context-fails-without-truncation",
            "restart-prefers-journal-over-stale-checkpoint",
            "task-bound-budget-cannot-be-omitted", "usage-recovery-is-idempotent",
            "paused-goal-blocks-descendant-work", "goal-needs-current-complete-dependencies",
            "blocking-question-prevents-final-receipt",
            "retired-fact-invalidates-transitive-evidence",
        }
        self.assertEqual(expected, {c["id"] for c in self.report["safety_checks"]})
        for case in self.report["safety_checks"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["passed"], case["detail"])

    def test_oracle_detects_dropped_or_wrong_conditions_independently(self):
        expected = SCENARIOS.facts_from_history(SCENARIOS._read_fixture()["records"])
        actual = copy.deepcopy(expected)
        actual["budgets.rent.limit"] = 2100
        del actual["requirements.floor.predicate"]
        actual["requirements.active_ids"] = ["area"]
        errors = SCENARIOS.differences(expected, actual)
        self.assertEqual({"budgets.rent.limit", "requirements.floor.predicate", "requirements.active_ids"},
                         {error["fact"] for error in errors})
        self.assertTrue(next(e for e in errors if e["fact"].endswith("predicate"))["missing"])
        self.assertNotEqual([], SCENARIOS.differences({"known-null": None}, {}))

    def test_lossy_proxy_is_explicit_and_not_quality_or_cost_evidence(self):
        report = self.report
        self.assertEqual(4, report["recent_records"])
        self.assertEqual(297, report["summary"]["naive_recent_records"]["errors"])
        self.assertEqual(0, report["llm_calls"])
        for name in ("model_quality", "tokens", "cost"):
            self.assertEqual("not_measured", report[name])
        text = SCENARIOS.render_markdown(report)
        for limitation in ("not measured token or cost savings", "not an implementation of Codex or Claude compaction",
                           "equivalence of final answer quality"):
            self.assertIn(limitation, text)

    def test_all_three_budget_scopes_remain_distinct(self):
        final = self.report["checkpoints"][-1]["expected_facts"]
        self.assertEqual(1650, final["budgets.rent.limit"])
        self.assertEqual(70000, final["budgets.tokens.limit"])
        self.assertEqual(3, final["budgets.spend.limit"])
        self.assertEqual("all-other-properties", final["requirements.floor-elsewhere.scope"])
        self.assertEqual("prohibit", final["requirements.floor-elsewhere.strength"])
        self.assertEqual("property-demo-only", final["requirements.floor.scope"])
        self.assertIn("step-free", final["requirements.floor.predicate"])

    def test_reports_are_explicit_local_artifacts_with_provenance(self):
        with tempfile.TemporaryDirectory(prefix="test-lifecycle-report-") as directory:
            json_path, md_path = SCENARIOS.write_report(self.report, directory)
            self.assertEqual(self.report, json.loads(json_path.read_text(encoding="utf-8")))
            self.assertTrue(md_path.read_text(encoding="utf-8").startswith("# Offline"))
        self.assertEqual(3, len(self.report["source_manifest"]))
        self.assertTrue(all(len(v) == 64 for v in self.report["source_manifest"].values()))

    def test_results_repeat_without_saved_python_state(self):
        with tempfile.TemporaryDirectory(prefix="test-lifecycle-repeat-") as directory:
            other = SCENARIOS.run_scenarios(Path(directory))
        self.assertEqual(self.report, other)

    def test_recent_record_limit_rejects_zero_and_boolean(self):
        for invalid in (0, -1, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                SCENARIOS.run_scenarios(self.project, recent_records=invalid)


if __name__ == "__main__":
    unittest.main()
