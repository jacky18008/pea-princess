# Claude → Codex handoff checkpoint · 2026-09-08

The handoff begins at `8126037ef68caf9ca85ed2fc8bfe19af17029985` on `main`.
Both this checkout and `pea-princess-skillfix` were clean. The second skill fix is
already merged; the worktree branch remains at `20b46dd`. No running process was
found for this repository's experiment runners. Other Claude tasks were left alone.

## Recoverable local snapshot

Backup: `/Users/chenhsienhao/Documents/pea-princess-handoff-20260908T113914Z`.

- `history.bundle`: all Git refs and reachable history; `git bundle verify` passed.
- `source-8126037.tar.gz`: exact tracked source at handoff.
- `local-experiment-artifacts.tar.gz`: ignored `bench/results`, private benchmark inputs,
  previous `dist`, and all pinned skill exports. All **2,060** regular files were
  checked against their archive contents with SHA-256.
- `artifact-inventory.json`: individual artifact sizes and SHA-256 digests.
- `git-state.txt`: refs, worktrees, initial status, and complete reachable commit log.
- `claude-handoff-transcript.txt`: the user's supplied final Claude output.
- `experiment-scratch-supplement.tar.gz`: temporary experiment chain scripts,
  retained A/B logs, saved pre-change scorecards, and pipeline diagnosis.
- `SHA256.json`: file-level checksums for the backup.

The hashes and location are committed in `2026-09-08-backup.json`. The raw archive
is local and is not included in Git; copying the repository alone does **not** copy
these raw records. To reconstruct elsewhere, clone `history.bundle`, then extract
the experiment archive into the clone. Preserve the private input directory's
existing ignored status. No remote is configured and no push or publication occurred.

## Completed before runner changes

- `python3 -m unittest discover -s tests -p 'test_*.py'`: **1,558 tests passed**,
  13.181 seconds. Existing unclosed-file `ResourceWarning`s were emitted.
- `python3 tools/build_dist.py`: passed; ZIP 559,312 bytes, manual instructions
  7,980 characters (8,000-character ceiling), 56 checksum entries.
- `python3 tools/copy_deck.py apply --dry-run`: every block matches its source.
- `python3 viewer/build_viewer.py --check`: generated viewer is current.

## Paused work

The first matrix and first-fix matrix each contain 32 graded sessions. The second-fix
confirmation attempted seven sessions, all ending in provider/network failure;
those failures do not measure skill quality. Only P1 baseline produced a first
reply before failing on turn 2.

Pending seed-1 sessions: P1 baseline, P3 baseline, P4 baseline and probe,
P5 baseline and probe, P8 baseline. Keep the existing model/skill experimental
conditions when resuming. A replacement model would be a new experiment.

Claude's last user-visible message reported a weekly reset on **2026-09-11 at
05:00 Europe/London (04:00 UTC)**. This is the supplied transcript's report, not
a fresh account-status check. All Claude-dependent model calls remain paused;
no paid API fallback was activated. Offline regrading, usage auditing, runner
safeguards and the final validation are recorded in the other handoff documents.
