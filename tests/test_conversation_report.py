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

    def request(self, call):
        session = next((s for s in self.plan['sessions'] if s['id'] == call.get('session')), None)
        request = {'model': session['model'] if session else self.plan['judge_model'],
                   'effort': session['effort'] if session else self.plan['judge_effort'], 'prompt': SECRET}
        frozen = {'request': request, 'request_sha256': _digest(request), 'call': call}
        self.write('records/' + call['id'] + '/request.json', frozen)
        return frozen

    def add_call(self, call, finish=True, unknown=False, failed=False, tool_output=SECRET):
        frozen = self.request(call)
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


if __name__ == '__main__':
    unittest.main()
