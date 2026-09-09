#!/usr/bin/env python3
"""Offline post-run contrasts and tables; does not import/invoke benchmark code."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
DOCS = Path(__file__).resolve().parent
DEFAULT = ROOT / "bench/results/ablation-2026-09-09/live-v1"
STATE_ARMS = ("state", "state_no_sources", "state_no_updates", "state_neither")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT)
    args = parser.parse_args()
    live = args.run.resolve()
    summary = read(live / "summary.json")
    if not summary["complete"] or not summary["usage_coverage_complete"]:
        raise SystemExit("Refuse to publish complete-run contrasts from an incomplete run.")
    calls = {r["id"]: r for r in (read(p) for p in (live / "calls").glob("*/result.json"))}
    grades = {r["job_id"]: r for j in summary["judgments"] for r in j["assessments"]}
    tokens = lambda ids: sum(calls[c]["usage"]["total_tokens"] for c in set(ids))
    rows = []
    for answer in summary["answers"]:
        grade = grades[answer["id"]]
        generators = answer["dependency_call_ids"]
        # Rental T2 updates add just their latest generation to incremental cost.
        incremental_generators = generators[-1:] if answer["experiment"] == "rental" else generators
        row = {k: answer.get(k) for k in ("id", "experiment", "case_id", "repeat", "turn", "length", "arm")}
        row.update(answer_tokens=tokens(answer["call_ids"]),
                   incremental_generation_tokens=tokens(incremental_generators),
                   incremental_pipeline_tokens=tokens(answer["call_ids"] + incremental_generators),
                   required_met=grade["required_met"], required_total=grade["required_total"],
                   critical_missed=grade["critical_missed"],
                   scalar_passed=answer["fact_check"]["passed"], scalar_total=answer["fact_check"]["total"],
                   scalar_mismatches=[r for r in answer["fact_check"]["checks"] if not r["pass"]],
                   unsupported_annotations=grade["assessment"]["unsupported_claims"],
                   contradiction_annotations=grade["assessment"]["contradictions"],
                   invalid_quotes=(answer["citation_check"] or {}).get("invalid", 0),
                   supplied_document_ids=answer.get("supplied_document_ids"),
                   requested_document_ids=answer.get("requested_document_ids"),
                   oracle_document_ids=answer.get("oracle_document_ids"),
                   answer_call_prompt_characters=sum(calls[c]["prompt_characters"] for c in answer["call_ids"]),
                   seconds=sum(calls[c]["seconds"] for c in answer["call_ids"]))
        rows.append(row)

    arms = []
    for key, original in summary["arms"].items():
        experiment, arm = key.split("/")
        subset = [r for r in rows if r["experiment"] == experiment and r["arm"] == arm]
        baseline = summary["arms"][experiment + ("/full" if experiment == "rental" else "/raw_full")]
        # Independent sum of incremental costs must match unique dependency union.
        assert sum(r["incremental_pipeline_tokens"] for r in subset) == original["standalone_pipeline_tokens"]
        arms.append({"experiment": experiment, "arm": arm, **original,
                     "pipeline_change_percent_vs_baseline": (original["standalone_pipeline_tokens"] / baseline["standalone_pipeline_tokens"] - 1) * 100,
                     "answer_change_percent_vs_baseline": (original["answer_tokens"] / baseline["answer_tokens"] - 1) * 100,
                     "finding_coverage_percent": 100 * original["required_met"] / original["required_total"],
                     "scalar_accuracy_percent": 100 * original["scalar_passed"] / original["scalar_total"]})

    matched = defaultdict(dict)
    for row in rows:
        key = (row["experiment"], row["case_id"], row["repeat"], row["turn"], row["length"])
        matched[key][row["arm"]] = row
    pairs = []
    for key, cells in matched.items():
        base = cells["full" if key[0] == "rental" else "raw_full"]
        for arm, row in cells.items():
            pairs.append({"id": row["id"], "baseline_id": base["id"],
                          "finding_delta": row["required_met"] - base["required_met"],
                          "incremental_pipeline_token_delta": row["incremental_pipeline_tokens"] - base["incremental_pipeline_tokens"],
                          "new_critical_missed": sorted(set(row["critical_missed"]) - set(base["critical_missed"])),
                          "scalar_delta": row["scalar_passed"] - base["scalar_passed"]})
    pair_by_id = {p["id"]: p for p in pairs}

    factorial = []
    for key, cells in matched.items():
        if key[0] != "rental":
            continue
        record = {"case_id": key[1], "repeat": key[2], "turn": key[3]}
        for metric in ("required_met", "scalar_passed", "answer_tokens", "incremental_pipeline_tokens"):
            s, ns, nu, nn = [cells[arm][metric] for arm in STATE_ARMS]
            record[metric] = {"source_effect": ((s - ns) + (nu - nn)) / 2,
                              "replacement_metadata_effect": ((s - nu) + (ns - nn)) / 2,
                              "interaction": s - ns - nu + nn}
        factorial.append(record)
    factorial_means = {}
    for turn in ("all", "T1", "T2"):
        selected = [f for f in factorial if turn == "all" or f["turn"] == turn]
        factorial_means[turn] = {
            "matched_cells": len(selected),
            "mean_effects": {metric: {effect: statistics.mean(f[metric][effect] for f in selected)
                                     for effect in ("source_effect", "replacement_metadata_effect", "interaction")}
                             for metric in ("required_met", "scalar_passed", "answer_tokens", "incremental_pipeline_tokens")},
        }

    length_effects = []
    for case_id in ("E1", "E2", "E3"):
        for arm in ("raw_full", "full", "summary", "lexical", "adaptive", "oracle"):
            short = next(r for r in rows if r["case_id"] == case_id and r["length"] == "short" and r["arm"] == arm)
            long = next(r for r in rows if r["case_id"] == case_id and r["length"] == "long" and r["arm"] == arm)
            length_effects.append({"case_id": case_id, "arm": arm,
                                   "short_pipeline_tokens": short["incremental_pipeline_tokens"],
                                   "long_pipeline_tokens": long["incremental_pipeline_tokens"],
                                   "long_minus_short_pipeline_tokens": long["incremental_pipeline_tokens"] - short["incremental_pipeline_tokens"],
                                   "short_findings": short["required_met"], "long_findings": long["required_met"],
                                   "short_critical_missed": short["critical_missed"], "long_critical_missed": long["critical_missed"]})

    def contrast(before, after, **metadata):
        return {**metadata, "before_id": before["id"], "after_id": after["id"],
                "answer_token_delta": after["answer_tokens"] - before["answer_tokens"],
                "incremental_pipeline_token_delta": after["incremental_pipeline_tokens"] - before["incremental_pipeline_tokens"],
                "finding_delta": after["required_met"] - before["required_met"],
                "scalar_delta": after["scalar_passed"] - before["scalar_passed"],
                "before_critical_missed": before["critical_missed"],
                "after_critical_missed": after["critical_missed"]}

    mechanisms = []
    amortization = []
    for key, cells in matched.items():
        if key[0] != "retrieval":
            continue
        for before, after, label in (("raw_full", "full", "add_summary"),
                                     ("full", "summary", "remove_documents"),
                                     ("summary", "lexical", "add_lexical_retrieval"),
                                     ("lexical", "oracle", "oracle_selection_headroom"),
                                     ("adaptive", "oracle", "adaptive_vs_oracle_bundle")):
            mechanisms.append(contrast(cells[before], cells[after], case_id=key[1], length=key[4], mechanism=label))
        for arm, candidate in cells.items():
            if arm in ("raw_full", "oracle"):
                continue
            saving = cells["raw_full"]["answer_tokens"] - candidate["answer_tokens"]
            generator = candidate["incremental_generation_tokens"]
            amortization.append({"case_id": key[1], "length": key[4], "arm": arm,
                                 "observed_answer_token_saving": saving, "one_summary_tokens": generator,
                                 "hypothetical_reuses_to_strictly_break_even": generator // saving + 1 if saving > 0 else None,
                                 "assumption": "Post-hoc arithmetic only: exactly reuse the unchanged generated summary, with constant observed per-answer cost and quality. No reuse experiment was run; other questions may require different information."})
    repeats, turns = [], []
    rental_rows = [r for r in rows if r["experiment"] == "rental"]
    for case_id in ("S1", "S2", "S3"):
        for arm in ("full", "prose", *STATE_ARMS):
            subset = [r for r in rental_rows if r["case_id"] == case_id and r["arm"] == arm]
            for turn in ("T1", "T2"):
                pair = sorted((r for r in subset if r["turn"] == turn), key=lambda r: r["repeat"])
                repeats.append(contrast(*pair, case_id=case_id, arm=arm, turn=turn,
                                        interpretation="Repeat 2 minus repeat 1; same fixture, stochastic samples."))
            for repeat in sorted(set(r["repeat"] for r in subset)):
                pair = sorted((r for r in subset if r["repeat"] == repeat), key=lambda r: r["turn"])
                turns.append(contrast(*pair, case_id=case_id, arm=arm, repeat=repeat,
                                      interpretation="T2 minus T1; questions and criteria differ, descriptive progression only."))

    gates = []
    for arm in arms:
        selected = [r for r in rows if r["experiment"] == arm["experiment"] and r["arm"] == arm["arm"]]
        new_critical = [p for r in selected for p in pair_by_id[r["id"]]["new_critical_missed"]]
        baseline = summary["arms"][arm["experiment"] + ("/full" if arm["experiment"] == "rental" else "/raw_full")]
        gates.append({"experiment": arm["experiment"], "arm": arm["arm"],
                      "is_implementable_candidate": not ((arm["experiment"] == "rental" and arm["arm"] == "full") or (arm["experiment"] == "retrieval" and arm["arm"] in ("raw_full", "oracle"))),
                      "saves_at_least_10_percent_pipeline": 10 * arm["standalone_pipeline_tokens"] <= 9 * baseline["standalone_pipeline_tokens"],
                      "no_new_paired_critical_misses": not new_critical,
                      "new_paired_critical_miss_ids": new_critical,
                      "no_lower_scalar_accuracy": arm["scalar_passed"] >= baseline["scalar_passed"],
                      "source_reviewed_consequential_claim_gate": "Requires separate source-review conclusion; raw annotation counts are not ground truth."})

    memories = [read(p) for p in sorted((live / "memories").glob("*.json"))]
    output = {"source_commit": summary["source_commit"], "source_summary_sha256": sha(live / "summary.json"),
              "complete": True, "actual_cli_calls": summary["calls"], "actual_cli_processed_tokens": summary["known_cli_processed_tokens"],
              "purpose_totals": summary["purpose_totals"], "arms": arms, "per_answer": rows,
              "paired_baseline_contrasts": pairs, "memory_factorial_cells": factorial,
              "memory_factorial_mean_effects": factorial_means, "retrieval_length_effects": length_effects,
              "retrieval_mechanism_contrasts": mechanisms, "rental_repeat_contrasts": repeats,
              "rental_turn_progression": turns,
              "posthoc_summary_amortization_scenarios": amortization,
              "provisional_adoption_gates": gates,
              "memory_generation_checks": [{"call_id": m["call_id"], "checks": m["checks"],
                                            "fact_count": len(m["memory"]["facts"]),
                                            "summary_characters": len(m["memory"]["summary"]),
                                            "status_counts": dict(Counter(f["status"] for f in m["memory"]["facts"])),
                                            "facts_json_characters": len(json.dumps(m["memory"]["facts"], ensure_ascii=False)),
                                            "note": "Character counts describe size, not tokenizer counts; membership checks do not establish semantic completeness."}
                                           for m in memories],
              "accounting": summary["accounting"], "limitations": summary["limitations"],
              "analysis_scope": "Descriptive paired contrasts; no p-values or confidence intervals. Primary judge labels remain unchanged; separate source-review reconciliation required."}
    write(DOCS / "ablation-results.json", output)
    (DOCS / "live-results.json").write_bytes((live / "summary.json").read_bytes())
    table = ["# Generated numerical tables", "", "Primary model-judge labels; source reviews are separate. All pipeline costs include required automatic generation/update. Arm totals share generator calls and must not be summed.", "",
             "| Experiment | Arm | Answer tokens | Generator tokens | Pipeline tokens | Δ pipeline vs baseline | Findings | Scalars | Critical misses |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in arms:
        table.append("| {experiment} | {arm} | {answer_tokens:,} | {dependency_tokens:,} | {standalone_pipeline_tokens:,} | {pipeline_change_percent_vs_baseline:+.2f}% | {required_met}/{required_total} | {scalar_passed}/{scalar_total} | {critical_misses} |".format(**arm))
    table += ["", "## Per-answer results", "", "Incremental pipeline tokens add only the generation/update introduced at that turn. Summed per arm, these equal the union-of-dependencies pipeline total.", "", "| Answer | Answer tokens | Incremental pipeline | Findings | Scalars | Critical misses |", "|---|---:|---:|---:|---:|---|"]
    for row in rows:
        table.append("| {id} | {answer_tokens:,} | {incremental_pipeline_tokens:,} | {required_met}/{required_total} | {scalar_passed}/{scalar_total} | {critical} |".format(**row, critical=", ".join(row["critical_missed"]) or "—"))
    table += ["", "## Memory metadata factorial effects", "", "Positive quality effects indicate more findings/scalars when metadata is present; positive token effects indicate more usage. Counts are per answer, not percentage points. These metadata-consumption effects use a common rich updater.", "", "| Turn stratum | Metric | Source effect | Replacement effect | Interaction |", "|---|---|---:|---:|---:|"]
    for turn, record in factorial_means.items():
        for metric, effects in record["mean_effects"].items():
            table.append("| %s | %s | %.3f | %.3f | %.3f |" % (turn, metric, effects["source_effect"], effects["replacement_metadata_effect"], effects["interaction"]))
    for heading, records in (("Retrieval mechanism contrasts", mechanisms), ("Rental repeat contrasts", repeats),
                             ("Rental turn progression (different questions and criteria)", turns)):
        table += ["", "## " + heading, "", "After minus before; critical criterion IDs belong to their own turns.", "",
                  "| Before | After | Δ answer tokens | Δ incremental pipeline | Δ findings | Δ scalars |", "|---|---|---:|---:|---:|---:|"]
        for record in records:
            table.append("| {before_id} | {after_id} | {answer_token_delta:+,} | {incremental_pipeline_token_delta:+,} | {finding_delta:+} | {scalar_delta:+} |".format(**record))
    (DOCS / "numerical-tables.md").write_text("\n".join(table) + "\n")
    print(json.dumps({"calls": output["actual_cli_calls"], "tokens": output["actual_cli_processed_tokens"], "arms": len(arms), "answers": len(rows), "factorial_cells": len(factorial)}, indent=2))


if __name__ == "__main__":
    main()
