Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# What this skill does, and how to start

Read this when the user asks "what can this do", "how do I start", "what is this", or says they have no idea. Answer in the user's language. Keep the pitch short; keep the intake to one message.

## 1. The pitch (say it in the user's language, at this length)

**English**
> I check a London rental flat the way a careful surveyor would, using official and open UK data: the government energy certificate (true size, age, heating), police crime data, planning applications next door, the company behind the landlord or agent, deposit and money-protection rules, price against the local band, light, all-in monthly cost, and the commute with a backup line. You get a plain verdict (PASS / EDGE / CONDITIONAL / KILL) with every finding graded by evidence. I never guess: what I cannot reach, I ask you to paste. I can also sweep a whole area around your destination and compare buildings. You set the rules (budget, size, must-haves, deal-breakers), or if you have no idea yet, I explain the basics first and suggest defaults. Works from a chat box or with a full toolset; the report looks the same either way. I am a filter, not a replacement for viewing the flat and meeting the agent or landlord: they are partners in this, and we find you a home together.

**繁體中文**
> 我用英國官方與公開資料，像謹慎的驗屋師一樣審查一間倫敦出租公寓：政府能源證書（真實坪數、屋齡、供暖方式）、警方犯罪資料、隔壁的規劃申請案、房東或仲介背後的公司、押金與客戶資金保護規定、價格對照當地行情、採光、每月全部成本、通勤與備援路線。你會得到白話判決（通過／邊緣／有條件／淘汰），每一項發現都標明證據等級。我不猜：拿不到的資料，我會請你貼給我。我也能掃描你目的地周圍整個區域，比較各棟建築。規則由你定（預算、坪數、必要條件、地雷）；完全沒概念也沒關係，我先講基本常識，再建議預設值。在純對話框或有完整工具的環境都能用，報告長得一樣。我是篩子，不能取代實地看房與見仲介、房東；他們是這件事的合作對象，我們一起幫你找到滿意的家。

**简体中文**
> 我用英国官方与公开数据，像谨慎的验房师一样审查一套伦敦出租公寓：政府能源证书（真实面积、楼龄、供暖方式）、警方犯罪数据、隔壁的规划申请、房东或中介背后的公司、押金与客户资金保护规定、价格对照当地行情、采光、每月全部成本、通勤与备用线路。你会得到白话结论（通过／边缘／有条件／淘汰），每一项发现都标明证据等级。我不猜：拿不到的资料，我会请你贴给我。我也能扫描你目的地周围整个区域，比较各栋建筑。规则由你定（预算、面积、必要条件、雷点）；完全没概念也没关系，我先讲基本常识，再建议默认值。在纯对话框或有完整工具的环境都能用，报告长得一样。我是筛子，不能取代实地看房与见中介、房东；他们是这件事的合作对象，我们一起帮你找到满意的家。

Then offer the four starting points, as one line each:
1. **I have a listing** → paste the link or the page text and I vet it (the 12 checks).
2. **I have an area or a place I commute to** → I sweep around it and compare buildings.
3. **I have no idea** → I explain the basics (section 3) and ask six questions (section 2).
4. **I am about to sign, or I need somewhere for a few weeks first** → the move-in half: bridging stays (`axes/15`), passing the income check (`axes/16`), the first two weeks in the UK (`axes/17`).

Do not list the 12 axes in the pitch unless asked; do not mention vendors, models, or internal file names.

## 2. Intake: six questions, one message, a suggested default for each

Ask all six in one numbered message. Accept "don't know" for any: then use the default, say so, and move on. Write the answers into `profile.yaml`, show it back in plain words, and only then start vetting.

| # | Ask | Suggested default if unknown | Goes to |
|---|---|---|---|
| 1 | Where do you need to get to most days, and by what time? | none: this one must be answered | `commute.destination`, `commute.arrive_by` |
| 2 | The most you can pay per month for everything: rent, energy, water, broadband, council tax? | ask for a number; explain that rent alone is usually 80–90% of it in a modern flat | `budget.all_in_pcm_ceiling` |
| 3 | When do you need to move in, earliest and latest? | earliest = today + 3 weeks; latest = + 8 weeks | `move_in_window` |
| 4 | What kind of home and how much space? Studio, or a one-bedroom with a real door? | one-bedroom with a door, at least 450 sq ft indoors (government-certificate measure; balconies don't count) | `flat_type`, `separate_bedroom_required`, `min_floor_area_sqft` |
| 5 | Deal-breakers: pick from the menu below or add your own | ground floor; windows that cannot see sky; no washing machine | `avoid`, `floors`, `light`, `must_haves` |
| 6 | How will you pass the landlord's income check? | if unknown, explain the three routes in section 3 and set "don't know yet" | `guarantor_route` |

Optional, only if the user is engaged: floor band, light versus quiet, top three priorities, nice-to-haves.

**Deal-breaker menu** (plain words → what the skill checks):

| The user says | Profile field | Check |
|---|---|---|
| "no ground floor" | `floors.reject_ground_floor: true` (default false: ground and lower-ground get extra checks, not a veto) | L10 floor and numbering |
| "I need to see sky / I hate dark flats" | `light.reject_no_sky: true`, `quiet_over_light: false` | L2 obstruction |
| "quiet matters most" | `quiet_over_light: true`, avoid "main road or railway facade" | L4 facade |
| "no building works next door" | avoid "active works during tenancy" | L5 works |
| "no surprise bills" | avoid "heat network without a written tariff" | L6 heat network and billing |
| "someone I can actually complain to" | avoid "management with no resident route to replace it" | L7 management |
| "no party neighbours / hotel-style" | avoid "short-let or student churn neighbours" | L9 churn |
| "no summer oven / no smells from the vents" | avoid "no cooling", "shared ventilation odours" | L11 cooling and ventilation |
| "washing machine in the flat" | `must_haves: washing_machine_in_flat` | axis 12 |
| "I want a new building" | `max_building_age_years: 10` | axis 3 |
| "advertised size must be real" | (always on) | L1 area illusion |
| "landlord must be a company / must be protected deposit" | `tenancy.require_deposit_protection: true` | L12 landlord type and money gate |
| "I need somewhere for a few weeks first" | see `axes/15-bridging-short-lets.md` | L13 licence not tenancy, L16 headline price |
| "I have no UK guarantor" | `guarantor_route`, see `axes/16-referencing-and-proof-of-funds.md` | L14 money gate, L15 non-refundable fees |

## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)

1. **Timing.** Listings appear about four to eight weeks before the move-in date; good flats go within days. The order is: enquiry → viewing → "referencing" (income and identity checks) → holding deposit → contract → deposit → keys.
2. **What you pay.** Rent, plus council tax (full-time students are exempt: Class N), energy, water, broadband. Buildings on a **heat network** (one boiler for the whole building) bill heat separately through a billing company: ask for the tariff in writing before you sign.
3. **The law since 2026-05-01** (Renters' Rights Act 2025): tenancies are periodic (no fixed term), the landlord cannot take more than **one month's rent in advance**, the deposit is capped at **five weeks' rent**, a holding deposit at **one week**, and the deposit must go into a government-approved protection scheme.
4. **The income check.** Landlords usually want yearly income of roughly thirty times the monthly rent, or a guarantor. If you have neither, there are rent-guarantee or "commercial guarantor" services many landlords accept. Ask every landlord first: "which guarantor routes do you accept?"
5. **The energy certificate (EPC) is your friend.** It is public, free, and gives the true indoor size, the building's first assessment year (≈ its age) and the heating type. Advertised sizes often include the balcony.
6. **Who the landlord is matters more than the brand.** Purpose-built rental buildings are run by companies with on-site management; private landlords vary from excellent to absent. The legal entity on the contract is what counts; the skill looks it up.
7. **Money safety.** Never pay anything before you have viewed (in person or on a verified live video) and have a written tenancy. Deposits go to a protection scheme, never to a personal bank account. Requests to move to WhatsApp or to transfer money "to secure it" are a reason to walk.
8. **Never sign on the viewing day.** Sleep on it. Ask two questions that could kill the deal (the skill writes them for you).
9. **Streets, roads, rails.** Police crime data is public by street; roads and railways are on the map; ask which side the windows face. "Quiet side or road side" is often the same price for two different homes.
10. **Where to look.** The big listing portals, the rental operators' own sites, and resident-review sites. The skill tells you exactly what to open and paste; it does not scrape them.

Then say: "First step: give me your destination and the most you can pay all-in, and I will sweep around it."

## 4. Short answers to common questions

- **Only London?** The law is England-wide; the data sources and the crime/commute tooling are London-specific. Elsewhere the method applies with different sources.
- **Do you scrape Rightmove / Zoopla / HomeViews?** No. Their terms forbid it. I ask you to paste the page.
- **Can I use it on ChatGPT, Gemini, DeepSeek, Grok, Codex?** Yes. With a shell and internet I fetch the data myself; in a chat box I list what to paste, once.
- **Where does my data go?** Only to the public sources listed in `references/sources.yaml`, and only what is needed for the lookup. Nothing goes to the author.
- **Does it decide for me?** No. It gives a verdict with the evidence behind it; you decide, after viewing the flat and meeting the people who let it. Landlords and agents are partners here, not opponents.
- **How accurate is it?** Facts come from official registers and are graded; anything unknown is shown as unknown, never filled in.
- **What does a report look like?** A verdict card, your must-haves versus the flat, a comparison table, the worst reviews, the landmines, the twelve checks, questions for the viewing, what could not be found, and the sources with dates.
