# Persona 對話實驗室

這是一個可互動的本機 alpha。你可以觀察既有 persona 與 Codex 的整段對話，也可以中途插話。產品交付是下載的 skill／tool，由使用者自己的 agent 執行；這個 UI 是本機驗收工具。最新發布範圍與訂閱政策見 `docs/local-product-and-provider-policy.md`。

## 開啟與操作

在 repo 根目錄執行 `python3 tools/persona_playground.py --port 8765`，開啟 `http://127.0.0.1:8765`。需要已登入的本機 Codex CLI；使用既有 ChatGPT 登入，不把憑證放入網頁。Python 標準函式庫即可，不需 npm install。

1. 選擇 16 個既有 persona 之一，確認模型、呼叫數及 token 上限，再建立對話。建立、重整頁面、切換紀錄都不呼叫模型。
2. 「下一步」跑到下一則回答；「連續對話」持續執行原 controller，直到 persona 結束、耐心／進度／時間限制、用量上限或失敗。
3. 在輸入框插入問題。正在產生的那一則先結束、記帳；你的問題接著優先回答。這不是把文字直接塞入正在生成的同一個模型 turn。
4. 如果要提高／降低預算或改變條件，勾「同時改變情境條件」。原文會保存成有版本的 requirement；以追加的原話和順序保留 scope／conditional，沒有宣稱自動正確解析任意自然語言。普通問題不會偷偷改條件。
5. 「暫停」在目前呼叫結束後停止；「恢復已保存的結果」只讀取既有模型證據，不自動 retry。未知用量仍停止；不能把它當零。
6. 匯出檔以 PRIVATE 命名，包含對話、插話、動作和每個 actor 的 usage。它不是公開回饋資料，也不會加入 Git。

選項中的 gpt-6-astra 是這台電腦檢查到的設定模型；也提供 Terra／Sol。思考強度明確設為 low，沒有繼承本機的 ultra。不同帳號的模型可用性以實際呼叫為準；失敗不自動切模型。沒有任何 Claude 呼叫。

## 原 persona 哪些行為保持

第一則為原卡片開場，後續由 `persona_prompt` 與 Codex 動態產生。重用 Controller 的文件釋出、trigger、friction、耐心、mood、learned、no-progress 與停止條件。文件由 fixture 原文展開；未釋出的文件不會提前送入回答者。UI 的 success 清單不會放入回答者或 persona prompt。

回答者保存完整展開後的歷史；persona 保存含 PASTE 標記的獨立歷史，並在每次生成時收到目前已釋出文件的凍結原文，才能記得自己交出了什麼。未來才釋出的文件保持隱藏。測試者的介入另外標記，避免冒充 persona 自己說過的話。重新開啟不會重播首輪或重買模型呼叫。每次 request、來源版本、原始 terminal usage 與結果由 durable runner 保存。

此版本明確採「按卡片配置執行」：只有 `budget_mode`、`fixed_form`、`ask_if_missing` 三個執行選项會顯示在畫面並傳給回答者。Persona 模型看不到這些設定，雙方都看不到 success／failure_modes 評分答案。這遵循 `docs/PERSONAS.md` 的 baseline 設定語義；如果要測「模型是否自行發現最適設定」，必須另定 discovery 實驗。舊 runner 的設定傳遞缺口及本輪修正前後版本差異詳見結果文件。

此介面將原本 shell／fetch 卡片也改以 chat 模式測試：沒有真實網路查詢、profile 寫檔或腳本執行。因此它測的是動態對話與補件行為，不是原 benchmark 的完整工具能力等效重跑。全部來源為既有虛構案例。人工插話或變更條件後會標示情境已改動。

Persona 的 END 也可能代表沒耐心，因此畫面寫「Persona 結束」，不當成所有需求都已完成。這版沒有隱藏 satisfaction 或模型 judge 呼叫；原始 success 清單是觀察清單，最終品質仍需獨立驗收。

## 保存與隔離

私人紀錄位於 `.pea-playground/<session-id>/`。`session.json` 保存 UI inbox、controller 和兩份歷史；該 session 的 `.pea-state/` 保存 revision、原話／條件與 physical calls。檔案使用 0600、目錄 0700，且檢查 hash、symlink 和單一 server ownership。Hash 和權限不是加密或多使用者身分驗證。

伺服器只綁定 127.0.0.1；Host、Origin、Sec-Fetch-Site、自訂 API header 與 CSP 防止普通外站網頁直接使用本機介面。沒有 CORS、任意檔案服務或 shell endpoint。每次 Codex 使用專案外的臨時工作目錄、stdin prompt、read-only、ephemeral、忽略使用者設定並關閉額外 project-doc 讀取。這不等於 OS 級完整讀取隔離；意外工具事件會使呼叫失敗，但事後檢查不能撤回已發生的讀取。

只有單一 model worker，回答者與 persona 共用 session 的上限。Token 計數是 input + output，cached input 已包含在 input；不是實際帳單或訂閱剩餘額度。一則呼叫可能超出上限。對話採完整歷史 replay，這次沒有宣称能省掉歷史 token；native thread caching／steering 是可獨立評估的下一個 adapter。

模型呼叫數與 token ceiling 在建立對話時設定，這版 UI 不能原地提高；情境條件中的租屋預算是另一回事。來源程式更新後，旧對話可以閱讀／匯出，但繼續測新版需建立新對話。極端中斷若發生在「保存待呼叫狀態」和真正 dispatch 之間，可能沒有可恢復的 physical receipt：保留待釐清狀態，不自動重買。這仍是公開服務前需要更完整處理的運維邊界。

明確容量：200 段本機 session、每段 80 個模型呼叫以內、10 則排隊訊息、8,000 字單則插話、18,000 字累積條件變更、160,000 字完整 step prompt、96,000 字狀態 packet。超限停止，不丟棄關鍵條件。原本 `session_runner` 32,000 字預設不變，較大 prompt 是這個可信 embedding caller 的明確參數。

## 到發布的距離

已有可供桌面測試的下載版 alpha。正式推薦前的缺口是乾淨環境安裝／更新／移除、各 host 真實多輪品質、來源與條件恢復、弱模型限制、版本和安全文件。

我們不代管模型工作；遠端 worker、多租戶帳號與模型轉售不是這個產品的必要条件。先前 1–2 週／3–6 週的估算基於代管聊天服務，已由使用者釐清的下載產品範圍取代。完整門檻與供應商政策見 [本機產品說明](local-product-and-provider-policy.md)。Token ceiling 主要保護使用者的訂閱額度／API 費用與時間；原生 agent 的全局用量仍由該 host 管理。

## 官方連接方式與後續

[Codex 非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode) 支援 stdin、JSONL 事件、既有登入與 resume；這版使用可審計的有界 exec replay。[進階設定](https://learn.chatgpt.com/docs/config-file/config-advanced) 說明 project-doc discovery 限制。[App Server](https://learn.chatgpt.com/docs/app-server) 提供真正的 turn/steer、turn/interrupt 與 thread/resume；導入時仍須把版本和 usage accounting 接上，不能把本版排隊插話宣稱成同一 turn 的即時 steering。

本輪已完成一次 P4 真實 smoke：3 個 persona 回合加一次插話，6 次呼叫、143,979 processed tokens。該結果屬於修正前的 `04373de`，不能拿來認證修正後品質。完整[結果與後續清單](persona-playground-results.md)、[逐筆用量](persona-playground-validation.json)、[事前固定計畫](persona-playground-smoke-plan.json)均已保存；歷史 benchmarks 保持原樣。
