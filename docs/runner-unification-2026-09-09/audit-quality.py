#!/usr/bin/env python3
"""Offline raw-event audit and descriptive comparison; never calls a model."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root, run, old):
    plan = read(run / "plan.json")
    summary = read(run / "summary.json")
    prior = read(old / "summary.json")
    problems, calls, totals, purposes, models = [], [], Counter(), Counter(), Counter()
    for rel, sha in plan["source_sha256"].items():
        if digest(root / rel) != sha:
            problems.append("source changed: " + rel)
    for rel, sha in plan["prepared_sha256"].items():
        if digest(run / rel) != sha:
            problems.append("prepared input changed: " + rel)
    for directory in sorted((run / "calls").iterdir()):
        if not directory.is_dir():
            continue
        if not (directory / "result.json").exists():
            problems.append("unresolved directory: " + directory.name)
            continue
        result = read(directory / "result.json")
        events = []
        for line in (directory / "events.jsonl").read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                problems.append("malformed event: " + directory.name)
        terminal = [e for e in events if e.get("type") == "turn.completed"]
        errors = [e for e in events if e.get("type") in ("turn.failed", "error")]
        tools = [(e.get("item") or {}).get("type") for e in events
                 if (e.get("item") or {}).get("type") not in (None, "agent_message", "reasoning")]
        usage = terminal[0].get("usage", {}) if len(terminal) == 1 else {}
        valid = (len(terminal) == 1 and all(type(usage.get(k)) is int and usage[k] >= 0
                 for k in ("input_tokens", "output_tokens", "cached_input_tokens")))
        if valid:
            valid = usage["cached_input_tokens"] <= usage["input_tokens"]
        if not valid or errors or tools or result["status"] != "complete":
            problems.append("failed call/evidence: " + directory.name)
        if valid:
            for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                totals[key] += usage[key]
                if (result.get("usage") or {}).get(key) != usage[key]:
                    problems.append("usage mismatch: " + directory.name + "/" + key)
            count = usage["input_tokens"] + usage["output_tokens"]
            totals["total_tokens"] += count
            purposes[result["purpose"]] += count
        for name, key in (("prompt.txt", "prompt_sha256"), ("schema.json", "schema_sha256"),
                          ("events.jsonl", "events_sha256"), ("answer.txt", "answer_sha256")):
            if not (directory / name).exists() or digest(directory / name) != result.get(key):
                problems.append("artifact mismatch: " + directory.name + "/" + name)
        models[result["requested_model"]] += 1
        calls.append({"id": directory.name, "purpose": result["purpose"], "usage": usage,
                      "status": result["status"], "tool_events": tools})
    if totals["total_tokens"] != summary["known_cli_processed_tokens"]:
        problems.append("summary total mismatch")
    progress_files = list(run.glob("*/progress.json"))
    controllers = {str(p.relative_to(run)): read(p) for p in progress_files}
    if not controllers:
        problems.append("no durable controller report")
    for name, progress in controllers.items():
        if not progress.get("plan_complete") or progress.get("paused"):
            problems.append("controller incomplete: " + name)
        if progress.get("completed_calls") != len(calls):
            problems.append("controller call count: " + name)
        if {c["call_id"] for c in progress["calls"]} != {c["id"] for c in calls}:
            problems.append("controller call identities: " + name)
        if set(plan["planned_call_ids"]) != ({c["id"] for c in calls} | set(progress["skipped_call_ids"])):
            problems.append("controller plan coverage: " + name)
        for field in ("input_tokens", "output_tokens", "cached_input_tokens"):
            if progress["usage"].get("known_" + field) != totals[field]:
                problems.append("controller usage mismatch: " + name + "/" + field)
        if progress["usage"].get("total_tokens") != totals["total_tokens"]:
            problems.append("controller total mismatch: " + name)
        checkpoint = read((run / name).with_name("checkpoint.json"))
        encoded = json.dumps(checkpoint["state"], ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()
        if hashlib.sha256(encoded).hexdigest() != checkpoint["state_sha256"]:
            problems.append("checkpoint checksum mismatch: " + name)
    matching_inputs = {name: digest(run / name) == digest(old / name)
                       for name in ("analysis-cases.json", "rental-cases.json", "target-instructions.md")}
    comparison = []
    for experiment, arms in summary["arms"].items():
        for arm, row in arms.items():
            previous = prior["arms"][experiment][arm]
            metrics = ("tasks", "calls", "required_met", "required_total", "critical_misses",
                       "unsupported_claims", "contradictions", "invalid_citations", "format_failures")
            comparison.append({"experiment": experiment, "arm": arm,
                               "new": {k: row[k] for k in metrics},
                               "historical": {k: previous[k] for k in metrics},
                               "new_answer_tokens": row["usage"]["total_tokens"],
                               "historical_answer_tokens": previous["usage"]["total_tokens"]})
    return {"status": "PASS" if not problems and summary["complete"] else "INCOMPLETE_OR_FAILED",
            "problems": problems, "source_commit": plan["source_commit"],
            "plan_sha256": digest(run / "plan.json"), "calls": len(calls),
            "requested_models": dict(models), "usage": dict(totals),
            "tokens_by_purpose": dict(purposes), "controllers": controllers,
            "matching_historical_inputs": matching_inputs, "comparison": comparison,
            "call_evidence": calls,
            "limitations": ["Historical comparison is descriptive, not a randomized runtime A/B.",
                            "Primary judgments retain the historical grader's known limitations.",
                            "Processed tokens are not invoice charges or account quota."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = audit(root, args.run.resolve(), args.old.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "problems", "calls", "usage")}))
