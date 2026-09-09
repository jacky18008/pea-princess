# 執行時間修正：保留原始失敗，繼續原矩陣

2026-09-09。使用者已要求先完成原矩陣、移除 600 萬 processed tokens 停止門檻，再分析浪費。192 次原定實體呼叫上限與 Claude 暫停仍有效。另問的「是否允許額外補跑」尚未收到答案；本修正不新增呼叫。

## 改了什麼、為什麼改

原先由實作者設定每次 240 秒，前六次有四次完成，兩次高 effort 執行在截止時仍未產生有效的最終回答檔。這個上限開始妨礙原本要觀察的任務交付。因此由 Codex 記錄操作決定：**尚未開始的原定呼叫最多 1,200 秒**。這不是使用者另外指定的期限，也不冒充新的使用者授權。

模型、effort、研究深度、提示全文、技能包、情境資料、訊息順序、評分標準及原定 call ID 都不變。已 dispatch 的六個 request、收據與用量不改；失敗 ID 不得再次 dispatch。這是執行政策變更，不是 prompt treatment，也不是節省 token 的新版本。

原 `e001e06` 凍結來源保持 240 秒；操作版本 `f1a95a2` 也另存於私有 run 的 `frozen-operational-f1a95a2/`。新的 `amendments/runtime-0001.json` 綁定原計畫、token amendment、1200 秒 adapter 的 SHA 與操作理由。只有明確指定此檔才選用新 adapter，並建立獨立的 `continuation-audit/budget-0001--runtime-0001/`；舊 audit 不覆寫。每次 request 和 invocation receipt 記錄實際 deadline。

## 已發生的兩次失敗

| 呼叫 | 觀察到的結果 | 最終回答 | 直接 token 用量 |
|---|---|---|---|
| `s48-t01` | 240 秒超時，10 個完成的 shell commands；沒有新增研究產物 | 缺失 | 未知 |
| `s20-t01` | 240.081 秒後終止，40 個完成的 shell commands；留下部分研究、算式與狀態檔，最後一個報告格式檢查仍失敗 | 缺失 | 未知 |

兩次的 `native-record.json`、完整工具輸出與 `failure-artifacts.json` 都保留。部分產物不當作完整交付，也不當作全無工作。未取得 terminal usage，總用量維持 null，四筆成功呼叫的已知小計為 1,073,081 processed tokens；cached input 已含在 input，不能再加一次。

第二次 acknowledgment 前的 controller checkpoint 另存，其 SHA-256 為 `85e56e4770b435995ef0d8ebd150243cfd2db8db7e7258a8debe25ad64cf85ad`。確認程序已終止後才可明確 acknowledgment 並續跑其他獨立案例。失敗後的對話回合與配對評分暫留，不補造缺失歷史。

## 對評估的影響

240 秒與 1,200 秒是不同的執行政策，報告必須列出每格實際 deadline，保留改動時間與首次失敗。跨政策的完成率、耗時或品質不能冒稱全部是在相同執行條件下比較。即使某次 1,200 秒設定的呼叫實際在四分鐘內完成，它仍屬新設定區段。

「截止前交付成功」可觀察為 false；缺失的最終回答品質、後續對話結果及未取得的用量保持不可評或未知。不能自動把完整的另一側判為配對勝者，不能用部分研究檔取代整段對話。若之後另獲補跑授權，首次嘗試可靠度和補跑後交付須分開列，所有失敗與費用都保留。

操作關係：[原凍結方案](conversation-ablation-protocol.md)、[token 上限修正](conversation-ablation-budget-amendment.md)、[失敗後繼續獨立案例](conversation-ablation-continuation.md)。原文件中的限制是當時版本，這份文件記錄後續變更，沒有追溯改寫原實驗。

## 驗證

21 個 continuation 測試與 17 個 native adapter 測試通過；其中實際啟動本機替身程序，核對 1,200 秒 invocation、未變的 prompt／model／effort、請求與收據 hash，以及未指定 policy 時仍選擇原 240 秒 adapter。完整離線回歸 **2,016 tests，60.239 秒，PASS**。另一個子代理獨立檢查程式，未發現 blocker。

若某個尚未 dispatch 的 ID 先前已保存不同的 240 秒 request，新設定會停止而非覆寫；本次實際續跑點沒有這種衝突。所有六筆既有 native 收據與 ledger hash 相符，50 個既有紀錄檔保持原 SHA。切換前另備份並逐檔核對 4,746 個私有檔案；這是中途恢復點，不冒稱最終交付備份。
