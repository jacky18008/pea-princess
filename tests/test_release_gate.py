# -*- coding: utf-8 -*-
"""Offline tests for bench/release_gate.py, the pre-release gate.

Synthetic results trees only: a scorecard, a kept report, and the truth to grade
it against, all written into a temporary folder. Nothing here touches the network
or the real bench/results tree.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
SAMPLE = os.path.join(HERE, "fixtures", "report-sample.json")

sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.join(ROOT, "skills", "vet-flat", "scripts"))
import release_gate  # noqa: E402

CONFIG = "B-lean"

# The truth that matches tests/fixtures/report-sample.json for candidate c1:
# 53 square metres / 571 square feet, first assessed 2019, a building-wide heat
# system, mid floor, 74 recorded crimes in the six-month window.
FACTS = {
    "epc": {
        "certificate_id": "0000-0000-0000-0000-0000",
        "floor_area_m2": 53.0,
        "floor_area_sqft": 571,
        "first_assessment_year": 2019,
        "heating_class": "community_heat_network",
        "floor_position": "mid",
        "retrieved_at": "2026-09-03T11:00:00Z",
    },
    "crime": {
        "box_half_m": 150,
        "months": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
        "total": 74,
        "tolerance_pct": 15,
        "retrieved_at": "2026-09-03T11:00:00Z",
    },
}

PROFILE = """min_floor_area_sqft: 490
max_building_age_years: 25
budget:
  all_in_pcm_ceiling: 2600
commute:
  destination: "SW1A 2AA"
  max_door_to_door_min: 40
floors:
  reject_ground_floor: true
"""


def read_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, payload):
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1))


def row(case="synthetic", run=1, config=CONFIG, fabrications=0, schema_valid=True, **extra):
    entry = {"run_at": "2026-09-05T10:00:00Z", "agent": "claude", "model": "example",
             "config": config, "case": case, "run_index": run, "kind": "report",
             "fabrications": fabrications, "schema_valid": schema_valid,
             "meets_pass_line": fabrications == 0, "report_path": None}
    entry.update(extra)
    return entry


def doctored():
    """The sample with an invented floor area: 62 square metres against 53 on the register."""
    bad = read_json(SAMPLE)
    cand = bad["candidates"][0]
    for axis in cand["axes"]:
        if axis["id"] != 2:
            continue
        for number in axis.get("numbers") or []:
            if number.get("label") == "Indoor floor area":
                number["value"] = 667
                number["unit"] = "square feet"
    return bad


def unsourced():
    """The sample with one number that names no source and no formula."""
    data = read_json(SAMPLE)
    for axis in data["candidates"][0]["axes"]:
        if axis["id"] == 6:
            axis.setdefault("numbers", []).append({
                "label": "Rumoured service charge", "value": 210, "unit": "GBP per month",
                "meaning": "Someone wrote this in a forum thread.",
                "compared_to": "No local benchmark found."})
    return data


class GateBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vetflat-gate-")
        self.results = os.path.join(self.tmp, "results", "2026-09-05")
        os.makedirs(os.path.join(self.results, "raw"))
        self.evals = os.path.join(self.tmp, "evals.json")
        write_json(self.evals, {"evals": [{
            "id": "synthetic", "address": "Flat 12, Harrowfield Court", "borough": "Test",
            "prompt": "Vet this flat.", "files": ["cases/synthetic/profile.yaml"],
            "expected_facts": copy.deepcopy(FACTS)}]})
        profile = os.path.join(self.tmp, "cases", "synthetic", "profile.yaml")
        os.makedirs(os.path.dirname(profile))
        with io.open(profile, "w", encoding="utf-8") as fh:
            fh.write(PROFILE)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scorecard(self, rows):
        write_json(os.path.join(self.results, "scorecard.json"), rows)

    def keep_report(self, report, case="synthetic", run=1, config=CONFIG):
        write_json(os.path.join(self.results, "raw", "%s-%s-%d.report.json" % (config, case, run)),
                   report)

    def gate(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = release_gate.main([self.results, "--evals", self.evals] + list(args))
        return code, out.getvalue()


class TestAPassingRelease(GateBase):
    def setUp(self):
        GateBase.setUp(self)
        self.scorecard([row()])
        self.keep_report(read_json(SAMPLE))

    def test_it_passes_and_says_so(self):
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn("VERDICT: PASS", out)

    def test_it_prints_one_table_with_the_two_gated_columns(self):
        _, out = self.gate()
        for header in ("case", "run", "fabrications", "schema", "no source", "graded", "result"):
            self.assertIn(header, out)
        self.assertIn("re-graded", out)
        self.assertIn("1 run(s), 1 passing", out)

    def test_it_re_grades_rather_than_trusting_the_row(self):
        self.keep_report(doctored())
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("VERDICT: FAIL", out)
        self.assertIn("re-graded", out)

    def test_an_unsourced_number_is_reported_but_does_not_fail_the_gate(self):
        self.keep_report(unsourced())
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn("VERDICT: PASS", out)
        self.assertIn("reported, not gated", out)
        table = [line for line in out.splitlines() if line.startswith("synthetic")][0]
        self.assertEqual(["synthetic", "1", "0", "ok", "1", "re-graded", "PASS"], table.split())

    def test_the_json_out_carries_the_verdict(self):
        path = os.path.join(self.tmp, "gate.json")
        code, _ = self.gate("--json-out", path)
        self.assertEqual(0, code)
        payload = read_json(path)
        self.assertEqual(CONFIG, payload["config"])
        self.assertTrue(payload["passed"])
        self.assertEqual(1, len(payload["runs"]))
        self.assertEqual(0, payload["runs"][0]["fabrications"])


class TestAFailingRelease(GateBase):
    def test_a_fabricated_number_fails_the_gate(self):
        self.scorecard([row()])
        self.keep_report(doctored())
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("FAIL", out)
        self.assertIn("1 run(s), 0 passing", out)

    def test_an_invalid_schema_fails_the_gate(self):
        self.scorecard([row(fabrications=0, schema_valid=False)])
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("INVALID", out)

    def test_one_bad_run_out_of_three_fails_the_whole_release(self):
        self.scorecard([row(run=1), row(run=2), row(run=3, fabrications=2)])
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("3 run(s), 2 passing", out)

    def test_an_empty_selection_is_a_failure_not_a_pass(self):
        self.scorecard([row(config="C-twenty")])
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("no runs of 'B-lean'", out)

    def test_an_ungraded_run_fails(self):
        self.scorecard([row(fabrications=None, schema_valid=None)])
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn("never graded", out)


class TestScopeAndFallback(GateBase):
    def test_a_missing_report_falls_back_to_the_recorded_score(self):
        self.scorecard([row()])
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn("scorecard", out)
        self.assertIn("no report kept in the results tree", out)

    def test_only_the_named_configuration_is_gated(self):
        self.scorecard([row(), row(config="A-legacy", case="other", fabrications=9)])
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertNotIn("other", out)
        code, out = self.gate("--config", "A-legacy")
        self.assertEqual(1, code, out)
        self.assertIn("Release gate: A-legacy", out)

    def test_it_reads_every_dated_folder_when_pointed_at_the_results_root(self):
        self.scorecard([row()])
        root = os.path.dirname(self.results)
        second = os.path.join(root, "2026-09-06")
        os.makedirs(second)
        write_json(os.path.join(second, "scorecard.json"), [row(run=2, fabrications=3)])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = release_gate.main([root, "--evals", self.evals])
        self.assertEqual(1, code, out.getvalue())
        self.assertIn("2 run(s), 1 passing", out.getvalue())

    def test_a_case_the_eval_file_does_not_know_keeps_the_recorded_score(self):
        self.scorecard([row(case="private-01")])
        self.keep_report(read_json(SAMPLE), case="private-01")
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn("is not in", out)
        self.assertIn("PASS", out)

    def test_a_missing_results_directory_is_a_usage_error(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(2, release_gate.main([os.path.join(self.tmp, "nope")]))
        self.assertIn("is not a directory", err.getvalue())


class TestDefaultConfiguration(unittest.TestCase):
    def test_the_repository_default_is_b_lean(self):
        self.assertEqual("B-lean", release_gate.default_config())

    def test_a_config_marked_default_wins(self):
        tmp = tempfile.mkdtemp(prefix="vetflat-configs-")
        try:
            for name, text in (("A-legacy.yaml", "name: A-legacy\n"),
                               ("Z-release.yaml", "name: Z-release\ndefault: true\n")):
                with io.open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                    fh.write(text)
            self.assertEqual("Z-release", release_gate.default_config(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_readme_documents_the_gate(self):
        with io.open(os.path.join(BENCH, "README.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("release_gate.py", text)
        self.assertIn("fabrications must be 0", text)


if __name__ == "__main__":
    unittest.main()
