# Requirements-panel example: validation record

Checked 2026-09-11. This record covers the proposed interface and test instructions. It does not establish model conversation quality or production dashboard integration.

## Scope and evidence

- Fragment SHA-256: `af7a693f232dc4f3dfb7ad50cb45f6888f7e473213758e471d0dde575ac29766`.
- The standalone page includes exactly the same fragment as the inline example. The builder uses only Python's standard library.
- Twenty browser check groups passed: fifteen interaction/layout checks and five targeted destination checks. These are interface checks, not model trials.
- Following the review edits, six viewport/theme combinations were checked again: 1024, 736 and 360 pixels, each light and dark. The 736-pixel layout now stacks the main panels to leave room for date and budget controls. Screenshots were visually reviewed before and after the adjustment.
- Covered: budget amount and basis; residential area separate from an unknown workplace; stale summary after edits; retained generated snapshots; unverified conditional evidence; unknown fields; invalid budget not replacing a summary; scenario switching; literal rendering of untrusted text; no script errors or external network requests in the observed interactions.
- No actor-model calls, live property research, Grok conversation or token comparison was run. The independent agent reviewed source and instructions only; this is not a zero-token claim about the development session itself.

Private browser logs and screenshots are retained under `.pea-playground/requirements-panel-20260911/`: `validation.json`, `destination-check.json` and `final-layout-check.json`. The last file also records a corrected QA assertion: it initially expected three matching history labels, while the actual markup correctly contains two. Product markup did not change to satisfy that assertion.

## Independent review and corrections

The independent reviewer found no P0/P1 issue within this limited source review and raised two P2 documentation/UI claims:

1. The form supports only the predefined dryness predicate. It cannot encode review Case A's combined bedroom-privacy and window-security conditions. The interface and README now say so; the actual agent must retain those conditions separately, without reducing them to unconditional acceptance.
2. History records generated-summary snapshots, not every edit or conversation turn. The interface and README now name that scope explicitly and require separate retention of original messages and corrections.

Root reviewed these findings and made both changes. Neither review proves the absence of other issues.

## Remaining limits and next acceptance step

This example has one destination, an exact-date control and a small set of predefined conditions. It has no model connection, persistent storage, verified commute, property research, authoritative-state import or automatic synchronization. Refreshing clears the page state. A current summary means it reflects the form revision, not that its housing claims have been verified.

The next step is one human-led Grok conversation using [the setup message](grok-start.md) and a single case from [the review guide](review-cases.md). Inspect the actual messages, current requirement file, report and next actions together. Preserve spontaneous questions and corrections. Stop and fix material state/evidence failures before expanding the test; record unavailable model/effort/tool/token metadata as unknown.
