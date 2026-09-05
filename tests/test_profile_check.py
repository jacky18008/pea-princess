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


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        fh.write(text); path = fh.name
    p = subprocess.run([sys.executable, CHECK, path, "--json"], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


class TestProfileCheck(unittest.TestCase):
    def test_shipped_profiles_are_valid(self):
        for name in os.listdir(os.path.join(ROOT, "skills", "vet-flat", "profiles")):
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

    def test_forbidden_content(self):
        code, res = run("story_summary: prefers a landlord of a certain nationality\n")
        self.assertEqual(code, 1)
        self.assertTrue(any("nationality" in e for e in res["errors"]))


if __name__ == "__main__":
    unittest.main()
