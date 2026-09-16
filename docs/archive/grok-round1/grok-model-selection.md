# Grok Bot model selection and generated files

Checked 2026-09-09 against official documentation. This is a documentation review; it adds no Grok or Claude model calls. The previous [native Grok smoke](grok-native-smoke-results.md) remains a separate, limited observation. Attachment repair is deferred while the conversation experience is corrected.

## Why there is no model picker

The official [Grok Bot settings page](https://docs.x.ai/grok-bot/settings-and-notifications#agent), updated September 2, explicitly says: “Cursor manages model selection, so there is no model picker.” Therefore the missing picker is documented product behavior. The documentation does not say that a more expensive subscription unlocks one, or disclose a fixed model for every Bot run. A model announcement linked in the documentation header is not evidence of the model used in a particular conversation.

## Products and subscription scope

| Surface | What the official documentation establishes |
| --- | --- |
| Grok Bot | Provider-managed model selection. Bot is distinct from ordinary grok.com and the Grok mobile apps, as the [product FAQ](https://docs.x.ai/grok/faq#products-models) explains. |
| Ordinary Grok chat / web Build | Do not infer their available controls from Bot or CLI documentation. This review does not establish the current model picker choices for a particular account. |
| Grok Build CLI | The [Build guide](https://docs.x.ai/build/overview#custom-models) supports configured models, `-m`, and `/model <name>` in its terminal interface. These controls do not imply the same selector exists in Grok Bot. |
| xAI API | The [API quickstart](https://docs.x.ai/developers/quickstart) uses API credits, an API key and an explicit `model` field. Bot access does not establish API entitlement. |

The [plans page linked by xAI](https://cursor.com/help/grok-bot/plans) says eligible paid Cursor plans include Bot, and individual SuperGrok, SuperGrok Plus, SuperGrok Heavy or X Premium+ can grant Bot usage by account linking. Included usage resets weekly; additional work can use shared on-demand spend when enabled. Plan differences affect usage allowance. They do not establish a user-selectable Bot model or prove the cause of an unsatisfactory answer.

## What counts as a delivered file

Official [Files and results](https://docs.x.ai/grok-bot/files-and-results#preview-generated-work) describes generated files as conversation cards that can be opened, previewed where supported, and saved. `/workspace` is shared intermediate storage; the final result or a clear link should still be returned in the conversation.

Our acceptance rule is to verify that the actual attachment opens or saves successfully. A displayed filename or raw filesystem path alone does not prove delivery. The reviewed Bot documentation does not specify a `sandbox:/mnt/data/...` URI contract or an internal attachment-tool name; do not invent either as a repair. File-delivery behavior and answer quality need separate checks.
