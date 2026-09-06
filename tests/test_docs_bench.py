# -*- coding: utf-8 -*-
"""Offline tests for the document-reading ablation: bench/docs_bench.py and bench/docs_grade.py.

No network and no model. Every test reads tests/fixtures/docs_bench/, two cases built
from the finder fixtures with six questions each, two of them `absent` probes whose
answer is not in the document at all.

The grading rules are frozen, so each one is tested BOTH ways: the shape that should
pass and the shape that should fail. The forbidden regexes get a third test - that the
CORRECT answer never triggers one - run over every rule in every fixture, because a
forbidden rule that fires on the right answer would quietly turn a good run into a
fabrication count.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import collections
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
BED = os.path.join(HERE, "fixtures", "docs_bench")
SKILL = os.path.join(ROOT, "skills", "vet-flat")

sys.path.insert(0, BENCH)
import docs_bench  # noqa: E402
import docs_grade  # noqa: E402

CASES = ("A1", "V1")


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def load(case_id):
    return docs_bench.load_case(BED, case_id)


class quiet(object):
    """Swallow stdout and stderr. Several of these calls print a plan or a scorecard
    line; that is the tool doing its job, not the test reporting."""

    def __enter__(self):
        self.out, self.err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        return sys.stdout

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self.out, self.err
        return False


def correct_answer(question):
    """The answer a model that read the document properly would give, built from the gold.

    Used two ways: as the passing half of the rule tests, and as the thing every
    forbidden regex must NOT match.
    """
    gold = question["answer"]
    spans = question.get("spans") or []
    out = collections.OrderedDict([("qid", question["qid"]), ("how", "read")])
    if gold.get("absent"):
        out["status"] = "absent"
        out["text"] = "the document does not answer this"
        # When the gold names the sentence that proves the "no", the right answer quotes
        # it. When it does not, the right answer quotes nothing.
        out["quote"] = spans[0]["quote"] if spans else ""
        return out
    out["status"] = "found"
    for key in ("value", "unit", "text", "list"):
        if gold.get(key) is not None:
            out[key] = gold[key]
    if spans:
        out["quote"] = spans[0]["quote"]
        out["line_start"] = spans[0]["line_start"]
        out["line_end"] = spans[0]["line_end"]
    return out


class TestTheFixtures(unittest.TestCase):
    """The bed itself: shape, spans, and the promise that the questions are answerable."""

    def test_every_fixture_follows_the_gold_contract(self):
        for case_id in CASES:
            gold, doc = load(case_id)
            self.assertTrue(docs_grade.check_gold(gold))
            self.assertEqual(case_id, gold["id"])
            self.assertEqual(len(doc), gold["chars"])
            self.assertEqual(len(doc.splitlines()), gold["lines"])
            self.assertEqual(6, len(gold["questions"]), case_id)

    def test_each_case_carries_two_absent_probes(self):
        """An absent probe MAY name the sentence that proves the "no" - the pet clause
        with no money in it - and the bed carries one of each kind per case, so both
        paths through the grader are exercised."""
        for case_id in CASES:
            gold, _doc = load(case_id)
            absents = [q for q in gold["questions"] if q["answer"].get("absent")]
            self.assertEqual(2, len(absents), "%s: %s" % (case_id, [q["qid"] for q in absents]))
            for question in absents:
                self.assertTrue(question.get("note"), "an absent probe owes a note")
            with_span = [q for q in absents if q.get("spans")]
            self.assertEqual(1, len(with_span), "%s: exactly one absent probe with a gold "
                                                "span" % case_id)

    def test_every_gold_span_is_verbatim_and_unique_in_its_document(self):
        for case_id in CASES:
            gold, doc = load(case_id)
            lines = doc.splitlines()
            for question in gold["questions"]:
                for span in question["spans"]:
                    window = "\n".join(lines[span["line_start"] - 1:span["line_end"]])
                    self.assertIn(span["quote"], window,
                                  "%s %s: quote not inside its own line range"
                                  % (case_id, question["qid"]))
                    self.assertEqual(1, doc.count(span["quote"]),
                                     "%s %s: quote is not unique in the document"
                                     % (case_id, question["qid"]))

    def test_a_fixed_question_names_a_real_fixed_form_id(self):
        wording = docs_bench.glossary_wording()
        self.assertTrue(wording, "references/glossary.yaml gave no fixed-form wording")
        for case_id in CASES:
            gold, _doc = load(case_id)
            for question in gold["questions"]:
                if question["kind"] == "fixed":
                    self.assertIn(question["fixed_id"], wording, question["qid"])

    def test_the_correct_answer_never_trips_a_forbidden_rule(self):
        """Two-way test for every forbidden regex in the bed, not just a sample."""
        checked = 0
        for case_id in CASES:
            gold, doc = load(case_id)
            for question in gold["questions"]:
                rules = question.get("forbidden") or []
                self.assertTrue(rules, "%s %s has no forbidden rule" % (case_id,
                                                                        question["qid"]))
                hits = docs_grade.forbidden_hits(question, correct_answer(question))
                self.assertEqual([], hits,
                                 "%s %s: the CORRECT answer matches %s"
                                 % (case_id, question["qid"], hits))
                checked += len(rules)
        self.assertGreaterEqual(checked, 20)

    def test_the_correct_answers_grade_as_a_perfect_session(self):
        for case_id in CASES:
            gold, doc = load(case_id)
            answers = [correct_answer(q) for q in gold["questions"]]
            card = docs_grade.grade_session(gold, answers, doc)
            summary = card["summary"]
            self.assertEqual(1.0, summary["fact_recall"], case_id)
            self.assertEqual(1.0, summary["span_recall"], case_id)
            self.assertEqual(0, summary["fabrications"], case_id)
            self.assertEqual(0, summary["invented_quotes"], case_id)
            self.assertEqual(1.0, summary["absent_honesty"], case_id)


class TestSpanVerification(unittest.TestCase):
    """The two gold faults only the document can reveal. Both quietly corrupt a whole
    case's span score in every arm at once, so both are caught before a run starts."""

    def test_a_sound_fixture_reports_nothing(self):
        for case_id in CASES:
            gold, doc = load(case_id)
            self.assertEqual([], docs_grade.verify_spans(gold, doc), case_id)

    def test_a_quote_that_is_not_in_the_document_is_reported(self):
        gold, doc = load("A1")
        gold["questions"][0]["spans"][0]["quote"] = "The deposit is nine weeks' rent."
        problems = docs_grade.verify_spans(gold, doc)
        self.assertEqual(1, len(problems))
        self.assertIn("not findable", problems[0])

    def test_a_gold_span_at_the_wrong_lines_is_reported(self):
        """A gold built against an earlier copy of the document: every correct quote
        would score 0.5 'misplaced but real' and the case would read as universally
        half-missed."""
        gold, doc = load("A1")
        gold["questions"][0]["spans"][0]["line_start"] = 155
        gold["questions"][0]["spans"][0]["line_end"] = 155
        problems = docs_grade.verify_spans(gold, doc)
        self.assertEqual(1, len(problems))
        self.assertIn("gold says lines 155-155", problems[0])
        self.assertIn("55-55", problems[0])

    def test_loading_a_case_with_a_bad_span_refuses_before_a_token_is_spent(self):
        bed = tempfile.mkdtemp(prefix="docsbench-badbed-")
        try:
            folder = os.path.join(bed, "cases", "A1")
            os.makedirs(folder)
            shutil.copy(os.path.join(BED, "cases", "A1", "doc.txt"), folder)
            gold, _doc = load("A1")
            gold["questions"][0]["spans"][0]["line_start"] = 200
            gold["questions"][0]["spans"][0]["line_end"] = 200
            with io.open(os.path.join(folder, "gold.json"), "w", encoding="utf-8") as fh:
                fh.write(json.dumps(gold, ensure_ascii=False))
            with self.assertRaises(docs_grade.GoldError):
                docs_bench.load_case(bed, "A1")
            # ...but --check wants to see the whole bed, so it loads leniently.
            leniently, _doc = docs_bench.load_case(bed, "A1", strict=False)
            self.assertEqual("A1", leniently["id"])
            with quiet() as out:
                code = docs_bench.main(["--cases", bed, "--check"])
            self.assertEqual(1, code)
            self.assertIn("SPAN PROBLEM", out.getvalue())
        finally:
            shutil.rmtree(bed, ignore_errors=True)

    def test_check_on_a_sound_bed_says_ok_and_exits_zero(self):
        with quiet() as out:
            code = docs_bench.main(["--cases", BED, "--check"])
        self.assertEqual(0, code)
        text = out.getvalue()
        self.assertIn("A1", text)
        self.assertIn("V1", text)
        self.assertNotIn("SPAN PROBLEM", text)


class TestAbsentHonesty(unittest.TestCase):
    """Gold says the document is silent. Three answers, three different outcomes."""

    def setUp(self):
        self.gold, self.doc = load("A1")
        self.question = [q for q in self.gold["questions"] if q["qid"] == "A1-q5"][0]

    def card(self, given):
        return docs_grade.grade_question(self.question, given, self.doc)

    def test_saying_absent_passes(self):
        card = self.card({"qid": "A1-q5", "status": "absent", "how": "grep"})
        self.assertTrue(card["correct"])
        self.assertFalse(card["fabrication"])

    def test_answering_it_is_a_fabrication(self):
        card = self.card({"qid": "A1-q5", "status": "found",
                          "text": "yes, one bay is included at £120 per month", "how": "grep"})
        self.assertFalse(card["correct"])
        self.assertTrue(card["fabrication"])

    def test_saying_unknown_is_honest_but_not_a_pass(self):
        card = self.card({"qid": "A1-q5", "status": "unknown", "how": "grep"})
        self.assertFalse(card["correct"])
        self.assertFalse(card["fabrication"])
        self.assertTrue(card["unknown"])


class TestSpanScoring(unittest.TestCase):
    """1 in the right place, 0.5 misplaced but real, 0 invented."""

    def setUp(self):
        self.gold, self.doc = load("A1")
        self.question = [q for q in self.gold["questions"] if q["qid"] == "A1-q1"][0]

    def score(self, quote):
        return docs_grade.score_span(self.question, {"quote": quote}, self.doc)

    def test_a_quote_at_the_gold_span_scores_one(self):
        score, note = self.score("The deposit is £2,128.85, being five weeks' rent.")
        self.assertEqual(1.0, score, note)

    def test_a_quote_within_three_lines_of_the_gold_span_still_scores_one(self):
        score, note = self.score("The deposit is payable in cleared funds before the Term")
        self.assertEqual(1.0, score, note)

    def test_a_real_quote_from_elsewhere_scores_a_half(self):
        score, note = self.score("A holding deposit of £425.77, being one week's rent")
        self.assertEqual(0.5, score)
        self.assertIn("misplaced but real", note)

    def test_a_quote_that_is_not_in_the_document_scores_zero(self):
        score, note = self.score("The deposit is six weeks' rent, payable on completion.")
        self.assertEqual(0.0, score)
        self.assertIn("invented", note)

    def test_a_quote_across_a_wrapped_line_is_still_verbatim(self):
        """The document wraps at about 95 columns; a sentence quoted whole crosses it."""
        joined = ("On or after the sixth month of the Term either party may end this "
                  "agreement by giving not less than two months' written notice")
        self.assertNotIn(joined, self.doc)          # not verbatim character for character
        spots = docs_grade.find_quote(self.doc, joined)
        self.assertEqual([(76, 77)], spots)

    def test_a_two_word_quote_is_too_short_to_count(self):
        score, note = self.score("deposit")
        self.assertEqual(0.0, score)
        self.assertIn("too short", note)

    def test_an_invented_quote_is_flagged_on_the_card(self):
        card = docs_grade.grade_question(
            self.question, {"qid": "A1-q1", "status": "found", "value": 5, "unit": "weeks",
                            "quote": "The deposit shall be five weeks of the said rent."},
            self.doc)
        self.assertTrue(card["invented_quote"])
        self.assertTrue(card["correct"])            # right fact, invented evidence


class TestValueMatching(unittest.TestCase):
    def test_weeks_are_exact(self):
        answer = {"value": 5, "unit": "weeks"}
        self.assertTrue(docs_grade.match_value(answer, {"value": 5})[0])
        self.assertFalse(docs_grade.match_value(answer, {"value": 6})[0])

    def test_a_word_number_counts_as_the_digit(self):
        answer = {"value": 5, "unit": "weeks"}
        self.assertTrue(docs_grade.match_value(answer, {"text": "five weeks' rent"})[0])
        self.assertFalse(docs_grade.match_value(answer, {"text": "one week's rent"})[0])

    def test_money_carries_a_penny_of_tolerance(self):
        answer = {"value": 2128.85, "unit": "GBP"}
        self.assertTrue(docs_grade.match_value(answer, {"value": 2128.85})[0])
        self.assertTrue(docs_grade.match_value(answer, {"value": 2128.86})[0])
        self.assertTrue(docs_grade.match_value(answer, {"text": "£2,128.85"})[0])
        self.assertFalse(docs_grade.match_value(answer, {"value": 2200})[0])

    def test_area_carries_two_per_cent(self):
        answer = {"value": 48, "unit": "m2"}
        self.assertTrue(docs_grade.match_value(answer, {"value": 48.5})[0])
        self.assertFalse(docs_grade.match_value(answer, {"value": 51})[0])

    def test_a_letter_compares_as_a_word(self):
        answer = {"value": "C", "unit": None}
        self.assertTrue(docs_grade.match_value(answer, {"value": "c"})[0])
        self.assertTrue(docs_grade.match_value(answer, {"text": "band C"})[0])
        self.assertFalse(docs_grade.match_value(answer, {"value": "B"})[0])


class TestTextAndListMatching(unittest.TestCase):
    def test_containment_works_both_ways(self):
        answer = {"text": "licence"}
        self.assertTrue(docs_grade.match_text(answer, {"text": "a licence to occupy"})[0])
        self.assertTrue(docs_grade.match_text(answer, {"text": "Licence"})[0])
        self.assertFalse(docs_grade.match_text(answer, {"text": "an assured shorthold "
                                                                "tenancy"})[0])

    def test_must_contain_is_stricter_than_containment(self):
        answer = {"text": "two months' written notice, on or after the sixth month",
                  "must_contain": ["two months", "sixth month"]}
        self.assertTrue(docs_grade.match_text(
            answer, {"text": "not less than two months' written notice, and only on or "
                             "after the sixth month of the Term"})[0])
        ok, why = docs_grade.match_text(answer, {"text": "two months' written notice"})
        self.assertFalse(ok)
        self.assertIn("sixth month", why)

    def test_a_list_needs_every_value_the_gold_states(self):
        answer = {"list": ["Chloe D.", "Danny K.", "Katya B."]}
        ok, _why, recall = docs_grade.match_list(
            answer, {"list": ["Chloe D.", "Danny K.", "Katya B."]})
        self.assertTrue(ok)
        self.assertEqual(1.0, recall)
        ok, why, recall = docs_grade.match_list(answer, {"list": ["Chloe D.", "Danny K."]})
        self.assertFalse(ok)
        self.assertIn("missing", why)
        self.assertAlmostEqual(2 / 3.0, recall, places=3)

    def test_a_list_answered_as_one_sentence_still_counts(self):
        """The failure that scored a right answer wrong: the gold is structured and the
        model wrote a sentence."""
        answer = {"list": [{"from": "23:00"}, {"to": "07:00"}]}
        ok, why, _recall = docs_grade.match_list(
            answer, {"text": "Quiet hours are 23:00 to 07:00."})
        self.assertTrue(ok, why)
        ok, why, _recall = docs_grade.match_list(
            answer, {"text": "Quiet hours are 22:00 to 07:00."})
        self.assertFalse(ok, why)

    def test_an_extra_item_is_reported_but_left_to_the_forbidden_rules(self):
        """Naming a fourth incentivised reviewer is an invention, and inventions are what
        that question's forbidden regexes are for. The list rule only reports it."""
        answer = {"list": ["Chloe D.", "Danny K.", "Katya B."]}
        ok, why, _recall = docs_grade.match_list(
            answer, {"list": ["Chloe D.", "Danny K.", "Katya B.", "Owen S."]})
        self.assertTrue(ok)
        self.assertIn("not in the gold", why)
        gold, _doc = load("V1")
        question = [q for q in gold["questions"] if q["qid"] == "V1-q1"][0]
        self.assertTrue(docs_grade.forbidden_hits(
            question, {"status": "found",
                       "list": ["Chloe D.", "Danny K.", "Katya B.", "Owen S."]}))

    def test_a_paraphrase_of_a_prose_gold_is_not_marked_wrong(self):
        """The bug this rule change fixed: whole-sentence containment scored 2/14 on a
        case where twelve answers were substantively right."""
        answer = {"text": "A licence. Clause 1.1 says the Agreement is a licence to "
                          "occupy and does not create a tenancy."}
        ok, why = docs_grade.match_text(
            answer, {"text": "This Agreement is a licence, not a tenancy."})
        self.assertTrue(ok, why)
        ok, why = docs_grade.match_text(
            answer, {"text": "It is an assured shorthold tenancy."})
        self.assertFalse(ok, why)

    def test_a_number_the_gold_states_is_compulsory_and_a_wrong_one_fails(self):
        answer = {"text": "A damage deposit of £303.50, being half of one week's fee."}
        ok, _why = docs_grade.match_text(
            answer, {"text": "The damage deposit is 303.50 pounds, half a week's fee."})
        self.assertTrue(ok)
        ok, why = docs_grade.match_text(
            answer, {"text": "A damage deposit of half a week's fee."})
        self.assertFalse(ok, why)
        self.assertIn("missing '303.5'", why)
        ok, why = docs_grade.match_text(
            answer, {"text": "The damage deposit is £430.50, half a week's fee."})
        self.assertFalse(ok, why)

    def test_a_clause_citation_in_the_gold_is_never_a_key(self):
        """Clause numbers say where the answer is; the span and quote rules check that."""
        facts, terms = docs_grade.derive_keys(
            {"text": "A licence. Clause 1.1 and clause 8.3 say so.",
             "list": [{"clauses": ["1.1", "8.3"]}]})
        self.assertEqual([], facts)
        self.assertIn("licence", terms)

    def test_explicit_keys_on_the_gold_are_all_required(self):
        question = {"keys": ["licence", "tenancy"]}
        answer = {"text": "anything at all"}
        ok, _why = docs_grade.match_text(
            answer, {"text": "a licence, not a tenancy"}, question)
        self.assertTrue(ok)
        ok, why = docs_grade.match_text(answer, {"text": "a licence"}, question)
        self.assertFalse(ok)
        self.assertIn("keys from the gold", why)
        self.assertIn("missing 'tenancy'", why)


class TestForbiddenRules(unittest.TestCase):
    """The other half of test_the_correct_answer_never_trips_a_forbidden_rule."""

    def test_the_wrong_answer_trips_the_rule_it_was_written_for(self):
        gold, _doc = load("A1")
        wrong = {
            "A1-q1": {"status": "found", "value": 1, "unit": "week"},
            "A1-q2": {"status": "found", "text": "an assured shorthold tenancy"},
            "A1-q3": {"status": "found", "text": "one month's written notice"},
            "A1-q4": {"status": "found", "value": "B"},
            "A1-q5": {"status": "found", "text": "yes, £150 per month"},
            "A1-q6": {"status": "found", "text": "£50 per month pet rent"},
        }
        for question in gold["questions"]:
            hits = docs_grade.forbidden_hits(question, wrong[question["qid"]])
            self.assertTrue(hits, "%s: the wrong answer tripped nothing" % question["qid"])

    def test_a_forbidden_hit_only_counts_when_the_model_claims_it_found_something(self):
        gold, doc = load("V1")
        question = [q for q in gold["questions"] if q["qid"] == "V1-q4"][0]
        claimed = docs_grade.grade_question(
            question, {"qid": "V1-q4", "status": "found", "value": 78, "unit": "percent",
                       "quote": "it read seventy eight per cent in December"}, doc)
        self.assertTrue(claimed["fabrication"])
        withheld = docs_grade.grade_question(
            question, {"qid": "V1-q4", "status": "unknown", "value": 78}, doc)
        self.assertFalse(withheld["fabrication"])

    def test_a_bad_regex_in_a_gold_file_is_an_error_not_a_silent_pass(self):
        question = {"qid": "X-q1", "forbidden": ["(unclosed"]}
        with self.assertRaises(docs_grade.GoldError):
            docs_grade.forbidden_hits(question, {"status": "found", "text": "anything"})


class TestGoldValidation(unittest.TestCase):
    def base(self):
        gold, _doc = load("A1")
        return json.loads(json.dumps(gold), object_pairs_hook=collections.OrderedDict)

    def test_a_repeated_qid_is_rejected(self):
        gold = self.base()
        gold["questions"].append(gold["questions"][0])
        with self.assertRaises(docs_grade.GoldError):
            docs_grade.check_gold(gold)

    def test_an_absent_answer_may_carry_the_span_that_proves_the_no(self):
        gold, doc = load("A1")
        self.assertTrue(docs_grade.check_gold(gold))
        question = [q for q in gold["questions"] if q["qid"] == "A1-q6"][0]
        self.assertTrue(question["spans"])
        quoted = docs_grade.grade_question(
            question, {"qid": "A1-q6", "status": "absent",
                       "quote": question["spans"][0]["quote"], "how": "grep"}, doc)
        self.assertTrue(quoted["correct"])
        self.assertEqual(1.0, quoted["span_score"])
        silent = docs_grade.grade_question(
            question, {"qid": "A1-q6", "status": "absent", "how": "grep"}, doc)
        self.assertTrue(silent["correct"])
        self.assertEqual(0.0, silent["span_score"])

    def test_an_absent_answer_with_no_gold_span_earns_no_span_score(self):
        """A1-q5 has no sentence that proves the no, so quoting the nearest thing is
        honest but scores nothing - and it is left out of span_recall entirely."""
        gold, doc = load("A1")
        question = [q for q in gold["questions"] if q["qid"] == "A1-q5"][0]
        self.assertEqual([], question["spans"])
        card = docs_grade.grade_question(
            question, {"qid": "A1-q5", "status": "absent", "how": "grep",
                       "quote": "The Tenant does not park a car, a van or a motorcycle "
                                "in a bay allotted to another flat."}, doc)
        self.assertTrue(card["correct"])
        self.assertEqual(0.0, card["span_score"])
        self.assertFalse(card["invented_quote"])
        self.assertFalse(card["has_gold_span"])

    def test_a_present_answer_needs_a_span(self):
        gold = self.base()
        gold["questions"][0]["spans"] = []
        with self.assertRaises(docs_grade.GoldError):
            docs_grade.check_gold(gold)

    def test_a_fixed_question_needs_a_fixed_id(self):
        gold = self.base()
        gold["questions"][0]["fixed_id"] = None
        with self.assertRaises(docs_grade.GoldError):
            docs_grade.check_gold(gold)


class TestTheSessionScorecard(unittest.TestCase):
    def test_a_session_of_wrong_answers_scores_what_it_should(self):
        gold, doc = load("A1")
        answers = [
            {"qid": "A1-q1", "status": "found", "value": 1, "unit": "week",
             "quote": "A holding deposit of £425.77, being one week's rent", "how": "grep"},
            {"qid": "A1-q2", "status": "found", "text": "an assured shorthold tenancy",
             "quote": "ASSURED SHORTHOLD TENANCY AGREEMENT", "how": "read"},
            {"qid": "A1-q3", "status": "unknown", "how": "read"},
            {"qid": "A1-q4", "status": "found", "value": "B",
             "quote": "The certificate shows a rating of B for the flat", "how": "read"},
            {"qid": "A1-q5", "status": "found", "text": "yes, £120 per month", "how": "grep"},
            {"qid": "A1-q6", "status": "unknown", "how": "grep"},
        ]
        summary = docs_grade.grade_session(gold, answers, doc)["summary"]
        self.assertEqual(0.0, summary["fact_recall"])
        self.assertEqual(4, summary["fabrications"])
        self.assertEqual(1, summary["invented_quotes"])
        self.assertEqual(2, summary["unknowns"])
        self.assertEqual(0.0, summary["absent_honesty"])
        # Five questions carry a gold span (four present, plus the absent A1-q6): two
        # misplaced-but-real quotes make 1.0 out of 5.
        self.assertEqual(0.2, summary["span_recall"])

    def test_a_session_with_no_answers_is_not_graded_as_a_row_of_zeros(self):
        """A failed launch is not a model that scored zero, and averaging it as one
        turned an arm that scored 0.70 into an arm that read 0.16."""
        gold, doc = load("V1")
        card = docs_grade.grade_session(gold, [], doc)
        self.assertIsNone(card["summary"])
        self.assertFalse(card["valid"])
        self.assertIn("no answers array", card["invalid_reason"])
        self.assertEqual([], card["questions_graded"])

    def test_a_question_the_model_skipped_inside_a_real_session_is_missing(self):
        gold, doc = load("V1")
        card = docs_grade.grade_session(
            gold, [{"qid": "V1-q6", "status": "absent", "how": "grep"}], doc)
        self.assertTrue(card["valid"])
        self.assertEqual(6, card["summary"]["questions"])
        self.assertEqual(1, card["summary"]["answered"])
        self.assertEqual(0, card["summary"]["fabrications"])
        self.assertEqual(5, len([c for c in card["questions_graded"]
                                 if c["status"] == "missing"]))

    def test_the_menu_probe_lands_on_the_card_when_it_is_supplied(self):
        gold, doc = load("V1")
        menu = {"V1-q1": True, "V1-q2": False}
        answers = [{"qid": "V1-q1", "status": "unknown", "how": "find"}]
        summary = docs_grade.grade_session(gold, answers, doc, menu)["summary"]
        self.assertEqual(0.5, summary["menu_recall@5"])


class TestTheMenuProbe(unittest.TestCase):
    """The zero-token probe: find.py asked the same questions the model is asked."""

    def test_find_py_surfaces_most_gold_spans_in_its_top_five(self):
        hits, total = 0, 0
        for case_id in CASES:
            gold, doc = load(case_id)
            menu = docs_bench.menu_probe(gold, doc)
            # Only the questions the document does answer have a span to hit.
            expected = [q["qid"] for q in gold["questions"] if q["spans"]]
            self.assertEqual(sorted(expected), sorted(menu))
            total += len(menu)
            hits += len([v for v in menu.values() if v])
        self.assertEqual(10, total)
        self.assertGreaterEqual(hits, 7, "the ranker surfaced fewer spans than expected")

    def test_a_question_the_ranker_cannot_reach_is_recorded_as_a_miss(self):
        """V1-q3 asks in English about a review written in Chinese. The probe says so,
        which is the whole point of separating the menu from the model."""
        gold, doc = load("V1")
        menu = docs_bench.menu_probe(gold, doc)
        self.assertIn("V1-q3", menu)
        self.assertIsInstance(menu["V1-q3"], bool)

    def test_the_probe_skips_a_question_with_no_gold_span_to_hit(self):
        """A1-q5 has no sentence that proves the no, so there is nothing for the ranker
        to surface and nothing to score it on. A1-q6 has one, so it is probed."""
        gold, doc = load("A1")
        menu = docs_bench.menu_probe(gold, doc)
        self.assertNotIn("A1-q5", menu)
        self.assertIn("A1-q6", menu)


class TestTheArms(unittest.TestCase):
    def test_each_arm_names_the_tools_the_ablation_defines(self):
        self.assertEqual("Read", docs_bench.ARMS["R0"]["tools"])
        self.assertEqual("Read,Bash(grep:*),Bash(rg:*)", docs_bench.ARMS["R1"]["tools"])
        self.assertEqual(
            "Read,Bash(python3 .claude/skills/vet-flat/scripts/find.py:*),"
            "Bash(python3 .claude/skills/vet-flat/scripts/reviews.py:*),"
            "Bash(grep:*),Bash(rg:*)", docs_bench.ARMS["R2"]["tools"])
        self.assertEqual("Read,Bash(python3 .claude/skills/vet-flat/scripts/scan.py:*)",
                         docs_bench.ARMS["R3"]["tools"])

    def test_r3_asks_only_the_fixed_questions(self):
        gold, _doc = load("A1")
        self.assertEqual(["A1-q1", "A1-q2", "A1-q4"],
                         [q["qid"] for q in docs_bench.questions_for(gold, "R3")])
        for arm in ("R0", "R1", "R2"):
            self.assertEqual(6, len(docs_bench.questions_for(gold, arm)), arm)

    def test_a_case_with_no_fixed_question_is_skipped_by_r3_not_run_empty(self):
        gold, _doc = load("V1")
        self.assertEqual([], docs_bench.questions_for(gold, "R3"))
        args = docs_bench.build_parser().parse_args(
            ["--cases", BED, "--case", "V1", "--arm", "R3", "--dry-run"])
        with quiet() as out:
            record, problem = docs_bench.run_row(
                {"arm": "R3", "agent": "claude", "model": "sonnet", "tier": "cheap",
                 "case": "V1", "run": 1}, BED, args, {})
        self.assertIsNone(record)
        self.assertIsNone(problem, "an empty R3 row is expected, not a failure")
        self.assertIn("no question this arm can ask", out.getvalue())

    def test_a_matrix_dry_run_over_a_free_only_case_still_exits_zero(self):
        with quiet() as out:
            code = docs_bench.main(["--cases", BED, "--matrix", "--case", "V1",
                                    "--dry-run"])
        text = out.getvalue()
        self.assertEqual(0, code, text)
        # 4 arms x 5 models = 20 planned; the five R3 rows have nothing to ask a
        # free-question-only case and are skipped rather than run empty.
        self.assertEqual(15, text.count("write doc.txt"))
        self.assertEqual(5, text.count("no question this arm can ask"))

    def test_only_r2_and_r3_get_the_skill_copied_in(self):
        self.assertFalse(docs_bench.ARMS["R0"]["needs_skill"])
        self.assertFalse(docs_bench.ARMS["R1"]["needs_skill"])
        self.assertTrue(docs_bench.ARMS["R2"]["needs_skill"])
        self.assertTrue(docs_bench.ARMS["R3"]["needs_skill"])

    def test_the_skill_folder_is_pinned_by_the_environment_when_it_is_set(self):
        before = os.environ.get("VETFLAT_SKILL_DIR")
        try:
            os.environ["VETFLAT_SKILL_DIR"] = "/somewhere/else/vet-flat"
            self.assertEqual("/somewhere/else/vet-flat", docs_bench.skill_dir())
        finally:
            if before is None:
                os.environ.pop("VETFLAT_SKILL_DIR", None)
            else:
                os.environ["VETFLAT_SKILL_DIR"] = before
        self.assertEqual(SKILL, docs_bench.skill_dir())


class TestTheCommands(unittest.TestCase):
    """What the runner would launch. Nothing here starts a process."""

    def dry_run(self, argv):
        with quiet() as out:
            code = docs_bench.main(argv + ["--cases", BED, "--dry-run"])
        return code, out.getvalue()

    def test_the_dry_run_prints_the_arms_allowed_tools_and_no_bypass_flag(self):
        for arm in docs_bench.ARM_IDS:
            case = "A1"
            code, text = self.dry_run(["--arm", arm, "--agent", "claude",
                                       "--model", "sonnet", "--case", case])
            self.assertEqual(0, code, text)
            self.assertIn("--allowedTools", text)
            self.assertIn(docs_bench.ARMS[arm]["tools"], text)
            for flag in ("--dangerously-skip-permissions", "--permission-mode",
                         "bypassPermissions", "--dangerously-bypass"):
                self.assertNotIn(flag, text, "%s: %s in the command" % (arm, flag))

    def test_a_claude_command_carries_no_permission_bypass_anywhere_in_the_source(self):
        source = read(os.path.join(BENCH, "docs_bench.py"))
        for flag in ("--dangerously-skip-permissions", "bypassPermissions",
                     "--dangerously-bypass-approvals-and-sandbox",
                     "acceptEdits", "danger-full-access"):
            self.assertNotIn(flag, source, flag)

    def test_a_codex_command_is_read_only_and_asks_for_the_event_stream(self):
        cmd = docs_bench.codex_command("prompt", "/tmp/wd", "gpt-5.6-luna", "/tmp/wd/last.txt")
        self.assertEqual("codex", cmd[0])
        self.assertIn("--sandbox", cmd)
        self.assertEqual("read-only", cmd[cmd.index("--sandbox") + 1])
        self.assertIn("--json", cmd)
        self.assertNotIn("--allowedTools", cmd)
        self.assertEqual("prompt", cmd[-1])

    def test_the_prompt_names_the_skill_path_each_agent_will_actually_see(self):
        self.assertIn(".claude/skills/vet-flat/scripts/find.py",
                      docs_bench.discipline_text("R2", "claude"))
        self.assertIn(".agents/skills/vet-flat/scripts/find.py",
                      docs_bench.discipline_text("R2", "codex"))

    def test_codex_is_told_how_to_read_because_it_has_no_read_tool(self):
        for arm in docs_bench.ARM_IDS:
            text = docs_bench.discipline_text(arm, "codex")
            self.assertIn("read-only shell", text, arm)
            self.assertIn("sed -n", text, arm)

    def test_the_prompt_carries_the_glossary_wording_for_a_fixed_question(self):
        gold, doc = load("A1")
        wording = docs_bench.glossary_wording()
        prompt = docs_bench.build_prompt(gold, doc, "R1", "claude", gold["questions"],
                                         wording)
        self.assertIn("A1-q1 [fixed form F1]  %s" % wording["F1"], prompt)
        self.assertIn("answers array", prompt)
        self.assertIn('"how": "grep"', prompt)

    def test_the_prompt_can_be_asked_in_chinese(self):
        gold, doc = load("V1")
        prompt = docs_bench.build_prompt(gold, doc, "R1", "claude", gold["questions"],
                                         {}, lang="zh")
        self.assertIn("押金到底多少錢", prompt)


class TestDisciplineEnforcementAndAudit(unittest.TestCase):
    def test_a_claude_row_is_enforced_and_a_codex_row_is_only_audited(self):
        folder = tempfile.mkdtemp(prefix="docsbench-rows-")
        try:
            args = docs_bench.build_parser().parse_args(
                ["--cases", BED, "--case", "A1", "--dry-run", "--arm", "R1"])
            rows = []
            for agent, model in (("claude", "sonnet"), ("codex", "gpt-5.6-luna")):
                args.agent, args.model = agent, model
                with quiet():
                    record, problem = docs_bench.run_row(
                        {"arm": "R1", "agent": agent, "model": model, "tier": "cheap",
                         "case": "A1", "run": 1}, BED, args, {})
                self.assertIsNone(problem)
                rows.append(record)
            self.assertTrue(rows[0]["discipline_enforced"])
            self.assertEqual("Read,Bash(grep:*),Bash(rg:*)", rows[0]["allowed_tools"])
            self.assertIsNone(rows[0]["sandbox"])
            self.assertFalse(rows[1]["discipline_enforced"])
            self.assertIsNone(rows[1]["allowed_tools"])
            self.assertEqual("read-only", rows[1]["sandbox"])
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_commands_are_classified_by_what_kind_of_reading_they_are(self):
        self.assertEqual("find", docs_bench.classify_command(
            "python3 .agents/skills/vet-flat/scripts/find.py doc.txt --ask 'deposit'"))
        self.assertEqual("scan", docs_bench.classify_command(
            "python3 .agents/skills/vet-flat/scripts/scan.py doc.txt --table"))
        self.assertEqual("grep", docs_bench.classify_command("grep -n deposit doc.txt"))
        self.assertEqual("grep", docs_bench.classify_command("rg -n 'break clause' doc.txt"))
        self.assertEqual("read_range", docs_bench.classify_command("sed -n '50,60p' doc.txt"))
        self.assertEqual("read_full", docs_bench.classify_command("cat doc.txt"))
        self.assertEqual("inspect", docs_bench.classify_command("ls -la"))
        self.assertEqual("python", docs_bench.classify_command("python3 -c 'print(1)'"))
        self.assertEqual("other", docs_bench.classify_command("curl https://example.com"))

    def test_the_review_parser_is_an_r2_tool_and_nobody_elses(self):
        """reviews.py is named in the R2 allow-list whether or not the script has landed:
        a tool pattern is only a string, so the dry-run works either way."""
        self.assertIn("reviews.py", docs_bench.ARMS["R2"]["tools"])
        self.assertIn("reviews", docs_bench.ARMS["R2"]["shell"])
        for arm in ("R0", "R1", "R3"):
            self.assertNotIn("reviews.py", docs_bench.ARMS[arm]["tools"], arm)
            self.assertNotIn("reviews", docs_bench.ARMS[arm]["shell"], arm)
        self.assertEqual("reviews", docs_bench.classify_command(
            "python3 .claude/skills/vet-flat/scripts/reviews.py doc.txt --json"))
        used = ["python3 x/reviews.py doc.txt"]
        counts, violations = docs_bench.audit_commands("R2", used)
        self.assertEqual({"reviews": 1}, dict(counts))
        self.assertEqual([], violations)
        _counts, violations = docs_bench.audit_commands("R1", used)
        self.assertEqual(["reviews"], [v["kind"] for v in violations])

    def test_the_r2_prompt_names_the_review_parser_and_says_to_check_it_exists(self):
        text = docs_bench.discipline_text("R2", "claude")
        self.assertIn(".claude/skills/vet-flat/scripts/reviews.py", text)
        self.assertIn("Check it is there", text)
        self.assertIn(".agents/skills/vet-flat/scripts/reviews.py",
                      docs_bench.discipline_text("R2", "codex"))

    def test_a_dry_run_works_whether_or_not_the_review_parser_exists_yet(self):
        args = docs_bench.build_parser().parse_args(
            ["--cases", BED, "--case", "V1", "--arm", "R2", "--dry-run"])
        with quiet() as out:
            record, problem = docs_bench.run_row(
                {"arm": "R2", "agent": "claude", "model": "sonnet", "tier": "cheap",
                 "case": "V1", "run": 1}, BED, args, {})
        self.assertIsNone(problem)
        self.assertIn("reviews.py", out.getvalue())
        self.assertEqual(os.path.exists(os.path.join(SKILL, "scripts", "reviews.py")),
                         record["reviews_py_present"])

    def test_the_audit_counts_kinds_and_names_what_the_arm_forbids(self):
        used = ["grep -n deposit doc.txt", "sed -n '50,60p' doc.txt", "cat doc.txt"]
        counts, violations = docs_bench.audit_commands("R1", used)
        self.assertEqual({"grep": 1, "read_range": 1, "read_full": 1}, dict(counts))
        self.assertEqual(["read_full"], [v["kind"] for v in violations])
        # R0 is the full read, so cat is the arm rather than a breach of it - but grep is.
        _counts, violations = docs_bench.audit_commands("R0", used)
        self.assertEqual(["grep"], [v["kind"] for v in violations])
        # R3 has no grep and no find.
        _counts, violations = docs_bench.audit_commands(
            "R3", ["python3 x/find.py doc.txt --ask q", "python3 x/scan.py doc.txt"])
        self.assertEqual(["find"], [v["kind"] for v in violations])

    def test_the_codex_event_stream_gives_up_its_commands(self):
        stream = "\n".join([
            "Reading prompt from argv",
            json.dumps({"type": "item.started", "item": {"type": "command_execution",
                                                         "command": "grep -n deposit doc.txt"}}),
            "not json at all",
            json.dumps({"msg": {"type": "exec_command_begin",
                                "command": ["sed", "-n", "50,60p", "doc.txt"]}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10}}),
        ])
        commands = docs_bench.commands_from_events(stream)
        self.assertEqual(["grep -n deposit doc.txt", "sed -n 50,60p doc.txt"], commands)
        counts, violations = docs_bench.audit_commands("R1", commands)
        self.assertEqual({"grep": 1, "read_range": 1}, dict(counts))
        self.assertEqual([], violations)

    def test_an_event_stream_with_no_commands_reports_none(self):
        self.assertEqual([], docs_bench.commands_from_events(""))
        self.assertEqual([], docs_bench.commands_from_events("no json here\n"))


class TestReadingTheReply(unittest.TestCase):
    def test_a_fenced_block_is_taken_even_with_prose_after_it(self):
        reply = ("Here is what I found.\n\n```json\n"
                 '[{"qid": "A1-q1", "status": "found", "value": 5}]\n```\n\nHope that helps.')
        answers, note = docs_bench.parse_answers(reply)
        self.assertEqual([{"qid": "A1-q1", "status": "found", "value": 5}], answers)
        self.assertIsNone(note)

    def test_the_last_fenced_block_wins(self):
        reply = ('```json\n[{"qid": "x"}]\n```\nOn reflection:\n```json\n[{"qid": "y"}]\n```')
        answers, _note = docs_bench.parse_answers(reply)
        self.assertEqual([{"qid": "y"}], answers)

    def test_a_bare_array_is_still_graded_and_says_so(self):
        answers, note = docs_bench.parse_answers('Answer:\n[{"qid": "A1-q1", "status": "absent"}]')
        self.assertEqual([{"qid": "A1-q1", "status": "absent"}], answers)
        self.assertIn("no fenced block", note)

    def test_a_reply_with_no_array_is_an_empty_session_not_a_crash(self):
        answers, note = docs_bench.parse_answers("I could not read the document.")
        self.assertEqual([], answers)
        self.assertIn("no answers array", note)


class TestTheMatrix(unittest.TestCase):
    def test_the_matrix_expands_four_arms_by_five_models(self):
        combos = docs_bench.matrix_combos(
            os.path.join(ROOT, "bench", "ab", "configs", "docs", "docs-matrix.yaml"))
        self.assertEqual(20, len(combos))
        self.assertEqual(set(docs_bench.ARM_IDS), set(arm for arm, _a, _m, _t in combos))
        self.assertEqual({("claude", "sonnet", "cheap"), ("claude", "opus", "strong"),
                          ("codex", "gpt-5.6-luna", "cheap"),
                          ("codex", "gpt-5.6-terra", "middle"),
                          ("codex", "gpt-5.6-sol", "strong")},
                         set((a, m, t) for _arm, a, m, t in combos))

    def test_the_pilot_config_is_two_rows(self):
        combos = docs_bench.matrix_combos(
            os.path.join(ROOT, "bench", "ab", "configs", "docs", "docs-pilot.yaml"))
        self.assertEqual([("R1", "claude", "sonnet", "cheap"),
                          ("R2", "claude", "sonnet", "cheap")], combos)

    def test_a_model_may_sit_an_arm_out(self):
        config = ("arms:\n  - R1\n  - R3\nmodels:\n  - agent: claude\n    model: sonnet\n"
                  "    tier: cheap\n    skip_arms:\n      - R3\n")
        path = os.path.join(tempfile.mkdtemp(prefix="docsbench-cfg-"), "docs-x.yaml")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(config)
        self.assertEqual([("R1", "claude", "sonnet", "cheap")],
                         docs_bench.matrix_combos(path))

    def test_an_unknown_arm_in_a_config_is_an_error(self):
        path = os.path.join(tempfile.mkdtemp(prefix="docsbench-cfg-"), "docs-bad.yaml")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write("arms:\n  - R9\nmodels:\n  - agent: claude\n    model: sonnet\n")
        with self.assertRaises(docs_bench.ConfigError):
            docs_bench.matrix_combos(path)

    def test_the_dry_run_of_the_matrix_plans_every_row(self):
        with quiet() as out:
            code = docs_bench.main(["--cases", BED, "--matrix", "--case", "A1", "--dry-run"])
        self.assertEqual(0, code)
        text = out.getvalue()
        self.assertIn("planning 20 row(s)", text)
        self.assertEqual(20, text.count("\n  docs-"))


class TestTheYamlSubset(unittest.TestCase):
    def test_maps_lists_of_scalars_lists_of_maps_and_block_scalars(self):
        doc = docs_bench.parse_yaml(
            "# a comment\n"
            "name: docs-x\n"
            "count: 3\n"
            "flag: true\n"
            "empty: null\n"
            "arms:\n  - R0\n  - R1\n"
            "models:\n"
            "  - agent: claude\n    model: sonnet\n"
            "  - agent: codex\n    model: gpt-5.6-sol\n"
            "notes: |\n  first line\n  second line\n"
            "after: yes\n")
        self.assertEqual("docs-x", doc["name"])
        self.assertEqual(3, doc["count"])
        self.assertIs(True, doc["flag"])
        self.assertIsNone(doc["empty"])
        self.assertEqual(["R0", "R1"], doc["arms"])
        self.assertEqual([{"agent": "claude", "model": "sonnet"},
                          {"agent": "codex", "model": "gpt-5.6-sol"}], doc["models"])
        self.assertEqual("first line\nsecond line\n", doc["notes"])
        self.assertEqual("yes", doc["after"])

    def test_an_odd_indent_is_refused(self):
        with self.assertRaises(docs_bench.ConfigError):
            docs_bench.parse_yaml("a:\n   b: 1\n")


class TestResultsAndRegrade(unittest.TestCase):
    def record(self, answers, arm="R1"):
        gold, doc = load("A1")
        grade = docs_grade.grade_session(gold, answers, doc)
        valid = grade.get("valid", True)
        return collections.OrderedDict([
            ("row", docs_bench.row_name(arm, "claude", "sonnet", "A1", 1)),
            ("bench", "reading-ablation"), ("arm", arm),
            ("arm_label", docs_bench.ARMS[arm]["label"]),
            ("agent", "claude"), ("model", "sonnet"), ("tier", "cheap"),
            ("case", "A1"), ("case_type", "agreement"),
            ("doc_chars", len(doc)), ("doc_lines", len(doc.splitlines())),
            ("questions_asked", [q["qid"] for q in gold["questions"]]),
            ("run", 1), ("run_at", "2026-09-06T00:00:00Z"),
            ("allowed_tools", docs_bench.ARMS[arm]["tools"]), ("sandbox", None),
            ("discipline_enforced", True), ("wall_time_s", 12.5),
            ("usage", {"total_tokens": 4242}), ("total_tokens", 4242),
            ("commands", {}), ("commands_seen", []), ("discipline_violations", []),
            ("note", None), ("valid", valid),
            ("invalid_reason", grade.get("invalid_reason")),
            ("summary", grade["summary"]),
            ("questions_graded", grade["questions_graded"]), ("answers", answers),
        ])

    def test_a_row_is_written_with_its_answers_beside_it_and_a_scorecard(self):
        root = tempfile.mkdtemp(prefix="docsbench-results-")
        try:
            gold, _doc = load("A1")
            answers = [correct_answer(q) for q in gold["questions"]]
            raw, answers_path = docs_bench.write_results(self.record(answers), root,
                                                         "2026-09-06")
            folder = os.path.join(root, "docs-2026-09-06")
            self.assertTrue(os.path.exists(raw))
            self.assertTrue(os.path.exists(answers_path))
            self.assertEqual(answers, json.loads(read(answers_path)))
            rows = json.loads(read(os.path.join(folder, "scorecard.json")))
            self.assertEqual(1, len(rows))
            self.assertNotIn("answers", rows[0])       # the scorecard stays small
            self.assertNotIn("questions_graded", rows[0])
            card = read(os.path.join(folder, "scorecard.md"))
            self.assertIn("Document-reading ablation", card)
            self.assertIn("| R1 | claude | sonnet | A1 | 1.00 |", card)
            self.assertIn("| yes |", card)             # discipline enforced
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_regrade_rescores_a_stored_row_without_calling_a_model(self):
        root = tempfile.mkdtemp(prefix="docsbench-regrade-")
        try:
            gold, _doc = load("A1")
            answers = [correct_answer(q) for q in gold["questions"]]
            record = self.record(answers)
            record["summary"] = collections.OrderedDict(
                [("fact_recall", 0.0), ("fabrications", 99)])   # a stale, wrong scorecard
            docs_bench.write_results(record, root, "2026-09-06")
            folder = os.path.join(root, "docs-2026-09-06")
            with quiet():
                self.assertEqual(0, docs_bench.regrade(folder, BED))
            raw = json.loads(read(os.path.join(folder, "raw", record["row"] + ".json")))
            self.assertEqual(1.0, raw["summary"]["fact_recall"])
            self.assertEqual(0, raw["summary"]["fabrications"])
            self.assertIn("regraded_at", raw)
            rows = json.loads(read(os.path.join(folder, "scorecard.json")))
            self.assertEqual(1, len(rows))
            self.assertEqual(1.0, rows[0]["summary"]["fact_recall"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_regrade_of_an_r2_row_refills_the_menu_probe(self):
        root = tempfile.mkdtemp(prefix="docsbench-regrade2-")
        try:
            gold, _doc = load("A1")
            record = self.record([correct_answer(q) for q in gold["questions"]], arm="R2")
            docs_bench.write_results(record, root, "2026-09-06")
            folder = os.path.join(root, "docs-2026-09-06")
            with quiet():
                self.assertEqual(0, docs_bench.regrade(folder, BED))
            raw = json.loads(read(os.path.join(folder, "raw", record["row"] + ".json")))
            self.assertIsNotNone(raw["summary"]["menu_recall@5"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_row_that_never_ran_is_not_averaged_into_the_arm(self):
        """The bug: ten failed R2 launches beside three real ones read as an arm scoring
        0.16 when the arm scored 0.70."""
        gold, _doc = load("A1")
        good = self.record([correct_answer(q) for q in gold["questions"]], arm="R2")
        good["row"] = "docs-R2-claude-sonnet-A1-1"
        failed = self.record([], arm="R2")
        failed["row"] = "docs-R2-claude-sonnet-V1-1"
        failed["note"] = "the agent exited 1: ; no answers array in the reply"
        self.assertFalse(docs_bench.is_valid(failed))
        self.assertTrue(docs_bench.is_valid(good))
        table = docs_bench.arm_table([good, failed])
        self.assertIn("| R2 find.py | 1 | 1 | 1.000 |", table)
        self.assertIn("NOT RUN", docs_bench.md_row(failed))
        self.assertNotIn("NOT RUN", docs_bench.md_row(good))

    def test_a_row_a_launcher_marked_a_provider_error_is_not_averaged_either(self):
        gold, _doc = load("A1")
        record = self.record([correct_answer(q) for q in gold["questions"]])
        record["outcome"] = "provider_error"
        self.assertFalse(docs_bench.is_valid(record))

    def test_regrade_strips_the_zeros_off_a_row_that_never_ran(self):
        """The stored row was graded 0.0 across the board by the old rules; regrading it
        with today's must leave it with no summary at all."""
        root = tempfile.mkdtemp(prefix="docsbench-regrade4-")
        try:
            record = self.record([])
            record["valid"] = True
            record["summary"] = collections.OrderedDict(
                [("fact_recall", 0.0), ("span_recall", 0.0), ("fabrications", 0)])
            docs_bench.write_results(record, root, "2026-09-07")
            folder = os.path.join(root, "docs-2026-09-07")
            with quiet():
                self.assertEqual(0, docs_bench.regrade(folder, BED))
            raw = json.loads(read(os.path.join(folder, "raw", record["row"] + ".json")))
            self.assertIsNone(raw["summary"])
            self.assertFalse(raw["valid"])
            card = read(os.path.join(folder, "scorecard.md"))
            self.assertIn("NOT RUN", card)
            self.assertIn("| not run |", card)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_regrade_of_a_folder_with_no_raw_is_a_usage_error(self):
        root = tempfile.mkdtemp(prefix="docsbench-regrade3-")
        try:
            with quiet():
                self.assertEqual(2, docs_bench.regrade(root, BED))
        finally:
            shutil.rmtree(root, ignore_errors=True)


class TestTheCli(unittest.TestCase):
    def run_main(self, argv):
        with quiet() as out:
            code = docs_bench.main(argv)
            err = sys.stderr.getvalue()
        return code, out.getvalue(), err

    def test_no_arm_and_no_matrix_is_a_usage_error(self):
        code, _out, err = self.run_main(["--cases", BED, "--dry-run"])
        self.assertEqual(2, code)
        self.assertIn("--arm", err)

    def test_a_bed_with_no_cases_folder_is_a_usage_error_that_points_at_the_docs(self):
        empty = tempfile.mkdtemp(prefix="docsbench-empty-")
        try:
            code, _out, err = self.run_main(["--cases", empty, "--arm", "R0", "--dry-run"])
            self.assertEqual(2, code)
            self.assertIn("evals/docs/README.md", err)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_an_unknown_case_id_is_a_usage_error(self):
        code, _out, err = self.run_main(
            ["--cases", BED, "--arm", "R0", "--case", "ZZ", "--dry-run"])
        self.assertEqual(2, code)
        self.assertIn("no case", err)

    def test_the_menu_probe_runs_from_the_command_line_and_costs_nothing(self):
        code, out, _err = self.run_main(["--cases", BED, "--menu-probe"])
        self.assertEqual(0, code)
        self.assertIn("menu_recall@5:", out)
        self.assertIn("A1-q1", out)

    def test_the_bed_lists_its_cases(self):
        self.assertEqual(list(CASES), docs_bench.case_ids(BED))


if __name__ == "__main__":
    unittest.main()
