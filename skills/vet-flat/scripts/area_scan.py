#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One call for "is this street quiet, safe, and is anything being built?": the four open registers,
one compact JSON, a plain reading. The model reads this, not the manuals and not the web.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Sources (all open, all already used by the skill's own scripts): postcodes.io for the point,
data.police.uk for crime in a ~300 m box over the last six months, the GLA Planning Datahub for
applications within 250 m, OpenStreetMap via Overpass for roads, rail, night economy and parks
within 300 m, and the 2025 living-environment deciles for the area. Nothing here reads a listing
or review site.

Usage:
    area_scan.py --postcode "N6 5QD"
    area_scan.py --lat 51.5732 --lng -0.1462
    area_scan.py --postcode "N6 5QD" --months 6 --crime-half-m 150 --planning-radius 250 --roads-radius 300

Output is one JSON object of about 3-5k characters with a fixed shape (schema vet-flat/area-scan/1):
where, quiet, crime, works, living_environment, reading (plain sentences), sources, not_found.
Each block carries ok/note from its register; a failed register is reported, never guessed.
Standard library only, Python 3.9; network through the other scripts' _fetch (curl, cached).
"""
from __future__ import unicode_literals

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import now_iso  # noqa: E402

SCHEMA = "vet-flat/area-scan/1"


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


def compose(where, crime, planning, roads, living, notes):
    """The fixed shape, from the raw outputs of the four scripts (any may be None)."""
    out = {"schema": SCHEMA, "ok": True, "retrieved_at": now_iso(), "where": where,
           "quiet": None, "crime": None, "works": None, "living_environment": None,
           "reading": [], "sources": [], "not_found": list(notes)}
    reading = out["reading"]

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
             "top_categories": [{"category": k, "count": v} for k, v in cats],
             "predatory_share": pred.get("share_of_total"), "box_half_m": (crime.get("query") or {}).get("half_m"),
             "latest_month": crime.get("latest_available_month"), "months_missing": crime.get("months_missing")}
        out["crime"] = c
        out["sources"].append(crime.get("source_url"))
        reading.append("Crime: %s recorded in %s months in a box about %d m across (%s a month); the four categories a resident meets on the street make up %s%%; biggest: %s." % (
            total, months, int((c["box_half_m"] or 150) * 2), c["per_month_avg"],
            int(round((pred.get("share_of_total") or 0) * 100)), ", ".join("%s %d" % (k, v) for k, v in cats[:3]) or "none"))
    elif crime is not None:
        out["not_found"].append("crime: " + str(crime.get("note") or "register unavailable"))

    if planning and planning.get("ok"):
        rows = planning.get("results") or []
        rows = sorted(rows, key=lambda r: (r.get("distance_m") is None, r.get("distance_m") or 0))
        keep = ("reference", "address", "description", "status", "decision", "decision_date", "distance_m", "storeys", "residential_units_proposed")
        top = [{k: ((r.get(k) or "")[:80] if k in ("address", "description") else r.get(k)) for k in keep} for r in rows[:5]]
        w = {"applications_within_m": planning.get("radius_m"), "count": planning.get("total_matching") or planning.get("count"), "since_year": planning.get("since_year"),
             "tall_building_hints": sum(1 for r in rows if r.get("tall_building_hint")), "nearest_five": top}
        out["works"] = w
        out["sources"].append(planning.get("source_url"))
        reading.append("Works: %s planning applications within %s m since %s, %s with a tall-building hint; the nearest: %s." % (
            w["count"], w["applications_within_m"], w["since_year"], w["tall_building_hints"],
            ("%s, %s (%s m)" % (top[0]["description"] or top[0]["reference"], top[0]["status"] or "status unknown", top[0]["distance_m"])) if top else "none"))
    elif planning is not None:
        out["not_found"].append("planning: " + str(planning.get("note") or "register unavailable"))

    if living and living.get("ok"):
        le = {"outdoors_decile": (living.get("outdoors") or {}).get("decile"), "indoors_decile": (living.get("indoors") or {}).get("decile"),
              "area": (living.get("lsoa") or {}).get("name"), "how_to_use": "context, never a filter"}
        out["living_environment"] = le
        out["sources"].append(living.get("source_url"))
        reading.append("Living environment (2025 indices, area of about 1,500 people): outdoors decile %s of 10 for air quality and road accidents, indoors decile %s for housing condition; 1 is the worst tenth in England, and inner London sits low outdoors almost everywhere." % (
            le["outdoors_decile"], le["indoors_decile"]))
    elif living is not None:
        out["not_found"].append("living environment: " + str(living.get("note") or "table unavailable"))

    reading.append("All of this is the area, not the flat: listen at the window on the viewing day, at night if you can, and read the flat's own EPC for fabric.")
    out["sources"] = [s for s in out["sources"] if s]
    out["ok"] = any(x is not None for x in (out["quiet"], out["crime"], out["works"], out["living_environment"]))
    return out


def scan(postcode=None, lat=None, lng=None, months=6, crime_half_m=150, planning_radius=250, roads_radius=300, verbose=False):
    import geo, crime as crime_mod, planning as planning_mod, roads as roads_mod, living_env  # noqa: E402
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
    c, e1 = _safe(crime_mod.box, lat, lng, crime_half_m, months, verbose=verbose)
    p, e2 = _safe(planning_mod.near, lat, lng, planning_radius, verbose=verbose)
    r, e3 = _safe(roads_mod.near, lat, lng, roads_radius, verbose=verbose)
    l, e4 = _safe(living_env.lookup, postcode=postcode, verbose=verbose) if postcode else (None, "living environment needs a postcode")
    for name, err in (("crime", e1), ("planning", e2), ("roads", e3), ("living environment", e4)):
        if err:
            notes.append("%s: %s" % (name, err))
    return compose(where, c, p, r, l, notes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--postcode")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--crime-half-m", type=float, default=150)
    ap.add_argument("--planning-radius", type=int, default=250)
    ap.add_argument("--roads-radius", type=int, default=300)
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if not a.postcode and (a.lat is None or a.lng is None):
        ap.print_help()
        return 2
    out = scan(a.postcode, a.lat, a.lng, a.months, a.crime_half_m, a.planning_radius, a.roads_radius, a.verbose)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
