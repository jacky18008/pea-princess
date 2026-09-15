# -*- coding: utf-8 -*-
"""scripts/doctor.py: the install self-check, offline part (no network in tests).

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import doctor as D  # noqa: E402


class TestOffline(unittest.TestCase):
    def test_every_offline_check_passes_in_this_checkout(self):
        results = D.offline_checks()
        self.assertGreaterEqual(len(results), 9)
        bad = [r["check"] for r in results if not r["ok"]]
        self.assertEqual([], bad)
        self.assertTrue(all("needed_for" in r and "seconds" in r for r in results))

    def test_cli_offline_json_shape_and_exit_code(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "doctor.py"), "--offline", "--json"], capture_output=True, text=True, timeout=120)
        self.assertEqual(0, proc.returncode, proc.stdout[-300:])
        out = json.loads(proc.stdout)
        self.assertTrue(out["ok"]); self.assertEqual(0, out["failed"]); self.assertIn("working", out["reading"])


if __name__ == "__main__":
    unittest.main()
