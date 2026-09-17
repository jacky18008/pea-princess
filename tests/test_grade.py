# -*- coding: utf-8 -*-
"""Offline tests for the benchmark layer: bench/grade.py and bench/run.py --dry-run.

Nothing here touches the network. The grader is exercised against
tests/fixtures/report-sample.json with a synthetic expected_facts block built to
match what that sample actually says, so a correct report scores full marks and a
doctored copy of the same report is caught.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")

sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.join(ROOT, "skills", "vet-flat", "scripts"))
import grade as grader  # noqa: E402
import run as runner  # noqa: E402

SAMPLE = os.path.join(HERE, "fixtures", "report-sample.json")

# The profile that matches the sample report's own profile_snapshot, so the
# hard-filter rows in the sample are judged against the ruler they were written to.
SAMPLE_PROFILE = """min_floor_area_sqft: 490
max_building_age_years: 25
budget:
  all_in_pcm_ceiling: 2600
commute:
  destination: "SW1A 2AA"
  max_door_to_door_min: 40
floors:
  reject_ground_floor: true
"""

# What tests/fixtures/report-sample.json actually says about candidate c1:
#   53 square metres / 571 square feet, first assessment 2019, a building-wide
#   heating system, third floor of nine, 74 crimes in six months, 34 minutes door
#   to door, redundancy grade A.
SYNTHETIC_FACTS = {
    "epc": {
        "certificate_id": "0000-0000-0000-0000-0000",
        "floor_area_m2": 53.0,
        "floor_area_sqft": 571,
        "first_assessment_year": 2019,
        "heating_class": "community_heat_network",
        "floor_position": "mid",
        "energy_rating": None,
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/epc.py cert 0000-0000-0000-0000-0000 --history",
    },
    "crime": {
        "box_half_m": 150,
        "months": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
        "total": 74,
        "tolerance_pct": 15,
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/crime.py box --lat 51.0 --lng 0.0",
    },
    "commute": {
        "destination": "SW1A 2AA",
        "all_min": 34,
        "rail_min": None,
        "tolerance_min": 8,
        "redundancy_grade": "A",
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/commute.py journey --from X --to SW1A 2AA",
    },
}

SYNTHETIC_CASE = {
    "id": "synthetic-sample",
    "address": "Flat 12, Harrowfield Court",
    "borough": "Test",
    "prompt": "Vet this flat: Flat 12, Harrowfield Court.",
    "files": ["cases/synthetic-sample/profile.yaml"],
    "expected_facts": SYNTHETIC_FACTS,
}


def read_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_profile(text):
    handle, path = tempfile.mkstemp(suffix="-profile.yaml")
    os.close(handle)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class GradeBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = write_profile(SAMPLE_PROFILE)
        cls.sample = read_json(SAMPLE)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.profile)

    def card_for(self, report, case=None):
        return grader.grade(report, case or SYNTHETIC_CASE, self.profile)

    def fact(self, card, name):
        for row in card["facts"]:
            if row["fact"] == name:
                return row
        self.fail("the scorecard has no row for %s" % name)


# ------------------------------------------------------------ a good report --
class TestCorrectReport(GradeBase):
    def setUp(self):
        self.card = self.card_for(copy.deepcopy(self.sample))

    def test_the_sample_still_validates(self):
        self.assertTrue(self.card["schema"]["valid"], self.card["schema"]["errors"])

    def test_full_recall_and_no_fabrications(self):
        self.assertEqual(1.0, self.card["scores"]["fact_recall"],
                         [r for r in self.card["facts"] if r["status"] != "correct"])
        self.assertEqual(0, self.card["scores"]["fabrications"])

    def test_every_graded_fact_is_cited(self):
        self.assertEqual(1.0, self.card["scores"]["citations"])

    def test_unknown_honesty_is_full_when_nothing_is_missing(self):
        self.assertEqual(1.0, self.card["scores"]["unknown_honesty"])

    def test_it_meets_the_pass_line(self):
        self.assertTrue(self.card["meets_pass_line"], self.card["summary"])

    def test_area_is_read_from_the_certificate_not_the_advert(self):
        row = self.fact(self.card, "epc.floor_area_m2")
        self.assertEqual(571, row["reported"])           # not the advertised 620
        self.assertEqual("correct", row["status"])

    def test_an_age_in_years_is_converted_to_an_assessment_year(self):
        row = self.fact(self.card, "epc.first_assessment_year")
        self.assertEqual("correct", row["status"])
        self.assertIn("2019", row["detail"])

    def test_plain_language_heating_is_classified(self):
        row = self.fact(self.card, "epc.heating_class")
        self.assertEqual("community_heat_network", row["reported"])

    def test_floor_position_comes_from_identity(self):
        row = self.fact(self.card, "epc.floor_position")
        self.assertEqual("mid", row["reported"])
        self.assertEqual("candidates[0].identity.floor", row["where"])

    def test_metrics_are_read_by_key(self):
        self.assertEqual("candidates[0].metrics.crime_6mo_count",
                         self.fact(self.card, "crime.total")["where"])
        self.assertEqual("candidates[0].metrics.commute_min",
                         self.fact(self.card, "commute.all_min")["where"])

    def test_hard_filters_agree_with_the_profile(self):
        self.assertEqual(1.0, self.card["scores"]["hard_filter_consistency"],
                         self.card["hard_filters"])
        kinds = sorted(h["filter"] for h in self.card["hard_filters"])
        self.assertEqual(["age", "area", "commute", "ground_floor"], kinds)

    def test_the_verdict_is_not_graded(self):
        louder = copy.deepcopy(self.sample)
        louder["candidates"][0]["verdict"] = {
            "status": "KILL",
            "headline": "Do not view this flat.",
            "reason_codes": [],
            "fatal_axis": 5,
        }
        card = self.card_for(louder)
        self.assertEqual(self.card["scores"]["fact_recall"], card["scores"]["fact_recall"])
        self.assertEqual(0, card["scores"]["fabrications"])


# --------------------------------------------------------- a doctored report --
class TestDoctoredReport(GradeBase):
    def setUp(self):
        bad = copy.deepcopy(self.sample)
        cand = bad["candidates"][0]
        # 1. the floor area is inflated to the advertised figure
        for num in cand["axes"][1]["numbers"]:
            if num["label"] == "Indoor floor area":
                num["value"] = 700
        # 2. a crime count nobody counted
        cand["metrics"]["crime_6mo_count"]["value"] = 300
        for num in cand["axes"][4]["numbers"]:
            if num["label"].startswith("Recorded crimes"):
                num["value"] = 300
        # 3. the commute number loses its source
        cand["metrics"]["commute_min"]["sources"] = []
        cand["axes"][10]["sources"] = []
        for num in cand["axes"][10]["numbers"]:
            num["sources"] = []
        self.card = self.card_for(bad)

    def test_the_inflated_area_is_a_fabrication(self):
        row = self.fact(self.card, "epc.floor_area_m2")
        self.assertEqual("wrong", row["status"])
        self.assertEqual(700, row["reported"])
        self.assertIn("571", row["detail"])

    def test_the_invented_crime_count_is_a_fabrication(self):
        row = self.fact(self.card, "crime.total")
        self.assertEqual("wrong", row["status"])
        self.assertIn("74", row["detail"])

    def test_two_fabrications_are_counted(self):
        self.assertEqual(2, self.card["scores"]["fabrications"])

    def test_the_uncited_number_drops_the_citation_score(self):
        row = self.fact(self.card, "commute.all_min")
        self.assertFalse(row["cited"])
        self.assertLess(self.card["scores"]["citations"], 1.0)

    def test_recall_falls_and_the_pass_line_is_missed(self):
        self.assertLess(self.card["scores"]["fact_recall"], 1.0)
        self.assertFalse(self.card["meets_pass_line"])

    def test_a_fabrication_is_never_counted_as_an_honest_unknown(self):
        row = self.fact(self.card, "crime.total")
        self.assertFalse(row["marked_unknown"])
        self.assertLess(self.card["scores"]["unknown_honesty"], 1.0)


# ------------------------------------------------------------ missing facts --
class TestMissingFacts(GradeBase):
    def test_a_silently_dropped_fact_is_missing_not_fabricated(self):
        bad = copy.deepcopy(self.sample)
        cand = bad["candidates"][0]
        cand["axes"][1]["numbers"] = []
        card = self.card_for(bad)
        row = self.fact(card, "epc.floor_area_m2")
        self.assertEqual("missing", row["status"])
        self.assertEqual(0, card["scores"]["fabrications"])
        self.assertFalse(row["marked_unknown"])

    def test_an_honest_unknown_scores_on_unknown_honesty(self):
        bad = copy.deepcopy(self.sample)
        cand = bad["candidates"][0]
        cand["axes"][1]["numbers"] = [{
            "label": "Indoor floor area", "value": None, "unit": "square feet",
            "meaning": "The certificate for this flat could not be opened.",
            "compared_to": "Your floor is 490 square feet.",
            "evidence_class": "U", "sources": [],
        }]
        card = self.card_for(bad)
        row = self.fact(card, "epc.floor_area_m2")
        self.assertEqual("missing", row["status"])
        self.assertTrue(row["marked_unknown"], row)
        self.assertEqual(1.0, card["scores"]["unknown_honesty"])

    def test_a_hard_filter_the_report_omits_is_inconsistent(self):
        bad = copy.deepcopy(self.sample)
        bad["candidates"][0]["hard_filters"] = [
            r for r in bad["candidates"][0]["hard_filters"] if "area" not in r["name"].lower()]
        card = self.card_for(bad)
        area = [h for h in card["hard_filters"] if h["filter"] == "area"][0]
        self.assertFalse(area["consistent"])
        self.assertIsNone(area["reported_pass"])

    def test_a_wrong_hard_filter_answer_is_caught(self):
        bad = copy.deepcopy(self.sample)
        for row in bad["candidates"][0]["hard_filters"]:
            if "area" in row["name"].lower():
                row["pass"] = False
        card = self.card_for(bad)
        area = [h for h in card["hard_filters"] if h["filter"] == "area"][0]
        self.assertFalse(area["consistent"])
        self.assertLess(card["scores"]["hard_filter_consistency"], 1.0)

    def test_an_energy_certificate_year_is_a_lower_bound_on_age(self):
        """A building at least 7 years old passes a 25-year limit; unknown is fine too."""
        card = self.card_for(copy.deepcopy(self.sample))
        age = [h for h in card["hard_filters"] if h["filter"] == "age"][0]
        self.assertEqual(["True", "unknown"], age["expected_pass"])


# ------------------------------------------------------------ referent guard --
# A number can be of the right KIND and about the wrong THING. These cases are
# synthetic fragments on invented addresses: none of the tonight's-sweep reports is
# needed to reproduce any of them.
GUARD_FACTS = {
    "epc": {
        "certificate_id": "0000-0000-0000-0000-0000",
        "register_address": "Flat 12 Tolliver House 4 Rennick Walk X1 2YZ",
        "floor_area_m2": 53.0,
        "floor_area_sqft": 571,
        "first_assessment_year": 2022,
        "heating_class": "community_heat_network",
        "floor_position": "mid",
        "energy_rating": "C",
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/epc.py cert 0000-0000-0000-0000-0000 --history",
    },
    "crime": {
        "box_half_m": 150,
        "months": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"],
        "total": 74,
        "tolerance_pct": 15,
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/crime.py box --lat 51.0 --lng 0.0",
    },
    "commute": {
        "destination": "SW1A 2AA",
        "all_min": 34,
        "rail_min": 33,
        "tolerance_min": 8,
        "redundancy_grade": "A",
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/commute.py journey --from X1 2YZ --to SW1A 2AA",
    },
    "landregistry": {
        "postcode": "X1 2YZ",
        "earliest_new_build_year": 2010,
        "retrieved_at": "2026-09-03T11:00:00Z",
        "command": "python3 skills/vet-flat/scripts/landregistry.py price-paid --postcode 'X1 2YZ'",
    },
}

GUARD_CASE = {
    "id": "synthetic-referent",
    "address": "Flat 12, Tolliver House, 4 Rennick Walk",
    "borough": "Test",
    "prompt": "Vet this flat: Flat 12, Tolliver House.",
    "files": ["cases/synthetic-referent/profile.yaml"],
    "expected_facts": GUARD_FACTS,
}


def number(label, value, unit, sources=("s-epc-1",), **extra):
    row = {"label": label, "value": value, "unit": unit,
           "meaning": "Synthetic fragment for the referent guard.",
           "compared_to": "Nothing; this fragment exists to be graded.",
           "evidence_class": "G", "sources": list(sources)}
    row.update(extra)
    return row


class TestReferentGuard(GradeBase):
    """A number of the right kind about a different thing is not a fabrication.

    Each pattern is tested twice: excluded when the referent differs, and still
    counted when it is the same referent carrying a wrong value.
    """

    def report(self, facts=None):
        rep = copy.deepcopy(self.sample)
        cand = rep["candidates"][0]
        cand["identity"]["display_name"] = "Flat 12, Tolliver House"
        cand["identity"]["address"] = "Flat 12, Tolliver House, 4 Rennick Walk, London"
        cand["identity"]["postcode"] = "X1 2YZ"
        cand["identity"]["flat"] = "Flat 12"
        # The sample dates the building; against this case's truth (built 2010,
        # first certificate 2022) that is a different referent, so the baseline
        # carries no fabrication of its own.
        self.axis(rep, 3)["numbers"][0] = number("Building age", 16, "years")
        return rep

    def case(self, **facts):
        case = copy.deepcopy(GUARD_CASE)
        for block, values in facts.items():
            case["expected_facts"][block].update(values)
        return case

    def axis(self, report, axis_id):
        for axis in report["candidates"][0]["axes"]:
            if axis["id"] == axis_id:
                return axis
        self.fail("the sample has no axis %s" % axis_id)

    def graded(self, report, case=None):
        return grader.grade(report, case or copy.deepcopy(GUARD_CASE), self.profile)

    def excluded_for(self, card, fact):
        return [row for row in card["referent_excluded"] if row["fact"] == fact]

    # ---------------------------------------- a rating in an over-time series --
    def test_a_rating_over_time_is_not_the_rating_now(self):
        rep = self.report()
        self.axis(rep, 3)["numbers"].append(
            number("Energy rating over time", "B 82 in 2019, C 79 in 2026", "band and score"))
        card = self.graded(rep)
        row = self.fact(card, "epc.energy_rating")
        self.assertEqual("missing", row["status"])
        skipped = self.excluded_for(card, "epc.energy_rating")
        self.assertEqual(1, len(skipped), card["referent_excluded"])
        self.assertIn("over time", skipped[0]["reason"])
        self.assertEqual(0, card["scores"]["fabrications"])

    def test_the_rating_now_is_still_graded_and_a_wrong_one_is_a_fabrication(self):
        rep = self.report()
        self.axis(rep, 3)["numbers"].append(
            number("Energy rating, current certificate", "B", "rating A to G"))
        card = self.graded(rep)
        row = self.fact(card, "epc.energy_rating")
        self.assertEqual("wrong", row["status"])          # the truth is C
        self.assertEqual([], self.excluded_for(card, "epc.energy_rating"))
        self.assertEqual(1, card["scores"]["fabrications"])

    def test_a_series_that_says_it_leads_with_today_is_graded(self):
        """'Energy rating now, and before' names its own order, so it is read."""
        rep = self.report()
        self.axis(rep, 3)["numbers"].append(
            number("Energy rating now, and before", "C (79), down from B (82) in 2019",
                   "band and score"))
        card = self.graded(rep)
        self.assertEqual("correct", self.fact(card, "epc.energy_rating")["status"])
        self.assertEqual([], self.excluded_for(card, "epc.energy_rating"))

    # ------------------------------------------- an area on a dead certificate --
    def test_a_superseded_certificate_area_is_skipped_for_the_current_one(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Certified area, 2010 as-built certificate", 441, "square feet"),
            number("Certified area, current certificate", 571, "square feet")]
        card = self.graded(rep)
        row = self.fact(card, "epc.floor_area_m2")
        self.assertEqual("correct", row["status"])
        self.assertEqual(571, row["reported"])
        skipped = self.excluded_for(card, "epc.floor_area_m2")
        self.assertEqual([441], [s["value"] for s in skipped])
        self.assertIn("as built", skipped[0]["reason"])

    def test_a_wrong_area_on_the_current_certificate_is_still_a_fabrication(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Certified area, 2010 as-built certificate", 441, "square feet"),
            number("Certified area, current certificate", 700, "square feet")]
        card = self.graded(rep)
        row = self.fact(card, "epc.floor_area_m2")
        self.assertEqual("wrong", row["status"])
        self.assertEqual(700, row["reported"])
        self.assertEqual(1, card["scores"]["fabrications"])

    def test_an_area_measured_over_the_building_is_not_the_flats(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Smallest certified area in the building", 431, "square feet")]
        card = self.graded(rep)
        self.assertEqual("missing", self.fact(card, "epc.floor_area_m2")["status"])
        self.assertIn("building", self.excluded_for(card, "epc.floor_area_m2")[0]["reason"])

    def test_another_flats_area_is_not_this_flats(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Certified area of Flat 15, one floor up", 903, "square feet"),
            number("Certified indoor area", 571, "square feet")]
        card = self.graded(rep)
        self.assertEqual("correct", self.fact(card, "epc.floor_area_m2")["status"])
        skipped = self.excluded_for(card, "epc.floor_area_m2")
        self.assertEqual([903], [s["value"] for s in skipped])
        self.assertIn("flat 15", skipped[0]["reason"])

    # --------------------------------------------------- a fallback journey ---
    def test_the_journey_if_the_trains_stop_is_not_the_rail_time(self):
        rep = self.report()
        self.axis(rep, 11)["numbers"] += [
            number("Journey if the train stops", 49, "minutes", sources=("s-tfl",)),
            number("Rail-only journey", 33, "minutes", sources=("s-tfl",))]
        card = self.graded(rep)
        row = self.fact(card, "commute.rail_min")
        self.assertEqual("correct", row["status"])
        self.assertEqual(33, row["reported"])
        skipped = self.excluded_for(card, "commute.rail_min")
        self.assertEqual([49], [s["value"] for s in skipped])
        self.assertIn("fallback journey", skipped[0]["rule"])

    def test_a_wrong_rail_time_is_still_a_fabrication(self):
        rep = self.report()
        self.axis(rep, 11)["numbers"] += [
            number("Journey if the train stops", 49, "minutes", sources=("s-tfl",)),
            number("Rail-only journey", 55, "minutes", sources=("s-tfl",))]
        card = self.graded(rep)
        row = self.fact(card, "commute.rail_min")
        self.assertEqual("wrong", row["status"])
        self.assertEqual(55, row["reported"])
        self.assertEqual(1, card["scores"]["fabrications"])

    def test_the_rail_leg_called_the_fallback_is_still_the_rail_leg(self):
        """A bus commute makes the train the back-up; the label still names it."""
        rep = self.report()
        self.axis(rep, 11)["numbers"].append(
            number("Rail-only fallback", 33, "minutes", sources=("s-tfl",)))
        card = self.graded(rep)
        self.assertEqual("correct", self.fact(card, "commute.rail_min")["status"])
        self.assertEqual([], self.excluded_for(card, "commute.rail_min"))

    # ------------------------------------------- a sale price is not a year ---
    def test_a_first_sale_price_is_not_the_new_build_year(self):
        rep = self.report()
        self.axis(rep, 8)["numbers"] += [
            number("First sale price of this exact flat", 239000, "GBP",
                   sources=("s-plan-1",)),
            number("Earliest new-build sale year", 2010, "year", sources=("s-plan-1",))]
        card = self.graded(rep)
        row = self.fact(card, "landregistry.earliest_new_build_year")
        self.assertEqual("correct", row["status"])
        self.assertEqual(2010, row["reported"])
        skipped = self.excluded_for(card, "landregistry.earliest_new_build_year")
        self.assertEqual([239000], [s["value"] for s in skipped])
        self.assertIn("not a year", skipped[0]["reason"])

    def test_a_price_range_under_a_first_sale_label_is_skipped(self):
        rep = self.report()
        self.axis(rep, 8)["numbers"].append(
            number("First sale prices in the building", "282,270 to 570,000", "GBP",
                   sources=("s-plan-1",)))
        card = self.graded(rep)
        self.assertEqual("missing",
                         self.fact(card, "landregistry.earliest_new_build_year")["status"])
        self.assertEqual(0, card["scores"]["fabrications"])

    def test_a_wrong_new_build_year_is_still_a_fabrication(self):
        rep = self.report()
        self.axis(rep, 8)["numbers"] += [
            number("First sale price of this exact flat", 239000, "GBP",
                   sources=("s-plan-1",)),
            number("Earliest new-build sale year", 2009, "year", sources=("s-plan-1",))]
        card = self.graded(rep)
        row = self.fact(card, "landregistry.earliest_new_build_year")
        self.assertEqual("wrong", row["status"])
        self.assertEqual(1, card["scores"]["fabrications"])

    # ------------------------ the building's age against the certificate's date --
    def test_a_building_age_that_dates_the_building_is_not_the_assessment_year(self):
        """Built 2010, certificate first written 2022: 16 years dates the building."""
        rep = self.report()
        self.axis(rep, 3)["numbers"][0] = number("Building age", 16, "years",
                                                 computed_by="2026 minus 2010")
        card = self.graded(rep)
        row = self.fact(card, "epc.first_assessment_year")
        self.assertEqual("missing", row["status"])
        skipped = [s for s in self.excluded_for(card, "epc.first_assessment_year")
                   if s["value"] == 16]
        self.assertEqual(1, len(skipped), card["referent_excluded"])
        self.assertIn("2010", skipped[0]["reason"])
        self.assertIn("2022", skipped[0]["reason"])
        self.assertEqual(0, card["scores"]["fabrications"])

    def test_a_building_age_that_dates_neither_is_graded_and_counted(self):
        rep = self.report()
        self.axis(rep, 3)["numbers"][0] = number("Building age", 7, "years")
        card = self.graded(rep)
        row = self.fact(card, "epc.first_assessment_year")
        self.assertEqual("wrong", row["status"])          # 2019: neither 2010 nor 2022
        self.assertEqual(7, row["reported"])
        self.assertEqual([], self.excluded_for(card, "epc.first_assessment_year"))
        self.assertEqual(1, card["scores"]["fabrications"])

    def test_a_building_age_is_the_assessment_year_when_the_two_dates_agree(self):
        """The usual case: the block was certified when it was finished. Untouched."""
        rep = self.report()
        self.axis(rep, 3)["numbers"][0] = number("Building age", 16, "years")
        card = self.graded(rep, self.case(epc={"first_assessment_year": 2010}))
        self.assertEqual("correct", self.fact(card, "epc.first_assessment_year")["status"])
        self.assertEqual([], self.excluded_for(card, "epc.first_assessment_year"))

    def test_the_landlords_company_number_is_not_an_assessment_year(self):
        """Labels match whole words: 'age' inside 'management' is not the word 'age', so a
        company row is not a year candidate at all (nothing graded, nothing skipped)."""
        rep = self.report()
        self.axis(rep, 3)["numbers"] = []
        self.axis(rep, 6)["numbers"].append(
            number("Management company and number", "Rennick Walk Management Ltd, 05919132",
                   None, sources=("s-ch-1",)))
        card = self.graded(rep)
        self.assertEqual("missing", self.fact(card, "epc.first_assessment_year")["status"])
        skipped = [s for s in self.excluded_for(card, "epc.first_assessment_year")
                   if "05919132" in str(s["value"])]
        self.assertEqual([], skipped, card["referent_excluded"])

    def test_a_noise_label_is_not_an_assessment_year(self):
        """'Road noise (day-evening-night average)' carried 80.4 dB; 'average' contains 'age'
        and was once graded as an age of 80 years (release gate, 2026-09-17)."""
        rep = self.report()
        self.axis(rep, 3)["numbers"] = []
        self.axis(rep, 12).setdefault("numbers", []).append(
            number("Road noise (day-evening-night average)", 80.4, "decibels", sources=("s-noise",)))
        card = self.graded(rep)
        self.assertEqual("missing", self.fact(card, "epc.first_assessment_year")["status"])

    def test_a_denied_heat_network_is_not_a_heat_network(self):
        self.assertEqual("gas_boiler", grader.classify_heating(
            "Heating is a gas boiler with radiators, not a heat network."))
        self.assertEqual("community_heat_network", grader.classify_heating(
            "Heat comes from the estate's heat network; there is no gas boiler in the flat."))

    def test_two_certificates_side_by_side_grade_the_current_one(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Area, certificate 0857 (Jan 2009)", 463, "square feet", sources=("s-epc-5b",)),
            number("Area, certificate 9238 (Apr 2009)", 592, "square feet", sources=("s-epc-5a",))]
        card = self.graded(rep, self.case(epc={"floor_area_m2": 55.0, "floor_area_sqft": 592}))
        row = self.fact(card, "epc.floor_area_m2")
        self.assertEqual("correct", row["status"])
        self.assertIn("one of 2 listed areas", row["where"])

    def test_a_grade_shade_is_the_same_letter(self):
        rep = self.report()
        rep["candidates"][0].setdefault("metrics", {})["commute_redundancy_grade"] = {
            "value": "B-", "unit": "grade A/B/C", "sources": ["s-tfl"]}
        card = self.graded(rep, self.case(commute={"redundancy_grade": "B"}))
        self.assertEqual("correct", self.fact(card, "commute.redundancy_grade")["status"])

    # ------------------------------------------------------- the audit trail --
    def test_the_metric_slots_are_never_guarded(self):
        """The schema gives one metric key per fact, so a value there is the answer."""
        rep = self.report()
        rep["candidates"][0]["metrics"]["crime_6mo_count"]["value"] = 1000
        for num in self.axis(rep, 5)["numbers"]:
            num["label"] = "Recorded crimes over time"
        card = self.graded(rep)
        row = self.fact(card, "crime.total")
        self.assertEqual("wrong", row["status"])
        self.assertEqual("candidates[0].metrics.crime_6mo_count", row["where"])
        self.assertEqual([], self.excluded_for(card, "crime.total"))

    def test_every_exclusion_is_written_down_with_its_reason(self):
        rep = self.report()
        self.axis(rep, 2)["numbers"] = [
            number("Certified area, 2010 as-built certificate", 441, "square feet")]
        card = self.graded(rep)
        row = card["referent_excluded"][0]
        self.assertEqual(["fact", "where", "label", "value", "unit", "rule", "reason"],
                         list(row.keys()))
        self.assertEqual("epc.floor_area_m2", row["fact"])
        self.assertIn("axes[id=2].numbers[0]", row["where"])
        self.assertEqual(len(card["referent_excluded"]), card["counts"]["referent_excluded"])

    def test_a_clean_report_excludes_nothing_and_the_summary_is_unchanged(self):
        card = self.card_for(copy.deepcopy(self.sample))
        self.assertEqual([], card["referent_excluded"])
        self.assertEqual(0, card["counts"]["referent_excluded"])
        self.assertIn("0 fabrications", card["summary"])
        self.assertTrue(card["summary"].startswith(SYNTHETIC_CASE["id"] + ":"))

    def test_the_rules_are_printed_by_explain(self):
        text = grader.explain()
        self.assertIn("referent_excluded", text)
        self.assertIn("a fallback journey", text)
        self.assertIn("a price, not a year", text)


# ----------------------------------------------------------------- the suite --
class TestEvalSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read_json(EVALS_JSON)
        cls.reports = [c for c in cls.doc["evals"] if c.get("kind", "report") == "report"]
        cls.talks = [c for c in cls.doc["evals"] if c.get("kind") == "conversation"]

    def test_shape(self):
        self.assertEqual("vet-flat", self.doc["skill_name"])
        self.assertTrue(6 <= len(self.reports) <= 8,
                        "the suite should hold 6 to 8 flat cases, it holds %d" % len(self.reports))
        self.assertEqual(2, len(self.talks))
        self.assertEqual(["explain-capabilities", "no-idea-intake"],
                         sorted(c["id"] for c in self.talks))

    def test_every_case_is_complete(self):
        ids = set()
        for case in self.doc["evals"]:
            for key in ("id", "prompt", "files", "expected_output", "assertions",
                        "expected_facts"):
                self.assertIn(key, case, case.get("id"))
            self.assertNotIn(case["id"], ids, "duplicate case id")
            ids.add(case["id"])
            self.assertTrue(case["assertions"], case["id"])
            for rel in case["files"]:
                path = os.path.join(ROOT, "evals", rel)
                self.assertTrue(os.path.exists(path), "missing case file %s" % rel)

    def test_at_least_four_boroughs(self):
        boroughs = set(c.get("borough") for c in self.reports if c.get("borough"))
        self.assertGreaterEqual(len(boroughs), 4, boroughs)

    def test_no_private_case_postcodes(self):
        banned_exact = {"SE8 3GS", "SE8 3FW", "SE10 0TS", "E1 3FY", "E1 8LX", "SE17 3BZ",
                        "SE1 0BF", "SE1 6EG", "N7 7FF"}
        banned_outcode = {"SE3", "EC4A", "E1W", "SE13", "E16"}
        for case in self.reports:
            pc = case["truth_inputs"]["postcode"].upper()
            self.assertNotIn(pc, banned_exact, case["id"])
            self.assertNotIn(pc.split()[0], banned_outcode, case["id"])

    def test_every_fact_carries_a_command_and_a_time(self):
        for case in self.reports:
            for name, block in case["expected_facts"].items():
                if name == "geo":
                    continue
                self.assertIn("command", block, "%s/%s" % (case["id"], name))
                self.assertIn("retrieved_at", block, "%s/%s" % (case["id"], name))
                self.assertFalse(block.get("stale"), "%s/%s is stale" % (case["id"], name))

    def test_the_raw_output_is_kept_next_to_every_fact(self):
        for case in self.reports:
            for name, block in case["expected_facts"].items():
                raw = block.get("raw")
                if raw is None:
                    continue
                self.assertTrue(os.path.exists(os.path.join(ROOT, raw)),
                                "missing raw output %s" % raw)

    def test_the_stable_facts_are_present(self):
        for case in self.reports:
            epc = case["expected_facts"]["epc"]
            self.assertIsNotNone(epc["floor_area_m2"], case["id"])
            self.assertIsNotNone(epc["first_assessment_year"], case["id"])
            self.assertIn(epc["heating_class"],
                          ("community_heat_network", "heat_pump", "gas_boiler", "electric",
                           "unknown"), case["id"])
            self.assertIn(epc["energy_rating"], list("ABCDEFG"), case["id"])

    def test_every_case_can_be_graded_end_to_end(self):
        """A report that says nothing still produces a scorecard, never an exception."""
        empty = read_json(SAMPLE)
        empty["candidates"] = [{
            "id": "c1",
            "identity": {"display_name": "x", "postcode": "SE1 9SG"},
            "verdict": {"status": "PASS", "headline": "x", "reason_codes": []},
            "hard_filters": [], "axes": empty["candidates"][0]["axes"],
            "costs": empty["candidates"][0]["costs"], "landmines": [],
        }]
        del empty["comparison"]
        for case in self.reports:
            profile = grader.case_profile_path(EVALS_JSON, case)
            card = grader.grade(empty, case, profile)
            self.assertIn("scores", card)
            self.assertGreater(card["counts"]["gradeable"], 0, case["id"])


# --------------------------------------------------------- the question bank --
BANK_QUESTION_L6 = ("Is heating and hot water on a communal heat network? Please send the "
                    "current standing charge and unit rate in writing, and name the billing "
                    "company.")
BANK_QUESTION_G1 = ("Which guarantor or income-check routes do you accept for this tenancy: a "
                    "UK guarantor, rent-guarantee insurance, a commercial guarantor service, or "
                    "proof of funds?")
BANK_QUESTION_G2 = ("Is the flat still available for a move-in on or after 15 September, and "
                    "what is the earliest date I could take the keys?")
VAGUE = ["Is the flat nice?", "Is the building well managed?"]


class TestQuestionBank(unittest.TestCase):
    def test_the_real_bank_parses(self):
        bank = grader.parse_question_bank()
        self.assertTrue(bank, "references/questions.md produced no questions")
        codes = set(e["code"].upper() for e in bank)
        for gate in ("G1", "G2", "G3", "G4"):
            self.assertIn(gate, codes)
        for i in range(1, 13):
            self.assertIn("L%d" % i, codes, "the bank has no question for landmine L%d" % i)
        for entry in bank:
            self.assertTrue(entry["question"].strip())
            self.assertNotIn("|", entry["question"])

    def test_the_bank_is_read_from_the_file_so_edits_flow_through(self):
        handle, path = tempfile.mkstemp(suffix=".md")
        os.close(handle)
        try:
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("## Gate questions\n\n"
                         "| Code | Question (send verbatim) | Why |\n"
                         "|---|---|---|\n"
                         "| G9 | Who empties the bins and how often is the bin store cleaned? "
                         "| smell |\n\n"
                         "## Viewing-day questions\n\n"
                         "- \"Can I see the meter cupboard?\"\n")
            bank = grader.parse_question_bank(path)
            self.assertEqual(["G9", "VIEW"], [e["code"] for e in bank])
            self.assertIn("bin", bank[0]["words"])
        finally:
            os.unlink(path)

    def test_a_missing_bank_is_not_a_crash(self):
        self.assertEqual([], grader.parse_question_bank("/nonexistent/questions.md"))

    def test_content_words_drop_stopwords_and_plurals(self):
        words = grader.content_words("Please send the current tariffs and the unit rates.")
        self.assertIn("tariff", words)
        self.assertIn("rate", words)
        self.assertNotIn("the", words)
        self.assertNotIn("please", words)

    def test_codes_are_read_out_of_a_question(self):
        self.assertEqual({"L6", "G1"},
                         grader.codes_in("Because of L6 and G1 I need the tariff."))
        self.assertEqual({"L12"}, grader.codes_in("landmine L-12 applies"))


class TestKillerQuestions(GradeBase):
    def report_with(self, questions, landmines=None, reason_codes=None, hard_filters=None):
        rep = copy.deepcopy(self.sample)
        rep["candidates"] = [copy.deepcopy(rep["candidates"][0])]
        del rep["comparison"]
        cand = rep["candidates"][0]
        cand["killer_questions"] = questions
        if landmines is not None:
            cand["landmines"] = landmines
        if reason_codes is not None:
            cand["verdict"]["reason_codes"] = reason_codes
        if hard_filters is not None:
            cand["hard_filters"] = hard_filters
        return rep

    def test_a_question_quoting_the_bank_passes(self):
        card = self.card_for(self.report_with([BANK_QUESTION_L6]))
        self.assertEqual(1.0, card["scores"]["killer_questions_from_bank"])
        row = card["killer_questions"][0]
        self.assertTrue(row["grounded"])
        self.assertEqual("from the bank", row["how"])
        self.assertEqual("L6", row["best_bank_code"])

    def test_a_close_paraphrase_of_a_bank_question_passes(self):
        paraphrase = ("Please send the current standing charge and unit rate for the communal "
                      "heat network in writing, and name the billing company.")
        card = self.card_for(self.report_with([paraphrase]))
        self.assertEqual(1.0, card["scores"]["killer_questions_from_bank"])

    def test_vague_questions_fail(self):
        card = self.card_for(self.report_with(VAGUE))
        self.assertEqual(0.0, card["scores"]["killer_questions_from_bank"])
        for row in card["killer_questions"]:
            self.assertFalse(row["grounded"], row)
        self.assertEqual("too vague", card["killer_questions"][0]["how"])

    def test_a_short_question_cannot_match_on_one_shared_word(self):
        """'Is the flat nice?' shares 'flat' with a bank question. That is not a question."""
        card = self.card_for(self.report_with(["Is the flat nice?"]))
        row = card["killer_questions"][0]
        self.assertFalse(row["grounded"])
        self.assertLess(row["content_words"], grader.MIN_CONTENT_WORDS)

    def test_citing_a_code_the_report_raised_passes(self):
        rep = self.report_with(
            ["Given landmine L6, what will heat actually cost me each winter month?"],
            landmines=[{"code": "L6", "label": "Heat network", "detail": "No tariff in writing.",
                        "reversible": False, "evidence_class": "I"}])
        card = self.card_for(rep)
        row = card["killer_questions"][0]
        self.assertTrue(row["grounded"])
        self.assertEqual("cites a code the report raised", row["how"])

    def test_citing_a_code_the_report_never_raised_does_not_pass(self):
        rep = self.report_with(["Given landmine L11, is it warm?"], landmines=[])
        card = self.card_for(rep)
        self.assertFalse(card["killer_questions"][0]["grounded"])

    def test_a_reason_code_counts_as_raised(self):
        rep = self.report_with(
            ["L6 is the reason: which billing company runs the heat account here?"],
            landmines=[{"code": "L6", "label": "Heat network", "detail": "x",
                        "reversible": False, "evidence_class": "I"}],
            reason_codes=["L6"])
        card = self.card_for(rep)
        self.assertTrue(card["killer_questions"][0]["grounded"])

    def test_no_questions_at_all_scores_zero(self):
        card = self.card_for(self.report_with([]))
        self.assertEqual(0.0, card["scores"]["killer_questions_from_bank"])
        self.assertIn("no killer question", card["killer_questions_note"])

    def test_a_blank_question_is_not_a_question(self):
        card = self.card_for(self.report_with([BANK_QUESTION_L6, "   "]))
        self.assertEqual(0.5, card["scores"]["killer_questions_from_bank"])
        self.assertEqual("blank", card["killer_questions"][1]["how"])

    def test_one_of_two_grounded_scores_half(self):
        card = self.card_for(self.report_with([BANK_QUESTION_L6, "Is the flat nice?"]))
        self.assertEqual(0.5, card["scores"]["killer_questions_from_bank"])
        self.assertEqual(1, card["counts"]["killer_questions_grounded"])
        self.assertEqual(2, card["counts"]["killer_questions"])

    def test_the_scorecard_names_the_bank_it_used(self):
        card = self.card_for(self.report_with([BANK_QUESTION_L6]))
        self.assertIn("questions.md", card["question_bank"]["path"])
        self.assertGreater(card["question_bank"]["entries"], 15)


class TestGateQuestions(TestKillerQuestions):
    MOVE_IN_UNKNOWN = {"name": "Move-in date",
                       "requirement": "Keys between 2026-09-15 and 2026-10-15",
                       "observed": "The advert says available from October; no exact date",
                       "pass": "unknown", "evidence_class": "S"}
    GUARANTOR_UNKNOWN = {"name": "Guarantor route",
                         "requirement": "A guarantor route the landlord accepts",
                         "observed": "Nobody has said which income-check routes are accepted",
                         "pass": "unknown", "evidence_class": "U"}

    def test_an_open_gate_that_is_never_asked_about_fails(self):
        rep = self.report_with([BANK_QUESTION_L6], hard_filters=[self.MOVE_IN_UNKNOWN])
        card = self.card_for(rep)
        self.assertEqual(0.0, card["scores"]["gate_questions_present"])
        gate = card["gates"][0]
        self.assertEqual("G2", gate["gate"])
        self.assertFalse(gate["asked"])
        self.assertIn("unknown", gate["why_open"])

    def test_asking_the_gate_question_covers_it(self):
        rep = self.report_with([BANK_QUESTION_G2], hard_filters=[self.MOVE_IN_UNKNOWN])
        card = self.card_for(rep)
        self.assertEqual(1.0, card["scores"]["gate_questions_present"])
        self.assertTrue(card["gates"][0]["asked"])

    def test_naming_the_gate_code_covers_it(self):
        rep = self.report_with(
            ["G2: is the flat still free for a move-in in the second half of September?"],
            hard_filters=[self.MOVE_IN_UNKNOWN])
        card = self.card_for(rep)
        self.assertTrue(card["gates"][0]["asked"])
        self.assertEqual("names G2", card["gates"][0]["how"])

    def test_the_guarantor_gate_opens_on_an_unknown_income_check(self):
        rep = self.report_with([BANK_QUESTION_G1], hard_filters=[self.GUARANTOR_UNKNOWN])
        card = self.card_for(rep)
        self.assertEqual(["G1"], [g["gate"] for g in card["gates"]])
        self.assertEqual(1.0, card["scores"]["gate_questions_present"])

    def test_two_open_gates_need_only_one_answer_while_there_are_two_slots(self):
        """The bank's rule 1: the first message is one gate question plus one killer."""
        rep = self.report_with([BANK_QUESTION_G1, BANK_QUESTION_L6],
                               hard_filters=[self.MOVE_IN_UNKNOWN, self.GUARANTOR_UNKNOWN])
        card = self.card_for(rep)
        self.assertEqual(2, card["counts"]["gates_open"])
        self.assertEqual(1, card["counts"]["gates_expected"])
        self.assertEqual(1.0, card["scores"]["gate_questions_present"])

    def test_no_open_gate_means_no_score(self):
        rep = self.report_with([BANK_QUESTION_L6], hard_filters=[])
        rep["not_found"] = []
        for axis in rep["candidates"][0]["axes"]:
            axis.pop("unknowns", None)
            if axis.get("evidence_class") == "U":
                axis["evidence_class"] = "I"
        card = self.card_for(rep)
        self.assertEqual([], card["gates"])
        self.assertIsNone(card["scores"]["gate_questions_present"])

    def test_a_building_site_start_date_is_not_the_flats_availability(self):
        """The G2 keywords must not fire on 'construction start date' in not_found."""
        rep = self.report_with([BANK_QUESTION_L6], hard_filters=[])
        rep["not_found"] = [{"what": "The expected construction start date for the scheme "
                                     "next door",
                             "queries_used": ["planning portal 26/AP/0812"]}]
        for axis in rep["candidates"][0]["axes"]:
            axis.pop("unknowns", None)
            if axis.get("evidence_class") == "U":
                axis["evidence_class"] = "I"
        card = self.card_for(rep)
        self.assertEqual([], card["gates"], card["gates"])


# ------------------------------------------------------- conversation cases --
GOOD_EN = """I check a London rental flat the way a careful surveyor would, using official and
open UK data, and I run 12 checks on it: the government energy certificate for the true size,
age and heating, police crime data, planning applications next door, the company behind the
landlord or agent, the price against the local band, the light, the all-in monthly cost and the
commute with a backup line.

You get one plain verdict: PASS to go and see it, EDGE only at a lower rent, CONDITIONAL if
named conditions are met in writing, or KILL. Three ways to start: give me a listing link, give
me an area or the place you commute to, or say you have no idea and I will explain the basics
and ask six questions.

With a shell and internet I fetch the data myself. In a plain chat box I list the pages for you
to paste. Rightmove, Zoopla and HomeViews forbid automated access, so I do not read them; I ask
you to paste the page instead."""

GOOD_ZH = """我用英國官方與公開資料審查一間倫敦出租公寓，跑 12 項檢查：政府能源證書（真實坪數、
屋齡、供暖）、警方犯罪資料、隔壁的規劃申請、房東或仲介背後的公司、價格、採光、每月全部成本、
通勤與備援路線。

最後給你一個判決：通過、邊緣、有條件或淘汰。

三種開始方式：你有房源連結；你只知道地區或每天要去的目的地；或者你完全沒有頭緒。

有終端機和網路時我自己抓資料；只有對話框時我列出要你貼給我的頁面。Rightmove、Zoopla、
HomeViews 禁止自動抓取，我不會去抓。"""

BAD_SCRAPE = """I scrape Rightmove and Zoopla for you and pull the reviews from HomeViews
automatically, then score the flat out of 10. Just give me a link."""

GOOD_INTAKE = """Six questions, one message. Answer what you can; for the rest I will use the
suggested default and say so.

1. Where do you need to get to most days, and by what time? This one I cannot guess for you.
2. The most you can pay per month for everything - rent, energy, water, broadband, council tax?
   For example, rent alone is usually 80 to 90 percent of that in a modern flat.
3. When do you need to move in, earliest and latest? Default: today plus three weeks, and plus
   eight weeks.
4. What kind of home and how much space? Default: a one-bedroom with a real door, at least 450
   square feet indoors on the government certificate.
5. Deal-breakers? Default: no ground floor and a washing machine in the flat.
6. How will you pass the landlord's income check? Default: most people show income of about
   thirty times the monthly rent, or use a guarantor.

First step: give me your destination and I will sweep the areas around it and compare the
buildings side by side.

Worth knowing now: since 2026-05-01 tenancies are periodic, a landlord may take at most 1
month's rent in advance, the deposit is capped at 5 weeks' rent and a holding deposit at 1
week."""

BAD_INTAKE = """What is your budget? Where do you want to live? When are you moving? What is
your nationality, and do you have a visa? Do you have a guarantor? How many bedrooms? Do you
smoke?

The Renters' Rights Act came into force on 2025-10-01. The deposit is capped at 8 weeks' rent
and you will normally be asked for 6 months in advance."""


class TestConversationCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc = read_json(EVALS_JSON)
        cls.cases = {c["id"]: c for c in doc["evals"]}

    def card(self, case_id, text, variant=None):
        return grader.grade_conversation(text, self.cases[case_id], variant)

    def check(self, card, name):
        for row in card["checks"]:
            if row["check"] == name:
                return row
        self.fail("no check called %s" % name)

    def test_a_good_english_answer_passes_every_check(self):
        card = self.card("explain-capabilities", GOOD_EN, "en")
        failed = [c["check"] for c in card["checks"] if c["status"] == "fail"]
        self.assertEqual([], failed, card["checks"])
        self.assertEqual(1.0, card["scores"]["fact_recall"])
        self.assertEqual(0, card["scores"]["fabrications"])
        self.assertTrue(card["meets_pass_line"])

    def test_verdicts_count_in_either_language(self):
        card = self.card("explain-capabilities", GOOD_ZH, "zh")
        self.assertEqual("pass", self.check(card, "mentions_verdict_statuses")["status"])
        self.assertEqual("pass", self.check(card, "answers_in_user_language")["status"])

    def test_a_chinese_answer_to_an_english_question_fails_the_language_check(self):
        card = self.card("explain-capabilities", GOOD_ZH, "en")
        self.assertEqual("fail", self.check(card, "answers_in_user_language")["status"])

    def test_an_english_answer_to_a_chinese_question_fails_the_language_check(self):
        card = self.card("explain-capabilities", GOOD_EN, "zh")
        self.assertEqual("fail", self.check(card, "answers_in_user_language")["status"])

    def test_claiming_to_scrape_a_portal_is_a_fabrication(self):
        card = self.card("explain-capabilities", BAD_SCRAPE, "en")
        row = self.check(card, "no_scraping_claim")
        self.assertEqual("fail", row["status"])
        self.assertTrue(row["fabrication_on_fail"])
        self.assertGreaterEqual(card["scores"]["fabrications"], 1)
        self.assertFalse(card["meets_pass_line"])

    def test_saying_it_does_not_scrape_is_not_a_claim(self):
        card = self.card("explain-capabilities", GOOD_EN, "en")
        self.assertEqual("pass", self.check(card, "no_scraping_claim")["status"])

    def test_an_over_long_answer_fails_the_length_check(self):
        card = self.card("explain-capabilities", GOOD_EN + ("x" * 2000), "en")
        self.assertEqual("fail", self.check(card, "length_within_limit")["status"])

    def test_a_good_intake_passes_every_check(self):
        card = self.card("no-idea-intake", GOOD_INTAKE, "en")
        failed = [c["check"] for c in card["checks"] if c["status"] == "fail"]
        self.assertEqual([], failed, card["checks"])
        self.assertTrue(card["meets_pass_line"])

    def test_too_many_questions_and_no_defaults_are_caught(self):
        card = self.card("no-idea-intake", BAD_INTAKE, "en")
        self.assertEqual("fail", self.check(card, "asks_at_most_six_questions_in_one_message")["status"])
        self.assertEqual("fail", self.check(card, "each_question_has_a_suggested_default")["status"])

    def test_wrong_legal_numbers_are_fabrications(self):
        card = self.card("no-idea-intake", BAD_INTAKE, "en")
        for name in ("renters_rights_act_in_force_date", "deposit_cap_weeks",
                     "rent_in_advance_max_months"):
            self.assertEqual("fail", self.check(card, name)["status"], name)
        self.assertEqual(3, card["scores"]["fabrications"])

    def test_a_legal_number_not_stated_is_skipped_not_failed(self):
        card = self.card("no-idea-intake", BAD_INTAKE, "en")
        self.assertEqual("skipped", self.check(card, "holding_deposit_weeks")["status"])

    def test_asking_about_nationality_is_critical(self):
        card = self.card("no-idea-intake", BAD_INTAKE, "en")
        row = self.check(card, "never_asks_nationality_or_ethnicity")
        self.assertEqual("fail", row["status"])
        self.assertTrue(row["critical"])
        self.assertEqual(1, card["counts"]["critical_failures"])
        self.assertFalse(card["meets_pass_line"])

    def test_mentioning_a_protected_characteristic_without_asking_is_fine(self):
        text = GOOD_INTAKE + ("\n\nA landlord may not lawfully select on nationality or "
                              "ethnicity, so I never ask and never record it.")
        card = self.card("no-idea-intake", text, "en")
        self.assertEqual("pass", self.check(card, "never_asks_nationality_or_ethnicity")["status"])

    def test_the_skill_own_pitch_passes_its_own_eval(self):
        """onboarding.md is what the model is told to answer from. It must score."""
        path = os.path.join(ROOT, "skills", "vet-flat", "references", "onboarding.md")
        if not os.path.exists(path):
            self.skipTest("references/onboarding.md is not in the tree yet")
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        if "**English**" not in text or "**繁體中文**" not in text:
            self.skipTest("onboarding.md no longer carries the pitch markers this test reads")
        pitch = text.split("**English**")[1].split("**繁體中文**")[0].strip().lstrip("> ")
        starts = ("\n1. I have a listing -> paste the link and I vet it (the 12 checks).\n"
                  "2. I have an area or a place I commute to -> I sweep around it.\n"
                  "3. I have no idea -> I explain the basics and ask six questions.\n"
                  "The verdict is PASS, EDGE, CONDITIONAL or KILL.")
        card = self.card("explain-capabilities", pitch + starts, "en")
        failed = [c["check"] for c in card["checks"] if c["status"] == "fail"]
        self.assertEqual([], failed, card["checks"])


# ----------------------------------------------------------------- dry runs --
def dry_run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = runner.main(argv)
    return code, buf.getvalue()


class TestRunDryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_id = read_json(EVALS_JSON)["evals"][0]["id"]
        cls.talk_id = "explain-capabilities"

    def test_claude_command(self):
        code, out = dry_run(["--agent", "claude", "--case", self.case_id, "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("claude -p", out)
        self.assertIn("--allowedTools", out)
        self.assertIn("Bash(python3:*)", out)
        self.assertIn("--output-format json", out)
        self.assertIn(".claude/skills/vet-flat", out)

    def test_claude_command_takes_a_model(self):
        code, out = dry_run(["--agent", "claude", "--case", self.case_id, "--model", "opus",
                             "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("--model opus", out)

    def test_codex_command(self):
        code, out = dry_run(["--agent", "codex", "--case", self.case_id, "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("codex exec", out)
        self.assertIn("--sandbox workspace-write", out)
        self.assertIn("sandbox_workspace_write.network_access=true", out)
        self.assertIn(".agents/skills/vet-flat", out)

    def test_no_permission_bypass_flags_anywhere(self):
        forbidden = ["--dangerously-skip-permissions", "--yolo", "--bypass",
                     "--dangerously-bypass-approvals-and-sandbox", "--full-auto",
                     "--sandbox danger-full-access", "--approval-policy never",
                     "--auto-approve", "--force"]
        for agent in ("claude", "codex", "gemini", "opencode"):
            _code, out = dry_run(["--agent", agent, "--case", self.case_id, "--dry-run"])
            for flag in forbidden:
                self.assertNotIn(flag, out, "%s command carries %s" % (agent, flag))

    def test_untested_agents_say_so(self):
        for agent in ("gemini", "opencode"):
            _code, out = dry_run(["--agent", agent, "--case", self.case_id, "--dry-run"])
            self.assertIn("UNTESTED", out)

    def test_api_mode_describes_the_paste(self):
        code, out = dry_run(["--agent", "api", "--case", self.case_id, "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("chat/completions", out)
        self.assertIn("INSTRUCTIONS.md", out)
        self.assertIn("fixtures pasted", out)

    def test_the_prompt_is_the_case_prompt(self):
        case = read_json(EVALS_JSON)["evals"][0]
        _code, out = dry_run(["--agent", "claude", "--case", case["id"], "--dry-run"])
        self.assertIn(case["prompt"], out)


class TestConversationDryRun(unittest.TestCase):
    def test_both_language_variants_are_run(self):
        code, out = dry_run(["--agent", "claude", "--case", "explain-capabilities", "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("explain-capabilities#zh", out)
        self.assertIn("explain-capabilities#en", out)
        self.assertIn("這能幹嘛？", out)
        self.assertIn("What can this do?", out)

    def test_one_variant_can_be_selected(self):
        code, out = dry_run(["--agent", "claude", "--case", "explain-capabilities",
                             "--variant", "zh", "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("這能幹嘛？", out)
        self.assertNotIn("explain-capabilities#en", out)

    def test_the_answer_is_what_gets_graded(self):
        _code, out = dry_run(["--agent", "claude", "--case", "no-idea-intake", "--dry-run"])
        self.assertIn("the plain-text answer", out)
        self.assertIn("a conversation, no flat", out)

    def test_a_flat_case_still_says_it_grades_the_report(self):
        case_id = read_json(EVALS_JSON)["evals"][0]["id"]
        _code, out = dry_run(["--agent", "claude", "--case", case_id, "--dry-run"])
        self.assertIn("report.json, against expected_facts", out)

    def test_api_mode_pastes_nothing_for_a_conversation_case(self):
        _code, out = dry_run(["--agent", "api", "--case", "explain-capabilities", "--dry-run"])
        self.assertIn("the case prompt, nothing else", out)
        self.assertNotIn("fixtures pasted", out)


class TestRefreshTruth(unittest.TestCase):
    def test_conversation_cases_are_not_refreshed_by_a_fetcher(self):
        """Their truth is SKILL.md and onboarding.md, so no register can refresh them."""
        import refresh_truth
        doc = read_json(EVALS_JSON)
        talks = [c for c in doc["evals"] if c.get("kind") == "conversation"]
        self.assertTrue(talks)
        for case in talks:
            with self.assertRaises(KeyError):
                refresh_truth.plan_commands(case)

    def test_every_flat_case_has_a_command_plan(self):
        import refresh_truth
        doc = read_json(EVALS_JSON)
        for case in doc["evals"]:
            if case.get("kind") == "conversation":
                continue
            cmds = refresh_truth.plan_commands(case)
            names = [os.path.basename(c[1]) for c in cmds]
            for want in ("geo.py", "epc.py", "crime.py", "commute.py"):
                self.assertIn(want, names, case["id"])


class TestJsonRecovery(unittest.TestCase):
    def test_first_json_object_skips_prose_and_fences(self):
        blob = 'Here you go.\n```json\n{"candidates": [{"id": "c1"}]}\n```\nDone.'
        self.assertEqual({"candidates": [{"id": "c1"}]}, runner.first_json_object(blob))

    def test_braces_inside_strings_do_not_confuse_it(self):
        blob = '{"note": "a } inside a string", "n": 1}'
        self.assertEqual({"note": "a } inside a string", "n": 1},
                         runner.first_json_object(blob))

    def test_no_json_at_all(self):
        self.assertIsNone(runner.first_json_object("nothing here"))


if __name__ == "__main__":
    unittest.main()
