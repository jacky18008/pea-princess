# 「禁止自動爬蟲」在英國與歐盟到底有多大拘束力

2026-09-11。回答的問題：Rightmove、Zoopla 這類網站寫「禁止自動抓取」，如果我照抓，會有法律責任嗎？

**結論：那句話本身不是法律，但它會啟動三種真的有拘束力的機制。個人少量抓取自己要看的頁面，實際風險接近零；做成公開工具替所有使用者自動抓，風險是真的。這也是豌豆公主「請使用者自己貼頁面、不自動抓這些站」的理由。**

證據標示：■ 法條或判決（一手來源）；● 觀察到的執法實務（未定案）。

| 機制 | 英國 | 歐盟 | 對你的意義 |
|---|---|---|---|
| **契約**（網站條款） | Rightmove 條款 2.2「使用即接受」、5.2 禁止 bots／crawlers／scrapers、5.5 只准「人工直接操作介面」取得資料、6.5 可封鎖並採法律行動；準據法英格蘭■ | 歐盟法院 *Ryanair v PR Aviation*（C-30/14，2015）■：即使資料庫不受著作權或資料庫權保護，網站仍可用條款禁止爬取，且該禁止可執行；英國脫歐後此判決屬保留的歐盟判例，仍有說服力 | 違反是**民事**：封鎖、終止帳號、求償。個人使用幾乎沒有可證明的損害；商業或大量使用才會被追 |
| **資料庫權**（sui generis right） | 1997 年《著作權及資料庫權利規則》承襲歐盟指令 96/9■ | 指令 96/9 第 7 條■ | 只有「系統性抽取或再利用實質部分」才侵權。貼一戶給助理看不算；寫工具替大家批量抓整站就算 |
| **著作權與文字資料探勘（TDM）例外** | CDPA 1988 s.29A：只限**非商業研究**、須**合法存取**、契約不得排除■。2024 年 12 月諮詢提出的「可 opt-out 的一般 TDM 例外」已在 2026 年 1–3 月被政府放棄，維持現狀■ | DSM 指令 2019/790 第 4 條：任何人（含商業）可做 TDM，**但權利人以機器可讀方式（robots.txt、條款）明示保留權利後，例外失效**■；第 3 條研究機構例外不能被排除■；AI Act 第 53 條要求通用 AI 模型供應商遵守這種保留■ | 在歐盟，網站把「不要爬」寫成機器可讀，**法律上真的有效**：它拿掉你的豁免，回到要授權。英國商業用途本來就沒有豁免；個人非商業研究才有 s.29A，而「合法存取」是否包含違反條款取得的頁面，尚無判決 |
| **刑事**（Computer Misuse Act 1990 s.1） | 公開頁面一般不構成「未經授權存取」；繞過登入、付費牆、反爬或速率限制才有刑事風險■ | 各國有類似的電腦犯罪條文 | 不破解、不繞封鎖，就不是刑事問題 |
| **個資**（UK GDPR／GDPR） | 廣告裡仲介的姓名、電話是個資；純個人家用豁免，公開工具不豁免■ | 同 | 工具若儲存仲介聯絡資料，需有合法基礎與告知 |

## 執法實務

- 我查不到英國法院對 Rightmove 或 Zoopla 爬蟲的判決；看得到的是封鎖 IP、終止帳號與律師函●。
- Rightmove 條款 5.5 的「只准人工直接操作」意味著：使用者自己開頁面、複製貼給助理，是條款允許的行為；助理替使用者自動開頁面抓，就不是。

## 對豌豆公主的設計含意

1. 維持「使用者貼頁面」：責任留在使用者自己的瀏覽行為，且不觸及資料庫權的「系統性抽取」。
2. 公開發布時在文件寫明：對 Rightmove、Zoopla、OnTheMarket、OpenRent、HomeViews、Trustpilot、Google 評論、Airbnb、Booking.com 只列名、不提供抓取方法（`references/sources.yaml` 已如此標示）。
3. 若日後想自動取得房源資料，正途是官方 API 或授權資料商，不是繞過條款。

## 來源

- [CDPA 1988 s.29A](https://www.legislation.gov.uk/ukpga/1988/48/section/29A)
- [Reed Smith：Text and data mining in UK](https://www.reedsmith.com/articles/text-and-data-mining-in-uk/)
- [Lewis Silkin：UK government rethinks its position on copyright and AI（2026-03-24）](https://www.lewissilkin.com/en/insights/2026/03/24/opt-out-cop-out-uk-government-rethinks-its-position-on-copyright-and-ai-102mnx9)
- [Kluwer Copyright Blog：DSM Directive Articles 3 and 4](https://legalblogs.wolterskluwer.com/copyright-blog/the-new-copyright-directive-text-and-data-mining-articles-3-and-4/)
- [Norton Rose Fulbright：Hamburg court on machine-readable opt-outs（2025-12）](https://www.insidetechlaw.com/blog/2025/12/machine-readable-opt-outs-and-ai-training-hamburg-court-clarifies-copyright-exceptions)
- [Gowling WLG：Ryanair v PR Aviation](https://gowlingwlg.com/en/insights-resources/articles/2015/ryanair-flying-high-at-the-cjeu)
- [Rightmove Terms of Use](https://www.rightmove.co.uk/c/terms-of-use/)
- [Sprintlaw：Is web scraping legal in the UK?](https://sprintlaw.co.uk/articles/is-web-scraping-legal-in-the-uk/)
- [EU AI Act Article 53](https://casrai.org/dictionary/term/eu-ai-act-article-53-general-purpose-ai-model-obligations)
