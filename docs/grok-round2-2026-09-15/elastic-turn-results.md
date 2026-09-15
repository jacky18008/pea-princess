# Grok Build CLI：放寬 14 次上限後的完整初答與用量

2026-09-15。這是一則使用者初問的端到端重跑，不是 Grok Bot 的完整多輪對話，也不是接續先前已取消的 CLI session。原本 `--max-turns 14` 在 14 次 agent 內部模型／工具迴圈時停止、沒有給使用者看的最終文字；本次在**另一個乾淨的獨立專案**執行一次同一合成使用者原文、同一公開 `pea-princess` 已安裝 SKILL 位元組、Grok 4.6、預設 effort／standard 深度、同一單一路由，不另附加短規則。actor SHA `125e7cd0140f610b7db2454f33e0329cd2ccdcc1e9085dcd3e87c5bbe2469208`；active SKILL SHA `3b91d2940d7bd440a3d6e690918508c7d140951ab14495b579e0356aab62d673`。`grok inspect --json` 確認本地實際路徑；`GROK_HOME` 僅改測試用隔離設定並在執行完恢復。CLI 1.0.30 的 `resume/continue/fork` 先前回 `Session does not exist`，不能稱本場是第 15–17 次「原 session」繼續。

本場 CLI 仍需在啟動時給一個固定硬上限；`--max-turns` [官方參考](https://docs.x.ai/build/cli/reference) 沒有描述執行中調整機制。將 **14 當為觀察點，32 為保護硬上限**：到 14 記錄用量與進度，正常完成便提前停止；若超過，再看是否仍在產出有用證據。實際命令使用 `--model grok-4.6 --no-subagents --sandbox workspace --always-approve --max-turns 32 --output-format streaming-json --prompt-file ...`。最初一次命令拼寫和一次 Codex 外層 sandbox 起動錯誤均在模型執行前退出，已分別修正；成功命令用受授權外層執行，仍保留 Grok 本身 workspace sandbox。從 raw 出口數只有**一通成功的模型測試 dispatch**。後來提交的 [可重用單次探針](/private/tmp/pea-princess-grok-cli-lean-route-20260915/tools/grok_elastic_probe.py) 提供 soft14/hard32、owner-only stream、inspect/SHA、無自動重試、預設 3600 秒 deadline 與離線 `audit`；它的 `run` 是後續實驗用，**不是假稱由探針啟動這場已跑的命令**。

| 指標 | 此次同位元組、放寬上限的乾淨重跑 | 早前 14 次失敗場（只作背景） |
|---|---:|---:|
| 第 14 次的可觀察 processed | **739,811**（當時 29 工具） | **643,882**，當場被取消 |
| 實際停止 | **17 次，`end_turn`／CLI exit 0，1600 字元完整初答** | 14 次，`cancelled`／exit 1，僅未送 draft |
| 全場工具 | **34**：10 read、16 terminal、2 list、1 grep、2 write、2 edit、1 native ask | **34**，類型分布不同 |
| 全場 input＋cache read＋output | **190,730＋782,336＋19,934＝993,000 processed** | 139,873＋483,968＋20,041＝643,882 |
| CLI 所報美元估價 | **US$0.30335888**；不是訂閱實際扣額 | US$0.21827184；同樣不是扣額 |

此次 output 的 19,934 含 16,337 reasoning tokens；cache-read 782,336 佔約 **78.8% processed**，表示模型／工具循環反覆帶回上下文，即使有 cache 命中，處理量仍累加。**本場**第 14 至 17 次新增約 **253,189 processed**，主要處理先前掃描資料、數字 lint、修字與答覆；不能拿 **993,000−643,882＝349,118** 當作原場「放寬三次」的因果增量，因為兩場是隨機性不同的乾淨呼叫。32 是保護欄，不是每次必燒到 32；經單次 dispatch 測試，這次在 17 完成。以離線 `audit` 解析端 `end.stopReason=end_turn`、末次 response 文字及 17 個 `usage` 事件，沒有把中途進度或 `.pea-state` 的草稿充作 final。

## 回答有送出，但品質還未達可公開的門檻

[原生匯出的對話](/Users/chenhsienhao/Documents/UK-Study/pea-princess-evidence-20260915/grok-build-cli-elastic/actor-01-transcript.md) 含初問、逐步進度與真正送出的結尾；[單獨最終回答](/Users/chenhsienhao/Documents/UK-Study/pea-princess-evidence-20260915/grok-build-cli-elastic/final-reply.md) 可直接 review。先比較 A/B 的廣告房租、房數、面積與同址 EPC 面積衝突；確實查到公開周邊掃描和 TfL，並把「喜歡安靜／45 分鐘左右可談」留為偏好；沒有再開商業房源、找新房、聯絡或安排看房。`reply_check.py` 在送出前對**草稿**先抓到兩項 £350 算式上下文缺失，模型補後草稿 lint 通過；對**最後送出文字**的事後檢查 exit 0／0 findings，不能與草稿的 native pre-send receipt 混稱為最後輸出的強制 gate。產品 state 當時 `verify` revision 9／9 events／0 documents；此初問未要求正式保存比較，故沒有跑 `save_gate` 不單算違規，但後續接續與保存尚未驗。

獨立 Astra 評估認為**可見第一輪已完成，品質仍有 P2 缺陷**：答覆把 Cable Walk 最快接駁的 08:58（9:00 前只剩兩分鐘）當作主要不利條件，卻同文列出鐵路約 30 分鐘、08:36 到的備案；推薦只深挖 A，應先比較同口徑路線、門口位置／班次等待和使用者對價格、走路與多一房的取捨。B 噪音範圍 56.7–63.4 dB 與文中用的 53 dB 相減，應是**3.7–10.4 dB**，原回覆卻寫 **7–12 dB**；native 數字 lint 有掃描來源字樣仍沒抓到此計算錯誤。WHO 53 dB 在掃描文字有值，原回覆沒有對這項標準的獨立官方 URL；公開數據和區域治安也缺可點開來源。送出前串流的第一句只說正在讀 skill，不先給 A/B 的有用比較；正式答覆雖以比較開頭，1600 字元還含不少內部時間、重複算式和硬條件術語，超出初問舒適長度。native `ask_user_question` 確實試過一次，tool 回覆 **沒有 user 可用**，所以不能稱原生選項已交到人的手上；最後的自由文字問題仍可見。沒有 P1 的「再也答不出來／偏好當必要」重現，不代表 P2 已解決。

另提交了[噪音數字修正](/private/tmp/pea-princess-grok-cli-lean-route-20260915/skills/vet-flat/scripts/noise.py)（`c13e619`），讓 scanner 分別算樣點和街道區間的差值，並給出 WHO 2018 官方 executive summary；16 項噪音與 31 項 area-scan 聚焦測試通過。**這項源碼修正晚於本場 pinned SKILL**，須重 build、核對 ZIP SHA 後再跑模型，不能替剛才的錯誤回答追認品質。

## 對 US$20／US$30 訂閱用戶怎麼判斷

這場**一則初答**動用 17 個 agent 模型內迴圈、34 個工具、993,000 processed 並仍有 P2 數字與推薦缺陷，作為日常找房入門的**預設路徑不合理**；14 這個硬上限本身也不合理，因它砍掉了有用研究之後的答覆。應讓 14 是可觀察 warning、32 和 deadline 是保護欄；更重要的是證據已有 A/B 兩次掃描與同一目的地路線後，編排成**短而帶 source/position/status 的 evidence packet**，停止重讀全 skill/源碼及無關 `--help`，以一則短答和一個有用追問收束。這是下一輪待測的架構，不可由此場直接報省 token 或等效品質。

[xAI 官方 SuperGrok FAQ](https://docs.x.ai/grok/faq) 說付費 Chat、Build 等產品會共享按週重置的使用池，長 coding task 耗計算較高，實際用量以 `Settings → Usage` 的**before/after 百分比與 Build 分項**為準；[定價頁](https://x.ai/pricing) 列 SuperGrok US$30/月。此場從 Grok Build `/usage` 讀池值回「Couldn't load usage… Internal error」，Codex IAB 的 grok.com 未登入；**沒有有效的前後百分比，也沒有官方的 token→池百分比換算**。此場命令從 task-only OAuth 授權，沒有觀察到 XAI_API_KEY；CLI 的 `$0.30335888` 是 telemetry 估價，**不是帳單出現的新費用或「只占 $30 的 1%」**。若用戶選 API／額外付費池，計費另需查實際 account/usage receipt。

本使用者先前說使用 X Premium+ 附帶的 Super Grok，這和直接購買 US$30/月 SuperGrok 不是同一張收據；[X 官方現行 Premium+ 價格表](https://help.x.com/en/premium-plus-price-update) 列英國 £31/月、美國 US$40/月。此輪只驗到 Grok CLI 能用 OAuth 跑模型，**未讀到該 X 帳戶已連結的 Grok 週池／帳單**；不能拿對照價格推定實際權益或消耗比例。

[OpenAI 官方 Codex 定價說明](https://learn.chatgpt.com/docs/pricing) 列 Plus US$20/月含 Codex；本地 Terra 約 25–200、Sol 10–100 **每五小時估計訊息數**，非固定額度，任務大小、模型、上下文、推理、工具與 cache 會變更使用。Grok 4.6 的 993,000 processed **不能換成 Plus 可做幾輪**，也不能把 17 個內部迴圈視作人發了 17 則訊息。等兩平台都有相同情境、官方用量前後讀數、品質盲評，才能對 $20 vs $30 的每週實際容量做數值結論。現階段可負責任的結論只有：本場 Grok 已送出初答，卻消耗大且有未修品質錯誤，**不宜讓低價個人方案每次都走這條深掃加長答路線**；不主張換方案或加購。

後續對此 **同 frozen actor／同官方結果快照** 用修正後 pinned ZIP 做 2–3 次 fresh arm，記同帳戶週重置日期與前後 pool%，不夾其他 Build/Chat 使用；每條都驗 model calls、tool status、短答品質、3.7–10.4 dB、同口徑 TfL／追問、明確「存好」的 journal/comparison/TODO `save_gate`、重開接續。單次完成不能估失敗率或品質浮動。原始 1.68 MB NDJSON、actor、active SKILL、state scan/events、export、checker 和 SHA 收據在 [owner-only evidence manifest](/Users/chenhsienhao/Documents/UK-Study/pea-princess-evidence-20260915/grok-build-cli-elastic/sha256-manifest.json)，[run-summary.json](/Users/chenhsienhao/Documents/UK-Study/pea-princess-evidence-20260915/grok-build-cli-elastic/run-summary.json) 是可複查數字；不包含 OAuth／API 憑證。
