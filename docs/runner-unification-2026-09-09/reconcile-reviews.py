#!/usr/bin/env python3
"""Reconcile fixed source reviews with primary judgments; never invoke a model.

Run after both source reviews and all ten judgments exist. Missing/incomplete
inputs exit nonzero before output is written. This script does not rescore,
adjudicate, modify, or silently fill in either evaluator's judgments.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


REPO = Path(__file__).resolve().parents[2]
DEFAULT_RUN = REPO / "bench/results/durable-quality-2026-09-09/live-v2"
EXPECTED = {**{f"A{i}": ("analysis", ("full", "summary", "adaptive")) for i in range(1, 5)},
            **{f"R{i}": ("rental", ("full", "compact")) for i in range(1, 7)}}


class InvalidInput(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidInput(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def indexed(items, key, label):
    result = {}
    for item in items:
        ident = item[key]
        require(ident not in result, f"Duplicate {label}: {ident}")
        result[ident] = item
    return result


def criterion_status(criterion):
    require(type(criterion["applicable"]) is bool, "applicable must be boolean")
    if not criterion["applicable"]:
        require(criterion["met"] in (None, False), "N/A criterion must not claim a pass")
        return "not_applicable"
    require(type(criterion["met"]) is bool, "Applicable criterion needs boolean met")
    return "met" if criterion["met"] else "missed"


def score(criteria, gold):
    applicable = [c for c in criteria if c["applicable"]]
    critical = [c for c in applicable if gold[c["id"]]["severity"] == "critical"]
    return {
        "criteria_total": len(criteria),
        "applicable_criteria": len(applicable),
        "met_criteria": sum(c["met"] for c in applicable),
        "critical_applicable": len(critical),
        "critical_met": sum(c["met"] for c in critical),
        "critical_missed": [c["id"] for c in critical if not c["met"]],
    }


def metrics(rows, side):
    scores = [r[side]["score"] for r in rows]
    total = {k: sum(s[k] for s in scores) for k in (
        "criteria_total", "applicable_criteria", "met_criteria", "critical_applicable", "critical_met")}
    total.update({
        "candidates": len(rows),
        "coverage_fraction": round(total["met_criteria"] / total["applicable_criteria"], 6)
        if total["applicable_criteria"] else None,
        "critical_misses": sum(len(s["critical_missed"]) for s in scores),
        "critical_miss_candidates": [r["job_id"] for r in rows if r[side]["score"]["critical_missed"]],
        "all_applicable_met_candidates": [r["job_id"] for r in rows
                                          if r[side]["score"]["met_criteria"] == r[side]["score"]["applicable_criteria"]],
    })
    for category in ("unsupported_claims", "contradictions", "exact_quote_defects"):
        if side == "primary" and category == "exact_quote_defects":
            total[category] = None
            total[category + "_candidates"] = None
            total[category + "_measurement"] = "not_measured_separately_by_primary_schema"
            continue
        total[category] = sum(len(r[side].get(category, [])) for r in rows)
        total[category + "_candidates"] = [r["job_id"] for r in rows if r[side].get(category)]
    return total


def analyze(run_dir, review_dir):
    # Read snapshots once; refuse missing files rather than wait, infer or publish partial totals.
    manifest = {}
    snapshots = {}

    def read(path):
        path = path.resolve()
        if path not in snapshots:
            require(path.is_file(), f"Required input not ready: {relative(path)}")
            snapshots[path] = path.read_bytes()
            manifest[relative(path)] = {"sha256": sha256(snapshots[path]), "bytes": len(snapshots[path])}
        return json.loads(snapshots[path])

    mapping = read(run_dir / "independent-review/unblind-mapping.json")
    expected_jobs = {f"{case}-{arm}" for case, (_, arms) in EXPECTED.items() for arm in arms}
    require(len(mapping) == 24 and set(mapping.values()) == expected_jobs, "Mapping must be bijective over all 24 planned jobs")
    require(len(set(mapping.values())) == len(mapping), "Mapping repeats an unblinded job")
    gold = {}
    reviews = {}
    review_sources = {}
    packet_candidates = {}
    for experiment in ("analysis", "rental"):
        cases = read(run_dir / f"{experiment}-cases.json")["cases"]
        expected_cases = {c for c, (e, _) in EXPECTED.items() if e == experiment}
        cases_by_id = indexed(cases, "id", "case")
        require(set(cases_by_id) == expected_cases, f"Unexpected {experiment} cases")
        for case in cases:
            gold[case["id"]] = indexed(case["gold"]["required_findings"], "id", "gold criterion")
        review_path = review_dir / f"{experiment}-source-review.json"
        document = read(review_path)
        packet_path = run_dir / f"independent-review/{experiment}-packet.json"
        packet = read(packet_path)
        require(document["packet_sha256"] == sha256(snapshots[packet_path.resolve()]), f"{experiment} packet hash differs from fixed review")
        candidates = document.get("reviews", document.get("candidates"))
        require(isinstance(candidates, list) and len(candidates) == 12, f"Expected 12 {experiment} source reviews")
        for group in packet["groups"]:
            case_id = group["case"]["id"]
            packet_gold = indexed(group["case"]["gold"]["required_findings"], "id", "packet criterion")
            require(packet_gold == gold[case_id], f"{case_id}: packet gold differs from run gold")
            for candidate_id, candidate in group["candidates"].items():
                require(candidate_id not in packet_candidates, f"Duplicate packet candidate {candidate_id}")
                packet_candidates[candidate_id] = {"case_id": case_id, "candidate": candidate}
        for candidate in candidates:
            ident = candidate["candidate_id"]
            require(ident not in reviews, f"Duplicate review candidate {ident}")
            reviews[ident] = candidate
            review_sources[ident] = relative(review_path)
    require(set(reviews) == set(mapping) == set(packet_candidates), "Mapping, source review and packet candidates differ")
    primary = {}
    primary_sources = {}
    for case_id, (experiment, arms) in EXPECTED.items():
        path = run_dir / f"judgments/{case_id}.json"
        judgment = read(path)
        require(judgment["case_id"] == case_id and judgment["experiment"] == experiment, f"Wrong identity in {path}")
        case_assessments = indexed(judgment["assessments"], "job_id", "primary job")
        require(set(case_assessments) == {f"{case_id}-{arm}" for arm in arms}, f"Incomplete/extra primary jobs in {case_id}")
        for job_id, assessment in case_assessments.items():
            require(job_id not in primary, f"Duplicate primary job {job_id}")
            primary[job_id] = assessment
            primary_sources[job_id] = relative(path)
    require(set(primary) == expected_jobs, "Expected all 24 primary assessments in ten judgments")

    comparisons = []
    for candidate_id, job_id in sorted(mapping.items()):
        source = reviews[candidate_id]
        case_id, arm = job_id.split("-", 1)
        experiment = EXPECTED[case_id][0]
        require(source["case_id"] == case_id == packet_candidates[candidate_id]["case_id"], f"Case mapping mismatch: {candidate_id}")
        record = primary[job_id]
        assessment = record["assessment"]
        source_criteria = indexed(source["criteria"], "id", f"{candidate_id} source criterion")
        primary_criteria = indexed(assessment["criteria"], "id", f"{job_id} primary criterion")
        require(set(source_criteria) == set(primary_criteria) == set(gold[case_id]), f"Missing/extra criteria: {job_id}")
        criteria = []
        for criterion_id, finding in gold[case_id].items():
            independent = source_criteria[criterion_id]
            judged = primary_criteria[criterion_id]
            require(independent["severity"] == finding["severity"], f"Severity differs: {candidate_id}/{criterion_id}")
            for entry in (independent, judged):
                require(isinstance(entry.get("reason"), str) and bool(entry["reason"].strip()), f"Missing rationale: {candidate_id}/{criterion_id}")
            independent_status, primary_status = criterion_status(independent), criterion_status(judged)
            criteria.append({
                "id": criterion_id, "description": finding["description"], "severity": finding["severity"],
                "agreement": independent_status == primary_status,
                "independent_status": independent_status, "primary_status": primary_status,
                "independent": independent, "primary": judged,
            })
        source_score = score(source["criteria"], gold[case_id])
        primary_score = score(assessment["criteria"], gold[case_id])
        require(source_score["met_criteria"] == source.get("required_met", source.get("met_criteria")), f"Independent saved met count differs: {job_id}")
        require(source_score["applicable_criteria"] == source.get("required_total", source.get("applicable_criteria")), f"Independent saved total differs: {job_id}")
        saved_critical = source.get("critical_missed", source.get("critical_misses", []))
        saved_critical_ids = [c["criterion_id"] if isinstance(c, dict) else c for c in saved_critical]
        require(set(source_score["critical_missed"]) == set(saved_critical_ids), f"Independent saved critical count differs: {job_id}")
        require(primary_score["met_criteria"] == record["required_met"] and primary_score["applicable_criteria"] == record["required_total"], f"Primary saved counts differ: {job_id}")
        require(set(primary_score["critical_missed"]) == set(record["critical_missed"]), f"Primary saved critical count differs: {job_id}")
        facts = source.get("factual_audit", source)
        comparisons.append({
            "candidate_id": candidate_id, "job_id": job_id, "case_id": case_id,
            "experiment": experiment, "arm": arm, "criteria": criteria,
            "disagreement_ids": [c["id"] for c in criteria if not c["agreement"]],
            "independent": {
                "source": review_sources[candidate_id], "score": source_score,
                "unsupported_claims": facts["unsupported_claims"], "contradictions": facts["contradictions"],
                "exact_quote_defects": source.get("exact_quote_defects", []),
                "review_notes": source.get("review_notes", source.get("minor_or_presentation_notes", [])),
                "main_decision_correct": source.get("main_decision_correct"),
                "evidence_absence_honesty": source.get("evidence_absence_honesty"),
                "practical_next_step": source.get("practical_next_step"),
                "no_extra_user_burden": source.get("no_extra_user_burden"),
            },
            "primary": {
                "source": primary_sources[job_id], "score": primary_score,
                "unsupported_claims": assessment["unsupported_claims"], "contradictions": assessment["contradictions"],
                "exact_quote_defects": [],
                "exact_quote_defects_note": "The primary schema has no separate quote-defect category; an empty list means not separately collected, not zero defects.",
                "useful_next_step": assessment["useful_next_step"],
                "appropriate_uncertainty": assessment["appropriate_uncertainty"],
                "user_burden_ok": assessment["user_burden_ok"], "overall_notes": assessment["overall_notes"],
            },
        })

    all_criteria = [c for row in comparisons for c in row["criteria"]]
    require(len(comparisons) == 24 and len(all_criteria) == 118, "Expected 24 candidates and 118 rubric decisions")
    grouped = defaultdict(list)
    for row in comparisons:
        grouped[(row["experiment"], row["arm"])].append(row)
    per_arm = []
    for (experiment, arm), rows in sorted(grouped.items()):
        per_arm.append({"experiment": experiment, "arm": arm,
                        "independent": metrics(rows, "independent"), "primary": metrics(rows, "primary"),
                        "criterion_disagreements": sum(len(row["disagreement_ids"]) for row in rows)})
    agreement = Counter((c["independent_status"], c["primary_status"]) for c in all_criteria)
    result = {
        "version": 1, "review_type": "Post-score unblinded reconciliation of two fixed AI evaluations; not human ground truth",
        "run_dir": relative(run_dir),
        "policy": {
            "models_called": 0, "input_reviews_or_judgments_modified": False,
            "source_scores_fixed_before_unblinding": True,
            "no_adjudicated_or_merged_score": True,
            "not_applicable_normalization": "met:null and met:false compare equally when applicable:false; each raw decision and reason remains preserved.",
            "denominators": "Coverage uses each evaluator's applicable criteria. Critical labels come from authored gold, not inferred danger or human outcomes.",
            "factual_categories": "Counts preserve each evaluator's categories; quote defects, unsupported assertions, source-scope confusion and omissions must not be conflated.",
        },
        "validation": {
            "unique_candidates": 24, "unique_jobs": 24, "cases": 10, "primary_judgment_files": 10,
            "independent_reviews": 24, "primary_assessments": 24, "criterion_pairs": 118,
            "all_expected_criteria_present_once": True, "mapping_bijective": True,
            "packet_hashes_match_fixed_reviews": True, "packet_gold_matches_run_gold": True,
            "saved_score_counts_verified": True,
        },
        "summary": {
            "independent": metrics(comparisons, "independent"), "primary": metrics(comparisons, "primary"),
            "criterion_agreements": sum(c["agreement"] for c in all_criteria),
            "criterion_disagreements": sum(not c["agreement"] for c in all_criteria),
            "agreement_fraction": round(sum(c["agreement"] for c in all_criteria) / len(all_criteria), 6),
            "status_matrix": [{"independent": a, "primary": b, "count": n} for (a, b), n in sorted(agreement.items())],
        },
        "per_arm": per_arm, "comparisons": comparisons,
        "limitations": [
            "All 24 answers were preselected before generation. This is one small synthetic run, without independent generations or statistical quality-equivalence evidence.",
            "Independent reviews were done directly by project AI agents. They are independent of primary scores but not a human or external-panel truth standard; visible evidence may reveal treatment.",
            "The primary judge sees full source documents. Analysis summary answers see only summary/catalog; marking their correct statements about missing visible evidence as contradictions confuses evaluator evidence with candidate evidence.",
            "Composite criteria admit interpretation differences. Both original decisions, response quotations and rationales are retained; this report does not retroactively rescore either side.",
            "Primary unsupported/contradiction totals and independent factual totals use different practical category interpretations. They are not interchangeable hallucination rates.",
            "Costs, model telemetry and output equivalence are outside this reconciliation; root separately audits the complete ledger.",
        ],
        "input_manifest": dict(sorted(manifest.items())),
        "script_sha256": sha256(Path(__file__).read_bytes()),
    }
    # Avoid publishing a mixed snapshot if a supposedly fixed input changes mid-read.
    for path, original in snapshots.items():
        require(path.read_bytes() == original, f"Input changed while reconciling: {relative(path)}")
    return result


def format_metric(m):
    return f"{m['met_criteria']}/{m['applicable_criteria']} ({m['coverage_fraction']:.1%})"


def quote_lines(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return "\n".join("> " + line for line in text.splitlines())


def markdown(result):
    summary = result["summary"]
    lines = ["# 固定評分解盲後對照：24 份答案", "",
             "這份文件比較已固定的獨立 AI source review 與原始 model judge；兩邊都不是人工 ground truth。解盲僅用於連結答案與比較，沒有修改原始分數、評語或生成新答案。", "",
             f"完整性：24 個唯一候選、10 份 primary judgments、118 組完整 criterion decisions；其中兩邊各有 {summary['independent']['criteria_total'] - summary['independent']['applicable_criteria']} 個 N/A。"
             f"逐項一致 {summary['criterion_agreements']}/118，差異 {summary['criterion_disagreements']}/118。", "",
             "| 實驗 / arm | 獨立 coverage | Primary coverage | 獨立 / primary critical misses | 獨立 / primary unsupported | 獨立 / primary contradictions | criterion 差異 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for row in result["per_arm"]:
        a, b = row["independent"], row["primary"]
        lines.append(f"| {row['experiment']} / {row['arm']} | {format_metric(a)} | {format_metric(b)} | {a['critical_misses']} / {b['critical_misses']} | {a['unsupported_claims']} / {b['unsupported_claims']} | {a['contradictions']} / {b['contradictions']} | {row['criterion_disagreements']} |")
    lines.extend(["", "Coverage 分母是各自判為 applicable 的條件。Critical 是原始 rubric 標籤；例如省略目前租金成分可以是 critical-labelled miss，而不代表建議錯誤或捏造租金。上表的 unsupported / contradictions 保留各 evaluator 的分類，不能直接當成同一定義的 hallucination rate。", "",
                  "分析 full 的一個引用缺陷（`同じ` 取代來源的 `same`）被 primary 放在 unsupported；獨立 review 將其分開記錄。獨立 review 合計只有一個 exact-quote defect；primary schema 沒有獨立 quote-defect 欄位，因此不把空欄宣稱為零缺陷。", "",
                  "Primary 對部分 summary 答案的矛盾判斷，把自己看到的完整文件當成候選也看過。候選正確說明可見資料不足，仍可能漏掉必須找出的 finding；這兩件事應分開讀。下面逐字保留原始理由，沒有據此回改分數。", "",
                  "## 逐候選分數", "", "| Candidate | 解盲 job | 獨立 | Primary | 不一致條件 |", "|---|---|---:|---:|---|"])
    for row in result["comparisons"]:
        a, b = row["independent"]["score"], row["primary"]["score"]
        lines.append(f"| {row['candidate_id']} | {row['job_id']} | {a['met_criteria']}/{a['applicable_criteria']} | {b['met_criteria']}/{b['applicable_criteria']} | {', '.join(row['disagreement_ids']) or '—'} |")
    lines.extend(["", "## Criterion-level 差異與原始理由", ""])
    for row in result["comparisons"]:
        for c in row["criteria"]:
            if c["agreement"]:
                continue
            lines.extend([f"### {row['job_id']} · {c['id']} ({c['severity']})", "", c["description"], "",
                          f"獨立：**{c['independent_status']}**。", "", quote_lines(c["independent"]["reason"]), ""])
            quotes = c["independent"].get("answer_quotes", [c["independent"].get("response_quote", "")])
            if any(quotes):
                lines.extend(["獨立 review 留存的答案摘錄：", ""])
                lines.extend(quote_lines(q) for q in quotes if q)
                lines.append("")
            lines.extend([f"Primary：**{c['primary_status']}**。", "", quote_lines(c["primary"]["reason"]), ""])
    lines.extend(["## 事實／引用分類：保留兩邊原話", ""])
    for row in result["comparisons"]:
        categories = ("unsupported_claims", "contradictions", "exact_quote_defects")
        if not any(row[side][category] for side in ("independent", "primary") for category in categories):
            continue
        lines.extend([f"### {row['job_id']}", ""])
        for side in ("independent", "primary"):
            for category in categories:
                issues = row[side][category]
                if not issues:
                    continue
                lines.extend([f"{side} / {category}：", ""])
                for issue in issues:
                    claim = issue.get("claim", issue.get("quote", ""))
                    lines.extend([quote_lines(claim), ""])
                    if issue.get("reason"):
                        lines.extend([quote_lines(issue["reason"]), ""])
    lines.extend(["## 範圍、限制與重現", ""])
    lines.extend(f"- {limitation}" for limitation in result["limitations"])
    lines.extend(["", "執行 `python3 docs/runner-unification-2026-09-09/reconcile-reviews.py` 重建此文件及 JSON。輸入未齊或不一致時會失敗且不發布部分結果；不等待、不呼叫模型、不修改原始 review/judgments。JSON 保存全部 118 項雙方 criterion、原始理由、每 arm 統計及輸入 SHA-256。", ""])
    return "\n".join(lines)


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix=".reconcile-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--review-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        result = analyze(args.run_dir.resolve(), args.review_dir.resolve())
    except (InvalidInput, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Reconciliation not published: {exc}", file=sys.stderr)
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(args.output_dir / "source-review-comparison.json", json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    atomic_write(args.output_dir / "source-review-comparison.md", markdown(result))
    print(json.dumps({"validation": result["validation"], "summary": result["summary"], "per_arm": result["per_arm"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
