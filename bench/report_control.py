#!/usr/bin/env python3
"""Offline, zero-model reporting-controller prototype; Python 3.9 stdlib only.

This is a pure event reducer and a hand-authored trace experiment, not a deployed
monitor. It makes no network, subprocess, model, or notification calls.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals/context-quality/controller-cases.json"
OUTCOMES = ("completed", "abandoned", "timeout", "invalid", "provider_error")
SAFETY = ("viewing_day_warning", "law_caps_and_date", "courteous_agent_draft",
          "verify_before_paying", "licence_not_tenancy")
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")
CONTRACT = {
    "version": 1,
    "states": ["running", "paused"],
    "events": ["dispatch", "result", "provider_error", "judge_error", "usage", "resume"],
    "dispatch": "A proposal, accepted only for a planned session while running. Unique request IDs; agent retries require the latest agent attempt to have a provider error. Judge dispatch requires an ungraded completed agent result and binds to that result's request ID.",
    "terminal": "First terminal event per request wins. Late results for already dispatched pending requests are accepted during a pause. Results for undispatched requests are ignored. Judge errors do not overwrite agent outcomes or acquire a zero grade.",
    "pause": "The first accepted provider_error immediately pauses scheduling, including provider errors in judge requests. Only resume acknowledging the current pause event ID reopens dispatch. A new outage requires a new acknowledgment.",
    "duplicates": "Duplicate event IDs are ignored; conflicting payloads are flagged. Duplicate request dispatches are ignored and cannot add cost. Original events remain in the audit history, including rejected events.",
    "usage": "Usage fields are final per-request quantities, not deltas. Input includes cached input. The first known nonnegative integer value wins; late usage fills missing fields. A new field that would make cached input exceed total input is rejected and remains unknown. Known values from failed attempts count. Unknown fields remain unknown; total_tokens is null while any input/output field is unknown. Explicit zero is known zero.",
    "quality": "Only non-provider-error agent outcomes with a numeric grade contribute. A successful judge can supply the grade for its bound agent result. Null grades and failed judges do not become zero. Safety flags count once per graded session.",
    "report": "Fixed JSON schema, sorted retry session IDs, insertion-ordered accepted request IDs. Paused takes precedence over all other decisions; otherwise report_results requires all planned sessions observed and no pending requests. Empty plans report_results.",
    "scope": "Offline simulation of serial event handling only; no production integration, concurrency guarantees, real notification latency measurement, or model-quality measurement.",
}


def initial_state(sessions):
    if not isinstance(sessions, list) or any(not isinstance(s, str) or not s for s in sessions):
        raise ValueError("planned sessions must be nonempty string IDs")
    if len(sessions) != len(set(sessions)):
        raise ValueError("planned session IDs must be unique")
    return {"sessions": list(sessions), "paused": False, "first_provider_error": None,
            "pause_cause": None, "requests": {}, "seen_events": {}, "history": [],
            "blocked_dispatches": [], "ignored_events": []}


def _latest(state, session, stage):
    rows = [r for r in state["requests"].values()
            if r["session"] == session and r["stage"] == stage]
    return rows[-1] if rows else None


def _ignore(state, event, reason):
    state["ignored_events"].append({"event_id": event["id"], "reason": reason})


def _usage(state, event, request):
    usage = event.get("usage")
    if usage is None:
        return
    if not isinstance(usage, dict) or set(usage) - set(TOKEN_FIELDS):
        _ignore(state, event, "invalid_usage")
        return
    for field in TOKEN_FIELDS:
        value = usage.get(field)
        if value is None:
            continue
        if type(value) is not int or value < 0:
            _ignore(state, event, "invalid_usage_" + field)
        elif request["usage"][field] is None:
            cache, total_input = request["usage"]["cached_input_tokens"], request["usage"]["input_tokens"]
            if field == "input_tokens" and cache is not None and value < cache:
                _ignore(state, event, "input_tokens_below_cached_input")
            elif field == "cached_input_tokens" and total_input is not None and value > total_input:
                _ignore(state, event, "cached_input_exceeds_input_tokens")
            else:
                request["usage"][field] = value
        elif request["usage"][field] != value:
            _ignore(state, event, "conflicting_usage_" + field)


def _grade(value):
    return value is None or (type(value) in (int, float) and math.isfinite(value)
                             and 0 <= value <= 1)


def reduce_event(previous, event):
    """Return a fresh state. Every input event is preserved without mutation."""
    if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"]:
        raise ValueError("every event needs a nonempty string id")
    state = copy.deepcopy(previous)
    event = copy.deepcopy(event)
    state["history"].append(event)
    if event["id"] in state["seen_events"]:
        reason = "duplicate_event" if state["seen_events"][event["id"]] == event else "conflicting_event_id"
        _ignore(state, event, reason)
        return state
    state["seen_events"][event["id"]] = event
    kind = event.get("type")
    if kind == "resume":
        if not state["paused"] or event.get("acknowledge") != state["pause_cause"]:
            _ignore(state, event, "invalid_resume")
        else:
            state["paused"] = False
            state["pause_cause"] = None
        return state
    request_id = event.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        _ignore(state, event, "invalid_request_id")
        return state
    request = state["requests"].get(request_id)
    if kind == "dispatch":
        session, stage = event.get("session"), event.get("stage", "agent")
        if request is not None:
            reason = "duplicate_request" if (request["session"], request["stage"]) == (session, stage) else "conflicting_request_id"
            _ignore(state, event, reason)
            return state
        reason = None
        agent = _latest(state, session, "agent")
        judge = _latest(state, session, "judge")
        if state["paused"]:
            reason = "paused"
        elif session not in state["sessions"]:
            reason = "unplanned_session"
        elif stage not in ("agent", "judge"):
            reason = "invalid_stage"
        elif stage == "agent" and agent is not None and agent["terminal"] != "provider_error":
            reason = "agent_not_retryable"
        elif stage == "judge" and (agent is None or agent["terminal"] != "completed"
                                    or agent["grade"] is not None):
            reason = "judge_requires_ungraded_completion"
        elif stage == "judge" and judge is not None and judge["source_request_id"] == agent["id"] \
                and judge["terminal"] not in ("provider_error", "judge_error"):
            reason = "judge_not_retryable"
        if reason:
            state["blocked_dispatches"].append({"request_id": request_id, "reason": reason})
        else:
            state["requests"][request_id] = {
                "id": request_id, "session": session, "stage": stage, "terminal": None,
                "grade": None, "safety_failed": [], "capped_by": [],
                "source_request_id": agent["id"] if stage == "judge" else None,
                "usage": {field: None for field in TOKEN_FIELDS}}
        return state
    if request is None:
        _ignore(state, event, "undispatched_request")
        return state
    if kind == "usage":
        _usage(state, event, request)
        return state
    if kind not in ("result", "provider_error", "judge_error"):
        _ignore(state, event, "unknown_event_type")
        return state
    # A repeated terminal callback can still supply previously missing usage.
    _usage(state, event, request)
    if request["terminal"] is not None:
        _ignore(state, event, "already_terminal")
        return state
    if kind == "provider_error":
        request["terminal"] = kind
        if state["first_provider_error"] is None:
            state["first_provider_error"] = event["id"]
        if not state["paused"]:
            state["pause_cause"] = event["id"]
        state["paused"] = True
    elif kind == "judge_error":
        if request["stage"] != "judge":
            _ignore(state, event, "judge_error_on_agent")
        else:
            request["terminal"] = kind
    else:
        outcome = event.get("outcome", "completed")
        grade = event.get("grade")
        failed, capped = event.get("safety_failed", []), event.get("capped_by", [])
        if outcome not in OUTCOMES[:-1] or not _grade(grade) \
                or not isinstance(failed, list) or any(s not in SAFETY for s in failed) \
                or not isinstance(capped, list) or any(not isinstance(s, str) for s in capped) \
                or (request["stage"] == "judge" and outcome != "completed"):
            _ignore(state, event, "invalid_result")
        else:
            request.update(terminal=outcome, grade=grade, safety_failed=failed, capped_by=capped)
    return state


def report(state):
    requests = list(state["requests"].values())
    outcomes = {name: 0 for name in OUTCOMES}
    graded, retry_sessions, retry_judges = [], [], []
    for session in state["sessions"]:
        agent, judge = _latest(state, session, "agent"), _latest(state, session, "judge")
        if agent is None or agent["terminal"] is None:
            continue
        outcomes[agent["terminal"]] += 1
        if agent["terminal"] == "provider_error":
            retry_sessions.append(session)
            continue
        row = agent
        if judge is not None and judge["source_request_id"] == agent["id"]:
            if judge["terminal"] == "provider_error":
                retry_judges.append(session)
            elif judge["terminal"] == "completed":
                row = judge
        if row["grade"] is not None:
            graded.append(row)
    values = [row["grade"] for row in graded]
    usage = {}
    for field in TOKEN_FIELDS:
        usage["known_" + field] = sum(r["usage"][field] for r in requests if r["usage"][field] is not None)
        usage["unknown_" + field + "_requests"] = sum(r["usage"][field] is None for r in requests)
    usage["total_tokens"] = None if usage["unknown_input_tokens_requests"] or usage["unknown_output_tokens_requests"] \
        else usage["known_input_tokens"] + usage["known_output_tokens"]
    pending = sum(r["terminal"] is None for r in requests)
    observed = sum(outcomes.values())
    return {
        "planned_sessions": len(state["sessions"]), "observed_sessions": observed,
        "in_flight_requests": pending, "outcomes": outcomes, "graded_sessions": len(graded),
        "quality": {"mean_grade": round(float(statistics.mean(values)), 4) if values else None,
                    "median_grade": round(float(statistics.median(values)), 4) if values else None,
                    "safety_capped_sessions": sum(bool(r["capped_by"]) for r in graded) if values else None},
        "safety_misses": {name: sum(name in r["safety_failed"] for r in graded) if values else None for name in SAFETY},
        "provider_error_attempts": sum(r["terminal"] == "provider_error" for r in requests),
        "judge_error_attempts": sum(r["terminal"] == "judge_error" for r in requests),
        "provider_retry_sessions": sorted(retry_sessions), "provider_retry_judges": sorted(retry_judges),
        "usage": usage, "paused": state["paused"], "first_provider_error": state["first_provider_error"],
        "pause_cause": state["pause_cause"],
        "decision": "pause_provider" if state["paused"] else
                    ("report_results" if observed == len(state["sessions"]) and not pending else "wait"),
        "scheduled_requests": list(state["requests"]),
        "blocked_dispatches": copy.deepcopy(state["blocked_dispatches"]),
        "ignored_events": copy.deepcopy(state["ignored_events"]),
    }


def invariant_failures(previous, state, event):
    """Hard checks at every event boundary, separate from the authored oracle."""
    failures = []
    current = report(state)
    requests = state["requests"]
    if sum(current["outcomes"].values()) != current["observed_sessions"]:
        failures.append("outcomes do not partition observed sessions")
    if current["graded_sessions"] > current["observed_sessions"] - current["outcomes"]["provider_error"]:
        failures.append("provider failure acquired a grade")
    if previous["paused"] and event.get("type") == "dispatch" and set(requests) != set(previous["requests"]):
        failures.append("dispatch accepted while paused")
    if state["paused"] and current["decision"] != "pause_provider":
        failures.append("pause did not take precedence")
    if event.get("type") == "provider_error" and event.get("request_id") in requests:
        request = requests[event["request_id"]]
        old = previous["requests"].get(event["request_id"])
        if old is not None and old["terminal"] is None and request["terminal"] == "provider_error" and not state["paused"]:
            failures.append("first provider error did not immediately pause")
    if state["history"] != previous["history"] + [event]:
        failures.append("original events were lost or modified")
    for request in requests.values():
        usage = request["usage"]
        if usage["cached_input_tokens"] is not None and usage["input_tokens"] is not None \
                and usage["cached_input_tokens"] > usage["input_tokens"]:
            failures.append("cached input exceeded total input")
    for request_id in previous["requests"]:
        old, new = previous["requests"][request_id], requests[request_id]
        if old["terminal"] is not None and old["terminal"] != new["terminal"]:
            failures.append("terminal outcome changed")
        for field in TOKEN_FIELDS:
            if old["usage"][field] is not None and new["usage"][field] != old["usage"][field]:
                failures.append("known request usage changed or was counted twice")
    return failures


def _compare(actual, expected, path="report"):
    """Strict complete comparisons; bool is not an acceptable numeric count."""
    failures = []
    if type(actual) is not type(expected):
        return [path + ": type differs"]
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            failures.append(path + ": fields differ")
        for key in expected.keys() & actual.keys():
            failures += _compare(actual[key], expected[key], path + "." + key)
    elif actual != expected:
        failures.append(path + ": value differs (actual=%r, expected=%r)" % (actual, expected))
    return failures


def replay(case):
    original = copy.deepcopy(case)
    state = initial_state(case["sessions"])
    snapshots = [{"after_events": 0, "report": report(state)}]
    failures = []
    for index, event in enumerate(case["events"], 1):
        previous = state
        previous_copy = copy.deepcopy(previous)
        state = reduce_event(previous, event)
        failures += ["event %d: %s" % (index, f) for f in invariant_failures(previous, state, event)]
        if previous != previous_copy:
            failures.append("event %d mutated prior state" % index)
        snapshots.append({"after_events": index, "report": report(state)})
    failures += _compare(report(state), case["expected"])
    for checkpoint in case.get("checkpoints", []):
        actual = snapshots[checkpoint["after_events"]]["report"]
        for key, expected in checkpoint["expected"].items():
            failures += _compare(actual[key], expected, "checkpoint_%d.%s" % (checkpoint["after_events"], key))
    if case != original:
        failures.append("input case was mutated")
    return {"id": case["id"], "description": case["description"], "pass": not failures,
            "failures": failures, "original_events": state["history"], "snapshots": snapshots,
            "expected": case["expected"], "actual": report(state)}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cases_path, output):
    fixture = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = fixture["cases"]
    if fixture["contract_version"] != CONTRACT["version"]:
        raise ValueError("fixture contract version differs")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("duplicate case IDs")
    if any(not case["id"] or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in case["id"]) for case in cases):
        raise ValueError("unsafe case ID")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "contract.json", CONTRACT)
    write_json(output / "cases.json", fixture)
    results = []
    for case in cases:
        result = replay(case)
        path = output / "traces" / (case["id"] + ".json")
        write_json(path, result)
        results.append({"id": case["id"], "pass": result["pass"], "failures": result["failures"],
                        "event_count": len(case["events"]), "artifact": str(path.relative_to(output)),
                        "sha256": digest(path)})
    manifest = {"experiment": "zero-model-report-control", "contract_version": CONTRACT["version"],
                "cases": len(cases), "passed": sum(r["pass"] for r in results),
                "events": sum(r["event_count"] for r in results),
                "benchmark_model_calls": 0, "deployments": 0, "network_calls": 0,
                "oracle": fixture["oracle"], "scope": CONTRACT["scope"],
                "source_sha256": {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                                  "cases": digest(cases_path),
                                  "tests/test_report_control.py": digest(ROOT / "tests/test_report_control.py")},
                "artifacts": {name: digest(output / name) for name in ("contract.json", "cases.json")},
                "results": results}
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--output", type=Path, required=True, help="new directory; never overwrite an experiment")
    args = parser.parse_args()
    manifest = run(args.cases, args.output)
    print(json.dumps({"cases": manifest["cases"], "passed": manifest["passed"],
                      "events": manifest["events"], "benchmark_model_calls": 0,
                      "artifact": str(args.output / "manifest.json")}))
    return 0 if manifest["passed"] == manifest["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
