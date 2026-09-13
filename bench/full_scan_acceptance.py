#!/usr/bin/env python3
"""Private, resumable coordinator for an explicitly frozen loopback lab study.

Python 3.9 standard library. Prepare/report are offline. Create uploads selected
evidence and creates sessions but never dispatches a model. Step/send dispatch
one call; reserve-ui dispatches none. Record-observed only reads existing host
receipts. There is no retry, automatic polling, grading, or delayed dispatch.
The lab owns physical calls; this ledger serializes study admission and accounts
for their retained direct usage across independently pinned lab servers.

After disconnection, report/export use only frozen local state. If a host still
has pending_call after its durable receipt completed, first manually verify no
active worker and use that host's receipt-only recover control, then run
record-observed. This coordinator never invokes recover or resends an input.
Global/per-session token ceilings are checked between calls; one physical call
may overshoot a ceiling. The first receipt always requires a cost review.
"""
import argparse
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit
import uuid


MAX_RESPONSE_BYTES = 32 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
REMOTE_ID = re.compile(r"[a-f0-9]{32}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")


class CoordinatorError(ValueError):
    pass


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _read(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise CoordinatorError("missing or unsafe file: " + str(path))
    return path.read_bytes()


def _json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CoordinatorError("duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(_read(path).decode("utf-8"), object_pairs_hook=pairs)
    _bytes(value)
    return value


def _write_raw(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise CoordinatorError("unsafe output path")
    with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(str(temporary), str(path))
        fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write(path, value):
    _write_raw(path, _bytes(value) + b"\n")


def _url(value):
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.username or parsed.password or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or not 1024 <= parsed.port <= 65535):
            raise ValueError()
        return parsed.port
    except (TypeError, ValueError):
        raise CoordinatorError("lab URL must be http://127.0.0.1:PORT") from None


def _positive(value, label, low=1, high=10**9):
    if type(value) is not int or not low <= value <= high:
        raise CoordinatorError("invalid " + label)
    return value


def _manifest(arm):
    _url(arm["url"])
    path = Path(arm["runtime_manifest"])
    raw = _read(path)
    if _sha(raw) != arm["runtime_manifest_sha256"]:
        raise CoordinatorError("frozen runtime manifest changed")
    manifest = json.loads(raw)
    if not isinstance(manifest.get("files"), dict) or not isinstance(manifest.get("public_skill"), dict):
        raise CoordinatorError("runtime manifest lacks frozen file/package inventory")
    for name, item in manifest["files"].items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or not name:
            raise CoordinatorError("unsafe runtime inventory path")
        body = _read(path.parent / rel)
        if _sha(body) != item["sha256"] or len(body) != item["bytes"]:
            raise CoordinatorError("frozen runtime file changed: " + name)
    return manifest


def _normalize(plan):
    plan = copy.deepcopy(plan)
    if plan.get("version") != 1:
        raise CoordinatorError("plan version must be 1")
    plan.setdefault("global_max_tokens", 4_000_000)
    _positive(plan["global_max_tokens"], "global_max_tokens")
    for key, value in (("model", "gpt-5.6-terra"), ("research_depth", "standard"), ("reasoning_effort", "low")):
        if plan.setdefault(key, value) != value:
            raise CoordinatorError("this study requires " + key + "=" + value)
    if not isinstance(plan.get("arms"), dict) or not plan["arms"]:
        raise CoordinatorError("plan requires arms")
    for key, arm in plan["arms"].items():
        if not ID.fullmatch(key) or not isinstance(arm, dict):
            raise CoordinatorError("invalid arm")
        if not HASH.fullmatch(arm.get("runtime_manifest_sha256", "")):
            raise CoordinatorError("arm requires runtime_manifest_sha256")
        arm["runtime_manifest"] = str(Path(arm["runtime_manifest"]).absolute())
        _manifest(arm)
    if not isinstance(plan.get("cases"), dict) or not plan["cases"]:
        raise CoordinatorError("plan requires cases")
    for case in plan["cases"].values():
        turns = case.get("turns")
        if not isinstance(turns, list) or not 1 <= len(turns) <= 80:
            raise CoordinatorError("case requires 1–80 planned turns")
        for index, turn in enumerate(turns):
            if turn.get("mode", "fixed") not in ("fixed", "choice"):
                raise CoordinatorError("turn mode must be fixed or choice")
            turn.setdefault("mode", "fixed")
            if turn["mode"] == "fixed" or index == 0:
                if not isinstance(turn.get("text"), str) or not turn["text"].strip() or len(turn["text"]) > 8000:
                    raise CoordinatorError("fixed turn requires bounded text")
            elif (not isinstance(turn.get("option_policy", ""), str)
                  or not turn.get("option_policy", "").strip()):
                raise CoordinatorError("choice turn requires a frozen option_policy")
            for field in ("text", "fallback_text"):
                if field in turn and (not isinstance(turn[field], str) or not turn[field].strip() or len(turn[field]) > 8000):
                    raise CoordinatorError("turn requires bounded " + field)
            if turn.get("kind", "question") not in ("question", "amendment"):
                raise CoordinatorError("invalid turn kind")
        if turns[0]["mode"] != "fixed":
            raise CoordinatorError("first turn must be fixed")
        if not isinstance(case.setdefault("attachments", []), list) or len(case["attachments"]) > 6:
            raise CoordinatorError("case attachments must be a list of at most six host IDs")
        for item in case.setdefault("files", []):
            item["path"] = str(Path(item["path"]).absolute())
            if _sha(_read(item["path"])) != item["sha256"]:
                raise CoordinatorError("selected case file differs from its pinned hash")
        if len(case["attachments"]) + len(case["files"]) > 6:
            raise CoordinatorError("case permits at most six total attachments")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise CoordinatorError("plan requires sessions")
    seen = set()
    for session in sessions:
        key = session.get("id", "")
        if not ID.fullmatch(key) or key in seen or session.get("arm") not in plan["arms"] or session.get("case_id") not in plan["cases"]:
            raise CoordinatorError("invalid or repeated session")
        seen.add(key)
        session["planned_calls"] = len(plan["cases"][session["case_id"]]["turns"])
        _positive(session.setdefault("max_tokens", 700000), "session max_tokens", 10000, 2000000)
        _positive(session.setdefault("seed", 1), "seed", 1, 10000)
    return plan


def prepare(out, plan_path):
    out = Path(out).absolute()
    if any(p.is_symlink() for p in (out, *out.parents)) or out.exists():
        raise CoordinatorError("prepare requires a new private directory; resume existing ledgers")
    plan = _normalize(_json(plan_path))
    out.mkdir(parents=True, mode=0o700)
    config = {"run_id": str(uuid.uuid4()), "plan": plan}
    _write(out / "config.json", {"value": config, "sha256": _sha(_bytes(config))})
    state = {"version": 1, "config_sha256": _sha(_bytes(config)), "revision": 0,
             "sessions": {s["id"]: {"remote_id": None, "created": False} for s in plan["sessions"]},
             "calls": [], "pending": None, "halted": None,
             "cost_checkpoint": False, "cost_reviews": []}
    _save(out, state)
    return report(out)


def _config(out):
    saved = _json(Path(out) / "config.json")
    if saved.get("sha256") != _sha(_bytes(saved.get("value"))):
        raise CoordinatorError("frozen config checksum differs")
    return saved["value"]


@contextmanager
def _locked(out):
    out = Path(out).absolute()
    config = _config(out)
    if any(p.is_symlink() for p in (out, *out.parents)):
        raise CoordinatorError("unsafe ledger directory")
    if (out / "coordinator.lock").is_symlink():
        raise CoordinatorError("unsafe lock path")
    with (out / "coordinator.lock").open("a+b") as lock:
        os.chmod(out / "coordinator.lock", 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CoordinatorError("another coordinator operation owns the study lock") from None
        saved = _json(out / "state.json")
        state = saved.get("value")
        if (saved.get("sha256") != _sha(_bytes(state))
                or state.get("config_sha256") != _sha(_bytes(config))):
            raise CoordinatorError("ledger/config checksum differs")
        try:
            yield out, config, state
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _summary(config, state):
    plan = config["plan"]
    known = sum(row["usage"]["processed_tokens"] for row in state["calls"] if row.get("usage"))
    unknown = bool(state["pending"]) or any(not row.get("usage") for row in state["calls"])
    if state["pending"]:
        next_action = ("Inspect the existing receipt; NEVER resend pending input. If the Lab still has pending_call, "
                       "manually verify no active worker and use its receipt-only recover control, then record-observed.")
    elif state["halted"]:
        next_action = "Stopped: " + state["halted"] + ". Preserve evidence; no automatic replacement."
    elif state["cost_checkpoint"]:
        next_action = "Review first-call cost; acknowledge-cost with a recorded forecast before any next dispatch."
    elif len(state["calls"]) == sum(s["planned_calls"] for s in plan["sessions"]):
        next_action = "All planned calls accounted for; export retained evidence."
    elif known >= plan["global_max_tokens"]:
        next_action = "Global token ceiling reached; preserve evidence and do not dispatch another call."
    else:
        next_action = "Resume from this config/ledger. Check budgets, then dispatch or reserve exactly one planned turn."
    return {"run_id": config["run_id"], "revision": state["revision"],
            "planned_calls": sum(s["planned_calls"] for s in plan["sessions"]),
            "recorded_calls": len(state["calls"]), "processed_tokens": None if unknown else known,
            "known_processed_tokens": known, "global_max_tokens": plan["global_max_tokens"],
            "pending": ({k: state["pending"][k] for k in ("session", "turn", "mode", "reserved_at")}
                        if state["pending"] else None), "halted": state["halted"],
            "cost_checkpoint": state["cost_checkpoint"], "next_action": next_action,
            "sessions": [{"id": s["id"], "arm": s["arm"],
                          "remote_id": state["sessions"][s["id"]]["remote_id"],
                          "created": state["sessions"][s["id"]]["created"],
                          "recorded_calls": sum(c["session"] == s["id"] for c in state["calls"]),
                          "known_processed_tokens": sum(c["usage"]["processed_tokens"] for c in state["calls"]
                                                        if c["session"] == s["id"] and c.get("usage")),
                          "max_tokens": s["max_tokens"],
                          "planned_calls": s["planned_calls"]} for s in plan["sessions"]]}


def _save(out, state):
    state["revision"] += 1
    _write(Path(out) / "state.json", {"value": state, "sha256": _sha(_bytes(state))})
    summary = _summary(_config(out), state)
    _write(Path(out) / "status.json", summary)
    # This short offline checkpoint deliberately excludes prompts/history/grades.
    path = Path(out) / "RESUME.md"
    body = ("Resume the frozen full-scan study\n\n" + summary["next_action"] + "\n\n"
            + "Recorded calls: %s / %s. Known processed tokens: %s / %s.\n" %
            (summary["recorded_calls"], summary["planned_calls"], summary["known_processed_tokens"], summary["global_max_tokens"])
            + "Use report --out with this directory. Do not prepare a replacement study or resend a pending dispatch.\n"
            + "The same frozen runtime may restart; verify its manifest and existing receipt before continuing.\n")
    # Human-readable derivative; the checksummed state above is authoritative.
    _write_raw(path, body.encode("utf-8"))


def report(out):
    with _locked(out) as (_out, config, state):
        return _summary(config, state)


def _request(out, state, arm, method, path, body=None):
    port = _url(arm["url"])
    if not path.startswith("/api/") or "\r" in path or "\n" in path:
        raise CoordinatorError("invalid local API path")
    key = str(time.time_ns()) + "-" + uuid.uuid4().hex
    log = Path(out) / "http" / (key + ".json")
    payload = _bytes(body) if body is not None else None
    headers = {"X-Pea-Client": "persona-lab", "Host": "127.0.0.1:" + str(port)}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    record = {"method": method, "url": arm["url"] + path, "headers": headers,
              "request": body, "started_at": time.time(), "response": None}
    _write(log, record)  # A transport crash leaves the exact attempted request.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise CoordinatorError("local API response exceeds retained byte limit")
        record.update(status=response.status, response_headers=response.getheaders(),
                      response=raw.decode("utf-8"), finished_at=time.time())
        _write(log, record)
        if response.status != 200:
            raise CoordinatorError("local API returned HTTP %s; inspect private HTTP record" % response.status)
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise CoordinatorError("local API response must be a JSON object")
        return value
    except Exception as error:
        record.update(error=type(error).__name__ + ": " + str(error), finished_at=time.time())
        _write(log, record)
        raise CoordinatorError("local API failed; no retry: " + str(error)) from error
    finally:
        connection.close()


def _parts(config, key):
    plan = config["plan"]
    session = next((s for s in plan["sessions"] if s["id"] == key), None)
    if session is None:
        raise CoordinatorError("session is outside the frozen plan")
    return session, plan["arms"][session["arm"]], plan["cases"][session["case_id"]]


def _verify_host(out, state, arm):
    manifest = _manifest(arm)
    catalog = _request(out, state, arm, "GET", "/api/catalog")
    package = catalog.get("skill_artifact", {})
    expected = manifest["public_skill"]
    if (package.get("kind") != "public_zip" or package.get("sha256") != expected.get("archive_sha256")
            or package.get("path") != str(Path(arm["runtime_manifest"]).parent / expected["skill_path"])
            or catalog.get("source_sync", {}).get("current") is not True):
        raise CoordinatorError("running lab does not match the selected frozen package")


def _client(config, key, suffix):
    return str(uuid.uuid5(uuid.UUID(config["run_id"]), key + "/" + suffix))


def create(out, key):
    with _locked(out) as (out, config, state):
        session, arm, case = _parts(config, key)
        _verify_host(out, state, arm)
        local = state["sessions"][key]
        if local["created"]:
            return _summary(config, state)
        client = _client(config, key, "create")
        remote = uuid.uuid5(uuid.NAMESPACE_URL, "pea-persona-lab/" + client).hex
        local["remote_id"] = remote
        _save(out, state)
        if "create_body" not in local:
            uploaded_ids = local.setdefault("uploaded_ids", [])
            for index, item in enumerate(case["files"]):
                if _sha(_read(item["path"])) != item["sha256"]:
                    raise CoordinatorError("selected case evidence changed")
                if index >= len(uploaded_ids):
                    uploaded = _request(out, state, arm, "POST", "/api/attachments", {"path": item["path"]})
                    if uploaded.get("sha256") != item["sha256"] or not REMOTE_ID.fullmatch(uploaded.get("id", "")):
                        raise CoordinatorError("uploaded evidence does not match its frozen source hash")
                    uploaded_ids.append(uploaded["id"])
                    _save(out, state)
            local["create_body"] = {"research_mode": "live", "output_mode": "agent", "initial_request": case["turns"][0]["text"],
                    "attachments": list(case["attachments"]) + uploaded_ids, "model": config["plan"]["model"],
                    "research_depth": config["plan"]["research_depth"], "reasoning_effort": config["plan"]["reasoning_effort"],
                    "max_calls": session["planned_calls"], "max_tokens": session["max_tokens"],
                    "seed": session["seed"], "client_id": client}
            _save(out, state)
        body = local["create_body"]
        # Lab create is idempotent under this stable client ID and cannot dispatch.
        result = _request(out, state, arm, "POST", "/api/sessions", body)
        if result.get("id") != remote:
            raise CoordinatorError("created session ID differs from its stable request identity")
        local["created"] = True
        _save(out, state)
        return _summary(config, state)


def _remote(out, state, arm, key):
    local = state["sessions"][key]
    if not local["created"] or not REMOTE_ID.fullmatch(local["remote_id"] or ""):
        raise CoordinatorError("create the planned session before dispatch")
    return _request(out, state, arm, "GET", "/api/session/" + local["remote_id"])


def _admit(out, config, state, key):
    if state["pending"] or state["halted"] or state["cost_checkpoint"]:
        raise CoordinatorError(_summary(config, state)["next_action"])
    total = _summary(config, state)
    if total["processed_tokens"] is None or total["known_processed_tokens"] >= total["global_max_tokens"]:
        raise CoordinatorError("global token budget reached or unknown; no dispatch")
    target = None
    # Detect UI calls that bypassed reserve-ui before another arm can spend.
    for spec in config["plan"]["sessions"]:
        current = spec["id"]
        if not state["sessions"][current]["created"]:
            continue
        _, arm, _ = _parts(config, current)
        _verify_host(out, state, arm)
        snap = _remote(out, state, arm, current)
        rows = [r for r in state["calls"] if r["session"] == current]
        if (snap.get("calls") != len(rows) or snap.get("busy") or snap.get("pending_call")
                or snap.get("auto") or snap.get("pending_count")):
            state["halted"] = "unrecorded or active host call in " + current
            state["pending"] = {"session": current, "turn": len(rows) + 1, "mode": "observed",
                                "before_calls": len(rows), "request": None, "questions": [],
                                "reserved_at": time.time()}
            _save(out, state)
            raise CoordinatorError(state["halted"] + "; inspect/record existing receipt only")
        if current == key:
            target = snap
    session, arm, case = _parts(config, key)
    if target is None:
        raise CoordinatorError("session has not been created")
    if (target.get("compatible") is not True or target.get("status") in ("error", "interrupted", "budget", "ended")
            or target.get("model") != config["plan"]["model"]):
        raise CoordinatorError("host session is stopped, incompatible, or has a different model")
    settings = target.get("execution_settings", {})
    if any(settings.get(k) != config["plan"][k] for k in ("research_depth", "reasoning_effort")):
        raise CoordinatorError("host execution settings differ from the frozen plan")
    rows = [r for r in state["calls"] if r["session"] == key]
    if len(rows) >= session["planned_calls"] or sum(r["usage"]["processed_tokens"] for r in rows) >= session["max_tokens"]:
        raise CoordinatorError("session call/token ceiling reached")
    return session, arm, case, target, len(rows) + 1


def _dispatch(out, key, mode):
    with _locked(out) as (out, config, state):
        session, arm, case, snap, turn = _admit(out, config, state, key)
        spec = case["turns"][turn - 1]
        if mode == "step" and turn != 1:
            raise CoordinatorError("step is only for the initial planned input")
        if mode == "send" and (turn == 1 or spec["mode"] != "fixed"):
            raise CoordinatorError("send requires a subsequent fixed turn; use actual UI for choice turns")
        if mode == "ui" and (turn == 1 or spec["mode"] != "choice"):
            raise CoordinatorError("reserve-ui requires a planned choice turn")
        body = {"action": "step", "client_id": _client(config, key, "turn-%d" % turn)} if mode == "step" else {
            "text": spec.get("text"), "kind": spec.get("kind", "question"), "client_id": _client(config, key, "turn-%d" % turn)}
        questions = []
        if mode == "ui":
            messages = snap.get("messages", [])
            if not messages or messages[-1].get("role") != "assistant":
                raise CoordinatorError("latest actual reply has no selectable question; do not invent a control")
            questions = copy.deepcopy(messages[-1].get("questions", []))
            if not questions and not spec.get("fallback_text"):
                raise CoordinatorError("latest actual reply has no selectable question and no frozen fallback")
            body = None
        state["pending"] = {"session": key, "turn": turn, "mode": mode,
                            "before_calls": turn - 1, "request": body,
                            "questions": questions, "reserved_at": time.time()}
        _save(out, state)  # Always precedes any irreversible dispatch or UI handoff.
        if mode != "ui":
            path = "/api/session/" + state["sessions"][key]["remote_id"] + ("/control" if mode == "step" else "/message")
            try:
                state["pending"]["accepted"] = _request(out, state, arm, "POST", path, body)
            except Exception as error:
                state["pending"]["transport_error"] = str(error)
                _save(out, state)
                raise
            _save(out, state)
        return _summary(config, state)


def step(out, key):
    return _dispatch(out, key, "step")


def send(out, key):
    return _dispatch(out, key, "send")


def reserve_ui(out, key):
    return _dispatch(out, key, "ui")


def _usage(detail):
    value = detail.get("usage", {})
    fields = ("input_tokens", "cached_input_tokens", "output_tokens")
    if any(type(value.get(k)) is not int or value[k] < 0 for k in fields):
        return None
    incoming, cached, outgoing = (value[k] for k in fields)
    if cached > incoming or value.get("processed_tokens") != incoming + outgoing:
        return None
    return {"input_tokens": incoming, "cached_input_tokens": cached,
            "uncached_input_tokens": incoming - cached, "output_tokens": outgoing,
            "processed_tokens": incoming + outgoing}


def _choice(spec, pending, submission, actual):
    if not isinstance(submission, dict) or submission.get("text") != actual:
        raise CoordinatorError("UI submission must preserve its exact actual transcript")
    question, option, free = (submission.get(k, "") for k in ("question", "option", "free_text"))
    if not all(isinstance(v, str) for v in (question, option, free)):
        raise CoordinatorError("invalid UI submission text")
    questions = pending.get("questions", [])
    if not questions and spec.get("fallback_text"):
        if question or option or free != spec["fallback_text"] or actual != free:
            raise CoordinatorError("missing question requires the exact frozen plain-text fallback")
        return {**copy.deepcopy(submission), "choice_coverage": "missing", "native_question": False}
    found = next((q for q in questions if q.get("question") == question), None)
    if found is None or (option and option not in found.get("options", [])) or not (option or free):
        raise CoordinatorError("submission is not an actual reserved question/option")
    if spec.get("text") and (free != spec["text"] or option):
        raise CoordinatorError("UI free-text-only input differs from frozen case input")
    if not spec.get("text") and not option and free != spec.get("fallback_text"):
        raise CoordinatorError("missing option requires the exact frozen fallback text")
    if not spec.get("text") and option and free:
        raise CoordinatorError("actual option submission cannot add unfrozen free text")
    expected = question + "\n" + "；".join(v for v in (option, free.strip()) if v)
    if actual != expected:
        raise CoordinatorError("UI transcript differs from the actual form serializer")
    if option and not submission.get("selection_reason", "").strip():
        raise CoordinatorError("record why the actual option matches the frozen semantic policy")
    return {**copy.deepcopy(submission), "choice_coverage": "actual_option" if option else "missing",
            "native_question": True}


def record_observed(out, key, submission=None):
    with _locked(out) as (out, config, state):
        session, arm, case = _parts(config, key)
        _verify_host(out, state, arm)
        pending = state["pending"]
        if pending and pending["session"] != key:
            raise CoordinatorError("another session owns the unresolved call")
        before = sum(r["session"] == key for r in state["calls"])
        snap = _remote(out, state, arm, key)
        if not pending and (snap.get("busy") or snap.get("pending_call") or snap.get("calls") != before):
            pending = {"session": key, "turn": before + 1, "mode": "observed",
                       "before_calls": before, "request": None, "questions": [],
                       "reserved_at": time.time()}
            state["pending"] = pending
            _save(out, state)
        if snap.get("busy") or snap.get("pending_call"):
            raise CoordinatorError("host call is unresolved; keep pending and inspect later, never resend")
        if snap.get("calls") != before + 1:
            if pending and isinstance(snap.get("calls"), int) and snap["calls"] > before + 1:
                state["halted"] = "multiple unrecorded calls; manual receipt audit required"
                _save(out, state)
            raise CoordinatorError("record-observed requires exactly one new host call")
        if before >= session["planned_calls"]:
            raise CoordinatorError("observed call exceeds frozen plan")
        remote = state["sessions"][key]["remote_id"]
        exported = _request(out, state, arm, "GET", "/api/session/" + remote + "/export")
        calls = exported.get("calls", [])
        if len(calls) != before + 1 or not isinstance(calls[-1], dict):
            raise CoordinatorError("export call roster disagrees with snapshot")
        call = calls[-1]
        call_id = call.get("id", "")
        if not ID.fullmatch(call_id):
            raise CoordinatorError("invalid observed call ID")
        detail = _request(out, state, arm, "GET", "/api/session/" + remote + "/inspect/" + call_id)
        if detail.get("call_id") != call_id:
            raise CoordinatorError("inspected call identity differs")
        usage = _usage(detail)
        spec = case["turns"][before]
        inputs = [m for m in exported.get("messages", []) if m.get("role") == "human"]
        actual = inputs[-1].get("text") if inputs else None
        selected = None
        if spec["mode"] == "choice":
            if not pending or pending.get("mode") != "ui":
                raise CoordinatorError("choice recovery requires the saved pre-UI reservation")
            selected = _choice(spec, pending, submission, actual)
        elif actual != spec["text"]:
            raise CoordinatorError("observed input differs from frozen case text")
        valid = (detail.get("integrity", {}).get("ok") is True
                 and HASH.fullmatch(detail.get("source", {}).get("record_sha256") or "")
                 and detail.get("execution_settings_evidence", {}).get("status") == "bound"
                 and detail.get("model") == config["plan"]["model"]
                 and all(detail.get("execution_settings", {}).get(k) == config["plan"][k]
                         for k in ("research_depth", "reasoning_effort")))
        complete = call.get("status") == "complete" and detail.get("status") == "complete"
        row = {"session": key, "turn": before + 1, "remote_call_id": call_id,
               "status": "complete" if valid and complete and usage is not None else "stopped",
               "usage": usage, "source": detail.get("source"), "recorded_at": time.time(),
               "submission": selected, "research_results": call.get("research_results"),
               "pending_intent": copy.deepcopy(pending)}
        state["calls"].append(row)
        state["pending"] = None
        if row["status"] != "complete":
            state["halted"] = "physical/integrity failure or unknown direct usage; preserved without replacement"
        elif state["halted"] and state["halted"].startswith("unrecorded or active host call in " + key):
            state["halted"] = None
        if len(state["calls"]) == 1:
            state["cost_checkpoint"] = True
        _write(out / "receipts" / (key + "-t%d.json" % (before + 1)), row)
        _save(out, state)
        return _summary(config, state)


def acknowledge_cost(out, note):
    if not isinstance(note, str) or not note.strip():
        raise CoordinatorError("cost review requires a recorded note/forecast")
    with _locked(out) as (out, config, state):
        if state["pending"] or state["halted"] or not state["cost_checkpoint"]:
            raise CoordinatorError("only a resolved first-call cost checkpoint may be acknowledged")
        state["cost_reviews"].append({"note": note, "time": time.time(),
                                      "known_processed_tokens": _summary(config, state)["known_processed_tokens"]})
        state["cost_checkpoint"] = False
        _save(out, state)
        return _summary(config, state)


def _archive(out, key, suffixes):
    with _locked(out) as (out, config, state):
        keys = [key] if key else [s["id"] for s in config["plan"]["sessions"] if state["sessions"][s["id"]]["created"]]
        for current in keys:
            _, arm, _ = _parts(config, current)
            _verify_host(out, state, arm)
            remote = state["sessions"][current]["remote_id"]
            for suffix in suffixes:
                _request(out, state, arm, "GET", "/api/session/" + remote + suffix)
        return _summary(config, state)


def snapshot(out, key=None):
    """Privately archive current host snapshots without dispatch or reconciliation."""
    return _archive(out, key, ("",))


def inspect(out, key=None):
    """Archive current host snapshot/export/index; never recover or dispatch a call."""
    return _archive(out, key, ("", "/export", "/inspect"))


def export(out):
    """Offline compact recovery export; full HTTP records stay in this directory."""
    with _locked(out) as (out, config, state):
        summary = _summary(config, state)
        _write(out / "status.json", summary)
        return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "create", "step", "send", "reserve-ui", "record-observed", "inspect", "snapshot", "export", "report", "acknowledge-cost"):
        command = sub.add_parser(name)
        command.add_argument("--out", required=True)
        if name in ("create", "step", "send", "reserve-ui", "record-observed"):
            command.add_argument("--session", required=True)
        if name in ("inspect", "snapshot"):
            command.add_argument("--session")
        if name == "prepare":
            command.add_argument("--plan", required=True)
        if name == "record-observed":
            command.add_argument("--submission", help="JSON: exact question, option/free_text, text, selection_reason")
        if name == "acknowledge-cost":
            command.add_argument("--note", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.out, args.plan)
        elif args.command == "report":
            result = report(args.out)
        elif args.command == "export":
            result = export(args.out)
        elif args.command == "acknowledge-cost":
            result = acknowledge_cost(args.out, args.note)
        elif args.command in ("inspect", "snapshot"):
            result = {"inspect": inspect, "snapshot": snapshot}[args.command](args.out, args.session)
        elif args.command == "record-observed":
            result = record_observed(args.out, args.session, _json(args.submission) if args.submission else None)
        else:
            result = {"create": create, "step": step, "send": send, "reserve-ui": reserve_ui}[args.command](args.out, args.session)
    except (CoordinatorError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
