#!/usr/bin/env python3
"""Archive a completed, committed ablation run locally; never runs a model."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
DOCS = Path(__file__).resolve().parent
RAW = ROOT / "bench/results/ablation-2026-09-09"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def command(*args):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((RAW / "live-v1/summary.json").read_text())
    if not summary["complete"] or not summary["usage_coverage_complete"]:
        raise SystemExit("Run must be complete with full usage coverage.")
    if command("git", "status", "--porcelain").stdout.strip():
        raise SystemExit("Commit the completed report first; worktree must be clean.")
    destination = args.destination.expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise SystemExit("Backup destination must be outside the repository and its raw input tree.")
    if destination.exists():
        raise SystemExit("Refuse to overwrite an existing backup.")
    os.umask(0o077)
    destination.mkdir(mode=0o700)
    source_commit = command("git", "rev-parse", "HEAD").stdout.strip()

    old = json.loads((DOCS / "validation-before-live.json").read_text())
    old_checks = []
    for entry in old["previous_artifact_integrity"]:
        saved = json.loads(Path(entry["inventory"]).read_text())
        expected = {r["path"]: r["sha256"] for r in saved} if isinstance(saved, list) else saved
        changed = [p for p, digest in expected.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
        old_checks.append({"inventory": entry["inventory"], "files": len(expected), "changed_or_missing": changed})
    changed_sources = [p for p, digest in old["source_sha256"].items() if sha(ROOT / p) != digest]
    if any(r["changed_or_missing"] for r in old_checks) or changed_sources:
        raise SystemExit("Historical or frozen-source integrity failure; backup remains incomplete.")
    write(destination / "preservation-checks.json", {"historical_artifacts": old_checks, "frozen_sources_changed": changed_sources})

    nodes = sorted(RAW.rglob("*"))
    if any(p.is_symlink() for p in nodes):
        raise SystemExit("Unexpected symlink in raw artifact tree.")
    files = [p for p in nodes if p.is_file()]
    inventory = {str(p.relative_to(ROOT)): sha(p) for p in files}
    write(destination / "raw-file-inventory.json", inventory)
    raw_tar = destination / "raw-artifacts.tar.gz"
    with tarfile.open(raw_tar, "w:gz") as archive:
        for path in files:
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    with tarfile.open(raw_tar, "r:gz") as archive:
        restored = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                    for m in archive.getmembers() if m.isfile()}
    if restored != inventory or any(sha(ROOT / p) != digest for p, digest in inventory.items()):
        raise SystemExit("Raw archive verification failed or source changed while archiving.")

    source_tar = destination / "source-HEAD.tar.gz"
    command("git", "archive", "--format=tar.gz", "--output=" + str(source_tar), source_commit)
    tracked = command("git", "ls-tree", "-r", "--name-only", source_commit).stdout.splitlines()
    source_inventory = {p: sha(ROOT / p) for p in tracked}
    with tarfile.open(source_tar, "r:gz") as archive:
        restored_source = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                           for m in archive.getmembers() if m.isfile()}
    if restored_source != source_inventory:
        raise SystemExit("Source archive differs from the committed source inventory.")
    write(destination / "source-file-inventory.json", source_inventory)
    bundle = destination / "repository.bundle"
    command("git", "bundle", "create", str(bundle), "--all")
    verify = command("git", "bundle", "verify", str(bundle))
    (destination / "bundle-verification.txt").write_text(verify.stdout + verify.stderr)
    (destination / "README.md").write_text(
        "# Completed ablation study backup\n\n"
        "COMPLETED.json records the exact result commit and verified archive hashes. "
        "raw-artifacts.tar.gz contains this study's raw artifacts; repository.bundle retains Git history. "
        "Earlier studies remain in their separate backups listed in preservation-checks.json; "
        "those historical raw files are not duplicated inside this tar.\n\n"
        "To restore into a NEW directory, clone repository.bundle, then extract raw-artifacts.tar.gz "
        "into that clone. Do not overwrite an existing working tree. "
        "The source-HEAD.tar.gz archive is an additional exact snapshot of the committed files.\n\n"
        "Offline reproduction commands are in docs/ablation-2026-09-09/results.md. "
        "No Claude calls were made; the original seven Claude confirmations remain paused.\n"
    )
    write(destination / "COMPLETED.json", {
        "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository": str(ROOT), "source_commit": source_commit,
        "preregistered_source_commit": summary["source_commit"],
        "raw_files": len(inventory), "source_files": len(source_inventory),
        "raw_archive_sha256": sha(raw_tar), "source_archive_sha256": sha(source_tar), "bundle_sha256": sha(bundle),
        "calls": summary["calls"], "processed_tokens": summary["known_cli_processed_tokens"],
        "raw_archive_verified": True, "source_archive_verified": True, "git_bundle_verified": True,
        "historical_files_unchanged": sum(r["files"] for r in old_checks),
        "claude_calls": 0, "original_claude_confirmations_remain_paused": 7,
        "accounting_scope": "Measured CLI invocations only; parent conversation and review/documentation agents excluded. Processed tokens are not billing or quota.",
    })
    hashes = {p.name: sha(p) for p in sorted(destination.iterdir()) if p.is_file()}
    (destination / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in hashes.items()))
    print(json.dumps({"backup": str(destination), "source_commit": source_commit,
                      "raw_files": len(inventory), "source_files": len(source_inventory)}, indent=2))


if __name__ == "__main__":
    main()
