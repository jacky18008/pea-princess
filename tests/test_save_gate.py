"""Offline saved-claim acceptance against the actual private journal and export."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
        return boundary.reconcile(self.store, self.payload(), self.evidence, 0)

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

    def test_fresh_plain_comparison_save_has_current_journal_and_receipt(self):
        reconciled = self.reconcile()
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 0, receipt)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["revision"], reconciled["revision"])
        self.assertEqual(receipt["event_hash"], reconciled["comparison"]["binding"]["event_hash"])
        self.assertEqual(receipt["evidence_sha256"], eligibility.canonical_hash(self.evidence))
        self.assertTrue((self.project / ".pea-state/events.json").is_file())
        self.assertTrue((self.project / ".pea-state/boundary-review.json").is_file())
        self.assertTrue((self.project / ".pea-state/boundary-context.json").is_file())
        self.assertEqual(set(self.store.show()["requirements"]), {"rent", "bedrooms", "quiet"})

    def test_informal_snapshot_cannot_claim_durable_comparison(self):
        snapshot = self.project / "state/comparison.json"
        snapshot.parent.mkdir()
        snapshot.write_text('{"A":"can consider", "B":"research"}', encoding="utf-8")
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        self.assertFalse((self.project / ".pea-state/events.json").exists())

    def test_evidence_drift_and_new_unreconciled_turn_invalidate_prior_export(self):
        self.reconcile()
        changed = copy.deepcopy(self.evidence)
        changed["candidates"][1]["fields"]["rent_gbp_month"]["value"] = 2200
        changed["candidates"][1]["fields"]["rent_gbp_month"]["quote"] = "B now advertises GBP 2200/month."
        changed["sources"]["B-rent_gbp_month"] = "B now advertises GBP 2200/month."
        self.evidence_path.write_text(json.dumps(changed), encoding="utf-8")
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])

        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")
        current = self.store.show()
        self.store.apply({"op": "request.capture", "id": "u2", "source": "user-message",
                          "text": "Lower rent limit to GBP 2200."}, expected_revision=current["revision"])
        code, receipt = self.cli("--scope", "comparison", "--evidence", str(self.evidence_path))
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])

    def test_comparison_scope_does_not_claim_registered_report(self):
        self.reconcile()
        code, receipt = self.cli("--scope", "report", "--output-id", "report-a-b")
        self.assertEqual(code, 2)
        self.assertFalse(receipt["ok"])
        self.assertEqual(save_gate.check(self.project, "comparison", evidence=self.evidence)["scope"],
                         "comparison")

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
