#!/usr/bin/env python3
"""Continue independent original experiment IDs after an explicit failure acknowledgment.

No retries, new calls, skips, deadline changes or provider switches. Frozen
request builders, native transport and local settlement remain authoritative.
The amended budget permits unknown spend, which remains unknown in all reports.
Acknowledgment is an operator assertion, not authentication of user permission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

import call_control
import conversation_resume as operational


class ContinueError(ValueError):
    pass


def _sha(path):
    path = operational._path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ContinueError('audit input must be an owned regular file')
        digest = hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()
    finally:
        os.close(fd)


def selection(plan, state, settled):
    """Pure scheduler: failures remain failures; every ancestor must be settled."""
    by_session = {s['id']: [c for c in plan['calls'] if c.get('session') == s['id']]
                  for s in plan['sessions']}
    pairs = {p['id']: p for p in plan['pairs']}
    ready, deferred = [], []
    for call in plan['calls']:
        if call['id'] in state['calls'] or call['id'] in settled:
            continue  # Existing pending/failed/successful physical IDs never dispatch again.
        if call['role'] == 'answer':
            prerequisites = [c['id'] for c in by_session[call['session']] if c['turn'] < call['turn']]
        else:
            # Full configured sessions, including the nine-turn extensions.
            prerequisites = [c['id'] for sid in pairs[call['pair']]['mask'].values()
                             for c in by_session[sid]]
        missing = [key for key in prerequisites if key not in settled]
        if missing:
            failed = [key for key in missing if state['calls'].get(key, {}).get('failure_kind')]
            deferred.append({'call_id': call['id'], 'blocking_call_ids': missing,
                             'failed_ancestor_call_ids': failed})
        else:
            ready.append(call)
    return ready, deferred


class Continue:
    def __init__(self, source, output, amendment):
        self.resume = operational.Resume(source, output, amendment)
        self.output, self.runner = self.resume.output, self.resume.runner
        self.code_paths = {'driver': Path(__file__).absolute(),
                           'controller': Path(call_control.__file__).absolute(),
                           'resume': Path(operational.__file__).absolute(),
                           'reducer': Path(call_control.report_control.__file__).absolute()}
        self.code_sha256 = {key: _sha(path) for key, path in self.code_paths.items()}
        self._validated()

    def _validated(self):
        if any(_sha(path) != self.code_sha256[key] for key, path in self.code_paths.items()):
            raise ContinueError('operational source changed; stop before another action')
        plan, amendment = self.resume._validated()
        if amendment['amended_token_ceiling'] is not None:
            raise ContinueError('unknown usage requires the validated removal of the budget ceiling')
        self.bindings = {'original_plan_sha256': amendment['original_plan_sha256'],
                         'amendment_sha256': amendment['amendment_sha256'],
                         'amendment_file_sha256': amendment['amendment_file_sha256'],
                         'source_commit': amendment['source_commit'],
                         'source_sha256': amendment['source_sha256'],
                         'source_root': str(self.resume.source), 'output_root': str(self.output),
                         'operational_sha256': self.code_sha256,
                         'max_cli_invocations': 192, 'amended_token_ceiling': None,
                         'automatic_retries': 0, 'claude_calls': 0}
        self.audit_dir = self.output / 'continuation-audit' / amendment['amendment_id']
        if self.audit_dir.exists() or self.audit_dir.is_symlink():
            operational._path(self.audit_dir, directory=True)
            manifest = self._audit_read(self.audit_dir / 'manifest.json')
            if manifest['bindings'] != self.bindings:
                raise ContinueError('continuation audit source or authorization differs')
        return plan, amendment

    def _paused(self):
        path = self.output / 'PAUSE_REQUESTED.json'
        return path.exists() or path.is_symlink()

    def _control(self, plan):
        directory = operational._path(self.output / 'controller', directory=True)
        # This driver only continues an existing run; never recreate lost paid history.
        _sha(directory / 'checkpoint.json')
        for name in ('checkpoint.json', 'controller.lock', 'progress.json'):
            path = directory / name
            if path.exists() or path.is_symlink():
                operational._path(path)
        control = call_control.CallControl(directory, [c['id'] for c in plan['calls']], allow_tools=True)
        if control.snapshot()['skipped']:
            raise ContinueError('this continuation does not authorize skipped original IDs')
        return control

    @staticmethod
    def _audit_read(path):
        envelope = operational._read(path)
        if set(envelope) != {'value', 'sha256'} or operational._digest(envelope['value']) != envelope['sha256']:
            raise ContinueError('immutable continuation audit checksum differs')
        return envelope['value']

    def _audit_write(self, path, value):
        if path.exists() or path.is_symlink():
            if self._audit_read(path) != value:
                raise ContinueError('immutable continuation audit already has different bytes')
        else:
            self.runner.native._write_new(path, operational._json({'value': value, 'sha256': operational._digest(value)}))

    def _failed_pins(self, state):
        result = {}
        for key, row in state['calls'].items():
            if row['failure_kind']:
                path = self.output / 'records' / key / 'native-record.json'
                result[key] = {'checkpoint_record_sha256': row['record_sha256'],
                               'native_record_file_sha256': _sha(path) if path.exists() or path.is_symlink() else None}
        return result

    def _audit(self, plan, amendment, control, action=None):
        state = control.snapshot()
        checkpoint_sha = _sha(control.checkpoint_path)
        failed = self._failed_pins(state)
        # Establish the original budget audit as well; neither audit rewrites its inputs.
        self.resume._check_audit(amendment, create=True)
        parent = self.audit_dir.parent
        if parent.exists() or parent.is_symlink():
            operational._path(parent, directory=True)
        else:
            parent.mkdir(mode=0o700)
        if not self.audit_dir.exists():
            self.audit_dir.mkdir(mode=0o700)
            self._audit_write(self.audit_dir / 'manifest.json', {
                'version': 1, 'bindings': self.bindings,
                'original_checkpoint_sha256': checkpoint_sha,
                'original_failed_receipts': failed})
        manifest = self._audit_read(self.audit_dir / 'manifest.json')
        if manifest['bindings'] != self.bindings:
            raise ContinueError('continuation audit bindings differ')
        if any(failed.get(key) != value for key, value in manifest['original_failed_receipts'].items()):
            raise ContinueError('original failed receipt changed')
        if action:
            self._audit_write(self.audit_dir / ('ack-' + action['call_id'] + '.json'), {
                'version': 1, 'manifest_sha256': operational._digest(manifest),
                'bindings': self.bindings, 'before_checkpoint_sha256': checkpoint_sha,
                'before_revision': state['revision'], 'failed_receipts': failed,
                'action': action})
        if _sha(control.checkpoint_path) != checkpoint_sha:
            raise ContinueError('controller changed while preparing continuation audit')
        return state

    def _settled(self, plan, state):
        settled = set()
        for call in plan['calls']:
            key = call['id']; row = state['calls'].get(key)
            folder = self.output / 'records' / key
            path = folder / 'finished.json'
            if not (path.exists() or path.is_symlink()):
                continue
            if row is None or row['record'] is None or row['failure_kind'] is not None:
                raise ContinueError('finished flag is not backed by a successful physical receipt')
            frozen = operational._read(folder / 'request.json')
            if frozen['call'] != call or operational._digest(frozen['request']) != frozen['request_sha256']:
                raise ContinueError('finished request integrity differs')
            expected = {'request_sha256': frozen['request_sha256'], 'record_sha256': row['record_sha256']}
            if call['role'] == 'answer':
                history = operational._read(folder / 'input-history.json')
                history.append({'role': 'assistant', 'turn': call['turn'], 'text': row['record']['answer']})
                expected['history_sha256'] = operational._digest(history)
            if operational._read(path) != expected:
                raise ContinueError('finished flag differs from its original receipt or history')
            settled.add(key)
        return settled

    def _view(self, plan, control):
        state = control.snapshot(); report = control.report()
        settled = self._settled(plan, state)
        ready, deferred = selection(plan, state, settled)
        keys = ('planned_calls', 'dispatched_calls', 'completed_calls', 'failed_calls',
                'pending_call_ids', 'usage', 'paused', 'plan_complete')
        return {**{key: report[key] for key in keys},
                'original_plan_complete': len(settled) == len(plan['calls']),
                'settled_call_ids': [c['id'] for c in plan['calls'] if c['id'] in settled],
                'failed_call_ids': [c['id'] for c in plan['calls'] if state['calls'].get(c['id'], {}).get('failure_kind')],
                'deferred': deferred, 'ready_call_ids': [c['id'] for c in ready],
                'known_processed_token_subtotal': report['usage']['known_input_tokens'] + report['usage']['known_output_tokens'],
                'amended_token_ceiling': None, 'provider_request_count': None,
                'operator_paused': self._paused()}

    def status(self):
        with self.runner.exclusive(self.output):
            plan, _ = self._validated()
            return self._view(plan, self._control(plan))

    def acknowledge(self, call_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ContinueError('an explicit nonempty operator reason is required')
        with self.runner.exclusive(self.output):
            plan, amendment = self._validated(); control = self._control(plan)
            if self._paused():
                return self._view(plan, control)
            state = control.snapshot()
            if any(row['record'] is None for row in state['calls'].values()):
                raise ContinueError('pending physical invocation blocks acknowledgment')
            row = state['calls'].get(call_id)
            if (row is None or row['failure_kind'] is None or row['record'] is None
                    or not state['reducer_state']['paused']
                    or state['reducer_state'].get('pause_cause') != 'terminal/' + call_id):
                raise ContinueError('acknowledgment must identify the current failed original call')
            record = row['record']
            if type(record.get('exit_code')) is not int:
                raise ContinueError('failed receipt does not establish process termination')
            launch = record.get('launch_result')
            if launch is not None and (not isinstance(launch, dict) or launch.get('exit_code') != record['exit_code']
                                       or launch.get('attempts') != 1):
                raise ContinueError('failed launch receipt termination or attempt count differs')
            self._audit(plan, amendment, control, {'operation': 'acknowledge_terminal_failure',
                        'call_id': call_id, 'reason_sha256': hashlib.sha256(reason.encode()).hexdigest(),
                        'allow_unknown_usage': True})
            self._validated()
            if self._paused():
                return self._view(plan, control)
            control.acknowledge_failure(call_id, reason, allow_unknown_usage=True)
            return {'acknowledged_call_id': call_id, **self._view(plan, control)}

    def step(self, roles=('answer', 'judge'), invoke=None):
        with self.runner.exclusive(self.output):
            plan, amendment = self._validated(); control = self._control(plan)
            report = control.report()
            if self._paused() or report['paused'] or report['pending_call_ids']:
                return {'blocked': True, **self._view(plan, control)}
            self._audit(plan, amendment, control)
            state = control.snapshot(); settled = self._settled(plan, state)
            # Recover only successful physical receipts. Never settle failed records.
            for call in plan['calls']:
                row = state['calls'].get(call['id'])
                if row and row['record'] is not None and row['failure_kind'] is None and call['id'] not in settled:
                    if call['role'] == 'answer' and any(
                            later.get('session') == call['session'] and later['turn'] > call['turn']
                            and later['id'] in state['calls'] for later in plan['calls']):
                        raise ContinueError('missing historical settlement after a later turn was dispatched')
                    self._validated()
                    if self._paused():
                        return self._view(plan, control)
                    self.runner.settle(self.output, plan, call, row['record'])
            settled = self._settled(plan, control.snapshot())
            ready, _ = selection(plan, control.snapshot(), settled)
            if not ready:
                return {'exhausted_independent_work': True, 'complete': len(settled) == len(plan['calls']), **self._view(plan, control)}
            call = ready[0]
            if call['role'] not in roles:
                return {'awaiting_role': call['role'], **self._view(plan, control)}
            self._validated()
            if self._paused():
                return self._view(plan, control)
            folder = self.output / 'records' / call['id']; folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            operational._path(folder, directory=True)
            if (folder / 'finished.json').exists():
                raise ContinueError('completed artifact is not reflected in the controller')
            factory = self.runner.answer_request if call['role'] == 'answer' else self.runner.judge_request
            request, work, history = factory(self.output, plan, call)
            request_digest = self.runner._digest(request)
            frozen = folder / 'request.json'
            if frozen.exists() and operational._read(frozen)['request_sha256'] != request_digest:
                raise ContinueError('prepared original request changed')
            self.runner.write(frozen, {'request': request, 'request_sha256': request_digest, 'call': call})
            if history is not None:
                self.runner.write(folder / 'input-history.json', history)
            self._validated()
            if self._paused():
                return self._view(plan, control)
            def callback():
                try:
                    record = (invoke or self.runner.native.invoke)(request, folder, work)
                except BaseException as error:
                    if isinstance(getattr(error, 'record', None), dict):
                        error.record['id'] = call['id']
                    raise
                record['id'] = call['id']
                try:
                    self.runner.write(folder / 'native-record.json', record)
                except BaseException as error:
                    record = dict(record, status='stopped', errors=record.get('errors', []) +
                                  [{'type': 'record_persistence_error', 'message': str(error)}])
                    error.record = record
                    raise
                return record
            record = control.run(call['id'], call.get('session', call['id']), call['role'], 'native', callback)
            self._validated()
            self.runner.settle(self.output, plan, call, record)
            return {'just_completed': call['id'], **self._view(plan, control)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--amendment', required=True, type=Path)
    parser.add_argument('--call-id')
    parser.add_argument('--reason')
    parser.add_argument('action', choices=('status', 'acknowledge', 'answers', 'judges'))
    args = parser.parse_args(argv)
    if args.action == 'acknowledge' and (not args.call_id or not args.reason):
        parser.error('acknowledge requires --call-id and --reason')
    if args.action != 'acknowledge' and (args.call_id is not None or args.reason is not None):
        parser.error('--call-id and --reason are only valid for acknowledge')
    try:
        driver = Continue(args.source, args.output, args.amendment)
        if args.action in ('status', 'acknowledge'):
            result = driver.status() if args.action == 'status' else driver.acknowledge(args.call_id, args.reason)
            print(json.dumps(result, ensure_ascii=False)); return 0
        while True:
            result = driver.step(roles=('answer',) if args.action == 'answers' else ('judge',))
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if any(result.get(key) for key in ('complete', 'exhausted_independent_work', 'awaiting_role', 'operator_paused', 'blocked')):
                return 0
    except Exception as error:
        # Provider exception text/records can contain private endpoints or transcript bytes.
        print(json.dumps({'stopped': True, 'error': type(error).__name__,
                          'message': 'Inspect the private original receipts; no automatic retry was attempted.'}), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
