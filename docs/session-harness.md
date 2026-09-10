# 長期專案 harness：狀態、來源、變更與恢復

2026-09-09。這一版提供本機狀態引擎、模型呼叫 bridge、Codex／Claude hook adapter，以及公開回饋 stage 1。它保護**已登錄狀態的保存、載入與版本一致性**，不宣稱模型的摘要、理解或推理無損。

## 檔案分層

| 檔案／目錄 | 用途與載入方式 |
|---|---|
| `AGENTS.md`、`CLAUDE.md` | 短入口、路徑、必要規則；載入時機依 host 不同 |
| `skills/vet-flat/references/session-harness.md` | 可攜操作協定，開始／恢復工作時讀取 |
| [skills/vet-flat/references/state-api.md](../skills/vet-flat/references/state-api.md) | 隨公開 skill 提供的精簡 CLI／Python 操作範例；使用狀態工具時才讀，不必先找本 repo 的完整手冊或讀程式猜 API |
| `.pea-state/events.json` | 使用者原文、需求 patch、任務與事件歷史；由程式還原當前狀態，不整份重送 |
| `.pea-state/object-<sha256>.txt` | 原始 UTF-8 文件的私人快照；按指定行檢索 |
| `.pea-state/checkpoint.json` | revision、event hash、完整當前 context packet；不經 LLM 摘要 |
| `.pea-state/runs/<id>/` | frozen request、實體呼叫帳本、raw 結果與 receipt |
| `docs/session-harness-plan.md` | 本次工程計畫／TODO，不能覆蓋較新的 runtime state |

`.pea-state/` 不進 Git 或公開 skill 發布。它不是加密資料庫；有本機讀取權限的工具仍可能存取。不要直接發布整個工作目錄或自動把這些資料加入報告／seed。

**只給路徑不能確保模型會讀，低階與高階模型皆然。** 一般 Codex／Claude 對話靠入口／hooks 提醒 Agent 讀取；`tools/session_runner.py` 則由程式自己讀完整 packet，放進每次實體呼叫，不必等模型主動開檔。Runner 檢查輸入與回覆的版本，返回尚未驗收的答案；可信 orchestrator 另送 `decision.record` 時，引擎才檢查條件 coverage 與 evidence。Runner 不會自動替答案評分或完成任務；若原生 Agent 跳過後續驗收，這個檢查也不會憑空發生。這兩種整合的保證不能混用，結構檢查通過也仍可能誤解資訊。

所有有效 requirements（含 prefer、prohibit、conditional）、predicate、scope、critical facts 進 packet。詳細來源以檔案快照保存。超過設定上限直接失敗，沒有「最後幾條被裁掉」的 fallback。字元／UTF-8 bytes 是工程上限，不是計費 tokens。

## 初始化、查看與恢復

在使用者的工作專案執行；若使用已安裝 skill，替換 script 路徑。

```bash
python3 skills/vet-flat/scripts/session_state.py --project . init --project-id my-project
python3 skills/vet-flat/scripts/session_state.py --project . show
python3 skills/vet-flat/scripts/session_state.py --project . context
python3 skills/vet-flat/scripts/session_state.py --project . checkpoint
python3 skills/vet-flat/scripts/session_state.py --project . verify
```

本 repo 的實際狀態另保存了前次品質報告、兩份來源複核及完整合成實驗來源；不是使用者的租屋偏好。入口使用 `context --max-chars 64000`，以容納持續新增的需求、驗收與來源 metadata，與 `AGENTS.md` 的恢復指令一致；此上限不是模型 token 預算。若 packet 超過上限，先明確調整容量並重新讀取完整內容，不可截斷需求後繼續。

`show` 還原完整狀態；`context` 輸出當前 packet；`checkpoint` 寫下可驗證的 snapshot。`--max-chars` 明確調整上限；`--max-tokens` 是保守 UTF-8-byte 上界，不是 tokenizer。若已有 profile，逐欄匯入並附來源，不能把 example profile 或舊摘要當成使用者現在的條件。

Journal 是原子替換的、邏輯上只追加事件的 JSON 與 hash chain，使用 POSIX lock、revision check、fsync、私有權限及 symlink／hardlink 檢查。Checkpoint 是衍生資料；較新的 journal 永遠優先。Hash 能發現損毀，不能防止持有整個目錄寫入權限的人重寫一整條歷史；獨立備份／Git 交付紀錄另有價值。

## 使用者原文 → patch → 重新評估

先保存新原話，hooks 已 capture 的不必再保存一份：

```json
{"op":"request.capture","id":"u-002","text":"總預算改成每月 £2300；A 房可以是一樓，但必須確認乾燥。","source":"user-message"}
```

把單一事件放在私人 event 檔後，用最新 revision 套用：

```bash
python3 skills/vet-flat/scripts/session_state.py --project . apply --expected-revision 1 --event-file event.json
```

`1` 只適用於剛 init 的示範。每次重新讀取 revision；遇到衝突先 reconcile，不能強蓋。Conditional 的完整事件例如：

```json
{
  "op": "requirement.add", "id": "floor-a",
  "value": "一樓可接受", "strength": "conditional", "scope": "candidate:a",
  "predicate": "現場檢查與證據確認無潮濕問題", "exceptions": [],
  "provenance": {
    "actor": "user", "authorized": true,
    "source_id": "u-002", "request_id": "u-002",
    "quote": "A 房可以是一樓，但必須確認乾燥。"
  }
}
```

有 `request_id` 時，quote 必須逐字出現在已保存原文。`actor:user`／`authorized:true` 是可信 orchestrator 的來源聲明，不是登入驗證；不能把第三方 JSON 原封不動送進 apply 來取得權限。

| 使用者改變 | 記錄與處理 |
|---|---|
| 提高／降低房租或 all-in 預算 | `requirement.update` 保存數字、幣別、週期與 scope；若另有登錄 rental budget，同一 pending request 下也用 `budget.set` 同步該上限；不會增加 API tokens |
| 提高／降低執行資源 | `budget.set` 區分 `api_tokens`／`execution_spend`；原本 spend 不歸零 |
| 新增／改值／必須變偏好 | `requirement.add` 或 `requirement.update` + `changes`，保留穩定 ID 和歷史 |
| 禁止改為 conditional | 保存新的 strength、predicate、scope、exceptions；未知 predicate 不可變成無條件 PASS |
| 刪除條件 | `requirement.retire`；歷史保留、ID 不重用 |
| 「不要再問」 | 改提問政策，不自行當成取消條件 |
| 含帳單／純租金不明 | blocking question 可限定 task_ids；受影響工作先停 |
| 只對某房源放寬 | 明示 candidate scope，其他房源保留原規則 |
| 新報價／新文件 | `document.add` + `supersedes`；舊快照保留，舊來源及依賴事實／結論失效 |

scope／predicate 的語意仍由 Agent 建模；本版不是任意自然語言的通用規則求解器。全域條件和候選例外衝突時先記錄問題。清楚指令已授權對應變更，顯示「舊 → 新」後可繼續；只澄清模糊處或 Agent 新提議的變更。

處理後用 `request.resolve`，resolution 為 `applied` 或有理由的 `no_change`。未 resolve 原話會阻擋新 dispatch，不能為了繼續執行就隨便標成 resolved。已失效的 KILL／PASS 都需重評，不會自行互換。

## 原文與證據

`document.add` 使用專案內的安全相對 path、`line_ranges`、provenance 和可選的 `supersedes`。程式複製原 bytes 到私人快照，而不是只保存可變路徑。首次文件不填 supersedes；版本更新使用新 ID，舊快照仍可檢索。

```json
{"op":"document.add","id":"quote-v2","path":"documents/quote-v2.txt","line_ranges":[[3,8]],"supersedes":"quote-v1","provenance":{"actor":"source","source_id":"agent-email-v2","quote":"Updated quote"}}
```

```bash
python3 skills/vet-flat/scripts/session_state.py --project . retrieve quote-v2 --start 3 --end 8
```

用 `fact.record` 保存關鍵值、來源、精確 quote。來源 hash 證明 bytes 相同；quote check 證明句子存在；兩者都不能證明來源真實或推論正確。租金新數字、費用的「估計」限定、夜間噪音的可驗證時段，必須各自保留，不靠一段概括摘要。

文件上限是 1 MiB UTF-8；較大材料先分成有明確界線的文字文件，並保留原檔。每段 excerpt／retrieve 有範圍與長度限制，超限會失敗。這些限制不允許悄悄丟掉必要條件。

## TODO、goal、workflow

`task.add` 的 kind 可為 task／goal／workflow，包含 `depends_on`、`requirement_ids`、`budget_ids`、`acceptance`。用 `task.update` 改計畫或 paused／blocked 狀態；`task.complete` 必須有最新 revision、當前 evidence 和完成的依賴。

長期流程可拆成：收材料 → 核對數字 → 對照當前條件 → 出判決 → 回歸驗證。每次做一個有界步驟，保存輸出與證據再更新 TODO。條件變更使受影響成果需要重評，不能因新訊息或预算變動解除既有暫停。

`decision.record` receipt 需覆蓋全部有效條件，硬條件 unknown／unmet 阻止 PASS；conditional 要判 PASS 時需 predicate 的 evidence 與 resolution。`output.record` 以 `document_id` 綁定有 hash 的輸出快照，並保存 `decision_ids` 與當前版本。這是結構驗證，並不把模型自己填的 met 當真值；完成前仍須核對來源及驗收條件。

## 實體模型呼叫與成本恢復

`tools/session_runner.py` 使用原 `bench/durable_run.py`／`CallControl`。先建立明確 token budget 與 ready task；下列為執行範例，初始化不會自動呼叫模型：

```bash
python3 tools/session_runner.py --project . run --id step-001 --task review-a \
  --model YOUR_CODEX_MODEL --token-budget model-tokens --prompt-file step.txt --timeout 180
python3 tools/session_runner.py --project . recover --id step-001
```

每次只跑一個 step，模型明確指定、timeout 有界、Claude 維持暫停。讀最新 packet、保存 frozen request、登錄 dispatch 後才呼叫模型；使用者 steering 使結果 stale 時拒絕當成目前結論。`recover` 只讀原 physical evidence，不呼叫模型、不重複累計 spend，不自動完成 task。

飛行中的呼叫可能已花費 token；新要求不會撤回該費用。程序確實停止、usage 已保存後，可用有使用者授權來源的 `dispatch.discard`（reason、`process_stopped:true`、`usage_accounted:true`）結束過期 dispatch，再安排新工作。這些 flags 是 orchestrator 的事實聲明，不能信任外部輸入自填。

未知費用會保存為 unknown，阻擋後续執行；單純提高 budget 不會清掉未知帳。只有取得可靠證據後，才能使用明確的 budget reconciliation。一次模型 call 可能超出 token ceiling：目前在呼叫之間檢查，不是 provider 即時計費鎖。Caller preflight 失敗也可能留下保守的 unknown 紀錄，它不證明 provider 已收費。

此 CLI bridge 支援單一 API-token budget；不能把不支援的美元 telemetry 假装成已結算。State engine 可記其他資源供可信 adapter 使用，但没有訂閱剩餘額度自動同步，也不監控任意 shell 另開的模型。此 runner 不會自動 retry 或自行建立無限迴圈。

## 原生 hooks

`tools/session_hook.py` 支援 UserPromptSubmit（保存原文）、SessionStart（最新狀態入口）、PreCompact／PostCompact（checkpoint）。預設返回短路徑與 revision，避免 host 截斷長 context。完整 packet 由 Agent 讀檔，或由 runner 直接注入。`--inline` 只用於已核對 host 長度限制的環境。

初始化後參照 [設定範例](session-hook-examples.md) 啟用。這次不修改全域設定、不繞過 Codex project／hook trust，也不宣稱正在執行的對話已被自動接管。Host 重送 UserPromptSubmit 可能產生重複 pending requests，需明確 reconcile，不自動消除可能不同的使用者意圖。

Codex hook 必須受 host 信任；Claude SessionStart 不能阻擋 session，部分 timeout 可能繼續送出 prompt。JSON／exit code 依 host 不同。Hooks 用於捕捉與提示，runner preflight 才是程式執行界線。官方來源與版本差異見 [source notes](harness-source-notes-2026-09-09.md)。

本版沒有自主排程服務；可關閉／多次恢復同一專案，需要定時喚醒再接 host scheduler。Journal 上限 32 MiB，超限停止；沒有自動刪歷史或 journal rotation，不能稱為無限記憶。

## 驗證與品質界線

```bash
python3 -m unittest discover -s tests -p 'test_session*.py'
python3 -m unittest discover -s tests -p 'test_community*.py'
python3 -m unittest discover -s tests -p 'test_*.py'
```

[Lifecycle validation](session-harness-validation.md) 使用獨立期望狀態，檢查多次需求改動／恢復／stale 拒收。「有損摘要」比較組是明示的近期紀錄截斷 proxy，不是真實 Codex／Claude compact。本輪沒有新的模型品質 A/B，字元數也不等於省下的 tokens。

在短案例中，來源與版本 metadata 甚至讓 packet 大於原始輸入。目的首先是可恢復、可追溯和防止漏掉已登錄條件；只有新的固定模型 A/B 才能測量最終回答是否改善／成本是否下降。[前次實驗](runner-unification-2026-09-09/results.md) 的 compact 品質取捨仍成立。

公開回饋已提供選項表單及本機 validate／import／search／export；文字只留投稿者 browser localStorage／私人下載。沒有公共收件伺服器、帳號或作者 Agent ACL。[Stage 1 guide](community-feedback-stage1.md) 說明操作和限制。
