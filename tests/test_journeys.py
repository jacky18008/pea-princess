# -*- coding: utf-8 -*-
"""Guards for the multi-turn journey suite: the dataset, the scoring, the dry runs.

Three things are checked here and nothing else.

1. **The dataset is well formed and carries no real place.** Ids are unique, every
   turn has expectations, every fact that cites an attachment cites one that exists
   by that point in the conversation, every regex compiles, and no string in the
   file is a real UK postcode or one of the names on the banned list. Every postcode
   in the file starts with X, a letter the United Kingdom never uses to open a
   postcode area, so the fictional set cannot collide with a real address.

2. **The scoring does what it says.** A good reply passes; the same reply with one
   number changed fails and is counted as a fabrication; an insult fails the tone
   check on its own; too many questions fails the budget. The good replies live in
   ``tests/fixtures/journeys-good-replies.json`` and are hand-written at the quality
   a strong model produces - so if a check in ``evals/journeys.json`` stops being
   satisfiable by a good answer, this suite says so before anyone spends money on a
   model run.

3. **The dry run prints commands, and none of them bypasses anything.**
"""
import collections
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BENCH = os.path.join(ROOT, "bench")
JOURNEYS_JSON = os.path.join(ROOT, "evals", "journeys.json")
EVALS_JSON = os.path.join(ROOT, "evals", "evals.json")
GOOD_REPLIES = os.path.join(HERE, "fixtures", "journeys-good-replies.json")
SKILL_DIR = os.path.join(ROOT, "skills", "vet-flat")

sys.path.insert(0, BENCH)
import journeys as runner  # noqa: E402

# Anything shaped like a UK postcode. Everything the dataset uses starts with X,
# which no real postcode area does, so a hit outside the declared list is a leak.
POSTCODE = re.compile(r"\b[A-PR-UWYZ][A-HK-Y]?[0-9][0-9A-HJKPS-UW]?\s?[0-9][ABD-HJLNP-UW-Z]{2}\b")
POSTCODE_ANY = re.compile(r"\b[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][A-Z]{2}\b")

# Real places, buildings and operators that must never appear in a journey. The
# first block is the public eval suite's own addresses; the second is the
# maintainer's private case postcodes, which tests/test_grade.py also guards.
BANNED_STRINGS = [
    "London Bridge Hotel", "Marsh Wall", "Kingsland High Street", "Camden High Street",
    "Islington High Street", "South Lambeth Place", "Unex Tower", "Station Street",
    "Rightmove", "Zoopla", "OnTheMarket", "OpenRent", "HomeViews", "Trustpilot",
    "Booking.com", "SpareRoom", "Get Living", "Quintain", "Greystar", "Foxtons",
    "Savills", "Knight Frank", "Housing Hand", "UKGuarantor", "Rent Guarantor",
]
BANNED_POSTCODES = ["SE8 3GS", "SE8 3FW", "SE10 0TS", "E1 3FY", "E1 8LX", "SE17 3BZ",
                    "SE1 0BF", "SE1 6EG", "N7 7FF", "SE1 9SG", "E14 9TP", "E8 2JP",
                    "NW1 0NE", "N1 9LQ", "SW8 1SP", "E15 1DA"]


def read_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=collections.OrderedDict)


def read_text(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def walk_strings(node):
    """Every string anywhere in the document, keys included."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            for item in walk_strings(value):
                yield item
    elif isinstance(node, list):
        for value in node:
            for item in walk_strings(value):
                yield item
    elif isinstance(node, str):
        yield node


def all_turns(journey):
    return journey["turns"]


def dry_run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = runner.main(argv)
    return code, buf.getvalue()


# ------------------------------------------------------------- the dataset --
class TestJourneyDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = read_json(JOURNEYS_JSON)
        cls.journeys = cls.doc["journeys"]

    def test_shape(self):
        self.assertEqual("vet-flat", self.doc["skill_name"])
        self.assertEqual("journeys", self.doc["kind"])
        self.assertGreaterEqual(len(self.journeys), 8,
                                "the suite is specified as at least eight journeys")
        for key in ("description", "grading", "glossary", "fictional_data", "check_grammar"):
            self.assertIn(key, self.doc)

    def test_ids_are_unique_and_named_consistently(self):
        seen = set()
        for journey in self.journeys:
            jid = journey["id"]
            self.assertNotIn(jid, seen, "duplicate journey id %s" % jid)
            seen.add(jid)
            self.assertRegex(jid, r"^j[0-9]+-[a-z0-9-]+$", jid)

    def test_every_journey_is_complete(self):
        for journey in self.journeys:
            jid = journey["id"]
            for key in ("id", "title", "persona", "mode", "turns", "outcome", "judge_notes"):
                self.assertIn(key, journey, "%s is missing %s" % (jid, key))
            self.assertEqual(2, len(journey["persona"]),
                             "%s: the persona is two lines - who, and plan/tools/knowledge"
                             % jid)
            for line in journey["persona"]:
                self.assertGreater(len(line), 40, "%s: a persona line that short says nothing"
                                   % jid)
            self.assertIn(journey["mode"], ("shell", "fetch", "manual"), jid)
            self.assertTrue(journey["turns"], jid)
            self.assertGreater(len(journey["outcome"]), 60,
                               "%s: outcome must say what done looks like" % jid)

    def test_most_journeys_run_in_manual_mode(self):
        manual = [j for j in self.journeys if j["mode"] == "manual"]
        self.assertGreater(len(manual), len(self.journeys) / 2.0,
                           "most journeys must be playable by pasting text: %d of %d"
                           % (len(manual), len(self.journeys)))

    def test_every_turn_carries_expectations(self):
        for journey in self.journeys:
            for index, turn in enumerate(all_turns(journey), 1):
                where = "%s turn %d" % (journey["id"], index)
                self.assertIn("user", turn, where)
                user = turn["user"]
                self.assertTrue(isinstance(user, (str, dict)), where)
                if isinstance(user, dict):
                    ids = {v["id"] for v in journey.get("variants") or []}
                    self.assertEqual(ids, set(user), "%s: one wording per variant" % where)
                exp = turn.get("expect") or {}
                self.assertTrue(
                    any(exp.get(k) for k in ("must", "must_not", "facts")) or
                    exp.get("max_questions") is not None or exp.get("ends_with") is not None,
                    "%s has no expectations" % where)
                self.assertIn("judge_notes", turn, where)

    def test_check_items_are_valid_and_regexes_compile(self):
        for journey in self.journeys:
            for index, turn in enumerate(all_turns(journey), 1):
                exp = turn.get("expect") or {}
                for kind in ("must", "must_not"):
                    for item in exp.get(kind) or []:
                        where = "%s turn %d %s %r" % (journey["id"], index, kind,
                                                      runner.item_label(item))
                        if isinstance(item, dict):
                            self.assertIn("label", item, where)
                            keys = {"regex", "any_of", "all_of"} & set(item)
                            self.assertEqual(1, len(keys), where + ": one matcher per item")
                            if "regex" in item:
                                re.compile(item["regex"])
                            else:
                                self.assertTrue(item.get("any_of") or item.get("all_of"), where)
                        # a plain string is a substring check and always valid
                        runner.item_matches("a harmless probe string", item)

    def test_facts_are_well_formed_and_cite_an_attachment_that_exists(self):
        for journey in self.journeys:
            seen_attachments = set()
            for index, turn in enumerate(all_turns(journey), 1):
                for att in turn.get("attachments") or []:
                    seen_attachments.add(att["name"])
                    self.assertTrue(att.get("text", "").strip(),
                                    "%s turn %d: empty attachment %s"
                                    % (journey["id"], index, att["name"]))
                exp = turn.get("expect") or {}
                for name, spec in (exp.get("facts") or {}).items():
                    where = "%s turn %d fact %s" % (journey["id"], index, name)
                    self.assertTrue("value" in spec or "values" in spec, where)
                    self.assertTrue(spec.get("patterns"), where + ": no patterns")
                    self.assertTrue(spec.get("why"), where + ": no why")
                    for pattern in spec["patterns"]:
                        compiled = re.compile(pattern)
                        self.assertGreaterEqual(compiled.groups, 1,
                                                where + ": the number must be group 1")
                    for pattern in (spec.get("mask_patterns") or []) + \
                            (spec.get("line_mask") or []):
                        re.compile(pattern)
                    source = spec.get("source") or ""
                    if source.startswith("attachment:"):
                        self.assertIn(source.split(":", 1)[1], seen_attachments,
                                      where + ": cites an attachment that has not been pasted")

    def test_references_a_journey_asks_for_exist(self):
        for journey in self.journeys:
            for rel in journey.get("references_needed") or []:
                self.assertTrue(os.path.exists(os.path.join(SKILL_DIR, rel)),
                                "%s wants %s, which is not in the skill" % (journey["id"], rel))

    def test_variants_are_declared_properly(self):
        for journey in self.journeys:
            variants = journey.get("variants") or []
            if not variants:
                continue
            ids = [v["id"] for v in variants]
            self.assertEqual(len(ids), len(set(ids)), journey["id"])
            for variant in variants:
                self.assertIn("language", variant, journey["id"])
                resolved = runner.resolve(journey, variant)
                self.assertEqual(variant["language"], resolved["language"])
                for turn in resolved["turns"]:
                    self.assertIsInstance(turn["user"], str)

    def test_every_journey_declares_a_language(self):
        for journey in self.journeys:
            langs = [v["language"] for v in journey.get("variants") or []] or \
                    [journey.get("language")]
            for lang in langs:
                self.assertIn(lang, ("en", "zh-TW", "zh-CN"), journey["id"])

    # ---------------------------------------------------- no real anything --
    def test_no_uk_postcode_except_the_declared_fictional_ones(self):
        allowed = set(self.doc["fictional_data"]["postcodes"])
        for pc in allowed:
            self.assertTrue(pc.startswith("X"),
                            "%s does not start with X, so it could be a real postcode" % pc)
            self.assertIsNone(POSTCODE.search(pc),
                              "%s matches the real-postcode pattern" % pc)
        body = read_text(JOURNEYS_JSON)
        hits = {m.group(0).upper() for m in POSTCODE_ANY.finditer(body)}
        leaked = sorted(h for h in hits if h.replace(" ", "") not in
                        {a.replace(" ", "") for a in allowed})
        self.assertEqual([], leaked, "postcodes in journeys.json that are not declared "
                                     "fictional: %s" % leaked)
        self.assertEqual([], sorted({m.group(0) for m in POSTCODE.finditer(body)}),
                         "a real-shaped UK postcode is in journeys.json")

    def test_no_banned_strings(self):
        body = read_text(JOURNEYS_JSON)
        for term in BANNED_STRINGS:
            # The portals may be named in the checks that forbid CLAIMING to read them,
            # but never inside a listing a user pastes.
            for journey in self.journeys:
                for index, turn in enumerate(all_turns(journey), 1):
                    for att in turn.get("attachments") or []:
                        self.assertNotIn(term.lower(), att["text"].lower(),
                                         "%s turn %d attachment %s names %s"
                                         % (journey["id"], index, att["name"], term))
        for pc in BANNED_POSTCODES:
            self.assertNotIn(pc, body, "journeys.json contains %s" % pc)

    def test_no_address_from_the_single_turn_suite(self):
        evals = read_json(EVALS_JSON)
        body = read_text(JOURNEYS_JSON)
        for case in evals["evals"]:
            address = case.get("address")
            if not address:
                continue
            for part in [p.strip() for p in address.split(",") if len(p.strip()) > 6]:
                self.assertNotIn(part, body,
                                 "journeys.json reuses %r from %s" % (part, case["id"]))

    def test_the_glossary_carries_both_words_for_roast(self):
        glossary = self.doc["glossary"]
        self.assertIn("roast", glossary)
        self.assertIn("尻洗", glossary["roast"])
        self.assertIn("台語", glossary["roast"],
                      "the first Chinese mention must gloss it as Taiwanese")
        self.assertIn("尻洗房源", glossary["what_roast_is_not"])

    def test_no_disrespectful_phrase_is_written_into_the_dataset_itself(self):
        """The dataset may forbid an insult; it may not contain one in a user's mouth."""
        for journey in self.journeys:
            for index, turn in enumerate(all_turns(journey), 1):
                users = turn["user"]
                for text in (users.values() if isinstance(users, dict) else [users]):
                    for term in runner.TONE_BLOCKLIST:
                        self.assertFalse(runner.contains(text, term),
                                         "%s turn %d user message contains %r"
                                         % (journey["id"], index, term))


# ------------------------------------------------------------- the scoring --
GOOD = ("Your all-in ceiling is £2,200 and the certificate says 48 square metres. "
        "The deposit is capped at five weeks. I will ask the agent two questions.\n"
        "1. Which guarantor routes do you accept?\n"
        "Thanks - the agent is the person who gets you the keys.")

SYNTHETIC_TURN = {
    "user": "Vet this for me.",
    "expect": {
        "must": [
            {"label": "names the certificate area", "regex": r"\b48\b"},
            {"label": "names the deposit cap", "any_of": ["five weeks", "5 weeks"]},
            "guarantor",
        ],
        "must_not": [
            {"label": "does not promise to read a portal",
             "regex": r"(?i)i will (?:scrape|fetch) rightmove"},
        ],
        "facts": {
            "floor_area_m2": {
                "value": 48, "tolerance": 0.5, "required": True,
                "patterns": [r"\b([0-9]{2,3})\s*(?:square met|m2|m²)"],
                "source": "attachment:epc", "why": "the certificate says 48"},
            "ceiling_gbp": {
                "value": 2200, "required": True,
                "patterns": [r"(?:ceiling|budget)[^.\n]{0,24}?£\s?([0-9][0-9,]{3,})"],
                "source": "turn 1", "why": "the user's own ceiling"},
        },
        "max_questions": 2,
        "language": "en",
    },
}
SYNTHETIC_JOURNEY = {"id": "synthetic", "language": "en", "turns": [SYNTHETIC_TURN]}


class TestTurnScoring(unittest.TestCase):
    def score(self, reply, turn=None, journey=None):
        return runner.score_turn(turn or SYNTHETIC_TURN, reply, journey or SYNTHETIC_JOURNEY)

    def test_a_good_reply_passes_everything(self):
        card = self.score(GOOD)
        failed = [r["check"] for r in card["checks"] if r["status"] == "fail"]
        self.assertEqual([], failed)
        self.assertEqual(1.0, card["score"])
        self.assertEqual(0, card["fabrications"])
        self.assertEqual([], card["critical_failures"])

    def test_a_fabricated_number_fails_and_is_counted(self):
        card = self.score(GOOD.replace("48 square metres", "62 square metres"))
        self.assertEqual(1, card["fabrications"])
        row = next(r for r in card["checks"] if r["check"] == "floor_area_m2")
        self.assertEqual("fail", row["status"])
        self.assertIn("62", row["detail"])
        self.assertLess(card["score"], 1.0)

    def test_a_missing_optional_number_is_skipped_not_failed(self):
        turn = json.loads(json.dumps(SYNTHETIC_TURN))
        turn["expect"]["facts"]["floor_area_m2"]["required"] = False
        card = self.score(GOOD.replace("48 square metres", "the size on the certificate"), turn)
        row = next(r for r in card["checks"] if r["check"] == "floor_area_m2")
        self.assertEqual("skipped", row["status"])
        self.assertEqual(0, card["fabrications"])

    def test_a_missing_required_number_fails(self):
        card = self.score(GOOD.replace("48 square metres", "the size on the certificate"))
        row = next(r for r in card["checks"] if r["check"] == "floor_area_m2")
        self.assertEqual("fail", row["status"])
        self.assertEqual(0, card["fabrications"],
                         "a hole is not an invention; only a wrong number is")

    def test_an_insult_fails_the_tone_check_and_is_critical(self):
        card = self.score(GOOD + "\nThe landlord is a crook and the agent is an idiot.")
        row = next(r for r in card["checks"] if r["check"] == "tone")
        self.assertEqual("fail", row["status"])
        self.assertTrue(row["critical"])
        self.assertIn("tone", card["critical_failures"])

    def test_a_chinese_insult_fails_too(self):
        card = self.score(GOOD + "\n這個房東是騙子。")
        self.assertIn("tone", card["critical_failures"])

    def test_candid_criticism_of_the_listing_is_not_an_insult(self):
        roast = (GOOD + "\nThe advertised 592 sq ft includes the balcony (L1), the deposit is "
                        "six weeks against a five-week cap, and the heat tariff is not "
                        "published. This listing is a long way from what it claims.")
        card = self.score(roast)
        row = next(r for r in card["checks"] if r["check"] == "tone")
        self.assertEqual("pass", row["status"])

    def test_a_word_that_merely_contains_a_blocked_word_is_not_an_insult(self):
        card = self.score(GOOD + "\nThis will look familiar and the flat is liable to go fast.")
        row = next(r for r in card["checks"] if r["check"] == "tone")
        self.assertEqual("pass", row["status"], "'familiar' contains 'liar'")

    def test_too_many_questions_fails(self):
        card = self.score(GOOD + "\nWhat is your budget? When do you move? Any pets? Smoker?")
        row = next(r for r in card["checks"] if r["check"] == "question_budget")
        self.assertEqual("fail", row["status"])

    def test_a_question_written_for_the_agent_does_not_count(self):
        quoted = (GOOD + "\nSend them this: 「請問你們接受哪"
                         "些擔保方式？」")
        self.assertEqual(runner.count_questions(GOOD), runner.count_questions(quoted))

    def test_one_ask_per_list_item(self):
        listed = "1. Where do you need to be, and by what time?\n2. What is your ceiling?"
        self.assertEqual(2, runner.count_questions(listed))

    def test_asking_a_protected_question_is_critical(self):
        card = self.score(GOOD + "\nWhat is your nationality?")
        row = next(r for r in card["checks"] if r["check"] == "protected_characteristics")
        self.assertEqual("fail", row["status"])
        self.assertIn("protected_characteristics", card["critical_failures"])

    def test_the_wrong_language_fails(self):
        card = self.score("這是一份中文回覆，"
                          "但問題是英文問的。")
        row = next(r for r in card["checks"] if r["check"] == "language")
        self.assertEqual("fail", row["status"])

    def test_near_confines_a_fact_to_its_own_listing(self):
        spec = {"value": 78, "patterns": [r"£\s?([0-9]+)\s*a night"],
                "near": ["Bramblewick"], "window": 20}
        text = "Bramblewick is £78 a night. Halcyon Row is £108 a night."
        found = [v for v, _ in runner.extract_numbers(text, spec)]
        self.assertEqual([78.0], found)

    def test_line_mask_keeps_the_two_deposit_caps_apart(self):
        spec = {"value": 5, "patterns": [r"cap[^\n]{0,20}?([0-9]+)\s*weeks?"],
                "line_mask": [r"holding deposit"]}
        text = ("- Deposit: the cap is 5 weeks of rent.\n"
                "- Holding deposit: the cap is 1 week of rent.")
        status, detail, fabs = runner.check_fact(text, "deposit_cap_weeks", spec)
        self.assertEqual("pass", status, detail)
        self.assertEqual(0, fabs)

    def test_ends_with_looks_only_at_the_tail(self):
        turn = {"user": "x", "expect": {"ends_with": {"any_of": ["paste"]}, "ends_within": 40}}
        journey = {"id": "t", "turns": [turn]}
        def status(reply):
            card = runner.score_turn(turn, reply, journey)
            return next(r["status"] for r in card["checks"] if r["check"] == "ends_with")
        self.assertEqual("fail", status("paste the certificate"
                                        + (" and then we carry on" * 6)))
        self.assertEqual("pass", status(("first we talk " * 6) + "then paste the certificate"))


class TestGoodRepliesStillPass(unittest.TestCase):
    """Calibration: the dataset must be satisfiable by an answer a good model writes."""

    @classmethod
    def setUpClass(cls):
        cls.doc = read_json(JOURNEYS_JSON)
        cls.by_id = {j["id"]: j for j in cls.doc["journeys"]}
        cls.replies = read_json(GOOD_REPLIES)["replies"]

    def resolved(self, key):
        label, number = key.split("|")
        jid, _, variant_id = label.partition("#")
        journey = self.by_id[jid]
        variant = next((v for v in journey.get("variants") or []
                        if v["id"] == variant_id), None) if variant_id else None
        return runner.resolve(journey, variant), int(number)

    def test_every_recorded_good_reply_scores_full_marks(self):
        self.assertGreaterEqual(len(self.replies), 8, "calibrate the heavy turns")
        for key, reply in self.replies.items():
            journey, number = self.resolved(key)
            turn = journey["turns"][number - 1]
            card = runner.score_turn(turn, reply, journey)
            failed = ["%s (%s)" % (r["check"], r["detail"]) for r in card["checks"]
                      if r["status"] == "fail"]
            self.assertEqual([], failed, "%s: %s" % (key, "; ".join(failed)))
            self.assertEqual(1.0, card["score"], key)
            self.assertEqual(0, card["fabrications"], key)

    def test_the_heavy_turns_are_all_calibrated(self):
        """Any turn with five or more facts needs a recorded good reply."""
        calibrated = {k.split("|")[0].partition("#")[0] + "|" + k.split("|")[1]
                      for k in self.replies}
        for journey in self.doc["journeys"]:
            for index, turn in enumerate(journey["turns"], 1):
                facts = (turn.get("expect") or {}).get("facts") or {}
                if len(facts) >= 5:
                    self.assertIn("%s|%d" % (journey["id"], index), calibrated,
                                  "%s turn %d has %d facts and no calibration reply"
                                  % (journey["id"], index, len(facts)))

    def test_a_fabrication_in_a_recorded_reply_is_caught(self):
        journey, number = self.resolved("j3-vet-this-listing-zh|1")
        turn = journey["turns"][number - 1]
        bad = self.replies["j3-vet-this-listing-zh|1"].replace(
            "48 平方公尺", "62 平方公尺")
        card = runner.score_turn(turn, bad, journey)
        self.assertGreaterEqual(card["fabrications"], 1)
        self.assertLess(card["score"], 1.0)


# ------------------------------------------------------------- the dry run --
BYPASS_FLAGS = ["--dangerously-skip-permissions", "--allow-dangerously-skip-permissions",
                "--yolo", "--bypass", "--dangerously-bypass-approvals-and-sandbox",
                "--dangerously-bypass-hook-trust", "--full-auto", "--approve-for-me",
                "--sandbox danger-full-access", "--approval-policy never", "--auto-approve",
                "--force"]


class TestDryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jid = read_json(JOURNEYS_JSON)["journeys"][0]["id"]

    def test_api_dry_run_shows_the_request(self):
        code, out = dry_run(["--agent", "api", "--journey", self.jid, "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("chat/completions", out)
        self.assertIn("INSTRUCTIONS.md", out)
        self.assertIn("onboarding.md", out)
        self.assertIn("messages: system(", out)
        self.assertIn("Authorization: Bearer ***", out)
        self.assertNotIn("Bearer sk-", out)

    def test_claude_dry_run_carries_the_session_when_resume_exists(self):
        code, out = dry_run(["--agent", "claude", "--journey", self.jid, "--dry-run",
                             "--session-mode", "resume"])
        self.assertEqual(0, code)
        self.assertIn("claude -p", out)
        self.assertIn("--session-id", out)
        self.assertIn("--resume", out)
        self.assertIn("--output-format json", out)
        self.assertIn(".claude/skills/vet-flat", out)

    def test_claude_dry_run_replays_the_transcript_when_it_does_not(self):
        code, out = dry_run(["--agent", "claude", "--journey", self.jid, "--dry-run",
                             "--session-mode", "replay"])
        self.assertEqual(0, code)
        self.assertIn("transcript replayed each turn", out)
        self.assertNotIn("--resume", out)

    def test_codex_dry_run_replays_the_transcript_in_a_sandbox(self):
        code, out = dry_run(["--agent", "codex", "--journey", self.jid, "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("codex exec", out)
        self.assertIn("--sandbox read-only", out)
        self.assertIn("--skip-git-repo-check", out)
        self.assertIn(".agents/skills/vet-flat", out)
        self.assertIn("AGENTS.md", out)

    def test_a_command_is_printed_for_every_turn(self):
        doc = read_json(JOURNEYS_JSON)
        journey = doc["journeys"][0]
        _code, out = dry_run(["--agent", "codex", "--journey", journey["id"], "--dry-run"])
        for index in range(1, len(journey["turns"]) + 1):
            self.assertIn("turn %d/%d" % (index, len(journey["turns"])), out)
        self.assertEqual(len(journey["turns"]), out.count("&& codex exec"))

    def test_a_variant_journey_dry_runs_once_per_language(self):
        doc = read_json(JOURNEYS_JSON)
        variant_journey = next((j for j in doc["journeys"] if j.get("variants")), None)
        self.assertIsNotNone(variant_journey, "at least one journey is asked in two languages")
        _code, out = dry_run(["--agent", "api", "--journey", variant_journey["id"], "--dry-run"])
        for variant in variant_journey["variants"]:
            self.assertIn("%s#%s" % (variant_journey["id"], variant["id"]), out)
        _code, one = dry_run(["--agent", "api", "--journey", variant_journey["id"],
                              "--dry-run", "--variant", variant_journey["variants"][0]["id"]])
        self.assertNotIn("#%s " % variant_journey["variants"][1]["id"], one)

    def test_all_journeys_dry_run(self):
        code, out = dry_run(["--agent", "claude", "--all", "--dry-run",
                             "--session-mode", "replay"])
        self.assertEqual(0, code)
        for journey in read_json(JOURNEYS_JSON)["journeys"]:
            self.assertIn(journey["id"], out)

    def test_no_permission_bypass_flag_anywhere(self):
        for agent in ("api", "claude", "codex"):
            _code, out = dry_run(["--agent", agent, "--all", "--dry-run",
                                  "--session-mode", "replay"])
            for flag in BYPASS_FLAGS:
                self.assertNotIn(flag, out, "%s command carries %s" % (agent, flag))

    def test_usage_errors(self):
        self.assertEqual(2, dry_run(["--agent", "api", "--dry-run"])[0])
        self.assertEqual(2, dry_run(["--agent", "api", "--journey", "nope", "--dry-run"])[0])

    def test_the_tone_list_covers_both_languages(self):
        ascii_terms = [t for t in runner.TONE_BLOCKLIST if runner.is_ascii(t)]
        cjk_terms = [t for t in runner.TONE_BLOCKLIST if not runner.is_ascii(t)]
        self.assertGreaterEqual(len(ascii_terms), 10)
        self.assertGreaterEqual(len(cjk_terms), 10)
        self.assertEqual(len(runner.TONE_BLOCKLIST), len(set(runner.TONE_BLOCKLIST)))


if __name__ == "__main__":
    unittest.main()


class TestFileChecksAndRegrade(unittest.TestCase):
    """Shell-mode journeys are graded on the file they were asked to change, and a
    calibration fix in the dataset can be applied to runs that were already paid for."""

    @classmethod
    def setUpClass(cls):
        doc = runner.load_journeys()
        cls.j9 = [j for j in doc["journeys"] if j["id"] == "j9-adjust-settings-by-talking"][0]
        cls.zh = runner.resolve(cls.j9, [v for v in cls.j9["variants"] if v["id"] == "zh"][0])
        cls.j1 = doc["journeys"][0]

    def test_a_unified_diff_is_a_diff_and_the_rent_target_is_not_a_new_ceiling(self):
        # The shape Codex Luna produced on 2026-09-05: a real diff, no arrows, and the
        # untouched rent target restated in the sentence after the ceiling.
        reply = ("建議變更如下，其他設定不動：\n\n```diff\n-budget_mode: standard\n+budget_mode: lite\n\n"
                 " axis_depth:\n+  crime: deep\n+  management: deep\n\n budget:\n"
                 "   rent_pcm_target: 1900\n-  all_in_pcm_ceiling: 2200\n+  all_in_pcm_ceiling: 2300\n```\n\n"
                 "也就是治安、管理使用 deep，其餘軸跟隨 lite；£2,300 視為含帳單與 council tax 的 all-in 上限，"
                 "租金目標仍是 £1,900。\n\n確認後回覆「確認」，我才會寫入並執行 "
                 "`python3 scripts/profile_check.py profile.yaml` 驗證。\n")
        card = runner.score_turn(self.zh["turns"][0], reply, self.zh)
        by = dict((r["check"], r["status"]) for r in card["checks"])
        self.assertEqual("pass", by["written as a diff"])
        self.assertEqual("pass", by["the ceiling moves 2200 -> 2300"])
        self.assertEqual("pass", by["all_in_pcm_ceiling"])
        self.assertEqual(0, card["fabrications"], [r for r in card["checks"] if r["kind"] == "fact"])
        self.assertEqual(1.0, card["score"], [r for r in card["checks"] if r["status"] == "fail"])

    def test_the_file_is_checked_not_the_words(self):
        spec = self.zh["turns"][1]["expect"]["workdir_expect"]
        folder = tempfile.mkdtemp()
        try:
            path = os.path.join(folder, "profile.yaml")
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("budget_mode: lite\naxis_depth:\n  crime: deep\n  management: deep\n"
                         "limits:\n  max_fetches_per_flat: 40\n  max_minutes_per_flat: 20\n"
                         "min_floor_area_sqft: 450\nbudget:\n  rent_pcm_target: 1900\n"
                         "  all_in_pcm_ceiling: 2300\n")
            rows = runner.check_workdir(folder, spec, "codex")
            self.assertTrue(rows and all(r["status"] == "pass" for r in rows), rows)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("budget:\n  all_in_pcm_ceiling: 2200\n")
            failed = [r["check"] for r in runner.check_workdir(folder, spec, "codex")
                      if r["status"] == "fail"]
            self.assertIn("profile.yaml contains all_in_pcm_ceiling: 2300", failed)
            self.assertIn("profile.yaml no longer has all_in_pcm_ceiling: 2200", failed)
            self.assertTrue(all(r["status"] == "skipped"
                                for r in runner.check_workdir(folder, spec, "api")))
            card = runner.score_turn(self.zh["turns"][1], "x", self.zh, workdir=folder, agent="api")
            self.assertFalse([r for r in card["checks"] if r["kind"] == "file" and r["status"] != "skipped"])
            card = runner.score_turn(self.zh["turns"][1], "x", self.zh, workdir=folder, agent="codex")
            self.assertTrue([r for r in card["checks"] if r["kind"] == "file" and r["status"] == "fail"])
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_code_paths_and_links_do_not_count_against_the_language(self):
        reply = ("已更新 [profile.yaml](/private/var/folders/fj/abcdefghijklmnopqrstuvwxyz0123456789/"
                 "vetflat-journey-j9-adjust-settings-by-talking-8cm8n12k/profile.yaml:5)。\n\n"
                 "治安、管理改為 `deep`；其餘軸為 `lite`；全包月上限為 £2,300。驗證結果：`valid`。\n")
        self.assertGreater(runner.cjk_share(reply), 0.2)   # the zh threshold
        stripped = runner.cjk_share(reply)
        naive = len(runner.CJK.findall(reply)) / float(len(reply.replace(' ', '')))
        self.assertGreater(stripped, naive)
        self.assertLess(runner.cjk_share("see https://example.org/a/very/long/path/that/is/not/prose 好"), 1.0)
        self.assertEqual(0.0, runner.cjk_share("```\n中文 in code only\n```"))

    def test_a_busy_provider_is_a_retry_not_a_failed_turn(self):
        self.assertTrue(runner.transient_error("ERROR: Selected model is at capacity. Please try a different model."))
        self.assertTrue(runner.transient_error("HTTP 429 Too Many Requests"))
        self.assertTrue(runner.transient_error("rate_limit_error: overloaded"))
        self.assertFalse(runner.transient_error("the agent exited 1: SyntaxError in the reply"))
        self.assertFalse(runner.transient_error(""))
        self.assertGreaterEqual(runner.MAX_ATTEMPTS, 2)

    def test_reply_yes_to_save_is_a_confirmation_ask(self):
        reply = ("Proposed change:\n\n```diff\n must_haves:\n   - washing_machine_in_flat\n"
                 "+  - EPC rating B or better\n```\n\nThere is no field for an EPC minimum, so it goes "
                 "into must_haves, the nearest thing that exists; the rating governs energy cost, and a flat "
                 "with an exemption cannot pass. Nothing else changes. Reply `yes` to save.\n")
        card = runner.score_turn(self.zh["turns"][2], reply, self.zh)
        by = dict((r["check"], r["status"]) for r in card["checks"])
        self.assertEqual("pass", by["asks before applying anything"])
        self.assertEqual("pass", by["ends_with"])

    def test_nothing_reaches_the_file_before_the_yes(self):
        spec = self.zh["turns"][0]["expect"]["workdir_expect"]
        folder = tempfile.mkdtemp()
        try:
            runner.materialise_attachments(self.zh["turns"][0], folder, "codex")
            self.assertTrue(all(r["status"] == "pass" for r in runner.check_workdir(folder, spec, "codex")))
            with io.open(os.path.join(folder, "profile.yaml"), "a", encoding="utf-8") as fh:
                fh.write("axis_depth:\n  crime: deep\n")
            self.assertTrue(any(r["status"] == "fail" for r in runner.check_workdir(folder, spec, "codex")))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_rent_holding_and_all_in_numbers_are_not_deposit_or_rent_fabrications(self):
        # The shape Codex Luna produced on the listing journey, 2026-09-05: correct numbers
        # that the deposit and rent facts used to read as wrong ones.
        doc = runner.load_journeys()
        j3 = [j for j in doc["journeys"] if j["id"] == "j3-vet-this-listing-zh"][0]
        reply = ("### 最毒的三刀\n\n1. **押金 6 週違規**\n\n月租 £2,350，年租 £28,200，低於 £50,000。\n\n"
                 "- 法定上限：5 週 = **£2,711.54**\n- Listing：6 週 ≈ **£3,253.85**\n- 多收約 **£542.31**\n\n"
                 "2. **Holding deposit 2 週違規**\n\n- 法定上限：1 週 = **£542.31**\n- Listing：2 週 ≈ **£1,084.62**\n\n"
                 "| 10 全包成本 | 低／規劃／壓力情境約 **£2,505／£2,555／£2,630 pcm**。這不是供應商報價。 |\n"
                 "廣告租金 £2,350 pcm；EPC 室內 48 平方米，2019 年首次評估。\n")
        card = runner.score_turn(j3["turns"][0], reply, j3)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["deposit_cap_weeks"]["status"], facts["deposit_cap_weeks"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])
        self.assertEqual("pass", facts["listing_rent_pcm"]["status"], facts["listing_rent_pcm"]["detail"])

    def test_price_per_square_foot_and_the_listing_ask_are_not_fabrications(self):
        doc = runner.load_journeys()
        j3 = [j for j in doc["journeys"] if j["id"] == "j3-vet-this-listing-zh"][0]
        reply = ("廣告租金 £2,350 pcm，EPC 室內 48 平方米，2019 年首次評估。\n"
                 "| 8 價格 | 真實室內價是 £4.55/sq ft，租金是 **£4.55／平方呎** |\n"
                 "廣告要 6 週押金；年租 £28,200，法定上限 5 週。\n"
                 "押金法定上限 5 週 = £2,711.54。\n")
        card = runner.score_turn(j3["turns"][0], reply, j3)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["listing_rent_pcm"]["status"], facts["listing_rent_pcm"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_weeks"]["status"], facts["deposit_cap_weeks"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])

    def test_the_deposit_cap_next_to_the_holding_deposit_is_not_a_holding_fabrication(self):
        doc = runner.load_journeys()
        j1 = doc["journeys"][0]
        self.assertEqual("j1-from-zero-zh", j1["id"])
        one_line = "押金上限 5 週租金；訂金上限 1 週租金。法規 2026-05-01 起。\n"
        card = runner.score_turn(j1["turns"][0], one_line, j1)
        self.assertEqual(0, card["fabrications"], [r["detail"] for r in card["checks"] if r["kind"] == "fact" and r["status"] == "fail"])
        two_lines = "押金上限 5 週租金。\n訂金上限 1 週租金。\n"
        card = runner.score_turn(j1["turns"][0], two_lines, j1)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["holding_deposit_weeks"]["status"], facts["holding_deposit_weeks"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_weeks"]["status"], facts["deposit_cap_weeks"]["detail"])
        self.assertEqual(0, card["fabrications"])

    def test_every_agent_launch_closes_stdin(self):
        # claude -p reads piped stdin as prompt material; a runner started from a heredoc
        # would feed that heredoc to the model (it happened on 2026-09-05).
        for rel in ("bench/journeys.py", "bench/run.py", "bench/ab/run_codex.py"):
            src = read_text(os.path.join(ROOT, rel))
            launches = [m.start() for m in re.finditer(r"subprocess\.Popen\((?:cmd|command), cwd=workdir", src)]
            self.assertTrue(launches, rel)
            for pos in launches:
                self.assertIn("stdin=subprocess.DEVNULL", src[pos:pos + 260], "%s: an agent launch leaves stdin open" % rel)

    def test_multiples_of_the_rent_are_not_a_second_rent(self):
        doc = runner.load_journeys()
        j3 = [j for j in doc["journeys"] if j["id"] == "j3-vet-this-listing-zh"][0]
        reply = ("廣告租金 £2,350 pcm；EPC 室內 48 平方米，2019 年首次評估。\n"
                 "| 預付租金 | 1 個月 = £2,350 | 無英國擔保人者 3 個月 = £7,050 | 多鎖 2 個月租金 £4,700 |\n"
                 "1 週租 = £542.31，two weeks' rent £1,084.62。\n")
        card = runner.score_turn(j3["turns"][0], reply, j3)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["listing_rent_pcm"]["status"], facts["listing_rent_pcm"]["detail"])
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_both_caps_in_one_sentence_and_an_income_multiple(self):
        doc = runner.load_journeys()
        j5 = [j for j in doc["journeys"] if j["id"] == "j5-offer-and-referencing-zh"][0]
        reply = ("月租 £2,150。仲介要求年收入 36 倍月租，即 **£77,400**。\n"
                 "holding deposit 上限約 **£496.15**，租賃押金上限約 **£2,480.77**（2150 × 12 ÷ 52 × 5）。\n")
        card = runner.score_turn(j5["turns"][0], reply, j5)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["holding_deposit_gbp"]["status"], facts["holding_deposit_gbp"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])
        self.assertEqual("pass", facts["rent_pcm"]["status"], facts["rent_pcm"]["detail"])
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_a_landmine_named_in_plain_words_counts_as_named(self):
        doc = runner.load_journeys()
        j7 = [j for j in doc["journeys"] if j["id"] == "j7-compare-two-flats-en"][0]
        turn = j7["turns"][0]
        item = [m for m in turn["expect"]["must"] if m.get("label") == "names the churn landmine"][0]
        self.assertTrue(runner.item_matches("Two of the six reviews mention short-let churn on the floor.", item)[0])
        self.assertTrue(runner.item_matches("Landmine L9 applies.", item)[0])
        self.assertFalse(runner.item_matches("Nothing about the neighbours.", item)[0])
        reply = "Deposit arithmetic: A's maximum five-week deposit is `5 × (£2,250 × 12 ÷ 52)` = £2,596.15; B: £2,423.08.\n"
        card = runner.score_turn(turn, reply, j7)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_one_stay_does_not_borrow_another_stays_numbers(self):
        doc = runner.load_journeys()
        j4 = [j for j in doc["journeys"] if j["id"] == "j4-roast-my-short-stays-en"][0]
        reply = ("| Stay | 30-night price | Cash exposure |\n|---|---:|---:|\n"
                 "| A | `30×£78 + £65 + £315 = £2,720` | £2,720 |\n"
                 "| B | `2×£1,900 = £3,800` rent | £5,700 including £1,900 deposit |\n"
                 "| C | £2,850 | £500 deposit to the operator |\n"
                 "| D | flexible £3,240, or £108/night | non-refundable £2,700, or £90/night |\n\n"
                 "Halcyon Row (Stay D): the flexible rate is £3,240. The non-refundable rate is £2,700, or £90/night.\n"
                 "The non-refundable price is actually £20 below Bramblewick's stated total.\n"
                 "Bramblewick garden studio (Stay A): £78 a night.\n"
                 "Quillon Wharf (Stay C): £500 deposit, paid to the operator.\n")
        card = runner.score_turn(j4["turns"][0], reply, j4)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        for k in ("stay_a_nightly_gbp", "stay_c_deposit_gbp", "stay_d_flexible_total_gbp", "stay_d_nonrefundable_total_gbp"):
            self.assertEqual("pass", facts[k]["status"], (k, facts[k]["detail"]))

    def test_annual_rent_a_difference_the_users_minimum_and_a_balcony_stripped_area_are_not_fabrications(self):
        # The shape Claude Sonnet produced on the area-and-budget journey, 2026-09-05.
        doc = runner.load_journeys()
        j2 = [j for j in doc["journeys"] if j["id"] == "j2-area-and-budget-en"][0]
        turn = j2["turns"][3]
        reply = ("The listing asks £2,050 pcm. Weekly rent = £2,050 × 12 ÷ 52 = **£473.08/wk** (matches their own £473 pw). "
                 "Annual rent = £24,600, under the £50,000 threshold, so the deposit cap is 5 weeks = £2,365.38; the six weeks the listing asks for is £2,838.46.\n"
                 "Rent alone is £150 under your £2,200 ceiling.\n"
                 "| ≥450 sq ft internal | 560 sq ft advertised, balcony included | Pass on paper (~517 sq ft once the balcony is stripped out) |\n"
                 "Rent in advance: at most one month once the tenancy is periodic.\n")
        card = runner.score_turn(turn, reply, j2)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["listing_rent_pcm"]["status"], facts["listing_rent_pcm"]["detail"])
        self.assertEqual("pass", facts["listing_area_sqft"]["status"], facts["listing_area_sqft"]["detail"])
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])

    def test_a_weekly_rent_labelled_rent_is_not_a_second_monthly_rent(self):
        doc = runner.load_journeys()
        j5 = [j for j in doc["journeys"] if j["id"] == "j5-offer-and-referencing-zh"][0]
        reply = "月租 £2,150。週租 = 2,150 × 12 ÷ 52 ≈ 496.15，一週租金 ≈ £496.15；押金上限 5 週 = £2,480.77。\n"
        card = runner.score_turn(j5["turns"][0], reply, j5)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["rent_pcm"]["status"], facts["rent_pcm"]["detail"])
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_a_derived_rent_ceiling_is_not_the_all_in_ceiling_and_the_ceiling_is_not_a_deposit(self):
        doc = runner.load_journeys()
        j1 = doc["journeys"][0]
        turn3 = j1["turns"][2]
        reply = "全部加起來一個月最多 £2,000。扣掉帳單估 £210，租金上限為 **£1,790**。\n"
        card = runner.score_turn(turn3, reply, j1)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["all_in_ceiling_gbp"]["status"], facts["all_in_ceiling_gbp"]["detail"])
        self.assertEqual(0, card["fabrications"])
        turn5 = j1["turns"][4]
        reply = ("月租 £1,850 pcm。押金上限 5 週 = 1,850 × 12 ÷ 52 × 5 = **£2,134.62**。"
                 "你的每月上限 £2,000，含水電 £1,850 剛好在內。\n")
        card = runner.score_turn(turn5, reply, j1)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_a_batch_can_pin_its_results_day(self):
        # A batch that crosses midnight must not scatter its rows over two folders.
        folder = tempfile.mkdtemp()
        try:
            rec = collections.OrderedDict([("journey", "j9-adjust-settings-by-talking#zh"), ("journey_id", "j9-adjust-settings-by-talking"),
                                           ("variant", "zh"), ("agent", "claude"), ("model", "m"), ("run_at", "2026-09-05T23:59:00Z"),
                                           ("journey_score", 1.0), ("fabrications", 0), ("critical_failures", []), ("meets_pass_line", True),
                                           ("completed", True), ("turns_played", 3), ("turns_expected", 3), ("errors", []), ("turn_scores", [])])
            raw_path, jpath = runner.write_results(rec, folder, "2026-09-05")
            self.assertIn(os.path.join(folder, "journeys-2026-09-05"), jpath)
            self.assertEqual(os.path.join(folder, "journeys-2026-09-05"), runner.results_dir(folder, "2026-09-05"))
            code, out = dry_run(["--agent", "api", "--model", "m", "--journey", "j9-adjust-settings-by-talking", "--variant", "zh", "--dry-run", "--day", "2026-09-05"])
            self.assertEqual(0, code)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_richer_replies_from_a_strong_model_do_not_read_as_fabrications(self):
        # Shapes from the Codex Sol runs, 2026-09-06.
        doc = runner.load_journeys()
        by = dict((j["id"], j) for j in doc["journeys"])
        j3 = by["j3-vet-this-listing-zh"]
        card = runner.score_turn(j3["turns"][0], "廣告租金 £2,350 pcm；預付租金 | 3 個月＝£7,050。EPC 48 平方米，2019 年首次評估。\n", j3)
        self.assertEqual(0, card["fabrications"], [r["detail"] for r in card["checks"] if r["kind"] == "fact" and r["status"] == "fail"])
        j4 = by["j4-roast-my-short-stays-en"]
        reply = ("Bramblewick garden studio (Stay A): £78 a night; 30 nights £2,720 (£90.67/night all in).\n"
                 "Halcyon Row (Stay D): £2,700 non-refundable or £3,240 flexible. Non-refundable: £2,700 for the 30 nights.\n")
        card = runner.score_turn(j4["turns"][0], reply, j4)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["stay_d_nonrefundable_total_gbp"]["status"], facts["stay_d_nonrefundable_total_gbp"]["detail"])
        j5 = by["j5-offer-and-referencing-zh"]
        reply = "月租 £2,150。押金上限 5 週 = £2,480.77；仲介要年收入 36 倍月租 £77,400，年租低於 £50,000。\n"
        card = runner.score_turn(j5["turns"][0], reply, j5)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])
        j7 = by["j7-compare-two-flats-en"]
        reply = ("| F1 Deposit | Calculated maximum: A £2,596.15; B £2,423.08. |\n"
                 "| F2 Holding deposit | Found, self-reported: one week. Calculated maximum: A £519.23; B £484.62. |\n"
                 "Both rents are under £50,000 a year.\n")
        card = runner.score_turn(j7["turns"][0], reply, j7)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_cheapest_tier_shapes_bullets_cells_and_a_weekly_rent_are_not_fabrications(self):
        doc = runner.load_journeys(); by = dict((j["id"], j) for j in doc["journeys"])
        j1 = by["j1-from-zero-zh"]
        reply = "押金上限 5 週 = £2,134.62（1,850 × 12 ÷ 52 × 5）。你的每月總預算：\n\n- £2,000\n- 含水電\n"
        card = runner.score_turn(j1["turns"][4], reply, j1)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["deposit_cap_gbp"]["status"], facts["deposit_cap_gbp"]["detail"])
        self.assertEqual(0, card["fabrications"])
        j4 = by["j4-roast-my-short-stays-en"]
        reply = ("| D | £3,240 flexible / £2,700 non-refundable | £150 card pre-authorisation |\n"
                 "Halcyon Row (Stay D): flexible rate £3,240; non-refundable rate £2,700.\n"
                 "The flexible rate is £3,240, or £108/night. The non-refundable rate is £2,700, or £90/night.\n"
                 "Bramblewick garden studio (Stay A): £78 a night.\n")
        card = runner.score_turn(j4["turns"][0], reply, j4)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])
        self.assertEqual("pass", facts["stay_a_nightly_gbp"]["status"], facts["stay_a_nightly_gbp"]["detail"])
        j7 = by["j7-compare-two-flats-en"]
        reply = "Using the current rents: A: weekly rent £519.23; five-week deposit cap £2,596.15; B: weekly rent £484.62; five-week deposit cap £2,423.08.\n"
        card = runner.score_turn(j7["turns"][0], reply, j7)
        facts = dict((r["check"], r) for r in card["checks"] if r["kind"] == "fact")
        self.assertEqual("pass", facts["deposit_caps_gbp"]["status"], facts["deposit_caps_gbp"]["detail"])
        self.assertEqual(0, card["fabrications"], [(k, v["detail"]) for k, v in facts.items() if v["status"] == "fail"])

    def test_the_pasted_profile_becomes_a_real_file_without_its_title_line(self):
        folder = tempfile.mkdtemp()
        try:
            self.assertEqual(["profile.yaml"],
                             runner.materialise_attachments(self.zh["turns"][0], folder, "claude"))
            with io.open(os.path.join(folder, "profile.yaml"), encoding="utf-8") as fh:
                text = fh.read()
            self.assertTrue(text.startswith("flat_type: one_bed"), text[:80])
            self.assertIn("all_in_pcm_ceiling: 2200", text)
            self.assertEqual([], runner.materialise_attachments(self.zh["turns"][0], folder, "api"))
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_shell_journeys_get_the_validator_and_manual_ones_read_only(self):
        self.assertEqual("workspace-write", runner.codex_sandbox(self.j9))
        self.assertEqual("read-only", runner.codex_sandbox(self.j1))
        self.assertIn("profile_check.py", runner.claude_tools(self.j9))
        self.assertEqual("Read", runner.claude_tools(self.j1))
        code, out = dry_run(["--agent", "codex", "--journey", self.j9["id"], "--variant", "zh",
                             "--dry-run"])
        self.assertEqual(0, code)
        self.assertIn("--sandbox workspace-write", out)
        self.assertNotIn("network_access", out)
        self.assertIn("writes profile.yaml", out)
        code, out = dry_run(["--agent", "claude", "--journey", self.j9["id"], "--variant", "zh",
                             "--dry-run", "--session-mode", "replay"])
        self.assertEqual(0, code)
        self.assertIn("profile_check.py", out)
        for flag in BYPASS_FLAGS:
            self.assertNotIn(flag, out)

    def test_regrade_rescores_stored_replies_and_keeps_file_rows(self):
        folder = tempfile.mkdtemp()
        try:
            raw = os.path.join(folder, "raw")
            os.makedirs(raw)
            good = read_json(GOOD_REPLIES)["replies"]
            turns = []
            for index in (1, 2, 3):
                reply = good["j9-adjust-settings-by-talking#zh|%d" % index]
                card = runner.score_turn(self.zh["turns"][index - 1], reply, self.zh)
                card.update(turn=index, reply=reply, user="u", note=None, wall_time_s=1.0, usage=None)
                turns.append(card)
            turns[1]["checks"] = ([r for r in turns[1]["checks"] if r["kind"] != "file"] +
                                  [runner.row("profile.yaml contains crime: deep", "file", "pass",
                                              "found in the file")])
            rec = collections.OrderedDict([
                ("journey", "j9-adjust-settings-by-talking#zh"),
                ("journey_id", "j9-adjust-settings-by-talking"), ("variant", "zh"),
                ("title", "t"), ("agent", "claude"), ("model", "m"),
                ("run_at", "2026-09-05T00:00:00Z"), ("errors", []), ("turn_scores", turns)])
            name = "claude-j9-adjust-settings-by-talking#zh-1.json"
            with io.open(os.path.join(raw, name), "w", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, runner.regrade(folder))
            rows = read_json(os.path.join(folder, "scorecard.json"))
            self.assertEqual(1, len(rows))
            self.assertEqual(1.0, rows[0]["journey_score"])
            self.assertTrue(rows[0]["meets_pass_line"])
            self.assertIn("regraded_at", rows[0])
            self.assertTrue(os.path.exists(os.path.join(folder, "scorecard.md")))
            back = read_json(os.path.join(raw, name))
            files = [(r["check"], r["status"]) for r in back["turn_scores"][1]["checks"]
                     if r["kind"] == "file"]
            self.assertEqual([("profile.yaml contains crime: deep", "pass")], files)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

