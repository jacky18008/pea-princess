"""Offline acceptance journeys through the real durable state and review CLI.

All user requests, candidates and source snippets below are synthetic. These
tests exercise consent boundaries, not automatic interpretation of user prose.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vet-flat/scripts"))
import boundary
import eligibility
import session_state


JOURNEY = {"kind": "journey", "destination_id": "synthetic-library-entrance",
           "time_window": "weekday-arrival-08:30-09:00"}


def predicate(value=45, field="commute_minutes", kind="number", operator="lte",
              unit="minutes", basis=None, scope=JOURNEY):
    row = dict(field=field, type=kind, operator=operator, value=value,
               unit=unit, basis=basis or ["observed", "estimate"])
    if scope is not None:
        row["scope"] = deepcopy(scope)
    return row


def provenance(request_id, quote, **extra):
    return dict(actor="user", authorized=True, source_id="synthetic-user-message",
                request_id=request_id, quote=quote, **extra)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.store = session_state.SessionStore(self.project)
        self.state = self.store.init("synthetic-boundary-test")
        self.sequence = 0
        self.evidence = dict(schema_version=eligibility.EVIDENCE_SCHEMA,
                             sources={}, candidates=[dict(id=key, fields={}) for key in "AB"])
        self.condition("commute", predicate(), "Keep every commute at 45 minutes or less.")
        for candidate in "AB":
            self.observe(candidate, "commute_minutes", 46, "minutes", scope=JOURNEY)

    def apply(self, op, **fields):
        self.state = self.store.apply(dict(op=op, **fields), self.state["revision"])
        return self.state

    def capture(self, quote):
        self.sequence += 1
        request_id = "user-%s" % self.sequence
        self.apply("request.capture", id=request_id, text=quote, source="synthetic-user-message")
        return provenance(request_id, quote)

    def resolve(self, source, resolution="applied"):
        self.apply("request.resolve", id=source["request_id"], resolution=resolution,
                   note="The exact synthetic request was reconciled.")

    def condition(self, identifier, check, quote, strength="must", scope="all candidates"):
        source = self.capture(quote)
        self.apply("requirement.add", id=identifier,
                   value=dict(deepcopy(check), schema_version=boundary.COMPARISON_SCHEMA),
                   strength=strength, scope=scope, provenance=source)
        self.resolve(source)

    def change_condition(self, check, quote="Change the overall commute condition.", **changes):
        source = self.capture(quote)
        changes["value"] = dict(deepcopy(check), schema_version=boundary.COMPARISON_SCHEMA)
        self.apply("requirement.update", id="commute", changes=changes, provenance=source)
        self.resolve(source)

    def observe(self, candidate, field, value, unit, qualifier="observed", scope=None):
        row = next(row for row in self.evidence["candidates"] if row["id"] == candidate)
        if qualifier == "unknown":
            item = dict(value=None, unit=unit, qualifier="unknown", source_id=None,
                        quote=None, reason="No retained observation for this synthetic check.")
        else:
            source_id = "%s-%s" % (candidate, field)
            quote = "%s %s: %s %s (%s)." % (candidate, field, value, unit, qualifier)
            self.evidence["sources"][source_id] = quote
            item = dict(value=value, unit=unit, qualifier=qualifier, source_id=source_id, quote=quote)
        if scope is not None:
            item["scope"] = deepcopy(scope)
        row["fields"][field] = item

    def proposal_event(self, identifier="accept-a", candidate="A", check=None):
        return dict(op="boundary.propose", id=identifier,
                    text="A takes 46 minutes against the stated 45-minute limit.",
                    why="Ask whether this recorded trade-off is acceptable for this candidate.",
                    requirement_id="commute", candidate_id=candidate,
                    accepted_check=deepcopy(check or predicate(46)), evidence=deepcopy(self.evidence))

    def propose(self, identifier="accept-a", candidate="A", check=None):
        event = self.proposal_event(identifier, candidate, check)
        return self.apply(event.pop("op"), **event)

    def decide(self, decision="candidate", identifier="accept-a", quote=None, **extra):
        quote = quote or "Accept 46 minutes for A only; keep the overall limit at 45."
        source = self.capture(quote)
        self.apply("boundary.decide", id=identifier, decision=decision, provenance=source, **extra)
        self.resolve(source)
        return source

    def review(self):
        return boundary.evaluate(self.store.show(), self.evidence)

    def checks(self, review, candidate="A"):
        return review["checks"]["candidates"][candidate]["checks"]

    def actions(self, review, candidate):
        return {row["action"] for row in review["todos"] if row["candidate_id"] == candidate}

    def rejected_atomically(self, event):
        before = self.store.show()
        journal = (self.store.state_root / "events.json").read_bytes()
        with self.assertRaises(ValueError):
            self.store.apply(event, before["revision"])
        self.assertEqual(before, self.store.show())
        self.assertEqual(journal, (self.store.state_root / "events.json").read_bytes())

    def cli(self, command, evidence=None, review=None, payload=None, revision=None):
        args = ["--project", str(self.project), command]
        for flag, value in (("evidence", evidence), ("review", review), ("input", payload)):
            if value is not None:
                path = self.project / (flag + ".json")
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                args.extend(["--" + flag, str(path)])
        if revision is not None:
            args.extend(["--expected-revision", str(revision)])
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = boundary.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_superseded_retained_proposal_cannot_override_newer_decision(self):
        self.propose("old-a")
        self.decide("retain", "old-a", "Keep A without viewing for now.")
        self.propose("new-a")
        self.decide("candidate", "new-a", "Now accept A's 46 minutes for this candidate.")
        for decision in ("decline", "retain", "candidate", "global"):
            with self.subTest(decision=decision):
                source = self.capture("Change the older proposal decision explicitly.")
                event = dict(op="boundary.decide", id="old-a", decision=decision,
                             provenance=source)
                if decision == "global":
                    event["global_check"] = predicate(50)
                self.rejected_atomically(event)
                self.assertEqual("retained", self.store.show()["proposed_checks"]["old-a"]["status"])
                self.assertEqual("accepted", self.store.show()["proposed_checks"]["new-a"]["status"])
                self.assertEqual("pending", self.store.show()["requests"][source["request_id"]]["status"])
                # The invalid operation cannot silently discard the newest user request.
                self.assertFalse(self.review()["ready"])
                self.assertFalse(self.review()["candidates"]["A"]["viewing_allowed"])
                self.resolve(source, "no_change")

    def test_superseding_one_candidate_does_not_supersede_another(self):
        self.propose("old-a")
        self.propose("offer-b", "B")
        self.decide("retain", "old-a", "Keep A without viewing.")
        self.propose("new-a")
        self.decide("candidate", "offer-b", "Accept only B at 46 minutes.")
        review = self.review()
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["offer-b"], review["candidates"]["B"]["exception_ids"])

    def test_pending_tradeoff_does_not_change_confirmed_condition_or_allow_viewing(self):
        before = deepcopy(self.state["requirements"])
        self.propose()
        review = self.review()
        self.assertEqual(before, review["confirmed_conditions"])
        self.assertEqual("pending", review["proposed_checks"][0]["status"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["accept-a"], review["candidates"]["A"]["consent_holds"])
        self.assertNotIn("A", review["ranking"])
        self.assertNotIn("viewing_permitted", self.actions(review, "A"))

    def test_missing_comparison_marker_cannot_validate_a_ranked_candidate_with_mould(self):
        self.observe("A", "commute_minutes", 44, "minutes", scope=JOURNEY)
        self.observe("A", "mould", True, None)
        source = self.capture("Do not consider a home with mould.")
        self.apply("requirement.add", id="no-mould", strength="prohibit", scope="all candidates",
                   value=predicate(False, "mould", "boolean", "eq", None, scope=None), provenance=source)
        self.resolve(source)
        review = self.review()
        self.assertEqual(["no-mould"], review["unmapped_requirement_ids"])
        self.assertFalse(review["ready"])
        self.assertEqual([], review["ranking"])
        self.assertEqual(["reconcile_conditions"], [row["action"] for row in review["todos"]])
        self.assertEqual(2, self.cli("validate", evidence=self.evidence, review=review)[0])

    def test_accepting_46_for_a_keeps_45_global_and_does_not_accept_b(self):
        before = deepcopy(self.state["requirements"])
        self.propose()
        source = self.decide()
        review = self.review()
        self.assertEqual(before, review["confirmed_conditions"])
        self.assertEqual(["A"], review["ranking"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertFalse(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual(["commute"], review["candidates"]["B"]["failed_requirement_ids"])
        self.assertEqual(["accept-a"], review["candidates"]["A"]["exception_ids"])
        self.assertEqual([], review["candidates"]["B"]["exception_ids"])
        self.assertIn("viewing_permitted", self.actions(review, "A"))
        self.assertIn("reconsider", self.actions(review, "B"))
        self.assertEqual("failed", self.checks(review)["commute"]["original_status"])
        self.assertEqual(source["quote"], review["proposed_checks"][0]["quote"])

    def test_new_75_unknown_or_different_journey_cannot_reuse_acceptance(self):
        self.propose()
        self.decide()
        baseline = deepcopy(self.evidence)
        changes = [(75, "observed", JOURNEY), (None, "unknown", JOURNEY),
                   (46, "observed", dict(JOURNEY, destination_id="different-entrance")),
                   (46, "observed", dict(JOURNEY, time_window="weekend-afternoon"))]
        for value, qualifier, scope in changes:
            with self.subTest(value=value, qualifier=qualifier, scope=scope):
                self.evidence = deepcopy(baseline)
                self.observe("A", "commute_minutes", value, "minutes", qualifier, scope)
                review = self.review()
                self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
                self.assertEqual([], review["candidates"]["A"]["exception_ids"])
                self.assertNotIn("viewing_permitted", self.actions(review, "A"))
        self.evidence = baseline
        self.assertTrue(self.review()["candidates"]["A"]["viewing_allowed"])

    def test_accepted_estimate_stays_unconfirmed_and_keeps_investigation_todo(self):
        self.observe("A", "commute_minutes", 46, "minutes", "estimate", JOURNEY)
        self.propose()
        self.decide()
        review = self.review()
        check = self.checks(review)["commute"]
        self.assertEqual("estimate", check["qualifier"])
        self.assertEqual("unresolved", check["status"])
        self.assertFalse(check["acceptance"]["fact_verification"])
        self.assertEqual("needs_evidence", review["candidates"]["A"]["status"])
        self.assertIn("commute", review["candidates"]["A"]["open_requirement_ids"])
        self.assertIn("investigate", self.actions(review, "A"))
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])

    def test_refusal_and_retain_preserve_user_decision_and_prevent_viewing(self):
        self.propose()
        self.propose("accept-b", "B")
        self.decide("decline", quote="No, do not proceed with A on that trade-off.")
        self.decide("retain", "accept-b", "Keep B on the list but do not arrange a viewing.")
        review = self.review()
        self.assertEqual([], review["ranking"])
        for candidate in "AB":
            self.assertFalse(review["candidates"][candidate]["viewing_allowed"])
            self.assertIn("hold_viewing", self.actions(review, candidate))
        self.assertEqual({"declined", "retained"}, {row["status"] for row in review["proposed_checks"]})
        self.assertEqual(45, review["confirmed_conditions"]["commute"]["value"]["value"])

    def test_retain_remains_action_hold_even_when_new_evidence_meets_45(self):
        self.propose()
        self.decide("retain", quote="Keep A for later; do not arrange a viewing.")
        self.observe("A", "commute_minutes", 44, "minutes", scope=JOURNEY)
        review = self.review()
        self.assertEqual("met", self.checks(review)["commute"]["status"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertIn("hold_viewing", self.actions(review, "A"))

    def test_explicit_global_50_updates_single_stored_condition_and_rechecks_both(self):
        self.propose()
        source = self.decide("global", quote="Change my overall commute limit to 50 minutes for all candidates.",
                             global_check=predicate(50))
        review = self.review()
        condition = review["confirmed_conditions"]["commute"]
        self.assertEqual(50, condition["value"]["value"])
        self.assertEqual(source, condition["provenance"])
        self.assertEqual(["A", "B"], review["ranking"])
        for candidate in "AB":
            self.assertTrue(review["candidates"][candidate]["viewing_allowed"])
            self.assertEqual([], review["candidates"][candidate]["exception_ids"])
            self.assertEqual("met", self.checks(review, candidate)["commute"]["status"])

    def test_commute_consent_never_waives_mould_prohibition_or_hardens_quiet_preference(self):
        self.condition("mould", predicate(False, "mould_present", "boolean", "eq", None,
                                          ["observed"], scope=None),
                       "Exclude candidates with mould present.", strength="prohibit")
        self.condition("quiet", predicate(True, "quiet", "boolean", "eq", None,
                                          ["observed"], scope=None),
                       "I prefer quiet surroundings, but it is not a hard condition.", strength="prefer")
        for candidate in "AB":
            self.observe(candidate, "mould_present", candidate == "A", None)
            self.observe(candidate, "quiet", False, None)
        self.propose()
        self.decide()
        review = self.review()
        self.assertEqual(["mould"], review["candidates"]["A"]["failed_requirement_ids"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertFalse(self.checks(review)["quiet"]["mandatory"])
        self.assertEqual(["quiet"], review["checks"]["candidates"]["A"]["advisory_failed_requirement_ids"])
        self.observe("A", "mould_present", False, None)
        review = self.review()
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual("prefer", review["confirmed_conditions"]["quiet"]["strength"])

    def test_exact_quote_survives_checkpoint_and_fresh_store_without_chat_history(self):
        self.propose()
        quote = "  For A only, 46 minutes is acceptable.\nKeep 45 minutes for every other candidate.  "
        source = self.decide(quote=quote)
        expected = self.review()
        self.store.checkpoint()
        restored = session_state.SessionStore(self.project)
        self.assertTrue(restored.verify()["ok"])
        self.assertEqual(expected, boundary.evaluate(restored.show(), self.evidence))
        self.assertEqual(quote, restored.context()["proposed_checks"]["accept-a"]["quote"])
        self.assertEqual(quote, restored.show()["requests"][source["request_id"]]["text"])

    def test_decision_requires_exact_authorized_reply_captured_after_proposal(self):
        early = self.capture("Accept A only.")
        self.resolve(early, "no_change")
        self.propose()
        exact = self.capture("  Accept 46 for A only.  ")
        attempts = [early, dict(exact, quote="Accept 50 for all candidates."),
                    dict(exact, actor="external"), dict(exact, actor="assistant"),
                    dict(exact, authorized=False),
                    {key: value for key, value in exact.items() if key != "request_id"}]
        for source in attempts:
            with self.subTest(source=source):
                self.rejected_atomically(dict(op="boundary.decide", id="accept-a", decision="candidate",
                                             provenance=source))

    def test_pending_new_user_request_prevents_current_permission_until_reconciled(self):
        self.propose()
        self.decide()
        self.assertTrue(self.review()["candidates"]["A"]["viewing_allowed"])
        source = self.capture("Wait, I need to revisit the current conditions.")
        review = self.review()
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertNotIn("viewing_permitted", self.actions(review, "A"))
        self.resolve(source, "no_change")
        self.assertTrue(self.review()["candidates"]["A"]["viewing_allowed"])

    def test_reopening_declined_proposal_preserves_history_and_requires_new_reply(self):
        self.propose()
        old_source = self.decide("decline", quote="Decline the extra minute for A.")
        old = deepcopy(self.state["proposed_checks"]["accept-a"])
        self.propose("reconsider-a")
        self.rejected_atomically(dict(op="boundary.decide", id="reconsider-a", decision="candidate",
                                     provenance=old_source))
        self.decide(identifier="reconsider-a", quote="I reconsidered: allow 46 minutes for A only.")
        review = self.review()
        self.assertEqual(old, self.store.show()["proposed_checks"]["accept-a"])
        self.assertEqual("accept-a", self.state["proposed_checks"]["reconsider-a"]["supersedes"])
        self.assertEqual(["reconsider-a"], review["candidates"]["A"]["exception_ids"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])

    def test_retained_decision_needs_later_reply_and_records_both_choices(self):
        self.propose()
        source = self.decide("retain", quote="Keep A but do not proceed yet.")
        self.rejected_atomically(dict(op="boundary.decide", id="accept-a", decision="candidate", provenance=source))
        self.decide(quote="Now accept the 46-minute trip for A only.")
        history = self.store.show()["proposed_checks"]["accept-a"]["decision_history"]
        self.assertEqual(["retain", "candidate"], [row["decision"] for row in history])
        self.assertTrue(self.review()["candidates"]["A"]["viewing_allowed"])

    def test_generic_condition_change_invalidates_old_candidate_acceptance(self):
        self.propose()
        self.decide()
        self.change_condition(predicate(40), "Tighten the global commute condition to 40 minutes.")
        review = self.review()
        self.assertFalse(review["proposed_checks"][0]["requirement_current"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual([], review["candidates"]["A"]["exception_ids"])
        self.assertNotIn("A", review["ranking"])

    def test_generic_relaxation_does_not_erase_retained_no_viewing_choice(self):
        self.propose()
        self.decide("retain", quote="Keep A, but no viewing.")
        self.change_condition(predicate(50), "The general commute limit can be 50 now.")
        review = self.review()
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertTrue(review["candidates"]["B"]["viewing_allowed"])
        self.assertIn("hold_viewing", self.actions(review, "A"))
        self.assertEqual("B", review["ranking"][0])

    def test_changed_condition_requires_fresh_proposal_before_old_pending_decision(self):
        self.propose()
        self.change_condition(predicate(44), "Use 44 minutes as the current global limit.")
        source = self.capture("Accept A at 46 minutes only.")
        self.rejected_atomically(dict(op="boundary.decide", id="accept-a", decision="candidate", provenance=source))
        self.resolve(source, "no_change")
        old = deepcopy(self.state["proposed_checks"]["accept-a"])
        self.propose("fresh-a")
        self.decide(identifier="fresh-a", quote="Accept A at 46 against the new 44-minute condition.")
        review = self.review()
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(["fresh-a"], review["candidates"]["A"]["exception_ids"])
        self.assertEqual(old, self.store.show()["proposed_checks"]["accept-a"])

    def test_unmapped_free_text_and_natural_scope_prevent_automatic_viewing(self):
        self.propose()
        self.decide()
        source = self.capture("The entrance and bedroom must suit my accessibility needs.")
        self.apply("requirement.add", id="access", value="Accessible entrance and bedroom",
                   strength="must", scope="all candidates", provenance=source)
        self.resolve(source)
        self.condition("area", predicate(45, "area_m2", "number", "gte", "m2", scope=None),
                       "Only compare the advertised room area for A.", scope="candidate A")
        review = self.review()
        self.assertEqual({"access", "area"}, set(review["unmapped_requirement_ids"]))
        self.assertEqual({"access", "area", "commute"}, set(review["confirmed_conditions"]))
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertNotIn("viewing_permitted", self.actions(review, "A"))

    def test_proposals_cannot_overwrite_records_or_use_unadopted_generic_api(self):
        self.propose()
        self.rejected_atomically(self.proposal_event())
        self.rejected_atomically(dict(op="proposal.add", id="generic", text="Check bedroom direction",
                                     why="Optional preference check", proposed_at="2026-09-14T10:00:00Z"))
        source = self.capture("Yes to the candidate-specific trade-off only.")
        self.rejected_atomically(dict(op="proposal.decide", id="accept-a", status="accepted",
                                     decided_at="2026-09-14T10:01:00Z", provenance=source,
                                     requirement=dict(id="invented", value=True, strength="must", scope="all candidates")))
        self.rejected_atomically(dict(op="boundary.decide", id="missing", decision="candidate", provenance=source))
        self.assertNotIn("invented", self.store.show()["requirements"])

    def test_proposal_scope_cannot_turn_explicit_unknown_into_unscoped_permission(self):
        check = predicate(45, "area_m2", "number", "gte", "m2", scope=None)
        check["scope"] = None
        self.condition("area", check, "Use at least 45 square metres once its applicability is known.")
        self.observe("A", "area_m2", 46, "m2")
        event = self.proposal_event(check=predicate(45, "area_m2", "number", "gte", "m2", scope=None))
        event["requirement_id"] = "area"
        self.rejected_atomically(event)

    def test_malformed_proposals_are_atomic_and_cannot_broaden_authority(self):
        base = self.proposal_event()
        edits = [{"status": "accepted"}, {"candidate_id": "missing"}, {"requirement_id": "missing"},
                 {"text": " "}, {"why": None}, {"evidence": {}},
                 {"accepted_check": dict(predicate(46), value=True)},
                 {"accepted_check": dict(predicate(46), unit="hours")},
                 {"accepted_check": dict(predicate(46), field="rent")},
                 {"accepted_check": dict(predicate(46), scope=dict(JOURNEY, destination_id="elsewhere"))},
                 {"accepted_check": dict(predicate(46), basis=["observed", "estimate", "reported"])},
                 {"accepted_check": predicate(45)}]
        for changes in edits:
            with self.subTest(changes=changes):
                self.rejected_atomically(dict(deepcopy(base), **changes))
        self.propose()
        self.rejected_atomically(self.proposal_event("second-pending"))

    def test_malformed_decisions_are_atomic_and_do_not_smuggle_global_changes(self):
        self.propose()
        source = self.capture("Accept 46 minutes for A only.")
        base = dict(op="boundary.decide", id="accept-a", decision="candidate", provenance=source)
        for changes in ({"decision": "accept-all"}, {"global_check": predicate(75)},
                        {"decision": "global"}, {"quote": source["quote"]},
                        {"decision": "global", "global_check": dict(predicate(50), basis=["reported"])}):
            with self.subTest(changes=changes):
                self.rejected_atomically(dict(deepcopy(base), **changes))

    def test_cli_review_is_current_and_rejects_altered_projection_or_source(self):
        self.propose()
        self.decide()
        code, stdout, stderr = self.cli("evaluate", evidence=self.evidence)
        self.assertEqual((0, ""), (code, stderr))
        original = json.loads(stdout)
        self.assertEqual(self.review(), original)
        self.assertEqual(0, self.cli("validate", evidence=self.evidence, review=original)[0])
        variants = []
        changed = deepcopy(original); changed["candidates"]["B"]["viewing_allowed"] = True; variants.append(changed)
        changed = deepcopy(original); changed["candidates"]["A"]["viewing_allowed"] = 1; variants.append(changed)
        changed = deepcopy(original); changed["ranking"] = ["B", "A"]; variants.append(changed)
        changed = deepcopy(original); changed["todos"] = []; variants.append(changed)
        changed = deepcopy(original); changed["confirmed_conditions"]["commute"]["value"]["value"] = 75; variants.append(changed)
        for changed in variants:
            code, stdout, stderr = self.cli("validate", evidence=self.evidence, review=changed)
            self.assertEqual((2, ""), (code, stdout))
            self.assertIn("error", json.loads(stderr))
        self.observe("A", "commute_minutes", 75, "minutes", scope=JOURNEY)
        self.assertEqual(2, self.cli("validate", evidence=self.evidence, review=original)[0])

    def test_cli_rejects_stale_state_revision_and_preserves_journal_on_stale_write(self):
        payload = self.proposal_event()
        del payload["op"]
        stale = self.state["revision"]
        source = self.capture("Explain the proposed trade-off first.")
        before = (self.store.state_root / "events.json").read_bytes()
        code, stdout, stderr = self.cli("propose", payload=payload, revision=stale)
        self.assertEqual((2, ""), (code, stdout))
        self.assertIn("error", json.loads(stderr))
        self.assertEqual(before, (self.store.state_root / "events.json").read_bytes())
        self.resolve(source, "no_change")
        self.propose()
        self.decide()
        old = self.review()
        self.apply("question.add", id="later-question", text="An unrelated optional detail", blocking=False)
        self.assertEqual(2, self.cli("validate", evidence=self.evidence, review=old)[0])

    def test_cli_handles_nonobject_evidence_and_invalid_candidate_rows_without_traceback(self):
        for evidence in ([], {"candidates": [None]}, {"candidates": ["A"]}):
            with self.subTest(evidence=evidence):
                code, stdout, stderr = self.cli("evaluate", evidence=evidence)
                self.assertEqual((2, ""), (code, stdout))
                self.assertIn("error", json.loads(stderr))


if __name__ == "__main__":
    unittest.main()
