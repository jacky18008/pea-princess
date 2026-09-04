#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the truth data behind evals/evals.json by running the repo's own fetchers.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

Why this exists
---------------
The benchmark grades facts, not verdicts, so the facts have to be right today.
Some of them move: police.uk publishes a new data month every month, so a
six-month crime total changes every month; TfL journey times change with the
timetable. This script re-runs every fetcher for every case, writes the raw
output to ``evals/truth/<case>/<script>-<sub>.json`` and rewrites the
``expected_facts`` block of each case with fresh values, each carrying the exact
command that produced it and the ``retrieved_at`` stamp from the fetcher.

It never invents a value. If a fetcher fails, the previous value is kept and the
block is marked ``stale`` with the reason, so a transient network failure cannot
quietly replace real truth with a hole.

The two conversation cases (``explain-capabilities``, ``no-idea-intake``) are
skipped: their truth is the skill's own text - SKILL.md and
references/onboarding.md - not a public register, so no fetcher can refresh them.
Update those two by hand when the pitch, the intake questions or the law changes.

Standard library only. Python 3.9. Network I/O happens inside the fetchers,
which throttle and cache themselves; this script also pauses between subprocess
calls because each subprocess starts with an empty in-process throttle.

Usage:
  bench/refresh_truth.py                      # every case
  bench/refresh_truth.py --case e14-marsh-wall-301 --case e8-kingsland-high-street-2
  bench/refresh_truth.py --dry-run            # print the commands, fetch nothing
  bench/refresh_truth.py --only epc,crime     # refresh some blocks only

Exit codes: 0 all blocks refreshed, 1 at least one block is stale, 2 usage error.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join("skills", "vet-flat", "scripts")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")
TRUTH_DIR = os.path.join(ROOT, "evals", "truth")
PRIVATE_TRUTH_DIR = os.path.join(ROOT, "bench", "private", "truth")  # cases from bench/private never write to the public tree


def truth_dir_for(evals_path):
    """Public cases keep evals/truth/; anything under bench/private/ writes to bench/private/truth/."""
    if evals_path and os.path.abspath(evals_path).startswith(os.path.join(ROOT, "bench", "private")):
        return PRIVATE_TRUTH_DIR
    return TRUTH_DIR

BLOCKS = ["epc", "crime", "commute", "company", "landregistry"]
PAUSE_S = 1.5


# ------------------------------------------------------------------ running --
def script_cmd(script, *args):
    """The command as a maintainer would type it, from the repository root."""
    return ["python3", os.path.join(SCRIPTS, script)] + [str(a) for a in args]


def shell(cmd):
    return " ".join(quote(part) for part in cmd)


def quote(part):
    if part and all(c.isalnum() or c in "-_./:=" for c in part):
        return part
    return "'" + part.replace("'", "'\\''") + "'"


class Runner(object):
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.calls = 0

    def run(self, cmd, timeout=300):
        """Run a fetcher and return (parsed_json_or_None, error_or_None)."""
        line = shell(cmd)
        if self.dry_run:
            print("  would run: " + line, file=sys.stderr)
            return None, "dry-run"
        if self.calls:
            time.sleep(PAUSE_S)
        self.calls += 1
        print("  $ " + line, file=sys.stderr)
        try:
            proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "timed out after %d s" % timeout
        except OSError as exc:
            return None, "could not start: %s" % exc
        if proc.returncode != 0:
            tail = (err or b"").decode("utf-8", "replace").strip().splitlines()
            return None, "exit %d: %s" % (proc.returncode, tail[-1] if tail else "no message")
        try:
            return json.loads((out or b"").decode("utf-8", "replace")), None
        except ValueError as exc:
            return None, "output was not JSON: %s" % exc


def save_raw(case_id, name, payload):
    d = os.path.join(truth_dir_for(getattr(args_ns, "evals", None)) if "args_ns" in globals() else TRUTH_DIR, case_id)
    if not os.path.isdir(d):
        os.makedirs(d)
    path = os.path.join(d, name + ".json")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n")
    return os.path.relpath(path, ROOT)


def od(*pairs):
    return collections.OrderedDict([p for p in pairs if p is not None])


# ------------------------------------------------------------------- blocks --
def refresh_epc(case, runner, previous):
    """epc.py cert --history: floor area, first assessment year, heating, floor, rating."""
    cid = case["truth_inputs"]["epc_certificate_id"]
    cmd = script_cmd("epc.py", "cert", cid, "--history")
    data, err = runner.run(cmd)
    if err:
        return stale(previous, err, shell(cmd))
    if not data.get("ok"):
        return stale(previous, "fetcher reported ok=false: %s" % data.get("note"), shell(cmd))
    raw = save_raw(case["id"], "epc-cert", data)

    search_cmd = script_cmd("epc.py", "search", "--postcode", case["truth_inputs"]["postcode"])
    sdata, serr = runner.run(search_cmd)
    search_raw = save_raw(case["id"], "epc-search", sdata) if sdata else None

    return od(
        ("certificate_id", data.get("certificate_id")),
        ("register_address", data.get("address")),
        ("floor_area_m2", data.get("total_floor_area_m2")),
        ("floor_area_sqft", data.get("total_floor_area_sqft")),
        ("first_assessment_year", data.get("first_assessment_year")),
        ("heating_class", data.get("heating_class")),
        ("floor_position", data.get("floor_position")),
        # A certificate with no property type states no floor. That is a VERIFIED
        # absence, not a gap in this benchmark, so the grader requires the report to
        # leave it unknown rather than guessing a floor from the flat number.
        ("floor_position_absent", data.get("floor_position") is None),
        ("energy_rating", data.get("energy_rating")),
        ("property_type", data.get("property_type")),
        ("air_permeability", data.get("air_permeability")),
        ("earlier_certificates", data.get("other_certificates") or []),
        ("retrieved_at", data.get("retrieved_at")),
        ("command", shell(cmd)),
        ("raw", raw),
        ("search_command", shell(search_cmd)),
        ("search_raw", search_raw),
        ("search_note", serr),
    )


def refresh_crime(case, runner, previous, geo):
    """crime.py box: a fixed six-month window in a 300 m box around the postcode centroid."""
    if not geo:
        return stale(previous, "no coordinates: the postcode lookup failed", None)
    spec = case["truth_inputs"].get("crime") or {}
    half = spec.get("box_half_m", 150)
    months = spec.get("months", 6)
    cmd = script_cmd("crime.py", "box", "--lat", geo["lat"], "--lng", geo["lng"],
                     "--half-m", half, "--months", months)
    data, err = runner.run(cmd, timeout=900)
    if err:
        return stale(previous, err, shell(cmd))
    if not data.get("ok"):
        return stale(previous, "fetcher reported ok=false: %s" % data.get("note"), shell(cmd))
    raw = save_raw(case["id"], "crime-box", data)
    pred = data.get("predatory_subset") or {}
    anchors = data.get("top_anchors") or []
    return od(
        ("box_half_m", half),
        ("months", data.get("months_fetched") or []),
        ("months_missing", data.get("months_missing") or []),
        ("total", data.get("total")),
        ("tolerance_pct", 15),
        ("predatory_count", pred.get("count")),
        ("top_anchor", (anchors[0] or {}).get("anchor") if anchors else None),
        ("top_anchor_share", (anchors[0] or {}).get("share_of_total") if anchors else None),
        ("centre", {"lat": geo["lat"], "lng": geo["lng"]}),
        ("retrieved_at", data.get("retrieved_at")),
        ("command", shell(cmd)),
        ("raw", raw),
    )


def refresh_commute(case, runner, previous, geo):
    """commute.py journey + redundancy: door-to-door minutes and the strike-family grade."""
    spec = case["truth_inputs"].get("commute") or {}
    dest = spec.get("destination")
    arrive = spec.get("arrive", "09:00")
    cmd = script_cmd("commute.py", "journey", "--from", case["truth_inputs"]["postcode"],
                     "--to", dest, "--arrive", arrive)
    data, err = runner.run(cmd, timeout=180)
    if err:
        return stale(previous, err, shell(cmd))
    if not data.get("ok", True):
        return stale(previous, "fetcher reported ok=false: %s" % data.get("note"), shell(cmd))
    raw = save_raw(case["id"], "commute-journey", data)

    grade, red_raw, red_cmd = None, None, None
    if geo:
        rcmd = script_cmd("commute.py", "redundancy", "--lat", geo["lat"], "--lng", geo["lng"])
        rdata, rerr = runner.run(rcmd, timeout=180)
        red_cmd = shell(rcmd)
        if rdata:
            grade = rdata.get("grade")
            red_raw = save_raw(case["id"], "commute-redundancy", rdata)

    plans = data.get("plans") or {}
    all_plan = plans.get("all") or {}
    return od(
        ("destination", dest),
        ("arrive_by", arrive),
        ("date_used", (data.get("query") or {}).get("date") or data.get("date")),
        ("all_min", all_plan.get("duration_min") if all_plan.get("duration_min") is not None
         else data.get("fastest_min")),
        ("rail_min", data.get("rail_only_min")),
        ("bus_min", data.get("bus_only_min")),
        ("tolerance_min", 8),
        ("redundancy_grade", grade),
        ("retrieved_at", data.get("retrieved_at") or (data.get("plans") or {}).get("retrieved_at")),
        ("command", shell(cmd)),
        ("raw", raw),
        ("redundancy_command", red_cmd),
        ("redundancy_raw", red_raw),
    )


def refresh_company(case, runner, previous):
    """company.py search: the register row for the one obvious named entity, if the case has one."""
    spec = case["truth_inputs"].get("company")
    if not spec:
        return None
    name = spec["name_query"]
    cmd = script_cmd("company.py", "search", "--name", name, "--limit", 20)
    data, err = runner.run(cmd, timeout=180)
    if err:
        return stale(previous, err, shell(cmd))
    if not data.get("ok"):
        return stale(previous, "fetcher reported ok=false: %s" % data.get("note"), shell(cmd))
    raw = save_raw(case["id"], "company-search", data)
    rows = data.get("results") or []
    active = [r for r in rows if not r.get("dissolved")]
    pick = active[0] if len(active) == 1 else (rows[0] if len(rows) == 1 else None)
    if pick is None:
        return stale(previous, "search returned %d rows, so there is no single obvious entity"
                     % len(rows), shell(cmd))
    return od(
        ("name_query", name),
        ("company_name", pick.get("name")),
        ("company_number", pick.get("company_number")),
        ("sic_codes", pick.get("sic_codes") or []),
        ("status", pick.get("status")),
        ("results_returned", len(rows)),
        ("retrieved_at", data.get("retrieved_at")),
        ("command", shell(cmd)),
        ("raw", raw),
        ("caveat", "This is a register row, not proof of ownership. The entity on the tenancy "
                   "agreement is what matters and is matched by company number, never by name."),
    )


def refresh_landregistry(case, runner, previous):
    """landregistry.py price-paid: the earliest new-build sale year in the postcode."""
    spec = case["truth_inputs"].get("landregistry")
    if not spec:
        return None
    pc = spec.get("postcode") or case["truth_inputs"]["postcode"]
    cmd = script_cmd("landregistry.py", "price-paid", "--postcode", pc)
    data, err = runner.run(cmd, timeout=300)
    if err:
        return stale(previous, err, shell(cmd))
    if not data.get("ok"):
        return stale(previous, "fetcher reported ok=false: %s" % data.get("note"), shell(cmd))
    raw = save_raw(case["id"], "landregistry-price-paid", data)
    return od(
        ("postcode", pc),
        ("earliest_new_build_year", data.get("earliest_new_build_year")),
        ("new_build_count", data.get("new_build_count")),
        ("transaction_count", data.get("count")),
        ("retrieved_at", data.get("retrieved_at")),
        ("command", shell(cmd)),
        ("raw", raw),
        ("caveat", "A new-build sale is a hard lower bound on the completion year. Blocks that "
                   "were never sold flat by flat leave no new-build row at all, so a missing "
                   "value proves nothing."),
    )


def refresh_geo(case, runner):
    cmd = script_cmd("geo.py", "lookup", case["truth_inputs"]["postcode"])
    data, err = runner.run(cmd, timeout=120)
    if err or not data or not data.get("ok"):
        return None, shell(cmd)
    save_raw(case["id"], "geo-lookup", data)
    return {"lat": data["lat"], "lng": data["lng"], "borough": data.get("admin_district")}, shell(cmd)


def plan_commands(case):
    """Every command this script would run for one case, in order, for --dry-run."""
    t = case["truth_inputs"]
    crime = t.get("crime") or {}
    commute = t.get("commute") or {}
    cmds = [
        script_cmd("geo.py", "lookup", t["postcode"]),
        script_cmd("epc.py", "cert", t["epc_certificate_id"], "--history"),
        script_cmd("epc.py", "search", "--postcode", t["postcode"]),
        script_cmd("crime.py", "box", "--lat", "<lat>", "--lng", "<lng>",
                   "--half-m", crime.get("box_half_m", 150), "--months", crime.get("months", 6)),
        script_cmd("commute.py", "journey", "--from", t["postcode"],
                   "--to", commute.get("destination"), "--arrive", commute.get("arrive", "09:00")),
        script_cmd("commute.py", "redundancy", "--lat", "<lat>", "--lng", "<lng>"),
    ]
    if t.get("company"):
        cmds.append(script_cmd("company.py", "search", "--name", t["company"]["name_query"],
                               "--limit", 20))
    if t.get("landregistry"):
        cmds.append(script_cmd("landregistry.py", "price-paid",
                               "--postcode", t["landregistry"].get("postcode", t["postcode"])))
    return cmds


def stale(previous, reason, command):
    """Keep what we had and say plainly why it was not refreshed."""
    out = collections.OrderedDict(previous or {})
    out["stale"] = True
    out["stale_reason"] = reason
    if command:
        out["stale_command"] = command
    if not previous:
        out["note"] = "no previous value and the refresh failed; this block is empty"
    return out


# --------------------------------------------------------------------- main --
def load_evals(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def write_evals(path, doc):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evals", default=EVALS_JSON, help="path to evals.json")
    ap.add_argument("--case", action="append", dest="cases", metavar="ID",
                    help="refresh this case only; repeatable")
    ap.add_argument("--only", help="comma list of blocks: %s" % ",".join(BLOCKS))
    ap.add_argument("--dry-run", action="store_true", help="print the commands, fetch nothing")
    ap.add_argument("--verbose", action="store_true")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    globals()["args_ns"] = args  # lets case_dir() route private cases to bench/private/truth
    only = [b.strip() for b in args.only.split(",")] if args.only else BLOCKS
    for b in only:
        if b not in BLOCKS:
            print("usage error: unknown block %r; known blocks are %s" % (b, ", ".join(BLOCKS)),
                  file=sys.stderr)
            return 2

    doc = load_evals(args.evals)
    runner = Runner(dry_run=args.dry_run, verbose=args.verbose)
    stale_blocks = []
    skipped = []
    touched = 0

    for case in doc["evals"]:
        if args.cases and case["id"] not in args.cases:
            continue
        if case.get("kind") == "conversation":
            # These two cases are graded against SKILL.md and references/onboarding.md,
            # not against a register. No fetcher can refresh them; a maintainer updates
            # them by hand when the pitch, the intake questions or the law changes.
            print("== %s: skipped, this case's truth is the skill's own text "
                  "(%s). Update it by hand."
                  % (case["id"], (case.get("truth_inputs") or {}).get("source", "SKILL.md")),
                  file=sys.stderr)
            skipped.append(case["id"])
            continue
        touched += 1
        print("== %s (%s)" % (case["id"], case.get("address", "")), file=sys.stderr)
        if args.dry_run:
            for cmd in plan_commands(case):
                print("  would run: " + shell(cmd), file=sys.stderr)
            continue
        facts = case.get("expected_facts") or collections.OrderedDict()
        if not isinstance(facts, collections.OrderedDict):
            facts = collections.OrderedDict(facts)
        geo, geo_cmd = refresh_geo(case, runner)
        if geo:
            facts["geo"] = od(("postcode", case["truth_inputs"]["postcode"]),
                              ("lat", geo["lat"]), ("lng", geo["lng"]),
                              ("borough", geo["borough"]), ("command", geo_cmd))

        if "epc" in only:
            facts["epc"] = refresh_epc(case, runner, facts.get("epc"))
        if "crime" in only:
            facts["crime"] = refresh_crime(case, runner, facts.get("crime"), geo)
        if "commute" in only:
            facts["commute"] = refresh_commute(case, runner, facts.get("commute"), geo)
        if "company" in only:
            block = refresh_company(case, runner, facts.get("company"))
            if block is not None:
                facts["company"] = block
        if "landregistry" in only:
            block = refresh_landregistry(case, runner, facts.get("landregistry"))
            if block is not None:
                facts["landregistry"] = block

        for name, block in facts.items():
            if isinstance(block, dict) and block.get("stale"):
                stale_blocks.append("%s/%s: %s" % (case["id"], name, block.get("stale_reason")))
        case["expected_facts"] = facts

    if args.dry_run:
        print("dry run: %d cases, nothing fetched, evals.json not written" % touched,
              file=sys.stderr)
        return 0

    write_evals(args.evals, doc)
    summary = collections.OrderedDict([
        ("cases_refreshed", touched),
        ("cases_skipped_by_hand", skipped),
        ("blocks", only),
        ("stale", stale_blocks),
        ("evals", os.path.relpath(args.evals, ROOT)),
        ("truth_dir", os.path.relpath(TRUTH_DIR, ROOT)),
    ])
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 1 if stale_blocks else 0


if __name__ == "__main__":
    sys.exit(main())
