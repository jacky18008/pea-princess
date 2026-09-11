# 找房源、追問、設定介面：別人怎麼做（2026-09-11 研究）

三個研究代理（Sonnet）各跑一個角度，來源附網址與日期；作者核對過的標 ◆，代理轉述的標 ■，廠商行銷數字標 ▲。兩個代理回報「找不到」的地方照實寫，不補。

## 結論（給豌豆公主）

1. **找房源這一步，業界的正式通道是「平台自己的 AI 入口」，不是抓取。** Rightmove 2026-02-24 宣布 ChatGPT 內的 @Rightmove 應用程式，從自家即時房源回傳含出租的卡片，再導回 Rightmove 看完整頁 ◆（作者核對新聞稿）。Zoopla 與 OpenAI 合作、Redfin 與 Zillow 也各有 ChatGPT 應用程式 ■。沒有一家靠抓取；獨立的房源 API 幾乎不存在 ■。Rightmove 的 robots.txt 全面禁止 GPTBot（只留房貸頁）和 CCbot ◆（作者核對）。
2. **最接近豌豆公主的先例是 PropertyData 的瀏覽器外掛**：在使用者正在看的 Rightmove／Zoopla 頁面上疊加土地登記、能源證書等資料，不重抓平台 ■。「貼頁面」的做法有先例（Rent By Prompt 提示詞包），但沒有任何公開數據說使用者能忍受多少貼頁面的麻煩 ■（兩個代理都找不到）。
3. **需求收集：業界預設是一個開放文字框，不是問卷。** Rightmove、OnTheMarket 都是「用你的話描述」一句話對應到篩選器；Redfin 多輪追問；結構化問卷只留給窄的數字子任務（Zillow 的負擔能力計算）■。
4. **追問的共識：最多 2 到 4 題、一次問完、能預設就預設、只問會改變下一步的事。** Anthropic、OpenAI、Google 的指引一致 ■。Typeform 報告說一次一題的完成率 47.3% 對業界基準 21.5%，六題以內 ▲（廠商報告）。
5. **各家的提問工具**：Claude Code 的選項式工具 1 到 4 題、每題 2 到 4 個選項、附「其他」可打字；Codex 命令列也有選項式提問（每題可自己打字）；Gemini 命令列的提問工具原生支援自由文字、選擇、是否 ■。純聊天產品沒有任何結構化工具。MCP 的 elicitation（伺服器請主程式收表單）各家支援不一、不支援巢狀欄位 ■。所以「每題標型別」三家都吃得下；純聊天用文字加預設值。
6. **設定用自然語言改並記住**：Claude Code 的自動記憶、Gemini 命令列的存記憶工具、ChatGPT 的記憶都是「使用者一句話→寫回一個小檔案」；Codex 靠靜態的 AGENTS.md，沒有文件說它會自動寫回 ■。可攜的做法：預設放技能檔，使用者的覆寫寫進一個獨立的小偏好檔（`profile.yaml`），由 agent 直接改。
7. **本機儀表板**：自含式 HTML（資料內嵌、不 fetch）可以直接 `file://` 打開，像 coverage.py 的報告；要「寫回設定檔」就得下載或跑一個小伺服器；手機和純聊天產品打不開 ■。所以現有的 `viewer/viewer.html` 加設定分頁是可行的桌面便利，不能當主路徑。
8. **技能大小**：Agent Skills 規格建議 SKILL.md 少於 500 行、正文少於 5,000 token，細節放 references 隨用隨讀；有 shell 的主程式都是懶載入，大小不是限制；純聊天產品（ChatGPT 專案 8,000 字元、Gemini Gems 建議 500 到 2,000 字元）沒有 references，要一份獨立精簡版 ■。這正是今天把 SKILL.md 瘦到 2,730 字元、規則搬到 `references/rules.md` 的理由。
9. **免費方案的真正風險是主程式的用量上限**，不是技能本身：Claude 免費方案幾則長文件回合就用完五小時額度 ■（轉述，未核）。技能要在開頭講清楚、能降級。

## 對產品形狀的意思

找房源不在範圍內、不限制也不管理；但在 ChatGPT 裡，使用者可以先用 @Rightmove 這類官方應用程式找，再把房源交給豌豆公主的純聊天版查。有 shell 的使用者則走「先縮地圖（區域掃描找建築）→ 自己去平台搜、設提醒 → 貼來 → 尻洗」。

---

## 附錄 A：租屋 AI 助理與資料來源（代理報告，原文）

# Rental/Property-Search AI Assistants — Research Brief (2025–2026)

## 1. Who exists, what they do, how they get listing data

- Rightmove's free-text conversational search beta ("Use AI"), built with Google Cloud/Gemini, runs on its own listings — describe in your own words, no filters — https://propertyindustryeye.com/rightmove-upgrades-ai-tools-to-improve-property-search/ (13 Feb 2026)
- Rightmove's app inside ChatGPT ("@Rightmove") returns a carousel from "Rightmove's live property listings" (sales, rentals), then links back to Rightmove for detail; free and paid ChatGPT both work — https://www.rightmove.co.uk/press-centre/rightmove-to-launch-app-in-chatgpt-in-next-phase-of-ai-innovation-2/ (Feb 2026)
- Zillow became "the only real estate app in ChatGPT," live for all logged-in US users on Free/Plus/Pro, showing Zillow's own listings (rentals included) with MLS/broker attribution via OpenAI's Apps SDK — not scraping — https://zillow.mediaroom.com/2025-10-06-Zillow-debuts-the-only-real-estate-app-in-ChatGPT (6 Oct 2025)
- Zillow's "AI Mode," using "Zillow's data...and custom AI models," began limited beta — https://www.zillow.com/news/zillow-debuts-ai-mode/ (25 Mar 2026)
- Redfin built multi-turn conversational search with Sierra on its own MLS data, then shipped a ChatGPT app — https://www.redfin.com/news/redfin-debuts-conversational-search/ (13 Nov 2025); https://www.rismedia.com/2026/02/09/redfin-extends-ai-powered-home-search-into-chatgpt/ (9 Feb 2026)
- Zoopla's new OpenAI-powered features (own listings) reportedly drove 80% higher listing views and 150% more leads among users — https://propertyindustryeye.com/zoopla-bets-big-on-ai-in-landmark-openai-deal/ (24 Apr 2026)
- OnTheMarket's "Otiem" maps one typed/spoken query onto existing filters — https://www.onlinemarketplaces.com/articles/onthemarket-launches-ai-powered-natural-language-search-and-agent-tools/ (accessed 2026-09-11)
- None of this scrapes — all runs on owned/licensed data. Independent listing APIs barely exist: Zillow retired its public API in 2021; today's route (Bridge Interactive) is gated to MLS brokerages/IDX vendors with multi-week approval — https://zillapi.com/blog/is-zillow-api-still-available-2026/ (accessed 2026-09-11)
- Closest precedent to vet-flat: extension "PropertyData" overlays Land Registry, EPC and SpareRoom data onto the Rightmove/Zoopla/OnTheMarket page the user is already viewing, instead of re-scraping the portal — https://propertydata.co.uk/browser-extension (accessed 2026-09-11)
- Rightmove's ToS bans "bots, crawlers, scrapers"; its live robots.txt blocks CCBot entirely and GPTBot outside mortgage pages — https://www.rightmove.co.uk/robots.txt (accessed 2026-09-11)
- Cautionary precedent: Craigslist cease-and-desisted rental-map startup PadMapper (June 2012) over scraped listings; PadMapper's replacement source, reseller 3taps, was also then sued — https://venturebeat.com/ai/craigslist-blocks-one-man-apartment-search-startup-padmapper (2012)
- Recent big suits target photos/antitrust, not small-tool scraping: CoStar sued Zillow over ~47,000 copied photos (Jul 2025); FTC sued Zillow/Redfin over an alleged rental-ad "pay-to-exit" deal (Sep 2025) — https://fortune.com/2025/07/30/zillow-copyright-infringement-lawsuit-costar-1-billion ; https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-sues-zillow-redfin-over-illegal-agreement-suppress-rental-advertising-competition

## 2. How these products capture requirements

- Rightmove opens with one open text box, not a quiz — sample query: "Victorian terrace with period features, a proper garden, and space to work from home near the station" — https://propertyindustryeye.com/rightmove-upgrades-ai-tools-to-improve-property-search/ (13 Feb 2026)
- OnTheMarket's Otiem: same shape, one open query auto-mapped to filters — https://www.onlinemarketplaces.com/articles/onthemarket-launches-ai-powered-natural-language-search-and-agent-tools/ (accessed 2026-09-11)
- Redfin goes multi-turn: after an initial budget/city query it "can ask clarifying questions" on neighbourhoods, commute or schools — https://www.redfin.com/news/redfin-debuts-conversational-search/ (13 Nov 2025)
- Structured quizzes survive only for narrow numeric sub-tasks: Zillow's BuyAbility asks income, credit score and comfortable monthly spend to score affordability, separate from open-text search — https://www.zillow.com/learn/what-is-buyability/ (accessed 2026-09-11)
- No portal (Rightmove, Zoopla, Zillow, Redfin, OnTheMarket) publishes completion, drop-off or satisfaction numbers for its search/quiz flow.
- Only completion figures found: an uncited vendor-blog claim (forms convert ~0.6%; 10-field forms complete 5–15% vs 30–50% for "conversational capture") — no external study cited, so treat as marketing, not research — https://getperspective.ai/blog/best-real-estate-chatbots-2026-9-platforms-ranked-lead-qualification (29 Jun 2026)

## 3. Pricing/scale for "bring your own AI" tools

- Apps-in-ChatGPT push distribution cost onto the platform, not the tool: Zillow's app is "live right now for all logged-in ChatGPT users...on Free, Plus and Pro plans" — https://zillow.mediaroom.com/2025-10-06-Zillow-debuts-the-only-real-estate-app-in-ChatGPT (6 Oct 2025)
- So BYOAI tools inherit host caps: ChatGPT free text chat carried a 10-messages/5-hours limit until lifted 6 Aug 2026 (uploads/voice/images still metered) — https://deployhyre.com/chatgpt-usage-limits/ (2026)
- Claude's free tier (vet-flat's runtime) is reported around 15–40 messages per rolling 5-hour window, and one long PDF summary "can drain the whole window in 5–8 turns" — relevant for a document-heavy skill — https://www.heyuan110.com/posts/ai/2026-07-08-claude-free-tier-limits/ (8 Jul 2026)
- Free/open-source "agentic-ops/real-estate-mcp" defaults to offline seed data plus free/keyless official sources (FEMA, EPA, NOAA, Census, Walk Score, FBI crime data), flagging cost only for optional paid add-ons (RentCast pay-per-call; Zillow ~$500+/month) — https://github.com/agentic-ops/real-estate-mcp (accessed 2026-09-11)
- Contrast: scraping-based "Zillow/Redfin/SpareRoom" MCP servers on Apify charge $2–3/1,000 results, $0.05–0.08/property, or $29/month unlimited — a paid, metered, ToS-adjacent model — https://apify.com/kawsar/affordable-zillow-search/api/mcp (accessed 2026-09-11)
- Zero-infrastructure alternative: "Rent By Prompt" is a free copy-paste prompt library for analysing rental listings/leases in the user's own ChatGPT/Claude/Gemini, monetised via affiliate links, not fees — https://rentbyprompt.com/prompts/ (accessed 2026-09-11)
- No published research was found on user tolerance (setup steps, pasting pages/PDFs) for free property or relocation AI tools specifically — appears to be an open, undocumented question industry-wide.

## What this means for Pea Princess

1. Vet-flat's no-scrape, official-open-data design already matches how every serious player operates; direct scraping is the exception, mostly done by paid third-party tools in ToS tension.
2. Portal AI competes on *finding* listings, not on independently cross-checking them against police/EPC/planning/Companies House data — that gap is still open ground.
3. "Paste a link/page" friction has real precedent (PropertyData's overlay, Rent By Prompt's packs) but no published tolerance data — vet-flat would be generating evidence, not following it.
4. Open free-text intake ("describe it"/"paste it") is now the industry default over quizzes; save structured questions for narrow numeric sub-tasks, as Zillow splits BuyAbility from search.
5. The real free-tier risk is host rate limits, not vet-flat's logic: Claude/ChatGPT free quotas can vanish in a few long-document turns, so warn users up front and degrade gracefully.

---

## 附錄 B：追問與結構化收集（代理報告，原文）

# Clarifying-Question UX Across Agent Hosts

## 1. Clarifying questions and structured intake across hosts/protocols

- MCP elicitation lets a server send `elicitation/create` so the client renders a form; schemas are capped at flat string/number/boolean/enum fields ("nested structures... intentionally not supported"), plus a URL mode for sensitive data — https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation (rev. 2025-11-25).
- Support is inconsistent: Claude Code's CLI has it, Claude Desktop doesn't (open request) — https://github.com/anthropics/claude-code/issues/41110 (n.d.); Gemini CLI's client errors "Method not found" on elicitation — https://github.com/google-gemini/gemini-cli/issues/22249 (n.d.); Codex CLI merged elicitation support — https://github.com/openai/codex/pull/17043 (merged 2026-04-08).
- Claude Code's `AskUserQuestion` takes 1-4 questions, 2-4 fixed options each, optional multi-select; free text isn't native (apps bolt on an "Other" choice); unavailable inside subagents — https://code.claude.com/docs/en/agent-sdk/user-input (n.d.).
- Gemini CLI's `ask_user` natively supports three question kinds — multiple-choice, free-form text, and yes/no — up to four per call, covering both question types vet-flat needs in one tool — https://geminicli.com/docs/tools/ask-user/ (updated 2026-06-18).
- Codex CLI's `ask_user_question` renders one tab per question plus Submit, arrow-key navigation, and a "type your own" option per question — https://github.com/openai/codex/issues/9926 (n.d.).
- OpenAI's Apps SDK renders custom React components in an iframe over a postMessage bridge; it has no built-in clarifying-question primitive, so a form must be hand-built as a widget — https://developers.openai.com/apps-sdk/build/custom-ux/ (n.d.); apps preview opened to Business/Enterprise/Edu users 2025-11-13 — https://openai.com/index/introducing-apps-in-chatgpt/.
- Google's A2UI is an open declarative JSON UI format (Apache-2.0, v0.8) letting an agent request a form rendered with native widgets (Lit/Angular, Flutter GenUI); used inside Google Opal and Gemini Enterprise — https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/ (2025-12-15).
- AG-UI is a 16-event, MIT protocol for the "agent-to-user" leg (vs. MCP's agent-to-tool, A2A's agent-to-agent), with human-in-the-loop "interrupts" and a declarative generative-UI form language — https://docs.ag-ui.com/introduction (n.d.).
- Cursor's AskQuestion-style tool only fires in Plan mode, not Agent mode, per an open feature request — https://forum.cursor.com/t/allow-askquestion-tool-calls-in-agent-mode-or-any-mode/152517 (n.d.); Windsurf/Cascade asks questions on complex tasks but for open-ended prompts "guesses at intent and executes" instead — https://www.lowcode.agency/blog/windsurf-cascade-feature (n.d.).

## 2. UX guidance on clarifying questions

- Anthropic: agents should "pause for human feedback at checkpoints or when encountering blockers," adding complexity "only when it demonstrably improves outcomes" — https://www.anthropic.com/engineering/building-effective-agents (2024-12-19).
- Anthropic's Claude Code docs recommend front-loading: have Claude "interview" the user with `AskUserQuestion` in one pass ("don't ask obvious questions, dig into the hard parts"), then write a spec so implementation needs no more questions — https://code.claude.com/docs/en/best-practices (n.d.).
- OpenAI's GPT-5.2 guide: act on reasonable assumptions by default; ask a narrow clarifying question "only when missing information would materially change the answer, affect safety, or create a wrong action," else ask up to 1-3 precise questions or present 2-3 interpretations — https://developers.openai.com/cookbook/examples/gpt-5/gpt-5-2_prompting_guide (n.d.).
- Google Cloud's Dialogflow CX guide warns against stacking two questions in one turn and says to end each turn with one guiding question, reusing a single yes/no confirmation intent — https://docs.cloud.google.com/dialogflow/cx/docs/concept/agent-design (n.d.); its design blog frames clarifying questions as conditional, only "when a query is ambiguous," not a default step — https://cloud.google.com/blog/products/ai-machine-learning/how-to-design-conversational-ai-agents (2025-10-31).
- A 2026 UX write-up citing Nielsen Norman Group findings advises offering "2 to 4 scoped options rather than guessing" when intent is unclear, since visible uncertainty preserves trust better than a silent wrong guess — https://www.parallelhq.com/blog/ux-ai-chatbots (n.d.).

## 3. Products combining chat with a form/dashboard for intake

- Lemonade's Maya replaces the insurance-quote form entirely with a one-question-at-a-time chat; the full quote-to-payment flow runs in under 90 seconds, and Lemonade's app holds a 4.9 rating — https://getperspective.ai/blog/lemonade-case-study-conversational-ai-insurance (2026-02-27).
- Zillow's new "AI mode" adds an "Ask Zillow" conversational box alongside its existing filter-based search UI rather than replacing it, in a phased beta through 2026 — https://www.zillow.com/news/zillow-debuts-ai-mode/ (announced 2026-03-25).
- Zumper keeps structured listing cards/filters as the base UI and layers a chat assistant ("Zoe") on top for free-text per-listing questions (pet policy, neighborhood), handing off to structured actions like booking a tour — https://www.zumper.com/blog/zumper-launches-app-in-chatgpt/ (2026-02); https://www.housingwire.com/articles/zumper-ai-assistant-zoe/ (n.d.).
- Typeform's "Data on Data" report (2.6M forms, 568M submissions) found one-question-at-a-time formatting averaged 47.3% completion versus a 21.5% industry baseline, and recommends capping forms at six questions or fewer — https://www.prnewswire.com/news-releases/new-typeform-report-reveals-how-marketers-can-drive-higher-form-completion-rates-302041979.html (2024-01).
- A 2026 lead-gen analysis recommends running the first 3-4 qualifying questions as conversation, then a short static form for the rest; conversational formats clear roughly 40%+ completion on 6+ field forms where traditional forms drop under 20% — https://tinycommand.com/blogs/conversational-forms-vs-traditional-forms-which-is-better-for-your-business (2026-06-11).

## What this means for a portable skill

1. No host-native question tool is both universal and free-text-first: `AskUserQuestion` and Codex's tool are choice-capped (1-4 questions, 2-4 options); only Gemini CLI's `ask_user` natively does free text; plain-chat hosts expose nothing structured at all.
2. MCP elicitation is the closest cross-host standard, but is unevenly shipped (Claude Code yes; Claude Desktop and Gemini CLI no) and its schema forbids nesting — fine for budget/deal-breaker fields, awkward for open prose like "where's your campus."
3. A2UI and AG-UI are richer generative-UI protocols but remain app-frontend technology today, not something a skill invoked from a CLI or chat box can call directly.
4. Guidance from Anthropic, OpenAI, and Google converges: ask at most 2-4 questions, batch them in one turn, default or skip whenever possible, and only ask what actually changes the next action.
5. Given this fragmentation: detect and use a native question tool when offered, fall back to short plain-chat Q&A with defaults otherwise, and keep the local HTML dashboard as the one channel guaranteed to take real free text and show the report everywhere.

---

## 附錄 C：可攜技能的慣例、自然語言設定、本機儀表板（代理報告，原文）

# Portable Agent Skill UI Research

## 1. Agent Skills format and host conventions

- Spec caps: `name` ≤64 chars, `description` ≤1024 chars, `compatibility` ≤500 chars; body is free-form but "keep your main SKILL.md under 500 lines," moving detail into references/scripts/assets — https://agentskills.io/specification (accessed 2026-09-11).
- Progressive disclosure is spec-defined: metadata ~100 tokens (always loaded) → SKILL.md body <5,000 tokens (loaded when triggered) → references/scripts/assets loaded only as needed — https://agentskills.io/specification (accessed 2026-09-11).
- Claude Code implements this: bundled files "cost None until accessed" — "no practical limit on bundled content"; skills live in `~/.claude/skills/` or `.claude/skills/` — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview (accessed 2026-09-11).
- Codex CLI, Gemini CLI, GitHub Copilot, Grok Build, Goose, Cline, and OpenCode all now load SKILL.md lazily from their own alias alongside portable `.agents/skills` — https://geminicli.com/docs/cli/skills (accessed 2026-09-11).
- Codex caps its upfront cross-skill listing at "2% of the model's context window, or 8,000 characters when the context window is unknown"; full SKILL.md loads only once picked — https://learn.chatgpt.com/docs/build-skills (accessed 2026-09-11; redirect target of developers.openai.com/codex/skills).
- Cursor skips SKILL.md; it uses `.cursor/rules/*.mdc` (own frontmatter: description/globs/alwaysApply); guidance is <200 words for always-loaded rules and <500 lines for path-triggered ones — https://cursor.com/docs/rules (accessed 2026-09-11).
- ChatGPT Project/Custom-GPT instructions and Gemini Gems use one flat field, no references. ChatGPT caps it at 8,000 characters (plain custom instructions are lower: 5,000/1,500 chars by plan, since 2026-07-15) — https://elephas.app/resources/chatgpt-projects-limits-files-size-and-how-many-projects (updated 2026-09-08).
- Google advises 500–2,000 characters for Gemini Gem instructions, pushing the rest into up to 10 attached knowledge files; no hard character ceiling found in Google's own docs — https://support.google.com/gemini/answer/15235603 (accessed 2026-09-11).

## 2. Natural-language settings patterns

- Claude Code splits settings into user-written `CLAUDE.md` (persistent instructions) vs. Claude-written "auto memory": e.g. "always use pnpm, not npm" saves automatically under `~/.claude/projects/<project>/memory/`; "add this to CLAUDE.md" targets the instruction file instead — https://code.claude.com/docs/en/memory (accessed 2026-09-11).
- `/memory` lists every CLAUDE.md and auto-memory file so a user can see, edit, or delete what got written back, and can toggle auto memory off — https://code.claude.com/docs/en/memory (accessed 2026-09-11).
- Gemini CLI's memory tool "persists durable facts, user preferences, and project details by editing Markdown files directly," citing preference persistence like "I prefer functional programming" as a use case — the clearest documented override-and-write-back pattern found — https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/memory.md (accessed 2026-09-11).
- ChatGPT "saved memories" work the same way conversationally ("remember that I am vegetarian"), surface a "Memory updated" notice, and stay user-editable/deletable in Settings — https://www.itechpost.com/articles/237009/20260811/how-does-chatgpts-memory-feature-work-saved-memories-chat-history-settings-explained.htm (2026-08-11).
- Cursor's "Memories" (v1.0+, June 2025) are proposed by a background model but need explicit user approval before saving, and stay scoped to one project rather than committed to the repo — https://hindsight.vectorize.io/blog/2026/06/12/cursor-persistent-memory (2026-06-12).
- Codex's AGENTS.md is static — "loaded at startup," shaping behavior "through instruction, not enforcement." No OpenAI doc was found of Codex auto-writing a correction back into AGENTS.md; it appears to need an explicit edit — https://developers.openai.com/codex/guides/agents-md (per secondary summary, 2026).

## 3. Local, serverless dashboards

- A fully self-contained static HTML report (data inlined in a `<script>` tag, nothing fetched at runtime) opens via `file://` — webpack-bundle-analyzer's `static` mode output "can be opened directly in any browser without a server" — https://github.com/webpack-contrib/webpack-bundle-analyzer (accessed 2026-09-11).
- Same pattern in Python tooling: `coverage html` generates a self-contained, per-file decorated-source report meant to be opened straight from disk — https://coverage.readthedocs.io/en/latest/commands/cmd_html.html (accessed 2026-09-11).
- What breaks it: a page calling `fetch`/XHR for its own data fails under `file://`, because "CORS requests may only use the HTTP or HTTPS URL scheme" and a local file's origin is null — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSRequestNotHttp (accessed 2026-09-11).
- Playwright's HTML report and Trace Viewer must be launched via `npx playwright show-report`/`show-trace` (a small local server) instead of opened as `file://`, because they fetch trace data at runtime — https://playwright.dev/docs/trace-viewer (accessed 2026-09-11).
- Writing a config file back to disk needs a bundled server: Decap CMS's `npx decap-server` runs a proxy on `localhost:8081` so the admin page can save edits to local files, not just preview them — https://decapcms.org/docs/decap-proxy/ (accessed 2026-09-11).
- Mobile breaks hardest: current iOS Safari cannot open a local `file://` HTML file and run scripts — viewing from Files/Mail gives a sandboxed, read-only preview; only "Share → Open in Safari" runs it interactively — Apple Community, https://discussions.apple.com/thread/255328822 (2026).
- Chrome/Android tightens the same door: current Chrome disables navigation to `file://` URLs once "Allow File Access" is off, layered on the same null-origin fetch restriction — https://issues.chromium.org/issues/40074299 (accessed 2026-09-11).

## What this means for a portable skill

- Scriptable hosts (Claude Code, Codex, Gemini CLI, Copilot, Grok Build, Goose, Cline, OpenCode) all lazy-load SKILL.md plus references/, so size isn't the constraint there — keep the full spec structure.
- Non-scripting hosts (ChatGPT Projects/Custom GPT, Gemini Gems, plain chat) cap out near 8,000 (or 2,000) characters with no on-demand references — ship a short, stand-alone "core" file for them.
- For "change a default in plain language," mirror Claude Code's auto-memory and Gemini CLI's save-to-Markdown tool: keep defaults in SKILL.md/references, write user overrides to one small, separate preferences file the agent edits directly.
- For the dashboard, keep HTML fully self-contained (data inlined, no `fetch`) so it opens via `file://` like coverage.py or webpack-bundle-analyzer; any live read/write of settings needs a manual download step or a tiny bundled server (Decap-CMS style).
- Do not promise the dashboard works on mobile or inside non-scripting chat apps — treat `file://` HTML as a desktop convenience and give those two contexts a plain-text fallback.
