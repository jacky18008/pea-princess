"""Offline host transaction boundaries; the eligibility engine is tested separately."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import persona_playground as p


def intent(**data):
    return dict(client_id=str(uuid.uuid4()), **data)


def terminal():
    return {'id': 'answer', 'status': 'complete', 'exit_code': 0, 'errors': [],
            'tool_events': [], 'malformed_event_lines': 0, 'terminal_usage_events': 1,
            'direct_terminal_usage': {'input_tokens': 15, 'output_tokens': 5, 'cached_input_tokens': 0},
            'answer': json.dumps({'candidates': [], 'focus_fields': []})}


def accept_stub(proposal, user_inputs, revision, sources):
    return {'proposal': copy.deepcopy(proposal), 'inputs': list(user_inputs),
            'revision': revision, 'sources': copy.deepcopy(sources),
            'reply': {'message': 'Checked host reply for revision %s.' % revision, 'questions': []}}


class LiveGateTransactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        # Isolate host transactions from concurrent engine development and from
        # semantic extraction, which has its own independent acceptance tests.
        for patch in (
            mock.patch.object(p, 'source_hashes', return_value={'test-host': 'frozen'}),
            mock.patch.object(p.live_eligibility, 'normalize', side_effect=lambda inputs, rev: {}, create=True),
            mock.patch.object(p.live_eligibility, 'accept', side_effect=accept_stub, create=True),
            mock.patch.object(p.live_eligibility, 'validate_artifact',
                side_effect=lambda artifact, inputs, rev, sources: {'valid': artifact == accept_stub(artifact['proposal'], inputs, rev, sources)},
                create=True),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.requests = []
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            return terminal()
        self.lab = p.Lab(self.root, invoke=invoke)
        self.addCleanup(self.close)

    def join(self):
        for _ in range(4):
            worker = self.lab.worker
            if worker:
                worker.join(10)
                self.assertFalse(worker.is_alive(), 'offline worker did not finish')
            if worker is self.lab.worker:
                return
        self.fail('unexpected repeated worker replacement')

    def close(self):
        self.join()
        self.lab.close()

    def create(self):
        return self.lab.create(intent(research_mode='live', initial_request='Rent ceiling GBP 2000 per month.',
            model='gpt-6-astra', max_calls=5, max_tokens=10000, seed=1))['id']

    def step(self, sid):
        self.lab.control(sid, intent(action='step'))
        self.join()

    def test_inflight_question_changes_invalidate_immediately_and_continue_once(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            if len(self.requests) == 1:
                started.set()
                if not release.wait(5):
                    raise AssertionError('test release missing')
            return terminal()
        self.lab.invoke = invoke
        sid = self.create()
        self.lab.control(sid, intent(action='step'))
        self.assertTrue(started.wait(5))
        change = intent(text='Change rent ceiling to GBP 1800 per month.', kind='question')
        self.lab.message(sid, change)
        self.lab.message(sid, change)
        queued = self.lab._load(sid)
        self.assertEqual(2, queued['intent_epoch'])
        self.assertEqual(1, len(queued['queue']))
        request = self.lab._store(queued).show()['requests']['human-' + uuid.UUID(change['client_id']).hex]
        self.assertEqual('pending', request['status'])
        release.set()
        self.join()
        saved = self.lab._load(sid)
        self.assertEqual(2, len(self.requests), self.lab.snapshot(sid)['notice'])
        self.assertEqual(['human', 'human', 'assistant'], [m['role'] for m in saved['messages']])
        self.assertEqual('stale', saved['calls'][0]['acceptance_status'])
        self.assertEqual('accepted', saved['calls'][1]['acceptance_status'])
        self.assertEqual('discarded', self.lab._store(saved).show()['dispatches'][saved['calls'][0]['id']]['status'])
        self.assertEqual(40, self.lab.snapshot(sid)['tokens'])
        self.assertEqual('current', self.lab.snapshot(sid)['comparison_status'])

    def test_interrupted_batch_replays_without_duplicate_inputs_or_events(self):
        sid = self.create()
        changes = [intent(text='Set rent ceiling to GBP 1800 per month.', kind='amendment'),
                   intent(text='Require at least two bedrooms.', kind='question')]
        with mock.patch.object(self.lab, '_start'):
            for change in changes:
                self.lab.message(sid, change)
        original_event = p.event
        def crash_after_first_resolution(store, op, **fields):
            result = original_event(store, op, **fields)
            if op == 'request.resolve':
                raise RuntimeError('simulated crash after durable request resolution')
            return result
        with mock.patch.object(p, 'event', side_effect=crash_after_first_resolution):
            with self.assertRaises(RuntimeError):
                self.lab._prepare(self.lab._load(sid))
        saved = self.lab._load(sid)
        self.assertTrue(saved['preparing_input'])
        self.assertEqual(2, len(saved['queue']))
        self.assertEqual(1, len(saved['history']))
        self.lab.control(sid, intent(action='recover'))
        self.step(sid)
        saved = self.lab._load(sid)
        expected = ['Rent ceiling GBP 2000 per month.'] + [row['text'] for row in changes]
        self.assertEqual(expected, self.lab._live_inputs(saved))
        self.assertEqual(expected, self.lab._store(saved).show()['requirements']['live-user-inputs']['value'])
        self.assertTrue(all(r['status'] == 'resolved' for r in self.lab._store(saved).show()['requests'].values()))
        self.assertEqual(1, len(self.requests))
        self.assertEqual('current', self.lab.snapshot(sid)['comparison_status'])

    def test_amendment_batch_preserves_cap_accounting_and_amended_flag(self):
        sid = self.create()
        change = intent(text='Set rent ceiling to GBP 1700 per month.', kind='amendment')
        self.lab.message(sid, change)
        self.join()
        self.assertEqual([change['text']], self.lab._load(sid)['amendments'])
        self.assertTrue(self.lab.snapshot(sid)['amended'])

    def test_acceptance_saved_before_session_crash_recovers_same_answer_without_new_call(self):
        sid = self.create()
        save = self.lab._save
        crashed = []
        def crash_once(s):
            if s.get('current_acceptance') and not crashed:
                crashed.append(True)
                raise RuntimeError('simulated session commit crash after acceptance artifact')
            return save(s)
        with mock.patch.object(self.lab, '_save', side_effect=crash_once):
            self.step(sid)
        self.assertEqual([True], crashed)
        saved = self.lab._load(sid)
        self.assertEqual(1, len(self.requests))
        self.assertEqual(1, len([m for m in saved['messages'] if m['role'] == 'assistant']))
        self.assertEqual(1, len(list((self.root / sid / 'acceptance').rglob('artifact.json'))))
        self.assertEqual(20, self.lab.snapshot(sid)['tokens'])
        self.assertEqual('current', self.lab.snapshot(sid)['comparison_status'])

    def test_partial_source_capture_recovery_does_not_claim_answer_restored(self):
        sid = self.create()
        def partial_capture(s, call_id, receipt):
            self.lab._snapshot_index(s, call_id).parent.mkdir(parents=True)
            raise OSError('simulated crash while retaining source group')
        with mock.patch.object(self.lab, '_capture_sources', side_effect=partial_capture):
            self.step(sid)
        saved = self.lab._load(sid)
        self.assertEqual(1, len(self.requests))
        self.assertEqual('rejected', saved['calls'][0]['acceptance_status'])
        self.assertEqual('error', saved['status'])
        self.assertFalse(any(m['role'] == 'assistant' for m in saved['messages']))
        self.assertNotIn('已從原有紀錄恢復這則回答', saved['notice'])
        self.assertIsNone(self.lab.export(sid)['current_comparison'])

    def test_stale_unknown_usage_keeps_recoverable_call_and_never_dispatches_followup(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            started.set()
            if not release.wait(5):
                raise AssertionError('test release missing')
            result = terminal()
            result.update(direct_terminal_usage=None, terminal_usage_events=0)
            return result
        self.lab.invoke = invoke
        sid = self.create()
        self.lab.control(sid, intent(action='step'))
        self.assertTrue(started.wait(5))
        self.lab.message(sid, intent(text='Change rent ceiling to GBP 1800 per month.', kind='amendment'))
        release.set()
        self.join()
        saved = self.lab._load(sid)
        self.assertEqual(1, len(self.requests))
        self.assertEqual('interrupted', saved['status'])
        self.assertIsNotNone(saved['pending_call'])
        self.assertEqual(1, len(saved['queue']))
        self.assertTrue(self.lab._store(saved).show()['budgets']['tokens']['unknown_spend'])
        self.assertFalse(any(m['role'] == 'assistant' for m in saved['messages']))

    def test_incompatible_code_has_no_current_comparison_in_snapshot_or_export(self):
        sid = self.create()
        self.step(sid)
        with mock.patch.object(p, 'source_hashes', return_value={'test-host': 'changed'}):
            snapshot, exported = self.lab.snapshot(sid), self.lab.export(sid)
        self.assertIsNone(snapshot['current_comparison'])
        self.assertIsNone(exported['current_comparison'])
        self.assertNotEqual('current', snapshot['comparison_status'])
        self.assertNotEqual('current', exported['comparison_status'])
        self.assertTrue(all(m.get('comparison_status') != 'current' for m in snapshot['messages']))

    def test_real_engine_accepts_host_source_receipt_shape(self):
        # A separately loaded engine avoids the host-only engine doubles above.
        # The public-page operation is replaced by a supplied synthetic snapshot.
        spec = importlib.util.spec_from_file_location('transaction_real_engine',
            ROOT / 'skills/vet-flat/scripts/live_eligibility.py')
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        url = 'https://www.foxtons.co.uk/unit/synthetic-transaction-test'
        text = '2 bedroom flat\nMonthly rent: £1800 pcm\nFloor: 3\nArea: 70 m2'
        def capture(source_url, folder):
            self.assertEqual(url, source_url)
            folder.mkdir(parents=True)
            (folder / 'text.txt').write_text(text, encoding='utf-8')
            return {'source_url': url, 'ok': True, 'http_status': 200, 'note': 'Synthetic offline source.',
                    'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'retrieved_at': '2026-09-11T12:00:00Z', 'source_claims_verified': False}
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            result = terminal()
            result['answer'] = json.dumps({'candidates': [{'source_url': url, 'label': 'Synthetic flat'}],
                                          'focus_fields': []})
            return result
        self.lab.invoke = invoke
        import public_source_snapshot
        with mock.patch.object(p, 'live_eligibility', engine), \
                mock.patch.object(public_source_snapshot, 'capture', side_effect=capture):
            sid = self.create()
            self.step(sid)
            snapshot = self.lab.snapshot(sid)
            self.assertEqual('current', snapshot['comparison_status'], snapshot['notice'])
            saved = self.lab._load(sid)
            self.assertEqual('accepted', saved['calls'][0]['acceptance_status'])
            self.assertIn('1,800', snapshot['messages'][-1]['text'])

    def test_real_clarification_roundtrip_retains_raw_but_normalizes_answer_only(self):
        spec = importlib.util.spec_from_file_location('transaction_clarification_engine',
            ROOT / 'skills/vet-flat/scripts/live_eligibility.py')
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        url = 'https://www.foxtons.co.uk/unit/synthetic-clarification-test'
        text = '2 bedroom flat\nMonthly rent: £1800 pcm\nFloor: 3\nArea: 70 m2'
        def capture(source_url, folder):
            self.assertEqual(url, source_url)
            folder.mkdir(parents=True)
            (folder / 'text.txt').write_text(text, encoding='utf-8')
            return {'source_url': url, 'ok': True, 'http_status': 200, 'note': 'Synthetic offline source.',
                    'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'retrieved_at': '2026-09-11T12:00:00Z', 'source_claims_verified': False}
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            result = terminal()
            result['answer'] = json.dumps({'candidates': [{'source_url': url, 'label': 'Synthetic flat'}],
                                          'focus_fields': []})
            return result
        self.lab.invoke = invoke
        import public_source_snapshot
        with mock.patch.object(p, 'live_eligibility', engine), \
                mock.patch.object(public_source_snapshot, 'capture', side_effect=capture):
            sid = self.lab.create(intent(research_mode='live', initial_request='預算上限 £2000',
                model='gpt-6-astra', max_calls=5, max_tokens=10000, seed=1))['id']
            self.step(sid)
            first = self.lab.snapshot(sid)
            self.assertEqual('current', first['comparison_status'], first['notice'])
            question = first['messages'][-1]['questions'][0]['question']
            answer = '我會補充確切條件；房租上限 £1900'
            raw = question + '\n' + answer  # Exact clarificationForm submission shape.
            change = intent(text=raw, kind='question')
            self.lab.message(sid, change)
            self.join()
            saved = self.lab._load(sid)
            request_id = 'human-' + uuid.UUID(change['client_id']).hex
            state = self.lab._store(saved).show()
            self.assertEqual(raw, state['requests'][request_id]['text'])
            self.assertEqual(raw, [m for m in saved['messages'] if m['role'] == 'human'][-1]['text'])
            self.assertEqual(['預算上限 £2000', answer], self.lab._live_inputs(saved))
            self.assertEqual(['預算上限 £2000', answer], state['requirements']['live-user-inputs']['value'])
            snapshot = self.lab.snapshot(sid)
            self.assertEqual('current', snapshot['comparison_status'], snapshot['notice'])
            artifact = snapshot['current_comparison']
            self.assertEqual([], artifact['normalization']['unresolved_intent'])
            self.assertFalse(artifact['reply']['questions'])
            rent = next(r for r in artifact['constraints']['requirements'] if r['id'] == 'rent-ceiling')
            self.assertEqual(1900, rent['value'])
            self.assertEqual(2, len(self.requests))


if __name__ == '__main__':
    unittest.main()
