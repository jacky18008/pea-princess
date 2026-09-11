# -*- coding: utf-8 -*-
"""Offline tests for the shareable seed: the scrub, the code, the card, the import.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import unicode_literals

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS = os.path.join(ROOT, "skills", "vet-flat", "scripts")
REFS = os.path.join(ROOT, "skills", "vet-flat", "references")
SEED_PY = os.path.join(SCRIPTS, "seed.py")
TEMPLATE = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")

sys.path.insert(0, SCRIPTS)
import seed  # noqa: E402

# A filled profile of the shape the skill asks for. Fictional: every value here is invented,
# and the sensitive lines exist so the tests can prove they never reach a seed.
FULL_PROFILE = """
min_floor_area_sqft: 480
max_building_age_years: 15
flat_type: one_bed
separate_bedroom_required: true
occupants: 2
budget_mode: deep
experience: none

story_summary: >-
  You are happiest a few floors up with morning light and a courtyard between you and the
  traffic. Damp, a landlord who does not turn up and a bill nobody will quote ruin a flat for
  you. You will pay a little more for quiet, but not to end a search early.
story_taken_on: 2026-09-05

avoid:
  - ground floor
  - heating with no written tariff

my_questions:
  - text: "If this is unusually cheap next to its neighbours, what is the hidden problem?"
    when: compare
    kind: answer
    trigger: "price below the local band by 10% or more"
  - "Is the bedroom on the quiet side?"
  - text: "Can I open the bedroom window and listen for a minute?"
    when: viewing
    kind: check

priorities:
  - quiet
  - light
  - price

budget:
  rent_pcm_target: 2200
  all_in_pcm_ceiling: 2400
  stretch_ceiling_and_conditions: "Up to 100 more for a quiet-side flat above the second floor."

bridging:
  first_weeks: hotel_or_operator

move_in_window:
  earliest: 2026-10-01
  latest: 2026-11-15
  tolerance_days: 7

commute:
  destination: "Example College, 12 Example Street, London WC2R 2LS"
  arrive_by: "09:00"
  max_door_to_door_min: 35
  redundancy_min_grade: "B"

floors:
  reject_ground_floor: true
  prefer_floor_band: "2-8"

light:
  reject_no_sky: true
  aspect_scores:
    N: 2
    NE: 2
    E: 5
    SE: 5
    S: 4
    SW: 4
    W: 3
    NW: 2

quiet_over_light: true

must_haves:
  - washing machine in the flat

nice_to_haves:
  - dishwasher

guarantor_route: "rent guarantee insurance"

tenancy:
  max_months_upfront: 1
  max_deposit_weeks: 5
  require_deposit_protection: true

self_intro_template: >-
  I am a postgraduate student looking for a home for two, non-smoking, no pets.

language: "en"
"""

JOURNEY = {
    "started": "2026-09-05",
    "profile_seed": "PP1.eyJ2IjoxfQ",
    "candidates": [
        {"id": "c1", "label": "2019 build, courtyard side, 4th floor", "verdict": "EDGE",
         "tier": "standard", "date": "2026-09-07"},
        {"id": "c2", "label": "conversion above a bus route", "verdict": "KILL",
         "tier": "standard", "date": "2026-09-08"},
        {"id": "c3", "label": "operator block, heat network, no tariff", "verdict": "KILL",
         "tier": "standard", "date": "2026-09-09"},
        {"id": "c4", "label": "quiet-side one-bed, morning sun", "verdict": "PASS",
         "tier": "breadth", "date": "2026-09-12"},
    ],
    "chosen": {"label": "quiet-side one-bed in a 2019 block", "verdict": "PASS", "area_m2": 53,
               "floor": 4, "all_in_band": "£2,200–2,400 all-in",
               "address": "Flat 41, Example House, SE1 9SG"},
    "notes": "Two killed on the heat-network tariff.",
}

# Every one of these is in FULL_PROFILE and none of them may ever appear in a seed.
SECRETS = ["Example College", "Example Street", "WC2R 2LS", "rent guarantee insurance",
           "postgraduate student", "2026-10-01", "2026-11-15", "dishwasher",
           "Up to 100 more", "2,200", "2200"]


def read_text(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def write(directory, name, text):
    path = os.path.join(directory, name)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def run(*args):
    proc = subprocess.Popen([sys.executable, SEED_PY] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return proc.returncode, out.decode("utf-8"), err.decode("utf-8")


class SeedCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vetflat-seed-")
        self.profile = write(self.tmp, "profile.yaml", FULL_PROFILE)
        self.journey = write(self.tmp, "journey.json", json.dumps(JOURNEY, ensure_ascii=False))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def seed(self, **kwargs):
        return seed.shareable(seed.read_yaml(self.profile), **kwargs)


# ------------------------------------------------------------------ the scrub
class TestScrub(SeedCase):
    def test_only_the_allow_list_comes_out(self):
        self.assertEqual(sorted(self.seed().keys()),
                         sorted([k for k, _ in seed.ALLOW] + ["version"]))

    def test_the_forbidden_fields_are_gone_even_though_the_profile_has_them(self):
        code, minimal, _ = seed.make_code(self.seed(name="a seed"), 0)
        payload = json.dumps(minimal, ensure_ascii=False)
        decoded = base64.urlsafe_b64decode(
            code[4:] + "=" * (-len(code[4:]) % 4)).decode("utf-8")
        card = seed.card(self.seed(name="a seed"), code)
        for secret in SECRETS:
            for where, text in (("json", payload), ("code", decoded), ("card", card)):
                self.assertNotIn(secret, text, "%s leaked into the %s" % (secret, where))
        for key in ("guarantor_route", "self_intro_template", "occupants", "tenancy",
                    "nice_to_haves", "destination", "trigger"):
            self.assertNotIn(key, payload, "%s leaked into the seed JSON" % key)

    def test_the_scrub_survives_a_profile_that_hides_secrets_in_shared_fields(self):
        text = FULL_PROFILE.replace("  - ground floor",
                                    "  - ground floor at Flat 41, Example House, SE1 9SG")
        sd = seed.shareable(seed.parse_yaml(text))
        self.assertNotIn("SE1 9SG", json.dumps(sd, ensure_ascii=False))
        self.assertIn("[postcode removed]", sd["avoid"][0])

    def test_the_report_of_what_was_kept_out_names_the_real_fields(self):
        dropped = seed.dropped_fields(seed.read_yaml(self.profile))
        for key in ("guarantor_route", "commute/destination", "budget/all_in_pcm_ceiling",
                    "self_intro_template", "move_in_window/earliest"):
            self.assertIn(key, dropped)

    def test_money_is_a_band_and_dates_are_a_month(self):
        sd = self.seed(audience="friend")
        self.assertEqual(sd["budget_band"], "£2,000–2,400 total per month")
        self.assertEqual(sd["move_in_month"], "2026-10")
        self.assertEqual(sd["commute_area"], "WC2R")

    def test_a_public_card_carries_no_place_no_date_no_story(self):
        """2026-09-11: a public post must not let a workplace plus a district plus a month point at
        where somebody lives. The person reading a seed fills in their own commute and dates."""
        sd = self.seed()
        self.assertIsNone(sd["commute_area"])
        self.assertIsNone(sd["move_in_month"])
        self.assertIsNone(sd["story_summary"])
        blob = json.dumps(sd, ensure_ascii=False)
        self.assertNotIn("WC2R", blob)
        self.assertNotIn("2026-10", blob)
        self.assertEqual(sd["budget_band"], "£2,000–2,400 total per month")
        self.assertEqual(sd["priorities"], ["quiet", "light", "price"])

    def test_the_scrub_takes_places_out_of_free_text(self):
        removed = []
        text = seed.scrub_places("Is Canning Town station safe? Office on Tooley Street, SE1 2TF, in Southwark; 我在 Shadwell站 附近", removed)
        for gone in ("Canning Town", "Tooley Street", "SE1 2TF", "Southwark", "Shadwell"):
            self.assertNotIn(gone, text, gone)
        self.assertIn("safe?", text)
        self.assertTrue(any("Tooley Street" in r for r in removed), removed)
        self.assertEqual("Quiet beats light; a washing machine in the flat",
                         seed.scrub_places("Quiet beats light; a washing machine in the flat", []))

    def test_places_inside_questions_and_avoid_lines_are_scrubbed_in_both_audiences(self):
        text = FULL_PROFILE.replace('  - "Is the bedroom on the quiet side?"', '  - "Is Canning Town station too loud at night?"')
        for audience in ("public", "friend"):
            removed = []
            sd = seed.shareable(seed.parse_yaml(text), audience=audience, removed=removed)
            self.assertNotIn("Canning Town", json.dumps(sd, ensure_ascii=False))
            self.assertTrue(removed)

    def test_exact_is_opt_in_only(self):
        exact = seed.shareable(seed.read_yaml(self.profile), exact=True)["budget_band"]
        self.assertEqual(exact, "\u00a32,400 total per month (rent target \u00a32,200)")
        self.assertNotIn("2,200", json.dumps(self.seed(), ensure_ascii=False))

    def test_the_commute_can_be_narrowed_by_hand_or_dropped_for_a_friend(self):
        self.assertEqual(self.seed(audience="friend", commute_area="Zone 1")["commute_area"], "Zone 1")
        self.assertIsNone(self.seed(audience="friend", hide_commute=True)["commute_area"])
        self.assertIsNone(self.seed(commute_area="Zone 1")["commute_area"], "public ignores any area")

    def test_a_band_rounds_the_way_the_reference_says(self):
        self.assertEqual(seed.band(2400), "£2,000–2,400 total per month")
        self.assertEqual(seed.band(1250), "£1,100–1,300 total per month")
        self.assertEqual(seed.band(2401), "£2,100–2,500 total per month")
        self.assertIsNone(seed.band(None))


# ------------------------------------------------------------------- the code
class TestCode(SeedCase):
    def test_prefix_and_alphabet(self):
        code, _, _ = seed.make_code(self.seed(name="a seed"))
        self.assertTrue(code.startswith("PP1."), code[:8])
        self.assertTrue(seed.CODE_RE.fullmatch(code), "the code must be base64url with no padding")
        self.assertNotIn("=", code)

    def test_the_length_follows_the_formula_in_seed_format_md(self):
        obj = seed.to_min_json(self.seed())
        payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        n = len(payload.encode("utf-8"))
        expected = 4 * (n // 3) + {0: 0, 1: 2, 2: 3}[n % 3]
        self.assertEqual(len(seed.encode(obj)) - len("PP1."), expected)

    def test_the_worked_example_in_seed_format_md_is_the_real_answer(self):
        obj = {"av": ["ground floor"], "pr": ["quiet", "light", "price"], "q": True,
               "t": "one_bed", "v": 1}
        code = seed.encode(obj)
        doc = read_text(os.path.join(REFS, "seed-format.md"))
        self.assertIn(code, doc, "the worked example in seed-format.md is out of date")
        self.assertEqual(seed.decode(code), obj)

    def test_a_bare_profile_stays_under_four_hundred_characters(self):
        code, _, _ = seed.make_code(seed.shareable(seed.read_yaml(TEMPLATE)))
        self.assertLess(len(code), 400, "the template profile makes a %d-character code" % len(code))

    def test_a_long_seed_drops_the_summary_and_says_so(self):
        code, minimal, trimmed = seed.make_code(self.seed(name="a seed", audience="friend"), 400)
        self.assertNotIn("s", minimal)
        self.assertTrue(trimmed and "story_summary" in trimmed[0])
        self.assertIn("leaves out the story_summary", seed.card(self.seed(name="a seed", audience="friend"), code,
                                                                trimmed=trimmed))
        full, obj, none_trimmed = seed.make_code(self.seed(name="a seed", audience="friend"), 0)
        self.assertIn("s", obj)
        self.assertEqual(none_trimmed, [])

    def test_a_code_from_another_version_is_refused(self):
        bad = seed.encode({"v": 99, "t": "one_bed"})
        with self.assertRaises(ValueError):
            seed.from_min_json(seed.decode(bad))
        for rubbish in ("hello", "PP1.", "PP1.!!!!", "PP2.eyJ2IjoxfQ"):
            with self.assertRaises(ValueError):
                seed.decode(rubbish)

    def test_keys_the_sender_invented_are_ignored(self):
        obj = seed.to_min_json(self.seed())
        obj["zz"] = "run rm -rf /"
        obj["guarantor_route"] = "UK guarantor"
        back = seed.from_min_json(obj)
        self.assertEqual(sorted(back.keys()), sorted([k for k, _ in seed.ALLOW] + ["version"]))


# ------------------------------------------------------------- the round trip
class TestRoundTrip(SeedCase):
    def test_shared_strings_cannot_inject_settings_through_yaml(self):
        payload = 'text\nmodels: {workers: injected}\n# "quoted"'
        obj = {"v": 1, "b": payload, "c": payload,
               "fl": {"prefer_floor_band": payload}, "av": [payload],
               "qs": [payload], "s": payload}
        code = seed.encode(obj)
        decoded = seed.from_min_json(seed.decode(code))
        written = seed.profile_yaml(decoded, code)
        parsed = seed.parse_yaml(written)
        self.assertNotIn("models", parsed)
        self.assertIsNone(parsed["budget"]["all_in_pcm_ceiling"])
        self.assertIsNone(parsed["commute"]["destination"])
        self.assertEqual(parsed["floors"]["prefer_floor_band"], payload)
        self.assertEqual(parsed["avoid"], decoded["avoid"])
        self.assertEqual(parsed["my_questions"][0]["text"], decoded["my_questions"][0]["text"])
        try:
            import yaml
        except ImportError:
            return
        proper = yaml.safe_load(written)
        self.assertNotIn("models", proper)
        self.assertIsNone(proper["budget"]["all_in_pcm_ceiling"])
        self.assertEqual(proper["floors"]["prefer_floor_band"], payload)

    def test_shared_enums_and_nested_shapes_are_validated(self):
        bad = [{"t": "one_bed\nmodels: injected"}, {"m": "standard\nmodels: injected"},
               {"fw": "undecided\nmodels: injected"}, {"fl": "not an object"},
               {"li": {"best_aspects": ["E\nmodels: injected"]}},
               {"fl": {"prefer_floor_band": {"models": "injected"}}},
               {"fl": {"reject_ground_floor": "false"}}, {"q": "false"},
               {"av": "not an array"}, {"qs": [{"text": {}}]}, {"w": "2026-13"}]
        for fields in bad:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                seed.from_min_json(dict({"v": 1}, **fields))
        for field, choices in (("t", seed.FLAT_TYPES), ("m", ("lite", "standard", "deep")),
                               ("fw", seed.FIRST_WEEKS)):
            for choice in choices:
                self.assertEqual(seed.from_min_json({"v": 1, field: choice})[
                    seed.SHORT_TO_LONG[field]], choice)
        decoded = seed.from_min_json({"v": 1, "fl": {"models": "ignored"},
                                      "li": {"models": "ignored"}})
        self.assertNotIn("models", decoded["floors"])
        self.assertNotIn("models", decoded["light"])

    def test_yaml_strings_preserve_quotes_comments_and_scalar_words(self):
        for text in ('hello " # still text', "yes", "no", "null", "a\nb", "a\u2028b"):
            with self.subTest(text=text):
                self.assertEqual(seed.parse_yaml("value: " + seed.yaml_scalar(text))["value"], text)

    def test_export_then_import_gives_the_same_seed(self):
        original = self.seed(name="quiet, high, morning sun")
        code, _, _ = seed.make_code(original, 0)
        self.assertEqual(seed.from_min_json(seed.decode(code)), original)

    def test_the_preferences_survive_a_trip_through_a_written_profile(self):
        original = self.seed()
        code, _, _ = seed.make_code(original, 0)
        rebuilt = seed.shareable(seed.parse_yaml(
            seed.profile_yaml(seed.from_min_json(seed.decode(code)), code)))
        for key in ("flat_type", "budget_mode", "avoid", "priorities", "must_haves",
                    "my_questions", "floors", "light", "quiet_over_light", "first_weeks",
                    "story_summary"):
            self.assertEqual(original[key], rebuilt[key], key)

    def test_the_numbers_that_are_somebody_elses_do_not_survive_on_purpose(self):
        code, _, _ = seed.make_code(self.seed(), 0)
        rebuilt = seed.shareable(seed.parse_yaml(
            seed.profile_yaml(seed.from_min_json(seed.decode(code)), code)))
        for key in ("budget_band", "commute_area", "move_in_month"):
            self.assertIsNone(rebuilt[key], "%s must not be inherited as a value" % key)


# -------------------------------------------------------------- the questions
class TestQuestions(SeedCase):
    def test_a_bare_string_means_vet_and_answer(self):
        questions = seed.clean_questions(["Is the bedroom on the quiet side?"])
        self.assertEqual(questions, [{"text": "Is the bedroom on the quiet side?",
                                      "when": "vet", "kind": "answer"}])

    def test_the_stage_and_the_kind_survive_the_code(self):
        original = self.seed()
        back = seed.from_min_json(seed.decode(seed.make_code(original, 0)[0]))
        self.assertEqual(original["my_questions"], back["my_questions"])
        self.assertEqual([q["when"] for q in back["my_questions"]], ["compare", "vet", "viewing"])
        self.assertEqual([q["kind"] for q in back["my_questions"]], ["answer", "answer", "check"])

    def test_a_default_question_travels_as_a_bare_string(self):
        obj = seed.to_min_json(self.seed())
        self.assertEqual(obj["qs"][1], "Is the bedroom on the quiet side?")
        self.assertEqual(obj["qs"][2]["when"], "viewing")

    def test_the_trigger_stays_at_home(self):
        code, minimal, _ = seed.make_code(self.seed(), 0)
        self.assertNotIn("trigger", json.dumps(minimal))
        self.assertNotIn("price below the local band", seed.card(self.seed(), code))
        self.assertIn("trigger", read_text(TEMPLATE))

    def test_a_made_up_stage_or_kind_falls_back_to_the_default(self):
        questions = seed.clean_questions([{"text": "x", "when": "whenever", "kind": "vibes"}])
        self.assertEqual(questions[0]["when"], "vet")
        self.assertEqual(questions[0]["kind"], "answer")

    def test_the_card_prints_the_stage_in_brackets(self):
        code, _, _ = seed.make_code(self.seed(), 0)
        card = seed.card(self.seed(), code)
        self.assertIn("My questions", card)
        self.assertIn("[compare]", card)
        self.assertIn("[viewing · check]", card)


# ------------------------------------------------------------------- the card
class TestCard(SeedCase):
    def test_three_sentences_and_what_each_one_is_for(self):
        lines = seed.sentences(self.seed())
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertTrue(line.endswith(".") or line.endswith("”"), line)
        self.assertTrue(lines[0].startswith("I want "))
        self.assertIn("one-bedroom", lines[0])
        self.assertIn("£2,000–2,400 total per month", lines[0])
        self.assertTrue(lines[1].startswith("I will not take:"))
        self.assertIn("heating with no written tariff", lines[1])
        self.assertIn("Price sits last", lines[2])
        self.assertIn("quiet wins", lines[2])

    def test_the_three_sentences_are_on_the_card(self):
        code, _, _ = seed.make_code(self.seed(), 0)
        card = seed.card(self.seed(name="a seed"), code)
        for line in seed.sentences(self.seed(name="a seed")):
            self.assertIn(line, card)
        self.assertIn("Pea Princess seed — a seed", card)
        self.assertIn(code, card)

    def test_the_yaml_block_reads_back_as_yaml(self):
        block = seed.yaml_block(self.seed(name="a seed"))
        parsed = seed.parse_yaml("seed:\n" + block)["seed"]
        self.assertEqual(parsed["flat_type"], "one_bed")
        self.assertEqual(parsed["priorities"], ["quiet", "light", "price"])
        self.assertTrue(parsed["quiet_over_light"])

    def test_the_journey_adds_counts_and_hides_the_address(self):
        lines = seed.journey_lines(JOURNEY)
        self.assertIn("4 flats vetted", lines[0])
        self.assertIn("1 PASS, 1 EDGE, 2 KILL", lines[0])
        self.assertIn("floor 4", lines[1])
        self.assertNotIn("Example House", " ".join(lines))
        revealed = seed.journey_lines(JOURNEY, reveal_address=True)
        self.assertIn("Example House", revealed[1])

    def test_a_postcode_in_a_journey_label_is_scrubbed(self):
        dirty = json.loads(json.dumps(JOURNEY))
        dirty["chosen"]["label"] = "one-bed at SE1 9SG"
        self.assertNotIn("SE1 9SG", " ".join(seed.journey_lines(dirty)))

    def test_no_journey_means_no_found_lines(self):
        self.assertEqual(seed.journey_lines(None), [])
        self.assertNotIn("what I found", seed.card(self.seed(), "PP1.x"))


# ----------------------------------------------------------------- the import
class TestImport(SeedCase):
    def test_it_writes_a_profile_with_blanks_for_everything_personal(self):
        code, _, _ = seed.make_code(self.seed(name="a seed"), 0)
        out = os.path.join(self.tmp, "new-profile.yaml")
        rc, stdout, _ = run("import", code, "--out", out)
        self.assertEqual(rc, 0)
        text = read_text(out)
        parsed = seed.parse_yaml(text)
        self.assertEqual(parsed["flat_type"], "one_bed")
        self.assertEqual(parsed["avoid"], ["ground floor", "heating with no written tariff"])
        self.assertEqual(len(parsed["my_questions"]), 3)
        for blank in ("min_floor_area_sqft", "guarantor_route", "self_intro_template"):
            self.assertIsNone(parsed[blank], "%s should be blank in an imported profile" % blank)
        self.assertIsNone(parsed["budget"]["all_in_pcm_ceiling"])
        self.assertIsNone(parsed["commute"]["destination"])
        self.assertIsNone(parsed["move_in_window"]["earliest"])
        self.assertGreaterEqual(text.count("FILL IN"), len(seed.BLANKS))
        for key, _why in seed.BLANKS:
            self.assertIn(key.split(".")[-1], text)
        self.assertIn("What is still yours to fill in", stdout)
        self.assertIn("guarantor_route", stdout)
        self.assertIn("Written to", stdout)

    def test_the_band_and_the_district_come_back_as_comments_not_values(self):
        code, _, _ = seed.make_code(self.seed(audience="friend"), 0)
        text = seed.profile_yaml(seed.from_min_json(seed.decode(code)), code)
        self.assertIn("# FILL IN — the seed said £2,000–2,400 total per month", text)
        self.assertIn("the seed only carried the district WC2R", text)
        self.assertIsNone(seed.parse_yaml(text)["budget"]["all_in_pcm_ceiling"])

    def test_it_refuses_to_overwrite_without_being_told_to(self):
        code, _, _ = seed.make_code(self.seed(), 0)
        rc, _, err = run("import", code, "--out", self.profile)
        self.assertEqual(rc, 2)
        self.assertIn("already exists", err)
        self.assertIn("min_floor_area_sqft: 480", read_text(self.profile))

    def test_it_reads_a_code_out_of_a_saved_card(self):
        rc, card, _ = run("export", "--profile", self.profile, "--name", "a seed")
        self.assertEqual(rc, 0)
        path = write(self.tmp, "card.txt", card)
        rc, stdout, _ = run("import", path)
        self.assertEqual(rc, 0)
        self.assertIn("What came with the seed", stdout)
        self.assertIn("Nothing was written", stdout)

    def test_a_seed_never_carries_the_things_the_import_asks_for(self):
        asked = [key for key, _ in seed.BLANKS]
        for key in ("guarantor_route", "commute.destination", "budget.all_in_pcm_ceiling",
                    "move_in_window.earliest", "self_intro_template"):
            self.assertIn(key, asked)


# -------------------------------------------------------------------- the CLI
class TestCli(SeedCase):
    def test_export_prints_a_card_and_a_code(self):
        rc, out, err = run("export", "--profile", self.profile, "--name", "a seed")
        self.assertEqual(rc, 0)
        self.assertIn("Pea Princess seed — a seed", out)
        self.assertIn("PP1.", out)
        self.assertIn("kept out of the seed", err)

    def test_export_json_carries_the_allow_list_and_the_scrub_report(self):
        rc, out, _ = run("export", "--profile", self.profile, "--journey", self.journey, "--json")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["shared_fields"], [k for k, _ in seed.ALLOW])
        self.assertEqual(len(data["sentences"]), 3)
        self.assertIn("guarantor_route", data["scrubbed_from_profile"])
        self.assertIn("4 flats vetted", data["journey_lines"][0])
        self.assertTrue(data["seed_code"].startswith("PP1."))

    def test_a_missing_file_fails_cleanly(self):
        rc, _, err = run("export", "--profile", os.path.join(self.tmp, "nope.yaml"))
        self.assertEqual(rc, 1)
        self.assertIn("no such file", err)
        rc, _, err = run("import", "not-a-code")
        self.assertEqual(rc, 1)

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(run()[0], 2)


if __name__ == "__main__":
    unittest.main()
