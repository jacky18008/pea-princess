Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# London rent levels, 2026 — reference numbers for example budgets

Compiled 2026-09-05. Each row gives the number, the period it describes and the source. Rows marked
**derived** are arithmetic done here on primary data, not a figure the source itself publishes.

## 1. A room in a shared flat or house

| Figure | Value | Refers to | Source |
|---|---|---|---|
| SpareRoom index, Greater London | **£915/mo**, −0.2% YoY | Q2 2026 (pub. Jul 2026) | [london-rents-q2-2026](https://www.spareroom.co.uk/statistics/london-rents-q2-2026) |
| SpareRoom, Inner / Outer London | **£979** (+0.3%) / **£794** (−0.6%) | Q2 2026 | same |
| SpareRoom, UK average room | £761/mo | Q2 2026 | [rental index](https://www.spareroom.co.uk/content/info-landlords/rentalindex/) |
| Cheapest / dearest postcode | E12 Manor Park £729 · SW7 £1,599 | Q2 2026 | london-rents-q2-2026 |
| Zone 2–3 student belt | E17 £842 · N15 £863 · E15 £899 · SE4 £917 · E3 £946 · SE14 £947 · SE15 £952 · E16 £979 · SE8 £983 · SW2 £986 · N7 £1,019 · SE16 £1,042 | Jul 2026 | [by postcode](https://www.spareroom.co.uk/content/info-flatsharing/average-london-rent-by-postcode/) |

**Reading.** SpareRoom room rents are asking prices **with bills included** — the site's own methodology
note, and why a room looks cheap beside an ONS flat rent. The realistic zone 2–3 east/south student band
is **£840–£1,050, midpoint ~£950, bills in**; inner London adds ~£185/mo. Postcode groups: E £933, SE
£961, N £937. **No current ONS or London Datastore room figure exists**: PIPR has no room/HMO category, and the [London Datastore borough set](https://data.london.gov.uk/dataset/average-private-rents-borough-29j80) is Valuation Office Agency data stopping at March 2019.

## 2. A one-bedroom flat

| Figure | Value | Refers to | Source |
|---|---|---|---|
| **ONS PIPR, London, 1 bedroom** | **£1,752/mo**, +3.2% YoY | Jul 2026 (rel. 19 Aug 2026) | [PIPR monthly price statistics](https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics) |
| ONS PIPR, London, all property types | £2,317/mo, +3.0% | Jul 2026 | same |
| ONS PIPR, UK, 1 bedroom | £1,132/mo | Jul 2026 | [bulletin Aug 2026](https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/privaterentandhousepricesuk/august2026) |
| Inner London 1-bed (**derived**, mean of 13 boroughs) | ≈£1,974 (£1,456 Lewisham → £2,597 Kens. & Chelsea) | Jul 2026 | PIPR borough rows |
| Outer London 1-bed (**derived**, mean of 19 boroughs) | ≈£1,420 (£1,216 Havering → £1,722 Richmond) | Jul 2026 | PIPR borough rows |
| Rightmove asking rent, all types | London £2,791 · Inner £3,299 · Outer £2,418 | Q2 2026 (rel. 16 Jul 2026) | [Rental Trends Tracker Q2 2026](https://www.rightmove.co.uk/news/content/uploads/2026/07/Rental-Trends-Tracker-Q2-2026-2.pdf) |
| HomeLet, new tenancies, Greater London | £2,238/mo, +5.1% YoY | Aug 2026 | [homelet.co.uk/homelet-rental-index](https://homelet.co.uk/homelet-rental-index) |

**Reading.** Use **£1,752** as the London one-bed anchor: PIPR covers the whole rented stock, new and
existing tenancies, and is the only official monthly series. Rightmove and HomeLet are *new-let asking*
prices running 20–30% above it. Bills are **excluded** throughout. Mid-market one-bed anchors: Waltham
Forest £1,402, Lewisham £1,456, Greenwich £1,551, Newham £1,630, Southwark £1,843, Tower Hamlets £1,981.

## 3. University halls, 2026/27 (postgraduate)

Monthly equivalent = total contract cost ÷ (weeks × 7 ÷ 30.4375). All three include energy, water,
Wi-Fi and contents insurance, and all three run **51-week** PG contracts — the summer is paid for.

| Hall | Room type | £/week | **£/month** | Source |
|---|---|---|---|---|
| QMUL Aspire Point (PG) | shared bathroom / ensuite / studio | 209.37 / 244.09 / 329.07 | **910 / 1,061 / 1,431** | [qmul.ac.uk … fees](https://www.qmul.ac.uk/residences/college/fees/) |
| LSE Robeson House (PG) | ensuite | 226.10–264.60 | **983–1,151** | [LSE fee table PDF](https://www.lse.ac.uk/asset-library/table-of-accommodation-fees.pdf) (5 Mar 2026) |
| LSE Lilian Knowles (PG) | ensuite, commonest band / studio | 253.39 / 326.20 | **1,102 / 1,418** | same |
| KCL Vauxhall (PG) | non-ensuite in 4-bed / ensuite | 336.00 / 391.00 | **1,461 / 1,700** | [kcl.ac.uk … vauxhall](https://www.kcl.ac.uk/accommodation/residences/vauxhall) |
| KCL City / Vine Street (PG) | studio | 541.00 | **2,352** | [kcl.ac.uk … city-vine-street](https://www.kcl.ac.uk/accommodation/residences/city-vine-street) |
| KCL portfolio span | KAAS bursary rate £169/wk → Battersea £414/wk | — | — | [kcl.ac.uk/accommodation/residences](https://www.kcl.ac.uk/accommodation/residences) |

**Reading.** Halls run **£910–£1,700/mo ensuite**, **£1,418–£2,352/mo studio**, all-in — the cheapest
matches a private zone 2–3 room (§1), the dearest beats a private one-bed (§2). Cautions: **UCL's fee
page blocks automated reading (HTTP 403)**; **Imperial publishes no in-house PG fee table**, routing
postgraduates to GradPad and Scape; LSE's *hall pages* show 2025/26 bands labelled 2026/27 — use the PDF.

## 4. Private purpose-built student accommodation (PBSA)

| Figure | Value | Refers to | Source |
|---|---|---|---|
| Unite Students, London (32 sites) | **from £264/wk** (Arch View, Wembley) → £360/wk (East Central, EC1); bills, Wi-Fi and contents insurance in | 2026/27 | [unitestudents.com … london](https://www.unitestudents.com/student-accommodation/london) |
| Scape, London (7 sites) | from £301/wk (Wembley) → £675/wk (Bloomsbury); 51 wks standard, rent fixed for the contract | 2026/27 | [scape.com … london](https://www.scape.com/student-accommodation-london/) |
| Yugo Therese House (EC1) / The Curve (E1) | ensuite £445 / £341–£360 per wk; studio £510–£525 / £394–£462 | 2026/27 | [yugo.com … therese-house](https://yugo.com/en-gb/global/united-kingdom/london/therese-house) |
| iQ City (EC1) | ensuite £339.63/wk × 51 wks = £17,321; studio £569/wk | 2026/27 | [iqstudentaccommodation.com/london](https://www.iqstudentaccommodation.com/london) |
| **BONARD, Greater London PBSA average** | **£466/wk** — highest in the UK (UK average £270) | data to Jun 2026 *(secondary)* | [propertyweek.com … BONARD](https://www.propertyweek.com/news/uk-pbsa-enters-more-saturated-phase-with-stock-to-rise-23-bonard-reveals) |
| **Unipol/HEPI London**, private direct-let | ensuite **£341/wk** (50 wks) · studio **£462/wk**; all-London average £295/wk; 14% of rooms over £20,000/yr; max maintenance loan £13,348 < average rent £13,595 | 2024/25 (pub. Dec 2024) | [hepi.ac.uk … london edition](https://www.hepi.ac.uk/wp-content/uploads/2024/12/Priced-Out-The-Accommodation-Costs-Survey-2024-London-Edition-1.pdf) |

**Reading.** Direct-let ensuite is **£290–£450/wk (£1,255–£1,950/mo)**, studios **£375–£675/wk
(£1,625–£2,925/mo)**, bills in, on 44–51 week contracts. **Booking channel beats building**: Scape
Hammersmith is £514/wk direct but **£199.34/wk on Imperial's nomination**, and KCL holds KAAS rooms at
£169/wk where direct equivalents run £330–£450. 2026/27 is a buyer's market — PBSA occupancy fell to
**85.4%**, rent growth slowed to **2%**, incentives run at **4.2%** of advertised rent (£400–£2,040 cashback).

## 5. What a private renter pays on top of rent

| Item | Figure | Refers to | Source |
|---|---|---|---|
| Energy cap, typical dual-fuel direct debit | **£1,723/yr = £143.58/mo**, +4%; standing charges alone £308/yr = **£25.71/mo** before any usage | 1 Oct – 31 Dec 2026 (ann. 26 Aug 2026) | [ofgem.gov.uk … +4% from October](https://www.ofgem.gov.uk/press-release/energy-price-cap-will-rise-4-october-2026) |
| Energy for a one-bed (**derived**, Ofgem Low consumption values) | **£101/mo dual fuel · £52/mo all-electric**. Ofgem cut typical values on 1 Jul 2026 (elec 2,700→2,500 kWh, gas 11,500→9,500) | Oct – Dec 2026 | [TDCV decision](https://www.ofgem.gov.uk/sites/default/files/2026-05/Review%20of%20typical%20domestic%20consumption%20values%20decision.pdf) (27 May 2026) |
| Water — Thames Water assessed household charge | **one bedroom £626.34/yr = £52.20/mo** · single occupier **£46.03/mo**; company average £658/yr | 2026/27 | [assessed household charges](https://www.thameswater.co.uk/help/account-and-billing/understand-your-bill/assessed-household-charges) |
| Broadband | **£31.05/mo** average standalone fixed broadband; out-of-contract costs ~£7/mo more | Q2 2025 data, pub. 26 Feb 2026 | [Ofcom pricing report](https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/multi-sector/pricing/2025/pricing-and-consumer-engagement-report.pdf) |
| TV Licence | **£180/yr = £15/mo**; needed for live TV on any channel or for BBC iPlayer | from 1 Apr 2026 | [gov.uk … fee 2026/27](https://www.gov.uk/government/news/cost-of-tv-licence-fee-set-for-202627) |
| Council tax, London | average Band D **£2,068/yr = £172/mo**; Band C spread **Westminster £931 → Southwark £1,749/yr**; councils bill over **10** instalments by default, not 12 | 2026/27 (pub. 25 Mar 2026) | [gov.uk … council tax levels 2026-27](https://www.gov.uk/government/statistics/council-tax-levels-set-by-local-authorities-in-england-2026-to-2027/council-tax-levels-set-by-local-authorities-in-england-2026-to-2027) |
| Council tax, students | all-student household is **exempt (Class N) — but you must apply**; leave one non-student adult and it becomes 25% off with **that adult paying all of it** | current | [students](https://www.gov.uk/council-tax/discounts-for-full-time-students) · [who has to pay](https://www.gov.uk/council-tax/who-has-to-pay) |

**Reading (derived).** Bills before council tax: **£150–£210/mo solo** (all-electric to dual-fuel) and
**£60–£90/mo per sharer** in a 3–4 bed flat. Council tax for a sole non-student adult after the 25%
discount runs **£58/mo (Westminster Band C) to £131/mo (Southwark Band C over 10 instalments)** — borough
matters more than band. Traps: the exemption **needs every occupant to be a student**; **heat networks in
newer blocks sit outside the Ofgem cap**; **1 Apr 2027** raises all of these and returns electricity VAT to 5%.

## 6. Where students live, and what they pay

Save the Student, *National Student Accommodation Survey 2026* (pub. 3 Mar 2026; n=1,149; fieldwork Nov
2025 – Jan 2026): **36% private landlord, 31% university accommodation, 13% private halls, 13% family
home, 3% own property**. Average rent **London £793/mo** (UK £575), *down* 2.3% from £812; by type,
university accommodation £641 and private landlord £576. Self-selecting sample — a floor, not a market
rate. [survey 2026](https://www.savethestudent.org/money/surveys/national-student-accommodation-survey-2026.html) **Do not cite a "NatWest Student Living Index 2026"** — NatWest discontinued the
city index and its 2026 report has no rent figures; the £1,031.60 London figure online is fabricated.

## Realistic budget tiers for examples

| Tier | Rent pcm | Bills pcm | Council tax pcm | **All-in pcm** |
|---|---|---|---|---|
| **(a) Student sharing a room** — zone 2–3 east/south (§1) | £850–£1,050 bills-in, or £750–£950 bills-out | £0 if included, else £60–£90 (§5) | £0, all-student household (§5) | **£900–£1,100** |
| **(b) Funded postgrad / early professional, solo studio or one-bed** — mid-market borough (§2) | £1,400–£1,750 | £150–£210 (§5) | £0 student · £60–£130 professional | **£1,550–£1,960** student · **£1,650–£2,090** professional |
| **(c) Comfortable solo one-bed, newer building** — zone 1–2 (§2) | £2,000–£2,600 | £170–£240, heat network can exceed this (§5) | £70–£175 | **£2,250–£3,000** |

**How each was built.** (a) SpareRoom zone 2–3 sample £842–£1,042 bills-in, midpoint £950; cross-checks
at £910 (QMUL shared-bathroom hall) and £1,255+ (direct-let PBSA ensuite). Students themselves report
£793/mo (§6) — lower because that sample spans all tenures, outer London and living at home. (b) PIPR
one-bed £1,752, mid-market boroughs £1,402–£1,750; council tax = Band C less the 25% single-person
discount. **Note the inversion**: a hall or PBSA studio at £1,418–£1,475/mo all-in undercuts a private
one-bed once bills and council tax are added. (c) Inner-London mean £1,974 and Rightmove's £3,299 bracket it.

**Rules.** Never mix a bills-included room rent with a bills-excluded flat rent; never apply the UK-wide
£575 student average to London; always state the council-tax assumption — it is the biggest single swing.
