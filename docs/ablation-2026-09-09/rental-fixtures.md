# Two-turn synthetic rental fixtures · 2026-09-09

`evals/ablation-2026-09-09/rental-cases.json` contains three new fictional rental
histories, each followed by two sequential user turns. All addresses, people,
organisations, documents, observations, bank details and figures are invented.
The setup agent authored histories, later turns, gold and scalar fact checks
together before any target outputs. These are authored pilot cases, not organic
production conversations, independent real-user holdouts or reused persona cards.

No handoff, compressed memory or target answer is included. The separate runner
will generate and update narrative/structured memories live. Those calls and
answer calls belong to its measured workload; current-agent fixture authorship
and review belong to setup and must be disclosed separately. No target-model or
Claude calls, real property lookups, external messages, transfers or bookings were
made in fixture creation. No skill or runner file was modified.

| Case | History messages | History characters | T1 / T2 characters | Decision dependency |
| --- | ---: | ---: | ---: | --- |
| S1 | 10 | 5,704 | 629 / 790 | User threshold versus property area; replaced cost basis; later replacement of two quote components |
| S2 | 10 | 5,675 | 649 / 1,057 | New zero-step requirement; operating state versus lift existence; dated repair and direct route observation versus a later-forwarded old notice |
| S3 | 10 | 5,752 | 532 / 1,537 | Exact-unit identity, recipient/authority and written terms; promised versus completed checks; expired quote versus an unbooked replacement fallback |

Counts exclude JSON formatting, IDs and role labels. Each history has five user
and five assistant messages. Historical assistant replies provide conversation
context only: they are not authoritative evidence. S1 deliberately contains an
assistant mistake that confuses a property's certificate area with the user's
minimum; the user corrects it before T1 then explicitly replaces that minimum in
T1. Later model answers must not acquire authority merely by being repeated.

Every turn has exactly five always-applicable findings and six exact scalar fact
checks. There are 30 findings and 36 fact checks across the set. Finding IDs are
globally unique (`S1-T1-F1`, etc.); user-message IDs are local to each case.
Every evidence reference resolves to `U1`–`U5`, `T1`, or `T2`. T1 never references
T2, and neither gold nor fact checks reference an assistant message, generated
answer or generated memory. Evaluate T2 against the original user evidence plus
T1 and T2, not against the memory generated for any experimental arm.

The final user turns explicitly request every scalar being checked. Numeric
expected values are plain strings with units in their keys; dates use
`YYYY-MM-DD`, and S3's known refund cutoff uses `YYYY-MM-DD HH:MM`. Other scalar
values have source-specific meanings, such as the current documented lift
status or the named payee on the current invoice. The checks are factual targets,
not a requirement to print a particular JSON schema or repeat the gold. A grader
should distinguish a semantically equivalent date/number presentation from an
actual wrong fact. Source provenance and estimates still matter when scalar
values happen to match.

The tasks require decisions, not only extraction:

- S1 T1 favours Pennythorn for a viewing under the updated all-in cap. T2 changes
  the relevant rent/utility entries, reversing the provisional viewing priority
  to Mosslantern. T2 says the previous message's funding/layout requirements still
  apply without repeating their numbers, so the £2,130 cap, 41 m² minimum and studio
  acceptance must be retained from T1. The prior answer remains a legitimate
  conversation aid in every arm, but it is not authoritative source evidence.
- S2 T1 supports neither unit as meeting the new access requirement. T2 provides
  a dated operating release and the user's successful complete route test, so
  progressing Flat 10 to a full viewing is supported. A forwarded older fault
  notice is not a newly observed fault. This is approval of a viewing on access
  evidence, not a promise of future lift reliability or complete tenancy approval.
- S3 T1 requires holding payment while verification is missing. T2 supplies the
  missing exact-unit, authority, recipient and written-term evidence, permitting
  progress to final tenancy-pack review. It explicitly authorises no payment or
  signature. The replacement fallback remains subject to availability and
  unbooked, though its refund cutoff is now supplied.

These positive-progress situations prevent an always-hold response from receiving
full credit. A correct response may still qualify remaining uncertainty; neither
approval control establishes a comprehensive legal, safety or property PASS.
All criteria concern the requested decisions and explicitly requested facts.
They do not require a recital of every unchanged profile field or irrelevant
due-diligence axis, and there are no conditional denominator exclusions.

Arithmetic was checked directly before running: S1's initial comparable totals
are £2,160 and £2,095; its updated totals are £2,080 and £2,175 against £2,130.
S3's supplied all-in estimate is £2,160. Structural validation passed for exact
schema, three case IDs, ten alternating messages per history, 5,000–7,000 history
characters, two turns per case, five findings and six scalars per turn, unique
finding/field IDs, valid severities and user-only evidence references. Source
read-through checked that superseded values remain attributable and no current
decision is pre-written as an answer in a supplied source document.

The repository's actual `dist/prompt-pack/INSTRUCTIONS.md` was read to align the
manual-mode tasks with the skill's evidence and verification intent. Its legal
and full-report instructions do not make these fictional next-turn cases an
evaluation of current law or the full tool-enabled skill. No new legal research
is needed to decide the given scope. The histories and user requests are English.
The benchmark remains a small, single-author synthetic pilot; live compression
results will not establish safety for arbitrary rental conversations.
