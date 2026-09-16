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
import noise as N  # noqa: E402


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


class TestNoiseDiagnostic(unittest.TestCase):
    """Synthetic Defra responses exercise the doctor without contacting a provider."""

    def observation(self, response):
        def level_fn(*args, **kwargs):
            return N.level(*args, fetcher=lambda url, **fetch_kw: response, **kwargs)
        return D.check("Defra strategic noise map", lambda: D.noise_check(level_fn=level_fn))

    @staticmethod
    def response(body="", ok=True, status=200, note="", cache=False):
        return {"body": body, "ok": ok, "status": status, "note": note,
                "from_cache": cache, "retrieved_at": "2026-09-15T18:00:00+00:00"}

    def test_timeout_and_http_failure_keep_the_underlying_reason(self):
        cases = [(self.response(ok=False, status=0, note="curl error 28: Operation timed out"), "timeout"),
                 (self.response(ok=False, status=504, note="http 504"), "http_error")]
        for source, outcome in cases:
            with self.subTest(outcome=outcome):
                result = self.observation(source)
                self.assertFalse(result["ok"])
                self.assertEqual(outcome, result["diagnostic"]["outcome"])
                self.assertEqual(source["note"], result["diagnostic"]["source_note"])
                self.assertIn(source["note"], result["note"])
                self.assertEqual(source["status"], result["diagnostic"]["http_status"])

    def test_bad_body_and_empty_map_are_distinct_unknowns(self):
        for body, outcome in [("<html>not JSON</html>", "invalid_response"),
                              ('{"wrong":"shape"}', "invalid_response"),
                              ('{"type":"FeatureCollection","features":[]}', "no_map_value")]:
            with self.subTest(outcome=outcome):
                result = self.observation(self.response(body=body))
                self.assertFalse(result["ok"])
                self.assertEqual(outcome, result["diagnostic"]["outcome"])
                self.assertIn("source note:", result["note"])

    def test_undrawn_zero_pixel_is_an_honest_absence_not_a_numeric_pass(self):
        response = self.response(body='{"features":[{"properties":{"GRAY_INDEX":0}}]}')
        result = self.observation(response)
        self.assertFalse(result["ok"])
        self.assertTrue(result["diagnostic"]["source_ok"])
        self.assertEqual("below_map_floor", result["diagnostic"]["outcome"])
        self.assertFalse(result["diagnostic"]["drawn"])
        self.assertIsNone(result["diagnostic"]["db"])
        self.assertIn("below the map's floor", result["note"])

    def test_failure_then_value_then_cached_value_have_separate_receipts(self):
        numeric = '{"features":[{"properties":{"GRAY_INDEX":64.87}}]}'
        attempts = [self.response(ok=False, status=0, note="curl error 28: Operation timed out"),
                    self.response(body=numeric), self.response(body=numeric, cache=True)]
        results = [self.observation(attempt) for attempt in attempts]
        self.assertEqual([False, True, True], [item["ok"] for item in results])
        self.assertEqual(["timeout", "numeric_value", "numeric_value"],
                         [item["diagnostic"]["outcome"] for item in results])
        self.assertEqual([False, False, True],
                         [item["diagnostic"]["from_cache"] for item in results])
        self.assertTrue(all(item["diagnostic"]["retrieved_at"] == attempts[0]["retrieved_at"] for item in results))
        self.assertIn("64.9 dB", results[1]["note"])


if __name__ == "__main__":
    unittest.main()
