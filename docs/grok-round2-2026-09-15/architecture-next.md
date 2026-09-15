# Grok 第二輪後的最小架構修正

2026-09-15。這是整合分支的**下一版設計清單**，不是 v3 原生測試的結果或對已凍結 ZIP 的修改。先按 [結果](results.md) 和 [v3 預登記方法](v3-method.md) 完成同一套觀察，再另開版本驗收下面的改動。`boundary.py` 現有的同戶例外、原話與 revision 檢查應保留；無須另造第二份條件帳本。

## 1. 每間房的「研究、考慮、聯絡、預約」分開記

先在目前 `.pea-state` 的候選投影旁加一個小的 action ledger。每筆只描述**該候選、該行為**，含 `candidate_id`、`action`、`status`、`request_id`、原話 `quote`、`captured_revision`、發話當時的條件／證據 pin、決定範圍與失效原因。`action` 固定為 `research`、`consider_viewing`、`contact_agent`、`book_viewing`；`status` 至少分 `requested`、`undecided`、`allowed`、`held`、`declined`、`revoked`。不要用單一遞增的「房源階段」取代這四項：人可擱置看房但繼續查 EPC，也可撤回聯絡授權而保留研究。

Trusted host 捕獲**實際送出的 user turn**後才可附上原話；`actor:user`、`authorized:true` 和字串包含檢查仍只是機器 receipt，不證明語意。無明確決定時保留 `undecided`，由 review agent 對照對話確認。對 A 說「可以考慮去看看」只允許顯示**可考慮**，對 B 說「還沒決定要不要看，先繼續查」使 `research:requested` 且 `consider_viewing:undecided`；兩句都不得推出 agent 可聯絡或預約。收到「先別看，但查它的帳單」時 `consider_viewing:held`、`research:requested`；收到「不要替我聯絡或預約」時兩個外部行為為 `held` 或 `revoked`。每個決定預設只作用於當前 `candidate_id`，只有明示全體範圍的原話才更新全體；一般條件變更與同戶例外依既有 boundary journal 更新，不從 action ledger 反推放寬條件。

建議的出站 gate 是 `contact_agent` 與 `book_viewing` **各自**有目前有效的明示授權、當前候選 identity／availability 經核實、當前條件與持有狀態可用，才可能讓相應動作通過。`consider_viewing:allowed` 不能代理另外兩個 gate；`research:requested` 只授權在現有資料來源規則內查事實，也不能變成商業網站重抓許可。測試平台可強制這些 gate；第三方 Grok Bot 主機若不接 gate，包內 JSON 本身不能攔住它的外部工具，應在 host 欄標 `not_enforced`。

驗收用四組同戶/異戶重播，加一組重開接續：A 可考慮、B 繼續研究；A 明示擱置看房但查帳單；只同意 A 的 46 分鐘例外、B 未決；撤回 A 的聯絡權。逐組核 state、回覆、排序與 TODO 都保留相同範圍；A 的可考慮不會出現在 B，沒有任何 `contact/book` tool receipt，重開後仍須讀到同一個有效 user quote。以人工／獨立 reviewer 判語意，機器驗收判 scope 和出站 gate；不能拿 regex 零命中代替兩者。

## 2. 改名目前的機器旗標，保留相容期

現有 [boundary API](../../skills/vet-flat/references/boundary-api.md) 的 `viewing_allowed` 由 mandatory checks、holds、未對帳 request 算出；`action:"viewing_permitted"` 是它的 TODO 名稱。兩者只表示**已記錄的比較 gate 沒擋住考慮看房**，並非 user consent、房源可約或 agent-side contact/book 授權。v2 pilot 的 self-audit 對 A、B 都報 `viewing_allowed:true` 且 `status:"needs_evidence"`；此組合本身並不矛盾，但「permitted」對人和 agent 都容易誤讀。

下一個 schema 版本把投影主欄改為 `comparison_gate_clear_for_consideration`，TODO 改為 `consideration_gate_clear`；另由第 1 節 ledger 產生 `user_viewing_position` 與兩個 external-action gates。遷移期可留 `viewing_allowed` 舊欄給既有讀者，但必須標 `deprecated`，不得用它產生「可排看房」字句或工具 dispatch。既有 journal 原始事件不必改寫；對舊投影重算新欄、hash/revision validation，並測舊讀者不會因欄位消失崩潰。最後才移除舊 alias。

驗收例：即使所有已映射 hard checks 都通過，B `user_viewing_position:undecided` 時只能說「可以繼續研究，是否看房待你決定」；A 原話「可考慮」時可說「可考慮自己看」，不能說「可排／已排」。`status:"needs_evidence"` 或當前空置未知時不得推出可預約；已有 retained hold 時 comparison gate 仍為 false。這需要回覆語意審核與 machine projection 同時過關。

## 3. 同一 revision 的來源、研究和交付

現在窄流程 `boundary.py reconcile` 原子保存 `.pea-state/boundary-review.json` 與 `boundary-context.json`，生成的 TODO 就是**比較流程目前的工作清單**；[boundary-turn.md](../../skills/vet-flat/references/boundary-turn.md) 明說它不是完整 assessment/report workflow。不能因 `tasks`／`outputs` 空，就說這個窄流程完全沒保存；也不能因 JSON/文字檔存在，就說完整報告的來源和人決定已驗。

用一個小的 `artifact receipt` 把每個**打算在重開後引用**的研究輸出，綁到 `candidate_id`、來源 ID／URL 或本機路徑、請求參數、取得 UTC、source/cache 時點、來源與房源的地址／戶號範圍、原始檔 SHA-256、qualifier（observed/estimate/reported/unknown）、state revision 和 `evidence_sha256`。地址或街段樣本不能升格成未知同戶 EPC；不同量測層（室外 road Lden、road/rail Lnight、室內臥室）分 scope。來源失效或條件改動時讓相依 fact/output/task 標 stale，重查或重算，而不是沿用舊段落。商業廣告只收使用者供給或已授權的 snapshot；receipt 不增加抓取權。

若此次只做候選邊界比較，保存並驗 `boundary-review/context` 的 revision/hash、輸入 evidence 和 TODO 就足以證**比較工作清單** current。若使用者要求可重開的**完整文字報告**，再按 [state-sources-api.md](../../skills/vet-flat/references/state-sources-api.md) 登來源 document/fact、相關 task、報告 document 和 `output.record`，並以當前 revision 完成/驗 task；不要把 generated comparison 本身當新 evidence source。Typed user decisions 只在真的作了決定時要求；「B 未決」沒有 typed `allow`，不能為湊 gate 虛構決策。驗收須明列 scope：窄 boundary save、完整 report register、外部行為授權，三者分別 pass/fail/unverified。

重開驗收：先 `session_state.py verify/context`，後以**同一時點的** evidence 重算 `boundary.py evaluate/validate`；比對 event hash、revision、來源 scope/時點和輸出 snapshot hash。把 A 單址 EPC 換到 B 未知戶號、把近期已租的 Sketch 快取當現時空置、或把 rev-10 report 配 rev-11 條件，都應拒絕 current claim。Journals 的 hash 可察覺意外變動，不能認證惡意 writer 或官方來源為真。

## 4. 每月花費作結構化資料，再給模型寫人話

v3 已修 `calc.py`、`render.py`、viewer 和 panel：council tax 未知時完整月費為 `null`，保留已知小計，不把未知稅算 £0；有可證的免繳或房租包含才可給 0。**尚未有原生 v3 證據證明每個 host 的自然語句照做**，而 £175 帳單 scenario、district-heating tariff、standing charge 和 broadband 也可能未知。

最小後續接口是每戶 `rent`、`council_tax`、`heat_tariff`、`other_bills`、`broadband` 各有 `{value, status, source_id, quote, scope, retrieved_at}`，`status` 僅 `verified_amount`、`included_verified`、`scenario_assumption`、`unknown`。計算器可以給已知小計和**明顯標示的** bills 情境；只有所有必要項為 verified/included、單位和付款人相同，才給 `complete_monthly_total` 數字。租客可能免 council tax 的推測仍是 unknown。比較兩戶花費時各戶都有同口徑 total 才能說「總花費差 £x」；否則只比較已知租金差和未確認的費用。

回覆檢查在送出 draft 前讀同一結構化 cost receipt 和當前 state，而不僅掃字面：若 `complete_monthly_total:null`，禁止把小計/情境金額寫成「每月總花費」或「含所有帳單」；若 rent-only 上限與 total-cost 上限不同，不得改其口徑。可先在本地測試台強制，Grok Bot/Claude Code/Codex 上只在**實際有呼叫** checker/hook 時記 `enforced`。驗收用 A £2,450+B £2,100、£175 假設與 tax/heat unknown：輸出可說租金差 £350、完整月費未知，不可寫 A £2,625/B £2,275 的完整總費；明示 tax £0 有證明的反例仍可計算。

## 5. Native 送出、工具與 token 的可核證界線

v2 的 composer 看似等於凍結文字，**真正送出的** consent 多了 IME 前綴，故該 pilot 不可算 1/3；另一 Bot 在 app 切換時只先收到 ZIP。v3 [方法](v3-method.md) 已要求 post-submit exact check 和 semantic option click。把 native 操作 receipt 固定成 `{bot_id, package_zip_sha256, installed_skill_sha256, actor_file_sha256, submitted_message_sha256, option_label, clicked_choice, utc, state_revision_after, source_receipt_paths}`；在任何 cell 的附件、安裝、送出或選項不同時標 `non_comparable`，保留 raw，不重寫。先選定 Bot/app owner，再按附件→安裝 hash→doctor→租房 turn 次序；UI 異動後先重新讀 AX/畫面，不用已失效的 index。若第三方主機無 token/tool trace，寫 `unknown`，不可寫 0 或由 Bot 的 manifest 標籤推出實際 invocation。

驗收要求每個 fresh Bot 的 setup、frozen actor **送出後**、native choices 和預登記的 state/export 各有 receipt；其中任一缺失便只能作 diagnostic pilot。`reply_check.py` 離線掃六則歷史答句所抓到的過度決策，是有用的 lint 證據，卻不是 native pre-send enforcement。需要另取實際 call trace 或受控測試台 hook receipt 才能宣稱主機執行了檢查器。Doctor 20/21→21/21 只證有一次來源特定間歇且同機重試成功，不證所有來源、時地或房源都可達。

## 6. 固定 runner 來源，壓低接續成本

跨宿主 j12 的首次 Codex 調用用的是**全域舊版** skill，花 555,778 processed tokens；T2 逾時 300 秒、usage unknown，不能拿兩者評整合包品質。現有 runner source-pin 和 inventory 限制已有**離線**檢查，仍需一次物理調用前核 mounted path、ZIP/SKILL hash、AGENTS/CLAUDE 入口和 fixture；有不符就拒派發，絕不在 model call 後才發現污染。記每通 request ID、package hash、prompt chars、input/output/cached usage、timeout/partial receipt，未知 usage 不記成零。避免把同一巨型上下文重發每回合；讓模型只看路由到的檔案、目前完整 state packet 的必要欄和前回合新證據，必要時把大型 source snapshot 留在本機引用。這是 runner 改善方向，非已測 token 節省結論。

在 project 的 owner-only checkpoint 留 `{goal, current_request_ids, requirement_revision, candidate_action_positions, open_tasks, source/artifact hashes, package_identity, fixture_sent_hashes, call_usage, pending_user_choice}`；新 session 先驗 package/state/current outputs，再讀小 checkpoint 和必要來源，不重新吞所有歷史 transcript。使用者改預算、條件強度、同戶例外或取消某個要求時，仍由**新 user turn + revision-checked event**變更帳本；checkpoint 只是索引，不能覆寫意圖。驗收為網路斷線後重開，無重複派送、無過期報告/條件、未知 spend 保留 unknown；與先前同 fixture 的正常續跑相比量 context/prompt chars 與 processed tokens，品質 gate 不下降才可聲稱節省。

優先順序：先完成凍結 v3 原生 receipt，不改被測包；其後先做 action ledger／旗標改名與 cost 出站 gate，因它們可能直接誤導看房權限和價格。再做完整報告 provenance、host receipts 與 runner 節省。每一步以小版號／分支和獨立 fixture 驗收；不要把 v2 缺陷、v3 離線修補、下一版設計混成同一個 pass。
