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
import os
import shutil
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
