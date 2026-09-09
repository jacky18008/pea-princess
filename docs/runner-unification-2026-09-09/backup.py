#!/usr/bin/env python3
"""Create and verify a private, local restoration snapshot. No network calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def command(root, *args):
    return subprocess.check_output(args, cwd=root, stderr=subprocess.PIPE).decode().strip()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = args.output.resolve()
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    out.chmod(0o700)
    if (out / "COMPLETED.json").exists():
        raise SystemExit("Refuse to replace a completed backup")
    if command(root, "git", "status", "--porcelain"):
        raise SystemExit("Commit the complete delivery before taking its restoration snapshot")
    head = command(root, "git", "rev-parse", "HEAD")
    baseline = json.loads((out / "historical-baseline.json").read_text())
    changed = [p for p, expected in baseline["historical_files"].items()
               if not (root / p).is_file() or sha(root / p) != expected]
    if changed:
        raise SystemExit("Historical artifacts changed: " + repr(changed[:10]))
    bundle = out / "delivery.bundle"
    subprocess.run(["git", "bundle", "create", str(bundle), "HEAD"], cwd=root,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bundle.chmod(0o600)
    subprocess.run(["git", "archive", "--format=tar.gz", "--output=" + str(out / "source.tar.gz"), "HEAD"],
                   cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw = {str(p.relative_to(root)): sha(p) for p in (root / "bench/results").rglob("*") if p.is_file()}
    # Prepared dist inputs are included so historical/fresh source hashes can be checked offline.
    raw.update({str(p.relative_to(root)): sha(p) for p in (root / "dist/prompt-pack").rglob("*") if p.is_file()})
    archive = out / "operational-artifacts.tar.gz"
    with tarfile.open(archive, "w:gz", dereference=False) as stream:
        for name in sorted(raw):
            path = root / name
            if path.is_symlink():
                raise SystemExit("Refuse to follow operational symlink: " + name)
            stream.add(path, arcname=name, recursive=False)
    verified = 0
    with tarfile.open(archive) as stream:
        for member in stream:
            if not member.isfile() or member.name not in raw:
                raise SystemExit("Unexpected archive member: " + member.name)
            content = stream.extractfile(member)
            if hashlib.sha256(content.read()).hexdigest() != raw[member.name]:
                raise SystemExit("Archive hash mismatch: " + member.name)
            verified += 1
    if verified != len(raw):
        raise SystemExit("Archive coverage mismatch")
    with tempfile.TemporaryDirectory(prefix="pea-durable-restore-") as temporary:
        checkout = Path(temporary) / "repo"
        subprocess.run(["git", "clone", "--quiet", str(bundle), str(checkout)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if command(checkout, "git", "rev-parse", "HEAD") != head:
            raise SystemExit("Restored commit differs")
        subprocess.run(["git", "fsck", "--full"], cwd=checkout, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out / "operational-sha256.json").write_text(json.dumps(raw, indent=2) + "\n")
    (out / "RESTORE.md").write_text(
        "# Restore privately\n\nAll files contain private operational evidence. Do not publish this directory.\n\n"
        "1. Clone `delivery.bundle` into a new directory with `git clone /absolute/path/delivery.bundle restored`.\n"
        "2. Verify the commit against `COMPLETED.json`.\n"
        "3. Inspect and extract `operational-artifacts.tar.gz` into that new checkout only.\n"
        "4. Verify files against `operational-sha256.json`. Use the offline audit scripts first.\n"
        "5. Historical plans remain frozen; never rerun their models automatically. A successful new-plan replay should make zero model calls.\n"
        "\n`source.tar.gz` is an additional source snapshot; `baseline.bundle` preserves the pre-migration commit.\n")
    result = {"commit": head, "historical_files_verified_unchanged": len(baseline["historical_files"]),
              "operational_files_verified": verified, "fresh_clone_and_fsck": "PASS",
              "artifacts": {p.name: sha(p) for p in (bundle, out / "source.tar.gz", archive,
                             out / "operational-sha256.json", out / "RESTORE.md")}}
    (out / "COMPLETED.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
