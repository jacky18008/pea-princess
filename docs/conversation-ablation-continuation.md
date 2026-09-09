# 超時後繼續原定的獨立案例

2026-09-09。`s48-t01` 在原定 240 秒截止前沒有交付最後回答，原始收據與未知用量已保存。使用者要求完成原矩陣並移除 token 停止門檻，因此可以在檢查已終止的失敗後繼續其他獨立案例；這不授權重送失敗 ID、補造對話、擴充 192 個原定 slot 或更改 timeout。

新的 `bench/conversation_continue.py` 使用凍結來源 `e001e06` 的 request builders、native transport、資料與結果保存流程。操作層另有版本和 hash；原提示、模型、effort、深度、240 秒限制都不變。已完成的四筆與失敗的一筆不重跑。

## 明確處理失敗，不覆寫失敗

`CallControl.acknowledge_failure()` 只接受目前的暫停原因、已持久化的終止收據，以及操作原因。pending 存在時拒絕。它透過原 reducer 的 `resume` event 追加紀錄，不改任何原始 call row、terminal outcome 或用量。

未知用量預設仍阻止這個操作。本次 continuation 只有在驗證使用者已移除 token 門檻後，才明確指定 `allow_unknown_usage=True`。總量持續為 null，已知小計與未知筆數分開報告；不把未知視為已對帳、不估算帳單。

控制器新增兩個必要保護：失敗的實體呼叫 ID 永遠不能再次 dispatch；下一次暫停會回報當下的 `pause_cause`，而非最早的歷史失敗。補跑若另獲授權，必須使用新的 attempt 身分及相應版本，原失敗仍保留。

## 相依工作與評分

新 scheduler 只挑選原計畫中尚未執行、而且前置回答都有成功保存紀錄的案例。失敗與成功分開；失敗後的同段對話及其配對評審標為 deferred，沒有被標成完成或跳過。

因此 `s48-t02`、`s48-t03` 與相關配對 `j23` 會暫留。其他 session 可以繼續。沒有完整對話的一側不能參與正常配對效果比較；完整的另一側仍可另行觀察，但不得藉缺失直接判為勝者。單次截止前未交付的可靠度，與未能觀測的對話品質，是兩個指標。

原 `plan_complete` 保留原意，不會因為「其他可執行工作已處理」而被改成 true。`exhausted_independent_work` 也不代表所有條件驗證通過。

## 可追溯操作

在首次 acknowledgment 或新 dispatch 前，`continuation-audit/budget-0001/` 保存不可覆寫的 manifest，綁定原計畫、預算 amendment、凍結來源、操作層程式、開始前 checkpoint 及失敗收據 hash。每個明確 acknowledgment 另有紀錄。後續檢查程式和原始失敗收據是否變動，變動則停止。

CLI 提供 `status`、`acknowledge --call-id ... --reason ...`、`answers`、`judges`；三個必要路徑參數與 [budget resume](conversation-ablation-budget-amendment.md) 相同。`PAUSE_REQUESTED.json` 仍可在 invocation 之間停止。新的失敗不會自動被 acknowledge 或重試，須先檢查私有收據。

這是延續原定工作所需的操作修正，不是省 token 的 treatment。工具文件、技能精簡及其他成本改善保留到這輪結果完成後比較。
