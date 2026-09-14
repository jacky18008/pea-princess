Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 15 — The bridge: a 2 to 8 week short let before the real tenancy

## Purpose
Most people arrive before the flat they actually want is free. The bridge is the gap. This axis prices the gap honestly, buys the right product for it, and stops the gap from making the long-let decision worse than it needs to be.
A bridge is a tent, not a home. It is vetted on three things only: clean, quiet enough to sleep, able to receive post. Do not run the full axis set on it.

## Two rules that come before any listing
1. **Book the bridge first.** Before you vet a single flat, have somewhere to sleep booked for at least the first two weeks — a hotel or an operator-run serviced stay; a private short let only after you have seen it or verified it live. Whether the very first nights are a hotel is a personal choice; arriving without a booking is not. Say this to the user before anything else when they have not landed yet.
2. **Signing is not moving in.** A found flat, an accepted offer, even a signed agreement is not keys. Referencing, the deposit going into a scheme, the previous tenant's move-out and the start date you agreed can put weeks between "we found it" and "we sleep there". The maintainer's own gap ran 45 days in one stretch (London, 2026) ●. Plan the bridge for the gap between signing and move-in, not for "a few nights on arrival", and price it with the year-total rule below.

## The first six weeks (`scripts/landing.py`)

The two rules above are a plan, so write it down as one. `scripts/landing.py plan --arrive <date> --start <date> [--keys-by <date> | --gap-weeks N] [--areas "Deptford, Lewisham"] [--budget-all-in N] [--bridge-weekly N]` prints a week-by-week table from the day you land to the day the keys are actually released: where you sleep that week (hotel or operator for the first two, a private short let only after you have seen it), what you do that week, what the week collides with, and the twelve-month total on the year-total basis above — computed by `calc.py`, not by anyone's head. When nobody knows the key date it plans the long end of four to seven weeks and says why. In a chat box with no shell, ask the four dates and write the same table by hand.

What it reads: bank holidays from GOV.UK (the days agents, referencing companies, councils and deposit schemes are shut), planned closures from the TfL line-status feed for the modes your areas actually use, `references/term-dates.yaml` for the ten London universities, and `references/london-events.yaml` for the recurring citywide occasions and the venues.

**Without a shell**, write the same table by hand from the four dates and two numbers, and show every step: bridge cost = weeks × weekly rate (or nights × nightly rate × (1 + service fee) + cleaning fee); the gap between signing and keys in weeks; the cash needed before keys = bridge cost + holding deposit (one week's rent = pcm × 12 ÷ 52) + first month + deposit (five weeks' rent; six at £50,000 a year or more). Give the totals as numbers with their formulas beside them, never as a search term or a shrug.

**Structural is not the same as a venue event, and the difference decides what you do about it.**
- **Structural** is university term start. Every September, without exception, and it tightens **long lets and short lets at the same time**, across the whole city. This is the real cause of the September squeeze. You cannot dodge it by moving borough; you dodge it by arriving with the bridge already booked, or by being one of the people signing in late October when the crowd has gone.
- **Venue** is a show at ExCeL, a concert or a match at Wembley, the O2, London Stadium, Twickenham or Olympia. It runs on that venue's own schedule, not on any yearly cycle, and it moves prices only around that venue — the tool works to a check band of about 8 km and a price band of about 2 km. You dodge it by looking at the venue's own calendar for your dates and moving your seam by a day, or by staying two miles further out. Wimbledon is July and has nothing to do with a September arrival.

**Never put a percentage on any of this.** We have not measured the uplift, in this repo or anywhere we can cite. The only honest sentence is "known to push local prices up; magnitude not measured here". A report that says "expect thirty per cent more" has invented a number, and the reader will plan around it.

## The one arithmetic rule that changes every ranking
A bridge is **not an extra cost**. During the bridge you are not paying the long-let rent. Compare whole years, not monthly averages:

> 12-month total = (bridge weeks × bridge weekly rate) + (remaining months × long-let all-in)

Worked shape: a flat available now at an all-in of A costs 12A over the year. A cheaper flat available `w` weeks later, at all-in B, costs `(w/4.33) × weekly_bridge + (12 − w/4.33) × B`. Whenever B is enough below A, **waiting is cheaper, not dearer**.
The wrong model — "amortise the bridge into the year as a surcharge, so every week of waiting lowers your rent ceiling" — double counts. It manufactures a false deadline and kills good October and November flats. If a report contains a "monthly cost after bridge amortisation" column, delete the column.
**Never raise the cost of waiting without the plan that pays for it.** Waiting a month or two for a clearly better long let is usually right; say so, then price the bridge realistically: in London a short let in tiers B–F runs about £45–75 a night (author's 2026 bookings ●; check the current quotes), a hotel £100–200. Quote the short-let band, name two tiers to try, and give the 12-month total with and without the wait — a bare "a hotel at £150 a night" only adds worry.

What waiting actually costs is three non-money things: moving twice; the risk that the bridge cannot be extended; and the value of having your own place, which is real but belongs in the comfort column, not the price column.

## Bookability tiers (pick the tier before you pick the listing)
| Tier | What it is | Typical price shape | Deposit | Cancellation | Use it when |
|---|---|---|---|---|---|
| A | Aparthotel / serviced apartment operator, booked direct | Highest per week, all bills in | Card pre-auth or a month held by the operator | Often a free-cancellation rate exists at a premium | You need certainty and a 24h front desk |
| B | Peer-to-peer short-let marketplace | High per week; platform fee ~10–15% on top | None | Graded, published, enforceable | You need reviews and zero counterparty risk |
| C | Mid-let / relocation marketplace reselling operator stock | Mid; a non-refundable platform fee | Paid to the operator, not the platform | Weak once accepted | The same room is cheaper than booking direct |
| D | Letting agent's short-let desk | Mid; may add an admin fee | Traditional deposit, sometimes protected | Contractual | You want a proper agreement and an address |
| E | Flatshare boards and private landlords | Lowest headline | Often a full month, unprotected | None | Only with a deposit at or near zero, in writing |
| F | Student operator or budget hotel chain | Low per night, poor kitchen | None | Flexible rates exist | Filling an 8–14 night seam |

## Refundability breakpoints
- A free-cancellation rate is a real product with a real price. Expect to pay roughly 15–25% over the non-refundable rate for it. That premium buys you the right to keep searching.
- **Book the refundable option early as an insurance position, then cancel it when something better lands.** Note the exact cancellation deadline in the calendar the day you book.
- Fully prepaid, non-refundable, request-to-book stock is the cheapest and the most dangerous. Only take it once your eligibility, the exact unit and the exact dates are confirmed in writing.
- On marketplaces that charge on acceptance, there is no "ask the host first" step: acceptance takes the first payment and the platform fee immediately. **Resolve every question by phone before you submit.**

## Total-price traps
1. **The headline "per month" is often an average that excludes the first week.** Always recompute three numbers yourself: per night, per week, and the total for your exact night count.
2. Platform fee: fixed, usually non-refundable, and not in the headline.
3. Deposit: ask **who holds it** — the platform or the operator. It changes the risk entirely.
4. Cleaning: a fee, an included service, or nothing at all. "£0" often means "not provided", not "free".
5. Month-boundary pro-rating: a 36-night stay spanning two months is billed as two part-months, which rarely equals the monthly rate.
6. Private landlords frequently bill **whole months**: 36 nights can be charged as two months.
7. Admin fee on an agent short let, and whether Wi-Fi and council tax are inside or outside the weekly rate.
8. Payment-rail cost: paying a sterling invoice with a foreign card can add ~3%. Ask for bank details and pay from a sterling balance.

### The break-even question, in one line
Convert every candidate to **all-in per week for your exact dates**, then ask what the cheaper option is missing: a front desk, a review history, a refund right, or a protected deposit. Decide what that is worth to you *before* you compare, and write the number down.

## Licence vs tenancy — the single most expensive distinction
- A short serviced stay is normally a **licence to occupy**, not an assured shorthold tenancy.
- A licence deposit is **not required to go into a government-approved deposit scheme**. If it goes wrong your route is the operator's redress scheme or the small claims track, not the scheme's adjudication.
- Therefore: **cap your exposure instead of trusting the paperwork.** Never hold more than one week's rent plus a small deposit with a counterparty you have not verified.
- A licence is also renewed week by week. The operator can decline to renew. On the day you move in, ask in writing: *what is the latest date I can extend to?*
- A proper short-let tenancy from an agent is the opposite trade: more paperwork, more checks, but you get an agreement with your name and the address on it — which is the document that unlocks banking and address proof.

## The 90-night rule (Greater London)
- A whole home may be let for short stays for at most **90 nights per calendar year** without planning permission. Beyond that it is a material change of use and the borough can enforce.
- Stays of 90 nights or more are outside the short-let definition — this is how compliant serviced-apartment operators work.
- Two uses for this rule: (a) if a building's flats appear on holiday-booking sites all year, the operator is probably in the grey zone, which tells you something about the landlord's character; (b) if the **long-let** building you are vetting has short-let churn, your neighbours will be suitcases (see axis 9).
- Listing pages on two sites owned by the same travel group are **one footprint, not two independent sources**. Old reviews that stop years ago usually mean a dead page, not an operating hotel — check the date of the newest review and whether a future date can actually be booked.

## What to ask before paying (short-let enquiry set)
1. Which exact unit is this, and does it face the street or the courtyard?
2. What is the contracting entity and its company number, and will rent and deposit be paid to a bank account in that exact name?
3. Is this a tenancy or a licence, and is the deposit protected in a government scheme?
4. Please send your current client-money-protection certificate and your redress-scheme membership number.
5. Can I view before paying anything?
6. Can post be received in my name, and will the agreement show my name and the property address?
7. Is there a washing machine **inside** the unit, and where is it?
8. Is the included Wi-Fi a fixed line with unlimited data, or a mobile router, and what speed?
9. Are the photos of this unit as it is today? What notice do you need for weekly extensions, and is there a cap on any end-of-stay cleaning fee?
10. What does the weekly rate include: council tax, electricity, water, heating, Wi-Fi? What is the total for my exact nights, the deposit, and every fee?

## Kitchen and laundry grades (decide which grade you need, then filter)
| Grade | Kitchen | Laundry | Fits |
|---|---|---|---|
| K3 | Private full kitchen: hob, oven, fridge-freezer | Washer inside the unit | Stays over 3 weeks; anyone who cooks |
| K2 | Private kitchenette: hob, microwave, small fridge | On-site laundry room | 2–4 weeks |
| K1 | Kettle and microwave only | Launderette nearby | Under 2 weeks |
| K0 | Shared kitchen | Shared or none | Avoid unless the price gap is decisive |
Confirm the grade from the **written description of your unit**, not the building's photos. A missing washer is not fatal on a short bridge, but you must know before you book, not after.

## Counterparty checks that are worth the twenty minutes
- Company register: incorporation date, status, charges, director disqualifications, filing history. A long-lived company with a **brand-new lettings arm** has no reviews because it has no history in lettings — that is not proof of quality either way, and it makes you an early customer.
- No reviews anywhere is a fact to explain, not a verdict. Find out what the company did before.
- Redress scheme and client money protection: ask for the certificate and check it is current. An expired certificate on a website is a finding.
- Scam fingerprints, any one of which ends the conversation: **price far below the market, money requested before viewing, and a deal done through social-media direct messages.** Attractive, well-known developments are the ones impersonated — being used as bait says nothing bad about the address.

## Payment armour
1. Never prepay more than one week's rent plus the deposit. A demand for one or two months up front is a stop signal.
2. Pay the first instalment by credit card where possible. Before any bank transfer, run the payee-name check; the account name must match the contracting entity exactly.
3. Get three documents before money moves: an invoice showing the company number, the redress membership number, and a current client-money-protection certificate. Missing the third means one week only.
4. Put every verbal promise back in an email and ask for a written "confirmed". Small operators have thin admin; your record will be better than theirs.
5. Insist on viewing before paying. If an in-person viewing is genuinely hard, a **live video walkthrough** is acceptable for a bridge: have them pan the window (street or courtyard), the kitchen, the washing machine.

## Seams and dates
- Budget the bridge in weeks, not nights: from arrival to the day the keys are actually released. Four to seven weeks is ordinary when you arrive in term-start season; the maintainer's was 45 days. Book a flexible second block rather than gamble on a short first one.
- Split the bridge into at most **two blocks**, and put the seam on a weekend, before term starts. Never move during induction or teaching week.
- Ask the current short-let host whether you can simply extend. It is free to ask and it is the only zero-move option.
- If handover falls on a Monday, ask whether keys can be released on the preceding Saturday. Two fewer bridge nights is a real saving.
- Offer only two kinds of flexibility, both of which help the other side: a **flexible start date**, and a **willingness to extend**. Never offer to shorten the stay — that manufactures a new gap.

## On arrival (30 minutes, do it before you unpack)
1. Photograph and video every room, including existing damage, and upload it off-device. This is your defence against end-of-stay cleaning and damage charges.
2. Smell test: corridor, bin store, the unit itself.
3. Run the hot tap and time it; check the shower pressure.
4. Test the Wi-Fi speed and check whether it is a fixed line.
5. Find the washing machine, the meter cupboard and the stopcock.
6. Listen at the window once at about 22:30.
7. Ask, in writing, the latest date you can extend to, and confirm the notice period for weekly extensions.

## Stays near or over a week: view first, or verify live
For a stay of five nights or more, treat it like a tenancy: ask to view in person or on a live video call before paying, and run the damp check in `14-site-visit.md` (lower-ground and ground stays especially). Two-night guests do not stay long enough to notice damp, a loud fridge or a light well; their five stars measure cleanliness and a fast reply. Price on a platform is a demand signal, not a quality signal.
If you arrive and the place is not habitable (damp, mould, water damage, pests, a safety issue):
1. Photograph everything with something for scale, the same day.
2. Message the host inside the platform, not on a messaging app, factual and polite: the host is usually trying, and a courteous request for an early check-out with a refund of unused nights is granted more often than a fight.
3. Do not press "cancel" yourself: that applies the listing's cancellation policy. Use the platform's complaint route for accommodation problems; most platforms have a short window after check-in (often about 72 hours) in which habitability problems can be raised for a refund of unused nights.
4. Book a cancellable fallback before you sleep on it. Then decide in the morning.

## Just arrived: ask before you book a private short let
Ask the user, once: "For the first one or two weeks, would a hotel or an operator-run serviced stay work for you, with a private short let only after you have viewed it?" Present it as a trade, not a rule: the hotel or operator route buys protected money, an instant exit and a responsible party, at a known premium per night and usually without a kitchen (price the eating-out cost with `scripts/calc.py`); the private short let is cheaper and has a kitchen, but a licence is not a tenancy and problems surface only after check-in (see the damp check in `14-site-visit.md`). Record the answer in `profile.yaml` under `bridging.first_weeks` (`hotel_or_operator` | `private_short_let` | `undecided`).

