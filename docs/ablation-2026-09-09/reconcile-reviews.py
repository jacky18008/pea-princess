#!/usr/bin/env python3
"""Unblind completed prospective AI source reviews without replacing primary labels."""
from collections import Counter
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
        raise SystemExit("Wait for the full live run before final unblinding.")
    sample = read(DOCS / "source-review-plan.json")
    plan = read(RUN / "plan.json")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(RUN / "plan.json") != sample["plan_sha256"]:
        raise SystemExit("Live plan differs from the prospectively selected source-review plan.")
    primary = {a["job_id"]: a for j in summary["judgments"] for a in j["assessments"]}
    review_paths = [DOCS / ("independent-" + kind + "-sample-review.json") for kind in ("rental", "retrieval")]
    assessments = [a for path in review_paths for a in read(path)["assessments"]]
    expected = {(group, candidate) for group in sample["review_groups"] for candidate in plan["judge_masks"][group]}
    actual = [(a["group_id"], a["candidate_id"]) for a in assessments]
    if len(set(actual)) != len(actual) or set(actual) != expected or len(actual) != 36:
        raise SystemExit("Review coverage must be exactly the 36 prospectively selected anonymous answers.")
    rows, disagreements = [], []
    for a in assessments:
        group, candidate = a["group_id"], a["candidate_id"]
        job = plan["judge_masks"][group][candidate]
        baseline = primary[job]
        packet = read(RUN / "review-packets" / (group + ".json"))
        required = {r["id"]: r for r in packet["case"]["gold"]["required_findings"]}
        def checked_criteria(criteria):
            if len(criteria) != len(required) or len({c["id"] for c in criteria}) != len(criteria):
                raise SystemExit("Duplicate or missing criteria for " + job)
            if any(type(c["met"]) is not bool for c in criteria):
                raise SystemExit("Non-boolean criterion verdict for " + job)
            return {c["id"]: c for c in criteria}
        review = checked_criteria(a["criteria"])
        grades = checked_criteria(baseline["assessment"]["criteria"])
        if set(review) != set(required) or set(grades) != set(required):
            raise SystemExit("Unexpected criterion coverage for " + job)
        differing = []
        for criterion, secondary in review.items():
            first = grades[criterion]
            if first["met"] != secondary["met"]:
                item = {"answer_id": job, "criterion_id": criterion,
                        "rubric": required[criterion], "primary": first, "independent_source_review": secondary}
                differing.append(criterion)
                disagreements.append(item)
        rows.append({"group_id": group, "candidate_id": candidate, "answer_id": job,
                     "primary_required_met": baseline["required_met"],
                     "review_required_met": sum(c["met"] for c in review.values()),
                     "required_total": len(required), "primary_critical_missed": baseline["critical_missed"],
                     "review_critical_missed": [key for key, r in required.items() if r["severity"] == "critical" and not review[key]["met"]],
                     "differing_criteria": differing,
                     "review_unsupported_claims": a["unsupported_claims"], "review_contradictions": a["contradictions"]})
    totals = {"answers": len(rows), "criteria": sum(r["required_total"] for r in rows),
              "primary_required_met": sum(r["primary_required_met"] for r in rows),
              "review_required_met": sum(r["review_required_met"] for r in rows),
              "criterion_disagreements": len(disagreements),
              "answers_with_any_disagreement": sum(bool(r["differing_criteria"]) for r in rows),
              "disagreements_by_criterion": dict(Counter(r["criterion_id"] for r in disagreements))}
    result = {"scope": "Prospective 36-answer blinded AI source review, then root unblinding. Not human ground truth or replacement of primary results.",
              "interpretation": "Criterion differences include rubric interpretation. More secondary points do not establish that the primary grader was wrong or that an answer model improved.",
              "provenance_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (DOCS / "source-review-plan.json", RUN / "plan.json", RUN / "summary.json")},
              "review_file_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in review_paths},
              "totals": totals, "per_answer": rows, "criterion_disagreements": disagreements}
    (DOCS / "source-review-reconciliation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Prospective source-review reconciliation", "", result["scope"], "", result["interpretation"], "",
             f"{totals['answers']} answers; {totals['criteria']} criteria; primary {totals['primary_required_met']}, secondary {totals['review_required_met']}; {len(disagreements)} criterion disagreements.", "",
             "| Answer | Primary | Source review | Differing criteria |", "|---|---:|---:|---|"]
    for row in rows:
        lines.append("| {answer_id} | {primary_required_met}/{required_total} | {review_required_met}/{required_total} | {different} |".format(**row, different=", ".join(row["differing_criteria"]) or "—"))
    for item in disagreements:
        lines += ["", "## " + item["answer_id"] + " / " + item["criterion_id"], "",
                  "Rubric: " + item["rubric"]["description"], "",
                  "Primary: " + item["primary"]["reason"], "",
                  "Source reviewer: " + item["independent_source_review"]["reason"]]
    (DOCS / "source-review-reconciliation.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
