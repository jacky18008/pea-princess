# Harness 與 stage 1 交付紀錄

2026-09-09。已交付可恢復的專案狀態、managed runner／hook adapters、短入口與外部操作文件，以及全選項公開回饋的本機 stage 1。

## 已完成與驗證

| 項目 | 實際結果 |
|---|---|
| 完整離線回歸 | **1,846 tests，43.553 秒，PASS** |
| 新增範圍 | 34 state、27 runner／hooks、8 lifecycle、18 community tests；包含於完整套件 |
| 多次需求變更與恢復 | 12 checkpoints、38 個不同事實，共 **401/401** 次重複核對通過 |
| 防錯情境 | **24/24**：舊 revision、漏 coverage、未知費用、來源損毀、conditional、暫停等 |
| 公開 skill 包 | 79 archive members；含 state script／操作協定；私人 state 不在包內 |
| 短 prompt pack | **7,799 characters**，必要提問規則與固定問題保留在 8,000 上限內 |
| 歷史模型 raw | **4,162 個檔案 SHA-256 未改動**，包括前輪新增的品質矩陣 |
| 私人備份 | source bundle／archive、4,220 個 operational files、私人 state 與完整測試 log；fresh clone／fsck／state restore 通過 |
| 本輪額外實驗模型呼叫 | **0**；不含這個編碼任務及其協作 Agent 的用量 |

套件第一次整合執行發現 README 新段落使 `docs/review-board.html` 產生資料過期；已透過本機 copy-deck builder 更新。Hook 的非預設 context 上限也補進恢復指令。上表是修正後完整重跑，沒有沿用先前失敗的執行數字。未新增針對外部服務的攻擊或模型呼叫。

機器可讀數字、程式來源 hashes 與完整測試 log hash 見 [delivery JSON](session-harness-delivery.json)。生命周期原始資料及方法限制见 [validation](session-harness-validation.md)。公開包是本機 build，沒有部署或發布。

## 實際專案保存了什麼

`.pea-state/` 已初始化，而不只是提供空的框架：保存本次主要求、外部細節的追加要求，以及先前不用 Claude 的原話；8 條可追溯條件；H1–H5、F1–F3、V1 與總目標。既有品質報告、分析／租屋來源複核及兩份完整合成 fixture 均有 immutable snapshot；後續驗收紀錄也保存為來源。

關鍵記錄包括：compact 遺漏 R5 最新租金、R2 估計費用的限制，以及 R3 下午看房無法驗證夜間噪音。這些是**合成實驗的缺陷**，不是當前使用者的租屋條件。沒有從 fixture 建立個人房租預算，也沒有憑空增加模型 token 配額。

恢復時執行：

```bash
python3 skills/vet-flat/scripts/session_state.py --project . verify
python3 skills/vet-flat/scripts/session_state.py --project . context --max-chars 24000
```

私人備份位於專案旁的 `pea-princess-harness-20260909T185125Z/`。`RESTORE.md` 提供步驟；`COMPLETED.json` 記錄最終交付 commit、archive hashes 與最新 state restore 結果。它位於 Git 之外，以免產生自我引用的 commit hash；私人內容不進公開 repo。先前的 `pea-princess-durable-20260909T173524Z/` 備份亦保留。

## 分層與低階模型的保證

`AGENTS.md`／`CLAUDE.md` 只有入口與路徑，細節在 [操作指南](session-harness.md)、[可攜協定](../skills/vet-flat/references/session-harness.md)、[hooks 範例](session-hook-examples.md) 與 [官方來源對照](harness-source-notes-2026-09-09.md)。這可减少每次固定載入的說明，不能強迫模型開啟連結。

Managed runner 由程式把完整當前 packet 放入 request，超限則停止；它能保證資料被送入。原生對話的檔案讀取仍受 Agent 與 host 控制。Runner 返回尚未驗收的答案；orchestrator 另送 `decision.record` 才驗證 coverage／evidence。結構核對不能證明模型理解正確、來源為真或推論充分。本次沒有改動全域設定，也沒有宣稱 native hooks 已獲信任或正在攔截這段對話。

## 品質、成本與下一步

前次實驗的 tradeoff 仍成立：Rental compact 省 5.49% 但來源複核覆蓋較低；文件 summary 省 12.42% 但覆蓋由 16/16 降到 7/16；adaptive 多 81.69%。[原始結果與分歧](runner-unification-2026-09-09/results.md) 保留原樣。

本輪測到的是資料保存和執行邊界。短 fixture 的 packet 因 provenance／status metadata，甚至比全部原始輸入更長；沒有新的 token savings 或最終模型品質等效結論。401 個 checks 是 38 個事實的重複核對；「只保留最後 4 筆」是明示的截斷 proxy，不是真實產品 compact。

下一個可選實驗已記成 paused TODO：固定模型、案例與輸出契約，比較 full history 和 packet＋按需原文，在多次預算／條件變更後的關鍵條件覆蓋、最終判斷、無依據主張與完整成本；低階與高階模型分開測，先固定呼叫數與 token ceiling。這不是本輪漏跑的已排定矩陣。Claude 繼續暫停。

Stage 1 已有本機表單、驗證、匯入、查詢、匯出、withdraw／pause。公共選項和私人文字分開；公開端未部署，catalog 為虛構 demo，沒有真实評論或帳號／反 Sybil 系統。完整邊界與操作见 [stage 1 guide](community-feedback-stage1.md)。

## 實作 commits

- `a4aac3e`：revisioned requirements、來源快照、workflow、state tests。
- `b986749`：全選項公共資料與本機私人筆記、CLI／UI tests。
- `739ccca`：runner／hooks、入口、官方對照與 lifecycle validation。
- 最後的交付紀錄 commit 由私人 `COMPLETED.json` 的 `commit` 欄位識別。
