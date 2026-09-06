#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print the plan scaffold for one flat: what to fetch, what to paste, what to ask.

This is the deterministic floor under the PLANNER role of references/pipeline.md. It
reads profile.yaml, the budget mode and the fixed-form tier, and prints a plan.json
(references/plan-schema.json) with the axes this depth works, the script commands for
each, the paste requests only the user can answer, and the fixed-question ids the run
owes an answer to. It reads no pages and fetches nothing.

WHAT THE PLANNER MAY DO TO IT
=============================
Add. A planner that knows the building spans two postcodes adds a second search; a
planner that reads "communal heat network" in the request adds the supplier lookup.
What it may NOT do is shrink the scaffold: drop an axis this mode works, drop a call
the scaffold marked required, or drop a fixed-question id the tier asks for.

  plan.py --check plan.json --mode standard

says whether anything required went missing, and exits 1 if it did. That is the whole
honesty mechanism: the planner decides WHAT TO GET, never what survives, and the check
is deterministic so it cannot be talked round.

The axis-to-depth mapping follows references/budget-modes.md; the fixed-question ids
come from the `tiers` block of references/fixed-questions.yaml and are never counted
in code.

Not a network tool. Standard library only, Python 3.9.

Usage:
  plan.py --mode standard --postcode "SE1 9SG" --flat 301        > plan.json
  plan.py --profile profile.yaml --case v2-buck                  > plan.json
  plan.py --mode lite --table                                    # the same thing as a table
  plan.py --check plan.json --mode standard                      # nothing required was dropped?
  plan.py --check plan.json --mode standard --table

Exit codes: 0 ok, 1 the check found something missing (or a file could not be read),
2 wrong arguments.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")
DEFAULT_QUESTIONS = os.path.join(REFS, "fixed-questions.yaml")

sys.path.insert(0, HERE)
import scan  # noqa: E402  the fixed-questions reader; the tiers live in one place only

MODES = ("lite", "standard", "deep")
SCHEMA = "vet-flat/plan/1"

# One executor takes one group, so axes that share a fetch share a group. Keeping the
# groups small is what lets the executors run in parallel without doing each other's
# work twice.
GROUP_OF = {1: "identity-area", 2: "identity-area",
            3: "fabric",
            4: "neighbourhood", 5: "neighbourhood",
            6: "people", 7: "people",
            8: "money", 10: "money",
            9: "place", 12: "place",
            11: "commute"}

AXIS_NAMES = {1: "identity", 2: "floor area", 3: "age and fabric",
              4: "construction nearby", 5: "crime",
              6: "management and neighbours", 7: "agent and landlord compliance",
              8: "price", 9: "aspect and light", 10: "all-in cost",
              11: "commute and redundancy", 12: "low-maintenance living"}

# Which axes each depth actually WORKS. An axis a mode does not work is not in the plan
# at all; the report still carries all twelve and marks that one unknown, which is what
# references/budget-modes.md means by "12 axes with U where skipped".
AXES_BY_MODE = {
    "lite": [1, 2, 3, 5, 7, 8, 10, 11],
    "standard": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "deep": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
}

# axis -> mode -> [(command template, why)]. A command is a template: the angle brackets
# are filled from the profile and the arguments, and an executor that cannot fill one
# writes an unknown item rather than guessing.
CALLS = {
    1: {"lite": [('scripts/geo.py lookup "<postcode>"',
                  "coordinates, borough and ward; every other axis keys off these"),
                 ('scripts/epc.py search --postcode "<postcode>"',
                  "the flats the register holds at this postcode, to pick the right one")],
        "standard": [], "deep": [('scripts/epc.py building --postcode "<postcode>"',
                                  "the whole building's certificates in one call")]},
    2: {"lite": [("scripts/epc.py cert <certificate_id>",
                  "certified internal area, from the certificate for THIS flat")],
        "standard": [],
        "deep": [("scripts/epc.py cert <certificate_id> --history",
                  "earlier certificates: a subdivided unit shows up here and nowhere else")]},
    3: {"lite": [], "standard": [],
        "deep": [("scripts/company.py heat-supplier <company_number>",
                  "when the heating is a communal network, who sells the heat")]},
    4: {"standard": [("scripts/planning.py near --lat <lat> --lng <lng> --radius 250 --limit 20",
                      "applications within 250 m; a discharged condition means work starts")],
        "deep": [("scripts/planning.py stages <application_reference>",
                  "how far along a nearby scheme is"),
                 ("scripts/roads.py near --lat <lat> --lng <lng>",
                  "which elevation faces a major road")]},
    5: {"lite": [("scripts/crime.py box --lat <lat> --lng <lng> --months 3 --no-sensitivity",
                  "the standard box, short window, no sensitivity sweep")],
        "standard": [("scripts/crime.py box --lat <lat> --lng <lng> --months 6 --no-sensitivity",
                      "the standard box over the fixed six-month window")],
        "deep": [("scripts/crime.py box --lat <lat> --lng <lng> --months 6",
                  "six months with the plus or minus 20 m sensitivity range")]},
    6: {"standard": [], "deep": []},
    7: {"lite": [("scripts/company.py profile <company_number>",
                  "the legal entity behind the agent or the landlord"),
                 ("scripts/calc.py deposit --rent-pcm <rent_pcm>",
                  "the deposit cap, with the right branch, computed not guessed")],
        "standard": [('scripts/company.py search --name "<agent_name>"',
                      "same-name shells and dissolved companies"),
                     ('scripts/redress.py cmp --agent "<agent_name>"',
                      "client money protection")],
        "deep": [('scripts/redress.py rogue --name "<agent_name>"',
                  "the rogue landlord and agent checker"),
                 ("scripts/company.py filings <company_number>",
                  "filed accounts: a heat supplier selling below cost predicts a tariff rise")]},
    8: {"lite": [("scripts/calc.py price-per-sqft --rent-pcm <rent_pcm> --area-m2 <area_m2>",
                  "pounds per square foot on the certified area, not the advertised one")],
        "standard": [],
        "deep": [('scripts/landregistry.py price-paid --postcode "<postcode>"',
                  "what the flats here actually sold for, and when they were new")]},
    9: {"standard": [], "deep": [("scripts/streetview.py brief --lat <lat> --lng <lng>",
                                  "what the window actually faces")]},
    10: {"lite": [("scripts/calc.py all-in --rent-pcm <rent_pcm> --bills-low <bills_low> "
                   "--bills-planning <bills_planning> --bills-stress <bills_stress>",
                   "rent plus bills plus council tax, one basis for every candidate")],
         "standard": [], "deep": []},
    11: {"lite": [('scripts/commute.py journey --from "<postcode>" --to "<destination>"',
                   "door to door, at the arrival time the profile asks for")],
         "standard": [("scripts/commute.py redundancy --lat <lat> --lng <lng>",
                       "a second independent rail family within a ten-minute walk")],
         "deep": [("scripts/commute.py stations --lat <lat> --lng <lng>",
                   "which stations they actually are")]},
    12: {"standard": [], "deep": [("scripts/geo.py nearby --lat <lat> --lng <lng> --radius 500",
                                   "what is inside a short walk")]},
}

# What only the user can supply, per axis, from the mode it starts to matter at.
PASTE = {
    2: {"standard": ["The floor plan, if the advert has one: the advertised area is a claim "
                     "and the certificate is the arbiter."]},
    6: {"standard": ["The resident reviews for this building, lowest first, with their dates. "
                     "Review sites forbid automated access, so they have to be pasted."],
        "deep": ["Any press or forum thread about the building's management."]},
    7: {"lite": ["The tenancy agreement or the offer email, for the deposit, the holding "
                 "deposit and the rent in advance."]},
    9: {"standard": ["A photo out of the window, or the compass on the floor plan."]},
    12: {"standard": ["What the advert says about bills, the washing machine and parcels."]},
}

SOURCES = {1: ["postcodes_io_lookup", "epc_register_search"],
           2: ["epc_register_certificate"],
           3: ["epc_register_certificate", "companies_house_profile"],
           4: ["planning_london_datahub"],
           5: ["police_uk_street_crime"],
           6: [],
           7: ["companies_house_profile", "companies_house_search"],
           8: ["land_registry_price_paid"],
           9: [],
           10: [],
           11: ["tfl_journey_planner"],
           12: ["postcodes_io_nearest"]}

# Every mode inherits the shallower one's calls, so `deep` really is `standard` plus.
INHERITS = {"lite": [], "standard": ["lite"], "deep": ["lite", "standard"]}


def calls_for(axis, mode):
    """[(cmd, why)] for this axis at this depth, shallower depths first."""
    out = []
    table = CALLS.get(axis) or {}
    for step in INHERITS[mode] + [mode]:
        for cmd, why in table.get(step) or []:
            out.append((cmd, why))
    return out


def paste_for(axis, mode):
    out = []
    table = PASTE.get(axis) or {}
    for step in INHERITS[mode] + [mode]:
        for item in table.get(step) or []:
            out.append(item)
    return out


def fill(text, values):
    """Replace <placeholder> with the value when we have one; leave it in when we do not.

    The templates already carry the quotes where a value can contain a space, so this
    substitutes plainly: adding another pair here would produce ""SE1 9SG"".
    """
    def swap(match):
        value = values.get(match.group(1))
        return match.group(0) if value in (None, "") else str(value)
    return re.sub(r"<([a-z_]+)>", swap, text)


def scaffold(mode="standard", tier=None, values=None, case=None, questions_path=None):
    """The plan every planner starts from. Deterministic: same inputs, same file."""
    if mode not in MODES:
        raise ValueError("budget mode must be one of %s" % ", ".join(MODES))
    values = values or {}
    tier = tier or mode
    questions_path = questions_path or DEFAULT_QUESTIONS
    doc = scan.load_document(questions_path)
    ids = scan.ids_for_tier(doc.get("questions") or {}, doc.get("tiers") or {}, tier)

    axes = []
    asked = []
    for axis in AXES_BY_MODE[mode]:
        calls = [collections.OrderedDict([("cmd", fill(cmd, values)), ("why", why),
                                          ("required", True)])
                 for cmd, why in calls_for(axis, mode)]
        pastes = paste_for(axis, mode)
        asked.extend(pastes)
        axes.append(collections.OrderedDict([
            ("id", axis), ("name", AXIS_NAMES[axis]), ("group", GROUP_OF[axis]),
            ("required", True), ("scripts", calls),
            ("sources", list(SOURCES.get(axis) or [])),
            ("paste_requests", pastes)]))

    skipped = [AXIS_NAMES[a] for a in sorted(AXIS_NAMES) if a not in AXES_BY_MODE[mode]]
    notes = ("Axes not worked at this depth, and unknown in the report: %s."
             % ", ".join(skipped)) if skipped else None
    return collections.OrderedDict([
        ("schema", SCHEMA), ("case", case), ("budget_mode", mode), ("tier", tier),
        ("axes", axes), ("fixed_form_ids", ids),
        ("user_questions", asked), ("notes", notes)])


# ------------------------------------------------------------------- checking --
FLAG = re.compile(r"(--[a-z][a-z0-9-]*)")


def call_shape(cmd):
    """(script, subcommand, frozenset of long flags) - what a call IS, minus its values.

    The planner fills the placeholders in, so `epc.py search --postcode "SE1 9SG"` has to
    read as the same call as `epc.py search --postcode "<postcode>"`. Values are dropped
    and only the shape is compared: the check is about what was DROPPED, never about
    whether an argument is right.
    """
    tokens = (cmd or "").split()
    script, sub = "", ""
    for token in tokens:
        if token.startswith("-"):
            continue
        base = os.path.basename(token)
        if not script and base.endswith(".py"):
            script = base
            continue
        if script and not sub:
            sub = base
            break
    return script, sub, frozenset(FLAG.findall(cmd or ""))


def check(plan, mode="standard", tier=None, questions_path=None, values=None):
    """{ok, missing_axes, missing_calls, missing_fixed_form_ids, added_*} - did it shrink?"""
    want = scaffold(mode, tier, values or {}, questions_path=questions_path)
    problems = collections.OrderedDict([
        ("ok", True), ("schema_ok", plan.get("schema") == SCHEMA),
        ("budget_mode", mode), ("tier", want["tier"]),
        ("missing_axes", []), ("missing_calls", []), ("missing_fixed_form_ids", []),
        ("added_axes", []), ("added_calls", 0)])

    got_axes = {}
    for axis in plan.get("axes") or []:
        if isinstance(axis, dict) and isinstance(axis.get("id"), int):
            got_axes[axis["id"]] = axis
    for axis in want["axes"]:
        found = got_axes.get(axis["id"])
        if found is None:
            problems["missing_axes"].append(
                collections.OrderedDict([("id", axis["id"]), ("name", axis["name"])]))
            for call in axis["scripts"]:
                problems["missing_calls"].append(
                    collections.OrderedDict([("axis", axis["id"]), ("cmd", call["cmd"])]))
            continue
        shapes = set(call_shape(c.get("cmd")) for c in (found.get("scripts") or [])
                     if isinstance(c, dict))
        for call in axis["scripts"]:
            if call_shape(call["cmd"]) not in shapes:
                problems["missing_calls"].append(
                    collections.OrderedDict([("axis", axis["id"]), ("cmd", call["cmd"])]))
        problems["added_calls"] += max(0, len(found.get("scripts") or []) - len(axis["scripts"]))
    for axis_id in sorted(set(got_axes) - set(a["id"] for a in want["axes"])):
        problems["added_axes"].append(axis_id)

    got_ids = set(plan.get("fixed_form_ids") or [])
    problems["missing_fixed_form_ids"] = [qid for qid in want["fixed_form_ids"]
                                          if qid not in got_ids]
    problems["ok"] = bool(problems["schema_ok"]
                          and not problems["missing_axes"]
                          and not problems["missing_calls"]
                          and not problems["missing_fixed_form_ids"])
    return problems


# --------------------------------------------------------------------- output --
def plan_table(plan):
    lines = ["plan: %s mode, %s tier, %d axes, %d fixed questions"
             % (plan.get("budget_mode"), plan.get("tier"), len(plan.get("axes") or []),
                len(plan.get("fixed_form_ids") or [])),
             "%-4s %-28s %-14s %s" % ("axis", "name", "group", "calls")]
    for axis in plan.get("axes") or []:
        lines.append("%-4s %-28s %-14s %d"
                     % (axis.get("id"), axis.get("name"), axis.get("group"),
                        len(axis.get("scripts") or [])))
        for call in axis.get("scripts") or []:
            lines.append("       %s" % call.get("cmd"))
        for ask in axis.get("paste_requests") or []:
            lines.append("       ask: %s" % ask)
    lines.append("fixed form: %s" % ", ".join(plan.get("fixed_form_ids") or []))
    if plan.get("notes"):
        lines.append("note: %s" % plan["notes"])
    return "\n".join(lines)


def check_table(result):
    lines = ["check: %s" % ("nothing required was dropped" if result["ok"] else "SHRUNK")]
    if not result["schema_ok"]:
        lines.append("  the file does not say schema: %s" % SCHEMA)
    for axis in result["missing_axes"]:
        lines.append("  missing axis %s (%s)" % (axis["id"], axis["name"]))
    for call in result["missing_calls"]:
        lines.append("  missing call on axis %s: %s" % (call["axis"], call["cmd"]))
    if result["missing_fixed_form_ids"]:
        lines.append("  missing fixed questions: %s"
                     % ", ".join(result["missing_fixed_form_ids"]))
    if result["added_axes"]:
        lines.append("  added axes (fine): %s"
                     % ", ".join(str(a) for a in result["added_axes"]))
    if result["added_calls"]:
        lines.append("  added calls (fine): %d" % result["added_calls"])
    return "\n".join(lines)


def profile_values(path):
    """The placeholders profile.yaml can fill. Missing keys just stay placeholders."""
    if not path or not os.path.exists(path):
        return {}, None
    sys.path.insert(0, HERE)
    import profile_check  # noqa: E402  the repository's own profile reader
    profile = profile_check.load(path)
    get = profile_check.get
    values = {"destination": get(profile, "commute.destination"),
              "rent_pcm": get(profile, "budget.rent_pcm_target"),
              "bills_low": get(profile, "budget.bills_low_pcm"),
              "bills_planning": get(profile, "budget.bills_planning_pcm"),
              "bills_stress": get(profile, "budget.bills_stress_pcm")}
    return dict((k, v) for k, v in values.items() if v not in (None, "")), \
        profile.get("budget_mode")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", help="profile.yaml; its budget_mode is the default mode")
    ap.add_argument("--mode", choices=MODES, help="budget mode; default from the profile, "
                                                  "else standard")
    ap.add_argument("--tier", help="fixed-form tier; default the same word as the mode")
    ap.add_argument("--case", help="a short label for this flat, never an address")
    ap.add_argument("--postcode", help="fills <postcode> in the call templates")
    ap.add_argument("--flat", help="the flat as the register writes it, for the record")
    ap.add_argument("--destination", help="fills <destination>")
    ap.add_argument("--rent-pcm", dest="rent_pcm", help="fills <rent_pcm>")
    ap.add_argument("--questions", default=DEFAULT_QUESTIONS,
                    help="a different fixed-questions.yaml")
    ap.add_argument("--check", help="a plan.json to check against the scaffold")
    ap.add_argument("--table", action="store_true", help="a plain table instead of JSON")
    ap.add_argument("--out", help="write to this file as well as stdout")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    values, profile_mode = {}, None
    if args.profile:
        if not os.path.exists(args.profile):
            print("no profile at %s" % args.profile, file=sys.stderr)
            return 2
        values, profile_mode = profile_values(args.profile)
    mode = args.mode or profile_mode or "standard"
    if mode not in MODES:
        print("budget mode must be one of %s (profile says %r)" % (", ".join(MODES), mode),
              file=sys.stderr)
        return 2
    for key, value in (("postcode", args.postcode), ("destination", args.destination),
                       ("rent_pcm", args.rent_pcm), ("flat", args.flat)):
        if value:
            values[key] = value

    if args.check:
        try:
            with io.open(args.check, encoding="utf-8") as fh:
                plan = json.load(fh, object_pairs_hook=collections.OrderedDict)
        except (IOError, OSError, ValueError) as exc:
            print("could not read %s: %s" % (args.check, exc), file=sys.stderr)
            return 1
        result = check(plan, mode, args.tier, args.questions, values)
        print(check_table(result) if args.table
              else json.dumps(result, ensure_ascii=False, indent=1))
        return 0 if result["ok"] else 1

    try:
        plan = scaffold(mode, args.tier, values, args.case, args.questions)
    except (scan.QuestionsError, ValueError) as exc:
        print("%s" % exc, file=sys.stderr)
        return 1
    text = plan_table(plan) if args.table else json.dumps(plan, ensure_ascii=False, indent=1)
    print(text)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
