#!/usr/bin/env python3
"""Deterministic arithmetic for renting decisions. Models must not do this in their heads.

Every subcommand prints JSON with `inputs`, `formula`, `steps` and `result`, so the report can
quote the working. England rules (Tenant Fees Act 2019; Renters' Rights Act 2025 from 2026-05-01):
deposit cap 5 weeks' rent when annual rent < £50,000 (6 weeks at or above), holding deposit cap
1 week, rent in advance at most 1 month. Weekly rent = monthly rent × 12 ÷ 52.

Usage:
  calc.py deposit --rent-pcm 2400
  calc.py affordability --rent-pcm 2400 --multiple 2.5 [--income 65000] [--guarantor-multiple 4]
  calc.py all-in --rent-pcm 2400 --bills-low 125 --bills-planning 175 --bills-stress 250 [--council-tax 0] [--broadband 30]
  calc.py price-per-sqft --rent-pcm 2400 --area-m2 52
  calc.py bridge --weeks 7.7 --weekly 500 --months 10.2 --all-in 2170 [--alt-all-in 2175 --alt-months 12]
  calc.py break-even --ceiling 2600 --bills-planning 175 [--council-tax 0]
  calc.py guarantor-product --rent-pcm 2400 --model oneoff --fee-months 1
  calc.py guarantor-product --rent-pcm 2400 --model annual --weeks 3 --setup 59.99 --years 1
  calc.py pro-rata --rent-pcm 2400 --move-in 2026-09-18
  calc.py pct-diff --a 2400 --b 2200
"""
import argparse
import datetime as dt
import json
import sys

WEEKS_PER_YEAR = 52.0
SQFT_PER_M2 = 10.7639


def r2(x):
    return round(x + 1e-9, 2)


def out(cmd, inputs, formula, steps, result):
    inputs = {k: v for k, v in inputs.items() if k not in ("f", "cmd") and v is not None}
    json.dump({"command": cmd, "inputs": inputs, "formula": formula, "steps": steps, "result": result,
               "note": "computed by scripts/calc.py; quote the formula in the report"}, sys.stdout,
              ensure_ascii=False, indent=1)
    print()


def weekly_rent(rent_pcm):
    return rent_pcm * 12.0 / WEEKS_PER_YEAR


def deposit(a):
    w = weekly_rent(a.rent_pcm)
    annual = a.rent_pcm * 12.0
    weeks_cap = 5 if annual < 50000 else 6
    steps = [f"weekly rent = {a.rent_pcm} × 12 ÷ 52 = {r2(w)}",
             f"annual rent = {a.rent_pcm} × 12 = {r2(annual)} → cap is {weeks_cap} weeks",
             f"max deposit = {weeks_cap} × {r2(w)} = {r2(weeks_cap * w)}",
             f"max holding deposit = 1 × {r2(w)} = {r2(w)}",
             "max rent in advance = 1 month = %s" % r2(a.rent_pcm)]
    out("deposit", vars(a), "deposit cap = weeks_cap × (rent_pcm × 12 ÷ 52)", steps,
        {"weekly_rent": r2(w), "deposit_cap_weeks": weeks_cap, "max_deposit": r2(weeks_cap * w),
         "max_holding_deposit": r2(w), "max_rent_in_advance": r2(a.rent_pcm)})


def affordability(a):
    annual_rent = a.rent_pcm * 12.0
    need = annual_rent * a.multiple
    steps = [f"annual rent = {a.rent_pcm} × 12 = {r2(annual_rent)}",
             f"required income = {r2(annual_rent)} × {a.multiple} = {r2(need)}"]
    res = {"annual_rent": r2(annual_rent), "required_income": r2(need), "multiple": a.multiple}
    if a.guarantor_multiple:
        g = annual_rent * a.guarantor_multiple
        steps.append(f"guarantor income or savings = {r2(annual_rent)} × {a.guarantor_multiple} = {r2(g)}")
        res["guarantor_required_income_or_savings"] = r2(g)
    if a.income is not None:
        ok = a.income >= need
        steps.append(f"income {a.income} {'≥' if ok else '<'} {r2(need)} → {'passes' if ok else 'fails'}")
        res["income"] = a.income; res["passes"] = ok
        res["max_rent_pcm_for_income"] = r2(a.income / a.multiple / 12.0)
    out("affordability", vars(a), "required income = rent_pcm × 12 × multiple", steps, res)


def all_in(a):
    fixed = (a.council_tax or 0) + (a.broadband or 0)
    res = {}
    steps = []
    for name, bills in (("low", a.bills_low), ("planning", a.bills_planning), ("stress", a.bills_stress)):
        if bills is None:
            continue
        tot = a.rent_pcm + bills + fixed
        steps.append(f"{name}: {a.rent_pcm} + {bills} + {fixed} = {r2(tot)}")
        res[f"all_in_{name}"] = r2(tot)
    out("all-in", vars(a), "all-in = rent_pcm + bills + council_tax + broadband", steps, res)


def price_per_sqft(a):
    sqft = a.area_m2 * SQFT_PER_M2
    steps = [f"sqft = {a.area_m2} × {SQFT_PER_M2} = {r2(sqft)}",
             f"£/sqft = {a.rent_pcm} ÷ {r2(sqft)} = {r2(a.rent_pcm / sqft)}",
             f"£/m² = {a.rent_pcm} ÷ {a.area_m2} = {r2(a.rent_pcm / a.area_m2)}"]
    out("price-per-sqft", vars(a), "£/sqft = rent_pcm ÷ (area_m2 × 10.7639)", steps,
        {"area_sqft": r2(sqft), "gbp_per_sqft": r2(a.rent_pcm / sqft), "gbp_per_m2": r2(a.rent_pcm / a.area_m2)})


def bridge(a):
    total = a.weeks * a.weekly + a.months * a.all_in
    steps = [f"bridge = {a.weeks} weeks × {a.weekly} = {r2(a.weeks * a.weekly)}",
             f"tenancy = {a.months} months × {a.all_in} = {r2(a.months * a.all_in)}",
             f"12-month total = {r2(a.weeks * a.weekly)} + {r2(a.months * a.all_in)} = {r2(total)}"]
    res = {"bridge_cost": r2(a.weeks * a.weekly), "tenancy_cost": r2(a.months * a.all_in), "total": r2(total)}
    if a.alt_all_in is not None:
        alt = a.alt_months * a.alt_all_in
        steps.append(f"alternative = {a.alt_months} × {a.alt_all_in} = {r2(alt)}; difference = {r2(total - alt)} (negative = waiting is cheaper)")
        res["alternative_total"] = r2(alt); res["difference"] = r2(total - alt)
    out("bridge", vars(a), "total = weeks × weekly + months × all_in (bridging is not an add-on to rent)", steps, res)


def break_even(a):
    rent = a.ceiling - a.bills_planning - (a.council_tax or 0)
    out("break-even", vars(a), "max rent = ceiling − bills_planning − council_tax",
        [f"{a.ceiling} − {a.bills_planning} − {a.council_tax or 0} = {r2(rent)}"], {"max_rent_pcm": r2(rent)})


def guarantor_product(a):
    if a.model == "oneoff":
        fee = a.rent_pcm * a.fee_months
        steps = [f"one-off fee = {a.rent_pcm} × {a.fee_months} month(s) = {r2(fee)}"]
        res = {"total_cost": r2(fee), "per_month_equivalent": r2(fee / 12.0)}
    else:
        w = weekly_rent(a.rent_pcm)
        premium = w * a.weeks
        total = premium * a.years + a.setup
        steps = [f"weekly rent = {a.rent_pcm} × 12 ÷ 52 = {r2(w)}",
                 f"annual premium = {a.weeks} weeks × {r2(w)} = {r2(premium)}",
                 f"total over {a.years} year(s) = {r2(premium)} × {a.years} + setup {a.setup} = {r2(total)}"]
        res = {"annual_premium": r2(premium), "setup_fee": a.setup, "total_cost": r2(total),
               "per_month_equivalent": r2(total / (12.0 * a.years))}
    res["reminder"] = "the tenant stays liable for the rent; the guarantor product pays the landlord and recovers from the tenant"
    out("guarantor-product", vars(a), "oneoff: rent × months; annual: weekly_rent × weeks × years + setup", steps, res)


def days_in_month(d):
    """Length of d's month, without importing the stdlib `calendar` module.

    Every script here runs with this directory as sys.path[0], so a file named
    after a standard-library module would shadow the real one process-wide. Nothing
    here is called calendar.py (the landing tool is `landing.py`, and
    tests/test_landing.py guards the directory), but one fewer name to collide with
    is one fewer way to break datetime.strptime by accident."""
    first_next = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return (first_next - dt.timedelta(days=1)).day


def pro_rata(a):
    d = dt.date.fromisoformat(a.move_in)
    days = days_in_month(d)
    remaining = days - d.day + 1
    first = a.rent_pcm * remaining / days
    out("pro-rata", vars(a), "first month = rent_pcm × remaining_days ÷ days_in_month",
        [f"days in {d.strftime('%B %Y')} = {days}; remaining incl. move-in day = {remaining}",
         f"first month = {a.rent_pcm} × {remaining} ÷ {days} = {r2(first)}"],
        {"days_in_month": days, "days_charged": remaining, "first_month_rent": r2(first)})


def pct_diff(a):
    if a.b == 0:
        raise SystemExit("--b must be non-zero (it is the reference)")
    p = (a.a - a.b) / a.b * 100.0
    out("pct-diff", vars(a), "(a − b) ÷ b × 100", [f"({a.a} − {a.b}) ÷ {a.b} × 100 = {r2(p)}%"], {"pct": r2(p)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("deposit"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm"); p.set_defaults(f=deposit)
    p = sub.add_parser("affordability"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm")
    p.add_argument("--multiple", type=float, default=2.5); p.add_argument("--income", type=float)
    p.add_argument("--guarantor-multiple", type=float, dest="guarantor_multiple"); p.set_defaults(f=affordability)
    p = sub.add_parser("all-in"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm")
    for k in ("bills-low", "bills-planning", "bills-stress", "council-tax", "broadband"):
        p.add_argument("--" + k, type=float, dest=k.replace("-", "_"))
    p.set_defaults(f=all_in)
    p = sub.add_parser("price-per-sqft"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm")
    p.add_argument("--area-m2", type=float, required=True, dest="area_m2"); p.set_defaults(f=price_per_sqft)
    p = sub.add_parser("bridge"); p.add_argument("--weeks", type=float, required=True); p.add_argument("--weekly", type=float, required=True)
    p.add_argument("--months", type=float, required=True); p.add_argument("--all-in", type=float, required=True, dest="all_in")
    p.add_argument("--alt-all-in", type=float, dest="alt_all_in"); p.add_argument("--alt-months", type=float, default=12.0, dest="alt_months"); p.set_defaults(f=bridge)
    p = sub.add_parser("break-even"); p.add_argument("--ceiling", type=float, required=True)
    p.add_argument("--bills-planning", type=float, required=True, dest="bills_planning"); p.add_argument("--council-tax", type=float, dest="council_tax"); p.set_defaults(f=break_even)
    p = sub.add_parser("guarantor-product"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm")
    p.add_argument("--model", choices=("oneoff", "annual"), required=True); p.add_argument("--fee-months", type=float, default=1.0, dest="fee_months")
    p.add_argument("--weeks", type=float, default=3.0); p.add_argument("--setup", type=float, default=0.0); p.add_argument("--years", type=int, default=1); p.set_defaults(f=guarantor_product)
    p = sub.add_parser("pro-rata"); p.add_argument("--rent-pcm", type=float, required=True, dest="rent_pcm"); p.add_argument("--move-in", required=True, dest="move_in"); p.set_defaults(f=pro_rata)
    p = sub.add_parser("pct-diff"); p.add_argument("--a", type=float, required=True); p.add_argument("--b", type=float, required=True); p.set_defaults(f=pct_diff)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
