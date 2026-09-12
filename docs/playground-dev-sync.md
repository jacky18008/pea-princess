# Automatic local developer synchronization

Run `python3 tools/start_playground.py --port 8765` in the shared Git checkout.
The default launcher starts an owned, detached local supervisor. It watches the
indexed working bytes of the public package and allowlisted controller inputs,
including uncommitted edits and newly indexed paths. It does not launch a model.
Use `--source-root /absolute/repository` to watch a different shared checkout and
`--state-dir /absolute/private/state` to retain an existing conversation store.

The service continues after the launcher and calling terminal exit. This is a
local detached process, not an installed login service: logout, reboot, host
termination or supervisor failure can stop it. Run the start command again after
those events; no model call is recovered or retried by this supervisor. Changes
to the supervisor's own implementation take effect on a deliberate service
stop/start; refreshed actor/controller snapshots include their current bytes.

Use the same source-root, state-dir and port with:

- `--service status`: current state, exact snapshot, source digest and log path.
- `--service logs`: the last bounded portion of the private service log.
- `--service stop`: request a stop, deferred until active workers finish.
- `--service start`: start if stopped, otherwise report the existing service.

The service directory is `<state-dir>/dev-service-<port>/`. Status and logs are
private. Start never kills a process found merely by port or recorded PID. Stop
an old unmanaged lab deliberately before handing its port to this service. If
the supervisor dies but its child survives, the next service reports the occupied
port and blocks; inspect and stop that old process before restarting. Do not use
this developer service to claim arbitrary code edits received an independent
security review or a full test-suite pass.

## Refresh and dispatch contract

After two seconds with an unchanged digest, the supervisor runs the existing
public builder against the current indexed sources, directing outputs into a
private staging directory. Its dependency, public identity and prompt-size
checks still apply. It does not replace the repository's `dist` artifacts.
Generated ZIPs, generated prompt instructions, private histories, logs, caches,
untracked files and unrelated Git commits do not trigger rebuild loops. New untracked public files are not published: review and add intended files to the Git index. If an indexed script imports a locally present but untracked sibling, the freshness check visibly blocks and asks for that review; it does not read or automatically publish the omitted file.

Before and after building/freezing, it checks current input bytes. Freeze also
checks source stability, validates the archive and compares its public members
against source. The generated prompt instructions come from that same build.
Frozen Python files are syntax-checked without executing them. An edit during preparation prevents activation. A failed build leaves the last
runtime and historical records intact, marks the service as an error, and blocks
new dispatches. It attempts a given input digest once; fix a source input or
explicitly stop/start to try again. This is a build retry policy, never a model
retry policy.

A managed runtime manifest contains `dev_sync.source_root`, `source_digest` and
`service_dir`. `playground_dev_sync.source_status(runtime_root)` supplies the
catalog's read-only current/stale status, including unavailable source or service.
`dispatch_guard(runtime_root)` checks freshness and holds a shared file lock for
the **entire worker**, including preparation, physical calls and finalization.
The worker rechecks source status before each additional queued/replay call.
HTTP mutations hold `operation_guard`, a shared lease without a freshness check,
so pausing an active call and saving review notes remain possible while source
edits wait. Creating a test and preparing a model call separately require fresh
sources. Both leases last through durable state writes.
Source editors do not share this lock: it detects the source state when checked,
not a transactional lock on every concurrent editor's write.

The supervisor needs the corresponding exclusive lock before retiring its owned
server and starting the new frozen snapshot. While a worker is active it waits;
it never terminates a running model to install an update. While switching, guard
acquisition fails immediately. The server integration must use this guard on all
model-dispatch paths; merely showing a catalog badge does not enforce freshness.
The supervisor also verifies the new child is alive and listening before marking
it ready. An unexpected child exit is reported without automatic process retry.

A successful activation also retains a separate private `generation.json` receipt.
On deliberate stop/start with unchanged source, the supervisor verifies that
receipt's manifest hash, the complete frozen file inventory and hashes, current
controller bytes, the public archive, and source/state/service directory bindings.
It then starts the exact same snapshot: paths and manifest bytes remain unchanged,
so same-version conversations remain compatible. Status text alone never
establishes identity. A changed source/helper version builds a new generation;
corrupt retained evidence blocks reuse rather than silently rewriting it. Legacy
services without the generation receipt cannot retroactively establish this pin.

There is no automatic message, replay, retry, session migration or model call on
refresh. Historical sessions and exports retain their original snapshot identity.
Create a new session or explicitly replay saved human inputs on the new runtime
to evaluate updated behavior; an older answer is not relabeled as a new result.

## Pinned comparisons

`--skill-archive /path/to/release.zip` keeps the existing single foreground server
behavior, with an immutable explicitly selected archive and no watcher.
`--freeze-only` prints a snapshot receipt without starting any service or server;
its omitted-archive mode still requires a current prebuilt `dist` archive.
Pinned/unmanaged runtimes report that automatic synchronization is disabled,
not that their old package equals today's source.

Tests use mocked builds/servers and synthetic repositories; they test lifecycle,
locking, source identity and history preservation, not model answer quality.

## Research continuity in the agent test lane

The host exposes only `<session>/research-results` as the additional writable
directory and sets `VETFLAT_SCAN_RESULT_DIR` and `VETFLAT_RESEARCH_DEPTH`. Temporary
scratch files disappear after each call. The public `area_scan.py` saves private
envelopes containing the exact request, source identity, retrieval time, result
and hash. Repeating an identical scan reuses complete, partial or failed results;
in-flight matching work waits briefly and reports pending instead of duplicating
network work. An abandoned producer reports interruption, with no automatic retry.

Each subsequent prompt includes bounded verified metadata and exact paths, not
an invented prose summary. The model can read the original envelope's `result`
field. Hash checks establish unchanged bytes, not source truth, complete coverage
or bedroom-level certainty. Changed preferences alone do not make observations
newer. Each call's `research_results` in the export records the observations seen
after that call; failed supplementary observation writes remain explicit gaps
and do not suppress a completed paid answer.

The agent lane receives the actual public SKILL, rules and conversation-quality
references. Other documents load by task intent. The earlier extra conversation
policy and automatic intake/reference bundle are no longer injected here;
fixture and checked-delivery lanes retain their own contracts. This is a changed
prompt treatment, requiring model acceptance, not proven lossless compression.
