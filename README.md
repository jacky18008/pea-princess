# Pea Princess · 豌豆公主 (`vet-flat`)

**EN** — A vendor-neutral agent skill that vets a London rental flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, all-in cost and commute, from official and open UK data, ending in a plain-language verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Gemini CLI, Grok CLI, Cursor, Copilot, OpenCode, Cline, Goose, OpenHands, Kimi Code, Qwen Code, pi, OpenClaw, Hermes Agent…) and, in reduced modes, with chat products that cannot run scripts.

**繁中** — 這是一個不綁定任何廠商的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣審查一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出白話判決。任何支援 Agent Skills 格式的 agent 都能用；只能對話不能跑程式的產品也能用「精簡模式」。

> Status: **draft** (2026-09-03). The EPC route is implemented and tested; other scripts, the report schema and the viewer are in progress. See `docs/` (coming) and the plan.

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
- `skills/vet-flat/scripts/epc.py` — GOV.UK EPC register: `search --postcode`, `search --street --town`, `cert <id>`, `building --postcode` (whole-building area, age, heating profile). Tested against 10 known flats: 10/10 floor areas match.
- more to come: crime, commute, company, planning, roads, render.

## Tests
```bash
python3 -m unittest tests/test_epc.py
```

## Sources you will not find here
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com are listed by name only. Their terms forbid automated access, so this project gives no method for them; the skill asks you to paste the page.

## Licence and attribution (proposed)
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with vet-flat <version> — <source URL>". Please keep it.
