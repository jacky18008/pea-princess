# Terra actual replay and neighborhood diagnostic — 2026-09-12

The original two-turn conversation was actually replayed through the browser,
using the same human inputs and the exact two retained PDF snapshots. The new
comparison was factually consistent with the PDFs, but it used substantially
more processed tokens. A separately amended, explicit neighborhood probe did
invoke the scanner, but selected deep despite standard settings, duplicated
both scans, and exposed a scanner crash. This is not a successful cost-reduction
result or a full conversation-quality acceptance.

## What was fixed and pinned

Source, public ZIP and running runtime are different artifacts. The public ZIP
is built from the shared public source; the test server safely extracts that ZIP
into an immutable runtime. Existing conversations stay pinned so later edits do
not silently change a recorded experiment. The previous deployment updated the
controller while retaining an older ZIP, then missed rebuilding/restarting after
Claude's subsequent edits. This was a release handoff failure.

This experiment includes Claude's `c2124f7` change to keep street scanning in the
current agent thread and `1df20ce` addition of the before-sending checkpoint.
The complete experiment checkout was frozen at `f98b6da` before dispatch. Later
changes did not enter an active model call.

- Model: `gpt-5.6-terra`.
- Research depth: `standard`; reasoning effort: `low`, saved per call and bound
  to its request. These are requested settings, not independent provider attestation.
- Public ZIP: `fd8dfb713cbfd8d528772b548c6639e08c903b572316276464b5dca729721af1`.
- Runtime: `20260911T230128Z-6845ad85ccd3`.
- Runtime manifest: `ec63e7e2a0791cf0f202cffada91a037ddf118b31ab852a57d71e6c9eef5d96f`.
- All 100 archive members matched the reviewed source before publication.

The default launcher now compares the archive's member set and bytes with the
current indexed public source before and after freezing. Missing, extra or
changed files stop a default launch and identify the need to rebuild. Explicit
`--skill-archive PATH` remains an intentional way to select a historical artifact.
The manifest records which selection mode was used. This guard is commit
`52d3b4f`; it was merged while this experiment retained its earlier frozen runtime.
It does not hot-update a running conversation or automatically rebuild releases.

For routine updates: finish/review source edits, run checks, build with
`python3 tools/build_dist.py`, then start with `python3 tools/start_playground.py`
without an explicit historical archive. Wait for active calls to finish before
replacing the server. A UI refresh alone does not replace its running skill.

## Original two-turn replay

The first request prioritizes advertised rent, bedrooms and area. Quietness remains
an active preference; it is not waived. The second input contains only the two
PDFs. Original assistant answers are retained for comparison but are not supplied
to the new model. The follow-up inputs are historical, not fresh satisfaction
feedback on the new answers.

| Metric | Original two turns | New two turns |
| --- | ---: | ---: |
| Processed tokens | 225,270 | 558,933 |
| Input tokens | 221,636 | 552,122 |
| Cached input tokens | 132,864 | 450,688 |
| Uncached input tokens | 88,772 | 101,434 |
| Output tokens | 3,634 | 6,811 |
| Recorded shell invocations | 8 | 9 |
| Recorded neighborhood scans | 0 | 0 |

New turn 1 used 151,813 processed tokens in 45.3 seconds; turn 2 used 407,120 in
101.1 seconds. All request/result integrity checks passed. The new total is
148.1% higher in processed tokens, while uncached input is 14.3% higher. Cached
input is included in processed tokens; these figures do not establish a billing
or subscription-allowance multiplier. One run with several source/prompt changes
is not an isolated causal experiment or evidence of statistical equivalence.

The visible PDF comparison retained the correct advertised rents, bedroom counts
and areas, along with qualifiers about advertised area, availability and quietness.
The office address printed elsewhere in a brochure was not used as the flat's
address in the visible comparison. It still foregrounded access policy in turn 1,
and repeated “advertisement PDF” in table cells in turn 2. “Eligible” would be
clearer as “matches rent/bedroom criteria” in that limited comparison.

The absence of neighborhood scanning in these first two turns is not itself a
tool-selection failure: the first request explicitly prioritizes rent, bedrooms
and area, and the second supplies the PDFs. It does not establish inability to
scan or fulfillment of the still-active quietness preference.

The tool trace identifies concrete remaining problems:

1. The first shell command failed because relative globs were expanded outside
   the package. The model then listed reference files and printed 109,317
   characters from rules, axes and report instructions before asking for the pages.
2. The next turn reread instructions, including already supplied material, and
   attempted twelve nonexistent axis filenames. The combined shell command
   ultimately exited 0, masking its earlier missing-file errors.
3. A combined scan/calculation/render command returned only two generated image
   filenames. That output does not establish successful execution of the requested
   scans or arithmetic. The final reply omitted the computed differences.
4. The draft checker rejected uncited numeric table lines; the model added repeated
   source labels and removed computed comparisons. A later “clean” result proves
   neither factual verification nor useful, natural conversation.

Inspector previews truncate long bodies at their display limit. That boundary
must not be mistaken for what the model actually received. The underlying retained
tool events, not just the preview, were used to check commands and error lines.

## Protocol deviation and separate final probe

The original plan was three model replies: the two replayed inputs, followed by
an explicit neighborhood question. The second in-flight reply crossed the
400,000-token between-call gate. The original session was stopped after two calls;
its limits and records were not changed to force another dispatch.

To complete the requested neighborhood capability diagnosis, the third and final
native model call was prospectively redefined as a separate, single-turn street
probe. It uses the same two streets and rental preferences, same model/settings
and public ZIP, but explicitly asks only for neighborhood evidence. It receives
neither PDFs nor old assistant answers. Its one-call cap, 200,000-token between-call
threshold and 300-second timeout are saved in a separate protocol amendment. The
threshold is not a per-call token cap. No automatic retry is allowed.

This separate probe cannot establish successful continuation of the original
conversation, and its tokens must not be included in the two-turn comparison.
The separate probe finished in 227.1 seconds. It produced 15 completed tool-event
records: ten shell invocations, two web-search events containing five queries,
and three draft-file changes. No actor subagent dispatch was observed. Tool
event counts are not HTTP-request counts, and a top-level exit 0 is not evidence
that all commands in a compound shell invocation succeeded.

The raw terminal receipt contains 840,437 input tokens, including 768,000 cached
and 72,437 uncached, plus 6,639 output: **847,076 processed tokens**. It agrees
with the session receipt. The original Inspector packet instead marks usage
unknown; this discrepancy is retained and investigated separately below. None
of these tokens belongs in the matched two-turn comparison above. Development
and evaluator usage is separate from all three native actor calls.

## What the neighborhood probe actually demonstrated

| Priority | Observed issue | Consequence / disposition |
| --- | --- | --- |
| High for experiment validity | Both street commands explicitly used `--depth deep` despite recorded `standard`. | This does not test the planned standard execution. The injected instruction calls standard a baseline and permits explicit scope changes; the probe asks about rail/nighttime. This is not proof of violating a hard user cap. Effective depth and the reason for changing it were not separately recorded. |
| High | Two scans were started in a compound command; before waiting for it, the actor started both again. | Four scanner invocations for two streets. “Once per street” instructions did not prevent duplicate execution; a pending job must be awaited and its saved result reused. |
| High | Milton's summary crashed on `KeyError: 'decision_date'`. | Our formatter removed empty fields while compacting a row, then directly indexed them. This is a product bug, not proof that the public data source was unavailable. Otherwise usable partial results were lost. |
| Medium | Road noise is presented as three-point coverage, though two road Lden requests and one road Lnight request returned HTTP 403. | Successful coverage was one of three and two of three respectively. Answering with the surviving value is possible, but the missing coverage must be stated. |
| Medium | The reply calls Lden “daytime” / “whole-day average.” | The source defines a day/evening/night weighted indicator. The numbers match, but the explanation is imprecise and can mislead. |
| Medium | Planning retrieval covers the nearest 200 of 1,675 matches, extending to about 130 m within a requested 500 m radius; the reply omits this limit. | It is not a complete 500 m review. Distances refer to the selected street scan point, not an identified flat. |
| Lower | Repeated broad instruction/source reads, guessed filenames, draft-checker rewrites and a zsh reserved-variable error. | Extra work and awkward prose, while a clean reply-check result still fails to establish semantic quality. |

There was useful, grounded progress: Southerton's returned JSON supports the
reported main-road and surface-tube distances and numeric noise values. The reply
distinguishes planning approval from actual construction, and missing map tags
from proven absence of nightlife. It does not rank Milton quieter because its
scan failed. Both the exact flat location and its indoor acoustic performance
remain unverified.

Search-event records retain queries but not result bodies. Accordingly, a further
Haringey document claim and the initial postcode search cannot be independently
verified from those search records alone. Generic source endpoint links are not
claim-level evidence. The retained successful scan result is available for audit;
it must not be replaced with a later live lookup and called the original result.

The independent GPT-6 Astra evaluator reached the same overall conclusion:
basic PDF comparison passes with minor presentation issues; actual scan selection
is demonstrated; the planned fixed-standard run and a complete two-street investigation
fail. The original continuous three-turn journey was not completed. No quality
equivalence or token savings claim is warranted.

## Review-process findings and next work

The root review checked retained full tool events, exact attachment bytes, terminal
counters and visible replies separately from the evaluator's judgment. A preliminary
evaluator interpretation confused Inspector display truncation with model-input
truncation; it was withdrawn after checking the underlying event. This correction
is retained in the private review, rather than silently deleting disagreement.

The cost evidence points to repeated instruction reads, duplicated scans, tool
errors and checker-driven rewrites as observed extra work. It does not isolate
their individual token contributions. Removing them should be evaluated in a
small new frozen case; the old results must not be relabeled as the fixed version.

The root also found a calibration issue in the initial depth finding: the actor's
instruction says baseline, not an immutable ceiling, and the probe asks for checks
available in deep. Calling this an unauthorized escalation overstates the evidence.
The demonstrated issue is that requested baseline, effective tool depth and scope
change were not reconciled in the record, so it cannot validate standard use/cost.
This distinction matters for legitimate mid-conversation changes in user priorities.
The evaluator appended a correction and rates this as a moderate protocol and
traceability mismatch, not proven violation of a hard user spending limit.

One root-authored review was entered through the human form, which hardcodes the
reviewer label as human despite the note explicitly saying it was AI review.
The append-only record is retained, with an agent-labelled correction and a
private machine-readable exclusion from human-response metrics. Both notes are
AI feedback. Agent reviewers should use the reviews API with `reviewer: agent`.

Before another quality run, prioritize the formatter crash, explicit effective-depth
and scope-change recording, pending-scan/result reuse, and partial source coverage.
An experiment that requires fixed depth must state it to the actor and check it;
the product must continue to support explicitly authorized changes of scope.
Do not solve this by merely adding another long prose instruction. This turn
stopped at three new native calls, with no Claude calls or automatic model retries.

## Fixes shipped after the actor run

- `188d01a` fixes the nullable/omitted planning-field crash, retains known zero
  distances, avoids treating unknown distances as zero coverage, and keeps
  unidentified planning rows distinct. Seven new offline regressions include
  a mocked complete scan path that retains the other registers' results.
- `3f40ea4` fixes Inspector's usage interpretation. Four web-search item events
  have duplicate nested JSON keys. The reader can identify their unique,
  non-terminal envelopes without accepting the ambiguous payloads. It retains
  four explicit integrity warnings, while independently validating the unique
  strict terminal event against the stored direct counters. Malformed/ambiguous
  terminal data, ambiguous outer event types and inconsistent counters still
  produce unknown usage. Saved raw events are never rewritten.

The original Inspector packets remain unchanged. Reinspection through the actual
server API now reports 847,076 processed tokens for the probe and still flags the
four tool-payload gaps. The two earlier calls retain their original verified
usage. All 24 pre-existing session files, original PDFs/replay copies and new
physical checkpoint hashes were checked unchanged after restarting.

The merged source `3f40ea4` passed **2,571 offline tests** in 112.569 seconds.
All 767 tracked source files remained byte-identical throughout that check.
The rebuilt 100-member public ZIP is
`6df6f79a428a3bca5dae1568902f66583e3c58dd97811a8356ac3574fe73b6f3`.
Default freeze verified it against current source and created runtime
`20260911T233254Z-56ffdba4be2b`, manifest
`2f9f35f037e2d8514d153dd83cc582bda8f0375aa4de48c25c646a1e1af00ba4`.
The local test server was restarted on this package after confirming no active
call. A real stale-ZIP startup attempt before rebuilding was rejected and named
`scripts/area_scan.py`, demonstrating the release guard on the changed artifact.

This later release received no additional native model call. It fixes the observed
code defects; it does not establish repaired conversation quality, eliminate
duplicate scans, or validate standard-depth cost. The three retained actor
responses continue to belong to the earlier `fd8dfb…` archive.

## Validation and retention

The exact experiment checkout passed 2,551 offline tests, with 17 skipped, before
dispatch. The startup guard passed its own full suite of 2,560 tests, 17 skipped;
the nine new guard tests also passed after merge. A default freeze on the actual
main checkout confirmed current-source verification without changing the running
experiment. No Claude model was dispatched.

Private plans, unchanged original session hashes, PDF verification/page text,
conversation exports, full physical-call records, Inspector packets and independent
Astra/root reviews are retained in the ignored local experiment directory. They
are not public package members. Native actor usage above excludes the development
and reviewer agents' own work.
