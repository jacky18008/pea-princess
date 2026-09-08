# Independent saved-run audit — 2026-09-08

**PASS with recorded diagnostics.** The 38 saved calls in `bench/results/context-quality-2026-09-08/live-v1` have one successful `turn.completed` event each. Independent reconstruction found no token-accounting, frozen-source, prompt-packet, answer-aggregation, judgment-mapping or summary discrepancy. This audit made **0 new model calls**, changed no source or run artifacts, and reran no experiment.

The audit did not import or execute `context_quality.py` or `launch.py`. It parsed each raw `events.jsonl`, read **only that call’s direct terminal `usage`** for accounting, and used normalized records only as comparison targets. Every direct field is present and a nonnegative integer; cache input is within input, and reasoning output is within output. No fallback usage or unknown-as-zero substitution was needed.

## Exact processed-token totals

| Group | CLI calls | Input | Cached input (subset) | Output | Input + output |
| --- | ---: | ---: | ---: | ---: | ---: |
| analysis/full | 4 | 66,709 | 24,064 | 3,346 | 70,055 |
| analysis/summary | 4 | 59,073 | 24,064 | 2,223 | 61,296 |
| analysis/adaptive | 8 | 123,713 | 48,128 | 3,476 | 127,189 |
| rental/full | 6 | 106,135 | 12,032 | 2,434 | 108,569 |
| rental/compact | 6 | 100,008 | 24,064 | 2,126 | 102,134 |
| Judges | 10 | 184,001 | 0 | 16,482 | 200,483 |
| All calls | 38 | 639,639 | 132,352 | 30,087 | 669,726 |

The 28 answer calls total **469,243** processed tokens; the 10 judge calls add **200,483**, for **669,726** overall. Overall uncached input is **507,287**. Reasoning output is **6,482**, already included in the 30,087 output tokens. Cached input is already included in input. Neither subset is added twice. The records contain no invoice, USD price or subscription allowance measure.

All four adaptive tasks made both a selection call and a retrieved-document answer call. Their first calls total **59,631** and their follow-ups **67,558**, totaling **127,189**. The final-answer aggregates include both phases in every case. There are 24 answer tasks, 28 answer CLI calls and 10 judge calls; all call directories and raw thread IDs are unique, and the run log follows the frozen job order. No extra saved retry was found. The 38-call cap and 900,000-token stop threshold were respected.

## Models and diagnostics

The actual saved command arguments specify `codex exec --model gpt-5.6-terra` **28 times** and `gpt-5.6-sol` **10 times**, all at low effort with the saved read-only/ephemeral controls. They agree with the plan and each result record. No Claude command/model or native tool event appears. The raw events do not independently attest a resolved provider model version beyond these CLI requests.

There are **0 raw `error`/`turn.failed` events, 0 malformed event lines, 0 nonzero exit codes and 0 call timeouts**. This does **not** mean stderr was empty: all **38 stderr files** contain “Reading additional input from stdin...”, and **34** additionally contain one model-catalog refresh timeout diagnostic. No other stderr diagnostic was found. The catalog message says the available-model refresh timed out waiting for a child process; the corresponding generation still completed successfully with direct usage. The audit does not attribute wall time to that message.

## Integrity and result checks

- All **6 source hashes**, **3 prepared-copy hashes** and **152 recorded per-call artifact hashes** match. Five versioned sources also match the frozen source commit; the generated `dist/prompt-pack/INSTRUCTIONS.md` is checked by its frozen hash, not a Git blob.
- All **38 command prompts** match their prompt files. All **28 target packets** match the intended frozen full/summary/handoff or requested-document input. Adaptive requests respect one retrieval round and at most two catalogued documents; final responses request none. Rental calls include the identical fixed instructions.
- All **10 judge packets** contain the frozen source/gold and correctly masked terminal answers. All ten review packets contain identical evidence and candidates after normalizing their top-level `case` field name. Raw judge labels, applicable criteria, scores and critical misses map exactly into the saved judgments and all five summary arms. This validates aggregation, not semantic correctness of the judge.
- All **24 answer usage aggregates** match the direct call sums. Overall and judge totals match `summary.json` exactly. Terminal message JSON, saved `answer.txt` and result-record answers agree in every call.
- The analysis outputs contain **107 citations: 104 valid supplied excerpts and 3 invalid exact excerpts**, all three in `A2-full`, matching the saved checks. Excerpt membership does not establish semantic support. The failing excerpts are listed below.
- Rental format checks pass: `R3-full` and `R3-compact` each contain six bullets; `R4-full` is **164 words** and `R4-compact` **159 words**, each with exactly three numbered checks. Word counts use whitespace-separated words. These checks do not replace substantive review.

- `A2-D01`: `這些 pass 標籤是便利擷取腳本的初步輸出`
- `A2-D01`: `未重播對話或在發布前檢查參數`
- `A2-D02`: `沒有較後的使用者批准或第二次報價呼叫`

## Evidence and limits

The [machine-readable audit](independent-run-audit-2026-09-08.json) contains every call’s direct usage and artifact hashes, source checks, per-answer sums, citation failures, rental counts, and all 34 diagnostic lines with their file paths. It also records a digest over the run’s 316-file path/hash inventory.

- Frozen source commit: `d01c369a7d863aa920d8d90c0c2ec563228b8478`.
- Plan SHA-256: `388b002c8a2468ba87970c66fb881159c415f0c8fad1bcf669afbf2e85a7c15f`.
- Summary SHA-256: `c52223b74d353d5ca81c093dcc9e04ebba84ba5f2be712ee918571d470434572`.
- Run inventory digest: `58ddf8d14c2f9c222e1e4b7f5f96a374090c57033469a9d17a84268b1a30d2dd`.

The audit verifies the saved run’s accounting and record consistency. It does not independently adjudicate every substantive finding, certify model-judge labels as ground truth, establish production behavior, measure external legal accuracy, or rule out unrecorded activity elsewhere. Setup, authored-summary creation and manual-review computation remain outside these live CLI totals.
