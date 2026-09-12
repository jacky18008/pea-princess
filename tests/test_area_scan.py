# -*- coding: utf-8 -*-
"""scripts/area_scan.py: four registers in, one compact fixed-shape JSON out; no network in the tests.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import copy
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
        for key in ("how_to_use", "schema", "ok", "retrieved_at", "where", "quiet", "crime", "works", "living_environment", "reading", "sources", "not_found"):
            self.assertIn(key, self.out, key)
        self.assertEqual("vet-flat/area-scan/2", self.out["schema"])
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
        self.assertLessEqual(len(w["nearest_five"][1]["description"]), 65); self.assertNotIn("storeys", w["nearest_five"][0], "empty fields are dropped")

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


class TestPartialPlanning(unittest.TestCase):
    def compose_rows(self, rows):
        return AS.compose(WHERE, CRIME, dict(PLANNING, results=rows), ROADS, LIVING, [])

    def test_valid_date_without_decision_date_keeps_notable_and_other_registers(self):
        # The full source schema has a nullable decision_date; compact rows omit it.
        for missing in (True, False):
            with self.subTest(compact=missing):
                row = dict(PLANNING["results"][0], valid_date="15/08/2024")
                if missing:
                    row.pop("decision_date")
                else:
                    row["decision_date"] = None
                original = copy.deepcopy(row)
                out = self.compose_rows([row])
                self.assertTrue(out["ok"])
                self.assertEqual(583, out["crime"]["total"])
                self.assertEqual(120, out["quiet"]["main_road_nearest_m"])
                self.assertEqual(1, out["living_environment"]["outdoors_decile"])
                self.assertEqual(row["reference"], out["works"]["notable_recent"][0]["reference"])
                self.assertIn("no decision date", " ".join(out["reading"]))
                self.assertEqual(original, row, "summarising must not rewrite source records")

    def test_optional_display_fields_can_each_be_absent_null_or_empty(self):
        for field in ("description", "reference", "address", "status", "distance_m"):
            for value in (None, "", "absent"):
                with self.subTest(field=field, value=value):
                    row = dict(PLANNING["results"][0])
                    if value == "absent":
                        row.pop(field)
                    else:
                        row[field] = value
                    out = self.compose_rows([row])
                    self.assertEqual(1, len(out["works"]["notable_recent"]))
                    self.assertNotIn("None", " ".join(out["reading"]))

    def test_zero_distance_is_known_and_retained_in_both_views(self):
        out = self.compose_rows([dict(PLANNING["results"][0], distance_m=0)])
        for key in ("nearest_five", "notable_recent"):
            self.assertEqual(0, out["works"][key][0]["distance_m"])
        self.assertIn("at 0 m", " ".join(out["reading"]))

    def test_unknown_distance_does_not_become_zero_or_a_coverage_radius(self):
        row = {"reference": "26/AP/0001", "valid_date": "15/08/2024", "storeys": 12}
        out = self.compose_rows([row])
        self.assertIsNone(out["works"]["seen_out_to_m"])
        text = " ".join(out["reading"])
        self.assertIn("distance unknown", text)
        self.assertIn("status unknown", text)
        self.assertIn("26/AP/0001", text)
        works_text = next(s for s in out["reading"] if s.startswith("Works:"))
        self.assertNotIn("at 0 m", works_text)
        self.assertNotIn("out to 0 m", works_text)
        self.assertNotIn("(0 m)", works_text)

    def test_unknown_distances_sort_last_without_claiming_complete_extent(self):
        unknown = dict(PLANNING["results"][0], reference="unknown", distance_m="")
        known = dict(PLANNING["results"][1], reference="known", distance_m=40)
        out = self.compose_rows([unknown, known])
        self.assertEqual(["known", "unknown"], [r["reference"] for r in out["works"]["nearest_five"]])
        self.assertIsNone(out["works"]["seen_out_to_m"])

    def test_anonymous_sparse_rows_are_not_claimed_to_be_the_same_site(self):
        out = self.compose_rows([{"valid_date": "2025-01-01", "storeys": 12},
                                 {"valid_date": "2025-02-01", "storeys": 6}])
        self.assertEqual(2, len(out["works"]["notable_recent"]))
        self.assertTrue(all(r["related_submissions"] == 0 for r in out["works"]["notable_recent"]))
        self.assertIn("description unavailable", " ".join(out["reading"]))

    def test_scan_returns_partial_registers_without_network(self):
        from unittest.mock import patch
        import crime, planning, roads, noise
        row = dict(PLANNING["results"][0], valid_date="15/08/2024", decision_date=None)
        with patch.object(crime, "box", return_value=CRIME), \
                patch.object(planning, "near", return_value=dict(PLANNING, results=[row])), \
                patch.object(roads, "near", return_value=ROADS), \
                patch.object(noise, "lookup", return_value={"ok": False, "note": "offline fixture"}):
            out = AS.scan(lat=WHERE["lat"], lng=WHERE["lng"], depth="lite", location_source="offline fixture")
        self.assertTrue(out["ok"])
        self.assertEqual(583, out["crime"]["total"])
        self.assertEqual(1, len(out["works"]["notable_recent"]))
        self.assertIn("no decision date", " ".join(out["reading"]))


NOISE = {"schema": "vet-flat/noise/1", "ok": True, "points": [{"road_lden_db": 61.5}, {"road_lden_db": 57.4}],
         "summary": {"road_lden_db": {"at_point": 61.5, "min": 57.4, "max": 61.5, "n": 2, "not_drawn": 0}},
         "band_2017": {"road_lden": "60.0-64.9", "ok": True, "note": ""}, "scale": "Lden: WHO 53 dB",
         "reading": ["Road noise, day-evening-night average: 61.5 dB at the point (57.4-61.5 dB across 2 points along the street): busy-road level.",
                     "The 2017 map put the point in the 60.0-64.9 dB band for road noise.",
                     "These are modelled outdoor levels from 2021 traffic, not a measurement at the window."],
         "sources": ["https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wms"], "not_found": []}
STREET = {"ok": True, "name": "Southerton Road", "highway": "residential", "offset_m": 236, "anchor": {"lat": 51.494684, "lng": -0.228128},
          "points": [{"lat": 51.494684, "lng": -0.228128}, {"lat": 51.4936, "lng": -0.2282}], "mapped_length_m": 263, "ways": 2,
          "source_url": "https://overpass-api.de/api/interpreter"}


def straight_street(n=9, step_m=50.0):
    """A north-south street of n points, step_m apart, through 51.5, -0.1."""
    return [(51.5 + i * step_m / 110540.0, -0.1) for i in range(n)]


class TestStreetAndNoise(unittest.TestCase):
    def test_the_given_point_off_the_street_is_named_and_the_scan_moves(self):
        out = AS.compose(WHERE, CRIME, PLANNING, ROADS, LIVING, [], noise=NOISE, street=STREET, depth="standard")
        self.assertEqual("standard", out["depth"])
        self.assertEqual(236, out["street"]["given_point_offset_m"]); self.assertEqual(2, out["street"]["points_sampled"])
        self.assertIn("236 m from Southerton Road: a centroid, not a door", out["reading"][0])
        self.assertEqual(61.5, out["noise"]["road_lden_db"]); self.assertEqual([57.4, 61.5], out["noise"]["road_lden_range_db"])
        self.assertEqual("60.0-64.9", out["noise"]["band_2017_road"])
        self.assertTrue(any(r.startswith("Road noise") for r in out["reading"]))
        self.assertFalse(any(r.startswith("These are modelled") for r in out["reading"]), "the scan carries its own closing caveat")
        self.assertIn("noise.py", out["how_to_use"]); self.assertEqual("how_to_use", list(out.keys())[0], "the first key tells a sub-agent the output is complete")
        self.assertLess(len(json.dumps(out, ensure_ascii=False)), 7000)

    def test_a_missing_street_is_reported_and_the_scan_stays_put(self):
        out = AS.compose(WHERE, CRIME, PLANNING, ROADS, LIVING, [], noise=NOISE, street={"ok": False, "note": "no named street within 250 m"})
        self.assertIsNone(out["street"]); self.assertIn("street: no named street within 250 m; the scan ran from the given point", out["not_found"])

    def test_sampling_walks_120_m_each_way_and_clamps_at_the_ends(self):
        line = straight_street()
        pts = AS.sample_points(line, 51.5 + 200 / 110540.0, -0.1005)
        self.assertEqual(3, len(pts))
        d_back = AS.haversine_m(pts[0][0], pts[0][1], pts[1][0], pts[1][1]); d_fwd = AS.haversine_m(pts[0][0], pts[0][1], pts[2][0], pts[2][1])
        self.assertAlmostEqual(120, d_back, delta=2); self.assertAlmostEqual(120, d_fwd, delta=2)
        end = AS.sample_points(line, 51.5 + 20 / 110540.0, -0.1)
        self.assertAlmostEqual(20, AS.haversine_m(end[0][0], end[0][1], end[1][0], end[1][1]), delta=2, msg="clamped at the street's end")

    def test_ways_split_at_junctions_are_joined_and_the_nearest_named_street_wins(self):
        a = straight_street(4); b = straight_street(9)[3:]   # two OSM ways sharing a node
        els = [{"type": "way", "id": 1, "tags": {"highway": "residential", "name": "Example Road"}, "geometry": [{"lat": p[0], "lon": p[1]} for p in a]},
               {"type": "way", "id": 2, "tags": {"highway": "residential", "name": "Example Road"}, "geometry": [{"lat": p[0], "lon": p[1]} for p in b]},
               {"type": "way", "id": 3, "tags": {"highway": "primary", "name": "Big Road"}, "geometry": [{"lat": 51.5, "lon": -0.102}, {"lat": 51.504, "lon": -0.102}]},
               {"type": "way", "id": 4, "tags": {"highway": "footway", "name": "Example Path"}, "geometry": [{"lat": 51.5, "lon": -0.1001}, {"lat": 51.504, "lon": -0.1001}]}]
        name, highway, d, line, group = AS.choose_street(els, 51.5 + 300 / 110540.0, -0.1003)
        self.assertEqual("Example Road", name); self.assertEqual(9, len(line), "joined into one polyline"); self.assertEqual(2, len(group))
        self.assertAlmostEqual(21, d, delta=2)
        named = AS.choose_street(els, 51.502, -0.1003, name="big road")
        self.assertEqual("Big Road", named[0], "the asked-for name wins even when farther, case-insensitively")
        self.assertIsNone(AS.choose_street(els, 51.502, -0.1003, name="Nowhere Street"))

    def test_the_named_street_query_is_tiny_and_escaped(self):
        q = AS.street_query(51.49, -0.22, name='St. John\'s Road')
        self.assertIn('["name"~"^St\\. John\'s Road$",i]', q); self.assertIn("around:250", q)
        self.assertIn('["highway"~"^(motorway|trunk', AS.street_query(51.49, -0.22))

    def test_notable_works_read_datahub_dates_and_skip_householder_noise(self):
        recent_big = {"decision_date": "08/05/2024", "description": "Demolition of the existing building and erection of a part-three, part-four storey block", "storeys": 4, "residential_units_proposed": 12}
        self.assertTrue(AS.notable_why(recent_big).startswith("big: 12 homes"))
        discharge = {"decision_date": None, "valid_date": "15/08/2024", "description": "Submission of details of an Air Quality Dust Management Plan (AQDMP)"}
        self.assertEqual("works signal: dust management", AS.notable_why(discharge))
        self.assertIsNone(AS.notable_why({"decision_date": "05/04/2023", "description": "Demolition of the existing building"}), "before 2024")
        self.assertIsNone(AS.notable_why({"decision_date": "08/05/2024", "description": "Demolition of the detached garage in the rear garden; erection of a single storey outbuilding"}))
        self.assertIsNone(AS.notable_why({"decision_date": "16/02/2024", "description": "Erection of a rear roof extension involving an increase in the ridge height"}))

    def test_an_empty_crime_box_says_so_and_carries_the_wider_figure(self):
        empty = dict(CRIME, total=0, by_category={}, predatory_subset={}, wider_box={"half_m": 300, "total": 155, "months": 6})
        out = AS.compose(WHERE, empty, None, ROADS, None, [])
        self.assertIn("none recorded in 6 months in a box about 300 m across; 155 in a box about 600 m across", out["reading"][1])
        self.assertEqual({"half_m": 300, "total": 155, "months": 6}, out["crime"]["wider_box"])


class TestParallelScan(unittest.TestCase):
    def test_the_registers_run_in_threads_and_land_in_the_same_shape(self):
        import time
        calls = []
        def slow(name, value):
            def fn(*a, **kw):
                calls.append(name); time.sleep(0.2); return value
            return fn
        t0 = time.time()
        got = AS._parallel({"a": (slow("a", 1), (), {}), "b": (slow("b", 2), (), {}), "c": (slow("c", None), (), {})})
        self.assertLess(time.time() - t0, 0.5, "three 0.2 s jobs ran together, not one after another")
        self.assertEqual({"a": (1, None), "b": (2, None)}, {k: got[k] for k in ("a", "b")})
        def boom(*a, **kw):
            raise RuntimeError("register down")
        self.assertEqual(None, AS._parallel({"x": (boom, (), {})})["x"][0])
        self.assertIn("register down", AS._parallel({"x": (boom, (), {})})["x"][1])

    def test_the_result_file_name_is_a_slug_under_the_temp_dir(self):
        p = AS.result_path(None, 51.49, -0.22, "Southerton Road", "standard")
        self.assertTrue(p.endswith("vet-flat-scan-southerton-road-standard.json"), p)
        self.assertTrue(AS.result_path("N6 5QD", None, None, None, "lite").endswith("vet-flat-scan-n6-5qd-lite.json"))


class TestCli(unittest.TestCase):
    def test_no_location_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "area_scan.py")], capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)

    def test_depth_and_street_flags_exist(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "area_scan.py"), "--help"], capture_output=True, text=True)
        self.assertIn("--depth {lite,standard,deep}", proc.stdout); self.assertIn("--street", proc.stdout)


if __name__ == "__main__":
    unittest.main()
