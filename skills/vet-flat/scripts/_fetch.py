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
import subprocess
import sys
import time
from datetime import datetime, timezone

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
TOOL_UA = "vet-flat/0.1 (flat-vetting research; contact via project page)"
CACHE_DIR = os.environ.get("VETFLAT_CACHE",
                           os.path.join(os.path.expanduser("~"), ".cache", "vet-flat"))
_last_hit = {}


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
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, hashlib.sha1(key.encode("utf-8")).hexdigest())


def fetch(url, ua=BROWSER_UA, headers=None, method="GET", data=None, timeout=20,
          min_gap=1.2, cache_ttl=86400, expect=None, verbose=False):
    """Fetch a URL via curl with per-host throttling and an on-disk cache.

    expect: optional callable(body:str)->bool. If it returns False the result has
    ok=False and note="content assertion failed" (status is still reported).
    """
    headers = dict(headers or {})
    headers.setdefault("Accept-Encoding", "identity")  # this Mac's curl has no brotli
    key = "\n".join([method, url, data or "", ua] + [f"{k}: {v}" for k, v in sorted(headers.items())])
    cpath = _cache_path(key)
    meta = None
    if cache_ttl and os.path.exists(cpath + ".json"):
        try:
            meta = json.load(open(cpath + ".json", encoding="utf-8"))
            age = time.time() - meta.get("_ts", 0)
            if age <= cache_ttl and os.path.exists(cpath):
                body = open(cpath, encoding="utf-8", errors="replace").read()
                res = dict(meta)
                res.update(body=body, from_cache=True)
                res.pop("_ts", None)
                if expect is not None:
                    res["ok"] = bool(expect(body))
                    if not res["ok"]:
                        res["note"] = "content assertion failed (cached copy)"
                return res
        except Exception:
            meta = None
    _throttle(url, min_gap)
    cmd = ["curl", "-sS", "-L", "-m", str(timeout), "-A", ua, "-o", cpath,
           "-w", "%{http_code}\t%{content_type}\t%{url_effective}"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if method.upper() == "POST":
        cmd += ["-X", "POST", "--data-binary", data or ""]
    cmd.append(url)
    if verbose:
        print("  $ " + " ".join(cmd[:12]) + " ...", file=sys.stderr)
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired:
        return dict(url=url, final_url=None, status=0, content_type=None, body="",
                    retrieved_at=now_iso(), from_cache=False, ok=False, note="curl timeout")
    if out.returncode != 0:
        return dict(url=url, final_url=None, status=0, content_type=None, body="",
                    retrieved_at=now_iso(), from_cache=False, ok=False,
                    note=f"curl error {out.returncode}: {out.stderr.strip()[:200]}")
    parts = (out.stdout or "").split("\t")
    status = int(parts[0]) if parts and parts[0].isdigit() else 0
    ctype = parts[1] if len(parts) > 1 else None
    final = parts[2] if len(parts) > 2 else None
    body = open(cpath, encoding="utf-8", errors="replace").read() if os.path.exists(cpath) else ""
    res = dict(url=url, final_url=final, status=status, content_type=ctype, body=body,
               retrieved_at=now_iso(), from_cache=False, ok=(200 <= status < 300), note="")
    if res["ok"] and expect is not None and not expect(body):
        res["ok"] = False
        res["note"] = "content assertion failed"
    elif not res["ok"]:
        res["note"] = f"http {status}"
    meta = {k: v for k, v in res.items() if k != "body"}
    meta["_ts"] = time.time()
    if 200 <= res["status"] < 300 and cache_ttl:  # never cache failures (a 504 replayed is a bug)
        json.dump(meta, open(cpath + ".json", "w", encoding="utf-8"))
    elif os.path.exists(cpath + ".json"):
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
    headers = dict(headers or {})
    headers.setdefault("Accept-Encoding", "identity")
    d = os.path.dirname(os.path.abspath(dest_path))
    if d:
        os.makedirs(d, exist_ok=True)
    _throttle(url, min_gap)
    cmd = ["curl", "-sS", "-L", "-m", str(timeout), "-A", ua, "-o", dest_path,
           "-w", "%{http_code}\t%{content_type}\t%{url_effective}"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    if verbose:
        print("  $ " + " ".join(cmd[:12]) + " ...", file=sys.stderr)
    base = dict(url=url, final_url=None, status=0, content_type=None, path=dest_path,
                bytes=0, retrieved_at=now_iso(), from_cache=False, ok=False, note="")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
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
    base["bytes"] = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
    base["ok"] = 200 <= base["status"] < 300
    if not base["ok"]:
        base["note"] = f"http {base['status']}"
    elif expect_content_type and not (base["content_type"] or "").startswith(expect_content_type):
        base["ok"] = False
        base["note"] = ("expected content-type %s, got %s — a 200 with the wrong body"
                        % (expect_content_type, base["content_type"]))
    if not base["ok"] and os.path.exists(dest_path):
        os.remove(dest_path)          # never leave a half-written or error-page "image" behind
        base["bytes"] = 0
    return base
