#!/usr/bin/env python3
"""Copy and regrade the interrupted September persona experiment without model calls.

Standard library only. Originals are hashed before and after; the output directory
must not already exist. The copies retain their original transcripts and model
judgments. This recalculates deterministic rules, not the model criterion scores.

Usage: python3 bench/handoff_personas.py --output /tmp/pea-persona-regrade
"""
import argparse
import collections
import contextlib
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess

import personas


BATCHES = (
    "personas-2026-09-07",
    "personas-2026-09-07-fixed",
    "personas-2026-09-07-fix2",
)
ROOT = Path(__file__).resolve().parent.parent


def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def mean(values):
    return statistics.mean(values) if values else None


def median(values):
    return statistics.median(values) if values else None


def describe(folder):
    records = [json.loads(p.read_text()) for p in sorted((folder / "cards").glob("*.json"))]
    graded = [r for r in records if r.get("grade") is not None
              and not personas.provider_error_row(r)]
    summaries, first_lengths, first_asks = [], [], []
    for r in records:
        _, dialogue = personas.parse_transcript(str(folder / "transcripts" / (r["session"] + ".md")))
        if r in graded and dialogue:
            first_lengths.append(len(dialogue[0]["assistant"]))
            first_asks.append((r.get("asks", {}).get("per_message") or [0])[0])
        summaries.append({k: r.get(k) for k in (
            "session", "variant", "seed", "outcome", "turns", "grade", "capped_by",
            "criteria_met", "agent", "model", "persona_model", "judge_model", "run_at")})
    return {
        "total_current_cards": len(records), "graded": len(graded),
        "provider_errors": sum(personas.provider_error_row(r) for r in records),
        "outcomes": dict(collections.Counter(r["outcome"] for r in records)),
        "grade_median": median([r["grade"] for r in graded]),
        "grade_mean": mean([r["grade"] for r in graded]),
        "capped_sessions": sum(bool(r.get("capped_by")) for r in graded),
        "uncapped_grade_mean": mean([r["grade"] for r in graded if not r.get("capped_by")]),
        "safety_misses": dict(collections.Counter(s["line"] for r in graded
                              for s in r.get("safety", []) if s.get("status") != "pass")),
        "criteria_mean": mean([c["score"] for r in graded for c in r.get("criteria", [])
                               if isinstance(c.get("score"), (int, float))]),
        "criteria_count_distribution": dict(collections.Counter(len(r.get("criteria", [])) for r in graded)),
        "criteria_met_count_mean": mean([r["criteria_met"] for r in graded]),
        "all_criteria_met_sessions": sum(all(c.get("score", -1) >= 2 for c in r.get("criteria", []))
                                         for r in graded),
        "all_criteria_top_score_sessions": sum(all(c.get("score") == 3 for c in r.get("criteria", []))
                                               for r in graded),
        "satisfaction_mean": mean([r["satisfaction"]["rating"] for r in graded
                                   if isinstance(r.get("satisfaction", {}).get("rating"), (int, float))]),
        "asks_median": median([r["asks"]["total"] for r in graded]),
        "first_reply_characters_median": median(first_lengths),
        "first_reply_asks_mean": mean(first_asks),
        "sessions": summaries,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, default=ROOT / "bench" / "results")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    source, output = args.source_root.resolve(), args.output.resolve()
    if output.exists():
        ap.error("output already exists; choose a fresh path to preserve prior analyses")
    if any(not (source / batch).is_dir() for batch in BATCHES):
        ap.error("source root must contain all three September persona batches")
    if any((source / batch) == output or (source / batch) in output.parents for batch in BATCHES):
        ap.error("output must be outside the original batch folders")
    before = {batch: hashes(source / batch) for batch in BATCHES}
    output.mkdir(parents=True)
    # Fail loudly if a future change accidentally crosses the rules-only boundary.
    def refuse_model(*_args, **_kwargs):
        raise RuntimeError("handoff regrade is offline: model launches are forbidden")
    personas.launch = refuse_model
    report = {}
    for batch in BATCHES:
        copied = output / batch
        shutil.copytree(source / batch, copied)
        with (output / (batch + ".log")).open("w") as log, contextlib.redirect_stdout(log):
            options = personas.build_parser().parse_args(["--regrade", str(copied), "--rules-only"])
            if personas.regrade(str(copied), options):
                raise RuntimeError("rules-only regrade failed: " + batch)
        report[batch] = describe(copied)
    old = {r["session"]: r for r in report[BATCHES[0]]["sessions"] if r["grade"] is not None}
    new = {r["session"]: r for r in report[BATCHES[1]]["sessions"] if r["grade"] is not None}
    paired = [{"session": s, "before": old[s]["grade"], "after": new[s]["grade"],
               "delta": round(new[s]["grade"] - old[s]["grade"], 4)} for s in sorted(old.keys() & new.keys())]
    report["paired"] = {"n": len(paired), "better": sum(p["delta"] > 0 for p in paired),
                        "worse": sum(p["delta"] < 0 for p in paired),
                        "same": sum(p["delta"] == 0 for p in paired),
                        "mean_delta": mean([p["delta"] for p in paired]), "sessions": paired}
    after = {batch: hashes(source / batch) for batch in BATCHES}
    if before != after:
        raise RuntimeError("source artifacts changed during analysis; investigate before using output")
    grading_files = [Path("bench/personas.py"), Path("bench/journeys.py"), Path("bench/launch.py"),
                     Path("bench/handoff_personas.py"), Path("evals/personas.json")]
    grading_files += [p.relative_to(ROOT) for p in (ROOT / "evals/personas/fixtures").rglob("*") if p.is_file()]
    grading_files += [p.relative_to(ROOT) for p in (ROOT / "skills/vet-flat").rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    provenance = {
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_root": str(source), "output": str(output),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip(),
        "rules_only": True, "model_launches": 0, "original_sources_unchanged": True,
        "source_files_sha256": before,
        "grading_inputs_sha256": {str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                  for p in sorted(set(grading_files))},
        "caveats": ["Git HEAD identifies checkout, not historical per-session source or model revisions.",
                    "Model criteria judgments are retained, not reassessed.",
                    "Transcript header grades are historical; consult copied JSON cards for the regrade.",
                    "Provider failures remain ungraded and excluded from summary statistics."],
    }
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output), "sources_unchanged": True,
                      "paired": {k: v for k, v in report["paired"].items() if k != "sessions"},
                      "pending_provider_errors": report[BATCHES[2]]["provider_errors"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
