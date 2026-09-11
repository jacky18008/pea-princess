"""Bounded native Codex transport for deliberately synthetic workspaces.

prepare_workdir(path, files) creates a private workspace from supplied bytes;
invoke(request, folder, workdir) makes exactly one CLI attempt, preserving tool
events, terminal usage, raw streams and the last answer. The caller owns the
durable controller, aggregate budget, source pinning and experiment rubric.

The workspace-write sandbox permits native tools. It is NOT adversarial read
isolation from the host account. Use only normal synthetic tests here; adversarial
containment needs a separate OS account/container with narrowly mounted files.
This adapter copies only explicitly supplied fixture bytes and never adds
evaluation criteria/tool prohibitions to the prompt. No automatic retry.
"""
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid

import launch
from durable_run import cli_record

MODELS = ('gpt-6-astra', 'gpt-5.6-luna')
EFFORTS = ('low', 'high')
MAX_PROMPT_BYTES = 1024 * 1024
MAX_STREAM_BYTES = 4 * 1024 * 1024
MAX_ANSWER_BYTES = 1024 * 1024
MAX_WORKSPACE_BYTES = 32 * 1024 * 1024
MAX_WORKSPACE_FILES = 2048
MAX_SCHEMA_BYTES = 16000
MAX_TIMEOUT_SECONDS = 1200
ARTIFACTS = ('native-invocation.json', 'native-stdout.jsonl', 'native-stderr.txt', 'native-answer.txt', 'native-schema.json')
ISOLATED_PERMISSION_PROFILE = 'pea_native_minimal'
ISOLATED_RUNTIME_ROOTS = (Path('/Library/Developer/CommandLineTools/usr/bin'),
                          Path('/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework'))
# Keep the candidate configuration available for offline validation, but never
# claim this boundary works until an actual supported runtime passes the probes.
ISOLATED_READS_UNSUPPORTED_REASON = (
    'isolate_workspace_reads is unsupported: tested Codex CLI 0.153.4 permits '
    'shared temporary-directory reads/writes despite explicit deny rules; '
    'no isolated invocation may start until enforcement is verified')


class NativeError(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _safe_path(path, directory=True):
    path = Path(path)
    if '..' in path.parts:
        raise NativeError('parent traversal is not permitted')
    path = path.absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise NativeError('native artifact paths must not contain symlinks')
    if not path.exists():
        raise NativeError('native artifact parent must already exist')
    info = path.stat()
    if info.st_uid != os.getuid() or (directory and not stat.S_ISDIR(info.st_mode)):
        raise NativeError('native artifact must be an owned directory')
    return path


def _read(path, limit):
    _safe_path(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise NativeError('invalid or oversized native artifact')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise NativeError('native artifact exceeds limit')
        return data
    finally:
        os.close(fd)


def _write_new(path, data):
    """Publish complete owner-only bytes, never overwrite any existing name."""
    _safe_path(path.parent)
    temporary = path.parent / ('.native-txn-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data); stream.flush(); os.fsync(fd)
        os.link(temporary, path, follow_symlinks=False)
        temporary.unlink()
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(parent)
        finally: os.close(parent)
    finally:
        os.close(fd)
        try: temporary.unlink()
        except FileNotFoundError: pass


def _snapshot(workdir):
    rows, total = {}, 0
    for parent, dirs, files in os.walk(workdir, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(parent) / name
            info = path.lstat()
            if info.st_uid != os.getuid() or stat.S_ISLNK(info.st_mode):
                raise NativeError('workspace contains an unowned artifact or symlink')
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise NativeError('workspace contains a special or hardlinked file')
            total += info.st_size
            if total > MAX_WORKSPACE_BYTES or len(rows) >= MAX_WORKSPACE_FILES:
                raise NativeError('synthetic workspace exceeds its bounded size')
            data = _read(path, MAX_WORKSPACE_BYTES)
            rows[str(path.relative_to(workdir))] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'files': rows, 'bytes': total}


def _marker(workdir):
    return workdir.parent / ('.' + workdir.name + '.native-workspace.json')


def prepare_workdir(path, files):
    """Create once from explicit synthetic/public bytes; .pea-state is allowed.

    The ownership marker lives beside, outside, the model-writable workspace.
    Existing directories are rejected; later calls reuse the same prepared tree.
    Source file paths are never followed/copied implicitly.
    """
    path = Path(path)
    if '..' in path.parts or not path.name or not isinstance(files, dict):
        raise NativeError('provide a new workspace and explicit file mapping')
    parent = _safe_path(path.absolute().parent)
    workdir = parent / path.name
    if workdir.exists() or workdir.is_symlink() or _marker(workdir).exists() or _marker(workdir).is_symlink():
        raise NativeError('workspace/ownership marker already exists; never replace it')
    prepared, total = {}, 0
    for name, value in files.items():
        if not isinstance(name, str) or not name or Path(name).is_absolute() or any(p in ('..', '.git') for p in Path(name).parts):
            raise NativeError('fixture name must be a safe relative path')
        if not isinstance(value, (str, bytes)):
            raise NativeError('fixture contents must be explicit text or bytes')
        data = value.encode('utf-8') if isinstance(value, str) else value
        relative = str(Path(name))
        if relative in prepared or relative == '.':
            raise NativeError('duplicate/empty fixture name')
        total += len(data)
        prepared[relative] = data
    if total > MAX_WORKSPACE_BYTES or len(prepared) > MAX_WORKSPACE_FILES:
        raise NativeError('initial workspace exceeds its bound')
    workdir.mkdir(mode=0o700)
    for name, data in prepared.items():
        target = workdir / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_new(target, data)
    value = {'version': 1, 'purpose': 'deliberately-synthetic-native-test', 'workspace': str(workdir),
             'initial': _snapshot(workdir)}
    _write_new(_marker(workdir), _json({'value': value, 'sha256': _digest(value)}))
    return workdir


def _validate_workspace(workdir):
    workdir = _safe_path(workdir)
    try:
        marker = json.loads(_read(_marker(workdir), 1024 * 1024))
    except (OSError, ValueError, UnicodeError) as error:
        raise NativeError('workspace ownership marker is missing or invalid') from error
    if not isinstance(marker, dict) or set(marker) != {'value', 'sha256'} or marker['sha256'] != _digest(marker['value']):
        raise NativeError('workspace marker integrity differs')
    value = marker['value']
    if not isinstance(value, dict) or value.get('version') != 1 or value.get('purpose') != 'deliberately-synthetic-native-test' or value.get('workspace') != str(workdir):
        raise NativeError('workspace ownership does not match')
    return workdir, marker['sha256'], _snapshot(workdir)


def _isolated_permission_args():
    """Host-specific child-tool read boundary; outer Codex still owns its auth/config."""
    if sys.platform != 'darwin':
        raise NativeError('isolate_workspace_reads is tested only on macOS')
    if any(not root.is_dir() or root.is_symlink() for root in ISOLATED_RUNTIME_ROOTS):
        raise NativeError('isolate_workspace_reads requires the approved macOS Python runtime roots')
    filesystem = {':minimal': 'read', ':workspace_roots': 'write',
                  ':tmpdir': 'deny', ':slash_tmp': 'deny', '/tmp': 'deny',
                  '/private/tmp': 'deny', '/var/tmp': 'deny', '/private/var/tmp': 'deny'}
    filesystem.update((str(root), 'read') for root in ISOLATED_RUNTIME_ROOTS)
    table = '{' + ','.join(json.dumps(key) + '=' + json.dumps(value) for key, value in filesystem.items()) + '}'
    shell_path = str(ISOLATED_RUNTIME_ROOTS[0]) + ':/usr/bin:/bin:/usr/sbin:/sbin'
    disabled_skills = [Path.home() / '.agents/skills' / name
                       for name in ('pea-princess', 'vet-flat')]
    return ['-c', 'default_permissions=' + json.dumps(ISOLATED_PERMISSION_PROFILE),
            '-c', 'permissions.' + ISOLATED_PERMISSION_PROFILE + '.filesystem=' + table,
            '-c', 'permissions.' + ISOLATED_PERMISSION_PROFILE + '.network.enabled=false',
            '-c', 'shell_environment_policy.inherit="none"',
            '-c', 'shell_environment_policy.set={PATH=' + json.dumps(shell_path) + '}',
            '-c', 'skills.config=[' + ','.join('{path=' + json.dumps(str(path)) + ',enabled=false}'
                                        for path in disabled_skills) + ']']


def invoke(request, folder, workdir):
    """One physical attempt; request has model, effort, prompt, timeout_seconds.

    Optional response_schema is supplied to Codex without changing prompt text.
    Optional skip_host_skill_discovery controls discovery, not filesystem reads.
    Optional isolate_workspace_reads currently fails closed: the tested macOS
    runtime did not enforce shared-temp denials. Candidate profile construction
    remains available for offline checks; this is not outer-process isolation.
    Optional tool_output_token_limit caps individual tool outputs in history,
    not total usage. Omitted controls preserve the original command line.
    folder is a fresh per-call artifact directory disjoint from the workspace.
    The record omits id so the caller can bind any durable dispatch identity.
    A stopped/unknown/invalid record must stop the caller's batch; never retry it.
    """
    if not isinstance(request, dict) or set(request) - {'model', 'effort', 'prompt', 'timeout_seconds', 'response_schema',
                                                      'skip_host_skill_discovery', 'tool_output_token_limit',
                                                      'isolate_workspace_reads'}:
        raise NativeError('unsupported native request fields')
    if request.get('model') not in MODELS or request.get('effort') not in EFFORTS:
        raise NativeError('explicit supported Codex model and low/high effort required')
    prompt = request.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt.encode('utf-8')) > MAX_PROMPT_BYTES:
        raise NativeError('native prompt is missing or too large')
    timeout = request.get('timeout_seconds')
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise NativeError('timeout_seconds must be an integer from 1 to %d' % MAX_TIMEOUT_SECONDS)
    if 'skip_host_skill_discovery' in request and type(request['skip_host_skill_discovery']) is not bool:
        raise NativeError('skip_host_skill_discovery must be a boolean')
    if 'isolate_workspace_reads' in request and type(request['isolate_workspace_reads']) is not bool:
        raise NativeError('isolate_workspace_reads must be a boolean')
    if request.get('isolate_workspace_reads', False) and ISOLATED_READS_UNSUPPORTED_REASON is not None:
        raise NativeError(ISOLATED_READS_UNSUPPORTED_REASON)
    if 'tool_output_token_limit' in request:
        limit = request['tool_output_token_limit']
        if type(limit) is not int or not 256 <= limit <= 16000:
            raise NativeError('tool_output_token_limit must be an integer from 256 to 16000')
    schema = request.get('response_schema')
    try:
        if schema is not None and (not isinstance(schema, dict) or len(_json(schema)) > MAX_SCHEMA_BYTES):
            raise NativeError('response schema is invalid or too large')
        request = json.loads(_json(request))  # Freeze caller-owned nested schema before dispatch.
    except (TypeError, ValueError, OverflowError) as error:
        raise NativeError('request must contain bounded JSON schema data') from error
    schema = request.get('response_schema')
    permission_args = _isolated_permission_args() if request.get('isolate_workspace_reads', False) else ['--sandbox', 'workspace-write']
    workdir, owner_sha, before = _validate_workspace(workdir)
    folder = _safe_path(folder)
    if folder == workdir or folder in workdir.parents or workdir in folder.parents:
        raise NativeError('call evidence and model-writable workspace must be disjoint')
    if any((folder / name).exists() or (folder / name).is_symlink() for name in ARTIFACTS):
        raise NativeError('call artifacts already exist; never invoke this folder twice')
    executable = shutil.which('codex')
    if not executable:
        raise NativeError('Codex executable is unavailable')
    if request.get('isolate_workspace_reads', False):
        # macOS helper dispatch retains the launched executable path. A HOME/bin
        # symlink is outside the minimal profile even when its target is allowed.
        # Launch the canonical binary instead of widening read access to that alias.
        try:
            canonical_executable = Path(executable).resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise NativeError('isolated Codex executable cannot be resolved') from error
        if not canonical_executable.is_file() or not os.access(str(canonical_executable), os.X_OK):
            raise NativeError('isolated Codex executable must be an executable regular file')
        executable = str(canonical_executable)
    answer = folder / 'native-answer.txt'
    command = [executable, 'exec', '--ignore-user-config', '--ephemeral', '--cd', str(workdir)] + permission_args + [
               '--skip-git-repo-check', '--model', request['model'],
               '-c', 'model_reasoning_effort="%s"' % request['effort'], '-c', 'project_doc_max_bytes=0',
               '--json', '--output-last-message', str(answer)]
    if request.get('skip_host_skill_discovery', False):
        command.extend(['--enable', 'skip_host_skill_discovery'])
    if 'tool_output_token_limit' in request:
        command.extend(['-c', 'tool_output_token_limit=%d' % request['tool_output_token_limit']])
    if schema is not None:
        schema_bytes = _json(schema)
        # Native tools can inspect this known schema; the CLI uses the protected
        # per-call original even if a tool later edits the inspectable copy.
        schema_copy = workdir / ('.native-response-schema-' + hashlib.sha256(schema_bytes).hexdigest() + '.json')
        if schema_copy.exists() or schema_copy.is_symlink():
            if _read(schema_copy, MAX_SCHEMA_BYTES) != schema_bytes:
                raise NativeError('workspace schema copy differs from the requested schema')
        else:
            _write_new(schema_copy, schema_bytes)
        before = _snapshot(workdir)
        _write_new(folder / 'native-schema.json', schema_bytes)
        command.extend(['--output-schema', str(folder / 'native-schema.json')])
    command.extend(['--', '-'])
    invocation = {'version': 1, 'request_sha256': _digest(request), 'command': command,
                  'workspace_owner_sha256': owner_sha, 'workspace_before': before,
                  'timeout_seconds': timeout, 'stream_limit_bytes': MAX_STREAM_BYTES}
    _write_new(folder / 'native-invocation.json', _json(invocation))
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    truncated = {'stdout': False, 'stderr': False}
    started = time.monotonic(); proc = None; writer = None; note = None; interrupted = None
    selector = selectors.DefaultSelector()
    try:
        proc = launch.start_process(command, cwd=str(workdir), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, umask=0o077)
        def send():
            try: proc.stdin.write(prompt.encode('utf-8')); proc.stdin.close()
            except (BrokenPipeError, OSError): pass
        writer = threading.Thread(target=send, daemon=True); writer.start()
        for name in streams:
            selector.register(getattr(proc, name), selectors.EVENT_READ, name)
        stop_at = None
        while selector.get_map() or proc.poll() is None:
            now = time.monotonic()
            if note is None and now - started >= timeout:
                note = 'timeout'; launch.stop_process(proc); stop_at = now
            if stop_at is not None and now - stop_at > 3:
                break  # Bounded cleanup even if a detached descendant holds a pipe.
            if not selector.get_map():
                time.sleep(.02)
            for key, _ in selector.select(.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj); continue
                name = key.data; remaining = max(0, MAX_STREAM_BYTES - len(streams[name]))
                streams[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[name] = True
                    if note is None:
                        note = 'output_limit'; launch.stop_process(proc); stop_at = time.monotonic()
        proc.wait(timeout=3)
    except BaseException as error:
        note = note or ('process_start_error' if proc is None else type(error).__name__)
        if not isinstance(error, Exception): interrupted = error
    finally:
        selector.close()
        if proc is not None:
            try: launch.finish_process(proc)
            except BaseException as error:
                note = note or 'process_cleanup_error'
                if not isinstance(error, Exception): interrupted = interrupted or error
            if writer: writer.join(timeout=2)
            for name in ('stdout', 'stderr', 'stdin'):
                stream = getattr(proc, name)
                if stream and not stream.closed: stream.close()
    out, err = (bytes(streams[name]).decode('utf-8', errors='replace') for name in ('stdout', 'stderr'))
    result = launch.LaunchResult(stdout=out, stderr=err, text=out,
        exit_code=proc.returncode if proc else None, seconds=time.monotonic()-started,
        attempts=1, provider_error=bool(note or proc is None or proc.returncode), note=note,
        attempt_records=[{'timeout': note == 'timeout'}])
    record = cli_record('answer', result, 'codex')
    record.pop('id')  # Also leaves interrupted exception.record safe for any CallControl ID.
    record.update(command=command, request_sha256=_digest(request), workspace_owner_sha256=owner_sha,
                  workspace_before=before, stream_truncated=truncated, answer='')
    try:
        record['answer'] = _read(answer, MAX_ANSWER_BYTES).decode('utf-8')
        if not record['answer'].strip(): raise NativeError('empty answer')
    except (OSError, ValueError, UnicodeError):
        record.update(answer='', status='stopped'); record['errors'].append({'type': 'invalid_answer_artifact'})
    try: record['workspace_after'] = _snapshot(workdir)
    except (OSError, ValueError):
        record.update(workspace_after=None, status='stopped'); record['errors'].append({'type': 'invalid_workspace_artifact'})
    try:
        _write_new(folder / 'native-stdout.jsonl', bytes(streams['stdout']))
        _write_new(folder / 'native-stderr.txt', bytes(streams['stderr']))
    except (OSError, ValueError):
        record['status'] = 'stopped'; record['errors'].append({'type': 'raw_artifact_write_failed'})
    if interrupted is not None:
        interrupted.record = record
        raise interrupted
    return record
