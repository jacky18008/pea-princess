"""Extract fixed human replay turns and copy only their recorded local evidence.

Standard library only. No model calls, shell evaluation, original-path reads,
network access or publication. extract_turns(session) is pure; the caller owns
source-session integrity and idle-state checks. clone_input_files(source, target,
turn["inputs"]) verifies immutable supplied-files snapshots for one chosen turn.
Source assistant prose is returned separately for comparison. Original form
controls accompany historical answers only as verifiable, inert lineage.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import playground_attachments as attachments
import conversation_reply


MAX_MESSAGES = 2000
MAX_INPUT_CHARS = 8000
MAX_FILES = 48
CALL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
FILE_FIELDS = {"id", "name", "bytes", "sha256", "path", "image", "source_kind"}
OPTIONAL_FILE_FIELDS = {"original_path", "mime_type"}
INPUT_FIELDS = {"text", "kind", "attachments", "attachment_only_default", "intent_text", "clarification_receipt", "clarification_source"}


class ReplayError(ValueError):
    """The saved replay input or selected evidence cannot be used safely."""


def _clarification_source(value):
    """Validate inert controls captured by extraction, never supplied by a client."""
    if (type(value) is not dict or set(value) != {"call_id", "questions"}
            or type(value["call_id"]) is not str or not CALL_ID.fullmatch(value["call_id"])):
        raise ReplayError("invalid original clarification controls")
    try:
        conversation_reply.decode(json.dumps({"message": "Recorded controls.", "questions": value["questions"]}))
    except (ValueError, TypeError) as error:
        raise ReplayError("invalid original clarification controls") from error
    return copy.deepcopy(value)


def _replayed_clarification_source(session, row, offset):
    """Resolve a historical click against the host-frozen replay input.

    The caller verifies saved-session integrity. Matching the exact original
    input prevents a new answer from being attributed to these old controls.
    New replay assistant wording is deliberately never used as a fallback.
    """
    replay = session.get("replay")
    turn = row.get("replay_turn")
    if type(replay) is not dict or type(turn) is not int or turn < 1 or type(replay.get("turns")) is not list:
        raise ReplayError("saved clarification has no original replay turn")
    matches = [item for item in replay["turns"] if type(item) is dict
               and type(item.get("index")) is int and item["index"] == turn]
    if len(matches) != 1 or type(matches[0].get("inputs")) is not list or offset >= len(matches[0]["inputs"]):
        raise ReplayError("saved clarification has no original replay input")
    original = matches[0]["inputs"][offset]
    if type(original) is not dict or any(row.get(key, "question" if key == "kind" else None) != original.get(key, "question" if key == "kind" else None)
                                       for key in ("text", "kind", "intent_text", "clarification_receipt")):
        raise ReplayError("saved clarification differs from the frozen replay input")
    return _clarification_source(original.get("clarification_source"))


def _file(row):
    if not isinstance(row, dict) or not FILE_FIELDS.issubset(row) or set(row) - FILE_FIELDS - OPTIONAL_FILE_FIELDS:
        raise ReplayError("invalid recorded replay attachment fields")
    if not isinstance(row["id"], str) or not attachments.ID.fullmatch(row["id"]):
        raise ReplayError("invalid recorded replay attachment ID")
    try:
        attachments._name(row["name"])
    except attachments.AttachmentError as error:
        raise ReplayError(str(error)) from error
    if type(row["bytes"]) is not int or not 0 <= row["bytes"] <= attachments.MAX_ATTACHMENT_BYTES:
        raise ReplayError("recorded replay attachment exceeds the byte limit")
    if not isinstance(row["sha256"], str) or not attachments.HASH.fullmatch(row["sha256"]):
        raise ReplayError("invalid recorded replay attachment digest")
    if type(row["image"]) is not bool or row["source_kind"] not in ("upload", "local_path"):
        raise ReplayError("invalid recorded replay attachment type")
    for field, maximum in (("path", 4096), ("original_path", 4096), ("mime_type", 255)):
        if field not in row:
            continue
        value = row[field]
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or attachments._controls(value):
            raise ReplayError("invalid recorded replay attachment " + field)
        if field in ("path", "original_path") and not Path(value).is_absolute():
            raise ReplayError("recorded replay attachment paths must be absolute")
    if ".." in Path(row["path"]).parts:
        raise ReplayError("recorded replay attachment path contains traversal")
    return copy.deepcopy(row)


def _input(row, strict=False):
    if not isinstance(row, dict) or (strict and set(row) - INPUT_FIELDS):
        raise ReplayError("invalid saved human replay input")
    text, kind, files = row.get("text"), row.get("kind", "question"), row.get("attachments", [])
    if not isinstance(text, str) or len(text) > MAX_INPUT_CHARS or kind not in ("question", "amendment"):
        raise ReplayError("invalid saved human replay text or kind")
    if not isinstance(files, list) or len(files) > attachments.MAX_ATTACHMENTS:
        raise ReplayError("a saved human input may contain at most six attachments")
    files = [_file(item) for item in files]
    if len({item["id"] for item in files}) != len(files):
        raise ReplayError("a saved human input repeats an attachment ID")
    if not text.strip() and not files:
        raise ReplayError("a saved human input must contain text or attachments")
    result = {"text": text, "kind": kind, "attachments": files}
    if 'intent_text' in row or 'clarification_receipt' in row:
        if (type(row.get('intent_text')) is not str or not row['intent_text'].strip()
                or len(row['intent_text'])>MAX_INPUT_CHARS or type(row.get('clarification_receipt')) is not dict):
            raise ReplayError('invalid saved clarification authority')
        result.update(intent_text=row['intent_text'],clarification_receipt=copy.deepcopy(row['clarification_receipt']))
    if 'clarification_source' in row:
        if 'clarification_receipt' not in result:
            raise ReplayError('original clarification controls have no saved answer')
        result['clarification_source'] = _clarification_source(row['clarification_source'])
    if "attachment_only_default" in row:
        default = row["attachment_only_default"]
        if not isinstance(default, str) or not default.strip() or len(default) > MAX_INPUT_CHARS or text or not files:
            raise ReplayError("invalid saved attachment-only default")
        result["attachment_only_default"] = default
    return result


def _remember(files, seen):
    for item in files:
        prior = seen.get(item["id"])
        if prior is not None and prior != item:
            raise ReplayError("one recorded replay attachment ID has conflicting metadata")
        seen[item["id"]] = item
    if len(seen) > MAX_FILES or sum(item["bytes"] for item in seen.values()) > attachments.MAX_STORE_BYTES:
        raise ReplayError("recorded replay attachments exceed the session limit")


def extract_turns(session):
    """Return completed human/assistant pairs without mutating saved evidence.

    Consecutive human messages form one turn. Missing legacy human kind means
    question. Trailing unanswered human messages and queued messages are counted
    in excluded_pending_count, and never returned as actor inputs. A saved
    attachment-only default stays distinct from the user's original empty text.
    """
    if not isinstance(session, dict) or session.get("research_mode") != "live":
        raise ReplayError("replay currently supports saved live sessions only; fixture sessions are unsupported")
    if session.get("output_mode", "checked") not in ("agent", "checked"):
        raise ReplayError("unsupported saved live session output mode")
    messages, queue = session.get("messages"), session.get("queue", [])
    if not isinstance(messages, list) or len(messages) > MAX_MESSAGES or not isinstance(queue, list) or len(queue) > MAX_MESSAGES:
        raise ReplayError("invalid or oversized saved replay message collection")
    turns, pending, seen, calls = [], [], {}, set()
    replay_offsets = {}
    previous_assistant = {}
    flagged_pending = False
    for row in messages:
        if not isinstance(row, dict) or row.get("role") not in ("human", "assistant"):
            raise ReplayError("saved live replay messages must be human or assistant messages")
        if "pending" in row and type(row["pending"]) is not bool:
            raise ReplayError("invalid saved replay pending marker")
        if row["role"] == "human":
            replay_turn = row.get('replay_turn')
            offset = replay_offsets.get(replay_turn, 0) if type(replay_turn) is int else 0
            if type(replay_turn) is int:
                replay_offsets[replay_turn] = offset + 1
            source = None
            if 'clarification_receipt' in row or 'intent_text' in row:
                import playground_intent
                try:
                    source = (_replayed_clarification_source(session, row, offset) if 'replay_turn' in row else
                              _clarification_source({key: previous_assistant.get(key) for key in ('call_id', 'questions')}))
                    playground_intent.saved_clarification(row, dict(role='assistant', **source))
                except (ValueError,KeyError,TypeError) as error:raise ReplayError('saved clarification cannot be verified') from error
            if 'clarification_source' in row:
                # Actual messages do not carry controls. They are derived here
                # from real source messages or the verified frozen replay plan.
                raise ReplayError('human message cannot supply clarification controls')
            item = _input(row)
            if source is not None:
                item['clarification_source'] = source
            _remember(item["attachments"], seen)
            pending.append(item)
            flagged_pending = flagged_pending or row.get("pending", False)
            continue
        reply = row.get("text")
        if not isinstance(reply, str) or not reply.strip() or len(reply) > 8 * 1024 * 1024:
            raise ReplayError("invalid saved assistant reply")
        if not pending or flagged_pending or row.get("pending", False):
            raise ReplayError("saved assistant reply has no completed human input group")
        call_id = row.get("call_id", row.get("acceptance_id"))
        if call_id is not None:
            if not isinstance(call_id, str) or not CALL_ID.fullmatch(call_id) or call_id in calls:
                raise ReplayError("invalid or repeated saved assistant call ID")
            calls.add(call_id)
        turns.append({"index": len(turns) + 1, "inputs": pending,
                      "original_reply": reply, "source_call_id": call_id})
        previous_assistant = row
        pending = []
    # Queue text is not consulted for input extraction, including path-looking
    # text and attachment defaults. Count only structurally plausible entries.
    for row in queue:
        if not isinstance(row, dict) or not isinstance(row.get("text"), str) or row.get("kind") not in ("question", "amendment"):
            raise ReplayError("invalid pending replay queue entry")
    return {"turns": turns, "excluded_pending_count": len(pending) + len(queue)}


def _folder(value):
    if not isinstance(value, (str, Path)):
        raise ReplayError("replay session folder must be a path")
    path = Path(value).absolute()
    if ".." in path.parts or not path.name:
        raise ReplayError("invalid replay session folder")
    # Canonicalize OS parent aliases, while leaving the session's final component
    # untouched for the symlink-free directory opener below.
    return path.parent.resolve(strict=True) / path.name


def _child(directory, name, create=False):
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=directory)
        except FileExistsError:
            pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ReplayError("replay supplied-files directory must be private and owned by the current user")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _verified(directory, name, metadata):
    raw = attachments._read_at(directory, name, attachments.MAX_ATTACHMENT_BYTES)
    if len(raw) != metadata["bytes"] or hashlib.sha256(raw).hexdigest() != metadata["sha256"]:
        raise ReplayError("recorded replay attachment bytes or digest differ")
    return raw


def clone_input_files(source_folder, dest_folder, inputs):
    """Return selected inputs with verified destination attachment paths.

    Both session folders must already exist. Only attachment metadata supplied
    in these inputs selects bytes; text and original_path are never opened or
    interpreted. The source path must name its ID-based direct supplied-files
    snapshot. Existing destination copies are reused only when still identical.
    A failed invocation removes only newly created copies and leaves the source
    unchanged. Earlier successful replay copies can remain for later turns.
    """
    if not isinstance(inputs, list) or not inputs or len(inputs) > MAX_MESSAGES:
        raise ReplayError("replay inputs must be a nonempty bounded list")
    result = [_input(row, strict=True) for row in inputs]
    files = {}
    for row in result:
        _remember(row["attachments"], files)
    if not files:
        return result
    descriptors, written = [], []
    target_files = None
    try:
        source, target = _folder(source_folder), _folder(dest_folder)
        if source == target:
            raise ReplayError("replay destination must differ from the source session")
        for item in files.values():
            name = item["id"] + attachments._extension(item["name"])
            if Path(item["path"]) != source / "supplied-files" / name:
                raise ReplayError("recorded replay attachment must be its ID-based source supplied-files snapshot")
        source_fd = attachments._directory(source, private=True)
        descriptors.append(source_fd)
        target_fd = attachments._directory(target, private=True)
        descriptors.append(target_fd)
        if (os.fstat(source_fd).st_dev, os.fstat(source_fd).st_ino) == (os.fstat(target_fd).st_dev, os.fstat(target_fd).st_ino):
            raise ReplayError("replay destination aliases the source session")
        source_files = _child(source_fd, "supplied-files")
        descriptors.append(source_files)
        target_files = _child(target_fd, "supplied-files", create=True)
        descriptors.append(target_files)
        for item in files.values():
            name = item["id"] + attachments._extension(item["name"])
            raw = _verified(source_files, name, item)
            try:
                attachments._write_at(target_files, name, raw)
                written.append(name)
            except FileExistsError:
                pass
            _verified(target_files, name, item)
            item["path"] = str(target / "supplied-files" / name)
        for row in result:
            row["attachments"] = [copy.deepcopy(files[item["id"]]) for item in row["attachments"]]
        return result
    except BaseException as error:
        if target_files is not None:
            for name in written:
                os.unlink(name, dir_fd=target_files)
        if isinstance(error, (OSError, UnicodeError, RuntimeError, attachments.AttachmentError)):
            raise ReplayError("cannot clone recorded replay attachment: " + str(error)) from error
        raise
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
