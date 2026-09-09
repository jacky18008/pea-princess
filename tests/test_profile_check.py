"""profile_check.py: the validator that catches invented fields and bad values."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CHECK = os.path.join(ROOT, "skills", "vet-flat", "scripts", "profile_check.py")
sys.path.insert(0, os.path.dirname(CHECK))
import profile_check


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        fh.write(text); path = fh.name
    p = subprocess.run([sys.executable, CHECK, path, "--json"], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


class TestProfileCheck(unittest.TestCase):
    def test_wrong_numeric_types_cannot_bypass_hard_constraint_validation(self):
        for dotted in profile_check.RANGES:
            for value in ("2100", "unlimited", True, [], float("inf"), float("nan")):
                with self.subTest(field=dotted, value=value):
                    profile = {}
                    node = profile
                    parts = dotted.split(".")
                    for key in parts[:-1]:
                        node = node.setdefault(key, {})
                    node[parts[-1]] = value
                    errors, _ = profile_check.check(profile)
                    self.assertTrue(any(dotted in error for error in errors), errors)

    def test_non_mapping_settings_are_invalid_without_crashing(self):
        for profile in ([], "budget: 2100", True, {"budget": "unlimited"},
                        {"limits": [100]}, {"axis_depth": "deep"}):
            with self.subTest(profile=profile):
                errors, _ = profile_check.check(profile)
                self.assertTrue(errors)

    def test_shipped_profiles_are_valid(self):
        for name in sorted(os.listdir(os.path.join(ROOT, "skills", "vet-flat", "profiles"))):
            if not name.endswith(".yaml"):
                continue  # seed cards (*.seed.md) live beside the profiles; only YAML is a profile
            p = subprocess.run([sys.executable, CHECK, os.path.join(ROOT, "skills", "vet-flat", "profiles", name)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, name + ": " + p.stdout)

    def test_invented_field_and_bad_enum(self):
        code, res = run("flat_type: mansion\nbudget_mode: turbo\nfavourite_colour: blue\n")
        self.assertEqual(code, 1)
        joined = " ".join(res["errors"])
        self.assertIn("favourite_colour", joined); self.assertIn("flat_type", joined); self.assertIn("budget_mode", joined)

    def test_rent_above_ceiling_and_axis_depth(self):
        code, res = run("budget:\n  rent_pcm_target: 2500\n  all_in_pcm_ceiling: 2000\naxis_depth:\n  crime: deep\n  vibes: lite\n")
        self.assertEqual(code, 1)
        joined = " ".join(res["errors"])
        self.assertIn("above the all-in ceiling", joined); self.assertIn("vibes", joined)

    def test_the_template_including_its_advanced_block_is_valid(self):
        tpl = os.path.join(ROOT, "skills", "vet-flat", "profile.template.yaml")
        p = subprocess.run([sys.executable, CHECK, tpl], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        with open(tpl, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("advanced:", text)
        self.assertIn("questions: auto", text)
        self.assertIn("ask_if_missing: gate", text)

    def test_the_advanced_block_accepts_every_documented_value(self):
        for questions in ("auto", "gate", "standard", "full"):
            for ask in ("gate", "all", "none"):
                code, res = run("advanced:\n  fixed_form:\n    questions: %s\n    ask_if_missing: %s\n"
                                % (questions, ask))
                self.assertEqual(code, 0, res["errors"])

    def test_a_bad_value_in_the_advanced_block_is_named(self):
        code, res = run("advanced:\n  fixed_form:\n    questions: everything\n    ask_if_missing: sometimes\n")
        self.assertEqual(code, 1)
        joined = " ".join(res["errors"])
        self.assertIn("advanced.fixed_form.questions", joined)
        self.assertIn("advanced.fixed_form.ask_if_missing", joined)
        self.assertIn("full", joined)

    def test_an_invented_key_under_advanced_is_refused(self):
        code, res = run("advanced:\n  fixed_form:\n    questions: gate\n    how_many: 9\n")
        self.assertEqual(code, 1)
        self.assertTrue(any("how_many" in e for e in res["errors"]), res["errors"])
        code, res = run("advanced:\n  turbo_mode:\n    on: true\n")
        self.assertEqual(code, 1)
        self.assertTrue(any("turbo_mode" in e for e in res["errors"]), res["errors"])

    def test_forbidden_content(self):
        code, res = run("story_summary: prefers a landlord of a certain nationality\n")
        self.assertEqual(code, 1)
        self.assertTrue(any("nationality" in e for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
