#!/usr/bin/env python3
"""Landing: what is happening in London between the day you land and the day you get keys.

Two rules come before any listing, and this tool is built to serve them
(`references/axes/15-bridging-short-lets.md`):

  1. Book the bridge first. Somewhere to sleep for the first two weeks, booked
     before you fly: a hotel or an operator-run serviced stay. A private short let
     only after you have seen it or verified it live.
  2. Signing is not moving in. Referencing, the deposit going into a scheme and the
     previous tenant's move-out sit between the signature and the keys. The
     maintainer's own gap ran 45 days in one stretch (London, 2026).

Four sources, then one plan:
  holidays  GOV.UK bank holidays JSON (open, no key)
  closures  TfL Unified API line status over a date range (open, no key at this volume)
  terms     references/term-dates.yaml, curated by hand, with the source and the day
            a human read it. Term start is the STRUCTURAL squeeze: it tightens long
            lets and short lets together, every September, across the whole city.
  events    references/london-events.yaml, curated. Citywide occasions with a typical
            window, and the venues whose own calendars you have to open yourself.
            A venue is local and occasional; it is not the September squeeze.

The magnitude rule, everywhere in this tool: these things are known to push local
prices up. We have not measured by how much, so no number is ever printed for it.

Usage:
  landing.py holidays --from 2026-09-16 --to 2026-11-04 [--division england-and-wales]
  landing.py closures --from 2026-09-16 --to 2026-09-30 [--lines tube,dlr,overground,elizabeth-line,national-rail]
  landing.py terms --year 2026 [--uni kcl,ucl]
  landing.py events --from 2026-09-16 --to 2026-11-04 [--near "Deptford, Lewisham"] [--paste events.txt]
  landing.py plan --arrive 2026-09-16 --start 2026-10-01 [--keys-by 2026-11-04 | --gap-weeks 6]
                   [--areas "Deptford, Lewisham"] [--budget-all-in 1900] [--bridge-weekly 550]

Add --plain for the table a person reads, --offline to read tests/fixtures/landing,
--verbose to see the curl commands on stderr. One JSON object on stdout by default.
Exit 0 on success, 2 on a usage error, 1 when a fetch failed.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import fetch  # noqa: E402


REFERENCES = os.path.join(os.path.dirname(HERE), "references")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "landing")
TERM_DATES_YAML = os.path.join(REFERENCES, "term-dates.yaml")
EVENTS_YAML = os.path.join(REFERENCES, "london-events.yaml")
AXIS_15 = "references/axes/15-bridging-short-lets.md"

BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"
BANK_HOLIDAYS_SOURCE = "GOV.UK bank holidays (england-and-wales division)"
TFL_BASE = "https://api.tfl.gov.uk"
RAIL_MODES = ("tube", "dlr", "overground", "elizabeth-line", "national-rail")
GOOD_SERVICE = 10

DEFAULT_GAP_WEEKS = (4, 7)
REFERENCE_GAP_DAYS = 45
REFERENCE_GAP_NOTE = ("the maintainer's own gap between signing and keys ran 45 days in one "
                      "stretch (London, 2026) — evidence grade ●, one case, not an average")
WEEKS_PER_YEAR = 52.0
FIRST_WEEKS_TIER = "hotel or operator-run serviced stay"
FIRST_WEEKS_WHY = ("protected money, an instant exit and someone responsible, at a known premium "
                   "per night and usually without a kitchen. Whether the very first nights are a "
                   "hotel is your choice; arriving with nothing booked is not")
LATER_TIER = "operator stay, or a private short let only after you have seen it or verified it live"
CALC = os.path.join(HERE, "calc.py")
EARTH_KM = 6371.0088


def die(msg, code=2):
    sys.stderr.write("landing.py: %s\n" % msg)
    raise SystemExit(code)


def today_date(arg=None):
    return dt.date.fromisoformat(arg) if arg else dt.date.today()


def as_date(text, label):
    try:
        return dt.date.fromisoformat(str(text).strip())
    except Exception:
        die("%s must be a date as YYYY-MM-DD, got %r" % (label, text))


# ------------------------------------------------------------------- yaml ----
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _scalar(text):
    s = text.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [] if not inner else [_scalar(p) for p in inner.split(",")]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    if " #" in s:
        s = s.split(" #", 1)[0].strip()
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    if _DATE_RE.match(s):
        return s
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def parse_yaml(text):
    """The deliberately tiny YAML subset the two curated files are written in.

    Maps, lists of maps, inline lists, comments, quoted strings, ISO dates. No
    anchors, no block scalars, no flow maps. Python 3.9, no package.
    """
    rows = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        body = raw.strip()
        if not body or body.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if body.startswith("- "):
            rows.append((indent, "-"))
            rows.append((indent + 2, body[2:].strip()))
        elif body == "-":
            rows.append((indent, "-"))
        else:
            rows.append((indent, body))
    if not rows:
        return {}
    value, _ = _parse_rows(rows, 0, rows[0][0])
    return value


def _parse_rows(rows, i, indent):
    if i < len(rows) and rows[i][0] == indent and rows[i][1] == "-":
        items = []
        while i < len(rows) and rows[i][0] == indent and rows[i][1] == "-":
            i += 1
            if i < len(rows) and rows[i][0] > indent:
                item, i = _parse_rows(rows, i, rows[i][0])
            else:
                item = None
            items.append(item)
        return items, i
    out = {}
    while i < len(rows) and rows[i][0] == indent and rows[i][1] != "-":
        key, sep, rest = rows[i][1].partition(":")
        i += 1
        if not sep:
            continue
        key, rest = key.strip(), rest.strip()
        if rest:
            out[key] = _scalar(rest)
        elif i < len(rows) and rows[i][0] > indent:
            child, i = _parse_rows(rows, i, rows[i][0])
            out[key] = child
        elif i < len(rows) and rows[i][0] == indent and rows[i][1] == "-":
            child, i = _parse_rows(rows, i, indent)
            out[key] = child
        else:
            out[key] = None
    return out, i


def read_yaml(path):
    if not os.path.exists(path):
        die("no such file: %s" % path, 2)
    with open(path, encoding="utf-8") as fh:
        return parse_yaml(fh.read())


def load_terms(path=None):
    return read_yaml(path or TERM_DATES_YAML)


def load_events(path=None):
    return read_yaml(path or EVENTS_YAML)


# ------------------------------------------------------------------ fetch ----
def read_fixture(name, fixtures=None):
    path = os.path.join(fixtures or FIXTURES, name)
    if not os.path.exists(path):
        die("--offline wanted %s and it is not there" % path, 1)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _envelope(url, res):
    return {"source_url": url, "http_status": res["status"], "ok": bool(res["ok"]),
            "note": res["note"], "retrieved_at": res["retrieved_at"], "from_cache": res["from_cache"],
            "evidence_class": "G"}


def _unknown(note):
    return ("unknown, try again — %s. Nothing here is a claim that there is nothing to find; "
            "it is a claim that I could not look." % note)


# --------------------------------------------------------------- holidays ----
def parse_holidays(obj, start, end, division="england-and-wales"):
    """A bank-holidays.json body -> the holidays inside [start, end]. Pure: no network."""
    if not isinstance(obj, dict) or division not in obj:
        return None, "the feed has no %r division (it has: %s)" % (
            division, ", ".join(sorted(obj.keys())) if isinstance(obj, dict) else "nothing")
    events = (obj.get(division) or {}).get("events") or []
    rows = []
    for e in events:
        try:
            d = dt.date.fromisoformat(e.get("date") or "")
        except Exception:
            continue
        if start <= d <= end:
            rows.append({"date": d.isoformat(), "title": e.get("title"),
                         "notes": e.get("notes") or "", "weekday": d.strftime("%A")})
    rows.sort(key=lambda r: r["date"])
    return rows, ""


def holidays(start, end, division="england-and-wales", offline=False, fixtures=None,
             verbose=False):
    out = {"command": "holidays", "query": {"from": start.isoformat(), "to": end.isoformat(),
                                            "division": division},
           "source": BANK_HOLIDAYS_SOURCE, "source_url": BANK_HOLIDAYS_URL}
    if offline:
        obj = read_fixture("bank-holidays.json", fixtures)
        out.update(http_status=None, ok=True, note="", retrieved_at="fixture",
                   from_cache=True, evidence_class="G", offline=True)
    else:
        res = fetch(BANK_HOLIDAYS_URL, cache_ttl=7 * 86400, verbose=verbose,
                    expect=lambda b: '"england-and-wales"' in b)
        out.update(_envelope(BANK_HOLIDAYS_URL, res))
        out["offline"] = False
        if not res["ok"]:
            out["ok"] = False
            out["note"] = _unknown("the bank holidays feed answered %s" % (res["note"] or "badly"))
            out["holidays"] = []
            return out
        try:
            obj = json.loads(res["body"])
        except ValueError as exc:
            out["ok"] = False
            out["note"] = _unknown("the feed was not JSON (%s)" % str(exc)[:80])
            out["holidays"] = []
            return out
    rows, why = parse_holidays(obj, start, end, division)
    if rows is None:
        out["ok"] = False
        out["note"] = _unknown(why)
        out["holidays"] = []
        return out
    out["holidays"] = rows
    out["count"] = len(rows)
    out["method"] = ("Every bank holiday the government publishes for %s that falls inside your "
                     "dates. A bank holiday is a day agents, referencing companies, councils and "
                     "deposit schemes are shut, so a signature or a key handover cannot land on "
                     "it." % division)
    return out


# --------------------------------------------------------------- closures ----
def closures_url(modes, start, end):
    return ("%s/Line/Mode/%s/Status?startDate=%s&endDate=%s&detail=true"
            % (TFL_BASE, ",".join(modes), start.isoformat(), end.isoformat()))


def _period_dates(period):
    def one(key):
        raw = (period or {}).get(key)
        if not raw:
            return None
        try:
            return dt.date.fromisoformat(str(raw)[:10])
        except Exception:
            return None
    return one("fromDate"), one("toDate")


def parse_closures(obj, start, end, modes=None):
    """A Line status body -> the disruptions overlapping [start, end]. Pure: no network.

    A status of Good Service is dropped. A status whose validity periods all sit
    outside the range is dropped: that is the overlap test. A status with no
    validity period at all is kept, flagged, and dated to the whole range — TfL
    only returned it because it applies somewhere in the range.
    """
    want = set(m.strip().lower() for m in (modes or []) if str(m).strip())
    rows = []
    for line in obj if isinstance(obj, list) else []:
        mode = (line.get("modeName") or "").lower()
        if want and mode not in want:
            continue
        for status in line.get("lineStatuses") or []:
            severity = status.get("statusSeverity")
            if severity == GOOD_SERVICE:
                continue
            periods, overlaps = [], False
            for p in status.get("validityPeriods") or []:
                a, b = _period_dates(p)
                if a is None and b is None:
                    continue
                a = a or start
                b = b or end
                periods.append({"from": a.isoformat(), "to": b.isoformat()})
                if a <= end and b >= start:
                    overlaps = True
            if periods and not overlaps:
                continue
            disruption = status.get("disruption") or {}
            rows.append({
                "line_id": line.get("id"),
                "line_name": line.get("name"),
                "mode": line.get("modeName"),
                "severity": severity,
                "severity_description": status.get("statusSeverityDescription"),
                "reason": (status.get("reason") or disruption.get("description") or "").strip(),
                "category": disruption.get("category"),
                "planned": (disruption.get("category") == "PlannedWork"
                            or "closure" in str(status.get("statusSeverityDescription")).lower()),
                "validity_periods": periods,
                "dated": bool(periods),
                "note": "" if periods else ("TfL gave no dates for this one; it applies somewhere "
                                            "in the range you asked for"),
            })
    rows.sort(key=lambda r: (r["mode"] or "", r["line_id"] or ""))
    return rows


def closures(start, end, modes=None, offline=False, fixtures=None, verbose=False):
    modes = [m for m in (modes or RAIL_MODES)]
    url = closures_url(modes, start, end)
    out = {"command": "closures",
           "query": {"from": start.isoformat(), "to": end.isoformat(), "modes": modes},
           "source": "TfL Unified API, line status by mode over a date range",
           "source_url": url}
    if offline:
        obj = read_fixture("tfl-line-status.json", fixtures)
        out.update(http_status=None, ok=True, note="", retrieved_at="fixture",
                   from_cache=True, evidence_class="G", offline=True)
    else:
        res = fetch(url, cache_ttl=6 * 3600, verbose=verbose,
                    expect=lambda b: b.strip().startswith("["))
        out.update(_envelope(url, res))
        out["offline"] = False
        if not res["ok"]:
            out["ok"] = False
            out["note"] = _unknown("TfL answered %s" % (res["note"] or "badly"))
            out["closures"] = []
            return out
        try:
            obj = json.loads(res["body"])
        except ValueError as exc:
            out["ok"] = False
            out["note"] = _unknown("TfL did not send JSON (%s)" % str(exc)[:80])
            out["closures"] = []
            return out
    rows = parse_closures(obj, start, end, modes)
    out["closures"] = rows
    out["count"] = len(rows)
    out["planned_count"] = sum(1 for r in rows if r["planned"])
    out["method"] = ("Everything TfL is not calling a Good Service on these modes between your two "
                     "dates. Planned work is published weeks ahead and is the kind that ruins a "
                     "moving day; anything else on this list is today's mess, not a forecast. No "
                     "key is needed at this volume.")
    return out


# ------------------------------------------------------------------ terms ----
def stale_days(checked_on, today):
    try:
        d = dt.date.fromisoformat(str(checked_on))
    except Exception:
        return None
    return (today - d).days


def terms(year, unis=None, today=None, path=None):
    today = today or dt.date.today()
    doc = load_terms(path)
    limit = int(doc.get("staleness_days") or 300)
    academic = str(doc.get("academic_year") or "")
    rows, warnings = [], []
    want = set(u.strip().lower() for u in (unis or []) if str(u).strip())
    known = [u for u in (doc.get("universities") or []) if isinstance(u, dict)]
    missing = sorted(want - {str(u.get("id")).lower() for u in known}) if want else []
    for u in known:
        if want and str(u.get("id")).lower() not in want:
            continue
        age = stale_days(u.get("checked_on"), today)
        stale = age is not None and age > limit
        row = dict(u)
        row["checked_days_ago"] = age
        row["stale"] = bool(stale)
        rows.append(row)
        if stale:
            warnings.append("%s was last checked %d days ago, more than the %d-day limit — open %s "
                            "and read the dates again before planning a move around them."
                            % (u.get("name"), age, limit, u.get("source")))
        if u.get("estimated"):
            warnings.append("%s: %s" % (u.get("name"), u.get("estimate_note") or "estimated"))
    out = {"command": "terms",
           "query": {"year": year, "uni": sorted(want) or "all"},
           "academic_year": academic,
           "source": "references/term-dates.yaml (curated by hand, one source URL per row)",
           "source_url": "references/term-dates.yaml",
           "as_of": doc.get("checked_on"),
           "staleness_days": limit,
           "ok": True, "note": "", "evidence_class": "G",
           "universities": rows, "count": len(rows), "warnings": warnings,
           "method": ("Term start is the structural squeeze: every September it tightens long lets "
                      "and short lets at the same time, across the whole city. These are the dates "
                      "the students move on. A row marked estimated could not be read on the "
                      "university's own page and says so in plain words.")}
    if missing:
        out["not_in_file"] = missing
        out["warnings"].append("I have no rows for: %s. This file covers ten London universities; "
                               "for anywhere else, open the university's own term-dates page."
                               % ", ".join(missing))
    if academic and not academic.startswith(str(year)):
        out["ok"] = False
        out["note"] = _unknown("this file covers %s only, and you asked for %s" % (academic, year))
    return out


# ----------------------------------------------------------------- events ----
def _mmdd_window(spike, year):
    """The typical window of a spike, as concrete dates in `year`. Handles the wrap at New Year."""
    a, b = spike.get("window_from"), spike.get("window_to")
    if not a or not b:
        return None
    try:
        am, ad = [int(x) for x in str(a).split("-")]
        bm, bd = [int(x) for x in str(b).split("-")]
    except Exception:
        return None
    start = dt.date(year, am, ad)
    end = dt.date(year if (bm, bd) >= (am, ad) else year + 1, bm, bd)
    return start, end


def _last_monday_august(year):
    d = dt.date(year, 8, 31)
    while d.weekday() != 0:
        d -= dt.timedelta(days=1)
    return d


def spike_windows(spike, start, end):
    """Every concrete window of one spike that overlaps [start, end]."""
    hits = []
    for year in range(start.year - 1, end.year + 1):
        if spike.get("anchor") == "last_monday_august":
            monday = _last_monday_august(year)
            window = (monday - dt.timedelta(days=1), monday)
        else:
            window = _mmdd_window(spike, year)
        if not window:
            continue
        a, b = window
        if a <= end and b >= start:
            hits.append({"from": a.isoformat(), "to": b.isoformat()})
    seen, uniq = set(), []
    for h in hits:
        key = (h["from"], h["to"])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    return uniq


def haversine_km(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return EARTH_KM * 2 * math.asin(min(1.0, math.sqrt(a)))


def resolve_areas(names, doc):
    """Area names or postcode districts -> gazetteer rows, plus what could not be placed."""
    areas = [a for a in (doc.get("areas") or []) if isinstance(a, dict)]
    index = {}
    for a in areas:
        index[str(a.get("district", "")).lower()] = a
        for n in a.get("names") or []:
            index[str(n).lower()] = a
    found, unplaced = [], []
    for raw in names:
        key = re.sub(r"[^a-z0-9 ]", "", str(raw).strip().lower()).strip()
        hit = index.get(key)
        if hit is None and key:
            hit = next((a for k, a in index.items() if k and (k in key or key in k)), None)
        if hit is None:
            unplaced.append(raw)
        elif hit not in found:
            found.append(hit)
    return found, unplaced


def venues_near(doc, areas, band_km=None):
    band = float(band_km if band_km is not None else (doc.get("check_band_km") or 8))
    rows = []
    for v in doc.get("venues") or []:
        if v.get("lat") is None or v.get("lng") is None:
            continue
        best = None
        for a in areas:
            if a.get("lat") is None:
                continue
            km = haversine_km(float(a["lat"]), float(a["lng"]), float(v["lat"]), float(v["lng"]))
            if best is None or km < best[0]:
                best = (km, a)
        if best is None:
            continue
        km, area = best
        row = dict(v)
        row["km_from_nearest_area"] = round(km, 2)
        row["nearest_area"] = area.get("district")
        row["near"] = km <= band
        rows.append(row)
    rows.sort(key=lambda r: r["km_from_nearest_area"])
    return [r for r in rows if r["near"]], [r for r in rows if not r["near"]], band


PASTE_PATTERNS = [
    re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"),
    re.compile(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*"
               r"(\d{4})?\b", re.I),
    re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})"
               r"(?:\s*,)?\s*(\d{4})?\b", re.I),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
]
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def scan_paste(text, start, end):
    """A pasted venue calendar page -> the dates on it that fall inside the window.

    No scraping and no cleverness: it reads dates out of text a human copied, and
    reports the line each one was on so the reader can see what it was next to.
    """
    hits, seen = [], set()
    for lineno, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        for pattern in PASTE_PATTERNS:
            for m in pattern.finditer(line):
                d = _paste_date(m, start, end)
                if d is None or not (start <= d <= end):
                    continue
                key = (d.isoformat(), lineno)
                if key in seen:
                    continue
                seen.add(key)
                hits.append({"date": d.isoformat(), "weekday": d.strftime("%A"),
                             "line_number": lineno, "line": line.strip()[:160]})
    hits.sort(key=lambda h: (h["date"], h["line_number"]))
    return hits


def _paste_date(match, start, end):
    groups = match.groups()
    try:
        if len(groups) == 3 and groups[0] and groups[0].isdigit() and len(groups[0]) == 4:
            return dt.date(int(groups[0]), int(groups[1]), int(groups[2]))
        if groups[0] and groups[0].isdigit() and groups[1] and not groups[1].isdigit():
            year = int(groups[2]) if groups[2] else start.year
            d = dt.date(year, MONTHS[groups[1][:3].lower()], int(groups[0]))
            return d if start <= d <= end else _reyear(d, start, end)
        if groups[0] and not groups[0].isdigit():
            year = int(groups[2]) if groups[2] else start.year
            d = dt.date(year, MONTHS[groups[0][:3].lower()], int(groups[1]))
            return d if start <= d <= end else _reyear(d, start, end)
        return dt.date(int(groups[2]), int(groups[1]), int(groups[0]))
    except (ValueError, KeyError, TypeError):
        return None


def _reyear(d, start, end):
    for year in (start.year, end.year):
        try:
            candidate = d.replace(year=year)
        except ValueError:
            continue
        if start <= candidate <= end:
            return candidate
    return d


def events(start, end, near=None, paste=None, path=None, band_km=None):
    doc = load_events(path)
    rows = []
    for spike in doc.get("spikes") or []:
        windows = spike_windows(spike, start, end)
        if not windows:
            continue
        row = {k: spike.get(k) for k in ("id", "name", "kind", "window_text", "moveable",
                                         "affects", "why", "check", "source", "note", "district")}
        row["windows"] = windows
        rows.append(row)
    areas, unplaced = resolve_areas(near or [], doc) if near else ([], list(near or []))
    if near:
        near_venues, far_venues, band = venues_near(doc, areas, band_km)
    else:
        near_venues, far_venues, band = (list(doc.get("venues") or []), [],
                                         float(band_km if band_km is not None
                                               else (doc.get("check_band_km") or 8)))
    out = {"command": "events",
           "query": {"from": start.isoformat(), "to": end.isoformat(),
                     "near": list(near or []), "band_km": band},
           "source": "references/london-events.yaml (curated; venue calendars are never scraped)",
           "source_url": "references/london-events.yaml",
           "as_of": doc.get("checked_on"),
           "ok": True, "note": "", "evidence_class": "S",
           "spikes": rows, "count": len(rows),
           "areas_resolved": [a.get("district") for a in areas],
           "areas_not_recognised": unplaced,
           "venues_to_check": [{"id": v.get("id"), "name": v.get("name"),
                                "district": v.get("district"),
                                "calendar": v.get("calendar"), "check": v.get("check"),
                                "km_from_nearest_area": v.get("km_from_nearest_area"),
                                "radius_note": v.get("radius_note"), "note": v.get("note")}
                               for v in near_venues],
           "venues_too_far": [{"id": v.get("id"), "name": v.get("name"),
                               "km_from_nearest_area": v.get("km_from_nearest_area")}
                              for v in far_venues],
           "magnitude_rule": (doc.get("rules") or {}).get("no_magnitude"),
           "price_radius_note": doc.get("price_radius_note"),
           "method": ("Recurring citywide occasions come from the curated file with a typical "
                      "window, not a promise about this year. Venues have no yearly cycle at all, "
                      "so the tool names the calendar and you open it. Every one of these is known "
                      "to push local prices up; how much is not measured here.")}
    if unplaced:
        out["note"] = ("I do not know where %s is, so I could not narrow the venue list for it. "
                       "Give me a postcode district instead." % ", ".join(str(u) for u in unplaced))
    if paste:
        if not os.path.exists(paste):
            die("no such file: %s" % paste, 2)
        with open(paste, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        out["paste"] = {"file": os.path.basename(paste),
                        "dates_in_window": scan_paste(text, start, end),
                        "method": ("Dates read out of a page you pasted. It is your copy of the "
                                   "venue's calendar; nothing was fetched and nothing was crawled.")}
        out["paste"]["count"] = len(out["paste"]["dates_in_window"])
    return out


# ------------------------------------------------------------------- plan ----
def run_calc_bridge(weeks, weekly, months, all_in):
    """The bridging total, computed by scripts/calc.py. Never re-implemented here."""
    args = [sys.executable, CALC, "bridge", "--weeks", repr(round(weeks, 2)),
            "--weekly", repr(float(weekly)), "--months", repr(round(months, 2)),
            "--all-in", repr(float(all_in))]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except Exception as exc:                                            # noqa: BLE001
        return {"ok": False, "note": _unknown("calc.py would not run (%s)" % str(exc)[:80])}
    if out.returncode != 0:
        return {"ok": False, "note": _unknown("calc.py exited %d: %s"
                                              % (out.returncode, out.stderr.strip()[:120]))}
    try:
        doc = json.loads(out.stdout)
    except ValueError:
        return {"ok": False, "note": _unknown("calc.py did not print JSON")}
    doc["ok"] = True
    doc["command_line"] = " ".join(["scripts/calc.py"] + args[2:])
    return doc


def _phase(week, total, sign_week):
    """What a given week of the bridge is for. A script, not a measurement."""
    if week == 1:
        return ("land", [
            "Sleep where you booked before you flew. Do not go looking for a bed today.",
            "Do the on-arrival half hour: photograph every room, run the hot tap, listen at the "
            "window at about 22:30, find the washing machine and the stopcock.",
            "Ask the bridge host, in writing, the latest date you can extend to.",
            "Book your first viewings. Do not pay anything for a long let this week."])
    if week < sign_week:
        return ("view", [
            "Viewings. Ask the fixed questions of every flat, in writing.",
            "Run the checks on the shortlist before you fall in love with one.",
            "Keep the refundable bridge booking; note its cancellation deadline in this calendar."])
    if week == sign_week:
        return ("sign", [
            "Offer and sign, if a flat has passed. Never sign on the viewing day.",
            "Signing is not moving in: from here the clock is referencing, the deposit going into "
            "a scheme, and the previous tenant's move-out.",
            "Ask the agent for the key-release date in writing, and ask whether a Saturday "
            "handover is possible if it falls on a Monday."])
    if week == sign_week + 1:
        return ("reference", [
            "Referencing and the money gate: income check or guarantor route, holding deposit, "
            "the deposit into a government-approved scheme.",
            "Extend the bridge to cover the whole gap now, before the rate moves.",
            "Put every verbal promise back into an email and ask for a written confirmation."])
    if week >= total:
        return ("keys", [
            "Keys, inventory and move. Photograph everything again on the way in.",
            "Move on a weekday if you can, and never during induction or teaching week.",
            "Close the bridge: final invoice, deposit returned, forwarding address."])
    return ("wait", [
        "Chase the two things that actually move the date: referencing and the previous tenant's "
        "move-out.",
        "Confirm the bridge covers the whole gap. Ask to extend rather than move twice.",
        "If the date slips, it slips in weeks. Re-price the bridge before you agree to it."])


def _week_rows(arrive, keys, total_weeks, sign_week):
    rows = []
    for w in range(1, total_weeks + 1):
        a = arrive + dt.timedelta(days=7 * (w - 1))
        b = min(keys, a + dt.timedelta(days=6))
        phase, todo = _phase(w, total_weeks, sign_week)
        if w <= 2:
            sleep = {"tier": FIRST_WEEKS_TIER, "why": FIRST_WEEKS_WHY,
                     "booked_before_you_fly": True}
        else:
            sleep = {"tier": LATER_TIER,
                     "why": ("by now you can view a private short let before paying. A licence is "
                             "not a tenancy: cap what you hand over at one week plus a small "
                             "deposit with anyone you have not verified"),
                     "booked_before_you_fly": False}
        rows.append({"week": w, "from": a.isoformat(), "to": b.isoformat(),
                     "phase": phase, "sleep": sleep, "do": todo, "overlaps": []})
    return rows


def _overlap_rows(row, hol, clos, term_rows, event_rows, near_venues, as_of):
    a = dt.date.fromisoformat(row["from"])
    b = dt.date.fromisoformat(row["to"])
    hits = []
    for h in hol.get("holidays") or []:
        d = dt.date.fromisoformat(h["date"])
        if a <= d <= b:
            hits.append({"kind": "bank_holiday",
                         "what": "%s, %s %s — offices, agents, referencing and deposit schemes "
                                 "are shut" % (h["title"], h["weekday"], h["date"]),
                         "source": BANK_HOLIDAYS_SOURCE, "as_of": _date_of(hol.get("retrieved_at"),
                                                                          as_of)})
    for c in clos.get("closures") or []:
        touching = [p for p in c["validity_periods"]
                    if dt.date.fromisoformat(p["from"]) <= b
                    and dt.date.fromisoformat(p["to"]) >= a]
        if not c["validity_periods"] or touching:
            hits.append({"kind": "closure",
                         "what": "%s (%s): %s" % (c["line_name"], c["severity_description"],
                                                  c["reason"] or "no reason given"),
                         "source": "TfL Unified API line status",
                         "as_of": _date_of(clos.get("retrieved_at"), as_of)})
    uni_hits = []
    for u in term_rows:
        for key, label in (("welcome_from", "welcome week"), ("teaching_starts", "teaching")):
            raw = u.get(key)
            if not raw:
                continue
            try:
                d = dt.date.fromisoformat(str(raw))
            except Exception:
                continue
            if a <= d <= b:
                uni_hits.append({"university": u.get("name"), "what": label, "date": str(raw),
                                 "estimated": bool(u.get("estimated")), "source": u.get("source"),
                                 "as_of": str(u.get("checked_on"))})
    if uni_hits:
        uni_hits.sort(key=lambda h: (h["date"], h["university"]))
        shown = "; ".join("%s %s %s%s" % (h["university"], h["what"], h["date"],
                                          " (estimated)" if h["estimated"] else "")
                          for h in uni_hits[:4])
        more = len(uni_hits) - 4
        hits.append({"kind": "structural",
                     "what": ("term start lands in this week — %s%s. This is the structural "
                              "squeeze: it tightens long lets and short lets together, across the "
                              "whole city, every September"
                              % (shown, ", and %d more in the file" % more if more > 0 else "")),
                     "source": "references/term-dates.yaml", "as_of": as_of,
                     "details": uni_hits})
    for e in event_rows:
        for w in e.get("windows") or []:
            if dt.date.fromisoformat(w["from"]) <= b and dt.date.fromisoformat(w["to"]) >= a:
                hits.append({"kind": e.get("kind"),
                             "what": "%s, %s to %s — %s" % (e.get("name"), w["from"], w["to"],
                                                            e.get("affects") or "London"),
                             "source": e.get("source") or "references/london-events.yaml",
                             "as_of": as_of})
    if near_venues:
        hits.append({"kind": "venue",
                     "what": ("check these dates against the venue calendars near your areas: %s. "
                              "Each is known to push local prices up; magnitude not measured here. "
                              "The links are at the foot of this plan"
                              % "; ".join(v["name"] for v in near_venues)),
                     "source": "references/london-events.yaml", "as_of": as_of,
                     "calendars": [v["calendar"] for v in near_venues]})
    return hits


def _date_of(stamp, fallback):
    if not stamp or stamp == "fixture":
        return fallback
    return str(stamp)[:10]


def plan(arrive, start, keys_by=None, gap_weeks=None, areas=None, budget_all_in=None,
         bridge_weekly=None, offline=False, fixtures=None, verbose=False, today=None,
         events_path=None, terms_path=None, lines=None):
    today = today or dt.date.today()
    as_of = today.isoformat()
    band_hint = ""
    if keys_by is not None:
        keys = keys_by
        gap_basis = "you gave me the key date"
    elif gap_weeks is not None:
        keys = arrive + dt.timedelta(days=int(round(gap_weeks * 7)))
        gap_basis = "you gave me a gap of %s weeks" % gap_weeks
    else:
        keys = arrive + dt.timedelta(days=DEFAULT_GAP_WEEKS[1] * 7)
        gap_basis = ("nobody told me when the keys come, so I planned the long end of the ordinary "
                     "band: four to seven weeks from landing to keys in term-start season "
                     "(%s). I plan to seven because being wrong on the long side costs bridge "
                     "weeks you can cancel, and being wrong on the short side leaves you with "
                     "nowhere to sleep" % AXIS_15)
        band_hint = "%d to %d weeks" % DEFAULT_GAP_WEEKS
    if keys <= arrive:
        die("--keys-by (%s) is on or before --arrive (%s); there is no bridge to plan"
            % (keys.isoformat(), arrive.isoformat()), 2)
    days = (keys - arrive).days
    bridge_weeks = days / 7.0
    total_weeks = max(1, int(math.ceil(days / 7.0)))
    sign_week = max(2, int(math.ceil(total_weeks * 0.4)))

    doc = load_events(events_path)
    area_names = [a.strip() for a in (areas or []) if str(a).strip()]
    resolved, unplaced = resolve_areas(area_names, doc)
    near_venues, far_venues, band = venues_near(doc, resolved, None) if resolved else ([], [], 8.0)
    modes = lines or sorted({m for a in resolved for m in (a.get("modes") or [])}) or list(RAIL_MODES)
    modes_why = ("the rail modes serving %s" % ", ".join(a["district"] for a in resolved)
                 if resolved and not lines else
                 "the modes you asked for" if lines else
                 "every rail mode, because I could not place your areas")

    hol = holidays(arrive, keys, offline=offline, fixtures=fixtures, verbose=verbose)
    clos = closures(arrive, keys, modes, offline=offline, fixtures=fixtures, verbose=verbose)
    ev = events(arrive, keys, near=area_names or None, paste=None, path=events_path)
    tm = terms(int(arrive.year), None, today=today, path=terms_path)
    term_rows = tm.get("universities") or []

    rows = _week_rows(arrive, keys, total_weeks, sign_week)
    venue_short = [{"name": v["name"], "calendar": v["calendar"]} for v in near_venues]
    for row in rows:
        row["overlaps"] = _overlap_rows(row, hol, clos, term_rows, ev.get("spikes") or [],
                                        venue_short, as_of)

    months = 12.0 - bridge_weeks * 12.0 / WEEKS_PER_YEAR
    if bridge_weekly is not None and budget_all_in is not None:
        bridging = run_calc_bridge(bridge_weeks, bridge_weekly, months, budget_all_in)
    else:
        bridging = {"ok": False,
                    "note": _unknown("I need --bridge-weekly (what the bridge costs per week) and "
                                     "--budget-all-in (the long let, rent plus every bill) before "
                                     "I can price the year")}
    out = {
        "command": "plan",
        "query": {"arrive": arrive.isoformat(), "start": start.isoformat(),
                  "keys_by": keys_by.isoformat() if keys_by else None,
                  "gap_weeks": gap_weeks, "areas": area_names,
                  "budget_all_in": budget_all_in, "bridge_weekly": bridge_weekly,
                  "offline": bool(offline)},
        "ok": bool(hol.get("ok") and clos.get("ok")),
        "note": "" if (hol.get("ok") and clos.get("ok")) else
                "; ".join(x for x in (hol.get("note"), clos.get("note")) if x),
        "as_of": as_of,
        "rules": [
            {"n": 1, "rule": "Book the bridge first",
             "says": ("somewhere to sleep for at least the first two weeks, booked before you fly: "
                      "a %s. A private short let only after you have seen it or verified it live."
                      % FIRST_WEEKS_TIER),
             "source": AXIS_15, "as_of": as_of},
            {"n": 2, "rule": "Signing is not moving in",
             "says": ("plan the bridge for the gap between the signature and the keys, in weeks. "
                      "%s." % REFERENCE_GAP_NOTE),
             "source": AXIS_15, "as_of": as_of},
        ],
        "gap": {"days": days, "weeks": round(bridge_weeks, 2), "keys_date": keys.isoformat(),
                "basis": gap_basis, "default_band_weeks": list(DEFAULT_GAP_WEEKS),
                "default_band_text": band_hint or "%d to %d weeks" % DEFAULT_GAP_WEEKS,
                "reference_case_days": REFERENCE_GAP_DAYS,
                "reference_case": REFERENCE_GAP_NOTE,
                "source": AXIS_15, "as_of": as_of},
        "assumptions": {
            "sign_week": sign_week,
            "sign_week_basis": ("a planning placeholder, not a measurement: viewings first, an "
                                "offer about two fifths of the way through the bridge, then "
                                "referencing. Move it the moment you have a real date."),
            "start_means": ("--start is the day you have to be functioning here: term start, or "
                            "your first day at work. It is a deadline, not a moving date."),
            "months_after_bridge": round(months, 2),
            "months_basis": "12 - bridge weeks x 12 / 52, the year-total rule in %s" % AXIS_15,
        },
        "weeks": rows,
        "bridging_total": bridging,
        "areas": {"asked": area_names, "resolved": [a.get("district") for a in resolved],
                  "not_recognised": unplaced, "band_km": band,
                  "source": "references/london-events.yaml", "as_of": doc.get("checked_on")},
        "venues_to_check": [{"name": v["name"], "district": v.get("district"),
                             "km_from_nearest_area": v.get("km_from_nearest_area"),
                             "calendar": v.get("calendar"), "check": v.get("check"),
                             "radius_note": v.get("radius_note")} for v in near_venues],
        "venues_too_far": [{"name": v["name"], "km_from_nearest_area": v["km_from_nearest_area"]}
                           for v in far_venues],
        "closures_query": {"modes": modes, "why": modes_why},
        "holidays": hol,
        "closures": clos,
        "events": ev,
        "terms": tm,
        "magnitude_rule": (doc.get("rules") or {}).get("no_magnitude"),
        "method": ("A week-by-week bridge from the day you land to the day the keys are actually "
                   "released. The bridge is booked before anything is vetted; the gap between "
                   "signing and keys is budgeted in weeks; the year is priced whole, because "
                   "during the bridge you are not paying the long-let rent."),
    }
    if start < keys:
        out["warnings"] = [("Your start deadline (%s) lands %d days before the keys (%s), so you "
                            "will still be in the bridge on the day it matters. Do not plan a move "
                            "that week."
                            % (start.isoformat(), (keys - start).days, keys.isoformat()))]
    else:
        out["warnings"] = []
    if unplaced:
        out["warnings"].append("I could not place: %s. I read the closure feed for every rail mode "
                               "instead, and I listed no venues for it. Give me a postcode district."
                               % ", ".join(str(u) for u in unplaced))
    for w in tm.get("warnings") or []:
        out["warnings"].append(w)
    return out


# ------------------------------------------------------------------ plain ----
def _stamp(source, as_of):
    return "[source: %s · as_of %s]" % (source or "unknown", as_of or "unknown")


def plain(doc):
    cmd = doc.get("command")
    if cmd == "holidays":
        return _plain_holidays(doc)
    if cmd == "closures":
        return _plain_closures(doc)
    if cmd == "terms":
        return _plain_terms(doc)
    if cmd == "events":
        return _plain_events(doc)
    return _plain_plan(doc)


def _plain_holidays(doc):
    q = doc["query"]
    as_of = _date_of(doc.get("retrieved_at"), dt.date.today().isoformat())
    out = ["Bank holidays, %s to %s (%s)" % (q["from"], q["to"], q["division"]), ""]
    if not doc.get("ok"):
        out.append("  " + doc.get("note", ""))
        return "\n".join(out)
    if not doc.get("holidays"):
        out.append("  None in this window. Nothing shuts the offices in your dates.")
    for i, h in enumerate(doc["holidays"], 1):
        out.append("%2d. %s (%s) — %s. Offices, agents and deposit schemes shut. %s"
                   % (i, h["date"], h["weekday"], h["title"], _stamp(doc["source"], as_of)))
    out += ["", doc.get("method", "")]
    return "\n".join(out)


def _plain_closures(doc):
    q = doc["query"]
    as_of = _date_of(doc.get("retrieved_at"), dt.date.today().isoformat())
    out = ["Planned closures and disruption, %s to %s, on %s"
           % (q["from"], q["to"], ", ".join(q["modes"])), ""]
    if not doc.get("ok"):
        out.append("  " + doc.get("note", ""))
        return "\n".join(out)
    if not doc.get("closures"):
        out.append("  Nothing but Good Service on those modes for those dates, as TfL has it today. "
                   "Planned work is added weeks ahead, so ask again nearer the day.")
    for i, c in enumerate(doc["closures"], 1):
        when = ("; ".join("%s to %s" % (p["from"], p["to"]) for p in c["validity_periods"])
                or "dates not given")
        out.append("%2d. %s — %s (%s). %s. %s %s"
                   % (i, c["line_name"], c["severity_description"], when,
                      c["reason"] or "no reason published",
                      "Planned work." if c["planned"] else "Not planned work.",
                      _stamp(doc["source"], as_of)))
    out += ["", doc.get("method", "")]
    return "\n".join(out)


def _plain_terms(doc):
    out = ["Term dates, %s — the structural squeeze" % doc.get("academic_year"), ""]
    for i, u in enumerate(doc.get("universities") or [], 1):
        welcome = ("welcome %s to %s" % (u.get("welcome_from"), u.get("welcome_to"))
                   if u.get("welcome_from") else "no welcome week published")
        out.append("%2d. %s: %s, teaching starts %s, autumn ends %s.%s %s"
                   % (i, u.get("name"), welcome, u.get("teaching_starts"), u.get("term_end"),
                      " ESTIMATED: %s" % u.get("estimate_note") if u.get("estimated") else "",
                      _stamp(u.get("source"), u.get("checked_on"))))
    for w in doc.get("warnings") or []:
        out.append("    ! " + w)
    out += ["", doc.get("method", "")]
    return "\n".join(out)


def _plain_events(doc):
    q = doc["query"]
    as_of = doc.get("as_of")
    out = ["London demand spikes, %s to %s" % (q["from"], q["to"]), ""]
    n = 0
    for s in doc.get("spikes") or []:
        n += 1
        when = "; ".join("%s to %s" % (w["from"], w["to"]) for w in s["windows"])
        out.append("%2d. [%s] %s — %s. Affects: %s.%s %s"
                   % (n, s.get("kind"), s.get("name"), when, s.get("affects"),
                      " Check: %s." % s.get("check") if s.get("check") else "",
                      _stamp(s.get("source") or doc["source"], as_of)))
    for v in doc.get("venues_to_check") or []:
        n += 1
        km = v.get("km_from_nearest_area")
        out.append("%2d. [venue] %s — %s. %s%s %s"
                   % (n, v.get("name"), v.get("check"),
                      "%s km from your nearest area. " % km if km is not None else "",
                      v.get("radius_note") or "", _stamp(v.get("calendar") or doc["source"], as_of)))
    if doc.get("paste"):
        for hit in doc["paste"]["dates_in_window"]:
            n += 1
            out.append("%2d. [pasted] %s (%s): %s %s"
                       % (n, hit["date"], hit["weekday"], hit["line"],
                          _stamp(doc["paste"]["file"], as_of)))
    if doc.get("note"):
        out.append("    ! " + doc["note"])
    out += ["", doc.get("magnitude_rule") or "", doc.get("method", "")]
    return "\n".join(out)


def _plain_plan(doc):
    q, gap = doc["query"], doc["gap"]
    as_of = doc["as_of"]
    out = ["The first weeks: land %s, be functioning by %s, keys about %s"
           % (q["arrive"], q["start"], gap["keys_date"]),
           "", "The two rules, before any listing:"]
    n = 0
    for r in doc["rules"]:
        n += 1
        out.append("%2d. %s — %s %s" % (n, r["rule"], r["says"], _stamp(r["source"], r["as_of"])))
    n += 1
    out.append("%2d. The gap: %d days, about %s weeks. %s. Ordinary band %s. %s"
               % (n, gap["days"], gap["weeks"], gap["basis"], gap["default_band_text"],
                  _stamp(gap["source"], gap["as_of"])))
    out.append("")
    out.append("Week by week:")
    for row in doc["weeks"]:
        n += 1
        out.append("%2d. Week %d, %s to %s — sleep: %s. %s"
                   % (n, row["week"], row["from"], row["to"], row["sleep"]["tier"],
                      _stamp(doc["rules"][0]["source"], as_of)))
        for job in row["do"]:
            out.append("      - %s" % job)
        for hit in row["overlaps"]:
            out.append("      ! [%s] %s %s" % (hit["kind"], hit["what"],
                                               _stamp(hit["source"], hit["as_of"])))
    out.append("")
    b = doc["bridging_total"]
    n += 1
    if b.get("ok"):
        r = b["result"]
        out.append("%2d. Twelve-month total %s pounds = bridge %s (the weeks before the keys) plus "
                   "tenancy %s (the rest of the year). The bridge is not an extra cost: while you "
                   "are in it you are not paying the long-let rent. %s"
                   % (n, r["total"], r["bridge_cost"], r["tenancy_cost"],
                      _stamp("scripts/calc.py bridge", as_of)))
        out.append("      formula: %s" % b["formula"])
    else:
        out.append("%2d. Twelve-month total: %s %s"
                   % (n, b.get("note"), _stamp("scripts/calc.py bridge", as_of)))
    if doc.get("venues_to_check"):
        n += 1
        out.append("%2d. Venue calendars to open for these dates: %s. Each is known to push local "
                   "prices up; magnitude not measured here. %s"
                   % (n, "; ".join("%s %s" % (v["name"], v["calendar"])
                                   for v in doc["venues_to_check"]),
                      _stamp(doc["areas"]["source"], doc["areas"]["as_of"])))
    for w in doc.get("warnings") or []:
        out.append("    ! " + w)
    out += ["", doc.get("method", "")]
    return "\n".join(out)


# -------------------------------------------------------------------- cli ----
def _csv(value):
    return [p.strip() for p in str(value or "").split(",") if p.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plain", action="store_true", help="the table a person reads")
    ap.add_argument("--offline", action="store_true", help="read tests/fixtures/landing, fetch nothing")
    ap.add_argument("--fixtures", help="where the offline fixtures live")
    ap.add_argument("--today", help="pin today, for reproducible output")
    ap.add_argument("--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("holidays")
    p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True)
    p.add_argument("--division", default="england-and-wales")

    p = sub.add_parser("closures")
    p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True)
    p.add_argument("--lines", help="modes: tube,dlr,overground,elizabeth-line,national-rail")

    p = sub.add_parser("terms")
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--uni", help="comma separated ids, e.g. kcl,ucl")

    p = sub.add_parser("events")
    p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True)
    p.add_argument("--near", help="area names or postcode districts, comma separated")
    p.add_argument("--paste", help="a pasted venue calendar page to scan for dates")

    p = sub.add_parser("plan")
    p.add_argument("--arrive", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--keys-by", dest="keys_by")
    p.add_argument("--gap-weeks", dest="gap_weeks", type=float)
    p.add_argument("--areas")
    p.add_argument("--budget-all-in", dest="budget_all_in", type=float)
    p.add_argument("--bridge-weekly", dest="bridge_weekly", type=float)
    p.add_argument("--lines")

    a = ap.parse_args(argv)
    today = today_date(a.today)
    fixtures = a.fixtures or FIXTURES
    if a.cmd == "holidays":
        doc = holidays(as_date(a.start, "--from"), as_date(a.end, "--to"), a.division,
                       offline=a.offline, fixtures=fixtures, verbose=a.verbose)
    elif a.cmd == "closures":
        doc = closures(as_date(a.start, "--from"), as_date(a.end, "--to"),
                       _csv(a.lines) or None, offline=a.offline, fixtures=fixtures,
                       verbose=a.verbose)
    elif a.cmd == "terms":
        doc = terms(a.year, _csv(a.uni) or None, today=today)
    elif a.cmd == "events":
        doc = events(as_date(a.start, "--from"), as_date(a.end, "--to"),
                     near=_csv(a.near) or None, paste=a.paste)
    else:
        if a.keys_by and a.gap_weeks is not None:
            die("give me --keys-by or --gap-weeks, not both", 2)
        doc = plan(as_date(a.arrive, "--arrive"), as_date(a.start, "--start"),
                   as_date(a.keys_by, "--keys-by") if a.keys_by else None,
                   a.gap_weeks, _csv(a.areas) or None, a.budget_all_in, a.bridge_weekly,
                   offline=a.offline, fixtures=fixtures, verbose=a.verbose, today=today,
                   lines=_csv(a.lines) or None)
    if a.plain:
        print(plain(doc))
    else:
        json.dump(doc, sys.stdout, ensure_ascii=False, indent=1)
        print()
    return 0 if doc.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
