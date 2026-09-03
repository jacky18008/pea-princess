"""Offline tests for scripts/crime.py — month windows, the analyser, route geometry.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import crime  # noqa: E402
import geo  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestMonthWindow(unittest.TestCase):
    def test_six_months_ending_at_the_latest(self):
        self.assertEqual(crime.month_window("2026-06", 6),
                         ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])

    def test_window_crosses_the_year_boundary(self):
        self.assertEqual(crime.month_window("2026-02", 4),
                         ["2025-11", "2025-12", "2026-01", "2026-02"])

    def test_single_month(self):
        self.assertEqual(crime.month_window("2026-01", 1), ["2026-01"])

    def test_thirteen_months_goes_back_a_full_year_and_one(self):
        w = crime.month_window("2026-01", 13)
        self.assertEqual(len(w), 13)
        self.assertEqual(w[0], "2025-01")
        self.assertEqual(w[-1], "2026-01")

    def test_window_is_inclusive_of_the_end_and_ordered_oldest_first(self):
        w = crime.month_window("2026-06", 6)
        self.assertEqual(w[-1], "2026-06")
        self.assertEqual(w, sorted(w))

    def test_zero_months_is_a_usage_error(self):
        with self.assertRaises(ValueError):
            crime.month_window("2026-06", 0)

    def test_latest_month_is_a_data_month_not_a_date(self):
        self.assertEqual(crime._month_of(read("crime-latest.json")["date"]), "2026-06")


class TestAnalyse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.may = read("crime-box-SE1-9SG-2026-05.json")
        cls.jun = read("crime-box-SE1-9SG-2026-06.json")
        cls.both = cls.may + cls.jun
        cls.a = crime.analyse(cls.both, ["2026-05", "2026-06"])

    def test_total_is_the_record_count(self):
        self.assertEqual(self.a["total"], len(self.both))
        self.assertEqual(self.a["total"], 197)

    def test_per_month_covers_exactly_the_months_fetched_and_sums_to_the_total(self):
        self.assertEqual(sorted(self.a["per_month"]), ["2026-05", "2026-06"])
        self.assertEqual(sum(self.a["per_month"].values()), self.a["total"])
        self.assertEqual(self.a["per_month"]["2026-05"], len(self.may))

    def test_all_fourteen_categories_present_even_at_zero(self):
        self.assertEqual(len(crime.CATEGORIES), 14)
        for c in crime.CATEGORIES:
            self.assertIn(c, self.a["by_category"])
        self.assertEqual(self.a["by_category"]["other-crime"], 0)

    def test_categories_sum_to_the_total(self):
        self.assertEqual(sum(self.a["by_category"].values()), self.a["total"])

    def test_predatory_subset_is_exactly_the_four_categories_added_up(self):
        p = self.a["predatory_subset"]
        self.assertEqual(p["categories"],
                         ["anti-social-behaviour", "violent-crime",
                          "theft-from-the-person", "robbery"])
        expected = sum(self.a["by_category"][c] for c in p["categories"])
        self.assertEqual(p["count"], expected)
        self.assertEqual(p["count"], sum(p["per_category"].values()))
        self.assertAlmostEqual(p["share_of_total"],
                               round(expected / float(self.a["total"]), 3), places=3)
        self.assertLessEqual(p["count"], self.a["total"])

    def test_predatory_subset_explains_busy_versus_dangerous(self):
        self.assertIn("busy", self.a["predatory_subset"]["explanation"].lower())

    def test_top_anchors_are_the_five_biggest_in_order(self):
        anchors = self.a["top_anchors"]
        self.assertLessEqual(len(anchors), 5)
        counts = [x["count"] for x in anchors]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(anchors[0]["anchor"], "On or near Hospital")
        self.assertEqual(self.a["top_anchor_share"], anchors[0]["share_of_total"])

    def test_anchor_dispersion_arithmetic(self):
        d = self.a["anchor_dispersion"]
        self.assertEqual(d["top5_total"], sum(x["count"] for x in self.a["top_anchors"]))
        self.assertAlmostEqual(d["top5_mean"], round(d["top5_total"] / 5.0, 1), places=1)
        self.assertAlmostEqual(d["top5_share_of_total"],
                               round(d["top5_total"] / float(self.a["total"]), 3), places=3)
        self.assertGreaterEqual(d["distinct_anchors"], len(self.a["top_anchors"]))
        self.assertIn("anchor", d["reading"].lower())

    def test_a_month_that_returned_nothing_shows_zero_rather_than_disappearing(self):
        a = crime.analyse(self.may, ["2026-04", "2026-05"])
        self.assertEqual(a["per_month"], {"2026-04": 0, "2026-05": len(self.may)})

    def test_one_month_is_never_scaled_up_to_the_window(self):
        one = crime.analyse(self.may, ["2026-05"])
        self.assertEqual(one["total"], len(self.may))
        self.assertLess(one["total"], self.a["total"])

    def test_empty_input(self):
        a = crime.analyse([], [])
        self.assertEqual(a["total"], 0)
        self.assertEqual(a["predatory_subset"]["count"], 0)
        self.assertIsNone(a["predatory_subset"]["share_of_total"])
        self.assertEqual(a["top_anchors"], [])

    def test_a_new_category_from_the_api_is_kept_not_dropped(self):
        rec = {"category": "space-piracy", "month": "2026-05",
               "location": {"latitude": "51.5", "longitude": "-0.09",
                            "street": {"name": "On or near Nowhere"}}}
        a = crime.analyse([rec], ["2026-05"])
        self.assertEqual(a["by_category"]["space-piracy"], 1)
        self.assertEqual(sum(a["by_category"].values()), 1)


class TestBoxGeometry(unittest.TestCase):
    def test_the_poly_handed_to_the_police_api_is_four_corners(self):
        b = geo.bbox(51.504963, -0.087625, 150)
        parts = b["poly"].split(":")
        self.assertEqual(len(parts), 4)
        self.assertAlmostEqual(b["width_m_actual"], 300, delta=1.0)

    def test_the_sensitivity_shift_is_twenty_metres(self):
        self.assertEqual(crime.SHIFT_M, 20.0)
        dlat = crime.SHIFT_M / crime.M_PER_DEG_LAT
        self.assertAlmostEqual(geo.haversine_m(51.5, 0.0, 51.5 + dlat, 0.0), 20, delta=0.2)


class TestRouteGeometry(unittest.TestCase):
    def test_parse_route(self):
        pts = crime.parse_route("51.5050,-0.0860;51.5041,-0.0885")
        self.assertEqual(len(pts), 2)
        self.assertAlmostEqual(pts[0][0], 51.5050)
        self.assertAlmostEqual(pts[1][1], -0.0885)

    def test_parse_route_tolerates_spaces_and_trailing_separators(self):
        self.assertEqual(len(crime.parse_route(" 51.5,-0.1 ; 51.6,-0.2 ; ")), 2)

    def test_parse_route_needs_two_points(self):
        with self.assertRaises(ValueError):
            crime.parse_route("51.5,-0.1")

    def test_parse_route_rejects_a_malformed_point(self):
        with self.assertRaises(ValueError):
            crime.parse_route("51.5,-0.1;nonsense")

    def test_point_to_segment_perpendicular(self):
        self.assertAlmostEqual(crime.point_segment_m(0, 0, -100, 10, 100, 10), 10.0, places=6)

    def test_point_to_segment_falls_back_to_the_nearer_end(self):
        d = crime.point_segment_m(-50, 0, 0, 10, 100, 10)
        self.assertAlmostEqual(d, math.hypot(50, 10), places=6)

    def test_point_on_the_line_is_zero(self):
        self.assertAlmostEqual(crime.point_segment_m(50, 10, 0, 10, 100, 10), 0.0, places=6)

    def test_degenerate_segment_is_a_point_distance(self):
        self.assertAlmostEqual(crime.point_segment_m(3, 4, 0, 0, 0, 0), 5.0, places=6)

    def test_planar_projection_matches_haversine_over_short_distances(self):
        proj = crime._planar(51.5, -0.1)
        x, y = proj(51.5 + 150 / crime.M_PER_DEG_LAT, -0.1)
        self.assertAlmostEqual(math.hypot(x, y), 150, delta=0.5)

    def test_real_records_can_be_filtered_by_distance_to_a_walk(self):
        # The London Bridge station forecourt to the SE1 9SG centroid.
        pts = [(51.505019, -0.086092), (51.504963, -0.087625)]
        proj = crime._planar(51.50499, -0.086859)
        seg = [proj(a, b) for a, b in pts]
        dists = []
        for r in read("crime-box-SE1-9SG-2026-06.json"):
            ll = crime._latlng(r)
            if ll is None:
                continue
            px, py = proj(ll[0], ll[1])
            dists.append(min(crime.point_segment_m(px, py, seg[i][0], seg[i][1],
                                                   seg[i + 1][0], seg[i + 1][1])
                             for i in range(len(seg) - 1)))
        self.assertTrue(dists)
        # police.uk snap points are coarser than a 30 m corridor: this is why
        # crime.py reports nearest_anchor_m and a corridor ladder instead of
        # letting a zero read as a safe walk.
        self.assertGreater(min(dists), 30)
        self.assertLess(min(dists), 200)


if __name__ == "__main__":
    unittest.main()
