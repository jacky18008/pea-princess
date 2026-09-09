#!/usr/bin/env python3
"""Independent offline auditor. No runner imports, models, polling or run writes.

Incomplete runs produce a stdout notice and exit 2, without writing an audit.
Use --output for a new JSON file after completion; existing files are never replaced.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN = ROOT / "bench/results/ablation-2026-09-09/live-v1"
FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens",
          "output_tokens", "reasoning_output_tokens")
CATALOG = "ERROR codex_models_manager::manager: failed to refresh available models: timeout waiting for child process to exit"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def usage_from_terminal(events):
    terminal = [e for e in events if e.get("type") == "turn.completed"]
    raw = terminal[0].get("usage") if len(terminal) == 1 else None
    raw = raw if isinstance(raw, dict) else {}
    values = {k: raw[k] if type(raw.get(k)) is int and raw[k] >= 0 else None for k in FIELDS}
    errors = [] if len(terminal) == 1 else ["not exactly one terminal completion"]
    for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
        if values[k] is None:
            errors.append("unknown/invalid direct " + k)
    inp, cache, out, reasoning = [values[k] for k in
                                 ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")]
    if inp is not None and cache is not None and cache > inp:
        errors.append("cached input exceeds input")
    if out is not None and reasoning is not None and reasoning > out:
        errors.append("reasoning output exceeds output")
    values["total_tokens"] = inp + out if inp is not None and out is not None else None
    return raw, values, errors, len(terminal)


def aggregate(rows):
    result = {}
    for key in FIELDS + ("total_tokens",):
        known = [r[key] for r in rows if r.get(key) is not None]
        result["known_" + key] = sum(known)
        result["unknown_" + key + "_calls"] = len(rows) - len(known)
        result[key] = sum(known) if len(rows) == len(known) else None
    inp, cache = result["input_tokens"], result["cached_input_tokens"]
    result["uncached_input_tokens"] = inp - cache if inp is not None and cache is not None else None
    return result


def completion_notice(run):
    try:
        summary = read(run / "summary.json") if (run / "summary.json").exists() else {}
        progress = read(run / "control/progress.json") if (run / "control/progress.json").exists() else {}
    except (ValueError, OSError):
        return {"status": "incomplete", "reason": "finished snapshot not readable"}
    if not summary.get("complete") or not progress.get("plan_complete") or progress.get("paused"):
        return {"status": "incomplete", "summary_complete": summary.get("complete", False),
                "controller_plan_complete": progress.get("plan_complete", False),
                "paused": progress.get("paused"), "completed_calls": progress.get("completed_calls"),
                "pending_call_ids": progress.get("pending_call_ids", []),
                "skipped_call_ids": progress.get("skipped_call_ids", [])}
    return None


def audit(run):
    issues, warnings = [], []

    def check(condition, message):
        if not condition:
            issues.append(message)

    fixed = {n: sha(run / n) for n in
             ("plan.json", "summary.json", "control/checkpoint.json", "control/progress.json")}
    plan, summary = read(run / "plan.json"), read(run / "summary.json")
    planned = plan["planned_call_ids"]
    check(len(planned) == len(set(planned)), "duplicate frozen call IDs")
    source_checks, prepared_checks = [], []
    for name, expected in plan["source_sha256"].items():
        actual = sha(ROOT / name)
        git = subprocess.run(["git", "show", plan["source_commit"] + ":" + name], cwd=str(ROOT),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        committed = hashlib.sha256(git.stdout).hexdigest() if git.returncode == 0 else None
        check(actual == expected, "current source hash: " + name)
        check(committed == expected if committed else name.startswith("dist/"), "frozen Git source: " + name)
        source_checks.append(dict(path=name, expected=expected, current=actual, committed=committed))
    for name, expected in plan["prepared_sha256"].items():
        actual = sha(run / name)
        check(actual == expected, "prepared hash: " + name)
        prepared_checks.append(dict(path=name, expected=expected, actual=actual))
    check(summary["plan_sha256"] == fixed["plan.json"], "summary plan hash")
    check(summary["source_commit"] == plan["source_commit"], "summary source commit")
    envelope, progress = read(run / "control/checkpoint.json"), read(run / "control/progress.json")
    state = envelope["state"]
    check(canonical_sha(state) == envelope["state_sha256"], "controller checkpoint checksum")
    check(state["planned_call_ids"] == planned, "controller frozen plan")
    check(state["reducer_sha256"] == plan["source_sha256"]["bench/report_control.py"], "controller reducer hash")
    ledger, skipped = state["calls"], state["skipped"]
    check(not set(ledger) & set(skipped), "skipped IDs also dispatched")
    check(set(ledger) | set(skipped) == set(planned), "controller plan coverage")
    check(all(i.endswith("-adaptive-retrieved") and isinstance(r, str) and r.strip()
              for i, r in skipped.items()), "invalid optional skips/reasons")
    check(summary["controller"] == progress, "summary/controller progress differs")
    rental = {c["id"]: c for c in read(run / "rental-cases.json")["cases"]}
    retrieval = {c["id"]: c for c in read(run / "retrieval-cases.json")["cases"]}
    groups = {g["id"]: g for g in plan["groups"]}
    jobs = {j: g for g in groups.values() for j in g["jobs"]}
    roles = {i: ("calibration", i, "calibration") for i in planned if i.startswith("cal-")}
    for g in groups.values():
        gid = g["id"]
        roles[gid + "-judge"] = ("judge", gid, "judge")
        if g["experiment"] == "rental":
            first = rental[g["case_id"]]["turns"][0]["id"]
            roles[gid + "-memory"] = ("memory", gid, "initial" if g["turn"] == first else "update")
        else:
            roles[gid + "-summary-generation"] = ("summary_generation", gid, "summary_generation")
        for job in g["jobs"]:
            adaptive = g["experiment"] == "retrieval" and job.endswith("-adaptive")
            roles[job] = ("answer", job, "selection_or_answer" if adaptive else "answer")
            if adaptive:
                roles[job + "-retrieved"] = ("retrieval_answer", job, "retrieved")
    check(set(roles) == set(planned), "unclassified frozen calls")
    directories = {p.name: p for p in (run / "calls").iterdir() if p.is_dir()}
    records = {p.parent.name: read(p) for p in (run / "calls").glob("*/result.json")}
    attempted = set(directories) | {r["id"] for r in records.values()} | set(ledger)
    missing, orphans = sorted(attempted - set(records)), sorted(attempted - set(planned))
    check(not missing, "attempts missing result: " + repr(missing))
    check(not orphans, "unplanned/orphan attempts: " + repr(orphans))
    check(set(directories) == set(records) == set(ledger), "raw/result/ledger attempt IDs differ")
    check(not set(directories) & set(skipped), "skipped call has raw artifacts")
    calls, raw_answers, threads, started, diagnostics = {}, {}, [], [], []
    model_counts, event_types, item_types = (collections.Counter() for _ in range(3))
    raw_errors, tools, malformed, hash_checks = [], [], [], 0
    for cid, directory in sorted(directories.items()):
        if cid not in records:
            continue
        record, cmd = records[cid], read(directory / "command.json")
        role, job, phase = roles.get(cid, (None, None, None))
        model = cmd[cmd.index("--model") + 1]
        model_counts[model] += 1
        target = plan["judge_model"] if role in ("judge", "calibration") else plan["answer_model"]
        check(cmd[:2] == ["codex", "exec"] and model == record["requested_model"] == target, cid + ": CLI/model")
        check(record["id"] == cid and record["purpose"] == role, cid + ": ID/purpose")
        check(record["effort"] == plan["effort"] and 'model_reasoning_effort="%s"' % plan["effort"] in cmd, cid + ": effort")
        check("--ignore-user-config" in cmd and "--ephemeral" in cmd and cmd[cmd.index("--sandbox") + 1] == "read-only", cid + ": CLI controls")
        for flag, path in (("--cd", directory), ("--output-schema", directory / "schema.json"),
                           ("--output-last-message", directory / "answer.txt")):
            check(cmd[cmd.index(flag) + 1] == str(path), cid + ": command " + flag)
        check(cmd[-1] == (directory / "prompt.txt").read_text(), cid + ": actual command prompt")
        hashes = {}
        for name, key in (("prompt.txt", "prompt_sha256"), ("schema.json", "schema_sha256"),
                          ("events.jsonl", "events_sha256"), ("answer.txt", "answer_sha256")):
            hashes[name] = sha(directory / name)
            check(hashes[name] == record[key], cid + ": recorded hash " + name)
            hash_checks += 1
        for name in ("result.json", "command.json", "stderr.txt"):
            hashes[name] = sha(directory / name)
        events = []
        for n, line in enumerate((directory / "events.jsonl").read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                malformed.append(dict(call_id=cid, line=n))
        for event in events:
            event_types[event.get("type")] += 1
            if event.get("thread_id"):
                threads.append(event["thread_id"])
            item = event.get("item") or {}
            if item.get("type"):
                item_types[item["type"]] += 1
            if item.get("type") not in (None, "agent_message", "reasoning"):
                tools.append(dict(call_id=cid, event=event))
            if event.get("type") in ("error", "turn.failed"):
                raw_errors.append(dict(call_id=cid, event=event))
        if any(e.get("type") == "turn.started" for e in events):
            started.append(cid)
        raw, usage, errors, terminal_count = usage_from_terminal(events)
        issues.extend(cid + ": " + e for e in errors)
        check(record["direct_terminal_usage"] == raw and record["terminal_usage_events"] == terminal_count, cid + ": direct metadata")
        check(record.get("diagnostic_unaccepted_usage") is None, cid + ": fallback/diagnostic usage")
        for k, value in usage.items():
            if value is not None:
                check((record.get("usage") or {}).get(k) == value, cid + ": normalized usage " + k)
        check(record["status"] == "complete" and record["exit_code"] == 0 and not record["timeout"], cid + ": status/exit/timeout")
        check(record["errors"] == [] and record["tool_events"] == [] and record["malformed_event_lines"] == 0, cid + ": stored diagnostics")
        messages = [json.loads(e["item"]["text"]) for e in events if (e.get("item") or {}).get("type") == "agent_message"]
        check(len(messages) == 1, cid + ": raw answer count")
        raw_answers[cid] = messages[-1]
        check(messages[-1] == record["answer"] == read(directory / "answer.txt"), cid + ": raw/saved answer")
        row = ledger.get(cid, {})
        check(row.get("record") == record and row.get("record_sha256") == canonical_sha(record), cid + ": controller record")
        check((row.get("role"), row.get("job_id"), row.get("phase")) == (role, job, phase), cid + ": controller metadata")
        check(row.get("failure_kind") is None, cid + ": controller failure")
        for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
            check(state["reducer_state"]["requests"][cid]["usage"][k] == usage[k], cid + ": reducer usage " + k)
        lines = [s for s in (directory / "stderr.txt").read_text().splitlines() if s.strip()]
        catalog = [s for s in lines if CATALOG in s]
        other = [s for s in lines if s != "Reading additional input from stdin..." and s not in catalog]
        diagnostics.append(dict(call_id=cid, nonempty=bool(lines), catalog_timeout_lines=catalog, other_lines=other))
        calls[cid] = dict(id=cid, role=role, job_id=job, phase=phase, cli_model=model, usage=usage, hashes=hashes)
    check(not raw_errors and not tools and not malformed, "raw errors/tools/malformed events")
    check(len(threads) == len(set(threads)) == len(calls), "duplicate/missing raw thread IDs")
    check(len(started) == len(calls), "missing raw started turns")

    def tokens(ids):
        return aggregate([calls[i]["usage"] for i in ids])["total_tokens"] if set(ids).issubset(calls) else None

    total = aggregate([c["usage"] for c in calls.values()])
    unknown = sorted(i for i, c in calls.items() if any(c["usage"][k] is None for k in
                                                      ("input_tokens", "cached_input_tokens", "output_tokens")))
    check(summary["calls"] == len(attempted) and summary["recorded_call_results"] == len(records), "summary attempt counts")
    check(summary["missing_result_call_ids"] == missing and summary["unknown_usage_call_ids"] == unknown, "summary unknown/missing IDs")
    check(summary["usage_coverage_complete"] == (not unknown), "summary usage coverage")
    check(summary["known_cli_processed_tokens"] == total["known_total_tokens"] and summary["cli_processed_tokens"] == total["total_tokens"], "whole-run raw/summary totals")
    check(len(attempted) <= plan["maximum_cli_calls"] and total["known_total_tokens"] <= plan["reported_token_stop_threshold"], "run bound exceeded")
    check(summary["claude_calls"] == 0 and not any("claude" in m.lower() for m in model_counts), "Claude model/call")
    for k in ("input_tokens", "cached_input_tokens", "output_tokens"):
        check(progress["usage"]["known_" + k] == total["known_" + k] and
              progress["usage"]["unknown_" + k + "_requests"] == total["unknown_" + k + "_calls"], "controller aggregate " + k)
    check(progress["usage"]["total_tokens"] == total["total_tokens"], "controller total")
    expected_progress = dict(planned_calls=len(planned), dispatched_calls=len(calls), completed_calls=len(calls),
                             failed_calls=0, skipped_calls=len(skipped), skipped_call_ids=list(skipped),
                             skip_reasons=skipped, completed_or_skipped_calls=len(calls) + len(skipped),
                             resolved_planned_calls=len(calls) + len(skipped), pending_call_ids=[],
                             plan_complete=len(calls) + len(skipped) == len(planned), paused=False, decision="report_results")
    for k, value in expected_progress.items():
        check(progress[k] == value, "controller coverage " + k)
    answers = {p.stem: read(p) for p in (run / "answers").glob("*.json")}
    check(set(answers) == set(jobs), "answer matrix coverage")
    check(summary["answers"] == [answers[k] for k in sorted(answers)], "summary answer copies")
    dependency_rows, direct_owners, deps_by_job = [], collections.Counter(), {}
    for job, answer in sorted(answers.items()):
        group, direct = jobs[job], [job]
        if group["experiment"] == "rental":
            turn_ids = [t["id"] for t in rental[group["case_id"]]["turns"]]
            index = turn_ids.index(group["turn"])
            earlier = [g for g in plan["groups"] if g["experiment"] == "rental" and
                       g["case_id"] == group["case_id"] and g["repeat"] == group["repeat"] and turn_ids.index(g["turn"]) <= index]
            deps = [] if answer["arm"] == "full" else [g["id"] + "-memory" for g in earlier]
            input_deps = list(deps)
            if index:
                prior = next(g for g in earlier if g["turn"] == turn_ids[index - 1])
                input_deps.append(next(j for j in prior["jobs"] if j.split("-", 3)[3] == answer["arm"]))
        else:
            deps = [] if answer["arm"] == "raw_full" else [group["id"] + "-summary-generation"]
            input_deps = list(deps)
            if answer["arm"] == "adaptive":
                requested = raw_answers[job].get("request_documents")
                doc_ids = {d["id"] for d in retrieval[group["case_id"]]["variants"][group["length"]]["documents"]}
                valid = isinstance(requested, list) and len(requested) <= 2 and all(isinstance(x, str) and x in doc_ids for x in requested)
                valid = valid and len(set(requested)) == len(requested)
                followup = job + "-retrieved"
                if valid and requested:
                    direct.append(followup)
                    input_deps.append(job)
                    check(followup in calls and followup not in skipped, job + ": requested follow-up absent")
                else:
                    check(followup in skipped and followup not in calls, job + ": unused follow-up not skipped")
                check(answer["requested_document_ids"] == requested, job + ": saved request differs")
        check(answer["call_ids"] == direct, job + ": direct call IDs")
        check(answer["dependency_call_ids"] == deps, job + ": shared dependencies")
        check(answer["input_dependency_call_ids"] == input_deps, job + ": input lineage")
        check(answer["final_answer"] == raw_answers[direct[-1]], job + ": final raw answer")
        check(not set(direct) & set(deps), job + ": direct/generation overlap")
        direct_owners.update(direct)
        deps_by_job[job] = deps
        dependency_rows.append(dict(job_id=job, direct_call_ids=direct, dependency_call_ids=deps,
                                    input_dependency_call_ids=input_deps, standalone_tokens=tokens(set(direct) | set(deps))))
    answer_ids = {i for i, c in calls.items() if c["role"] in ("answer", "retrieval_answer")}
    check(set(direct_owners) == answer_ids and all(n == 1 for n in direct_owners.values()), "orphan/duplicated physical answer call")
    arm_costs = {}
    for name, saved in summary["arms"].items():
        experiment, arm = name.split("/", 1)
        rows = [a for a in answers.values() if a["experiment"] == experiment and a["arm"] == arm]
        direct = {i for a in rows for i in a["call_ids"]}
        deps = {i for a in rows for i in deps_by_job[a["id"]]}
        value = dict(answers=len(rows), answer_calls=len(direct), dependency_calls=len(deps),
                     answer_tokens=tokens(direct), dependency_tokens=tokens(deps), standalone_pipeline_tokens=tokens(direct | deps))
        for k, n in value.items():
            check(saved[k] == n, name + ": arm accounting " + k)
        arm_costs[name] = dict(value, physical_call_ids=sorted(direct | deps))
    check(set(arm_costs) == {"rental/" + a for a in plan["rental_arms"]} | {"retrieval/" + a for a in plan["retrieval_arms"]}, "arm matrix")
    role_totals = {role: dict(calls=sum(c["role"] == role for c in calls.values()),
                              known_tokens=sum(c["usage"]["total_tokens"] or 0 for c in calls.values() if c["role"] == role))
                   for role in {c["role"] for c in calls.values()}}
    check(summary["purpose_totals"] == role_totals, "summary role totals")
    generation_ids = {i for i, c in calls.items() if c["role"] in ("memory", "summary_generation")}
    check({i for ds in deps_by_job.values() for i in ds} == generation_ids, "orphan/missing shared generator")
    categories = {"answer_and_retrieval": answer_ids, "shared_generation": generation_ids,
                  "judge": {i for i, c in calls.items() if c["role"] == "judge"},
                  "calibration": {i for i, c in calls.items() if c["role"] == "calibration"}}
    check(sum(len(s) for s in categories.values()) == len(calls) and set().union(*categories.values()) == set(calls), "whole-run partition")
    partition = {k: dict(calls=len(ids), tokens=tokens(ids)) for k, ids in categories.items()}
    check(sum(v["tokens"] or 0 for v in partition.values()) == total["total_tokens"], "whole-run disjoint partition total")
    judgments = {p.stem: read(p) for p in (run / "judgments").glob("*.json")}
    check(set(judgments) == set(groups), "judgment coverage")
    check(summary["judgments"] == [judgments[k] for k in sorted(judgments)], "summary judgment copies")
    for gid, judgment in judgments.items():
        raw, mask = raw_answers[gid + "-judge"]["assessments"], plan["judge_masks"][gid]
        check(len(raw) == len(mask) and {a["candidate_id"] for a in raw} == set(mask), gid + ": raw candidate coverage")
        for row in judgment["assessments"]:
            check(row["assessment"] in raw and mask[row["assessment"]["candidate_id"]] == row["job_id"], gid + ": raw judgment mapping")
    calibration = [read(p) for p in sorted((run / "calibration-results").glob("*.json"))]
    check(summary["calibration"] == calibration, "summary calibration copies")
    check({r["call_id"] for r in calibration} == categories["calibration"], "calibration coverage")
    for row in calibration:
        check(row["answer"] == raw_answers[row["call_id"]], row["call_id"] + ": raw calibration answer")
    logged = []
    if (run / "run.log").exists():
        for line in (run / "run.log").read_text().splitlines():
            try:
                row = json.loads(line)
                if "call" in row:
                    logged.append(row["call"])
                    check(row.get("tokens") == calls.get(row["call"], {}).get("usage", {}).get("total_tokens"), "logged tokens: " + row["call"])
            except ValueError:
                pass
        check(logged == [i for i in planned if i not in skipped], "run log order, omitted call or repeated attempt")
    else:
        warnings.append("run.log absent; raw/controller coverage still checked")
    catalog_files = sum(bool(r["catalog_timeout_lines"]) for r in diagnostics)
    other_files = sum(bool(r["other_lines"]) for r in diagnostics)
    if catalog_files:
        warnings.append("%d calls contain nonfatal catalog-timeout diagnostics; stderr is not clean" % catalog_files)
    if other_files:
        warnings.append("%d calls contain other stderr lines requiring review" % other_files)
    for name, before in fixed.items():
        check(sha(run / name) == before, "run changed during audit: " + name)
    return dict(status="FAIL" if issues else "PASS_WITH_DIAGNOSTICS" if warnings else "PASS",
                finished_run=True, run=str(run), new_model_calls=0, problems=issues, warnings=warnings,
                method="Independent raw turn.completed.usage recount; no runner/controller imports or fallback usage. Shared dependencies are deduplicated by physical call ID.",
                source_commit=plan["source_commit"], fixed_file_sha256=fixed,
                source_checks=source_checks, prepared_checks=prepared_checks,
                counts=dict(planned_slots=len(planned), actual_attempt_ids=len(attempted), raw_directories=len(directories),
                            result_records=len(records), raw_started_calls=len(started), unique_threads=len(set(threads)),
                            skipped_optionals=len(skipped), answers=len(answers), judgments=len(judgments),
                            calibration_calls=len(calibration), recorded_call_hash_checks=hash_checks,
                            raw_error_events=len(raw_errors), native_tool_events=len(tools), malformed_lines=len(malformed),
                            nonempty_stderr_files=sum(r["nonempty"] for r in diagnostics),
                            catalog_timeout_files=catalog_files, catalog_timeout_lines=sum(len(r["catalog_timeout_lines"]) for r in diagnostics),
                            other_stderr_files=other_files, duplicate_logged_call_ids=len(logged) - len(set(logged))),
                missing_result_ids=missing, orphan_ids=orphans, optional_skips=skipped,
                cli_requested_models=dict(model_counts), role_totals=role_totals,
                actual_whole_run_usage=total, disjoint_whole_run_partition=partition,
                standalone_arm_costs=arm_costs, answer_dependencies=dependency_rows,
                accounting="Actual totals include each shared generator once plus judges/calibration. Standalone arm costs overlap and MUST NOT be summed. A prior-turn answer is input lineage, not a second billed call.",
                controller_report=progress, calls=list(calls.values()), raw_event_types=dict(event_types),
                raw_item_types=dict(item_types), raw_errors=raw_errors, tool_events=tools, stderr_diagnostics=diagnostics,
                limits=["CLI model requests are verified, not the resolved provider model/version.",
                        "Input includes cached input; output includes reasoning. No invoice, USD price or allowance is inferred.",
                        "This checks record/accounting/dependency consistency, not independent semantic rescoring or judge accuracy.",
                        "No activity outside this run directory can be ruled out."])


def self_test():
    one = [{"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}}]
    raw, usage, errors, count = usage_from_terminal(one)
    assert not errors and count == 1 and usage["total_tokens"] == 12
    assert aggregate([usage, usage])["total_tokens"] == 24
    missing = usage_from_terminal([{"type": "turn.completed", "usage": {"input_tokens": 10}}])[1]
    assert aggregate([usage, missing])["total_tokens"] is None
    assert aggregate([usage, missing])["known_input_tokens"] == 20
    assert usage_from_terminal(one * 2)[2]
    assert usage_from_terminal([{"type": "turn.completed", "usage": {"input_tokens": True, "cached_input_tokens": 0, "output_tokens": 2}}])[2]
    assert usage_from_terminal([{"type": "turn.completed", "usage": {"input_tokens": 1, "cached_input_tokens": 2, "output_tokens": 2}}])[2]
    print(json.dumps({"self_test": "PASS", "new_model_calls": 0}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, help="New JSON path; no overwrite and no output file while incomplete")
    parser.add_argument("--self-test", action="store_true", help="Check accounting helpers without inspecting a run")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    run = args.run.resolve()
    notice = completion_notice(run)
    if notice:
        print(json.dumps(dict(notice, run=str(run), output_written=False, new_model_calls=0)))
        return 2
    result = audit(run)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps(dict(status=result["status"], problems=result["problems"], counts=result["counts"],
                              tokens=result["actual_whole_run_usage"]["total_tokens"],
                              output=str(args.output), output_sha256=sha(args.output))))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({"status": "AUDIT_ERROR", "error": str(error), "new_model_calls": 0}), file=sys.stderr)
        raise SystemExit(1)
