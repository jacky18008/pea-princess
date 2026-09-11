# Supplemental public-data access audit — 11 September 2026

針對「永久免費、使用者本機安裝、由自己的 agent 工作」補查 15 個來源／產品。這是授權證據清單，沒有更動程式、來源白名單或執行政策；沒有建立帳號、付款、聯絡供應商、跑房源爬蟲或模型實驗。機器可讀細節在 [supplemental-public-data.json](supplemental-public-data.json)。

「未知」不是准許，也不是違法判定。官方 API、內容授權、個資責任、服務配額需分開看。robots 不是內容授權；本輪只重試 TPO／Propertymark robots，均未成功，其餘未重查。只保留摘要與網址，未保存完整條款快照；官方搜尋索引與直接讀取不一致處已註記。

## 已有實際減少手動複製的路線

| 來源 | 可行方式與限制 |
| --- | --- |
| Companies House | 免費官方 API，需開發者 key；每五分鐘 600 次。公開登記資料的法源與 Companies House 自寫內容的 OGL 不同，不能把所有申報文件一概視為 OGL。第三方權利／個資仍需處理。HTML 不是已有 API 欄位的必要途徑。[法源及再利用](https://www.gov.uk/government/publications/companies-house-accreditation-to-information-fair-traders-scheme/public-task-copyright-and-crown-copyright)、[免費 API](https://www.api.gov.uk/ch/companies-house/)、[配額](https://developer.company-information.service.gov.uk/developer-guidelines) |
| Land Registry Price Paid | 官方月檔／年檔 CSV、查詢工具與 linked data，可下載後本機篩選。OGL 需署名；Royal Mail／OS 地址資料另有限制，個人／非商業使用與住宅價格資訊展示獲許可，不能推廣成所有地址用途。UPRN／INSPIRE 對照表另有條件。[下載及授權](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads)、[查詢方式](https://www.gov.uk/guidance/about-the-price-paid-data) |
| Ofgem | 官方 Crown 內容可按 OGL 免費讀取、保存與引用；排除標誌、已標明第三方內容。獨立 register／API 需另查。[Copyright](https://www.ofgem.gov.uk/c-ofgem-2026) |
| Mapillary | 官方免費 API 與 CC-BY-SA 圖像是候選路線；保留作者、原圖／來源、授權，適用時遵守相同方式分享。完整版服務條款這次回傳登入頁，尚未完成服務權限／配額審核；圖像許可不等於所有衍生資料許可。[圖像授權](https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data)、[免費說明](https://help.mapillary.com/hc/en-us/articles/8348198426396-Mapillary-FAQ)、[官方 API 範例](https://github.com/mapillary/api-demo)、[待讀完整條款](https://www.mapillary.com/terms) |
| KartaView | 官方條款 §4 將街景／3D 資料以 CC-BY-SA 4.0 授權，需 Grab／貢獻者署名；程式碼 MIT 是另一件事。有 photo GET API，但本輪未確認目前認證／配額，不能直接宣布已可上線。條款／詳細 API 來自官方索引，直接頁面為 JS／錯誤。[條款](https://kartaview.org/terms)、[Photos API](https://kartaview.org/doc/photos)、[認證文件](https://kartaview.org/doc/authentication) |

這些來源補足公司、歷史成交、政策、街景；它們不提供完整即時出租庫存。上面的零資料費也不代表使用者自己的模型、網路或裝置沒有成本。

## 不能混用的授權

- **Land Registry title register／plan**：線上各 £7，official copy 各 £11，與免費 Price Paid 分開。此輪不購買；已合法持有 PDF 的使用者可選本機檔案，但其處理／公開分享權限仍需依文件判斷。普通下載副本不是 official proof of ownership。[官方說明與價格](https://www.gov.uk/get-information-about-property-and-land/search-the-register)
- **VOA Council Tax**：官方回覆拒絕 bulk list disclosure，援引法定職務及納稅資料保密；一般網頁供個別房屋及附近比較。這是 VOA 對批次揭露的立場，不能擴寫為「每次 AI 查詢均違法」；也不能把 GOV.UK 回覆文章的 OGL 當成整個地址／稅級庫授權。服務頁本輪未讀成功、公共 API 未確認。[官方回覆](https://www.gov.uk/government/publications/addresses-council-tax-bands-effective-dates/response-to-request-for-access-to-council-tax-database)
- **Find Case Law**：OJL v2 允許一般閱讀、下載、引用，須署名、用現行版本、遵守法院限制。大量程式搜尋／計算分析需另申請，申請免費；公開 API 沒有取消此條件。官方一方面把個別閱讀列為一般使用，一方面將 AI 產品列入計算分析例子，因此單案 agent 分析的邊界仍需釐清，不概括判成全面禁止或全面允許。[OJL v2](https://caselaw.nationalarchives.gov.uk/open-justice-licence/version/2)、[分析界線及免費申請](https://caselaw.nationalarchives.gov.uk/when-you-need-permission)、[API](https://nationalarchives.github.io/ds-find-caselaw-docs/public)
- **Google Street View**：Static API 需啟用計費。平台條款限制外部擷取、影像快取、衍生內容及模型改善／測試／驗證；pano ID 可長存不是照片可長存。一般 Google Maps 使用者條款另有限制，EEA 計費地址也有另外條款。可提供官方 viewer 連結供使用者查看；不能當成免費離線影像來源。單次 AI 推論不自動等於模型訓練，但其內容擷取／衍生輸出仍需審查。[平台條款 §3.2.3](https://cloud.google.com/maps-platform/terms)、[Street View policies](https://developers.google.com/maps/documentation/streetview/policies)、[計費](https://developers.google.com/maps/documentation/streetview/usage-and-billing)、[一般使用者條款](https://www.google.com/intl/en/help/terms_maps/)
- **Wayback**：Availability／CDX API 提供快照資訊，原站內容權利不因存入 Archive 而消失。可先找精確日期的連結；不能把它當成原站限制的通用替代入口、當前可租證據或公開轉貼許可。完整版現行條款只回傳 JS 提示，本輪未完整確認。[API](https://archive.org/help/wayback_api.php)、[官方權利說明](https://archivesupport.zendesk.com/hc/en-us/articles/360014759692-Rights)、[條款](https://archive.org/about/terms)

## 補充名冊：查得到不代表已有自動化授權

| 名冊 | 本輪官方證據與下一步 |
| --- | --- |
| Client Money Protect | 網站 IP 保留給 mydeposits，未找到正面 API／自動化／再利用授權。先連官方查詢；單一方案查無結果不等於不合法。[Terms](https://www.clientmoneyprotect.co.uk/terms-and-conditions/) |
| Property Redress | 官網保留版權；scheme terms of reference、會員 portal 或 logo 下載不等於資料 feed 許可。公開讀取 API／權限未知。[官網](https://www.propertyredress.co.uk/) |
| TPO | Copyright 頁面對複製、下載、保存、改作等要求事先書面許可，保留法律例外；未取得。可以連結官方查詢，不將會員事實與整頁複製混為一談。[Copyright](https://www.tpos.co.uk/copyright/) |
| Propertymark | 有 public expert-finder；未查得本輪所需 API／內容授權。Privacy policy 與會員商務文件不是再利用許可；無自願認證不等於不合法。[官網](https://www.propertymark.co.uk/)、[Privacy](https://www.propertymark.co.uk/privacy-policy.html) |
| Heat Trust | 未查得公開資料 feed／自動化授權。必須核對特定 heat network 及供應契約；業者 logo 不代表每個網路都註冊。商標另有限制。[名冊及適用範圍](https://heattrust.org/our-members) |

這五組沒有確認到公共 API，費用與 eligibility 保持未知；沒有聯絡任何單位，也沒有提交名冊查詢。提供連結是現階段可交付的入口，並不聲稱已完成免手動輸入的串接。
