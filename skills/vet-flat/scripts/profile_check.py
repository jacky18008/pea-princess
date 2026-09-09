#!/usr/bin/env python3
"""Validate profile.yaml and explain problems in plain words (no model needed).

Cheap models write profiles fine but sometimes invent fields or values. Run this after every
change: it lists unknown keys, bad enum values, out-of-range numbers and inconsistent settings.
Usage:  profile_check.py profile.yaml [--json]
Exit 0 = valid (warnings allowed), 1 = errors.
Parses YAML with PyYAML when available, else a small built-in reader for the subset this
profile uses (mappings, lists of strings or mappings, scalars, comments).
"""
import argparse
import json
import math
import re
import sys

AXES = {"identity", "floor_area", "age_fabric", "construction", "crime", "management", "compliance",
        "price", "aspect_light", "all_in_cost", "commute", "livability", "bridging", "referencing",
        "admin", "street_view"}
ENUMS = {
    "flat_type": {"room_in_shared_flat", "studio", "one_bed", "two_bed", "three_bed_plus", "any"},
    "experience": {"none", "some", "expert"},
    "budget_mode": {"lite", "standard", "deep"},
    "guarantor_route": None,  # free text
    "commute.redundancy_min_grade": {"A", "B", "B-", "C"},
    "bridging.first_weeks": {"hotel_or_operator", "private_short_let", "undecided"},
    "advanced.fixed_form.questions": {"auto", "gate", "standard", "full"},
    "advanced.fixed_form.ask_if_missing": {"gate", "all", "none"},
    "language": None,
}
# The optional Advanced block: every key it may hold, and nothing else. A typo here is
# silence, not an error message, so the validator names it instead.
ADVANCED = {"fixed_form": {"questions", "ask_if_missing"}}
KNOWN_TOP = {"flat_type", "separate_bedroom_required", "occupants", "experience", "budget_mode", "axis_depth",
             "limits", "avoid", "priorities", "min_room_area_m2", "min_floor_area_sqft", "max_building_age_years",
             "budget", "bridging", "move_in_window", "commute", "floors", "light", "quiet_over_light",
             "must_haves", "nice_to_haves", "guarantor_route", "tenancy", "self_intro_template",
             "story_summary", "story_taken_on", "language", "my_questions", "models", "advanced"}
RANGES = {"min_floor_area_sqft": (150, 3000), "min_room_area_m2": (6, 60), "max_building_age_years": (0, 300),
          "budget.rent_pcm_target": (300, 20000), "budget.all_in_pcm_ceiling": (300, 25000),
          "commute.max_door_to_door_min": (5, 180), "occupants": (1, 12),
          "limits.max_fetches_per_flat": (1, 500), "limits.max_minutes_per_flat": (1, 240),
          "tenancy.max_months_upfront": (0, 12), "tenancy.max_deposit_weeks": (0, 6)}


def _mini_yaml(text):
    """Subset reader: nested mappings by indentation, lists of scalars or of flat mappings, scalars."""
    lines = [l.rstrip("\n") for l in text.splitlines()]
    def parse_block(i, indent):
        result = {}
        while i < len(lines):
            raw = lines[i]
            if not raw.strip() or raw.strip().startswith("#"):
                i += 1; continue
            ind = len(raw) - len(raw.lstrip(" "))
            if ind < indent:
                break
            line = raw.strip()
            if line.startswith("- "):
                break
            m = re.match(r'^([A-Za-z0-9_.\-]+):\s*(.*)$', line)
            if not m:
                i += 1; continue
            key, val = m.group(1), m.group(2).split(" #")[0].strip()
            if val == "" or val in (">-", ">", "|", "|-"):
                # block scalar or nested
                j = i + 1
                if val in (">-", ">", "|", "|-"):
                    buf = []
                    while j < len(lines) and (not lines[j].strip() or (len(lines[j]) - len(lines[j].lstrip(" "))) > ind):
                        buf.append(lines[j].strip()); j += 1
                    result[key] = " ".join(b for b in buf if b); i = j; continue
                # list?
                k = j
                while k < len(lines) and (not lines[k].strip() or lines[k].strip().startswith("#")):
                    k += 1
                if k < len(lines) and lines[k].strip().startswith("- "):
                    items = []
                    while k < len(lines):
                        rawk = lines[k]
                        if not rawk.strip() or rawk.strip().startswith("#"):
                            k += 1; continue
                        indk = len(rawk) - len(rawk.lstrip(" "))
                        if indk <= ind or not rawk.strip().startswith("- "):
                            break
                        item = rawk.strip()[2:].strip()
                        mm = re.match(r'^([A-Za-z0-9_.\-]+):\s*(.*)$', item)
                        if mm and not item.startswith('"'):
                            d = {mm.group(1): _scalar(mm.group(2))}
                            k += 1
                            while k < len(lines) and lines[k].strip() and not lines[k].strip().startswith("- ") and (len(lines[k]) - len(lines[k].lstrip(" "))) > indk:
                                m2 = re.match(r'^([A-Za-z0-9_.\-]+):\s*(.*)$', lines[k].strip())
                                if m2: d[m2.group(1)] = _scalar(m2.group(2))
                                k += 1
                            items.append(d)
                        else:
                            items.append(_scalar(item)); k += 1
                    result[key] = items; i = k; continue
                sub, i2 = parse_block(j, ind + 1)
                result[key] = sub; i = i2; continue
            if val.startswith("{") and val.endswith("}"):
                d = {}
                for part in val[1:-1].split(","):
                    if ":" in part:
                        a, b = part.split(":", 1); d[a.strip()] = _scalar(b.strip())
                result[key] = d
            else:
                result[key] = _scalar(val)
            i += 1
        return result, i
    return parse_block(0, 0)[0]


def _scalar(v):
    v = v.strip()
    if v == "" or v in ("null", "~"):
        return None
    if v.startswith('"') and v.endswith('"') or v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v) if re.match(r'^-?\d+$', v) else float(v) if re.match(r'^-?\d+\.\d+$', v) else v
    except ValueError:
        return v


def load(path):
    text = open(path, encoding="utf-8").read()
    try:
        import yaml  # type: ignore
        value = yaml.safe_load(text)
        return {} if value is None else value
    except ImportError:
        return _mini_yaml(text)


def get(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def check(profile):
    errors, warnings = [], []
    if not isinstance(profile, dict):
        return ["the profile must be a block of named settings, not a list or single value"], []
    for k in profile:
        if k not in KNOWN_TOP:
            errors.append(f"unknown field '{k}' — the agent may have invented it; remove or rename")
    for key, allowed in ENUMS.items():
        v = get(profile, key)
        if allowed and v not in (None, "") and str(v) not in allowed:
            errors.append(f"'{key}' is '{v}'; allowed: {', '.join(sorted(allowed))}")
    for key, (lo, hi) in RANGES.items():
        v = get(profile, key)
        if v is None or v == "":
            continue
        if (isinstance(v, bool) or not isinstance(v, (int, float))
                or (isinstance(v, float) and not math.isfinite(v))):
            errors.append(f"'{key}' must be a finite number, not text, a boolean or a list")
        elif not (lo <= v <= hi):
            errors.append(f"'{key}' = {v} is outside the sensible range {lo}–{hi}")
    for key in ("axis_depth", "limits", "budget", "bridging", "move_in_window", "commute",
                "floors", "light", "tenancy", "models"):
        if profile.get(key) is not None and not isinstance(profile[key], dict):
            errors.append(f"'{key}' must be a block of settings, not a list or single value")
    adv = profile.get("advanced")
    if adv is not None:
        if not isinstance(adv, dict):
            errors.append("'advanced' must be a block of settings, not a single value")
        else:
            for key, value in adv.items():
                if key not in ADVANCED:
                    errors.append(f"advanced: unknown setting '{key}'; known: {', '.join(sorted(ADVANCED))}")
                elif not isinstance(value, dict):
                    errors.append(f"advanced.{key} must be a block of settings, not a single value")
                else:
                    for sub in value:
                        if sub not in ADVANCED[key]:
                            errors.append(f"advanced.{key}: unknown setting '{sub}'; "
                                          f"known: {', '.join(sorted(ADVANCED[key]))}")
    ad = profile.get("axis_depth") or {}
    if isinstance(ad, dict):
        for axis, depth in ad.items():
            if axis not in AXES:
                errors.append(f"axis_depth: unknown axis '{axis}'; known: {', '.join(sorted(AXES))}")
            if depth not in ("lite", "standard", "deep"):
                errors.append(f"axis_depth.{axis} = '{depth}'; allowed: lite, standard, deep")
    rent, ceiling = get(profile, "budget.rent_pcm_target"), get(profile, "budget.all_in_pcm_ceiling")
    if isinstance(rent, (int, float)) and isinstance(ceiling, (int, float)) and rent > ceiling:
        errors.append(f"rent target {rent} is above the all-in ceiling {ceiling}; bills come on top of rent")
    if isinstance(rent, (int, float)) and isinstance(ceiling, (int, float)) and ceiling - rent < 80:
        warnings.append(f"only {ceiling - rent} left for bills between rent {rent} and ceiling {ceiling}; London bills rarely fit in that")
    mq = profile.get("my_questions") or []
    for q in mq:
        if isinstance(q, dict):
            if q.get("when") not in (None, "filter", "vet", "compare", "viewing", "sign"):
                errors.append(f"my_questions.when = '{q.get('when')}'; allowed: filter, vet, compare, viewing, sign")
            if q.get("kind") not in (None, "answer", "ask", "check"):
                errors.append(f"my_questions.kind = '{q.get('kind')}'; allowed: answer, ask, check")
            if not q.get("text"):
                errors.append("a my_questions entry has no text")
    for key in ("commute.destination",):
        if not get(profile, key):
            warnings.append(f"'{key}' is empty; the commute axis cannot run without it")
    for forbidden in ("nationality", "ethnicity", "religion", "visa"):
        if forbidden in json.dumps(profile, ensure_ascii=False).lower():
            errors.append(f"the profile mentions '{forbidden}'; the skill does not use that and it must not be stored")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profile"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    prof = load(a.profile)
    errors, warnings = check(prof)
    if a.json:
        json.dump({"valid": not errors, "errors": errors, "warnings": warnings}, sys.stdout, ensure_ascii=False, indent=1); print()
    else:
        for e in errors: print("ERROR:", e)
        for w in warnings: print("warning:", w)
        print("valid" if not errors else f"{len(errors)} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
