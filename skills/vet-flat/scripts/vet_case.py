#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vet_case.py — the fixed vetting chain for one flat, in one command, with explicit data states.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - MIT

    vet_case.py --postcode "SE1 9SG" --flat 4 --building "Corbel House" --rent-pcm 1950 --area-m2 48 \\
                --agent "Orrin & Vale" --destination "Strand, London" --commute-max 45
    vet_case.py --listing saved-page.html --rent-pcm 2100          # fields read from the page first
    vet_case.py --postcode "SE1 9SG" --fixture canned.json          # no network: canned register outputs

Why it exists (2026-09-15). The replayed conversations showed that about half of what a cheap model
misses against the original answers is work the skill already asks for: a register not run, a
certificate not matched, "no result" read as "fine". The skill's plan scaffold (`plan.py`) lists the
chain but never runs it. This script runs it, in a fixed order, and returns the outcome as states a
model cannot soften:

  identity        exact | ambiguous | unresolved      which flat the register evidence is about
  register.state  ok | not_found | unreachable | not_applicable | skipped
  check.state     pass | flag | unknown | not_applicable
  check.scope     unit | building | street | area | journey | management

Rules the code enforces, so the reply does not have to remember them:
  * unknown never becomes pass. A register that could not be reached, or answered nothing, leaves the
    check unknown with a `next_step` that says what would settle it.
  * a register that lists only bad news (rogue landlords, redress schemes, Heat Trust members) can say
    flag or unknown, never pass: absence is not a clean record (evidence class U).
  * unit-scope facts need an exact identity. With an ambiguous identity the certificate figures are
    given as the building's range, and the unit-level check stays unknown.
  * there is no overall verdict field. The states are the answer; the report contract decides words.

Registers, in this order, all imported as modules (shared spacing and cache, never a subprocess):
  postcodes.io (geo) → energy certificates (epc: search, match, cert, building) → HM Land Registry
  (landregistry) → the area scan (area_scan: crime, planning, roads, noise, in parallel with its own
  deadline) → Companies House + redress registers (company, redress) → TfL (commute) → arithmetic
  (deposit cap, price per square metre; the same rules as calc.py, quoted as computed).
Every fetch has a wall-clock budget (`--deadline-seconds`, default 240); a register still running at
the deadline is recorded as unreachable ("timed out"), never as clean.

Output: one JSON document (schema vet-flat/vet-case/1); `how_to_use` first, then `identity`,
`checks[]`, `next_steps[]`, `registers`, `not_found[]` (report-contract shape), `sources[]`, `timing`.
A copy is saved under `.pea-state/vet-cases/` unless `--no-save`; the path goes to stderr.
Standard library only, Python 3.9.
"""
from __future__ import print_function, unicode_literals

import argparse
import io
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import area_scan  # noqa: E402
import commute  # noqa: E402
import company  # noqa: E402
import epc  # noqa: E402
import geo  # noqa: E402
import landregistry  # noqa: E402
import redress  # noqa: E402

try:
    import listing_fields  # noqa: E402
except Exception:  # noqa: BLE001
    listing_fields = None

SCHEMA = "vet-flat/vet-case/1"
HOW_TO_USE = ("Each check carries a state. pass: checked, nothing to act on. flag: checked, needs the person's "
              "attention. unknown: could not be checked; next_step says what would settle it. not_applicable: no "
              "input for it. There is no overall verdict: unknown never becomes pass, and a register that lists only "
              "bad news (rogue landlords, redress schemes) can only say flag or unknown. scope says what the evidence "
              "is about: this unit, the whole building, the street, the area around the point, the journey, or the "
              "people managing it. Quote value and source together; keep the state words out of the reply.")
NOISE_FLAG_DB = 65.0          # Defra road Lden at or above this: a busy-road level at the facade
NOISE_QUIET_DB = 55.0         # below this: quiet by the model (WHO night guidance sits lower still)
MAIN_ROAD_M = 60              # a trunk or primary road within this distance of the point
RAIL_M = 100                  # surface rail or tube within this distance
AREA_TOLERANCE = 0.05         # advertised vs certificate floor area, relative
DEPOSIT_WEEKS_LOW, DEPOSIT_WEEKS_HIGH, DEPOSIT_ANNUAL_LINE = 5, 6, 50000.0


# ----------------------------------------------------------------------------- helpers --
def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def register_state(res):
    """Classify one register call's result: ok, not_found or unreachable (never pass/fail)."""
    if res is None:
        return "unreachable", "no result"
    if isinstance(res, Exception):
        return "unreachable", "%s: %s" % (type(res).__name__, str(res)[:120])
    if not isinstance(res, dict):
        return "unreachable", "unexpected result type %s" % type(res).__name__
    if res.get("scan_status"):   # the area scan: its own status vocabulary, and not_found[] holds coverage notes
        st = res["scan_status"]
        notes = "; ".join(str(x) for x in (res.get("not_found") or [])[:3])
        return ("ok" if st in ("complete", "partial") else "unreachable"), ("%s%s" % (st, ": " + notes if notes else ""))[:160]
    if res.get("disambiguation"):
        return "unreachable", ("place not resolved: %s" % json.dumps(res["disambiguation"], ensure_ascii=False))[:160]
    nf = res.get("not_found")
    if res.get("ok") is False and not nf:
        return "unreachable", (res.get("note") or res.get("error") or "ok=false")[:160]
    if nf:
        if isinstance(nf, dict):
            note = nf.get("meaning") or nf.get("note") or "not found"
        elif isinstance(nf, (list, tuple)):
            note = "; ".join(str(x) for x in nf[:3]) or "not found"
        else:
            note = "not found"
        return "not_found", str(note)[:160]
    if res.get("no_results") or res.get("too_many_results"):
        return "not_found", "too many results to list" if res.get("too_many_results") else "no results"
    return "ok", (res.get("note") or "")[:160]


def run_all(jobs, deadline_s, fixture=None):
    """Run {name: callable} in daemon threads; a job still running at the deadline is 'timed out'."""
    results, threads, started = {}, {}, time.time()

    def run(name, fn):
        try:
            results[name] = fn()
        except Exception as exc:  # noqa: BLE001
            results[name] = exc

    for name, fn in jobs.items():
        if fixture is not None and name in fixture:
            results[name] = fixture[name]
            continue
        t = threading.Thread(target=run, args=(name, fn), name="vet-" + name)
        t.daemon = True
        t.start()
        threads[name] = t
    for name, t in threads.items():
        remaining = deadline_s - (time.time() - started)
        t.join(max(0.0, remaining))
        if t.is_alive():
            results[name] = TimeoutError("timed out after %d s" % deadline_s)
    return results


def unit_pattern(flat):
    """A word-boundary match for the flat number in a certificate address ('Flat 4', '4,', 'Apartment 4')."""
    n = re.sub(r"^(flat|apartment|apt|unit)\s*", "", (flat or "").strip().lower())
    if not n:
        return None
    return re.compile(r"(?<![0-9a-z])(?:(?:flat|apartment|apt|unit)\s*)?%s(?![0-9a-z])" % re.escape(n))


def match_certificates(rows, flat=None, building=None):
    pat = unit_pattern(flat)
    b = re.sub(r"\s+", " ", (building or "").strip().lower())
    kept = []
    for r in rows or []:
        addr = re.sub(r"\s+", " ", (r.get("address") or "").lower())
        if pat and not pat.search(addr):
            continue
        if b and b not in addr:
            continue
        kept.append(r)
    return kept


def resolve_identity(search, flat=None, building=None):
    """exact / ambiguous / unresolved from an energy-certificate search at the postcode."""
    state, note = register_state(search)
    if state == "unreachable":
        return {"state": "unresolved", "reason": "the energy certificate register could not be read (%s)" % note,
                "certificate": None, "candidates": 0, "register": state}
    rows = (search or {}).get("results") or []
    if not rows:
        why = "the register lists no certificate at this postcode" if state != "ok" else "no certificate rows came back"
        return {"state": "unresolved", "reason": why + "; the flat may be listed under another postcode, or never certified",
                "certificate": None, "candidates": 0, "register": state}
    if flat or building:
        kept = match_certificates(rows, flat, building)
        if len(kept) == 1:
            return {"state": "exact", "reason": "one certificate matches the flat given", "certificate": kept[0],
                    "candidates": len(rows), "register": state}
        if len(kept) > 1:
            return {"state": "ambiguous", "reason": "%d certificates match the flat given (re-issues or a lettered unit); the newest is not necessarily this letting" % len(kept),
                    "certificate": None, "candidates": len(rows), "matches": kept[:6], "register": state}
        return {"state": "unresolved", "reason": "none of the %d certificates at this postcode carries the flat given" % len(rows),
                "certificate": None, "candidates": len(rows), "register": state}
    if len(rows) == 1:
        return {"state": "exact", "reason": "the only certificate at this postcode", "certificate": rows[0],
                "candidates": 1, "register": state}
    return {"state": "ambiguous", "reason": "%d certificates at this postcode and no flat number given" % len(rows),
            "certificate": None, "candidates": len(rows), "matches": rows[:6], "register": state}


def deposit_cap(rent_pcm):
    annual = rent_pcm * 12.0
    weeks = DEPOSIT_WEEKS_HIGH if annual >= DEPOSIT_ANNUAL_LINE else DEPOSIT_WEEKS_LOW
    return {"cap_gbp": round(annual / 52.0 * weeks, 2), "weeks": weeks, "annual_rent_gbp": round(annual, 2),
            "formula": "rent_pcm * 12 / 52 * %d (annual rent %s £50,000)" % (weeks, ">=" if weeks == 6 else "<")}


def check(cid, name, scope, state, value=None, source=None, why="", next_step=None, evidence_class=None):
    if evidence_class is None:
        evidence_class = "U" if state == "unknown" else "I" if source == "computed" else "G"
    return {"id": cid, "name": name, "scope": scope, "state": state, "evidence_class": evidence_class,
            "value": value, "source": source, "why": why, "next_step": next_step}


# ------------------------------------------------------------------------------ chain --
def vet(postcode, flat=None, building=None, street=None, rent_pcm=None, area_m2=None, floor=None, deposit_gbp=None,
        agent=None, landlord=None, destination=None, commute_max=None, depth="standard", deadline_s=240,
        fixture=None, verbose=False):
    t0 = time.time()
    registers, checks, not_found, sources = {}, [], [], []
    inputs = {"postcode": postcode, "flat": flat, "building": building, "street": street, "rent_pcm": rent_pcm,
              "area_m2": area_m2, "floor": floor, "deposit_gbp": deposit_gbp, "agent": agent, "landlord": landlord,
              "destination": destination, "commute_max_min": commute_max, "depth": depth}

    def record(name, res, query):
        state, note = register_state(res)
        registers[name] = {"state": state, "note": note, "query": query}
        if isinstance(res, dict):
            if res.get("source_url"):
                sources.append({"register": name, "url": res.get("source_url"), "retrieved_at": res.get("retrieved_at")})
        return state

    # 1. location + identity (sequential: everything else hangs off them)
    first = run_all({"geo": lambda: geo.lookup(postcode), "epc_search": lambda: epc.search(postcode=postcode)}, deadline_s, fixture)
    where = first.get("geo")
    geo_state = record("geo", where, {"postcode": postcode})
    lat = lng = None
    if geo_state == "ok" and isinstance(where, dict):
        lat, lng = where.get("lat"), where.get("lng")
    identity = resolve_identity(first.get("epc_search"), flat, building)
    record("epc_search", first.get("epc_search"), {"postcode": postcode, "flat": flat, "building": building})

    # 2. the registers, in parallel, under one deadline
    jobs = {}
    cert_id = ((identity.get("certificate") or {}).get("certificate_id") or (identity.get("certificate") or {}).get("certificate_url"))
    if identity["state"] == "exact" and cert_id:
        jobs["epc_cert"] = lambda: epc.cert(cert_id)
    if depth != "lite" and identity["state"] != "unresolved":
        jobs["epc_building"] = lambda: epc.building(postcode=postcode, limit=12)
    jobs["sales"] = lambda: landregistry.price_paid(postcode, paon=building or None)
    if lat is not None or postcode:
        jobs["area"] = lambda: area_scan.scan(postcode=postcode, depth=depth, street=street, deadline_seconds=min(180, deadline_s))
    if agent:
        jobs["redress_cmp"] = lambda: redress.cmp_search(agent)
        jobs["company_agent"] = lambda: company.search(agent, limit=10)
    if landlord:
        jobs["company_landlord"] = lambda: company.search(landlord, limit=10)
    if agent or landlord:
        jobs["rogue"] = lambda: redress.rogue(name=landlord or agent)
    if destination:
        jobs["commute"] = lambda: commute.journey(postcode, destination, arrive="09:00")
    remaining = max(20.0, deadline_s - (time.time() - t0))
    res = run_all(jobs, remaining, fixture)
    for name in jobs:
        record(name, res.get(name), {"postcode": postcode} if name in ("epc_building", "sales", "area") else {"name": agent or landlord} if name in ("redress_cmp", "company_agent", "company_landlord", "rogue") else {"from": postcode, "to": destination} if name == "commute" else {"certificate": cert_id})

    # 3. checks -------------------------------------------------------------------------
    # C1 identity
    if identity["state"] == "exact":
        c = identity["certificate"] or {}
        checks.append(check("C1", "which flat the register evidence is about", "unit", "pass",
                            value={"address": c.get("address"), "certificate_id": c.get("certificate_id")},
                            source="energy certificate register", why=identity["reason"]))
    elif identity["state"] == "ambiguous":
        checks.append(check("C1", "which flat the register evidence is about", "building", "flag",
                            value={"certificates_at_postcode": identity["candidates"]}, source="energy certificate register",
                            why=identity["reason"], next_step="Ask which flat it is (number or certificate reference); until then every unit-level figure below is the building's range, not this flat's."))
    else:
        checks.append(check("C1", "which flat the register evidence is about", "unit", "unknown",
                            source="energy certificate register", why=identity["reason"],
                            next_step="Ask the agent for the energy certificate reference or the exact address as registered; a flat with no certificate cannot legally be let (unless exempt)."))
        not_found.append({"what": "an energy certificate for this flat", "queries_used": ["epc.search postcode=%s flat=%s" % (postcode, flat or "-")],
                          "where_looked": "find-energy-certificate.service.gov.uk", "next_step": "certificate reference from the agent"})

    cert = res.get("epc_cert") if isinstance(res.get("epc_cert"), dict) else None
    cert_ok = cert is not None and registers.get("epc_cert", {}).get("state") == "ok"
    bld = res.get("epc_building") if isinstance(res.get("epc_building"), dict) else None
    bld_summary = (bld or {}).get("summary") or {}
    bld_range = (bld_summary.get("floor_area_m2") or {}) if registers.get("epc_building", {}).get("state") == "ok" else {}

    # C2 floor area
    cert_area = _num((cert or {}).get("total_floor_area_m2")) if cert_ok else None
    if cert_area:
        if area_m2:
            diff = (area_m2 - cert_area) / cert_area
            state = "pass" if abs(diff) <= AREA_TOLERANCE else "flag"
            why = "advertised %.0f m² vs certificate %.0f m² (%+.0f%%)" % (area_m2, cert_area, diff * 100)
            nxt = None if state == "pass" else "The advert %s the certificate by %.0f%%; ask which figure the agent stands by and whether a balcony or hallway was counted." % ("overstates" if diff > 0 else "understates", abs(diff) * 100)
        else:
            state, why, nxt = "pass", "certificate says %.0f m²; the advert gives no area to compare" % cert_area, None
        checks.append(check("C2", "floor area", "unit", state, value={"certificate_m2": cert_area, "advertised_m2": area_m2}, source="energy certificate", why=why, next_step=nxt))
    elif bld_range.get("min") is not None:
        checks.append(check("C2", "floor area", "building", "unknown", value={"building_range_m2": [bld_range.get("min"), bld_range.get("max")], "advertised_m2": area_m2},
                            source="energy certificates of the building", why="no certificate is tied to this flat; the building's certificates run %s–%s m²" % (bld_range.get("min"), bld_range.get("max")),
                            next_step="Once the flat is identified, read its certificate for the measured area."))
    else:
        checks.append(check("C2", "floor area", "unit", "unknown", value={"advertised_m2": area_m2}, source=None,
                            why="no certificate read for this flat", next_step="Ask the agent for the certificate reference; the advertised area is the agent's figure, not a measurement."))

    # C3 energy rating (legal minimum E for a new letting unless exempt)
    rating = ((cert or {}).get("energy_rating") if cert_ok else None) or ((identity.get("certificate") or {}).get("rating") if identity["state"] == "exact" else None)
    if rating:
        rating = str(rating).strip().upper()[:1]
        checks.append(check("C3", "energy rating", "unit", "flag" if rating in ("F", "G") else "pass", value=rating, source="energy certificate",
                            why="rating %s; E is the legal minimum for a new letting unless an exemption is registered" % rating,
                            next_step=None if rating not in ("F", "G") else "Ask whether an exemption is registered; an F or G flat cannot legally be let without one, and bills will be high."))
    else:
        checks.append(check("C3", "energy rating", "unit", "unknown", source="energy certificate", why="no certificate tied to this flat", next_step="Comes with the certificate reference (see C1)."))

    # C4 heating
    heat = (cert or {}).get("heating_class") if cert_ok else None
    if heat and heat != "unknown":
        state = "flag" if heat in ("community_heat_network", "electric") else "pass"
        why = {"community_heat_network": "heat network: no supplier choice, the tariff is set by the network operator",
               "electric": "electric heating: usually the dearest to run", "gas_boiler": "gas boiler", "heat_pump": "heat pump"}.get(heat, heat)
        nxt = {"community_heat_network": "Ask for the heat tariff and standing charge in writing before signing, and whether the operator is a Heat Trust member.",
               "electric": "Ask for last winter's electricity bills or a tariff, and whether storage heaters or panel heaters."}.get(heat)
        checks.append(check("C4", "heating type", "unit", state, value=heat, source="energy certificate", why=why, next_step=nxt))
    else:
        checks.append(check("C4", "heating type", "unit", "unknown", source="energy certificate", why="no certificate tied to this flat", next_step="Comes with the certificate reference (see C1)."))

    # C5 floor position
    pos = ((cert or {}).get("floor_position") if cert_ok else None) or (str(floor).strip().lower() if floor not in (None, "") else None)
    if pos:
        top = pos in ("top", "penthouse") or "top" in pos
        checks.append(check("C5", "floor position", "unit", "flag" if top else "pass", value=pos, source="energy certificate" if cert_ok and (cert or {}).get("floor_position") else "advert",
                            why="top floor: summer heat under the roof and a lift question" if top else "not the top floor",
                            next_step="Ask which way the bedroom faces and whether a portable air conditioner is allowed; view on a warm afternoon." if top else None))
    else:
        checks.append(check("C5", "floor position", "unit", "unknown", why="neither the certificate nor the advert says which floor", next_step="Ask which floor and whether there is a lift."))

    # C6 sales history / age
    sales = res.get("sales") if isinstance(res.get("sales"), dict) else None
    s_state = registers.get("sales", {}).get("state")
    if s_state == "ok" and sales and (sales.get("count") or 0) > 0:
        checks.append(check("C6", "sales history and building age", "building", "pass",
                            value={"sales_at_postcode": sales.get("count"), "latest": sales.get("latest_transaction"), "earliest_new_build_year": sales.get("earliest_new_build_year"),
                                   "same_building_price_range": sales.get("same_building_price_range")},
                            source="HM Land Registry price paid", why="sales recorded at this postcode; a new-build sale dates the building, an older one bounds it"))
    elif s_state in ("not_found", "ok"):
        checks.append(check("C6", "sales history and building age", "building", "unknown", source="HM Land Registry price paid",
                            why="no sale recorded at this postcode: build-to-rent blocks are never sold flat by flat, and postcodes issued later have no history",
                            next_step="Ask the agent when the building completed and who the freeholder is."))
    else:
        checks.append(check("C6", "sales history and building age", "building", "unknown", source="HM Land Registry price paid",
                            why="the register could not be read (%s)" % registers.get("sales", {}).get("note"), next_step="Re-run later; the query is cached once it works."))

    # C7 deposit cap, C8 price per square metre (computed)
    if rent_pcm:
        cap = deposit_cap(float(rent_pcm))
        if deposit_gbp is not None:
            over = float(deposit_gbp) > cap["cap_gbp"] + 0.01
            checks.append(check("C7", "deposit against the legal cap", "unit", "flag" if over else "pass",
                                value={"advertised_gbp": deposit_gbp, "cap_gbp": cap["cap_gbp"], "weeks": cap["weeks"], "formula": cap["formula"]}, source="computed",
                                why="cap is %d weeks' rent = £%.2f" % (cap["weeks"], cap["cap_gbp"]) + ("; the advert asks more" if over else ""),
                                next_step="The deposit asked exceeds the Tenant Fees Act cap; ask for it to be corrected before paying anything." if over else None))
        else:
            checks.append(check("C7", "deposit against the legal cap", "unit", "pass", value={"cap_gbp": cap["cap_gbp"], "weeks": cap["weeks"], "formula": cap["formula"]},
                                source="computed", why="cap is %d weeks' rent = £%.2f; compare with what the agent asks" % (cap["weeks"], cap["cap_gbp"])))
        area_for_price = cert_area or area_m2
        if area_for_price:
            checks.append(check("C8", "rent per square metre", "unit", "pass", value={"gbp_per_m2_pcm": round(float(rent_pcm) / area_for_price, 2), "area_basis": "certificate" if cert_area else "advertised"},
                                source="computed", why="£%.0f pcm over %.0f m² (%s area)" % (float(rent_pcm), area_for_price, "certificate" if cert_area else "advertised")))
        else:
            checks.append(check("C8", "rent per square metre", "unit", "not_applicable", why="no floor area from any source"))
    else:
        checks.append(check("C7", "deposit against the legal cap", "unit", "not_applicable", why="no rent given"))
        checks.append(check("C8", "rent per square metre", "unit", "not_applicable", why="no rent given"))

    # C9–C12 the area scan
    area = res.get("area") if isinstance(res.get("area"), dict) else None
    a_state = registers.get("area", {}).get("state")
    works = (area or {}).get("works") if a_state in ("ok", "not_found") else None
    if works:
        notable = works.get("notable_recent") or []
        checks.append(check("C9", "building works nearby", "area", "flag" if notable else "pass",
                            value={"applications": works.get("count"), "within_m": works.get("applications_within_m"), "notable": [{"what": n.get("what") or n.get("description"), "distance_m": n.get("distance_m"), "status": n.get("status")} for n in notable[:3]]},
                            source="GLA planning datahub", why="%s applications within %s m; %d notable" % (works.get("count"), works.get("applications_within_m"), len(notable)) + ("; application records do not prove works are under way" if notable else ""),
                            next_step="Ask the agent and look at the site on the visit: is the notable application under construction, and which side of the flat faces it?" if notable else None))
    else:
        checks.append(check("C9", "building works nearby", "area", "unknown", source="GLA planning datahub", why="planning register not read (%s)" % (registers.get("area", {}).get("note") or "no scan"), next_step="Re-run the area scan; search the borough's planning portal by street if it stays down."))
    noise = (area or {}).get("noise") if a_state in ("ok", "not_found") else None
    db = (noise or {}).get("road_lden_db")
    if noise and (db is not None or noise.get("road_lden_db") == "not drawn"):
        if db == "not drawn" or (_num(db) is None):
            checks.append(check("C10", "road noise at the point", "area", "pass", value="below the map's floor", source="Defra strategic noise map", evidence_class="G",
                                why="nothing drawn here: the modelled level is under the map's lowest band; a model of outdoor noise, not a measurement at any window"))
        else:
            dbf = _num(db)
            state = "flag" if dbf >= NOISE_FLAG_DB else "pass"
            checks.append(check("C10", "road noise at the point", "area", state, value={"road_lden_db": dbf, "rail_lden_db": noise.get("rail_lden_db")}, source="Defra strategic noise map", evidence_class="G",
                                why="%.0f dB day-evening-night average at the scan point (%s); a 10 m grid model at 4 m height, not a window" % (dbf, "busy-road level" if dbf >= NOISE_FLAG_DB else "moderate" if dbf >= NOISE_QUIET_DB else "quiet by the model"),
                                next_step="Ask which side the bedroom faces and whether the windows are double-glazed; listen on the visit at night." if state == "flag" else None))
    else:
        checks.append(check("C10", "road noise at the point", "area", "unknown", source="Defra strategic noise map", why="noise map not read", next_step="Re-run the area scan; the road and rail distances in C11 are the fallback."))
    quiet = (area or {}).get("quiet") if a_state in ("ok", "not_found") else None
    if quiet:
        main = quiet.get("main_road_nearest_m"); rail = [d for d in (quiet.get("railway_surface_nearest_m"), quiet.get("tube_surface_nearest_m")) if d is not None]
        near_main = main is not None and main <= MAIN_ROAD_M; near_rail = bool(rail) and min(rail) <= RAIL_M
        checks.append(check("C11", "main road and rail nearby", "street", "flag" if (near_main or near_rail) else "pass",
                            value={"main_road_m": main, "main_road_names": (quiet.get("main_road_names") or [])[:2], "rail_or_tube_m": min(rail) if rail else None, "night_economy_count": quiet.get("night_economy_count")},
                            source="OpenStreetMap", evidence_class="C", why=("main road at %d m" % main if main is not None else "no main road within the radius") + ("; rail or tube at %d m" % min(rail) if rail else ""),
                            next_step="Check which facade the bedroom is on relative to that road or line." if (near_main or near_rail) else None))
    else:
        checks.append(check("C11", "main road and rail nearby", "street", "unknown", source="OpenStreetMap", why="road map not read", next_step="Re-run the area scan."))
    crime = (area or {}).get("crime") if a_state in ("ok", "not_found") else None
    if crime and crime.get("total") is not None:
        checks.append(check("C12", "recorded crime around the point", "area", "pass", value={"total": crime.get("total"), "months": crime.get("months"), "per_month": crime.get("per_month_avg") or crime.get("per_month"), "top_categories": (crime.get("top_categories") or [])[:3], "reading": crime.get("reading")},
                            source="data.police.uk", why="context, never a filter: counts in a box around the point, locations anonymised to snap points"))
    else:
        checks.append(check("C12", "recorded crime around the point", "area", "unknown", source="data.police.uk", why="police data not read", next_step="Re-run the area scan."))

    # C13–C15 management (absence-only registers: flag or unknown, never pass — except a positive CMP/company match)
    if agent:
        cmp_ = res.get("redress_cmp") if isinstance(res.get("redress_cmp"), dict) else None
        st = registers.get("redress_cmp", {}).get("state")
        if st == "ok" and cmp_ and (cmp_.get("count") or 0) > 0:
            checks.append(check("C13", "agent's client money protection", "management", "pass", value={"scheme": "Client Money Protect", "matches": cmp_.get("count")}, source="CMP member search", why="the agent is listed by one government-approved scheme"))
        elif st in ("ok", "not_found"):
            checks.append(check("C13", "agent's client money protection", "management", "unknown", value={"scheme_checked": "Client Money Protect"}, source="CMP member search", evidence_class="U",
                                why="not listed by this scheme; it is one of six approved schemes, so this is not proof of no cover", next_step="Ask the agent which client money protection scheme they belong to and check that scheme's register."))
        else:
            checks.append(check("C13", "agent's client money protection", "management", "unknown", source="CMP member search", why="register not read (%s)" % registers.get("redress_cmp", {}).get("note"), next_step="Ask the agent for their scheme certificate."))
    else:
        checks.append(check("C13", "agent's client money protection", "management", "not_applicable", why="no agent name given"))
    who = landlord or agent
    if who:
        key = "company_landlord" if landlord else "company_agent"
        co = res.get(key) if isinstance(res.get(key), dict) else None
        st = registers.get(key, {}).get("state")
        if st == "ok" and co and (co.get("count") or 0) > 0:
            active = [r for r in (co.get("results") or []) if str(r.get("status") or "").lower().startswith("active")]
            state = "pass" if active else "flag"
            checks.append(check("C14", "the company behind the name", "management", state, value={"matches": co.get("count"), "active": len(active), "dissolved": co.get("dissolved_count"), "same_name_warning": co.get("same_name_warning")},
                                source="Companies House", why="%d companies match the name, %d active" % (co.get("count") or 0, len(active)) + ("; a brand is not the landlord" if co.get("same_name_warning") else ""),
                                next_step="Ask for the exact company name and number on the tenancy before paying; the name matches only dissolved companies." if not active else None))
        elif st in ("ok", "not_found"):
            checks.append(check("C14", "the company behind the name", "management", "unknown", source="Companies House", evidence_class="U", why="no company of that name found; private landlords are not companies, and trading names differ from registered ones",
                                next_step="Ask for the registered company name and number, or the landlord's full name and address (a legal right before signing)."))
        else:
            checks.append(check("C14", "the company behind the name", "management", "unknown", source="Companies House", why="register not read (%s)" % registers.get(key, {}).get("note"), next_step="Re-run later."))
        rg = res.get("rogue") if isinstance(res.get("rogue"), dict) else None
        st = registers.get("rogue", {}).get("state")
        if st == "ok" and rg and (rg.get("count") or 0) > 0:
            checks.append(check("C15", "rogue landlord and agent checker", "management", "flag", value={"entries": rg.get("count")}, source="GLA rogue landlord checker", why="an enforcement entry matches the name", next_step="Read the entry: which offence, which year, and is it the same legal person?"))
        elif st in ("ok", "not_found"):
            checks.append(check("C15", "rogue landlord and agent checker", "management", "unknown", value={"entries": 0}, source="GLA rogue landlord checker", evidence_class="U",
                                why="no entry for the name: the checker lists enforcement outcomes only, so absence is not a clean record; nothing settles this, weigh reviews and the deposit scheme certificate instead", next_step=None))
        else:
            checks.append(check("C15", "rogue landlord and agent checker", "management", "unknown", source="GLA rogue landlord checker", why="checker not read (%s)" % registers.get("rogue", {}).get("note"), next_step="Re-run later."))
    else:
        checks.append(check("C14", "the company behind the name", "management", "not_applicable", why="no agent or landlord name given"))
        checks.append(check("C15", "rogue landlord and agent checker", "management", "not_applicable", why="no agent or landlord name given"))

    # C16 commute
    if destination:
        j = res.get("commute") if isinstance(res.get("commute"), dict) else None
        st = registers.get("commute", {}).get("state")
        fastest = _num((j or {}).get("fastest_min")) if st == "ok" else None
        if fastest is not None:
            over = commute_max is not None and fastest > float(commute_max)
            checks.append(check("C16", "commute to the destination", "journey", "flag" if over else "pass",
                                value={"fastest_min": fastest, "rail_only_min": j.get("rail_only_min"), "bus_only_min": j.get("bus_only_min"), "ceiling_min": commute_max, "arrive_by": "09:00"},
                                source="TfL journey planner", why="a timetable plan, not a measured trip%s" % ("; over the %s-minute ceiling" % commute_max if over else ""),
                                next_step="Over the ceiling the person set; ask before treating this flat as a candidate, and check the walk to the station on the visit." if over else None))
        else:
            checks.append(check("C16", "commute to the destination", "journey", "unknown", source="TfL journey planner", why="no plan came back (%s)" % (registers.get("commute", {}).get("note") or "unknown"),
                                next_step="Give the destination as a postcode or station name and re-run."))
    else:
        checks.append(check("C16", "commute to the destination", "journey", "not_applicable", why="no destination given"))

    # C17 Heat Trust when on a heat network
    if heat == "community_heat_network":
        ht = run_all({"heat_trust": lambda: redress.heat_trust(site=building or postcode)}, 30, fixture).get("heat_trust")
        st = record("heat_trust", ht, {"site": building or postcode})
        if st == "ok" and isinstance(ht, dict) and (ht.get("match_count") or 0) > 0:
            checks.append(check("C17", "heat network operator in Heat Trust", "building", "pass", value={"matches": ht.get("match_count")}, source="Heat Trust member list", why="a member site or supplier matches"))
        else:
            checks.append(check("C17", "heat network operator in Heat Trust", "building", "unknown", source="Heat Trust member list", evidence_class="U", why="no member match for the site name; membership is voluntary, so absence is not a verdict",
                                next_step="Ask the agent who operates the heat network and whether it is a Heat Trust member."))
    else:
        checks.append(check("C17", "heat network operator in Heat Trust", "building", "not_applicable", why="not on a heat network, or heating unknown"))

    # 4. next steps, code-generated: identity first, then blocking unknowns, then flags
    order = {"C1": 0, "unknown": 1, "flag": 2}
    steps = []
    for c in sorted(checks, key=lambda c: (0 if c["id"] == "C1" else order.get(c["state"], 3), c["id"])):
        if c.get("next_step") and c["state"] in ("unknown", "flag") and c["next_step"] not in steps:
            steps.append(c["next_step"])
    counts = {s: sum(1 for c in checks if c["state"] == s) for s in ("pass", "flag", "unknown", "not_applicable")}
    for name, r in registers.items():
        if r["state"] == "unreachable":
            not_found.append({"what": "%s (register unreachable)" % name, "queries_used": [json.dumps(r["query"], ensure_ascii=False)], "where_looked": name, "next_step": "re-run; the call is cached once it succeeds"})
    for c in checks:
        if c["state"] == "unknown" and c["id"] != "C1" and c.get("next_step"):
            not_found.append({"what": c["name"], "queries_used": [json.dumps(registers.get(k, {}).get("query") or {}, ensure_ascii=False) for k in registers][:1] or ["-"], "where_looked": c.get("source") or "-", "next_step": c["next_step"][:240]})
    out = {"how_to_use": HOW_TO_USE, "schema": SCHEMA, "ok": True, "retrieved_at": _now(), "inputs": inputs,
           "where": {"lat": lat, "lng": lng, "admin_district": (where or {}).get("admin_district") if isinstance(where, dict) else None, "state": geo_state},
           "identity": identity, "checks": checks, "summary": counts, "next_steps": steps[:8], "registers": registers,
           "not_found": not_found, "sources": sources, "verdict": None,
           "verdict_note": "no overall verdict by design; the report contract turns the states into words",
           "area_scan_status": (area or {}).get("scan_status") if isinstance(area, dict) else None,
           "timing": {"seconds": round(time.time() - t0, 1), "deadline_seconds": deadline_s}}
    return out


# --------------------------------------------------------------------------------- CLI --
def listing_inputs(path):
    """Fields from a saved page or pasted text, through listing_fields.py (no network)."""
    if listing_fields is None:
        return {}
    raw = io.open(path, "rb").read()
    kind = "saved_page" if path.lower().endswith((".html", ".htm", ".mhtml")) else "pasted_text"
    try:
        out = listing_fields.extract(raw, kind)
    except Exception:  # noqa: BLE001
        return {}
    f = (out or {}).get("fields") or {}
    got = {}
    if f.get("postcode"):
        got["postcode"] = f["postcode"].get("value")
    if f.get("rent") and f["rent"].get("unit") == "GBP/month":
        got["rent_pcm"] = _num(f["rent"].get("value"))
    if f.get("floor_area"):
        v = _num(f["floor_area"].get("value"))
        if v is not None:
            got["area_m2"] = round(v * 0.092903, 1) if f["floor_area"].get("unit") == "sq_ft" else v
    if f.get("floor"):
        got["floor"] = f["floor"].get("value")
    if f.get("deposit"):
        got["deposit_gbp"] = _num(f["deposit"].get("value"))
    return got


def save_copy(out, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", "%s-%s" % (out["inputs"].get("postcode") or "x", out["inputs"].get("flat") or "unit")).strip("-").lower()
    path = os.path.join(out_dir, "%s-%s.json" % (slug, time.strftime("%Y%m%dT%H%M%S")))
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--postcode")
    ap.add_argument("--flat", help="flat number or letter as the advert gives it (4, 4B, 'Flat 4')")
    ap.add_argument("--building", help="building name, if any")
    ap.add_argument("--street")
    ap.add_argument("--rent-pcm", type=float)
    ap.add_argument("--area-m2", type=float, help="advertised floor area in square metres")
    ap.add_argument("--floor", help="advertised floor (ground, 3, top, penthouse)")
    ap.add_argument("--deposit", type=float, help="advertised deposit in pounds")
    ap.add_argument("--agent", help="letting agent's name")
    ap.add_argument("--landlord", help="landlord's or management company's name")
    ap.add_argument("--destination", help="commute destination (postcode, station or place name)")
    ap.add_argument("--commute-max", type=float, help="the person's commute ceiling in minutes")
    ap.add_argument("--depth", choices=("lite", "standard"), default="standard")
    ap.add_argument("--listing", help="saved page or pasted text: fields are read from it first (flags override)")
    ap.add_argument("--fixture", help="JSON of canned register outputs keyed by register name (tests; no network for those)")
    ap.add_argument("--deadline-seconds", type=int, default=240)
    ap.add_argument("--out", default=os.path.join(".pea-state", "vet-cases"))
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    got = listing_inputs(a.listing) if a.listing else {}
    postcode = a.postcode or got.get("postcode")
    if not postcode:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": "no postcode: give --postcode or a --listing that states one"}, ensure_ascii=False))
        return 2
    fixture = json.load(io.open(a.fixture, encoding="utf-8")) if a.fixture else None
    out = vet(postcode, flat=a.flat, building=a.building, street=a.street, rent_pcm=a.rent_pcm or got.get("rent_pcm"),
              area_m2=a.area_m2 or got.get("area_m2"), floor=a.floor or got.get("floor"), deposit_gbp=a.deposit if a.deposit is not None else got.get("deposit_gbp"),
              agent=a.agent, landlord=a.landlord, destination=a.destination, commute_max=a.commute_max, depth=a.depth,
              deadline_s=a.deadline_seconds, fixture=fixture, verbose=a.verbose)
    if not a.no_save:
        try:
            print("saved copy: %s" % save_copy(out, a.out), file=sys.stderr)
        except OSError as exc:
            print("could not save a copy: %s" % exc, file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
