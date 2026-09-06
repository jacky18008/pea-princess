#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The referent guard: is this number about the thing we are asking about?

A number can be the right KIND and still be the wrong THING. The area of the building
is not the area of the flat. The rating on a replaced certificate is not the rating in
force. The journey "if the line is shut" is not the commute. A sale price is never a
year. Reports go wrong this way far more often than they go wrong by inventing a
figure, and the wrong-thing number reads exactly like a right one.

This module is the WORD LISTS and the KEYWORD RULES that catch those cases, in one
place so that two very different tools can apply the same test:

  skills/vet-flat/scripts/verify.py   the skill's own verifier, for any vendor
  bench/grade.py                      the benchmark's grader, which imports the lists
                                      from here so the two can never drift apart

Only the keyword half lives here. ``bench/grade.py`` keeps a few extra rules that need
to look at the report's own structure (a value that is a run of dated readings, an age
that is not a certificate date); those are the grader's business and are not portable.
``tests/test_verify.py`` asserts that the shared lists and the shared verdicts agree.

A rule fires when one of ``any_of`` appears in the text being judged, UNLESS one of
``keep_any`` also appears - the report has then said this IS the number the question
asks for, and we believe it.

Not a network tool. Standard library only, Python 3.9. It has no command line: it is
imported.
"""
from __future__ import unicode_literals

import collections
import re

# The label says this reading has been superseded.
HISTORICAL_WORDS = ["as built", "as designed", "design stage", "previous", "previously",
                    "earlier", "superseded", "expired", "lapsed", "historic", "historical",
                    "over time", "then and now", "when new", "originally", "at the time",
                    "no longer", "used to", "back then", "old certificate", "former",
                    "since replaced", "withdrawn", "history"]
# ... unless it also says this is the reading in force now.
CURRENT_WORDS = ["current", "latest", "most recent", "in force", "today", "now",
                 "as it stands"]
# A journey that is not the one the profile asks for: the fallback, the diversion,
# the strike plan, the weekend.
FALLBACK_WORDS = ["if", "fallback", "fall back", "back up", "backup", "alternative",
                  "alternate", "second best", "diversion", "diverted", "detour", "strike",
                  "strikes", "disruption", "disrupted", "engineering work", "replacement",
                  "night", "weekend", "worst case", "contingency", "plan b", "without",
                  "instead", "when the trains", "when the tube", "when the line"]
# ... unless the label names the very journey the fact asks for.
PRIMARY_JOURNEY_WORDS = ["door to door", "rail only", "train only", "trains only", "tube only"]
# Money. A price is never a year.
MONEY_WORDS = ["gbp", "pound", "pounds", "sterling", "price", "prices", "sale price",
               "sold for", "paid"]
# The certificate register, as opposed to the price register or the planning register.
CERTIFICATE_WORDS = ["assessment", "assessments", "assessed", "certificate", "certificates",
                     "epc", "energy"]
# The landlord's registered number is not a date.
COMPANY_WORDS = ["company", "companies house", "landlord", "agent", "managing agent",
                 "management", "freeholder", "leaseholder", "entity", "director",
                 "registered office", "registration"]
# The age of the building is not the date on the flat's certificate.
BUILDING_AGE_WORDS = ["building age", "age of the building", "building's age", "block age",
                      "age of the block", "development age", "age of the development",
                      "age of the scheme", "how old the building is"]
# Something measured over the whole building rather than inside this flat ...
BUILDING_WORDS = ["building", "block", "development", "estate", "scheme", "communal",
                  "whole building", "site"]
# ... unless the label says it is the flat's.
FLAT_WORDS = ["flat", "apartment", "unit", "home", "dwelling", "property"]

FLAT_ID = re.compile(r"\b(?:flat|apartment|apt|unit)\s+([0-9]+[a-z]?)\b")

# Which claims each rule is allowed to judge. A claim is matched by plain substring on
# the normalised claim text, so "certified internal floor area" matches "floor area".
AREA_CLAIMS = ["floor area", "area", "square metre", "square metres", "sq m", "m2", "sqft",
               "square foot", "square feet"]
RATING_CLAIMS = ["energy rating", "epc rating", "rating", "epc letter"]
YEAR_CLAIMS = ["assessment year", "first assessment", "year of assessment", "build year",
               "completion year", "new build year", "year built"]
JOURNEY_CLAIMS = ["commute", "journey", "door to door", "door-to-door", "travel time",
                  "minutes to", "rail time"]

# id, which claims it judges, what makes it fire, what cancels it, and why in one line.
# `guard` names an extra cancel that keywords cannot express. There is one:
# "year_value" - a year quoted under a money label is still a year.
Rule = collections.namedtuple("Rule", "id claims any_of keep_any why guard")

RULES = [
    Rule("building_not_flat", AREA_CLAIMS, BUILDING_WORDS, FLAT_WORDS,
         "this is measured over the building, not inside this flat", None),
    Rule("superseded_certificate", AREA_CLAIMS + RATING_CLAIMS, HISTORICAL_WORDS, CURRENT_WORDS,
         "this sits on a certificate the evidence itself marks as replaced", None),
    Rule("company_not_certificate", YEAR_CLAIMS, COMPANY_WORDS, CERTIFICATE_WORDS,
         "the number belongs to a company, not to a certificate", None),
    Rule("money_not_a_year", YEAR_CLAIMS, MONEY_WORDS, [],
         "the number is money, and money is never a year", "year_value"),
    Rule("fallback_journey", JOURNEY_CLAIMS, FALLBACK_WORDS, PRIMARY_JOURNEY_WORDS,
         "this is the journey under some other condition, not the one asked for", None),
]

# The widest a value can be and still be read as a year. bench/grade.py uses the report's
# own generated_at year; here there is no report, so the ceiling is generous on purpose -
# the rule it cancels is about telling a price from a date, and prices are far larger.
YEAR_MIN, YEAR_MAX = 1900, 2200

WORD_SPLIT = re.compile(r"[^a-z0-9]+")


def normalise(text):
    """Lower case, punctuation to single spaces, so word tests are plain substring tests."""
    return " " + " ".join(WORD_SPLIT.split((text or "").lower())).strip() + " "


def _hit(haystack, words):
    """The first word in `words` that appears in the normalised haystack, or None.

    Whole words only. `normalise` pads both ends with a space, so a padded substring
    test is a word-boundary test - which matters: "if" is inside "certificate", and a
    plain substring match would fire the fallback-journey rule on every certificate.
    """
    for word in words:
        if (" " + word + " ") in haystack:
            return word
    return None


def looks_like_a_year(value):
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return False
    return YEAR_MIN <= number <= YEAR_MAX and number == int(number)


def problems(claim, text, flat=None, value=None):
    """[{rule, why, matched}] - the reasons this number is about something else.

    claim  what the number is supposed to be (the evidence item's `claim`)
    text   everything the item says about itself: claim, note, quote, unit, source
    flat   the flat the report is about ("301", "12b"), when it is known. A label that
           names a DIFFERENT flat is the one rule that needs to know which flat we mean.
    value  the number itself, for the one rule that has to look at it: a year quoted
           under a money label is still a year.
    """
    hay_claim = normalise(claim)
    hay = normalise(text)
    out = []
    for rule in RULES:
        if rule.claims and not _hit(hay_claim, rule.claims):
            continue
        matched = _hit(hay, rule.any_of)
        if not matched:
            continue
        if rule.keep_any and _hit(hay, rule.keep_any):
            continue
        if rule.guard == "year_value" and looks_like_a_year(value):
            continue
        out.append({"rule": rule.id, "why": rule.why, "matched": matched})
    # EVERY flat the text names, not just the first: an energy-register search result
    # lists the neighbours, and taking the first would condemn a correct number for
    # flat 301 because flat 201 happens to be printed above it.
    named = FLAT_ID.findall(normalise(text))
    if flat and named and str(flat).strip().lower() not in [n.lower() for n in named]:
        out.append({"rule": "another_flat",
                    "why": "the evidence names flat %s, and the report is about flat %s"
                           % (", ".join(named[:3]), flat),
                    "matched": "flat " + named[0]})
    return out
