Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 6 — Management, neighbours and reviews

## Purpose
Work out who actually runs the building, how well, and who you will live next to.
Most of the raw material is on resident-review sites whose terms forbid automated access, so the method here is a reading method, not a fetching method.

## What counts as evidence
- **G** — company filings and registered activity codes; the presence or absence of a resident-owned management company; planning objections; tribunal decisions; enforcement records.
- **S** — the operator's own service claims and marketing.
- **C** — resident reviews, local news, forum threads.
- **I** — a management quality inferred from a small or invited-only sample.
- **U** — the building has no natural review sample at all.

## Method in shell mode
Nothing here fetches a review site. `scripts/reviews.py` reads the pages the user pastes - see the review surgery below, which is where this axis's real work happens - and these scripts do the work around them:
1. `python3 scripts/company.py search "<managing agent or landlord>"` → `profile <company number>` → `filings <company number>` — activity codes, charges, accounts, officers.
2. `python3 scripts/company.py address-search "<building postcode>"` — companies registered at the building. A building with no resident-owned management or right-to-manage company means residents structurally cannot change the managing agent; that absence is an official-register finding.
3. `python3 scripts/redress.py rogue --name "<landlord or agent>"` — the London enforcement checker (absence only means no borough reported one).
4. `python3 scripts/planning.py search --text "<building>"` — objections and consultation records name residents and their complaints.

## Method in fetch mode
Company and enforcement registers are fetchable. Review sites are not — see `inputs.md`.

## Method in manual mode
Ask the user for the full review pages for the named building, all pages, oldest first, pasted as text, plus the site's stated total number of reviews. Then run the review surgery below on what they paste.

### Review surgery (this is the axis's real method)
**Shell mode.** The surgery is a script, so run it rather than doing it from memory. `python3 scripts/reviews.py stats <the pasted pages>` splits them into reviews and prints the count against the site's stated total, the rating histogram, the mean, the organic mean with the incentivised reviews removed, the organic mean with review-drive days removed as well, the same-day and same-month bursts, the move-out reviews and a mentions table - every figure with what it means in one clause. Then `python3 scripts/reviews.py lowest <the pages> --n 5` prints those five whole, with their line spans, and you read them in the original wording; `mentions --topic damp|noise|management|short_let` does the same for one theme, and a zero there is a finding to record, not a clean bill. The organic mean with its sample size, the incentivised share and the burst flags go into `numbers[]` carrying `computed_by: reviews.py`. It fetches nothing; if no page could be parsed it exits 1 rather than inventing a score. Without a shell, do every step below by hand and say in the finding that the counting was done by hand.

1. Take everything, not a sample; check the count against the site's stated total.
2. Remove reviews the site itself marks as incentivised or invited.
3. Remove same-day bursts: `review_burst_same_day_min` or more reviews on one date is a review-drive day, even when none of them are marked incentivised. In one building 55% of all reviews fell on 25 such days.
4. What is left — not incentivised, not on a burst day — is the only score that enters the verdict. Report it as the organic score with its sample size.
5. Read the lowest-scoring reviews in full, in the original wording. Never summarise from the star rating.
6. Move-out reviews weigh most ("moved out", "I left", "during my tenancy"). One of those outweighs ten from current residents — the same resident has given 5 out of 5 on a review-drive day and 2 out of 5 on the way out.
7. Grep themes and record the zero counts too: smells through vents, neighbours and parties, corridor noise, leaks, lifts, heating and hot water, billing, repairs response.
8. No natural sample within `review_staleness_years` means the score is expired. Say "the last resident voice here is four years old, so this building is unmeasured on reviews" and stop quoting the number.
9. Quantify the invited premium: the gap between the invited average and the natural average.
10. If the invited share rises towards 100% across the years while the average rises with it, that is a selection effect, not an improving building. One building went from 4.52 with 43% invited to 4.97 with 100% invited: what improved was the sample. Recent scores are then unusable; go back and read the earliest natural batch, where the damaging testimony usually sits.
11. On two-sided review sites, watch four poisoning fingerprints: the same staff name repeated, single-day clusters, competitors writing in, and a sharp break in the time series.
12. Write down the false alarms you cleared. A report that shows nothing was manufactured is more trustworthy than one with more red flags.
13. A zero denominator is not clean. Small leasehold blocks are systematically absent from review sites. Switch to planning objections, hyperlocal news, forum threads and the registers, which for a building with no reviews are at least as good.

## How to read the numbers
- `review_burst_same_day_min`, `review_staleness_years`, `review_min_organic_sample` — the hygiene constants above.
- `management_organic_score_min` — profile. There is no universal pass mark; state the bar you used.
- `structural_finding_min_developments` and `structural_finding_min_years` — a theme seen across at least this many buildings and this many years is structural and may be generalised to the area; anything narrower is a single-building defect and may not.

## Traps and lessons
- **Sample size weighs.** 281 reviews averaging 4.69 is a signal; 7 reviews averaging 3.89 is a footnote; one organic review is not a management score at all.
- **Scores attach to a building, not a development.** Do not lend one block's score to the block next door, even under the same brand.
- **Agent or landlord? Read the registers, not the brand.** A company with a "real estate agency" activity code, no charges and no property is an agent, and the landlord behind it is a private individual. A company with an "own or leased real estate" code and a mortgage charge naming the building address really is the owner. The brand on the door is not the landlord; the legal name on the tenancy is.
- **The delayed fuse.** An institutional owner whose group accounts say it will "continue the sale of the residential investment portfolio", marketing "tenanted apartments", has not closed the door — it has fitted a fuse. The flat can change hands mid-tenancy, and the tenancy transfers with it while the new owner never assessed you. Ask, in writing, whether the flat is on the market and what happens to the tenancy after a sale.
- **Quality is the weakest compulsory supplier on the chain.** Billing platform, broadband provider and outsourced maintenance are all things a resident cannot swap. Check them in order: landlord, managing agent, billing provider, broadband provider. Billing providers tend to be regional rather than brand-tied, so checking one building tells you about a whole area. "Bills included" tied to a single provider is only a benefit once that provider checks out.
- **Neighbour mix is bought with tenure structure, not with rent.** Look at the short-let footprint in the building, the share of adverts aimed at sharers or students, whether affordable homes have their own core (mixed tenure is not the problem; management response time is), and whether the block was sold off-plan to overseas investors, which produces the highest turnover.
- **Short lets.** Ask the user to check the building name on short-let and hotel platforms; sites owned by the same group share inventory, so count one footprint, not two. A hit is not automatically fatal — separate a trading operation from a left-over page by the date of the most recent review and by trying a future date. But **"cannot book" is not proof of closure**: it can mean full, withdrawn inventory, or a channel restriction. If it is trading, you have transient neighbours; if it is a stale page, ask for written confirmation that all flats in the building are now let on ordinary residential tenancies.
- **The legal frame for short lets:** in Greater London, more than `short_let_nights_per_calendar_year` nights of temporary sleeping accommodation needs planning permission. The exemption is counted per property per calendar year, not per person, and requires someone providing the accommodation to be liable for council tax; if either condition fails, the exemption fails. What it becomes above the limit is decided by the local authority on the actual operation, not by the contract's title. And planning compliance is not lease, freeholder, mortgage or insurance permission — those are separate.
- **A quiet positive signal:** a landlord who keeps the flat in good order and prices it sensibly is showing you their character before you meet them. Wishful pricing points the other way. How they answer a well-evidenced offer is the most direct character test available, and it beats any review.
- **Ask at the viewing:** how long did the last tenant stay, and why did they leave. A tenant who left after a year voted with their feet.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 6`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.management_organic_score`, `management_incentivised_share`, `landlord_type`.
- `candidates[].worst_reviews[]` — `building`, `source_name`, `date`, `score`, `organic`, `excerpt` (quoted, never summarised), `why_it_matters`.
- `candidates[].landmines[]` with code **L7** (failing management the residents cannot replace), **L8** (prompted, burst or expired reviews, and no reviews at all is unknown rather than clean) and **L9** (short-let or student churn next door).
- `comparison.structural_findings[]` and `comparison.single_building_findings[]` — a theme is generalisable only if it clears both structural thresholds.
Numbers to record: organic score with its sample size, invited share, number of review-drive days, date of the most recent natural review, short-let footprint.
