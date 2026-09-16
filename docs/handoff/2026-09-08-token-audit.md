# Claude token / weekly-limit audit — 2026-09-08

這次不是單純「DNS 壞掉把 token 吃光」。可量到的主要原因是：大量完整實驗、實際使用 Opus、長到數十萬 tokens 的控制對話，以及每個進度通知又喚醒模型。計量也有漏項，讓原本的實驗成本表看起來比真正的整套工作便宜。

本次審查只讀本機結果與相關 Claude JSONL 的 metadata，沒有呼叫任何模型。以下是交接前已存在紀錄的分析；後續 runner 修補另見交接紀錄。

## 先分清三種數字

- **本報告的 processed tokens** = `input_tokens` + `cache_creation_input_tokens` + `cache_read_input_tokens` + `output_tokens`。同一段歷史被 cache 讀取十次就計十次；不是十份新內容，也不是十倍原價。
- **結果檔的 `total_cost_usd`** 是 Claude CLI 回報的估價；不能當成信用卡帳單。Anthropic 說明 Session 的美元數字由 CLI 根據 token 與定價計算，訂閱內的用量不以該數字計費。[Claude Code costs](https://code.claude.com/docs/en/costs)
- **訂閱 weekly allowance** 不是上述 token 或美元直接相除。模型、effort、對話長度及功能都影響用量，而且 Claude 網頁、Desktop、Code 共用額度。本機紀錄無法還原其他裝置或網頁的消耗，也沒有足夠資料算出「本專案占週額度幾％」。[Usage and length limits](https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work)

使用者貼上的最後一則訊息明確是 **weekly limit，2026-09-11 05:00 Europe/London 重置**；之前凌晨的是 `ENOTFOUND`。兩者是不同障礙。若這是同一個固定週期，目前週期起點可推為 2026-09-04 05:00 BST（04:00 UTC），但本次沒有重新查詢帳戶頁驗證。[Max weekly-reset 說明](https://support.claude.com/en/articles/11049741-what-is-the-max-plan)

## 實驗本身有多大

資料來源只取 `~/.claude/projects` 內 `vetflat*` 暫存工作目錄與 `pea-princess` 專案目錄：602 個 JSONL，272,030,172 bytes。日期範圍 9 月 3 日至 8 日本機最後一則紀錄。以 `(requestId, message.id)` 全域去重；重複 content blocks 不重算，`<synthetic>` 錯誤排除。這些是與 benchmark 對應的獨立目錄，沒有把 Documents 混合主對話算進來。

| 獨立工作目錄類別 | Unique responses | Processed tokens |
|---|---:|---:|
| 房源 A/B (`vetflat-claude-*`，含其 subagents) | 6,751 | 632,081,050 |
| Pipeline (`vetflat-pipeline-*`) | 609 | 66,287,108 |
| Journey / persona chat (`vetflat-journey-*`) | 932 | 59,073,736 |
| Document benchmark (`vetflat-docs-*`) | 975 | 35,098,354 |
| Persona shell (`vetflat-persona-*`) | 339 | 13,425,112 |
| 專案 CLI / 其他 bench 暫存目錄 | 40 | 1,349,535 |
| **合計** | **9,646** | **807,314,895** |

其中 cache read **756,785,218（93.74%）**，cache creation 36,836,651，fresh input 46,599，output 13,646,427。這證明 cache 大致有工作；問題是讀取次數及上下文體積非常大。API cache hit 有較低費率，API 的 cache-read rate-limit 待遇也不能直接套到訂閱 weekly allowance。[Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

在推定的本週週期內，上述獨立目錄仍有 **7,053 responses / 625,258,449 processed tokens**，其中 cache read 占 94.29%。因此「這週突然很快用完」與密集跑矩陣的時間相符。這是因果線索，不是帳戶額度的完整歸因。

| 實際 response model（全觀測期） | Responses | Fresh input | Cache creation | Cache read | Output |
|---|---:|---:|---:|---:|---:|
| `claude-opus-5` | 7,837 | 15,674 | 27,911,261 | 636,416,027 | 11,127,008 |
| `claude-sonnet-5` | 1,480 | 2,960 | 6,082,382 | 80,265,943 | 1,552,696 |
| `claude-fable-5-1` | 329 | 27,965 | 2,843,008 | 40,103,248 | 966,723 |

模型名稱取自本機 response metadata，沒有從 README 或 CLI alias 猜測。尤其 persona 卡片的 `model: null` **不是 Sonnet**：pilot 6 場、first matrix 32 場、fixed matrix 32 場的所有成功 response 都是 `claude-opus-5`；fix2 唯一已得到回答的 P1 也是它。其餘 fix2 六場只有錯誤，不能聲稱它們成功跑過某模型。逐場來源檔與 SHA256 見 [model provenance](2026-09-08-model-provenance.json)。後續同條件確認必須 pin 這個 model ID；為了省錢改模型應另立實驗 arm。

### 最近兩輪不是 64 次簡單問答

| Dataset | 場次 | 已保存 agent 回合 | Agent processed tokens | CLI 回報估價（USD） |
|---|---:|---:|---:|---:|
| `personas-2026-09-07` | 32 | 233 | 29,895,120 | 69.5061 |
| `personas-2026-09-07-fixed` | 32 | 254 | 32,264,923 | 71.2633 |
| `personas-2026-09-07-fix2` | 7（全 provider_error） | 1 | 459,791 | 0.9305 |

表格直接加總各 dataset 的 `scorecard.json[].usage`，不是另外的獨立消耗，**不可再加到上面 session-log 合計**。前兩輪各 16 場 shell Claude、16 場 chat Claude；除了 487 則已保存 agent 回覆，還有 persona、滿意度與 judge 的 helper 呼叫。這兩輪 helper 用 Codex Terra / Sol，所以 helper 漏算會低估跨供應商總消耗，不應誤寫成額外 Claude 消耗。

## 進度通知確實有昂貴的隱藏成本

貼文對應的控制對話是 Documents 專案的 session `44703858-d269-4541-80a2-3677f100b2bd`。它包含其他工作，**整份及其 subagents 不可全歸因 pea-princess**。以下獨立列出來診斷控制方式，不與專案合計相加。

這份主對話有 1,097 unique model responses、575,127,884 processed tokens；其中 cache read 558,427,805。每次 response 的 input context（fresh + cache write + cache read）中位數 **531,375**，90 百分位 833,027，最大 **966,788**。主模型為 `claude-fable-5-1`。所以介面上只看到「繼續等」幾字，也可能重新處理五十多萬 tokens 的上下文。

- 主對話有 **335 個不同的 Monitor 通知**，282 個之後有成功模型用量。
- 用「最近一則非 tool-result 的 user event 是 Monitor」歸因其後模型呼叫，直到下一則同類 user event：得到 **623 responses / 324,478,441 processed tokens**，其中 318,642,511 是 cache read。
- 推定本週內是 **260 個通知 / 523 responses / 265,718,841 processed tokens**。
- 單是最新 fixed A/B 的進度 Monitor 就歸因 **30,761,872 processed tokens**。

這個 callback 歸因包含通知後真正做的判讀、修補、重跑安排及 commit，不能全稱浪費，也不是嚴格的反事實節省估算。但頻繁把「第幾場／繼續等」交給長對話模型處理，明顯是可避免的一大項。該 parent 的 66 個 subagent 檔另有 662,406,739 processed tokens；其中包含其他專案，僅保留為混合工作量背景，不能當成此專案的附加數字。數據檔將這兩層與獨立 benchmark 分開。

## 重試與成本紀錄有哪些洞

交接前的 `bench/launch.py` / `bench/personas.py` 顯示：

1. `personas.play()` 只把被測 agent 的 `res.usage` 加入 dialogue；persona、satisfaction、judge 的 usage 沒被保存。`sum_usage(dialogue)` 因而不是全角色成本。
2. `launch.run()` 自動重試最多 3 次，但只回傳最後一次 stdout 的 usage。先前嘗試已做的工作不在該 row；timeout 分支直接 `usage=None`。失敗不保證零消耗，缺記錄也不能填 0。
3. `--retry-failed` 從整場開頭再玩一次。前段成功回覆可能再次付出成本；first matrix 的 superseded 有 7 場，fixed 有 5 場，都是 provider_error 舊版本。
4. 已修復的歷史 bug（commit `28d38d9`）曾把 stderr 的單字 `rate` 誤判為拒絕，成功回答也重試。`persona-chain-2026-09-07.log` 可見 persona、satisfaction、judge 連續重試。此處多為 Codex helper，不能全算到 Claude 頭上；浪費的歷史成本也沒有完整 per-attempt usage 可精算。
5. fix2 log 有 7 次最終 provider_error、14 行明確 `ENOTFOUND` 重試，也就是 7 個失敗 agent 呼叫各試 3 次。P1 之前已完成一回合，其後失敗；其餘 6 場第一回合即失敗。現存分數卡只記到該成功回合的 459,791 tokens。這批 DNS failure 本身沒有證據顯示吞掉大量生成 tokens，主要損失是約 96 分鐘與無效排程；不能把整週暴增都怪 DNS。
6. CLI 的 `total_tokens` 已包含四項；nested `iterations` 和 output thinking 是細分，不可再加一次。原始 session 一個 response 往往出現數個 content blocks；本次從 36,215 usage rows 去重到 14,964 responses（此數含分開列出的混合 parent/subagents），直接逐行相加會高估。

## 之後的節流方式

1. **讓 Python 等待，不讓模型反覆說「繼續等」。** 程式把逐場進度寫 log；只在整批完成、連續失敗、需要決策時通知模型。控制對話與批次執行分離；新階段使用精簡 handoff 與必要結果，避免帶近百萬 tokens 的歷史監看整夜。
2. **斷線或 quota 先熔斷。** 固定週額度不會在 60 / 180 秒後恢復。把 provider 暫停標記持久化，在 reset 前不啟動該供應商的 agent、persona、judge；連續 DNS 失敗也先停止整批。恢复后用一場原定個案檢查，再補剩餘場次。
3. **完整記錄每次呼叫。** 保存 role、resolved model、session/request ID、attempt、四種 token、estimated USD、provider/error、已知／未知用量，含 helpers 與 timeout 的 partial metadata。品質分只看有效回覆；成本表仍要計已知失敗消耗。
4. **先 pilot，再放大。** 每批先列「場次 × 預估回合 × 角色 × 重試上限」，用 2–3 場實測估整批成本；採小批增量與整批累積上限。規則更動先 rules-only regrade，再針對剩餘缺失確認。CLI 的美元上限只是估價 guard，不能視為訂閱額度的精準預算。[Claude Code costs](https://code.claude.com/docs/en/costs)
5. **不要把所有工作都交給最大模型。** 保留同條件 A/B 的 `claude-opus-5`，下一版實驗明確另測較小模型；判讀或特定難題才升級。縮短報告及 helper context，優先結構化需要的欄位，避免每回合重貼整份長報告。這次 64 場第一則回覆中位仍約 4,000 字，少問幾題不等於少生成內容。

## 如何重現與查證

- [機器可讀彙總](2026-09-08-token-audit-data.json)：role、model、日期窗口、四種 token、去重及 callback 歸因規則。
- [逐場模型來源](2026-09-08-model-provenance.json)：來源 JSONL 相對路徑與 SHA256，可對照本機私有備份；不包含對話內容。
- 原始實驗來源：上述三組 persona scorecards/cards、`bench/results/persona-fix2-2026-09-08.log`、`bench/results/persona-chain-2026-09-07.log`、`bench/results/persona-retry-2026-09-07.log`、`bench/launch.py` 的歷史。
- Session 重算流程：只選上述專案／vetflat 工作目錄 → 篩選日期 → 取 assistant `message.usage` → 排除 synthetic → 依 request/message ID 全域去重（重複 block 每欄取最大值）→ 四項分開累計。依目錄分 role、依 response `message.model` 分 model。不要把 result JSON、scorecards、merged 副本再與同一批 session 記錄相加。
- Private archive 的持久來源清單與可重跑標準函式庫腳本存於 `<repo>-handoff-20260908T113914Z/audit-scripts/`：`isolated-claude-log-paths.txt`（602 個獨立 logs）、`all-audited-claude-log-paths.txt`（669 個讀取來源）、`reproduce_token_audit.py`。已重跑並確認核心 aggregates、逐 response metadata、Monitor 歸因與模型 provenance 和首次輸出完全一致；不需要將完整私人 Claude logs 放進 Git。本報告沒有讀 credential 檔、沒有連線恢復模型、也沒有啟用付費額外用量。
