#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Road and rail noise at a point, from Defra's strategic noise maps for England: the modelled
Lden and Lnight levels in dB from the 2022 maps (Round 4, 2021 traffic), plus the 2017 band the
point sits in (Round 3). Open data, Open Government Licence v3.0, attribution "© Crown Copyright".

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

What the numbers are: Lden is the day-evening-night average (evening +5 dB, night +10 dB
weighting); Lnight is the 23:00-07:00 average. Both are a model of outdoor noise at 4 m height on
a 10 m grid, not a measurement at any window. WHO's 2018 guideline values for road traffic are
Lden 53 dB and Lnight 45 dB. The 2017 vector map only draws bands from 55 dB (Lden) / 50 dB
(Lnight); the 2022 raster floors at 40 dB (Lden) / 35 dB (Lnight): a point at the floor is
"quieter than the map draws", not silent.

Sources (verified 2026-09-11, docs/research/defra-noise-endpoints-2026-09-11.md):
    Round 4 WMS GetFeatureInfo, a dB value at a point:
        https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wms
        https://environment.data.gov.uk/spatialdata/noise-data/wms          (rail; the slug is not a typo)
    Round 3 WFS, the 2017 band polygon that contains the point:
        https://environment.data.gov.uk/spatialdata/road-noise-lden-england-round-3/wfs   (and lnight, rail)

Usage:
    noise.py --lat 51.4926 --lng -0.2284
    noise.py --postcode "W6 0QU"                              # postcode centroid via postcodes.io, not a door
    noise.py --lat 51.4926 --lng -0.2284 --rail --night       # add rail, and the night-time layers
    noise.py --points "51.4926,-0.2284;51.4930,-0.2290"       # several points, one summary (a street)
    noise.py ... --no-band                                    # skip the 2017 band lookup

Output: one JSON object (schema vet-flat/noise/1) of about 1,500 characters: points (each with
the dB values asked for), summary (min/max per layer), band_2017, reading (plain sentences),
scale, sources, licence, caveats, not_found. A layer that fails is reported, never guessed.
Standard library only, Python 3.9; network through _fetch (curl, cached for a day).
"""
from __future__ import unicode_literals

import argparse
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import get, now_iso, TOOL_UA  # noqa: E402

SCHEMA = "vet-flat/noise/1"
BASE = "https://environment.data.gov.uk/spatialdata/"
WMS = {"road": BASE + "road-noise-all-metrics-england-round-4/wms",
       "rail": BASE + "noise-data/wms"}
LAYER = {("road", "lden"): "Road_Noise_Lden_England_Round_4_All",
         ("road", "lnight"): "Road_Noise_Lnight_England_Round_4_All",
         ("rail", "lden"): "Rail_Noise_Lden_England_Round_4_All",
         ("rail", "lnight"): "Rail_Noise_Lnight_England_Round_4_All"}
WFS = {("road", "lden"): ("road-noise-lden-england-round-3",
                          "dataset-fd1c6327-ad77-42ae-a761-7c6a0866523d:Road_Noise_Lden_England_Round_3"),
       ("road", "lnight"): ("road-noise-lnight-england-round-3",
                            "dataset-cc48e728-602a-4e8a-9221-49f661ab58f8:Road_Noise_Lnight_England_Round_3"),
       ("rail", "lden"): ("rail-noise-lden-england-round-3",
                          "dataset-e8e78e12-9297-450b-b875-e0523cb3c9ea:Rail_Noise_Lden_England_Round_3"),
       ("rail", "lnight"): ("rail-noise-lnight-england-round-3",
                            "dataset-f6c0e3b6-3186-4d0a-b0e7-ca32bfb6573f:Rail_Noise_Lnight_England_Round_3")}
FLOOR = {"lden": 40.0, "lnight": 35.0}        # the 2022 raster is not drawn below these
BAND_FLOOR = {"lden": 55.0, "lnight": 50.0}   # the 2017 polygons start here
WHO = {("road", "lden"): 53.0, ("road", "lnight"): 45.0, ("rail", "lden"): 54.0, ("rail", "lnight"): 44.0}  # WHO 2018 guideline values
LICENCE = "Open Government Licence v3.0; attribution: © Crown Copyright (Defra strategic noise mapping)"
HALF = 0.00008   # degrees: a 3x3-pixel box about 18 m tall and 11 m wide in London; the centre pixel is read
SCALE = ("Lden (day-evening-night average, night weighted +10 dB): WHO guidelines road %d dB, rail %d dB. "
         "Lnight (23:00-07:00): WHO guidelines road %d dB, rail %d dB. These compare modelled outdoor "
         "traffic exposure, not indoor levels, window direction or how often noise will be heard."
         % (WHO[("road", "lden")], WHO[("rail", "lden")], WHO[("road", "lnight")], WHO[("rail", "lnight")]))
CAVEATS = ["A model of outdoor noise at 4 m height on a 10 m grid from 2021 traffic counts, not a measurement at any window; indoor levels depend on the flat itself.",
           "The value read is the map pixel under the point; on a road edge the neighbouring pixel can differ by several dB. Treat differences under 3 dB as noise.",
           "Only road and rail traffic are mapped: no pubs, building sites, bin lorries, neighbours or aircraft."]


def feature_info_url(source, metric, lat, lng):
    layer = LAYER[(source, metric)]
    q = [("SERVICE", "WMS"), ("VERSION", "1.3.0"), ("REQUEST", "GetFeatureInfo"), ("LAYERS", layer), ("QUERY_LAYERS", layer),
         ("CRS", "EPSG:4326"), ("BBOX", "%.5f,%.5f,%.5f,%.5f" % (lat - HALF, lng - HALF, lat + HALF, lng + HALF)),
         ("WIDTH", "3"), ("HEIGHT", "3"), ("I", "1"), ("J", "1"), ("INFO_FORMAT", "application/json"), ("FORMAT", "image/png")]
    return WMS[source] + "?" + urllib.parse.urlencode(q)


def band_url(source, metric, lat, lng):
    slug, typename = WFS[(source, metric)]
    q = [("service", "WFS"), ("version", "2.0.0"), ("request", "GetFeature"), ("typeName", typename),
         ("outputFormat", "application/json"), ("propertyName", "noiseclass"),
         ("CQL_FILTER", "INTERSECTS(shape,SRID=4326;POINT(%.6f %.6f))" % (lng, lat))]
    return BASE + slug + "/wfs?" + urllib.parse.urlencode(q)


def parse_feature_info(body):
    """(value in dB rounded to one decimal, or None, note)."""
    try:
        d = json.loads(body or "")
    except ValueError:
        return None, "response was not JSON"
    feats = d.get("features") or []
    if not feats:
        return None, "no value at this point (outside the mapped area)"
    v = (feats[0].get("properties") or {}).get("GRAY_INDEX")
    if v is None:
        return None, "no value in the response"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None, "value was not a number"
    if v < 0 or v > 130:
        return None, "no-data value %s" % v
    return round(v, 1), ""


def band_low(text):
    m = re.search(r"\d+(?:\.\d+)?", text or "")
    return float(m.group(0)) if m else -1.0


def parse_band(body):
    """(band text or None, note). None with an empty note = no polygon here = below the drawn floor."""
    try:
        d = json.loads(body or "")
    except ValueError:
        return None, "response was not JSON"
    feats = d.get("features")
    if feats is None:
        return None, "no features field in the response"
    bands = [str((f.get("properties") or {}).get("noiseclass") or "") for f in feats]
    bands = [b for b in bands if b]
    if not feats:
        return None, ""
    if not bands:
        return None, "polygon without a band value"
    return max(bands, key=band_low), ""   # two polygons can share the edge under the point: keep the louder


def describe(db, metric, source="road"):
    """Compare modelled outdoor exposure to the source's guideline, without predicting audibility."""
    if db is None:
        return "nothing drawn here (below the map's floor)"
    who = WHO[(source, metric)]
    guideline = "WHO night guideline" if metric == "lnight" else "WHO guideline"
    if metric == "lnight":
        if db < who - 5:
            relation = "well under"
        elif db < who:
            relation = "under"
        elif db < who + 5:
            relation = "at or above"
        elif db < who + 10:
            relation = "5–10 dB above"
        else:
            relation = "at least 10 dB above"
    elif db < who - 8:
        relation = "well under"
    elif db < who:
        relation = "under"
    elif db < who + 7:
        relation = "at or above"
    elif db < who + 12:
        relation = "7–12 dB above"
    elif db < who + 17:
        relation = "12–17 dB above"
    else:
        relation = "at least 17 dB above"
    return "modelled outdoor exposure %s the %s of %d dB" % (relation, guideline, who)


def level(lat, lng, source="road", metric="lden", verbose=False, fetcher=None):
    url = feature_info_url(source, metric, lat, lng)
    res = (fetcher or get)(url, ua=TOOL_UA, timeout=25, min_gap=0.5, verbose=verbose)
    out = {"source": source, "metric": metric, "db": None, "ok": False, "note": "",
           "retrieved_at": res.get("retrieved_at"), "from_cache": bool(res.get("from_cache"))}
    if not res.get("ok"):
        out["note"] = res.get("note") or "fetch failed"
        return out
    v, note = parse_feature_info(res.get("body") or "")
    out["db"], out["ok"], out["note"] = v, v is not None, note
    if v is not None and v < FLOOR[metric] - 1:
        # the raster holds 0 where nothing is drawn: that is "no mapped noise", never "0 dB"
        out["db"], out["ok"], out["drawn"] = None, True, False
        out["note"] = "nothing drawn here: below the map's floor of %d dB" % int(FLOOR[metric])
    elif v is not None:
        out["drawn"] = True
        if v <= FLOOR[metric] + 0.6:
            out["note"] = "at the map's floor of %d dB: quieter than the map draws" % int(FLOOR[metric])
    return out


def band(lat, lng, source="road", metric="lden", verbose=False, fetcher=None):
    url = band_url(source, metric, lat, lng)
    res = (fetcher or get)(url, ua=TOOL_UA, timeout=25, min_gap=0.5, verbose=verbose)
    out = {"source": source, "metric": metric, "band": None, "ok": False, "note": "", "floor_db": BAND_FLOOR[metric],
           "retrieved_at": res.get("retrieved_at"), "from_cache": bool(res.get("from_cache"))}
    if not res.get("ok"):
        out["note"] = res.get("note") or "fetch failed"
        return out
    text, note = parse_band(res.get("body") or "")
    if text is None and not note:
        out["band"], out["ok"] = "below %d dB (no band drawn here in 2017)" % int(BAND_FLOOR[metric]), True
    else:
        out["band"], out["ok"], out["note"] = text, text is not None, note
    return out


def _fmt(v):
    return "unknown" if v is None else ("%.0f" % v if abs(v - round(v)) < 0.05 else "%.1f" % v)


def lookup(points, rail=False, night=False, with_band=True, verbose=False, fetcher=None):
    """points: [(lat, lng), ...]; the first is the point of interest (the door or the street point)."""
    points = [(float(a), float(b)) for a, b in points][:5]
    layers = [("road", "lden")] + ([("road", "lnight")] if night else []) + ([("rail", "lden")] if rail else []) \
        + ([("rail", "lnight")] if rail and night else [])
    out = {"schema": SCHEMA, "ok": False, "retrieved_at": now_iso(), "points": [], "summary": {}, "band_2017": None,
           "reading": [], "scale": SCALE, "sources": [], "licence": LICENCE, "caveats": CAVEATS, "not_found": []}
    values = {k: [] for k in layers}
    for lat, lng in points:
        row = {"lat": round(lat, 6), "lng": round(lng, 6)}
        for src, met in layers:
            r = level(lat, lng, src, met, verbose=verbose, fetcher=fetcher)
            key = "%s_%s_db" % (src, met)
            row[key] = r["db"]
            if r["db"] is not None:
                values[(src, met)].append(r["db"])
            elif r.get("ok"):
                row[key] = "not drawn"
            if r["note"] and not r.get("ok"):
                out["not_found"].append("%s %s at %.5f,%.5f: %s" % (src, met, lat, lng, r["note"]))
            elif r["note"] and "floor of" in r["note"] and r["db"] is not None:
                row[key + "_note"] = r["note"]
        out["points"].append(row)
    for (src, met), vals in values.items():
        first = out["points"][0].get("%s_%s_db" % (src, met)) if out["points"] else None
        out["summary"]["%s_%s_db" % (src, met)] = {"at_point": first if isinstance(first, float) else None,
                                                    "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                                                    "n": len(vals), "not_drawn": sum(1 for p in out["points"] if p.get("%s_%s_db" % (src, met)) == "not drawn")}
    out["sources"] = sorted(set(WMS[s] for s, _ in layers))
    if with_band and points:
        b = band(points[0][0], points[0][1], "road", "lden", verbose=verbose, fetcher=fetcher)
        out["band_2017"] = {"road_lden": b["band"], "ok": b["ok"], "note": b["note"]}
        out["sources"].append(BASE + WFS[("road", "lden")][0] + "/wfs")
        if not b["ok"]:
            out["not_found"].append("2017 road band: " + (b["note"] or "unavailable"))
    out["ok"] = any(v for v in values.values()) or any(p.get("road_lden_db") == "not drawn" for p in out["points"])

    n = len(points)
    reading = out["reading"]
    def _sentence(label, src, met):
        sm = out["summary"].get("%s_%s_db" % (src, met)) or {}
        if not sm.get("n") and sm.get("not_drawn"):
            return "%s: nothing drawn at any of the %d point%s (below the map's %d dB floor), so no mapped %s noise here." % (
                label, len(points), "" if len(points) == 1 else "s", int(FLOOR[met]), src)
        if not sm.get("n"):
            return "%s: no value could be read for this point." % label
        v = sm["at_point"] if sm["at_point"] is not None else sm["max"]
        at = "at the point" if sm["at_point"] is not None else "at the loudest of the sampled points (nothing drawn at the point itself)"
        span = "" if n == 1 or sm["min"] == sm["max"] else " (%s-%s dB across %d points along the street)" % (_fmt(sm["min"]), _fmt(sm["max"]), sm["n"])
        return "%s: %s dB %s%s: %s." % (label, _fmt(v), at, span, describe(v, met, src))
    reading.append(_sentence("Road noise, day-evening-night average", "road", "lden"))
    if night:
        reading.append(_sentence("Road noise at night (23:00-07:00)", "road", "lnight"))
    if rail:
        reading.append(_sentence("Rail noise, day-evening-night average", "rail", "lden"))
        if night:
            reading.append(_sentence("Rail noise at night", "rail", "lnight"))
    if out["band_2017"] and out["band_2017"].get("ok"):
        reading.append("The 2017 map drew no road-noise band here (below 55 dB then)." if "below" in str(out["band_2017"]["road_lden"])
                       else "The 2017 map put the point in the %s dB band for road noise." % out["band_2017"]["road_lden"])
    reading.append("These are modelled outdoor levels from 2021 traffic, not a measurement at any window; differences under 3 dB are within the model's grain.")
    return out


def parse_points(text):
    pts = []
    for part in re.split(r"[;|]", text or ""):
        part = part.strip()
        if not part:
            continue
        a, b = part.split(",")
        pts.append((float(a), float(b)))
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--postcode")
    ap.add_argument("--points", help='"lat,lng;lat,lng;..." up to five points; the first is the point of interest')
    ap.add_argument("--rail", action="store_true")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--no-band", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    pts = parse_points(a.points) if a.points else []
    where = {"postcode": a.postcode}
    if not pts and a.lat is not None and a.lng is not None:
        pts = [(a.lat, a.lng)]
    if not pts and a.postcode:
        import geo
        g = geo.lookup(a.postcode, a.verbose)
        if not g or not g.get("ok"):
            json.dump({"schema": SCHEMA, "ok": False, "note": "postcode not located: %s" % (g or {}).get("note"), "where": where}, sys.stdout, ensure_ascii=False, indent=1)
            print()
            return 1
        pts = [(g["lat"], g["lng"])]
        where["how_located"] = "postcode centroid via postcodes.io (tens of metres off a door)"
    if not pts:
        ap.print_help()
        return 2
    out = lookup(pts, rail=a.rail, night=a.night, with_band=not a.no_band, verbose=a.verbose)
    out["where"] = where
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
