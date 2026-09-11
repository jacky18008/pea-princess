# Pea Princess 資料來源授權查核

查核日期：**2026-09-11**。產品前提：永久免費的本機 skill，由使用者自己的 agent 執行。目標包含找出真實房源、比較選項，以及自動補 EPC、施工、環境、通勤和統計背景；手動貼文只能是可選入口。

**政府與開放資料已有可接的正式路線；跨 Rightmove、Airbnb 等網站完整自動代看的授權仍有缺口。** 本輪沒有確認任何一個能零設定、零授權費、完整覆蓋所有平台的通用入口。這是對查到的文件和接口的判斷，不代表免費 skill 本身違法，也不是法院對條款效力的判定。

**同日補正：** 初版漏查 Zoopla 已宣布的官方 ChatGPT App；這是指定AI平台的房源入口，與開放任意爬蟲不同。本使用者帳號可用性及跨host處理範圍尚未驗證。詳見 [AI通路與曝光補充報告](ai-distribution-addendum.md)。

## 逐站文件

| 分組 | 查核範圍 | 完整紀錄 |
|---|---|---|
| 房源平台 | Rightmove、Zoopla、OnTheMarket、OpenRent、SpareRoom | [閱讀版](portals.md) · [JSON](portals.json) |
| 仲介與出租業者 | Foxtons、Savills、Knight Frank、Dexters、Chestertons、JLL、Grainger、Get Living、Fizzy Living | [閱讀版](agents-operators.md) · [JSON](agents-operators.json) |
| 短住與評論 | Airbnb、Booking.com、Expedia、Premier Inn、Travelodge、HomeViews、Trustpilot、Google Maps/Places | [閱讀版](shortstay-reviews.md) · [JSON](shortstay-reviews.json) |
| 核心政府／開放資料 | EPC、Postcodes.io、Police、TfL、MHCLG Planning、GLA、PlanIt、borough portals、Street Manager、OSM、Defra noise、London Air、EA flood、ONS/Nomis、GOV.UK、legislation、GLA checker | [閱讀版](government-open-data.md) · [JSON](government-open-data.json) |
| 其他現有來源 | 公司／土地／稅帶／判決／街景／存檔／會員登記 | [閱讀版](supplemental-public-data.md) · [JSON](supplemental-public-data.json) |

[來源對照表](source-coverage.json) 將現行 `sources.yaml` 每一個 ID 對到查核紀錄；[registry.json](registry.json) 提供所有紀錄的索引。**有對照紀錄不代表已取得授權**：例如 borough 是多站佔位符，本輪未逐一核完所有地方政府；Savills 等有讀取失敗；不確定項目保持不確定。範圍也不是所有英國仲介、出租業者或住宿品牌。

## Rightmove 的房源怎麼辦

Rightmove 的現行 §5.2、§5.5 對自動讀取和非直接人工互動有明確限制；§8、§13 對保存、資產與軟體連結另有限制。使用者登入、免費使用、瀏覽器操作或限制三戶都不會自動取得例外。公開找到的 ADF 文件是廣告商把自己的房源傳進去，不是讓租客搜尋全站的讀取 API。[使用條款](https://www.rightmove.co.uk/c/terms-of-use/)、[ADF](https://www.rightmove.co.uk/adf.html)。

可以評估四條路，但不能把它們寫成已完成的授權：

1. **同一房源的原仲介／業者來源。** 若該來源允許所需操作，可直接取得事實並比較，使用者不必貼 Rightmove。須獨立發現或從有權處理的資料得知來源，不能先違反入口限制讀取 Rightmove 再稱為替代。不是所有房源都有另一個來源，照片和文案也可能仍是第三方權利。
2. **取得平台或資料供應商的明確讀取授權。** 必須覆蓋本機分散安裝、使用者自己的雲端模型、必要快取、比較報告及可用連結。是否接納免費個人專案、是否收費，本輪未確認；不能用第三方「能抓」的 API 廣告代替授權鏈證據。
3. **官方房源提醒進入使用者授權的信件資料夾。** 技術上能省去貼文；但本輪找到的提醒說明只確認產品功能，沒有確認外部 agent 的擷取／保存範圍。這是待確認的整合候選，不是已解決的法律捷徑。[Rightmove 提醒](https://faq.rightmove.co.uk/support/solutions/articles/7000048758-how-to-register-for-property-alerts)。
4. **使用者自選原站閱讀／提供文件。** 保留給喜歡這樣操作的人；這不滿足完整代看，不應成為產品唯一流程。單純提供檔案也不會自動解決後续任意複製和再發布的權利。

對於要求「完全不想自己看」的使用者，如果沒有該站適用的授權，就應明講本次只搜尋已支援來源、可能漏掉哪些市場；不能用虛構房源、舊資料或搜尋摘要填滿數量。

## 最有用的新發現

| 項目 | 查到什麼 | 對產品的影響 |
|---|---|---|
| OnTheMarket | §3.3 有 Permitted Program 例外，要求唯一 User-Agent 身分及完全遵守 robots；§2.2 的保存、§3.4–3.5 連結限制仍在。 | 值得先做範圍評估；不能說只加一個 header 就獲得完整自動比較權利。[條款](https://www.onthemarket.com/terms/) |
| Booking.com | A15.2 明文包含非商業用途及使用者瀏覽器中的 AI 助手；Demand API 要合作資格。 | 個人訂閱／本機 agent 不自帶例外；合作 search-and-redirect 是另一路線。[條款](https://www.booking.com/content/terms.en-gb.html)、[資格](https://developers.booking.com/demand/docs/getting-started/prerequisites) |
| Airbnb | 消費者條款限制自動擷取；Host Services API 有批准與用途範圍。 | 房東同步庫存與訪客搜全站是不同能力。[UK 條款](https://www.airbnb.co.uk/help/article/2908)、[API](https://www.airbnb.com/help/article/3418) |
| EPC | 新版正式 API 已存在，One Login 可取得 bearer token；非地址欄位與地址欄位授權不同。 | 可以自動做能源核對；不能把 EPC 地址庫直接變成一般房源底庫。[API](https://get-energy-performance-data.communities.gov.uk/guidance/energy-certificate-data-apis)、[授權](https://get-energy-performance-data.communities.gov.uk/guidance/licensing-restrictions) |
| 施工與噪音 | 規劃資料不等於實際開工；Street Manager 有道路工程事件；現行 agglomerations 資料是範圍邊界。 | 要分「申請／已准／開工／道路工程」，不能用城市邊界假裝噪音測量。[Planning](https://www.planning.data.gov.uk/docs)、[Roadworks](https://www.gov.uk/guidance/find-and-use-roadworks-data)、[Noise metadata](https://environment.data.gov.uk/dataset/c4bc5ebd-eab8-4b8a-be54-83d2f7132059) |
| 空污 | London Air 現行頁指OGL，但API仍有舊版限制更嚴的條款PDF。 | 版本衝突待釐清，成功fetch不代表問題消失。[现行說明](https://www.londonair.org.uk/Londonair/API/)、[舊條款](https://api.erg.ic.ac.uk/AirQuality/Information/Terms/pdf) |

## 實作方向與驗收

詳見 [implementation-plan.md](implementation-plan.md)。建議先做兩件事：**把政府資料接入可靠的候選核對；解決第一個可持續自動取得真實房源的來源授權。** 前者已有多條清晰路線，後者是跨站省時功能目前真正的產品缺口。

使用者仍可選自己的 agent 與模型，不需要我們營運中央模型或遠端 worker。但資料服務可能要求個人 key、配額或付費；免費 skill 不能替這些服務承諾永遠免費。本輪核對的 overpass-api.de 公共主機也不適合被所有安裝者共同當作無限免費後端；Street Manager 的事件訂閱需要可被存取的接收端，因此不適合作為零設定純本機必備依賴。[Overpass 使用指引](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)、[Street Manager 訂閱](https://department-for-transport-streetmanager.github.io/street-manager-docs/open-data/)。

## 方法及限制

按來源拆開搜尋／存取、使用者指定的 AI 瀏覽、保存與再利用、圖片／評論展示、API方向、資格、費用與來源日期。優先官方條款與開發文件；部分採官方搜尋索引文字，讀取失敗有保留。沒有以 robots 空白、沒有寫AI、公開可見、API可回200或別人都在抓當成許可。

本輪查核人員交叉複核關鍵結論，並提供 JSON 和 inventory 完整對照。沒有建立帳號、簽協議、聯絡業者、購買資料、登入API或抓取新房源；沒有重跑模型品質實驗。官方網頁可能改版，本地保存的是有日期的查核紀錄、必要短摘述及URL，不是完整不可變的條款原頁存檔。檔案雜湊只證明本次報告版本。

「未確認完整 AI 工作流程授權」不是指分析任何事實都必須先取得AI專用許可。必須逐一檢查實際取用／複製行為、合約、法定例外及第三方權利；本報告採可追溯的產品接入判斷。法律層次另見 [UK/EU 背景分析](../legal/scraping-terms-uk-eu-2026-09-11.md)。本輪**尚未修改 runtime、來源政策或抓取器**，已發現需修正的地方列在實作清單，不能把這份查核當作上線驗收通過。
