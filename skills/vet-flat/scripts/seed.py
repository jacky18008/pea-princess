#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn a profile.yaml into a shareable seed (a card plus a short code), and read one back.

Not a data source: this script fetches nothing and needs no network, no key and no login.
It reads the user's own `profile.yaml`, keeps only the fields on the allow-list below, turns
money into a band and the commute destination into a postcode district, and prints:

  1. a **seed card** — three sentences drafted from the profile plus a compact YAML block, for
     a person to read; the agent may rewrite the three sentences before posting them.
  2. a **seed code** — `PP1.` followed by base64url of a minimal JSON of the same fields, short
     enough to paste into a social post. `references/seed-format.md` specifies it exactly, so an
     agent with no shell can write and read one by hand.

What is shared is an allow-list, not a deny-list: a field that is not listed cannot leak,
whatever the profile grows later. Never shared, even when present: any address, any person's or
company's name, the guarantor route, income, savings, the self-introduction, exact dates,
tenancy terms, and everything under `bridging` except the `first_weeks` choice.

Shared: name (yours, for the seed), flat type, budget as a band, budget_mode, commute district,
move-in month, must_haves, avoid, priorities, my_questions, floor rules, light rules,
quiet_over_light, bridging.first_weeks, story_summary.

Usage:
  seed.py export --profile profile.yaml
  seed.py export --profile profile.yaml --name "quiet, high, morning sun"
  seed.py export --profile profile.yaml --journey journey.json
  seed.py export --profile profile.yaml --exact            # real numbers instead of a band
  seed.py export --profile profile.yaml --commute-area "Zone 1"   # or --hide-commute
  seed.py export --profile profile.yaml --json             # the machine object, for other tools
  seed.py import "PP1.eyJ2IjoxLC..."
  seed.py import seed-card.txt --out profile.yaml

Standard library only, Python 3.9. Exit codes: 0 ok, 1 the input could not be used, 2 usage error.
Errors go to stderr; the card, the code and the import summary go to stdout.
"""
from __future__ import unicode_literals

import argparse
import base64
import datetime as dt
import io
import json
import math
import os
import re
import sys

PREFIX = "PP1."
SEED_VERSION = 1
DEFAULT_MAX_CODE = 400

# --------------------------------------------------------------- the allow-list
# (seed field, short key in the JSON). Nothing outside this table is ever encoded,
# printed on the card or written back on import.
ALLOW = [
    ("name", "n"),                  # a label the user chose for the seed, not their own name
    ("flat_type", "t"),
    ("budget_band", "b"),
    ("budget_mode", "m"),
    ("commute_area", "c"),
    ("move_in_month", "w"),
    ("must_haves", "mh"),
    ("avoid", "av"),
    ("priorities", "pr"),
    ("my_questions", "qs"),         # the questions the user makes every report answer
    ("floors", "fl"),               # {reject_ground_floor, prefer_floor_band}
    ("light", "li"),                # {reject_no_sky, best_aspects}
    ("quiet_over_light", "q"),
    ("first_weeks", "fw"),          # the one key allowed out of `bridging`
    ("story_summary", "s"),
]
LONG_TO_SHORT = dict(ALLOW)
SHORT_TO_LONG = dict((s, l) for l, s in ALLOW)
FLOOR_KEYS = ("reject_ground_floor", "prefer_floor_band")
LIGHT_KEYS = ("reject_no_sky", "best_aspects")

# Named so that a reader can see what the scrub is for. These never reach the seed even if a
# profile, a journey label or a hand-written seed carries them.
FORBIDDEN = (
    "address", "postcode", "street", "building", "building_name", "flat_number",
    "landlord", "agent", "employer", "occupation", "phone", "email", "full_name",
    "guarantor_route", "income", "annual_income", "salary", "savings", "proof_of_funds",
    "self_intro_template", "self_intro",
    "destination", "arrive_by", "max_door_to_door_min", "redundancy_min_grade",
    "rent_pcm_target", "all_in_pcm_ceiling", "stretch_ceiling_and_conditions",
    "earliest", "latest", "tolerance_days", "occupants",
    "max_months_upfront", "max_deposit_weeks", "require_deposit_protection",
    "date_of_birth", "nationality", "ethnicity", "religion", "immigration_status", "health",
    "models", "workers", "judge",
)
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s*[0-9][A-Z]{2}\b", re.I)
OUTWARD_RE = re.compile(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?)\s*[0-9][A-Z]{2}\b", re.I)
CODE_RE = re.compile(r"PP1\.[A-Za-z0-9_-]+")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
FLAT_TYPES = {
    "studio": "a studio",
    "one_bed": "a one-bedroom flat",
    "two_bed": "a two-bedroom flat",
    "three_bed_plus": "a flat with three bedrooms or more",
    "any": "a flat of any size",
}
FIRST_WEEKS = {
    "hotel_or_operator": "a hotel or an operator-run stay for the first weeks",
    "private_short_let": "a private short let for the first weeks, viewed first",
    "undecided": "no decision yet on the first weeks",
}
VERDICTS = ["PASS", "EDGE", "CONDITIONAL", "KILL"]
# The five stages of a search and the three things that answer a question. A bare string means
# `when: vet, kind: answer`; `trigger` stays in the profile and is never shared.
WHEN = ["filter", "vet", "compare", "viewing", "sign"]
KIND = ["answer", "ask", "check"]
WHEN_DEFAULT, KIND_DEFAULT = "vet", "answer"


def die(msg, code=1):
    sys.stderr.write(msg.rstrip() + "\n")
    raise SystemExit(code)


# ------------------------------------------------------------------ mini YAML --
# The same deliberately small subset the other scripts read: nested maps, `- ` lists,
# scalars, `>-` and `|` blocks. Enough for profile.yaml and nothing more.
def _strip_comment(line):
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (not out or out[-1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _scalar(text):
    text = text.strip()
    if not text:
        return None
    if len(text) > 1 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    low = text.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _rows(text):
    rows = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = _strip_comment(raw)
        if not line.strip():
            continue
        rows.append((len(line) - len(line.lstrip(" ")), line.strip(), raw))
    return rows


def _block_scalar(lines, start, indent, fold):
    body, i = [], start
    while i < len(lines):
        raw = lines[i]
        if raw.strip() and (len(raw) - len(raw.lstrip(" "))) <= indent:
            break
        body.append(raw[indent + 1:] if len(raw) > indent else "")
        i += 1
    while body and not body[-1].strip():
        body.pop()
    joined = " ".join(x.strip() for x in body if x.strip()) if fold else "\n".join(body)
    return joined, i


def parse_yaml(text):
    raw_lines = text.replace("\r\n", "\n").split("\n")
    rows = _rows(text)
    index = {}                       # row -> position in raw_lines, for block scalars
    pos = 0
    for depth, body, raw in rows:
        while pos < len(raw_lines) and raw_lines[pos] != raw:
            pos += 1
        index[len(index)] = pos
        pos += 1

    def parse(i, indent):
        if i < len(rows) and rows[i][1].startswith("- "):
            items = []
            while i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
                head = rows[i][1][2:]
                key, sep, rest = head.partition(":")
                if sep and KEY_RE.match(key.strip()):        # `- text: ...`, a map in a list
                    item = {key.strip(): _scalar(rest)}
                    i += 1
                    while (i < len(rows) and rows[i][0] > indent
                           and not rows[i][1].startswith("- ")):
                        k2, s2, v2 = rows[i][1].partition(":")
                        if s2 and KEY_RE.match(k2.strip()):
                            item[k2.strip()] = _scalar(v2)
                        i += 1
                    items.append(item)
                else:
                    items.append(_scalar(head))
                    i += 1
            return items, i
        out = {}
        while i < len(rows) and rows[i][0] == indent and not rows[i][1].startswith("- "):
            body = rows[i][1]
            if ":" not in body:
                i += 1
                continue
            key, _, rest = body.partition(":")
            key, rest = key.strip(), rest.strip()
            if rest in (">", ">-", "|", "|-"):
                value, _end = _block_scalar(raw_lines, index[i] + 1, indent, rest.startswith(">"))
                out[key] = value or None
                i += 1
                while i < len(rows) and rows[i][0] > indent:
                    i += 1
                continue
            if rest:
                out[key] = _scalar(rest)
                i += 1
                continue
            if i + 1 < len(rows) and rows[i + 1][0] > indent:
                child, i = parse(i + 1, rows[i + 1][0])
                out[key] = child
            else:
                out[key] = None
                i += 1
        return out, i

    if not rows:
        return {}
    value, _ = parse(0, rows[0][0])
    return value if isinstance(value, dict) else {}


def read_yaml(path):
    if not os.path.exists(path):
        die("no such file: %s" % path)
    try:
        with io.open(path, encoding="utf-8") as fh:
            return parse_yaml(fh.read())
    except Exception as exc:                                          # noqa: BLE001
        die("could not read %s (%s)" % (path, exc))


# ------------------------------------------------------------------- the scrub --
def strip_postcodes(text):
    """Take any UK postcode out of free text. Labels are meant to have none; belt and braces."""
    if not isinstance(text, str):
        return text
    return re.sub(r"\s{2,}", " ", POSTCODE_RE.sub("[postcode removed]", text)).strip()


def clean_questions(value, limit=5):
    """`my_questions` as {text, when, kind}. A bare string is {text, vet, answer}; `trigger`
    is dropped here, because it is the one part of a question that stays at home."""
    out = []
    for item in (value or []):
        if isinstance(item, dict):
            text, when, kind = item.get("text"), item.get("when"), item.get("kind")
        elif isinstance(item, str):
            text, when, kind = item, None, None
        else:
            continue
        text = strip_postcodes(str(text or "").strip())[:200]
        if not text or text.lower() in [q["text"].lower() for q in out]:
            continue
        when = str(when or "").strip().lower()
        kind = str(kind or "").strip().lower()
        out.append({"text": text,
                    "when": when if when in WHEN else WHEN_DEFAULT,
                    "kind": kind if kind in KIND else KIND_DEFAULT})
    return out[:limit]


def question_label(question):
    """`[compare]`, or `[viewing - ask]` when answering it takes more than the data."""
    if question.get("kind", KIND_DEFAULT) == KIND_DEFAULT:
        return "[%s]" % question.get("when", WHEN_DEFAULT)
    return "[%s \u00b7 %s]" % (question.get("when", WHEN_DEFAULT), question["kind"])


def clean_list(value, limit=8, width=120):
    out = []
    for item in (value or []):
        if isinstance(item, (dict, list)) or item is None:
            continue
        text = strip_postcodes(str(item).strip())
        if text and text.lower() not in [x.lower() for x in out]:
            out.append(text[:width])
    return out[:limit]


def band(ceiling, exact=False, label="all-in"):
    if ceiling is None:
        return None
    try:
        value = float(ceiling)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    if exact:
        return "£%s %s" % (format(int(round(value)), ","), label)
    high = int(math.ceil(value / 100.0) * 100)
    width = 200 if high < 1500 else 400
    low = max(0, high - width)
    return "£%s–%s %s" % (format(low, ","), format(high, ","), label)


def district(destination):
    """A commute destination reduced to its postcode district, or None."""
    if not destination:
        return None
    found = OUTWARD_RE.search(str(destination))
    return found.group(1).upper() if found else None


def month_of(*dates):
    for value in dates:
        if not value:
            continue
        text = str(value).strip()
        if re.match(r"^\d{4}-\d{2}", text):
            return text[:7]
    return None


def best_aspects(scores):
    if not isinstance(scores, dict):
        return []
    pairs = []
    for key, value in scores.items():
        try:
            pairs.append((float(value), str(key).upper()))
        except (TypeError, ValueError):
            continue
    if not pairs:
        return []
    top = max(p[0] for p in pairs)
    if top < 4:
        return []
    return [name for score, name in sorted(pairs, key=lambda p: (-p[0], p[1])) if score >= top][:3]


def shareable(profile, name=None, exact=False, commute_area=None, hide_commute=False):
    """Everything on the allow-list, and nothing else, from a parsed profile.yaml."""
    profile = profile or {}
    budget = profile.get("budget") or {}
    window = profile.get("move_in_window") or {}
    commute = profile.get("commute") or {}
    floors = profile.get("floors") or {}
    light = profile.get("light") or {}
    bridging = profile.get("bridging") or {}
    if not isinstance(budget, dict):
        budget = {}

    money = band(budget.get("all_in_pcm_ceiling"), exact)
    if money is None:
        money = band(budget.get("rent_pcm_target"), exact, label="rent, bills on top")
    if exact and budget.get("all_in_pcm_ceiling") and budget.get("rent_pcm_target"):
        money = "%s (rent target £%s)" % (money, format(int(budget["rent_pcm_target"]), ","))

    if hide_commute:
        area = None
    elif commute_area:
        area = strip_postcodes(str(commute_area).strip())[:40] or None
    else:
        area = district((commute or {}).get("destination"))

    seed = {
        "version": SEED_VERSION,
        "name": (strip_postcodes(str(name).strip())[:60] if name else None) or None,
        "flat_type": profile.get("flat_type") or None,
        "budget_band": money,
        "budget_mode": profile.get("budget_mode") or None,
        "commute_area": area,
        "move_in_month": month_of(window.get("earliest"), window.get("latest")),
        "must_haves": clean_list(profile.get("must_haves")),
        "avoid": clean_list(profile.get("avoid")),
        "priorities": clean_list(profile.get("priorities"), limit=3),
        "my_questions": clean_questions(profile.get("my_questions")),
        "floors": {
            "reject_ground_floor": bool(floors.get("reject_ground_floor")) if isinstance(floors, dict) else False,
            "prefer_floor_band": (str(floors.get("prefer_floor_band"))[:20]
                                  if isinstance(floors, dict) and floors.get("prefer_floor_band") else None),
        },
        "light": {
            "reject_no_sky": bool(light.get("reject_no_sky")) if isinstance(light, dict) else False,
            "best_aspects": best_aspects((light or {}).get("aspect_scores")),
        },
        "quiet_over_light": bool(profile.get("quiet_over_light")),
        "first_weeks": (bridging.get("first_weeks") if isinstance(bridging, dict) else None) or None,
        "story_summary": (strip_postcodes(str(profile["story_summary"]))[:600]
                          if profile.get("story_summary") else None),
    }
    return seed


def dropped_fields(profile):
    """Which forbidden keys the profile actually held, so the user can see the scrub working."""
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN and value not in (None, "", [], {}):
                    found.append("/".join(path + [str(key)]))
                walk(value, path + [str(key)])
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(profile or {}, [])
    return sorted(set(found))


# ------------------------------------------------------------- code and JSON --
def questions_to_json(questions):
    """A question at the defaults travels as a bare string; anything else as an object."""
    out = []
    for question in questions or []:
        if (question.get("when", WHEN_DEFAULT) == WHEN_DEFAULT
                and question.get("kind", KIND_DEFAULT) == KIND_DEFAULT):
            out.append(question["text"])
        else:
            out.append({"text": question["text"], "when": question.get("when", WHEN_DEFAULT),
                        "kind": question.get("kind", KIND_DEFAULT)})
    return out


def to_min_json(seed):
    """The minimal JSON object behind the code: short keys, empty values left out."""
    out = {"v": SEED_VERSION}
    for long_key, short in ALLOW:
        value = seed.get(long_key)
        if long_key == "my_questions":
            value = questions_to_json(value)
        elif long_key == "floors":
            value = dict((k, v) for k, v in (value or {}).items() if v not in (None, False, "", []))
        elif long_key == "light":
            value = dict((k, v) for k, v in (value or {}).items() if v not in (None, False, "", []))
        if value in (None, "", [], {}, False):
            continue
        out[short] = value
    return out


def from_min_json(obj):
    if not isinstance(obj, dict):
        raise ValueError("a seed must be a JSON object")
    if int(obj.get("v", 0)) != SEED_VERSION:
        raise ValueError("this seed says version %r; this script reads version %d"
                         % (obj.get("v"), SEED_VERSION))
    seed = {"version": SEED_VERSION}
    for long_key, short in ALLOW:
        seed[long_key] = obj.get(short)
    # shape the two nested blocks and drop anything the sender invented
    floors = seed.get("floors") if isinstance(seed.get("floors"), dict) else {}
    light = seed.get("light") if isinstance(seed.get("light"), dict) else {}
    seed["floors"] = {"reject_ground_floor": bool(floors.get("reject_ground_floor")),
                      "prefer_floor_band": floors.get("prefer_floor_band") or None}
    seed["light"] = {"reject_no_sky": bool(light.get("reject_no_sky")),
                     "best_aspects": clean_list(light.get("best_aspects"), limit=3)}
    seed["my_questions"] = clean_questions(seed.get("my_questions"))
    for key in ("must_haves", "avoid", "priorities"):
        seed[key] = clean_list(seed.get(key), limit=3 if key == "priorities" else 8)
    for key in ("name", "flat_type", "budget_band", "budget_mode", "commute_area",
                "move_in_month", "first_weeks", "story_summary"):
        seed[key] = strip_postcodes(str(seed[key]))[:600] if seed.get(key) else None
    seed["quiet_over_light"] = bool(seed.get("quiet_over_light"))
    return seed


def encode(obj):
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    raw = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return PREFIX + raw


def decode(code):
    code = (code or "").strip()
    if not code.startswith(PREFIX):
        raise ValueError("a seed code starts with %s" % PREFIX)
    body = re.sub(r"\s+", "", code[len(PREFIX):])
    if not body:
        raise ValueError("the seed code has nothing after %s" % PREFIX)
    body += "=" * (-len(body) % 4)
    try:
        payload = base64.urlsafe_b64decode(body.encode("ascii")).decode("utf-8")
    except Exception as exc:                                          # noqa: BLE001
        raise ValueError("the seed code is not base64url (%s)" % exc)
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise ValueError("the seed code does not hold JSON (%s)" % exc)


def make_code(seed, max_code=DEFAULT_MAX_CODE):
    """The code, shortened by one documented step if it would be too long to paste."""
    obj = to_min_json(seed)
    code = encode(obj)
    trimmed = []
    if max_code and len(code) > max_code and "s" in obj:
        del obj["s"]
        trimmed.append("story_summary (it stays on the card)")
        code = encode(obj)
    return code, obj, trimmed


# -------------------------------------------------------------- the sentences --
def _join(items, last="and"):
    items = [x for x in items if x]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return "%s %s %s" % (", ".join(items[:-1]), last, items[-1])


def sentences(seed):
    """Three sentences: what I want, what I refuse, how I trade money for quality."""
    floors = seed.get("floors") or {}
    light = seed.get("light") or {}
    want = [FLAT_TYPES.get(seed.get("flat_type"), "a flat")]
    if floors.get("prefer_floor_band"):
        want.append("on floors %s" % floors["prefer_floor_band"])
    if light.get("best_aspects"):
        want.append("with windows facing %s" % _join(light["best_aspects"], "or"))
    if seed.get("commute_area"):
        want.append("within reach of %s" % seed["commute_area"])
    if seed.get("move_in_month"):
        want.append("from %s" % pretty_month(seed["move_in_month"]))
    if seed.get("budget_band"):
        want.append("at %s" % seed["budget_band"])
    one = "I want %s" % ", ".join(want)
    if seed.get("must_haves"):
        one += "; it must have %s" % _join(seed["must_haves"][:3])
    if seed.get("priorities"):
        one += "; and I rank %s in that order" % _join(seed["priorities"])
    one += "."

    refuse = list(seed.get("avoid") or [])
    if floors.get("reject_ground_floor") and not any("ground" in x.lower() for x in refuse):
        refuse.insert(0, "a ground-floor flat")
    if light.get("reject_no_sky"):
        refuse.append("windows that cannot see sky")
    two = ("I will not take: %s." % "; ".join(refuse[:5])) if refuse else "I have no absolute deal-breakers."

    lowered = [x.lower() for x in (seed.get("priorities") or [])]
    where = next((i for i, x in enumerate(lowered) if x in ("price", "budget", "cost", "cheap")), None)
    if where == 0:
        three = "Price leads: I take the cheapest home that clears every rule above"
    elif where is None:
        three = ("Price is not in my top three: I will pay to the top of the band for a benefit "
                 "I can name")
    else:
        three = ("Price sits %s of my three priorities: I will pay towards the top of the band for "
                 "a benefit I can name" % ("second" if where == 1 else "last"))
    three += (", and quiet wins when quiet and light conflict."
              if seed.get("quiet_over_light") else ", and I would rather have light than silence.")
    if seed.get("first_weeks") in FIRST_WEEKS and seed["first_weeks"] != "undecided":
        three += " I plan on %s." % FIRST_WEEKS[seed["first_weeks"]]
    quotable = next((q["text"] for q in (seed.get("my_questions") or [])
                     if len(q.get("text") or "") <= 100), None)
    if quotable:
        three += " I ask of every flat: \u201c%s\u201d" % quotable
    return [one, two, three]


def pretty_month(value):
    try:
        year, month = str(value).split("-")[:2]
        return "%s %s" % (MONTHS[int(month) - 1], year)
    except Exception:                                                 # noqa: BLE001
        return str(value)


# ------------------------------------------------------------------ the card --
def yaml_scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value)
    if text and (text[0] in "\"'&*#?|-<>=!%@`[{" or text[0].isdigit() or ":" in text
                 or "–" in text or text.strip() != text):
        return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')
    return text


def yaml_block(seed, indent="  "):
    rows, out = [], []
    rows.append(("name", seed.get("name")))
    rows.append(("flat_type", seed.get("flat_type")))
    rows.append(("budget_band", seed.get("budget_band")))
    rows.append(("budget_mode", seed.get("budget_mode")))
    rows.append(("commute_area", seed.get("commute_area")))
    rows.append(("move_in_month", seed.get("move_in_month")))
    for key, value in rows:
        if value:
            out.append("%s%s: %s" % (indent, key, yaml_scalar(value)))
    if seed.get("my_questions"):
        out.append("%s# My questions \u2014 every report has to answer each of these by name,"
                   " at the stage in brackets" % indent)
        out.append("%smy_questions:" % indent)
        for question in seed["my_questions"]:
            out.append("%s  - %s" % (indent, yaml_scalar("%s %s" % (question_label(question),
                                                                   question["text"]))))
    for key in ("priorities", "must_haves", "avoid"):
        values = seed.get(key) or []
        if values:
            out.append("%s%s:" % (indent, key))
            out.extend("%s  - %s" % (indent, yaml_scalar(v)) for v in values)
    floors = seed.get("floors") or {}
    if floors.get("reject_ground_floor") or floors.get("prefer_floor_band"):
        out.append("%sfloors:" % indent)
        if floors.get("reject_ground_floor"):
            out.append("%s  reject_ground_floor: yes" % indent)
        if floors.get("prefer_floor_band"):
            out.append("%s  prefer_floor_band: %s" % (indent, yaml_scalar(floors["prefer_floor_band"])))
    light = seed.get("light") or {}
    if light.get("reject_no_sky") or light.get("best_aspects"):
        out.append("%slight:" % indent)
        if light.get("reject_no_sky"):
            out.append("%s  reject_no_sky: yes" % indent)
        if light.get("best_aspects"):
            out.append("%s  best_aspects:" % indent)
            out.extend("%s    - %s" % (indent, a) for a in light["best_aspects"])
    out.append("%squiet_over_light: %s" % (indent, "yes" if seed.get("quiet_over_light") else "no"))
    if seed.get("first_weeks"):
        out.append("%sfirst_weeks: %s" % (indent, yaml_scalar(seed["first_weeks"])))
    if seed.get("story_summary"):
        out.append("%sstory_summary: >-" % indent)
        out.extend("%s  %s" % (indent, line) for line in wrap(seed["story_summary"], 88))
    return "\n".join(out)


def wrap(text, width):
    words, line, out = str(text).split(), "", []
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out or [""]


def journey_lines(journey, reveal_address=False):
    """The "what I found" lines: how many flats, what the verdicts were, what was chosen."""
    if not journey:
        return []
    candidates = [c for c in (journey.get("candidates") or []) if isinstance(c, dict)]
    counts = {}
    for cand in candidates:
        status = str(cand.get("verdict") or "").upper()
        if status in VERDICTS:
            counts[status] = counts.get(status, 0) + 1
    tally = ", ".join("%d %s" % (counts[v], v) for v in VERDICTS if counts.get(v))
    lines = []
    head = "what I found: %d flat%s vetted" % (len(candidates), "" if len(candidates) == 1 else "s")
    if tally:
        head += " — %s" % tally
    if journey.get("started"):
        head += " (since %s)" % strip_postcodes(str(journey["started"]))[:10]
    lines.append(head + ".")
    chosen = journey.get("chosen") if isinstance(journey.get("chosen"), dict) else None
    if chosen:
        bits = [strip_postcodes(str(chosen.get("label") or "the one I took"))[:120]]
        if chosen.get("floor") not in (None, ""):
            bits.append("floor %s" % chosen["floor"])
        if chosen.get("area_m2"):
            bits.append("about %s m²" % chosen["area_m2"])
        if chosen.get("all_in_band"):
            bits.append(str(chosen["all_in_band"]))
        if chosen.get("verdict"):
            bits.append("verdict %s" % str(chosen["verdict"]).upper())
        line = "chose: %s." % (bits[0] if len(bits) == 1 else "%s — %s" % (bits[0], ", ".join(bits[1:])))
        if reveal_address and chosen.get("address"):
            line = line[:-1] + " — %s." % chosen["address"]
        lines.append(line)
    return lines


def card(seed, code, journey=None, reveal_address=False, trimmed=None):
    title = "Pea Princess seed"
    if seed.get("name"):
        title += " — %s" % seed["name"]
    out = [title,
           "what I am looking for, and nothing about where I live, what I earn or who I am.",
           ""]
    out.extend(sentences(seed))
    out.append("")
    out.append("seed:")
    out.append(yaml_block(seed))
    found = journey_lines(journey, reveal_address)
    if found:
        out.append("")
        out.extend(found)
    out.append("")
    out.append("seed code (paste it into any AI agent that has the Pea Princess skill, "
               "and it will set itself up the way I did):")
    out.append(code)
    if trimmed:
        out.append("(the code leaves out the %s to stay short enough to paste; it is on the card "
                   "above)" % _join([t.split(" (")[0] for t in trimmed]))
    return "\n".join(out) + "\n"


# ------------------------------------------------------- writing a profile back --
BLANKS = [
    ("min_floor_area_sqft", "the smallest indoor area you will accept, in square feet"),
    ("max_building_age_years", "the oldest building you will accept, in years"),
    ("budget.rent_pcm_target", "the rent you are aiming at, before bills"),
    ("budget.all_in_pcm_ceiling", "your real ceiling: rent plus bills plus council tax"),
    ("budget.stretch_ceiling_and_conditions", "what you would pay more for, and how much more"),
    ("move_in_window.earliest", "the earliest date you can take the keys"),
    ("move_in_window.latest", "the latest date you can take the keys"),
    ("commute.destination", "where you must get to most days (this seed only carries a district)"),
    ("commute.max_door_to_door_min", "the longest door-to-door journey you will accept"),
    ("guarantor_route", "how you will pass the landlord's income check"),
    ("self_intro_template", "one neutral sentence about yourself for enquiries"),
]


def profile_yaml(seed, code, today=None):
    """A profile.yaml carrying the seed's fields and a blank for everything else."""
    today = today or dt.date.today().isoformat()
    lines = [
        "# Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen "
        "— https://github.com/jacky18008/pea-princess — CC BY 4.0",
        "#",
        "# Written by scripts/seed.py import on %s from this seed code:" % today,
        "#   %s" % code,
        "# A seed carries preferences and bands only. Every line marked FILL IN is yours: nobody",
        "# else's budget, dates, destination or income check can be inherited, and the skill will",
        "# ask you for them once and then state them as assumptions.",
        "",
        "min_floor_area_sqft:                    # FILL IN",
        "max_building_age_years:                 # FILL IN",
        "flat_type: %s" % (seed.get("flat_type") or "one_bed"),
        "separate_bedroom_required: true         # FILL IN if a studio is fine",
        "occupants: 1                            # FILL IN",
        "budget_mode: %s" % (seed.get("budget_mode") or "standard"),
        "experience: none",
        "",
    ]
    if seed.get("story_summary"):
        lines.append("story_summary: >-")
        lines.extend("  %s" % line for line in wrap(seed["story_summary"], 88))
        lines.append("story_taken_on:                         # FILL IN if you keep this summary")
        lines.append("# The three sentences above came with the seed. Read them; if they are not")
        lines.append("# about you, delete them and do the five-minute story session yourself.")
        lines.append("")
    lines.append("avoid:")
    lines.extend("  - %s" % yaml_scalar(x) for x in (seed.get("avoid") or ["ground floor"]))
    lines.append("")
    lines.append("# Every report has to answer each of these by name, with evidence, at the stage")
    lines.append("# named in `when`. Add `trigger:` to any of them to say when it applies at all.")
    lines.append("my_questions:")
    for question in (seed.get("my_questions") or []):
        lines.append("  - text: %s" % yaml_scalar(question["text"]))
        lines.append("    when: %s" % question.get("when", WHEN_DEFAULT))
        lines.append("    kind: %s" % question.get("kind", KIND_DEFAULT))
    lines.append("")
    lines.append("priorities:")
    lines.extend("  - %s" % yaml_scalar(x) for x in (seed.get("priorities") or ["quiet", "commute", "price"]))
    lines.append("")
    lines.append("budget:")
    lines.append("  rent_pcm_target:                      # FILL IN")
    hint = (" — the seed said %s" % seed["budget_band"]) if seed.get("budget_band") else ""
    lines.append("  all_in_pcm_ceiling:                   # FILL IN%s" % hint)
    lines.append("  stretch_ceiling_and_conditions:       # FILL IN")
    lines.append("")
    lines.append("bridging:")
    lines.append("  first_weeks: %s" % (seed.get("first_weeks") or "undecided"))
    lines.append("")
    lines.append("move_in_window:")
    hint = (" \u2014 the seed said %s" % pretty_month(seed["move_in_month"])) if seed.get("move_in_month") else ""
    lines.append("  earliest:                             # FILL IN%s" % hint)
    lines.append("  latest:                               # FILL IN")
    lines.append("  tolerance_days: 0")
    lines.append("")
    lines.append("commute:")
    hint = (" \u2014 the seed only carried the district %s"
            % seed["commute_area"]) if seed.get("commute_area") else ""
    lines.append("  destination:                          # FILL IN%s" % hint)
    lines.append('  arrive_by: "09:00"')
    lines.append("  max_door_to_door_min:                 # FILL IN")
    lines.append('  redundancy_min_grade: "B"')
    lines.append("")
    floors = seed.get("floors") or {}
    lines.append("floors:")
    lines.append("  reject_ground_floor: %s" % ("true" if floors.get("reject_ground_floor") else "false"))
    lines.append("  prefer_floor_band: %s"
                 % ('"%s"' % floors["prefer_floor_band"] if floors.get("prefer_floor_band") else ""))
    lines.append("")
    light = seed.get("light") or {}
    lines.append("light:")
    lines.append("  reject_no_sky: %s" % ("true" if light.get("reject_no_sky") else "false"))
    lines.append("  aspect_scores:")
    top = [a.upper() for a in (light.get("best_aspects") or [])]
    for point in ("N", "NE", "E", "SE", "S", "SW", "W", "NW"):
        lines.append("    %s: %d" % (point, 5 if point in top else 2))
    lines.append("")
    lines.append("quiet_over_light: %s" % ("true" if seed.get("quiet_over_light") else "false"))
    lines.append("")
    lines.append("must_haves:")
    lines.extend("  - %s" % yaml_scalar(x) for x in (seed.get("must_haves") or []))
    lines.append("")
    lines.append("nice_to_haves:                          # FILL IN: seeds never carry these")
    lines.append("")
    lines.append("guarantor_route:                        # FILL IN")
    lines.append("")
    lines.append("tenancy:")
    lines.append("  max_months_upfront: 1")
    lines.append("  max_deposit_weeks: 5")
    lines.append("  require_deposit_protection: true")
    lines.append("")
    lines.append("self_intro_template:                    # FILL IN")
    lines.append("")
    lines.append('language: "en"')
    return "\n".join(line.rstrip() for line in lines) + "\n"


def import_summary(seed, code, out_path=None):
    got, missing = [], []
    labels = [("name", "seed name"), ("flat_type", "kind of home"), ("budget_band", "budget band"),
              ("budget_mode", "how deep the checks go"), ("commute_area", "commute district"),
              ("move_in_month", "move-in month"), ("priorities", "priorities"),
              ("must_haves", "must-haves"), ("avoid", "deal-breakers"),
              ("my_questions", "questions for every flat"),
              ("first_weeks", "plan for the first weeks"), ("story_summary", "three-sentence summary")]
    for key, label in labels:
        value = seed.get(key)
        if key == "my_questions":
            for n, question in enumerate(value or []):
                got.append("  %-26s %s %s" % ((label + ":") if n == 0 else "",
                                              question_label(question), question["text"]))
            continue
        if value:
            text = "; ".join(value) if isinstance(value, list) else str(value)
            got.append("  %-26s %s" % (label + ":", text if len(text) < 110 else text[:107] + "..."))
    floors, light = seed.get("floors") or {}, seed.get("light") or {}
    if floors.get("reject_ground_floor"):
        got.append("  %-26s %s" % ("floors:", "no ground floor"))
    if floors.get("prefer_floor_band"):
        got.append("  %-26s %s" % ("preferred floors:", floors["prefer_floor_band"]))
    if light.get("reject_no_sky"):
        got.append("  %-26s %s" % ("light:", "the windows must see sky"))
    if light.get("best_aspects"):
        got.append("  %-26s %s" % ("best aspects:", ", ".join(light["best_aspects"])))
    got.append("  %-26s %s" % ("quiet over light:", "yes" if seed.get("quiet_over_light") else "no"))
    for key, why in BLANKS:
        missing.append("  %-40s %s" % (key, why))
    out = ["Imported from %s" % code[:24] + ("..." if len(code) > 24 else ""), "",
           "What came with the seed (preferences only):"] + got
    out += ["", "What is still yours to fill in — a seed carries none of it:"] + missing
    if out_path:
        out += ["", "Written to %s. Open it, fill in every FILL IN line, and then start." % out_path]
    else:
        out += ["", "Nothing was written. Add --out profile.yaml to save it as a profile."]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ commands --
def cmd_export(args):
    profile = read_yaml(args.profile)
    if not isinstance(profile, dict) or not profile:
        die("%s does not look like a profile.yaml" % args.profile)
    seed = shareable(profile, name=args.name, exact=args.exact,
                     commute_area=args.commute_area, hide_commute=args.hide_commute)
    journey = None
    if args.journey:
        if not os.path.exists(args.journey):
            die("no such file: %s" % args.journey)
        try:
            with io.open(args.journey, encoding="utf-8") as fh:
                journey = json.load(fh)
        except ValueError as exc:
            die("%s is not valid JSON (%s)" % (args.journey, exc))
        if not isinstance(journey, dict):
            die("%s must hold one JSON object" % args.journey)
    code, minimal, trimmed = make_code(seed, args.max_code)
    text = card(seed, code, journey, args.reveal_address, trimmed)
    if args.json:
        json.dump({"command": "export", "seed": seed, "seed_json": minimal, "seed_code": code,
                   "code_length": len(code), "sentences": sentences(seed),
                   "card": text, "journey_lines": journey_lines(journey, args.reveal_address),
                   "trimmed_from_code": trimmed,
                   "scrubbed_from_profile": dropped_fields(profile),
                   "shared_fields": [k for k, _ in ALLOW],
                   "note": "preferences and bands only; see references/sharing.md"},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    sys.stdout.write(text)
    dropped = dropped_fields(profile)
    if dropped:
        sys.stderr.write("kept out of the seed: %s\n" % ", ".join(dropped))
    if args.max_code and len(code) > args.max_code:
        sys.stderr.write("the code is %d characters, over the %d you asked for. It still works; "
                         "if a site cuts it off, post the card and put the code in a reply, or "
                         "shorten `avoid` and `my_questions`\n" % (len(code), args.max_code))
    return 0


def read_code(source):
    """A code on the command line, or the first code inside a file (a saved card counts)."""
    text = source
    if not source.strip().startswith(PREFIX) and os.path.exists(source):
        try:
            with io.open(source, encoding="utf-8") as fh:
                text = fh.read()
        except Exception as exc:                                      # noqa: BLE001
            die("could not read %s (%s)" % (source, exc))
    found = CODE_RE.search(text.replace("\n", ""))
    if not found:
        die("no %s... code in %s" % (PREFIX, "that text" if text is source else source))
    return found.group(0)


def cmd_import(args):
    code = read_code(args.source)
    try:
        seed = from_min_json(decode(code))
    except ValueError as exc:
        die(str(exc))
    if args.out:
        if os.path.exists(args.out) and not args.force:
            die("%s already exists; pass --force to overwrite it" % args.out, 2)
        try:
            with io.open(args.out, "w", encoding="utf-8") as fh:
                fh.write(profile_yaml(seed, code))
        except Exception as exc:                                      # noqa: BLE001
            die("could not write %s (%s)" % (args.out, exc))
    if args.json:
        json.dump({"command": "import", "seed_code": code, "seed": seed,
                   "written_to": args.out, "still_to_fill_in": [k for k, _ in BLANKS],
                   "note": "a seed never carries budget numbers, dates, a destination or an "
                           "income-check route"},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    sys.stdout.write(import_summary(seed, code, args.out))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="seed.py", description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    subs = parser.add_subparsers(dest="cmd")

    export = subs.add_parser("export", help="write the seed card and the seed code")
    export.add_argument("--profile", required=True, help="path to profile.yaml")
    export.add_argument("--journey", help="path to journey.json (optional)")
    export.add_argument("--name", help='a label for this seed, e.g. "quiet, high, morning sun"')
    export.add_argument("--exact", action="store_true",
                        help="share the real budget numbers instead of a band")
    export.add_argument("--commute-area", dest="commute_area",
                        help='say the area by hand, e.g. "Zone 1" (default: the postcode district)')
    export.add_argument("--hide-commute", dest="hide_commute", action="store_true",
                        help="leave the commute area out altogether")
    export.add_argument("--reveal-address", dest="reveal_address", action="store_true",
                        help="print the chosen flat's address from journey.json (off by default)")
    export.add_argument("--max-code", dest="max_code", type=int, default=DEFAULT_MAX_CODE,
                        help="target length for the code (default %d)" % DEFAULT_MAX_CODE)
    export.add_argument("--json", action="store_true", help="print the machine object instead")
    export.set_defaults(func=cmd_export)

    imp = subs.add_parser("import", help="rebuild a profile.yaml from a seed code")
    imp.add_argument("source", help="a PP1. code, or a file holding one (a saved card counts)")
    imp.add_argument("--out", help="write the profile here (refuses to overwrite)")
    imp.add_argument("--force", action="store_true", help="overwrite --out if it exists")
    imp.add_argument("--json", action="store_true", help="print the machine object instead")
    imp.set_defaults(func=cmd_import)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(1)
