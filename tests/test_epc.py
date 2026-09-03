"""Offline parser tests for scripts/epc.py (run: python3 -m unittest tests/test_epc.py)."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import epc  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    return open(os.path.join(FIX, name), encoding="utf-8").read()


class TestCertificateParsing(unittest.TestCase):
    def test_rdsap_certificate(self):
        d = epc.parse_certificate(read("epc-cert-rdsap-1090-0965-0722-3091-3203.html"))
        self.assertEqual(d["total_floor_area_m2"], 93.0)
        self.assertEqual(d["property_type"], "Mid-floor flat")
        self.assertEqual(d["floor_position"], "mid")
        self.assertEqual(d["energy_rating"], "C")
        self.assertEqual(d["energy_score"], 80)
        self.assertEqual(d["valid_until"], "15 December 2030")
        self.assertEqual(d["certificate_number"], "1090-0965-0722-3091-3203")
        self.assertEqual(d["assessment_type"], "RdSAP")
        self.assertEqual(d["heating_class"], "gas_boiler")
        self.assertIsNone(d["air_permeability"])
        self.assertEqual(d["first_assessment_year"], 2020)

    def test_sap_new_build_certificate(self):
        d = epc.parse_certificate(read("epc-cert-sap-8205-6646-6439-6827-6513.html"))
        self.assertEqual(d["total_floor_area_m2"], 51.0)
        self.assertEqual(d["assessment_type"], "SAP")
        self.assertEqual(d["heating_class"], "community_heat_network")
        self.assertEqual(d["air_permeability"], 3.2)
        self.assertTrue(d["mechanical_ventilation_inferred"])
        self.assertEqual(d["kwh_per_year_heating"], 1179)
        self.assertEqual(d["first_assessment_year"], 2019)


class TestSearchParsing(unittest.TestCase):
    def test_search_rows(self):
        body = read("epc-search-SE1-9SG.html")
        ids = epc.CERT_RE.findall(body)
        self.assertGreaterEqual(len(ids), 10)
        self.assertIn("1090-0965-0722-3091-3203", ids)
        self.assertTrue(re.search(r"Flat 200, London Bridge Hotel", body))


if __name__ == "__main__":
    unittest.main()
