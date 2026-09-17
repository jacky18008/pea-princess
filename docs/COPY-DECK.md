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
| README — the front page (Traditional Chinese, the page GitHub shows) | 36 | `README.md` |
| README.en.md — the front page, English | 36 | `README.en.md` |
| docs/USING.md — the plain-words walkthrough (English) | 21 | `docs/USING.md` |
| docs/USING.zh-TW.md — the walkthrough, Traditional Chinese | 18 | `docs/USING.zh-TW.md` |
| docs/USING.zh-CN.md — the walkthrough, Simplified Chinese | 8 | `docs/USING.zh-CN.md` |
| docs/INSTALL.md — install page | 14 | `docs/INSTALL.md` |
| docs/EXPERIMENTS.md — which configuration to run | 7 | `docs/EXPERIMENTS.md` |
| onboarding.md — what the skill says to a new user | 30 | `skills/vet-flat/references/onboarding.md` |
| sharing.md — social posts and the card description | 6 | `skills/vet-flat/references/sharing.md` |
| inputs.md — the one message that asks the user for what is missing | 1 | `skills/vet-flat/references/inputs.md` |
| profiles/ — the sentences a profile carries | 14 | `skills/vet-flat/profiles/*.yaml` |
| seed.py — the seed card sentences (read-only here) | 25 | `skills/vet-flat/scripts/seed.py` |
| **Total** | **216** | |

---

## README — the front page (Traditional Chinese, the page GitHub shows)

All prose paragraphs. Tables, headings and code blocks are not in the deck.

### deck:readme:1

- source: `README.md` · L20
- under: (top of file)
- lang: zh-TW
- write-back: yes

```text
這是一個在倫敦檢視跟搜尋房源用的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣尻洗一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出判決。任何支援 [Agent Skills](https://agentskills.io) 格式的 agent 都能用（Ex: GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc）；一般的 chat mode, 也可以，只是建議使用 agent mode, 複雜的任務會比較穩定。跟 AI 講白話文就好。
```

### deck:readme:2

- source: `README.md` · L23
- under: ## 為什麼叫「豌豆公主」
- lang: zh-TW
- write-back: yes

```text
童話裡，只有真正的公主能隔著二十層床墊感覺到那顆豌豆。在這裡，**你**就是那位公主。這個工具幫你一層一層把床墊掀開：翻登記資料、數犯罪案件、查規劃申請和公司申報文件，告訴你豌豆可能藏在哪裡。但只有你感覺得到：親自去看房、走一走那條街、跟仲介和房東聊一聊。這份報告是一道濾網，趕時間的時候，它也只是一道濾網。它的第一個責任，是說出自己不知道什麼，然後開口問你。
```

### deck:readme:3

- source: `README.md` · L25
- under: ## 為什麼叫「豌豆公主」
- lang: zh-TW
- write-back: yes

```text
作者自己的經歷，發在社群的繁體中文原文：[到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md)。
```

### deck:readme:4

- source: `README.md` · L29
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
三條路，從最省事到最手動。挑一條跟你現在在用的工具對得上的。
```

### deck:readme:5

- source: `README.md` · L31
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
1. **你在用 agent 應用程式**（Claude Code、Codex、Cursor、Gemini CLI、Grok Build……）。把這句話貼給它，然後等：
```

### deck:readme:6

- source: `README.md` · L33
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
   > 請安裝 https://github.com/jacky18008/pea-princess 這個技能，裝好後告訴我它能做什麼
```

### deck:readme:7

- source: `README.md` · L35
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
   Agent 會把這個專案抓下來，用 `pea-princess` 這個名字把技能裝好，然後回答你。從此就只要講話：「尻洗這間房：」再把房源貼上去。
```

### deck:readme:8

- source: `README.md` · L37
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
2. **你在用有 Skills 功能的聊天軟體**（claude.ai、Claude Cowork、ChatGPT Business）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下載 `pea-princess-skill.zip`，打開 Settings → Skills → Upload，選這個 zip。然後問它「這能幹嘛？」。
```

### deck:readme:9

- source: `README.md` · L39
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
3. **你在用沒有 Skills 的聊天軟體**（ChatGPT Plus Projects、Grok Projects、Gemini Gems、Perplexity Spaces）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下載提示詞包，把 `INSTRUCTIONS.md` 貼進專案的指示欄，再附上 `references/` 裡的檔案。之後技能會一次告訴你要貼什麼。
```

### deck:readme:10

- source: `README.md` · L41
- under: ## 從這裡開始，不需要終端機
- lang: zh-TW
- write-back: yes

```text
不用寫程式，不用改設定檔：接下來全部都是一句一句的話，打字或用語音都行。五分鐘上手看 [USING.zh-TW.md](docs/USING.zh-TW.md)；每一種安裝方式和它的注意事項在 [INSTALL.md](docs/INSTALL.md)。
```

### deck:readme:11

- source: `README.md` · L45
- under: ### 跟它說說你自己
- lang: zh-TW
- write-back: yes

```text
你不用填表格。把你的需求和你的雷點講給它聽就好——含帳單的預算、通勤、「再也不要住地下室」——還有你住過的地方，最好的和最差的；連你還記得的購物習慣，都能讓它知道你是怎麼做決定的。它會把這些記在你的 `profile.yaml` 裡，每次要改都先讓你看過，你中途改變主意也沒關係。懶得打字就用講的：手機或電腦內建的語音輸入，或是 Typeless、Wispr Flow 這類工具，中英文混著講也沒問題。語音輸入真的超讚。
```

### deck:readme:12

- source: `README.md` · L60
- under: ## 它查什麼，答案從哪裡來
- lang: zh-TW
- write-back: yes

```text
每一項結論都帶著它的證據等級。查不到的東西，它會一次、用一則訊息問你。它不會自己去開房源網站：頁面由你交給它，[上手指南](docs/USING.zh-TW.md)裡有三種做法。
```

### deck:readme:13

- source: `README.md` · L64
- under: ## 它只是篩子，房子要親自去看
- lang: zh-TW
- write-back: yes

```text
這裡的每一句話，不是從登記簿讀來的，就是從你貼給它的東西讀來的。它聞不到霉味，聽不到半夜兩點的車聲，也看不到你問「房東到底是誰」的時候，仲介臉上的表情。所以請把報告當成一張「該看什麼」的清單，然後親自走一趟：
```

### deck:readme:14

- source: `README.md` · L70
- under: ## 它只是篩子，房子要親自去看
- lang: zh-TW
- write-back: yes

```text
作者會做這個，是因為在倫敦找房子真的很折磨人，而一個會自己去翻登記簿的助理，幫他少走了很多冤枉路。但它取代不了你自己的兩條腿。
```

### deck:readme:15

- source: `README.md` · L74
- under: ## 哪種方案，用哪種模式
- lang: zh-TW
- write-back: yes

```text
用你自己已經有的訂閱就好；做這件事，個人訂閱比按量計費的 API 金鑰划算不少，而且什麼都不用設定。比起純聊天，建議用 agent 模式（Claude Code、Codex、Grok Build、Cursor……）：這些檢查是一個步驟很多的長任務，聊天模式得你一步一步牽著它走。$20～$30 的方案先從 `lite` 開始，比較省 token。
```

### deck:readme:16

- source: `README.md` · L85
- under: ## 哪種方案，用哪種模式
- lang: zh-TW
- write-back: yes

```text
設定一次就好：寫在你的 `profile.yaml`（`budget_mode: lite`），或直接講「這間用 deep」，助理會確認後改。這幾個模式查的是同一批東西，差別只在深度：`lite` 一間房控制在十次抓取以內，硬性條件、判決和那兩個問題照樣會給；`standard` 是平常的完整版；`deep` 再加上進了決選名單才需要的項目。有兩件事是在真實房子上量出來的，不是意見：深度比模型大小重要（強模型跑 `lite` 的分數，輸給弱模型跑 `standard`），而且會亂編數字的都是便宜的組合——這也是為什麼這裡每一個數字都必須帶著來源，不然就要標成不知道。細節和注意事項：[INSTALL.md](docs/INSTALL.md)、[預算模式](skills/vet-flat/references/budget-modes.md)、[實驗紀錄](docs/EXPERIMENTS.md)。
```

### deck:readme:17

- source: `README.md` · L94
- under: ## 三種模式
- lang: zh-TW
- write-back: yes

```text
> 狀態：**草稿**。本機蒐集、區域掃描、報告產生和實驗框架都已經做好了。處理個人資料或要做發布之前，先讀[安全與隱私邊界](SECURITY.md)。使用方式：`docs/INSTALL.md`、`docs/SCRIPTS.md`、`docs/CONVENTIONS.md`。
```

### deck:readme:18

- source: `README.md` · L96
- under: ## 三種模式
- lang: zh-TW
- write-back: yes

```text
**發布方式：** 下載這個技能／工具，用你自己的 agent 跑。Pea Princess 不代管模型工作程序，也不碰訂閱帳號的憑證。本機的人物實驗室只是測試用的夥伴。詳見[桌機／手機的界線、供應商訂閱政策、發布關卡](docs/local-product-and-provider-policy.md)。
```

### deck:readme:19

- source: `README.md` · L111
- under: # then, on any host with a shell: is it installed right? (one request per open register)
- lang: zh-TW
- write-back: yes

```text
這個技能安裝和呼叫的名字都是 **`pea-princess`**；上傳用的檔案是 `dist/pea-princess-skill.zip`。專案原始碼還是放在 `skills/vet-flat/`，這樣既有的腳本路徑和實驗紀錄才不會失效。這就是一個技能，一個安裝名稱。
```

### deck:readme:20

- source: `README.md` · L113
- under: # then, on any host with a shell: is it installed right? (one request per open register)
- lang: zh-TW
- write-back: yes

```text
Codex：把沙箱網路打開（`sandbox_workspace_write.network_access = true`），或改用 manual 模式。
```

### deck:readme:21

- source: `README.md` · L116
- under: ### 腳本（只用 Python 3.9 標準函式庫；網路走 curl）
- lang: zh-TW
- write-back: yes

```text
全部在 `skills/vet-flat/scripts/`；每一支都印出一個 JSON 物件，裡面有 `source_url`、`retrieved_at`、`http_status`、`ok` 和一個證據等級。用法細節在 `docs/SCRIPTS.md`。
```

### deck:readme:22

- source: `README.md` · L131
- under: ### 腳本（只用 Python 3.9 標準函式庫；網路走 curl）
- lang: zh-TW
- write-back: yes

```text
沒有 shell 的人要看報告排版：用瀏覽器打開 `viewer/viewer.html`，把 JSON 貼進去。需求頁面對另一個檔案也是同樣的做法：`scripts/panel.py --profile profile.yaml --out requirements.html` 會寫出一頁唯讀的現況，讓人隨時想看就打開。沒有任何助理會自己寫 HTML；模型寫 YAML 和 JSON，由腳本負責排版。
```

### deck:readme:23

- source: `README.md` · L134
- under: ### 問它能做什麼
- lang: zh-TW
- write-back: yes

```text
問它 **「這能幹嘛？」**（或 "What can this do?"）。答案來自 `skills/vet-flat/references/onboarding.md`：一段簡短說明、三個起點（有房源 → 尻洗它；有區域或目的地 → 掃一遍；完全沒概念 → 十個基本事實加六個帶建議預設值的問題）。你自己的規則寫在 `profile.yaml`（預算、面積、房型、不能接受的條件、優先順序，還有 `budget_mode`——哪個方案該設哪個值，看「哪種方案，用哪種模式」那張表）。Agent 一定要問的硬問題在 `references/questions.md`。
```

### deck:readme:24

- source: `README.md` · L137
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
`evals/evals.json` 收了 7 個行政區的 8 間真實房子，加上 2 個對話情境（「這能幹嘛」、「我完全沒概念」），標準答案由專案自己的抓取腳本在 2026-09-03 產生。`bench/grade.py` 評分的項目有事實召回率、捏造、引用、對未知的誠實度、硬性條件的一致性；`bench/run.py --dry-run` 會印出 Claude Code、Codex、Gemini CLI 或 OpenAI 相容 API 的完整指令。詳見 `bench/README.md`。
```

### deck:readme:25

- source: `README.md` · L139
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
**要跑哪一種設定：** `docs/EXPERIMENTS.md` 記錄了最早的看房比較實驗。[後來的上下文消融實驗](docs/ablation-2026-09-09/results.md)包含生成成本和來源檢視：在測到的規模下，額外的摘要、結構化記憶和多次檢索呼叫並沒有省下 token。起點就維持「一個 agent 帶完整上下文」；四角色流水線還在實驗階段。這些研究量的是不同的任務，不是一份通用的模型排名。
```

### deck:readme:26

- source: `README.md` · L141
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
**長時間的專案和會變的需求：** [session harness](docs/session-harness.md) 會保存使用者的原話、帶版本的需求和條件式例外、來源快照、目標、待辦和執行狀態。受管理的 runner 自己把當前的封包塞進去，並拒絕過期的結果。`AGENTS.md`／`CLAUDE.md` 保持簡短，只連到詳細規則；光放指標不能保證對方會去讀。[生命週期驗證](docs/session-harness-validation.md)測的是不呼叫模型也能復原，不是品質等價或省 token。
```

### deck:readme:27

- source: `README.md` · L143
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
**想試一整段人物對話：** 跑 `python3 tools/persona_playground.py`，再打開它印出來的本機網址。[互動實驗室](docs/persona-playground.md)用你本機的 Codex 登入來產生動態的人物回覆和助理答案，支援單步／連續／暫停、排隊的真人提問、情境修訂、私有歷史和共用的用量上限。16 張人物卡都有，以清楚標示的聊天改編版呈現；這是本機 alpha，沒有公開部署，也沒有隱藏的模型裁判。
```

### deck:readme:28

- source: `README.md` · L145
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
**社群回饋，第一階段：** 打開[本機選項表單](community/index.html)，照著[指南](docs/community-feedback-stage1.md)做。公開的 JSON 只放受控的選項；選填的文字留在作者自己的裝置上。本機的驗證、匯入和搜尋用的是虛構的示範目錄。目前還沒有線上投稿服務，也沒有真實的評論資料集。
```

### deck:readme:29

- source: `README.md` · L147
- under: ### 基準測試（事實在每個模型上都要對；判決可以不一樣）
- lang: zh-TW
- write-back: yes

```text
**看的是整段對話，不是單一回答：** `docs/JOURNEYS.md` 為九段寫好腳本的多輪旅程評分，`docs/PERSONAS.md` 再往前一步——十六個由模型扮演的虛構人物，搭配一個決定性的控制器保管他們的文件，讓任何東西都編不出來；裁判必須引用自己的證據；每個人還配一個只動一項設定的對照探針。`python3 bench/personas.py --matrix pilot --dry-run` 不呼叫模型就能印出整份計畫。
```

### deck:readme:30

- source: `README.md` · L157
- under: ## 這裡不會有的來源
- lang: zh-TW
- write-back: yes

```text
Rightmove、Zoopla、OnTheMarket、OpenRent、HomeViews、Trustpilot、Airbnb、Booking.com 在這裡只會出現名字。它們的條款不希望程式自動存取，所以這個專案不提供任何做法；技能會向你要頁面（PDF、截圖或純文字），不會自己去開房源連結。這包沒有這些網頁的爬蟲，也不能鼓勵你讓 agent 去爬蟲。
```

### deck:readme:31

- source: `README.md` · L161
- under: ## 改成你的樣子
- lang: zh-TW
- write-back: yes

```text
技能就是一個資料夾，裡面是 Markdown 和幾支腳本，這一包本來就是設計來讓你隨手改的。不用讀程式碼：跟你的 agent 用講的。
```

### deck:readme:32

- source: `README.md` · L170
- under: ## 改成你的樣子
- lang: zh-TW
- write-back: yes

```text
任何主機都能先試這一句：
```

### deck:readme:33

- source: `README.md` · L172
- under: ## 改成你的樣子
- lang: zh-TW
- write-back: yes

```text
> 把這個技能改成每份報告開頭先講每月總花費，改完跑測試，告訴我你改了什麼。
```

### deck:readme:34

- source: `README.md` · L175
- under: ## 授權與姓名標示（提案中）
- lang: zh-TW
- write-back: yes

```text
文件和技能文字：CC BY 4.0。程式碼：MIT。每一份報告都會帶著 "Generated with pea-princess <version> — <source URL>"。請留著它。
```

### deck:readme:35

- source: `README.md` · L177
- under: ## 授權與姓名標示（提案中）
- lang: zh-TW
- write-back: yes

```text
插圖出自 Edmund Dulac 1911 年為 *Stories from Hans Andersen*（Hodder & Stoughton，倫敦）畫的彩頁，屬於公有領域。`docs/assets/mark.svg` 裡的標誌（七層床墊下的一顆豌豆）是原創的，跟文件一起以 CC BY 4.0 釋出；`docs/assets/social-preview.png` 是同一個標誌做成的 1280×640 預覽卡。
```

### deck:readme:36

- source: `README.md` · L181
- under: ## 作者的聯絡方式
- lang: zh-TW
- write-back: yes

```text
陳先灝 Hsien Hao (Jacky) Chen — [LinkedIn](https://www.linkedin.com/in/jacky-chen-a49177137/)。有問題、想法，或你自己找房的故事，歡迎在這裡開 issue 或到 LinkedIn 私訊。
```

---

## README.en.md — the front page, English

All prose paragraphs. Tables, headings and code blocks are not in the deck.

### deck:readme-en:1

- source: `README.en.md` · L20
- under: (top of file)
- lang: en
- write-back: yes

```text
An agent skill for checking and searching rental listings in London. It vets a flat the way a careful surveyor would: identity, floor area, age, heating, construction nearby, crime, management reviews, agent compliance, price, light, total monthly cost and commute, from official and open UK data, ending in a verdict. Works with any agent that reads the [Agent Skills](https://agentskills.io) format (e.g. GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc.). Plain chat mode works too, but agent mode is recommended: it is steadier on complex tasks. Just talk to the AI in plain words.
```

### deck:readme-en:2

- source: `README.en.md` · L23
- under: ## Why "Pea Princess"
- lang: en
- write-back: yes

```text
In the fairy tale only the real princess feels the pea through twenty mattresses. Here **you** are the princess. This tool lifts the mattresses one by one: it reads the registers, counts the crimes, checks the planning applications and the company filings, and tells you where the pea might be. Only you can feel it: go and see the flat, walk the street, talk to the agent and the landlord. The report is a filter, and when you are in a hurry it is only a filter. Its first duty is to say what it does not know and ask you for it.
```

### deck:readme-en:3

- source: `README.en.md` · L25
- under: ## Why "Pea Princess"
- lang: zh-TW
- write-back: yes

```text
The author's own account, in Traditional Chinese, as posted to the community: [到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md).
```

### deck:readme-en:4

- source: `README.en.md` · L29
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
Three ways in, from easiest to most manual. Pick the one that matches what you already use.
```

### deck:readme-en:5

- source: `README.en.md` · L31
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
1. **You use an agent app** (Claude Code, Codex, Cursor, Gemini CLI, Grok Build, …). Paste this sentence to it and wait:
```

### deck:readme-en:6

- source: `README.en.md` · L33
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
   > Install the skill from https://github.com/jacky18008/pea-princess and then tell me what it can do.
```

### deck:readme-en:7

- source: `README.en.md` · L35
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
   The agent fetches this repository, installs the skill under the name `pea-princess`, and answers. From then on, just talk: "Roast this flat:" and paste the listing.
```

### deck:readme-en:8

- source: `README.en.md` · L37
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
2. **You use a chat app with a Skills feature** (claude.ai, Claude Cowork, ChatGPT Business). Download `pea-princess-skill.zip` from [Releases](https://github.com/jacky18008/pea-princess/releases), open Settings → Skills → Upload, choose the zip. Then ask "What can this do?".
```

### deck:readme-en:9

- source: `README.en.md` · L39
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
3. **You use a chat app without Skills** (ChatGPT Plus Projects, Grok Projects, Gemini Gems, Perplexity Spaces). Download the prompt pack from [Releases](https://github.com/jacky18008/pea-princess/releases), paste `INSTRUCTIONS.md` into the project's instructions and attach the `references/` files. The skill then tells you, once, what to paste.
```

### deck:readme-en:10

- source: `README.en.md` · L41
- under: ## Start here — no terminal needed
- lang: en
- write-back: yes

```text
No code, no settings files: everything after that is sentences, typed or dictated. The five-minute walkthrough is [USING.md](docs/USING.md); every install route with its caveats is [INSTALL.md](docs/INSTALL.md).
```

### deck:readme-en:11

- source: `README.en.md` · L45
- under: ### Tell it about you
- lang: en
- write-back: yes

```text
You do not fill in a form. Say what you need and what you cannot stand — the budget with bills, the commute, "never a basement again" — and the places you have lived, the best and the worst; even a shopping habit you remember tells it how you decide. It keeps that in your `profile.yaml`, shows every change before it makes it, and you can change your mind halfway. If typing is a chore, dictate: the built-in dictation on your phone or computer, or an app such as Typeless or Wispr Flow, and mixed Chinese and English is fine.
```

### deck:readme-en:12

- source: `README.en.md` · L60
- under: ## What it checks, and where the answers come from
- lang: en
- write-back: yes

```text
Every finding carries its evidence grade. What it cannot reach, it asks you for, once, in one message. It never opens listing sites: you hand it the page, and [the walkthrough](docs/USING.md) shows the three ways to do that.
```

### deck:readme-en:13

- source: `README.en.md` · L64
- under: ## It is a filter. Go and see the flat
- lang: en
- write-back: yes

```text
Everything here is read from registers and from what you paste. It cannot smell the damp, hear the road at 2 a.m., or see the agent's face when you ask who the landlord is. So treat the report as the list of what to look at, then go:
```

### deck:readme-en:14

- source: `README.en.md` · L70
- under: ## It is a filter. Go and see the flat
- lang: en
- write-back: yes

```text
The author built this because looking for a flat in London is a grim process, and an assistant that reads the registers saved them many wasted viewings. It is not a replacement for your own feet.
```

### deck:readme-en:15

- source: `README.en.md` · L74
- under: ## Which plan, which mode
- lang: en
- write-back: yes

```text
Use the subscription you already have; for this work a personal plan is far better value than pay-as-you-go keys, and it needs no setup. Prefer an agent mode (Claude Code, Codex, Grok Build, Cursor…) over plain chat: the checks are a long task with many small steps, and chat mode has to be walked through them by hand.
```

### deck:readme-en:16

- source: `README.en.md` · L85
- under: ## Which plan, which mode
- lang: en
- write-back: yes

```text
Set it once in your `profile.yaml` (`budget_mode: lite`) or just say it ("use deep for this one"); the assistant confirms the change. The modes are depths of the same checks: `lite` keeps under ten fetches a flat and still gives the hard filters, the verdict and the two questions; `standard` is the usual set; `deep` adds the shortlist extras. Two things measured on real flats, not opinions: depth matters more than model size (a strong model in `lite` scored below a weak one in `standard`), and cheap set-ups are the ones that invent numbers, which is why every number here must carry its source or be marked unknown. Details and caveats: [INSTALL.md](docs/INSTALL.md), [budget modes](skills/vet-flat/references/budget-modes.md), [experiments](docs/EXPERIMENTS.md).
```

### deck:readme-en:17

- source: `README.en.md` · L94
- under: ## Three modes
- lang: en
- write-back: yes

```text
> Status: **draft**. Local collection, area sweep, report rendering and experiment harnesses are implemented. Read [security and privacy boundaries](SECURITY.md) before handling personal data or building a release. Usage: `docs/INSTALL.md`, `docs/SCRIPTS.md`, `docs/CONVENTIONS.md`.
```

### deck:readme-en:18

- source: `README.en.md` · L96
- under: ## Three modes
- lang: en
- write-back: yes

```text
**Distribution:** download the skill/tool and run it with your own agent. Pea Princess does not host model workers or handle subscription credentials. The local persona lab is a testing companion. See [desktop/mobile boundaries, provider subscription policies, and release gates](docs/local-product-and-provider-policy.md).
```

### deck:readme-en:19

- source: `README.en.md` · L111
- under: # then, on any host with a shell: is it installed right? (one request per open register)
- lang: en
- write-back: yes

```text
The skill is installed and invoked as **`pea-princess`**; the upload artifact is `dist/pea-princess-skill.zip`. The repository still stores its source in `skills/vet-flat/` so existing script paths and experiment records remain valid. This is one skill, with one installed name.
```

### deck:readme-en:20

- source: `README.en.md` · L113
- under: # then, on any host with a shell: is it installed right? (one request per open register)
- lang: en
- write-back: yes

```text
Codex: enable sandbox network (`sandbox_workspace_write.network_access = true`) or use manual mode.
```

### deck:readme-en:21

- source: `README.en.md` · L116
- under: ### Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
All in `skills/vet-flat/scripts/`; each prints one JSON object with `source_url`, `retrieved_at`, `http_status`, `ok` and an evidence class. Usage details: `docs/SCRIPTS.md`.
```

### deck:readme-en:22

- source: `README.en.md` · L131
- under: ### Scripts (Python 3.9 standard library only; network via curl)
- lang: en
- write-back: yes

```text
Report layout for people without a shell: open `viewer/viewer.html` in a browser and paste the JSON. The requirements page is the same idea for the other file: `scripts/panel.py --profile profile.yaml --out requirements.html` writes a read-only page of where things stand, for the person to open whenever they like. No assistant writes HTML; the model writes YAML and JSON, the scripts render them.
```

### deck:readme-en:23

- source: `README.en.md` · L134
- under: ### Ask it what it can do
- lang: en
- write-back: yes

```text
Ask **"What can this do?"** (or 這能幹嘛？). The answer comes from `skills/vet-flat/references/onboarding.md`: a short pitch, three starting points (a listing → vet it; an area or destination → sweep; no idea → a ten-fact primer and six questions with suggested defaults). Your rules live in `profile.yaml` (budget, size, flat type, deal-breakers, priorities, and `budget_mode` — which value fits which plan is the table under "Which plan, which mode"). The hard follow-up questions the agent must ask are in `references/questions.md`.
```

### deck:readme-en:24

- source: `README.en.md` · L137
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
`evals/evals.json` has 8 real flats across 7 boroughs plus 2 conversation cases ("what can this do", "I have no idea"), with truth produced by the repo's own fetchers on 2026-09-03. `bench/grade.py` scores fact recall, fabrications, citations, unknown-honesty and hard-filter consistency; `bench/run.py --dry-run` prints the exact command for Claude Code, Codex, Gemini CLI or an OpenAI-compatible API. See `bench/README.md`.
```

### deck:readme-en:25

- source: `README.en.md` · L139
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Which configuration to run:** `docs/EXPERIMENTS.md` records the original flat-vetting comparisons. The [later context ablation](docs/ablation-2026-09-09/results.md) includes generation costs and source reviews: extra summarization, structured memory and multiple retrieval calls did not save tokens at the tested sizes. Keep one agent with full context as the starting point; the four-role pipeline remains experimental. These studies measure different tasks, not a universal model ranking.
```

### deck:readme-en:26

- source: `README.en.md` · L141
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Long-running projects and changing requirements:** the [session harness](docs/session-harness.md) saves exact user requests, revisioned requirements and conditional exceptions, source snapshots, goals, TODOs and execution state. The managed runner inserts the current packet itself and rejects stale results. Short `AGENTS.md` / `CLAUDE.md` files link to detailed rules; pointers alone cannot ensure reading. [Lifecycle validation](docs/session-harness-validation.md) tests recovery without new model calls, not quality equivalence or token savings.
```

### deck:readme-en:27

- source: `README.en.md` · L143
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Try a whole persona conversation:** run `python3 tools/persona_playground.py` and open the printed local URL. The [interactive lab](docs/persona-playground.md) uses your local Codex login for dynamic persona replies and assistant answers, with step/run/pause, queued human questions, scenario amendments, private history and shared usage ceilings. All 16 cards are available in a clearly labelled chat adaptation; this is a local alpha, with no public deployment or hidden model judge.
```

### deck:readme-en:28

- source: `README.en.md` · L145
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Community feedback, stage 1:** open the [local options form](community/index.html) and follow the [guide](docs/community-feedback-stage1.md). Public JSON contains controlled choices; optional text stays on the author's device. Local validation, import and search use a fictional demo catalog. There is no online submission service or real review dataset yet.
```

### deck:readme-en:29

- source: `README.en.md` · L147
- under: ### Benchmark (facts must be right on every model; verdicts may differ)
- lang: en
- write-back: yes

```text
**Whole conversations, not one answer:** `docs/JOURNEYS.md` scores nine scripted multi-turn journeys, and `docs/PERSONAS.md` goes one step further — sixteen fictional people played by a model, with a deterministic controller holding their documents so nothing can be invented, a judge that has to quote its evidence, and a paired probe per person that moves exactly one setting. `python3 bench/personas.py --matrix pilot --dry-run` prints the whole plan without calling a model.
```

### deck:readme-en:30

- source: `README.en.md` · L157
- under: ## Sources you will not find here
- lang: en
- write-back: yes

```text
Rightmove, Zoopla, OnTheMarket, OpenRent, HomeViews, Trustpilot, Airbnb, Booking.com appear here by name only. Their terms do not want programs reading them automatically, so this project provides no method for that; the skill asks you for the page (a PDF, screenshots or the plain text) and never opens listing links itself. There is no scraper for these sites in this package, and it cannot encourage you to have your agent scrape them either.
```

### deck:readme-en:31

- source: `README.en.md` · L161
- under: ## Make it yours
- lang: en
- write-back: yes

```text
A skill is a folder of Markdown and a few scripts, and this one is written to be bent. You do not need to read the code: say what you want to your agent.
```

### deck:readme-en:32

- source: `README.en.md` · L170
- under: ## Make it yours
- lang: en
- write-back: yes

```text
One sentence to try first, on any host:
```

### deck:readme-en:33

- source: `README.en.md` · L172
- under: ## Make it yours
- lang: en
- write-back: yes

```text
> Change this skill so that every report starts with the all-in monthly cost, run the tests, and tell me what you changed.
```

### deck:readme-en:34

- source: `README.en.md` · L175
- under: ## Licence and attribution (proposed)
- lang: en
- write-back: yes

```text
Documentation and skill text: CC BY 4.0. Code: MIT. Every report carries "Generated with pea-princess <version> — <source URL>". Please keep it.
```

### deck:readme-en:35

- source: `README.en.md` · L177
- under: ## Licence and attribution (proposed)
- lang: en
- write-back: yes

```text
The illustration is Edmund Dulac's 1911 plate for *Stories from Hans Andersen* (Hodder & Stoughton, London), public domain. The mark in `docs/assets/mark.svg` (a pea under seven mattresses) is original and released with the documentation under CC BY 4.0; `docs/assets/social-preview.png` is the same mark as a 1280×640 preview card.
```

### deck:readme-en:36

- source: `README.en.md` · L181
- under: ## Contact the author
- lang: en
- write-back: yes

```text
Hsien Hao (Jacky) Chen 陳先灝 — [LinkedIn](https://www.linkedin.com/in/jacky-chen-a49177137/). Questions, ideas and stories from your own search are welcome: open an issue here or write on LinkedIn.
```

---

## docs/USING.md — the plain-words walkthrough (English)

Every paragraph, step and bullet. Headings are not in the deck.

### deck:using:1

- source: `docs/USING.md` · L1
- under: (top of file)
- lang: zh-TW
- write-back: yes

```text
**English** · [繁體中文](USING.zh-TW.md) · [简体中文](USING.zh-CN.md)
```

### deck:using:2

- source: `docs/USING.md` · L7
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
Tell the assistant what you want to understand. You do not need to write code, complete a questionnaire or choose technical settings before it can help.
```

### deck:using:3

- source: `docs/USING.md` · L9
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
After installing the skill using the [installation guide](INSTALL.md), try:
```

### deck:using:4

- source: `docs/USING.md` · L11
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
- “I'm moving to London in October. Show me some examples and explain how to choose.”
```

### deck:using:5

- source: `docs/USING.md` · L12
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
- “I want a quiet one-bedroom home. My total monthly cost, including rent and bills, should stay below £2,200.”
```

### deck:using:6

- source: `docs/USING.md` · L13
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
- “Compare these two listings, and tell me what to check at a viewing.”
```

### deck:using:7

- source: `docs/USING.md` · L14
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
- “Pause the comparison: what does a guarantor do?”
```

### deck:using:8

- source: `docs/USING.md` · L16
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
It starts with useful examples or the evidence you provide, explains a trade-off, and learns what matters from your reaction. Usually it asks zero to two questions at a time, never more than three essential clarifications. You can say “not sure”. A complete set of preferences is not required before making progress.
```

### deck:using:9

- source: `docs/USING.md` · L18
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
The assistant uses real rental examples with source links and dates. A public advert is not a guarantee of availability. If a source cannot be reached, it continues with supported information and asks for the missing extract; it does not switch to fictional homes. Invented teaching examples are used only if you request them. Your assistant may need you to paste a listing or attach a floor plan. It explains what is needed and why, while continuing other checks. If your app supports a choice panel, it can use that; otherwise you answer in ordinary text.
```

### deck:using:10

- source: `docs/USING.md` · L20
- under: # You can start with a conversation
- lang: en
- write-back: yes

```text
**Handing over a listing page.** The skill never opens listing links (the sites' terms do not allow programs to read for you), so give it the page itself. On a computer: File → Save Page As → "Webpage, Complete", then attach the `.html` — it carries more than the screen shows, including the full postcode. On an iPhone: Safari's share sheet, either with the one-tap shortcut described at the top of `skills/vet-flat/scripts/capture_page.js` or with Options → Web Archive. A PDF or the copied text also works, with less in it. Photos and the floor plan are pictures: save them, or print the page to PDF.
```

### deck:using:11

- source: `docs/USING.md` · L24
- under: ### Speak instead of typing
- lang: en
- write-back: yes

```text
If speaking is easier, use your device's built-in dictation or an app you already like to enter text in the assistant's chat box. [Typeless](https://www.typeless.com/pricing) and [Wispr Flow](https://wisprflow.ai/pricing) are optional examples; both list free plans with usage limits, which vary by plan or platform (checked 11 September 2026). Check the linked pages for current allowances; installing or paying for another app is not required.
```

### deck:using:12

- source: `docs/USING.md` · L26
- under: ### Speak instead of typing
- lang: en
- write-back: yes

```text
Describe in your own words what you want, the rentals or stays that were especially good or especially bad, even a shopping experience you still remember — it all helps the assistant understand you. You can change your mind midway. Before sending, just glance at the text to check it was transcribed correctly.
```

### deck:using:13

- source: `docs/USING.md` · L30
- under: ### Learn by comparing
- lang: en
- write-back: yes

```text
Start with differences you can react to: a shorter commute versus more space, a quiet bedroom versus a busy road, lower rent versus uncertain bills. The assistant explains the likely consequences, then helps you inspect the evidence or prepare a viewing check. You can ask about London areas, rental budgets, paperwork or common problems whenever they become relevant. For claims about the current market or the law, you can ask the assistant to attach the sources it checked.
```

### deck:using:14

- source: `docs/USING.md` · L34
- under: ### Read the recommendation
- lang: en
- write-back: yes

```text
The answer begins with what to do next and why. Numbers keep their source and uncertainty: “landlord estimate: 20 minutes, not checked” is different from a journey planner prediction for your destination and arrival time. A quote matching the landlord's message does not prove the claim is true. Unknown information remains unknown; a low estimate alone does not confirm that a home meets your limit.
```

### deck:using:15

- source: `docs/USING.md` · L36
- under: ### Read the recommendation
- lang: en
- write-back: yes

```text
A fuller report covers the money, paperwork, size, bills, move-in timing and other checks relevant to the home. These are things the assistant works through, not a form you must fill out before it helps. It asks for the few missing items that matter next and keeps other gaps visible.
```

### deck:using:16

- source: `docs/USING.md` · L40
- under: ### Change your mind or interrupt
- lang: en
- write-back: yes

```text
Say “Raise my total monthly limit to £2,300”, “Quiet matters more than light”, or “A longer commute is okay, but never over 45 minutes”. The assistant applies clear instructions, explains the effect in plain words and preserves conditions and previous requirements. It asks only when your meaning is materially ambiguous or it proposes a change itself.
```

### deck:using:17

- source: `docs/USING.md` · L42
- under: ### Change your mind or interrupt
- lang: en
- write-back: yes

```text
Ask a side question at any point. It should answer it, keep the original work available, and resume without making you repeat your preferences. Saving across conversations depends on the host's file and memory support; the assistant must say when it cannot save something.
```

### deck:using:18

- source: `docs/USING.md` · L46
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
Compare temporary accommodation if it would give you time to view longer-term homes. Check actual cancellation, payment and departure terms; no accommodation type guarantees a refund or same-day exit. Build an arrival plan from your dates and verified costs, leaving gaps explicit.
```

### deck:using:19

- source: `docs/USING.md` · L48
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
Use the report to decide what to investigate, then see the flat and speak with the agent or landlord. Take the agreement away to read; do not sign at the viewing. The assistant gives legal and payment guidance at the decision it affects, with the applicable date and agreement type.
```

### deck:using:20

- source: `docs/USING.md` · L50
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
**Your own little secretary.** Anything personal or local that the shared skill does not check — the walk to your gym, a school's catchment, a noise source you know about, a data set you trust — goes into `extensions/` in your copy as a one-page add-on (or just tell the assistant the whole list and let it put it in). These extras are labelled in the report, never change the verdict by themselves, read no listing or review sites, and never describe an area by who lives there.
```

### deck:using:21

- source: `docs/USING.md` · L52
- under: ### Before arriving or committing
- lang: en
- write-back: yes

```text
**Share what you learned, not where you live.** Ask the assistant for your seed and post it: it carries your taste, deal-breakers and the questions you make every flat answer, never where you go each day or when you move. Around it, say what helped you; leave out your employer, school, station and moving date. There is no version that includes them: a friend who needs everything gets your profile file, not a seed.
```

---

## docs/USING.zh-TW.md — the walkthrough, Traditional Chinese

Every paragraph, step and bullet. Headings are not in the deck.

### deck:using-zh-tw:1

- source: `docs/USING.zh-TW.md` · L1
- under: (top of file)
- lang: zh-TW
- write-back: yes

```text
[English](USING.md) · **繁體中文** · [简体中文](USING.zh-CN.md)
```

### deck:using-zh-tw:2

- source: `docs/USING.zh-TW.md` · L7
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
不用寫程式，也不用先填完整問卷或挑技術設定。按照[安裝說明](INSTALL.md)加入技能後，可以直接說：
```

### deck:using-zh-tw:3

- source: `docs/USING.zh-TW.md` · L9
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
- 「我十月要去倫敦，先給我例子，教我怎麼挑。」
```

### deck:using-zh-tw:4

- source: `docs/USING.zh-TW.md` · L10
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
- 「我想找安靜的一房，每月總花費（房租加帳單）不要超過 £2,200。」
```

### deck:using-zh-tw:5

- source: `docs/USING.zh-TW.md` · L11
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
- 「比較這兩間，告訴我看房時要查什麼。」
```

### deck:using-zh-tw:6

- source: `docs/USING.zh-TW.md` · L12
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
- 「先插問一下：擔保人是做什麼的？」
```

### deck:using-zh-tw:7

- source: `docs/USING.zh-TW.md` · L14
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
Agent 會先用例子或你提供的房源做出有用的比較，再從你的反應了解偏好。通常一次問零到兩題，必要確認最多三題；「還不知道」也可以，不必先把所有條件想清楚。
```

### deck:using-zh-tw:8

- source: `docs/USING.zh-TW.md` · L16
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
能搜尋時，真實房源會附來源與日期；不能搜尋時，教學例子會明確標示為虛構，不會把假設價格說成倫敦現在的行情。需要你貼房源、戶型圖或其他文件時，會說明用途，並繼續做不受影響的部分。聊天軟體有選項介面就用選項，沒有就直接打字。
```

### deck:using-zh-tw:9

- source: `docs/USING.zh-TW.md` · L18
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
**把房源頁面交給它。** 技能不會自己開房源連結（網站條款不允許程式代替你讀），所以把頁面本身給它。電腦上：「檔案 → 另存網頁 → 網頁，完整」，然後附上 `.html`，裡面的資訊比畫面多，連完整郵遞區號都在。iPhone 上：用 Safari 的分享面板，裝一次 `skills/vet-flat/scripts/capture_page.js` 開頭寫的捷徑就能一鍵送出，或用「選項 → 網頁封存」。PDF 或複製文字也可以，只是資訊少一些。照片和平面圖是圖片，另外存下來，或把頁面列印成 PDF。
```

### deck:using-zh-tw:10

- source: `docs/USING.zh-TW.md` · L20
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
**不想打字，可以用語音輸入。** 用手機或電腦內建的聽寫，或你習慣的語音轉文字工具，把內容輸入助理的對話框即可；[Typeless](https://www.typeless.com/pricing) 和 [Wispr Flow](https://wisprflow.ai/pricing) 都是可選例子。兩者目前都有免費方案，但有用量限制，依平台與方案而異（2026-09-11 查核，最新額度看官方頁面）；不需要為了使用這個 skill 另外安裝或付費。
```

### deck:using-zh-tw:11

- source: `docs/USING.zh-TW.md` · L22
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
可以直接說你的需求、過去特別好或特別糟的租房/住宿經驗，甚至是過去印象深刻的購物經驗也可以，會讓 AI 更理解你。中途改主意也行。送出前看一下文字有沒有辨識正確就好。
```

### deck:using-zh-tw:12

- source: `docs/USING.zh-TW.md` · L24
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
可以先比較「通勤近一點，還是空間大一點」、「臥室安靜，還是生活機能方便」、「租金低一點，還是帳單比較確定」。邊看邊問倫敦的區域、預算、租屋流程或常見問題，也可以請助理教你如何在看房時查證。涉及目前行情或法律的說法，可以要求 Agent 應附上查過的來源。
```

### deck:using-zh-tw:13

- source: `docs/USING.zh-TW.md` · L26
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
答案先說下一步和理由。數字會保留來源與限制：「房東估計通勤 20 分鐘，還沒查證」不等於實際通勤已確認；逐字核對房東訊息，也不代表內容一定正確。每月總花費會說明房租、能源、水、網路與適用的市政稅哪些已知、哪些只是估計。
```

### deck:using-zh-tw:14

- source: `docs/USING.zh-TW.md` · L28
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
中途改條件直接說：「總預算提高到 £2,300」、「安靜比採光重要」、「通勤可以久一點，但超過 45 分鐘就不要」。助理會套用明確指示，用白話說明影響，保留例外和其他條件；不需要再確認同一個要求。只有意思不明確，或助理自己提議修改時，才需要釐清。
```

### deck:using-zh-tw:15

- source: `docs/USING.zh-TW.md` · L30
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
隨時可以插問其他問題，再回到原本的找房工作，不必重新交代偏好。跨對話保存取決於你使用的軟體；助理不能假裝已經存好。
```

### deck:using-zh-tw:16

- source: `docs/USING.zh-TW.md` · L32
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
還沒抵達時，可以比較暫住方案，替實地看房留時間。取消、退款和退房條件都要看實際條款，不能只因為是旅館或服務式公寓就當成有保障。看房時親自確認環境、和仲介或房東談清楚；合約帶回去讀，看房當天不簽約。法律與付款提醒會放在相關決定旁，不會每次開場都貼一整段。
```

### deck:using-zh-tw:17

- source: `docs/USING.zh-TW.md` · L34
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
**自己的小秘書。** 共用技能沒查、但你在意的東西，例如到健身房的步行時間、學區、你知道的噪音來源、你信任的資料集，寫成一頁放進你自己那份的 `extensions/` 資料夾（或是直接跟 Agent 講一整串讓它放進去）。這些額外項目在報告裡會標示出來、不會自己改變判決、不讀房源和評價網站、也不用「住的是誰」來描述一個地區。
```

### deck:using-zh-tw:18

- source: `docs/USING.zh-TW.md` · L36
- under: # 從聊天開始就好
- lang: zh-TW
- write-back: yes

```text
**分享你學到的，不分享你住哪。** 跟助理要一組「種子」貼出去：它帶的是你的口味、地雷和你要求每間房回答的問題，從來不含你每天去哪、什麼時候搬。貼文裡寫對你有幫助的事就好，別補上公司、學校、車站和搬家日。沒有任何一種版本會帶這些；真的要給朋友全部，就直接給設定檔，不用種子。
```

---

## docs/USING.zh-CN.md — the walkthrough, Simplified Chinese

Every paragraph, step and bullet. Headings are not in the deck.

### deck:using-zh-cn:1

- source: `docs/USING.zh-CN.md` · L1
- under: (top of file)
- lang: zh-TW
- write-back: yes

```text
[English](USING.md) · [繁體中文](USING.zh-TW.md) · **简体中文**
```

### deck:using-zh-cn:2

- source: `docs/USING.zh-CN.md` · L7
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
直接聊天就能开始，不用先填问卷。可以说「先给我例子，教我怎么挑」，或贴两套房源请助理比较。它会先做有用的分析，再从你的反应了解偏好；通常一次问零到两题，必要确认最多三题。支持选项界面时使用真实选项，没有就直接打字。
```

### deck:using-zh-cn:3

- source: `docs/USING.zh-CN.md` · L9
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
**把房源页面交给它。** 技能不会自己打开房源链接（网站条款不允许程序代替你读），所以把页面本身给它：电脑上「文件 → 网页另存为 → 网页，全部」再附上 `.html`，里面的信息比屏幕多，连完整邮编都在；iPhone 上用 Safari 的分享面板，装一次 `skills/vet-flat/scripts/capture_page.js` 开头写的快捷指令即可一键发送，或用「选项 → 网页归档」。PDF 或复制文字也可以，只是信息少一些。照片和户型图另外保存，或把页面打印成 PDF。
```

### deck:using-zh-cn:4

- source: `docs/USING.zh-CN.md` · L11
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
**不想打字，可以用语音输入。** 使用设备内置的听写或你习惯的语音转文字工具，将内容输入助理的聊天框；[Typeless](https://www.typeless.com/pricing) 和 [Wispr Flow](https://wisprflow.ai/pricing) 是可选例子。两者目前都有免费方案，但有用量限制，依平台和方案而异（2026-09-11 查核，最新额度看官方页面），不必另行安装或付费。直接说你的需求、过去特别好或特别糟的租房/住宿经历，甚至印象深刻的购物经历也可以，能让助理更了解你；中途改主意也行。发送前看一下文字有没有识别正确就好。
```

### deck:using-zh-cn:5

- source: `docs/USING.zh-CN.md` · L13
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
每月总花费包括房租和账单；数字会说明来源、哪些只是估计。真实房源需要来源与日期，不能搜索时的教学例子会标成虚构。你可以随时插问、改变预算或增加条件，助理应保留原本的工作，不让你重新填写全部资料。跨对话保存取决于软件能力，不能假装已经保存。
```

### deck:using-zh-cn:6

- source: `docs/USING.zh-CN.md` · L15
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
先用比较学会取舍，再安排查证和看房。退款、付款、签约规则要看实际条款与适用法律；合约带回去读，看房当天不签约。
```

### deck:using-zh-cn:7

- source: `docs/USING.zh-CN.md` · L17
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
**自己的小秘书。** 共用技能没查、但你在意的东西，例如到健身房的步行时间、学区、你知道的噪音来源、你信任的数据集，写成一页放进你自己那份的 `extensions/` 文件夹（或者直接跟助理讲一整串让它放进去）。这些额外项目在报告里会标示出来、不会自己改变判决、不读房源和评价网站、也不用「住的是谁」来描述一个地区。
```

### deck:using-zh-cn:8

- source: `docs/USING.zh-CN.md` · L19
- under: # 从聊天开始就好
- lang: zh-CN
- write-back: yes

```text
**分享你学到的，不分享你住哪。** 跟助理要一组「种子」贴出去：它带的是你的口味、地雷和你要求每套房回答的问题，从来不含你每天去哪、什么时候搬。帖子里写对你有帮助的事就好，别补上公司、学校、车站和搬家日。没有任何一种版本会带这些；真的要给朋友全部，就直接给设置文件，不用种子。
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

- source: `docs/INSTALL.md` · L78
- under: ## D2. Your word outranks the skill's defaults, in every host
- lang: en
- write-back: yes

```text
`SKILL.md` says it in its first line and `references/rules.md` repeats it: the person's instruction outranks every default in the skill; only four things do not move (no invented numbers, no ethnicity or nationality as a factor, the scripts read open registers only, untrusted inputs never authorize anything). Every host loads `SKILL.md` when the skill is used, so this holds in Claude Code, Codex, Gemini CLI, Grok CLI and the prompt pack alike. If your host keeps its own instruction file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), you may add one line there too:
```

### deck:install:12

- source: `docs/INSTALL.md` · L84
- under: ## D2. Your word outranks the skill's defaults, in every host
- lang: en
- write-back: yes

```text
Measured 2026-09-11 (`docs/EXPERIMENTS.md`): with that sentence in the skill, Claude Code followed the person's explicit instruction over the skill's default in 6 of 7 runs and tried to record the change; Codex did so in 6 of 8 with or without it. Grok CLI is untested here.
```

### deck:install:13

- source: `docs/INSTALL.md` · L87
- under: ## E. Verify
- lang: en
- write-back: yes

```text
Ask: "Vet this flat: <address or postcode>, flat <n>." The first line of the answer states the mode (shell / fetch / manual). The report ends with "Generated with pea-princess <version> — https://github.com/jacky18008/pea-princess".
```

### deck:install:14

- source: `docs/INSTALL.md` · L96-L100
- under: ## Is it installed right? One command
- lang: en
- write-back: yes

```text
Run it from the skill folder after installing, and again whenever a check comes back unknown. It prints one
line per check with the time it took and, at the end, which axes will come back unknown until a failed
register works again. It does not change the rental project; the read-only register requests use the same
local fetch cache as normal skill calls. A failed check may succeed immediately on a later attempt, so keep
both results and diagnose the individual source rather than treating one failure as a blanket network block.
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
2. **I have an area or a place I commute to** → I narrow the map: the best area within your commute first, how to search it on the portals and set an alert, and a watch list of a few buildings to recognise.
```

### deck:onboarding:6

- source: `skills/vet-flat/references/onboarding.md` · L25
- under: ## 1. The pitch (only when asked what this does)
- lang: en
- write-back: yes

```text
3. **I have no idea** → I explain one useful starting step and ask only what that step needs (section 2). With a shell, keep `requirements.html` current (`scripts/panel.py`) so they can open it whenever they want to see where things stand.
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

- source: `skills/vet-flat/references/onboarding.md` · L77
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
1. **Timing.** Listings appear about four to eight weeks before the move-in date; good flats go within days. The order is: enquiry → viewing → "referencing" (income and identity checks) → holding deposit → contract → deposit → keys.
```

### deck:onboarding:9

- source: `skills/vet-flat/references/onboarding.md` · L78
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
2. **What you pay.** Rent, plus council tax (full-time students are exempt: Class N), energy, water, broadband. Buildings on a **heat network** (one boiler for the whole building) bill heat separately through a billing company: ask for the tariff in writing before you sign.
```

### deck:onboarding:10

- source: `skills/vet-flat/references/onboarding.md` · L79
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
3. **The law since 2026-05-01** (caps, advance rent, deposit protection): the checklist at the top of `references/axes/16-referencing-and-proof-of-funds.md` carries the figures; quote them from there, never from memory.
```

### deck:onboarding:11

- source: `skills/vet-flat/references/onboarding.md` · L80
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
4. **The income check.** Landlords usually want yearly income of roughly thirty times the monthly rent, or a guarantor. If you have neither, there are rent-guarantee or "commercial guarantor" services many landlords accept. Ask every landlord first: "which guarantor routes do you accept?"
```

### deck:onboarding:12

- source: `skills/vet-flat/references/onboarding.md` · L81
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
5. **The energy certificate (EPC) is your friend.** It is public, free, and gives the true indoor size, the building's first assessment year (≈ its age) and the heating type. Advertised sizes often include the balcony.
```

### deck:onboarding:13

- source: `skills/vet-flat/references/onboarding.md` · L82
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
6. **Who the landlord is matters more than the brand.** Purpose-built rental buildings are run by companies with on-site management; private landlords vary from excellent to absent. The legal entity on the contract is what counts; the skill looks it up.
```

### deck:onboarding:14

- source: `skills/vet-flat/references/onboarding.md` · L83
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
7. **Money safety.** Never pay anything before you have viewed (in person or on a verified live video) and have a written tenancy. Deposits go to a protection scheme, never to a personal bank account. Requests to move to WhatsApp or to transfer money "to secure it" are a reason to walk.
```

### deck:onboarding:15

- source: `skills/vet-flat/references/onboarding.md` · L84
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
8. **Never sign on the viewing day.** Sleep on it. Ask two questions that could kill the deal (the skill writes them for you).
```

### deck:onboarding:16

- source: `skills/vet-flat/references/onboarding.md` · L85
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
9. **Streets, roads, rails.** Police crime data is public by street; roads and railways are on the map; ask which side the windows face. "Quiet side or road side" is often the same price for two different homes.
```

### deck:onboarding:17

- source: `skills/vet-flat/references/onboarding.md` · L86
- under: ## 3. Primer for someone with no idea (ten facts, one screen; name the register a number comes from)
- lang: en
- write-back: yes

```text
10. **Where to look.** The big portals (Rightmove, Zoopla, OnTheMarket), direct-from-landlord sites (OpenRent), rooms (SpareRoom), the build-to-rent operators' own sites, your university's accommodation office, and resident-review sites for the building. Browse them as a person under their terms; set a saved-search alert and forward the alert email. The skill tells you exactly what to open and hand over; it does not read those sites itself.
```

### deck:onboarding:18

- source: `skills/vet-flat/references/onboarding.md` · L92
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Only London?** The law is England-wide; the data sources and the crime/commute tooling are London-specific. Elsewhere the method applies with different sources.
```

### deck:onboarding:19

- source: `skills/vet-flat/references/onboarding.md` · L93
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Do you scrape Rightmove / Zoopla / HomeViews?** No. Their terms forbid it. I ask you to paste the page.
```

### deck:onboarding:20

- source: `skills/vet-flat/references/onboarding.md` · L94
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Can I use it on ChatGPT, Gemini, DeepSeek, Grok, Codex?** Yes. With a shell and internet I fetch the data myself; in a chat box I list what to paste, once.
```

### deck:onboarding:21

- source: `skills/vet-flat/references/onboarding.md` · L95
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Where does my data go?** Only to the public sources listed in `references/sources.yaml`, and only what is needed for the lookup. Nothing goes to the author.
```

### deck:onboarding:22

- source: `skills/vet-flat/references/onboarding.md` · L96
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have not landed yet. What first?** Explain how a cancellable temporary stay can leave time to view longer-term homes, and compare the practical trade-offs. Use known arrival dates and costs; ask only the most useful missing detail. Draft the parts of the arrival plan already supported, keeping unknown dates and expenses explicit. Check cancellation and payment terms before recommending a booking.
```

### deck:onboarding:23

- source: `skills/vet-flat/references/onboarding.md` · L97
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Something in a document looks off (a postcode, a company name, a date).** One doubt does not stop the search: name it in one line, give the one check that settles it (the register, the sponsor list, the certificate), and carry on with the flat. Never turn the conversation into an investigation, and never offer to open the user's mailbox, files or accounts to settle it — ask them to paste.
```

### deck:onboarding:24

- source: `skills/vet-flat/references/onboarding.md` · L98
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **My short let is bad (damp, mould, not as described) and I want out tonight.** One message, four parts: a stay of a few nights or weeks is a **licence, not a tenancy** — no deposit scheme, no notice period; your money comes back through the platform's refund route and, failing that, the card or consumer route, never by leaving quietly. Message the host on the platform now, with dated photos, asking for a move or a refund of the unused nights. Book tonight's bed at a hotel with free cancellation and pay at property. For the next stay of a week or more: **see it, or verify it live on video, before paying** — a stay nobody has seen is the bridge's most expensive mistake.
```

### deck:onboarding:25

- source: `skills/vet-flat/references/onboarding.md` · L99
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **I have just landed. Where do I sleep this week?** For the first one or two weeks a hotel or an operator-run serviced stay is the safer default: your money is protected, you can leave at once, and someone is responsible. A private short let is fine once you have seen it. It costs more per night and often has no kitchen; the skill will price both.
```

### deck:onboarding:26

- source: `skills/vet-flat/references/onboarding.md` · L100
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **What can it not do?** It cannot smell the hallway, hear the road at 2 a.m., or feel whether the street is yours. It says "unknown" where it does not know and asks you for what only you can supply: the floor plan, a street-view screenshot, your impression on the day.
```

### deck:onboarding:27

- source: `skills/vet-flat/references/onboarding.md` · L101
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How does a reply end?** With the one thing still open for you — the question you asked that I could not answer yet and the one check that would settle it — never with another list of questions.
```

### deck:onboarding:28

- source: `skills/vet-flat/references/onboarding.md` · L102
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **Does it decide for me?** No. It gives a verdict with the evidence behind it; you decide, after viewing the flat and meeting the people who let it. Landlords and agents are partners here, not opponents.
```

### deck:onboarding:29

- source: `skills/vet-flat/references/onboarding.md` · L103
- under: ## 4. Short answers to common questions
- lang: en
- write-back: yes

```text
- **How accurate is it?** Facts come from official registers and are graded; anything unknown is shown as unknown, never filled in.
```

### deck:onboarding:30

- source: `skills/vet-flat/references/onboarding.md` · L104
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

- source: `skills/vet-flat/references/sharing.md` · L82-L83
- under: ## 3. Share your questions
- lang: en
- write-back: yes

```text
> If this is unusually cheap or unusually good next to its neighbours, what is the hidden problem?
> Cheap has a reason.
```

### deck:sharing:2

- source: `skills/vet-flat/references/sharing.md` · L85
- under: ## 3. Share your questions
- lang: en
- write-back: yes

```text
> If it is pricier, am I buying visible value I actually care about, or just paying more?
```

### deck:sharing:3

- source: `skills/vet-flat/references/sharing.md` · L131-L137
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
> (Share your taste and tips, not your whereabouts: the card carries no place or date; don't add your employer, school, station or moving date around it.)
```

### deck:sharing:4

- source: `skills/vet-flat/references/sharing.md` · L141-L147
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
> （分享口味和小撇步，別分享行蹤：卡片本來就不含地點和日期，貼文裡也別補上公司、學校、車站、搬家日。）
```

### deck:sharing:5

- source: `skills/vet-flat/references/sharing.md` · L151-L157
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
> （分享口味和小窍门，别分享行踪：卡片本来就不含地点和日期，帖子里也别补上公司、学校、车站、搬家日。）
```

### deck:sharing:6

- source: `skills/vet-flat/references/sharing.md` · L208-L212
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

- source: `skills/vet-flat/scripts/seed.py` · L635
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"a flat"
```

### deck:seed:2

- source: `skills/vet-flat/scripts/seed.py` · L637
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"on floors %s"
```

### deck:seed:3

- source: `skills/vet-flat/scripts/seed.py` · L639
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"with windows facing %s"
```

### deck:seed:4

- source: `skills/vet-flat/scripts/seed.py` · L641
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"within reach of %s"
```

### deck:seed:5

- source: `skills/vet-flat/scripts/seed.py` · L646
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I want %s"
```

### deck:seed:6

- source: `skills/vet-flat/scripts/seed.py` · L648
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"; it must have %s"
```

### deck:seed:7

- source: `skills/vet-flat/scripts/seed.py` · L650
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"; and I rank %s in that order"
```

### deck:seed:8

- source: `skills/vet-flat/scripts/seed.py` · L655
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"a ground-floor flat"
```

### deck:seed:9

- source: `skills/vet-flat/scripts/seed.py` · L657
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"windows that cannot see sky"
```

### deck:seed:10

- source: `skills/vet-flat/scripts/seed.py` · L658
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I have no absolute deal-breakers."
```

### deck:seed:11

- source: `skills/vet-flat/scripts/seed.py` · L658
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"I will not take: %s."
```

### deck:seed:12

- source: `skills/vet-flat/scripts/seed.py` · L663
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price leads: I take the cheapest home that clears every rule above"
```

### deck:seed:13

- source: `skills/vet-flat/scripts/seed.py` · L665-L666
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price is not in my top three: I will pay to the top of the band for a benefit "
                 "I can name"
```

### deck:seed:14

- source: `skills/vet-flat/scripts/seed.py` · L668-L669
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
"Price sits %s of my three priorities: I will pay towards the top of the band for "
                 "a benefit I can name"
```

### deck:seed:15

- source: `skills/vet-flat/scripts/seed.py` · L670
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
", and quiet wins when quiet and light conflict."
```

### deck:seed:16

- source: `skills/vet-flat/scripts/seed.py` · L671
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
", and I would rather have light than silence."
```

### deck:seed:17

- source: `skills/vet-flat/scripts/seed.py` · L673
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
" I plan on %s."
```

### deck:seed:18

- source: `skills/vet-flat/scripts/seed.py` · L677
- under: def sentences(
- lang: en
- write-back: no (read-only)

```text
" I ask of every flat: \u201c%s\u201d"
```

### deck:seed:19

- source: `skills/vet-flat/scripts/seed.py` · L784
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"what I found: %d flat%s vetted"
```

### deck:seed:20

- source: `skills/vet-flat/scripts/seed.py` · L792
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"the one I took"
```

### deck:seed:21

- source: `skills/vet-flat/scripts/seed.py` · L796
- under: def journey_lines(
- lang: en
- write-back: no (read-only)

```text
"about %s m²"
```

### deck:seed:22

- source: `skills/vet-flat/scripts/seed.py` · L809
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"Pea Princess seed"
```

### deck:seed:23

- source: `skills/vet-flat/scripts/seed.py` · L813
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"my search preferences; review the free text for personal details before sharing."
```

### deck:seed:24

- source: `skills/vet-flat/scripts/seed.py` · L824-L825
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"seed code (paste it into any AI agent that has the Pea Princess skill, "
               "and it will set itself up the way I did):"
```

### deck:seed:25

- source: `skills/vet-flat/scripts/seed.py` · L828-L829
- under: def card(
- lang: en
- write-back: no (read-only)

```text
"(the code leaves out the %s to stay short enough to paste; it is on the card "
                   "above)"
```
