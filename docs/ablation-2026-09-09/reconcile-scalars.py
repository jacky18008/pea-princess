#!/usr/bin/env python3
"""Keep exact scalar scores and source-reviewed semantic sensitivity separate."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parents[1]
RUN = ROOT / "bench/results/ablation-2026-09-09/live-v1"


def read(path):
    return json.loads(path.read_text())


def main():
    summary = read(RUN / "summary.json")
    if not summary["complete"]:
        raise SystemExit("Wait for the complete study.")
    review_path = DOCS / "scalar-source-review.json"
    reviews = read(review_path)["reviews"]
    by_key = {(r["answer_id"], r["key"]): r for r in reviews}
    if len(by_key) != len(reviews):
        raise SystemExit("Duplicate semantic scalar review.")
    expected = {(a["id"], c["key"]): c for a in summary["answers"]
                for c in a["fact_check"]["checks"] if not c["pass"]}
    if set(by_key) != set(expected):
        raise SystemExit("Scalar review coverage differs from all deterministic mismatches: " + str(set(by_key) ^ set(expected)))
    for key, review in by_key.items():
        original = expected[key]
        if review["expected"] != original["expected"] or review["got"] != original["got"]:
            raise SystemExit("Original scalar values changed for " + str(key))
        if type(review["semantic_equivalent"]) is not bool:
            raise SystemExit("Non-boolean semantic equivalence for " + str(key))
        raw = RUN / "answers" / (review["answer_id"] + ".json")
        if hashlib.sha256(raw.read_bytes()).hexdigest() != review["answer_sha256"]:
            raise SystemExit("Source answer hash changed for " + str(key))
    arms = defaultdict(lambda: {"answers": 0, "scalar_total": 0, "exact_passed": 0, "supported_equivalent_mismatches": 0, "remaining_non_equivalent": 0})
    for answer in summary["answers"]:
        arm = arms[answer["experiment"] + "/" + answer["arm"]]
        arm["answers"] += 1
        arm["scalar_total"] += answer["fact_check"]["total"]
        arm["exact_passed"] += answer["fact_check"]["passed"]
        for check in answer["fact_check"]["checks"]:
            if not check["pass"]:
                equivalent = by_key[answer["id"], check["key"]]["semantic_equivalent"]
                arm["supported_equivalent_mismatches" if equivalent else "remaining_non_equivalent"] += 1
    for arm in arms.values():
        arm["posthoc_semantic_passed"] = arm["exact_passed"] + arm["supported_equivalent_mismatches"]
        assert arm["posthoc_semantic_passed"] + arm["remaining_non_equivalent"] == arm["scalar_total"]
    result = {"scope": "Post-hoc source-reviewed semantic sensitivity for all exact scalar mismatches. Primary scores and preregistered adoption gates remain unchanged.",
              "limits": "AI source review, not human truth. Context-resolved dates may preserve the fact while failing requested formatting. Correct fields do not prove correct prose, provenance or decisions.",
              "complete_mismatch_coverage": True, "mismatch_count": len(reviews),
              "classification_counts": dict(Counter(r["classification"] for r in reviews)),
              "semantic_equivalent_mismatches": sum(r["semantic_equivalent"] for r in reviews),
              "source_review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
              "arms": dict(sorted(arms.items())),
              "non_equivalent_values": [{k: r[k] for k in ("answer_id", "key", "expected", "got", "classification", "reason")} for r in reviews if not r["semantic_equivalent"]]}
    (DOCS / "scalar-reconciliation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Scalar semantic sensitivity", "", result["scope"], "", result["limits"], "",
             "| Arm | Exact | Additional source-supported equivalents | Post-hoc semantic | Remaining non-equivalent |", "|---|---:|---:|---:|---:|"]
    for name, arm in sorted(arms.items()):
        lines.append("| %s | %s/%s | %s | %s/%s | %s |" % (name, arm["exact_passed"], arm["scalar_total"], arm["supported_equivalent_mismatches"], arm["posthoc_semantic_passed"], arm["scalar_total"], arm["remaining_non_equivalent"]))
    (DOCS / "scalar-reconciliation.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"mismatches": len(reviews), "equivalent": result["semantic_equivalent_mismatches"], "arms": len(arms)}, indent=2))


if __name__ == "__main__":
    main()
