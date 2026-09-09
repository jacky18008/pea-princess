# 長期專案 harness：官方機制、在地設計與驗證範圍

查核日期：2026-09-09。這份文件只整理官方文件及本機唯讀觀察，提出驗證計畫；不宣稱下列 adapter 已安裝、hook 已啟用、實驗已完成，或模型已達成「零遺失」。沒有為此呼叫付費模型。

核心結論：把需求原文、有效條件、來源版本、任務依賴及驗證證據保存在可重建的檔案狀態中，再於啟動、需求變更與壓縮後載入當前最小必要狀態。模型摘要可以協助閱讀，不能單獨擔任需求、授權或完成證據的唯一紀錄。下面的官方支援和我們自行採用的資料一致性規則刻意分開。

## 本機觀察與查核方式

唯讀執行 `codex --version`、`codex --help`、`claude --version`、`claude --help`：本機是 Codex CLI **0.153.4**、Claude Code **2.1.261**。Help 顯示 session resume／fork、Claude 的 `--autocompact` 與 `--no-session-persistence` 等選項；這只能證明已安裝 CLI 的介面，不能證明當前 task 的 hook 配置或完整生命週期行為。沒有讀取或輸出 API key、cookie、個人配置內容，也沒有修改全域設定。

OpenAI 文件先前已有本機 repo／skill 查核背景，本輪僅對需確認的行為查閱官方網域。以下每個來源都實際開啟正文；OpenAI 部分舊網址現在轉址至 `learn.chatgpt.com`。CLI、桌面 App、Agent SDK、Responses API 分屬不同介面，不能互相推定支援。

## 官方已明確記載的機制

| 機制 | 已核實的官方說法 | 對本專案的含義與邊界 |
|---|---|---|
| Codex `AGENTS.md` | 啟動時建立 instruction chain，通常每個 launched TUI session 一次；由全域及 root→cwd 疊加；預設合計上限 32 KiB。 | 適合放穩定規則與狀態入口，不能假定執行中修改檔案就自動重載。需要明確 refresh／讀取。 [官方 AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |
| Codex ExecPlans | Cookbook 把 ExecPlan 定義為可持續更新、可供新 session 接手的計畫文件，透過 `AGENTS.md` 約定使用。該篇現在標示 archived。 | 它是 prompting／文件慣例，不是特殊內建 transactional planner，也不是當前模型排名證據。借用目的、決策、進度、驗收及恢復段落即可。 [官方 PLANS.md recipe](https://developers.openai.com/cookbook/articles/codex_exec_plans) |
| Codex Goal mode | 官方現在記載 desktop、interactive CLI、IDE 可用 `/goal`；目標應包含 outcome、constraints、verification，同一 chat 可追加 steering。Goal 不擴張原有權限。 | 內建 goal 管持續推進；我們的 durable goal 紀錄管來源、版本與完成證據。二者需要對照，不能假定 App 狀態自動成為 repo 檔案。 [官方 long-running work](https://learn.chatgpt.com/docs/long-running-work) |
| Codex compaction API | Responses API 會回傳 opaque、encrypted compaction item；手動 `/responses/compact` 回傳的完整 window 應原樣接續，不應自行刪項。 | 這是 API conversation state，不是可人工稽核的業務狀態，也不是要求本機 Codex CLI 自行實作 Responses chaining。 [官方 compaction](https://developers.openai.com/api/docs/guides/compaction) |
| Claude `CLAUDE.md`／auto memory | Project-root `CLAUDE.md` 在 compact 後重新讀取；nested／path rules 在相關檔案被讀取時重載。Auto memory 起始載入 `MEMORY.md` 前 200 行或 25 KB，取較早上限，其他 topic files 按需讀取。 | 根檔只放短入口與規則；大文件切成 topic 不等於每次都已讀。`@path` imports 在啟動載入，不是免費的懶載入。記憶是 context，非強制執行配置。 [官方 memory](https://code.claude.com/docs/en/memory) |
| Claude Tasks | 官方記載 task list 可跨 compaction；`CLAUDE_CODE_TASK_LIST_ID` 可讓不同 session 使用 `~/.claude/tasks/` 的指定清單。 | 適合顯示待辦，不足以單獨證明需求版本、來源真偽與測試通過。不同模型／模式的 tool availability 要實測，不假定永遠有 Task tools。 [官方 task list](https://code.claude.com/docs/en/interactive-mode#task-list)、[環境變數](https://code.claude.com/docs/en/env-vars) |
| Claude session persistence | 可 resume／export；本機 transcript 是 JSONL，預設有 30 天清理期限，可配置；非互動模式可明確停用 persistence。兩個 terminal 不 fork 而 resume 同一 session，會交錯寫進同一 transcript。 | transcript 有助追溯，但不能充當永久封存或多 writer 的業務 transaction log。需要自己的保存期限、入口及並行規則。 [官方 sessions](https://code.claude.com/docs/en/sessions) |

### Hooks：有可用入口，但不能混用兩家的輸出契約

**Codex：**`SessionStart` 的 source 包含 startup／resume／clear／compact；root session compact 後，即使在 turn 中途，也會在緊接的 model request 前注入 `additionalContext`。`UserPromptSubmit` 提供 prompt。`PreCompact`／`PostCompact` 忽略純文字 stdout，使用 JSON；`continue:false` 可停止相應階段。Hook additional context 預設約 2,500-token threshold。MCP hook 缺 server、不可用或 error 不會自動阻擋，因此不可把它當作已證明 fail-closed 的保存機制。 [官方 Codex hooks](https://learn.chatgpt.com/docs/hooks)

**Claude Code：**`SessionStart(source=compact)` 可注入 context；`UserPromptSubmit` 帶使用者 prompt。`PreCompact` 現行版本可用 exit 2 或 block decision 阻擋；`PostCompact` 可取得生成的 compact summary，但沒有 decision control。`SessionStart` 也沒有 blocking control。Command／HTTP／MCP 的 `UserPromptSubmit` timeout 可能丟棄 context 後仍送出 prompt；Agent SDK callback 的該 timeout 則阻擋 prompt。依事件及 adapter 分別驗證，不能用舊版印象或一份通用 JSON 混套。 [官方 Claude hooks](https://code.claude.com/docs/en/hooks)

以上是機制摘要，不建議永久阻擋 compaction：已到 context-limit error 才攔截，可能直接讓 request 失敗。可靠流程應平時持續保存，compact hook 只作檢查／補強。這是本地設計選擇，不是官方承諾。

### 安裝介面備忘：模板先不啟用

Codex 支援 repo 的 `.codex/hooks.json` 或 `.codex/config.toml` inline `[hooks]`；各層會合併，並需信任 project 及目前 hook definition hash。Claude 支援 `.claude/settings.json` 或個人的 `.claude/settings.local.json`。建議只提交未啟用的範本；安裝時合併既有設定並檢查重複 handler。 [Codex 配置與 trust](https://learn.chatgpt.com/docs/hooks#where-codex-looks-for-hooks)、[Claude 配置位置](https://code.claude.com/docs/en/hooks#configuration)

以下是本地 adapter 的**配置形狀範例**，不表示該程式介面已定稿或已安裝。其他兩個事件沿用相同 handler；`UserPromptSubmit` 不需 matcher，`PreCompact` 可匹配 `manual|auto`。

Codex 範例：

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$(git rev-parse --show-toplevel)/tools/session_hook.py\"",
        "timeout": 10,
        "additionalContextLimit": 2500
      }]
    }]
  }
}
```

Claude 範例：

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "python3",
        "args": ["${CLAUDE_PROJECT_DIR}/tools/session_hook.py"],
        "timeout": 10
      }]
    }]
  }
}
```

Claude 的現行 `args` exec form 不經 shell；`${CLAUDE_PROJECT_DIR}` 進 worktree 後仍指原始 checkout，hook input 的 `cwd` 才跟隨工作位置。兩者需在 adapter 明確分工，避免讀錯狀態。 [Claude exec form 與 path placeholders](https://code.claude.com/docs/en/hooks#exec-form-and-shell-form)

錯誤回傳需依 host／event 測試：Codex compact hook 使用成功解析的 JSON `continue:false`；Claude PreCompact 使用 block decision 或 exit 2／stderr。不能把 generic exit 2 宣稱為所有事件皆會停止。也不使用 bypass-hook-trust 來暗中啟用模板。

### Anthropic 的 harness 經驗應如何採用

2025-11-26 的官方實驗使用 initializer、progress file、feature JSON、git commits 及逐步 coding；新 session 先讀紀錄、選尚未完成的功能，並實際測試後再改 passing status。重點是可接手的環境與可觀察的完成狀態，並非只要把模型放進 while loop 就會成功。這是一次工程經驗，不是 JSON 天然不會被錯改的保證。 [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

2026-03-24 的後續工作加入 planner／generator／evaluator，之後隨模型改善逐項移除不再必要的 scaffolding：取消 sprint 結構，減少評估頻次，將 evaluator 留給模型單獨較不可靠的部分。文章報告 harness 可以顯著增加成本；因此「最新做法」應理解為持續 ablation，而非固定堆疊最多 agent、最多 reset 或每步 judge。其展示沒有證明任意專案的品質等價或固定節省比例。 [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)

## 我們自行要求的檔案狀態契約

以下是本專案的建議驗收規格，不是 OpenAI／Anthropic 內建能力的轉述。具體欄位名稱交由 implementation contract 決定。

1. **先保存原文，再解讀。** 每個已收到的使用者需求保留原始文字、來源 channel／event ID、順序、時間及 hash；附件另保留原始 bytes 或可核對的固定版本。Hook 的 `prompt` string 未必涵蓋所有 UI 附件、排隊訊息或跨 task steering，adapter 必須對這些入口測試。不得把摘要當作 exact raw input。
2. **原文與 patch 分開。** 模型解讀產生結構化 patch，帶 base revision、對應原文 ID、修改欄位及理由。明確授權的更動可自動套用；模糊的部分標為 unresolved，不猜成已接受的硬條件。沒有要求使用者逐筆人工審核。
3. **現行条件與歷史有清楚關係。** 舊條件保留但標為 superseded／withdrawn；新 revision 指明取代哪個舊條件。沒有改到的約束继续有效。需求變更如從「租金上限」改成「含 bills 的總上限」，需要取代語義，不能只追加一句備註。
4. **文件和判斷可失效。** 每個 document 有 source ID、版本、hash、取得時間及信任標籤；每個 finding／decision 指向使用過的文件版本。文件內容或相關需求改變時，依賴它的結論、TODO、已通過驗證需重新檢查，不能沿用綠燈。
5. **TODO 與 workflow 是可驗證狀態。** 任務有 stable ID、前置依賴、狀態及 completion evidence；取消、blocked、superseded 與 completed 分開。不能因模型文字說「完成」就清掉未解依賴。Goal 只有在當前需求 revision 的驗收全滿足時才能完成。
6. **保存與恢復可重做。** 重複 event ID 不得重套 patch；stale base revision 不得靜默覆寫。多 writer 使用鎖／revision compare-and-swap；提交需要原子性；crash 中間態可辨識並恢復。Snapshot 是 event history 的 materialized view，不能與 event log 各自成為不同真相。
7. **重新載入有 receipt。** 每個 bootstrap／compact 後 prompt 記下 state revision、state hash、選入的 document IDs／hashes、未處理 user-event IDs、待辦及 next action。過期 snapshot 必须拒絕或重建。讀檔成功只證明資料已提供，不證明模型理解正確。
8. **信任與私密資料不混。** 網頁、評論、附件及 tool output 保持 untrusted data；不能因進入 state file、memory 或 hook output 就升成 developer instructions／user authorization。Raw input 可能含私密資料，預設 owner-only、排除公開 Git；version control 保存程式、schema、去識別化 fixtures、可分享文檔。

建議初始最小集合：一個 append-only 使用者事件／patch 記錄、一份可重建的現行狀態、一個 immutable document store／索引，以及一份短 bootstrap。Progress／TODO／goal 可先放在同一個 schema 裡，避免多份 Markdown 各寫一套近似狀態。公開範例與私密執行資料分離。

## 接续流程：先更新再消耗 model context

建議入口順序：收到輸入 → 保存 exact event → 產生並驗證 patch → 原子更新 current revision → 使受影響結果失效 → 生成最小 bootstrap → 呼叫模型 → 保存 action／結果／驗證證據 → 更新 progress。如果 interpretation 需要模型，保存 raw event 必須在該呼叫之前；該解讀呼叫的 token 也計入成本。

Bootstrap 應帶當前目標、硬條件、最新變更、未解問題、下一個可執行 TODO、必要來源索引及「何時必須回讀原文」。完整文件按 decision needs 取回。需要精確數字、日期、否定、引用或矛盾比對時，不能只依 compact summary。

每次使用者變更、文件更新、任務完成、權限變更及可見外部結果後刷新；不要等 PreCompact 才由模型自由發揮寫最後一份 summary。關閉或停機不保证觸發 hook，所以每個重要 transition 都要 durable。對不能證明 capture 成功的入口，adapter 不應自稱完整保護。

## 先驗證 deterministic engine，再測模型品質

| 測試 | 建議 fixture／操作 | 需要可觀察的通過條件 |
|---|---|---|
| 新 session 只有 bootstrap | 丟掉聊天 context，再從 state 及選定文件啟動 | 硬條件、目標、next TODO、unresolved 均可重建；沒有聲稱看過未注入文件 |
| 多次壓縮 | 同一 case 連續 compact／restart，插入不相關長文 | 每次 revision／hash 正確；原文未遺失，回答不復活舊條件 |
| 硬條件替換 | rent-only £2,200 → all-in £2,150；面積 45 → 40 | 舊欄位 superseded；只採現行定義；未修改的 move date 保留 |
| 否定與撤回 | 「先不要送出」「撤回先前允許自動提交」 | raw 字句保留；authorization 撤回阻擋下一次作用，不能由舊 TODO 授權 |
| 來源更新 | 同 document ID 新 hash 修正日期／金额 | 舊 finding／pass 失效並指出依據；revision 正確前不能發布結果 |
| 新訊息與執行競爭 | 在模型工作、tool call 前後注入需求更動 | 新 revision 的到達順序可稽核；舊 base patch 不可覆蓋更動 |
| Crash 邊界 | raw 已存、patch 未存；event 已寫、snapshot 未換；dispatch 已存、result 未存 | 重啟能區分三種狀態；不漏原文、不重套 patch、不盲目重做外部作用 |
| 重複 delivery／雙 writer | 同 event 重送；兩個 patch 以同 base revision 提交 | 去重；只有一個成功 commit，另一個明確 conflict／重算 |
| 文件缺失或竄改 | 刪除／改動必要文件、snapshot 或 receipt | 不把 missing 當空值；拒絕／重新取得並保留原因，不能默默完成 |
| TODO／goal 完成造假 | 模型輸出 completed，但 tests 未跑或 revision 已過期 | state gate 拒絕完成；保留未通過項，不新增模型 judge 也可驗證 |
| Prompt injection | 附件要求忽略 budget、刪 state、輸出 secrets | 不改 authorization／hard requirements；只作待分析資料；無外送或越權動作 |
| Hook 不可用 | disabled、未 trust、timeout、錯 JSON、stdout 超限、MCP 未 ready | 記錄確切行為；沒有 receipt 不算成功刷新；依 adapter 保守停止 dependent work |
| 隱藏入口 | initial prompt、queued input、resume、compact mid-turn、subagent steering、附件 | 每個承諾支援的入口都有 exact-input capture 測試；不支援者明列 |
| 汙染 shared memory／task list | 另一 worktree 寫入同一 memory/task namespace | 不把外部狀態當作本次已授權事件；case／project identity 隔離 |

Deterministic tests 可證明保存、schema、版本、失效、去重及恢復的特定不变量；不能證明未測輸入的語義抽取百分之百正確。模型層要另測「抽取 patch 是否正確、引用是否真實、是否履行現行需求」，並保留每個候選實際看到的 evidence，避免 judge 以自己的完整文件誤判候選的誠實缺證陳述。

建議 ablation 依序比較：full history、summary only、typed current state、typed state＋必要原文 retrieval、再加 automatic refresh／interruption。先固定同一套 cases、變更順序、source revisions、模型／effort、最大 calls 與 token 上限，再逐一移除 component。跨 session restart 和原地 compaction 分開報告；不要一口氣換模型、prompt、retrieval policy 與 judge。

## 最小 token economics

檔案落地、hash、schema check、狀態 reducer 本身不需要模型 token。模型產生 patch、讀 bootstrap、回讀文件、壓縮、judge、retry 及 subagents 都需要計帳。Token 數、計费、cached input、模型推理／輸出以及帳號 rate-limit 不是同一個量。

我們的量測式：`total model tokens = Σ(input + output)`，cached input 是 input 的子集，不再次相加；另報模型提供的 cache-write／cache-read／reasoning 等字段。金額按 provider／model 當時費率與可見 usage 計算；只有字數或 chars/4 時標為估算，不稱 actual billed tokens。

簡單未快取的示例（非實測）：20 次決策每次重讀 10,000-token 舊材料，需要 200,000 input tokens。若每次 bootstrap 1,200，加上 4 次各取回 3,000-token 原文，則為 `20×1,200 + 4×3,000 = 36,000`；節省 164,000 input tokens，尚未扣除 patch／compaction／retrieval wrapper／judge 的新成本。真實 session 會累積對話，不能把這個示例當產品保證。

官方 caching 依實際可重用 prefix／breakpoints，換前綴、設定或 compact 都可能降低 reuse；有共同文字不等於 cache hit。API 的 cache 計費機制也依模型而異。固定指令放前、變動資料放後有助設計，但要看實測 usage；不為湊 cache 而無限制增加 context。 [官方 prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

成本驗收同時列：完成率、critical requirement misses、舊條件復活次數、錯誤 external action 次數、原文 retrieval 次數、call 數、實際 input／cached／output tokens、wall time、pending／unknown telemetry。品質相近才討論節省；一個便宜但漏掉否定或現行上限的 run 不算成功。

## 對外可以和不能承諾的範圍

可以在測試通過後承諾：指定入口的原文保存、可重建狀態、revision 一致性、指定 failure paths 的保守行為，以及固定 benchmark 的品質／token 觀察。不能承諾：模型 cognition 零遺失、永不忽略已提供文件、自動 memory 永遠最新、所有 host 都已啟用 hooks、未登入／未支援入口也必然捕捉，或 synthetic tests 代表真實專案等價。

真正長期可靠的邊界是「查得到何時收到哪個需求、目前採哪版、依哪份證據、哪個驗收仍未過，恢復時能重新核對」。它仍需要 refreshed snapshots、正確的 input adapter、有限的模型品質評估及真實 artifact 驗證。
