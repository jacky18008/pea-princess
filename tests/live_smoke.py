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
import json
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


# ----------------------------------------------------------- planning.py ----
@unittest.skipUnless(LIVE, WHY)
class LivePlanning(unittest.TestCase):
    """GLA Planning London Datahub - 4 calls (3 Elasticsearch, 1 PlanIt fallback)."""

    def test_near_returns_sorted_neighbours_with_a_portal_url(self):
        import planning
        out = planning.near(LAT, LNG, radius=250, since=2018, limit=50)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["http_status"], 200)
        self.assertEqual(out["evidence_class"], "G")
        self.assertEqual(out["geo_filter"], "geo_distance on centroid (geo_point)")
        self.assertGreater(out["count"], 0)
        # track_total_hits must defeat the 10000 cap, so the count is exact
        self.assertGreater(out["total_matching"], 0)
        d = [r["distance_m"] for r in out["results"]]
        self.assertEqual(d, sorted(d))
        self.assertTrue(all(x <= 250 for x in d))
        first = out["results"][0]
        self.assertTrue(first["reference"])
        self.assertEqual(first["lpa_name"], "Southwark")
        self.assertTrue(first["portal_url"].startswith("https://"))
        self.assertIn(first["tall_building_hint"], (True, False))
        self.assertIn("zero hits is not proof", out["caveat"])

    def test_stages_explains_the_status_and_points_at_the_portal(self):
        import planning
        out = planning.stages("26/AP/0812", "Southwark")
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["record"]["reference"], "26/AP/0812")
        self.assertTrue(out["what_this_means"])
        self.assertTrue(any("permission granted" in x for x in out["what_this_means"]))
        self.assertIn("planning.southwark.gov.uk", out["conditions"]["portal_url"])
        self.assertIn(out["conditions"]["in_api"], (True, False))

    def test_a_site_name_the_developer_never_filed_returns_a_real_zero(self):
        import planning
        out = planning.search("Emery Wharf", limit=5)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["count"], 0)
        self.assertEqual(out["total_matching"], 0)
        self.assertIn("not_found", out)
        self.assertIn("Try the street name", out["not_found"]["meaning"])

    def test_planit_fallback_still_answers_on_pcode_and_krad(self):
        import planning
        out = planning.planit("SE1 9SG", km=0.2, limit=5)
        self.assertTrue(out["ok"], out["note"])
        self.assertEqual(out["evidence_class"], "C")
        self.assertIn("robots", out)
        self.assertGreater(out["count"], 0)
        self.assertTrue(out["results"][0]["reference"])


# -------------------------------------------------------------- roads.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveRoads(unittest.TestCase):
    """Overpass - 1 call. The facade check reuses that same answer."""

    @classmethod
    def setUpClass(cls):
        import roads
        cls.roads = roads
        cls.out = roads.near(LAT, LNG, radius=300)

    def test_overpass_answers_a_tool_user_agent(self):
        self.assertTrue(self.out["ok"], self.out["note"])
        self.assertEqual(self.out["http_status"], 200)
        self.assertIn(self.out["overpass_instance"], self.roads.INSTANCES)
        self.assertNotEqual(self.out["http_status"], 406)   # 406 = browser UA sent
        self.assertGreater(self.out["element_count"], 0)
        self.assertIn("out geom;", self.out["query_used"])

    def test_the_categories_look_like_central_london(self):
        self.assertLessEqual(self.out["trunk_or_primary_road"]["nearest"]["distance_m"], 300)
        self.assertGreater(self.out["railway_surface"]["count"], 0)
        self.assertIsNotNone(self.out["supermarket"]["nearest"]["walk_minutes_street_estimate"])
        self.assertEqual(self.out["helipad_or_aerodrome"]["count"], 0)
        self.assertEqual(self.out["night_economy"]["search_radius_m"], 100)

    def test_distances_are_ints_or_null_never_zero_as_a_stand_in(self):
        for key, val in self.out.items():
            if isinstance(val, dict) and "nearest" in val:
                near_ = val["nearest"]
                if near_ is None:
                    self.assertEqual(val["count"], 0, key)
                else:
                    self.assertIsInstance(near_["distance_m"], int, key)

    def test_obstruction_angles_are_derivable(self):
        for r in self.out["obstruction_candidates"]["worst_first"]:
            if r["height_m_estimate"]:
                self.assertIsNotNone(r["obstruction_angle_deg"])
                self.assertLessEqual(r["obstruction_angle_deg"], 90)

    def test_facade_note_reuses_the_same_query(self):
        out = self.roads.facade_note(LAT, LNG, 300, full=self.out)
        self.assertEqual(out["query_used"], self.out["query_used"])
        self.assertEqual(out["facade_note_trigger_m"], 60)


# -------------------------------------------------------------- sweep.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveSweep(unittest.TestCase):
    """The whole orchestrator, end to end, on a 300 m circle - about 90 calls.

    The caps are deliberate: a bare 300 m sweep in central London is 40 street
    searches and 200 certificate pages. This asserts the pipeline, not the area, so
    it searches four streets, samples three certificates per building and takes two
    buildings through the fact run. Everything is cached, so a re-run is nearly free.
    """

    @classmethod
    def setUpClass(cls):
        import subprocess
        import tempfile
        cls.out = tempfile.mkdtemp(prefix="vetflat-sweep-")
        cmd = [sys.executable, os.path.join(HERE, "..", "skills", "vet-flat", "scripts",
                                            "sweep.py"),
               "--anchor", POSTCODE, "--radius", "300", "--dest", "WC2R 2LS",
               "--out", cls.out, "--max-buildings", "2",
               "--max-streets", "4", "--max-filter-buildings", "3",
               "--certs-per-building", "3", "--crime-months", "2",
               "--max-postcode-lookups", "20"]
        cls.proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        cls.result = json.loads(cls.proc.stdout) if cls.proc.stdout.strip().startswith("{") \
            else None

    def _read(self, name):
        with open(os.path.join(self.out, name), encoding="utf-8") as fh:
            return json.load(fh) if name.endswith(".json") else fh.read()

    def test_the_run_finishes_and_reports_its_own_coverage(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])
        self.assertIsNotNone(self.result, self.proc.stdout[:400])
        self.assertTrue(self.result["ok"])
        cov = self.result["coverage"]
        self.assertGreater(cov["streets_found"], 0)
        self.assertEqual(cov["streets_searched"], 4)
        self.assertGreater(cov["certificates_seen"], 0)
        self.assertGreater(cov["buildings"], 0)
        self.assertGreater(cov["fetches"], 0)

    def test_every_stage_wrote_its_file(self):
        for name in ("anchor.json", "buildings.json", "filtered.json", "summary.json",
                     "summary.md", "report-skeleton.json", "manifest.json",
                     "ask-the-user.md"):
            self.assertTrue(os.path.exists(os.path.join(self.out, name)), name)

    def test_the_manifest_records_every_fetch_including_the_failures(self):
        man = self._read("manifest.json")
        self.assertEqual(len(man["fetches"]), man["summary"]["fetches"])
        for row in man["fetches"]:
            for field in ("url", "status", "ok", "note", "retrieved_at", "stage"):
                self.assertIn(field, row)
        self.assertEqual(len([r for r in man["fetches"] if not r["ok"]]),
                         man["summary"]["failures"])

    def test_each_candidate_is_under_the_four_kilobyte_cap(self):
        import glob
        files = sorted(glob.glob(os.path.join(self.out, "candidates", "*.json")))
        self.assertTrue(files, "no candidate was written")
        self.assertLessEqual(len(files), 2)
        for path in files:
            self.assertLessEqual(os.path.getsize(path), 4096, os.path.basename(path))
            with open(path, encoding="utf-8") as fh:
                rec = json.load(fh)
            self.assertTrue(rec["display_address"])
            self.assertIn("metrics", rec)
            for block in ("epc", "crime", "commute"):
                if block in rec:
                    self.assertIn("source_url", rec[block], block)
                    self.assertIn("retrieved_at", rec[block], block)
                    self.assertIn("evidence_class", rec[block], block)

    def test_the_ask_file_names_sites_and_carries_no_search_urls(self):
        text = self._read("ask-the-user.md")
        self.assertIn("HomeViews", text)
        self.assertIn("Rightmove", text)
        # site names only: a review or portal URL with a search in it must never
        # appear, because the user has to open the site under their own terms
        self.assertNotIn("http", text)

    def test_the_dry_run_stops_before_the_expensive_stages(self):
        import subprocess
        import tempfile
        out = tempfile.mkdtemp(prefix="vetflat-dry-")
        cmd = [sys.executable, os.path.join(HERE, "..", "skills", "vet-flat", "scripts",
                                            "sweep.py"),
               "--anchor", POSTCODE, "--radius", "300", "--dest", "WC2R 2LS",
               "--out", out, "--dry-run"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        plan = json.loads(proc.stdout)
        self.assertTrue(plan["dry_run"])
        self.assertGreater(plan["streets_found"], 0)
        self.assertIn("grand_total_excluding_postcodes", plan["estimated_fetches"])
        self.assertFalse(os.path.exists(os.path.join(out, "buildings.json")))


# --------------------------------------------------------- streetview.py ----
@unittest.skipUnless(LIVE, WHY)
class LiveStreetView(unittest.TestCase):
    """Only the FREE calls run live. `fetch` is deliberately never exercised
    here: every image is a billable call on somebody's own Google account, and a
    test suite is not allowed to spend the user's money. The paid path is
    covered offline in tests/test_streetview.py with a stubbed downloader."""

    def setUp(self):
        import streetview
        self.sv = streetview

    def test_metadata_is_free_and_dated_or_says_it_has_no_key(self):
        out = self.sv.check(LAT, LNG)
        if out.get("access") == "manual":            # no key on this machine: still a pass
            self.assertIn("GOOGLE_MAPS_KEY", out["note"])
            self.assertTrue(out["how_to_get_a_key"])
            self.assertIn("key=REDACTED", out["source_url"])
            return
        self.assertTrue(out["ok"], out["note"])
        self.assertIn(out["status"], ("OK", "ZERO_RESULTS"))
        self.assertNotIn("key=", out["source_url"].replace("key=REDACTED", ""))
        if out["status"] == "OK":
            self.assertTrue(out["pano_id"])
            self.assertRegex(out["date"] or "", r"^\d{4}(-\d{2})?$")
            self.assertIsNotNone(out["location"])
            self.assertLessEqual(out["camera_distance_m"], 60)

    def test_fetch_refuses_without_a_key_and_writes_nothing(self):
        import shutil
        import tempfile
        if self.sv.google_key():
            self.skipTest("a key is present; the refusal path is tested offline")
        tmp = tempfile.mkdtemp(prefix="vetflat-sv-")
        target = os.path.join(tmp, "sv")
        try:
            man, code = self.sv.fetch_images(LAT, LNG, target)
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(target))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mapillary_answers_or_says_it_has_no_token(self):
        out = self.sv.mapillary(LAT, LNG, radius=60, limit=5)
        self.assertEqual(out["licence"], "CC BY-SA 4.0")
        if out.get("access") == "manual":
            self.assertIn("MAPILLARY_TOKEN", out["note"])
            return
        self.assertTrue(out["ok"], out["note"])
        self.assertLess(out["bbox"]["north"] - out["bbox"]["south"], 0.01)
        for im in out["images"]:
            self.assertTrue(im["id"])
            self.assertLessEqual(im["distance_m"], 400)
            self.assertIn("mapillary.com", im["page_url"])
        if not out["images"]:
            self.assertIn("not_found", out)

    def test_brief_needs_no_network_at_all(self):
        b = self.sv.brief()
        self.assertTrue(b["ok"])
        self.assertEqual(b["evidence_class"], "C")
        self.assertEqual(len(b["routes"]), 3)
        self.assertIn("ethnicity", b["text"].lower())


if __name__ == "__main__":
    unittest.main()
