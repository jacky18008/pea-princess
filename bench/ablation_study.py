#!/usr/bin/env python3
"""Preregistered Codex-only ablations. prepare/summarize are offline; run is live."""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import re
import subprocess
import time

import context_quality as q
from call_control import CallControl

ROOT = q.ROOT
OLD = ROOT / "bench/results/context-quality-2026-09-08/live-v1"
RENTAL_ARMS = ("full", "prose", "state", "state_no_sources", "state_no_updates", "state_neither")
RETRIEVAL_ARMS = ("raw_full", "full", "summary", "lexical", "adaptive", "oracle")
CALIBRATION = ("A1", "A2", "R3", "R5")
LIMIT = 4200000
MAX_CALLS = 158
REPEATS = 2
SOURCES = (
    "bench/ablation_study.py", "bench/call_control.py", "bench/report_control.py",
    "bench/context_quality.py", "bench/launch.py",
    "evals/ablation-2026-09-09/rental-cases.json",
    "evals/ablation-2026-09-09/retrieval-cases.json",
    "docs/ablation-2026-09-09/protocol.md", "dist/prompt-pack/INSTRUCTIONS.md",
)
MEMORY_SCHEMA = q.obj({
    "summary": q.STRING,
    "facts": q.array(q.obj({
        "id": q.STRING, "key": q.STRING, "value": q.STRING,
        "qualification": {"type": "string", "enum": ["reported", "estimated", "confirmed_in_source", "unknown"]},
        "source_id": q.STRING, "quote": q.STRING,
        "status": {"type": "string", "enum": ["current", "superseded", "uncertain"]},
        "supersedes": q.array(q.STRING),
    }), maxItems=48),
})
MEMORY_RULES = """Create a compact handoff from the supplied fictional user-source messages.
Do not answer a future question or recommend a final property. Produce BOTH a neutral
narrative summary (aim <=200 English words) and structured facts (at most48).
Preserve decision-relevant numbers, exact identities, requirements vs property values,
uncertainty, fallback booking status, and corrections. Use a stable entity-qualified
key, a concise scalar value, and qualification for each fact. Cite the source message
ID and an EXACT excerpt >=8 characters. Never treat prior assistant output as evidence.
Keep superseded values as separate fact rows; mark status and point supersedes to the
old fact ID from the replacing fact. Stable keys must not encode old/new/current status;
that belongs in status and supersedes. Do not embed recency labels in scalar values.
For an update, use only prior memory and new user-source messages. Retain existing IDs,
source IDs and exact quotes for still-relevant old facts. Do not reconstruct forgotten
facts or invent source text. Missing knowledge remains unknown. Narrative and facts
should cover the same relevant known information. No tools or external facts.
"""
VISIBILITY_RULES = """
Every candidate includes ACTUAL available_evidence. This is different from the full
reference packet YOU can read. An answer truthfully saying it was not given a document
must not be labelled a contradiction merely because that document is in YOUR packet.
Use full reference truth to score missing required findings; use actual available
evidence to judge honesty about access and support. A model-made summary/state is not
independent verification and can itself contain errors. Check numeric requirements
separately from property measurements; check that a claimed source actually says it.
Distinguish unsupported material facts, exact-quote defects, missing findings and
reasonable conditional wording. Do not require every historical profile field to be
recited when the decision demonstrably applies the relevant current constraints.
Look for both false approval and unjustified refusal. Correctly supported narrow
approval should not be penalized merely for being affirmative. The structured facts
field does not excuse contradictory prose. All new-case criteria are applicable.
"""


def jtext(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def rotate(items, seed):
    result = list(items)
    random.Random(seed).shuffle(result)
    return result


def rental_id(case, repeat, turn, arm):
    return "%s-r%d-%s-%s" % (case, repeat, turn, arm)


def length_order(case_id):
    return ("long", "short") if case_id == "E2" else ("short", "long")


def schedule(rental, retrieval):
    calls, groups = [], []
    for index, case in enumerate(CALIBRATION):
        for mode in (("legacy", "visible") if index % 2 == 0 else ("visible", "legacy")):
            calls.append("cal-%s-%s" % (case, mode))
    for case in rental["cases"]:
        for repeat in range(1, REPEATS + 1):
            for turn in case["turns"]:
                group = rental_id(case["id"], repeat, turn["id"], "group")
                jobs = [rental_id(case["id"], repeat, turn["id"], a) for a in rotate(RENTAL_ARMS, group)]
                calls += [group + "-memory"] + jobs + [group + "-judge"]
                groups.append({"id": group, "experiment": "rental", "case_id": case["id"],
                               "repeat": repeat, "turn": turn["id"], "jobs": jobs})
    for case in retrieval["cases"]:
        for length in length_order(case["id"]):
            group = case["id"] + "-" + length
            jobs = [group + "-" + a for a in rotate(RETRIEVAL_ARMS, group)]
            calls.append(group + "-summary-generation")
            for job in jobs:
                calls.append(job)
                if job.endswith("-adaptive"):
                    calls.append(job + "-retrieved")
            calls.append(group + "-judge")
            groups.append({"id": group, "experiment": "retrieval", "case_id": case["id"],
                           "length": length, "jobs": jobs})
    if len(calls) != MAX_CALLS or len(calls) != len(set(calls)):
        raise ValueError("unexpected call matrix")
    return calls, groups


def prepare(output):
    if output.exists():
        raise ValueError("refuse to overwrite an existing run")
    rental = q.read(ROOT / SOURCES[5])
    retrieval = q.read(ROOT / SOURCES[6])
    assert len(rental["cases"]) == len(retrieval["cases"]) == 3
    assert all(len(c["turns"]) == 2 for c in rental["cases"])
    calls, groups = schedule(rental, retrieval)
    output.mkdir(parents=True)
    q.write(output / "rental-cases.json", rental)
    q.write(output / "retrieval-cases.json", retrieval)
    (output / "target-instructions.md").write_bytes((ROOT / SOURCES[-1]).read_bytes())
    old_plan = q.read(OLD / "plan.json")
    for case_id in CALIBRATION:
        packet = q.read(OLD / "review-packets" / (case_id + ".json"))
        candidates = {}
        for label, old_job in old_plan["judge_masks"][case_id].items():
            answer = q.read(OLD / "answers" / (old_job + ".json"))
            final = dict(answer["final_answer"])
            final.pop("request_documents", None)
            if case_id.startswith("A"):
                evidence = {"summary": packet["case"]["summary"], "documents": [d for d in packet["case"]["documents"] if d["id"] in answer["supplied_document_ids"]]}
            else:
                evidence = {"history": packet["case"]["history"]} if answer["arm"] == "full" else {"memory": packet["case"]["handoff"]}
                evidence["latest_user_question"] = packet["case"]["question"]
            candidates[label] = {"response": final, "available_evidence": evidence}
        q.write(output / "calibration" / (case_id + ".json"), {"case": packet["case"], "candidates": candidates})
    prepared = {str(p.relative_to(output)): q.digest(p) for p in output.rglob("*") if p.is_file()}
    plan = {
        "version": 1, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip(),
        "source_sha256": {p: q.digest(ROOT / p) for p in SOURCES}, "prepared_sha256": prepared,
        "answer_model": q.ANSWER_MODEL, "judge_model": q.JUDGE_MODEL, "effort": q.EFFORT,
        "maximum_cli_calls": MAX_CALLS, "reported_token_stop_threshold": LIMIT,
        "timeout_seconds_per_call": 240, "planned_call_ids": calls, "groups": groups,
        "rental_arms": list(RENTAL_ARMS), "retrieval_arms": list(RETRIEVAL_ARMS),
        "judge_masks": {g["id"]: {"candidate_%d" % (i + 1): job for i, job in enumerate(rotate(g["jobs"], "judge-" + g["id"]))} for g in groups},
        "scope": "Authored finite mechanism ablations; two rental replicates, one retrieval replicate per length. No human ground truth, population equivalence or deployment claim.",
        "calibration_scope": "Selected known-error development regressions, not held-out grading validation. Legacy/visible differ in evidence visibility and explicit grading rules, a bundled grader change.",
    }
    q.write(output / "plan.json", plan)
    return {"prepared": str(output), "maximum_calls": len(calls), "answer_groups": len(groups), "live_calls": 0}


def memory_view(memory, arm):
    if arm == "prose":
        return memory["summary"]
    facts = copy.deepcopy(memory["facts"])
    for fact in facts:
        if arm in ("state_no_sources", "state_neither"):
            fact.pop("source_id", None)
            fact.pop("quote", None)
        if arm in ("state_no_updates", "state_neither"):
            fact.pop("status", None)
            fact.pop("supersedes", None)
    return {"facts": facts}


def memory_check(memory, messages):
    sources = {m["id"]: m["text"] for m in messages if m["role"] == "user"}
    ids = [f["id"] for f in memory["facts"]]
    rows = []
    for fact in memory["facts"]:
        quote = fact["quote"]
        rows.append({"id": fact["id"], "source_id": fact["source_id"],
                     "exact_user_source_quote": len(quote.strip()) >= 8 and " ".join(quote.split()) in " ".join(sources.get(fact["source_id"], "").split()),
                     "valid_supersedes_ids": all(x in ids and x != fact["id"] for x in fact["supersedes"])})
    return {"facts": rows, "duplicate_fact_ids": len(ids) - len(set(ids)),
            "invalid_quotes": sum(not r["exact_user_source_quote"] for r in rows),
            "invalid_supersedes": sum(not r["valid_supersedes_ids"] for r in rows),
            "scope": "Membership and reference integrity only, not complete semantic truth or recall."}


def fact_schema(fact_checks):
    return q.array(q.obj({"key": {"type": "string", "enum": [f["key"] for f in fact_checks]},
                          "value": q.STRING, "source_ids": q.array(q.STRING)}),
                   minItems=len(fact_checks), maxItems=len(fact_checks))


def answer_schema(case, analysis=False):
    schema = copy.deepcopy(q.ANALYSIS_SCHEMA if analysis else q.RENTAL_SCHEMA)
    schema["properties"]["facts"] = fact_schema(case["fact_checks"])
    schema["required"].append("facts")
    return schema


def normalize_scalar(value):
    value = str(value).strip().casefold().replace(",", "").replace("£", "")
    value = re.sub(r"(?<=\d)t(?=\d{2}:\d{2})", " ", value)
    value = re.sub(r"\s+", " ", value)
    numeric = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(?:m²|m2|cm|minutes?|mins?|gbp|%)?", value)
    return str(float(numeric.group(1))) if numeric else value


def check_facts(answer, expected):
    rows = answer.get("facts", [])
    keys = [r.get("key") for r in rows]
    checks = []
    for fact in expected:
        got = [r for r in rows if r.get("key") == fact["key"]]
        accepted = [fact["expected_value"]] + fact.get("accepted_values", [])
        checks.append({"key": fact["key"], "expected": fact["expected_value"],
                       "got": got[0]["value"] if len(got) == 1 else None,
                       "pass": len(got) == 1 and normalize_scalar(got[0]["value"]) in {normalize_scalar(x) for x in accepted},
                       "reference_source_ids": fact["source_ids"]})
    return {"checks": checks, "passed": sum(r["pass"] for r in checks), "total": len(checks),
            "duplicate_or_unknown_keys": len(keys) != len(set(keys)) or set(keys) != {f["key"] for f in expected},
            "scope": "Exact normalized output scalar fields; correct fields do not excuse contradictory natural-language answers."}


def fact_instructions(case):
    return ("\nAlso fill one fact row for each key below. Use concise scalar values, plain numbers without currency/unit formatting for numeric keys, ISO dates when known, and 'unknown' for unavailable facts. "
            "Do not invent missing values. Cite actually available source IDs (or 'memory'/'summary' for those views). "
            "The prose answer and fact rows must agree. Required keys only (no expected values supplied):\n" + jtext([f["key"] for f in case["fact_checks"]]))


def lexical_select(question, documents):
    # Frozen TF-IDF-style lexical ranker; no gold, embeddings or model invocation.
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "is", "for", "with", "this", "that", "it", "on", "be", "as", "are", "from", "by", "what", "which", "should", "can", "we"}
    terms = lambda s: [x for x in re.findall(r"[a-z0-9]+", s.casefold()) if x not in stop]
    query = set(terms(question))
    bags = [Counter(terms(d["title"] + " " + d["text"])) for d in documents]
    scores = []
    for doc, bag in zip(documents, bags):
        score = sum((1 + math.log(bag[t])) * math.log(1 + len(documents) / (1 + sum(t in b for b in bags))) for t in query if bag[t])
        scores.append({"document_id": doc["id"], "score": score})
    scores.sort(key=lambda r: (-r["score"], r["document_id"]))
    return [r["document_id"] for r in scores[:2]], scores


def rental_packet(case, turn_index, arm, memory, previous):
    turn = case["turns"][turn_index]
    packet = {"latest_user_question": {"id": turn["id"], "text": turn["text"]}}
    if arm == "full":
        history = copy.deepcopy(case["history"])
        if turn_index:
            history.append({"id": case["turns"][0]["id"], "role": "user", "text": case["turns"][0]["text"]})
        packet["history"] = history
    else:
        packet["memory"] = memory_view(memory, arm)
    if previous:
        packet["your_previous_answer"] = previous
        packet["previous_answer_is_source_evidence"] = False
    return packet


def make_judge_prompt(case, candidates, visible=True):
    if not visible:
        candidates = {k: v["response"] for k, v in candidates.items()}
    return q.JUDGE_RULES + (VISIBILITY_RULES if visible else "") + "\n" + jtext({"source_case_and_frozen_rubric": case, "candidates": candidates})


class Study:
    def __init__(self, output):
        self.output = output
        self.plan = q.read(output / "plan.json")
        self.control = CallControl(output / "control", self.plan["planned_call_ids"])

    def call(self, call_id, prompt, schema, purpose, job_id=None, phase=None):
        model = self.plan["judge_model"] if purpose in ("judge", "calibration") else self.plan["answer_model"]
        # Always verify existing raw calls as well as the controller's durable record.
        existing = self.output / "calls" / call_id / "result.json"
        if existing.exists():
            record = q.invoke(self.output, call_id, prompt, schema, model, purpose, self.plan)
            return self.control.run(call_id, job_id or call_id, purpose, phase or purpose, lambda: record)
        def invoke():
            try:
                return q.invoke(self.output, call_id, prompt, schema, model, purpose, self.plan)
            except ValueError:
                if existing.exists():
                    return q.read(existing)
                raise
        return self.control.run(call_id, job_id or call_id, purpose, phase or purpose, invoke)

    def judge(self, group, case, answers):
        mask = self.plan["judge_masks"][group["id"]]
        by_id = {a["id"]: a for a in answers}
        candidates = {label: {"response": by_id[job]["final_answer"], "available_evidence": by_id[job]["available_evidence"]} for label, job in mask.items()}
        prompt = make_judge_prompt(case, candidates)
        q.write(self.output / "review-packets" / (group["id"] + ".json"), {"case": case, "candidates": candidates})
        record = self.call(group["id"] + "-judge", prompt, q.judge_schema(case, list(mask)), "judge", group["id"])
        assessments = q.validate_assessments(record["answer"], case, mask)
        critical = {f["id"] for f in case["gold"]["required_findings"] if f["severity"] == "critical"}
        rows = [{"job_id": mask[a["candidate_id"]], "assessment": a,
                 "required_met": sum(c["met"] and c["applicable"] for c in a["criteria"]),
                 "required_total": sum(c["applicable"] for c in a["criteria"]),
                 "critical_missed": [c["id"] for c in a["criteria"] if c["id"] in critical and not c["met"]]} for a in assessments]
        q.write(self.output / "judgments" / (group["id"] + ".json"), {"group": group, "judge_call": record["id"], "assessments": rows})

    def calibration(self):
        for index, case_id in enumerate(CALIBRATION):
            packet = q.read(self.output / "calibration" / (case_id + ".json"))
            for mode in (("legacy", "visible") if index % 2 == 0 else ("visible", "legacy")):
                record = self.call("cal-%s-%s" % (case_id, mode), make_judge_prompt(packet["case"], packet["candidates"], mode == "visible"), q.judge_schema(packet["case"], list(packet["candidates"])), "calibration")
                q.validate_assessments(record["answer"], packet["case"], packet["candidates"])
                q.write(self.output / "calibration-results" / (case_id + "-" + mode + ".json"), {"case_id": case_id, "mode": mode, "call_id": record["id"], "answer": record["answer"]})

    def rental(self):
        cases = q.read(self.output / "rental-cases.json")["cases"]
        for case in cases:
            for repeat in range(1, REPEATS + 1):
                memory, previous, memory_calls = None, {}, []
                for index, turn in enumerate(case["turns"]):
                    group = next(g for g in self.plan["groups"] if g["experiment"] == "rental" and g["case_id"] == case["id"] and g["repeat"] == repeat and g["turn"] == turn["id"])
                    source_messages = [m for m in case["history"] if m["role"] == "user"]
                    if index:
                        new_message = {"id": case["turns"][0]["id"], "role": "user", "text": case["turns"][0]["text"]}
                        source_messages.append(new_message)
                        memory_input = {"prior_memory": memory, "new_user_source_messages": [new_message]}
                    else:
                        memory_input = {"user_source_messages": source_messages}
                    made = self.call(group["id"] + "-memory", q.BOUNDARY + MEMORY_RULES + "\n" + jtext(memory_input), MEMORY_SCHEMA, "memory", group["id"], "initial" if not index else "update")
                    memory = made["answer"]
                    memory_calls.append(made["id"])
                    q.write(self.output / "memories" / (group["id"] + ".json"), {"call_id": made["id"], "input_dependency_call_ids": memory_calls[-2:-1], "memory": memory, "checks": memory_check(memory, source_messages)})
                    answers = []
                    for job in group["jobs"]:
                        # IDs use the common case/repeat/turn prefix followed by arm.
                        arm = job.split("-", 3)[3]
                        packet = rental_packet(case, index, arm, memory, previous.get(arm))
                        prompt = (q.BOUNDARY + q.RENTAL_RULES + fact_instructions(turn) + "\n<fixed_target_guidance>\n" + (self.output / "target-instructions.md").read_text() + "\n</fixed_target_guidance>\n" + jtext(packet))
                        record = self.call(job, prompt, answer_schema(turn), "answer", job)
                        result = {"id": job, "experiment": "rental", "case_id": case["id"], "repeat": repeat, "turn": turn["id"], "arm": arm,
                                  "call_ids": [record["id"]], "dependency_call_ids": [] if arm == "full" else list(memory_calls),
                                  "input_dependency_call_ids": ([] if arm == "full" else list(memory_calls)) + ([rental_id(case["id"], repeat, case["turns"][0]["id"], arm)] if index else []),
                                  "final_answer": record["answer"], "available_evidence": packet,
                                  "fact_check": check_facts(record["answer"], turn["fact_checks"]), "citation_check": None,
                                  "protocol_violation": None if record["answer"].get("answer", "").strip() else "empty answer"}
                        q.write(self.output / "answers" / (job + ".json"), result)
                        previous[arm] = record["answer"]
                        answers.append(result)
                    reference = {"id": group["id"], "history": copy.deepcopy(case["history"]), "question": turn["text"], "gold": turn["gold"], "fact_checks": turn["fact_checks"]}
                    if index:
                        reference["history"].append({"id": case["turns"][0]["id"], "role": "user", "text": case["turns"][0]["text"]})
                    reference["latest_user_source_id"] = turn["id"]
                    self.judge(group, reference, answers)

    def retrieval(self):
        for case in q.read(self.output / "retrieval-cases.json")["cases"]:
            for length in length_order(case["id"]):
                group = next(g for g in self.plan["groups"] if g["experiment"] == "retrieval" and g["case_id"] == case["id"] and g["length"] == length)
                documents = case["variants"][length]["documents"]
                made = self.call(group["id"] + "-summary-generation", q.BOUNDARY + "Create a neutral factual overview of this fictional source packet in <=180 English words. Preserve important uncertainty and conflicts. Do not recommend an approval/rejection or answer an unasked question. Do not invent facts.\n" + jtext({"documents": documents}), q.obj({"summary": q.STRING}), "summary_generation", group["id"])
                source_case = {"id": case["id"], "question": case["question"], "summary": made["answer"]["summary"], "documents": documents, "gold": case["gold"], "fact_checks": case["fact_checks"]}
                chosen, ranking = lexical_select(case["question"], documents)
                answers = []
                for job in group["jobs"]:
                    arm = job.split("-", 2)[2]
                    supplied = [d["id"] for d in documents] if arm in ("full", "raw_full") else chosen if arm == "lexical" else case["oracle_document_ids"] if arm == "oracle" else []
                    mapped_arm = "adaptive" if arm == "adaptive" else "full" if arm in ("full", "raw_full") else "summary"
                    selected = supplied if arm in ("lexical", "oracle") else None
                    input_case = dict(source_case, summary="") if arm == "raw_full" else source_case
                    prompt = q.analysis_prompt(input_case, mapped_arm, selected=selected) + fact_instructions(case)
                    first = self.call(job, prompt, answer_schema(case, True), "answer", job, "selection_or_answer" if arm == "adaptive" else "answer")
                    records = [first]
                    violation = q.validate_request(source_case, mapped_arm, first["answer"])
                    requested = first["answer"].get("request_documents", [])
                    if arm == "adaptive" and requested and not violation:
                        supplied = requested
                        followup = q.analysis_prompt(source_case, "adaptive", supplied, first["answer"]) + fact_instructions(case)
                        records.append(self.call(job + "-retrieved", followup, answer_schema(case, True), "retrieval_answer", job, "retrieved"))
                        violation = q.validate_request(source_case, "adaptive", records[-1]["answer"], final=True)
                    elif arm == "adaptive":
                        self.control.skip(job + "-retrieved", "No valid retrieval request; no follow-up authorized by frozen protocol.")
                    final = records[-1]["answer"]
                    result = {"id": job, "experiment": "retrieval", "case_id": case["id"], "length": length, "arm": arm,
                              "call_ids": [r["id"] for r in records], "dependency_call_ids": [] if arm == "raw_full" else [made["id"]],
                              "input_dependency_call_ids": ([] if arm == "raw_full" else [made["id"]]) + ([first["id"]] if len(records) > 1 else []), "final_answer": final,
                              "available_evidence": {"summary": input_case["summary"], "document_catalog": [{"id": d["id"], "title": d["title"]} for d in documents], "documents": [d for d in documents if d["id"] in supplied]},
                              "supplied_document_ids": supplied, "requested_document_ids": requested, "oracle_document_ids": case["oracle_document_ids"],
                              "lexical_ranking": ranking if arm == "lexical" else None,
                              "fact_check": check_facts(final, case["fact_checks"]), "citation_check": q.citation_check(input_case, final, supplied), "protocol_violation": violation}
                    q.write(self.output / "answers" / (job + ".json"), result)
                    answers.append(result)
                self.judge(group, source_case, answers)


def summarize(output):
    plan = q.read(output / "plan.json")
    calls = q.all_calls(output)
    by_call = {c["id"]: c for c in calls}
    controller = None
    if (output / "control/checkpoint.json").exists():
        controller = CallControl(output / "control", plan["planned_call_ids"]).report()
    raw_dirs = {p.name for p in (output / "calls").glob("*") if p.is_dir()}
    attempted = raw_dirs | set(by_call) | {c["call_id"] for c in (controller or {}).get("calls", [])}
    missing_result = sorted(attempted - set(by_call))
    unknown_usage = sorted(set(missing_result) | {c["id"] for c in calls if c.get("usage") is None})
    answers = [q.read(p) for p in sorted((output / "answers").glob("*.json"))]
    judgments = [q.read(p) for p in sorted((output / "judgments").glob("*.json"))]
    judged = {a["job_id"]: a for j in judgments for a in j["assessments"]}
    arms = {}
    for experiment, names in (("rental", RENTAL_ARMS), ("retrieval", RETRIEVAL_ARMS)):
        for arm in names:
            rows = [a for a in answers if a["experiment"] == experiment and a["arm"] == arm]
            direct = {c for a in rows for c in a["call_ids"]}
            dependencies = {c for a in rows for c in a["dependency_call_ids"]}
            total = lambda ids: (sum(by_call[i]["usage"]["total_tokens"] for i in ids)
                                 if all(i in by_call and by_call[i].get("usage") is not None for i in ids) else None)
            grades = [judged[a["id"]] for a in rows if a["id"] in judged]
            arms[experiment + "/" + arm] = {
                "answers": len(rows), "answer_calls": len(direct), "dependency_calls": len(dependencies),
                "answer_tokens": total(direct), "dependency_tokens": total(dependencies), "standalone_pipeline_tokens": total(direct | dependencies),
                "required_met": sum(g["required_met"] for g in grades), "required_total": sum(g["required_total"] for g in grades),
                "critical_misses": sum(len(g["critical_missed"]) for g in grades),
                "scalar_passed": sum(a["fact_check"]["passed"] for a in rows), "scalar_total": sum(a["fact_check"]["total"] for a in rows),
                "unsupported_annotations": sum(len(g["assessment"]["unsupported_claims"]) for g in grades),
                "contradiction_annotations": sum(len(g["assessment"]["contradictions"]) for g in grades),
                "invalid_quotes": sum((a["citation_check"] or {}).get("invalid", 0) for a in rows),
                "protocol_violations": sum(bool(a["protocol_violation"]) for a in rows),
            }
    purposes = defaultdict(lambda: {"calls": 0, "known_tokens": 0})
    for c in calls:
        purposes[c["purpose"]]["calls"] += 1
        purposes[c["purpose"]]["known_tokens"] += (c.get("usage") or {}).get("total_tokens", 0)
    calibration = [q.read(p) for p in sorted((output / "calibration-results").glob("*.json"))]
    complete = (len(answers) == 108 and len(judgments) == 18 and len(calibration) == 8
                and not unknown_usage and all(c["status"] == "complete" for c in calls)
                and controller is not None and controller["plan_complete"] and not controller["paused"])
    result = {"complete": complete,
              "source_commit": plan["source_commit"], "plan_sha256": q.digest(output / "plan.json"), "calls": len(attempted),
              "recorded_call_results": len(calls), "missing_result_call_ids": missing_result, "unknown_usage_call_ids": unknown_usage,
              "controller": controller,
              "known_cli_processed_tokens": sum((c.get("usage") or {}).get("total_tokens", 0) for c in calls),
              "cli_processed_tokens": None if unknown_usage else sum(c["usage"]["total_tokens"] for c in calls),
              "usage_coverage_complete": not unknown_usage, "claude_calls": 0,
              "purpose_totals": dict(purposes), "arms": arms, "answers": answers, "judgments": judgments, "calibration": calibration,
              "accounting": "Actual workload counts each shared generation once. Standalone arm pipelines count each dependency once per case/replicate, including initial and update; arm totals overlap and MUST NOT be summed. Judge/calibration cost included in whole-run actual total and shown separately. Joint prose+state generator is charged in full to either standalone arm; not optimized pure-prose production cost.",
              "limitations": ["Synthetic mechanism study, not statistical equivalence; repeated rental samples share cases and are not independent users.", "Shared source-only memory generation/update, with each arm's prior answer separately retained. Does not measure full assistant-history compaction.", "Oracle has preregistered gold document IDs and is a diagnostic bound, not a deployable retriever.", "Two document lengths and one sample per retrieval cell cannot establish a general crossover curve.", "Calibration uses known errors and a bundled prompt+visibility change, not held-out judge accuracy or a visibility-only causal estimate.", "CLI costs exclude parent/subagent authoring, reviews and documentation; processed tokens are not billing/quota."]}
    q.write(output / "summary.json", result)
    return result


def run(output):
    plan = q.read(output / "plan.json")
    for p, checksum in plan["source_sha256"].items():
        if q.digest(ROOT / p) != checksum:
            raise ValueError("frozen source changed: " + p)
    for p, checksum in plan["prepared_sha256"].items():
        if q.digest(output / p) != checksum:
            raise ValueError("prepared source changed: " + p)
    study = Study(output)
    try:
        study.calibration()
        study.rental()
        study.retrieval()
    finally:
        summary = summarize(output)
    return {"complete": summary["complete"], "calls": summary["calls"], "known_tokens": summary["known_cli_processed_tokens"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "summarize"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"prepare": prepare, "run": run, "summarize": summarize}[args.command](args.output.resolve())
    print(jtext(result) if args.command != "summarize" else jtext({k: result[k] for k in ("complete", "calls", "known_cli_processed_tokens")}))


if __name__ == "__main__":
    main()
