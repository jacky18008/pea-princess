#!/usr/bin/env python3
"""Verify review identity coverage; this checks completeness, not reviewer truth."""
import hashlib
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parents[1]
RUN = ROOT / "bench/results/ablation-2026-09-09/live-v1"


def read(path):
    return json.loads(path.read_text())


def unique(rows, fields):
    keys = [tuple(row[key] for key in fields) for row in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("Duplicate review identities: " + str(fields))
    return set(keys)


def check(label, expected, actual):
    if expected != actual:
        raise SystemExit(label + " coverage differs: " + str(expected ^ actual))
    return {"items": len(expected), "missing_or_extra": [], "complete": True}


def main():
    summary = read(RUN / "summary.json")
    if not summary["complete"]:
        raise SystemExit("Wait for the complete live run.")
    targeted = read(DOCS / "targeted-source-review.json")
    memory_review = read(DOCS / "memory-source-review.json")
    scalar_review = read(DOCS / "scalar-source-review.json")
    expected_flags, expected_critical = set(), set()
    for judge in summary["judgments"]:
        for a in judge["assessments"]:
            for kind in ("unsupported_claims", "contradictions"):
                for i, _ in enumerate(a["assessment"][kind]):
                    expected_flags.add((a["job_id"], kind, i))
            expected_critical.update((a["job_id"], key) for key in a["critical_missed"])
    expected_citations, expected_scalars = set(), set()
    for answer in summary["answers"]:
        expected_scalars.update((answer["id"], c["key"]) for c in answer["fact_check"]["checks"] if not c["pass"])
        expected_citations.update((answer["id"], i) for i, c in enumerate((answer["citation_check"] or {}).get("citations", [])) if not c["valid_supplied_excerpt"])
    actual_critical = {(r["answer_id"], r["reviewed_criterion_id"]) for r in targeted["criterion_omission_reviews"]}
    for row in targeted["rental_primary_flag_coverage"]["critical_omission_review_index"]:
        for pointer in row["source_review_pointers"]:
            item = targeted
            for part in pointer.strip("/").split("/"):
                item = item[int(part)] if isinstance(item, list) else item[part]
            if item["answer_id"] != row["answer_id"]:
                raise SystemExit("Wrong answer at critical review pointer " + pointer)
        actual_critical.add((row["answer_id"], row["criterion_id"]))
    expected_memory = set()
    for path in (RUN / "memories").glob("*.json"):
        memory = read(path)
        expected_memory.update((memory["call_id"], f["id"]) for f in memory["checks"]["facts"] if not f["exact_user_source_quote"])
        if memory["checks"]["duplicate_fact_ids"] or memory["checks"]["invalid_supersedes"]:
            raise SystemExit("Additional memory-integrity failures need explicit review coverage.")
    checks = {
        "primary_unsupported_and_contradiction_flags": check("primary flags", expected_flags, unique(targeted["flag_reviews"], ("answer_id", "primary_flag_type", "primary_flag_index"))),
        "primary_critical_omissions": check("critical", expected_critical, actual_critical),
        "invalid_answer_citations": check("citations", expected_citations, unique(targeted["citation_reviews"], ("answer_id", "citation_index"))),
        "scalar_mismatches": check("scalars", expected_scalars, unique(scalar_review["reviews"], ("answer_id", "key"))),
        "invalid_memory_quotes": check("memory", expected_memory, unique(memory_review["occurrences"], ("call_id", "fact_id"))),
    }
    result = {"complete": True, "scope": "Every primary material flag/critical omission and deterministic mismatch is source reviewed; prospective blind sample is audited separately. Identity coverage is not semantic validation or human ground truth.",
              "checks": checks,
              "review_sha256": {name: hashlib.sha256((DOCS / name).read_bytes()).hexdigest() for name in ("targeted-source-review.json", "scalar-source-review.json", "memory-source-review.json")}}
    (DOCS / "review-coverage-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
