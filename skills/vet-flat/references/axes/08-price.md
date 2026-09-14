Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 8 — Price

## Purpose
Put the rent on a comparable basis — pounds per square foot of certified internal area — and decide whether any discount or premium has a name.
Two presumptions drive this axis: cheap has a reason, and you pay more only for a benefit you can name.

## What counts as evidence
- **G** — registered sale prices for the same building and postcode; the certified floor area the calculation rests on.
- **S** — the asking rent, "from £X", the operator's own price list.
- **C** — a portal's price-reduction history, a comparable let reported by a resident.
- **I** — a band median assembled from a handful of comparables.
- **U** — no comparables at all in the area.

## Method in shell mode
1. `python3 scripts/epc.py building --postcode "<pc>"` — the area distribution, so the £ per square foot is computed on the right denominator.
2. `python3 scripts/landregistry.py price-paid --postcode "<pc>" --brief` — the price summary and the recent sales in the same building (drop `--brief` for the full sequence); the best available evidence of relative value between units and of the building's real vintage.
3. Compute: rent ÷ certified square feet; the band median £ per square foot; the flat's percentile in the band.

## Method in fetch mode
Registered sale prices answer over a query endpoint. Asking rents and reduction histories live on listing portals, which forbid automated access — ask the user.

## Method in manual mode
Ask the user for:
1. The listing page text, including the price, any "reduced on" and "added on" dates, and the full description.
2. Three to five comparable listings in the same area with their sizes, so a band can be assembled.
3. The operator's own price for the same unit if there is a direct site — a gap between the operator's price and the portal's means one of them is stale.

## How to read the numbers
- `price_per_sqft_epc` = monthly rent ÷ certified square feet. Never use the advertised square footage.
- **Median back-check:** band median £ per square foot × this flat's certified area = what it ought to cost. If the asking rent lands on that figure, the "cheap has a reason" presumption does not fire and there is no discount to explain — say so and move on.
- `price_below_band_flag_pct` — run the test on both the monthly rent and the £ per square foot. Below the band by more than this, name the discount or leave.
- `price_above_comparable_flag_pct` — above a same-building, same-floor comparable by more than this, with no nameable benefit, leave. One flat was 23.9% above a same-floor let of similar size in the same building with nothing to show for it.
- `rent_ceiling_pcm`, `all_in_ceiling_pcm` — profile. Price alone never decides; axis 10 does.

## Traps and lessons
- **Name the discount or walk.** A price below the local band means someone has a reason to sell it to you. Decompose it into named, checkable causes: location, age, conversion, works next door, timing, management, commute, aspect, facade. An unexplained discount is a reason to leave.
- **A reduction is compensation, not a bonus.** The question is never "how much has it come down" but "is the compensation enough for the defect it is compensating". A building where 75% of listings have been reduced, against a borough average of 29%, has a site-specific discount pressure — find it.
- **"From £X" is a floor price**: the smallest, lowest, worst-facing unit in the building, not the one you were shown.
- **A marketing unit number is not a lettable flat.** Brochure and catalogue numbers have no leasable counterpart; ask for the unit reference the tenancy would name.
- **The whole-building area distribution kills false alarms.** An apparently cheap £ per square foot is often just where the flat sits on the size curve.
- **Exit liquidity.** A flat that sits on the market a long time, in a building whose owners objected to a neighbouring scheme and lost, means you are taking on what they are trying to leave.
- **Time has a value, but it never raises the budget.** Minutes saved on a commute can be converted into money for ranking and for negotiation. It is a tie-breaker inside the budget and an argument to use with an agent, never a reason to spend more.
- **Ask what sits under the prettiest feature.** Name the most attractive thing about the listing — the view, the finish, the price — then check what it is standing on, axis by axis.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 8`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.price_per_sqft_epc` — rent divided by the certified indoor area, with the band it is compared against in `compared_to`.
- `candidates[].costs.rent_pcm` — the rent this axis measured; axis 10 adds the rest.
- `candidates[].verdict.break_even_rent_pcm` — set when the verdict is EDGE.
- `candidates[].landmines[]` — a price this axis cannot explain usually surfaces as a landmine on whichever axis explains it.
Numbers to record: rent, pounds per square foot, band median, percentile in the band, the median back-check figure, the discount or premium as a percentage, days on the market.
