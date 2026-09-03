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
                   "ui.fail", "ui.unknown", "ui.evidence", "ui.nothing_listed", "ui.no_data"]
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
        self.assertLess(size, 120 * 1024, "viewer.html is %.1f KB, the budget is 120 KB" % (size / 1024.0))

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

    def test_build_step_is_up_to_date(self):
        self.assertEqual(0, build_viewer.main(["--check"]),
                         "viewer.html is out of date: run python3 viewer/build_viewer.py")


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
