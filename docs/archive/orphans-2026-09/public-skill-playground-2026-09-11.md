# Public skill connected to the local test interface

The test interface now loads the exact public `dist/pea-princess-skill.zip` for new conversations and replays. The live responder uses the extracted `skills/pea-princess/` directory, including its references, scripts and viewer. Synthetic persona tests also take their injected instructions from this archive. The legacy source directory supplies controller imports only; installed host skills are not the actor target.

## Pinned version

- Implementation commit in the working repository: `7e48de6` (isolated implementation: `846f8af`).
- ZIP SHA-256: `cc5b7886a04fb60b95f96b71127dc3be3a43601a4231eb4e3d38c89730659eb8`.
- Public files: **99**, verified individually against the retained archive.
- SKILL.md SHA-256: `3c897b3ffd5adcb3e435d420bbd0fadcbff8aa4dd3a0c52d2964bed00f61df62`.
- Deployed snapshot: `.pea-playground/runtime/20260911T215639Z-16b4e2fbbb9e`.

The ZIP was not rebuilt or modified. Concurrent untracked `noise.py` development was preserved and was not silently added to the tested public archive. The snapshot manifest pins both the controller implementation and the separate public artifact.

## Using it

Open or refresh `http://127.0.0.1:8765/`. The creation panel displays `pea-princess 公開 ZIP · cc5b7886a04f`; expand it for the full hash. Create a conversation and press **研究並回覆**, or select an existing conversation and choose **用新版重測**. A selected conversation displays its own saved version. Older records without this provenance stay labelled older/unverified, even when the current server uses the public ZIP.

The 21 existing conversation files were verified byte-for-byte unchanged after restart. Reading, exporting, creating a conversation and preparing a replay do not dispatch a model. Explicit research/step/run/send actions use the selected model and recorded limits. This change does not alter those limits or convert the processed-token threshold into a hard provider billing cap.

## Verification

- **198 relevant offline tests passed**: 158 playground tests, 31 persona-playground tests and 9 live-research tests. These include ZIP safety/integrity, source changes during startup, immutable staging cleanup, prompt routing, historical provenance, file inputs, replay and UI behavior.
- An independent reviewer ran 26 focused checks and found no unresolved P1/P2 issues after fixes.
- A frozen copy of the actual 99-file public ZIP loaded all 16 persona instruction sets. Both `area_scan.py --help` and `reply_check.py --help` ran successfully without network access.
- A separate browser server completed create → answer → replay → answer using two deterministic callbacks. No native model was called. The first browser assertion expected the wrong progress wording and timed out after both callbacks had completed; read-only checks then confirmed both records without repeating calls. No browser JavaScript errors were observed.
- The deployed server's catalog, live prompt path and embedded SKILL.md were checked against the public archive. Old session hashes were compared before and after restart.

Private evidence is retained in `.pea-playground/public-skill-ui-20260911/`, including freeze manifests, browser screenshot, callback records, test log and deployment/session-hash checks. It is ignored by Git and not included in the public package.

## Scope

This verifies version selection and functioning test transport, not model reply quality, token savings or equivalence across native agent products. The lab still adds its conversation policy, context/receipt controller and tool settings. Live calls use the existing workspace-write/network sandbox so shipped scripts can retrieve permitted public data; their cache and temporary files stay in the call workspace, which is deleted afterward. The actor must return useful results in its reply rather than claim those temporary files are persistent reports. Package files/directories are read-only, and Python bytecode writing is disabled for the actor process. Same-user filesystem isolation is not guaranteed by these instructions.

Startup retains the selected ZIP and rejects unsafe entries, conflicting paths, wrong skill identity and altered extracted content. A frozen runtime with a missing or altered public artifact fails rather than selecting development or installed skills. To test another existing public ZIP, restart through `tools/start_playground.py --skill-archive /absolute/path/pea-princess-skill.zip` and create a new conversation or replay.
