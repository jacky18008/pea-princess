"""Offline saved-claim acceptance against the actual private journal and export."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/vet-flat/scripts"
sys.path.insert(0, str(SCRIPTS))
import boundary
import eligibility
import save_gate
import session_state


class SaveGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.store = session_state.SessionStore(self.project)
        self.evidence = {"schema_version": eligibility.EVIDENCE_SCHEMA, "sources": {}, "candidates": []}
        for key, rent, bedrooms in (("A", 2450, 2), ("B", 2100, 1)):
            fields = {}
            for field, amount, unit in (("rent_gbp_month", rent, "GBP/month"),
                                        ("bedrooms", bedrooms, "bedrooms")):
                source = key + "-" + field
                quote = "%s advertised %s is %s %s." % (key, field, amount, unit)
                self.evidence["sources"][source] = quote
                fields[field] = {"value": amount, "unit": unit, "qualifier": "reported",
                                 "source_id": source, "quote": quote}
            fields["quiet"] = {"value": None, "unit": None, "qualifier": "unknown",
                               "source_id": None, "quote": None,
                               "reason": "Bedroom noise has not been measured."}
            self.evidence["candidates"].append({"id": key, "fields": fields})
        self.evidence_path = self.project / "evidence.json"
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")

    def payload(self):
        raw = ("My monthly rent ceiling is GBP 2500. I need at least one bedroom. "
               "Quiet is a preference. Compare A and B and save the comparison and next steps.")
        return {"request": {"id": "u1", "text": raw}, "requirements": [
            {"id": "rent", "strength": "must", "scope": "all candidates",
             "quote": "My monthly rent ceiling is GBP 2500.",
             "check": {"field": "rent_gbp_month", "type": "number", "operator": "lte",
                       "value": 2500, "unit": "GBP/month", "basis": ["reported"]}},
            {"id": "bedrooms", "strength": "must", "scope": "all candidates",
             "quote": "I need at least one bedroom.",
             "check": {"field": "bedrooms", "type": "number", "operator": "gte",
                       "value": 1, "unit": "bedrooms", "basis": ["reported"]}},
            {"id": "quiet", "strength": "prefer", "scope": "all candidates",
             "quote": "Quiet is a preference.",
             "check": {"field": "quiet", "type": "boolean", "operator": "eq",
                       "value": True, "unit": None, "basis": ["observed"]}},
        ]}

    def reconcile(self):
        return boundary.reconcile(self.store, self.payload(), self.evidence,
                                  self.store.show()["revision"] if (self.project / ".pea-state/events.json").exists() else 0)

    def register_fidelity(self, tool_records=None, journeys=None):
        tool_records = tool_records or {}
        current = self.store.init("synthetic-save-gate")
        bindings = {}
        for source_id, text in self.evidence["sources"].items():
            if source_id in tool_records:
                path = self.project / (source_id + ".json")
                path.write_text(json.dumps(tool_records[source_id], ensure_ascii=False, indent=2), encoding="utf-8")
                actor, quote, kind = "tool", text, "tool_record"
            else:
                path = self.project / (source_id + ".txt")
                path.write_text(text + "\n", encoding="utf-8")
                actor, quote, kind = "user", text, "user_extract"
            current = self.store.apply({"op": "document.add", "id": "doc-" + source_id,
                "path": path.name, "provenance": {"actor": actor, "source_id": source_id,
                                                  "quote": quote}}, current["revision"])
            bindings[source_id] = {"document_id": "doc-" + source_id,
                                   "sha256": current["documents"]["doc-" + source_id]["sha256"],
                                   "kind": kind}
        pending = {}
        for candidate in self.evidence["candidates"]:
            key = candidate["id"]
            pending[key] = {
                "rent_gbp_month": {"action": "verify_source", "needed": "Verify the advertised monthly rent against the saved extract.",
                                   "requirement_ids": ["rent"]},
                "bedrooms": {"action": "verify_source", "needed": "Confirm the bedroom count in the saved property extract.",
                             "requirement_ids": ["bedrooms"]},
                "quiet": {"action": "inspect_property", "needed": "Check bedroom quietness at night during a permitted inspection.",
                          "requirement_ids": ["quiet"]}}
        manifest = {"schema_version": save_gate.FIDELITY_SCHEMA,
                    "evidence_sha256": eligibility.canonical_hash(self.evidence),
                    "sources": bindings, "journeys": journeys or {}, "pending_checks": pending}
        path = self.project / "fidelity.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        current = self.store.apply({"op": "document.add", "id": "comparison-fidelity",
            "path": path.name, "provenance": {"actor": "assistant", "source_id": "local-fidelity",
                                              "quote": save_gate.FIDELITY_SCHEMA}}, current["revision"])
        return current

    def register_report(self, *, complete=False):
        self.reconcile()
        current = self.store.show()
        def apply(event):
            nonlocal current
            current = self.store.apply(event, expected_revision=current["revision"])

        apply({"op": "task.add", "id": "compare-a-b", "title": "Check saved comparison report",
               "acceptance": ["Saved report preserves its quoted source and uncertainties."]})
        report = "A advertises GBP 2450/month; B advertises GBP 2100/month. Bedroom quiet is unknown."
        path = self.project / "report.md"
        path.write_text(report + "\n", encoding="utf-8")
        apply({"op": "document.add", "id": "report-doc", "path": "report.md", "line_ranges": [[1, 1]],
               "provenance": {"actor": "assistant", "source_id": "local-report", "quote": report}})
        apply({"op": "output.record", "id": "report-a-b", "task_id": "compare-a-b",
               "document_id": "report-doc", "decision_ids": [],
               "based_on_revision": current["revision"]})
        if complete:
            apply({"op": "task.complete", "id": "compare-a-b", "evidence_ids": ["report-doc"],
                   "based_on_revision": current["revision"]})
        return current, path

    def cli(self, *extra):
        result = subprocess.run([sys.executable, str(SCRIPTS / "save_gate.py"),
                                 "--project", str(self.project), *extra, "--json"],
                                text=True, capture_output=True, timeout=10)
        return result.returncode, json.loads(result.stdout)

    def test_fresh_fidelity_bound_comparison_save_has_current_journal_and_receipt(self):
        self.register_fidelity()
        reconciled = self.reconcile()
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path),
                                 "--fidelity-document-id", "comparison-fidelity")
        self.assertEqual(code, 0, receipt)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["revision"], reconciled["revision"])
        self.assertEqual(receipt["event_hash"], reconciled["comparison"]["binding"]["event_hash"])
        self.assertEqual(receipt["evidence_sha256"], eligibility.canonical_hash(self.evidence))
        self.assertTrue((self.project / ".pea-state/events.json").is_file())
        self.assertTrue((self.project / ".pea-state/boundary-review.json").is_file())
        self.assertTrue((self.project / ".pea-state/boundary-context.json").is_file())
        self.assertEqual(set(self.store.show()["requirements"]), {"rent", "bedrooms", "quiet"})
        self.assertEqual(set(receipt["source_sha256"]), set(self.evidence["sources"]))

    def test_old_revision_only_receipt_cannot_claim_full_comparison_save(self):
        self.reconcile()
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 0, receipt)
        self.assertNotIn("source_sha256", receipt)
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.assertIn("fidelity-document-id", receipt["message"])

    def test_raw_tfl_alternatives_and_official_status_are_bound(self):
        scope = {"kind": "journey", "destination_id": "test-stop", "time_window": "weekday-arrival-09:00"}
        url = "https://api.tfl.gov.uk/Journey/JourneyResults/SE10%201AA/to/1000139?date=20260917&time=0900&timeIs=Arriving"
        def plan(mode, minutes, arrival):
            return {"source_url": url + ("&mode=" + mode if mode else ""),
                    "http_status": 200, "ok": True, "note": "", "retrieved_at": "2026-09-16T10:00:00Z",
                    "evidence_class": "G", "duration_min": minutes,
                    "start": "2026-09-17T08:00:00", "arrival": arrival,
                    "alternatives_min": [minutes, minutes + 4], "journeys_returned": 2}
        raw = {"source_url": url, "http_status": 200, "ok": True,
               "retrieved_at": "2026-09-16T10:00:00Z", "evidence_class": "G",
               "query": {"from": "SE10 1AA", "to": "1000139", "date": "20260917",
                         "arrive_by": "09:00", "door_buffer_min": 0,
                         "plans": ["all", "rail", "bus"]},
               "plans": {"all": plan(None, 28, "2026-09-17T08:58:00"),
                         "rail": plan("tube", 30, "2026-09-17T08:36:00"),
                         "bus": plan("bus", 63, "2026-09-17T08:57:00")},
               "fastest_plan": "all", "fastest_min": 28}
        source_text = '"fastest_min": 28'
        self.evidence["sources"]["tfl-b"] = source_text
        b = self.evidence["candidates"][1]["fields"]
        b["commute_minutes"] = {"value": 28, "unit": "minutes", "qualifier": "estimate",
                                "source_id": "tfl-b", "quote": source_text, "scope": scope}
        b["arrives_by_0900"] = {"value": True, "unit": None, "qualifier": "estimate",
                                "source_id": "tfl-b", "quote": source_text, "scope": scope}
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")
        journeys = {"B": {"source_id": "tfl-b", "query": raw["query"],
                          "plans": {mode: save_gate._plan_summary(raw["plans"][mode])
                                    for mode in ("all", "rail", "bus")}}}
        self.register_fidelity({"tfl-b": raw}, journeys)
        self.reconcile()
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path),
                                 "--fidelity-document-id", "comparison-fidelity")
        self.assertEqual(code, 0, receipt)
        self.assertIn("B", journeys)
        self.assertEqual(journeys["B"]["plans"]["rail"]["arrival"], "2026-09-17T08:36:00")
        self.assertIn("tfl-b", receipt["source_sha256"])

    def test_incomplete_tfl_manifest_fails_even_with_raw_source_document(self):
        raw = {"query": {"plans": ["all", "rail", "bus"], "date": "20260917",
                         "arrive_by": "09:00", "door_buffer_min": 0},
               "plans": {"all": {}, "rail": {}, "bus": {}}}
        with self.assertRaisesRegex(session_state.SessionStateError, "saved journey alternatives"):
            save_gate._check_journey(raw, {"source_id": "tfl-b", "query": raw["query"],
                                          "plans": {"all": save_gate._plan_summary({})}}, "B", "tfl-b")

    def test_informal_snapshot_cannot_claim_durable_comparison(self):
        snapshot = self.project / "state/comparison.json"
        snapshot.parent.mkdir()
        snapshot.write_text('{"A":"can consider", "B":"research"}', encoding="utf-8")
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        self.assertFalse((self.project / ".pea-state/events.json").exists())

    def test_evidence_drift_and_new_unreconciled_turn_invalidate_prior_export(self):
        self.register_fidelity()
        self.reconcile()
        changed = copy.deepcopy(self.evidence)
        changed["candidates"][1]["fields"]["rent_gbp_month"]["value"] = 2200
        changed["candidates"][1]["fields"]["rent_gbp_month"]["quote"] = "B now advertises GBP 2200/month."
        changed["sources"]["B-rent_gbp_month"] = "B now advertises GBP 2200/month."
        self.evidence_path.write_text(json.dumps(changed), encoding="utf-8")
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path),
                                 "--fidelity-document-id", "comparison-fidelity")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])

        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")
        current = self.store.show()
        self.store.apply({"op": "request.capture", "id": "u2", "source": "user-message",
                          "text": "Lower rent limit to GBP 2200."}, expected_revision=current["revision"])
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path),
                                 "--fidelity-document-id", "comparison-fidelity")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])

    def test_comparison_scope_does_not_claim_registered_report(self):
        self.register_fidelity()
        self.reconcile()
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        self.assertEqual(save_gate.check(self.project, "comparison-full", evidence=self.evidence,
                                         fidelity_document_id="comparison-fidelity")["scope"],
                         "comparison-full")

    def test_frozen_t2_snapshot_rejected_without_registered_sources_and_todos(self):
        snapshot = os.environ.get("PEA_T2_SNAPSHOT")
        if not snapshot:
            self.skipTest("set PEA_T2_SNAPSHOT to replay a private frozen T2 snapshot")
        frozen = Path(snapshot)
        self.assertTrue((frozen / "events.json").is_file())
        state_dir = self.project / ".pea-state"
        state_dir.mkdir()
        for name in ("events.json", "identity.json", "boundary-review.json", "boundary-context.json"):
            shutil.copyfile(frozen / name, state_dir / name)
        shutil.copyfile(frozen / "evidence.json", self.evidence_path)
        self.assertEqual(self.store.verify()["revision"], 21)
        self.assertEqual(self.store.show()["documents"], {})
        frozen_evidence = json.loads(self.evidence_path.read_text(encoding="utf-8"))
        self.assertNotIn("08:36", frozen_evidence["sources"]["tfl-b"])
        frozen_review = json.loads((state_dir / "boundary-review.json").read_text(encoding="utf-8"))
        self.assertTrue(all("needed" not in row for row in frozen_review["todos"]))
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 0, receipt)
        code, receipt = self.cli("--scope", "comparison-full", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2, receipt)
        self.assertIn("fidelity-document-id", receipt["message"])

    def test_registered_report_requires_validated_task_and_fails_after_change(self):
        current, _ = self.register_report()
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2, receipt)  # Registration alone leaves acceptance pending.
        current = self.store.apply({"op": "task.complete", "id": "compare-a-b",
                                    "evidence_ids": ["report-doc"],
                                    "based_on_revision": current["revision"]},
                                   expected_revision=current["revision"])
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt["document_sha256"], current["documents"]["report-doc"]["sha256"])
        # The full report can be registered even though the old narrow comparison
        # export no longer matches the current revision; the scopes are separate.
        code, _ = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.store.apply({"op": "request.capture", "id": "u2", "source": "user-message",
                          "text": "New rent ceiling GBP 2200."},
                         expected_revision=current["revision"])
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])

    def test_current_report_file_edit_and_symlink_fail_without_journal_change(self):
        current, path = self.register_report(complete=True)
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 0, receipt)
        frozen_revision = current["revision"]
        frozen_hash = current["event_hash"]
        original_bytes = path.read_bytes()

        path.write_text("A newer unsaved report with different facts.\n", encoding="utf-8")
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        self.assertEqual(self.store.verify()["revision"], frozen_revision)
        self.assertEqual(self.store.verify()["event_hash"], frozen_hash)

        target = self.project / "replacement.md"
        target.write_bytes(original_bytes)  # Following this link would incorrectly pass the hash.
        path.unlink()
        path.symlink_to(target)
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        path.unlink()
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])


if __name__ == "__main__":
    unittest.main()
