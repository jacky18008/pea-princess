#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One call for "is this street quiet, safe, and is anything being built?": the open registers,
one compact JSON, a plain reading. The model reads this, not the manuals and not the web.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Sources (all open, all already used by the skill's own scripts): postcodes.io for the point,
OpenStreetMap via Overpass for the street itself and for roads, rail, night economy and parks
within 300 m, Defra's strategic noise maps for modelled road (and rail) noise in dB, data.police.uk
for crime in a ~300 m box over the last six months, the GLA Planning Datahub for applications
within 250 m (500 m at deep), and the 2025 living-environment deciles for the area. Nothing here
reads a listing or review site.

Depth (the summary is the same size at every depth; only the requests and the time differ):
    lite      the given point: four registers + road noise at that point            (~5 requests)
    standard  finds the nearest named street (or --street NAME), moves the scan onto it, samples
              road noise at three points ~120 m apart along it, adds the 2017 noise band and the
              stage of the biggest recent planning application                        (~10 requests)
    deep      standard + rail and night-time noise layers, planning within 500 m      (~19 requests)

Usage (replace placeholders with the person's location, never copy sample coordinates):
    area_scan.py --postcode "<full postcode or outward code>" --street "<street name>"
    area_scan.py --postcode "<full postcode>" --depth lite
    area_scan.py --postcode "<outward code>" --street "<street name>" --depth deep --escalation-reason "requested rail/night review"
    area_scan.py --lat <latitude> --lng <longitude> --location-source "<user input or saved geocoder evidence>"

An outward code requires a named street. It is resolved through postcodes.io, then
mapped street geometry supplies a representative midpoint; never use the district
centroid as the flat. A missing or ambiguous named street stops geographic research.

Set VETFLAT_SCAN_RESULT_DIR to a session-owned directory outside a host's temporary call folder.
Otherwise private results live in .pea-state/area-scans under the current working directory.
Identical requests reuse original timestamped observations, including partial/failure snapshots;
they do not silently refresh. Pending/interrupted results never automatically start another scan.
The store holds at most 128 requests with 1 MiB per snapshot. Its hashes detect corruption, not
source truth or malicious edits by this same OS user. Use --no-save only to explicitly opt out.
Each source has a 90-second deadline and the full attempt has 180 seconds by default; both
can be set explicitly up to 240 seconds. Completed source summaries and source timestamps
are checkpointed. A timeout retains available evidence but reports scan_status=timed_out,
never full coverage. ok only means some usable evidence exists. A host may call
area_scan_store.reconcile_running on its mutable store to close abandoned producer leases;
this makes no requests. It must not apply recovery mutations to frozen experiment archives.
VETFLAT_RESEARCH_DEPTH selects the baseline (otherwise standard); changing --depth requires a
recorded --escalation-reason, which is not itself proof of user authorization.

Give --street whenever the street name is known: a postcode or outcode centroid can sit on the
wrong street, and the scan then says how far off it was and runs from the street itself.

Output is one JSON object of about 7-9k characters (2.5-3k tokens) with a fixed shape (schema vet-flat/area-scan/2):
where, street, quiet, noise, crime, works, living_environment, reading (plain sentences), sources,
not_found. Each block carries ok/note from its register; a failed register is reported, never
guessed. Standard library only, Python 3.9; network through the other scripts' _fetch (curl, cached).
"""
from __future__ import unicode_literals

import argparse
import json
import math
import os
import re
import sys
import tempfile
import threading
import signal
import time
import copy
import area_scan_store as scan_store

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import now_iso, fetch_budget  # noqa: E402

SCHEMA = "vet-flat/area-scan/2"
DEFAULT_SCAN_SECONDS = 180
DEFAULT_SOURCE_SECONDS = 90
_scan_context = threading.local()


class ScanBudget:
    """One finite attempt. Only its supervising thread publishes checkpoints."""
    def __init__(self, seconds, source_seconds, checkpoint=None):
        self.deadline = time.monotonic() + seconds
        self.source_seconds = source_seconds
        self.checkpoint = checkpoint
        self.sources = {}
        self.observations = {}
        self.where = {}
        self.street = None
        self.depth = "standard"
        self.workers = []

    def snapshot(self):
        partial = compose(self.where, None, None, None, None, [], street=self.street, depth=self.depth)
        for label, (value, error) in self.observations.items():
            if value is None or label not in ("crime", "planning", "roads", "living", "noise"):
                continue
            args = [None] * 4
            if label != "noise":
                args[("crime", "planning", "roads", "living").index(label)] = value
            try:
                part = compose(self.where, *args, [], noise=value if label == "noise" else None, depth=self.depth)
                for key in ("quiet", "noise", "crime", "works", "living_environment"):
                    if part.get(key) is not None:
                        partial[key] = part[key]
                partial["sources"].extend(part["sources"])
                partial["reading"].extend(part["reading"][:-1])
                partial["not_found"].extend(part["not_found"])
                partial["ok"] = partial["ok"] or part["ok"]
            except Exception as exc:
                partial["not_found"].append("%s checkpoint summary unavailable: %s" % (label, type(exc).__name__))
        for label, progress in self.sources.items():
            if progress["status"] != "complete":
                partial["not_found"].append("%s: %s%s" % (label, progress["status"], ": " + progress["note"] if progress.get("note") else ""))
        partial["source_progress"] = copy.deepcopy(self.sources)
        partial["scan_status"] = "running"
        partial["how_to_use"] = "In-progress checkpoint. Only completed source observations are available; this is not a completed scan. Preserve source gaps and do not start another attempt automatically."
        return {"sources": copy.deepcopy(self.sources), "result": partial}

    def publish(self):
        if self.checkpoint:
            self.checkpoint(self.snapshot())

    def close(self):
        # _fetch cooperatively cancels and reaps owned curl children. A source
        # stuck in arbitrary Python code is a daemon, has no checkpoint writer,
        # and further fetch calls are refused; this is not hostile-code isolation.
        for thread, cancel in self.workers:
            cancel.set()
        deadline = time.monotonic() + .5
        for thread, _ in self.workers:
            thread.join(max(0, deadline - time.monotonic()))
STREET_TYPES = re.compile(r"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)(_link)?$")
TIERS = {"lite": dict(street=False, band=False, rail=False, night=False, planning_radius=None, stages=False),
         "standard": dict(street=True, band=True, rail=False, night=False, planning_radius=None, stages=True),
         "deep": dict(street=True, band=True, rail=True, night=True, planning_radius=500, stages=True)}
STEP_M = 120      # distance between the sampled points along the street
OFF_STREET_M = 40  # beyond this, the given point is called a centroid, not a door
NAMED_RADIUS_M = 1500  # a named street is looked for this far out: an outcode centroid can be a kilometre off
OUTCODE_RE = re.compile(r"^[A-Z]{1,2}[0-9][A-Z0-9]?$")
NOTABLE_SINCE = 2024
NOTABLE_RULE = ("investigation leads since %d, selected by application scale (5+ storeys, 10+ homes, tall-building hint) "
                "or subject (demolition, basement, piling, crane, hoarding, construction/dust plan); explicit existing-use "
                "certificates excluded, small-householder keyword filter applied; nearest first. "
                "Selection does not establish current or imminent works" % NOTABLE_SINCE)
BIG_WORDS = re.compile(r"(?i)demoli(?:tion|sh)\b(?! of the (?:existing |detached )?(?:garage|shed|outbuilding|cycle store|refuse|bin|conservatory|fence|wall|porch))"
                       r"|basement|redevelop|new[- ]build|excavat|piling|crane|hoarding|scaffold"
                       r"|construction (?:logistics|management|environmental|traffic) plan|demolition and construction|\bCEMP\b|\bCMP\b|\bCLP\b|dust management"
                       r"|erection of (?:a |an )?(?:\w+[- ])*(?:building|block|tower|flats|dwellings|houses)"
                       r"|\b(?:three|four|five|six|seven|eight|nine|ten|\d{1,2})[- ]storey")
SMALL_WORDS = re.compile(r"(?i)single[- ]storey|rear extension|side extension|roof extension|dormer|outbuilding|garage|cycle store|refuse|shed|fence|"
                         r"advertisement|signage|shopfront|window|door|conservatory|porch|loft|certificate of lawfulness|tree|hedge")
EXISTING_CERTIFICATE = re.compile(
    r"(?ix)^\s*(?:application\s+for\s+(?:a\s+)?)?(?:"
    r"(?:certificate\s+of\s+(?:lawfulness|lawful\s+(?:use|development))|lawful\s+development\s+certificate)"
    r"[\s(:-]*(?:(?:for|of|in\s+respect\s+of)\s+)?(?:(?:the|an)\s+)?existing\b"
    r"|certificate\s+of\s+existing\s+lawful\s+(?:use|development)\b"
    r"|(?:CLEUD|CLE)\s*$|LDC[\s(:-]+existing\b)")


def _year(text):
    m = re.search(r"(19|20)\d{2}", str(text or ""))
    return int(m.group(0)) if m else None


def _cut(text, n):
    text = (text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n]
    return (cut[:cut.rfind(" ")] if " " in cut[n // 2:] else cut).rstrip(",;:( ") + "…"


def notable_why(r, since=NOTABLE_SINCE):
    """Select recent application subjects/scale for investigation, not evidence of works starting."""
    years = [y for y in (_year(r.get("decision_date")), _year(r.get("valid_date"))) if y]
    if not years or max(years) < since:
        return None
    # A certificate about existing use/development is a legal-status record, even
    # when its subject includes a basement or many homes. Keep it in nearest/raw rows.
    if any(EXISTING_CERTIFICATE.search(str(r.get(k) or "")) for k in
           ("description", "application_type", "application_type_full")):
        return None
    big = ((r.get("storeys") or 0) >= 5 or (r.get("residential_units_proposed") or 0) >= 10 or r.get("tall_building_hint"))
    text = str(r.get("description") or "")
    signal = BIG_WORDS.search(text)
    if big:
        return "application scale: %s" % ", ".join(x for x in (("%s storeys" % r.get("storeys")) if (r.get("storeys") or 0) >= 5 else "",
                                                ("%s homes" % r.get("residential_units_proposed")) if (r.get("residential_units_proposed") or 0) >= 10 else "",
                                                "tall-building hint" if r.get("tall_building_hint") else "") if x)
    if signal and not (SMALL_WORDS.search(text) and not re.search(r"(?i)basement|piling|crane|hoarding|management plan|dust|CEMP|CMP|CLP", text)):
        return "application subject: " + signal.group(0).lower()[:60]
    return None


# ------------------------------------------------------------- the street -------

def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def street_query(lat, lng, radius=250, timeout=25, name=None):
    """Every named street (not paths, footways or service roads) within the radius, with geometry;
    with a name, only that street (case-insensitive), out to a wider radius."""
    if name:
        safe = re.sub(r'[\\"\n]', "", name.strip())
        safe = re.sub(r"([.^$*+?()\[\]{}|])", r"\\\1", safe)   # Overpass regex: escape metacharacters, keep spaces
        return ('[out:json][timeout:%d];way(around:%d,%s,%s)["highway"]["name"~"^%s$",i];out geom;'
                % (timeout, int(radius), lat, lng, safe))
    return ('[out:json][timeout:%d];way(around:%d,%s,%s)["highway"~"^(motorway|trunk|primary|secondary|tertiary|'
            'unclassified|residential|living_street)(_link)?$"]["name"];out geom;' % (timeout, int(radius), lat, lng))


def street_ways(elements, any_highway=False):
    out = []
    for el in elements or []:
        t = el.get("tags") or {}
        if el.get("type") == "way" and t.get("name") and el.get("geometry") and (any_highway or STREET_TYPES.match(str(t.get("highway") or ""))):
            out.append(el)
    return out


def _lines(el):
    return [[(g["lat"], g["lon"]) for g in el.get("geometry") or [] if g.get("lat") is not None]]


def join_lines(lines, tol_m=1.5):
    """Chain polylines whose ends meet (OSM splits a street at every junction) into longer ones."""
    lines = [list(l) for l in lines if len(l) >= 2]
    changed = True
    while changed and len(lines) > 1:
        changed = False
        for i in range(len(lines)):
            for j in range(len(lines)):
                if i == j:
                    continue
                a, b = lines[i], lines[j]
                if haversine_m(a[-1][0], a[-1][1], b[0][0], b[0][1]) <= tol_m:
                    lines[i] = a + b[1:]
                elif haversine_m(a[-1][0], a[-1][1], b[-1][0], b[-1][1]) <= tol_m:
                    lines[i] = a + list(reversed(b))[1:]
                elif haversine_m(a[0][0], a[0][1], b[-1][0], b[-1][1]) <= tol_m:
                    lines[i] = b + a[1:]
                elif haversine_m(a[0][0], a[0][1], b[0][0], b[0][1]) <= tol_m:
                    lines[i] = list(reversed(b)) + a[1:]
                else:
                    continue
                del lines[j]
                changed = True
                break
            if changed:
                break
    return lines


def connected_street_lines(lines, tol_m=1.5):
    """Check shared vertices, including junctions inside ways; keep ordering deterministic.

    A named side loop may meet the main way at interior vertices. It is part of
    the same mapped network, but it need not be part of the sampled chain.
    Nearby parallel/disconnected roads are not silently bridged.
    """
    lines = sorted(min(list(line), list(reversed(line))) for line in lines if len(line) >= 2)
    if not lines:
        return None
    reached, pending = {0}, set(range(1, len(lines)))
    while pending:
        linked = {j for j in pending if any(
            haversine_m(*a, *b) <= tol_m
            for i in reached for a in lines[i] for b in lines[j])}
        if not linked:
            return None
        reached.update(linked)
        pending.difference_update(linked)
    return join_lines(lines)


def _nearest_on_segment(plat, plng, a, b):
    """(distance_m, lat, lng, fraction) of the closest point on segment a-b, in a local flat frame."""
    kx = math.cos(math.radians(plat)) * 111320.0
    ky = 110540.0
    ax, ay = (a[1] - plng) * kx, (a[0] - plat) * ky
    bx, by = (b[1] - plng) * kx, (b[0] - plat) * ky
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    f = 0.0 if l2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / l2))
    x, y = ax + f * dx, ay + f * dy
    return math.hypot(x, y), a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), f


def anchor_on_line(line, lat, lng):
    """(distance_m, (lat, lng), segment_index) of the closest point of the polyline."""
    best = (float("inf"), None, None)
    for i in range(len(line) - 1):
        d, plat, plng, _ = _nearest_on_segment(lat, lng, line[i], line[i + 1])
        if d < best[0]:
            best = (d, (plat, plng), i)
    return best


def walk(line, seg, start, step_m, forward=True):
    """The point step_m along the polyline from start (which lies on segment seg); clamps at the end."""
    remaining, cur = float(step_m), start
    idx, stride = (seg + 1, 1) if forward else (seg, -1)
    while 0 <= idx < len(line):
        nxt = line[idx]
        d = haversine_m(cur[0], cur[1], nxt[0], nxt[1])
        if d >= remaining and d > 0:
            f = remaining / d
            return (cur[0] + (nxt[0] - cur[0]) * f, cur[1] + (nxt[1] - cur[1]) * f), True
        remaining -= d
        cur = nxt
        idx += stride
    return cur, False


def sample_points(line, lat, lng, step_m=STEP_M):
    """[anchor, one point step_m back, one point step_m forward] along the street, deduplicated."""
    d, anchor, seg = anchor_on_line(line, lat, lng)
    if anchor is None:
        return []
    back, _ = walk(line, seg, anchor, step_m, forward=False)
    fwd, _ = walk(line, seg, anchor, step_m, forward=True)
    pts = [anchor]
    for p in (back, fwd):
        if all(haversine_m(p[0], p[1], q[0], q[1]) > 15 for q in pts):
            pts.append(p)
    return pts


def polyline_length_m(line):
    return sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(line[:-1], line[1:]))


def choose_street(elements, lat, lng, name=None):
    """The nearest named street (or the one called `name`): (name, highway, offset_m, joined_line, ways)."""
    ways = street_ways(elements)
    if name:
        want = name.strip().lower()
        ways = [w for w in ways if w["tags"]["name"].strip().lower() == want]
        if not ways:  # a named street may be mapped as pedestrian or a path: accept any highway type when asked by name
            ways = [w for w in street_ways(elements, any_highway=True) if w["tags"]["name"].strip().lower() == want]
    if not ways:
        return None
    by_name = {}
    for w in ways:
        by_name.setdefault(w["tags"]["name"].strip().casefold(), []).append(w)
    best = None
    for _, group in sorted(by_name.items()):
        n = min(w["tags"]["name"].strip() for w in group)
        lines = join_lines([l for w in group for l in _lines(w)])
        for line in lines:
            d, anchor, seg = anchor_on_line(line, lat, lng)
            if anchor is not None and (best is None or d < best[2]):
                best = (n, group[0]["tags"].get("highway"), d, line, group)
    return best


def find_street(lat, lng, name=None, radius=250, verbose=False, runner=None, representative=False):
    """One Overpass request; the street block for the scan (ok False, never a guess, when nothing fits)."""
    import roads as roads_mod
    if name:
        radius = max(radius, NAMED_RADIUS_M)
    query = street_query(lat, lng, radius, name=name)
    data, meta = (runner or roads_mod.run_overpass)(query, verbose=verbose)
    out = {"ok": False, "name": name, "note": "", "source_url": (meta or {}).get("source_url"), "retrieved_at": (meta or {}).get("retrieved_at"), "query": query}
    if not data:
        out["note"] = (meta or {}).get("note") or "overpass unavailable"
        return out
    best = choose_street(data.get("elements") or [], lat, lng, name)
    if not best:
        out["note"] = "no named street within %d m%s" % (radius, (" called %r" % name) if name else "")
        return out
    n, highway, d, line, group = best
    if representative:
        components = connected_street_lines([part for way in group for part in _lines(way)])
        if not components:
            out["note"] = "Named street has disconnected mapped sections; need a more precise location."
            return out
        # Deterministic longest end-joined chain; other connected branches are
        # explicitly outside the noise-sample route, not folded into its values.
        line = min(components, key=lambda part: (-polyline_length_m(part), part))
        midpoint, _ = walk(line, 0, line[0], polyline_length_m(line) / 2)
        if haversine_m(lat, lng, *midpoint) > radius:
            out["note"] = "The mapped way extends beyond this location search; its representative midpoint is outside the search radius. Need a more precise location."
            return out
        pts = sample_points(line, *midpoint)
        d = haversine_m(lat, lng, *pts[0])
        out["location_coverage"] = {
            "lookup_radius_m": radius, "joined_chains": len(components),
            "mapped_total_length_m": int(sum(polyline_length_m(part) for part in components)),
            "sample_route_length_m": int(polyline_length_m(line)),
            "note": "Representative points on the longest connected mapped chain returned by this query; not the whole street or a known home. Other branches are not noise-sampled. The outward code is a search seed, not proof of the street's postal district."}
    else:
        pts = sample_points(line, lat, lng)
    out.update({"ok": True, "name": n, "highway": highway, "offset_m": int(round(d)),
                "anchor": {"lat": round(pts[0][0], 6), "lng": round(pts[0][1], 6)},
                "points": [{"lat": round(a, 6), "lng": round(b, 6)} for a, b in pts],
                "mapped_length_m": int(polyline_length_m(line)), "ways": len(group),
                "anchor_method": ("mapped_street_midpoint" if len(components) == 1 else "longest_connected_chain_midpoint") if representative else "nearest_point_on_mapped_street"})
    return out


def _safe(fn, *a, **kw):
    try:
        return fn(*a, **kw), None
    except Exception as exc:  # noqa: BLE001 — one failed register must not sink the scan
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:160])


def nearest_m(block):
    n = (block or {}).get("nearest") or {}
    return n.get("distance_m") if isinstance(n, dict) else None


def names(block, limit=3):
    return [str(x)[:60] for x in ((block or {}).get("names") or [])[:limit]]


def compose(where, crime, planning, roads, living, notes, noise=None, street=None, depth="standard"):
    """The fixed shape, from the raw outputs of the register scripts (any may be None)."""
    out = {"how_to_use": "Use the available observations in this JSON; check scan_status and source gaps before claiming coverage. Do not read this script's source, the cache, or the registers again, and do not run crime.py, planning.py, roads.py, noise.py or living_env.py for the same point.",
           "schema": SCHEMA, "ok": True, "retrieved_at": now_iso(), "depth": depth, "where": where,
           "street": None, "quiet": None, "noise": None, "crime": None, "works": None, "living_environment": None,
           "reading": [], "sources": [], "not_found": list(notes)}
    reading = out["reading"]

    if street and street.get("ok"):
        st = {"name": street.get("name"), "type": street.get("highway"), "given_point_offset_m": street.get("offset_m"),
              "points_sampled": len(street.get("points") or []), "mapped_length_m": street.get("mapped_length_m"),
              "scan_point": street.get("anchor")}
        out["street"] = st
        out["sources"].append(street.get("source_url"))
        off = st["given_point_offset_m"] or 0
        if off > OFF_STREET_M:
            reading.append("The given point is %d m from %s: a centroid, not a door. The registers were run from the street itself and noise was sampled at %d points about %d m apart along it." % (
                off, st["name"], st["points_sampled"], STEP_M))
        else:
            reading.append("Street: %s (%s), %d m from the given point; noise sampled at %d points about %d m apart along it." % (
                st["name"], st["type"] or "road", off, st["points_sampled"], STEP_M))
    elif street is not None:
        out["not_found"].append("street: " + str(street.get("note") or "not found") + "; the scan ran from the given point")

    if roads and roads.get("ok"):
        q = {"main_road_nearest_m": nearest_m(roads.get("trunk_or_primary_road")),
             "main_road_names": names(roads.get("trunk_or_primary_road")),
             "secondary_road_nearest_m": nearest_m(roads.get("secondary_road")),
             "railway_surface_nearest_m": nearest_m(roads.get("railway_surface")),
             "tube_surface_nearest_m": nearest_m(roads.get("tube_surface")),
             "night_economy_count": (roads.get("night_economy") or {}).get("count"),
             "night_economy_radius_m": (roads.get("night_economy") or {}).get("search_radius_m"),
             "night_economy_nearest_m": nearest_m(roads.get("night_economy")),
             "night_economy_names": names(roads.get("night_economy")),
             "park_nearest_m": nearest_m(roads.get("park_or_green")),
             "facade_note": roads.get("facade_note"), "radius_m": roads.get("radius_m")}
        out["quiet"] = q
        out["sources"].append(roads.get("source_url"))
        main = q["main_road_nearest_m"]
        rail = [d for d in (q["railway_surface_nearest_m"], q["tube_surface_nearest_m"]) if d is not None]
        def extent(radius):
            return "%s m" % radius if radius is not None else "the queried area (radius not reported)"
        road_radius = (roads.get("trunk_or_primary_road") or {}).get("search_radius_m") or q["radius_m"]
        rail_radius = (roads.get("railway_surface") or {}).get("search_radius_m") or q["radius_m"]
        night_radius = q["night_economy_radius_m"]
        night_count = q["night_economy_count"]
        reading.append("Roads (OSM query returned): %s%s. Rail at surface: %s. Bars, pubs and clubs in the OSM query within %s: %s mapped%s%s." % (
            ("nearest main road %s at %d m" % (q["main_road_names"][0], main)) if main is not None and q["main_road_names"] else
            ("nearest main road at %d m" % main) if main is not None else "none listed in this map/query within %s" % extent(road_radius),
            ("; a secondary road at %d m" % q["secondary_road_nearest_m"]) if q["secondary_road_nearest_m"] is not None else "",
            ("nearest at %d m" % min(rail)) if rail else "none listed in this map/query within %s" % extent(rail_radius),
            extent(night_radius), night_count if night_count is not None else "unknown",
            (" (nearest %s at %d m)" % (q["night_economy_names"][0], q["night_economy_nearest_m"])) if q["night_economy_names"] and q["night_economy_nearest_m"] is not None else "",
            " (zero mapped here does not prove no venues exist)" if night_count == 0 else ""))
        if q["facade_note"]:
            reading[-1] += (" Road proximity is a prompt to check window direction and sound insulation; "
                            "it does not establish the flat's facade orientation or a quiet side.")
    elif roads is not None:
        out["not_found"].append("roads: " + str(roads.get("note") or "register unavailable"))

    if crime and crime.get("ok"):
        cats = sorted((crime.get("by_category") or {}).items(), key=lambda kv: -kv[1])[:5]
        months = crime.get("months_counted") or crime.get("months_fetched") or len(crime.get("per_month") or {})
        total = crime.get("total")
        pred = crime.get("predatory_subset") or {}
        c = {"total": total, "months": months, "per_month_avg": (round(total / months, 1) if total is not None and months else None),
             "top_categories": [{"category": k, "count": v} for k, v in cats if v],
             "wider_box": crime.get("wider_box"),
             "predatory_share": pred.get("share_of_total"), "box_half_m": (crime.get("query") or {}).get("half_m"),
             "latest_month": crime.get("latest_available_month"), "months_missing": crime.get("months_missing")}
        out["crime"] = c
        out["sources"].append(crime.get("source_url"))
        if total:
            reading.append("Crime: %s recorded in %s months in a box about %d m across (%s a month); the four categories a resident meets on the street make up %s%%; biggest: %s." % (
                total, months, int((c["box_half_m"] or 150) * 2), c["per_month_avg"],
                int(round((pred.get("share_of_total") or 0) * 100)), ", ".join("%s %d" % (k, v) for k, v in cats[:3] if v) or "none"))
        else:
            wb = c.get("wider_box") or {}
            reading.append("Crime: none recorded in %s months in a box about %d m across%s. Police map points are snapped to a few street locations, so a small box can be empty while the street is ordinary; use the wider figure." % (
                months, int((c["box_half_m"] or 150) * 2),
                ("; %s in a box about %d m across" % (wb.get("total"), int(wb["half_m"] * 2))) if wb.get("total") is not None else ""))
    elif crime is not None:
        out["not_found"].append("crime: " + str(crime.get("note") or "register unavailable"))

    if planning and planning.get("ok"):
        rows = planning.get("results") or []
        rows = sorted(rows, key=lambda r: (r.get("distance_m") in (None, ""), r.get("distance_m") or 0))
        keep = ("reference", "address", "description", "status", "decision_date", "distance_m", "storeys", "residential_units_proposed")
        def brief(r):
            b = {k: (_cut(r.get(k), 64 if k == "description" else 40) if k in ("address", "description") else r.get(k)) for k in keep}
            # Optional fields may be absent even in full records; zero metres is known.
            return {k: v for k, v in b.items() if v not in (None, "")}
        def label(r):
            return r.get("description") or r.get("reference") or r.get("address") or "description unavailable"
        def distance(r):
            return "%s m" % r["distance_m"] if r.get("distance_m") not in (None, "") else "distance unknown"
        top = [brief(r) for r in rows[:5]]
        notable, sites = [], {}
        for r in rows:
            why = notable_why(r)
            if not why:
                continue
            site = re.sub(r"\W+", " ", str(r.get("address") or "")).strip().lower()[:40] or r.get("reference")
            if site and site in sites:   # condition discharges and amendments for one permission: count them, list the site once
                sites[site]["related_submissions"] += 1
                continue
            b = brief(r)
            b["why"], b["related_submissions"] = why, 0
            if site:
                sites[site] = b
            notable.append(b)
        notable = notable[:3]
        seen = len(rows)
        total = planning.get("total_matching") or planning.get("count") or seen
        distances = [r["distance_m"] for r in rows if r.get("distance_m") not in (None, "")]
        far = max(distances) if distances and len(distances) == seen else None
        w = {"applications_within_m": planning.get("radius_m"), "count": total, "rows_seen": seen,
             "seen_out_to_m": int(far) if far is not None and total and seen < total else None, "since_year": planning.get("since_year"),
             "tall_building_hints": sum(1 for r in rows if r.get("tall_building_hint")), "nearest_five": top,
             "notable_recent": notable, "notable_rule": NOTABLE_RULE}
        w["coverage"] = {"requested_radius_m": planning.get("radius_m"), "rows_read": seen,
                         "total_matching": total, "all_matching_rows_read": seen >= total,
                         "furthest_read_m": far, "distance_origin": "street scan point, not a flat door"}
        if seen < total:
            out["not_found"].append("planning coverage: only %s of %s matching rows read within %s m; furthest read distance %s m; unreturned rows remain unknown" %
                                    (seen, total, planning.get("radius_m"), far if far is not None else "unknown"))
        out["works"] = w
        out["sources"].append(planning.get("source_url"))
        reading.append("Works: %s planning applications within %s m since %s%s, %s with a tall-building hint; the nearest: %s. Investigation leads (%s): %s. These application records do not establish current or imminent works." % (
            w["count"], w["applications_within_m"], w["since_year"],
            (" (the nearest %d read, out to %d m)" % (seen, far)) if w["seen_out_to_m"] is not None else "", w["tall_building_hints"],
            ("%s, %s (%s)" % (label(top[0]), top[0].get("status") or "status unknown", distance(top[0]))) if top else "none returned by this query",
            "since %d, selected by application scale or subject" % NOTABLE_SINCE,
            "; ".join("%s at %s (%s, %s; %s%s)" % (label(n), distance(n), n.get("status") or "status unknown", n.get("decision_date") or "no decision date", n["why"],
                                                     (", +%d related submissions for the same site" % n["related_submissions"]) if n["related_submissions"] else "") for n in notable[:3]) or "none selected from returned records"))
    elif planning is not None:
        out["not_found"].append("planning: " + str(planning.get("note") or "register unavailable"))

    if noise is not None:
        sm = noise.get("summary") or {}
        attempted = len(noise.get("points") or [])
        noise_coverage = {k: {"attempted": attempted, "numeric_values": v.get("n", 0),
                             "not_drawn": v.get("not_drawn", 0),
                             "successful": v.get("n", 0) + v.get("not_drawn", 0),
                             "failed": max(0, attempted - v.get("n", 0) - v.get("not_drawn", 0))}
                          for k, v in sm.items() if isinstance(v, dict)}
        nz = {"road_lden_db": (sm.get("road_lden_db") or {}).get("at_point"),
              "road_lden_range_db": [(sm.get("road_lden_db") or {}).get("min"), (sm.get("road_lden_db") or {}).get("max")],
              "road_lnight_db": (sm.get("road_lnight_db") or {}).get("at_point") if sm.get("road_lnight_db") else None,
              "rail_lden_db": (sm.get("rail_lden_db") or {}).get("at_point") if sm.get("rail_lden_db") else None,
              "rail_not_drawn": (sm.get("rail_lden_db") or {}).get("not_drawn") if sm.get("rail_lden_db") else None,
              "band_2017_road": ((noise.get("band_2017") or {}).get("road_lden")),
              "points": attempted, "scale": noise.get("scale"), "available": bool(noise.get("ok")),
              "coverage": noise_coverage}
        out["noise"] = nz
        out["sources"].extend(noise.get("sources") or [])
        reading.extend([r for r in (noise.get("reading") or []) if not r.startswith("These are modelled")])
        out["not_found"].extend("noise: " + x for x in (noise.get("not_found") or []))
        for layer, cov in noise_coverage.items():
            text = "Noise coverage %s: %s/%s requests succeeded (%s numeric, %s not drawn); %s failed." % (
                layer, cov["successful"], cov["attempted"], cov["numeric_values"], cov["not_drawn"], cov["failed"])
            reading.append(text)
            if cov["failed"]:
                out["not_found"].append(text)
        if not noise.get("ok") and not noise.get("not_found"):
            out["not_found"].append("noise: map unavailable")

    if living and living.get("ok"):
        le = {"outdoors_decile": (living.get("outdoors") or {}).get("decile"), "indoors_decile": (living.get("indoors") or {}).get("decile"),
              "area": (living.get("lsoa") or {}).get("name"), "how_to_use": "context, never a filter"}
        out["living_environment"] = le
        out["sources"].append(living.get("source_url"))
        reading.append("Living environment (2025 indices, area of about 1,500 people): outdoors decile %s of 10 for air quality and road accidents, indoors decile %s for housing condition; 1 is the worst tenth in England, and inner London sits low outdoors almost everywhere." % (
            le["outdoors_decile"], le["indoors_decile"]))
    elif living is not None:
        out["not_found"].append("living environment: " + str(living.get("note") or "table unavailable"))

    reading.append("Quiet and safety are different questions: the roads, rail, night-economy and noise lines answer quiet; the crime line answers safety and says nothing about noise. All of this is the area around the point, not the flat: nothing here says which way any window faces or what is heard indoors.")
    if ((where or {}).get("how_located") or "").startswith("lat/lng given") and not (street and street.get("ok")):
        reading.append("The point was given as coordinates: if it is an area centroid rather than a door, every distance is a rough guide; a scan with --street NAME runs from the street itself.")
    out["sources"] = [s for s in out["sources"] if s]
    out["ok"] = any(x is not None for x in (out["quiet"], out["crime"], out["works"], out["living_environment"])) or bool(noise and noise.get("ok"))
    return out


def add_stage(out, planning_raw, verbose=False):
    """Standard and deep: the stage of the biggest recent application, from planning.py stages (one request)."""
    import planning as planning_mod
    w = out.get("works") or {}
    top = (w.get("notable_recent") or [None])[0]
    if not top or not top.get("reference"):
        return
    lpa = None
    for r in (planning_raw or {}).get("results") or []:
        if r.get("reference") == top["reference"]:
            lpa = r.get("lpa_name")
            break
    s, err = _call("planning_stage", planning_mod.stages, top["reference"], lpa, verbose=verbose)
    if err or not s or s.get("ok") is False or not s.get("record"):
        out["not_found"].append("stage of %s: %s" % (top["reference"], err or (s or {}).get("note") or "not found"))
        return
    means = [m for m in (s.get("what_this_means") or []) if m][:3]
    w["top_notable_stage"] = {"reference": top["reference"], "status": (s.get("record") or {}).get("status"),
                              "what_this_means": [m[:200] for m in means], "portal_url": (s.get("conditions") or {}).get("portal_url")}
    if means:
        out["reading"].insert(min(3, len(out["reading"])), "The biggest recent application nearby, %s at %s m: %s" % (
            top["reference"], top.get("distance_m"), " ".join(means)[:400]))


def _bounded_jobs(jobs):
    """Finite concurrent source attempts; expired sources do not erase neighbours."""
    budget = getattr(_scan_context, "budget", None)
    own_budget = budget is None
    budget = budget or ScanBudget(DEFAULT_SCAN_SECONDS, DEFAULT_SOURCE_SECONDS)
    results, active = {}, {}
    completions = {}
    completion_ready = threading.Condition()
    def run(name, fn, args, kwargs, deadline, cancelled):
        with fetch_budget(deadline, cancelled):
            value = _safe(fn, *args, **kwargs)
        # Completion publication and deadline expiry share a short lock. There
        # is no disk I/O under it. A slow checkpoint must not age a queued result
        # into a timeout or discard its already finished neighbours.
        with completion_ready:
            completions[name] = (value, time.monotonic(), now_iso())
            completion_ready.notify()
    try:
        for name, (fn, args, kwargs) in jobs.items():
            started = now_iso()
            deadline = min(budget.deadline, time.monotonic() + budget.source_seconds)
            if deadline <= time.monotonic():
                results[name] = (None, "scan deadline reached before source started; no request made")
                budget.sources[name] = {"status": "timed_out", "started_at": None, "finished_at": started, "note": results[name][1]}
                continue
            cancelled = threading.Event()
            thread = threading.Thread(target=run, args=(name, fn, args, kwargs, deadline, cancelled), daemon=True)
            budget.sources[name] = {"status": "running", "started_at": started, "finished_at": None}
            active[name] = (deadline, cancelled)
            budget.workers.append((thread, cancelled))
            thread.start()
        budget.publish()
        while active:
            changed = False
            with completion_ready:
                if not completions:
                    completion_ready.wait(timeout=max(0, min(.1, min(x[0] for x in active.values()) - time.monotonic())))
                for name, (value, completed_at, finished_at) in list(completions.items()):
                    if name not in active:
                        continue
                    deadline, cancelled = active.pop(name)
                    if completed_at >= deadline:
                        value = (None, "source deadline reached; no automatic retry")
                        status = "timed_out"
                        cancelled.set()
                    else:
                        status = "failed" if value[1] or (isinstance(value[0], dict) and value[0].get("ok") is False) else "complete"
                    results[name] = value
                    budget.observations[name] = value
                    note = value[1]
                    if not note and isinstance(value[0], dict):
                        note = str(value[0].get("note", ""))[:300]
                    budget.sources[name].update(status=status, finished_at=finished_at, note=note)
                    changed = True
                completions.clear()
                # All available completions are adopted before expiring remaining
                # jobs; workers cannot publish between this drain and the sweep.
                for name, (deadline, cancelled) in list(active.items()):
                    if time.monotonic() >= deadline:
                        cancelled.set()
                        results[name] = (None, "source deadline reached; no automatic retry")
                        budget.sources[name].update(status="timed_out", finished_at=now_iso(), note=results[name][1])
                        active.pop(name)
                        changed = True
            if changed:
                budget.publish()
        return results
    finally:
        for _, cancelled in active.values():
            cancelled.set()
        if own_budget:
            budget.close()


def _parallel(jobs):
    return _bounded_jobs(jobs)


def _call(name, fn, *args, **kwargs):
    return _bounded_jobs({name: (fn, args, kwargs)})[name]


def result_path(postcode, lat, lng, street, depth):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", (street or postcode or "%s-%s" % (lat, lng))).strip("-").lower()[:40]
    return os.path.join(tempfile.gettempdir(), "vet-flat-scan-%s-%s.json" % (slug or "point", depth))


def validate_location(postcode, lat, lng, street, location_source):
    """Shared CLI/import boundary; invalid inputs must not reach network calls."""
    if (lat is None) != (lng is None):
        raise ValueError("supply both coordinates, or use --postcode with --street")
    if lat is not None:
        if (type(lat) not in (int, float) or type(lng) not in (int, float)
                or not math.isfinite(lat) or not math.isfinite(lng)
                or not -90 <= lat <= 90 or not -180 <= lng <= 180):
            raise ValueError("coordinates must be finite latitude/longitude")
        if not isinstance(location_source, str) or not location_source.strip():
            raise ValueError("coordinates need --location-source; never use guessed or example coordinates. Prefer --postcode plus --street.")
    if not postcode and lat is None:
        raise ValueError("give --postcode or --lat and --lng")
    if postcode and OUTCODE_RE.fullmatch(str(postcode).strip().upper()) and not (street or "").split(",", 1)[0].strip():
        raise ValueError("an outward code needs --street; do not scan a district centroid as a home")


def _scan(postcode=None, lat=None, lng=None, months=6, crime_half_m=150, planning_radius=250, roads_radius=300,
         depth="standard", street=None, verbose=False, announce=None, location_source=None):
    import geo, crime as crime_mod, planning as planning_mod, roads as roads_mod, living_env, noise as noise_mod  # noqa: E402
    validate_location(postcode, lat, lng, street, location_source)
    tier = TIERS.get(depth) or TIERS["standard"]
    notes = []
    if announce:
        announce("area_scan: %s, depth %s. Independent registers are queried in parallel; wait for this run, do not start a duplicate.\n" % (
            street or postcode or "%s,%s" % (lat, lng), depth))
    coarse = bool(postcode and OUTCODE_RE.fullmatch(str(postcode).strip().upper()))
    requested_street = street
    # Brochure headings commonly append district and postcode after commas.
    if street and "," in street:
        street = street.split(",", 1)[0].strip()
    if coarse and not street:
        raise ValueError("an outward code needs --street; a district centroid is not a property")
    where = {"postcode": postcode, "lat": lat, "lng": lng, "district": None, "how_located": "lat/lng given" if lat is not None else None}
    budget = getattr(_scan_context, "budget", None)
    if budget:
        budget.where, budget.depth = where, depth
    if lat is None or lng is None:
        if not postcode:
            raise ValueError("give --postcode or --lat and --lng")
        g, err = _call("location", geo.lookup_outcode if coarse else geo.lookup, postcode, verbose)
        if err or not g or not g.get("ok"):
            return {"schema": SCHEMA, "ok": False, "retrieved_at": now_iso(), "where": where,
                    "note": "postcode not located: %s" % (err or (g or {}).get("note")), "reading": [], "sources": [], "not_found": ["postcode lookup"]}
        lat, lng = g["lat"], g["lng"]
        where.update({"lat": lat, "lng": lng, "district": g.get("admin_district"), "ward": g.get("admin_ward"),
                      "how_located": "outcode centroid resolved through postcodes.io; locating named street" if coarse else "postcode centroid via postcodes.io (tens of metres off a door)",
                      "location_source": {"source_url": g.get("source_url"), "retrieved_at": g.get("retrieved_at"), "precision": "postal_district" if coarse else "postcode"}})
    elif location_source:
        where["location_source"] = {"caller_reference": location_source, "verified": False}
    st = None
    at_lat, at_lng, pts = lat, lng, [(lat, lng)]
    if tier["street"] or street:
        street_options = {"verbose": verbose}
        if coarse:
            street_options["representative"] = True
        st, e0 = _call("street", find_street, lat, lng, street, **street_options)
        if e0:
            st = {"ok": False, "name": street, "note": e0}
        if budget:
            budget.street = st
        if st and st.get("ok"):
            at_lat, at_lng = st["anchor"]["lat"], st["anchor"]["lng"]
            pts = [(p["lat"], p["lng"]) for p in st["points"]]
            where["scan_point"] = {"lat": at_lat, "lng": at_lng, "why": "mapped street midpoint" if coarse else "moved onto %s" % st["name"]}
            where["street_location"] = {"requested_label": requested_street, "matched_name": st["name"],
                "source_url": st.get("source_url"), "retrieved_at": st.get("retrieved_at"), "query": st.get("query"),
                "method": st.get("anchor_method"), "coverage": st.get("location_coverage"), "property_location_known": False}
        elif street:
            return {"schema": SCHEMA, "ok": False, "retrieved_at": now_iso(), "where": where,
                    "street": st, "note": "Named street not established; no geographic registers queried. " + str((st or {}).get("note", "")),
                    "reading": [], "sources": [], "not_found": ["named street location"]}
    if coarse:
        notes.append("Outward code and mapped street midpoint only; exact home unknown. Distances use that midpoint and can vary along the street.")
    pr = tier["planning_radius"] or planning_radius
    # sensitivity=False: the centre box only (6 monthly requests, not 30 with the four 20 m shifts): a street
    # scan wants the count and its denominator, not the shift analysis, and the police API is ~6 s a request
    jobs = {"crime": (crime_mod.box, (at_lat, at_lng, crime_half_m, months), {"verbose": verbose, "sensitivity": False}),
            "planning": (planning_mod.near, (at_lat, at_lng, pr), {"verbose": verbose}),
            "roads": (roads_mod.near, (at_lat, at_lng, roads_radius), {"verbose": verbose}),
            "noise": (noise_mod.lookup, (pts,), {"rail": tier["rail"], "night": tier["night"], "with_band": tier["band"], "verbose": verbose})}
    if postcode and not coarse:
        jobs["living"] = (living_env.lookup, (), {"postcode": postcode, "verbose": verbose})
    got = _parallel(jobs)
    c, e1 = got["crime"]
    p, e2 = got["planning"]
    r, e3 = got["roads"]
    n, e5 = got["noise"]
    l, e4 = got["living"] if postcode and not coarse else (None, "living environment needs a full property postcode")
    if c and c.get("ok") and not c.get("total"):
        wide, e1b = _call("crime_wider_box", crime_mod.box, at_lat, at_lng, crime_half_m * 2, months, verbose=verbose, sensitivity=False)
        if wide and wide.get("ok"):
            c["wider_box"] = {"half_m": crime_half_m * 2, "total": wide.get("total"), "months": wide.get("months_counted")}
    for name, err in (("crime", e1), ("planning", e2), ("roads", e3), ("noise", e5), ("living environment", e4)):
        if err:
            notes.append("%s: %s" % (name, err))
    try:
        out = compose(where, c, p, r, l, notes, noise=n, street=st, depth=depth)
    except Exception as exc:
        # A malformed register must not discard successfully retrieved neighbours.
        out = compose(where, None, None, None, None, notes, street=st, depth=depth)
        out["not_found"].append("combined summary failed: %s; preserving independent register summaries" % type(exc).__name__)
        for label, values in (("crime", (c, None, None, None, None)), ("planning", (None, p, None, None, None)),
                              ("roads", (None, None, r, None, None)), ("living", (None, None, None, l, None)),
                              ("noise", (None, None, None, None, n))):
            if not any(v is not None for v in values):
                continue
            try:
                part = compose(where, *values[:4], [], noise=values[4], depth=depth)
                for key in ("quiet", "noise", "crime", "works", "living_environment"):
                    if part.get(key) is not None:
                        out[key] = part[key]
                out["sources"].extend(part["sources"])
                out["not_found"].extend(part["not_found"])
                out["reading"].extend(part["reading"][:-1])
                out["ok"] = out["ok"] or part["ok"]
            except Exception as part_exc:
                out["not_found"].append("%s summary unavailable: %s" % (label, type(part_exc).__name__))
    if coarse:
        out["reading"].insert(0, "Using the mapped street midpoint, not a known home location. Distances and sampled values can differ elsewhere along this street.")
    if tier["stages"]:
        try:
            add_stage(out, p, verbose=verbose)
        except Exception as exc:
            out["not_found"].append("planning stage summary unavailable: %s" % type(exc).__name__)
    return out


def scan(postcode=None, lat=None, lng=None, months=6, crime_half_m=150, planning_radius=250, roads_radius=300,
         depth="standard", street=None, verbose=False, announce=None, location_source=None,
         deadline_seconds=DEFAULT_SCAN_SECONDS, source_timeout_seconds=DEFAULT_SOURCE_SECONDS, checkpoint=None):
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 < v <= 240
               for v in (deadline_seconds, source_timeout_seconds)):
        raise ValueError("scan and source deadlines must be positive, at most 240 seconds")
    budget = ScanBudget(deadline_seconds, source_timeout_seconds, checkpoint)
    previous = getattr(_scan_context, "budget", None)
    _scan_context.budget = budget
    try:
        out = _scan(postcode, lat, lng, months, crime_half_m, planning_radius, roads_radius,
                    depth, street, verbose, announce, location_source)
        out["source_progress"] = copy.deepcopy(budget.sources)
        timed_out = [name for name, item in budget.sources.items() if item["status"] == "timed_out"]
        if timed_out:
            out["scan_status"] = "timed_out"
            out.setdefault("not_found", []).append("Incomplete scan: source deadline reached for %s; retained completed evidence, no automatic retry." % ", ".join(timed_out))
        else:
            out["scan_status"] = "failed" if not out.get("ok") else ("partial" if out.get("not_found") else "complete")
        out["how_to_use"] = "Scan status: %s. %s" % (out["scan_status"], out.get("how_to_use") or "Use only the available observations, preserve missing sources, and do not retry automatically.")
        return out
    finally:
        budget.close()
        _scan_context.budget = previous


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Run it once per street and write from the JSON; check scan_status and source gaps before claiming coverage. --depth is the person's budget mode; standard when unknown. Reading this file's source or the cache adds nothing.")
    ap.add_argument("--postcode", help="full postcode, or outward code with --street; resolved from public data")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--location-source", help="required for supplied coordinates: user input or retained geocoder evidence; a citation alone is not verification")
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--crime-half-m", type=float, default=150)
    ap.add_argument("--planning-radius", type=int, default=250)
    ap.add_argument("--roads-radius", type=int, default=300)
    ap.add_argument("--depth", choices=("lite", "standard", "deep"), help="effective depth; defaults to requested baseline")
    ap.add_argument("--requested-depth", choices=("lite", "standard", "deep"), help="baseline, otherwise VETFLAT_RESEARCH_DEPTH or standard")
    ap.add_argument("--escalation-reason", help="required when effective depth differs from baseline; a recorded reason is not authorization proof")
    ap.add_argument("--street", help="the street's name when known; the scan moves onto it and says how far off the point was")
    ap.add_argument("--result-dir", help="private durable results directory; otherwise VETFLAT_SCAN_RESULT_DIR or .pea-state/area-scans")
    ap.add_argument("--lock-wait-seconds", type=float, default=2, help="bounded wait for an existing scan (0–30 seconds)")
    ap.add_argument("--deadline-seconds", type=float, default=DEFAULT_SCAN_SECONDS, help="whole scan deadline (default 180, maximum 240 seconds)")
    ap.add_argument("--source-timeout-seconds", type=float, default=DEFAULT_SOURCE_SECONDS, help="per-source deadline (default 90, maximum 240 seconds)")
    ap.add_argument("--out", help="also atomically export returned JSON to this private directory (0700)")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    baseline = a.requested_depth or os.environ.get("VETFLAT_RESEARCH_DEPTH", "standard")
    if baseline not in TIERS:
        ap.error("VETFLAT_RESEARCH_DEPTH must be lite, standard or deep")
    a.depth = a.depth or baseline
    reason = (a.escalation_reason or "").strip()
    if a.depth != baseline and not reason:
        ap.error("a depth different from the baseline requires --escalation-reason before any lookup")
    if not math.isfinite(a.lock_wait_seconds) or not 0 <= a.lock_wait_seconds <= 30:
        ap.error("--lock-wait-seconds must be between 0 and 30")
    if not all(math.isfinite(v) and 0 < v <= 240 for v in (a.deadline_seconds, a.source_timeout_seconds)):
        ap.error("scan and source deadlines must be positive, at most 240 seconds")
    if any(v is not None and not math.isfinite(v) for v in (a.lat, a.lng)) or (a.lat is not None and not -90 <= a.lat <= 90) or (a.lng is not None and not -180 <= a.lng <= 180):
        ap.error("coordinates must be finite latitude/longitude")
    if not 1 <= a.months <= 24 or not all(1 <= v <= 5000 for v in (a.crime_half_m, a.planning_radius, a.roads_radius)):
        ap.error("months must be 1–24 and radii 1–5000 metres")
    if any(len(v or "") > 500 for v in (a.postcode, a.street, reason, a.location_source)):
        ap.error("location and reason text must be at most 500 characters")
    try:
        validate_location(a.postcode, a.lat, a.lng, a.street, a.location_source)
    except ValueError as exc:
        ap.error(str(exc))
    def announce(msg):
        sys.stderr.write(msg)
        sys.stderr.flush()
    request = {k: getattr(a, k) for k in ("postcode", "lat", "lng", "months", "crime_half_m", "planning_radius", "roads_radius", "depth", "street", "location_source")}
    request.update(requested_depth=baseline, escalation_reason=reason or None,
                   effective_planning_radius=TIERS[a.depth]["planning_radius"] or a.planning_radius,
                   deadline_seconds=a.deadline_seconds, source_timeout_seconds=a.source_timeout_seconds)
    def interrupted(signum, frame):
        raise KeyboardInterrupt("signal %s" % signum)
    def perform(checkpoint=None):
        previous = None
        if threading.current_thread() is threading.main_thread():
            previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            return scan(a.postcode, a.lat, a.lng, a.months, a.crime_half_m, a.planning_radius, a.roads_radius,
                        a.depth, a.street, a.verbose, announce=announce, location_source=a.location_source,
                        deadline_seconds=a.deadline_seconds, source_timeout_seconds=a.source_timeout_seconds,
                        checkpoint=checkpoint)
        finally:
            if previous is not None:
                signal.signal(signal.SIGTERM, previous)
    if a.no_save:
        out = perform()
        out["execution"] = {"requested_depth": baseline, "effective_depth": a.depth, "escalation_reason": reason or None,
                            "reason_is_authorization_proof": False}
    else:
        root = a.result_dir or os.environ.get("VETFLAT_SCAN_RESULT_DIR") or os.path.join(os.getcwd(), ".pea-state", "area-scans")
        try:
            identity = scan_store.source_identity(HERE)
            out = scan_store.run(root, request, identity, perform, now_iso, a.lock_wait_seconds, with_checkpoint=True)
        except (OSError, ValueError) as exc:
            out = scan_store.status_result("storage_error", "Scanner identity unavailable: %s; no lookup performed" % exc)
    if a.out:
        try:
            with scan_store.directory(os.path.dirname(os.path.abspath(a.out))) as (_, fd):
                scan_store.atomic_json(fd, os.path.basename(a.out), out)
        except (OSError, ValueError) as exc:
            out.setdefault("not_found", []).append("could not export a copy: %s" % exc)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok") and out.get("scan_status") not in ("timed_out", "interrupted") else 1


if __name__ == "__main__":
    sys.exit(main())
