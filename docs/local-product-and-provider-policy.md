# 本機 skill 的產品範圍、訂閱與供應商政策

2026-09-09 核對。Pea Princess 的公開交付是使用者下載的 skill／tool，由使用者自己的 agent 執行。現在的 persona 網頁是開發者／使用者的本機測試台；不是我們代管的聊天服務。先測桌面，手機或遠端執行交給各 host 原本支援的方式。

## 我們交付什麼

| 元件 | 負責者 |
|---|---|
| SKILL.md、引用文件、Python scripts、schema、安裝包、版本與驗收案例 | Pea Princess |
| 模型登入、訂閱資格、模型供應、sandbox、裝置或雲端執行環境 | 使用者選用的 agent／供應商 |
| 使用者原話、條件、文件、狀態及報告 | 使用者自己的工作目錄；可能在其裝置或所選 agent 的雲端環境 |
| 手機操作、遠端連線、背景工作可用性 | 各 agent 的官方產品能力；不是下載 ZIP 到手機就能執行 Python |
| Token／呼叫上限、未知用量停止、無進展停止 | 保護使用者的額度、費用、時間；訂閱仍有 rate limit |
| 可選公開回饋資料 | 獨立全選項 feed；不包含私人對話或選填文字 |

不需要為這個下載產品建立自己的模型 worker、使用者模型帳號、模型轉售收費或多租戶聊天資料庫。若未來另做代管服務，那是另外的產品範圍，才需要那些設施。上一次 1–2 週／3–6 週估算用了代管服務假設，不能當成下載 skill 的上線工期。

檔案放在使用者本機不代表推論完全離線；原廠 agent 仍可能把 prompt 和文件送往它的模型服務。Grok Bot 這類產品也可能在使用者所屬的雲端電腦處理檔案。Pea Princess 不自行接管其帳號或保證所有 host 的保留／訓練政策相同。

## 個人訂閱能否使用

結論是保留「在原生 agent 裡安裝 skill」這條路線，並將登入與計費留給原廠。下列是官方文件支持的設計判斷，不是廠商對 Pea Princess 的個別認證，也不保證未來政策永遠不變。

**Codex。** 官方支援 ChatGPT 訂閱登入與 API key 兩種方式，後者按 Platform API 計費。官方 `codex exec` 文件明列沿用 CLI 登入、JSONL 輸出和 resume；自動化建議以 API key 為預設，也另列有限制的 ChatGPT-managed CI 路徑。因此不能把所有 `exec` 都說成強制 API 計費，也不能把任意自製服務視為訂閱授權範圍。[登入與計費](https://learn.chatgpt.com/docs/auth)、[非互動模式](https://learn.chatgpt.com/docs/non-interactive-mode)

這個本機 tester 使用未修改的 Codex CLI、自己的既有登入及公開 CLI 參數；不讀取、轉傳或共享訂閱 token。發布的是測試工具，不提供公用模型 endpoint。一般條款仍禁止分享帳號、繞過額度及未授權的輸出擷取；官方支持的 CLI 流程不能被擴張解讀成網頁 scraping 或私有 session endpoint 的許可。[OpenAI 條款](https://openai.com/policies/terms-of-use/)

**Claude Code。** 原生 skills／plugins 有正式支援。官方 June 16, 2026 公告明說 June 15 的 SDK／`claude -p` 計費變更已暫停，目前仍計入訂閱額度；同頁下方舊方案僅保留參考。不能繼續引用舊新聞說它已全面生效。[Skills](https://code.claude.com/docs/en/skills)、[最新計費公告](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)

原生未修改 Claude Code 讓使用者自己登入，和第三方 app 蒐集／代轉 Claude.ai token 不同。Legal 文件禁止後者；Agent SDK 文件也不能被解讀成任意第三方都可自行提供訂閱登入。Pea Princess 只交付 skill／scripts，不處理 Claude.ai 憑證。[Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)、[SDK](https://code.claude.com/docs/en/agent-sdk/overview)

有訂閱仍可能意外用到 API：Claude 官方指南指出 `ANTHROPIC_API_KEY` 可以優先走 API 費用。使用前要由原廠介面確認 active auth；不在安裝包保存金鑰，也不讓 fallback 靜默切換收費方式。[Pro／Max 指南](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)

**Grok。** 官方 X Premium+ 頁面確實列有 SuperGrok／Grok Bot，不能只憑使用者說的 $31 要求另購方案。部分 get-started 頁面仍列較窄方案，實際以登入／綁定後可用入口確認。[X Premium](https://help.x.com/en/using-x/x-premium)、[Bot availability](https://docs.x.ai/grok-bot/teams-and-enterprises)

Grok Bot 支援 skills／plugins 和持久工作環境；普通 Grok 也已有可從對話或檔案建立的 Skills，但上傳檔案不等於保證完整讀取或執行每個腳本。[Bot skills](https://docs.x.ai/grok-bot/skills-routines-and-automations)、[Grok Skills](https://x.ai/news/grok-skills)、[檔案 FAQ](https://docs.x.ai/grok/faq)

Public API 另有用量計费，Premium+ 不證明帳號有 API 餘額；但 xAI 也正式提供特定 subscription OAuth integrations，例如 Kilo Code。因此也不能一概說「所有 agent 整合都必須另買 API」。只使用原廠公開支援的入口，不把 cookie／私有 session endpoint 當 API。[API billing](https://docs.x.ai/developers/faq/billing)、[正式 OAuth integration](https://x.ai/news/grok-kilocode)、[AUP](https://x.ai/legal/acceptable-use-policy)

Grok Build 有明確 `.grok/skills/`、SKILL.md 與 Claude Code／`~/.agents/skills/` 相容規格；其 `allowed-tools` 不是權限隔離。這個「格式相容」也不能替代實際安裝和多輪驗收。[Build skills 規格](https://docs.x.ai/build/features/skills-plugins-marketplaces)

## 下載版的發布門檻

已有可用的 skill ZIP、prompt pack、腳本和本機測試台，可以先以明確標示限制的 alpha 分發。廣泛推薦之前還要完成：

- [ ] 在乾淨環境驗證安裝、更新、移除及相對路徑；公開 package 不含私文、state 或 credentials。
- [ ] 各目標 host 至少一次真實多輪驗收：載入來源、補件、中途更改条件、恢復、最終未完成項目。只支援格式不等於已通過。
- [ ] 將弱模型漏讀、過期條件、數字來源錯誤及 persona simulator 缺陷加入固定 regression cases。
- [ ] 發布相容性表：完整 scripts、fetch 或 manual；哪些 host 可強制注入 state、哪些只是提示模型去讀。
- [ ] 明示登入與計費由 host 管理、rate limit 不自動 retry；私人素材保留與刪除路徑清楚。
- [ ] 用固定 release commit、checksums 和可重建 package 發布；這轮沒有自動發布 GitHub Release 或推送私人紀錄。

Persona tester 的 call ceiling 和持久 ledger 是測試／整合層。使用者直接在原生 agent 聊天時，Pea Princess 無法僅靠 SKILL.md 攔截該 host 每一次模型呼叫；必須如實區分程式可強制保證的部分，以及依賴原廠 host 的部分。

## 插話如何成為測試集

本機 UI 已保存每則插話原文、情境變更類型、排隊順序、前後回答、controller 和 usage。私人資料保持在 `.pea-playground/`；本桌面任務中新要求也保存於 `.pea-state/`。測試候選匯出方式见 [playground cases](playground-cases.md)。候選仍含私人原文，先保留在自己的 repo runtime；不是可直接公開的 benchmark，也不是標準答案。對齊不確定或尚未回答的輸入必須標記 unknown／queued，不硬湊對應。
