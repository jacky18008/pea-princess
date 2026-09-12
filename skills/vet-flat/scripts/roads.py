#!/usr/bin/env python3
"""OpenStreetMap via Overpass — what is physically around a flat.

Source: https://overpass-api.de/api/interpreter (fallback
https://overpass.kumi.systems/api/interpreter). Data is OpenStreetMap,
(c) OpenStreetMap contributors, licensed ODbL 1.0. No key, no login, no fee.

Two things about Overpass that bite:
  1. It answers a BROWSER User-Agent with 406 Not Acceptable — the exact
     inverse of every other host in this repo. Send `_fetch.TOOL_UA`.
  2. The public instance rate-limits hard, and the refusal often arrives as a
     dropped TLS connection rather than an HTTP 429. This tool sends ONE
     combined query per call and backs off 2 / 4 / 8 s on 429, 5xx and
     transport errors before falling back to the mirror.
overpass-api.de/robots.txt says `Disallow: /api/` for everyone. That rule is
aimed at crawlers indexing the interpreter; this is a single user-directed
query per flat. Keep it that way: do not loop this over a list of addresses.

WHAT IT ANSWERS, and the radius each answer uses (the fixed radii are the
nuisance distance for that thing, so --radius only widens the linear features):
  trunk_or_primary_road   highway=motorway|trunk|primary        --radius (300 m)
  secondary_road          highway=secondary                     --radius
  railway_surface         railway=rail, usage=main|branch, not in tunnel
  railway_tunnel_portal   the nearest END NODE of a tunnel=yes railway way
  tube_surface            railway=subway|light_rail, not in tunnel
  helipad_or_aerodrome    aeroway=helipad|aerodrome                    1000 m
  night_economy           amenity=pub|bar|nightclub                     100 m
  food_smell_sources      amenity=restaurant|fast_food|marketplace,
                          shop=butcher|fishmonger                        60 m
  waste_or_recycling      amenity=recycling|waste_transfer_station,
                          landuse=industrial                            150 m
  supermarket             shop=supermarket|convenience                  400 m
  park_or_green           leisure=park                                  400 m
  obstruction_candidates  buildings with building:levels or height       60 m
Distances are point-to-SEGMENT against the real `out geom` geometry, not to a
centroid, so a road that runs past the flat is measured where it actually
passes. A point inside a polygon (a park, an industrial estate) scores 0 m.
Every distance is an integer in metres; `null` means nothing of that kind was
found inside that radius — which is an OSM coverage statement, not proof.

Usage:
  roads.py near --lat 51.5045 --lng -0.0865 [--radius 300]
  roads.py facade-note --lat 51.5045 --lng -0.0865 [--radius 300]
Both print one JSON object carrying source_url, http_status, ok, note,
retrieved_at, evidence_class "C" (third-party open data: OSM is crowd-sourced,
not an official register), plus query_used and overpass_instance.
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fetch import fetch, TOOL_UA, now_iso  # noqa: E402

INSTANCES = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter"]
BACKOFF_S = [2, 4, 8]
ATTRIBUTION = "© OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)"

R_AERO, R_NIGHT, R_FOOD, R_WASTE, R_SHOP, R_PARK, R_BUILD = 1000, 100, 60, 150, 400, 400, 60
FACADE_TRIGGER_M = 60
WALK_M_PER_MIN = 80.0          # 4.8 km/h
STREET_DETOUR = 1.3            # straight line -> walked distance, rule of thumb
STOREY_M = 3.0                 # assumed floor-to-floor when only building:levels is tagged

FACADE_NOTE = ("a mapped main road is within %d m of the query point; check the flat's window "
               "direction and sound insulation. This proximity check does not establish its "
               "facade orientation or a quiet side" % FACADE_TRIGGER_M)


# ------------------------------------------------------------- geometry ----
EARTH_R = 6371008.8


def haversine_m(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1, lng1, lat2, lng2):
    """Initial great-circle bearing, degrees clockwise from true north (0-360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg):
    return None if deg is None else COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def _local_xy(lat, lng, lat0, lng0):
    """Equirectangular metres about (lat0, lng0). Under 0.1 % error at km scale."""
    k = math.cos(math.radians(lat0))
    return (math.radians(lng - lng0) * EARTH_R * k, math.radians(lat - lat0) * EARTH_R)


def nearest_point_on_segment(plat, plng, alat, alng, blat, blng):
    """(distance_m, lat, lng) from P to the segment AB — not to A or B alone."""
    ax, ay = _local_xy(alat, alng, plat, plng)
    bx, by = _local_xy(blat, blng, plat, plng)
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / den))
    return (math.hypot(ax + t * dx, ay + t * dy),
            alat + (blat - alat) * t, alng + (blng - alng) * t)


def point_segment_distance_m(plat, plng, alat, alng, blat, blng):
    return nearest_point_on_segment(plat, plng, alat, alng, blat, blng)[0]


def point_in_ring(plat, plng, ring):
    """Ray-cast point-in-polygon on a closed ring of (lat, lng) pairs."""
    if len(ring) < 4 or ring[0] != ring[-1]:
        return False
    inside = False
    for (y1, x1), (y2, x2) in zip(ring[:-1], ring[1:]):
        if (y1 > plat) != (y2 > plat):
            xin = x1 + (plat - y1) * (x2 - x1) / (y2 - y1)
            if plng < xin:
                inside = not inside
    return inside


# ----------------------------------------------------- OSM element shapes ---
def element_lines(el):
    """[[(lat,lng), ...], ...] — every polyline an element contributes."""
    if el.get("type") == "node":
        if el.get("lat") is not None:
            return [[(el["lat"], el["lon"])]]
        return []
    if el.get("geometry"):
        return [[(g["lat"], g["lon"]) for g in el["geometry"] if g.get("lat") is not None]]
    out = []
    for m in el.get("members") or []:
        if m.get("geometry"):
            out.append([(g["lat"], g["lon"]) for g in m["geometry"] if g.get("lat") is not None])
    return [ln for ln in out if ln]


def nearest_on_element(plat, plng, el):
    """(distance_m, lat, lng) to the closest point of the element's geometry.

    0 m if the point falls inside a closed ring (a park you already live in).
    """
    best = (float("inf"), None, None)
    for line in element_lines(el):
        if len(line) == 1:
            d = haversine_m(plat, plng, line[0][0], line[0][1])
            if d < best[0]:
                best = (d, line[0][0], line[0][1])
            continue
        if line[0] == line[-1] and point_in_ring(plat, plng, line):
            return 0.0, plat, plng
        for a, b in zip(line[:-1], line[1:]):
            cand = nearest_point_on_segment(plat, plng, a[0], a[1], b[0], b[1])
            if cand[0] < best[0]:
                best = cand
    return best if best[1] is not None else (None, None, None)


def end_nodes(el):
    """[(node_id_or_None, lat, lng)] for the first and last vertex of each polyline."""
    ids = el.get("nodes") or []
    out = []
    for line in element_lines(el):
        if not line:
            continue
        first = ids[0] if len(ids) == len(line) else None
        last = ids[-1] if len(ids) == len(line) else None
        out.append((first, line[0][0], line[0][1]))
        if len(line) > 1:
            out.append((last, line[-1][0], line[-1][1]))
    return out


def surface_rail_node_ids(elements):
    """Node ids belonging to railway ways that are NOT in a tunnel.

    A tunnel way's end node is usually just where the mapper split the way. It
    is a real portal only where the tunnel way meets a surface railway way, i.e.
    where the shared node also appears in a non-tunnel railway way.
    """
    ids = set()
    for el in elements:
        t = _t(el)
        if t.get("railway") in ("rail", "subway", "light_rail") and not _in_tunnel(t):
            ids.update(el.get("nodes") or [])
    return ids


def osm_id(el):
    return "%s/%s" % (el.get("type"), el.get("id"))


def osm_url(el):
    return "https://www.openstreetmap.org/%s/%s" % (el.get("type"), el.get("id"))


# ------------------------------------------------------------ the query -----
def build_query(lat, lng, radius=300, timeout=40):
    """One Overpass QL request covering every category. Classification happens
    client-side off each element's tags, so this stays a single round trip."""
    p = "%s,%s" % (lat, lng)
    return """[out:json][timeout:{t}];
(
  way(around:{r},{p})["highway"~"^(motorway|trunk|primary|secondary)$"];
  way(around:{r},{p})["railway"~"^(rail|subway|light_rail)$"];
  nwr(around:{aero},{p})["aeroway"~"^(helipad|aerodrome)$"];
  nwr(around:{night},{p})["amenity"~"^(pub|bar|nightclub)$"];
  nwr(around:{food},{p})["amenity"~"^(restaurant|fast_food|marketplace)$"];
  nwr(around:{food},{p})["shop"~"^(butcher|fishmonger)$"];
  nwr(around:{waste},{p})["amenity"~"^(recycling|waste_transfer_station)$"];
  nwr(around:{waste},{p})["landuse"="industrial"];
  nwr(around:{shop},{p})["shop"~"^(supermarket|convenience)$"];
  nwr(around:{park},{p})["leisure"="park"];
  way(around:{build},{p})["building"][~"^(building:levels|height)$"~"."];
);
out geom;""".format(t=timeout, r=int(radius), p=p, aero=R_AERO, night=R_NIGHT,
                    food=R_FOOD, waste=R_WASTE, shop=R_SHOP, park=R_PARK, build=R_BUILD)


def _retryable(res):
    """Overpass says 'slow down' in several dialects.

    Sometimes 429. Sometimes 504. Often not HTTP at all: the public instance
    drops the connection, and curl reports 'Empty reply from server' (52),
    'SSL_ERROR_SYSCALL' (35) or 'Recv failure' (56) with no status. Any
    transport-level failure is therefore worth a backoff and then the mirror.
    A 400 (bad Overpass QL) or 406 (wrong User-Agent) is not — retrying those
    just wastes someone else's server.
    """
    if res["status"] in (408, 429, 500, 502, 503, 504):
        return True
    return res["status"] == 0


def run_overpass(query, verbose=False, cache_ttl=86400):
    """POST the query, backing off 2/4/8 s, then trying the mirror.

    Returns (data_or_None, meta) where meta carries the envelope fields plus the
    instance actually used and every attempt made.
    """
    body = "data=" + urllib.parse.quote(query)
    attempts, res = [], None
    for url in INSTANCES:
        for i, wait in enumerate([0] + BACKOFF_S):
            # Only the first attempt may read the on-disk cache. _fetch caches any
            # response that carried a status, a 504 included, so retrying against
            # the cache would just replay the same failure and burn the backoff.
            ttl = cache_ttl if i == 0 else 0
            if wait and not (res or {}).get("from_cache"):
                time.sleep(wait)
            res = fetch(url, ua=TOOL_UA, method="POST", data=body,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=90, min_gap=2.0, cache_ttl=ttl, verbose=verbose,
                        expect=lambda b: '"elements"' in b)
            attempts.append({"instance": url, "attempt": i + 1, "http_status": res["status"],
                             "ok": res["ok"], "note": res["note"],
                             "from_cache": res.get("from_cache", False)})
            if res["ok"]:
                try:
                    data = json.loads(res["body"])
                except ValueError:
                    res["ok"], res["note"] = False, "response was not JSON"
                    break
                return data, {"source_url": url, "http_status": res["status"], "ok": True,
                              "note": "", "retrieved_at": res["retrieved_at"],
                              "overpass_instance": url, "attempts": attempts,
                              "from_cache": res.get("from_cache", False)}
            if not _retryable(res):
                break
    note = (res or {}).get("note") or "overpass unavailable"
    if (res or {}).get("status") == 406:
        note += " (406 = Overpass refused the User-Agent; it rejects browser UAs)"
    return None, {"source_url": INSTANCES[0], "http_status": (res or {}).get("status", 0),
                  "ok": False, "note": note, "retrieved_at": now_iso(),
                  "overpass_instance": None, "attempts": attempts}


# --------------------------------------------------------- classification ---
def _t(el):
    return el.get("tags") or {}


def _name(el):
    t = _t(el)
    return t.get("name") or t.get("ref") or t.get("operator") or t.get("brand") or None


def is_trunk_or_primary(el):
    return _t(el).get("highway") in ("motorway", "trunk", "primary")


def is_secondary(el):
    return _t(el).get("highway") == "secondary"


def _in_tunnel(t):
    return t.get("tunnel") not in (None, "no") or t.get("location") == "underground"


def is_railway_surface(el):
    t = _t(el)
    return (t.get("railway") == "rail" and t.get("usage") in ("main", "branch")
            and not _in_tunnel(t))


def is_railway_tunnel(el):
    t = _t(el)
    return t.get("railway") in ("rail", "subway", "light_rail") and _in_tunnel(t)


def is_tube_surface(el):
    t = _t(el)
    return t.get("railway") in ("subway", "light_rail") and not _in_tunnel(t)


def is_aero(el):
    return _t(el).get("aeroway") in ("helipad", "aerodrome")


def is_night(el):
    return _t(el).get("amenity") in ("pub", "bar", "nightclub")


def is_food_smell(el):
    t = _t(el)
    return (t.get("amenity") in ("restaurant", "fast_food", "marketplace")
            or t.get("shop") in ("butcher", "fishmonger"))


def is_waste(el):
    t = _t(el)
    return (t.get("amenity") in ("recycling", "waste_transfer_station")
            or t.get("landuse") == "industrial")


def is_supermarket(el):
    return _t(el).get("shop") in ("supermarket", "convenience")


def is_park(el):
    return _t(el).get("leisure") == "park"


def is_obstruction(el):
    t = _t(el)
    return bool(t.get("building")) and (t.get("building:levels") or t.get("height"))


def parse_height_m(tag):
    """OSM `height` is metres by default but ' m', "'" and 'ft' all show up."""
    if tag is None:
        return None
    s = str(tag).strip().lower()
    m = re.match(r"^([\d.]+)\s*(m|metres?|meters?|ft|feet|')?$", s)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return round(v * 0.3048, 1) if m.group(2) in ("ft", "feet", "'") else v


def obstruction_angle_deg(height_m, distance_m):
    """Elevation angle of a neighbour's roofline from ground level at the flat.

    angle ~= atan(height / distance). Over 45 degrees on a low floor means the
    building fills more than half the sky in that direction.
    """
    if not height_m or distance_m is None:
        return None
    if distance_m <= 0:
        return 90.0                       # the point is inside the footprint
    return round(math.degrees(math.atan(height_m / distance_m)), 1)


# ------------------------------------------------------------- assembly -----
def _record(el, dist, plat, plng, near_pt=None, extra=None):
    lat, lng = (near_pt or (None, None))
    rec = {"distance_m": int(round(dist)) if dist is not None else None,
           "name": _name(el), "osm_id": osm_id(el), "osm_url": osm_url(el)}
    if lat is not None:
        b = bearing_deg(plat, plng, lat, lng)
        rec["bearing_deg"] = int(round(b))
        rec["direction"] = compass(b)
    rec.update(extra or {})
    return rec


def _category(elements, plat, plng, pred, limit_m, tag_keys=(), sort_key=None):
    """Nearest match plus a count, for one category."""
    found = []
    for el in elements:
        if not pred(el):
            continue
        d, lat, lng = nearest_on_element(plat, plng, el)
        if d is None or d > limit_m:
            continue
        t = _t(el)
        extra = {k: t.get(k) for k in tag_keys if t.get(k) is not None}
        found.append((d, _record(el, d, plat, plng, (lat, lng), extra)))
    found.sort(key=sort_key or (lambda x: x[0]))
    names, seen = [], set()
    for _, r in found:                       # OSM splits one road into many ways;
        n = r.get("name")                    # the distinct names are the useful count
        if n and n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)
    return {"search_radius_m": int(limit_m),
            "count": len(found),
            "count_note": "count is OSM elements, not places: a single road or railway is "
                          "usually split into many ways. See names.",
            "names": names[:12],
            "nearest": found[0][1] if found else None,
            "others": [r for _, r in found[1:6]]}


def near(lat, lng, radius=300, verbose=False, elements=None, meta=None):
    query = build_query(lat, lng, radius)
    if elements is None:
        data, meta = run_overpass(query, verbose=verbose)
        elements = (data or {}).get("elements") or []
    meta = meta or {"source_url": INSTANCES[0], "http_status": 200, "ok": True, "note": "",
                    "retrieved_at": now_iso(), "overpass_instance": "fixture", "attempts": []}
    out = {
        "source_url": meta["source_url"], "http_status": meta["http_status"], "ok": meta["ok"],
        "note": meta["note"], "retrieved_at": meta["retrieved_at"], "evidence_class": "C",
        "attribution": ATTRIBUTION, "point": {"lat": lat, "lng": lng}, "radius_m": radius,
        "overpass_instance": meta.get("overpass_instance"), "attempts": meta.get("attempts"),
        "query_used": query, "element_count": len(elements),
    }
    if not meta["ok"]:
        out["not_found"] = {"what": "everything — Overpass did not answer", "query": query,
                            "meaning": "no result at all; this is a fetch failure, not an "
                                       "absence of roads, rail or shops"}
        return out

    road_tags = ("highway", "ref", "lanes", "maxspeed", "oneway")
    out["trunk_or_primary_road"] = _category(elements, lat, lng, is_trunk_or_primary,
                                             radius, road_tags)
    out["secondary_road"] = _category(elements, lat, lng, is_secondary, radius, road_tags)
    out["railway_surface"] = _category(elements, lat, lng, is_railway_surface, radius,
                                       ("railway", "usage", "electrified", "layer"))
    out["tube_surface"] = _category(elements, lat, lng, is_tube_surface, radius,
                                    ("railway", "layer"))

    # tunnel portals: measure to the END NODES of tunnel ways, not along their length
    surface_ids = surface_rail_node_ids(elements)
    portals, seen_nodes = [], set()
    for el in elements:
        if not is_railway_tunnel(el):
            continue
        for nid, nlat, nlng in end_nodes(el):
            d = haversine_m(lat, lng, nlat, nlng)
            if d > radius or (nid is not None and nid in seen_nodes):
                continue
            if nid is not None:
                seen_nodes.add(nid)
            confirmed = nid is not None and nid in surface_ids
            b = bearing_deg(lat, lng, nlat, nlng)
            portals.append((0 if confirmed else 1, d, {
                "distance_m": int(round(d)), "name": _name(el),
                "osm_id": osm_id(el), "osm_url": osm_url(el),
                "bearing_deg": int(round(b)), "direction": compass(b),
                "railway": _t(el).get("railway"), "node_id": nid,
                "confirmed_portal": confirmed,
                "note": ("this end node is shared with a surface railway way, so it really is "
                         "where the line comes out of the ground") if confirmed else
                        ("end of a tunnel way with no surface railway meeting it inside the "
                         "search radius — most likely just where the mapper split the way, "
                         "not a portal")}))
    portals.sort(key=lambda x: (x[0], x[1]))
    conf = [r for c, _, r in portals if c == 0]
    out["railway_tunnel_portal"] = {
        "search_radius_m": int(radius),
        "count": len(conf),
        "count_unconfirmed_way_ends": len(portals) - len(conf),
        "nearest": conf[0] if conf else None,
        "others": conf[1:6],
        "unconfirmed_way_ends": [r for c, _, r in portals if c == 1][:4]}

    out["helipad_or_aerodrome"] = _category(elements, lat, lng, is_aero, R_AERO,
                                            ("aeroway", "iata", "icao"))
    out["night_economy"] = _category(elements, lat, lng, is_night, R_NIGHT,
                                     ("amenity", "opening_hours", "outdoor_seating"))
    out["food_smell_sources"] = _category(elements, lat, lng, is_food_smell, R_FOOD,
                                          ("amenity", "shop", "cuisine"))
    out["waste_or_recycling"] = _category(elements, lat, lng, is_waste, R_WASTE,
                                          ("amenity", "landuse", "recycling_type"))
    out["park_or_green"] = _category(elements, lat, lng, is_park, R_PARK, ("leisure", "access"))

    sm = _category(elements, lat, lng, is_supermarket, R_SHOP, ("shop", "brand", "opening_hours"))
    if sm["nearest"]:
        d = sm["nearest"]["distance_m"]
        sm["nearest"]["walk_minutes_straight_line"] = max(1, int(round(d / WALK_M_PER_MIN)))
        sm["nearest"]["walk_minutes_street_estimate"] = max(
            1, int(round(d * STREET_DETOUR / WALK_M_PER_MIN)))
        sm["walking_note"] = ("straight-line distance at %d m/min; the street estimate adds a "
                              "%.0f%% detour factor and still ignores crossings and stairs"
                              % (WALK_M_PER_MIN, (STREET_DETOUR - 1) * 100))
    out["supermarket"] = sm

    # obstruction candidates: what blocks the sky, and from which direction
    obs = []
    for el in elements:
        if not is_obstruction(el):
            continue
        d, blat, blng = nearest_on_element(lat, lng, el)
        if d is None or d > R_BUILD:
            continue
        t = _t(el)
        try:
            levels = float(t.get("building:levels")) if t.get("building:levels") else None
        except ValueError:
            levels = None
        h = parse_height_m(t.get("height"))
        h_est = h if h is not None else (round(levels * STOREY_M, 1) if levels else None)
        inside = d <= 0.5
        b = None if inside else bearing_deg(lat, lng, blat, blng)
        obs.append((d, {
            "distance_m": int(round(d)),
            "bearing_deg": None if b is None else int(round(b)),
            "direction": compass(b),
            "contains_point": inside,
            "building": t.get("building"), "name": _name(el),
            "building_levels": levels, "height_m": h,
            "height_m_estimate": h_est,
            "height_source": "height tag" if h is not None else
                             ("building:levels x %.1f m" % STOREY_M if levels else None),
            "obstruction_angle_deg": 90 if inside else obstruction_angle_deg(h_est, d),
            "osm_id": osm_id(el), "osm_url": osm_url(el)}))
    obs.sort(key=lambda x: (-(x[1]["obstruction_angle_deg"] or 0), x[0]))
    out["obstruction_candidates"] = {
        "search_radius_m": R_BUILD, "count": len(obs),
        "worst_first": [r for _, r in obs[:12]],
        "how_to_read": ("obstruction_angle_deg = atan(height / distance) measured from ground "
                        "level at the point. Over 45 degrees means the neighbour fills more than "
                        "half that slice of sky from a low floor; the angle shrinks by roughly "
                        "atan((height - floor_height) / distance) as you go up. height_m_estimate "
                        "is a tagged height where OSM has one and otherwise levels x %.1f m."
                        % STOREY_M)}

    tp = out["trunk_or_primary_road"]["nearest"]
    out["facade_note"] = (FACADE_NOTE if tp and tp["distance_m"] is not None
                          and tp["distance_m"] <= FACADE_TRIGGER_M else None)
    out["facade_note_trigger_m"] = FACADE_TRIGGER_M

    empty = [k for k in ("trunk_or_primary_road", "secondary_road", "railway_surface",
                         "railway_tunnel_portal", "tube_surface", "helipad_or_aerodrome",
                         "night_economy", "food_smell_sources", "waste_or_recycling",
                         "supermarket", "park_or_green")
             if not out[k]["count"]]
    if empty:
        out["not_found"] = {
            "what": empty, "query": query,
            "meaning": "nothing of these kinds is mapped in OpenStreetMap inside that radius. "
                       "OSM is crowd-sourced: a missing pub or an untagged building is a gap in "
                       "the map, not proof of a quiet street."}
    return out


def facade_note(lat, lng, radius=300, verbose=False, full=None):
    """Only the road-proximity prompt to check windows, off the same single query."""
    full = full if full is not None else near(lat, lng, radius, verbose=verbose)
    out = dict((k, full.get(k)) for k in
               ("source_url", "http_status", "ok", "note", "retrieved_at", "evidence_class",
                "attribution", "point", "radius_m", "overpass_instance", "attempts",
                "query_used"))
    out["trunk_or_primary_road"] = (full.get("trunk_or_primary_road") or {}).get("nearest")
    out["secondary_road"] = (full.get("secondary_road") or {}).get("nearest")
    out["facade_note_trigger_m"] = FACADE_TRIGGER_M
    out["facade_note"] = full.get("facade_note")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print curl commands to stderr")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("near", "everything around the point"),
                           ("facade-note", "just the road-proximity prompt to check windows")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--lat", type=float, required=True)
        p.add_argument("--lng", type=float, required=True)
        p.add_argument("--radius", type=int, default=300,
                       help="metres for roads, rail and tube (default 300); the other "
                            "categories keep their own fixed radii")
    a = ap.parse_args()
    if a.cmd == "near":
        out = near(a.lat, a.lng, a.radius, verbose=a.verbose)
    else:
        out = facade_note(a.lat, a.lng, a.radius, verbose=a.verbose)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    if not out.get("ok"):
        sys.stderr.write("fetch failed: %s\n" % out.get("note"))
        sys.exit(1)


if __name__ == "__main__":
    main()
