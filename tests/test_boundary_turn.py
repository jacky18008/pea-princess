"""Offline whole-turn reconciliation with the real atomic state journal.

Every message and candidate below is synthetic. No model or network is used.
"""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vet-flat/scripts"))
import boundary
import eligibility
import session_state


JOURNEY = {"kind": "journey", "destination_id": "fictional-library-entrance",
           "time_window": "weekday-arrival-09:00"}


def commute(value=45):
    return dict(field="commute_minutes", type="number", operator="lte", value=value,
                unit="minutes", basis=["observed", "estimate"], scope=deepcopy(JOURNEY))


def boolean_check(field, value):
    return dict(field=field, type="boolean", operator="eq", value=value, unit=None,
                basis=["observed"])


class BoundaryTurnTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.store = session_state.SessionStore(self.project)
        self.revision = 0
        self.evidence = dict(schema_version=eligibility.EVIDENCE_SCHEMA, sources={},
                             candidates=[dict(id=key, fields={}) for key in "ABC"])
        for candidate in "ABC":
            self.observe(candidate, "commute_minutes", 43 if candidate == "C" else 46,
                         "minutes", qualifier="estimate", scope=JOURNEY)
            self.observe(candidate, "mould", candidate == "C", None)
            self.observe(candidate, "leakage", False, None)
            self.observe(candidate, "quiet", None, None, qualifier="unknown")

    def observe(self, candidate, field, value, unit, qualifier="observed", scope=None):
        row = next(row for row in self.evidence["candidates"] if row["id"] == candidate)
        if qualifier == "unknown":
            item = dict(value=None, unit=unit, qualifier="unknown", source_id=None,
                        quote=None, reason="Bedroom noise at night has not been checked.")
        else:
            source = candidate + "-" + field
            quote = "%s %s: %s %s (%s)." % (candidate, field, value, unit, qualifier)
            self.evidence["sources"][source] = quote
            item = dict(value=value, unit=unit, qualifier=qualifier, source_id=source, quote=quote)
        if scope is not None:
            item["scope"] = deepcopy(scope)
        row["fields"][field] = item

    def first_payload(self, strict=False):
        commute_quote = ("Do not view anything above 45 minutes." if strict else
                         "About 45 minutes is my preference; ask before viewing anything above it.")
        defect_quote = "Exclude homes with mould or leakage."
        quiet_quote = "Quiet is a bonus, not a requirement."
        request = "Compare A, B and C. " + " ".join((commute_quote, defect_quote, quiet_quote))
        specifications = [("commute", commute(), "must" if strict else "prefer", commute_quote),
                          ("mould", boolean_check("mould", False), "prohibit", defect_quote),
                          ("leakage", boolean_check("leakage", False), "prohibit", defect_quote),
                          ("quiet", boolean_check("quiet", True), "prefer", quiet_quote)]
        return {"request": {"id": "u1", "text": request},
                "requirements": [dict(id=key, check=check, strength=strength,
                                      scope="all candidates", quote=quote)
                                 for key, check, strength, quote in specifications],
                "proposals": [dict(id="offer-" + candidate, candidate_id=candidate,
                                   requirement_id="commute", accepted_check=commute(46),
                                   text="Would you accept %s's estimated 46-minute commute for this candidate only?" % candidate,
                                   why="The supplied evidence records this candidate's actual journey estimate.")
                              for candidate in "AB"]}

    def turn(self, payload, **kwargs):
        result = boundary.reconcile(self.store, payload, self.evidence, self.revision, **kwargs)
        self.revision = result["revision"]
        return result

    def decision(self, request_id, text, decision, **extra):
        return self.turn({"request": {"id": request_id, "text": text},
                          "decisions": [dict(id="offer-A", decision=decision, quote=text, **extra)]})

    def snapshot(self):
        return {name: (self.store.state_root / name).read_bytes()
                for name in ("events.json", "boundary-context.json", "boundary-review.json")
                if (self.store.state_root / name).exists()}

    def assert_current_exports(self, result):
        state = self.store.show()
        context = json.loads((self.store.state_root / "boundary-context.json").read_text())
        review = json.loads((self.store.state_root / "boundary-review.json").read_text())
        self.assertEqual(result["revision"], state["revision"])
        self.assertEqual(result["context"], context)
        self.assertEqual(context, self.store.context(max_chars=64000))
        self.assertEqual(review, boundary.evaluate(state, self.evidence))
        self.assertEqual(review["binding"]["revision"], context["revision"])
        self.assertEqual(review["binding"]["event_hash"], context["event_hash"])
        self.assertEqual(review["binding"], result["comparison"]["binding"])
        self.assertTrue(review["ready"])
        self.assertEqual(review["unmapped_requirement_ids"], [])
        return review

    def test_cli_starts_an_empty_project_at_revision_zero_and_exports_one_current_view(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = boundary.main(["--project", str(self.project), "context"])
        self.assertEqual(0, code, stderr.getvalue())
        self.assertEqual(0, json.loads(stdout.getvalue())["revision"])
        turn_file, evidence_file = self.project / "turn.json", self.project / "evidence.json"
        turn_file.write_text(json.dumps(self.first_payload()))
        evidence_file.write_text(json.dumps(self.evidence))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = boundary.main(["--project", str(self.project), "reconcile", "--expected-revision", "0",
                                  "--input", str(turn_file), "--evidence", str(evidence_file)])
        self.assertEqual(0, code, stderr.getvalue())
        result = json.loads(stdout.getvalue())
        review = self.assert_current_exports(result)
        self.assertEqual(review["candidates"]["C"]["failed_requirement_ids"], ["mould"])
        self.assertNotIn("C", review["ranking"])
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertFalse(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual(set(self.store.show()["requirements"]), {"commute", "mould", "leakage", "quiet"})
        self.assertTrue(all(row["value"]["schema_version"] == boundary.COMPARISON_SCHEMA
                            for row in self.store.show()["requirements"].values()))
        self.assertFalse((self.project / "comparison-constraints.json").exists())

    def test_candidate_acceptance_survives_reopening_without_relaxing_other_candidates(self):
        self.turn(self.first_payload())
        quote = "Only A is okay at 46 minutes; leave the general limit unchanged."
        result = self.decision("u2", quote, "candidate")
        self.store = session_state.SessionStore(self.project)
        review = self.assert_current_exports(result)
        self.assertTrue(self.store.verify()["ok"])
        self.assertTrue(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(review["candidates"]["A"]["exception_ids"], ["offer-A"])
        self.assertIn("commute", review["candidates"]["A"]["open_requirement_ids"])
        self.assertFalse(review["candidates"]["B"]["viewing_allowed"])
        self.assertEqual(self.store.show()["requirements"]["commute"]["value"]["value"], 45)
        self.assertEqual(self.store.show()["proposed_checks"]["offer-A"]["quote"], quote)
        self.assertEqual(review["candidates"]["C"]["failed_requirement_ids"], ["mould"])

    def test_retained_candidate_then_explicit_global_change_recomputes_both_candidates(self):
        self.turn(self.first_payload(strict=True))
        result = self.decision("u2", "Keep A for comparison, but do not view it.", "retain")
        self.assertFalse(result["comparison"]["candidates"]["A"]["viewing_allowed"])
        result = self.decision("u3", "Change the overall commute limit to 50 minutes; A can be considered for viewing.",
                               "global", global_check=commute(50))
        review = self.assert_current_exports(result)
        for candidate in "AB":
            self.assertTrue(review["candidates"][candidate]["viewing_allowed"])
        self.assertEqual(self.store.show()["requirements"]["commute"]["value"]["value"], 50)
        history = self.store.show()["proposed_checks"]["offer-A"]["decision_history"]
        self.assertEqual([row["decision"] for row in history], ["retain", "global"])

    def test_worse_evidence_does_not_extend_a_preferred_commute_exception(self):
        self.turn(self.first_payload())
        self.decision("u2", "Only A is okay at 46 minutes.", "candidate")
        self.observe("A", "commute_minutes", 75, "minutes", qualifier="estimate", scope=JOURNEY)
        result = self.turn({"request": {"id": "u3", "text": "The new supplied estimate for A is 75 minutes. Reconsider it."}})
        review = self.assert_current_exports(result)
        self.assertFalse(review["candidates"]["A"]["viewing_allowed"])
        self.assertEqual(review["candidates"]["A"]["exception_ids"], [])
        self.assertEqual(self.store.show()["requirements"]["commute"]["value"]["value"], 45)
        self.assertEqual(self.store.show()["proposed_checks"]["offer-A"]["quote"], "Only A is okay at 46 minutes.")

    def test_malformed_and_unquoted_changes_commit_no_partial_turn(self):
        self.turn(self.first_payload())
        baseline = self.snapshot()
        changes = [
            {"request": {"id": "u2", "text": "Keep the current limit."}, "requirements": [
                dict(id="commute", check=commute(50), strength="must", scope="all candidates", quote="Raise it to 50.")]},
            {"request": {"id": "u2", "text": "Raise it to 50."}, "requirements": [
                dict(id="commute", check=commute(50), strength="must", scope="all candidates")]},
            {"request": {"id": "u2", "text": "Keep the current limit."}, "proposals": [
                dict(id="bad", text="Accept another journey?", why="Worth considering", requirement_id="commute",
                     candidate_id="missing", accepted_check=commute(46))]}]
        for payload in changes:
            with self.subTest(payload=payload):
                with self.assertRaises((session_state.SessionStateError, eligibility.EligibilityError)):
                    self.turn(payload)
                self.assertEqual(baseline, self.snapshot())
                self.assertNotIn("u2", self.store.show()["requests"])

    def test_callback_rejects_partial_mapping_without_publishing_new_request(self):
        self.turn(self.first_payload())
        quote = "I also care about daylight."
        provenance = dict(actor="user", authorized=True, request_id="legacy", source_id="legacy", quote=quote)
        state = self.store.apply_many([
            dict(op="request.capture", id="legacy", text=quote, source="user-message"),
            dict(op="requirement.add", id="daylight", value="bright rooms", strength="prefer", scope="all candidates", provenance=provenance),
            dict(op="request.resolve", id="legacy", resolution="applied", note="Preserved an as-yet unmapped preference.")], self.revision)
        self.revision = state["revision"]
        baseline = self.snapshot()
        with self.assertRaisesRegex(session_state.SessionStateError, "unmapped|pending"):
            self.turn({"request": {"id": "u2", "text": "Continue the comparison."}})
        self.assertEqual(baseline, self.snapshot())
        self.assertNotIn("u2", self.store.show()["requests"])
        partial = boundary.evaluate(self.store.show(), self.evidence)
        self.assertFalse(partial["ready"])
        self.assertEqual(partial["ranking"], [])
        self.assertEqual([row["action"] for row in partial["todos"]], ["reconcile_conditions"])

    def test_context_overflow_callback_rolls_back_the_whole_turn(self):
        self.turn(self.first_payload())
        baseline = self.snapshot()
        with self.assertRaises(session_state.ContextOverflow):
            self.turn({"request": {"id": "u2", "text": "Continue with these conditions."}}, max_chars=64)
        self.assertEqual(baseline, self.snapshot())
        self.assertNotIn("u2", self.store.show()["requests"])

    def test_first_turn_callback_failure_does_not_publish_initialization(self):
        payload = self.first_payload()
        payload.pop("proposals")
        self.evidence["candidates"][0]["fields"]["mould"]["quote"] = "This quote is not in the retained source."
        with self.assertRaises(eligibility.EligibilityError):
            self.turn(payload)
        self.assertEqual(self.snapshot(), {})
        self.assertFalse((self.store.state_root / "identity.json").exists())
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = boundary.main(["--project", str(self.project), "context"])
        self.assertEqual(0, code, stderr.getvalue())
        self.assertEqual(0, json.loads(stdout.getvalue())["revision"])

    def test_duplicate_turn_and_stale_revision_are_rejected_without_reapplying(self):
        payload = self.first_payload()
        self.turn(payload)
        baseline = self.snapshot()
        with self.assertRaises(session_state.SessionStateError):
            boundary.reconcile(self.store, payload, self.evidence, self.revision)
        with self.assertRaises(session_state.SessionStateError):
            boundary.reconcile(self.store, {"request": {"id": "u2", "text": "Continue."}}, self.evidence, self.revision - 1)
        self.assertEqual(baseline, self.snapshot())

    def test_export_failure_reports_saved_revision_and_never_replays_the_committed_turn(self):
        self.turn(self.first_payload())
        old_revision = self.revision
        payload = {"request": {"id": "u2", "text": "Continue with the existing comparison."}}
        original_write = self.store._write

        def fail_export(directory, name, value):
            if name == "boundary-context.json":
                raise OSError("synthetic export failure")
            return original_write(directory, name, value)

        with mock.patch.object(self.store, "_write", side_effect=fail_export):
            with self.assertRaisesRegex((session_state.SessionStateError, OSError), "saved.*revision|revision.*saved"):
                self.turn(payload)
        state = self.store.show()
        self.assertGreater(state["revision"], old_revision)
        self.assertEqual(state["requests"]["u2"]["status"], "resolved")
        baseline = self.snapshot()
        with self.assertRaises(session_state.SessionStateError):
            boundary.reconcile(self.store, payload, self.evidence, state["revision"])
        self.assertEqual(baseline, self.snapshot())
        self.assertTrue(boundary.evaluate(state, self.evidence)["ready"])


if __name__ == "__main__":
    unittest.main()
