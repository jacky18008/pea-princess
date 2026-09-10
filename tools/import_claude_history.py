#!/usr/bin/env python3
"""Export explicitly selected Claude JSONL records to a private, offline archive.

This is a record-order view, not a reconstruction of the canonical UI or a branch.
Only stdlib is used. Source text is data: it is never executed or rendered as HTML.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys


SCHEMA_VERSION = 2
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
INTERPRETATION = (
    "Record-order archive, not proof of canonical UI order or a single branch. "
    "Parent and logical-parent edges are descriptive. Siblings can be parallel "
    "assistant blocks, queued inputs, revisions, or branches; a fork does not prove "
    "an alternative conversation. No siblings are merged or continuation invented."
)
VISIBILITY = (
    "All recognized visible text in the selected records is retained exactly. "
    "Selection completeness and original UI visibility are unknown; heuristics can "
    "misclassify text. Controls and hidden/tool content are separate evidence. "
    "Images and documents have not received visual review; binary payloads remain "
    "only in raw snapshots. This archive is private by filesystem permissions, "
    "not encrypted or an access-control boundary against the same user."
)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_id(value, label):
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError("unsafe %s" % label)
    return value


def _path(value, base=None):
    path = Path(value).expanduser()
    if ".." in path.parts:
        raise ValueError("parent traversal is not allowed")
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    # Do not resolve first: that would hide symlink ancestors.
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError("symlink path is not allowed: %s" % part)
    return path.absolute()


def _regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("source must be a regular file: %s" % path)
    return info


def _signature(info):
    return {key: getattr(info, key) for key in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size",
        "st_mtime_ns", "st_ctime_ns")}


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mkdir(path):
    if path.exists():
        if not path.is_dir() or path.is_symlink():
            raise ValueError("unsafe directory: %s" % path)
        return
    _mkdir(path.parent)
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _new_file(path, binary=False):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8", "newline": ""}))


def _write(path, content):
    with _new_file(path) as stream:
        stream.write(content)


def _write_json(path, value):
    _write(path, _json(value) + "\n")


def _copy_stream(source_stream, destination_stream):
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: source_stream.read(1024 * 1024), b""):
        destination_stream.write(chunk)
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _snapshot_source(source_path, raw_destination):
    source_path = _path(source_path)
    before = _signature(_regular(source_path))
    fd = os.open(str(source_path), os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as source:
        if _signature(os.fstat(source.fileno())) != before:
            raise ValueError("source changed before snapshot")
        with _new_file(raw_destination, binary=True) as target:
            digest, size = _copy_stream(source, target)
            target.flush()
            os.fsync(target.fileno())
        if _signature(os.fstat(source.fileno())) != before:
            raise ValueError("source changed during snapshot")
    receipt = {"path": str(source_path), "sha256": digest, "bytes": size, "stat": before}
    _verify_source(receipt)
    if _hash(raw_destination) != digest:
        raise ValueError("raw snapshot hash mismatch")
    return receipt


def _verify_source(receipt):
    path = _path(receipt["path"])
    if _signature(_regular(path)) != receipt["stat"] or _hash(path) != receipt["sha256"]:
        raise ValueError("source changed; export cannot attest a stable snapshot")
    if _signature(_regular(path)) != receipt["stat"]:
        raise ValueError("source changed during verification")


def _git(args, cwd):
    return subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(cwd), *args],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, check=False)


def _check_destination(path):
    if path.exists():
        raise ValueError("destination already exists; overwrite is forbidden")
    ancestor = path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    found = _git(["rev-parse", "--show-toplevel"], ancestor)
    if found.returncode:
        return  # Explicit external private directory, created below with mode 0700.
    root = Path(found.stdout.strip()).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return
    if not relative.parts or relative.parts[0] != ".pea-playground":
        raise ValueError("repository destination must be under ignored .pea-playground")
    ignored = _git(["check-ignore", "-q", "--", relative.as_posix()], root)
    tracked = _git(["ls-files", "-z", "--", relative.as_posix()], root)
    if ignored.returncode != 0 or tracked.returncode != 0 or tracked.stdout:
        raise ValueError("repository destination must be Git ignored and untracked")


def _fence(text, language="text"):
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return fence + language + "\n" + text + ("" if text.endswith("\n") else "\n") + fence + "\n\n"


def _provenance(record, line, block_index=None):
    message = record.get("message")
    message = message if isinstance(message, dict) else {}
    return {"source_line": line, "uuid": record.get("uuid"),
            "parentUuid": record.get("parentUuid"), "logicalParentUuid": record.get("logicalParentUuid"),
            "timestamp": record.get("timestamp"), "model": message.get("model", record.get("model")),
            "effort": record.get("effort", message.get("effort")),
            "message_id": message.get("id"), "block_index": block_index,
            "apiBlockIndex": record.get("apiBlockIndex"), "isSidechain": record.get("isSidechain"),
            "record_type": record.get("type")}


def _entry(record, line, kind, confidence="explicit", block_index=None, **values):
    return {**_provenance(record, line, block_index), "kind": kind, "confidence": confidence, **values}


def _control_reason(record, text):
    if record.get("isSidechain") is True:
        return "sidechain", "explicit"
    if record.get("isApiErrorMessage") is True:
        return "api_error", "explicit"
    message = record.get("message", {})
    model = message.get("model", record.get("model")) if isinstance(message, dict) else record.get("model")
    if isinstance(model, str) and model.lower() in {"<synthetic>", "synthetic"}:
        return "synthetic_message", "explicit"
    if record.get("isCompactSummary") is True:
        return "compact_summary", "explicit"
    if record.get("isMeta") is True:
        return "meta", "explicit"
    origin = record.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return "machine_origin", "explicit"
    queued = record.get("attachment")
    queued = isinstance(queued, dict) and queued.get("type") == "queued_command"
    if record.get("type") == "user" or queued:
        start = text.lstrip().lower()
        markers = ("<local-command", "<command-name", "<command-message", "<stdout",
                   "<task-notification", "<system-reminder", "[request interrupted",
                   "request interrupted", "this session is being continued from a previous conversation",
                   "this conversation is being continued from a previous conversation")
        if start.startswith(markers):
            return "leading_control_marker", "heuristic"
    return None


def _attachment(block):
    source = block.get("source")
    source = source if isinstance(source, dict) else {}
    # No payload copying or fetching; even unknown encodings stay in the raw file.
    metadata = {"type": block.get("type"), "visual_review": "missing",
                "binary_payload_location": "raw/source.jsonl only"}
    for key in ("media_type", "type"):
        if isinstance(source.get(key), str):
            metadata["source_" + key if key == "type" else key] = source[key]
    for key in ("title", "filename", "name"):
        if isinstance(block.get(key), str):
            metadata[key] = block[key]
    return metadata


def _entries(record, line):
    """Yield (visible, entry); controls remain separately indexed evidence."""
    role = record.get("type")
    attachment = record.get("attachment")
    if role == "attachment" and isinstance(attachment, dict) and attachment.get("type") == "queued_command":
        prompt = attachment.get("prompt")
        blocks = [{"type": "text", "text": prompt}] if isinstance(prompt, str) else prompt
        if isinstance(blocks, list):
            origin = attachment.get("origin")
            origin = origin if isinstance(origin, dict) else {}
            origin_kind = origin.get("kind")
            human = origin_kind == "human"
            unknown = origin_kind is None
            kind = "queued_human_input" if human else "queued_input_unknown" if unknown else "queued_machine_input"
            source_uuid = attachment.get("source_uuid", record.get("source_uuid"))
            metadata = {"attachment_timestamp": attachment.get("timestamp"), "origin": origin,
                        "source_uuid": source_uuid, "queued_input_kind": kind,
                        "representation_relation": (
                            "references source_uuid; not proof of an independent input" if source_uuid else None)}
            first_text = next((block["text"] for block in blocks if isinstance(block, dict)
                               and block.get("type") == "text" and isinstance(block.get("text"), str)), "")
            record_reason = _control_reason(record, first_text)
            for index, block in enumerate(blocks):
                block_index = None if isinstance(prompt, str) else index
                if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                    reason = record_reason or _control_reason(record, block["text"])
                    yield (human or unknown) and reason is None, _entry(
                        record, line, reason[0] if reason else kind,
                        reason[1] if reason else "unknown" if unknown else "explicit", block_index,
                        text=block["text"], **metadata)
                elif isinstance(block, dict) and block.get("type") in ("image", "document"):
                    yield (human or unknown) and record_reason is None, _entry(
                        record, line, "attachment", "unknown" if unknown else "explicit", block_index,
                        attachment=_attachment(block), visibility_reason=record_reason, **metadata)
                else:
                    yield False, _entry(record, line, "unrecognized_queued_block", "unknown", block_index,
                                        block_type=block.get("type") if isinstance(block, dict) else None, **metadata)
            return
    if role not in ("user", "assistant"):
        values = {}
        if isinstance(record.get("content"), str):
            values["text"] = record["content"]
        yield False, _entry(record, line, "control_event", event_type=role, **values)
        return
    message = record.get("message")
    if not isinstance(message, dict):
        yield False, _entry(record, line, "unrecognized_message", "unknown")
        return
    content = message.get("content")
    blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
    if not isinstance(blocks, list):
        yield False, _entry(record, line, "unrecognized_content", "unknown")
        return
    first_text = next((block["text"] for block in blocks if isinstance(block, dict)
                       and block.get("type") == "text" and isinstance(block.get("text"), str)), "")
    record_reason = _control_reason(record, first_text)
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            yield False, _entry(record, line, "unrecognized_block", "unknown", index)
            continue
        kind = block.get("type")
        if kind == "text" and isinstance(block.get("text"), str):
            text = block["text"]
            reason = record_reason or _control_reason(record, text)
            if reason:
                yield False, _entry(record, line, reason[0], reason[1], index, text=text)
            else:
                yield True, _entry(record, line, "human_input" if role == "user" else "assistant_text",
                                  "inferred_role", index, text=text)
        elif kind in ("image", "document"):
            reason = record_reason
            yield reason is None, _entry(record, line, "attachment", block_index=index,
                                        attachment=_attachment(block), visibility_reason=reason)
        else:
            values = {"block_type": kind}
            # Text controls are searchable evidence, never included as ordinary prompts.
            if kind == "thinking" and isinstance(block.get("thinking"), str):
                values["text"] = block["thinking"]
            elif kind == "tool_result" and isinstance(block.get("content"), str):
                values["text"] = block["content"]
            yield False, _entry(record, line, kind if isinstance(kind, str) else "unknown_block",
                                "explicit" if kind else "unknown", index, **values)


def _lineage(nodes):
    by_id = {node["uuid"]: node for node in nodes}
    edges, roots, missing, compact = [], [], [], []
    children, groups = defaultdict(list), defaultdict(list)
    for node in nodes:
        uid = node["uuid"]
        parent = node["parentUuid"]
        if parent is None:
            roots.append(uid)
        for relation in ("parentUuid", "logicalParentUuid"):
            target = node[relation]
            if target is not None:
                edge = {"from": target, "to": uid, "relation": relation}
                edges.append(edge)
                if target not in by_id:
                    missing.append(edge)
        if parent is not None:
            children[parent].append(uid)
        if node["compact_boundary"]:
            compact.append({key: node[key] for key in ("uuid", "source_line", "parentUuid", "logicalParentUuid", "preservedSegment")})
        if node["message_id"] is not None:
            groups[node["message_id"]].append({"uuid": uid, "source_line": node["source_line"], "apiBlockIndex": node["apiBlockIndex"]})
    done, cycles = set(), []
    for start in by_id:
        path, positions = [], {}
        current = start
        while current in by_id and current not in done:
            if current in positions:
                cycles.append(path[positions[current]:])
                break
            positions[current] = len(path)
            path.append(current)
            current = by_id[current]["parentUuid"]
        done.update(path)
    return {"interpretation": INTERPRETATION, "nodes": nodes, "edges": edges, "roots": roots,
            "forks": [{"parentUuid": key, "children": value, "meaning": "structural siblings; branch meaning unknown"}
                      for key, value in children.items() if len(value) > 1],
            "missing_parents": missing, "compact_boundaries": compact,
            "message_id_groups": [{"message_id": key, "records": value} for key, value in groups.items()],
            "cycles": cycles}


def _export_session(session, source, folder):
    _mkdir(folder / "raw")
    receipt = _snapshot_source(source, folder / "raw/source.jsonl")
    counts = Counter()
    malformed, warnings, nodes, seen = [], [], [], set()
    with _new_file(folder / "messages.jsonl") as messages, _new_file(folder / "controls.jsonl") as controls, \
            _new_file(folder / "conversation.md") as markdown, (folder / "raw/source.jsonl").open("rb") as raw:
        markdown.write("# Session " + session + "\n\n" + INTERPRETATION + "\n\n" + VISIBILITY + "\n\n")
        markdown.write("[Lineage](lineage.json) · [Exact visible records](messages.jsonl) · "
                       "[Controls/evidence index](controls.jsonl) · [Immutable raw snapshot](raw/source.jsonl)\n\n")
        offset = 0
        for line_number, data in enumerate(raw, 1):
            counts["source_lines"] += 1
            try:
                record = json.loads(data.decode("utf-8"))
                if not isinstance(record, dict):
                    raise ValueError("JSON line is not an object")
            except (UnicodeDecodeError, ValueError) as error:
                issue = {"source_line": line_number, "byte_offset": offset, "bytes": len(data),
                         "reason": type(error).__name__ + ": " + str(error)[:160]}
                malformed.append(issue)
                controls.write(_json({**issue, "kind": "malformed_line", "confidence": "explicit"}) + "\n")
                offset += len(data)
                continue
            offset += len(data)
            uid = record.get("uuid")
            for field in ("uuid", "parentUuid", "logicalParentUuid"):
                if record.get(field) is not None:
                    _safe_id(record[field], field)
            if uid is not None:
                if uid in seen:
                    raise ValueError("duplicate record UUID in selected session %s at line %d" % (session, line_number))
                seen.add(uid)
                compact = record.get("compactMetadata")
                compact = compact if isinstance(compact, dict) else {}
                node = {**{key: value for key, value in _provenance(record, line_number).items()
                           if key in ("uuid", "source_line", "parentUuid", "logicalParentUuid", "message_id", "apiBlockIndex")},
                        "type": record.get("type"), "preservedSegment": record.get("preservedSegment", compact.get("preservedSegment")),
                        "compact_boundary": record.get("subtype") == "compact_boundary" or record.get("isCompactSummary") is True
                            or (record.get("parentUuid") is None and record.get("logicalParentUuid") is not None)}
                nodes.append(node)
            counts["records"] += 1
            for visible, entry in _entries(record, line_number):
                entry["source_session_id"] = session
                entry["raw_path"] = "raw/source.jsonl"
                counts[entry["kind"]] += 1
                if visible:
                    counts["visible_entries"] += 1
                    if uid is None:
                        warnings.append({"source_line": line_number, "reason": "visible record has no UUID"})
                    messages.write(_json(entry) + "\n")
                    markdown.write("## Source line %d · %s\n\n" % (line_number, entry["kind"]))
                    metadata = {key: value for key, value in entry.items() if key not in ("text", "attachment")}
                    markdown.write(_fence(_json(metadata), "json"))
                    if "text" in entry:
                        markdown.write(_fence(entry["text"]))
                    if "attachment" in entry:
                        markdown.write(_fence(_json(entry["attachment"]), "json"))
                else:
                    counts["control_entries"] += 1
                    controls.write(_json(entry) + "\n")
        if not counts["source_lines"]:
            markdown.write("No source records. This selected source is empty; derived completeness is false.\n")
        if malformed:
            markdown.write("\n%d malformed lines remain only in the raw snapshot and evidence index.\n" % len(malformed))
    lineage = _lineage(nodes)
    _write_json(folder / "lineage.json", lineage)
    audit = {"schema_version": SCHEMA_VERSION, "session_id": session, "source": receipt,
             "complete": bool(counts["records"]) and not malformed,
             "complete_meaning": "nonempty selected source parsed; not proof of complete history or UI visibility",
             "visibility_complete": "unknown", "malformed_lines": malformed, "warnings": warnings,
             "counts": dict(counts), "interpretation": INTERPRETATION,
             "human_count_meaning": "archived classified input entries, not independent rounds; source_uuid relations can repeat representations",
             "files": {path.relative_to(folder).as_posix(): {"sha256": _hash(path), "bytes": path.stat().st_size}
                       for path in sorted(folder.rglob("*")) if path.is_file()}}
    _write_json(folder / "audit.json", audit)
    return audit


def export_history(manifest_path, destination):
    """Create a new private export from an explicit sources manifest; never scan history."""
    manifest_path = _path(manifest_path)
    _regular(manifest_path)
    manifest_data = manifest_path.read_bytes()
    manifest = json.loads(manifest_data.decode("utf-8"))
    sources = manifest.get("sources") if isinstance(manifest, dict) else None
    if not isinstance(sources, list) or not sources:
        raise ValueError("manifest must contain a nonempty sources list")
    destination = _path(destination)
    _check_destination(destination)
    chosen, ids, paths = [], set(), set()
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("each selected source requires path and session_id")
        session = _safe_id(item.get("session_id"), "session_id")
        source = _path(item["path"], manifest_path.parent)
        info = _regular(source)
        identity = (info.st_dev, info.st_ino)
        if session in ids or identity in paths:
            raise ValueError("duplicate selected session or source")
        ids.add(session)
        paths.add(identity)
        chosen.append((session, source))
    _mkdir(destination.parent)
    destination.mkdir(mode=0o700)  # Exclusive creation also rejects a concurrent destination.
    destination.chmod(0o700)
    try:
        manifest_receipt = _snapshot_source(manifest_path, destination / "selected-sources.json")
        if manifest_receipt["sha256"] != hashlib.sha256(manifest_data).hexdigest():
            raise ValueError("selected sources manifest changed before snapshot")
        audits = [_export_session(session, source, destination / "sessions" / session) for session, source in chosen]
        # Recheck every source after the whole batch, not only immediately after copying.
        for audit in audits:
            _verify_source(audit["source"])
            raw = destination / "sessions" / audit["session_id"] / "raw/source.jsonl"
            if _hash(raw) != audit["source"]["sha256"]:
                raise ValueError("raw snapshot changed during export")
        _verify_source(manifest_receipt)
        totals = Counter()
        for audit in audits:
            totals.update(audit["counts"])
        complete = all(audit["complete"] for audit in audits)
        intro = "# Private Claude record archive\n\n" + INTERPRETATION + "\n\n" + VISIBILITY + "\n\n"
        listing = "\n".join("- [%s](sessions/%s/conversation.md): %d visible entries; %d malformed lines."
                            % (audit["session_id"], audit["session_id"], audit["counts"].get("visible_entries", 0), len(audit["malformed_lines"]))
                            for audit in audits) + "\n"
        _write(destination / "index.md", intro + listing)
        _write(destination / "README.md", intro + "Open [the session index](index.md). "
               "`messages.jsonl` preserves exact parsed visible text and source anchors; "
               "`controls.jsonl` is evidence, not ordinary prompts. `lineage.json` describes "
               "physical and logical relationships without selecting a branch. "
               "Raw copies are never rewritten; audit SHA-256 hashes detect later changes. "
               "No attachment has been opened, fetched, decoded, or visually reviewed.\n\n" + listing)
        audit = {"schema_version": SCHEMA_VERSION, "complete": complete, "visibility_complete": "unknown",
                 "selected_manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
                 "counts": dict(totals), "sessions": [{"session_id": item["session_id"],
                     "source_sha256": item["source"]["sha256"], "audit_sha256": _hash(destination / "sessions" / item["session_id"] / "audit.json")}
                     for item in audits], "interpretation": INTERPRETATION, "visibility": VISIBILITY}
        _write_json(destination / "audit.json", audit)
        return {"ok": True, "output": str(destination), "sessions": len(audits), "complete": complete,
                "counts": dict(totals), "audit_sha256": _hash(destination / "audit.json")}
    except Exception:
        # Retain any private partial snapshots for diagnosis; never retry or overwrite.
        failure = destination / "INCOMPLETE.txt"
        if not failure.exists():
            _write(failure, "Export failed. This directory is incomplete and must not be treated as a verified archive.\n")
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True, type=Path, help="explicit selected-sources JSON manifest")
    parser.add_argument("--output", required=True, type=Path, help="new private destination (never overwritten)")
    args = parser.parse_args(argv)
    try:
        result = export_history(args.sources, args.output)
    except (OSError, ValueError, TypeError) as error:
        print("import_claude_history: " + str(error), file=sys.stderr)
        return 2
    print(_json(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
