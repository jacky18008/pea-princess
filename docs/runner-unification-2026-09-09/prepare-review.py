#!/usr/bin/env python3
"""Prepare treatment/cost/primary-score-masked source packets for all new answers."""
import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bench"))
import context_quality as q


def read(path):
    return json.loads(path.read_text())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--experiment", choices=("analysis", "rental"))
    args = ap.parse_args()
    run = args.run.resolve()
    plan = read(run / "plan.json")
    out = run / "independent-review"
    out.mkdir(mode=0o700, exist_ok=True)
    mapping = read(out / "unblind-mapping.json") if (out / "unblind-mapping.json").exists() else {}
    for experiment in ([args.experiment] if args.experiment else ("analysis", "rental")):
        cases = read(run / (experiment + "-cases.json"))["cases"]
        groups = []
        for case in cases:
            jobs = [j for j in plan["jobs"] if j["case_id"] == case["id"]]
            random.Random("durable-quality-review-20260909-" + case["id"]).shuffle(jobs)
            candidates = {}
            for i, job in enumerate(jobs, 1):
                label = case["id"] + "-candidate-" + str(i)
                result = read(run / "answers" / (job["id"] + ".json"))
                if experiment == "analysis":
                    evidence = {"summary": case["summary"], "documents": [d for d in case["documents"]
                                if d["id"] in result["supplied_document_ids"]]}
                else:
                    evidence = {"source_material": case["history"] if job["arm"] == "full" else case["handoff"],
                                "question": case["question"]}
                candidates[label] = {"response": result["final_answer"], "available_evidence": evidence}
                mapping[label] = job["id"]
            groups.append({"case": case, "candidates": candidates})
        packet = {"experiment": experiment, "groups": groups,
                  "common_target_guidance": (q.BOUNDARY + q.RENTAL_RULES + (run / "target-instructions.md").read_text()) if experiment == "rental" else q.BOUNDARY + q.ANALYSIS_RULES,
                  "review_scope": "All 24 answers selected before generation; costs, treatment names and primary scores hidden. Evidence may reveal treatment. AI review, not human ground truth."}
        (out / (experiment + "-packet.json")).write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    (out / "unblind-mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print(json.dumps({"review_packets": str(out), "selected_answers": len(mapping)}))
