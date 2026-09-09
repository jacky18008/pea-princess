# 原生代理對話消融：凍結方案

2026-09-09。使用者授權192次受控模型執行、600萬processedtokens，研究深度為mode；Claude繼續暫停。這份方案把公開skill放進合成專案，由原生Codex讀檔、使用腳本、保存結果。與純聊天lab的七次UX實測分開。

## 固定矩陣與交付

四組指引：既有入口＋預載文件、既有入口＋按需讀檔、短入口＋預載文件、短入口＋按需讀檔。前者沿用正式skill；候選入口在`evals/conversation-quality/skill-outcome.md`，尚不自動替換正式版本。兩個因子完整交叉，入口修改包含去重與減少固定程序，不能再把這兩者拆開歸因。

各組交叉Astra／Luna、low／high、lite／standard／deep，共48個session。每格先跑同一合成使用者的三輪對話，共144次回答；其中兩模型、low、standard的基準組與完整候選組，各再延伸六輪，共24次。最後24次匿名成對評分，總計192次。四段長對話各有9則使用者訊息和9則回答；其餘為3＋3。每格只有一個情境，沒有獨立重複，不能宣稱品質等效或通用相容性。

預載組額外把`inputs.md`及`onboarding.md`全文放入prompt；路由組的相同檔案留在可讀skill目錄。兩組都能使用相同的工具和資料。所有組別的模型、effort與工具能力由共同runner固定，舊文件不能授權換模型、額外子代理或網路存取。深度只改查核範圍；不代表低深度就沒有shell，也不代表深度高就應該對使用者說得更長。

## 案例與資料釋出

案例包含具體候選比較、預算降低、安靜／交通優先順序、面積必要條件、無完全符合房源時的下一步、只對一間生效的地面層例外、插問、來源更正、房東估計與實測通勤、只放寬通勤上限，以及最終可恢復檔案。

第二、七輪有依前則回答長度或問號數觸發的固定反應。這只是可重現的模擬器分支，不是語意判斷、人類滿意度或真實對話自然度。資料、語句、固定反應與成功條件都在凍結scenario；只有已釋出的文件和訊息會交給回答者，未來訊息與評分gold放在外部控制器。

第六輪只把新訊息放入prompt，先前完整對話仍在`conversation.json`；agent須從保存的資料接續。這是檔案恢復測試，不是假稱真的操作Codex原生compaction。模型每次為新的nativeinvocation；前面的全部資料保持可讀。

## 版本、完整性與用量

`prepare`只建檔，不呼叫模型，保存sourcecommit、來源SHA、公共ZIP、場景、rubric、排程、匿名映射、每個專案的初始內容。不能覆寫舊run。`next`／`answers`／`judges`才實際執行。每次先保存request，再由共用CallControl寫入dispatch，最後保留完整終端、工具事件、回答、檔案快照及直接用量。

已完成呼叫從收據恢復，不重新執行。未完成／失敗／未知用量停止後續dispatch。歷史、原始證據或skill被變更會停止；來源更新只能由預定scenario釋出。單次原生執行最多240秒；最後一次可能超過600萬停止門檻，因為只能在兩次執行間檢查。192的單位是CLI／agent執行，內部provider請求次數無獨立觀測時為null，不能改稱192次API請求。

input已包含cachedinput；processedtotal=input+output。失敗的已知用量仍計入，未知不是零。24次標準化評審包含於相同ledger；主代理、協作編碼與評估子代理本身的對話用量無相同token收據，另列不可觀測，不併入此表冒稱完整帳單。

這是一般合成行為測試。workspace-write與提示中的工作目錄限制不構成對同一帳號資料的敵對隔離；沒有測試讀取真實密碼或信用卡。評審gold未複製到回答者目錄，工具紀錄可檢查實際讀取；不宣稱作業系統阻止所有越界讀取。

## 評分與過程複核

獨立GPT-6 Astra子代理操作24次Astra／low匿名成對評審，再閱讀原始對話、工具與評分依據；root另做流程review。共同前三輪與延伸對話分開評，不能拿9輪的成果贏3輪的對話。候選名稱、模型、組別、成本與可識別路徑從評審副本移除；原始bytes保留，匿名映射到評分完成後才用於分析。說話風格或模型自己寫入的內容仍可能讓評審推測組別，匿名不是完全保證。

匿名配對為既有預載↔短入口路由、既有路由↔短入口預載；兩個長對話配對因此都具有延伸。單因子差異由同model/effort/depth/另一因子的對應格分數計算，部分對比跨不同評審配對；這個評審上下文差異需保留在報告。

評分14個面向與3個不可被文筆抵銷的門檻，見[評估設計](conversation-evaluation-design.md)。root複核格式、未知／不可評處理、引文與訊息ID、原始產出存在、估計與觀察、使用者更新的範圍，以及正確但難用、好聽但錯誤這兩種反例。實際可讀檔案會提供給評審，不只把agent的「已寫入」當成證據。

不把這批用來修改入口的情境稱為held-out。除了完整結果與失敗，還要交付：按model/effort/depth拆分的品質與成本、相同條件下的消融差異、來源／輸出／工具使用診斷、盲評失敗與分歧、尚未驗證的部署範圍。只有證據支持時才採用候選；沒有通過的格子保留失敗，不合併成「全部workable」。

## 操作

```sh
python3 bench/conversation_ablation.py prepare --output .pea-playground/conversation-ablation-20260909-v1
python3 bench/conversation_ablation.py answers --output .pea-playground/conversation-ablation-20260909-v1
python3 bench/conversation_ablation.py status --output .pea-playground/conversation-ablation-20260909-v1
```

`judges`由獨立評估子代理執行；其執行命令不會把成本／組別提供給native評審。分析只能在評分後讀映射。中斷後先用status核對pending／failed與原始終端，再處理本機收據恢復，不能為了填滿矩陣自動重試。
