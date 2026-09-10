#!/usr/bin/env python3
"""One independent, immutable public-page capture after an actor's research.

This is not the original model tool result, an actor-time reconstruction, or
verification of a listing claim. Only the explicit operator domains below are
supported. No redirects, cookies, credentials, proxies, retries or model calls.
Version 2 caps retained responses at 2 MiB within a 10-second request deadline.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import http.client
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path
import queue
import re
import socket
import ssl
import threading
import time
from urllib.parse import quote, urlsplit


ALLOWED_HOSTS = frozenset({"www.foxtons.co.uk", "www.graingerplc.co.uk",
                           "prod.graingerplc.co.uk", "www.getliving.com", "www.fizzyliving.com"})
MAX_BYTES = 2 * 1024 * 1024
TIMEOUT = 10


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new_folder(folder):
    folder = Path(folder).absolute()
    if ".." in folder.parts or any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ValueError("unsafe capture destination")
    if folder.exists():
        raise ValueError("capture destination already exists; overwrite is forbidden")
    missing = []
    parent = folder.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    if not parent.is_dir():
        raise ValueError("capture parent is not a directory")
    for path in reversed(missing):
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    return folder


def _save(path, data):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _url(url):
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError("invalid HTTPS URL")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS
            or parts.username is not None or parts.password is not None
            or parts.port not in (None, 443)):
        raise ValueError("URL must use HTTPS port 443 on an explicitly allowed public operator host")
    target = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if parts.query:
        target += "?" + quote(parts.query, safe="%/:?@!$&'()*+,;=-._~")
    return parts.hostname, target


def _resolve_public(host):
    # A daemon bounds DNS waiting without leaving a later HTTP request running.
    result = queue.Queue(maxsize=1)
    def resolve():
        try:
            result.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except Exception as error:
            result.put(error)
    threading.Thread(target=resolve, daemon=True).start()
    try:
        rows = result.get(timeout=TIMEOUT)
    except queue.Empty as error:
        raise TimeoutError("public DNS lookup timed out") from error
    if isinstance(rows, Exception):
        raise rows
    addresses = []
    for row in rows:
        address = row[4][0]
        ip = ipaddress.ip_address(address)
        if ("%" in address or not ip.is_global or ip.is_private or ip.is_loopback
                or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified
                or getattr(ip, "ipv4_mapped", None) is not None
                or getattr(ip, "sixtofour", None) is not None or getattr(ip, "teredo", None) is not None):
            raise ValueError("DNS included a nonpublic or translated address")
        if str(ip) not in addresses:
            addresses.append(str(ip))
    if not addresses:
        raise ValueError("public DNS returned no addresses")
    return addresses


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("public capture exceeded its 10-second deadline")
    return remaining


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        # Load compiled system trust paths explicitly, ignoring SSL_CERT_* env overrides.
        defaults = ssl.get_default_verify_paths()
        cafile = defaults.openssl_cafile if os.path.isfile(defaults.openssl_cafile or "") else None
        capath = defaults.openssl_capath if os.path.isdir(defaults.openssl_capath or "") else None
        if not cafile and not capath:
            raise ValueError("system TLS trust store is unavailable")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cafile=cafile, capath=capath)
        super().__init__(host, port=443, timeout=timeout, context=context)
        self.address = address

    def connect(self):
        deadline = time.monotonic() + self.timeout
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(_remaining(deadline))
            # Numeric vetted address only: never resolve the hostname again.
            sock.connect((self.address, 443))
            sock.settimeout(_remaining(deadline))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _open_response(host, target, address, timeout):
    deadline = time.monotonic() + timeout
    connection = _PinnedHTTPSConnection(host, address, timeout)
    try:
        connection.connect()
        connection.sock.settimeout(_remaining(deadline))
        connection.request("GET", target, headers={"User-Agent": "PeaPrincessSourceCapture/1.0",
                           "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "identity",
                           "Connection": "close"})
        connection.sock.settimeout(_remaining(deadline))
        return connection, connection.getresponse()
    except Exception:
        connection.close()
        raise


class _VisibleText(HTMLParser):
    SKIP = {"script", "style", "head", "template", "noscript", "svg", "nav", "header", "footer"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    BLOCK = {"p", "div", "section", "article", "header", "footer", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.parts = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        style = (attrs.get("style") or "").replace(" ", "").lower()
        hidden = (tag in self.SKIP or "hidden" in attrs or attrs.get("aria-hidden") == "true"
                  or "display:none" in style or "visibility:hidden" in style
                  or any(item[1] for item in self.stack))
        if not hidden and tag in self.BLOCK:
            self.parts.append("\n")
        if tag not in self.VOID:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag):
        if not any(item[1] for item in self.stack) and tag in self.BLOCK:
            self.parts.append("\n")
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(item[1] for item in self.stack):
            self.parts.append(data)


def _extract(body, content_type):
    match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", content_type, re.I)
    if not match:
        match = re.search(r"charset\s*=\s*[\"']?([^;\s\"'/>]+)", body[:4096].decode("ascii", errors="ignore"), re.I)
    parser = _VisibleText()
    parser.feed(body.decode(match.group(1) if match else "utf-8"))
    parser.close()
    return "\n".join(line for line in (" ".join(line.split()) for line in "".join(parser.parts).splitlines()) if line) + "\n"


def capture(url, folder):
    """Make one capture in a new private folder; network/content failures are receipts."""
    folder = _new_folder(folder)
    requested_url = url if isinstance(url, str) else None
    receipt = {"version": 2, "ok": False, "requested_url": requested_url, "captured_at": _now(),
               "role": "independent_host_capture_after_actor", "source_claims_verified": False,
               "note": "Separate later host capture, not the original model tool result or exact actor-time reconstruction. HTML text extraction is not rendered visual review.",
               "method": "GET", "status": None, "error": None, "body": None, "text": None,
               "declared_content_length": None,
               "timeout_seconds": TIMEOUT, "max_body_bytes": MAX_BYTES, "redirects_followed": 0}
    deadline = time.monotonic() + TIMEOUT
    connection, response, body = None, None, bytearray()
    complete = False
    try:
        host, target = _url(url)
        addresses = _resolve_public(host)
        receipt["resolved_addresses"] = addresses
        receipt["connected_address"] = addresses[0]
        connection, response = _open_response(host, target, addresses[0], _remaining(deadline))
        receipt["status"] = response.status
        content_type = response.getheader("Content-Type", "")
        encoding = response.getheader("Content-Encoding", "identity").lower()
        receipt["content_type"] = content_type
        receipt["content_encoding"] = encoding
        length = response.getheader("Content-Length")
        expected = int(length) if length is not None else None
        receipt["declared_content_length"] = expected
        if expected is not None and expected < 0:
            raise ValueError("invalid content length")
        if 300 <= response.status < 400:
            receipt["redirect_location"] = response.getheader("Location")
        while len(body) < MAX_BYTES:
            if getattr(connection, "sock", None) is not None:
                connection.sock.settimeout(_remaining(deadline))
            else:
                _remaining(deadline)
            chunk = response.read(min(65536, MAX_BYTES - len(body)))
            if not chunk:
                complete = expected is None or len(body) == expected
                break
            body.extend(chunk)
            if expected is not None and len(body) == expected:
                complete = True
                break
        if not complete:
            raise ValueError("response body limit reached or body incomplete")
        if not 200 <= response.status < 300:
            raise ValueError("HTTP status %s; redirects are never followed" % response.status)
        if content_type.split(";", 1)[0].strip().lower() not in ("text/html", "application/xhtml+xml"):
            raise ValueError("response is not HTML")
        if encoding not in ("", "identity"):
            raise ValueError("encoded response is retained raw; text extraction refused")
        text = _extract(bytes(body), content_type)
        if not text.strip():
            raise ValueError("HTML contained no extracted visible text")
        receipt["text"] = _save(folder / "text.txt", text.encode("utf-8"))
        receipt["ok"] = True
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)[:300]
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception as error:
                receipt["close_error"] = type(error).__name__ + ": " + str(error)[:100]
    if response is not None:
        receipt["body"] = {**_save(folder / "body.bin", bytes(body)), "complete": complete}
    receipt["completed_at"] = _now()
    receipt.update(url=requested_url, source_url=requested_url, retrieved_at=receipt["completed_at"],
                   http_status=receipt["status"], text_path="text.txt" if receipt["text"] else None,
                   text_sha256=receipt["text"]["sha256"] if receipt["text"] else None,
                   body_path="body.bin" if receipt["body"] else None,
                   body_sha256=receipt["body"]["sha256"] if receipt["body"] else None)
    metadata = _save(folder / "receipt.json", (json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    return {**receipt, "receipt_path": metadata["path"], "receipt_sha256": metadata["sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = capture(args.url, args.folder)
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
