# -*- coding: utf-8 -*-
"""scripts/living_env.py: the living-environment deciles from the 2025 indices, nothing about people.

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen -
https://github.com/jacky18008/pea-princess - CC BY 4.0

The fixture is three real rows of File 7 (English Indices of Deprivation 2025, OGL v3):
Enfield 022C (middle), Camden 014A (worst tenth outdoors), Bromley 039B (best tenth outdoors).
"""
from __future__ import unicode_literals

import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "skills", "vet-flat", "scripts")
FIX = os.path.join(HERE, "fixtures", "living_env-file7-sample.csv")
sys.path.insert(0, SCRIPTS)
import living_env as LE  # noqa: E402


class TestReadingTheTable(unittest.TestCase):
    def test_columns_are_found_by_heading_not_position(self):
        header, row = LE.find_row(FIX, "E01001567")
        out = LE.parse_row(header, row)
        self.assertEqual("Enfield 022C", out["lsoa"]["name"])
        self.assertEqual("Enfield", out["lsoa"]["local_authority"])
        self.assertEqual(4, out["living_environment"]["decile"])
        self.assertEqual(11026, out["living_environment"]["rank"])
        self.assertAlmostEqual(26.854, out["living_environment"]["score"])
        self.assertEqual(4, out["indoors"]["decile"])
        self.assertEqual(4, out["outdoors"]["decile"])
        self.assertEqual(33755, out["outdoors"]["of"])

    def test_the_two_halves_say_what_they_measure(self):
        header, row = LE.find_row(FIX, "E01000843")
        out = LE.parse_row(header, row)
        self.assertIn("quality of housing", out["indoors"]["measures"])
        self.assertIn("air quality and road traffic accidents", out["outdoors"]["measures"])
        self.assertEqual(1, out["outdoors"]["decile"])
        self.assertIn("most deprived fifth", out["outdoors"]["reading"])

    def test_readings_across_the_deciles(self):
        self.assertIn("most deprived fifth", LE.reading(1))
        self.assertIn("most deprived fifth", LE.reading(2))
        self.assertEqual("below the middle", LE.reading(3))
        self.assertEqual("around the middle", LE.reading(5))
        self.assertEqual("above the middle", LE.reading(8))
        self.assertIn("least deprived fifth", LE.reading(10))
        self.assertEqual("unknown", LE.reading(None))

    def test_an_area_missing_from_the_table_is_reported_not_guessed(self):
        out = LE.lookup(lsoa="W01000001", csv_path=FIX)
        self.assertFalse(out["ok"])
        self.assertIn("not in the 2025 table", out["note"])
        self.assertNotIn("outdoors", out)


class TestNothingAboutPeople(unittest.TestCase):
    """The user's rule (2026-09-11): the living environment, never income or who lives there."""

    def test_no_income_employment_health_or_crime_field_is_printed(self):
        out = LE.lookup(lsoa="E01000655", csv_path=FIX)
        self.assertTrue(out["ok"])
        blob = json.dumps(out).lower()
        for word in ("income", "employment", "idaci", "idaopi", "health deprivation", "crime decile",
                     "education, skills", "barriers to housing"):
            self.assertNotIn(word, blob, word)
        self.assertEqual(10, out["outdoors"]["decile"])
        self.assertIn("never a filter", out["how_to_use"])

    def test_the_module_never_names_an_income_column(self):
        with io.open(os.path.join(SCRIPTS, "living_env.py"), encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("Income Decile", source)
        self.assertNotIn("IDACI", source)


class TestCli(unittest.TestCase):
    def test_lookup_by_code_with_a_local_table_prints_one_json_object(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "living_env.py"), "lookup",
                               "--lsoa", "E01000843", "--csv", FIX], capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual("G", out["evidence_class"])
        self.assertEqual("Open Government Licence v3.0", out["licence"])
        self.assertEqual("Camden 014A", out["lsoa"]["name"])
        self.assertEqual(1, out["living_environment"]["decile"])

    def test_no_arguments_is_a_usage_error(self):
        proc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "living_env.py"), "lookup"],
                              capture_output=True, text=True)
        self.assertEqual(2, proc.returncode)


if __name__ == "__main__":
    unittest.main()
