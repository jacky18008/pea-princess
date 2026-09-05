"""Offline tests for scripts/streetview.py (street-level imagery).

No network: the two fetch helpers are replaced with stubs. What is tested is the
arithmetic (headings, cost), the URL building, the fact that no key ever reaches
a manifest, and the no-key behaviour of each subcommand.

Run: python3 -m unittest tests/test_streetview.py
"""
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import streetview  # noqa: E402

FAKE_KEY = "AIzaSyFAKE-key-do-not-use-0000000000000"


class KeylessMixin(unittest.TestCase):
    """Blind the module to any real .env or environment key, both ways."""

    def setUp(self):
        self._env = {k: os.environ.pop(k, None)
                     for k in ("GOOGLE_MAPS_KEY", "MAPILLARY_TOKEN")}
        self._load_env = streetview.load_env
        streetview.load_env = lambda path=None: {}

    def tearDown(self):
        streetview.load_env = self._load_env
        for k, v in self._env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)


# ------------------------------------------------------------- headings -----
class TestHeading(unittest.TestCase):
    def test_cardinals_from_one_point_to_another(self):
        for dlat, dlng, want in ((1, 0, 0.0), (0, 1, 90.0), (-1, 0, 180.0), (0, -1, 270.0)):
            got = streetview.heading_toward(51.5, -0.1,
                                            51.5 + dlat * 0.001, -0.1 + dlng * 0.001)
            self.assertAlmostEqual(got, want, delta=0.5, msg="%s,%s" % (dlat, dlng))

    def test_north_east_is_about_forty_five(self):
        got = streetview.heading_toward(
            51.5, -0.1, 51.5 + 0.001, -0.1 + 0.001 / math.cos(math.radians(51.5)))
        self.assertAlmostEqual(got, 45.0, delta=1.0)

    def test_direction_is_reversible(self):
        """Camera->building and building->camera differ by 180 degrees."""
        a, b = (51.50450, -0.08650), (51.50470, -0.08620)
        there = streetview.heading_toward(a[0], a[1], b[0], b[1])
        back = streetview.heading_toward(b[0], b[1], a[0], a[1])
        self.assertAlmostEqual((there - back) % 360.0, 180.0, delta=0.5)

    def test_range_is_zero_to_three_sixty(self):
        h = streetview.heading_toward(51.5, -0.1, 51.499, -0.101)
        self.assertTrue(0.0 <= h < 360.0)

    def test_headings_around_are_four_ninety_degree_steps(self):
        self.assertEqual(streetview.headings_around(37.0), [37.0, 127.0, 217.0, 307.0])

    def test_headings_around_wraps_past_north(self):
        self.assertEqual(streetview.headings_around(300.0), [300.0, 30.0, 120.0, 210.0])

    def test_plan_headings_precedence(self):
        # explicit --headings wins over --toward
        self.assertEqual(streetview.plan_headings("10,20", 300.0), [10.0, 20.0])
        # --toward alone gives four views around the target
        self.assertEqual(streetview.plan_headings(None, 90.0), [90.0, 180.0, 270.0, 0.0])
        # neither gives the cardinals
        self.assertEqual(streetview.plan_headings(None, None), [0.0, 90.0, 180.0, 270.0])

    def test_plan_headings_dedupes_normalises_and_caps_at_four(self):
        self.assertEqual(streetview.plan_headings("0,360,0,90,180,270,45", None),
                         [0.0, 90.0, 180.0, 270.0])


# ------------------------------------------------------ parameter clamps ----
class TestParameterLimits(unittest.TestCase):
    def test_size_is_capped_at_the_documented_640(self):
        self.assertEqual(streetview.parse_size("640x640"), (640, 640))
        self.assertEqual(streetview.parse_size("2048x1024"), (640, 640))
        self.assertEqual(streetview.parse_size(" 400 X 300 "), (400, 300))

    def test_bad_size_raises(self):
        for bad in ("", None, "640", "640*640", "sixhundred"):
            self.assertRaises(ValueError, streetview.parse_size, bad)

    def test_fov_and_pitch_clamps(self):
        self.assertEqual(streetview.clamp_fov(90), 90)
        self.assertEqual(streetview.clamp_fov(999), streetview.MAX_FOV_DEG)
        self.assertEqual(streetview.clamp_fov(0), streetview.MIN_FOV_DEG)
        self.assertEqual(streetview.clamp_pitch(0), 0)
        self.assertEqual(streetview.clamp_pitch(120), 90)
        self.assertEqual(streetview.clamp_pitch(-120), -90)


# ------------------------------------------------------ URLs and secrets ----
class TestUrlBuilding(unittest.TestCase):
    def test_metadata_url_shape(self):
        u = streetview.metadata_url(51.5045, -0.0865, FAKE_KEY, radius=50)
        self.assertTrue(u.startswith("https://maps.googleapis.com/maps/api/streetview/metadata?"))
        self.assertIn("location=51.5045%2C-0.0865", u)
        self.assertIn("radius=50", u)
        self.assertIn("key=" + FAKE_KEY, u)

    def test_metadata_url_by_pano_drops_location(self):
        u = streetview.metadata_url(None, None, FAKE_KEY, pano="PANO123")
        self.assertIn("pano=PANO123", u)
        self.assertNotIn("location=", u)

    def test_image_url_shape_and_defaults(self):
        u = streetview.image_url(FAKE_KEY, lat=51.5045, lng=-0.0865, heading=123.456)
        self.assertTrue(u.startswith("https://maps.googleapis.com/maps/api/streetview?"))
        self.assertIn("size=640x640", u)
        self.assertIn("heading=123.46", u)
        self.assertIn("fov=90", u)
        self.assertIn("pitch=0", u)
        self.assertIn("return_error_code=true", u)

    def test_image_url_prefers_pano_over_location(self):
        u = streetview.image_url(FAKE_KEY, lat=51.5, lng=-0.1, pano="PANO123")
        self.assertIn("pano=PANO123", u)
        self.assertNotIn("location=", u)

    def test_image_url_normalises_heading(self):
        self.assertIn("heading=10.0", streetview.image_url(FAKE_KEY, pano="P", heading=370))
        self.assertIn("heading=350.0", streetview.image_url(FAKE_KEY, pano="P", heading=-10))


class TestRedaction(unittest.TestCase):
    def test_key_value_is_replaced_not_the_parameter(self):
        u = streetview.image_url(FAKE_KEY, pano="P", heading=0)
        r = streetview.redact_key(u)
        self.assertNotIn(FAKE_KEY, r)
        self.assertIn("key=REDACTED", r)

    def test_redacts_mid_url_without_eating_the_next_parameter(self):
        r = streetview.redact_key("https://x/y?key=SECRET&size=640x640&pitch=0")
        self.assertEqual(r, "https://x/y?key=REDACTED&size=640x640&pitch=0")

    def test_redacts_access_token_and_signature_too(self):
        r = streetview.redact_key("https://x/y?a=1&access_token=T0K3N&signature=SIG")
        self.assertNotIn("T0K3N", r)
        self.assertNotIn("SIG", r)
        self.assertIn("access_token=REDACTED", r)
        self.assertIn("signature=REDACTED", r)

    def test_leaves_a_keyless_url_alone_and_tolerates_none(self):
        self.assertEqual(streetview.redact_key("https://x/y?size=1x1"), "https://x/y?size=1x1")
        self.assertEqual(streetview.redact_key(None), "")


# ----------------------------------------------------------- cost model -----
class TestCostEstimate(unittest.TestCase):
    """Arithmetic against the constants verified on the Google pricing page."""

    def test_the_verified_constants(self):
        self.assertEqual(streetview.FREE_IMAGE_CALLS_PER_MONTH, 10000)
        self.assertEqual(streetview.PRICE_BANDS_USD_PER_1000,
                         [(0, 7.00), (100000, 5.60), (500000, 4.20)])
        self.assertTrue(streetview.METADATA_IS_FREE)

    def test_inside_the_free_allowance_costs_nothing(self):
        self.assertEqual(streetview.estimate_cost_usd(4, 0), 0.0)
        self.assertEqual(streetview.estimate_cost_usd(4, 9996), 0.0)

    def test_first_paid_calls_are_seven_dollars_per_thousand(self):
        # 4 images with the allowance already spent = 4 x $7.00/1000
        self.assertAlmostEqual(streetview.estimate_cost_usd(4, 10000), 0.028, places=6)
        self.assertAlmostEqual(streetview.estimate_cost_usd(1000, 10000), 7.00, places=6)

    def test_the_allowance_boundary_is_split_correctly(self):
        # 10 calls straddling the allowance: 4 free, 6 billed
        self.assertAlmostEqual(streetview.estimate_cost_usd(10, 9996), 6 * 0.007, places=6)

    def test_volume_bands_step_down(self):
        self.assertAlmostEqual(streetview.estimate_cost_usd(1, 100000), 0.0056, places=6)
        self.assertAlmostEqual(streetview.estimate_cost_usd(1, 500000), 0.0042, places=6)
        self.assertAlmostEqual(streetview.estimate_cost_usd(1, 99999), 0.007, places=6)

    def test_zero_and_negative_are_zero(self):
        self.assertEqual(streetview.estimate_cost_usd(0, 0), 0.0)
        self.assertEqual(streetview.estimate_cost_usd(-5, 0), 0.0)

    def test_cost_block_reports_the_billable_split(self):
        b = streetview.cost_block(4, used_this_month=9998)
        self.assertEqual(b["free_image_calls_left_before_this_run"], 2)
        self.assertEqual(b["billable_image_calls"], 2)
        self.assertAlmostEqual(b["estimated_usd"], 0.014, places=6)
        self.assertEqual(b["metadata_usd"], 0.0)
        self.assertEqual(b["pricing_checked"], streetview.PRICING_CHECKED)
        self.assertIn("developers.google.com", b["pricing_source"])


# -------------------------------------------------------- no-key routes -----
class TestNoKey(KeylessMixin):
    def test_check_returns_manual_access_and_instructions(self):
        out = streetview.check(51.5045, -0.0865)
        self.assertEqual(out["access"], "manual")
        self.assertFalse(out["ok"])
        self.assertEqual(out["evidence_class"], "U")
        self.assertIsNone(out["pano_id"])
        self.assertIsNone(out["date"])
        self.assertIn("GOOGLE_MAPS_KEY", out["note"])
        self.assertTrue(any("console.cloud.google.com" in s for s in out["how_to_get_a_key"]))
        self.assertTrue(any("Street View Static API" in s for s in out["how_to_get_a_key"]))
        self.assertTrue(any("Restrict the key" in s for s in out["how_to_get_a_key"]))
        self.assertTrue(any("screenshot" in s.lower() for s in out["or_do_it_by_hand"]))

    def test_check_with_no_key_still_redacts_its_own_source_url(self):
        out = streetview.check(51.5045, -0.0865)
        self.assertIn("key=REDACTED", out["source_url"])

    def test_fetch_refuses_and_writes_nothing(self):
        tmp = tempfile.mkdtemp()
        target = os.path.join(tmp, "sv")
        try:
            man, code = streetview.fetch_images(51.5045, -0.0865, target)
            self.assertEqual(code, 2, "no key must be a usage error, exit 2")
            self.assertEqual(man["access"], "manual")
            self.assertFalse(os.path.exists(target), "must not create the output directory")
            self.assertEqual(man["images"], [])
            self.assertIn("cost_estimate", man)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mapillary_returns_manual_access_and_instructions(self):
        out = streetview.mapillary(51.5045, -0.0865)
        self.assertEqual(out["access"], "manual")
        self.assertFalse(out["ok"])
        self.assertIn("MAPILLARY_TOKEN", out["note"])
        self.assertTrue(any("mapillary.com/dashboard/developers" in s
                            for s in out["how_to_get_a_token"]))
        self.assertEqual(out["licence"], "CC BY-SA 4.0")


# ------------------------------------------------- manifest (stubbed net) ---
META_OK = json.dumps({"status": "OK", "pano_id": "PANO_ABC", "date": "2023-07",
                      "copyright": "© Google",
                      "location": {"lat": 51.50448, "lng": -0.08661}})


def _stub_fetch(body, status=200, ok=True):
    def _f(url, **kw):
        return {"url": url, "final_url": url, "status": status, "content_type": "application/json",
                "body": body, "retrieved_at": "2026-09-05T00:00:00+00:00",
                "from_cache": False, "ok": ok, "note": ""}
    return _f


class _StubBinary(object):
    """Records the URLs it was asked for and writes a tiny placeholder file."""

    def __init__(self):
        self.urls = []

    def __call__(self, url, dest_path, **kw):
        self.urls.append(url)
        with open(dest_path, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0stub")
        return {"url": url, "final_url": url, "status": 200, "content_type": "image/jpeg",
                "path": dest_path, "bytes": os.path.getsize(dest_path),
                "retrieved_at": "2026-09-05T00:00:00+00:00", "from_cache": False,
                "ok": True, "note": ""}


class TestManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "sv")
        self._fetch, self._bin = streetview.fetch, streetview.fetch_binary
        streetview.fetch = _stub_fetch(META_OK)
        self.binary = _StubBinary()
        streetview.fetch_binary = self.binary

    def tearDown(self):
        streetview.fetch, streetview.fetch_binary = self._fetch, self._bin
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_fetch(self, **kw):
        man, code = streetview.fetch_images(51.5045, -0.0865, self.out, key=FAKE_KEY, **kw)
        with open(os.path.join(self.out, "manifest.json"), encoding="utf-8") as fh:
            return man, code, fh.read()

    def test_four_images_and_a_manifest(self):
        man, code, raw = self.run_fetch()
        self.assertEqual(code, 0)
        self.assertEqual(len(man["images"]), 4)
        self.assertEqual(man["images_downloaded"], 4)
        self.assertEqual([i["heading_deg"] for i in man["images"]], [0.0, 90.0, 180.0, 270.0])
        for i in man["images"]:
            self.assertTrue(os.path.exists(os.path.join(self.out, i["file"])))

    def test_the_key_never_reaches_the_manifest(self):
        man, _, raw = self.run_fetch()
        self.assertNotIn(FAKE_KEY, raw, "the API key must never be written to manifest.json")
        self.assertNotIn(FAKE_KEY, json.dumps(man))
        for i in man["images"]:
            self.assertIn("key=REDACTED", i["url"])
        self.assertIn("key=REDACTED", man["metadata_url"])
        # but the real key did go on the wire
        self.assertTrue(all(("key=" + FAKE_KEY) in u for u in self.binary.urls))

    def test_manifest_carries_the_envelope_and_the_capture_date(self):
        man, _, _ = self.run_fetch()
        for field in ("source_url", "retrieved_at", "evidence_class", "attribution",
                      "capture_date_note", "privacy_and_storage", "cost_estimate"):
            self.assertIn(field, man)
        self.assertEqual(man["evidence_class"], "C")
        self.assertEqual(man["capture_date"], "2023-07")
        self.assertEqual(man["pano_id"], "PANO_ABC")
        self.assertIn("© Google", man["attribution"])
        self.assertTrue(all(i["capture_date"] == "2023-07" for i in man["images"]))

    def test_all_four_views_are_pinned_to_one_panorama(self):
        self.run_fetch()
        self.assertTrue(all("pano=PANO_ABC" in u for u in self.binary.urls))
        self.assertTrue(all("location=" not in u for u in self.binary.urls))

    def test_toward_sets_the_first_heading_at_the_target(self):
        # target due east of the camera point
        man, _, _ = self.run_fetch(toward_lat=51.5045, toward_lng=-0.0855)
        self.assertAlmostEqual(man["toward_heading_deg"], 90.0, delta=0.5)
        self.assertAlmostEqual(man["images"][0]["heading_deg"], 90.0, delta=0.5)
        self.assertEqual(man["images"][0]["shows"],
                         "the target (the building), from the camera point")
        self.assertEqual(len(man["images"]), 4)

    def test_explicit_headings_are_honoured_and_capped(self):
        man, _, _ = self.run_fetch(headings="0,45,90,135,180")
        self.assertEqual([i["heading_deg"] for i in man["images"]], [0.0, 45.0, 90.0, 135.0])

    def test_cost_estimate_matches_the_image_count(self):
        man, _, _ = self.run_fetch(used_this_month=10000)
        self.assertEqual(man["cost_estimate"]["image_calls"], 4)
        self.assertEqual(man["cost_estimate"]["billable_image_calls"], 4)
        self.assertAlmostEqual(man["cost_estimate"]["estimated_usd"], 0.028, places=6)

    def test_zero_results_downloads_nothing_and_bills_nothing(self):
        streetview.fetch = _stub_fetch(json.dumps({"status": "ZERO_RESULTS"}))
        man, code = streetview.fetch_images(51.5045, -0.0865, self.out, key=FAKE_KEY)
        self.assertEqual(code, 0)
        self.assertFalse(man["ok"])
        self.assertEqual(man["images"], [])
        self.assertEqual(self.binary.urls, [])
        self.assertEqual(man["cost_estimate"]["image_calls"], 0)
        self.assertIn("ZERO_RESULTS", man["note"])


# -------------------------------------------------------- mapillary bbox ----
class TestMapillaryGeometry(unittest.TestCase):
    def test_bbox_stays_under_the_documented_hundredth_of_a_degree(self):
        for r in (10, 60, 300, 5000):
            (w, s, e, n), used = streetview._bbox(51.5045, -0.0865, r)
            self.assertLess(n - s, 0.01, "lat span must stay under 0.01 degrees at r=%s" % r)
            self.assertLess(e - w, 0.01, "lng span must stay under 0.01 degrees at r=%s" % r)
            self.assertLessEqual(used, streetview.MAPILLARY_MAX_RADIUS_M)

    def test_bbox_is_centred_on_the_point(self):
        (w, s, e, n), _ = streetview._bbox(51.5045, -0.0865, 60)
        self.assertAlmostEqual((s + n) / 2, 51.5045, places=5)
        self.assertAlmostEqual((w + e) / 2, -0.0865, places=5)

    def test_epoch_ms_to_iso(self):
        self.assertEqual(streetview._epoch_ms_to_iso(1700000000000),
                         "2023-11-14T22:13:20+00:00")
        self.assertIsNone(streetview._epoch_ms_to_iso(None))
        self.assertIsNone(streetview._epoch_ms_to_iso("not a number"))


# ------------------------------------------------------------- the brief ----
class TestBrief(unittest.TestCase):
    def test_text_is_present_and_lists_every_checklist_heading(self):
        b = streetview.brief()
        self.assertTrue(b["ok"])
        text = b["text"]
        self.assertTrue(len(text) > 500)
        for block in streetview.CHECKLIST:
            self.assertIn(block["heading"], text)
            for item in block["items"]:
                self.assertIn(item, text)

    def test_the_eight_headings_cover_the_axis(self):
        heads = " ".join(b["heading"].lower() for b in streetview.CHECKLIST)
        for word in ("facade", "ground", "construction", "vacant", "sky", "managed",
                     "capture date", "not to infer"):
            self.assertIn(word, heads, word)

    def test_the_forbidden_inferences_are_spelled_out(self):
        text = " ".join(i.lower() for b in streetview.CHECKLIST for i in b["items"])
        for phrase in ("ethnicity", "nationality", "crime", "people in the frame"):
            self.assertIn(phrase, text, phrase)

    def test_all_three_routes_are_described(self):
        names = [r["name"] for r in streetview.brief()["routes"]]
        self.assertEqual(len(names), 3)
        self.assertIn("Google Street View Static API", names)
        self.assertIn("Mapillary", names)
        self.assertIn("the user's own screenshots", names)

    def test_brief_asks_for_the_capture_date(self):
        b = streetview.brief()
        self.assertTrue(any("capture date" in s for s in b["screenshots_to_ask_for"]))
        self.assertIn("years", b["capture_date_note"])


# ---------------------------------------------------------- the contract ----
class TestConventions(unittest.TestCase):
    def test_every_public_output_carries_the_envelope(self):
        for out in (streetview.brief(),):
            for field in ("source_url", "retrieved_at", "evidence_class", "ok", "note"):
                self.assertIn(field, out)

    def test_street_imagery_is_always_evidence_class_c(self):
        self.assertEqual(streetview.brief()["evidence_class"], "C")

    def test_storage_note_states_the_caching_rule(self):
        self.assertIn("panorama ID", streetview.STORAGE_NOTE)
        self.assertIn("Delete the image files", streetview.STORAGE_NOTE)

    def test_docstring_records_the_verified_price_and_terms(self):
        doc = streetview.__doc__
        for token in ("9BD0-A2EE-44C3", "3168-48A9-5C8C", "10,000 free", "$7.00",
                      "No Scraping", "No Caching", "2026-09-05"):
            self.assertIn(token, doc, token)


if __name__ == "__main__":
    unittest.main()
