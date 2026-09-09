# 本輪 harness 與 stage 1 交付計畫

2026-09-09。使用者要求保存 compact 可能遺失的關鍵條件與文件，支援長期專案、TODO／workflow／goal、中途需求變更，採用全選項公共回饋＋本機私人文字。後續要求入口文件精簡、細節外置，並說明低階模型漏讀的限制。

## 目標與驗收

| ID | 目標 | 驗收 |
|---|---|---|
| H1 | 原文、需求、例外與來源可恢復 | 重啟還原最新值；舊值與原文可追溯 |
| H2 | 使用者中途修改條件 | 增／減預算、退休條件、conditional、candidate scope、source supersession 測試 |
| H3 | 模型輸入包含必要條件 | runner 注入完整 packet，拒絕超限／舊 revision；orchestrator 另送 decision.record 時檢查 coverage／evidence |
| H4 | 有界執行與長期進度 | goals／workflows／tasks、依賴、暫停、checkpoint、pending／stale 與費用恢復 |
| H5 | portable 文件＋host adapters | 短 AGENTS／CLAUDE、外部協定、CLI guide、hooks 範例與 host 限制 |
| F1 | public options only | 額外欄位、任意文字、未知 place_id、日期與 consent 驗證 |
| F2 | 私人文字留本機 | JS handler sentinel 測試；public 匯出／索引／錯誤不含筆記 |
| F3 | 可操作的 stage 1 | 表單、匯入／搜尋／export、dedupe、withdraw、pause；demo catalog 明示虛構 |
| V1 | 可重現與交付紀錄 | 完整測試、生命周期實驗、文件、commits 與私人備份 |

## 工作狀態

- [x] 查官方 Codex／Claude 文件，區分產品支援與本機設計。
- [x] 實作狀態引擎、physical runner bridge 與 hooks adapter。
- [x] 實作 public options／local note 的 stage 1。
- [x] 完成跨模組審查、完整回歸與 lifecycle validation。
- [x] 初始化此專案私人 state，保存既有品質報告與關鍵結論。
- [ ] 保存交付 commits／backup／驗證數字。

## 保留界線與後續實驗

不宣稱模型理解無損或新 token savings；Claude 暫停保留。原生 hook 安裝／信任及 host timeout 不由此 repo 完全控制。這版沒有部署公共收件、登入、反 Sybil 或自主排程服務。

下一步適合固定模型、案例與輸出契約，比較 full history 和 packet＋按需原文，在多次需求改動後的答案品質及完整成本；低階／高階模型分開測，先設定呼叫／token ceiling。本輪程式測試不能代替模型品質等效證明。
