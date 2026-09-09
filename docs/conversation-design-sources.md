# Conversation design: sources and acceptance rules

Checked 2026-09-09. The user asked for a collaborative rental assistant: at most three essential questions, useful progress immediately, everyday language, and selectable answers where the host supports them. These are product requirements, not claims that every provider enforces the same conversation style.

| Product rule | Official basis and scope |
| --- | --- |
| Ask only for missing information that changes the next useful step. Skip answered questions; use clearly stated, reversible assumptions for nonessential details. At most three questions per reply. | OpenAI's [GPT-5.2 guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.2) gives a prompting example with 1–3 precise questions or labeled interpretations. This is an example, not a universal model limit. |
| Start useful work with the information already supplied. Do not make the user complete a full questionnaire before seeing a comparison or recommendation. | OpenAI's [current model guidance](https://developers.openai.com/api/docs/guides/latest-model#initiative-and-follow-through) recommends completing authorized work before blocking for clarification. It also recommends avoiding extra disclaimers or approval flows based only on hypothetical risk. |
| Use familiar words and short answers. Explain a necessary unfamiliar term at first use. Show execution settings in report About/details, not the opening answer. | OpenAI's [writing guidance](https://developers.openai.com/api/docs/guides/latest-model#personality-and-writing-style) calls for concise prose, familiar words, and technical detail only when it helps the reader. Hiding routine internal labels is this product's implementation of that principle. |
| Use a real choice interface when available; otherwise ask a short text question. Accept a custom answer. | [Codex App Server](https://learn.chatgpt.com/docs/app-server) documents experimental `tool/requestUserInput` with 1–3 questions and a client response lifecycle. [Claude Code user input](https://code.claude.com/docs/en/agent-sdk/user-input) documents `AskUserQuestion`, its SDK callback, custom text, and limits of 1–4 questions with 2–4 options. Our three-question cap still applies. |
| Keep questions and changes connected to the current conversation. A later budget change should update the comparison rather than restart onboarding. | [Claude's user-input guide](https://code.claude.com/docs/en/agent-sdk/user-input#streaming-input) describes streaming input for interruptions, additional context and follow-ups during work. This requires host integration; a prompt alone does not implement interruption or choice widgets. |
| Evaluate understanding, relevance, factual accuracy and time to useful resolution, not just formal completeness. | Anthropic's [customer-support guide](https://platform.claude.com/docs/en/about-claude/use-case-guides/customer-support-chat) recommends representative good conversations and separate success criteria for these qualities and relevant sources. |

## Rental conversation examples

- If the user has already given a date, preferred home type and a wish for quiet, retain those facts. Ask only for missing essentials such as monthly budget and commute destination.
- Say “total monthly cost” / “每月總花費”, explaining included bills where necessary. Schema fields such as `all_in_pcm_ceiling` remain internal compatibility identifiers.
- Give a useful preliminary comparison immediately. If no live listing search is available, label examples as examples and say what information would allow an actual listing check. Never invent available homes or claim to have searched.
- Keep listing and legal sources near the facts they support. Internal prompt paths, test labels and execution headers are diagnostic metadata, not evidence for rental advice.
- Mention a concrete payment, contract or evidence limitation when it affects the current decision. Do not append the entire legal checklist to a general greeting.

## Acceptance cases

1. All essential details supplied: no repeated onboarding; start the requested work.
2. Details missing: at most three questions, with concise choices and custom text where supported, plus useful initial progress.
3. Partial answers: retain answered fields and ask only the next necessary question.
4. Mid-conversation change: preserve prior facts, apply the changed budget or preference, and revise affected conclusions.
5. No search/choice capability: use an honest, useful fallback without claiming unavailable actions.
6. Report rendering: no configuration banner before the verdict; metadata remains in About. Current labels use everyday cost terms, while imported historical text remains verbatim.

These are regression criteria. Passing deterministic tests does not establish model quality, token savings, or factual correctness of a generated rental recommendation. Model comparisons require separately frozen prompts, cases and recorded usage.
