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

Usage:
    area_scan.py --postcode "N6 5QD"
    area_scan.py --lat 51.5732 --lng -0.1462 --street "Milton Park"      # the street is known: say so
    area_scan.py --postcode "N6 5QD" --depth lite
    area_scan.py --postcode "N6 5QD" --depth deep --months 6 --crime-half-m 150 --roads-radius 300

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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import now_iso  # noqa: E402

SCHEMA = "vet-flat/area-scan/2"
STREET_TYPES = re.compile(r"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)(_link)?$")
TIERS = {"lite": dict(street=False, band=False, rail=False, night=False, planning_radius=None, stages=False),
         "standard": dict(street=True, band=True, rail=False, night=False, planning_radius=None, stages=True),
         "deep": dict(street=True, band=True, rail=True, night=True, planning_radius=500, stages=True)}
STEP_M = 120      # distance between the sampled points along the street
OFF_STREET_M = 40  # beyond this, the given point is called a centroid, not a door
NAMED_RADIUS_M = 1500  # a named street is looked for this far out: an outcode centroid can be a kilometre off
NOTABLE_SINCE = 2024
NOTABLE_RULE = ("since %d and either big (5+ storeys, 10+ homes, tall-building hint) or a works signal (demolition, basement, "
                "piling, crane, hoarding, construction/dust plan); householder works excluded; nearest first" % NOTABLE_SINCE)
BIG_WORDS = re.compile(r"(?i)demoli(?:tion|sh)\b(?! of the (?:existing |detached )?(?:garage|shed|outbuilding|cycle store|refuse|bin|conservatory|fence|wall|porch))"
                       r"|basement|redevelop|new[- ]build|excavat|piling|crane|hoarding|scaffold"
                       r"|construction (?:logistics|management|environmental|traffic) plan|demolition and construction|\bCEMP\b|\bCMP\b|\bCLP\b|dust management"
                       r"|erection of (?:a |an )?(?:\w+[- ])*(?:building|block|tower|flats|dwellings|houses)"
                       r"|\b(?:three|four|five|six|seven|eight|nine|ten|\d{1,2})[- ]storey")
SMALL_WORDS = re.compile(r"(?i)single[- ]storey|rear extension|side extension|roof extension|dormer|outbuilding|garage|cycle store|refuse|shed|fence|"
                         r"advertisement|signage|shopfront|window|door|conservatory|porch|loft|certificate of lawfulness|tree|hedge")


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
    """Why a planning row is notable, or None: recent, and either big or a works-about-to-start signal."""
    years = [y for y in (_year(r.get("decision_date")), _year(r.get("valid_date"))) if y]
    if not years or max(years) < since:
        return None
    big = ((r.get("storeys") or 0) >= 5 or (r.get("residential_units_proposed") or 0) >= 10 or r.get("tall_building_hint"))
    text = str(r.get("description") or "")
    signal = BIG_WORDS.search(text)
    if big:
        return "big: %s" % ", ".join(x for x in (("%s storeys" % r.get("storeys")) if (r.get("storeys") or 0) >= 5 else "",
                                                ("%s homes" % r.get("residential_units_proposed")) if (r.get("residential_units_proposed") or 0) >= 10 else "",
                                                "tall-building hint" if r.get("tall_building_hint") else "") if x)
    if signal and not (SMALL_WORDS.search(text) and not re.search(r"(?i)basement|piling|crane|hoarding|management plan|dust|CEMP|CMP|CLP", text)):
        return "works signal: " + signal.group(0).lower()[:60]
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
        by_name.setdefault(w["tags"]["name"], []).append(w)
    best = None
    for n, group in by_name.items():
        lines = join_lines([l for w in group for l in _lines(w)])
        for line in lines:
            d, anchor, seg = anchor_on_line(line, lat, lng)
            if anchor is not None and (best is None or d < best[2]):
                best = (n, group[0]["tags"].get("highway"), d, line, group)
    return best


def find_street(lat, lng, name=None, radius=250, verbose=False, runner=None):
    """One Overpass request; the street block for the scan (ok False, never a guess, when nothing fits)."""
    import roads as roads_mod
    if name:
        radius = max(radius, NAMED_RADIUS_M)
    data, meta = (runner or roads_mod.run_overpass)(street_query(lat, lng, radius, name=name), verbose=verbose)
    out = {"ok": False, "name": name, "note": "", "source_url": (meta or {}).get("source_url"), "retrieved_at": (meta or {}).get("retrieved_at")}
    if not data:
        out["note"] = (meta or {}).get("note") or "overpass unavailable"
        return out
    best = choose_street(data.get("elements") or [], lat, lng, name)
    if not best:
        out["note"] = "no named street within %d m%s" % (radius, (" called %r" % name) if name else "")
        return out
    n, highway, d, line, group = best
    pts = sample_points(line, lat, lng)
    out.update({"ok": True, "name": n, "highway": highway, "offset_m": int(round(d)),
                "anchor": {"lat": round(pts[0][0], 6), "lng": round(pts[0][1], 6)},
                "points": [{"lat": round(a, 6), "lng": round(b, 6)} for a, b in pts],
                "mapped_length_m": int(polyline_length_m(line)), "ways": len(group)})
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
    out = {"how_to_use": "Complete. Write the answer from this JSON. Do not read this script's source, the cache, or the registers again, and do not run crime.py, planning.py, roads.py, noise.py or living_env.py for the same point.",
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
             "night_economy_nearest_m": nearest_m(roads.get("night_economy")),
             "night_economy_names": names(roads.get("night_economy")),
             "park_nearest_m": nearest_m(roads.get("park_or_green")),
             "facade_note": roads.get("facade_note"), "radius_m": roads.get("radius_m")}
        out["quiet"] = q
        out["sources"].append(roads.get("source_url"))
        main = q["main_road_nearest_m"]
        rail = [d for d in (q["railway_surface_nearest_m"], q["tube_surface_nearest_m"]) if d is not None]
        reading.append("Roads: %s%s. Rail at surface: %s. Bars, pubs and clubs within %s m: %s%s." % (
            ("nearest main road %s at %d m" % (q["main_road_names"][0], main)) if main is not None and q["main_road_names"] else
            ("nearest main road at %d m" % main) if main is not None else "no main road within the search radius",
            ("; a secondary road at %d m" % q["secondary_road_nearest_m"]) if q["secondary_road_nearest_m"] is not None else "",
            ("nearest at %d m" % min(rail)) if rail else "none within the radius",
            q["radius_m"], q["night_economy_count"] if q["night_economy_count"] is not None else "unknown",
            (" (nearest %s at %d m)" % (q["night_economy_names"][0], q["night_economy_nearest_m"])) if q["night_economy_names"] and q["night_economy_nearest_m"] is not None else ""))
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
        rows = sorted(rows, key=lambda r: (r.get("distance_m") is None, r.get("distance_m") or 0))
        keep = ("reference", "address", "description", "status", "decision_date", "distance_m", "storeys", "residential_units_proposed")
        def brief(r):
            b = {k: (_cut(r.get(k), 64 if k == "description" else 40) if k in ("address", "description") else r.get(k)) for k in keep}
            return {k: v for k, v in b.items() if v not in (None, "", 0)}
        top = [brief(r) for r in rows[:5]]
        notable, sites = [], {}
        for r in rows:
            why = notable_why(r)
            if not why:
                continue
            site = re.sub(r"\W+", " ", str(r.get("address") or "")).strip().lower()[:40] or r.get("reference")
            if site in sites:   # condition discharges and amendments for one permission: count them, list the site once
                sites[site]["related_submissions"] += 1
                continue
            b = brief(r)
            b["why"], b["related_submissions"] = why, 0
            sites[site] = b
            notable.append(b)
        notable = notable[:3]
        seen = len(rows)
        total = planning.get("total_matching") or planning.get("count") or seen
        far = max([r.get("distance_m") or 0 for r in rows] or [0])
        w = {"applications_within_m": planning.get("radius_m"), "count": total, "rows_seen": seen,
             "seen_out_to_m": int(far) if seen and total and seen < total else None, "since_year": planning.get("since_year"),
             "tall_building_hints": sum(1 for r in rows if r.get("tall_building_hint")), "nearest_five": top,
             "notable_recent": notable, "notable_rule": NOTABLE_RULE}
        out["works"] = w
        out["sources"].append(planning.get("source_url"))
        reading.append("Works: %s planning applications within %s m since %s%s, %s with a tall-building hint; the nearest: %s. Notable recent (%s): %s." % (
            w["count"], w["applications_within_m"], w["since_year"],
            (" (the nearest %d read, out to %d m)" % (seen, far)) if w["seen_out_to_m"] else "", w["tall_building_hints"],
            ("%s, %s (%s m)" % (top[0]["description"] or top[0]["reference"], top[0]["status"] or "status unknown", top[0]["distance_m"])) if top else "none",
            "since %d, big or a works-about-to-start signal" % NOTABLE_SINCE,
            "; ".join("%s at %s m (%s, %s; %s%s)" % (n["description"] or n["reference"], n["distance_m"], n["status"] or "status unknown", n["decision_date"] or "no decision date", n["why"],
                                                     (", +%d related submissions for the same site" % n["related_submissions"]) if n["related_submissions"] else "") for n in notable[:3]) or "none found"))
    elif planning is not None:
        out["not_found"].append("planning: " + str(planning.get("note") or "register unavailable"))

    if noise and noise.get("ok"):
        sm = noise.get("summary") or {}
        nz = {"road_lden_db": (sm.get("road_lden_db") or {}).get("at_point"),
              "road_lden_range_db": [(sm.get("road_lden_db") or {}).get("min"), (sm.get("road_lden_db") or {}).get("max")],
              "road_lnight_db": (sm.get("road_lnight_db") or {}).get("at_point") if sm.get("road_lnight_db") else None,
              "rail_lden_db": (sm.get("rail_lden_db") or {}).get("at_point") if sm.get("rail_lden_db") else None,
              "rail_not_drawn": (sm.get("rail_lden_db") or {}).get("not_drawn") if sm.get("rail_lden_db") else None,
              "band_2017_road": ((noise.get("band_2017") or {}).get("road_lden")),
              "points": len(noise.get("points") or []), "scale": noise.get("scale")}
        out["noise"] = nz
        out["sources"].extend(noise.get("sources") or [])
        reading.extend([r for r in (noise.get("reading") or []) if not r.startswith("These are modelled")])
        out["not_found"].extend("noise: " + x for x in (noise.get("not_found") or []))
    elif noise is not None:
        out["not_found"].append("noise: " + str((noise.get("not_found") or ["map unavailable"])[0]))

    if living and living.get("ok"):
        le = {"outdoors_decile": (living.get("outdoors") or {}).get("decile"), "indoors_decile": (living.get("indoors") or {}).get("decile"),
              "area": (living.get("lsoa") or {}).get("name"), "how_to_use": "context, never a filter"}
        out["living_environment"] = le
        out["sources"].append(living.get("source_url"))
        reading.append("Living environment (2025 indices, area of about 1,500 people): outdoors decile %s of 10 for air quality and road accidents, indoors decile %s for housing condition; 1 is the worst tenth in England, and inner London sits low outdoors almost everywhere." % (
            le["outdoors_decile"], le["indoors_decile"]))
    elif living is not None:
        out["not_found"].append("living environment: " + str(living.get("note") or "table unavailable"))

    reading.append("Quiet and safety are different questions: the roads, rail, night-economy and noise lines answer quiet; the crime line answers safety and says nothing about noise. All of this is the area, not the flat: listen at the window on the viewing day, at night if you can, and read the flat's own EPC for fabric.")
    if (where or {}).get("how_located", "").startswith("lat/lng given") and not (street and street.get("ok")):
        reading.append("The point was given as coordinates: if it is an area centroid rather than a door, treat every distance as a rough guide and scan again with --street NAME.")
    out["sources"] = [s for s in out["sources"] if s]
    out["ok"] = any(x is not None for x in (out["quiet"], out["noise"], out["crime"], out["works"], out["living_environment"]))
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
    s, err = _safe(planning_mod.stages, top["reference"], lpa, verbose=verbose)
    if err or not s or not s.get("record"):
        out["not_found"].append("stage of %s: %s" % (top["reference"], err or (s or {}).get("note") or "not found"))
        return
    means = [m for m in (s.get("what_this_means") or []) if m][:3]
    w["top_notable_stage"] = {"reference": top["reference"], "status": (s.get("record") or {}).get("status"),
                              "what_this_means": [m[:200] for m in means], "portal_url": (s.get("conditions") or {}).get("portal_url")}
    if means:
        out["reading"].insert(min(3, len(out["reading"])), "The biggest recent application nearby, %s at %s m: %s" % (
            top["reference"], top.get("distance_m"), " ".join(means)[:400]))


def scan(postcode=None, lat=None, lng=None, months=6, crime_half_m=150, planning_radius=250, roads_radius=300,
         depth="standard", street=None, verbose=False):
    import geo, crime as crime_mod, planning as planning_mod, roads as roads_mod, living_env, noise as noise_mod  # noqa: E402
    tier = TIERS.get(depth) or TIERS["standard"]
    notes = []
    where = {"postcode": postcode, "lat": lat, "lng": lng, "district": None, "how_located": "lat/lng given" if lat is not None else None}
    if lat is None or lng is None:
        if not postcode:
            raise ValueError("give --postcode or --lat and --lng")
        g, err = _safe(geo.lookup, postcode, verbose)
        if err or not g or not g.get("ok"):
            return {"schema": SCHEMA, "ok": False, "retrieved_at": now_iso(), "where": where,
                    "note": "postcode not located: %s" % (err or (g or {}).get("note")), "reading": [], "sources": [], "not_found": ["postcode lookup"]}
        lat, lng = g["lat"], g["lng"]
        where.update({"lat": lat, "lng": lng, "district": g.get("admin_district"), "ward": g.get("admin_ward"),
                      "how_located": "postcode centroid via postcodes.io (tens of metres off a door)"})
    st = None
    at_lat, at_lng, pts = lat, lng, [(lat, lng)]
    if tier["street"] or street:
        st, e0 = _safe(find_street, lat, lng, street, verbose=verbose)
        if e0:
            st = {"ok": False, "name": street, "note": e0}
        if st and st.get("ok"):
            at_lat, at_lng = st["anchor"]["lat"], st["anchor"]["lng"]
            pts = [(p["lat"], p["lng"]) for p in st["points"]]
            where["scan_point"] = {"lat": at_lat, "lng": at_lng, "why": "moved onto %s" % st["name"]}
    pr = tier["planning_radius"] or planning_radius
    c, e1 = _safe(crime_mod.box, at_lat, at_lng, crime_half_m, months, verbose=verbose)
    if c and c.get("ok") and not c.get("total"):
        wide, e1b = _safe(crime_mod.box, at_lat, at_lng, crime_half_m * 2, months, verbose=verbose)
        if wide and wide.get("ok"):
            c["wider_box"] = {"half_m": crime_half_m * 2, "total": wide.get("total"), "months": wide.get("months_counted")}
    p, e2 = _safe(planning_mod.near, at_lat, at_lng, pr, verbose=verbose)
    r, e3 = _safe(roads_mod.near, at_lat, at_lng, roads_radius, verbose=verbose)
    n, e5 = _safe(noise_mod.lookup, pts, rail=tier["rail"], night=tier["night"], with_band=tier["band"], verbose=verbose)
    l, e4 = _safe(living_env.lookup, postcode=postcode, verbose=verbose) if postcode else (None, "living environment needs a postcode")
    for name, err in (("crime", e1), ("planning", e2), ("roads", e3), ("noise", e5), ("living environment", e4)):
        if err:
            notes.append("%s: %s" % (name, err))
    out = compose(where, c, p, r, l, notes, noise=n, street=st, depth=depth)
    if tier["stages"]:
        add_stage(out, p, verbose=verbose)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="Run it once per street and write from the JSON; the output is complete. --depth is the person's budget mode; standard when unknown. Reading this file's source or the cache adds nothing.")
    ap.add_argument("--postcode")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--crime-half-m", type=float, default=150)
    ap.add_argument("--planning-radius", type=int, default=250)
    ap.add_argument("--roads-radius", type=int, default=300)
    ap.add_argument("--depth", choices=("lite", "standard", "deep"), default="standard", help="the person's budget mode; see the module docstring")
    ap.add_argument("--street", help="the street's name when known; the scan moves onto it and says how far off the point was")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if not a.postcode and (a.lat is None or a.lng is None):
        ap.print_help()
        return 2
    out = scan(a.postcode, a.lat, a.lng, a.months, a.crime_half_m, a.planning_radius, a.roads_radius, a.depth, a.street, a.verbose)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
