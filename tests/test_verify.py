# -*- coding: utf-8 -*-
"""scripts/verify.py: every rule gets a pair - correct evidence must not trigger it,
wrong evidence must.

The lesson this file is built on comes from the maintainer's earlier ablation: a
deterministic grader has its own failure mode, and unlike a judge model it never tells
you it is wrong. So no rule is trusted on the strength of firing; each one has to stay
silent on evidence that is right, and fire on the one thing that is wrong, with
everything else held constant.
"""
import copy
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
FIX = os.path.join(HERE, "fixtures", "pipeline")
SOURCES = os.path.join(FIX, "sources")

sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(ROOT, "bench"))
import referents  # noqa: E402
import verify as V  # noqa: E402


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def run(evidence, tier="lite", strict=False, report=None, gold=None):
    return V.verify(evidence, report if report is not None else load("report-stub.json"),
                    V.load_sources(SOURCES), tier, strict, gold=gold)


def state(result, item_id):
    for verdict in result["items"]:
        if verdict["id"] == item_id:
            return verdict
    raise AssertionError("no verdict for %s" % item_id)


def item(evidence, item_id):
    for entry in evidence["items"]:
        if entry["id"] == item_id:
            return entry
    raise AssertionError("no item %s" % item_id)


class CorrectEvidenceIsLeftAlone(unittest.TestCase):
    """The half that is easy to forget: a rule that fires on a right answer is worse
    than no rule, because it looks like diligence."""

    def setUp(self):
        self.result = run(load("evidence-good.json"))

    def test_nothing_fails(self):
        failures = [v for v in self.result["items"] if v["state"] == "fail"]
        self.assertEqual(failures, [], "clean evidence must not trigger any rule")
        self.assertFalse(V.failed(self.result))

    def test_the_one_unknown_is_the_one_nobody_could_get(self):
        self.assertEqual(self.result["counts"]["unknown"], 1)
        self.assertEqual(state(self.result, "e-reviews")["state"], "unknown")

    def test_an_unknown_with_a_tried_list_survives_strict(self):
        self.assertFalse(V.failed(run(load("evidence-good.json"), strict=True)))

    def test_the_legal_caps_are_recomputed_from_the_evidence(self):
        caps = self.result["counts"]["legal_caps"]
        self.assertEqual(caps["rent_pcm"], 2000.0)
        self.assertEqual(caps["deposit_cap_weeks"], 5)
        self.assertAlmostEqual(caps["deposit_cap_gbp"], 2307.69, places=2)
        self.assertIn("e-rent", caps["rent_pcm_from"])

    def test_the_fixed_form_is_complete_at_this_tier(self):
        self.assertEqual(self.result["counts"]["fixed_form_missing"], [])

    def test_every_quote_was_actually_read(self):
        self.assertEqual(self.result["counts"]["quotes_unchecked"], [])

    def test_a_pass_nobody_could_check_is_counted_as_such(self):
        """A run whose passes were never read is a different thing from one whose
        passes were, and the scorecard has to be able to tell them apart."""
        result = V.verify(load("evidence-good.json"), load("report-stub.json"), {}, "lite")
        self.assertIn("e-area", result["counts"]["quotes_unchecked"])


class WrongEvidenceMustTrigger(unittest.TestCase):
    """One mutation at a time, from the same clean base, so a firing rule can only be
    about the thing that changed."""

    def base(self):
        return copy.deepcopy(load("evidence-good.json"))

    def test_a_quote_that_is_not_in_the_source(self):
        ev = self.base()
        item(ev, "e-area")["quote"] = "The certificate gives the area as fifty-four metres."
        verdict = state(run(ev), "e-area")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("quote_in_source", verdict["rules"])

    def test_a_quote_rewrapped_but_not_reworded_still_passes(self):
        ev = self.base()
        item(ev, "e-area")["quote"] = "Total floor area:\n   54    square metres."
        self.assertEqual(state(run(ev), "e-area")["state"], "pass",
                         "whitespace is normalised; only the words have to match")

    def test_a_source_id_that_resolves_nowhere(self):
        ev = self.base()
        item(ev, "e-crime")["source"] = "made-up-register"
        verdict = state(run(ev), "e-crime")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("source_resolves", verdict["rules"])

    def test_a_number_with_no_unit(self):
        ev = self.base()
        del item(ev, "e-area")["unit"]
        verdict = state(run(ev), "e-area")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("unit_present", verdict["rules"])

    def test_the_building_is_not_the_flat(self):
        ev = self.base()
        target = item(ev, "e-area")
        target["claim"] = "certified floor area"
        target["note"] = "measured over the whole block"
        target["value"] = 910.0
        verdict = state(run(ev), "e-area")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("referent:building_not_flat", verdict["rules"])

    def test_a_replaced_certificate_is_not_the_one_in_force(self):
        ev = self.base()
        target = item(ev, "e-rating")
        target["claim"] = "energy rating"
        target["note"] = "from the previous certificate, since replaced"
        verdict = state(run(ev), "e-rating")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("referent:superseded_certificate", verdict["rules"])

    def test_another_flats_number_is_not_this_flats(self):
        ev = self.base()
        item(ev, "e-area")["note"] = "this is the figure for flat 12"
        verdict = state(run(ev), "e-area")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("referent:another_flat", verdict["rules"])

    def test_the_deposit_cap_branch_above_fifty_thousand_a_year(self):
        ev = self.base()
        item(ev, "e-rent")["value"] = 5000        # £60,000 a year: the cap is six weeks
        item(ev, "e-f1")["claim"] = "F1 legal deposit cap for this tenancy"
        verdict = state(run(ev), "e-f1")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("deposit_cap_branch", verdict["rules"])
        self.assertIn("60000", verdict["reason"])

    def test_the_same_cap_below_the_threshold_is_right(self):
        ev = self.base()
        item(ev, "e-f1")["claim"] = "F1 legal deposit cap for this tenancy"
        self.assertEqual(state(run(ev), "e-f1")["state"], "pass",
                         "five weeks is the right branch at £24,000 a year")

    def test_a_deposit_over_the_cap(self):
        ev = self.base()
        item(ev, "e-f1")["value"] = 8
        verdict = state(run(ev), "e-f1")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("deposit_over_cap", verdict["rules"])

    def test_a_holding_deposit_over_one_week(self):
        ev = self.base()
        item(ev, "e-f2")["value"] = 2
        self.assertIn("holding_deposit_cap", state(run(ev), "e-f2")["rules"])

    def test_more_than_one_month_in_advance(self):
        ev = self.base()
        item(ev, "e-f3")["value"] = 6
        self.assertIn("rent_in_advance_cap", state(run(ev), "e-f3")["rules"])

    def test_the_listing_area_against_the_certificate_area(self):
        ev = self.base()
        ev["items"].append({"id": "e-area-advert", "axis": 2,
                            "claim": "advertised floor area from the listing", "status": "ok",
                            "value": 62.0, "unit": "m2", "source": "pasted:listing",
                            "quote": "Advertised floor area: 62 square metres, including "
                                     "the balcony."})
        result = run(ev)
        self.assertEqual(result["counts"]["contradictions"], 1)
        for ident in ("e-area", "e-area-advert"):
            self.assertIn("contradiction:area", state(result, ident)["rules"])

    def test_two_areas_that_agree_are_not_a_contradiction(self):
        ev = self.base()
        ev["items"].append({"id": "e-area-advert", "axis": 2,
                            "claim": "advertised floor area from the listing", "status": "ok",
                            "value": 54.2, "unit": "m2", "source": "pasted:listing",
                            "quote": "Advertised floor area: 62 square metres, including "
                                     "the balcony."})
        self.assertEqual(run(ev)["counts"]["contradictions"], 0)

    def test_a_listing_rating_against_the_register_rating(self):
        ev = self.base()
        ev["items"].append({"id": "e-rating-advert", "axis": 3,
                            "claim": "energy rating as advertised", "status": "ok",
                            "value": "A", "unit": "EPC letter", "source": "pasted:listing",
                            "quote": "Rent: £2,000 per calendar month."})
        self.assertIn("contradiction:energy_rating",
                      state(run(ev), "e-rating-advert")["rules"])

    def test_a_missing_fixed_form_id_for_the_tier(self):
        ev = self.base()
        clean = run(ev, tier="lite")
        self.assertEqual(clean["counts"]["fixed_form_missing"], [])
        wider = run(ev, tier="standard")
        self.assertEqual(wider["counts"]["fixed_form_missing"],
                         ["F9", "F10", "F11", "F12", "F13", "F14"])
        self.assertTrue(V.failed(wider))

    def test_an_unknown_nobody_tried_fails_only_under_strict(self):
        ev = self.base()
        item(ev, "e-reviews")["tried"] = []
        self.assertEqual(state(run(ev), "e-reviews")["state"], "unknown")
        strict = state(run(ev, strict=True), "e-reviews")
        self.assertEqual(strict["state"], "fail")
        self.assertIn("untried_unknown", strict["rules"])

    def test_every_failure_becomes_one_replan_ask_and_no_more(self):
        result = run(load("evidence-bad.json"), tier="standard",
                     report=load("report-stub.json"))
        self.assertTrue(result["replan"])
        self.assertTrue(all(entry["round"] == 1 for entry in result["replan"]),
                        "there is no second round")


class ThingsAModelWritingTheEvidenceGetsWrong(unittest.TestCase):
    """evidence.json is written by a model, so the schema violations to expect are
    missing ids, repeated ids, and a rent quoted per year."""

    def test_two_items_sharing_an_id_do_not_collapse_into_one_verdict(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        item(ev, "e-crime")["source"] = "made-up-register"
        item(ev, "e-crime")["id"] = "e-area"          # the same id as the good item
        result = run(ev)
        self.assertEqual(len(result["items"]), len(ev["items"]),
                         "one verdict per item, or a failure disappears")
        self.assertTrue(V.failed(result), "the unresolvable source must still fail")

    def test_an_item_with_no_id_gets_one(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        del item(ev, "e-area")["id"]
        result = run(ev)
        self.assertEqual(len(result["items"]), len(ev["items"]))
        self.assertTrue(all(v["id"] for v in result["items"]))

    def test_a_rent_quoted_per_year_does_not_flip_the_deposit_branch(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        ev["items"].insert(0, {"id": "e-rent-year", "axis": 8, "claim": "annual rent",
                               "status": "ok", "value": 24000, "unit": "GBP per year",
                               "source": "pasted:listing",
                               "quote": "Rent: £2,000 per calendar month."})
        item(ev, "e-f1")["claim"] = "F1 legal deposit cap for this tenancy"
        result = run(ev)
        self.assertEqual(result["counts"]["legal_caps"]["rent_pcm"], 2000.0,
                         "the monthly rent is the one the caps run on")
        self.assertEqual(state(result, "e-f1")["state"], "pass")

    def test_the_same_contradiction_is_said_once_however_many_pairs_produce_it(self):
        """One area item can be in three pairs at once, and two of those can render the
        identical sentence. Saying it twice in one line helps nobody - but two pairs that
        really are different still both get said."""
        result = run(load("evidence-bad.json"), tier="standard")
        reason = state(result, "b-referent")["reason"]
        self.assertEqual(reason.count("pasted:epc-cert says 54.0 and pasted:epc-cert "
                                      "says 910.0"), 1)
        self.assertIn("pasted:epc-cert says 910.0 and pasted:listing says 62.0", reason,
                      "a different pair is still worth saying")


class SourcesTheSkillItselfDocuments(unittest.TestCase):
    """The first pilot's executors cited `postcodes_io_lookup` - a real source, and the
    only name that register has. verify.py resolved it nowhere and returned `unknown` for
    every item, so nothing was ever checked and the report came out empty."""

    def test_a_sources_yaml_id_resolves(self):
        self.assertIn("postcodes_io_lookup", V.known_source_ids())
        ev = copy.deepcopy(load("evidence-good.json"))
        target = item(ev, "e-crime")
        target["source"] = "postcodes_io_lookup"
        verdict = state(run(ev), "e-crime")
        self.assertEqual(verdict["state"], "pass")
        self.assertNotIn("source_resolves", verdict["rules"])

    def test_an_id_in_no_register_at_all_still_fails(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        item(ev, "e-crime")["source"] = "made-up-register"
        self.assertIn("source_resolves", state(run(ev), "e-crime")["rules"])

    def test_a_quote_nobody_can_open_is_a_pass_that_is_counted_not_an_unknown(self):
        """A whole file of `unknown` is what emptied the first pilot's report. With no
        text held, the item is not failed and not blanked - it passes, and its id is in
        quotes_unchecked so the scorecard can say how much was never read."""
        ev = copy.deepcopy(load("evidence-good.json"))
        item(ev, "e-crime")["source"] = "postcodes_io_lookup"
        result = V.verify(ev, None, {}, "lite")
        states = set(v["state"] for v in result["items"])
        self.assertIn("pass", states, "not everything may come back unknown")
        self.assertIn("e-crime", result["counts"]["quotes_unchecked"])

    def test_a_calc_item_needs_no_source_and_no_quote(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        ev["items"].append({"id": "e-calc", "axis": 10, "claim": "all-in monthly cost",
                            "status": "ok", "value": 2575, "unit": "GBP per month",
                            "computed_by": "scripts/calc.py all-in --rent-pcm 2400 -> 2575"})
        self.assertEqual(state(run(ev), "e-calc")["state"], "pass")


class InformationSufficiency(unittest.TestCase):
    """Deterministic, no model, no tokens: was the fact even in the evidence?"""

    def test_a_fact_in_the_evidence_and_one_that_is_not(self):
        result = run(load("evidence-good.json"), gold=load("gold-tiny.json"))
        probes = dict((p["id"], p["present"]) for p in result["sufficiency"]["probes"])
        self.assertTrue(probes["g-area"], "54 m2 is in the evidence")
        self.assertTrue(probes["g-rating"], "the rating sentence is quoted")
        self.assertFalse(probes["g-heat"], "the executors never collected the heating")
        self.assertAlmostEqual(result["sufficiency"]["sufficiency"], 2 / 3.0, places=3)

    def test_collecting_the_missing_fact_moves_the_probe(self):
        ev = copy.deepcopy(load("evidence-good.json"))
        ev["items"].append({"id": "e-heat", "axis": 3, "claim": "main heating system",
                            "status": "ok", "value": "community heat network",
                            "source": "pasted:epc-cert",
                            "quote": "Main heating: community heat network."})
        result = run(ev, gold=load("gold-tiny.json"))
        self.assertEqual(result["sufficiency"]["sufficiency"], 1.0)

    def test_a_landmine_gold_file_is_read_too(self):
        gold = {"candidates": [{"id": "X1", "gold_landmines": [
            {"code": "L1", "confidence": "high", "name": "area overstated",
             "evidence": [{"rule": "area", "field": "epc", "text": "certificate 54 square"}]},
            {"code": "L2", "confidence": "high", "name": "nothing here",
             "evidence": [{"rule": "x", "field": "y", "text": "helipad 4318 metres"}]},
            {"code": "L9", "confidence": "low", "name": "ignored",
             "evidence": [{"rule": "x", "field": "y", "text": "whatever"}]}]}]}
        result = V.verify(load("evidence-good.json"), load("report-stub.json"),
                          V.load_sources(SOURCES), "lite", gold=gold, gold_id="X1")
        rows = dict((p["id"], p["present"]) for p in result["sufficiency"]["probes"])
        self.assertEqual(sorted(rows), ["L1", "L2"], "low-confidence codes are left out")
        self.assertTrue(rows["L1"])
        self.assertFalse(rows["L2"])


class DerivingEvidenceFromAFinishedReport(unittest.TestCase):
    """The P3 arm: verify a single agent's report without re-running it."""

    REPORT = {"candidates": [{
        "identity": {"flat": "301"},
        "metrics": {"crime_6mo_count": {"value": 199, "unit": "crimes",
                                        "sources": ["police-uk"], "meaning": "six months"}},
        "axes": [{"id": 2, "name": "floor area", "numbers": [
            {"label": "certified internal floor area", "value": 54.0, "unit": "m2",
             "sources": ["epc-cert"], "meaning": "the certificate's figure"}]}],
        "fixed_answers": [{"id": "F1", "status": "found", "answer": "5 weeks",
                           "source": "listing", "quote": "Deposit: five weeks' rent."},
                          {"id": "F2", "status": "unknown"}]}],
        "sources": [{"id": "police-uk", "url": "https://data.police.uk"},
                    {"id": "epc-cert", "url": "https://find-energy-certificate.service.gov.uk"},
                    {"id": "listing", "url": "a page the user pasted"}]}

    def test_every_number_and_answer_becomes_an_item(self):
        evidence = V.evidence_from_report(self.REPORT, "x-demo")
        ids = [i["id"] for i in evidence["items"]]
        self.assertEqual(ids, ["m-crime_6mo_count", "a2-1", "f-F1", "f-F2"])
        self.assertEqual(evidence["flat"], "301")
        self.assertEqual(evidence["schema"], V.EVIDENCE_SCHEMA)

    def test_a_number_with_no_quote_comes_back_unverified_not_verified(self):
        evidence = V.evidence_from_report(self.REPORT, "x-demo")
        result = V.verify(evidence, self.REPORT, V.load_sources(SOURCES), "lite")
        verdict = state(result, "a2-1")
        self.assertEqual(verdict["state"], "fail")
        self.assertIn("quote_missing", verdict["rules"],
                      "an unverified number is not a verified one")


class TheSharedReferentRules(unittest.TestCase):
    """The skill's verifier and the benchmark's grader must not drift apart."""

    def test_the_word_lists_are_one_object(self):
        import grade
        for name in ("HISTORICAL_WORDS", "CURRENT_WORDS", "FALLBACK_WORDS",
                     "PRIMARY_JOURNEY_WORDS", "MONEY_WORDS", "CERTIFICATE_WORDS",
                     "COMPANY_WORDS", "BUILDING_AGE_WORDS", "BUILDING_WORDS", "FLAT_WORDS"):
            self.assertIs(getattr(grade, name), getattr(referents, name), name)
        self.assertIs(grade.FLAT_ID, referents.FLAT_ID)

    def test_a_register_row_that_lists_the_neighbours_does_not_condemn_this_flat(self):
        """An energy-register search prints every flat at the postcode. Taking the first
        one it names would fail a correct number for flat 301 because 201 is above it."""
        text = "flat 201 48 m2, flat 301 54 m2, flat 401 61 m2"
        self.assertEqual(referents.problems("certified floor area", text, flat="301"), [])
        wrong = referents.problems("certified floor area", text, flat="507")
        self.assertEqual([p["rule"] for p in wrong], ["another_flat"])

    def test_they_agree_on_shared_fixtures(self):
        import grade
        cases = [
            ("epc.floor_area_m2", "certified internal floor area",
             {"label": "communal floor area of the block", "unit": "m2", "value": 910}, True),
            ("epc.floor_area_m2", "certified internal floor area",
             {"label": "floor area of this flat", "unit": "m2", "value": 54}, False),
            ("epc.energy_rating", "energy rating",
             {"label": "the previous certificate's energy rating", "value": "D"}, True),
            ("epc.energy_rating", "energy rating",
             {"label": "current energy rating", "value": "B"}, False),
            ("epc.first_assessment_year", "first assessment year",
             {"label": "sale price paid", "unit": "GBP", "value": 615000}, True),
            ("epc.first_assessment_year", "first assessment year",
             {"label": "the price register's year", "unit": "GBP", "value": 2015}, False),
            ("epc.first_assessment_year", "first assessment year",
             {"label": "the managing agent's company registration", "value": 8854998}, True),
            ("commute.all_min", "door to door commute",
             {"label": "journey time if the Jubilee line is shut", "value": 55}, True),
            ("commute.all_min", "door to door commute",
             {"label": "door to door journey time", "value": 27}, False),
            # The cancel matters as much as the rule: a label that names the very
            # journey the question asks for is kept even though it also says "if".
            ("commute.all_min", "door to door commute",
             {"label": "door to door, even if the Jubilee line is shut", "value": 31},
             False),
        ]
        guard = grade.ReferentGuard({"generated_at": "2026-09-06T00:00:00Z"}, {})
        for fact, claim, number, expect in cases:
            grader_says = guard.check(fact, {"name": ""}, number, "test") is not None
            skill_says = bool(referents.problems(claim, "%s %s" % (number.get("label"),
                                                                  number.get("unit") or ""),
                                                 value=number.get("value")))
            self.assertEqual(grader_says, expect,
                             "bench/grade.py disagrees on %r" % number["label"])
            self.assertEqual(skill_says, expect,
                             "scripts/verify.py disagrees on %r" % number["label"])


class TheCommandLine(unittest.TestCase):
    def run_it(self, *args):
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "verify.py")] + list(args),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        return proc.returncode, out.decode("utf-8"), err.decode("utf-8")

    def test_clean_evidence_exits_zero_and_dirty_evidence_exits_one(self):
        code, out, _err = self.run_it(os.path.join(FIX, "evidence-good.json"),
                                      "--sources", SOURCES, "--tier", "lite", "--table")
        self.assertEqual(code, 0, out)
        code, out, _err = self.run_it(os.path.join(FIX, "evidence-bad.json"),
                                      "--sources", SOURCES,
                                      "--report", os.path.join(FIX, "report-stub.json"),
                                      "--tier", "standard", "--table")
        self.assertEqual(code, 1)
        self.assertIn("fixed form (standard tier) still owes", out)

    def test_the_table_names_the_rule_and_the_working(self):
        _code, out, _err = self.run_it(os.path.join(FIX, "evidence-bad.json"),
                                       "--sources", SOURCES,
                                       "--report", os.path.join(FIX, "report-stub.json"),
                                       "--tier", "standard", "--table")
        self.assertIn("legal caps from rent", out)
        self.assertIn("the cap here is 6 weeks", out)

    def test_from_report_prints_evidence(self):
        code, out, _err = self.run_it("--from-report", os.path.join(FIX, "report-stub.json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["schema"], V.EVIDENCE_SCHEMA)

    def test_no_arguments_is_a_usage_error(self):
        code, _out, err = self.run_it()
        self.assertEqual(code, 2)
        self.assertIn("usage error", err)


if __name__ == "__main__":
    unittest.main()
