"""Offline parser tests for scripts/company.py.

Run: python3 -m unittest tests/test_company.py
Fixtures are captured from find-and-update.company-information.service.gov.uk and
trimmed to the tab panel / results table the parsers actually read.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import company  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class TestAdvancedSearchParsing(unittest.TestCase):
    def setUp(self):
        self.body = read("company-advanced-name-getliving.html")
        self.rows = company.parse_advanced_results(self.body)

    def test_row_count_and_site_total(self):
        self.assertEqual(len(self.rows), 20)
        self.assertEqual(company._advanced_total(self.body), 66)

    def test_dissolved_row_is_flagged(self):
        r = self.rows[0]
        self.assertEqual(r["company_number"], "07883003")
        self.assertEqual(r["name"], "GET LIVING IT LTD")
        self.assertEqual(r["status"], "Dissolved")
        self.assertTrue(r["dissolved"])
        self.assertEqual(r["dissolved_on"], "20 April 2021")
        self.assertEqual(r["incorporated"], "15 December 2011")
        self.assertEqual(r["sic_codes"], ["62090", "86900"])
        self.assertIn("Peterchurch", r["address"])

    def test_active_row(self):
        r = [x for x in self.rows if x["company_number"] == "15778219"][0]
        self.assertEqual(r["status"], "Active")
        self.assertFalse(r["dissolved"])
        self.assertIsNone(r["dissolved_on"])
        self.assertEqual(r["company_type"], "Private limited company")
        self.assertEqual(r["sic_codes"], ["68209"])
        self.assertEqual(r["address"], "1 East Park Walk, London, England E20 1JL")

    def test_overseas_entity_says_registered_not_incorporated(self):
        r = [x for x in self.rows if x["company_number"] == "OE006451"][0]
        self.assertEqual(r["status"], "Registered")
        self.assertEqual(r["registration_event"], "Registered")
        self.assertEqual(r["incorporated"], "5 December 2022")
        self.assertEqual(r["company_type"], "Overseas entity")
        self.assertIn("Tortola", r["address"])
        self.assertFalse(r["dissolved"])

    def test_uk_rows_say_incorporated(self):
        r = [x for x in self.rows if x["company_number"] == "15778219"][0]
        self.assertEqual(r["registration_event"], "Incorporated")

    def test_address_search_rows(self):
        body = read("company-advanced-address-se19sg.html")
        rows = company.parse_advanced_results(body)
        self.assertEqual(len(rows), 20)
        self.assertEqual(company._advanced_total(body), 3259)
        # every row on page 1 really is at the queried postcode
        self.assertTrue(all("SE1 9SG" in (r["address"] or "") for r in rows))


class TestProfileParsing(unittest.TestCase):
    def test_active_company(self):
        d = company.parse_profile(read("company-profile-08854998.html"))
        self.assertEqual(d["name"], "LOKA ENERGY LIMITED")
        self.assertEqual(d["company_number"], "08854998")
        self.assertEqual(d["status"], "Active")
        self.assertEqual(d["company_type"], "Private limited Company")
        self.assertEqual(d["incorporated_on"], "21 January 2014")
        self.assertIsNone(d["dissolved_on"])
        self.assertEqual(d["registered_office_address"],
                         "Level 9 6 Mitre Passage, Greenwich Peninsula, London, England, SE10 0ER")
        self.assertEqual(d["accounts"]["last_made_up_to"], "30 June 2025")
        self.assertEqual(d["accounts"]["next_made_up_to"], "30 June 2026")
        self.assertEqual(d["accounts"]["next_due"], "31 March 2027")
        self.assertFalse(d["accounts"]["overdue"])
        self.assertEqual(d["confirmation_statement"]["next_statement_date"], "1 October 2026")
        self.assertEqual(d["confirmation_statement"]["next_due"], "15 October 2026")
        self.assertEqual(d["confirmation_statement"]["last_statement_dated"], "1 October 2025")
        self.assertEqual(d["sic_codes"], [{"code": "74909",
                                           "description": "Other professional, scientific and "
                                                          "technical activities not elsewhere "
                                                          "classified"}])
        self.assertEqual(d["previous_names"],
                         [{"name": "GREENWICH PENINSULA OPCO LIMITED",
                           "period": "21 Jan 2014 - 03 Sep 2014"}])
        self.assertEqual(d["insolvency_signals_profile"], [])

    def test_dissolved_company_is_a_signal(self):
        d = company.parse_profile(read("company-profile-dissolved-07883003.html"))
        self.assertEqual(d["status"], "Dissolved")
        self.assertEqual(d["dissolved_on"], "20 April 2021")
        self.assertEqual(len(d["insolvency_signals_profile"]), 1)
        self.assertIn("Dissolved", d["insolvency_signals_profile"][0])
        self.assertEqual([s["code"] for s in d["sic_codes"]], ["62090", "86900"])

    def test_property_company_sic(self):
        d = company.parse_profile(read("company-profile-sic68209-15778219.html"))
        self.assertEqual([s["code"] for s in d["sic_codes"]], ["68209"])
        self.assertEqual(d["status"], "Active")


class TestSicClassifier(unittest.TestCase):
    def test_68209_owner(self):
        r = company.classify_sic([{"code": "68209", "description": "Other letting and operating"}])
        self.assertEqual(r["landlord_type_hint"], "owner_or_investor")
        self.assertEqual(r["matched_sic"], "68209")
        self.assertEqual(r["evidence_class"], "I")

    def test_68310_is_an_agent_not_an_owner(self):
        r = company.classify_sic(["68310"])
        self.assertEqual(r["landlord_type_hint"], "agent_not_owner")

    def test_68320_managing_agent(self):
        self.assertEqual(company.classify_sic(["68320"])["landlord_type_hint"], "managing_agent")

    def test_68100_buying_selling(self):
        self.assertEqual(company.classify_sic(["68100"])["landlord_type_hint"], "buying_selling")

    def test_unrelated_sic_is_other(self):
        r = company.classify_sic([{"code": "74909", "description": "Other professional"}])
        self.assertEqual(r["landlord_type_hint"], "other")
        self.assertIsNone(r["matched_sic"])

    def test_empty_is_other(self):
        self.assertEqual(company.classify_sic([])["landlord_type_hint"], "other")
        self.assertEqual(company.classify_sic(None)["landlord_type_hint"], "other")

    def test_owner_wins_over_agent_when_both_present(self):
        r = company.classify_sic(["68310", "68209"])
        self.assertEqual(r["matched_sic"], "68209")

    def test_every_hint_carries_the_brand_note(self):
        for codes in (["68209"], ["68310"], ["68320"], ["68100"], ["12345"]):
            self.assertIn("tenancy agreement", company.classify_sic(codes)["note"])


class TestOfficersParsing(unittest.TestCase):
    def setUp(self):
        self.d = company.parse_officers(read("company-officers-08854998.html"))

    def test_counts(self):
        self.assertEqual(self.d["officers_listed"], 6)
        self.assertEqual(self.d["active_officer_count"], 2)
        self.assertEqual(self.d["officers_total_reported"], 6)
        self.assertEqual(self.d["resignations_reported"], 4)

    def test_active_officer_fields(self):
        o = self.d["officers"][0]
        self.assertEqual(o["name"], "ELLIS, Aaron Max")
        self.assertEqual(o["role"], "Director")
        self.assertEqual(o["status"], "Active")
        self.assertEqual(o["appointed_on"], "18 December 2025")
        self.assertIsNone(o["resigned_on"])

    def test_resigned_officer_has_a_resignation_date(self):
        resigned = [o for o in self.d["officers"] if o["resigned_on"]]
        self.assertEqual(len(resigned), 4)
        self.assertTrue(all(o["status"] == "Resigned" for o in resigned))

    def test_no_personal_data_is_extracted(self):
        for o in self.d["officers"]:
            self.assertEqual(set(o), {"name", "role", "status", "appointed_on", "resigned_on"})


class TestChargesParsing(unittest.TestCase):
    def test_outstanding_charges(self):
        d = company.parse_charges(read("company-charges-08613907.html"))
        self.assertEqual(d["total"], 2)
        self.assertEqual(d["outstanding"], 2)
        self.assertEqual(d["satisfied"], 0)
        self.assertEqual(d["part_satisfied"], 0)
        self.assertEqual(len(d["charges"]), 2)
        c = d["charges"][0]
        self.assertEqual(c["charge"], "Charge code 0861 3907 0002")
        self.assertEqual(c["status"], "Outstanding")
        self.assertEqual(c["created"], "1 October 2019")
        self.assertEqual(c["persons_entitled"], ["Cbre Loan Services Limited"])

    def test_company_with_no_charges(self):
        d = company.parse_charges(read("company-charges-none-08854998.html"))
        self.assertEqual(d["total"], 0)
        self.assertEqual(d["outstanding"], 0)
        self.assertEqual(d["charges"], [])


class TestFilingHistoryParsing(unittest.TestCase):
    def setUp(self):
        self.entries = company.parse_filings(read("company-filings-08854998-page2.html"), limit=60)

    def test_entries(self):
        self.assertEqual(len(self.entries), 18)
        e = self.entries[0]
        self.assertTrue(e["date"])
        self.assertTrue(e["type"])
        self.assertTrue(e["description"])
        self.assertTrue(e["document_url"].startswith(
            "https://find-and-update.company-information.service.gov.uk/company/08854998/"
            "filing-history/"))

    def test_limit_is_respected(self):
        self.assertEqual(len(company.parse_filings(
            read("company-filings-08854998-page2.html"), limit=5)), 5)

    def test_flags_registered_office_change(self):
        addr, names, accounts = company._flag_filings(self.entries)
        self.assertEqual(len(addr), 1)
        self.assertEqual(addr[0]["type"], "AD01")
        self.assertIn("Registered office address changed", addr[0]["description"])

    def test_flags_name_change(self):
        addr, names, accounts = company._flag_filings(self.entries)
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0]["type"], "CERTNM")

    def test_flags_accounts_with_made_up_to(self):
        addr, names, accounts = company._flag_filings(self.entries)
        self.assertEqual(len(accounts), 5)
        self.assertTrue(all(a["made_up_to"] for a in accounts))
        self.assertEqual(accounts[0]["type"], "AA")

    def test_flagger_on_synthetic_rows(self):
        rows = [
            {"date": "01 Jan 2020", "type": "AD01",
             "description": "Registered office address changed from A to B", "document_url": None},
            {"date": "02 Jan 2020", "type": "CERTNM",
             "description": "Company name changed old ltd", "document_url": None},
            {"date": "03 Jan 2020", "type": "AA",
             "description": "Total exemption full accounts made up to 31 December 2019",
             "document_url": None},
            {"date": "04 Jan 2020", "type": "CS01",
             "description": "Confirmation statement made on 1 January 2020", "document_url": None},
        ]
        addr, names, accounts = company._flag_filings(rows)
        self.assertEqual([a["type"] for a in addr], ["AD01"])
        self.assertEqual([n["type"] for n in names], ["CERTNM"])
        self.assertEqual(accounts[0]["made_up_to"], "31 December 2019")


class TestRmcDetection(unittest.TestCase):
    def _hits(self, name):
        import re
        return [why for pat, why in company.RMC_PATTERNS if re.search(pat, name.upper())]

    def test_typical_rmc_names_match(self):
        for n in ["ACACIA COURT RESIDENTS MANAGEMENT COMPANY LIMITED",
                  "12 MILL STREET RTM COMPANY LIMITED",
                  "RIVERSIDE RIGHT TO MANAGE COMPANY LTD",
                  "SOMEWHERE FREEHOLD LIMITED",
                  "MILL WHARF MANAGEMENT COMPANY LIMITED"]:
            self.assertTrue(self._hits(n), n)

    def test_ordinary_trading_names_do_not_match(self):
        for n in ["ART ASSETS ADMINISTRATION LLP", "EURO VS TRADING LTD", "LOKA ENERGY LIMITED"]:
            self.assertFalse(self._hits(n), n)


class TestDotEnv(unittest.TestCase):
    def test_parses_key_value_lines(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# comment\n\nCOMPANIES_HOUSE_KEY = \"abc123\"\nOTHER=plain\nbroken line\n")
            path = fh.name
        try:
            env = company.read_dotenv(path)
            self.assertEqual(env["COMPANIES_HOUSE_KEY"], "abc123")
            self.assertEqual(env["OTHER"], "plain")
            self.assertNotIn("broken line", env)
        finally:
            os.unlink(path)

    def test_missing_file_is_empty(self):
        self.assertEqual(company.read_dotenv("/nonexistent/path/.env"), {})


if __name__ == "__main__":
    unittest.main()
