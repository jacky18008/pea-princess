"""Offline tests for scripts/geo.py — pure maths and the postcodes.io parsers.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import geo  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestHaversine(unittest.TestCase):
    def test_zero_distance(self):
        self.assertEqual(geo.haversine_m(51.5, -0.1, 51.5, -0.1), 0.0)

    def test_one_degree_of_latitude(self):
        # A degree of latitude is about 111.2 km anywhere.
        d = geo.haversine_m(51.0, 0.0, 52.0, 0.0)
        self.assertTrue(111000 < d < 111400, d)

    def test_symmetric(self):
        a = geo.haversine_m(51.504963, -0.087625, 51.505019, -0.086092)
        b = geo.haversine_m(51.505019, -0.086092, 51.504963, -0.087625)
        self.assertAlmostEqual(a, b, places=9)

    def test_longitude_shrinks_with_latitude(self):
        # One degree of longitude at 51.5N is cos(51.5) of one at the equator.
        eq = geo.haversine_m(0.0, 0.0, 0.0, 1.0)
        london = geo.haversine_m(51.5, 0.0, 51.5, 1.0)
        self.assertAlmostEqual(london / eq, math.cos(math.radians(51.5)), places=3)

    def test_known_short_distance(self):
        # SE1 9SG centroid to London Bridge rail station coordinates.
        d = geo.haversine_m(51.504963, -0.087625, 51.505019, -0.086092)
        self.assertTrue(100 < d < 115, d)


class TestBbox(unittest.TestCase):
    def setUp(self):
        self.b = geo.bbox(51.5, 0.0, 150)

    def test_corner_count_and_ring_order(self):
        c = self.b["corners"]
        self.assertEqual(len(c), 4)
        self.assertLess(c[0]["lat"], c[1]["lat"])   # SW below NW
        self.assertEqual(c[1]["lat"], c[2]["lat"])  # NW and NE share a latitude
        self.assertLess(c[1]["lng"], c[2]["lng"])   # NW west of NE
        self.assertEqual(c[0]["lng"], c[1]["lng"])  # SW and NW share a longitude

    def test_deltas_at_51_5_north(self):
        self.assertAlmostEqual(self.b["delta_lat_deg"], 150 / 111320.0, places=9)
        expected_lng = 150 / (111320.0 * math.cos(math.radians(51.5)))
        self.assertAlmostEqual(self.b["delta_lng_deg"], expected_lng, places=9)
        # Longitude degrees are about 1.6x bigger than latitude ones at this latitude.
        self.assertAlmostEqual(self.b["delta_lng_deg"] / self.b["delta_lat_deg"],
                               1.0 / math.cos(math.radians(51.5)), places=6)

    def test_metres_actually_covered(self):
        self.assertAlmostEqual(self.b["half_m_actual_ns"], 149.8, delta=0.5)
        self.assertAlmostEqual(self.b["half_m_actual_ew"], 149.8, delta=0.5)
        self.assertAlmostEqual(self.b["width_m_actual"], 299.7, delta=1.0)
        # Cosine correction means the box is square on the ground, not in degrees.
        self.assertAlmostEqual(self.b["width_m_actual"], self.b["height_m_actual"], delta=0.5)

    def test_poly_string_shape(self):
        parts = self.b["poly"].split(":")
        self.assertEqual(len(parts), 4)
        for p in parts:
            lat, lng = p.split(",")
            float(lat), float(lng)

    def test_corners_are_150m_from_centre_on_the_axes(self):
        for corner in self.b["corners"]:
            d = geo.haversine_m(51.5, 0.0, corner["lat"], corner["lng"])
            self.assertAlmostEqual(d, 150 * math.sqrt(2), delta=1.0)


class TestHexLattice(unittest.TestCase):
    def test_centre_always_present(self):
        self.assertIn((0.0, 0.0), geo._hex_lattice(1600.0, 1500.0))

    def test_all_points_inside_radius(self):
        for x, y in geo._hex_lattice(3200.0, 1500.0):
            self.assertLessEqual(math.hypot(x, y), 3200.0 + 1e-6)

    def test_tile_count_grows_with_radius(self):
        small = len(geo._hex_lattice(1600.0, 1500.0))
        big = len(geo._hex_lattice(3200.0, 1500.0))
        self.assertEqual(small, 7)   # centre plus one ring
        self.assertGreater(big, small)

    def test_no_duplicate_points(self):
        pts = geo._hex_lattice(3200.0, 1500.0)
        self.assertEqual(len(pts), len(set(pts)))

    def test_offset_moves_the_right_way(self):
        lat, lng = geo._offset(51.5, 0.0, 0.0, 150.0)
        self.assertGreater(lat, 51.5)
        self.assertAlmostEqual(geo.haversine_m(51.5, 0.0, lat, lng), 150, delta=0.5)


class TestLookupParser(unittest.TestCase):
    def test_parses_the_fields_the_skill_uses(self):
        rec, err = geo.parse_lookup(read("geo-lookup-SE1-9SG.json"))
        self.assertIsNone(err)
        self.assertEqual(rec["postcode"], "SE1 9SG")
        self.assertAlmostEqual(rec["lat"], 51.504963, places=6)
        self.assertAlmostEqual(rec["lng"], -0.087625, places=6)
        self.assertEqual(rec["admin_district"], "Southwark")
        self.assertEqual(rec["admin_ward"], "London Bridge & West Bermondsey")
        self.assertEqual(rec["lsoa"], "Southwark 006F")
        self.assertEqual(rec["msoa"], "Southwark 006")
        self.assertEqual(rec["outcode"], "SE1")
        self.assertEqual(rec["region"], "London")

    def test_missing_postcode_returns_the_api_error_not_a_guess(self):
        rec, err = geo.parse_lookup(read("geo-lookup-not-found.json"))
        self.assertIsNone(rec)
        self.assertEqual(err, "Invalid postcode")

    def test_garbage_body(self):
        self.assertEqual(geo.parse_lookup([1, 2, 3]), (None, "expected a JSON object"))


class TestNearbyParser(unittest.TestCase):
    def setUp(self):
        self.rows = geo.parse_nearby(read("geo-nearby-SE1-9SG-r2000.json"),
                                     51.504963, -0.087625)

    def test_row_count_hits_the_api_limit(self):
        self.assertEqual(len(self.rows), geo.MAX_LIMIT)

    def test_sorted_nearest_first(self):
        d = [r["distance_m"] for r in self.rows]
        self.assertEqual(d, sorted(d))
        self.assertEqual(self.rows[0]["postcode"], "SE1 9SG")
        self.assertEqual(self.rows[0]["distance_m"], 0.0)

    def test_the_2000m_radius_never_reached_before_the_100_row_cap(self):
        # This is the documented trap: a full page means truncation, not coverage.
        self.assertLess(self.rows[-1]["distance_m"], 500)

    def test_empty_result(self):
        self.assertEqual(geo.parse_nearby({"result": None}, 51.5, -0.1), [])


class TestRadiusGuard(unittest.TestCase):
    def test_nearby_refuses_more_than_the_api_cap(self):
        with self.assertRaises(ValueError) as cm:
            geo.nearby(51.5, -0.1, radius=5000)
        self.assertIn("2000", str(cm.exception))

    def test_cover_refuses_a_step_that_leaves_gaps(self):
        with self.assertRaises(ValueError):
            geo.cover(51.5, -0.1, radius=10000, step=9000)

    def test_cover_refuses_a_zero_step(self):
        with self.assertRaises(ValueError):
            geo.cover(51.5, -0.1, radius=1000, step=0)


class TestCounts(unittest.TestCase):
    def test_counts_drop_none_and_sort_by_frequency(self):
        self.assertEqual(geo._counts(["a", "b", "a", None]), {"a": 2, "b": 1})


if __name__ == "__main__":
    unittest.main()
