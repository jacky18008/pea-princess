#!/usr/bin/env python3
"""Dependency-free HTTP fetch for vet-flat scripts.

Why curl and not urllib: the macOS system Python (3.9, LibreSSL 2.8) fails TLS
against several UK public hosts (e.g. data.police.uk). curl on the same machine
works. So all network I/O goes through curl; Python only parses.

Every result carries: url, final_url, status, content_type, body, retrieved_at,
from_cache, ok, note. "ok" is a CONTENT assertion, never just HTTP 200 — several
sources return 200 with the wrong page.
"""
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlsplit

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
TOOL_UA = "vet-flat/0.1 (flat-vetting research; contact via project page)"
# Where fetched bodies are kept. $VETFLAT_CACHE, else ~/.cache/vet-flat - but only if it can
# be written to: an unwritable cache
# directory used to turn every cache miss into "curl error 56" while cache hits kept working.
# Codex's default workspace-write sandbox denies writes under the home directory, which is
# exactly that case (found 2026-09-07). cache_dir() therefore falls back, in order, to
# a per-user $TMPDIR/vet-flat directory and ./.vet-flat-cache, then a fresh temp directory.
CACHE_DIR = os.environ.get("VETFLAT_CACHE",
                           os.path.join(os.path.expanduser("~"), ".cache", "vet-flat"))
_cache_dir_resolved = None
_last_hit = {}


def cache_dir():
    """Choose a writable, owned, non-shared cache directory, once per process."""
    global _cache_dir_resolved
    if _cache_dir_resolved:
        return _cache_dir_resolved
    candidates = [CACHE_DIR,
                  os.path.join(tempfile.gettempdir(), "vet-flat-%s" % getattr(os, "getuid", lambda: "user")()),
                  os.path.join(os.getcwd(), ".vet-flat-cache")]
    for cand in candidates:
        try:
            os.makedirs(cand, mode=0o700, exist_ok=True)
            info = os.lstat(cand)
            if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o022
                    or (hasattr(os, "geteuid") and info.st_uid != os.geteuid())):
                continue
            fd, probe = tempfile.mkstemp(prefix=".write-probe-", dir=cand)
            os.close(fd)
            os.remove(probe)
        except OSError:
            continue
        _cache_dir_resolved = cand
        return cand
    _cache_dir_resolved = tempfile.mkdtemp(prefix="vet-flat-cache-")
    return _cache_dir_resolved


def _curl_note(returncode, stderr):
    note = f"curl error {returncode}: {(stderr or '').strip()[:200]}"
    if returncode in (23, 56):
        note += f"; curl could not write the body - is the cache directory writable? ({cache_dir()})"
    return note


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _host(url):
    return url.split("//", 1)[-1].split("/", 1)[0].lower()


def _throttle(url, min_gap):
    h = _host(url)
    last = _last_hit.get(h)
    if last is not None:
        wait = min_gap - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
    _last_hit[h] = time.time()


def _cache_path(key):
    return os.path.join(cache_dir(), hashlib.sha1(key.encode("utf-8")).hexdigest())


def _read_regular(path, binary=False):
    """Cache entries are regular files, never links to another file on the host."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("cache entry is not a regular file")
        with os.fdopen(fd, "rb") as fh:
            fd = None
            data = fh.read()
        return data if binary else data.decode("utf-8", errors="replace")
    finally:
        if fd is not None:
            os.close(fd)


def _temporary_path(folder):
    fd, path = tempfile.mkstemp(prefix=".fetch-", dir=folder)
    os.close(fd)
    return path


def _atomic_json(path, value):
    temporary = _temporary_path(os.path.dirname(path))
    try:
        with open(temporary, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _valid_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not any(ord(ch) < 32 for ch in url))
    except (TypeError, ValueError):
        return False


def _config_value(value, multiline=False):
    """Quote one curl-config value without allowing a new config directive."""
    if not isinstance(value, str):
        raise ValueError("curl request values must be strings")
    permitted = "\r\n\t\v" if multiline else ""
    if any((ord(ch) < 32 and ch not in permitted) or ord(ch) == 127 for ch in value):
        raise ValueError("control character in curl request")
    escapes = {"\\": "\\\\", '"': '\\"', "\r": "\\r", "\n": "\\n", "\t": "\\t", "\v": "\\v"}
    return '"' + "".join(escapes.get(ch, ch) for ch in value) + '"'


def _curl_command(url, path, timeout, ua, headers, method="GET", data=None):
    # -q must be first: local curl config must not add uploads or extra output files.
    # URL and redirect protocols are explicit; file:// and curl option injection are not HTTP.
    cmd = ["curl", "-q", "--globoff", "--proto", "=http,https", "--proto-redir", "=http,https",
           "-sS", "-m", str(timeout), "-o", path,
           "-w", "%{http_code}\t%{content_type}\t%{url_effective}"]
    config = ["url = " + _config_value(url), "user-agent = " + _config_value(ua)]
    custom_headers = False
    for k, v in headers.items():
        if not isinstance(k, str) or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", k):
            raise ValueError("invalid HTTP header name")
        _config_value(v)  # HTTP headers never admit CR/LF, even escaped in a config file.
        if k.lower() == "accept-encoding" and v == "identity":
            continue  # curl requests an uncompressed body by default; no custom header needed.
        custom_headers = True
        config.append("header = " + _config_value(k + ": " + v))
    if method.upper() == "POST":
        config += ['request = "POST"', "data-raw = " + _config_value(data or "", multiline=True)]
    query_credentials = any(any(marker in key.lower() for marker in
                               ("key", "token", "secret", "password", "signature", "auth"))
                            for key, _ in parse_qsl(urlsplit(url).query))
    # curl forwards arbitrary custom headers on redirects. Fail closed for custom
    # headers, POST bodies and credential query URLs, including same-host redirects;
    # a caller must choose the final endpoint instead of leaking data across origins.
    if method.upper() == "GET" and not custom_headers and not query_credentials:
        cmd += ["-L"]
    # URL, headers and body stay in a stdin pipe, not ps-visible argv or a config file.
    return cmd + ["--config", "-"], "\n".join(config) + "\n"


def fetch(url, ua=BROWSER_UA, headers=None, method="GET", data=None, timeout=20,
          min_gap=1.2, cache_ttl=86400, expect=None, verbose=False):
    """Fetch a URL via curl with per-host throttling and an on-disk cache.

    expect: optional callable(body:str)->bool. If it returns False the result has
    ok=False and note="content assertion failed" (status is still reported).
    cache_ttl=0: bypass cache reads and leave no response/config file behind.
    URLs, headers and POST data travel through stdin, never curl argv. Requests
    with custom headers, POST data or credential query parameters do not follow
    redirects; choose their final endpoint explicitly. Cached URL metadata can
    contain credentials, so cache files are private, not anonymous or encrypted.
    """
    if not _valid_url(url):
        return dict(url=url, final_url=None, status=0, content_type=None, body="",
                    retrieved_at=now_iso(), from_cache=False, ok=False,
                    note="only HTTP(S) URLs without embedded credentials are accepted")
    headers = dict(headers or {})
    headers.setdefault("Accept-Encoding", "identity")  # this Mac's curl has no brotli
    key = "\n".join([method, url, data or "", ua] + [f"{k}: {v}" for k, v in sorted(headers.items())])
    cpath = _cache_path(key)
    meta = None
    if cache_ttl and os.path.exists(cpath + ".json"):
        try:
            meta = json.loads(_read_regular(cpath + ".json"))
            age = time.time() - meta.get("_ts", 0)
            raw = _read_regular(cpath, binary=True)
            if (0 <= age <= cache_ttl and 200 <= meta.get("status", 0) < 300
                    and meta.get("_body_sha256") == hashlib.sha256(raw).hexdigest()):
                body = raw.decode("utf-8", errors="replace")
                res = dict(meta)
                res.update(body=body, from_cache=True)
                res.pop("_ts", None)
                res.pop("_body_sha256", None)
                if expect is not None:
                    res["ok"] = bool(expect(body))
                    if not res["ok"]:
                        res["note"] = "content assertion failed (cached copy)"
                return res
        except Exception:
            meta = None
    _throttle(url, min_gap)
    temporary = _temporary_path(cache_dir())
    try:
        try:
            cmd, config = _curl_command(url, temporary, timeout, ua, headers, method, data)
        except ValueError:
            return dict(url=url, final_url=None, status=0, content_type=None, body="",
                        retrieved_at=now_iso(), from_cache=False, ok=False,
                        note="invalid HTTP request: headers or request values contain invalid characters")
        if verbose:
            print("  $ " + " ".join(cmd[:12]) + " ... (request via stdin)", file=sys.stderr)
        try:
            out = subprocess.run(cmd, input=config, capture_output=True, text=True, timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            return dict(url=url, final_url=None, status=0, content_type=None, body="",
                        retrieved_at=now_iso(), from_cache=False, ok=False, note="curl timeout")
        raw = _read_regular(temporary, binary=True)
        if out.returncode == 0 and cache_ttl:
            # Never let curl truncate a live cache entry or follow a pre-existing link.
            # Metadata stores the digest so concurrent writers cannot mix body and metadata.
            os.replace(temporary, cpath)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    if out.returncode != 0:
        return dict(url=url, final_url=None, status=0, content_type=None, body="",
                    retrieved_at=now_iso(), from_cache=False, ok=False,
                    note=_curl_note(out.returncode, out.stderr))
    parts = (out.stdout or "").split("\t")
    status = int(parts[0]) if parts and parts[0].isdigit() else 0
    ctype = parts[1] if len(parts) > 1 else None
    final = parts[2] if len(parts) > 2 else None
    body = raw.decode("utf-8", errors="replace")
    res = dict(url=url, final_url=final, status=status, content_type=ctype, body=body,
               retrieved_at=now_iso(), from_cache=False, ok=(200 <= status < 300), note="")
    if res["ok"] and expect is not None and not expect(body):
        res["ok"] = False
        res["note"] = "content assertion failed"
    elif not res["ok"]:
        res["note"] = f"http {status}"
    meta = {k: v for k, v in res.items() if k != "body"}
    meta["_ts"] = time.time()
    meta["_body_sha256"] = hashlib.sha256(raw).hexdigest()
    if 200 <= res["status"] < 300 and cache_ttl:  # never cache failures (a 504 replayed is a bug)
        _atomic_json(cpath + ".json", meta)
    elif cache_ttl and os.path.exists(cpath + ".json"):
        os.remove(cpath + ".json")
    return res


def get(url, **kw):
    return fetch(url, **kw)


def post_json(url, payload, **kw):
    headers = kw.pop("headers", {}) or {}
    headers["Content-Type"] = "application/json"
    return fetch(url, method="POST", data=json.dumps(payload), headers=headers, **kw)


def fetch_binary(url, dest_path, ua=BROWSER_UA, headers=None, timeout=30, min_gap=1.2,
                 expect_content_type=None, verbose=False):
    """Download a URL straight to dest_path. For bytes that must not be decoded.

    fetch() reads the body as UTF-8 with errors="replace", which silently
    destroys binary content, so images come through here instead. There is no
    on-disk cache: some image licences forbid keeping a copy (see
    scripts/streetview.py), so the CALLER decides where the bytes live and for
    how long. Returns the usual envelope minus `body`, plus `path` and `bytes`.

    expect_content_type: optional prefix, e.g. "image/". A 200 whose
    Content-Type does not start with it is ok=False — several hosts answer a
    missing image with an HTML error page and a 200.
    """
    base = dict(url=url, final_url=None, status=0, content_type=None, path=dest_path,
                bytes=0, retrieved_at=now_iso(), from_cache=False, ok=False, note="")
    if not _valid_url(url):
        base["note"] = "only HTTP(S) URLs without embedded credentials are accepted"
        return base
    headers = dict(headers or {})
    headers.setdefault("Accept-Encoding", "identity")
    d = os.path.dirname(os.path.abspath(dest_path))
    if d:
        os.makedirs(d, exist_ok=True)
    _throttle(url, min_gap)
    temporary = _temporary_path(d)
    try:
        try:
            cmd, config = _curl_command(url, temporary, timeout, ua, headers)
        except ValueError:
            base["note"] = "invalid HTTP request: headers or request values contain invalid characters"
            return base
        if verbose:
            print("  $ " + " ".join(cmd[:12]) + " ... (request via stdin)", file=sys.stderr)
        try:
            out = subprocess.run(cmd, input=config, capture_output=True, text=True, timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            base["note"] = "curl timeout"
            return base
        if out.returncode != 0:
            base["note"] = f"curl error {out.returncode}: {out.stderr.strip()[:200]}"
            return base
        parts = (out.stdout or "").split("\t")
        base["status"] = int(parts[0]) if parts and parts[0].isdigit() else 0
        base["content_type"] = parts[1] if len(parts) > 1 else None
        base["final_url"] = parts[2] if len(parts) > 2 else None
        base["ok"] = 200 <= base["status"] < 300
        if not base["ok"]:
            base["note"] = f"http {base['status']}"
        elif expect_content_type and not (base["content_type"] or "").startswith(expect_content_type):
            base["ok"] = False
            base["note"] = ("expected content-type %s, got %s — a 200 with the wrong body"
                            % (expect_content_type, base["content_type"]))
        if base["ok"]:
            base["bytes"] = os.path.getsize(temporary)
            os.replace(temporary, dest_path)
        return base
    finally:
        # Failed downloads leave an existing destination untouched, never a partial image.
        if os.path.exists(temporary):
            os.remove(temporary)
