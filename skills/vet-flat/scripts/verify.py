#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check evidence.json before anybody writes a verdict from it.

This is the deterministic half of the VERIFIER role in references/pipeline.md. It reads
what the executors collected (references/evidence-schema.json), applies rules that have
one answer, and writes references/verified-schema.json. A model then reads only the
items this flagged - which is the point: a verifier that re-reads everything costs as
much as the run it is checking, and gets bored in the same places.

WHAT IT CHECKS
==============
quote_in_source     the quote is really in the source, comparing text with the
                    whitespace normalised and the case ignored. A quote that has been
                    tidied, joined up or paraphrased is not a quote. Where no text is
                    held for the source the quote cannot be checked; the item is not
                    failed for that, and its id is listed under counts.quotes_unchecked,
                    because a run whose passes were never read is a different thing
                    from one whose passes were.
source_resolves     the source id resolves: an entry in report.json's sources[] with a
                    url, or a file in the pasted-sources folder for "pasted:<name>".
unit_present        a number carries a unit. 54 is not an area.
referent            the number is about the thing it says it is about, by the shared
                    rules in scripts/referents.py: the building's area is not the
                    flat's, a replaced certificate's rating is not the one in force, a
                    sale price is never a year, the strike-day journey is not the
                    commute. bench/grade.py uses the same word lists.
deposit_cap_branch  every legal cap recomputed from the rent the evidence itself
holding_deposit_cap carries, against references/thresholds.yaml: deposit five weeks
rent_in_advance_cap under fifty thousand pounds a year and six at or above it, holding
deposit_over_cap    deposit one week, rent in advance one month. A cap quoted with the
                    wrong branch is the failure this catches, and it is a common one:
                    the branch changes at an annual figure nobody computes.
contradiction       two items about the same thing that disagree - the advert's area
                    against the certificate's, the advert's energy letter against the
                    register's. Both are flagged; the verifier decides which survives.
fixed_form          every fixed question the tier owes an answer to is answered
                    somewhere, in one of its three states. The tier mapping is read
                    from references/fixed-questions.yaml and never counted in code.

Run with neither --sources nor --report and there is nothing to check a quote or a
source id against, so every item comes back `unknown` rather than quietly passing. The
cap, contradiction and fixed-form checks still run: they read the evidence itself.

AND, FOR THE BENCH ONLY: --gold runs an INFORMATION-SUFFICIENCY PROBE. Given this
evidence and nothing else, is each known-good fact even derivable? It is deterministic
string and number matching, it costs no tokens, and it separates two failures that look
identical in a scorecard: the planner and executors never fetched the fact, or they did
and the integrator failed to use it. Never run it outside a benchmark: the gold is the
answer sheet.

Not a network tool. Standard library only, Python 3.9.

Usage:
  verify.py evidence.json                                  > verified.json
  verify.py evidence.json --report report.json --sources pasted/
  verify.py evidence.json --tier standard --table
  verify.py evidence.json --strict            # an unknown nobody tried is a failure
  verify.py --from-report report.json         > evidence.json   (derive, then verify)
  verify.py evidence.json --gold gold.json --gold-id V2_BUCK    # bench only

Exit codes: 0 nothing failed, 1 at least one item or file check failed (or a file could
not be read), 2 wrong arguments.
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
REFS = os.path.join(HERE, "..", "references")
DEFAULT_QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")
DEFAULT_THRESHOLDS = os.path.join(REFS, "thresholds.yaml")

sys.path.insert(0, HERE)
import referents  # noqa: E402  the referent word lists, shared with bench/grade.py
import scan  # noqa: E402  the tiny YAML reader and the fixed-question tiers

SCHEMA = "vet-flat/verified/1"
EVIDENCE_SCHEMA = "vet-flat/evidence/1"
MONEY_TOLERANCE = 1.0        # pounds: rounding, not a different answer
WEEKS_TOLERANCE = 0.05       # weeks
SOURCE_SUFFIXES = (".txt", ".md", ".json", ".html", ".htm", "")


def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def read_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


# ------------------------------------------------------------------ text work --
WS = re.compile(r"\s+")


def flatten(text):
    """Whitespace normalised, case folded. A quote may be re-wrapped, never re-worded."""
    return WS.sub(" ", (text or "")).strip().lower()


def numbers_in(text):
    """Every number in a string, as floats, commas removed."""
    out = []
    for raw in re.findall(r"-?\d[\d,]*(?:\.\d+)?", text or ""):
        try:
            out.append(float(raw.replace(",", "")))
        except ValueError:
            pass
    return out


def as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        found = numbers_in(value)
        return found[0] if len(found) == 1 else None
    return None


# ------------------------------------------------------------------- sources ---
def load_sources(folder):
    """{name: text} for every file in the pasted-sources folder, by stem and by filename."""
    out = collections.OrderedDict()
    if not folder or not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (IOError, OSError):
            continue
        out[name] = text
        out.setdefault(os.path.splitext(name)[0], text)
    return out


def report_source_ids(report):
    """{id: url} from a report's top-level sources[]."""
    out = {}
    for source in (report or {}).get("sources") or []:
        if isinstance(source, dict) and source.get("id"):
            out[source["id"]] = source.get("url") or ""
    return out


def source_text(item, pasted, report_texts):
    """The text the quote should be findable in, or None when we hold no text for it."""
    source = (item.get("source") or "").strip()
    if source.startswith("pasted:"):
        return pasted.get(source[len("pasted:"):])
    if source in pasted:
        return pasted[source]
    return (report_texts or {}).get(source)


# --------------------------------------------------------------- item checks ---
def check_item(item, pasted, source_ids, report_texts, flat=None, strict=False):
    """(state, reason, [rule ids]) for one evidence item."""
    rules, reasons = [], []
    status = item.get("status") or ("unknown" if item.get("value") is None else "ok")

    if status == "unknown":
        tried = [t for t in (item.get("tried") or []) if str(t).strip()]
        if not tried and strict:
            return "fail", ("nobody says what was tried, so this is a gap nobody looked "
                            "at rather than one somebody could not fill"), ["untried_unknown"]
        return "unknown", (item.get("note") or "the executor could not get it"), []

    if not pasted and not source_ids:
        return "unknown", ("no source text and no sources list were given, so nothing about "
                           "this item could be checked"), []

    source = (item.get("source") or "").strip()
    if not source:
        rules.append("source_resolves")
        reasons.append("no source id")
    elif source.startswith("pasted:"):
        if source[len("pasted:"):] not in pasted:
            rules.append("source_resolves")
            reasons.append("no pasted file named %r" % source[len("pasted:"):])
    elif source_ids and source not in source_ids:
        rules.append("source_resolves")
        reasons.append("source id %r is in no sources[] entry" % source)
    elif source_ids and not source_ids.get(source):
        rules.append("source_resolves")
        reasons.append("source id %r has no url" % source)

    quote = item.get("quote")
    text = source_text(item, pasted, report_texts)
    if quote and text is not None:
        if flatten(quote) not in flatten(text):
            rules.append("quote_in_source")
            reasons.append("the quote is not in the source, even ignoring whitespace")
    elif not quote and "source_resolves" not in rules:
        rules.append("quote_missing")
        reasons.append("a found item needs the sentence it was read in")

    number = as_number(item.get("value"))
    if number is not None and not (item.get("unit") or "").strip():
        rules.append("unit_present")
        reasons.append("a number with no unit is not evidence")

    context = " ".join(str(x) for x in [item.get("claim"), item.get("note"),
                                        item.get("quote"), item.get("unit"),
                                        item.get("source"), item.get("script")] if x)
    for problem in referents.problems(item.get("claim"), context, flat,
                                      item.get("value")):
        rules.append("referent:" + problem["rule"])
        reasons.append(problem["why"])

    if rules:
        return "fail", "; ".join(reasons), rules
    return "pass", None, []


# ---------------------------------------------------------------- legal caps ---
def load_thresholds(path=None):
    path = path or DEFAULT_THRESHOLDS
    with io.open(path, encoding="utf-8") as fh:
        doc = scan.parse_questions(fh.read())
    out = {}
    for key, block in doc.items():
        if isinstance(block, dict) and "value" in block:
            out[key] = block["value"]
    return out


def rent_pcm_from(items, given=None):
    """The monthly rent this run is working from: the argument, else the evidence."""
    if given:
        return float(given), "the --rent-pcm argument"
    for item in items:
        claim = referents.normalise(item.get("claim"))
        unit = referents.normalise(item.get("unit"))
        if " rent " not in claim:
            continue
        if " deposit " in claim or " advance " in claim:
            continue
        number = as_number(item.get("value"))
        if number is None:
            continue
        if " week " in unit or " weeks " in unit or " weekly " in claim:
            continue
        # A yearly figure read as a monthly one multiplies the annual rent by twelve and
        # flips the deposit branch, so a CORRECT five-week cap starts failing.
        if (" year " in unit or " annum " in unit or " yearly " in unit
                or " annual " in claim or " yearly " in claim or " per year " in claim
                or " per annum " in claim):
            continue
        return number, "evidence item %s" % item.get("id")
    return None, None


CAP_WORDS = ["cap", "capped", "maximum", "max", "ceiling", "legal limit", "limit"]


def cap_checks(items, thresholds, rent_pcm=None):
    """[{item, rule, reason}] - every legal cap recomputed from the rent in evidence."""
    out = []
    rent, whence = rent_pcm_from(items, rent_pcm)
    if rent is None:
        return out, None
    weekly = rent * 12.0 / 52.0
    annual = rent * 12.0
    threshold = float(thresholds.get("deposit_annual_rent_threshold_gbp") or 50000)
    low_weeks = float(thresholds.get("deposit_cap_weeks") or 5)
    high_weeks = float(thresholds.get("deposit_cap_weeks_high_rent") or 6)
    cap_weeks = low_weeks if annual < threshold else high_weeks
    other_weeks = high_weeks if cap_weeks == low_weeks else low_weeks
    hold_weeks = float(thresholds.get("holding_deposit_weeks") or 1)
    advance_months = float(thresholds.get("rent_in_advance_max_months") or 1)
    working = collections.OrderedDict([
        ("rent_pcm", round(rent, 2)), ("rent_pcm_from", whence),
        ("weekly_rent", round(weekly, 2)), ("annual_rent", round(annual, 2)),
        ("branch_threshold_gbp", threshold),
        ("deposit_cap_weeks", cap_weeks),
        ("deposit_cap_gbp", round(weekly * cap_weeks, 2)),
        ("holding_deposit_cap_weeks", hold_weeks),
        ("holding_deposit_cap_gbp", round(weekly * hold_weeks, 2)),
        ("rent_in_advance_max_months", advance_months)])

    for item in items:
        if (item.get("status") or "ok") == "unknown":
            continue
        claim = referents.normalise(item.get("claim"))
        unit = referents.normalise(item.get("unit"))
        value = as_number(item.get("value"))
        if value is None:
            continue
        is_cap = any((" %s " % w) in claim for w in CAP_WORDS)
        in_weeks = " week " in unit or " weeks " in unit or " weeks of rent " in unit
        in_months = " month " in unit or " months " in unit
        in_money = not in_weeks and not in_months

        if " holding deposit " in claim:
            limit_weeks, limit_money = hold_weeks, weekly * hold_weeks
            rule = "holding_deposit_cap"
        elif " advance " in claim:
            if in_months and value > advance_months + 1e-9:
                out.append({"item": item.get("id"), "rule": "rent_in_advance_cap",
                            "reason": "%s months in advance is over the legal maximum of %s"
                                      % (value, advance_months)})
            continue
        elif " deposit " in claim:
            limit_weeks, limit_money = cap_weeks, weekly * cap_weeks
            rule = "deposit_cap_branch" if is_cap else "deposit_over_cap"
        else:
            continue

        if is_cap and in_weeks:
            if abs(value - limit_weeks) > WEEKS_TOLERANCE:
                why = ("the cap here is %g weeks, not %g: the annual rent is %s and the "
                       "branch changes at %s" % (limit_weeks, value, round(annual),
                                                 round(threshold))) \
                    if abs(value - other_weeks) <= WEEKS_TOLERANCE and rule == \
                    "deposit_cap_branch" else \
                    "the cap here is %g weeks, and this says %g" % (limit_weeks, value)
                out.append({"item": item.get("id"), "rule": rule, "reason": why})
        elif is_cap and in_money:
            if abs(value - limit_money) > MONEY_TOLERANCE:
                out.append({"item": item.get("id"), "rule": rule,
                            "reason": "the cap on this rent is %.2f, and this says %g"
                                      % (limit_money, value)})
        elif in_weeks and value > limit_weeks + WEEKS_TOLERANCE:
            out.append({"item": item.get("id"), "rule": rule,
                        "reason": "%g weeks is over the legal cap of %g weeks"
                                  % (value, limit_weeks)})
        elif in_money and value > limit_money + MONEY_TOLERANCE:
            out.append({"item": item.get("id"), "rule": rule,
                        "reason": "%g is over the legal cap of %.2f on this rent"
                                  % (value, limit_money)})
    return out, working


# ------------------------------------------------------------- contradictions --
# Two items about the same thing must agree. The pairs that matter are the ones where
# one number comes from a page somebody is selling and the other from a register.
FACT_KEYS = [
    ("area", ["floor area", "area", "square metres", "square feet", "sq ft", "sqm"],
     ["balcony", "terrace", "plot", "garden"], "pct", 5.0),
    ("energy_rating", ["energy rating", "epc rating", "epc letter", "energy letter"],
     [], "exact", 0),
    ("crime_total", ["recorded crime", "crimes", "crime count", "crime total"],
     ["category"], "pct", 15.0),
    ("commute_minutes", ["door to door", "commute", "journey time"], [], "abs", 8.0),
]


def fact_key(item):
    claim = referents.normalise(item.get("claim"))
    for key, words, blockers, _kind, _tol in FACT_KEYS:
        if any((" %s " % b) in claim for b in blockers):
            continue
        if any((" %s " % w) in claim for w in words):
            return key
    return None


def contradictions(items):
    """[{items, rule, reason}] - items that claim the same thing and disagree."""
    tolerance = dict((k, (kind, tol)) for k, _w, _b, kind, tol in FACT_KEYS)
    groups = collections.OrderedDict()
    for item in items:
        if (item.get("status") or "ok") == "unknown":
            continue
        key = fact_key(item)
        if key:
            groups.setdefault(key, []).append(item)
    out = []
    for key, group in groups.items():
        kind, tol = tolerance[key]
        for i, left in enumerate(group):
            for right in group[i + 1:]:
                if not disagree(left, right, kind, tol):
                    continue
                out.append({"items": [left.get("id"), right.get("id")],
                            "rule": "contradiction:" + key,
                            "reason": "%s says %s and %s says %s; one of them is about "
                                      "something else, or one of them is wrong"
                                      % (left.get("source") or left.get("id"),
                                         left.get("value"),
                                         right.get("source") or right.get("id"),
                                         right.get("value"))})
    return out


def disagree(left, right, kind, tol):
    a, b = left.get("value"), right.get("value")
    if a is None or b is None:
        return False
    if kind == "exact":
        return str(a).strip().lower() != str(b).strip().lower()
    x, y = as_number(a), as_number(b)
    if x is None or y is None:
        return str(a).strip().lower() != str(b).strip().lower()
    x, y = same_unit(x, left.get("unit")), same_unit(y, right.get("unit"))
    if kind == "abs":
        return abs(x - y) > tol
    biggest = max(abs(x), abs(y)) or 1.0
    return abs(x - y) / biggest * 100.0 > tol


def same_unit(value, unit):
    """Square feet to square metres, so an advert in feet can be compared with a register."""
    unit = referents.normalise(unit)
    if any(w in unit for w in (" sq ft ", " sqft ", " square feet ", " square foot ", " ft2 ")):
        return value / 10.7639
    return value


# ------------------------------------------------------------- the fixed form --
FIXED_ID = re.compile(r"\bF([1-9]|1[0-8])\b")


def fixed_form_check(items, report, tier, questions_path=None):
    """(missing ids, wanted ids) for this tier. The mapping lives in one file only."""
    doc = scan.load_document(questions_path or DEFAULT_QUESTIONS)
    wanted = scan.ids_for_tier(doc.get("questions") or {}, doc.get("tiers") or {}, tier)
    answered = set()
    for candidate in (report or {}).get("candidates") or []:
        for answer in (candidate or {}).get("fixed_answers") or []:
            if isinstance(answer, dict) and answer.get("id"):
                answered.add(answer["id"])
    for item in items:
        for field in (item.get("claim"), item.get("note")):
            for found in FIXED_ID.findall(field or ""):
                answered.add("F" + found)
    return [qid for qid in wanted if qid not in answered], wanted


# ----------------------------------------------------- information sufficiency --
# Words too common in this domain to say anything on their own.
STOP = set("the and for with that this from have been they were what when which their "
           "there about would could should than then into over under also only just "
           "very much more most some such each other "
           "metres metre square feet foot flat area rent week weeks month months year "
           "years london street road building certificate report data".split())


def gold_probes(gold, gold_id=None):
    """[{id, label, needles, mode}] from either gold shape. Deterministic, no model.

    Canonical (what the tests use): {"facts": [{"id", "claim", "all_of"/"any_of": [...],
    "value", "unit", "tolerance_pct"}]}.

    Benchmark shape: {"candidates": [{"id", "gold_landmines": [{"code", "confidence",
    "evidence": [{"text"}]}]}]}. The needles are the numbers and the distinctive words in
    the hand-written evidence, and a landmine counts as derivable when one of them is in
    the payload. That is a COARSE proxy - it says the material is there to notice the
    problem, not that a reader would notice it - and it is reported as such.
    """
    probes = []
    for fact in gold.get("facts") or []:
        needles = list(fact.get("all_of") or [])
        mode = "all"
        if not needles:
            needles = list(fact.get("any_of") or [])
            mode = "any"
        if fact.get("value") is not None and not needles:
            needles, mode = [str(fact["value"])], "number"
        probes.append({"id": fact.get("id") or fact.get("claim"),
                       "label": fact.get("claim") or fact.get("id"),
                       "needles": needles, "mode": mode,
                       "value": fact.get("value"),
                       "tolerance_pct": fact.get("tolerance_pct")})
    if probes:
        return probes
    for candidate in gold.get("candidates") or []:
        if gold_id and candidate.get("id") != gold_id:
            continue
        for mine in candidate.get("gold_landmines") or []:
            if mine.get("confidence") != "high":
                continue
            numbers, words = [], []
            for piece in mine.get("evidence") or []:
                text = (piece or {}).get("text") or ""
                numbers.extend(re.findall(r"\d[\d,]*(?:\.\d+)?", text))
                words.extend(w for w in re.findall(r"[A-Za-z]{4,}", text)
                             if w.lower() not in STOP)
            # Numbers first, and only numbers when there are any: "metres" appears in
            # every area quote ever written, so a word match on it says nothing about
            # whether THIS problem was visible in the evidence.
            needles = numbers or words
            probes.append({"id": mine.get("code"), "label": mine.get("name"),
                           "needles": sorted(set(needles)), "mode": "any",
                           "value": None, "tolerance_pct": None})
    return probes


def sufficiency(evidence, gold, gold_id=None):
    payload = json.dumps(evidence, ensure_ascii=False)
    hay = flatten(payload)
    haystack_numbers = set(numbers_in(payload))
    probes = gold_probes(gold, gold_id)
    rows = []
    for probe in probes:
        needles = probe["needles"]
        if probe["mode"] == "number" or (probe["value"] is not None and probe["tolerance_pct"]):
            want = as_number(probe["value"])
            tol = float(probe.get("tolerance_pct") or 0) / 100.0
            present = any(abs(n - want) <= abs(want) * tol + 1e-9 for n in haystack_numbers) \
                if want is not None else False
        elif not needles:
            present = False
        elif probe["mode"] == "all":
            present = all(flatten(n) in hay for n in needles)
        else:
            present = any(flatten(n) in hay for n in needles)
        rows.append(collections.OrderedDict([("id", probe["id"]), ("label", probe["label"]),
                                             ("present", bool(present)),
                                             ("needles", len(needles))]))
    total = len(rows)
    return collections.OrderedDict([
        ("derivable", sum(1 for r in rows if r["present"])),
        ("total", total),
        ("sufficiency", round(sum(1 for r in rows if r["present"]) / float(total), 4)
         if total else None),
        ("note", "deterministic probe over the evidence payload; it says the material is "
                 "there, not that a reader would use it"),
        ("probes", rows)])


# ------------------------------------------------------ derive from a report ---
def evidence_from_report(report, case=None):
    """Turn a finished report.json into evidence items, deterministically.

    This is what lets a single-agent run be verified without being re-run: every
    labelled number, every metric and every fixed answer becomes an item. Most carry no
    quote, so most come back `unknown` rather than `pass` - which is exactly the point.
    An unverified number is not a verified one.
    """
    items = []
    candidates = report.get("candidates") or []
    candidate = candidates[0] if candidates else {}
    flat = ((candidate.get("identity") or {}).get("flat")
            if isinstance(candidate.get("identity"), dict) else None)
    for key, metric in sorted((candidate.get("metrics") or {}).items()):
        if not isinstance(metric, dict) or metric.get("value") is None:
            continue
        items.append(collections.OrderedDict([
            ("id", "m-" + key), ("axis", 1), ("claim", key.replace("_", " ")),
            ("status", "ok"), ("value", metric.get("value")),
            ("unit", metric.get("unit")),
            ("source", (metric.get("sources") or [None])[0]),
            ("quote", None), ("note", metric.get("meaning")),
            ("computed_by", metric.get("computed_by"))]))
    for axis in candidate.get("axes") or []:
        if not isinstance(axis, dict):
            continue
        for i, number in enumerate(axis.get("numbers") or [], 1):
            if not isinstance(number, dict):
                continue
            items.append(collections.OrderedDict([
                ("id", "a%s-%d" % (axis.get("id"), i)), ("axis", axis.get("id") or 1),
                ("claim", number.get("label") or ""), ("status", "ok"),
                ("value", number.get("value")), ("unit", number.get("unit")),
                ("source", (number.get("sources") or [None])[0]),
                ("quote", None),
                ("note", number.get("meaning") or number.get("compared_to")),
                ("computed_by", number.get("computed_by"))]))
    for answer in candidate.get("fixed_answers") or []:
        if not isinstance(answer, dict):
            continue
        status = "unknown" if answer.get("status") == "unknown" else "ok"
        items.append(collections.OrderedDict([
            ("id", "f-" + str(answer.get("id"))), ("axis", 7),
            ("claim", "%s %s" % (answer.get("id"), answer.get("answer") or "")),
            ("status", status), ("value", answer.get("answer")),
            ("unit", None), ("source", answer.get("source")),
            ("quote", answer.get("quote")), ("note", answer.get("note")),
            ("tried", [] if status == "unknown" else None)]))
    for item in items:
        for key in [k for k, v in item.items() if v is None and k in ("computed_by", "tried")]:
            del item[key]
    return collections.OrderedDict([("schema", EVIDENCE_SCHEMA), ("case", case),
                                    ("flat", flat), ("items", items)])


# ------------------------------------------------------------------- assembly --
def verify(evidence, report=None, pasted=None, tier="standard", strict=False,
           thresholds=None, questions_path=None, rent_pcm=None, gold=None, gold_id=None,
           case=None):
    items = [i for i in (evidence.get("items") or []) if isinstance(i, dict)]
    pasted = pasted or {}
    source_ids = report_source_ids(report)
    flat = evidence.get("flat")
    thresholds = thresholds if thresholds is not None else load_thresholds()

    unique_ids(items)
    verdicts = collections.OrderedDict()
    for item in items:
        state, reason, rules = check_item(item, pasted, source_ids, {}, flat, strict)
        verdicts[item.get("id")] = collections.OrderedDict([
            ("id", item.get("id")), ("state", state), ("reason", reason),
            ("rules", rules), ("checked_by", "verify.py")])

    caps, working = cap_checks(items, thresholds, rent_pcm)
    for problem in caps:
        mark_fail(verdicts, [problem["item"]], problem["rule"], problem["reason"])
    clashes = contradictions(items)
    for problem in clashes:
        mark_fail(verdicts, problem["items"], problem["rule"], problem["reason"])

    missing_fixed, wanted_fixed = fixed_form_check(items, report, tier, questions_path)

    replan = []
    for verdict in verdicts.values():
        if verdict["state"] == "fail":
            replan.append(collections.OrderedDict([
                ("axis", axis_of(items, verdict["id"])), ("item", verdict["id"]),
                ("ask", "go back for this one: %s" % (verdict["reason"] or "")), ("round", 1)]))
    for qid in missing_fixed:
        replan.append(collections.OrderedDict([
            ("axis", 7), ("item", None),
            ("ask", "the fixed form owes %s an answer at the %s tier; find it or ask the "
                    "user once" % (qid, tier)), ("round", 1)]))

    # A quote we hold no text for is not a checked quote. It does not fail the item -
    # we have no evidence against it - but a run where most passes are unchecked is a
    # different thing from one where they were read, and the scorecard should say which.
    unchecked = [i.get("id") for i in items
                 if (i.get("status") or "ok") != "unknown" and i.get("quote")
                 and source_text(i, pasted, {}) is None]

    states = [v["state"] for v in verdicts.values()]
    counts = collections.OrderedDict([
        ("items", len(items)),
        ("pass", states.count("pass")), ("fail", states.count("fail")),
        ("unknown", states.count("unknown")),
        ("quotes_unchecked", unchecked),
        ("fixed_form_tier", tier),
        ("fixed_form_wanted", len(wanted_fixed)),
        ("fixed_form_missing", missing_fixed),
        ("contradictions", len(clashes)),
        ("cap_failures", len(caps)),
        ("legal_caps", working)])

    out = collections.OrderedDict([
        ("schema", SCHEMA), ("case", case or evidence.get("case")),
        ("checked_at", now()), ("items", list(verdicts.values())),
        ("replan", replan), ("counts", counts)])
    if gold is not None:
        out["sufficiency"] = sufficiency(evidence, gold, gold_id)
    return out


def unique_ids(items):
    """Give every item an id nobody else has, in place, before anything is keyed by it.

    evidence.json is written by a model, so a missing or repeated id is the schema
    violation to expect - and the verdicts are a map from id, so two items sharing one
    would collapse into a single verdict and a failure would simply disappear. Renaming
    happens before the verdict loop so the cap and contradiction checks see the same ids.
    """
    seen = set()
    for n, item in enumerate(items, 1):
        ident = item.get("id")
        if not ident or ident in seen:
            ident = "item-%d" % n
            while ident in seen:
                ident += "x"
            item["id"] = ident
        seen.add(ident)
    return items


def axis_of(items, item_id):
    for item in items:
        if item.get("id") == item_id:
            return item.get("axis") or 1
    return 1


def mark_fail(verdicts, ids, rule, reason):
    """Fail these items for this rule, without repeating a rule or a reason it already has.

    One area item can be in three contradiction pairs at once; saying so three times in
    one line helps nobody.
    """
    for item_id in ids:
        verdict = verdicts.get(item_id)
        if verdict is None:
            continue
        verdict["state"] = "fail"
        if rule not in verdict["rules"]:
            verdict["rules"] = list(verdict["rules"]) + [rule]
        current = verdict.get("reason") or ""
        if reason and reason not in current:
            verdict["reason"] = "; ".join(x for x in (current, reason) if x)


def failed(result):
    """True when anything failed: an item, or the fixed form for this tier."""
    if any(v["state"] == "fail" for v in result.get("items") or []):
        return True
    return bool((result.get("counts") or {}).get("fixed_form_missing"))


def table(result):
    counts = result.get("counts") or {}
    lines = ["verify: %s items - %s pass, %s fail, %s unknown"
             % (counts.get("items"), counts.get("pass"), counts.get("fail"),
                counts.get("unknown")),
             "%-14s %-8s %s" % ("item", "state", "why")]
    for verdict in result.get("items") or []:
        lines.append("%-14s %-8s %s" % (verdict.get("id"), verdict.get("state"),
                                        verdict.get("reason") or ""))
    if counts.get("legal_caps"):
        caps = counts["legal_caps"]
        lines.append("legal caps from rent %s (%s): deposit %g weeks = %s, holding %s, "
                     "advance %g month(s)"
                     % (caps.get("rent_pcm"), caps.get("rent_pcm_from"),
                        caps.get("deposit_cap_weeks"), caps.get("deposit_cap_gbp"),
                        caps.get("holding_deposit_cap_gbp"),
                        caps.get("rent_in_advance_max_months")))
    if counts.get("quotes_unchecked"):
        lines.append("quotes not checked (no text held for the source): %s"
                     % ", ".join(counts["quotes_unchecked"]))
    if counts.get("fixed_form_missing"):
        lines.append("fixed form (%s tier) still owes: %s"
                     % (counts.get("fixed_form_tier"),
                        ", ".join(counts["fixed_form_missing"])))
    if result.get("sufficiency"):
        suff = result["sufficiency"]
        lines.append("information sufficiency: %s of %s derivable from this evidence (%s)"
                     % (suff.get("derivable"), suff.get("total"), suff.get("sufficiency")))
        for probe in suff.get("probes") or []:
            lines.append("   %-8s %-6s %s" % (probe.get("id"),
                                              "yes" if probe.get("present") else "NO",
                                              probe.get("label") or ""))
    if result.get("replan"):
        lines.append("replan (one round only): %d item(s)" % len(result["replan"]))
    return "\n".join(lines)


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("evidence", nargs="?", help="evidence.json from the executors")
    ap.add_argument("--report", help="report.json, for the source ids and the fixed form")
    ap.add_argument("--sources", help="a folder of pasted sources; 'pasted:listing' is "
                                      "the file whose name or stem is 'listing'")
    ap.add_argument("--tier", default="standard",
                    help="the fixed-form tier this run owes an answer to")
    ap.add_argument("--strict", action="store_true",
                    help="an unknown with nothing in `tried` counts as a failure")
    ap.add_argument("--rent-pcm", dest="rent_pcm", type=float,
                    help="the monthly rent, when the evidence does not carry it")
    ap.add_argument("--thresholds", help="a different thresholds.yaml")
    ap.add_argument("--questions", help="a different fixed-questions.yaml")
    ap.add_argument("--gold", help="BENCH ONLY: run the information-sufficiency probe")
    ap.add_argument("--gold-id", dest="gold_id", help="which candidate in the gold file")
    ap.add_argument("--from-report", dest="from_report",
                    help="derive evidence items from a finished report.json and print them")
    ap.add_argument("--table", action="store_true", help="a plain table instead of JSON")
    ap.add_argument("--out", help="write verified.json here as well as stdout")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.from_report:
        try:
            report = read_json(args.from_report)
        except (IOError, OSError, ValueError) as exc:
            print("could not read %s: %s" % (args.from_report, exc), file=sys.stderr)
            return 1
        print(json.dumps(evidence_from_report(report), ensure_ascii=False, indent=1))
        return 0
    if not args.evidence:
        print("usage error: give an evidence.json, or --from-report report.json",
              file=sys.stderr)
        return 2
    try:
        evidence = read_json(args.evidence)
        report = read_json(args.report) if args.report else None
        gold = read_json(args.gold) if args.gold else None
        thresholds = load_thresholds(args.thresholds)
    except (IOError, OSError, ValueError, scan.QuestionsError) as exc:
        print("could not read an input: %s" % exc, file=sys.stderr)
        return 1

    result = verify(evidence, report, load_sources(args.sources), args.tier, args.strict,
                    thresholds, args.questions, args.rent_pcm, gold, args.gold_id)
    text = table(result) if args.table else json.dumps(result, ensure_ascii=False, indent=1)
    print(text)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    return 1 if failed(result) else 0


if __name__ == "__main__":
    sys.exit(main())
