"""Offline process races, durable follow-up, failure and unsafe-file regressions."""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "vet-flat" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import area_scan_store as store
import area_scan

REQUEST = {"postcode": "AA1 1AA", "lat": None, "lng": None, "street": "Example Road", "months": 6,
           "crime_half_m": 150, "planning_radius": 250, "effective_planning_radius": 250,
           "roads_radius": 300, "requested_depth": "standard", "depth": "standard", "escalation_reason": None}
RESULT = {"schema": "vet-flat/area-scan/2", "ok": True, "retrieved_at": "2026-01-01T12:00:00+00:00",
          "quiet": {"main_road_nearest_m": 100}, "reading": ["Some observation"], "sources": [], "not_found": []}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = os.path.join(os.path.realpath(self.temp.name), "results")

    def run_scan(self, scan=None, request=None, **kw):
        return store.run(self.root, request or REQUEST, "source-v1", scan or (lambda: copy.deepcopy(RESULT)),
                         lambda: "2026-01-02T12:00:00+00:00", **kw)

    def test_followup_reuses_exact_snapshot_preserves_age_and_partial_gaps(self):
        partial = dict(RESULT, not_found=["rail map: HTTP 403"])
        first = self.run_scan(lambda: partial)
        again = self.run_scan(lambda: self.fail("follow-up must not fetch"))
        self.assertEqual("partial", again["persistence"]["status"])
        self.assertTrue(again["persistence"]["reused"])
        self.assertEqual(RESULT["retrieved_at"], again["retrieved_at"])
        self.assertEqual(partial["not_found"], again["not_found"])
        self.assertEqual(first["saved_to"], again["saved_to"])
        index = store.verified_index(self.root)
        self.assertFalse(index["gaps"])
        self.assertEqual("partial", index["results"][0]["status"])
        self.assertEqual(REQUEST, index["results"][0]["arguments"])
        self.assertEqual(0o700, os.stat(self.root).st_mode & 0o777)
        self.assertEqual(0o600, os.stat(first["saved_to"]).st_mode & 0o777)

    def test_failed_scan_is_saved_and_not_automatically_retried(self):
        def fail():
            raise RuntimeError("synthetic register failure")
        first = self.run_scan(fail)
        second = self.run_scan(lambda: self.fail("failed snapshot must not auto retry"))
        self.assertEqual("failed", first["persistence"]["status"])
        self.assertFalse(second["ok"])
        self.assertIn("synthetic register failure", second["note"])

    def test_all_effective_arguments_and_source_identity_separate_results(self):
        base = self.run_scan()
        for name, value in (("months", 3), ("crime_half_m", 200), ("roads_radius", 400),
                            ("planning_radius", 300), ("effective_planning_radius", 300),
                            ("depth", "deep"), ("street", "Other Road"), ("lat", 51.5), ("lng", -.1)):
            out = self.run_scan(request=dict(REQUEST, **{name: value}))
            self.assertNotEqual(base["saved_to"], out["saved_to"])
        out = store.run(self.root, REQUEST, "source-v2", lambda: RESULT, lambda: "now")
        self.assertNotEqual(base["saved_to"], out["saved_to"])

    def test_two_processes_make_only_one_scan(self):
        # Real processes exercise filesystem locking; the scanner itself is synthetic.
        code = """import json,os,sys,time
sys.path.insert(0, sys.argv[1])
import area_scan_store as s
request=json.loads(sys.argv[3]); result=json.loads(sys.argv[4])
def fake():
    with open(sys.argv[5], 'a') as f: f.write('scan\\n')
    time.sleep(.25)
    return result
print(json.dumps(s.run(sys.argv[2],request,'source-v1',fake,lambda:'now',2)))
"""
        count = os.path.join(os.path.realpath(self.temp.name), "calls")
        args = [sys.executable, "-c", code, str(SCRIPTS), self.root, json.dumps(REQUEST), json.dumps(RESULT), count]
        processes = [subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = []
        for proc in processes:
            out, err = proc.communicate(timeout=5)
            self.assertEqual(0, proc.returncode, err)
            results.append(json.loads(out))
        self.assertEqual(["scan"], pathlib.Path(count).read_text().splitlines())
        self.assertEqual([False, True], sorted(r["persistence"]["reused"] for r in results), results)

    def test_pending_wait_is_bounded_and_does_not_start_duplicate(self):
        started, release = threading.Event(), threading.Event()
        def slow():
            started.set()
            release.wait(3)
            return RESULT
        worker = threading.Thread(target=lambda: self.run_scan(slow))
        worker.start()
        self.addCleanup(lambda: (release.set(), worker.join(3)))
        self.assertTrue(started.wait(2))
        t0 = time.monotonic()
        other = self.run_scan(lambda: self.fail("duplicate producer"), wait_seconds=.05)
        self.assertLess(time.monotonic() - t0, .5)
        self.assertEqual("pending", other["persistence"]["status"])
        release.set()
        worker.join(3)

    def test_interrupted_producer_is_recoverable_without_retry(self):
        code = """import json,os,sys
sys.path.insert(0,sys.argv[1]); import area_scan_store as s
s.run(sys.argv[2],json.loads(sys.argv[3]),'source-v1',lambda:os._exit(7),lambda:'now')
"""
        proc = subprocess.run([sys.executable, "-c", code, str(SCRIPTS), self.root, json.dumps(REQUEST)], timeout=5)
        self.assertEqual(7, proc.returncode)
        result = self.run_scan(lambda: self.fail("interrupted producer must not auto retry"))
        self.assertEqual("interrupted", result["persistence"]["status"])

    def test_corruption_symlink_hardlink_and_public_permissions_are_rejected(self):
        result = self.run_scan()
        path = pathlib.Path(result["saved_to"])
        original = path.read_bytes()
        body = json.loads(original)
        body["result"]["quiet"]["main_road_nearest_m"] = 1
        path.write_text(json.dumps(body))
        self.assertEqual("storage_error", self.run_scan()["persistence"]["status"])
        self.assertTrue(store.verified_index(self.root)["gaps"])
        path.unlink()
        target = pathlib.Path(self.temp.name) / "untrusted"
        target.write_bytes(original)
        os.chmod(target, 0o600)
        path.symlink_to(target)
        self.assertEqual("storage_error", self.run_scan()["persistence"]["status"])
        path.unlink()
        os.link(target, path)
        self.assertEqual("storage_error", self.run_scan()["persistence"]["status"])
        path.unlink()
        path.write_bytes(original)
        os.chmod(path, 0o644)
        self.assertEqual("storage_error", self.run_scan()["persistence"]["status"])

    def test_result_directory_symlink_rejected_before_scan(self):
        target = os.path.join(os.path.realpath(self.temp.name), "elsewhere")
        os.mkdir(target, 0o700)
        os.symlink(target, self.root)
        result = self.run_scan(lambda: self.fail("unsafe directory must not fetch"))
        self.assertEqual("storage_error", result["persistence"]["status"])

    def test_capacity_and_index_metadata_are_bounded(self):
        with mock.patch.object(store, "MAX_RECORDS", 2):
            self.run_scan()
            self.run_scan(request=dict(REQUEST, months=3))
            out = self.run_scan(lambda: self.fail("full store must not fetch"), request=dict(REQUEST, months=4))
            self.assertEqual("capacity", out["persistence"]["status"])
            idx = store.verified_index(self.root, limit=1)
            self.assertTrue(idx["truncated"])
            self.assertEqual(1, len(idx["results"]))
            self.assertLessEqual(len(store.encoded(idx)), 16000)

    def test_source_identity_changes_when_actual_implementation_changes(self):
        scripts = pathlib.Path(self.temp.name) / "scripts"
        scripts.mkdir()
        source = scripts / "scan.py"
        source.write_text("version = 1")
        first = store.source_identity(str(scripts))
        source.write_text("version = 2")
        self.assertNotEqual(first, store.source_identity(str(scripts)))

    def test_main_reuses_session_directory_across_calls(self):
        import io
        with mock.patch.dict(os.environ, {"VETFLAT_SCAN_RESULT_DIR": self.root, "VETFLAT_RESEARCH_DEPTH": "standard"}), mock.patch.object(sys, "argv", ["area_scan", "--postcode", "AA1 1AA"]), mock.patch.object(area_scan, "scan", return_value=copy.deepcopy(RESULT)) as scan:
            replies = []
            for _ in range(2):
                with mock.patch("sys.stdout", new_callable=io.StringIO) as output:
                    area_scan.main()
                    replies.append(json.loads(output.getvalue()))
            self.assertEqual(1, scan.call_count)
            self.assertTrue(replies[1]["persistence"]["reused"])
            self.assertEqual(replies[0]["retrieved_at"], replies[1]["retrieved_at"])


class DepthAndCoverageTests(unittest.TestCase):
    def test_depth_change_without_reason_rejected_before_network(self):
        import io
        with mock.patch.dict(os.environ, {"VETFLAT_RESEARCH_DEPTH": "standard"}), mock.patch.object(sys, "argv", ["area_scan", "--postcode", "AA1 1AA", "--depth", "deep"]), mock.patch.object(area_scan, "scan") as scan, mock.patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as exc:
                area_scan.main()
            self.assertEqual(2, exc.exception.code)
            scan.assert_not_called()

    def test_environment_baseline_and_explicit_reason_are_recorded(self):
        import io
        for args, expected in (([], "lite"), (["--depth", "deep", "--escalation-reason", "user requested rail noise"], "deep")):
            with mock.patch.dict(os.environ, {"VETFLAT_RESEARCH_DEPTH": "lite"}), mock.patch.object(sys, "argv", ["area_scan", "--postcode", "AA1 1AA", "--no-save"] + args), mock.patch.object(area_scan, "scan", return_value=copy.deepcopy(RESULT)) as scan, mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                area_scan.main()
                out = json.loads(stdout.getvalue())
                self.assertEqual(expected, out["execution"]["effective_depth"])
                self.assertEqual("lite", out["execution"]["requested_depth"])
                self.assertEqual(expected, scan.call_args.args[7])

    def test_noise_numeric_not_drawn_and_failed_coverage_remain_distinct(self):
        noise = {"ok": True, "points": [{}, {}, {}], "summary": {"road_lden_db": {"n": 1, "not_drawn": 0, "at_point": 56.5}, "rail_lden_db": {"n": 1, "not_drawn": 1}}, "not_found": ["road layer HTTP 403"]}
        out = area_scan.compose({}, None, None, None, None, [], noise=noise)
        cov = out["noise"]["coverage"]
        self.assertEqual(2, cov["road_lden_db"]["failed"])
        self.assertEqual(2, cov["rail_lden_db"]["successful"])
        self.assertEqual(1, cov["rail_lden_db"]["numeric_values"])
        self.assertIn("1/3 requests succeeded", " ".join(out["reading"]))
        noise["ok"] = False
        out = area_scan.compose({}, None, None, None, None, [], noise=noise)
        self.assertFalse(out["ok"], "coverage metadata alone is not successful evidence")

    def test_planning_coverage_cap_and_unknown_distances_are_visible(self):
        planning = {"ok": True, "radius_m": 500, "total_matching": 2000, "results": [{"reference": "test", "valid_date": "2026-01-01", "description": "Basement construction", "distance_m": None}]}
        out = area_scan.compose({}, None, planning, None, None, [])
        cov = out["works"]["coverage"]
        self.assertEqual(1, cov["rows_read"])
        self.assertEqual(2000, cov["total_matching"])
        self.assertFalse(cov["all_matching_rows_read"])
        self.assertIsNone(cov["furthest_read_m"])
        self.assertIn("no decision date", " ".join(out["reading"]))
        self.assertIn("only 1 of 2000", " ".join(out["not_found"]))

    def test_malformed_register_summary_preserves_other_registers(self):
        got = {"crime": ({"ok": True, "total": 1, "months_counted": 1, "by_category": {}}, None),
               "planning": ({"ok": True, "results": [{"distance_m": 10, "valid_date": "2026", "storeys": "bad"}]}, None),
               "roads": ({"ok": True, "radius_m": 300, "trunk_or_primary_road": {"nearest": {"distance_m": 80}}}, None),
               "noise": ({"ok": False, "not_found": ["HTTP 403"]}, None)}
        with mock.patch.object(area_scan, "_parallel", return_value=got):
            out = area_scan.scan(lat=51.5, lng=-.1, depth="lite", location_source="offline fixture")
        self.assertTrue(out["ok"])
        self.assertEqual(80, out["quiet"]["main_road_nearest_m"])
        self.assertEqual(1, out["crime"]["total"])
        self.assertIsNone(out["works"])
        self.assertIn("planning summary unavailable", " ".join(out["not_found"]))

    def test_failed_stage_with_a_record_does_not_become_success(self):
        import planning
        out = {"works": {"notable_recent": [{"reference": "EXAMPLE", "distance_m": 5}]}, "not_found": [], "reading": []}
        with mock.patch.object(planning, "stages", return_value={"ok": False, "note": "source assertion failed", "record": {"status": "Approved"}}):
            area_scan.add_stage(out, {})
        self.assertNotIn("top_notable_stage", out["works"])
        self.assertIn("source assertion failed", out["not_found"][0])


if __name__ == "__main__":
    unittest.main()
