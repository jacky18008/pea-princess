#!/usr/bin/env python3
"""Area sweep orchestrator — one address in, compact machine facts per building out.

This is the cost gate of `references/axes/00-area-sweep.md` turned into a program.
It calls the other scripts in this directory as modules (never by shelling out) and
writes one small JSON file per stage under `--out`, so a run can be resumed and so
the model reads JSON only — never a raw page.

Sources, all official or open, all reached through the other scripts:
  postcodes.io (geo.py) - locating only; it returns at most 100 postcodes per call,
    so it can never enumerate a central-London circle.
  OpenStreetMap via Overpass (roads.py helpers) - the named residential streets in
    the circle. This is the enumerator. One further widened query serves every
    building's road, rail and daylight facts, because roads.py asks callers not to
    loop its query over a list of addresses.
  GOV.UK energy certificate register (epc.py) - one street-name search per street,
    then a sample of certificates per building. The register refuses to list a
    street with too many certificates and says to search by postcode instead, so
    the sweep does exactly that (--postcode-fallback); without it the busiest
    streets vanish silently.
  data.police.uk (crime.py), TfL (commute.py), GLA Planning Datahub (planning.py),
    Companies House (company.py), Heat Trust (redress.py), HM Land Registry
    (landregistry.py) - the per-building facts, for survivors only.
No key, no login and no fee is needed for any of it.

Volume note (read before widening the radius): the energy register's robots.txt
disallows crawling, so this tool keeps the 1.2 s per-host spacing built into
_fetch.py, caps the street census with `--max-streets`, and is meant for an area a
person is actually house-hunting in. A 3300 m radius in central London is hundreds
of street searches; `--dry-run` tells you how many before you spend them.

Stages (each writes its own file under --out; `--resume` reuses what is there):
  S0  anchor.json          the anchor, radius, profile and destination
  S1  buildings.json       streets -> certificates -> buildings (+ S1b exclusions)
  S2  filtered.json        certificate sample per building, hard filters, pass/fail
  S3  candidates/<key>.json  per-building facts, each <= 4 KB pretty-printed
  S4  ask-the-user.md      the review pages and listings only a person can fetch
  S5  summary.json, summary.md, report-skeleton.json
  --  manifest.json        every fetch: url, status, ok, note, retrieved_at

Usage:
  sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/
  sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
           --profile profile.yaml --max-buildings 4 --out sweep/
  sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/ --dry-run
Exit codes: 0 success, 2 usage error, 1 the sweep could not be started.
"""
import argparse
import copy
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _fetch                                     # noqa: E402
from _fetch import now_iso                        # noqa: E402
import commute                                    # noqa: E402
import company                                    # noqa: E402
import crime                                      # noqa: E402
import epc                                        # noqa: E402
import geo                                        # noqa: E402
import landregistry                               # noqa: E402
import planning                                   # noqa: E402
import redress                                    # noqa: E402
import roads                                      # noqa: E402

VERSION = "0.1"
DEFAULT_RADIUS_M = 800
MAX_RADIUS_M = 3300                 # about two miles; a warning, not a refusal
CANDIDATE_BUDGET_BYTES = 4096       # per-building JSON, pretty-printed
DEFAULT_TOWN = "London"

# Above this radius the one-query-per-sweep OpenStreetMap trick is dropped: the
# widened query would pull megabytes. Below it, every building is served from one
# Overpass answer, which is what roads.py asks for - its docstring says not to loop
# that query over a list of addresses.
SHARED_OVERPASS_MAX_M = 1200

# Highway values that carry homes. `service` is included only when the way is named,
# which is why every branch of the query below also requires a name.
STREET_HIGHWAYS = ("residential", "living_street", "tertiary", "unclassified",
                   "pedestrian", "service")

# ---------------------------------------------------------------- exclusions --
# Stage 1b. Matched case-insensitively against the building's display address and
# its name. A match never deletes the building: it sets `excluded_reason`, so a
# reader can see what was set aside and disagree.
EXCLUSION_PATTERNS = [
    ("student_accommodation",
     r"\bstudents?\b|\bhalls? of residence\b|\bstudent (?:village|house|court|hall)\b|"
     r"\bdormitor(?:y|ies)\b",
     "reads as purpose-built student accommodation or a hall of residence"),
    ("serviced_apartments",
     r"\bserviced (?:apartments?|suites?|accommodation|flats?)\b|\bapart[- ]?hotel\b|"
     r"\bshort[- ]?(?:stay|let|lets|term)\b|\bholiday (?:lets?|apartments?)\b",
     "reads as serviced apartments or an aparthotel, not a home to rent"),
    ("hotel_or_hostel",
     r"\bhotels?\b|\bhostels?\b|\bmotels?\b|\bguest ?house\b",
     "reads as a hotel or hostel"),
    ("care_or_retirement",
     r"\bcare home\b|\bnursing home\b|\bresidential home\b|\brest home\b|\bhospice\b|"
     r"\bretirement (?:home|village|living|court|apartments?)\b|"
     r"\bsheltered (?:housing|accommodation)\b|\bextra[- ]care\b|\balmshouses?\b",
     "reads as a care home, hospice or retirement scheme"),
]
_EXCLUSION_RE = [(name, re.compile(pat, re.I), why) for name, pat, why in EXCLUSION_PATTERNS]

# ------------------------------------------------------------------ manifest --
CURRENT_STAGE = "s0"


class Manifest(object):
    """Every fetch the run made, failures included. Never hides a failure."""

    def __init__(self):
        self.records = []
        self._orig = None

    def install(self, modules):
        """Wrap _fetch.fetch and rebind it inside each module that imported it."""
        if self._orig is not None:
            return
        self._orig = _fetch.fetch
        orig = self._orig
        records = self.records

        def recording_fetch(url, *a, **kw):
            res = orig(url, *a, **kw)
            records.append({
                "stage": CURRENT_STAGE,
                "url": (res.get("url") or url)[:400],
                "method": (kw.get("method") or "GET").upper(),
                "status": res.get("status"),
                "ok": bool(res.get("ok")),
                "note": (res.get("note") or "")[:200],
                "retrieved_at": res.get("retrieved_at"),
                "from_cache": bool(res.get("from_cache")),
            })
            return res

        _fetch.fetch = recording_fetch
        for mod in modules:
            if hasattr(mod, "fetch"):
                mod.fetch = recording_fetch

    def remove(self, modules):
        if self._orig is None:
            return
        _fetch.fetch = self._orig
        for mod in modules:
            if hasattr(mod, "fetch"):
                mod.fetch = self._orig
        self._orig = None

    @property
    def total(self):
        return len(self.records)

    @property
    def failures(self):
        return [r for r in self.records if not r["ok"]]

    @property
    def network_calls(self):
        return len([r for r in self.records if not r["from_cache"]])

    def summary(self):
        by_stage = Counter(r["stage"] for r in self.records)
        return {"fetches": self.total, "from_cache": self.total - self.network_calls,
                "network_calls": self.network_calls, "failures": len(self.failures),
                "by_stage": dict(sorted(by_stage.items()))}


FETCH_MODULES = (geo, epc, crime, commute, company, redress, landregistry, planning, roads)


# ------------------------------------------------------------- tiny yaml -----
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
    t = text.strip()
    if t == "" or t in ("~", "null", "Null", "NULL"):
        return None
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        return t[1:-1]
    low = t.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _yaml_lines(text):
    rows = []
    for raw in text.splitlines():
        stripped = raw.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        rows.append((len(raw) - len(stripped), _strip_comment(stripped)))
    return [(i, c) for i, c in rows if c]


def _parse_block(rows, start, indent):
    """Return (value, next_index) for the block at `indent` starting at `start`."""
    if start >= len(rows):
        return None, start
    if rows[start][1].startswith("- "):
        items, i = [], start
        while i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
            items.append(_scalar(rows[i][1][2:]))
            i += 1
        return items, i
    out, i = OrderedDict(), start
    while i < len(rows):
        ind, content = rows[i]
        if ind < indent:
            break
        if ind > indent:            # stray deeper line; skip rather than crash
            i += 1
            continue
        if ":" not in content:
            i += 1
            continue
        key, _, rest = content.partition(":")
        key, rest = key.strip(), rest.strip()
        if rest in (">", ">-", "|", "|-", ">+", "|+"):
            fold = rest[0] == ">"
            j, parts = i + 1, []
            while j < len(rows) and rows[j][0] > ind:
                parts.append(rows[j][1])
                j += 1
            out[key] = (" " if fold else "\n").join(parts)
            i = j
        elif rest == "":
            child, j = _parse_block(rows, i + 1, _child_indent(rows, i + 1, ind))
            out[key] = child if j > i + 1 else None
            i = max(j, i + 1)
        else:
            out[key] = _scalar(rest)
            i += 1
    return out, i


def _child_indent(rows, start, parent_indent):
    if start < len(rows) and rows[start][0] > parent_indent:
        return rows[start][0]
    return parent_indent + 2


def parse_yaml(text):
    """A deliberately small YAML subset: nested maps, scalars, '- ' lists, block
    scalars. Enough for profile.yaml and nothing more; anything else is ignored."""
    rows = _yaml_lines(text)
    if not rows:
        return {}
    value, _ = _parse_block(rows, 0, rows[0][0])
    return value or {}


PERMISSIVE_PROFILE = {
    "min_floor_area_sqft": None,
    "max_building_age_years": None,
    "reject_ground_floor": False,
    "destination": None,
    "arrive_by": "09:00",
    "max_door_to_door_min": None,
    "redundancy_min_grade": None,
    "language": "en",
}


def read_profile(path):
    """Return (profile_dict, source_note, warnings). No file = permissive defaults."""
    prof = dict(PERMISSIVE_PROFILE)
    warnings = []
    if not path:
        return prof, ("no --profile given: permissive defaults in use, so nothing is "
                      "filtered on area, age or floor"), warnings
    if not os.path.exists(path):
        warnings.append("profile file not found: %s" % path)
        return prof, "profile file %s not found: permissive defaults in use" % path, warnings
    try:
        with open(path, encoding="utf-8") as fh:
            raw = parse_yaml(fh.read())
    except Exception as exc:                                     # noqa: BLE001
        warnings.append("could not read %s (%s); permissive defaults in use" % (path, exc))
        return prof, "profile unreadable: permissive defaults in use", warnings
    prof["min_floor_area_sqft"] = raw.get("min_floor_area_sqft")
    prof["max_building_age_years"] = raw.get("max_building_age_years")
    floors = raw.get("floors") or {}
    if isinstance(floors, dict) and floors.get("reject_ground_floor") is not None:
        prof["reject_ground_floor"] = bool(floors.get("reject_ground_floor"))
    # the profile can also say it in plain words under `avoid:`; either shape counts
    for item in (raw.get("avoid") or []):
        if isinstance(item, str) and "ground floor" in item.lower():
            prof["reject_ground_floor"] = True
    comm = raw.get("commute") or {}
    if isinstance(comm, dict):
        prof["destination"] = comm.get("destination") or None
        prof["arrive_by"] = comm.get("arrive_by") or "09:00"
        prof["max_door_to_door_min"] = comm.get("max_door_to_door_min")
        prof["redundancy_min_grade"] = comm.get("redundancy_min_grade")
    if raw.get("language"):
        prof["language"] = raw.get("language")
    blanks = [k for k in ("min_floor_area_sqft", "max_building_age_years") if prof[k] is None]
    if blanks:
        warnings.append("profile leaves %s blank: that filter is not applied"
                        % " and ".join(blanks))
    return prof, "read from %s" % path, warnings


# ---------------------------------------------------------- address parsing --
POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?)\s*([0-9][A-Z]{2})\b", re.I)
UNIT_RE = re.compile(r"^(?:flat|apartment|apt|unit|studio|room|suite|penthouse|maisonette)\b",
                     re.I)
BARE_UNIT_RE = re.compile(r"^[0-9]{1,4}[a-z]?$", re.I)
FLOOR_UNIT_RE = re.compile(r"\bflat\b", re.I)
LEADING_NUMBER_RE = re.compile(r"^([0-9]{1,5}[a-z]?(?:\s*[-–/]\s*[0-9]{1,5}[a-z]?)?)\s+(\S.*)$",
                               re.I)
ABBREV = {"st": "street", "rd": "road", "ave": "avenue", "av": "avenue", "ln": "lane",
          "pl": "place", "sq": "square", "gdns": "gardens", "cres": "crescent",
          "ct": "court", "dr": "drive", "gr": "grove", "hse": "house", "pk": "park",
          "ter": "terrace", "wlk": "walk", "yd": "yard", "bldg": "building"}


def normalise_postcode(text):
    m = POSTCODE_RE.search(text or "")
    if not m:
        return None, None
    return ("%s %s" % (m.group(1).upper(), m.group(2).upper()), m.group(1).upper())


def norm_token(text):
    """Lower case, a number range reduced to its first number ("4-6" -> "4"), then
    punctuation out and the common street abbreviations expanded. Used only to build
    grouping keys: a letter suffix stays, because 4A and 4 are different addresses."""
    t = (text or "").lower()
    t = re.sub(r"^\s*([0-9]+)\s*[-\u2013/]\s*[0-9]+[a-z]?(?=\s|$)", r"\1", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return ""
    words = t.split(" ")
    if len(words) > 1:
        # only the LAST word is a street type: "St. Thomas Street" is Saint Thomas,
        # not Street Thomas, and every abbreviation in the table comes last in a
        # British address.
        words[-1] = ABBREV.get(words[-1], words[-1])
    return " ".join(words)


def slug(text, maxlen=40):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:maxlen].strip("-") or "x"


def parse_address(address):
    """Split an energy-register address into flat / building / street / postcode.

    The register writes 'Flat 5, 4 London Bridge Street, LONDON, SE1 9SG' and also
    'Apartment 1, The Shard, LONDON, SE1 9SG' — a building name with no street.
    """
    out = {"raw": address, "flat": None, "building_name": None, "building_number": None,
           "street": None, "town": None, "postcode": None, "outcode": None}
    if not address:
        return out
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if not parts:
        return out
    pc, outcode = normalise_postcode(parts[-1])
    if pc:
        out["postcode"], out["outcode"] = pc, outcode
        parts = parts[:-1]
    elif len(parts) > 1:
        pc, outcode = normalise_postcode(address)
        out["postcode"], out["outcode"] = pc, outcode
    while parts and parts[-1].strip().lower() in ("london", "greater london", "england", "uk"):
        out["town"] = parts[-1].strip().title()
        parts = parts[:-1]
    if not parts:
        return out
    units, rest = [], list(parts)
    while len(rest) > 1 and (UNIT_RE.match(rest[0]) or BARE_UNIT_RE.match(rest[0])
                             or (FLOOR_UNIT_RE.search(rest[0]) and len(rest[0].split()) <= 4)):
        units.append(rest.pop(0))
    if units:
        out["flat"] = ", ".join(units)
    street_line = rest[-1]
    if len(rest) >= 2:
        out["building_name"] = rest[-2]
    m = LEADING_NUMBER_RE.match(street_line)
    if m:
        out["building_number"] = m.group(1).strip()
        out["street"] = m.group(2).strip()
    elif len(rest) >= 2:
        out["street"] = street_line
    else:
        out["building_name"] = out["building_name"] or street_line
    return out


def building_key(parsed, street_searched=None):
    """The grouping key AND the candidate file name: building + street + outcode.

    Two flats in one building are one candidate, so the flat number is never in the
    key. The street on the certificate wins over the street that was searched, so a
    building found twice - once by the street census, once by a user-supplied
    postcode - lands on one key instead of two. Abbreviated spellings ("4 London
    Bridge" for "4 London Bridge Street") are reunited afterwards by
    merge_abbreviated_streets, which works for postcode-sourced certificates too.
    """
    street = norm_token(parsed.get("street") or "") or norm_token(street_searched or "")
    token = norm_token(parsed.get("building_name") or parsed.get("building_number") or street)
    outcode = (parsed.get("outcode") or "").lower()
    return "%s--%s--%s" % (slug(token), slug(street), slug(outcode, 6))


def same_building(a, b):
    """Compare two grouping keys, ignoring the outcode when one side has none - a
    user who writes "4 London Bridge Street" with no postcode still means one
    building, not every building the postcode search returned."""
    if a == b:
        return True
    pa, pb = a.rsplit("--", 1), b.rsplit("--", 1)
    if pa[1] in ("x", "") or pb[1] in ("x", ""):
        return pa[0] == pb[0]
    return False


def display_address(parsed, street_searched=None):
    head = parsed.get("building_name")
    number = parsed.get("building_number")
    street = parsed.get("street") or street_searched
    bits = []
    if head:
        bits.append(head)
    if number and street:
        bits.append("%s %s" % (number, street))
    elif street and not head:
        bits.append(street)
    elif number:
        bits.append(number)
    if not bits:
        bits.append(parsed.get("raw") or "unknown")
    if parsed.get("postcode"):
        bits.append(parsed["postcode"])
    return ", ".join(bits)


def merge_abbreviated_streets(buildings):
    """Reunite "4 London Bridge" with "4 London Bridge Street".

    The register spells the same street both ways, so one building arrives as two.
    Two buildings merge when the building token and the outcode match and one
    street name is a word-prefix of the other; the longer, more specific spelling
    wins. Returns (kept, merges) and never loses a certificate.
    """
    groups, merges, dropped = OrderedDict(), [], set()
    for b in buildings:
        parts = b["key"].split("--")
        if len(parts) != 3:
            continue
        groups.setdefault((parts[0], parts[2]), []).append((parts[1], b))
    for items in groups.values():
        if len(items) < 2:
            continue
        items.sort(key=lambda it: (-len(it[0]), it[0]))
        for i in range(len(items) - 1, 0, -1):
            short_street, short_b = items[i]
            if id(short_b) in dropped:
                continue
            for long_street, long_b in items[:i]:
                if id(long_b) in dropped or not long_street.startswith(short_street + "-"):
                    continue
                long_b["certificates"] += short_b["certificates"]
                long_b["certificate_count"] += short_b["certificate_count"]
                for pc in short_b["postcodes"]:
                    if pc not in long_b["postcodes"]:
                        long_b["postcodes"].append(pc)
                if short_b["distance_m"] is not None and (
                        long_b["distance_m"] is None
                        or short_b["distance_m"] < long_b["distance_m"]):
                    long_b["distance_m"] = short_b["distance_m"]
                    long_b["coordinates"] = short_b["coordinates"]
                long_b["user_supplied"] = long_b["user_supplied"] or short_b["user_supplied"]
                long_b.setdefault("merged_from", []).append(
                    {"key": short_b["key"], "display_address": short_b["display_address"],
                     "why": "the register spells this street both ways"})
                dropped.add(id(short_b))
                merges.append({"merged": short_b["key"], "into": long_b["key"]})
                break
    return [b for b in buildings if id(b) not in dropped], merges


def exclusion_for(*texts):
    """Stage 1b. Return (code, reason) for the first pattern that matches, else None."""
    blob = " ".join(t for t in texts if t)
    for name, rx, why in _EXCLUSION_RE:
        m = rx.search(blob)
        if m:
            return name, "%s (matched %r)" % (why, m.group(0).strip())
    return None


# ------------------------------------------------------------------ numbers --
def median(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    if n % 2:
        return vals[n // 2]
    return (vals[n // 2 - 1] + vals[n // 2]) / 2.0


def _round(x, n=1):
    return None if x is None else round(x, n)


def spread(items, k):
    """Take k items spread across the list, not the first k: a big block's first
    certificates are all one floor and one layout."""
    if k <= 0 or not items:
        return []
    if len(items) <= k:
        return list(items)
    step = len(items) / float(k)
    picked, seen = [], set()
    for i in range(k):
        idx = min(len(items) - 1, int(round(i * step)))
        while idx in seen and idx + 1 < len(items):
            idx += 1
        if idx not in seen:
            seen.add(idx)
            picked.append(items[idx])
    return picked


# ------------------------------------------------------ building profile -----
def building_profile(certs):
    """The Stage 2 profile computed from the sampled certificates only."""
    ok = [c for c in certs if c.get("ok")]
    areas = [c.get("total_floor_area_m2") for c in ok if c.get("total_floor_area_m2")]
    sqft = [c.get("total_floor_area_sqft") for c in ok if c.get("total_floor_area_sqft")]
    years = [c.get("first_assessment_year") for c in ok if c.get("first_assessment_year")]
    perms = [c.get("air_permeability") for c in ok if c.get("air_permeability") is not None]
    floors = [c.get("floor_position") for c in ok]
    ground = sum(1 for f in floors if f in ("ground", "basement"))
    return {
        "certificates_sampled": len(certs),
        "certificates_parsed": len(ok),
        "floor_area_m2_median": _round(median(areas)),
        "floor_area_sqft_median": int(round(median(sqft))) if sqft else None,
        "floor_area_sqft_max": max(sqft) if sqft else None,
        "floor_area_sqft_min": min(sqft) if sqft else None,
        "earliest_assessment_year": min(years) if years else None,
        "latest_assessment_year": max(years) if years else None,
        "heating_classes": dict(Counter(c.get("heating_class") for c in ok if c.get("heating_class"))),
        "assessment_types": dict(Counter(c.get("assessment_type") for c in ok if c.get("assessment_type"))),
        "ground_floor_count": ground,
        "ground_floor_share": round(ground / float(len(ok)), 2) if ok else None,
        "air_permeability_median": _round(median(perms), 2),
        "floor_positions": dict(Counter(f for f in floors if f)),
    }


def hard_filter(prof, bprofile, this_year):
    """Stage 2. Rows follow report-schema `hard_filter`: an unknown is never a pass,
    but only an explicit false drops the building out of the expensive stage."""
    checks = []
    parsed = bprofile.get("certificates_parsed") or 0

    max_age = prof.get("max_building_age_years")
    year = bprofile.get("earliest_assessment_year")
    if max_age:
        if year:
            age = this_year - year
            checks.append({
                "name": "Building age",
                "requirement": "No older than %d years (first energy assessment in %d or later)"
                               % (max_age, this_year - max_age),
                "observed": "earliest sampled energy assessment %d, about %d years old"
                            % (year, age),
                "pass": bool(age <= max_age), "evidence_class": "I"})
        else:
            checks.append({
                "name": "Building age",
                "requirement": "No older than %d years" % max_age,
                "observed": "no assessment year in the %d certificate(s) sampled" % parsed,
                "pass": "unknown", "evidence_class": "U"})

    min_area = prof.get("min_floor_area_sqft")
    if min_area:
        biggest = bprofile.get("floor_area_sqft_max")
        if biggest:
            checks.append({
                "name": "Indoor floor area",
                "requirement": "At least %d square feet indoors in at least one flat" % min_area,
                "observed": "largest of %d sampled flats is %d square feet (median %s)"
                            % (parsed, biggest, bprofile.get("floor_area_sqft_median")),
                "pass": bool(biggest >= min_area), "evidence_class": "G"})
        else:
            checks.append({
                "name": "Indoor floor area",
                "requirement": "At least %d square feet indoors" % min_area,
                "observed": "no floor area on the %d certificate(s) sampled" % parsed,
                "pass": "unknown", "evidence_class": "U"})

    if prof.get("reject_ground_floor"):
        share = bprofile.get("ground_floor_share")
        if share is None:
            checks.append({
                "name": "Ground floor",
                "requirement": "No ground-floor or basement flat",
                "observed": "no floor position on the %d certificate(s) sampled" % parsed,
                "pass": "unknown", "evidence_class": "U"})
        else:
            checks.append({
                "name": "Ground floor",
                "requirement": "No ground-floor or basement flat",
                "observed": "%d of %d sampled flats are ground or basement (%.0f%%); this "
                            "filter applies per flat, not per building"
                            % (bprofile.get("ground_floor_count") or 0, parsed, 100 * share),
                "pass": bool(share < 1.0), "evidence_class": "G"})

    if parsed == 0:
        checks.append({
            "name": "Residential certificates",
            "requirement": "At least one readable residential energy certificate",
            "observed": "none of the %d sampled certificates could be read"
                        % (bprofile.get("certificates_sampled") or 0),
            "pass": False, "evidence_class": "U"})

    failed = [c for c in checks if c["pass"] is False]
    unknown = [c for c in checks if c["pass"] == "unknown"]
    return {
        "checks": checks,
        "pass": not failed,
        "fail_reasons": ["%s: %s" % (c["name"], c["observed"]) for c in failed],
        "unknowns": ["%s: %s" % (c["name"], c["observed"]) for c in unknown],
    }


# ------------------------------------------------------------- size budget ---
def load_json(path):
    """Read a stage file back for --resume; a corrupt file is recomputed, not trusted."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError):
        return None


def json_bytes(obj):
    return len(json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8"))


def _dig(obj, path):
    cur = obj
    for key in path.split(".")[:-1]:
        if not isinstance(cur, dict) or key not in cur:
            return None, None
        cur = cur[key]
    last = path.split(".")[-1]
    if not isinstance(cur, dict) or last not in cur:
        return None, None
    return cur, last


# Applied in order until the record fits. Cheap metadata goes first; the three lists
# the method actually asks for - the top crime anchors, the nearest planning cases and
# the nearest of each road category - go last. `metrics` is never trimmed, and neither
# is a block's source_url, retrieved_at or evidence_class.
TRIM_STEPS = [
    # 1. metadata that is repeated in summary.json or derivable from what stays
    ("commute.legs", "drop", None),
    ("crime.months_missing", "drop", None),
    ("crime.top_anchor_share", "drop", None),
    ("crime.box", "drop", None),
    ("crime.window", "drop", None),
    ("crime.half_m", "drop", None),
    ("commute.arrive_by", "drop", None),
    ("commute.nearest_family_walk_m", "drop", None),
    ("commute.second_family_walk_m", "drop", None),
    ("commute.walking_min", "drop", None),
    ("planning.radius_m", "drop", None),
    ("roads.radius_m", "drop", None),
    ("land_registry.postcode", "drop", None),
    ("companies.postcode", "drop", None),
    ("epc.assessment_types", "drop", None),
    ("epc.air_permeability_median", "drop", None),
    ("epc.certificates_sampled", "drop", None),
    ("epc.sample_certificate_ids", "list", 3),
    ("companies.rmc_rtm_names", "list", 3),
    # 2. detail the summary table does not use
    ("roads.obstruction", "list", 2),
    ("commute.redundancy_reason", "drop", None),
    ("roads.obstruction", "drop", None),
    ("epc.sample_certificate_ids", "drop", None),
    ("companies.inference", "drop", None),
    ("coordinates.provenance", "drop", None),
    ("land_registry.transactions", "drop", None),
    ("companies.companies_at_address", "drop", None),
    ("crime.sensitivity_spread", "drop", None),
    ("crime.predatory_count", "drop", None),
    ("planning.tall_scheme_count", "drop", None),
    ("planning.count_in_radius", "drop", None),
    ("planning.total_matching", "drop", None),
    ("commute.changes", "drop", None),
    ("postcodes", "list", 3),
    ("failures", "list", 2),
    ("companies.rmc_rtm_names", "drop", None),
    ("land_registry.new_build_count", "drop", None),
    ("epc.floor_area_sqft_max", "drop", None),
    # 3. the lists the method names, largest first, cut rather than dropped
    ("crime.by_category", "dict", 5),
    ("crime.top_anchors", "list", 3),
    ("planning.nearest", "list", 2),
    ("roads.waste_or_recycling", "drop", None),
    ("roads.park_or_green", "drop", None),
    ("roads.night_economy", "drop", None),
    ("crime.by_category", "dict", 3),
    ("crime.top_anchors", "list", 1),
    ("planning.nearest", "list", 1),
    ("roads.supermarket", "drop", None),
    ("roads.tube_surface", "drop", None),
    ("roads.secondary", "drop", None),
    ("roads.not_mapped", "drop", None),
    ("crime.by_category", "drop", None),
    ("crime.top_anchors", "drop", None),
    ("planning.nearest", "drop", None),
    ("roads.railway_surface", "drop", None),
    ("metrics_not_measured", "drop", None),
]


def _trim_note(applied, still_over=False):
    """A short marker inside the record; the full list goes to summary.json, because a
    complete trim log is easily bigger than the bytes it saved."""
    head = ", ".join(a for a in applied[:4] if a != "STILL OVER BUDGET")
    if len(applied) > 4:
        head += " and %d more" % (len(applied) - 4)
    note = "%d field(s) dropped to fit the %d-byte cap: %s" % (
        len([a for a in applied if a != "STILL OVER BUDGET"]), CANDIDATE_BUDGET_BYTES, head)
    return ("STILL OVER BUDGET after " + note) if still_over else note


def fit_to_budget(record, budget=CANDIDATE_BUDGET_BYTES, steps=None, log=None):
    """Shrink a candidate record until it fits, recording what was dropped.

    The cap is the point of the sweep: the model reads many of these, so any one of
    them staying small matters more than any one of them staying complete. Nothing in
    `metrics` is ever trimmed, and neither is a block's source_url, retrieved_at or
    evidence_class - a number with no provenance is worse than no number.
    """
    rec = copy.deepcopy(record)
    rec.pop("trimmed", None)
    if json_bytes(rec) <= budget:
        return rec
    applied = []
    for path, action, n in (TRIM_STEPS if steps is None else steps):
        parent, key = _dig(rec, path)
        if parent is None:
            continue
        value = parent[key]
        if action == "drop":
            del parent[key]
            applied.append(path)
        elif action == "list" and isinstance(value, list) and len(value) > n:
            parent[key] = value[:n]
            applied.append("%s->%d" % (path, n))
        elif action == "dict" and isinstance(value, dict) and len(value) > n:
            items = sorted(value.items(), key=lambda kv: (-kv[1] if isinstance(kv[1], (int, float))
                                                          else 0, kv[0]))
            parent[key] = dict(items[:n])
            applied.append("%s->%d" % (path, n))
        else:
            continue
        rec["trimmed"] = _trim_note(applied)
        if json_bytes(rec) <= budget:
            if log is not None:
                log.extend(applied)
            return rec
    # last resort: shorten the long free-text fields rather than lose a number
    for path in ("roads.facade_note", "companies.inference", "commute.redundancy_reason",
                 "coordinates.provenance"):
        parent, key = _dig(rec, path)
        if parent is not None and isinstance(parent[key], str) and len(parent[key]) > 40:
            parent[key] = parent[key][:40] + "..."
            applied.append(path + "(cut)")
            rec["trimmed"] = _trim_note(applied)
            if json_bytes(rec) <= budget:
                if log is not None:
                    log.extend(applied)
                return rec
    applied.append("STILL OVER BUDGET")
    rec["trimmed"] = _trim_note(applied, still_over=True)
    if log is not None:
        log.extend(applied)
    return rec


# ------------------------------------------------------------------- S0 ------
def stage0_anchor(args, prof, prof_source, prof_warnings):
    global CURRENT_STAGE
    CURRENT_STAGE = "s0"
    text = args.anchor.strip()
    m = re.match(r"^\s*(-?[0-9]+(?:\.[0-9]+)?)\s*,\s*(-?[0-9]+(?:\.[0-9]+)?)\s*$", text)
    anchor = {"query": text, "retrieved_at": now_iso(), "radius_m": args.radius,
              "generated_by": "sweep.py %s" % VERSION}
    if m:
        lat, lng = float(m.group(1)), float(m.group(2))
        back = geo.reverse(lat, lng, radius=200, limit=5)
        nearest = (back.get("results") or [None])[0] if back.get("ok") else None
        anchor.update({
            "kind": "coordinates", "lat": lat, "lng": lng,
            "postcode": (nearest or {}).get("postcode"),
            "admin_district": (nearest or {}).get("admin_district"),
            "admin_ward": (nearest or {}).get("admin_ward"),
            "region": (nearest or {}).get("region"),
            "source_url": back.get("source_url"), "ok": bool(back.get("ok")),
            "http_status": back.get("http_status"), "evidence_class": "G",
            "note": "coordinates given directly; postcode and borough are the nearest "
                    "postcode centroid, not the anchor itself"})
    else:
        up = geo.lookup(text)
        if not up.get("ok") or up.get("lat") is None:
            anchor.update({"kind": "postcode", "ok": False, "lat": None, "lng": None,
                           "source_url": up.get("source_url"),
                           "http_status": up.get("http_status"),
                           "note": "could not locate the anchor: %s" % (up.get("note") or "")})
            return anchor
        anchor.update({
            "kind": "postcode", "lat": up["lat"], "lng": up["lng"],
            "postcode": up.get("postcode"), "admin_district": up.get("admin_district"),
            "admin_ward": up.get("admin_ward"), "region": up.get("region"),
            "source_url": up.get("source_url"), "ok": True,
            "http_status": up.get("http_status"), "evidence_class": "G",
            "note": "postcode centroid, not a door: expect tens of metres of error"})
    anchor["town_searched"] = args.town or (
        DEFAULT_TOWN if (anchor.get("region") or "").lower() == "london"
        else (anchor.get("admin_district") or DEFAULT_TOWN))
    anchor["destination"] = args.dest or prof.get("destination")
    anchor["arrive_by"] = args.arrive or prof.get("arrive_by") or "09:00"
    anchor["profile_source"] = prof_source
    anchor["profile_snapshot"] = dict(prof)
    anchor["profile_warnings"] = prof_warnings
    anchor["radius_warning"] = (
        "%d m is a wide sweep: the street census and the certificate sample grow with the "
        "area, so expect several hundred fetches and check --dry-run first." % args.radius
        if args.radius > 1200 else None)
    return anchor


# ------------------------------------------------------------------- S1 ------
def overpass_street_query(lat, lng, radius, timeout=90):
    """Named ways that carry homes, inside the circle. One request."""
    return ("[out:json][timeout:%d];\n"
            "way(around:%d,%s,%s)[\"highway\"~\"^(%s)$\"][\"name\"];\n"
            "out geom;" % (timeout, int(radius), lat, lng, "|".join(STREET_HIGHWAYS)))


def streets_in_circle(lat, lng, radius, verbose=False):
    """Unique street names in the circle, nearest first, from OpenStreetMap."""
    query = overpass_street_query(lat, lng, radius)
    data, meta = roads.run_overpass(query, verbose=verbose)
    out = {"source_url": meta.get("source_url"), "http_status": meta.get("http_status"),
           "ok": bool(meta.get("ok")), "note": meta.get("note"),
           "retrieved_at": meta.get("retrieved_at"), "evidence_class": "C",
           "attribution": roads.ATTRIBUTION, "query_used": query,
           "overpass_instance": meta.get("overpass_instance"), "streets": []}
    if not meta.get("ok"):
        out["not_found"] = {"what": "named residential streets around %s,%s" % (lat, lng),
                            "query": query,
                            "meaning": "Overpass did not answer; this is a fetch failure, "
                                       "not an absence of streets"}
        return out
    best = {}
    for el in (data or {}).get("elements") or []:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        dist = roads.nearest_on_element(lat, lng, el)[0]
        if dist is None:
            continue
        prev = best.get(name)
        if prev is None or dist < prev["nearest_m"]:
            best[name] = {"name": name, "nearest_m": int(round(dist)),
                          "highway": tags.get("highway")}
    out["streets"] = sorted(best.values(), key=lambda s: (s["nearest_m"], s["name"]))
    out["count"] = len(out["streets"])
    return out


def overpass_area_query(lat, lng, sweep_radius, roads_radius=300, timeout=80):
    """roads.py's own query with every radius widened by the sweep radius, so ONE
    answer serves every building in the circle. roads.near() re-filters it per
    building at each category's proper distance, so nothing is over-counted. The
    query is taken from roads.build_query rather than copied, so the tag list cannot
    drift; the timeout stays under run_overpass's 90 s curl timeout, so a slow query
    comes back as an Overpass error rather than a dropped connection."""
    q = roads.build_query(lat, lng, radius=roads_radius, timeout=timeout)
    r = int(sweep_radius)
    return re.sub(r"around:(\d+),", lambda m: "around:%d," % (int(m.group(1)) + r), q)


def shared_osm(anchor, args):
    """Fetch the widened Overpass answer once, or say why it was not worth it."""
    if args.radius > SHARED_OVERPASS_MAX_M:
        return None, ("radius %d m is over the %d m ceiling for one shared OpenStreetMap "
                      "query; each building gets its own"
                      % (args.radius, SHARED_OVERPASS_MAX_M))
    query = overpass_area_query(anchor["lat"], anchor["lng"], args.radius,
                                roads_radius=args.roads_radius)
    data, meta = roads.run_overpass(query, verbose=args.verbose)
    if not meta.get("ok"):
        return None, "the shared OpenStreetMap query failed (%s); each building gets its own" \
                     % (meta.get("note") or meta.get("http_status"))
    meta = dict(meta)
    meta["note"] = ("one Overpass answer for the whole %d m circle, re-filtered per building "
                    "at each category's own distance" % args.radius)
    return {"elements": (data or {}).get("elements") or [], "meta": meta}, None


class PostcodeBook(object):
    """Postcode -> coordinates, primed with one cheap call and topped up one at a time.

    postcodes.io returns at most 100 rows per call, so it can locate but never
    enumerate. This class exists so a street census does not turn into one HTTP
    request per certificate.
    """

    def __init__(self, lat, lng, radius, max_lookups=120):
        self.lat, self.lng, self.radius = lat, lng, radius
        self.max_lookups = max_lookups
        self.cache = {}
        self.lookups = 0
        self.skipped = []
        self.primed = None
        self.nearest_first = []      # primed postcodes, nearest first, all inside the circle

    def prime(self):
        """One reverse-geocode call. It returns at most 100 rows, so in central London
        it reaches only a few hundred metres; everything past that falls through to
        one lookup per postcode, which is why `--max-postcode-lookups` exists."""
        capped = min(self.radius, geo.MAX_RADIUS_M)
        res = geo.nearby(self.lat, self.lng, radius=capped)
        rows = res.get("results") or []
        self.primed = {"call": "geo.nearby", "radius_m": capped, "count": len(rows),
                       "saturated": bool(res.get("saturated")),
                       "reach_m": res.get("furthest_m"),
                       "source_url": res.get("source_url"), "ok": bool(res.get("ok")),
                       "note": ("the 100-row cap was hit at about %s m, so this primer is a "
                                "floor, not a census" % res.get("furthest_m"))
                               if res.get("saturated") else ""}
        for row in rows:
            pc = row.get("postcode")
            if pc and row.get("lat") is not None:
                self.cache[pc] = {"lat": row["lat"], "lng": row["lng"],
                                  "distance_m": row.get("distance_m"),
                                  "source": "geo.nearby"}
                if (row.get("distance_m") or 0) <= self.radius:
                    self.nearest_first.append(pc)
        return self.primed

    def get(self, postcode):
        if not postcode:
            return None
        if postcode in self.cache:
            return self.cache[postcode]
        if self.lookups >= self.max_lookups:
            if postcode not in self.skipped:
                self.skipped.append(postcode)
            return None
        self.lookups += 1
        up = geo.lookup(postcode)
        if not up.get("ok") or up.get("lat") is None:
            self.cache[postcode] = None
            return None
        dist = geo.haversine_m(self.lat, self.lng, up["lat"], up["lng"])
        self.cache[postcode] = {"lat": up["lat"], "lng": up["lng"],
                                "distance_m": round(dist, 1), "source": "geo.lookup"}
        return self.cache[postcode]


def stage1_enumerate(anchor, args, book, extra_candidates):
    global CURRENT_STAGE
    CURRENT_STAGE = "s1"
    lat, lng, radius = anchor["lat"], anchor["lng"], args.radius
    town = anchor["town_searched"]

    st = streets_in_circle(lat, lng, radius, verbose=args.verbose)
    streets = st["streets"]
    searched = streets if not args.max_streets else streets[:args.max_streets]
    skipped_streets = [s["name"] for s in streets[len(searched):]]

    book.prime()
    certs, not_found, searches, too_many = {}, [], [], []
    for s in searched:
        res = epc.search(street=s["name"], town=town)
        searches.append({"street": s["name"], "url": res.get("source_url"),
                         "ok": bool(res.get("ok")), "count": res.get("count") or 0})
        if not res.get("ok"):
            not_found.append({"what": "energy certificates on %s" % s["name"],
                              "queries_used": [res.get("source_url") or
                                               "epc.search(street=%r, town=%r)" % (s["name"], town)],
                              "where_looked": "GOV.UK energy certificate register",
                              "next_step": "open the street search page and paste the results"})
            continue
        if res.get("too_many_results"):
            too_many.append(s["name"])
            not_found.append({
                "what": "the full certificate list for %s" % s["name"],
                "queries_used": [res.get("source_url")],
                "where_looked": "GOV.UK energy certificate register",
                "next_step": "the register served its 'Too many results for this address' "
                             "page and told us to search by postcode instead; the sweep "
                             "does that below"})
            continue
        if not res.get("count"):
            not_found.append({"what": "energy certificates on %s" % s["name"],
                              "queries_used": [res.get("source_url")],
                              "where_looked": "GOV.UK energy certificate register",
                              "next_step": "the street may have no certificates, or the "
                                           "register spells it differently"})
            continue
        for row in res["results"]:
            cid = row.get("certificate_id")
            if cid and cid not in certs:
                row = dict(row)
                row["street_searched"] = s["name"]
                certs[cid] = row

    # The register refuses to list a street with too many certificates, and those are
    # exactly the busiest streets. Its own advice is to search by postcode, so that is
    # what happens next: the postcodes already primed from one geo.nearby call, nearest
    # first, capped so the fallback cannot run away with the budget.
    pc_searches, pc_skipped = [], []
    if too_many and args.postcode_fallback:
        wanted = book.nearest_first[:args.postcode_fallback]
        pc_skipped = book.nearest_first[args.postcode_fallback:]
        for pc in wanted:
            res = epc.search(postcode=pc)
            pc_searches.append({"postcode": pc, "url": res.get("source_url"),
                                "ok": bool(res.get("ok")), "count": res.get("count") or 0})
            if not res.get("ok"):
                not_found.append({"what": "energy certificates in %s" % pc,
                                  "queries_used": [res.get("source_url") or pc],
                                  "where_looked": "GOV.UK energy certificate register",
                                  "next_step": "open the postcode search page and paste it"})
                continue
            for row in res["results"]:
                cid = row.get("certificate_id")
                if cid and cid not in certs:
                    row = dict(row)
                    row["street_searched"] = None      # the address carries the street
                    row["found_by"] = "postcode fallback"
                    certs[cid] = row
        if pc_skipped:
            not_found.append({
                "what": "certificates in %d further postcode(s) inside the circle"
                        % len(pc_skipped),
                "queries_used": ["epc.py search --postcode %r" % p for p in pc_skipped[:5]],
                "where_looked": "GOV.UK energy certificate register",
                "next_step": "raise --postcode-fallback above %d" % args.postcode_fallback})
    elif too_many:
        not_found.append({
            "what": "the streets the register would not list (%d of them)" % len(too_many),
            "queries_used": too_many[:5],
            "where_looked": "GOV.UK energy certificate register",
            "next_step": "run again with --postcode-fallback above 0"})

    for extra in extra_candidates:
        for row in extra.get("rows", []):
            cid = row.get("certificate_id")
            if cid and cid not in certs:
                certs[cid] = row
        if extra.get("not_found"):
            not_found.append(extra["not_found"])

    # certificate -> coordinates -> inside or outside the circle
    buildings, outside, ungeocoded = OrderedDict(), 0, []
    for cid, row in certs.items():
        parsed = parse_address(row.get("address") or "")
        pc = parsed.get("postcode")
        loc = book.get(pc)
        forced = bool(row.get("user_supplied"))
        if loc is None:
            if not forced:
                if pc and pc not in ungeocoded:
                    ungeocoded.append(pc)
                continue
            dist = None
        else:
            dist = loc.get("distance_m")
            if dist is None:
                dist = round(geo.haversine_m(anchor["lat"], anchor["lng"],
                                             loc["lat"], loc["lng"]), 1)
            if dist > radius and not forced:
                outside += 1
                continue
        key = building_key(parsed, row.get("street_searched"))
        b = buildings.get(key)
        if b is None:
            b = buildings[key] = {
                "key": key,
                "display_address": display_address(parsed, row.get("street_searched")),
                "building_name": parsed.get("building_name"),
                "building_number": parsed.get("building_number"),
                "street": parsed.get("street") or row.get("street_searched"),
                "outcode": parsed.get("outcode"),
                "postcodes": [], "certificate_count": 0, "sample_certificate_ids": [],
                "certificates": [], "distance_m": dist,
                "coordinates": ({"lat": loc["lat"], "lng": loc["lng"],
                                 "provenance": "postcode centroid (%s) via postcodes.io; "
                                               "not the door" % pc} if loc else None),
                "user_supplied": forced, "excluded_reason": None, "excluded_code": None,
            }
        b["certificate_count"] += 1
        if pc and pc not in b["postcodes"]:
            b["postcodes"].append(pc)
        b["certificates"].append({"certificate_id": cid, "address": row.get("address"),
                                  "rating": row.get("rating")})
        if dist is not None and (b["distance_m"] is None or dist < b["distance_m"]):
            b["distance_m"] = dist
            if loc:
                b["coordinates"] = {"lat": loc["lat"], "lng": loc["lng"],
                                    "provenance": "postcode centroid (%s) via postcodes.io; "
                                                  "not the door" % pc}
        b["user_supplied"] = b["user_supplied"] or forced

    kept, merges = merge_abbreviated_streets(list(buildings.values()))

    # Stage 1b — exclude by name, never silently
    for b in kept:
        b["sample_certificate_ids"] = [c["certificate_id"]
                                       for c in spread(b["certificates"], 5)]
        hit = exclusion_for(b["display_address"], b.get("building_name"))
        if hit and not b["user_supplied"]:
            b["excluded_code"], b["excluded_reason"] = hit
        elif hit:
            b["excluded_reason"] = None
            b["excluded_code"] = None
            b["note"] = "matched exclusion %s but was supplied by the user, so it stays" % hit[0]

    ordered = sorted(kept,
                     key=lambda x: (not x["user_supplied"],
                                    x["distance_m"] if x["distance_m"] is not None else 9e9,
                                    x["key"]))
    if ungeocoded:
        not_found.append({
            "what": "coordinates for %d postcode(s) seen on certificates" % len(ungeocoded),
            "queries_used": ["geo.lookup(%r)" % p for p in ungeocoded[:5]],
            "where_looked": "postcodes.io",
            "next_step": "raise --max-postcode-lookups, or accept that those certificates "
                         "were not placed in or out of the circle"})
    return {
        "generated_at": now_iso(),
        "anchor": {"lat": lat, "lng": lng, "radius_m": radius, "town_searched": town},
        "streets": {"source_url": st.get("source_url"), "ok": st.get("ok"),
                    "note": st.get("note"), "retrieved_at": st.get("retrieved_at"),
                    "evidence_class": st.get("evidence_class"),
                    "attribution": st.get("attribution"),
                    "overpass_instance": st.get("overpass_instance"),
                    "found": len(streets), "searched": len(searched),
                    "skipped_over_max": skipped_streets,
                    "too_many_results": too_many,
                    "names": [s["name"] for s in searched]},
        "epc_searches": searches,
        "postcode_fallback": {"triggered_by_streets": len(too_many),
                              "postcodes_searched": len(pc_searches),
                              "postcodes_not_searched": len(pc_skipped),
                              "cap": args.postcode_fallback,
                              "searches": pc_searches},
        "postcode_book": {"primed": book.primed, "individual_lookups": book.lookups,
                          "not_geocoded": ungeocoded,
                          "skipped_over_cap": book.skipped},
        "certificates_seen": len(certs),
        "certificates_outside_radius": outside,
        "buildings": ordered,
        "merged_abbreviated_streets": merges,
        "counts": {"buildings": len(ordered),
                   "merged_abbreviated_streets": len(merges),
                   "excluded": sum(1 for b in ordered if b["excluded_code"]),
                   "user_supplied": sum(1 for b in ordered if b["user_supplied"])},
        "not_found": not_found,
    }


def read_candidates_file(path, town):
    """User-supplied addresses or postcodes, one per line. Always included."""
    out = []
    if not path:
        return out
    if not os.path.exists(path):
        return [{"rows": [], "not_found": {"what": "the --candidates file",
                                           "queries_used": [path],
                                           "where_looked": "local disk",
                                           "next_step": "check the path"}}]
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pc, _ = normalise_postcode(line)
        looks_like_postcode = bool(pc) and len(line.replace(" ", "")) <= 8
        want_key = None
        if looks_like_postcode:
            res = epc.search(postcode=pc)
        else:
            parsed = parse_address(line)
            if parsed.get("building_name") or parsed.get("building_number"):
                want_key = building_key(parsed)
            if parsed.get("postcode"):
                res = epc.search(postcode=parsed["postcode"])
            elif parsed.get("street"):
                res = epc.search(street=parsed["street"], town=town)
            else:
                out.append({"rows": [], "not_found": {
                    "what": "user-supplied candidate %r" % line,
                    "queries_used": [line], "where_looked": "GOV.UK energy certificate register",
                    "next_step": "give a postcode or a street name so it can be searched"}})
                continue
        rows = []
        for row in res.get("results") or []:
            if want_key and not same_building(want_key,
                                              building_key(parse_address(row.get("address")))):
                continue          # the search was by postcode; the user named one building
            row = dict(row)
            row["user_supplied"] = True
            row["user_supplied_line"] = line
            rows.append(row)
        entry = {"rows": rows, "line": line, "source_url": res.get("source_url")}
        if not rows:
            entry["not_found"] = {"what": "energy certificates for %r" % line,
                                  "queries_used": [res.get("source_url") or line],
                                  "where_looked": "GOV.UK energy certificate register",
                                  "next_step": "open the register and paste the search page"}
        out.append(entry)
    return out


# ------------------------------------------------------------------- S2 ------
def stage2_filter(buildings_doc, prof, args):
    global CURRENT_STAGE
    CURRENT_STAGE = "s2"
    this_year = int(now_iso()[:4])
    rows, assessed = [], 0
    candidates = [b for b in buildings_doc["buildings"] if not b["excluded_code"]]
    limit = args.max_filter_buildings or len(candidates)
    for b in candidates:
        if assessed >= limit and not b["user_supplied"]:
            rows.append({"key": b["key"], "display_address": b["display_address"],
                         "distance_m": b["distance_m"], "assessed": False, "pass": False,
                         "fail_reasons": ["not assessed: past the --max-filter-buildings "
                                          "cap of %d, ordered by distance" % limit],
                         "profile": None, "checks": []})
            continue
        assessed += 1
        picked = spread(b["certificates"], args.certs_per_building)
        certs = []
        for row in picked:
            try:
                certs.append(epc.cert(row["certificate_id"]))
            except SystemExit as exc:                            # bad id from the page
                certs.append({"certificate_id": row.get("certificate_id"), "ok": False,
                              "note": str(exc)})
        bp = building_profile(certs)
        verdict = hard_filter(prof, bp, this_year)
        rows.append({
            "key": b["key"], "display_address": b["display_address"],
            "distance_m": b["distance_m"], "assessed": True,
            "certificates_in_building": b["certificate_count"],
            "certificate_ids_sampled": [c.get("certificate_id") for c in certs],
            "profile": bp, "checks": verdict["checks"],
            "pass": verdict["pass"] or bool(b["user_supplied"]),
            "fail_reasons": verdict["fail_reasons"], "unknowns": verdict["unknowns"],
            "user_supplied": b["user_supplied"],
        })
        if b["user_supplied"] and verdict["fail_reasons"]:
            rows[-1]["note"] = ("kept because the user asked for it, although %d hard filter(s) "
                                "failed" % len(verdict["fail_reasons"]))
    survivors = [r for r in rows if r["pass"]]
    failed = [r for r in rows if r.get("assessed") and not r["pass"]]
    not_assessed = [r for r in rows if not r.get("assessed")]
    return {"generated_at": now_iso(), "this_year": this_year,
            "profile_snapshot": dict(prof),
            "certs_per_building": args.certs_per_building,
            "max_filter_buildings": args.max_filter_buildings,
            "counts": {"in": len(buildings_doc["buildings"]),
                       "excluded_before_filter":
                           len(buildings_doc["buildings"]) - len(candidates),
                       "assessed": assessed, "passed": len(survivors),
                       "failed": len(failed),
                       "not_assessed_over_cap": len(not_assessed)},
            "buildings": rows}


# ------------------------------------------------------------------- S3 ------
def _envelope(res):
    """Block-level provenance, kept short. Every number in the block is covered by the
    source_url, retrieved_at and evidence_class of the block it sits in. A plain 200,
    an empty note and `ok: true` are dropped: they cost bytes and say nothing. A block
    that failed keeps `ok: false`, the status and the note, so a failure is never
    mistaken for an absence."""
    if not res:
        return {"ok": False, "note": "no result"}
    out = {}
    for k in ("source_url", "http_status", "ok", "note", "retrieved_at", "evidence_class"):
        if k in res:
            out[k] = res[k]
    if isinstance(out.get("source_url"), str):
        out["source_url"] = out["source_url"][:150]
    ts = out.get("retrieved_at")
    if isinstance(ts, str) and len(ts) >= 16:
        out["retrieved_at"] = ts[:16] + "Z"      # minute precision; the schema allows it
    if out.get("ok"):
        out.pop("ok", None)
        if out.get("http_status") == 200:
            out.pop("http_status", None)
    if not out.get("note"):
        out.pop("note", None)
    elif isinstance(out["note"], str):
        out["note"] = out["note"][:120]
    return out


def _safe(label, failures, fn, *a, **kw):
    try:
        res = fn(*a, **kw)
    except Exception as exc:                                     # noqa: BLE001
        failures.append({"step": label, "error": "%s: %s" % (type(exc).__name__, exc)[:200]})
        return None
    if isinstance(res, dict) and res.get("ok") is False:
        failures.append({"step": label, "error": (res.get("note") or "not ok")[:200],
                         "http_status": res.get("http_status")})
    return res


def facts_for_building(building, filt, anchor, args, failures, osm=None,
                       crime_end=None):
    lat = (building.get("coordinates") or {}).get("lat")
    lng = (building.get("coordinates") or {}).get("lng")
    bp = (filt or {}).get("profile") or {}
    rec = OrderedDict()
    rec["key"] = building["key"]
    rec["display_address"] = building["display_address"]
    rec["postcodes"] = building["postcodes"][:4]
    rec["distance_m"] = building["distance_m"]
    rec["coordinates"] = building.get("coordinates")
    rec["generated_at"] = now_iso()

    heating = bp.get("heating_classes") or {}
    rec["epc"] = {
        "certificates_in_building": building["certificate_count"],
        "certificates_sampled": bp.get("certificates_parsed"),
        "sample_certificate_ids": building["sample_certificate_ids"][:4],
        "floor_area_sqft_median": bp.get("floor_area_sqft_median"),
        "floor_area_sqft_max": bp.get("floor_area_sqft_max"),
        "earliest_assessment_year": bp.get("earliest_assessment_year"),
        "heating_classes": heating,
        "ground_floor_share": bp.get("ground_floor_share"),
        "assessment_types": bp.get("assessment_types"),
        "air_permeability_median": bp.get("air_permeability_median"),
        "source_url": "https://find-energy-certificate.service.gov.uk/",
        "retrieved_at": rec["generated_at"], "evidence_class": "G",
    }

    if lat is None:
        failures.append({"step": "coordinates", "error": "no coordinates for this building"})
        rec["metrics"] = build_metrics(rec, None)
        rec["metrics_not_measured"] = METRICS_NOT_MEASURED
        return rec

    # `end` is fixed once for the whole sweep: the method insists on one window for
    # every candidate, and crime.box would otherwise re-read the latest published
    # month per building and could straddle a publication.
    cr = _safe("crime.box", failures, crime.box, lat, lng, half_m=args.crime_half_m,
               months=args.crime_months, end=crime_end, verbose=args.verbose)
    if cr and cr.get("ok"):
        cr = dict(cr, source_url="https://data.police.uk/api/crimes-street/all-crime")
        pred = cr.get("predatory_subset") or {}
        cats = cr.get("by_category") or {}
        rec["crime"] = dict(_envelope(cr), **{
            "months": len(cr.get("months_fetched") or []),
            "window": "%s..%s" % ((cr.get("months_fetched") or ["?"])[0],
                                  (cr.get("months_fetched") or ["?"])[-1]),
            "half_m": int(args.crime_half_m),
            "box": "square of side %d m centred on the coordinates above"
                   % int(2 * args.crime_half_m),
            "total": cr.get("total"),
            "predatory_count": pred.get("count"),
            "predatory_share": pred.get("share_of_total"),
            "top_anchors": [{"anchor": a["anchor"][:40], "count": a["count"]}
                            for a in (cr.get("top_anchors") or [])[:5]],
            "top_anchor_share": cr.get("top_anchor_share"),
            "by_category": dict(list(sorted(cats.items(), key=lambda kv: -kv[1]))[:5]),
            "sensitivity_spread": (cr.get("sensitivity") or {}).get("spread"),
            "months_missing": cr.get("months_missing") or [],
        })
    elif cr:
        rec["crime"] = _envelope(cr)

    dest = anchor.get("destination")
    jr = _safe("commute.journey", failures, commute.journey, "%s,%s" % (lat, lng), dest,
               arrive=anchor.get("arrive_by") or "09:00", date="next-weekday",
               plans=["all", "rail"], verbose=args.verbose)
    rd = _safe("commute.redundancy", failures, commute.redundancy, lat, lng, radius=2000,
               verbose=args.verbose)
    if jr:
        plans = jr.get("plans") or {}
        rec["commute"] = dict(_envelope(jr), **{
            "to": dest, "arrive_by": anchor.get("arrive_by"),
            "all_min": jr.get("fastest_min"), "rail_min": jr.get("rail_only_min"),
            "changes": (plans.get("rail") or {}).get("changes"),
            "walking_min": (plans.get("rail") or {}).get("walking_min"),
            "legs": [("%s %s" % (lg.get("mode"), lg.get("line") or "")).strip()
                     for lg in ((plans.get("rail") or {}).get("legs") or [])][:5],
        })
        if rd and rd.get("ok"):
            rec["commute"]["redundancy_grade"] = rd.get("grade")
            rec["commute"]["redundancy_reason"] = (rd.get("reason") or "")[:120]
            rec["commute"]["nearest_family_walk_m"] = rd.get("nearest_family_walk_m")
            rec["commute"]["second_family_walk_m"] = rd.get("second_family_walk_m")

    pl = _safe("planning.near", failures, planning.near, lat, lng, radius=args.planning_radius,
               since=2018, limit=200, verbose=args.verbose)
    if pl:
        results = pl.get("results") or []
        tall = [r for r in results if r.get("tall_building_hint")]
        rec["planning"] = dict(_envelope(pl), **{
            "radius_m": args.planning_radius,
            "total_matching": pl.get("total_matching"),
            "count_in_radius": len(results),
            "tall_scheme_count": len(tall),
            "nearest_tall": ({"reference": tall[0]["reference"],
                              "distance_m": tall[0]["distance_m"],
                              "storeys": tall[0].get("storeys"),
                              "status": tall[0].get("status")} if tall else None),
            "nearest": [{"reference": r["reference"], "distance_m": r["distance_m"],
                         "status": (r.get("status") or "")[:24],
                         "tall": bool(r.get("tall_building_hint")),
                         "what": (r.get("description") or "")[:50]}
                        for r in results[:3]],
        })

    if osm:
        rl = _safe("roads.near (shared query)", failures, roads.near, lat, lng,
                   radius=args.roads_radius, elements=osm["elements"], meta=osm["meta"])
    else:
        rl = _safe("roads.near", failures, roads.near, lat, lng, radius=args.roads_radius,
                   verbose=args.verbose)
    if rl and rl.get("ok"):
        def _near(key):
            n = (rl.get(key) or {}).get("nearest")
            if not n:
                return None
            out = {"distance_m": n.get("distance_m")}
            if n.get("name"):
                out["name"] = n["name"][:36]
            return out
        obs = (rl.get("obstruction_candidates") or {}).get("worst_first") or []
        block = dict(_envelope(rl), **{"radius_m": args.roads_radius})
        absent = []
        for short, key in (("trunk_or_primary", "trunk_or_primary_road"),
                           ("secondary", "secondary_road"),
                           ("railway_surface", "railway_surface"),
                           ("tube_surface", "tube_surface"),
                           ("night_economy", "night_economy"),
                           ("supermarket", "supermarket"),
                           ("park_or_green", "park_or_green"),
                           ("waste_or_recycling", "waste_or_recycling")):
            val = _near(key)
            if val:
                block[short] = val
            else:
                absent.append(short)
        if absent:
            block["not_mapped"] = absent
        if rl.get("facade_note"):
            block["facade_note"] = rl["facade_note"]
        if obs:
            block["obstruction"] = [{"name": (o.get("name") or "?")[:24],
                                     "distance_m": o.get("distance_m"),
                                     "angle_deg": o.get("obstruction_angle_deg")}
                                    for o in obs[:3]]
        rec["roads"] = block
    elif rl:
        rec["roads"] = _envelope(rl)

    if "community_heat_network" in heating:
        ht = _safe("redress.heat_trust", failures, redress.heat_trust,
                   site=building.get("building_name") or building["display_address"].split(",")[0],
                   verbose=args.verbose)
        if ht:
            rec["heat_network"] = dict(_envelope(ht), **{
                "why_checked": "at least one sampled certificate is on a community heat network",
                "match_count": ht.get("match_count"),
                "as_at": ht.get("as_at"),
            })

    pc = (building["postcodes"] or [None])[0]
    if pc:
        lr = _safe("landregistry.price_paid", failures, landregistry.price_paid, pc,
                   paon=building.get("building_name") or building.get("building_number"),
                   verbose=args.verbose)
        if lr:
            rec["land_registry"] = dict(_envelope(lr), **{
                "postcode": pc,
                "transactions": lr.get("count"),
                "new_build_count": lr.get("new_build_count"),
                "earliest_new_build_year": lr.get("earliest_new_build_year"),
                "earliest_transaction_date": (lr.get("earliest_transaction") or {}).get("date"),
            })
        co = _safe("company.address_search", failures, company.address_search, pc,
                   limit=60, verbose=args.verbose)
        if co:
            rec["companies"] = dict(_envelope(co), **{
                "postcode": pc,
                "companies_at_address": co.get("count"),
                "rmc_rtm_count": co.get("rmc_rtm_count"),
                "rmc_rtm_names": [r.get("name", "")[:40]
                                  for r in (co.get("rmc_rtm_candidates") or [])[:5]],
                "inference": ("zero resident management or right-to-manage company at this "
                              "postcode; residents may have no route to replace the managing "
                              "agent (inference, confirm from the lease)")
                             if not co.get("rmc_rtm_count") else None,
            })
    if failures:
        rec["failures"] = failures[-6:]
    rec["metrics"] = build_metrics(rec, None)
    rec["metrics_not_measured"] = METRICS_NOT_MEASURED
    return rec


TODO_MEANING = "TO BE WRITTEN BY THE MODEL"

# The four report-schema metrics a sweep cannot reach on its own, and why. They are
# named rather than emitted, because a `measure` costs about 180 bytes of the 4 KB
# budget and an empty one teaches the model nothing it cannot read here.
METRICS_NOT_MEASURED = (
    "price_per_sqft_epc needs the asking rent; management_organic_score and "
    "management_incentivised_share need the review pages in ask-the-user.md; "
    "landlord_type needs the entity on the tenancy agreement")


def _fmt_num(x):
    if isinstance(x, float) and x == int(x):
        return str(int(x))
    return str(x)


def build_metrics(rec, medians):
    """The report-schema metric keys the sweep can fill. `compared_to` is mechanical
    (the sweep median); `meaning` is the model's job and says so."""
    med = medians or {}
    n = med.get("_n", 0)

    def cmp_text(key, unit):
        val = med.get(key)
        if val is None:
            return "No sweep benchmark yet: stage 5 fills this in."
        return ("Sweep median %s %s across %d building%s."
                % (_fmt_num(val), unit, n, "" if n == 1 else "s"))

    crime_block = rec.get("crime") or {}
    commute_block = rec.get("commute") or {}
    planning_block = rec.get("planning") or {}
    nearest_tall = planning_block.get("nearest_tall") or {}
    nearest_any = (planning_block.get("nearest") or [{}])[0]
    works_m = nearest_tall.get("distance_m")
    if works_m is None:
        works_m = nearest_any.get("distance_m")
    months = crime_block.get("months") or 6
    return OrderedDict([
        ("crime_6mo_count", {
            "value": crime_block.get("total"),
            "unit": "crimes in %d month%s" % (months, "" if months == 1 else "s"),
            "meaning": TODO_MEANING if crime_block.get("total") is not None
                       else "Not measured: police open data did not answer.",
            "compared_to": cmp_text("crime_total", "crimes"),
            "evidence_class": "G" if crime_block.get("total") is not None else "U"}),
        ("commute_min", {
            "value": commute_block.get("all_min"), "unit": "minutes",
            "meaning": TODO_MEANING if commute_block.get("all_min") is not None
                       else "Not measured: the journey planner did not answer.",
            "compared_to": cmp_text("commute_min", "minutes"),
            "evidence_class": "G" if commute_block.get("all_min") is not None else "U"}),
        ("commute_redundancy_grade", {
            "value": commute_block.get("redundancy_grade"), "unit": None,
            "meaning": TODO_MEANING if commute_block.get("redundancy_grade")
                       else "Not measured: the station list did not answer.",
            "compared_to": "Grades in this sweep: %s." % (med.get("grades") or "none yet"),
            "evidence_class": "G" if commute_block.get("redundancy_grade") else "U"}),
        ("nearest_works_m", {
            "value": works_m, "unit": "metres",
            "meaning": TODO_MEANING if works_m is not None
                       else "Not measured: no planning case inside the radius.",
            "compared_to": cmp_text("works_m", "metres"),
            "evidence_class": "G" if works_m is not None else "U"}),
    ])


def stage3_facts(buildings_doc, filtered_doc, anchor, args, out_dir):
    global CURRENT_STAGE
    CURRENT_STAGE = "s3"
    by_key = {b["key"]: b for b in buildings_doc["buildings"]}
    survivors = [r for r in filtered_doc["buildings"] if r["pass"]]
    survivors.sort(key=lambda r: (not r.get("user_supplied"),
                                  r["distance_m"] if r["distance_m"] is not None else 9e9))
    chosen = survivors[:args.max_buildings]
    cdir = os.path.join(out_dir, "candidates")
    os.makedirs(cdir, exist_ok=True)
    records, skipped = [], survivors[args.max_buildings:]
    trim_logs = {}
    osm, osm_note, crime_end = None, "no building reached stage 3", None
    if chosen:
        osm, osm_note = shared_osm(anchor, args)
        if osm_note:
            print("stage 3: %s" % osm_note, file=sys.stderr)
        latest = _safe("crime.latest", [], crime.latest, verbose=args.verbose)
        crime_end = (latest or {}).get("latest_month")
        if crime_end:
            print("stage 3: crime window ends %s for every building" % crime_end,
                  file=sys.stderr)
    for filt in chosen:
        path = os.path.join(cdir, filt["key"] + ".json")
        if args.resume and os.path.exists(path):
            cached = load_json(path)
            if cached is not None:
                records.append(cached)
                continue
        failures = []
        rec = facts_for_building(by_key[filt["key"]], filt, anchor, args, failures,
                                 osm=osm, crime_end=crime_end)
        log = []
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(fit_to_budget(rec, log=log), fh, ensure_ascii=False, indent=1)
        trim_logs[filt["key"]] = log
        records.append(rec)      # untrimmed in memory; stage 5 re-trims with the medians
    return records, [{"key": s["key"], "display_address": s["display_address"],
                      "distance_m": s["distance_m"],
                      "why": "past the --max-buildings cap of %d" % args.max_buildings}
                     for s in skipped], cdir, trim_logs


def sweep_medians(records):
    med = {"_n": len(records)}
    med["crime_total"] = median([(r.get("crime") or {}).get("total") for r in records])
    med["commute_min"] = median([(r.get("commute") or {}).get("all_min") for r in records])
    med["rail_min"] = median([(r.get("commute") or {}).get("rail_min") for r in records])
    med["area_sqft"] = median([(r.get("epc") or {}).get("floor_area_sqft_median")
                               for r in records])
    med["earliest_year"] = median([(r.get("epc") or {}).get("earliest_assessment_year")
                                   for r in records])
    med["distance_m"] = median([r.get("distance_m") for r in records])
    works = []
    for r in records:
        p = r.get("planning") or {}
        t = (p.get("nearest_tall") or {}).get("distance_m")
        if t is None:
            t = ((p.get("nearest") or [{}])[0]).get("distance_m")
        works.append(t)
    med["works_m"] = median(works)
    grades = [g for g in ((r.get("commute") or {}).get("redundancy_grade") for r in records) if g]
    med["grades"] = ", ".join("%s x%d" % (g, n) for g, n in sorted(Counter(grades).items())) \
        if grades else None
    return med


def refill_metrics(records, medians, cdir, trim_logs):
    """Second pass: the sweep median is only knowable once every candidate is in."""
    out = []
    for rec in records:
        rec = copy.deepcopy(rec)
        rec["metrics"] = build_metrics(rec, medians)
        log = []
        fitted = fit_to_budget(rec, log=log)
        trim_logs[rec["key"]] = log
        with open(os.path.join(cdir, rec["key"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump(fitted, fh, ensure_ascii=False, indent=1)
        out.append(fitted)
    return out


# ------------------------------------------------------------------- S4 ------
REVIEW_SITES = ["HomeViews", "Google Maps reviews", "Trustpilot"]
LISTING_PORTALS = ["Rightmove", "Zoopla", "OnTheMarket", "OpenRent"]


def stage4_ask(records, anchor, out_dir):
    global CURRENT_STAGE
    CURRENT_STAGE = "s4"
    lines = []
    lines.append("# What only you can fetch")
    lines.append("")
    lines.append("This sweep read every open register it could: the energy certificate "
                 "register, police open data, the journey planner, the planning index, "
                 "Companies House, the Land Registry and OpenStreetMap. Three things are "
                 "left, and all three need a person, because the sites involved forbid "
                 "automated access.")
    lines.append("")
    lines.append("Send this back in one go. Paste as plain text; do not summarise, because "
                 "the hygiene steps need the individual reviews, their dates and their scores.")
    lines.append("")
    lines.append("## For every building below")
    lines.append("")
    lines.append("1. **Resident reviews.** Open %s and search the building name. Paste every "
                 "review page, oldest first, with dates and scores intact. Why: the public "
                 "average is unusable until prompted reviews and same-day bursts are removed."
                 % ", ".join(REVIEW_SITES))
    lines.append("2. **Listings.** Check %s for flats in the building. Paste the asking rent, "
                 "the advertised size, the floor, the available date and the agent's name for "
                 "each. Why: rent per square foot and the all-in cost cannot be computed "
                 "without a real asking price."
                 % ", ".join(LISTING_PORTALS))
    lines.append("3. **Anything the building sends you.** A tariff sheet for a heat network, "
                 "a service-charge budget, a floor plan with a compass. Upload the file.")
    lines.append("")
    lines.append("## The buildings")
    lines.append("")
    for i, rec in enumerate(records, 1):
        pcs = ", ".join(rec.get("postcodes") or []) or "postcode unknown"
        lines.append("%d. **%s** — %s, about %s m from the anchor."
                     % (i, rec["display_address"], pcs,
                        int(rec["distance_m"]) if rec.get("distance_m") is not None else "?"))
        hints = []
        heat = (rec.get("epc") or {}).get("heating_classes") or {}
        if "community_heat_network" in heat:
            hints.append("ask for the heat-network tariff: the flats are on a communal "
                         "network and the price is not regulated like gas")
        tall = (rec.get("planning") or {}).get("nearest_tall")
        if tall:
            hints.append("ask what stage %s is at: a tall scheme is %s m away"
                         % (tall.get("reference"), tall.get("distance_m")))
        if (rec.get("companies") or {}).get("rmc_rtm_count") == 0:
            hints.append("ask who the managing agent is and who appoints them")
        for h in hints:
            lines.append("   - %s" % h)
    lines.append("")
    lines.append("Nothing here is a URL with a search in it: open the site yourself and search "
                 "the name, so the terms you agreed to are the ones that apply.")
    lines.append("")
    lines.append("Anchor: %s, radius %s m, generated %s by sweep.py %s."
                 % (anchor.get("postcode") or anchor.get("query"), anchor.get("radius_m"),
                    now_iso(), VERSION))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(out_dir, "ask-the-user.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


# ------------------------------------------------------------------- S5 ------
SUMMARY_COLUMNS = [
    "building", "dist m", "certs", "median sqft", "earliest yr", "heating", "grnd %",
    "crime 6mo", "predatory %", "commute all/rail", "redund", "nearest tall (m)",
    "nearest trunk road (m)", "RMC/RTM", "1st new-build",
]


def _row_for(rec):
    e = rec.get("epc") or {}
    c = rec.get("crime") or {}
    m = rec.get("commute") or {}
    p = rec.get("planning") or {}
    r = rec.get("roads") or {}
    lr = rec.get("land_registry") or {}
    co = rec.get("companies") or {}
    heat = e.get("heating_classes") or {}
    heat_s = max(heat.items(), key=lambda kv: kv[1])[0].replace("_", " ") if heat else "?"
    tall = p.get("nearest_tall") or {}
    trunk = r.get("trunk_or_primary") or {}
    gshare = e.get("ground_floor_share")
    pshare = c.get("predatory_share")
    return [
        rec["display_address"][:38],
        "%s" % (int(rec["distance_m"]) if rec.get("distance_m") is not None else "?"),
        "%s" % (e.get("certificates_in_building") or "?"),
        "%s" % (e.get("floor_area_sqft_median") or "?"),
        "%s" % (e.get("earliest_assessment_year") or "?"),
        heat_s,
        "%d" % round(100 * gshare) if gshare is not None else "?",
        "%s" % (c.get("total") if c.get("total") is not None else "?"),
        "%d" % round(100 * pshare) if pshare is not None else "?",
        "%s/%s" % (m.get("all_min") or "?", m.get("rail_min") or "?"),
        "%s" % (m.get("redundancy_grade") or "?"),
        "%s (%s)" % (tall.get("reference") or "none", tall.get("distance_m")
                     if tall.get("distance_m") is not None else "-"),
        "%s (%s)" % ((trunk.get("name") or "none")[:18],
                     trunk.get("distance_m") if trunk.get("distance_m") is not None else "-"),
        "%s" % (co.get("rmc_rtm_count") if co.get("rmc_rtm_count") is not None else "?"),
        "%s" % (lr.get("earliest_new_build_year") or "none"),
    ]


def _md_table(header, rows):
    widths = [len(h) for h in header]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    def line(cells):
        return "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    out = [line(header), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    out += [line(r) for r in rows]
    return "\n".join(out)


def stage5_summary(records, anchor, buildings_doc, filtered_doc, skipped, manifest,
                   args, out_dir, medians, wall_s, trim_logs=None):
    global CURRENT_STAGE
    CURRENT_STAGE = "s5"
    st = buildings_doc["streets"]
    coverage = OrderedDict([
        ("streets_found", st.get("found")),
        ("streets_searched", st.get("searched")),
        ("streets_skipped_over_max", len(st.get("skipped_over_max") or [])),
        ("streets_too_many_results", len(st.get("too_many_results") or [])),
        ("postcode_fallback_searches",
         (buildings_doc.get("postcode_fallback") or {}).get("postcodes_searched", 0)),
        ("postcodes_not_searched_over_cap",
         (buildings_doc.get("postcode_fallback") or {}).get("postcodes_not_searched", 0)),
        ("certificates_seen", buildings_doc.get("certificates_seen")),
        ("certificates_outside_radius", buildings_doc.get("certificates_outside_radius")),
        ("postcode_lookups", (buildings_doc.get("postcode_book") or {}).get("individual_lookups")),
        ("postcodes_not_geocoded",
         len((buildings_doc.get("postcode_book") or {}).get("not_geocoded") or [])),
        ("buildings", buildings_doc["counts"]["buildings"]),
        ("merged_abbreviated_streets",
         buildings_doc["counts"].get("merged_abbreviated_streets", 0)),
        ("excluded", buildings_doc["counts"]["excluded"]),
        ("assessed_in_hard_filter", filtered_doc["counts"]["assessed"]),
        ("passed_hard_filter", filtered_doc["counts"]["passed"]),
        ("failed_hard_filter", filtered_doc["counts"]["failed"]),
        ("not_assessed_over_filter_cap",
         filtered_doc["counts"].get("not_assessed_over_cap", 0)),
        ("fetched_facts_for", len(records)),
        ("over_max_buildings", len(skipped)),
        ("fetches", manifest.total),
        ("fetches_from_cache", manifest.total - manifest.network_calls),
        ("failures", len(manifest.failures)),
        ("wall_seconds", round(wall_s, 1)),
    ])
    excluded = [{"key": b["key"], "display_address": b["display_address"],
                 "excluded_code": b["excluded_code"], "reason": b["excluded_reason"]}
                for b in buildings_doc["buildings"] if b["excluded_code"]]
    failed = [{"key": b["key"], "display_address": b["display_address"],
               "reasons": b["fail_reasons"]}
              for b in filtered_doc["buildings"] if b.get("assessed") and not b["pass"]]
    not_assessed = [{"key": b["key"], "display_address": b["display_address"],
                     "distance_m": b["distance_m"]}
                    for b in filtered_doc["buildings"] if not b.get("assessed")]
    not_found = list(buildings_doc.get("not_found") or [])
    recovered = set(r["url"] for r in manifest.records if r["ok"])
    for f in manifest.failures[:20]:
        if f["url"] in recovered:
            continue                       # a retry or the mirror answered; not a gap
        not_found.append({"what": "a fetch that failed", "queries_used": [f["url"]],
                          "where_looked": f["url"].split("/")[2] if "//" in f["url"] else "?",
                          "next_step": "re-run; the note was: %s" % (f["note"] or f["status"])})
    rows = [_row_for(r) for r in records]
    med_row = ["MEDIAN", "%s" % (int(medians["distance_m"]) if medians.get("distance_m") else "?"),
               "-", "%s" % (medians.get("area_sqft") or "?"),
               "%s" % (int(medians["earliest_year"]) if medians.get("earliest_year") else "?"),
               "-", "-", "%s" % (medians.get("crime_total") or "?"), "-",
               "%s/%s" % (medians.get("commute_min") or "?", medians.get("rail_min") or "?"),
               "-", "%s" % (medians.get("works_m") or "?"), "-", "-", "-"]
    summary = OrderedDict([
        ("generated_at", now_iso()),
        ("generated_by", "sweep.py %s" % VERSION),
        ("anchor", {k: anchor.get(k) for k in
                    ("query", "kind", "lat", "lng", "postcode", "admin_district",
                     "radius_m", "destination", "arrive_by", "town_searched")}),
        ("profile_source", anchor.get("profile_source")),
        ("profile_snapshot", anchor.get("profile_snapshot")),
        ("coverage", coverage),
        ("sweep_medians", {k: v for k, v in medians.items() if k != "_n"}),
        ("table_columns", SUMMARY_COLUMNS),
        ("table_rows", rows),
        ("candidates", [{"key": r["key"], "display_address": r["display_address"],
                         "distance_m": r.get("distance_m"),
                         "file": "candidates/%s.json" % r["key"],
                         "bytes": json_bytes(r),
                         "trimmed_fields": (trim_logs or {}).get(r["key"]) or []}
                        for r in records]),
        ("excluded_buildings", excluded),
        ("failed_hard_filter", failed),
        ("not_assessed_over_filter_cap", not_assessed),
        ("skipped_over_max_buildings", skipped),
        ("not_found", not_found),
        ("manifest", manifest.summary()),
    ])
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)

    md = ["# Area sweep — %s, radius %s m" % (anchor.get("postcode") or anchor.get("query"),
                                              anchor.get("radius_m")),
          "",
          "Anchor %s,%s (%s). Destination %s, arriving %s. Profile: %s."
          % (anchor.get("lat"), anchor.get("lng"), anchor.get("admin_district") or "?",
             anchor.get("destination"), anchor.get("arrive_by"), anchor.get("profile_source")),
          "",
          "## Candidates", ""]
    md.append(_md_table(SUMMARY_COLUMNS, rows + [med_row]))
    md += ["", "Crime is a %d-month window in a %d m box; commute is door-to-door minutes for "
                "'any mode / rail only'; redundancy is the strike-family grade; the tall column "
                "is the nearest planning application flagged as a tall building within %d m."
           % (args.crime_months, 2 * args.crime_half_m, args.planning_radius),
           "", "## Coverage", ""]
    md.append(_md_table(["what", "count"], [[k.replace("_", " "), v]
                                            for k, v in coverage.items()]))
    if excluded:
        md += ["", "## Excluded at stage 1b", ""]
        md.append(_md_table(["building", "code", "why"],
                            [[e["display_address"][:44], e["excluded_code"],
                              (e["reason"] or "")[:60]] for e in excluded]))
    if not_assessed:
        md += ["", "## Not assessed", "",
               "%d building(s) sat past the --max-filter-buildings cap of %s and were never "
               "sampled, nearest first. They are neither passed nor failed; raise the cap or "
               "narrow the radius to reach them. The full list is in summary.json."
               % (len(not_assessed), args.max_filter_buildings or "none")]
    if failed:
        md += ["", "## Failed the hard filter", ""]
        md.append(_md_table(["building", "why"],
                            [[f["display_address"][:44], "; ".join(f["reasons"])[:80]]
                             for f in failed[:20]]))
    if not_found:
        md += ["", "## Not found (the exact queries)", ""]
        for nf in not_found[:20]:
            md.append("- %s — tried: %s" % (nf["what"], "; ".join(nf["queries_used"])[:200]))
    md += ["", "Generated with vet-flat sweep.py %s — "
               "https://github.com/jacky18008/pea-princess" % VERSION, ""]
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    skeleton = OrderedDict([
        ("_skeleton_notes", [
            "Written by sweep.py. It is NOT yet valid against report-schema.json: every "
            "candidate still needs verdict, twelve axes, costs and landmines.",
            "Replace every 'TO BE WRITTEN BY THE MODEL' string before publishing.",
            "Delete every key that starts with an underscore when you are done.",
        ]),
        ("schema_version", "1"),
        ("generated_by", {"name": "vet-flat sweep.py", "version": VERSION}),
        ("generated_at", now_iso()),
        ("language", (anchor.get("profile_snapshot") or {}).get("language") or "en"),
        ("profile_snapshot", anchor.get("profile_snapshot")),
        ("candidates", [OrderedDict([
            ("id", "c%d" % (i + 1)),
            ("identity", {"display_name": r["display_address"][:80],
                          "address": r["display_address"][:200],
                          "postcode": (r.get("postcodes") or ["?"])[0],
                          "building": (r["display_address"].split(",")[0])[:120]}),
            ("metrics", r.get("metrics")),
            ("hard_filters", _skeleton_filters(r, filtered_doc)),
            ("_facts_file", "candidates/%s.json" % r["key"]),
        ]) for i, r in enumerate(records)]),
        ("not_found", not_found[:40]),
        ("blocked_sources", [
            {"source": "Resident review sites (%s)" % ", ".join(REVIEW_SITES),
             "http_status": "not requested",
             "reason": "Their terms forbid automated access, so this skill has no method "
                       "for them.",
             "workaround": "Open the site, search the building name and paste the reviews; "
                           "see ask-the-user.md."},
            {"source": "Listing portals (%s)" % ", ".join(LISTING_PORTALS),
             "http_status": "not requested",
             "reason": "Their terms forbid automated access.",
             "workaround": "Paste the listing text and the asking rent."},
        ] + _blocked_from_manifest(manifest)),
        ("sources", _sources(records, buildings_doc, manifest)),
        ("footer", "Generated with vet-flat sweep.py %s — "
                   "https://github.com/jacky18008/pea-princess" % VERSION),
    ])
    with open(os.path.join(out_dir, "report-skeleton.json"), "w", encoding="utf-8") as fh:
        json.dump(skeleton, fh, ensure_ascii=False, indent=1)
    return summary, "\n".join(md)


def _skeleton_filters(rec, filtered_doc):
    for row in filtered_doc["buildings"]:
        if row["key"] == rec["key"]:
            return row.get("checks") or []
    return []


def _blocked_from_manifest(manifest):
    seen, out = set(), []
    for f in manifest.failures:
        host = f["url"].split("/")[2] if "//" in f["url"] else f["url"][:40]
        if host in seen:
            continue
        seen.add(host)
        out.append({"source": host, "http_status": f["status"],
                    "reason": (f["note"] or "the request did not return the expected page")[:300],
                    "workaround": "re-run the sweep; a repeat failure means the source is down "
                                  "or refusing this tool"})
    return out[:10]


def _sources(records, buildings_doc, manifest):
    """The sources the report actually cites: every block-level source_url in the
    candidate records first, then anything else the manifest fetched successfully.

    Built from the records rather than only from the manifest, because a `--resume`
    run fetches almost nothing and its manifest would name almost nothing.
    """
    out, seen = [], set()

    def dedupe_key(url):
        """One entry per endpoint, not per call: the query string and the certificate
        id are what change between calls, and the ids are in the candidate records."""
        base = url.split("?")[0]
        return re.sub(r"/energy-certificate/[0-9-]+$", "/energy-certificate/", base)

    def add(url, retrieved_at, evidence_class, name=None, status=None):
        if not url:
            return
        k = dedupe_key(url)
        if k in seen:
            return
        seen.add(k)
        host = url.split("/")[2] if "//" in url else url[:40]
        out.append({"id": slug("%s-%d" % (host, len(out)), 48), "name": name or host,
                    "url": url[:500],
                    "retrieved_at": retrieved_at or now_iso(),
                    "evidence_class": evidence_class or "G", "http_status": status})

    st = (buildings_doc or {}).get("streets") or {}
    add(st.get("source_url"), st.get("retrieved_at"), st.get("evidence_class"),
        "OpenStreetMap via Overpass")
    add("https://find-energy-certificate.service.gov.uk/",
        (buildings_doc or {}).get("generated_at"), "G",
        "GOV.UK energy certificate register")
    for rec in records or []:
        for block in ("epc", "crime", "commute", "planning", "roads", "land_registry",
                      "companies", "heat_network"):
            b = rec.get(block) or {}
            add(b.get("source_url"), b.get("retrieved_at"), b.get("evidence_class"))
    for r in manifest.records:
        if r["ok"]:
            add(r["url"], r["retrieved_at"], "G", status=r["status"])
    return out[:40]


# ------------------------------------------------------------------- plan ----
# Per-building fetch model for stage 3, used by --dry-run and the cost line.
def fetch_estimate(n_streets, n_buildings_filtered, certs_per_building, n_facts,
                   crime_months):
    per_building_facts = (crime_months * 5      # crime.box: months x centre + 4 shifts
                          + 2                   # commute.journey: 'all' and 'rail'
                          + 2                   # commute.redundancy: stations (+ bus)
                          + 1                   # planning.near
                          + 1                   # landregistry.price_paid
                          + 1)                  # company.address_search
    return OrderedDict([
        ("street_query", 1),
        ("shared_openstreetmap_query", 1),
        ("epc_street_searches", n_streets),
        ("postcode_lookups", "up to the --max-postcode-lookups cap"),
        ("epc_certificates", n_buildings_filtered * certs_per_building),
        ("per_building_facts", per_building_facts),
        ("facts_total", n_facts * per_building_facts),
        ("grand_total_excluding_postcodes",
         2 + n_streets + n_buildings_filtered * certs_per_building
         + n_facts * per_building_facts),
        ("postcode_fallback_searches", "0 unless the register refuses a street as "
                                       "'too many results'; then up to --postcode-fallback"),
        ("note", "past months of police data and every certificate page are cached on disk, "
                 "so a re-run inside the cache window costs almost nothing"),
    ])


# ------------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor", required=True,
                    help='a postcode ("SE1 9SG") or coordinates ("51.5045,-0.0865")')
    ap.add_argument("--radius", type=int, default=DEFAULT_RADIUS_M,
                    help="enumeration radius in metres (default %d, max %d)"
                         % (DEFAULT_RADIUS_M, MAX_RADIUS_M))
    ap.add_argument("--dest", help="commute destination; required unless --profile has one")
    ap.add_argument("--arrive", help="arrival time HH:MM (default from the profile, else 09:00)")
    ap.add_argument("--profile", help="profile.yaml with the hard filters")
    ap.add_argument("--candidates", help="file of addresses or postcodes, one per line, "
                                         "always included")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--town", help="postal town for the street search (default London)")
    ap.add_argument("--max-streets", type=int, default=0,
                    help="cap the street census (0 = no cap)")
    ap.add_argument("--postcode-fallback", type=int, default=40,
                    help="when the register refuses a street as 'too many results', search "
                         "this many postcodes instead, nearest first (0 = off)")
    ap.add_argument("--max-postcode-lookups", type=int, default=120,
                    help="cap the one-by-one postcode geocodes (default 120)")
    ap.add_argument("--max-filter-buildings", type=int, default=25,
                    help="cap the buildings that get a certificate sample, nearest first "
                         "(default 25, 0 = no cap)")
    ap.add_argument("--certs-per-building", type=int, default=8,
                    help="certificates sampled per building at stage 2 (default 8)")
    ap.add_argument("--max-buildings", type=int, default=8,
                    help="cap the buildings that get the full fact run (default 8)")
    ap.add_argument("--crime-months", type=int, default=6)
    ap.add_argument("--crime-half-m", type=float, default=150.0)
    ap.add_argument("--planning-radius", type=int, default=250)
    ap.add_argument("--roads-radius", type=int, default=300)
    ap.add_argument("--resume", action="store_true",
                    help="reuse stage files already in --out instead of recomputing")
    ap.add_argument("--dry-run", action="store_true",
                    help="locate the anchor, count the streets, print the plan and stop")
    ap.add_argument("--verbose", action="store_true", help="print the curl commands to stderr")
    args = ap.parse_args()
    global CURRENT_STAGE

    if args.radius <= 0:
        ap.error("--radius must be positive")
    if args.radius > MAX_RADIUS_M:
        ap.error("--radius %d m is beyond the %d m ceiling this tool will sweep"
                 % (args.radius, MAX_RADIUS_M))
    if args.radius > 1200:
        print("warning: a %d m radius means a large street census and hundreds of fetches; "
              "run --dry-run first" % args.radius, file=sys.stderr)

    prof, prof_source, prof_warnings = read_profile(args.profile)
    for w in prof_warnings:
        print("profile: %s" % w, file=sys.stderr)
    if not args.dest and not prof.get("destination"):
        ap.error("--dest is required unless the profile sets commute.destination")

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    manifest = Manifest()
    manifest.install(FETCH_MODULES)
    started = time.time()
    try:
        anchor_path = os.path.join(out_dir, "anchor.json")
        anchor = None
        if args.resume and os.path.exists(anchor_path):
            anchor = load_json(anchor_path)
        if anchor is None:
            anchor = stage0_anchor(args, prof, prof_source, prof_warnings)
            with open(anchor_path, "w", encoding="utf-8") as fh:
                json.dump(anchor, fh, ensure_ascii=False, indent=1)
        if not anchor.get("ok") or anchor.get("lat") is None:
            print("could not locate the anchor: %s" % anchor.get("note"), file=sys.stderr)
            return 1
        if anchor.get("radius_warning"):
            print("warning: %s" % anchor["radius_warning"], file=sys.stderr)

        if args.dry_run:
            CURRENT_STAGE = "s1"
            st = streets_in_circle(anchor["lat"], anchor["lng"], args.radius,
                                   verbose=args.verbose)
            n_streets = len(st["streets"]) if not args.max_streets \
                else min(len(st["streets"]), args.max_streets)
            plan_out = OrderedDict([
                ("dry_run", True), ("anchor", anchor),
                ("streets_found", len(st["streets"])),
                ("streets_that_would_be_searched", n_streets),
                ("street_names", [s["name"] for s in st["streets"][:n_streets]]),
                ("caps", {"max_streets": args.max_streets,
                          "max_postcode_lookups": args.max_postcode_lookups,
                          "max_filter_buildings": args.max_filter_buildings,
                          "certs_per_building": args.certs_per_building,
                          "max_buildings": args.max_buildings}),
                ("estimated_fetches",
                 fetch_estimate(n_streets, args.max_filter_buildings or 25,
                                args.certs_per_building, args.max_buildings,
                                args.crime_months)),
                ("manifest", manifest.summary()),
            ])
            json.dump(plan_out, sys.stdout, ensure_ascii=False, indent=1)
            print()
            return 0

        book = PostcodeBook(anchor["lat"], anchor["lng"], args.radius,
                            max_lookups=args.max_postcode_lookups)
        b_path = os.path.join(out_dir, "buildings.json")
        buildings_doc = None
        if args.resume and os.path.exists(b_path):
            buildings_doc = load_json(b_path)
        if buildings_doc is None:
            extra = read_candidates_file(args.candidates, anchor["town_searched"])
            buildings_doc = stage1_enumerate(anchor, args, book, extra)
            with open(b_path, "w", encoding="utf-8") as fh:
                json.dump(buildings_doc, fh, ensure_ascii=False, indent=1)
        print("stage 1: %d streets searched, %d certificates, %d buildings (%d excluded)"
              % (buildings_doc["streets"]["searched"], buildings_doc["certificates_seen"],
                 buildings_doc["counts"]["buildings"], buildings_doc["counts"]["excluded"]),
              file=sys.stderr)

        f_path = os.path.join(out_dir, "filtered.json")
        filtered_doc = None
        if args.resume and os.path.exists(f_path):
            filtered_doc = load_json(f_path)
        if filtered_doc is None:
            filtered_doc = stage2_filter(buildings_doc, prof, args)
            with open(f_path, "w", encoding="utf-8") as fh:
                json.dump(filtered_doc, fh, ensure_ascii=False, indent=1)
        print("stage 2: %d assessed, %d passed, %d failed, %d not assessed (over the "
              "--max-filter-buildings cap)"
              % (filtered_doc["counts"]["assessed"], filtered_doc["counts"]["passed"],
                 filtered_doc["counts"]["failed"],
                 filtered_doc["counts"].get("not_assessed_over_cap", 0)), file=sys.stderr)

        n_facts = min(args.max_buildings, filtered_doc["counts"]["passed"])
        est = fetch_estimate(buildings_doc["streets"]["searched"],
                             filtered_doc["counts"]["assessed"], args.certs_per_building,
                             n_facts, args.crime_months)
        print("stage 3 plan: %d building(s) x about %d fetches = about %d fetches "
              "(%d already spent)" % (n_facts, est["per_building_facts"], est["facts_total"],
                                      manifest.total), file=sys.stderr)

        records, skipped, cdir, trim_logs = stage3_facts(buildings_doc, filtered_doc,
                                                         anchor, args, out_dir)
        medians = sweep_medians(records)
        records = refill_metrics(records, medians, cdir, trim_logs)
        stage4_ask(records, anchor, out_dir)
        summary, _ = stage5_summary(records, anchor, buildings_doc, filtered_doc, skipped,
                                    manifest, args, out_dir, medians, time.time() - started,
                                    trim_logs)
    finally:
        with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"generated_at": now_iso(), "summary": manifest.summary(),
                       "fetches": manifest.records}, fh, ensure_ascii=False, indent=1)
        manifest.remove(FETCH_MODULES)

    json.dump({"ok": True, "out": os.path.abspath(out_dir),
               "candidates": len(records),
               "coverage": summary["coverage"],
               "sweep_medians": summary["sweep_medians"],
               "files": ["anchor.json", "buildings.json", "filtered.json",
                         "candidates/*.json", "ask-the-user.md", "summary.json",
                         "summary.md", "report-skeleton.json", "manifest.json"]},
              sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
