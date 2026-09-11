#!/usr/bin/env python3
"""Freeze the local test package, then run its server in the foreground.

No network, model call, credentials or account access. Reads Git-tracked working
files, plus the explicitly named generated prompt pack used by the existing lab.
Private conversation state stays in the original .pea-playground directory.
Usage: python3 tools/start_playground.py --port 8765
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
GENERATED = 'dist/prompt-pack/INSTRUCTIONS.md'
REQUIRED = (
    'tools/persona_playground.py', 'tools/session_runner.py',
    'tools/conversation_reply.py', 'tools/public_source_snapshot.py', 'tools/playground_review.py',
    'bench/personas.py', 'bench/journeys.py', 'bench/durable_run.py',
    'bench/call_control.py', 'bench/launch.py',
    'skills/vet-flat/SKILL.md', 'skills/vet-flat/scripts/session_state.py',
    'evals/personas.json', 'playground/index.html', 'playground/app.js',
    'playground/style.css', 'playground/review.js', 'playground/review.css', 'playground/conversation-policy.md',
    'docs/persona-playground.md', GENERATED,
)
PRIVATE_PARTS = frozenset(('private', 'secrets', 'credentials', 'runtime', 'raw',
                           'results', 'node_modules', '__pycache__'))
EXTENSIONS = frozenset(('.py', '.md', '.json', '.yaml', '.yml', '.txt', '.csv',
                       '.html', '.js', '.css', '.svg'))


class FreezeError(ValueError):
    pass


def eligible(name):
    """Narrow runtime roots; never copy arbitrary tracked personal documents."""
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or str(path) != name:
        return False
    if any(part.startswith('.') or part.lower() in PRIVATE_PARTS for part in path.parts):
        return False
    lower = path.name.lower()
    if any(word in lower for word in ('credential', 'secret', 'password', 'private-key')):
        return False
    if name == 'docs/persona-playground.md':
        return True
    return (name.startswith(('tools/', 'bench/', 'playground/', 'skills/vet-flat/', 'evals/'))
            and path.suffix.lower() in EXTENSIONS)


def tracked(root):
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise FreezeError('Cannot read tracked runtime files from this Git checkout.')
    try:
        return sorted({name for name in result.stdout.decode('utf-8').split('\0') if eligible(name)})
    except UnicodeDecodeError as error:
        raise FreezeError('Runtime paths must be valid UTF-8.') from error


def regular(root, name):
    path = root / name
    try:
        for item in (path, *path.parents):
            if item == root.parent:
                break
            if item.is_symlink():
                return False
        info = path.lstat()
        return stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    except FileNotFoundError:
        return False


def read_source(root, name):
    """Detect changes during a read as well as between the two freeze passes."""
    if not regular(root, name):
        raise FreezeError('Runtime file is missing or not a regular independent file: ' + name)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(str(root / name), flags), 'rb') as handle:
        before = handle_stat(handle)
        body = handle.read()
        after = handle_stat(handle)
    if before != after or not regular(root, name):
        raise FreezeError('Runtime file changed while being read: ' + name)
    return body, before


def handle_stat(handle):
    info = os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise FreezeError('Runtime source is not a regular independent file.')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def private_directory(path):
    # Resolving first would hide a symlink pointing at an unrelated directory.
    path = Path(os.path.abspath(str(path)))
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise FreezeError('Runtime/state directory must not traverse symbolic links.')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir():
        raise FreezeError('Runtime/state path is not a directory.')
    return path


def freeze(root=ROOT, state_dir=None):
    """Copy current bytes once, verify their stability, then publish a snapshot."""
    root = Path(root).resolve()
    state_dir = private_directory(state_dir if state_dir is not None else root / '.pea-playground')
    # DurableRun discovers Git from its source directory. Keep the executable
    # snapshot under the checkout even if private sessions use another directory.
    runtime = private_directory(root / '.pea-playground' / 'runtime')
    snapshot_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:12]
    staging = runtime / ('.preparing-' + snapshot_id)
    destination = runtime / snapshot_id
    staging.mkdir(mode=0o700)
    try:
        indexed = tracked(root)
        names = [name for name in indexed if regular(root, name)]
        # Existing generated prompt instructions are a required runtime input,
        # not an invitation to copy the ignored dist directory or private packs.
        if GENERATED not in names and regular(root, GENERATED):
            names.append(GENERATED)
        names.sort()
        missing = sorted(set(REQUIRED) - set(names))
        if missing:
            raise FreezeError('Required runtime files unavailable: ' + ', '.join(missing))
        records = {}
        observations = {}
        for name in names:
            body, observations[name] = read_source(root, name)
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(body)
            target.chmod(0o400)
            records[name] = {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body),
                             'origin': 'generated-runtime-input' if name == GENERATED else 'tracked-working-file'}
        if indexed != tracked(root):
            raise FreezeError('Tracked runtime file list changed during freeze; restart when edits settle.')
        for name in names:
            body, observed = read_source(root, name)
            if observed != observations[name] or hashlib.sha256(body).hexdigest() != records[name]['sha256']:
                raise FreezeError('Runtime file changed during freeze; restart when edits settle: ' + name)
        head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        manifest = {'schema_version': 1, 'snapshot_id': snapshot_id,
                    'source_root': str(root), 'state_dir': str(state_dir),
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'git_head': head.stdout.decode('ascii').strip() if head.returncode == 0 else None,
                    'files': records,
                    'note': 'Hashes describe current working bytes, including uncommitted tracked edits; Git HEAD alone does not identify this snapshot.'}
        raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8') + b'\n'
        (staging / 'runtime-manifest.json').write_bytes(raw)
        (staging / 'runtime-manifest.json').chmod(0o400)
        staging.rename(destination)
        return {'snapshot_id': snapshot_id, 'snapshot': str(destination),
                'manifest': str(destination / 'runtime-manifest.json'),
                'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                'state_dir': str(state_dir), 'files': len(records)}
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def server_command(snapshot, state_dir, port, python=sys.executable):
    return [python, '-B', str(Path(snapshot) / 'tools/persona_playground.py'),
            '--state-dir', str(state_dir), '--port', str(port)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.pea-playground')
    parser.add_argument('--freeze-only', action='store_true', help='Print the snapshot receipt without starting a server.')
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error('port must be 1024..65535')
    os.umask(0o077)
    try:
        result = freeze(ROOT, args.state_dir)
        result['url'] = 'http://127.0.0.1:' + str(args.port)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if not args.freeze_only:
            os.execv(sys.executable, server_command(result['snapshot'], result['state_dir'], args.port))
    except (FreezeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
