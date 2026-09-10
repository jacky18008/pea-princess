"""Offline synthetic evidence packages; never inspect live runs or call models."""
import base64
import json
from pathlib import Path
import stat
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_supplement as supplement
import test_conversation_report as fixtures


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ConversationReportTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.run, self.directory, self.plan = self.fixture.run, self.fixture.directory, self.fixture.plan
        self.output = self.directory / 'supplement'
        self.fixture.complete()
        for pair in self.plan['pairs']:
            data = supplement.encoded({'pair_id': pair['id'], 'private': 'frozen original formal packet'})
            path = self.run / ('judges/' + pair['id'] + '/work/packet.json')
            path.parent.mkdir(parents=True); path.write_bytes(data)
            self.patch_record(pair['id'], lambda record, data=data: record.update(
                workspace_before={'files': {'packet.json': {'sha256': supplement.sha(data), 'bytes': len(data)}}}))
        scenario = {'initial_files': {'README.md': 'installed'}, 'turns': [{'files': {'later.txt': 'installed'}}]}
        self.fixture.write('scenario.json', scenario)
        frozen = json.loads((self.run / 'frozen.json').read_text())
        frozen['scenario_sha256'] = self.fixture.sha('scenario.json')
        self.fixture.write('frozen.json', frozen)
        # Every unconfigured stdout is explicitly captured empty, not an invalid
        # synthetic placeholder from the aggregate fixture.
        for call in self.plan['calls']:
            if call['role'] == 'answer':
                self.patch_record(call['id'], lambda record: record['launch_result'].update(stdout=''))

    def checkpoint(self):
        return json.loads((self.run / 'controller/checkpoint.json').read_text())

    def save_checkpoint(self, envelope):
        envelope['state_sha256'] = supplement.report._digest(envelope['state'])
        self.fixture.write('controller/checkpoint.json', envelope)

    def patch_record(self, cid, change):
        envelope = self.checkpoint(); row = envelope['state']['calls'][cid]
        change(row['record']); row['record_sha256'] = supplement.report._digest(row['record'])
        self.fixture.write('records/' + cid + '/native-record.json', row['record'])
        finished = self.run / ('records/' + cid + '/finished.json')
        if finished.exists():
            value = json.loads(finished.read_text()); value['record_sha256'] = row['record_sha256']
            self.fixture.write('records/' + cid + '/finished.json', value)
        self.save_checkpoint(envelope)
        return row['record']

    def stream(self, cid, events, tail=b'', truncated=False):
        raw = b''.join(supplement.encoded(event).replace(b'\n', b' ') + b'\n' for event in events) + tail
        (self.run / ('records/' + cid + '/native-stdout.jsonl')).write_bytes(raw)
        def change(record):
            record['launch_result']['stdout'] = raw.decode('utf-8', errors='replace')
            record['stream_truncated'] = {'stdout': truncated}
        self.patch_record(cid, change)
        return raw

    def snapshot(self, cid, bodies, inventory=True):
        rows = {name: {'sha256': supplement.sha(raw), 'bytes': len(raw),
                       'base64': base64.b64encode(raw).decode()} for name, raw in bodies.items()}
        self.fixture.write('records/' + cid + '/artifacts.json', rows)
        if inventory:
            self.patch_record(cid, lambda record: record.update(workspace_after={'files': {
                name: {'sha256': row['sha256'], 'bytes': row['bytes']} for name, row in rows.items()}}))
        return rows

    @staticmethod
    def event(text, phase=None, item_id='provider-item', **extra):
        item = {'type': 'agent_message', 'text': text}
        if item_id is not None:
            item['id'] = item_id
        if phase:
            item['phase'] = phase
        return {'type': 'item.completed', 'item': item, **extra}

    def build(self, pairs=None):
        return supplement.build(self.run, self.output, pairs)

    def packet(self, pair='j01'):
        return json.loads((self.output / ('evaluator/' + pair + '/packet.json')).read_text())

    def test_all_pairs_all_turn_snapshots_masked_and_exact_originals_retained_without_source_writes(self):
        body = ('model-a effort=low existing-bulk s1-t01 ' + str(self.run) + ' low rent high noise').encode()
        for call in self.plan['calls']:
            if call['role'] == 'answer':
                self.stream(call['id'], [self.event(body.decode(), 'commentary')])
                self.snapshot(call['id'], {'model-a-existing-bulk-s1.html': body, 'skill/new-result.md': b'real new output'})
        before = self.fixture.files(); result = self.build()
        self.assertEqual(result['released_pairs'], ['j01', 'j02'])
        self.assertEqual(before, self.fixture.files())
        evaluator = '\n'.join(p.read_text() for p in (self.output / 'evaluator').rglob('*') if p.is_file())
        for private in ('model-a', 'existing-bulk', 's1-t01', str(self.run), 'effort=low'):
            self.assertNotIn(private, evaluator)
        self.assertIn('low rent high noise', evaluator)
        self.assertIn('HIDDEN_EFFORT', evaluator)
        manifest = json.loads((self.output / 'operator/source-manifest.json').read_text())
        for source, entry in manifest['inputs'].items():
            if entry['copy']:
                self.assertEqual((self.output / 'operator' / entry['copy']).read_bytes(), (self.run / source).read_bytes())
        provenance_ids = []
        for pid in result['released_pairs']:
            for candidate in self.packet(pid)['candidates'].values():
                self.assertEqual(len(candidate['turns']), candidate['planned_turns'])
                for turn in candidate['turns']:
                    provenance_ids.extend(e['provenance_id'] for e in turn['agent_messages'])
                    entries = turn['artifact_snapshot']['entries']
                    self.assertEqual(len(entries), 2)
                    for entry in entries:
                        self.assertTrue(entry['file'].endswith('.txt'))
                        self.assertEqual(entry['receipt_snapshot_binding'], 'verified_workspace_after')
                        provenance_ids.append(entry['provenance_id'])
        self.assertEqual(len(set(provenance_ids)), len(provenance_ids))
        verified = json.loads((self.output / 'VERIFIED.json').read_text())
        self.assertIn('README.txt', verified['evaluator_file_sha256'])
        for rel, expected in verified['evaluator_file_sha256'].items():
            self.assertEqual(supplement.sha((self.output / 'evaluator' / rel).read_bytes()), expected)
        for path in [self.output, *self.output.rglob('*')]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700 if path.is_dir() else 0o600)

    def test_stream_phases_repeated_events_final_duplicate_and_unknown_visibility(self):
        final = fixtures.SECRET
        events = [self.event('working', 'commentary', timestamp=123), self.event('working more', 'commentary'),
                  self.event(final), self.event('unclassified', item_id=None), self.event('another', item_id=None)]
        events[0]['type'] = 'item.started'; events[1]['type'] = 'item.updated'
        self.stream('s1-t01', events)
        self.build(['j01']); turn = self.packet()['candidates']['A']['turns'][0]
        actual = turn['agent_messages']
        self.assertEqual(len(actual), 5)
        self.assertEqual(actual[0]['item_id'], actual[1]['item_id'])
        self.assertIsNone(actual[3]['item_id']); self.assertIsNone(actual[4]['item_id'])
        self.assertEqual(actual[0]['kind'], 'intermediate_agent_message')
        self.assertEqual(actual[2]['kind'], 'final_answer')
        self.assertEqual(turn['saved_final_answer']['matching_stream_lines'], [3])
        self.assertEqual(actual[0]['provider_reported_timestamps'][0]['value'], 123)
        for event in actual:
            for field in ('generated_at', 'stdout_received_at', 'ui_displayed_at', 'ui_visibility'):
                self.assertIsNone(event[field])

    def test_reasoning_excluded_at_event_and_item_levels_case_insensitively(self):
        events = [{'type': 'item.completed', 'item': {'type': 'reasoning', 'text': 'SECRET_REASONING_ITEM'}},
                  self.event('SECRET_EVENT_ANALYSIS', phase='commentary', channel='ANALYSIS'),
                  self.event('SECRET_ITEM_ANALYSIS', phase='Reasoning')]
        raw = self.stream('s1-t01', events)
        self.build(['j01'])
        text = (self.output / 'evaluator/j01/packet.json').read_text()
        for secret in ('SECRET_REASONING_ITEM', 'SECRET_EVENT_ANALYSIS', 'SECRET_ITEM_ANALYSIS'):
            self.assertNotIn(secret, text)
        events_out = self.packet()['candidates']['A']['turns'][0]['agent_messages']
        self.assertEqual(len(events_out), 2)
        self.assertTrue(all(e['text_status'] == 'withheld_reasoning' for e in events_out))
        manifest = json.loads((self.output / 'operator/source-manifest.json').read_text())
        rel = manifest['inputs']['records/s1-t01/native-stdout.jsonl']['copy']
        self.assertEqual((self.output / 'operator' / rel).read_bytes(), raw)

    def test_malformed_truncated_and_invalid_utf8_are_visible_gaps_not_exported_tail(self):
        self.stream('s1-t01', [self.event('progress')], b'\xffPRIVATE_MALFORMED_TAIL', True)
        self.build(['j01']); turn = self.packet()['candidates']['A']['turns'][0]
        self.assertEqual(turn['capture']['malformed_lines'], 1)
        self.assertEqual(turn['capture']['utf8_replacement_characters'], 1)
        self.assertTrue(turn['capture']['truncated'])
        self.assertEqual(turn['capture']['coverage'], 'known_incomplete')
        self.assertNotIn('PRIVATE_MALFORMED_TAIL', json.dumps(self.packet()))

    def test_missing_empty_fallback_and_unbound_stdout_have_distinct_coverage(self):
        self.patch_record('s1-t01', lambda r: r['launch_result'].pop('stdout'))
        self.stream('s1-t02', [])
        self.stream('s1-t03', [self.event('fallback')])
        (self.run / 'records/s1-t03/native-stdout.jsonl').unlink()
        self.stream('s1-t04', [self.event('unbound')])
        self.patch_record('s1-t04', lambda r: r['launch_result'].pop('stdout'))
        self.build(['j01']); turns = self.packet()['candidates']['A']['turns']
        self.assertIsNone(turns[0]['capture']['agent_message_events'])
        self.assertEqual(turns[1]['capture']['agent_message_events'], 0)
        self.assertEqual(turns[2]['capture']['receipt_stdout_binding'], 'receipt_stdout_only')
        self.assertEqual(turns[3]['capture']['receipt_stdout_binding'], 'unknown_no_saved_stdout')
        self.assertEqual(turns[3]['capture']['coverage'], 'withheld_missing_receipt_stdout_binding')
        self.assertEqual(turns[3]['agent_messages'], [])
        self.assertIsNone(turns[3]['capture']['agent_message_events'])
        self.assertNotIn('"text": "unbound"', json.dumps(self.packet()))
        manifest = json.loads((self.output / 'operator/source-manifest.json').read_text())
        saved = manifest['inputs']['records/s1-t04/native-stdout.jsonl']['copy']
        self.assertIn(b'unbound', (self.output / 'operator' / saved).read_bytes())

    def test_consistently_rehashed_artifact_tampering_is_rejected_by_paid_inventory(self):
        self.snapshot('s1-t01', {'result.md': b'actual captured result'})
        self.snapshot('s1-t01', {'result.md': b'replaced and self rehashed'}, inventory=False)
        with self.assertRaisesRegex(supplement.SupplementError, 'original receipt workspace'):
            self.build(['j01'])
        self.assertFalse(self.output.exists())

    def test_missing_inventory_explicitly_unknown_and_harness_binary_withheld(self):
        self.snapshot('s1-t01', {'result.md': b'observed only in snapshot', 'README.md': b'changed harness bytes',
                               'conversation.json': b'settlement bytes', 'binary.dat': b'\x00secret'}, inventory=False)
        self.build(['j01']); entries = self.packet()['candidates']['A']['turns'][0]['artifact_snapshot']['entries']
        self.assertEqual(sum(e['coverage'] == 'withheld_harness_path_as_in_formal_packet' for e in entries), 2)
        self.assertEqual(sum(e['coverage'] == 'withheld_binary_not_safely_blindable' for e in entries), 1)
        for entry in entries:
            if entry['coverage'] == 'withheld_missing_receipt_inventory_binding':
                self.assertEqual(entry['receipt_snapshot_binding'], 'unknown_receipt_inventory_unavailable')
        self.assertTrue(all(entry['file'] is None for entry in entries))
        self.assertNotIn('observed only in snapshot', json.dumps(self.packet()))

    def test_receipt_files_omitted_from_snapshot_are_an_explicit_coverage_limit(self):
        self.snapshot('s1-t01', {'result.md': b'captured result'})
        self.patch_record('s1-t01', lambda r: r['workspace_after']['files'].update(
            {'private-source-name.py': {'sha256': '0' * 64, 'bytes': 1}}))
        self.build(['j01']); snapshot = self.packet()['candidates']['A']['turns'][0]['artifact_snapshot']
        self.assertEqual(snapshot['receipt_files_absent_from_snapshot'], 1)
        self.assertEqual(snapshot['coverage_of_receipt_workspace'], 'not_asserted')
        self.assertNotIn('private-source-name.py', json.dumps(self.packet()))

    def test_failed_and_unsettled_turns_are_gaps_without_reconstructed_files(self):
        envelope = self.checkpoint(); envelope['state']['calls']['s1-t01']['failure_kind'] = 'timeout'
        self.save_checkpoint(envelope)
        (self.run / 'records/s1-t01/finished.json').unlink()
        (self.run / 'records/s1-t02/finished.json').unlink()
        live = self.run / 'sessions/s1/work/current.md'; live.parent.mkdir(parents=True); live.write_text('DO_NOT_RECONSTRUCT')
        self.build(['j01']); turns = self.packet()['candidates']['A']['turns']
        self.assertEqual(turns[0]['receipt_status'], 'failed')
        self.assertEqual(turns[1]['receipt_status'], 'complete_unsettled')
        self.assertEqual(turns[2]['unsettled_or_failed_prior_turns'], [1, 2])
        self.assertEqual(turns[0]['artifact_snapshot']['availability'], 'missing')
        self.assertNotIn('DO_NOT_RECONSTRUCT', json.dumps(self.packet()))

    def test_orphan_native_stream_or_artifacts_are_not_attributed_to_undispatched_turn(self):
        cid = 's1-t01'; envelope = self.checkpoint(); del envelope['state']['calls'][cid]; self.save_checkpoint(envelope)
        for name in ('native-record.json', 'finished.json'):
            (self.run / ('records/' + cid + '/' + name)).unlink()
        self.fixture.write('records/' + cid + '/artifacts.json', {})
        with self.assertRaisesRegex(supplement.SupplementError, 'orphan output'):
            self.build(['j01'])

    def test_formal_grade_release_requires_finished_paid_receipt_and_packet_binding(self):
        (self.run / 'records/j02/finished.json').unlink()
        result = self.build()
        self.assertEqual(result['released_pairs'], ['j01'])
        self.assertEqual(result['deferred_ungraded_pairs'], ['j02'])
        self.assertFalse((self.output / 'evaluator/j02').exists())

    def test_modified_formal_packet_and_judgment_each_fail_closed(self):
        path = self.run / 'judges/j01/work/packet.json'; original = path.read_bytes(); path.write_bytes(b'{}')
        with self.assertRaisesRegex(supplement.SupplementError, 'formal packet'):
            self.build(['j01'])
        path.write_bytes(original)
        self.fixture.write('records/j01/judgment.json', {'pair_id': 'j01'})
        with self.assertRaisesRegex(supplement.SupplementError, 'formal judgment'):
            self.build(['j01'])

    def test_receipt_and_stdout_corruption_fail_closed(self):
        self.stream('s1-t01', [self.event('saved')])
        (self.run / 'records/s1-t01/native-stdout.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(supplement.SupplementError, 'stdout file differs'):
            self.build(['j01'])

    def test_pending_anywhere_prevents_release_and_no_controller_writes(self):
        envelope = self.checkpoint(); envelope['state']['calls']['s2-t01']['record'] = None; self.save_checkpoint(envelope)
        before = self.fixture.files()
        with self.assertRaisesRegex(supplement.SupplementError, 'pending'):
            self.build(['j01'])
        self.assertEqual(before, self.fixture.files())

    def test_output_no_overwrite_no_inside_run_no_symlink_or_parent_traversal(self):
        self.output.mkdir()
        invalid = [self.output, self.run / 'new', self.directory / 'missing' / '..' / 'new']
        link = self.directory / 'link'; link.symlink_to(self.directory, target_is_directory=True)
        invalid.append(link / 'new')
        for path in invalid:
            with self.subTest(path=str(path)), self.assertRaises((supplement.SupplementError, supplement.report.ReportError)):
                supplement.build(self.run, path, ['j01'])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_moving_snapshot_does_not_publish_or_change_originals(self):
        original = supplement.report._read; counts = {}
        def moving(root, relative, *args, **kwargs):
            raw = original(root, relative, *args, **kwargs)
            counts[relative] = counts.get(relative, 0) + 1
            if relative == 'controller/checkpoint.json' and counts[relative] > 1:
                return raw + b' '
            return raw
        before = self.fixture.files()
        with mock.patch.object(supplement.report, '_read', side_effect=moving):
            with self.assertRaisesRegex(supplement.SupplementError, 'source changed'):
                self.build(['j01'])
        self.assertEqual(before, self.fixture.files()); self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
