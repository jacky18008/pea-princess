#!/usr/bin/env python3
"""Post-hoc, offline report assembly. Never invokes models or rewrites primary results."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = Path(__file__).resolve().parent
LIVE = ROOT / "bench/results/context-quality-2026-09-08/live-v1"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (DOCS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    summary = read(LIVE / "summary.json")
    assert summary["complete"] and summary["calls"] == 38
    plan = read(LIVE / "plan.json")
    # Byte-exact, explicitly named copy of the frozen primary result, not an adjudication.
    (DOCS / "live-results-2026-09-08.json").write_bytes((LIVE / "summary.json").read_bytes())
    rubrics = {}
    for category in ("analysis", "rental"):
        for case in read(ROOT / f"evals/context-quality/{category}-cases.json")["cases"]:
            for criterion in case["gold"]["required_findings"]:
                rubrics[criterion["id"]] = criterion
    reviews = {}
    review_paths = []
    for category, key in (("analysis", "reviews"), ("rental", "cases")):
        path = DOCS / f"independent-{category}-review-2026-09-08.json"
        review_paths.append(path)
        for row in read(path)[key]:
            job = plan["judge_masks"][row["case_id"]][row["candidate_id"]]
            reviews[job] = row

    conditional = {"R1-F6", "R2-F6"}
    aggregates = defaultdict(lambda: defaultdict(int))
    rows, disagreements = [], []
    for judgment in summary["judgments"]:
        for primary in judgment["assessments"]:
            job = primary["job_id"]
            category, arm = judgment["experiment"], job.split("-", 1)[1]
            secondary = reviews[job]
            labels = {"primary": primary["assessment"], "independent": secondary}
            metrics = {}
            for label, assessment in labels.items():
                criteria = assessment["criteria"]
                applicable = [c for c in criteria if c.get("applicable", True)]
                always = [c for c in criteria if c["id"] not in conditional]
                critical = [c for c in criteria if rubrics[c["id"]]["severity"] == "critical"]
                metrics[label] = {
                    "always_required_met": sum(c["met"] for c in always),
                    "always_required_total": len(always),
                    "applicable_met": sum(c["met"] for c in applicable),
                    "applicable_total": len(applicable),
                    "critical_misses": sum(not c["met"] for c in critical),
                    "unsupported_annotations": len(assessment["unsupported_claims"]),
                    "contradiction_annotations": len(assessment["contradictions"]),
                }
                for metric, value in metrics[label].items():
                    aggregates[f"{category}/{arm}/{label}"][metric] += value
            secondary_by_id = {c["id"]: c for c in secondary["criteria"]}
            for criterion in primary["assessment"]["criteria"]:
                other = secondary_by_id[criterion["id"]]
                if (criterion["met"], criterion.get("applicable", True)) != (
                    other["met"], other.get("applicable", True)
                ):
                    disagreements.append({
                        "job_id": job, "criterion_id": criterion["id"],
                        "primary": criterion, "independent": other,
                        "resolution": "Retain both judgments; no primary relabeling or model rerun. See source review and report for interpretation.",
                    })
            rows.append({
                "job_id": job, "candidate_id": secondary["candidate_id"],
                "metrics": metrics,
                "primary_unsupported_claims": primary["assessment"]["unsupported_claims"],
                "primary_contradictions": primary["assessment"]["contradictions"],
                "independent_unsupported_claims": secondary["unsupported_claims"],
                "independent_contradictions": secondary["contradictions"],
            })

    annotations = [
        {
            "jobs": ["A1-summary", "A1-adaptive", "A2-summary", "A3-summary", "A4-summary"],
            "finding": "Primary judge confused its own full-source visibility with each answerer's visibility.",
            "root_assessment": "The 11 contradiction annotations and 2 unsupported annotations on these jobs rely on sources being supplied when they were not. Actual prompts and supplied_document_ids show summary-only access, or A1 adaptive D02/D03 without D01. Missing core findings still count as omissions, but these annotations do not establish a material false claim.",
        },
        {
            "jobs": ["A2-full"],
            "finding": "Three supported translations were placed in exact quotation fields.",
            "root_assessment": "Retain all three deterministic quote failures. Primary unsupported-claim annotations explicitly acknowledge the supported substance. Classify as citation fidelity defects rather than three fabricated material facts.",
        },
        {
            "jobs": ["A2-adaptive"],
            "finding": "Primary judge flagged uncertainty about consent in other unsupplied material.",
            "root_assessment": "Main answer and quotes explicitly establish no approval in the complete cedar-17 trace. The limitations phrase about other material is unnecessarily broad and could imply missing in-run consent. Treat as a scope/wording ambiguity; independent review found no material contradiction. Do not erase the primary flag or count it as a proven incorrect core conclusion.",
        },
        {
            "jobs": ["R2-compact"],
            "finding": "Primary judge called Never sign or pay at the viewing a contradiction with conditional repair evidence.",
            "root_assessment": "The source and fixed entry guidance support withholding on-the-spot commitment in this case. Repair evidence could change the property assessment while off-site review before commitment remains appropriate. The absolute wording is broader than necessary, but is not a contradiction in the user's fictional record. Bridge availability and its unbooked status remain incompletely communicated.",
        },
        {
            "jobs": ["R3-full", "R3-compact"],
            "finding": "Both answers explicitly call 42 square metres the user's minimum; U1 says 40 and U3 gives B's area as 42.",
            "root_assessment": "A real shared source error missed by the primary judge and caught by the blinded review. It does not change which listed flat meets the true threshold here, but it defeats a claim of error-free outputs.",
        },
        {
            "jobs": ["R5-compact"],
            "finding": "Answer assumes a balcony listening location without evidence that the property has a balcony.",
            "root_assessment": "Both reviews flag this minor unsupported assumption. A balcony preference does not establish a balcony exists.",
        },
        {
            "jobs": ["R6-compact"],
            "finding": "Primary judge flagged tenancy/deposit/advance-rent terms from the landlord's Friday message; that message only corrects handover date.",
            "root_assessment": "This source-attribution ambiguity remains a valid concern even though the independent review did not flag it. Asking for terms is reasonable, but saying from the Friday message implies that unsupplied terms were in that message. Do not claim all compact-answer unsupported details were cleared by review.",
        },
        {
            "jobs": ["R5-full", "R5-compact"],
            "finding": "Primary judge marks one composite critical profile criterion missed in each answer; blinded review marks it met.",
            "root_assessment": "The disagreement is over restating unchanged move-date/age details and all profile fields, not choosing using a withdrawn budget, destination or layout restriction. Both choose on the revised profile. Report primary one critical miss per arm and independent zero, without claiming human-validated equivalence or erasing the stricter rubric reading.",
        },
    ]
    write("review-reconciliation-2026-09-08.json", {
        "review_type": "Post-hoc root synthesis of two separately blinded AI source reviews and frozen primary model judgments; not human ground truth",
        "primary_labels_modified": False,
        "additional_benchmark_model_calls": 0,
        "source_commit": summary["source_commit"],
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [LIVE / "plan.json", LIVE / "summary.json", *review_paths]},
        "denominator_rule": "Analysis: 16 always-required findings per arm. Rental: 33 always-required findings, with R1-F6/R2-F6 conditional accuracy reported separately. Applicable total is 34 per rental arm in both reviews.",
        "aggregates": dict(aggregates),
        "candidate_mapping_and_metrics": rows,
        "criterion_disagreements": disagreements,
        "root_source_annotations": annotations,
        "limits": ["Checklist counts are descriptive, not statistical equivalence or user satisfaction.", "Root annotations saw arm/cost information after the blinded reviews and are not a third blinded grader.", "All raw primary labels and independent source reasons remain inspectable; no single reconciled score is substituted."],
    })
    write("cost-ledger-2026-09-08.json", {
        "source_summary_sha256": sha(LIVE / "summary.json"),
        "definition": "Direct terminal CLI input + output; cached input is a subset, not added again. Not billing or account quota.",
        "known_cli_processed_tokens": summary["known_cli_processed_tokens"],
        "answer_processed_tokens": sum(a["usage"]["total_tokens"] for a in summary["answers"]),
        "judge_processed_tokens": summary["judge_processed_tokens"],
        "calls": summary["calls"],
        "arms": [{
            "experiment": category, "arm": arm,
            "calls": data["calls"], "tasks": data["tasks"], "usage": data["usage"],
            "change_percent_vs_full": (data["usage"]["total_tokens"] / arms["full"]["usage"]["total_tokens"] - 1) * 100,
            "seconds": round(sum(a["seconds"] for a in summary["answers"] if a["experiment"] == category and a["arm"] == arm), 3),
        } for category, arms in summary["arms"].items() for arm, data in arms.items()],
        "answers": [{key: a[key] for key in ("id", "case_id", "arm", "experiment", "call_ids", "requested_documents", "supplied_document_ids", "usage", "seconds", "citation_check", "format_check", "protocol_violation")} for a in summary["answers"]],
        "excluded": ["Parent/subagent preparation and fixture/summary authorship", "Parent/subagent source review and documentation", "Offline compute", "Earlier separate cost-probe experiment"],
    })
    print(json.dumps({"aggregates": dict(aggregates), "criterion_disagreements": len(disagreements)}, indent=2))


if __name__ == "__main__":
    main()
