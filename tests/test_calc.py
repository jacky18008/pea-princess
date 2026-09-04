"""Arithmetic helpers must be exact (run: python3 -m unittest tests/test_calc.py)."""
import json
import os
import subprocess
import sys
import unittest

CALC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "vet-flat", "scripts", "calc.py")


def run(*args):
    out = subprocess.run([sys.executable, CALC] + list(args), capture_output=True, text=True, check=True).stdout
    return json.loads(out)["result"]


class TestCalc(unittest.TestCase):
    def test_deposit_cap_five_weeks(self):
        r = run("deposit", "--rent-pcm", "2400")
        self.assertEqual(r["deposit_cap_weeks"], 5)
        self.assertAlmostEqual(r["weekly_rent"], 553.85, places=2)
        self.assertAlmostEqual(r["max_deposit"], 2769.23, places=2)
        self.assertAlmostEqual(r["max_holding_deposit"], 553.85, places=2)

    def test_deposit_cap_six_weeks_at_50k(self):
        self.assertEqual(run("deposit", "--rent-pcm", "4200")["deposit_cap_weeks"], 6)

    def test_affordability(self):
        r = run("affordability", "--rent-pcm", "2400", "--multiple", "2.5", "--income", "65000", "--guarantor-multiple", "4")
        self.assertEqual(r["required_income"], 72000.0)
        self.assertFalse(r["passes"])
        self.assertEqual(r["guarantor_required_income_or_savings"], 115200.0)
        self.assertAlmostEqual(r["max_rent_pcm_for_income"], 2166.67, places=2)

    def test_all_in_and_break_even(self):
        r = run("all-in", "--rent-pcm", "2400", "--bills-low", "125", "--bills-planning", "175", "--bills-stress", "250", "--council-tax", "0", "--broadband", "30")
        self.assertEqual((r["all_in_low"], r["all_in_planning"], r["all_in_stress"]), (2555.0, 2605.0, 2680.0))
        self.assertEqual(run("break-even", "--ceiling", "2600", "--bills-planning", "175")["max_rent_pcm"], 2425.0)

    def test_price_per_sqft(self):
        r = run("price-per-sqft", "--rent-pcm", "2400", "--area-m2", "52")
        self.assertAlmostEqual(r["area_sqft"], 559.72, places=2)
        self.assertAlmostEqual(r["gbp_per_sqft"], 4.29, places=2)

    def test_bridge_not_an_addon(self):
        r = run("bridge", "--weeks", "7.7", "--weekly", "500", "--months", "10.2", "--all-in", "1995", "--alt-all-in", "2175", "--alt-months", "12")
        self.assertAlmostEqual(r["total"], 24199.0, places=0)
        self.assertLess(r["difference"], 0)

    def test_guarantor_products(self):
        one = run("guarantor-product", "--rent-pcm", "2400", "--model", "oneoff", "--fee-months", "1")
        self.assertEqual(one["total_cost"], 2400.0)
        ann = run("guarantor-product", "--rent-pcm", "2400", "--model", "annual", "--weeks", "3", "--setup", "59.99", "--years", "1")
        self.assertAlmostEqual(ann["annual_premium"], 1661.54, places=2)
        self.assertAlmostEqual(ann["total_cost"], 1721.53, places=2)

    def test_pro_rata_and_pct(self):
        r = run("pro-rata", "--rent-pcm", "3000", "--move-in", "2026-09-18")
        self.assertEqual((r["days_in_month"], r["days_charged"]), (30, 13))
        self.assertEqual(r["first_month_rent"], 1300.0)
        self.assertAlmostEqual(run("pct-diff", "--a", "2400", "--b", "2200")["pct"], 9.09, places=2)


if __name__ == "__main__":
    unittest.main()
