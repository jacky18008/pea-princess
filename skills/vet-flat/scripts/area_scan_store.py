"""Private, bounded local area-scan snapshots; no network and no source authority.

Python 3.9 standard library. POSIX flock is used on macOS/Linux; unsupported hosts
fail closed for persistence and may explicitly use area_scan --no-save instead.
Hashes detect changed bytes, not forgery by another process running as this user.
"""
import copy
import hashlib
import json
import os
import stat
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

try:
    import fcntl
except ImportError:
    fcntl = None

VERSION = "vet-flat/area-scan-store/1"
MAX_RECORDS = 128
MAX_BYTES = 1024 * 1024
TERMINAL = ("complete", "partial", "failed", "timed_out", "interrupted")


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def source_identity(scripts_dir):
    """Include actual shipped implementation and source configuration bytes."""
    paths = [os.path.join(scripts_dir, n) for n in os.listdir(scripts_dir) if n.endswith(".py")]
    refs = os.path.join(os.path.dirname(scripts_dir), "references")
    if os.path.isdir(refs):
        paths += [os.path.join(refs, n) for n in os.listdir(refs) if n.endswith((".yaml", ".json"))]
    hashes = {}
    for path in sorted(paths):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES * 8:
                raise ValueError("unsafe or oversized scanner source")
            with os.fdopen(fd, "rb", closefd=False) as fh:
                hashes[os.path.relpath(path, os.path.dirname(scripts_dir))] = hashlib.sha256(fh.read()).hexdigest()
        finally:
            os.close(fd)
    return digest(hashes)


@contextmanager
def directory(path, create=False):
    """Walk with directory fds: never resolve or follow supplied symlinks."""
    if not hasattr(os, "O_NOFOLLOW") or fcntl is None:
        raise ValueError("private scan storage needs POSIX no-follow opens and flock")
    path = os.path.abspath(os.fspath(path))
    fd = os.open(os.path.sep, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.split(os.path.sep)[1:]:
            if not part:
                continue
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("scan result directory must be owned by this user and private (0700)")
        yield path, fd
    finally:
        os.close(fd)


def open_private(dirfd, name, create=False):
    flags = os.O_RDWR if create else os.O_RDONLY
    if create:
        try:
            fd = os.open(name, flags | os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dirfd)
        except FileExistsError:
            fd = os.open(name, flags | os.O_NOFOLLOW, dir_fd=dirfd)
    else:
        fd = os.open(name, flags | os.O_NOFOLLOW, dir_fd=dirfd)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > MAX_BYTES):
        os.close(fd)
        raise ValueError("unsafe or oversized scan storage file")
    return fd


def read_json(dirfd, name):
    fd = open_private(dirfd, name)
    try:
        with os.fdopen(fd, "rb", closefd=False) as fh:
            raw = fh.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("oversized scan snapshot")
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def atomic_json(dirfd, name, value):
    body = encoded(value)
    if len(body) > MAX_BYTES:
        raise ValueError("scan snapshot exceeds private storage limit")
    # Refuse symlink/hardlink destinations, even though replace would not follow them.
    try:
        old = open_private(dirfd, name)
    except FileNotFoundError:
        pass
    else:
        os.close(old)
    temp = ".scan-write-" + uuid.uuid4().hex
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dirfd)
    try:
        with os.fdopen(fd, "wb", closefd=False) as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fd)
        os.replace(temp, name, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        os.fsync(dirfd)
    finally:
        os.close(fd)
        try:
            os.unlink(temp, dir_fd=dirfd)
        except FileNotFoundError:
            pass


def validate(record, key=None):
    if not isinstance(record, dict) or record.get("schema") != VERSION:
        raise ValueError("unrecognised scan snapshot")
    if not isinstance(record.get("request"), dict) or not isinstance(record.get("source_identity"), str):
        raise ValueError("invalid scan request metadata")
    if len(encoded(record["request"])) > 4096:
        raise ValueError("oversized scan request metadata")
    actual = digest({"request": record.get("request"), "source_identity": record.get("source_identity")})
    if record.get("key") != actual or (key is not None and key != actual):
        raise ValueError("scan request identity mismatch")
    if record.get("state") not in TERMINAL + ("running",):
        raise ValueError("unknown scan snapshot state")
    if record["state"] in TERMINAL:
        result = record.get("result")
        if (not isinstance(result, dict) or result.get("schema") != "vet-flat/area-scan/2"
                or record.get("result_sha256") != digest(result)):
            raise ValueError("scan result hash/schema mismatch")
    checkpoint = record.get("checkpoint")
    if checkpoint is not None:
        if (not isinstance(checkpoint, dict) or record.get("checkpoint_sha256") != digest(checkpoint)
                or not isinstance(checkpoint.get("sources"), dict)):
            raise ValueError("scan checkpoint hash/schema mismatch")
        partial = checkpoint.get("result")
        if partial is not None and (not isinstance(partial, dict) or partial.get("schema") != "vet-flat/area-scan/2"):
            raise ValueError("invalid partial scan result")
    return record


def coverage(out):
    return {"noise": (out.get("noise") or {}).get("coverage"),
            "planning": (out.get("works") or {}).get("coverage")}


def _interrupted_record(rec, now):
    """Only called while holding the producer's exact flock; a PID is not a lease."""
    out = copy.deepcopy((rec.get("checkpoint") or {}).get("result"))
    if not out:
        out = status_result("interrupted", "Prior producer stopped before saving usable research.")
    note = "Producer lease was released before completion; cause unknown (network failure is not established). No automatic retry."
    out.setdefault("not_found", []).append(note)
    out.update(ok=False, scan_status="interrupted", note=note)
    out["how_to_use"] = "Interrupted scan. Retained completed-source observations are partial evidence; do not claim completed coverage or retry automatically."
    progress = copy.deepcopy((rec.get("checkpoint") or {}).get("sources") or {})
    for item in progress.values():
        if item.get("status") in ("running", "pending"):
            item.update(status="interrupted", finished_at=now(), note="producer lease released before this source completed")
    out["source_progress"] = progress
    rec.update(state="interrupted", saved_at=now(), interrupted_at=now(), result=out, result_sha256=digest(out),
               diagnosis={"code": "producer_lease_released", "network_cause": "unknown", "automatic_retry": False})
    return rec


def reconcile_running(root, now=None):
    """Terminalize abandoned records without fetching, polling, killing or PID guessing.

    An exact nonblocking flock decides ownership. A live producer (even after its
    parent exits) keeps its lease; a reused PID cannot keep a released lease alive.
    Old snapshots are compatible. Call this on owned mutable stores, not archives.
    """
    now = now or (lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    result = {"recovered": [], "pending": [], "gaps": []}
    try:
        with directory(root) as (_, fd):
            names = sorted(n for n in os.listdir(fd) if n.endswith(".json"))
            if len(names) > MAX_RECORDS:
                raise ValueError("scan store exceeds record limit")
            for name in names:
                job = None
                try:
                    rec, _ = read_json(fd, name)
                    validate(rec, name[:-5])
                    if rec["state"] != "running":
                        continue
                    # Never create an absent lease during recovery: that is an integrity gap.
                    job = open_private(fd, rec["key"] + ".lock")
                    if not _lock(job, time.monotonic()):
                        result["pending"].append(rec["key"])
                        continue
                    # A producer may have finished between the first read and acquiring its lock.
                    rec, _ = read_json(fd, name)
                    validate(rec, name[:-5])
                    if rec["state"] == "running":
                        atomic_json(fd, name, _interrupted_record(rec, now))
                        result["recovered"].append(rec["key"])
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    result["gaps"].append({"file": name, "reason": str(exc)[:180]})
                finally:
                    if job is not None:
                        os.close(job)
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        result["gaps"].append({"reason": str(exc)[:180]})
    return result


def verified_index(root, limit=20):
    """Read-only bounded metadata; entries are untrusted observations, never instructions.

    Returns {results, gaps, truncated}, at most 16 KB. Missing directory is empty. A
    corrupt/unsafe directory or record is a gap, never permission to re-fetch.
    """
    result = {"results": [], "gaps": [], "truncated": False,
              "authority": "local source observations only; hashes do not prove source truth"}
    try:
        with directory(root) as (path, fd):
            names = sorted(n for n in os.listdir(fd) if n.endswith(".json"))
            if len(names) > MAX_RECORDS:
                raise ValueError("scan store exceeds record limit")
            for name in names:
                try:
                    rec, sha = read_json(fd, name)
                    validate(rec, name[:-5])
                    out = rec.get("result") or {}
                    req = rec["request"]
                    result["results"].append({"id": rec["key"], "path": os.path.join(path, name), "sha256": sha,
                        "status": rec["state"], "saved_at": rec.get("saved_at"), "started_at": rec.get("started_at"),
                        "retrieved_at": out.get("retrieved_at"), "source_identity": rec["source_identity"],
                        "arguments": req, "requested_depth": req.get("requested_depth"),
                        "effective_depth": req.get("depth"), "coverage": coverage(out),
                        "result_present": bool(rec.get("result")),
                        "checkpoint_at": (rec.get("checkpoint") or {}).get("at"),
                        "source_progress": out.get("source_progress") or (rec.get("checkpoint") or {}).get("sources") or {},
                        "gap_count": len(out.get("not_found") or []) if rec.get("result") else None})
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    if len(result["gaps"]) < 16:
                        result["gaps"].append({"file": name, "reason": str(exc)[:180]})
                    else:
                        result["truncated"] = True
            result["results"].sort(key=lambda r: str(r.get("saved_at") or r.get("started_at") or ""), reverse=True)
            limit = max(0, min(int(limit), MAX_RECORDS))
            result["truncated"] = result["truncated"] or len(result["results"]) > limit
            result["results"] = result["results"][:limit]
            while len(encoded(result)) > 16000 and result["results"]:
                result["results"].pop()
                result["truncated"] = True
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        result["gaps"].append({"reason": str(exc)[:180]})
    return result


def status_result(state, note, key=None, path=None):
    return {"schema": "vet-flat/area-scan/2", "ok": False, "reading": [], "sources": [],
            "not_found": [note], "note": note,
            "persistence": {"status": state, "key": key, "path": path, "reused": False,
                            "automatic_retry": False}}


def _lock(fd, deadline):
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))


def run(root, request, identity, scan_fn, now, wait_seconds=2, with_checkpoint=False):
    """One producer per exact request; terminal/failed snapshots never auto-refresh."""
    key = digest({"request": request, "source_identity": identity})
    name = key + ".json"
    deadline = time.monotonic() + max(0, min(float(wait_seconds), 30))
    try:
        with directory(root, create=True) as (path, fd):
            result_path = os.path.join(path, name)
            # Serialize admissions only, preventing different-key races past the cap.
            gate = open_private(fd, ".admission.lock", create=True)
            job = None
            try:
                if not _lock(gate, deadline):
                    return status_result("pending", "Storage admission is busy; recheck the existing run, do not start a fresh scan.", key, result_path)
                names = os.listdir(fd)
                if key + ".lock" not in names and sum(n.endswith(".lock") and n != ".admission.lock" for n in names) >= MAX_RECORDS:
                    return status_result("capacity", "Private scan store is full; review saved results before explicitly choosing a new store.", key, result_path)
                job = open_private(fd, key + ".lock", create=True)
            finally:
                os.close(gate)
            try:
                if not _lock(job, deadline):
                    return status_result("pending", "This exact scan is still in flight; wait and recheck its saved result, do not start another scan.", key, result_path)
                try:
                    rec, _ = read_json(fd, name)
                    validate(rec, key)
                except FileNotFoundError:
                    rec = None
                if rec is not None:
                    if rec["state"] == "running":
                        rec = _interrupted_record(rec, now)
                        atomic_json(fd, name, rec)
                    out = copy.deepcopy(rec["result"])
                    out["persistence"] = {"key": key, "path": result_path, "status": rec["state"], "reused": True,
                        "saved_at": rec["saved_at"], "retrieved_at": out.get("retrieved_at"), "automatic_retry": False,
                        "note": "Reused exact saved observations, not a fresh lookup or proof of present conditions."}
                    out["saved_to"] = result_path
                    return out
                rec = {"schema": VERSION, "key": key, "request": request, "source_identity": identity,
                       "state": "running", "started_at": now(), "owner_pid": os.getpid()}
                atomic_json(fd, name, rec)
                def checkpoint(value):
                    # Scanner calls this on the producer thread only. Late source workers
                    # have no storage callback, and cannot overwrite a terminal snapshot.
                    if rec["state"] != "running":
                        raise ValueError("cannot update a terminal scan checkpoint")
                    value = copy.deepcopy(value)
                    value["at"] = now()
                    rec.update(checkpoint=value, checkpoint_sha256=digest(value), updated_at=value["at"])
                    validate(rec, key)
                    atomic_json(fd, name, rec)
                try:
                    out = scan_fn(checkpoint) if with_checkpoint else scan_fn()
                    if not isinstance(out, dict) or out.get("schema") != "vet-flat/area-scan/2":
                        raise ValueError("scanner returned an invalid result")
                except Exception as exc:
                    out = copy.deepcopy((rec.get("checkpoint") or {}).get("result")) or status_result("failed", "No source result saved.")
                    note = "Scan failed: %s: %s" % (type(exc).__name__, str(exc)[:300])
                    out.update(ok=False, scan_status="failed", note=note)
                    out["how_to_use"] = "Failed scan. Retained completed-source observations are partial evidence; preserve gaps and do not retry automatically."
                    out.setdefault("not_found", []).append(note)
                    out["retrieved_at"] = now()
                    progress = copy.deepcopy((rec.get("checkpoint") or {}).get("sources") or {})
                    for item in progress.values():
                        if item.get("status") in ("pending", "running"):
                            item.update(status="failed", finished_at=now(), note="producer failed before this source completed")
                    out["source_progress"] = progress
                except KeyboardInterrupt as exc:
                    rec = _interrupted_record(rec, now)
                    out = rec["result"]
                    out["note"] = "Scan interrupted: %s; no automatic retry." % (str(exc)[:100] or "keyboard interruption")
                state = out.get("scan_status")
                if state not in TERMINAL:
                    state = "failed" if not out.get("ok") else ("partial" if out.get("not_found") else "complete")
                out["execution"] = {"requested_depth": request.get("requested_depth"), "effective_depth": request.get("depth"),
                                    "escalation_reason": request.get("escalation_reason"),
                                    "reason_is_authorization_proof": False}
                rec.update(state=state, saved_at=now(), result=out, result_sha256=digest(out))
                atomic_json(fd, name, rec)
                returned = copy.deepcopy(out)
                returned["saved_to"] = result_path
                returned["persistence"] = {"key": key, "path": result_path, "status": state, "reused": False,
                                            "saved_at": rec["saved_at"], "automatic_retry": False}
                return returned
            finally:
                if job is not None:
                    os.close(job)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return status_result("storage_error", "Private result storage rejected: %s; no automatic scan or retry." % str(exc)[:240], key)
