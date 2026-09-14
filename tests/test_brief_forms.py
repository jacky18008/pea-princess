# -*- coding: utf-8 -*-
"""The --brief forms of epc search, roads near and landregistry price-paid: the same facts, a tenth of the
characters, so a later tool call re-sends less. Offline: built from constructed outputs.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import epc as EPC  # noqa: E402
import roads as ROADS  # noqa: E402
import landregistry as LR  # noqa: E402


def epc_search_out(n=62):
    rows = [{"certificate_id": "%04d-0000-0000-0000-0000" % i, "address": "%d Buckstone Apartments, 140, Blackfriars Road, LONDON, SE1 8BW" % i,
             "rating": "B", "valid_until": "6 June 2027", "certificate_url": "https://find-energy-certificate.service.gov.uk/energy-certificate/%04d" % i}
            for i in range(1, n + 1)]
    return {"query": {"postcode": "SE1 8BW"}, "source_url": "https://x", "http_status": 200, "ok": True, "note": "", "retrieved_at": "t",
            "evidence_class": "G", "count": n, "results": rows, "too_many_results": False, "no_results": False, "caveat": "..."}


class TestEpcSearchBrief(unittest.TestCase):
    def test_match_keeps_the_flat_and_says_what_it_dropped(self):
        out = EPC.search_match(epc_search_out(), "8 Buckstone")
        self.assertEqual(1, out["match"]["kept"], "a word-boundary match: not 18, 28 or 58 Buckstone"); self.assertEqual(62, out["match"]["of"])
        self.assertEqual("8 Buckstone Apartments, 140, Blackfriars Road, LONDON, SE1 8BW", out["results"][0]["address"])
        none = EPC.search_match(epc_search_out(), "Flat 99 Nowhere")
        self.assertEqual(0, none["match"]["kept"]); self.assertIn("no certificate address", none["match"]["note"])

    def test_brief_is_a_tenth_of_the_size_and_keeps_the_ids(self):
        full = epc_search_out(); brief = EPC.search_brief(full)
        self.assertLess(len(json.dumps(brief)), len(json.dumps(full)) / 1.5)   # measured live: 19.4k → 11.4k, and 1.5k with --match
        self.assertEqual(62, len(brief["results"])); self.assertEqual("0008-0000-0000-0000-0000", brief["results"][7]["id"])
        self.assertNotIn("certificate_url", brief["results"][0]); self.assertIn("epc.py cert <id>", brief["next"])


class TestRoadsBrief(unittest.TestCase):
    def test_categories_keep_count_nearest_and_three_names(self):
        full = {"ok": True, "source_url": "u", "attempts": [{"x": 1}] * 3, "query_used": "[out:json]" * 50, "element_count": 400, "radius_m": 300,
                "trunk_or_primary_road": {"count": 55, "names": ["Blackfriars Road", "St George's Circus", "Borough Road", "Lambeth Road"],
                                          "nearest": {"name": "Blackfriars Road", "distance_m": 23, "osm_url": "https://osm/way/1", "geometry": [[1, 2]] * 200},
                                          "elements": [{"id": i} for i in range(55)]},
                "night_economy": {"count": 0, "names": [], "nearest": None, "elements": []},
                "facade_note": "one facade faces the main road", "not_found": ["helipad: none within 2000 m"]}
        b = ROADS.brief(full)
        self.assertNotIn("attempts", b); self.assertNotIn("query_used", b)
        self.assertEqual(55, b["trunk_or_primary_road"]["count"]); self.assertEqual(23, b["trunk_or_primary_road"]["nearest"]["distance_m"])
        self.assertNotIn("geometry", b["trunk_or_primary_road"]["nearest"]); self.assertEqual(3, len(b["trunk_or_primary_road"]["names"]))
        self.assertIsNone(b["night_economy"]["nearest"]); self.assertTrue(b["brief"])
        self.assertLess(len(json.dumps(b)), len(json.dumps(full)) / 5)


class TestLandRegistryBrief(unittest.TestCase):
    def test_summary_recent_and_no_transaction_list(self):
        rows = [{"date": "2019-0%d-01" % (i % 9 + 1), "price": str(300000 + i * 10000), "saon": "FLAT %d" % i, "paon": "BUCKSTONE APARTMENTS",
                 "street": "BLACKFRIARS ROAD", "property_type": "flat-maisonette", "new_build": i < 28} for i in range(49)]
        full = {"query": {"postcode": "SE1 8BW"}, "ok": True, "note": "", "count": 49, "transactions": rows, "new_build_count": 28,
                "earliest_transaction": rows[0], "latest_transaction": rows[-1], "sparql": "SELECT" * 100}
        b = LR.brief(full)
        self.assertNotIn("transactions", b); self.assertNotIn("sparql", b)
        self.assertEqual(49, b["price_summary"]["n"]); self.assertEqual(300000, b["price_summary"]["min"]); self.assertEqual(780000, b["price_summary"]["max"])
        self.assertEqual(540000, b["price_summary"]["median"]); self.assertEqual({"flat-maisonette": 49}, b["price_summary"]["by_property_type"])
        self.assertEqual(5, len(b["recent"])); self.assertTrue(b["recent"][0]["date"] >= b["recent"][-1]["date"])
        self.assertLess(len(json.dumps(b)), len(json.dumps(full)) / 4)


if __name__ == "__main__":
    unittest.main()
