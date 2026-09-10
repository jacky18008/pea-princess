# 對話體驗的獨立驗收門檻

2026-09-10。這是新一輪驗收規格與離線工具，**不是模型已通過的結果**。它補上使用者要求的第一句體驗，保留[既有完整評估設計](conversation-evaluation-design.md)的事實、授權與任務成果檢查；不回寫歷史 rubric 或分數。

使用者要求的「posh」在這裡指精緻、溫暖、有判斷力的服務：第一句就提供與當下決定相關的資訊、洞見或取捨，讓下一輪值得繼續。華麗字眼、稱讚使用者、制式同理、空泛保證，都不能代替這件事。這是專案的產品選擇，並非 OpenAI 或 Anthropic 規定的文風。

## 哪一句接受驗收

每次使用者發話後，按照實際事件順序找出**第一則使用者可見助理訊息**，檢查其第一句。原生工具呼叫前的 progress／commentary 也算；不能只拿最後比較漂亮的 final 評分。隱藏分析、內部工具資料不算可見回覆；顯示狀態由 controller 明確記錄，不能由評審為了拿高分自行推測。

除了第一句，評審要讀該輪所有可見內容。好的開場後面仍可能出現過量提問或流程說明；好的結尾也不能抹去不好的開場。若進度訊息是否顯示、完整性或順序無法確認，標為未知，不能宣稱已驗收。純粹的暫停、道謝等社交發話，可以自然接續，不要求每次硬塞一則新知。

## 不可互相抵銷的門檻

機器可讀定義在 [ux-gate-v1.json](../evals/conversation-acceptance/ux-gate-v1.json)。每個狀態都是 `pass / fail / unknown`；只有單輪資料無法觀察的整段門檻可以標 `not_applicable`。

| 層次 | ID | 要證明的事情 |
|---|---|---|
| 每輪 | O1 | 第一個可見句子精緻、切題，提供有依據的答案、洞見或取捨。 |
| 每輪 | U1 | 回答當前問題，包括插問與需求調整。 |
| 每輪 | U2 | 給出比較、解釋、可用檢查或實際研究成果；尊重合理停止點。 |
| 每輪 | U3 | 講人話、資訊順序合理、負擔可接受，沒有把內部管理工作丟給使用者。 |
| 每輪 | U4 | 問題有必要、沒有重問或暗藏多個決定，通常零至兩題，最多三題。 |
| 整段 | C1 | 研究、選項、使用者反應與下一步接得起來；插問與重開後不用重新填表。 |
| 整段 | C2 | 使用者實際反應確實改變後續回答與工作，沒有虛構同意或滿意。 |

**全部適用門檻通過，才算 UX 通過。** 任一失敗直接阻止通過；未知也不能通過。內容正確、字數很少、問號很少、工具很多、主觀總分很高，都不能抵銷。明確要求詳細解說或完整問卷時，評審必須引用該要求，不能機械地因為長就扣分。

完整產品驗收還需要獨立的 `G1` 事實／證據、`G2` 授權／安全、`G3` 必要條件三項通過，以及當前任務成果完成。程式條件核對仍需對照原始使用者授權、實際來源和保存產物；UX 工具不負責判斷房源真的符合條件。

## 留下什麼證據

評審輸入保留完整的可見對話、選項、工具軌跡、當時可用的來源、條件事件、最新產物及恢復狀態。每輪只能用當時已提供的資料判斷；未來的來源或使用者變更不能倒過來替早先猜測辯護。

每個語意判斷都寫簡短原因與精確引文。O1 指向第一則可見訊息開頭；C2 必須同時引使用者的實際反應與助理後續內容。評審不需要輸出隱藏推理。使用者改優先順序是正常探索，不自動扣分；感謝、沉默或合成人物的開心也不是成果完成或真人滿意的證明。

[calibration-v1.json](../evals/conversation-acceptance/calibration-v1.json) 是八個作者撰寫的合成正反例，供獨立評審先檢查尺度。包含有用開場、先講內部狀態後才給好答案、禮貌卻無用、尊重暫停、流暢但擅自放寬硬條件、插問後調整、口頭接受卻忽略反應，以及缺失進度紀錄。它們不提供給回答模型、不作為新驗收情境，也不是人類標註或模型已通過的回歸結果。

獨立 Astra 評審先保存原判，再由 root 複核證據與分歧。任何更正另外保存原因、原值、新值與適用範圍，不把討論後分數冒充新的獨立樣本。這仍是 AI 評估；真人驗收與其他模型的結果分開記錄。

## 離線驗證介面

[conversation_ux_gate.py](../bench/conversation_ux_gate.py) 不呼叫模型，也不使用關鍵字規則判斷「講人話」。它驗證評審記錄的完整性、引用、最早可見訊息與門檻合併：

```python
from conversation_ux_gate import evaluate, packet_digest

result = evaluate(packet, judgment,
                  correctness_gates={"G1": "pass", "G2": "pass", "G3": "pass"},
                  task_outcome="complete")
```

`packet` 是完整評審包的最小可見訊息投影，欄位如下。每層明確列出的欄位都必填；不要拿這個投影取代完整原始證據。

```json
{
  "schema_version": 1,
  "session_id": "session-id",
  "user_kind": "scripted",
  "turns": [{
    "turn_id": "t01",
    "trace_complete": true,
    "messages": [{
      "id": "u01",
      "role": "user",
      "channel": "message",
      "visible": true,
      "content": "The exact user message."
    }, {
      "id": "a01-progress",
      "role": "assistant",
      "channel": "commentary",
      "visible": true,
      "content": "The exact first visible reply."
    }]
  }]
}
```

`user_kind` 接受 `human / scripted / model / mixed / unknown`；訊息角色為 `user / assistant / tool`。訊息陣列依原始事件順序，不依 final 優先重排。完整性是 controller 的聲明，需另外核對原始紀錄，並非這支程式能自證。

`judgment` 必填 `schema_version: 1`、`rubric_id: pea-conversation-ux-gate-v1`、`session_id`、`packet_sha256: packet_digest(packet)`、`turns`、`session_gates`。每個 turn 判斷含 `turn_id`、`opening_message_id`、`gates`；`gates` 必須完整包含 O1/U1/U2/U3/U4，session_gates 則包含 C1/C2。各 gate 都有：

```json
{
  "status": "pass",
  "reason": "A concise evidence-based assessment.",
  "evidence": [{"message_id": "a01-progress", "quote": "The exact first visible reply."}]
}
```

沒有可見回覆時，`opening_message_id` 為 null，該輪各門檻全部 unknown。缺失進度紀錄即使可評保留內容，整體仍 unknown。程式核對 O1 引文從第一則可見訊息開頭起始；是否涵蓋完整第一句、是否有洞見，仍由評審與 root 語意複核。單輪資料的 C1/C2 不能宣告 pass。

CLI：

```bash
python3 bench/conversation_ux_gate.py --packet packet.json --judgment judgment.json \
  --correctness correctness.json --task-outcome complete
```

`correctness.json` 是另行驗證的 G1/G2/G3 狀態 map；省略時 overall acceptance 保持 unknown。stdout 一個 JSON，包含獨立 UX、正確性、任務成果與整體狀態。有效的 fail／unknown 判定仍是正常 exit 0；資料格式或引用錯誤 exit 2。程式不修改原始輸入、不自動修分、不補跑評審。

[離線測試](../tests/test_conversation_ux_gate.py) 覆蓋早期 progress、不完整紀錄、遺漏／重複／重排輪次、假引文、跨輪未來引文、隱藏訊息、錯誤 packet、使用者反應證據與相互不可抵銷的門檻。這些測試證明工具行為，不證明模型已具備好對話能力。
