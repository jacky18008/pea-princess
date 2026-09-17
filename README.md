<p align="center">
  <img src="docs/assets/dulac-1911-the-princess-and-the-pea.jpg" width="300" alt="The Princess and the Pea, illustrated by Edmund Dulac in 1911">
</p>
<p align="center"><sub>Edmund Dulac, 1911 · public domain</sub></p>

<h1 align="center">Pea Princess · 豌豆公主</h1>

<p align="center"><b>English</b> · <a href="README.zh-TW.md">繁體中文</a> · <a href="README.zh-CN.md">简体中文</a></p>

<p align="center">An agent skill that vets a London rental flat from official and open UK data —<br>and says plainly what it does not know.</p>

<p align="center">
  <img alt="skill text: CC BY 4.0" src="https://img.shields.io/badge/skill%20text-CC%20BY%204.0-8A2846">
  <img alt="code: MIT" src="https://img.shields.io/badge/code-MIT-2F6F55">
  <img alt="format: Agent Skills" src="https://img.shields.io/badge/format-Agent%20Skills-1F1D26">
  <img alt="listing sites: never fetched" src="https://img.shields.io/badge/listing%20sites-never%20fetched-6B6679">
</p>

An agent skill for checking and searching rental listings in London. It vets a flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, total monthly cost and commute, from official and open UK data, ending in a verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (e.g. GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc.). Plain chat mode works too, but agent mode is recommended: it is steadier on complex tasks. Just talk to the AI in plain words.

## Start here — no terminal needed

Three ways in, from easiest to most manual. Pick the one that matches what you already use.

1. **You use an agent app** (Claude Code, Codex, Cursor, Gemini CLI, Grok Build, …). Paste this sentence to it and wait:

   > Install the skill from https://github.com/jacky18008/pea-princess and then tell me what it can do.

   The agent fetches this repository, installs the skill under the name `pea-princess`, and answers. From then on, just talk: "Roast this flat:" and paste the listing.

2. **You use a chat app with a Skills feature** (claude.ai, Claude Cowork, ChatGPT Business). Download `pea-princess-skill.zip` from [Releases](https://github.com/jacky18008/pea-princess/releases), open Settings → Skills → Upload, choose the zip. Then ask "What can this do?".

3. **You use a chat app without Skills** (ChatGPT Plus Projects, Grok Projects, Gemini Gems, Perplexity Spaces). Download the prompt pack from [Releases](https://github.com/jacky18008/pea-princess/releases), paste `INSTRUCTIONS.md` into the project's instructions and attach the `references/` files. The skill then tells you, once, what to paste.

No code, no settings files: everything after that is sentences, typed or dictated. The five-minute walkthrough is [USING.md](docs/USING.md); every install route with its caveats is [INSTALL.md](docs/INSTALL.md).

## What it checks, and where the answers come from

| The question | Where the answer comes from |
|---|---|
| Is this flat what the advert says — which unit, how big, how old, how is it heated? | the GOV.UK energy certificate register |
| What is being built next door, and how tall? | GLA planning applications |
| How safe is the street, and the walk home at night? | police.uk crime data, six months, a 300 m box |
| Who is the landlord or agent, really, and are they compliant? | Companies House, Client Money Protect, Heat Trust, the GLA rogue landlord checker |
| Is the rent fair for the band, and what will a month really cost? | HM Land Registry sales, the skill's own arithmetic with every source shown |
| Light, noise, the main road, the night economy | OpenStreetMap, Defra noise maps |
| How long is the commute, and is there a backup line? | the TfL journey planner |
| The paperwork: deposit cap, rent in advance, the tenancy rules since 2026-05-01, referencing | the Renters' Rights Act 2025 rules carried in the skill, plus your own documents |

Every finding carries its evidence grade. What it cannot reach, it asks you for, once, in one message. It never opens listing sites: you hand it the page, and [the walkthrough](docs/USING.md) shows the three ways to do that.

## Why "Pea Princess"
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.

The author's own account, in Traditional Chinese, as posted to the community: [到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md).

## Three modes
| Mode | You have | What happens |
|---|---|---|
| Shell | python3 + curl + internet | Scripts fetch and parse; the model reads only compact JSON |
| Fetch | a URL-fetch tool, no shell | Open GET sources only; the skill asks you for the rest |
| Manual | a chat box | The skill lists the pages to open and paste, once, with links |

> Status: **draft**. Local collection, area sweep, report rendering and experiment harnesses are implemented. Read [security and privacy boundaries](SECURITY.md) before handling personal data or building a release. Usage: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.

**Distribution:** download the skill/tool and run it with your own agent. Pea Princess does not host model workers or handle subscription credentials. The local persona lab is a testing companion. See [desktop/mobile boundaries, provider subscription policies, and release gates](docs/local-product-and-provider-policy.md).

<details>
<summary><b>For engineers: install commands, scripts, benchmark, tests</b></summary>

### Install
```bash
# most agents (Codex, Gemini CLI, Cursor, Copilot, OpenCode, Cline, Goose, pi, OpenClaw, Hermes…)
npx skills add jacky18008/pea-princess
# Claude Code
/plugin marketplace add jacky18008/pea-princess && /plugin install pea-princess@pea-princess
# claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
# then, on any host with a shell: is it installed right? (one request per open register)
python3 ~/.claude/skills/pea-princess/scripts/doctor.py   # or the folder your agent installed it to
```
The skill is installed and invoked as **`pea-princess`**; the upload artifact is `dist/pea-princess-skill.zip`. The repository still stores its source in `skills/vet-flat/` so existing script paths and experiment records remain valid. This is one skill, with one installed name.

Codex: enable sandbox network (`sandbox_workspace_write.network_access = true`) or use manual mode.

### Scripts (Python 3.9 standard library only; network via curl)
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

Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON. The requirements page is the same idea for the other file: `scripts/panel.py --profile profile.yaml --out requirements.html` writes a read-only page of where things stand, for the person to open whenever they like. No assistant writes HTML; the model writes YAML and JSON, the scripts render them.

### Ask it what it can do
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, `budget_mode` lite/standard/deep for £20 plans and chat-only use). The hard follow-up questions the agent must ask are in `references/questions.md`.

### Benchmark (facts must be right on every model; verdicts may differ)
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.

**Which configuration to run:** `docs/EXPERIMENTS.md` records the original flat-vetting comparisons. The [later context ablation](docs/ablation-2026-09-09/results.md) includes generation costs and source reviews: extra summarization, structured memory and multiple retrieval calls did not save tokens at the tested sizes. Keep one agent with full context as the starting point; the four-role pipeline remains experimental. These studies measure different tasks, not a universal model ranking.

**Long-running projects and changing requirements:** the [session harness](docs/session-harness.md) saves exact user requests, revisioned requirements and conditional exceptions, source snapshots, goals, TODOs and execution state. The managed runner inserts the current packet itself and rejects stale results. Short `AGENTS.md` / `CLAUDE.md` files link to detailed rules; pointers alone cannot ensure reading. [Lifecycle validation](docs/session-harness-validation.md) tests recovery without new model calls, not quality equivalence or token savings.

**Try a whole persona conversation:** run `python3 tools/persona_playground.py` and open the printed local URL. The [interactive lab](docs/persona-playground.md) uses your local Codex login for dynamic persona replies and assistant answers, with step/run/pause, queued human questions, scenario amendments, private history and shared usage ceilings. All 16 cards are available in a clearly labelled chat adaptation; this is a local alpha, with no public deployment or hidden model judge.

**Community feedback, stage 1:** open the [local options form](community/index.html) and follow the [guide](docs/community-feedback-stage1.md). Public JSON contains controlled choices; optional text stays on the author's device. Local validation, import and search use a fictional demo catalog. There is no online submission service or real review dataset yet.

**Whole conversations, not one answer:** `docs/JOURNEYS.md` scores nine scripted multi-turn journeys, and `docs/PERSONAS.md` goes one step further — sixteen fictional people played by a model, with a deterministic controller holding their documents so nothing can be invented, a judge that has to quote its evidence, and a paired probe per person that moves exactly one setting. `python3 bench/personas.py --matrix pilot --dry-run` prints the whole plan without calling a model.

### Tests
```bash
python3 -m unittest tests/test_epc.py
```

</details>

## Sources you will not find here
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com appear here by name only. Their terms do not want programs reading them automatically, so this project provides no method for that; the skill asks you for the page (a PDF, screenshots or the plain text) and never opens listing links itself. There is no scraper for these sites in this package, and it cannot encourage you to have your agent scrape them either.

## Licence and attribution (proposed)
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with pea-princess <version> — <source URL>". Please keep it.

The illustration is Edmund Dulac's 1911 plate for *Stories from Hans Andersen* (Hodder & Stoughton, London), public domain. The mark in `docs/assets/mark.svg` (a pea under seven mattresses) is original and released with the documentation under CC BY 4.0; `docs/assets/social-preview.png` is the same mark as a 1280×640 preview card.
