"""Offline extraction: exact interventions, uncertain pairing, and private paths."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import playground_cases as p


class PlaygroundCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.sid = 'a' * 32
        self.folder = self.root / self.sid
        self.folder.mkdir(mode=0o700)
        self.path = self.folder / 'session.json'
        self.state = {'schema_version': 1, 'id': self.sid, 'revision': 8, 'model': 'gpt-6-astra',
                      'messages': [{'role': 'persona', 'text': 'Compare these supplied options.'}],
                      'actions': [], 'queue': [], 'calls': [], 'client_ids': {},
                      'sources': {'tools/persona_playground.py': 'b' * 64},
                      'card': {'id': 'P4', 'success': ['Private benchmark gold.']},
                      'fixtures': {'listing.txt': 'Saved supplied text.'}, 'system': 'Frozen system.',
                      'runtime_settings': {'ask_if_missing': 'none'}, 'pending_call': None}

    def intent(self, text='  Why this choice?\nPlease explain.  ', kind='question', client_id=None):
        return {'client_id': client_id or str(uuid.uuid4()), 'text': text, 'kind': kind}

    def add(self, data, answer=None, queued=False):
        self.state['actions'].append({'kind': 'human_input_queued', 'data': copy.deepcopy(data), 'time': 1})
        self.state['client_ids'][str(uuid.UUID(data['client_id']))] = p.digest(data)
        if queued:
            self.state['queue'].append(copy.deepcopy(data))
        else:
            self.state['messages'].append({'role': 'human', 'kind': data['kind'], 'text': data['text']})
            if answer is not None:
                self.state['messages'].append({'role': 'assistant', 'text': answer, 'responding_to': 'human'})
                self.state['calls'].append({'id': 'call-%03d-assistant' % (len(self.state['calls']) + 1),
                    'actor': 'assistant', 'tokens': 19, 'status': 'complete',
                    'receipt': {'answer': answer, 'processed_tokens': 19, 'record_sha256': 'c' * 64}})

    def save(self):
        self.path.write_bytes(p.canonical({'value': self.state, 'sha256': p.digest(self.state)}))
        self.path.chmod(0o600)

    def extract(self, name=None):
        self.save()
        before = self.path.read_bytes()
        result = p.extract(self.root, self.sid, name)
        self.assertEqual(before, self.path.read_bytes())
        saved = json.loads(Path(result['path']).read_text())
        self.assertEqual(saved['sha256'], p.digest(saved['value']))
        self.assertEqual(0o600, Path(result['path']).stat().st_mode & 0o777)
        self.assertEqual(1, Path(result['path']).stat().st_nlink)
        return result, saved['value']

    def test_answered_and_queued_keep_exact_intent_and_audited_context(self):
        first = self.intent()
        second = self.intent('Budget increases only if dry.', kind='amendment')
        self.add(first, answer='Check the supplied evidence first.')
        self.add(second, queued=True)
        result, value = self.extract()
        self.assertEqual({'answered': 1, 'queued': 1, 'unknown': 0}, result['counts'])
        answered, queued = value['candidates']
        self.assertEqual(first, answered['intervention'])
        self.assertEqual('exact_fifo_legacy', answered['association'])
        self.assertEqual(1, answered['preceding_transcript']['end_exclusive'])
        self.assertEqual('Check the supplied evidence first.', answered['assistant_reply']['text'])
        self.assertEqual(19, value['calls'][answered['usage_ref']['index']]['tokens'])
        self.assertEqual(second, queued['intervention'])
        self.assertIsNone(queued['preceding_transcript'])
        self.assertIn('may include later', queued['context_at_snapshot']['note'])
        self.assertEqual(self.state['sources'], value['source']['source_versions'])
        self.assertEqual(8, value['source']['revision'])
        self.assertNotIn('Private benchmark gold.', json.dumps(value))
        self.assertFalse(answered['evaluation']['ground_truth'])
        self.assertIsNone(answered['evaluation']['expected_answer'])

    def test_repeated_intent_dedupes_but_identical_text_new_intent_survives(self):
        first = self.intent('Same question?')
        self.add(first, answer='First response.')
        self.state['actions'].append(copy.deepcopy(self.state['actions'][0]))
        self.add(self.intent('Same question?'), answer='Second response.')
        _, value = self.extract()
        self.assertEqual(2, len(value['candidates']))
        self.assertEqual(3, len(value['candidates'][0]['source_refs']))
        self.assertNotEqual(value['candidates'][0]['id'], value['candidates'][1]['id'])

    def test_conflicting_intent_or_dedupe_manifest_fails_without_output(self):
        first = self.intent()
        self.add(first, queued=True)
        self.state['queue'][0]['text'] = 'Changed request under the same ID.'
        self.save()
        with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        self.assertEqual(['session.json'], [path.name for path in self.folder.iterdir()])

    def test_missing_reply_and_mismatched_human_prefix_remain_unknown(self):
        self.add(self.intent())
        _, value = self.extract('pending.private.json')
        self.assertEqual('unknown', value['candidates'][0]['status'])
        self.assertIsNotNone(value['candidates'][0]['preceding_transcript'])
        self.state['messages'][1]['text'] = 'Other text, not this intent.'
        _, value = self.extract('mismatch.private.json')
        self.assertEqual('unknown', value['candidates'][0]['status'])
        self.assertIsNone(value['candidates'][0]['assistant_reply'])
        self.assertIsNone(value['candidates'][0]['preceding_transcript'])

    def test_identical_saved_answers_do_not_guess_usage_receipt(self):
        self.add(self.intent('First question?'), answer='Same answer.')
        self.add(self.intent('Second question?'), answer='Same answer.')
        _, value = self.extract()
        self.assertEqual(2, value['counts']['answered'])
        self.assertTrue(all(row['usage_ref'] is None for row in value['candidates']))

    def test_explicit_future_ids_must_agree_and_can_bind_repeated_answer_usage(self):
        first, second = self.intent(), self.intent('Second question?')
        self.add(first, answer='Same answer.')
        self.add(second, answer='Same answer.')
        self.state['messages'][1]['client_id'] = first['client_id']
        self.state['messages'][2].update(responding_to_client_id=first['client_id'], call_id='call-001-assistant')
        _, value = self.extract('explicit.private.json')
        self.assertEqual('explicit_client_id', value['candidates'][0]['association'])
        self.assertEqual(0, value['candidates'][0]['usage_ref']['index'])
        self.state['messages'][2]['responding_to_client_id'] = second['client_id']
        _, value = self.extract('conflict.private.json')
        self.assertEqual('unknown', value['candidates'][0]['status'])

    def test_digest_corruption_duplicate_json_and_nonfinite_values_are_rejected(self):
        self.save()
        saved = json.loads(self.path.read_text())
        saved['value']['model'] = 'tampered'
        for raw in (json.dumps(saved), '{"value":{},"value":{},"sha256":"x"}', '{"value":NaN,"sha256":"x"}'):
            self.path.write_text(raw)
            with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)

    def test_traversal_session_ids_and_output_paths_are_rejected(self):
        self.save()
        for sid in ('../escape', self.sid.upper(), '/tmp/session'):
            with self.assertRaises(p.CaseError): p.extract(self.root, sid)
        for name in ('../escape.private.json', '/tmp/escape.private.json', 'public.json', 'session.json'):
            with self.assertRaises(p.CaseError): p.extract(self.root, self.sid, name)
        with self.assertRaises(p.CaseError): p.extract(self.root / self.sid / '..', self.sid)

    def test_session_file_folder_and_parent_symlinks_are_rejected(self):
        self.save()
        original = self.path.read_bytes()
        self.path.unlink()
        target = self.root / 'other.json'; target.write_bytes(original)
        self.path.symlink_to(target)
        with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        self.path.unlink(); self.path.write_bytes(original)
        alias = self.root / ('b' * 32); alias.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(p.CaseError): p.extract(self.root, alias.name)
        parent_alias = self.root / 'alias'; parent_alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(p.CaseError): p.extract(parent_alias, self.sid)

    def test_hardlinked_source_and_existing_output_never_overwritten(self):
        self.save()
        linked = self.folder / 'linked.json'; os.link(self.path, linked)
        with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        linked.unlink()
        result, _ = self.extract()
        output = Path(result['path']); before = output.read_bytes()
        with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        self.assertEqual(before, output.read_bytes())
        alias = self.folder / 'alias.private.json'; alias.symlink_to(output)
        with self.assertRaises(p.CaseError): p.extract(self.root, self.sid, alias.name)
        self.assertEqual(before, output.read_bytes())

    def test_fifo_source_is_rejected_without_waiting_for_a_writer(self):
        os.mkfifo(self.path, 0o600)
        result = subprocess.run([sys.executable, str(ROOT / 'tools/playground_cases.py'),
                                 '--state-dir', str(self.root), '--session', self.sid],
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(2, result.returncode)
        self.assertIn('bounded regular', result.stderr)

    def test_failed_atomic_publish_and_size_limit_leave_source_untouched(self):
        self.add(self.intent(), queued=True); self.save(); before = self.path.read_bytes()
        with mock.patch.object(p.os, 'link', side_effect=OSError('disk failed')):
            with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        with mock.patch.object(p, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaises(p.CaseError): p.extract(self.root, self.sid)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(['session.json'], [path.name for path in self.folder.iterdir()])

    def test_cli_prints_only_private_path_metadata_without_model_or_network_calls(self):
        self.add(self.intent('PRIVATE TEXT MUST STAY IN ARTIFACT'), queued=True); self.save()
        out = io.StringIO()
        with mock.patch('subprocess.Popen', side_effect=AssertionError('no model process')), mock.patch('socket.socket', side_effect=AssertionError('no network')), mock.patch('sys.stdout', out):
            self.assertEqual(0, p.main(['--state-dir', str(self.root), '--session', self.sid]))
        self.assertTrue(json.loads(out.getvalue())['private'])
        self.assertNotIn('PRIVATE TEXT MUST STAY IN ARTIFACT', out.getvalue())

    def test_actual_lab_envelope_extracts_a_synthetic_answer_without_replay(self):
        import persona_playground as lab_module
        calls = []
        def invoke(request, folder):
            calls.append(request)
            return {'id': 'answer', 'status': 'complete', 'exit_code': 0, 'errors': [],
                    'tool_events': [], 'malformed_event_lines': 0, 'terminal_usage_events': 1,
                    'direct_terminal_usage': {'input_tokens': 14, 'output_tokens': 5, 'cached_input_tokens': 0},
                    'answer': 'The saved synthetic response to the tester.'}
        lab_root = self.root / 'lab'
        lab = lab_module.Lab(lab_root, invoke=invoke)
        try:
            with mock.patch('socket.socket', side_effect=AssertionError('no network')):
                sid = lab.create({'persona_id': 'P4', 'model': 'gpt-6-astra', 'max_calls': 3,
                                  'max_tokens': 10000, 'seed': 1, 'client_id': str(uuid.uuid4())})['id']
                data = self.intent('Which evidence is still missing?')
                lab.message(sid, data)
                lab.worker.join(10)
                self.assertFalse(lab.worker.is_alive())
                original = (lab_root / sid / 'session.json').read_bytes()
                result = p.extract(lab_root, sid)
                value = json.loads(Path(result['path']).read_text())['value']
            self.assertEqual(1, len(calls))
            self.assertEqual({'answered': 1, 'queued': 0, 'unknown': 0}, value['counts'])
            self.assertEqual(data, value['candidates'][0]['intervention'])
            self.assertEqual(19, value['calls'][0]['receipt']['processed_tokens'])
            self.assertEqual(original, (lab_root / sid / 'session.json').read_bytes())
        finally:
            if lab.worker:
                lab.worker.join(10)
            lab.close()


if __name__ == '__main__':
    unittest.main()
