# Grok Build CLI：單一路由 v4 的失敗樣本與下一步

2026-09-15。本分支 `codex/grok-cli-lean-route-2026-09-15` 從 v4 整合修補 `4ef889d` 出發，加入 `comparison-research.md` 單一路由、TfL 七位 stop ID 類型／說明，其他比較及保存門檻沿用 v4。**這是實驗分支，尚不採用到公開 main。** 同一 frozen 合成使用者初問 SHA-256 `125e7cd0140f610b7db2454f33e0329cd2ccdcc1e9085dcd3e87c5bbe2469208`；A/B/Sketch 真實廣告摘錄和公開來源範圍見 [v3 固定方法](v3-method.md)。Grok Build CLI 1.0.30、`grok-4.6`（telemetry `grok-4.6-build`）、預設 effort、預設研究深度 standard、task-only `GROK_HOME`、`--no-subagents --sandbox workspace --always-approve --max-turns 14`。`grok inspect --json` 的 active `pea-princess` 路徑是解開的本分支 ZIP，無舊全域 pea skill 和 Claude 相容 hook；已裝 SKILL SHA-256 `3b91d2940d7bd440a3d6e690918508c7d140951ab14495b579e0356aab62d673`，當時 ZIP SHA-256 `2db65343885eff7948750b844e8d108ac5a7e490f53b417cebdd21e343c122d2`。被測安裝的完整 regular files 打成 owner-only [檔案與 SHA manifest](/Users/chenhsienhao/Documents/UK-Study/pea-princess-evidence-20260915/manifest.json) 中 `grok-build-cli-v4/tested-installed-skill.tar.gz`。後來為修舊測試的精確文案縮了 SKILL 前幾行並重 build（最終 ZIP `f6a1f4bf5646fa856490d3479c044a1178c2079dceb4fd80225b45b966d097ed`）；該新位元組**未經此 Grok 場驗收**，不能冒充被測 ZIP。

## 實際結果

| 固定 v3 actor 的 Grok CLI arm | 官方資料是否被呼叫 | 完成文字 | 工具／模型 | processed tokens |
|---|---|---|---|---:|
| v3 無額外短規則、42 工具後人工終止 | 否 | 否 | 28 read＋13 grep＋1 list；9 已知 usage snapshots | 約 **422,523 下界**，無 end |
| v3 ZIP＋短額外規則、8 turns | 是，第三通模型前開始 | 否 | 8 models、30 tools | **317,420** |
| **v4 單一路由、無額外短規則、14 turns** | 是，A/B 周邊與 TfL | **否**；僅專案內 draft | 14 models、34 tools：10 read、3 grep、2 list、13 terminal、6 edits | **643,882** =139,873 normal input＋483,968 cache-read＋20,041 output；CLI 估價 US$0.21827 |

前兩列取自 [v3 CLI 報告](v3-cli-results.md)。max-turns、extra rules、基底程式與專案檔不同，這不是可估品質等效或嚴格省 token 率的 randomized A/B。第三列雖有較多可用查證，處理量**更高且仍無 final**，所以此短路由不能全面採用。所有 raw NDJSON 在 owner-only evidence；[Grok export 的靜態可見回合](v4-cli-route-transcript.md) 與 [未送出的 draft](v4-cli-route-draft.md) 可供日後評閱，不要把 draft 當使用者已看過的 reply。

實際工具順序：先讀 SKILL、rules、`comparison-research.md`，仍加讀 session-harness、state-api、listing_fields 部分源碼；從使用者給的摘錄另建三份 `.pea-listings`。A 的 `SE3 7RS`＋Seren Park Gardens 路名 lookup 失敗，改完整郵遞區號掃描，A 最終 `complete`、`Restell Close` 樣點（不是 172 號戶內）；B 的合法 `SE10` outward code＋Cable Walk 街道中點 `partial`。v4 結果在兩次成功掃描的 `quiet.night_economy_radius_m` 都是 **100**，model-facing `reading` 寫「OSM 在 100 m 查到 0 mapped，不能證明沒有場所」，沒有 v3 的錯誤 300 m 範圍。這是**程式輸出修補在真實官庫呼叫生效**，不是 Grok final reply pass。

TfL 初次用 `London Bridge Station` 收歧義，CLI 隨後以回應中的**鐵路站 `1000139`** 重查 A；B 用 scanner 回的 Cable Walk 中點座標同樣查 `1000139`，不再另搜尋終點座標。官方返回 A 17 分鐘、B 28 分鐘；B 最快方案的 08:58 到站只有 2 分鐘餘裕，但 rail-only 方案約 30 分鐘、08:36 到，故不能由前者直接說 B 平日難準時，應比較可選班次／穩健度並讓使用者權衡。不同出發點仍不是各戶門口，零等待接駁也不能保證實走。

在 `max_turns_reached` 前，CLI 建出 `.pea-state/events.json` 並記錄這則 actor：房數與 £2,500 上限為 `must`，臥室安靜和「約 45 分鐘可談」為 `prefer`，9:00 前到站與這輪不找新房／不約看房各有使用者原句與 scope。**這一項比 v3 Bot「偏好升成硬條件」有改善**，但花了多通模型呼叫去讀狀態文件；沒有比較／TODO 的正式 output 註冊或 `save_gate` receipt，且本初問本來也沒要求「存好」。後續追問和保存未驗。

未送 draft 第一段已給 A 優先、B £350 價格差和 Sketch 最近租出；它把兩間廣告當「你提供的摘錄」，沒有預約。然而約 1,800 字的初答重新列出大量內部算式／小區統計，不符合此前設定的「先給引人往下用的有用資訊」長度和焦點；B rail-only 08:36 的備案又與「B 最快方案壓 9:00」的推論拉扯。後置 `reply_check.py` **exit 1、3 個 numbers findings**，其中表格房租／45 分鐘句有上下文來源但 regex 漏判，WHO 道路 53 dB 指引沒有當輪來源收據，需要人類確認或刪掉。CLI 沒有實際在送出前跑 checker，僅呼叫過 `--help`，而且沒有可見 final，故不能通過「講人話」或整輪品質 gate。

## P1–P3 分級與架構處理

**P1：回合耗盡沒有 reply。** 無 final 時，使用者看不到已完成的公開資料研究；14 models／643,882 processed 比 v3 瘦身 arm 高。Host controller 要從 `streaming-json` 計模型呼叫、工具類型、processed/unknown spend、階段與 deadline；在例如 6–8 個 research tool batches 已得兩筆官方結果後，強制切**回答階段**，用輸入 actor＋經 hash 固定的小 evidence packet 開一個禁止額外工具的新 session。這不是透明原 session 接續，須在報告標 `handoff`。先做 runner 離線 stub／中斷／重開測試，避免真模型再反覆探路。

**P1：宿主沒有強制保存與送出前 gate。** ZIP 裡的指示不能保證 Grok Bot／CLI 自己執行 checker 或 `save_gate`。CLI 可由外部 controller 拒絕未通過 authority/source/length/state receipt 的 final；xAI 官方 [Hooks](https://docs.x.ai/build/features/hooks) 的 `PreToolUse` 是唯一 blocking event，可阻止超額讀檔、商業 listing 抓取或外部聯絡，`Stop` 只通知、不能擋壞 reply。Project hooks 要使用者 trust，Grok Bot 是否裝載同一 hooks 未驗；因此公開 skill 附安全規則、宿主測試台加硬 gate，產品說明明示哪個 host 有 enforcement。

**P2：模型把最快方案的兩分鐘餘裕當總體通勤風險。** 程式應輸出同一站點、日期、door buffer 下 `all`/`rail`/`bus` 的可比摘要和假定等待，模型只在該 packet 上排序，或主動問使用者「便宜一房與穩健通勤哪個更重要？」。沒有精確門口時留下未知，不自動排除 B。

**P2：初答太長、checker 誤報和未引用 WHO。** 把研究 JSON 壓成一頁 `{listing_reported, official_estimate, unknown, candidate_decision, next_question}`，先給 2–3 個實際差異與一個選擇；來源半徑／位置在可展開證據中。人類 QA 檢查「已回答當下需求／有推進／不把建議當決定」與數字來源，不能只靠字數或 regex。

**P3：Grok Build CLI 1.0.30 的 session list/export 成功，resume/continue/fork 實測均回 `Session does not exist`。** 對長對話把要求原句、變更、比較、來源 snapshot、TODO 存在產品的 durable state，export 只當審閱附件；在 CLI session loader 修好前不把 host session 當唯一 checkpoint。

下一個可採用的實驗是**兩階段 deterministic research＋小 evidence answer**，同 frozen actor、同 Grok 4.6、同 effort/depth、至少兩次；每輪都要看 final、source/authority lint、pre-send enforcement、follow-up 中 A「可考慮」與 B「尚未決定」以及 current TODO receipt。若 handoff 能在明顯少於 643,882 tokens 下完成而不損品質，才再比較它與其他模型；單純在 SKILL.md 多加論述，本場已無實驗證據支持。

本輪寫文件時 main 已由 Claude 等工作前進到 `2cad479`；它比本實驗的共同祖先多四個 commits，`SKILL.md`、掃描／checker 等仍有位元組差異。**測過的安裝不會因 main 新 commit 自動更新**。保留這個 frozen 實驗分支；下一次先以 `grok inspect`、ZIP/內層 SHA 對照明確選出的版本，再開以最新 main 為底的整合分支處理衝突、重跑同 fixture，才有可比較的同步聲明。不要把本分支的 full-suite pass 或官方資料輸出稱為 `2cad479` 版也已通過模型驗收。
