Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 10 — All-in cost

## Purpose
Put every candidate on one cost basis: rent plus a bills model plus council tax, recomputed by you from the same assumptions for all of them.
A comparison where one flat carries the operator's estimate and another carries your own is not a comparison.

## What counts as evidence
- **G** — the council tax band from the national band lookup; a published tariff; a statutory exemption or discount.
- **S** — "bills included" at a fixed monthly figure; an agent's estimate; a supplier's indicative figure.
- **C** — residents reporting what they actually pay against what the FAQ promised.
- **I** — your bills model. Always labelled as a shared assumption, never as a quote.
- **U** — no tariff and no band.

## Method in shell mode
1. Council tax band: the national band lookup is a fetch or a manual step; record the band and the borough's current rate for it.
2. `python3 scripts/redress.py heat-trust --site "<building>"` and `python3 scripts/company.py profile <supplier>` — whether the heat supplier is inside the consumer-protection scheme and whether its accounts point at a tariff rise (axis 3).
3. Compute three totals from the same model for every candidate: low, planning and stress.
   If the council tax amount or an applicable exemption has not been confirmed, the calculator returns a known subtotal and a null total. Do not treat an omitted `--council-tax` flag as £0 or compare that subtotal with a person's total-spending ceiling.

## Method in fetch mode
The band lookup and the regulator's pages are fetchable. Tariffs usually are not.

## Method in manual mode
Ask the user for:
1. Exactly what "bills included" covers, in writing: which utilities, what cap, and what happens above the cap.
2. The heat-network tariff page — standing charge and unit rate.
3. The council tax band, or the address, so the band can be looked up.
4. Any one-off fees quoted: check-in inventory, referencing, a commercial guarantor product, and any verification or damage-deposit product.

## How to read the numbers
- `bills_low_pcm`, `bills_planning_pcm`, `bills_stress_pcm` — profile placeholders. Use the same three numbers for every candidate in one run and print them next to the total. They are a sensitivity assumption, not a supplier's quote for any heating system, and the report must say so.
- When council tax is unknown, write “rent plus the stated bills model = £X, **plus council tax still to check**”. This is a subtotal, not the whole monthly cost. A heat-network standing charge or tariff missing from the bills model is also an unresolved extra; don't bury it inside a £0 assumption. `--council-tax 0` applies only when an actual exemption has been established and named in the basis note.
- `all_in_ceiling_pcm` — profile. On or under it is a pass on this axis.
- `edge_band_over_ceiling_pcm` — over the ceiling by up to this much is EDGE, and the report must carry the break-even rent; more than that is a different price bracket, not an edge case.
- `bridging_weekly_cost` and `move_in_window` — profile, and only relevant if the user would bridge to reach a later start date.

## The all-in rules
1. **One basis, printed with the number.** Six sub-reports quoting bills between £148 and £315 cannot be compared with each other. Recompute all of them.
2. **Bundled bills go in at the bundle price**, flagged as bundled, with what the bundle excludes.
3. **Council tax depends on the household.** Some households are exempt or discounted (for example where every occupier is a full-time student). State which rule you applied and that it is a rule, not an assumption about the user.
   Null is unknown; zero requires a verified exemption. Without the amount, do not mark the total-cost axis as passed or supply a break-even rent target. The rent-only limit can still be checked separately.
4. **One-off costs count**: inventory, moving, referencing, guarantor product fees, verification products, and any cash damage deposit — the last is also an exit-friction item, not just a cost.
5. **Break-even.** When a candidate is over the ceiling, compute the rent at which it comes back under. That number is the negotiating target and belongs in the report.

## Bridging and temporary accommodation
- **Bridging is not an add-on to rent.** While you are in temporary accommodation you are not paying the long rent.
- Compare **twelve-month totals**: (bridging weeks × weekly bridging cost) + (remaining months × all-in). Where the weekly bridging cost converts to less than the candidates' all-in, a later move-in date often costs the same or less, and can be cheaper. In one worked comparison a later start saved about £1,900 over the year against an immediately available flat.
- **Never amortise bridging into a monthly surcharge**, and never say that moving in earlier "saves" the bridging cost.
- The real cost of waiting is not money: moving twice, whether the temporary let can be extended at all (a weekly licence can simply not be renewed — ask the maximum extension at check-in), and the loss of settledness.
- For a temporary let, price the friction too: two payment instalments for a stay over about a month are two parts of one total, not two prices; a rate can flip from refundable to non-refundable somewhere between short and long stays, so test several lengths; a price shown next to "no availability on the selected dates" is not a price; and a refundable rate costing £80 more is £80 spent on the risk of the booking falling through, which should be written down that way.

## Traps and lessons
- **A billing platform's FAQ figure and residents' actual bills can differ by a factor of two.** Prefer a resident's reported bill to a marketing figure, and label which you used.
- **Electric-only and heat-network flats have different bases**; do not carry one model across both without saying so.
- **Never let a cost model quietly become a quote.** Set `not_a_supplier_quote: true` on the model in the report.
- **If a launderette replaces a washing machine**, that is money plus 60 to 90 minutes a week — cost it here and grade it on axis 12.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 10`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].costs` — `rent_pcm`, `bills_low`, `bills_planning`, `bills_stress`, `council_tax`, `all_in_planning`, `basis_note` and `sources`. The `basis_note` must say that the bills figures are a shared assumption applied identically to every candidate and are not a supplier quote.
- `candidates[].hard_filters[]` — one row for the profile's all-in ceiling.
- `candidates[].verdict.break_even_rent_pcm` — the rent at which an over-ceiling candidate comes back under; this is the negotiating target.
Numbers to record: each one-off cost, the twelve-month total on each scenario, and, where bridging applies, the bridging weeks and weekly cost with the twelve-month comparison spelled out.
