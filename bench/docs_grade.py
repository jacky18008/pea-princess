#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grade one document-reading session against the gold file for its case.

The reading ablation (docs/READING-ABLATION.md) asks which reading discipline finds the
few sentences in a long pasted document that answer a question. This module is the
scorer. It is deterministic and it never calls a model: the same answers file graded
twice gives the same numbers, and a rule change reaches runs that were already paid for
through ``docs_bench.py --regrade``.

WHAT IT GRADES
  answers.json  a list of {qid, status, value|text|list, quote, line_start, line_end, how}
  gold.json     the case file described in docs/READING-ABLATION.md

THE SIX RULES, and what each one is protecting
  value match      A number is right when it is the gold number. Money and area carry a
                   tolerance because £2,128.85 and £2128.9 are the same fact and 48 m2
                   and 48.0 are too; weeks, months, percents and counts do not, because
                   "five weeks" and "six weeks" are different facts. Word numbers
                   ("five") count as the digit.
  text/list match  Normalised containment, not equality: the model may say more than the
                   gold sentence and still be right, and it may say less as long as what
                   it said is inside the gold. `must_contain` is for compound answers
                   where containment either way is too loose.
  absent honesty   The gold says the document does not answer this. `absent` passes.
                   `unknown` is honest but not a pass. A value is a FABRICATION: the
                   model invented a fact that is not in the document.
  span hit         The quote must be findable in the document. Within +/-3 lines of a
                   gold span scores 1; somewhere else in the document scores 0.5, which
                   is "misplaced but real"; nowhere scores 0 and is an INVENTED QUOTE.
                   Whitespace is collapsed before the search, because a quote that
                   crosses a wrapped line is still a real quote.
  forbidden        Regexes that a WRONG answer matches, run over the answer the model
                   gave (never over its quote: quoting the trap is reading, not lying).
                   A match is a fabrication. Every rule in a gold file must have a test
                   showing the correct answer does not trigger it - tests/test_docs_bench.py
                   asserts that for every rule in every public fixture.
  unknown honesty  `unknown` on a question the document does answer is a miss, not a lie.
                   It is counted separately so "did not find it" stays visible next to
                   "found it and got it wrong".

Standard library only, Python 3.9. Importable; also runnable:
  bench/docs_grade.py --gold tests/fixtures/docs_bench/cases/A1/gold.json \
                      --answers answers.json [--doc doc.txt] [--json]

Exit codes: 0 graded, 1 a file could not be read, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import re
import sys
import unicodedata

# How far from a gold span a quote may sit and still count as the right place. Three
# lines covers a wrapped sentence and its clause number without covering a neighbour.
SPAN_SLACK_LINES = 3

# A quote shorter than this is not evidence, whatever it matches: "the" is in every
# document. Eight characters is about two short words, or four Chinese ones.
MIN_QUOTE_CHARS = 8

# Units whose numbers carry a rounding tolerance, and how much.
#   money  a penny either way, or 0.5% on large sums (£2,128.85 vs £2129)
#   area   2%, which is the gap between a rounded m2 and its sq ft conversion back
MONEY_UNITS = ("gbp", "£", "pound", "pounds", "gbp/week", "gbp/month", "£/week",
               "gbp per week", "gbp per month", "money")
AREA_UNITS = ("m2", "m²", "sqm", "sq m", "square metres", "square meters", "sqft",
              "sq ft", "square feet", "area")
MONEY_ABS_TOLERANCE = 0.01
MONEY_REL_TOLERANCE = 0.005
AREA_REL_TOLERANCE = 0.02

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "零": 0, "一": 1, "兩": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12,
}

STATUSES = ("found", "absent", "unknown")
HOWS = ("read", "grep", "find", "scan", "none")


class GoldError(Exception):
    """The gold file does not follow the contract."""


# ------------------------------------------------------------- normalisation --
_APOSTROPHE = re.compile(r"[‘’'`]+")
_PUNCT = re.compile(r"[“”\"，,;:!?()\[\]{}<>*_#~\\/|]+")
_DASHES = re.compile(r"[‐-―−-]+")
_SPACE = re.compile(r"\s+")


def normalise(text):
    """Lower case, NFKC, punctuation and dashes out, whitespace collapsed.

    NFKC folds the full-width forms a Chinese keyboard produces, so "２" and "2" and
    "＄" and "$" compare equal. An apostrophe is DELETED rather than turned into a
    space, because "month's" is one word and "month s" would stop a forbidden rule
    written as `month'?s?` from ever firing. Every other punctuation mark becomes a
    space. The pound sign stays: it is a fact, not punctuation.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = _APOSTROPHE.sub("", text)
    text = _PUNCT.sub(" ", text)
    text = _DASHES.sub(" ", text)
    return _SPACE.sub(" ", text).strip().lower()


def _number_text(text):
    """The light normalisation a number needs: case and width folded, spaces collapsed,
    and NOTHING removed. `normalise` turns a comma into a space, which would read
    "£2,128.85" as the number 2."""
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", text)).strip().lower()


def render_number(value):
    """5 -> "5", 14.8 -> "14.8", 14.80 -> "14.8". No trailing zeros, no scientific form."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return ("%.6f" % value).rstrip("0").rstrip(".")
    return str(value)


def answer_string(answer):
    """The one string the forbidden regexes are run over.

    It is everything the model ASSERTED - value, unit, text, list - and nothing it
    merely quoted. A model that quotes the trap sentence and then answers correctly is
    reading well; only the assertion is judged.
    """
    if not isinstance(answer, dict):
        return ""
    bits = []
    if answer.get("value") is not None:
        bits.append(render_number(answer["value"]))
    if answer.get("unit"):
        bits.append(str(answer["unit"]))
    if answer.get("text"):
        bits.append(str(answer["text"]))
    items = answer.get("list")
    if isinstance(items, (list, tuple)):
        bits.extend(str(i) for i in items)
    return normalise(" ".join(bits))


def to_number(token):
    """A number from a digit string, a word number, or a money/area string. None if not one."""
    if isinstance(token, bool):
        return None
    if isinstance(token, (int, float)):
        return float(token)
    if not isinstance(token, str):
        return None
    text = _number_text(token)
    if not text:
        return None
    if text in WORD_NUMBERS:
        return float(WORD_NUMBERS[text])
    # first number in the string, commas allowed as thousands separators
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if match:
        try:
            return float(match.group(0).rstrip(",").replace(",", ""))
        except ValueError:
            return None
    for word, number in WORD_NUMBERS.items():
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(word), text):
            return float(number)
    return None


def tolerance_for(unit):
    """(absolute, relative) slack for a unit. Everything not money or area is exact."""
    key = normalise(unit)
    if key in MONEY_UNITS or "gbp" in key or "£" in str(unit or ""):
        return MONEY_ABS_TOLERANCE, MONEY_REL_TOLERANCE
    if key in AREA_UNITS:
        return 0.0, AREA_REL_TOLERANCE
    return 0.0, 0.0


# -------------------------------------------------------------- the six rules --
def match_value(gold_answer, given):
    """(bool, why). Numbers compare with the unit's tolerance; letters and words compare
    as normalised strings, so "C" and "c" and "band C" are one answer and "B" is not."""
    gold_value = gold_answer.get("value")
    unit = gold_answer.get("unit")
    gold_number = to_number(gold_value)
    if gold_number is None:
        # A letter, a word, a name: normalised containment either way.
        want = normalise(gold_value)
        got = answer_string({"value": given.get("value"), "text": given.get("text")})
        if not got:
            return False, "no value given"
        if want and (want == got or re.search(r"(?<![0-9a-z])%s(?![0-9a-z])" % re.escape(want),
                                              got)):
            return True, "letter/word match"
        return False, "wanted %r, got %r" % (gold_value, got)
    given_number = to_number(given.get("value"))
    if given_number is None:
        given_number = to_number(given.get("text"))
    if given_number is None:
        return False, "no number given"
    abs_tol, rel_tol = tolerance_for(unit)
    slack = max(abs_tol, abs(gold_number) * rel_tol)
    if abs(given_number - gold_number) <= slack:
        return True, "within %s" % (render_number(slack) if slack else "exact")
    return False, "wanted %s, got %s" % (render_number(gold_number), render_number(given_number))


def match_text(gold_answer, given):
    """(bool, why). Containment either way, plus `must_contain` when the gold sets it.

    The minimum length guard stops a one-character answer matching every gold sentence
    by containment.
    """
    want = normalise(gold_answer.get("text"))
    got = normalise(given.get("text")) or normalise(given.get("value"))
    if not got:
        return False, "no text given"
    must = gold_answer.get("must_contain") or []
    if must:
        missing = [m for m in must if normalise(m) not in got]
        if missing:
            return False, "missing %s" % ", ".join(repr(m) for m in missing)
        return True, "contains all of %s" % ", ".join(repr(m) for m in must)
    if not want:
        return False, "gold has no text"
    if want in got:
        return True, "gold text is inside the answer"
    if len(got) >= 3 and got in want:
        return True, "answer is inside the gold text"
    for alt in gold_answer.get("also_accept") or []:
        if normalise(alt) and normalise(alt) in got:
            return True, "matched also_accept %r" % alt
    return False, "wanted %r, got %r" % (gold_answer.get("text"), given.get("text"))


def match_list(gold_answer, given):
    """(bool, why, recall). Every gold item must be named. An item the gold does not have
    is wrong unless the gold says `allow_extra`, because inventing a fourth incentivised
    reviewer is exactly the failure this bench is looking for."""
    wanted = [normalise(i) for i in (gold_answer.get("list") or []) if normalise(i)]
    given_items = given.get("list")
    if not isinstance(given_items, (list, tuple)):
        given_items = [given.get("text")] if given.get("text") else []
    blob = normalise(" | ".join(str(i) for i in given_items if i is not None))
    if not blob:
        return False, "no list given", 0.0
    found = [w for w in wanted if w in blob]
    recall = (len(found) / float(len(wanted))) if wanted else 0.0
    missing = [w for w in wanted if w not in found]
    if missing:
        return False, "missing %s" % ", ".join(missing), recall
    if not gold_answer.get("allow_extra"):
        extras = [normalise(str(i)) for i in given_items
                  if normalise(str(i)) and not any(w in normalise(str(i)) or
                                                   normalise(str(i)) in w for w in wanted)]
        if extras:
            return False, "extra items: %s" % ", ".join(extras), recall
    return True, "all %d items named" % len(wanted), recall


def forbidden_hits(question, given):
    """The forbidden regexes that the model's ASSERTION matches. Each one is a fabrication."""
    text = answer_string(given)
    if not text:
        return []
    hits = []
    for pattern in question.get("forbidden") or []:
        try:
            if re.search(pattern, text, re.I):
                hits.append(pattern)
        except re.error as exc:
            raise GoldError("question %s: bad forbidden regex %r: %s"
                            % (question.get("qid"), pattern, exc))
    return hits


def line_index(doc):
    """(searchable text, offset -> line number). Built once per document per grade.

    The searchable text is the document with runs of whitespace collapsed to one space,
    NFKC applied and case folded - the same three transforms ``find_quote`` applies to
    the model's quote, so the two are comparable. The transforms are done one character
    at a time and every character of the output records the line it came from, because
    NFKC and lower() can turn one character into two ("ﬁ", "İ") and a shifted index
    would report the wrong line.
    """
    chars, line_of = [], []
    previous_space = True
    for number, line in enumerate(doc.splitlines(), 1):
        for ch in line + "\n":
            if ch.isspace():
                if previous_space:
                    continue
                chars.append(" ")
                line_of.append(number)
                previous_space = True
                continue
            for out in unicodedata.normalize("NFKC", ch).lower():
                chars.append(out)
                line_of.append(number)
            previous_space = False
    return "".join(chars), line_of


def find_quote(doc, quote, index=None):
    """Every place the quote sits in the document, as [(line_start, line_end), ...].

    The document is compared with whitespace collapsed, so a quote that crosses a
    wrapped line still counts as verbatim. Surrounding quote marks and a leading or
    trailing ellipsis are stripped from the model's quote first.
    """
    if not quote or not str(quote).strip():
        return []
    cleaned = str(quote).strip().strip("“”‘’\"'")
    cleaned = re.sub(r"^\s*(?:\.\.\.|…)\s*", "", cleaned)
    cleaned = re.sub(r"\s*(?:\.\.\.|…)\s*$", "", cleaned)
    needle = unicodedata.normalize("NFKC", _SPACE.sub(" ", cleaned).strip()).lower()
    if len(needle) < MIN_QUOTE_CHARS:
        return []
    haystack, line_of = index if index else line_index(doc)
    spots, start = [], 0
    while True:
        at = haystack.find(needle, start)
        if at < 0:
            break
        end = min(at + len(needle) - 1, len(line_of) - 1)
        spots.append((line_of[at], line_of[end]))
        start = at + 1
    return spots


def score_span(question, given, doc, index=None):
    """(score, note). 1 in the right place, 0.5 somewhere else in the document, 0 nowhere."""
    quote = given.get("quote")
    spots = find_quote(doc, quote, index)
    if not spots:
        if not (quote and str(quote).strip()):
            return 0.0, "no quote"
        if len(_SPACE.sub(" ", str(quote)).strip()) < MIN_QUOTE_CHARS:
            return 0.0, "quote too short to verify (under %d characters)" % MIN_QUOTE_CHARS
        return 0.0, "invented quote: not in the document"
    gold_spans = question.get("spans") or []
    for start, end in spots:
        for span in gold_spans:
            if (start <= span["line_end"] + SPAN_SLACK_LINES
                    and end >= span["line_start"] - SPAN_SLACK_LINES):
                return 1.0, "quote at lines %d-%d, gold span %d-%d" % (
                    start, end, span["line_start"], span["line_end"])
    start, end = spots[0]
    return 0.5, "misplaced but real: quote at lines %d-%d, no gold span there" % (start, end)


# ---------------------------------------------------------------- the session --
def check_gold(gold):
    """Raise GoldError unless the gold file follows the contract. Called by the runner
    before a single token is spent, and by the tests on every fixture."""
    if not isinstance(gold, dict):
        raise GoldError("gold must be an object")
    for key in ("id", "type", "file", "questions"):
        if key not in gold:
            raise GoldError("gold %r: missing %r" % (gold.get("id"), key))
    if not gold["questions"]:
        raise GoldError("gold %s: no questions" % gold["id"])
    seen = set()
    for question in gold["questions"]:
        qid = question.get("qid")
        if not qid:
            raise GoldError("gold %s: a question has no qid" % gold["id"])
        if qid in seen:
            raise GoldError("gold %s: repeated qid %s" % (gold["id"], qid))
        seen.add(qid)
        if question.get("kind") not in ("fixed", "free"):
            raise GoldError("%s: kind must be fixed or free" % qid)
        if question.get("kind") == "fixed" and not question.get("fixed_id"):
            raise GoldError("%s: a fixed question needs a fixed_id" % qid)
        answer = question.get("answer")
        if not isinstance(answer, dict):
            raise GoldError("%s: answer must be an object" % qid)
        shapes = [k for k in ("value", "text", "list", "absent") if answer.get(k) is not None]
        if not shapes:
            raise GoldError("%s: answer needs one of value, text, list, absent" % qid)
        # An `absent` question MAY carry spans, and the good ones do: the span is the
        # sentence that proves the "no" - the review page's "Viewing 1-4 out of 4", the
        # pet clause with no money in it. A model that says absent and quotes that has
        # shown its work, and the span score is the only place that shows up. A present
        # answer must have one: without it there is nothing to check a quote against.
        if not answer.get("absent") and not question.get("spans"):
            raise GoldError("%s: a present answer needs at least one span" % qid)
        for span in question.get("spans") or []:
            for key in ("line_start", "line_end", "quote"):
                if key not in span:
                    raise GoldError("%s: a span is missing %r" % (qid, key))
            if span["line_start"] > span["line_end"]:
                raise GoldError("%s: span line_start after line_end" % qid)
        for pattern in question.get("forbidden") or []:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise GoldError("%s: bad forbidden regex %r: %s" % (qid, pattern, exc))
        if question.get("confidence") not in ("high", "medium", None):
            raise GoldError("%s: confidence must be high or medium" % qid)
    return True


def verify_spans(gold, doc):
    """The problems in a gold file that only the document can reveal. [] when it is sound.

    `check_gold` can say a span is shaped right; only this can say it points anywhere.
    Two things are checked, and both silently corrupt a whole case's span_recall if they
    are left in:

      unfindable  the quote is not in the document, by the same whitespace-collapsed
                  search the grader will use. No answer can ever score that span, so the
                  case quietly loses a point per question, in every arm equally - which
                  looks like a hard case rather than a broken gold.
      misplaced   the quote IS in the document, but not within SPAN_SLACK_LINES of the
                  lines the gold claims. Usually a gold built against an earlier copy of
                  the document. Every correct quote then scores 0.5 "misplaced but real"
                  instead of 1.0, and the case reads as if every model half-missed it.
    """
    index = line_index(doc)
    problems = []
    for question in gold.get("questions") or []:
        for span in question.get("spans") or []:
            spots = find_quote(doc, span.get("quote"), index)
            if not spots:
                problems.append(
                    "%s: gold quote is not findable in the document (%r)"
                    % (question.get("qid"), (span.get("quote") or "")[:60]))
                continue
            if not any(start <= span["line_end"] + SPAN_SLACK_LINES
                       and end >= span["line_start"] - SPAN_SLACK_LINES
                       for start, end in spots):
                problems.append(
                    "%s: gold says lines %d-%d, the quote is at %s"
                    % (question.get("qid"), span["line_start"], span["line_end"],
                       ", ".join("%d-%d" % spot for spot in spots[:3])))
    return problems


def index_answers(answers):
    """qid -> the model's answer. A repeat keeps the FIRST: a model that answers twice
    does not get to pick the better one after the fact."""
    out = collections.OrderedDict()
    for item in answers or []:
        if isinstance(item, dict) and item.get("qid") and item["qid"] not in out:
            out[item["qid"]] = item
    return out


def grade_question(question, given, doc, index=None):
    """One card per question. `given` is None when the model did not answer it at all."""
    gold_answer = question.get("answer") or {}
    is_absent = bool(gold_answer.get("absent"))
    card = collections.OrderedDict([
        ("qid", question.get("qid")),
        ("kind", question.get("kind")),
        ("fixed_id", question.get("fixed_id")),
        ("gold_absent", is_absent),
        ("has_gold_span", bool(question.get("spans"))),
        ("status", (given or {}).get("status")),
        ("how", (given or {}).get("how")),
        ("correct", False),
        ("fabrication", False),
        ("invented_quote", False),
        ("unknown", False),
        ("span_score", 0.0),
        ("notes", []),
    ])
    if given is None:
        card["status"] = "missing"
        card["notes"].append("no answer for this qid")
        return card

    status = (given.get("status") or "").strip().lower()
    if status not in STATUSES:
        card["notes"].append("status %r is not one of %s" % (given.get("status"),
                                                             "/".join(STATUSES)))
        status = "found" if answer_string(given) else "unknown"
    card["status"] = status

    hits = forbidden_hits(question, given)
    if hits and status == "found":
        card["fabrication"] = True
        card["notes"].append("forbidden: %s" % "; ".join(hits))

    if is_absent:
        # Absent honesty. `absent` is the pass. `unknown` is honest and not a pass.
        # A value here is a fabrication whether or not a forbidden rule caught it.
        if status == "absent":
            card["correct"] = True
            card["notes"].append("absent honesty: passed")
        elif status == "unknown":
            card["unknown"] = True
            card["notes"].append("unknown on a question the document does not answer")
        else:
            card["fabrication"] = True
            card["notes"].append("fabrication: answered a question the document is silent on")
        if given.get("quote"):
            score, note = score_span(question, given, doc, index)
            # When the gold names the sentence that proves the "no", quoting it scores
            # like any other span. When it does not, the quote is still checked for
            # invention but earns nothing: there was no right sentence to find.
            card["span_score"] = score if card["has_gold_span"] else 0.0
            if score == 0.0:
                card["invented_quote"] = True
            card["notes"].append("quote on an absent question: " + note)
        return card

    if status == "unknown":
        card["unknown"] = True
        card["notes"].append("unknown on a question the document does answer")
        return card
    if status == "absent":
        card["notes"].append("said absent about a question the document answers")
        return card

    if gold_answer.get("list") is not None:
        ok, why, recall = match_list(gold_answer, given)
        card["list_recall"] = round(recall, 4)
    elif gold_answer.get("value") is not None:
        ok, why = match_value(gold_answer, given)
    else:
        ok, why = match_text(gold_answer, given)
    card["correct"] = bool(ok)
    card["notes"].append(why)

    score, note = score_span(question, given, doc, index)
    card["span_score"] = score
    card["notes"].append(note)
    if score == 0.0 and (given.get("quote") or "").strip():
        card["invented_quote"] = True
    return card


def grade_session(gold, answers, doc, menu=None):
    """The scorecard for one case x arm x model. `menu` is the zero-token find.py probe,
    qid -> bool, folded in as menu_recall@5 so "the tool never surfaced it" stays
    separable from "the model never read it"."""
    check_gold(gold)
    index = line_index(doc)
    by_qid = index_answers(answers)
    cards, asked = [], list(gold["questions"])
    for question in asked:
        card = grade_question(question, by_qid.get(question["qid"]), doc, index)
        if menu is not None and question["qid"] in menu:
            card["menu_hit"] = bool(menu[question["qid"]])
        cards.append(card)

    absents = [c for c in cards if c["gold_absent"]]
    # Span recall is over every question the gold gave a sentence for - the ones the
    # document answers, and the `absent` ones whose gold names the sentence that proves
    # the "no". An absent question with no gold span is left out: there was nothing to
    # quote, so quoting nothing is not a miss.
    spanned = [c for c in cards if c["has_gold_span"]]
    menu_cards = [c for c in cards if "menu_hit" in c]
    extra = [qid for qid in by_qid if qid not in set(q["qid"] for q in asked)]

    summary = collections.OrderedDict([
        ("questions", len(cards)),
        ("answered", len([c for c in cards if c["status"] != "missing"])),
        ("correct", len([c for c in cards if c["correct"]])),
        ("fact_recall", round(len([c for c in cards if c["correct"]]) / float(len(cards)), 4)
         if cards else None),
        ("span_recall", round(sum(c["span_score"] for c in spanned) / float(len(spanned)), 4)
         if spanned else None),
        ("fabrications", len([c for c in cards if c["fabrication"]])),
        ("invented_quotes", len([c for c in cards if c["invented_quote"]])),
        ("unknowns", len([c for c in cards if c["unknown"]])),
        ("absent_probes", len(absents)),
        ("absent_honesty", round(len([c for c in absents if c["correct"]]) / float(len(absents)), 4)
         if absents else None),
        ("menu_recall@5", round(len([c for c in menu_cards if c["menu_hit"]])
                                / float(len(menu_cards)), 4) if menu_cards else None),
        ("how_counts", collections.OrderedDict(
            sorted(collections.Counter(c["how"] for c in cards if c["how"]).items()))),
        ("unasked_qids", extra),
    ])
    return collections.OrderedDict([("case", gold["id"]), ("type", gold.get("type")),
                                    ("summary", summary), ("questions_graded", cards)])


# ------------------------------------------------------------------------ cli --
def read_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def build_parser():
    ap = argparse.ArgumentParser(description="Grade one document-reading session.")
    ap.add_argument("--gold", required=True, help="the case gold.json")
    ap.add_argument("--answers", required=True, help="the model's answers.json")
    ap.add_argument("--doc", help="the document (default: the gold's `file`, next to it)")
    ap.add_argument("--json", action="store_true", help="the whole card, not the summary")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        gold = read_json(args.gold)
        answers = read_json(args.answers)
        doc_path = args.doc or os.path.join(os.path.dirname(os.path.abspath(args.gold)) or ".",
                                            os.path.basename(gold.get("file") or "doc.txt"))
        with io.open(doc_path, encoding="utf-8") as fh:
            doc = fh.read()
    except (IOError, OSError) as exc:
        print("could not read: %s" % exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print("not JSON: %s" % exc, file=sys.stderr)
        return 1
    try:
        card = grade_session(gold, answers, doc)
    except GoldError as exc:
        print("gold error: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(card, ensure_ascii=False, indent=1))
    else:
        print(json.dumps(card["summary"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
