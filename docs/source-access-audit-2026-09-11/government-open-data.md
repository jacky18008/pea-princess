# 政府與開放資料：逐來源查核

核對日期：2026-09-11。這是官方文件查核及工程建議，沒有開帳號、取得新授權或試抓房源。狀態按操作區分；未列價不等於保證免費。資料授權不等於公共主機提供無限免費資源。

完整欄位見 [government-open-data.json](government-open-data.json)。新候選尚未接入 runtime。

## MHCLG EPC / Get energy performance data

狀態：`official_api_with_registration`。

**取得方式：** 新版正式 API 可搜尋及取得證書；GOV.UK One Login 後取得 bearer token。舊 Find 網域的一條 /api/domestic/ 回傳404，不能推論整個 EPC 服務沒有 API。

**保存與再利用：** 非地址欄位（包含 UPRN）為 OGL v3；地址及郵遞區號受 OS/Royal Mail 用途限制。租售市場了解能源效率是列明目的之一；拿地址另建一般房源、收入或周邊情報資料庫不能直接套用。分享地址須附其 copyright/database notice。 該公告亦保留符合條件的非商業研究／私人研習等法定例外。通用地址資料庫超出列明目的屬本報告的用途判斷，不是排除所有法定例外的法律結論。

**資格與費用：** 開發者可建立自己的 One Login；未確認另收 API 費用，不能把無列價寫成保證永遠免費。

**本機與模型處理：** 分開標記地址與 OGL 欄位；地址層級能源資料可能是個資。使用者自己的 agent 若呼叫雲端模型仍可能傳出本機；依目的與適用條款最小化送出欄位。

**服務限制：** 官方標準6000 requests/5minutes/originating IP；共用網路合計，429後退避。這是服務上限，非建議用量。

**資料含義：** 證書可能已過期、被取代或不是該戶；先核對 UPRN/地址/證書日期。EPC 不是即時空房清單。

**後續工作：** P1：新增正式 API adapter，個人憑證留本機；明確區分能源核對及通用地理 join 的地址來源。

官方依據：[How to get started / Conditions of use](https://get-energy-performance-data.communities.gov.uk/guidance/energy-certificate-data-apis)；[Non-Address Data / OS and Royal Mail notice](https://get-energy-performance-data.communities.gov.uk/guidance/licensing-restrictions)；[Registration / Data Protection Act](https://get-energy-performance-data.communities.gov.uk/guidance/data-protection-requirements)；[API specifications / Rate limiting](https://get-energy-performance-data.communities.gov.uk/api-technical-documentation)。

## Postcodes.io

狀態：`documented_public_api`。

**取得方式：** 官方提供免費郵遞區號 lookup、nearest 等 API，可省去人工找座標；不是政府營運服務。

**保存與再利用：** 程式碼 MIT 不等於資料 MIT：Great Britain 資料是 OS OpenData；BT 郵區另受 ONSPD/NI 條件。保留 OS、Royal Mail、ONS、NRS 歸屬。

**資格與費用：** 公開免費服務；高需求的 Ideal Postcodes 是另項產品。

**服務限制：** 本輪未確認託管服務精確配額或 SLA；低量、快取、退避，不把開源授權當無限免費運算。

**資料含義：** 郵區中心不等於建築物或公寓座標。

**後續工作：** 沿用公開 API，補齊資料歸屬與區域授權標記。

官方依據：[API / free tool](https://postcodes.io/)；[Licences](https://postcodes.io/docs/licences/)。

## data.police.uk

狀態：`documented_public_api`。

**取得方式：** 官方 JSON API 及每月 CSV/bulk download，適合自動查詢區域犯罪統計。

**保存與再利用：** 明示 OGL v3，保留來源、資料月份和匿名化的地點語義。

**資格與費用：** 公开資料 API，不需把查詢移到商業網站。未見逐次收費。

**服務限制：** API 平均低於15 requests/second，允許短暫30；超限429。

**資料含義：** 匿名化地點、資料延迟及通報差異；不能宣稱某一戶發生某犯罪或零結果等於安全。

**後續工作：** 保留每月快取，勿逐輪重查相同區域。

官方依據：[Licence / data downloads](https://data.police.uk/about/)；[API call limits](https://data.police.uk/docs/api-call-limits/)。

## TfL Unified API / Transport Data Service

狀態：`licensed_api_with_registration`。

**取得方式：** 正式 Transport Data Service 提供通勤、站點、營運狀態；依服務註冊及 API portal 的實際金鑰配額。

**保存與再利用：** 採修改版 OGL v2，非通用 OGL v3。可建立應用及再利用授權資料；須 Powered by TfL Open Data 與適用第三方歸屬。

**資格與費用：** 條款稱免費資料服務；註冊條款適用。

**服務限制：** 資料授權寫500calls/min/feed；API帳號實際配額可能另有限制。禁止把此授權擴至 Oyster、Congestion Charge、Santander Cycles 網站的自動擷取。

**資料含義：** 出發日期、時間與交通異常必須保留；旅程估計不是通勤保證。

**後續工作：** 保留使用者自己的API設定；只查候選所需路線。

官方依據：[Licence / limitations / attribution](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service)；[API portal](https://api-portal.tfl.gov.uk/)。

## MHCLG Planning Data（新增候選）

狀態：`documented_public_api`。

**取得方式：** 正式 API 可依座標、UPRN、dataset 查詢，並提供 CSV/JSON/GeoJSON/Parquet 批次檔。

**保存與再利用：** 多數內容 OGL；個別 dataset、第三方著作/圖資及連出去的原站仍需分開確認。

**資格與費用：** 公開開發者文件；未見本輪列價或必要帳號。

**服務限制：** 官方要求 polite rate limiting；大量物件建議下載資料本機運算。服務 beta。

**資料含義：** 規劃申請資料規格仍在開發，地方政府未被要求全數按此格式供應；無結果不等於無限制或無工程。

**後續工作：** P1：作為區域限制等開放資料優先入口，保留資料集覆蓋率及日期。

官方依據：[Getting started / Monitoring applications / Downloading data](https://www.planning.data.gov.uk/docs)；[Using the service / third-party links](https://www.planning.data.gov.uk/terms-and-conditions)。

## Planning London Datahub / London Datastore

狀態：`documented_guest_api_reuse_conditions`。

**取得方式：** GLA 官方文件公開 guest read API，另有 Datahub CSV 匯出；無需把使用者導向每個 borough 手動貼資料。

**保存與再利用：** London Datastore 條款允許資料再利用及建立軟體，要求說明GLA不保證品質/正確性。不可據此假設所有外連附件、OS底圖或不同主機全文皆有同一授權；新舊Datahub主機適用關係須在adapter固定。

**資格與費用：** 官方guest讀取文件；未見個別API使用費。

**服務限制：** 精確目前配額未確認；不要把公開guest設定當私人secret或自行探索寫入API。

**資料含義：** 資料由申請人/LPA供應，可能未即時完成品質檢查；批准不等於已開工，開工不等於每天施工時間。

**後續工作：** 保留應用編號、來源LPA、階段與時間；按主機/資料欄位核對授權。

官方依據：[Guest API connection](https://www.london.gov.uk/sites/default/files/planninglondondatahub_api_connection_technical_documentation_v1.pdf)；[You / data re-use](https://data.london.gov.uk/about/terms-and-conditions)；[Data quality / export CSV / OS notice](https://planninglondondatahub.london.gov.uk/)；[Dataset record](https://data.london.gov.uk/dataset/planning-london-datahub-applications-236qk)。

## PlanIt UK

狀態：`documented_api_reuse_scope_partial`。

**取得方式：** 站方明文提供規劃申請JSON/CSV等API、地理查詢及pagination；這比自行猜內部endpoint有明確依據。

**保存與再利用：** Acknowledgements 分別說明郵區/邊界授權；沒有確認一份覆蓋全部申請欄位的通用OGL。原地方政府圖則/圖紙僅限所列consultation等用途，額外複製須權利人同意。

**資格與費用：** 公開API、站方稱協助維持免費；具體商業/高量方案及完整再利用授權未確認。

**服務限制：** 每請求5000筆/1000kB上限不是建議值；小頁、429/Retry-After退避，403停止確認原因。

**資料含義：** 聚合器覆蓋、stale/inactive LPA、分頁皆需保留。

**後續工作：** 只用已文件化查詢；在建立持久整合資料庫前釐清欄位授權。

官方依據：[API / Results Format and Limitations](https://www.planit.org.uk/api/)；[Postcodes / Boundaries / Documents](https://www.planit.org.uk/acknowledgements/)。

## 各 borough planning / committee portals

狀態：`authority_specific_unverified`。

**取得方式：** 現行sources.yaml這兩項是多站佔位符，沒有單一授權。本輪未逐一讀完所有borough條款。

**保存與再利用：** 公開查閱義務不等於申請人/建築師圖紙可任意再發布；議會自製文字與第三方附件分開。

**資格與費用：** 依地方政府及託管供應商而異。

**服務限制：** 先用已授權GLA/MHCLG資料定位，個別缺口再驗證該borough入口。

**資料含義：** 規劃案≠全部噪音來源；鄰戶裝修或臨時施工可能無紀錄。

**後續工作：** P2：按實際倫敦搜尋覆蓋需求逐個borough擴充，未核對者不繼承別站許可。

官方依據：[Linking from planning.data.gov.uk](https://www.planning.data.gov.uk/terms-and-conditions)；[Documents](https://www.planit.org.uk/acknowledgements/)。

## DfT Street Manager roadworks（新增候選）

狀態：`registered_open_data_subscription`。

**取得方式：** 官方 open-data feed 提供道路/管線工程 permits、開工停工等事件。不是只提供給道路機關寫資料的API。

**保存與再利用：** 官方說明公開資料子集供data customers使用，open-data API另有再利用路徑；不可把內部登入系統所有資料當同一開放範圍。接入前仍須接受適用Open Data條款。

**資格與費用：** 需要登記姓名/組織/聯絡方式及接收endpoint；一般道路管理用戶費率不能套算成open-data消費者費率。本輪未確認完整subscriber費用。

**服務限制：** 現有Open Data文件要求可供AWS SNS存取的POST endpoint，驗topic及message signature；不是零設定純本機pull。

**資料含義：** 道路工程更貼近實際日期，但不包含所有建築工地；proposed/actual及撤銷事件必須區分。

**後續工作：** P2：先評估官方歷史下載或使用者已選的授權供應商；不為此默默新增Pea自營遠端worker。

官方依據：[Roadworks service API](https://www.gov.uk/guidance/find-and-use-roadworks-data)；[Registration / messages / timing](https://department-for-transport-streetmanager.github.io/street-manager-docs/open-data/)；[Data sharing / Linking via APIs](https://department-for-transport-streetmanager.github.io/street-manager-docs/terms)。

## OpenStreetMap / Overpass

狀態：`open_data_host_service_limits`。

**取得方式：** OSM資料ODbL，可透過文件化Overpass查詢。資料開放不等於公共主機可當大眾產品免費後端。

**保存與再利用：** 保留OSM contributors歸屬、ODbL資訊；公開衍生資料庫的share-alike另行評估。不要誤稱所有分析程式都必須ODbL。

**資格與費用：** 資料免授權費；託管/自架成本另計。

**服務限制：** 本輪核對的overpass-api.de營運者指引反對非OSM繪圖大眾app依賴其後端，約10000次/日、1GB/日只是大致公平使用指引，不是產品授權額度。 其他獨立Overpass主機須按其自身條款確認。

**資料含義：** 酒吧/鐵路等POI不存在於OSM不等於現場沒有；地圖時間與缺漏需保留。

**後續工作：** 公開交付前支援使用者自選合適endpoint或授權資料快照；免強制Pea遠端worker。

官方依據：[Licensing / Additional services](https://www.openstreetmap.org/copyright)；[Magnitudes / quotas](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)。

## Defra strategic noise datasets

狀態：`licensed_download_and_ogc_services`。

**取得方式：** 兩個既有dataset均明列OGL，可使用其官方下載/WMS/WCS或WFS服務，不需爬地圖畫面。

**保存與再利用：** 各資料集歸屬不同：Road Round4為Defra2023；Agglomerations Round2為Crown copyright。

**資格與費用：** 無public access constraints/OGL資料；未見列價。

**服務限制：** 取所需地區及指標；服務quota未核實。

**資料含義：** 重要更正：c4bc…是Round2城市範圍邊界，不是該區每戶噪音數值！Road Round4是2022建模、年度平均、4m高度，非即時室內分貝。

**後續工作：** P1：修正來源語義與報告標籤，絕不能以agglomeration邊界推論安靜程度。

官方依據：[Road Noise Round4 / Licence / methodology](https://environment.data.gov.uk/dataset/562c9d56-7c2d-4d42-83bb-578d6e97a517)；[END Noise Mapping Agglomerations Round2 / Licence; official indexed text used after timeout](https://environment.data.gov.uk/dataset/c4bc5ebd-eab8-4b8a-be54-83d2f7132059)。

## London Air / Imperial ERG API

狀態：`conflicting_official_terms_unresolved`。

**取得方式：** 現行London Air data-feeds頁鼓勵API應用並指向OGL；同一API仍提供舊King's College terms v1.1 PDF。

**保存與再利用：** 舊PDF含單一fixed IP、不可向第三方提供API資料、public app告知/歸屬等限制，與現行OGL說明不一致。本輪不能自行宣稱已被取代。

**資格與費用：** 現行頁稱open feeds，舊授權稱royalty-free；不代表所有限制解除。

**服務限制：** 發布或雲端AI傳送前須解決適用版本；可另評估Defra UK-AIR等明確開放資料集，本輪未核對該替代。

**資料含義：** 監測站讀值不是特定flat室內空氣。

**後續工作：** P1：將完整自動化/再分享範圍列待釐清，不以目前成功fetch當授權證據。

官方依據：[How do you use it?](https://www.londonair.org.uk/Londonair/API/)；[Terms v1.1 clauses1–3,9,12; old institutional name retained](https://api.erg.ic.ac.uk/AirQuality/Information/Terms/pdf)。

## Environment Agency long-term flood risk

狀態：`licensed_dataset_alternative_to_web`。

**取得方式：** 新官方Flood risk postcode search tool data提供CSV並標OGL，適合本機自動初筛；不需猜公開地圖內部endpoint。

**保存與再利用：** 該postcode資料集OGL，附EA2025歸屬；不可外推為所有EA地圖、第三方底圖或Public Registers均OGL。

**資格與費用：** 公開下載；未見費用。

**服務限制：** 資料集更新週期quarterly；取metadata版本，避免每輪下載全國檔。

**資料含義：** 風險是postcode/地址周圍土地，不是建築本身，更不是未來五天天氣或一定淹水。

**後續工作：** P1：資料集查詢優於網頁抓取，適當引導官方個別風險服務。

官方依據：[Summary / Downloads / Licence; updated2026-07-10](https://www.data.gov.uk/dataset/87b9fa90-86c8-45f1-9211-9496d66b7168/flood-risk-postcode-search-tool-data)；[Access new NaFRA data](https://www.gov.uk/guidance/updates-to-national-flood-and-coastal-erosion-risk-information)。

## ONS / Nomis aggregate income and labour statistics（新增候選）

狀態：`documented_public_api`。

**取得方式：** ONS dataset API、Nomis REST提供官方統計；先選定合適ASHE/GDHI/小區income dataset及可用地域，不能假裝API每種收入都有。

**保存與再利用：** ONS/Nomis多數材料OGL，需ONS來源歸屬；第三方地圖另授權。Nomis明文不得用統計反推出特定個人、住戶或企業。

**資格與費用：** 公開資料；Nomis可有個人UID改善限額，不能公開私人key。

**服務限制：** Nomis多種下載預設25000cells，並限制併發；選欄位/地區/時間，勿每輪全量。

**資料含義：** 平均薪資、住戶可支配收入、房東要求的收入證明是不同概念；區域收入不是個人收入、治安或鄰居品質分數。

**後續工作：** P1：先用作區域背景與預算討論；不收集個別住戶收入。

官方依據：[Using ONS content](https://www.ons.gov.uk/help/terms-conditions)；[Dataset API](https://developer.ons.gov.uk/)；[Concurrent requests / data download](https://www.nomisweb.co.uk/api/v01/help)；[Reproducing ONS material / Confidentiality](https://www.nomisweb.co.uk/home/copyright.asp)。

## GOV.UK guidance / bank holidays / tribunal publication pages

狀態：`open_content_and_documented_feeds`。

**取得方式：** GOV.UK主站多數內容OGL且供feeds；bank-holidays.json是既有公開機器入口。特定交易服務仍可有額外條款。

**保存與再利用：** 租屋指南及政府自製內容按OGL引用；不能用主站頁尾一口氣授權所有外連服務或判決附件。

**資格與費用：** 公開內容；未見逐次費用。

**服務限制：** 不影響他人使用，依具體服務條款/速率。

**資料含義：** 記錄日期、適用地域及租約種類；資料授權查核不代表法律解釋已核實。Tribunal附件若涉及個資或特定再利用條件需分別檢查。

**後續工作：** 保留官方版本/來源；完整判決機器分析另看Find Case Law紀錄。

官方依據：[Services and transactions / Using GOV.UK content](https://www.gov.uk/help/terms-conditions)；[Permissions / attribution / exemptions](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)。

## The National Archives legislation.gov.uk

狀態：`documented_licensed_api`。

**取得方式：** 官方資料目錄確認REST及XML/RDF/HTML片段API，OGL；developer頁本輪直接讀取失敗，以官方目錄為證據。

**保存與再利用：** 按OGL保留來源及版本，可本機存法條片段，不能把法條翻譯/LLM推論說成官方法律意見。

**資格與費用：** 公開API；本輪未見收費。

**服務限制：** 實際服務配額未核實。

**資料含義：** 修正文本、原始制定版、生效日和未生效條款必須區分。

**後續工作：** 使用正式表述格式，保存版本時間及引用。

官方依據：[Licence / Summary; updated2026-06-24](https://www.data.gov.uk/dataset/a2416481-271a-42b2-ace8-fc247dd251be/legislation-api)。

## GLA Rogue Landlord and Agent Checker

狀態：`public_lookup_bulk_or_ai_access_unverified`。

**取得方式：** 官方public tier供租客核對；沒有確認可供本工具使用的讀取API或完整再發布授權。

**保存與再利用：** 有public/private tier及保留/移除政策，不能永久鏡像罪名和姓名。GLA Datastore另一個服務的授權不能直接套到此checker。

**資格與費用：** public lookup；API資格、費用未知。

**服務限制：** 未核對完整目前service terms；public tier之外不碰。

**資料含義：** 姓名對應、裁罰日期、public retention及撤銷狀態重要；無結果不是良好記錄保證。

**後續工作：** P2：釐清個案agent讀取和最小保存scope，無來源就標未核對。

官方依據：[Public tier / retention policies;2023document, not verified2026contract](https://www.london.gov.uk/sites/default/files/2023-02/RLAC%20Policies%20and%20Procedures%20.pdf)。
