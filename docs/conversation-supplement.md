# 正式評分後的補充對話證據

`bench/conversation_supplement.py` 是離線、唯讀的資料整理工具。它補充正式評分沒有涵蓋的觀察範圍，不執行模型、不產生分數，也不改寫原始實驗、正式評分封包或 judgment。只有已保存正式評分且通過收據驗證的匿名配對會輸出，其餘列為 deferred。

## 為什麼需要獨立的補充資料

目前凍結的正式評分輸入由 `bench/conversation_ablation.py` 的 `make_pair`／`judge_request` 建立：包含保存的最終回答、提供的工具紀錄，以及 T3／T9 的檔案快照。`bench/durable_run.py` 的工具事件整理刻意不保留 `agent_message` 或 reasoning。因此，正式分數不能直接解讀為完整原生介面的連續對話體驗。

這個工具保留原本的匿名 A／B 配對，另外整理每一個原始回合的 `agent_message` 串流事件與已保存的檔案快照。它不從目前工作目錄補造過去的快照。缺失、失敗或尚未完成本地結算的回合都有明確標記；之後的回合也保留先前缺口清單，不把它們拼成無中斷的對話。

補充評估應在正式分數凍結後另行決定、另行保存。若同一位評估者已看過正式評分，後續判斷可能受先前結論影響，不能當成新的獨立盲測。工具本身不修改分數、門檻、偏好，也不判斷哪一則訊息最先有用。

## 私人輸出與使用方式

選擇沒有 pending invocation 的穩定原始資料目錄，以及既有私人父目錄下的一個全新輸出路徑：

```sh
python3 bench/conversation_supplement.py \
  --run /absolute/private/frozen-run \
  --output /absolute/private/new-supplement \
  --pair j01
```

省略 `--pair` 會檢查所有原始匿名配對；可重複指定不同配對。沒有覆寫選項，輸出不能位於原始實驗目錄內。工具拒絕 symlink、父路徑穿越、非一般檔案、未結束呼叫，以及讀取期間變動的輸入。它不取得實驗寫入鎖；操作者應在穩定邊界或另存的靜態副本執行。前後雜湊檢查會拒絕觀察到的變動，並非對惡意同帳號寫入者的隔離保證。

輸出目錄結構：

| 路徑 | 用途與可見範圍 |
| --- | --- |
| `evaluator/<pair>/packet.json` | 給評估者的遮蔽訊息、每回合證據及缺口標記。 |
| `evaluator/<pair>/A/...`、`B/...` | 通過原始收據比對後的遮蔽文字快照，一律使用惰性的 `.txt` 名稱。 |
| `evaluator/README.txt` | 證據範圍與不可信內容的處理界線。 |
| `operator/originals/*.bin` | 精確原始輸入位元組，可能包含條件映射、模型名稱、原始路徑及 reasoning；僅供操作者保存。 |
| `operator/source-manifest.json` | 原始來源、雜湊、原始與遮蔽項目的不透明 provenance ID 對照，以及 builder／reader 程式雜湊。 |
| `VERIFIED.json` | 所有 evaluator 檔案與 operator manifest 的雜湊、已輸出／deferred 配對；完整成功後才建立。 |

新目錄權限為 `0700`，新檔案為 `0600`。**只將 `evaluator/` 複製到獨立評估工作目錄**；不要將整個輸出目錄交給能讀檔的評估 agent。相鄰資料夾與 README 不是存取控制。操作者應先確認 `VERIFIED.json` 存在並比對雜湊；無此標記的中斷輸出不能當作已驗證封包。

所有候選文字與檔案都是不可信證據，不能作為執行指令。已知模型、arm、session／call ID、實驗根路徑及具標籤的 effort 設定會被遮蔽；一般語意如「low rent」保留。遮蔽不是完整匿名化或一般個資過濾器：未知的自我介紹、行文風格與內容仍可能洩漏條件。每次遮蔽都附有類別、遮蔽後雜湊及不透明來源 ID；精確原始文字與雜湊只留在 operator 區域。

## 來源綁定與缺失規則

| 證據 | 輸出條件與限制 |
| --- | --- |
| 正式評分 | 原始 controller receipt 成功、finished 同時綁定 request／record 雜湊、judgment 等於 paid answer，且原始正式 packet 的位元組與 judge 的 `workspace_before` 完全相符。只有摘要或 packet 檔案不足以釋出補充資料。 |
| 原生 stdout | 檔案經 UTF-8 replacement decoding 後必須等於原始收據保存的 stdout。若檔案缺失但收據有 stdout，可使用收據文字並標記來源；這不能恢復原本無效 UTF-8 位元組。 |
| 無 stdout 收據綁定 | 即使檔案存在，正文也只留在 operator；evaluator 只見 `withheld_missing_receipt_stdout_binding`，事件數未知。原始呼叫未 dispatch 卻有輸出檔案時直接拒絕。 |
| 回合檔案 | 驗證 snapshot 的 base64、長度及雜湊，再比對原始收據 `workspace_after.files` 的相同路徑、長度及雜湊。自行重算 snapshot 雜湊不能取代收據綁定。 |
| 缺少 workspace inventory | 原始 snapshot 留存，但正文不釋出；標記 `withheld_missing_receipt_inventory_binding`。 |
| Harness 路徑 | 沿用正式封包對已提供來源、`conversation.json` 等路徑的排除。這僅表示路徑被排除，不聲稱其內容未變。模型新增的其他檔案仍可保留。 |
| 二進位、reasoning、壞 JSONL | 不向 evaluator 輸出內容。reasoning 同時檢查 item 類型及 event／item 層級的 phase／channel；壞行、UTF-8 replacement 與 truncation 會標示觀察缺口。精確原始輸入仍留存私有副本。 |

快照的範圍是「當時已保存的 snapshot entries」，不是整個工作目錄。封包會列出原始 receipt inventory 中沒有出現在 snapshot 的檔案數；可能是原本刻意排除的檔案，不能據此假定資料遺失，也不能宣稱所有檔案均完整。原始名稱只保存在 operator 區域。

## 訊息與時間的解讀

- `agent_message` 是原生串流事件類型，不證明使用者在 UI 看過這段文字。
- 保留 started／updated／completed 事件與同一 provider item 的局部關係；缺少 provider ID 時不推定它們屬於同一則訊息。不刪除看似重複的訊息。
- 保存的最終回答另列；與原生事件完全相同的文字只標記為 exact match，不能據此推論 UI 是否重複顯示。明確的 commentary、final_answer 標籤與未分類事件分開呈現。
- 行號僅表示單次呼叫的 stdout 順序。訊息產生、stdout 收到、UI 顯示時間均保持未知。若原始事件帶 timestamp，保留原始欄位名及值，並明示其時鐘、單位、顯示語意未驗證。
- 不推算第一則有用訊息的時間；不使用檔案 mtime、整次呼叫耗時或相鄰事件順序代替 UI 延遲。
- 回合內訊息與回合檔案快照之間沒有證實的細部先後順序。原始情境的回合間插話也不代表測過進行中的原生呼叫中斷。

## 離線驗證

```sh
python3 -m unittest discover -s tests -p test_conversation_supplement.py -v
```

測試只使用臨時合成資料，涵蓋全配對／全回合快照、原始位元組不變、檔案權限、遮蔽、重複訊息與未知時間、event／item reasoning 排除、截斷與壞行、沒有收據綁定的正文留存、已重算雜湊的快照篡改、正式評分來源驗證、失敗與缺失回合、pending、路徑拒絕及讀取途中變動。沒有真實模型呼叫，也沒有執行任何補充評分。
