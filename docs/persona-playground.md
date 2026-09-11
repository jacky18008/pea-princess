# 本機真實研究與 Persona 對話實驗室

這是一個可互動的本機 alpha。你可以觀察既有 persona 與 Codex 的整段對話，也可以中途插話。產品交付是下載的 skill／tool，由使用者自己的 agent 執行；這個 UI 是本機驗收工具。最新發布範圍與訂閱政策見 `docs/local-product-and-provider-policy.md`。

## 開啟與操作

在 repo 根目錄執行 `python3 tools/persona_playground.py --port 8765`，開啟 `http://127.0.0.1:8765`。需要已登入的本機 Codex CLI；使用既有 ChatGPT 登入，不把憑證放入網頁。Python 標準函式庫即可，不需 npm install。

1. 選「真實研究」，輸入自己的找房需求；或選「固定資料測試」觀察 16 個 persona。確認模型及用量上限後建立對話；建立、重整、切換紀錄都不呼叫模型。
2. 真實研究由你的訊息推進；「下一步」執行一則回答，之後等你回覆，不另呼叫模型扮演你。固定資料測試可選「連續對話」，沿用 persona controller 的文件釋出和停止條件。
3. 在輸入框插入問題。新版真實研究會立即保存原话並使舊比較失效；正在產生的舊提案結束後仍記帳，但不發布，接著處理新輸入。多則排隊文字保持順序合併處理。這不是直接改寫正在生成的同一個模型 turn。
4. 真實研究直接輸入提高／降低預算或其他條件，不需勾選；普通追問裡的條件也會保存。程式只解析支援的明確語句，模糊預算、未知需求與複雜例外保留待釐清原文。「查看目前條件與待辦」可展開檢查。合成人物測試才使用「同時改變情境條件」勾選框。
5. 「暫停」在目前呼叫結束後停止；「恢復已保存的結果」只讀取既有模型證據，不自動 retry。未知用量仍停止；不能把它當零。
6. 匯出檔以 PRIVATE 命名，包含對話、插話、動作和每個 actor 的 usage。它不是公開回饋資料，也不會加入 Git。

新版回答先給具體比較或可行的下一步，再漸進釐清偏好。需要澄清時，回答下方會顯示最多三題的選項；沒有預先勾選，可以只答部分問題，也能自行填寫。送出會保存完整題目與回答，接著由 Codex 回應。這是測試台的選項介面；正式 skill 使用原廠 host 實際提供的澄清工具，並非這裡已接上原生 Codex／Claude 互動工具。

新版真實比較的選項來自已核對的 host 回覆。送出後，訊息／插話紀錄保留完整題目及回答；條件解析只接使用者實際選擇或自填的文字。只有與目前有效回覆完全相符的題目前綴才可移除，避免把程式自己提出的問題誤當使用者新增要求。

真實研究通過本機 Codex CLI 啟用公開網頁搜尋，載入 repo 當前的 skill 和相關說明；它不使用 persona 虛構文件。回覆應提供來源、日期及適用範圍；公開刊登仍不等於已確認可入住。來源失敗時保留缺口，不切成虛構候選。新版模型只提出最多三個候選網址及本次比較重點，本機在發布正式比較前獨立擷取原頁，保存原始HTML、抽取文字、時間與hash；目前僅支援Foxtons、Grainger（含prod主機）、Get Living、Fizzy列明的公開主機。失敗或超限也保留；這不是原始模型工具結果或可租確認。完整小型快照會提供給後續研究，較大正文明示未載入。程式從完整本機快照提取有限房源欄位，與目前條件核對，再一次產生比較、排序及待辦；模型原提案留在私人收據，不能自行把超標房源改成例外。每次閱讀／匯出會重新核對來源與條件。來源或版本變動時，舊比較標為歷史且不進 current_comparison。固定資料測試仍明示合成來源並關閉搜尋；兩種結果不能混報。實際驗收與分級見 [本輪紀錄](live-evidence-2026-09-10/plan.md)及[停止後修正](live-evidence-2026-09-10/plan-v2.md)。

選項中的 gpt-6-astra 是這台電腦檢查到的設定模型；也提供 Terra／Sol。思考強度明確設為 low，沒有繼承本機的 ultra。不同帳號的模型可用性以實際呼叫為準；失敗不自動切模型。沒有任何 Claude 呼叫。

## 原 persona 哪些行為保持

第一則為目前版本卡片的開場，後續由 `persona_prompt` 與 Codex 動態產生。卡片 1.1.0 修正使用者話語中的術語及不合適的六題開場評分；舊對話保留當時卡片，不能視為同一版本重跑。重用 Controller 的文件釋出、trigger、friction、耐心、mood、learned、no-progress 與停止條件。文件由 fixture 原文展開；未釋出的文件不會提前送入回答者。UI 的 success 清單不會放入回答者或 persona prompt。

回答者保存完整展開後的歷史；persona 保存含 PASTE 標記的獨立歷史，並在每次生成時收到目前已釋出文件的凍結原文，才能記得自己交出了什麼。未來才釋出的文件保持隱藏。測試者的介入另外標記，避免冒充 persona 自己說過的話。重新開啟不會重播首輪或重買模型呼叫。每次 request、來源版本、原始 terminal usage 與結果由 durable runner 保存。

此版本採「按卡片配置執行」：只有 `budget_mode`、`fixed_form`、`ask_if_missing` 三個執行選项傳給回答者，留在私人紀錄，不出現在使用者回答與主要對話標題。Persona 模型看不到這些設定，雙方都看不到 success／failure_modes 評分答案。如果要測「模型是否自行發現最適設定」，必須另定實驗。

此介面將原本 shell／fetch 卡片也改以 chat 模式測試：沒有真實網路查詢、profile 寫檔或腳本執行。因此它測的是動態對話與補件行為，不是原 benchmark 的完整工具能力等效重跑。全部來源為既有虛構案例。人工插話或變更條件後會標示情境已改動。

Persona 的 END 也可能代表沒耐心，因此畫面寫「Persona 結束」，不當成所有需求都已完成。這版沒有隱藏 satisfaction 或模型 judge 呼叫；原始 success 清單是觀察清單，最終品質仍需獨立驗收。

## 保存與隔離

私人紀錄位於 `.pea-playground/<session-id>/`。`session.json` 保存 UI inbox、controller 和兩份歷史；該 session 的 `.pea-state/` 保存 revision、原話／條件與 physical calls。檔案使用 0600、目錄 0700，且檢查 hash、symlink 和單一 server ownership。Hash 和權限不是加密或多使用者身分驗證。

伺服器只綁定 127.0.0.1；Host、Origin、Sec-Fetch-Site、自訂 API header 與 CSP 防止普通外站網頁直接使用本機介面。沒有 CORS、任意檔案服務或 shell endpoint。每次 Codex 使用專案外的臨時工作目錄、stdin prompt、read-only、ephemeral、忽略使用者設定並關閉額外 project-doc 讀取。這不等於 OS 級完整讀取隔離；固定資料模式的工具事件會使呼叫失敗；真實研究明確允許工具事件並保留原始紀錄。政策允許的是唯讀公開研究，沒有授權聯絡／付款。這些提示和事後紀錄不是工具權限防火牆，不能撤回已發生的讀取。

真實研究目前是一個有明確欄位的候選比較介面：一般閒聊、任意租屋知識問答、複雜條件例外與超過三戶的長清單，尚不能靠這個固定呈現器完整處理。不要把原生 skill 的開放式對話能力，與本機介面的程式核對範圍混為一談。完整[接入契約](../skills/vet-flat/references/live-eligibility.md)及[本輪驗收](live-eligibility-2026-09-11/results.md)分別說明支援與實測界線。

只有單一 model worker；固定資料模式的回答者與 persona 共用上限，真實研究不額外產生 persona。Token 計數是 input + output，cached input 已包含在 input；不是實際帳單或訂閱剩餘額度。一則呼叫可能超出上限。對話採完整歷史 replay，這次沒有宣称能省掉歷史 token；native thread caching／steering 是可獨立評估的下一個 adapter。

模型呼叫數與 token ceiling 在建立對話時設定，這版 UI 不能原地提高；情境條件中的租屋預算是另一回事。來源程式更新後，旧對話可以閱讀／匯出，但繼續測新版需建立新對話。極端中斷若發生在「保存待呼叫狀態」和真正 dispatch 之間，可能沒有可恢復的 physical receipt：保留待釐清狀態，不自動重買。這仍是公開服務前需要更完整處理的運維邊界。

明確容量：200 段本機 session、每段 80 個模型呼叫以內、10 則排隊訊息、8,000 字單則插話、18,000 字累積條件變更、160,000 字完整 step prompt、96,000 字狀態 packet。超限停止，不丟棄關鍵條件。原本 `session_runner` 32,000 字預設不變，較大 prompt 是這個可信 embedding caller 的明確參數。

## 到發布的距離

已有可供桌面測試的下載版 alpha。正式推薦前的缺口是乾淨環境安裝／更新／移除、各 host 真實多輪品質、來源與條件恢復、弱模型限制、版本和安全文件。

我們不代管模型工作；遠端 worker、多租戶帳號與模型轉售不是這個產品的必要条件。先前 1–2 週／3–6 週的估算基於代管聊天服務，已由使用者釐清的下載產品範圍取代。完整門檻與供應商政策見 [本機產品說明](local-product-and-provider-policy.md)。Token ceiling 主要保護使用者的訂閱額度／API 費用與時間；原生 agent 的全局用量仍由該 host 管理。

## 官方連接方式與後續

[Codex 非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode) 支援 stdin、JSONL 事件、既有登入與 resume；這版使用可審計的有界 exec replay。[進階設定](https://learn.chatgpt.com/docs/config-file/config-advanced) 說明 project-doc discovery 限制。[App Server](https://learn.chatgpt.com/docs/app-server) 提供真正的 turn/steer、turn/interrupt 與 thread/resume；導入時仍須把版本和 usage accounting 接上，不能把本版排隊插話宣稱成同一 turn 的即時 steering。

本輪已完成一次 P4 真實 smoke：3 個 persona 回合加一次插話，6 次呼叫、143,979 processed tokens。該結果屬於修正前的 `04373de`，不能拿來認證修正後品質。完整[結果與後續清單](persona-playground-results.md)、[逐筆用量](persona-playground-validation.json)、[事前固定計畫](persona-playground-smoke-plan.json)均已保存；歷史 benchmarks 保持原樣。
