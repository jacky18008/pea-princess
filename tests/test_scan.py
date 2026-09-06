# -*- coding: utf-8 -*-
"""Offline tests for scripts/scan.py, the fixed-form pre-scanner.

No network: the only input is tests/fixtures/pasted-listing.txt, an invented flat at an
invented address, and references/fixed-questions.yaml.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

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

sys.path.insert(0, SCRIPTS)
import scan  # noqa: E402

QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")
LISTING = os.path.join(HERE, "fixtures", "pasted-listing.txt")
IDS = ["F%d" % i for i in range(1, 19)]
GATE = IDS[:8]
LISTING_IDS = IDS[8:14]
EXTENDED = IDS[14:]


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def run_cli(*args):
    proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "scan.py")] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8"), err.decode("utf-8")


class TestTheParser(unittest.TestCase):
    def test_maps_lists_quotes_and_comments(self):
        doc = scan.parse_questions(
            '# a comment\n'
            'version: "1"\n'
            'questions:\n'
            '  F1:\n'
            '    group: gate\n'
            '    axis: 7\n'
            '    why: "one sentence"\n'
            '    look_for:\n'
            "      - 'deposit\\s+\\d+'\n"
            '      - "plain"\n')
        self.assertEqual("1", doc["version"])
        item = doc["questions"]["F1"]
        self.assertEqual("gate", item["group"])
        self.assertEqual(7, item["axis"])
        self.assertEqual("one sentence", item["why"])
        self.assertEqual(["deposit\\s+\\d+", "plain"], item["look_for"])

    def test_a_single_quoted_value_keeps_its_backslashes(self):
        doc = scan.parse_questions("a:\n  b: '[^.\\n]{0,40}'\n")
        self.assertEqual("[^.\\n]{0,40}", doc["a"]["b"])

    def test_an_unquoted_sentence_is_refused(self):
        with self.assertRaises(scan.QuestionsError):
            scan.parse_questions("a:\n  why: a bare sentence, with a comma\n")

    def test_an_odd_indent_is_refused(self):
        with self.assertRaises(scan.QuestionsError):
            scan.parse_questions("a:\n   b: \"x\"\n")


class TestTheQuestionsFile(unittest.TestCase):
    def setUp(self):
        self.questions = scan.load_questions(QUESTIONS)

    def test_eighteen_questions_with_compiled_patterns(self):
        self.assertEqual(IDS, sorted(self.questions, key=scan.sort_key))
        for fid, item in self.questions.items():
            self.assertEqual(fid, item["id"])
            self.assertTrue(item["patterns"], fid)

    def test_the_header_says_how_the_file_is_read(self):
        text = read(QUESTIONS)
        self.assertIn("Part of Pea Princess (vet-flat)", text.splitlines()[0])
        for word in ("found", "asked", "unknown", "scripts/scan.py"):
            self.assertIn(word, text)


class TestTheTiersBlock(unittest.TestCase):
    """The one place the mapping from how deep a run goes to how many questions lives."""

    def setUp(self):
        self.questions = scan.load_questions(QUESTIONS)
        self.tiers = scan.load_tiers(QUESTIONS)

    def test_every_question_is_in_exactly_one_group(self):
        groups = {}
        for fid, item in self.questions.items():
            groups.setdefault(item.get("group"), []).append(fid)
        self.assertEqual(["extended", "gate", "listing"], sorted(groups))
        self.assertEqual(GATE, sorted(groups["gate"], key=scan.sort_key))
        self.assertEqual(LISTING_IDS, sorted(groups["listing"], key=scan.sort_key))
        self.assertEqual(EXTENDED, sorted(groups["extended"], key=scan.sort_key))

    def test_every_group_a_tier_names_is_a_real_group(self):
        real = set(item.get("group") for item in self.questions.values())
        for name, groups in self.tiers.items():
            self.assertTrue(set(groups) <= real, "%s names %s" % (name, groups))

    def test_the_budget_modes_and_the_recorded_tiers_all_resolve(self):
        # profile.yaml budget_mode, generated_by.tier, and the words the user may write
        # in advanced.fixed_form.questions - every one of them has to be in the block.
        for name in ("lite", "standard", "deep", "breadth", "manual", "gate", "full"):
            self.assertIn(name, self.tiers, name)

    def test_eight_fourteen_eighteen(self):
        ids = lambda name: scan.ids_for_tier(self.questions, self.tiers, name)
        self.assertEqual(GATE, ids("lite"))
        self.assertEqual(GATE, ids("gate"))
        self.assertEqual(GATE + LISTING_IDS, ids("standard"))
        self.assertEqual(GATE + LISTING_IDS, ids("manual"))
        for name in ("deep", "breadth", "full"):
            self.assertEqual(IDS, ids(name), name)

    def test_a_tier_nobody_recognises_answers_the_fourteen(self):
        self.assertEqual(GATE + LISTING_IDS,
                         scan.ids_for_tier(self.questions, self.tiers, "no-such-tier"))

    def test_a_file_with_no_tiers_block_is_an_error_not_a_silent_zero(self):
        with self.assertRaises(scan.QuestionsError):
            scan.load_tiers(LISTING)


class TestScanningAPastedPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = scan.load_questions(QUESTIONS)
        cls.result = scan.scan(read(LISTING), cls.questions, "pasted-listing.txt")
        cls.by_id = dict((item["id"], item) for item in cls.result["items"])

    def test_the_fixture_is_invented_and_says_so(self):
        text = read(LISTING)
        self.assertIn("X12 4AB", text, "the postcode has to be an impossible one")
        self.assertTrue(any(ord(ch) > 0x2E00 for ch in text), "the fixture has Chinese lines too")

    def test_every_question_is_reported_in_order(self):
        self.assertEqual(IDS, [item["id"] for item in self.result["items"]])

    def test_it_finds_candidates_for_at_least_ten_of_them(self):
        answered = [fid for fid in IDS if self.by_id[fid]["candidates"]]
        self.assertGreaterEqual(len(answered), 10, "only found %s" % answered)

    def test_the_candidates_are_sentences_from_the_page_with_line_numbers(self):
        lines = read(LISTING).splitlines()
        for item in self.result["items"]:
            for cand in item["candidates"]:
                self.assertTrue(1 <= cand["line_no"] <= len(lines))
                self.assertIn(cand["text"], lines[cand["line_no"] - 1])
                self.assertLessEqual(len(cand["text"]), scan.MAX_TEXT)

    def test_it_reads_the_english_and_the_chinese(self):
        deposit = [c["text"] for c in self.by_id["F1"]["candidates"]]
        self.assertTrue(any("five weeks" in t for t in deposit), deposit)
        self.assertTrue(any("\u62bc\u91d1" in t for t in deposit), deposit)
        area = [c["text"] for c in self.by_id["F9"]["candidates"]]
        self.assertTrue(any("68 sq m" in t for t in area), area)
        self.assertTrue(any("\u5e73\u65b9\u7c73" in t for t in area), area)

    def test_at_most_five_candidates_per_question_and_no_repeats(self):
        for item in self.result["items"]:
            texts = [c["text"] for c in item["candidates"]]
            self.assertLessEqual(len(texts), scan.MAX_CANDIDATES, item["id"])
            self.assertEqual(len(texts), len(set(t.lower() for t in texts)), item["id"])

    def test_the_silent_ids_are_the_ones_with_nothing_to_read(self):
        silent = self.result["summary"]["silent"]
        self.assertEqual(silent, [fid for fid in IDS if not self.by_id[fid]["candidates"]])
        self.assertTrue(silent, "the fixture is meant to leave some questions silent")
        for fid in silent:
            self.assertIn(fid, scan.silent_line(self.result))
        self.assertIn("ask the user", scan.silent_line(self.result))

    def test_a_page_that_answers_nothing_is_silent_on_every_question(self):
        result = scan.scan("A flat. It is nice. Come and see it.\n", self.questions, "x.txt")
        self.assertEqual(IDS, result["summary"]["silent"])
        self.assertEqual(0, result["summary"]["found_candidates"])

    def test_an_empty_page_does_not_break_it(self):
        result = scan.scan("", self.questions, "x.txt")
        self.assertEqual(0, result["lines"])
        self.assertEqual(IDS, result["summary"]["silent"])


class TestSentencesAndExcerpts(unittest.TestCase):
    def test_a_decimal_point_does_not_end_a_sentence(self):
        self.assertEqual(["The rent is 2,400.00 a month."],
                         scan.sentences("The rent is 2,400.00 a month."))

    def test_english_and_chinese_sentences_split(self):
        self.assertEqual(["One. ".strip(), "Two."], scan.sentences("One. Two."))
        self.assertEqual(["\u62bc\u91d1\u4e94\u9031\u3002", "\u79df\u671f\u4e00\u5e74\u3002"],
                         scan.sentences("\u62bc\u91d1\u4e94\u9031\u3002\u79df\u671f\u4e00\u5e74\u3002"))

    def test_a_very_long_line_is_cut_to_a_window_around_the_match(self):
        import re
        text = "x " * 300 + "deposit five weeks" + " y" * 300
        got = scan.excerpt(text, re.search("deposit five weeks", text))
        self.assertLessEqual(len(got), scan.MAX_TEXT)
        self.assertIn("deposit five weeks", got)


class TestTheCommandLine(unittest.TestCase):
    def test_json_on_stdout_and_the_silent_line_on_stderr(self):
        code, out, err = run_cli(LISTING)
        self.assertEqual(0, code, err)
        payload = json.loads(out)
        self.assertTrue(payload["ok"])
        self.assertEqual("pasted-listing.txt", payload["source"])
        self.assertEqual(18, len(payload["items"]))
        self.assertEqual("full", payload["tier"])
        self.assertIn("no sentence found for", err)
        for fid in payload["summary"]["silent"]:
            self.assertIn(fid, err)

    def test_it_reads_stdin(self):
        proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "scan.py"), "-"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate(read(LISTING).encode("utf-8"))
        self.assertEqual(0, proc.returncode, err.decode("utf-8"))
        payload = json.loads(out.decode("utf-8"))
        self.assertEqual("stdin", payload["source"])
        self.assertGreater(payload["summary"]["found_candidates"], 10)

    def test_the_gate_tier_looks_for_the_gate_and_names_only_gate_misses(self):
        code, out, err = run_cli(LISTING, "--tier", "gate", "--table")
        self.assertEqual(0, code, err)
        silent = err.split("no sentence found for ")[1].split(" \u2014")[0]
        self.assertTrue(set(silent.split(", ")) <= set(GATE), silent)
        for fid in LISTING_IDS + EXTENDED:
            self.assertNotIn("\n" + fid + " ", out, "%s is not a gate question" % fid)
        code, out, _err = run_cli(LISTING, "--tier", "gate")
        self.assertEqual(GATE, [item["id"] for item in json.loads(out)["items"]])

    def test_an_unknown_tier_exits_two_and_lists_the_real_ones(self):
        code, _out, err = run_cli(LISTING, "--tier", "enormous")
        self.assertEqual(2, code)
        self.assertIn("Unknown tier", err)
        self.assertIn("standard", err)

    def test_the_table_is_readable_and_names_the_silent_ones(self):
        code, out, err = run_cli(LISTING, "--table")
        self.assertEqual(0, code, err)
        self.assertIn("candidate sentence", out)
        self.assertIn("nothing found", out)
        self.assertIn("F14", out)

    def test_a_missing_file_exits_one_with_a_readable_message(self):
        code, _out, err = run_cli(os.path.join(HERE, "no-such-file.txt"))
        self.assertEqual(1, code)
        self.assertIn("Cannot read the text", err)

    def test_a_broken_questions_file_exits_one(self):
        code, _out, err = run_cli(LISTING, "--questions", LISTING)
        self.assertEqual(1, code)
        self.assertIn("Cannot read the questions", err)


class TestItIsOfflineAndStandardLibraryOnly(unittest.TestCase):
    def test_no_network_no_third_party_imports(self):
        text = read(os.path.join(SCRIPTS, "scan.py"))
        for forbidden in ("import requests", "urllib", "_fetch", "socket", "subprocess"):
            self.assertNotIn(forbidden, text, forbidden)


if __name__ == "__main__":
    unittest.main()
