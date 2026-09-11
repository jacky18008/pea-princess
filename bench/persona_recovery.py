#!/usr/bin/env python3
"""Recover only C1-baseline-s1 after one Claude reply and a local persona start error.

prepare SOURCE DESTINATION is offline; run DESTINATION --allow-claude is explicit,
serial and single-use. Original evidence is never opened for writing. Claude uses
new full-transcript calls with the frozen system, not the old native session.
This is engineering continuation evidence, not a fresh quality comparison. The
old missing usage remains unknown; the token ceiling gates known counters between
calls and cannot certify an exact combined spend or prevent final-call overshoot.
"""
import argparse
from contextlib import contextmanager, redirect_stdout
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import call_control
import durable_run
import launch
import legacy_control
import personas

ROOT = Path(__file__).resolve().parents[1]
VERSION = 1
JOB = 'C1-baseline-s1'
ENV = ('VETFLAT_SKILL_DIR', 'VETFLAT_SKILL_MD_OVERRIDE', 'VETFLAT_CLAUDE_RESUME')
CALLS = ['call-%06d' % n for n in range(1, 31)]
MODE = 'frozen_system_full_transcript_replay_new_native_calls'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(str(path), 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def _safe(path):
    path = Path(path).absolute()
    legacy_control.reject_links(path)
    return path.resolve()


def _inventory(folder):
    folder = _safe(folder)
    if not folder.is_dir():
        raise ValueError('missing evidence directory')
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('source contains a symlink or special file')
        if path.is_file():
            before = path.stat()
            if before.st_size > 4 * 1024 * 1024:
                raise ValueError('unsupported source size')
            data = path.read_bytes()
            after = path.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError('source changed during read')
            files[str(path.relative_to(folder))] = _sha(data)
    return files


def _envelope(path, value_key='value', hash_key='sha256'):
    envelope = json.loads(path.read_text(encoding='utf-8'))
    value = envelope[value_key]
    if envelope[hash_key] != call_control._digest(value):
        raise ValueError('evidence checksum differs: ' + path.name)
    return value


def _request(folder, call_id):
    path = folder / 'requests' / (_sha(call_id.encode()) + '.json')
    value = _envelope(path)
    if value['call_id'] != call_id:
        raise ValueError('request identity differs')
    return value


def _fixtures(arguments, config):
    # Only the selected synthetic persona definition and its source fixtures.
    definition = _safe(arguments['personas'])
    expected_definition = _safe(ROOT / 'evals/personas.json')
    if definition != expected_definition:
        raise ValueError('unsupported persona definition path')
    fixture_root = _safe(ROOT / 'evals/personas/fixtures/C1')
    expected = {Path(p) for p in config['input_sha256']
                if fixture_root in Path(p).parents}
    current = {p for p in fixture_root.rglob('*') if not p.is_dir()}
    if not expected or current != expected:
        raise ValueError('persona fixture file set changed')
    paths = [definition] + sorted(expected)
    result = {}
    for path in paths:
        if path.is_dir():
            continue
        path = _safe(path)
        digest = _sha(path.read_bytes())
        if config['input_sha256'].get(str(path)) != digest:
            raise ValueError('persona definition or fixture changed')
        result[str(path)] = digest
    return result


def _source(folder):
    folder = _safe(folder)
    inventory = _inventory(folder)
    expected = {'run.json', 'control/checkpoint.json', 'control/progress.json',
                'control/controller.lock', 'run.lock'}
    expected.update('requests/' + _sha(c.encode()) + '.json' for c in CALLS[:2])
    if set(inventory) != expected:
        raise ValueError('only the observed two-call source is supported')
    manifest = _envelope(folder / 'run.json')
    state = _envelope(folder / 'control/checkpoint.json', 'state', 'state_sha256')
    args = manifest['config']['arguments']
    required = {'persona': 'C1', 'seed': 1, 'model': 'claude-sonnet-5',
                'persona_model': 'gpt-5.6-terra', 'judge_model': 'gpt-5.6-sol',
                'persona_agent': 'auto', 'session_mode': 'auto', 'max_calls': 30,
                'max_total_tokens': 1500000, 'allow_claude': True, 'agent': None,
                'matrix': None, 'probe': False, 'dry_run': False, 'rules_only': False,
                'regrade': None, 'retry_failed': None, 'skip_existing': False,
                'workdir': None, 'max_sessions': None}
    if any(args.get(k) != v for k, v in required.items()):
        raise ValueError('unsupported persona/model/seed/mode or original limits')
    if (manifest['planned_call_ids'] != CALLS or state['planned_call_ids'] != CALLS
            or manifest['max_total_tokens'] != 1500000
            or manifest['allow_claude'] is not True or manifest['allow_tools'] is not True
            or set(state['calls']) != set(CALLS[:2]) or state['skipped']
            or any(manifest['config']['environment'].get(k) for k in ENV)):
        raise ValueError('unsupported source plan or environment')
    for n, call_id in enumerate(CALLS[:2]):
        row = state['calls'][call_id]
        record = row['record']
        if (row['call_id'] != call_id or row['job_id'] != JOB or row['phase'] != 'legacy'
                or row['role'] != ('turn 1 agent', 'turn 2 persona')[n]
                or call_control._digest(record) != row['record_sha256']):
            raise ValueError('physical record identity/checksum differs')
        result = launch.LaunchResult(**record['launch_result'])
        canonical = durable_run.cli_record(call_id, result, ('claude', 'codex')[n])
        if any(record.get(k) != v for k, v in canonical.items()):
            raise ValueError('raw launch does not match canonical record')
        if record.get('workdir_artifacts') or record.get('output_artifacts'):
            raise ValueError('recovery supports only an empty chat workspace')
        if call_control.failure_kind(record, True) != row['failure_kind']:
            raise ValueError('saved failure classification differs')
    first, failed = (state['calls'][c]['record'] for c in CALLS[:2])
    bad = failed['launch_result']
    attempts = bad.get('attempt_records') or []
    if (state['calls'][CALLS[0]]['failure_kind'] is not None
            or state['calls'][CALLS[1]]['failure_kind'] != 'process_error'
            or bad['exit_code'] is not None or bad['usage'] is not None
            or bad['stdout'] or bad['stderr'] or bad['seconds'] != 0
            or bad['attempts'] != 1 or len(attempts) != 1
            or not attempts[0].get('start_error')
            or not str(bad['note']).startswith("could not start 'codex':")
            or '/_persona' not in attempts[0]['start_error']):
        raise ValueError('second call is not the supported local pre-start failure')
    report = call_control.CallControl._report(state)
    if (report != json.loads((folder / 'control/progress.json').read_text())
            or set(state['reducer_state']['requests']) != set(CALLS[:2])):
        raise ValueError('original progress/request ledger differs')
    direct = first['direct_terminal_usage']
    for field in call_control.FIELDS:
        if (report['usage']['known_' + field] != direct[field]
                or report['usage']['unknown_' + field + '_requests'] != 1):
            raise ValueError('original usage summary differs from raw records')
    requests = [_request(folder, c) for c in CALLS[:2]]
    if [r['family'] for r in requests] != ['claude', 'codex']:
        raise ValueError('original request family differs')
    command = requests[0]['request']['command']
    if command.count('--append-system-prompt') != 1 or '--resume' in command:
        raise ValueError('missing original frozen Claude system')
    frozen_system = command[command.index('--append-system-prompt') + 1]
    fixtures = _fixtures(args, manifest['config'])
    card = personas.variant_of(personas.card_by_id(personas.load_personas(args['personas']), 'C1'), False)
    if personas.default_agent(card) != 'chat':
        raise ValueError('only the original chat harness is supported')
    if _inventory(folder) != inventory:
        raise ValueError('source changed during validation')
    return {'source': str(folder), 'source_files': inventory, 'arguments': args,
            'fixtures': fixtures, 'card': card, 'requests': requests,
            'first_launch_result': first['launch_result'], 'original_usage': report['usage'],
            'original_calls': 2, 'original_failure_kind': 'local_pre_start_error_usage_unknown',
            'frozen_system': frozen_system}


def _args(plan, destination):
    destination = Path(destination).resolve()
    values = copy.deepcopy(plan['arguments'])
    values.update(durable_dir=str(destination / 'continuation'), results=str(destination / 'results'),
                  day='recovered', session_mode='replay', max_calls=28,
                  max_total_tokens=plan['remaining_known_token_allowance'], allow_claude=True,
                  recovery_manifest_sha256=call_control._digest(plan))
    return argparse.Namespace(**values)


def _normalize(command, cwd, ignore_session=False):
    result, skip = [], False
    for part in command:
        if skip:
            skip = False
            continue
        if ignore_session and part == '--session-id':
            skip = True
            continue
        result.append(str(part).replace(str(Path(cwd).resolve()), '<WORKDIR>'))
    return result


class _Prepared(Exception):
    pass


def _trace_result(destination, index, label, result, error=None):
    value = {'label': label, 'error': error,
             'launch_result': dict(result._asdict()) if result else None}
    _write(destination / 'actor-trace' / ('%04d-result.json' % index), value)
    # Exact visible replies survive a later rate limit before personas.write_session.
    text = legacy_control.reply_text(result, 'codex' if 'persona' in label or label in ('judge', 'satisfaction') else 'claude') if result else ''
    fence = '`' * max(3, 1 + max([len(m) for m in re.findall(r'`+', text)] or [0]))
    path = destination / 'conversation-trace.md'
    with path.open('a', encoding='utf-8') as stream:
        os.chmod(str(path), 0o600)
        stream.write('\n## ' + label + '\n\n' + fence + 'text\n' + text + '\n' + fence + '\n')
        if error:
            stream.write('\nStopped; see retained result JSON.\n')
        stream.flush()
        os.fsync(stream.fileno())


def _trace_opening(destination, text):
    fence = '`' * max(3, 1 + max([len(m) for m in re.findall(r'`+', text)] or [0]))
    path = destination / 'conversation-trace.md'
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(str(path), 0o600)
        stream.write('# Frozen conversation continuation\n\n'
                     'The original first reply is reused. Later native calls use full transcript replay. '
                     'Exact actor request JSON preserves system, history and expanded pasted files; '
                     'persona replies below retain their raw paste markers. This is not a current-skill evaluation.\n\n'
                     '## Original user opening\n\n' + fence + 'text\n' + text + '\n' + fence + '\n')
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def _replay(plan, destination, session, preparing=False):
    original_active, original_run = legacy_control._ACTIVE, legacy_control.run_cli
    original_system = personas.system_prompt
    count = [0]
    proof = {'reused_original_call_id': CALLS[0], 'next_original_call_id': CALLS[1]}

    def run_cli(command, cwd, timeout, family, **kwargs):
        index = count[0]
        count[0] += 1
        if index < 2:
            expected = plan['requests'][index]
            actual = {'command': _normalize(command, cwd, index == 0), 'timeout': timeout}
            wanted = copy.deepcopy(expected['request'])
            wanted['command'] = _normalize(wanted['command'], cwd, index == 0)
            if (actual != wanted or family != expected['family']
                    or kwargs.get('label') != ('turn 1 agent', 'turn 2 persona')[index]):
                raise ValueError('reconstructed original request differs before dispatch')
            proof[('first_agent_request_sha256', 'first_persona_request_sha256')[index]] = call_control._digest(actual)
            if index == 0:
                result = launch.LaunchResult(**plan['first_launch_result'])
                if not preparing:
                    _write(destination / 'actor-trace' / '0001-request.json',
                           {'label': kwargs['label'], 'reused_original_call': CALLS[0],
                            'new_physical_call': False, 'request': actual})
                    _trace_result(destination, 1, kwargs['label'], result)
                return result
            if preparing:
                raise _Prepared()
            if proof != json.loads((destination / 'reconstruction.json').read_text()):
                raise ValueError('prepared controller reconstruction differs')
        # No retry or old native session: each Claude call carries frozen system + history.
        if family == 'claude' and ('--resume' in command or '--session-id' in command
                                  or command[command.index('--append-system-prompt') + 1] != plan['frozen_system']):
            raise ValueError('recovery Claude call changed replay policy')
        if (_inventory(Path(plan['source'])) != plan['source_files']
                or _inventory(destination / 'original') != plan['source_files']):
            raise ValueError('original evidence changed before continuation dispatch')
        call_id = 'call-%06d' % (session.ordinal + 1)
        _write(destination / 'actor-trace' / ('%04d-request.json' % (index + 1)),
               {'label': kwargs['label'], 'family': family, 'new_physical_call': True,
                'continuation_call_id': call_id, 'at': datetime.now(timezone.utc).isoformat(),
                'request': {'command': _normalize(command, cwd), 'timeout': timeout}})
        try:
            result = original_run(command, cwd, timeout, family, **kwargs)
        except BaseException as exc:
            record = session.controller.control.record(call_id)
            saved = (record or {}).get('launch_result')
            result = launch.LaunchResult(**saved) if saved else None
            _trace_result(destination, index + 1, kwargs['label'], result, str(exc))
            raise
        _trace_result(destination, index + 1, kwargs['label'], result)
        return result

    legacy_control._ACTIVE = session
    legacy_control.run_cli = run_cli
    personas.system_prompt = lambda card, harness: plan['frozen_system']
    try:
        yield proof
    finally:
        legacy_control._ACTIVE = original_active
        legacy_control.run_cli = original_run
        personas.system_prompt = original_system


def _check_environment():
    if any(os.environ.get(k) for k in ENV) or legacy_control._ACTIVE is not None:
        raise ValueError('recovery requires no skill overrides or nested legacy invocation')


def prepare(source, destination):
    _check_environment()
    destination = _safe(destination)
    private = _safe(ROOT / '.pea-playground')
    if private not in destination.parents or destination.exists():
        raise ValueError('destination must be a new private .pea-playground directory')
    plan = _source(source)
    if Path(plan['source']) in destination.parents:
        raise ValueError('destination cannot be inside original source')
    known = plan['original_usage']['known_input_tokens'] + plan['original_usage']['known_output_tokens']
    plan.update(version=VERSION, mode=MODE, new_max_calls=28, original_max_calls=30,
                original_token_ceiling=1500000, remaining_known_token_allowance=1500000 - known,
                usage_limit_note='Original failed-call usage stays unknown; known counters gate between calls, not exact spend.',
                source_sha256=durable_run.source_fingerprint())
    if plan['remaining_known_token_allowance'] <= 0:
        raise ValueError('original known usage exhausted the ceiling')
    destination.mkdir(parents=True, mode=0o700)
    for relative, digest in plan['source_files'].items():
        data = (Path(plan['source']) / relative).read_bytes()
        if _sha(data) != digest:
            raise ValueError('original changed while snapshotting')
        target = destination / 'original' / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with target.open('xb') as stream:
            os.chmod(str(target), 0o600)
            stream.write(data)
    _write(destination / 'recovery.json', {'value': plan, 'sha256': call_control._digest(plan)})
    args = _args(plan, destination)
    session = legacy_control.Session(args, 'persona_recovery.py')
    session.ensure()  # Freeze current source and remaining slots, without dispatch.
    with _replay(plan, destination, session, preparing=True) as proof, redirect_stdout(sys.stderr):
        try:
            personas.play(plan['card'], args, 'baseline', 1)
        except _Prepared:
            pass
        else:
            raise ValueError('controller did not reach the original second request')
    _write(destination / 'reconstruction.json', proof)
    return {'ok': True, 'prepared': str(destination), 'mode': MODE, 'new_max_calls': 28,
            'original_calls': 2, 'original_usage': plan['original_usage'],
            'remaining_known_token_allowance': plan['remaining_known_token_allowance']}


def run(destination, allow_claude=False):
    if allow_claude is not True:
        raise ValueError('this recovery requires explicit --allow-claude')
    _check_environment()
    destination = _safe(destination)
    if _safe(ROOT / '.pea-playground') not in destination.parents:
        raise ValueError('recovery destination must remain private')
    plan = _envelope(destination / 'recovery.json')
    if plan['version'] != VERSION or plan['mode'] != MODE:
        raise ValueError('unsupported recovery manifest')
    if (_inventory(Path(plan['source'])) != plan['source_files']
            or _inventory(destination / 'original') != plan['source_files']
            or durable_run.source_fingerprint() != plan['source_sha256']):
        raise ValueError('original evidence or frozen current source changed')
    for path, digest in plan['fixtures'].items():
        if _sha(_safe(path).read_bytes()) != digest:
            raise ValueError('persona fixture changed after preparation')
    args = _args(plan, destination)
    session = legacy_control.Session(args, 'persona_recovery.py')
    session.ensure()
    if session.controller.report()['dispatched_calls']:
        raise ValueError('continuation already dispatched; no automatic restart/retry')
    _write(destination / 'run-started.json', {'recovery_sha256': call_control._digest(plan),
                                            'mode': MODE, 'allow_claude': True,
                                            'at': datetime.now(timezone.utc).isoformat()})
    _trace_opening(destination, plan['requests'][0]['request']['command'][-1])
    error, record = None, None
    try:
        with _replay(plan, destination, session), redirect_stdout(sys.stderr):
            record = personas.play(plan['card'], args, 'baseline', 1)
            record['recovery'] = {'mode': MODE, 'original_source': plan['source'],
                                  'reused_launch_labels': ['turn 1 agent'],
                                  'original_failed_call_id': CALLS[1],
                                  'quality_scope': 'old frozen-system conversation continuation; not current shipped skill evaluation or fresh quality A/B'}
            _write(destination / 'conversation.json', record)
            personas.write_session(record, args.results, args.day)
            session.finished(0)
    except (Exception, KeyboardInterrupt) as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        try:
            report = session.controller.report()
        except Exception as exc:
            report = None
            error = (error + '; ' if error else '') + 'ledger report unavailable: ' + str(exc)
        usage = report['usage'] if report else None
        combined = {}
        if usage is not None:
            for field in call_control.FIELDS:
                for prefix in ('known_', 'unknown_'):
                    key = prefix + field + ('_requests' if prefix == 'unknown_' else '')
                    combined[key] = plan['original_usage'][key] + usage[key]
        combined['total_tokens'] = None  # Original start error has no direct usage.
        try:
            unchanged = (_inventory(Path(plan['source'])) == plan['source_files']
                         and _inventory(destination / 'original') == plan['source_files'])
        except (OSError, ValueError):
            unchanged = False
        if not unchanged:
            error = (error + '; ' if error else '') + 'original evidence changed during continuation'
        result = {'ok': error is None, 'error': error, 'mode': MODE,
                  'conversation_outcome': record.get('outcome') if record else None,
                  'quality_scope': 'old frozen-system engineering continuation; no current-skill or fresh A/B claim',
                  'new_calls': report['dispatched_calls'] if report else None, 'original_calls': 2,
                  'combined_calls': 2 + report['dispatched_calls'] if report else None, 'max_combined_calls': 30,
                  'new_usage': usage, 'original_usage': plan['original_usage'],
                  'combined_usage': combined, 'usage_limit_note': plan['usage_limit_note'],
                  'original_unchanged': unchanged}
        _write(destination / 'recovery-result.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    prep = subs.add_parser('prepare')
    prep.add_argument('source')
    prep.add_argument('destination')
    live = subs.add_parser('run')
    live.add_argument('destination')
    live.add_argument('--allow-claude', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = prepare(args.source, args.destination) if args.command == 'prepare' else run(args.destination, args.allow_claude)
    except (ValueError, OSError, KeyError, TypeError, call_control.CallControlError) as exc:
        result = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
