"""Owned start/resume and crash-recovery checks using local fake processes only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bench'))
import native_continuity as continuity
from call_control import CallControl, CallControlPaused

THREAD = '01234567-89ab-4cde-8fab-0123456789ab'
OTHER_THREAD = '11234567-89ab-4cde-8fab-0123456789ab'
USAGE = {'input_tokens': 20, 'cached_input_tokens': 7, 'output_tokens': 5}


class NativeContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.runtime = self.root / 'fake-codex'; self.runtime.write_text('synthetic runtime'); self.runtime.chmod(0o700)
        self.source = self.root / 'frozen-source.txt'; self.source.write_text('immutable source')
        self.commands = []; self.processes = []
        self.real_start = continuity.native.launch.start_process
        self.new_session('first')

    def new_session(self, name, timeout=2):
        self.work = continuity.native.prepare_workdir(self.root / (name + '-work'), {'fixture.txt': 'synthetic'})
        self.session = self.root / (name + '-control')
        runtime = {'path': str(self.runtime), 'sha256': continuity._file_hash(self.runtime), 'version': 'codex-cli offline-test'}
        with mock.patch.object(continuity, '_runtime_identity', return_value=runtime):
            self.prepared = continuity.prepare_session(self.session, self.work, max_calls=3,
                                                       timeout_seconds=timeout, source_paths=[self.source])

    def request(self, turn='t01', prompt='Please compare these fictional options.'):
        return {'turn_id': turn, 'prompt': prompt}

    def invoke(self, request=None):
        request = request or self.request()
        return continuity.invoke(request, self.session / 'calls' / request['turn_id'], self.work, self.session)

    def fake(self, request=None, thread=THREAD, usage=None, thread_events=None, tail='', terminal_count=1):
        request = request or self.request()
        usage = USAGE if usage is None else usage
        events = [{'type': 'thread.started', 'thread_id': thread}] if thread_events is None else thread_events
        script = '''import json, sys, time
from pathlib import Path
answer, work, turn = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
prompt = sys.stdin.read()
(work / (turn + '-received.txt')).write_text(prompt)
answer.write_text('A measured choice: inspect the evidence before committing.')
'''
        script += '\n'.join('print(' + repr(json.dumps(event)) + ', flush=True)' for event in events) + '\n'
        script += "print(json.dumps({'type':'item.completed','item':{'id':'progress','type':'agent_message','channel':'commentary','text':'A measured comparison begins with the hard conditions.'}}), flush=True)\n"
        script += "print(json.dumps({'type':'item.completed','item':{'id':'final','type':'agent_message','channel':'final','text':'A measured choice: inspect the evidence before committing.'}}), flush=True)\n"
        script += ('print(' + repr(json.dumps({'type': 'turn.completed', 'usage': usage})) + ', flush=True)\n') * terminal_count
        script += tail
        def start(command, **kwargs):
            self.commands.append(copy.deepcopy(command))
            answer = command[command.index('--output-last-message') + 1]
            proc = self.real_start([sys.executable, '-c', script, answer, str(self.work), request['turn_id']], **kwargs)
            self.processes.append(proc)
            return proc
        with mock.patch.object(continuity.native.launch, 'start_process', side_effect=start):
            return self.invoke(request)

    def test_first_turn_persists_uuid_and_all_visible_messages_with_exact_stdin(self):
        request = self.request(prompt='Exact new turn: £2,350; literal $(do-not-run).')
        result = self.fake(request)
        command = self.commands[0]
        self.assertEqual(str(self.runtime), command[0])
        for forbidden in ('--ephemeral', '--last', '--all', 'resume'):
            self.assertNotIn(forbidden, command)
        for expected in ('--ignore-user-config', '--ignore-rules', 'workspace-write', 'gpt-6-astra', 'skip_host_skill_discovery'):
            self.assertIn(expected, command)
        self.assertEqual(['--', '-'], command[-2:])
        self.assertEqual(THREAD, result['thread_uuid']); self.assertIsNone(result['resumed_from_uuid'])
        self.assertEqual(request['prompt'], (self.work / 't01-received.txt').read_text())
        self.assertEqual(['commentary', 'final'], [row['item']['channel'] for row in result['assistant_messages']])
        self.assertEqual('A measured comparison begins with the hard conditions.', result['assistant_messages'][0]['item']['text'])
        report = continuity.recover(self.session)
        self.assertEqual((THREAD, 1, 't02', 25), (report['thread_uuid'], report['completed_turns'], report['next_turn_id'], report['raw_counter_sum']))
        self.assertFalse(report['usage_scope_qualified']); self.assertFalse(report['native_account_storage_exported'])
        self.assertTrue(all(proc.poll() is not None for proc in self.processes))

    def test_resume_exact_owned_uuid_with_only_new_prompt_and_unqualified_raw_counter_sum(self):
        first = self.fake()
        request = self.request('t02', 'Raise only the monthly ceiling; keep the area requirement.')
        second = self.fake(request, usage={'input_tokens': 40, 'cached_input_tokens': 8, 'output_tokens': 7})
        command = self.commands[-1]
        self.assertIn('resume', command); self.assertEqual([THREAD, '-'], command[-2:])
        self.assertNotIn('--ephemeral', command); self.assertEqual(THREAD, second['resumed_from_uuid'])
        self.assertEqual(request['prompt'], (self.work / 't02-received.txt').read_text())
        self.assertNotEqual(first['request_sha256'], second['request_sha256'])
        self.assertEqual(continuity.native._digest(request), second['request_sha256'])
        self.assertEqual(72, continuity.recover(self.session)['raw_counter_sum'])
        self.assertEqual(continuity.USAGE_SCOPE, second['usage_scope'])
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            self.assertEqual(second, self.invoke(request))
            start.assert_not_called()

    def test_uuid_absent_duplicate_malformed_or_changed_stops_without_retry(self):
        cases = [[], [{'type':'thread.started','thread_id':THREAD}] * 2,
                 [{'type':'thread.started','thread_id':'latest'}]]
        for index, events in enumerate(cases):
            if index: self.new_session('uuid-' + str(index))
            with self.subTest(events=events), self.assertRaises(CallControlPaused):
                self.fake(thread_events=events)
            with mock.patch.object(continuity.native.launch, 'start_process') as start:
                with self.assertRaisesRegex(continuity.ContinuityError, 'unresolved or failed'): self.invoke()
                start.assert_not_called()
            self.assertTrue(continuity.recover(self.session)['blocked'])
        self.new_session('uuid-mismatch'); self.fake()
        with self.assertRaises(CallControlPaused): self.fake(self.request('t02'), thread=OTHER_THREAD)
        report = continuity.recover(self.session)
        self.assertEqual(THREAD, report['thread_uuid']); self.assertEqual(1, report['completed_turns'])

    def test_record_only_recovery_repairs_post_commit_identity_failure_without_new_process(self):
        with mock.patch.object(continuity, '_atomic_json', side_effect=OSError('synthetic identity crash')):
            with self.assertRaisesRegex(OSError, 'identity crash'): self.fake()
        (self.session / 'calls/t01/result.json').unlink()
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            report = continuity.recover(self.session)
            saved = self.invoke()
            start.assert_not_called()
        self.assertEqual((1, THREAD), (report['completed_turns'], report['thread_uuid']))
        self.assertEqual(saved, continuity._read_json(self.session / 'calls/t01/result.json'))
        self.assertEqual(1, len(self.commands))

    def test_planned_turn_ceiling_stops_without_fresh_session_fallback(self):
        for turn in ('t01', 't02', 't03'):
            self.fake(self.request(turn, 'Explicit new user turn ' + turn))
        report = continuity.recover(self.session)
        self.assertEqual((3, 3, 75), (report['completed_turns'], report['dispatched_calls'], report['raw_counter_sum']))
        self.assertIsNone(report['next_turn_id']); self.assertFalse(report['blocked'])
        self.assertTrue(all(command[-2] == THREAD for command in self.commands[1:]))
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            with self.assertRaises(continuity.ContinuityError): self.invoke(self.request('t04'))
            start.assert_not_called()

    def test_pending_dispatch_blocks_reopen_without_automatic_resubmission(self):
        def crash(control, call_id, job_id, role, phase, callback):
            control.dispatch(call_id, job_id, role, phase)
            raise KeyboardInterrupt()
        with mock.patch.object(CallControl, 'run', crash), mock.patch.object(continuity.native.launch, 'start_process') as start:
            with self.assertRaises(KeyboardInterrupt): self.invoke()
            start.assert_not_called()
        report = continuity.recover(self.session)
        self.assertTrue(report['blocked']); self.assertEqual(['t01'], report['unknown_usage_call_ids'])
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            with self.assertRaises(continuity.ContinuityError): self.invoke()
            with self.assertRaises(continuity.ContinuityError): self.invoke(self.request('t02'))
            start.assert_not_called()

    def test_turn_source_runtime_workspace_and_lock_preflight_refuse_dispatch(self):
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            with self.assertRaises(continuity.ContinuityError): self.invoke(self.request('t02'))
            with self.assertRaises(continuity.ContinuityError): self.invoke(self.request() | {'thread_uuid': THREAD})
            self.source.write_text('changed')
            with self.assertRaisesRegex(continuity.ContinuityError, 'source changed'): self.invoke()
            self.source.write_text('immutable source')
            self.runtime.write_text('changed executable')
            with self.assertRaisesRegex(continuity.ContinuityError, 'runtime changed'): self.invoke()
            self.runtime.write_text('synthetic runtime')
            (self.work / 'unexpected.txt').write_text('changed after prepare')
            with self.assertRaisesRegex(continuity.ContinuityError, 'before first dispatch'): self.invoke()
            (self.work / 'unexpected.txt').unlink()
            with continuity._locked(self.session):
                with self.assertRaisesRegex(continuity.ContinuityError, 'already in use'): self.invoke()
            start.assert_not_called()

    def test_owned_prompt_identity_and_artifact_tampering_refuse_replay(self):
        self.fake()
        with mock.patch.object(continuity.native.launch, 'start_process') as start:
            with self.assertRaisesRegex(continuity.ContinuityError, 'different prompt'):
                self.invoke(self.request(prompt='A different user turn cannot reuse t01.'))
            identity, _ = continuity._read_envelope(self.session / 'identity.json')
            corrupted = dict(identity, thread_uuid=OTHER_THREAD)
            continuity._atomic_json(self.session / 'identity.json', continuity._envelope(corrupted))
            with self.assertRaisesRegex(continuity.ContinuityError, 'identity mapping'): continuity.recover(self.session)
            continuity._atomic_json(self.session / 'identity.json', continuity._envelope(identity))
            (self.session / 'calls/t01/native-answer.txt').write_text('changed saved answer')
            with self.assertRaisesRegex(continuity.ContinuityError, 'artifact changed'): continuity.recover(self.session)
            start.assert_not_called()

    def test_bad_usage_missing_duplicate_and_negative_preserve_failure_and_block(self):
        cases = [(0, USAGE), (2, USAGE), (1, {'input_tokens': -1, 'cached_input_tokens': 0, 'output_tokens': 5}),
                 (1, {'input_tokens': 1, 'cached_input_tokens': 2, 'output_tokens': 5})]
        for index, (count, usage) in enumerate(cases):
            if index: self.new_session('usage-' + str(index))
            with self.subTest(count=count, usage=usage), self.assertRaises(CallControlPaused):
                self.fake(usage=usage, terminal_count=count)
            self.assertTrue(continuity.recover(self.session)['blocked'])

    def test_timeout_and_output_bounds_stop_owned_process_with_one_attempt(self):
        self.new_session('timeout', timeout=1)
        started = time.monotonic()
        with self.assertRaises(CallControlPaused): self.fake(tail='time.sleep(60)\n')
        self.assertLess(time.monotonic() - started, 6)
        record = CallControl(self.session / 'controller', ['t01','t02','t03'], allow_tools=True).record('t01')
        self.assertTrue(record['timeout']); self.assertEqual(1, record['launch_result']['attempts'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])
        self.new_session('output-cap')
        with mock.patch.object(continuity.native, 'MAX_STREAM_BYTES', 1000):
            with self.assertRaises(CallControlPaused): self.fake(tail="sys.stderr.write('x'*10000);sys.stderr.flush();time.sleep(60)\n")
        self.assertTrue(all(proc.poll() is not None for proc in self.processes))


if __name__ == '__main__': unittest.main()
