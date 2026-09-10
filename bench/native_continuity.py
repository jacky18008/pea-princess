#!/usr/bin/env python3
"""Owned persistent Codex turns; stdlib, one attempt, no session enumeration.

prepare_session() is offline. invoke() starts once or resumes only the UUID
emitted by this session's own successful first call. recover() repairs derived
receipts without submitting a prompt. This uses workspace-write, not read
isolation; native account persistence remains outside this adapter's directory.
Raw resumed usage has unqualified scope: its sum is a conservative stopping
metric, never a claim of exact processed tokens, provider requests or cost.
"""
from contextlib import contextmanager
import copy
import fcntl
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

import conversation_native as native
from call_control import CallControl, _atomic_json

VERSION = 1
USAGE_SCOPE = 'unqualified_native_cli_terminal_counter'
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024 * 1024


class ContinuityError(native.NativeError):
    pass


def _file_hash(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContinuityError('pinned source/runtime must be a regular file')
        digest = hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()
    finally:
        os.close(fd)


def _runtime_identity():
    executable = shutil.which('codex')
    if not executable:
        raise ContinuityError('Codex executable is unavailable')
    executable = Path(executable).resolve(strict=True)
    if not executable.is_file() or not os.access(str(executable), os.X_OK):
        raise ContinuityError('Codex must resolve to an executable regular file')
    version = subprocess.run([str(executable), '--version'], capture_output=True,
                             text=True, timeout=10, check=True).stdout.strip()
    if not version.startswith('codex-cli ') or len(version) > 200:
        raise ContinuityError('unexpected Codex version response')
    return {'path': str(executable), 'sha256': _file_hash(executable), 'version': version}


def _read_json(path, limit=MAX_MANIFEST_BYTES):
    return json.loads(native._read(Path(path), limit))


def _new_json(path, value):
    native._write_new(Path(path), native._json(value))


def _envelope(value):
    return {'value': value, 'sha256': native._digest(value)}


def _read_envelope(path):
    saved = _read_json(path)
    if not isinstance(saved, dict) or set(saved) != {'value', 'sha256'} or native._digest(saved['value']) != saved['sha256']:
        raise ContinuityError('continuity artifact checksum differs')
    return saved['value'], saved['sha256']


def _uuid(value):
    if not isinstance(value, str):
        raise ContinuityError('native thread identity must be a canonical UUID')
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise ContinuityError('native thread identity must be a canonical UUID') from error
    if str(parsed) != value:
        raise ContinuityError('native thread identity must be a canonical UUID')
    return value


def _disjoint(left, right):
    return left != right and left not in right.parents and right not in left.parents


@contextmanager
def _locked(session_dir):
    session_dir = native._safe_path(session_dir)
    fd = os.open(session_dir / 'session.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            raise ContinuityError('invalid continuity lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ContinuityError('owned native session is already in use') from error
        yield session_dir
    finally:
        os.close(fd)


def prepare_session(session_dir, workdir, *, max_calls, model='gpt-6-astra',
                    effort='low', timeout_seconds=360, source_paths=()):
    """Create private ownership/plan metadata; no model invocation.

    Use a new session_dir disjoint from native.prepare_workdir's workdir.
    Turn IDs are t01..tNN. Additional source_paths are explicit immutable files;
    mutable requirements, newly released sources and outputs belong in workdir.
    """
    if type(max_calls) is not int or not 1 <= max_calls <= 26:
        raise ContinuityError('max_calls must be an integer from 1 to 26')
    if model not in native.MODELS or effort not in native.EFFORTS:
        raise ContinuityError('unsupported explicit model/effort')
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= native.MAX_TIMEOUT_SECONDS:
        raise ContinuityError('invalid native timeout')
    if isinstance(source_paths, (str, bytes, Path)):
        raise ContinuityError('source_paths must be a sequence of explicit files')
    workdir, owner_sha, snapshot = native._validate_workspace(workdir)
    session_dir = Path(session_dir).absolute()
    native._safe_path(session_dir.parent)
    if not _disjoint(session_dir, workdir) or session_dir.exists() or session_dir.is_symlink():
        raise ContinuityError('provide a new private session directory disjoint from the workspace')
    runtime = _runtime_identity()
    import call_control
    import durable_run
    import report_control
    paths = [Path(__file__), Path(native.__file__), Path(native.launch.__file__), Path(call_control.__file__),
             Path(durable_run.__file__), Path(report_control.__file__)]
    paths.extend(Path(path) for path in source_paths)
    pins = {}
    for path in paths:
        path = path.absolute()
        native._safe_path(path.parent)
        pins[str(path)] = _file_hash(path)
    plan = {'version': VERSION, 'local_session_id': str(uuid.uuid4()),
            'workdir': str(workdir), 'workspace_owner_sha256': owner_sha,
            'prepared_workspace_sha256': native._digest(snapshot),
            'model': model, 'effort': effort, 'timeout_seconds': timeout_seconds,
            'turn_ids': ['t%02d' % number for number in range(1, max_calls + 1)],
            'runtime': runtime, 'source_sha256': pins,
            'disabled_host_skill_path': str(Path.home() / '.agents/skills/vet-flat'),
            'usage_scope': USAGE_SCOPE}
    session_dir.mkdir(mode=0o700)
    (session_dir / 'calls').mkdir(mode=0o700)
    _new_json(session_dir / 'plan.json', _envelope(plan))
    _new_json(session_dir / 'identity.json', _envelope({
        'plan_sha256': native._digest(plan), 'thread_uuid': None, 'completed_turns': 0,
        'last_record_sha256': None}))
    CallControl(session_dir / 'controller', plan['turn_ids'], allow_tools=True)
    return {'session_dir': str(session_dir), 'workdir': str(workdir),
            'turn_ids': plan['turn_ids'], 'plan_sha256': native._digest(plan),
            'runtime': runtime, 'model_calls': 0}


def _plan(session_dir):
    plan, digest = _read_envelope(session_dir / 'plan.json')
    if plan.get('version') != VERSION or plan.get('usage_scope') != USAGE_SCOPE:
        raise ContinuityError('unsupported continuity plan')
    _uuid(plan.get('local_session_id'))
    expected = ['t%02d' % number for number in range(1, len(plan['turn_ids']) + 1)]
    if not 1 <= len(expected) <= 26 or plan['turn_ids'] != expected:
        raise ContinuityError('continuity turn plan differs')
    workdir, owner_sha, snapshot = native._validate_workspace(Path(plan['workdir']))
    if owner_sha != plan['workspace_owner_sha256'] or not _disjoint(session_dir, workdir):
        raise ContinuityError('owned workspace identity differs')
    return plan, digest, snapshot


def _verify_pins(plan):
    for path, digest in plan['source_sha256'].items():
        native._safe_path(Path(path).parent)
        if _file_hash(path) != digest:
            raise ContinuityError('immutable continuity source changed: ' + path)
    runtime = plan['runtime']
    if not os.access(runtime['path'], os.X_OK) or _file_hash(runtime['path']) != runtime['sha256']:
        raise ContinuityError('pinned canonical Codex runtime changed')


def _call_folder(session_dir, turn_id):
    return session_dir / 'calls' / turn_id


def _reconcile(session_dir, plan, plan_sha, control):
    """Repair identity/result copies only from already committed owned records."""
    snapshot = control.snapshot()
    ids = plan['turn_ids']
    if snapshot['skipped'] or set(snapshot['calls']) != set(ids[:len(snapshot['calls'])]):
        raise ContinuityError('continuity ledger is not a contiguous owned turn sequence')
    identity, _ = _read_envelope(session_dir / 'identity.json')
    if identity.get('plan_sha256') != plan_sha:
        raise ContinuityError('native identity belongs to another plan')
    complete, thread_id, hashes, raw_sum, unknown, calls = 0, None, [], 0, [], []
    for turn_id in ids[:len(snapshot['calls'])]:
        row = snapshot['calls'][turn_id]; record = row['record']
        folder = _call_folder(session_dir, turn_id)
        frozen, frozen_sha = _read_envelope(folder / 'request.json')
        if frozen.get('plan_sha256') != plan_sha or frozen.get('request', {}).get('turn_id') != turn_id:
            raise ContinuityError('frozen turn belongs to another plan or ID')
        if frozen.get('expected_thread_uuid') != thread_id:
            raise ContinuityError('frozen turn has an unowned native UUID')
        usage = record.get('direct_terminal_usage') if record else None
        if isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens')):
            raw_sum += usage['input_tokens'] + usage['output_tokens']
        else:
            unknown.append(turn_id)
        good = record is not None and row['failure_kind'] is None
        calls.append({'turn_id': turn_id, 'status': 'complete' if good else ('failed' if record else 'pending'),
                      'record_dir': str(folder), 'usage_scope': USAGE_SCOPE})
        if not good:
            if turn_id != ids[len(snapshot['calls']) - 1]:
                raise ContinuityError('a turn follows an unresolved physical invocation')
            continue
        if record.get('turn_id') != turn_id or record.get('dispatch_sha256') != frozen_sha or record.get('continuity_plan_sha256') != plan_sha:
            raise ContinuityError('physical result identity differs from frozen dispatch')
        seen = _uuid(record.get('thread_uuid'))
        if record.get('resumed_from_uuid') != thread_id or (thread_id is not None and seen != thread_id):
            raise ContinuityError('native result UUID does not match this owned session')
        artifacts = record.get('artifact_sha256', {})
        if set(artifacts) != {'native-invocation.json', 'native-stdout.jsonl', 'native-stderr.txt', 'native-answer.txt'}:
            raise ContinuityError('completed physical artifact set differs')
        for name, digest in artifacts.items():
            if hashlib.sha256(native._read(folder / name, native.MAX_STREAM_BYTES)).hexdigest() != digest:
                raise ContinuityError('saved native artifact changed: ' + name)
        result_path = folder / 'result.json'
        if result_path.exists():
            if _read_json(result_path, MAX_RECORD_BYTES) != record:
                raise ContinuityError('saved result copy differs from durable controller')
        else:
            _new_json(result_path, record)
        thread_id = seen; complete += 1; hashes.append(native._digest(record))
    old_count = identity.get('completed_turns')
    if type(old_count) is not int or not 0 <= old_count <= complete:
        raise ContinuityError('native identity completion count is ahead of its durable records')
    expected_old_hash = hashes[old_count - 1] if old_count else None
    if identity.get('last_record_sha256') != expected_old_hash or identity.get('thread_uuid') != (thread_id if old_count else None):
        raise ContinuityError('saved native identity mapping differs')
    updated = {'plan_sha256': plan_sha, 'thread_uuid': thread_id,
               'completed_turns': complete, 'last_record_sha256': hashes[-1] if hashes else None}
    if updated != identity:
        _atomic_json(session_dir / 'identity.json', _envelope(updated))
    blocked = any(call['status'] != 'complete' for call in calls)
    return {'session_dir': str(session_dir), 'local_session_id': plan['local_session_id'],
            'thread_uuid': thread_id, 'completed_turns': complete, 'dispatched_calls': len(calls),
            'next_turn_id': ids[len(calls)] if len(calls) < len(ids) and not blocked else None,
            'blocked': blocked, 'calls': calls, 'raw_counter_sum': raw_sum,
            'unknown_usage_call_ids': unknown, 'usage_scope': USAGE_SCOPE,
            'usage_scope_qualified': False,
            'native_account_storage_exported': False,
            'native_storage_note': 'Only owned requests, JSONL streams, receipts and workspace artifacts are available here; no account session tree or authentication files were enumerated/read.',
            'aggregation_note': 'Sum of reported raw input/output counters for conservative stopping only; not exact processed tokens, provider requests or cost.'}


def recover(session_dir):
    """Return/repair owned saved progress without invoking Codex or reading its account store."""
    with _locked(Path(session_dir).absolute()) as session_dir:
        plan, digest, _ = _plan(session_dir)
        return _reconcile(session_dir, plan, digest, CallControl(session_dir / 'controller', plan['turn_ids'], allow_tools=True))


def _command(plan, folder, thread_id):
    command = [plan['runtime']['path'], 'exec', '--ignore-user-config', '--ignore-rules',
               '--cd', plan['workdir'], '--sandbox', 'workspace-write', '--skip-git-repo-check',
               '-c', 'project_doc_max_bytes=0', '-c', 'approval_policy="never"',
               '-c', 'shell_environment_policy.set={PYTHONDONTWRITEBYTECODE="1"}',
               '-c', 'skills.config=[{path=' + json.dumps(plan['disabled_host_skill_path']) + ',enabled=false}]',
               '--enable', 'skip_host_skill_discovery']
    if thread_id is not None:
        command.extend(['resume', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check'])
    command.extend(['--model', plan['model'], '-c', 'model_reasoning_effort=' + json.dumps(plan['effort']),
                    '--json', '--output-last-message', str(folder / 'native-answer.txt')])
    command.extend([thread_id, '-'] if thread_id is not None else ['--', '-'])
    return command


def _invoke_physical(plan, frozen, frozen_sha, folder):
    """Same bounded low-level launcher as the ephemeral transport; one process only."""
    command = _command(plan, folder, frozen['expected_thread_uuid'])
    invocation = {'version': VERSION, 'command': command, 'dispatch_sha256': frozen_sha,
                  'request_sha256': native._digest(frozen['request']), 'plan_sha256': frozen['plan_sha256'],
                  'timeout_seconds': plan['timeout_seconds'], 'workspace_before': frozen['workspace_before'],
                  'expected_thread_uuid': frozen['expected_thread_uuid'], 'stream_limit_bytes': native.MAX_STREAM_BYTES}
    _new_json(folder / 'native-invocation.json', invocation)
    streams = {'stdout': bytearray(), 'stderr': bytearray()}; truncated = {key: False for key in streams}
    selector = selectors.DefaultSelector(); proc = None; writer = None; note = None; interrupted = None
    started = time.monotonic()
    try:
        proc = native.launch.start_process(command, cwd=plan['workdir'], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, umask=0o077)
        def send():
            try: proc.stdin.write(frozen['request']['prompt'].encode('utf-8')); proc.stdin.close()
            except (BrokenPipeError, OSError): pass
        writer = threading.Thread(target=send, daemon=True); writer.start()
        for name in streams: selector.register(getattr(proc, name), selectors.EVENT_READ, name)
        stop_at = None
        while selector.get_map() or proc.poll() is None:
            now = time.monotonic()
            if note is None and now - started >= plan['timeout_seconds']:
                note = 'timeout'; native.launch.stop_process(proc); stop_at = now
            if stop_at is not None and now - stop_at > 3: break
            if not selector.get_map(): time.sleep(.02)
            for key, _ in selector.select(.1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk: selector.unregister(key.fileobj); continue
                name = key.data; remaining = max(0, native.MAX_STREAM_BYTES - len(streams[name]))
                streams[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated[name] = True
                    if note is None:
                        note = 'output_limit'; native.launch.stop_process(proc); stop_at = time.monotonic()
        proc.wait(timeout=3)
    except BaseException as error:
        note = note or ('process_start_error' if proc is None else type(error).__name__)
        if not isinstance(error, Exception): interrupted = error
    finally:
        selector.close()
        if proc is not None:
            try: native.launch.finish_process(proc)
            except BaseException as error:
                note = note or 'process_cleanup_error'
                if not isinstance(error, Exception): interrupted = interrupted or error
            if writer: writer.join(timeout=2)
            for name in ('stdin', 'stdout', 'stderr'):
                stream = getattr(proc, name)
                if stream and not stream.closed: stream.close()
    out, err = (bytes(streams[key]).decode('utf-8', errors='replace') for key in ('stdout', 'stderr'))
    result = native.launch.LaunchResult(stdout=out, stderr=err, text=out,
        exit_code=proc.returncode if proc else None, seconds=time.monotonic() - started,
        attempts=1, provider_error=bool(note or proc is None or proc.returncode), note=note,
        attempt_records=[{'timeout': note == 'timeout'}])
    record = native.cli_record('answer', result, 'codex'); record.pop('id')
    record.update(command=command, request_sha256=native._digest(frozen['request']), dispatch_sha256=frozen_sha,
                  continuity_plan_sha256=frozen['plan_sha256'], turn_id=frozen['request']['turn_id'],
                  resumed_from_uuid=frozen['expected_thread_uuid'], thread_uuid=None,
                  workspace_before=frozen['workspace_before'], stream_truncated=truncated,
                  usage_scope=USAGE_SCOPE, answer='', assistant_messages=[])
    thread_events = []
    for line_number, line in enumerate(out.splitlines(), 1):
        try: event = json.loads(line)
        except (ValueError, TypeError): continue
        if not isinstance(event, dict): continue
        if event.get('type') == 'thread.started': thread_events.append(event.get('thread_id'))
        item = event.get('item')
        if isinstance(item, dict) and item.get('type') == 'agent_message':
            record['assistant_messages'].append({'stream_line': line_number, 'event_type': event.get('type'),
                                                  'item': copy.deepcopy(item)})
    try:
        if len(thread_events) != 1: raise ContinuityError('expected exactly one native thread.started UUID')
        record['thread_uuid'] = _uuid(thread_events[0])
        if frozen['expected_thread_uuid'] is not None and record['thread_uuid'] != frozen['expected_thread_uuid']:
            raise ContinuityError('resumed native UUID differs from the owned thread')
        record['answer'] = native._read(folder / 'native-answer.txt', native.MAX_ANSWER_BYTES).decode('utf-8')
        if not record['answer'].strip(): raise ContinuityError('empty native answer')
        record['workspace_after'] = native._snapshot(Path(plan['workdir']))
        _verify_pins(plan)
    except (OSError, ValueError, UnicodeError) as error:
        record['status'] = 'stopped'; record['errors'].append({'type': 'invalid_owned_result', 'message': str(error)})
    record['artifact_sha256'] = {}
    try:
        native._write_new(folder / 'native-stdout.jsonl', bytes(streams['stdout']))
        native._write_new(folder / 'native-stderr.txt', bytes(streams['stderr']))
        for name in ('native-invocation.json', 'native-stdout.jsonl', 'native-stderr.txt', 'native-answer.txt'):
            record['artifact_sha256'][name] = hashlib.sha256(native._read(folder / name, native.MAX_STREAM_BYTES)).hexdigest()
    except (OSError, ValueError) as error:
        record['status'] = 'stopped'; record['errors'].append({'type': 'native_artifact_failure', 'message': str(error)})
    if interrupted is not None:
        interrupted.record = record
        raise interrupted
    return record


def invoke(request, record_dir, workdir, session_dir):
    """Run explicit next turn or return that exact already committed turn; never retry."""
    if not isinstance(request, dict) or set(request) != {'turn_id', 'prompt'}:
        raise ContinuityError('request requires only turn_id and the exact new prompt')
    if not isinstance(request['prompt'], str) or not request['prompt'].strip() or len(request['prompt'].encode('utf-8')) > native.MAX_PROMPT_BYTES:
        raise ContinuityError('new prompt is missing or oversized')
    request = json.loads(native._json(request))
    with _locked(Path(session_dir).absolute()) as session_dir:
        plan, plan_sha, before = _plan(session_dir)
        if str(Path(workdir).absolute()) != plan['workdir'] or request['turn_id'] not in plan['turn_ids']:
            raise ContinuityError('workspace/turn is outside this owned session')
        folder = _call_folder(session_dir, request['turn_id'])
        if Path(record_dir).absolute() != folder:
            raise ContinuityError('record_dir must be session_dir/calls/turn_id')
        control = CallControl(session_dir / 'controller', plan['turn_ids'], allow_tools=True)
        report = _reconcile(session_dir, plan, plan_sha, control)
        previous = control.snapshot()['calls'].get(request['turn_id'])
        if previous is not None:
            frozen, _ = _read_envelope(folder / 'request.json')
            if frozen['request'] != request: raise ContinuityError('owned turn ID reused with a different prompt')
            if previous['record'] is None or previous['failure_kind']:
                raise ContinuityError('owned turn is unresolved or failed; no retry or fallback')
            return copy.deepcopy(previous['record'])
        if report['blocked'] or report['next_turn_id'] != request['turn_id']:
            raise ContinuityError('only the next resolved owned turn may be submitted')
        _verify_pins(plan)
        if not report['dispatched_calls'] and native._digest(before) != plan['prepared_workspace_sha256']:
            raise ContinuityError('prepared workspace changed before first dispatch')
        if folder.exists():
            native._safe_path(folder)
            if any(folder.iterdir()): raise ContinuityError('unused turn folder already contains artifacts; inspect without resubmitting')
        else:
            folder.mkdir(mode=0o700)
        frozen = {'request': request, 'plan_sha256': plan_sha, 'workspace_before': before,
                  'expected_thread_uuid': report['thread_uuid']}
        frozen_sha = native._digest(frozen)
        _new_json(folder / 'request.json', _envelope(frozen))
        result = control.run(request['turn_id'], plan['local_session_id'], 'assistant', 'native-continuity',
                             lambda: _invoke_physical(plan, frozen, frozen_sha, folder))
        _reconcile(session_dir, plan, plan_sha, control)
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare = sub.add_parser('prepare'); prepare.add_argument('--session-dir', type=Path, required=True)
    prepare.add_argument('--workdir', type=Path, required=True); prepare.add_argument('--max-calls', type=int, required=True)
    prepare.add_argument('--model', default='gpt-6-astra'); prepare.add_argument('--effort', default='low')
    prepare.add_argument('--timeout-seconds', type=int, default=360); prepare.add_argument('--source-path', type=Path, action='append', default=[])
    run = sub.add_parser('invoke'); run.add_argument('--session-dir', type=Path, required=True)
    run.add_argument('--turn-id', required=True); run.add_argument('--prompt-file', type=Path, required=True)
    restored = sub.add_parser('recover'); restored.add_argument('--session-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare_session(args.session_dir, args.workdir, max_calls=args.max_calls, model=args.model,
                                     effort=args.effort, timeout_seconds=args.timeout_seconds, source_paths=args.source_path)
        elif args.command == 'recover': result = recover(args.session_dir)
        else:
            plan, _ = _read_envelope(args.session_dir / 'plan.json')
            result = invoke({'turn_id': args.turn_id, 'prompt': native._read(args.prompt_file, native.MAX_PROMPT_BYTES).decode('utf-8')},
                            args.session_dir / 'calls' / args.turn_id, Path(plan['workdir']), args.session_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__, 'message': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
