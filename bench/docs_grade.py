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
  text/list match  KEY containment, not sentence containment. A gold reading "A licence.
                   Clause 1.1 says the Agreement is a licence to occupy and does not
                   create a tenancy" and an answer reading "This Agreement is a licence,
                   not a tenancy" are the same answer, and whole-sentence matching scored
                   that wrong. The keys are `keys: [...]` on the gold question when the
                   bed's author has named them - then every one is required - or else
                   derived: every number the gold states (clause citations excluded),
                   every value in its `list` (citation keys excluded), and up to three
                   distinctive terms. Derived numbers and list values are FACTS and all
                   required; derived terms are this module's guess at vocabulary, so one
                   is enough. The keys used are written into every graded item so the
                   maintainer can see what an answer was judged on.
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

A session with NO answers array is not a session that scored zero. Its launch failed, and
grading it as a row of zeros poisons every mean it lands in: ten failed R2 launches beside
three real ones would read as an arm scoring 0.16 when the arm scored 0.70. Such a row gets
`valid: false`, no summary at all, and the scorecard counts it under "not run".

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

# A quote shorter than this is not evidence on its own: "the" is in every document.
# Eight characters is about two short words, or four Chinese ones. A short quote still
# counts when it sits in the document at most SHORT_QUOTE_MAX_HITS times: "£485 pw" or
# "1 Beds" is verifiable exactly because it is rare.
MIN_QUOTE_CHARS = 8
SHORT_QUOTE_MAX_HITS = 3

# On a question the document does not answer, a model sometimes files "found" and then
# says, in words, that the page is silent ("no price is shown", "does not state the
# window", "the agreement names no landlord"), quoting the sentence that proves it.
# That is the honest answer under the wrong status label: it earns the absent-honesty
# pass and is counted separately as `absent_said_as_found`, never as a fabrication.
SAYS_IT_IS_ABSENT = re.compile(
    r"\b(?:no|not|isn'?t|is not|does ?n'?o?t|do ?n'?o?t|never|none|nothing|nowhere|without|"
    r"neither|nor)\b[^.;\n]{0,60}?\b(?:shown|stated?|states|given|specified|specify|mentioned|"
    r"mentions?|listed|available|provided|said|says?|indicated|included|appears?|present|found|"
    r"disclosed|named|names|quoted|set out|visible|displayed|confirmed|known|clear|identified|"
    r"defined|described|recorded|published|offered|priced)\b"
    r"|\b(?:states|names|gives|lists|mentions|shows|specifies|provides|identifies|records|"
    r"offers|contains|includes)\s+(?:no|nothing|neither)\b"
    r"|\bnot applicable\b|\bsilent\b|\bunspecified\b|\bunstated\b|\bunknown\b|\bn/a\b"
    r"|未(?:提|列|載|寫|說明|標|顯示)|沒有?(?:提|列|寫|說明|標|顯示|給|載)|无|未知|不明|沒有?說",
    re.I)

# Text pulled out of a two-column PDF interleaves the columns line by line, so one
# sentence from the left column is cut by half-lines of the right one. A model that
# reads the sentence the way a person would cannot quote it verbatim against that text.
# The grader therefore also accepts a quote whose words appear in order within this
# many lines, when at least this share of them is found and the quote has at least
# COLUMN_MIN_TOKENS words (fewer would match scattered words anywhere).
COLUMN_WINDOW_LINES = 12
COLUMN_TOKEN_SHARE = 0.9
COLUMN_MIN_TOKENS = 6
# ...and the found words must make up at least this share of all the words between the
# first and the last hit. Two interleaved columns give about a half; the same words
# scattered by chance across twelve lines of a long document give a few percent.
COLUMN_MIN_DENSITY = 0.25

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


# Words of five letters or more that carry no answer, so they cannot be a key. Two
# groups: ordinary English filler, and the CITATION scaffolding of these documents -
# "clause", "section", "schedule", "agreement" appear in every sentence and would be keys
# that any answer passes, which is worse than no key at all. Nothing that names a FACT is
# in here: "licence", "tenancy", "deposit", "guarantor" are the answers to this bed's
# questions and have to stay eligible.
STOP_WORDS = frozenset("""
about above after again against among another because before being below between both
cannot could does doing during each either every except further having however
inside into itself might more most much must other otherwise over same
should since some such than that their theirs them themselves then there these they
this those through under until upon were what when where which while whose will with
within without would your yours
also always applies apply based case cases does given includes including makes means
name named number numbers only other part parts place provided provides refer refers
relating relevant right rights said says shall show shows state stated states subject
taken takes term terms thing things time times used uses using various
agreement agreements clause clauses document documents paragraph paragraphs
schedule schedules section sections
""".split())

# A clause citation is not the answer. "Clause 1.1 says the Agreement is a licence" has
# one fact in it and the 1.1 is not it: the span and quote rules already check that the
# model went to the right place. Derived numeric keys skip these.
CLAUSE_REF = re.compile(
    r"\b(?:clause|clauses|section|sections|paragraph|para|paras|schedule|article|art|cl)\s*"
    r"\.?\s*\d+(?:\.\d+)*", re.I)
NUMBER_IN_TEXT = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
WORD_IN_TEXT = re.compile(r"[A-Za-z][A-Za-z'-]{4,}")
MAX_DERIVED_TERMS = 3
# How close two numbers have to be to count as the same one. A penny, or half a per cent
# of the larger figure: £10,319.00 and £10319 are one number, 5 and 6 are two.
KEY_ABS_TOLERANCE = 0.01
KEY_REL_TOLERANCE = 0.005


# A dict entry under one of these keys is a CITATION, not a fact: it says where the
# answer lives, and the span and quote rules already check that the model went there.
# `{"clauses": ["1.1", "8.3"]}` beside a gold text reading "A licence" would otherwise
# make five clause numbers compulsory, and "This Agreement is a licence, not a tenancy"
# would be marked wrong for not citing them.
CITATION_KEYS = frozenset((
    "clause", "clauses", "section", "sections", "paragraph", "paragraphs", "para",
    "paras", "schedule", "schedules", "article", "articles", "line", "lines",
    "line_start", "line_end", "source", "sources", "ref", "refs", "reference",
    "references", "cite", "citation", "citations", "quote", "quotes", "span", "spans"))


def scalars(value):
    """Every scalar inside a value, however deeply it nests, canonicalised.

    Numbers go through `render_number` so a gold's 10319.0 and the same figure written in
    its prose as "£10,319.00" become the one key "10319" rather than two that only one of
    them can satisfy.
    """
    if value is None:
        return []
    if isinstance(value, bool):
        return [str(value).lower()]
    if isinstance(value, (int, float)):
        return [render_number(value)]
    if isinstance(value, dict):
        out = []
        for key, item in value.items():
            if str(key).strip().lower() in CITATION_KEYS:
                continue
            out.extend(scalars(item))
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            out.extend(scalars(item))
        return out
    return [str(value)]


def flatten_values(answer):
    """Every scalar the gold states, as strings, in the order it states them.

    A `list` of dicts - `[{"from": "23:00"}, {"to": "07:00"}]` - contributes each dict's
    VALUES, because "from" and "to" are the schema and "23:00" is the fact. A dict entry
    naming a citation (CITATION_KEYS) contributes nothing.
    """
    out = []
    if answer.get("text"):
        out.append(str(answer["text"]))
    out.extend(scalars(answer.get("list")))
    return out


def numbers_in(text):
    """Every number in a string, as floats, in order, with clause citations removed."""
    cleaned = CLAUSE_REF.sub(" ", text or "")
    out = []
    for token in NUMBER_IN_TEXT.findall(cleaned):
        try:
            out.append(float(token.rstrip(",").replace(",", "")))
        except ValueError:
            continue
    return out


def derive_keys(gold_answer):
    """The keys of a gold answer when the gold file does not name them.

    Three sources, in this order:
      1. every number the gold states (clause citations excluded - see CLAUSE_REF);
      2. each dict key's VALUE in a `list` of dicts;
      3. up to three distinctive terms - words of five letters or more that are not in
         STOP_WORDS, the first three that appear in the gold text.

    Derivation is a fallback, not a contract. The keys it produces are written into the
    graded item's notes on every question so the maintainer can see what an answer was
    actually judged on, and put an explicit `keys: [...]` on the gold where this guessed
    wrong. A prose gold whose first sentence is the answer and whose rest is the
    citation is the case derivation handles worst.
    """
    values = flatten_values(gold_answer)
    keys, seen = [], set()

    def add(key):
        token = normalise(key)
        if token and token not in seen:
            seen.add(token)
            keys.append(key)
            return True
        return False

    # Numbers come from the gold's prose. A list's values are added whole just below, so
    # taking numbers out of them as well would turn {"from": "23:00"} into the three keys
    # 23, 0 and "23:00" and say nothing more than "23:00" already says.
    for number in numbers_in(gold_answer.get("text") or ""):
        add(render_number(number))
    for value in scalars(gold_answer.get("list")):
        add(value)
    facts = list(keys)
    terms = []
    for text in values:
        for word in WORD_IN_TEXT.findall(CLAUSE_REF.sub(" ", text)):
            if len(terms) >= MAX_DERIVED_TERMS:
                break
            if word.lower() in STOP_WORDS or normalise(word) in seen:
                continue
            if add(word):
                terms.append(word)
        if len(terms) >= MAX_DERIVED_TERMS:
            break
    return facts, terms


def keys_for(question, gold_answer):
    """(facts, terms, where they came from).

    `facts` must ALL be in the answer. `terms` are softer: at least one has to be, and
    only when there is no fact to check. The split is the difference between what the
    gold KNOWS and what the harness GUESSED. A number and a dict value are facts the gold
    states; a distinctive term is this module's guess at which words a right answer would
    use, and a right answer is free to paraphrase. Requiring all three guessed terms is
    what scored "This Agreement is a licence, not a tenancy" as wrong against a gold
    reading "A licence. Clause 1.1 says the Agreement is a licence to occupy and does not
    create a tenancy".

    An explicit `keys: [...]` on the gold question is all facts and always wins: when the
    bed's author has named the keys, every one of them is required.
    """
    explicit = question.get("keys") if isinstance(question, dict) else None
    if explicit:
        return [str(k) for k in explicit], [], "keys from the gold"
    facts, terms = derive_keys(gold_answer)
    return facts, terms, "keys derived"


def key_present(key, got_text, got_numbers, unit=None):
    """Is one key in the answer? Numbers compare as numbers, words as normalised text."""
    number = to_number(key) if NUMBER_IN_TEXT.search(str(key) or "") else None
    if number is not None and normalise(key) == normalise(render_number(number)):
        abs_tol, rel_tol = tolerance_for(unit)
        slack = max(abs_tol, KEY_ABS_TOLERANCE, abs(number) * max(rel_tol, KEY_REL_TOLERANCE))
        return any(abs(candidate - number) <= slack for candidate in got_numbers)
    token = normalise(key)
    return bool(token) and token in got_text


def match_keys(question, gold_answer, given):
    """(bool, why, recall). The answer is right when every key of the gold is in it.

    This replaces whole-sentence containment, which scored a correct paraphrase as wrong:
    a gold reading "A licence. Clause 1.1 says the Agreement is a licence to occupy and
    does not create a tenancy" and an answer reading "This Agreement is a licence, not a
    tenancy" are the same answer, and only a key test says so.
    """
    facts, terms, source = keys_for(question, gold_answer)
    got_text = answer_string(given)
    got_numbers = numbers_in(" ".join(
        str(v) for v in (given.get("text"), given.get("value"),
                         " ".join(str(i) for i in (given.get("list") or [])
                                  if i is not None)) if v is not None))
    why = "%s: %s" % (source, ", ".join(repr(k) for k in facts + terms) or "none")
    if not got_text:
        return False, "no answer given; " + why, 0.0
    if not facts and not terms:
        return False, "the gold states no key to check (%s)" % source, 0.0
    unit = gold_answer.get("unit")
    found_facts = [k for k in facts if key_present(k, got_text, got_numbers, unit)]
    found_terms = [k for k in terms if key_present(k, got_text, got_numbers, unit)]
    everything = facts + terms
    recall = (len(found_facts) + len(found_terms)) / float(len(everything))
    missing = [k for k in facts if k not in found_facts]
    if missing:
        return False, why + "; missing %s" % ", ".join(repr(k) for k in missing), recall
    # A derived term is a guess at vocabulary, so one hit is enough to say the answer is
    # about the same thing - and only when the gold stated no fact to check instead.
    if terms and not facts and not found_terms:
        return False, why + "; none of the derived terms is in the answer", recall
    if terms:
        why += "; %d of %d derived term(s) present" % (len(found_terms), len(terms))
    return True, why + ("; all facts present" if facts else ""), recall


def match_text(gold_answer, given, question=None):
    """(bool, why). Key containment. `must_contain` on the gold is an explicit key list
    under an older name and still wins over derivation."""
    must = gold_answer.get("must_contain") or []
    if must and not (question or {}).get("keys"):
        question = dict(question or {})
        question["keys"] = must
    ok, why, _recall = match_keys(question or {}, gold_answer, given)
    if ok:
        return True, why
    for alt in gold_answer.get("also_accept") or []:
        if normalise(alt) and normalise(alt) in answer_string(given):
            return True, "matched also_accept %r" % alt
    return False, why


def match_list(gold_answer, given, question=None):
    """(bool, why, recall). Right when every value the gold list states is in the answer.

    An item the gold does not have is NOT wrong here - a model that names a fourth
    incentivised reviewer is caught by that question's forbidden regexes, which is where
    inventions belong. Extras are still reported in the note so they stay visible.
    """
    ok, why, recall = match_keys(question or {}, gold_answer, given)
    given_items = given.get("list")
    if isinstance(given_items, (list, tuple)):
        wanted = set(normalise(v) for v in flatten_values(gold_answer))
        extras = [str(i) for i in given_items
                  if normalise(str(i)) and not any(normalise(str(i)) in w or
                                                   w in normalise(str(i)) for w in wanted)]
        if extras:
            why += "; not in the gold: %s" % ", ".join(repr(e) for e in extras[:5])
    return ok, why, recall


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


def clean_quote(quote):
    """The model's quote without surrounding quote marks or a leading/trailing ellipsis."""
    if not quote or not str(quote).strip():
        return ""
    cleaned = str(quote).strip().strip("“”‘’\"'")
    cleaned = re.sub(r"^\s*(?:\.\.\.|…)\s*", "", cleaned)
    cleaned = re.sub(r"\s*(?:\.\.\.|…)\s*$", "", cleaned)
    return cleaned.strip()


def normalise_quote(cleaned):
    return unicodedata.normalize("NFKC", _SPACE.sub(" ", cleaned).strip()).lower()


def _exact_spots(needle, haystack, line_of):
    spots, start = [], 0
    while True:
        at = haystack.find(needle, start)
        if at < 0:
            break
        end = min(at + len(needle) - 1, len(line_of) - 1)
        spots.append((line_of[at], line_of[end]))
        start = at + 1
    return spots


_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def _tokens(text):
    return [t for t in _TOKEN.findall(unicodedata.normalize("NFKC", text).lower())
            if len(t) > 1 or t.isdigit()]


def find_quote_reassembled(doc, cleaned):
    """Where the quote's words sit in order within COLUMN_WINDOW_LINES lines, as
    [(line_start, line_end)] — the match for a sentence read correctly out of two
    interleaved PDF columns. Empty when the quote is short or the words are not there."""
    want = _tokens(cleaned)
    if len(want) < COLUMN_MIN_TOKENS:
        return []
    per_line = [_tokens(line) for line in doc.splitlines()]
    flat, line_of = [], []
    for number, toks in enumerate(per_line, 1):
        flat.extend(toks)
        line_of.extend([number] * len(toks))
    if not flat:
        return []
    need = int(len(want) * COLUMN_TOKEN_SHARE + 0.999)
    best = None
    first_positions = [i for i, t in enumerate(flat) if t == want[0]]
    for at in first_positions:
        limit_line = line_of[at] + COLUMN_WINDOW_LINES - 1
        pos, hits, last = at, 0, at
        for token in want:
            j = pos
            while j < len(flat) and line_of[j] <= limit_line and flat[j] != token:
                j += 1
            if j < len(flat) and line_of[j] <= limit_line:
                hits += 1
                last = j
                pos = j + 1
        if hits >= need and hits / float(last - at + 1) >= COLUMN_MIN_DENSITY:
            span = (line_of[at], line_of[last])
            if best is None or (span[1] - span[0]) < (best[1] - best[0]):
                best = span
    return [best] if best else []


def locate_quote(doc, quote, index=None):
    """([(line_start, line_end), ...], how) for the model's quote.

    how is one of: "empty" (no quote), "verbatim" (found with whitespace collapsed, so a
    quote across a wrapped line counts), "reassembled" (words in order within a few
    lines: two-column PDF text), "short" (found, under MIN_QUOTE_CHARS, but rare enough
    to verify), "short_common" (under MIN_QUOTE_CHARS and all over the document: no
    evidence, but not invented), "invented" (not in the document).
    """
    cleaned = clean_quote(quote)
    if not cleaned:
        return [], "empty"
    needle = normalise_quote(cleaned)
    haystack, line_of = index if index else line_index(doc)
    spots = _exact_spots(needle, haystack, line_of) if needle else []
    if len(needle) < MIN_QUOTE_CHARS:
        if not spots:
            return [], "invented"
        if len(spots) > SHORT_QUOTE_MAX_HITS:
            return [], "short_common"
        return spots, "short"
    if spots:
        return spots, "verbatim"
    spots = find_quote_reassembled(doc, cleaned)
    if spots:
        return spots, "reassembled"
    return [], "invented"


def find_quote(doc, quote, index=None):
    """Every place the quote sits in the document, as [(line_start, line_end), ...];
    empty when it is not there (or too short and too common to verify)."""
    return locate_quote(doc, quote, index)[0]


def score_span(question, given, doc, index=None):
    """(score, note, invented). 1 in the right place, 0.5 somewhere else in the
    document, 0 nowhere. `invented` is True only when the quote is not in the document
    at all — never for an empty quote or one too short and common to verify."""
    quote = given.get("quote")
    spots, how = locate_quote(doc, quote, index)
    if how == "empty":
        return 0.0, "no quote", False
    if how == "short_common":
        return 0.0, ("quote too short to verify (under %d characters and found more than "
                     "%d times)" % (MIN_QUOTE_CHARS, SHORT_QUOTE_MAX_HITS)), False
    if how == "invented":
        return 0.0, "invented quote: not in the document", True
    label = {"verbatim": "quote", "reassembled": "quote reassembled from interleaved columns",
             "short": "short but rare quote"}[how]
    gold_spans = question.get("spans") or []
    for start, end in spots:
        for span in gold_spans:
            if (start <= span["line_end"] + SPAN_SLACK_LINES
                    and end >= span["line_start"] - SPAN_SLACK_LINES):
                return 1.0, "%s at lines %d-%d, gold span %d-%d" % (
                    label, start, end, span["line_start"], span["line_end"]), False
    start, end = spots[0]
    return 0.5, "misplaced but real: %s at lines %d-%d, no gold span there" % (label, start, end), False


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
        ("absent_said_as_found", False),
        ("quote_how", None),
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
        elif not hits and SAYS_IT_IS_ABSENT.search(answer_string(given) or ""):
            card["correct"] = True
            card["absent_said_as_found"] = True
            card["notes"].append("absent honesty: passed, said in words under a 'found' status")
        else:
            card["fabrication"] = True
            card["notes"].append("fabrication: answered a question the document is silent on")
        if given.get("quote"):
            score, note, invented = score_span(question, given, doc, index)
            # When the gold names the sentence that proves the "no", quoting it scores
            # like any other span. When it does not, the quote is still checked for
            # invention but earns nothing: there was no right sentence to find.
            card["span_score"] = score if card["has_gold_span"] else 0.0
            card["invented_quote"] = invented
            card["quote_how"] = locate_quote(doc, given.get("quote"), index)[1]
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
        ok, why, recall = match_list(gold_answer, given, question)
        card["key_recall"] = round(recall, 4)
    elif gold_answer.get("value") is not None:
        ok, why = match_value(gold_answer, given)
    else:
        ok, why = match_text(gold_answer, given, question)
    card["correct"] = bool(ok)
    card["notes"].append(why)

    score, note, invented = score_span(question, given, doc, index)
    card["span_score"] = score
    card["invented_quote"] = invented
    card["quote_how"] = locate_quote(doc, given.get("quote"), index)[1]
    card["notes"].append(note)
    return card


def grade_session(gold, answers, doc, menu=None):
    """The scorecard for one case x arm x model. `menu` is the zero-token find.py probe,
    qid -> bool, folded in as menu_recall@5 so "the tool never surfaced it" stays
    separable from "the model never read it"."""
    check_gold(gold)
    if not answers:
        # A row whose launch failed - the CLI exited non-zero, or the reply carried no
        # answers array - is NOT a model that scored zero, and grading it as one poisons
        # every mean it lands in. It has no summary at all, and the scorecard leaves it
        # out of the arm table rather than averaging a fiction. `bench/launch.py` will
        # classify the cause (provider_error) and re-run it; this is the floor that stops
        # the number being wrong in the meantime.
        return collections.OrderedDict([
            ("case", gold["id"]), ("type", gold.get("type")),
            ("valid", False),
            ("invalid_reason", "no answers array in the reply, so nothing was graded"),
            ("summary", None), ("questions_graded", [])])
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
        ("quotes_reassembled", len([c for c in cards if c["quote_how"] == "reassembled"])),
        ("quotes_short", len([c for c in cards if c["quote_how"] in ("short", "short_common")])),
        ("unknowns", len([c for c in cards if c["unknown"]])),
        ("absent_probes", len(absents)),
        ("absent_honesty", round(len([c for c in absents if c["correct"]]) / float(len(absents)), 4)
         if absents else None),
        ("absent_said_as_found", len([c for c in absents if c["absent_said_as_found"]])),
        ("menu_recall@5", round(len([c for c in menu_cards if c["menu_hit"]])
                                / float(len(menu_cards)), 4) if menu_cards else None),
        ("how_counts", collections.OrderedDict(
            sorted(collections.Counter(c["how"] for c in cards if c["how"]).items()))),
        ("unasked_qids", extra),
    ])
    return collections.OrderedDict([("case", gold["id"]), ("type", gold.get("type")),
                                    ("valid", True), ("invalid_reason", None),
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
