# -*- coding: utf-8 -*-
"""scripts/vet_case.py: the fixed vetting chain with explicit data states (offline; canned register outputs).

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0
"""
from __future__ import unicode_literals

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
sys.path.insert(0, SCRIPTS)
import vet_case as V  # noqa: E402

CERTS = [{"certificate_id": "1111-aaaa", "address": "Flat 1, Corbel House, London XE4 2QP", "rating": "C"},
         {"certificate_id": "4444-dddd", "address": "Flat 4, Corbel House, London XE4 2QP", "rating": "C"},
         {"certificate_id": "1414-nnnn", "address": "Flat 14, Corbel House, London XE4 2QP", "rating": "B"},
         {"certificate_id": "5555-eeee", "address": "Flat 5, Corbel House, London XE4 2QP", "rating": "D"}]


def fixture(**over):
    base = {
        "geo": {"ok": True, "lat": 51.5, "lng": -0.1, "admin_district": "Southwark", "source_url": "https://api.postcodes.io/postcodes/XE42QP", "retrieved_at": "t"},
        "epc_search": {"ok": True, "results": list(CERTS), "source_url": "https://find-energy-certificate.service.gov.uk/x"},
        "epc_cert": {"ok": True, "certificate_id": "4444-dddd", "total_floor_area_m2": 48, "energy_rating": "C", "heating_class": "gas_boiler", "floor_position": "mid", "source_url": "https://find-energy-certificate.service.gov.uk/c"},
        "epc_building": {"ok": True, "summary": {"certificates_found": 4, "floor_area_m2": {"min": 41, "median": 47, "max": 55}}},
        "sales": {"ok": True, "count": 2, "latest_transaction": {"date": "2021-03-01", "price": 450000}, "earliest_new_build_year": 2016, "source_url": "https://landregistry.data.gov.uk/q"},
        "area": {"scan_status": "complete", "ok": True,
                 "works": {"count": 12, "applications_within_m": 250, "notable_recent": []},
                 "noise": {"road_lden_db": 68.0, "rail_lden_db": None},
                 "quiet": {"main_road_nearest_m": 35, "main_road_names": ["A200"], "railway_surface_nearest_m": None, "tube_surface_nearest_m": None, "night_economy_count": 2},
                 "crime": {"total": 40, "months": 6, "top_categories": [{"category": "anti-social behaviour", "count": 12}]}},
        "redress_cmp": {"ok": True, "count": 1, "matches": [{"name": "Orrin & Vale"}], "source_url": "https://cmp/x"},
        "company_agent": {"ok": True, "count": 2, "results": [{"status": "Active"}, {"status": "Dissolved"}], "dissolved_count": 1, "source_url": "https://ch/x"},
        "rogue": {"ok": True, "count": 0, "results": [], "not_found": {"query": "Orrin & Vale", "endpoint": "rogue"}, "evidence_class": "U", "source_url": "https://gla/x"},
        "commute": {"ok": True, "fastest_min": 52, "rail_only_min": 55, "bus_only_min": 70, "source_url": "https://api.tfl.gov.uk/j"},
    }
    base.update(over)
    return base


def by_id(out):
    return {c["id"]: c for c in out["checks"]}


class NoNetwork(unittest.TestCase):
    """Every register function is replaced by one that fails the test if it is ever called."""

    def setUp(self):
        self.patches = []
        for mod, names in ((V.geo, ["lookup"]), (V.epc, ["search", "cert", "building"]), (V.landregistry, ["price_paid"]),
                           (V.area_scan, ["scan"]), (V.company, ["search"]), (V.redress, ["cmp_search", "rogue", "heat_trust"]),
                           (V.commute, ["journey"])):
            for n in names:
                p = mock.patch.object(mod, n, side_effect=AssertionError("network call %s.%s in a test" % (mod.__name__, n)))
                p.start(); self.patches.append(p)

    def tearDown(self):
        for p in self.patches:
            p.stop()


class TestExactIdentity(NoNetwork):
    def test_the_full_chain_with_an_exact_flat(self):
        out = V.vet("XE4 2QP", flat="4", building="Corbel House", rent_pcm=1950, area_m2=48, deposit_gbp=2500,
                    agent="Orrin & Vale", destination="XC1 2AB", commute_max=45, fixture=fixture())
        self.assertEqual("how_to_use", list(out.keys())[0])
        self.assertEqual("exact", out["identity"]["state"])
        self.assertEqual("4444-dddd", out["identity"]["certificate"]["certificate_id"])  # not Flat 14
        c = by_id(out)
        self.assertEqual(("pass", "unit"), (c["C1"]["state"], c["C1"]["scope"]))
        self.assertEqual("pass", c["C2"]["state"]); self.assertEqual(48.0, c["C2"]["value"]["certificate_m2"])
        self.assertEqual(("pass", "C"), (c["C3"]["state"], c["C3"]["value"]))
        self.assertEqual("pass", c["C4"]["state"]); self.assertEqual("pass", c["C5"]["state"]); self.assertEqual("pass", c["C6"]["state"])
        self.assertEqual("flag", c["C7"]["state"]); self.assertEqual(2250.0, c["C7"]["value"]["cap_gbp"])  # 5 weeks of £1,950 pcm
        self.assertEqual("pass", c["C8"]["state"]); self.assertAlmostEqual(1950 / 48.0, c["C8"]["value"]["gbp_per_m2_pcm"], delta=0.01)
        self.assertEqual("pass", c["C9"]["state"])
        self.assertEqual(("flag", "area"), (c["C10"]["state"], c["C10"]["scope"]))   # 68 dB
        self.assertEqual(("flag", "street"), (c["C11"]["state"], c["C11"]["scope"]))  # main road at 35 m
        self.assertEqual("pass", c["C12"]["state"])
        self.assertEqual("pass", c["C13"]["state"])
        self.assertEqual("pass", c["C14"]["state"]); self.assertEqual(1, c["C14"]["value"]["active"])
        self.assertEqual(("unknown", "U"), (c["C15"]["state"], c["C15"]["evidence_class"]))  # absence is not a clean record
        self.assertEqual("flag", c["C16"]["state"]); self.assertEqual(52.0, c["C16"]["value"]["fastest_min"])
        self.assertEqual("not_applicable", c["C17"]["state"])
        self.assertIsNone(out["verdict"])
        self.assertTrue(all(r["state"] == "ok" or (n == "rogue" and r["state"] == "not_found") for n, r in out["registers"].items()), out["registers"])
        self.assertTrue(any("deposit" in s.lower() for s in out["next_steps"]))
        self.assertEqual(out["summary"], {"pass": 11, "flag": 4, "unknown": 1, "not_applicable": 1})
        codes = [e["code"] for e in out["landmines"]]
        self.assertEqual(["L12", "L4"], sorted(codes))          # deposit over the cap; noise and the main road share one L4 entry
        l4 = [e for e in out["landmines"] if e["code"] == "L4"][0]
        self.assertEqual(["C10", "C11"], l4["checks"]); self.assertFalse(l4["reversible"])
        self.assertTrue(all(k in e for e in out["landmines"] for k in ("code", "label", "detail", "reversible", "evidence_class")))


class TestAmbiguousAndUnresolved(NoNetwork):
    def test_no_flat_number_keeps_unit_facts_unknown_and_gives_the_building_range(self):
        fx = fixture(); fx.pop("epc_cert")
        out = V.vet("XE4 2QP", rent_pcm=1950, area_m2=48, fixture=fx)
        self.assertEqual("ambiguous", out["identity"]["state"]); self.assertEqual(4, out["identity"]["candidates"])
        c = by_id(out)
        self.assertEqual(("flag", "building"), (c["C1"]["state"], c["C1"]["scope"]))
        self.assertEqual(("unknown", "building"), (c["C2"]["state"], c["C2"]["scope"]))
        self.assertEqual([41, 55], c["C2"]["value"]["building_range_m2"])
        self.assertEqual("unknown", c["C3"]["state"]); self.assertEqual("unknown", c["C4"]["state"])
        self.assertIn("which flat", out["next_steps"][0].lower())
        self.assertNotIn("epc_cert", out["registers"])

    def test_a_flat_the_register_does_not_carry_is_unresolved(self):
        fx = fixture(); fx.pop("epc_cert")
        out = V.vet("XE4 2QP", flat="9", fixture=fx)
        self.assertEqual("unresolved", out["identity"]["state"])
        self.assertIn("none of the 4 certificates", out["identity"]["reason"])
        self.assertEqual("unknown", by_id(out)["C1"]["state"])

    def test_an_unreachable_register_is_unknown_never_pass(self):
        fx = fixture(epc_search=RuntimeError("curl timeout"), sales=RuntimeError("504"))
        fx.pop("epc_cert"); fx.pop("epc_building")
        out = V.vet("XE4 2QP", flat="4", rent_pcm=1950, fixture=fx)
        self.assertEqual("unresolved", out["identity"]["state"])
        self.assertEqual("unreachable", out["registers"]["epc_search"]["state"])
        self.assertEqual("unreachable", out["registers"]["sales"]["state"])
        c = by_id(out)
        for cid in ("C1", "C2", "C3", "C4", "C5", "C6"):
            self.assertEqual("unknown", c[cid]["state"], cid)
        self.assertEqual("pass", c["C7"]["state"])  # arithmetic needs no register
        self.assertTrue(any("unreachable" in n["what"] for n in out["not_found"]))

    def test_no_match_in_an_absence_only_register_is_unknown(self):
        fx = fixture(redress_cmp={"ok": True, "count": 0, "matches": [], "not_found": {"query": "x", "endpoint": "cmp"}, "evidence_class": "U"},
                     sales={"ok": True, "count": 0, "transactions": [], "not_found": {"query": "x", "endpoint": "lr", "meaning": "build to rent"}},
                     epc_search={"ok": True, "results": [], "no_results": True, "not_found": {"query": "x", "meaning": "none"}})
        fx.pop("epc_cert"); fx.pop("epc_building")
        out = V.vet("XE4 2QP", flat="4", agent="Orrin & Vale", fixture=fx)
        c = by_id(out)
        self.assertEqual("unresolved", out["identity"]["state"])
        self.assertEqual(("unknown", "U"), (c["C13"]["state"], c["C13"]["evidence_class"]))
        self.assertEqual("unknown", c["C6"]["state"])
        for cid in ("C1", "C2", "C3", "C4", "C5", "C6", "C13", "C15"):   # every absence or unreachable case stays unknown
            self.assertEqual("unknown", c[cid]["state"], cid)
        self.assertEqual("pass", c["C14"]["state"])   # a positive Companies House match is a real pass


class TestFloorsAndLandmines(NoNetwork):
    def test_a_lower_ground_flat_is_a_caution_L10_and_a_top_floor_L11(self):
        fx = fixture(); fx["epc_cert"]["floor_position"] = "basement"
        out = V.vet("XE4 2QP", flat="4", building="Corbel House", rent_pcm=1950, fixture=fx)
        self.assertEqual("flag", by_id(out)["C5"]["state"])
        self.assertIn("L10", [e["code"] for e in out["landmines"]])
        fx = fixture(); fx["epc_cert"]["floor_position"] = "top"
        out = V.vet("XE4 2QP", flat="4", building="Corbel House", rent_pcm=1950, fixture=fx)
        self.assertIn("L11", [e["code"] for e in out["landmines"]])

    def test_a_heat_network_is_L6_but_electric_heating_is_not_a_landmine(self):
        fx = fixture(); fx["epc_cert"]["heating_class"] = "electric"
        out = V.vet("XE4 2QP", flat="4", building="Corbel House", rent_pcm=1950, fixture=fx)
        self.assertEqual("flag", by_id(out)["C4"]["state"]); self.assertNotIn("L6", [e["code"] for e in out["landmines"]])
        fx = fixture(); fx["epc_cert"]["heating_class"] = "community_heat_network"; fx["heat_trust"] = {"ok": True, "match_count": 0, "not_found": {"query": "x"}}
        out = V.vet("XE4 2QP", flat="4", building="Corbel House", rent_pcm=1950, fixture=fx)
        self.assertIn("L6", [e["code"] for e in out["landmines"]]); self.assertEqual("unknown", by_id(out)["C17"]["state"])


class TestPieces(unittest.TestCase):
    def test_deposit_cap_branches_on_the_annual_rent(self):
        self.assertEqual((2250.0, 5), (V.deposit_cap(1950)["cap_gbp"], V.deposit_cap(1950)["weeks"]))
        self.assertEqual((6230.77, 6), (V.deposit_cap(4500)["cap_gbp"], V.deposit_cap(4500)["weeks"]))  # £54,000 a year

    def test_flat_matching_is_word_bounded(self):
        kept = V.match_certificates(CERTS, flat="4")
        self.assertEqual(["4444-dddd"], [k["certificate_id"] for k in kept])
        self.assertEqual(["4444-dddd"], [k["certificate_id"] for k in V.match_certificates(CERTS, flat="Flat 4", building="Corbel House")])
        self.assertEqual([], V.match_certificates(CERTS, flat="4", building="Other House"))
        self.assertEqual(4, len(V.match_certificates(CERTS, building="corbel house")))

    def test_a_job_still_running_at_the_deadline_is_unreachable(self):
        res = V.run_all({"slow": lambda: time.sleep(3) or {"ok": True}}, 0.3)
        self.assertEqual("unreachable", V.register_state(res["slow"])[0])
        self.assertIn("timed out", V.register_state(res["slow"])[1])

    def test_register_state_vocabulary(self):
        self.assertEqual("ok", V.register_state({"ok": True, "count": 3})[0])
        self.assertEqual("not_found", V.register_state({"ok": True, "not_found": {"query": "q", "meaning": "m"}})[0])
        self.assertEqual("unreachable", V.register_state({"ok": False, "note": "curl timeout"})[0])
        self.assertEqual("unreachable", V.register_state(None)[0])


class TestCli(unittest.TestCase):
    def test_fixture_run_prints_the_document_and_saves_nothing(self):
        fx = fixture(); fx.pop("epc_cert"); fx.pop("epc_building")
        d = tempfile.mkdtemp()
        path = os.path.join(d, "fx.json")
        io.open(path, "w", encoding="utf-8").write(json.dumps(fx))
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "vet_case.py"), "--postcode", "XE4 2QP", "--rent-pcm", "1950",
                               "--fixture", path, "--no-save", "--deadline-seconds", "5"], capture_output=True, text=True, timeout=60, cwd=d)
        self.assertEqual(0, proc.returncode, proc.stderr[-400:])
        out = json.loads(proc.stdout)
        self.assertEqual(V.SCHEMA, out["schema"]); self.assertEqual("ambiguous", out["identity"]["state"])
        self.assertFalse(os.path.exists(os.path.join(d, ".pea-state")))

    def test_no_postcode_is_a_clean_error(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "vet_case.py"), "--rent-pcm", "1950", "--no-save"], capture_output=True, text=True, timeout=60)
        self.assertEqual(2, proc.returncode); self.assertIn("no postcode", json.loads(proc.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
