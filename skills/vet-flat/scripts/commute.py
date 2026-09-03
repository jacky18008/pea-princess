#!/usr/bin/env python3
"""TfL Unified API — official Transport for London journey planner and stop finder.

Source: https://api.tfl.gov.uk. No key is needed at this volume: the anonymous
call succeeds outright (verified 2026-09-03). A free `app_key` only raises the
quota for sustained use. If you have one, put it in a plain `.env` file next to
this script as `TFL_APP_KEY=...` (this script parses KEY=VALUE lines itself, no
third-party package); an environment variable of the same name wins over the
file. robots.txt is a 404 JSON error, so nothing is disallowed; the fetch helper
still spaces requests ~1.2 s apart. Evidence class "G" (official operator).

What the numbers are and are not:
  * A journey time is a PLAN off the timetable, not a measured trip. It assumes
    every connection is made. Compare plans with each other, not with a stopwatch.
  * TfL chains legs back to back, so a plan often shows a leg departing at the
    exact minute the previous one arrives. That is a zero-wait sample: the plan
    has spent none of your budget waiting. `wait_sample_note` flags it.
  * Walking distance to a station is estimated as straight line x 1.3. It is an
    estimate of street distance, not a routed walk; rivers, railways and estates
    all break it.
  * Nothing personal is built in. `--to` is required.

Usage:
  commute.py journey --from "SE1 9SG" --to "WC2R 2LS" [--arrive 09:00]
                     [--date next-weekday|YYYYMMDD] [--door-buffer-min 0]
                     [--plans all,rail,bus]
  commute.py journey --from "51.5049,-0.0876" --to "51.5119,-0.1166"
  commute.py stations --lat 51.504963 --lng -0.087625 [--radius 800]
  commute.py redundancy --lat 51.504963 --lng -0.087625 [--radius 2000]
Add --verbose to see the curl commands on stderr. One JSON object on stdout.
Exit 0 on success, 2 on usage error, 1 on fetch failure.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402
from geo import haversine_m  # noqa: E402

BASE = "https://api.tfl.gov.uk"
PLANS = {
    "all": None,  # let TfL pick from every mode, including bus
    "rail": "tube,dlr,overground,elizabeth-line,national-rail,walking",
    "bus": "bus,walking",
}
STOP_TYPES = "NaptanMetroStation,NaptanRailStation,NaptanFerryPort"
BUS_STOP_TYPES = "NaptanPublicBusCoachTram"
RAIL_MODES = ("tube", "dlr", "overground", "elizabeth-line", "national-rail", "river-bus")
FAMILIES = {
    "family_A": ["tube", "dlr"],
    "family_B": ["national-rail", "overground", "elizabeth-line"],
    "family_C": ["river-bus"],
}
FAMILY_WHY = ("Two lines of the same family do not count as redundancy; they tend to strike "
              "together, and they share the same tunnels, the same control room and the same "
              "flood.")
WALK_FACTOR = 1.3          # straight line -> street distance, a rule of thumb
WALK_M_PER_MIN = 80.0      # about 4.8 km/h
COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$")


# ------------------------------------------------------------- env / key ----
def load_env(path=None):
    """Parse a plain KEY=VALUE .env next to this script. No package, no export."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    out = {}
    if not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                if k.lower().startswith("export "):
                    k = k[7:].strip()
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                if k:
                    out[k] = v
    except Exception:
        return out
    return out


def app_key():
    return os.environ.get("TFL_APP_KEY") or load_env().get("TFL_APP_KEY") or None


def _with_key(url):
    k = app_key()
    if not k:
        return url
    return url + ("&" if "?" in url else "?") + "app_key=" + k


def _redact(url):
    return re.sub(r"app_key=[^&]+", "app_key=REDACTED", url)


# --------------------------------------------------------------- places -----
def parse_place(text):
    """'lat,lng' or a postcode or free text -> (api_value, kind, label)."""
    if text is None or not str(text).strip():
        raise ValueError("empty place")
    s = str(text).strip()
    m = COORD_RE.match(s)
    if m:
        lat, lng = float(m.group(1)), float(m.group(2))
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError("coordinates out of range: %r" % s)
        return "%s,%s" % (repr(lat), repr(lng)), "coords", "%s,%s" % (lat, lng)
    squashed = "".join(s.split()).upper()
    if POSTCODE_RE.match(squashed) or POSTCODE_RE.match(squashed[:-3] + " " + squashed[-3:]):
        pc = squashed[:-3] + " " + squashed[-3:]
        return pc.replace(" ", "%20"), "postcode", pc
    return s.replace(" ", "%20"), "text", s


def next_weekday(today=None):
    d = today or datetime.date.today()
    d += datetime.timedelta(days=1)
    while d.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        d += datetime.timedelta(days=1)
    return d


def resolve_date(spec):
    if not spec or spec == "next-weekday":
        return next_weekday().strftime("%Y%m%d"), "next-weekday"
    s = "".join(str(spec).split()).replace("-", "")
    if not re.match(r"^\d{8}$", s):
        raise ValueError("--date must be 'next-weekday' or YYYYMMDD, got %r" % spec)
    datetime.datetime.strptime(s, "%Y%m%d")  # raises ValueError if not a real date
    return s, "explicit"


def resolve_time(spec):
    m = re.match(r"^(\d{1,2}):?(\d{2})$", "".join(str(spec or "09:00").split()))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ValueError("--arrive must look like HH:MM, got %r" % spec)
    return "%02d%02d" % (int(m.group(1)), int(m.group(2)))


# ------------------------------------------------------------- journeys -----
def _leg_line(leg):
    for o in (leg.get("routeOptions") or []):
        name = o.get("name") or ((o.get("lineIdentifier") or {}) or {}).get("name")
        if name:
            return name
    return None


def _point_name(leg, key):
    p = leg.get(key) or {}
    return p.get("commonName") or p.get("name") or None


def parse_journey(journey, door_buffer_min=0):
    """One TfL journey -> the fields this skill actually uses."""
    legs, zero_wait, wait_total = [], 0, 0
    prev_arr = None
    for leg in journey.get("legs") or []:
        mode = ((leg.get("mode") or {}).get("id")) or "unknown"
        dep, arr = leg.get("departureTime"), leg.get("arrivalTime")
        if prev_arr and dep:
            if dep == prev_arr:
                zero_wait += 1
            else:
                try:
                    a = datetime.datetime.strptime(prev_arr[:16], "%Y-%m-%dT%H:%M")
                    b = datetime.datetime.strptime(dep[:16], "%Y-%m-%dT%H:%M")
                    wait_total += max(0, int((b - a).total_seconds() // 60))
                except ValueError:
                    pass
        prev_arr = arr or prev_arr
        legs.append({
            "mode": mode,
            "line": _leg_line(leg) or None,
            "from": _point_name(leg, "departurePoint"),
            "to": _point_name(leg, "arrivalPoint"),
            "duration_min": leg.get("duration"),
            "departure": dep,
            "arrival": arr,
            "summary": ((leg.get("instruction") or {}).get("summary")),
        })
    transit = [l for l in legs if l["mode"] != "walking"]
    walking = [l for l in legs if l["mode"] == "walking"]
    raw = journey.get("duration")
    out = {
        "duration_min": (raw + door_buffer_min) if raw is not None else None,
        "duration_min_before_buffer": raw,
        "door_buffer_min": door_buffer_min,
        "start": journey.get("startDateTime"),
        "arrival": journey.get("arrivalDateTime"),
        "legs": legs,
        "changes": max(0, len(transit) - 1),
        "transit_legs": len(transit),
        "walking_min": sum(l["duration_min"] or 0 for l in walking),
        "first_leg_walk_min": (legs[0]["duration_min"] or 0)
                              if legs and legs[0]["mode"] == "walking" else 0,
        "last_leg_walk_min": (legs[-1]["duration_min"] or 0)
                             if legs and legs[-1]["mode"] == "walking" else 0,
        "waiting_min_in_plan": wait_total,
        "zero_wait_joins": zero_wait,
        "modes": sorted({l["mode"] for l in transit}),
        "lines": [l["line"] for l in transit if l["line"]],
    }
    out["wait_sample_note"] = (
        ("%d of the %d connections in this plan depart at the exact minute the previous leg "
         "arrives. That is a zero-wait sample: the plan has budgeted nothing for waiting, so "
         "the real trip is this number plus however long the next service takes to turn up."
         % (zero_wait, max(0, len(legs) - 1))) if zero_wait else None)
    return out


def _journey_url(frm, to, date, time, mode):
    url = ("%s/Journey/JourneyResults/%s/to/%s?date=%s&time=%s&timeIs=Arriving"
           % (BASE, frm, to, date, time))
    if mode:
        url += "&mode=" + mode
    return url


def _disambiguation(obj):
    out = {}
    for key in ("fromLocationDisambiguation", "toLocationDisambiguation",
                "viaLocationDisambiguation"):
        block = obj.get(key) or {}
        opts = block.get("disambiguationOptions") or []
        if opts:
            out[key] = [{"name": (o.get("place") or {}).get("commonName"),
                         "parameter": o.get("parameterValue")} for o in opts[:8]]
    return out or None


def parse_journey_response(obj, door_buffer_min=0):
    """A whole JourneyResults body -> the fastest journey plus alternatives.

    Pure: no network. Returns a dict that always carries `ok`; on failure it
    carries `note` and, for an HTTP 300 body, `disambiguation`.
    """
    if not isinstance(obj, dict):
        return {"ok": False, "note": "expected a JSON object"}
    if "Disambiguation" in (obj.get("$type") or ""):
        return {"ok": False,
                "note": ("TfL could not pin down one of the endpoints; pass a postcode or "
                         "lat,lng instead of a place name"),
                "disambiguation": _disambiguation(obj)}
    journeys = obj.get("journeys") or []
    if not journeys:
        return {"ok": False, "note": obj.get("message") or "no journeys returned"}
    parsed = [parse_journey(j, door_buffer_min) for j in journeys]
    parsed.sort(key=lambda p: (p["duration_min"] is None, p["duration_min"]))
    best = dict(parsed[0])
    best["ok"] = True
    best["alternatives_min"] = [p["duration_min"] for p in parsed]
    best["journeys_returned"] = len(parsed)
    return best


def plan(frm, to, date, time, mode, door_buffer_min=0, verbose=False):
    url = _journey_url(frm, to, date, time, mode)
    res = fetch(_with_key(url), cache_ttl=6 * 3600, verbose=verbose,
                expect=lambda b: '"journeys"' in b or "Disambiguation" in b or '"message"' in b)
    out = {"source_url": _redact(url), "http_status": res["status"], "ok": bool(res["ok"]),
           "note": res["note"], "retrieved_at": res["retrieved_at"], "evidence_class": "G",
           "mode_filter": mode or "(TfL default: every mode)"}
    try:
        obj = json.loads(res["body"]) if res["body"] else {}
    except Exception as exc:
        out["ok"] = False
        out["note"] = "response was not JSON: %s" % str(exc)[:120]
        return out
    parsed = parse_journey_response(obj, door_buffer_min)
    if not parsed.get("ok"):
        out["ok"] = False
        out["note"] = (out["note"] + "; " if out["note"] else "") + (parsed.get("note") or "")
        if parsed.get("disambiguation"):
            out["disambiguation"] = parsed["disambiguation"]
        else:
            out["not_found"] = {"query": _redact(url)}
        return out
    parsed.pop("ok", None)
    out.update(parsed)
    return out


def journey(frm, to, arrive="09:00", date=None, door_buffer_min=0, plans=None, verbose=False):
    if not to:
        raise ValueError("--to is required; this skill hard-codes no destination")
    f_api, f_kind, f_label = parse_place(frm)
    t_api, t_kind, t_label = parse_place(to)
    d, d_kind = resolve_date(date)
    t = resolve_time(arrive)
    wanted = [p.strip() for p in (plans or list(PLANS)) if p.strip()]
    for p in wanted:
        if p not in PLANS:
            raise ValueError("unknown plan %r; choose from %s" % (p, ", ".join(PLANS)))
    results = {}
    for name in wanted:
        results[name] = plan(f_api, t_api, d, t, PLANS[name], door_buffer_min, verbose=verbose)
    ok_plans = {k: v for k, v in results.items() if v.get("ok")}
    fastest = min(ok_plans.items(), key=lambda kv: kv[1]["duration_min"])[0] if ok_plans else None
    out = {
        "query": {"from": f_label, "from_kind": f_kind, "to": t_label, "to_kind": t_kind,
                  "arrive_by": "%s:%s" % (t[:2], t[2:]), "date": d, "date_source": d_kind,
                  "door_buffer_min": door_buffer_min, "plans": wanted},
        "source_url": results[wanted[0]]["source_url"] if wanted else None,
        "http_status": results[wanted[0]]["http_status"] if wanted else None,
        "ok": bool(ok_plans),
        "note": "" if len(ok_plans) == len(wanted) else "%d of %d plans failed"
                % (len(wanted) - len(ok_plans), len(wanted)),
        "retrieved_at": now_iso(),
        "evidence_class": "G",
        "app_key_used": bool(app_key()),
        "plans": results,
        "fastest_plan": fastest,
        "fastest_min": ok_plans[fastest]["duration_min"] if fastest else None,
        "rail_only_min": (results.get("rail") or {}).get("duration_min"),
        "bus_only_min": (results.get("bus") or {}).get("duration_min"),
        "method": (
            "TfL Journey Planner, arriving by %s:%s on %s (%s). Three plans: 'all' lets TfL "
            "choose any mode, 'rail' restricts to tube, DLR, Overground, Elizabeth line, "
            "national rail and walking, 'bus' to bus and walking. The bus number is the "
            "answer to 'what happens when the trains stop', so read it as the fallback, not "
            "as the commute. `door_buffer_min` is %d and is added only because you asked; "
            "TfL plans to the street, not through the front door of a building."
            % (t[:2], t[2:], d, d_kind, door_buffer_min)),
    }
    return out


# -------------------------------------------------------------- stations ----
def _stop_url(lat, lng, radius, stop_types):
    return ("%s/StopPoint?lat=%s&lon=%s&stopTypes=%s&radius=%d&returnLines=true"
            % (BASE, repr(float(lat)), repr(float(lng)), stop_types, int(radius)))


def _walk(straight_m):
    walk_m = straight_m * WALK_FACTOR
    return round(walk_m), round(walk_m / WALK_M_PER_MIN, 1)


def parse_stoppoints(obj, lat, lng, keep_modes=RAIL_MODES):
    """A StopPoint search body -> (stations, dropped). Pure: no network.

    `distance` from the API is used when present, otherwise haversine from the
    query point. Stops whose modes are all outside `keep_modes` are dropped, with
    a reason: the API files some bus-only piers under station stop types.
    """
    raw = obj.get("stopPoints") if isinstance(obj, dict) else (obj if isinstance(obj, list) else [])
    items, dropped = [], []
    for s in raw or []:
        modes = list(s.get("modes") or [])
        if keep_modes is not None and not any(m in keep_modes for m in modes):
            dropped.append({"name": s.get("commonName"), "modes": modes,
                            "stop_type": s.get("stopType")})
            continue
        slat, slng = s.get("lat"), s.get("lon")
        hav = haversine_m(lat, lng, slat, slng) if slat is not None else None
        straight = s.get("distance")
        source = "tfl"
        if straight is None:
            straight, source = hav, "haversine"
        walk_m, walk_min = _walk(straight) if straight is not None else (None, None)
        items.append({
            "name": s.get("commonName"),
            "naptan_id": s.get("naptanId") or s.get("id"),
            "stop_type": s.get("stopType"),
            "modes": sorted(modes),
            "lines": sorted({(l.get("name") or "") for l in (s.get("lines") or []) if l.get("name")}),
            "lat": slat, "lng": slng,
            "straight_line_m": round(straight) if straight is not None else None,
            "straight_line_source": source,
            "haversine_m": round(hav) if hav is not None else None,
            "walk_m_estimate": walk_m,
            "walk_min_estimate": walk_min,
        })
    items.sort(key=lambda x: (x["straight_line_m"] is None, x["straight_line_m"]))
    return items, dropped


def stations(lat, lng, radius=800, stop_types=STOP_TYPES, keep_modes=RAIL_MODES,
             verbose=False):
    url = _stop_url(lat, lng, radius, stop_types)
    res = fetch(_with_key(url), cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: '"stopPoints"' in b or '"$type"' in b)
    out = {"query": {"lat": lat, "lng": lng, "radius_m": radius, "stop_types": stop_types},
           "source_url": _redact(url), "http_status": res["status"], "ok": bool(res["ok"]),
           "note": res["note"], "retrieved_at": res["retrieved_at"], "evidence_class": "G"}
    try:
        obj = json.loads(res["body"]) if res["body"] else {}
    except Exception as exc:
        out["ok"] = False
        out["note"] = "response was not JSON: %s" % str(exc)[:120]
        out["count"], out["stations"] = 0, []
        return out
    items, dropped = parse_stoppoints(obj, lat, lng, keep_modes)
    out["count"] = len(items)
    out["stations"] = items
    out["dropped_wrong_mode"] = dropped
    if not items:
        out["not_found"] = {"query": _redact(url)}
    out["method"] = (
        "TfL StopPoint search within %d m straight line of the point, stop types %s, then "
        "anything whose modes are not one of %s is dropped (the API files some bus-only piers "
        "and interchanges under station stop types). `straight_line_m` is TfL's own `distance` "
        "field where it exists; it runs a little longer than the great-circle line between the "
        "two coordinates TfL itself reports (it measures from the station hub, not the stop "
        "point), so `haversine_m` is given alongside it. The walk estimate uses TfL's number, "
        "the longer of the two here. `walk_m_estimate` is that straight line times %.1f and "
        "`walk_min_estimate` divides it by %d m per minute — an ESTIMATE of street distance, "
        "not a routed walk. A river or a railway between you and the station breaks it badly, "
        "so check one route on a map before trusting a tight number."
        % (radius, stop_types, ", ".join(keep_modes or ["any"]), WALK_FACTOR, int(WALK_M_PER_MIN)))
    return out


# ------------------------------------------------------------ redundancy ----
def _family_of(modes):
    for fam, members in FAMILIES.items():
        if any(m in members for m in modes):
            return fam
    return None


def nearest_by_family(station_list):
    """The closest station of each strike family, keyed by family name."""
    fams = {}
    for s in station_list or []:
        if s.get("walk_m_estimate") is None:
            continue
        for fam, members in FAMILIES.items():
            if any(m in (s.get("modes") or []) for m in members):
                cur = fams.get(fam)
                if cur is None or s["walk_m_estimate"] < cur["walk_m_estimate"]:
                    fams[fam] = s
    return fams


def grade_redundancy(station_list, bus_stops_near=None, search_radius_m=2000):
    """Strike-family grade. Pure: no network.

    bus_stops_near: list of bus stops already found within an 800 m walk, or None
    if that lookup has not been done. When only one rail family is present and
    bus_stops_near is None, the result carries needs_bus_check=True so the caller
    knows one more lookup would sharpen C into B-.
    """
    fams = nearest_by_family(station_list)
    a, b, c = fams.get("family_A"), fams.get("family_B"), fams.get("family_C")
    rail = [(f, s) for f, s in (("family_A", a), ("family_B", b)) if s]
    rail.sort(key=lambda kv: kv[1]["walk_m_estimate"])
    d1 = rail[0][1]["walk_m_estimate"] if rail else None
    d2 = rail[1][1]["walk_m_estimate"] if len(rail) > 1 else None
    needs_bus_check = False

    if d1 is None:
        grade = "C"
        why = ("No tube, DLR, national rail, Overground or Elizabeth line station found within "
               "a %d m straight line. On this data the address has no rail family at all."
               % search_radius_m)
    elif d2 is None:
        near_bus = list(bus_stops_near or [])
        needs_bus_check = bus_stops_near is None
        if near_bus and d1 <= 800:
            grade = "B-"
            why = ("Only one rail family is reachable (%s, about %d m on foot). The second "
                   "option is bus only — %d bus stop(s) within an 800 m walk — and a bus is not "
                   "redundancy against a rail strike, it is what everyone else also falls back on."
                   % (rail[0][0], d1, len(near_bus)))
        elif d1 <= 800:
            grade = "C"
            why = ("Only one rail family is reachable (%s, about %d m on foot)%s."
                   % (rail[0][0], d1,
                      "" if needs_bus_check else " and no bus stop sits within an 800 m walk either"))
        else:
            grade = "C"
            why = ("Only one rail family was found and it is not even within an 800 m walk (%s, "
                   "about %d m)." % (rail[0][0], d1))
    elif d1 <= 800 and d2 <= 800:
        grade = "A"
        why = ("Both families are within an 800 m walk (%s about %d m, %s about %d m), so a "
               "strike on one leaves the other standing."
               % (rail[0][0], d1, rail[1][0], d2))
    elif d1 <= 800 and d2 <= 1600:
        grade = "B"
        why = ("The nearer family is within an 800 m walk (%s about %d m) and the second is a "
               "longer but usable walk (%s about %d m)." % (rail[0][0], d1, rail[1][0], d2))
    elif d1 <= 800:
        grade = "B-"
        why = ("One family is close (%s about %d m) but the second is over 1600 m away (%s "
               "about %d m), which is a 20 minute walk in the rain on the day you need it."
               % (rail[0][0], d1, rail[1][0], d2))
    else:
        grade = "C"
        why = ("No rail family is within an 800 m walk; the nearest is %s at about %d m."
               % (rail[0][0], d1))

    return {
        "grade": grade,
        "reason": why,
        "needs_bus_check": needs_bus_check,
        "explanation": FAMILY_WHY,
        "families": {
            "family_A": _fam_out(a, FAMILIES["family_A"]),
            "family_B": _fam_out(b, FAMILIES["family_B"]),
            "family_C": _fam_out(c, FAMILIES["family_C"]),
        },
        "nearest_family": rail[0][0] if rail else None,
        "nearest_family_walk_m": d1,
        "second_family_walk_m": d2,
    }


def redundancy(lat, lng, radius=2000, verbose=False):
    st = stations(lat, lng, radius=radius, verbose=verbose)
    graded = grade_redundancy(st.get("stations") or [], None, radius)
    bus = None
    if graded["needs_bus_check"]:
        bus = stations(lat, lng, radius=800, stop_types=BUS_STOP_TYPES,
                       keep_modes=("bus", "tram", "coach"), verbose=verbose)
        near_bus = [s for s in (bus.get("stations") or [])
                    if (s["walk_m_estimate"] or 9e9) <= 800]
        graded = grade_redundancy(st.get("stations") or [], near_bus, radius)
    out = {
        "query": {"lat": lat, "lng": lng, "search_radius_m": radius},
        "source_url": st["source_url"], "http_status": st["http_status"],
        "ok": bool(st["ok"]), "note": st["note"], "retrieved_at": now_iso(),
        "evidence_class": "G",
    }
    out.update(graded)
    out.pop("needs_bus_check", None)
    out["bus_fallback"] = ({"stops_within_800m_walk": len([s for s in (bus.get("stations") or [])
                                                           if (s["walk_m_estimate"] or 9e9) <= 800]),
                            "source_url": bus.get("source_url")} if bus else None)
    out["stations_considered"] = [{"name": s["name"], "modes": s["modes"],
                                   "family": _family_of(s["modes"]),
                                   "walk_m_estimate": s["walk_m_estimate"],
                                   "walk_min_estimate": s["walk_min_estimate"]}
                                  for s in (st.get("stations") or [])]
    out["method"] = (
        "Stations within %d m straight line, each put in a strike family: family_A is tube and "
        "DLR, family_B is national rail, Overground and the Elizabeth line, family_C is the "
        "river bus (a pleasant backup, not a commute). Grades: A = both A and B within an 800 m "
        "walk; B = both, second one 800-1600 m; B- = one within 800 m and the other beyond "
        "1600 m or bus only; C = one family only. Distances are the straight line times %.1f, "
        "an estimate, so treat a number near a threshold as a tie."
        % (radius, WALK_FACTOR))
    return out


def _fam_out(station, members):
    if not station:
        return {"members": members, "nearest": None, "walk_m_estimate": None}
    return {"members": members, "nearest": station["name"], "modes": station["modes"],
            "lines": station["lines"], "straight_line_m": station["straight_line_m"],
            "walk_m_estimate": station["walk_m_estimate"],
            "walk_min_estimate": station["walk_min_estimate"]}


# ------------------------------------------------------------------ cli -----
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("journey", help="door-to-door plans, three mode sets")
    p.add_argument("--from", dest="frm", required=True, help='postcode or "lat,lng"')
    p.add_argument("--to", required=True, help='postcode or "lat,lng" — required, never assumed')
    p.add_argument("--arrive", default="09:00", help="arrive-by time HH:MM (default 09:00)")
    p.add_argument("--date", default="next-weekday", help="next-weekday or YYYYMMDD")
    p.add_argument("--door-buffer-min", type=int, default=0, dest="door_buffer_min",
                   help="minutes added for the building entrance; default 0, applied only if set")
    p.add_argument("--plans", default="all,rail,bus", help="comma list of all,rail,bus")

    p = sub.add_parser("stations", help="rail and river stations near a point")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=800)

    p = sub.add_parser("redundancy", help="strike-family grade for a point")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=2000)

    a = ap.parse_args()
    try:
        if a.cmd == "journey":
            out = journey(a.frm, a.to, a.arrive, a.date, a.door_buffer_min,
                          a.plans.split(","), verbose=a.verbose)
        elif a.cmd == "stations":
            out = stations(a.lat, a.lng, a.radius, verbose=a.verbose)
        else:
            out = redundancy(a.lat, a.lng, a.radius, verbose=a.verbose)
    except ValueError as exc:
        print("usage error: %s" % exc, file=sys.stderr)
        return 2
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
