# -*- coding: utf-8 -*-
"""scripts/noise.py: Defra strategic noise maps at a point, parsed from canned responses; no network.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

The fixtures are real responses captured on 2026-09-11: King Street, Hammersmith (road Lden 75.29 dB,
2017 band 70.0-74.9), a point on Hampstead Heath (40.59, the raster floor), and the raster's 0 where
nothing is drawn (rail away from any line).
"""
from __future__ import unicode_literals

import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import noise as N  # noqa: E402

KING_ST = '{"type":"FeatureCollection","features":[{"type":"Feature","id":"","geometry":null,"properties":{"GRAY_INDEX":75.29000091552734}}],"totalFeatures":"unknown","numberReturned":1}'
HEATH = '{"type":"FeatureCollection","features":[{"type":"Feature","id":"","geometry":null,"properties":{"GRAY_INDEX":40.59000015258789}}]}'
NOTHING = '{"type":"FeatureCollection","features":[{"type":"Feature","id":"","geometry":null,"properties":{"GRAY_INDEX":0.0}}]}'
OUTSIDE = '{"type":"FeatureCollection","features":[],"totalFeatures":"unknown","numberReturned":0}'
BAND = '{"type":"FeatureCollection","features":[{"type":"Feature","id":"Road_Noise_Lden_England_Round_3.1538039","geometry":null,"properties":{"noiseclass":"70.0-74.9"}}],"totalFeatures":1}'
NO_BAND = '{"type":"FeatureCollection","features":[],"totalFeatures":0,"numberMatched":0,"numberReturned":0}'


def fake(bodies):
    """A fetcher that answers each URL from a table keyed by a substring of the URL."""
    def fetcher(url, **kw):
        for key, body in bodies:
            if key in url:
                return {"ok": True, "status": 200, "body": body, "retrieved_at": "2026-09-11T21:49:00Z", "from_cache": False, "note": ""}
        return {"ok": False, "status": 0, "body": "", "retrieved_at": "2026-09-11T21:49:00Z", "from_cache": False, "note": "curl error 6"}
    return fetcher


class TestParsing(unittest.TestCase):
    def test_a_value_is_read_and_rounded(self):
        self.assertEqual((75.3, ""), N.parse_feature_info(KING_ST))
        self.assertEqual((40.6, ""), N.parse_feature_info(HEATH))

    def test_outside_the_map_and_bad_bodies_are_reported(self):
        v, note = N.parse_feature_info(OUTSIDE)
        self.assertIsNone(v); self.assertIn("outside", note)
        self.assertEqual("response was not JSON", N.parse_feature_info("<html>")[1])

    def test_the_band_and_its_absence(self):
        self.assertEqual(("70.0-74.9", ""), N.parse_band(BAND))
        self.assertEqual((None, ""), N.parse_band(NO_BAND), "no polygon = below the drawn floor, not an error")
        two = '{"features":[{"properties":{"noiseclass":"60.0-64.9"}},{"properties":{"noiseclass":">=75.0"}}]}'
        self.assertEqual(">=75.0", N.parse_band(two)[0], "two polygons on a shared edge: keep the louder")

    def test_the_urls_query_the_right_layer_and_order(self):
        u = N.feature_info_url("rail", "lnight", 51.4646, -0.1706)
        self.assertIn("/noise-data/wms", u); self.assertIn("Rail_Noise_Lnight_England_Round_4_All", u); self.assertIn("CRS=EPSG%3A4326", u)
        b = N.band_url("road", "lden", 51.4926, -0.2284)
        self.assertIn("road-noise-lden-england-round-3/wfs", b)
        self.assertIn("POINT%28-0.228400+51.492600%29", b, "lon then lat inside the point")


class TestLevels(unittest.TestCase):
    def test_a_zero_pixel_is_nothing_drawn_never_zero_decibels(self):
        r = N.level(51.5, -0.1, "rail", "lden", fetcher=fake([("Rail_Noise_Lden", NOTHING)]))
        self.assertTrue(r["ok"]); self.assertIsNone(r["db"]); self.assertFalse(r["drawn"]); self.assertIn("nothing drawn", r["note"])

    def test_the_floor_is_flagged(self):
        r = N.level(51.5606, -0.1637, fetcher=fake([("Road_Noise_Lden", HEATH)]))
        self.assertEqual(40.6, r["db"]); self.assertIn("floor", r["note"])

    def test_a_failed_fetch_is_reported(self):
        r = N.level(51.5, -0.1, fetcher=fake([]))
        self.assertFalse(r["ok"]); self.assertEqual("curl error 6", r["note"])

    def test_describe_is_anchored_to_the_who_guideline(self):
        self.assertIn("12 dB below the WHO guideline of 53", N.describe(41.0, "lden"))
        self.assertIn("3 dB above the WHO guideline of 53", N.describe(56.0, "lden"))
        self.assertIn("22.3 dB above the WHO guideline of 53", N.describe(75.3, "lden"))
        self.assertIn("45 dB", N.describe(43.0, "lnight"))
        self.assertIn("54", N.describe(50.0, "lden", "rail"))
        self.assertIn("nothing drawn", N.describe(None, "lden"))

    def test_every_threshold_describes_modelled_exposure_not_audibility_or_location(self):
        for source in ("road", "rail"):
            for metric in ("lden", "lnight"):
                who = N.WHO[(source, metric)]
                for offset in (-12, -8, -5, -1, 0, 4, 5, 6, 7, 9, 10, 11, 12, 16, 17, 25):
                    with self.subTest(source=source, metric=metric, offset=offset):
                        text = N.describe(who + offset, metric, source)
                        self.assertIn("modelled outdoor exposure", text)
                        self.assertIn("%d dB" % who, text)
                        self.assertIn("below" if offset < 0 else "at" if offset == 0 else "above", text)
                        for unsupported in ("audible", "window open", "constant presence", "quiet",
                                            "loud", "frontage", "trackside", "right by", "busy-road", "A-road"):
                            self.assertNotIn(unsupported, text)

    def test_threshold_boundaries_report_exact_gaps(self):
        self.assertIn("at the WHO guideline of 53", N.describe(53, "lden"))
        self.assertIn("7 dB above", N.describe(60, "lden"))
        self.assertIn("12 dB above", N.describe(65, "lden"))
        self.assertIn("17 dB above", N.describe(70, "lden"))
        self.assertIn("at the WHO night guideline of 45", N.describe(45, "lnight"))
        self.assertIn("5 dB above", N.describe(50, "lnight"))
        self.assertIn("10 dB above", N.describe(55, "lnight"))


class TestLookup(unittest.TestCase):
    def test_three_points_one_summary_and_a_reading(self):
        f = fake([("Round_3", BAND), ("BBOX=51.49252", KING_ST), ("Road_Noise_Lden", HEATH)])
        out = N.lookup([(51.4926, -0.2284), (51.4930, -0.2300), (51.4922, -0.2270)], fetcher=f)
        self.assertTrue(out["ok"]); self.assertEqual("vet-flat/noise/1", out["schema"])
        self.assertEqual(3, len(out["points"])); self.assertEqual(75.3, out["points"][0]["road_lden_db"])
        sm = out["summary"]["road_lden_db"]
        self.assertEqual((75.3, 40.6, 75.3, 3), (sm["at_point"], sm["min"], sm["max"], sm["n"]))
        self.assertIn("75.3 dB at the point (40.6-75.3 dB across 3 points", out["reading"][0])
        self.assertEqual("70.0-74.9", out["band_2017"]["road_lden"]); self.assertIn("70.0-74.9 dB band", out["reading"][1])
        self.assertIn("not a measurement at any window", out["reading"][-1])
        self.assertIn("modelled outdoor exposure", out["reading"][0])
        self.assertIn("not indoor levels, window direction or how often noise will be heard", out["scale"])
        self.assertIn("road 53 dB, rail 54 dB", out["scale"])
        self.assertIn("road 45 dB, rail 44 dB", out["scale"])
        self.assertEqual(N.WHO_GUIDELINE_SOURCE, out["guideline_source_url"])
        self.assertIn(N.WHO_GUIDELINE_SOURCE, out["sources"], "the area scan forwards these source URLs")
        for unsupported in ("quiet back streets", "main-road frontages", "just noticeable", "twice as loud"):
            self.assertNotIn(unsupported, out["scale"])
        self.assertIn("Crown Copyright", out["licence"])
        self.assertLess(len(json.dumps(out, ensure_ascii=False)), 3500)

    def test_street_span_and_point_use_their_own_exact_who_gaps(self):
        sample = lambda db: {"db": db, "ok": True, "note": ""}
        with mock.patch.object(N, "level", side_effect=[sample(63.4), sample(56.7)]):
            out = N.lookup([(51.5179, -0.0560), (51.5180, -0.0561)], with_band=False)
        reading = out["reading"][0]
        self.assertIn("63.4 dB at the point", reading)
        self.assertIn("56.7-63.4 dB across 2 points", reading)
        self.assertIn("WHO guideline of 53 dB, from 3.7 dB above to 10.4 dB above", reading)
        self.assertIn("modelled outdoor exposure 10.4 dB above the WHO guideline of 53 dB", reading)
        self.assertNotIn("7–12 dB", reading)

    def test_rail_nothing_drawn_reads_as_no_mapped_noise(self):
        f = fake([("Round_3", NO_BAND), ("Road_Noise_Lden", KING_ST), ("Rail_Noise_Lden", NOTHING)])
        out = N.lookup([(51.4926, -0.2284)], rail=True, fetcher=f)
        self.assertEqual("not drawn", out["points"][0]["rail_lden_db"])
        self.assertEqual(1, out["summary"]["rail_lden_db"]["not_drawn"])
        self.assertTrue(any(r.startswith("Rail noise") and "nothing drawn" in r for r in out["reading"]), out["reading"])
        self.assertIn("drew no road-noise band here", " ".join(out["reading"]))
        self.assertEqual([], out["not_found"])

    def test_a_dead_map_is_in_not_found(self):
        out = N.lookup([(51.4926, -0.2284)], fetcher=fake([]))
        self.assertFalse(out["ok"]); self.assertTrue(out["not_found"]); self.assertIn("no value could be read", out["reading"][0])


class TestCli(unittest.TestCase):
    def test_no_point_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "noise.py")], capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)

    def test_points_are_parsed(self):
        self.assertEqual([(51.4926, -0.2284), (51.493, -0.23)], N.parse_points("51.4926,-0.2284; 51.4930,-0.2300"))


if __name__ == "__main__":
    unittest.main()
