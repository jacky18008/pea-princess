<p align="center">
  <img src="docs/assets/dulac-1911-the-princess-and-the-pea.jpg" width="300" alt="The Princess and the Pea, illustrated by Edmund Dulac in 1911">
</p>
<p align="center"><sub>Edmund Dulac, 1911 · public domain</sub></p>

<h1 align="center">Pea Princess · 豌豆公主</h1>

<p align="center"><a href="README.md">繁體中文</a> · <b>English</b></p>

<p align="center">An agent skill that vets a London rental flat from official and open UK data —<br>and says plainly what it does not know.</p>

<p align="center">
  <img alt="skill text: CC BY 4.0" src="https://img.shields.io/badge/skill%20text-CC%20BY%204.0-8A2846">
  <img alt="code: MIT" src="https://img.shields.io/badge/code-MIT-2F6F55">
  <img alt="format: Agent Skills" src="https://img.shields.io/badge/format-Agent%20Skills-1F1D26">
  <img alt="listing sites: never fetched" src="https://img.shields.io/badge/listing%20sites-never%20fetched-6B6679">
</p>
<p align="center"><sub>Author: Hsien Hao (Jacky) Chen 陳先灝 · <a href="https://www.linkedin.com/in/jacky-chen-a49177137/">LinkedIn</a></sub></p>

An agent skill for checking and searching rental listings in London. It vets a flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, total monthly cost and commute, from official and open UK data, ending in a verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (e.g. GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc.). Plain chat mode works too, but agent mode is recommended: it is steadier on complex tasks. Just talk to the AI in plain words.

## Why "Pea Princess"
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.

The author's own account, in Traditional Chinese, as posted to the community: [到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md).

## Start here — no terminal needed

Three ways in, from easiest to most manual. Pick the one that matches what you already use.

1. **You use an agent app** (Claude Code, Codex, Cursor, Gemini CLI, Grok Build, …). Paste this sentence to it and wait:

   > Install the skill from https://github.com/jacky18008/pea-princess and then tell me what it can do.

   The agent fetches this repository, installs the skill under the name `pea-princess`, and answers. From then on, just talk: "Roast this flat:" and paste the listing.

2. **You use a chat app with a Skills feature** (claude.ai, Claude Cowork, ChatGPT Business). Download `pea-princess-skill.zip` from [Releases](https://github.com/jacky18008/pea-princess/releases), open Settings → Skills → Upload, choose the zip. Then ask "What can this do?".

3. **You use a chat app without Skills** (ChatGPT Plus Projects, Grok Projects, Gemini Gems, Perplexity Spaces). Download the prompt pack from [Releases](https://github.com/jacky18008/pea-princess/releases), paste `INSTRUCTIONS.md` into the project's instructions and attach the `references/` files. The skill then tells you, once, what to paste.

No code, no settings files: everything after that is sentences, typed or dictated. The five-minute walkthrough is [USING.md](docs/USING.md); every install route with its caveats is [INSTALL.md](docs/INSTALL.md).

### Tell it about you

You do not fill in a form. Say what you need and what you cannot stand — the budget with bills, the commute, "never a basement again" — and the places you have lived, the best and the worst; even a shopping habit you remember tells it how you decide. It keeps that in your `profile.yaml`, shows every change before it makes it, and you can change your mind halfway. If typing is a chore, dictate: the built-in dictation on your phone or computer, or an app such as Typeless or Wispr Flow, and mixed Chinese and English is fine.

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

## It is a filter. Go and see the flat

Everything here is read from registers and from what you paste. It cannot smell the damp, hear the road at 2 a.m., or see the agent's face when you ask who the landlord is. So treat the report as the list of what to look at, then go:

- **At the viewing**: the report ends with the two questions most likely to change your mind and what to check in the first thirty minutes — the meter, the boiler or heat-network billing, the window over the road, the lift, the bins.
- **With the agent and the landlord**: ask who is on the contract, which scheme will hold the deposit, what is included in the bills, how long you are tied in, and when you can move in. Take the agreement away to read. Never sign on the viewing day.
- **Afterwards**: paste the chat with the agent, the photos and anything they sent, and ask it to check them against the report. A claim in a message is not a fact until a register or a document agrees.

The author built this because looking for a flat in London is a grim process, and an assistant that reads the registers saved them many wasted viewings. It is not a replacement for your own feet.

## Which plan, which mode

Use the subscription you already have; for this work a personal plan is far better value than pay-as-you-go keys, and it needs no setup. Prefer an agent mode (Claude Code, Codex, Grok Build, Cursor…) over plain chat: the checks are a long task with many small steps, and chat mode has to be walked through them by hand.

| You pay for | Use it in | Set `budget_mode` to | Worth knowing |
|---|---|---|---|
| ChatGPT Plus, about £20 | Codex (app, CLI or IDE) | `lite` | the most published headroom and usage numbers you can plan with; turn Codex's sub-agents off (`[agents] enabled = false`) or each answer costs five to twenty times more |
| Claude Pro, about £20 | Claude Code, or claude.ai with the skill uploaded | `lite` | works well; no published usage figures, and it shares one pool with chat |
| Claude Max or ChatGPT Pro, £100 and up | the same | `standard`, `deep` for the last two flats | the author's own setup: Codex for the legwork, Claude's largest model for the judgement calls — the hard cases and the final advice |
| SuperGrok or X Premium+ | Grok Build CLI | `lite` | it runs the skill, but in our first measurements an answer took about ten minutes and millions of tokens; not a daily default yet |
| A chat app without Skills | the prompt pack | manual | the skill lists, once, what to paste |
| An API key | Codex, OpenCode or Gemini CLI with a cheap model | `standard` | a quick check costs pence and an area sweep under £1, at the price of a key and a config file |

Set it once in your `profile.yaml` (`budget_mode: lite`) or just say it ("use deep for this one"); the assistant confirms the change. The modes are depths of the same checks: `lite` keeps under ten fetches a flat and still gives the hard filters, the verdict and the two questions; `standard` is the usual set; `deep` adds the shortlist extras. Two things measured on real flats, not opinions: depth matters more than model size (a strong model in `lite` scored below a weak one in `standard`), and cheap set-ups are the ones that invent numbers, which is why every number here must carry its source or be marked unknown. Details and caveats: [INSTALL.md](docs/INSTALL.md), [budget modes](skills/vet-flat/references/budget-modes.md), [experiments](docs/EXPERIMENTS.md).

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
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, and `budget_mode` — which value fits which plan is the table under "Which plan, which mode"). The hard follow-up questions the agent must ask are in `references/questions.md`.

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

## Make it yours

A skill is a folder of Markdown and a few scripts, and this one is written to be bent. You do not need to read the code: say what you want to your agent.

- **Your rules, in your words.** "Raise my all-in ceiling to £2,300", "quiet matters more than light", "only ask me the eight money questions". The assistant shows the change, waits for your yes, then writes it into your `profile.yaml`. Depth too: `lite` on a £20 plan, `deep` when a flat is serious.
- **Your own checks.** Anything the shared skill does not look at — the walk to your gym, a school's catchment, a noise you know about — goes into `extensions/` as one page, or you dictate the list and let the agent write it. They are labelled as yours in the report and never move the verdict by themselves.
- **Change the skill itself.** Tell the agent what annoys you or what is missing: "put the monthly cost first in every report", "add a check for upper floors without a lift", "ask the questions in Cantonese". It edits the files under `skills/vet-flat/`; `python3 -m unittest discover -s tests` tells you nothing broke, and the report schema keeps the output readable by the viewer.
- **Your private edition.** The author keeps a token-hungry "roast everything" version; yours can be a fork, or just an `extensions/` folder. Keep `profile.yaml`, `.pea-state/` and your documents out of anything you publish (see [SECURITY.md](SECURITY.md)).
- **Another country.** Fork it for Taiwan, the US or the EU: the register scripts are the part to swap, the conversation rules travel as they are. Keep the attribution (CC BY 4.0 text, MIT code) and say where it came from; the author is glad to compare notes.
- **Share tips, not your address.** "Share my seed" gives a short code that carries your taste and your questions, never where you live or when you move.

One sentence to try first, on any host:

> Change this skill so that every report starts with the all-in monthly cost, run the tests, and tell me what you changed.

## Licence and attribution (proposed)
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with pea-princess <version> — <source URL>". Please keep it.

The illustration is Edmund Dulac's 1911 plate for *Stories from Hans Andersen* (Hodder & Stoughton, London), public domain. The mark in `docs/assets/mark.svg` (a pea under seven mattresses) is original and released with the documentation under CC BY 4.0; `docs/assets/social-preview.png` is the same mark as a 1280×640 preview card.

## Contact the author

Hsien Hao (Jacky) Chen 陳先灝 — [LinkedIn](https://www.linkedin.com/in/jacky-chen-a49177137/). Questions, ideas and stories from your own search are welcome: open an issue here or write on LinkedIn.
