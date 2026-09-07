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


class TestNilResultPages(unittest.TestCase):
    """Two pages that mean "nothing here", captured live on 2026-09-03.

    A search that comes back on one of these has been answered. Reading it as a
    fetch failure hides a fact behind an error and makes a nil result and a broken
    request look the same, which is the one thing the not_found table exists to
    prevent.
    """
    EXPECT = staticmethod(
        lambda b: ("epb-search-results" in b or "no certificates" in b.lower()
                   or "could not find" in b.lower() or epc.TOO_MANY_MARKER in b
                   or epc.NIL_STREET_MARKER in b or epc.NIL_POSTCODE_MARKER in b))

    def test_a_postcode_with_no_certificates(self):
        body = read("epc-search-postcode-no-results-se19bs.html")
        self.assertIn(epc.NIL_POSTCODE_MARKER, body)
        self.assertTrue(self.EXPECT(body))
        self.assertEqual(epc.CERT_RE.findall(body), [])

    def test_a_street_with_no_certificates(self):
        body = read("epc-search-street-no-results-joiner.html")
        self.assertIn(epc.NIL_STREET_MARKER, body)
        self.assertTrue(self.EXPECT(body))
        self.assertEqual(epc.CERT_RE.findall(body), [])

    def test_a_results_page_is_still_a_results_page(self):
        body = read("epc-search-SE1-9SG.html")
        self.assertTrue(self.EXPECT(body))
        self.assertNotIn(epc.NIL_STREET_MARKER, body)
        self.assertNotIn(epc.TOO_MANY_MARKER, body)
        self.assertGreater(len(epc.CERT_RE.findall(body)), 0)


class TestTooManyResultsPage(unittest.TestCase):
    """The street search refuses a busy street and serves its own page saying so.

    Fixture: the live answer for "Tooley Street, London" on 2026-09-03. This is the
    failure mode that silently loses the streets with the most homes on them, so it
    has to read as a real answer with `too_many_results` set, not as a fetch failure
    and not as an empty street.
    """
    BODY = None

    @classmethod
    def setUpClass(cls):
        cls.BODY = read("epc-search-street-too-many-tooley.html")

    def test_the_marker_is_on_the_page(self):
        self.assertIn(epc.TOO_MANY_MARKER, self.BODY)
        self.assertIn("Search by postcode instead", self.BODY)

    def test_the_content_assertion_accepts_it(self):
        expect = (lambda b: "epb-search-results" in b or "no certificates" in b.lower()
                  or "could not find" in b.lower() or epc.TOO_MANY_MARKER in b)
        self.assertTrue(expect(self.BODY), "a real answer must not read as a failed fetch")

    def test_it_carries_no_certificate_rows(self):
        self.assertEqual(epc.CERT_RE.findall(self.BODY), [])

    def test_a_results_page_is_not_mistaken_for_it(self):
        results = read("epc-search-SE1-9SG.html")
        self.assertNotIn(epc.TOO_MANY_MARKER, results)


if __name__ == "__main__":
    unittest.main()


class TestBuildingPropagatesAFailedSearch(unittest.TestCase):
    """A search that died (curl error, sandbox, timeout) is not an empty postcode."""

    def test_a_dead_search_is_ok_false_with_a_null_count(self):
        dead = {"ok": False, "note": "curl error 56: Failure writing output to destination",
                "count": 0, "results": [], "query": {"postcode": "SE1 8BW"},
                "source_url": "https://example.invalid/search"}
        real = epc.search
        epc.search = lambda **kw: dead
        try:
            out = epc.building(postcode="SE1 8BW")
        finally:
            epc.search = real
        self.assertIs(False, out["ok"])
        self.assertIn("curl error 56", out["note"])
        self.assertIsNone(out["summary"]["certificates_found"])
        self.assertIsNone(out["summary"]["earliest_assessment_year"])

    def test_an_empty_postcode_is_ok_true_with_a_zero_count(self):
        empty = {"ok": True, "note": None, "count": 0, "results": [],
                 "query": {"postcode": "SE1 8BW"}, "source_url": "https://example.invalid/search"}
        real = epc.search
        epc.search = lambda **kw: empty
        try:
            out = epc.building(postcode="SE1 8BW")
        finally:
            epc.search = real
        self.assertIs(True, out["ok"])
        self.assertIsNone(out["note"])
        self.assertEqual(0, out["summary"]["certificates_found"])
