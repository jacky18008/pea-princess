# Runner 統一與新版品質 A/B 結果

2026-09-09。**程式統一完成；完整離線測試 1,759 項通過；新版品質矩陣 38 次呼叫全部完成。** Claude 呼叫為 0，原先暫停的七場 Claude 確認沒有恢復。這次重跑的是 10 個案例的品質回歸，先前完整 156-call ablation 保留原始結果。

## 1. 執行流程完成了什麼

八個舊入口（whole-skill、journeys、personas、documents、pipeline、A/B sweep、Codex A/B、document worker）透過共用 adapter 接入 `CallControl`。cost probe、context quality 與 ablation 三個較新入口也使用同一個持久帳本及 process lifecycle。

- 每個 runner 發出的實體 CLI/API 呼叫先保存 dispatch，完成後保存直接 usage 與原始輸出。
- 成功呼叫重播不啟動模型；failed、pending、遺失帳本、缺 usage、改過 request/source/config 都拒絕新增呼叫。
- 明確指定模型、呼叫數與 token ceiling。Claude 預設暫停。Codex JSON 與 Claude JSON envelope 旗標在 dispatch 前檢查。
- 實體呼叫串行，沒有內部自動重試。正常低分回答保留為品質結果，不因分數低而重買一次。
- Persona 的停止條件使用記錄的呼叫時間，恢復後不因 cached replay 太快而跑進另一個分支。A/B 子流程共享帳本。
- 歷史失敗／重評資料複製到新 run 的 owned output 再處理；拒絕不安全的來源包含关系、symlink 祖先和超出界線的目的地。歷史原檔保持不變。

實作 commits：`bbabe95`（context/shared lifecycle）、`a6357e3`（cost/ablation）、`1ba4a80`（durable CLI/API adapter）、`523e49a`（legacy 入口統一）。完整 CLI 與恢復規則見 [migration.md](migration.md)。

## 2. 實際模型量與重播證據

品質 run：`bench/results/durable-quality-2026-09-09/live-v2`。生成前保存的 [協定](protocol.md) 與 [plan](quality-plan.json) 固定 Terra 答題、Sol 評分，effort `low`；38 calls、900,000 processed-token threshold、每次 180 秒。第一個正常案例就是 canary，沒有另外付費探針。

| 工作 | Calls | Processed tokens |
|---|---:|---:|
| 初始回答／檢索選擇 | 24 | 401,546 |
| 實際補取資料後回答 | 4 | 67,797 |
| 主要模型裁判 | 10 | 201,482 |
| 合計 | 38 | **670,825** |

Input **639,694**＋output **31,131**＝**670,825**；cached input **144,384** 已包含在 input，不能再加一次。38 次均成功，failed/pending/unused optional 均為 0。

[獨立 raw audit](raw-quality-audit.json) 對 source/prepared hashes、每次原始 terminal event、call identities、controller coverage 與 token 合計得到 **PASS，problems=[]**。再重播整個 run，攔截任何新 process callback：**0 次新程序、266 個 raw 檔案 hashes 不變、controller report 不變**，見 [replay-audit.json](replay-audit.json)。這才是本次去重的直接驗證。

歷史 pilot 為 669,726 tokens，本輪多 1,099（約 **0.16%**）。這不證明 controller 讓單次回答更便宜；controller 的價值是可追查、失敗即停和避免重複呼叫。所有數字只涵蓋這個 CLI 矩陣，不含編碼、文件、父任務與獨立 AI 複核的用量，也不是帳单或帳號剩餘配額。

## 3. 品質 A/B：有代價，不能宣稱無損

下表同時保留原主要裁判，以及生成前選定全部 24 份答案的第二輪來源複核。後者看到每份答案實際得到的證據與共同指引，評分時不看 arm、成本或主評分；證據形式仍可能透露組別。**兩者都是 AI 評估，沒有人工 ground truth。**

| 任務／組別 | 回答＋檢索 tokens，不含裁判 | 主要裁判必要條件 | 獨立來源複核必要條件 |
|---|---:|---:|---:|
| 文件分析：full | 70,099 | 14/16 | **16/16** |
| 文件分析：summary | 61,395 | 4/16 | **7/16** |
| 文件分析：adaptive | 127,363 | 15/16 | **16/16** |
| Rental：full | 108,214 | 28/34 | **30/34** |
| Rental：compact | 102,272 | 23/35 | **24/35** |

分母不同是部分條件式判準的 applicability 不同，不能把所有比值當同一份考卷的正確率。完整逐條紀錄：[analysis review](analysis-source-review.md)、[rental review](rental-source-review.md)、[主評分與來源複核對照](source-review-comparison.md)。

**文件分析：summary 省 12.42%，但必要資訊覆蓋明顯降低。** 三個關鍵 finding 沒有被找出。獨立複核認為這些答案對資料不足是誠實的，沒有因此判作捏造事實；但誠實不知道仍可能沒完成使用者的問題。Adaptive 補取了正確材料，覆蓋與 full 相同，代價卻高 **81.69%**。這組小文件的兩輪 CLI 固定成本，沒有被少給的文件抵銷。

**Rental compact 省 5.49%，細節覆蓋較差。** 獨立複核認為兩組主要決策各 6/6 正確，但 compact 有以下缺陷：

- R5 沒寫出最新 £1,830 租金，是遺漏而非填錯數字，仍未完成關鍵判準。
- R2 把估計總費用下的租金適配直接說成符合，沒有保留估計限制。
- R3 建議在下午 5 點看房時確認晚上 10 點後的噪音，驗證方式與可觀察時段不符。

沒有找到錯誤的面積、預算／租金數字、日期、目的地或捏造房屋／醫療事實，並不代表答案完整。也不應因主要決策正確就忽略遗漏和不可行的建議。

102 個分析引用中有一處不精確引用，把來源的 `same` 寫成 `同じ`；其「同一批案例」事實本身有依據。精確引用缺陷保留，沒有把它改報成新的虛構事實。

## 4. 新舊版本能比較到什麼

分析與 rental fixtures 的內容 hashes 都與歷史 pilot 相同，requested model 與 effort 也相同。**Rental 的共同 target instructions 有變**：7,980 → 7,916 characters，包含前次安全審查加入的不可信輸入界線、法律適用範圍修正與若干文字縮短。本次 runner migration 沒有另改答題與裁判 prompt 模板，但讀入的是已修正的目前產品指引。

因此，這是「目前產品／安全執行版本下的新一轮 full/compact 等 treatment 比較」，不是把 runtime 單獨隨機分組的因果 A/B。不能把新舊答案差異全歸因於 controller；單輪、小型合成案例、模型隨機性與未獨立核定的後端修訂，也不允許宣告品質等效。

原主要裁判的弱點仍可重現：例如 summary 候選誠實說自己只拿到摘要與目錄，裁判卻因自己看到了全文而判它矛盾。第二輪來源複核把「不知道」和「說錯」分開；這不是覆寫或清除主要模型的原始分數。

兩輪評分在 118 組 criterion decisions 中有 **13 組不同**，不是所有差異都往同一方向。必要條件合計為主評分 84/117、來源複核 93/117（另有一個 N/A）；保留兩者與逐項理由，不合併成一個冒充真值的分數。

## 5. 本輪得到的實作判斷

1. **Durable control 應保留為所有實驗的執行底座。** 重播去重、原始 usage、固定模型／來源和失敗即停，已能直接驗證。
2. **優先移除重複進度回報與不用模型的統計工作。** 這不需要犧牲使用者已提供的房源事實。
3. **不能為 5.49% 的 observed token savings，就把 compact handoff 宣稱成無損預設。** 更合理的是保存來源、更新關係和关键限制，對缺失資料有明確補取流程。
4. **小文件先直接提供相關原文。** 本輪 adaptive 的额外模型回合昂貴；固定程式檢索可先縮小材料，再由模型作答。
5. **Judge 要知道候選實際看到什麼。** 自動分數仍需可追溯的失敗分析；「幻覺」「遺漏」「不精確引用」不可混為一談。

## 6. 驗證、保存與邊界

- 完整離線套件：**1,759 tests，42.755 秒，PASS**。另有固定的 34／38／158-call stub matrix、legacy CLI/API replay、跨日／計時分支、symlink recovery、未知 usage 和 nested A/B stop 測試。
- 歷史 **3,849 個檔案逐一 SHA-256 驗證未改動**。
- 新品質資料和歷史 raw 均在私人 operational archive 保存；實作 Git bundle 可離線 clone。備份位置與恢復入口見 [local-backup.json](local-backup.json)，該目錄的 `COMPLETED.json` 記錄交付 commit、全部 archive hashes、fresh-clone/fsck 驗證。
- 沒有發布 repo、部署回饋服務、寄信或重啟 Claude。

Token ceiling 在呼叫之間檢查，仍可能超出一個 call；ledger 管理 runner 發出的呼叫，不是對廣權限 shell 內任意另開模型的完整計費監控。檔案重播也不能撤回外部副作用或還原遠端 Claude session。這些界線與 [migration guide](migration.md) 一起保留，不宣稱已完成所有安全隔離。

公開回饋的獨立建議已整理成 [全選項＋私人文字筆記設計](../community-feedback-design.md)。它是可審閱的設計文件，目前沒有新建投稿服務或收集使用者資料。
