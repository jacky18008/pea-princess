#!/usr/bin/env python3
"""Check whether a claimed comparison or report is current in private state.

This is a read-only verification of recorded bytes and their revision, not a
source-truth, consent, or external-action check. Run it just before saying that
work has been saved. It does not initialize state or repair a failed save.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import boundary
import eligibility
import session_state


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


def check(project, scope, *, evidence=None, output_id=None):
    store = session_state.SessionStore(project)
    # This also checks the optional checkpoint, journal chain and source objects.
    store.verify()
    with store._locked() as directory:
        _, state = store._load(directory)
        _require(state["project_id"] is not None and state["revision"] > 0,
                 "formal project journal is missing")
        receipt = {"ok": True, "scope": scope, "project_id": state["project_id"],
                   "revision": state["revision"], "event_hash": state["event_hash"]}

        if scope == "comparison":
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
    parser.add_argument("--scope", choices=("comparison", "report"), required=True)
    parser.add_argument("--evidence", type=Path, help="private evidence JSON used for the comparison")
    parser.add_argument("--output-id", help="registered output ID for a completed report")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        _require((args.scope == "comparison") == bool(args.evidence),
                 "comparison requires --evidence; report uses --output-id instead")
        _require((args.scope == "report") == bool(args.output_id),
                 "report requires --output-id; comparison uses --evidence instead")
        evidence = eligibility._read(args.evidence) if args.evidence else None
        result = check(args.project, args.scope, evidence=evidence, output_id=args.output_id)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "scope": args.scope, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), file=sys.stdout if args.json else sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
