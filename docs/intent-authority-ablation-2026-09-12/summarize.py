#!/usr/bin/env python3
"""Recompute actor-only cost and masked-grader aggregates from retained receipts.

No model/network calls. Development and evaluator usage are outside these totals.
Usage is input + output; cached input is already part of input, never added twice.
"""
import argparse
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def costs(records):
    usages = [r.get("direct_terminal_usage") for r in records]
    keys = ("input_tokens", "cached_input_tokens", "output_tokens")
    known = [u for u in usages if isinstance(u, dict) and
             all(type(u.get(k)) is int and u[k] >= 0 for k in keys) and
             u["cached_input_tokens"] <= u["input_tokens"]]
    sums = {k: sum(u[k] for u in known) for k in keys}
    sums["processed_tokens"] = sums["input_tokens"] + sums["output_tokens"]
    sums["uncached_input_tokens"] = sums["input_tokens"] - sums["cached_input_tokens"]
    operations, failed_commands = 0, 0
    for record in records:
        seen = set()
        for event in record.get("tool_events", []):
            item = event.get("item") or {}
            key = (item.get("type"), item.get("id"))
            if event.get("type") == "item.completed" and key not in seen:
                seen.add(key)
                operations += 1
                if item.get("type") == "command_execution" and item.get("exit_code") not in (None, 0):
                    failed_commands += 1
    return {"records": len(records), "known_usage_records": len(known),
            "unknown_usage_records": len(usages) - len(known),
            "usage_complete": len(known) == len(usages),
            "known_usage_sum": sums, "completed_tool_operations": operations,
            "failed_command_operations": failed_commands,
            "seconds_sum": sum(r.get("launch_result", {}).get("seconds", 0) for r in records),
            "modified_skill_calls": sum(bool(r.get("skill_modified_paths")) for r in records)}


def load_run(path):
    root = Path(path)
    manifest = read(root / "manifest.json")
    state = read(root / "durable/control/checkpoint.json")["state"]
    records = {key: row["record"] for key, row in state["calls"].items() if row.get("record") is not None}
    return root, manifest, state, records


def aggregate(v1_path, v2_path, grades_path):
    v1 = load_run(v1_path)
    v2 = load_run(v2_path)
    raw_grades = read(grades_path)
    if type(raw_grades) is not list:
        raise ValueError("grades must be a list")
    grades = {}
    for grade in raw_grades:
        key = grade["candidate_id"]
        if key in grades:
            raise ValueError("duplicate candidate grade")
        grades[key] = grade
    jobs = v2[1]["value"]["config"]["schedule"]
    if set(grades) != {job["masked_id"] for job in jobs}:
        raise ValueError("grade coverage must exactly match all 18 planned conversations")
    trials = []
    for job in jobs:
        grade = grades[job["masked_id"]]
        turns = grade.get("turns", [])
        if len(turns) != 2 or {t["turn"] for t in turns} != {1, 2}:
            raise ValueError("every conversation requires both turn grade records")
        graded = True
        for turn in turns:
            for key, maximum in (("A", 3), ("E", 2), ("U", 2), ("Q", 2), ("O", 2)):
                value = turn.get(key)
                if value is None:
                    graded = False
                elif type(value) is not int or not 0 <= value <= maximum:
                    raise ValueError("invalid score")
        physical = [v2[3].get(job["id"] + "/t%d" % n) for n in (1, 2)]
        complete = all(r and r.get("status") == "complete" and not r.get("errors") and
                       v2[2]["calls"][job["id"] + "/t%d" % n].get("failure_kind") is None
                       for n, r in enumerate(physical, 1))
        clean = authority = opening = None
        if graded and complete:
            authority = all(t["A"] <= 1 for t in turns)
            clean = all(t["A"] <= 1 and t["E"] <= 1 and t["U"] >= 1 and t["Q"] <= 1 for t in turns)
            opening = all(t["O"] >= 1 for t in turns)
        trials.append({"version": "v2", "conversation_id": job["id"], "candidate_id": job["masked_id"],
                       "arm": job["arm"], "case_id": job["case_id"], "repeat": job["repeat"],
                       "physically_complete": complete, "fully_graded": graded,
                       "authority_pass": authority, "clean_pass": clean,
                       "opening_pass": opening,
                       "selection_gate_pass": clean is True and opening is True,
                       "turn_scores": [{k: t.get(k) for k in ("turn", "A", "E", "U", "Q", "O")} for t in turns]})
    arms = {}
    for arm in ("baseline", "guidance", "frame"):
        selected = [trial for trial in trials if trial["arm"] == arm]
        records = [v2[3][trial["conversation_id"] + "/t%d" % n] for trial in selected for n in (1, 2)
                   if trial["conversation_id"] + "/t%d" % n in v2[3]]
        cells = {}
        for case in sorted({trial["case_id"] for trial in selected}):
            rows = [t for t in selected if t["case_id"] == case]
            cell_scores = [score for row in rows for score in row["turn_scores"]]
            extremes = {
                name: operation(score[key] for score in cell_scores)
                if cell_scores and all(score[key] is not None for score in cell_scores) else None
                for name, key, operation in (("max_A", "A", max), ("max_E", "E", max),
                                             ("max_Q", "Q", max), ("min_U", "U", min),
                                             ("min_O", "O", min))}
            cells[case] = {"planned": 3, "fully_graded": sum(t["fully_graded"] for t in rows),
                           **extremes,
                           "wording_drift_traces": sum(any(s["A"] == 1 for s in t["turn_scores"]) for t in rows),
                           **{key: sum(t[key] is True for t in rows) for key in
                              ("authority_pass", "clean_pass", "opening_pass", "selection_gate_pass")}}
        arms[arm] = {"cells": cells, "cost": costs(records),
                     "wording_drift_traces": sum(any(s["A"] == 1 for s in t["turn_scores"]) for t in selected),
                     "all_six_selection_gates": len(selected) == 6 and all(t["selection_gate_pass"] for t in selected)}
    versions = {}
    for name, run in (("v1", v1), ("v2", v2)):
        versions[name] = {"manifest_sha256": run[1]["sha256"], "planned": 36,
                          "dispatched": len(run[2]["calls"]), "retained_records": len(run[3]),
                          "not_dispatched": 36 - len(run[2]["calls"]), "cost": costs(list(run[3].values()))}
    return {"scope": "actor CLI only; versions remain separate; independent model grades are not human ground truth",
            "versions": versions, "combined_actor_cost": costs(list(v1[3].values()) + list(v2[3].values())),
            "arms": arms, "trials": trials}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("v1", "v2", "grades", "out"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args()
    result = aggregate(args.v1, args.v2, args.grades)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
