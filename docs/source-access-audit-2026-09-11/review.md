# 查核複核紀錄

日期：2026-09-11。主查核與分組查核交叉進行；以下是報告品質複核，並非律師意見、來源方批准或runtime安全驗收。

## 已核對的關鍵結論

- Root 重新讀取 Rightmove §5.2/5.5/8.3/13、OnTheMarket §2.2/3.3–3.5 及其 robots、Booking 現行 A15.2，確認自動瀏覽、保存和連結是不同問題。Booking 同頁也附有舊版條款，不能只搜尋較舊的「commercial purpose」段落。
- 獨立複核確認 EPC 非地址/UPRN OGL、地址用途限制；London Air 現行OGL頁與舊API文件衝突；GLA官方guest-read文件；Street Manager公開訂閱與内部業務API分開。
- 獨立複核確認 Expedia Rapid評論48小時快取、Travel Redirect新申請暫停、Trustpilot顯示評論每日刷新等限制，不能維持通用永久原文副本政策。
- Root 閱讀五份分組報告，檢查每個來源紀錄的身分、操作、官方證據入口與未知項目。沒有把廣告商upload feed當成租客全站read API，沒有把金鑰／授權費unknown改成零。

## 複核後已修正的三處表述

1. EPC 地址公告本身保留符合條件的非商業研究／私人研習等法定例外。一般地址資料庫是否落在用途外是本報告的判讀，不能写成排除一切例外的法律斷言。
2. Overpass公共主機規則明確限於本輪核對的 `overpass-api.de` 營運者指引；其他獨立主機有自己的服務条件。
3. 永久免費發佈skill不等於永遠禁止使用者自選付費API。本輪未獲授權開帳號／付款／啟用新整合；未來可選API仍需明示資格、費用及用途。

## 交付檢查

本輪產生54筆provider/product紀錄：5個房源平台、9個仲介／業者、8個住宿／評論來源、17個政府／開放來源分組、15個補充來源。現行 `sources.yaml` 的53個ID均已對照，沒有未映射ID。這是inventory完整性，不是54站全部獲許可；某些紀錄涵蓋多站或多產品，borough仍有逐站待查範圍。

JSON可解析、索引唯一、JSON Pointer可解、source reference可對照、Markdown本機連結存在，以及來源inventory雜湊一致均已檢查。`git diff --check` 檢查本輪檔案。檔案清單與SHA-256保存在 [validation.json](validation.json)，其雜湊只證明本輪報告內容，不是官方原頁真實性的證明。

本次只交付文件與索引。沒有修改目前運行中的skill、抓取helper、來源白名單、playground或評估器；沒有建立或啟用新API／帳號。後續待辦及驗收條件在 [implementation-plan.md](implementation-plan.md)。因此「查核已完成」不等於「所有來源都能串接」或「產品已可公開上線」。
