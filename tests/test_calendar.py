# -*- coding: utf-8 -*-
"""Offline tests for scripts/calendar.py — the landing calendar and the first-weeks plan.

Everything here reads tests/fixtures/calendar or the two curated reference files.
Nothing touches the network: `fetch` is replaced with a landmine in setUp, so a
test that reaches for it fails loudly instead of going quiet on a plane.

The module is loaded by path, deliberately. It is called calendar.py, and a plain
`import calendar` inside a test process would shadow the standard library module
for every other test in the same run.

Run: python3 -m unittest tests.test_calendar -q
"""
import datetime as dt
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
REFERENCES = os.path.join(ROOT, "skills", "vet-flat", "references")
FIX = os.path.join(HERE, "fixtures", "calendar")
CALC = os.path.join(SCRIPTS, "calc.py")
EVENTS_YAML = os.path.join(REFERENCES, "london-events.yaml")
TERM_DATES_YAML = os.path.join(REFERENCES, "term-dates.yaml")

_spec = importlib.util.spec_from_file_location("vetflat_calendar",
                                               os.path.join(SCRIPTS, "calendar.py"))
cal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cal)

D = dt.date.fromisoformat


def fixture(name):
    with io.open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


class NoNetwork(unittest.TestCase):
    """Every test in this file inherits a fetch() that refuses to be called."""

    def setUp(self):
        self._fetch = cal.fetch

        def landmine(*a, **kw):
            raise AssertionError("a test reached the network: %r" % (a[:1],))

        cal.fetch = landmine

    def tearDown(self):
        cal.fetch = self._fetch


# ------------------------------------------------------------------- yaml ----
class TestMiniYaml(NoNetwork):
    def test_the_two_shipped_files_parse(self):
        events = cal.load_events()
        terms = cal.load_terms()
        self.assertGreaterEqual(len(events["venues"]), 8)
        self.assertGreaterEqual(len(events["spikes"]), 7)
        self.assertGreaterEqual(len(events["areas"]), 30)
        self.assertEqual(len(terms["universities"]), 10)

    def test_scalars_lists_and_nesting(self):
        doc = cal.parse_yaml("version: \"1\"\n"
                             "# a comment\n"
                             "rules:\n"
                             "  a: \"colons: inside a quoted value\"\n"
                             "items:\n"
                             "  - id: one\n"
                             "    lat: 51.5\n"
                             "    on: true\n"
                             "    names: [Alpha Bravo, Charlie]\n"
                             "    empty:\n"
                             "  - id: two\n"
                             "    when: 2026-09-16\n")
        self.assertEqual(doc["version"], "1")
        self.assertEqual(doc["rules"]["a"], "colons: inside a quoted value")
        self.assertEqual(doc["items"][0]["names"], ["Alpha Bravo", "Charlie"])
        self.assertEqual(doc["items"][0]["lat"], 51.5)
        self.assertIs(doc["items"][0]["on"], True)
        self.assertIsNone(doc["items"][0]["empty"])
        self.assertEqual(doc["items"][1]["when"], "2026-09-16")


# --------------------------------------------------------------- holidays ----
class TestHolidays(NoNetwork):
    def test_range_selects_only_the_dates_asked_for(self):
        rows, why = cal.parse_holidays(fixture("bank-holidays.json"),
                                       D("2026-12-01"), D("2027-01-15"))
        self.assertEqual(why, "")
        self.assertEqual([r["date"] for r in rows],
                         ["2026-12-25", "2026-12-28", "2027-01-01"])
        self.assertEqual(rows[0]["weekday"], "Friday")

    def test_division_is_selected_and_a_missing_one_is_an_honest_failure(self):
        ew, _ = cal.parse_holidays(fixture("bank-holidays.json"),
                                   D("2026-01-01"), D("2026-12-31"))
        sc, _ = cal.parse_holidays(fixture("bank-holidays.json"),
                                   D("2026-01-01"), D("2026-12-31"), "scotland")
        self.assertNotIn("2026-01-02", [r["date"] for r in ew])
        self.assertIn("2026-01-02", [r["date"] for r in sc])
        rows, why = cal.parse_holidays(fixture("bank-holidays.json"),
                                       D("2026-01-01"), D("2026-12-31"), "wales-only")
        self.assertIsNone(rows)
        self.assertIn("wales-only", why)

    def test_the_offline_envelope_carries_a_source_and_says_what_a_holiday_costs(self):
        doc = cal.holidays(D("2026-08-25"), D("2026-09-05"), offline=True, fixtures=FIX)
        self.assertTrue(doc["ok"])
        self.assertEqual([h["date"] for h in doc["holidays"]], ["2026-08-31"])
        self.assertIn("bank-holidays.json", doc["source_url"])
        self.assertIn("shut", doc["method"])


# --------------------------------------------------------------- closures ----
class TestClosures(NoNetwork):
    def test_overlap_logic_drops_work_outside_the_window(self):
        obj = fixture("tfl-line-status.json")
        september = cal.parse_closures(obj, D("2026-09-12"), D("2026-09-13"))
        october = cal.parse_closures(obj, D("2026-10-17"), D("2026-10-18"))
        self.assertNotIn("suffragette", [r["line_id"] for r in september])
        self.assertEqual(["suffragette"], [r["line_id"] for r in october])
        self.assertIn("circle", [r["line_id"] for r in september])

    def test_good_service_is_never_a_closure(self):
        rows = cal.parse_closures(fixture("tfl-line-status.json"),
                                  D("2026-09-12"), D("2026-09-13"))
        self.assertTrue(all(r["severity"] != cal.GOOD_SERVICE for r in rows))
        self.assertNotIn("bakerloo", [r["line_id"] for r in rows])

    def test_the_line_filter_is_a_mode_filter(self):
        obj = fixture("tfl-line-status.json")
        tube = cal.parse_closures(obj, D("2026-09-12"), D("2026-09-13"), ["tube"])
        overground = cal.parse_closures(obj, D("2026-10-17"), D("2026-10-18"), ["overground"])
        self.assertEqual({"tube"}, {r["mode"] for r in tube})
        self.assertEqual(["suffragette"], [r["line_id"] for r in overground])
        self.assertEqual([], cal.parse_closures(obj, D("2026-09-12"), D("2026-09-13"), ["dlr"]))

    def test_a_disruption_with_no_dates_is_kept_and_flagged_not_dropped(self):
        obj = [{"id": "mildmay", "name": "Mildmay", "modeName": "overground",
                "lineStatuses": [{"statusSeverity": 6, "statusSeverityDescription": "Severe Delays",
                                  "reason": "a signal failure", "validityPeriods": []}]}]
        rows = cal.parse_closures(obj, D("2026-09-16"), D("2026-09-20"))
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["dated"])
        self.assertIn("no dates", rows[0]["note"])

    def test_the_url_carries_the_modes_and_the_date_range(self):
        url = cal.closures_url(["tube", "dlr"], D("2026-09-16"), D("2026-09-20"))
        self.assertIn("/Line/Mode/tube,dlr/Status", url)
        self.assertIn("startDate=2026-09-16", url)
        self.assertIn("endDate=2026-09-20", url)

    def test_offline_closures_read_the_fixture_and_count_the_planned_work(self):
        doc = cal.closures(D("2026-09-12"), D("2026-09-13"), offline=True, fixtures=FIX)
        self.assertTrue(doc["ok"])
        self.assertGreaterEqual(doc["planned_count"], 2)


# ------------------------------------------------------------ term dates ----
class TestTermDates(NoNetwork):
    @classmethod
    def setUpClass(cls):
        cls.doc = cal.load_terms()

    def test_every_entry_has_a_source_a_check_date_and_either_dates_or_an_estimate(self):
        for u in self.doc["universities"]:
            self.assertTrue(str(u.get("source", "")).startswith("http"),
                            "%s has no source URL" % u.get("id"))
            self.assertRegex(str(u.get("checked_on")), r"^\d{4}-\d{2}-\d{2}$")
            complete = all(u.get(k) for k in ("welcome_from", "welcome_to", "teaching_starts",
                                              "term_start", "term_end"))
            self.assertTrue(complete or u.get("estimated") is True,
                            "%s is missing a date and is not marked estimated" % u.get("id"))
            if u.get("estimated"):
                self.assertGreaterEqual(len(str(u.get("estimate_note") or "").split()), 8,
                                        "%s is estimated with no explanation" % u.get("id"))

    def test_the_ten_london_universities_are_all_there_and_dated_in_2026(self):
        ids = {u["id"] for u in self.doc["universities"]}
        self.assertEqual(ids, {"kcl", "ucl", "lse", "imperial", "qmul", "citystgeorges",
                               "westminster", "goldsmiths", "soas", "birkbeck"})
        for u in self.doc["universities"]:
            self.assertTrue(str(u["teaching_starts"]).startswith("2026-"),
                            "%s does not start teaching in 2026" % u["id"])

    def test_a_stale_reading_is_warned_about_and_a_fresh_one_is_not(self):
        fresh = cal.terms(2026, today=D("2026-10-01"))
        stale = cal.terms(2026, today=D("2028-10-01"))
        self.assertFalse(any("more than the" in w for w in fresh["warnings"]))
        self.assertTrue(any("more than the 300-day limit" in w for w in stale["warnings"]))
        self.assertTrue(all(u["stale"] for u in stale["universities"]))

    def test_the_uni_filter_and_an_id_the_file_does_not_have(self):
        doc = cal.terms(2026, ["kcl", "goldsmiths", "oxford"], today=D("2026-09-06"))
        self.assertEqual([u["id"] for u in doc["universities"]], ["kcl", "goldsmiths"])
        self.assertEqual(doc["not_in_file"], ["oxford"])
        self.assertTrue(any("oxford" in w for w in doc["warnings"]))

    def test_a_year_the_file_does_not_cover_is_unknown_not_invented(self):
        doc = cal.terms(2031, today=D("2026-09-06"))
        self.assertFalse(doc["ok"])
        self.assertIn("unknown, try again", doc["note"])


# ---------------------------------------------------------------- events ----
class TestEventsFile(NoNetwork):
    @classmethod
    def setUpClass(cls):
        cls.doc = cal.load_events()
        with io.open(EVENTS_YAML, encoding="utf-8") as fh:
            cls.text = fh.read()

    def test_no_percentage_is_ever_claimed_in_the_file(self):
        self.assertNotIn("%", self.text,
                         "a per-cent sign in london-events.yaml: we have not measured any uplift")

    def test_every_kind_is_one_of_the_three_and_windows_parse(self):
        for spike in self.doc["spikes"]:
            self.assertIn(spike["kind"], ("structural", "citywide", "venue"))
            self.assertTrue(spike.get("check"), "%s says nothing to check" % spike["id"])
            if spike.get("anchor") != "last_monday_august":
                window = cal._mmdd_window(spike, 2026)
                self.assertIsNotNone(window, "%s has an unparseable window" % spike["id"])
        for venue in self.doc["venues"]:
            self.assertEqual(venue["kind"], "venue")

    def test_every_venue_names_its_own_calendar_and_carries_the_radius_note(self):
        for venue in self.doc["venues"]:
            self.assertEqual(venue["check"], "the venue's own events calendar")
            self.assertTrue(str(venue["calendar"]).startswith("http"))
            self.assertIn("2 km", venue["radius_note"])
            self.assertIsNotNone(venue["lat"])
        self.assertIn("2 km", self.doc["price_radius_note"])

    def test_term_start_is_the_structural_one_and_wimbledon_is_july(self):
        spikes = {s["id"]: s for s in self.doc["spikes"]}
        self.assertEqual(spikes["term_start"]["kind"], "structural")
        self.assertEqual(spikes["wimbledon"]["kind"], "citywide")
        self.assertIn("SW19", spikes["wimbledon"]["affects"])
        july = cal.spike_windows(spikes["wimbledon"], D("2026-09-01"), D("2026-11-01"))
        self.assertEqual(july, [], "Wimbledon must not surface for a September arrival")


class TestEventsCommand(NoNetwork):
    def test_a_late_august_arrival_is_told_about_carnival_on_the_right_weekend(self):
        doc = cal.events(D("2026-08-26"), D("2026-09-30"))
        carnival = [s for s in doc["spikes"] if s["id"] == "notting_hill_carnival"]
        self.assertEqual(len(carnival), 1)
        self.assertEqual(carnival[0]["windows"], [{"from": "2026-08-30", "to": "2026-08-31"}])
        self.assertEqual(carnival[0]["kind"], "citywide")

    def test_deptford_gets_the_o2_and_excel_and_never_twickenham(self):
        doc = cal.events(D("2026-09-16"), D("2026-11-04"), near=["Deptford"])
        near = [v["name"] for v in doc["venues_to_check"]]
        far = [v["name"] for v in doc["venues_too_far"]]
        self.assertIn("The O2", near)
        self.assertIn("ExCeL London", near)
        self.assertTrue(any("Twickenham" in name for name in far))
        self.assertFalse(any("Twickenham" in name for name in near))
        self.assertEqual(doc["areas_resolved"], ["SE8"])

    def test_an_area_it_cannot_place_is_said_out_loud(self):
        doc = cal.events(D("2026-09-16"), D("2026-11-04"), near=["Narnia"])
        self.assertEqual(doc["areas_not_recognised"], ["Narnia"])
        self.assertIn("I do not know where", doc["note"])

    def test_a_pasted_calendar_page_is_scanned_and_never_fetched(self):
        doc = cal.events(D("2026-09-16"), D("2026-11-04"),
                         paste=os.path.join(FIX, "events-paste.txt"))
        dates = [h["date"] for h in doc["paste"]["dates_in_window"]]
        self.assertIn("2026-09-24", dates)
        self.assertIn("2026-10-17", dates)
        self.assertNotIn("2026-09-12", dates)   # before the window
        self.assertNotIn("2027-02-14", dates)   # after it
        self.assertIn("nothing was crawled", doc["paste"]["method"])


# ------------------------------------------------------------------ plan ----
class TestPlan(NoNetwork):
    def setUp(self):
        NoNetwork.setUp(self)
        self.doc = cal.plan(D("2026-09-16"), D("2026-10-01"), areas=["Deptford", "Lewisham"],
                            budget_all_in=1900.0, bridge_weekly=550.0,
                            offline=True, fixtures=FIX, today=D("2026-09-06"))

    def test_the_bridge_is_booked_before_anything_else_is_looked_at(self):
        self.assertEqual(self.doc["rules"][0]["rule"], "Book the bridge first")
        for row in self.doc["weeks"][:2]:
            self.assertEqual(row["sleep"]["tier"], "hotel or operator-run serviced stay")
            self.assertTrue(row["sleep"]["booked_before_you_fly"])
        first = " ".join(self.doc["weeks"][0]["do"])
        self.assertIn("Sleep where you booked before you flew", first)
        self.assertIn("Do not pay anything for a long let", first)

    def test_a_september_arrival_is_told_about_term_start_and_fashion_week(self):
        flags = [hit["what"] for row in self.doc["weeks"] for hit in row["overlaps"]]
        blob = " | ".join(flags)
        self.assertIn("term start", blob)
        self.assertIn("London Fashion Week", blob)
        kinds = {hit["kind"] for row in self.doc["weeks"] for hit in row["overlaps"]}
        self.assertIn("structural", kinds)
        self.assertIn("citywide", kinds)

    def test_the_default_gap_is_four_to_seven_weeks_with_the_forty_five_day_case(self):
        self.assertEqual(self.doc["gap"]["default_band_weeks"], [4, 7])
        self.assertEqual(self.doc["gap"]["days"], 49)
        self.assertEqual(self.doc["gap"]["keys_date"], "2026-11-04")
        self.assertIn("four to seven weeks", self.doc["gap"]["basis"])
        self.assertEqual(self.doc["gap"]["reference_case_days"], 45)
        self.assertIn("45 days", self.doc["rules"][1]["says"])

    def test_the_bridging_total_is_calc_pys_answer_and_not_a_second_implementation(self):
        weeks = self.doc["gap"]["weeks"]
        months = self.doc["assumptions"]["months_after_bridge"]
        out = subprocess.run([sys.executable, CALC, "bridge", "--weeks", str(weeks),
                              "--weekly", "550.0", "--months", str(months), "--all-in", "1900.0"],
                             capture_output=True, text=True, check=True)
        expected = json.loads(out.stdout)["result"]
        self.assertTrue(self.doc["bridging_total"]["ok"])
        self.assertEqual(self.doc["bridging_total"]["result"]["total"], expected["total"])
        self.assertEqual(self.doc["bridging_total"]["result"]["bridge_cost"],
                         expected["bridge_cost"])
        self.assertIn("not an add-on to rent", self.doc["bridging_total"]["formula"])

    def test_the_areas_choose_the_venues_and_the_closure_feed(self):
        near = [v["name"] for v in self.doc["venues_to_check"]]
        self.assertIn("The O2", near)
        self.assertIn("ExCeL London", near)
        self.assertFalse(any("Twickenham" in name for name in near))
        self.assertEqual(self.doc["areas"]["resolved"], ["SE8", "SE13"])
        self.assertEqual(sorted(self.doc["closures_query"]["modes"]),
                         ["dlr", "national-rail", "overground"])

    def test_no_percentage_uplift_is_ever_claimed_in_the_output(self):
        blob = json.dumps(self.doc, ensure_ascii=False)
        self.assertIn("magnitude not measured here", blob)
        self.assertNotIn("per cent", blob)
        self.assertFalse(re.search(r"\d\s?(?:%|per ?cent)", blob),
                         "the plan quoted a percentage uplift")

    def test_keys_before_the_start_date_still_puts_the_first_nights_in_a_hotel(self):
        doc = cal.plan(D("2026-09-16"), D("2026-10-01"), keys_by=D("2026-09-25"),
                       offline=True, fixtures=FIX, today=D("2026-09-06"))
        self.assertEqual(doc["gap"]["days"], 9)
        self.assertEqual(doc["weeks"][0]["sleep"]["tier"], "hotel or operator-run serviced stay")
        self.assertTrue(doc["weeks"][0]["sleep"]["booked_before_you_fly"])
        self.assertIn("you gave me the key date", doc["gap"]["basis"])

    def test_gap_weeks_moves_the_key_date_and_says_so(self):
        doc = cal.plan(D("2026-09-16"), D("2026-10-01"), gap_weeks=5,
                       offline=True, fixtures=FIX, today=D("2026-09-06"))
        self.assertEqual(doc["gap"]["keys_date"], "2026-10-21")
        self.assertEqual(len(doc["weeks"]), 5)
        self.assertIn("you gave me a gap of 5 weeks", doc["gap"]["basis"])

    def test_without_the_two_numbers_the_total_is_unknown_not_guessed(self):
        doc = cal.plan(D("2026-09-16"), D("2026-10-01"), offline=True, fixtures=FIX,
                       today=D("2026-09-06"))
        self.assertFalse(doc["bridging_total"]["ok"])
        self.assertIn("unknown, try again", doc["bridging_total"]["note"])
        self.assertIn("--bridge-weekly", doc["bridging_total"]["note"])

    def test_an_unplaceable_area_widens_the_feed_and_says_it_did(self):
        doc = cal.plan(D("2026-09-16"), D("2026-10-01"), areas=["Narnia"],
                       offline=True, fixtures=FIX, today=D("2026-09-06"))
        self.assertEqual(doc["areas"]["not_recognised"], ["Narnia"])
        self.assertEqual(doc["closures_query"]["modes"], list(cal.RAIL_MODES))
        self.assertTrue(any("could not place" in w for w in doc["warnings"]))


class TestPlainOutput(NoNetwork):
    NUMBERED = re.compile(r"^\s*\d+\.\s")

    def numbered(self, text):
        return [ln for ln in text.split("\n") if self.NUMBERED.match(ln)]

    def assert_every_numbered_line_is_sourced(self, text):
        lines = self.numbered(text)
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertIn("[source: ", line, "unsourced line: %s" % line[:90])
            self.assertRegex(line, r"as_of \d{4}-\d{2}-\d{2}\]",
                             "no as_of date on: %s" % line[:90])

    def test_the_plan_table_sources_and_dates_every_numbered_line(self):
        doc = cal.plan(D("2026-09-16"), D("2026-10-01"), areas=["Deptford"],
                       budget_all_in=1900.0, bridge_weekly=550.0,
                       offline=True, fixtures=FIX, today=D("2026-09-06"))
        text = cal.plain(doc)
        self.assert_every_numbered_line_is_sourced(text)
        self.assertIn("Book the bridge first", text)
        self.assertIn("45 days", text)

    def test_the_other_four_tables_source_and_date_their_lines_too(self):
        for doc in (cal.holidays(D("2026-12-01"), D("2027-01-15"), offline=True, fixtures=FIX),
                    cal.closures(D("2026-09-12"), D("2026-09-13"), offline=True, fixtures=FIX),
                    cal.terms(2026, today=D("2026-09-06")),
                    cal.events(D("2026-08-26"), D("2026-09-30"), near=["Deptford"])):
            self.assert_every_numbered_line_is_sourced(cal.plain(doc))


class TestItDoesNotShadowTheStandardLibrary(unittest.TestCase):
    """This file is called calendar.py, so `import calendar` in any process with the
    scripts directory on sys.path finds it — including the lazy import inside
    datetime.strptime and email.utils. It has to carry the standard library's surface."""

    def test_the_stdlib_surface_survives_the_name_clash(self):
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys, datetime\n"
             "sys.path.insert(0, %r)\n" % SCRIPTS +
             "import calendar\n"
             "assert calendar.__file__.endswith('scripts/calendar.py'), calendar.__file__\n"
             "assert list(calendar.day_abbr)[0] == 'Mon'\n"
             "assert calendar.monthrange(2026, 2) == (6, 28)\n"
             "assert datetime.datetime.strptime('2026-09-16T08:30', '%Y-%m-%dT%H:%M').hour == 8\n"
             "import email.utils; email.utils.formatdate(0)\n"
             "assert hasattr(calendar, 'parse_closures') and hasattr(calendar, 'plan')\n"
             "print('ok')"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr[-600:])
        self.assertIn("ok", out.stdout)

    def test_calc_py_no_longer_needs_the_stdlib_module_of_that_name(self):
        out = subprocess.run([sys.executable, CALC, "pro-rata", "--rent-pcm", "2400",
                              "--move-in", "2024-02-10"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr[-400:])
        self.assertEqual(json.loads(out.stdout)["result"]["days_in_month"], 29)


class TestCli(unittest.TestCase):
    """The command line itself, in a subprocess, offline. No fetch is possible."""

    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "calendar.py")] + list(args),
                              capture_output=True, text=True)

    def test_offline_plan_prints_one_json_object_and_exits_zero(self):
        out = self.run_cli("--offline", "--today", "2026-09-06", "plan",
                           "--arrive", "2026-09-16", "--start", "2026-10-01",
                           "--areas", "Deptford, Lewisham",
                           "--budget-all-in", "1900", "--bridge-weekly", "550")
        self.assertEqual(out.returncode, 0, out.stderr[:400])
        doc = json.loads(out.stdout)
        self.assertEqual(doc["command"], "plan")
        self.assertEqual(len(doc["weeks"]), 7)

    def test_two_ways_of_saying_the_same_thing_is_a_usage_error(self):
        out = self.run_cli("plan", "--arrive", "2026-09-16", "--start", "2026-10-01",
                           "--keys-by", "2026-11-01", "--gap-weeks", "6")
        self.assertEqual(out.returncode, 2)
        self.assertIn("not both", out.stderr)

    def test_keys_before_arrival_is_a_usage_error_not_a_negative_bridge(self):
        out = self.run_cli("plan", "--arrive", "2026-09-16", "--start", "2026-10-01",
                           "--keys-by", "2026-09-10")
        self.assertEqual(out.returncode, 2)
        self.assertIn("no bridge to plan", out.stderr)


if __name__ == "__main__":
    unittest.main()
