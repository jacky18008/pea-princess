# -*- coding: utf-8 -*-
"""Offline tests for scripts/find.py, the grep-shaped finder for pasted documents.

No network. The only inputs are tests/fixtures/find/ — four invented documents at an
invented address — and skills/vet-flat/references/{find-synonyms,fixed-questions}.yaml.

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
FIXTURES = os.path.join(HERE, "fixtures", "find")

sys.path.insert(0, SCRIPTS)
import find  # noqa: E402
import scan  # noqa: E402

TENANCY = os.path.join(FIXTURES, "tenancy-agreement.txt")
REVIEWS = os.path.join(FIXTURES, "resident-reviews.txt")
PLANNING = os.path.join(FIXTURES, "planning-officer-report.txt")
LISTING = os.path.join(FIXTURES, "listing.txt")
SYNONYMS = os.path.join(REFS, "find-synonyms.yaml")

# What the four fixtures split into: paragraphs, plus the windows of the one long clause.
EXPECTED_UNITS = {"listing.txt": 4, "planning-officer-report.txt": 12,
                  "resident-reviews.txt": 42, "tenancy-agreement.txt": 39}


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def run_cli(*args):
    proc = subprocess.Popen([sys.executable, os.path.join(SCRIPTS, "find.py")] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8"), err.decode("utf-8")


def blocks(out):
    """The hit blocks of a --context 0 run: a paragraph never contains a blank line."""
    return [b for b in out.split("\n\n") if b.strip()]


def hits_json(*args):
    code, out, err = run_cli(*(list(args) + ["--json"]))
    return code, json.loads(out) if out.strip() else [], err


class TestTheTokenizer(unittest.TestCase):
    def test_cjk_runs_become_character_bigrams(self):
        self.assertEqual(["押金"], find.tokens("押金"))
        self.assertEqual(["提前", "前退", "退租"], find.tokens("提前退租"))
        self.assertIn("潮濕", find.tokens("臥室牆角一到冬天就潮濕，窗邊發霉"))
        self.assertIn("發霉", find.tokens("臥室牆角一到冬天就潮濕，窗邊發霉"))

    def test_money_percent_and_numbers_survive(self):
        got = find.tokens("Deposit £2,128.85 is 5 weeks, or 12% of 48 m²")
        for term in ("£", "2,128.85", "5", "week", "12", "%", "48", "m", "²"):
            self.assertIn(term, got, term)

    def test_light_stemming_keeps_four_letters(self):
        self.assertEqual("week", find.stem("weeks"))
        self.assertEqual("clause", find.stem("clauses"))
        self.assertEqual("heat", find.stem("heating"))
        self.assertEqual("furnish", find.stem("furnished"))
        for short in ("gas", "is", "as", "less", "thing"):
            self.assertEqual(short, find.stem(short), short)


class TestTheSynonymFile(unittest.TestCase):
    def setUp(self):
        self.groups = find.load_synonyms(SYNONYMS)

    def test_it_parses_with_the_tiny_reader_scan_py_uses(self):
        doc = scan.parse_questions(read(SYNONYMS))
        self.assertEqual(sorted(doc), ["groups", "version"])
        self.assertEqual(doc["groups"], self.groups)
        self.assertGreaterEqual(len(self.groups), 40)

    def test_every_group_is_a_list_of_lower_case_terms(self):
        for name, terms in self.groups.items():
            self.assertIsInstance(terms, list, name)
            self.assertGreaterEqual(len(terms), 2, name)
            for term in terms:
                self.assertEqual(term, term.lower().strip(), term)
                self.assertTrue(find.tokens(term), term)

    def test_the_map_is_bilingual(self):
        for name in ("deposit", "break_clause", "damp", "move_out"):
            terms = self.groups[name]
            self.assertTrue(any(ord(ch) > 0x2E00 for t in terms for ch in t), name)
            self.assertTrue(any(all(ord(ch) < 0x2E00 for ch in t) for t in terms), name)


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.groups = find.load_synonyms(SYNONYMS)

    def test_break_clause_ranks_a_clause_headed_early_termination_first(self):
        code, out, err = run_cli(TENANCY, "--ask", "break clause", "--top", "3", "--context", "0")
        self.assertEqual(0, code, err)
        first = blocks(out)[0]
        self.assertIn("9. Early termination", first)
        self.assertNotIn("break clause", first.lower())

    def test_a_chinese_question_finds_an_english_clause(self):
        code, out, err = run_cli(TENANCY, "--ask", "押金", "--top", "2", "--context", "0")
        self.assertEqual(0, code, err)
        first = blocks(out)[0]
        self.assertIn("7. Deposit", first)
        self.assertIn("five weeks' rent", first)
        self.assertNotIn("押金", read(TENANCY))       # nothing Chinese in the document itself

    def test_a_synonym_never_outranks_a_literal_match_on_equal_evidence(self):
        literal = "The deposit is held by the agent as stakeholder for the tenant."
        synonym = "The 押金 is held by the agent as stakeholder for the tenant."
        units = find.index_text(literal + "\n\n" + synonym + "\n", "pair.txt")
        self.assertEqual(2, len(units))
        scored = sorted(find.rank(units, find.expand("deposit", self.groups)), reverse=True)
        self.assertEqual(2, len(scored))
        self.assertIn("deposit", units[scored[0][1]]["text"])
        self.assertGreater(scored[0][0], scored[1][0])

    def test_windowing_finds_a_term_inside_a_five_thousand_character_clause(self):
        clause = [e - s for s, e in find.paragraphs(read(TENANCY)) if e - s > 1200]
        self.assertEqual(1, len(clause))
        self.assertGreater(clause[0], 5000)
        code, got, err = hits_json(TENANCY, "--ask", "trampoline")
        self.assertEqual(0, code, err)
        self.assertIn("trampoline", got[0]["text"])
        self.assertLessEqual(got[0]["end"] - got[0]["start"], 800)

    def test_damp_reviews_from_people_who_moved_out_beat_the_five_star_burst(self):
        code, got, err = hits_json(REVIEWS, "--ask", "潮濕 發霉 move-out", "--top", "5",
                                   "--context", "0")
        self.assertEqual(0, code, err)
        for hit in got[:3]:
            self.assertTrue(any(w in hit["text"].lower() for w in
                                ("damp", "mould", "condensation", "潮濕", "發霉")), hit["text"])
        burst = [h for h in got if "4 February 2026" in h["text"]]
        self.assertEqual([], burst, "a same-day five-star review outranked a damp review")

    def test_a_forty_review_page_stays_under_a_thousand_characters_a_hit(self):
        code, got, err = hits_json(REVIEWS, "--ask", "damp mould", "--top", "8", "--context", "2")
        self.assertEqual(0, code, err)
        self.assertGreaterEqual(len(got), 5)
        for hit in got:
            self.assertLessEqual(len(hit["text"]), find.MAX_VIEW, hit["text"][:60])


class TestTheFixedForm(unittest.TestCase):
    def test_fixed_f1_finds_the_deposit_weeks_sentence(self):
        code, out, err = run_cli(TENANCY, "--fixed", "F1", "--top", "3", "--context", "0")
        self.assertEqual(0, code, err)
        self.assertIn("five weeks' rent", out)
        where = [n for n, b in enumerate(blocks(out)) if "five weeks' rent" in b]
        self.assertTrue(where and where[0] <= 1, "the deposit clause fell below rank 2")

    def test_fixed_hits_carry_the_question_id_in_matched_terms(self):
        code, got, err = hits_json(TENANCY, "--fixed", "F13", "--top", "2", "--context", "0")
        self.assertEqual(0, code, err)
        self.assertIn("F13", got[0]["matched_terms"])
        self.assertIn("Early termination", got[0]["text"])

    def test_an_unknown_fixed_id_is_a_usage_error(self):
        code, _out, err = run_cli(TENANCY, "--fixed", "F99")
        self.assertEqual(2, code)
        self.assertIn("F99", err)

    def test_ids_from_fixed_questions_runs_every_question(self):
        code, got, err = hits_json(LISTING, "--ids-from", "fixed-questions", "--top", "4",
                                   "--context", "0")
        self.assertEqual(0, code, err)
        self.assertTrue(got)
        self.assertTrue(any(t.startswith("F") and t[1:].isdigit()
                            for hit in got for t in hit["matched_terms"]))


class TestOutputShapes(unittest.TestCase):
    def test_the_default_block_is_rank_score_file_line_then_the_paragraph(self):
        code, out, err = run_cli(LISTING, "--ask", "heat network", "--context", "0")
        self.assertEqual(0, code, err)
        head, _sep, body = blocks(out)[0].partition("\n")
        self.assertRegex(head, r"^#1  \d+\.\d\d  .*listing\.txt:\d+$")
        self.assertIn("heat network", body)

    def test_all_is_grep_n_shaped(self):
        code, out, err = run_cli(REVIEWS, "--ask", "damp mould", "--all")
        self.assertEqual(0, code, err)
        lines = [line for line in out.splitlines() if line.strip()]
        self.assertGreater(len(lines), 5)
        for line in lines:
            path, _colon, rest = line.partition(":")
            self.assertTrue(path.endswith("resident-reviews.txt"), line)
            self.assertTrue(rest.split(":")[0].isdigit(), line)
            self.assertLessEqual(len(rest.split(":", 1)[1]), find.LINE_WIDTH + 1, line)

    def test_json_carries_the_documented_keys(self):
        code, got, err = hits_json(TENANCY, "--ask", "who holds the deposit", "--top", "2")
        self.assertEqual(0, code, err)
        self.assertEqual(2, len(got))
        for n, hit in enumerate(got, 1):
            self.assertEqual(sorted(hit), ["end", "file", "line", "matched_terms", "rank",
                                           "score", "start", "text"])
            self.assertEqual(n, hit["rank"])
            self.assertTrue(hit["file"].endswith("tenancy-agreement.txt"))
            self.assertGreater(hit["end"], hit["start"])
            self.assertIn("deposit", " ".join(hit["matched_terms"]))
        self.assertGreaterEqual(got[0]["score"], got[1]["score"])

    def test_the_line_number_points_at_the_paragraph_in_the_file(self):
        code, got, err = hits_json(TENANCY, "--ask", "council tax band", "--top", "1")
        self.assertEqual(0, code, err)
        lines = read(TENANCY).splitlines()
        self.assertIn("Council tax", lines[got[0]["line"] - 1])

    def test_the_footer_counts_units_files_and_milliseconds(self):
        code, _out, err = run_cli(FIXTURES, "--ask", "deposit", "--top", "1")
        self.assertEqual(0, code)
        self.assertRegex(err.strip(), r"^97 units, 4 files, \d+ hits, \d+ ms$")


class TestTheCorpus(unittest.TestCase):
    def test_the_four_fixtures_index_the_expected_unit_counts(self):
        for name, expected in sorted(EXPECTED_UNITS.items()):
            _files, units = find.index_files([os.path.join(FIXTURES, name)])
            self.assertEqual(expected, len(units), name)
        files, units = find.index_files([FIXTURES])
        self.assertEqual(4, len(files))
        self.assertEqual(sum(EXPECTED_UNITS.values()), len(units))

    def test_a_folder_and_a_file_list_give_the_same_corpus(self):
        by_folder = find.index_files([FIXTURES])[1]
        by_file = find.index_files([LISTING, PLANNING, REVIEWS, TENANCY])[1]
        self.assertEqual([u["text"] for u in by_folder], [u["text"] for u in by_file])


class TestTheCommandLine(unittest.TestCase):
    def test_no_hits_exits_one(self):
        code, out, err = run_cli(FIXTURES, "--ask", "zebra quokka")
        self.assertEqual(1, code)
        self.assertEqual("", out.strip())
        self.assertIn("0 hits", err)

    def test_a_question_with_nothing_to_search_is_a_usage_error(self):
        self.assertEqual(2, run_cli(FIXTURES)[0])
        self.assertEqual(2, run_cli("--ask", "deposit")[0])

    def test_selftest_passes(self):
        code, out, err = run_cli("--selftest")
        self.assertEqual(0, code, err)
        self.assertIn("selftest ok", out)

    def test_min_score_drops_the_weak_hits(self):
        code, loose, err = hits_json(TENANCY, "--ask", "deposit", "--top", "20")
        self.assertEqual(0, code, err)
        cutoff = loose[0]["score"] - 0.01
        code, tight, err = hits_json(TENANCY, "--ask", "deposit", "--top", "20",
                                     "--min-score", str(cutoff))
        self.assertEqual(0, code, err)
        self.assertEqual(1, len(tight))
        self.assertLess(len(tight), len(loose))


if __name__ == "__main__":
    unittest.main()
