# Pea Princess (vet-flat) — review bundle for an external reviewer

Generated 2026-09-05 from the public repository (private data excluded). Each section below is one file, verbatim.

## Table of contents
- README — `README.md`
- Install guide — `docs/INSTALL.md`
- SKILL.md (the model-facing instructions, under 8,000 chars) — `skills/vet-flat/SKILL.md`
- Onboarding: pitch, intake, primer — `skills/vet-flat/references/onboarding.md`
- Budget modes and the escalation ladder — `skills/vet-flat/references/budget-modes.md`
- Ask-the-user protocol — `skills/vet-flat/references/inputs.md`
- Question bank — `skills/vet-flat/references/questions.md`
- Profile template — `skills/vet-flat/profile.template.yaml`
- Axis 00 area sweep — `skills/vet-flat/references/axes/00-area-sweep.md`
- Axis 01 — `skills/vet-flat/references/axes/01-identity.md`
- Axis 02 — `skills/vet-flat/references/axes/02-floor-area.md`
- Axis 03 — `skills/vet-flat/references/axes/03-age-fabric-heating.md`
- Axis 04 — `skills/vet-flat/references/axes/04-construction-nearby.md`
- Axis 05 — `skills/vet-flat/references/axes/05-crime.md`
- Axis 06 — `skills/vet-flat/references/axes/06-management-neighbours.md`
- Axis 07 — `skills/vet-flat/references/axes/07-compliance-landlord.md`
- Axis 08 — `skills/vet-flat/references/axes/08-price.md`
- Axis 09 — `skills/vet-flat/references/axes/09-aspect-light.md`
- Axis 10 — `skills/vet-flat/references/axes/10-all-in-cost.md`
- Axis 11 — `skills/vet-flat/references/axes/11-commute-redundancy.md`
- Axis 12 — `skills/vet-flat/references/axes/12-livability.md`
- Axis 13 — `skills/vet-flat/references/axes/13-adversarial-review.md`
- Axis 14 — `skills/vet-flat/references/axes/14-site-visit.md`
- Axis 15 — `skills/vet-flat/references/axes/15-bridging-short-lets.md`
- Axis 16 — `skills/vet-flat/references/axes/16-referencing-and-proof-of-funds.md`
- Axis 17 — `skills/vet-flat/references/axes/17-uk-admin-pitfalls.md`
- Thresholds — `skills/vet-flat/references/thresholds.yaml`
- Sources catalogue (tested 2026-09-03) — `skills/vet-flat/references/sources.yaml`
- Borough catalogue summary — `skills/vet-flat/references/boroughs-summary.md`
- Scripts usage — `docs/SCRIPTS.md`
- Experiments: A/B and ablation results — `docs/EXPERIMENTS.md`
- Benchmark README — `bench/README.md`
- A/B harness README — `bench/ab/README.md`
- Conventions — `docs/CONVENTIONS.md`


---

## README — `README.md`

````markdown
# Pea Princess · 豌豆公主 (`vet-flat`)

**EN** — A vendor-neutral agent skill that vets a London rental flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, all-in cost and commute, from official and open UK data, ending in a plain-language verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Gemini CLI, Grok CLI, Cursor, Copilot, OpenCode, Cline, Goose, OpenHands, Kimi Code, Qwen Code, pi, OpenClaw, Hermes Agent…) and, in reduced modes, with chat products that cannot run scripts.

**繁中** — 這是一個不綁定任何廠商的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣審查一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出白話判決。任何支援 Agent Skills 格式的 agent 都能用；只能對話不能跑程式的產品也能用「精簡模式」。

> Status: **draft** (2026-09-03). Nine fetchers, the report schema, both renderers, 15 axis references, onboarding, the question bank, budget modes and the benchmark are in; the area-sweep orchestrator is in progress. Docs: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.

## Three modes
| Mode | You have | What happens |
|---|---|---|
| Shell | python3 + curl + internet | Scripts fetch and parse; the model reads only compact JSON |
| Fetch | a URL-fetch tool, no shell | Open GET sources only; the skill asks you for the rest |
| Manual | a chat box | The skill lists the pages to open and paste, once, with links |

## Install
```bash
# most agents (Codex, Gemini CLI, Cursor, Copilot, OpenCode, Cline, Goose, pi, OpenClaw, Hermes…)
npx skills add jacky18008/pea-princess
# Claude Code
/plugin marketplace add jacky18008/pea-princess && /plugin install vet-flat@pea-princess
# claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
```
Codex: enable sandbox network (`sandbox_workspace_write.network_access = true`) or use manual mode.

## Scripts (Python 3.9 standard library only; network via curl)
All in `skills/vet-flat/scripts/`; each prints one JSON object with `source_url`, `retrieved_at`, `http_status`, `ok` and an evidence class. Usage details: `docs/SCRIPTS.md`.

| Script | Source (official? key?) | What it gives |
|---|---|---|
| `epc.py` | GOV.UK EPC register (official, no key; HTML only) | search by postcode/street, one certificate, whole-building profile (area distribution, first assessment year, heating, air permeability). Validated 10/10 floor areas |
| `geo.py` | postcodes.io (open) | postcode ↔ coordinates, nearby postcodes, hex-tile cover for a radius, bounding boxes |
| `crime.py` | data.police.uk (official, no key) | fixed 6-month window in a ~300 m box, categories, predatory subset, anchors, ±20 m sensitivity, walk-home corridor |
| `commute.py` | TfL Unified API (official, no key) | door-to-door journeys (all / rail / bus), nearby stations, strike-family redundancy grade |
| `company.py` | Companies House (official, no key) | search with status, profile (SIC, charges, officers, accounts), filings, registered-address search for resident management companies |
| `redress.py` | Client Money Protect, Heat Trust, GLA rogue landlord checker (open) | agent CMP membership, heat-network sites/suppliers, published enforcement actions; PRS/TPO are manual |
| `landregistry.py` | HM Land Registry price-paid linked data (official, no key) | transactions by postcode, earliest new-build sale as completion-year evidence; title register is manual (£7) |
| `planning.py` | GLA Planning Datahub (open; all 33 boroughs) | applications within a radius by geo distance, tall-building hint, decision conditions text |
| `roads.py` | OpenStreetMap via Overpass (open) | nearest main road, surface rail, tunnel portals, night economy, smell sources, supermarkets, obstruction candidates with bearing and angle |
| `render.py` | — | `report.json` → HTML or Markdown, validated against `references/report-schema.json` |

Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON.

## Start here, on any platform
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, `budget_mode` lite/standard/deep for £20 plans and chat-only use). The hard follow-up questions the agent must ask are in `references/questions.md`.

## Benchmark (facts must be right on every model; verdicts may differ)
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.

**Which configuration to run:** `docs/EXPERIMENTS.md` compares fifteen setups on five real flats against a human-built gold set of landmines, with a cost-versus-recall chart. The default it argues for is a cheap model for the extraction workers and the strongest model you have for the judgment — the tables are there so you can pick something else.

## Tests
```bash
python3 -m unittest tests/test_epc.py
```

## Sources you will not find here
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com are listed by name only. Their terms forbid automated access, so this project gives no method for them; the skill asks you to paste the page.

## Licence and attribution (proposed)
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with vet-flat <version> — <source URL>". Please keep it.
````

---

## Install guide — `docs/INSTALL.md`

```markdown
# Install (every channel) · 安裝方式（各平台）

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
Verified against vendor documentation on 2026-09-03; product features change, so check the linked pages if a step looks different.

## A. Agents with a shell (best experience — scripts run, the model reads JSON)

| Product | Install | Note |
|---|---|---|
| Claude Code | `/plugin marketplace add jacky18008/pea-princess` then `/plugin install vet-flat@pea-princess` | Local shell; full mode |
| Codex (CLI, IDE, app, cloud) | `npx skills add jacky18008/pea-princess -a codex` or in-session `$skill-installer install https://github.com/jacky18008/pea-princess` | **Sandbox network is off by default.** Enable with `codex -c 'sandbox_workspace_write.network_access=true'` or set it in `~/.codex/config.toml`; otherwise use manual mode |
| Gemini CLI | `gemini skills install https://github.com/jacky18008/pea-princess` | Needs a Gemini API key (or Code Assist Standard/Enterprise): consumer Google AI Pro/Ultra sign-in stopped on 2026-06-18; Antigravity CLI is Google's first-party route for those plans |
| Grok CLI | `npx skills add jacky18008/pea-princess -a grok` (also reads Claude Code marketplaces) | |
| Cursor · GitHub Copilot · OpenCode · Cline · Goose · OpenHands · Kimi Code · Qwen Code · pi · OpenClaw · Hermes Agent | `npx skills add jacky18008/pea-princess -a <agent>` (or omit `-a` to auto-detect) | All read the `.agents/skills/` convention or their own folder |
| Hermes Agent (alt) | `hermes skills install jacky18008/pea-princess` | Use an API key or a local model; do not sign in with a Claude subscription (see A2) |
| OpenClaw (alt) | `openclaw skills install git:jacky18008/pea-princess` | |

## A2. Which harness for the plan you already pay for (verified 2026-09-03)

The skill does not care which harness runs it. What decides your experience is whether your subscription is allowed inside that harness:

| You pay for | Use, with no extra cost | Also allowed | Not permitted / avoid |
|---|---|---|---|
| Claude Pro / Max | Claude Code, Claude Cowork | Cline, Goose (ACP) and OpenClaw, because they launch your own unmodified `claude` | pi and Hermes Agent signing in with your Claude account (they reuse Claude Code's login identity; Anthropic's policy forbids it). Use an API key or a local model there |
| ChatGPT (Free, Go, Plus, Pro, Business) | Codex (CLI, app, IDE), ChatGPT | OpenCode, Goose, Cline, OpenClaw via "Sign in with ChatGPT" (OpenAI documents this) | — |
| Google AI Pro / Ultra | Antigravity CLI (Google's own) | Gemini CLI with an API key | Any third-party harness on a Google consumer login (Google names and bans this) |
| SuperGrok / X Premium+ | Grok Build CLI | OpenCode (documented by xAI) | — |
| Nothing (or maximum privacy) | Ollama / LM Studio / llama.cpp with pi, OpenClaw, Hermes, OpenCode, Goose, Cline | any API key on pay-as-you-go | — |

**Which plan, from the author (personal experience, 2026-09; not a measured result).** At about £20 a month, ChatGPT Plus with Codex gives the most published headroom and the only numbers you can plan with (messages per five-hour window plus a credit rate card); Claude Pro works well in `lite` mode but publishes no usage figures and shares one pool with chat. At the top tier the author's daily experience is that Claude's largest model (Fable 5.1) is markedly stronger than GPT-5.6 Sol on the judgment parts of this work: reading the lowest reviews, naming what sits under a discount, deciding what to ask. That is an opinion from use, not a benchmark: the suite in `bench/` grades facts, not judgment, and the facts come from the scripts, so any model that runs them gets the same numbers. Run the benchmark on the plan you have and decide for yourself.

On a £20-a-month plan set `budget_mode: lite` in `profile.yaml` (see `skills/vet-flat/references/budget-modes.md`): a single flat takes fewer than ten fetches and still gets the hard filters, the verdict and the two killer questions.

## A3. Subscription or API key?

Subscription by default. This workload is cheap in absolute terms at pay-as-you-go prices (a `lite` check of one flat costs a few pence, an area sweep well under £1, a whole search of 20–30 flats and a few sweeps roughly £2–£20 on a mid-size model), so what a subscription buys is not savings but zero setup: no account, card, key, config file or bill to understand. Heavy users on £100+ plans get far more than the equivalent API spend; for this workload that only matters if you already pay for one.

| You are | Do this |
|---|---|
| Already paying ~£20 for a chat product | Use that vendor's own harness in `lite` or `standard` mode: Claude Pro → Claude Cowork; ChatGPT Plus → the Codex app, or paste the prompt pack into a Project; Google AI Pro → Antigravity. No API key |
| Paying nothing | A free ChatGPT account can sign in to Codex (limits unpublished); or any free chat box plus the prompt pack in manual mode |
| Running batch sweeps, or your plan's windows keep stopping you | Get an API key and use a cheap model (Gemini Flash, Grok build, Sonnet) in Codex, OpenCode or Gemini CLI: predictable, under £1 per sweep |
| On a £100+ plan already | `deep` mode everywhere; nothing to decide |

## B. Chat products with a Skills feature (upload the zip from Releases)

| Product | Steps | Network for scripts |
|---|---|---|
| claude.ai / Claude Desktop | Settings → Capabilities → enable "Code execution and file creation" → Customize → Skills → + → Upload a skill → the zip | On by default for Free/Pro/Max; **off by default on Team/Enterprise** (an owner enables it) |
| Claude Cowork | Same account: skills enabled on claude.ai sync automatically; or Customize → Plugins → "Add from a repository" → this repo's URL | Has a real browser and a shell in Anthropic's sandbox |
| ChatGPT (Skills) / ChatGPT Work | Skills → Create → Upload from your computer → the zip; invoke with `@vet-flat` | Available on Business / Enterprise / Edu plans at the time of writing (check your plan) |
| Gemini app (Skills) | Skills → upload | Scripts cannot reach the internet there, and the feature is not offered in the UK: use manual mode |

## C. Chat boxes without Skills (manual mode: paste the instructions, attach the references)

Use `dist/prompt-pack/` from Releases: `INSTRUCTIONS.md` (the SKILL.md text, under 8,000 characters) plus the reference files.

| Product | Where to paste | Limit |
|---|---|---|
| ChatGPT Free/Plus | Projects → Instructions; attach references as project files | 8,000 characters for instructions |
| Gemini app | Gems → Instructions; attach files | file upload needs a paid plan |
| Perplexity | Spaces → Instructions + files | — |
| Grok | Projects / Workspaces → Instructions | ~12,000 characters |
| DeepSeek, Kimi, Qwen, local models | Paste `INSTRUCTIONS.md` at the start of each session | nothing persists between sessions |

In manual mode the skill will list, once, the pages you need to open and paste (see `skills/vet-flat/references/inputs.md`).

## D. Verify
Ask: "Vet this flat: <address or postcode>, flat <n>." The first line of the answer states the mode (shell / fetch / manual). The report ends with "Generated with vet-flat <version> — https://github.com/jacky18008/pea-princess".
```

---

## SKILL.md (the model-facing instructions, under 8,000 chars) — `skills/vet-flat/SKILL.md`

```markdown
---
name: vet-flat
description: Due-diligence pipeline for renting a flat in London (UK). Given a listing or address, verifies identity, floor area, building age, heating, nearby construction, crime, management reviews, agent compliance, price, light, all-in cost and commute from official and open UK data, then writes a plain-language verdict (PASS / EDGE / CONDITIONAL / KILL) with evidence grades. Use when the user shares a London rental listing, asks whether a flat is any good, wants flats compared, or wants an area swept for candidates.
license: CC-BY-4.0
compatibility: Best with a shell and internet access (python3 + curl). Works in fetch-only or chat-only runtimes in reduced modes; the skill tells the user exactly what to paste.
metadata:
  author: "Hsien Hao (Jacky) Chen"
  source: "https://github.com/jacky18008/pea-princess"
  version: "1.0.0-draft"
  brand: "Pea Princess / 豌豆公主"
---

# vet-flat — London flat vetting

## 0. Pick your mode first (tell the user in one line which one you are in)
- **Shell mode**: you can run `python3` and `curl` with internet access. Run `scripts/*.py`; read only their JSON.
- **Fetch mode**: fetch only, no scripts. Use the open GET sources in `references/sources.yaml`; ask the user for the rest.
- **Manual mode**: neither. Ask the user to paste pages (`references/inputs.md`).

## 0b. If asked "what can this do", "how do I start", or "I have no idea"
Answer from `references/onboarding.md`: the short pitch in the user's language, then the starting points (a listing → vet it; an area or destination → sweep; no idea → primer and six intake questions; about to sign or need a bridge → axes 15–17; just arrived → ask about a hotel or operator-run stay first). Write the answers into `profile.yaml`, show it back, then start.

## 1. Load the profile
Read `profile.yaml` (hard filters: floor area, building age, budget bands, move-in window, commute destination and minutes, guarantor route, floor and light rules, must-haves, and `budget_mode` lite/standard/deep — see `references/budget-modes.md`). If it is missing, ask for the six essentials once (budget, area, age, move-in, destination, must-haves), then proceed and state your assumptions.

## 2. Two presumptions that run through every axis
1. **Cheap has a reason.** A price below the local band means the landlord or agent has a reason to sell you. Find it and name it. An unexplained discount is a reason to walk.
2. **Pay more only for a nameable benefit** (aspect, floor, quiet side, management).
3. **Landlords and agents are partners, not adversaries.** This skill is a filter; nothing replaces viewing the flat and meeting them.
Ask of every listing: "What sits under its prettiest feature?"

## 3. The 12 axes (method per axis in `references/axes/`)
1. **Identity** — exact flat number, building, postcode; the EPC register is the arbiter (`scripts/epc.py search`, `cert`). Big buildings span postcodes; search by street if needed.
2. **Floor area** — EPC internal m² only, balconies excluded; listing and floor-plan figures are claims.
3. **Age and fabric** — first EPC assessment year ≈ completion; heating class (heat network, gas, electric, heat pump); air permeability ≤ 5 implies mechanical ventilation; `scripts/epc.py building` profiles the whole building.
4. **Construction nearby** — planning applications within ~250 m, phase and decision dates; officer reports carry distance numbers; conditions being discharged show whether works start or finish.
5. **Crime** — data.police.uk, fixed six-month window in a ~300 m box; type mix; nodes on the walk home count in full; never scale up missing months.
6. **Management and neighbours** — reviews with incentivised and same-day-burst ones removed; read the lowest in full; move-out reviews weigh most; short-let footprint.
7. **Agent and landlord compliance** — legal entity on Companies House, redress scheme, client-money protection, deposit protection; landlord type (institutional > professional > absentee).
8. **Price** — £ per sq ft on EPC area against the local band; a discount must have a name; price-reduction history.
9. **Aspect and light** — floor-plan compass, sky openness, obstruction angle; quiet beats light unless there is almost none.
10. **All-in cost** — rent + bills model + council tax on one basis for every candidate.
11. **Commute and redundancy** — TfL door-to-door minutes; two independent rail families within a 10-minute walk.
12. **Low-maintenance living** — bundled bills, in-flat washing machine, parcel handling, blackout bedroom, shop within 3 minutes, direct route.
**Move-in half**: `references/axes/15`–`17` (bridging, referencing, first weeks); also `13` (adversarial review), `14` (site visit).
**Escalation ladder** (automatic): every flat starts at `standard` (scripts; cheap workers only for pasted text; strong judge). Go to `breadth` (one cheap reader per reading-heavy axis, in parallel) only for the final two or three flats, or a CONDITIONAL/EDGE verdict with over 40% of axes unknown. Four or more subagents at once always use the cheap tier. State the tier and reason on the report's first line (`generated_by.tier`, `escalation_reason`). Details: `references/budget-modes.md`.
**Area sweep** (compare everything around an address): shell mode `python3 scripts/sweep.py --anchor "<postcode>" --radius 800 --dest "<postcode>" --profile profile.yaml --out sweep/`; then read `sweep/summary.md` and `sweep/candidates/*.json`, and send the user `sweep/ask-the-user.md` once. Method: `references/axes/00-area-sweep.md`.
Legal facts (England, Renters' Rights Act 2025, in force 2026-05-01): periodic tenancies only, at most one month's rent in advance, deposit ≤ 5 weeks' rent, holding deposit ≤ 1 week; cite `references/sources.yaml`.
**Arithmetic is never done in your head.** Deposit caps, affordability multiples, all-in cost, £ per sq ft, bridging totals, break-even rent, guarantor fees and pro-rata rent come from `scripts/calc.py` (it prints every step); with no shell, write the formula and each step, then check it a second way.

## 4. Evidence grades — mark every finding
**G** official register · **S** self-reported (landlord, agent, listing) · **C** third-party (reviews, press) · **I** inference · **U** unknown. Two sources disagreeing is itself a finding. An HTTP 200 with the wrong page is not evidence.

## 5. Sources you may automate, and sources you may only name
Automatable open sources are catalogued in `references/sources.yaml`.
Named only, no method (terms forbid automated access): Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com. Ask the user to paste.
Per-borough portals: `references/boroughs.yaml`.

## 6. When you cannot get something
Follow `references/inputs.md`: try first; collect every gap; ask **once**, with URL, format and why; record `provenance: user_supplied`; mark the axis **U** if it stays unavailable. Never invent a number.

## 7. Output contract
Write `report.json` conforming to `references/report-schema.json`. Shell mode: `python3 scripts/render.py report.json > report.html`. Otherwise give the JSON for `viewer/viewer.html`. Also print the one-page verdict in the user's language.
Plain language everywhere: short sentences; no jargon without a gloss; every number says what it means and what it is compared with; evidence grades as plain labels.
Verdict: **PASS** · **EDGE** (with the break-even rent) · **CONDITIONAL** (conditions listed) · **KILL** (fatal axis named). Include: ≤2 killer questions from `references/questions.md`; viewing-day checks; a "not found" table with the search strings; sources with retrieval times; the footer "Generated with vet-flat <version> — <source URL>".

## 8. Never
Sign on the viewing day. Treat listing area as fact. Scale crime figures for missing months. Turn a missing item into a pass. Hide a red flag. Use ethnicity or nationality as a risk factor.
```

---

## Onboarding: pitch, intake, primer — `skills/vet-flat/references/onboarding.md`

```markdown
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
| 3 | When do you need to move in, earliest and latest? If you are arriving from abroad: would you consider a hotel or an operator-run serviced stay for the first one to two weeks, and a private short let only after you have seen it? | earliest = today + 3 weeks; latest = + 8 weeks; first weeks in a hotel or operator-run stay is the safer default (protected money, instant exit, someone responsible) at a known premium and usually without a kitchen | `move_in_window`, `bridging.first_weeks` |
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
- **I have just landed. Where do I sleep this week?** For the first one or two weeks a hotel or an operator-run serviced stay is the safer default: your money is protected, you can leave at once, and someone is responsible. A private short let is fine once you have seen it. It costs more per night and often has no kitchen; the skill will price both.
- **Does it decide for me?** No. It gives a verdict with the evidence behind it; you decide, after viewing the flat and meeting the people who let it. Landlords and agents are partners here, not opponents.
- **How accurate is it?** Facts come from official registers and are graded; anything unknown is shown as unknown, never filled in.
- **What does a report look like?** A verdict card, your must-haves versus the flat, a comparison table, the worst reviews, the landmines, the twelve checks, questions for the viewing, what could not be found, and the sources with dates.
```

---

## Budget modes and the escalation ladder — `skills/vet-flat/references/budget-modes.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Budget modes: the same checks at three depths

People on a £20-a-month plan share usage caps and smaller sandboxes; people with no tools at all paste pages by hand. The skill must still give them the basic functions: hard filters, a verdict, and the two killer questions. `profile.yaml: budget_mode` selects the depth. Default `standard`. The agent states the mode on the first line of the report and lists what was skipped. Depth also moves on its own during a run: see "The escalation ladder" below.

| | `lite` | `standard` | `deep` |
|---|---|---|---|
| Who | £20 plans, chat-only users, a first quick screen | most users | £100+ plans, final shortlists, area sweeps |
| Fetches per flat (shell mode, approx.) | ≤ 8 | ≈ 15–25 | 40+ |
| Identity and area | `epc.py search --postcode "<postcode>"` to list the flats, then `epc.py cert <certificate id>` for the matching flat (never pass an address to `cert`) | + `epc.py search` for the building's flats | + whole-building profile (`epc.py building`) and certificate history |
| Crime | `geo.py lookup "<postcode>"` for coordinates, then `crime.py box --lat <lat> --lng <lng> --months 3 --no-sensitivity` (4 calls) | 6 months, no sensitivity (6 calls) | 6 months + ±20 m sensitivity (30 calls) + route corridor |
| Commute | `commute.py journey --from "<postcode>" --to "<destination postcode>"` (postcodes work directly) | + rail and bus plans, `redundancy` | + `stations` detail and alternative arrival times |
| Company and compliance | `company.py profile` of the named entity | + `search` for same-name shells, `redress.py cmp`, `heat-trust` | + `filings`, `address-search` (RMC/RTM), `rogue`, `landregistry.py price-paid` |
| Planning | skip (state it) | `planning.py near --radius 250 --limit 20` | + `stages` on tall schemes, `roads.py near` |
| Reviews | ask the user for the lowest reviews only | full paste, incentivised and burst filters | + Trustpilot/press, cross-building matrix |
| Report | verdict card, hard filters, 2 questions, 12 axes with U where skipped | full | full + comparison |
| Area sweep | not offered; suggest `standard` | `sweep.py --radius 600 --max-buildings 6` | run several `--radius 1000` sweeps on different anchors (one per neighbourhood) with `--max-buildings 8` each; a single 3,200 m sweep trips the map service's rate limit and needs the filter caps raised |

## The escalation ladder (automatic)

Depth is not chosen up front. Every candidate starts at tier 1, and moves up only when a stated
trigger fires. Record where you ended up in the report: `generated_by.tier` and
`generated_by.escalation_reason`. Both renderers print them as the first line under the title, so the
reader can see how much machine was behind the words before reading a single finding.

| Tier | Name | What runs | When |
|---|---|---|---|
| 1 | `standard` | Scripts for every fetchable fact; cheap workers only for text the user pasted; the strongest model you have doing the judging. | The default for every candidate. Always start here. |
| 2 | `breadth` | One bounded reader per reading-heavy axis — reviews, planning, press, the landlord entity, the listing, the geometry — up to six, in parallel, on the cheap model. One document in, one small JSON object out. | Only on a trigger, below. |
| 3 | `manual` / `lite` | No shell: the user pastes, the model writes, the viewer renders. `lite` is the same shape with a fetch budget of about eight calls. | Chat-only runs, and £20 plans that have to stretch one window over many flats. |

**Escalate to `breadth` when either of these is true:**
- the candidate is in the final shortlist of two or three; or
- the verdict is CONDITIONAL or EDGE **and** more than 40 % of the axes are unknown (5 or more of the 12).

**Never start at breadth.** Run tier 1 first, escalate on a trigger, and say so in
`escalation_reason` ("final shortlist of three", "CONDITIONAL with 6 of 12 axes unknown"). Breadth
buys roughly 0.55–0.70 landmine recall up to about 0.85, and costs about five times the tokens and
twice the wall time (`docs/EXPERIMENTS.md`). That is worth paying on the last two or three flats and
wasted on a flat a hard filter kills in one line.

**Fan-out rule.** Whenever four or more subagents run at once, they use the cheap tier, whatever the
budget says. Fan-out, not depth, is what empties a subscription window: four parallel readers on the
strongest model burn more in a minute than a whole `standard` run.

**What the tier implies.** Tiers 1, 2 and `lite` run cheap workers with a strong judge; `manual` runs
no workers at all. The renderers print `Configuration: <tier> — <reason or "default">; workers:
<cheap|strong>; judge: <model_name>` under the title and again in "About this report". A report with no
`tier` prints "not stated", which is itself a finding about the report.

## What never gets cut
Hard filters from the profile · evidence grades · the "not found" table · the attribution footer · "never sign on the viewing day" · asking the user once, in one list, for what cannot be fetched.

## Chat-only users on any plan
The prompt pack (`INSTRUCTIONS.md` + references) plus `viewer.html` is the lite path: the user pastes the certificate page and the listing, the agent applies the filters and writes the report JSON, the viewer renders it. No fetch budget is consumed.

## Measuring it
`bench/run.py` records wall time and tokens when the CLI reports them; run the same case in `lite` and `standard` and keep the numbers in `bench/results/`. Target for `lite` on a single flat: under ten tool calls and one report.

## How much a £20 plan actually buys (checked 2026-09-03; these change often)
- **ChatGPT Plus → Codex** is the only £20 plan that publishes numbers: 10–100 messages per 5-hour window on the largest model, 250–2,000 on the smallest, plus a credit rate card. A `lite` run is one message, so tens of flats per window on the large model and hundreds on the small one; an undisclosed weekly cap sits behind that.
- **Claude Pro → Claude Code / Cowork** publishes no number ("at least 5× free"); one pool is shared with chat; the default model is the mid-size one and the largest is credits-only. Use `lite`, and split sweeps into ≤ 600 m runs.
- **Google AI Pro → Antigravity** publishes no number ("generous, refreshed every five hours until the weekly limit"). Gemini CLI needs an API key.
- **xAI** has no £20 tier; SuperGrok shows usage as a percentage of an unpublished allowance.
- **Pay-as-you-go is cheap per flat**: at list API prices a `lite` run costs a few pence and a sweep well under £1 on any vendor's mid-size model. If a plan's windows get in the way, an API key on a cheap model is the predictable route for batch sweeps.

## Which models
Two jobs, two different answers. Vendor names below are examples, not requirements: pick by role.

- **Extraction workers** — pull one stated number or fact out of one document (a saved reviews page, a planning officer's report, a tariff page, a certificate, a raw journey JSON). Use **the cheapest model that passes the worker eval** (`bench/ab/worker_eval.py`: fifteen tasks, exact match, no tools). A mid-tier model scored 15/15 on that eval at 42% of the cost of the top-tier model, which scored 14/15. Paying more here buys nothing.
- **Judgment** — the main loop: deciding what the numbers mean, applying the hard filters, weighing evidence grades, writing the verdict and the two killer questions. Use **the strongest model you have**. Across the measured arms this is the one substitution that moved the result: strongest main model 0.71 landmine recall, mid 0.57, cheapest 0.46.
- **If you only have one model**, put it on the judgment and cut axes instead.

### On a £20 plan
Keep `standard` mode and run **fewer axes**. Do not switch to `lite` with all twelve. Measured: `lite` on the strongest model found fewer landmines (0.38) than `standard` on the weakest (0.46), and `lite` runs invented numbers far more often (2.0–2.3 fabricated numbers per run against 0.3 in `standard`). Depth is what stops the model guessing; breadth is the part you can safely trade away. When you drop axes, say which ones and mark them `U`.

Full tables, method, caveats and the cost/recall chart: `docs/EXPERIMENTS.md` — https://github.com/jacky18008/pea-princess/blob/main/docs/EXPERIMENTS.md
```

---

## Ask-the-user protocol — `skills/vet-flat/references/inputs.md`

````markdown
# When the agent cannot get something: ask the user (the "you fetch, I read" protocol)

Part of Pea Princess (vet-flat). CC BY 4.0.

Many sources are open but not reachable from every runtime: some sandboxes have no
network, some fetchers honour robots.txt (the EPC register and council planning
portals disallow everything), some sites block bots, some need a login or a fee,
and some things (floor plans, the flat itself) are not on any API. **This is
normal. Do not guess, do not fabricate, do not silently skip the axis.** Ask.

## Rules for asking
1. First try what you can: run the scripts in `scripts/` if you have a shell and
   network; fetch open URLs if you only have a fetch tool.
2. Collect every missing item, then **ask once**, in one message, as a numbered
   list. For each item give: what you need, the exact URL or place to get it, the
   format you want back (paste text / upload file / a number), and why it matters
   (one short sentence). Never send one question per axis.
3. While waiting, continue with everything that does not depend on the answer.
4. Record what the user supplied with `provenance: user_supplied` and the date.
   Official documents supplied by the user (an EPC page, a Land Registry title,
   a planning decision) keep evidence class **G (official)**; what the user
   *tells* you (the agent said, the landlord said) is class **S (self-reported)**.
5. If the user cannot supply an item, mark the axis **U (unknown)** in the report
   with the reason. An unknown is never a pass.

## What to ask for, per axis

| Axis | Try first | If blocked, ask the user for | Where they get it | Format |
|---|---|---|---|---|
| Identity, floor area, age, heating | `scripts/epc.py search --postcode` then `cert` | The certificate page for the exact flat (or the search page listing all flats) | find-energy-certificate.service.gov.uk → "Find an energy certificate" → postcode | Paste the whole page text, or the certificate number |
| Whole-building EPC profile | `scripts/epc.py building --postcode` | Nothing; skip or ask for the search-page text | same | Paste |
| Floor plan and orientation | (no API) | The floor plan image and any developer plan with a compass | Listing page, developer brochure | Image upload (jpg/png/pdf) |
| Listing text, price history | (portal terms forbid automated access) | The listing page saved as HTML or its full text, plus the URL | Rightmove / Zoopla / OnTheMarket / OpenRent | "Save page as… (complete)" or select-all-copy |
| Owner / landlord entity | `scripts/company.py` (Companies House, open) | The Land Registry title register PDF | search-property-information.service.gov.uk (£7, needs GOV.UK sign-in) | PDF upload |
| Resident reviews | (site terms forbid automated access) | The full reviews page text for the named development | HomeViews, Google Maps, Trustpilot | Paste text (all pages, oldest first) |
| Planning near the site | GLA Planning Datahub (open) | Application numbers and the officer report PDF | The borough planning portal (see `boroughs.yaml`) | Paste numbers / upload PDF |
| Crime | `scripts/crime.py` (data.police.uk, open) | Nothing; open data | — | — |
| Commute | `scripts/commute.py` (TfL, open) | Confirm the exact destination address and arrival time | — | Text |
| Heat network supplier & tariff | Heat Trust members page (open) | The Welcome Pack tariff page | Landlord / agent | PDF or photo |
| Redress and client-money protection | Client Money Protect search (open) | Agent's CMP certificate and redress-scheme membership number | Ask the agent in writing | Photo / PDF |
| Anything on site (smell, noise, light, lift log, phone signal) | (never available remotely) | The viewing-day checklist answers | The viewing | Text / photos |

## Optional keys and logins (never required)
If the user has them, they go in `.env` next to the scripts and the scripts use
them automatically; otherwise the free HTML routes are used.

| Variable | Service | How to get | Benefit |
|---|---|---|---|
| `COMPANIES_HOUSE_KEY` | Companies House REST API | developer.company-information.service.gov.uk (free) | JSON instead of HTML, higher rate limit |
| `TFL_APP_KEY` | TfL Unified API | api-portal.tfl.gov.uk (free) | Higher quota |
| (download) | EPC open data CSV | get-energy-performance-data.communities.gov.uk (free GOV.UK One Login) | Bulk building data without page fetches |

## Template for the ask (copy, fill, send once)
```
I can finish X of 12 axes myself. To complete the rest I need 3 things:
1. EPC page for Flat 12, 4 London Bridge Street — go to
   https://find-energy-certificate.service.gov.uk, search postcode SE1 9SG, open
   the row for Flat 12, and paste the whole page here. (Sets the floor area, age
   and heating type; everything else keys off it.)
2. The floor plan image from the listing. (Orientation and windowless rooms.)
3. The HomeViews page text for "<development>", all review pages, oldest first.
   (Management score after removing incentivised reviews.)
Meanwhile I am running crime, commute, planning and company checks.
```
````

---

## Question bank — `skills/vet-flat/references/questions.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The question bank: what to ask the agent or landlord, and when

Every report's `killer_questions` (at most two) and the enquiry-letter pack are drawn from this bank. Pick by the landmine codes the checks raised; do not invent softer versions. Each question is written so that a vague answer is itself a finding.

## Rules of engagement
1. **First message: two questions at most** (the gate question plus the one that could kill this flat). Portal enquiry forms are short; a long first message gets a template reply. The full pack goes in the second round, after a human replies.
2. **Ask for documents, not opinions**: "send me the tariff page", not "are bills reasonable?".
3. **Write down the answer with its evidence class**: a written tariff is G; "the agent said about £120" is S.
4. **A non-answer is an answer**: silence or deflection on a gate question closes the file.
5. Never ask about, or volunteer, nationality, ethnicity, religion or immigration status.
6. **Ask as a partner, not a prosecutor.** The agent or landlord is the person who gets you the keys; the same questions asked of every flat, in a friendly tone, get better answers than an interrogation. A defect you find is shared information, not a charge.

## Gate questions (ask before any viewing effort)

| Code | Question (send verbatim) | Why | If the answer is... |
|---|---|---|---|
| G1 | "Which guarantor or income-check routes do you accept for this tenancy: a UK guarantor, rent-guarantee insurance, a commercial guarantor service, or proof of funds?" | The money gate; a mismatch wastes a viewing | "UK guarantor only, no alternatives" → out unless the user has one |
| G2 | "Is the flat still available for a move-in on or after {earliest date}, and what is the earliest date I could take the keys?" | Advertised availability is not verified availability | vague → treat as unverified |
| G3 | "Who is the landlord on the tenancy agreement (the legal entity), and who manages the flat day to day?" | Brand ≠ landlord; sets axis 7 | refuses → red flag |
| G4 | "Is the deposit held in a government-approved custodial scheme, and is client money protection in place? Please name the schemes." | Money safety, L12 | "we'll sort that later" → red flag |

## Questions by landmine

| Code | Landmine | Question |
|---|---|---|
| L1 | Area illusion | "What is the internal floor area excluding balconies, and does it match the energy certificate for this exact flat? Which certificate is it?" |
| L1 | Photos | "Are the photographs of this exact flat as it stands today, and when was it last refurbished?" |
| L2 | No sky / obstruction | "Which floor is the flat on, and what is directly outside the main living-room window: a building, a courtyard, or open sky? How far away?" |
| L3 | Walk home | "Which station entrance do residents use after dark, and is the route lit and on a main street?" |
| L4 | Road / rail facade | "Do the bedroom and living-room windows face the main road (or railway), or the courtyard / quiet side?" |
| L5 | Works nearby | "Is the development fully complete? Are any buildings, phases or neighbouring sites still under construction or approved to start during a 12-month tenancy?" |
| L6 | Heat network and billing | "Is heating and hot water on a communal heat network? Please send the current standing charge and unit rate in writing (the welcome-pack tariff page), and name the billing company." |
| L6 | Bills bundled | "Which bills are included in the rent, and which billing company or supplier do residents deal with for the rest?" |
| L7 | Management with no exit | "Who is the managing agent, is there a residents' management company or right-to-manage company, and what is the target time for repairs?" |
| L8 | Reviews | "How long did the previous tenant stay, and why did they leave?" |
| L9 | Churn | "Are all flats in the building let on assured (periodic) tenancies, or are some used for short lets, serviced stays or student lets?" |
| L9 | Sale risk | "Is this flat, or the building, currently marketed for sale, and what happens to the tenancy if it is sold?" |
| L10 | Floor and numbering | "Is any part of the flat at ground or basement level, and what does the energy certificate call the property type?" |
| L11 | Cooling and ventilation | "Is there comfort cooling or air conditioning? Is ventilation mechanical (MVHR/MEV) or natural, and is the system shared with other flats?" |
| L11 | Summer heat | "What temperature does the living room reach on a hot afternoon, and which direction do the main windows face?" |
| L12 | Landlord type | "Is the landlord an individual or a company, based in the UK, and how many properties do they let?" |
| L12 | Deposit amount | "The advertised deposit is {n} weeks of the advertised rent; will it be five weeks of the current rent on the contract?" |
| Cost | All-in | "What did the last tenant pay in total per month including energy, water and broadband? If unknown, what does the building quote as typical?" |
| Cost | Council tax | "What is the council tax band?" |
| Legal | Conversions | "What was the building's original use, and when was it converted to residential?" |
| Practical | Washing machine | "Is there a washing machine inside the flat (not a shared laundry)?" |
| Practical | Parcels | "How are parcels received when I am out: concierge, parcel room, lockers, or nothing?" |

## Viewing-day questions (in person; answers are S until seen)
- "Can I see the meter cupboard / heat interface unit and the last bill?"
- "Can I open a window and close it again while you are quiet for one minute?" (noise test)
- "Which flat is this on the fire-escape plan?" (exact unit identity)
- "Where is the lift maintenance record?"
- "Who do residents call at 11 pm when something floods?"

## Enquiry-letter skeleton (second round, after a human replies)
Intro (one neutral sentence from `profile.yaml.self_intro_template`) → the two gate questions not yet answered → at most five landmine questions ranked by what could kill the deal → a closing line asking for documents: energy certificate, floor plan with compass, tariff page, deposit scheme name.

## From the bridging and referencing lessons

New gate questions (axes 15–17). Ask G5 and G6 in the same breath as G1: a money gate you cannot pass makes every other answer worthless.

| Code | Question (send verbatim) | Why | If the answer is... |
|---|---|---|---|
| G5 | "Please send your published affordability criteria. What income or savings multiple applies to my applicant type, and is that multiple applied to the contractual rent or to any discounted rate?" | The affordability test is the real gate; a spoken multiple is not evidence | refuses to send a document → treat the multiple as unverified and do not view |
| G6 | "Which guarantor products do you accept, what does each charge for a twelve-month tenancy at this rent, and can I be referenced on proof of funds instead?" | Approved lists are set at group level; the savings route only exists if the landlord enables it | "our list is fixed and there is no savings route" → price the guarantor fee into the all-in before viewing |
| G7 | "If referencing does not complete, are the guarantor fee and the holding deposit refundable or transferable to another property?" | Both are commonly non-refundable; some products transfer, most fees do not | "nothing is refundable" → do not pay the guarantor fee until the holding deposit is confirmed exclusive |
| G8 | "Is the deposit five weeks of the contractual rent, held in a government-approved custodial scheme, and can you confirm the scheme and send the certificate once protected?" | The cap and the scheme are law, not preference; deposit-replacement products are a non-refundable fee | offers only a deposit-replacement product → reply "I'd prefer the traditional deposit in a custodial scheme" |

| Code | Landmine | Question |
|---|---|---|
| B1 | Bridge: contract type | "Is this a tenancy or a licence to occupy, is the deposit protected in a government scheme, and what is the latest date I could extend to?" |
| B2 | Bridge: total price | "What is the total for my exact dates, broken into rent, platform or admin fee, deposit, cleaning, and anything else? Which of council tax, electricity, water, heating and Wi-Fi are included?" |
| B3 | Bridge: who holds the money | "What is the contracting entity and its company number, will rent and deposit be paid to an account in that exact name, and can you send a current client-money-protection certificate?" |
| B4 | Bridge: refund right | "What is the cancellation deadline and what is refundable after it? Can I view, in person or by live video, before paying anything?" |
| B5 | Bridge: kitchen and laundry | "Does this unit have a private kitchen with a hob and oven, and is there a washing machine inside the unit? Where is it?" |
| B6 | Bridge: connectivity | "Is the included Wi-Fi a fixed line with unlimited data, or a mobile router, and what speed?" |
| B7 | Bridge: post | "Can post be received at the building in my name, and will the agreement show my name and the property address?" |
| B8 | Short-let churn in a long-let building | "How many flats in this building are let on assured shorthold tenancies, and are any operated as short stays or serviced apartments?" |
| B9 | Holding deposit exclusivity | "Please confirm in writing that this apartment is reserved exclusively for my application from the date of my holding deposit, including while the payment is clearing, and that no other holding deposit will be accepted for it." |
| B10 | Deadline for agreement | "What is the deadline-for-agreement date, and can it be extended in writing if the referencing check is slow?" |
| B11 | Concession | "Does this unit qualify for the advertised rent-free concession, will it be written into the offer, and is it paid as a lump or in instalments that are forfeited on early exit?" |
| B12 | Savings route | "As a self-funded applicant paying rent from savings, can the savings route be enabled on my check, what is the multiple, and over what look-back period?" |
| B13 | Statement format | "Will an official bank statement showing the account cover page plus three months of transactions with balances be accepted, and does it need to be in English?" |
| B14 | Utility charge | "What does the monthly utility charge cover, and how is any overage billed?" |
| B15 | Heat network tariff | "Please send the current standing charge per day and unit rate per kWh for the heat network in writing." |
| B16 | Council tax | "Is council tax included in this rate, and will you confirm the property is eligible for the full-time student exemption?" |
| B17 | Key handover | "If the move-in date falls on a Monday, can keys be released on the preceding Saturday?" |
```

---

## Profile template — `skills/vet-flat/profile.template.yaml`

```yaml
# Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
#
# Copy this file to `profile.yaml` next to it and fill it in. The skill reads `profile.yaml`
# and judges every flat against it; whatever you leave blank, the skill will ask about once
# and then state as an assumption in the report.
#
# Rules for this file:
#   * Personal values are deliberately left BLANK here. Do not commit your own profile.yaml.
#   * Money is pounds sterling. Areas are square feet indoors, measured the way the government
#     energy certificate measures them (balconies and terraces do not count).
#   * Anything you write here is copied into the report as `profile_snapshot`, so a reader can
#     see the ruler that was used. Do not put anything here you would not want in the report.
#   * Never put ethnicity, nationality, religion or immigration status in this file. The skill
#     will refuse to use them and they are not lawful grounds for filtering anything.

# ---------------------------------------------------------------- hard filters
# These are pass/fail. A flat that misses one is not "a bit worse"; it is out, or it is an
# exception you make on purpose and write down.

# Smallest indoor area you will live in, in square feet, from the energy certificate.
# Leave blank if you have no floor. Typical one-bed floors people set: 450-550.
min_floor_area_sqft:

# Oldest building you will accept, in years. Leave blank for no limit.
# Note this is about the building fabric, not charm: older usually means worse sound
# insulation, no mechanical ventilation, and single-supplier heating is less likely.
max_building_age_years:

# What kind of home. One of: studio | one_bed | two_bed | three_bed_plus | any
flat_type: one_bed
# true = the bedroom must have a door and a window. A "studio suite" with a bed alcove does not count.
separate_bedroom_required: true
# How many people will live there.
occupants: 1
# How deep the checks go: lite | standard | deep. lite = few fetches, fits £20 plans and chat-only
# use; standard = default; deep = everything, for final shortlists and area sweeps.
# See references/budget-modes.md for exactly what each level runs.
budget_mode: standard

# OPTIONAL. Which model does which job. Leave the whole block commented out and the agent uses
# whatever it is already running; nothing here is required and nothing breaks if it is absent.
# Two jobs, two answers:
#   workers: cheap   -> extraction only (pull one stated number out of one pasted document).
#                       The cheapest model that passes the worker eval is enough; a bigger one
#                       measured no better and cost more than twice as much.
#   judge:   strong  -> the main loop: what the numbers mean, the hard filters, the verdict.
#                       The strongest model you have. This is the substitution that moved the score.
# Vendor names are your choice — write whatever your agent understands, or leave the words
# "cheap" and "strong" and let the agent map them. The numbers behind this are in
# docs/EXPERIMENTS.md (https://github.com/jacky18008/pea-princess/blob/main/docs/EXPERIMENTS.md).
# models:
#   workers: cheap
#   judge: strong

# How much you already know about renting in London: none | some | expert.
# "none" = the skill explains each term the first time and suggests defaults instead of asking open questions.
experience: none

# Your deal-breakers in plain words, one per line. The skill maps them to its checks
# (menu in references/onboarding.md). Examples:
#   - ground floor
#   - windows that cannot see sky
#   - heat network without a written tariff
#   - main windows facing a main road or railway
#   - building works next door during my tenancy
#   - short-let or hotel-style neighbours
#   - no washing machine in the flat
#   - management with no resident route to replace it
avoid:
  - ground floor

# Your top three priorities, in order. Words such as: quiet, light, price, space, commute,
# new building, bills included, on-site management, outdoor space.
priorities:
  - quiet
  - commute
  - price

budget:
  # What you want the rent itself to be, per month, before bills.
  rent_pcm_target:
  # The hard ceiling on rent PLUS bills PLUS council tax, per month. This is the number the
  # report compares against. If you only set one budget number, set this one.
  all_in_pcm_ceiling:
  # If you would go above the ceiling for something specific, say what and by how much, in one
  # sentence. Example: "Up to 150 more per month only for a second rail line within 8 minutes."
  # An unnamed stretch budget becomes your real budget within a week.
  stretch_ceiling_and_conditions:

# Where to sleep for the first one or two weeks after arriving: hotel_or_operator | private_short_let | undecided.
# Hotel or operator-run stays protect your money and let you leave at once; private short lets are
# cheaper and have kitchens but should be viewed first (see references/axes/15-bridging-short-lets.md).
bridging:
  first_weeks: undecided

move_in_window:
  # Earliest date you can take the keys, as YYYY-MM-DD.
  earliest:
  # Latest date you can take the keys, as YYYY-MM-DD.
  latest:
  # How many days either side you can absorb (hotel, storage, a friend's sofa).
  # Set 0 if a date miss kills the deal.
  tolerance_days: 0

commute:
  # Where you must get to most days: a full address or a station name. Required.
  # The skill has no default destination and will not guess one.
  destination:
  # The time you have to arrive, as HH:MM, 24-hour. Journey times are measured for this time,
  # because a 20-minute trip at 11:00 can be a 40-minute trip at 08:45.
  arrive_by: "09:00"
  # The longest door-to-door journey you will accept, in minutes, including both walks.
  max_door_to_door_min:
  # Minimum backup grade you will accept when one line stops:
  #   A = two independent rail lines within a 10-minute walk
  #   B = one rail line plus a bus route that actually works for this journey
  #   C = one line only, no plan B
  redundancy_min_grade: "B"

floors:
  # Ground and lower-ground flats are a caution, not a no. Plenty are fine; they need extra checks
  # for damp and mould, security, privacy and light (see references/axes/14-site-visit.md).
  # Set true only if you already know you will not take one.
  reject_ground_floor: false
  # The floors you actually want, as a range like "2-8". High floors trade lift dependence
  # and summer heat for light and quiet. Leave blank if you have no preference.
  prefer_floor_band:

light:
  # true = a flat whose main windows cannot see sky is an automatic no, whatever else it has.
  reject_no_sky: true
  # Score each compass direction 0-5 for how much you want it. These are preferences, not
  # filters: they break ties, they do not kill candidates.
  # In London: south is bright and hot, north is even and dim, east is morning light,
  # west is evening light and evening heat.
  aspect_scores:
    N: 2
    NE: 2
    E: 4
    SE: 5
    S: 4
    SW: 4
    W: 3
    NW: 2

# true = when light and quiet conflict, quiet wins. Set false only if you know that a dim
# flat makes you miserable faster than a noisy one does.
quiet_over_light: true

# ------------------------------------------------------- must-haves and extras
# Plain words, one per line. A must_have that fails is a hard fail, so keep this list short
# and honest. Anything you would trade away belongs in nice_to_haves.
must_haves:
  - washing_machine_in_flat
  # - separate_bedroom_door
  # - openable_windows
  # - parcel_room_or_concierge

nice_to_haves:
  # - dishwasher
  # - blackout_blinds_in_bedroom
  # - bike_storage
  # - supermarket_within_3_min_walk
  # - lift
  # - balcony

# ------------------------------------------------------------- money gate
# How you will satisfy the landlord's income test. Landlords in England usually want annual
# income of about 30 times the monthly rent, or a guarantor, or rent paid up front.
# One of: "UK guarantor" | "rent guarantee insurance" | "overseas guarantor" |
#         "proof of funds only" | "none needed"
guarantor_route:

tenancy:
  # The most months of rent you are willing to pay before you move in.
  # In England since 2026-05-01 the legal maximum is 1. Leave this at 1: a landlord who asks
  # for six months up front is telling you something, and it is not about your credit file.
  max_months_upfront: 1
  # The most weeks of rent you will hand over as a deposit. The legal cap is 5.
  max_deposit_weeks: 5
  # true = the deposit must be held by a government-approved scheme, confirmed in writing.
  require_deposit_protection: true

# --------------------------------------------------------- how you introduce yourself
# One neutral sentence the skill can adapt into an enquiry. Fill the placeholders in and keep
# it to facts a landlord may lawfully ask about: what you do, how many people, smoking, pets,
# whether you can prove funds, how you cover the income test.
# Never add nationality, ethnicity, religion or visa status: it is not lawful ground for a
# landlord to select on, and volunteering it invites exactly that.
self_intro_template: >-
  I am a {occupation} looking for a home for {occupants}, non-smoking, {pets},
  able to provide {proof_of_funds}, with {guarantor_route} for the income check.

# Language for the report: a BCP-47 tag such as en, zh-TW, zh-CN, ja, ko, fr.
# The findings are written in this language; the layout labels are translated by the renderer.
language: "en"
```

---

## Axis 00 area sweep — `skills/vet-flat/references/axes/00-area-sweep.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 0 — Area sweep

## Purpose
Sweep a whole area for candidates instead of vetting one flat: enumerate every building that could qualify, filter cheaply, then vet only the survivors.
The twelve axes are the per-building method; this file is the order in which they are run over many buildings without exhausting the budget.

## The cost gate (read this before starting)
Enumerate cheaply, read expensively, and only at the end.
1. Cheap and mechanical: geocoding, postcode coverage, the energy register, the crime and journey APIs, the company register, the planning index. All of it goes through scripts.
2. Free: filtering that list by distance, age, area, floor and price band.
3. Moderate: asking the user to paste review pages for the survivors only.
4. Expensive, and last: the agent reading review text and officer reports.
**The agent reads compact JSON and pasted excerpts. It never reads raw pages.** The compression happens in the scripts; if page text reaches the agent, the sweep costs several times what it should.
Deep review reading is done only inside `sweep_deep_read_radius_m`, even when the enumeration radius is `sweep_radius_m`.

## Stage 0 — Anchor
- Anchor on a **real street address or postcode**, never an area name: "two kilometres around this address", not "around this district".
- `python3 scripts/geo.py lookup "<postcode>"` for the official coordinates, borough, ward and statistical areas.
- A map pin on a listing portal is never geometry. Neither is a police snap point.
- Record the radius, the anchor and the date at the top of the report; every later number is relative to them.

## Stage 1 — Enumerate (take the union of two routes)
1. **Energy-register postcode census.** `python3 scripts/geo.py cover --lat <lat> --lng <lng> --radius <m>` gives the postcodes inside the circle (the underlying radius search caps at `nearest_postcode_max_radius_m` and silently ignores a larger value, so page the circle rather than asking for one big one); then `python3 scripts/epc.py search --postcode "<pc>"` for each, and `python3 scripts/epc.py building --postcode "<pc>" --match "<name>"` for each building worth expanding. Where high floors are missing, search by street instead.
2. **A user-supplied list.** Listing portals and resident-review sites cannot be enumerated automatically; ask the user to paste the search results or the names of the developments they already know, and merge that list in. See `inputs.md`.
Deduplicate by building, not by listing: one building split across postcodes is one candidate, and two flats in the same building are one entry with two units.

## Stage 1b — Exclude
Drop, with a reason recorded for each:
- purpose-built student accommodation and halls;
- serviced apartments and aparthotels;
- blocks that are entirely social or affordable housing, and waiting-list stock;
- anything whose coordinates land outside the circle (a name collision with a development elsewhere);
- buildings with no residential certificates at all.

## Stage 2 — Hard filter (mechanical, from register data only)
- First assessment year and building age against `max_building_age_years`.
- Certified internal area against `min_floor_area_sqft`.
- Floor position from the certificate's property type against `floor_position_exclusions`.
- Advertised price band against `rent_ceiling_pcm`.
Anything that fails here never reaches a script that costs money. Record the count in and the count out.

## Stage 3 — Per-building facts (scripts only, capped)
Cap the deep lines at `sweep_max_deep_lines` buildings. For each, run and store **one compact JSON record**, every field carrying `source_url`, `retrieved_at` and `evidence_class`:
`epc.py building` · `crime.py latest` then `crime.py box` · `commute.py journey`, `stations`, `redundancy` · `planning.py near` and `stages` · `roads.py near` · `company.py search`, `profile`, `address-search` · `redress.py cmp|prs|tpo|rogue|heat-trust` · `landregistry.py price-paid`.
No page text is kept. The record is the input to every later stage.

## Stage 4 — Worst-review surgery (paste mode)
For the survivors only, ask the user once for the review pages, then run the full review hygiene in `06-management-neighbours.md`:
remove incentivised reviews, remove same-day bursts of `review_burst_same_day_min` or more, read the lowest reviews in full, weight move-out reviews highest, treat a building with no natural sample in `review_staleness_years` as unmeasured, and never read a zero denominator as clean.
Attach every score to a **building**, not to a development or a brand.
Cross-check the same building against other sources — hyperlocal news, planning objections, tribunal and company records — because for a small block with no reviews those are the better evidence.

## Stage 5 — Adversarial pass (two lenses)
Give every surviving candidate a fresh reviewing agent that has not seen the first pass, working two lenses:
- **Lens A — landlord, management, bills:** who owns it, who manages it, what the money gate looks like, what the bills really are.
- **Lens B — noise, works, commute, street:** what is being built, what the facade faces, whether the journey survives a strike, what the walk home is like.
Every objection must be written in the five-column format in `13-adversarial-review.md` and must name a **release condition** — the evidence that would retire it. An objection with no release condition is not a valid objection.
Every reviewer must also file a **"checked but not proven"** list: the defects they looked for and did not find. Without it, a reviewer under pressure invents findings.

## Stage 6 — Integration
Produce, in this order:
1. **Coverage and denominator table** — how many buildings were enumerated, excluded, filtered, vetted; and for each source, what was searched and what came back empty.
2. **Comparison table**, one row per building: original verdict, verdict after the adversarial pass, organic management score and invited share, harshest review theme, commute and redundancy grade, residual crime reading, distance to works, best available unit and its all-in cost, landlord type.
3. **Worst-review matrix**: building, distance, source, date, score, organic or not, and a short verbatim excerpt.
4. **Structural versus single-building findings.** A theme found across at least `structural_finding_min_developments` buildings and at least `structural_finding_min_years` years is structural and may be generalised to the area. Anything narrower is a single-building defect and may not.
5. **Red flags and green lights**, each with a grade, a source class, and whether it is reversible; plus the "not found" table carrying the exact search strings used.
6. **Ranking by quality × probability of closing.** Score quality on the twelve axes and multiply by the chance the deal actually completes. Enquiries change the probability, not the quality — that is what the letters are for.
7. **At most `sweep_max_decision_questions` decision questions** put back to the user, and a per-candidate list of at most two questions for the agent.
8. A viewing-day plan: what must be in writing before leaving the house, at most three flats in one area in a day, and the on-site-only list from `14-site-visit.md`.

## Traps and lessons
- **Name collisions.** Two developments can share a name in different postcodes; check the postcode before moving any review, crime figure or planning record between them.
- **Two flats in one building are not two options.** They share the works risk and the crime box.
- **Nil results are queries, not facts.** Record every search string that returned nothing, so a later reader can tell "there is nothing" from "we did not find it".
- **One fixed geometry for every candidate.** Same box, same window, same journey basis, same bills model — otherwise the table compares methods rather than flats.
- **The enumeration is the cheap part and the reading is the expensive part.** If the budget is running out, cut the number of deep lines, never the hygiene steps.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract. A sweep produces one `candidates[]` entry per building that reached stage 3, each with its twelve `axes[]`, and then fills the sweep-level containers:
- `comparison.ranking[]` — `candidate_id`, `quality_score`, `closing_probability`, `expected_value`, `reason`. Quality is the twelve-axis score; the enquiry letters move the probability, not the quality.
- `comparison.structural_findings[]` — `theme`, `detail`, `buildings_count`, `years`, `generalisable`, `sources`. Set `generalisable` true only when both structural thresholds are met.
- `comparison.single_building_findings[]` — `building`, `theme`, `detail`, `generalisable: false`, `sources`.
- `not_found[]` — `what`, `queries_used` (the exact strings), `where_looked`, `next_step`. This is the coverage table; a sweep without it cannot be audited.
- `blocked_sources[]` — `source`, `http_status`, `reason`, `workaround`, for everything that refused, challenged or returned the wrong page.
- `sources[]` — every source used, with `id` matching `sources.yaml`, `retrieved_at`, `evidence_class` and `provenance`.
- `profile_snapshot` — the ruler used, so a reader can see which filters produced this shortlist.
Keep the excluded buildings and the reason for each in the run's working notes, and summarise the counts in the sweep's opening section.
```

---

## Axis 01 — `skills/vet-flat/references/axes/01-identity.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 1 — Identity

## Purpose
Pin the exact flat: unit number, building, street, postcode, and the certificate that proves it exists.
Every other axis keys off this. If identity is unresolved, no axis above it can be graded better than U.

## What counts as evidence
- **G (official register)** — the EPC register row for the exact flat ("FLAT 16, 4 Example Street"); a Land Registry title register naming the same unit; a planning or licensing register entry for the address.
- **S (self-reported)** — the listing address, the agent's email, the operator's own unit schedule, a brochure unit number.
- **C (third party)** — a resident review or news article that names the building; an aggregator's copy of a listing.
- **I (inference)** — a floor read off a unit number; a stack position read off a four-digit number; "same building, so probably the same address series".
- **U** — no certificate matches and the user cannot supply one.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` — official coordinates, borough, ward. Use these, never a map pin.
2. `python3 scripts/epc.py search --postcode "<postcode>"` — every certificate registered at that postcode, with full flat-level addresses.
3. If the flat is missing: `python3 scripts/epc.py search --street "<street>" --town "<town>"`.
4. `python3 scripts/geo.py cover --lat <lat> --lng <lng> --radius 250` — the other postcodes that cover the same building footprint; repeat step 2 for each.
5. `python3 scripts/epc.py building --postcode "<postcode>" --match "<building name>"` — the whole-building profile (how many flats, which address series, whether ground-floor flats exist).
6. `python3 scripts/epc.py cert <certificate id>` — the certificate for the exact flat.

## Method in fetch mode
Fetch the EPC postcode-search page and then the certificate page (see `sources.yaml`, `epc_find_by_postcode`, `epc_certificate_page`).
The register's robots.txt disallows these paths for crawlers, so a robots-honouring fetcher will not get them. That is expected: fall through to manual mode.

## Method in manual mode
Ask the user for, in one message:
1. The EPC search page for the postcode — "open the Find an energy certificate service, search the postcode, paste the whole results page".
2. The certificate page for the exact flat (or its 20-digit certificate number).
3. The full address exactly as it will appear on the tenancy agreement, including the flat number and any building name.
4. If the flat is not in the results: the street and town, so you can search by street instead.

## How to read the numbers
- `epc_validity_years` — a certificate older than this is expired; the flat may have been re-assessed under another certificate.
- `fetch_host_spacing_seconds` — the minimum gap between requests to one host; do not bulk-harvest a register for an address you are not vetting.
- No pass/fail number lives on this axis. The output is a boolean: `identity.epc_exact_match`.

## Traps and lessons
- **One building, several postcodes.** Large blocks are commonly split across postcodes by floor band, so a high-floor flat is simply absent from the postcode you searched. Search by street, and check every covering postcode before concluding the flat has no certificate.
- **Unit-number decoding is a hypothesis, not evidence.** A four-digit number often encodes floor plus stack (1701 = floor 17, stack 01), and the same stack usually repeats its geometry up the building. Useful for generating questions; never quotable as a fact.
- **"Mid-floor" is not a floor number.** The register records only Ground, Basement, Mid-floor and Top-floor. It cannot yield "first" or "second", and a flat numbered 180 is not evidence of the 18th floor. Conversely, a flat advertised as "Flat 201" has appeared on its certificate as a ground-floor flat.
- **One complex can carry two independent address series** (for example Flats 1–8 on the street number and a separate 61–180 series under an older building name). Matching the wrong series produces the wrong area, age and floor.
- **Same complex is not the same building.** Shared branding does not prove shared floors, corridors, lifts or services; a separate entrance does not prove structural independence either. Say which you verified.
- **Name collision.** Two developments in different postcodes can share a name. Never move reviews, crime counts or planning history between them; check the postcode on every borrowed fact.
- **A search that misses a listing does not prove it was never advertised.** Trace aggregator → source platform → detail id; the same id across several sites is one feed and counts once.
- **HTTP status has meaning.** 410 means archived, not blocked. 403 with a challenge page means you were stopped, not that the listing was withdrawn. "Document unavailable" is not 404. Record what actually happened; never dress a failed fetch as "checked, nothing found".
- **A 200 with the wrong page is the worst failure mode** — some council systems return a plausible page for a stale id. Assert on the expected content, not the status code.
- **Out-of-range pagination can return a repeat of the previous page.** Sanity-check the flat-number range before treating a list as complete.
- **Two flats in the same building are not two independent candidates.** They share the works risk and the same crime box; merge them in any comparison.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 1`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].identity` — `display_name`, `address`, `postcode`, `flat`, `floor`, `building`, `listing_url`.
- `candidates[].provenance_notes` — whether the certificate is this flat's own or a neighbour's, which postcodes were searched, and who supplied the page.
- `candidates[].landmines[]` with code **L10** when the flat number implies a floor the official record does not confirm, or the flat is at street level.
- `not_found[]` — one entry per failed search, with `queries_used` (the exact strings), `where_looked` and `next_step`.
- `blocked_sources[]` — anything that returned a challenge, a redirect or a 200 with the wrong page, with `http_status`, `reason` and `workaround`.
Numbers to record: number of certificates at the postcode, number of covering postcodes, certificate age in years.
```

---

## Axis 02 — `skills/vet-flat/references/axes/02-floor-area.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 2 — Floor area

## Purpose
Establish how big the flat actually is, in internal square metres, from the energy certificate.
Everything advertised — square feet on a listing, a figure on a floor plan, a developer's brochure — is a claim until the certificate agrees with it.

## What counts as evidence
- **G** — "Total floor area: 51 square metres" on the flat's own EPC; the whole-building area distribution from the register.
- **S** — the listing's square footage; the agent's floor plan; the landlord's own description.
- **C** — a developer brochure or a press unit schedule.
- **I** — an area scaled off a plan by hand; the area of "a similar unit in the building".
- **U** — no certificate for this flat and no plan.

## Method in shell mode
1. `python3 scripts/epc.py cert <certificate id>` — `total_floor_area_m2` and `total_floor_area_sqft`.
2. `python3 scripts/epc.py building --postcode "<postcode>" --match "<building>"` — `summary.floor_area_m2` gives min, median, max and a histogram, plus `property_types` and `ground_or_basement_flats`.
3. Compare: advertised area, plan area, EPC area. Record all three and the variance.

## Method in fetch mode
Fetch the certificate page and read the "Total floor area" row. Nothing else on the page is an area.

## Method in manual mode
Ask the user for:
1. The certificate page text for this exact flat (the area is one row on it).
2. The floor plan image from the listing, at full size, including the small print under it.
3. If the plan states an area: the exact wording ("approximate gross internal area", "including balcony", or a separately dimensioned balcony).

## How to read the numbers
- `min_floor_area_sqft` — the user's floor, from `profile.yaml`. There is no generic default; if the profile is silent, report the area and do not fail the flat on size.
- `floor_area_exception_band_sqft` — profile: some users allow a slightly smaller flat in a specific area or with specific compensations. State the exception's scope; never apply a city-wide exception.
- `area_variance_investigate_pct` — an advertised-vs-certificate gap above this needs a named explanation before anything else on the listing is trusted.
- `studio_living_area_share` — if the living area is at or above this share of the total, the flat is a studio however it is advertised.

## Traps and lessons
- **The advertised area often includes the balcony; the certificate never does.** A 2019 riverside tower advertised at 885 sq ft had 570 sq ft on its energy certificate. Always convert and compare in the same unit.
- **"Approximate gross internal area" does not automatically include a balcony.** If the balcony is dimensioned separately on the same plan, the stated internal area excludes it. Do not assert either way without reading the plan; withdraw any earlier inference that assumed it.
- **Mezzanines and galleries** may or may not be counted. If the plan shows a second level, ask which areas the certificate measured.
- **The whole-building distribution is worth more than one certificate.** It tells you whether this flat is a mainstream type or an edge type, whether an apparent £ per square foot gap is just the size curve, and whether the building contains ground-floor flats at all. In one sweep it cancelled a false "dark side discount" alarm outright.
- **A self-described "studio suite" is not evidence.** Use the building's area bands plus the living-area share to decide whether it is a real one-bedroom.
- **Borrowed areas are not this flat's area.** If the only certificate is for a neighbouring unit, set `epc_exact_match: false` and grade the axis S at best.
- **Sources disagreeing is itself a finding.** A plan saying 459 sq ft against a certificate saying 549 sq ft is a document-quality problem; record it separately from any management or landlord judgement, and use it as a question, not an accusation.
- **A listing that contradicts itself** (an accessibility field saying ground floor while the text says 16th) tells you how carefully the listing was assembled. Note it here and again in axis 7.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 2`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the profile's minimum area: `requirement`, `observed`, `pass`, `evidence_class`.
- `candidates[].metrics.price_per_sqft_epc` — this axis supplies the denominator; axis 8 supplies the rent.
- `candidates[].landmines[]` with code **L1** when the advertised size exceeds the certified indoor area, or a balcony or gallery is being counted as room.
- `candidates[].photos_vs_reality_notes` — a wide lens, a shot from the one corner with sky, furniture at doll scale.
Numbers to record: certified area in square metres and square feet, advertised area, the gap as a percentage, the building's median and range.
```

---

## Axis 03 — `skills/vet-flat/references/axes/03-age-fabric-heating.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 3 — Age, fabric, heating and ventilation

## Purpose
Date the building, work out whether it was built as housing or converted into it, and identify how it is heated, ventilated and billed.
This axis decides most of the running-cost and comfort risk, and it is where refurbishment claims are tested.

## What counts as evidence
- **G** — first EPC assessment year; the earliest registered sale with a new-build flag; the original use class in the planning register; the heat supplier's filed accounts; a scheme's entry on the heat-network consumer-protection register.
- **S** — "built 2019" in the listing; "recently refurbished"; the operator's tariff page.
- **C** — resident reports of summer heat, smells through vents, or a tariff rise; local press.
- **I** — completion year inferred from the first certificate; ventilation type inferred from air permeability.
- **U** — no certificate history and no planning record.

## Method in shell mode
1. `python3 scripts/epc.py cert <id> --history` — every certificate for the flat, oldest first; `first_assessment_year`, ratings over time.
2. `python3 scripts/epc.py building --postcode "<pc>" --match "<building>"` — `earliest_assessment_year`, `assessment_year_counts`, `assessment_types`, `heating_classes`, `air_permeability_values`.
3. `python3 scripts/landregistry.py price-paid --postcode "<pc>"` — the earliest sales and their new-build flag. This is the hardest available counter-evidence to an age claim.
4. `python3 scripts/planning.py search --site-name "<building>"` and `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250` — the original permission and use class.
5. Heat networks: `python3 scripts/redress.py heat-trust --site "<building>"`, then `python3 scripts/company.py search "<supplier>"` → `profile` → `filings` for the accounts and the registered office.

## Method in fetch mode
Certificate pages, the planning datahub, the heat-network register and the regulator's heat-networks page are all fetchable. Company filings are fetchable on the free HTML service.

## Method in manual mode
Ask the user for:
1. The certificate page for this flat and, if offered, the older certificates linked from it.
2. The heating and hot-water rows, verbatim, if they only paste part of the page.
3. The welcome pack or tariff page for the heat network — standing charge and unit rate, in writing, from the landlord or agent.
4. One sentence from the agent: "when was the flat last refurbished, and are the photographs of this exact flat as it stands today?"

## How to read the numbers
- `max_building_age_years` — profile. Compute age from the first assessment year, and say it is an approximation.
- `epc_validity_years` — a whole building re-assessed on one day is usually this clock expiring, not a refurbishment.
- `air_permeability_mech_vent_threshold` — an air permeability at or below this value implies the flat must have mechanical ventilation to meet the ventilation building regulation. It implies mechanical ventilation; it does not identify which kind.
- `heat_network_supplier_margin_flag` — cost of sales above revenue in the supplier's accounts.

## Traps and lessons
- **First assessment year approximates completion, it does not prove it.** The earliest registered sale carrying a new-build flag is stronger, and has overturned an age claim outright.
- **New build versus conversion.** No "new dwelling" certificates in the register while the first certificate year is well after 2008 points to a conversion, not a new build.
- **Conversions skipped the daylight and space standards.** Office-to-residential permitted development, live/work units turned residential, and warehouse conversions were never assessed against residential daylight or internal space standards. The certificate and the listing will not reveal this; the planning register's original use class will. An unusually cheap split-level flat deserves the question "what was this before?" — one such unit was a live/work commercial shell converted years later, with a 2.44 m ceiling and a bedroom wall of street-facing glazing.
- **Two-generation certificate comparison is a refurbishment test.** Line up each flat's old and new rating: ratings rising is evidence of refurbishment; flat or falling across the whole building is a strong indicator that nothing was refurbished. It is an indicator, not proof — assessment-method revisions can lower ratings on their own, so state the caveat.
- **Photographs are recycled.** Completion photography can run for a decade, and "brand new" copy with it. The consequence is that condition can only be verified at the viewing, and any gap between photograph and reality is negotiating leverage.
- **Heat networks have no price cap.** The regulator took on heat networks with pricing benchmarks and standards of performance following later, so a tenancy signed in the gap has no price protection. There is a statutory ombudsman route; a scheme outside the consumer-protection register should be marked as having no independent complaints route beyond that.
- **Read the heat supplier's accounts.** A retail heat supplier whose cost of sales exceeds its revenue is selling below cost and will raise the tariff — the accounts show it about a year before residents notice. A registered office that has moved away from the developer's address signals a change of ownership, after which the retailer becomes a pass-through and pricing control sits elsewhere. This is harder evidence than any press release.
- **Ventilation ladder:** cooling > heat-recovery ventilation > mechanical extract > openable windows only. Heat recovery is not cooling; on a hot day its bypass simply brings outdoor air in at outdoor temperature. Its real value is air change with the windows shut (which serves quiet), night purge, and continuous air quality.
- **"The EPC does not list air conditioning" does not mean there is no cooling.** Air permeability alone does not prove a heat-recovery system, and an extract-only system is not automatically inadequate. Ask; do not infer a whole-area rejection from a silent field.
- **Shared ducts carry neighbours' smells.** Extract systems and shared risers move smoke and cooking smells between flats, and a new building is not immune. Search resident reviews for smell-through-vent reports; treat a hit as a real defect on this axis.
- **Warehouse and loft conversions** raise three separate questions: industrial glazing (noise and heat), the heating cost of a double-height space, and non-standard layouts.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 3`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the profile's maximum building age.
- `candidates[].landmines[]` with code **L6** (heat bought from a building-wide system at a rate the tenant cannot switch away from, plus whoever bills it) and code **L11** (no cooling, or mechanical ventilation carrying cooking and smoke between flats).
- `candidates[].viewing_day_checks[]` — open the utility cupboard, find the ventilation unit and the heat interface unit.
- `candidates[].provenance_notes` — if the age rests on the first assessment year rather than a registered sale, say so.
Numbers to record: first assessment year, age in years, earliest registered sale year, air permeability, heating kWh a year, supplier revenue against cost of sales.
```

---

## Axis 04 — `skills/vet-flat/references/axes/04-construction-nearby.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 4 — Construction and works nearby

## Purpose
Find out what will be built, demolished or dug up near the flat during the tenancy, and which facade takes the hit.
For any development begun after about 2010, the first question is: is the scheme finished, and which phase am I facing?

## What counts as evidence
- **G** — planning applications, decision notices, officer and committee reports, discharge-of-condition records, licensing and highways notices.
- **S** — the developer's or agent's account of the programme; a marketing site plan.
- **C** — local press, residents' objections, a neighbourhood forum thread.
- **I** — a phase inferred from which conditions are being discharged; distance measured off a map.
- **U** — the borough portal is unreadable and the user cannot search it.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` for coordinates.
2. `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250` — applications within the standard radius from the London-wide index.
3. `python3 scripts/planning.py search --site-name "<building or neighbour site>"` — by name, and by street when the name fails.
4. `python3 scripts/planning.py stages --ref "<application reference>"` — decision date, conditions, and which conditions have been discharged.
5. `python3 scripts/planning.py planit --postcode "<pc>" --radius-km 0.3` — a second index, queried by postcode and radius (a free-text site-name search there matches only the description field and will return nothing).
6. `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 200` — distance to the nearest major road, railway, tunnel mouth and late-night food or market use.

## Method in fetch mode
The London-wide planning index answers over plain GET. Borough portals are all robots-disallowed, so treat them as manual. Council committee pages are fetchable, but only if you assert on the page title containing "Agenda for" — a stale meeting id returns a plausible-looking page with HTTP 200.

## Method in manual mode
Ask the user for:
1. A search of the borough's planning portal for the building name and each adjacent street, pasted as the list of application references with dates and decisions.
2. The officer report or committee report PDF for any large neighbouring scheme — these state distances between buildings and often name affected properties and windows.
3. Anything the agent says in writing about works, and when they are due to finish.

## How to read the numbers
- `planning_radius_m` — the standard search radius around the flat.
- `road_facade_distance_m` — inside this distance from a major road, the building must be split by facade before any noise judgement.
- `construction_decision_within_tenancy` — an undecided application whose decision is expected during the tenancy is a live risk, not a non-event.
- `hospital_helipad_distance_m` — inside this distance from an accident-and-emergency entrance, an ambulance route or a helipad, treat it as a deduction. Being near a hospital is never scored as a benefit on this axis; one rooftop helipad 230 m away averaged five movements a day.

## Traps and lessons
- **Read the officer report before doing your own geometry.** Committee and officer reports for a neighbouring scheme frequently name the affected building and give the numbers window by window — including findings such as "moderate adverse" daylight effects and materially harmful winter sunlight to named windows. Search for the report first.
- **Condition discharge tells you the phase.** Pre-commencement conditions (archaeology, piling method, construction management plan) mean works are about to start. Pre-occupation conditions (accessible parking bays, cycle stores, remediation verification, ecology compensation) mean a scheme is finishing.
- **Status fields lie in both directions.** A London-wide index can mark an implemented permission as lapsed, creating a false three-year clock; an aggregator can be years stale and still show a withdrawn scheme as registered; a borough portal can hide a withdrawn application behind "details not available". Take form data and decision dates from the index, and take the real state from recent condition activity in the borough register.
- **Zero hits is a coverage gap, not an absence.** A regional index carries the larger and referable schemes; a small named site may simply not be in it. Never write "no planning activity" off a nil result — record the exact query in the `not_found[]` table.
- **Coordinate precedence for distances:** grid coordinates printed on a phasing or site plan > the portal's own site point > an address point. An address point has been observed 190 m from the real site boundary. A portal map pin and a police snap point are never geometry.
- **Only registry documents date a start.** Piling method statements, construction environmental management plans and build programmes naming a contractor and week numbers are official-grade. A company announcement is self-reported. An agent's assurance is not evidence.
- **Include trunk roads in any road query.** Major A-roads are frequently classified as trunk rather than primary, and a filter that omits the class has missed a five-lane road 42 m away and written the building up as quiet.
- **Split the building by facade.** Within `road_facade_distance_m` of a major road, the road side and the courtyard side are two different products at the same rent. Ask the agent, in these words: does the window face the main road or the courtyard?
- **A tunnel mouth, a cutting or a bridge deck acts as a megaphone**; so does a bin or delivery yard at night. Check what sits under the prettiest feature: a river view can be a river-facing main road.
- **Two flats in the same building share this axis.** Merge them; they are not independent options.
- **A bank-holiday visit proves nothing.** No site activity on a holiday does not tell you why the site is quiet and says nothing about a Tuesday. See `14-site-visit.md`.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 4`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.nearest_works_m` — distance to the nearest active site or approved scheme, with what it is and when it runs in `meaning`.
- `candidates[].landmines[]` with code **L5** (a site next door, or a tall scheme still undecided whose decision lands during the tenancy) and code **L4** (the flat faces a main road, a railway or a tunnel mouth).
- `candidates[].killer_questions[]` — "does this window face the main road or the courtyard" earns its place here.
- `not_found[]` — every planning query that returned nothing, with the exact search terms, because a nil result on a regional index is a coverage gap.
Numbers to record: distance to each scheme, storeys, decision date, works window, distance to the nearest trunk road and railway.
```

---

## Axis 05 — `skills/vet-flat/references/axes/05-crime.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 5 — Crime and the walk home

## Purpose
Grade the immediate area with open police data, on one fixed geometry for every candidate, and separately assess the route from the station to the door.
The output is a tier and a texture, not a precise ranking of streets.

## What counts as evidence
- **G** — street-level crime records published by the police open-data service, with the months they cover.
- **S** — the agent's or operator's characterisation of the area.
- **C** — local press, resident reports, a neighbourhood policing page.
- **I** — anything you scaled, extrapolated or inferred from a partial window.
- **U** — the address is too new to appear in the street gazetteer, so it is unmeasured (which is not the same as clean).

## Method in shell mode
1. `python3 scripts/crime.py latest` — the newest month the dataset actually holds. Choose months from this, never from today's date.
2. `python3 scripts/geo.py box --lat <lat> --lng <lng> --half-width 150` — the polygon. Same spec for every candidate.
3. `python3 scripts/crime.py box --lat <lat> --lng <lng> --half-width 150 --months 6 --sensitivity 20` — counts by month and category, the top street anchors, and the four shifted boxes.
4. Classify each top anchor as on or off the station-to-door route, using the walking leg from `commute.py journey`.

## Method in fetch mode
The police open-data API is open, has an empty robots file, and answers plain GET requests. Use the polygon form, not a single point — a point query returns a one-mile circle, which is a different question.

## Method in manual mode
Open data, so this axis rarely needs the user. If it does, ask for: the postcode's official coordinates, and the exact route they walk home from the station.

## How to read the numbers
- `crime_box_half_width_m`, `crime_box_lat_delta_deg`, `crime_box_lng_delta_deg` — the standard box (about 300 m by 305 m at London latitude). Never resize it per candidate.
- `crime_window_months` — a fixed window, always the same length.
- `police_data_lag_months` — publication runs behind by this much; the newest month available is not last month.
- `crime_sensitivity_shift_m` — shift the box this far in each of four directions and report the range.
- `crime_point_source_share_flag` — a single anchor carrying at least this share of the counts is a point source; say so.
- `crime_top_anchor_count` — how many street anchors to list.
- `night_route_node_share_flag` — the share of counts sitting on the walk home; above this is a red flag on its own.

## Traps and lessons
- **Never scale up for missing months.** Publication delay is not a reduction in exposure, and multiplying a short window to a six-month equivalent is unsupported. Use a fixed window, mark missing months as missing, never fill them with zeros, and if you must extrapolate, state the observed period and the assumption in the same sentence.
- **Get the sign of the longitude from the geocoder.** A flipped sign puts the box a kilometre away over empty ground and returns a fake quiet reading. Do not infer the sign from the postcode area — a rule of that kind was tested and found wrong for a street on the "obvious" side of the meridian. After the query, check that the top street names are actually near the target.
- **Report the sensitivity range, not a point.** Shifting the box 20 m has moved a count by 37%. One box centre is an opinion; five boxes are a range.
- **Box size and centre change the conclusion.** Over one area the six-month count moved between 66 and 139 with the centre; shrinking the box from 150 m to 120 m removed exactly the two anchors carrying all the violence. Use the standard spec for every candidate, and say so in the method note.
- **"On or near <street>" is a snap point**, not the place the offence happened. Anchors are for pattern reading, never for street-level precision.
- **Anchor spread is character.** Counts spread across the top five street names is neighbourhood-wide antisocial behaviour and cannot be discounted. One street dominating is usually a retail or transport point source that can be discounted for the area grade.
- **The point-source discount grades the area; it never erases the walk home.** A node sitting on the line from the station to the door counts in full, at full weight — one candidate had 89% of its counts on two nodes directly on the route home. Report `crime.night_route_node_share` separately from the area tier.
- **Adjacent boxes share anchors.** Two overlapping candidate boxes can contain the same 21 records; never add them.
- **Texture beats the total.** A predatory subset — antisocial behaviour, violence, theft from the person, robbery — separates a busy place from a dangerous one far better than the headline count. A transport interchange produces a large count of a specific, predatory kind.
- **Unmeasured is not clean.** A building too new for the street gazetteer can return almost nothing at its own address while the surrounding streets are busy.
- **Reading the street in person.** Chain convenience shops across London have had guards since retail theft rose in 2023, so a guard is background, not a signal. The signal is posture and fitting-out: two or more guards, one standing at the door, security tags on alcohol, meat and coffee, gates at the self-checkout exit. Then read the 20 m outside the shop. Compare a store fitted out defensively with one that is relaxed a mile away.
- **Personal discomfort can be a valid personal reason to walk away, and must never be written up as police evidence that an area is dangerous.** Keep the two sentences apart in the report.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 5`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.crime_6mo_count` — the fixed-window count, with the box specification and the months actually retrieved in `meaning`.
- `candidates[].landmines[]` with code **L3** when the counts sit on the route between the station and the front door.
- `candidates[].viewing_day_checks[]` — walk the station-to-door route after dark.
- `candidates[].axes[].unknowns[]` — any month the dataset did not have. Never fill a missing month with a zero, and never scale a short window up.
Numbers to record: window count, the four shifted counts as a range, the predatory subset, the top anchors with their shares, the share sitting on the walk home, the publication lag.
```

---

## Axis 06 — `skills/vet-flat/references/axes/06-management-neighbours.md`

```markdown
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
Nothing here fetches a review site. Scripts do the work around them:
1. `python3 scripts/company.py search "<managing agent or landlord>"` → `profile <company number>` → `filings <company number>` — activity codes, charges, accounts, officers.
2. `python3 scripts/company.py address-search "<building postcode>"` — companies registered at the building. A building with no resident-owned management or right-to-manage company means residents structurally cannot change the managing agent; that absence is an official-register finding.
3. `python3 scripts/redress.py rogue --name "<landlord or agent>"` — the London enforcement checker (absence only means no borough reported one).
4. `python3 scripts/planning.py search --site-name "<building>"` — objections and consultation records name residents and their complaints.

## Method in fetch mode
Company and enforcement registers are fetchable. Review sites are not — see `inputs.md`.

## Method in manual mode
Ask the user for the full review pages for the named building, all pages, oldest first, pasted as text, plus the site's stated total number of reviews. Then run the review surgery below on what they paste.

### Review surgery (this is the axis's real method)
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
```

---

## Axis 07 — `skills/vet-flat/references/axes/07-compliance-landlord.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 7 — Agent and landlord compliance (the money gate)

## Purpose
Establish which legal person you would be contracting with, whether they are allowed to hold your money, and what the law entitles you to.
Nothing on this axis is optional: it is the gate that money passes through.

## What counts as evidence
- **G** — the company register (number, status, activity codes, charges, officers, filing history); the Land Registry title register naming the proprietor; redress-scheme and client-money registries; the borough's rental licensing register; enforcement and tribunal records; legislation.
- **S** — the agent's own certificate PDF, a logo on their website, a verbal assurance.
- **C** — press coverage, review sites, an industry body listing.
- **I** — a landlord type inferred from activity codes or charges.
- **U** — the entity cannot be resolved.

## Method in shell mode
1. `python3 scripts/company.py search "<name>"` → `profile <company number>` → `filings <company number>`.
2. `python3 scripts/company.py address-search "<postcode>"` — related entities at the same address.
3. `python3 scripts/redress.py cmp --name "<agent>"` — client-money protection; `redress.py prs --name`, `redress.py tpo --name` — redress schemes; `redress.py rogue --name` — the London enforcement checker.
4. `python3 scripts/landregistry.py title --address "<full address>"` — the route to the title register (a paid, signed-in human step; the script tells the user what to buy).

## Method in fetch mode
The company register, the client-money registry and the enforcement checker are fetchable. One redress scheme's site blocks named AI crawler user agents outright, and another's member-lookup endpoint silently ignores its filter and returns the same recent-members list for every query — treat both as manual and never report their default output as a search result.

## Method in manual mode
Ask the user for:
1. The agent's redress-scheme membership number and their client-money certificate, obtained in writing from the agent.
2. The client-money registry entry opened to the current certificate (an old PDF on the agent's own site is the usual cause of a false "lapsed" finding).
3. The title register for a private landlord (`land_registry_title_fee_gbp` per document, signed-in card payment; never automate it).
4. The name of the legal entity on the draft tenancy agreement, and the payee name on any invoice.

## How to read the numbers
- `deposit_cap_weeks` where annual rent is below `deposit_annual_rent_threshold_gbp`, otherwise `deposit_cap_weeks_high_rent`.
- `holding_deposit_weeks` — the maximum holding deposit.
- `rent_in_advance_max_months` — after the first payment, no more than this may be required in advance.
- `deposit_protection_days` — the deadline for the deposit to be placed in a protection scheme.
- `tenant_notice_months` — the tenant's notice period, in writing; a shorter period can be agreed in writing, so agree it before signing if a short stay is possible.
- `land_registry_title_fee_gbp`, `land_registry_document_fee_gbp`.

## Legal facts (England, as at 2026-09)
- **Renters' Rights Act 2025 (c. 26)**, in force from **2026-05-01** for assured tenancies that are not social housing, by SI 2026/421. Assured tenancies are periodic; there are no fixed terms and no fixed end date; no more than one month's rent may be taken in advance after the first payment. Cite from `sources.yaml`.
- Deposit caps and the holding-deposit cap come from the **Tenant Fees Act 2019**; the deposit-protection deadline from the **Housing Act 2004**.
- There is no minimum contract length; a "minimum six months" claim is a myth.
- **Exclusive possession decides tenancy versus licence**, not the title on the document.
- More than `short_let_nights_per_calendar_year` nights of short letting in Greater London needs planning permission (Deregulation Act 2015 s.44 and the provision it inserts).
- A tenancy transfers with the property on a sale; the tenant keeps the tenancy, and the buyer never assessed the tenant.

## Traps and lessons
- **Resolve the entity by number, not by name.** Dissolved same-name shells and near-identical trading names are common; match the company number.
- **Four registers do four different jobs and cannot substitute for each other:** the portal advert (marketing), the Land Registry (ownership), the energy register (energy), and the borough's rental licensing register (mandatory, additional or selective licensing).
- **Evidence ladder for membership:** an entry in the independent registry beats the agent's own certificate, which beats a logo on their website. Open the registry entry to read the current expiry. A number that does not match is a document to resolve, not a fraud finding.
- **Payee name in three sources.** A trading name is not a legal entity ("X Ltd trading as Y"). A third entity appearing on the invoice or as the payee is a red flag.
- **Conduct forensics on the entity:** no liquidation; no judgments in the property tribunal or the case-law records; no director disqualification; no charge over the trading assets; no phoenix pattern; no recent change of name; check gazette notices; and check whether filings stayed on time through quiet periods. Archived snapshots of the company's own site show whether an operator is an experienced restart or genuinely new.
- **A deposit above the cap is usually a stale price, not an intention.** The cap runs on the current rent, and an advertised deposit is often five weeks of a previous, higher rent left un-updated. Ask for the correction, treat it as leverage, and do not present it as an accusation.
- **Off-platform pressure is a retreat signal.** A phone number spelled out in words to defeat a filter, a push to a messaging app, a request for a bank transfer outside the platform: keep money and messages where they are logged.
- **Absence of an enforcement record only means no borough reported one.** It is not a clean bill of health.
- **Universal armour, applied identically to every landlord and agent, with no exceptions based on who they are:**
  1. a custodial deposit scheme, so the landlord never holds the money;
  2. an independent, third-party check-in inventory, with photographs;
  3. everything in writing, in the language of the tenancy;
  4. a red flag means walk away.
  Amateur landlords of every background dispute deposits at similar rates; the armour is what protects you, and it is worn for everyone.
- **Guarantor route.** Ask early, before spending anything on viewings: which guarantor arrangements does the landlord accept, and is a commercial guarantor product acceptable? Route this through `profile.yaml`; the only structural blocker is "an individual guarantor in this country, with no commercial alternative accepted".
- **Ask the money-gate questions before any money moves:** which deposit scheme, in which mode; the client-money certificate in writing; and who the payee is.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 7`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row for the guarantor route from the profile.
- `candidates[].landmines[]` with code **L12** (who owns it and what they will demand: rent in advance beyond the legal limit, an oversized deposit, a guarantor requirement, a newly formed company with no history).
- `candidates[].killer_questions[]` — the money-gate question usually belongs here.
- `sources[]` — every registry entry with its `id`, `retrieved_at`, `evidence_class` and, where relevant, the membership or company number in `note`.
Numbers to record: deposit weeks requested against the cap, months of rent in advance, deposit protection deadline in days, company number, certificate expiry date.

## Working with agents and landlords
Everything in this axis is verification, not suspicion. Agents and landlords are the other half of every tenancy and the people who will hand over the keys; most are trying to do a decent job under pressure. Ask for documents as a matter of routine ("the same for every flat I look at"), thank them for what they send, and treat a missing document as a question to ask, not a verdict. The skill is a filter that gets you to the right viewings; the viewing, and the conversation there, decides.
```

---

## Axis 08 — `skills/vet-flat/references/axes/08-price.md`

```markdown
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
2. `python3 scripts/landregistry.py price-paid --postcode "<pc>"` — the sale sequence in the same building; the best available evidence of relative value between units and of the building's real vintage.
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
```

---

## Axis 09 — `skills/vet-flat/references/axes/09-aspect-light.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 9 — Aspect, light and the floor plan

## Purpose
Judge how much daylight the flat will actually get, and read the plan for windowless rooms, blind walls and awkward geometry.
In a London winter, indoor brightness comes from sky openness, floor level and window area far more than from the compass.

## What counts as evidence
- **G** — a developer's or architect's plan with a north point; a daylight assessment in a planning document.
- **S** — "south facing" in the listing text; an agent-drawn plan with no compass.
- **C** — resident comments about darkness, overheating or facing a wall.
- **I** — an orientation read off a window photograph, a shadow, or the stack position.
- **U** — no plan, no compass, no photograph.

## Method in shell mode
1. `python3 scripts/geo.py lookup "<postcode>"` and `python3 scripts/geo.py nearby "<postcode>" --radius 100` — what stands around the building.
2. `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 150` — the buildings, roads and railways the windows face.
3. `python3 scripts/planning.py near --lat <lat> --lng <lng> --radius 250` — any consented scheme that will take the sky away, and any daylight assessment naming this building.
4. Compute the obstruction angle: the height of the facing obstruction over the distance to it, as an angle from the window.

## Method in fetch mode
Planning documents and mapping data are fetchable. Floor plans and marketing photographs are not — they sit on listing portals.

## Method in manual mode
Ask the user for:
1. The floor plan image at full size, plus any developer plan or site plan that carries a north point.
2. Photographs taken from the windows, and the time of day and season if known.
3. The floor number and which way the living room faces, in the agent's own words, so it can be tested against the plan.

## How to read the numbers
- `obstruction_angle_kill_deg` — an obstruction subtending more than this angle from the window, on a low floor, is the "almost no light" case.
- `sky_openness_good_obstruction_angle_deg` — below this, the sky in front of the window is effectively open.
- `min_sky_openness_note` — sky openness is the winter criterion; orientation is a summer and shoulder-season criterion.
- `floor_position_exclusions` — profile (some users exclude ground and basement outright).
- `reject_no_sky` — profile. When true, the almost-no-light case below is a hard fail rather than a deduction.
- `quiet_over_light` — profile. When true, the quiet elevation wins any conflict with the brighter one, short of almost no light.

## The floor plan, read three ways
1. **Window convention.** Within one consistent set of plans, external openings are always drawn. A room whose external wall carries no opening mark has no window, and that is plan-grade evidence, not a guess.
2. **Service-wing stacking.** Overlay the same projection on the other floors' plans. If every floor puts bathrooms, WCs, laundry and storage in that wing — rooms that need no window — the wing's external wall is a blind wall by design. A blind wall facing a railway or a main road suggests the living side was deliberately turned to the quiet side. That is a good hypothesis to take to the viewing with a compass, not a conclusion.
3. **Odd layouts.** If the main rooms are square and the projection is an add-on, the flat is still a complete standard unit without it, and the projection is a bonus. If the main rooms themselves are chopped into awkward leftovers by the projection, walk. Price a windowless second room as storage, and do not tell the agent what you value it at.

## Traps and lessons
- **Sky openness beats orientation in winter.** Through December to February the sun is above the horizon for only a couple of hours of usable light a day on average and most daytime hours are overcast, so what matters is the obstruction angle from the window, the floor level relative to the building opposite, and the glazed area. A high floor with open sky can beat a lower floor facing the "right" way.
- **The only light-related walk-away is "almost no light".** Low floor plus close obstruction (the facing building taller than the gap between them, obstruction angle above `obstruction_angle_kill_deg`), a deep light well, or a single elevation facing a wall. Anything else is scored, not fatal.
- **Quiet beats light unless there is almost no light.** Light serves the morning; quiet serves sleep, and sleep sits upstream of everything else. Half-decent light on the quiet side beats full light on the noisy side. In the same building at the same price, take the quiet elevation first and then look at the light.
- **Summer is the other half of this axis.** A west-facing living room with no cooling overheats through the late afternoon; a recessed balcony shades in summer and still admits low winter sun. Note both.
- **Agent plans usually have no compass**, so "south facing" in the text is copy, not data. Only a developer or architect plan settles it. Where the plan has none, the compass at the window on the viewing day does.
- **Marketing photography for a rental building is shot per unit type, not per flat** ("example furniture only"), so at best it fixes the orientation of the stack, not of this flat.
- **Date a window photograph** from landmarks on the skyline, the direction of shadows, leaf cover and any scaffolding — then say what the photograph can and cannot establish.
- **A split level with a spiral staircase** is a daily tax; note it here and again on axis 12.
- **A rejection made on orientation alone should be revisited** once sky openness is measured: several units rejected for "no direct sun" turned out to be acceptable on openness, while their other defects stood unchanged.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 9`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].landmines[]` with code **L2** when another building, a wall or a deep recess takes the sky away from the main windows.
- `candidates[].hard_filters[]` — the profile's no-sky rule and any floor-position exclusion.
- `candidates[].viewing_day_checks[]` — a compass reading at each window and a photograph of any works visible from it.
- `candidates[].photos_vs_reality_notes` — marketing photography for a rental building is shot per unit type, not per flat.
Numbers to record: floor level, obstruction angle in degrees and what it was measured against, distance to the facing building and its height, orientation in degrees, number of windowless rooms.
```

---

## Axis 10 — `skills/vet-flat/references/axes/10-all-in-cost.md`

```markdown
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
- `all_in_ceiling_pcm` — profile. On or under it is a pass on this axis.
- `edge_band_over_ceiling_pcm` — over the ceiling by up to this much is EDGE, and the report must carry the break-even rent; more than that is a different price bracket, not an edge case.
- `bridging_weekly_cost` and `move_in_window` — profile, and only relevant if the user would bridge to reach a later start date.

## The all-in rules
1. **One basis, printed with the number.** Six sub-reports quoting bills between £148 and £315 cannot be compared with each other. Recompute all of them.
2. **Bundled bills go in at the bundle price**, flagged as bundled, with what the bundle excludes.
3. **Council tax depends on the household.** Some households are exempt or discounted (for example where every occupier is a full-time student). State which rule you applied and that it is a rule, not an assumption about the user.
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
```

---

## Axis 11 — `skills/vet-flat/references/axes/11-commute-redundancy.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 11 — Commute and route redundancy

## Purpose
Measure the door-to-door journey to a destination the user names, on one consistent basis, and check that the route survives a strike or a weekend closure.
A journey time is only half the axis; the other half is what happens on the day the line is shut.

## What counts as evidence
- **G** — the transport authority's journey planner output, with its legs and times; station locations from the same source.
- **S** — "ten minutes to the station" in a listing.
- **C** — a resident correcting the advertised walk ("more like 17 minutes").
- **I** — any time you assembled from more than one query.
- **U** — no journey could be planned.

## Method in shell mode
1. `python3 scripts/commute.py journey --from "<postcode or lat,lng>" --to "<destination address>" --arrive 09:00` — the destination is always an argument. Never build a destination into a script.
2. `python3 scripts/commute.py stations --lat <lat> --lng <lng> --radius 800` — every rail, underground and light-rail station within the redundancy walk.
3. `python3 scripts/commute.py redundancy --lat <lat> --lng <lng> --walk-min 10` — which strike families are reachable on foot and what grade that gives.
4. Run the journey three ways and keep them separate: average walking speed (the headline), fast walking speed (a sensitivity run only), and an entrance buffer added at the destination.

## Method in fetch mode
The journey planner answers plain GET requests with postcodes or coordinates and needs no key at this volume.

## Method in manual mode
Ask the user for:
1. The exact destination address and the time they need to arrive.
2. Which door of the destination they actually use, so the entrance buffer is right.
3. Whether they would rather sit still on one line for longer or change twice for a shorter total.

## How to read the numbers
- `commute_max_minutes` — profile. The headline is the door-to-door average-walking-speed number.
- `commute_entrance_buffer_min` — added at the destination, reported separately, never folded silently into the headline.
- `redundancy_walk_min` and `redundancy_walk_m` — the walk within which a second ticket counts.
- `station_to_door_walk_max_min` — profile, if the user sets one.
- `redundancy_min_grade` — profile. Grades are reported in `metrics.commute_redundancy_grade` and must carry the meanings the report schema fixes: **A** — two independent rail families within `redundancy_walk_min`. **B** — one rail family plus a bus route that genuinely serves this journey. **C** — one line only, no plan B.
- Say the finer reading in the finding rather than inventing a new letter: inside an A, whether the second family is at the same station or needs a 12 to 20 minute walk; inside a B, whether a second-family station sits just beyond the walk.

## The two strike families
- **Family one:** the underground and the light-rail network — the same union constituency, and they usually stop together.
- **Family two:** national rail, the overground and the cross-London line — a different constituency.
- **River services** are a third, uncorrelated ticket. Buses are not a family: they are what is left when both families fail.
- **Two lines of the same family are not redundancy.** The classic false A is a station with two underground-family lines: it is not an A, unless a second-family station is one stop or a short walk away.
- The two failure modes the grade exists for are periodic underground strikes and chronic weekend engineering work on national rail.

## Traps and lessons
- **Never splice.** Nearest station, total time and number of changes must all come from the same single journey. Assembling the best leg from three different routes produces a journey nobody can take.
- **Zero-wait samples.** Check the leg times: if arrival at the platform equals the departure time, the sample assumes a perfect connection. Report a five-minute and a ten-minute wait scenario alongside it.
- **Walking legs can contain zero-time in-station segments.** A 709 m walk shown as five minutes included a moving-link segment counted at zero, so it is not evidence of a short station-to-door walk. Read the legs, not the total.
- **The three speeds are not interchangeable.** The average-speed run is the value that goes in the table; the fast run is sensitivity; the entrance buffer is a third number. Never let one stand in for another.
- **Advertised walk times are marketing.** A resident's correction overrides the listing.
- **A postcode centroid is not the door.** Record the coordinate provenance with the result, and say it is not a verified doorway.
- **Say what you optimised.** Sitting still on one direct line for 55 minutes can be better than changing twice for 35, especially on a low-energy day. If the user's preference is a direct route, say that the ranking reflects it.
- **Off-peak, night and weekend journeys are different journeys.** A grade earned at 09:00 on a weekday says nothing about getting home at midnight; check the last services on both families.
- **The walk home is an axis-5 question as much as an axis-11 one.** Cross-reference the route against the crime anchors before grading either.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 11`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].metrics.commute_min` and `metrics.commute_redundancy_grade`.
- `candidates[].hard_filters[]` — one row for the profile's maximum door-to-door time and one for its minimum redundancy grade.
- `candidates[].axes[].unknowns[]` — anything the journey planner could not resolve, such as an ambiguous destination.
Numbers to record: door-to-door minutes at average walking speed, the fast-walk sensitivity, the entrance buffer, the number of changes, the station walk in minutes and metres, and the stations reachable on foot with their strike family.
```

---

## Axis 12 — `skills/vet-flat/references/axes/12-livability.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 12 — Low-maintenance living

## Purpose
Ask whether the flat still works on a week when the tenant has no energy for it: whether the bills pay themselves, the laundry happens, the parcels arrive and the bedroom is sleepable.
This axis catches what the other eleven miss, because none of them are about daily friction.

## What counts as evidence
- **G** — the tenancy or the inventory listing the appliances; a bundled-bill contract; the building's own parcel policy in writing.
- **S** — the listing's amenity list and the operator's description.
- **C** — residents describing what actually happens with parcels, lifts, laundry and the concierge.
- **I** — an appliance inferred from a photograph or a plan symbol.
- **U** — nobody has confirmed it and the viewing has not happened.

## Method in shell mode
1. `python3 scripts/geo.py nearby "<postcode>" --radius 400` and `python3 scripts/roads.py near --lat <lat> --lng <lng> --radius 400` — the nearest food shop, launderette, pharmacy and the walking distance to each.
2. `python3 scripts/commute.py journey` — whether the daily route is direct or needs changes (a direct route beats a route that saves five minutes with a change).
3. Reviews (paste mode, axis 6) — search for lifts, parcels, laundry and heating complaints.

## Method in fetch mode
Mapping and journey data only. Everything about the inside of the flat comes from the listing or the viewing.

## Method in manual mode
Ask the user for:
1. The amenity list from the listing and the appliance list from the inventory, if there is one.
2. Whether bills are one bundled payment or separate accounts, and which utilities are in the bundle.
3. A photograph of the kitchen and utility cupboard, and of the bedroom window and any blind.
4. Whether the building's parcel room accepts couriers other than the national postal service.

## How to read the numbers
- `supermarket_walk_min` — a food shop within this walk.
- `redundancy_walk_min` — reused here for the launderette and pharmacy walk.
- `washing_machine_required` — profile. For most users a machine inside the flat is close to a hard requirement; a missing one is usually only found in older conversions, where the age filter has already bitten.
- `launderette_trip_cost` and `launderette_trip_minutes` — profile placeholders for costing the alternative on axis 10.

## The checklist
1. **Bills structure.** One bundled bill is the gold standard; five separate accounts set up by the tenant is a deduction, because a missed direct debit is exactly what a bad week produces.
2. **Washing machine inside the flat.** Grade the alternatives rather than treating them as equal: in-flat machine; shared laundry in the building; launderette within a short walk; launderette far away; none. Cost the trips into axis 10.
3. **Dishwasher** is a bonus, not a requirement.
4. **Parcels.** A concierge or parcel room, and whether it takes couriers other than the national post. This is the single most common quiet failure in a tall building.
5. **A food shop within `supermarket_walk_min`.**
6. **A bedroom that closes and blacks out**, so daytime sleep is possible when the routine slips.
7. **One named reason to leave the house nearby.** If you cannot finish the sentence "the thing that would get me out of the flat here is …", the location is a deduction, not a saving. A discount earned by an empty neighbourhood is a discount taken out of this axis.
8. **A direct route beats saving five minutes with a change** (see axis 11).
9. **Move-in week routine:** set up the direct debits, the council tax account and any exemption, and the broadband payment in one sitting, while there is energy to do it.
10. **Kitchen grading** — for a temporary or serviced let: a private kitchen with a hob, a fridge and either an oven or a microwave is a full kitchen. The word "kitchenette" does not disqualify anything; read the equipment list instead.

## Traps and lessons
- **A listing that contradicts itself is a quality signal about the operator**: "high-speed wi-fi" in the description with "unavailable: wi-fi" in the amenity list; "studio, 0 bathrooms"; a one-month minimum stay that will nevertheless accept a seven-night request. Record it here and cross-reference axis 7.
- **Split levels and spiral staircases** are a daily tax and a moving-in problem; deduct.
- **A windowless second room is storage**, whatever it is called. If the user actually wants a dark room, that is a private benefit — it does not raise the price you offer.
- **"Bills included" tied to one compulsory supplier** is only a benefit once that supplier has been checked (axis 6).
- **Nothing on this axis can be confirmed remotely.** Almost every item here belongs on the viewing-day list; see `14-site-visit.md`.

## What goes into the report
Fields are from `references/report-schema.json`, which is the contract.
This axis writes one entry in `candidates[].axes[]` with `id: 12`, `name`, `finding` (600 characters, plain sentences), `evidence_class`, `unknowns[]` and `sources[]`. Every figure quoted in the finding is repeated in `numbers[]` as a labelled number (`label`, `value`, `unit`, `meaning`, `compared_to`, `evidence_class`, `sources`).

Also fills:
- `candidates[].hard_filters[]` — one row per must-have from the profile, each with what was observed and whether it passes.
- `candidates[].viewing_day_checks[]` — most of this axis is a viewing-day list; write each item as a question the visit can answer.
- `candidates[].landmines[]` with code **L11** where the flat has no cooling or shares its ventilation.
- `candidates[].photos_vs_reality_notes` — where the listing contradicts itself, say which version the report used.
Numbers to record: walking minutes to a food shop, to a launderette and to a pharmacy; the number of separate utility accounts; the cost and time of a laundry trip where there is no machine.
```

---

## Axis 13 — `skills/vet-flat/references/axes/13-adversarial-review.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 13 — Adversarial review

## Purpose
Have a second agent attack the verdict before the user acts on it, in a format that forces every objection to be answerable.
The purpose is not to find fault; it is to make the report's weak points visible and to say exactly what would settle each one.

## The five-column objection format
Every objection is one row. A row missing any column is not an objection.

| Column | What it must contain |
|---|---|
| **Claim to challenge** | The exact sentence from the report being disputed, quoted, with the axis it sits on. |
| **Counter-evidence** | What contradicts it, with a source and an evidence class (G / S / C / I). "It feels wrong" is not counter-evidence. |
| **Severity** | CRITICAL, HIGH or MEDIUM, defined below. |
| **Recommended action** | What the main report should do: change the verdict, add a condition, add a question, re-run a query, mark U. |
| **Release evidence** | The specific evidence that would retire this objection. **An objection with no release condition is not a valid objection.** |

Add a `sources[]` list to every row.

### Severity
- **CRITICAL** — new, direct counter-evidence that removes the candidate's eligibility (for example a registered sale that contradicts the claimed building age).
- **HIGH** — a hard condition is not met and the candidate is nevertheless ranked highly.
- **MEDIUM** — a presentation or maturity problem: an unsupported adjective, a missing denominator, an unlabelled inference.

## The "not proven defects" section
Every reviewer must also file the list of things they went looking for and **did not** find wrong, with the queries used.
Without this section, a reviewer under pressure to produce findings will manufacture them. With it, the silence is evidence.

## Disposition vocabulary (the deciding agent's reply to each row)
accepted · partly accepted · accepted in full and withdrawn from the ranking · partly released · accepted with a document to follow · accepted with a limit · accepted and tracked · rejected.
Use these words and no others, so dispositions can be counted and compared between rounds.

## Time classification of corrections (E / R / N / U / J)
When correcting an earlier judgement, classify why it was wrong. This stops new rules being used to retro-score old decisions.
- **E** — an error identifiable with what was known at the time.
- **R** — the standard changed afterwards; the old judgement was right under the old rule.
- **N** — new data arrived afterwards.
- **U** — still not enough data; the finding stays unknown.
- **J** — a defensible judgement call that could have gone either way.

## Explaining a change of rank
Decompose every movement into four causes and name which applied:
candidate pool changed · rule changed · evidence corrected · weights changed.
**A number going down does not mean the flat got worse.** Say which of the four moved it.

## Freeze, then compare
1. Produce the independent version first, without reading the earlier material.
2. Record a timestamp and a content hash for every output file.
3. Only then read the earlier reports and compare.
4. Re-check the hashes after the comparison to prove nothing was edited during it.
5. Issue corrections as a **separate errata document**. **Never rewrite a frozen output.** Version files side by side; do not overwrite.

## The retrieval manifest
Log every fetch that failed, with its status: 403, 406, 410, 429, 500, an empty body, or a 200 carrying the wrong page. Record whether the raw response was kept.
- Never work around a block and describe it as a successful check.
- Never claim to have kept a raw response you did not keep.
- **A failed fetch is recorded as a failed fetch**, never as "checked, nothing found".

## Limits on the adversary
- Models from the same family share blind spots; several agents agreeing is not verification.
- A reviewer may not turn caution into permanent inaction: "more evidence would be nice" is not an objection unless it names the evidence and the decision it would change.
- A reviewer may not introduce a personal preference as a fact. Preferences belong in `profile.yaml` and are labelled as preferences.
- Objections must attach to the report's claims, not to the user's choices.

## Delivery QA gate
Before handing anything over, check mechanically for: broken internal anchors; duplicate element ids; dead local links; replacement characters from a bad encoding; the axis count per candidate (all twelve present, or an explicit U); and any candidate still flagged not-ready while appearing in a ranking.

## Fixed closing three paragraphs
Every adversarial round ends with exactly these three, in this order:
1. **What this round did** — the checks run and the sources reached.
2. **What is unfinished is not a hidden pass** — every U listed item by item, with why it is unknown and what would resolve it.
3. **What this round did not attempt** — the checks deliberately skipped, so the next round knows where to start.

## What goes into the report
The adversarial round's own artefacts do not live in `report.json`. Keep them in a separate, versioned file beside it: the five-column objection table, the not-proven list, the disposition table, the correction classes, the rank-change decomposition, the freeze hashes and the retrieval manifest.
What enters `report.json` (per `references/report-schema.json`) is only what was **adopted**:
- `candidates[].verdict` — a changed `status`, added `conditions[]`, a changed `fatal_axis` or `reason_codes[]`.
- `candidates[].landmines[]` — a new problem found by the reviewer, under its code, with `evidence_class` and `sources`.
- `candidates[].axes[].unknowns[]` — anything the reviewer showed was never actually established.
- `candidates[].axes[].finding` — corrected wording where a claim overreached its evidence.
- `not_found[]` and `blocked_sources[]` — the reviewer's failed and blocked retrievals, recorded honestly rather than as "checked, nothing found".
- `candidates[].provenance_notes` — that an adversarial round ran, on what date, and where its full record sits.
Never overwrite the frozen version to make the two agree. Publish the errata alongside it.
```

---

## Axis 14 — `skills/vet-flat/references/axes/14-site-visit.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 14 — The site visit

## Purpose
Fold what the user saw, heard and smelled at the property into the report without letting a single visit overturn evidence it cannot reach.
A visit is a sample of one moment. It is extremely good at some things and worthless at others; this file separates the two.

## The three-column adoption table
Every observation is recorded as one row, and all three columns must be filled in.

| What was observed | How this round adopts it | What it cannot be used to claim |
|---|---|---|
| The user's own words, with the time, date and exact standing position. | The specific change: an assumption replaced, a concern lowered, a question added. | The claims this observation does not support, spelled out. |

## The four boundaries (declare all four, every time)
1. **Time of day** — an afternoon visit says nothing about the evening.
2. **Day type** — a weekend or public holiday says nothing about a weekday.
3. **Scope** — a street segment is not the building, and the building is not the flat.
4. **Subject** — the block is not this unit, and this unit is not this unit's window elevation.
An observation missing any of the four is recorded but not adopted.

## The four allowed effects
A visit may:
1. **Replace an assumption** with an observation (for example, "orientation unknown" becomes "compass reading taken at the living-room window").
2. **Lower a concern** that the desk research raised.
3. **Trigger a withdrawal** from a high position, if what was seen is bad enough — without inventing a precise new rank to replace it.
4. Nothing else.
A visit may **never upgrade anything to a pass**. It cannot grant "quiet", cannot grant "safe", cannot turn CONDITIONAL into PASS, and cannot release a hold. Those need evidence that a visit does not produce.

## Observation → scenario × flip-condition matrix
Expand each sensory observation into three or four scenarios, each with the condition that would flip it. For example, a strong cooking smell in the corridor becomes:
a neighbour cooking once (flips if absent on a second visit at a different hour) · a restaurant extract in the shared riser (flips if the plan shows no commercial unit below) · a shared ventilation path between flats (flips if the system is confirmed as flat-by-flat) · an extract fault under repair (flips on a maintenance record).
Never collapse the matrix to whichever scenario is most convenient.

## Conditional positives keep their condition
Record the whole sentence, condition included: "as long as there are no drunks and no event traffic, it is a quiet, comfortable little block." The condition is the finding. Quoting only the first half turns an observation into a conclusion it never was.

## Boundaries in practice
- **A public-holiday visit proves nothing about weekdays.** No activity on a building site that day does not tell you why it was idle, and says nothing about a Tuesday morning.
- **A phone decibel app is a relative comparison only.** It is not a calibrated measurement and not a test of sound insulation. Use it to compare two rooms in the same session, never to assert a level.
- **One visit is one sample.** Two visits at different hours are worth far more than one long one.

## Ten things only a visit can measure
1. The smell test: the corridor, the lift, the lobby, and the bin store — separately.
2. The lift's statutory inspection record: photograph it.
3. Three minutes with the window open and three with it shut, in the same room, at the same time.
4. Whether the parcel room accepts couriers other than the national postal service — ask, do not assume.
5. The walk from the station to the door after dark, on the route actually used.
6. Phone signal in the bedroom, on the user's own network.
7. How dark the bedroom actually gets: blinds down, curtains shut, mid-afternoon.
8. What is inside the utility cupboard: the meter, the heat interface unit, the ventilation unit, the stopcock.
9. A compass reading at each window, plus a photograph of any site works visible from it.
10. Whether the one named reason to go out (axis 12) is genuinely there and genuinely open.

## Rules for the visit itself
- **Never sign on the viewing day.** A holding payment buys a night to sleep on it and a morning to check the scoresheet.
- Get in writing, before leaving home: the tariff or bills position, the deposit scheme and amount, the guarantor position, the appliance list, and the availability date.
- At most three flats in one area in one day; more than that and the observations blur together.
- Book any celebratory meal for after the viewings, not between them.

## What goes into the report
Fields are from `references/report-schema.json`. A visit writes into an existing report; it does not create a candidate.
- `candidates[].viewing_day_checks[]` — each of the ten items, answered or explicitly recorded as not answered.
- `candidates[].axes[].finding` — the observation, with its four boundaries in the same sentence, and its evidence class. An observation is class C at best, never G.
- `candidates[].axes[].unknowns[]` — anything the visit was expected to settle and did not.
- `candidates[].landmines[]` — a defect the visit found, under its code, marked `reversible` where it is.
- `candidates[].photos_vs_reality_notes` — the gap between the listing photographs and the room.
- `candidates[].provenance_notes` — the date, time of day, day type and exact standing position, plus the standing rule that a visit may replace an assumption, lower a concern or trigger a withdrawal, and may never raise a verdict to PASS or release a hold.
- `candidates[].verdict.conditions[]` — a condition the visit satisfied may be struck; a condition may not be struck merely because nothing bad happened during one visit.

## Ground and lower-ground floors: the damp check (a caution, not a veto)
Many street-level and below-street flats are good homes. They fail in one specific way, damp, and it is invisible in photographs and in two-night reviews. Check, in this order, and photograph with a pen in frame for scale:
1. **Nose at the door.** Musty, earthy or "old carpet" smell on entry, before anything else.
2. **Wall corners and skirting.** Bubbling or flaking paint, dark spots, tide marks, salt bloom on plaster.
3. **Behind radiators and under windows.** Black mould, brown water staining, rust runs from pipes.
4. **Floorboards.** Blackened joints, edges lifting, a white haze on wood, a soft step: wood that has been wet.
5. **Windows.** Condensation on the inside in the morning, closed trickle vents, no extractor in bathroom or kitchen.
6. **Outside.** Where the external ground sits against the wall, blocked gullies, a light well full of leaves.
7. **Ask, politely:** when was the flat last damp-proofed or redecorated, and is there an extractor that runs on a humidistat. A landlord who answers with dates is a landlord who maintains.
What it means for the verdict: strong signs on two or more items = walk away from that flat; one weak sign = ask and re-view after rain. Not seen = say "not seen", not "no damp".

## Tone on the day
The agent or landlord showing you round is the person who will get you the keys. Ask everything on the list, write the answers down, and stay courteous; a defect you found is information for both sides, not an accusation.
```

---

## Axis 15 — `skills/vet-flat/references/axes/15-bridging-short-lets.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 15 — The bridge: a 2 to 8 week short let before the real tenancy

## Purpose
Most people arrive before the flat they actually want is free. The bridge is the gap. This axis prices the gap honestly, buys the right product for it, and stops the gap from making the long-let decision worse than it needs to be.
A bridge is a tent, not a home. It is vetted on three things only: clean, quiet enough to sleep, able to receive post. Do not run the full axis set on it.

## The one arithmetic rule that changes every ranking
A bridge is **not an extra cost**. During the bridge you are not paying the long-let rent. Compare whole years, not monthly averages:

> 12-month total = (bridge weeks × bridge weekly rate) + (remaining months × long-let all-in)

Worked shape: a flat available now at an all-in of A costs 12A over the year. A cheaper flat available `w` weeks later, at all-in B, costs `(w/4.33) × weekly_bridge + (12 − w/4.33) × B`. Whenever B is enough below A, **waiting is cheaper, not dearer**.
The wrong model — "amortise the bridge into the year as a surcharge, so every week of waiting lowers your rent ceiling" — double counts. It manufactures a false deadline and kills good October and November flats. If a report contains a "monthly cost after bridge amortisation" column, delete the column.
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
```

---

## Axis 16 — `skills/vet-flat/references/axes/16-referencing-and-proof-of-funds.md`

```markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 16 — Referencing, affordability and proof of funds

## Purpose
Decide, before you spend a viewing on a flat, whether you can actually pass its money gate. Most wasted weeks in a search come from finding the right flat and then discovering the landlord's rule set does not have a route for you.
The gate has three parts: **an affordability test**, **a referencing check**, and **a guarantor position**. Ask for all three in writing in the first message (question G1).

## The affordability test
Landlords apply a multiple of the rent, and the multiple depends on which box you are in. Multiples below are the shapes seen in published operator criteria; the number for **this** landlord must come from their own document.

| Applicant type | Typical published rule | Notes |
|---|---|---|
| Employed | Income of about 2.5×–3× the annual rent | Verified by payslips, employer reference or open banking |
| Self-employed | Minimum demonstrable income around **2.66×** rent | Verified 6 months of income by open banking, bank statements, tax return, or an accountant's reference — usually only an accountant based in the UK. **Business account statements are commonly not accepted; personal income only** |
| Student | No income test; a guarantor or a guarantor product instead | Guarantor needs demonstrable **income or savings of about 4× the rent**. One guarantor per unit is preferred; one guarantor per resident covering their share (total rent ÷ residents) is often accepted |
| Not currently earning | A guarantor is required | |
| Anyone, via savings | A savings route, where the landlord enables it | Threshold seen in published referencing rules: **36× the monthly rent** held as savings |

Rules of use:
- **Always ask for the operator's published criteria as a document.** "The agent said 30 times" is a self-reported claim; the criteria page is evidence.
- The multiple is applied to the **contractual rent on the agreement**, not to a discounted or promotional headline. Ask which figure they use, and whether a separate monthly utility charge counts.
- Where a criteria table adds "alternative options available, please ask", that sentence is an invitation. Asking may not help; not asking definitely will not.

## What "referencing" actually checks
Referencing is normally run by a third-party checking company on the landlord's rules. It looks at:
1. **Identity** and right to rent.
2. **Affordability**: income or savings against the multiple above.
3. **Credit**: adverse records, bankruptcies, county court judgments. A thin or absent UK file is normal for a new arrival and is not by itself a fail.
4. **Previous landlord reference**, where one exists.
5. **Employer or education confirmation**.
The checking company executes; **the landlord sets the rules**. If a route is missing from your application form, it is usually because the landlord did not switch it on — so ask the landlord, not only the checker.

## The three routes, compared
| | Personal UK guarantor | Commercial guarantor product | Proof of funds / savings route |
|---|---|---|---|
| What it is | A named individual signing a deed | A company standing as guarantor for a fee | Your own savings evidenced instead of income |
| Cost | £0 | See the two fee models below | £0 |
| Availability to a new arrival | Usually none | Wide | Only where the landlord enables it |
| Who stays liable | Guarantor, jointly | **You** — the provider pays the landlord then recovers from you | You |
| Speed | Days, plus their own referencing | Often approval within ~48 hours | Same as any check, once enabled |
| The catch | Guarantor must pass a 4× test themselves | Fee is usually non-refundable | Balance must hold above the threshold for the whole look-back |

### Two fee models inside "commercial guarantor product"
- **One-off fee model.** A single fee, commonly quoted as "up to one month's rent"; market quotes seen range from a few hundred pounds to 2–4 weeks' rent depending on provider and rent level. Documents required: photo ID, proof of income or financial support, tenancy details. Cover is typically capped, for example *up to 12 months of rent in total across a maximum 3-year tenancy*. Some providers **transfer an approval to a different property within ~60 days at no extra cost** if the first tenancy falls through, and some offer optional credit building by reporting on-time rent to the credit bureaux. Applying should not affect your credit score — confirm that in writing.
- **Annual insurance-premium model.** An annual premium, typically around **3 weeks' rent in year one plus a setup fee**, auto-renewing yearly up to about 3 years, with the renewal price notified ahead and possibly falling if no claim was made. Cancelled and refunded if the tenancy never starts. Usually referred through the agent's platform, arranged by a regulated insurance intermediary and underwritten by an insurer.
- Compare on six axes, every time: **fee model, cover cap, renewal and repricing, transferability, whether liability stays with you, credit effect.** In both models the liability stays with you: this is protection for the landlord, not insurance for you.

### Legal boundary
Paying a third-party guarantor company is lawful, and a landlord may lawfully require *a guarantor*. A landlord may **not** require you to buy one specific paid product as a condition of the tenancy — wording of the form "a UK guarantor **or** one of our approved guarantor companies" is the compliant shape. **Any fee payable to the landlord or agent themselves, rather than to the guarantor provider, is a prohibited payment: refuse it.**
Approved-provider lists are usually set at group level; the local lettings person cannot add a provider. Ask which providers are approved and what each charges, then choose.

### A route that no longer exists
Offering to **pay six or twelve months' rent up front in place of a UK guarantor** was closed off by legislation. Treat any listing or FAQ that still asks for a year's rent in advance as an out-of-date page — and as a hint that the landlord's student policy is being rewritten, which is exactly when it is worth asking for the savings route.

## The savings route, in detail
- Threshold seen in published rules: **36 × monthly rent** in savings. Whether it is offered at all is at the landlord's discretion.
- The check looks at the **lowest balance across the look-back period** (commonly the last 3 months), not today's balance.
- **Do not move money out of the evidenced account until the check has passed** — including converting currency to a new UK account. A transfer can drop the minimum below the line.
- Recently arrived money may be discounted because it has not been held long enough. Plan the look-back before the search, not after.
- Documents: an **official bank statement** including the account cover page (your name, account number, bank) plus transactions with running balances. Screenshots and bare transaction exports are commonly rejected. Remove any PDF password before uploading — an encrypted file is often just rejected. Export in English where the bank supports it.
- Say only that you are **above their threshold**; do not volunteer a total. The statement speaks for itself.
- If the application form offers no savings option, **do not pick a wrong income category to get past the page** — some systems will not let you delete an added income source, and claiming a category you cannot document manufactures a failed check, which is exactly what the "no refund if referencing fails" clause is waiting for. Message support and the landlord instead.

## Holding deposits: the rules that protect you
- A holding deposit is capped at **one week's rent** and is credited against the first rent.
- While a landlord or agent **holds a holding deposit for a property, they may not accept another one for the same property.** That is what makes it exclusive — not a verbal promise. If payment is still clearing, ask for written confirmation that the exclusivity runs from the date you paid, including while the payment is processing.
- Three clocks start: the document deadline the landlord sets (often 7 days), the validity of the offer (often 14 days), and the **statutory 15-day deadline for agreement**, which can be extended **in writing**. Ask for the deadline-for-agreement date in writing so a slow check does not cost you the deposit.
- Some offers include a short full-refund window after a viewing (24–72 hours is common). Write the expiry in your calendar the day you pay.
- Terms that say "not refundable if referencing fails" are often drafted wider than the law: where you provided truthful information and cooperated, the deposit generally cannot be kept. Note it; do not argue about it before you need to.
- The name on the direct debit or payee is the **legal landlord entity** on the agreement. Check it matches.

## Concessions are part of the money gate
A portal price below the offer price is usually a rent-free period spread across the year (for example, four weeks free on a twelve-month term ≈ the annual rent × 48/52). Ask three things: does this unit qualify; will it be **written into the offer** (a concession not written in has not been granted); and **how is it paid** — a lump, or in instalments that are forfeited if you leave early. A four-week concession is often worth about the same as a commercial guarantor fee, which makes it the thing to negotiate.

## The document pack to prepare BEFORE searching
- Passport, and the immigration document or online status the landlord will check.
- Offer or enrolment letter, plus the course start and end dates.
- Official bank statements: account cover page plus 3–6 months of transactions with balances, unencrypted, in English if available.
- A savings or balance certificate from the bank, in English, if one can be issued.
- Previous tenancy agreement and previous landlord's contact details, from any country. This is worth more than a hotel or holiday-let stay, which is not a tenancy and produces no landlord reference.
- Employment or income evidence if you have any, including a tax return; for the self-employed, be ready for **personal**, not business, evidence.
- Your current address and the previous address with dates, written once and reused everywhere.
- If using a commercial guarantor: a pre-approval done before you start viewing. Pre-approval is cheap, fast, and is a **trust accelerator at the viewing**, not a prerequisite for locking a flat. The thing that locks a flat is the holding deposit; the full guarantee only has to complete inside the referencing window.
- Debug identity verification at home, not in a hotel room on viewing day.

## Timeline
| Step | Typical elapsed |
|---|---|
| Guarantor pre-approval | Same day to 48 hours |
| Holding deposit paid → referencing invitation | Same day to 3 days; chase if it has not arrived within 48 hours |
| Documents submitted → decision | 2–5 working days if nothing is queried |
| Decision → agreement signed | Within the statutory 15 days unless extended in writing |

## What a rejection means, and what to ask next
A decline is a rule mismatch far more often than a judgement about you. Ask, in one message:
1. **Which specific criterion was not met** — affordability, credit, previous landlord, or documents?
2. Is there an **alternative route** for this criterion: a guarantor product, the savings route, a larger deposit within the legal cap, or a different multiple?
3. If it was a document problem, **exactly which document, in what format**, would satisfy it?
4. Since I provided truthful information and cooperated, **will the holding deposit be returned**?
Then decide: fix the document, buy the guarantor product, or walk. Do not re-apply to the same landlord with the same file.

## How to present yourself, lawfully
- Lead with what the criteria actually ask about: single occupant or household size, non-smoker, no pets, funding source, guarantor position, earliest move-in, and that you can decide quickly.
- Put the guarantor position in the **body** of the first message: "I use a commercial guarantor service; please confirm the landlord accepts this." A tick-box cannot express it, and this sentence means nobody can later say you misled them.
- On the tick-box "are you able to provide a guarantor?", a commercial guarantor **is** a guarantor: answer yes, and disclose the type in the body.
- If you are staying somewhere temporary, do not claim to be a current tenant. Choose "temporary accommodation" or "other" and add one line: temporary accommodation until *date*, recently relocated.
- Keep the current address identical across the landlord, the checking company and any other agent, so the file reconciles.
- **Never volunteer, and never ask about, nationality, ethnicity, religion or immigration status beyond the identity document the check formally requires.** Do not use those categories to screen a landlord or agent either.
```

---

## Axis 17 — `skills/vet-flat/references/axes/17-uk-admin-pitfalls.md`

````markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Axis 17 — The first two weeks: admin traps and the order that works

## Purpose
Everything in this file is a chicken-and-egg problem: the bank wants an address, the address comes from a tenancy, the tenancy needs money that is in an account you cannot open yet. There is an order that dissolves the loop. Follow it, and none of these steps blocks another.

## The dependency loop, and the order that breaks it
```
       (proof of address)
bank  <──────────────── tenancy ────────> council tax ──> utilities
  │                        ▲                                  │
  │  (money to pay)        │ (deposit + first rent)           │
  └────────────────────────┘                                  ▼
                                                     GP, post, everything else
```
**The order that works**

1. **Before you fly** — open a money corridor that does not need a UK address: a home-country account plus an international transfer account. Get an international payee mandate set up in person at the home bank before you leave; that setup is a branch task and often takes a couple of days to become effective. Getting a full UK bank account from overseas is optional, not on the critical path.
2. **Week 1, on arrival** — get a UK mobile number, open an app-based UK current account using your passport and your online immigration status, and pay for the bridge from the transfer account.
3. **Week 1–2** — sign the tenancy. **The signed agreement is proof of address from the day it is signed, not from the day you move in.**
4. **Then** — update the address everywhere, order cards, register for council tax (and the student exemption), set up utilities and broadband, register with a doctor.

Nothing in the search itself depends on having a UK bank account: a deposit, a holding deposit and the first month's rent can all be paid from an international transfer account, and referencing and guarantor providers do not require a UK account.
**Let the flat decide the bank, not the bank decide the flat.**

## Proof of address — what counts, in order of strength
| Document | Accepted as address proof? |
|---|---|
| Signed tenancy agreement (long let or an agent's short let) | Yes, widely — the strongest thing a new arrival can get quickly |
| Utility bill or council tax bill in your name | Yes |
| Bank statement showing name and address (home country, often acceptable) | Usually, if recent and issued by the bank |
| University letter confirming enrolment and residential address | Yes, and it is the classic student route |
| Government correspondence | Yes |
| Hotel or holiday-let booking confirmation | **No** |
| A holiday-let host's address, entered as "your address" | No — and entering it can look like inaccurate information |

Practical rules:
- Before you have a UK address, use a **stable home address that documents can actually prove** — the one your bank and government records already hold — not a rental you are about to leave. The address on the form and the address on the document must match exactly.
- Once you have a tenancy, change the address once, everywhere, in one sitting.
- Do not change an account's address to a hotel to unlock a card. Wait for the tenancy.
- A short let from an agent gives you an agreement with your name and the address on it — that is its hidden value over a hotel.
- Keep the **same current address** on every application in flight so the files reconcile.

## Bank accounts
- Applying from overseas can stall for reasons that have nothing to do with your money: an unsupported country in a dropdown, an address document format the system will not take. **Money does not open the door**; the risk asymmetry means no individual has an incentive to make an exception.
- Treat an overseas application as optional. Landing as a resident with a tenancy and a local address is a shorter, cleaner path.
- The retail market has no equivalent of a long "relationship" discount. Checks are model-driven, loyalty is often priced worse than switching, and what follows you is your **credit file and your account behaviour**, not your tenure at one bank.
- Two account categories are worth having: an app-based everyday account for direct debits and daily spending, and a transfer account for moving and converting currency. A premium tier is a product you buy: price the interest you forgo on any balance it locks up against the benefits, and re-decide annually.
- Cards and PINs arrive in **separate envelopes, on paper**. Do not tick "card received" if it has not arrived. Once a card is activated, most apps show the PIN, so the PIN letter never needs to be opened. When you have a permanent address, ask for a reissue there and destroy the old pair.
- Cost of moving money: converting through a transfer account and sending domestically is usually far cheaper than an international transfer in the destination currency. Compare the FX spread, not the flat fee — the spread is where the money is.
- Verification texts: some travel eSIMs cannot receive automated verification messages. If codes do not arrive, that is the first thing to test.

## Deposits and their protection
- For an assured shorthold tenancy the deposit is capped at **five weeks' rent** where the annual rent is under the statutory threshold, and the holding deposit at one week.
- The deposit must be placed in a **government-approved scheme** within 30 days, and you must be given the prescribed information. **Ask for the scheme name and the certificate; keep the email.**
- Recompute the cap yourself against the rent on the agreement. A deposit above five weeks is either an error or evidence the rent was recently reduced — either way it is a question worth asking.
- Deposit-replacement or "no deposit" products are a **non-refundable fee**, not a deposit, and you still pay for damage. They are always optional. One sentence is enough: *"I'd prefer the traditional deposit in a custodial scheme, please."*
- A short-stay **licence** deposit is not required to be protected at all. Cap your exposure instead (axis 15).

## Council tax
- Full-time students are **exempt**; a household of only full-time students pays nothing. Do not budget for it on a student long let.
- The exemption is not automatic. Register with the council for the address, then submit the university's council-tax certificate. Do this in the first fortnight — chasing a wrongly issued bill later costs far more time.
- Serviced apartments and aparthotels are on business rates; a short-stay guest is not billed.
- On any short let, get in writing whether the weekly rate includes council tax.

## Utilities and heat networks
- Ask which bills are inside the rent and which are outside, and **who the billing company is**, before signing.
- A **communal heat network** means you cannot choose a supplier. Ask for the tariff page in writing and read two numbers:
  - **Standing charge (per day)**: ≤45p is cheap, 45–85p is normal, ≥£1 is expensive, and well above that is a walk-away.
  - **Unit rate (per kWh of heat)**: ≤12p cheap, 14–18p normal, ≥22p expensive.
- In a well-insulated new building the heat used is small and mostly hot water, so the **standing charge can be about half the heat bill**. That is why "I never turn the heating on and still get a big bill" is a real complaint and why the daily rate matters more than the unit rate.
- Heat networks are now regulated, so a written tariff breakdown is something you are entitled to ask for. Refusal to provide one is a red flag.
- A fixed monthly "utility charge" on a build-to-rent tenancy needs two answers: **what it covers** (heat, hot water, water, electricity?) and **how overage is billed**.
- An operator's "typical bills" figure is an average across the year. In an electrically heated flat, winter months will exceed it.
- Put utility accounts in your own name on direct debit: it is also how a credit file gets built.

## Broadband
- Where the rent includes a building-wide fibre package, an upgrade to a faster tier is normally a personal add-on at a modest monthly cost. Ask who the provider is and what the upgrade costs.
- On a short let, ask explicitly: **fixed line or mobile router, unlimited or capped, and what speed.** A capped mobile router marketed as "Wi-Fi included" is a common gap.

## Right to rent, immigration status and identity
- A landlord or agent must check your right to rent before the tenancy. For most people this is done with an online status and a **share code generated for the landlord**; some hold a physical document instead. Generate the code shortly before it is needed and note its expiry.
- Bring the passport and the share code (or document) to viewings where an offer might be made on the day.
- The check is the landlord's legal duty and applies to everyone. Nothing beyond the required document should be discussed, requested or volunteered.

## Health, and the rest of the first fortnight
- Register with a local doctor's practice as soon as you have an address; you do not need to be ill, and you do not need to wait for any number to be issued. Registration takes days, and being registered before you need it is the whole point.
- A pharmacist can advise on minor conditions without an appointment, which covers the gap while registration completes.
- A National Insurance number is only needed for work; it does not gate housing, banking or healthcare and can be applied for later.

## Post and parcels
- On a bridge, prefer somewhere with a staffed front desk that will hold post in your name; a private short let's letterbox is far less reliable.
- Ask for post to be receivable in your name, and for the agreement to carry your name and the property address.
- Cards typically arrive within about a week; a card from a transfer account can take one to two weeks. A five-week bridge absorbs both — but only order to an address you will still be at.

## What to keep in writing
1. The tenancy agreement, and the legal landlord entity named on it.
2. Deposit scheme name, certificate and prescribed information.
3. The tariff page or bills position, with the standing charge and unit rate.
4. Any concession, written into the offer, with how and when it is paid.
5. The guarantor position and which providers are accepted.
6. The deadline-for-agreement date and any extension.
7. Confirmation that the holding deposit reserves the property exclusively, effective from the date you paid.
8. Every verbal promise, emailed back with a request to confirm.
9. Move-in photos and video, stored off-device.
````

---

## Thresholds — `skills/vet-flat/references/thresholds.yaml`

```yaml
# Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
#
# Every number the axis files reference, by id.
# Shape: id: {value, unit, meaning, default_source, note}
#   default_source: generic  -> a method constant or a legal fact; safe to use as shipped
#   default_source: profile  -> a personal preference; value is null until profile.yaml sets it
# A null value with default_source: profile is NOT a failure. If the profile is silent,
# report the measurement and do not fail the flat on that threshold.
version: "2026-09-03"

# ---------------------------------------------------------------- fetching --
fetch_host_spacing_seconds:
  value: 1.2
  unit: seconds
  meaning: "Minimum gap between two requests to the same host."
  default_source: generic
  note: "Enforced by scripts/_fetch.py. Do not bulk-harvest a register for addresses you are not vetting."

nearest_postcode_max_radius_m:
  value: 2000
  unit: metres
  meaning: "Maximum radius the postcode radius-search accepts."
  default_source: generic
  note: "A larger value is accepted with HTTP 200 and silently ignored: the result set does not widen. Page the circle instead."

# ------------------------------------------------------------ area sweep ----
sweep_radius_m:
  value: 2000
  unit: metres
  meaning: "Enumeration radius around the anchor address."
  default_source: generic
  note: "Anchor on a real address, never an area name."
sweep_deep_read_radius_m:
  value: 1600
  unit: metres
  meaning: "Radius inside which full review reading is done."
  default_source: generic
  note: "The cost gate: enumerate to the full radius, read deeply only inside this one."
sweep_max_deep_lines:
  value: 8
  unit: buildings
  meaning: "Maximum buildings taken through the full per-building script run."
  default_source: generic
  note: "If the budget runs short, cut this number, never the review-hygiene steps."
sweep_max_decision_questions:
  value: 2
  unit: questions
  meaning: "Maximum questions put back to the user at the end of a sweep."
  default_source: generic
  note: "Separate from the at-most-two questions per candidate aimed at the agent."
structural_finding_min_developments:
  value: 2
  unit: buildings
  meaning: "A theme must appear in at least this many buildings before it can be called structural."
  default_source: generic
  note: "Below this it is a single-building defect and may not be generalised to the area."
structural_finding_min_years:
  value: 2
  unit: years
  meaning: "A theme must span at least this many years before it can be called structural."
  default_source: generic
  note: "Applied together with structural_finding_min_developments."

# -------------------------------------------------------------- floor area --
min_floor_area_sqft:
  value: null
  unit: square_feet
  meaning: "Smallest certified internal area the user will accept."
  default_source: profile
  profile_key: "min_floor_area_sqft"
  note: "Set in profile.yaml. Measured on the energy certificate, which excludes balconies."
floor_area_exception_band_sqft:
  value: null
  unit: square_feet
  meaning: "A narrower band the user allows only in a stated area or with stated compensations."
  default_source: profile
  note: "State the exception's scope in the report. Never apply an area-specific exception city-wide."
area_variance_investigate_pct:
  value: 5
  unit: percent
  meaning: "Gap between advertised and certified area above which the listing needs an explanation before anything on it is trusted."
  default_source: generic
  note: "The usual cause is a balcony counted in the advertised figure."
studio_living_area_share:
  value: 0.75
  unit: fraction
  meaning: "Living area at or above this share of total floor area means the flat is a studio, however it is advertised."
  default_source: generic

# -------------------------------------------------------- age and fabric ----
max_building_age_years:
  value: null
  unit: years
  meaning: "Oldest building the user will accept, from the first assessment year."
  default_source: profile
  profile_key: "max_building_age_years"
  note: "Set in profile.yaml. The first assessment year approximates completion; the earliest registered sale is stronger."
epc_validity_years:
  value: 10
  unit: years
  meaning: "How long an energy certificate stays valid."
  default_source: generic
  note: "A whole building re-assessed on one day is usually this clock expiring, not a refurbishment."
air_permeability_mech_vent_threshold:
  value: 5
  unit: "m3/h.m2 at 50 Pa"
  meaning: "Air permeability at or below this implies the dwelling needs mechanical ventilation to meet the ventilation building regulation."
  default_source: generic
  note: "Implies mechanical ventilation; does not identify which kind, and does not prove heat recovery."
heat_network_supplier_margin_flag:
  value: 1.0
  unit: "ratio of cost of sales to revenue"
  meaning: "A heat supplier whose cost of sales meets or exceeds revenue is selling below cost, which predicts a tariff rise."
  default_source: generic
  note: "Read from filed accounts on the company register, typically about a year before residents notice."

# ------------------------------------------------------------ construction --
planning_radius_m:
  value: 250
  unit: metres
  meaning: "Standard search radius for planning applications around the flat."
  default_source: generic
road_facade_distance_m:
  value: 60
  unit: metres
  meaning: "Within this distance of a major road, the building must be split by facade before any noise judgement."
  default_source: generic
  note: "Road-facing and courtyard-facing are two different products at the same rent. Include trunk-classified roads in the query."
hospital_helipad_distance_m:
  value: 300
  unit: metres
  meaning: "Distance within which an emergency entrance, ambulance route or helipad counts as a deduction."
  default_source: generic
  note: "Proximity to a hospital is never scored as a benefit on this axis."
construction_decision_within_tenancy:
  value: true
  unit: boolean
  meaning: "An undecided application whose decision falls inside the intended tenancy is a live risk."
  default_source: generic

# ------------------------------------------------------------------ crime ---
crime_box_half_width_m:
  value: 150
  unit: metres
  meaning: "Half-width of the standard crime polygon; the box is about 300 m by 305 m."
  default_source: generic
  note: "One fixed spec for every candidate. Resizing it per candidate changes the answer."
crime_box_lat_delta_deg:
  value: 0.00135
  unit: degrees
  meaning: "Latitude offset used to build the standard box."
  default_source: generic
crime_box_lng_delta_deg:
  value: 0.0022
  unit: degrees
  meaning: "Longitude offset used to build the standard box at London latitude."
  default_source: generic
  note: "Take the sign of the longitude from the geocoder. A flipped sign returns a fake quiet reading a kilometre away."
crime_window_months:
  value: 6
  unit: months
  meaning: "Fixed observation window for every candidate."
  default_source: generic
  note: "Missing months are marked missing. Never scale a short window up to a six-month equivalent, and never fill with zeros."
police_data_lag_months:
  value: "2-3"
  unit: months
  meaning: "How far behind the present the published street-level crime data runs."
  default_source: generic
  note: "Query the last-updated endpoint before choosing months; the newest month available is not last month."
crime_sensitivity_shift_m:
  value: 20
  unit: metres
  meaning: "Distance the box is shifted in each of four directions to produce a sensitivity range."
  default_source: generic
  note: "A 20 m shift has moved a count by 37 percent. Report the range, not a single figure."
crime_point_source_share_flag:
  value: 0.40
  unit: fraction
  meaning: "A single street anchor carrying this share or more of the counts is a point source and must be labelled."
  default_source: generic
crime_top_anchor_count:
  value: 5
  unit: anchors
  meaning: "How many street anchors to list. Spread across all five is neighbourhood-wide; one dominating is a point source."
  default_source: generic
night_route_node_share_flag:
  value: 0.50
  unit: fraction
  meaning: "Share of counts sitting on the station-to-door route above which the walk home is a red flag in its own right."
  default_source: generic
  note: "Nodes on the route home are never discounted, whatever the area grade says."

# ------------------------------------------------- management and reviews ---
review_burst_same_day_min:
  value: 4
  unit: reviews
  meaning: "This many reviews on one date is a review-drive day; all of them come out of the organic sample."
  default_source: generic
  note: "Applies even when the site does not mark them as incentivised."
review_staleness_years:
  value: 3
  unit: years
  meaning: "No natural (non-incentivised, non-burst) review within this period means the score is expired."
  default_source: generic
  note: "Say the building is unmeasured on reviews and stop quoting the number. Zero denominator is not clean."
review_min_organic_sample:
  value: 5
  unit: reviews
  meaning: "Fewest organic reviews that can support a management score."
  default_source: generic
  note: "One organic review is not a score. Always print the sample size next to the average."
management_organic_score_min:
  value: null
  unit: "score out of 5"
  meaning: "The user's bar for the organic management score."
  default_source: profile
  note: "No universal pass mark. Set in profile.yaml; state in the report which bar was used."

# ----------------------------------------------------------- legal facts ----
deposit_cap_weeks:
  value: 5
  unit: weeks_of_rent
  meaning: "Maximum tenancy deposit where the annual rent is below deposit_annual_rent_threshold_gbp."
  default_source: generic
  note: "Tenant Fees Act 2019. The cap runs on the current rent; an advertised deposit is often five weeks of an older, higher rent."
deposit_cap_weeks_high_rent:
  value: 6
  unit: weeks_of_rent
  meaning: "Maximum tenancy deposit where the annual rent is at or above deposit_annual_rent_threshold_gbp."
  default_source: generic
  note: "Tenant Fees Act 2019."
deposit_annual_rent_threshold_gbp:
  value: 50000
  unit: GBP_per_year
  meaning: "Annual rent at which the deposit cap changes from five to six weeks."
  default_source: generic
holding_deposit_weeks:
  value: 1
  unit: weeks_of_rent
  meaning: "Maximum holding deposit."
  default_source: generic
  note: "Tenant Fees Act 2019."
rent_in_advance_max_months:
  value: 1
  unit: months
  meaning: "Maximum rent that may be required in advance after the first payment."
  default_source: generic
  note: "Renters' Rights Act 2025, in force 2026-05-01 in England. It removes paying six or twelve months up front as a substitute for a guarantor."
deposit_protection_days:
  value: 30
  unit: days
  meaning: "Deadline for placing a deposit in a protection scheme."
  default_source: generic
  note: "Housing Act 2004."
tenant_notice_months:
  value: 2
  unit: months
  meaning: "Tenant's notice period on an assured periodic tenancy, in writing."
  default_source: generic
  note: "A shorter period can be agreed in writing. Agree it before signing if a short stay is possible. There is no minimum contract length."
short_let_nights_per_calendar_year:
  value: 90
  unit: nights
  meaning: "Nights of temporary sleeping accommodation in Greater London above which planning permission is needed."
  default_source: generic
  note: "Deregulation Act 2015 s.44. Counted per property per calendar year, not per person, and conditional on someone providing it being liable for council tax. Planning compliance is not lease, freeholder, mortgage or insurance permission."
land_registry_title_fee_gbp:
  value: 7
  unit: GBP
  meaning: "Cost of a title register or title plan."
  default_source: generic
  note: "A signed-in card payment; a human step, never automated."
land_registry_document_fee_gbp:
  value: 11
  unit: GBP
  meaning: "Cost of a copy of a filed document, such as a lease."
  default_source: generic

# ------------------------------------------------------------------ price ---
rent_ceiling_pcm:
  value: null
  unit: GBP_per_month
  meaning: "The user's rent ceiling before bills."
  default_source: profile
  profile_key: "budget.rent_pcm_target"
price_below_band_flag_pct:
  value: 15
  unit: percent
  meaning: "Below the local band by more than this: name the discount or leave."
  default_source: generic
  note: "Run the test on both the monthly rent and the pounds per square foot."
price_above_comparable_flag_pct:
  value: 15
  unit: percent
  meaning: "Above a same-building, same-floor comparable by more than this, with no nameable benefit: leave."
  default_source: generic

# ----------------------------------------------------------- aspect, light --
obstruction_angle_kill_deg:
  value: 45
  unit: degrees
  meaning: "Obstruction subtending more than this angle from the window, on a low floor, is the almost-no-light case."
  default_source: generic
  note: "Equivalent to the facing building being taller than the gap between the buildings."
sky_openness_good_obstruction_angle_deg:
  value: 25
  unit: degrees
  meaning: "Obstruction below this angle means the sky in front of the window is effectively open."
  default_source: generic
min_sky_openness_note:
  value: null
  unit: note
  meaning: "Sky openness, floor level and glazed area decide winter brightness; orientation is a summer and shoulder-season criterion."
  default_source: generic
  note: "Kept as an id so axis files can reference the rule rather than restate it."
floor_position_exclusions:
  value: null
  unit: list
  meaning: "Floor positions the user excludes outright, for example ground and basement."
  default_source: profile
  profile_key: "floors.reject_ground_floor, floors.prefer_floor_band"
  note: "Read from the certificate's property type, which records only Ground, Basement, Mid-floor and Top-floor."

# --------------------------------------------------------------- all-in ----
all_in_ceiling_pcm:
  value: null
  unit: GBP_per_month
  meaning: "Rent plus bills plus council tax ceiling."
  default_source: profile
  profile_key: "budget.all_in_pcm_ceiling"
  note: "The number the verdict is taken against. A named stretch above it belongs in budget.stretch_ceiling_and_conditions, never in this id."
edge_band_over_ceiling_pcm:
  value: 100
  unit: GBP_per_month
  meaning: "Over the all-in ceiling by up to this much is EDGE, and the report must carry the break-even rent."
  default_source: generic
  note: "More than this is a different price bracket, not an edge case."
bills_low_pcm:
  value: null
  unit: GBP_per_month
  meaning: "Optimistic bills scenario."
  default_source: profile
  note: "A shared sensitivity assumption, not a supplier quote. Use the same three figures for every candidate in a run and print them with the totals."
bills_planning_pcm:
  value: null
  unit: GBP_per_month
  meaning: "Planning bills scenario, the one the verdict is taken on."
  default_source: profile
  note: "A shared sensitivity assumption, not a supplier quote for any heating system."
bills_stress_pcm:
  value: null
  unit: GBP_per_month
  meaning: "Stress bills scenario."
  default_source: profile
bridging_weekly_cost:
  value: null
  unit: GBP_per_week
  meaning: "Weekly cost of temporary accommodation while waiting for a later move-in date."
  default_source: profile
  note: "Bridging is never an add-on to rent. Compare twelve-month totals: bridging weeks times weekly cost, plus remaining months times all-in."
move_in_window:
  value: null
  unit: date_range
  meaning: "The user's preferred move-in window."
  default_source: profile
  profile_key: "move_in_window.earliest, move_in_window.latest, move_in_window.tolerance_days"
  note: "Used by the all-in axis when a later start would need bridging."

# ---------------------------------------------------- commute, redundancy ---
commute_max_minutes:
  value: null
  unit: minutes
  meaning: "Door-to-door ceiling, measured at average walking speed."
  default_source: profile
  profile_key: "commute.max_door_to_door_min"
  note: "The destination and arrival time are also profile values (commute.destination, commute.arrive_by). Neither has a default: the skill never guesses a destination."
commute_entrance_buffer_min:
  value: 3
  unit: minutes
  meaning: "Buffer added at the destination, from the public door to the actual door."
  default_source: generic
  note: "Reported separately. Never folded silently into the headline time."
redundancy_walk_min:
  value: 10
  unit: minutes
  meaning: "Walk within which a second, independent rail family counts as redundancy."
  default_source: generic
redundancy_walk_m:
  value: 800
  unit: metres
  meaning: "Distance equivalent of redundancy_walk_min."
  default_source: generic
station_to_door_walk_max_min:
  value: null
  unit: minutes
  meaning: "The user's ceiling for the walk from station to front door."
  default_source: profile
  note: "Read the journey legs, not the total: a walking leg can contain zero-time in-station segments."

# -------------------------------------------------- low-maintenance living --
supermarket_walk_min:
  value: 3
  unit: minutes
  meaning: "A food shop within this walk."
  default_source: generic
washing_machine_required:
  value: null
  unit: boolean
  meaning: "Whether a machine inside the flat is a requirement for this user."
  default_source: profile
  profile_key: "must_haves (washing_machine_in_flat)"
  note: "For most users this is close to a hard requirement. Grade the alternatives rather than treating them as equal."
launderette_trip_cost:
  value: null
  unit: GBP_per_trip
  meaning: "Cost of one launderette trip, for costing a flat with no machine."
  default_source: profile
launderette_trip_minutes:
  value: null
  unit: minutes
  meaning: "Time cost of one launderette trip, for costing a flat with no machine."
  default_source: profile

reject_no_sky:
  value: null
  unit: boolean
  meaning: "Whether a flat whose main windows cannot see sky is a hard fail rather than a deduction."
  default_source: profile
  profile_key: "light.reject_no_sky"
  note: "Applied together with obstruction_angle_kill_deg, which defines what counts as no sky."
quiet_over_light:
  value: null
  unit: boolean
  meaning: "Whether the quiet elevation wins when quiet and light conflict."
  default_source: profile
  profile_key: "quiet_over_light"
  note: "The rule holds short of the almost-no-light case, which is decided by reject_no_sky."
redundancy_min_grade:
  value: null
  unit: grade
  meaning: "Lowest acceptable commute redundancy grade."
  default_source: profile
  profile_key: "commute.redundancy_min_grade"
  note: "Letters mean what report-schema.json fixes them to mean: A two independent rail families within redundancy_walk_min, B one rail family plus a bus route that serves the journey, C one line only."
```

---

## Sources catalogue (tested 2026-09-03) — `skills/vet-flat/references/sources.yaml`

```yaml
# Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
#
# Every source the axis files use. Per-borough planning, committee and licensing pages live in boroughs.yaml.
#
# Field guide
#   official            true if a public body, a statutory register or legislation publishes it
#   access              open | open_robots_disallow | key_free | login_free | paid | manual
#   method              GET | POST | manual
#   needs_key           true if a key, login or payment is required before a request will work
#   robots_note         what robots.txt said for a general crawler on the tested path
#   tos_note            what the site's terms say about automated access
#   content_assertion   a string that must appear in a good response; a 200 without it is a failure
#   used_by_scripts     the scripts in skills/vet-flat/scripts that call it
#   used_for            the axes and questions it answers
#   last_tested         the date the URL was actually fetched
#   verify_before_release  true where this repo has not itself opened the page and confirmed the content
version: "2026-09-03"
tested_from: "London, UK network, curl with a browser user agent, 1-2 s between requests to one host"

sources:

  # ------------------------------------------------------------ geography --
  - id: postcodes_io_lookup
    name: "postcodes.io postcode lookup"
    url: "https://api.postcodes.io/postcodes/SE19SG"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served (404), so nothing is disallowed."
    tos_note: "Open data service over Ordnance Survey and ONS open data."
    content_assertion: '"result"'
    used_by_scripts: [geo.py]
    used_for: [identity, geocoding, borough_resolution, ward, crime_box_centre]
    last_tested: 2026-09-03
    note: "The most reliable source in the set. Always take coordinates from here, never from a map pin, and never guess the sign of the longitude."

  - id: postcodes_io_nearest
    name: "postcodes.io nearest postcodes (radius search)"
    url: "https://api.postcodes.io/postcodes/SE19SG/nearest"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served (404)."
    tos_note: "Open data service."
    content_assertion: '"result"'
    used_by_scripts: [geo.py]
    used_for: [area_sweep, postcode_coverage, comparables]
    last_tested: 2026-09-03
    note: "Radius caps at nearest_postcode_max_radius_m. A larger radius returns HTTP 200 with the same result set and no error, so never assume a wide radius took effect."

  # ---------------------------------------------------- energy performance --
  - id: epc_find_by_postcode
    name: "GOV.UK Find an energy certificate, postcode search"
    url: "https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-postcode"
    official: true
    access: open_robots_disallow
    method: GET
    needs_key: false
    robots_note: "Disallow: / for a general crawler, with two /type-of-property paths allowed. No group names any AI user agent, so they all fall under the general rule. The page also carries a noindex, nofollow meta tag."
    tos_note: "Crown copyright, Open Government Licence. No automation ban in the terms; the robots file is the constraint."
    content_assertion: "EPCs for"
    used_by_scripts: [epc.py]
    used_for: [identity, floor_area, age, heating, building_profile]
    last_tested: 2026-09-03
    note: "Server-rendered. Flat-level addresses appear in full. A robots-honouring fetcher cannot read this; ask the user to paste the page."

  - id: epc_find_by_street
    name: "GOV.UK Find an energy certificate, street and town search"
    url: "https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-street-name-and-town"
    official: true
    access: open_robots_disallow
    method: GET
    needs_key: false
    robots_note: "As epc_find_by_postcode."
    tos_note: "Open Government Licence."
    content_assertion: "energy certificate"
    used_by_scripts: [epc.py]
    used_for: [identity, floor_area]
    last_tested: 2026-09-03
    note: "Parameters are street_name and town. Use it when a building is split across postcodes and a high floor is missing from the postcode search. A broad street returns a too-many-results page."

  - id: epc_certificate_page
    name: "GOV.UK energy certificate page"
    url: "https://find-energy-certificate.service.gov.uk/energy-certificate/"
    official: true
    access: open_robots_disallow
    method: GET
    needs_key: false
    robots_note: "As epc_find_by_postcode; two major search engines are additionally barred from this path."
    tos_note: "Open Government Licence."
    content_assertion: "Total floor area"
    used_by_scripts: [epc.py]
    used_for: [floor_area, property_type, air_permeability, heating, rating_history]
    last_tested: 2026-09-03
    note: "Keyed by the 20-digit certificate reference. The only working route to a certified floor area."

  - id: epc_json_api_absent
    name: "GOV.UK energy certificate register, JSON API (confirmed absent)"
    url: "https://find-energy-certificate.service.gov.uk/api/domestic/"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "As epc_find_by_postcode."
    tos_note: "n/a"
    content_assertion: "Page not found"
    used_by_scripts: []
    used_for: [negative_result]
    last_tested: 2026-09-03
    note: "Recorded so nobody rebuilds a client for it: both the search and the certificate JSON paths return the GOV.UK page-not-found page. Parse the HTML instead."

  - id: epc_open_data_bulk
    name: "Get energy performance of buildings data (bulk download)"
    url: "https://get-energy-performance-data.communities.gov.uk/"
    official: true
    access: login_free
    method: manual
    needs_key: true
    robots_note: "Allow the homepage and an opt-out path, Disallow: / for everything else."
    tos_note: "Open Government Licence, behind a free national sign-in account."
    content_assertion: "Get energy performance of buildings data"
    used_by_scripts: []
    used_for: [bulk_epc, area_sweep]
    last_tested: 2026-09-03
    note: "This replaced the old open-data domain, whose API paths now 404. Bulk download needs a free account; a human step, never an automated sign-in."

  # ----------------------------------------------------------------- crime --
  - id: police_uk_crimes_street
    name: "Police open data, street-level crime"
    url: "https://data.police.uk/api/crimes-street/all-crime"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "robots.txt is served empty, so nothing is disallowed for anyone."
    tos_note: "Open Government Licence."
    content_assertion: '"category"'
    used_by_scripts: [crime.py]
    used_for: [crime, safety, night_route]
    last_tested: 2026-09-03
    note: "Use the poly form for a fixed box; the lat/lng form searches a one-mile circle, which is a different question. Locations are snapped to anonymised street anchors."

  - id: police_uk_crime_last_updated
    name: "Police open data, last updated"
    url: "https://data.police.uk/api/crime-last-updated"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "Empty robots.txt."
    tos_note: "Open Government Licence."
    content_assertion: '"date"'
    used_by_scripts: [crime.py]
    used_for: [crime, data_freshness]
    last_tested: 2026-09-03
    note: "Call this before choosing months. It returns the newest data month, which ran two to three months behind the calendar when tested."

  - id: police_uk_crimes_street_dates
    name: "Police open data, available data months"
    url: "https://data.police.uk/api/crimes-street-dates"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "Empty robots.txt."
    tos_note: "Open Government Licence."
    content_assertion: '"date"'
    used_by_scripts: [crime.py]
    used_for: [crime, data_freshness]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Intended use is to list the months actually available before building a fixed window, so missing months are marked rather than filled."

  - id: police_uk_neighbourhoods
    name: "Police open data, neighbourhood teams"
    url: "https://data.police.uk/api/metropolitan/neighbourhoods"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "Empty robots.txt."
    tos_note: "Open Government Licence."
    content_assertion: '"id"'
    used_by_scripts: [crime.py]
    used_for: [crime, neighbourhood_policing]
    last_tested: 2026-09-03
    note: "Identifiers are statistical ward codes. The City of London has its own force identifier and is not covered by the metropolitan force."

  # ------------------------------------------------------------- transport --
  - id: tfl_journey_planner
    name: "Transport for London Unified API, journey planner"
    url: "https://api.tfl.gov.uk/Journey/JourneyResults/"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served."
    tos_note: "Open data under the transport authority's own terms; a free application key raises the quota."
    content_assertion: '"journeys"'
    used_by_scripts: [commute.py]
    used_for: [commute, door_to_door, walk_to_station]
    last_tested: 2026-09-03
    note: "Accepts postcodes, place names or coordinates for both ends. Add an arrival time for a commute test. The destination is always an argument, never built into a script."

  - id: tfl_stoppoint_search
    name: "Transport for London Unified API, stop point search and radius"
    url: "https://api.tfl.gov.uk/StopPoint/Search/"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served."
    tos_note: "Open data; free key optional."
    content_assertion: '"matches"'
    used_by_scripts: [commute.py]
    used_for: [commute, redundancy, walk_to_station]
    last_tested: 2026-09-03
    note: "The radius form with stop types returns the nearest stations and their modes, which is what the redundancy grade is built from."

  # -------------------------------------------------------------- planning --
  - id: gla_planning_datahub_post
    name: "London-wide planning application index (search, POST)"
    url: "https://planningdata.london.gov.uk/api-guest/applications/_search"
    official: true
    access: open
    method: POST
    needs_key: false
    robots_note: "No robots.txt is served."
    tos_note: "Open guest search over a public planning dataset."
    content_assertion: '"hits"'
    used_by_scripts: [planning.py]
    used_for: [construction, development_pipeline, decision_conditions]
    last_tested: 2026-09-03
    note: "Covers every London planning authority in one index. Zero hits is a coverage gap, not an absence: it carries referable and major schemes, and small named sites can simply be missing. Its status field can mark an implemented permission as lapsed, so take decision dates and form data from here and the real state from recent condition activity."

  - id: gla_planning_datahub_get
    name: "London-wide planning application index (search, GET form)"
    url: "https://planningdata.london.gov.uk/api-guest/applications/_search"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served."
    tos_note: "As above."
    content_assertion: '"hits"'
    used_by_scripts: [planning.py]
    used_for: [construction, development_pipeline]
    last_tested: 2026-09-03
    note: "Same index, query passed as an encoded source parameter. This is the form a fetch-only runtime can use."

  - id: planit_applications_api
    name: "PlanIt UK planning application aggregator"
    url: "https://www.planit.org.uk/api/applics/json"
    official: false
    access: open_robots_disallow
    method: GET
    needs_key: false
    robots_note: "Disallow on the API path for a general crawler; no group names any AI user agent, so all fall under it."
    tos_note: "Non-commercial use of aggregated public planning data."
    content_assertion: '"records"'
    used_by_scripts: [planning.py]
    used_for: [construction, second_opinion]
    last_tested: 2026-09-03
    note: "Query by postcode plus radius, or by authority plus a date range. A free-text search matches only the description field, so searching a site name returns an empty set that is easy to misread as no activity. Records can be years stale."

  - id: borough_planning_portals
    name: "Borough planning registers (per-borough URLs in boroughs.yaml)"
    url: null
    official: true
    access: open_robots_disallow
    method: manual
    needs_key: false
    robots_note: "The common portal software serves a blanket Disallow: / on every borough instance tested."
    tos_note: "Public registers; the robots file is the constraint, not the terms."
    content_assertion: "Simple Search"
    used_by_scripts: [planning.py]
    used_for: [construction, condition_discharge, officer_reports]
    last_tested: 2026-09-03
    note: "Reachable but robots-disallowed, so treat as a user step. This is where condition discharge lives: pre-commencement conditions mean works are starting, pre-occupation conditions mean they are finishing. Some instances hide withdrawn applications behind a details-not-available page."

  - id: council_committee_reports
    name: "Council committee and democracy sites (per-borough URLs in boroughs.yaml)"
    url: null
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "Typically only a script path is disallowed; the agenda pages are allowed."
    tos_note: "Public meeting papers."
    content_assertion: "Agenda for"
    used_by_scripts: [planning.py]
    used_for: [construction, daylight_assessment, officer_reports]
    last_tested: 2026-09-03
    note: "The highest-risk trap in the set: a stale meeting identifier returns HTTP 200 with a plausible generic page. Always assert on the title containing 'Agenda for', and discover identifiers by walking the committee list, then the meeting list, then the documents page. Officer and committee reports name affected buildings and give window-by-window daylight findings."

  # ----------------------------------------------------- roads and geometry --
  - id: osm_overpass
    name: "OpenStreetMap Overpass API"
    url: "https://overpass-api.de/api/interpreter"
    official: false
    access: open_robots_disallow
    method: POST
    needs_key: false
    robots_note: "Disallow on the API path for a general crawler; no group names any AI user agent."
    tos_note: "Open Database Licence data; the public instance rate-limits aggressively."
    content_assertion: '"elements"'
    used_by_scripts: [roads.py]
    used_for: [road_noise, railway_distance, nearby_uses, facade_split]
    last_tested: 2026-09-03
    note: "This host refuses browser user agents with 406; send a descriptive tool user agent instead, which is the inverse of every other source here. Any road query must include the trunk class or major A-roads are missed."

  - id: defra_noise_road_mapping
    name: "Strategic road noise mapping, England"
    url: "https://environment.data.gov.uk/dataset/562c9d56-7c2d-4d42-83bb-578d6e97a517"
    official: true
    access: open
    method: manual
    needs_key: false
    robots_note: "No restriction observed on the dataset page."
    tos_note: "Open Government Licence."
    content_assertion: "Road Noise"
    used_by_scripts: []
    used_for: [noise]
    last_tested: 2026-09-03
    note: "A bulk geographic download on a 10 m grid with day and night bands, not a per-address lookup. Rail and airport rounds are sibling datasets."

  - id: defra_noise_agglomerations
    name: "Environmental noise mapping, urban agglomerations"
    url: "https://environment.data.gov.uk/dataset/c4bc5ebd-eab8-4b8a-be54-83d2f7132059"
    official: true
    access: open
    method: manual
    needs_key: false
    robots_note: "No restriction observed."
    tos_note: "Open Government Licence."
    content_assertion: "noise"
    used_by_scripts: []
    used_for: [noise]
    last_tested: 2026-09-03
    note: "The layer that covers Greater London. Manual download."

  - id: laqn_monitoring_sites
    name: "London air quality network, monitoring sites"
    url: "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "No restriction observed."
    tos_note: "Academic network publishing open air quality data."
    content_assertion: "MonitoringSite"
    used_by_scripts: []
    used_for: [air_quality]
    last_tested: 2026-09-03
    note: "Each site carries coordinates and a site type; use it to find the monitor nearest the flat."

  - id: laqn_hourly_index
    name: "London air quality network, hourly index"
    url: "https://api.erg.ic.ac.uk/AirQuality/Hourly/MonitoringIndex/GroupName=London/Json"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "No restriction observed."
    tos_note: "As above."
    content_assertion: "HourlyAirQualityIndex"
    used_by_scripts: []
    used_for: [air_quality]
    last_tested: 2026-09-03

  - id: ea_long_term_flood_risk
    name: "Check long term flood risk"
    url: "https://check-long-term-flood-risk.service.gov.uk/"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Open Government Licence."
    content_assertion: "Where do you want to check"
    used_by_scripts: []
    used_for: [flood_risk, insurance]
    last_tested: 2026-09-03
    note: "Server-rendered flow: postcode, then address, then the risk page. No challenge."

  # ------------------------------------------------ companies and ownership --
  - id: companies_house_html
    name: "Companies House, find and update company information"
    url: "https://find-and-update.company-information.service.gov.uk/"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No robots.txt is served, so nothing is disallowed."
    tos_note: "Crown copyright; public register."
    content_assertion: "Companies House"
    used_by_scripts: [company.py]
    used_for: [landlord_identity, agent_identity, sic_codes, charges, filings, resident_management_company]
    last_tested: 2026-09-03
    note: "Search, company page, officers and filing history are all server-rendered. Match on the company number, never the name: dissolved same-name shells are common. Searching by registered address finds every company at a building, which is how you learn whether a resident-owned management company exists."

  - id: companies_house_api
    name: "Companies House REST API"
    url: "https://api.company-information.service.gov.uk/"
    official: true
    access: key_free
    method: GET
    needs_key: true
    robots_note: "n/a, API host."
    tos_note: "Free key after a one-off registration; public register data."
    content_assertion: '"company_name"'
    used_by_scripts: [company.py]
    used_for: [landlord_identity, agent_identity]
    last_tested: 2026-09-03
    note: "Without a key it returns an empty-authorisation error, which confirms the endpoint is live. The free HTML service above covers most vetting without a key."

  - id: land_registry_price_paid_sparql
    name: "HM Land Registry open data, price paid and transactions"
    url: "https://landregistry.data.gov.uk/landregistry/query"
    official: true
    access: open
    method: POST
    needs_key: false
    robots_note: "No blocking observed on the query endpoint."
    tos_note: "Open Government Licence."
    content_assertion: '"results"'
    used_by_scripts: [landregistry.py]
    used_for: [price_comparables, building_age, new_build_flag]
    last_tested: 2026-09-03
    note: "Works without a key. Postcodes must be spaced and upper case exactly as registered. The earliest sale with a new-build flag is the hardest available counter-evidence to a claimed building age."

  - id: land_registry_title_register
    name: "HM Land Registry title register and title plan"
    url: "https://www.gov.uk/search-property-information-land-registry"
    official: true
    access: paid
    method: manual
    needs_key: true
    robots_note: "The search service itself sits behind an interactive challenge whose robots file cannot be read."
    tos_note: "Paid, signed-in service."
    content_assertion: "title register"
    used_by_scripts: [landregistry.py]
    used_for: [ownership, proprietor, lease_term, restrictions]
    last_tested: 2026-09-03
    note: "land_registry_title_fee_gbp per title register or plan, land_registry_document_fee_gbp per filed document. Card payment and a signed-in journey: a human step, never automated. The only source that names the registered proprietor."

  # ------------------------------------ redress, client money, enforcement ---
  - id: client_money_protect
    name: "Client Money Protect, agent search"
    url: "https://www.clientmoneyprotect.co.uk/agent-search/"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "Only administrative paths disallowed."
    tos_note: "No automation ban observed."
    content_assertion: "Agent search"
    used_by_scripts: [redress.py]
    used_for: [agent_compliance, client_money_protection, deposit_safety]
    last_tested: 2026-09-03
    note: "An agent holding rent or deposits must belong to a client-money scheme by law, but this is one provider of several: absence here is a prompt to check the others, not yet a finding. Open the certificate itself to read the current expiry."

  - id: property_redress_agent_finder
    name: "Property Redress, agent finder"
    url: "https://www.propertyredress.co.uk/agent-finder"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed on the finder page."
    tos_note: "No automation ban observed."
    content_assertion: "Agent finder"
    used_by_scripts: [redress.py]
    used_for: [agent_compliance, redress_scheme]
    last_tested: 2026-09-03
    note: "An older member-search path now redirects to the home page. A member-lookup endpoint on the same service silently ignores its name filter and returns the same recent-members list for every query, so never report its default output as a search result."

  - id: property_ombudsman_find_a_member
    name: "The Property Ombudsman, find a member"
    url: "https://www.tpos.co.uk/find-a-member"
    official: false
    access: manual
    method: manual
    needs_key: false
    robots_note: "robots.txt blocks several named AI crawler user agents site-wide, including the kind this skill's fetcher uses. Do not crawl it."
    tos_note: "The site asserts a reservation of rights against text and data mining."
    content_assertion: "member"
    used_by_scripts: [redress.py]
    used_for: [agent_compliance, redress_scheme]
    last_tested: 2026-09-03
    note: "The member search also redirects away from this path. Ask the user to open the member search and paste the result."

  - id: propertymark_find_an_expert
    name: "Propertymark, find an agent"
    url: "https://www.propertymark.co.uk/find-an-expert.html"
    official: false
    access: manual
    method: manual
    needs_key: false
    robots_note: "The search query-string form is specifically disallowed."
    tos_note: "No general automation ban observed."
    content_assertion: "find an expert"
    used_by_scripts: [redress.py]
    used_for: [agent_compliance, professional_body]
    last_tested: 2026-09-03
    note: "The page loads but the results are rendered in the browser, so there is nothing to parse. A human step."

  - id: gla_rogue_landlord_checker
    name: "London rogue landlord and agent checker"
    url: "https://www.london.gov.uk/programmes-strategies/housing-and-land/renting-home/private-renting/check-landlord-or-agent/rogue-landlord-and-agent-checker"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Public enforcement record."
    content_assertion: "rogue landlord"
    used_by_scripts: [redress.py]
    used_for: [landlord_identity, agent_identity, enforcement_history]
    last_tested: 2026-09-03
    note: "Server-rendered with name and address filters. It records only enforcement action taken by London boroughs and reported centrally, so absence is not proof of a clean landlord."

  - id: ftt_property_chamber_decisions
    name: "First-tier Tribunal (Property Chamber) decisions"
    url: "https://www.gov.uk/residential-property-tribunal-decisions"
    official: true
    access: open
    method: manual
    needs_key: false
    robots_note: "Not checked."
    tos_note: "Open Government Licence."
    content_assertion: "residential property tribunal"
    used_by_scripts: []
    used_for: [management_disputes, service_charges, landlord_conduct]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Used to check whether a building or a managing agent has a decided dispute history."

  - id: find_case_law
    name: "Find Case Law (National Archives)"
    url: "https://caselaw.nationalarchives.gov.uk/"
    official: true
    access: open
    method: manual
    needs_key: false
    robots_note: "Not checked."
    tos_note: "Open Justice Licence."
    content_assertion: "Find Case Law"
    used_by_scripts: []
    used_for: [landlord_conduct, judgments]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Used in the conduct forensics on a landlord or agent entity."

  # ------------------------------------------------------- heat and energy --
  - id: heat_trust_members
    name: "Heat Trust registered sites and participants"
    url: "https://heattrust.org/our-members"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "Only default administrative paths disallowed."
    tos_note: "No automation ban observed."
    content_assertion: "Heat Trust Registered Sites"
    used_by_scripts: [redress.py]
    used_for: [heat_network, communal_heating, consumer_protection, running_cost]
    last_tested: 2026-09-03
    note: "Supplier and site names appear in plain HTML, so they cross-reference straight against the company register. A registered site has a consumer-protection standard on a heat network that is otherwise uncapped on price. An older path for this page returns 404."

  - id: ofgem_heat_networks
    name: "Ofgem, heat networks regulation"
    url: "https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/heat-networks"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "Standard content-management paths disallowed only."
    tos_note: "Public regulator information."
    content_assertion: "Heat networks"
    used_by_scripts: []
    used_for: [heat_network, regulation, complaints_route]
    last_tested: 2026-09-03
    note: "Follow the redirect; the short path is not canonical. The regulator took on heat networks, with pricing benchmarks and standards of performance following later, so there is a period with a statutory complaints route but no price cap. Check the current position before quoting a date."

  # ------------------------------------------------------------ council tax --
  - id: voa_council_tax_band
    name: "Check your council tax band (England and Wales)"
    url: "https://www.tax.service.gov.uk/check-council-tax-band/search"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Open Government Licence."
    content_assertion: "Council Tax band"
    used_by_scripts: []
    used_for: [council_tax, all_in_cost]
    last_tested: 2026-09-03
    note: "The national band lookup. The per-borough entries in boroughs.yaml are billing and rate pages, not band lookups."

  # ----------------------------------------------------------- legislation --
  - id: legislation_renters_rights_act_2025
    name: "Renters' Rights Act 2025 (c. 26)"
    url: "https://www.legislation.gov.uk/ukpga/2025/26/contents"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Open Government Licence."
    content_assertion: "Renters' Rights Act 2025"
    used_by_scripts: []
    used_for: [tenancy_law, periodic_tenancy, rent_in_advance]
    last_tested: 2026-09-03
    note: "Exact title verified: a UK Public General Act of 2025, chapter 26. Earlier drafts of this skill named it as a 2026 Act; that was wrong."

  - id: legislation_rra_commencement_no2
    name: "Renters' Rights Act 2025 (Commencement No. 2 and Transitional and Saving Provisions) Regulations 2026 (SI 2026/421)"
    url: "https://www.legislation.gov.uk/uksi/2026/421/regulation/2/made"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Open Government Licence."
    content_assertion: "come into force on 1st May 2026"
    used_by_scripts: []
    used_for: [tenancy_law, commencement_date]
    last_tested: 2026-09-03
    note: "Commencement verified on this URL: the tenancy-reform chapter, the possession-grounds schedule and the related schedule come into force on 2026-05-01 for assured tenancies that are not social housing assured tenancies."

  - id: legislation_deregulation_2015_s44
    name: "Deregulation Act 2015 s.44, short-term use of London accommodation"
    url: "https://www.legislation.gov.uk/ukpga/2015/20/section/44"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "No blocking observed."
    tos_note: "Open Government Licence."
    content_assertion: "Short-term use of London accommodation"
    used_by_scripts: []
    used_for: [short_let, lease_breach, planning]
    last_tested: 2026-09-03
    note: "Content verified. It amends the 1973 London general powers Act by inserting the provision that carries the nightly limit and its conditions; the number of nights sits in the inserted section, not in the s.44 heading."

  - id: legislation_tenant_fees_act_2019
    name: "Tenant Fees Act 2019 (c. 4), permitted payments and deposit caps"
    url: "https://www.legislation.gov.uk/ukpga/2019/4/schedule/1"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "As other legislation pages."
    tos_note: "Open Government Licence."
    content_assertion: "Permitted payments"
    used_by_scripts: []
    used_for: [deposit_cap, holding_deposit, prohibited_fees]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Source for deposit_cap_weeks, deposit_cap_weeks_high_rent, deposit_annual_rent_threshold_gbp and holding_deposit_weeks. Confirm the paragraph numbers and that the caps are current before quoting them in a report."

  - id: legislation_housing_act_2004_s213
    name: "Housing Act 2004 s.213, tenancy deposit schemes"
    url: "https://www.legislation.gov.uk/ukpga/2004/34/section/213"
    official: true
    access: open
    method: GET
    needs_key: false
    robots_note: "As other legislation pages."
    tos_note: "Open Government Licence."
    content_assertion: "tenancy deposit scheme"
    used_by_scripts: []
    used_for: [deposit_protection]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Source for deposit_protection_days. Confirm the current period before quoting it."

  # ------------------------------------------------------------- archives ---
  - id: wayback_availability
    name: "Internet Archive availability API and snapshots"
    url: "https://archive.org/wayback/available"
    official: false
    access: open
    method: GET
    needs_key: false
    robots_note: "Not checked."
    tos_note: "Public archive."
    content_assertion: '"archived_snapshots"'
    used_by_scripts: []
    used_for: [company_history, listing_history, claim_dating]
    last_tested: null
    verify_before_release: true
    note: "Not opened by this repo's audit. Ask the availability endpoint for an exact timestamp first, then request that timestamped snapshot; a vague year-level snapshot path can hang."

  # ------------------------------ commercial portals and review sites -------
  - id: commercial_portals_and_review_sites
    name: "Rightmove; Zoopla; OnTheMarket; OpenRent; HomeViews; Trustpilot; Google reviews; Airbnb; Booking.com"
    url: null
    official: false
    access: manual
    method: manual
    needs_key: false
    robots_note: "Not recorded. Their robots files are more permissive than their terms, and robots compliance is not terms compliance."
    tos_note: "Automated access prohibited. Every one of these sites whose terms could be read bans bots, crawlers, scrapers and automated data collection."
    content_assertion: null
    used_by_scripts: []
    used_for: [listing_text, asking_price, price_reduction_history, resident_reviews, management_reputation, short_let_check]
    last_tested: null
    note: "Deliberately no URL, endpoint, parameter, selector or technique is recorded for any of these. Ask the user to open the page and paste the text, or use your own compliant means; see inputs.md. The review-reading method in axes/06-management-neighbours.md applies to whatever text the user supplies."
```

---

## Borough catalogue summary — `skills/vet-flat/references/boroughs-summary.md`

````markdown
# London flat vetting: verified source catalogue

Companion summary for `boroughs.yaml`. **All 33 London local authorities (32 boroughs + the City of London) plus 35 London-wide / national sources.**

## How this was verified

Every URL was fetched **exactly once** on **2026-09-03** from a London UK network (macOS, curl 8.7.1 / LibreSSL 3.3.6) with:

```
curl -sS -L -m 12 -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 \
  (KHTML, like Gecko) Chrome/128.0 Safari/537.36" -o <tmpfile> \
  -w "%{http_code} %{content_type} %{url_effective}"
```

For each response the HTTP status, final URL, `<title>` (or JSON shape) and any Cloudflare / AWS WAF / Imperva challenge were recorded. `robots.txt` was fetched once per planning-portal host. No logins, no payments, no accounts.

**Read the status columns carefully.** Three councils return a *success* code that is not a real page:

- **HTTP 202 + zero-byte body** = AWS WAF JavaScript challenge (Hammersmith & Fulham, Waltham Forest) or an NEC/Northgate hub refusing non-JS clients (Barking & Dagenham, Hackney, Merton).
- **HTTP 200 + "Pardon Our Interruption"** = Imperva (all of `barnet.gov.uk`). A 200 from that host proves nothing.
- **HTTP 403 + "Just a moment..."** = Cloudflare (Camden, Enfield, Kensington & Chelsea, and several `*.moderngov.co.uk` committee hosts).

## Headline counts

| Measure | Count |
|---|---|
| Planning portals on **Idox** Public Access | **18** of 33 |
| Planning portals on **Northgate / NEC** | 5 |
| Planning portals on **Arcus** (Salesforce public register) | 2 |
| Planning portals on **something else** (Agile/IEG4 SPA, OcellaWeb, Objective, bespoke) | 8 |
| Planning hosts whose robots.txt is `* Disallow: /` | 23 |
| Planning hosts whose robots.txt is unknown (host blocked/unreachable) | 5 |
| Planning hosts whose robots.txt is none published | 3 |
| Planning hosts whose robots.txt is crawling allowed | 2 |
| Councils with an **active selective OR additional** scheme | **28** of 33 |
| - of which **selective** is live | 22 |
| - of which **additional** is live | 26 |
| Councils on **mandatory HMO licensing only** | 5 (City of London, Bromley, Croydon, Kingston upon Thames, Richmond upon Thames) |
| Councils with **no public online register** | 3 (City of London, Bromley, Hammersmith and Fulham) |

## Local authorities

Legend: **OK** = real page returned; **BLOCKED** = bot wall (status shown); **FAIL** = no HTTP response at all.

| Borough | GSS | Planning search | Sys | robots (`*`) | Cttee | Licensing page | Active schemes | Public register | C.Tax | What to watch |
|---|---|---|---|---|---|---|---|---|---|---|
| **Barking and Dagenham** | E09000002 | [link](https://online-befirst.lbbd.gov.uk/planning/index.html?fa=search) BLOCKED 202 | northgate | `* Disallow: /` | BLOCKED 403 | [link](https://www.lbbd.gov.uk/private-sector-housing/property-licensing) BLOCKED 403 | mandatory, additional, selective | [link](https://lbbd.metastreet.co.uk/public-register) 200 | BLOCKED 403 | WORST-CASE BOROUGH FOR AUTOMATION: the council website (plain 403 on every path), the planning hub (202 with an empty body) and the committee site (Cloudflare 403) are ALL closed to scripted access. |
| **Barnet** | E09000003 | [link](https://publicaccess.barnet.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | BLOCKED 403 | [link](https://www.barnet.gov.uk/housing/private-housing/houses-multiple-occupation) BLOCKED 200 | mandatory, additional | [link](https://open.barnet.gov.uk/dataset/hmo-register-29r12) 200 | BLOCKED 200 | Idox planning portal is fine; the COUNCIL site is not - Imperva returns HTTP 200 with a 'Pardon Our Interruption' body for every barnet.gov.uk path, so never treat a 200 from that host as proof of anything. |
| **Bexley** | E09000004 | [link](https://pa.bexley.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.bexley.gov.uk/services/housing/property-licensing/property-licensing-schemes) OK 200 | mandatory, selective | [link](https://www.bexley.gov.uk/sites/default/files/2026-08/hmo-public-register-10-aug-2026.csv) 200 | OK 200 | Everything works: Idox planning, ModernGov committee, plain-HTML licensing page, CSV register. |
| **Brent** | E09000005 | [link](https://pa.brent.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.brent.gov.uk/housing/landlords/property-licensing) OK 200 | mandatory, additional, selective | [link](https://www.brent.gov.uk/-/media/files/resident-documents/housing-documents/online-register-of-licenced-properties.pdf) 200 | OK 200 | Highest licensing coverage after Newham - every private rental except Wembley Park ward needs a licence, so an unlicensed Brent flat is a live compliance flag. |
| **Bromley** | E09000006 | [link](https://planningaccess.bromley.gov.uk/s/) OK 200 | arcus | `* Allow: /` | OK 200 | [link](https://www.bromley.gov.uk/housing-advice-options/houses-multiple-occupation-hmo-advice-landlords) OK 200 | mandatory | none | OK 200 | Planning moved off Idox to an Arcus/Salesforce register whose results are JS-rendered - and it is the ONLY London planning portal whose robots.txt permits crawling. |
| **Camden** | E09000007 | [link](https://accountforms.camden.gov.uk/planning-search/) OK 200 | other | unknown | BLOCKED 403 | [link](https://www.camden.gov.uk/houses-multiple-occupation) BLOCKED 403 | mandatory, additional | [link](https://opendata.camden.gov.uk/Housing/HMO-Licensing-Register/x43g-c2rf) 200 | BLOCKED 403 | Cloudflare blocks www.camden.gov.uk AND the planningrecords portal. Two doors are open: accountforms.camden.gov.uk/planning-search/ for planning (server-rendered, works) and opendata.camden.gov.uk for the HMO register. |
| **City of London** | E09000001 | [link](https://www.planning2.cityoflondon.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.cityoflondon.gov.uk/services/licensing/other-licence-and-business-permit-types/houses-in-multiple-occupation-hmo) OK 200 | mandatory | none | OK 200 | Square Mile: Idox planning portal works and is the cleanest in London, but there is no online HMO register at all - a licence check is an appointment at the Guildhall. |
| **Croydon** | E09000008 | [link](https://publicaccess3.croydon.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.croydon.gov.uk/housing/private-tenants/landlord-licensing) OK 200 | mandatory | [link](https://landlordlicensing.croydon.gov.uk/public-register) 200 | OK 200 | TIME-CRITICAL: mandatory-HMO-only today, but selective plus additional licensing go live on 25 September 2026, so any licensing verdict reached now expires in weeks. |
| **Ealing** | E09000009 | [link](https://pam.ealing.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | BLOCKED 403 | [link](https://www.ealing.gov.uk/info/201086/housing/3306/private_rented_properties) OK 200 | mandatory, additional, selective | [link](https://ealing.metastreet.co.uk/public-register) 200 | OK 200 | All three licensing schemes run to 31 March 2027, but the selective AREAS exist only inside a JS map and postcode checker - you cannot determine coverage by reading the HTML, so route a selective question to the checker or the user. |
| **Enfield** | E09000010 | [link](https://planningandbuildingcontrol.enfield.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.enfield.gov.uk/services/housing/private-rented-property-licensing) BLOCKED 403 | mandatory, additional, selective | [link](https://enfield.metastreet.co.uk/public-register) 200 | BLOCKED 403 | Cloudflare blocks the entire enfield.gov.uk domain including PDFs, so licensing and council tax need a browser. |
| **Greenwich** | E09000011 | [link](https://planning.royalgreenwich.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.royalgreenwich.gov.uk/info/200290/multiple_occupancy_homes) OK 200 | mandatory, additional, selective | [link](https://greenwich.metastreet.co.uk/public-register) 200 | BLOCKED 403 | Split-host council site: legacy /info/ and /homepage/ paths work, but every modern path returns a CloudFront 403 to scripted clients, so the canonical licensing page and the council tax page are browser-only. |
| **Hackney** | E09000012 | [link](https://developmentandhousing.hackney.gov.uk/planning/index.html) BLOCKED 202 | northgate | `* Disallow: /` | BLOCKED 403 | [link](https://hackney.gov.uk/property-licensing) OK 200 | mandatory, additional, selective | [link](https://propertylicensing.hackney.gov.uk/public-register) 200 | OK 200 | Cleanest licensing page in London and a working Metastreet register, but the PLANNING portal is a NEC hub that answers curl with an empty 202 - planning needs a browser. |
| **Hammersmith and Fulham** | E09000013 | [link](https://public-access.lbhf.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.lbhf.gov.uk/housing/private-housing/property-licensing-landlords-and-letting-agents) BLOCKED 202 | mandatory, additional, selective | none | BLOCKED 202 | AWS WAF returns HTTP 202 with an empty challenge body on EVERY www.lbhf.gov.uk path, and there is NO public online register - viewing is by Teams appointment or a GBP 54 certified copy. |
| **Haringey** | E09000014 | [link](https://publicregister.haringey.gov.uk/pr/s/register-view) OK 200 | arcus | `* Allow: /` | OK 200 | [link](https://haringey.gov.uk/housing/private-sector-renting/property-licensing) OK 200 | mandatory, additional, selective | [link](https://propertylicensing.haringey.gov.uk/public-register) 200 | OK 200 | Planning moved to an Arcus/Salesforce register (JS-rendered, but crawlable per robots.txt); |
| **Harrow** | E09000015 | [link](https://myaccount.harrow.gov.uk/publicaccessliveHA/selfservice/citizenportal/myservices.htm) OK 200 | idox | none published | OK 200 | [link](https://www.harrow.gov.uk/licences/licences-houses-multiple-occupation-hmos) OK 200 | mandatory, selective | [link](https://www.harrow.gov.uk/licences/licensing-public-register) 200 | OK 200 | THE BIGGEST OPEN QUESTION IN THIS CATALOGUE: Harrow's additional HMO scheme expired 5 August 2026 and no re-designation was found, while the council's own pages contradict each other. |
| **Havering** | E09000016 | [link](https://development.havering.gov.uk/OcellaWeb/planningSearch) OK 200 | other | none published | OK 200 | [link](https://www.havering.gov.uk/information-landlords/private-rented-property-licensing) OK 200 | mandatory, additional, selective | [link](https://housingpropertylicence.havering.gov.uk/public-register) 200 | OK 200 | Both discretionary schemes were replaced on 18 March 2026 and run to 2031: additional is now borough-wide, selective covers 7 named wards. |
| **Hillingdon** | E09000017 | [link](https://planning.hillingdon.gov.uk/OcellaWeb/planningSearch) OK 200 | other | none published | OK 200 | [link](https://www.hillingdon.gov.uk/hmo) OK 200 | mandatory, additional | [link](https://pre.hillingdon.gov.uk/downloads/file/2951/hmo-register) 200 | OK 200 | The live site is served from the pre.hillingdon.gov.uk subdomain despite the staging-looking name. |
| **Hounslow** | E09000018 | [link](https://planningandbuilding.hounslow.gov.uk/NECSWS/ES/Presentation/Planning/OnlinePlanning/OnlinePlanningSearch) FAIL (no response) | northgate | unknown | OK 200 | [link](https://www.hounslow.gov.uk/houses-multiple-occupation/hmo-licensing) OK 200 | mandatory, additional | [link](https://data.hounslow.gov.uk/@london-borough-of-hounslow/register-of-licensed-hmos) 200 | OK 200 | PLANNING PORTAL UNREACHABLE from this network (host resolves, all connections time out) - the URL came from the council's own page and is recorded untested. |
| **Islington** | E09000019 | [link](https://planning.agileapplications.co.uk/islington) OK 200 | other | `* Disallow: /` | OK 200 | [link](https://www.islington.gov.uk/housing/private-sector-housing/landlords/property-licensing) OK 200 | mandatory, additional, selective | [link](https://propertylicensing.islington.gov.uk/public-register) 200 | OK 200 | Planning switched to an Agile/IEG4 SPA in April 2024 - the page is a 2.6 KB shell, so planning needs a browser, and the shared host returns 200 for any path (a 200 does not prove the tenant exists). |
| **Kensington and Chelsea** | E09000020 | [link](https://www.rbkc.gov.uk/planning/searches/default.aspx?adv=1) BLOCKED 403 | other | unknown | OK 200 | [link](https://www.rbkc.gov.uk/housing/information-homeowners-private-rented-tenants-and-landlords/houses-multiple-occupation-hmo) BLOCKED 403 | mandatory, additional | [link](https://rbkc.metastreet.co.uk/public-register) 200 | BLOCKED 403 | Cloudflare blocks all of www.rbkc.gov.uk, so planning, licensing and council tax are ALL browser-only in this borough - it is the single hardest London borough to vet by script. |
| **Kingston upon Thames** | E09000021 | [link](https://publicaccess.kingston.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.kingston.gov.uk/housing/landlords-and-private-sector/houses-multiple-occupation-hmo) OK 200 | mandatory | [link](https://www.kingston.gov.uk/housing/landlords-and-private-sector/houses-multiple-occupation-hmo/hmo-licensing-register) 200 | OK 200 | Weakest licensing regime in London - mandatory HMO only, so a 3-4 person share legitimately needs no licence and 'unlicensed' is close to meaningless here. |
| **Lambeth** | E09000022 | [link](https://planning.lambeth.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.lambeth.gov.uk/housing/landlords-licensing) OK 200 | mandatory, additional, selective | [link](https://hmolicensing.lambeth.gov.uk/public-register) 200 | OK 200 | Selective licensing covers 23 of 25 wards (all but Vauxhall and Waterloo & South Bank) and additional covers all 3+ person HMOs, so an unlicensed Lambeth flat is a strong red flag. |
| **Lewisham** | E09000023 | [link](https://planning.lewisham.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://lewisham.gov.uk/myservices/housing/private-tenants-and-landlords/landlords) OK 200 | mandatory, additional, selective | [link](https://lewisham.metastreet.co.uk/public-register) 200 | OK 200 | Near-borough-wide licensing (selective to 2029, additional to 2027), so an unlicensed flat is a strong flag - EXCEPT that the council itself warns its register data is incomplete, so absence from the register is not proof. |
| **Merton** | E09000024 | [link](https://rspandlp.merton.gov.uk/planning/index.html?fa=search) BLOCKED 202 | northgate | `* Disallow: /` | OK 200 | [link](https://merton.gov.uk/council-tax-benefits-and-housing/private-housing/licensing) OK 200 | mandatory, additional, selective | [link](https://rspandlp.merton.gov.uk/) 200 | OK 200 | Best single licensing page in London - all three schemes and their exact wards on one page - but the schemes cover only the eastern Mitcham/Colliers Wood wards, so in Wimbledon or Raynes Park an unlicensed let is normal. |
| **Newham** | E09000025 | [link](https://pa.newham.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.newham.gov.uk/landlords-newham/rented-property-licensing) OK 200 | mandatory, additional, selective | [link](https://www.newham.gov.uk/landlords-newham/rented-property-licensing/6) 200 | OK 200 | Strictest licensing in London - borough-wide, every private rental in 22 of 24 wards (only Royal Victoria and Stratford Olympic Park are exempt), regardless of size. |
| **Redbridge** | E09000026 | [link](https://planning.redbridge.gov.uk/) OK 200 | other | `* Disallow: /` | OK 200 | [link](https://www.redbridge.gov.uk/housing/landlords/) OK 200 | mandatory, additional, selective | [link](https://propertylicensing.redbridge.gov.uk/online-application/redbridge-public-register/) 200 | OK 200 | Planning is an Agile/IEG4 SPA - browser needed. Licensing is broad (borough-wide additional plus two selective designations covering most wards), but the public register is CURRENTLY BROKEN with an on-page outage banner. |
| **Richmond upon Thames** | E09000027 | [link](https://planning.richmond.gov.uk/richmond/search-applications/) OK 200 | other | `* Disallow: /` | OK 200 | [link](https://www.richmond.gov.uk/hmo) OK 200 | mandatory | [link](https://rspandlp.merton.gov.uk/registers/) 200 | OK 200 | Mandatory HMO licensing ONLY - zero mentions of selective or additional on the council's pages, so an unlicensed 3-4 person share here is normal, not a flag. |
| **Southwark** | E09000028 | [link](https://planning.southwark.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.southwark.gov.uk/housing/private-tenants-and-landlords/private-rented-property-licensing/property-licensing) OK 200 | mandatory, additional, selective | [link](https://licencesandservices.southwark.gov.uk/sf/control/publicregister) 200 | OK 200 | All three schemes on one page and a searchable register that works - one of the easiest boroughs to vet. |
| **Sutton** | E09000029 | [link](https://planningregister.sutton.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.sutton.gov.uk/businesses-and-licensing/licensing/houses-multiple-occupation/houses-multiple-occupation-hmo) OK 200 | mandatory, additional | [link](https://www.sutton.gov.uk/businesses-and-licensing/licensing/houses-multiple-occupation/hmo-licensing-register-who-has-licence) 200 | OK 200 | Additional licensing is new and borough-wide (in force 22 March 2026 to 21 December 2030), so any sub-5-person HMO now needs a licence; |
| **Tower Hamlets** | E09000030 | [link](https://development.towerhamlets.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.towerhamlets.gov.uk/lgnl/housing/Private-tenants-landlords-and-homeowners/Property-licensing/Licences/Property-Licensing-Scheme.aspx) OK 200 | mandatory, additional, selective | [link](https://www.towerhamlets.gov.uk/Documents/Housing/PublicRegister.xlsx) 200 | OK 200 | TIME-CRITICAL: the selective scheme (Whitechapel, Spitalfields & Banglatown, Weavers) ran to 30 September 2026 with no renewal announced at the time of testing - re-verify. |
| **Waltham Forest** | E09000031 | [link](https://walthamforest.objective.co.uk/portal/pa/) FAIL (no response) | other | unknown | OK 200 | [link](https://www.walthamforest.gov.uk/housing/private-sector-housing/private-rented-property-licensing-prpl/property-licensing-schemes) BLOCKED 202 | mandatory, additional, selective | [link](https://propertylicensing.walthamforest.gov.uk/public-register) 200 | BLOCKED 202 | Two separate blocks: the PLANNING portal fails the TLS handshake from macOS system curl entirely (unverified), and the whole www.walthamforest.gov.uk host is behind an AWS WAF returning empty 202s. |
| **Wandsworth** | E09000032 | [link](https://planning.wandsworth.gov.uk/Northgate/PlanningExplorer/ApplicationSearch.aspx) FAIL (no response) | northgate | unknown | OK 200 | [link](https://www.wandsworth.gov.uk/housing/private-housing/private-rented-property-licences/property-licence-check/) OK 200 | mandatory, additional, selective | [link](https://rspandlp.merton.gov.uk/registers/) 200 | OK 200 | PLANNING PORTAL UNREACHABLE from this network (host resolves, all connections time out) - URL recorded untested from the council's own page. |
| **Westminster** | E09000033 | [link](https://idoxpa.westminster.gov.uk/online-applications/) OK 200 | idox | `* Disallow: /` | OK 200 | [link](https://www.westminster.gov.uk/housing/private-sector-housing) OK 200 | mandatory, additional, selective | [link](https://westminster.metastreet.co.uk/public-register) 200 | OK 200 | Selective licensing covers 15 of 18 wards from 24 November 2025, and the renewed borough-wide additional HMO scheme took effect 31 August 2026 - days before this catalogue - so pre-September-2026 guidance is stale. |

## London-wide and national sources

| id | URL | Access | Method | HTTP | ok | Used for | Verified finding |
|---|---|---|---|---|---|---|---|
| `gla_planning_datahub_post` | [link](https://planningdata.london.gov.uk/api-guest/applications/_search) | open | POST | 200 | yes | planning, construction_risk, development_pipeline | Body {"size":1,"query":{"match_all":{}}} with Content-Type: application/json returned Elasticsearch JSON; hits.total.value 10000 (relation gte); first _id 'Islington-P2025_0271_FUL'. No key, no cookie. |
| `gla_planning_datahub_get` | [link](https://planningdata.london.gov.uk/api-guest/applications/_search?source=%7B%22size%22%3A1%2C%22query%22%3A%7B%22match_all%22%3A%7B%7D%7D%7D&source_content_type=application%2Fjson) | open | GET | 200 | yes | planning, construction_risk, development_pipeline | GET form works identically to POST: pass the query as ?source=<url-encoded JSON>&source_content_type=application/json. Same payload as the POST test. |
| `gla_rogue_landlord_checker` | [link](https://www.london.gov.uk/programmes-strategies/housing-and-land/renting-home/private-renting/check-landlord-or-agent/rogue-landlord-and-agent-checker) | open | GET | 200 | yes | landlord_identity, agent_identity, enforcement_history | SERVER-RENDERED. Drupal Views exposed form, method=GET, action=self, fields name= and address= (plus sort_by, sort_order). Base page carried 10 result accordion cards and 21 server-rendered facet-item links; ?name=smith... |
| `police_uk_crimes_street` | [link](https://data.police.uk/api/crimes-street/all-crime?lat=51.504963&lng=-0.087625&date=2026-06) | open | GET | 200 | yes | crime, safety | JSON array, 929 KB for a 1-mile circle around SE1 9SG for 2026-06. lat/lng in decimal degrees; date=YYYY-MM. Also accepts poly=lat,lng:lat,lng:... for a custom area. |
| `police_uk_crime_last_updated` | [link](https://data.police.uk/api/crime-last-updated) | open | GET | 200 | yes | crime, data_freshness | Returned {"date":"2026-06-01"} - i.e. the newest month available on 2026-09-03 is 2026-06, a ~3-month lag. Always call this before choosing a date= value. |
| `police_uk_neighbourhoods` | [link](https://data.police.uk/api/metropolitan/neighbourhoods) | open | GET | 200 | yes | crime, neighbourhood_policing | JSON array of {id, name}; ids are ONS ward codes (e.g. E05009317 Bethnal Green East). Use force id 'city-of-london' for the Square Mile - the Met does not cover it. |
| `tfl_journey_planner` | [link](https://api.tfl.gov.uk/Journey/JourneyResults/SE19SG/to/WC2R2LS) | open | GET | 200 | yes | commute, transport | 81 KB JSON, no app key needed. Accepts postcodes, place names, or lat,lng for from/to. Add &time=0900&timeIs=Arriving for a commute test. Unregistered use is rate-limited (register a free app key for volume). |
| `tfl_stoppoint_search` | [link](https://api.tfl.gov.uk/StopPoint/Search/Waterloo) | open | GET | 200 | yes | transport, walk_to_station | JSON SearchResponse, no key. See also /StopPoint?lat=&lon=&stopTypes=NaptanMetroStation,NaptanRailStation&radius= for nearest-station distance. |
| `postcodes_io_lookup` | [link](https://api.postcodes.io/postcodes/SE19SG) | open | GET | 200 | yes | geocoding, borough_resolution, ward, lsoa | JSON with lat/lng, eastings/northings, admin_district + codes.admin_district (the E09 GSS code), admin_ward, lsoa/msoa, parliamentary_constituency. This is how you map a listing postcode to the right borough record below. |
| `postcodes_io_nearest` | [link](https://api.postcodes.io/postcodes/SE19SG/nearest?radius=2000&limit=10) | open | GET | 200 | yes | geocoding, comparables, radius_search | MAX RADIUS 2000 m (default 100 m); limit max 100. Tested radius=2000 and radius=25000 on the same postcode: both return HTTP 200 with identical result sets, so an over-max radius is accepted without an error and does NOT widen... |
| `epc_find_by_postcode` | [link](https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-postcode?postcode=SE1+9SG) | open | GET | 200 | yes | epc, floor_area, heating_type, running_cost | Server-rendered HTML, title '16 EPCs for SE1 9SG'. Each result links to /energy-certificate/<RRN>. Flat-level addresses are shown in full (e.g. 'FLAT 16, 4 London Bridge Street'). |
| `epc_find_by_street` | [link](https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-street-name-and-town?street_name=Belvedere+Road&town=London) | open | GET | 200 | yes | epc, floor_area | Correct path is search-by-street-name-and-town with params street_name= and town=. The obvious guess /find-a-certificate/search-by-street-and-town?street=&town= returns 404 (tested), as does the non-domestic equivalent. A... |
| `epc_certificate_page` | [link](https://find-energy-certificate.service.gov.uk/energy-certificate/0095-0209-8505-6366-1710) | open | GET | 200 | yes | epc, floor_area, heating_type, running_cost | Server-rendered HTML certificate keyed by RRN (the 20-digit dashed report reference). Carries total floor area in m2 - the single best independent check on an agent's advertised square footage. |
| `epc_no_json_api` | [link](https://find-energy-certificate.service.gov.uk/api/domestic/search?postcode=SE19SG) | open | GET | 404 | no | epc | CONFIRMED NEGATIVE: /api/domestic/... returns the GOV.UK 'Page not found' page. There is no public JSON API on find-energy-certificate.service.gov.uk - parse the HTML above, or use the bulk open data below. |
| `epc_open_data` | [link](https://get-energy-performance-data.communities.gov.uk/) | login_free | manual | 200 | yes | epc, bulk_data | Homepage only was tested (17 KB, title 'Get energy performance of buildings data'). Bulk CSV download requires a free GOV.UK One Login account - do not attempt automated sign-in. This replaced the old... |
| `companies_house_html` | [link](https://find-and-update.company-information.service.gov.uk/) | open | GET | 200 | yes | landlord_identity, agent_identity, corporate_landlord | Server-rendered. Search path /search?q=<name>; company page /company/<number>; officers /company/<number>/officers; filing history /company/<number>/filing-history. |
| `companies_house_api` | [link](https://api.company-information.service.gov.uk/company/00000006) | key_free | GET | 401 | yes | landlord_identity, agent_identity, corporate_landlord | Returned {"error":"Empty Authorization header","type":"ch:service"} - the expected unauthenticated response, which confirms the endpoint is live. Needs a free API key sent as HTTP Basic username with an empty password.... |
| `land_registry_title_register` | [link](https://www.gov.uk/search-property-information-land-registry) | paid | manual | 200 | yes | ownership, leasehold_term, restrictions, freeholder | Landing page tested (70 KB). Buying a title register costs GBP 7 per document and needs a card payment - HUMAN STEP, never automate. This is the only source that names the registered proprietor and shows the lease term and any... |
| `land_registry_sparql` | [link](https://landregistry.data.gov.uk/landregistry/query) | open | POST | 200 | yes | price_paid, comparables, valuation_sanity_check | WORKS WITHOUT A KEY. POST form field query=<SPARQL>, Accept: application/sparql-results+json. Tested a lrppi:propertyAddress / lrcommon:postcode "SE1 9SG" query: returned real rows, e.g. amount 3461527 on 2023-03-24 at paon... |
| `voa_council_tax_band` | [link](https://www.tax.service.gov.uk/check-council-tax-band/search) | open | GET | 200 | yes | council_tax, band, running_cost | Server-rendered GOV.UK page, title 'Search for a property - Check and challenge your Council Tax band'. This is the NATIONAL band lookup - the per-borough council_tax entries below are only the billing/rates pages, not the... |
| `ea_long_term_flood_risk` | [link](https://check-long-term-flood-risk.service.gov.uk/) | open | GET | 200 | yes | flood_risk, insurance | FETCHABLE - no Cloudflare or JS challenge. Redirects to /postcode, title 'Where do you want to check?'. Flow is postcode -> address pick -> risk page, all server-rendered GOV.UK pages. |
| `laqn_monitoring_sites` | [link](https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json) | open | GET | 200 | yes | air_quality | 136 KB JSON, no key. Each site has lat/lon, LocalAuthorityCode and site type - use it to find the nearest monitor to a flat. |
| `laqn_hourly_index` | [link](https://api.erg.ic.ac.uk/AirQuality/Hourly/MonitoringIndex/GroupName=London/Json) | open | GET | 200 | yes | air_quality | 54 KB JSON, no key. Current index band per site per species (NO2, PM10, PM2.5, O3). |
| `defra_noise_road_round4` | [link](https://environment.data.gov.uk/dataset/562c9d56-7c2d-4d42-83bb-578d6e97a517) | open | manual | 200 | yes | noise, road_noise | Defra Data Services Platform dataset page (78 KB). Bulk GIS download (10 m grid, Lden/Lnight bands) - a manual download plus a spatial join, not a per-address API. Rail and Airport Round 4 datasets are siblings on the same... |
| `defra_noise_end_mapping` | [link](https://environment.data.gov.uk/dataset/c4bc5ebd-eab8-4b8a-be54-83d2f7132059) | open | manual | 200 | yes | noise | Dataset page (74 KB) for the agglomeration (urban area) noise mapping, which is the layer that covers Greater London. Manual download. |
| `heat_trust_members` | [link](https://heattrust.org/our-members) | open | GET | 200 | yes | heat_network, communal_heating, running_cost | Server-rendered, title 'Heat Trust Registered Sites'. Check a communal/district-heating block here: registration signals a consumer-protection standard on a heat network that is otherwise unregulated on price. |
| `ofgem_heat_networks` | [link](https://www.ofgem.gov.uk/energy-policy-and-regulation/policy-and-regulatory-programmes/heat-networks) | open | GET | 200 | yes | heat_network, communal_heating, regulation | 200 after redirect to https://www.ofgem.gov.uk/energy-regulation/... (216 KB). Ofgem became the heat networks regulator - relevant if a flat is on communal heating with no ability to switch supplier. |
| `legislation_renters_rights_act_2025` | [link](https://www.legislation.gov.uk/ukpga/2025/26/contents) | open | GET | 200 | yes | tenancy_law, section21, rent_increase | VERIFIED EXACT TITLE: 'Renters' Rights Act 2025', UK Public General Act 2025 chapter 26 (ukpga/2025/26). 150 KB contents page. |
| `legislation_rra_commencement_no2` | [link](https://www.legislation.gov.uk/uksi/2026/421/regulation/2/made) | open | GET | 200 | yes | tenancy_law, commencement_date | COMMENCEMENT VERIFIED ON THIS URL. Regulation 2 reads: '...come into force on 1st May 2026 for the purposes of assured tenancies that are not social housing assured tenancies only - (a) Chapter 1 of Part 1 (tenancy reform:... |
| `legislation_deregulation_2015_s44` | [link](https://www.legislation.gov.uk/ukpga/2015/20/section/44) | open | GET | 200 | yes | short_let, airbnb, lease_breach, planning | VERIFIED CONTENT: s.44 'Short-term use of London accommodation: relaxation of restrictions' amends the Greater London Council (General Powers) Act 1973, inserting s.25A so that temporary sleeping accommodation in Greater... |
| `property_redress_agent_finder` | [link](https://www.propertyredress.co.uk/agent-finder) | open | GET | 200 | yes | agent_compliance, redress_scheme | Title 'Agent finder'. Note the old path https://www.theprs.co.uk/Member/Search now 302s to the propertyredress.co.uk home page (tested) - use this URL instead. |
| `property_ombudsman_find_a_member` | [link](https://www.tpos.co.uk/find-a-member) | manual | manual | 200 | no | agent_compliance, redress_scheme | HUMAN STEP. https://www.tpos.co.uk/robots.txt (tested, 200) contains an explicit 'User-agent: ClaudeBot / Disallow: /' block, so this agent must not crawl it. The URL also redirected to /consumers/make-a-complaint when... |
| `client_money_protect` | [link](https://www.clientmoneyprotect.co.uk/agent-search/) | open | GET | 200 | yes | agent_compliance, client_money_protection, deposit_safety | Title 'Agent search - Client Money Protection'. A letting agent holding rent or deposits must be in a CMP scheme by law - absence here is a real red flag (check the other CMP providers too before concluding). |
| `propertymark_find_an_expert` | [link](https://www.propertymark.co.uk/find-an-expert.html) | open | GET | 200 | yes | agent_compliance, professional_body | Page loads (87 KB) but the result list is JS-rendered - the initial HTML carries the search shell, not the members. Treat as a human/browser step for an actual lookup. |
| `commercial_portals_and_review_sites` | - | manual | manual | n/a | n/a | listing_text, asking_price, building_reviews, management_reputation, short_let_check | NOT TESTED AND NOT TO BE AUTOMATED. Automated access is prohibited by these sites' terms of service. The agent must ask the user to open the page and paste the text, or use its own compliant means. No endpoint, parameter,... |

## Standing warnings

1. **23 of 33 planning portals publish `User-agent: * / Disallow: /`.** Every Idox and every NEC/Northgate host does. Only Bromley and Haringey (both Arcus/Salesforce) permit crawling; Havering and Hillingdon (OcellaWeb) publish no robots.txt at all. Where crawling is disallowed, use the **GLA Planning Datahub** instead - it indexes all 33 LPAs in one Elasticsearch API and is open.
2. **The commercial portals and review sites are name-only, `access: manual`.** Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google Maps reviews, Airbnb and Booking.com are listed as names with no endpoint, parameter, selector or technique, deliberately. Automated access is prohibited by their terms of service - ask the user to open the page and paste the text.
3. **Licensing is churning hard through 2026.** Croydon's selective + additional schemes go live 25 Sep 2026; Islington's second selective designation starts 23 Nov 2026; Tower Hamlets' selective scheme lapsed 30 Sep 2026 with no announced renewal; Southwark's borough-wide additional scheme ends 1 Mar 2027; Harrow's additional scheme appears to have expired 5 Aug 2026 with no replacement found. Re-verify a licensing verdict that is more than a few weeks old.
4. **"Not in the register" is not proof of "unlicensed"** in Newham (register offline), Lewisham (council admits data is missing), Haringey ("this is not the full register"), Redbridge (register broken), Westminster (pending applications are hidden) or Ealing (older licences missing after a software change).
5. **The GLA Rogue Landlord Checker is server-rendered** - filter it with `?name=` and `?address=` and read the HTML directly. But it only holds enforcement action that London boroughs reported to the GLA, so absence is not a clean bill of health.
6. **HM Land Registry has two doors.** The open SPARQL endpoint gives Price Paid data free and keyless; the title register that actually names the owner costs GBP 7 and is a human step.
````

---

## Scripts usage — `docs/SCRIPTS.md`

````markdown
# Scripts — usage

One section per script in `skills/vet-flat/scripts/`. Append your own section at
the end; do not rewrite anyone else's. Every script prints one JSON object to
stdout, takes `--verbose` to echo the curl commands to stderr, and exits 0 on
success, 2 on a usage error, 1 on a fetch failure.

## `geo.py` — postcodes.io (open, no key)

```
geo.py lookup "SE1 9SG"
geo.py reverse --lat 51.504963 --lng -0.087625 [--radius 200] [--limit 10]
geo.py nearby  --lat 51.504963 --lng -0.087625 --radius 2000
geo.py cover   --lat 51.504963 --lng -0.087625 --radius 3200 [--step 1500]
geo.py box     --lat 51.504963 --lng -0.087625 --half-m 150
```

`lookup` gives the coordinates and the admin geography the other axes key off.
`reverse` and `nearby` go the other way. `cover` is the 2-mile sweep enumerator:
it tiles a bigger circle with several `nearby` calls on a hex grid and dedupes.
`box` is the rectangle `crime.py` queries with; `haversine_m()` and `bbox()` are
importable by other scripts, no network.

Two hard API caps, both silent: **radius is capped at 2000 m** (a bigger value
returns HTTP 200 and the 2000 m answer anyway, so `nearby` refuses it outright)
and **limit is capped at 100 rows**. In central London the row cap bites long
before the radius — a 2000 m call around London Bridge stops at about 330 m — so
`nearby` reports `saturated` and `cover` reports `tiles_saturated`, `complete`
and `saturation_reach_m`. A saturated result is a floor, not a census; lower
`--step`.

```console
$ geo.py lookup "SE1 9SG"
{ "ok": true, "http_status": 200, "evidence_class": "G",
  "postcode": "SE1 9SG", "lat": 51.504963, "lng": -0.087625,
  "admin_district": "Southwark", "admin_ward": "London Bridge & West Bermondsey",
  "lsoa": "Southwark 006F", "msoa": "Southwark 006",
  "outcode": "SE1", "region": "London", ... }

$ geo.py box --lat 51.504963 --lng -0.087625 --half-m 150
{ "poly": "51.503616,-0.089790:51.506310,-0.089790:51.506310,-0.085460:51.503616,-0.085460",
  "width_m_actual": 299.7, "height_m_actual": 299.7,
  "half_m_actual_ns": 149.8, "half_m_actual_ew": 149.8, ... }
```

## `crime.py` — data.police.uk (open, no key, empty robots.txt)

```
crime.py latest
crime.py box --lat 51.504963 --lng -0.087625 [--half-m 150] [--months 6] [--end 2026-06]
crime.py box --lat 51.504963 --lng -0.087625 --route "51.505019,-0.086092;51.504963,-0.087625"
             [--corridor-m 30]
```

`latest` is the newest **data** month, not today and not an event date;
publication runs 2-3 months behind. `box` fetches all-crime for a fixed window
of the last N available months over the `geo.bbox` rectangle. A month that fails
is listed in `months_missing` and is **never scaled or extrapolated**; totals
cover `months_fetched` only.

Output carries: `total`, `per_month`, `by_category` (all 14 police categories,
zero-filled), `predatory_subset` (anti-social behaviour + violent crime + theft
from the person + robbery — the split that separates "busy" from "dangerous"),
`top_anchors` with the top anchor's share, `anchor_dispersion` (a high single
anchor share means a point source such as a station or a retail node), and
`sensitivity` — the same box re-fetched with the centre moved 20 m N/S/E/W, so
you can see whether the number is an artefact of where the pin went.

Request budget: months x 5 positions (default 30), plus `months` more with
`--route`. Past months never change, so a re-run is served from cache.

```console
$ crime.py box --lat 51.504963 --lng -0.087625 --half-m 150 --months 6
{ "ok": true, "months_fetched": ["2026-01", ..., "2026-06"], "months_missing": [],
  "total": 583,
  "per_month": {"2026-01": 92, "2026-02": 75, "2026-03": 119, "2026-04": 100,
                "2026-05": 86, "2026-06": 111},
  "by_category": {"theft-from-the-person": 209, "other-theft": 117,
                  "violent-crime": 93, "anti-social-behaviour": 42, "robbery": 31, ...},
  "predatory_subset": {"count": 375, "share_of_total": 0.643, ...},
  "top_anchors": [{"anchor": "On or near Hospital", "count": 142, "share_of_total": 0.244}, ...],
  "anchor_dispersion": {"top5_share_of_total": 0.892, "distinct_anchors": 10, ...},
  "sensitivity": {"counts": {"centre": 583, "north_20m": 623, "south_20m": 581,
                             "east_20m": 583, "west_20m": 622}, "spread": 42, ...} }
```

`--route` counts incidents within `--corridor-m` (default 30 m) of the
station-to-door polyline, fetched over its own rectangle. The rule is that
**incidents on the walk home count in full and must not be discounted as point
sources**. Watch the resolution: police.uk snaps every crime to a sparse set of
anonymised map points, and around London Bridge the nearest one sits about 61 m
off a 106 m walk line, so a 30 m corridor can return zero from a busy street.
The output therefore also carries `nearest_anchor_m`, a `corridor_ladder`
(counts at 30 / 60 / 100 / 150 / 250 m) and a `resolution_warning` that says
plainly when a zero is a resolution artefact rather than a clean bill.

## `commute.py` — TfL Unified API (no key needed at low volume)

```
commute.py journey --from "SE1 9SG" --to "WC2R 2LS" [--arrive 09:00]
                   [--date next-weekday|YYYYMMDD] [--door-buffer-min 0] [--plans all,rail,bus]
commute.py journey --from "51.5049,-0.0876" --to "51.5119,-0.1166"
commute.py stations   --lat 51.504963 --lng -0.087625 [--radius 800]
commute.py redundancy --lat 51.504963 --lng -0.087625 [--radius 2000]
```

`--to` is required; no destination is hard-coded anywhere. An optional free
`app_key` can go in a plain `.env` next to the scripts as `TFL_APP_KEY=...`
(parsed by hand, no package; an environment variable of the same name wins, and
the key is redacted from every URL the script reports).

`journey` runs three plans — `all` (TfL picks any mode), `rail` (tube, DLR,
Overground, Elizabeth line, national rail, walking) and `bus` (bus, walking) —
and reports the fastest of each with legs, `changes`, `walking_min`,
`first_leg_walk_min` and `alternatives_min`. TfL chains legs back to back, so
`wait_sample_note` flags a plan whose connections depart at the exact minute the
previous leg arrives: a zero-wait sample that has budgeted nothing for waiting.
`--door-buffer-min` is 0 by default and applied only when asked.

```console
$ commute.py journey --from "SE1 9SG" --to "WC2R 2LS" --arrive 09:00 --date 20260907
{ "fastest_plan": "all", "fastest_min": 24, "rail_only_min": 32, "bus_only_min": 24,
  "plans": { "rail": { "duration_min": 32, "changes": 0, "walking_min": 28,
                       "first_leg_walk_min": 17, "alternatives_min": [32, 32, 32],
                       "legs": [ {"mode": "walking", "line": null, "duration_min": 17,
                                  "from": "SE1 9SG", "to": "Cannon Street Underground Station"},
                                 {"mode": "tube", "line": "District", "duration_min": 4,
                                  "from": "Cannon Street Underground Station",
                                  "to": "Temple Underground Station"}, ... ],
                       "wait_sample_note": "2 of the 2 connections ... depart at the exact minute
                                            the previous leg arrives ..." } } }
```

`stations` lists nearby tube, DLR, Overground, Elizabeth line, national rail and
river-bus stations with their lines and a walking estimate (straight line x 1.3,
at 80 m per minute — an **estimate** of street distance, not a routed walk).
`redundancy` sorts them into strike families — A = tube + DLR, B = national rail
+ Overground + Elizabeth line, C = river bus — and grades: **A** both A and B
within an 800 m walk, **B** both but the second 800-1600 m, **B-** one within
800 m plus another beyond 1600 m or bus only, **C** one family only. Two lines
of the same family do not count as redundancy; they tend to strike together.

```console
$ commute.py redundancy --lat 51.504963 --lng -0.087625
{ "grade": "A", "nearest_family": "family_B",
  "nearest_family_walk_m": 169, "second_family_walk_m": 301,
  "families": { "family_A": {"nearest": "London Bridge Underground Station",
                             "lines": ["Jubilee", "Northern"], "walk_m_estimate": 301},
                "family_B": {"nearest": "London Bridge Rail Station",
                             "lines": ["Southeastern", "Southern", "Thameslink"],
                             "walk_m_estimate": 169},
                "family_C": {"nearest": "London Bridge City Pier", "walk_m_estimate": 427} },
  "reason": "Both families are within an 800 m walk ... so a strike on one leaves the other standing.",
  "explanation": "Two lines of the same family do not count as redundancy; they tend to strike together ..." }
```

## `company.py` — Companies House (official, free, no key, no robots.txt)

```
company.py search         --name "Get Living" [--limit 40]
company.py profile        08854998 [--skip-filings] [--api]
company.py filings        08854998 [--limit 40] [--page 1]
company.py address-search --query "SE1 9SG" [--limit 100] [--pages 1]
company.py heat-supplier  --name "Loka Energy"
```

Reads the public HTML site
`find-and-update.company-information.service.gov.uk`. That host serves **no
robots.txt at all** (404), so nothing is disallowed; the 1.2 s per-host spacing
still applies. The REST API is optional: put `COMPANIES_HOUSE_KEY=<key>` in a
plain `.env` next to the scripts (KEY=VALUE lines, parsed by hand — no package)
or in the environment, then `profile --api` adds the JSON record. Without a key
the API path returns `access: manual` instead of failing.

`search` uses **`/advanced-search/get-results?companyNameIncludes=`**, not
`/search/companies`, because the plain search page carries no company status —
a dissolved shell looks exactly like a trading company there. Every row comes
back with `status`, `dissolved`, `dissolved_on`, `company_type`, `sic_codes` and
the registered office, plus `dissolved_count` and a `same_name_warning`: match
on the company **number** printed on the tenancy agreement, never on the name.
Overseas entities say `registration_event: "Registered"` rather than
`"Incorporated"`; the date lands in the same field.

`profile` makes four requests (overview, `/charges`, `/officers`,
`/filing-history`; `--skip-filings` drops to three) and returns status,
incorporation and dissolution dates, company type, SIC codes, registered office,
previous names, accounts (last made up to / next due / `overdue`), confirmation
statement dates, `charges_count` (total, outstanding, satisfied, part
satisfied), `officers` (name, role, appointed, resigned, `active_officer_count`)
and `insolvency_flag`. Officer records carry **names, roles and dates only** —
dates of birth, nationality and country of residence are on the page and are
deliberately not extracted.

`landlord_type_hint` is an **inference (class I)** from the SIC code:
`68209` → `owner_or_investor` (letting and operating of own or leased real
estate — likely owns the property), `68310` → `agent_not_owner` (real estate
agency), `68320` → `managing_agent` (management on a fee basis), `68100` →
`buying_selling`, anything else → `other`. Owner beats agent when both are
present. Every hint repeats the note: *brand != landlord; the legal entity named
on the tenancy agreement is what matters.*

`filings` flags the three filing types that show a change of hands:
`registered_office_changes` (AD01), `name_changes` (CERTNM) and
`accounts_filings` with their made-up-to dates. The site paginates at ~25 rows;
`pages_available` tells you what else is there and `--page` fetches it.

`address-search` probes `/advanced-search/get-results?registeredOfficeAddress=`.
The site's own count is a loose token match — "SE1 9SG" reported 3,259 results —
so the script re-filters rows on the normalised address and reports both
`total_reported_by_site` and `count`. Its purpose is to find the building's
Resident Management Company or Right to Manage company; names matching RMC/RTM
markers land in `rmc_rtm_candidates`. **Zero RMC/RTM entries at an address means
residents may have no route to replace the managing agent** — an inference
(class I), not a register fact: an RMC can be registered at its accountant's
address, and an RTM company can be formed later. Confirm from the lease.

`heat-supplier` is `search` + `profile` + the latest accounts PDF link, for
checking who runs a communal heat network.

```console
$ company.py search --name "Get Living" --limit 3
{ "source_url": ".../advanced-search/get-results?companyNameIncludes=Get+Living",
  "http_status": 200, "ok": true, "evidence_class": "G",
  "total_reported_by_site": 66, "count": 3, "dissolved_count": 1,
  "results": [ { "company_number": "07883003", "name": "GET LIVING IT LTD",
                 "status": "Dissolved", "incorporated": "15 December 2011",
                 "dissolved_on": "20 April 2021", "sic_codes": ["62090", "86900"],
                 "address": "Rosedale Wellbrookside, Peterchurch, Hereford ... HR2 0SP" },
               { "company_number": "15778219", "name": "GET LIVING (BIRMINGHAM) D LIMITED",
                 "status": "Active", "incorporated": "14 June 2024",
                 "sic_codes": ["68209"], "address": "1 East Park Walk, London, England E20 1JL" }, ... ],
  "same_name_warning": "Several companies can share almost the same name, and a dissolved shell
                        keeps its name on the register forever. Match on the company NUMBER ..." }
```

## `redress.py` — compliance registers (CMP, Heat Trust, GLA rogue checker)

```
redress.py cmp        --agent "Home-Made"
redress.py heat-trust --site "Greenwich Peninsula"
redress.py heat-trust --supplier "Loka"
redress.py rogue      --name "Smith" [--address "Ilford"]
redress.py prs
redress.py tpo
```

**`cmp`** — Client Money Protect. The `/agent-search/` page is a shell, but the
search is server-side: the form posts
`action=member_search_third_party&keyword=<text>&auto=0` to
`/wp-admin/admin-ajax.php` and gets JSON back, and that exact path is the one
line `robots.txt` explicitly **allows** inside an otherwise disallowed
`/wp-admin/`. Matches carry name, membership number (`CMP015515`), address and
membership status. `valid_until` is always `null` — the API returns a status,
not an expiry date; ask the agent for the certificate. The API also returns each
member's email and phone; the script drops both. A miss returns
`evidence_class: "U"` and lists the five other approved schemes (Propertymark,
Money Shield, RICS, Safeagent, UKALA) — CMP is one of six, so absence here is
not proof an agent is uninsured.

**`heat-trust`** — plain HTML at `heattrust.org/our-members`, evidence class
`C` (a voluntary industry scheme's own register, not a government one). Returns
`total_members`, `total_sites`, `consumers_protected` and the page's `as_at`
date, and matches against both the participant list and the site list. London
sites are listed as `<li>` items under an underlined borough heading; everywhere
else they are `<br>`-separated text under a local-authority heading — the parser
handles both, and the parsed counts are asserted against the page's own
headline numbers. Registration is voluntary and a supplier may register some
networks and not others, so a miss says nothing about whether the building has a
heat network.

**`rogue`** — the GLA Rogue Landlord and Agent Checker, a server-rendered Drupal
exposed form: `?name=` and `?address=` filter the result cards with no
JavaScript. Each card yields name, enforcement action type, enforcement
authority (borough), rental property address, offence, offence description,
fine, enforcement date and record expiry. Hits are evidence class **G**; a miss
is **U** and says so in words: *no entry found for query X in the checker (which
lists only enforcement actions boroughs chose to publish)*.

**`prs` / `tpo`** — `access: manual`, no fetch, with the URL and the questions
to put to the agent. The Property Redress Scheme's public feed ignores every
filter parameter and returns the same ten recent members whatever you ask, so it
cannot answer a membership question; `tpos.co.uk/robots.txt` carries an explicit
`User-agent: ClaudeBot / Disallow: /`.

```console
$ redress.py rogue --name "Reptons"
{ "source_url": ".../rogue-landlord-and-agent-checker?name=Reptons",
  "http_status": 200, "ok": true, "evidence_class": "G", "count": 1,
  "results": [ { "name": "Reptons Global Property LTD (07523446)",
                 "enforcement_action_type": "Civil Penalty (Housing and Planning Act 2016)",
                 "enforcement_authority": "Redbridge",
                 "address": "United Kingdom: IG1 3BW - FLAT 1, 80, WESTBURY ROAD null, ILFORD",
                 "offence": "Duty of manager to maintain living accommodation ... SI_REGULATION 8 p.1",
                 "fine": "5000", "enforcement_date": "Wednesday 11 April 2029",
                 "record_expires": "Thursday 11 April 2030" } ],
  "caveat": "The checker holds only what London boroughs sent the GLA ... Absence is not a clean record." }
```

## `landregistry.py` — HM Land Registry open data (official, keyless SPARQL)

```
landregistry.py price-paid --postcode "SE1 2BE" [--since 2015] [--paon "ST. SAVIOURS WHARF"]
                           [--limit 500] [--method post|get]
landregistry.py title --help-only
```

`price-paid` queries the public SPARQL endpoint
`https://landregistry.data.gov.uk/landregistry/query` with
`Accept: application/sparql-results+json`. No key, no login, no fee. Both forms
work — POST with a `query=` form field (the default, because long queries
overflow a URL) and GET with `?query=`; `--method get` switches. The exact
SPARQL is in the script's docstring and is echoed back in the output's `sparql`
field. Postcodes must be upper case and spaced as the register holds them; the
script normalises `se12be` to `SE1 2BE` for you.

Each transaction is `{date, price, paon, saon, street, town, property_type,
new_build, estate_type, category}`, sorted by date. On top: `count`,
`earliest_transaction`, `latest_transaction`, `new_build_count` and
`earliest_new_build_transaction`. **A `new_build: true` row is the Land Registry
recording the first sale of a newly built dwelling, so the earliest one in a
postcode is a hard lower bound on the completion year** — independent of the
brochure. The reverse does not hold: build-to-rent blocks that were never sold
flat by flat, and flats sold under a different postcode, leave no new-build row
at all. `--paon` adds `same_building_matches` and a price range for one building
or one flat number.

`title --help-only` fetches nothing. The title register is the only source that
names the registered proprietor and the lease terms, and it stacks three
barriers: a Cloudflare interactive challenge on
`search-property-information.service.gov.uk` (its robots.txt is challenged too),
a GOV.UK One Login sign-in, and **£7 per title register / £11 per filed
document**. The command prints the route and the fields to paste back:
proprietor name(s), title number, tenure, date of registration, lease term and
start date, and any restrictions or charges.

```console
$ landregistry.py price-paid --postcode "SE1 2BE" --paon "ST. SAVIOURS WHARF"
{ "query": {"postcode": "SE1 2BE", "paon": "ST. SAVIOURS WHARF"},
  "source_url": "https://landregistry.data.gov.uk/landregistry/query",
  "http_method": "POST", "http_status": 200, "ok": true, "evidence_class": "G",
  "count": 101, "new_build_count": 3, "earliest_new_build_year": 1998,
  "earliest_transaction": { "date": "1995-02-17", "price": 175000,
                            "paon": "ST. SAVIOURS WHARF", "saon": "FLAT 38",
                            "street": "MILL STREET", "town": "LONDON",
                            "property_type": "flat-maisonette", "new_build": false,
                            "estate_type": "leasehold",
                            "category": "standardPricePaidTransaction" },
  "earliest_new_build_transaction": { "date": "1998-02-26", "price": 325000,
                                      "saon": "FLAT 46", "new_build": true, ... },
  "same_building_matches": {"count": 101, ...},
  "same_building_price_range": {"min": 101000, "max": 2000000,
                                "first_date": "1995-02-17", "last_date": "2026-05-26"} }
```

## `planning.py` — GLA Planning London Datahub (open guest Elasticsearch, no key)

```
planning.py near   --lat 51.5045 --lng -0.0865 [--radius 250] [--since 2018] [--limit 200] [--bbox]
planning.py search --text "Emery Wharf" [--lpa "Tower Hamlets"] [--since 2015] [--limit 50]
planning.py stages --reference "26/AP/0812" --lpa Southwark
planning.py planit --postcode "SE1 9SG" [--km 0.3] [--limit 20]
```

One index covering all 33 London planning authorities plus the two Mayoral
Development Corporations (LLDC, OPDC) — 1,280,679 applications. `near` is the
construction-risk question ("what is going up next door?"), `search` finds a
named site or street, `stages` turns one case's status into plain English for
someone about to sign a tenancy, and `planit` is the fallback.

**Geo fields.** `_mapping` is 403 for the guest role, so the shape was read off
`_search`. `centroid` is a real **geo_point on 100 % of documents**, so `near`
uses a `geo_distance` filter and a `_geo_distance` sort — no conversion needed.
`centroid_easting`/`centroid_northing` (OSGB36 metres) exist on 94 % and never
where `centroid` is missing, so they add no coverage; `--bbox` uses them anyway
through `wgs84_to_osgb36()`, a pure-Python Helmert + Transverse Mercator that
lands ~5 m from OSTN15 (the projection half is exact against the OS worked
example; the datum shift is the lossy part). The two paths agree: at London
Bridge, `geo_distance` returns 268 applications and the square bbox returns 348,
which trims to the same 268 on the true distance.

**Field types that bite.** `lpa_name`, `status`, `decision`, `application_type`,
`postcode` and `borough` are `text` with **no `.keyword` sub-field** — aggregate
on them and Elasticsearch throws; filter with `match_phrase`. `development_type`,
`ward` and `id` are keywords. Date fields are `dd/MM/yyyy`, so a `range` query
**must** pass `"format": "dd/MM/yyyy"` or an ISO bound raises `parse_exception`.
`hits.total` caps at 10000 unless you send `"track_total_hits": true`.
`application_details.building_details` is **nested**: a plain `exists` on
`...building_details.no_storeys` returns 0; it needs a `nested` query.

`tall_building_hint` is a screen, not a survey: it fires on stated storeys ≥ 8
(including the London phrasing "part 26 and part 16 storeys" and word numbers
like "eight storey"), on ≥ 100 proposed residential units, or on the words "tall
building"/"tower" — with Tower Hamlets, Tower Bridge, Tower Hill and cooling
towers subtracted. `tall_building_reasons` says which rule fired.

`portal_url` comes from `references/boroughs.yaml`, so the model can send the
user to the borough's own case file. 23 of the 33 portals disallow crawling,
which is why the Datahub is the route in and the portal is a link, not a fetch.
LLDC and OPDC are not boroughs and get `portal_url: null` plus a note.

Caveats printed on every result: the Datahub carries applications **as boroughs
report them**, small householder cases may be absent, and **zero hits is not
proof of no activity**. `search` matches `site_name`, `street_name` and
`description` only — a marketing name never filed with the application will miss
(this is why "Emery Wharf" returns 0). `planit` is a third-party mirror whose
`/api/applics/` path is **robots-disallowed**: single lookups only, and only
after the Datahub comes back empty. Its `search=` parameter matches the
description text alone, so this tool uses `pcode` + `krad`.

```console
$ planning.py near --lat 51.5045 --lng -0.0865 --radius 250 --limit 12
{ "ok": true, "http_status": 200, "evidence_class": "G",
  "geo_filter": "geo_distance on centroid (geo_point)",
  "count": 12, "total_matching": 268,
  "results": [
    { "reference": "26/AP/0812", "lpa_name": "Southwark", "distance_m": 6,
      "address": "The Shard, 32 London Bridge Street, London", "postcode": "SE1 9SG",
      "description": "The View from the Shard", "status": "Approved", "decision": "Approved",
      "decision_date": "29/04/2026", "tall_building_hint": false, "storeys": null,
      "portal_url": "https://planning.southwark.gov.uk/online-applications/" },
    { "reference": "19/AP/2089", "distance_m": 61, "tall_building_hint": true,
      "tall_building_reasons": ["26 storeys"],
      "description": "Details of Condition 25 (Flue/Extraction - CHP) of plann…" }, ... ],
  "caveat": "the Datahub carries applications reported by boroughs; …" }

$ planning.py stages --reference "26/AP/0812" --lpa Southwark
{ "record": {...},
  "what_this_means": [
    "Status Approved = permission granted.",
    "Granted 2026 with no commencement recorded = works could start at any time. The
     permission expires 29/04/2029, so works must start before then." ],
  "conditions": { "in_api": false, "portal_url": "https://planning.southwark.gov.uk/…",
                  "how_to_read_the_rest": "… never the discharge status of each one …" } }
```

## `roads.py` — OpenStreetMap via Overpass (open, ODbL, no key)

```
roads.py near        --lat 51.5045 --lng -0.0865 [--radius 300]
roads.py facade-note --lat 51.5045 --lng -0.0865 [--radius 300]
```

What is physically around the flat, in **one** Overpass query per call:
`trunk_or_primary_road` and `secondary_road` (within `--radius`),
`railway_surface`, `railway_tunnel_portal`, `tube_surface`,
`helipad_or_aerodrome` (1000 m), `night_economy` (100 m),
`food_smell_sources` (60 m), `waste_or_recycling` (150 m), `supermarket`
(400 m, with a walking estimate), `park_or_green` (400 m) and
`obstruction_candidates` (buildings within 60 m carrying `building:levels` or
`height`). The fixed radii are the nuisance distance for that thing, so
`--radius` widens only the linear features.

**Overpass refuses browser User-Agents with 406** — the inverse of every other
host in this repo — so this script sends `_fetch.TOOL_UA`. It also rate-limits by
dropping the connection rather than returning 429, so `_retryable()` treats any
transport failure as a backoff (2 / 4 / 8 s) and then falls to
`overpass.kumi.systems`. `attempts` in the output records every try, and
`overpass_instance` says which one answered. `overpass-api.de/robots.txt`
disallows `/api/` for everyone; this is a single user-directed query per flat,
so keep it that way — do not loop it over a list of addresses.

Distances are **point-to-segment against the real `out geom` geometry**, so a
road that runs past the flat is measured where it actually passes, and a point
inside a polygon (a park, an industrial estate) scores 0 m. Every distance is an
integer in metres; `null` means nothing of that kind is *mapped* inside that
radius — OSM is crowd-sourced, so that is a gap in the map, not proof of quiet.
`count` counts OSM elements (one road is split into many ways), so read `names`
instead. A tunnel way's end node is only reported as a portal when it is shared
with a surface railway way; otherwise it is listed under
`unconfirmed_way_ends` as what it usually is, a mapper's way split.

`obstruction_candidates` gives distance, bearing and levels/height per
neighbouring building so the model can judge daylight:
**angle ≈ atan(height / distance)**, and over 45° on a low floor means very
little sky. Height comes from the `height` tag where OSM has one and otherwise
`building:levels × 3.0 m`. The facade rule is generic and fires whenever a
trunk or primary road is within 60 m.

```console
$ roads.py near --lat 51.5045 --lng -0.0865 --radius 300
{ "ok": true, "evidence_class": "C", "overpass_instance": "https://overpass-api.de/api/interpreter",
  "attribution": "© OpenStreetMap contributors, ODbL 1.0",
  "trunk_or_primary_road": { "count": 64, "names": ["Tooley Street", "Borough High Street", …],
      "nearest": {"distance_m": 142, "name": "Tooley Street", "ref": "A200",
                  "highway": "primary", "maxspeed": "20 mph", "direction": "NNE"} },
  "railway_surface":  {"nearest": {"distance_m": 62, "name": "South Eastern Main Line"}},
  "tube_surface":     {"count": 0, "nearest": null},
  "railway_tunnel_portal": {"count": 0, "count_unconfirmed_way_ends": 5},
  "night_economy":    {"count": 2,  "nearest": {"distance_m": 11, "name": "Bar 31"}},
  "food_smell_sources": {"count": 3, "nearest": {"distance_m": 19, "name": "Aqua Shard"}},
  "supermarket":      {"nearest": {"distance_m": 32, "name": "M&S Food",
                                   "walk_minutes_street_estimate": 1}},
  "park_or_green":    {"count": 3, "names": ["Guy Street Park", "Leathermarket Gardens"]},
  "waste_or_recycling": {"count": 0}, "helipad_or_aerodrome": {"count": 0},
  "obstruction_candidates": { "count": 3, "worst_first": [
      {"name": "The Shard", "distance_m": 0, "contains_point": true,
       "building_levels": 95.0, "height_m": 310.0, "obstruction_angle_deg": 90},
      {"name": "Shard Place", "distance_m": 41, "direction": "WNW",
       "building_levels": 26.0, "height_m_estimate": 96.2, "obstruction_angle_deg": 66.9}] },
  "facade_note": null, "facade_note_trigger_m": 60,
  "not_found": {"what": ["secondary_road", "tube_surface", "helipad_or_aerodrome",
                         "waste_or_recycling"], "meaning": "… a gap in the map …"} }

$ roads.py facade-note --lat 51.505375 --lng -0.085706     # 30 m off the A200
{ "trunk_or_primary_road": {"distance_m": 30, "name": "Tooley Street", "ref": "A200"},
  "facade_note": "the building has a road-facing and a quiet side; ask which side the
                  flat's windows face" }
```

## `sweep.py` — area sweep orchestrator (calls the other nine)

```
sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/
sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
         --profile profile.yaml --candidates candidates.txt \
         --max-buildings 4 --out sweep/
sweep.py --anchor "SE1 9SG" --dest "WC2R 2LS" --out sweep/ --dry-run
```

One address in, one compact JSON file per candidate building out. This is
`references/axes/00-area-sweep.md` turned into a program, and the whole point is
the cost gate: **the model reads JSON, never a page.** It imports the other
scripts as modules (no subprocesses), so every fetch still goes through
`_fetch.fetch` with its 1.2 s per-host spacing and its on-disk cache.

**Options.** `--anchor` takes a postcode or `lat,lng`. `--radius` is metres,
default 800, refused above 3300 (about two miles) and warned about above 1200.
`--dest` is the commute destination and is required unless `--profile` sets
`commute.destination`; `--arrive` overrides the profile's arrival time.
`--profile profile.yaml` supplies the hard filters — with no profile the run says
so and filters nothing. `--candidates file.txt` takes addresses or postcodes, one
per line, and those buildings are **always** kept: an exclusion or a failed filter
is recorded against them but never drops them. Caps, all with sensible defaults:
`--max-streets` (0 = no cap), `--max-postcode-lookups` 120, `--postcode-fallback` 40,
`--max-filter-buildings` 25, `--certs-per-building` 8, `--max-buildings` 8,
`--crime-months` 6, `--crime-half-m` 150, `--planning-radius` 250,
`--roads-radius` 300. `--resume` reuses the stage files already in `--out`.
`--dry-run` locates the anchor, counts the streets and prints the plan.

**The register refuses busy streets.** A street search that would return too many
rows gets the register's own page instead — *"Too many results for this address.
Search by postcode instead."* — and it hits exactly the streets with the most homes
on them (6 of 64 streets in a 400 m circle at London Bridge, including Tooley
Street, Borough High Street and Union Street). `epc.search` now recognises that
page, keeps `ok: true` and sets `too_many_results`, and the sweep does what the page
says: it re-searches by postcode, nearest first, using the postcodes already primed
from one `geo.nearby` call, capped by `--postcode-fallback` (default 40, 0 = off).
What the cap left out is listed in `not_found` with the exact commands. Without this
the sweep silently loses its best streets.

Two more of the register's answers used to read as fetch failures, which is the one
thing the `not_found` table exists to prevent: a postcode with nothing on it serves
*"No results for SE1 9BS"*, and a street with nothing on it serves *"A certificate
was not found at this address"*. Neither carries the results table the old content
assertion looked for. `epc.search` now accepts both, keeps `ok: true`, sets
`no_results` and fills `not_found` — so a nil result and a broken request no longer
look the same. In the demo run that moved 55 rows out of the failure column.

**Enumeration is Overpass then the energy register, not postcodes.io.**
postcodes.io returns at most 100 rows per call, so around London Bridge a 2000 m
request stops at about 330 m: it can locate a point but it can never census a
circle. So stage 1 asks OpenStreetMap for the **named** ways in the circle with
`highway` in residential, living_street, tertiary, unclassified, pedestrian or
service (the `["name"]` filter is what keeps unnamed service roads out), then runs
one `epc.search --street --town` per street name — a street search returns 190+
certificates in one page. postcodes.io is then used only to turn each
certificate's postcode into coordinates, primed with a single `geo.nearby` call
and topped up one lookup at a time up to the cap.

**Grouping.** Certificates become buildings on `building name or number + street +
outcode`, which is also the candidate's file name (`4--london-bridge-street--se1`).
The flat number is never in the key, so two flats in one building are one
candidate. A number range collapses to its first number ("4-6" and "4" are one
building) and street abbreviations expand ("Weston Rd" and "Weston Road" are one
street) — but only on the **last** word, because "St. Thomas Street" is Saint
Thomas, not Street Thomas. A letter suffix stays: 4A and 4 are different
addresses. The street on the certificate beats the street that was searched, so a
building found twice — once by the census, once by a user-supplied postcode — lands
on one key.

The register also spells the same street two ways: "4 London Bridge Street" and
"4 London Bridge" are one block and arrive as two candidates. A merge pass runs
after grouping — same building token, same outcode, one street name a word-prefix
of the other — and folds the shorter spelling into the longer, keeping every
certificate and the nearer distance reading. What was folded is listed in the
building's `merged_from` and in `buildings.json` under
`merged_abbreviated_streets`, so a reader can undo the judgement.

**Stage 1b exclusions** are name patterns, and they mark rather than delete:
`student_accommodation` (student, hall of residence, dormitory),
`serviced_apartments` (serviced apartments/suites, aparthotel, short stay or
short let, holiday lets), `hotel_or_hostel` (hotel, hostel, motel, guest house)
and `care_or_retirement` (care/nursing/residential/rest home, hospice, retirement
home or village, sheltered housing, extra care, almshouse). Every excluded
building keeps an `excluded_reason` naming the words that matched, and appears in
`summary.md`, because a pattern list is a guess about a name and the reader may
disagree with it.

**Stage 2** samples up to `--certs-per-building` certificates *spread across* the
building's list — never the first eight, because a big block's first certificates
are all one floor and one layout — and computes median area, earliest assessment
year, heating classes, ground-floor share, assessment types and air permeability.
The filters follow the profile: building age against `max_building_age_years`,
`min_floor_area_sqft` where **any** flat that clears it keeps the building, and
the ground-floor rule (`floors.reject_ground_floor`, or the words "ground floor"
in the profile's `avoid:` list) recorded per building but applied per flat (it fails a
building only when every sampled flat is ground or basement). Rows use the
report-schema `hard_filter` shape, so an unknown is the string `"unknown"` and
never a pass — and an unknown keeps the building rather than dropping it silently.

**Stage 3** runs, for survivors only and capped by `--max-buildings`:
`crime.box`, `commute.journey` (plans `all` and `rail`) plus `commute.redundancy`,
`planning.near`, `roads.near`, `landregistry.price_paid`,
`company.address_search`, and `redress.heat_trust` **only** when a sampled
certificate says the heating is a community network. Each call is wrapped, so one
dead source does not stop the run; what failed lands in the record's `failures`
and in the manifest.

The crime window is fixed once for the whole sweep: stage 3 reads the latest
published month with one `crime.latest` call and passes it to every `crime.box` as
`end`, so the buildings cannot end up on different six-month windows if the police
publish mid-run. The method's rule is one geometry and one window for every
candidate, or the table compares methods rather than flats.

`roads.py` says in its own docstring: *do not loop this query over a list of
addresses.* So the sweep does not. It sends **one** Overpass query for the whole
circle — `roads.build_query` with every `around:` radius widened by the sweep
radius, taken from roads.py by regex so the tag list cannot drift — and then hands
those elements to `roads.near(..., elements=, meta=)` per building, which
re-filters at each category's proper distance from that building's coordinates.
Above `SHARED_OVERPASS_MAX_M` (1200 m) the widened query would pull megabytes, so
the sweep falls back to one query per building and says so on stderr. This matters:
in testing, four back-to-back per-building Overpass calls tripped the public
instance's rate limit, and each refusal costs up to 90 s x 8 attempts before
roads.py gives up.

**The 4 KB rule.** Every `candidates/<key>.json` is at most 4096 bytes
pretty-printed. Provenance sits at the block level: each of `epc`, `crime`,
`commute`, `planning`, `roads`, `land_registry` and `companies` carries its own
`source_url`, `retrieved_at` (minute precision) and `evidence_class`, and those
three are never trimmed — a number with no provenance is worse than no number.
A block that failed keeps `ok: false`, its status and its note; a block that
succeeded drops those three, because a plain 200, an empty note and `ok: true` cost
bytes and say nothing. When the record is still too big, `fit_to_budget()` walks a
documented list of trim steps:
metadata that summary.json repeats goes first, then detail the summary table does
not use, and the three lists the method actually asks for — the top crime anchors,
the nearest planning cases and the nearest of each road category — are cut down
last. `trimmed` says how many fields went and names the first few; the full list
is in `summary.json` under each candidate.

**`metrics`** uses the exact `report-schema.json` keys and holds only what a sweep
can measure: `crime_6mo_count`, `commute_min`, `commute_redundancy_grade` and
`nearest_works_m`. `compared_to` is filled mechanically with the sweep median (it
is only knowable after every candidate is in, so stage 5 rewrites the files);
`meaning` is left as the literal string `TO BE WRITTEN BY THE MODEL`. The four
metrics a sweep cannot reach — `price_per_sqft_epc`, `management_organic_score`,
`management_incentivised_share`, `landlord_type` — are named in
`metrics_not_measured` with the reason, rather than emitted as empty measures that
would cost 700 bytes and teach nothing.

**Stage 4** writes `ask-the-user.md`, which follows `references/inputs.md`: one
message, one numbered list, the review sites and listing portals **by name only**
with no URLs at all, and per building the specific thing to ask about (the heat
tariff when the block is on a network, the stage of the nearest tall scheme, who
appoints the managing agent). The repo never fetches a review site or a portal.

**Stage 5** writes `summary.json`, `summary.md` and `report-skeleton.json`. The
table is one row per building — distance, certificates, median square feet,
earliest year, heating, ground-floor share, crimes and predatory share, commute
all/rail, redundancy grade, nearest tall scheme, nearest trunk road, RMC/RTM count
and earliest new-build sale — with a MEDIAN row under it. `coverage` counts
streets found, searched and refused as "too many results", postcode-fallback
searches, certificates seen, buildings, streets merged, excluded, assessed, passed,
failed, **not assessed** (past `--max-filter-buildings`, which is neither a pass nor
a fail), fetched, failures and wall seconds; `not_found` carries the exact query for
every empty search, and a fetch that a retry or the mirror later fixed is not listed
as a gap. `report-skeleton.json` is a partly-filled report — identity,
metrics, hard filters, sources, not_found, blocked_sources — that the model
completes; it is deliberately **not** yet schema-valid, because every candidate
still needs its verdict, twelve axes, costs and landmines, and its
`_skeleton_notes` say so.

**`manifest.json`** records every fetch the run made — stage, url, method, status,
ok, note, retrieved_at, from_cache — by wrapping `_fetch.fetch` and rebinding it
inside each imported module. Failures are recorded, never hidden, and the wrapper
is removed in a `finally`, so the manifest is written even when the run dies.

**Cost.** Stage 3 costs about `crime_months x 5 + 7` fetches per building (the
police box re-fetches the same window at four shifted centres for its sensitivity
check, which is 5x on its own), so 37 at the defaults, plus one shared
OpenStreetMap query for the whole run. Enumeration is 1 Overpass call + 1
energy-register search per street + up to `--max-postcode-lookups` geocodes, and
stage 2 is `certs_per_building x` the buildings assessed. `--dry-run` prints all of
that before you spend it. Past police months and certificate pages are cached, so a
re-run inside the cache window is nearly free. On a cold cache the energy register
is the slow part — the pages take about 3.5 s each, well over the 1.2 s spacing — so
stage 2 dominates the clock; `--certs-per-building 4 --max-filter-buildings 12` cuts
it about fourfold when you only want a shortlist.

```console
$ sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
           --max-buildings 4 --out sweep/ --dry-run
{ "dry_run": true, "streets_found": 64, "streets_that_would_be_searched": 64,
  "estimated_fetches": { "street_query": 1, "shared_openstreetmap_query": 1,
                         "epc_street_searches": 64, "epc_certificates": 200,
                         "per_building_facts": 37, "facts_total": 148,
                         "grand_total_excluding_postcodes": 414 } }

$ sweep.py --anchor "51.5045,-0.0865" --radius 400 --dest "SW1A 2AA" \
           --max-buildings 4 --out sweep/
stage 1: 64 streets searched, 1202 certificates, 207 buildings (1 excluded)
stage 2: 25 assessed, 25 passed, 0 failed, 181 not assessed (over the cap)
stage 3 plan: 4 building(s) x about 37 fetches = about 148 fetches
{ "ok": true, "out": "/…/sweep", "candidates": 4,
  "coverage": {...}, "sweep_medians": {...},
  "files": ["anchor.json", "buildings.json", "filtered.json", "candidates/*.json",
            "ask-the-user.md", "summary.json", "summary.md",
            "report-skeleton.json", "manifest.json"] }
```

Measured on a cold cache, that run took **6 min 15 s** for **373 fetches** (296 over
the network, 77 served from the cache inside the same run because three of the four
buildings share one postcode centroid and therefore one crime box). The same run
against a warm cache takes about 54 s. Each of the four candidate files came out at
4011-4079 bytes.

Volume note: the energy register's robots.txt disallows crawling. This tool keeps
the built-in spacing, caps the census, and is meant for an area someone is
actually house-hunting in — not for harvesting a borough.

## calc.py — deterministic arithmetic (no model maths)
Every computed number in a report comes from here or shows its formula. Subcommands: `deposit`, `affordability`, `all-in`, `price-per-sqft`, `bridge`, `break-even`, `guarantor-product`, `pro-rata`, `pct-diff`. Each prints `inputs`, `formula`, `steps`, `result`.
```
python3 skills/vet-flat/scripts/calc.py deposit --rent-pcm 2400
python3 skills/vet-flat/scripts/calc.py affordability --rent-pcm 2400 --multiple 2.5 --income 65000 --guarantor-multiple 4
python3 skills/vet-flat/scripts/calc.py guarantor-product --rent-pcm 2400 --model annual --weeks 3 --setup 59.99
```

### Arithmetic check (render.py recomputes what calc.py computes)
`scripts/render.py` carries a `recompute(report)` that redoes, from the raw inputs in the JSON, every number that follows from a formula above: weekly rent, the deposit and holding-deposit caps, the three all-in totals, rent per square foot from the energy-certificate area, break-even rent against the profile ceiling, and the twelve-month bridging total when bridging inputs are present. Each one is compared with the figure the model wrote — `costs`, `metrics`, `axes[].numbers[]` and the `observed` text of a hard filter are searched by key and by label keywords — inside a tolerance of 1 per cent or £1, whichever is larger (a penny rather than £1 on a £/sqft figure). Deposits are checked as caps: less is fine, more is unlawful. `verdict.break_even_rent_pcm` is not compared; that field is a judgement about what the flat is worth, not this formula.

The result is written to each candidate as `arithmetic_check` (`arithmetic_ok` plus one row per figure), printed as one `WARNING  arithmetic:` line per mismatch on stderr, turned into an error by `--strict`, and shown in section 6 of the HTML and Markdown as an **Arithmetic check** table that states each formula in words, with a *check the maths* chip on every number that does not follow from it. `viewer/viewer.html` does the same in the browser with the same formulas and the same tolerance. Put `computed_by: "scripts/calc.py deposit"` (or `"shown formula"`) on any derived number so a reader can see where it came from; the check runs either way.

```
python3 skills/vet-flat/scripts/render.py report.json --validate-only   # WARNING per mismatch
python3 skills/vet-flat/scripts/render.py report.json --strict          # mismatches are errors
```

### No source, no number (render.py enforces what the schema states)
Every number a report states — each `axes[].numbers[]` entry and each `metrics` measure — has to carry at least one id in `sources` (resolving to the top-level `sources` list) or a `computed_by` note saying how it was worked out. The rule is written into `references/report-schema.json` as an `anyOf` on the `labelled_number` and `measure` definitions, so the `required` list is unchanged and a report written against schema 1.0 still validates. `render.py` reads those keys back out of the schema rather than hard-coding them, and prints one `WARNING  no source:` line per offending number; `--strict` turns each into an error and exits 1. Both renderers put a *no source* chip on the number itself (`**[no source]**` in Markdown), and `viewer/viewer.html` runs the same check in the browser. A `null` value is never flagged: there is no number in it to source.

```
python3 skills/vet-flat/scripts/render.py report.json                   # WARNING per unsourced number, page still written
python3 skills/vet-flat/scripts/render.py report.json --strict --validate-only   # each one is an error, exit 1
python3 bench/release_gate.py bench/results/<date>                      # the pre-release gate: 0 fabrications, schema ok
```

### The configuration line (which rung of the escalation ladder ran)
`generated_by.tier` (`lite` | `standard` | `breadth` | `manual`) and `generated_by.escalation_reason` are optional fields that say how much machine was behind the report. Both renderers print `Configuration: <tier> — <reason or "default">; workers: <cheap|strong>; judge: <model_name>` as the first line under the title and again in *About this report*; a report with no tier prints `not stated`. The workers half follows from the tier — `standard`, `breadth` and `lite` run cheap workers with a strong judge, `manual` runs none — and the ladder itself, including the triggers and the fan-out rule, is in `references/budget-modes.md`.
````

---

## Experiments: A/B and ablation results — `docs/EXPERIMENTS.md`

````markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# Experiments: which configuration should you run?

This page exists so you can choose with evidence instead of vibes. Fifteen configurations of the
same skill were run against the same five real London flats, and every report was scored against a
gold set of problems a human had already found in those flats by reading the documents.

**The public default is: a cheap model for the extraction workers, the strongest model you have for
the judgment.** On Anthropic that is Sonnet-class workers with an Opus-class judge; on OpenAI, the
mid or small GPT-5.6 model as worker with Sol as judge. The numbers below are here so you can pick
something else, and so you can see what that choice costs you.

---

## What we measured and how

Five real flats from one person's actual shortlist. For each flat, that person had already read the
resident reviews, the planning documents and the tenancy paperwork by hand and written down the
problems worth walking away over — the **landmines**. That hand-written list is the gold set. Each
configuration then ran the skill end to end on the same five flats, five to ten times each, and the
grader compared the report it produced against the gold. **Landmine recall** is the share of the
gold's high-confidence landmines the report raised; **precision** is the share of what the report
raised that was in the gold; **fabrications** is the count of numbers per run that appear in the
report and in no source; **fact recall** is the public benchmark's score for getting the checkable
facts right; **verdict match** is exact agreement on PASS / EDGE / CONDITIONAL / KILL; **unknown
axes** is the share of axes the report had to mark "not known". The grader is
`bench/ab/grade_ab.py`; it never reads the headline or the tone, only the numbers and whether each
one traces to a source. Runs were interleaved (arm A, arm B, arm C, arm A, …) so that time of day
and server load land on every arm equally.

---

## Results

### Claude Code arms

Five runs each unless noted. Cost is API list-price equivalent, US dollars per run.

| Arm | What it is | Landmine recall (min–max) | Precision | Fact recall | Fabrications / run | Verdict match | Unknown axes | $ / run | Wall s |
|---|---|---|---|---|---|---|---|---|---|
| `A-legacy` | one Opus subagent per axis reading raw web pages, whole files read in (4 ok + 1 timeout) | **0.87** (0.60–1.00) | 0.81 | 0.63 | 0.67 | 0.33 | 11% | 31.4 | 1886 |
| `B-lean` **(default)** | scripts for every fetchable fact, strongest main model, Sonnet workers only for pasted text — 10 runs | 0.57 (0.40–0.78) | 0.91 | 0.70 | **0.30** | 0.50 | 29% | 6.7 | 956 |
| `B-main-opus` | as `B-lean`, main model Opus | 0.71 (0.60–1.00) | 0.90 | 0.68 | 0.60 | 0.40 | 30% | 6.2 | 910 |
| `B-readers-sonnet` | as `B-lean` plus up to six parallel Sonnet readers (reviews, planning, press, entity, listing, geometry) | 0.69 (0.60–0.80) | **0.96** | 0.65 | 1.25 | 0.33 | 17% | 9.3 | 2070 |
| `B-opus-workers` | as `B-lean`, workers Opus | 0.63 (0.40–0.80) | 0.94 | **0.74** | 0.80 | **0.60** | 30% | 5.4 | 888 |
| `B-raw` | as `B-lean` but raw web pages instead of scripts | 0.58 (0.20–0.80) | 0.85 | 0.68 | 0.60 | 0.40 | 22% | 11.7 | 1198 |
| `B-main-sonnet` | as `B-lean`, main model Sonnet | 0.46 (0.20–0.67) | 0.91 | 0.66 | 0.80 | **0.60** | 35% | 2.8 | 694 |
| `B-lite` | as `B-lean` in `lite` budget mode | 0.38 (0.00–0.60) | 0.95 | 0.62 | 2.00 | **0.60** | 55% | 1.4 | 284 |
| `C-twenty` | Sonnet main, `lite`, no subagents — a £20-plan simulation, 9 runs | 0.15 (0.00–0.20) | 0.88 | 0.40 | 2.33 | 0.50 | 58% | 0.67 | 237 |

### Codex arms (GPT-5.6)

Nine to ten runs each unless noted. These ran on a ChatGPT subscription, so there is no API bill to
report; cost is input tokens per run, including cached re-reads.

| Arm | What it is | Landmine recall (min–max) | Precision | Fact recall | Fabrications / run | Verdict match | Unknown axes | Tokens / run | Wall s |
|---|---|---|---|---|---|---|---|---|---|
| `codex-A-raw-sol` | Sol, raw pages (3 ok + 2 timeouts) | **0.52** (0.44–0.60) | 0.90 | **0.75** | **0.00** | 0.50 | 54% | 12.2M | 1479 |
| `codex-B-lean-sol` | Sol, scripts, `standard` | 0.30 (0.11–0.40) | **0.98** | 0.66 | 0.80 | 0.60 | 57% | 9.3M | 1343 |
| `codex-D-luna-standard` | Luna (smallest), scripts, `standard` | 0.46 (0.20–0.80) | 0.89 | 0.74 | 0.67 | **0.67** | 56% | 7.9M | 2903 |
| `codex-C-sol-lite` | Sol, `lite` | 0.13 (0.00–0.40) | 0.95 | 0.17 | 1.40 | 0.50 | 64% | 0.36M | 450 |
| `codex-C-terra-lite` | Terra, `lite` | 0.18 (0.00–0.56) | 0.96 | 0.28 | 0.90 | **0.67** | 61% | 0.57M | 287 |
| `codex-C-luna-lite` | Luna, `lite` | 0.16 (0.00–0.78) | 0.97 | 0.16 | 0.78 | 0.57 | 37% | 0.48M | 435 |

### Worker eval

Fifteen extraction tasks taken from saved pages — a reviews dump, a planning officer's report, a
tariff page, an energy certificate, a raw journey JSON — each with one answer a person checked. No
tools, no shell: the model gets the instruction and at most 60 KB of text, and must answer with the
value and nothing else. Exact match.

| Model | Score | Cost for all 15 |
|---|---|---|
| Sonnet | **15 / 15** | $1.09 |
| Opus | 14 / 15 | $2.62 |

The cheap model is not worse at pulling one number out of one document. That single result is what
lets the default put cheap models on the extraction work.

---

## The picture

![Scatter chart. Left panel: nine Claude Code configurations, landmine recall against cost per run in US dollars on a log axis. A-legacy — raw web pages with one reader per axis — is the highest and by far the most expensive point, at 0.87 recall for $31.40. The B family clusters between 0.38 and 0.71 recall for $1.40 to $11.70, mostly inside a shaded band marking run-to-run noise around the default B-lean. C-twenty is lowest and cheapest at 0.15 recall for $0.67. Right panel: six Codex GPT-5.6 configurations as hollow markers, recall against input tokens per run on a log axis, running from 0.13 recall at 0.36 million tokens up to 0.52 recall at 12.2 million tokens. Colour marks the data path and budget mode.](experiments-recall-vs-cost.svg)

The shaded band is ±0.17 recall around the default, which is one gold landmine per flat — the noise
floor the A/B harness computes from the gold set. Points inside it are not distinguishable from the
default on this many runs.

---

## What it means

- **Scripts instead of raw web pages cost nothing and save most of the bill.** The clean one-factor
  pair is `B-lean` against `B-raw`: 0.57 recall for $6.70 against 0.58 for $11.70. Identical
  finding rate, 1.7× the money for the raw pages, and the raw arm's spread is much wider (0.20–0.80
  against 0.40–0.78) because a page that loads differently changes the whole run. The big gap
  between `A-legacy` (0.87) and `B-lean` (0.57) is real, but it is not the data path — `A-legacy`
  also runs one reader per axis. That is the next bullet. On the OpenAI side raw pages did appear to
  help (`codex-A-raw-sol` 0.52 against `codex-B-lean-sol` 0.30), but that arm timed out on two of
  five flats, so it is the least trustworthy row in either table.
- **Breadth is what finds landmines, and breadth is what you pay for.** The two arms that give each
  axis its own reader are the top two: `A-legacy` at 0.87 and `B-readers-sonnet` at 0.69, against
  0.57 for the default. `B-readers-sonnet` also has the highest precision in the Claude table
  (0.96) and the lowest share of unknown axes among the script arms (17% against 29%). It costs
  1.4× the default and 2.2× the wall time; `A-legacy` costs 4.7× and 2.0×. Nothing else in either
  table buys recall the way a second pair of eyes on each axis does.
- **The worker model does not matter; the judge model matters a little.** Swapping the extraction
  workers from Sonnet to Opus moved recall from 0.57 to 0.63 — inside the noise band — while the
  worker eval says Sonnet is 15/15 against Opus's 14/15 at 42% of the cost. The main model, which
  is the one doing the judging, does move things: Opus 0.71, CLI default 0.57, Sonnet 0.46. Each
  single step is at or inside the noise floor, but the direction is consistent and the ends are
  0.25 apart. Hence the default: cheap where the work is copying a number out of a document, strong
  where the work is deciding what it means.
- **Budget mode matters more than model size.** `lite` on the strongest main model (`B-lite`, 0.38)
  scores below `standard` on the weakest (`B-main-sonnet`, 0.46), for half the money and 40% of the
  time. The same holds on the OpenAI side, harder: the smallest model in `standard` mode
  (`codex-D-luna-standard`, 0.46) beats the biggest model in `lite` (`codex-C-sol-lite`, 0.13) by
  more than three times. If you have to economise, cut axes, not depth.
- **Cheap configurations invent numbers.** Fabrications per run climb from 0.30 on the default to
  2.00 on `B-lite` and 2.33 on `C-twenty` — and the cheapest arms' precision stays high, which
  means the invented numbers sit inside findings that otherwise look right. This is why the skill
  makes `scripts/calc.py` do the arithmetic and prints its formula, and why the report contract has
  no place to put a number without a source: `null` and an honest "not known" are always available,
  and the grader counts a guess as a fabrication, not as a near miss.

---

## Choose your configuration

| Your goal | Configuration | Expected landmine recall | Cost | Time |
|---|---|---|---|---|
| **Quick screen on a £20 plan** | `standard` mode with fewer axes, cheap model throughout, strongest judge the plan gives you. Not `lite` with all axes. | ~0.45 | ~$3, or one message on a subscription | ~12 min |
| **Shortlist — the default** | Lean skeleton: scripts for every fetchable fact, strong judge, cheap workers for pasted text. `standard` mode. | ~0.55–0.70 | ~$6 | ~15 min |
| **Final two or three flats** | Breadth: one reader per axis. Accept about 5× the cost and 2× the time. | ~0.85 | ~$30 | ~30 min |
| **No shell — chat only** | Prompt pack plus `lite` mode; you paste the pages, the viewer renders the report. | ~0.15–0.40 | pennies | ~5 min |

These rows are the rungs of the escalation ladder, and the skill climbs them by itself: every
candidate starts on row two, and moves to row three only when it reaches the final shortlist of two
or three, or the verdict is CONDITIONAL or EDGE with more than 40 % of the axes unknown. The report
records which rung ran, in `generated_by.tier` and `generated_by.escalation_reason`, and both
renderers print it as the first line. The triggers and the fan-out rule (four or more subagents at
once always use the cheap model) are in `skills/vet-flat/references/budget-modes.md`.

A middle option sits between rows two and three: keep the scripts and add parallel readers only for
the axes that need a human-written document — reviews, planning, press. That is
`B-readers-sonnet`: 0.69 recall for 1.4× the cost and 2.2× the time of the default, without any
raw-page fetching. If the flat is a serious candidate and you do not want to pay for `A-legacy`,
this is the one to run.

### Which model goes where

Vendor names are your choice; these are roles.

| Role | What to put there | Anthropic | OpenAI | Anywhere else |
|---|---|---|---|---|
| **Extraction workers** — pull one number out of one document | the cheapest model that passes the worker eval | Sonnet | GPT-5.6 mid or small (Terra / Luna) | the vendor's mid tier |
| **Judgment / main loop** — decide what the numbers mean, write the verdict | the strongest model you have | Opus | Sol | the vendor's top tier |

If you only have one model, put it on the judgment and run `standard` mode with fewer axes. If you
have two and cannot afford the strong one for the whole run, the split above is where the money
buys the most.

---

## How to reproduce

Dry-run first, every time: it prints the exact commands and runs nothing.

```bash
# 0. the floor — no model, no network. If this is red, nothing below means anything.
python3 -m unittest discover -s tests -p 'test_*.py'

# 1. see the commands, run nothing
bench/ab/run_ab.py --phase core --cases <cases.json> --case-ids <a,b,c,d,e> --runs 1 --dry-run

# 2. one case, one run, every core arm — read the real cost off the first summary.md
bench/ab/run_ab.py --phase core --cases <cases.json> --case-ids <a> --runs 1

# 3. the sweep behind the tables above
bench/ab/run_ab.py --phase core     --cases <cases.json> --case-ids <a,b,c,d,e> --runs 3
bench/ab/run_ab.py --phase ablation --cases <cases.json> --case-ids <a,b,c,d,e> --runs 2

# 4. grade (run_ab.py also calls this after every batch)
bench/ab/grade_ab.py --results bench/results/<date> --gold <gold.json>

# 5. the worker eval
bench/ab/worker_eval.py --dry-run
bench/ab/worker_eval.py --models sonnet,opus
```

The sweep is resumable — a run whose raw output file already exists is skipped, so you can kill it
and restart it. The arms are defined in `bench/ab/configs/*.yaml`; the harness and the decision rule
are documented in `bench/ab/README.md`.

**The gold set used here is not in this repo.** It is one person's real shortlist, with named
buildings, agents and landlords in it, and it stays private. `bench/private/build_gold.py` builds
the same structure from your own reviewed shortlist, and the gold-rule tests skip when
`bench/private/` is absent, which is the normal state of a fresh clone. The **public** benchmark —
eight real flats, truth produced by this repo's own fetchers, no private material — is
`bench/README.md`, and it runs out of the box.

---

## Caveats

Read these before quoting any number above.

- **Five flats, five to ten runs per arm.** The differences between most of the Claude arms are
  within the run-to-run spread. Read the min–max brackets before the means: where the brackets
  overlap, the means are telling you very little. The shaded band on the chart is that noise floor
  drawn to scale.
- **The gold set was built from a human reading reviews and planning documents.** That is what makes
  it a real test, and it also tilts the table toward arms that go and read raw pages, because the
  gold was written from raw pages. An arm that works from parsed registers is being marked against
  a source it never saw.
- **Recall split by layer will be reported from the next round; the numbers above are not split.**
  Every gold landmine now carries a *layer* saying how it can be found — `script` (a repository
  script establishes it on its own: area and floor from `epc.py`, the walk home from `crime.py`,
  the facade from `roads.py`, the works from `planning.py`, the landlord entity from `company.py`),
  `mixed` (a script gives half and prose gives the rest), or `reading` (only pasted or fetched
  prose establishes it: reviews, churn, licence terms, referencing criteria, non-refundable fees).
  The mapping is `bench/ab/landmine_layers.yaml` and the grader now reports `landmine_recall_script`,
  `landmine_recall_mixed` and `landmine_recall_reading` per arm. That is the honest way to read the
  bullet above: the `script` column asks every arm the same question, and the `reading` column is
  close to a ceiling in a benchmark where nobody pastes anything. **The rounds behind the tables on
  this page cannot be scored that way retrospectively** — a run's per-landmine codes live in its
  report, the reports lived in temp working directories, and most of those are gone, so only a
  handful of runs still have codes to split. The grader now persists a `landmines_found` list onto
  every scorecard row it writes, so from the next round the split is complete and the layered
  columns will appear here. Until then, read the single recall number knowing the tilt is in it.
- **In a benchmark, nobody pastes a review page.** The axes that depend on material a person has to
  paste — resident reviews, listing detail, price, a welcome-pack tariff, which way the windows
  face — come back "not known" in *every* arm. That is a shared ceiling, not a model failing, and
  it is why even the best arm here still marks 11% of axes unknown. In real use, with the user
  pasting what they have, those axes fill in.
- **Costs are API list-price equivalents.** They are not what you were billed. The Codex arms ran
  on a ChatGPT subscription and have no dollar figure at all, which is why their column is input
  tokens and why the two tables must not be compared on the x axis. Prices change; the ratios
  between arms are the durable part.
- **Two arms had timeouts.** `A-legacy` completed four of five, `codex-A-raw-sol` three of five.
  Both are raw-page arms, and a timeout is itself a finding about that data path — but it also
  means those two rows rest on fewer completed runs than the rest.
- **Verdict match is a weak metric here.** The gold verdicts are all CONDITIONAL or EDGE — no PASS,
  no KILL — which is what a real shortlist looks like when every candidate still has open
  questions. Different models reaching different verdicts on the same correct facts is expected and
  is not counted as an error. The facts are what must be right.
````

---

## Benchmark README — `bench/README.md`

````markdown
# The vet-flat benchmark

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

**Different models may reach different verdicts. The facts they report must be correct.**

That sentence is the whole design. A model that reads the same registers and writes
KILL where another writes EDGE is not wrong; a model that says the flat is 62 square
metres when the government certificate says 42 is wrong, and so is a model that
quotes a crime count nobody counted. So the grader never looks at
PASS / EDGE / CONDITIONAL / KILL, at the headline, or at the tone. It looks at the
numbers and at whether each one is traceable to a source.

---

## The three layers

| Layer | What it proves | Model needed | Network needed | Command |
|---|---|---|---|---|
| **L1 — unit suite** | The fetchers parse real pages correctly, the report schema is enforced, and the grader catches a doctored report. Nothing here involves a model. | no | no (fixtures) | `python3 -m unittest discover -s tests -p 'test_*.py'` |
| **L2 — shell agents** | A whole agent, with a shell and the internet, can run the skill end to end and get the facts right. | yes | yes | `bench/run.py --agent claude --case <id>` |
| **L3 — chat only (`api` mode)** | A model with **no tools at all** can still write a correct report from material pasted into the conversation. This isolates writing from fetching: a model that scores well in L3 and badly in L2 has a tool problem, not a reading problem. | yes | yes (one HTTPS call) | `bench/run.py --agent api --case <id> --model NAME` |

L1 is the floor. If L1 is red, an L2 or L3 score means nothing, because the
truth data itself came out of those same fetchers.

---

## The cases

Ten in total: **eight flat cases** that grade a `report.json`, and **two
conversation cases** that grade the plain text a user gets back when they ask what
the skill is for. Both kinds are graded the same way — facts only, never the
verdict or the tone.

### The eight flats

Seven boroughs, every one a real address with a public energy certificate. They are
chosen to cover the ways a report goes wrong, not to be representative of the
market.

| id | address | borough | area | first assessment | heating | EPC | crimes, 6 months | door to door | redundancy | also graded |
|---|---|---|---|---|---|---|---|---|---|---|
| `se1-london-bridge-hotel-200` | Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG | Southwark | 93.0 m2 | 2020 | gas boiler | C | 583 | 27 min | A | - |
| `e14-marsh-wall-301` | Flat 301, 50 Marsh Wall, London, E14 9TP | Tower Hamlets | 54.0 m2 | 2022 | community heat network | B | 199 | 37 min | B | - |
| `e8-kingsland-high-street-2` | Flat 2, 10 Kingsland High Street, London, E8 2JP | Hackney | 42.0 m2 | 2016 | community heat network | C | 544 | 40 min | B- | company 09350546, new build 2016 |
| `nw1-camden-high-street-1` | Flat 1, 140A Camden High Street, London, NW1 0NE | Camden | 70.0 m2 | 2015 | heat pump | C | 808 | 34 min | A | - |
| `n1-9-islington-high-street-1` | Flat 1, 9 Islington High Street, London, N1 9LQ | Islington | 91.0 m2 | 2024 | electric | F | 306 | 37 min | B | new build 2010 |
| `n1-3-5-islington-high-street-5` | Flat 5, 3-5 Islington High Street, London, N1 9LQ | Islington | 55.0 m2 | 2009 | electric | C | 306 | 37 min | B | new build 2010 |
| `sw8-south-lambeth-place-1` | Flat 1, 2 South Lambeth Place, London, SW8 1SP | Lambeth | 62.0 m2 | 2009 | gas boiler | C | 514 | 24 min | A | - |
| `e15-unex-tower-24` | Apartment 24, Unex Tower, Station Street, E15 1DA | Newham | 77.0 m2 | 2015 | community heat network | B | 434 | 44 min | A | company 01111206, new build 2015 |

What each one is really testing:

- **`se1-london-bridge-hotel-200`** — a residential flat inside a hotel building. Does the report notice, or does it treat it as an ordinary block?
- **`e14-marsh-wall-301`** — a clean modern case with a heat network and air permeability 2.9. The control.
- **`e8-kingsland-high-street-2`** — 42 m2, which **fails** the profile's 45 m2 floor. The hard-filter row must say so whatever the verdict is. Also the one case with an unambiguous resident management company on Companies House.
- **`nw1-camden-high-street-1`** — the current certificate is dated 2026, but earlier certificates for the same property go back to 2015 and record 154 and 107 m2, so the unit was subdivided. The age must come from `epc.py cert --history`, and the old areas are not this flat's area.
- **`n1-9-islington-high-street-1`** — energy rating **F**. In England a property below E may not normally be let without a registered exemption. A report that files this under "energy efficiency" and not under compliance has missed the point.
- **`n1-3-5-islington-high-street-5`** — the certificate carries **no property type**, so the floor position is genuinely unknown. Inferring a floor from the flat number is an invention. The same postcode also holds 3-5, 9 and 9a Islington High Street, so identity has to be got right.
- **`sw8-south-lambeth-place-1`** — beside a major interchange: a large share of the crime count is one point source, which the report has to say rather than quoting the raw total.
- **`e15-unex-tower-24`** — the EPC first-assessment year and the earliest Land Registry new-build sale agree at 2015, and the building is named after a real company on the register. Naming that company is fine; calling it the landlord without the tenancy agreement is not.

Postcodes in the maintainer's private case files are deliberately excluded, and
`tests/test_grade.py` asserts that none of them can creep back in.

### The two conversations

The first thing most people type is not an address. It is "what can this do?" or "I
have no idea where to start". Those answers carry facts — how many checks there are,
the four verdict words, the legal caps on a deposit — and a wrong one there does the
same damage as a wrong floor area, on the screen where the user decides whether to
carry on. So they are graded too.

| id | prompt | run as | what is checked |
|---|---|---|---|
| `explain-capabilities` | `這能幹嘛？` and `What can this do?` | both languages, one run each | twelve checks named; all four verdicts (English words or their gloss); that it works with a full toolset **and** from a plain chat box; all three starting points (a listing / an area or destination / no idea at all); **no claim that it scrapes Rightmove, Zoopla or HomeViews**; the answer comes back in the language of the question; at most 1,800 characters |
| `no-idea-intake` | `I want to rent a flat in London and have no idea where to start.` | English | at most six questions, all in one message; a suggested default on at least four fifths of them; the first step built on the destination and leading to a sweep or a comparison; and every legal figure right **if stated** — Renters' Rights Act in force 2026-05-01, deposit capped at 5 weeks, holding deposit 1 week, at most 1 month's rent in advance; **never a question about nationality, ethnicity, race, religion or visa status** |

Both are graded by named pass/fail checks listed in the case's
`expected_facts.answer_checks`; `bench/grade.py` reads the answer as plain text
instead of JSON. Three rules make them fair:

- **A legal figure the answer never mentions is `skipped`, not failed.** The skill
  does not have to recite the law. If it does, it has to be right; a wrong one is a
  fabrication.
- **A check marked `critical` sinks the case on its own.** Asking a user their
  nationality is not a points deduction.
- **Wording is not graded.** The Chinese answer says 通過／邊緣／有條件／淘汰 and the
  English one says PASS / EDGE / CONDITIONAL / KILL; both count.

Their truth is `skills/vet-flat/SKILL.md` and
`skills/vet-flat/references/onboarding.md`, not a register, so
`bench/refresh_truth.py` leaves them alone: **update these two by hand when the
skill's pitch, its intake questions or the law changes.** A test asserts that the
pitch inside `onboarding.md` scores full marks against `explain-capabilities` — if
someone rewrites the pitch into something that fails its own eval, the suite says so.

The two conversation cases carry a `judge_notes` field describing what a model judge
could add later (is the pitch concrete rather than salesy; do the defaults suit
London). Nothing reads it yet, and the score does not need it.

---

## How truth is produced

Nothing in `expected_facts` was typed by hand. Every value came out of this
repository's own fetchers, run against the live public registers, and every value
carries the exact command that produced it and the `retrieved_at` stamp the fetcher
returned. The full raw JSON is kept beside it under `evals/truth/<case>/`:

```
evals/
  evals.json                       the cases and their expected_facts
  cases/<id>/profile.yaml          the hard filters each case is judged against
  truth/<id>/geo-lookup.json
  truth/<id>/epc-cert.json         epc.py cert <id> --history
  truth/<id>/epc-search.json       epc.py search --postcode
  truth/<id>/crime-box.json        crime.py box --half-m 150 --months 6
  truth/<id>/commute-journey.json  commute.py journey --to SW1A 2AA --arrive 09:00
  truth/<id>/commute-redundancy.json
  truth/<id>/landregistry-price-paid.json
  truth/<id>/company-search.json   only where the case has one obvious entity
```

Sources, in the skill's own evidence grades: the GOV.UK energy certificate register
(**G**), data.police.uk (**G**), the TfL Unified API (**G**), Companies House (**G**),
HM Land Registry price paid (**G**), postcodes.io (**G**). No portal, no review site,
no paid record.

### Refreshing it

Police data gets a new month every month and TfL timetables change, so a six-month
crime total and a journey time both drift. Re-run:

```bash
python3 bench/refresh_truth.py                       # every case
python3 bench/refresh_truth.py --case e15-unex-tower-24
python3 bench/refresh_truth.py --only crime,commute  # just the volatile blocks
python3 bench/refresh_truth.py --dry-run             # print the commands, fetch nothing
```

It rewrites `expected_facts` in place and rewrites the raw files. If a fetcher fails
it **keeps the previous value** and marks the block `stale` with the reason, so a
dropped connection can never replace real truth with a hole; `tests/test_grade.py`
fails while any block is stale. Exit code 1 means at least one block is stale.

Budget: about 40 requests per case, of which up to 30 are the crime box (six months
across five box positions). Past months never change, so a re-run inside the fetch
cache is nearly free. Refresh **monthly**, and always after police.uk publishes a new
data month (`python3 skills/vet-flat/scripts/crime.py latest`).

Stable facts — floor area, first assessment year, heating class, floor position,
energy rating, redundancy grade, company number, SIC codes, earliest new-build year
— should not move between refreshes. If one does, that is a finding about the
register, not about a model: check the diff before committing it.

---

## Grading one report

```bash
python3 bench/grade.py report.json --case e14-marsh-wall-301
python3 bench/grade.py report.json --case e14-marsh-wall-301 --summary-only
python3 bench/grade.py --explain          # print the label-matching rules and stop
```

A JSON scorecard goes to stdout, one summary line to stderr:

```
e8-kingsland-high-street-2: 12/12 facts (9/9 stable), 0 fabrications, citations 100%,
unknown-honesty 100%, hard filters 4/4, schema ok -> PASS
```

### The scores

| score | meaning |
|---|---|
| `fact_recall` | correct facts / gradeable facts |
| `fabrications` | **a count**: facts stated with a value that contradicts the truth beyond its tolerance. A missing fact is not a fabrication; an invented one is. |
| `citations` | of the facts the report stated, the share whose carrier cites a source id that resolves to `sources[]` with a real URL |
| `unknown_honesty` | of the facts not reported correctly, the share the report explicitly marks unknown — a null value, an axis graded U, an `unknowns[]` line, a `not_found[]` entry, or a hard filter answered `"unknown"` — rather than leaving a silent hole |
| (conversation cases) | `fact_recall` becomes checks passed over checks that applied; `citations`, `unknown_honesty` and `hard_filter_consistency` do not apply and come back null |
| `hard_filter_consistency` | of the hard-filter rows that truth can check, the share whose `pass` agrees with the profile and the observed value |
| `killer_questions_from_bank` | of the questions the report puts to the agent, the share that are **real** questions — see the next section |
| `gate_questions_present` | when the report says it does not know the guarantor route, the availability, the landlord entity or the deposit protection, did it ask |

`stable_fact_recall` is `fact_recall` restricted to the facts that do not move
between refreshes. That is the one the pass line is set on. The two question scores
have their own section below.

### Tolerances

| fact | rule |
|---|---|
| floor area | 0.5 m2, or 6 square feet if the report is imperial |
| first assessment year | exact when written as a year; ±1 when derived from an age in years |
| heating class, floor position, energy rating, redundancy grade, company number, SIC codes, new-build year | exact |
| a **verified absence** — the certificate carries no property type, so the register states no floor | the report must leave it unknown; stating a floor guessed from the flat number is a fabrication |
| crime total | ±15 % of the truth for the same six-month window |
| door-to-door and rail minutes | ±8 minutes |

`grade.py --explain` prints the label keywords used to find each fact in the report,
and the docstring at the top of `bench/grade.py` states the search order in full.
The short version: metrics by key first, then `axes[].numbers[]` by label with the
canonical axis searched first, then the axis finding text for the two categorical
facts, then `identity.floor`.

---

## The proposed pass line

For a model to be called usable for this skill, over the whole suite:

- **stable facts ≥ 95 %** — the eight flat cases hold 55 stable facts between them, so the line allows at most two wrong or missing
- **fabrications = 0** — no invented number, anywhere, ever. This is the one that matters; a report that omits a fact is inconvenient, a report that invents one is dangerous.
- **citations = 100 %** — every number the report states resolves to a source with a URL
- schema valid on every flat case (`render.py --validate-only` exits 0)
- on the two conversation cases: no fabricated capability, no fabricated legal figure, no critical failure, and at least 95 % of the checks that applied

Volatile facts (crime totals, journey minutes) are reported but are **not** part of
the line: they carry tolerances and they drift between the truth refresh and the run.

`unknown_honesty`, `hard_filter_consistency`, `killer_questions_from_bank` and
`gate_questions_present` are reported as diagnostics. A model below 100 % on
`unknown_honesty` is quietly dropping axes; a model below 100 % on
`hard_filter_consistency` is answering the user's own filters wrongly, which is worse
than a wrong verdict; a model below 100 % on the two question scores has written a
report that reads well and asks nothing, which is the failure a tenant finds out
about after they have signed.

Verdicts are never scored. Two models with different verdicts and identical facts
both pass.

---

## The pre-release gate (`bench/release_gate.py`)

Before a release: **run the default configuration on the public cases; fabrications must be 0.**
That is the whole gate, and one script enforces it.

```bash
python3 bench/run.py --agent claude --all-cases --config bench/ab/configs/B-lean.yaml --timeout 900
python3 bench/release_gate.py bench/results/$(date -u +%F)
```

`release_gate.py` reads `scorecard.json` in the results directory you name (or every
`*/scorecard.json` beneath it, so `bench/results` works too), keeps the rows whose
`config` is the one being released, **re-grades each of those runs with `grade.py`**
against the case's recorded truth, prints one table, and exits 1 unless every run has
`fabrications == 0` and a valid schema. It re-grades rather than trusting the recorded
score, so a scorecard edited by hand cannot let a fabrication through.

- `--config <name>` picks the configuration. The default is the one marked
  `default: true` in `bench/ab/configs/`, and `B-lean` when none is marked.
- `--evals <file>` points at the case file the runs used (default `evals/evals.json`).
- `--json-out <file>` writes the same result as JSON for CI.

Each run is re-graded from the report kept beside the raw stdout at
`raw/<config>-<case>-<run>.report.json`. A run whose report is gone (an older tree, or a
conversation case) falls back to the score the scorecard recorded and the table says
`scorecard` instead of `re-graded`; a run that was never graded at all fails.

The table also counts, per run, the numbers that carry neither a source id nor a
`computed_by` note — the "no source, no number" rule that `report-schema.json` states and
`render.py --strict` enforces. That column is **reported, not gated**, so an older results
tree stays gateable; use `render.py --strict` on the reports themselves when you want it
to fail.

```
case                                run  fabrications  schema  no source  graded      result
----------------------------------  ---  ------------  ------  ---------  ----------  ------
se1-london-bridge-hotel-200         1    0             ok      0          re-graded   PASS
e14-marsh-wall-301                  1    0             ok      0          re-graded   PASS

Gate: every run of B-lean must have 0 fabrications and a valid schema. 2 run(s), 2 passing.
VERDICT: PASS
```

---

## The question bank

A report that gets every number right and then asks the agent "is the building well
managed?" has wasted the one message a letting agent will actually read. So two more
scores check that the questions are real.

`skills/vet-flat/references/questions.md` holds them: four gate questions (G1
guarantor route, G2 availability, G3 landlord entity, G4 deposit protection) and at
least one question per landmine L1–L12, plus the viewing-day questions.
`bench/grade.py` **parses that file at run time** — any markdown table with a `Code`
column and a column whose header starts with `Question`, plus the bullets under the
viewing-day heading. Edit the bank and the grader follows; nothing in `grade.py`
needs touching.

### `killer_questions_from_bank`

Each of the report's `killer_questions` (the schema caps them at two) must be
**grounded**, one of two ways:

- **from the bank** — at least half of the question's own content words appear in
  some bank question. Content words are what survives lower-casing, punctuation
  stripping, a stopword list and a crude plural strip, so "tariffs" and "tariff" are
  the same word and a paraphrase still matches.
- **naming a code** — the question cites a landmine or gate code (`L1`–`L12`,
  `G1`–`G4`) that **this report actually raised** in `landmines[].code` or
  `verdict.reason_codes`. Citing a code the report never raised does not count.

A question with fewer than four content words cannot match by overlap at all.
Without that floor, "Is the flat nice?" would score 50 % against the bank on the word
"flat" alone — which is the exact failure this check exists to catch. A report with
no killer questions, or with a blank one, scores zero on that question.

The scorecard shows `best_bank_code` and `best_bank_overlap` for every question, so a
near miss is visible: a specific, sensible question that simply is not the bank's
version of itself shows up as, say, "closest bank entry is L5 at 33 %". The bank's
own rule is *pick by the landmine codes the checks raised; do not invent softer
versions*, and this score enforces it.

### `gate_questions_present`

A gate is **open** when the report itself says it does not know: a hard filter
answered `"unknown"`, a `not_found[]` entry, an axis `unknowns[]` line, or an axis
graded U, whose words belong to that gate. A hard filter is read by its `name` and
`observed` only — never the `requirement`, which restates the user's own rule and
often names the landlord in passing. A report that never mentions a gate at all opens
none; silence is already punished by `unknown_honesty` and is not punished twice.

For every open gate, one of that gate's bank questions has to appear in
`killer_questions` (matched the same two ways: word overlap, or naming the code).
How many are expected depends on the room available: rule 1 of the bank says the
first message carries **the gate question plus the one that could kill this flat**,
and the schema caps `killer_questions` at two, so with only killer questions a report
is expected to cover **one** open gate. If the schema ever gains a
`questions_for_next_round` array and a report fills it, every open gate is expected;
`grade.py` reads that field if it exists. With no open gate the score is `null`, not
a free 100 %.

---

## Running an agent

`bench/run.py` prepares a clean working directory (the case's `profile.yaml`, plus
the skill linked into the folder that agent reads skills from), builds the
non-interactive command, runs it, finds `report.json`, grades it, and appends a row
to `bench/results/<date>/scorecard.json` and `scorecard.md`.

**On flags.** Every flag used here either scopes what the agent may touch or tells it
where to work. None of them skips a permission prompt, disables a sandbox, or raises
privilege. `tests/test_grade.py` asserts that no bypass flag appears in any generated
command. If an agent will not run without one, that is a finding to write down, not a
flag to add.

### Claude Code

```bash
python3 bench/run.py --agent claude --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent claude --case se1-london-bridge-hotel-200 --model opus --timeout 900
python3 bench/run.py --agent claude --all-cases --timeout 900
```

Dry-run output, verbatim:

```
case:     se1-london-bridge-hotel-200  (Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG, Southwark)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-se1
          copy evals/cases/se1-london-bridge-hotel-200/profile.yaml -> profile.yaml
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.
command:  cd /tmp/vetflat-bench/claude-se1 && claude -p 'Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.' --allowedTools 'Bash(python3:*)' Read Write --output-format json
```

`--allowedTools` names the only tools this run may use: `Bash(python3:*)` to run the
fetchers, `Read` to read the skill and the profile, `Write` to write `report.json`.
Everything else stays unavailable. `--output-format json` is what carries the token
counts and `total_cost_usd` back into the scorecard.

### Codex

```bash
python3 bench/run.py --agent codex --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent codex --case se1-london-bridge-hotel-200 --model gpt-5-codex
```

Dry-run output, verbatim:

```
case:     se1-london-bridge-hotel-200  (Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG, Southwark)
agent:    codex
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/codex-se1
          copy evals/cases/se1-london-bridge-hotel-200/profile.yaml -> profile.yaml
          symlink skills/vet-flat -> .agents/skills/vet-flat
prompt:   Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.
command:  cd /tmp/vetflat-bench/codex-se1 && codex exec --cd /tmp/vetflat-bench/codex-se1 --sandbox workspace-write -c sandbox_workspace_write.network_access=true --skip-git-repo-check 'Vet this flat: Flat 200, London Bridge Hotel, London Bridge Street, SE1 9SG. Use profile.yaml. Write report.json following references/report-schema.json.'
```

Codex's sandbox blocks the network by default, which stops every fetcher in this
skill dead. `-c sandbox_workspace_write.network_access=true` turns the network on
**inside** the sandbox and leaves the sandbox itself in place — it is the setting
`docs/INSTALL.md` already tells Codex users to set. `--skip-git-repo-check` is only
needed because the temporary working directory is not a git repository.

### A conversation case

The two conversation cases have no `profile.yaml` and no report; the skill is still
linked in so the agent can read its own pitch, and what gets graded is the text that
comes back. `explain-capabilities` is asked twice, once per language, and produces
one scorecard row each (`explain-capabilities#zh`, `explain-capabilities#en`).
`--variant zh` runs just one.

```
case:     explain-capabilities#zh  (a conversation, no flat)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-explain
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   這能幹嘛？
graded:   the plain-text answer, by the checks in expected_facts
command:  cd /tmp/vetflat-bench/claude-explain && claude -p '這能幹嘛？' --allowedTools 'Bash(python3:*)' Read Write --output-format json

case:     explain-capabilities#en  (a conversation, no flat)
agent:    claude
model:    (the agent's default)
workdir:  /tmp/vetflat-bench/claude-explain
          symlink skills/vet-flat -> .claude/skills/vet-flat
prompt:   What can this do?
graded:   the plain-text answer, by the checks in expected_facts
command:  cd /tmp/vetflat-bench/claude-explain && claude -p 'What can this do?' --allowedTools 'Bash(python3:*)' Read Write --output-format json
```

These two matter most in `api` mode, because a chat box is where a new user actually
meets this skill. There the user message is the question and nothing else — no
schema, no fixtures — so the answer comes from the skill text alone.

### Gemini CLI and OpenCode — untested

```bash
python3 bench/run.py --agent gemini   --case se1-london-bridge-hotel-200 --dry-run
python3 bench/run.py --agent opencode --case se1-london-bridge-hotel-200 --dry-run
```

These print `[UNTESTED — flags not verified against the vendor documentation]`. The
commands are `gemini --prompt <prompt>` and `opencode run <prompt>`, both with the
skill in `.agents/skills/vet-flat`. Check them against the current vendor docs before
you trust a number from them, and change `build_command()` in `bench/run.py` rather
than working around it on the command line.

### Chat-only (`api`)

```bash
export OPENAI_BASE_URL=https://api.example.com/v1
export OPENAI_API_KEY=...
python3 bench/run.py --agent api --case se1-london-bridge-hotel-200 --model <name>
```

One POST to an OpenAI-compatible `/v1/chat/completions`, through the same curl-backed
`_fetch` the rest of the repository uses.

- **system** = `dist/prompt-pack/INSTRUCTIONS.md` + `skills/vet-flat/references/inputs.md`, plus one line saying there is no shell and no internet in this run.
- **user** = the case prompt, the case `profile.yaml`, `report-schema.json`, and the truth fixtures pasted as text: the energy certificate page, the police crime JSON, the TfL journey and redundancy JSON, and where the case has them the Companies House and Land Registry JSON.

With no key set it prints one line saying what to set and exits 1 without calling
anything. Note that `api` mode hands the model the answers as *material*: it measures
reading, arithmetic and honesty, not retrieval. A model that fabricates here has
fabricated with the correct page in front of it.

---

## Adding a case

1. Find a real flat with a public certificate:
   `python3 skills/vet-flat/scripts/epc.py search --postcode "E8 2JP"`.
   Prefer a postcode in a borough the suite does not cover yet, and pick a flat that
   tests something the others do not — a failing hard filter, a missing field, an
   identity trap. Never use one of the maintainer's private case postcodes.
2. Add an entry to `evals/evals.json`:
   - `id` — short, stable, lower case, starts with the outcode
   - `address`, `borough` — as the register spells them
   - `prompt` — `Vet this flat: <address>. Use profile.yaml. Write report.json following references/report-schema.json.`
   - `files` — `["cases/<id>/profile.yaml"]`
   - `expected_output` — one sentence
   - `assertions` — human-readable, one per thing you are actually testing, plus the five common ones the other cases carry
   - `truth_inputs` — `postcode`, `borough`, `epc_certificate_id`, `crime`, `commute`, `landregistry`, and `company` only if the case has one obvious named entity
   - `expected_facts` — leave it `{}`
3. Copy any existing `evals/cases/<id>/profile.yaml` to the new case folder. The
   profile is generic and identical for every case on purpose: 45 m2 (484 sq ft)
   minimum, 25 years maximum age, £2,600 all-in ceiling, destination `SW1A 2AA`
   arriving 09:00, 45-minute door-to-door ceiling, no ground floor, a washing machine
   in the flat. Nothing in it is anybody's real requirement.
4. Fill in the truth: `python3 bench/refresh_truth.py --case <id>`.
5. Read the diff. Every number should look like the register, not like a surprise.
6. `python3 -m unittest discover -s tests -p 'test_*.py'`.

A case only earns its place if a plausible report could get it wrong.

### Adding a conversation case

Set `"kind": "conversation"`, leave `files` empty, give `prompt_variants` one entry
per language, and write `expected_facts.answer_checks` as named checks. The rules
available are `regex`, `all_of`, `any_of`, `groups`, `forbidden_claim`, `language`,
`max_chars`, `max_questions`, `defaults_per_question`, `no_protected_questions`,
`number_if_stated` and `date_if_stated`; they are defined in `bench/grade.py` under
"conversation cases", each with a `why` field explaining what it is protecting.
Mark a check `fabrication_on_fail` when failing it means the answer stated something
untrue, and `critical` when failing it should sink the case by itself. Then check
your calibration both ways: the skill's own reference text must score full marks,
and a deliberately bad answer must fail.

---

## What the benchmark does not measure

- **Verdict quality.** On purpose. There is no ground truth for "should you rent it".
- **Anything behind a portal.** Rent, listing photos, price history and resident reviews are all on sites whose terms forbid automated access, so the benchmark holds no truth for price per square foot, management scores or the incentivised-review share, and `grade.py` does not grade them.
- **Whether the agent answers.** The question scores check that the right question was asked, not what came back. A gate question sent and ignored is rule 4 of the bank — "a non-answer is an answer" — and only the user can record that.
- **Aspect, light and the flat itself.** No open register knows which way the windows face.
- **Planning and roads.** `planning.py` and `roads.py` are still being finished; when they land, `nearest_works_m` becomes gradeable and a `planning` block belongs in `expected_facts`.
- **Taste.** A dull correct report and a vivid correct report score the same, and the same goes for the two conversation answers: only the facts and the shape are scored.

## The A/B harness (`bench/ab/`)

The first bullet above — verdict quality is not graded — is exactly what the A/B
harness grades, and it is why it lives in a separate folder with a separate,
**private** gold set.

`bench/ab/` asks a different question from this benchmark: not "did the model get the
facts right" but "if the harness changes — the repository's scripts instead of raw web
pages, a small model for the reading and a big one only for the judgment, no whole-file
reads — does the *answer* get worse?" It grades the landmine codes, the verdict, the
killer questions, and the token bill, against a gold set built from one person's real,
human-reviewed shortlist.

That gold cannot be public: it is real addresses, real landlords and real money. So
`bench/private/` is gitignored, and every A/B script degrades honestly without it —
`bench/ab/grade_ab.py` says which file is missing, and the gold-rule tests in
`tests/test_ab.py` skip. The protocol, the arms, the decision rule and the cost
estimate are in `bench/ab/README.md`; `bench/ab/CODEX_BRIEF.md` is the same experiment
written out for the OpenAI side.

`bench/run.py` grew two flags for it, and they work on this suite too:
`--config bench/ab/configs/<arm>.yaml` applies a system-prompt appendix, an
`--allowedTools` list, a main model and a `budget_mode`, and `--cases <file>` swaps the
case file. Every run's stdout is kept verbatim at
`bench/results/<date>/raw/<config>-<case>-<run>.json`.
````

---

## A/B harness README — `bench/ab/README.md`

````markdown
Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0

# The A/B harness: does a lean harness cost quality?

The public benchmark (`bench/README.md`) asks whether a model gets the facts right.
This one asks a different question: **if you change how the agent works — scripts
instead of raw pages, a small model for the reading, a big model only for the
judgment — does the answer get worse?**

Facts are cheap to grade and they are already graded. What the lean settings could
quietly destroy is the part nobody grades: the landmines the report finds, the verdict
it reaches, and the questions it tells you to ask. So the A/B grades those, against a
private gold set built from one person's real, human-reviewed London shortlist.

---

## The arms

| config | phase | agent | main model | budget | what it isolates |
|---|---|---|---|---|---|
| `A-legacy` | core | claude | CLI default | standard | the baseline: Opus subagents per axis, raw web pages, whole files read in |
| `B-lean` | core | claude | CLI default | standard | the candidate: scripts only, Sonnet workers, no file over 40 KB, one big output |
| `C-twenty` | core | claude | `sonnet` | lite | the cheapest realistic setup, no subagents, no web tools |
| `codex-B-lean-sol` | core | codex | `gpt-5.6-sol` | standard | the lean arm on the OpenAI side |
| `codex-C-terra-lite` | core | codex | `gpt-5.6-terra` | lite | cheap setup, OpenAI side |
| `codex-C-luna-lite` | core | codex | `gpt-5.6-luna` | lite | cheap setup, smallest model |
| `B-raw` | ablation | claude | `fable` | standard | **data path**: raw pages instead of the scripts |
| `B-opus-workers` | ablation | claude | CLI default | standard | **worker model**: Opus instead of Sonnet on the subagents |
| `B-lite` | ablation | claude | CLI default | lite | **budget mode**, main model held at the default |
| `B-main-opus` | ablation | claude | `opus` | standard | **main model** pinned to Opus |
| `B-main-sonnet` | ablation | claude | `sonnet` | standard | **main model** pinned to Sonnet |
| `codex-A-raw-sol` | ablation | codex | `gpt-5.6-sol` | standard | **data path** on the OpenAI side |
| `codex-C-sol-lite` | ablation | codex | `gpt-5.6-sol` | lite | **budget mode** on the default Codex model |
| `codex-D-luna-standard` | ablation | codex | `gpt-5.6-luna` | standard | **budget mode** on the smallest Codex model |

`A-legacy` and `B-lean` both leave `main_model` null, so both run on whatever the CLI
default is. That is deliberate: the two core arms differ in *how they work*, not in
which model they are. `B-main-opus` and `B-main-sonnet` are what pin the model down.

`C-twenty` never votes on adoption. It answers one question — do the basic functions
survive on the cheapest setup — and has its own pass line.

Claude Code model aliases (`claude --help`): `opus`, `sonnet`, `fable` name the latest
model in each family; a full name such as `claude-fable-5` also works. Codex model ids
were read off the installed CLI (codex 0.151): `gpt-5.6-sol` (the default in
`~/.codex/config.toml`), `gpt-5.6-terra`, `gpt-5.6-luna`.

Nothing anywhere passes a permission-bypass flag. The Claude side is scoped by
`--allowedTools`; the Codex side by `-s workspace-write` with the documented
`sandbox_workspace_write.network_access=true`. A test asserts it
(`test_no_config_asks_for_a_permission_bypass`).

---

## The protocol

1. **Build the gold** (private, once):

   ```
   bench/private/build_gold.py
   ```

   Writes `gold.json`, `cases_private.json`, `gold_rules.md` and `profile.yaml` into
   `bench/private/`, which is gitignored. The rules are in `gold_rules.md` and are
   generated from the same table the builder uses, so they cannot drift.

2. **Run the sweep**:

   ```
   bench/ab/run_ab.py --phase core \
       --cases bench/private/cases_private.json \
       --case-ids v2-buck,s09,e01,s02,nw03 --runs 3
   ```

   The loop is **run → case → config**, so the arms interleave: A, B, C, A, B, C …
   Time of day, a register that updates at noon, a model that gets busier at 5 pm —
   all of it lands on every arm equally. No arm ever runs twice in a row.

   It is **resumable**: a run is identified by its raw output file,
   `bench/results/<date>/raw/<config>-<case>-<run>.json`. If that file exists the run
   is skipped. Kill the sweep and restart it and it picks up where it stopped.
   `--no-resume` runs everything again.

   `--dry-run` prints the exact command list and stops. `--parallel N` launches N runs
   at a time, taken in order off the interleaved list, and waits for all of them before
   starting the next batch. At `--parallel 2` that means A and B go out together on the
   same case, which is the tightest possible pairing. Above about 3 you start giving
   back the time-of-day control you interleaved for, and you are also rate-limiting
   yourself, so keep it small.

   The smallest thing worth looking at first — two cases, three configs, one run:

   ```
   bench/ab/run_ab.py --configs A-legacy,B-lean,C-twenty \
       --cases bench/private/cases_private.json \
       --case-ids v2-buck,s09 --runs 1 --agent claude --dry-run
   ```

   which prints six commands in this order, and nothing else happens:

   ```
     1. r1  A-legacy   v2-buck  claude
     2. r1  B-lean     v2-buck  claude
     3. r1  C-twenty   v2-buck  claude
     4. r1  A-legacy   s09      claude
     5. r1  B-lean     s09      claude
     6. r1  C-twenty   s09      claude
   ```

   Each line is followed by the full `bench/run.py --agent claude --config … --cases …
   --case … --run-index …` command it would run. Drop `--dry-run` to run them.

3. **Grade**:

   ```
   bench/ab/grade_ab.py --results bench/results/<date> --gold bench/private/gold.json
   ```

   `run_ab.py` calls it after every batch, so you can watch the tables fill in. It
   writes `summary.md` and `summary.json` next to the scorecard.

   **After `bench/refresh_truth.py` fills a case's `expected_facts`, re-score the runs
   you already have:**

   ```
   bench/ab/grade_ab.py --results bench/results/<date> --regrade \
       --cases bench/private/cases_private.json
   ```

   A run graded before that shows `0/0` facts forever, because the fact table it was
   graded against was empty. `--regrade` finds each run's report — its `report_path`,
   then its workdir, then the stored raw stdout (Claude's `.result`, Codex's event
   stream) — re-scores it against the current cases file, and rewrites that row in
   place. Only the scores change: tokens, cost, wall time, the command and the raw file
   are kept. The scorecard is written through a temp file and renamed, and re-read just
   before the write, so a sweep appending rows at the same time is never truncated or
   lost. A run that produced no report is left exactly as it was and said so in the log.

   Note the report finder refuses `report-schema.json` itself: the schema also has a
   top-level `candidates` key, so a naive search of an event stream would score the
   schema the agent read on its way to writing a report.

4. **Worker eval**, separately, when the A/B says the worker model matters:

   ```
   bench/ab/worker_eval.py --dry-run
   bench/ab/worker_eval.py --models sonnet,opus
   ```

   Fifteen extraction tasks, three of each kind — a saved reviews dump, a planning
   officer's committee report, a tariff page, an energy certificate, a raw TfL journey
   JSON — each with one answer a person checked. No tools, no shell: the model gets the
   instruction and at most 60 KB of UTF-8 from the file, and must answer with the value
   and nothing else. A task on a file bigger than that names `window_start_bytes`;
   every task is answerable from its own window alone.

   This is the one measurement the eleven-axis A/B cannot make cleanly. If Sonnet is
   worse at pulling one number out of one document, the whole lean arm is worse, and the
   A/B would only show it as noise spread thin. Here it shows up as a count.

---

## What is measured

Per run, on top of the public fact scores from `bench/grade.py`:

| metric | what it means | good is |
|---|---|---|
| `landmine_recall` | of the gold's **high-confidence** codes, the share the report raised | high |
| `landmine_recall_script` | the same, over only the codes a repo script can establish | high |
| `landmine_recall_mixed` | the same, over the codes a script half-answers | high |
| `landmine_recall_reading` | the same, over the codes only prose establishes | context, mostly |
| `landmine_recall_low_confidence` | the same for low-confidence gold codes, reported separately and **never** counted in the decision | context only |
| `landmine_precision` | of the codes the report raised, the share in the gold (high or low) | high |
| `verdict_agreement` | exact PASS/EDGE/CONDITIONAL/KILL match | high |
| `verdict_agreement_kill_split` | the 2-level match, KILL vs not-KILL | high |
| `killer_question_overlap` | share of the report's questions sharing ≥50% of their content words with a gold question | high |
| `killer_questions_from_bank` | the public check, carried through | high |
| `unknown_share` | share of the twelve axes graded `U` | low, but honest beats confident |
| `total_tokens`, `total_cost_usd`, `wall_time_s` | the bill | low |

### Two-layer scoring: what a script can find, and what only reading can

The gold set was written by a person who read the resident reviews, the planning
documents and the tenancy paperwork, and who walked the route home at night. That is
what makes it a real test. It is also a **tilt**: an arm that works only from parsed
registers is being marked against sources it never saw, and one overall recall number
hides that completely. `A-legacy` reading raw pages and `B-lean` reading script JSON
are not being asked the same question.

So every gold landmine carries a **layer**, and recall is reported inside each layer as
well as overall. The two poles are `script` and `reading`; `mixed` is the bridge between
them.

| layer | what it means | codes | why it is there |
|---|---|---|---|
| `script` | a repository script establishes it on its own, with no page read | L1, L3, L4, L5, L10, L12 | `epc.py` (area, floor), `crime.py` (the walk home), `roads.py` (the facade), `planning.py` (the works), `company.py` (the landlord entity) |
| `mixed` | a script narrows it or gives half the number; prose gives the rest | L2, L6, L7, L11, L16 | obstruction candidates + planning drawings; heating class + a tariff document; RMC/RTM + reviews; air permeability + reviews; `calc.py` + the listing text |
| `reading` | only pasted or fetched prose establishes it | L8, L9, L13, L14, L15 | reviews, churn, licence terms, published referencing criteria, non-refundable fees |

The mapping is `bench/ab/landmine_layers.yaml`, one line of justification per code, and
it covers L1–L16 exactly once. A **single gold landmine may override its code's layer**
by carrying its own `layer:` — an L2 whose only evidence was a sentence in a planning
officer's report is `reading` for that case, even though L2 is `mixed` in general.
`build_gold.py` stamps the default onto every gold landmine and carries any hand-written
override through a regeneration; that is the one hand edit to `gold.json` that survives.

**How to read the three columns.**

* **`script` is the column that compares arms fairly.** Nothing in it needs a page.
  An arm with no web tools at all should score here, so a miss is a harness or a
  reasoning failure, never a missing input. If two arms differ here, that difference is
  real.
* **`reading` is close to a ceiling.** Nobody pastes a review page into a benchmark run,
  so a low number here is mostly the suite talking about itself — the same story the
  "no input" axes tell. It rewards arms that go and fetch, which is exactly the tilt the
  split exists to make visible. Do not read it as a quality difference on its own.
* **`mixed` is ambiguous by construction.** Read it next to `script` before concluding
  anything: an arm that holds `script` and loses `mixed` lost its access to prose, not
  its judgment.
* **Null is not zero.** A case with no gold code in a layer scores `null` there, so it
  never drags that layer's mean down. Layers where the gold is thin — on the current
  five-case set `reading` holds about 0.4 high-confidence codes per case against
  `script`'s 3.8 — carry very little weight, and `summary.md` prints those counts next
  to the table so you can see how much a column is worth before quoting it.

The three columns are **reported, never voted on**. The overall `landmine_recall` and
the ADOPT / KEEP / UNDECIDED rule below are untouched by this split, and so is the
ablation table's effect word: the layered numbers are extra columns on that table, there
to say *where* a factor moved things.

**One practical limit.** A run can only be scored by layer if the codes it raised are
known, and those come from its report. Reports live in a temp workdir that gets cleaned
up, so `grade_ab.py` now writes a `landmines_found` list onto each scorecard row it
regrades. A row without stored codes and without a readable report scores **null** in
every layer — the grader never guesses which codes a lost run had. The rounds already in
`bench/results/` mostly predate that, so their layered columns are sparse; from the next
round they are complete.

### Why an axis is unknown

`summary.md` carries a per-config table of how often each of the twelve axes came back
`U`, with a **no input** column. Six axes have nothing for a benchmark run to work from:
the material is on a portal this repo will not fetch (price, listing detail, resident
reviews), or it is a document somebody has to paste (a welcome-pack tariff, the landlord
on the tenancy), or no register records it at all (which way the windows face). Those
come back unknown in **every** arm, and the summary says so in as many words, with the
reason per axis, so nobody reads a shared ceiling as a model that failed.

The column to read is **spread**: an axis where the arms differ is a real difference, and
an axis that is unknown everywhere is the suite talking about itself. If an axis is
unknown in every arm and is *not* on the no-input list, the summary says that too — that
one is a genuine gap worth chasing.

`total_tokens` is input + output + cache-read + cache-creation, summed across the main
loop and every subagent (Claude Code reports the split in `usage` and `modelUsage`, and
both are kept in the scorecard row). It is not the API bill — `total_cost_usd` is that,
and it is reported next to it — it is "how much text did this arm have to move", which
is the thing the lean settings are supposed to change.

Two honest limits, so nobody over-reads the tables:

* **The gold verdicts are 10 CONDITIONAL and 10 EDGE — no PASS, no KILL.** That is
  what a real shortlist looks like when every candidate still has open questions. So
  `verdict_agreement_kill_split` is satisfied by any arm that never says KILL, and it
  is a floor check, not a discriminator. The exact-match number is the one to read.
* **Question overlap does not cross languages.** The gold questions are bilingual: the
  reviewer's own are Chinese, the letters actually sent are English. Every candidate
  carries English letter questions, so an English report has English gold to match
  against; a Chinese report matches the Chinese gold through CJK bigrams. A Chinese
  gold question will never match an English report question, and should not.

---

## The decision rule

Printed at the end of `summary.md`, for B against A:

```
ADOPT B    if  fact recall B  >= fact recall A - 0.02
           and fabrications B <= fabrications A
           and the mean landmine recall drop <= one code per case
               (that is, <= 1 / mean gold high-confidence codes per case)
           and tokens B <= 0.5 x tokens A

UNDECIDED  if the B - A differences are smaller than the within-config
           run-to-run spread. Nothing was measured; add runs.

KEEP A     otherwise, with the failing clause named.
```

On the current gold the mean is **5.80 high-confidence codes per case**, so "one code
per case" is a recall drop of about **0.17**. That number moves when the gold moves;
the grader recomputes it and prints it in `inputs.landmine_recall_drop_allowed`.

`C-twenty` and the two cheap Codex arms are judged separately, by the
**basic-functions** line — all of it, or FAIL:

* stable fact recall ≥ 0.90
* fabrications = 0
* hard filter consistency = 1.0
* at least one killer question from the bank
* a verdict is present
* the report is schema-valid

### The factor table

Each ablation config is paired against `B-lean`, one factor at a time, and gets one
line: **effect within noise**, **helps** or **hurts**. "Within noise" means the mean
paired difference on fact recall, landmine recall and verdict agreement is no bigger
than the largest run-to-run spread either arm showed against itself on one case. That
is the whole point of running each case more than once.

---

## How to read the tables

`summary.md` has four, plus the layer block between the first and the second:

1. **Per config** — mean over runs, with min–max in brackets for landmine recall, its
   three layered columns (`script`, `mixed`, `reading`) and tokens. Read the brackets
   first. If they overlap between two arms, the means are telling you very little. Then
   read `script` before the overall number: it is the column where every arm had the
   same input.
2. **Paired differences** — B minus A, *per case*, plus how many cases B was at least
   as good on. A mean difference of −0.1 made of five −0.02s is a different animal
   from one made of one −0.5, and the per-case table is where you see which.
3. **Ablation** — one factor at a time against B-lean, with the effect word.
4. **Basic functions** — the cheap arms, pass or fail, check by check.

Between them sits **Landmine recall by layer**, which says how many gold codes each
layer holds on the cases that ran, how many runs had codes to score at all, and any
per-case layer override in the gold. Read it before quoting a layered column: a column
scored against 0.4 codes per case is not the same evidence as one scored against 3.8.

Then the decision block, with every input it used and the noise floor it compared
against.

---

## The run plan, and what it costs

The core sweep, six configs, five cases, three runs:

| phase | configs | cases | runs | agent runs | rough tokens |
|---|---:|---:|---:|---:|---:|
| core | 6 | 5 | 3 | 90 | ~7.2 M |
| ablation | 8 | 5 | 2 | 80 | ~6.4 M |

The rough number is 90 runs × ~80 k tokens for a lean run. **Read it as a floor, not
an estimate.** The raw-page arms — `A-legacy`, `B-raw`, `codex-A-raw-sol` — pull whole
rendered pages into context, which is one to two orders of magnitude more than the JSON
a fetcher returns, so budget several times that for them. In the core sweep two of the
six arms (`A-legacy`, and any run that falls back to the web) are the expensive ones;
in the ablation set it is `B-raw` and `codex-A-raw-sol`.

A practical way to find out what it really costs before committing: run one case, one
run, all core configs, and read `total_tokens` per config off the first `summary.md`.

```
bench/ab/run_ab.py --phase core --cases bench/private/cases_private.json \
    --case-ids v2-buck --runs 1
```

Five cases is the smallest set that gives the paired tables anything to say. Twenty
are available; `--case-ids` picks any subset.

---

## Adding a gold case

The gold is generated, never hand-edited. To add a case:

1. Add the candidate to the campaign review file that `bench/private/build_gold.py`
   reads.
2. Re-run `bench/private/build_gold.py` and read the coverage table it prints.
3. If a landmine code came out wrong, fix the keyword table **in the builder**, not in
   `gold.json`: the file is regenerated and your edit would be lost. `gold_rules.md`
   is regenerated from the same table, so the documentation follows automatically.
   The one exception is a per-case `layer:` on a gold landmine — that is carried over
   when the gold is rebuilt, because no keyword rule can know that this particular L2
   was only ever visible in an officer's report. The code defaults live in
   `bench/ab/landmine_layers.yaml` and are re-read on every build.
4. If a case genuinely needs a KILL verdict, no rule produces one automatically — say
   so by hand and write why in `notes`.
5. Re-run the tests: `python3 -m unittest discover -s tests -p 'test_*.py'`.

The gold-rule tests in `tests/test_ab.py` skip when `bench/private/` is absent, which
is the normal state of a fresh clone. Everything else in that file runs on synthetic
data and is always green.

---

## Files

```
bench/ab/configs/*.yaml     the arms
bench/ab/landmine_layers.yaml  L1-L16 -> script | mixed | reading, one line of why each
bench/ab/run_ab.py          the sweep: runs x cases x configs, interleaved, resumable
bench/ab/run_codex.py       one config x case against the Codex CLI
bench/ab/grade_ab.py        the metrics, the tables, the decision
bench/ab/worker_eval.py     Sonnet vs Opus on the extraction tasks
bench/ab/CODEX_BRIEF.md     paste this into Codex to run the same thing on the OpenAI side
bench/private/              PRIVATE, gitignored: the gold, the cases, the worker tasks
bench/results/<date>/       scorecard.json, summary.md, summary.json, raw/
tests/test_ab.py            offline tests for all of the above
```
````

---

## Conventions — `docs/CONVENTIONS.md`

```markdown
# Conventions (read before adding a script or reference)

## Scripts (`skills/vet-flat/scripts/`)
- Python 3.9 compatible, **standard library only**. No pip packages. Network I/O only through `_fetch.fetch()` (curl under the hood; per-host throttle ≥1.2 s; on-disk cache; `expect=` content assertion). Never call urllib for network.
- Every script: `argparse` CLI, subcommands where natural, prints **one JSON object** to stdout, human-readable errors to stderr, exit code 0 on success, 2 on usage error, 1 on fetch failure. `--verbose` prints the curl commands to stderr.
- Output envelope for every fetched record: `source_url`, `http_status`, `ok`, `note`, `retrieved_at` (UTC ISO), `evidence_class` (`G` official register / `S` self-reported / `C` third-party / `I` inference / `U` unknown), plus the parsed fields. Missing = `null`, never a guess. Counts of things you looked for but did not find go in `not_found` with the exact query used.
- A 200 with the wrong page is a failure: always pass an `expect` lambda. Record the assertion that failed in `note`.
- Use the browser UA (`_fetch.BROWSER_UA`) except where a host wants a tool UA (Overpass: `_fetch.TOOL_UA`).
- **No personal parameters.** Destinations, budgets, thresholds come from arguments or `profile.yaml`. Defaults must be generic (e.g. destination is a required argument, not a hard-coded campus).
- **Commercial portals and review sites** (Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Google reviews, Airbnb, Booking.com): no fetch code, no selectors, no endpoints, anywhere in this repo. Scripts may *parse a local file the user saved* only if the file format is documented publicly; if in doubt, leave it out.
- Docstring at the top: what the source is, whether it is official, whether a key/login/fee is needed, robots/ToS note, usage examples.

## Tests (`tests/`)
- `unittest` only (pytest is not assumed). Offline parser tests read `tests/fixtures/<script>-<case>.{html,json}` captured from the live site (keep each fixture ≤ 400 KB; strip nothing that the parser needs). One live smoke test per script under `tests/live_smoke.py`, skipped unless `VETFLAT_LIVE=1`.
- Run: `python3 -m unittest discover -s tests -p 'test_*.py'`.

## References (`skills/vet-flat/references/`)
- English, model-facing, plain sentences, checklists over prose. Numbers live in `thresholds.yaml` and are referenced by id; endpoints live in `sources.yaml`.
- First line of every reference file: `Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0`.
- No codenames, no personal circumstances, no named real buildings, no ethnicity/nationality rules.

## Report contract
- `references/report-schema.json` is the single source of truth for the report. Text fields follow the plain-language rules in SKILL.md §7. `render.py` (shell) and `viewer/viewer.html` (browser) must produce the same layout from the same JSON, and both print the footer `Generated with vet-flat <version> — https://github.com/jacky18008/pea-princess`.

## Git
- Small commits per script or reference, with tests. Commit messages end with the Co-Authored-By trailer used in this repo.
```
