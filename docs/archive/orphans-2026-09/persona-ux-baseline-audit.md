# Persona chat UX baseline: private-log audit

2026-09-09. Read-only inspection of the three recent synthetic C1, C2 and P2 first responses in the local persona lab. Original sessions, physical outputs and managed state were preserved. This document contains relevant aggregate telemetry and implementation causes; private transcripts and user-identifying material remain outside this document. No extra model call was made for the audit.

All three used `gpt-6-astra` with low reasoning effort and the lab source SHA-256 `cc21c0dfd72711d7a1fc64d16abd75ca1a8767d8159f75ede2e3198051ce553c`. Shared runner source: `7a6b2c66ef4652ec7bfcf68dd841cec6dabf614808b483777c7ddb9031d001f8`. These are historical versions, before the new conversation/choice contract.

| Synthetic persona | Input tokens | Output tokens | Cached input, included in input | Total processed | Assembled prompt characters |
|---|---:|---:|---:|---:|---:|
| C1: newcomer | 25,879 | 696 | 11,520 | 26,575 | 43,319 |
| C2: area search | 25,898 | 740 | 11,520 | 26,638 | 43,350 |
| P2: contract first | 25,900 | 564 | 11,520 | 26,464 | 43,670 |
| Total | 77,677 | 2,000 | 34,560 | 79,677 | — |

Each saved call had one physical attempt, a complete receipt, no provider errors and no tool events. Logical manifests, physical checkpoint state hashes and terminal record hashes were verified. All three sessions were paused with no pending call or queued human intervention at inspection. The source system text alone was roughly 41,380 characters; each first-step state packet was 1,246 characters. Repeated prompt input, rather than generated reply length or hidden retries, accounts for most observed processed tokens. This is not a monetary billing estimate.

Observed problems and their causes:

- **Six-question onboarding:** C1 displayed six numbered intake questions and appended a legal paragraph. `references/onboarding.md` explicitly required all six in one message, followed by the legal sentence and safety warnings. It also supplied suggested area/floor defaults, explaining why those appeared before learning the person's preferences.
- **Mode and tier jargon:** the prompt pack required stating `manual`/other mode and naming the tier on the report's first line. The interactive app reused this report-oriented contract for a chat opening.
- **Internal labels presented as sources:** C2 cited `THIS RUN` and `ACTIVE RUNTIME SETTINGS`. `bench/journeys.py:system_prompt` inserted the first heading; `tools/persona_playground.py:configured_system` added the settings heading and requested a visible summary. `tools/session_runner.py:run_step` added a global instruction to cite source IDs. The model treated internal prompt headings as citation targets.
- **Unexplained vocabulary:** `all-in` was present in synthetic opening messages and the instruction pack. A user-facing language policy was needed even when the source material already used that phrase.

The relevant assembly chain was `journeys.system_prompt` → `personas.system_prompt(card, 'chat')` → `configured_system` → `_prepare` → `session_runner.run_step`. It included the generated prompt pack, retrieval instructions, onboarding text and selected references before replaying the conversation. The complaints therefore point to an instruction/UI contract problem, not damaged transport or missing model output.

The replacement should preserve exact user constraints and uncertainty while moving configuration details out of the reply. Local structured choices are a presentation aid, not native provider tools, confirmed preferences or quality evidence. Offline format/queue/restart tests can verify those mechanics; they do not establish improved model quality or new token savings. A later bounded comparison must keep this baseline's original artifacts intact.
