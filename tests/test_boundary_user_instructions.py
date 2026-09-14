"""Synthetic offline journeys for explicit user instructions without an offer.

These tests check retained quotes and caller-supplied scope/authority structure;
they do not claim to infer consent from prose or authenticate a trusted caller.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import unittest

import test_boundary_turn as fixtures


class BoundaryUserInstructionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BoundaryTurnTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def first(self, decision="retain", **extra):
        t = self.fixture
        payload = t.first_payload(strict=True)
        del payload["proposals"]
        quote = ("  Keep A for comparison, but do not arrange a viewing.\nDo not invent a numerical exception.  "
                 if decision == "retain" else "Accept A's estimated 46-minute commute for A only.")
        payload["request"]["text"] += "\n" + quote
        payload["instructions"] = [dict(id="user-a", decision=decision, candidate_id="A",
                                        requirement_id="commute", quote=quote, **extra)]
        return payload

    def followup(self, request_id, quote, *instructions):
        return self.fixture.turn({"request": {"id": request_id, "text": quote},
                                  "instructions": [dict(row, quote=quote) for row in instructions]})

    def global_instruction(self, identifier="global-50"):
        return dict(id=identifier, decision="global", requirement_id="commute", global_check=fixtures.commute(50))

    def release_instruction(self, identifier="release-a", candidate="A", requirement="commute"):
        return dict(id=identifier, decision="release", candidate_id=candidate, requirement_id=requirement)

    def record(self, identifier="user-a"):
        return self.fixture.store.show()["proposed_checks"][identifier]

    def test_initial_cli_retain_records_actual_user_instruction_without_fabricated_offer_or_bound(self):
        t = self.fixture
        payload = self.first()
        turn_file, evidence_file = t.project / "turn.json", t.project / "evidence.json"
        turn_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        evidence_file.write_text(json.dumps(t.evidence), encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = fixtures.boundary.main(["--project", str(t.project), "reconcile", "--expected-revision", "0",
                                          "--input", str(turn_file), "--evidence", str(evidence_file)])
        self.assertEqual((0, ""), (code, stderr.getvalue()))
        result = json.loads(stdout.getvalue())
        t.revision = result["revision"]
        review = t.assert_current_exports(result)
        record = self.record()
        self.assertEqual(("user", "retain", "retained"), (record["origin"], record["decision"], record["status"]))
        self.assertEqual(payload["instructions"][0]["quote"], record["quote"])
        self.assertEqual(payload["request"]["text"], t.store.show()["requests"]["u1"]["text"])
        self.assertEqual("u1", record["provenance"]["request_id"])
        self.assertNotIn("accepted_check", record)
        self.assertNotIn("offered_evidence", record)
        self.assertNotIn("offered_source", record)
        events = json.loads((t.store.state_root / "events.json").read_text())["events"]
        operations = [entry["event"]["op"] for entry in events]
        self.assertIn("boundary.instruct", operations)
        self.assertNotIn("boundary.propose", operations)
        self.assertNotIn("boundary.decide", operations)
        self.assertEqual([], [row for row in review["proposed_checks"] if row["status"] == "pending"])
        self.assertEqual(["user-a"], review["candidates"]["A"]["consent_holds"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(45, review["confirmed_conditions"]["commute"]["value"]["value"])
        self.assertEqual([], review["candidates"]["B"]["consent_holds"])
        self.assertEqual([], review["candidates"]["B"]["exception_ids"])
        self.assertEqual(["commute"], review["candidates"]["B"]["failed_requirement_ids"])

    def test_explicit_global_50_and_consider_a_releases_only_its_hold_in_one_turn(self):
        t = self.fixture
        t.turn(self.first())
        previous = deepcopy(self.record())
        result = self.followup("u2", "Raise the overall commute limit to 50 minutes and release A's viewing hold.",
                               self.global_instruction(), self.release_instruction())
        review = t.assert_current_exports(result)
        self.assertEqual(50, review["confirmed_conditions"]["commute"]["value"]["value"])
        self.assertEqual(previous, self.record("user-a"))
        self.assertEqual("user", self.record("global-50")["origin"])
        self.assertIsNone(self.record("global-50")["candidate_id"])
        self.assertEqual("released", self.record("release-a")["status"])
        self.assertNotIn("accepted_check", self.record("release-a"))
        for candidate in "AB":
            self.assertTrue(review["candidates"][candidate]["viewing_allowed"])
            self.assertEqual([], review["candidates"][candidate]["exception_ids"])
            self.assertEqual("estimate", review["checks"]["candidates"][candidate]["checks"]["commute"]["qualifier"])
        self.assertFalse(review["candidates"]["C"]["viewing_allowed"])
        self.assertEqual(["mould"], review["candidates"]["C"]["failed_requirement_ids"])
        t.store = fixtures.session_state.SessionStore(t.project)
        self.assertTrue(t.store.verify()["ok"])
        self.assertEqual(review, t.assert_current_exports(result))

    def test_global_change_alone_preserves_existing_user_no_viewing_hold(self):
        t = self.fixture
        t.turn(self.first())
        result = self.followup("u2", "Change only the overall commute limit to 50 minutes.", self.global_instruction())
        review = t.assert_current_exports(result)
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["user-a"], review["candidates"]["A"]["consent_holds"])
        self.assertEqual("retained", self.record()["status"])
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])

    def test_releasing_hold_under_active_45_does_not_create_numeric_exception(self):
        t = self.fixture
        t.turn(self.first())
        before = deepcopy(t.store.show()["requirements"])
        result = self.followup("u2", "Release A's extra action hold, while keeping the original 45-minute condition.",
                               self.release_instruction())
        review = t.assert_current_exports(result)
        self.assertEqual(before, review["confirmed_conditions"])
        self.assertEqual([], review["candidates"]["A"]["consent_holds"])
        self.assertEqual([], review["candidates"]["A"]["exception_ids"])
        self.assertEqual(["commute"], review["candidates"]["A"]["failed_requirement_ids"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual("released", self.record("release-a")["status"])
        self.assertNotIn("accepted_check", self.record("release-a"))

    def test_release_needs_new_user_request_and_cannot_use_the_initial_retain_quote(self):
        t = self.fixture
        t.turn(self.first())
        before = t.snapshot()
        event = dict(op="boundary.instruct", id="release-with-old-quote", decision="release",
                     candidate_id="A", requirement_id="commute", provenance=self.record()["provenance"], evidence=t.evidence)
        with self.assertRaises(fixtures.session_state.SessionStateError):
            t.store.apply(event, t.revision)
        self.assertEqual(before, t.snapshot())
        self.assertEqual("retained", self.record()["status"])

    def test_other_candidate_and_other_condition_holds_are_not_released(self):
        t = self.fixture
        payload = self.first()
        quote = "Keep A and B without viewing; A also stays on hold for the unresolved quietness preference."
        payload["request"]["text"] += "\n" + quote
        payload["instructions"].extend([
            dict(id="hold-b", decision="retain", candidate_id="B", requirement_id="commute", quote=quote),
            dict(id="hold-a-quiet", decision="retain", candidate_id="A", requirement_id="quiet", quote=quote)])
        t.turn(payload)
        result = self.followup("u2", "Raise the global commute limit to 50 and release only A's commute-related hold.",
                               self.global_instruction(), self.release_instruction())
        review = t.assert_current_exports(result)
        self.assertEqual(["hold-a-quiet"], review["candidates"]["A"]["consent_holds"])
        self.assertEqual(["hold-b"], review["candidates"]["B"]["consent_holds"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertFalse(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual("prefer", review["confirmed_conditions"]["quiet"]["strength"])

    def test_direct_bounded_acceptance_applies_to_a_only_without_becoming_an_observation(self):
        t = self.fixture
        result = t.turn(self.first("candidate", accepted_check=fixtures.commute(46)))
        review = t.assert_current_exports(result)
        record = self.record()
        self.assertEqual(("user", "accepted", "candidate"), (record["origin"], record["status"], record["decision"]))
        self.assertEqual(46, record["accepted_check"]["value"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["user-a"], review["candidates"]["A"]["exception_ids"])
        self.assertFalse(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual([], review["candidates"]["B"]["exception_ids"])
        self.assertEqual(45, review["confirmed_conditions"]["commute"]["value"]["value"])
        check = review["checks"]["candidates"]["A"]["checks"]["commute"]
        self.assertEqual(("estimate", "unresolved"), (check["qualifier"], check["status"]))
        self.assertFalse(check["acceptance"]["fact_verification"])

    def test_direct_acceptance_never_covers_75_unknown_or_another_journey(self):
        t = self.fixture
        t.turn(self.first("candidate", accepted_check=fixtures.commute(46)))
        baseline = deepcopy(t.evidence)
        variants = [(75, "estimate", fixtures.JOURNEY),
                    (None, "unknown", fixtures.JOURNEY),
                    (46, "estimate", dict(fixtures.JOURNEY, destination_id="another-entrance")),
                    (46, "estimate", dict(fixtures.JOURNEY, time_window="weekend-afternoon"))]
        for value, qualifier, scope in variants:
            with self.subTest(value=value, qualifier=qualifier, scope=scope):
                t.evidence = deepcopy(baseline)
                t.observe("A", "commute_minutes", value, "minutes", qualifier=qualifier, scope=scope)
                review = fixtures.boundary.evaluate(t.store.show(), t.evidence)
                self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
                self.assertEqual([], review["candidates"]["A"]["exception_ids"])
                self.assertNotIn("viewing_permitted", {row["action"] for row in review["todos"] if row["candidate_id"] == "A"})
        self.assertEqual(46, self.record()["accepted_check"]["value"])

    def test_preferred_target_keeps_acceptance_hold_for_unsupported_basis_without_hardening_other_candidates(self):
        t = self.fixture
        payload = t.first_payload(strict=False)
        del payload["proposals"]
        commute_row = next(row for row in payload["requirements"] if row["id"] == "commute")
        preference_quote = "About 45 minutes is my preference, using observed or estimated journey evidence."
        payload["request"]["text"] = payload["request"]["text"].replace(commute_row["quote"], preference_quote)
        commute_row["quote"] = preference_quote
        consent_quote = "Accept A's estimated 46-minute commute for A only."
        payload["request"]["text"] += "\n" + consent_quote
        payload["instructions"] = [dict(id="user-a", decision="candidate", candidate_id="A", requirement_id="commute",
                                        accepted_check=fixtures.commute(46), quote=consent_quote)]
        t.turn(payload)
        for candidate in "AB":
            t.observe(candidate, "commute_minutes", 44, "minutes", qualifier="reported", scope=fixtures.JOURNEY)
        review = fixtures.boundary.evaluate(t.store.show(), t.evidence)
        self.assertEqual("prefer", review["confirmed_conditions"]["commute"]["strength"])
        for candidate in "AB":
            check = review["checks"]["candidates"][candidate]["checks"]["commute"]
            self.assertFalse(check["mandatory"])
            self.assertIs(True, check["comparison"])
            self.assertEqual(("reported", "unresolved"), (check["qualifier"], check["status"]))
            self.assertEqual([], review["candidates"][candidate]["failed_requirement_ids"])
        self.assertEqual([], review["candidates"]["A"]["exception_ids"])
        self.assertEqual(["user-a"], review["candidates"]["A"]["consent_holds"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual([], review["candidates"]["B"]["consent_holds"])
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])

    def test_external_actor_cannot_authorize_instruction_even_with_matching_captured_quote(self):
        t = self.fixture
        t.turn(self.first())
        quote = "Accept A at 46 minutes only."
        state = t.store.apply(dict(op="request.capture", id="actual-reply", text=quote, source="synthetic-user"), t.revision)
        t.revision = state["revision"]
        before = t.snapshot()
        base = dict(actor="user", authorized=True, source_id="actual-reply", request_id="actual-reply", quote=quote)
        for changes in ({"actor": "external"}, {"actor": "assistant"}, {"authorized": False},
                        {"source_id": "listing-snapshot"}, {"quote": "Accept 75 for all."}):
            with self.subTest(changes=changes):
                event = dict(op="boundary.instruct", id="forged-instruction", decision="candidate", candidate_id="A",
                             requirement_id="commute", accepted_check=fixtures.commute(46), evidence=t.evidence,
                             provenance=dict(base, **changes))
                with self.assertRaises(fixtures.session_state.SessionStateError):
                    t.store.apply(event, t.revision)
                self.assertEqual(before, t.snapshot())
                self.assertNotIn("forged-instruction", t.store.show()["proposed_checks"])

    def test_direct_user_instruction_cannot_be_recast_as_an_assistant_proposal_decision(self):
        t = self.fixture
        t.turn(self.first())
        original = deepcopy(self.record())
        quote = "Accept A at 46 minutes now."
        state = t.store.apply(dict(op="request.capture", id="reply", text=quote, source="synthetic-user"), t.revision)
        t.revision = state["revision"]
        before = t.snapshot()
        event = dict(op="boundary.decide", id="user-a", decision="candidate",
                     provenance=dict(actor="user", authorized=True, source_id="reply", request_id="reply", quote=quote))
        with self.assertRaises(fixtures.session_state.SessionStateError):
            t.store.apply(event, t.revision)
        self.assertEqual(before, t.snapshot())
        self.assertEqual(original, self.record())

    def test_invented_bounds_and_ambiguous_scope_are_rejected_atomically(self):
        t = self.fixture
        t.turn(self.first())
        before = t.snapshot()
        bad = [dict(id="bad", decision="retain", candidate_id="A", requirement_id="commute", accepted_check=fixtures.commute(46)),
               dict(id="bad", decision="release", candidate_id="A", requirement_id="commute", accepted_check=fixtures.commute(46)),
               dict(self.global_instruction("bad"), candidate_id="A"),
               dict(id="bad", decision="candidate", candidate_id="A", requirement_id="commute"),
               dict(id="bad", decision="retain", candidate_id="missing", requirement_id="commute")]
        for instruction in bad:
            with self.subTest(instruction=instruction):
                with self.assertRaises(ValueError):
                    self.followup("invalid-reply", "Keep the actual scope of this instruction.", instruction)
                self.assertEqual(before, t.snapshot())
                self.assertNotIn("invalid-reply", t.store.show()["requests"])

    def exercise_retained_predecessor_chain(self, origin, terminal_decision):
        t = self.fixture
        if origin == "user":
            t.turn(self.first())
            retained_id = "user-a"
        else:
            payload = t.first_payload(strict=True)
            payload["proposals"] = [payload["proposals"][0]]
            t.turn(payload)
            t.decision("retain-reply", "Keep A without arranging a viewing.", "retain")
            retained_id = "offer-A"
        original_retention = deepcopy(self.record(retained_id))

        def propose(identifier, bound):
            return t.turn({"request": {"id": identifier + "-request", "text": "Continue checking A while preserving my viewing instruction."},
                           "proposals": [dict(id=identifier, candidate_id="A", requirement_id="commute",
                                              accepted_check=fixtures.commute(bound),
                                              text="Would you accept A under this stated commute bound?",
                                              why="The retained source supplies A's current journey estimate.")]})

        propose("pending-one", 46)
        result = self.followup("global-only", "Change only the overall commute limit to 50 minutes.",
                               self.global_instruction())
        review = t.assert_current_exports(result)
        pending = next(row for row in review["proposed_checks"] if row["id"] == "pending-one")
        self.assertEqual("pending", pending["status"])
        self.assertFalse(pending["requirement_current"])
        self.assertIn(retained_id, review["candidates"]["A"]["consent_holds"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])
        result = propose("pending-two", 50)
        review = t.assert_current_exports(result)
        self.assertEqual("pending-one", self.record("pending-two")["supersedes"])
        self.assertIn(retained_id, review["candidates"]["A"]["consent_holds"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        instruction = dict(id="actual-new-consent", decision=terminal_decision, candidate_id="A", requirement_id="commute")
        if terminal_decision == "candidate":
            instruction["accepted_check"] = fixtures.commute(50)
            quote = "Accept A within the current 50-minute bound and proceed beyond its earlier viewing hold."
        else:
            quote = "Explicitly release A's retained viewing hold, leaving the current numeric conditions unchanged."
        result = self.followup("actual-new-reply", quote, instruction)
        review = t.assert_current_exports(result)
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual([], review["candidates"]["A"]["consent_holds"])
        self.assertEqual([], review["candidates"]["B"]["consent_holds"])
        self.assertEqual(original_retention, self.record(retained_id))
        self.assertEqual("pending-two", self.record("actual-new-consent")["supersedes"])
        if terminal_decision == "release":
            self.assertNotIn("accepted_check", self.record("actual-new-consent"))
            self.assertEqual([], review["candidates"]["A"]["exception_ids"])
        # Another unanswered offer must stop at that actual decision, rather
        # than resurrecting an older retention anywhere deeper in its history.
        propose("after-consent", 50)
        result = self.followup("global-reaffirm", "The overall commute limit remains 50 minutes.",
                               self.global_instruction("global-50-again"))
        review = t.assert_current_exports(result)
        self.assertEqual([], review["candidates"]["A"]["consent_holds"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])
        t.store = fixtures.session_state.SessionStore(t.project)
        self.assertTrue(t.store.verify()["ok"])
        self.assertEqual(review, t.assert_current_exports(result))

    def test_user_retention_survives_pending_chain_until_actual_candidate_acceptance(self):
        self.exercise_retained_predecessor_chain("user", "candidate")

    def test_offered_retention_survives_pending_chain_until_explicit_release(self):
        self.exercise_retained_predecessor_chain("assistant", "release")


if __name__ == "__main__":
    unittest.main()
