# AI 找房通路、曝光與 Zoopla 查核補正

補查日期：2026-09-11。更正初版 commit `543663e` 遺漏的官方 AI 分發入口。這不是爬取授權或實際整合驗收；沒有啟用App、登入帳號、取得房源或聯絡平台。

## 補正：Zoopla 已宣布官方 ChatGPT App

Zoopla 於2026-04-24宣布與OpenAI合作，並稱已將所有房源接入自己的ChatGPT App，目的是讓房源觸及新受眾。初版只查網站條款、廣告商API與提醒信件，**漏掉這個由平台提供的AI搜尋入口**，因此免貼資料的可行通路描述不完整。[Zoopla官方公告](https://business.zoopla.co.uk/zoopla-signs-enterprise-agreement-with-open-ai)、[官方新聞稿](https://www.zoopla.co.uk/press/releases/zoopla-signs-enterprise-agreement-with-openai-investing-in-ai-to-drive-higher-lead-quality-and-customer-roi/)。

官方App目錄的搜尋索引描述包含英國買屋及租屋；本輪直接開啟目錄URL則跳回一般plugins頁，因此**沒有確認本使用者帳號目前能啟用或順利搜尋**。索引內容不是即時可用性測試。[App目錄紀錄](https://chatgpt.com/apps/zoopla/asdk_app_694547c513008191a7b8f44c95fb14c3?locale=pt-BR)。

這是指定host內、由供應商經營的通路；公告並未授予任意爬蟲、第三方公開API、Codex存取、永久保存或跨模型再利用權利。原網站的自動化條款仍需分開看。Pea若要使用此通路，還須確認host支援、資料可見範圍及能否接續政府資料分析。[Zoopla網站條款](https://www.zoopla.co.uk/terms/)。

## 曝光比較的正確範圍

下列是商業機制推論，不是實測結果：若使用者將搜尋交給外部AI，且其他條件相近、只有Zoopla能供該agent讀取，那麼Zoopla房源進入候選清單的機會更高。這可以形成刊登者的誘因，尤其對較少人主動造訪的平台。

但需要分開衡量：

| 指標 | 問題 |
|---|---|
| 房源曝光 | 是否進入agent候選清單、是否真正展示給使用者？一次bot抓取不等於一次人類觀看。 |
| 平台收益 | 詢問、看房和後續交易是否回到平台或其客戶？網頁點擊可能下降，但有效詢問可以上升。 |
| 房東／仲介收益 | 是否新增合格租客及縮短空置？同一戶多站刊登，可能只是詢問渠道轉移。 |
| 使用者結果 | 是否找到合條件的真實房源、少花時間，還是因來源不全漏掉更好的房子？ |

開放程度本身不決定整體勝負：獨家庫存、原有直接流量、房源更新、資料品質、agent使用率與平台內AI能力都影響結果。Rightmove已公布以Gemini為基礎的站內對話搜尋。它的存在支持「平台可以自己提供AI體驗」這項選擇；不能從拒絕一般爬蟲推論它完全沒有AI入口。[Rightmove官方公告](https://www.rightmove.co.uk/press-centre/rightmove-launches-next-phase-of-ai-powered-property-search/)。

平台也可以用指定合作通路取得新曝光，同時保留資料與聯絡流程的控制。Zillow公開描述其ChatGPT App如何保留broker/MLS歸屬，並讓看房和聯絡回到Zillow，且對資料留存／再利用施加限制。這是另一種實際通路設計，不是全面開放抓取。[Zillow官方說明](https://www.zillow.com/news/how-zillows-app-in-chatgpt-expands-listing-reach-and-protects-industry-rules/)。

## 不可誤用的效果數字

Zoopla公告的80%房源瀏覽增加、150%詢問增加，指其自身App內AI搜尋使用者的早期測試。不是ChatGPT入口的增量成效、與Rightmove的對照，也沒有披露足以支持因果結論的樣本／隨機化方法。本報告不用這兩個數字估算Pea會增加多少曝光。[原始統計語境](https://business.zoopla.co.uk/zoopla-signs-enterprise-agreement-with-open-ai)。

## 後續評估方式

若要實測，先以有權使用的相同房源集合、相同時段與使用者需求固定比較，按房源身份去重；分別報告進入候選率、實際展示率、有效詢問／看房、任務成功與使用者時間。真實發布／轉換實驗需平台或仲介資料及對應授權。禁止來源的讀取不應成為對照組必要操作；離線可用缺失來源的情境測試agent，結果只能稱為覆蓋敏感度。

對Pea的下一步是優先確認「使用者選用的平台官方AI App能否接續我們的核對流程」，並保留可跨host的API／授權feed路線。開放程度只影響可取得的候選集合，不能讓agent把「容易取得」混充為「更適合使用者」。

## 複核與紀錄

Root及獨立子agent核對Zoopla兩份官方公告，並區分App目錄索引與實際帳號可用性；確認成效數字的原測試語境。已補README、portals閱讀版及JSON，初版仍保留在Git歷史和私人來源快照。這次提問原文另存私人會話狀態，用於後續continuous-conversation檢閱。
