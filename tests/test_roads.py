"""Offline tests for scripts/roads.py (OpenStreetMap via Overpass).

Run: python3 -m unittest tests/test_roads.py
Fixtures are raw Overpass `out geom` responses captured on 2026-09-03 for two
points 130 m apart at London Bridge: one beside the Shard, one 30 m off the
A200 Tooley Street.
"""
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import roads  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------- geodesy ----
class TestDistance(unittest.TestCase):
    def test_one_degree_of_latitude(self):
        self.assertAlmostEqual(roads.haversine_m(51.0, 0.0, 52.0, 0.0), 111195, delta=60)

    def test_zero(self):
        self.assertEqual(roads.haversine_m(51.5, -0.1, 51.5, -0.1), 0.0)

    def test_hundred_metres_north(self):
        self.assertAlmostEqual(roads.haversine_m(51.5, -0.1, 51.5 + 100 / 111320.0, -0.1),
                               100, delta=0.5)


class TestBearing(unittest.TestCase):
    def test_cardinals(self):
        for dlat, dlng, want in ((1, 0, 0), (0, 1, 90), (-1, 0, 180), (0, -1, 270)):
            got = roads.bearing_deg(51.5, -0.1, 51.5 + dlat * 0.001, -0.1 + dlng * 0.001)
            self.assertAlmostEqual(got, want, delta=0.5, msg="%s,%s" % (dlat, dlng))

    def test_north_east_is_about_forty_five(self):
        b = roads.bearing_deg(51.5, -0.1, 51.5 + 0.001, -0.1 + 0.001 / math.cos(math.radians(51.5)))
        self.assertAlmostEqual(b, 45, delta=1.0)

    def test_range_is_zero_to_three_sixty(self):
        b = roads.bearing_deg(51.5, -0.1, 51.499, -0.101)
        self.assertTrue(0 <= b < 360)

    def test_compass_labels(self):
        self.assertEqual(roads.compass(0), "N")
        self.assertEqual(roads.compass(90), "E")
        self.assertEqual(roads.compass(180), "S")
        self.assertEqual(roads.compass(270), "W")
        self.assertEqual(roads.compass(359), "N")
        self.assertEqual(roads.compass(23), "NNE")
        self.assertIsNone(roads.compass(None))


class TestPointToSegment(unittest.TestCase):
    """A road is a line, not a dot: distance must be to the segment."""

    def test_perpendicular_foot_inside_the_segment(self):
        # segment runs east-west along lat 51.5; the point sits ~111 m north of
        # its middle, so the answer is the perpendicular, not the end distance.
        d = roads.point_segment_distance_m(51.501, -0.1000, 51.500, -0.1010, 51.500, -0.0990)
        self.assertAlmostEqual(d, 111.2, delta=1.0)

    def test_clamps_to_the_near_endpoint_when_the_foot_is_off_the_end(self):
        d = roads.point_segment_distance_m(51.500, -0.0900, 51.500, -0.1010, 51.500, -0.0990)
        straight = roads.haversine_m(51.500, -0.0900, 51.500, -0.0990)
        self.assertAlmostEqual(d, straight, delta=0.5)

    def test_point_on_the_segment_is_zero(self):
        self.assertAlmostEqual(
            roads.point_segment_distance_m(51.500, -0.1000, 51.500, -0.1010, 51.500, -0.0990),
            0.0, delta=0.5)

    def test_degenerate_segment_is_a_point(self):
        d = roads.point_segment_distance_m(51.501, -0.1, 51.500, -0.1, 51.500, -0.1)
        self.assertAlmostEqual(d, roads.haversine_m(51.501, -0.1, 51.500, -0.1), delta=0.1)

    def test_nearest_point_is_returned_for_the_bearing(self):
        d, lat, lng = roads.nearest_point_on_segment(51.501, -0.1000,
                                                     51.500, -0.1010, 51.500, -0.0990)
        self.assertAlmostEqual(lat, 51.500, places=5)
        self.assertAlmostEqual(lng, -0.1000, places=4)
        self.assertAlmostEqual(roads.bearing_deg(51.501, -0.1000, lat, lng), 180, delta=1.0)

    def test_matches_a_hand_computed_case(self):
        """1 km segment, point 500 m north of its start -> 500 m."""
        a = (51.5000, -0.1000)
        b = (51.5000, -0.1000 + 1000 / (111320.0 * math.cos(math.radians(51.5))))
        p = (51.5000 + 500 / 111320.0, -0.1000)
        self.assertAlmostEqual(roads.point_segment_distance_m(p[0], p[1], a[0], a[1], b[0], b[1]),
                               500, delta=2)


class TestPointInRing(unittest.TestCase):
    RING = [(51.500, -0.101), (51.502, -0.101), (51.502, -0.099),
            (51.500, -0.099), (51.500, -0.101)]

    def test_inside(self):
        self.assertTrue(roads.point_in_ring(51.501, -0.100, self.RING))

    def test_outside(self):
        self.assertFalse(roads.point_in_ring(51.505, -0.100, self.RING))
        self.assertFalse(roads.point_in_ring(51.501, -0.200, self.RING))

    def test_open_ring_is_not_a_polygon(self):
        self.assertFalse(roads.point_in_ring(51.501, -0.100, self.RING[:-1]))


class TestElementGeometry(unittest.TestCase):
    def test_node(self):
        el = {"type": "node", "id": 1, "lat": 51.5, "lon": -0.1}
        d, lat, lng = roads.nearest_on_element(51.501, -0.1, el)
        self.assertAlmostEqual(d, 111.2, delta=1.0)
        self.assertEqual((lat, lng), (51.5, -0.1))

    def test_way(self):
        el = {"type": "way", "id": 2,
              "geometry": [{"lat": 51.500, "lon": -0.101}, {"lat": 51.500, "lon": -0.099}]}
        self.assertAlmostEqual(roads.nearest_on_element(51.501, -0.100, el)[0], 111.2, delta=1.0)

    def test_inside_a_closed_way_scores_zero(self):
        ring = TestPointInRing.RING
        el = {"type": "way", "id": 3, "geometry": [{"lat": a, "lon": b} for a, b in ring]}
        self.assertEqual(roads.nearest_on_element(51.501, -0.100, el)[0], 0.0)

    def test_relation_members(self):
        el = {"type": "relation", "id": 4, "members": [
            {"type": "way", "role": "outer",
             "geometry": [{"lat": 51.500, "lon": -0.101}, {"lat": 51.500, "lon": -0.099}]}]}
        self.assertAlmostEqual(roads.nearest_on_element(51.501, -0.100, el)[0], 111.2, delta=1.0)

    def test_end_nodes_carry_their_ids(self):
        el = {"type": "way", "id": 5, "nodes": [10, 11, 12],
              "geometry": [{"lat": 51.5, "lon": -0.1}, {"lat": 51.501, "lon": -0.1},
                           {"lat": 51.502, "lon": -0.1}]}
        ends = roads.end_nodes(el)
        self.assertEqual([e[0] for e in ends], [10, 12])


# ------------------------------------------------------- heights / angles ---
class TestHeightParsing(unittest.TestCase):
    def test_plain_metres(self):
        self.assertEqual(roads.parse_height_m("96.2"), 96.2)
        self.assertEqual(roads.parse_height_m("310"), 310.0)

    def test_unit_suffixes(self):
        self.assertEqual(roads.parse_height_m("24 m"), 24.0)
        self.assertEqual(roads.parse_height_m("24 metres"), 24.0)
        self.assertEqual(roads.parse_height_m("100 ft"), 30.5)
        self.assertEqual(roads.parse_height_m("100'"), 30.5)

    def test_junk(self):
        for junk in (None, "", "tall", "3-5", "about 20"):
            self.assertIsNone(roads.parse_height_m(junk))


class TestObstructionAngle(unittest.TestCase):
    def test_equal_height_and_distance_is_forty_five_degrees(self):
        self.assertEqual(roads.obstruction_angle_deg(30, 30), 45.0)

    def test_twice_as_tall_as_it_is_far(self):
        self.assertAlmostEqual(roads.obstruction_angle_deg(60, 30), 63.4, places=1)

    def test_far_away_is_shallow(self):
        self.assertLess(roads.obstruction_angle_deg(30, 300), 6)

    def test_inside_the_footprint_is_overhead(self):
        self.assertEqual(roads.obstruction_angle_deg(100, 0), 90.0)

    def test_no_height_no_angle(self):
        self.assertIsNone(roads.obstruction_angle_deg(None, 30))


# ---------------------------------------------------------- classifiers -----
def way(**tags):
    return {"type": "way", "id": 1, "tags": tags}


class TestClassifiers(unittest.TestCase):
    def test_trunk_primary_and_secondary_are_separate(self):
        for h in ("motorway", "trunk", "primary"):
            self.assertTrue(roads.is_trunk_or_primary(way(highway=h)))
            self.assertFalse(roads.is_secondary(way(highway=h)))
        self.assertTrue(roads.is_secondary(way(highway="secondary")))
        self.assertFalse(roads.is_trunk_or_primary(way(highway="secondary")))
        self.assertFalse(roads.is_trunk_or_primary(way(highway="residential")))

    def test_railway_surface_needs_a_main_or_branch_usage_and_no_tunnel(self):
        self.assertTrue(roads.is_railway_surface(way(railway="rail", usage="main")))
        self.assertTrue(roads.is_railway_surface(way(railway="rail", usage="branch")))
        self.assertFalse(roads.is_railway_surface(way(railway="rail", usage="industrial")))
        self.assertFalse(roads.is_railway_surface(way(railway="rail")))
        self.assertFalse(roads.is_railway_surface(way(railway="rail", usage="main", tunnel="yes")))

    def test_tunnel_no_is_not_a_tunnel(self):
        self.assertTrue(roads.is_railway_surface(way(railway="rail", usage="main", tunnel="no")))

    def test_tube_surface_excludes_tunnels_and_underground_locations(self):
        self.assertTrue(roads.is_tube_surface(way(railway="subway")))
        self.assertTrue(roads.is_tube_surface(way(railway="light_rail")))
        self.assertFalse(roads.is_tube_surface(way(railway="subway", tunnel="yes")))
        self.assertFalse(roads.is_tube_surface(way(railway="subway", location="underground")))
        self.assertFalse(roads.is_tube_surface(way(railway="rail")))

    def test_tunnel_railway(self):
        self.assertTrue(roads.is_railway_tunnel(way(railway="subway", tunnel="yes")))
        self.assertFalse(roads.is_railway_tunnel(way(railway="subway")))

    def test_the_amenity_and_shop_buckets(self):
        self.assertTrue(roads.is_night(way(amenity="nightclub")))
        self.assertFalse(roads.is_night(way(amenity="cafe")))
        self.assertTrue(roads.is_food_smell(way(amenity="fast_food")))
        self.assertTrue(roads.is_food_smell(way(shop="fishmonger")))
        self.assertTrue(roads.is_waste(way(landuse="industrial")))
        self.assertTrue(roads.is_waste(way(amenity="recycling")))
        self.assertTrue(roads.is_supermarket(way(shop="convenience")))
        self.assertTrue(roads.is_park(way(leisure="park")))
        self.assertFalse(roads.is_park(way(leisure="garden")))
        self.assertTrue(roads.is_aero(way(aeroway="helipad")))

    def test_obstruction_needs_a_building_and_a_height_signal(self):
        self.assertTrue(roads.is_obstruction(way(building="yes", height="24")))
        self.assertTrue(roads.is_obstruction(way(building="yes", **{"building:levels": "8"})))
        self.assertFalse(roads.is_obstruction(way(building="yes")))
        self.assertFalse(roads.is_obstruction(way(height="24")))


# --------------------------------------------------------- query builder ----
class TestQueryBuilder(unittest.TestCase):
    def setUp(self):
        self.q = roads.build_query(51.5045, -0.0865, 300)

    def test_carries_the_point_and_the_radius(self):
        self.assertIn("around:300,51.5045,-0.0865", self.q)

    def test_each_category_keeps_its_own_radius(self):
        for r in (roads.R_AERO, roads.R_NIGHT, roads.R_FOOD, roads.R_WASTE,
                  roads.R_SHOP, roads.R_PARK, roads.R_BUILD):
            self.assertIn("around:%d," % r, self.q)

    def test_is_one_statement_returning_geometry(self):
        self.assertEqual(self.q.count("out "), 1)
        self.assertIn("out geom;", self.q)
        self.assertTrue(self.q.startswith("[out:json][timeout:"))

    def test_radius_is_an_integer(self):
        self.assertIn("around:300,", roads.build_query(51.5, -0.1, 300.9))


class TestBackoffRule(unittest.TestCase):
    def test_rate_limits_and_transport_failures_retry(self):
        for st in (408, 429, 500, 502, 503, 504):
            self.assertTrue(roads._retryable({"status": st, "note": ""}))
        for note in ("curl error 52: Empty reply from server",
                     "curl error 35: SSL_ERROR_SYSCALL", "curl timeout"):
            self.assertTrue(roads._retryable({"status": 0, "note": note}))

    def test_a_bad_query_or_a_refused_user_agent_does_not_retry(self):
        self.assertFalse(roads._retryable({"status": 400, "note": ""}))
        self.assertFalse(roads._retryable({"status": 406, "note": ""}))
        self.assertFalse(roads._retryable({"status": 200, "note": ""}))

    def test_backoff_is_two_four_eight(self):
        self.assertEqual(roads.BACKOFF_S, [2, 4, 8])
        self.assertEqual(len(roads.INSTANCES), 2)
        self.assertIn("overpass-api.de", roads.INSTANCES[0])


# -------------------------------------------------------- fixture parsing ---
class TestLondonBridgeFixture(unittest.TestCase):
    """51.5045, -0.0865 — beside the Shard, 142 m off the A200."""

    @classmethod
    def setUpClass(cls):
        data = load("roads-overpass-london-bridge.json")
        cls.out = roads.near(51.5045, -0.0865, 300, elements=data["elements"])

    def test_envelope(self):
        for k in ("source_url", "http_status", "ok", "note", "retrieved_at", "evidence_class",
                  "query_used", "overpass_instance", "attribution"):
            self.assertIn(k, self.out)
        self.assertEqual(self.out["evidence_class"], "C")
        self.assertIn("ODbL", self.out["attribution"])

    def test_nearest_primary_road(self):
        r = self.out["trunk_or_primary_road"]["nearest"]
        self.assertEqual(r["name"], "Tooley Street")
        self.assertEqual(r["highway"], "primary")
        self.assertEqual(r["ref"], "A200")
        self.assertAlmostEqual(r["distance_m"], 142, delta=3)
        self.assertEqual(r["direction"], "NNE")

    def test_distinct_road_names_are_listed(self):
        names = self.out["trunk_or_primary_road"]["names"]
        self.assertIn("Tooley Street", names)
        self.assertIn("Borough High Street", names)
        self.assertLess(len(names), self.out["trunk_or_primary_road"]["count"])

    def test_surface_railway(self):
        r = self.out["railway_surface"]["nearest"]
        self.assertEqual(r["name"], "South Eastern Main Line")
        self.assertAlmostEqual(r["distance_m"], 62, delta=3)

    def test_the_tube_here_is_all_in_tunnel(self):
        self.assertEqual(self.out["tube_surface"]["count"], 0)
        self.assertIsNone(self.out["tube_surface"]["nearest"])

    def test_a_tunnel_way_end_is_not_reported_as_a_portal(self):
        """Jubilee Line ways end inside the radius, but none meets a surface
        railway there, so they are way splits, not portals."""
        p = self.out["railway_tunnel_portal"]
        self.assertEqual(p["count"], 0)
        self.assertIsNone(p["nearest"])
        self.assertGreater(p["count_unconfirmed_way_ends"], 0)
        self.assertFalse(p["unconfirmed_way_ends"][0]["confirmed_portal"])

    def test_night_economy_counts_and_nearest(self):
        n = self.out["night_economy"]
        self.assertEqual(n["search_radius_m"], 100)
        self.assertEqual(n["count"], 2)
        self.assertEqual(n["nearest"]["name"], "Bar 31")
        self.assertLess(n["nearest"]["distance_m"], 20)

    def test_food_smell_sources(self):
        f = self.out["food_smell_sources"]
        self.assertEqual(f["search_radius_m"], 60)
        self.assertGreaterEqual(f["count"], 3)
        self.assertEqual(f["nearest"]["name"], "Aqua Shard")

    def test_supermarket_carries_a_walking_estimate(self):
        s = self.out["supermarket"]["nearest"]
        self.assertEqual(s["name"], "M&S Food")
        self.assertAlmostEqual(s["distance_m"], 32, delta=3)
        self.assertGreaterEqual(s["walk_minutes_street_estimate"],
                                s["walk_minutes_straight_line"])
        self.assertIn("walking_note", self.out["supermarket"])

    def test_park(self):
        self.assertEqual(self.out["park_or_green"]["search_radius_m"], 400)
        self.assertGreater(self.out["park_or_green"]["count"], 0)
        self.assertIn("Guy Street Park", self.out["park_or_green"]["names"])

    def test_nothing_industrial_or_airborne_nearby(self):
        self.assertEqual(self.out["waste_or_recycling"]["count"], 0)
        self.assertEqual(self.out["helipad_or_aerodrome"]["count"], 0)
        self.assertIn("waste_or_recycling", self.out["not_found"]["what"])
        self.assertIn("crowd-sourced", self.out["not_found"]["meaning"])

    def test_obstruction_candidates_are_worst_first(self):
        o = self.out["obstruction_candidates"]
        self.assertEqual(o["search_radius_m"], 60)
        angles = [r["obstruction_angle_deg"] for r in o["worst_first"]]
        self.assertEqual(angles, sorted(angles, reverse=True))
        top = o["worst_first"][0]
        self.assertEqual(top["name"], "The Shard")
        self.assertTrue(top["contains_point"])
        self.assertEqual(top["obstruction_angle_deg"], 90)
        self.assertIsNone(top["bearing_deg"])

    def test_a_neighbouring_tower_gets_a_steep_angle_and_a_direction(self):
        r = [x for x in self.out["obstruction_candidates"]["worst_first"]
             if x["name"] == "Shard Place"][0]
        self.assertAlmostEqual(r["distance_m"], 41, delta=3)
        self.assertEqual(r["direction"], "WNW")
        self.assertEqual(r["building_levels"], 26.0)
        self.assertAlmostEqual(r["height_m_estimate"], 78.0, delta=20)
        self.assertGreater(r["obstruction_angle_deg"], 45)

    def test_the_facade_note_does_not_fire_at_142_metres(self):
        self.assertIsNone(self.out["facade_note"])
        self.assertEqual(self.out["facade_note_trigger_m"], 60)


class TestTooleyStreetFixture(unittest.TestCase):
    """51.505375, -0.085706 — 30 m off the A200, so the facade rule fires."""

    @classmethod
    def setUpClass(cls):
        data = load("roads-overpass-tooley-street.json")
        cls.out = roads.near(51.505375, -0.085706, 300, elements=data["elements"])

    def test_the_primary_road_is_within_the_trigger_distance(self):
        r = self.out["trunk_or_primary_road"]["nearest"]
        self.assertEqual(r["name"], "Tooley Street")
        self.assertLessEqual(r["distance_m"], roads.FACADE_TRIGGER_M)
        self.assertAlmostEqual(r["distance_m"], 30, delta=4)

    def test_the_facade_note_is_emitted_verbatim(self):
        self.assertEqual(self.out["facade_note"],
                         "a mapped main road is within 60 m of the query point; check the flat's window "
                         "direction and sound insulation. This proximity check does not establish its "
                         "facade orientation or a quiet side")

    def test_proximity_alone_can_trigger_a_prompt_without_building_evidence(self):
        elements = [{"type": "way", "id": 1, "tags": {"highway": "primary", "name": "Example Road"},
                     "geometry": [{"lat": 51.5, "lon": -0.101}, {"lat": 51.5, "lon": -0.099}]}]
        out = roads.near(51.5 + 30 / 111320.0, -0.1, 300, elements=elements)
        self.assertEqual(30, out["trunk_or_primary_road"]["nearest"]["distance_m"])
        self.assertEqual(0, out["obstruction_candidates"]["count"])
        self.assertIn("query point", out["facade_note"])
        self.assertIn("check the flat's window direction and sound insulation", out["facade_note"])
        self.assertIn("does not establish its facade orientation or a quiet side", out["facade_note"])

    def test_facade_note_subcommand_returns_the_same_answer(self):
        out = roads.facade_note(51.505375, -0.085706, 300, full=self.out)
        self.assertEqual(out["facade_note"], self.out["facade_note"])
        self.assertEqual(out["trunk_or_primary_road"]["name"], "Tooley Street")
        self.assertIn("query_used", out)
        self.assertNotIn("obstruction_candidates", out)


class TestNullsNotZeros(unittest.TestCase):
    def test_an_empty_world_reports_null_distances_not_zero(self):
        out = roads.near(51.5, -0.1, 300, elements=[])
        for k in ("trunk_or_primary_road", "railway_surface", "supermarket", "park_or_green"):
            self.assertIsNone(out[k]["nearest"])
            self.assertEqual(out[k]["count"], 0)
        self.assertIsNone(out["facade_note"])
        self.assertEqual(out["obstruction_candidates"]["count"], 0)
        self.assertIn("meaning", out["not_found"])

    def test_every_reported_distance_is_a_whole_number_of_metres(self):
        data = load("roads-overpass-london-bridge.json")
        out = roads.near(51.5045, -0.0865, 300, elements=data["elements"])
        for k, v in out.items():
            if isinstance(v, dict) and v.get("nearest"):
                self.assertIsInstance(v["nearest"]["distance_m"], int, k)


if __name__ == "__main__":
    unittest.main()
