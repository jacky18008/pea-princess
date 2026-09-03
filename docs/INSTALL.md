# Install (every channel) · 安裝方式（各平台）

Part of Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
Verified against vendor documentation on 2026-09-03; product features change, so check the linked pages if a step looks different.

## A. Agents with a shell (best experience — scripts run, the model reads JSON)

| Product | Install | Note |
|---|---|---|
| Claude Code | `/plugin marketplace add jacky18008/pea-princess` then `/plugin install vet-flat@pea-princess` | Local shell; full mode |
| Codex (CLI, IDE, app, cloud) | `npx skills add jacky18008/pea-princess -a codex` or in-session `$skill-installer install https://github.com/jacky18008/pea-princess` | **Sandbox network is off by default.** Enable with `codex -c 'sandbox_workspace_write.network_access=true'` or set it in `~/.codex/config.toml`; otherwise use manual mode |
| Gemini CLI | `gemini skills install https://github.com/jacky18008/pea-princess` | Activation asks for consent once |
| Grok CLI | `npx skills add jacky18008/pea-princess -a grok` (also reads Claude Code marketplaces) | |
| Cursor · GitHub Copilot · OpenCode · Cline · Goose · OpenHands · Kimi Code · Qwen Code · pi · OpenClaw · Hermes Agent | `npx skills add jacky18008/pea-princess -a <agent>` (or omit `-a` to auto-detect) | All read the `.agents/skills/` convention or their own folder |
| Hermes Agent (alt) | `hermes skills install jacky18008/pea-princess` | |
| OpenClaw (alt) | `openclaw skills install git:jacky18008/pea-princess` | |

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
