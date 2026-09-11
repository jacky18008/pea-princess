# -*- coding: utf-8 -*-
"""scripts/area_scan.py: four registers in, one compact fixed-shape JSON out; no network in the tests.

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
import area_scan as AS  # noqa: E402

WHERE = {"postcode": "SE1 9SG", "lat": 51.504963, "lng": -0.087625, "district": "Southwark", "how_located": "postcode centroid"}
ROADS = {"ok": True, "source_url": "https://overpass.example/q", "radius_m": 300,
         "trunk_or_primary_road": {"count": 1, "names": ["Tooley Street"], "nearest": {"distance_m": 120}},
         "secondary_road": {"count": 0, "names": [], "nearest": None},
         "railway_surface": {"count": 1, "names": ["London Bridge approach"], "nearest": {"distance_m": 210}},
         "tube_surface": {"count": 0, "nearest": None},
         "night_economy": {"count": 4, "names": ["The Example Arms"], "nearest": {"distance_m": 90}},
         "park_or_green": {"count": 1, "nearest": {"distance_m": 250}}, "facade_note": "one facade faces the main road"}
CRIME = {"ok": True, "source_url": "https://data.police.uk/api/x", "query": {"half_m": 150}, "total": 583, "months_counted": 6,
         "per_month": {"2026-02": 75, "2026-03": 119, "2026-04": 100, "2026-05": 86, "2026-06": 111, "2026-07": 92},
         "by_category": {"theft-from-the-person": 192, "other-theft": 115, "violent-crime": 100, "anti-social-behaviour": 42, "robbery": 37, "drugs": 14},
         "predatory_subset": {"share_of_total": 0.636}, "latest_available_month": "2026-07", "months_missing": []}
PLANNING = {"ok": True, "source_url": "https://planningdata.london.gov.uk/x", "radius_m": 250, "count": 12, "since_year": 2018,
            "results": [{"reference": "26/AP/0001", "address": "1 Example Street", "description": "Erection of a 12-storey building " * 3,
                         "status": "Approved", "decision": "Grant", "decision_date": "2026-03-01", "distance_m": 80, "storeys": 12,
                         "residential_units_proposed": 90, "tall_building_hint": True},
                        {"reference": "25/AP/0002", "address": "2 Example Street", "description": "Rear extension", "status": "Decided",
                         "decision": "Grant", "decision_date": "2025-11-01", "distance_m": 40, "storeys": None, "residential_units_proposed": None}]}
LIVING = {"ok": True, "source_url": "https://assets.publishing.service.gov.uk/x.csv", "lsoa": {"name": "Southwark 006F"},
          "outdoors": {"decile": 1}, "indoors": {"decile": 4}}


class TestCompose(unittest.TestCase):
    def setUp(self):
        self.out = AS.compose(WHERE, CRIME, PLANNING, ROADS, LIVING, [])

    def test_the_shape_is_fixed_and_small(self):
        for key in ("schema", "ok", "retrieved_at", "where", "quiet", "crime", "works", "living_environment", "reading", "sources", "not_found"):
            self.assertIn(key, self.out, key)
        self.assertEqual("vet-flat/area-scan/1", self.out["schema"])
        self.assertTrue(self.out["ok"])
        self.assertLess(len(json.dumps(self.out, ensure_ascii=False)), 6000, "the whole scan must stay a few thousand characters")

    def test_quiet_block_and_its_sentence(self):
        q = self.out["quiet"]
        self.assertEqual(120, q["main_road_nearest_m"]); self.assertEqual(["Tooley Street"], q["main_road_names"])
        self.assertEqual(210, q["railway_surface_nearest_m"]); self.assertEqual(4, q["night_economy_count"])
        self.assertIn("nearest main road Tooley Street at 120 m", self.out["reading"][0])
        self.assertIn("Rail at surface: nearest at 210 m", self.out["reading"][0])
        self.assertIn("The Example Arms at 90 m", self.out["reading"][0])

    def test_crime_block_keeps_the_denominator(self):
        c = self.out["crime"]
        self.assertEqual(583, c["total"]); self.assertEqual(6, c["months"]); self.assertEqual(97.2, c["per_month_avg"])
        self.assertEqual("theft-from-the-person", c["top_categories"][0]["category"])
        self.assertIn("583 recorded in 6 months in a box about 300 m across (97.2 a month)", self.out["reading"][1])
        self.assertIn("64%", self.out["reading"][1])

    def test_works_are_the_nearest_five_with_short_fields(self):
        w = self.out["works"]
        self.assertEqual(12, w["count"]); self.assertEqual(1, w["tall_building_hints"])
        self.assertEqual("25/AP/0002", w["nearest_five"][0]["reference"], "sorted by distance")
        self.assertLessEqual(len(w["nearest_five"][1]["description"]), 80)

    def test_living_environment_and_the_closing_caveat(self):
        self.assertEqual(1, self.out["living_environment"]["outdoors_decile"])
        self.assertIn("outdoors decile 1 of 10", self.out["reading"][3])
        self.assertIn("the area, not the flat", self.out["reading"][-1])
        self.assertEqual(4, len(self.out["sources"]))

    def test_a_failed_register_is_reported_not_guessed(self):
        out = AS.compose(WHERE, {"ok": False, "note": "curl error 6"}, None, ROADS, None, ["planning: timeout"])
        self.assertIsNone(out["crime"]); self.assertIsNone(out["works"])
        self.assertIn("crime: curl error 6", out["not_found"]); self.assertIn("planning: timeout", out["not_found"])
        self.assertTrue(out["ok"], "roads alone still makes a scan")
        self.assertTrue(all("Crime:" not in s for s in out["reading"]))


class TestCli(unittest.TestCase):
    def test_no_location_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "area_scan.py")], capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)


if __name__ == "__main__":
    unittest.main()
