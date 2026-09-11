"""Offline schedule, information-boundary and paid-call recovery regressions.

The fixture contains a tiny public skill archive and synthetic files. Native
workspace preparation and the durable ledger are real; every invocation is fake.
"""
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_ablation as runner


def paid_record(answer='已比較候選；未知的部分仍待查證。', **changes):
    value = {'status': 'complete', 'exit_code': 0, 'timeout': False,
             'errors': [], 'tool_events': [], 'malformed_event_lines': 0,
             'terminal_usage_events': 1,
             'direct_terminal_usage': {'input_tokens': 100,
                                      'cached_input_tokens': 20,
                                      'output_tokens': 10},
             'answer': answer}
    value.update(changes)
    return value


class ConversationAblationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.repo = self.directory / 'fixture-repo'
        self.repo.mkdir()
        self.output = self.directory / 'run'
        self.scenario = json.loads((ROOT / runner.BASE / 'scenario.json').read_text())
        self.rubric = json.loads((ROOT / runner.BASE / 'rubric.json').read_text())
        for relative in runner.SOURCES:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('frozen offline source: ' + relative + '\n')
        (self.repo / runner.BASE / 'scenario.json').write_text(json.dumps(self.scenario))
        (self.repo / runner.BASE / 'rubric.json').write_text(json.dumps(self.rubric))
        (self.repo / runner.BASE / 'skill-outcome.md').write_text('OUTCOME_ENTRY_ONLY\n')
        with zipfile.ZipFile(self.repo / 'dist/pea-princess-skill.zip', 'w') as archive:
            archive.writestr('pea-princess/SKILL.md', 'BASELINE_ENTRY_ONLY\n')
            archive.writestr('pea-princess/references/inputs.md', 'BULK_INPUT_GUIDANCE\n')
            archive.writestr('pea-princess/references/onboarding.md', 'BULK_ONBOARDING_GUIDANCE\n')
            archive.writestr('pea-princess/scripts/calc.py', '# deterministic test fixture\n')
        self.root_patch = mock.patch.object(runner, 'ROOT', self.repo)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.git_patch = mock.patch.object(runner.subprocess, 'check_output', return_value='offline-source-commit\n')
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def prepare(self):
        result = runner.prepare(self.output)
        self.assertEqual(result['live_calls'], 0)
        return runner.read(self.output / 'plan.json')

    def first_call(self, plan):
        return plan['calls'][0]

    def call_for(self, plan, session, turn):
        return next(c for c in plan['calls'] if c.get('session') == session and c.get('turn') == turn)

    def history_before(self, plan, session, turn):
        history = []
        for number in range(1, turn):
            history.extend([{'role': 'user', 'turn': number, 'text': 'EARLIER_USER_%d' % number},
                            {'role': 'assistant', 'turn': number, 'text': 'EARLIER_ANSWER_%d' % number}])
        runner.write(self.output / 'sessions' / session / 'history.json', history)
        if turn > 1:
            runner.write(self.output / 'records' / (session + '-t%02d' % (turn - 1)) / 'finished.json',
                         {'history_sha256': runner._digest(history)})
        return history

    def test_complete_factorial_and_exact_192_call_schedule(self):
        sessions, pairs, calls = runner.layout()
        self.assertEqual(len(sessions), 48)
        self.assertEqual(len(pairs), 24)
        self.assertEqual(len(calls), 192)
        self.assertEqual(len({c['id'] for c in calls}), 192)
        self.assertEqual(sum(c['role'] == 'answer' for c in calls), 48 * 3 + 4 * 6)
        self.assertEqual(sum(s['turns'] == 9 for s in sessions), 4)
        self.assertEqual(len({(s['model'], s['effort'], s['depth'], s['arm']) for s in sessions}), 48)
        self.assertTrue(all(c['role'] == 'answer' for c in calls[:168]))
        self.assertTrue(all(c['role'] == 'judge' for c in calls[168:]))
        for session in sessions:
            observed = [c['turn'] for c in calls if c.get('session') == session['id']]
            self.assertEqual(observed, list(range(1, session['turns'] + 1)))
        by_id = {s['id']: s for s in sessions}
        for pair in pairs:
            left, right = (by_id[pair['mask'][key]] for key in ('A', 'B'))
            for factor in ('model', 'effort', 'depth'):
                self.assertEqual(left[factor], right[factor])
            self.assertNotEqual(left['arm'].split('-')[1], right['arm'].split('-')[1])
            self.assertEqual({left['arm'].split('-')[0], right['arm'].split('-')[0]}, {'existing', 'outcome'})
            self.assertEqual(left['turns'], right['turns'])
        self.assertEqual(runner.layout(), (sessions, pairs, calls))

    def test_prepare_makes_real_owned_workspaces_without_future_or_grader_data(self):
        plan = self.prepare()
        for session in plan['sessions']:
            work = self.output / 'sessions' / session['id'] / 'work'
            runner.native._validate_workspace(work)
            expected = 'OUTCOME_ENTRY_ONLY' if session['arm'].startswith('outcome') else 'BASELINE_ENTRY_ONLY'
            self.assertIn(expected, (work / 'skill/SKILL.md').read_text())
            self.assertTrue((work / 'documents/catalog.json').exists())
            self.assertFalse((work / 'documents/update-v2.json').exists())
            self.assertFalse((work / 'rubric.json').exists())
            self.assertFalse((work / 'scenario.json').exists())
            visible = '\n'.join(p.read_text() for p in work.rglob('*') if p.is_file())
            self.assertNotIn(self.scenario['judge_only']['prefix_outcome'], visible)
        with self.assertRaises(ValueError):
            runner.prepare(self.output)

    def test_bulk_only_preloads_guidance_and_neither_prompt_contains_private_gold(self):
        plan = self.prepare()
        for arm in runner.ARMS:
            session = next(s for s in plan['sessions'] if s['arm'] == arm)
            request, work, history = runner.answer_request(self.output, plan, self.call_for(plan, session['id'], 1))
            self.assertEqual('BULK_ONBOARDING_GUIDANCE' in request['prompt'], arm.endswith('-bulk'))
            self.assertEqual('BULK_INPUT_GUIDANCE' in request['prompt'], arm.endswith('-bulk'))
            self.assertNotIn('judge_only', request['prompt'])
            self.assertNotIn(self.scenario['judge_only']['prefix_outcome'], request['prompt'])
            self.assertNotIn('compact_pair_record_schema', request['prompt'])
            self.assertEqual(len(history), 1)
            self.assertEqual(runner.read(work / 'conversation.json'), history)

    def test_resume_omits_prompt_history_but_retains_exact_file_history_and_releases_v2(self):
        plan = self.prepare()
        session = next(s for s in plan['sessions'] if s['turns'] == 9)
        previous = self.history_before(plan, session['id'], 6)
        work = self.output / 'sessions' / session['id'] / 'work'
        original_catalog = (work / 'documents/catalog.json').read_bytes()
        request, work, history = runner.answer_request(self.output, plan, self.call_for(plan, session['id'], 6))
        self.assertNotIn('EARLIER_USER_1', request['prompt'])
        self.assertIn('conversation.json', request['prompt'])
        self.assertEqual(history[:-1], previous)
        self.assertEqual(runner.read(work / 'conversation.json'), history)
        self.assertEqual((work / 'documents/catalog.json').read_bytes(), original_catalog)
        self.assertEqual(runner.read(work / 'documents/update-v2.json'), self.scenario['turns'][5]['files']['documents/update-v2.json'])
        self.assertEqual(len(history), 11)

    def test_non_resume_turn_preserves_full_dialogue_and_reaction_is_labeled_synthetic(self):
        plan = self.prepare()
        session = plan['sessions'][0]['id']
        previous = self.history_before(plan, session, 2)
        previous[-1]['text'] = '一？二？三？四？'
        runner.write(self.output / 'sessions' / session / 'history.json', previous)
        runner.write(self.output / 'records' / (session + '-t01') / 'finished.json',
                     {'history_sha256': runner._digest(previous)})
        request, _, history = runner.answer_request(self.output, plan, self.call_for(plan, session, 2))
        self.assertIn('EARLIER_USER_1', request['prompt'])
        self.assertEqual(history[-1]['synthetic_reaction_branch'], 'question_burden_proxy')
        self.assertIn(self.scenario['turns'][1]['user'], history[-1]['text'])
        self.assertNotIn('human_satisfaction', history[-1])

    def test_source_version_change_blocks_before_invocation(self):
        self.prepare()
        source = self.repo / runner.SOURCES[0]
        source.write_text(source.read_text() + '# changed\n')
        fake = mock.Mock()
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        fake.assert_not_called()

    def test_copied_scenario_and_rubric_changes_rejected(self):
        self.prepare()
        for name in ('scenario.json', 'rubric.json'):
            with self.subTest(name=name):
                path = self.output / name
                original = path.read_bytes()
                value = json.loads(original)
                value['unexpected_source_change'] = True
                runner.write(path, value)
                with self.assertRaises(ValueError):
                    runner.verify_plan(self.output)
                path.write_bytes(original)

    def test_plan_model_and_budget_changes_rejected(self):
        plan = self.prepare()
        path = self.output / 'plan.json'
        original = path.read_bytes()
        for field in ('model', 'token_limit', 'mask'):
            with self.subTest(field=field):
                changed = copy.deepcopy(plan)
                if field == 'model':
                    changed['sessions'][0]['model'] = 'unplanned-model'
                elif field == 'token_limit':
                    changed['processed_token_stop_before_next_call'] += 1
                else:
                    changed['pairs'][0]['mask']['A'] = changed['pairs'][0]['mask']['B']
                runner.write(path, changed)
                with self.assertRaises(ValueError):
                    runner.verify_plan(self.output)
                path.write_bytes(original)

    def test_model_modified_source_blocks_before_dispatch(self):
        plan = self.prepare()
        call = self.first_call(plan)
        work = self.output / 'sessions' / call['session'] / 'work'
        (work / 'documents/catalog.json').write_text('{"rewritten_by_model":true}\n')
        fake = mock.Mock()
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        fake.assert_not_called()

    def test_changed_prior_message_is_rejected_even_when_turn_count_matches(self):
        plan = self.prepare()
        runner.run_next(self.output, invoke=mock.Mock(return_value=paid_record()))
        first = self.first_call(plan)
        history_path = self.output / 'sessions' / first['session'] / 'history.json'
        history = runner.read(history_path)
        history[0]['text'] = 'An altered old requirement that the user never supplied.'
        runner.write(history_path, history)
        with self.assertRaises(ValueError):
            runner.answer_request(self.output, plan, self.call_for(plan, first['session'], 2))

    def test_source_changed_during_paid_call_is_captured_then_blocks_further_calls(self):
        plan = self.prepare()
        def fake(request, folder, work):
            (work / 'documents/catalog.json').write_text('{"silently_changed":true}\n')
            return paid_record('已完成。')
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        call = self.first_call(plan)
        record_dir = self.output / 'records' / call['id']
        self.assertTrue((record_dir / 'native-record.json').exists())
        self.assertTrue((record_dir / 'artifacts.json').exists())
        self.assertFalse((record_dir / 'finished.json').exists())
        retry = mock.Mock()
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=retry)
        retry.assert_not_called()
        self.assertEqual(runner.status(self.output)['dispatched_calls'], 1)

    def test_paid_result_records_actual_artifact_bytes_not_save_claim(self):
        plan = self.prepare()
        def fake(request, folder, work):
            (work / 'real-note.txt').write_text('Actual saved requirement: £2,250\n')
            return paid_record('已儲存 imagined-report.json。')
        result = runner.run_next(self.output, invoke=fake)
        call = self.first_call(plan)
        self.assertEqual(result['just_completed'], call['id'])
        artifacts = runner.read(self.output / 'records' / call['id'] / 'artifacts.json')
        self.assertNotIn('imagined-report.json', artifacts)
        self.assertEqual(base64.b64decode(artifacts['real-note.txt']['base64']).decode(), 'Actual saved requirement: £2,250\n')
        self.assertFalse(any(name.startswith('skill/') for name in artifacts))
        history = runner.read(self.output / 'sessions' / call['session'] / 'history.json')
        self.assertEqual([m['role'] for m in history], ['user', 'assistant'])
        self.assertEqual(result['usage']['total_tokens'], 110)

    def test_failed_paid_call_is_paused_and_never_retried(self):
        self.prepare()
        fake = mock.Mock(return_value=paid_record(status='stopped', errors=[{'type': 'provider_failure'}]))
        with self.assertRaises(Exception):
            runner.run_next(self.output, invoke=fake)
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        self.assertEqual(fake.call_count, 1)
        state = runner.status(self.output)
        self.assertEqual(state['dispatched_calls'], 1)
        self.assertEqual(state['failed_calls'], 1)
        self.assertEqual(state['usage']['total_tokens'], 110)

    def test_receipt_write_failure_preserves_known_paid_usage_and_stops(self):
        self.prepare()
        original_write = runner.write
        def interrupted_write(path, value):
            if Path(path).name == 'native-record.json':
                raise OSError('synthetic disk failure after paid result')
            return original_write(path, value)
        fake = mock.Mock(return_value=paid_record())
        with mock.patch.object(runner, 'write', side_effect=interrupted_write):
            with self.assertRaises(OSError):
                runner.run_next(self.output, invoke=fake)
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        self.assertEqual(fake.call_count, 1)
        state = runner.status(self.output)
        self.assertEqual(state['usage']['total_tokens'], 110)
        self.assertEqual(state['failed_calls'], 1)

    def test_new_output_under_skill_directory_is_captured(self):
        plan = self.prepare()
        def fake(request, folder, work):
            (work / 'skill/saved-comparison.txt').write_text('A remains over budget.\n')
            return paid_record()
        runner.run_next(self.output, invoke=fake)
        rows = runner.read(self.output / 'records' / self.first_call(plan)['id'] / 'artifacts.json')
        self.assertIn('skill/saved-comparison.txt', rows)
        self.assertNotIn('skill/SKILL.md', rows)
        self.assertNotIn('skill/references/onboarding.md', rows)

    def test_unknown_usage_and_pending_invocations_block_new_calls(self):
        plan = self.prepare()
        control = runner.CallControl(self.output / 'controller', [c['id'] for c in plan['calls']], allow_tools=True)
        call = self.first_call(plan)
        control.dispatch(call['id'], call['session'], call['role'], 'native')
        fake = mock.Mock()
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        fake.assert_not_called()
        control.complete(call['id'], paid_record(terminal_usage_events=0, direct_terminal_usage=None))
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        fake.assert_not_called()
        self.assertIsNone(runner.status(self.output)['usage']['total_tokens'])

    def test_token_threshold_blocks_the_next_invocation(self):
        self.prepare()
        fake = mock.Mock(return_value=paid_record(direct_terminal_usage={
            'input_tokens': runner.TOKEN_LIMIT, 'cached_input_tokens': 0, 'output_tokens': 0}))
        runner.run_next(self.output, invoke=fake)
        with self.assertRaises(ValueError):
            runner.run_next(self.output, invoke=fake)
        self.assertEqual(fake.call_count, 1)

    def test_operator_pause_before_first_dispatch_preserves_ledger_and_inputs(self):
        self.prepare()
        runner.write(self.output / 'PAUSE_REQUESTED.json', {'reason': 'Offline operator pause fixture'})
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        histories = {p: p.read_bytes() for p in (self.output / 'sessions').glob('*/history.json')}
        fake = mock.Mock(side_effect=AssertionError('paused run must never invoke'))
        with mock.patch.object(runner, 'answer_request', side_effect=AssertionError('paused run must not assemble or mutate inputs')):
            result = runner.run_next(self.output, invoke=fake)
        fake.assert_not_called()
        self.assertTrue(result['operator_paused'])
        self.assertEqual(0, result['dispatched_calls'])
        self.assertEqual(0, result['completed_calls'])
        self.assertEqual(before, checkpoint.read_bytes())
        self.assertFalse((self.output / 'records').exists())
        self.assertEqual(histories, {p: p.read_bytes() for p in histories})

    def test_operator_pause_after_paid_call_keeps_exact_usage_without_another_callback(self):
        self.prepare()
        fake = mock.Mock(return_value=paid_record())
        first = runner.run_next(self.output, invoke=fake)
        runner.write(self.output / 'PAUSE_REQUESTED.json', {'reason': 'Pause before the next paid call'})
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        records = {str(p.relative_to(self.output)): p.read_bytes()
                   for p in (self.output / 'records').rglob('*') if p.is_file()}
        with mock.patch.object(runner, 'settle', side_effect=AssertionError('pause must precede materialization')):
            result = runner.run_next(self.output, invoke=fake)
        self.assertTrue(result['operator_paused'])
        self.assertEqual(1, fake.call_count)
        self.assertEqual(1, result['dispatched_calls'])
        self.assertEqual(first['usage'], result['usage'])
        self.assertEqual(110, result['usage']['total_tokens'])
        self.assertEqual(before, checkpoint.read_bytes())
        self.assertEqual(records, {str(p.relative_to(self.output)): p.read_bytes()
                                  for p in (self.output / 'records').rglob('*') if p.is_file()})

    def test_answers_cli_exits_after_operator_pause_instead_of_busy_looping(self):
        self.prepare()
        runner.write(self.output / 'PAUSE_REQUESTED.json', {'reason': 'Offline pause fixture'})
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        with mock.patch.object(sys, 'argv', ['conversation_ablation.py', 'answers', '--output', str(self.output)]), \
                mock.patch.object(runner, 'run_next', wraps=runner.run_next) as next_call, \
                mock.patch.object(runner.native, 'invoke', side_effect=AssertionError('paused CLI must not invoke')) as native_call, \
                mock.patch('builtins.print'):
            self.assertEqual(0, runner.main())
        self.assertEqual(1, next_call.call_count)
        native_call.assert_not_called()
        self.assertEqual(before, checkpoint.read_bytes())

    def test_post_receipt_crash_recovers_without_second_model_call_or_duplicate_history(self):
        plan = self.prepare()
        fake = mock.Mock(return_value=paid_record())
        with mock.patch.object(runner, 'artifact_snapshot', side_effect=OSError('synthetic snapshot interruption')):
            with self.assertRaises(OSError):
                runner.run_next(self.output, invoke=fake)
        self.assertEqual(fake.call_count, 1)
        runner.run_next(self.output, roles=('judge',),
                        invoke=mock.Mock(side_effect=AssertionError('local recovery must not invoke a model')))
        call = self.first_call(plan)
        history = runner.read(self.output / 'sessions' / call['session'] / 'history.json')
        self.assertEqual([m['role'] for m in history], ['user', 'assistant'])
        self.assertTrue((self.output / 'records' / call['id'] / 'finished.json').exists())
        self.assertEqual(runner.status(self.output)['dispatched_calls'], 1)

    def test_pair_has_whole_histories_and_real_prefix_and_continuation_artifacts(self):
        plan = self.prepare()
        pair = next(p for p in plan['pairs'] if any(s['id'] in p['mask'].values() and s['turns'] == 9 for s in plan['sessions']))
        for label, sid in pair['mask'].items():
            session = next(s for s in plan['sessions'] if s['id'] == sid)
            self.history_before(plan, sid, session['turns'] + 1)
            for number in (3, 9):
                if number > session['turns']:
                    continue
                runner.write(self.output / 'records' / (sid + '-t%02d' % number) / 'artifacts.json', {
                    'report.json': {'bytes': 2, 'sha256': 'fixture', 'base64': base64.b64encode(b'{}').decode()},
                    'documents/catalog.json': {'bytes': 2, 'sha256': 'fixture', 'base64': base64.b64encode(b'{}').decode()}})
        packet = runner.make_pair(self.output, plan, pair)
        self.assertEqual(set(packet['candidates']), {'A', 'B'})
        for label, value in packet['candidates'].items():
            self.assertNotIn('model', value)
            self.assertNotIn('arm', value)
            self.assertNotIn('effort', value)
            self.assertIn('3', value['artifacts_by_turn'])
            expected_turns = 9 if value['continuation_available'] else 3
            self.assertEqual(len(value['transcript']), expected_turns * 2)
            self.assertEqual('9' in value['artifacts_by_turn'], value['continuation_available'])
            self.assertNotIn('documents/catalog.json', value['artifacts_by_turn']['3'])

    def test_judge_workspace_has_grader_data_and_preserves_blind_candidate_keys(self):
        plan = self.prepare()
        call = next(c for c in plan['calls'] if c['role'] == 'judge')
        request, work, history = runner.judge_request(self.output, plan, call)
        self.assertIsNone(history)
        runner.native._validate_workspace(work)
        packet = runner.read(work / 'packet.json')
        self.assertEqual(set(packet['candidates']), {'A', 'B'})
        self.assertIn('judge_only', packet['case'])
        schema = request['response_schema']
        self.assertEqual(schema['type'], 'object')
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), set(self.rubric['compact_pair_record_schema']['required']))
        self.assertNotIn('"$ref"', json.dumps(schema))
        reasons = schema['properties']['common_prefix']['properties']['A']['properties']['unscored_reasons']
        self.assertEqual(set(reasons['required']), {row['id'] for row in self.rubric['dimensions']})
        self.assertFalse(reasons['additionalProperties'])

    def test_judge_masks_artifact_names_bytes_and_tool_traces_without_changing_originals(self):
        plan = self.prepare()
        call = next(c for c in plan['calls'] if c['role'] == 'judge')
        pair = next(p for p in plan['pairs'] if p['id'] == call['pair'])
        label, sid = next(iter(pair['mask'].items()))
        record_dir = self.output / 'records' / (sid + '-t03')
        original = b'{"generated_by":{"model":"gpt-6-astra"},"finding":"observed 30 minutes"}'
        rows = {'gpt-6-astra-report.json': {'bytes': len(original), 'sha256': 'fixture',
                                         'base64': base64.b64encode(original).decode()}}
        runner.write(record_dir / 'artifacts.json', rows)
        runner.write(record_dir / 'native-record.json', {'tool_events': [
            {'type': 'command_execution', 'command': 'cat gpt-6-astra-report.json',
             'aggregated_output': 'observed 30 minutes'}]})
        _, work, _ = runner.judge_request(self.output, plan, call)
        packet = runner.read(work / 'packet.json')
        candidate = packet['candidates'][label]
        for artifact in candidate['artifacts_by_turn']['3'].values():
            self.assertTrue((work / artifact['file']).is_file(), artifact['file'])
            self.assertNotIn('gpt-6-astra', artifact['file'])
            content = (work / artifact['file']).read_text()
            self.assertNotIn('gpt-6-astra', content)
            self.assertIn('observed 30 minutes', content)
        self.assertTrue(candidate['tool_trace_files'])
        for name in candidate['tool_trace_files']:
            self.assertNotIn('gpt-6-astra', (work / name).read_text())
            self.assertIn('observed 30 minutes', (work / name).read_text())
        self.assertEqual(runner.read(record_dir / 'artifacts.json'), rows)

    def test_judge_keeps_new_model_documents_but_omits_exact_installed_sources(self):
        plan = self.prepare()
        call = next(c for c in plan['calls'] if c['role'] == 'judge')
        pair = next(p for p in plan['pairs'] if p['id'] == call['pair'])
        label, sid = next(iter(pair['mask'].items()))
        row = {'bytes': 2, 'sha256': 'fixture', 'base64': base64.b64encode(b'{}').decode()}
        runner.write(self.output / 'records' / (sid + '-t03') / 'artifacts.json', {
            'documents/catalog.json': row, 'documents/README.md': row,
            'documents/report.json': row, 'requirements.json': row})
        packet = runner.make_pair(self.output, plan, pair)
        outputs = packet['candidates'][label]['artifacts_by_turn']['3']
        self.assertIn('documents/report.json', outputs)
        self.assertIn('requirements.json', outputs)
        self.assertNotIn('documents/catalog.json', outputs)
        self.assertNotIn('documents/README.md', outputs)

    def test_archive_path_traversal_rejected(self):
        with zipfile.ZipFile(self.repo / 'dist/pea-princess-skill.zip', 'w') as archive:
            archive.writestr('pea-princess/SKILL.md', 'entry')
            archive.writestr('../escape.txt', 'escape')
        with self.assertRaises(ValueError):
            runner.public_skill()


if __name__ == '__main__':
    unittest.main()
