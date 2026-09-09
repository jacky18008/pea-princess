# 原生代理 pilot：三次呼叫的成本診斷

2026-09-09。這是執行成本與工具使用紀錄的檢查，不是回答品質評分。三筆既有結果屬於凍結來源 `e001e06d01a3963b4be5f7cbf03c8bc543620fde`；後來加入的暫停功能不能回溯算成這三筆所使用的版本。

**目前實際完成 3 次原生 Codex CLI invocation，共 908,860 processed tokens，已使用原先 6,000,000 上限的 15.15%。** 每次 invocation 都只有 1 次 launcher attempt，均有完整終端用量、成功回覆與完成標記。這不是 3 次底層模型請求的證明：一次原生代理 invocation 內可以反覆呼叫工具及模型，現有終端用量是整次 invocation 的合計，沒有各次底層 provider request 的明細。沒有 Claude 呼叫。

## 三筆實際用量

`processed = input + output`。`cached input` 是 `input` 的子集，不可再加一次；`noncached input = input − cached input`。下表只整理 CLI 已回報的數字，不推估價格、帳單或 API 請求數。

| 呼叫 | 模型／effort | 版本與研究深度 | Input | Cached input（已含在 input） | Noncached input | Output | Processed |
|---|---|---|---:|---:|---:|---:|---:|
| `s02-t01` | `gpt-6-astra`／low | existing-routed／lite | 363,782 | 323,840 | 39,942 | 3,116 | 366,898 |
| `s10-t01` | `gpt-6-astra`／low | existing-routed／deep | 341,450 | 296,064 | 45,386 | 4,162 | 345,612 |
| `s28-t01` | `gpt-5.6-luna`／low | outcome-routed／lite | 193,128 | 160,000 | 33,128 | 3,222 | 196,350 |
| **合計** | **3 次 invocation** | **尚未形成完整配對比較** | **898,360** | **779,904** | **118,456** | **10,500** | **908,860** |

快取占全部 input 的 **86.81%**，占 processed 的 **85.81%**。因此「快取很多」和「processed tokens 增加很快」可以同時成立；本實驗約定的 processed-token 上限包含這些已快取輸入。不能從這些數字推論相同金額的支出，也不能直接推論帳戶的 rate-limit 計法。

三筆 wrapper prompt 均為 **1,273 字元**；最後可見回答分別為 **673、788、597 字元**。所以最後回覆長度不能代表整個原生代理回合的成本。Output counters 也不應直接解讀為最後可見回答的字數。

## 第一筆工具事件顯示了什麼

以下只檢查 `s02-t01/native-record.json` 的 `tool_events`，未讀第二、三筆工具軌跡來挑選例子，也未進行品質評分。這一筆有 **40 個工具事件：20 個 started、20 個 completed，對應 20 個 shell 指令**。以下指令序號依 completed 事件出現順序編號；started/completed 不算兩次工具執行。

工具回傳合計 **129,731 Unicode 字元／130,558 UTF-8 bytes**。這是紀錄中的 `aggregated_output` 長度，不是 tokenizer 的 token 數，也不是逐步計費明細。

| 類別 | 指令序號 | Shell 指令數 | 回傳字元 | 可觀察行為 |
|---|---|---:|---:|---|
| 技能與介面文件探索 | 1、2、5 | 3 | 83,789 | 讀技能入口、列檔案、完整讀取 report schema |
| 混合的研究資料與操作指引讀取 | 3 | 1 | 23,220 | 同一指令讀 catalog／README 與數個操作、報告、算術 references；不能全數歸為多餘成本 |
| 狀態 API 探索與失敗探測 | 4、6、7、12、13、14、16、17、18 | 9 | 17,300 | 查 help、搜尋／閱讀狀態程式實作；包含初始化前一次 context 探測，exit code 2 |
| 獨立算術計算 | 8、9、10 | 3 | 1,656 | 對候選逐一執行 deterministic calculator |
| 狀態初始化 | 11 | 1 | 340 | 建立合成工作目錄中的 durable state |
| 已有對話檢索 | 15 | 1 | 260 | 讀本地 conversation file |
| 保存狀態與研究產物，並再次計算 | 19 | 1 | 80 | 一個 Python shell 指令內套用狀態事件、保存快照／計算／比較／續接資料，並在候選迴圈內再執行 calculator |
| 狀態 context 驗證 | 20 | 1 | 3,086 | 讀取已保存的 context packet |
| **合計** | **1–20** | **20** | **129,731** | **以頂層 shell 指令分類；不捏造內部子程序的獨立 telemetry** |

最大的單一輸出是第 5 個指令完整讀取 `skill/references/report-schema.json`：**73,923 字元，占全部工具回傳字元的 56.98%**。技能／介面文件探索加上狀態 API 探索共 **12 個 shell 指令、101,089 回傳字元**。這個數字不代表全部都能安全刪除；它只指出哪裡應優先做受控改善實驗。

紀錄確實包含研究材料讀取、算術、保存和驗證工作，不是只有探索。三個獨立 calculator 指令之後，保存腳本又在候選迴圈內執行 calculator；可測試能否第一次計算就保存並沿用結果。初始化前失敗的 context 探測是 invocation 裡的一個工具命令，沒有造成另一個 launcher attempt。

## 能支持的診斷與不能支持的結論

這個回合在產出短回覆前，取得了大量 schema、操作文件及程式實作文字，並進行多次原生工具往返。大量工具結果進入後續上下文、後續請求再次帶入其中內容，是和高 input／cached-input counters 一致的機制解釋；**目前不能把 366,898 tokens 精確分攤給某一條指令，也不能用 73,923 字元直接換算成已花費 tokens**。

從三筆不完整配對樣本不能得出「某個模型、depth 或版本比較省」的可靠結論，也沒有證明節省後品質相同。這三筆仍可交給獨立評估者看結果和實際檔案；本文件不給品質分數，不把成功執行等同研究結論正確。

## 下一個受控成本實驗

1. 提供短且可執行的狀態工具 quick start，包含初始化、套用事件和 context 的正確最小例子，再量測 API 探索指令是否下降。保留完整工具能力。
2. 區分初步研究和正式完整報告所需的介面資訊。測試短報告契約與按需讀取 schema，並驗證產物仍符合真正適用的要求；不預設整份 schema 都不需要。
3. 讓算術第一次執行就保存可檢查的結果，後續寫報告讀取同一份結果；輸入改變才重算。
4. 以新凍結版本做一個小額 pilot，檢查完整 terminal usage 與品質，再決定是否展開較大矩陣。原三筆保留原版本標籤，不能與修改後結果混成同一 treatment。

這些是待測假設，沒有實測節省數字。完成這份三筆診斷後，使用者明確要求先跑完整個原定矩陣、放寬 6,000,000 processed tokens 門檻，完成後才研究浪費。原計畫與三筆收據保留；另存預算 amendment，不把工具文件改善混進同一輪。192 次受控 invocation 的原定範圍不變，也沒有新增 Claude 授權。

## 暫停與可追溯性

原先 `e001e06` 記憶體中的迴圈沒有新的 pause-file 分支；它在當前 invocation 完成後由來源雜湊檢查停止，因此留下三筆成功原始紀錄。後續 runner 的 `PAUSE_REQUESTED.json` guard 會在下一次 request 組裝、settlement 或 callback 前回傳 `operator_paused`，answers loop 收到後退出。它是 **invocation 之間的停止機制**，不會追回當前 invocation 已產生的用量。

新增三個離線回歸測試，涵蓋首次呼叫前暫停、已有一筆付費 receipt 後暫停，以及 answers CLI 不會忙迴圈；均檢查 callback 不增加、checkpoint bytes 不變，且已有用量原樣保存。`python3 -m unittest discover -s tests -p test_conversation_ablation.py -v`：**26 tests passed**。測試使用合成資料與 fake invocation，沒有呼叫模型。

本機、已被 Git 忽略的原始依據在 `.pea-playground/conversation-ablation-20260909-v1/`：

- `plan.json`、`controller/checkpoint.json`：來源版本、三筆 receipt 與用量。
- `records/{s02-t01,s10-t01,s28-t01}/native-record.json`：原始完整 receipt；只有第一筆的工具事件用於本次詳細分類。
- 各筆 `request.json`、`finished.json`：請求 metadata 與完成標記。
- `PAUSE_REQUESTED.json`：暫停原因。未修改上述任何原始檔案。

來源 pins：runner `cb734a6a6f7134c74c4906d80c80ae174758d095e2e8aaf0f665781780bb6004`；native adapter `9e0b5b901edcd7b096d08a2f0398439872cad78adca94665e8287025f80f6f9d`。第一筆 `native-record.json` 檔案 SHA-256 為 `a464606b1d0353871a379896cd518e8a12c997b774412e4ab114a4274a5ec924`。

本文件只公開合成 pilot 的聚合數字、分類和來源識別；不複製原始使用者文字、完整工具指令中的引文、私人對話或原始回答。
