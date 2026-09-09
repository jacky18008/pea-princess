"""Offline tests: frozen request/receipt protocol, current operational scheduling."""
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_ablation as current_runner
import conversation_continue as continuation
import conversation_resume as operational


def paid(tokens=110):
    return {'status': 'complete', 'exit_code': 0, 'timeout': False,
            'errors': [], 'tool_events': [], 'malformed_event_lines': 0,
            'terminal_usage_events': 1, 'direct_terminal_usage': {
                'input_tokens': tokens - 10, 'cached_input_tokens': 20, 'output_tokens': 10},
            'answer': 'Synthetic useful response.'}


def failed(exit_code=-15):
    return paid() | {'status': 'stopped', 'exit_code': exit_code, 'timeout': True,
                     'errors': [{'type': 'timeout', 'message': 'https://secret.example/private?token=SECRET'}],
                     'terminal_usage_events': 0, 'direct_terminal_usage': None, 'answer': ''}


class ContinueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.source = self.root / 'frozen-source'
        self.source.mkdir()
        for name in current_runner.SOURCES:
            target = self.source / name; target.parent.mkdir(parents=True, exist_ok=True)
            if name != 'dist/vet-flat-skill.zip':
                shutil.copyfile(ROOT / name, target)
                if name == 'bench/conversation_native.py':
                    # The experiment's frozen adapter predates the current runtime policy.
                    text = target.read_text()
                    self.assertIn('MAX_TIMEOUT_SECONDS = 1200', text)
                    target.write_text(text.replace('MAX_TIMEOUT_SECONDS = 1200', 'MAX_TIMEOUT_SECONDS = 240'))
        with zipfile.ZipFile(self.source / 'dist/vet-flat-skill.zip', 'w') as archive:
            for name in ('SKILL.md', 'references/inputs.md', 'references/onboarding.md'):
                archive.writestr('vet-flat/' + name, 'Synthetic public guide\n')
        self.original = operational._load_frozen(self.source); self.output = self.root / 'run'
        with mock.patch.object(self.original.subprocess, 'check_output', return_value='e' * 40 + '\n'):
            self.original.prepare(self.output)
        self.plan = self.original.read(self.output / 'plan.json')
        self.amendment_path = self.root / 'budget-0001.json'
        self.amendment = {'version': 1, 'amendment_id': 'budget-0001',
            'operation': 'complete_original_frozen_plan', 'original_plan_sha256': operational._digest(self.plan),
            'source_commit': self.plan['source_commit'], 'original_token_ceiling': 6000000,
            'amended_token_ceiling': None, 'max_cli_invocations': 192,
            'schedule_sha256': operational._digest(self.plan['calls']), 'automatic_retries': 0,
            'claude_calls': 0, 'previous_amendment_sha256': None,
            'authorization': {'actor': 'user', 'quote': 'Offline authorization: remove ceiling, keep original IDs.',
                              'source': 'offline fixture', 'authorized_at': '2026-09-09T20:00:00+01:00'}}
        self.amendment_path.write_bytes(operational._json(self.amendment))

    def driver(self, execution_policy=None):
        return continuation.Continue(self.source, self.output, self.amendment_path, execution_policy=execution_policy)

    def runtime_policy(self):
        policy = {'version': 1, 'policy_id': 'runtime-0001',
                  'operation': 'extend_deadline_for_unstarted_original_calls',
                  'original_plan_sha256': operational._digest(self.plan),
                  'budget_amendment_sha256': operational._digest(self.amendment),
                  'previous_timeout_seconds': 240, 'timeout_seconds': 1200,
                  'native_sha256': continuation._sha(ROOT / 'bench/conversation_native.py'),
                  'max_cli_invocations': 192, 'automatic_retries': 0, 'claude_calls': 0,
                  'operator': {'actor': 'codex', 'rationale': 'Offline operator implementation rationale; no claimed user permission.',
                               'recorded_at': '2026-09-09T22:00:00+01:00'}}
        path = self.root / 'runtime-0001.json'; path.write_bytes(operational._json(policy))
        return path, policy

    def control(self):
        return continuation.call_control.CallControl(self.output / 'controller', [c['id'] for c in self.plan['calls']], allow_tools=True)

    def fail_next(self, receipt=None):
        dispatched = self.control().report()['dispatched_calls']; key = self.plan['calls'][dispatched]['id']
        with self.assertRaises(Exception):
            self.original.run_next(self.output, invoke=mock.Mock(return_value=receipt or failed()))
        self.assertEqual('failed', self.control().report()['calls'][-1]['status'])
        return key

    def test_acknowledge_then_next_independent_preserves_originals_unknown_usage_and_request(self):
        self.original.run_next(self.output, invoke=mock.Mock(return_value=paid(1000)))
        key = self.fail_next(); control = self.control(); before = control.snapshot(); before_usage = control.report()['usage']
        receipt_path = self.output / 'records' / key / 'native-record.json'; receipt = receipt_path.read_bytes()
        originals = {name: (self.output / name).read_bytes() for name in ('plan.json', 'scenario.json', 'rubric.json', 'frozen.json')}
        checkpoint_sha = continuation._sha(control.checkpoint_path)
        driver = self.driver(); native = mock.Mock(side_effect=AssertionError('blocked work must not dispatch'))
        self.assertTrue(driver.step(invoke=native)['blocked']); native.assert_not_called()
        original_ack = continuation.call_control.CallControl.acknowledge_failure
        def assert_audit(instance, call_id, reason, allow_unknown_usage=False):
            manifest = driver._audit_read(driver.audit_dir / 'manifest.json')
            audit = driver._audit_read(driver.audit_dir / ('ack-' + key + '.json'))
            self.assertEqual(checkpoint_sha, manifest['original_checkpoint_sha256'])
            self.assertEqual(checkpoint_sha, audit['before_checkpoint_sha256'])
            self.assertEqual(before['calls'][key]['record_sha256'], audit['failed_receipts'][key]['checkpoint_record_sha256'])
            self.assertTrue(allow_unknown_usage)
            return original_ack(instance, call_id, reason, allow_unknown_usage)
        with mock.patch.object(continuation.call_control.CallControl, 'acknowledge_failure', assert_audit):
            acknowledged = driver.acknowledge(key, 'Continue independent original IDs; do not retry.')
        self.assertFalse(acknowledged['paused']); self.assertIsNone(acknowledged['usage']['total_tokens'])
        self.assertEqual(1000, acknowledged['known_processed_token_subtotal'])
        after = control.snapshot()
        self.assertEqual(before['calls'], after['calls'])
        self.assertEqual(before['reducer_state']['requests'], after['reducer_state']['requests'])
        self.assertEqual(before_usage, control.report()['usage'])
        next_call = self.plan['calls'][2]
        expected, _, _ = self.original.answer_request(self.output, self.plan, next_call)
        captured = []
        def fake(request, folder, work):
            captured.append(copy.deepcopy(request)); return paid()
        result = driver.step(invoke=fake)
        self.assertEqual(next_call['id'], result['just_completed']); self.assertEqual([expected], captured)
        self.assertEqual(240, captured[0]['timeout_seconds'])
        self.assertEqual(1110, result['known_processed_token_subtotal']); self.assertIsNone(result['usage']['total_tokens'])
        self.assertFalse(result['original_plan_complete']); self.assertEqual([key], result['failed_call_ids'])
        self.assertEqual(receipt, receipt_path.read_bytes())
        self.assertEqual(before['calls'][key], control.snapshot()['calls'][key])
        self.assertEqual(originals, {name: (self.output / name).read_bytes() for name in originals})
        self.assertEqual({}, control.snapshot()['skipped'])
        self.assertNotIn('SECRET', json.dumps(result)); self.assertNotIn('secret.example', json.dumps(result))

    def test_failed_id_never_reruns_and_descendants_are_not_assembled(self):
        key = self.fail_next(); driver = self.driver(); driver.acknowledge(key, 'Keep original failure.')
        call = next(c for c in self.plan['calls'] if c['id'] == key)
        factory = driver.runner.answer_request
        def guarded(output, plan, row):
            self.assertNotEqual(call['session'], row['session']); return factory(output, plan, row)
        with mock.patch.object(driver.runner, 'answer_request', side_effect=guarded), \
             mock.patch.object(driver.runner, 'settle', wraps=driver.runner.settle) as settle:
            driver.step(invoke=mock.Mock(return_value=paid()))
            self.assertNotIn(key, [item.args[2]['id'] for item in settle.call_args_list])
        with self.assertRaises(continuation.call_control.ConflictingCallError):
            self.control().dispatch(key, call['session'], 'answer', 'native')
        result = driver.status(); deferred = {row['call_id']: row for row in result['deferred']}
        for row in self.plan['calls']:
            if row.get('session') == call['session'] and row['turn'] > 1:
                self.assertIn(key, deferred[row['id']]['failed_ancestor_call_ids'])
                self.assertFalse((self.output / 'records' / row['id']).exists())

    def test_pair_requires_full_nine_turn_sessions_and_never_judges_failed_pair(self):
        plan = self.plan; long_sid = plan['long_sessions'][0]
        pair = next(p for p in plan['pairs'] if long_sid in p['mask'].values())
        blocked = next(c for c in plan['calls'] if c.get('session') == long_sid and c['turn'] == 9)
        settled = {c['id'] for c in plan['calls'] if c['role'] == 'answer'} - {blocked['id']}
        state = {'calls': {c['id']: {'record': {}, 'failure_kind': None} for c in plan['calls'] if c['id'] in settled}}
        state['calls'][blocked['id']] = {'record': failed(), 'failure_kind': 'timeout'}
        ready, deferred = continuation.selection(plan, state, settled)
        judge = next(c for c in plan['calls'] if c.get('pair') == pair['id'])
        self.assertNotIn(judge, ready)
        self.assertEqual([blocked['id']], next(d['blocking_call_ids'] for d in deferred if d['call_id'] == judge['id']))
        self.assertEqual([c for c in plan['calls'] if c['role'] == 'judge' and c != judge], ready)
        # Behavioral dispatch proof with the pure scheduler's synthetic settlement
        # supplied at the boundary: the blocked judge factory is never entered.
        driver = self.driver(); control = self.control()
        fake_state = copy.deepcopy(control.snapshot()); fake_state['calls'] = state['calls']
        report = control.report()
        with mock.patch.object(driver, '_audit'), mock.patch.object(driver, '_settled', return_value=settled), \
             mock.patch.object(control, 'snapshot', return_value=fake_state), \
             mock.patch.object(control, 'report', return_value=report), \
             mock.patch.object(driver, '_control', return_value=control), \
             mock.patch.object(driver.runner, 'judge_request', side_effect=RuntimeError('selected ready judge')) as factory:
            with self.assertRaisesRegex(RuntimeError, 'selected ready judge'):
                driver.step(roles=('judge',), invoke=mock.Mock())
        self.assertEqual(ready[0], factory.call_args.args[2]); self.assertNotEqual(judge, factory.call_args.args[2])

    def test_pending_stale_and_unterminated_acknowledgments_fail_without_audit(self):
        first = self.plan['calls'][0]; control = self.control()
        control.dispatch(first['id'], first['session'], 'answer', 'native')
        driver = self.driver()
        with self.assertRaises(continuation.ContinueError):
            driver.acknowledge(first['id'], 'Cannot acknowledge pending.')
        self.assertFalse(driver.audit_dir.exists())
        control.complete(first['id'], failed(exit_code=None))
        with self.assertRaisesRegex(continuation.ContinueError, 'termination'):
            driver.acknowledge(first['id'], 'No termination proof.')
        with self.assertRaises(continuation.ContinueError):
            driver.acknowledge(self.plan['calls'][1]['id'], 'Wrong failure.')
        self.assertFalse(driver.audit_dir.exists())

    def test_duplicate_acknowledgment_is_rejected_without_rewriting_audit(self):
        key = self.fail_next(); driver = self.driver(); driver.acknowledge(key, 'One acknowledgment.')
        before = {p.name: p.read_bytes() for p in driver.audit_dir.iterdir()}
        checkpoint = self.control().checkpoint_path.read_bytes()
        with self.assertRaises(continuation.ContinueError):
            driver.acknowledge(key, 'One acknowledgment.')
        self.assertEqual(before, {p.name: p.read_bytes() for p in driver.audit_dir.iterdir()})
        self.assertEqual(checkpoint, self.control().checkpoint_path.read_bytes())

    def test_successful_receipt_local_recovery_does_not_repeat_native_call(self):
        driver = self.driver(); fake = mock.Mock(return_value=paid())
        settle = driver.runner.settle
        with mock.patch.object(driver.runner, 'settle', side_effect=OSError('offline local write failure')):
            with self.assertRaises(OSError):
                driver.step(invoke=fake)
        first = self.plan['calls'][0]['id']; self.assertFalse((self.output / 'records' / first / 'finished.json').exists())
        driver.runner.settle = settle
        driver.step(invoke=fake)
        self.assertEqual(2, fake.call_count)  # First ID recovered locally; only next ID dispatches.
        self.assertTrue((self.output / 'records' / first / 'finished.json').exists())
        self.assertEqual(2, self.control().report()['dispatched_calls'])

    def test_missing_old_finished_flag_cannot_overwrite_a_later_turn_history(self):
        driver = self.driver(); driver.step(invoke=mock.Mock(return_value=paid()))
        first = self.plan['calls'][0]
        second = next(c for c in self.plan['calls'] if c.get('session') == first['session'] and c['turn'] == 2)
        request, work, history = driver.runner.answer_request(self.output, self.plan, second)
        folder = self.output / 'records' / second['id']; folder.mkdir()
        driver.runner.write(folder / 'request.json', {'request': request, 'request_sha256': driver.runner._digest(request), 'call': second})
        driver.runner.write(folder / 'input-history.json', history)
        record = self.control().run(second['id'], second['session'], 'answer', 'native',
                                    mock.Mock(return_value=paid() | {'id': second['id']}))
        driver.runner.write(folder / 'native-record.json', record)
        driver.runner.settle(self.output, self.plan, second, record)
        history_path = self.output / 'sessions' / first['session'] / 'history.json'
        before_history = history_path.read_bytes(); before_conversation = (work / 'conversation.json').read_bytes()
        first_folder = self.output / 'records' / first['id']; old_artifacts = (first_folder / 'artifacts.json').read_bytes()
        (first_folder / 'finished.json').unlink(); fake = mock.Mock()
        with self.assertRaisesRegex(continuation.ContinueError, 'historical settlement'):
            driver.step(invoke=fake)
        fake.assert_not_called()
        self.assertEqual(before_history, history_path.read_bytes())
        self.assertEqual(before_conversation, (work / 'conversation.json').read_bytes())
        self.assertEqual(old_artifacts, (first_folder / 'artifacts.json').read_bytes())

    def test_pause_source_change_and_bad_amendment_block_native(self):
        driver = self.driver(); checkpoint = self.control().checkpoint_path.read_bytes()
        fake = mock.Mock(side_effect=AssertionError('must not dispatch'))
        pause = self.output / 'PAUSE_REQUESTED.json'; pause.write_text('{}')
        self.assertTrue(driver.step(invoke=fake)['operator_paused'])
        self.assertEqual(checkpoint, self.control().checkpoint_path.read_bytes()); self.assertFalse(driver.audit_dir.exists())
        pause.unlink()
        pin = driver.code_paths['driver']; old_sha = driver.code_sha256['driver']; driver.code_sha256['driver'] = '0' * 64
        with self.assertRaises(continuation.ContinueError):
            driver.step(invoke=fake)
        driver.code_sha256['driver'] = old_sha
        source = self.source / 'bench/conversation_native.py'; source.write_text(source.read_text() + '\n# changed\n')
        with self.assertRaises(operational.ResumeError):
            driver.step(invoke=fake)
        fake.assert_not_called(); self.assertEqual(checkpoint, self.control().checkpoint_path.read_bytes())
        self.amendment['max_cli_invocations'] = 193; self.amendment_path.write_bytes(operational._json(self.amendment))
        with self.assertRaises(operational.ResumeError):
            self.driver()

    def test_audit_binding_changed_after_restart_fails_closed(self):
        driver = self.driver(); driver.step(invoke=mock.Mock(return_value=paid()))
        manifest = driver._audit_read(driver.audit_dir / 'manifest.json')
        manifest['bindings']['operational_sha256']['driver'] = '0' * 64
        (driver.audit_dir / 'manifest.json').write_bytes(operational._json({'value': manifest, 'sha256': operational._digest(manifest)}))
        with self.assertRaises(continuation.ContinueError):
            self.driver()

    def test_audit_write_failure_prevents_acknowledgment(self):
        key = self.fail_next(); driver = self.driver(); before = self.control().snapshot()
        with mock.patch.object(driver, '_audit_write', side_effect=OSError('offline audit storage failure')):
            with self.assertRaises(OSError):
                driver.acknowledge(key, 'Audit must exist before changing pause.')
        self.assertEqual(before, self.control().snapshot())
        self.assertTrue(self.control().report()['paused'])

    def test_second_failure_requires_its_own_acknowledgment_and_keeps_first_audit(self):
        first = self.fail_next(); driver = self.driver(); driver.acknowledge(first, 'First failure acknowledged.')
        audit_path = driver.audit_dir / ('ack-' + first + '.json'); original_audit = audit_path.read_bytes()
        fake = mock.Mock(return_value=failed())
        with self.assertRaises(continuation.call_control.CallControlPaused) as raised:
            driver.step(invoke=fake)
        second = self.plan['calls'][1]['id']; self.assertEqual(second, raised.exception.call_id)
        self.assertEqual(1, fake.call_count)
        with self.assertRaises(continuation.ContinueError):
            driver.acknowledge(first, 'Historical acknowledgment cannot clear another failure.')
        result = driver.acknowledge(second, 'Second failure acknowledged, no retry.')
        self.assertFalse(result['paused']); self.assertEqual([first, second], result['failed_call_ids'])
        self.assertIsNone(result['usage']['total_tokens']); self.assertEqual(0, result['known_processed_token_subtotal'])
        self.assertEqual(original_audit, audit_path.read_bytes())
        second_audit = driver._audit_read(driver.audit_dir / ('ack-' + second + '.json'))
        self.assertEqual({first, second}, set(second_audit['failed_receipts']))
        self.assertFalse((self.output / 'records' / second / 'finished.json').exists())

    def test_runtime_uses_selected_native_with_real_fake_process_and_exact_request_hashes(self):
        path, policy = self.runtime_policy(); driver = self.driver(path)
        self.assertEqual(240, driver.runner.native.MAX_TIMEOUT_SECONDS)
        self.assertEqual(1200, driver.native.MAX_TIMEOUT_SECONDS)
        self.assertIsNot(driver.native, driver.runner.native)
        self.assertIs(driver.native.launch, driver.runner.native.launch)
        self.assertIs(driver.native.cli_record, driver.runner.native.cli_record)
        call = self.plan['calls'][0]
        original_request, work, _ = self.original.answer_request(self.output, self.plan, call)
        expected = original_request | {'timeout_seconds': 1200}
        real_start = driver.native.launch.start_process; commands = []
        script = """import json, sys
from pathlib import Path
Path('received.txt').write_text(sys.stdin.read())
Path(sys.argv[1]).write_text('Synthetic runtime response.')
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 20, 'cached_input_tokens': 7, 'output_tokens': 5}}), flush=True)
"""
        def start(command, **kwargs):
            commands.append(command)
            answer = command[command.index('--output-last-message') + 1]
            return real_start([sys.executable, '-c', script, answer], **kwargs)
        with mock.patch.object(driver.native.shutil, 'which', return_value='/offline/fake-codex'), \
             mock.patch.object(driver.native.launch, 'start_process', side_effect=start), \
             mock.patch.object(driver.runner.native, 'invoke', side_effect=AssertionError('runtime must select current adapter')):
            result = driver.step()  # Deliberately no injected invoke: exercise adapter selection.
        self.assertEqual(call['id'], result['just_completed']); self.assertEqual(1, len(commands))
        self.assertEqual(25, result['known_processed_token_subtotal'])
        self.assertEqual('runtime-0001', result['execution_policy_id']); self.assertEqual(1200, result['next_unstarted_timeout_seconds'])
        folder = self.output / 'records' / call['id']
        request = operational._read(folder / 'request.json')
        receipt = operational._read(folder / 'native-record.json')
        invocation = operational._read(folder / 'native-invocation.json')
        self.assertEqual(expected, request['request'])
        self.assertEqual(original_request['prompt'], (work / 'received.txt').read_text())
        self.assertEqual(original_request['model'], commands[0][commands[0].index('--model') + 1])
        self.assertIn('model_reasoning_effort="' + original_request['effort'] + '"', commands[0])
        self.assertEqual(1200, invocation['timeout_seconds'])
        self.assertEqual(operational._digest(expected), request['request_sha256'])
        self.assertEqual(request['request_sha256'], receipt['request_sha256'])
        self.assertEqual(request['request_sha256'], invocation['request_sha256'])
        self.assertEqual(operational._digest(receipt), operational._read(folder / 'finished.json')['record_sha256'])
        self.assertEqual('budget-0001--runtime-0001', driver.audit_dir.name)
        manifest = driver._audit_read(driver.audit_dir / 'manifest.json')
        self.assertEqual(operational._digest(policy), manifest['bindings']['execution_policy']['sha256'])
        self.assertEqual(policy['native_sha256'], manifest['bindings']['operational_sha256']['execution_native'])

    def test_runtime_audit_isolation_preserves_older_policy_receipts_and_failed_ids(self):
        older = self.driver(); older.step(invoke=mock.Mock(return_value=paid()))
        first_folder = self.output / 'records' / self.plan['calls'][0]['id']
        first_files = {p.name: p.read_bytes() for p in first_folder.iterdir()}
        with self.assertRaises(continuation.call_control.CallControlPaused):
            older.step(invoke=mock.Mock(return_value=failed()))
        failed_id = self.plan['calls'][1]['id']; old_receipt = self.control().snapshot()['calls'][failed_id]
        original_audit = {p.name: p.read_bytes() for p in older.audit_dir.iterdir()}
        policy_path, _ = self.runtime_policy(); policy_bytes = policy_path.read_bytes()
        driver = self.driver(policy_path)
        acknowledged = driver.acknowledge(failed_id, 'New deadline only for untouched independent IDs.')
        self.assertFalse(acknowledged['paused']); self.assertEqual([failed_id], acknowledged['failed_call_ids'])
        captured = []
        def fake(request, folder, work):
            captured.append(request); return paid() | {'request_sha256': operational._digest(request)}
        result = driver.step(invoke=fake)
        self.assertEqual(self.plan['calls'][2]['id'], result['just_completed'])
        self.assertEqual(1200, captured[0]['timeout_seconds'])
        self.assertEqual(old_receipt, self.control().snapshot()['calls'][failed_id])
        self.assertFalse((self.output / 'records' / failed_id / 'finished.json').exists())
        self.assertEqual(original_audit, {p.name: p.read_bytes() for p in older.audit_dir.iterdir()})
        self.assertEqual(first_files, {p.name: p.read_bytes() for p in first_folder.iterdir()})
        self.assertEqual(policy_bytes, policy_path.read_bytes())
        self.assertFalse(result['original_plan_complete']); self.assertEqual(192, result['planned_calls'])
        with self.assertRaises(continuation.call_control.ConflictingCallError):
            self.control().dispatch(failed_id, self.plan['calls'][1]['session'], 'answer', 'native')

    def test_default_still_uses_frozen_adapter_and_240_second_request(self):
        driver = self.driver(); self.assertIs(driver.native, driver.runner.native)
        self.assertEqual(240, driver.native.MAX_TIMEOUT_SECONDS)
        with mock.patch.object(driver.runner.native, 'invoke', return_value=paid()) as invoked:
            result = driver.step()
        self.assertEqual(240, invoked.call_args.args[0]['timeout_seconds'])
        self.assertIsNone(result['execution_policy_id']); self.assertEqual(240, result['next_unstarted_timeout_seconds'])
        self.assertEqual('budget-0001', driver.audit_dir.name)
        self.assertNotIn('execution_native', driver.code_sha256)

    def test_runtime_policy_scope_and_native_hash_fail_before_mutation(self):
        path, original = self.runtime_policy(); before = self.control().checkpoint_path.read_bytes()
        changes = [{'native_sha256': '0' * 64}, {'original_plan_sha256': '0' * 64},
                   {'budget_amendment_sha256': '0' * 64}, {'previous_timeout_seconds': 239},
                   {'timeout_seconds': 1201}, {'max_cli_invocations': 193}, {'automatic_retries': 1},
                   {'claude_calls': 1}, {'policy_id': '../runtime-0001'}, {'version': True},
                   {'operator': original['operator'] | {'actor': 'user'}},
                   {'operator': original['operator'] | {'rationale': ''}},
                   {'operator': original['operator'] | {'recorded_at': '2026-09-09'}}]
        for change in changes:
            with self.subTest(change=change):
                path.write_bytes(operational._json(original | change))
                with self.assertRaises(continuation.ContinueError):
                    self.driver(path)
                self.assertEqual(before, self.control().checkpoint_path.read_bytes())
        self.assertFalse((self.output / 'continuation-audit').exists())

    def test_runtime_native_source_change_and_policy_change_fail_closed(self):
        path, policy = self.runtime_policy()
        copied = self.root / 'operational-copy'; copied.mkdir()
        for name in ('conversation_continue.py', 'conversation_native.py'):
            shutil.copyfile(ROOT / 'bench' / name, copied / name)
        with mock.patch.object(continuation, '__file__', str(copied / 'conversation_continue.py')):
            driver = self.driver(path)
        driver.step(invoke=mock.Mock(return_value=paid()))
        before = self.control().checkpoint_path.read_bytes()
        manifest = (driver.audit_dir / 'manifest.json').read_bytes(); fake = mock.Mock()
        selected = copied / 'conversation_native.py'; original_native = selected.read_bytes()
        selected.write_bytes(original_native + b'\n# changed after source pin\n')
        with self.assertRaisesRegex(continuation.ContinueError, 'source changed'):
            driver.step(invoke=fake)
        selected.write_bytes(original_native)
        path.write_bytes(operational._json(policy | {'operator': policy['operator'] | {'rationale': 'Changed later.'}}))
        with self.assertRaisesRegex(continuation.ContinueError, 'policy changed'):
            driver.step(invoke=fake)
        fake.assert_not_called(); self.assertEqual(before, self.control().checkpoint_path.read_bytes())
        self.assertEqual(manifest, (driver.audit_dir / 'manifest.json').read_bytes())

    def test_runtime_does_not_overwrite_a_prepared_240_second_request(self):
        first = self.plan['calls'][0]; original_request, work, history = self.original.answer_request(self.output, self.plan, first)
        folder = self.output / 'records' / first['id']; folder.mkdir(parents=True)
        self.original.write(folder / 'request.json', {'request': original_request, 'request_sha256': operational._digest(original_request), 'call': first})
        self.original.write(folder / 'input-history.json', history)
        before = (folder / 'request.json').read_bytes(); path, _ = self.runtime_policy(); fake = mock.Mock()
        with self.assertRaisesRegex(continuation.ContinueError, 'prepared original request changed'):
            self.driver(path).step(invoke=fake)
        fake.assert_not_called(); self.assertEqual(before, (folder / 'request.json').read_bytes())
        self.assertEqual(0, self.control().report()['dispatched_calls'])

    def test_cli_does_not_print_provider_exception_or_endpoint(self):
        with mock.patch.object(continuation, 'Continue', side_effect=RuntimeError('https://secret.example/?token=SECRET')), \
             mock.patch('sys.stdout', new_callable=io.StringIO) as stream:
            code = continuation.main(['--source', str(self.source), '--output', str(self.output),
                                      '--amendment', str(self.amendment_path), 'answers'])
        self.assertEqual(1, code); self.assertNotIn('SECRET', stream.getvalue()); self.assertNotIn('secret.example', stream.getvalue())
        self.assertTrue(json.loads(stream.getvalue())['stopped'])

    def test_missing_original_checkpoint_is_never_reinitialized(self):
        self.fail_next(); driver = self.driver(); checkpoint = self.output / 'controller/checkpoint.json'
        checkpoint.unlink(); fake = mock.Mock()
        with self.assertRaises(FileNotFoundError):
            driver.step(invoke=fake)
        fake.assert_not_called(); self.assertFalse(checkpoint.exists()); self.assertFalse(driver.audit_dir.exists())

    def test_outer_experiment_lock_prevents_duplicate_work(self):
        driver = self.driver(); fake = mock.Mock()
        with self.original.exclusive(self.output):
            with self.assertRaises(BlockingIOError):
                driver.step(invoke=fake)
            with self.assertRaises(BlockingIOError):
                driver.acknowledge(self.plan['calls'][0]['id'], 'No concurrent operator mutation.')
        fake.assert_not_called(); self.assertFalse(driver.audit_dir.exists())

    def test_status_has_no_audit_side_effects_or_raw_receipt_content(self):
        self.fail_next(); driver = self.driver(); checkpoint = self.control().checkpoint_path.read_bytes()
        result = driver.status()
        self.assertEqual(192, result['planned_calls']); self.assertEqual(1, result['failed_calls'])
        self.assertIsNone(result['usage']['total_tokens']); self.assertEqual(0, result['known_processed_token_subtotal'])
        self.assertFalse(driver.audit_dir.exists()); self.assertEqual(checkpoint, self.control().checkpoint_path.read_bytes())
        self.assertNotIn('SECRET', json.dumps(result)); self.assertNotIn('secret.example', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
