# 原矩陣的預算變更與恢復

2026-09-09。原方案是 192 次受控原生執行、6,000,000 processed tokens。三次完成後曾在 invocation 邊界暫停；使用者隨後明確要求先跑完原定矩陣、鬆動 600 萬門檻，之後再研究浪費。

本次因此解除 token 停止門檻，保留原定 **168 次回答＋24 次評審**、48 個 session、模型／effort／研究深度、原始提示、合成資料、排程及零自動重試。Claude 保持暫停。沒有把放寬預算解讀成新增案例、無限重試或購買額外服務。

原 `plan.json`、`frozen.json` 和前三次原始收據不修改。源碼以 `e001e06d01a3963b4be5f7cbf03c8bc543620fde` 保存為獨立私有目錄，另放入當時的公共 ZIP；12 個凍結來源 SHA 全部核對一致。新的 state API 說明與其他改善保留在後續 commit，不混進這輪。

`bench/conversation_resume.py` 是執行管理的外層工具。它先驗證凍結源碼與原計畫，再驗證單獨的預算 amendment；只在記憶體中替換「下次呼叫前的 token 停止值」。原計畫的數字留作歷史。外層工具不改 `answer_request`／`judge_request`，不清空用量、不替換模型，也不跳過未知用量或尚未處理的失敗。

私有 `amendments/budget-0001.json` 保存使用者原文、來源 request ID、時間、原 plan 與排程 digest；首次恢復另寫不可覆寫的 `resume-audit/budget-0001.json`，綁定 wrapper hash、凍結源碼及 amendment。預算變更是 trusted operator 對使用者授權的紀錄，檔案雜湊不是使用者身分認證。

操作時，`--source` 指向獨立的凍結 source，`--output` 指向原本三次結果所在的 run，`--amendment` 指向上述私有 JSON。先執行 `status` 核對用量與 pending；移走並封存已處理的 `PAUSE_REQUESTED.json` 後才執行 `answers`。`judges` 由獨立 evaluator 操作。再次建立 pause 檔會在下次 invocation 前停止；不能收回已進行中的模型用量。

完整實驗仍用每次實際終端收據記帳。一次 CLI invocation 可能含多輪 provider 請求；input 包含 cached input，processed 為 input 加 output。主代理及協作子代理的對話用量沒有相同收據，另列未知，不宣稱這是整個帳戶完整帳單。

相關文件：[原凍結方案](conversation-ablation-protocol.md)、[三次成本診斷](../native-pilot-cost-diagnosis.md)、[評估流程複核](../conversation-evaluation-process-review.md)。
