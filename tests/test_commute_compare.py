"""Offline regressions for source-consistent TfL comparison audits.

Set PEA_FROZEN_TFL_STREAM to the private T1 stream for the owner-only receipt
regression. The portable tests use a small independent TfL-shaped snapshot.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import commute_compare  # noqa: E402

TARGET = "London Bridge Rail Station"
STOP = "1000139"
DAY = "20260917"


def _url(origin, mode):
    encoded = origin.replace(" ", "%20")
    suffix = {"all": "", "rail": "&mode=tube,dlr,overground,elizabeth-line,national-rail,walking",
              "bus": "&mode=bus,walking"}[mode]
    return ("https://api.tfl.gov.uk/Journey/JourneyResults/%s/to/%s"
            "?date=%s&time=0900&timeIs=Arriving%s" % (encoded, STOP, DAY, suffix))


def _plan(origin, mode, duration, start, arrival, endpoint, modes):
    return {"ok": True, "http_status": 200, "source_url": _url(origin, mode),
            "duration_min": duration, "start": "2026-09-17T" + start + ":00",
            "arrival": "2026-09-17T" + arrival + ":00",
            "actual_endpoint": endpoint, "modes": modes,
            "legs": [{"to": endpoint}], "zero_wait_joins": 1}


def snapshot():
    a_origin, b_origin = "SE1 9SG", "51.489981,0.00434"
    base = {"to": STOP, "to_kind": "tfl_stop_id", "arrive_by": "09:00",
            "date": DAY, "door_buffer_min": 0, "plans": ["all", "rail", "bus"]}
    a = {"query": dict(base, **{"from": a_origin, "from_kind": "postcode"}),
         "plans": {
             "all": _plan(a_origin, "all", 17, "08:19", "08:36", TARGET, ["national-rail"]),
             "rail": _plan(a_origin, "rail", 17, "08:19", "08:36", TARGET, ["national-rail"]),
             "bus": _plan(a_origin, "bus", 63, "07:43", "08:46", "London Bridge Station", ["bus"])}}
    b = {"query": dict(base, **{"from": b_origin, "from_kind": "coords"}),
         "plans": {
             "all": _plan(b_origin, "all", 28, "08:30", "08:58",
                          "London Bridge Underground Station", ["bus", "tube"]),
             "rail": _plan(b_origin, "rail", 30, "08:06", "08:36", TARGET, ["national-rail"]),
             "bus": {"ok": False, "http_status": 0, "source_url": _url(b_origin, "bus"),
                     "note": "curl error 28: timed out"}}}
    return {"A": a, "B": b}


ORIGINS = {"A": "postcode point, not the door", "B": "street midpoint, not the unknown unit"}


class TestCommuteComparison(unittest.TestCase):
    def test_frozen_shape_retains_modes_and_rejects_blanket_buffer_claim(self):
        result = commute_compare.audit_commute_comparison(
            snapshot(), TARGET, "真正差在 A 到站較早，B 幾乎貼著 9:00。", ORIGINS)
        self.assertEqual(result["status"], "correction_required")
        self.assertEqual(result["candidates"]["A"]["largest_target_buffer_min"], 24)
        self.assertEqual(result["candidates"]["B"]["largest_target_buffer_min"], 24)
        self.assertEqual(result["candidates"]["B"]["shortest_target_duration_min"], 30)
        rows = result["candidates"]["B"]["plans"]
        self.assertEqual([r["mode"] for r in rows], ["all", "rail", "bus"])
        self.assertEqual([r["status"] for r in rows],
                         ["other_endpoint", "target_endpoint", "unknown"])
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("unsupported_near_deadline", codes)
        self.assertIn("unsupported_earlier_arrival", codes)
        self.assertIn("unexpected_endpoint", codes)
        self.assertNotIn("no_bus_route", codes)

    def test_exclusive_buffer_claim_is_rejected(self):
        result = commute_compare.audit_commute_comparison(
            snapshot(), TARGET, "只有 A 有 9:00 前的緩衝。", ORIGINS)
        self.assertIn("unsupported_exclusive_buffer",
                      [f["code"] for f in result["findings"]])

    def test_synthetic_successful_alternative_is_kept_with_its_endpoint(self):
        receipts = snapshot()
        primary = receipts["B"]["plans"]["rail"]
        alternative = _plan(receipts["B"]["query"]["from"], "rail", 35,
                            "08:07", "08:42", TARGET, ["national-rail"])
        primary["alternatives"] = [copy.deepcopy(primary), alternative]
        result = commute_compare.audit_commute_comparison(receipts, TARGET,
                                                          "B 幾乎貼著 9:00。", ORIGINS)
        b_rows = result["candidates"]["B"]["plans"]
        rail = [r for r in b_rows if r["mode"] == "rail"]
        self.assertEqual(len(rail), 2)
        self.assertEqual([r["buffer_min"] for r in rail], [24, 18])
        self.assertEqual(result["candidates"]["B"]["target_routes"], 2)
        self.assertEqual(result["status"], "correction_required")

    def test_shared_query_and_each_source_url_are_checked(self):
        receipts = snapshot()
        receipts["B"]["query"]["date"] = "20260918"
        result = commute_compare.audit_commute_comparison(receipts, TARGET,
                                                          origin_descriptions=ORIGINS)
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("comparison_basis_mismatch", codes)
        self.assertIn("source_query_mismatch", codes)
        self.assertEqual(result["status"], "correction_required")

    def test_mode_url_mismatch_is_not_ranked_as_clean_source(self):
        receipts = snapshot()
        receipts["B"]["plans"]["rail"]["source_url"] = _url(
            receipts["B"]["query"]["from"], "bus")
        result = commute_compare.audit_commute_comparison(receipts, TARGET,
                                                          origin_descriptions=ORIGINS)
        self.assertIn("source_mode_mismatch",
                      [f["code"] for f in result["findings"]])
        self.assertEqual(result["status"], "correction_required")
        self.assertIsNone(result["candidates"]["B"]["shortest_target_duration_min"])

    def test_successful_unlisted_mode_is_still_audited(self):
        receipts = snapshot()
        receipts["B"]["query"]["plans"] = ["all", "bus"]
        result = commute_compare.audit_commute_comparison(receipts, TARGET,
                                                          origin_descriptions=ORIGINS)
        self.assertEqual([r["mode"] for r in result["candidates"]["B"]["plans"]],
                         ["all", "bus", "rail"])
        self.assertEqual(result["candidates"]["B"]["shortest_target_duration_min"], 30)
        self.assertIn("unlisted_plan_mode", [f["code"] for f in result["findings"]])

    def test_cli_can_block_the_frozen_shape_draft_offline(self):
        script = os.path.join(HERE, "..", "skills", "vet-flat", "scripts",
                              "commute_compare.py")
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            for label, receipt in snapshot().items():
                paths[label] = os.path.join(directory, label + ".json")
                with open(paths[label], "w", encoding="utf-8") as fh:
                    json.dump(receipt, fh)
            draft = os.path.join(directory, "draft.txt")
            with open(draft, "w", encoding="utf-8") as fh:
                fh.write("真正差在 A 到站較早，B 幾乎貼著 9:00。")
            proc = subprocess.run([sys.executable, script,
                "--candidate", "A=" + paths["A"], "--candidate", "B=" + paths["B"],
                "--target-endpoint", TARGET, "--origin", "A=" + ORIGINS["A"],
                "--origin", "B=" + ORIGINS["B"], "--draft", draft],
                capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "correction_required")

    def test_unknown_bus_request_does_not_become_negative_evidence(self):
        result = commute_compare.audit_commute_comparison(snapshot(), TARGET,
                                                          origin_descriptions=ORIGINS)
        self.assertEqual(result["status"], "review_required")
        bus = [r for r in result["candidates"]["B"]["plans"] if r["mode"] == "bus"]
        self.assertEqual(bus[0]["status"], "unknown")
        self.assertIn("timed out", bus[0]["note"])

    @unittest.skipUnless(os.environ.get("PEA_FROZEN_TFL_STREAM"),
                         "owner-only frozen receipt path was not provided")
    def test_actual_private_t1_receipts_plus_synthetic_alternative(self):
        receipts = {}
        with open(os.environ["PEA_FROZEN_TFL_STREAM"], encoding="utf-8") as fh:
            for line in fh:
                event = json.loads(line)
                raw = event.get("rawOutput") or {}
                if event.get("type") != "tool_call_update" or raw.get("type") != "Bash":
                    continue
                output = raw.get("output")
                if not isinstance(output, list):
                    continue
                try:
                    body = json.loads(bytes(output).decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    continue
                query = body.get("query") or {}
                if query.get("to") != STOP or query.get("date") != DAY:
                    continue
                if query.get("from") == "SE1 9SG":
                    receipts["A"] = body
                elif query.get("from") == "51.489981,0.00434":
                    receipts["B"] = body
        self.assertEqual(set(receipts), {"A", "B"})
        result = commute_compare.audit_commute_comparison(
            receipts, TARGET, "B 幾乎貼著 9:00。", ORIGINS)
        self.assertEqual(result["candidates"]["B"]["largest_target_buffer_min"], 24)
        self.assertEqual(result["candidates"]["B"]["plans"][0]["actual_endpoint"],
                         "London Bridge Underground Station")
        self.assertEqual(result["candidates"]["B"]["plans"][1]["arrival"],
                         "2026-09-17T08:36:00")
        self.assertEqual(result["candidates"]["B"]["plans"][2]["status"], "unknown")
        self.assertEqual(result["status"], "correction_required")
        if os.environ.get("PEA_FROZEN_TFL_ANSWER"):
            with open(os.environ["PEA_FROZEN_TFL_ANSWER"], encoding="utf-8") as fh:
                actual_draft = fh.read()
            checked = commute_compare.audit_commute_comparison(
                receipts, TARGET, actual_draft, ORIGINS)
            self.assertIn("unsupported_near_deadline",
                          [f["code"] for f in checked["findings"]])
        augmented = copy.deepcopy(receipts)
        rail = augmented["B"]["plans"]["rail"]
        rail["alternatives"] = [copy.deepcopy(rail),
                                _plan(augmented["B"]["query"]["from"], "rail", 35,
                                      "08:07", "08:42", TARGET, ["national-rail"])]
        again = commute_compare.audit_commute_comparison(augmented, TARGET,
                                                         origin_descriptions=ORIGINS)
        self.assertEqual(len([r for r in again["candidates"]["B"]["plans"]
                              if r["mode"] == "rail"]), 2)


if __name__ == "__main__":
    unittest.main()
