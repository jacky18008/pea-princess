# Pea Princess · 豌豆公主 (`pea-princess`)

**EN** — A vendor-neutral agent skill that vets a London rental flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, total monthly cost and commute, from official and open UK data, ending in a plain-language verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Gemini CLI, Grok CLI, Cursor, Copilot, OpenCode, Cline, Goose, OpenHands, Kimi Code, Qwen Code, pi, OpenClaw, Hermes Agent…) and, in reduced modes, with chat products that cannot run scripts.

**繁中** — 這是一個不綁定任何廠商的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣尻洗（台語，roast）一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出白話判決。任何支援 Agent Skills 格式的 agent 都能用；只能對話不能跑程式的產品也能用「精簡模式」。

> Status: **draft**. Local collection, area sweep, report rendering and experiment harnesses are implemented. Read [security and privacy boundaries](SECURITY.md) before handling personal data or building a release. Usage: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.

**Distribution:** download the skill/tool and run it with your own agent. Pea Princess does not host model workers or handle subscription credentials. The local persona lab is a testing companion. See [desktop/mobile boundaries, provider subscription policies, and release gates](docs/local-product-and-provider-policy.md).

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
/plugin marketplace add jacky18008/pea-princess && /plugin install pea-princess@pea-princess
# claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
```
The skill is installed and invoked as **`pea-princess`**; the upload artifact is `dist/pea-princess-skill.zip`. The repository still stores its source in `skills/vet-flat/` so existing script paths and experiment records remain valid. This is one skill, with one installed name.

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

Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON. The requirements form is the same idea in the other direction: `viewer/requirements.html` (or `scripts/panel.py --profile profile.yaml`) shows the profile as a page, and a filled form copies back as `profile.yaml`. No assistant writes HTML; the model writes YAML and JSON, the two pages render them.

## Why "Pea Princess"
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.

## No code required · 不用會寫程式
Everything is done by typing or dictating sentences: install (one pasted line, or a zip upload in a chat app), then ask, paste what it asks for, read the report, and change any setting by saying it. [The walkthrough](docs/USING.md) explains it in English and Chinese.

**Prefer speaking? · 不想打字？** Use your device's built-in dictation, or an optional app such as Typeless or Wispr Flow, to put your words into the assistant's text box. 可以直接口述需求、住屋經驗或中途補充，不用先整理成表單。See [voice input and free-plan limits](docs/USING.md#speak-instead-of-typing).

## Start here, on any platform
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, `budget_mode` lite/standard/deep for £20 plans and chat-only use). The hard follow-up questions the agent must ask are in `references/questions.md`.

## Benchmark (facts must be right on every model; verdicts may differ)
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.

**Which configuration to run:** `docs/EXPERIMENTS.md` records the original flat-vetting comparisons. The [later context ablation](docs/ablation-2026-09-09/results.md) includes generation costs and source reviews: extra summarization, structured memory and multiple retrieval calls did not save tokens at the tested sizes. Keep one agent with full context as the starting point; the four-role pipeline remains experimental. These studies measure different tasks, not a universal model ranking.

**Long-running projects and changing requirements:** the [session harness](docs/session-harness.md) saves exact user requests, revisioned requirements and conditional exceptions, source snapshots, goals, TODOs and execution state. The managed runner inserts the current packet itself and rejects stale results. Short `AGENTS.md` / `CLAUDE.md` files link to detailed rules; pointers alone cannot ensure reading. [Lifecycle validation](docs/session-harness-validation.md) tests recovery without new model calls, not quality equivalence or token savings.

**Try a whole persona conversation:** run `python3 tools/persona_playground.py` and open the printed local URL. The [interactive lab](docs/persona-playground.md) uses your local Codex login for dynamic persona replies and assistant answers, with step/run/pause, queued human questions, scenario amendments, private history and shared usage ceilings. All 16 cards are available in a clearly labelled chat adaptation; this is a local alpha, with no public deployment or hidden model judge.

**Community feedback, stage 1:** open the [local options form](community/index.html) and follow the [guide](docs/community-feedback-stage1.md). Public JSON contains controlled choices; optional text stays on the author's device. Local validation, import and search use a fictional demo catalog. There is no online submission service or real review dataset yet.

**Whole conversations, not one answer:** `docs/JOURNEYS.md` scores nine scripted multi-turn journeys, and `docs/PERSONAS.md` goes one step further — sixteen fictional people played by a model, with a deterministic controller holding their documents so nothing can be invented, a judge that has to quote its evidence, and a paired probe per person that moves exactly one setting. `python3 bench/personas.py --matrix pilot --dry-run` prints the whole plan without calling a model.

## Tests
```bash
python3 -m unittest tests/test_epc.py
```

## Sources you will not find here
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com are listed by name only. Their terms forbid automated access, so this project gives no method for them; the skill asks you for the page (a PDF, screenshots or the text) and does not open listing links itself. How you and your assistant use those sites is your responsibility under their terms; nothing here does it or asks for it.

## Licence and attribution (proposed)
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with pea-princess <version> — <source URL>". Please keep it.
