Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The 12 checks, one line each

Read the axis file before doing the check; this page is the map.

1. **Identity** (`01-identity.md`) — exact flat, building, postcode; verify with EPC (`scripts/epc.py`). Buildings can span postcodes.
2. **Floor area** (`02-floor-area.md`) — EPC internal m² only, balconies excluded; listing and floor-plan figures are claims.
3. **Age and fabric** (`03-age-fabric-heating.md`) — first EPC ≈ completion; heating; air permeability ≤ 5 suggests mechanical ventilation.
4. **Construction nearby** (`04-construction-nearby.md`) — planning applications within ~250 m; discharged conditions show whether works start or finish.
5. **Crime** (`05-crime.md`) — data.police.uk, fixed six-month window in a ~300 m box; nodes on the walk home count in full.
6. **Management and neighbours** (`06-management-neighbours.md`) — reviews minus incentivised and same-day bursts; read the lowest in full; move-out reviews weigh most; short-let footprint.
7. **Agent and landlord compliance** (`07-compliance-landlord.md`) — legal entity on Companies House, redress scheme, client-money protection, deposit protection; landlord type.
8. **Price** (`08-price.md`) — £ per EPC sq ft vs local band; explain discounts.
9. **Aspect and light** (`09-aspect-light.md`) — floor-plan compass, sky openness, obstruction angle; quiet beats light unless there is almost none; lower-ground checklist.
10. **Total monthly cost** (`10-all-in-cost.md`) — rent + bills + council tax on one basis; `references/arithmetic.md` (`scripts/calc.py all-in`): estimate (I), not U.
11. **Commute and redundancy** (`11-commute-redundancy.md`) — TfL door-to-door; two independent rail families within a 10-minute walk.
12. **Low-maintenance living** (`12-livability.md`) — bills bundled, washer, parcels, blackout, shop within 3 minutes; the area's living environment (`scripts/living_env.py`: housing quality, air, road accidents) as context, never a filter.

A street in one call: `scripts/area_scan.py --street NAME --depth <budget mode>` (quiet, road noise in dB via `scripts/noise.py`, safety, works, living environment; once per street, then write).

Beyond the twelve: `00-area-sweep.md` (candidates around a commute point, `scripts/sweep.py`), `13-adversarial-review.md` (the roast), `14-site-visit.md` and `18-street-view.md` (the viewing), `15-bridging-short-lets.md`, `16-referencing-and-proof-of-funds.md`, `17-uk-admin-pitfalls.md` (the move-in half).
