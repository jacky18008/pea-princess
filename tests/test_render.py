# -*- coding: utf-8 -*-
"""Offline tests for the report layer: schema checker, render.py, viewer.html.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import copy
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
REFS = os.path.join(ROOT, "skills", "vet-flat", "references")
VIEWER_DIR = os.path.join(ROOT, "viewer")

sys.path.insert(0, SCRIPTS)
sys.path.insert(0, VIEWER_DIR)
import render  # noqa: E402
import build_viewer  # noqa: E402

SAMPLE = os.path.join(HERE, "fixtures", "report-sample.json")
SCHEMA = os.path.join(REFS, "report-schema.json")
GLOSSARY = os.path.join(REFS, "glossary.yaml")
VIEWER = os.path.join(VIEWER_DIR, "viewer.html")
PROFILE = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")

FOOTER = "Generated with vet-flat 1.0.0-draft \u2014 https://github.com/jacky18008/pea-princess"

SECTION_TITLES_EN = [
    "Verdict",
    "Your must-haves versus this flat",
    "Side by side",
    "Worst resident reviews",
    "Landmines",
    "The 12 checks in detail",
    "Questions to ask, and what to check on the day",
    "What we could not find",
    "Sources and when they were read",
    "About this report",
]


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def load_sample():
    return json.loads(read(SAMPLE))


def load_schema():
    return json.loads(read(SCHEMA))


def broken_sample():
    """The sample, with a deposit above the five-week cap and a wrong price per square foot.

    Rent is 2,150 a month, so a week is 496.15 and the cap is 5 x 496.15 = 2,480.77;
    the deposit below asks 3,200. The energy certificate area is 571 square feet, so
    the rent per square foot is 2,150 / 571 = 3.77, not the 2.90 written here.
    """
    bad = load_sample()
    cand = bad["candidates"][0]
    for axis in cand["axes"]:
        if axis["id"] == 7:
            axis.setdefault("numbers", []).append({
                "label": "Deposit asked", "value": 3200, "unit": "GBP",
                "meaning": "This is what the agent wants to hold for the tenancy.",
                "compared_to": "The legal maximum is five weeks' rent."})
        for number in axis.get("numbers") or []:
            if number.get("label") == "Rent per square foot":
                number["value"] = 2.9
    cand["metrics"]["price_per_sqft_epc"]["value"] = 2.9
    return bad


def unsourced_sample():
    """The sample, with one axis number and one metric that name no source and no formula.

    Everything else in the fixture cites a source id, so exactly two numbers are
    expected to warn: the invented service charge and the stripped metric.
    """
    bad = load_sample()
    cand = bad["candidates"][0]
    for axis in cand["axes"]:
        if axis["id"] == 6:
            axis.setdefault("numbers", []).append({
                "label": "Rumoured service charge", "value": 210, "unit": "GBP per month",
                "meaning": "Someone wrote this in a forum thread.",
                "compared_to": "No local benchmark found."})
    cand["metrics"]["nearest_works_m"].pop("sources", None)
    cand["metrics"]["nearest_works_m"].pop("computed_by", None)
    return bad


def write_temp(report):
    import tempfile
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False))
    return path


def run_cli(*args):
    proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "render.py")] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8"), err.decode("utf-8")


# ------------------------------------------------------------------ glossary
class TestGlossary(unittest.TestCase):
    def setUp(self):
        self.terms = render.load_glossary(GLOSSARY)

    def test_every_label_the_renderer_needs_exists(self):
        needed = ["section." + s for s in ("verdict", "hard_filters", "comparison", "worst_reviews",
                                           "landmines", "axes", "questions", "gaps", "sources", "about")]
        needed += ["verdict." + s for s in ("PASS", "EDGE", "CONDITIONAL", "KILL")]
        needed += ["evidence." + s for s in "GSCIU"]
        needed += ["axis.%d" % i for i in range(1, 13)]
        needed += ["landmine.L%d" % i for i in range(1, 13)]
        needed += [tid for _, tid in render.METRIC_KEYS]
        needed += [tid for _, tid in render.COST_KEYS]
        needed += ["ui.report_title", "ui.requirement", "ui.observed", "ui.result", "ui.pass",
                   "ui.fail", "ui.unknown", "ui.evidence", "ui.nothing_listed", "ui.no_data",
                   "ui.configuration", "ui.tier_default", "ui.not_stated", "ui.no_source"]
        missing = [t for t in needed if t not in self.terms]
        self.assertEqual([], missing, "glossary.yaml is missing: %s" % missing)

    def test_every_term_has_english_and_a_plain_gloss(self):
        for key, entry in self.terms.items():
            self.assertTrue(entry.get("en"), "%s has no en label" % key)
            self.assertTrue(entry.get("plain"), "%s has no plain gloss" % key)

    def test_three_languages_for_layout_terms(self):
        for key, entry in build_viewer.layout_terms(self.terms).items():
            for lang in ("zh-TW", "zh-CN"):
                self.assertTrue(entry.get(lang), "%s has no %s label" % (key, lang))

    def test_language_fallback_chain(self):
        labels = render.Labels(self.terms, "zh-HK")
        self.assertEqual("\u5224\u6c7a", labels.label("section.verdict"))  # falls back to zh-TW
        self.assertEqual("Verdict", render.Labels(self.terms, "fr").label("section.verdict"))

    def test_parser_rejects_unquoted_values(self):
        with self.assertRaises(render.GlossaryError):
            render.parse_mini_yaml("terms:\n  a:\n    en: bare\n")


# ----------------------------------------------------------------- validator
class TestSchemaChecker(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()
        self.data = load_sample()

    def test_sample_is_accepted(self):
        errors, warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_broken_copy_is_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["candidates"][0]["axes"].append({"id": 13, "name": "Thirteenth", "finding": "x",
                                             "evidence_class": "G"})
        bad["candidates"][0]["killer_questions"] = ["one?", "two?", "three?"]
        bad["candidates"][1]["verdict"]["status"] = "MAYBE"
        errors, _ = render.validate(bad, self.schema)
        joined = "\n".join(errors)
        self.assertIn("axes", joined)
        self.assertIn("12", joined)
        self.assertIn("killer_questions", joined)
        self.assertIn("at most 2", joined)
        self.assertIn("PASS", joined)  # the status enum is quoted back to the model
        self.assertIn("MAYBE", joined)

    def test_thirteen_axes_alone_is_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["candidates"][0]["axes"].append(dict(bad["candidates"][0]["axes"][0]))
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("axes" in e for e in errors), errors)

    def test_three_killer_questions_alone_is_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["candidates"][1]["killer_questions"] = ["a?", "b?", "c?"]
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("killer_questions" in e for e in errors), errors)

    def test_over_long_headline_is_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["candidates"][0]["verdict"]["headline"] = "x" * 141
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("headline" in e and "140" in e for e in errors), errors)

    def test_status_dependent_fields_are_required(self):
        bad = copy.deepcopy(self.data)
        bad["candidates"][0]["verdict"] = {"status": "KILL", "headline": "No.", "reason_codes": []}
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("fatal_axis" in e for e in errors), errors)

        bad = copy.deepcopy(self.data)
        bad["candidates"][1]["verdict"]["break_even_rent_pcm"] = None
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("break_even_rent_pcm" in e for e in errors), errors)

    def test_comparison_is_required_for_two_candidates(self):
        bad = copy.deepcopy(self.data)
        del bad["comparison"]
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("comparison" in e for e in errors), errors)

    def test_single_building_finding_may_not_claim_to_generalise(self):
        bad = copy.deepcopy(self.data)
        bad["comparison"]["single_building_findings"][0]["generalisable"] = True
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("generalisable" in e for e in errors), errors)

    def test_unknown_source_id_is_a_warning_not_an_error(self):
        soft = copy.deepcopy(self.data)
        soft["candidates"][0]["axes"][0]["sources"] = ["s-does-not-exist"]
        errors, warnings = render.validate(soft, self.schema)
        self.assertEqual([], errors)
        self.assertTrue(any("s-does-not-exist" in w for w in warnings), warnings)


# ---------------------------------------------------------------------- HTML
class TestHtmlOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code, cls.html, cls.err = run_cli(SAMPLE)
        cls.code = code

    def test_exit_code_and_document(self):
        self.assertEqual(0, self.code, self.err)
        self.assertTrue(self.html.startswith("<!doctype html>"))
        self.assertIn("</html>", self.html)

    def test_all_ten_section_headings(self):
        for i, title in enumerate(SECTION_TITLES_EN, 1):
            self.assertIn(">%d. %s</h2>" % (i, title), self.html,
                          "section %d (%s) is missing from the HTML" % (i, title))

    def test_footer(self):
        self.assertIn(FOOTER, self.html)

    def test_self_contained(self):
        for forbidden in ("<script src=", "<link ", "@import", "<iframe"):
            self.assertNotIn(forbidden, self.html)

    def test_theme_aware(self):
        self.assertIn("@media (prefers-color-scheme: dark)", self.html)
        self.assertIn(':root:not([data-theme="light"])', self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)

    def test_tables_scroll_and_page_prints(self):
        self.assertIn("overflow-x:auto", self.html)
        self.assertIn("@media print", self.html)
        self.assertIn('<div class="tw"><table>', self.html)

    def test_evidence_shown_as_plain_labels(self):
        self.assertIn("Official record", self.html)
        self.assertIn("Self-reported", self.html)
        self.assertNotIn(">G</span>", self.html)

    def test_numbers_carry_meaning_and_comparison(self):
        self.assertIn('class="meaning" title="', self.html)
        self.assertIn("The local band is 3.80 to 4.40.", self.html)

    def test_language_switch(self):
        code, zh, err = run_cli(SAMPLE, "--lang", "zh-TW")
        self.assertEqual(0, code, err)
        self.assertIn("1. \u5224\u6c7a</h2>", zh)
        self.assertIn("\u96f7\u9ede", zh)
        self.assertIn(FOOTER, zh)

    def test_broken_report_fails_with_a_readable_message(self):
        import tempfile
        bad = load_sample()
        bad["candidates"][0]["verdict"]["status"] = "MAYBE"
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        try:
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(bad, ensure_ascii=False))
            code, out, err = run_cli(path)
            self.assertEqual(1, code)
            self.assertEqual("", out)
            self.assertIn("does not match report-schema.json", err)
            self.assertIn("MAYBE", err)
        finally:
            os.unlink(path)


# ------------------------------------------------------------------ Markdown
class TestMarkdownOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.md, cls.err = run_cli(SAMPLE, "--md")

    def test_exit_code(self):
        self.assertEqual(0, self.code, self.err)

    def test_same_ten_sections_in_the_same_order(self):
        found = [line for line in self.md.splitlines() if line.startswith("## ")]
        self.assertEqual(["## %d. %s" % (i, t) for i, t in enumerate(SECTION_TITLES_EN, 1)], found)

    def test_footer(self):
        self.assertIn(FOOTER, self.md)

    def test_carries_the_content(self):
        self.assertIn("Flat 12, Harrowfield Court", self.md)
        self.assertIn("| Rank |", self.md)


# -------------------------------------------------------------------- viewer
class TestViewer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read(VIEWER)

    def test_size_budget(self):
        size = len(self.html.encode("utf-8"))
        self.assertLess(size, 125 * 1024, "viewer.html is %.1f KB, the budget is 125 KB" % (size / 1024.0))

    def test_contains_the_generated_glossary(self):
        self.assertIn("var GLOSSARY = {", self.html)
        start = self.html.index("/*BEGIN:GLOSSARY*/")
        end = self.html.index("/*END:GLOSSARY*/")
        block = self.html[start:end]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        terms = build_viewer.layout_terms(render.load_glossary(GLOSSARY))
        self.assertEqual(terms, payload)
        for key in ("section.verdict", "axis.1", "landmine.L12", "evidence.G", "verdict.KILL"):
            self.assertIn(key, payload)

    def test_contains_the_generated_sample(self):
        self.assertIn("var SAMPLE = {", self.html)
        start = self.html.index("/*BEGIN:SAMPLE*/")
        end = self.html.index("/*END:SAMPLE*/")
        block = self.html[start:end]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        self.assertEqual(load_sample(), payload)

    def test_footer_string(self):
        self.assertIn("Generated with vet-flat {version} \u2014 {url}", self.html)
        self.assertIn("https://github.com/jacky18008/pea-princess", self.html)

    def test_same_sections_in_the_same_order(self):
        for term_id, anchor in render.SECTIONS:
            self.assertIn('["%s","%s"]' % (term_id, anchor), self.html.replace(", ", ","))

    def test_self_contained(self):
        body = self.html.split("/*BEGIN:SAMPLE*/")[0] + self.html.split("/*END:SAMPLE*/")[1]
        for forbidden in ("<script src=", "<link ", "@import", "<iframe", "fetch(", "XMLHttpRequest"):
            self.assertNotIn(forbidden, body)

    def test_theme_aware(self):
        self.assertIn("@media (prefers-color-scheme: dark)", self.html)
        self.assertIn(':root:not([data-theme="light"])', self.html)
        self.assertIn(':root[data-theme="dark"]', self.html)

    def test_offers_copy_when_downloads_are_blocked(self):
        self.assertIn("Copy HTML", self.html)
        self.assertIn("Download HTML", self.html)

    def test_carries_the_same_recompute_and_block(self):
        for needle in ("function recompute(", "function recomputeCandidate(", "function arithBlock(",
                       "function badLocations(", "ui.arithmetic_check", "ui.check_the_maths",
                       "weekly rent = monthly rent \u00d7 12 \u00f7 52",
                       "all-in = rent + bills + council tax + broadband",
                       "\u00a3 per square foot = rent \u00f7 (floor area in m\u00b2 \u00d7 10.7639)",
                       "break-even rent = your all-in ceiling \u2212 bills \u2212 council tax",
                       "bridge total = weeks \u00d7 weekly rate + months \u00d7 all-in",
                       "WEEKS_PER_YEAR=52.0", "SQFT_PER_M2=10.7639", "SIX_WEEK_ANNUAL_RENT=50000.0",
                       "TOL_PCT=0.01", "TOL_FLOOR_PCM=1.0", "TOL_FLOOR_RATE=0.01",
                       "chip maths"):
            self.assertIn(needle, self.html, "viewer.html is missing %r" % needle)

    def test_build_step_is_up_to_date(self):
        self.assertEqual(0, build_viewer.main(["--check"]),
                         "viewer.html is out of date: run python3 viewer/build_viewer.py")


# ---------------------------------------------------------- arithmetic check
class TestArithmeticCheck(unittest.TestCase):
    """render.py recomputes every derivable number and compares it with the model's."""

    def test_the_sample_is_arithmetically_consistent(self):
        data = load_sample()
        entries = render.recompute(data)
        self.assertEqual(2, len(entries))
        for entry in entries:
            bad = [c for c in entry["checks"] if not c["ok"]]
            self.assertEqual([], bad, "%s: %s" % (entry["candidate_id"], bad))
            self.assertTrue(entry["arithmetic_ok"])
        for cand in data["candidates"]:
            self.assertTrue(cand["arithmetic_check"]["arithmetic_ok"])

    def test_every_check_carries_the_five_fields(self):
        for entry in render.recompute(load_sample()):
            for check in entry["checks"]:
                for key in ("field", "model_value", "recomputed", "delta", "ok"):
                    self.assertIn(key, check)

    def test_the_fields_it_recomputes(self):
        fields = [c["field"] for c in render.recompute(load_sample())[0]["checks"]]
        for expected in ("weekly_rent", "deposit_cap", "holding_deposit_cap", "all_in_low",
                         "all_in_planning", "all_in_stress", "price_per_sqft", "break_even_rent"):
            self.assertIn(expected, fields)

    def test_the_formulas_are_the_ones_in_calc_py(self):
        import calc
        self.assertEqual(calc.WEEKS_PER_YEAR, render.WEEKS_PER_YEAR)
        self.assertEqual(calc.SQFT_PER_M2, render.SQFT_PER_M2)
        rent, area_m2 = 2400.0, 52.0
        self.assertAlmostEqual(calc.weekly_rent(rent), rent * 12.0 / render.WEEKS_PER_YEAR, 6)
        self.assertAlmostEqual(rent / (area_m2 * render.SQFT_PER_M2),
                               rent / (area_m2 * calc.SQFT_PER_M2), 9)
        self.assertIn("12", render.FORMULAS["weekly_rent"])
        self.assertIn("52", render.FORMULAS["weekly_rent"])
        self.assertIn("10.7639", render.FORMULAS["price_per_sqft"])

    def test_the_schema_accepts_what_the_renderer_writes(self):
        data = load_sample()
        render.recompute(data)
        errors, warnings = render.validate(data, load_schema())
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_computed_by_is_allowed_on_numbers_and_metrics(self):
        data = load_sample()
        data["candidates"][0]["axes"][0].setdefault("numbers", []).append(
            {"label": "Made up", "value": 1, "unit": "GBP per month", "meaning": "x",
             "compared_to": "y", "computed_by": "scripts/calc.py all-in"})
        data["candidates"][0]["metrics"]["commute_min"]["computed_by"] = "shown formula"
        errors, _ = render.validate(data, load_schema())
        self.assertEqual([], errors)

    def test_a_deposit_over_the_cap_and_a_wrong_rate_are_caught(self):
        entry = render.recompute(broken_sample())[0]
        self.assertFalse(entry["arithmetic_ok"])
        failed = dict((c["field"], c) for c in entry["checks"] if not c["ok"])
        self.assertIn("deposit_cap", failed)
        self.assertEqual("cap", failed["deposit_cap"]["kind"])
        self.assertEqual(3200, failed["deposit_cap"]["model_value"])
        self.assertAlmostEqual(2480.77, failed["deposit_cap"]["recomputed"], 2)
        self.assertIn("price_per_sqft", failed)
        self.assertAlmostEqual(3.77, failed["price_per_sqft"]["recomputed"], 2)

    def test_a_penny_off_still_passes(self):
        data = load_sample()
        data["candidates"][0]["costs"]["all_in_planning"] = 2528.4
        self.assertTrue(render.recompute(data)[0]["arithmetic_ok"])

    def test_warnings_name_the_number_and_the_formula(self):
        lines = render.arithmetic_warnings(broken_sample())
        joined = "\n".join(lines)
        self.assertIn("Deposit asked", joined)
        self.assertIn("above the legal cap", joined)
        self.assertIn("does not match", joined)
        self.assertIn("model said", joined)
        self.assertIn("formula gives", joined)
        self.assertIn("rent + bills + council tax + broadband", "\n".join(
            c["formula"] for e in render.recompute(load_sample()) for c in e["checks"]))


class TestArithmeticCheckOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = write_temp(broken_sample())
        cls.html_code, cls.html, cls.html_err = run_cli(cls.path)
        cls.md_code, cls.md, cls.md_err = run_cli(cls.path, "--md")
        cls.strict = run_cli(cls.path, "--strict", "--validate-only")
        cls.clean = run_cli(SAMPLE, "--validate-only")
        cls.clean_strict = run_cli(SAMPLE, "--strict", "--validate-only")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)

    def test_html_has_the_block_the_formulas_and_a_chip(self):
        self.assertEqual(0, self.html_code, self.html_err)
        self.assertIn("Arithmetic check", self.html)
        self.assertIn("weekly rent = monthly rent \u00d7 12 \u00f7 52", self.html)
        self.assertIn("all-in = rent + bills + council tax + broadband", self.html)
        self.assertIn("does not match: model said", self.html)
        self.assertIn("matches (model said", self.html)
        self.assertIn("is above the legal cap: model said", self.html)
        self.assertIn('class="chip maths"', self.html)
        self.assertIn("check the maths", self.html)

    def test_markdown_has_the_block_and_the_flag(self):
        self.assertEqual(0, self.md_code, self.md_err)
        self.assertIn("**Arithmetic check**", self.md)
        self.assertIn("| Numbers | Formula | Result |", self.md)
        self.assertIn("does not match: model said", self.md)
        self.assertIn("is above the legal cap: model said", self.md)
        self.assertIn("**[check the maths]**", self.md)

    def test_a_warning_per_mismatch_on_stderr(self):
        self.assertIn("WARNING  arithmetic:", self.html_err)
        self.assertIn("WARNING  arithmetic:", self.strict[2])
        # the deposit cap, and the wrong rate in both the metric and the axis number
        self.assertEqual(3, self.html_err.count("WARNING  arithmetic:"), self.html_err)

    def test_strict_turns_a_mismatch_into_an_error(self):
        self.assertEqual(1, self.strict[0], self.strict[2])
        self.assertIn("treated as errors", self.strict[2])
        self.assertIn("arithmetic", self.strict[2])

    def test_the_clean_sample_passes_validate_only_and_strict(self):
        self.assertEqual(0, self.clean[0], self.clean[2])
        self.assertNotIn("WARNING  arithmetic:", self.clean[2])
        self.assertIn("recomputed and matches", self.clean[2])
        self.assertEqual(0, self.clean_strict[0], self.clean_strict[2])

    def test_the_clean_sample_renders_the_block_with_no_chip(self):
        code, html, err = run_cli(SAMPLE)
        self.assertEqual(0, code, err)
        self.assertIn("Arithmetic check", html)
        self.assertNotIn('class="chip maths"', html)
        self.assertIn("not stated in the report; formula gives", html)


# ------------------------------------------------- no source, no number
class TestUnsourcedNumbers(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_the_rule_is_in_the_schema_as_an_anyof_on_both_number_definitions(self):
        for name in ("labelled_number", "measure"):
            branches = self.schema["definitions"][name].get("anyOf")
            self.assertTrue(branches, "%s has no anyOf" % name)
            required = sorted(sum([b.get("required", []) for b in branches], []))
            self.assertEqual(["computed_by", "sources"], required)
            self.assertEqual(["sources", "computed_by"],
                             render.source_alternatives(self.schema, name))

    def test_the_required_list_did_not_change_so_older_reports_still_validate(self):
        for name in ("labelled_number", "measure"):
            self.assertNotIn("sources", self.schema["definitions"][name]["required"])
            self.assertNotIn("computed_by", self.schema["definitions"][name]["required"])
        old = load_sample()
        old["schema_version"] = "1.0"
        old["generated_by"].pop("tier", None)
        old["generated_by"].pop("escalation_reason", None)
        errors, warnings = render.validate(old, self.schema)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_the_sample_sources_every_number_it_states(self):
        self.assertEqual([], render.unsourced_numbers(load_sample(), self.schema))

    def test_a_number_with_a_source_or_a_formula_passes(self):
        data = load_sample()
        axis = [a for a in data["candidates"][0]["axes"] if a["id"] == 6][0]
        axis.setdefault("numbers", []).append(
            {"label": "Worked out", "value": 12, "unit": "GBP per month", "meaning": "x",
             "compared_to": "y", "computed_by": "shown formula"})
        self.assertEqual([], render.unsourced_numbers(data, self.schema))

    def test_an_empty_sources_list_is_not_a_source(self):
        data = load_sample()
        data["candidates"][0]["metrics"]["commute_min"]["sources"] = []
        gaps = render.unsourced_numbers(data, self.schema)
        self.assertEqual([("metrics", "commute_min")], [g["loc"] for g in gaps])

    def test_a_null_value_is_not_flagged_because_there_is_no_number_in_it(self):
        data = load_sample()
        metric = data["candidates"][0]["metrics"]["commute_min"]
        metric["sources"] = []
        metric["value"] = None
        self.assertEqual([], render.unsourced_numbers(data, self.schema))

    def test_it_finds_both_the_axis_number_and_the_metric(self):
        gaps = render.unsourced_numbers(unsourced_sample(), self.schema)
        self.assertEqual(2, len(gaps), gaps)
        self.assertEqual([("axis", 6, 2), ("metrics", "nearest_works_m")],
                         [g["loc"] for g in gaps])
        joined = "\n".join(g["message"] for g in gaps)
        self.assertIn("Rumoured service charge", joined)
        self.assertIn("nearest_works_m", joined)
        self.assertIn("computed_by", joined)


class TestUnsourcedOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = write_temp(unsourced_sample())
        cls.code, cls.html, cls.err = run_cli(cls.path)
        cls.md_code, cls.md, cls.md_err = run_cli(cls.path, "--md")
        cls.strict = run_cli(cls.path, "--strict", "--validate-only")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)

    def test_a_warning_per_number_by_default_and_the_page_is_still_written(self):
        self.assertEqual(0, self.code, self.err)
        self.assertEqual(2, self.err.count("WARNING  no source:"), self.err)
        self.assertIn("Rumoured service charge", self.err)
        self.assertIn("metrics.nearest_works_m", self.err)
        self.assertIn("</html>", self.html)

    def test_strict_makes_each_one_an_error(self):
        code, out, err = self.strict
        self.assertEqual(1, code, err)
        self.assertIn("WARNING  no source:", err)
        self.assertIn("2 number(s) with no source", err)
        self.assertEqual("", out)

    def test_the_html_marks_the_number_with_a_visible_chip(self):
        self.assertEqual(2, self.html.count('class="chip nosource"'), self.html.count("nosource"))
        self.assertIn(">no source<", self.html)
        self.assertIn(".chip.nosource{", self.html)

    def test_the_markdown_marks_the_number_too(self):
        self.assertEqual(0, self.md_code, self.md_err)
        self.assertEqual(2, self.md.count("**[no source]**"), self.md)

    def test_the_clean_sample_is_marked_nowhere(self):
        code, html, err = run_cli(SAMPLE)
        self.assertEqual(0, code, err)
        self.assertNotIn('class="chip nosource"', html)
        self.assertNotIn("WARNING  no source:", err)

    def test_the_viewer_runs_the_same_check_and_draws_the_same_chip(self):
        viewer = read(VIEWER)
        for needle in ('var SOURCE_KEYS = ["sources","computed_by"]', "function noSrc(",
                       "function unsourcedNumbers(", "function chipNoSource(",
                       'chip("nosource"', ".chip.nosource{", "ui.no_source"):
            self.assertIn(needle, viewer, needle)


# ------------------------------------------------------- the escalation ladder
class TestEscalationLadder(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_the_schema_carries_the_two_optional_fields(self):
        gb = self.schema["definitions"]["generated_by"]
        self.assertEqual(["lite", "standard", "breadth", "manual"],
                         gb["properties"]["tier"]["enum"])
        self.assertEqual(200, gb["properties"]["escalation_reason"]["maxLength"])
        for key in ("tier", "escalation_reason"):
            self.assertNotIn(key, gb["required"], "%s must stay optional" % key)

    def test_an_unknown_tier_is_rejected(self):
        bad = load_sample()
        bad["generated_by"]["tier"] = "deep"
        errors, _ = render.validate(bad, self.schema)
        self.assertTrue(any("tier" in e and "breadth" in e for e in errors), errors)

    def test_the_line_names_the_tier_the_reason_the_workers_and_the_judge(self):
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        data = load_sample()
        self.assertEqual("Configuration: breadth \u2014 final shortlist of two; "
                         "workers: cheap; judge: example-model-1 (fixture, not a real run)",
                         render.configuration_line(data, L))

    def test_no_escalation_reads_default(self):
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        data = load_sample()
        data["generated_by"]["tier"] = "standard"
        data["generated_by"].pop("escalation_reason")
        self.assertIn("Configuration: standard \u2014 default; workers: cheap;",
                      render.configuration_line(data, L))

    def test_a_missing_tier_reads_not_stated(self):
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        data = load_sample()
        data["generated_by"].pop("tier")
        data["generated_by"].pop("escalation_reason")
        self.assertEqual("Configuration: not stated \u2014 not stated; workers: not stated; "
                         "judge: example-model-1 (fixture, not a real run)",
                         render.configuration_line(data, L))

    def test_a_manual_run_says_it_had_no_workers(self):
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        data = load_sample()
        data["generated_by"]["tier"] = "manual"
        self.assertIn("workers: none;", render.configuration_line(data, L))

    def test_the_html_prints_it_first_under_the_title_and_again_in_about(self):
        code, html, err = run_cli(SAMPLE)
        self.assertEqual(0, code, err)
        line = "Configuration: breadth \u2014 final shortlist of two; workers: cheap; judge:"
        self.assertEqual(2, html.count(line), html.count("Configuration:"))
        title = html.index("</h1>")
        self.assertLess(html.index(line), html.index("&middot;", title))
        self.assertLess(html.index("10. About this report"), html.rindex(line))

    def test_the_markdown_prints_it_in_both_places(self):
        code, md, err = run_cli(SAMPLE, "--md")
        self.assertEqual(0, code, err)
        lines = md.splitlines()
        self.assertTrue(lines[0].startswith("# "), lines[0])
        self.assertTrue(lines[2].startswith("Configuration: breadth \u2014 "), lines[:4])
        self.assertEqual(2, md.count("Configuration: breadth \u2014 "), md.count("Configuration"))
        after = md[md.index("## 10. About this report"):]
        self.assertIn("Configuration: breadth \u2014 ", after)

    def test_the_viewer_prints_the_same_line(self):
        viewer = read(VIEWER)
        for needle in ("function configLine(", "function configP(", "TIER_WORKERS",
                       "ui.configuration", "ui.not_stated", "ui.tier_default", "{judge}"):
            self.assertIn(needle, viewer, needle)

    def test_the_ladder_is_documented_where_the_skill_points(self):
        modes = read(os.path.join(REFS, "budget-modes.md"))
        self.assertIn("## The escalation ladder (automatic)", modes)
        for needle in ("`standard`", "`breadth`", "`manual`", "`lite`",
                       "generated_by.tier", "escalation_reason",
                       "final shortlist of two or three", "40 %",
                       "Never start at breadth", "four or more subagents"):
            self.assertIn(needle, modes, needle)


# ------------------------------------------------------------------- profile
class TestProfileTemplate(unittest.TestCase):
    def test_every_documented_filter_is_present(self):
        text = read(PROFILE)
        for key in ("min_floor_area_sqft", "max_building_age_years", "rent_pcm_target",
                    "all_in_pcm_ceiling", "stretch_ceiling_and_conditions", "move_in_window",
                    "earliest", "latest", "tolerance_days", "commute", "destination", "arrive_by",
                    "max_door_to_door_min", "redundancy_min_grade", "reject_ground_floor",
                    "prefer_floor_band", "reject_no_sky", "aspect_scores", "quiet_over_light",
                    "must_haves", "nice_to_haves", "guarantor_route", "max_months_upfront",
                    "self_intro_template", "language"):
            self.assertIn(key, text, "profile.template.yaml has no %s" % key)

    def test_personal_values_are_left_blank(self):
        text = read(PROFILE)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("min_floor_area_sqft") or stripped.startswith("destination"):
                self.assertTrue(stripped.endswith(":"), "%r should be blank in the template" % line)


if __name__ == "__main__":
    unittest.main()
