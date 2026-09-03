"""Offline tests for scripts/sweep.py (the area-sweep orchestrator).

Run: python3 -m unittest tests/test_sweep.py

Nothing here touches the network. The synthetic inputs are shaped like the real
ones: address strings copied from the energy-register search fixture, an Overpass
answer in the same shape roads.py parses, and a candidate record in the shape
stage 3 builds.
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import _fetch  # noqa: E402
import epc     # noqa: E402
import roads   # noqa: E402
import sweep   # noqa: E402

FIX = os.path.join(HERE, "fixtures")
TEMPLATE = os.path.join(HERE, "..", "skills", "vet-flat", "profile.template.yaml")


# ------------------------------------------------------- address parsing ----
class TestParseAddress(unittest.TestCase):
    def test_flat_number_street_postcode(self):
        p = sweep.parse_address("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG")
        self.assertEqual(p["flat"], "Flat 5")
        self.assertEqual(p["building_number"], "4")
        self.assertEqual(p["street"], "London Bridge Street")
        self.assertEqual(p["postcode"], "SE1 9SG")
        self.assertEqual(p["outcode"], "SE1")
        self.assertEqual(p["town"], "London")

    def test_building_name_with_no_street(self):
        p = sweep.parse_address("Apartment 1, The Shard, LONDON, SE1 9SG")
        self.assertEqual(p["building_name"], "The Shard")
        self.assertIsNone(p["street"])
        self.assertIsNone(p["building_number"])

    def test_name_and_numbered_street(self):
        p = sweep.parse_address("Flat 3, Tower Court, 12 High Street, LONDON, SE1 1AA")
        self.assertEqual(p["building_name"], "Tower Court")
        self.assertEqual(p["building_number"], "12")
        self.assertEqual(p["street"], "High Street")

    def test_house_with_no_flat(self):
        p = sweep.parse_address("12 Snowsfields, London, SE1 3SU")
        self.assertIsNone(p["flat"])
        self.assertEqual(p["building_number"], "12")
        self.assertEqual(p["street"], "Snowsfields")

    def test_a_missing_postcode_is_null_not_a_guess(self):
        p = sweep.parse_address("Flat 5, 4 London Bridge Street, LONDON")
        self.assertIsNone(p["postcode"])
        self.assertIsNone(p["outcode"])

    def test_empty_input_never_raises(self):
        self.assertEqual(sweep.parse_address("")["raw"], "")
        self.assertIsNone(sweep.parse_address(None)["postcode"])

    def test_postcode_is_normalised_to_one_space_upper_case(self):
        pc, outcode = sweep.normalise_postcode("se1  9sg")
        self.assertEqual(pc, "SE1 9SG")
        self.assertEqual(outcode, "SE1")


# ---------------------------------------------------------- grouping key ----
class TestBuildingKey(unittest.TestCase):
    def key(self, address, street=None):
        return sweep.building_key(sweep.parse_address(address), street)

    def test_two_flats_in_one_building_are_one_key(self):
        a = self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG")
        b = self.key("FLAT 16, 4 London Bridge Street, LONDON, SE1 9SG")
        self.assertEqual(a, b)

    def test_the_flat_number_is_never_in_the_key(self):
        self.assertNotIn("5", self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG")
                         .replace("4--", ""))

    def test_different_buildings_on_one_street_are_different_keys(self):
        a = self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG")
        b = self.key("Flat 5, 30 London Bridge Street, LONDON, SE1 9SG")
        self.assertNotEqual(a, b)

    def test_a_number_range_normalises_to_its_first_number(self):
        a = self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG")
        b = self.key("Flat 16, 4-6 London Bridge Street, LONDON, SE1 9SG")
        self.assertEqual(a, b)

    def test_a_street_abbreviation_does_not_split_a_building(self):
        a = self.key("Flat 1, 12 Weston Rd, LONDON, SE1 3QB")
        b = self.key("Flat 2, 12 Weston Road, LONDON, SE1 3QB")
        self.assertEqual(a, b)

    def test_a_saint_prefix_is_not_a_street_type(self):
        """St. Thomas Street is Saint Thomas, not Street Thomas: only the last word
        of a British street name is a street type."""
        k = self.key("Flat 1, 9 St. Thomas Street, LONDON, SE1 9RY")
        self.assertEqual(k, "9--st-thomas-street--se1")
        self.assertEqual(k, self.key("Flat 2, 9 St Thomas St, LONDON, SE1 9RY"))

    def test_the_same_building_in_two_outcodes_is_two_keys(self):
        a = self.key("Flat 1, 12 High Street, LONDON, SE1 1AA")
        b = self.key("Flat 1, 12 High Street, LONDON, E1 1AA")
        self.assertNotEqual(a, b)

    def test_the_certificate_street_beats_the_street_that_was_searched(self):
        """A building found twice - by the street census and by a postcode - must
        land on one key, so the key cannot depend on how it was found."""
        a = self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG", "London Bridge Street")
        b = self.key("Flat 5, 4 London Bridge Street, LONDON, SE1 9SG", None)
        self.assertEqual(a, b)

    def test_a_name_only_address_falls_back_to_the_street_searched(self):
        k = self.key("Apartment 1, The Shard, LONDON, SE1 9SG", "London Bridge Street")
        self.assertIn("the-shard", k)
        self.assertIn("london-bridge-street", k)

    def test_the_key_is_a_safe_file_name(self):
        k = self.key("Flat 1, 12 St. Thomas' Street, LONDON, SE1 9RY")
        self.assertRegex(k, r"^[a-z0-9-]+$")
        self.assertNotIn("/", k)
        self.assertNotIn(" ", k)

    def test_the_register_fixture_groups_into_the_buildings_a_reader_would_see(self):
        with open(os.path.join(FIX, "epc-search-SE1-9SG.html"), encoding="utf-8") as fh:
            body = fh.read()
        import re
        addresses = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
            if not epc.CERT_RE.search(tr):
                continue
            a = re.search(r"<a[^>]*href=\"/energy-certificate/[0-9-]+\"[^>]*>(.*?)</a>", tr, re.S)
            if a:
                addresses.append(epc._clean(a.group(1)))
        self.assertGreater(len(addresses), 10)
        keys = {}
        for addr in addresses:
            keys.setdefault(self.key(addr, "London Bridge Street"), []).append(addr)
        # ten Shard apartments are one building, not ten
        shard = [v for k, v in keys.items() if k.startswith("the-shard")]
        self.assertEqual(len(shard), 1)
        self.assertEqual(len(shard[0]), 10)
        self.assertLess(len(keys), len(addresses))


class TestSameBuilding(unittest.TestCase):
    def test_identical_keys_match(self):
        self.assertTrue(sweep.same_building("4--high-street--se1", "4--high-street--se1"))

    def test_a_user_line_with_no_postcode_still_matches_one_building(self):
        want = sweep.building_key(sweep.parse_address("4 London Bridge Street"))
        got = sweep.building_key(sweep.parse_address(
            "Flat 5, 4 London Bridge Street, LONDON, SE1 9SG"))
        self.assertNotEqual(want, got)
        self.assertTrue(sweep.same_building(want, got))

    def test_a_different_building_in_the_same_postcode_does_not_match(self):
        want = sweep.building_key(sweep.parse_address("4 London Bridge Street"))
        other = sweep.building_key(sweep.parse_address(
            "Flat 5, 30 London Bridge Street, LONDON, SE1 9SG"))
        self.assertFalse(sweep.same_building(want, other))

    def test_two_outcodes_never_match(self):
        self.assertFalse(sweep.same_building("4--high-street--se1", "4--high-street--e1"))


def building(key, display, certs=1, postcodes=("SE1 9SG",), distance=100.0):
    return {"key": key, "display_address": display, "certificate_count": certs,
            "certificates": [{"certificate_id": "%s-%d" % (key, i)} for i in range(certs)],
            "postcodes": list(postcodes), "distance_m": distance,
            "coordinates": {"lat": 51.5, "lng": -0.08}, "user_supplied": False,
            "excluded_code": None, "excluded_reason": None,
            "building_name": None, "building_number": None, "street": None,
            "outcode": "SE1", "sample_certificate_ids": []}


class TestMergeAbbreviatedStreets(unittest.TestCase):
    """The register writes "4 London Bridge Street" and "4 London Bridge" for the
    same block, so one building arrives as two candidates unless they are reunited."""

    def test_the_longer_spelling_wins_and_keeps_every_certificate(self):
        a = building("4--london-bridge-street--se1", "4 London Bridge Street, SE1 9SG", certs=3)
        b = building("4--london-bridge--se1", "4 London Bridge, SE1 9SG", certs=1,
                     distance=50.0)
        kept, merges = sweep.merge_abbreviated_streets([a, b])
        self.assertEqual([k["key"] for k in kept], ["4--london-bridge-street--se1"])
        self.assertEqual(kept[0]["certificate_count"], 4)
        self.assertEqual(len(kept[0]["certificates"]), 4)
        self.assertEqual(kept[0]["distance_m"], 50.0, "the nearer reading survives")
        self.assertEqual(merges, [{"merged": "4--london-bridge--se1",
                                   "into": "4--london-bridge-street--se1"}])
        self.assertEqual(kept[0]["merged_from"][0]["key"], "4--london-bridge--se1")

    def test_a_different_building_number_never_merges(self):
        a = building("4--london-bridge-street--se1", "4 London Bridge Street, SE1 9SG")
        b = building("30--london-bridge--se1", "30 London Bridge, SE1 9SG")
        kept, merges = sweep.merge_abbreviated_streets([a, b])
        self.assertEqual(len(kept), 2)
        self.assertEqual(merges, [])

    def test_a_different_outcode_never_merges(self):
        a = building("4--london-bridge-street--se1", "x")
        b = building("4--london-bridge--e1", "y")
        kept, _ = sweep.merge_abbreviated_streets([a, b])
        self.assertEqual(len(kept), 2)

    def test_an_unrelated_street_that_merely_starts_the_same_does_not_merge(self):
        a = building("4--high-street-north--se1", "x")
        b = building("4--high-road--se1", "y")
        kept, _ = sweep.merge_abbreviated_streets([a, b])
        self.assertEqual(len(kept), 2)

    def test_a_user_supplied_flag_survives_the_merge(self):
        a = building("4--london-bridge-street--se1", "x")
        b = building("4--london-bridge--se1", "y")
        b["user_supplied"] = True
        kept, _ = sweep.merge_abbreviated_streets([a, b])
        self.assertEqual(len(kept), 1)
        self.assertTrue(kept[0]["user_supplied"])

    def test_three_spellings_collapse_to_the_longest(self):
        a = building("4--london-bridge-street--se1", "x", certs=2)
        b = building("4--london-bridge--se1", "y", certs=1)
        c = building("4--london--se1", "z", certs=1)
        kept, merges = sweep.merge_abbreviated_streets([a, b, c])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["certificate_count"], 4)
        self.assertEqual(len(merges), 2)

    def test_nothing_to_merge_leaves_the_list_alone(self):
        rows = [building("4--a-street--se1", "x"), building("6--b-street--se1", "y")]
        kept, merges = sweep.merge_abbreviated_streets(rows)
        self.assertEqual(len(kept), 2)
        self.assertEqual(merges, [])


# ------------------------------------------------------------- exclusions ---
class TestExclusions(unittest.TestCase):
    def test_hotel(self):
        code, why = sweep.exclusion_for("Flat 200, London Bridge Hotel, SE1 9SG")
        self.assertEqual(code, "hotel_or_hostel")
        self.assertIn("Hotel", why)

    def test_student_and_halls(self):
        self.assertEqual(sweep.exclusion_for("Chapter Student Village")[0],
                         "student_accommodation")
        self.assertEqual(sweep.exclusion_for("Nightingale Hall of Residence")[0],
                         "student_accommodation")

    def test_serviced_and_aparthotel(self):
        self.assertEqual(sweep.exclusion_for("Serviced Apartments, 1 High Street")[0],
                         "serviced_apartments")
        self.assertEqual(sweep.exclusion_for("City Aparthotel")[0], "serviced_apartments")
        self.assertEqual(sweep.exclusion_for("Riverside Short Stay Suites")[0],
                         "serviced_apartments")

    def test_care_and_retirement(self):
        self.assertEqual(sweep.exclusion_for("Sunnyside Care Home")[0], "care_or_retirement")
        self.assertEqual(sweep.exclusion_for("Elm Retirement Village")[0], "care_or_retirement")
        self.assertEqual(sweep.exclusion_for("Sheltered Housing, 4 Elm Road")[0],
                         "care_or_retirement")

    def test_ordinary_buildings_are_left_alone(self):
        for name in ["The Shard", "12 Snowsfields", "Gray's Inn Road", "Tower Court",
                     "Chapter House", "Innisfree Court", "Hotelier Way"[:0] or "Bermondsey Wall"]:
            self.assertIsNone(sweep.exclusion_for(name), name)

    def test_every_documented_pattern_compiles_and_has_a_reason(self):
        self.assertEqual(len(sweep.EXCLUSION_PATTERNS), len(sweep._EXCLUSION_RE))
        for name, pattern, why in sweep.EXCLUSION_PATTERNS:
            self.assertTrue(name and pattern and why)
            self.assertGreater(len(why), 20, name)

    def test_exclusion_matches_across_the_whole_address(self):
        self.assertIsNotNone(sweep.exclusion_for("Flat 2", "Ivy Nursing Home, SE1 1AA"))


# ------------------------------------------------------- building profile ---
def cert(area_m2=50.0, year=2016, heating="gas_boiler", floor="mid", perm=None,
         atype="SAP", ok=True):
    return {"ok": ok, "total_floor_area_m2": area_m2,
            "total_floor_area_sqft": int(round(area_m2 * 10.7639)) if area_m2 else None,
            "first_assessment_year": year, "heating_class": heating,
            "floor_position": floor, "air_permeability": perm, "assessment_type": atype}


class TestBuildingProfile(unittest.TestCase):
    def test_median_area_year_and_shares(self):
        certs = [cert(40.0, 2018), cert(50.0, 2016), cert(60.0, 2019, floor="ground")]
        bp = sweep.building_profile(certs)
        self.assertEqual(bp["certificates_parsed"], 3)
        self.assertEqual(bp["floor_area_m2_median"], 50.0)
        self.assertEqual(bp["earliest_assessment_year"], 2016)
        self.assertEqual(bp["ground_floor_count"], 1)
        self.assertAlmostEqual(bp["ground_floor_share"], 0.33, places=2)
        self.assertEqual(bp["heating_classes"], {"gas_boiler": 3})

    def test_unreadable_certificates_are_excluded_from_every_number(self):
        bp = sweep.building_profile([cert(ok=False), cert(ok=False)])
        self.assertEqual(bp["certificates_sampled"], 2)
        self.assertEqual(bp["certificates_parsed"], 0)
        self.assertIsNone(bp["floor_area_sqft_median"])
        self.assertIsNone(bp["earliest_assessment_year"])
        self.assertIsNone(bp["ground_floor_share"])


class TestHardFilter(unittest.TestCase):
    YEAR = 2026

    def prof(self, **kw):
        p = dict(sweep.PERMISSIVE_PROFILE)
        p.update(kw)
        return p

    def test_permissive_profile_filters_nothing(self):
        bp = sweep.building_profile([cert(30.0, 1900)])
        out = sweep.hard_filter(self.prof(), bp, self.YEAR)
        self.assertTrue(out["pass"])
        self.assertEqual(out["checks"], [])

    def test_building_age_fails_an_old_block(self):
        bp = sweep.building_profile([cert(50.0, 1999)])
        out = sweep.hard_filter(self.prof(max_building_age_years=20), bp, self.YEAR)
        self.assertFalse(out["pass"])
        self.assertEqual(out["checks"][0]["pass"], False)
        self.assertIn("1999", out["checks"][0]["observed"])

    def test_building_age_passes_a_new_block(self):
        bp = sweep.building_profile([cert(50.0, 2019)])
        out = sweep.hard_filter(self.prof(max_building_age_years=20), bp, self.YEAR)
        self.assertTrue(out["pass"])
        self.assertIs(out["checks"][0]["pass"], True)

    def test_an_unknown_age_is_unknown_and_never_a_pass(self):
        bp = sweep.building_profile([cert(50.0, None)])
        out = sweep.hard_filter(self.prof(max_building_age_years=20), bp, self.YEAR)
        self.assertEqual(out["checks"][0]["pass"], "unknown")
        self.assertEqual(out["checks"][0]["evidence_class"], "U")
        self.assertTrue(out["pass"], "an unknown must not drop the building silently")
        self.assertTrue(out["unknowns"])

    def test_one_big_enough_flat_keeps_the_whole_building(self):
        bp = sweep.building_profile([cert(30.0), cert(30.0), cert(60.0)])
        out = sweep.hard_filter(self.prof(min_floor_area_sqft=500), bp, self.YEAR)
        self.assertTrue(out["pass"])
        self.assertIs(out["checks"][0]["pass"], True)

    def test_a_building_of_only_small_flats_fails(self):
        bp = sweep.building_profile([cert(30.0), cert(35.0)])
        out = sweep.hard_filter(self.prof(min_floor_area_sqft=500), bp, self.YEAR)
        self.assertFalse(out["pass"])
        self.assertIn("Indoor floor area", out["fail_reasons"][0])

    def test_ground_floor_is_a_per_flat_filter_not_a_building_filter(self):
        bp = sweep.building_profile([cert(floor="ground"), cert(floor="mid")])
        out = sweep.hard_filter(self.prof(reject_ground_floor=True), bp, self.YEAR)
        self.assertTrue(out["pass"])
        self.assertIn("per flat", out["checks"][0]["observed"])

    def test_an_all_ground_floor_building_does_fail(self):
        bp = sweep.building_profile([cert(floor="ground"), cert(floor="basement")])
        out = sweep.hard_filter(self.prof(reject_ground_floor=True), bp, self.YEAR)
        self.assertFalse(out["pass"])

    def test_no_readable_certificate_is_a_hard_fail(self):
        bp = sweep.building_profile([cert(ok=False)])
        out = sweep.hard_filter(self.prof(), bp, self.YEAR)
        self.assertFalse(out["pass"])
        self.assertIn("Residential certificates", out["fail_reasons"][0])

    def test_every_row_has_the_report_schema_shape(self):
        bp = sweep.building_profile([cert(60.0, 2010, floor="ground")])
        out = sweep.hard_filter(self.prof(min_floor_area_sqft=400, max_building_age_years=30,
                                          reject_ground_floor=True), bp, self.YEAR)
        self.assertEqual(len(out["checks"]), 3)
        for row in out["checks"]:
            self.assertEqual(sorted(row), ["evidence_class", "name", "observed", "pass",
                                           "requirement"])
            self.assertIn(row["pass"], (True, False, "unknown"))
            self.assertTrue(row["observed"], "an unfound value is words, never a dash")


# ------------------------------------------------------------- 4 KB cap -----
def fat_record():
    return {
        "key": "k", "display_address": "1 Example Street, SE1 9SG", "distance_m": 120.0,
        "postcodes": ["SE1 9SG", "SE1 9SH", "SE1 9SJ", "SE1 9SL", "SE1 9SN"],
        "coordinates": {"lat": 51.5, "lng": -0.08, "provenance": "postcode centroid " * 5},
        "epc": {"source_url": "https://find-energy-certificate.service.gov.uk/",
                "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G",
                "sample_certificate_ids": ["1111-2222-3333-4444-%04d" % i
                                           for i in range(8)],
                "certificates_in_building": 96, "certificates_sampled": 8,
                "floor_area_sqft_max": 780, "air_permeability_median": 4.2,
                "heating_classes": {"community_heat_network": 6, "electric": 2},
                "ground_floor_share": 0.12,
                "assessment_types": {"SAP": 6, "RdSAP": 2},
                "floor_area_sqft_median": 520, "earliest_assessment_year": 2016},
        "crime": {"source_url": "https://data.police.uk/api/crimes-street/all-crime",
                  "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G", "total": 300,
                  "months": 6,
                  "half_m": 150, "predatory_count": 180, "predatory_share": 0.6,
                  "top_anchor_share": 0.24, "months_missing": [], "sensitivity_spread": 42,
                  "window": "2026-01..2026-06",
                  "box": "square of side 300 m centred on the coordinates above",
                  "top_anchors": [{"anchor": "On or near Somewhere Long Name %d" % i,
                                   "count": 30 - i} for i in range(5)],
                  "by_category": {"cat-%d" % i: 20 - i for i in range(14)}},
        "commute": {"source_url": "https://api.tfl.gov.uk/Journey/x",
                    "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G",
                    "all_min": 27, "rail_min": 32, "changes": 1, "walking_min": 18,
                    "to": "WC2R 2LS", "arrive_by": "09:00",
                    "redundancy_grade": "A", "nearest_family_walk_m": 169,
                    "second_family_walk_m": 301,
                    "redundancy_reason": "Both families are within an 800 m walk, so a "
                                         "strike on one leaves the other standing.",
                    "legs": ["tube Northern", "walking ", "rail Southeastern"] * 3},
        "planning": {"source_url": "https://planningdata.london.gov.uk/x",
                     "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G",
                     "nearest": [{"reference": "26/AP/%04d" % i, "distance_m": i,
                                  "status": "Approved", "tall": False,
                                  "what": "A long description of the works " * 2}
                                 for i in range(3)]},
        "roads": {"source_url": "https://overpass-api.de/api/interpreter",
                  "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "C",
                  "radius_m": 300,
                  "trunk_or_primary": {"distance_m": 142, "name": "Tooley Street"},
                  "secondary": {"distance_m": 60, "name": "Snowsfields"},
                  "railway_surface": {"distance_m": 62, "name": "South Eastern Main Line"},
                  "night_economy": {"distance_m": 11, "name": "A Bar With A Long Name"},
                  "supermarket": {"distance_m": 32, "name": "A Supermarket Name"},
                  "park_or_green": {"distance_m": 139, "name": "Guy Street Park"},
                  "not_mapped": ["tube_surface", "waste_or_recycling"],
                  "facade_note": "the building has a road-facing and a quiet side; ask "
                                 "which side the flat's windows face",
                  "obstruction": [{"name": "Neighbour %d" % i, "distance_m": i,
                                   "angle_deg": 60} for i in range(3)]},
        "land_registry": {"source_url": "https://landregistry.data.gov.uk/landregistry/query",
                          "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G",
                          "postcode": "SE1 9SG", "transactions": 101, "new_build_count": 3,
                          "earliest_new_build_year": 1998},
        "companies": {"source_url": "https://find-and-update.company-information.service.gov"
                                    ".uk/advanced-search/get-results?registeredOffice=SE1+9SG",
                      "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G",
                      "postcode": "SE1 9SG", "companies_at_address": 20, "rmc_rtm_count": 0,
                      "rmc_rtm_names": [], "inference": "zero resident management company"},
        "metrics": sweep.build_metrics({"crime": {"total": 300, "months": 6},
                                        "commute": {"all_min": 27, "redundancy_grade": "A"},
                                        "planning": {"nearest_tall": {"distance_m": 61}}},
                                       {"_n": 3, "crime_total": 250, "commute_min": 30,
                                        "works_m": 100, "grades": "A x3"}),
        "metrics_not_measured": sweep.METRICS_NOT_MEASURED,
    }


class TestFitToBudget(unittest.TestCase):
    def test_a_small_record_is_returned_untouched(self):
        rec = {"key": "k", "metrics": {}}
        out = sweep.fit_to_budget(rec)
        self.assertEqual(out, rec)
        self.assertNotIn("trimmed", out)

    def test_a_fat_record_is_brought_under_the_cap(self):
        rec = fat_record()
        self.assertGreater(sweep.json_bytes(rec), sweep.CANDIDATE_BUDGET_BYTES)
        out = sweep.fit_to_budget(rec)
        self.assertLessEqual(sweep.json_bytes(out), sweep.CANDIDATE_BUDGET_BYTES)

    def test_the_input_record_is_not_mutated(self):
        rec = fat_record()
        before = copy.deepcopy(rec)
        sweep.fit_to_budget(rec)
        self.assertEqual(rec, before)

    def test_what_was_dropped_is_recorded_in_the_record_and_in_the_log(self):
        log = []
        out = sweep.fit_to_budget(fat_record(), log=log)
        self.assertIn("trimmed", out)
        self.assertIn("dropped to fit", out["trimmed"])
        self.assertTrue(log)
        self.assertIn("commute.legs", log)
        # the marker must not itself be the biggest thing in the file
        self.assertLess(len(out["trimmed"]), 220)

    def test_metrics_and_provenance_survive_the_trim(self):
        out = sweep.fit_to_budget(fat_record())
        self.assertEqual(out["metrics"]["crime_6mo_count"]["value"], 300)
        for block in ("epc", "crime", "commute", "planning", "roads"):
            self.assertIn("source_url", out[block], block)
            self.assertIn("retrieved_at", out[block], block)
            self.assertIn("evidence_class", out[block], block)

    def test_lists_are_cut_before_facts_are_dropped(self):
        rec = fat_record()
        out = sweep.fit_to_budget(rec, budget=3000)
        self.assertLessEqual(sweep.json_bytes(out), 3000)
        self.assertEqual(out["crime"]["total"], 300)
        self.assertEqual(out["epc"]["floor_area_sqft_median"], 520)

    def test_a_hopeless_budget_still_returns_a_record_and_says_so(self):
        out = sweep.fit_to_budget(fat_record(), budget=200)
        self.assertIn("STILL OVER BUDGET", out["trimmed"])
        self.assertIn("metrics", out)

    def test_the_trim_steps_only_name_reachable_paths(self):
        rec = fat_record()
        reachable = 0
        for path, action, n in sweep.TRIM_STEPS:
            self.assertIn(action, ("drop", "list", "dict"), path)
            self.assertLessEqual(len(path.split(".")), 2, path)
            parent, key = sweep._dig(rec, path)
            if parent is not None:
                reachable += 1
        self.assertGreater(reachable, len(sweep.TRIM_STEPS) * 0.7,
                           "most trim paths should exist in a real stage-3 record")


# --------------------------------------------------------------- medians ----
class TestSweepMedians(unittest.TestCase):
    def records(self):
        def rec(crime, commute, rail, sqft, year, dist, tall, grade):
            return {"key": "k%d" % dist, "distance_m": dist,
                    "epc": {"floor_area_sqft_median": sqft, "earliest_assessment_year": year},
                    "crime": {"total": crime},
                    "commute": {"all_min": commute, "rail_min": rail,
                                "redundancy_grade": grade},
                    "planning": {"nearest_tall": {"distance_m": tall}}}
        return [rec(100, 20, 25, 400, 2010, 100, 50, "A"),
                rec(200, 30, 35, 500, 2014, 200, 150, "A"),
                rec(300, 40, 45, 600, 2018, 300, 250, "B")]

    def test_odd_count_takes_the_middle(self):
        med = sweep.sweep_medians(self.records())
        self.assertEqual(med["_n"], 3)
        self.assertEqual(med["crime_total"], 200)
        self.assertEqual(med["commute_min"], 30)
        self.assertEqual(med["area_sqft"], 500)
        self.assertEqual(med["earliest_year"], 2014)
        self.assertEqual(med["works_m"], 150)

    def test_even_count_averages_the_middle_pair(self):
        self.assertEqual(sweep.median([1, 2, 3, 4]), 2.5)

    def test_missing_values_are_skipped_not_counted_as_zero(self):
        recs = self.records()
        recs[0]["crime"] = {}
        med = sweep.sweep_medians(recs)
        self.assertEqual(med["crime_total"], 250)

    def test_no_values_at_all_gives_null_not_zero(self):
        self.assertIsNone(sweep.median([]))
        self.assertIsNone(sweep.median([None, None]))
        med = sweep.sweep_medians([])
        self.assertIsNone(med["crime_total"])
        self.assertIsNone(med["grades"])

    def test_grades_are_counted_not_averaged(self):
        med = sweep.sweep_medians(self.records())
        self.assertEqual(med["grades"], "A x2, B x1")

    def test_the_median_lands_in_compared_to_and_never_in_meaning(self):
        recs = self.records()
        med = sweep.sweep_medians(recs)
        metrics = sweep.build_metrics(recs[0], med)
        self.assertIn("Sweep median 200 crimes", metrics["crime_6mo_count"]["compared_to"])
        self.assertEqual(metrics["crime_6mo_count"]["meaning"], sweep.TODO_MEANING)
        self.assertEqual(metrics["crime_6mo_count"]["value"], 100)

    def test_metrics_use_only_report_schema_keys(self):
        with open(os.path.join(HERE, "..", "skills", "vet-flat", "references",
                               "report-schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        allowed = set(schema["definitions"]["metrics"]["properties"])
        metrics = sweep.build_metrics({}, None)
        self.assertTrue(set(metrics) <= allowed, set(metrics) - allowed)
        for name, measure in metrics.items():
            self.assertTrue(set(measure) <=
                            set(schema["definitions"]["measure"]["properties"]), name)
            for required in ("value", "meaning", "compared_to"):
                self.assertIn(required, measure, name)
                if required != "value":
                    self.assertTrue(measure[required], name)
        for key in ("price_per_sqft_epc", "management_organic_score", "landlord_type"):
            self.assertIn(key, sweep.METRICS_NOT_MEASURED)


class TestSourceList(unittest.TestCase):
    """report-skeleton `sources`: built from the candidate records, so a --resume run
    (which fetches almost nothing) still names everything the report cites."""

    class FakeManifest(object):
        records = [{"url": "https://api.postcodes.io/postcodes/SE19SG", "ok": True,
                    "status": 200, "retrieved_at": "2026-09-03T11:00Z"},
                   {"url": "https://data.police.uk/api/x?poly=1", "ok": False,
                    "status": 500, "retrieved_at": "2026-09-03T11:00Z"}]

    def sources(self):
        rec = {"crime": {"source_url": "https://data.police.uk/api/crimes-street/all-crime",
                         "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "G"},
               "roads": {"source_url": "https://overpass-api.de/api/interpreter",
                         "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "C"}}
        buildings = {"streets": {"source_url": "https://overpass-api.de/api/interpreter",
                                 "retrieved_at": "2026-09-03T11:00Z", "evidence_class": "C"},
                     "generated_at": "2026-09-03T11:00Z"}
        return sweep._sources([rec], buildings, self.FakeManifest())

    def test_every_row_has_what_the_schema_requires(self):
        for row in self.sources():
            for field in ("id", "url", "retrieved_at", "evidence_class"):
                self.assertIn(field, row)
                self.assertTrue(row[field], field)
            self.assertIn(row["evidence_class"], ("G", "S", "C", "I", "U"))

    def test_ids_are_unique(self):
        ids = [r["id"] for r in self.sources()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_one_entry_per_endpoint_not_one_per_call(self):
        urls = [r["url"] for r in self.sources()]
        self.assertEqual(len([u for u in urls if "overpass" in u]), 1)

    def test_a_failed_fetch_is_not_listed_as_a_source(self):
        self.assertFalse(any("poly=1" in r["url"] for r in self.sources()))

    def test_the_evidence_class_of_the_block_is_kept(self):
        overpass = [r for r in self.sources() if "overpass" in r["url"]][0]
        self.assertEqual(overpass["evidence_class"], "C")


# -------------------------------------------------------------- manifest ----
class TestManifest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.orig_fetch = _fetch.fetch
        self.orig_epc_fetch = epc.fetch

        def stub(url, *a, **kw):
            self.calls.append(url)
            bad = "bad" in url
            return {"url": url, "final_url": url, "status": 500 if bad else 200,
                    "content_type": "text/html", "body": "x",
                    "retrieved_at": "2026-09-03T11:00:00+00:00", "from_cache": False,
                    "ok": not bad, "note": "http 500" if bad else ""}
        _fetch.fetch = stub
        epc.fetch = stub

    def tearDown(self):
        _fetch.fetch = self.orig_fetch
        epc.fetch = self.orig_epc_fetch

    def test_every_fetch_is_recorded_with_the_five_required_fields(self):
        man = sweep.Manifest()
        man.install([epc])
        try:
            epc.fetch("https://example.gov.uk/good")
        finally:
            man.remove([epc])
        self.assertEqual(man.total, 1)
        row = man.records[0]
        for field in ("url", "status", "ok", "note", "retrieved_at"):
            self.assertIn(field, row)
        self.assertEqual(row["url"], "https://example.gov.uk/good")
        self.assertEqual(row["status"], 200)
        self.assertTrue(row["ok"])
        self.assertEqual(row["stage"], sweep.CURRENT_STAGE)

    def test_a_failure_is_recorded_and_never_hidden(self):
        man = sweep.Manifest()
        man.install([epc])
        try:
            epc.fetch("https://example.gov.uk/good")
            epc.fetch("https://example.gov.uk/bad")
        finally:
            man.remove([epc])
        self.assertEqual(man.total, 2)
        self.assertEqual(len(man.failures), 1)
        self.assertEqual(man.failures[0]["status"], 500)
        self.assertEqual(man.failures[0]["note"], "http 500")
        self.assertEqual(man.summary()["failures"], 1)
        self.assertEqual(man.summary()["fetches"], 2)

    def test_removing_the_recorder_puts_the_original_back(self):
        man = sweep.Manifest()
        man.install([epc])
        self.assertIsNot(epc.fetch, self.orig_epc_fetch)
        man.remove([epc])
        self.assertIs(epc.fetch, epc.fetch)
        epc.fetch("https://example.gov.uk/good")
        self.assertEqual(man.total, 0)

    def test_the_stage_label_follows_the_run(self):
        man = sweep.Manifest()
        man.install([epc])
        before = sweep.CURRENT_STAGE
        try:
            sweep.CURRENT_STAGE = "s3"
            epc.fetch("https://example.gov.uk/good")
        finally:
            sweep.CURRENT_STAGE = before
            man.remove([epc])
        self.assertEqual(man.records[0]["stage"], "s3")
        self.assertEqual(man.summary()["by_stage"], {"s3": 1})

    def test_cached_reads_are_counted_apart_from_network_calls(self):
        man = sweep.Manifest()
        man.install([epc])
        try:
            epc.fetch("https://example.gov.uk/good")
        finally:
            man.remove([epc])
        man.records[0]["from_cache"] = True
        self.assertEqual(man.network_calls, 0)
        self.assertEqual(man.summary()["from_cache"], 1)


# ------------------------------------------------------------ enumeration ---
OVERPASS_STREETS = {"elements": [
    {"type": "way", "id": 1, "tags": {"highway": "residential", "name": "Weston Street"},
     "geometry": [{"lat": 51.5000, "lon": -0.0860}, {"lat": 51.5010, "lon": -0.0860}]},
    {"type": "way", "id": 2, "tags": {"highway": "residential", "name": "Weston Street"},
     "geometry": [{"lat": 51.5020, "lon": -0.0860}, {"lat": 51.5030, "lon": -0.0860}]},
    {"type": "way", "id": 3, "tags": {"highway": "service", "name": "Bridge Yard"},
     "geometry": [{"lat": 51.5044, "lon": -0.0864}, {"lat": 51.5045, "lon": -0.0864}]},
    {"type": "way", "id": 4, "tags": {"highway": "residential"},         # unnamed: skipped
     "geometry": [{"lat": 51.5045, "lon": -0.0865}, {"lat": 51.5046, "lon": -0.0865}]},
]}


class TestStreetEnumeration(unittest.TestCase):
    def setUp(self):
        self.orig = roads.run_overpass

    def tearDown(self):
        roads.run_overpass = self.orig

    def test_the_query_asks_for_named_ways_only(self):
        q = sweep.overpass_street_query(51.5045, -0.0865, 400)
        self.assertIn("around:400", q)
        self.assertIn('["name"]', q)
        self.assertIn("out geom;", q)
        for highway in sweep.STREET_HIGHWAYS:
            self.assertIn(highway, q)
        self.assertNotIn("motorway", q)

    def test_names_are_deduped_and_sorted_by_distance(self):
        roads.run_overpass = lambda q, **kw: (OVERPASS_STREETS, {
            "source_url": "https://overpass-api.de/api/interpreter", "http_status": 200,
            "ok": True, "note": "", "retrieved_at": "2026-09-03T11:00:00+00:00",
            "overpass_instance": "https://overpass-api.de/api/interpreter", "attempts": []})
        out = sweep.streets_in_circle(51.5045, -0.0865, 400)
        self.assertTrue(out["ok"])
        self.assertEqual([s["name"] for s in out["streets"]], ["Bridge Yard", "Weston Street"])
        self.assertEqual(out["count"], 2)
        self.assertLess(out["streets"][0]["nearest_m"], out["streets"][1]["nearest_m"])
        self.assertIn("OpenStreetMap", out["attribution"])

    def test_a_dead_overpass_is_a_fetch_failure_not_an_empty_area(self):
        roads.run_overpass = lambda q, **kw: (None, {
            "source_url": "https://overpass-api.de/api/interpreter", "http_status": 504,
            "ok": False, "note": "http 504", "retrieved_at": "2026-09-03T11:00:00+00:00",
            "overpass_instance": None, "attempts": []})
        out = sweep.streets_in_circle(51.5045, -0.0865, 400)
        self.assertFalse(out["ok"])
        self.assertEqual(out["streets"], [])
        self.assertIn("not an absence", out["not_found"]["meaning"])


class TestSharedOverpassQuery(unittest.TestCase):
    def test_every_radius_is_widened_by_the_sweep_radius(self):
        q = sweep.overpass_area_query(51.5045, -0.0865, 400, roads_radius=300)
        import re as _re
        widened = sorted({int(m) for m in _re.findall(r"around:(\d+),", q)})
        base = sorted({int(m) for m in _re.findall(
            r"around:(\d+),", roads.build_query(51.5045, -0.0865, radius=300))})
        self.assertEqual(widened, [b + 400 for b in base])

    def test_the_query_timeout_stays_under_the_curl_timeout(self):
        q = sweep.overpass_area_query(51.5045, -0.0865, 400)
        self.assertIn("[timeout:80]", q)

    def test_the_tag_list_is_taken_from_roads_not_copied(self):
        q = sweep.overpass_area_query(51.5045, -0.0865, 0, roads_radius=300)
        self.assertEqual(q.replace("[timeout:80]", "[timeout:40]"),
                         roads.build_query(51.5045, -0.0865, radius=300))


class TestSpread(unittest.TestCase):
    def test_it_spans_the_list_rather_than_taking_the_front(self):
        picked = sweep.spread(list(range(100)), 5)
        self.assertEqual(len(picked), 5)
        self.assertEqual(picked[0], 0)
        self.assertGreater(picked[-1], 70)

    def test_a_short_list_comes_back_whole(self):
        self.assertEqual(sweep.spread([1, 2, 3], 8), [1, 2, 3])

    def test_edges(self):
        self.assertEqual(sweep.spread([], 5), [])
        self.assertEqual(sweep.spread([1, 2], 0), [])

    def test_no_duplicates(self):
        picked = sweep.spread(list(range(7)), 5)
        self.assertEqual(len(set(picked)), len(picked))


# ---------------------------------------------------------------- profile ---
class TestProfile(unittest.TestCase):
    def test_no_profile_means_permissive_defaults_and_says_so(self):
        prof, source, warnings = sweep.read_profile(None)
        self.assertEqual(prof, sweep.PERMISSIVE_PROFILE)
        self.assertIn("permissive", source)
        self.assertEqual(warnings, [])

    def test_a_missing_file_is_a_warning_not_a_crash(self):
        prof, source, warnings = sweep.read_profile("/nowhere/profile.yaml")
        self.assertEqual(prof["min_floor_area_sqft"], None)
        self.assertTrue(warnings)
        self.assertIn("not found", source)

    def test_the_shipped_template_parses(self):  # noqa: D401
        prof, source, warnings = sweep.read_profile(TEMPLATE)
        self.assertIn("profile.template.yaml", source)
        self.assertIs(prof["reject_ground_floor"], True)
        self.assertEqual(prof["arrive_by"], "09:00")
        self.assertEqual(prof["redundancy_min_grade"], "B")
        self.assertIsNone(prof["destination"])
        self.assertTrue(any("blank" in w for w in warnings))

    def test_the_yaml_subset_reads_maps_lists_and_blocks(self):
        text = ("a: 1\n"
                "b: \"two\"\n"
                "c:\n"
                "  d: true\n"
                "  e:\n"
                "f:\n"
                "  - one\n"
                "  - two\n"
                "g: >-\n"
                "  folded line\n"
                "  continues\n"
                "# comment\n"
                "h: 2.5  # trailing comment\n")
        got = sweep.parse_yaml(text)
        self.assertEqual(got["a"], 1)
        self.assertEqual(got["b"], "two")
        self.assertEqual(got["c"], {"d": True, "e": None})
        self.assertEqual(got["f"], ["one", "two"])
        self.assertEqual(got["g"], "folded line continues")
        self.assertEqual(got["h"], 2.5)

    def test_ground_floor_can_be_said_in_plain_words_under_avoid(self):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("avoid:\n  - ground floor\n  - heat network without a written tariff\n"
                     "commute:\n  destination: WC2R 2LS\n")
        try:
            prof, _, _ = sweep.read_profile(path)
        finally:
            os.remove(path)
        self.assertIs(prof["reject_ground_floor"], True)
        self.assertEqual(prof["destination"], "WC2R 2LS")

    def test_a_hash_inside_a_quoted_string_is_not_a_comment(self):
        self.assertEqual(sweep.parse_yaml('a: "x # y"')["a"], "x # y")


# ------------------------------------------------------------- cost gate ----
class TestFetchEstimate(unittest.TestCase):
    def test_the_estimate_adds_up(self):
        est = sweep.fetch_estimate(n_streets=40, n_buildings_filtered=10,
                                   certs_per_building=8, n_facts=4, crime_months=6)
        self.assertEqual(est["epc_street_searches"], 40)
        self.assertEqual(est["epc_certificates"], 80)
        self.assertEqual(est["facts_total"], 4 * est["per_building_facts"])
        self.assertEqual(est["shared_openstreetmap_query"], 1,
                         "OpenStreetMap is asked once for the whole circle, "
                         "not once per building")
        self.assertEqual(est["grand_total_excluding_postcodes"],
                         2 + 40 + 80 + 4 * est["per_building_facts"])

    def test_fewer_crime_months_cost_less(self):
        six = sweep.fetch_estimate(1, 1, 1, 1, 6)["per_building_facts"]
        one = sweep.fetch_estimate(1, 1, 1, 1, 1)["per_building_facts"]
        self.assertGreater(six, one)


# --------------------------------------------------- stage 1, end to end ----
class Args(object):
    """The argparse namespace stage 1 reads, with the CLI defaults."""
    def __init__(self, **kw):
        self.radius = 400
        self.max_streets = 0
        self.postcode_fallback = 40
        self.max_postcode_lookups = 120
        self.verbose = False
        for k, v in kw.items():
            setattr(self, k, v)


def row(cid, address):
    return {"certificate_id": cid, "address": address, "rating": "C",
            "valid_until": "1 January 2030",
            "certificate_url": "https://find-energy-certificate.service.gov.uk/x"}


class TestStage1Enumerate(unittest.TestCase):
    """Streets -> certificates -> buildings, with every fetcher stubbed.

    Weston Street is the street the register refuses ("too many results"), which is
    the case that silently loses the busiest streets if the fallback is missing.
    """
    NEARBY = [{"postcode": "SE1 3QB", "lat": 51.5040, "lng": -0.0862, "distance_m": 60.0},
              {"postcode": "SE1 9SG", "lat": 51.5049, "lng": -0.0876, "distance_m": 95.0},
              {"postcode": "SE1 9ZZ", "lat": 51.5200, "lng": -0.0876, "distance_m": 1800.0}]
    BY_POSTCODE = {
        "SE1 3QB": [row("1111-0000-0000-0000-0001", "Flat 1, 12 Weston Street, LONDON, SE1 3QB"),
                    row("1111-0000-0000-0000-0002", "Flat 2, 12 Weston Street, LONDON, SE1 3QB")],
        "SE1 9SG": [row("2222-0000-0000-0000-0001",
                        "Flat 200, London Bridge Hotel, LONDON, SE1 9SG")],
    }
    BY_STREET = {
        "Bridge Yard": [row("3333-0000-0000-0000-0001", "Flat 1, 3 Bridge Yard, LONDON, SE1 3QB"),
                        row("3333-0000-0000-0000-0002",
                            "Flat 2, 3 Bridge Yard, LONDON, SE1 9ZZ")],
    }

    def setUp(self):
        self.saved = (roads.run_overpass, epc.search, sweep.geo.nearby, sweep.geo.lookup)
        roads.run_overpass = lambda q, **kw: (OVERPASS_STREETS, {
            "source_url": "https://overpass-api.de/api/interpreter", "http_status": 200,
            "ok": True, "note": "", "retrieved_at": "2026-09-03T11:00:00+00:00",
            "overpass_instance": "https://overpass-api.de/api/interpreter", "attempts": []})

        def fake_search(postcode=None, street=None, town=None):
            base = {"source_url": "https://find-energy-certificate.service.gov.uk/x",
                    "http_status": 200, "ok": True, "note": "",
                    "retrieved_at": "2026-09-03T11:00:00+00:00", "evidence_class": "G",
                    "too_many_results": False}
            if postcode:
                rows = self.BY_POSTCODE.get(postcode, [])
            elif street in self.BY_STREET:
                rows = self.BY_STREET[street]
            else:                                   # the register refuses a busy street
                base["too_many_results"] = True
                rows = []
            base["count"] = len(rows)
            base["results"] = rows
            return base

        epc.search = fake_search
        sweep.geo.nearby = lambda lat, lng, radius=2000, **kw: {
            "ok": True, "source_url": "https://api.postcodes.io/x", "saturated": False,
            "furthest_m": 1800.0, "results": self.NEARBY, "count": len(self.NEARBY)}
        sweep.geo.lookup = lambda pc, **kw: {"ok": False, "lat": None, "note": "stub"}

    def tearDown(self):
        roads.run_overpass, epc.search, sweep.geo.nearby, sweep.geo.lookup = self.saved

    def run_stage1(self, **kw):
        args = Args(**kw)
        anchor = {"lat": 51.5045, "lng": -0.0865, "town_searched": "London"}
        book = sweep.PostcodeBook(anchor["lat"], anchor["lng"], args.radius,
                                  max_lookups=args.max_postcode_lookups)
        return sweep.stage1_enumerate(anchor, args, book, [])

    def test_a_refused_street_is_recorded_and_recovered_by_postcode(self):
        out = self.run_stage1()
        self.assertEqual(out["streets"]["too_many_results"], ["Weston Street"])
        self.assertEqual(out["postcode_fallback"]["triggered_by_streets"], 1)
        self.assertEqual(out["postcode_fallback"]["postcodes_searched"], 2)
        keys = [b["key"] for b in out["buildings"]]
        self.assertIn("12--weston-street--se1", keys,
                      "the refused street must come back through the postcode fallback")

    def test_the_fallback_can_be_switched_off_and_says_what_was_lost(self):
        out = self.run_stage1(postcode_fallback=0)
        self.assertEqual(out["postcode_fallback"]["postcodes_searched"], 0)
        self.assertNotIn("12--weston-street--se1", [b["key"] for b in out["buildings"]])
        self.assertTrue(any("would not list" in nf["what"] for nf in out["not_found"]))

    def test_a_certificate_outside_the_circle_is_counted_and_dropped(self):
        out = self.run_stage1()
        self.assertEqual(out["certificates_outside_radius"], 1)
        self.assertNotIn("SE1 9ZZ", sum((b["postcodes"] for b in out["buildings"]), []))

    def test_two_flats_in_one_building_are_one_candidate(self):
        out = self.run_stage1()
        weston = [b for b in out["buildings"] if b["key"] == "12--weston-street--se1"][0]
        self.assertEqual(weston["certificate_count"], 2)
        self.assertEqual(weston["distance_m"], 60.0)
        self.assertEqual(weston["coordinates"]["lat"], 51.5040)
        self.assertIn("postcode centroid", weston["coordinates"]["provenance"])

    def test_the_hotel_is_marked_not_deleted(self):
        out = self.run_stage1()
        hotel = [b for b in out["buildings"] if "hotel" in b["key"]]
        self.assertEqual(len(hotel), 1)
        self.assertEqual(hotel[0]["excluded_code"], "hotel_or_hostel")
        self.assertEqual(out["counts"]["excluded"], 1)

    def test_buildings_come_back_nearest_first(self):
        out = self.run_stage1()
        d = [b["distance_m"] for b in out["buildings"] if b["distance_m"] is not None]
        self.assertEqual(d, sorted(d))

    def test_every_empty_search_leaves_the_exact_query_behind(self):
        out = self.run_stage1()
        self.assertTrue(out["not_found"])
        for nf in out["not_found"]:
            self.assertTrue(nf["what"])
            self.assertTrue(nf["queries_used"])


if __name__ == "__main__":
    unittest.main()
