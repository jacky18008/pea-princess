"""Offline interruption/deadline tests; no public HTTP or model calls."""
import copy
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "vet-flat" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import area_scan as scan
import area_scan_store as store
import _fetch

REQUEST = {"postcode": "AA1 1AA", "depth": "lite", "requested_depth": "lite"}
RESULT = {"schema": scan.SCHEMA, "ok": True, "sources": [], "reading": [], "not_found": [],
          "quiet": {"main_road_nearest_m": 40}, "retrieved_at": "offline"}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = os.path.join(os.path.realpath(self.temp.name), "results")

    def test_one_hanging_source_returns_partial_and_never_writes_late_completion(self):
        import roads, noise, crime, planning
        release = threading.Event()
        checkpoints = []
        self.addCleanup(release.set)
        def hanging(*args, **kwargs):
            release.wait(3)
            return {"ok": True, "total": 999, "months_counted": 1}
        def perform(checkpoint):
            def capture(value):
                checkpoints.append(copy.deepcopy(value))
                checkpoint(value)
            return scan.scan(lat=51.5, lng=-.1, location_source="offline fixture", depth="lite",
                             deadline_seconds=.12, source_timeout_seconds=.08, checkpoint=capture)
        with mock.patch.object(crime, "box", side_effect=hanging), \
                mock.patch.object(roads, "near", return_value={"ok": True, "radius_m": 300, "trunk_or_primary_road": {"nearest": {"distance_m": 40}}}), \
                mock.patch.object(noise, "lookup", return_value={"ok": False, "note": "offline network interruption", "not_found": ["connection reset"]}), \
                mock.patch.object(planning, "near", return_value={"ok": False, "note": "offline timeout"}):
            t0 = time.monotonic()
            out = store.run(self.root, REQUEST, "fixture", perform, lambda: "now", with_checkpoint=True)
        self.assertLess(time.monotonic() - t0, 1)
        self.assertEqual("timed_out", out["persistence"]["status"])
        self.assertEqual(40, out["quiet"]["main_road_nearest_m"])
        self.assertEqual("timed_out", out["source_progress"]["crime"]["status"])
        self.assertEqual("failed", out["source_progress"]["noise"]["status"])
        self.assertIn("connection reset", " ".join(out["not_found"]))
        self.assertTrue(checkpoints)
        saved = pathlib.Path(out["saved_to"])
        original = saved.read_bytes()
        count = len(checkpoints)
        release.set()
        time.sleep(.05)
        self.assertEqual(original, saved.read_bytes())
        self.assertEqual(count, len(checkpoints))
        again = store.run(self.root, REQUEST, "fixture", lambda: self.fail("automatic retry"), lambda: "now")
        self.assertTrue(again["persistence"]["reused"])
        self.assertEqual("timed_out", again["persistence"]["status"])
        self.assertIn("Scan status: timed_out", out["how_to_use"])
        self.assertFalse(out["how_to_use"].startswith("Complete."))
        self.assertIn("not a completed scan", checkpoints[0]["result"]["how_to_use"])

    def test_slow_checkpoint_does_not_turn_finished_neighbours_into_timeouts(self):
        completed = []
        def fast(name):
            completed.append(name)
            return {"ok": True, "name": name}
        def slow_checkpoint(value):
            # Simulates initial durable fsync taking longer than both source budgets.
            time.sleep(.1)
        budget = scan.ScanBudget(.1, .08, slow_checkpoint)
        previous = getattr(scan._scan_context, "budget", None)
        scan._scan_context.budget = budget
        try:
            result = scan._bounded_jobs({name: (fast, (name,), {}) for name in ("a", "b")})
            self.assertEqual(["a", "b"], sorted(completed))
            for name in ("a", "b"):
                self.assertEqual(({"ok": True, "name": name}, None), result[name])
                self.assertEqual("complete", budget.sources[name]["status"])
        finally:
            budget.close()
            scan._scan_context.budget = previous

    def test_deadline_before_later_stage_makes_no_new_source_call(self):
        budget = scan.ScanBudget(.02, .02)
        previous = getattr(scan._scan_context, "budget", None)
        scan._scan_context.budget = budget
        try:
            time.sleep(.03)
            fn = mock.Mock()
            result = scan._call("later", fn)
            fn.assert_not_called()
            self.assertIn("before source started", result[1])
        finally:
            budget.close()
            scan._scan_context.budget = previous

    def test_cli_partial_evidence_timeout_is_not_success_exit(self):
        with mock.patch.object(sys, "argv", ["scan", "--postcode", "AA1 1AA", "--no-save"]), \
                mock.patch.object(scan, "scan", return_value=dict(RESULT, scan_status="timed_out")), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(1, scan.main())

    def test_reconcile_dead_owner_preserves_checkpoint_and_treats_pid_as_metadata(self):
        code = """import json,os,sys
sys.path.insert(0,sys.argv[1]); import area_scan_store as s
def fake(cp):
 cp({'sources':{'roads':{'status':'complete'},'crime':{'status':'running'}},'result':json.loads(sys.argv[4])})
 os._exit(7)
s.run(sys.argv[2],json.loads(sys.argv[3]),'fixture',fake,lambda:'before',with_checkpoint=True)
"""
        proc = subprocess.run([sys.executable, "-c", code, str(SCRIPTS), self.root, json.dumps(REQUEST), json.dumps(RESULT)], timeout=5)
        self.assertEqual(7, proc.returncode)
        path = next(pathlib.Path(self.root).glob("*.json"))
        record = json.loads(path.read_text())
        record["owner_pid"] = os.getpid()  # Simulate a reused PID belonging to a live, unrelated process.
        with store.directory(self.root) as (_, fd):
            store.atomic_json(fd, path.name, record)
        before = store.verified_index(self.root)["results"][0]
        self.assertFalse(before["result_present"])
        self.assertIsNone(before["gap_count"])
        receipt = store.reconcile_running(self.root, now=lambda: "after")
        self.assertEqual([record["key"]], receipt["recovered"])
        self.assertFalse(receipt["gaps"])
        out = json.loads(path.read_text())
        self.assertEqual("interrupted", out["state"])
        self.assertEqual(40, out["result"]["quiet"]["main_road_nearest_m"])
        self.assertEqual("interrupted", out["result"]["source_progress"]["crime"]["status"])
        self.assertEqual("unknown", out["diagnosis"]["network_cause"])
        self.assertIn("Interrupted scan", out["result"]["how_to_use"])
        self.assertFalse(out["result"]["how_to_use"].startswith("Complete."))
        self.assertEqual([], store.reconcile_running(self.root)["recovered"])

    def test_live_owner_retains_lease_even_when_claimed_pid_is_dead(self):
        started, release = threading.Event(), threading.Event()
        def slow():
            started.set()
            release.wait(3)
            return RESULT
        worker = threading.Thread(target=lambda: store.run(self.root, REQUEST, "fixture", slow, lambda: "now"))
        worker.start()
        self.addCleanup(lambda: (release.set(), worker.join(3)))
        self.assertTrue(started.wait(2))
        key = store.digest({"request": REQUEST, "source_identity": "fixture"})
        receipt = store.reconcile_running(self.root)
        self.assertEqual([key], receipt["pending"])
        self.assertEqual([], receipt["recovered"])
        self.assertEqual("running", store.verified_index(self.root)["results"][0]["status"])

    def test_completion_between_initial_read_and_lock_acquisition_is_not_overwritten(self):
        started, release = threading.Event(), threading.Event()
        def slow():
            started.set()
            release.wait(3)
            return RESULT
        worker = threading.Thread(target=lambda: store.run(self.root, REQUEST, "fixture", slow, lambda: "now"))
        worker.start()
        self.addCleanup(lambda: (release.set(), worker.join(3)))
        self.assertTrue(started.wait(2))
        original_lock = store._lock
        def finish_before_lock(fd, deadline):
            release.set()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            return original_lock(fd, deadline)
        with mock.patch.object(store, "_lock", side_effect=finish_before_lock):
            receipt = store.reconcile_running(self.root)
        self.assertFalse(receipt["recovered"])
        self.assertFalse(receipt["gaps"])
        self.assertEqual("complete", store.verified_index(self.root)["results"][0]["status"])

    def test_exited_parent_does_not_invalidate_live_child_producer_lease(self):
        child_script = pathlib.Path(self.temp.name) / "producer.py"
        child_script.write_text("""import sys,time
sys.path.insert(0,sys.argv[1]); import area_scan_store as s
def slow():
 time.sleep(30)
s.run(sys.argv[2],{'depth':'lite'},'fixture',slow,lambda:'now')
""")
        launcher = "import subprocess,sys; p=subprocess.Popen(sys.argv[1:],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid)"
        parent = subprocess.run([sys.executable, "-c", launcher, sys.executable, str(child_script), str(SCRIPTS), self.root], capture_output=True, text=True, timeout=3)
        self.assertEqual(0, parent.returncode, parent.stderr)
        child_pid = int(parent.stdout)
        def cleanup():
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.addCleanup(cleanup)
        deadline = time.monotonic() + 3
        while not pathlib.Path(self.root).exists() or not list(pathlib.Path(self.root).glob("*.json")):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.01)
        key = store.digest({"request": {"depth": "lite"}, "source_identity": "fixture"})
        self.assertEqual([key], store.reconcile_running(self.root)["pending"])
        cleanup()
        deadline = time.monotonic() + 2
        while True:
            receipt = store.reconcile_running(self.root)
            if receipt["recovered"]:
                break
            self.assertLess(time.monotonic(), deadline)
            time.sleep(.01)
        self.assertEqual([key], receipt["recovered"])
        self.assertEqual("interrupted", store.verified_index(self.root)["results"][0]["status"])

    def test_missing_or_unsafe_lease_is_gap_and_does_not_claim_interruption(self):
        def stop(cp):
            raise KeyboardInterrupt("test")
        store.run(self.root, REQUEST, "fixture", stop, lambda: "now", with_checkpoint=True)
        path = next(pathlib.Path(self.root).glob("*.json"))
        record = json.loads(path.read_text())
        record.update(state="running")
        with store.directory(self.root) as (_, fd):
            store.atomic_json(fd, path.name, record)
        path.with_suffix(".lock").unlink()
        receipt = store.reconcile_running(self.root)
        self.assertTrue(receipt["gaps"])
        self.assertFalse(receipt["recovered"])
        path.with_suffix(".lock").symlink_to(path)
        receipt = store.reconcile_running(self.root)
        self.assertTrue(receipt["gaps"])
        self.assertFalse(receipt["recovered"])

    def test_sigterm_cli_saves_completed_checkpoint_as_interrupted(self):
        marker = pathlib.Path(self.temp.name) / "ready"
        code = """import os,sys,time
sys.path.insert(0,sys.argv[1]); import area_scan as a
marker=sys.argv[-1]; sys.argv=['scan','--postcode','AA1 1AA','--result-dir',sys.argv[2]]
def fixed(*args,**kwargs):
 kwargs['checkpoint']({'sources':{'noise':{'status':'running'}},'result':{'schema':a.SCHEMA,'ok':True,'quiet':{'main_road_nearest_m':40},'reading':[],'sources':[],'not_found':[]}})
 open(marker,'w').write('ready'); time.sleep(30)
a.scan=fixed
sys.exit(a.main())
"""
        proc = subprocess.Popen([sys.executable, "-c", code, str(SCRIPTS), self.root, str(marker)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(marker.exists())
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=3)
        self.assertEqual(1, proc.returncode, stderr)
        out = json.loads(stdout)
        self.assertEqual("interrupted", out["persistence"]["status"])
        self.assertEqual(40, out["quiet"]["main_road_nearest_m"])
        self.assertEqual("interrupted", store.verified_index(self.root)["results"][0]["status"])


if __name__ == "__main__":
    unittest.main()
