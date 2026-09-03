"""Offline parser tests for scripts/landregistry.py.

Run: python3 -m unittest tests/test_landregistry.py
Fixtures are raw SPARQL JSON results from
https://landregistry.data.gov.uk/landregistry/query.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import landregistry  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class TestPostcodeNormalisation(unittest.TestCase):
    def test_spacing_and_case(self):
        for given in ("se1 2be", "SE12BE", " se12be ", "Se1  2Be"):
            self.assertEqual(landregistry.normalise_postcode(given), "SE1 2BE")

    def test_long_outcode(self):
        self.assertEqual(landregistry.normalise_postcode("sw1h0dx"), "SW1H 0DX")

    def test_short_input_is_returned_upper_cased(self):
        self.assertEqual(landregistry.normalise_postcode("se1"), "SE1")


class TestQueryBuilder(unittest.TestCase):
    def test_postcode_is_embedded_and_ordered_by_date(self):
        q = landregistry.build_query("SE1 2BE")
        self.assertIn('lrcommon:postcode "SE1 2BE"', q)
        self.assertIn("ORDER BY ?date", q)
        self.assertIn("lrppi:newBuild", q)
        self.assertNotIn("FILTER", q)

    def test_since_adds_a_date_filter(self):
        q = landregistry.build_query("SE1 2BE", since=2015)
        self.assertIn('FILTER (?date >= "2015-01-01"^^xsd:date)', q)

    def test_limit(self):
        self.assertIn("LIMIT 25", landregistry.build_query("SE1 2BE", limit=25))


class TestResultParsing(unittest.TestCase):
    def setUp(self):
        self.rows = landregistry.parse_results(read("landregistry-price-paid-se12be.json"))

    def test_row_count(self):
        self.assertEqual(len(self.rows), 101)

    def test_rows_are_sorted_by_date(self):
        dates = [r["date"] for r in self.rows]
        self.assertEqual(dates, sorted(dates))

    def test_first_row_fields(self):
        r = self.rows[0]
        self.assertEqual(r["date"], "1995-02-17")
        self.assertEqual(r["price"], 175000)
        self.assertEqual(r["paon"], "ST. SAVIOURS WHARF")
        self.assertEqual(r["saon"], "FLAT 38")
        self.assertEqual(r["street"], "MILL STREET")
        self.assertEqual(r["town"], "LONDON")
        self.assertEqual(r["property_type"], "flat-maisonette")
        self.assertEqual(r["estate_type"], "leasehold")
        self.assertEqual(r["category"], "standardPricePaidTransaction")
        self.assertIs(r["new_build"], False)

    def test_new_build_is_a_real_boolean(self):
        for r in self.rows:
            self.assertIn(r["new_build"], (True, False, None))
        self.assertEqual(sum(1 for r in self.rows if r["new_build"]), 3)

    def test_missing_optionals_are_none_not_guesses(self):
        rows = landregistry.parse_results(read("landregistry-price-paid-se19sg.json"))
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[0]["saon"])       # "8 London Bridge Street" has no sub-address
        self.assertEqual(rows[1]["saon"], "LEVEL 11")

    def test_accepts_a_dict_as_well_as_a_string(self):
        payload = json.loads(read("landregistry-price-paid-se19sg.json"))
        self.assertEqual(len(landregistry.parse_results(payload)), 2)

    def test_empty_result_set(self):
        empty = {"head": {"vars": []}, "results": {"bindings": []}}
        self.assertEqual(landregistry.parse_results(empty), [])


class TestSummary(unittest.TestCase):
    def setUp(self):
        self.rows = landregistry.parse_results(read("landregistry-price-paid-se12be.json"))

    def test_counts_and_extremes(self):
        s = landregistry.summarise(self.rows)
        self.assertEqual(s["count"], 101)
        self.assertEqual(s["earliest_transaction"]["date"], "1995-02-17")
        self.assertEqual(s["latest_transaction"]["date"], "2026-05-26")

    def test_earliest_new_build_is_the_completion_proof(self):
        s = landregistry.summarise(self.rows)
        self.assertEqual(s["new_build_count"], 3)
        self.assertEqual(s["earliest_new_build_year"], 1998)
        self.assertEqual(s["earliest_new_build_transaction"]["date"], "1998-02-26")
        self.assertTrue(s["earliest_new_build_transaction"]["new_build"])

    def test_no_new_build_rows_leaves_nulls_not_guesses(self):
        rows = landregistry.parse_results(read("landregistry-price-paid-se19sg.json"))
        s = landregistry.summarise(rows)
        self.assertEqual(s["new_build_count"], 0)
        self.assertIsNone(s["earliest_new_build_transaction"])
        self.assertIsNone(s["earliest_new_build_year"])

    def test_same_building_matches(self):
        s = landregistry.summarise(self.rows, paon="ST. SAVIOURS WHARF")
        self.assertEqual(s["same_building_matches"]["query"], "ST. SAVIOURS WHARF")
        self.assertEqual(s["same_building_matches"]["count"], 101)
        self.assertEqual(s["same_building_price_range"]["min"], 101000)
        self.assertEqual(s["same_building_price_range"]["first_date"], "1995-02-17")

    def test_same_building_matches_on_a_flat_number(self):
        s = landregistry.summarise(self.rows, paon="FLAT 46")
        self.assertGreaterEqual(s["same_building_matches"]["count"], 1)
        for r in s["same_building_matches"]["transactions"]:
            self.assertEqual(r["saon"], "FLAT 46")

    def test_unknown_building_returns_zero_not_everything(self):
        s = landregistry.summarise(self.rows, paon="NOWHERE HOUSE")
        self.assertEqual(s["same_building_matches"]["count"], 0)

    def test_no_paon_means_no_same_building_key(self):
        self.assertNotIn("same_building_matches", landregistry.summarise(self.rows))


class TestTitleHelp(unittest.TestCase):
    def test_is_manual_and_fetches_nothing(self):
        d = landregistry.title_help()
        self.assertEqual(d["access"], "manual")
        self.assertEqual(d["evidence_class"], "U")
        self.assertIsNone(d["http_status"])
        self.assertEqual(d["cost"]["title_register"], "GBP 7")
        self.assertIn("Cloudflare", d["note"])

    def test_lists_the_fields_to_paste_back(self):
        fields = " ".join(landregistry.title_help()["paste_back_fields"]).lower()
        for wanted in ("proprietor", "title number", "tenure", "date of registration"):
            self.assertIn(wanted, fields)

    def test_serialisable(self):
        json.dumps(landregistry.title_help())


class TestContentAssertion(unittest.TestCase):
    def test_expect_accepts_sparql_json(self):
        self.assertTrue(landregistry._expect(read("landregistry-price-paid-se19sg.json")))

    def test_expect_rejects_an_html_error_page(self):
        self.assertFalse(landregistry._expect("<html><title>Just a moment...</title></html>"))
        self.assertFalse(landregistry._expect('{"error":"nope"}'))


if __name__ == "__main__":
    unittest.main()
