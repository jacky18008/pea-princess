"""Offline tests for scripts/planning.py (GLA Planning London Datahub).

Run: python3 -m unittest tests/test_planning.py
Fixtures are raw Elasticsearch responses captured from
planningdata.london.gov.uk on 2026-09-03.
"""
import json
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import planning  # noqa: E402

FIX = os.path.join(HERE, "fixtures")
LAT, LNG = 51.5045, -0.0865            # London Bridge / the Shard


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------- OSGB conversion ----
class TestOsgb36(unittest.TestCase):
    """WGS84 -> OSGB36 National Grid, Helmert + Transverse Mercator."""

    def test_central_london_reference_pair(self):
        # 51.5074, -0.1278 is quoted as E 530034 N 180381. That published pair
        # comes from OSTN15, the official grid-shift file. The Helmert route
        # this script uses cannot reproduce OSTN15 exactly; it lands ~5 m away,
        # which is the documented accuracy of the method.
        e, n = planning.wgs84_to_osgb36(51.5074, -0.1278)
        off = math.hypot(e - 530034, n - 180381)
        self.assertLess(off, 8.0, "%d/%d is %.1f m from the reference pair" % (e, n, off))
        self.assertGreater(off, 1.0, "suspiciously exact — did someone wire in OSTN15?")

    def test_returns_whole_metre_ints(self):
        e, n = planning.wgs84_to_osgb36(51.5074, -0.1278)
        self.assertIsInstance(e, int)
        self.assertIsInstance(n, int)

    def test_moving_north_increases_northing(self):
        e0, n0 = planning.wgs84_to_osgb36(51.5000, -0.1000)
        e1, n1 = planning.wgs84_to_osgb36(51.5010, -0.1000)      # ~111 m north
        self.assertAlmostEqual(n1 - n0, 111, delta=3)
        self.assertAlmostEqual(e1 - e0, 0, delta=3)

    def test_moving_east_increases_easting(self):
        e0, n0 = planning.wgs84_to_osgb36(51.5000, -0.1000)
        e1, n1 = planning.wgs84_to_osgb36(51.5000, -0.0990)      # ~69 m east
        self.assertAlmostEqual(e1 - e0, 69, delta=3)
        self.assertAlmostEqual(n1 - n0, 0, delta=3)

    def test_grid_distance_matches_great_circle(self):
        """Grid metres and ground metres must agree over a few hundred metres.

        The half-percent tolerance is dominated by the spherical-Earth radius in
        the haversine, not by the projection: the National Grid's own scale
        factor at London is within 0.02 % of 1.
        """
        a = planning.wgs84_to_osgb36(51.5045, -0.0865)
        b = planning.wgs84_to_osgb36(51.5075, -0.0810)
        grid = math.hypot(a[0] - b[0], a[1] - b[1])
        arc = planning._haversine_m(51.5045, -0.0865, 51.5075, -0.0810)
        self.assertLess(abs(grid - arc) / arc, 0.005)

    def test_ellipsoidal_height_barely_moves_the_answer(self):
        self.assertEqual(planning.wgs84_to_osgb36(51.5074, -0.1278, 0.0),
                         planning.wgs84_to_osgb36(51.5074, -0.1278, 60.0))

    def test_edinburgh_is_north_of_london(self):
        _, n_lon = planning.wgs84_to_osgb36(51.5074, -0.1278)
        _, n_edi = planning.wgs84_to_osgb36(55.9533, -3.1883)
        self.assertGreater(n_edi, n_lon + 480000)


# ------------------------------------------------------ query builders ------
class TestGeoFilter(unittest.TestCase):
    def test_default_is_geo_distance_on_the_centroid_geo_point(self):
        f = planning.geo_filter(LAT, LNG, 250)
        self.assertEqual(f, {"geo_distance": {"distance": "250m",
                                              "centroid": {"lat": LAT, "lon": LNG}}})

    def test_radius_is_rendered_as_whole_metres(self):
        self.assertEqual(planning.geo_filter(LAT, LNG, 300.7)["geo_distance"]["distance"], "300m")

    def test_bbox_filter_brackets_the_osgb_grid_reference(self):
        f = planning.geo_filter(LAT, LNG, 250, bbox=True)
        e, n = planning.wgs84_to_osgb36(LAT, LNG)
        clauses = f["bool"]["filter"]
        self.assertEqual(clauses[0]["range"]["centroid_easting"], {"gte": e - 250, "lte": e + 250})
        self.assertEqual(clauses[1]["range"]["centroid_northing"], {"gte": n - 250, "lte": n + 250})

    def test_bbox_filter_touches_no_geo_point_field(self):
        self.assertNotIn("centroid\"", json.dumps(planning.geo_filter(LAT, LNG, 250, bbox=True)))


class TestSinceFilter(unittest.TestCase):
    def test_uses_the_indexs_own_date_format(self):
        f = planning.since_filter(2018)
        shoulds = f["bool"]["should"]
        self.assertEqual(f["bool"]["minimum_should_match"], 1)
        self.assertEqual(shoulds[0]["range"]["valid_date"],
                         {"gte": "01/01/2018", "format": "dd/MM/yyyy"})
        self.assertEqual(shoulds[1]["range"]["decision_date"]["format"], "dd/MM/yyyy")

    def test_zero_and_none_disable_it(self):
        self.assertIsNone(planning.since_filter(0))
        self.assertIsNone(planning.since_filter(None))


# --------------------------------------------------- tall building hint -----
class TestTallBuildingHint(unittest.TestCase):
    def hint(self, *a, **kw):
        return planning.tall_building_hint(*a, **kw)

    def test_digit_storeys_at_or_over_the_threshold(self):
        ok, why = self.hint("Erection of a 12 storey residential building")
        self.assertTrue(ok)
        self.assertIn("12 storeys", why)

    def test_hyphenated_and_plural_forms(self):
        self.assertTrue(self.hint("a 9-storey block")[0])
        self.assertTrue(self.hint("part 26 and part 16 storeys")[0])

    def test_word_numbers(self):
        ok, why = self.hint("erection of an eight storey building")
        self.assertTrue(ok)
        self.assertIn("8 storeys", why)

    def test_below_the_threshold_is_not_a_hint(self):
        self.assertFalse(self.hint("Erection of a 7 storey building")[0])
        self.assertFalse(self.hint("Single storey rear extension")[0])

    def test_units_threshold(self):
        self.assertTrue(self.hint("Redevelopment", units=218)[0])
        self.assertIn("218 residential units", self.hint("Redevelopment", units=218)[1])
        self.assertFalse(self.hint("Redevelopment", units=99)[0])

    def test_storeys_argument_beats_silent_text(self):
        ok, why = self.hint("Redevelopment of the site", storeys=17)
        self.assertTrue(ok)
        self.assertIn("17 storeys", why)

    def test_tall_building_phrase(self):
        self.assertTrue(self.hint("a tall building in the cluster")[0])

    def test_tower_counts(self):
        ok, why = self.hint("Erection of a residential tower")
        self.assertTrue(ok)
        self.assertIn('description says "tower"', why)

    def test_london_place_names_containing_tower_do_not_count(self):
        for text in ("Site in Tower Hamlets", "Land at Tower Bridge Road",
                     "Tower Hill ticket hall", "view of the Tower of London",
                     "replacement cooling tower"):
            self.assertFalse(self.hint(text)[0], text)

    def test_tower_hamlets_plus_real_storeys_still_flags(self):
        ok, why = self.hint("Tower Hamlets: erection of a 14 storey block")
        self.assertTrue(ok)
        self.assertEqual(why, ["14 storeys"])

    def test_nothing_at_all(self):
        self.assertEqual(self.hint(None), (False, []))
        self.assertEqual(self.hint("Replacement shopfront"), (False, []))

    def test_storeys_in_text_picks_the_largest(self):
        self.assertEqual(planning.storeys_in_text("part 26 and part 16 storeys"), 26)
        self.assertIsNone(planning.storeys_in_text("no numbers here"))


# ------------------------------------------------------ borough portals -----
class TestBoroughPortals(unittest.TestCase):
    def test_reads_all_thirty_three_boroughs(self):
        self.assertEqual(len(planning.borough_portals()), 33)

    def test_ampersand_and_short_names_map_to_the_yaml_spelling(self):
        for lpa in ("Barking & Dagenham", "Hammersmith & Fulham", "Kensington & Chelsea",
                    "Kingston", "Richmond", "London Borough of Newham",
                    "Bromley Custodian Code", "City of Westminster"):
            url, note = planning.portal_for(lpa)
            self.assertTrue(url and url.startswith("http"), "%s -> %r" % (lpa, url))
            self.assertIsNone(note)

    def test_city_of_london_is_not_swallowed_by_the_city_of_prefix(self):
        url, _ = planning.portal_for("City of London")
        self.assertIn("cityoflondon", url)

    def test_development_corporations_get_a_note_not_a_url(self):
        for lpa in ("LLDC", "OPDC"):
            url, note = planning.portal_for(lpa)
            self.assertIsNone(url)
            self.assertIn("Mayoral Development Corporation", note)

    def test_unknown_lpa_says_so(self):
        url, note = planning.portal_for("Manchester")
        self.assertIsNone(url)
        self.assertIn("boroughs.yaml", note)


# ---------------------------------------------------- fixture parsing -------
class TestNearFixture(unittest.TestCase):
    """tests/fixtures/planning-near-london-bridge.json — the live `near` response."""

    @classmethod
    def setUpClass(cls):
        cls.data = load("planning-near-london-bridge.json")
        cls.rows = planning.rows_from_hits(cls.data, LAT, LNG, radius=250)

    def test_total_is_the_real_count_not_the_10000_cap(self):
        total = self.data["hits"]["total"]
        self.assertEqual(total["relation"], "eq")
        self.assertGreater(total["value"], 100)

    def test_rows_are_sorted_by_distance(self):
        d = [r["distance_m"] for r in self.rows]
        self.assertEqual(d, sorted(d))
        self.assertTrue(all(x is not None and x <= 250 for x in d))

    def test_nearest_record_is_the_shard(self):
        r = self.rows[0]
        self.assertEqual(r["reference"], "26/AP/0812")
        self.assertEqual(r["lpa_name"], "Southwark")
        self.assertEqual(r["postcode"], "SE1 9SG")
        self.assertLess(r["distance_m"], 15)
        self.assertIn("London Bridge Street", r["address"])
        self.assertEqual(r["portal_url"], "https://planning.southwark.gov.uk/online-applications/")
        self.assertIsNone(r["portal_note"])

    def test_every_row_has_the_full_shape(self):
        want = {"reference", "lpa_name", "address", "postcode", "description",
                "application_type", "development_type", "status", "decision",
                "decision_date", "valid_date", "distance_m", "tall_building_hint",
                "storeys", "residential_units_proposed", "portal_url"}
        for r in self.rows:
            self.assertTrue(want.issubset(r.keys()))

    def test_descriptions_are_trimmed_to_300_characters(self):
        for r in self.rows:
            if r["description"]:
                self.assertLessEqual(len(r["description"]), planning.DESC_CHARS)

    def test_addresses_are_single_line(self):
        """site_name arrives with embedded newlines; they must not reach the report."""
        for r in self.rows:
            if r["address"]:
                self.assertNotIn("\n", r["address"])

    def test_the_part_26_part_16_scheme_is_flagged_at_26(self):
        """These records read "part 26 and part 16 storeys"; only "16" sits next
        to the word, so the part-storey rule has to catch the 26."""
        flagged = [r for r in self.rows if r["tall_building_hint"]]
        self.assertTrue(flagged)
        self.assertTrue(any("26 storeys" in "".join(r["tall_building_reasons"]) for r in flagged))

    def test_bbox_path_refilters_the_square_corners(self):
        wide = planning.rows_from_hits(self.data, LAT, LNG, radius=50, bbox=True)
        self.assertTrue(all(r["distance_m"] <= 50 for r in wide))
        self.assertLess(len(wide), len(self.rows))


class TestStagesFixture(unittest.TestCase):
    """tests/fixtures/planning-stages-26-AP-0812.json — one full record."""

    @classmethod
    def setUpClass(cls):
        cls.src = load("planning-stages-26-AP-0812.json")["hits"]["hits"][0]["_source"]
        cls.rec = planning.shape(cls.src)
        cls.lines = planning.explain(cls.rec, cls.src)

    def test_record_identity(self):
        self.assertEqual(self.rec["reference"], "26/AP/0812")
        self.assertEqual(self.rec["decision"], "Approved")

    def test_explains_the_status_in_plain_words(self):
        self.assertTrue(any("Approval is recorded" in x for x in self.lines))

    def test_uses_the_recorded_expiry_not_a_guessed_three_years(self):
        self.assertTrue(any("actual start date remains unknown" in x for x in self.lines))
        self.assertTrue(any("lapse date of 29/04/2029" in x for x in self.lines))
        self.assertFalse(any("three years" in x or "must start" in x for x in self.lines))

    def test_a_future_expiry_is_not_reported_as_lapsed(self):
        self.assertFalse(any("Lapsed" in x for x in self.lines))

    def test_date_parser(self):
        self.assertEqual(planning._as_date("29/04/2029").year, 2029)
        self.assertEqual(planning._as_date("29/04/2029").month, 4)
        self.assertIsNone(planning._as_date("2029-04-29"))
        self.assertIsNone(planning._as_date(None))


class TestStageEvidenceLimits(unittest.TestCase):
    def test_inconsistent_outcomes_and_pending_aliases_are_checked_both_ways(self):
        pairs = [('Approved', 'Refused'), ('Approve', 'Under Consideration'),
                 ('Approved', 'Pending Decision'), ('Granted', 'Received'),
                 ('Refused', 'Application Under Consideration')]
        for left, right in pairs:
            for status, decision in ((left, right), (right, left)):
                with self.subTest(status=status, decision=decision):
                    text = ' '.join(planning.explain({'status': status, 'decision': decision}, {}))
                    self.assertIn('fields conflict', text)
                    self.assertNotIn('Approval is recorded', text)
                    self.assertNotIn('Approval relates', text)

    def test_lifecycle_labels_do_not_negate_an_earlier_recorded_decision(self):
        for status in ('Closed', 'Superseded', 'Lapsed', 'Completed', 'Withdrawn'):
            with self.subTest(status=status):
                text = ' '.join(planning.explain({'status': status, 'decision': 'Approved'}, {}))
                self.assertIn('Status ' + status, text)
                self.assertNotIn('fields conflict', text)
                self.assertNotIn('without a planning decision', text)
                self.assertNotIn('before a decision', text)

    def test_generic_conditions_and_variations_are_not_classified_as_discharge(self):
        descriptions = [
            'New dwelling subject to condition 4 for landscaping',
            'Variation of condition 2 (approved plans)',
            'New dwelling following approval of details reserved by condition 4',
        ]
        for description in descriptions:
            with self.subTest(description=description):
                rec = {'status': 'Approved', 'decision': 'Approved', 'description': description,
                       'application_type_full': 'Full Planning Permission'}
                text = ' '.join(planning.explain(rec, {}))
                self.assertIn('record mentions planning conditions', text)
                self.assertNotIn('Approval relates to submitted condition details', text)
                self.assertNotIn('not a new general planning permission', text)
                self.assertNotIn('text concerns pre-occupation', text)

    def test_explicit_application_type_or_current_details_wording_identifies_discharge(self):
        cases = [{'application_type': 'AOD', 'description': 'Building materials'},
                 {'application_type_full': 'Discharge of Conditions', 'description': 'Building materials'},
                 {'description': 'Approval of details reserved by condition 4'},
                 {'description': 'Application for discharge of condition 4'}]
        for fields in cases:
            with self.subTest(fields=fields):
                rec = dict(fields, status='Approved', decision='Approved')
                text = ' '.join(planning.explain(rec, {}))
                self.assertIn('Approval relates to submitted condition details', text)
                self.assertIn('not evidence that work is starting or finishing', text)

    def test_unknown_decision_wording_is_not_invented_as_approval(self):
        text = ' '.join(planning.explain({'decision': 'Approval not required'}, {}))
        self.assertNotIn('Approval is recorded', text)

    def test_explanations_leave_raw_conflicting_fields_and_dates_intact(self):
        source = {'status': 'Under Consideration', 'decision': 'Approved',
                  'decision_date': '11/08/2026', 'actual_commencement_date': '12/08/2026',
                  'actual_completion_date': '01/09/2026', 'lapsed_date': '11/08/2029'}
        rec = planning.shape(source)
        before = json.dumps([source, rec], sort_keys=True)
        text = ' '.join(planning.explain(rec, source))
        self.assertIn('fields conflict', text)
        self.assertIn('commencement on 12/08/2026', text)
        self.assertIn('completion on 01/09/2026', text)
        self.assertIn('lapse date of 11/08/2029', text)
        self.assertEqual('Under Consideration', rec['status'])
        self.assertEqual('Approved', rec['decision'])
        self.assertEqual('11/08/2026', rec['decision_date'])
        self.assertEqual(before, json.dumps([source, rec], sort_keys=True))

    def test_pending_status_overrules_inconsistent_approval_field_for_inference(self):
        rec={'status':'Application Under Consideration','decision':'Approved','decision_date':'11/08/2026',
             'description':'Demolition of an extension','application_type_full':'Full Planning Permission'}
        lines=planning.explain(rec,{})
        text=' '.join(lines)
        self.assertIn('fields conflict',text)
        self.assertNotIn('Granted',text);self.assertNotIn('2029',text)
        self.assertNotIn('Approval is recorded',text)
    def test_condition_approval_is_not_new_permission_or_imminent_works(self):
        rec={'status':'Approved','decision':'Approved','decision_date':'10/12/2024',
             'description':'Approval of details reserved by condition 4 (construction management)',
             'application_type_full':'Discharge of Conditions'}
        text=' '.join(planning.explain(rec,{'lapsed_date':'10/12/2027'}))
        self.assertIn('submitted condition details',text);self.assertIn('not evidence',text)
        for bad in ('permission granted','works are about to start','must start before','permission expires'):
            self.assertNotIn(bad,text)
        self.assertIn('lapse date of 10/12/2027',text)
    def test_approval_without_expiry_does_not_invent_a_three_year_window(self):
        text=' '.join(planning.explain({'status':'Approved','decision':'Approved','decision_date':'11/08/2026'},{}))
        self.assertIn('actual start date remains unknown',text)
        self.assertNotIn('2029',text);self.assertNotIn('three years',text)
    def test_recorded_completion_does_not_guarantee_all_disruption_over(self):
        text=' '.join(planning.explain({'status':'Completed'},{'actual_completion_date':'01/08/2026'}))
        self.assertIn('completion on 01/08/2026',text)
        self.assertNotIn('disruption is over',text)
        self.assertIn('other or later works',text)


class TestTallWithConditionsFixture(unittest.TestCase):
    """A record carrying nested building_details, unit counts and conditions."""

    @classmethod
    def setUpClass(cls):
        cls.src = load("planning-tall-with-conditions.json")["hits"]["hits"][0]["_source"]
        cls.rec = planning.shape(cls.src)

    def test_storeys_come_out_of_the_nested_building_details(self):
        self.assertEqual(self.rec["storeys"], 17)      # stored as 17.0, a float

    def test_units_come_out_of_residential_details(self):
        self.assertEqual(self.rec["residential_units_proposed"], 218)

    def test_both_reasons_are_reported(self):
        self.assertTrue(self.rec["tall_building_hint"])
        self.assertEqual(sorted(self.rec["tall_building_reasons"]),
                         ["17 storeys", "218 residential units"])

    def test_conditions_are_present_in_the_api_for_this_record(self):
        self.assertIsInstance(self.src.get("decision_conditions"), list)
        self.assertTrue(self.src["decision_conditions"])


class TestZeroHits(unittest.TestCase):
    def test_no_rows_and_a_real_zero(self):
        data = load("planning-search-zero-hits.json")
        self.assertEqual(data["hits"]["total"]["value"], 0)
        self.assertEqual(planning.rows_from_hits(data, LAT, LNG), [])


# ------------------------------------------------------------ shaping -------
class TestLooseTypes(unittest.TestCase):
    """The Datahub is loosely typed; the shaper must not raise on any of it."""

    def test_int_site_number(self):
        self.assertEqual(planning._address({"site_number": 80, "street_name": "Aberdeen Park"}),
                         "80 Aberdeen Park")

    def test_list_valued_street(self):
        self.assertEqual(planning._address({"street_name": ["High", "Street"]}), "High Street")

    def test_missing_everything(self):
        self.assertIsNone(planning._address({}))

    def test_centroid_accepts_every_geo_point_spelling(self):
        for src, want in (({"centroid": {"lat": 51.5, "lon": -0.1}}, (51.5, -0.1)),
                          ({"centroid": "51.5,-0.1"}, (51.5, -0.1)),
                          ({"centroid": [-0.1, 51.5]}, (51.5, -0.1)),
                          ({"centroid": {"lat": "51.5", "lon": "-0.1"}}, (51.5, -0.1)),
                          ({}, (None, None))):
            self.assertEqual(planning.centroid_of(src), want)

    def test_application_details_may_be_a_non_dict(self):
        self.assertIsNone(planning._storeys({"application_details": "nope"}))
        self.assertIsNone(planning._units({"application_details": []}))


if __name__ == "__main__":
    unittest.main()
