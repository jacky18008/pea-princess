# Grok Bot 原生介面相容性測試

2026-09-09。已在使用者安裝的官方 Grok Bot 桌面 app 建立 **Pea Princess Test**，透過正常附件介面提供公開 skill ZIP，執行三個人工指定的 synthetic prompts。不是 metered API runner，也沒有讀取訂閱 cookie／token。沒有 Claude 呼叫。

## 範圍與版本

- [事前計畫](grok-local-smoke-plan.json)固定最多三個測試 prompt；[完整原文](grok-smoke-prompts.json)已保存。Bot 建立時的自動歡迎訊息不列入這三個 prompt。
- 提供的 ZIP 有 79 個成員，SHA-256 `b3ab818b201f57faab7505b2c95bebc08f254d86e75b43bf03b22404e06cf8e5`。已檢查檔名，沒有私人 state、對話或登入檔案。
- 沒有把 persona 卡片或評分答案放入 Grok；這是獨立的小型相容性案例，不是原 P4 benchmark，也不是 Grok／Codex 品質 A/B。
- 使用 Grok Bot 可用的預設模型；UI 沒有顯示可核對的精確模型版本、內部模型呼叫數和 token usage，全部保持未知。三個 prompt 不等於三次底層模型呼叫。

## 結果

| 測試 | 觀察 |
|---|---|
| 1：載入公開 skill | 接受 ZIP，回報解到 `/workspace/pea-princess-compat-test/vet-flat/`，讀 SKILL.md／session-harness.md，正確解釋用途、三種模式及私人 state；回報 Python 3.13.5 |
| 2：保存條件與比較 | 正確算出 A £2,420，超 £2,400 上限 £20；B £2,310，但 ground floor 違反原条件；沒有把任何一間判成整體 PASS |
| 3：候選別預算和 conditional | A 上限只改為 £2,350，超支差額變 £70；B 仍 £2,400。B 的 ground floor 僅在獨立現場乾燥證明成立時允許，現有證明缺席，沒有變成無條件 PASS |
| 來源雜湊 | Grok 回報的 SKILL.md SHA-256 與本機原檔一致：`ee9f59b5a29d57c441e7ad4c4a1a54176c2898d1029e6e484f8d9ca55baa3bbe` |
| Durable 狀態 | 回報 revision 35 → 45、舊事件保留、fresh Python process context／verify 通過；尚未取回 state bytes，因此這部分是模型回報，非本機獨立驗證 |
| 證據交付 | **未通過。** ZIP 在聊天顯示「圖片無法使用」，沒有可用下載入口；透過 Bot 的正常電腦／檔案管理員看見 scenario、vet-flat 與 30,087-byte ZIP 確實存在，但未成功下載並檢查內容 |

原生 UI 的時間標示約為第一步 32 秒、第二步 155 秒、第三步 94 秒；這是送出與最後回答時間差，不是底層每次 call 的計時或計費證據。過程沒有再追加第四個 prompt 來修附件。

## 品質缺口與可得到的結論

**可行方向：** 這次看到了「提供 skill／工具包 → 由使用者自己的 Bot 在它的工作環境執行 → 承接下一則條件修改」的實際流程。不需要我們提供遠端模型 worker。這裡的工作目錄在 Grok Bot 的雲端電腦，並非使用者 Mac 的本機磁碟。

**仍有兩個缺口。** 第二輪把房東自述的「估計通勤 20／24 分鐘」顯示為打勾，摘要没有繼續明示估計／未驗證性質。數字保留正確，但證據語氣過度確定。另一個是證據附件交付失敗；不能只看 Bot 說「打包完成」就把備份／恢復驗收標為通過。

Grok 回報第三輪曾修正乾燥證明事實的原文對齊問題，這與有 exact-quote 檢查的 state engine 設計相符；未取得原始事件／錯誤輸出前，不能聲稱我們獨立驗證了那次拒絕或修正。

回報的第三輪 event hash 為 `117a173e6e6d8be963c31dfe9e587ea82238b5746dfb6d5e899fa634abc0b431`，ZIP hash 為 `ce6a49b1f2f303f26e6da0a9c20df90e63d5ddffe08677d3a1ee72fc945778df`。這兩個值目前都是遠端模型回報，並非本機驗過的 archive checksum。

本輪沒有把 ZIP 註冊成原廠 Plugins 清單中的可自動觸發 skill；測到的是 Bot 對明確附件指示的載入與執行。跨會話自動發現、手機使用、原生 skill import、其他模型及較弱模型表現仍需各自測試。

## 下一個有界案例

1. 修好官方附件交付／下載流程，再取回 synthetic state，用本 repo 的可信 engine 驗證 hash chain、原文、scope、conditional 和新 process 恢復；不執行遠端包內未知腳本。
2. 加入「估計／未驗證時間不得顯示為確定通過」的必要判準，與費用估計一起驗證。
3. 將同一個 public skill 透過正式 Plugins／Skills 入口安裝，測下一個新對話是否會載入必需文件；不能用這次明確提示的成功代替自動觸發測試。
4. 只有取得可比較的模型版本及完整用量後，才做成本／品質對照。訂閱 UI 沒有 token 明細時應保留未知，不填零。
