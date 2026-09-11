# Grok Bot: one-time test setup

Use this after deliberately installing or attaching a known version of the `pea-princess` skill. The panel example alone is not the skill. Keep the reviewer scenarios and expected outcomes out of the actor's context. This setup does not select a model, create a routine or authorize sending anything to landlords.

Copy the following setup message, then send your actual initial rental request separately:

> 這次請使用我提供的 pea-princess skill 陪我找房。我會直接跟你聊，也可能用語音轉文字、中途插問或改條件。
>
> 先簡短確認你實際讀到了哪一份 skill；若讀不到，就說明缺哪個檔案。之後請依我的需求正常研究與討論，不用反覆介紹工具或內部流程。
>
> 請在這次專用的工作資料夾保留目前需求、修改紀錄和研究來源。我說「整理目前需求」時，給我可閱讀的摘要與可下載的最新檔案；我說「整理報告」時，用目前條件和已有證據更新同一份報告。附上版本或時間，讓我們之後能核對。若沒有檔案工具，直接說明，先在對話裡保留即可。

Do not paste all test turns at once. The real test begins with the next user message. A reply acknowledging setup is not the rental opening and should not receive an opening-quality score.

A reviewer should retain the exact submitted setup, actual skill bytes/hash when retrievable, and whatever model/effort/usage information the host actually exposes. A Bot's claim to have installed a file is weaker evidence than the downloaded file itself. Do not fill unavailable usage with zero.

When finished, use the host's conversation export if available. Also retrieve the latest requirement file, its change history and the report. If the Bot itself produces a retrospective conversation transcript, label it as model-reconstructed and compare it with native records before using it as verbatim evidence. Transfer only the dedicated test folder, not an entire account workspace.
