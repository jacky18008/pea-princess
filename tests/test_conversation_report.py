"""Synthetic frozen-run aggregates; no model calls or live transcript reads."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_report as report
from call_control import CallControl, CallControlPaused, _digest

SECRET = 'PRIVATE_TEXT_MUST_NOT_APPEAR_IN_AGGREGATES'


class ConversationReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.run = self.directory / 'original-run'
        self.run.mkdir()
        self.rubric = json.loads((ROOT / 'evals/conversation-quality/rubric.json').read_text())
        arms = ['existing-bulk', 'existing-routed', 'outcome-bulk', 'outcome-routed']
        sessions = [{'id': 's%d' % (i + 1), 'model': 'model-a', 'effort': 'low',
                     'depth': 'standard', 'arm': arm, 'turns': 9 if i in (0, 3) else 3}
                    for i, arm in enumerate(arms)]
        pairs = [{'id': 'j01', 'mask': {'A': 's1', 'B': 's4'}},
                 {'id': 'j02', 'mask': {'A': 's2', 'B': 's3'}}]
        calls = [{'id': s['id'] + '-t%02d' % n, 'role': 'answer', 'session': s['id'], 'turn': n}
                 for n in range(1, 10) for s in sessions if n <= s['turns']]
        calls += [{'id': p['id'], 'role': 'judge', 'pair': p['id']} for p in pairs]
        self.plan = {'source_commit': 'deadbeef0123456789', 'sessions': sessions, 'pairs': pairs,
                     'calls': calls, 'judge_model': 'model-a', 'judge_effort': 'low',
                     'source_sha256': {}, 'limits': SECRET}
        self.write('plan.json', self.plan)
        self.write('rubric.json', self.rubric)
        self.write('scenario.json', {'judge_only': SECRET})
        self.write('frozen.json', {'plan_sha256': _digest(self.plan),
                                  'rubric_sha256': self.sha('rubric.json'),
                                  'scenario_sha256': self.sha('scenario.json')})
        self.control = CallControl(self.run / 'controller', [c['id'] for c in calls], allow_tools=True)

    def write(self, relative, value):
        path = self.run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))

    def sha(self, relative):
        return hashlib.sha256((self.run / relative).read_bytes()).hexdigest()

    def files(self):
        return {str(p.relative_to(self.run)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.run.rglob('*') if p.is_file()}

    def summary(self, score=2):
        ids = [d['id'] for d in self.rubric['dimensions']]
        return {'scores': dict.fromkeys(ids, score), 'unscored_reasons': dict.fromkeys(ids),
                'gates': {'G1': 'pass', 'G2': 'pass', 'G3': 'pass'},
                'task_outcome': 'complete', 'main_issue': SECRET,
                'evidence': [{'dimension_ids': ids, 'message_id': 'm0002', 'quote': SECRET, 'note': SECRET}]}

    def judgment(self, pid):
        segment = {'A': self.summary(2), 'B': self.summary(3), 'preferred': 'B', 'reason': SECRET}
        value = {'rubric_id': self.rubric['rubric_id'], 'pair_id': pid,
                 'common_prefix': segment, 'continuation': None, 'limitations': [SECRET]}
        if pid == 'j01':
            value['continuation'] = {'A': self.summary(1), 'B': self.summary(2),
                                     'preferred': 'B', 'reason': SECRET}
        return value

    def request(self, call, deadline=None):
        session = next((s for s in self.plan['sessions'] if s['id'] == call.get('session')), None)
        request = {'model': session['model'] if session else self.plan['judge_model'],
                   'effort': session['effort'] if session else self.plan['judge_effort'], 'prompt': SECRET}
        if deadline is not None:
            request['timeout_seconds'] = deadline
        frozen = {'request': request, 'request_sha256': _digest(request), 'call': call}
        self.write('records/' + call['id'] + '/request.json', frozen)
        return frozen

    def add_call(self, call, finish=True, unknown=False, failed=False, tool_output=SECRET,
                 deadline=None, invocation=False, invocation_deadline=None):
        frozen = self.request(call, deadline)
        if invocation:
            self.write('records/' + call['id'] + '/native-invocation.json', {
                'version': 1, 'request_sha256': frozen['request_sha256'],
                'timeout_seconds': deadline if invocation_deadline is None else invocation_deadline,
                'command': [SECRET], 'workspace_before': {'private_field': SECRET}})
        answer = json.dumps(self.judgment(call['pair'])) if call['role'] == 'judge' else SECRET
        item = {'id': 'item-0', 'type': 'command_execution', 'command': SECRET,
                'aggregated_output': tool_output, 'exit_code': 0}
        record = {'id': call['id'], 'status': 'stopped' if failed else 'complete',
                  'exit_code': 1 if failed else 0, 'errors': [{'type': 'failure', 'message': SECRET}] if failed else [],
                  'timeout': failed, 'malformed_event_lines': 0,
                  'terminal_usage_events': 0 if unknown else 1,
                  'direct_terminal_usage': None if unknown else {'input_tokens': 100, 'cached_input_tokens': 60, 'output_tokens': 10},
                  'tool_events': [{'type': 'item.started', 'item': deepcopy(item)},
                                  {'type': 'item.completed', 'item': deepcopy(item)}],
                  'answer': answer, 'request_sha256': frozen['request_sha256'],
                  'launch_result': {'attempts': 1, 'seconds': 1.25, 'stdout': SECRET}}
        try:
            self.control.run(call['id'], call.get('session', call['id']), call['role'], 'native', lambda: record)
        except CallControlPaused:
            if not (unknown or failed):
                raise
        if finish and not (failed or unknown):
            self.write('records/' + call['id'] + '/finished.json',
                       {'record_sha256': _digest(record), 'request_sha256': frozen['request_sha256']})
            if call['role'] == 'judge':
                self.write('records/' + call['id'] + '/judgment.json', json.loads(answer))
        return record

    def complete(self):
        for call in self.plan['calls']:
            self.add_call(call)

    def test_incomplete_snapshot_known_cost_is_not_a_projection_or_quality_score(self):
        self.add_call(self.plan['calls'][0])
        before = self.files()
        value = report.aggregate(self.run)
        self.assertEqual(self.files(), before)
        self.assertFalse(value['complete'])
        self.assertEqual(value['observed_cost']['usage']['processed_tokens'], 110)
        self.assertIsNone(value['full_run_processed_tokens'])
        self.assertEqual(value['observed_cost']['usage']['noncached_input_tokens'], 40)
        self.assertEqual(value['quality']['graded_pairs'], 0)
        self.assertEqual(value['quality']['descriptive_main_effects'], [])
        for row in value['quality']['segments'].values():
            self.assertIsNone(row['quality_index_mean'])
            self.assertIsNone(row['first_useful_turn'])
        self.assertEqual(value, report.aggregate(self.run))

    def test_unknown_failed_usage_keeps_known_subtotal_and_no_zero_imputation(self):
        self.add_call(self.plan['calls'][0])
        self.add_call(self.plan['calls'][1], unknown=True, failed=True)
        value = report.aggregate(self.run)
        usage = value['observed_cost']['usage']
        self.assertIsNone(usage['processed_tokens'])
        self.assertEqual(usage['known_processed_tokens'], 110)
        self.assertEqual(usage['unknown_input_tokens_invocations'], 1)
        self.assertEqual(usage['unknown_output_tokens_invocations'], 1)
        self.assertEqual(value['observed_cost']['statuses']['failed'], 1)
        text = report.markdown(value)
        self.assertIn('**unknown**', text)
        self.assertIn('known input/output subtotal: 110', text)

    def test_pending_call_has_unknown_usage_and_unknown_tool_trace(self):
        self.add_call(self.plan['calls'][0])
        call = self.plan['calls'][1]
        self.request(call)
        self.control.dispatch(call['id'], call['session'], 'answer', 'native')
        value = report.aggregate(self.run)
        self.assertEqual(value['observed_cost']['statuses']['pending'], 1)
        self.assertIsNone(value['observed_cost']['usage']['processed_tokens'])
        self.assertIsNone(value['observed_cost']['command_completed_events'])
        self.assertEqual(value['observed_cost']['known_command_completed_events'], 1)

    def test_nested_original_receipt_checksum_is_checked_independently(self):
        self.add_call(self.plan['calls'][0])
        path = self.run / 'controller/checkpoint.json'
        envelope = json.loads(path.read_text())
        first = self.plan['calls'][0]['id']
        envelope['state']['calls'][first]['record']['answer'] = 'Changed after the original receipt.'
        envelope['state_sha256'] = _digest(envelope['state'])
        path.write_text(json.dumps(envelope))
        with self.assertRaises(report.ReportError):
            report.aggregate(self.run)

    def test_moving_controller_snapshot_is_rejected_without_writing_run(self):
        self.add_call(self.plan['calls'][0])
        from unittest import mock
        original = report._read
        reads = 0
        def read(root, relative, *args, **kwargs):
            nonlocal reads
            data = original(root, relative, *args, **kwargs)
            if str(relative) == 'controller/checkpoint.json':
                reads += 1
                if reads == 2:
                    return data + b' '
            return data
        before = self.files()
        with mock.patch.object(report, '_read', side_effect=read):
            with self.assertRaises(report.ReportError):
                report.aggregate(self.run)
        self.assertEqual(self.files(), before)

    def test_known_failed_usage_counts_as_spent_and_unsettled_success_is_not_complete(self):
        self.add_call(self.plan['calls'][0], finish=False)
        self.add_call(self.plan['calls'][1], failed=True)
        value = report.aggregate(self.run)
        self.assertEqual(value['observed_cost']['usage']['processed_tokens'], 220)
        self.assertEqual(value['pending_local_settlements'], 1)
        self.assertFalse(value['complete'])

    def test_full_run_separates_prefix_extra_turns_nine_turn_totals_and_judge_cost(self):
        self.complete()
        value = report.aggregate(self.run)
        self.assertTrue(value['complete'])
        self.assertEqual(value['full_run_processed_tokens'], 26 * 110)
        self.assertEqual(value['cost_by_role']['answer']['usage']['processed_tokens'], 24 * 110)
        self.assertEqual(value['cost_by_role']['judge']['usage']['processed_tokens'], 2 * 110)
        rows = {r['segment']: r for r in value['cost_by_condition'] if r['arm'] == 'existing-bulk'}
        self.assertEqual(rows['prefix_turns_1_3']['usage']['processed_tokens'], 330)
        self.assertEqual(rows['extension_turns_4_9']['usage']['processed_tokens'], 660)
        self.assertEqual(rows['long_session_turns_1_9']['usage']['processed_tokens'], 990)
        self.assertEqual(value['quality']['segments']['common_prefix']['graded_sessions'], 4)
        self.assertEqual(value['quality']['segments']['continuation']['graded_sessions'], 2)
        self.assertGreater(value['quality']['segments']['common_prefix']['quality_index_mean'],
                           value['quality']['segments']['continuation']['quality_index_mean'])

    def test_public_export_removes_every_private_text_surface(self):
        self.complete()
        value = report.aggregate(self.run)
        text = json.dumps(value) + report.markdown(value)
        self.assertNotIn(SECRET, text)
        self.assertNotIn('preferred_session', text)
        self.assertNotIn('unscored_reasons', text)
        self.assertNotIn('source_request_id', text)
        self.assertNotIn(str(self.run), text)
        self.assertTrue(value['quality']['condition_rows'])
        self.assertEqual(value['quality']['reducer'], 'conversation_grading.summarize')

    def test_started_and_completed_events_are_not_double_counted(self):
        self.add_call(self.plan['calls'][0])
        value = report.aggregate(self.run)['observed_cost']
        self.assertEqual(value['command_started_events'], 1)
        self.assertEqual(value['command_completed_events'], 1)
        self.assertEqual(value['completed_tool_event_records'], 1)
        self.assertEqual(value['tool_output_characters'], len(SECRET))
        self.assertEqual(value['launcher_attempts'], 1)
        self.assertIsNone(value['physical_provider_requests'])

    def test_missing_command_output_is_unknown_not_zero_characters(self):
        self.add_call(self.plan['calls'][0], tool_output=None)
        value = report.aggregate(self.run)['observed_cost']
        self.assertEqual(value['command_completed_events'], 1)
        self.assertIsNone(value['tool_output_characters'])

    def test_tampered_source_receipt_finish_or_judgment_is_rejected(self):
        self.complete()
        paths = ['plan.json', 'scenario.json', 'rubric.json', 'controller/checkpoint.json',
                 'records/s1-t01/finished.json', 'records/j01/judgment.json', 'records/s1-t01/request.json']
        for path in paths:
            with self.subTest(path=path):
                target = self.run / path
                original = target.read_bytes()
                data = json.loads(original)
                if path.endswith('finished.json'):
                    data['record_sha256'] = '0' * 64
                elif path.endswith('judgment.json'):
                    data['common_prefix']['preferred'] = 'A'
                elif path.endswith('request.json'):
                    data['request']['prompt'] = 'tampered'
                else:
                    data['untrusted_change'] = True
                    if path.endswith('checkpoint.json'):
                        data['state']['revision'] += 1
                target.write_text(json.dumps(data))
                with self.assertRaises(report.ReportError):
                    report.aggregate(self.run)
                target.write_bytes(original)

    def test_judgment_without_completed_answer_prefix_is_rejected(self):
        self.add_call(self.plan['calls'][-2])
        with self.assertRaises(report.ReportError):
            report.aggregate(self.run)

    def test_publish_is_explicit_reproducible_and_never_overwrites_run_or_unrelated_files(self):
        self.add_call(self.plan['calls'][0])
        before = self.files()
        destination = self.directory / 'public-report'
        report.publish(self.run, destination)
        self.assertEqual(before, self.files())
        first = {p.name: p.read_bytes() for p in destination.iterdir()}
        with self.assertRaises(report.ReportError):
            report.publish(self.run, destination)
        (destination / 'keep.txt').write_text('keep')
        report.publish(self.run, destination, overwrite=True)
        self.assertEqual(first['report.json'], (destination / 'report.json').read_bytes())
        self.assertEqual(first['report.md'], (destination / 'report.md').read_bytes())
        self.assertEqual((destination / 'keep.txt').read_text(), 'keep')
        with self.assertRaises(report.ReportError):
            report.publish(self.run, self.run / 'report', overwrite=True)

    def test_parent_traversal_symlinks_and_hardlink_outputs_rejected(self):
        bad = self.directory / 'unused' / '..' / self.run.name / 'reports'
        with self.assertRaises(report.ReportError):
            report.publish(self.run, bad)
        link = self.directory / 'alias'
        link.symlink_to(self.run, target_is_directory=True)
        with self.assertRaises(report.ReportError):
            report.aggregate(link)
        output = self.directory / 'reports'; output.mkdir()
        (output / 'report.json').symlink_to(self.run / 'plan.json')
        with self.assertRaises(report.ReportError):
            report.publish(self.run, output, overwrite=True)
        (output / 'report.json').unlink()
        import os
        os.link(self.run / 'plan.json', output / 'report.json')
        with self.assertRaises(report.ReportError):
            report.publish(self.run, output, overwrite=True)

    def test_old_missing_deadlines_stay_unknown_without_assuming240(self):
        self.add_call(self.plan['calls'][0])
        before = self.files()
        value = report.aggregate(self.run)
        self.assertEqual(2, value['schema_version'])
        self.assertEqual(before, self.files())
        slot = value['original_slots'][0]
        self.assertEqual('s1-t01', slot['slot_id'])
        self.assertEqual('s1-t01', slot['attempt_id'])
        self.assertIsNone(slot['deadline_seconds'])
        self.assertEqual('unknown', slot['deadline_source'])
        self.assertIsNone(slot['invocation_receipt_sha256'])
        self.assertEqual(1, len(value['cost_by_execution_deadline']))
        self.assertIsNone(value['cost_by_execution_deadline'][0]['deadline_seconds'])
        self.assertEqual(110, value['cost_by_execution_deadline'][0]['usage']['processed_tokens'])
        session = value['session_execution_policies'][0]['segments']['prefix_turns_1_3']
        self.assertEqual([None, None, None], session['deadline_vector_seconds'])
        self.assertEqual('incomplete', session['classification'])

    def test_hashed_deadline_evidence_and_unstarted_slots_do_not_expose_private_data(self):
        call = self.plan['calls'][0]
        self.add_call(call, deadline=240, invocation=True)
        # A prepared request without a ledger dispatch is not an observed attempt.
        self.request(self.plan['calls'][1], deadline=1200)
        value = report.aggregate(self.run)
        slot, unstarted = value['original_slots'][:2]
        self.assertEqual(240, slot['deadline_seconds'])
        self.assertEqual('hashed_request_and_invocation', slot['deadline_source'])
        self.assertEqual(self.sha('records/s1-t01/native-invocation.json'), slot['invocation_receipt_sha256'])
        self.assertEqual(self.control.record(call['id'])['request_sha256'], slot['request_sha256'])
        self.assertEqual(1.25, slot['wall_seconds'])
        self.assertFalse(slot['timed_out'])
        self.assertTrue(slot['final_answer_present'])
        self.assertEqual('not_dispatched', unstarted['status'])
        self.assertIsNone(unstarted['attempt_id'])
        self.assertIsNone(unstarted['deadline_seconds'])
        self.assertIsNone(unstarted['request_sha256'])
        text = json.dumps(value) + report.markdown(value)
        self.assertNotIn(SECRET, text)
        self.assertNotIn(str(self.run), text)
        self.assertNotIn('private_field', text)
        self.assertNotIn('recorded_at', text)

    def test_request_only_and_invocation_only_deadlines_have_explicit_provenance(self):
        self.add_call(self.plan['calls'][0], deadline=240)
        self.add_call(self.plan['calls'][1], invocation=True, invocation_deadline=1200)
        slots = report.aggregate(self.run)['original_slots']
        self.assertEqual((240, 'hashed_request'), (slots[0]['deadline_seconds'], slots[0]['deadline_source']))
        self.assertEqual((1200, 'invocation_receipt'), (slots[1]['deadline_seconds'], slots[1]['deadline_source']))

    def test_mixed_session_and_pair_vectors_preserve_prefix_extension_and_judge_deadlines(self):
        for call in self.plan['calls']:
            deadline = 1200
            if call['role'] == 'answer' and (call['session'] in ('s2', 's3') or (call['session'] == 's1' and call['turn'] <= 3)):
                deadline = 240
            self.add_call(call, deadline=deadline, invocation=True)
        before = self.files()
        value = report.aggregate(self.run)
        self.assertEqual(before, self.files())
        sessions = {row['session_id']: row['segments'] for row in value['session_execution_policies']}
        s1 = sessions['s1']
        self.assertEqual([240] * 3, s1['prefix_turns_1_3']['deadline_vector_seconds'])
        self.assertEqual([1200] * 6, s1['extension_turns_4_9']['deadline_vector_seconds'])
        self.assertEqual([240] * 3 + [1200] * 6, s1['configured_session']['deadline_vector_seconds'])
        self.assertEqual('same_uniform', s1['prefix_turns_1_3']['classification'])
        self.assertEqual('mixed', s1['configured_session']['classification'])
        self.assertIsNone(sessions['s2']['extension_turns_4_9'])
        pairs = {row['pair_id']: row for row in value['pair_execution_policies']}
        prefix = pairs['j01']['segments']['prefix_turns_1_3']
        self.assertEqual('mixed', prefix['classification'])
        self.assertEqual([240] * 3, prefix['candidates']['A']['deadline_vector_seconds'])
        self.assertEqual([1200] * 3, prefix['candidates']['B']['deadline_vector_seconds'])
        self.assertEqual('same_uniform', pairs['j01']['segments']['extension_turns_4_9']['classification'])
        self.assertEqual('same_uniform', pairs['j02']['segments']['prefix_turns_1_3']['classification'])
        self.assertIsNone(pairs['j02']['segments']['extension_turns_4_9'])
        self.assertEqual(1200, pairs['j01']['judge_deadline_seconds'])
        costs = {row['deadline_seconds']: row for row in value['cost_by_execution_deadline']}
        self.assertEqual(9 * 110, costs[240]['usage']['processed_tokens'])
        self.assertEqual(17 * 110, costs[1200]['usage']['processed_tokens'])
        self.assertEqual(26 * 110, value['observed_cost']['usage']['processed_tokens'])
        self.assertEqual(4, value['quality']['segments']['common_prefix']['graded_sessions'])
        self.assertEqual('s1', value['quality']['condition_rows'][0]['session_id'])
        self.assertIn('mixed', report.markdown(value))
        self.assertIn('[240, 240, 240]', report.markdown(value))

    def test_unknown_failed_usage_and_incomplete_mixed_deadlines_remain_distinct(self):
        first = next(c for c in self.plan['calls'] if c['id'] == 's1-t01')
        second = next(c for c in self.plan['calls'] if c['id'] == 's1-t02')
        self.add_call(first, deadline=240, invocation=True)
        self.add_call(second, deadline=1200, invocation=True, unknown=True, failed=True)
        value = report.aggregate(self.run)
        session = value['session_execution_policies'][0]['segments']['prefix_turns_1_3']
        self.assertEqual('incomplete', session['classification'])
        self.assertTrue(session['has_mixed_observed_deadlines'])
        self.assertEqual([240, 1200, None], session['deadline_vector_seconds'])
        self.assertEqual(['complete', 'failed', 'not_dispatched'], session['status_vector'])
        costs = {row['deadline_seconds']: row for row in value['cost_by_execution_deadline']}
        self.assertIsNone(costs[1200]['usage']['processed_tokens'])
        self.assertEqual(1, costs[1200]['usage']['unknown_input_tokens_invocations'])
        self.assertEqual(110, costs[240]['usage']['processed_tokens'])
        self.assertEqual(0, costs[None]['dispatched_cli_invocations'])
        self.assertIsNone(value['observed_cost']['usage']['processed_tokens'])
        failed = next(row for row in value['original_slots'] if row['slot_id'] == second['id'])
        self.assertTrue(failed['timed_out'])
        self.assertEqual(1200, failed['deadline_seconds'])

    def test_pending_invocation_deadline_is_declared_without_inventing_elapsed_or_success(self):
        call = self.plan['calls'][0]
        self.request(call, deadline=1200)
        self.control.dispatch(call['id'], call['session'], 'answer', 'native')
        slot = report.aggregate(self.run)['original_slots'][0]
        self.assertEqual('pending', slot['status'])
        self.assertEqual(1200, slot['deadline_seconds'])
        self.assertEqual('hashed_request', slot['deadline_source'])
        self.assertIsNone(slot['wall_seconds'])
        self.assertIsNone(slot['timed_out'])
        self.assertIsNone(slot['final_answer_present'])

    def test_invocation_deadline_hash_version_and_invalid_values_fail_closed(self):
        self.add_call(self.plan['calls'][0], deadline=240, invocation=True)
        path = self.run / 'records/s1-t01/native-invocation.json'
        original = path.read_bytes()
        changes = [{'timeout_seconds': 1200}, {'timeout_seconds': True}, {'timeout_seconds': 0},
                   {'timeout_seconds': -1}, {'timeout_seconds': 2.5}, {'timeout_seconds': None},
                   {'request_sha256': '0' * 64}, {'version': True}]
        for change in changes:
            with self.subTest(change=change):
                path.write_text(json.dumps(json.loads(original) | change))
                before = self.files()
                with self.assertRaises(report.ReportError):
                    report.aggregate(self.run)
                self.assertEqual(before, self.files())
        for malformed in (None, [], 'not-an-object', 42):
            with self.subTest(malformed=malformed):
                path.write_text(json.dumps(malformed))
                with self.assertRaises(report.ReportError):
                    report.aggregate(self.run)
        path.write_bytes(original)

    def test_different_length_configured_sessions_are_not_a_uniform_pair_comparison(self):
        observations = []
        sessions = {'short': {'turns': 3}, 'long': {'turns': 9}}
        for sid, session in sessions.items():
            for turn in range(1, session['turns'] + 1):
                observations.append({'slot_id': sid + '-t' + str(turn), 'session_id': sid, 'pair_id': None,
                                     'turn': turn, 'deadline_seconds': 240, 'status': 'complete'})
        observations.append({'slot_id': 'judge', 'session_id': None, 'pair_id': 'pair',
                             'deadline_seconds': 240, 'status': 'complete'})
        _, pairs = report._execution_policies(observations, sessions, {'pair': {'mask': {'A': 'short', 'B': 'long'}}})
        self.assertEqual('same_uniform', pairs[0]['segments']['prefix_turns_1_3']['classification'])
        self.assertEqual('incomplete', pairs[0]['segments']['configured_session']['classification'])
        self.assertFalse(pairs[0]['segments']['configured_session']['candidate_turn_counts_match'])
        self.assertIsNone(pairs[0]['segments']['extension_turns_4_9']['candidates']['A'])

    def test_changed_request_deadline_cannot_be_rebound_away_from_original_receipt(self):
        self.add_call(self.plan['calls'][0], deadline=240)
        path = self.run / 'records/s1-t01/request.json'
        frozen = json.loads(path.read_text())
        frozen['request']['timeout_seconds'] = 1200
        frozen['request_sha256'] = _digest(frozen['request'])
        path.write_text(json.dumps(frozen))
        with self.assertRaises(report.ReportError):
            report.aggregate(self.run)

    def test_changing_or_new_invocation_receipt_during_read_is_rejected(self):
        self.add_call(self.plan['calls'][0], deadline=240)
        from unittest import mock
        original = report._read
        invocation_reads = 0
        def read(root, relative, *args, **kwargs):
            nonlocal invocation_reads
            data = original(root, relative, *args, **kwargs)
            if str(relative) == 'records/s1-t01/native-invocation.json':
                invocation_reads += 1
                if invocation_reads == 2:
                    return b'{}'
            return data
        before = self.files()
        with mock.patch.object(report, '_read', side_effect=read):
            with self.assertRaises(report.ReportError):
                report.aggregate(self.run)
        self.assertEqual(before, self.files())


if __name__ == '__main__':
    unittest.main()
