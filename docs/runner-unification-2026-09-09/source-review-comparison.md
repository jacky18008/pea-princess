# 固定評分解盲後對照：24 份答案

這份文件比較已固定的獨立 AI source review 與原始 model judge；兩邊都不是人工 ground truth。解盲僅用於連結答案與比較，沒有修改原始分數、評語或生成新答案。

完整性：24 個唯一候選、10 份 primary judgments、118 組完整 criterion decisions；其中兩邊各有 1 個 N/A。逐項一致 105/118，差異 13/118。

| 實驗 / arm | 獨立 coverage | Primary coverage | 獨立 / primary critical misses | 獨立 / primary unsupported | 獨立 / primary contradictions | criterion 差異 |
|---|---:|---:|---:|---:|---:|---:|
| analysis / adaptive | 16/16 (100.0%) | 15/16 (93.8%) | 0 / 0 | 0 / 0 | 0 / 1 | 1 |
| analysis / full | 16/16 (100.0%) | 14/16 (87.5%) | 0 / 0 | 0 / 1 | 0 / 0 | 2 |
| analysis / summary | 7/16 (43.8%) | 4/16 (25.0%) | 3 / 3 | 0 / 2 | 0 / 8 | 3 |
| rental / compact | 24/35 (68.6%) | 23/35 (65.7%) | 1 / 2 | 1 / 5 | 1 / 4 | 5 |
| rental / full | 30/34 (88.2%) | 28/34 (82.4%) | 0 / 1 | 0 / 1 | 0 / 0 | 2 |

Coverage 分母是各自判為 applicable 的條件。Critical 是原始 rubric 標籤；例如省略目前租金成分可以是 critical-labelled miss，而不代表建議錯誤或捏造租金。上表的 unsupported / contradictions 保留各 evaluator 的分類，不能直接當成同一定義的 hallucination rate。

分析 full 的一個引用缺陷（`同じ` 取代來源的 `same`）被 primary 放在 unsupported；獨立 review 將其分開記錄。獨立 review 合計只有一個 exact-quote defect；primary schema 沒有獨立 quote-defect 欄位，因此不把空欄宣稱為零缺陷。

Primary 對部分 summary 答案的矛盾判斷，把自己看到的完整文件當成候選也看過。候選正確說明可見資料不足，仍可能漏掉必須找出的 finding；這兩件事應分開讀。下面逐字保留原始理由，沒有據此回改分數。

## 逐候選分數

| Candidate | 解盲 job | 獨立 | Primary | 不一致條件 |
|---|---|---:|---:|---|
| A1-candidate-1 | A1-full | 4/4 | 3/4 | A1-F4 |
| A1-candidate-2 | A1-adaptive | 4/4 | 3/4 | A1-F4 |
| A1-candidate-3 | A1-summary | 2/4 | 0/4 | A1-F3, A1-F4 |
| A2-candidate-1 | A2-adaptive | 4/4 | 4/4 | — |
| A2-candidate-2 | A2-full | 4/4 | 4/4 | — |
| A2-candidate-3 | A2-summary | 1/4 | 0/4 | A2-F4 |
| A3-candidate-1 | A3-full | 4/4 | 4/4 | — |
| A3-candidate-2 | A3-adaptive | 4/4 | 4/4 | — |
| A3-candidate-3 | A3-summary | 0/4 | 0/4 | — |
| A4-candidate-1 | A4-full | 4/4 | 3/4 | A4-F4 |
| A4-candidate-2 | A4-adaptive | 4/4 | 4/4 | — |
| A4-candidate-3 | A4-summary | 4/4 | 4/4 | — |
| R1-candidate-1 | R1-full | 5/6 | 5/6 | — |
| R1-candidate-2 | R1-compact | 3/6 | 4/6 | R1-F6 |
| R2-candidate-1 | R2-full | 3/5 | 2/5 | R2-F2 |
| R2-candidate-2 | R2-compact | 3/6 | 2/6 | R2-F2 |
| R3-candidate-1 | R3-compact | 4/6 | 5/6 | R3-F5 |
| R3-candidate-2 | R3-full | 6/6 | 6/6 | — |
| R4-candidate-1 | R4-full | 6/6 | 6/6 | — |
| R4-candidate-2 | R4-compact | 5/6 | 4/6 | R4-F5 |
| R5-candidate-1 | R5-compact | 4/5 | 3/5 | R5-F1 |
| R5-candidate-2 | R5-full | 5/5 | 4/5 | R5-F1 |
| R6-candidate-1 | R6-compact | 5/6 | 5/6 | — |
| R6-candidate-2 | R6-full | 5/6 | 5/6 | — |

## Criterion-level 差異與原始理由

### A1-full · A1-F4 (minor)

Limit findings to a convenience replay subset; neither demographic effects nor a proven causal diagnosis or production effect follows.

獨立：**met**。

> 明确指出便利樣本、一次回放、流量權重與因果歸因限制；未捏造人口特徵效果或生產結果。

獨立 review 留存的答案摘錄：

> 不能推論所有隊列或實際生產成效

Primary：**missed**。

> 雖明確寫出「便利樣本…不能推論…實際生產成效」及「失敗是否由提示或檢索改動造成仍屬假設」，但未傳達資料不能支持人口統計差異結論，故未完整涵蓋此 finding。

### A1-adaptive · A1-F4 (minor)

Limit findings to a convenience replay subset; neither demographic effects nor a proven causal diagnosis or production effect follows.

獨立：**met**。

> 以便利樣本與非隨機失敗摘錄限制外推和機制頻率；把識別碼及確認處理問題標成假說，沒有超出兩份可見文件。

獨立 review 留存的答案摘錄：

> 現有材料不能證實生產環境、其他佇列或真實流量下的效能

Primary：**missed**。

> 「convenience sample」「不能證實生產環境」及將失敗機制稱作「假說」正確限制外推與因果結論，但沒有說明不能推論人口統計效應，故未完整滿足此 finding。

### A1-summary · A1-F3 (major)

Propose reviewing/re-scoring paired assisted failures and a fresh subgroup validation or route-specific gate before broad deployment. Guarded or postponed rollout is acceptable when justified.

獨立：**met**。

> 要求分層比較與獨立、覆蓋擬推行隊列的新測試，再依門檻分階段推行；是可見證據支持的合格下一步，不要求猜出隱藏的assisted名稱。

獨立 review 留存的答案摘錄：

> 取得按支援佇列及關鍵案例類型分層的P/R成功紀錄

Primary：**missed**。

> 建議「按佇列與關鍵案例類型分層」及用新案例重測具有一般用途，但沒有針對已知 assisted 回歸提出配對失敗審查，也未提出明確的 assisted 路徑門檻或保留 P 的 gate。

### A1-summary · A1-F4 (minor)

Limit findings to a convenience replay subset; neither demographic effects nor a proven causal diagnosis or production effect follows.

獨立：**met**。

> 指出固定包與實際流量的差距、抽樣代表性未知，並沒有聲稱查閱未提供文件、人口差異或已知根因。

獨立 review 留存的答案摘錄：

> 亦未證明可外推至案例包以外

Primary：**missed**。

> 「未證明可外推至案例包以外」正確限制外推，但沒有區分人口統計效應、因果診斷與生產效果均未被證實，因此未完整傳達 finding。

### A2-summary · A2-F4 (major)

Propose correcting wording/scores and checking ordered affirmative approval plus final-quote handling in scoring or safeguards; do not claim a completed fix.

獨立：**met**。

> 提出取得原文、核對rubric與時間序並降低發布措辭；沒有宣稱證據已核實或修正已完成。

獨立 review 留存的答案摘錄：

> 確認金額來源、客戶批准的原文與其是否早於 mutation

Primary：**missed**。

> 雖提出核對批准原文、金額來源和 mutation 順序，但這些資料已在所附 A2-D02 中，且未提出依現有證據更正分數；建議降為「單次重播顯示相關項目通過」仍保留被原始軌跡推翻的誤導性通過說法。

### A4-full · A4-F4 (major)

Propose a conditional search for independent output evidence or reconstruction using recovered build/configuration and an inert canary, distinguishing replay behavior from direct historical proof. A focused request for payload-level or receiver evidence suffices; every implementation detail is not required.

獨立：**met**。

> 有來源支持的具體build/config請求，明確只用來評估可能規則、不當成歷史payload證明；此項按可執行的重建第一步給分，不強求此輪就描述完整canary實驗。

獨立 review 留存的答案摘錄：

> 索取部署 sanitizer 雜湊及有效環境覆蓋

Primary：**missed**。

> 「追蹤 BUILD-DEMO-81，索取部署 sanitizer 雜湊及有效環境覆蓋」是合理的輔助調查，但回答只建議取得程式身分與設定來評估規則可能性；未提出尋找獨立 payload／接收端輸出證據，也未提出使用無害 canary 進行受控重建，因此未完整傳達本項要求的下一次輸出層驗證。

### R1-compact · R1-F6 (minor)

Keep total affordability unresolved because only rent is supplied; if discussed, age/commute/lift remain supplied claims and balcony cannot count toward internal area.

獨立：**missed**。

> There is no assessment of the £2,100 all-in cap, unknown bills/tax, or residual affordability gap. This is an omission, not a claim that the flat passes the budget.

Primary：**met**。

> The response accurately distinguishes “internal area (not balcony),” so it does not count the balcony toward the 42 m² requirement. It does not discuss or make claims about total affordability, age, commute, or lift.

### R2-full · R2-F2 (major)

Explain the unresolved conflict between agent cosmetic/switch-setting account and later caretaker investigation/part note; paint/video/caption do not resolve it.

獨立：**met**。

> Uses the substantive caretaker record over the cosmetic/video assurance. It does not repeat every sentence of the older agent account, but identifies the actual unresolved conflict.

獨立 review 留存的答案摘錄：

> the sill seal still needs investigation and the fan part has no installation date; fresh paint and the inconclusive video do not overturn that

Primary：**missed**。

> It cites the caretaker note and says “fresh paint and the inconclusive video do not overturn that,” but does not communicate the conflict with the agent’s earlier old-leak/cosmetic and switch-setting account.

### R2-compact · R2-F2 (major)

Explain the unresolved conflict between agent cosmetic/switch-setting account and later caretaker investigation/part note; paint/video/caption do not resolve it.

獨立：**met**。

> Keeps the caretaker findings unresolved despite fresh paint/open-window video. The earlier agent explanation is not quoted in full, but the substantive source conflict is preserved.

獨立 review 留存的答案摘錄：

> the caretaker said the sill seal needed investigation and the fan awaited a part, with no date or records

Primary：**missed**。

> It correctly says the caretaker note remains open and that “Fresh paint, an open window and an undated short video do not close that gap,” but omits the conflicting agent account that the mark was cosmetic and the fan merely had a switch-setting issue.

### R3-compact · R3-F5 (major)

Give a short copy-ready agent message prioritising useful verification such as clear desk width, utility evidence and late-night noise, without claiming to send or book.

獨立：**missed**。

> The copyable unsent draft is otherwise useful, but schedules checking after-10-pm noise at a 5 pm viewing. It needs to ask for separate late-night evidence or residents’ experience instead of implying that observation is available during this slot.

獨立 review 留存的答案摘錄：

> At the viewing I’d like to check the 1.35 m desk space, whether it keeps the kitchen route clear, and noise after 10 pm.

Primary：**met**。

> The short copy-ready message groups useful checks concerning the desk space, unobstructed route, late-night noise, and possible recurring charges, without claiming it was sent or that a booking occurred.

### R4-compact · R4-F5 (major)

Specify brief return evidence (measurement/observed facts and short clips) feasible with a tape and phone in 15 minutes; no app, later return or invasive task.

獨立：**met**。

> Asks for brief measurements, short clips and plain observations with existing tools. Two short noise clips instead of one combined clip and a redundant courtyard-side sentence add minor burden, but remain feasible within the visit.

獨立 review 留存的答案摘錄：

> Send the measurement, clip

Primary：**missed**。

> The measurements, observations, and recordings are generally feasible, but “Send both clips” for the noise check conflicts with Maya’s stated capacity of one short video per check.

### R5-compact · R5-F1 (critical)

Use the active £2,150 all-in, 40 m², studio-acceptable, 120 cm desk, West Loom Laboratory/35-minute profile; respect 3 December and no age cut-off.

獨立：**met**。

> Uses the corrected budget/area/layout/destination rather than any superseded value; the 35-minute cap is stated. It does not repeat 3 December, the exact 120 cm minimum or no-age-cutoff, but does not replace or violate them.

獨立 review 留存的答案摘錄：

> active constraints are all-in cost, 40 m² minimum, studio acceptable, and West Loom Laboratory

Primary：**missed**。

> The response correctly states the active “£2,150 cap,” “40 m² minimum,” studio acceptance, West Loom destination, and 35-minute maximum, but it does not communicate the retained 3 December requirement or the absence of an age cut-off.

### R5-full · R5-F1 (critical)

Use the active £2,150 all-in, 40 m², studio-acceptable, 120 cm desk, West Loom Laboratory/35-minute profile; respect 3 December and no age cut-off.

獨立：**met**。

> Uses the active total budget, area/layout and final West Loom/35-minute basis; keeps 3 December. It refers to the desk wall but does not restate the 120 cm threshold or age flexibility, without contradicting either.

獨立 review 留存的答案摘錄：

> hard £2,150 all-in ceiling, made a studio acceptable at 40 m²

Primary：**missed**。

> The response correctly applies the “hard £2,150 all-in ceiling,” 40 m²/studio rule, desk condition, West Loom destination, 35-minute limit, and mentions “3 December availability,” but it does not communicate that there is no building-age cut-off.

## 事實／引用分類：保留兩邊原話

### A1-full

independent / exact_quote_defects：

> 同じ 240 cases. There was one run per case per system.

primary / unsupported_claims：

> 「同じ 240 cases. There was one run per case per system.」

> 標作 A1-D01 的精確引文，但來源原文是「same 240 cases」，沒有「同じ」；內容方向正確，但不是所要求的精確摘錄。

### A1-summary

primary / contradictions：

> 「且沒有佇列／子群分列結果」

> A1-D01 明確提供 standard 與 assisted 分列 ledger，包括 assisted 的 P=28/40、R=16/40。

> 「僅提供摘要與文件目錄，未提供A1-D01至A1-D03的內容」

> 題目完整提供了 A1-D01、A1-D02、A1-D03 的正文。

> 「未提供失敗型態、佇列構成、抽樣代表性」

> 來源提供 selected reviewer failure excerpts、200:40 route composition，並明示 replay pack 是 convenience sample；雖然沒有完整錯誤分類或母體代表性證明，但聲稱這些資訊一概未提供不正確。

### A2-adaptive

primary / contradictions：

> 「A2-D03僅見於目錄與摘要，未提供其內容」

> 題目實際完整提供了 A2-D03 正文，因此這項來源可用性陳述與材料直接矛盾；所幸核心判斷並未依賴此錯誤。

### A2-summary

primary / contradictions：

> 「未提供 A2-D01、A2-D02 或 A2-D03 的正文、評分依據、對話原文或工具事件值」

> 題目完整提供三份文件正文，包括 rubric、seq=1–8 對話與工具值、欄位定義及 replay 說明。

> 「摘要只聲稱三項計分通過，未在所提供內容中列出其細節或原始證據」

> 除摘要外，所提供的 A2-D01 列出分數卡與擷取缺陷，A2-D02 列出完整有序事件及欄位語義。

> 「未符合前，將發布說法降為『單次重播顯示相關項目通過』」

> 原始軌跡已顯示三項行為分數不符合書面 rubric；把它改寫成相關項目通過仍與較可靠證據衝突並可能誤導。

### A3-summary

primary / unsupported_claims：

> 「未提供A3-D01至A3-D03的內容」

> 題目完整提供了A3-D01、A3-D02與A3-D03正文。

> 「沒有證據把唯一標記漏失與保存標記物件直接連結」

> A3-D01直接說C4失敗是因執行集包含active-preservation object；A3-D02給出具體物件、有效標記、無解除紀錄及選取紀錄。

primary / contradictions：

> 「摘要明說未提供該失誤的來源事件」並據此稱「無法確認該失誤是否涉及保存物件」

> 摘要只說摘要本身未重現事件；完整packet中的A3-D01和A3-D02已提供並確認事件。候選人把摘要的範圍限制錯套到整份題目。

> 「取得並核對A3-D02」

> A3-D02已隨題目提供，且候選人的limitations錯稱其內容未提供。

### R1-compact

primary / unsupported_claims：

> “the payee is an individual”

> The evidence gives the payee name as “M. Vale” and describes the account as the owner’s collection account, but does not independently establish the payee’s legal status as an individual.

primary / contradictions：

> “The payment request is for a viewing”

> The supplied email calls it a reservation payment and threatens to offer the viewing to somebody else; it does not clearly establish that the £300 itself purchases or reserves only a viewing.

### R2-full

primary / unsupported_claims：

> “check the bridge room’s refund deadline and use it”

> The room is unbooked and its availability is established only for the pasted quote today; relying on it also requires reconfirming availability.

### R2-compact

independent / unsupported_claims：

> The rent, size and commute fit, and the visit was quiet

> The all-in price is only an estimate. No invented number appears, but “fit” is not qualified and the price uncertainty is never restored.

primary / unsupported_claims：

> “The rent…fit”

> The £2,020 total is based partly on a £220 bills/council-tax estimate, so definitive affordability is not established.

> “You would also need the actual agreement and the missing payment/deposit terms before committing.”

> Those materials and this additional commitment criterion are not part of the supplied repair-focused evidence or frozen required findings.

### R3-compact

independent / contradictions：

> make that the decisive on-site check tomorrow

> The subject is quiet after 10 pm, but the only offered viewing is 5 pm and the user explicitly says daylight will not settle late-night noise. The draft repeats this timing problem.

primary / contradictions：

> “Neither flat has evidence on quiet after 10 pm; make that the decisive on-site check tomorrow.”

> The scheduled viewing is at 5 pm, and the source explicitly says a daylight visit will not settle the late-night noise concern. Quiet should remain unresolved or be investigated through another suitable source.

### R4-compact

primary / contradictions：

> “Send the measurement, clip and whether blackout mounting is permitted” versus “We still cannot settle ... blind-installation permission from this visit.”

> The message asks Maya to return permission as an answer but later categorically lists that same permission as something the visit cannot settle, without distinguishing an agent statement from definitive permission.

### R6-compact

primary / unsupported_claims：

> “Flat 1 is the only viable viewing candidate on the current evidence”

> Flat 1 is correctly the priority, but its complete no-step route is still unproven, so calling it presently “viable” is stronger than the evidence unless understood as only conditionally viable.

> “Written confirmation of the tenancy type, deposit/holding-deposit amounts, minimum term/break clause...” is one of the few confirmations needed before treating Flat 1 as the main option

> These may be sensible general due-diligence questions, but the source and frozen rubric identify access, handover, and estimated costs as the focused confirmations for this decision.

primary / contradictions：

> “Its uncapped costs also mean it has not yet been shown to fit your £2,000 all-in limit.”

> The supplied £1,990 all-in estimate does show an estimated fit, albeit with only £10 margin and no guarantee that actual costs will remain below the ceiling.

## 範圍、限制與重現

- All 24 answers were preselected before generation. This is one small synthetic run, without independent generations or statistical quality-equivalence evidence.
- Independent reviews were done directly by project AI agents. They are independent of primary scores but not a human or external-panel truth standard; visible evidence may reveal treatment.
- The primary judge sees full source documents. Analysis summary answers see only summary/catalog; marking their correct statements about missing visible evidence as contradictions confuses evaluator evidence with candidate evidence.
- Composite criteria admit interpretation differences. Both original decisions, response quotations and rationales are retained; this report does not retroactively rescore either side.
- Primary unsupported/contradiction totals and independent factual totals use different practical category interpretations. They are not interchangeable hallucination rates.
- Costs, model telemetry and output equivalence are outside this reconciliation; root separately audits the complete ledger.

執行 `python3 docs/runner-unification-2026-09-09/reconcile-reviews.py` 重建此文件及 JSON。輸入未齊或不一致時會失敗且不發布部分結果；不等待、不呼叫模型、不修改原始 review/judgments。JSON 保存全部 118 項雙方 criterion、原始理由、每 arm 統計及輸入 SHA-256。
