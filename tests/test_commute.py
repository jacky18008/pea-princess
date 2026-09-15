"""Offline tests for scripts/commute.py — journey parsing, stop points, strike families.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import commute  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def stn(name, modes, walk_m, lines=None):
    """A station shaped like parse_stoppoints() output, for grading tests."""
    return {"name": name, "modes": list(modes), "lines": lines or [],
            "straight_line_m": round(walk_m / commute.WALK_FACTOR),
            "walk_m_estimate": walk_m,
            "walk_min_estimate": round(walk_m / commute.WALK_M_PER_MIN, 1)}


class TestEnvFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, ".env")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_plain_key_value(self):
        self.write("TFL_APP_KEY=abc123\n")
        self.assertEqual(commute.load_env(self.path)["TFL_APP_KEY"], "abc123")

    def test_comments_blanks_quotes_and_export_prefix(self):
        self.write("# a comment\n\nexport TFL_APP_KEY='quoted value'\nOTHER=\"two\"\nbroken\n")
        env = commute.load_env(self.path)
        self.assertEqual(env["TFL_APP_KEY"], "quoted value")
        self.assertEqual(env["OTHER"], "two")
        self.assertNotIn("broken", env)

    def test_value_may_contain_equals_signs(self):
        self.write("TFL_APP_KEY=a=b=c\n")
        self.assertEqual(commute.load_env(self.path)["TFL_APP_KEY"], "a=b=c")

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(commute.load_env(os.path.join(self.dir, "nope")), {})

    def test_key_is_redacted_from_any_url_we_report(self):
        url = "https://api.tfl.gov.uk/StopPoint?lat=1&app_key=SECRET&radius=800"
        self.assertNotIn("SECRET", commute._redact(url))
        self.assertIn("app_key=REDACTED", commute._redact(url))


class TestPlaces(unittest.TestCase):
    def test_coordinates(self):
        api, kind, label = commute.parse_place("51.5049,-0.0876")
        self.assertEqual(kind, "coords")
        self.assertEqual(api, "51.5049,-0.0876")

    def test_coordinates_with_spaces(self):
        self.assertEqual(commute.parse_place(" 51.5 , -0.1 ")[1], "coords")

    def test_postcode_is_normalised_and_encoded(self):
        api, kind, label = commute.parse_place("se19sg")
        self.assertEqual(kind, "postcode")
        self.assertEqual(label, "SE1 9SG")
        self.assertEqual(api, "SE1%209SG")

    def test_postcode_with_a_space_already(self):
        self.assertEqual(commute.parse_place("WC2R 2LS")[2], "WC2R 2LS")

    def test_free_text_falls_through(self):
        self.assertEqual(commute.parse_place("Victoria")[1], "text")

    def test_disambiguated_tfl_station_id_can_be_requeried_without_guessing(self):
        api, kind, label = commute.parse_place("1000139")
        self.assertEqual((api, kind, label), ("1000139", "tfl_stop_id", "1000139"))
        url = commute._journey_url("SE3%207RS", api, "20260916", "0900", "")
        self.assertIn("/to/1000139?", url)

    def test_empty_is_a_usage_error(self):
        with self.assertRaises(ValueError):
            commute.parse_place("  ")

    def test_out_of_range_coordinates(self):
        with self.assertRaises(ValueError):
            commute.parse_place("951.5,-0.1")


class TestDateAndTime(unittest.TestCase):
    def test_next_weekday_after_a_friday_is_monday(self):
        self.assertEqual(commute.next_weekday(datetime.date(2026, 9, 4)),
                         datetime.date(2026, 9, 7))

    def test_next_weekday_after_a_saturday_is_monday(self):
        self.assertEqual(commute.next_weekday(datetime.date(2026, 9, 5)),
                         datetime.date(2026, 9, 7))

    def test_next_weekday_after_a_wednesday_is_thursday(self):
        self.assertEqual(commute.next_weekday(datetime.date(2026, 9, 2)),
                         datetime.date(2026, 9, 3))

    def test_next_weekday_is_always_strictly_in_the_future(self):
        d = commute.next_weekday()
        self.assertGreater(d, datetime.date.today())
        self.assertLess(d.weekday(), 5)

    def test_explicit_date(self):
        self.assertEqual(commute.resolve_date("20260907"), ("20260907", "explicit"))
        self.assertEqual(commute.resolve_date("2026-09-07"), ("20260907", "explicit"))

    def test_default_is_the_next_weekday(self):
        self.assertEqual(commute.resolve_date(None)[1], "next-weekday")
        self.assertEqual(commute.resolve_date("next-weekday")[1], "next-weekday")

    def test_a_date_that_does_not_exist_is_refused(self):
        with self.assertRaises(ValueError):
            commute.resolve_date("20260231")

    def test_bad_date_format(self):
        with self.assertRaises(ValueError):
            commute.resolve_date("tuesday")

    def test_times(self):
        self.assertEqual(commute.resolve_time("09:00"), "0900")
        self.assertEqual(commute.resolve_time("9:00"), "0900")
        self.assertEqual(commute.resolve_time("1830"), "1830")
        self.assertEqual(commute.resolve_time(None), "0900")

    def test_bad_times(self):
        for bad in ("25:00", "09:99", "nine"):
            with self.assertRaises(ValueError):
                commute.resolve_time(bad)


class TestJourneyParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.all = commute.parse_journey_response(read("commute-journey-SE1-to-WC2R-all.json"))
        cls.rail = commute.parse_journey_response(read("commute-journey-SE1-to-WC2R-rail.json"))
        cls.bus = commute.parse_journey_response(read("commute-journey-SE1-to-WC2R-bus.json"))

    def test_all_three_plans_parse(self):
        for p in (self.all, self.rail, self.bus):
            self.assertTrue(p["ok"])
            self.assertIsInstance(p["duration_min"], int)

    def test_fastest_journey_is_chosen_not_the_first(self):
        self.assertEqual(self.bus["duration_min"], min(self.bus["alternatives_min"]))
        self.assertEqual(self.bus["alternatives_min"], sorted(self.bus["alternatives_min"]))

    def test_rail_plan_uses_rail_only(self):
        self.assertEqual(self.rail["modes"], ["tube"])
        self.assertEqual(self.rail["lines"], ["District"])
        self.assertEqual(self.rail["duration_min"], 32)

    def test_bus_plan_uses_bus_only(self):
        self.assertEqual(self.bus["modes"], ["bus"])
        self.assertEqual(self.bus["lines"], ["17", "736"])

    def test_changes_is_transit_legs_minus_one(self):
        self.assertEqual(self.rail["transit_legs"], 1)
        self.assertEqual(self.rail["changes"], 0)
        self.assertEqual(self.bus["transit_legs"], 2)
        self.assertEqual(self.bus["changes"], 1)

    def test_walking_minutes_and_the_first_leg(self):
        self.assertEqual(self.rail["first_leg_walk_min"], 17)
        self.assertEqual(self.rail["walking_min"], 28)
        self.assertEqual(self.bus["first_leg_walk_min"], 0)

    def test_leg_shape(self):
        leg = self.rail["legs"][1]
        for k in ("mode", "line", "from", "to", "duration_min", "departure", "arrival"):
            self.assertIn(k, leg)
        self.assertEqual(leg["mode"], "tube")
        self.assertEqual(leg["line"], "District")
        self.assertTrue(leg["from"].startswith("Cannon Street"))
        self.assertTrue(leg["to"].startswith("Temple"))

    def test_walking_legs_carry_no_line(self):
        self.assertIsNone(self.rail["legs"][0]["line"])

    def test_zero_wait_connections_are_flagged(self):
        self.assertEqual(self.rail["zero_wait_joins"], 2)
        self.assertIsNotNone(self.rail["wait_sample_note"])
        self.assertIn("zero-wait", self.rail["wait_sample_note"])

    def test_real_waiting_time_is_counted_when_the_plan_has_any(self):
        self.assertEqual(self.bus["waiting_min_in_plan"], 4)

    def test_a_plan_with_no_zero_wait_join_has_no_note(self):
        j = {"duration": 10, "legs": [
            {"duration": 5, "mode": {"id": "walking"},
             "departureTime": "2026-09-07T08:00:00", "arrivalTime": "2026-09-07T08:05:00"},
            {"duration": 5, "mode": {"id": "tube"},
             "departureTime": "2026-09-07T08:09:00", "arrivalTime": "2026-09-07T08:14:00"}]}
        p = commute.parse_journey(j)
        self.assertIsNone(p["wait_sample_note"])
        self.assertEqual(p["waiting_min_in_plan"], 4)

    def test_door_buffer_is_applied_only_when_asked(self):
        plain = commute.parse_journey_response(read("commute-journey-SE1-to-WC2R-all.json"))
        buffered = commute.parse_journey_response(
            read("commute-journey-SE1-to-WC2R-all.json"), door_buffer_min=3)
        self.assertEqual(plain["door_buffer_min"], 0)
        self.assertEqual(plain["duration_min"], plain["duration_min_before_buffer"])
        self.assertEqual(buffered["duration_min"], plain["duration_min"] + 3)
        self.assertEqual(buffered["duration_min_before_buffer"], plain["duration_min"])

    def test_disambiguation_is_reported_not_guessed(self):
        p = commute.parse_journey_response(read("commute-journey-disambiguation.json"))
        self.assertFalse(p["ok"])
        self.assertIn("fromLocationDisambiguation", p["disambiguation"])
        self.assertTrue(p["disambiguation"]["fromLocationDisambiguation"])

    def test_empty_response(self):
        p = commute.parse_journey_response({"journeys": []})
        self.assertFalse(p["ok"])

    def test_non_object_response(self):
        self.assertFalse(commute.parse_journey_response([])["ok"])


class TestStopPointParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.dropped = commute.parse_stoppoints(
            read("commute-stoppoints-london-bridge-r800.json"), 51.504963, -0.087625)

    def test_stations_found_and_sorted_by_distance(self):
        self.assertEqual(len(self.items), 6)
        d = [s["straight_line_m"] for s in self.items]
        self.assertEqual(d, sorted(d))
        self.assertEqual(self.items[0]["name"], "London Bridge Rail Station")

    def test_a_bus_only_pier_filed_under_a_station_stop_type_is_dropped(self):
        self.assertEqual(len(self.dropped), 1)
        self.assertEqual(self.dropped[0]["stop_type"], "NaptanFerryPort")
        self.assertEqual(self.dropped[0]["modes"], ["bus"])

    def test_walk_estimate_is_the_straight_line_times_the_factor(self):
        s = self.items[0]
        self.assertEqual(s["walk_m_estimate"], round(s["straight_line_m"] * commute.WALK_FACTOR))
        self.assertAlmostEqual(s["walk_min_estimate"],
                               round(s["walk_m_estimate"] / commute.WALK_M_PER_MIN, 1), places=1)

    def test_tfl_distance_is_used_and_the_haversine_is_reported_beside_it(self):
        s = self.items[0]
        self.assertEqual(s["straight_line_source"], "tfl")
        self.assertGreater(s["straight_line_m"], s["haversine_m"])

    def test_haversine_is_the_fallback_when_tfl_omits_distance(self):
        obj = {"stopPoints": [{"commonName": "X", "stopType": "NaptanMetroStation",
                               "modes": ["tube"], "lat": 51.505019, "lon": -0.086092}]}
        items, _ = commute.parse_stoppoints(obj, 51.504963, -0.087625)
        self.assertEqual(items[0]["straight_line_source"], "haversine")
        self.assertAlmostEqual(items[0]["straight_line_m"], 106, delta=2)

    def test_modes_and_lines_are_kept(self):
        tube = [s for s in self.items if s["name"] == "London Bridge Underground Station"][0]
        self.assertEqual(tube["modes"], ["tube"])
        self.assertEqual(tube["lines"], ["Jubilee", "Northern"])

    def test_empty_response(self):
        self.assertEqual(commute.parse_stoppoints({"stopPoints": []}, 51.5, -0.1), ([], []))


class TestRedundancyGrading(unittest.TestCase):
    def grade(self, stations, bus=None):
        return commute.grade_redundancy(stations, bus)

    def test_grade_a_both_families_within_800m(self):
        g = self.grade([stn("Tube", ["tube"], 300), stn("Rail", ["national-rail"], 500)])
        self.assertEqual(g["grade"], "A")
        self.assertEqual(g["nearest_family_walk_m"], 300)
        self.assertEqual(g["second_family_walk_m"], 500)

    def test_grade_b_second_family_between_800_and_1600(self):
        g = self.grade([stn("Tube", ["tube"], 300), stn("Ovg", ["overground"], 1200)])
        self.assertEqual(g["grade"], "B")

    def test_grade_b_minus_second_family_beyond_1600(self):
        g = self.grade([stn("Tube", ["tube"], 300), stn("Liz", ["elizabeth-line"], 1800)])
        self.assertEqual(g["grade"], "B-")

    def test_grade_b_minus_one_family_plus_a_bus(self):
        g = self.grade([stn("Tube", ["tube"], 300)], bus=[stn("Stop", ["bus"], 200)])
        self.assertEqual(g["grade"], "B-")
        self.assertIn("bus", g["reason"])

    def test_grade_c_one_family_and_no_bus(self):
        g = self.grade([stn("Tube", ["tube"], 300)], bus=[])
        self.assertEqual(g["grade"], "C")

    def test_two_lines_of_the_same_family_are_not_redundancy(self):
        # Tube plus DLR are both family A; that is one family, not two.
        g = self.grade([stn("Tube", ["tube"], 200), stn("DLR", ["dlr"], 400)], bus=[])
        self.assertEqual(g["grade"], "C")
        self.assertIsNone(g["second_family_walk_m"])
        self.assertIn("strike", g["explanation"])

    def test_river_bus_is_not_a_rail_family(self):
        g = self.grade([stn("Tube", ["tube"], 300), stn("Pier", ["river-bus"], 200)], bus=[])
        self.assertEqual(g["grade"], "C")
        self.assertEqual(g["families"]["family_C"]["nearest"], "Pier")
        self.assertIsNone(g["second_family_walk_m"])

    def test_grade_c_when_the_nearest_family_is_beyond_800m(self):
        g = self.grade([stn("Tube", ["tube"], 1000), stn("Rail", ["national-rail"], 1200)])
        self.assertEqual(g["grade"], "C")

    def test_grade_c_when_nothing_is_found(self):
        g = self.grade([])
        self.assertEqual(g["grade"], "C")
        self.assertIsNone(g["nearest_family_walk_m"])

    def test_bus_check_is_requested_only_when_it_could_change_the_grade(self):
        self.assertTrue(self.grade([stn("Tube", ["tube"], 300)])["needs_bus_check"])
        self.assertFalse(self.grade([stn("Tube", ["tube"], 300),
                                     stn("Rail", ["national-rail"], 500)])["needs_bus_check"])

    def test_nearest_of_each_family_wins(self):
        fams = commute.nearest_by_family([stn("Far", ["tube"], 900), stn("Near", ["dlr"], 200)])
        self.assertEqual(fams["family_A"]["name"], "Near")

    def test_grading_the_real_london_bridge_fixture(self):
        items, _ = commute.parse_stoppoints(
            read("commute-stoppoints-london-bridge-r800.json"), 51.504963, -0.087625)
        g = commute.grade_redundancy(items)
        self.assertEqual(g["grade"], "A")
        self.assertEqual(g["families"]["family_A"]["nearest"], "London Bridge Underground Station")
        self.assertEqual(g["families"]["family_B"]["nearest"], "London Bridge Rail Station")
        self.assertEqual(g["families"]["family_C"]["nearest"], "London Bridge City Pier")

    def test_grading_the_real_canary_wharf_fixture(self):
        items, _ = commute.parse_stoppoints(
            read("commute-stoppoints-canary-wharf-r900.json"), 51.5054, -0.0235)
        g = commute.grade_redundancy(items)
        self.assertEqual(g["grade"], "A")
        self.assertEqual(g["families"]["family_A"]["nearest"], "Canary Wharf DLR Station")
        self.assertIn("elizabeth-line", g["families"]["family_B"]["modes"])

    def test_family_of_maps_modes_to_families(self):
        self.assertEqual(commute._family_of(["dlr"]), "family_A")
        self.assertEqual(commute._family_of(["elizabeth-line"]), "family_B")
        self.assertEqual(commute._family_of(["river-bus"]), "family_C")
        self.assertIsNone(commute._family_of(["bus"]))


if __name__ == "__main__":
    unittest.main()
