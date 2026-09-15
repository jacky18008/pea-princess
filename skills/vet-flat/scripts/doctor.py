#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Is this install working? One command, no side effects: the interpreter and curl, the skill's own files, its
arithmetic on a fixed example, and one tiny request to each open register the scripts use, with the time it
took. Prints a plain report a person can paste into a bug report; exit code 0 = everything usable.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

    doctor.py                # everything
    doctor.py --offline      # no network: files, interpreter, arithmetic only
    doctor.py --json

The network checks read only open registers already used by the skill (postcodes.io, data.police.uk, the
EPC register, the GLA Planning Datahub, Overpass, Defra's noise map, TfL, Companies House, the Land Registry)
with a fixed London postcode, cached for a day like every other call; nothing is written anywhere.
Standard library only, Python 3.9.
"""
from __future__ import unicode_literals

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

POSTCODE = "SE1 9SG"
LAT, LNG = 51.5045, -0.0865


def check(name, fn, need=None):
    t0 = time.time()
    try:
        ok, note = fn()
    except Exception as exc:  # noqa: BLE001 - a failed check is a finding, not a crash
        ok, note = False, "%s: %s" % (type(exc).__name__, str(exc)[:120])
    return {"check": name, "ok": bool(ok), "note": note or "", "seconds": round(time.time() - t0, 1), "needed_for": need or "everything"}


def offline_checks():
    out = []
    out.append(check("python 3.9 or newer", lambda: (sys.version_info >= (3, 9), "python %d.%d" % sys.version_info[:2])))
    out.append(check("curl on PATH", lambda: (shutil.which("curl") is not None, shutil.which("curl") or "not found: the register scripts fetch with curl"), "every register check"))
    for rel in ("SKILL.md", "references/rules.md", "references/axes/README.md", "references/report-schema.json", "scripts/calc.py", "scripts/area_scan.py", "scripts/reply_check.py"):
        out.append(check("skill file " + rel, lambda rel=rel: (os.path.exists(os.path.join(ROOT, rel)), os.path.join(ROOT, rel))))
    def arithmetic():
        import calc
        proc = subprocess.run([sys.executable, os.path.join(HERE, "calc.py"), "deposit", "--rent-pcm", "2000"], capture_output=True, text=True, timeout=30)
        d = json.loads(proc.stdout or "{}")
        return (proc.returncode == 0 and bool(d.get("result")), "deposit cap for £2,000 pcm: %s" % json.dumps(d.get("result"), ensure_ascii=False)[:80])
    out.append(check("arithmetic (calc.py deposit)", arithmetic, "every money answer"))
    def checker():
        import reply_check
        f = reply_check.scan("押金最多 5 週房租。")
        return (any(x["kind"] == "numbers" for x in f), "flags a figure without a source, as it should")
    out.append(check("pre-send checker (reply_check.py)", checker, "the checkpoint"))
    return out


def network_checks(verbose=False):
    out = []
    def geo_():
        import geo
        g = geo.lookup(POSTCODE, verbose)
        return (bool(g.get("ok")) and g.get("lat") is not None, "%s → %s, %s" % (POSTCODE, g.get("admin_district"), g.get("admin_ward")))
    out.append(check("postcodes.io (postcode → point)", geo_, "identity, area, every scan"))
    def crime_():
        import crime
        r = crime.latest(verbose)
        return (bool(r.get("ok")), "latest month %s" % r.get("latest_month"))
    out.append(check("data.police.uk (crime)", crime_, "axis 05, the street scan"))
    def epc_():
        import epc
        r = epc.search(POSTCODE)
        return (bool(r.get("ok")), "%s certificates at %s" % (r.get("count"), POSTCODE))
    out.append(check("EPC register (find-energy-certificate)", epc_, "axes 01–03, 08"))
    def planning_():
        import planning
        r = planning.near(LAT, LNG, 150, verbose=verbose)
        return (bool(r.get("ok")), "%s applications within 150 m" % (r.get("total_matching") or r.get("count")))
    out.append(check("GLA Planning Datahub", planning_, "axis 04, the street scan"))
    def roads_():
        import roads
        r = roads.near(LAT, LNG, 150, verbose=verbose)
        return (bool(r.get("ok")), "%s map elements within 150 m" % r.get("element_count"))
    out.append(check("OpenStreetMap via Overpass", roads_, "axes 04, 09, 12, the street scan"))
    def noise_():
        import noise
        r = noise.level(LAT, LNG, "road", "lden", verbose=verbose)
        return (bool(r.get("ok")), "road Lden at the point: %s dB" % r.get("db"))
    out.append(check("Defra strategic noise map", noise_, "the street scan (noise)"))
    def living_():
        import living_env
        r = living_env.lookup(postcode=POSTCODE, verbose=verbose)
        return (bool(r.get("ok")), "living-environment decile %s" % ((r.get("living_environment") or {}).get("decile")))
    out.append(check("Indices of Deprivation 2025 (living environment)", living_, "axis 12"))
    def commute_():
        import commute
        r = commute.journey(POSTCODE, "WC2R 2LS", verbose=verbose)
        return (bool(r.get("ok")), "fastest %s min (rail %s, bus %s)" % (r.get("fastest_min"), r.get("rail_only_min"), r.get("bus_only_min")))
    out.append(check("TfL journey planner", commute_, "axis 11"))
    def landreg_():
        import landregistry
        r = landregistry.price_paid(POSTCODE, verbose=verbose)
        return (bool(r.get("ok")), "%s sales on record" % r.get("count"))
    out.append(check("HM Land Registry price paid", landreg_, "axes 03, 08"))
    def company_():
        import company
        r = company.search("Get Living", limit=3, verbose=verbose)
        return (bool(r.get("ok")), "%s companies matched" % (r.get("count") or len(r.get("results") or [])))
    out.append(check("Companies House", company_, "axis 07"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    results = offline_checks()
    if not a.offline:
        results += network_checks(a.verbose)
    bad = [r for r in results if not r["ok"]]
    summary = {"ok": not bad, "checks": len(results), "failed": len(bad), "skill_root": ROOT, "results": results,
               "reading": ("Everything this skill needs is working." if not bad else
                           "%d of %d checks failed; the axes listed under needed_for will come back unknown until they pass." % (len(bad), len(results)))}
    if a.json:
        json.dump(summary, sys.stdout, ensure_ascii=False, indent=1); print()
    else:
        for r in results:
            print("%s %-48s %5.1fs  %s" % ("OK " if r["ok"] else "BAD", r["check"], r["seconds"], r["note"]))
        print("\n" + summary["reading"])
        for r in bad:
            print("  - %s: needed for %s" % (r["check"], r["needed_for"]))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
