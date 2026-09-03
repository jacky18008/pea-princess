#!/usr/bin/env python3
"""data.police.uk — official Home Office street-level crime API. No key, no fee.

Source: https://data.police.uk/api/ (Home Office / police.uk open data, Open
Government Licence). robots.txt is served with content-length 0, i.e. an empty
file: nothing is disallowed for anyone. The fetch helper still spaces requests
~1.2 s apart. Evidence class "G" (official register).

Four things to know before you read any number this prints:
  * Locations are ANONYMISED. Every record is snapped to a nearby map point and
    labelled "On or near <street>". The snap point can sit a couple of hundred
    metres from where the crime happened, and a single snap point can absorb a
    whole shopping centre or station. Anchors tell you where the police map puts
    things, not where they happened.
  * Publication lags 2-3 months. `latest` reports the newest DATA month, which is
    not today's date and not an event date.
  * Counts are raw. There is no population denominator, no footfall denominator
    and no night/day split, so a busy transport interchange out-counts a quiet
    residential street with more burglary per resident.
  * A month that fails to fetch is NEVER scaled or extrapolated. It is listed in
    `months_missing` and the totals cover `months_fetched` only.

Usage:
  crime.py latest
  crime.py box --lat 51.504963 --lng -0.087625 [--half-m 150] [--months 6] [--end 2026-06]
  crime.py box --lat 51.5 --lng -0.09 --route "51.5050,-0.0860;51.5041,-0.0885"
Add --verbose to see the curl commands on stderr. One JSON object on stdout.
Exit 0 on success, 2 on usage error, 1 on fetch failure.

Request budget: `box` makes months x 5 calls (default 6 x 5 = 30) for the centre
plus the four 20 m sensitivity shifts, plus `months` more if --route is given.
Past months never change, so the on-disk cache makes a re-run free.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402
from geo import bbox, haversine_m, M_PER_DEG_LAT  # noqa: E402

BASE = "https://data.police.uk/api"

# The 14 street-level categories the API publishes (crime-categories minus the
# synthetic "all-crime" bucket), checked against /api/crime-categories 2026-09-03.
CATEGORIES = [
    "anti-social-behaviour", "bicycle-theft", "burglary", "criminal-damage-arson",
    "drugs", "other-crime", "other-theft", "possession-of-weapons", "public-order",
    "robbery", "shoplifting", "theft-from-the-person", "vehicle-crime", "violent-crime",
]
PREDATORY = ["anti-social-behaviour", "violent-crime", "theft-from-the-person", "robbery"]
PREDATORY_WHY = (
    "These four are the ones a resident meets in person: being harassed, hit, pickpocketed "
    "or mugged. Separating them from the rest tells 'busy' apart from 'dangerous' — a place "
    "full of shoplifting and vehicle crime is commercial, not threatening to someone walking home."
)
SHIFT_M = 20.0


# ------------------------------------------------------------- helpers ------
def _month_of(date_str):
    return (date_str or "")[:7] or None


def month_window(end_month, n):
    """The n data months ending at end_month inclusive, oldest first."""
    if n < 1:
        raise ValueError("--months must be >= 1")
    y, m = int(end_month[:4]), int(end_month[5:7])
    out = []
    for k in range(n - 1, -1, -1):
        yy, mm = y, m - k
        while mm < 1:
            mm += 12
            yy -= 1
        out.append("%04d-%02d" % (yy, mm))
    return out


def _planar(lat0, lng0):
    """Local equirectangular projection: (lat,lng) -> metres east/north of origin."""
    kx = M_PER_DEG_LAT * math.cos(math.radians(lat0))
    return lambda la, ln: ((ln - lng0) * kx, (la - lat0) * M_PER_DEG_LAT)


def point_segment_m(px, py, ax, ay, bx, by):
    """Distance in metres from P to segment AB, all in planar metres."""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    denom = vx * vx + vy * vy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / denom))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def parse_route(text):
    """'lat,lng;lat,lng;...' -> [(lat,lng), ...]; needs at least two points."""
    pts = []
    for chunk in (text or "").replace("|", ";").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split(",")
        if len(parts) != 2:
            raise ValueError("route point %r is not 'lat,lng'" % chunk)
        pts.append((float(parts[0]), float(parts[1])))
    if len(pts) < 2:
        raise ValueError("--route needs at least two 'lat,lng' points separated by ';'")
    return pts


def _counts(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def _anchor(rec):
    loc = rec.get("location") or {}
    street = (loc.get("street") or {})
    return street.get("name") or "unknown"


def _latlng(rec):
    loc = rec.get("location") or {}
    try:
        return float(loc["latitude"]), float(loc["longitude"])
    except (KeyError, TypeError, ValueError):
        return None


# ------------------------------------------------------------- fetching -----
def latest(verbose=False):
    url = "%s/crime-last-updated" % BASE
    res = fetch(url, cache_ttl=86400, verbose=verbose, expect=lambda b: '"date"' in b)
    out = {"source_url": url, "http_status": res["status"], "ok": bool(res["ok"]),
           "note": res["note"], "retrieved_at": res["retrieved_at"], "evidence_class": "G",
           "latest_month": None, "raw_date": None}
    if res["ok"]:
        try:
            obj = json.loads(res["body"])
            out["raw_date"] = obj.get("date")
            out["latest_month"] = _month_of(obj.get("date"))
        except Exception as exc:
            out["ok"] = False
            out["note"] = "could not parse: %s" % str(exc)[:120]
    out["method"] = ("This is the newest month of DATA available, not an event date and not "
                     "today. police.uk publishes about 2-3 months behind, so the newest month "
                     "already describes a season that has passed.")
    return out


def fetch_month(poly, month, verbose=False):
    """One /crimes-street/all-crime call. Returns (records|None, url, res, reason)."""
    url = "%s/crimes-street/all-crime?poly=%s&date=%s" % (BASE, poly.replace(",", "%2C"), month)
    res = fetch(url, cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: b.startswith("[") or b.startswith("{"))
    if not res["ok"]:
        reason = res["note"] or "http %s" % res["status"]
        if res["status"] == 503:
            reason += " (the API returns 503 when a polygon holds more than 10000 crimes)"
        return None, url, res, reason
    try:
        obj = json.loads(res["body"])
    except Exception as exc:
        return None, url, res, "response was not JSON: %s" % str(exc)[:100]
    if not isinstance(obj, list):
        return None, url, res, "expected a JSON array, got %s" % type(obj).__name__
    return obj, url, res, None


def fetch_set(poly, months, verbose=False):
    """Fetch every month for one polygon. Missing months are reported, never filled."""
    records, fetched, missing, urls = [], [], [], []
    status = 0
    for m in months:
        recs, url, res, reason = fetch_month(poly, m, verbose=verbose)
        urls.append(url)
        status = res["status"] or status
        if recs is None:
            missing.append({"month": m, "reason": reason, "http_status": res["status"]})
        else:
            fetched.append(m)
            records.extend(recs)
    return {"records": records, "months_fetched": fetched, "months_missing": missing,
            "urls": urls, "http_status": status}


# ---------------------------------------------------------------- box -------
def analyse(records, months_fetched):
    per_month = _counts([r.get("month") for r in records])
    per_month = {m: per_month.get(m, 0) for m in months_fetched}
    seen = _counts([r.get("category") for r in records])
    by_category = {c: seen.get(c, 0) for c in CATEGORIES}
    for c, n in seen.items():
        if c not in by_category:
            by_category[c] = n  # a category the API added after this script was written
    total = len(records)
    pred = sum(by_category.get(c, 0) for c in PREDATORY)
    anchors = sorted(_counts([_anchor(r) for r in records]).items(),
                     key=lambda kv: (-kv[1], kv[0]))
    top5 = anchors[:5]
    top5_total = sum(n for _, n in top5)
    top1 = top5[0][1] if top5 else 0
    share = (lambda n: round(n / float(total), 3)) if total else (lambda n: None)
    if total and top1 / float(total) >= 0.30:
        reading = ("One anchor holds %d%% of everything in the box. That is a point source — "
                   "a station, a shopping centre, a hospital — not a street-wide problem. Look "
                   "at where it sits relative to the door before treating it as your risk."
                   % round(100 * top1 / float(total)))
    elif total and top5_total / float(total) >= 0.60:
        reading = ("The top five anchors hold %d%% of everything. Crime here clusters at a few "
                   "nodes rather than spreading along the streets."
                   % round(100 * top5_total / float(total)))
    else:
        reading = ("No single anchor dominates: the count is spread across the box, which reads "
                   "as general street activity rather than one problem address.")
    return {
        "total": total,
        "per_month": per_month,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
        "predatory_subset": {
            "categories": PREDATORY,
            "count": pred,
            "share_of_total": share(pred),
            "per_category": {c: by_category.get(c, 0) for c in PREDATORY},
            "explanation": PREDATORY_WHY,
        },
        "top_anchors": [{"anchor": a, "count": n, "share_of_total": share(n)} for a, n in top5],
        "top_anchor_share": share(top1),
        "anchor_dispersion": {
            "distinct_anchors": len(anchors),
            "top5_total": top5_total,
            "top5_mean": round(top5_total / 5.0, 1) if top5 else 0.0,
            "top5_share_of_total": share(top5_total),
            "top1_share_of_total": share(top1),
            "reading": reading,
        },
        "anchor_caveat": ("'On or near X' is an anonymised snap point, not an address. Two "
                          "incidents on the same anchor may be a hundred metres apart."),
    }


def route_analysis(route_pts, months, corridor_m, box_total, verbose=False):
    lats = [p[0] for p in route_pts]
    lngs = [p[1] for p in route_pts]
    clat, clng = sum(lats) / len(lats), sum(lngs) / len(lngs)
    pad = corridor_m + 40.0
    dlat = pad / M_PER_DEG_LAT
    dlng = pad / (M_PER_DEG_LAT * math.cos(math.radians(clat)))
    south, north = min(lats) - dlat, max(lats) + dlat
    west, east = min(lngs) - dlng, max(lngs) + dlng
    poly = ":".join("%.6f,%.6f" % c for c in
                    [(south, west), (north, west), (north, east), (south, east)])
    got = fetch_set(poly, months, verbose=verbose)
    proj = _planar(clat, clng)
    seg = [proj(la, ln) for la, ln in route_pts]
    scored, hits = [], []
    for r in got["records"]:
        ll = _latlng(r)
        if ll is None:
            continue
        px, py = proj(ll[0], ll[1])
        d = min(point_segment_m(px, py, seg[i][0], seg[i][1], seg[i + 1][0], seg[i + 1][1])
                for i in range(len(seg) - 1))
        scored.append((d, r))
        if d <= corridor_m:
            rr = dict(r)
            rr["_distance_m"] = round(d, 1)
            hits.append(rr)
    a = analyse(hits, got["months_fetched"])
    length_m = sum(haversine_m(route_pts[i][0], route_pts[i][1],
                               route_pts[i + 1][0], route_pts[i + 1][1])
                   for i in range(len(route_pts) - 1))
    nearest = min([d for d, _ in scored] or [None]) if scored else None
    ladder = sorted({float(corridor_m), 60.0, 100.0, 150.0, 250.0})
    ladder_counts = {"%dm" % int(w): sum(1 for d, _ in scored if d <= w) for w in ladder}
    warning = None
    if nearest is not None and nearest > corridor_m:
        warning = (
            "ZERO IS NOT A CLEAN BILL. The nearest anonymised police point is %.0f m from this "
            "line, which is further than the %.0f m corridor, so nothing could have matched. "
            "police.uk snaps every crime to a sparse set of map points; around here they sit "
            "tens to hundreds of metres apart, coarser than the corridor. Read `corridor_ladder` "
            "instead, or re-run with --corridor-m %d."
            % (nearest, corridor_m, int(min(w for w in ladder if w >= nearest))
               if any(w >= nearest for w in ladder) else int(nearest) + 10))
    elif not scored:
        warning = ("No police records at all in the rectangle around this route for the months "
                   "fetched. Check the months and the coordinates before reading this as quiet.")
    return {
        "route_points": [{"lat": p[0], "lng": p[1]} for p in route_pts],
        "route_length_m": round(length_m, 1),
        "corridor_m": corridor_m,
        "source_url": got["urls"][0] if got["urls"] else None,
        "source_urls_count": len(got["urls"]),
        "http_status": got["http_status"],
        "months_fetched": got["months_fetched"],
        "months_missing": got["months_missing"],
        "route_incidents": a["total"],
        "route_share": (round(a["total"] / float(box_total), 3) if box_total else None),
        "route_per_month": a["per_month"],
        "route_by_category": {k: v for k, v in a["by_category"].items() if v},
        "route_predatory": a["predatory_subset"]["count"],
        "route_anchors": a["top_anchors"],
        "nearest_anchor_m": round(nearest, 1) if nearest is not None else None,
        "records_in_route_rectangle": len(scored),
        "corridor_ladder": ladder_counts,
        "resolution_warning": warning,
        "rule": ("Incidents on the walk home count in full and must not be discounted as point "
                 "sources. A station forecourt that absorbs a hundred records is somebody else's "
                 "statistic until it sits on the route you take every night, and then it is yours."),
        "method": ("Separate police fetch over a rectangle covering the route padded by %d m, "
                   "then every record kept whose anonymised point lies within %d m of the "
                   "polyline. `route_share` is measured against the box total, so it compares "
                   "two different areas: read it as 'how much of the box's crime sits on my "
                   "walk', not as a share of one population." % (int(pad), int(corridor_m))),
    }


def box(lat, lng, half_m=150.0, months=6, end=None, route=None, corridor_m=30.0,
        verbose=False):
    end_month = end
    latest_rec = None
    if not end_month:
        latest_rec = latest(verbose=verbose)
        if not latest_rec["ok"] or not latest_rec["latest_month"]:
            return {"query": {"lat": lat, "lng": lng}, "source_url": latest_rec["source_url"],
                    "http_status": latest_rec["http_status"], "ok": False,
                    "note": "could not read the latest available month: " + (latest_rec["note"] or ""),
                    "retrieved_at": now_iso(), "evidence_class": "G"}
        end_month = latest_rec["latest_month"]
    if not (len(end_month) == 7 and end_month[4] == "-"):
        raise ValueError("--end must look like YYYY-MM")
    window = month_window(end_month, months)

    centre_box = bbox(lat, lng, half_m)
    dlat = SHIFT_M / M_PER_DEG_LAT
    dlng = SHIFT_M / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
    positions = [("centre", lat, lng),
                 ("north_20m", lat + dlat, lng),
                 ("south_20m", lat - dlat, lng),
                 ("east_20m", lat, lng + dlng),
                 ("west_20m", lat, lng - dlng)]

    sets, sensitivity = {}, {}
    for name, plat, plng in positions:
        b = bbox(plat, plng, half_m)
        got = fetch_set(b["poly"], window, verbose=verbose)
        sets[name] = got
        sensitivity[name] = len(got["records"]) if got["months_fetched"] else None

    centre = sets["centre"]
    a = analyse(centre["records"], centre["months_fetched"])
    vals = [v for v in sensitivity.values() if v is not None]
    out = {
        "query": {"lat": lat, "lng": lng, "half_m": half_m, "months": months,
                  "end_month": end_month, "corridor_m": corridor_m if route else None},
        "source_url": centre["urls"][0] if centre["urls"] else None,
        "source_urls_count": sum(len(s["urls"]) for s in sets.values()),
        "http_status": centre["http_status"],
        "ok": bool(centre["months_fetched"]) and not centre["months_missing"],
        "note": ("%d of %d months missing" % (len(centre["months_missing"]), len(window)))
                if centre["months_missing"] else "",
        "retrieved_at": now_iso(),
        "evidence_class": "G",
        "latest_available_month": (latest_rec or {}).get("latest_month"),
        "box": {k: centre_box[k] for k in ("corners", "poly", "height_m_actual",
                                           "width_m_actual", "half_m_requested")},
        "months_requested": window,
        "months_fetched": centre["months_fetched"],
        "months_missing": centre["months_missing"],
    }
    out.update(a)
    out["months_counted"] = len(centre["months_fetched"])
    out["sensitivity"] = {
        "counts": sensitivity,
        "shift_m": SHIFT_M,
        "spread": (max(vals) - min(vals)) if len(vals) > 1 else None,
        "spread_share_of_centre": (round((max(vals) - min(vals)) / float(sensitivity["centre"]), 3)
                                   if len(vals) > 1 and sensitivity.get("centre") else None),
        "explanation": ("The same box re-fetched with the centre moved 20 m north, south, east "
                        "and west. A big spread means the number is an artefact of where you put "
                        "the pin, usually because one anonymised anchor sits just inside or just "
                        "outside the edge. A small spread means the count is robust."),
    }
    if route:
        pts = parse_route(route) if isinstance(route, str) else route
        out["route"] = route_analysis(pts, window, corridor_m, a["total"], verbose=verbose)
        if out["route"]["months_missing"]:
            out["ok"] = False
            out["note"] = (out["note"] + "; " if out["note"] else "") + "route months missing"
    out["method"] = (
        "data.police.uk street-level all-crime over a %.0f m x %.0f m box (half-width %.0f m, "
        "cosine-corrected), months %s to %s, %d of %d months actually returned. Totals cover the "
        "months fetched only — nothing is scaled up to fill a gap. Caveats: locations are "
        "anonymised snap points ('On or near X'), there is no night/day split, there is no "
        "population or footfall denominator so busy places out-count dangerous ones, and "
        "publication runs 2-3 months behind, so this describes a window that has already closed."
        % (centre_box["width_m_actual"], centre_box["height_m_actual"], half_m,
           window[0], window[-1], len(centre["months_fetched"]), len(window)))
    return out


# ------------------------------------------------------------------ cli -----
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("latest", help="newest DATA month published by police.uk")

    p = sub.add_parser("box", help="all-crime in a box around a point, fixed month window")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--half-m", type=float, default=150.0, dest="half_m",
                   help="half-width in metres (default 150 -> a 300 m square)")
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--end", help="last data month, YYYY-MM (default: latest available)")
    p.add_argument("--route", help='"lat,lng;lat,lng;..." — the station-to-door walk')
    p.add_argument("--corridor-m", type=float, default=30.0, dest="corridor_m",
                   help="how far from the route line an incident still counts (default 30 m)")

    a = ap.parse_args()
    try:
        if a.cmd == "latest":
            out = latest(verbose=a.verbose)
        else:
            out = box(a.lat, a.lng, a.half_m, a.months, a.end, a.route, a.corridor_m,
                      verbose=a.verbose)
    except ValueError as exc:
        print("usage error: %s" % exc, file=sys.stderr)
        return 2
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
