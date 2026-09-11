# Install (every channel) · 安裝方式（各平台）

Part of Pea Princess by Hsien Hao (Jacky) Chen — https://github.com/jacky18008/pea-princess — CC BY 4.0
Verified against vendor documentation on 2026-09-03; product features change, so check the linked pages if a step looks different.

**Never used a terminal?** You do not need to. Sections B and C need only a chat app; section A is one pasted line and then everything is sentences too. Plain-words walkthrough: `docs/USING.md`.

## A. Agents with a shell (best experience — scripts run, the model reads JSON)

| Product | Install | Note |
|---|---|---|
| Claude Code | `/plugin marketplace add jacky18008/pea-princess` then `/plugin install pea-princess@pea-princess` | Local shell; full mode |
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

## B. Chat products with a Skills feature (upload pea-princess-skill.zip from Releases)

| Product | Steps | Network for scripts |
|---|---|---|
| claude.ai / Claude Desktop | Settings → Capabilities → enable "Code execution and file creation" → Customize → Skills → + → Upload a skill → the zip | On by default for Free/Pro/Max; **off by default on Team/Enterprise** (an owner enables it) |
| Claude Cowork | Same account: skills enabled on claude.ai sync automatically; or Customize → Plugins → "Add from a repository" → this repo's URL | Has a real browser and a shell in Anthropic's sandbox |
| ChatGPT (Skills) / ChatGPT Work | Skills → Create → Upload from your computer → the zip; invoke with `@pea-princess` | Available on Business / Enterprise / Edu plans at the time of writing (check your plan) |
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

## D. Local package and existing installations

`python3 tools/build_dist.py` creates `dist/pea-princess-skill.zip` with one root folder, `pea-princess/`. Install that folder in your agent's skills directory, such as `~/.agents/skills/pea-princess/`; invoke it as `$pea-princess` in Codex.

If you installed the former `vet-flat` package, preserve that directory outside every agent skills directory before installing the replacement. Keep only `pea-princess` discoverable, then reload the agent's skill list or start a new session. The source tree still uses `skills/vet-flat/` for existing script imports and historical tests; that internal path is not an additional installed skill. Existing report/schema identifiers remain readable.

## D2. Your word outranks the skill's defaults, in every host

`SKILL.md` says it in its first line and `references/rules.md` repeats it: the person's instruction outranks every default in the skill; only four things do not move (no invented numbers, no ethnicity or nationality as a factor, the scripts read open registers only, untrusted inputs never authorize anything). Every host loads `SKILL.md` when the skill is used, so this holds in Claude Code, Codex, Gemini CLI, Grok CLI and the prompt pack alike. If your host keeps its own instruction file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), you may add one line there too:

```
When using pea-princess, my instructions outrank the skill's defaults; say what changed and record it.
```

Measured 2026-09-11 (`docs/EXPERIMENTS.md`): with that sentence in the skill, Claude Code followed the person's explicit instruction over the skill's default in 6 of 7 runs and tried to record the change; Codex did so in 6 of 8 with or without it. Grok CLI is untested here.

## E. Verify
Ask: "Vet this flat: <address or postcode>, flat <n>." The first line of the answer states the mode (shell / fetch / manual). The report ends with "Generated with pea-princess <version> — https://github.com/jacky18008/pea-princess".
