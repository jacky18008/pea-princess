Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Arithmetic is never done in your head

Small models get rent maths wrong, and wrong money numbers are the most expensive kind of fabrication. Every derived number in a report comes from `scripts/calc.py` (shell mode) or from a formula written out step by step and checked a second way (fetch or manual mode). Both renderers recompute the key figures from the report's own inputs and flag mismatches.

## Shell mode: `scripts/calc.py`
| Need | Command |
|---|---|
| Simple differences or four-operation expressions | `calc.py arithmetic "2300 - 2250" "61.5 - 57.2"` |
| Deposit and holding-deposit caps, rent in advance | `calc.py deposit --rent-pcm 2400` |
| Income test, guarantor multiple, max rent for an income | `calc.py affordability --rent-pcm 2400 --multiple 2.5 --income 65000 --guarantor-multiple 4` |
| All-in monthly cost, three bill scenarios | `calc.py all-in --rent-pcm 2400 --bills-low 125 --bills-planning 175 --bills-stress 250 --council-tax 0 --broadband 30` |
| £ per sq ft from the EPC area | `calc.py price-per-sqft --rent-pcm 2400 --area-m2 52` |
| Bridging stay versus waiting | `calc.py bridge --weeks 7.7 --weekly 500 --months 10.2 --all-in 1995 --alt-all-in 2175` |
| Break-even rent under an all-in ceiling | `calc.py break-even --ceiling 2600 --bills-planning 175` |
| Guarantor product cost, one-off or annual | `calc.py guarantor-product --rent-pcm 2400 --model annual --weeks 3 --setup 59.99` |
| First month pro-rata | `calc.py pro-rata --rent-pcm 3000 --move-in 2026-09-18` |
| Percent difference against a band | `calc.py pct-diff --a 2400 --b 2200` |

Arithmetic also accepts quoted expressions directly (`calc.py "484 - 342"`). It returns one decimal-string result per expression; `rounded: true` marks division or operations rounded to 50 significant digits. Only numbers, `+ - * /` and parentheses are accepted, with size and magnitude limits.

Each prints `inputs`, `formula`, `steps`, `result`; quote the formula in the report and set `computed_by: "scripts/calc.py <subcommand>"` on the number.

## Without a shell
1. Write the formula in words (for example: weekly rent = monthly rent × 12 ÷ 52; deposit cap = 5 × weekly rent when the annual rent is under £50,000, else 6 ×).
2. Write every intermediate step with its number.
3. Check the result a second way (a different order of operations, or a bound: five weeks' rent is a little more than a month's rent).
4. Set `computed_by: "shown formula"` on the number.

## Constants (England)
Weeks per year 52 · sq ft per m² 10.7639 · deposit cap 5 weeks (6 at or above £50,000 annual rent) · holding deposit 1 week · rent in advance normally 1 month only in the monthly, in-scope pre-tenancy case (after signing; see axis 07) · the affordability multiple is the landlord's published figure (commonly 2.5–3× for employed applicants; students and the self-employed follow the operator's table in `axes/16`).
