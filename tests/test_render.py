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
import scan  # noqa: E402
import build_viewer  # noqa: E402

SAMPLE = os.path.join(HERE, "fixtures", "report-sample.json")
SCHEMA = os.path.join(REFS, "report-schema.json")
GLOSSARY = os.path.join(REFS, "glossary.yaml")
FIXED_QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")
VIEWER = os.path.join(VIEWER_DIR, "viewer.html")
PROFILE = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")

FOOTER = "Generated with vet-flat 1.0.0-draft \u2014 https://github.com/jacky18008/pea-princess"

SECTION_TITLES_EN = [
    "Verdict",
    "Your must-haves versus this flat",
    "The questions we always answer",
    "Side by side",
    "Worst resident reviews",
    "Landmines",
    "The 12 checks in detail",
    "Questions to ask, and what to check on the day",
    "What only you can tell",
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


# The five stages of the user's own questions, as the example report answers them.
Q_FILTER = "Is the bedroom on the quiet side, away from a main road or a railway?"
Q_VET = "What does this flat cost me every month, once the heating is paid for?"
Q_COMPARE = "If this flat is unusually cheap, unusually good or unusually available"
Q_VIEWING = "Can I hear the lift and the corridor door from the bedroom?"
Q_SIGN = "Is the deposit no more than five weeks' rent, and which scheme will hold it?"


def unknown_axes_sample():
    """The sample with two axes graded unknown, so section 8 has axes to ask about."""
    data = load_sample()
    for axis in data["candidates"][0]["axes"]:
        if axis["id"] in (4, 9):
            axis["evidence_class"] = "U"
    return data


def unsourced_answer_sample():
    """The sample, with one answer that states a number and names nothing to back it."""
    data = load_sample()
    data["candidates"][0]["question_answers"].append({
        "question": "How many flats in the building are let by the night?",
        "when": "vet", "kind": "answer",
        "answer": "About 6 of the 41 flats, going by what neighbours say.",
        "evidence_class": "C"})
    return data


def esc_label(text):
    """The label as the HTML renderer writes it (apostrophes are escaped)."""
    return render.esc(text)


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
        needed += ["section.only_you", "ui.your_questions", "ui.before_signing", "ui.trigger_fired",
                   "ui.trigger_not_fired", "ui.no_trigger", "ui.unknown_axes_request"]
        needed += render.ONLY_YOU_DEFAULTS
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

    def test_all_twelve_section_headings(self):
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

    def test_same_twelve_sections_in_the_same_order(self):
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
        # 152 KB since the fixed form: fourteen questions per candidate in the example
        # report, their wording in three languages, and the `why` line under an unknown.
        self.assertEqual(build_viewer.SIZE_LIMIT, 152 * 1024, "the budget is 152 KB")
        self.assertLess(size, build_viewer.SIZE_LIMIT,
                        "viewer.html is %.1f KB, the budget is %.0f KB"
                        % (size / 1024.0, build_viewer.SIZE_LIMIT / 1024.0))

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

    def test_the_share_card_mirrors_seed_py_and_shares_nothing_else(self):
        sys.path.insert(0, SCRIPTS)
        import seed  # noqa: E402  (same reduction, in Python)
        for needle in ("function shareBlock(", "function seedFrom(", "function seedSentences(",
                       "function sBand(", "Share card", "sharetext", "sharecopy",
                       "[postcode removed]", "what I found: ", "My questions:",
                       "I will not take: ", "quiet wins when quiet and light conflict"):
            self.assertIn(needle, self.html, "viewer.html is missing %r" % needle)
        # the band rule is the one in seed.py and references/seed-format.md
        self.assertIn("hi=Math.ceil(v/100)*100, lo=Math.max(0,hi-(hi<1500?200:400))", self.html)
        self.assertEqual(seed.band(2400), "\u00a32,000\u20132,400 all-in")
        # a snapshot may hold these; the card may not read them
        body = self.html[self.html.index("/* ---- share card"):self.html.index("/* ---- page wiring")]
        for forbidden in ("guarantor_route", "notes", "rent_pcm_target", "self_intro"):
            self.assertNotIn(forbidden, body, "the share card must not read %s" % forbidden)

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


# ------------------------------------------ your questions, answered
def section_html(html, anchor):
    """The HTML of one section: from its <h2> to the next one."""
    start = html.index('<h2 id="%s"' % anchor)
    nxt = html.find("<h2 id=", start + 1)
    return html[start:nxt if nxt > 0 else len(html)]


def section_md(md, heading):
    start = md.index("## %s" % heading)
    nxt = md.find("\n## ", start + 1)
    return md[start:nxt if nxt > 0 else len(md)]


class TestQuestionAnswersSchema(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()
        self.data = load_sample()
        self.entry = {"question": "Who pays for the heating?", "when": "vet", "kind": "answer",
                      "answer": "The tenant, on the building tariff.", "evidence_class": "S",
                      "triggered": None, "sources": ["s-heat"]}

    def test_a_valid_entry_is_accepted(self):
        self.data["candidates"][0]["question_answers"].append(self.entry)
        errors, warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_an_unknown_stage_is_rejected(self):
        self.entry["when"] = "signing"
        self.data["candidates"][0]["question_answers"].append(self.entry)
        errors, _ = render.validate(self.data, self.schema)
        joined = "\n".join(errors)
        self.assertIn("when", joined)
        self.assertIn("signing", joined)
        self.assertIn("viewing", joined)  # the allowed stages are quoted back to the model

    def test_an_unknown_kind_is_rejected(self):
        self.entry["kind"] = "guess"
        self.data["candidates"][0]["question_answers"].append(self.entry)
        errors, _ = render.validate(self.data, self.schema)
        self.assertTrue(any("kind" in e and "guess" in e for e in errors), errors)

    def test_the_question_and_the_answer_are_required(self):
        del self.entry["answer"]
        self.data["candidates"][0]["question_answers"].append(self.entry)
        errors, _ = render.validate(self.data, self.schema)
        self.assertTrue(any("answer" in e for e in errors), errors)

    def test_a_request_the_user_cannot_read_in_one_line_is_rejected(self):
        self.data["candidates"][0]["only_you_can_tell"] = ["x" * 241]
        errors, _ = render.validate(self.data, self.schema)
        self.assertTrue(any("only_you_can_tell" in e and "240" in e for e in errors), errors)

    def test_the_stages_are_the_ones_the_profile_validator_accepts(self):
        """render.py places exactly the stages profile_check.py lets a user write."""
        import subprocess as sp
        import tempfile
        check = os.path.join(SCRIPTS, "profile_check.py")
        body = "my_questions:\n" + "".join(
            '  - text: "q%d"\n    when: %s\n    kind: answer\n' % (i, stage)
            for i, stage in enumerate(render.QUESTION_STAGES))
        for text, ok in ((body, True), (body + '  - text: "q"\n    when: someday\n', False)):
            handle, path = tempfile.mkstemp(suffix=".yaml")
            os.close(handle)
            try:
                with io.open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                proc = sp.Popen([sys.executable, check, path, "--json"], stdout=sp.PIPE, stderr=sp.PIPE)
                out, _err = proc.communicate()
                res = json.loads(out.decode("utf-8"))
                stage_errors = [e for e in res["errors"] if "my_questions.when" in e]
                if ok:
                    self.assertEqual([], stage_errors, res["errors"])
                else:
                    self.assertTrue(stage_errors, res["errors"])
            finally:
                os.unlink(path)
        self.assertEqual(sorted(render.QUESTION_STAGES),
                         sorted(self.schema["definitions"]["question_answer"]
                                ["properties"]["when"]["enum"]))

    def test_the_no_source_rule_is_in_the_schema_as_an_anyof(self):
        branches = self.schema["definitions"]["question_answer"].get("anyOf")
        self.assertTrue(branches, "question_answer has no anyOf")
        self.assertEqual(["computed_by", "sources"],
                         sorted(sum([b.get("required", []) for b in branches], [])))
        self.assertEqual(["sources", "computed_by"],
                         render.source_alternatives(self.schema, "question_answer"))
        for key in ("sources", "computed_by"):
            self.assertNotIn(key, self.schema["definitions"]["question_answer"]["required"])

    def test_a_compare_question_with_nothing_to_compare_is_a_warning(self):
        one = load_sample()
        one["candidates"] = one["candidates"][:1]
        del one["comparison"]
        _errors, warnings = render.validate(one, self.schema)
        self.assertTrue(any("compare question" in w for w in warnings), warnings)

    def test_a_compare_question_answered_for_one_candidate_only_is_a_warning(self):
        half = load_sample()
        half["candidates"][1]["question_answers"] = []
        _errors, warnings = render.validate(half, self.schema)
        self.assertTrue(any("hole" in w for w in warnings), warnings)


class TestUnsourcedAnswers(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_an_answer_with_a_bare_number_is_flagged(self):
        gaps = render.unsourced_numbers(unsourced_answer_sample(), self.schema)
        self.assertEqual([("question", 6)], [g["loc"] for g in gaps])
        self.assertIn("question_answers[6]", gaps[0]["message"])
        self.assertIn("computed_by", gaps[0]["message"])

    def test_an_answer_with_no_number_in_it_is_not_flagged(self):
        data = unsourced_answer_sample()
        data["candidates"][0]["question_answers"][-1]["answer"] = "Nobody would say."
        self.assertEqual([], render.unsourced_numbers(data, self.schema))

    def test_the_example_report_backs_every_answer_that_states_a_number(self):
        self.assertEqual([], render.unsourced_numbers(load_sample(), self.schema))

    def test_strict_turns_it_into_an_error(self):
        path = write_temp(unsourced_answer_sample())
        try:
            code, out, err = run_cli(path, "--strict", "--validate-only")
            self.assertEqual(1, code, err)
            self.assertIn("WARNING  no source:", err)
            self.assertIn("1 number(s) with no source", err)
            self.assertEqual("", out)
        finally:
            os.unlink(path)

    def test_the_html_marks_that_answer_and_the_clean_one_is_marked_nowhere(self):
        path = write_temp(unsourced_answer_sample())
        try:
            code, html, err = run_cli(path)
            self.assertEqual(0, code, err)
            self.assertEqual(1, html.count('class="chip nosource"'), html.count("nosource"))
        finally:
            os.unlink(path)
        code, html, err = run_cli(SAMPLE)
        self.assertEqual(0, code, err)
        self.assertNotIn('class="chip nosource"', html)


class TestQuestionAnswersOutput(unittest.TestCase):
    """Every question is answered where the user reads it, in both renderers."""

    @classmethod
    def setUpClass(cls):
        cls.code, cls.html, cls.err = run_cli(SAMPLE)
        cls.md_code, cls.md, cls.md_err = run_cli(SAMPLE, "--md")

    def test_a_filter_question_sits_with_the_hard_filters_and_nowhere_else(self):
        self.assertEqual(0, self.code, self.err)
        self.assertIn(Q_FILTER, section_html(self.html, "hard-filters"))
        self.assertEqual(1, self.html.count(Q_FILTER), "a question belongs to one stage only")
        self.assertEqual(1, self.md.count(Q_FILTER), self.md_err)
        self.assertIn(Q_FILTER, section_md(self.md, "2. Your must-haves"))

    def test_a_vet_question_sits_under_the_verdict(self):
        verdict = section_html(self.html, "verdict")
        self.assertIn(Q_VET, verdict)
        self.assertIn("Your questions, answered", verdict)
        self.assertIn(Q_VET, section_md(self.md, "1. Verdict"))

    def test_a_compare_question_is_a_row_of_the_side_by_side_table(self):
        comparison = section_html(self.html, "comparison")
        self.assertIn(Q_COMPARE, comparison)
        # one row for the question, one cell per candidate, so the text appears once
        self.assertEqual(1, comparison.count(Q_COMPARE))
        self.assertIn(Q_COMPARE, section_md(self.md, "4. Side by side"))

    def test_the_viewing_and_signing_questions_sit_in_the_checklists(self):
        questions = section_html(self.html, "questions")
        self.assertIn(Q_VIEWING, questions)
        self.assertIn(Q_SIGN, questions)
        self.assertIn("Before you sign", questions)
        md = section_md(self.md, "8. Questions to ask")
        self.assertIn(Q_VIEWING, md)
        self.assertIn(Q_SIGN, md)
        self.assertIn("**Before you sign**", md)

    def test_each_answer_carries_an_evidence_grade_and_whether_the_trigger_fired(self):
        for needle in ("the trigger fired", "the trigger did not fire", "asked of every flat"):
            self.assertIn(needle, self.html, needle)
            self.assertIn(needle, self.md, needle)
        filters = section_html(self.html, "hard-filters")
        self.assertIn("the trigger fired", filters)
        self.assertIn("Self-reported", filters)

    def test_the_reader_sees_the_labels_in_their_own_language(self):
        code, zh, err = run_cli(SAMPLE, "--lang", "zh-TW")
        self.assertEqual(0, code, err)
        self.assertIn("\u4f60\u7684\u554f\u984c\uff0c\u7b54\u6848\u5728\u9019", zh)   # Your questions, answered
        self.assertIn("\u4f60\u8a2d\u7684\u689d\u4ef6\u6210\u7acb\u4e86", zh)              # the trigger fired
        self.assertIn("\u7c3d\u7d04\u4e4b\u524d", zh)                                    # Before you sign


class TestOnlyYouCanTell(unittest.TestCase):
    """Section 8: the unknown axes and the things no tool can sense, as a request."""

    @classmethod
    def setUpClass(cls):
        cls.path = write_temp(unknown_axes_sample())
        cls.code, cls.html, cls.err = run_cli(cls.path)
        cls.md_code, cls.md, cls.md_err = run_cli(cls.path, "--md")
        cls.plain_code, cls.plain_html, cls.plain_err = run_cli(SAMPLE)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.path)

    def test_the_section_is_between_the_questions_and_the_gaps(self):
        self.assertEqual(0, self.plain_code, self.plain_err)
        self.assertIn('<h2 id="only-you">9. What only you can tell</h2>', self.plain_html)
        self.assertLess(self.plain_html.index('id="questions"'), self.plain_html.index('id="only-you"'))
        self.assertLess(self.plain_html.index('id="only-you"'), self.plain_html.index('id="gaps"'))
        self.assertEqual(("section.only_you", "only-you"), render.SECTIONS[8])

    def test_it_opens_with_a_request_not_a_gap(self):
        block = section_html(self.plain_html, "only-you")
        self.assertIn("We could not check these for you.", block)
        self.assertIn("Please", block)

    def test_it_lists_every_unknown_axis_by_its_label(self):
        self.assertEqual(0, self.code, self.err)
        block = section_html(self.html, "only-you")
        for label in ("Construction nearby", "Aspect and light"):
            self.assertIn("<strong>%s</strong>" % label, block)
        self.assertNotIn("<strong>Crime</strong>", block)   # graded official, not unknown
        for label in ("Construction nearby", "Aspect and light"):
            self.assertIn("**%s**" % label, section_md(self.md, "9. What only you can tell"))

    def test_it_shows_what_the_report_asked_for(self):
        block = section_html(self.plain_html, "only-you")
        self.assertIn("the ventilation is shared", block)
        self.assertIn("reached for the light", block)
        self.assertIn("the ventilation is shared", section_md(self.md, "9. What only you can tell"))

    def test_a_candidate_that_asked_for_nothing_gets_the_four_standard_requests(self):
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        block = section_html(self.plain_html, "only-you")
        second = block[block.index("Flat 201, Marlow Wharf"):]
        self.assertEqual(4, len(render.ONLY_YOU_DEFAULTS))
        for term_id in render.ONLY_YOU_DEFAULTS:
            self.assertIn(L.label(term_id), second, term_id)
            self.assertIn(L.label(term_id), section_md(self.md, "9. What only you can tell"))

    def test_the_requests_read_the_same_in_chinese(self):
        code, zh, err = run_cli(SAMPLE, "--lang", "zh-TW")
        self.assertEqual(0, code, err)
        L = render.Labels(render.load_glossary(GLOSSARY), "zh-TW")
        self.assertIn(L.label("section.only_you"), zh)
        self.assertIn(L.label("only_you.smell"), zh)


class TestViewerDrawsBothSections(unittest.TestCase):
    def setUp(self):
        self.viewer = read(VIEWER)

    def test_it_carries_the_same_pieces(self):
        for needle in ("function qaAt(", "function qaBlock(", "function trigState(",
                       "function onlyYouAsks(", "function noSrcQA(", "ONLY_YOU_DEFAULTS",
                       "ui.your_questions", "ui.before_signing", "ui.trigger_fired",
                       "ui.trigger_not_fired", "ui.no_trigger", "ui.unknown_axes_request",
                       '["section.only_you","only-you"]',
                       "var RENDERERS=[s1,s2,s2f,s3,s4,s5,s6,s7,s8,s9,s10,s11]"):
            self.assertIn(needle, self.viewer.replace(", ", ","), needle)

    def test_it_carries_the_four_standard_requests_in_three_languages(self):
        start = self.viewer.index("/*BEGIN:GLOSSARY*/")
        block = self.viewer[start:self.viewer.index("/*END:GLOSSARY*/")]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        for term_id in render.ONLY_YOU_DEFAULTS + ["section.only_you", "ui.your_questions"]:
            self.assertIn(term_id, payload)
            for lang in ("en", "zh-TW", "zh-CN"):
                self.assertTrue(payload[term_id].get(lang), "%s has no %s" % (term_id, lang))

    def test_the_example_it_ships_answers_the_questions(self):
        start = self.viewer.index("/*BEGIN:SAMPLE*/")
        block = self.viewer[start:self.viewer.index("/*END:SAMPLE*/")]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        stages = [qa["when"] for qa in payload["candidates"][0]["question_answers"]]
        self.assertEqual(["filter", "vet", "compare", "compare", "viewing", "sign"], stages)
        self.assertTrue(payload["candidates"][0]["only_you_can_tell"])
        self.assertNotIn("only_you_can_tell", payload["candidates"][1],
                         "the second candidate exercises the four standard requests")

    def test_the_build_step_is_up_to_date_and_inside_the_budget(self):
        self.assertEqual(0, build_viewer.main(["--check"]))
        self.assertLess(len(self.viewer.encode("utf-8")), build_viewer.SIZE_LIMIT)


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
        self.assertLess(html.index("12. About this report"), html.rindex(line))

    def test_the_markdown_prints_it_in_both_places(self):
        code, md, err = run_cli(SAMPLE, "--md")
        self.assertEqual(0, code, err)
        lines = md.splitlines()
        self.assertTrue(lines[0].startswith("# "), lines[0])
        self.assertTrue(lines[2].startswith("Configuration: breadth \u2014 "), lines[:4])
        self.assertEqual(2, md.count("Configuration: breadth \u2014 "), md.count("Configuration"))
        after = md[md.index("## 12. About this report"):]
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



# ------------------------------------------------- the fixed form: fourteen questions
def fixed_entry(cand, fid):
    for entry in cand["fixed_answers"]:
        if entry["id"] == fid:
            return entry
    raise AssertionError("the sample does not answer %s" % fid)


class TestFixedQuestionsFile(unittest.TestCase):
    """references/fixed-questions.yaml: the machine side of the form."""

    def setUp(self):
        self.questions = scan.load_questions(FIXED_QUESTIONS)
        self.terms = render.load_glossary(GLOSSARY)

    def test_fourteen_questions_with_the_fields_the_form_needs(self):
        self.assertEqual(render.FIXED_IDS, sorted(self.questions, key=scan.sort_key))
        for fid, item in self.questions.items():
            self.assertIn(item.get("group"), ("gate", "listing"), fid)
            self.assertIn(item.get("answer_type"),
                          ("weeks", "money", "yes_no", "text", "letter", "date"), fid)
            self.assertIn(item.get("ask_if_missing"), ("always", "when_page_pasted"), fid)
            self.assertTrue(item.get("why"), "%s has no why line" % fid)
            self.assertTrue(item.get("look_for"), "%s has nothing to look for" % fid)

    def test_the_gate_is_asked_of_every_flat_and_the_listing_only_on_a_paste(self):
        gate = [f for f, i in self.questions.items() if i["group"] == "gate"]
        listing = [f for f, i in self.questions.items() if i["group"] == "listing"]
        self.assertEqual(render.FIXED_IDS[:8], sorted(gate, key=scan.sort_key))
        self.assertEqual(render.FIXED_IDS[8:], sorted(listing, key=scan.sort_key))
        for fid in gate:
            self.assertEqual("always", self.questions[fid]["ask_if_missing"], fid)
        for fid in listing:
            self.assertEqual("when_page_pasted", self.questions[fid]["ask_if_missing"], fid)

    def test_every_cap_points_at_a_real_threshold(self):
        thresholds = read(os.path.join(REFS, "thresholds.yaml"))
        capped = [f for f, i in self.questions.items() if i.get("cap")]
        self.assertTrue(set(["F1", "F2", "F3"]) <= set(capped), capped)
        for fid in capped:
            pointer = self.questions[fid]["cap"]
            self.assertTrue(pointer.startswith("thresholds.yaml#"), pointer)
            key = pointer.split("#", 1)[1]
            self.assertIn("\n%s:" % key, thresholds, "%s points at a missing threshold" % fid)

    def test_the_patterns_are_bilingual_and_compile(self):
        for fid, item in self.questions.items():
            patterns = item["look_for"]
            self.assertTrue(any(not any(ord(ch) > 0x2E00 for ch in p) for p in patterns),
                            "%s has no English pattern" % fid)
            self.assertTrue(any(any(ord(ch) > 0x2E00 for ch in p) for p in patterns),
                            "%s has no Chinese pattern" % fid)
            self.assertEqual(len(patterns), len(item["patterns"]))

    def test_the_wording_is_in_the_glossary_in_three_languages(self):
        for fid in render.FIXED_IDS:
            entry = self.terms.get("fixed." + fid)
            self.assertTrue(entry, "glossary.yaml has no fixed.%s" % fid)
            for lang in ("en", "zh-TW", "zh-CN"):
                self.assertTrue(entry.get(lang), "fixed.%s has no %s label" % (fid, lang))
            self.assertTrue(entry.get("plain"), "fixed.%s has no plain gloss" % fid)
        for term_id in ("section.fixed", "ui.found", "ui.asked_you", "ui.unknown", "ui.quote",
                        "ui.fixed_lead"):
            self.assertIn(term_id, self.terms)
            for lang in ("en", "zh-TW", "zh-CN"):
                self.assertTrue(self.terms[term_id].get(lang), "%s has no %s" % (term_id, lang))


class TestFixedAnswersSchema(unittest.TestCase):
    """Three states and no fourth, fourteen ids, once each."""

    def setUp(self):
        self.schema = load_schema()
        self.data = load_sample()

    def test_the_example_answers_all_fourteen_for_every_candidate(self):
        for cand in self.data["candidates"]:
            ids = [e["id"] for e in cand["fixed_answers"]]
            self.assertEqual(render.FIXED_IDS, sorted(ids, key=scan.sort_key))
            self.assertEqual(sorted(ids), sorted(set(ids)))
        errors, warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_a_valid_found_answer_is_accepted(self):
        entry = fixed_entry(self.data["candidates"][0], "F1")
        self.assertEqual("found", entry["status"])
        self.assertTrue(entry["quote"])
        self.assertNotEqual("user", entry["source"])
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)

    def test_a_found_answer_with_no_quote_is_rejected(self):
        fixed_entry(self.data["candidates"][0], "F1").pop("quote")
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertTrue(any("carries no quote" in e for e in errors), errors)

    def test_a_found_answer_sourced_to_the_user_is_rejected(self):
        fixed_entry(self.data["candidates"][0], "F1")["source"] = "user"
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertTrue(any("'found' with source 'user'" in e for e in errors), errors)

    def test_an_asked_answer_with_a_source_that_is_not_the_user_is_rejected(self):
        fixed_entry(self.data["candidates"][0], "F3")["source"] = "s-listing-1"
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertTrue(any("is 'asked' but its source is" in e for e in errors), errors)

    def test_an_unknown_answer_that_carries_a_quote_is_rejected(self):
        fixed_entry(self.data["candidates"][0], "F6")["quote"] = "The deposit is protected."
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertTrue(any("'unknown' but carries a quote" in e for e in errors), errors)

    def test_a_repeated_id_is_an_error(self):
        cand = self.data["candidates"][0]
        cand["fixed_answers"].append(dict(fixed_entry(cand, "F1")))
        errors, _warnings = render.validate(self.data, self.schema)
        self.assertTrue(any("a second time" in e for e in errors), errors)

    def test_a_missing_id_warns_by_default_and_fails_strict(self):
        cand = self.data["candidates"][0]
        cand["fixed_answers"] = [e for e in cand["fixed_answers"] if e["id"] != "F8"]
        errors, warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)
        self.assertTrue(any("does not answer F8" in w for w in warnings), warnings)
        path = write_temp(self.data)
        try:
            self.assertEqual(0, run_cli(path, "--validate-only")[0])
            self.assertEqual(1, run_cli(path, "--validate-only", "--strict")[0])
        finally:
            os.unlink(path)

    def test_no_fixed_answers_at_all_warns_rather_than_breaking_an_older_report(self):
        self.data["candidates"][0].pop("fixed_answers")
        errors, warnings = render.validate(self.data, self.schema)
        self.assertEqual([], errors)
        self.assertTrue(any("has no fixed_answers" in w for w in warnings), warnings)

    def test_an_unknown_that_states_a_number_is_flagged_and_fails_strict(self):
        entry = fixed_entry(self.data["candidates"][0], "F6")
        entry["answer"] = "Probably one of the 3 schemes, nobody said which."
        gaps = render.unsourced_numbers(self.data, self.schema)
        self.assertEqual([("fixed", 5)], [g["loc"] for g in gaps])
        self.assertIn("F6", gaps[0]["message"])
        path = write_temp(self.data)
        try:
            self.assertEqual(0, run_cli(path, "--validate-only")[0])
            self.assertEqual(1, run_cli(path, "--validate-only", "--strict")[0])
        finally:
            os.unlink(path)

    def test_a_found_answer_with_a_source_and_an_asked_answer_state_numbers_freely(self):
        self.assertEqual([], render.unsourced_numbers(self.data, self.schema))
        found = fixed_entry(self.data["candidates"][0], "F1")
        self.assertTrue(render.states_a_number(found["answer"]))
        asked = fixed_entry(self.data["candidates"][0], "F3")
        self.assertEqual("user", asked["source"])


class TestFixedAnswersOutput(unittest.TestCase):
    """Section 3 in both renderers, from the same JSON."""

    @classmethod
    def setUpClass(cls):
        cls.code, cls.html, cls.err = run_cli(SAMPLE)
        cls.md_code, cls.md, cls.md_err = run_cli(SAMPLE, "--md")
        cls.questions = scan.load_questions(FIXED_QUESTIONS)

    def test_the_section_sits_right_after_the_hard_filters(self):
        self.assertEqual(0, self.code, self.err)
        self.assertIn('<h2 id="fixed">3. The questions we always answer</h2>', self.html)
        self.assertLess(self.html.index('id="hard-filters"'), self.html.index('id="fixed"'))
        self.assertLess(self.html.index('id="fixed"'), self.html.index('id="comparison"'))
        self.assertEqual(("section.fixed", "fixed"), render.SECTIONS[2])

    def test_every_question_is_a_row_with_its_own_wording(self):
        block = section_html(self.html, "fixed")
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        for fid in render.FIXED_IDS:
            self.assertIn(esc_label(L.label("fixed." + fid)), block, fid)

    def test_the_three_states_draw_the_three_chips(self):
        block = section_html(self.html, "fixed")
        self.assertIn('<span class="ok" title="Somebody wrote this down', block)
        self.assertIn('<span class="unk" title="Nothing was written down', block)
        self.assertIn('<span class="bad" title="Nobody checked', block)

    def test_a_found_answer_shows_the_sentence_it_came_from(self):
        block = section_html(self.html, "fixed")
        self.assertIn("\u201c%s\u201d" % render.esc("Deposit: five weeks' rent, 2,480."), block)

    def test_an_unknown_row_tells_the_reader_what_to_go_and_find(self):
        block = section_html(self.html, "fixed")
        self.assertIn(self.questions["F6"]["why"], block)
        self.assertIn(self.questions["F8"]["why"], block)

    def test_the_markdown_mirrors_it(self):
        self.assertEqual(0, self.md_code, self.md_err)
        block = section_md(self.md, "3. The questions we always answer")
        L = render.Labels(render.load_glossary(GLOSSARY), "en")
        for fid in render.FIXED_IDS:
            self.assertIn(L.label("fixed." + fid), block, fid)
        for state in ("Found in writing", "You told us", "Not known"):
            self.assertIn(state, block, state)
        self.assertIn("Deposit: five weeks' rent, 2,480.", block)
        self.assertIn(self.questions["F6"]["why"], block)

    def test_the_reader_sees_the_questions_in_their_own_language(self):
        code, zh, err = run_cli(SAMPLE, "--lang", "zh-TW")
        self.assertEqual(0, code, err)
        L = render.Labels(render.load_glossary(GLOSSARY), "zh-TW")
        self.assertIn(L.label("section.fixed"), zh)
        self.assertIn(L.label("fixed.F1"), zh)
        self.assertIn(L.label("ui.found"), zh)
        self.assertIn(L.label("ui.fixed_lead"), zh)

    def test_an_unsourced_number_in_an_answer_gets_the_visible_chip(self):
        data = load_sample()
        for entry in data["candidates"][0]["fixed_answers"]:
            if entry["id"] == "F8":
                entry["answer"] = "There are 2 licensing schemes in this borough, nobody said which."
        path = write_temp(data)
        try:
            code, html, err = run_cli(path)
            self.assertEqual(0, code, err)
            self.assertIn("no source", section_html(html, "fixed"))
            self.assertIn("WARNING  no source", err)
        finally:
            os.unlink(path)


class TestViewerDrawsTheFixedForm(unittest.TestCase):
    def setUp(self):
        self.viewer = read(VIEWER)

    def test_it_carries_the_same_pieces(self):
        for needle in ("function s2f(", "function fixedRows(", "function noSrcFixed(",
                       "var FIXED_STATES=", '["section.fixed","fixed"]', "var FIXED = {",
                       "ui.found", "ui.asked_you", "ui.quote", "ui.fixed_lead"):
            self.assertIn(needle, self.viewer.replace(", ", ","), needle)

    def test_it_inlines_the_why_lines_and_nothing_the_scanner_needs(self):
        start = self.viewer.index("/*BEGIN:FIXED*/")
        block = self.viewer[start:self.viewer.index("/*END:FIXED*/")]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        self.assertEqual(build_viewer.layout_questions(scan.load_questions(FIXED_QUESTIONS)), payload)
        self.assertEqual(render.FIXED_IDS, sorted(payload, key=scan.sort_key))
        for fid, item in payload.items():
            self.assertTrue(item["why"], fid)
            self.assertNotIn("look_for", item)
            self.assertNotIn("patterns", item)

    def test_the_questions_are_inlined_in_three_languages(self):
        start = self.viewer.index("/*BEGIN:GLOSSARY*/")
        block = self.viewer[start:self.viewer.index("/*END:GLOSSARY*/")]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        for fid in render.FIXED_IDS:
            for lang in ("en", "zh-TW", "zh-CN"):
                self.assertTrue(payload["fixed." + fid].get(lang), "fixed.%s %s" % (fid, lang))

    def test_the_example_it_ships_answers_all_fourteen(self):
        start = self.viewer.index("/*BEGIN:SAMPLE*/")
        block = self.viewer[start:self.viewer.index("/*END:SAMPLE*/")]
        payload = json.loads(block[block.index("{"):block.rindex("}") + 1])
        for cand in payload["candidates"]:
            self.assertEqual(render.FIXED_IDS,
                             sorted([e["id"] for e in cand["fixed_answers"]], key=scan.sort_key))
        states = set(e["status"] for c in payload["candidates"] for e in c["fixed_answers"])
        self.assertEqual(set(["found", "asked", "unknown"]), states)

    def test_the_build_step_is_up_to_date_and_inside_the_budget(self):
        self.assertEqual(0, build_viewer.main(["--check"]))
        self.assertLess(len(self.viewer.encode("utf-8")), build_viewer.SIZE_LIMIT)


if __name__ == "__main__":
    unittest.main()
