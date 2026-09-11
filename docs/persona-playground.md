# 本機 Agent 輸出與 Persona 對話測試台

這是一個可互動的本機 alpha。你可以觀察既有 persona 與 Codex 的整段對話，也可以中途插話。產品交付是下載的 skill／tool，由使用者自己的 agent 執行；這個 UI 是本機驗收工具。最新發布範圍與訂閱政策見 `docs/local-product-and-provider-policy.md`。

## 開啟與操作

頁面上方的「檢閱過程」可查看每次呼叫的畫面回覆與選項、實際提示內容、工具輸入／輸出、快取與非快取 tokens，以及整段對話的插問。評閱筆記另外保存並綁定原始內容，檢閱、匯出和寫筆記都不呼叫模型。完整規格、review agent API 與限制見 [Pipeline Inspector](pipeline-inspector-2026-09-11.md)。

Agent 對話測試也可選擇／拖放檔案或加入本機路徑。送出時交給模型的是已保存的檔案快照；加入附件本身不呼叫模型。開頭和追問都能附檔，檢閱台會記錄來源名稱、版本與大小。[使用方式與範圍](playground-attachments-2026-09-11.md)。

新對話與「用新版重測」可分別選擇研究深度（lite／standard／deep）和模型推理 effort（low／medium／high）；真人對話預設 standard／low。合成人物預設沿用人物卡的研究深度，可在建立前調整。研究深度會作為起始工作範圍注入提示，effort 實際傳入 Codex CLI；對話中的明確追加要求仍可改變研究範圍。對話標頭、Inspector 和匯出都會顯示設定，逐次呼叫另存當時送出的設定與來源。舊紀錄缺少的值顯示「未記錄」，不以目前預設補值。[設定與紀錄格式](playground-settings-2026-09-11.md)。

在 repo 根目錄執行 `python3 tools/start_playground.py --port 8765`，開啟 `http://127.0.0.1:8765`。需要已登入的本機 Codex CLI；使用既有 ChatGPT 登入，不把憑證放入網頁。Python 標準函式庫即可，不需 npm install。

啟動器把測試程式與 `dist/pea-princess-skill.zip` 凍結成私人快照，再啟動測試台。預設啟動先逐檔比對 ZIP 與目前 Git 索引選定的來源內容；缺檔、多檔或內容不同會停止，請先執行 `python3 tools/build_dist.py` 重建。判定看實際位元組，包含已追蹤但未提交的修改，不單看 Git HEAD 或檔案時間。回答者讀取 ZIP 解開的 `skills/pea-princess/`；逐檔核對內容，保留 ZIP 與 SHA-256，不使用電腦上另外安裝的私人 skill。介面顯示公開包版本，展開可見完整雜湊。需要歷史 A/B 時，明確傳入 `--skill-archive /完整路徑/pea-princess-skill.zip` 可選既有公開包：仍驗證安全性與套件完整性，但不要求與目前來源相同，manifest 記錄此選擇。兩種方式都不會自動重建或偷偷改用開發版。

這項檢查只防止以過期的預設 ZIP 啟動，不會自動同步已執行中的快照；進行中的實驗必須維持原先固定的版本。之後 Claude 或其他工作修改主 repo，不會中斷這份快照的對話。需要測新版時重新啟動，再開新對話或使用「用新版重測」沿用已輸入的問題與附件；舊紀錄不改寫，也不會改標成新版。控制器程式仍採 Git 追蹤檔案的目前內容，另保留舊 prompt pack 供相容性識別；公開包模式的回答者不使用該 pack。新增但尚未加入 Git 的程式不會自動帶入。這是指定 skill 版本的測試，仍有本機測試台的對話／工具設定，不代表所有 agent 的原生安裝已驗收。

1. 選「Agent 對話測試」，輸入需求；或選「合成人物測試」觀察 persona。確認模型及用量上限後建立對話；建立、重整、切換紀錄不呼叫模型。
2. 按「研究並回覆」執行第一則回答。之後直接在下方送出追問或條件變更，每則真人訊息推進一次回答，不另呼叫模型扮演使用者。
3. 顯示的是 Codex 回传的原始 `message` 與選項，沒有經過房源比較模板改寫。完整 JSON 回答、輸入歷史、工具事件、用量及版本指紋保存在 `.pea-playground/<session-id>/`，供 eval 檢閱。
4. 可以測一般租屋問答、比較與中途改要求。已有房源資料直接貼入正文；目前 skill 不開房源連結。Codex 可讀取 repo 的 skill 文件、參考檔和腳本，並依 skill 規則查開放公共資料。這條路徑不執行 host 的刊登頁面擷取。
5. 執行中插話會排隊，在目前回答完成後依序處理，不是原生同一 turn 的即時 steering。「暫停」等目前呼叫完成後停止；「恢復已保存的結果」只讀既有證據，不自動 retry。未知用量仍停止。
6. 匯出檔以 PRIVATE 命名，包含對話、插話、動作和用量，不進 Git。重啟後可接續同一版本且仍有額度的對話；既有兩次上限場不被偷偷提高，測新版請建立新場。

這是模型輸出的測試，不把輸出當成已通過程式核對的推薦。此路徑的 `current_comparison` 為空。原有條件核對工具保留獨立測試，產品整合時仍須另外驗證它與 agent 回覆的一致性。

新版回答先給具體比較或可行的下一步，再漸進釐清偏好。需要澄清時，回答下方會顯示最多三題的選項；沒有預先勾選，可以只答部分問題，也能自行填寫。送出會保存完整題目與回答，接著由 Codex 回應。這是測試台的選項介面；正式 skill 使用原廠 host 實際提供的澄清工具，並非這裡已接上原生 Codex／Claude 互動工具。

舊版「真實找房研究」使用 `output_mode: checked`：模型只交候選 URL 與欄位，host 生成比較、排序和待辦。其舊紀錄及 API 相容性保留，但瀏覽器建立的新真人場明確指定 `output_mode: agent`。不要把舊模板回覆當成新版 agent 對話品質的證據；新版也不繼承舊場的核對標章。

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

舊 `checked` 路徑是一個有明確欄位的候選比較介面；新版 `agent` 路徑保留模型自己的開放式回答。不要把原生 skill 的開放式對話能力，與本機介面的程式核對範圍混為一談。完整[接入契約](../skills/vet-flat/references/live-eligibility.md)及[本輪驗收](live-eligibility-2026-09-11/results.md)分別說明支援與實測界線。

只有單一 model worker；固定資料模式的回答者與 persona 共用上限，真實研究不額外產生 persona。Token 計數是 input + output，cached input 已包含在 input；不是實際帳單或訂閱剩餘額度。一則呼叫可能超出上限。對話採完整歷史 replay，這次沒有宣称能省掉歷史 token；native thread caching／steering 是可獨立評估的下一個 adapter。

模型呼叫數與 token ceiling 在建立對話時設定，這版 UI 不能原地提高；情境條件中的租屋預算是另一回事。來源程式更新後，旧對話可以閱讀／匯出，但繼續測新版需建立新對話。極端中斷若發生在「保存待呼叫狀態」和真正 dispatch 之間，可能沒有可恢復的 physical receipt：保留待釐清狀態，不自動重買。這仍是公開服務前需要更完整處理的運維邊界。

明確容量：200 段本機 session、每段 80 個模型呼叫以內、10 則排隊訊息、8,000 字單則插話、18,000 字累積條件變更、160,000 字完整 step prompt、96,000 字狀態 packet。超限停止，不丟棄關鍵條件。原本 `session_runner` 32,000 字預設不變，較大 prompt 是這個可信 embedding caller 的明確參數。

## 到發布的距離

已有可供桌面測試的下載版 alpha。正式推薦前的缺口是乾淨環境安裝／更新／移除、各 host 真實多輪品質、來源與條件恢復、弱模型限制、版本和安全文件。

我們不代管模型工作；遠端 worker、多租戶帳號與模型轉售不是這個產品的必要条件。先前 1–2 週／3–6 週的估算基於代管聊天服務，已由使用者釐清的下載產品範圍取代。完整門檻與供應商政策見 [本機產品說明](local-product-and-provider-policy.md)。Token ceiling 主要保護使用者的訂閱額度／API 費用與時間；原生 agent 的全局用量仍由該 host 管理。

## 官方連接方式與後續

[Codex 非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode) 支援 stdin、JSONL 事件、既有登入與 resume；這版使用可審計的有界 exec replay。[進階設定](https://learn.chatgpt.com/docs/config-file/config-advanced) 說明 project-doc discovery 限制。[App Server](https://learn.chatgpt.com/docs/app-server) 提供真正的 turn/steer、turn/interrupt 與 thread/resume；導入時仍須把版本和 usage accounting 接上，不能把本版排隊插話宣稱成同一 turn 的即時 steering。

本輪已完成一次 P4 真實 smoke：3 個 persona 回合加一次插話，6 次呼叫、143,979 processed tokens。該結果屬於修正前的 `04373de`，不能拿來認證修正後品質。完整[結果與後續清單](persona-playground-results.md)、[逐筆用量](persona-playground-validation.json)、[事前固定計畫](persona-playground-smoke-plan.json)均已保存；歷史 benchmarks 保持原樣。

## 2026-09-11 輸出測試修正

這次只恢復可測實際回答的測試台，不繼續草稿保存或介面設計。此工具仍使用唯讀 Codex exec、low effort 與完整歷史 replay；模型可按需讀取完整 skill 包，但不測原生 host 的檔案寫入、同 turn steering 或其他模型。它不等於 Codex、Grok、Claude Code 的跨 host 驗收。最新操作與 smoke 證據見 [輸出測試結果](agent-output-platform-2026-09-11.md)。

## 重測已打過的對話

選取已保存的真人對話，按「用新版重測」即可沿用原問題與附件，改選模型並使用目前的程式／skill 版本。建立時不花模型用量；可逐輪或連續執行，另存新回答並展開新舊對照。中途插話會停止自動重測。完整邊界與評估限制見 [重測指南](playground-replay-2026-09-11.md)。
