"""Live smoke tests — one per script, against the real endpoints.

These make real network calls, so they are SKIPPED unless you opt in:

    VETFLAT_LIVE=1 python3 -m unittest tests/live_smoke.py

The file is deliberately not named `test_*.py`, so the offline suite
(`python3 -m unittest discover -s tests -p 'test_*.py'`) never picks it up.

Each class keeps its call budget small and leans on the on-disk cache in
`_fetch.py`, so a second run inside the cache window costs nothing. Scripts
added later should append their own class here rather than editing an existing
one.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))

LIVE = os.environ.get("VETFLAT_LIVE") == "1"
WHY = "set VETFLAT_LIVE=1 to run the live smoke tests"

# A public, stable reference point: the SE1 9SG postcode centroid at London Bridge.
LAT, LNG = 51.504963, -0.087625
POSTCODE = "SE1 9SG"


# ---------------------------------------------------------------- geo.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveGeo(unittest.TestCase):
    """postcodes.io — 2 calls."""

    def test_lookup_and_reverse_agree(self):
        import geo
        up = geo.lookup(POSTCODE)
        self.assertTrue(up["ok"], up["note"])
        self.assertEqual(up["http_status"], 200)
        self.assertEqual(up["evidence_class"], "G")
        self.assertEqual(up["postcode"], POSTCODE)
        self.assertAlmostEqual(up["lat"], LAT, places=3)
        self.assertAlmostEqual(up["lng"], LNG, places=3)
        self.assertTrue(up["admin_district"])
        self.assertTrue(up["lsoa"])

        back = geo.reverse(up["lat"], up["lng"], radius=200, limit=10)
        self.assertTrue(back["ok"], back["note"])
        self.assertGreater(back["count"], 0)
        self.assertEqual(back["nearest"]["postcode"], POSTCODE)
        self.assertLess(back["nearest"]["distance_m"], 50)

    def test_the_radius_cap_is_still_a_cap(self):
        import geo
        with self.assertRaises(ValueError):
            geo.nearby(LAT, LNG, radius=geo.MAX_RADIUS_M + 1)


# -------------------------------------------------------------- crime.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveCrime(unittest.TestCase):
    """data.police.uk — 1 call for `latest`, 5 for a one-month box."""

    def test_latest_month_is_published_and_lagging(self):
        import crime
        out = crime.latest()
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["evidence_class"], "G")
        self.assertRegex(out["latest_month"], r"^\d{4}-\d{2}$")

    def test_one_month_box_parses_and_never_extrapolates(self):
        import crime
        out = crime.box(LAT, LNG, half_m=150, months=1)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(len(out["months_requested"]), 1)
        self.assertEqual(out["months_missing"], [])
        self.assertEqual(out["months_fetched"], out["months_requested"])
        self.assertEqual(sum(out["per_month"].values()), out["total"])
        self.assertEqual(sum(out["by_category"].values()), out["total"])
        self.assertLessEqual(out["predatory_subset"]["count"], out["total"])
        self.assertEqual(sorted(out["sensitivity"]["counts"]),
                         ["centre", "east_20m", "north_20m", "south_20m", "west_20m"])
        self.assertIn("anonymised", out["method"])


# ------------------------------------------------------------ commute.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveCommute(unittest.TestCase):
    """TfL Unified API — 1 StopPoint call and 1 journey call."""

    def test_stations_nearby(self):
        import commute
        out = commute.stations(LAT, LNG, radius=800)
        self.assertTrue(out["ok"], out["note"])
        self.assertGreater(out["count"], 0)
        first = out["stations"][0]
        self.assertTrue(first["name"])
        self.assertTrue(first["modes"])
        self.assertGreater(first["walk_m_estimate"], first["straight_line_m"])

    def test_one_rail_journey_plan(self):
        import commute
        out = commute.journey(POSTCODE, "WC2R 2LS", arrive="09:00",
                              date="next-weekday", plans=["rail"])
        self.assertTrue(out["ok"], out["note"])
        rail = out["plans"]["rail"]
        self.assertTrue(rail["ok"], rail["note"])
        self.assertGreater(rail["duration_min"], 0)
        self.assertTrue(rail["legs"])
        self.assertGreaterEqual(rail["changes"], 0)
        self.assertNotIn("app_key=", out["source_url"].replace("app_key=REDACTED", ""))

    def test_destination_is_never_assumed(self):
        import commute
        with self.assertRaises(ValueError):
            commute.journey(POSTCODE, None)


# ------------------------------------------------------------ company.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveCompany(unittest.TestCase):
    """Companies House HTML site - 1 search call, 3 profile calls, 1 filings call.

    08854998 is LOKA ENERGY LIMITED, a heat supplier. Its incorporation date and
    its first name are historical facts and cannot change; status, officers and
    accounts can, so nothing here asserts on those values.
    """
    NUMBER = "08854998"

    def test_search_returns_status_for_every_row(self):
        import company
        out = company.search("Get Living", limit=20)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["http_status"], 200)
        self.assertEqual(out["evidence_class"], "G")
        self.assertGreater(out["count"], 0)
        self.assertIn("advanced-search", out["source_url"])
        for r in out["results"]:
            self.assertRegex(r["company_number"], r"^[0-9A-Z]{8}$")
            self.assertTrue(r["name"])
            self.assertTrue(r["status"], "the plain search page has no status; advanced does")
            self.assertTrue(r["incorporated"])
            self.assertEqual(r["dissolved"], "dissolv" in (r["status"] or "").lower())
            if r["dissolved"]:
                self.assertTrue(r["dissolved_on"])
        self.assertIn("tenancy agreement", out["same_name_warning"])

    def test_profile_reads_status_sic_officers_and_charges(self):
        import company
        out = company.profile(self.NUMBER, skip_filings=True)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["http_status"], 200)
        self.assertEqual(out["company_number"], self.NUMBER)
        self.assertTrue(out["name"])
        self.assertTrue(out["status"])
        self.assertEqual(out["incorporated_on"], "21 January 2014")
        self.assertTrue(out["registered_office_address"])
        self.assertTrue(out["sic_codes"])
        self.assertTrue(all(s["code"] for s in out["sic_codes"]))
        self.assertTrue(out["charges_count"]["ok"])
        self.assertIsNotNone(out["charges_count"]["total"])
        self.assertEqual(len(out["charges"]), out["charges_count"]["total"])
        self.assertGreater(len(out["officers"]), 0)
        self.assertLessEqual(out["active_officer_count"], len(out["officers"]))
        self.assertIn(out["landlord_type_hint"],
                      ["owner_or_investor", "agent_not_owner", "managing_agent",
                       "buying_selling", "other"])
        self.assertIn("tenancy agreement", out["note"])
        self.assertIn(out["insolvency_flag"], (True, False))

    def test_filing_history_flags_and_document_links(self):
        import company
        out = company.filings(self.NUMBER, limit=25)
        self.assertTrue(out["ok"], out["note"])
        self.assertGreater(out["count"], 0)
        for e in out["filings"]:
            self.assertTrue(e["date"])
            self.assertTrue(e["description"])
            if e["document_url"]:
                self.assertIn("/filing-history/", e["document_url"])
        for a in out["accounts_filings"]:
            self.assertIn("accounts", (a["description"] or "").lower())

    def test_missing_key_makes_the_api_path_manual_not_a_crash(self):
        import company
        if company.api_key():
            self.skipTest("a COMPANIES_HOUSE_KEY is configured; the keyless path is not exercised")
        out = company.api_profile(self.NUMBER)
        self.assertEqual(out["access"], "manual")
        self.assertFalse(out["ok"])


# ------------------------------------------------------------ redress.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveRedress(unittest.TestCase):
    """Client Money Protect (1 POST), Heat Trust (1 GET), GLA checker (2 GETs)."""

    def test_client_money_protect_search_is_server_side(self):
        import redress
        out = redress.cmp_search("London")
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["access"], "automated")
        self.assertEqual(out["api_status"], "sucess")   # yes, the API misspells it
        self.assertGreater(out["count"], 0)
        for m in out["matches"]:
            self.assertTrue(m["name"])
            self.assertRegex(m["membership_number"], r"^CMP\d+$")
            self.assertIsNone(m["valid_until"])
            self.assertNotIn("email", m)
            self.assertNotIn("phone", m)

    def test_heat_trust_counts_match_the_lists(self):
        import redress
        out = redress.heat_trust(site="Greenwich Peninsula")
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["evidence_class"], "C")
        self.assertTrue(out["as_at"])
        self.assertGreater(out["total_members"], 0)
        self.assertGreater(out["total_sites"], 0)
        # a parser that silently loses list items is the failure mode worth catching
        self.assertGreaterEqual(out["participants_listed"], out["total_members"] * 0.9)
        self.assertGreaterEqual(out["sites_listed"], out["total_sites"] * 0.9)
        for s in out["matches"].get("sites", []):
            self.assertTrue(s["area"])

    def test_rogue_checker_hit_and_miss(self):
        import redress
        hit = redress.rogue(address="London")
        self.assertTrue(hit["ok"], hit["note"])
        for c in hit["results"]:
            self.assertTrue(c["name"])
            self.assertEqual(set(c), {"name"} | set(redress.ROGUE_FIELDS.values()))
        if hit["results"]:
            self.assertEqual(hit["evidence_class"], "G")

        miss = redress.rogue(name="zzznotarealnamezzz")
        self.assertTrue(miss["ok"], miss["note"])
        self.assertEqual(miss["count"], 0)
        self.assertEqual(miss["evidence_class"], "U")
        self.assertTrue(miss["no_results_banner"])
        self.assertIn("no entry found", miss["interpretation"])

    def test_prs_and_tpo_never_fetch(self):
        import redress
        for out in (redress.prs(), redress.tpo()):
            self.assertEqual(out["access"], "manual")
            self.assertIsNone(out["http_status"])


# ------------------------------------------------------ landregistry.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveLandRegistry(unittest.TestCase):
    """HM Land Registry SPARQL - 1 POST. SE1 2BE is St Saviours Wharf, Bermondsey."""

    def test_price_paid_by_postcode(self):
        import landregistry
        out = landregistry.price_paid("se1 2be")
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["http_status"], 200)
        self.assertEqual(out["evidence_class"], "G")
        self.assertEqual(out["query"]["postcode"], "SE1 2BE")
        self.assertGreater(out["count"], 0)
        dates = [t["date"] for t in out["transactions"]]
        self.assertEqual(dates, sorted(dates))
        # Price Paid is append-only, so the first recorded sale can only get earlier
        self.assertLessEqual(out["earliest_transaction"]["date"], "1995-02-17")
        for t in out["transactions"]:
            self.assertIsInstance(t["price"], int)
            self.assertIn(t["new_build"], (True, False, None))
            self.assertIn(t["estate_type"], ("leasehold", "freehold", None))

    def test_since_and_paon_narrow_the_answer(self):
        import landregistry
        out = landregistry.price_paid("SE1 2BE", since=2020, paon="ST. SAVIOURS WHARF")
        self.assertTrue(out["ok"], out["note"])
        self.assertTrue(all(t["date"] >= "2020-01-01" for t in out["transactions"]))
        self.assertEqual(out["same_building_matches"]["count"], out["count"])

    def test_title_register_is_a_human_step(self):
        import landregistry
        out = landregistry.title_help()
        self.assertEqual(out["access"], "manual")
        self.assertIsNone(out["http_status"])
        self.assertEqual(out["cost"]["title_register"], "GBP 7")


if __name__ == "__main__":
    unittest.main()
