"""Finite fetch attempts cancel blocked subprocesses and future batch requests."""
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
import _fetch as fetch


class FetchDeadlineTests(unittest.TestCase):
    def test_cancelled_source_cannot_start_cache_or_network_work(self):
        cancel = threading.Event()
        cancel.set()
        with fetch.fetch_budget(time.monotonic() + 20, cancel), mock.patch.object(fetch, "cache_dir") as cache, mock.patch.object(fetch.subprocess, "Popen") as popen:
            out = fetch.fetch("https://example.invalid/")
        cache.assert_not_called()
        popen.assert_not_called()
        self.assertFalse(out["ok"])
        self.assertIn("cancellation", out["note"])

    def test_throttle_deadline_stops_before_launch_and_followup_stays_cancelled(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = threading.Event()
            with mock.patch.object(fetch, "cache_dir", return_value=folder), mock.patch.dict(fetch._last_hit, {"example.invalid": time.time()}), \
                    fetch.fetch_budget(time.monotonic() + .03, cancel), mock.patch.object(fetch.subprocess, "Popen") as popen:
                started = time.monotonic()
                first = fetch.fetch("https://example.invalid/", min_gap=2)
                second = fetch.fetch("https://example.invalid/other")
            self.assertLess(time.monotonic() - started, .3)
            popen.assert_not_called()
            self.assertFalse(first["ok"])
            self.assertFalse(second["ok"])

    def test_real_hanging_child_is_killed_reaped_and_not_retried(self):
        cancel = threading.Event()
        children = []
        original = subprocess.Popen
        def remember(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        with fetch.fetch_budget(time.monotonic() + .08, cancel), mock.patch.object(fetch.subprocess, "Popen", side_effect=remember):
            with self.assertRaises((fetch.FetchCancelled, subprocess.TimeoutExpired)):
                fetch._run_curl([sys.executable, "-c", "import time; time.sleep(30)"], "", 20)
        self.assertEqual(1, len(children))
        self.assertIsNotNone(children[0].poll())
        with self.assertRaises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)

    def test_cancel_event_ends_active_child_before_long_deadline(self):
        cancel = threading.Event()
        timer = threading.Timer(.08, cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        started = time.monotonic()
        with fetch.fetch_budget(time.monotonic() + 20, cancel):
            with self.assertRaises(fetch.FetchCancelled):
                fetch._run_curl([sys.executable, "-c", "import time; time.sleep(30)"], "", 20)
        self.assertLess(time.monotonic() - started, .5)


if __name__ == "__main__":
    unittest.main()
