# Copy deck — Pea Princess (`vet-flat`)

Every sentence a *reader* sees, in one place, so it can be rewritten in one voice.
Model-facing text (SKILL.md, the axis files, budget modes, the question tables, the
schemas, thresholds and sources) is deliberately **not** here.

**Edit the fenced text only. Keep the ids. Run `python3 tools/copy_deck.py apply`.**

How it works
- Each block below is a verbatim span of lines from its source file. Keep the line
  prefixes you see — `> `, `- `, `1. `, two spaces of indent, a `key:` — they are part
  of the file, not decoration.
- `apply` finds the old text in the source by exact match (not by line number) and
  swaps it. If the old text is gone or appears twice, that block is refused by name
  and **nothing in that file is written**.
- `deck:<file>:<n>` is positional: `n` counts blocks in that file, top to bottom. A
  re-extract after the source is restructured can renumber; the ids are stable as long
  as blocks are not inserted above one another.
- Blocks marked `write-back: no` are read-only in this deck. Edit those in the source.
- Line numbers are informational and go stale; the exact text is what matches.

On a phone
- `docs/review-board.html` is the same deck as a page you can edit with your thumbs.
  Publish it as an Artifact with `capabilities: {"db": {}}` and its edits land in the
  artifact store; `python3 tools/copy_deck.py board` refreshes what it shows.
- To bring those edits home: read the store into a file (or use the page's
  "Copy edits as Markdown"), then `merge --from <file>` and `apply`.


## Contents

| Surface | Blocks | Source |
|---|---|---|
| README — the front page | 18 | `README.md` |
| docs/USING.md — the plain-words walkthrough | 42 | `docs/USING.md` |
| docs/INSTALL.md — install page | 9 | `docs/INSTALL.md` |
| docs/EXPERIMENTS.md — which configuration to run | 7 | `docs/EXPERIMENTS.md` |
| onboarding.md — what the skill says to a new user | 30 | `skills/vet-flat/references/onboarding.md` |
| sharing.md — social posts and the card description | 6 | `skills/vet-flat/references/sharing.md` |
| inputs.md — the one message that asks the user for what is missing | 1 | `skills/vet-flat/references/inputs.md` |
| profiles/ — the sentences a profile carries | 14 | `skills/vet-flat/profiles/*.yaml` |
| seed.py — the seed card sentences (read-only here) | 25 | `skills/vet-flat/scripts/seed.py` |
| **Total** | **152** | |

---

## README — the front page

All prose paragraphs. Tables, headings and code blocks are not in the deck.

### deck:readme:1

- source: `README.md` · L3
- under: # Pea Princess · 豌豆公主 (`vet-flat`)
- lang: en
- write-back: yes

```text
**EN** — A vendor-neutral agent skill that vets a London rental flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, all-in cost and commute, from official and open UK data, ending in a plain-language verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Gemini CLI, Grok CLI, Cursor, Copilot, OpenCode, Cline, Goose, OpenHands, Kimi Code, Qwen Code, pi, OpenClaw, Hermes Agent…) and, in reduced modes, with chat products that cannot run scripts.
```

### deck:readme:2

- source: `README.md` · L5
- under: # Pea Princess · 豌豆公主 (`vet-flat`)
- lang: zh-TW
- write-back: yes

```text
**繁中** — 這是一個不綁定任何廠商的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣尻洗（台語，roast）一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出白話判決。任何支援 Agent Skills 格式的 agent 都能用；只能對話不能跑程式的產品也能用「精簡模式」。
```

### deck:readme:3

- source: `README.md` · L7
- under: # Pea Princess · 豌豆公主 (`vet-flat`)
- lang: en
- write-back: yes

```text
> Status: **draft**. Local collection, area sweep, report rendering and experiment harnesses are implemented. Read [security and privacy boundaries](SECURITY.md) before handling personal data or building a release. Usage: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.
```

### deck:readme:4

- source: `README.md` · L9
- under: # Pea Princess · 豌豆公主 (`vet-flat`)
- lang: en
- write-back: yes

```text
**Distribution:** download the skill/tool and run it with your own agent. Pea Princess does not host model workers or handle subscription credentials. The local persona lab is a testing companion. See [desktop/mobile boundaries, provider subscription policies, and release gates](docs/local-product-and-provider-policy.md).
```

### deck:readme:5

- source: `README.md` · L26
- under: # claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
- lang: en
- write-back: yes

```text
Codex: enable sandbox network (`sandbox_workspace_write.network_access = true`) or use manual mode.
```

### deck:readme:6

- source: `README.md` · L29
- under: ## Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
All in `skills/vet-flat/scripts/`; each prints one JSON object with `source_url`, `retrieved_at`, `http_status`, `ok` and an evidence class. Usage details: `docs/SCRIPTS.md`.
```

### deck:readme:7

- source: `README.md` · L44
- under: ## Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON.
```

### deck:readme:8

- source: `README.md` · L47
- under: ## Why "Pea Princess"
- lang: en
- write-back: yes

```text
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.
```

### deck:readme:9

- source: `README.md` · L50
- under: ## No code required · 不用會寫程式
- lang: en
- write-back: yes

```text
Everything is done by typing sentences: install (one pasted line, or a zip upload in a chat app), then ask, paste what it asks for, read the report, and change any setting by saying it. `docs/USING.md` walks through it in five minutes, in English and Chinese.
```

### deck:readme:10

- source: `README.md` · L53
- under: ## Start here, on any platform
- lang: en
- write-back: yes

```text
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, `budget_mode` lite/standard/deep for £20 plans and chat-only use). The hard follow-up questions the agent must ask are in `references/questions.md`.
```

### deck:readme:11

- source: `README.md` · L56
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.
```

### deck:readme:12

- source: `README.md` · L58
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Which configuration to run:** `docs/EXPERIMENTS.md` records the original flat-vetting comparisons. The [later context ablation](docs/ablation-2026-09-09/results.md) includes generation costs and source reviews: extra summarization, structured memory and multiple retrieval calls did not save tokens at the tested sizes. Keep one agent with full context as the starting point; the four-role pipeline remains experimental. These studies measure different tasks, not a universal model ranking.
```

### deck:readme:13

- source: `README.md` · L60
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Long-running projects and changing requirements:** the [session harness](docs/session-harness.md) saves exact user requests, revisioned requirements and conditional exceptions, source snapshots, goals, TODOs and execution state. The managed runner inserts the current packet itself and rejects stale results. Short `AGENTS.md` / `CLAUDE.md` files link to detailed rules; pointers alone cannot ensure reading. [Lifecycle validation](docs/session-harness-validation.md) tests recovery without new model calls, not quality equivalence or token savings.
```

### deck:readme:14

- source: `README.md` · L62
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Try a whole persona conversation:** run `python3 tools/persona_playground.py` and open the printed local URL. The [interactive lab](docs/persona-playground.md) uses your local Codex login for dynamic persona replies and assistant answers, with step/run/pause, queued human questions, scenario amendments, private history and shared usage ceilings. All 16 cards are available in a clearly labelled chat adaptation; this is a local alpha, with no public deployment or hidden model judge.
```

### deck:readme:15

- source: `README.md` · L64
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Community feedback, stage 1:** open the [local options form](community/index.html) and follow the [guide](docs/community-feedback-stage1.md). Public JSON contains controlled choices; optional text stays on the author's device. Local validation, import and search use a fictional demo catalog. There is no online submission service or real review dataset yet.
```

### deck:readme:16

- source: `README.md` · L66
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Whole conversations, not one answer:** `docs/JOURNEYS.md` scores nine scripted multi-turn journeys, and `docs/PERSONAS.md` goes one step further — sixteen fictional people played by a model, with a deterministic controller holding their documents so nothing can be invented, a judge that has to quote its evidence, and a paired probe per person that moves exactly one setting. `python3 bench/personas.py --matrix pilot --dry-run` prints the whole plan without calling a model.
```

### deck:readme:17

- source: `README.md` · L74
- under: ## Sources you will not find here
- lang: en
- write-back: yes

```text
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com are listed by name only. Their terms forbid automated access, so this project gives no method for them; the skill asks you to paste the page.
```

### deck:readme:18

- source: `README.md` · L77
- under: ## Licence and attribution (proposed)
- lang: en
- write-back: yes

```text
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with vet-flat <version> — <source URL>". Please keep it.
```

---

## docs/USING.md — the plain-words walkthrough

Every paragraph, step and bullet, in all three languages. Headings are not in the deck.

### deck:using:1

- source: `docs/USING.md` · L7
- under: ## English
- lang: en
- write-back: yes

```text
**Everything in Pea Princess is done by typing sentences.** No code, no settings files to hand-edit, no programming ideas. The words "terminal", "Codex" and "Claude Code" in the install guide mean a text box where you type sentences to an assistant that can also run the checks for you. If you would rather not see a terminal at all, use a chat app instead (Claude, ChatGPT and others accept the same skill as an upload); the checks still apply, but independent fetching and automatic arithmetic require tools; otherwise you supply the source material and inspect the shown calculations.
```

### deck:using:2

- source: `docs/USING.md` · L10
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
1. **Install** (one of): paste one line into the assistant's text box (the install guide shows it), or upload the zip in your chat app's Skills page. Done.
```

### deck:using:3

- source: `docs/USING.md` · L11
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
2. **Type:** "What can this do?" — you get a short answer and three ways to start.
```

### deck:using:4

- source: `docs/USING.md` · L12
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
3. **Type one of:**
```

### deck:using:5

- source: `docs/USING.md` · L13
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
   - "I'm moving to London in October and starting from zero. Teach me."
```

### deck:using:6

- source: `docs/USING.md` · L14
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
   - "I want a one-bed in east London, £2,200 all-in, moving 1 November."
```

### deck:using:7

- source: `docs/USING.md` · L15
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
   - "Roast this flat: " and paste the listing text.
```

### deck:using:8

- source: `docs/USING.md` · L16
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
   - "Here are four short stays, roast them" and paste them.
```

### deck:using:9

- source: `docs/USING.md` · L17
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
4. **Answer the six questions** it asks (budget, space, dates, destination, deal-breakers, income check). "Don't know" is a fine answer; it suggests a default.
```

### deck:using:10

- source: `docs/USING.md` · L18
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
5. **Paste what it asks for** — a page's text, a floor-plan picture, a street-view screenshot — once, from a list it gives you with links.
```

### deck:using:11

- source: `docs/USING.md` · L19
- under: ### Five minutes, start to finish
- lang: en
- write-back: yes

```text
6. **Read the report.** The first line says which configuration it used. Every number says where it came from. "Unknown" means it does not know, and it tells you how to find out.
```

### deck:using:12

- source: `docs/USING.md` · L22
- under: ### The questions it always answers
- lang: en
- write-back: yes

```text
Every flat gets the same questions, in the same order: the deposit, the money asked up front, who the landlord on the contract actually is, which scheme will hold your deposit, the floor area, the energy letter, what the bills cover, how long you are tied in, when you can move in. Each one comes back in one of three ways — **found in writing**, with the sentence it was read in quoted next to it; **you told us**, because it asked you; or **not known**, which means nobody has checked yet, never that it is fine. It asks you once, in one message, about everything still not known.
```

### deck:using:13

- source: `docs/USING.md` · L24
- under: ### The questions it always answers
- lang: en
- write-back: yes

```text
How many it answers follows how deep you asked it to look: a quick check answers the eight about money and paperwork, the normal one answers fourteen, and a deep check answers eighteen — adding the council tax band, whether they want a guarantor who lives in the UK, what their tenant checks will ask you to prove, and what furniture comes with the flat. You do not have to choose. If you ever want to, say "only ask me the eight that matter" or "answer all eighteen"; those two live in an **Advanced** part of your settings file that nobody is asked about when they start.
```

### deck:using:14

- source: `docs/USING.md` · L27
- under: ### Before you land
- lang: en
- write-back: yes

```text
If you are flying in, do one thing before you look at a single flat: book somewhere to sleep for the first two weeks — a hotel or an operator-run serviced stay, where the money is protected and you can walk out the same day. Then plan about six weeks, not six nights, because signing is not moving in: after the signature come the tenant checks, the deposit going into a government scheme and the last tenant moving out, and four to seven weeks from landing to keys is ordinary in September (the author's own gap was 45 days). Tell it four things — the day you land, the day you have to be functioning here, the day you hope for keys, and what a week of the bridge costs — and it writes the week-by-week plan, marking the weeks that run into term start, a bank holiday, a planned line closure or a big local event.
```

### deck:using:15

- source: `docs/USING.md` · L30
- under: ### Changing anything
- lang: en
- write-back: yes

```text
Say it. "Raise my all-in ceiling to 2,300." "Dig deeper on crime and management, keep the rest light." "I hate noise." "I always ask whether a cheap flat is cheap for a reason." The assistant shows you exactly what will change, waits for your yes, then applies it. It never changes a setting silently.
```

### deck:using:16

- source: `docs/USING.md` · L33
- under: ### Sharing
- lang: en
- write-back: yes

```text
"Share my seed" gives you a short code and a three-sentence card to post; a friend pastes the code into their own assistant and starts with your preferences and your questions.
```

### deck:using:17

- source: `docs/USING.md` · L36
- under: ### The only three rules to remember
- lang: en
- write-back: yes

```text
- It is a filter. Go and see the flat; talk to the agent and the landlord. You are the princess; it only lifts the mattresses.
```

### deck:using:18

- source: `docs/USING.md` · L37
- under: ### The only three rules to remember
- lang: en
- write-back: yes

```text
- It will say "unknown" and ask you rather than guess. Give it what only you have.
```

### deck:using:19

- source: `docs/USING.md` · L38
- under: ### The only three rules to remember
- lang: en
- write-back: yes

```text
- Never sign on the viewing day.
```

### deck:using:20

- source: `docs/USING.md` · L42
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
**豌豆公主的每一件事都是「打一句話」完成的。** 不用寫程式、不用手改設定檔、不需要任何程式概念。安裝說明裡的「終端機」「Codex」「Claude Code」，其實就是一個打字框：你打句子給助理，助理順便幫你跑查核。如果你完全不想看到終端機，就用聊天軟體（Claude、ChatGPT 等都能上傳同一個 skill），只是慢一點而已。
```

### deck:using:21

- source: `docs/USING.md` · L45
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
1. **安裝**（擇一）：把安裝說明給的一行字貼進助理的打字框；或在聊天軟體的 Skills 頁上傳 zip。完成。
```

### deck:using:22

- source: `docs/USING.md` · L46
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
2. **打**：「這能幹嘛？」你會得到短短的回答和三個開始方式。
```

### deck:using:23

- source: `docs/USING.md` · L47
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
3. **打其中一句**：
```

### deck:using:24

- source: `docs/USING.md` · L48
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
   - 「我 10 月要去倫敦，從零開始，教教我。」
```

### deck:using:25

- source: `docs/USING.md` · L49
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
   - 「我想在東倫敦找一房，含帳單 2,200，11 月 1 日入住。」
```

### deck:using:26

- source: `docs/USING.md` · L50
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
   - 「幫我尻洗（台語，roast）這個房源：」然後貼上房源文字。
```

### deck:using:27

- source: `docs/USING.md` · L51
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
   - 「這是四間短租，幫我尻洗。」然後貼上。
```

### deck:using:28

- source: `docs/USING.md` · L52
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
4. **回答它問的六個問題**（預算、坪數、日期、目的地、地雷、收入審核）。「不知道」也是好答案，它會建議預設值。
```

### deck:using:29

- source: `docs/USING.md` · L53
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
5. **貼它要的東西**：頁面文字、戶型圖、街景截圖。它會一次列清單、附網址，只問一次。
```

### deck:using:30

- source: `docs/USING.md` · L54
- under: ### 五分鐘從頭到尾
- lang: zh-TW
- write-back: yes

```text
6. **看報告**。第一行寫用了哪一級設定；每個數字都寫出處；「未知」就是它不知道，並告訴你怎麼查。
```

### deck:using:31

- source: `docs/USING.md` · L57
- under: ### 每一戶都會回答的問題
- lang: zh-TW
- write-back: yes

```text
每一戶都問同一份問題、同樣的順序：押金幾週、要先付多少、合約上的房東到底是誰、押金放進哪個保管方案、室內面積、能源等級、帳單包含什麼、最短要住多久、什麼時候可以入住。每一題只有三種答案：**文件上有**（旁邊附上那句原文）、**你告訴我們的**（它問了你），或**還不知道**——「還不知道」是沒人查過，不是沒問題。剩下還不知道的，它會一次問你，只問一次。
```

### deck:using:32

- source: `docs/USING.md` · L59
- under: ### 每一戶都會回答的問題
- lang: zh-TW
- write-back: yes

```text
答幾題看你要它查多深：快查答八題（錢和文件那八題），一般答十四題，深查答十八題——多問市政稅是哪一級、要不要住在英國的擔保人、他們的租客審核要你證明什麼、屋裡附哪些家具。你不用選。真要選的話就說「只問把關的八題」或「全部十八題都要」；這兩個開關放在設定檔的**進階**區，剛開始用的人不會被問到。
```

### deck:using:33

- source: `docs/USING.md` · L62
- under: ### 還沒落地就先做這件事
- lang: zh-TW
- write-back: yes

```text
如果你是飛過去的，在看任何一間房子之前先做一件事：把前兩週的床先訂好——旅館或有營運商在管的服務式公寓，錢有保障、想走當天就能走。然後用「六週」而不是「六晚」來抓時間，因為簽約不等於入住：簽完之後還有租客審核、押金進政府保管方案、上一位房客搬走，從落地到拿鑰匙四到七週在九月很常見（作者自己那次是 45 天）。把四件事告訴它——哪天落地、哪天一定要能正常過日子、希望哪天拿鑰匙、短租一週多少錢——它就會寫出一週一列的計畫，並標出哪幾週會撞上開學、國定假日、事先公告的路線停駛，或附近場館的大型活動。
```

### deck:using:34

- source: `docs/USING.md` · L65
- under: ### 想改什麼，用說的
- lang: zh-TW
- write-back: yes

```text
「把含帳單上限改成 2,300。」「治安跟管理挖深一點，其他維持輕量。」「我怕吵。」「我每次都會問：便宜是不是有原因。」助理會先把「哪一項從什麼改成什麼」列給你看，等你說好才改，絕不偷偷改。
```

### deck:using:35

- source: `docs/USING.md` · L68
- under: ### 分享
- lang: zh-TW
- write-back: yes

```text
「分享我的設定檔」會給你一段短碼和三句話的卡片；朋友把短碼貼進自己的助理，就從你的偏好和你的問題開始。
```

### deck:using:36

- source: `docs/USING.md` · L71
- under: ### 只要記得三件事
- lang: zh-TW
- write-back: yes

```text
- 它是篩子。房子要親自去看、要跟仲介和房東聊。你才是豌豆公主，它只負責掀床墊。
```

### deck:using:37

- source: `docs/USING.md` · L72
- under: ### 只要記得三件事
- lang: zh-TW
- write-back: yes

```text
- 它會說「不知道」然後問你，不會亂編。把只有你有的東西給它。
```

### deck:using:38

- source: `docs/USING.md` · L73
- under: ### 只要記得三件事
- lang: zh-TW
- write-back: yes

```text
- 看房當天不簽約。
```

### deck:using:39

- source: `docs/USING.md` · L76
- under: ## 简体中文（摘要）
- lang: zh-CN
- write-back: yes

```text
每件事都是打一句话完成：不用写代码、不用改设置文件。安装是贴一行字或上传 zip；然后打「这能干嘛？」开始。想改设置就用说的，助理会先列出改动、等你说好才改。它是筛子，房子要亲自去看；看房当天不签约。
```

### deck:using:40

- source: `docs/USING.md` · L78
- under: ## 简体中文（摘要）
- lang: zh-CN
- write-back: yes

```text
每一户都答同一份问题（押金、先付多少、房东是谁、面积、账单、最短租期、入住日……）：文件上有（附原文）、你告诉它的，或还不知道；「还不知道」是没人查过，不是没问题，它会一次问你。
```

### deck:using:41

- source: `docs/USING.md` · L80
- under: ## 简体中文（摘要）
- lang: zh-CN
- write-back: yes

```text
还没落地就先做一件事：把前两周的床先订好（旅馆或有运营商在管的服务式公寓，钱有保障、想走当天就能走），再用「六周」而不是「六晚」抓时间——签约不等于入住，签完还有租客审核、押金进政府保管方案、上一位房客搬走，从落地到拿钥匙四到七周在九月很常见（作者自己那次是 45 天）。告诉它四件事：哪天落地、哪天一定要能正常生活、希望哪天拿钥匙、短租一周多少钱，它就写出一周一列的计划，并标出哪几周会撞上开学、国定假日、事先公告的线路停驶或附近场馆的大型活动。
```

### deck:using:42

- source: `docs/USING.md` · L82
- under: ## 简体中文（摘要）
- lang: zh-CN
- write-back: yes

```text
答几题看查多深：快查八题、一般十四题、深查十八题（多问市政税等级、要不要英国担保人、租客审核要你证明什么、附哪些家具）。想自己决定就说「只问把关的八题」或「全部十八题都要」，开关在设置档的**进阶**区，新手不会被问到。
```

---

## docs/INSTALL.md — install page

The intro and every section's prose. The install tables are not in the deck.

### deck:install:1

- source: `docs/INSTALL.md` · L4
- under: # Install (every channel) · 安裝方式（各平台）
- lang: en
- write-back: yes

```text
Verified against vendor documentation on 2026-09-03; product features change, so check the linked pages if a step looks different.
```

### deck:install:2

- source: `docs/INSTALL.md` · L6
- under: # Install (every channel) · 安裝方式（各平台）
- lang: en
- write-back: yes

```text
**Never used a terminal?** You do not need to. Sections B and C need only a chat app; section A is one pasted line and then everything is sentences too. Plain-words walkthrough: `docs/USING.md`.
```

### deck:install:3

- source: `docs/INSTALL.md` · L22
- under: ## A2. Which harness for the plan you already pay for (verified 2026-09-03)
- lang: en
- write-back: yes

```text
The skill does not care which harness runs it. What decides your experience is whether your subscription is allowed inside that harness:
```

### deck:install:4

- source: `docs/INSTALL.md` · L32
- under: ## A2. Which harness for the plan you already pay for (verified 2026-09-03)
- lang: en
- write-back: yes

```text
**Which plan, from the author (personal experience, 2026-09; not a measured result).** At about £20 a month, ChatGPT Plus with Codex gives the most published headroom and the only numbers you can plan with (messages per five-hour window plus a credit rate card); Claude Pro works well in `lite` mode but publishes no usage figures and shares one pool with chat. At the top tier the author's daily experience is that Claude's largest model (Fable 5.1) is markedly stronger than GPT-5.6 Sol on the judgment parts of this work: reading the lowest reviews, naming what sits under a discount, deciding what to ask. That is an opinion from use, not a benchmark: the suite in `bench/` grades facts, not judgment, and the facts come from the scripts, so any model that runs them gets the same numbers. Run the benchmark on the plan you have and decide for yourself.
```

### deck:install:5

- source: `docs/INSTALL.md` · L34
- under: ## A2. Which harness for the plan you already pay for (verified 2026-09-03)
- lang: en
- write-back: yes

```text
On a £20-a-month plan set `budget_mode: lite` in `profile.yaml` (see `skills/vet-flat/references/budget-modes.md`): a single flat takes fewer than ten fetches and still gets the hard filters, the verdict and the two killer questions.
```

### deck:install:6

- source: `docs/INSTALL.md` · L38
- under: ## A3. Subscription or API key?
- lang: en
- write-back: yes

```text
Subscription by default. This workload is cheap in absolute terms at pay-as-you-go prices (a `lite` check of one flat costs a few pence, an area sweep well under £1, a whole search of 20–30 flats and a few sweeps roughly £2–£20 on a mid-size model), so what a subscription buys is not savings but zero setup: no account, card, key, config file or bill to understand. Heavy users on £100+ plans get far more than the equivalent API spend; for this workload that only matters if you already pay for one.
```

### deck:install:7

- source: `docs/INSTALL.md` · L58
- under: ## C. Chat boxes without Skills (manual mode: paste the instructions, attach the references)
- lang: en
- write-back: yes

```text
Use `dist/prompt-pack/` from Releases: `INSTRUCTIONS.md` (the SKILL.md text, under 8,000 characters) plus the reference files.
```

### deck:install:8

- source: `docs/INSTALL.md` · L68
- under: ## C. Chat boxes without Skills (manual mode: paste the instructions, attach the references)
- lang: en
- write-back: yes

```text
In manual mode the skill will list, once, the pages you need to open and paste (see `skills/vet-flat/references/inputs.md`).
```

### deck:install:9

- source: `docs/INSTALL.md` · L71
- under: ## D. Verify
- lang: en
- write-back: yes

```text
Ask: "Vet this flat: <address or postcode>, flat <n>." The first line of the answer states the mode (shell / fetch / manual). The report ends with "Generated with vet-flat <version> — https://github.com/jacky18008/pea-princess".
```

---

## docs/EXPERIMENTS.md — which configuration to run

The intro, and the “What it means” bullets. Result tables and caveats are not in the deck.

### deck:experiments:1

- source: `docs/EXPERIMENTS.md` · L5-L7
- under: # Experiments: which configuration should you run?
- lang: en
- write-back: yes

```text
This page exists so you can choose with evidence instead of vibes. Fifteen configurations of the
same skill were run against the same five real London flats, and every report was scored against a
gold set of problems a human had already found in those flats by reading the documents.
```

### deck:experiments:2

- source: `docs/EXPERIMENTS.md` · L9-L12
- under: # Experiments: which configuration should you run?
- lang: en
- write-back: yes

```text
**The public default is: a cheap model for the extraction workers, the strongest model you have for
the judgment.** On Anthropic that is Sonnet-class workers with an Opus-class judge; on OpenAI, the
mid or small GPT-5.6 model as worker with Sol as judge. The numbers below are here so you can pick
something else, and so you can see what that choice costs you.
```

### deck:experiments:3

- source: `docs/EXPERIMENTS.md` · L407-L414
- under: ## What it means
- lang: en
- write-back: yes

```text
- **Scripts instead of raw web pages cost nothing and save most of the bill.** The clean one-factor
  pair is `B-lean` against `B-raw`: 0.57 recall for $6.70 against 0.58 for $11.70. Identical
  finding rate, 1.7× the money for the raw pages, and the raw arm's spread is much wider (0.20–0.80
  against 0.40–0.78) because a page that loads differently changes the whole run. The big gap
  between `A-legacy` (0.87) and `B-lean` (0.57) is real, but it is not the data path — `A-legacy`
  also runs one reader per axis. That is the next bullet. On the OpenAI side raw pages did appear to
  help (`codex-A-raw-sol` 0.52 against `codex-B-lean-sol` 0.30), but that arm timed out on two of
  five flats, so it is the least trustworthy row in either table.
```

### deck:experiments:4

- source: `docs/EXPERIMENTS.md` · L415-L420
- under: ## What it means
- lang: en
- write-back: yes

```text
- **Breadth is what finds landmines, and breadth is what you pay for.** The two arms that give each
  axis its own reader are the top two: `A-legacy` at 0.87 and `B-readers-sonnet` at 0.69, against
  0.57 for the default. `B-readers-sonnet` also has the highest precision in the Claude table
  (0.96) and the lowest share of unknown axes among the script arms (17% against 29%). It costs
  1.4× the default and 2.2× the wall time; `A-legacy` costs 4.7× and 2.0×. Nothing else in either
  table buys recall the way a second pair of eyes on each axis does.
```

### deck:experiments:5

- source: `docs/EXPERIMENTS.md` · L421-L427
- under: ## What it means
- lang: en
- write-back: yes

```text
- **The worker model does not matter; the judge model matters a little.** Swapping the extraction
  workers from Sonnet to Opus moved recall from 0.57 to 0.63 — inside the noise band — while the
  worker eval says Sonnet is 15/15 against Opus's 14/15 at 42% of the cost. The main model, which
  is the one doing the judging, does move things: Opus 0.71, CLI default 0.57, Sonnet 0.46. Each
  single step is at or inside the noise floor, but the direction is consistent and the ends are
  0.25 apart. Hence the default: cheap where the work is copying a number out of a document, strong
  where the work is deciding what it means.
```

### deck:experiments:6

- source: `docs/EXPERIMENTS.md` · L428-L432
- under: ## What it means
- lang: en
- write-back: yes

```text
- **Budget mode matters more than model size.** `lite` on the strongest main model (`B-lite`, 0.38)
  scores below `standard` on the weakest (`B-main-sonnet`, 0.46), for half the money and 40% of the
  time. The same holds on the OpenAI side, harder: the smallest model in `standard` mode
  (`codex-D-luna-standard`, 0.46) beats the biggest model in `lite` (`codex-C-sol-lite`, 0.13) by
  more than three times. If you have to economise, cut axes, not depth.
```

### deck:experiments:7

- source: `docs/EXPERIMENTS.md` · L433-L438
- under: ## What it means
- lang: en
- write-back: yes

```text
- **Cheap configurations invent numbers.** Fabrications per run climb from 0.30 on the default to
  2.00 on `B-lite` and 2.33 on `C-twenty` — and the cheapest arms' precision stays high, which
  means the invented numbers sit inside findings that otherwise look right. This is why the skill
  makes `scripts/calc.py` do the arithmetic and prints its formula, and why the report contract has
  no place to put a number without a source: `null` and an honest "not known" are always available,
  and the grader counts a guess as a fabrication, not as a near miss.
```

---

## onboarding.md — what the skill says to a new user

The three pitches, the four starting points, the ten-fact primer, the Q&A answers. The intake tables and the distilling rules are model-facing and not in the deck.

### deck:onboarding:1

- source: `skills/vet-flat/references/onboarding.md` · L10
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: en
- write-back: yes

```text
> I check a London rental flat the way a careful surveyor would, using official and open UK data: the government energy certificate (true size, age, heating), police crime data, planning applications next door, the company behind the landlord or agent, deposit and money-protection rules, price against the local band, light, all-in monthly cost, and the commute with a backup line. You get a plain verdict (PASS / EDGE / CONDITIONAL / KILL) with every finding graded by evidence. I never guess: what I cannot reach, I ask you to paste. I can also sweep a whole area around your destination and compare buildings. You set the rules (budget, size, must-haves, deal-breakers), or if you have no idea yet, I explain the basics first and suggest defaults. Works from a chat box or with a full toolset; the report looks the same either way. You are the princess; I only lift the mattresses. I am a filter, not a replacement for viewing the flat and meeting the agent or landlord: they are partners in this, and only you can feel the pea.
```

### deck:onboarding:2

- source: `skills/vet-flat/references/onboarding.md` · L13
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: zh-TW
- write-back: yes

```text
> 我用英國官方與公開資料，像謹慎的驗屋師一樣尻洗（台語，roast）一間倫敦出租公寓：政府能源證書（真實坪數、屋齡、供暖方式）、警方犯罪資料、隔壁的規劃申請案、房東或仲介背後的公司、押金與客戶資金保護規定、價格對照當地行情、採光、每月全部成本、通勤與備援路線。你會得到白話判決（通過／邊緣／有條件／淘汰），每一項發現都標明證據等級。我不猜：拿不到的資料，我會請你貼給我。我也能掃描你目的地周圍整個區域，比較各棟建築。規則由你定（預算、坪數、必要條件、地雷）；完全沒概念也沒關係，我先講基本常識，再建議預設值。在純對話框或有完整工具的環境都能用，報告長得一樣。你才是豌豆公主，我只負責把床墊一層層掀開。我是篩子，不能取代實地看房與見仲介、房東；他們是合作對象，那顆豌豆只有你躺上去才感覺得到。
```

### deck:onboarding:3

- source: `skills/vet-flat/references/onboarding.md` · L16
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: zh-CN
- write-back: yes

```text
> 我用英国官方与公开数据，像谨慎的验房师一样尻洗（台语，roast）一套伦敦出租公寓：政府能源证书（真实面积、楼龄、供暖方式）、警方犯罪数据、隔壁的规划申请、房东或中介背后的公司、押金与客户资金保护规定、价格对照当地行情、采光、每月全部成本、通勤与备用线路。你会得到白话结论（通过／边缘／有条件／淘汰），每一项发现都标明证据等级。我不猜：拿不到的资料，我会请你贴给我。我也能扫描你目的地周围整个区域，比较各栋建筑。规则由你定（预算、面积、必要条件、雷点）；完全没概念也没关系，我先讲基本常识，再建议默认值。在纯对话框或有完整工具的环境都能用，报告长得一样。你才是豌豆公主，我只负责把床垫一层层掀开。我是筛子，不能取代实地看房与见中介、房东；他们是合作对象，那颗豌豆只有你躺上去才感觉得到。
```

### deck:onboarding:4

- source: `skills/vet-flat/references/onboarding.md` · L19
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: en
- write-back: yes

```text
1. **I have a listing** → paste the link or the page text and I roast it (the 12 checks).
```

### deck:onboarding:5

- source: `skills/vet-flat/references/onboarding.md` · L20
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: en
- write-back: yes

```text
2. **I have an area or a place I commute to** → I sweep around it and compare buildings.
```

### deck:onboarding:6

- source: `skills/vet-flat/references/onboarding.md` · L21
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: en
- write-back: yes

```text
3. **I have no idea** → I explain the basics (section 3) and ask six questions (section 2).
```

### deck:onboarding:7

- source: `skills/vet-flat/references/onboarding.md` · L22
- under: ## 1. The pitch (say it in the user's language, at this length)
- lang: en
- write-back: yes

```text
4. **I am about to sign, or I need somewhere for a few weeks first** → the move-in half: bridging stays (`axes/15`), passing the income check (`axes/16`), the first two weeks in the UK (`axes/17`).
```

### deck:onboarding:8

- source: `skills/vet-flat/references/onboarding.md` · L200
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
1. **Timing.** Listings appear about four to eight weeks before the move-in date; good flats go within days. The order is: enquiry → viewing → "referencing" (income and identity checks) → holding deposit → contract → deposit → keys.
```

### deck:onboarding:9

- source: `skills/vet-flat/references/onboarding.md` · L201
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
2. **What you pay.** Rent, plus council tax (full-time students are exempt: Class N), energy, water, broadband. Buildings on a **heat network** (one boiler for the whole building) bill heat separately through a billing company: ask for the tariff in writing before you sign.
```

### deck:onboarding:10

- source: `skills/vet-flat/references/onboarding.md` · L202
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
3. **The law since 2026-05-01**: in-scope private assured tenancies are periodic. No rent before signing; normally **one month's rent in advance** between signing and commencement for monthly rent. Deposit cap **five weeks' rent** (six at £50,000 annual rent), holding deposit **one week**. Identify halls, licences and lodgers separately; axis 07 gives scope, timing and exceptions.
```

### deck:onboarding:11

- source: `skills/vet-flat/references/onboarding.md` · L203
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
4. **The income check.** Landlords usually want yearly income of roughly thirty times the monthly rent, or a guarantor. If you have neither, there are rent-guarantee or "commercial guarantor" services many landlords accept. Ask every landlord first: "which guarantor routes do you accept?"
```

### deck:onboarding:12

- source: `skills/vet-flat/references/onboarding.md` · L204
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
5. **The energy certificate (EPC) is your friend.** It is public, free, and gives the true indoor size, the building's first assessment year (≈ its age) and the heating type. Advertised sizes often include the balcony.
```

### deck:onboarding:13

- source: `skills/vet-flat/references/onboarding.md` · L205
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
6. **Who the landlord is matters more than the brand.** Purpose-built rental buildings are run by companies with on-site management; private landlords vary from excellent to absent. The legal entity on the contract is what counts; the skill looks it up.
```

### deck:onboarding:14

- source: `skills/vet-flat/references/onboarding.md` · L206
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
7. **Money safety.** Never pay anything before you have viewed (in person or on a verified live video) and have a written tenancy. Deposits go to a protection scheme, never to a personal bank account. Requests to move to WhatsApp or to transfer money "to secure it" are a reason to walk.
```

### deck:onboarding:15

- source: `skills/vet-flat/references/onboarding.md` · L207
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
8. **Never sign on the viewing day.** Sleep on it. Ask two questions that could kill the deal (the skill writes them for you).
```

### deck:onboarding:16

- source: `skills/vet-flat/references/onboarding.md` · L208
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
9. **Streets, roads, rails.** Police crime data is public by street; roads and railways are on the map; ask which side the windows face. "Quiet side or road side" is often the same price for two different homes.
```

### deck:onboarding:17

- source: `skills/vet-flat/references/onboarding.md` · L209
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
10. **Where to look.** The big listing portals, the rental operators' own sites, and resident-review sites. The skill tells you exactly what to open and paste; it does not scrape them.
```

### deck:onboarding:18

- source: `skills/vet-flat/references/onboarding.md` · L215
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Only London?** The law is England-wide; the data sources and the crime/commute tooling are London-specific. Elsewhere the method applies with different sources.
```

### deck:onboarding:19

- source: `skills/vet-flat/references/onboarding.md` · L216
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Do you scrape Rightmove / Zoopla / HomeViews?** No. Their terms forbid it. I ask you to paste the page.
```

### deck:onboarding:20

- source: `skills/vet-flat/references/onboarding.md` · L217
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Can I use it on ChatGPT, Gemini, DeepSeek, Grok, Codex?** Yes. With a shell and internet I fetch the data myself; in a chat box I list what to paste, once.
```

### deck:onboarding:21

- source: `skills/vet-flat/references/onboarding.md` · L218
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Where does my data go?** Only to the public sources listed in `references/sources.yaml`, and only what is needed for the lookup. Nothing goes to the author.
```

### deck:onboarding:22

- source: `skills/vet-flat/references/onboarding.md` · L219
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have not landed yet. What first?** Book the bridge before you vet anything: a hotel or an operator-run serviced stay for the first two weeks, and plan for the gap between signing and keys — weeks, not nights (the maintainer's ran 45 days). Then start the search. Two sentences hold whatever the calendar says: never sign or pay for a flat you have not seen, and never sign or pay at the viewing itself — take the agreement away and read it that evening. Then give me four things — the day you land, the day you have to be functioning here, the day you hope for keys (or "no idea"), and what a week of the bridge costs — and I will write the week-by-week plan for the first six weeks, marking which weeks run into term start, a bank holiday, a planned line closure or a local event, with the bridge cost and the cash you need before keys as numbers with their working.
```

### deck:onboarding:23

- source: `skills/vet-flat/references/onboarding.md` · L220
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Something in a document looks off (a postcode, a company name, a date).** One doubt does not stop the search: name it in one line, give the one check that settles it (the register, the sponsor list, the certificate), and carry on with the flat. Never turn the conversation into an investigation, and never offer to open the user's mailbox, files or accounts to settle it — ask them to paste.
```

### deck:onboarding:24

- source: `skills/vet-flat/references/onboarding.md` · L221
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **My short let is bad (damp, mould, not as described) and I want out tonight.** One message, four parts: a stay of a few nights or weeks is a **licence, not a tenancy** — no deposit scheme, no notice period; your money comes back through the platform's refund route and, failing that, the card or consumer route, never by leaving quietly. Message the host on the platform now, with dated photos, asking for a move or a refund of the unused nights. Book tonight's bed at a hotel with free cancellation and pay at property. For the next stay of a week or more: **see it, or verify it live on video, before paying** — a stay nobody has seen is the bridge's most expensive mistake.
```

### deck:onboarding:25

- source: `skills/vet-flat/references/onboarding.md` · L222
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have just landed. Where do I sleep this week?** For the first one or two weeks a hotel or an operator-run serviced stay is the safer default: your money is protected, you can leave at once, and someone is responsible. A private short let is fine once you have seen it. It costs more per night and often has no kitchen; the skill will price both.
```

### deck:onboarding:26

- source: `skills/vet-flat/references/onboarding.md` · L223
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **What can it not do?** It cannot smell the hallway, hear the road at 2 a.m., or feel whether the street is yours. It says "unknown" where it does not know and asks you for what only you can supply: the floor plan, a street-view screenshot, your impression on the day.
```

### deck:onboarding:27

- source: `skills/vet-flat/references/onboarding.md` · L224
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How does a reply end?** With the one thing still open for you — the question you asked that I could not answer yet and the one check that would settle it — never with another list of questions.
```

### deck:onboarding:28

- source: `skills/vet-flat/references/onboarding.md` · L225
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Does it decide for me?** No. It gives a verdict with the evidence behind it; you decide, after viewing the flat and meeting the people who let it. Landlords and agents are partners here, not opponents.
```

### deck:onboarding:29

- source: `skills/vet-flat/references/onboarding.md` · L226
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How accurate is it?** Facts come from official registers and are graded; anything unknown is shown as unknown, never filled in.
```

### deck:onboarding:30

- source: `skills/vet-flat/references/onboarding.md` · L227
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **What does a report look like?** A verdict card, your must-haves versus the flat, a comparison table, the worst reviews, the landmines, the twelve checks, questions for the viewing, what could not be found, and the sources with dates.
```

---

## sharing.md — social posts and the card description

The three social posts, the two questions worth copying, and what to say to somebody importing another person's seed. The rest of the file is model-facing.

### deck:sharing:1

- source: `skills/vet-flat/references/sharing.md` · L72-L73
- under: ## 3. Share your questions
- lang: en
- write-back: yes

```text
> If this is unusually cheap or unusually good next to its neighbours, what is the hidden problem?
> Cheap has a reason.
```

### deck:sharing:2

- source: `skills/vet-flat/references/sharing.md` · L75
- under: ## 3. Share your questions
- lang: en
- write-back: yes

```text
> If it is pricier, am I buying visible value I actually care about, or just paying more?
```

### deck:sharing:3

- source: `skills/vet-flat/references/sharing.md` · L111-L116
- under: ## 4. The social post, ready to send
- lang: en
- write-back: yes

```text
> I found a flat in London with this Pea Princess seed — paste it into any AI agent that has the
> skill and it will check flats the way mine did: PP1.…
>
> What it means: [three sentences from the card]
> What I asked of every flat: [the questions]
> What I found: 14 flats vetted — 2 PASS, 3 EDGE, 9 KILL.
```

### deck:sharing:4

- source: `skills/vet-flat/references/sharing.md` · L120-L125
- under: ## 4. The social post, ready to send
- lang: zh-TW
- write-back: yes

```text
> 我用這組「豌豆公主」條件碼在倫敦找到房子了——把它貼給任何裝了這個技能的 AI 代理，
> 它就會照我的標準幫你審房：PP1.…
>
> 這組條件是什麼意思：〔卡片上的三句話〕
> 我要求每間房都回答的問題：〔你的問題〕
> 結果：看了 14 間，2 間通過、3 間邊緣、9 間淘汰。
```

### deck:sharing:5

- source: `skills/vet-flat/references/sharing.md` · L129-L134
- under: ## 4. The social post, ready to send
- lang: zh-CN
- write-back: yes

```text
> 我用这组「豌豆公主」条件码在伦敦找到房子了——把它贴给任何装了这个技能的 AI 代理，
> 它就会照我的标准帮你审房：PP1.…
>
> 这组条件是什么意思：〔卡片上的三句话〕
> 我要求每套房都回答的问题：〔你的问题〕
> 结果：看了 14 套，2 套通过、3 套边缘、9 套淘汰。
```

### deck:sharing:6

- source: `skills/vet-flat/references/sharing.md` · L185-L189
- under: ## 6. Importing somebody else's seed
- lang: en
- write-back: yes

```text
> This is somebody else's taste, not a recommendation. Their budget band, their district and their
> month are comments in the file, not your numbers — tell me yours. Read their deal-breakers and
> their questions and keep the ones you agree with; delete the rest. If their three-sentence summary
> is not about you, delete it and I will ask you about the places you have lived instead
> (`references/onboarding.md`, section 2b).
```

---

## inputs.md — the one message that asks the user for what is missing

The ask template only. The per-axis table is model-facing.

### deck:inputs:1

- source: `skills/vet-flat/references/inputs.md` · L58-L66
- under: ## Template for the ask (copy, fill, send once)
- lang: en
- write-back: yes

```text
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

---

## profiles/ — the sentences a profile carries

`story_summary`, `self_intro_template` and the `my_questions` texts. Keep the YAML shape: the key, the indent and the quotes are part of the block.

### deck:example-quiet-postgraduate-one-bed:1

- source: `skills/vet-flat/profiles/example-quiet-postgraduate-one-bed.yaml` · L64
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "If this flat is unusually cheap, unusually good or unusually available next to its neighbours, what is the hidden problem? Cheap has a reason."
```

### deck:example-quiet-postgraduate-one-bed:2

- source: `skills/vet-flat/profiles/example-quiet-postgraduate-one-bed.yaml` · L68
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "If it is pricier than its neighbours, am I buying visible value I actually care about (quiet side, floor, light, management), or just paying more?"
```

### deck:example-quiet-postgraduate-one-bed:3

- source: `skills/vet-flat/profiles/example-quiet-postgraduate-one-bed.yaml` · L101-L102
- under: self_intro_template:
- lang: en
- write-back: yes

```text
  I am a full-time postgraduate student looking for a home for one person, non-smoking, no pets,
  able to provide proof of funds, with a rent guarantee product for the income check.
```

### deck:example-quiet-postgraduate-one-bed:4

- source: `skills/vet-flat/profiles/example-quiet-postgraduate-one-bed.yaml` · L105-L109
- under: story_summary:
- lang: en
- write-back: yes

```text
  Moved to London for a one-year course after years of city-flat living, and cares more about sleeping
  well and a home that runs itself than about views. Has been burned by a damp lower-ground short let,
  by an advertised size that included the balcony, and by bills that only appeared after signing.
  Would rather pay a little more for a quiet side, a real bedroom door and someone who answers when
  the heating fails.
```

### deck:example-solo-engineer-one-bed:1

- source: `skills/vet-flat/profiles/example-solo-engineer-one-bed.yaml` · L49
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "Would I feel fine walking from the station to the door alone at 11 pm? What is on that route?"
```

### deck:example-solo-engineer-one-bed:2

- source: `skills/vet-flat/profiles/example-solo-engineer-one-bed.yaml` · L53
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "Who exactly am I renting from, and can I verify them before I hand over any money?"
```

### deck:example-solo-engineer-one-bed:3

- source: `skills/vet-flat/profiles/example-solo-engineer-one-bed.yaml` · L57
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "If this is cheaper than its neighbours, what is the reason?"
```

### deck:example-solo-engineer-one-bed:4

- source: `skills/vet-flat/profiles/example-solo-engineer-one-bed.yaml` · L99-L100
- under: self_intro_template:
- lang: en
- write-back: yes

```text
  I am a software engineer employed full-time in London, looking for a home for one person,
  non-smoking, no pets, with payslips and a contract for the income check.
```

### deck:example-solo-engineer-one-bed:5

- source: `skills/vet-flat/profiles/example-solo-engineer-one-bed.yaml` · L103-L106
- under: story_summary:
- lang: en
- write-back: yes

```text
  Moving to London for a first job in the UK and renting alone for the first time. Wants a home that
  feels safe to come back to late, a bedroom that is dark and quiet, and a landlord who can be
  verified before any money moves. Has read enough scam warnings to refuse to pay before a viewing,
  and would rather pay a little more for a staffed building than save on a street that feels empty.
```

### deck:example-student-shared-room:1

- source: `skills/vet-flat/profiles/example-student-shared-room.yaml` · L47
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "Is everyone in this household a full-time student, and is the tenancy joint or individual?"
```

### deck:example-student-shared-room:2

- source: `skills/vet-flat/profiles/example-student-shared-room.yaml` · L51
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "Are bills really included, and is there a cap after which I pay?"
```

### deck:example-student-shared-room:3

- source: `skills/vet-flat/profiles/example-student-shared-room.yaml` · L55
- under: my_questions:
- lang: en
- write-back: yes

```text
  - text: "If this room is cheaper than the others on the street, why?"
```

### deck:example-student-shared-room:4

- source: `skills/vet-flat/profiles/example-student-shared-room.yaml` · L93-L94
- under: self_intro_template:
- lang: en
- write-back: yes

```text
  I am a full-time student looking for a room in a shared flat, non-smoking, no pets, able to
  provide proof of funds, with a rent guarantee product for the income check.
```

### deck:example-student-shared-room:5

- source: `skills/vet-flat/profiles/example-student-shared-room.yaml` · L97-L99
- under: story_summary:
- lang: en
- write-back: yes

```text
  First time renting abroad, on a student budget, and would rather share a well-run flat near the
  campus than live alone far out. Has heard enough about deposits vanishing and bills surprises to
  insist on a protected deposit and a written answer on what "bills included" means.
```

---

## seed.py — the seed card sentences (read-only here)

Fragments the card assembles at run time; `%s` is filled in from the profile. Shown verbatim as Python literals. Write-back is off for this file — edit it in the source.

### deck:seed:1

- source: `skills/vet-flat/scripts/seed.py` · L589
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"a flat"
```

### deck:seed:2

- source: `skills/vet-flat/scripts/seed.py` · L591
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"on floors %s"
```

### deck:seed:3

- source: `skills/vet-flat/scripts/seed.py` · L593
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"with windows facing %s"
```

### deck:seed:4

- source: `skills/vet-flat/scripts/seed.py` · L595
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"within reach of %s"
```

### deck:seed:5

- source: `skills/vet-flat/scripts/seed.py` · L600
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I want %s"
```

### deck:seed:6

- source: `skills/vet-flat/scripts/seed.py` · L602
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"; it must have %s"
```

### deck:seed:7

- source: `skills/vet-flat/scripts/seed.py` · L604
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"; and I rank %s in that order"
```

### deck:seed:8

- source: `skills/vet-flat/scripts/seed.py` · L609
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"a ground-floor flat"
```

### deck:seed:9

- source: `skills/vet-flat/scripts/seed.py` · L611
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"windows that cannot see sky"
```

### deck:seed:10

- source: `skills/vet-flat/scripts/seed.py` · L612
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I have no absolute deal-breakers."
```

### deck:seed:11

- source: `skills/vet-flat/scripts/seed.py` · L612
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I will not take: %s."
```

### deck:seed:12

- source: `skills/vet-flat/scripts/seed.py` · L617
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price leads: I take the cheapest home that clears every rule above"
```

### deck:seed:13

- source: `skills/vet-flat/scripts/seed.py` · L619-L620
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price is not in my top three: I will pay to the top of the band for a benefit "
                 "I can name"
```

### deck:seed:14

- source: `skills/vet-flat/scripts/seed.py` · L622-L623
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price sits %s of my three priorities: I will pay towards the top of the band for "
                 "a benefit I can name"
```

### deck:seed:15

- source: `skills/vet-flat/scripts/seed.py` · L624
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
", and quiet wins when quiet and light conflict."
```

### deck:seed:16

- source: `skills/vet-flat/scripts/seed.py` · L625
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
", and I would rather have light than silence."
```

### deck:seed:17

- source: `skills/vet-flat/scripts/seed.py` · L627
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
" I plan on %s."
```

### deck:seed:18

- source: `skills/vet-flat/scripts/seed.py` · L631
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
" I ask of every flat: \u201c%s\u201d"
```

### deck:seed:19

- source: `skills/vet-flat/scripts/seed.py` · L738
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"what I found: %d flat%s vetted"
```

### deck:seed:20

- source: `skills/vet-flat/scripts/seed.py` · L746
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"the one I took"
```

### deck:seed:21

- source: `skills/vet-flat/scripts/seed.py` · L750
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"about %s m²"
```

### deck:seed:22

- source: `skills/vet-flat/scripts/seed.py` · L763
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"Pea Princess seed"
```

### deck:seed:23

- source: `skills/vet-flat/scripts/seed.py` · L767
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"my search preferences; review the free text for personal details before sharing."
```

### deck:seed:24

- source: `skills/vet-flat/scripts/seed.py` · L778-L779
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"seed code (paste it into any AI agent that has the Pea Princess skill, "
               "and it will set itself up the way I did):"
```

### deck:seed:25

- source: `skills/vet-flat/scripts/seed.py` · L782-L783
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"(the code leaves out the %s to stay short enough to paste; it is on the card "
                   "above)"
```
