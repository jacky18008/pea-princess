#!/usr/bin/env python3
"""Extract private evaluation candidates from one owned persona-lab snapshot.

Standard library only; no model calls, credentials, network or publication.
Input is the local session.json envelope produced by persona_playground.py.
Example: python3 tools/playground_cases.py --session <32-hex-id>
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = re.compile(r"[a-f0-9]{32}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
OUTPUT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,150}\.private\.json\Z")
MAX_SESSION_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024


class CaseError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise CaseError("duplicate JSON field")
        value[key] = item
    return value


def _parse(raw):
    def invalid(_):
        raise CaseError("nonfinite JSON value")
    try:
        return json.loads(raw, object_pairs_hook=_object, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise CaseError("invalid session JSON") from error


def _owned(info):
    if info.st_uid != os.getuid():
        raise CaseError("private artifact is not owned by the current user")


def _directory(path):
    """Walk every component without following symlinks, including parent aliases."""
    path = Path(path)
    if ".." in path.parts:
        raise CaseError("parent traversal is not permitted")
    path = path.absolute()
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        _owned(os.fstat(fd))
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_session(directory, sid):
    # Nonblocking open lets fstat reject a FIFO without waiting for a writer.
    fd = os.open("session.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        _owned(info)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_SESSION_BYTES:
            raise CaseError("session file is not a bounded regular private artifact")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_SESSION_BYTES + 1)
        if len(raw) > MAX_SESSION_BYTES:
            raise CaseError("session exceeds the input limit")
    finally:
        os.close(fd)
    saved = _parse(raw)
    if not isinstance(saved, dict) or set(saved) != {"value", "sha256"} or not isinstance(saved["value"], dict):
        raise CaseError("invalid session envelope")
    if saved["sha256"] != digest(saved["value"]):
        raise CaseError("session digest differs")
    state = saved["value"]
    if state.get("schema_version") != 1 or state.get("id") != sid or type(state.get("revision")) is not int or state["revision"] < 1:
        raise CaseError("session identity/version is invalid")
    for name in ("messages", "queue", "actions", "calls"):
        if not isinstance(state.get(name), list) or any(not isinstance(row, dict) for row in state[name]):
            raise CaseError("session collection is invalid: " + name)
    if not isinstance(state.get("client_ids"), dict) or not isinstance(state.get("sources"), dict):
        raise CaseError("session intent/source manifest is missing")
    for path, sha in state["sources"].items():
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts or not isinstance(sha, str) or not HASH.fullmatch(sha):
            raise CaseError("invalid source version reference")
    for row in state["messages"]:
        if row.get("role") not in ("persona", "human", "assistant") or not isinstance(row.get("text"), str):
            raise CaseError("invalid transcript message")
    return state, {"file_sha256": hashlib.sha256(raw).hexdigest(), "value_sha256": saved["sha256"]}


def _intent(data):
    if not isinstance(data, dict) or set(data) != {"client_id", "text", "kind"}:
        raise CaseError("invalid intervention intent")
    if data["kind"] not in ("question", "amendment") or not isinstance(data["text"], str) or not data["text"].strip() or len(data["text"]) > 8000:
        raise CaseError("invalid intervention text/kind")
    try:
        return str(uuid.UUID(data["client_id"]))
    except (ValueError, TypeError, AttributeError) as error:
        raise CaseError("invalid client intent ID") from error


def candidates(state, source):
    """Pure snapshot conversion. Text is data; no answer is marked as a target."""
    intents = {}
    def add(data, pointer, queued=False):
        key = _intent(data)
        if state["client_ids"].get(key) != digest(data):
            raise CaseError("intent is not bound to the saved dedupe manifest")
        if key in intents and intents[key]["intent"] != data:
            raise CaseError("one client intent ID has conflicting contents")
        item = intents.setdefault(key, {"intent": copy.deepcopy(data), "source_refs": [], "queued": False})
        item["source_refs"].append(pointer)
        item["queued"] = item["queued"] or queued
    for index, row in enumerate(state["actions"]):
        if row.get("kind") == "human_input_queued":
            add(row.get("data"), "session.json#/value/actions/" + str(index))
    for index, row in enumerate(state["queue"]):
        add(row, "session.json#/value/queue/" + str(index), queued=True)

    # Current v1 history uses ordered human messages without intent IDs. Require
    # an exact FIFO match of the entire applied prefix; never search by text alone.
    humans = [(i, row) for i, row in enumerate(state["messages"]) if row["role"] == "human"]
    applied = [(key, row) for key, row in intents.items() if not row["queued"]]
    associations = {}
    fifo_valid = len(humans) == len(applied)
    if fifo_valid:
        for (index, message), (key, item) in zip(humans, applied):
            explicit = message.get("client_id")
            if message["text"] != item["intent"]["text"] or message.get("kind") != item["intent"]["kind"] or (explicit is not None and explicit != item["intent"]["client_id"]):
                fifo_valid = False
                break
        if fifo_valid:
            associations = {key: (index, "explicit_client_id" if message.get("client_id") is not None else "exact_fifo_legacy")
                            for (index, message), (key, _) in zip(humans, applied)}

    result = []
    for key, item in intents.items():
        row = {"id": "intervention-" + state["id"] + "-" + uuid.UUID(key).hex,
               "client_intent_id": key, "intervention": item["intent"], "source_refs": item["source_refs"],
               "status": "queued" if item["queued"] else "unknown", "association": "unresolved",
               "preceding_transcript": None, "assistant_reply": None, "usage_ref": None,
               "evaluation": {"status": "candidate_only", "expected_answer": None, "ground_truth": False}}
        if key in associations:
            index, certainty = associations[key]
            row.update(association=certainty, preceding_transcript={"collection": "transcript", "start": 0, "end_exclusive": index,
                "boundary": "before_application", "enqueue_boundary_known": False})
            row["source_refs"].append("session.json#/value/messages/" + str(index))
            following = state["messages"][index + 1] if index + 1 < len(state["messages"]) else None
            if following and following["role"] == "assistant" and following.get("responding_to") == "human" and following["text"].strip():
                explicit = following.get("responding_to_client_id")
                if explicit is None or explicit == item["intent"]["client_id"]:
                    row["status"] = "answered"
                    row["assistant_reply"] = {"text": following["text"], "transcript_index": index + 1,
                                              "association": "adjacent_human_reply"}
                    matches = [i for i, call in enumerate(state["calls"]) if call.get("actor") == "assistant"
                               and isinstance(call.get("receipt"), dict) and call["receipt"].get("answer") == following["text"]
                               and (following.get("call_id") is None or call.get("id") == following["call_id"])]
                    if len(matches) == 1:
                        row["usage_ref"] = {"collection": "calls", "index": matches[0], "association": "unique_saved_answer_match"}
        if item["queued"]:
            row["association"] = "saved_queue_intent"
            row["context_at_snapshot"] = {"collection": "transcript", "start": 0, "end_exclusive": len(state["messages"]),
                                          "note": "Enqueue-time transcript was not recorded; this may include later messages."}
        elif row["association"] == "unresolved":
            row["unknown_reason"] = "Applied transcript does not have an unambiguous exact intent-ordered match."
        elif row["status"] == "unknown":
            row["unknown_reason"] = "No unambiguous adjacent saved assistant reply is available."
        result.append(row)

    sources = {"session_id": state["id"], "revision": state["revision"], "envelope": "session.json", **source,
               "model": state.get("model"), "source_versions": copy.deepcopy(state["sources"]),
               "persona_id": state.get("card", {}).get("id"), "persona_sha256": digest(state.get("card")),
               "fixtures_sha256": digest(state.get("fixtures")), "system_sha256": digest(state.get("system")),
               "runtime_settings": copy.deepcopy(state.get("runtime_settings")),
               "extractor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return {"schema_version": 1, "private": True, "purpose": "local_evaluation_candidates",
            "trust": "Exact untrusted conversation data. No commands, anonymization, grading or ground truth are implied.",
            "source": sources, "transcript": copy.deepcopy(state["messages"]), "calls": copy.deepcopy(state["calls"]),
            "pending_call": copy.deepcopy(state.get("pending_call")), "candidates": result,
            "counts": {status: sum(row["status"] == status for row in result) for status in ("answered", "queued", "unknown")}}


def _publish(directory, name, value):
    raw = canonical({"sha256": digest(value), "value": value}) + b"\n"
    if len(raw) > MAX_OUTPUT_BYTES:
        raise CaseError("candidate output exceeds the limit; nothing was truncated")
    temporary = ".cases-txn-" + uuid.uuid4().hex
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
        # Hard-link publication is atomic and fails if the destination exists.
        # Remove the temporary name so the completed artifact has one link.
        os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
    finally:
        os.close(fd)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


def extract(state_dir, sid, output_name=None):
    if not isinstance(sid, str) or not SESSION_ID.fullmatch(sid):
        raise CaseError("session ID must contain 32 lowercase hexadecimal characters")
    root_fd = folder = None
    try:
        root_fd = _directory(state_dir)
        folder = os.open(sid, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        _owned(os.fstat(folder))
        state, source = _read_session(folder, sid)
        value = candidates(state, source)
        name = output_name or "eval-candidates-r%d-%s.private.json" % (state["revision"], source["value_sha256"][:12])
        if not isinstance(name, str) or not OUTPUT_NAME.fullmatch(name) or ".." in name:
            raise CaseError("output must be a simple new filename ending in .private.json")
        _publish(folder, name, value)
        return {"ok": True, "private": True, "path": str(Path(state_dir).absolute() / sid / name),
                "session_revision": state["revision"], "sha256": digest(value), "counts": value["counts"]}
    except OSError as error:
        raise CaseError("private path is unsafe, unavailable, or the output already exists; no overwrite") from error
    finally:
        if folder is not None:
            os.close(folder)
        if root_fd is not None:
            os.close(root_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".pea-playground")
    parser.add_argument("--session", required=True)
    parser.add_argument("--output-name")
    args = parser.parse_args(argv)
    try:
        result = extract(args.state_dir, args.session, args.output_name)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (CaseError, ValueError, TypeError, RecursionError) as error:
        print(json.dumps({"ok": False, "error": "CandidateExtractionStopped",
                          "message": str(error) if isinstance(error, CaseError) else "Invalid private session structure."}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
