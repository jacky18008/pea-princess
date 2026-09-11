"""Guards for the human-facing contract: SKILL.md size, onboarding coverage, profile fields."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "skills", "vet-flat")


def read(*parts):
    return open(os.path.join(SKILL, *parts), encoding="utf-8").read()


class TestSkillMd(unittest.TestCase):
    def test_under_prompt_pack_limit(self):
        s = read("SKILL.md")
        self.assertLess(len(s), 10000, "SKILL.md is a router; keep it under 10,000 characters")

    def test_prompt_pack_instructions_fit(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_dist", os.path.join(HERE, "..", "tools", "build_dist.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        text = mod.compose_instructions()
        self.assertLessEqual(len(text), 8000, "the prompt-pack INSTRUCTIONS.md must fit ChatGPT Projects (8,000 chars)")
        self.assertIn("Manual-mode digest", text)

    def test_the_prompt_pack_carries_the_eighteen_fixed_questions(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_dist", os.path.join(HERE, "..", "tools", "build_dist.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        text = mod.compose_instructions()
        for i in range(1, 19):
            self.assertIn("F%d " % i, text, "F%d is missing from the manual-mode digest" % i)
        for state in ("found", "asked", "unknown"):
            self.assertIn(state, text, state)
        self.assertIn("fixed-questions.yaml", text)
        # The three tiers and the knob that overrides them travel with the pack too.
        for needle in ("lite 8", "standard 14", "deep 18", "advanced.fixed_form"):
            self.assertIn(needle, text, needle)
        # Never at the cost of the digest that tells a model how to ask for what it lacks.
        self.assertIn("## Rules for asking", text)

    def test_the_fixed_form_digest_stays_compact(self):
        s = read("references", "report-contract.md")
        block = s[s.index("## The fixed form"):s.index("## Plain-language rules")].strip()
        self.assertLessEqual(len(block) + 1, 560,
                             "the digest is copied into the prompt pack; keep it under 560 chars")

    def test_the_fixed_form_is_a_rule_that_never_bends(self):
        s = read("SKILL.md")
        block = s[s.index("## Rules that never bend"):s.index("## Output")]
        self.assertIn("references/fixed-questions.yaml", block)
        self.assertIn("scripts/scan.py", block)
        for word in ("found", "asked", "unknown"):
            self.assertIn(word, block, word)
        # Eight, fourteen or eighteen by depth, and the user's own setting wins.
        for word in ("eight", "fourteen", "eighteen", "budget mode", "advanced.fixed_form"):
            self.assertIn(word, block, word)

    def test_portable_frontmatter_only(self):
        fm = re.search(r"^---\n(.*?)\n---", read("SKILL.md"), re.S).group(1)
        keys = {line.split(":")[0].strip() for line in fm.splitlines() if line and not line.startswith(" ")}
        self.assertTrue(keys <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}, keys)

    def test_capability_answer_section(self):
        s = read("SKILL.md")
        self.assertIn("what this does", s)
        self.assertIn("references/onboarding.md", s)
        self.assertIn("Never", s)
        self.assertIn("Route by intent", s)


class TestOnboarding(unittest.TestCase):
    def test_sections_and_languages(self):
        s = read("references", "onboarding.md")
        for h in ["## 1. The pitch", "## 2. Start with at most three essential clarifications",
                  "## 3. Primer", "## 4. Short answers"]:
            self.assertIn(h, s)
        for lang in ["**English**", "**繁體中文**", "**简体中文**"]:
            self.assertIn(lang, s)
        self.assertIn("2026-05-01", s)
        self.assertIn("five weeks", s)
        self.assertNotIn("Rightmove scraping", s)

    def test_deal_breaker_menu_maps_to_landmines(self):
        s = read("references", "onboarding.md")
        for code in ["L1", "L2", "L4", "L5", "L6", "L7", "L9", "L10", "L11", "L12"]:
            self.assertIn(code, s)


class TestQuestionBank(unittest.TestCase):
    def test_every_landmine_has_a_question(self):
        s = read("references", "questions.md")
        for code in ["G1", "G2", "G3", "G4"] + [f"L{i}" for i in range(1, 13)]:
            self.assertIn(f"| {code} |", s, code)
        self.assertIn("two questions at most", s)


class TestBudgetModes(unittest.TestCase):
    def test_modes_documented_and_wired(self):
        s = read("references", "budget-modes.md")
        for m in ["`lite`", "`standard`", "`deep`"]:
            self.assertIn(m, s)
        self.assertIn("budget_mode: standard", read("profile.template.yaml"))
        self.assertIn("budget-modes.md", read("SKILL.md"))


class TestProfileTemplate(unittest.TestCase):
    def test_new_fields(self):
        s = read("profile.template.yaml")
        for key in ["flat_type:", "separate_bedroom_required:", "experience:", "avoid:", "priorities:",
                    "all_in_pcm_ceiling:", "destination:", "guarantor_route:",
                    "story_summary:", "story_taken_on:", "my_questions:"]:
            self.assertIn(key, s)

    def test_the_story_fields_say_what_may_not_go_in_them(self):
        s = read("profile.template.yaml")
        block = s[s.index("story_summary") - 900:s.index("story_taken_on")]
        self.assertIn("never the stories themselves", block.lower().replace("preferences, never", "never"))
        for forbidden in ("health", "nationality", "religion", "immigration status"):
            self.assertIn(forbidden, block)
        for blank in ("story_summary:", "story_taken_on:"):
            self.assertIn("\n" + blank + "\n", s, "%s must be left blank in the template" % blank)

    def test_my_questions_documents_the_stages_the_kinds_and_the_two_examples(self):
        s = read("profile.template.yaml")
        block = s[s.index("# The questions you always ask"):s.index("# Your top three priorities")]
        for stage in ("filter", "vet", "compare", "viewing", "sign"):
            self.assertIn(stage, block, stage)
        for kind in ("answer", "ask", "check"):
            self.assertIn(kind, block, kind)
        self.assertIn("Cheap has a reason", block)
        self.assertIn("am I buying visible value", block)
        self.assertIn("trigger:", block)
        self.assertIn("price below the local band by 10% or more", block)
        self.assertIn("price above the local band", block)
        self.assertIn("must answer EVERY question here", block)


class TestStoryIntake(unittest.TestCase):
    """The five-minute story session in onboarding.md section 2b."""

    def setUp(self):
        self.s = read("references", "onboarding.md")
        self.section = self.s[self.s.index("## 2b."):self.s.index("## 3. Primer")]

    def test_the_section_is_there_and_says_it_is_optional(self):
        self.assertIn("## 2b. Tell me about the places you have lived (optional, 5 minutes)", self.s)
        self.assertIn("dictation", self.section)
        self.assertIn("voice memo", self.section)

    def test_it_names_at_most_two_dictation_apps_and_says_any_works(self):
        offer = self.section[self.section.index("Say it roughly"):self.section.index("Any transcript")]
        self.assertIn("any of them works", offer)
        named = [app for app in ("Otter", "Notta", "Whisper", "Dragon", "Rev", "Descript")
                 if app in offer]
        self.assertLessEqual(len(named), 2, "name at most two dictation apps: %s" % named)

    def test_it_listens_for_the_good_the_bad_and_the_money(self):
        for signal in ("light", "quiet", "kitchen", "neighbours", "management", "location habits",
                       "damp", "noise", "landlord", "bill shocks", "commute", "Money attitudes",
                       "shops"):
            self.assertIn(signal, self.section, signal)

    def test_every_story_element_lands_in_a_profile_field(self):
        for field in ("`avoid`", "`priorities`", "`must_haves`", "`nice_to_haves`",
                      "quiet_over_light", "light.reject_no_sky", "floors.reject_ground_floor",
                      "budget.stretch_ceiling_and_conditions", "`my_questions`"):
            self.assertIn(field, self.section, field)
        for code in ("L2", "L4", "L5", "L6", "L7", "L9", "L10", "L11"):
            self.assertIn("| " + code + " |", self.section, code)

    def test_the_stories_themselves_are_never_stored(self):
        self.assertIn("Never store the stories", self.section)
        self.assertIn("Do not save the transcript", self.section)
        for forbidden in ("ethnicity", "nationality", "religion", "health", "immigration status"):
            self.assertIn(forbidden, self.section, forbidden)
        self.assertIn("Do not diagnose", self.section)

    def test_the_write_back_is_three_sentences_and_needs_a_yes(self):
        self.assertIn("exactly three sentences", self.section)
        self.assertIn("story_summary", self.section)
        self.assertIn("story_taken_on", self.section)
        self.assertIn("Shall I save these?", self.section)

    def test_the_worked_example_is_six_lines_in_and_eight_lines_out(self):
        example = self.section[self.section.index("### Worked example"):]
        transcript = [line for line in example.split("```diff")[0].splitlines()
                      if line.startswith("> The") or line.startswith("> I ") or
                      line.startswith("> One")]
        self.assertEqual(len(transcript), 6, "the story is meant to be six lines")
        diff = example.split("```diff")[1].split("```")[0]
        self.assertEqual(len([line for line in diff.splitlines() if line.startswith("+")]), 8,
                         "the worked example is meant to change eight lines")
        self.assertIn("(fictional)", self.section)

    def test_recurring_personal_questions_are_offered_and_classified(self):
        recurring = self.section[self.section.index("### Recurring personal questions"):]
        self.assertIn("Are there questions you always ask of every place?", recurring)
        for word in ("compare", "filter", "viewing", "vet", "ask", "check", "trigger"):
            self.assertIn(word, recurring, word)
        self.assertIn("let\nthem correct it", recurring.replace("  ", " "))


class TestSharing(unittest.TestCase):
    """The seed: references/sharing.md, seed-format.md and seed-schema.json."""

    def setUp(self):
        self.sharing = read("references", "sharing.md")
        self.fmt = read("references", "seed-format.md")

    def test_the_headings_cover_the_card_the_code_and_the_import(self):
        for heading in ["# Sharing a seed: the card, the code, the import",
                        "## 1. When the user asks",
                        "## 2. What is shared, in plain words",
                        "## 3. Share your questions",
                        "## 4. The social post, ready to send",
                        "## 5. `journey.json` — the record of one search",
                        "## 6. Importing somebody else's seed"]:
            self.assertIn(heading, self.sharing, heading)

    def test_it_names_the_triggers_in_three_languages(self):
        for trigger in ("share my seed", "分享我的設定檔", "分享我的设置"):
            self.assertIn(trigger, self.sharing, trigger)

    def test_the_social_post_is_written_in_three_languages(self):
        post = self.sharing[self.sharing.index("## 4. The social post"):
                            self.sharing.index("## 5. `journey.json`")]
        for lang in ("**English**", "**繁體中文**", "**简体中文**"):
            self.assertIn(lang, post, lang)
        self.assertIn("I found a flat in London with this Pea Princess seed", post)
        self.assertEqual(post.count("PP1."), 3, "each post carries the code")

    def test_it_distinguishes_excluded_fields_from_free_text_privacy(self):
        for shared in ("band", "district", "month", "deal-breakers", "must-haves", "priorities"):
            self.assertIn(shared, self.sharing, shared)
        for never in ("address", "income", "savings", "guarantor route", "introduction",
                      "exact dates", "health"):
            self.assertIn(never, self.sharing, never)
        for boundary in ("does not anonymize arbitrary text", "Base64url is not encryption",
                         "complete card and decoded code", "A postcode scrub is not an identity scrub"):
            self.assertIn(boundary, self.sharing)

    def test_it_tells_the_agent_what_to_do_with_and_without_a_shell(self):
        self.assertIn("scripts/seed.py export", self.sharing)
        self.assertIn("Without a shell", self.sharing)
        self.assertIn("references/seed-format.md", self.sharing)

    def test_it_describes_the_journey_file(self):
        journey = self.sharing[self.sharing.index("## 5. `journey.json`"):]
        for key in ("started", "profile_seed", "candidates", "label", "verdict", "tier", "date",
                    "chosen", "area_m2", "floor", "all_in_band", "notes", "--reveal-address"):
            self.assertIn(key, journey, key)
        self.assertIn("no address", journey)

    def test_the_questions_are_encouraged_and_the_stages_explained(self):
        block = self.sharing[self.sharing.index("## 3. Share your questions"):
                             self.sharing.index("## 4. The social post")]
        self.assertIn("Cheap has a reason", block)
        self.assertIn("steal other people's", block)
        for stage in ("`filter`", "`vet`", "`compare`", "`viewing`", "`sign`"):
            self.assertIn(stage, block, stage)
        for kind in ("`answer`", "`ask`", "`check`"):
            self.assertIn(kind, block, kind)
        self.assertIn("Triggers are not shared", block)

    def test_the_format_reference_is_model_followable(self):
        self.assertIn("PP1.", self.fmt)
        self.assertIn("base64url", self.fmt)
        for key in ("`v`", "`n`", "`t`", "`b`", "`m`", "`c`", "`w`", "`mh`", "`av`", "`pr`",
                    "`qs`", "`fl`", "`li`", "`q`", "`fw`", "`s`"):
            self.assertIn("| " + key + " |", self.fmt, key)
        self.assertIn("worked example", self.fmt.lower())
        self.assertIn("83 bytes", self.fmt)

    def test_the_seed_schema_is_valid_json_and_matches_the_script(self):
        import json
        schema = json.loads(read("references", "seed-schema.json"))
        sys.path.insert(0, os.path.join(HERE, "..", "skills", "vet-flat", "scripts"))
        import seed as seed_script
        self.assertEqual(sorted(schema["properties"]),
                         sorted(["v"] + [short for _, short in seed_script.ALLOW]))
        self.assertIn("journey", schema["definitions"])
        self.assertEqual(schema["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main()


class TestNoLinkFetching(unittest.TestCase):
    """A listing link is never an input the skill acts on: the host would fetch it, and that
    is the automated access the skill's terms position rules out (2026-09-11). The person
    hands over the page text or a saved copy; a link is answered with the one sentence."""

    def _skill_texts(self):
        out = {}
        for folder, _dirs, files in os.walk(SKILL):
            for name in files:
                if name.endswith((".md", ".yaml", ".yml")):
                    path = os.path.join(folder, name)
                    out[os.path.relpath(path, SKILL)] = open(path, encoding="utf-8").read()
        return out

    def test_no_skill_text_asks_for_a_link(self):
        bad = re.compile(r"(?i)\b(paste|send|share|give me|drop|post)\s+(me\s+)?(the\s+|a\s+|your\s+)?(link|url)s?\b"
                         r"|\b(link|url) or (the )?(page|text)\b|貼(上)?(網址|連結)")
        hits = ["%s: %s" % (rel, m.group(0)) for rel, text in self._skill_texts().items()
                for m in bad.finditer(text)]
        self.assertEqual([], hits, hits)

    def test_the_router_says_a_link_is_never_opened(self):
        s = read("SKILL.md")
        self.assertIn("A listing link is never opened", s)
        self.assertIn("fetch/browser tool", s)
        self.assertIn("never read by skill or host tools", s)

    def test_the_menu_asks_for_the_page_not_the_link(self):
        s = read("references", "onboarding.md")
        line = [l for l in s.splitlines() if l.startswith("1. **I have a listing**")][0]
        self.assertIn("copy the page text", line)
        self.assertIn("not the link", line)

    def test_the_one_sentence_rule_covers_fetch_tools_and_alert_emails(self):
        s = read("references", "listing-fields.md")
        self.assertIn("not with a fetch tool, a browser tool or curl", s)
        self.assertIn("The links inside it are not opened either", s)
