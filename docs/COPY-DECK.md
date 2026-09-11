# Copy deck — Pea Princess (`pea-princess`)

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
| README — the front page | 20 | `README.md` |
| docs/USING.md — the plain-words walkthrough | 38 | `docs/USING.md` |
| docs/INSTALL.md — install page | 11 | `docs/INSTALL.md` |
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
- under: # Pea Princess · 豌豆公主 (`pea-princess`)
- lang: en
- write-back: yes

```text
**EN** — A vendor-neutral agent skill that vets a London rental flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, total monthly cost and commute, from official and open UK data, ending in a plain-language verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (Claude Code, Codex, Gemini CLI, Grok CLI, Cursor, Copilot, OpenCode, Cline, Goose, OpenHands, Kimi Code, Qwen Code, pi, OpenClaw, Hermes Agent…) and, in reduced modes, with chat products that cannot run scripts.
```

### deck:readme:2

- source: `README.md` · L5
- under: # Pea Princess · 豌豆公主 (`pea-princess`)
- lang: zh-TW
- write-back: yes

```text
**繁中** — 這是一個不綁定任何廠商的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣尻洗（台語，roast）一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出白話判決。任何支援 Agent Skills 格式的 agent 都能用；只能對話不能跑程式的產品也能用「精簡模式」。
```

### deck:readme:3

- source: `README.md` · L7
- under: # Pea Princess · 豌豆公主 (`pea-princess`)
- lang: en
- write-back: yes

```text
> Status: **draft**. Local collection, area sweep, report rendering and experiment harnesses are implemented. Read [security and privacy boundaries](SECURITY.md) before handling personal data or building a release. Usage: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.
```

### deck:readme:4

- source: `README.md` · L9
- under: # Pea Princess · 豌豆公主 (`pea-princess`)
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
The skill is installed and invoked as **`pea-princess`**; the upload artifact is `dist/pea-princess-skill.zip`. The repository still stores its source in `skills/vet-flat/` so existing script paths and experiment records remain valid. This is one skill, with one installed name.
```

### deck:readme:6

- source: `README.md` · L28
- under: # claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
- lang: en
- write-back: yes

```text
Codex: enable sandbox network (`sandbox_workspace_write.network_access = true`) or use manual mode.
```

### deck:readme:7

- source: `README.md` · L31
- under: ## Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
All in `skills/vet-flat/scripts/`; each prints one JSON object with `source_url`, `retrieved_at`, `http_status`, `ok` and an evidence class. Usage details: `docs/SCRIPTS.md`.
```

### deck:readme:8

- source: `README.md` · L46
- under: ## Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON.
```

### deck:readme:9

- source: `README.md` · L49
- under: ## Why "Pea Princess"
- lang: en
- write-back: yes

```text
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.
```

### deck:readme:10

- source: `README.md` · L52
- under: ## No code required · 不用會寫程式
- lang: en
- write-back: yes

```text
Everything is done by typing or dictating sentences: install (one pasted line, or a zip upload in a chat app), then ask, paste what it asks for, read the report, and change any setting by saying it. [The walkthrough](docs/USING.md) explains it in English and Chinese.
```

### deck:readme:11

- source: `README.md` · L54
- under: ## No code required · 不用會寫程式
- lang: zh-TW
- write-back: yes

```text
**Prefer speaking? · 不想打字？** Use your device's built-in dictation, or an optional app such as Typeless or Wispr Flow, to put your words into the assistant's text box. 可以直接口述需求、住屋經驗或中途補充，不用先整理成表單。See [voice input and free-plan limits](docs/USING.md#speak-instead-of-typing).
```

### deck:readme:12

- source: `README.md` · L57
- under: ## Start here, on any platform
- lang: en
- write-back: yes

```text
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, `budget_mode` lite/standard/deep for £20 plans and chat-only use). The hard follow-up questions the agent must ask are in `references/questions.md`.
```

### deck:readme:13

- source: `README.md` · L60
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.
```

### deck:readme:14

- source: `README.md` · L62
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Which configuration to run:** `docs/EXPERIMENTS.md` records the original flat-vetting comparisons. The [later context ablation](docs/ablation-2026-09-09/results.md) includes generation costs and source reviews: extra summarization, structured memory and multiple retrieval calls did not save tokens at the tested sizes. Keep one agent with full context as the starting point; the four-role pipeline remains experimental. These studies measure different tasks, not a universal model ranking.
```

### deck:readme:15

- source: `README.md` · L64
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Long-running projects and changing requirements:** the [session harness](docs/session-harness.md) saves exact user requests, revisioned requirements and conditional exceptions, source snapshots, goals, TODOs and execution state. The managed runner inserts the current packet itself and rejects stale results. Short `AGENTS.md` / `CLAUDE.md` files link to detailed rules; pointers alone cannot ensure reading. [Lifecycle validation](docs/session-harness-validation.md) tests recovery without new model calls, not quality equivalence or token savings.
```

### deck:readme:16

- source: `README.md` · L66
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Try a whole persona conversation:** run `python3 tools/persona_playground.py` and open the printed local URL. The [interactive lab](docs/persona-playground.md) uses your local Codex login for dynamic persona replies and assistant answers, with step/run/pause, queued human questions, scenario amendments, private history and shared usage ceilings. All 16 cards are available in a clearly labelled chat adaptation; this is a local alpha, with no public deployment or hidden model judge.
```

### deck:readme:17

- source: `README.md` · L68
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Community feedback, stage 1:** open the [local options form](community/index.html) and follow the [guide](docs/community-feedback-stage1.md). Public JSON contains controlled choices; optional text stays on the author's device. Local validation, import and search use a fictional demo catalog. There is no online submission service or real review dataset yet.
```

### deck:readme:18

- source: `README.md` · L70
- under: ## Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Whole conversations, not one answer:** `docs/JOURNEYS.md` scores nine scripted multi-turn journeys, and `docs/PERSONAS.md` goes one step further — sixteen fictional people played by a model, with a deterministic controller holding their documents so nothing can be invented, a judge that has to quote its evidence, and a paired probe per person that moves exactly one setting. `python3 bench/personas.py --matrix pilot --dry-run` prints the whole plan without calling a model.
```

### deck:readme:19

- source: `README.md` · L78
- under: ## Sources you will not find here
- lang: en
- write-back: yes

```text
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com are listed by name only. Their terms forbid automated access, so this project gives no method for them; the skill asks you for the page (a PDF, screenshots or the text) and does not open listing links itself.
```

### deck:readme:20

- source: `README.md` · L81
- under: ## Licence and attribution (proposed)
- lang: en
- write-back: yes

```text
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with pea-princess <version> — <source URL>". Please keep it.
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
Tell the assistant what you want to understand. You do not need to write code, complete a questionnaire or choose technical settings before it can help.
```

### deck:using:2

- source: `docs/USING.md` · L9
- under: ## English
- lang: en
- write-back: yes

```text
After installing the skill using the [installation guide](INSTALL.md), try:
```

### deck:using:3

- source: `docs/USING.md` · L11
- under: ## English
- lang: en
- write-back: yes

```text
- “I'm moving to London in October. Show me some examples and explain how to choose.”
```

### deck:using:4

- source: `docs/USING.md` · L12
- under: ## English
- lang: en
- write-back: yes

```text
- “I want a quiet one-bedroom home. My total monthly cost, including rent and bills, should stay below £2,200.”
```

### deck:using:5

- source: `docs/USING.md` · L13
- under: ## English
- lang: en
- write-back: yes

```text
- “Compare these two listings, and tell me what to check at a viewing.”
```

### deck:using:6

- source: `docs/USING.md` · L14
- under: ## English
- lang: en
- write-back: yes

```text
- “Pause the comparison: what does a guarantor do?”
```

### deck:using:7

- source: `docs/USING.md` · L16
- under: ## English
- lang: en
- write-back: yes

```text
It starts with useful examples or the evidence you provide, explains a trade-off, and learns what matters from your reaction. Usually it asks zero to two questions at a time, never more than three essential clarifications. You can say “not sure”. A complete set of preferences is not required before making progress.
```

### deck:using:8

- source: `docs/USING.md` · L18
- under: ## English
- lang: en
- write-back: yes

```text
The assistant uses real rental examples with source links and dates. A public advert is not a guarantee of availability. If a source cannot be reached, it continues with supported information and asks for the missing extract; it does not switch to fictional homes. Invented teaching examples are used only if you request them. Your assistant may need you to paste a listing or attach a floor plan. It explains what is needed and why, while continuing other checks. If your app supports a choice panel, it can use that; otherwise you answer in ordinary text.
```

### deck:using:9

- source: `docs/USING.md` · L22
- under: ### Speak instead of typing
- lang: en
- write-back: yes

```text
If speaking is easier, use your device's built-in dictation or an app you already like to enter text in the assistant's chat box. [Typeless](https://www.typeless.com/pricing) and [Wispr Flow](https://wisprflow.ai/pricing) are optional examples; both list free plans with usage limits, which vary by plan or platform (checked 11 September 2026). Check the linked pages for current allowances; installing or paying for another app is not required.
```

### deck:using:10

- source: `docs/USING.md` · L24
- under: ### Speak instead of typing
- lang: en
- write-back: yes

```text
Describe what you want, a home you liked or disliked, or a change of mind in your own words. You do not need to prepare a polished prompt or a form. Before sending, glance at names, postcodes, amounts, dates and words such as “not” or “only if” so a transcription error does not change your conditions. This is speech-to-text input; it does not require the assistant to support a voice call.
```

### deck:using:11

- source: `docs/USING.md` · L28
- under: ### Learn by comparing
- lang: en
- write-back: yes

```text
Start with differences you can react to: a shorter commute versus more space, a quiet bedroom versus a busy road, lower rent versus uncertain bills. The assistant explains the likely consequences, then helps you inspect the evidence or prepare a viewing check. You can ask about London areas, rental budgets, paperwork or common problems whenever they become relevant. Current market and legal claims need current sources.
```

### deck:using:12

- source: `docs/USING.md` · L32
- under: ### Read the recommendation
- lang: en
- write-back: yes

```text
The answer begins with what to do next and why. Numbers keep their source and uncertainty: “landlord estimate: 20 minutes, not checked” is different from a journey planner prediction for your destination and arrival time. A quote matching the landlord's message does not prove the claim is true. Unknown information remains unknown; a low estimate alone does not confirm that a home meets your limit.
```

### deck:using:13

- source: `docs/USING.md` · L34
- under: ### Read the recommendation
- lang: en
- write-back: yes

```text
A fuller report covers the money, paperwork, size, bills, move-in timing and other checks relevant to the home. These are things the assistant works through, not a form you must fill out before it helps. It asks for the few missing items that matter next and keeps other gaps visible.
```

### deck:using:14

- source: `docs/USING.md` · L38
- under: ### Change your mind or interrupt
- lang: en
- write-back: yes

```text
Say “Raise my total monthly limit to £2,300”, “Quiet matters more than light”, or “A longer commute is okay, but never over 45 minutes”. The assistant applies clear instructions, explains the effect in plain words and preserves conditions and previous requirements. It asks only when your meaning is materially ambiguous or it proposes a change itself.
```

### deck:using:15

- source: `docs/USING.md` · L40
- under: ### Change your mind or interrupt
- lang: en
- write-back: yes

```text
Ask a side question at any point. It should answer it, keep the original work available, and resume without making you repeat your preferences. Saving across conversations depends on the host's file and memory support; the assistant must say when it cannot save something.
```

### deck:using:16

- source: `docs/USING.md` · L44
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
Compare temporary accommodation if it would give you time to view longer-term homes. Check actual cancellation, payment and departure terms; no accommodation type guarantees a refund or same-day exit. Build an arrival plan from your dates and verified costs, leaving gaps explicit.
```

### deck:using:17

- source: `docs/USING.md` · L46
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
Use the report to decide what to investigate, then see the flat and speak with the agent or landlord. Take the agreement away to read; do not sign at the viewing. The assistant gives legal and payment guidance at the decision it affects, with the applicable date and agreement type.
```

### deck:using:18

- source: `docs/USING.md` · L48
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
**Your own little secretary.** Anything personal or local that the shared skill does not check — the walk to your gym, a school's catchment, a noise source you know about, a data set you trust — goes into `extensions/` in your copy as a one-page add-on (there is a template). Add-ons are labelled in the report, never change the verdict by themselves, read no listing or review sites, and never describe an area by who lives there.
```

### deck:using:19

- source: `docs/USING.md` · L52
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
不用寫程式，也不用先填完整問卷或挑技術設定。按照[安裝說明](INSTALL.md)加入技能後，可以直接說：
```

### deck:using:20

- source: `docs/USING.md` · L54
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
- 「我十月要去倫敦，先給我例子，教我怎麼挑。」
```

### deck:using:21

- source: `docs/USING.md` · L55
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
- 「我想找安靜的一房，每月總花費（房租加帳單）不要超過 £2,200。」
```

### deck:using:22

- source: `docs/USING.md` · L56
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
- 「比較這兩間，告訴我看房時要查什麼。」
```

### deck:using:23

- source: `docs/USING.md` · L57
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
- 「先插問一下：擔保人是做什麼的？」
```

### deck:using:24

- source: `docs/USING.md` · L59
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
助理會先用例子或你提供的房源做出有用的比較，再從你的反應了解偏好。通常一次問零到兩題，必要確認最多三題；「還不知道」也可以，不必先把所有條件想清楚。
```

### deck:using:25

- source: `docs/USING.md` · L61
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
能搜尋時，真實房源會附來源與日期；不能搜尋時，教學例子會明確標示為虛構，不會把假設價格說成倫敦現在的行情。需要你貼房源、戶型圖或其他文件時，會說明用途，並繼續做不受影響的部分。聊天軟體有選項介面就用選項，沒有就直接打字。
```

### deck:using:26

- source: `docs/USING.md` · L63
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
**不想打字，可以用語音輸入。** 用手機或電腦內建的聽寫，或你習慣的語音轉文字工具，把內容輸入助理的對話框即可；[Typeless](https://www.typeless.com/pricing) 和 [Wispr Flow](https://wisprflow.ai/pricing) 都是可選例子。兩者目前都有免費方案，但有用量限制，依平台與方案而異（2026-09-11 查核，最新額度看官方頁面）；不需要為了使用這個 skill 另外安裝或付費。
```

### deck:using:27

- source: `docs/USING.md` · L65
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
可以直接說需求、過去住過的好房子或雷點，也能中途改主意，不用先整理成表單或漂亮的提示詞。送出前看一下校名、郵遞區號、金額、日期，以及「不要」「只有……才可以」有沒有辨識正確。這是把聲音轉成文字，不要求助理本身支援語音通話。
```

### deck:using:28

- source: `docs/USING.md` · L67
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
可以先比較「通勤近一點，還是空間大一點」、「臥室安靜，還是生活機能方便」、「租金低一點，還是帳單比較確定」。邊看邊問倫敦的區域、預算、租屋流程或常見問題，也可以請助理教你如何在看房時查證。涉及目前行情或法律的說法，應附上查過的來源。
```

### deck:using:29

- source: `docs/USING.md` · L69
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
答案先說下一步和理由。數字會保留來源與限制：「房東估計通勤 20 分鐘，還沒查證」不等於實際通勤已確認；逐字核對房東訊息，也不代表內容一定正確。每月總花費會說明房租、能源、水、網路與適用的市政稅哪些已知、哪些只是估計。
```

### deck:using:30

- source: `docs/USING.md` · L71
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
中途改條件直接說：「總預算提高到 £2,300」、「安靜比採光重要」、「通勤可以久一點，但超過 45 分鐘就不要」。助理會套用明確指示，用白話說明影響，保留例外和其他條件；不需要再確認同一個要求。只有意思不明確，或助理自己提議修改時，才需要釐清。
```

### deck:using:31

- source: `docs/USING.md` · L73
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
隨時可以插問其他問題，再回到原本的找房工作，不必重新交代偏好。跨對話保存取決於你使用的軟體；助理不能假裝已經存好。
```

### deck:using:32

- source: `docs/USING.md` · L75
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
還沒抵達時，可以比較暫住方案，替實地看房留時間。取消、退款和退房條件都要看實際條款，不能只因為是旅館或服務式公寓就當成有保障。看房時親自確認環境、和仲介或房東談清楚；合約帶回去讀，看房當天不簽約。法律與付款提醒會放在相關決定旁，不會每次開場都貼一整段。
```

### deck:using:33

- source: `docs/USING.md` · L77
- under: ## 繁體中文
- lang: zh-TW
- write-back: yes

```text
**自己的小秘書。** 共用技能沒查、但你在意的東西，例如到健身房的步行時間、學區、你知道的噪音來源、你信任的資料集，寫成一頁放進你自己那份的 `extensions/` 資料夾（有範本）。這些加購項目在報告裡會標示出來、不會自己改變判決、不讀房源和評價網站、也不用「住的是誰」來描述一個地區。
```

### deck:using:34

- source: `docs/USING.md` · L81
- under: ## 简体中文
- lang: zh-CN
- write-back: yes

```text
直接聊天就能开始，不用先填问卷。可以说「先给我例子，教我怎么挑」，或贴两套房源请助理比较。它会先做有用的分析，再从你的反应了解偏好；通常一次问零到两题，必要确认最多三题。支持选项界面时使用真实选项，没有就直接打字。
```

### deck:using:35

- source: `docs/USING.md` · L83
- under: ## 简体中文
- lang: zh-CN
- write-back: yes

```text
**不想打字，可以用语音输入。** 使用设备内置的听写或你习惯的语音转文字工具，将内容输入助理的聊天框；[Typeless](https://www.typeless.com/pricing) 和 [Wispr Flow](https://wisprflow.ai/pricing) 是可选例子。两者目前都有免费方案，但有用量限制，依平台和方案而异（2026-09-11 查核，最新额度看官方页面），不必另行安装或付费。直接说需求、住屋经历或临时改动即可；发送前核对名称、邮编、金额、日期及否定词、附带条件。无需先填表，也不要求助理支持语音通话。
```

### deck:using:36

- source: `docs/USING.md` · L85
- under: ## 简体中文
- lang: zh-CN
- write-back: yes

```text
每月总花费包括房租和账单；数字会说明来源、哪些只是估计。真实房源需要来源与日期，不能搜索时的教学例子会标成虚构。你可以随时插问、改变预算或增加条件，助理应保留原本的工作，不让你重新填写全部资料。跨对话保存取决于软件能力，不能假装已经保存。
```

### deck:using:37

- source: `docs/USING.md` · L87
- under: ## 简体中文
- lang: zh-CN
- write-back: yes

```text
先用比较学会取舍，再安排查证和看房。退款、付款、签约规则要看实际条款与适用法律；合约带回去读，看房当天不签约。
```

### deck:using:38

- source: `docs/USING.md` · L89
- under: ## 简体中文
- lang: zh-CN
- write-back: yes

```text
**自己的小秘书。** 共用技能没查、但你在意的东西，例如到健身房的步行时间、学区、你知道的噪音来源、你信任的数据集，写成一页放进你自己那份的 `extensions/` 文件夹（有模板）。这些加购项目在报告里会标示出来、不会自己改变判决、不读房源和评价网站、也不用「住的是谁」来描述一个地区。
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

- source: `docs/INSTALL.md` · L72
- under: ## D. Local package and existing installations
- lang: en
- write-back: yes

```text
`python3 tools/build_dist.py` creates `dist/pea-princess-skill.zip` with one root folder, `pea-princess/`. Install that folder in your agent's skills directory, such as `~/.agents/skills/pea-princess/`; invoke it as `$pea-princess` in Codex.
```

### deck:install:10

- source: `docs/INSTALL.md` · L74
- under: ## D. Local package and existing installations
- lang: en
- write-back: yes

```text
If you installed the former `vet-flat` package, preserve that directory outside every agent skills directory before installing the replacement. Keep only `pea-princess` discoverable, then reload the agent's skill list or start a new session. The source tree still uses `skills/vet-flat/` for existing script imports and historical tests; that internal path is not an additional installed skill. Existing report/schema identifiers remain readable.
```

### deck:install:11

- source: `docs/INSTALL.md` · L77
- under: ## E. Verify
- lang: en
- write-back: yes

```text
Ask: "Vet this flat: <address or postcode>, flat <n>." The first line of the answer states the mode (shell / fetch / manual). The report ends with "Generated with pea-princess <version> — https://github.com/jacky18008/pea-princess".
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

- source: `skills/vet-flat/references/onboarding.md` · L14
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
> A lower advertised rent can lose its advantage once the bills and daily journey are included. I help you compare that whole picture, spot the checks that could change your choice, and find a sensible next step from a listing or a rough idea.
```

### deck:onboarding:2

- source: `skills/vet-flat/references/onboarding.md` · L17
- under: ## 1. The pitch (only when asked what this does)
- lang: zh-TW
- write-back: yes

```text
> 房租比較便宜，加上帳單與每天的交通，未必就是更划算的選擇。我會陪你把這些差別看清楚，找出真正會影響決定的問題；有房源就從房源看起，只有模糊想法也能開始。
```

### deck:onboarding:3

- source: `skills/vet-flat/references/onboarding.md` · L20
- under: ## 1. The pitch (only when asked what this does)
- lang: zh-CN
- write-back: yes

```text
> 房租比较便宜，加上账单与每天的交通，未必就是更划算的选择。我会陪你把这些差别看清楚，找出真正会影响决定的问题；有房源就从房源看起，只有模糊想法也能开始。
```

### deck:onboarding:4

- source: `skills/vet-flat/references/onboarding.md` · L23
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
1. **I have a listing** → give me the page as a PDF, screenshots or copied text (a link alone carries no photos or floor plan, and I do not open listing sites) and I roast it (the 12 checks).
```

### deck:onboarding:5

- source: `skills/vet-flat/references/onboarding.md` · L24
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
2. **I have an area or a place I commute to** → I sweep around it and compare buildings.
```

### deck:onboarding:6

- source: `skills/vet-flat/references/onboarding.md` · L25
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
3. **I have no idea** → I explain one useful starting step and ask only what that step needs (section 2).
```

### deck:onboarding:7

- source: `skills/vet-flat/references/onboarding.md` · L26
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
4. **I am about to sign, or I need somewhere for a few weeks first** → the move-in half: bridging stays (`axes/15`), passing the income check (`axes/16`), the first two weeks in the UK (`axes/17`).
```

### deck:onboarding:8

- source: `skills/vet-flat/references/onboarding.md` · L207
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
1. **Timing.** Listings appear about four to eight weeks before the move-in date; good flats go within days. The order is: enquiry → viewing → "referencing" (income and identity checks) → holding deposit → contract → deposit → keys.
```

### deck:onboarding:9

- source: `skills/vet-flat/references/onboarding.md` · L208
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
2. **What you pay.** Rent, plus council tax (full-time students are exempt: Class N), energy, water, broadband. Buildings on a **heat network** (one boiler for the whole building) bill heat separately through a billing company: ask for the tariff in writing before you sign.
```

### deck:onboarding:10

- source: `skills/vet-flat/references/onboarding.md` · L209
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
3. **The law since 2026-05-01**: in-scope private assured tenancies are periodic. No rent before signing; normally **one month's rent in advance** between signing and commencement for monthly rent. Deposit cap **five weeks' rent** (six at £50,000 annual rent), holding deposit **one week**. Identify halls, licences and lodgers separately; axis 07 gives scope, timing and exceptions.
```

### deck:onboarding:11

- source: `skills/vet-flat/references/onboarding.md` · L210
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
4. **The income check.** Landlords usually want yearly income of roughly thirty times the monthly rent, or a guarantor. If you have neither, there are rent-guarantee or "commercial guarantor" services many landlords accept. Ask every landlord first: "which guarantor routes do you accept?"
```

### deck:onboarding:12

- source: `skills/vet-flat/references/onboarding.md` · L211
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
5. **The energy certificate (EPC) is your friend.** It is public, free, and gives the true indoor size, the building's first assessment year (≈ its age) and the heating type. Advertised sizes often include the balcony.
```

### deck:onboarding:13

- source: `skills/vet-flat/references/onboarding.md` · L212
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
6. **Who the landlord is matters more than the brand.** Purpose-built rental buildings are run by companies with on-site management; private landlords vary from excellent to absent. The legal entity on the contract is what counts; the skill looks it up.
```

### deck:onboarding:14

- source: `skills/vet-flat/references/onboarding.md` · L213
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
7. **Money safety.** Never pay anything before you have viewed (in person or on a verified live video) and have a written tenancy. Deposits go to a protection scheme, never to a personal bank account. Requests to move to WhatsApp or to transfer money "to secure it" are a reason to walk.
```

### deck:onboarding:15

- source: `skills/vet-flat/references/onboarding.md` · L214
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
8. **Never sign on the viewing day.** Sleep on it. Ask two questions that could kill the deal (the skill writes them for you).
```

### deck:onboarding:16

- source: `skills/vet-flat/references/onboarding.md` · L215
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
9. **Streets, roads, rails.** Police crime data is public by street; roads and railways are on the map; ask which side the windows face. "Quiet side or road side" is often the same price for two different homes.
```

### deck:onboarding:17

- source: `skills/vet-flat/references/onboarding.md` · L216
- under: ## 3. Primer for someone with no idea (ten facts, one screen; cite `references/sources.yaml` ids where numbers appear)
- lang: en
- write-back: yes

```text
10. **Where to look.** The big listing portals, the rental operators' own sites, and resident-review sites. The skill tells you exactly what to open and paste; it does not scrape them.
```

### deck:onboarding:18

- source: `skills/vet-flat/references/onboarding.md` · L222
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Only London?** The law is England-wide; the data sources and the crime/commute tooling are London-specific. Elsewhere the method applies with different sources.
```

### deck:onboarding:19

- source: `skills/vet-flat/references/onboarding.md` · L223
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Do you scrape Rightmove / Zoopla / HomeViews?** No. Their terms forbid it. I ask you to paste the page.
```

### deck:onboarding:20

- source: `skills/vet-flat/references/onboarding.md` · L224
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Can I use it on ChatGPT, Gemini, DeepSeek, Grok, Codex?** Yes. With a shell and internet I fetch the data myself; in a chat box I list what to paste, once.
```

### deck:onboarding:21

- source: `skills/vet-flat/references/onboarding.md` · L225
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Where does my data go?** Only to the public sources listed in `references/sources.yaml`, and only what is needed for the lookup. Nothing goes to the author.
```

### deck:onboarding:22

- source: `skills/vet-flat/references/onboarding.md` · L226
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have not landed yet. What first?** Explain how a cancellable temporary stay can leave time to view longer-term homes, and compare the practical trade-offs. Use known arrival dates and costs; ask only the most useful missing detail. Draft the parts of the arrival plan already supported, keeping unknown dates and expenses explicit. Check cancellation and payment terms before recommending a booking.
```

### deck:onboarding:23

- source: `skills/vet-flat/references/onboarding.md` · L227
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Something in a document looks off (a postcode, a company name, a date).** One doubt does not stop the search: name it in one line, give the one check that settles it (the register, the sponsor list, the certificate), and carry on with the flat. Never turn the conversation into an investigation, and never offer to open the user's mailbox, files or accounts to settle it — ask them to paste.
```

### deck:onboarding:24

- source: `skills/vet-flat/references/onboarding.md` · L228
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **My short let is bad (damp, mould, not as described) and I want out tonight.** One message, four parts: a stay of a few nights or weeks is a **licence, not a tenancy** — no deposit scheme, no notice period; your money comes back through the platform's refund route and, failing that, the card or consumer route, never by leaving quietly. Message the host on the platform now, with dated photos, asking for a move or a refund of the unused nights. Book tonight's bed at a hotel with free cancellation and pay at property. For the next stay of a week or more: **see it, or verify it live on video, before paying** — a stay nobody has seen is the bridge's most expensive mistake.
```

### deck:onboarding:25

- source: `skills/vet-flat/references/onboarding.md` · L229
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have just landed. Where do I sleep this week?** For the first one or two weeks a hotel or an operator-run serviced stay is the safer default: your money is protected, you can leave at once, and someone is responsible. A private short let is fine once you have seen it. It costs more per night and often has no kitchen; the skill will price both.
```

### deck:onboarding:26

- source: `skills/vet-flat/references/onboarding.md` · L230
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **What can it not do?** It cannot smell the hallway, hear the road at 2 a.m., or feel whether the street is yours. It says "unknown" where it does not know and asks you for what only you can supply: the floor plan, a street-view screenshot, your impression on the day.
```

### deck:onboarding:27

- source: `skills/vet-flat/references/onboarding.md` · L231
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How does a reply end?** With the one thing still open for you — the question you asked that I could not answer yet and the one check that would settle it — never with another list of questions.
```

### deck:onboarding:28

- source: `skills/vet-flat/references/onboarding.md` · L232
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Does it decide for me?** No. It gives a verdict with the evidence behind it; you decide, after viewing the flat and meeting the people who let it. Landlords and agents are partners here, not opponents.
```

### deck:onboarding:29

- source: `skills/vet-flat/references/onboarding.md` · L233
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How accurate is it?** Facts come from official registers and are graded; anything unknown is shown as unknown, never filled in.
```

### deck:onboarding:30

- source: `skills/vet-flat/references/onboarding.md` · L234
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

- source: `skills/vet-flat/references/inputs.md` · L59-L67
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
