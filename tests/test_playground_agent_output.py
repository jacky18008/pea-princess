"""Offline actual-agent output, human continuity and receipt preservation checks."""
import copy
import json
from agent_reply_fixture import attach_claims
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
import public_source_snapshot


def intent(**data):
    return dict(client_id=str(uuid.uuid4()), **data)


def terminal(reply, request=None):
    return {'id': 'answer', 'status': 'complete', 'exit_code': 0, 'errors': [],
            'tool_events': [], 'malformed_event_lines': 0, 'terminal_usage_events': 1,
            'direct_terminal_usage': {'input_tokens': 15, 'output_tokens': 5,
                                      'cached_input_tokens': 0},
            'answer': json.dumps(attach_claims(reply, request), ensure_ascii=False)}


class AgentOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        # Test this transport contract independently of concurrent doc edits.
        frozen = mock.patch.object(p, 'source_hashes', return_value={'test-package': 'frozen'})
        frozen.start()
        self.addCleanup(frozen.stop)
        self.requests = []
        self.replies = []
        self.lab = p.Lab(self.root, invoke=self.invoke)
        self.addCleanup(self.close)

    def invoke(self, request, folder):
        self.requests.append(copy.deepcopy(request))
        if not self.replies:
            raise AssertionError('Unexpected additional actor call')
        return terminal(self.replies.pop(0), request)

    def join(self):
        for _ in range(4):
            worker = self.lab.worker
            if worker:
                worker.join(10)
                self.assertFalse(worker.is_alive(), 'offline worker did not finish')
            if worker is self.lab.worker:
                return
        self.fail('Unexpected repeated worker replacement')

    def close(self):
        self.join()
        self.lab.close()

    def create(self, text='我想比較我手上的兩份房源資料。', **extra):
        data = intent(research_mode='live', output_mode='agent', initial_request=text,
                      model='gpt-6-astra', max_calls=6, max_tokens=10000, seed=1)
        data.update(extra)
        return self.lab.create(data)['id']

    def step(self, sid):
        self.lab.control(sid, intent(action='step'))
        self.join()

    def test_actual_prose_choices_and_raw_receipt_are_retained_without_host_replacement(self):
        reply = {'message': '先看你每天真正會用到的空間：這兩間的差別，比房數更值得比較。',
                 'questions': [{'question': '你較想先比較哪一項？',
                                'options': ['每月開支', '室內空間']}]}
        self.replies = [reply]
        with mock.patch.object(p.personas, 'fixture_text', side_effect=AssertionError('no fixture')), \
                mock.patch.object(p, 'FrozenController', side_effect=AssertionError('no simulator')), \
                mock.patch.object(p.Lab, '_capture_sources', side_effect=AssertionError('no capture')):
            sid = self.create()
            self.step(sid)
        view = self.lab.snapshot(sid)
        exported = self.lab.export(sid)
        saved = self.lab._load(sid)
        self.assertEqual(['human', 'assistant'], [m['role'] for m in view['messages']], view['notice'])
        self.assertEqual(reply['message'], view['messages'][-1]['display_text'])
        self.assertEqual(reply['questions'], view['messages'][-1]['questions'])
        self.assertEqual(p.conversation_reply.transcript(reply), view['messages'][-1]['text'])
        self.assertEqual(attach_claims(reply,self.requests[0]), json.loads(exported['calls'][0]['receipt']['answer']))
        self.assertEqual(view['messages'], exported['messages'])
        self.assertIn('intent_claims', self.requests[0]['response_schema']['required'])
        self.assertTrue(exported['calls'][0]['intent_guard']['ok'])
        self.assertEqual('live_research', self.requests[0]['tool_policy'])
        self.assertNotIn('live_gate_version', saved)
        self.assertEqual({}, saved['fixtures'])
        self.assertEqual([], saved['persona_history'])
        self.assertIsNone(view['current_comparison'])
        self.assertNotEqual('current', view['comparison_status'])
        self.assertEqual({'assistant': 1, 'persona': 0}, view['actor_calls'])
        self.assertEqual(20, view['tokens'])
        self.assertIsNone(view['next_actor'])

    def test_budget_change_heating_question_and_next_reply_share_exact_history(self):
        opening = ('房租上限 £2300。比較以下我貼的資料，不用找新房源。\n'
                   'A：£2250／月，一房，44.96 平方公尺。\n'
                   'B：£1800／月，一房，31.77 平方公尺。')
        change = '房租上限改成 £2100。臥室正對大馬路就排除。暖氣費包含在房租裡嗎？先不找新房源。'
        followup = '先只保留 B；幫我列出應該問的那一句話。'
        first = {'message': '依你貼的房租，B 每月少 £450；A 的廣告面積則較大。', 'questions': []}
        second = {'message': '你貼的資料沒有交代暖氣費；B 的房租在新上限內，A 則超出 £150。',
                  'questions': []}
        third = {'message': '可以問：「£1800 的月租是否已包含暖氣費，臥室窗戶是否直接朝向大馬路？」',
                 'questions': []}
        self.replies = [first, second, third]
        with mock.patch.object(p.Lab, '_capture_sources', side_effect=AssertionError('no capture')):
            sid = self.create(opening)
            self.step(sid)
            self.lab.message(sid, intent(text=change, kind='question'))
            self.join()
            self.lab.message(sid, intent(text=followup, kind='question'))
            self.join()
        saved = self.lab._load(sid)
        view = self.lab.snapshot(sid)
        self.assertEqual(3, len(self.requests), view['notice'])
        self.assertIn(opening, self.requests[1]['prompt'])
        self.assertIn(first['message'], self.requests[1]['prompt'])
        self.assertIn(change, self.requests[1]['prompt'])
        self.assertIn(second['message'], self.requests[2]['prompt'])
        self.assertIn(change, self.requests[2]['prompt'])
        self.assertIn(followup, self.requests[2]['prompt'])
        self.assertEqual([opening, change, followup],
                         self.lab._store(saved).show()['requirements']['live-user-inputs']['value'])
        self.assertEqual([opening, change, followup],
                         [text for role, text in saved['history'] if role == 'user'])
        self.assertEqual([first['message'], second['message'], third['message']],
                         [m['display_text'] for m in view['messages'] if m['role'] == 'assistant'])
        self.assertEqual([change, followup],
                         [row['text'] for row in self.lab.export(sid)['interventions'] if row['role'] == 'human'])
        self.assertTrue(all(r['status'] == 'resolved' for r in self.lab._store(saved).show()['requests'].values()))

    def test_supplied_url_is_not_automatically_fetched_even_when_actor_repeats_it(self):
        url = 'https://example.com/listing-a'
        self.replies = [{'message': '先用你貼的資料比較；[房源連結](' + url + ') 本身沒有提供暖氣費資訊。',
                         'questions': []}]
        with mock.patch.object(p.Lab, '_capture_sources', side_effect=AssertionError('no host fetch')) as host, \
                mock.patch.object(public_source_snapshot, 'capture', side_effect=AssertionError('no fetch')) as fetch:
            sid = self.create('房源網址：' + url + '\n我貼的廣告文字：一房，月租 £1800。')
            self.step(sid)
            view = self.lab.snapshot(sid)
            exported = self.lab.export(sid)
        host.assert_not_called()
        fetch.assert_not_called()
        self.assertIn(url, view['messages'][-1]['display_text'])
        self.assertEqual(1, view['calls'], view['notice'])
        self.assertEqual([], exported['calls'][0].get('source_snapshots', []))
        self.assertIsNone(exported['current_comparison'])

    def test_restart_resume_and_repeated_message_reuse_record_without_extra_call(self):
        first = {'message': '房租差額已記下，下一步可以看暖氣費。', 'questions': []}
        second = {'message': '廣告沒寫暖氣費，暫時不能把它算成已含。', 'questions': []}
        self.replies = [first, second]
        sid = self.create('比較貼上的一房資料。')
        self.step(sid)
        before = self.lab.export(sid)
        self.lab.close()
        self.lab = p.Lab(self.root, invoke=self.invoke)
        self.assertEqual(before, self.lab.export(sid))
        self.assertEqual(1, len(self.requests))
        message = intent(text='暖氣費呢？', kind='question')
        self.lab.message(sid, message)
        self.join()
        after = self.lab.export(sid)
        response = self.lab.message(sid, message)
        self.join()
        self.assertTrue(response.get('duplicate'))
        self.assertEqual(after, self.lab.export(sid))
        self.assertEqual(2, len(self.requests))
        self.assertIn(first['message'], self.requests[1]['prompt'])
        self.assertEqual(second['message'], self.lab.snapshot(sid)['messages'][-1]['display_text'])
        self.assertEqual(40, self.lab.snapshot(sid)['tokens'])

    def test_inflight_interjection_is_preserved_and_duplicate_is_answered_once(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        first = {'message': '先比較你貼上的兩份資料。', 'questions': []}
        second = {'message': '已改按 £2100 比較，暖氣費仍需向出租方確認。', 'questions': []}
        self.replies = [first, second]
        def invoke(request, folder):
            if not self.requests:
                started.set()
                if not release.wait(5):
                    raise AssertionError('test release missing')
            return self.invoke(request, folder)
        self.lab.invoke = invoke
        sid = self.create('房租上限 £2300；比較貼上的房源。')
        self.lab.control(sid, intent(action='step'))
        self.assertTrue(started.wait(5))
        message = intent(text='改成 £2100。順便確認暖氣費。', kind='question')
        self.lab.message(sid, message)
        self.lab.message(sid, message)
        self.assertEqual(1, self.lab.snapshot(sid)['pending_count'])
        release.set()
        self.join()
        view = self.lab.snapshot(sid)
        self.assertEqual(2, len(self.requests), view['notice'])
        self.assertEqual(1, sum(m['text'] == message['text'] for m in view['messages']))
        self.assertIn(message['text'], self.requests[1]['prompt'])
        self.assertEqual(second['message'], view['messages'][-1]['display_text'])
        self.assertEqual(0, view['actor_calls']['persona'])
        self.assertEqual(0, view['pending_count'])
        self.assertEqual(40, view['tokens'])


if __name__ == '__main__':
    unittest.main()
