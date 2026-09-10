# v3：修正證據完整性與啟動警告，只執行最後一個 slot

延續 [v2](plan-v2.md)，總上限不變：跨版本最多四次 actor、1,100,000 processed tokens。前三次已實際呼叫，合計 823,715；不重跑或覆寫。只剩 `source-gap`，Astra low、無工具、固定真實一房摘錄；單次 300 秒，呼叫間 150,000-token 停止線，沒有自動 retry。

第三次 `real-snapshot` 的模型完成且用量已知（18,512），但 c99a87f controller 把一個已知的 CLI 啟動 warning 當工具。原始失敗仍為失敗，原回答可以另行評品質；不以修後 parser 重写舊 receipt。

本次變更：

- 只將精確符合格式、feature 名稱、啟動位置的已知 warning 存入 `diagnostic_events`。未知 item/error、web、command 與實際 provider error 仍走保守阻擋，不放寬工具政策。
- 來源索引不合法、hash 不符或中斷時保留明示錯誤；因未知其影響 URL，停止向更舊來源組回退。較新的完整來源保留。指定 URL 的正文遺失／hash 不符時，context 標不可用，不能回退成該 URL 的舊證據。原始 receipt 不改寫。

`source-gap` 仍使用前定的相同問題：十一月十五日入住，舊摘錄的十月月份是否足以確認，以及租金是否代表每月全部開銷。這是腳本設定的來源缺口，不是實際 outage，不加入修正用的答案 key。此最後 slot 可驗證修正版 text-only 交付，但不是重測先前失敗案例，也不驗證新版初始即時搜尋。

最終原始輸出交由獨立 Astra 和 root 分開 review；修正的完整性路徑做離線故障測試。來源程式 hash 與 commit 在私有 `dispatch-plan-v3.json` 於 dispatch 前固定。舊計畫／舊 artifact 的版本歸屬不變。
