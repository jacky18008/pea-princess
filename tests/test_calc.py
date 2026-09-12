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


class TestArithmetic(unittest.TestCase):
    def test_observed_multiple_differences_work_with_and_without_subcommand(self):
        expressions = ('2300 - 2250', '2300 - 1800', '484 - 342', '2250 - 1800', '61.5 - 57.2')
        for prefix in ((), ('arithmetic',)):
            with self.subTest(prefix=prefix):
                rows = run(*(prefix + expressions))
                self.assertEqual(['50', '500', '142', '450', '4.3'], [row['result'] for row in rows])
                self.assertEqual(list(expressions), [row['expression'] for row in rows])
                self.assertTrue(all(not row['rounded'] for row in rows))

    def test_decimal_precedence_parentheses_negatives_and_rounding(self):
        rows = run('arithmetic', '0.1 + 0.2', '(10 - 2) * 3 / 4', '-2 + 1', '1 / 3')
        self.assertEqual(['0.3', '6', '-1'], [row['result'] for row in rows[:3]])
        self.assertTrue(rows[3]['rounded'])
        self.assertEqual('0.' + '3' * 50, rows[3]['result'])

    def test_code_nonfinite_unsupported_operators_and_zero_division_are_rejected(self):
        for expression in ('__import__("os").getcwd()', 'x+1', '(1).__class__', 'NaN', 'Infinity', '1e999',
                           '2**3', '5//2', '5%2', '1/0', 'True+1', '[1][0]', '1;2', '1_000+2'):
            with self.subTest(expression=expression):
                proc = subprocess.run([sys.executable, CALC, 'arithmetic', expression], capture_output=True, text=True)
                self.assertEqual(2, proc.returncode, proc.stdout + proc.stderr)
                self.assertIn('error', json.loads(proc.stdout))
                self.assertNotIn('result', json.loads(proc.stdout))

    def test_resource_bounds_and_atomic_batch_failure(self):
        batches = [('1+' * 130 + '1',), ('-' * 26 + '1',), ('9' * 33,), ('1' + '0'*25,),
                   ('1',)*17, ('2+3','1/0')]
        for batch in batches:
            with self.subTest(batch=batch):
                proc = subprocess.run([sys.executable, CALC, 'arithmetic', *batch], capture_output=True, text=True)
                self.assertEqual(2, proc.returncode)
                self.assertNotIn('result', json.loads(proc.stdout))


if __name__ == "__main__":
    unittest.main()
