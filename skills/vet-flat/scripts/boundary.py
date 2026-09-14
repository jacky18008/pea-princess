#!/usr/bin/env python3
"""Persist and check candidate-specific user tradeoffs, offline (stdlib only).

No source access, login, fee or network/robots interaction. Inputs are trusted-host
normalizations, not automatic intent extraction. User quotes do not authenticate
the caller or prove semantic consent. See references/boundary-api.md.
Usage: boundary.py --project PRIVATE_PROJECT evaluate --evidence evidence.json
"""
import argparse
import copy
import json
from pathlib import Path
import sys

import eligibility

COMPARISON_SCHEMA = "pea-princess/comparison/1"
PROJECTION_SCHEMA = "pea-princess/boundary-review/1"


def _state_api():
    # Also called by session_state's reducer; avoid an import-time cycle.
    import session_state
    return session_state


def _require(ok, message):
    if not ok:
        raise _state_api().SessionStateError(message)


def _comparison(row):
    value = row.get("value")
    if (not isinstance(value, dict) or value.get("schema_version") != COMPARISON_SCHEMA
            or row.get("strength") == "conditional"):
        return None
    result = {k: copy.deepcopy(v) for k, v in value.items() if k != "schema_version"}
    eligibility._predicate(result, "comparison", {})
    return result


def normalized(state):
    """Use the existing requirement value as the ONE stored comparison value.

    Free-text/conditional requirements are retained as unmapped; never silently
    omitted from a ready-to-view claim. This adapter does not interpret prose.
    """
    requirements, unmapped = [], []
    for key, row in state["requirements"].items():
        if row["status"] != "active":
            continue
        check = _comparison(row)
        if check is None or row["scope"] != "all candidates":
            unmapped.append(key)
            continue
        provenance = row.get("provenance", {})
        request = state["requests"].get(provenance.get("request_id"), {})
        if (not request or provenance.get("quote", "") not in request.get("text", "")
                or not provenance.get("quote")):
            unmapped.append(key)
            continue
        requirements.append(dict(check, id=key, mandatory=row["strength"] != "prefer",
                                 provenance=copy.deepcopy(provenance)))
    return requirements, unmapped


def _latest(state):
    result = {}
    for row in state.get("proposed_checks", {}).values():
        if row.get("kind") != "boundary" or row.get("candidate_id") is None:
            continue
        pair = (row["candidate_id"], row["requirement_id"])
        if pair not in result or row["created_revision"] > result[pair]["created_revision"]:
            result[pair] = row
    return result


def _retained_hold(state, row):
    """An undecided assistant offer cannot replace an actual retained choice."""
    while row and row["status"] == "pending" and row.get("supersedes"):
        predecessor = state["proposed_checks"].get(row["supersedes"])
        if (not predecessor or predecessor.get("candidate_id") != row["candidate_id"]
                or predecessor.get("requirement_id") != row["requirement_id"]
                or predecessor["created_revision"] >= row["created_revision"]):
            break
        row = predecessor
    return row if row and row["status"] == "retained" else None


def inputs(state, evidence):
    _require(isinstance(evidence, dict) and isinstance(evidence.get("candidates"), list),
             "evidence must be an object with a candidates array")
    _require(all(isinstance(row, dict) and isinstance(row.get("id"), str)
                 and isinstance(row.get("fields"), dict) for row in evidence["candidates"]),
             "each evidence candidate needs an id and fields object")
    requirements, unmapped = normalized(state)
    _require(bool(requirements), "no comparable captured user conditions; normalize them first")
    ids = {row["id"] for row in requirements}
    candidate_ids = {row["id"] for row in evidence.get("candidates", [])}
    exceptions = []
    for row in _latest(state).values():
        if (row["status"] == "accepted" and row.get("decision") == "candidate"
                and row["requirement_id"] in ids and row["candidate_id"] in candidate_ids):
            provenance = row["provenance"]
            exceptions.append({"id": row["id"], "candidate_id": row["candidate_id"],
                "requirement_id": row["requirement_id"], "request_id": provenance["request_id"],
                "quote": provenance["quote"], "when": [],
                "requirement_sha256": row["requirement_sha256"],
                "accepted_check": copy.deepcopy(row["accepted_check"])})
    constraints = {"schema_version": eligibility.CONSTRAINTS_SCHEMA, "revision": state["revision"],
        "requirements": requirements, "exceptions": exceptions,
        "user_requests": {key: row["text"] for key, row in state["requests"].items()}}
    pins = {"revision": state["revision"], "constraints_sha256": eligibility.canonical_hash(constraints),
            "evidence_sha256": eligibility.canonical_hash(evidence)}
    return constraints, pins, unmapped


def evaluate(state, evidence):
    constraints, pins, unmapped = inputs(state, evidence)
    checked = eligibility.evaluate(constraints, evidence, **pins)
    requirements = {row["id"]: row for row in constraints["requirements"]}
    proposals = []
    for row in state.get("proposed_checks", {}).values():
        if row.get("kind") != "boundary":
            continue
        current = requirements.get(row["requirement_id"])
        proposals.append(dict(copy.deepcopy(row), requirement_current=bool(current and
            eligibility.canonical_hash(current) == row["requirement_sha256"])))
    latest = _latest(state)
    rows, todos = {}, []
    for key, result in checked["candidates"].items():
        holds = []
        pending_boundary_requirements = set()
        for (candidate_id, requirement_id), proposal in latest.items():
            if candidate_id != key:
                continue
            # This action hold outlives the numeric condition itself. Retiring
            # that condition or writing another undecided assistant offer does
            # not mean the person agreed to view the home.
            retained = _retained_hold(state, proposal)
            if retained:
                holds.append(retained["id"])
            current = requirements.get(requirement_id)
            if current is None:
                continue
            same = eligibility.canonical_hash(current) == proposal["requirement_sha256"]
            if same and proposal["status"] in ("pending", "declined"):
                holds.append(proposal["id"])
                if proposal["status"] == "pending":
                    pending_boundary_requirements.add(requirement_id)
            if (proposal["status"] == "accepted" and proposal.get("decision") == "candidate"
                    and proposal["id"] not in result["exception_ids"]
                    and (result["checks"][requirement_id].get("comparison") is not True
                         or result["checks"][requirement_id]["qualifier"] not in current["basis"])):
                # Consent to a bounded tradeoff expires outside that bound even
                # when the target is only a preference. Falling back to that
                # target still requires its own permitted evidence basis.
                holds.append(proposal["id"])
        unmet = [rid for rid, check in result["checks"].items()
                 if check["mandatory"] and (check.get("comparison") is not True
                     or check["qualifier"] not in requirements[rid]["basis"])
                 and not check.get("exception_id")]
        allowed = (result["status"] != "blocked" and not holds and not unmapped
                   and not unmet and not state.get("pending_requests", {})
                   and not any(row["status"] == "pending" for row in state["requests"].values()))
        rows[key] = {"candidate_id": key, "status": result["status"],
            "viewing_allowed": allowed, "consent_holds": holds,
            "failed_requirement_ids": result["failed_requirement_ids"],
            "open_requirement_ids": result["open_requirement_ids"],
            "exception_ids": result["exception_ids"]}
        if holds:
            todos.append({"candidate_id": key, "action": "hold_viewing", "proposal_ids": holds})
        if result["status"] == "blocked":
            todos.append({"candidate_id": key, "action": "reconsider", "requirement_ids": result["failed_requirement_ids"]})
        if (result["open_requirement_ids"] and (result["status"] != "blocked"
                or set(result["failed_requirement_ids"]) <= pending_boundary_requirements)):
            todos.append({"candidate_id": key, "action": "investigate", "requirement_ids": result["open_requirement_ids"]})
        if allowed:
            todos.append({"candidate_id": key, "action": "viewing_permitted", "requirement_ids": []})
    # Administrative order only: evidence-ready first, then fewer open checks.
    # Do not pretend this is the person's overall utility/rental recommendation.
    ranking = sorted((key for key, row in rows.items() if row["status"] != "blocked"),
                     key=lambda key: (not rows[key]["viewing_allowed"], len(rows[key]["open_requirement_ids"]), key))
    pending = [key for key, request in state["requests"].items() if request["status"] == "pending"]
    ready = not unmapped and not pending
    if not ready:
        ranking = []
        todos = [{"action": "reconcile_conditions", "candidate_id": None,
                  "requirement_ids": unmapped, "request_ids": pending}]
    return {"schema_version": PROJECTION_SCHEMA, "ready": ready,
        "binding": dict(pins, event_hash=state["event_hash"]),
        "confirmed_conditions": copy.deepcopy(state["requirements"]), "proposed_checks": proposals,
        "unmapped_requirement_ids": unmapped, "checks": checked, "candidates": rows,
        "ranking": ranking, "ranking_basis": "viewing permission, then fewer unresolved checks, then ID; not a preference score",
        "todos": todos, "notice": "Permission is not a booking, source verification or an overall property approval."}


def turn_events(state, payload, evidence):
    """Construct explicit quoted changes; do not infer intent from user text.

    This constructor supplies mechanical schema/provenance fields so callers
    cannot accidentally omit a comparison marker and drop a known condition.
    """
    s = _state_api()
    allowed = {"request", "requirements", "proposals", "decisions", "instructions", "retire"}
    _require(isinstance(payload, dict) and not set(payload) - allowed, "unknown turn fields")
    request = payload.get("request")
    _require(isinstance(request, dict) and set(request) == {"id", "text"}, "turn requires exact request id/text")
    s._id(request["id"])
    s._text(request["text"], "request.text", 200000)
    events = []
    if state["project_id"] is None:
        events.append({"op": "project.init", "project_id": "rental-project"})
    events.append({"op": "request.capture", "id": request["id"], "text": request["text"], "source": "user-message"})

    def source(quote):
        s._text(quote, "user quote")
        _require(quote in request["text"], "change quote must occur in this actual user message")
        return {"actor": "user", "authorized": True, "source_id": request["id"],
                "request_id": request["id"], "quote": quote}

    def rows(name):
        result = payload.get(name, [])
        _require(isinstance(result, list) and len(result) <= 40, name + " must be a bounded array")
        return result

    for row in rows("requirements"):
        _require(isinstance(row, dict) and {"id", "check", "strength", "scope", "quote"} <= set(row)
                 and not set(row) - {"id", "check", "strength", "scope", "quote", "label"},
                 "requirements need id, check, strength, scope, quote and optional label")
        eligibility._predicate(row["check"], "requirement.check", {})
        _require(row["strength"] in ("must", "prefer", "prohibit") and row["scope"] == "all candidates",
                 "this comparison adapter needs an explicit strength and all-candidates scope")
        value = dict(copy.deepcopy(row["check"]), schema_version=COMPARISON_SCHEMA)
        changes = {"value": value, "strength": row["strength"], "scope": row["scope"]}
        if "label" in row:
            changes["label"] = s._text(row["label"], "condition label", 4000)
        provenance = source(row["quote"])
        if row["id"] in state["requirements"]:
            events.append({"op": "requirement.update", "id": row["id"], "changes": changes, "provenance": provenance})
        else:
            events.append(dict(changes, op="requirement.add", id=row["id"], provenance=provenance))
    for row in rows("retire"):
        _require(isinstance(row, dict) and set(row) == {"id", "quote"}, "retirement needs id and exact quote")
        events.append({"op": "requirement.retire", "id": row["id"], "provenance": source(row["quote"])})
    # Decisions refer to an earlier actual proposal, never one authored in this
    # same turn before manufacturing an assent to it.
    for row in rows("decisions"):
        _require(isinstance(row, dict) and {"id", "decision", "quote"} <= set(row)
                 and not set(row) - {"id", "decision", "quote", "global_check"}, "invalid turn decision fields")
        event = {key: copy.deepcopy(value) for key, value in row.items() if key != "quote"}
        event.update(op="boundary.decide", provenance=source(row["quote"]))
        events.append(event)
    # A person may initiate a decision without replying to an assistant offer.
    # Preserve that chronology instead of manufacturing a proposal and assent.
    for row in rows("instructions"):
        _require(isinstance(row, dict) and {"id", "decision", "requirement_id", "quote"} <= set(row)
                 and not set(row) - {"id", "decision", "requirement_id", "quote", "candidate_id",
                                     "accepted_check", "global_check"}, "invalid turn instruction fields")
        event = {key: copy.deepcopy(value) for key, value in row.items() if key != "quote"}
        event.update(op="boundary.instruct", provenance=source(row["quote"]), evidence=copy.deepcopy(evidence))
        events.append(event)
    for row in rows("proposals"):
        _require(isinstance(row, dict) and set(row) == {"id", "text", "why", "requirement_id", "candidate_id", "accepted_check"},
                 "invalid turn proposal fields")
        events.append(dict(copy.deepcopy(row), op="boundary.propose", evidence=copy.deepcopy(evidence)))
    events.append({"op": "request.resolve", "id": request["id"], "resolution": "applied",
                   "note": "Reconciled the explicit changes and generated the current comparison and viewing work."})
    return events


def reconcile(store, payload, evidence, expected_revision, max_chars=64000):
    before = current_or_empty(store)
    _require(before["revision"] == expected_revision, "turn is based on a stale revision; reload and reconcile")
    events = turn_events(before, payload, evidence)
    artifacts = {}

    def validate(state):
        review = evaluate(state, evidence)
        _require(review["ready"], "unmapped or pending conditions: reconcile them before publishing a comparison")
        artifacts["review"] = review
        artifacts["context"] = store._context(state, max_chars)

    state = store.apply_many(events, expected_revision, validate=validate)
    # Journal commit precedes export. A failed export is recovered by context /
    # evaluate; repeating this user turn would be a duplicate, never a retry.
    try:
        with store._locked() as directory:
            _require(store._load(directory)[1]["revision"] == state["revision"],
                     "another change arrived; recompute current context/review before publishing")
            for name, artifact in artifacts.items():
                store._write(directory, "boundary-" + name + ".json", artifact)
    except (OSError, ValueError) as exc:
        raise _state_api().SessionStateError("turn saved at revision %s; export failed: %s; use context/evaluate, do not resubmit" %
                                             (state["revision"], exc)) from exc
    review = artifacts["review"]
    return {"ok": True, "revision": state["revision"], "context": artifacts["context"],
            "files": {name: str(store.state_root / ("boundary-" + name + ".json")) for name in artifacts},
            "comparison": {key: review[key] for key in ("ready", "binding", "checks", "candidates", "ranking", "todos")}}


def current_or_empty(store):
    with store._locked(create=True) as directory:
        journal, state = store._load(directory, missing=True)
        _require(journal is not None or store._read(directory, "identity.json", missing=True) is None,
                 "initialized project lost its journal; restore it before continuing")
        return state


def _same_predicate(check, original):
    eligibility._predicate(check, "accepted_check", {})
    _require(("scope" in check) == ("scope" in original), "a boundary proposal must preserve scope presence")
    for key in ("field", "type", "operator", "unit", "scope"):
        _require(check.get(key) == original.get(key), "a boundary proposal cannot change " + key)
    _require(set(check["basis"]) <= set(original["basis"]), "a proposal cannot broaden evidence authority")


def _instruct(state, event, revision):
    """Record trusted caller normalization of an actual user-initiated decision.

    Exact captured provenance establishes the recorded source and chronology,
    not semantic consent. Retention/release changes an action hold, never a
    numeric bound; global changes do not supersede candidate-specific holds.
    """
    s = _state_api()
    allowed = {"op", "id", "decision", "requirement_id", "candidate_id", "accepted_check",
               "global_check", "provenance", "evidence"}
    _require(set(event) <= allowed, "unknown boundary instruction fields")
    state.setdefault("proposed_checks", {})
    identifier = event.get("id")
    s._new(state, "proposed_checks", identifier)
    decision = event.get("decision")
    _require(decision in ("retain", "candidate", "global", "release"), "unknown boundary instruction")
    _require((decision == "candidate") == ("accepted_check" in event),
             "only candidate instructions require an accepted_check")
    _require((decision == "global") == ("global_check" in event),
             "only global instructions require a global_check")
    _require((decision != "global") == ("candidate_id" in event),
             "global instructions have no candidate; other instructions require candidate_id")
    provenance = s._provenance(event.get("provenance"), state, user=True)
    request = state["requests"].get(provenance.get("request_id"))
    _require(request and provenance["source_id"] == provenance["request_id"],
             "instruction requires the actual captured user request as its source")
    requirement_id = event.get("requirement_id")
    requirements, _ = normalized(state)
    target = next((row for row in requirements if row["id"] == requirement_id), None)
    pair = (event.get("candidate_id"), requirement_id)
    previous = _latest(state).get(pair)
    if previous:
        _require(request["captured_revision"] > previous["updated_revision"],
                 "instruction requires a fresh captured user message after the latest proposal/decision")
    if decision == "release":
        retained = _retained_hold(state, previous)
        _require(retained is not None,
                 "release requires the latest retained viewing hold for this candidate and condition")
        # A retained hold can outlive a retired condition. Releasing it does not
        # restore the condition or authorize any exception to remaining checks.
        target = target or copy.deepcopy(retained["original_condition"])
    else:
        _require(target is not None, "instruction requires a current comparable user condition")
    condition_request = state["requests"][target["provenance"]["request_id"]]
    _require(request["captured_revision"] >= condition_request["captured_revision"],
             "instruction predates the current user condition")
    evidence = event.get("evidence")
    constraints, pins, _ = inputs(state, evidence)
    eligibility.evaluate(constraints, evidence, **pins)
    candidate = None
    if decision != "global":
        candidate = next((row for row in evidence["candidates"] if row["id"] == event["candidate_id"]), None)
        _require(candidate is not None, "instruction candidate is missing from evidence")
    check = None
    if decision in ("candidate", "global"):
        check = copy.deepcopy(event["accepted_check" if decision == "candidate" else "global_check"])
        _same_predicate(check, target)
    if decision == "candidate":
        comparison = eligibility._check(check, candidate["fields"])
        _require(comparison.get("comparison") is True and comparison["qualifier"] in check["basis"],
                 "the accepted bound must cover this candidate's known, correctly scoped evidence")
    if decision == "global":
        requirement = state["requirements"][requirement_id]
        requirement.update(value=dict(check, schema_version=COMPARISON_SCHEMA),
                           provenance=copy.deepcopy(provenance), updated_revision=revision)
        requirement.pop("label", None)
        s._requirements(requirement)
    record = {"decision": decision, "provenance": copy.deepcopy(provenance), "revision": revision}
    row = {"id": identifier, "kind": "boundary", "origin": "user", "decision": decision,
           "status": {"retain": "retained", "candidate": "accepted", "global": "accepted", "release": "released"}[decision],
           "candidate_id": pair[0], "requirement_id": requirement_id,
           "requirement_sha256": eligibility.canonical_hash(target), "original_condition": copy.deepcopy(target),
           "provenance": provenance, "quote": provenance["quote"], "decision_history": [record],
           "evidence_sha256": pins["evidence_sha256"], "created_revision": revision, "updated_revision": revision}
    if check is not None:
        name = "accepted_check" if decision == "candidate" else "global_check"
        row[name] = check
        record[name] = copy.deepcopy(check)
    if candidate is not None:
        source = candidate["fields"].get(target["field"])
        row["instruction_evidence"] = copy.deepcopy(source)
        row["instruction_source"] = (copy.deepcopy(evidence["sources"].get(source.get("source_id")))
                                     if source else None)
    if previous:
        row["supersedes"] = previous["id"]
    state["proposed_checks"][identifier] = row
    return row


def reduce_event(state, event, revision):
    """Called inside SessionStore's existing locked, atomic journal transaction."""
    s = _state_api()
    identifier = event.get("id")
    if event["op"] == "boundary.instruct":
        row = _instruct(state, event, revision)
    elif event["op"] == "boundary.propose":
        allowed = {"op", "id", "text", "why", "requirement_id", "candidate_id", "accepted_check", "evidence"}
        _require(set(event) <= allowed, "unknown boundary proposal fields")
        state.setdefault("proposed_checks", {})
        s._new(state, "proposed_checks", identifier)
        requirements, _ = normalized(state)
        target = next((row for row in requirements if row["id"] == event.get("requirement_id")), None)
        _require(target is not None, "proposal requires a current comparable user condition")
        check = copy.deepcopy(event.get("accepted_check"))
        _same_predicate(check, target)
        evidence = event.get("evidence")
        _require(isinstance(evidence, dict), "proposal requires retained candidate evidence")
        constraints, pins, _ = inputs(state, evidence)
        eligibility.evaluate(constraints, evidence, **pins)
        candidate = next((row for row in evidence["candidates"] if row["id"] == event.get("candidate_id")), None)
        _require(candidate is not None, "proposal candidate is missing from evidence")
        comparison = eligibility._check(check, candidate["fields"])
        _require(comparison.get("comparison") is True and comparison["qualifier"] in check["basis"],
                 "the offered bound must cover this candidate's known, correctly scoped evidence")
        pair = (candidate["id"], target["id"])
        previous = _latest(state).get(pair)
        _require(not previous or previous["status"] != "pending"
                 or previous["requirement_sha256"] != eligibility.canonical_hash(target),
                 "decide the existing current pending proposal first")
        source = candidate["fields"][target["field"]]
        row = {"id": identifier, "kind": "boundary", "text": s._text(event.get("text"), "proposal.text", 4000),
            "why": s._text(event.get("why"), "proposal.why", 4000), "status": "pending",
            "candidate_id": candidate["id"], "requirement_id": target["id"],
            "requirement_sha256": eligibility.canonical_hash(target), "original_condition": copy.deepcopy(target),
            "accepted_check": check, "offered_evidence": copy.deepcopy(source),
            "offered_source": evidence["sources"][source["source_id"]],
            "evidence_sha256": pins["evidence_sha256"], "created_revision": revision, "updated_revision": revision,
            "quote": None, "decision_history": []}
        if previous:
            row["supersedes"] = previous["id"]
        state["proposed_checks"][identifier] = row
    elif event["op"] == "boundary.decide":
        allowed = {"op", "id", "decision", "provenance", "global_check"}
        _require(set(event) <= allowed, "unknown boundary decision fields")
        row = state.get("proposed_checks", {}).get(identifier)
        _require(not row or row.get("origin") != "user",
                 "a user instruction is not an earlier assistant proposal; record a fresh instruction")
        _require(row and row.get("kind") == "boundary" and row["status"] in ("pending", "retained"),
                 "decide a pending or retained boundary proposal; otherwise make a new proposal")
        latest = _latest(state).get((row["candidate_id"], row["requirement_id"]))
        _require(latest and latest["id"] == identifier,
                 "proposal was superseded; decide the latest proposal or make a fresh one")
        provenance = s._provenance(event.get("provenance"), state, user=True)
        request = state["requests"].get(provenance.get("request_id"))
        _require(request and request["captured_revision"] > row["updated_revision"],
                 "decision requires an actual captured user reply after the proposal/latest decision")
        decision = event.get("decision")
        _require(decision in ("candidate", "global", "decline", "retain", "release"),
                 "unknown boundary decision")
        _require(decision == "global" or "global_check" not in event, "only a global decision may change the overall bound")
        requirements, _ = normalized(state)
        target = next((r for r in requirements if r["id"] == row["requirement_id"]), None)
        if decision == "release":
            retired = state["requirements"].get(row["requirement_id"], {})
            _require(row["status"] == "retained" and retired.get("status") == "retired",
                     "release requires a retained viewing hold whose condition was retired")
        else:
            _require(target and eligibility.canonical_hash(target) == row["requirement_sha256"],
                     "the original condition changed; make a fresh proposal")
        if decision == "global":
            check = copy.deepcopy(event.get("global_check"))
            _same_predicate(check, target)
            requirement = state["requirements"][row["requirement_id"]]
            requirement.update(value=dict(check, schema_version=COMPARISON_SCHEMA),
                               provenance=provenance, updated_revision=revision)
            # Display text may contain the old bound. Preserve it in history,
            # rather than presenting it beside the newly authorized comparison.
            requirement.pop("label", None)
            s._requirements(requirement)
        row.update(status={"candidate": "accepted", "global": "accepted", "decline": "declined", "retain": "retained", "release": "released"}[decision],
                   decision=decision, provenance=provenance, quote=provenance["quote"], updated_revision=revision)
        record = {"decision": decision, "provenance": copy.deepcopy(provenance), "revision": revision}
        if decision == "global":
            record["global_check"] = check
        row["decision_history"].append(record)
    else:
        raise s.SessionStateError("unknown boundary operation")
    s._invalidate(state, revision, "boundary decision/proposal changed: " + identifier,
                  requirements=[row["requirement_id"]])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    ctx = sub.add_parser("context")
    ctx.add_argument("--max-chars", type=int, default=32000)
    for command in ("propose", "decide", "instruct"):
        child = sub.add_parser(command)
        child.add_argument("--expected-revision", type=int, required=True)
        child.add_argument("--input", type=Path, required=True)
    for command in ("evaluate", "validate"):
        child = sub.add_parser(command)
        child.add_argument("--evidence", type=Path, required=True)
        if command == "validate":
            child.add_argument("--review", type=Path, required=True)
    turn = sub.add_parser("reconcile")
    turn.add_argument("--expected-revision", type=int, required=True)
    turn.add_argument("--input", type=Path, required=True)
    turn.add_argument("--evidence", type=Path, required=True)
    turn.add_argument("--max-chars", type=int, default=64000)
    args = parser.parse_args(argv)
    try:
        store = _state_api().SessionStore(args.project)
        if args.command == "context":
            result = store._context(current_or_empty(store), args.max_chars)
        elif args.command == "reconcile":
            result = reconcile(store, eligibility._read(args.input), eligibility._read(args.evidence),
                               args.expected_revision, max_chars=args.max_chars)
        elif args.command in ("propose", "decide", "instruct"):
            event = eligibility._read(args.input)
            _require("op" not in event, "input contains payload fields only, no op")
            event["op"] = "boundary." + args.command
            state = store.apply(event, expected_revision=args.expected_revision)
            result = {"ok": True, "revision": state["revision"],
                      "instruction" if args.command == "instruct" else "proposal": state["proposed_checks"][event["id"]]}
        else:
            state = store.show()
            result = evaluate(state, eligibility._read(args.evidence))
            if args.command == "validate":
                supplied = eligibility._read(args.review)
                _require(result["ready"], "unmapped or pending conditions prevent a current comparison validation")
                _require(eligibility.canonical_hash(supplied) == eligibility.canonical_hash(result),
                         "review differs from current conditions, evidence, decisions or TODOs")
                result = {"valid": True, "binding": result["binding"]}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
