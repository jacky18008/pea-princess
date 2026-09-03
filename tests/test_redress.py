"""Offline parser tests for scripts/redress.py.

Run: python3 -m unittest tests/test_redress.py
The Client Money Protect fixtures are the real admin-ajax JSON with each
member's email and phone replaced by placeholders - the parser never reads
those fields, so redacting them costs the tests nothing.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
import redress  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class TestClientMoneyProtect(unittest.TestCase):
    def setUp(self):
        self.status, self.rows = redress.parse_cmp(read("redress-cmp-london.json"))

    def test_status_and_count(self):
        self.assertEqual(self.status, "sucess")   # the API really does spell it that way
        self.assertEqual(len(self.rows), 12)

    def test_member_fields(self):
        r = self.rows[0]
        self.assertEqual(r["name"], "DW LONDON ESTATES LTD")
        self.assertEqual(r["membership_number"], "CMP015515")
        self.assertEqual(r["address"], "6 Leigh Street WC1H9EW")
        self.assertEqual(r["membership_status"], "Active")
        self.assertIsNone(r["valid_until"])   # the API carries no expiry date
        self.assertEqual(r["branches"], [])

    def test_contact_details_are_not_carried_through(self):
        for r in self.rows:
            self.assertEqual(set(r), {"name", "membership_number", "address",
                                      "membership_status", "valid_until", "branches"})

    def test_no_match_payload(self):
        status, rows = redress.parse_cmp(read("redress-cmp-miss.json"))
        self.assertEqual(status, "fail")
        self.assertEqual(rows, [])

    def test_garbage_payload_is_not_an_exception(self):
        self.assertEqual(redress.parse_cmp("<html>nope</html>"), (None, []))


class TestHeatTrust(unittest.TestCase):
    def setUp(self):
        self.d = redress.parse_heat_trust(read("redress-heattrust-members.html"))

    def test_headline_numbers_and_as_at_date(self):
        self.assertEqual(self.d["as_at"], "31 July 2026")
        self.assertEqual(self.d["total_members"], 31)
        self.assertEqual(self.d["total_sites"], 154)
        self.assertEqual(self.d["consumers_protected"], 96800)

    def test_parsed_lists_match_the_headline_counts(self):
        self.assertEqual(self.d["participants_listed"], self.d["total_members"])
        self.assertEqual(self.d["sites_listed"], self.d["total_sites"])

    def test_participants(self):
        self.assertIn("Loka Energy Ltd (Hemiko)", self.d["participants"])
        self.assertIn("Switch2 Energy Ltd", self.d["participants"])
        self.assertIn("Kensa Utilities Ltd", self.d["participants"])

    def test_london_sites_carry_their_borough(self):
        gp = [s for s in self.d["sites"] if s["name"] == "Greenwich Peninsula"]
        self.assertEqual(len(gp), 1)
        self.assertEqual(gp[0]["area"], "Greenwich")
        self.assertTrue(gp[0]["region"].startswith("Registered Sites in London"))

    def test_sites_outside_london_are_parsed_from_the_other_layout(self):
        bath = [s for s in self.d["sites"] if s["name"] == "Bath Western Riverside"]
        self.assertEqual(len(bath), 1)
        self.assertEqual(bath[0]["area"], "Bath and North East Somerset")
        self.assertIn("rest of England", bath[0]["region"])

    def test_no_footer_text_leaks_into_the_site_list(self):
        for s in self.d["sites"]:
            self.assertNotIn("Heat Customer Protection", s["name"])
            self.assertNotIn("document.getElementById", s["name"])
            self.assertTrue(s["area"], s)

    def test_a_stray_underlined_break_does_not_lose_the_area(self):
        # "Glasgow:" is followed by Dalmarnock, an empty underlined <br>, then Wyndford
        glasgow = sorted(s["name"] for s in self.d["sites"] if s["area"] == "Glasgow")
        self.assertEqual(glasgow, ["Dalmarnock", "Wyndford"])


class TestRogueChecker(unittest.TestCase):
    def test_unfiltered_page_has_ten_cards(self):
        cards = redress.parse_rogue(read("redress-rogue-base.html"))
        self.assertEqual(len(cards), 10)

    def test_card_fields(self):
        cards = redress.parse_rogue(read("redress-rogue-name-reptons.html"))
        self.assertEqual(len(cards), 1)
        c = cards[0]
        self.assertEqual(c["name"], "Reptons Global Property LTD (07523446)")
        self.assertEqual(c["enforcement_action_type"],
                         "Civil Penalty (Housing and Planning Act 2016)")
        self.assertEqual(c["enforcement_authority"], "Redbridge")
        self.assertIn("IG1 3BW", c["address"])
        self.assertEqual(c["fine"], "5000")
        self.assertEqual(c["enforcement_date"], "Wednesday 11 April 2029")
        self.assertEqual(c["record_expires"], "Thursday 11 April 2030")
        self.assertIn("Houses in Multiple Occupation", c["offence"])
        self.assertTrue(c["offence_description"])

    def test_every_card_has_every_key(self):
        for c in redress.parse_rogue(read("redress-rogue-base.html")):
            self.assertEqual(set(c), {"name"} | set(redress.ROGUE_FIELDS.values()))

    def test_no_results_page(self):
        body = read("redress-rogue-noresults.html")
        self.assertEqual(redress.parse_rogue(body), [])
        self.assertIn("Sorry, no results were found", body)


class TestManualSources(unittest.TestCase):
    def test_prs_is_manual_and_fetches_nothing(self):
        d = redress.prs()
        self.assertEqual(d["access"], "manual")
        self.assertEqual(d["evidence_class"], "U")
        self.assertIsNone(d["http_status"])
        self.assertTrue(d["manual_instructions"])
        self.assertIn("propertyredress.co.uk", d["source_url"])

    def test_tpo_is_manual_and_says_why(self):
        d = redress.tpo()
        self.assertEqual(d["access"], "manual")
        self.assertEqual(d["evidence_class"], "U")
        self.assertIn("ClaudeBot", d["note"])
        self.assertTrue(d["manual_instructions"])

    def test_manual_records_are_json_serialisable(self):
        json.dumps(redress.prs())
        json.dumps(redress.tpo())


if __name__ == "__main__":
    unittest.main()
