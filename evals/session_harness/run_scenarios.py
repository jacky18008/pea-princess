#!/usr/bin/env python3
"""Offline synthetic continuity experiment; no model, subprocess or network calls.

The full-history oracle is an explicit fixture of semantic facts. The lossy
baseline keeps only the most recent N fact records, without model summarization.
Neither its errors nor character counts estimate provider compaction quality,
real tokens, monetary savings, or model-answer quality.

The default report directory is a fresh temporary directory. Use --output-dir
explicitly to publish the JSON and Markdown artifacts to a reviewed location.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/vet-flat/scripts"))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def facts_from_history(records, last=None):
    """Read hand-authored fact deltas, independently of the engine event reducer."""
    facts = {}
    for record in records if last is None else records[-last:]:
        facts.update(copy.deepcopy(record["facts"]))
    return facts


def differences(expected, actual):
    """Missing is different from explicit null; report every expected semantic fact."""
    return [{"fact": key, "expected": value,
             "actual": actual.get(key), "missing": key not in actual}
            for key, value in sorted(expected.items())
            if key not in actual or actual[key] != value]


def _read_fixture():
    return json.loads((Path(__file__).with_name("lifecycle.json")).read_text(encoding="utf-8"))


def apply_current(store, event):
    return store.apply(event, expected_revision=store.show()["revision"])


def provenance(record, actor="user"):
    return {"actor": actor, "authorized": actor == "user", "source_id": record["id"],
            "quote": record.get("text", "Synthetic offline lifecycle fixture.")}


def apply_record(store, record, fixture):
    """Thin API translation only; expected facts never enter the state engine."""
    action = record["action"]
    if action == "budget":
        event = {"op": "budget.set", "id": record["budget_id"],
                 **{k: record[k] for k in ("scope", "limit", "unit")},
                 "provenance": provenance(record)}
    elif action == "requirement":
        event = {"op": "requirement.add", "id": record["requirement_id"],
                 "value": record["text"], "strength": record["strength"],
                 "scope": record["scope"], "provenance": provenance(record)}
    elif action == "retire":
        event = {"op": "requirement.retire", "id": record["requirement_id"],
                 "provenance": provenance(record)}
    elif action == "conditional":
        apply_current(store, {"op": "requirement.update", "id": record["requirement_id"],
                             "changes": {"value": record["text"], "strength": "conditional",
                                         "scope": record["scope"], "predicate": record["predicate"]},
                             "provenance": provenance(record)})
        event = {"op": "requirement.add", "id": "floor-elsewhere", "strength": "prohibit",
                 "scope": "all-other-properties",
                 "value": "Do not accept ground-floor apartments other than property-demo.",
                 "provenance": provenance(record)}
    elif action == "task":
        event = {"op": "task.add", "id": record["task_id"],
                 **{k: record[k] for k in ("kind", "title", "depends_on", "requirement_ids", "budget_ids")},
                 "acceptance": ["Retain every active requirement and current source provenance."]}
    elif action == "task_status":
        event = {"op": "task.update", "id": record["task_id"],
                 "changes": {"status": record["status"]}}
    elif action == "document":
        document_id = record["document_id"]
        text = fixture["documents"][document_id]
        (store.project_root / (document_id + ".txt")).write_text(text, encoding="utf-8")
        event = {"op": "document.add", "id": document_id, "path": document_id + ".txt",
                 "line_ranges": [[1, len(text.splitlines())]],
                 "provenance": {"actor": "external", "source_id": record["source_id"],
                                "quote": text.splitlines()[0]}}
        if record.get("supersedes"):
            event["supersedes"] = record["supersedes"]
    elif action == "capture":
        event = {"op": "request.capture", "id": record["request_id"],
                 "text": record["text"], "source": "synthetic-user-message"}
    elif action == "resolve":
        event = {"op": "request.resolve", "id": record["request_id"],
                 "resolution": "no_change", "note": record["text"]}
    else:
        raise ValueError("unknown fixture action: " + action)
    return apply_current(store, event)


def project_facts(state):
    result = {}
    for identifier, row in state["budgets"].items():
        for field in ("limit", "scope", "unit"):
            result["budgets.%s.%s" % (identifier, field)] = row[field]
    for identifier, row in state["requirements"].items():
        for field in ("status", "strength", "scope", "predicate"):
            if field in row:
                result["requirements.%s.%s" % (identifier, field)] = row[field]
        result["requirements.%s.text" % identifier] = row["value"]
    result["requirements.active_ids"] = sorted(i for i, r in state["requirements"].items()
                                                if r["status"] == "active")
    for identifier, row in state["tasks"].items():
        for field in ("kind", "status"):
            result["tasks.%s.%s" % (identifier, field)] = row[field]
    result["documents.current_ids"] = sorted(i for i, r in state["documents"].items()
                                              if r["status"] == "active")
    result["requests.pending_ids"] = sorted(i for i, r in state["requests"].items()
                                             if r["status"] == "pending")
    for identifier, row in state["requests"].items():
        result["requests.%s.text" % identifier] = row["text"]
    return result


def _dispatch(store, identifier="physical-1", task="review"):
    return apply_current(store, {"op": "dispatch.start", "id": identifier, "task_id": task,
                                 "based_on_revision": store.show()["revision"],
                                 "request_hash": digest(identifier), "budget_ids": ["tokens"]})


def _coverage(store, status="unknown", evidence_ids=None):
    return [{"requirement_id": identifier, "status": status,
             "evidence_ids": list(evidence_ids or [])}
            for identifier, row in sorted(store.show()["requirements"].items())
            if row["status"] == "active"]


def _reject(store, event, expected_revision=None):
    from session_state import SessionStateError
    path = store.project_root / ".pea-state/events.json"
    before = path.read_bytes()
    revision = store.show()["revision"] if expected_revision is None else expected_revision
    try:
        store.apply(event, expected_revision=revision)
    except SessionStateError:
        if path.read_bytes() != before:
            raise AssertionError("rejected transition mutated the journal")
        return
    raise AssertionError("unsafe transition was accepted")


def run_safety_checks(base_store, fixture):
    """Each adversarial branch starts from the same synthetic durable snapshot."""
    from session_state import SessionStateError, SessionStore
    outcomes = []

    def run(identifier, detail, callback):
        with tempfile.TemporaryDirectory(prefix="pea-lifecycle-case-") as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(base_store.project_root, project)
            branch = SessionStore(project)
            try:
                callback(branch)
                outcomes.append({"id": identifier, "passed": True, "detail": detail})
            except Exception as error:
                outcomes.append({"id": identifier, "passed": False,
                                 "detail": type(error).__name__ + ": " + str(error)})

    def stale_write(store):
        revision = store.show()["revision"]
        apply_current(store, {"op": "question.add", "id": "q-new", "text": "Synthetic open question?"})
        _reject(store, {"op": "question.add", "id": "q-stale", "text": "Old writer?"}, revision)
    run("stale-writer-rejected", "A second writer cannot commit using an earlier revision; journal unchanged.", stale_write)

    def stale_decision(store):
        _reject(store, {"op": "decision.record", "id": "stale-decision", "task_id": "review",
                        "based_on_revision": store.show()["revision"] - 1,
                        "verdict": "HOLD", "coverage": _coverage(store)})
    run("stale-decision-rejected", "Current write revision cannot launder an older reasoning receipt.", stale_decision)

    def preferred_coverage(store):
        apply_current(store, {"op": "requirement.add", "id": "quiet", "value": "Prefer quiet rooms.",
                              "strength": "prefer", "scope": "all-properties",
                              "provenance": provenance({"id": "user-quiet", "text": "Prefer quiet rooms."})})
        _reject(store, {"op": "decision.record", "id": "missing-preference", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "verdict": "HOLD",
                        "coverage": [c for c in _coverage(store) if c["requirement_id"] != "quiet"]})
    run("every-active-requirement-covered", "Even a preferred requirement must be acknowledged; unmet preference alone need not block PASS.", preferred_coverage)

    def conditional_missing_predicate(store):
        _reject(store, {"op": "decision.record", "id": "predicate-bypass", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "verdict": "PASS",
                        "coverage": _coverage(store, "met", ["listing-v2"])})
    run("conditional-pass-requires-predicate-evidence", "The word met cannot silently satisfy an exception predicate.", conditional_missing_predicate)

    def hard_unknown(store):
        _reject(store, {"op": "decision.record", "id": "unknown-pass", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "verdict": "PASS",
                        "coverage": _coverage(store)})
    run("unknown-hard-condition-cannot-pass", "An unknown hard requirement keeps PASS unavailable.", hard_unknown)

    def fabricated_quote(store):
        _reject(store, {"op": "fact.record", "id": "fake-quote", "value": "Rent is free.",
                        "source_ids": ["listing-v2"], "critical": True,
                        "provenance": {"actor": "external", "source_id": "listing-v2",
                                       "quote": "Monthly rent is GBP 0."}})
    run("source-bound-quote-must-be-verbatim", "A fabricated quote cannot become checked document evidence.", fabricated_quote)

    def exact_retrieval(store):
        old = fixture["documents"]["listing-v1"]
        (store.project_root / "listing-v1.txt").write_text("Changed original file.\n", encoding="utf-8")
        result = store.retrieve("listing-v1", start=1, end=len(old.splitlines()))
        if result["sha256"] != digest(old) or result["text"] != old.rstrip("\n"):
            raise AssertionError("retrieval did not use the exact retained snapshot")
        new = store.retrieve("listing-v2", start=2, end=2)
        if new["sha256"] != digest(fixture["documents"]["listing-v2"]) or new["text"] != "Monthly rent is GBP 1950.":
            raise AssertionError("new version rent quote/hash is wrong")
    run("raw-document-hash-and-exact-retrieval", "Both source versions retain byte hashes; retrieval ignores later edits to the original file.", exact_retrieval)

    def snapshot_tamper(store):
        row = store.show()["documents"]["listing-v2"]
        (store.project_root / ".pea-state" / ("object-" + row["sha256"] + ".txt")).write_text("tampered\n", encoding="utf-8")
        try:
            store.show()
        except SessionStateError:
            return
        raise AssertionError("damaged immutable source snapshot was accepted")
    run("damaged-source-snapshot-rejected", "Hash verification detects modified retained bytes before state use.", snapshot_tamper)

    def source_supersession(store):
        apply_current(store, {"op": "fact.record", "id": "rent-evidence", "value": 1950,
                              "source_ids": ["listing-v2"], "critical": True,
                              "provenance": {"actor": "external", "source_id": "listing-v2",
                                             "quote": "Monthly rent is GBP 1950."}})
        apply_current(store, {"op": "fact.record", "id": "derived-rent", "value": "Above GBP 1650.",
                              "source_ids": ["rent-evidence"], "critical": True, "derived": True,
                              "based_on_revision": store.show()["revision"],
                              "provenance": {"actor": "agent", "source_id": "rent-evidence",
                                             "quote": "Monthly rent is GBP 1950."}})
        apply_current(store, {"op": "decision.record", "id": "source-decision", "task_id": "review",
                              "based_on_revision": store.show()["revision"], "verdict": "HOLD",
                              "coverage": _coverage(store, "unknown", ["rent-evidence"])})
        apply_current(store, {"op": "task.complete", "id": "review",
                              "based_on_revision": store.show()["revision"], "evidence_ids": ["rent-evidence"]})
        text = "Synthetic listing revision 3.\nMonthly rent is GBP 1600.\n"
        (store.project_root / "listing-v3.txt").write_text(text, encoding="utf-8")
        apply_current(store, {"op": "document.add", "id": "listing-v3", "path": "listing-v3.txt",
                              "supersedes": "listing-v2", "line_ranges": [[1, 2]],
                              "provenance": {"actor": "external", "source_id": "listing", "quote": text.splitlines()[0]}})
        state = store.show()
        if state["documents"]["listing-v2"]["status"] == "active":
            raise AssertionError("superseded document is still active")
        for identifier in ("rent-evidence", "derived-rent"):
            if state["facts"][identifier].get("valid") is not False:
                raise AssertionError("source-dependent fact stayed valid: " + identifier)
        if state["decisions"]["source-decision"]["valid"] or state["tasks"]["review"]["valid"]:
            raise AssertionError("superseded source left a decision/completion valid")
    run("source-supersession-invalidates-dependent-work", "A new source invalidates direct and derived facts, decisions and prior task completion.", source_supersession)

    def retire_fact_chain(store):
        for identifier, source in (("first-fact", "listing-v2"), ("second-fact", "first-fact")):
            apply_current(store, {"op": "fact.record", "id": identifier, "value": 1950,
                                  "source_ids": [source], "derived": False, "critical": True,
                                  "provenance": {"actor": "external", "source_id": source,
                                                 "quote": "Monthly rent is GBP 1950."}})
        apply_current(store, {"op": "fact.retire", "id": "first-fact",
                              "provenance": provenance({"id": "withdraw-fact", "text": "Withdraw the first rent fact as evidence."})})
        if store.show()["facts"]["second-fact"]["valid"]:
            raise AssertionError("retired factual source left a non-derived dependent fact valid")
        _reject(store, {"op": "task.complete", "id": "review", "based_on_revision": store.show()["revision"],
                        "evidence_ids": ["second-fact"]})
    run("retired-fact-invalidates-transitive-evidence", "Retiring a cited fact also invalidates copied downstream facts, even when not labelled derived.", retire_fact_chain)

    def pending_request(store):
        apply_current(store, {"op": "request.capture", "id": "new-user-request",
                              "text": "Change the conditions; reconciliation is pending.", "source": "synthetic-user"})
        _reject(store, {"op": "dispatch.start", "id": "blocked-request", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("pending"),
                        "budget_ids": ["tokens"]})
    run("pending-request-blocks-dispatch", "Exact raw steering must be reconciled before a new dispatch.", pending_request)

    def paused_workflow(store):
        apply_current(store, {"op": "task.update", "id": "research", "changes": {"status": "paused"}})
        apply_current(store, {"op": "request.capture", "id": "while-paused", "text": "Do not resume.", "source": "synthetic-user"})
        apply_current(store, {"op": "request.resolve", "id": "while-paused", "resolution": "no_change", "note": "Keep pause."})
        if store.show()["tasks"]["research"]["status"] != "paused":
            raise AssertionError("state invalidation silently removed the workflow pause")
        _reject(store, {"op": "dispatch.start", "id": "blocked-pause", "task_id": "research",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("paused"),
                        "budget_ids": ["tokens"]})
    run("pause-persists-through-steering", "A pause survives capture/reconciliation and still prevents workflow dispatch.", paused_workflow)

    def stale_result(store):
        started = _dispatch(store)
        apply_current(store, {"op": "request.capture", "id": "steering-during-call",
                              "text": "The conditions changed while the call was running.", "source": "synthetic-user"})
        _reject(store, {"op": "dispatch.finish", "id": "physical-1", "dispatch_revision": started["revision"],
                        "status": "completed", "result_hash": digest("old result"), "evidence_ids": []})
    run("mid-call-steering-rejects-stale-result", "An earlier physical response cannot complete against newer user requirements.", stale_result)

    def stale_unsettled_dispatch(store):
        _dispatch(store)
        apply_current(store, {"op": "request.capture", "id": "steer", "text": "Change while running.", "source": "synthetic-user"})
        apply_current(store, {"op": "request.resolve", "id": "steer", "resolution": "no_change", "note": "Keep requirements; old call still unresolved."})
        _reject(store, {"op": "dispatch.start", "id": "premature-followup", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("followup"),
                        "budget_ids": ["tokens"]})
    run("unsettled-stale-call-blocks-next-dispatch", "Reconciled user text does not settle the old physical call or its usage.", stale_unsettled_dispatch)

    def spend_gate(store, amount):
        apply_current(store, {"op": "budget.spend", "id": "tokens", "amount": amount})
        _reject(store, {"op": "dispatch.start", "id": "spend-bypass", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("spend"),
                        "budget_ids": ["tokens"]})
    run("unknown-usage-is-not-zero", "Unknown token usage pauses new spending.", lambda s: spend_gate(s, None))
    run("overspend-prevents-followup", "A measured ceiling overrun remains recorded and prevents another call.", lambda s: spend_gate(s, 70001))

    def scope_reclassification(store):
        _reject(store, {"op": "budget.set", "id": "rent", "scope": "api_tokens", "limit": 100000,
                        "unit": "tokens", "provenance": provenance({"id": "bad-budget", "text": "Synthetic invalid reclassification."})})
    run("housing-budget-cannot-become-api-credit", "Stable budget IDs cannot change economic scope or unit.", scope_reclassification)

    def bound_budget(store):
        apply_current(store, {"op": "task.update", "id": "review", "changes": {"budget_ids": ["tokens"]}})
        apply_current(store, {"op": "budget.spend", "id": "tokens", "amount": None})
        _reject(store, {"op": "dispatch.start", "id": "omit-budget", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("omit"),
                        "budget_ids": []})
    run("task-bound-budget-cannot-be-omitted", "A caller cannot bypass an unknown task-bound budget with an empty dispatch list.", bound_budget)

    def idempotent_spend(store):
        _dispatch(store)
        event = {"op": "budget.spend", "id": "tokens", "amount": 17, "dispatch_id": "physical-1"}
        first = apply_current(store, event)
        replay = apply_current(store, event)
        if first != replay or replay["budgets"]["tokens"]["spent"] != 17:
            raise AssertionError("recovery duplicated usage or created an unnecessary event")
        _reject(store, dict(event, amount=18))
    run("usage-recovery-is-idempotent", "Same dispatch usage is counted once; conflicting telemetry is rejected.", idempotent_spend)

    def paused_goal(store):
        apply_current(store, {"op": "task.add", "id": "project-goal", "kind": "goal", "title": "Finish the synthetic review",
                              "depends_on": ["review"], "acceptance": ["Review is currently complete."]})
        apply_current(store, {"op": "task.update", "id": "project-goal", "changes": {"status": "paused"}})
        _reject(store, {"op": "dispatch.start", "id": "under-paused-goal", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "request_hash": digest("goal"),
                        "budget_ids": ["tokens"]})
    run("paused-goal-blocks-descendant-work", "A paused parent goal also pauses its prerequisite work, not just its own dispatch.", paused_goal)

    def incomplete_dependency(store):
        apply_current(store, {"op": "task.add", "id": "project-goal", "kind": "goal", "title": "Finish review",
                              "depends_on": ["review"], "acceptance": ["Review is complete with current evidence."]})
        _reject(store, {"op": "task.complete", "id": "project-goal", "based_on_revision": store.show()["revision"],
                        "evidence_ids": ["listing-v2"]})
    run("goal-needs-current-complete-dependencies", "A saved source document cannot bypass an unfinished prerequisite task.", incomplete_dependency)

    def pending_question(store):
        apply_current(store, {"op": "question.add", "id": "blocking-choice", "text": "Which scope did the user mean?",
                              "blocking": True, "task_ids": ["review"]})
        _reject(store, {"op": "decision.record", "id": "before-answer", "task_id": "review",
                        "based_on_revision": store.show()["revision"], "verdict": "HOLD", "coverage": _coverage(store)})
    run("blocking-question-prevents-final-receipt", "An unresolved material question prevents a current decision receipt for affected work.", pending_question)

    def overflow(store):
        before = (store.project_root / ".pea-state/events.json").read_bytes()
        try:
            store.context(max_chars=100)
        except SessionStateError:
            if before != (store.project_root / ".pea-state/events.json").read_bytes():
                raise AssertionError("context failure changed the journal")
            return
        raise AssertionError("oversized required context was silently truncated")
    run("small-context-fails-without-truncation", "Insufficient context capacity is an explicit failure, not omitted requirements.", overflow)

    def stale_checkpoint(store):
        checkpoint = store.checkpoint(max_chars=100000)
        apply_current(store, {"op": "request.capture", "id": "after-checkpoint", "text": "New exact user input.", "source": "synthetic-user"})
        restarted = SessionStore(store.project_root)
        check = restarted.verify()["checkpoint"]
        packet = restarted.context(max_chars=100000)
        if check["current"] or packet["revision"] <= checkpoint["revision"] or "after-checkpoint" not in packet["pending_requests"]:
            raise AssertionError("stale checkpoint masked a newer journal event")
    run("restart-prefers-journal-over-stale-checkpoint", "Fresh recovery exposes pending input that arrived after the saved checkpoint.", stale_checkpoint)

    return outcomes


def run_scenarios(project, recent_records=4):
    from session_state import SessionStore
    if type(recent_records) is not int or recent_records < 1:
        raise ValueError("recent_records must be positive")
    fixture = _read_fixture()
    store = SessionStore(project)
    store.init("offline-synthetic-project")
    records, checkpoints = [], []
    for record in fixture["records"]:
        apply_record(store, record, fixture)
        records.append(record)
        if not record.get("checkpoint"):
            continue
        expected = facts_from_history(records)
        naive = facts_from_history(records, last=recent_records)
        # Fresh object reconstructs from disk, with no earlier Python state object.
        store.checkpoint(max_chars=100000)
        restored = SessionStore(project)
        state = restored.show()
        packet = restored.context(max_chars=100000)
        visible_documents = {r["document_id"]: fixture["documents"][r["document_id"]]
                             for r in records if r["action"] == "document"}
        checkpoints.append({"id": record["checkpoint"], "revision": state["revision"],
                            "checks": len(expected), "expected_facts": expected,
                            "naive_errors": differences(expected, naive),
                            "durable_errors": differences(expected, project_facts(state)),
                            "characters": {"full_input": len(canonical({"documents": visible_documents,
                                                                         "records": [{k: v for k, v in r.items()
                                                                                      if k not in ("facts", "checkpoint")}
                                                                                     for r in records]})),
                                           "naive_facts": len(canonical(naive)),
                                           "durable_packet": len(canonical(packet))}})
    safety_checks = run_safety_checks(store, fixture)
    checks = sum(c["checks"] for c in checkpoints)
    summary = {"full_history_oracle": {"checks": checks, "errors": 0, "reference_only": True},
               "naive_recent_records": {"checks": checks,
                                        "errors": sum(len(c["naive_errors"]) for c in checkpoints)},
               "durable_resume": {"checks": checks,
                                  "errors": sum(len(c["durable_errors"]) for c in checkpoints)},
               "safety": {"checks": len(safety_checks), "passed": sum(c["passed"] for c in safety_checks)}}
    return {"version": 1, "synthetic": True, "llm_calls": 0, "model_quality": "not_measured",
            "tokens": "not_measured", "cost": "not_measured", "recent_records": recent_records,
            "design": {"input_records": len(records), "checkpoints": len(checkpoints),
                       "unique_semantic_facts": len(facts_from_history(records)),
                       "fact_checks_are_repeated_checkpoint_assertions": True},
            "fixture_sha256": digest(canonical(fixture)),
            "source_manifest": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (Path(__file__).resolve(), Path(__file__).with_name("lifecycle.json").resolve(),
                                             ROOT / "skills/vet-flat/scripts/session_state.py")},
            "summary": summary,
            "checkpoints": checkpoints, "safety_checks": safety_checks,
            "ok": summary["durable_resume"]["errors"] == 0 and all(c["passed"] for c in safety_checks)}


def render_markdown(report):
    lines = ["# Offline session lifecycle validation", "",
             "All scenarios use synthetic data and make zero LLM calls. The expected-state "
             "oracle consists of hand-authored semantic fact updates. The lossy comparator "
             "retains only the last %s fact records; it is a deterministic truncation proxy, "
             "not an implementation of Codex or Claude compaction." % report["recent_records"], "",
             "The %s fact checks repeat %s distinct semantic facts across %s checkpoints. "
             "They are not independent model trials." %
             (report["summary"]["durable_resume"]["checks"], report["design"]["unique_semantic_facts"],
              report["design"]["checkpoints"]), "",
             "| Path | Fact checks | State errors |", "|---|---:|---:|"]
    for name in ("full_history_oracle", "naive_recent_records", "durable_resume"):
        item = report["summary"][name]
        lines.append("| %s | %s | %s |" % (name, item["checks"], item["errors"]))
    lines.extend(["", "The oracle's zero error count is definitional: the full fixture is the "
                  "reference, not a tested reasoning agent.", "",
                  "| Checkpoint | Full input characters | Lossy fact characters | Durable packet characters | Durable errors |",
                  "|---|---:|---:|---:|---:|"])
    for item in report["checkpoints"]:
        size = item["characters"]
        lines.append("| %s | %s | %s | %s | %s |" %
                     (item["id"], size["full_input"], size["naive_facts"],
                      size["durable_packet"], len(item["durable_errors"])))
    lines.extend(["", "Character counts measure different representations and do not include "
                  "provider tokenization, cache writes/reads, model output or subsequent document "
                  "retrieval. They are not measured token or cost savings.", "",
                  "On this short fixture, durable packets include provenance, status and version "
                  "metadata, so they can be larger than the full input history. Continuity checks "
                  "are useful independently of whether the chosen representation is smaller.", "",
                  "| Safety invariant | Passed | Detail |", "|---|---|---|"])
    for item in report["safety_checks"]:
        lines.append("| %s | %s | %s |" %
                     (item["id"], str(item["passed"]).lower(), item["detail"].replace("|", "\\|")))
    lines.extend(["", "This run checks state storage, retrieval, lifecycle transitions and rejection "
                  "boundaries. It does not establish semantic extraction accuracy, source truth, "
                  "prompt-injection containment of a tool-enabled model, real native hook delivery, "
                  "or equivalence of final answer quality. A coverage receipt can still contain "
                  "an incorrect claim; exact retained quotes establish provenance, not truth.", ""])
    return "\n".join(lines)


def write_report(report, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "session-harness-validation.json"
    md_path = output_dir / "session-harness-validation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="explicit destination; defaults to a new temporary directory")
    parser.add_argument("--recent-records", type=int, default=4)
    args = parser.parse_args()
    if args.recent_records < 1:
        parser.error("--recent-records must be positive")
    with tempfile.TemporaryDirectory(prefix="pea-lifecycle-state-") as project:
        report = run_scenarios(Path(project), recent_records=args.recent_records)
    destination = args.output_dir or Path(tempfile.mkdtemp(prefix="pea-lifecycle-report-"))
    paths = write_report(report, destination)
    print(json.dumps({"ok": report["ok"], "reports": [str(p) for p in paths],
                      "summary": report["summary"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
