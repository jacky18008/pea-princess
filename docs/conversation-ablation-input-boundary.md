# 對話消融的實際輸入邊界

2026-09-10。這是原始矩陣收集期間新增的限制揭露，沒有修改凍結來源 `e001e06`、原分組、請求、回答或正式評分規則。本文寫作時，正式配對評分尚未開始。**已確認四次呼叫的本機工具輸出返回了實驗工作目錄外的舊版 skill 本文；因此，凍結輸入的雜湊正確，不能再被解讀成模型只取得那些輸入。**

## 已查範圍與觀察

兩份分開保存的稽核使用不同的固定範圍，不能混用分母，也不能把它們當成目前整個執行的普查：

| 稽核範圍 | 已確認返回舊版本文的呼叫 | 另列的搜尋嘗試 |
| --- | --- | --- |
| 第一輪全部 48 筆及第二輪全部 46 筆終態收據，共 94 筆；第一輪包括兩筆失敗 | `s30-t02`、`s29-t02` | `s37-t01` |
| 稽核時固定的 22 筆第三輪成功收據；不含後來完成的第三輪 | `s26-t03`、`s33-t03` | 此範圍沒有新增同類匹配 |

四筆本文事件分屬四段對話。它們的已完成 shell 指令從主機安裝位置讀取 `SKILL.md`，再輸出其他資訊。稽核依混合指令的明確分隔邊界抽出歷史返回區塊：每筆都是 123 行、17,422 字元，區塊雜湊相同；與凍結 ZIP 的既有入口、凍結短入口均不同，含有情境外的舊版指令。私人條件、本文與實際主機路徑不在此公開文件重印。

這是保存輸出在該次有界讀取內的證據。稽核沒有重新讀取目前主機上的 skill，也沒有把混合輸出的檔案清單算成 skill 本文。四筆事件均未見保存收據的輸出截斷旗標；這仍不代表已盤點整個主機、所有工具內容或所有可能的讀取方式。

`s37-t01` 必須分開解讀：它嘗試透過搜尋指令查找工作目錄與一個外部 skill 位置，保存的兩行輸出只有當次工作目錄及工作區內的 fixture 檔名，**沒有返回主機 skill 的檔名、路徑或本文**。整條指令的退出碼為 0，但搜尋元件接在管線中，且其錯誤輸出被重新導向，因此 `rg` 自身的退出碼與錯誤未知。這只能標記為「嘗試搜尋；未證實成功發現」，不能算作第五筆本文讀取，也不能據此斷言外部位置不存在。

收據核對包含 canonical record 雜湊、保存的 native record、對應請求與來源 pin；第一、二輪的選定檔案在讀取前後保持相同。篩查對象是保存的已完成工具指令及命中的歷史返回內容，不涵蓋執行中的呼叫、未保存事件或任意隱藏讀取。**未被這次篩查標記的案例，仍不能稱為已證明隔離。**

## CLI 設定實際保證了什麼

保存的相關 invocation 與凍結 native runner 使用 `codex exec`，指定實驗工作目錄、`--ignore-user-config`、`--ephemeral`、`--sandbox workspace-write`、`project_doc_max_bytes=0` 及 JSON 事件輸出；沒有加入 skill discovery 的停用覆寫。

| 設定 | 官方定義與本次解讀 |
| --- | --- |
| `--ignore-user-config` | 不載入 `$CODEX_HOME/config.toml`；驗證身分仍使用 `CODEX_HOME`。不能把這個旗標擴張解讀成停用全部主機 skill。見 [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。 |
| `--ephemeral` | 不將 session rollout 檔持久保存到磁碟，並非建立乾淨的主機環境。見 [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)。 |
| `project_doc_max_bytes=0` | 該設定限制組建 project instructions 時讀取 `AGENTS.md` 的位元組數；不是 `SKILL.md` 探索開關。見 [Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)。 |
| `--sandbox workspace-write` | 設定模型產生指令的 sandbox 政策；寫入範圍與 skill 探索是不同層次，不能單憑此設定宣稱所有主機讀取都被隔離。見 [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli) 與 [Sandbox](https://learn.chatgpt.com/docs/sandboxing)。 |

官方另行描述從 repository、user、admin、system 位置探索 skills，包括一般的 `$HOME/.agents/skills` 路徑；初始上下文可以包含名稱、描述與路徑，選用時才讀本文。文件也提供逐項 `skills.config` 停用方式；`allow_implicit_invocation: false` 只關閉隱式選用，明確選用仍可用。這些機制解釋為何必須單獨驗證 skill 來源，不能證明本次每一個歷史呼叫實際注入了哪份清單。見 [Build skills](https://learn.chatgpt.com/docs/build-skills)。

本機只讀 CLI 稽核在 2026-09-10 觀察到 **0.153.4**，另存當時 executable 的 SHA-256。這是稽核當下的版本與位元組記錄，**不是所有歷史 invocation 的 binary 證明**。當時 `codex features list` 列出 `skip_host_skill_discovery` 為 `under development`、值為 `false`；它僅是下一版可驗證的候選控制，本次沒有啟用或試跑，也沒有驗證其涵蓋 user、admin、system、plugin 或 repository 的哪些來源。這份 feature listing 也不是歷史子程序的有效設定快照。

目前 receipt 的明確欄位記錄自有 prompt、指令、工作區快照、CLI 輸出與工具事件，沒有獨立的「完整有效 system prompt／skill catalog」欄位。本次 CLI 稽核亦未另行擷取完整有效清單；其他歷史記錄能否重建它，尚未確定。這不等於已完整搜尋全部 log 並證明那些資訊不存在。

## 對成本、品質與消融解讀的限制

依私人 Astra 評估政策及後續更正，原指定分組與實際返回內容分開記錄。四筆事件是已觀察到的額外輸入與 protocol deviation；不能把案例改分到另一個 arm，也不能因為讀到舊版本文就自動判零分、判定 rubric gate 失敗或預測品質升降。原回答仍依原 rubric 評分；比較是否足以支持處理效果，是另一個問題。

保存的本機 returned bytes 不能獨立證明 provider 完整收到多少內容、模型注意了哪些段落或採納了哪些指令。若要聲稱後續回答遵從舊版條件，需要另外核對具體行為與來源，且相似文字本身不足以建立因果關係。本次發現也沒有提供「多少 token 是因此增加」的可辨識估計；不能用本文長度直接換算整段額外用量，更不能將整個用量激增歸因於此。

第二輪已返回本文的兩段對話，後續可能透過回答重放或檔案狀態延續影響。第三輪沒有再次讀取的事件，也不能自動把整段對話改列為符合輸入排他條件。只有後輪保存的 prompt 確實包含相應文字，或後輪保存的讀取事件與相應產物版本相符，才能進一步標記已觀察到的傳遞；目前這份邊界稽核沒有完成該逐段判定。單憑對話繼續或檔案存在，只能列為可能承接、實際傳遞未知。這次仍是每輪新 CLI invocation 搭配歷史／檔案恢復，未測試 native persistent conversation 或 native compaction；見[連續性限制](native-continuity-followup.md)。

完整矩陣仍有描述「在這台實際主機環境下，指定方案產生哪些成本與輸出」的價值，但須揭露額外輸入、未知覆蓋及執行時間差異，不能冒稱已隔離出入口、讀檔方式、模型或 effort 的純效果。配對兩邊都出現額外讀取也不保證影響抵銷，因為時點、內容與後續採納可能不同。

若完成收集後另看「排除已知偏離」的子集，只能標記為 **post-hoc sensitivity analysis（事後敏感度分析）**。保留原配對結構，逐項報告分母、失去的配對與未知狀態；不能把篩選後的案例叫做已證明隔離的樣本。額外讀取行為本身可能受處理條件影響，事後篩選有選擇偏差；每格僅一段對話的設計尤其不能靠這種篩選補成新的因果證明。

## 保留原始資料與下一版邊界

原矩陣、原始收據與正式評分保留；補充觀察和事實更正以新增紀錄追溯，不覆蓋原證據。`s37-t01` 先前被措辭為可能成功找到主機位置的說法，已由追加更正收斂為上述「僅嘗試搜尋」；這份公開說明採更正後的分類。當前收集繼續使用既有凍結方案，沒有因本發現中途換 prompt、替換 skill、啟用候選旗標或補做優化實驗。

下一版應先以合成資料驗證兩個不同的邊界：skill discovery／有效提示是否只包含准許來源，以及 shell 能否讀取工作目錄外的資料。關閉探索即使有效，也不會自動阻止對已知路徑的檔案讀取。可在專用 OS 使用者或隔離環境中，用非私人 canary 檔驗證預期允許與拒絕，再保存每次 executable、有效設定、可用 skill 來源及必要的提示來源證據。這是尚未執行的設計工作，不是本輪已修復或已隔離的宣稱。

此處記錄的是研究輸入邊界偏離，沒有由這些讀取事件推論 sandbox escape 或資料外洩。這次稽核沒有重新讀取目前主機 skill 或驗證身分資料。

## 私人追溯索引

以下是受限 operator audit 的檔名索引，未複製原指令、私人路徑或本文；原始 hash manifest 留在私人備份中：

- `t1t2-host-skill-audit-20260910T072932Z/`：`screen.json`、`final-audit.json`、`source-pin-confirmation.json`、`s37-discovery-clarification.json` 與追加的 `CHECKSUMS-clarified.json`。
- `t3-prefix-external-path-audit-20260910T072427Z.json` 及同名 Markdown：固定 22 筆第三輪範圍與兩筆返回本文的證據。
- CLI 邊界稽核的 `operator-note.md`、help／features 輸出及 checksum manifest：當時 executable、旗標與可觀測性限制。
- `external-input-policy-review.md`：Astra 的評估處理政策及後續追加的範圍、搜尋事件與 catalog 可觀測性更正；不改動原 formal packets 或 judgments。

進度快照另見[執行紀錄](conversation-ablation-progress.md)。本文件沒有新增模型呼叫、評分或品質勝負結論。
