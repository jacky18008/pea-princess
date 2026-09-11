#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neighbourhood living environment from the English Indices of Deprivation 2025 (official, open).

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

Source: Ministry of Housing, Communities and Local Government, "English indices of
deprivation 2025", File 7 (all ranks, scores and deciles for every Lower layer Super Output
Area, 2021 boundaries, 33,755 areas). Open Government Licence v3.0. No key, no login.
The area code for a postcode comes from postcodes.io (ONS Postcode Directory, open).

What this script reads, and nothing else:
  - the Living Environment Deprivation domain (score, rank, decile), and its two halves:
  - "indoors": the quality of housing (housing in poor condition, homes without central heating);
  - "outdoors": air quality and road traffic accidents.
The income, employment, health, education, crime and barriers domains are not read and not
printed. The skill uses direct police data for crime and does not sort neighbourhoods by
who lives in them.

How to read it: decile 1 is the most deprived tenth of small areas in England, decile 10 the
least. A Lower layer Super Output Area holds roughly 1,500 people, so this is the street
and its neighbours, not the building. Inner London sits low on the outdoors half because
of air quality almost everywhere, so compare candidates with each other, not with England.
It is context for axis 12 (low-maintenance living), never a filter and never a verdict.

Usage:
    living_env.py lookup --postcode "N21 1BD"
    living_env.py lookup --lsoa E01001567
    living_env.py lookup --postcode "SE3 0BU" --csv tests/fixtures/living_env-file7-sample.csv

The 9.9 MB table is downloaded once into the vet-flat cache and reused for 90 days.
Python 3.9, standard library only; network through _fetch (curl).
"""
from __future__ import unicode_literals

import argparse
import csv
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _fetch import BROWSER_UA, cache_dir, fetch, fetch_binary, now_iso  # noqa: E402

RELEASE_URL = "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025"
FILE7_URL = ("https://assets.publishing.service.gov.uk/media/691ded56d140bbbaa59a2a7d/"
             "File_7_IoD2025_All_Ranks_Scores_Deciles_Population_Denominators.csv")
POSTCODES = "https://api.postcodes.io/postcodes/%s"
LICENCE = "Open Government Licence v3.0"
AREAS = 33755
TABLE_TTL_S = 90 * 86400

COLUMNS = {
    "code": "LSOA code (2021)",
    "name": "LSOA name (2021)",
    "district": "Local Authority District name (2024)",
    "living_environment": "Living Environment",
    "indoors": "Indoors Sub-domain",
    "outdoors": "Outdoors Sub-domain",
}
MEASURES = {
    "living_environment": "the quality of housing, air quality and road traffic accidents together",
    "indoors": "the quality of housing: housing in poor condition, homes without central heating",
    "outdoors": "air quality and road traffic accidents",
}
HOW_TO_USE = ("Context for axis 12, never a filter and never a verdict. The area is about 1,500 "
              "people around the postcode, not this building. Inner London sits low on the "
              "outdoors half almost everywhere because of air quality: compare candidates with "
              "each other, not with England. Nothing here describes who lives in the area.")


def reading(decile):
    """Plain words for a decile, 1 = most deprived tenth of England's small areas."""
    if decile is None:
        return "unknown"
    if decile <= 2:
        return "among the most deprived fifth of small areas in England"
    if decile <= 4:
        return "below the middle"
    if decile <= 6:
        return "around the middle"
    if decile <= 8:
        return "above the middle"
    return "among the least deprived fifth of small areas in England"


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_row(header, row):
    """The three living-environment blocks out of one File 7 row, by column heading."""
    d = dict(zip(header, row))
    out = {"lsoa": {"code": d.get(COLUMNS["code"]), "name": d.get(COLUMNS["name"]),
                    "local_authority": d.get(COLUMNS["district"])}}
    for key in ("living_environment", "indoors", "outdoors"):
        prefix = COLUMNS[key]
        block = {"score": None, "rank": None, "decile": None}
        for h, v in d.items():
            if not h.startswith(prefix):
                continue
            rest = h[len(prefix):].strip().lower()
            if rest.startswith("score"):
                block["score"] = _num(v)
            elif rest.startswith("rank"):
                r = _num(v)
                block["rank"] = int(r) if r is not None else None
            elif rest.startswith("decile"):
                dec = _num(v)
                block["decile"] = int(dec) if dec is not None else None
        block["of"] = AREAS
        block["reading"] = reading(block["decile"])
        block["measures"] = MEASURES[key]
        out[key] = block
    return out


def find_row(path, lsoa_code):
    """Stream the table and return (header, row) for one area, or (header, None)."""
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for row in reader:
            if row and row[0] == lsoa_code:
                return header, row
    return header, None


def table_path(verbose=False):
    """The File 7 CSV in the cache, downloaded when missing or older than 90 days."""
    folder = cache_dir()
    path = os.path.join(folder, "iod2025_file7.csv")
    fresh = os.path.exists(path) and (time.time() - os.path.getmtime(path)) < TABLE_TTL_S \
        and os.path.getsize(path) > 1000000
    if fresh:
        return path, {"http_status": None, "ok": True, "note": "table from cache", "retrieved_at": now_iso()}
    res = fetch_binary(FILE7_URL, path, ua=BROWSER_UA, timeout=120, verbose=verbose)
    ok = bool(res.get("ok")) and os.path.exists(path) and os.path.getsize(path) > 1000000
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        first = fh.readline() if ok else ""
    if ok and not first.startswith("LSOA code (2021)"):
        ok = False
        res["note"] = (res.get("note") or "") + "; downloaded file is not the 2025 File 7 table"
    return path, {"http_status": res.get("status"), "ok": ok, "note": res.get("note") or None,
                  "bytes": res.get("bytes"), "retrieved_at": res.get("retrieved_at") or now_iso()}


def lsoa_for(postcode, verbose=False):
    """(code, name, envelope) for a postcode via postcodes.io; 2021 boundaries."""
    pc = "".join(postcode.split()).upper()
    url = POSTCODES % pc
    res = fetch(url, cache_ttl=30 * 86400, verbose=verbose,
                expect=lambda b: '"codes"' in b or '"error"' in b)
    env = {"source_url": url, "http_status": res.get("http_status"), "ok": bool(res.get("ok")),
           "note": res.get("note"), "retrieved_at": res.get("retrieved_at") or now_iso()}
    if not res.get("ok") or not res.get("body"):
        return None, None, env
    try:
        obj = json.loads(res["body"])
    except ValueError:
        env["ok"] = False
        env["note"] = (env["note"] or "") + "; postcodes.io returned no JSON"
        return None, None, env
    result = obj.get("result") or {}
    codes = result.get("codes") or {}
    code = codes.get("lsoa21") or codes.get("lsoa")
    if not code:
        env["ok"] = False
        env["note"] = (env["note"] or "") + "; postcode not found or no LSOA code"
    return code, result.get("lsoa"), env


def lookup(postcode=None, lsoa=None, csv_path=None, verbose=False):
    out = {"query": {"postcode": postcode, "lsoa": lsoa},
           "source_url": FILE7_URL, "release": RELEASE_URL, "licence": LICENCE,
           "evidence_class": "G", "retrieved_at": now_iso(), "http_status": None, "ok": False,
           "note": None}
    code, name = lsoa, None
    if postcode and not lsoa:
        code, name, env = lsoa_for(postcode, verbose=verbose)
        out["postcode_lookup"] = env
        if not code:
            out["note"] = "no area code for this postcode: " + str(env.get("note"))
            return out
    if csv_path:
        path, tenv = csv_path, {"http_status": None, "ok": True, "note": "table from --csv"}
    else:
        path, tenv = table_path(verbose=verbose)
    out["http_status"] = tenv.get("http_status")
    out["table"] = tenv
    if not tenv.get("ok"):
        out["note"] = "table unavailable: " + str(tenv.get("note"))
        return out
    header, row = find_row(path, code)
    if row is None:
        out["note"] = "area %s is not in the 2025 table (England only; 2021 boundaries)" % code
        return out
    out.update(parse_row(header, row))
    if name and not out["lsoa"].get("name"):
        out["lsoa"]["name"] = name
    out["ok"] = True
    out["how_to_use"] = HOW_TO_USE
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("lookup", help="living-environment deciles for a postcode or an LSOA code")
    p.add_argument("--postcode")
    p.add_argument("--lsoa", help="LSOA code (2021), e.g. E01001567")
    p.add_argument("--csv", help="use this File 7 CSV instead of downloading (tests, offline)")
    p.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.cmd != "lookup" or not (args.postcode or args.lsoa):
        ap.print_help()
        return 2
    out = lookup(postcode=args.postcode, lsoa=args.lsoa, csv_path=args.csv, verbose=args.verbose)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
