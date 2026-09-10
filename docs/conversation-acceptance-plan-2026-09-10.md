# Conversation acceptance: frozen protocol v1

This is a new, bounded product acceptance study. It does not extend the closed
192-slot ablation or the seven-call waste probe. Claude remains paused.

## What must pass

The first visible assistant sentence must be polished, warm and useful: an
evidence-grounded observation, comparison or direct answer that makes continuing
worthwhile. A process announcement followed by a good final answer does not pass.
Every turn separately needs an answer to the current request, useful progress,
plain language and appropriate clarification. Correctness cannot compensate for
a failed experience gate. Length and question counts are diagnostic only.

Known mandatory conditions must be checked by the shipped deterministic eligibility
tool. The runner independently recomputes results from operator-pinned constraints
and evidence, then validates the saved ranking, first choice, outstanding checks
and TODOs. It also reviews the actual prose and durable state; valid JSON alone is
insufficient. Estimates and unverified conditions cannot become verified passes.
An exception needs the user's exact authorization, scope and required evidence.

## Fixed scope and limits

| Item | Bound |
| --- | --- |
| Actor | GPT-6 Astra, low effort, same frozen skill and local tool corpus |
| Core | Three independent owned sessions, six user turns each |
| Scenarios | Vague novice needs; an interruption and changed priorities; tightening/relaxing budget, scoped exception and restart |
| Transport qualification | Two additional calls in a separate owned session |
| Total launch ceiling | 26: two qualification, 18 core, at most six explicitly versioned repair checks |
| Usage stop | Before another dispatch when summed raw terminal input + output counters reach 8,000,000 |
| Per-call timeout | 360 seconds; no automatic retry |
| Other models | No Claude, no second actor model, no expansion of the old matrix |

The usage ceiling is an operator stopping rule, not an estimate or a new user
spending budget. Native counter scope must be investigated during qualification.
Until established, the sum is a conservative counter-based stop metric, **not an
exact processed-token, monetary-cost or subscription-limit claim**. Cached input
is not added twice. Missing usage blocks subsequent dispatch globally. One running
call can exceed the stop threshold. Root and evaluator usage is outside this CLI
ledger and must be disclosed separately as unavailable when not measured.

## Evidence and transport

The three authored conversations use new fictional candidate/source packets that
were not supplied to the prompt/rubric implementation agent. They are frozen,
hashed and released turn by turn; future messages and evidence are absent from
the actor workspace until scheduled. These are authored user responses, not
observed customer satisfaction. Real user interventions, if any, are recorded
separately and can create an explicit protocol amendment.

The actor has native local file and shell tools and the delivered skill scripts.
It researches the supplied source documents, computes costs, persists conditions,
and writes actual artifacts. This controlled acceptance does **not** establish
live property discovery, native clarification UI, mobile support or live web
research quality. No network, messaging, additional models or unrelated host
files are part of the task. Workspace-write and disabled discovery are not an OS
read-isolation boundary.

The host, rather than the actor, captures each authored user message and supplies
its reviewed normalized conditions to SessionStore before dispatch. It pins these
inputs outside the actor workspace and rejects actor changes to them. This tests
enforcement of already-known conditions; it does not establish the accuracy of an
automatic natural-language intent extractor. Source truth and free-text advice
still require independent review. The shipped conversation guide is injected
once at session start, so the first progress sentence is governed before a tool
read can happen. Later turns resume without replaying that guide or dialogue.

Start each session without `--ephemeral`, bind its own `thread.started` UUID,
then use only explicit UUID resume. Supply the new turn and current authoritative
input pointers, without repeating the full dialogue. Restart the controller
process before the scheduled recovery turn and reload its manifest from disk.
This tests same-thread restart plus file consistency, not a forced native compact
or an interruption during an executing model turn. Record the exact command,
runtime pins, source hashes, every input, raw stream, visible assistant message,
usage event and before/after workspace snapshot. Native persisted account-side
session storage is an additional private surface; never enumerate other sessions
or copy authentication to obtain it.

The local CLI exposes exact-session resume. Official documentation describes
JSONL events and explicit-session continuation but does not by itself establish
the accounting scope in this experiment. See [OpenAI's non-interactive mode
documentation](https://learn.chatgpt.com/docs/non-interactive-mode), inspected
2026-09-10, and the [earlier read-only design](native-continuity-followup.md).

## Stop, repair and independent evaluation

Dispatch one turn at a time after a saved root review of the preceding result.
Transport, UUID, source-pin, pending-call, unknown-usage or global-budget failures
stop all dispatches. A failed eligibility/prose/state check stops dependent turns
of that case; the other independent frozen cases may proceed after a recorded
root decision. Preserve every failed attempt. Do not count blocked turns as passes.

If a repair is warranted, save the original result, make a new source commit and
protocol amendment, and use at most the six reserved calls for targeted checks in
new owned sessions. They are repair evidence, not a clean rerun of all three
conversations or an A/B saving estimate. Further calls need a separately reviewed
plan; this script cannot silently enlarge the ceiling.

After completion, an independent GPT-6 Astra subagent receives the complete
dialogues, first visible messages, source packets, state and artifacts, together
with the versioned UX rubric. It sees neither expected rankings nor cost-based
treatment labels before grading. The root separately checks the actual evidence
and evaluator process; disagreement and missing evidence remain visible. Report
per-turn UX vetoes, final task/state results and limitations, not just an average.
Passing these three small cases permits scoped local acceptance, not a claim of
quality equivalence across models, research depths or long production histories.
