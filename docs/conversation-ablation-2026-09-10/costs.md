# 對話消融實驗：成本與用量分析（2026-09-10）

本篇分析原始 4 方案 × 2 模型 × 2 effort × 3 研究深度矩陣的成本。48 段對話各規劃前三輪，其中 4 段延伸至九輪，另有 24 個正式配對評分名額。成本以工具回傳的 token 計數為準；本篇沒有讀取品質評分、評分理由或回答正文，也不宣布品質勝者、品質等效或因果上的最佳方案。

實驗來源凍結於 `e001e06d01a3963b4be5f7cbf03c8bc543620fde`。執行期間的期限改版、失敗與來源限制見[實驗進度與版本紀錄](../conversation-ablation-progress.md)及[輸入邊界稽核](../conversation-ablation-input-boundary.md)。本篇是核對後的公開統計衍生文件；原始對話、收據正文、操作映射與逐檔私有證據仍保留於私有紀錄。條件與呼叫 ID 為合成實驗標記，並非使用者身分。

已知 processed tokens 小計為 **161,368,696**：input 159,831,793 ＋ output 1,536,903。其中 cached input 146,934,656 已經包含在 input，佔已知 input **91.9%**，不能再加一次。已知 noncached input 為 12,897,137。這些不是金額，也不能直接換算訂閱 rate limit；本輪沒有帳單／配額扣減的可用對照。

**完整用量仍未知。** s48-t01、s20-t01 在 240 秒設定下失敗，均沒有 terminal usage event，三個 counter 都必須保持 null。它們分別留下 10、40 個 completed command，並非「沒有做事所以耗用為零」。其後 4 個回答及 2 個 pair judge 未派送；原 192 個 slot 實際派送 186 個，184 成功、2 失敗。不得用缺失較多的組別較低小計宣稱省 token。

186 次 launcher attempts 對應 186 次 CLI invocation；原始串流核對出 3,239 個 command started 與 3,239 個 command completed，合計 3,470 個 completed tool events。它們不是 3,239 個獨立付費 CLI 呼叫；底層 provider request 次數未知。42,953.55 秒是各 invocation 的原始耗時加總，約 11.93 小時，不是完整專案的人時或端到端經過時間。專案協調、其他對話及後續補充評估自身的用量不在這個實驗執行帳本內，無法補算；上述總量只涵蓋原矩陣。

## 各階段

單位 M = 百萬 processed tokens。表內皆為已知小計，未知失敗另列；每筆平均只除以有 terminal usage 的呼叫。T4–9 只含四段長對話的後六輪，與 T1–3 不重疊。

| 階段 | 成功／派送 | 未知用量筆數 | 已知 M | 每筆已知平均 M | completed commands | 原始工具輸出字元 |
|---|---:|---:|---:|---:|---:|---:|
| T1 | 46/48 | 2 | 39.233 | 0.853 | 868 | 11,013,822 |
| T2 | 46/46 | 0 | 42.029 | 0.914 | 851 | 8,075,428 |
| T3 | 46/46 | 0 | 67.711 | 1.472 | 1,213 | 13,637,938 |
| T4–9 | 24/24 | 0 | 6.302 | 0.263 | 173 | 1,561,203 |
| judge | 22/22 | 0 | 6.094 | 0.277 | 134 | 5,717,475 |

T3 占全部已知小計 42.0%；它的每筆平均約為 T2 的 1.61 倍。這是同一批 46 段完成第三輪的描述；輪次同時改變了任務、歷史與執行動作，不能把增加量全歸給某一份文件。Judge 占已知小計 3.8%；它們確實有成本，這批最大的用量仍在回答階段。

## 模型、effort、研究深度與方案

以下只用共同 T1–3 前綴，避免把僅 low／standard 的四段延伸混入模型與 effort 比較。各區塊是同一份用量的不同切法，不能再相加。

| 分組 | 成功筆數 | 未知筆數 | 已知 M | 每筆已知平均 M | completed commands |
|---|---:|---:|---:|---:|---:|
| model: gpt-5.6-luna | 69 | 1 | 107.611 | 1.560 | 1,815 |
| model: gpt-6-astra | 69 | 1 | 41.362 | 0.599 | 1,117 |
| effort: high | 66 | 2 | 120.619 | 1.828 | 2,191 |
| effort: low | 72 | 0 | 28.354 | 0.394 | 741 |
| depth: deep | 45 | 1 | 48.213 | 1.071 | 1,006 |
| depth: lite | 48 | 0 | 48.301 | 1.006 | 1,021 |
| depth: standard | 45 | 1 | 52.459 | 1.166 | 905 |
| arm: existing-bulk | 36 | 0 | 36.635 | 1.018 | 773 |
| arm: existing-routed | 36 | 0 | 36.392 | 1.011 | 781 |
| arm: outcome-bulk | 36 | 0 | 43.961 | 1.221 | 760 |
| arm: outcome-routed | 30 | 2 | 31.985 | 1.066 | 618 |

| 模型 × effort（T1–3） | 成功筆數 | 未知筆數 | 已知 M | 每筆已知平均 M |
|---|---:|---:|---:|---:|
| gpt-6-astra / low | 36 | 0 | 15.725 | 0.437 |
| gpt-6-astra / high | 33 | 1 | 25.637 | 0.777 |
| gpt-5.6-luna / low | 36 | 0 | 12.628 | 0.351 |
| gpt-5.6-luna / high | 33 | 1 | 94.982 | 2.878 |

本次 high 組的用量與動作數較高，但有兩筆未知失敗，且模型、具體工作路徑與上下文來源也會影響結果。lite 的已知平均沒有隨標籤等比例縮小；「研究深度」不是硬性 token 上限。不能憑模型的名稱或規模推論完整 agent workflow 一定較省。四段延伸全部為 low／standard，只有 existing-bulk 與 outcome-routed，因此不代表完整矩陣的深度或 effort 比較。

## 高耗用尾端

162 筆成功回答的平均為 0.958M，中位數 0.504M；線性插值 P90 2.603M、P95 3.771M，最大單筆 6.246M。前 5／10／20 筆分別占已知回答小計 17.3%／29.8%／47.0%。這個排序不把兩筆未知失敗當零，也不包含 judge。

| 呼叫 | 模型／effort／深度／方案 | processed M | input 內的 cached M | commands | 原始輸出字元 |
|---|---|---:|---:|---:|---:|
| s43-t03 | gpt-5.6-luna/high/standard/outcome-bulk | 6.246 | 5.964 | 44 | 734,416 |
| s40-t03 | gpt-5.6-luna/high/lite/outcome-routed | 5.672 | 5.431 | 76 | 797,538 |
| s45-t03 | gpt-5.6-luna/high/deep/existing-bulk | 5.593 | 5.371 | 87 | 483,695 |
| s47-t03 | gpt-5.6-luna/high/deep/outcome-bulk | 4.735 | 4.414 | 59 | 493,992 |
| s42-t03 | gpt-5.6-luna/high/standard/existing-routed | 4.559 | 4.383 | 69 | 453,465 |
| s42-t02 | gpt-5.6-luna/high/standard/existing-routed | 4.349 | 4.150 | 66 | 1,236,904 |
| s40-t01 | gpt-5.6-luna/high/lite/outcome-routed | 4.274 | 4.076 | 39 | 420,980 |
| s39-t03 | gpt-5.6-luna/high/lite/outcome-bulk | 3.815 | 3.636 | 71 | 513,377 |
| s42-t01 | gpt-5.6-luna/high/standard/existing-routed | 3.800 | 3.529 | 38 | 492,473 |
| s41-t02 | gpt-5.6-luna/high/standard/existing-bulk | 3.214 | 3.034 | 42 | 254,302 |

40,005,866 是所有 completed command 的原始回傳字元，不是 token 數，也不是去重後文件大小或模型實際消費量。最高用量呼叫同時有大量命令與長輸出，但本執行帳本沒有每個 tool step 的 provider usage，不能把某條 grep、檔案或指南分攤成精確 token 成本；命令數也不保證與 token 一對一。

## 設定一致的成本對照

原 24 個正式配對是兩因素的對角線比較：existing-bulk 對 outcome-routed，或 existing-routed 對 outcome-bulk；兩個因素同時變動。只有 18 個前綴配對同時滿足兩側完整、counter 已知、deadline 全部相同且一致；另有 2 個延伸配對符合。其餘不混入可比成本差值。排除條件是任一側結果不完整、用量未知，或已觀察到的期限不一致；這不是重新評分或改配對。最初 6 次呼叫使用 240 秒，其中 2 次失敗；之後尚未開始的原名額改為 1,200 秒。相同期限制定不代表實際工作與上下文完全一致。下表將方向固定為舊方案→新方案，正值代表新方案耗用較高。

| 原 pair | 模型／effort／深度 | 區段 | 基準 → 比較 | 已知成本差 |
|---|---|---|---|---:|
| j01 | gpt-6-astra/low/lite | prefix_T1_3 | existing-bulk → outcome-routed | +11.0% |
| j03 | gpt-6-astra/low/standard | prefix_T1_3 | existing-bulk → outcome-routed | -9.5% |
| j03 | gpt-6-astra/low/standard | extension_T4_9 | existing-bulk → outcome-routed | -15.1% |
| j04 | gpt-6-astra/low/standard | prefix_T1_3 | existing-routed → outcome-bulk | +56.3% |
| j05 | gpt-6-astra/low/deep | prefix_T1_3 | existing-bulk → outcome-routed | +27.9% |
| j07 | gpt-6-astra/high/lite | prefix_T1_3 | existing-bulk → outcome-routed | +59.2% |
| j08 | gpt-6-astra/high/lite | prefix_T1_3 | existing-routed → outcome-bulk | +35.0% |
| j10 | gpt-6-astra/high/standard | prefix_T1_3 | existing-routed → outcome-bulk | +34.2% |
| j11 | gpt-6-astra/high/deep | prefix_T1_3 | existing-bulk → outcome-routed | +21.4% |
| j12 | gpt-6-astra/high/deep | prefix_T1_3 | existing-routed → outcome-bulk | +31.0% |
| j14 | gpt-5.6-luna/low/lite | prefix_T1_3 | existing-routed → outcome-bulk | +103.4% |
| j15 | gpt-5.6-luna/low/standard | prefix_T1_3 | existing-bulk → outcome-routed | +25.7% |
| j15 | gpt-5.6-luna/low/standard | extension_T4_9 | existing-bulk → outcome-routed | -34.8% |
| j16 | gpt-5.6-luna/low/standard | prefix_T1_3 | existing-routed → outcome-bulk | +62.2% |
| j17 | gpt-5.6-luna/low/deep | prefix_T1_3 | existing-bulk → outcome-routed | +24.0% |
| j19 | gpt-5.6-luna/high/lite | prefix_T1_3 | existing-bulk → outcome-routed | +150.6% |
| j20 | gpt-5.6-luna/high/lite | prefix_T1_3 | existing-routed → outcome-bulk | +36.8% |
| j21 | gpt-5.6-luna/high/standard | prefix_T1_3 | existing-bulk → outcome-routed | -8.7% |
| j22 | gpt-5.6-luna/high/standard | prefix_T1_3 | existing-routed → outcome-bulk | -17.7% |
| j24 | gpt-5.6-luna/high/deep | prefix_T1_3 | existing-routed → outcome-bulk | +28.6% |

另做事後的純成本單因素配對：固定 model、effort、depth、另一因素，並要求兩段完整且均為相同單一 deadline。每列只比較自己的符合條件子集，不能拿不同列的總量互比。短 entry 同時改了去重與程序指示，仍不能分離這兩項效果。

| 事後成本比較 | 符合／原本可配 | 合併小計差 | 每對差中位數 | 每對最小～最大 |
|---|---:|---:|---:|---:|
| 固定 bulk，existing entry → outcome entry | 12/12 | +20.0% | +18.7% | -31.6% ～ +177.7% |
| 固定 routed，existing entry → outcome entry | 6/12 | +12.4% | +42.3% | -44.0% ～ +114.5% |
| 固定 existing entry，bulk → routed | 9/12 | +1.2% | -16.3% | -66.4% ～ +62.9% |
| 固定 outcome entry，bulk → routed | 9/12 | +0.2% | +2.8% | -55.4% ～ +56.7% |

這批資料沒有顯示「entry 較短就會穩定降低整段工作用量」。例如 bulk 下 12 個設定一致配對的 outcome entry 小計反而高 20.0%；routed 下只能用 6 對，小計高 12.4%。routing 的合併差接近零，但各格方向與幅度差很大。這只是單一合成情境、每格 n=1 的描述，不是一般化效果或品質等效證明；額外主機 skill 輸入、可能的延續污染、設定改版與不同腳本反應分支仍限制解讀。腳本反應不是真人滿意度，各方案的工具也相同，沒有測試移除工具的因果效果。未標記額外輸入的個案仍未被證明完全隔離；限制子集只是事後敏感度分析，不能建立新的因果證明。

## 觀察、機制與下一輪控制

可直接觀察的是：輸入占已知 processed 小計約 99.0%、高比例 cached input、少數呼叫的高耗用尾端、數千條工具動作，以及 T3 的明顯用量增加。凍結的原生代理呼叫方式每輪重新執行 `exec`；輸入組裝器會重放對話並保留文件，T6 只縮減直接附在提示中的歷史，並要求從檔案恢復。它沒有測試真正的原生對話 resume／compaction。T5 的需求變動發生在兩次呼叫之間，也不是執行中的即時介入測試。

合理但尚未量化的機制包括：較長的上下文在工具循環中反覆被處理、API 用法探索或大段讀檔增加上下文、重新啟動後重讀已持久化內容，以及不同 effort 導致不同工作步數。現有遙測不能把 1.61 億 token 切成「某份文件造成多少」；高 cache 也不等於這些處理免費。不能把 T4–9 的低平均當成 T6 compact 成功，因為任務與樣本同時改變。

以下列出下一輪應驗證的控制；其中狀態 API 速查表已交付，其模型用量收益尚未測量：

1. 先跑小型、版本固定的跨模型 canary，設定實際 token／tool-step／回傳字元門檻；超門檻就停止擴大矩陣並保存證據。本輪用量只能當下一輪容量規劃參考，不能宣稱新門檻已經省下多少。
2. **已交付的狀態 API 速查表：**[可攜式最小 API 範例](../../skills/vet-flat/references/state-api.md)已包含於交付版本 `b5ee42619b4ac82477d2040fa52e5487717ffdc1` 並通過離線測試；它不在本次凍結的 `e001e06` 輸入中。下一輪應單獨驗證它能否減少 `--help`／原始碼探索等重複工作，不能把已完成的文件實作當成已證實的 token 節省。
3. 由確定性工具提供有行數／位元組上限的搜尋結果、必要片段與檔案指標；先取小範圍，只有具體缺口才擴讀。不要默默刪除必要條件或來源限定。
4. 對研究深度設明確的工作範圍與停止條件，effort 預設值留待品質對照決定；未知 failure usage 繼續顯示 null。若事後 budget gate 只能在 CLI 返回時才拿到 usage，就不是即時硬性 token cap；更細 gate 需要工具攔截或更細用量事件。
5. 下一版單獨比較本次 fresh invocation 與明確 owned thread ID 的真實 resume，保留完整回放／文件恢復證據、取消和用量核對。先處理 host skill discovery／讀取邊界，避免更省的路徑其實讀了額外未指定資料。
6. 評分保留必要且已綁定的原始證據；下一版可先用檔案索引與證據片段導航，再由 evaluator 按需展開。不要事後改寫本輪正式輸入來降低已發生的評分成本。

## 核對範圍與來源

本篇使用原矩陣穩定完成邊界的執行帳本 revision 374。獨立核對了 186 筆正式收據與其已保存版本、請求與執行設定、成功完成標記、原始串流的終止用量及工具事件數，並重算整體、角色與全部 56 個條件區段小計；結果與最終統計報告一致。184 筆具有一個直接終止用量事件，2 筆沒有終止用量事件。所有核對過的輸入最後再次檢查雜湊；沒有修改原始收據、正式評分或凍結程式。

成本統計沒有讀取品質評分欄位或回答正文，不包含原始工具輸出正文、主機檔案路徑、私人內容或帳戶資訊。完整私有核對紀錄供維護者追溯，本篇僅保留合成條件 ID、彙總與解讀所需的小計。輸入雜湊一致能證明所核對檔案未變，不能證明模型只讀了指定資料；來源邊界、部分盲評與額外輸入的限制仍適用，詳見[輸入邊界稽核](../conversation-ablation-input-boundary.md)。原始資料仍保持私有。
