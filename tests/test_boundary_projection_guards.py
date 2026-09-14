"""Adversarial offline checks for evidence authority and retained viewing holds."""
from copy import deepcopy
import json
import unittest

import test_boundary as fixtures


class BoundaryProjectionGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BoundaryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def add_quiet_preference(self):
        t = self.fixture
        t.condition("quiet", fixtures.predicate(True, "quiet", "boolean", "eq", None,
                                                ["observed"], scope=None),
                    "I prefer quiet surroundings.", strength="prefer")
        for candidate in "AB":
            t.observe(candidate, "quiet", True, None)

    def retire_commute(self):
        t = self.fixture
        source = t.capture("Stop using a commute limit as a condition.")
        t.apply("requirement.retire", id="commute", provenance=source)
        t.resolve(source)

    def retain_then_retire(self):
        t = self.fixture
        self.add_quiet_preference()
        t.propose()
        source = t.decide("retain", quote="Keep A but do not arrange a viewing.")
        self.retire_commute()
        return source

    def test_disallowed_evidence_basis_cannot_grant_viewing_despite_true_comparison(self):
        t = self.fixture
        t.change_condition(fixtures.predicate(45, basis=["observed"]),
                           "Require an observed journey at or below 45 minutes.")
        for qualifier in ("reported", "estimate"):
            with self.subTest(qualifier=qualifier):
                t.observe("A", "commute_minutes", 44, "minutes", qualifier, fixtures.JOURNEY)
                review = t.review()
                check = t.checks(review)["commute"]
                self.assertIs(True, check["comparison"])
                self.assertEqual("unresolved", check["status"])
                self.assertEqual(qualifier, check["qualifier"])
                self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
                self.assertIn("investigate", t.actions(review, "A"))
                self.assertNotIn("viewing_permitted", t.actions(review, "A"))

    def test_allowed_estimate_within_original_bound_stays_open_but_can_permit_viewing(self):
        t = self.fixture
        t.observe("A", "commute_minutes", 44, "minutes", "estimate", fixtures.JOURNEY)
        review = t.review()
        self.assertEqual("unresolved", t.checks(review)["commute"]["status"])
        self.assertEqual("estimate", t.checks(review)["commute"]["qualifier"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual({"investigate", "viewing_permitted"}, t.actions(review, "A"))

    def test_global_update_removes_stale_label_without_changing_checks_or_erasing_history(self):
        t = self.fixture
        old_label = "Maximum commute: 45 minutes"
        t.change_condition(fixtures.predicate(45), "Keep the overall commute at 45 minutes.", label=old_label)
        for candidate in "AB":
            t.observe(candidate, "commute_minutes", 46, "minutes", "estimate", fixtures.JOURNEY)
        t.propose()
        t.decide("retain", quote="Keep A without arranging a viewing yet.")
        journal_path = t.store.state_root / "events.json"
        earlier_events = json.loads(journal_path.read_text())["events"]
        self.assertTrue(any(entry["event"].get("changes", {}).get("label") == old_label for entry in earlier_events))
        source = t.decide("global", quote="Raise the overall commute limit to 50 minutes for every candidate.",
                          global_check=fixtures.predicate(50))
        review = t.review()
        condition = review["confirmed_conditions"]["commute"]
        self.assertEqual(50, condition["value"]["value"])
        self.assertEqual(source, condition["provenance"])
        self.assertNotIn("label", condition)
        self.assertNotIn("label", t.store.context()["requirements"]["commute"])
        for candidate in "AB":
            self.assertTrue(review["candidates"][candidate]["viewing_allowed"])
            self.assertEqual([], review["candidates"][candidate]["consent_holds"])
            self.assertEqual("unresolved", t.checks(review, candidate)["commute"]["status"])
            self.assertEqual("estimate", t.checks(review, candidate)["commute"]["qualifier"])
        # Labels never participate in normalized constraint pins or consent checks.
        with_old_label = t.store.show()
        with_old_label["requirements"]["commute"]["label"] = old_label
        display_only_variant = fixtures.boundary.evaluate(with_old_label, t.evidence)
        for field in ("binding", "checks", "candidates", "ranking", "todos"):
            self.assertEqual(review[field], display_only_variant[field])
        self.assertEqual(earlier_events, json.loads(journal_path.read_text())["events"][:len(earlier_events)])
        self.assertEqual(["retain", "global"], [entry["decision"] for entry in review["proposed_checks"][0]["decision_history"]])
        restored = fixtures.session_state.SessionStore(t.project)
        self.assertTrue(restored.verify()["ok"])
        self.assertEqual(review, fixtures.boundary.evaluate(restored.show(), t.evidence))

    def test_retirement_preserves_explicit_retained_hold_and_its_history(self):
        t = self.fixture
        self.retain_then_retire()
        review = t.review()
        self.assertTrue(review["ready"])
        self.assertEqual("retired", review["confirmed_conditions"]["commute"]["status"])
        self.assertEqual("retained", review["proposed_checks"][0]["status"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["accept-a"], review["candidates"]["A"]["consent_holds"])
        self.assertIn("hold_viewing", t.actions(review, "A"))
        self.assertNotIn("viewing_permitted", t.actions(review, "A"))
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual("B", review["ranking"][0])

    def test_explicit_release_after_retirement_lifts_only_the_retained_hold(self):
        t = self.fixture
        old_source = self.retain_then_retire()
        before = deepcopy(t.store.show()["requirements"])
        t.rejected_atomically(dict(op="boundary.decide", id="accept-a", decision="release", provenance=old_source))
        source = t.decide("release", quote="Release A's viewing hold now that I removed the commute condition.")
        review = t.review()
        self.assertEqual(before, review["confirmed_conditions"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual([], review["candidates"]["A"]["consent_holds"])
        row = t.store.show()["proposed_checks"]["accept-a"]
        self.assertEqual("released", row["status"])
        self.assertEqual(source["quote"], row["quote"])
        self.assertEqual(["retain", "release"], [entry["decision"] for entry in row["decision_history"]])
        restored = fixtures.session_state.SessionStore(t.project)
        self.assertTrue(restored.verify()["ok"])
        self.assertEqual(review, fixtures.boundary.evaluate(restored.show(), t.evidence))

    def test_releasing_retired_hold_does_not_bypass_another_mandatory_failure(self):
        t = self.fixture
        self.retain_then_retire()
        t.condition("mould", fixtures.predicate(False, "mould", "boolean", "eq", None,
                                                ["observed"], scope=None),
                    "Exclude homes with mould present.", strength="prohibit")
        t.observe("A", "mould", True, None)
        t.observe("B", "mould", False, None)
        t.decide("release", quote="Release A's old commute hold; keep the mould prohibition.")
        review = t.review()
        self.assertEqual([], review["candidates"]["A"]["consent_holds"])
        self.assertEqual(["mould"], review["candidates"]["A"]["failed_requirement_ids"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertNotIn("viewing_permitted", t.actions(review, "A"))

    def test_release_cannot_replace_acceptance_while_original_condition_is_active(self):
        t = self.fixture
        t.propose()
        t.decide("retain", quote="Keep A but do not arrange a viewing.")
        source = t.capture("Release A's hold.")
        t.rejected_atomically(dict(op="boundary.decide", id="accept-a", decision="release", provenance=source))
        self.assertEqual("retained", t.store.show()["proposed_checks"]["accept-a"]["status"])

    def test_pending_tradeoff_keeps_research_todos_until_an_independent_hard_failure_exists(self):
        t = self.fixture
        self.add_quiet_preference()
        t.observe("A", "quiet", None, None, qualifier="unknown")
        t.propose()
        review = t.review()
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["commute"], review["candidates"]["A"]["failed_requirement_ids"])
        investigations = [row for row in review["todos"] if row["candidate_id"] == "A" and row["action"] == "investigate"]
        self.assertEqual(["quiet"], investigations[0]["requirement_ids"])
        self.assertIn("hold_viewing", t.actions(review, "A"))
        t.condition("mould", fixtures.predicate(False, "mould", "boolean", "eq", None,
                                                ["observed"], scope=None),
                    "Exclude homes with mould present.", strength="prohibit")
        t.observe("A", "mould", True, None)
        t.observe("B", "mould", False, None)
        review = t.review()
        self.assertEqual(["commute", "mould"], review["candidates"]["A"]["failed_requirement_ids"])
        self.assertIn("reconsider", t.actions(review, "A"))
        self.assertNotIn("investigate", t.actions(review, "A"))


if __name__ == "__main__":
    unittest.main()
