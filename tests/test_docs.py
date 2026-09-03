"""Guards for the human-facing contract: SKILL.md size, onboarding coverage, profile fields."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "skills", "vet-flat")


def read(*parts):
    return open(os.path.join(SKILL, *parts), encoding="utf-8").read()


class TestSkillMd(unittest.TestCase):
    def test_under_prompt_pack_limit(self):
        s = read("SKILL.md")
        self.assertLess(len(s), 8000, "SKILL.md must stay under 8,000 characters (ChatGPT Projects limit)")

    def test_portable_frontmatter_only(self):
        fm = re.search(r"^---\n(.*?)\n---", read("SKILL.md"), re.S).group(1)
        keys = {line.split(":")[0].strip() for line in fm.splitlines() if line and not line.startswith(" ")}
        self.assertTrue(keys <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}, keys)

    def test_capability_answer_section(self):
        s = read("SKILL.md")
        self.assertIn('what can this do', s)
        self.assertIn("references/onboarding.md", s)
        self.assertIn("Never", s)


class TestOnboarding(unittest.TestCase):
    def test_sections_and_languages(self):
        s = read("references", "onboarding.md")
        for h in ["## 1. The pitch", "## 2. Intake", "## 3. Primer", "## 4. Short answers"]:
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


class TestProfileTemplate(unittest.TestCase):
    def test_new_fields(self):
        s = read("profile.template.yaml")
        for key in ["flat_type:", "separate_bedroom_required:", "experience:", "avoid:", "priorities:",
                    "all_in_pcm_ceiling:", "destination:", "guarantor_route:"]:
            self.assertIn(key, s)


if __name__ == "__main__":
    unittest.main()
