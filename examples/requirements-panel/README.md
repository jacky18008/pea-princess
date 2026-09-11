# Requirements panel: interactive example and human-led test

This is a proposed interface for Pea Princess, not a replacement for the person's own agent. It supports a destination supplied as an address, station or district, including an unknown destination. An employer or school name is not required. The initial values are editable interface examples, not the current user's rental requirements or researched property data.

The panel edits a small demonstration record and generates a deterministic requirements summary from that record. It does not research homes, call a model, calculate real journeys, or synchronize with the production `.pea-state`. A generated summary can be current for its form revision without any housing condition being independently verified. Changing a field makes an earlier summary stale.

Open `index.html` in a browser; no server, account or installation is needed for the example. Edits stay in the page until it is refreshed. The expandable structured-text view can be copied deliberately for review. `panel.fragment.html` is the editable source; run `python3 examples/requirements-panel/build_preview.py` from the repository to refresh the standalone page after a source change. The optional inline layout-design control is absent outside hosts that provide it; normal form interactions still work.

## What to try

1. Start with the scenario that discloses only a work district. Enter a station or district directly without naming an employer.
2. Change the monthly amount and whether it covers rent alone or rent plus bills. Generate a requirements summary and check both values.
3. Set ground floor to conditional acceptance. Check that the condition remains visible and unknown evidence has not become a pass.
4. Edit the destination after generating a summary. The previous summary should be visibly out of date; regenerate it from the current requirements.
5. Try an unknown destination and a blank budget. These are missing information, not unlimited spending or permission to invent a workplace.

The controls are a way to inspect an agent's future structured record. They are not a required intake form. In the intended product, conversation and deliberate panel edits would update one authoritative project record. A person who never opens the panel can still use the skill.

This prototype only demonstrates the predefined dryness condition; it cannot represent arbitrary conditions such as bedroom privacy **and** lockable windows in review Case A. Keep those conditions in the agent's requirement file, never simplify them to unconditional ground-floor acceptance. The date control also accepts an exact date only; unknown days, months and date ranges need a richer representation before integration.

The history contains snapshots taken when a changed summary is generated. It is not a complete change log: intermediate edits, original messages and corrections must be captured separately in the real conversation test.

## Input design decisions

| Information | Representation and consequence |
| --- | --- |
| Commute destination | User-supplied text and explicit precision: address, station, area, or unknown. An address is not a verified geocode. |
| Preferred residential area | Separate from the commute destination. Wanting to live in Stratford does not mean working there. |
| Employer or school identity | Optional; never inferred from an address, and never a prerequisite for geographical research. |
| Several regular destinations | Preserve each separately with purpose and frequency. The current single-destination prototype does not implement this yet. |
| Budget | Amount, currency, period and basis belong together. A blank amount is unknown. |
| Conditional permission | Preserve the predicate and candidate scope. "Only if dry" remains conditional until supported evidence exists. |
| Voice correction | Save the actual received text and correction; do not claim access to the speaker's original audio unless it was provided. |

With only a district, research can compare areas and representative routes, identifying the chosen reference point and missing last leg. It cannot claim an exact door-to-door commute or mark the user's journey limit satisfied. Unknown arrival time, attendance frequency and commute mode can also affect the comparison; ask only when the next decision needs them.

## Test the real agent separately

Use [grok-start.md](grok-start.md) for a short setup message, then send the opening of **one** scenario from [review-cases.md](review-cases.md). Keep later corrections and review criteria out of the actor's initial context. Actual human wording and spontaneous questions are part of the evidence, not deviations that should be rewritten into a script.

Start with one conversation of roughly five or six user turns, then one different case if the first has no material state or evidence failure. This is a small functional and experience check, not a model/effort ablation, a token-saving result, or an equivalence study. No model run is launched by these files. Stop on provider limits rather than automatically retrying.

Grok Bot's official documentation describes [messages during ongoing work](https://docs.x.ai/grok-bot/chat-and-collaboration), [file inputs and reviewable outputs](https://docs.x.ai/grok-bot/files-and-results), and [saved skills](https://docs.x.ai/grok-bot/skills-routines-and-automations) (checked 2026-09-11). These support a human-led chat-and-files test. They do not establish that arbitrary interactive HTML executes in every preview, that all native questions offer free text, or that a cloud Bot can reach a laptop's localhost.

Local copies of the first two official pages are listed in [the saved-page index](../../docs/grok-reference-pages-2026-09-11.md), with original source URLs and retrieval metadata.

The previous native automation attempt produced [zero valid quality samples](../../docs/grok-native-followup-2026-09-11.md). Input corruption and an unverified installed package prevented a clean run. A new Bot also referenced older test context, so a new name alone is not proof of isolation. Record the package hash, actual workspace and any pre-existing context in a new test.

## What remains before a shared live dashboard

- Bind typed question IDs and answers to the existing revisioned requirement engine; do not flatten them into an untraceable string or create a second authority.
- Implement and test importing/exporting deliberate changes between the panel and an agent's workspace, including stale-version conflicts. This prototype has no automatic synchronization.
- Validate each host's available controls and file-preview behavior. Fall back to ordinary chat and readable files when a feature is absent.
- Extend the existing distinction between search-area preferences and commute obligations to multiple regular destinations with purpose and frequency.

For now, evaluate the interface here and the model's dialogue in its own host. Compare the actual conversation, current requirement file and report. A polished panel is not evidence that the agent followed the requirements.
