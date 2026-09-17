#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grade one vet-flat report.json against the recorded truth for one eval case.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

THE RULE THIS TOOL ENFORCES
===========================
Different models may reach different verdicts. The facts they report must be
correct. Nothing here looks at PASS / EDGE / CONDITIONAL / KILL, at the
headline, or at the tone. A KILL and a PASS on the same flat both score full
marks if the numbers behind them are right.

WHAT IT DOES
============
1. Validates the report with the checker inside ``skills/vet-flat/scripts/render.py``
   (the same one ``render.py`` itself uses), so a report that would not render is
   flagged before anything else.
2. Pulls the graded facts out of the report.
3. Scores five things and prints a JSON scorecard to stdout and one summary line
   to stderr.

THE FIVE SCORES
===============
fact_recall             correct facts / gradeable facts. A fact is gradeable when
                        the case's expected_facts carries a non-null value for it.
fabrications            how many facts were reported with a value that contradicts
                        the truth beyond its tolerance. A count, not a rate. The
                        pass line is zero. A missing fact is NOT a fabrication;
                        an invented one is. Neither is a number of the right KIND
                        about a different THING - see THE REFERENT GUARD below.
citations               of the facts we found a value for, the share whose carrier
                        (the metric, the labelled number, or its axis) cites at
                        least one source id that resolves to an entry in the
                        top-level sources[] with a non-empty url.
unknown_honesty         of the facts that were not reported correctly, the share
                        that the report explicitly marks unknown (a null value, an
                        axis graded U, an unknowns[] line, a not_found[] entry, or a
                        hard filter whose pass is "unknown") instead of leaving a
                        silent hole or filling it with a guess. 1.0 when every fact
                        is correct.
hard_filter_consistency of the hard-filter rows we can check against truth, the
                        share whose ``pass`` agrees with the profile and the
                        observed value.
killer_questions_       of the questions the report puts to the agent, the share
from_bank               that are real: either drawn from
                        ``references/questions.md`` (at least half of the
                        question's own content words appear in a bank question) or
                        naming a landmine or gate code the report itself raised.
                        A report with no killer questions scores zero here. Soft
                        questions - "is it well managed?" - do not count.
gate_questions_present  when the report says it does not know the guarantor route
                        (G1), the availability (G2), the landlord entity (G3) or
                        the deposit protection (G4), it has to ask. See THE
                        QUESTION BANK below.

WHERE THE FACTS ARE LOOKED FOR (the label-matching rules)
=========================================================
Only ``candidates[0]`` is graded: an eval case is one flat.

Order of search, first hit wins:

  (a) ``candidates[0].metrics.<key>.value`` for the three facts the schema gives a
      metric key: crime total -> ``crime_6mo_count``, door-to-door minutes ->
      ``commute_min``, redundancy letter -> ``commute_redundancy_grade``.
      The schema has NO metric key for floor area, assessment year, heating class,
      energy rating or floor position, so those are only ever found in (b)-(d).

  (b) ``candidates[0].axes[].numbers[]``, matched on ``label``. The label is
      lower-cased, punctuation is replaced by spaces and runs of spaces collapse.
      A label matches when EVERY "require" group has at least one of its words in
      the label AND none of the "exclude" words appears. The canonical axis for
      the fact is searched first (floor area -> axis 2, age and rating -> axis 3,
      crime -> axis 5, commute -> axis 11, new-build year -> axis 3), then every
      other axis in order, so a model that files a number under a different axis
      still gets credit.

  (c) free text: the canonical axis's ``finding`` for the two categorical facts
      that have no natural number - heating class and energy rating.

  (d) ``candidates[0].identity.floor`` for the floor position.

  (e) any text anywhere in the candidate for a company number, which is an exact
      string, and for the SIC codes.

Keyword sets per fact are in FACT_RULES below and are printed by ``--explain``.

THE REFERENT GUARD
==================
A label rule finds a number of the right KIND. It cannot tell whether that number
is about the right THING. A report that says the area on the replaced 2010
certificate was 441 sq ft, that the bus takes 49 minutes if the trains stop, that a
flat first sold for GBP 228,000, or that the building is 16 years old is not
claiming that the flat is 441 sq ft, that the train takes 49 minutes, that a sale
happened in the year 228,000, or that its certificate was first written in 2010.
Scored naively, all four read as fabrications.

So before a matched number is graded, REFERENT_RULES asks whether it is about the
fact at hand, and skips it when it plainly is not: a superseded certificate, a
run of dated readings rather than the reading in force, a journey "if" something
else happens, a price where a year is wanted, the building where the flat is
wanted, another flat's number. Where the report's own structure settles it - the
unit, the axis a number sits under, the working in ``computed_by``, the flat named
in ``identity`` - that decides, and the label keywords are the fallback. Every skip
is listed on the card under ``referent_excluded`` with the rule and the evidence, so
the guard can be audited rather than trusted, and ``--explain`` prints the rules.

What the guard never does is excuse a wrong value. A number with the same referent
and a different value is a fabrication exactly as before; no rule reads the truth
to decide whether a value is right. A skipped number leaves the fact MISSING, which
costs recall - so a report cannot buy a pass by mislabelling its numbers.

HOW EACH FACT IS COMPARED
=========================
floor area          units are normalised first. A unit naming metres compares
                    against floor_area_m2 within 0.5 m2; a unit naming feet
                    compares against floor_area_sqft within 6 sq ft (0.5 m2). With
                    no unit, a value under 200 is read as square metres and a value
                    at or over 200 as square feet.
first assessment    a value of 1900 or more is read as a year and must match
year                exactly. A smaller value under a label mentioning age is read
                    as an age in years and is converted with the report's own
                    generated_at year; that path allows +/-1 year for rounding.
heating class       the finding text is classified into one of
                    community_heat_network / heat_pump / gas_boiler / electric by
                    keyword, in that priority order, so "a communal heat network,
                    not a gas boiler" reads as community_heat_network.
energy rating,      exact letter. A plus or a minus is part of the grade, so the
redundancy grade    redundancy grades A, B, B- and C are four different answers.
floor position      ground / basement / top / mid. "3rd of 9", "5th floor" and
                    "mid-floor" all read as mid.
crime total         within tolerance_pct (15%) of the truth for the same window.
commute minutes     within tolerance_min (8) of the truth.
company number      the exact number must appear in the report text. A different
                    company number quoted in axis 7 while the true one is absent
                    counts as a fabrication.
SIC codes           every code in the truth must appear in the report text.
new-build year      exact.

A VERIFIED ABSENCE is graded too. When the certificate carries no property type
the register states no floor, and the truth block records that with
``floor_position_absent``. The report must then leave the floor unknown: stating a
floor for a flat whose certificate does not give one - guessing it from the flat
number, say - counts as a fabrication, not as a lucky guess.

HARD FILTERS
============
Rows are matched to a filter type by keywords in ``name`` + ``requirement``.
Expected values come from the case profile.yaml and the truth, and some are a SET
because more than one answer is defensible:

  floor area     pass == (truth sqft >= profile min sqft).                 one answer
  building age   an EPC year is a LOWER BOUND on the building's age: the
                 building is at least that old and may be much older. So when
                 the implied age is inside the limit, both true and "unknown"
                 are consistent; when the implied age already exceeds the limit
                 the answer can only be false.
  ground floor   pass == (truth floor position is not ground or basement).
                 Ungraded when the certificate states no property type.
  commute        true when the journey plus tolerance is inside the ceiling,
                 false when it minus tolerance is outside, otherwise any answer.
  cost, must-haves, move-in: not graded - the benchmark holds no truth for them.

A gradeable filter that the report does not list at all counts as inconsistent.

CONVERSATION CASES
==================
Two cases in the suite are not reports at all: they are the answer a user gets
when they ask what the skill does, or say they have no idea where to start. Those
answers still state facts - how many checks there are, the four verdict words, the
legal caps on a deposit - and a wrong one there is as bad as a wrong floor area.
They are graded by named pass/fail checks listed in the case's
``expected_facts.answer_checks``; ``grade.py`` reads the file as plain text instead
of JSON, ``fact_recall`` becomes checks passed over checks that applied, and a
check marked ``fabrication_on_fail`` counts towards ``fabrications``. A check may
also return "skipped": a legal cap the answer never mentions is not a failure, but
if it is mentioned it must be right. A check marked ``critical`` (asking about
nationality or ethnicity, for instance) blocks the pass line on its own.
Citations, unknown honesty and hard filters do not apply and come back null.

Usage:
  bench/grade.py report.json --case e14-marsh-wall-301
  bench/grade.py report.json --case e14-marsh-wall-301 --json-out score.json
  bench/grade.py answer.txt --case explain-capabilities --variant zh
  bench/grade.py --explain                       # print the matching rules and stop

Exit codes: 0 graded, 1 the report failed schema validation or could not be read,
2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
REFS = os.path.join(ROOT, "skills", "vet-flat", "references")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")
SCHEMA_PATH = os.path.join(REFS, "report-schema.json")

sys.path.insert(0, SCRIPTS)
import render  # noqa: E402  the repository's own schema checker
import referents  # noqa: E402  the shared referent word lists (skills/vet-flat/scripts)

class Absent(object):
    """The register was read and it states nothing. Not the same as 'we did not look'.

    A fact marked absent is still graded: the report must leave it unknown. Stating a
    value for something the official record does not carry is an invention, which is
    exactly what a floor guessed from a flat number is.
    """

    def __repr__(self):
        return "<verified absence>"


ABSENT = Absent()

SQFT_PER_M2 = 10.7639
AREA_TOL_M2 = 0.5
AREA_TOL_SQFT = 6

PASS_LINE = {"stable_fact_recall": 0.95, "fabrications": 0, "citations": 1.0}

# Facts whose truth does not move month to month. The pass line is set on these.
STABLE_FACTS = ("epc.floor_area_m2", "epc.first_assessment_year", "epc.heating_class",
                "epc.floor_position", "epc.energy_rating", "commute.redundancy_grade",
                "company.company_number", "company.sic_codes",
                "landregistry.earliest_new_build_year")


# --------------------------------------------------------------- label rules --
# require: list of groups; the label must contain a word from EVERY group.
# exclude: any of these words disqualifies the label.
FACT_RULES = collections.OrderedDict([
    ("epc.floor_area_m2", dict(
        axis=2, metric=None,
        unknown_words=["floor area", "internal area", "indoor area"],
        require=[["floor area", "internal area", "indoor area", "usable area", "area"]],
        exclude=["advertised", "advert", "listing", "listed", "brochure", "claimed",
                 "marketing", "floor plan", "balcony", "terrace", "external", "gross",
                 "per square", "psf", "price"],
        kind="area")),
    ("epc.first_assessment_year", dict(
        axis=3, metric=None,
        unknown_words=["assessment year", "first assessment", "building age", "age of the building",
                       "completion year", "year built", "year the building"],
        require=[["assessment", "certificate", "epc", "energy", "built", "completion", "age"],
                 ["year", "date", "age", "first"]],
        exclude=["valid", "expiry", "expires", "new build", "new-build", "land registry",
                 "sale", "sold"],
        kind="year")),
    ("epc.energy_rating", dict(
        axis=3, metric=None,
        unknown_words=["energy rating", "epc rating", "energy certificate rating"],
        require=[["energy rating", "epc rating", "efficiency rating", "rating"]],
        exclude=["potential", "review", "management", "score of 5", "out of 5",
                 "resident", "star", "crime", "landlord"],
        kind="letter", letters="ABCDEFG",
        text_patterns=[r"energy rating (?:is |of )?[\"'\u201c]?([A-G])\b",
                       r"\b(?:EPC|certificate) (?:rating|band) (?:is |of )?[\"'\u201c]?([A-G])\b",
                       r"\brated ([A-G])\b",
                       r"\bband ([A-G])\b"])),
    ("epc.heating_class", dict(
        axis=3, metric=None, require=None, exclude=None, kind="heating",
        unknown_words=["heating", "heat network", "main heating", "how it is heated"])),
    ("epc.floor_position", dict(
        axis=1, metric=None, require=None, exclude=None, kind="floor_position",
        unknown_words=["floor position", "which floor", "floor of the flat", "storey",
                       "property type"])),
    ("crime.total", dict(
        axis=5, metric="crime_6mo_count",
        unknown_words=["crime", "recorded crime", "police"],
        require=[["crime", "crimes", "offence", "offences", "incident", "incidents"]],
        exclude=["per month", "monthly", "route", "corridor", "walk", "predatory",
                 "against people", "anti social", "anti-social", "share", "percent"],
        kind="count")),
    ("commute.all_min", dict(
        axis=11, metric="commute_min",
        unknown_words=["door to door", "commute", "journey time"],
        require=[["door", "journey", "commute", "travel", "trip"]],
        exclude=["rail only", "rail-only", "bus", "walk", "walking", "wait", "buffer"],
        kind="minutes")),
    ("commute.rail_min", dict(
        axis=11, metric=None,
        unknown_words=["rail journey", "rail only", "rail-only"],
        require=[["rail", "train", "tube"], ["min", "journey", "only", "time", "door"]],
        exclude=["bus", "walk", "walking"],
        kind="minutes")),
    ("commute.redundancy_grade", dict(
        axis=11, metric="commute_redundancy_grade",
        unknown_words=["redundancy", "strike", "second line"],
        require=[["redundancy", "backup", "back up", "strike", "resilience", "grade"]],
        exclude=[], kind="letter", letters="ABCU",
        text_patterns=[r"redundancy grade (?:is |of )?[\"'\u201c]?([ABCU])\s*([+-]?)",
                       r"\bgrade ([ABCU])\s*([+-]?)"])),
    ("company.company_number", dict(
        axis=7, metric=None, require=None, exclude=None, kind="company_number",
        unknown_words=["company number", "companies house", "legal entity",
                       "landlord entity", "who owns"])),
    ("company.sic_codes", dict(
        axis=7, metric=None, require=None, exclude=None, kind="sic_codes",
        unknown_words=["sic code", "companies house", "what the company does"])),
    ("landregistry.earliest_new_build_year", dict(
        axis=3, metric=None,
        unknown_words=["new build", "land registry", "price paid", "first sale"],
        require=[["new build", "new-build", "newbuild", "first sale", "land registry",
                  "price paid"], ["year", "sale", "date", "registry", "build"]],
        exclude=["assessment", "certificate"],
        kind="year")),
])

# The report is written in plain language on purpose, so these lists carry the plain
# phrasings as well as the technical ones. First class to match wins, so
# "a communal heat network, not a boiler in the flat" reads as a heat network.
HEATING_KEYWORDS = collections.OrderedDict([
    ("community_heat_network", ["communal heat", "community heat", "communal scheme",
                                "community scheme", "district heat", "heat network",
                                "heat interface", "communal boiler", "shared heating",
                                "communal heating", "district heating", "shared hot water",
                                "building wide", "whole building", "building system",
                                "building's system", "one system for the building",
                                "central plant", "estate heating", "heat station"]),
    ("heat_pump", ["heat pump", "air source", "air-source", "ground source", "ground-source"]),
    ("gas_boiler", ["gas boiler", "mains gas", "gas-fired", "gas fired", "gas central",
                    "boiler and radiators", "combi boiler", "boiler in the flat",
                    "own boiler", "gas supply for heating"]),
    ("electric", ["storage heater", "electric heating", "electric heater", "panel heater",
                  "direct electric", "electric radiator", "night storage", "all electric",
                  "electricity for heating", "immersion"]),
])

FILTER_RULES = collections.OrderedDict([
    ("area", dict(any_of=["floor area", "area", "square feet", "square metre", "size"],
                  none_of=["outdoor", "balcony", "terrace"])),
    ("age", dict(any_of=["age", "built", "old", "year of construction", "construction year"],
                 none_of=[])),
    ("ground_floor", dict(any_of=["ground floor", "ground-floor", "floor", "storey"],
                          none_of=["area", "plan"])),
    ("commute", dict(any_of=["commute", "journey", "door to door", "door-to-door", "travel"],
                     none_of=[])),
])


# ------------------------------------------------------------------ helpers --
def norm(text):
    """Lower-case, punctuation to spaces, runs of spaces collapsed."""
    if text is None:
        return ""
    text = str(text).lower().replace("²", "2").replace("’", "'")
    text = re.sub(r"[^a-z0-9'%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def label_matches(label, rule):
    """True when every require group is present and no exclude word is."""
    text = " " + norm(label) + " "
    for word in (rule.get("exclude") or []):
        if " " + norm(word) + " " in text or norm(word) in text:
            return False
    for group in (rule.get("require") or []):
        # whole words: "age" must not match "average" (a road-noise label once graded as a build year)
        if not any(re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(norm(w)), text) for w in group):
            return False
    return True


def as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"-?\d[\d,]*(?:\.\d+)?", value)
        if m:
            try:
                return float(m.group(0).replace(",", ""))
            except ValueError:
                return None
    return None


def candidate_text(cand):
    """Every string in the candidate, flattened, for exact-string checks."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, str):
            out.append(node)
    walk(cand)
    return "\n".join(out)


def axis_by_id(cand, axis_id):
    for axis in cand.get("axes") or []:
        if isinstance(axis, dict) and axis.get("id") == axis_id:
            return axis
    return None


def report_year(report):
    stamp = report.get("generated_at") or ""
    m = re.match(r"(\d{4})", str(stamp))
    if m:
        return int(m.group(1))
    return datetime.datetime.utcnow().year


# ----------------------------------------------------------- referent guard --
# A number can be of the right KIND and about the wrong THING: the area on a
# certificate that has since been replaced, the bus you would take IF the trains
# stopped, the PRICE a flat sold for rather than the YEAR it sold, the age of the
# building rather than the date on this flat's certificate. None of those is a
# fabrication - the report is answering a different question, usually openly and
# usefully - so they are skipped by the fact search and listed on the card under
# ``referent_excluded``, with the rule and the evidence, for a maintainer to audit.
#
# Two rules keep the guard honest:
#
#   * The report's own structure decides wherever it speaks: the unit (money is
#     never a year), the axis a number sits under, the flat named in ``identity``,
#     the working shown in ``computed_by``. Label keywords are the fallback, and a
#     rule may read any field of the number, the names of its sources included.
#   * A number with the SAME referent and a different value is STILL a fabrication.
#     Nothing here excludes a number for being wrong, only for being about
#     something else. No rule reads the truth to decide whether a value is right.
#
# The metric slots (``candidates[0].metrics.*``) are never guarded. The schema
# gives one metric key per fact, so a value sitting in it is the report's own answer
# to that fact and cannot be about something else: a crime count in
# ``crime_6mo_count`` counted over a wider box than the method asks for is a wrong
# count, not a different question.

# The word lists below are shared with the skill's own verifier and live in
# skills/vet-flat/scripts/referents.py, so the grader and scripts/verify.py can never
# drift apart. tests/test_verify.py asserts they agree.
# The label says this reading has been superseded.
HISTORICAL_WORDS = referents.HISTORICAL_WORDS
# ... unless it also says this is the reading in force now.
CURRENT_WORDS = referents.CURRENT_WORDS
# A journey that is not the one the profile asks for: the fallback, the diversion,
# the strike plan, the weekend.
FALLBACK_WORDS = referents.FALLBACK_WORDS
# ... unless the label names the very journey the fact asks for.
PRIMARY_JOURNEY_WORDS = referents.PRIMARY_JOURNEY_WORDS
# Money. A price is never a year.
MONEY_WORDS = referents.MONEY_WORDS
# The certificate register, as opposed to the price register or the planning register.
CERTIFICATE_WORDS = referents.CERTIFICATE_WORDS
# The landlord's registered number is not a date. FACT_RULES matches labels by plain
# substring, so "age" is inside "management" and a company row can match a year rule.
COMPANY_WORDS = referents.COMPANY_WORDS
# The age of the building is not the date on the flat's certificate.
BUILDING_AGE_WORDS = referents.BUILDING_AGE_WORDS
# Something measured over the whole building rather than inside this flat ...
BUILDING_WORDS = referents.BUILDING_WORDS
# ... unless the label says it is the flat's.
FLAT_WORDS = referents.FLAT_WORDS

FLAT_ID = referents.FLAT_ID

# Per fact: the referents this fact is NOT about. A rule triggers either on keywords
# (any_of, in fields) or on a named test method of ReferentGuard, for the referents
# keywords alone cannot see. Either way keep_any, in keep_fields, cancels it: the
# report has said this IS the number the fact asks for.
REFERENT_RULES = collections.OrderedDict([
    ("epc.floor_area_m2", [
        dict(rule="a superseded certificate",
             fields=("label",), any_of=HISTORICAL_WORDS,
             keep_fields=("label", "computed_by"), keep_any=CURRENT_WORDS,
             why="this area is on a certificate the report itself marks as replaced"),
        dict(rule="the building, not the flat",
             fields=("label",), any_of=BUILDING_WORDS,
             keep_fields=("label",), keep_any=FLAT_WORDS,
             why="the area is measured over the building, not inside this flat"),
        dict(rule="another flat", test="another_flat",
             why="the label names a different flat"),
    ]),
    ("epc.energy_rating", [
        dict(rule="a superseded certificate",
             fields=("label",), any_of=HISTORICAL_WORDS,
             keep_fields=("label", "computed_by"), keep_any=CURRENT_WORDS,
             why="this rating is on a certificate the report itself marks as replaced"),
        dict(rule="a series, not a rating", test="series_value",
             keep_fields=("label", "computed_by"), keep_any=CURRENT_WORDS,
             why="the value is a run of dated readings, not the rating in force"),
        dict(rule="another flat", test="another_flat",
             why="the label names a different flat"),
    ]),
    ("epc.first_assessment_year", [
        dict(rule="the building's age, not the certificate's date",
             test="building_age_not_certificate",
             why="the number dates the building rather than this flat's certificate"),
        dict(rule="the landlord, not the certificate",
             fields=("label", "axis_name"), any_of=COMPANY_WORDS,
             keep_fields=("label",), keep_any=CERTIFICATE_WORDS,
             why="the number belongs to a company, not to a certificate"),
        dict(rule="a price, not a year", test="money_not_a_year",
             why="the number is money, and money is never a year"),
        dict(rule="a series, not a year", test="series_value",
             keep_fields=("label", "computed_by"), keep_any=CURRENT_WORDS,
             why="the value is a run of dated readings, not one assessment year"),
        dict(rule="another flat", test="another_flat",
             why="the label names a different flat"),
    ]),
    ("commute.all_min", [
        dict(rule="a fallback journey",
             fields=("label",), any_of=FALLBACK_WORDS,
             keep_fields=("label",), keep_any=PRIMARY_JOURNEY_WORDS,
             why="this is the journey under some other condition, not the one the "
                 "profile asks for"),
    ]),
    ("commute.rail_min", [
        dict(rule="a fallback journey",
             fields=("label",), any_of=FALLBACK_WORDS,
             keep_fields=("label",), keep_any=PRIMARY_JOURNEY_WORDS,
             why="this is the journey under some other condition, not the primary "
                 "rail time"),
    ]),
    ("landregistry.earliest_new_build_year", [
        dict(rule="a price, not a year", test="money_not_a_year",
             why="the number is a sale price in pounds, not the year of a sale"),
        dict(rule="another flat", test="another_flat",
             why="the label names a different flat"),
    ]),
])


def phrase_in(text, phrase):
    """Whole-word containment, on text that has already been through norm()."""
    if not text:
        return False
    return (" " + text + " ").find(" " + norm(phrase) + " ") >= 0


def any_phrase(ctx, fields, words):
    """The first (field, phrase) that hits, or None."""
    for field in fields or ():
        for word in words or ():
            if phrase_in(ctx.get(field), word):
                return (field, word)
    return None


def cite(hit):
    return '"%s" in the %s' % (hit[1], hit[0].replace("_", " "))


def flat_id(text):
    m = FLAT_ID.search(norm(text))
    return m.group(1) if m else None


def as_year(value):
    num = as_number(value)
    return int(num) if num is not None and 1800 <= num <= 2200 else None


class ReferentGuard(object):
    """Is this number of the right kind about the right thing?

    Built once per report. ``check`` returns a reason to skip a number, or None to
    grade it, and every skip is remembered in ``excluded`` for the scorecard.
    """

    def __init__(self, report, facts):
        self.report = report or {}
        self.facts = facts or {}
        self.year = report_year(self.report)
        cands = self.report.get("candidates") or []
        cand = cands[0] if cands and isinstance(cands[0], dict) else {}
        self.subject_flat = flat_id((cand.get("identity") or {}).get("flat"))
        self.names = {}
        for src in (self.report.get("sources") or []):
            if isinstance(src, dict) and src.get("id"):
                self.names[src["id"]] = src.get("name") or ""
        self.excluded = []

    def context(self, axis, num):
        """Everything a rule may read about one number, normalised."""
        srcs = num.get("sources") or (axis or {}).get("sources") or []
        return {
            "label": norm(num.get("label")),
            "unit": norm(num.get("unit")),
            "value": norm(num.get("value")),
            "meaning": norm(num.get("meaning")),
            "compared_to": norm(num.get("compared_to")),
            "computed_by": norm(num.get("computed_by")),
            "source_names": norm(" ".join(self.names.get(s, "") for s in srcs
                                          if isinstance(s, str))),
            "axis_name": norm((axis or {}).get("name")),
        }

    def check(self, fact, axis, num, where):
        """A reason to skip this number, or None. Skips are recorded."""
        rules = REFERENT_RULES.get(fact) or []
        if not rules or not isinstance(num, dict):
            return None
        ctx = self.context(axis, num)
        for spec in rules:
            if spec.get("test"):
                evidence = getattr(self, spec["test"])(ctx, num)
            else:
                hit = any_phrase(ctx, spec.get("fields"), spec.get("any_of"))
                evidence = cite(hit) if hit else None
            if not evidence:
                continue
            if any_phrase(ctx, spec.get("keep_fields"), spec.get("keep_any")):
                continue                     # the report says this IS the wanted one
            reason = "%s: %s (%s)" % (spec["rule"], spec["why"], evidence)
            self.excluded.append(collections.OrderedDict([
                ("fact", fact), ("where", where), ("label", num.get("label")),
                ("value", num.get("value")), ("unit", num.get("unit")),
                ("rule", spec["rule"]), ("reason", reason)]))
            return reason
        return None

    # ------------------------------------------------- tests a rule can name --
    def implied_year(self, num):
        """The year this number states, whether written as a year or as an age."""
        value = as_number(num.get("value"))
        if value is None:
            return None
        return int(value) if value >= 1900 else self.year - int(value)

    def money_not_a_year(self, ctx, num):
        hit = any_phrase(ctx, ("unit", "label"), MONEY_WORDS)
        if not hit:
            return None
        value = as_number(num.get("value"))
        if value is not None and 1900 <= value <= self.year + 1:
            return None          # a year quoted under a money label is still a year
        return "%s, and the value is not a year" % cite(hit)

    def series_value(self, ctx, num):
        raw = str(num.get("value") if num.get("value") is not None else "")
        years = re.findall(r"\b(?:19|20)\d{2}\b", raw)
        grades = re.findall(r"\b[A-G]\b", raw.upper())
        readings = max(len(years), len(grades))
        if readings < 2:
            return None
        return "the value carries %d readings, not one" % readings

    def building_age_not_certificate(self, ctx, num):
        """The age of the building is not always the date on the flat's certificate.

        Dating a building from its first certificate is the normal, graded case: for
        most blocks the two coincide, the report means the one when it writes the
        other, and nothing here interferes. The two part company when a flat is
        re-certified long after it was built - The Printworks sold new in 2010 and
        this flat's certificate was first written in 2022 - and a report that says
        "building age: 16 years" is then plainly dating the building, which is what
        the Land Registry fact next door is for.

        So this fires only when the register's own two dates disagree AND the number
        lands on the building's completion rather than on the certificate. The truth
        is read to tell two referents apart, never to decide whether a value is
        right: a building-age number that lands on neither date is graded and counts
        as a fabrication exactly as before.
        """
        hit = any_phrase(ctx, ("label",), BUILDING_AGE_WORDS)
        if not hit:
            return None
        built = as_year((self.facts.get("landregistry") or {}).get("earliest_new_build_year"))
        assessed = as_year((self.facts.get("epc") or {}).get("first_assessment_year"))
        year = self.implied_year(num)
        if (built is None or assessed is None or year is None
                or abs(built - assessed) <= 1
                or abs(year - built) > 1 or abs(year - assessed) <= 1):
            return None
        return ("%s: the building sold new in %d and the certificate was first assessed "
                "in %d, and this number dates the building" % (cite(hit), built, assessed))

    def another_flat(self, ctx, num):
        named = flat_id(ctx["label"])
        if self.subject_flat and named and named != self.subject_flat:
            return "the label names flat %s, and this case is flat %s" % (
                named, self.subject_flat)
        return None


# ------------------------------------------------------------- finding a fact --
Found = collections.namedtuple("Found", "value unit where sources axis_id explicit_null")


def find_in_numbers(cand, rule, guard=None, fact=None, every=False):
    """Search axes[].numbers[] by label, canonical axis first, then the rest.

    A ``guard`` skips numbers whose label matches but whose referent is something
    else; without one, every label match is graded, which is how the finders behave
    when called on their own.
    """
    axes = [a for a in (cand.get("axes") or []) if isinstance(a, dict)]
    ordered = ([a for a in axes if a.get("id") == rule.get("axis")] +
               [a for a in axes if a.get("id") != rule.get("axis")])
    null_hit = None
    hits = []
    for axis in ordered:
        for i, num in enumerate(axis.get("numbers") or []):
            if not isinstance(num, dict) or not label_matches(num.get("label"), rule):
                continue
            where = "candidates[0].axes[id=%s].numbers[%d] (%s)" % (
                axis.get("id"), i, num.get("label"))
            if guard is not None and guard.check(fact, axis, num, where):
                continue
            srcs = num.get("sources") or axis.get("sources") or []
            if num.get("value") is None:
                null_hit = null_hit or Found(None, num.get("unit"), where, srcs,
                                             axis.get("id"), True)
                continue
            found = Found(num.get("value"), num.get("unit"), where, srcs, axis.get("id"), False)
            if every:
                hits.append(found)
                continue
            return found
    if every:
        return hits + ([null_hit] if null_hit and not hits else [])
    return null_hit


def find_in_metric(cand, key):
    metrics = cand.get("metrics") or {}
    m = metrics.get(key)
    if not isinstance(m, dict):
        return None
    where = "candidates[0].metrics.%s" % key
    return Found(m.get("value"), m.get("unit"), where, m.get("sources") or [], None,
                 m.get("value") is None)


NEGATION_BEFORE = re.compile(r"(?:\bnot\b|\bno\b|\bnever\b|\bwithout\b|\brather than\b|\binstead of\b|\bisn't\b|\bis not\b|\bnot a\b|\bnot on a\b)[^.;]{0,30}$")


def classify_heating(text):
    """The heating class a text names, in priority order, ignoring a class it denies
    ("a gas boiler with radiators, not a heat network" is gas_boiler)."""
    low = norm(text)
    for cls, words in HEATING_KEYWORDS.items():
        for w in words:
            for m in re.finditer(re.escape(norm(w)), low):
                if not NEGATION_BEFORE.search(low[max(0, m.start() - 40):m.start()]):
                    return cls
    return None


def classify_floor_position(text, bare_number_counts=True):
    """ground / basement / top / mid from a phrase.

    `bare_number_counts` is True for identity.floor, a field whose whole job is to
    hold the floor, so "3rd of 9" means the third floor. It is False for free
    prose, where a lone number is far more likely to be a flat number, a year or a
    distance: there the text has to say "floor" or "storey" for a number to count.
    """
    low = norm(text)
    if not low:
        return None
    if "basement" in low or "lower ground" in low:
        return "basement"
    if re.search(r"\bground\b", low):
        return "ground"
    if re.search(r"\btop\b", low) or "penthouse" in low:
        return "top"
    if re.search(r"\bmid\b", low) or "mid floor" in low or "middle" in low:
        return "mid"
    if bare_number_counts:
        m = re.search(r"\b(\d+)\s*(?:st|nd|rd|th)?\b", low)
    else:
        m = (re.search(r"\b(\d+)\s*(?:st|nd|rd|th)?\s+(?:floor|storey|story)\b", low)
             or re.search(r"\b(?:floor|storey|story)\s+(\d+)\b", low))
    if m and int(m.group(1)) > 0:
        return "mid"
    return None


def looks_unknown(text):
    low = norm(text)
    return bool(low) and any(w in low for w in
                             ["unknown", "not known", "not stated", "no property type",
                              "could not", "not found", "not recorded", "does not say",
                              "not confirmed", "no data", "nothing found"])


def read_letter(raw, letters):
    """'B', 'b-', 'Grade B minus' -> 'B' / 'B-'. The plus and minus are part of the grade."""
    if raw is None:
        return None
    text = str(raw).strip()
    m = re.match(r"\s*(?:grade\s+)?([A-Za-z])\b\s*(\+|-|plus\b|minus\b)?", text, re.I)
    if not m or m.group(1).upper() not in letters:
        return None
    tail = (m.group(2) or "").lower()
    suffix = "+" if tail in ("+", "plus") else "-" if tail in ("-", "minus") else ""
    return m.group(1).upper() + suffix


def find_letter(cand, rule, guard=None, fact=None):
    """A single letter grade, from a labelled number first, then the axis finding text."""
    letters = rule.get("letters", "")
    hit = find_in_numbers(cand, rule, guard, fact)
    if hit and hit.value is not None:
        letter = read_letter(hit.value, letters)
        if letter:
            return hit._replace(value=letter)
    axis = axis_by_id(cand, rule.get("axis"))
    if axis:
        raw = str(axis.get("finding") or "")
        # collapse whitespace only: the +/- on a grade must survive
        raw = re.sub(r"\s+", " ", raw)
        for pattern in rule.get("text_patterns") or []:
            m = re.search(pattern, raw, re.I)
            if not m:
                continue
            letter = read_letter("".join(g for g in m.groups() if g), letters)
            if letter:
                return Found(letter, None,
                             "candidates[0].axes[id=%s].finding" % axis.get("id"),
                             axis.get("sources") or [], axis.get("id"), False)
    # A number that is not a letter (a review score, say) is not an answer to this
    # question; only an explicit null is carried through, so it can count as an
    # honest unknown rather than as an invented grade.
    return hit if (hit is not None and hit.value is None) else None


def find_fact(cand, fact, rule, truth, guard=None):
    """Return a Found for this fact, or None when the report says nothing about it.

    ``guard`` is a ReferentGuard: a number of the right kind about a different thing
    is skipped here rather than graded as a wrong value.
    """
    kind = rule["kind"]
    if rule.get("metric"):
        hit = find_in_metric(cand, rule["metric"])
        if hit and hit.value is not None:
            return hit
        metric_null = hit
    else:
        metric_null = None

    if kind == "area":
        hits = find_in_numbers(cand, rule, guard, fact, every=True)
        real = [h for h in hits if h.value is not None]
        if len(real) > 1 and isinstance(truth, dict):
            # Two certificates listed side by side, disagreeing, is honest reporting: grade the one
            # that is the current record when it is there, and say so.
            for h in real:
                if compare(fact, rule, h, truth, None)[0] == "correct":
                    return h._replace(where=h.where + " [one of %d listed areas]" % len(real))
        return (real[0] if real else (hits[0] if hits else None)) or metric_null
    if kind in ("year", "count", "minutes"):
        hit = find_in_numbers(cand, rule, guard, fact)
        return hit or metric_null

    if kind == "letter":
        return find_letter(cand, rule, guard, fact) or metric_null

    if kind == "heating":
        axis = axis_by_id(cand, 3)
        blobs = []
        if axis:
            blobs.append(("candidates[0].axes[id=3].finding", axis.get("finding"),
                          axis.get("sources") or [], 3))
            for i, num in enumerate(axis.get("numbers") or []):
                blobs.append(("candidates[0].axes[id=3].numbers[%d]" % i,
                              "%s %s" % (num.get("label"), num.get("value")),
                              num.get("sources") or axis.get("sources") or [], 3))
        axis10 = axis_by_id(cand, 10)
        if axis10:
            blobs.append(("candidates[0].axes[id=10].finding", axis10.get("finding"),
                          axis10.get("sources") or [], 10))
        for where, text, srcs, aid in blobs:
            cls = classify_heating(text)
            if cls:
                return Found(cls, None, where, srcs, aid, False)
        return None

    if kind == "floor_position":
        ident = cand.get("identity") or {}
        axis1 = axis_by_id(cand, 1)
        srcs1 = (axis1 or {}).get("sources") or []
        if ident.get("floor") is not None:
            pos = classify_floor_position(ident.get("floor"))
            if pos:
                return Found(pos, None, "candidates[0].identity.floor", srcs1, 1, False)
            if looks_unknown(ident.get("floor")):
                return Found(None, None, "candidates[0].identity.floor", srcs1, 1, True)
        for aid in (1, 2, 9):
            axis = axis_by_id(cand, aid)
            if not axis:
                continue
            pos = classify_floor_position(axis.get("finding"), bare_number_counts=False)
            if pos:
                return Found(pos, None, "candidates[0].axes[id=%d].finding" % aid,
                             axis.get("sources") or [], aid, False)
        return None

    if kind == "company_number":
        text = candidate_text(cand)
        want = str(truth)
        if want and want in text:
            axis7 = axis_by_id(cand, 7)
            return Found(want, None, "candidates[0] text", (axis7 or {}).get("sources") or [],
                         7, False)
        axis7 = axis_by_id(cand, 7)
        blob = " ".join([str((axis7 or {}).get("finding") or "")] +
                        [str(n.get("value")) for n in ((axis7 or {}).get("numbers") or [])])
        m = re.search(r"\b((?:[A-Z]{2})?\d{6,8})\b", blob)
        if m:
            return Found(m.group(1), None, "candidates[0].axes[id=7]",
                         (axis7 or {}).get("sources") or [], 7, False)
        return None

    if kind == "sic_codes":
        text = candidate_text(cand)
        codes = list(truth or [])
        if not codes:
            return None
        present = [c for c in codes if str(c) in text]
        if not present:
            return None
        axis7 = axis_by_id(cand, 7)
        return Found(present, None, "candidates[0] text",
                     (axis7 or {}).get("sources") or [], 7, False)
    return None


# ------------------------------------------------------------------ compare --
def compare(fact, rule, found, truth, report):
    """Return (status, detail). status is 'correct', 'wrong' or 'missing'."""
    kind = rule["kind"]
    value = found.value

    if kind == "area":
        unit = norm(found.unit)
        num = as_number(value)
        if num is None:
            return "missing", "no number"
        metric = any(w in unit for w in ["metre", "meter", "m2", "sq m", "sqm"])
        imperial = any(w in unit for w in ["foot", "feet", "sqft", "sq ft", "ft2"])
        if not metric and not imperial:
            metric = num < 200
            imperial = not metric
        if metric:
            ok = abs(num - float(truth["floor_area_m2"])) <= AREA_TOL_M2
            return ("correct" if ok else "wrong",
                    "%.1f m2 against %.1f m2 (tolerance %.1f)" %
                    (num, truth["floor_area_m2"], AREA_TOL_M2))
        ok = abs(num - float(truth["floor_area_sqft"])) <= AREA_TOL_SQFT
        return ("correct" if ok else "wrong",
                "%.0f sq ft against %d sq ft (tolerance %d)" %
                (num, truth["floor_area_sqft"], AREA_TOL_SQFT))

    if kind == "year":
        num = as_number(value)
        if num is None:
            return "missing", "no number"
        want = int(truth)
        if num >= 1900:
            return ("correct" if int(num) == want else "wrong",
                    "%d against %d (exact)" % (int(num), want))
        derived = report_year(report) - int(num)
        return ("correct" if abs(derived - want) <= 1 else "wrong",
                "an age of %d years in a %d report implies %d, against %d (+/-1)" %
                (int(num), report_year(report), derived, want))

    if kind in ("count", "minutes"):
        num = as_number(value)
        if num is None:
            return "missing", "no number"
        if kind == "count":
            tol = float(truth["tolerance_pct"]) / 100.0 * float(truth["value"])
            want = float(truth["value"])
            return ("correct" if abs(num - want) <= tol else "wrong",
                    "%.0f against %.0f (tolerance %.0f, %.0f%%)" %
                    (num, want, tol, truth["tolerance_pct"]))
        tol = float(truth["tolerance_min"])
        want = float(truth["value"])
        return ("correct" if abs(num - want) <= tol else "wrong",
                "%.0f min against %.0f min (tolerance %.0f min)" % (num, want, tol))

    if kind in ("letter", "heating", "floor_position", "company_number"):
        if value is None:
            return "missing", "no value"
        ok = str(value).strip().upper() == str(truth).strip().upper()
        if not ok and fact == "commute.redundancy_grade" and str(value).strip()[:1].upper() == str(truth).strip()[:1].upper():
            # commute.py itself grades B- as a shade of B; a walk of a few metres flips the modifier
            return "correct", "%r against %r (same letter; the modifier is a threshold shade)" % (value, truth)
        return ("correct" if ok else "wrong", "%r against %r (exact)" % (value, truth))

    if kind == "sic_codes":
        want = [str(c) for c in (truth or [])]
        got = [str(c) for c in (value or [])]
        missing = [c for c in want if c not in got]
        return ("correct" if not missing else "wrong",
                "found %s of %s" % (got or "none", want))

    return "missing", "no rule"


# ---------------------------------------------------------------- unknowns --
def marked_unknown(cand, report, fact, rule, found):
    """Did the report say plainly that it could not get this fact?"""
    if found is not None and found.explicit_null:
        return True, found.where + " is null"
    axis = axis_by_id(cand, rule.get("axis"))
    words = rule.get("unknown_words") or []
    if axis:
        if axis.get("evidence_class") == "U":
            return True, "axis %s is graded unknown" % axis.get("id")
        for line in axis.get("unknowns") or []:
            if any(norm(w) in norm(line) for w in words):
                return True, "axis %s unknowns: %s" % (axis.get("id"), line)
    for entry in report.get("not_found") or []:
        if not isinstance(entry, dict):
            continue
        if any(norm(w) in norm(entry.get("what")) for w in words):
            return True, "not_found: %s" % entry.get("what")
    for row in cand.get("hard_filters") or []:
        if not isinstance(row, dict) or row.get("pass") != "unknown":
            continue
        blob = "%s %s" % (row.get("name"), row.get("requirement"))
        if any(norm(w) in norm(blob) for w in words):
            return True, "hard filter %r is unknown" % row.get("name")
    return False, None


# ------------------------------------------------------------ hard filters --
PROFILE_KEYS = {
    "min_floor_area_sqft": r"^\s*min_floor_area_sqft\s*:\s*([0-9.]+)",
    "max_building_age_years": r"^\s*max_building_age_years\s*:\s*([0-9.]+)",
    "all_in_pcm_ceiling": r"^\s*all_in_pcm_ceiling\s*:\s*([0-9.]+)",
    "max_door_to_door_min": r"^\s*max_door_to_door_min\s*:\s*([0-9.]+)",
    "reject_ground_floor": r"^\s*reject_ground_floor\s*:\s*(true|false)",
}


def read_profile(path):
    """A deliberately small reader for the eval profiles, which have a fixed shape."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with io.open(path, encoding="utf-8") as fh:
        text = fh.read()
    for key, pattern in PROFILE_KEYS.items():
        m = re.search(pattern, text, re.M)
        if not m:
            continue
        raw = m.group(1)
        out[key] = (raw == "true") if raw in ("true", "false") else float(raw)
    m = re.search(r"^\s*destination\s*:\s*[\"']?([^\"'\n]+)", text, re.M)
    if m:
        out["commute_destination"] = m.group(1).strip()
    return out


def filter_kind(row):
    blob = norm("%s %s" % (row.get("name"), row.get("requirement")))
    for kind, rule in FILTER_RULES.items():
        if any(norm(w) in blob for w in rule["any_of"]) and \
           not any(norm(w) in blob for w in rule["none_of"]):
            return kind
    return None


def expected_filters(profile, facts, report):
    """{kind: (set of acceptable pass values, the sentence that explains why)}."""
    out = collections.OrderedDict()
    epc = facts.get("epc") or {}
    commute = facts.get("commute") or {}

    if epc.get("floor_area_sqft") is not None and profile.get("min_floor_area_sqft") is not None:
        ok = float(epc["floor_area_sqft"]) >= float(profile["min_floor_area_sqft"])
        out["area"] = ({ok}, "%d sq ft on the certificate against a floor of %d sq ft"
                       % (epc["floor_area_sqft"], profile["min_floor_area_sqft"]))

    if epc.get("first_assessment_year") and profile.get("max_building_age_years") is not None:
        age = report_year(report) - int(epc["first_assessment_year"])
        limit = float(profile["max_building_age_years"])
        if age > limit:
            out["age"] = ({False},
                          "the first assessment was %d, so the building is at least %d years "
                          "old, past the %d-year limit"
                          % (epc["first_assessment_year"], age, limit))
        else:
            out["age"] = ({True, "unknown"},
                          "the first assessment was %d, so the building is at least %d years "
                          "old; an energy certificate year is a lower bound, so both a pass and "
                          "an honest unknown are consistent" % (epc["first_assessment_year"], age))

    if epc.get("floor_position") and profile.get("reject_ground_floor"):
        ok = epc["floor_position"] not in ("ground", "basement")
        out["ground_floor"] = ({ok}, "the certificate calls it a %s flat" % epc["floor_position"])

    if commute.get("all_min") is not None and profile.get("max_door_to_door_min") is not None:
        got = float(commute["all_min"])
        tol = float(commute.get("tolerance_min") or 0)
        ceiling = float(profile["max_door_to_door_min"])
        if got + tol <= ceiling:
            acceptable = {True}
        elif got - tol > ceiling:
            acceptable = {False}
        else:
            acceptable = {True, False, "unknown"}
        out["commute"] = (acceptable, "%d minutes door to door against a ceiling of %d, with a "
                                      "tolerance of %d" % (got, ceiling, tol))
    return out


def grade_hard_filters(cand, profile, facts, report):
    expected = expected_filters(profile, facts, report)
    rows = [r for r in (cand.get("hard_filters") or []) if isinstance(r, dict)]
    seen = {}
    for row in rows:
        kind = filter_kind(row)
        if kind and kind not in seen:
            seen[kind] = row
    out = []
    for kind, (acceptable, why) in expected.items():
        row = seen.get(kind)
        if row is None:
            out.append(collections.OrderedDict([
                ("filter", kind), ("row", None), ("expected_pass", sorted(map(str, acceptable))),
                ("reported_pass", None), ("consistent", False),
                ("why", why + "; the report lists no hard-filter row for this")]))
            continue
        got = row.get("pass")
        out.append(collections.OrderedDict([
            ("filter", kind), ("row", row.get("name")),
            ("expected_pass", sorted(map(str, acceptable))),
            ("reported_pass", got), ("consistent", got in acceptable), ("why", why)]))
    return out


# ------------------------------------------------------------------- truth --
def truth_for(fact, facts):
    """The truth value for a fact, or None when the case cannot grade it."""
    block_name, key = fact.split(".", 1)
    block = facts.get(block_name)
    if not isinstance(block, dict) or block.get("stale"):
        return None
    if fact == "epc.floor_position" and block.get("floor_position") is None:
        return ABSENT if block.get("floor_position_absent") else None
    if fact == "epc.floor_area_m2":
        if block.get("floor_area_m2") is None:
            return None
        return {"floor_area_m2": block["floor_area_m2"],
                "floor_area_sqft": block.get("floor_area_sqft") or
                round(block["floor_area_m2"] * SQFT_PER_M2)}
    if fact == "crime.total":
        if block.get("total") is None:
            return None
        return {"value": block["total"], "tolerance_pct": block.get("tolerance_pct", 15)}
    if fact in ("commute.all_min", "commute.rail_min"):
        value = block.get(key)
        if value is None:
            return None
        return {"value": value, "tolerance_min": block.get("tolerance_min", 8)}
    return block.get(key)


def truth_display(fact, truth):
    if truth is ABSENT:
        return "the official record states none"
    if fact == "epc.floor_area_m2":
        return "%.1f m2 / %d sq ft" % (truth["floor_area_m2"], truth["floor_area_sqft"])
    if isinstance(truth, dict):
        return truth.get("value")
    return truth


# ----------------------------------------------------------- question bank --
# skills/vet-flat/references/questions.md is the single source of the questions a
# report may ask. It is parsed at RUN TIME from its markdown tables, so a
# maintainer who edits the bank changes what the grader accepts, without touching
# this file. Two things are scored:
#
#   killer_questions_from_bank  every killer question must be grounded: it either
#                               overlaps a bank question by at least half its own
#                               content words, or it names a landmine or gate code
#                               that this report actually raised. A question that
#                               is neither is a soft question dressed up as a hard
#                               one - "is the building well managed?" instead of
#                               "who is the managing agent and what is the target
#                               repair time?".
#   gate_questions_present      when the report itself says it does not know the
#                               guarantor route (G1), the availability (G2), the
#                               landlord entity (G3) or the deposit protection
#                               (G4), it has to ask about it.
#
# Neither score is part of the pass line; both are reported as diagnostics.

QUESTIONS_MD = os.path.join(REFS, "questions.md")

# Enough of a stopword list for one page of English questions. Anything left is a
# content word, and content words are what two questions have to share.
STOPWORDS = set("""
a an the this that these those it its is are was were be been being am do does did doing done
have has had having will would shall should can could may might must and or but if then so
of in on at to for with from by as into over under about than up down out off through during
i you your yours we our ours us they them their he she his her him what which who whom whose
when where why how please any some all no not none there here also just very still yet more
most other another each both few many much such own same too only get got give given send
me my mine one two three tell ask say said know
""".split())

CODE_RE = re.compile(r"\b([GL])\s*-?\s*(\d{1,2})\b")
PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")
MIN_CONTENT_WORDS = 4   # below this a question is too vague to be "from the bank"
BANK_OVERLAP = 0.5

# How the report says, in its own words, that a gate is still open. The keywords are
# matched against a hard filter's name and requirement, a not_found entry's "what",
# an axis unknowns line, or the finding of an axis graded unknown.
GATE_KEYWORDS = collections.OrderedDict([
    ("G1", ["guarantor", "income check", "income test", "referencing", "proof of funds",
            "rent guarantee"]),
    # "start date" and a bare "keys" are deliberately absent: a not_found entry about a
    # building site's start date is not the flat's availability.
    ("G2", ["move in", "moving in", "still available", "available from", "availability",
            "take the keys", "tenancy start", "earliest move"]),
    ("G3", ["landlord", "legal entity", "who owns", "managing agent", "management company",
            "freeholder", "company on the tenancy"]),
    ("G4", ["deposit", "client money", "protection scheme", "custodial", "money protection"]),
])


def content_words(text):
    """Lower-cased words that carry meaning, crudely singularised."""
    text = PLACEHOLDER_RE.sub(" ", text or "")
    words = set()
    for raw in re.findall(r"[a-z][a-z'\-]*", text.lower()):
        word = raw.replace("'", "").replace("-", "")
        if len(word) < 2 or word in STOPWORDS:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]      # tariffs -> tariff, works -> work
        if word not in STOPWORDS:
            words.add(word)
    return words


def parse_question_bank(path=None):
    """Read questions.md and return [{code, question, section, words}].

    Every markdown table whose header carries a "Code" column and a column whose
    header starts with "Question" contributes its body rows. The bullet list under
    the viewing-day heading is added with the code VIEW. Nothing else is read, so
    prose in the bank cannot accidentally become a question.
    """
    path = path or QUESTIONS_MD
    out = []
    if not os.path.exists(path):
        return out
    with io.open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    section, code_col, q_col = "", None, None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("# ").strip()
            code_col, q_col = None, None
            continue
        if not stripped.startswith("|"):
            if stripped.startswith("- ") and "viewing-day" in section.lower():
                text = stripped[2:].strip().strip('"')
                if text:
                    out.append({"code": "VIEW", "question": text, "section": section,
                                "words": content_words(text)})
            code_col, q_col = (code_col, q_col) if stripped else (None, None)
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):        # the |---|---| separator row
            continue
        lowered = [c.lower() for c in cells]
        if "code" in lowered and any(c.startswith("question") for c in lowered):
            code_col = lowered.index("code")
            q_col = next(i for i, c in enumerate(lowered) if c.startswith("question"))
            continue
        if code_col is None or q_col is None or len(cells) <= max(code_col, q_col):
            continue
        code = cells[code_col].strip()
        text = cells[q_col].strip().strip('"').strip("“”")
        if not code or not text:
            continue
        out.append({"code": code, "question": text, "section": section,
                    "words": content_words(text)})
    return out


def codes_in(text):
    """G1, L6, 'L-12' -> {'G1', 'L6', 'L12'}."""
    return set(m.group(1).upper() + str(int(m.group(2))) for m in CODE_RE.finditer(text or ""))


def raised_codes(cand):
    """The landmine and gate codes this report actually stood behind."""
    out = set()
    for mine in cand.get("landmines") or []:
        if isinstance(mine, dict) and mine.get("code"):
            out.add(str(mine["code"]).upper())
    for code in (cand.get("verdict") or {}).get("reason_codes") or []:
        out.add(str(code).upper())
    return out


def bank_match(question, bank):
    """The best bank entry for this question, by share of the question's own words."""
    words = content_words(question)
    if len(words) < MIN_CONTENT_WORDS:
        return None, 0.0, len(words)
    best, best_ratio = None, 0.0
    for entry in bank:
        if not entry["words"]:
            continue
        ratio = len(words & entry["words"]) / float(len(words))
        if ratio > best_ratio:
            best, best_ratio = entry, ratio
    return best, best_ratio, len(words)


def grade_killer_questions(cand, bank):
    """Every killer question must come from the bank or name a code the report raised."""
    questions = [q for q in (cand.get("killer_questions") or []) if isinstance(q, str)]
    nonblank = [q for q in questions if q.strip()]
    raised = raised_codes(cand)
    rows, grounded = [], 0

    for i, question in enumerate(questions):
        row = collections.OrderedDict([("index", i), ("question", question)])
        if not question.strip():
            row.update([("grounded", False), ("how", "blank"),
                        ("detail", "an empty question is not a question")])
            rows.append(row)
            continue
        cited = codes_in(question) & raised
        entry, ratio, n_words = bank_match(question, bank)
        row["content_words"] = n_words
        row["best_bank_code"] = entry["code"] if entry else None
        row["best_bank_overlap"] = round(ratio, 3)
        if cited:
            grounded += 1
            row.update([("grounded", True), ("how", "cites a code the report raised"),
                        ("detail", "names %s, which this report raised in landmines or "
                                   "reason_codes" % ", ".join(sorted(cited)))])
        elif ratio >= BANK_OVERLAP:
            grounded += 1
            row.update([("grounded", True), ("how", "from the bank"),
                        ("detail", "shares %.0f%% of its content words with bank entry %s: %r"
                         % (ratio * 100, entry["code"], entry["question"][:90]))])
        elif n_words < MIN_CONTENT_WORDS:
            row.update([("grounded", False), ("how", "too vague"),
                        ("detail", "only %d content words; a question this short cannot be "
                                   "matched to the bank" % n_words)])
        else:
            row.update([("grounded", False), ("how", "not in the bank"),
                        ("detail", "closest bank entry is %s at %.0f%% of this question's "
                                   "content words, the floor is %.0f%%, and it names no code "
                                   "this report raised"
                         % (entry["code"] if entry else "none", ratio * 100,
                            BANK_OVERLAP * 100))])
        rows.append(row)

    if not nonblank:
        score = 0.0
        note = ("the report asks no killer question. Two questions whose answers would change "
                "the verdict are part of the output contract.")
    else:
        score = round(grounded / float(len(questions)), 4)
        note = None
    return rows, score, grounded, len(questions), note


def open_gates(cand, report):
    """Which of G1-G4 the report itself leaves unknown, with the line that says so."""
    said = []
    for row in cand.get("hard_filters") or []:
        if isinstance(row, dict) and row.get("pass") == "unknown":
            # name and observed only. The requirement restates the user's own rule and
            # often names the landlord in passing ("a guarantor route the landlord
            # accepts"), which would open the landlord gate for no reason.
            said.append(("hard filter %r" % row.get("name"),
                         "%s %s" % (row.get("name"), row.get("observed"))))
    for entry in report.get("not_found") or []:
        if isinstance(entry, dict):
            said.append(("not_found", entry.get("what") or ""))
    for axis in cand.get("axes") or []:
        if not isinstance(axis, dict):
            continue
        for line in axis.get("unknowns") or []:
            said.append(("axis %s unknowns" % axis.get("id"), line))
        if axis.get("evidence_class") == "U":
            said.append(("axis %s is unknown" % axis.get("id"),
                         "%s %s" % (axis.get("name"), axis.get("finding"))))

    out = collections.OrderedDict()
    for gate, keywords in GATE_KEYWORDS.items():
        for where, text in said:
            low = norm(text)
            hit = next((k for k in keywords if norm(k) in low), None)
            if hit:
                out[gate] = "%s says %r is unknown" % (where, hit)
                break
    return out


def grade_gate_questions(cand, report, bank):
    """An open gate has to be asked about, not just noted."""
    gates = open_gates(cand, report)
    asked = [q for q in (cand.get("killer_questions") or []) if isinstance(q, str) and q.strip()]
    # The schema has no questions_for_next_round today; read it if it ever gains one.
    extra = cand.get("questions_for_next_round")
    has_next_round = isinstance(extra, list)
    if has_next_round:
        asked += [q for q in extra if isinstance(q, str) and q.strip()]

    by_code = {}
    for entry in bank:
        by_code.setdefault(entry["code"].upper(), []).append(entry)

    rows, covered = [], 0
    for gate, why in gates.items():
        entries = by_code.get(gate, [])
        hit, how = None, None
        for question in asked:
            if gate in codes_in(question):
                hit, how = question, "names %s" % gate
                break
            words = content_words(question)
            if len(words) < MIN_CONTENT_WORDS:
                continue
            for entry in entries:
                if entry["words"] and \
                        len(words & entry["words"]) / float(len(words)) >= BANK_OVERLAP:
                    hit, how = question, "matches the %s question in the bank" % gate
                    break
            if hit:
                break
        if hit:
            covered += 1
        rows.append(collections.OrderedDict([
            ("gate", gate),
            ("bank_question", entries[0]["question"] if entries else None),
            ("why_open", why),
            ("asked", bool(hit)),
            ("how", how),
            ("question", hit)]))

    # The bank's rule 1 says the first message carries the gate question plus the one
    # that could kill the flat, and the schema caps killer_questions at two. So with
    # only killer_questions available a report is expected to cover ONE open gate; a
    # report that also carries a next-round list is expected to cover them all.
    expected = min(len(gates), len(gates) if has_next_round else 1)
    score = None if not gates else round(min(covered, expected) / float(expected), 4)
    return rows, score, covered, len(gates), expected, has_next_round


# ------------------------------------------------------- conversation cases --
# Two cases in the suite are not reports: they are the answers a user gets when
# they ask what the skill does, or say they have no idea where to start. Those
# still contain facts - the number of checks, the four verdict words, the legal
# caps - and those facts can be wrong, so they are graded the same way: pass or
# fail per check, fabrications counted separately, verdict-style judgements left
# alone. Every check is a named function below and takes its parameters from the
# case's expected_facts, so a maintainer can read what is being tested without
# reading this file.

CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿぀-ヿ]")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+|\n+")
NEGATIONS = ["cannot", "can not", "can't", "do not", "does not", "don't", "never",
             "forbid", "not allowed", "no method", "will not", "won't", "instead",
             "不能", "無法", "禁止", "不會", "沒有"]

DEFAULT_MARKERS = ["default", "for example", "e.g.", "typical", "most people", "usually",
                   "if you are not sure", "if unsure", "i will assume", "assume",
                   "suggested", "say ", "預設", "例如", "一般",
                   "多數人", "預設值", "比方說"]

PROTECTED_TERMS = ["nationality", "ethnicity", "ethnic", "race", "racial", "religion",
                   "immigration status", "visa status", "where are you from",
                   "country of origin", "國籍", "種族", "族裔",
                   "宗教", "簽證", "移民"]

SCRAPE_CLAIM = [
    r"(scrap\w*|crawl\w*|spider\w*)[^.。]{0,70}(rightmove|zoopla|onthemarket|openrent|"
    r"homeviews|trustpilot|airbnb|booking\.com)",
    r"(rightmove|zoopla|onthemarket|openrent|homeviews|trustpilot|airbnb|booking\.com)"
    r"[^.。]{0,70}(scrap\w*|crawl\w*|spider\w*)",
    r"(automatically|directly)\s+(fetch\w*|download\w*|pull\w*|read\w*|search\w*|check\w*)"
    r"[^.。]{0,70}(rightmove|zoopla|onthemarket|openrent|homeviews|trustpilot)",
    r"(fetch\w*|download\w*|pull\w*|search\w*)\s+(the\s+)?(listings?|prices?|reviews?|data)"
    r"\s+(from|on)\s+(rightmove|zoopla|onthemarket|openrent|homeviews|trustpilot)",
]


def sentences(text):
    return [s for s in SENTENCE_SPLIT.split(text or "") if s.strip()]


def negated(fragment):
    low = fragment.lower()
    return any(word in low for word in NEGATIONS)


def cjk_share(text):
    body = re.sub(r"\s+", "", text or "")
    if not body:
        return 0.0
    return len(CJK.findall(body)) / float(len(body))


def count_questions(text):
    """Question marks, plus numbered lines that are clearly asking something."""
    marks = len(re.findall(r"[?？]", text or ""))
    if marks:
        return marks
    return len(re.findall(r"^\s*\d+[.)]\s+\S", text or "", re.M))


def _hit(terms, low):
    return [t for t in terms if t.lower() in low]


# Each check returns (status, detail). status is "pass", "fail" or "skipped".
def chk_regex(text, params):
    m = re.search(params["pattern"], text or "", re.I | re.U)
    return ("pass" if m else "fail",
            "matched %r" % m.group(0)[:60] if m else "no match for %s" % params["pattern"])


def chk_all_of(text, params):
    low = (text or "").lower()
    missing = [t for t in params["terms"] if t.lower() not in low]
    return ("pass" if not missing else "fail",
            "all present" if not missing else "missing %s" % ", ".join(missing))


def chk_any_of(text, params):
    low = (text or "").lower()
    hits = _hit(params["terms"], low)
    return ("pass" if hits else "fail",
            "found %s" % ", ".join(hits[:4]) if hits else "none of %s" % ", ".join(params["terms"]))


def chk_groups(text, params):
    """Every group must contribute at least one term: three ideas, any wording."""
    low = (text or "").lower()
    missing, found = [], []
    for i, group in enumerate(params["groups"]):
        hits = _hit(group, low)
        (found if hits else missing).append(hits[0] if hits else "group %d" % (i + 1))
    return ("pass" if not missing else "fail",
            "found %s" % ", ".join(found) if not missing
            else "nothing from %s" % ", ".join(missing))


def chk_forbidden_claim(text, params):
    """Fail when the answer CLAIMS a capability the skill does not have."""
    for pattern in params.get("patterns", SCRAPE_CLAIM):
        for m in re.finditer(pattern, text or "", re.I | re.U):
            window = (text or "")[max(0, m.start() - 120):m.end() + 120]
            if not negated(window):
                return "fail", "claims %r" % m.group(0)[:80]
    return "pass", "no claim of automated access to a portal that forbids it"


def chk_language(text, params):
    """The answer must come back in the language the question was asked in."""
    share = cjk_share(text)
    want = params.get("language", "en")
    if want.startswith("zh") or want.startswith("ja"):
        ok = share >= params.get("min_cjk_share", 0.2)
        return ("pass" if ok else "fail",
                "%.0f%% of the characters are CJK, the floor is %.0f%%"
                % (share * 100, params.get("min_cjk_share", 0.2) * 100))
    ok = share <= params.get("max_cjk_share", 0.05)
    return ("pass" if ok else "fail",
            "%.0f%% of the characters are CJK, the ceiling is %.0f%%"
            % (share * 100, params.get("max_cjk_share", 0.05) * 100))


def chk_max_chars(text, params):
    n = len(text or "")
    return ("pass" if n <= params["max"] else "fail",
            "%d characters against a limit of %d" % (n, params["max"]))


def chk_max_questions(text, params):
    n = count_questions(text)
    lo, hi = params.get("min", 1), params["max"]
    return ("pass" if lo <= n <= hi else "fail",
            "%d questions, the range is %d to %d" % (n, lo, hi))


def chk_defaults_per_question(text, params):
    low = (text or "").lower()
    markers = sum(low.count(m.lower()) for m in params.get("markers", DEFAULT_MARKERS))
    questions = max(1, count_questions(text))
    need = max(1, int(round(questions * params.get("ratio", 1.0))))
    return ("pass" if markers >= need else "fail",
            "%d suggested defaults for %d questions, need %d" % (markers, questions, need))


def chk_no_protected_questions(text, params):
    """A question about nationality, ethnicity, religion or visa status is never asked."""
    terms = params.get("terms", PROTECTED_TERMS)
    for sentence in sentences(text):
        low = sentence.lower()
        hits = _hit(terms, low)
        if hits and re.search(r"[?？]", sentence):
            return "fail", "asks about %s: %r" % (hits[0], sentence.strip()[:100])
    mentions = _hit(terms, (text or "").lower())
    return "pass", ("no question about a protected characteristic"
                    + (" (mentions %s, but not as a question)" % mentions[0] if mentions else ""))


WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
                "\u4e00": 1, "\u5169": 2, "\u4e8c": 2, "\u4e09": 3, "\u56db": 4, "\u4e94": 5,
                "\u516d": 6}


def to_int(token):
    """'5', 'five' and the Chinese numeral all mean five; anything else means nothing."""
    if token is None:
        return None
    token = token.strip().lower()
    if re.match(r"^\d+$", token):
        return int(token)
    return WORD_NUMBERS.get(token)


def chk_number_if_stated(text, params):
    """A number the answer did not have to give, but must get right if it does."""
    want = params["value"]
    body = text or ""
    for span in params.get("mask_patterns", []):
        body = re.sub(span, " ", body, flags=re.I | re.U)
    found = []
    for pattern in params["patterns"]:
        for m in re.finditer(pattern, body, re.I | re.U):
            for g in m.groups():
                n = to_int(g)
                if n is not None:
                    found.append(n)
    if not found:
        return "skipped", "the answer does not state this number, which is allowed"
    wrong = [n for n in found if n != want]
    return ("pass" if not wrong else "fail",
            "states %s, the register says %s" % (sorted(set(found)), want))


def chk_date_if_stated(text, params):
    """A date the answer did not have to give, but must get right if it does."""
    body = text or ""
    if any(re.search(p, body, re.I | re.U) for p in params["correct_patterns"]):
        return "pass", "states the correct date"
    for pattern in params.get("trigger_patterns", []):
        m = re.search(pattern, body, re.I | re.U)
        if m:
            return "fail", "gives a date for this that is not %s: %r" % (
                params["value"], m.group(0)[:80])
    return "skipped", "the answer does not date this, which is allowed"


CONVERSATION_CHECKS = {
    "regex": chk_regex,
    "all_of": chk_all_of,
    "any_of": chk_any_of,
    "groups": chk_groups,
    "forbidden_claim": chk_forbidden_claim,
    "language": chk_language,
    "max_chars": chk_max_chars,
    "max_questions": chk_max_questions,
    "defaults_per_question": chk_defaults_per_question,
    "no_protected_questions": chk_no_protected_questions,
    "number_if_stated": chk_number_if_stated,
    "date_if_stated": chk_date_if_stated,
}


def grade_conversation(text, case, variant=None):
    """Score a plain-text answer. Same scorecard shape, different rows."""
    facts = case.get("expected_facts") or {}
    checks = facts.get("answer_checks") or collections.OrderedDict()
    variants = {v["id"]: v for v in (case.get("prompt_variants") or [])}
    chosen = variants.get(variant) or (list(variants.values())[0] if variants else {})
    rows, passed, gradeable, fabrications, critical = [], 0, 0, 0, []

    for name, spec in checks.items():
        rule = spec.get("rule")
        fn = CONVERSATION_CHECKS.get(rule)
        if fn is None:
            continue
        params = dict(spec)
        params.pop("rule", None)
        if rule == "language" and chosen.get("language"):
            params["language"] = chosen["language"]
        status, detail = fn(text, params)
        row = collections.OrderedDict([
            ("check", name), ("rule", rule), ("status", status), ("detail", detail),
            ("why", spec.get("why")),
            ("fabrication_on_fail", bool(spec.get("fabrication_on_fail"))),
            ("critical", bool(spec.get("critical"))),
        ])
        rows.append(row)
        if status == "skipped":
            continue
        gradeable += 1
        if status == "pass":
            passed += 1
        else:
            if spec.get("fabrication_on_fail"):
                fabrications += 1
            if spec.get("critical"):
                critical.append(name)

    recall = round(passed / float(gradeable), 4) if gradeable else None
    meets = (fabrications == 0 and not critical
             and (recall or 0) >= PASS_LINE["stable_fact_recall"])
    label = case["id"] + ("#" + variant if variant else "")
    summary = ("%s: %d/%d checks, %d fabrication%s%s -> %s"
               % (label, passed, gradeable, fabrications,
                  "" if fabrications == 1 else "s",
                  ", CRITICAL: " + ", ".join(critical) if critical else "",
                  "PASS" if meets else "BELOW LINE"))
    return collections.OrderedDict([
        ("case", case["id"]),
        ("kind", "conversation"),
        ("variant", variant),
        ("prompt", chosen.get("prompt") or case.get("prompt")),
        ("graded_at", datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"),
        ("schema", collections.OrderedDict([("valid", True), ("errors", []),
                                            ("warnings", ["not a report; no schema applies"])])),
        ("scores", collections.OrderedDict([
            ("fact_recall", recall), ("stable_fact_recall", recall),
            ("fabrications", fabrications), ("citations", None),
            ("unknown_honesty", None), ("hard_filter_consistency", None)])),
        ("counts", collections.OrderedDict([
            ("gradeable", gradeable), ("correct", passed),
            ("skipped", sum(1 for r in rows if r["status"] == "skipped")),
            ("wrong", sum(1 for r in rows if r["status"] == "fail")),
            ("critical_failures", len(critical))])),
        ("pass_line", collections.OrderedDict(sorted(PASS_LINE.items()))),
        ("meets_pass_line", meets),
        ("checks", rows),
        ("answer_chars", len(text or "")),
        ("judge_notes", facts.get("judge_notes")),
        ("summary", summary),
    ])


# ------------------------------------------------------------------- scoring --
def source_index(report):
    out = {}
    for src in report.get("sources") or []:
        if isinstance(src, dict) and src.get("id"):
            out[src["id"]] = src
    return out


def cites_ok(source_ids, index):
    for sid in source_ids or []:
        src = index.get(sid)
        if src and (src.get("url") or "").strip():
            return True
    return False


def grade(report, case, profile_path=None):
    with io.open(SCHEMA_PATH, encoding="utf-8") as fh:
        schema = json.load(fh)
    errors, warnings = render.validate(report, schema)

    facts = case.get("expected_facts") or {}
    cands = report.get("candidates") or []
    cand = cands[0] if cands and isinstance(cands[0], dict) else {}
    index = source_index(report)
    profile = read_profile(profile_path)
    guard = ReferentGuard(report, facts)

    rows, correct, found_n, cited_n, fabrications, honest, dishonest = [], 0, 0, 0, 0, 0, 0
    stable_total, stable_correct = 0, 0

    for fact, rule in FACT_RULES.items():
        truth = truth_for(fact, facts)
        if truth is None:
            continue
        found = find_fact(cand, fact, rule, truth, guard)
        if truth is ABSENT:
            if found is not None and found.value is not None:
                status = "wrong"
                detail = ("the register carries no value for this, so %r was invented"
                          % (found.value,))
            else:
                status, detail = "correct", "left unknown, which is what the register supports"
            where = found.where if found else None
            srcs = found.sources if found else []
        elif found is None or found.value is None:
            status, detail = "missing", "the report states no value"
            where, srcs = (found.where if found else None), (found.sources if found else [])
        else:
            status, detail = compare(fact, rule, found, truth, report)
            where, srcs = found.where, found.sources

        row = collections.OrderedDict([
            ("fact", fact),
            ("stable", fact in STABLE_FACTS),
            ("truth", truth_display(fact, truth)),
            ("reported", found.value if found else None),
            ("unit", found.unit if found else None),
            ("status", status),
            ("detail", detail),
            ("where", where),
            ("sources", list(srcs or [])),
        ])
        if fact in STABLE_FACTS:
            stable_total += 1
        if status == "correct":
            correct += 1
            if fact in STABLE_FACTS:
                stable_correct += 1
        if status in ("correct", "wrong"):
            found_n += 1
            row["cited"] = cites_ok(srcs, index)
            if row["cited"]:
                cited_n += 1
        if status == "wrong":
            fabrications += 1
        if status == "missing":
            # Only a fact the report did NOT state can be an honest unknown. A value
            # that contradicts the truth was invented, whatever else the report says.
            is_unknown, why = marked_unknown(cand, report, fact, rule, found)
            row["marked_unknown"] = is_unknown
            row["marked_unknown_note"] = why
            if is_unknown:
                honest += 1
            else:
                dishonest += 1
        elif status == "wrong":
            row["marked_unknown"] = False
            row["marked_unknown_note"] = "a value was stated, so this is not an unknown"
            dishonest += 1
        rows.append(row)

    gradeable = len(rows)
    not_correct = honest + dishonest
    hard = grade_hard_filters(cand, profile, facts, report)
    hard_ok = sum(1 for h in hard if h["consistent"])

    bank = parse_question_bank()
    kq_rows, kq_score, kq_ok, kq_total, kq_note = grade_killer_questions(cand, bank)
    gate_rows, gate_score, gates_ok, gates_open_n, gates_expected, has_next_round = \
        grade_gate_questions(cand, report, bank)

    scores = collections.OrderedDict([
        ("fact_recall", round(correct / float(gradeable), 4) if gradeable else None),
        ("stable_fact_recall",
         round(stable_correct / float(stable_total), 4) if stable_total else None),
        ("fabrications", fabrications),
        ("citations", round(cited_n / float(found_n), 4) if found_n else None),
        ("unknown_honesty", round(honest / float(not_correct), 4) if not_correct else 1.0),
        ("hard_filter_consistency", round(hard_ok / float(len(hard)), 4) if hard else None),
        ("killer_questions_from_bank", kq_score),
        ("gate_questions_present", gate_score),
    ])

    meets = (scores["fabrications"] == 0
             and (scores["stable_fact_recall"] or 0) >= PASS_LINE["stable_fact_recall"]
             and (scores["citations"] if scores["citations"] is not None else 0)
             >= PASS_LINE["citations"]
             and not errors)

    summary = ("%s: %d/%d facts (%d/%d stable), %d fabrication%s, citations %s, "
               "unknown-honesty %s, hard filters %d/%d, questions %d/%d from the bank, "
               "gates %d/%d, schema %s -> %s"
               % (case["id"], correct, gradeable, stable_correct, stable_total, fabrications,
                  "" if fabrications == 1 else "s",
                  pct(scores["citations"]), pct(scores["unknown_honesty"]),
                  hard_ok, len(hard), kq_ok, kq_total, gates_ok, gates_expected,
                  "ok" if not errors else "%d errors" % len(errors),
                  "PASS" if meets else "BELOW LINE"))

    return collections.OrderedDict([
        ("case", case["id"]),
        ("address", case.get("address")),
        ("borough", case.get("borough")),
        ("graded_at", datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"),
        ("schema", collections.OrderedDict([("valid", not errors), ("errors", errors),
                                            ("warnings", warnings)])),
        ("scores", scores),
        ("counts", collections.OrderedDict([
            ("gradeable", gradeable), ("correct", correct), ("found", found_n),
            ("missing", gradeable - found_n), ("wrong", fabrications),
            ("cited", cited_n), ("marked_unknown", honest),
            ("hard_filters_checked", len(hard)), ("hard_filters_consistent", hard_ok),
            ("killer_questions", kq_total), ("killer_questions_grounded", kq_ok),
            ("gates_open", gates_open_n), ("gates_covered", gates_ok),
            ("gates_expected", gates_expected),
            ("referent_excluded", len(guard.excluded))])),
        ("pass_line", collections.OrderedDict(sorted(PASS_LINE.items()))),
        ("meets_pass_line", meets),
        ("facts", rows),
        ("referent_excluded", guard.excluded),
        ("hard_filters", hard),
        ("killer_questions", kq_rows),
        ("killer_questions_note", kq_note),
        ("gates", gate_rows),
        ("question_bank", collections.OrderedDict([
            ("path", os.path.relpath(QUESTIONS_MD, ROOT)),
            ("entries", len(bank)),
            ("next_round_field_used", has_next_round)])),
        ("crime_window", (facts.get("crime") or {}).get("months")),
        ("truth_retrieved_at", collections.OrderedDict(
            (k, (v or {}).get("retrieved_at")) for k, v in facts.items()
            if isinstance(v, dict) and v.get("retrieved_at"))),
        ("summary", summary),
    ])


def pct(value):
    return "n/a" if value is None else "%.0f%%" % (value * 100)


# --------------------------------------------------------------------- main --
def load_case(evals_path, case_id):
    with io.open(evals_path, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=collections.OrderedDict)
    for case in doc.get("evals") or []:
        if case.get("id") == case_id:
            return case, doc
    raise KeyError(case_id)


def case_profile_path(evals_path, case):
    for rel in case.get("files") or []:
        if rel.endswith("profile.yaml"):
            return os.path.join(os.path.dirname(os.path.abspath(evals_path)), rel)
    return None


def explain():
    lines = ["Label-matching rules, one line per graded fact.", ""]
    for fact, rule in FACT_RULES.items():
        req = " AND ".join("(" + " | ".join(g) + ")" for g in (rule.get("require") or [])) or "-"
        exc = ", ".join(rule.get("exclude") or []) or "-"
        lines.append("%-38s kind=%-14s axis=%-4s metric=%s"
                     % (fact, rule["kind"], rule.get("axis"), rule.get("metric") or "-"))
        lines.append("    require: %s" % req)
        lines.append("    exclude: %s" % exc)
    lines.append("")
    lines.append("Heating classes are decided by these keywords, in this priority order:")
    for cls, words in HEATING_KEYWORDS.items():
        lines.append("    %-24s %s" % (cls, ", ".join(words)))
    lines.append("")
    lines.append("The referent guard. A matched number is SKIPPED, not graded, when one of")
    lines.append("these says it is about something else. Skips are listed on the card under")
    lines.append("referent_excluded. The metric slots are never guarded.")
    for fact, rules in REFERENT_RULES.items():
        lines.append("%s" % fact)
        for spec in rules:
            lines.append("    %-38s %s" % (spec["rule"], spec["why"]))
            if spec.get("test"):
                lines.append("        decided by: %s()" % spec["test"])
            else:
                lines.append("        any of: %s" % ", ".join(spec.get("any_of") or []))
                lines.append("        in: %s" % ", ".join(spec.get("fields") or ()))
            if spec.get("keep_any"):
                lines.append("        unless %s says: %s"
                             % (", ".join(spec.get("keep_fields") or ()),
                                ", ".join(spec["keep_any"])))
    return "\n".join(lines)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", nargs="?",
                    help="the report.json to grade, or for a conversation case the text file "
                         "holding the agent's answer")
    ap.add_argument("--case", help="the eval case id from evals/evals.json")
    ap.add_argument("--evals", default=EVALS_JSON, help="path to evals.json")
    ap.add_argument("--profile", help="the profile.yaml the run used (default: the case's own)")
    ap.add_argument("--json-out", help="also write the scorecard here")
    ap.add_argument("--variant", help="for a conversation case run in more than one language, "
                                      "which prompt variant this answer came from")
    ap.add_argument("--summary-only", action="store_true", help="print only the summary line")
    ap.add_argument("--explain", action="store_true", help="print the matching rules and stop")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.explain:
        print(explain())
        return 0
    if not args.report or not args.case:
        print("usage error: a report.json and --case <id> are both required "
              "(or use --explain)", file=sys.stderr)
        return 2
    try:
        case, _ = load_case(args.evals, args.case)
    except KeyError:
        print("usage error: no case %r in %s" % (args.case, args.evals), file=sys.stderr)
        return 2
    try:
        with io.open(args.report, encoding="utf-8") as fh:
            raw = fh.read()
    except (IOError, OSError) as exc:
        print("could not read the answer: %s" % exc, file=sys.stderr)
        return 1

    if case.get("kind") == "conversation":
        card = grade_conversation(raw, case, args.variant)
    else:
        try:
            report = json.loads(raw)
        except ValueError as exc:
            print("the report is not valid JSON: %s" % exc, file=sys.stderr)
            return 1
        profile_path = args.profile or case_profile_path(args.evals, case)
        card = grade(report, case, profile_path)
    card["report"] = os.path.abspath(args.report)
    if not args.summary_only:
        json.dump(card, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        print(card["summary"])
    if args.json_out:
        with io.open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(card, ensure_ascii=False, indent=1) + "\n")
    print(card["summary"], file=sys.stderr)
    return 0 if card["schema"]["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
