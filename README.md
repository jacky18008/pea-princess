<p align="center">
  <img src="docs/assets/dulac-1911-the-princess-and-the-pea.jpg" width="300" alt="豌豆公主，Edmund Dulac 1911 年插圖">
</p>
<p align="center"><sub>Edmund Dulac, 1911 · 公有領域</sub></p>

<h1 align="center">Pea Princess · 豌豆公主</h1>

<p align="center"><b>繁體中文</b> · <a href="README.en.md">English</a></p>

<p align="center">用英國官方與公開資料，替你尻洗一間倫敦出租公寓，<br>並老實說出它不知道的事。</p>

<p align="center">
  <img alt="技能文字：CC BY 4.0" src="https://img.shields.io/badge/skill%20text-CC%20BY%204.0-8A2846">
  <img alt="程式碼：MIT" src="https://img.shields.io/badge/code-MIT-2F6F55">
  <img alt="格式：Agent Skills" src="https://img.shields.io/badge/format-Agent%20Skills-1F1D26">
  <img alt="房源網站：從不抓取" src="https://img.shields.io/badge/listing%20sites-never%20fetched-6B6679">
</p>
<p align="center"><sub>作者：陳先灝 Hsien Hao (Jacky) Chen · <a href="https://www.linkedin.com/in/jacky-chen-a49177137/">LinkedIn</a></sub></p>

這是一個在倫敦檢視跟搜尋房源用的 agent skill，用官方與公開的英國資料，像謹慎的驗屋師一樣尻洗一間倫敦出租公寓：身份、面積、屋齡、供暖、周邊工地、治安、管理評價、仲介合規、價格、採光、全部月成本、通勤，最後給出判決。任何支援 [Agent Skills](https://agentskills.io) 格式的 agent 都能用（Ex: GPT, Claude, Grok, Gemini, pi-agent, DeepSeek, etc）；一般的 chat mode, 也可以，只是建議使用 agent mode, 複雜的任務會比較穩定。跟 AI 講白話文就好。

## 為什麼叫「豌豆公主」
童話裡，只有真正的公主能隔著二十層床墊感覺到那顆豌豆。在這裡，**你**就是那位公主。這個工具幫你一層一層把床墊掀開：翻登記資料、數犯罪案件、查規劃申請和公司申報文件，告訴你豌豆可能藏在哪裡。但只有你感覺得到：親自去看房、走一走那條街、跟仲介和房東聊一聊。這份報告是一道濾網，趕時間的時候，它也只是一道濾網。它的第一個責任，是說出自己不知道什麼，然後開口問你。

作者自己的經歷，發在社群的繁體中文原文：[到了倫敦才發現自己有病，是公主病](docs/posts/2026-09-launch.zh-TW.md)。

## 從這裡開始，不需要終端機

三條路，從最省事到最手動。挑一條跟你現在在用的工具對得上的。

1. **你在用 agent 應用程式**（Claude Code、Codex、Cursor、Gemini CLI、Grok Build……）。把這句話貼給它，然後等：

   > 請安裝 https://github.com/jacky18008/pea-princess 這個技能，裝好後告訴我它能做什麼

   Agent 會把這個專案抓下來，用 `pea-princess` 這個名字把技能裝好，然後回答你。從此就只要講話：「尻洗這間房：」再把房源貼上去。

2. **你在用有 Skills 功能的聊天軟體**（claude.ai、Claude Cowork、ChatGPT Business）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下載 `pea-princess-skill.zip`，打開 Settings → Skills → Upload，選這個 zip。然後問它「這能幹嘛？」。

3. **你在用沒有 Skills 的聊天軟體**（ChatGPT Plus Projects、Grok Projects、Gemini Gems、Perplexity Spaces）。到 [Releases](https://github.com/jacky18008/pea-princess/releases) 下載提示詞包，把 `INSTRUCTIONS.md` 貼進專案的指示欄，再附上 `references/` 裡的檔案。之後技能會一次告訴你要貼什麼。

不用寫程式，不用改設定檔：接下來全部都是一句一句的話，打字或用語音都行。五分鐘上手看 [USING.zh-TW.md](docs/USING.zh-TW.md)；每一種安裝方式和它的注意事項在 [INSTALL.md](docs/INSTALL.md)。

### 跟它說說你自己

你不用填表格。把你的需求和你的雷點講給它聽就好——含帳單的預算、通勤、「再也不要住地下室」——還有你住過的地方，最好的和最差的；連你還記得的購物習慣，都能讓它知道你是怎麼做決定的。它會把這些記在你的 `profile.yaml` 裡，每次要改都先讓你看過，你中途改變主意也沒關係。懶得打字就用講的：手機或電腦內建的語音輸入，或是 Typeless、Wispr Flow 這類工具，中英文混著講也沒問題。語音輸入真的超讚。

## 它查什麼，答案從哪裡來

| 問題 | 答案從哪裡來 |
|---|---|
| 這間房是不是廣告上寫的那間——哪一戶、多大、多舊、怎麼供暖？ | GOV.UK 能源證書登記冊 |
| 隔壁在蓋什麼，蓋多高？ | GLA 的規劃申請案 |
| 這條街安不安全？晚上走回家呢？ | police.uk 犯罪資料，六個月，300 公尺方框 |
| 房東或仲介到底是誰，有沒有合規？ | Companies House、Client Money Protect、Heat Trust、GLA 惡房東查詢 |
| 這個價位帶的租金合不合理？一個月真正要花多少？ | HM Land Registry 成交紀錄，加上技能自己的算式，每一項來源都列出來 |
| 採光、噪音、大馬路、夜間經濟 | OpenStreetMap、Defra 噪音地圖 |
| 通勤要多久？有沒有備用路線？ | TfL 行程規劃工具 |
| 文件流程：押金上限、預付租金、2026-05-01 起的租約規定、租客資格審查 | 技能內建的 Renters' Rights Act 2025 規定，加上你自己的文件 |

每一項結論都帶著它的證據等級。查不到的東西，它會一次、用一則訊息問你。它不會自己去開房源網站：頁面由你交給它，[上手指南](docs/USING.zh-TW.md)裡有三種做法。

## 它只是篩子，房子要親自去看

這裡的每一句話，不是從登記簿讀來的，就是從你貼給它的東西讀來的。它聞不到霉味，聽不到半夜兩點的車聲，也看不到你問「房東到底是誰」的時候，仲介臉上的表情。所以請把報告當成一張「該看什麼」的清單，然後親自走一趟：

- **看房當下**：報告最後會給你兩個最可能改變你決定的問題，還有前三十分鐘要確認的東西——電表、鍋爐或熱網的收費方式、對著馬路的那扇窗、電梯、垃圾間。
- **跟房仲和房東聊**：問合約上是誰、押金會放進哪個保管機制、帳單包含哪些、綁約多久、什麼時候可以入住。合約帶回家慢慢看。看房當天絕對不要簽。
- **看完之後**：把你們的對話紀錄、房屋照片，還有他們傳給你的任何東西丟給它，請它跟報告對一遍。訊息裡講的話，在登記簿或文件點頭之前，都還不算事實。

作者會做這個，是因為在倫敦找房子真的很折磨人，而一個會自己去翻登記簿的助理，幫他少走了很多冤枉路。但它取代不了你自己的兩條腿。

## 哪種方案，用哪種模式

用你自己已經有的訂閱就好；做這件事，個人訂閱比按量計費的 API 金鑰划算不少，而且什麼都不用設定。比起純聊天，建議用 agent 模式（Claude Code、Codex、Grok Build、Cursor……）：這些檢查是一個步驟很多的長任務，聊天模式得你一步一步牽著它走。$20～$30 的方案先從 `lite` 開始，比較省 token。

| 你付的是 | 用在哪裡 | `budget_mode` 設成 | 要知道的事 |
|---|---|---|---|
| ChatGPT Plus 約 £20 | Codex（app、CLI 或 IDE） | `lite` | token 給得比較大方，用量數字也公布得最清楚，你可以照著規劃；記得把 Codex 的子 agent 關掉（`[agents] enabled = false`），不然每一次回答會貴上五到二十倍 |
| Claude Pro 約 £20 | Claude Code，或把技能上傳到 claude.ai | `lite` | 很好用；但沒有公布用量數字，而且跟聊天共用同一個額度池 |
| Claude Max 或 ChatGPT Pro，£100 起跳 | 同上 | `standard`，最後在比的那兩間房用 `deep` | 作者自己的配置：跑腿的交給 Codex，需要判斷的交給 Claude 最強的 Fable 5.1——疑難雜症和最終建議（貴有貴的道理） |
| SuperGrok 或 X Premium+ | Grok Build CLI | `lite` | 它跑得動這個技能，但我們第一次實測，一個回答花了大約十分鐘、好幾百萬個 token；還不適合當每天的預設 |
| 沒有 Skills 的聊天軟體 | 提示詞包 | manual | 技能會一次列出要貼什麼 |
| API 金鑰 | Codex、OpenCode 或 Gemini CLI 搭配便宜的模型 | `standard` | 快速查一間只要幾便士，掃一個區域不到 £1，代價是要自己弄一把金鑰和一個設定檔 |

設定一次就好：寫在你的 `profile.yaml`（`budget_mode: lite`），或直接講「這間用 deep」，助理會確認後改。這幾個模式查的是同一批東西，差別只在深度：`lite` 一間房控制在十次抓取以內，硬性條件、判決和那兩個問題照樣會給；`standard` 是平常的完整版；`deep` 再加上進了決選名單才需要的項目。有兩件事是在真實房子上量出來的，不是意見：深度比模型大小重要（強模型跑 `lite` 的分數，輸給弱模型跑 `standard`），而且會亂編數字的都是便宜的組合——這也是為什麼這裡每一個數字都必須帶著來源，不然就要標成不知道。細節和注意事項：[INSTALL.md](docs/INSTALL.md)、[預算模式](skills/vet-flat/references/budget-modes.md)、[實驗紀錄](docs/EXPERIMENTS.md)。

## 三種模式
| 模式 | 你手上有 | 會發生什麼 |
|---|---|---|
| Shell | python3 + curl + internet | 腳本負責抓取和解析；模型只讀精簡過的 JSON |
| Fetch | 有網址抓取工具，沒有 shell | 只用公開 GET 的來源；其餘的技能會問你 |
| Manual | 一個聊天框 | 技能會一次列出要開、要貼的頁面，並附上連結 |

> 狀態：**草稿**。本機蒐集、區域掃描、報告產生和實驗框架都已經做好了。處理個人資料或要做發布之前，先讀[安全與隱私邊界](SECURITY.md)。使用方式：`docs/INSTALL.md`、`docs/SCRIPTS.md`、`docs/CONVENTIONS.md`。

**發布方式：** 下載這個技能／工具，用你自己的 agent 跑。Pea Princess 不代管模型工作程序，也不碰訂閱帳號的憑證。本機的人物實驗室只是測試用的夥伴。詳見[桌機／手機的界線、供應商訂閱政策、發布關卡](docs/local-product-and-provider-policy.md)。

<details>
<summary><b>給工程師：安裝指令、腳本、基準測試、測試</b></summary>

### 安裝
```bash
# most agents (Codex, Gemini CLI, Cursor, Copilot, OpenCode, Cline, Goose, pi, OpenClaw, Hermes…)
npx skills add jacky18008/pea-princess
# Claude Code
/plugin marketplace add jacky18008/pea-princess && /plugin install pea-princess@pea-princess
# claude.ai / Claude Cowork / ChatGPT Skills: upload the zip from Releases
# then, on any host with a shell: is it installed right? (one request per open register)
python3 ~/.claude/skills/pea-princess/scripts/doctor.py   # or the folder your agent installed it to
```
這個技能安裝和呼叫的名字都是 **`pea-princess`**；上傳用的檔案是 `dist/pea-princess-skill.zip`。專案原始碼還是放在 `skills/vet-flat/`，這樣既有的腳本路徑和實驗紀錄才不會失效。這就是一個技能，一個安裝名稱。

Codex：把沙箱網路打開（`sandbox_workspace_write.network_access = true`），或改用 manual 模式。

### 腳本（只用 Python 3.9 標準函式庫；網路走 curl）
全部在 `skills/vet-flat/scripts/`；每一支都印出一個 JSON 物件，裡面有 `source_url`、`retrieved_at`、`http_status`、`ok` 和一個證據等級。用法細節在 `docs/SCRIPTS.md`。

| 腳本 | 來源（官方？需要金鑰？） | 能拿到什麼 |
|---|---|---|
| `epc.py` | GOV.UK EPC register (official, no key; HTML only) | 依郵遞區號／街道搜尋、單一證書、整棟樓的輪廓（面積分布、首次評估年份、供暖、氣密性）。10/10 筆面積已驗證 |
| `geo.py` | postcodes.io (open) | 郵遞區號 ↔ 座標、鄰近郵遞區號、半徑內的六角格覆蓋、邊界框 |
| `crime.py` | data.police.uk (official, no key) | 固定六個月、約 300 公尺方框內的資料，分類、掠奪型子集、定錨點、±20 公尺敏感度、走回家的路廊 |
| `commute.py` | TfL Unified API (official, no key) | 門到門的行程（全部／軌道／公車）、附近車站、罷工同族的備援等級 |
| `company.py` | Companies House (official, no key) | 帶狀態的搜尋、公司概況（SIC、抵押權、董事、財報）、申報文件、用註冊地址找住戶管理公司 |
| `redress.py` | Client Money Protect, Heat Trust, GLA rogue landlord checker (open) | 仲介的 CMP 會籍、熱網的站點／供應商、已公布的裁罰紀錄；PRS／TPO 要手動查 |
| `landregistry.py` | HM Land Registry price-paid linked data (official, no key) | 依郵遞區號查成交紀錄、用最早的新成屋成交當作完工年份的證據；產權謄本要手動查（£7） |
| `planning.py` | GLA Planning Datahub (open; all 33 boroughs) | 依地理距離抓半徑內的申請案、高樓提示、核准條件的文字 |
| `roads.py` | OpenStreetMap via Overpass (open) | 最近的大馬路、地面鐵路、隧道口、夜間經濟、氣味來源、超市、可能擋住採光的建物（含方位角與仰角） |
| `render.py` | — | `report.json` → HTML 或 Markdown，並用 `references/report-schema.json` 驗證 |

沒有 shell 的人要看報告排版：用瀏覽器打開 `viewer/viewer.html`，把 JSON 貼進去。需求頁面對另一個檔案也是同樣的做法：`scripts/panel.py --profile profile.yaml --out requirements.html` 會寫出一頁唯讀的現況，讓人隨時想看就打開。沒有任何助理會自己寫 HTML；模型寫 YAML 和 JSON，由腳本負責排版。

### 問它能做什麼
問它 **「這能幹嘛？」**（或 "What can this do?"）。答案來自 `skills/vet-flat/references/onboarding.md`：一段簡短說明、三個起點（有房源 → 尻洗它；有區域或目的地 → 掃一遍；完全沒概念 → 十個基本事實加六個帶建議預設值的問題）。你自己的規則寫在 `profile.yaml`（預算、面積、房型、不能接受的條件、優先順序，還有 `budget_mode`——哪個方案該設哪個值，看「哪種方案，用哪種模式」那張表）。Agent 一定要問的硬問題在 `references/questions.md`。

### 基準測試（事實在每個模型上都要對；判決可以不一樣）
`evals/evals.json` 收了 7 個行政區的 8 間真實房子，加上 2 個對話情境（「這能幹嘛」、「我完全沒概念」），標準答案由專案自己的抓取腳本在 2026-09-03 產生。`bench/grade.py` 評分的項目有事實召回率、捏造、引用、對未知的誠實度、硬性條件的一致性；`bench/run.py --dry-run` 會印出 Claude Code、Codex、Gemini CLI 或 OpenAI 相容 API 的完整指令。詳見 `bench/README.md`。

**要跑哪一種設定：** `docs/EXPERIMENTS.md` 記錄了最早的看房比較實驗。[後來的上下文消融實驗](docs/ablation-2026-09-09/results.md)包含生成成本和來源檢視：在測到的規模下，額外的摘要、結構化記憶和多次檢索呼叫並沒有省下 token。起點就維持「一個 agent 帶完整上下文」；四角色流水線還在實驗階段。這些研究量的是不同的任務，不是一份通用的模型排名。

**長時間的專案和會變的需求：** [session harness](docs/session-harness.md) 會保存使用者的原話、帶版本的需求和條件式例外、來源快照、目標、待辦和執行狀態。受管理的 runner 自己把當前的封包塞進去，並拒絕過期的結果。`AGENTS.md`／`CLAUDE.md` 保持簡短，只連到詳細規則；光放指標不能保證對方會去讀。[生命週期驗證](docs/session-harness-validation.md)測的是不呼叫模型也能復原，不是品質等價或省 token。

**想試一整段人物對話：** 跑 `python3 tools/persona_playground.py`，再打開它印出來的本機網址。[互動實驗室](docs/persona-playground.md)用你本機的 Codex 登入來產生動態的人物回覆和助理答案，支援單步／連續／暫停、排隊的真人提問、情境修訂、私有歷史和共用的用量上限。16 張人物卡都有，以清楚標示的聊天改編版呈現；這是本機 alpha，沒有公開部署，也沒有隱藏的模型裁判。

**社群回饋，第一階段：** 打開[本機選項表單](community/index.html)，照著[指南](docs/community-feedback-stage1.md)做。公開的 JSON 只放受控的選項；選填的文字留在作者自己的裝置上。本機的驗證、匯入和搜尋用的是虛構的示範目錄。目前還沒有線上投稿服務，也沒有真實的評論資料集。

**看的是整段對話，不是單一回答：** `docs/JOURNEYS.md` 為九段寫好腳本的多輪旅程評分，`docs/PERSONAS.md` 再往前一步——十六個由模型扮演的虛構人物，搭配一個決定性的控制器保管他們的文件，讓任何東西都編不出來；裁判必須引用自己的證據；每個人還配一個只動一項設定的對照探針。`python3 bench/personas.py --matrix pilot --dry-run` 不呼叫模型就能印出整份計畫。

### 測試
```bash
python3 -m unittest tests/test_epc.py
```

</details>

## 這裡不會有的來源
Rightmove、Zoopla、OnTheMarket、OpenRent、HomeViews、Trustpilot、Airbnb、Booking.com 在這裡只會出現名字。它們的條款不希望程式自動存取，所以這個專案不提供任何做法；技能會向你要頁面（PDF、截圖或純文字），不會自己去開房源連結。這包沒有這些網頁的爬蟲，也不能鼓勵你讓 agent 去爬蟲。

## 改成你的樣子

技能就是一個資料夾，裡面是 Markdown 和幾支腳本，這一包本來就是設計來讓你隨手改的。不用讀程式碼：跟你的 agent 用講的。

- **你的規則，用你的話講。** 「含帳單上限改成 £2,300」、「安靜比採光重要」、「只問我錢的那八題」。助理會先列出要改什麼，等你說好才寫進你的 `profile.yaml`。查多深也一樣：$20 方案用 `lite`，認真看的房子用 `deep`。
- **你自己的檢查項目。** 共用技能沒查、但你在意的東西（到健身房的步行時間、學區、你知道的噪音來源），寫成一頁放進 `extensions/`，或直接口述一串讓 agent 幫你寫。報告裡會標成你自己加的，不會自己改變判決。
- **改技能本身。** 跟 agent 說哪裡不順、少了什麼：「每份報告先講每月總花費」、「加一項高樓層沒電梯的檢查」、「用粵語問我問題」。它會改 `skills/vet-flat/` 裡的檔案；`python3 -m unittest discover -s tests` 會告訴你有沒有弄壞什麼，報告格式有規格檔守著，檢視器照樣讀得懂。
- **你的私人版本。** 作者自己有一個很吃 token 的「超無敵尻洗版」；你的可以是一個 fork，或只是一個 `extensions/` 資料夾。要公開任何東西之前，把 `profile.yaml`、`.pea-state/` 和你的文件留在自己電腦上（見 [SECURITY.md](SECURITY.md)）。
- **別的國家。** 想做台灣版、美國版、歐洲版就 fork：要換的是查登記簿的腳本，對話規則直接帶走。記得保留署名（文字 CC BY 4.0、程式 MIT）並註明出處；作者很樂意交流。
- **分享心得，不分享地址。** 「分享我的種子」會給你一段短碼，帶的是你的口味和你要問的問題，從來不含你住哪、什麼時候搬。

任何主機都能先試這一句：

> 把這個技能改成每份報告開頭先講每月總花費，改完跑測試，告訴我你改了什麼。

## 授權與姓名標示（提案中）
文件和技能文字：CC BY 4.0。程式碼：MIT。每一份報告都會帶著 "Generated with pea-princess <version> — <source URL>"。請留著它。

插圖出自 Edmund Dulac 1911 年為 *Stories from Hans Andersen*（Hodder & Stoughton，倫敦）畫的彩頁，屬於公有領域。`docs/assets/mark.svg` 裡的標誌（七層床墊下的一顆豌豆）是原創的，跟文件一起以 CC BY 4.0 釋出；`docs/assets/social-preview.png` 是同一個標誌做成的 1280×640 預覽卡。

## 作者的聯絡方式

陳先灝 Hsien Hao (Jacky) Chen — [LinkedIn](https://www.linkedin.com/in/jacky-chen-a49177137/)。有問題、想法，或你自己找房的故事，歡迎在這裡開 issue 或到 LinkedIn 私訊。
