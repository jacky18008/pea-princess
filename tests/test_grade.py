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
