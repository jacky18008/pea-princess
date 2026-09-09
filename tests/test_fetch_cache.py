# -*- coding: utf-8 -*-
"""The fetch cache must land somewhere writable, whatever the sandbox forbids.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

Codex's workspace-write sandbox denies writes under the home directory; curl writes every
fetched body straight into the cache file; so an unwritable cache directory turned every
cache miss into "curl error 56" while cache hits kept working (found 2026-09-07).
"""
from __future__ import unicode_literals

import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import _fetch  # noqa: E402


def with_cache_env(value):
    old = os.environ.get("VETFLAT_CACHE")
    if value is None:
        os.environ.pop("VETFLAT_CACHE", None)
    else:
        os.environ["VETFLAT_CACHE"] = value
    mod = importlib.reload(_fetch)
    return mod, old


def restore(old):
    if old is None:
        os.environ.pop("VETFLAT_CACHE", None)
    else:
        os.environ["VETFLAT_CACHE"] = old
    importlib.reload(_fetch)


class TestCacheDir(unittest.TestCase):
    def test_symlink_and_shared_directories_are_not_selected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td, "target")
            target.mkdir()
            link = Path(td, "link")
            link.symlink_to(target, target_is_directory=True)
            for candidate in (link, target):
                if candidate == target:
                    candidate.chmod(0o777)
                mod, old = with_cache_env(str(candidate))
                try:
                    self.assertNotEqual(str(candidate), mod.cache_dir())
                finally:
                    restore(old)
    def test_a_writable_cache_dir_is_used_as_it_is(self):
        want = tempfile.mkdtemp(prefix="vetflat-cache-test-")
        mod, old = with_cache_env(want)
        try:
            self.assertEqual(want, mod.cache_dir())
            self.assertTrue(mod._cache_path("k").startswith(want))
        finally:
            restore(old)
            shutil.rmtree(want, ignore_errors=True)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can write anywhere")
    def test_an_unwritable_cache_dir_falls_back_to_a_writable_one(self):
        ro = tempfile.mkdtemp(prefix="vetflat-cache-ro-")
        os.chmod(ro, 0o500)
        mod, old = with_cache_env(ro)
        try:
            got = mod.cache_dir()
            self.assertNotEqual(ro, got)
            self.assertTrue(os.path.isdir(got), got)
            probe = os.path.join(got, "probe-from-test")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            self.assertEqual(got, mod.cache_dir(), "decided once per process")
        finally:
            restore(old)
            os.chmod(ro, 0o700)
            shutil.rmtree(ro, ignore_errors=True)

    def test_a_curl_write_error_names_the_cache_directory(self):
        note = _fetch._curl_note(56, "curl: (56) Failure writing output to destination")
        self.assertIn("curl error 56", note)
        self.assertIn("cache directory writable", note)
        self.assertIn(_fetch.cache_dir(), note)
        self.assertNotIn("cache directory", _fetch._curl_note(6, "could not resolve host"))


class TestSafeTransfers(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.mod, self.old = with_cache_env(self.folder.name)
        self.url = "https://example.invalid/data"
        self.calls = []
        self.configs = []

    def tearDown(self):
        restore(self.old)
        self.folder.cleanup()

    def transfer(self, body=b"complete body", returncode=0, status=200, content_type="text/plain",
                 timeout=False):
        def run(cmd, **kw):
            self.calls.append(cmd)
            self.configs.append(kw.get("input", ""))
            Path(cmd[cmd.index("-o") + 1]).write_bytes(body)
            if timeout:
                raise self.mod.subprocess.TimeoutExpired(cmd, 20)
            return SimpleNamespace(returncode=returncode,
                                   stdout="%s\t%s\t%s" % (status, content_type, self.url), stderr="")
        return mock.patch.object(self.mod.subprocess, "run", side_effect=run)

    def cache_path(self):
        key = "\n".join(["GET", self.url, "", self.mod.BROWSER_UA, "Accept-Encoding: identity"])
        return Path(self.mod._cache_path(key))

    def test_cache_body_and_metadata_links_do_not_overwrite_their_targets(self):
        body = self.cache_path()
        for destination in (body, Path(str(body) + ".json")):
            marker = Path(self.folder.name, "marker-" + destination.suffix.replace(".", "meta"))
            marker.write_text("keep this")
            destination.symlink_to(marker)
            with self.transfer():
                self.assertTrue(self.mod.fetch(self.url, min_gap=0)["ok"])
            self.assertEqual(marker.read_text(), "keep this")
            self.assertFalse(destination.is_symlink())
            body.unlink(missing_ok=True)
            Path(str(body) + ".json").unlink(missing_ok=True)

    def test_partial_failed_refresh_preserves_complete_cached_response(self):
        with self.transfer():
            self.mod.fetch(self.url, min_gap=0)
        for timeout in (False, True):
            with self.transfer(b"partial", returncode=56, timeout=timeout):
                failed = self.mod.fetch(self.url, cache_ttl=0, min_gap=0)
                self.assertFalse(failed["ok"])
            with mock.patch.object(self.mod.subprocess, "run", side_effect=AssertionError("unexpected fetch")):
                cached = self.mod.fetch(self.url, min_gap=0)
            self.assertTrue(cached["from_cache"])
            self.assertEqual(cached["body"], "complete body")
        self.assertFalse(list(Path(self.folder.name).glob(".fetch-*")))

    def test_mismatched_cache_body_is_not_returned_as_verified_cached_data(self):
        with self.transfer():
            self.mod.fetch(self.url, min_gap=0)
        self.cache_path().write_text("mismatched concurrent response")
        with self.transfer(b"new verified body"):
            result = self.mod.fetch(self.url, min_gap=0)
        self.assertFalse(result["from_cache"])
        self.assertEqual(result["body"], "new verified body")
        self.assertEqual(self.cache_path().stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(str(self.cache_path()) + ".json").stat().st_mode & 0o777, 0o600)

    def test_binary_failure_preserves_destination_and_success_replaces_link(self):
        marker = Path(self.folder.name, "original")
        marker.write_bytes(b"original")
        destination = Path(self.folder.name, "image")
        destination.symlink_to(marker)
        for options in ({"returncode": 56}, {"timeout": True}, {"status": 500},
                        {"content_type": "text/html"}):
            with self.transfer(b"partial", **options):
                failed = self.mod.fetch_binary(self.url, str(destination), min_gap=0,
                                               expect_content_type="image/")
            self.assertFalse(failed["ok"])
            self.assertEqual(marker.read_bytes(), b"original")
            self.assertTrue(destination.is_symlink())
        with self.transfer(b"complete image", content_type="image/png"):
            complete = self.mod.fetch_binary(self.url, str(destination), min_gap=0,
                                             expect_content_type="image/")
        self.assertTrue(complete["ok"])
        self.assertEqual(marker.read_bytes(), b"original")
        self.assertEqual(destination.read_bytes(), b"complete image")
        self.assertFalse(destination.is_symlink())
        self.assertFalse(list(Path(self.folder.name).glob(".fetch-*")))

    def test_non_http_and_option_urls_never_invoke_curl(self):
        with mock.patch.object(self.mod.subprocess, "run", side_effect=AssertionError("unexpected fetch")):
            for url in ("file:///tmp/example", "gopher://localhost/", "--config=/tmp/example",
                        "https://user:password@example.invalid/", "https://example.invalid/\nnext"):
                self.assertFalse(self.mod.fetch(url)["ok"])
                self.assertFalse(self.mod.fetch_binary(url, str(Path(self.folder.name, "image")))["ok"])

    def test_curl_protocol_limits_and_literal_post_data_are_explicit(self):
        with self.transfer():
            self.mod.fetch(self.url, method="POST", data="@local-file", min_gap=0)
        cmd = self.calls[-1]
        self.assertEqual(cmd[:2], ["curl", "-q"])
        self.assertEqual(cmd[cmd.index("--proto") + 1], "=http,https")
        self.assertEqual(cmd[cmd.index("--proto-redir") + 1], "=http,https")
        self.assertEqual(cmd[-2:], ["--config", "-"])
        self.assertIn('data-raw = "@local-file"', self.configs[-1])
        self.assertNotIn(self.url, cmd)
        self.assertNotIn("-L", cmd, "POST data cannot follow a redirect to another origin")

    def test_credentials_and_request_body_never_appear_in_process_arguments(self):
        url = self.url + "?key=FAKE_QUERY_CREDENTIAL"
        headers = {"Authorization": "Bearer FAKE_HEADER_CREDENTIAL"}
        payload = {"message": 'line one\nurl = "https://unwanted.invalid/"', "secret": "FAKE_BODY_SECRET"}
        with self.transfer():
            result = self.mod.post_json(url, payload, headers=headers, cache_ttl=0, min_gap=0)
        self.assertTrue(result["ok"])
        argv = " ".join(self.calls[-1])
        for private in (url, "FAKE_QUERY_CREDENTIAL", "FAKE_HEADER_CREDENTIAL", "FAKE_BODY_SECRET"):
            self.assertNotIn(private, argv)
            self.assertIn(private, self.configs[-1])
        self.assertEqual(sum(line.startswith("url = ") for line in self.configs[-1].splitlines()), 1)
        self.assertNotIn("-L", self.calls[-1])
        self.assertEqual(list(Path(self.folder.name).iterdir()), [], "no cached body, metadata or config file")

    def test_authenticated_timeout_leaves_no_request_or_partial_response_file(self):
        with self.transfer(b"partial", timeout=True):
            result = self.mod.fetch(self.url, headers={"Authorization": "Bearer FAKE_CREDENTIAL"},
                                    cache_ttl=0, min_gap=0)
        self.assertFalse(result["ok"])
        self.assertNotIn("FAKE_CREDENTIAL", " ".join(self.calls[-1]))
        self.assertEqual(list(Path(self.folder.name).iterdir()), [])

    def test_uncached_api_error_keeps_response_body_without_persisting_it(self):
        body = b'{"error":{"type":"rate_limit"}}'
        with self.transfer(body, status=429, content_type="application/json"):
            result = self.mod.post_json(self.url, {"message": "test"},
                                        headers={"Authorization": "Bearer FAKE_CREDENTIAL"},
                                        cache_ttl=0, min_gap=0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 429)
        self.assertEqual(result["body"], body.decode())
        self.assertEqual(list(Path(self.folder.name).iterdir()), [])

    def test_binary_transfer_hides_key_url_from_arguments(self):
        destination = Path(self.folder.name, "image")
        with self.transfer(b"image", content_type="image/png"):
            result = self.mod.fetch_binary(self.url + "?key=FAKE_KEY", str(destination), min_gap=0)
        self.assertTrue(result["ok"])
        self.assertNotIn("FAKE_KEY", " ".join(self.calls[-1]))
        self.assertIn("FAKE_KEY", self.configs[-1])
        self.assertNotIn("-L", self.calls[-1])

    def test_custom_headers_and_control_injection_do_not_cross_redirect_boundary(self):
        with self.transfer(status=302):
            result = self.mod.fetch(self.url, headers={"X-Api-Token": "FAKE_TOKEN"}, min_gap=0)
        self.assertFalse(result["ok"])
        self.assertNotIn("-L", self.calls[-1])
        with mock.patch.object(self.mod.subprocess, "run", side_effect=AssertionError("unexpected fetch")):
            for headers in ({"Authorization": "Bearer token\nurl = other"},
                            {"Bad\rHeader": "value"}, {"@local-header-file": "value"}):
                self.assertFalse(self.mod.fetch(self.url, headers=headers, cache_ttl=0, min_gap=0)["ok"])
        with self.transfer():
            self.mod.fetch(self.url, cache_ttl=0, min_gap=0)
        self.assertIn("-L", self.calls[-1], "plain public GETs retain HTTP redirect support")


if __name__ == "__main__":
    unittest.main()
