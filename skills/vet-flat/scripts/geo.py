#!/usr/bin/env python3
"""postcodes.io — open UK postcode geocoder. No key, no login, no fee.

Source: https://api.postcodes.io (community-run service that republishes the ONS
Postcode Directory and OS Code-Point Open, both official open data). No robots.txt
(the host answers /robots.txt with a 404 JSON error), so nothing is disallowed;
the fetch helper still spaces requests ~1.2 s apart. Evidence class "G": the
underlying register is official; postcodes.io is the delivery mechanism.

Known API limits, measured 2026-09-03 against api.postcodes.io:
  * `radius` on the reverse-geocode endpoint is capped at **2000 m**. Larger
    values are accepted with HTTP 200 and then silently ignored — you get the
    2000 m answer with no warning. This script REFUSES radius > 2000 rather than
    let a caller believe a 5 km sweep happened.
  * `limit` is capped at **100**. Asking for 200 returns 100, no error. In dense
    central London a 2000 m call therefore stops at the 100th nearest postcode —
    about 330 m out around London Bridge. Results come back nearest-first, so a
    full response of 100 rows means the enumeration was truncated, not that the
    area only holds 100 postcodes. `cover` detects this and says so.
  * A postcode that does not exist returns HTTP 404 with a JSON error body.

Usage:
  geo.py lookup "SE1 9SG"
  geo.py reverse --lat 51.504963 --lng -0.087625 [--radius 200] [--limit 10]
  geo.py nearby  --lat 51.504963 --lng -0.087625 --radius 2000
  geo.py cover   --lat 51.504963 --lng -0.087625 --radius 3200 [--step 1500]
  geo.py box     --lat 51.504963 --lng -0.087625 --half-m 150
Add --verbose to see the curl commands on stderr. All commands print one JSON
object on stdout. Exit 0 on success, 2 on usage error, 1 on fetch failure.

Importable pure-math helpers (no network): haversine_m(), bbox().
"""
import argparse
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, now_iso  # noqa: E402

BASE = "https://api.postcodes.io"
MAX_RADIUS_M = 2000       # hard cap in the API; bigger values are ignored silently
MAX_LIMIT = 100           # hard cap in the API; bigger values are ignored silently
M_PER_DEG_LAT = 111320.0  # WGS84 mean; good to ~0.1 % anywhere in the UK
EARTH_R_M = 6371008.8     # IUGG mean Earth radius

FIELDS = ("postcode", "latitude", "longitude", "admin_district", "admin_ward",
          "lsoa", "msoa", "outcode", "incode", "region", "country",
          "parliamentary_constituency", "eastings", "northings", "quality")


# ------------------------------------------------------------ pure maths ----
def haversine_m(lat1, lng1, lat2, lng2):
    """Great-circle distance in metres between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * EARTH_R_M * math.asin(math.sqrt(a))


def bbox(lat, lng, half_m):
    """Axis-aligned rectangle `half_m` metres from the centre in each direction.

    Longitude is cosine-corrected for the centre latitude, so the box is square
    on the ground rather than square in degrees. Returns the four corners in
    ring order (SW, NW, NE, SE) plus the metres actually covered, measured back
    off the corners with haversine so the caller can check the approximation.
    """
    half_m = float(half_m)
    dlat = half_m / M_PER_DEG_LAT
    dlng = half_m / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
    south, north = lat - dlat, lat + dlat
    west, east = lng - dlng, lng + dlng
    corners = [(south, west), (north, west), (north, east), (south, east)]
    return {
        "centre": {"lat": lat, "lng": lng},
        "half_m_requested": half_m,
        "delta_lat_deg": dlat,
        "delta_lng_deg": dlng,
        "south": south, "north": north, "west": west, "east": east,
        "corners": [{"lat": round(a, 6), "lng": round(b, 6)} for a, b in corners],
        "poly": ":".join("%.6f,%.6f" % (a, b) for a, b in corners),
        "height_m_actual": round(haversine_m(south, lng, north, lng), 1),
        "width_m_actual": round(haversine_m(lat, west, lat, east), 1),
        "half_m_actual_ns": round(haversine_m(lat, lng, north, lng), 1),
        "half_m_actual_ew": round(haversine_m(lat, lng, lat, east), 1),
        "note": ("Cosine-corrected rectangle, not a circle. A 'radius' of R metres "
                 "quoted from this box means the half-width; the corners sit R*1.414 out."),
    }


def _hex_lattice(radius_m, step_m):
    """Offsets (east_m, north_m) of a hexagonal lattice covering a disc.

    Rows are step*sqrt(3)/2 apart and every other row is shifted half a step, so
    each point is at most step/sqrt(3) from its neighbours' shared boundary.
    """
    pts = [(0.0, 0.0)]
    dy = step_m * math.sqrt(3.0) / 2.0
    rows = int(math.ceil(radius_m / dy)) if dy else 0
    for j in range(-rows, rows + 1):
        y = j * dy
        offset = (step_m / 2.0) if (j % 2) else 0.0
        cols = int(math.ceil((radius_m + step_m) / step_m))
        for i in range(-cols, cols + 1):
            x = i * step_m + offset
            if (x, y) == (0.0, 0.0):
                continue
            if math.hypot(x, y) <= radius_m:
                pts.append((x, y))
    return pts


def _offset(lat, lng, east_m, north_m):
    return (lat + north_m / M_PER_DEG_LAT,
            lng + east_m / (M_PER_DEG_LAT * math.cos(math.radians(lat))))


# ---------------------------------------------------------------- fetch -----
def _json_body(res):
    """Parse a postcodes.io response body; return (obj, error_string)."""
    try:
        return json.loads(res["body"]), None
    except Exception as exc:
        return None, "response was not JSON: %s" % str(exc)[:120]


def _envelope(res, url, note_extra=None):
    note = res["note"]
    if note_extra:
        note = (note + "; " if note else "") + note_extra
    return {"source_url": url, "http_status": res["status"], "ok": bool(res["ok"]),
            "note": note, "retrieved_at": res["retrieved_at"], "evidence_class": "G"}


def _slim(row):
    out = {k: row.get(k) for k in FIELDS}
    out["lat"] = out.pop("latitude", None)
    out["lng"] = out.pop("longitude", None)
    return out


# ------------------------------------------------------- pure parsers -------
def parse_lookup(obj):
    """postcodes.io /postcodes/<pc> body -> (record|None, api_error|None)."""
    if not isinstance(obj, dict):
        return None, "expected a JSON object"
    result = obj.get("result")
    if not isinstance(result, dict):
        return None, obj.get("error") or "no result in response"
    return _slim(result), None


def parse_nearby(obj, lat, lng):
    """postcodes.io reverse-geocode body -> rows with distance_m, nearest first."""
    rows = obj.get("result") if isinstance(obj, dict) else None
    items = []
    for r in rows or []:
        s = _slim(r)
        s["distance_m"] = (round(haversine_m(lat, lng, s["lat"], s["lng"]), 1)
                           if s["lat"] is not None else None)
        items.append(s)
    items.sort(key=lambda x: (x["distance_m"] is None, x["distance_m"]))
    return items


# --------------------------------------------------------------- lookup -----
def lookup_outcode(outcode, verbose=False):
    """Coarse postal-district centroid, not a property location.

    https://postcodes.io/docs/outcode/lookup/ documents this separate endpoint.
    """
    code = str(outcode).strip().upper()
    if not re.fullmatch(r"[A-Z]{1,2}[0-9][A-Z0-9]?", code):
        raise ValueError("give one outward code, not an address")
    url = "%s/outcodes/%s" % (BASE, code)
    res = fetch(url, cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: '"latitude"' in b or '"error"' in b)
    out = dict(_envelope(res, url), query={"outcode": code}, lat=None, lng=None,
               outcode=code, precision="postal_district", method="Outcode centroid; not a home or street location.")
    obj, error = _json_body(res) if res.get("body") else (None, "empty body")
    row = obj.get("result") if isinstance(obj, dict) else None
    valid = isinstance(obj, dict) and obj.get("status") == 200 and isinstance(row, dict) and str(row.get("outcode", "")).upper() == code
    if valid:
        lat, lng = row.get("latitude"), row.get("longitude")
        valid = (type(lat) in (int, float) and type(lng) in (int, float)
                 and math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180)
    if not out["ok"] or not valid:
        out.update(ok=False, note=error or (obj.get("error") if isinstance(obj, dict) else None) or "outcode centroid unavailable")
        return out
    out.update(lat=lat, lng=lng, admin_district=row.get("admin_district"), admin_ward=row.get("admin_ward"))
    return out


def lookup(postcode, verbose=False):
    pc = "".join(postcode.split()).upper()
    url = "%s/postcodes/%s" % (BASE, pc)
    res = fetch(url, cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: '"latitude"' in b or '"error"' in b)
    out = {"query": {"postcode": postcode, "normalised": pc}}
    out.update(_envelope(res, url))
    obj, err = _json_body(res) if res["body"] else (None, "empty body")
    if err:
        out["ok"] = False
        out["note"] = (out["note"] + "; " if out["note"] else "") + err
    record, api_err = parse_lookup(obj) if obj is not None else (None, err)
    if record is None:
        out["ok"] = False
        if api_err:
            out["note"] = (out["note"] + "; " if out["note"] else "") + str(api_err)
        out["not_found"] = {"query": pc, "endpoint": url}
        for k in ("lat", "lng", "admin_district", "admin_ward", "lsoa", "msoa",
                  "outcode", "region"):
            out[k] = None
        return out
    out.update(record)
    out["method"] = ("ONS Postcode Directory via postcodes.io. `quality` 1 means the "
                     "coordinate is within the building; higher numbers are coarser. "
                     "A postcode centroid is not a door: expect tens of metres of error.")
    return out


# -------------------------------------------------------------- reverse -----
def _reverse_call(lat, lng, radius, limit, verbose=False, wide_search=False):
    url = ("%s/postcodes?lat=%s&lon=%s&radius=%d&limit=%d"
           % (BASE, repr(float(lat)), repr(float(lng)), int(radius), int(limit)))
    if wide_search:
        url += "&wideSearch=true"
    res = fetch(url, cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: '"result"' in b or '"error"' in b)
    obj, err = _json_body(res) if res["body"] else (None, "empty body")
    rows = (obj or {}).get("result") if isinstance(obj, dict) else None
    if rows is None:
        rows = []
    return url, res, rows, err


def reverse(lat, lng, radius=200, limit=10, verbose=False):
    if radius > MAX_RADIUS_M:
        raise ValueError("postcodes.io caps radius at %d m" % MAX_RADIUS_M)
    url, res, rows, err = _reverse_call(lat, lng, radius, min(limit, MAX_LIMIT), verbose)
    out = {"query": {"lat": lat, "lng": lng, "radius_m": radius, "limit": min(limit, MAX_LIMIT)}}
    out.update(_envelope(res, url, err))
    if err:
        out["ok"] = False
    items = parse_nearby({"result": rows}, lat, lng)
    out["count"] = len(items)
    out["nearest"] = items[0] if items else None
    out["results"] = items
    if not items:
        out["not_found"] = {"query": url}
    return out


def nearby(lat, lng, radius=2000, verbose=False):
    """All postcodes within `radius` (max 2000 m), nearest first, max 100 rows."""
    if radius > MAX_RADIUS_M:
        raise ValueError(
            "radius %d m exceeds the postcodes.io cap of %d m. The API would accept it, "
            "return HTTP 200 and silently give you the %d m answer. Use `cover` to tile a "
            "bigger circle." % (radius, MAX_RADIUS_M, MAX_RADIUS_M))
    out = reverse(lat, lng, radius=radius, limit=MAX_LIMIT, verbose=verbose)
    out["saturated"] = out["count"] >= MAX_LIMIT
    out["furthest_m"] = max([r["distance_m"] for r in out["results"]
                             if r["distance_m"] is not None] or [None]) if out["results"] else None
    out["postcodes"] = [r["postcode"] for r in out["results"]]
    out["outcodes"] = sorted({r["outcode"] for r in out["results"] if r.get("outcode")})
    out["method"] = ("postcodes.io reverse geocode. Hard caps: radius 2000 m, 100 rows. "
                     "`saturated` true means the 100-row cap was hit before the radius, so "
                     "this is the nearest 100 postcodes out to `furthest_m`, not every "
                     "postcode in the circle.")
    return out


# ---------------------------------------------------------------- cover -----
def cover(lat, lng, radius=3200, step=1500, verbose=False):
    """Union of several <=2000 m `nearby` calls on a hex grid — the 2-mile sweep.

    Each tile still obeys the 100-row cap, so in dense London a tile saturates
    long before its 2000 m radius. `complete` says whether every tile came back
    under the cap; when it is false, re-run with a smaller --step.
    """
    if step <= 0:
        raise ValueError("--step must be positive")
    tile_radius = MAX_RADIUS_M
    max_step = tile_radius * math.sqrt(3.0)
    if step > max_step:
        raise ValueError("--step %d m leaves gaps: with a %d m tile radius the hex grid "
                         "needs step <= %d m" % (step, tile_radius, int(max_step)))
    offsets = _hex_lattice(float(radius), float(step))
    tiles, seen, urls = [], {}, []
    n_saturated, n_failed = 0, 0
    for east_m, north_m in offsets:
        tlat, tlng = _offset(lat, lng, east_m, north_m)
        url, res, rows, err = _reverse_call(tlat, tlng, tile_radius, MAX_LIMIT, verbose)
        urls.append(url)
        sat = len(rows) >= MAX_LIMIT
        if sat:
            n_saturated += 1
        if not res["ok"] or err:
            n_failed += 1
        far = 0.0
        for r in rows:
            if r.get("latitude") is None:
                continue
            far = max(far, haversine_m(tlat, tlng, r["latitude"], r["longitude"]))
            d = haversine_m(lat, lng, r["latitude"], r["longitude"])
            pc = r.get("postcode")
            if pc and (pc not in seen or d < seen[pc]["distance_m"]):
                s = _slim(r)
                s["distance_m"] = round(d, 1)
                seen[pc] = s
        tiles.append({"lat": round(tlat, 6), "lng": round(tlng, 6),
                      "east_m": round(east_m), "north_m": round(north_m),
                      "http_status": res["status"], "ok": bool(res["ok"]) and not err,
                      "returned": len(rows), "saturated": sat,
                      "reach_m": round(far, 1) if rows else None})
    inside = {pc: s for pc, s in seen.items() if s["distance_m"] <= radius}
    reaches = [t["reach_m"] for t in tiles if t["saturated"] and t["reach_m"] is not None]
    return {
        "query": {"lat": lat, "lng": lng, "radius_m": radius, "step_m": step,
                  "tile_radius_m": tile_radius},
        "source_url": urls[0] if urls else None,
        "source_urls_count": len(urls),
        "http_status": tiles[0]["http_status"] if tiles else 0,
        "ok": n_failed == 0,
        "note": ("%d of %d tiles failed" % (n_failed, len(tiles))) if n_failed else "",
        "retrieved_at": now_iso(), "evidence_class": "G",
        "tiles": tiles, "tiles_requested": len(offsets), "tiles_saturated": n_saturated,
        "complete": n_failed == 0 and n_saturated == 0,
        "count": len(inside),
        "count_including_overspill": len(seen),
        "postcodes": sorted(inside),
        "outcodes": sorted({s["outcode"] for s in inside.values() if s.get("outcode")}),
        "outcode_counts": _counts([s.get("outcode") for s in inside.values()]),
        "admin_districts": _counts([s.get("admin_district") for s in inside.values()]),
        "saturation_reach_m": round(min(reaches), 1) if reaches else None,
        "method": (
            "Hex grid of %d postcodes.io reverse-geocode calls, each radius %d m (the API "
            "maximum), deduped and clipped to %d m of the centre. Each call also caps at 100 "
            "rows: %d tile(s) hit that cap, so those tiles only enumerated out to about %s m "
            "and the union is a floor, not a census. Lower --step to close the gap."
            % (len(offsets), tile_radius, radius, n_saturated,
               ("%.0f" % min(reaches)) if reaches else "n/a")),
    }


def _counts(values):
    out = {}
    for v in values:
        if v is None:
            continue
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


# ------------------------------------------------------------------ cli -----
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lookup", help="postcode -> coordinates and admin geography")
    p.add_argument("postcode")

    p = sub.add_parser("reverse", help="coordinates -> nearest postcodes")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=200)
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("nearby", help="every postcode within a radius (max 2000 m)")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=2000)

    p = sub.add_parser("cover", help="tile a bigger circle with several nearby calls")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius", type=int, default=3200, help="metres; 3200 = 2 miles")
    p.add_argument("--step", type=int, default=1500, help="hex grid spacing in metres")

    p = sub.add_parser("box", help="cosine-corrected rectangle around a point")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--half-m", type=float, default=150.0, dest="half_m")

    a = ap.parse_args()
    v = a.verbose
    try:
        if a.cmd == "lookup":
            out = lookup(a.postcode, verbose=v)
        elif a.cmd == "reverse":
            out = reverse(a.lat, a.lng, a.radius, a.limit, verbose=v)
        elif a.cmd == "nearby":
            out = nearby(a.lat, a.lng, a.radius, verbose=v)
        elif a.cmd == "cover":
            out = cover(a.lat, a.lng, a.radius, a.step, verbose=v)
        else:
            out = bbox(a.lat, a.lng, a.half_m)
            out.update(retrieved_at=now_iso(), evidence_class="I", ok=True,
                       source_url=None, http_status=None)
    except ValueError as exc:
        print("usage error: %s" % exc, file=sys.stderr)
        return 2
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
