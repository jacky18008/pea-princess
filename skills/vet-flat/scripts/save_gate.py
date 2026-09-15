#!/usr/bin/env python3
"""Check whether a claimed comparison or report is current in private state.

This is a read-only verification of recorded bytes and their revision, not a
source-truth, consent, or external-action check. A full comparison save also
requires a registered fidelity document: raw source bindings, all TfL plan
alternatives, and concrete pending checks. It does not repair a failed save.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import datetime
from urllib.parse import parse_qs, urlsplit

import boundary
import eligibility
import session_state

FIDELITY_SCHEMA = "pea-princess/comparison-fidelity/1"


def _require(condition, message):
    if not condition:
        raise session_state.SessionStateError(message)


def _current_report_bytes(store, path):
    """Read the currently visible report through project-relative no-follow fds."""
    _require(isinstance(path, str) and path and not Path(path).is_absolute(),
             "registered report path is not project-relative")
    parts = Path(path).parts
    _require(parts and all(part not in ("", ".", "..", ".pea-state") for part in parts),
             "registered report path is unsafe")
    descriptors = []
    try:
        parent = os.open(str(store.project_root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(parent)
        for part in parts[:-1]:
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            descriptors.append(parent)
        return store._read(parent, parts[-1], session_state.MAX_DOCUMENT_BYTES)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _snapshot_bytes(store, directory, state, document_id, actor=None):
    document = state["documents"].get(document_id)
    _require(document and document["status"] == "active" and document["valid"],
             "fidelity source document is missing or stale: " + str(document_id))
    if actor is not None:
        _require(document["provenance"]["actor"] in actor,
                 "assistant prose cannot be a provider source: " + document_id)
    data = store._read(directory, "object-" + document["sha256"] + ".txt",
                       session_state.MAX_DOCUMENT_BYTES)
    _require(hashlib.sha256(data).hexdigest() == document["sha256"]
             and len(data) == document["byte_length"],
             "fidelity source snapshot differs: " + document_id)
    return document, data


def _plan_summary(plan):
    return {key: plan.get(key) for key in ("ok", "http_status", "duration_min",
            "start", "arrival", "alternatives_min", "journeys_returned", "note")}


def _check_journey(raw, saved, candidate_id, source_id):
    _require(type(raw) is dict and type(raw.get("query")) is dict
             and type(raw.get("plans")) is dict, "journey source is not raw commute output")
    query = raw["query"]
    _require(query.get("plans") == ["all", "rail", "bus"]
             and set(raw["plans"]) == {"all", "rail", "bus"},
             "journey must retain all, rail and bus plan statuses: " + candidate_id)
    _require(saved.get("source_id") == source_id and saved.get("query") == query
             and saved.get("plans") == {mode: _plan_summary(raw["plans"][mode])
                                              for mode in ("all", "rail", "bus")},
             "saved journey alternatives differ from raw plans: " + candidate_id)
    # All three requests must have used the same origin, destination, date,
    # arrival time and door assumption. Only TfL's mode filter may vary.
    request_keys = []
    for mode in ("all", "rail", "bus"):
        url = raw["plans"][mode].get("source_url")
        _require(type(url) is str and url.startswith("https://api.tfl.gov.uk/Journey/"),
                 "journey plan lacks a TfL request URL: " + mode)
        parsed = urlsplit(url)
        parameters = parse_qs(parsed.query)
        request_keys.append((parsed.path, tuple(sorted((key, tuple(value)) for key, value
                          in parameters.items() if key != "mode"))))
        _require(parameters.get("date") == [query.get("date")]
                 and parameters.get("time") == [query.get("arrive_by", "").replace(":", "")]
                 and parameters.get("timeIs") == ["Arriving"],
                 "journey plan query differs from saved date/arrival")
    _require(len(set(request_keys)) == 1,
             "journey alternatives used different origin/destination/date")
    _require(type(query.get("door_buffer_min")) is int and query["door_buffer_min"] >= 0,
             "journey door buffer is invalid")


def _check_fidelity(store, directory, state, evidence, review, document_id):
    _require(document_id, "full comparison save needs --fidelity-document-id")
    document, data = _snapshot_bytes(store, directory, state, document_id, {"assistant"})
    _require(_current_report_bytes(store, document["path"]) == data,
             "current fidelity file differs from its registered snapshot")
    manifest = session_state._parse(data)
    _require(type(manifest) is dict and set(manifest) == {"schema_version",
             "evidence_sha256", "sources", "journeys", "pending_checks"}
             and manifest["schema_version"] == FIDELITY_SCHEMA,
             "comparison fidelity document has invalid schema")
    _require(manifest["evidence_sha256"] == eligibility.canonical_hash(evidence),
             "fidelity document is bound to different evidence")
    _require(type(manifest["sources"]) is dict
             and set(manifest["sources"]) == set(evidence["sources"]),
             "every evidence source needs a registered raw source binding")
    source_hashes, raw_sources = {}, {}
    for source_id, binding in manifest["sources"].items():
        _require(type(binding) is dict and set(binding) == {"document_id", "sha256", "kind"}
                 and binding["kind"] in ("tool_record", "user_extract"),
                 "source binding is invalid: " + source_id)
        allowed = {"tool", "external"} if binding["kind"] == "tool_record" else {"user"}
        source, source_data = _snapshot_bytes(store, directory, state,
                                              binding["document_id"], allowed)
        _require(binding["sha256"] == source["sha256"]
                 and binding["document_id"] != document_id,
                 "source binding hash or identity differs: " + source_id)
        text = source_data.decode("utf-8")
        _require(evidence["sources"][source_id] in text,
                 "evidence source is an unbound prose summary: " + source_id)
        if binding["kind"] == "tool_record":
            record = session_state._parse(source_data)
            _require(type(record) is dict and type(record.get("source_url")) is str
                     and urlsplit(record["source_url"]).scheme in ("http", "https")
                     and bool(urlsplit(record["source_url"]).netloc)
                     and type(record.get("http_status")) is int
                     and 100 <= record["http_status"] <= 599
                     and type(record.get("retrieved_at")) is str
                     and record["retrieved_at"].strip()
                     and record.get("evidence_class") in ("G", "S", "C", "I", "U"),
                     "raw tool source lacks URL/status/time/class provenance: " + source_id)
            if record["evidence_class"] == "G":
                _require(urlsplit(record["source_url"]).scheme == "https",
                         "official source must use HTTPS: " + source_id)
            raw_sources[source_id] = record
        source_hashes[source_id] = source["sha256"]
    for candidate in evidence["candidates"]:
        for field, item in candidate["fields"].items():
            if item["qualifier"] != "unknown":
                bound = manifest["sources"][item["source_id"]]
                source = state["documents"][bound["document_id"]]
                source_data = store._read(directory, "object-" + source["sha256"] + ".txt",
                                          session_state.MAX_DOCUMENT_BYTES).decode("utf-8")
                _require(item["quote"] in source_data,
                         "evidence quote is absent from registered source: " + field)
    journey_fields = {candidate["id"]: {item["source_id"] for item in candidate["fields"].values()
                      if item["qualifier"] != "unknown" and item.get("scope", {}).get("kind") == "journey"}
                      for candidate in evidence["candidates"]}
    journey_fields = {key: refs for key, refs in journey_fields.items() if refs}
    _require(type(manifest["journeys"]) is dict and set(manifest["journeys"]) == set(journey_fields),
             "journey alternatives are missing for a candidate")
    for candidate_id, refs in journey_fields.items():
        _require(len(refs) == 1, "candidate journey fields cite different source records")
        source_id = next(iter(refs))
        _require(source_id in raw_sources, "journey needs registered raw tool output")
        _check_journey(raw_sources[source_id], manifest["journeys"][candidate_id],
                       candidate_id, source_id)
        fields = next(row["fields"] for row in evidence["candidates"] if row["id"] == candidate_id)
        if "commute_minutes" in fields and fields["commute_minutes"]["qualifier"] != "unknown":
            _require(fields["commute_minutes"]["value"] == raw_sources[source_id].get("fastest_min"),
                     "commute field differs from fastest raw plan")
        if "arrives_by_0900" in fields and fields["arrives_by_0900"]["qualifier"] != "unknown":
            raw = raw_sources[source_id]
            _require(raw["query"].get("arrive_by") == "09:00"
                     and raw.get("fastest_plan") in ("all", "rail", "bus"),
                     "arrival field lacks a 09:00 fastest plan")
            arrival = raw["plans"][raw["fastest_plan"]].get("arrival")
            _require(type(arrival) is str and len(arrival) >= 16,
                     "fastest plan lacks an arrival timestamp")
            try:
                local_arrival = datetime.datetime.fromisoformat(arrival.replace("Z", "+00:00"))
                date = datetime.datetime.strptime(raw["query"]["date"], "%Y%m%d").date()
            except (TypeError, ValueError) as error:
                raise session_state.SessionStateError("fastest plan arrival is invalid") from error
            met = local_arrival.date() == date and local_arrival.time() <= datetime.time(9, 0)
            _require(fields["arrives_by_0900"]["value"] is met,
                     "arrival field differs from fastest raw plan")
    _require(type(manifest["pending_checks"]) is dict,
             "pending checks must be an object by candidate")
    candidate_ids = {row["id"] for row in evidence["candidates"]}
    _require(set(manifest["pending_checks"]) == candidate_ids,
             "pending checks must cover every compared candidate")
    for candidate in evidence["candidates"]:
        candidate_id, fields = candidate["id"], candidate["fields"]
        checks = manifest["pending_checks"][candidate_id]
        _require(type(checks) is dict and set(checks) >=
                 {field for field, item in fields.items() if item["qualifier"] == "unknown"},
                 "unknown fields lack concrete pending checks: " + candidate_id)
        open_ids = set(review["candidates"][candidate_id]["open_requirement_ids"])
        covered = set()
        for field, pending in checks.items():
            _require(field in fields and type(pending) is dict
                     and set(pending) == {"action", "needed", "requirement_ids"}
                     and pending["action"] in ("request_user_detail", "obtain_document",
                                                "inspect_property", "verify_source", "retain_hold")
                     and type(pending["needed"]) is str and len(pending["needed"].strip()) >= 12
                     and type(pending["requirement_ids"]) is list,
                     "pending check is not concrete: " + candidate_id + "/" + field)
            for requirement_id in pending["requirement_ids"]:
                _require(requirement_id in open_ids
                         and state["requirements"][requirement_id]["value"]["field"] == field,
                         "pending check requirement does not match its field")
                covered.add(requirement_id)
        _require(covered == open_ids,
                 "investigate TODO requirements lack field-specific pending checks: " + candidate_id)
    return {"fidelity_document_id": document_id, "fidelity_sha256": document["sha256"],
            "source_sha256": source_hashes,
            "pending_checks_sha256": eligibility.canonical_hash(manifest["pending_checks"]),
            "journeys_sha256": eligibility.canonical_hash(manifest["journeys"])}


def check(project, scope, *, evidence=None, output_id=None, fidelity_document_id=None):
    store = session_state.SessionStore(project)
    # This also checks the optional checkpoint, journal chain and source objects.
    store.verify()
    with store._locked() as directory:
        _, state = store._load(directory)
        _require(state["project_id"] is not None and state["revision"] > 0,
                 "formal project journal is missing")
        receipt = {"ok": True, "scope": scope, "project_id": state["project_id"],
                   "revision": state["revision"], "event_hash": state["event_hash"]}

        if scope in ("comparison", "comparison-full"):
            _require(evidence is not None, "comparison scope needs the saved evidence bundle")
            review = session_state._parse(store._read(directory, "boundary-review.json"))
            context = session_state._parse(store._read(directory, "boundary-context.json"))
            _require(isinstance(review, dict) and isinstance(context, dict),
                     "saved comparison artifacts are invalid")
            expected = boundary.evaluate(state, evidence)
            _require(expected["ready"] and eligibility.canonical_hash(review) == eligibility.canonical_hash(expected),
                     "saved comparison is stale or differs from current evidence/conditions")
            _require(context == store._context(state, 64000),
                     "saved comparison context differs from current project state")
            binding = review["binding"]
            _require(binding["revision"] == state["revision"] and binding["event_hash"] == state["event_hash"],
                     "saved comparison revision or event hash is stale")
            receipt.update(review_sha256=eligibility.canonical_hash(review),
                           evidence_sha256=binding["evidence_sha256"])
            if scope == "comparison-full":
                receipt.update(_check_fidelity(store, directory, state, evidence, review,
                                               fidelity_document_id))
        elif scope == "report":
            _require(output_id, "report scope needs the registered output ID")
            output = state["outputs"].get(output_id)
            _require(output and output["status"] == "current" and output["valid"],
                     "report output is missing or stale")
            document = state["documents"].get(output["document_id"])
            task = state["tasks"].get(output["task_id"])
            _require(document and document["status"] == "active" and document["valid"]
                     and document["provenance"]["actor"] == "assistant",
                     "registered assistant report document is missing or stale")
            quote = document["provenance"].get("quote")
            _require(quote and any(quote in excerpt["text"] for excerpt in document["excerpts"]),
                     "registered report quote is absent from its saved excerpt")
            _require(task and task["status"] == "completed" and task["valid"]
                     and output["document_id"] in task["evidence_ids"],
                     "report task has not validated its saved document")
            current_bytes = _current_report_bytes(store, document["path"])
            _require(len(current_bytes) == document["byte_length"]
                     and hashlib.sha256(current_bytes).hexdigest() == document["sha256"],
                     "current report file differs from its registered snapshot")
            receipt.update(output_id=output_id, document_id=output["document_id"],
                           document_sha256=document["sha256"], task_id=output["task_id"])
        else:
            raise session_state.SessionStateError("unknown save scope")
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--scope", choices=("comparison", "comparison-full", "report"), required=True)
    parser.add_argument("--evidence", type=Path, help="private evidence JSON used for the comparison")
    parser.add_argument("--output-id", help="registered output ID for a completed report")
    parser.add_argument("--fidelity-document-id", help="registered source/plan/TODO fidelity document ID for comparison-full")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        _require((args.scope in ("comparison", "comparison-full")) == bool(args.evidence),
                 "comparison scopes require --evidence; report uses --output-id instead")
        _require((args.scope == "report") == bool(args.output_id),
                 "report requires --output-id; comparison uses --evidence instead")
        _require((args.scope == "comparison-full") == bool(args.fidelity_document_id),
                 "comparison-full requires --fidelity-document-id; other scopes do not")
        evidence = eligibility._read(args.evidence) if args.evidence else None
        result = check(args.project, args.scope, evidence=evidence, output_id=args.output_id,
                       fidelity_document_id=args.fidelity_document_id)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "scope": args.scope, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), file=sys.stdout if args.json else sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
