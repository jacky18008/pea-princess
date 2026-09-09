# Persona 對話實驗室：交付、實測與上線評估

2026-09-09。本輪交付本機 alpha：16 個既有 persona、Codex 回答、動態多輪、途中插話、暫停、私人持久紀錄及逐筆用量。已跑一次真實 P4 對話；它證明接口與連續互動可運作，沒有證明所有 persona 品質通過。

操作入口：`python3 tools/persona_playground.py --port 8765`，瀏覽 `http://127.0.0.1:8765/`。[操作與邊界](persona-playground.md)。網頁由本機程式呼叫已登入的 Codex CLI；這個桌面編碼對話本身不會被拿來當每一則 persona 回答的上下文。

## 這輪實際交付

- 原始卡片開場，後續由模型依照原 Controller 的 documents、friction、mood、progress 和 patience 動態生成。不是預先寫好的問題播放清單。
- 回答者和 persona 保存分開的歷史。測試者插話獨立標示；目前呼叫先完成並記帳，插話接著優先回答。能改情境條件並保存原話、版本和 scope；沒有宣稱理解任意自然語言變更的語義都正確。
- 單 worker、共同 ceiling、不自動 retry；重整、開啟保存紀錄和匯出都不花模型 token。未知用量、來源漂移、待恢復呼叫和超限會停止。
- Loopback、精確 Host、API Origin／Fetch Metadata／custom header、靜態路徑 allowlist、CSP、plaintext rendering、0600／0700 私人檔案與單一 server ownership。
- 原始 shell／fetch 卡片在這裡轉成 chat：不做真實查詢、寫 profile 或外部聯絡。它是互動驗收工具，尚未把完整租屋產品 pipeline 變成線上服務。

## 有界真實測試

事前在 [smoke plan](persona-playground-smoke-plan.json) 固定 P4、seed 1、gpt-6-astra、low、最多 8 calls／160,000 processed tokens。只做一次，不呼叫 Claude，不附帶模型 judge。來源 commit 是 `04373de957a6e869453c4fb0b4cd69a2209463b7`。使用與 UI 相同的本機 HTTP API，第一則回答進行時送入問題：分開 £4,600 租金與 £500 bills，列兩個下一步，保持條件不變。

| 結果 | 實測 |
|---|---:|
| Persona 回合 | 3，包含固定開場 |
| 回答者呼叫 | 4 |
| Persona 模型呼叫 | 2 |
| 插話及回答 | 1 組，順序正確 |
| Input tokens | 142,059 |
| Output tokens | 1,920 |
| Processed tokens | **143,979** |
| Cached input，已含在 input | 69,120 |
| 回答者／persona processed tokens | 108,635／35,344 |
| 各呼叫時間總和 | 約 97.8 秒；單次約 10.2–22.4 秒 |
| 重試／Claude／自動 judge／工具事件 | 各 0 |
| 結束時待處理呼叫／插話 | 各 0 |
| Stop reason | `abandoned`：達 P4 的 3 回合耐心上限 |

每一筆原始 JSONL terminal usage 都與 physical checkpoint 和 UI receipt 交叉核對：每個 call 恰好一次 terminal event、一次 attempt，input + output 相符。完整逐筆資料及 raw hashes 見 [validation JSON](persona-playground-validation.json)。完整對話與原始模型事件保存在私人 `.pea-playground/`，不加入 Git。上述數量不包含這個編碼任務和協作 review 的模型用量。

## 最終品質與發現的問題

以下是 Codex 協作 Agent 對這份 synthetic transcript 的來源複核，不是人工真值、盲評或法律時效認證，也沒有額外購買 CLI judge。

1. **有解決問題並承接插話。** 首句立即區分可看房和不宜現場簽約；插話後正確分開 rent／bills，提供兩個動作，沒有把普通問題登錄成條件變更。後續保留 September 25、£5,500 all-in、furnished one-bedroom、working lift、20-minute campus walk。
2. **數字與未知保留良好。** £4,600 + £500 = £5,100，年租 £55,200；依提供的 synthetic agreement 與 guidance，以 rent 排除 bills 算六週押金為 £6,369.23。Landlord 身分、deposit scheme、bills coverage 仍標示未知。這是對提供材料的核對，不是對真實房源或現行法律的查證。
3. **Persona 本身出現文件記憶缺口。** 它質疑 Flat 94／Ellerby House 的來源，但該地址就在它上一輪貼出的 draft 的 Property 欄。回答者沒有捏造地址。原 adapter 只把 PASTE 標記留在 persona history，模擬者看不到自己交出的 bytes。只看對話表面，很容易把 simulator 的錯誤判成回答者幻覺。
4. **P4 並沒有在宣告的設定下執行。** 卡片是 lite／gate／none，但舊 system 沒有傳入 active settings，回答者依通用指示宣告 standard 並要三組補件。不能把它判成「收到 P4 設定卻違反」。歷史設定 A/B 也應先確認配置是否真正改變模型輸入，不能只看 metadata 的 arm 名稱。
5. **對低耐心人物仍偏長。** 首則約 303 words，最後約 314 words；替人物寫的單句約 88 words。雖然首句給了決定，但還沒證明整體閱讀負擔適合 P4。
6. **停止不是完成證明。** 3 回合耐心上限只說明 controller 停了。沒有 success 逐項驗收；listing 雖已對 persona 釋出，卻未實際貼給回答者，不能拿其中 bills 細節去指控回答者漏讀。

## 實測後修正與證據範圍

修正版每次讓 persona 收到已釋出文件的完整凍結原文；未來文件仍不提供，回答者仍需等人物實際分享。另把 budget_mode／fixed_form／ask_if_missing 三項執行設定明確傳給回答者並顯示在 UI。成功條件、failure modes、未透露的租屋條件和未分享文件不隨設定注入。

配置語義依據是 [PERSONAS 的 settings 與 baseline 規格](PERSONAS.md)。原始 [Claude 設計](personas/design-notes-claude-2026-09-06.md)把 settings 當 profile 參數；[Astra 設計](personas/design-notes-astra-2026-09-06.md)則有「透過對話抵達理想設定」的不同設想。本介面選擇明確的 configured run；discovery 應另立實驗，不混在同一個分數裡。

兩項修正有離線驗證及獨立程式 review。另修正從外站連結開啟靜態首頁時被誤擋的問題；私人 API 仍拒絕跨來源讀取與操作。**修正後沒有再花模型 token 重跑；143,979 的成本及這份 transcript 都只屬於修正前版本。** 舊紀錄可讀可匯出，測新版需建立新對話。

## 離線驗證

完整 repo 回歸 **1,872 tests、50.916 秒、PASS**。其中本機 lab 的 25 個 backend／HTTP 測試和一個執行實際 app.js 的 Node DOM 測試，合計 26 tests、4.587 秒、PASS。涵蓋中途插話、重複送出、暫停、遺失回傳恢復、重新開啟不花費、條件保留、超限、未知用量、來源變動停止、文件釋出、設定投影、跨來源及私人路徑保護。這是程式行為驗證；沒有完整瀏覽器視覺 QA，也不取代模型語義品質驗收。來源和測試 log hashes 已寫入 validation JSON。

## 為什麼仍然很花 token

這輪輸入佔 processed tokens 約 98.7%。回答者每次重送約 40,668 字元的基礎 system，加上完整歷史和當前 state；其送入 CLI 的 prompt 從 42,701 增長到 50,279 字元。Persona 的兩次 prompt 是 8,880、10,799 字元，但實際 input tokens 達 17,179、17,707，提醒我們 CLI 提供的整體模型上下文也有成本，不能只從應用 prompt 字元數估帳單。

69,120 cached input 已包含在 142,059 input 內，不能再相加。也不能直接拿 processed tokens 換算訂閱百分比或美元；這裡沒有讀到該帳號的計費換算。固定 low 減少思考設定的不確定性，但沒有自動消除上下文成本。

目前可做的操作是先用「下一步」、小 persona、明確 call ceiling，觀察有用進展再連續執行。程式優化應分開驗證：持續 thread 降低重建成本、只載入相關的固定說明、保存必需條件與來源的可驗證 packet。每個方向都要同時看完整用量與需求覆蓋，不能重新把 compact 當無損。

## 發布範圍更正與後續 TODO

使用者後續明確指定公開交付為下載 skill／tool，由自己的 agent 執行。原先代管聊天服務的 1–2 週／3–6 週估算及遠端 worker 要求不適用，詳見 [本機產品與政策說明](local-product-and-provider-policy.md)。本文件的實测結果不變；發布缺口以安装、相容性、品質、安全及版本紀錄為主。

- [ ] **品質 release gate：** 先固定小、中、長對話和中途條件變更案例，驗證修正版的設定遵守、來源記憶、必要條件覆蓋、篇幅、未完成項目；通過後才擴大模型矩陣。
- [ ] **節省成本實驗：** 同模型、同案例、同上限比較 full replay 與 native thread／定向 reference 載入；保存 cache usage、失敗成本和輸出來源檢查。Persona 和回答者分開計成本。
- [ ] **更即時互動：** 接 Codex App Server 的 turn/steer、interrupt、resume，仍由 durable ledger 管理每個 turn；目前是兩次呼叫間優先插話。
- **另案範圍，非下載版 TODO — 受邀服務：** 身分登入、每人資料隔離、受控遠端 worker、每人配額、重啟／取消語義、刪除／匯出資料、支援流程。不能把本機 Codex 的登入分享給網頁使用者。
- **另案範圍，非下載版 TODO — 公開服務：** 多 worker 可恢復 queue、濫用與成本監控、服務指標、模型／工具權限隔離；將來源讀取與具有外部副作用的工具分開。
- [ ] **公開回饋 stage 1：** 繼續只收固定選項；先完成 catalog 管理、投稿與撤回流程，optional 文字仍留作者裝置，預設 agent 不讀。

要避免把「網站有畫面」誤當成「產品已能上線」：這輪補上的是可操作的驗收面，不是多租戶服務或品質等效證明。
