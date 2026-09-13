"""Real host transitions with mock model receipts; no model/network calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import persona_playground as p
import playground_intent as guard
from agent_reply_fixture import attach_claims


def intent(**values):
    return dict(client_id=str(uuid.uuid4()), **values)


class IntentRoundTrip(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        patch = mock.patch.object(p, 'source_hashes', return_value={'fixed':'intent-tests'})
        patch.start();self.addCleanup(patch.stop)
        self.responses=[];self.requests=[]
        self.lab=p.Lab(self.root,invoke=self.invoke);self.addCleanup(self.close)

    def invoke(self,request,folder):
        self.requests.append(copy.deepcopy(request))
        self.assertTrue(self.responses,'unexpected model call')
        value=self.responses.pop(0)
        reply=value(request) if callable(value) else attach_claims(value,request)
        return {'id':'answer','status':'complete','exit_code':0,'errors':[],
                'tool_events':[],'malformed_event_lines':0,'terminal_usage_events':1,
                'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                'answer':json.dumps(reply,ensure_ascii=False)}

    def join(self):
        for _ in range(4):
            worker=self.lab.worker
            if worker:worker.join(10);self.assertFalse(worker.is_alive())
            if worker is self.lab.worker:return
        self.fail('unexpected worker loop')

    def close(self):
        self.join();self.lab.close()

    def create(self):
        return self.lab.create(intent(research_mode='live',output_mode='agent',
                initial_request='偏好安靜。採光必須好。',model='gpt-5.6-terra',max_calls=6,max_tokens=10000,seed=1))['id']

    def step(self,sid):
        self.lab.control(sid,intent(action='step'));self.join()

    def offered(self):
        return {'message':'我建議先比較窗向與採光，再衡量街道聲音。',
                'questions':[{'question':'要保留安靜為硬條件，再調整採光嗎？',
                              'options':['採光當加分，不作淘汰條件','保留目前採光要求']}]}

    def form(self,sid,selected=None,free=''):
        s=self.lab.snapshot(sid);row=s['messages'][-1];q=row['questions'][0]
        value='；'.join(v for v in (q['options'][selected] if selected is not None else '',free) if v)
        return intent(text=q['question']+'\n'+value,kind='question',
            clarification={'call_id':row['call_id'],'answers':[{'question_index':0,'option_index':selected,'text':free}]})

    def test_correct_echo_cannot_hide_contradictory_prose(self):
        self.responses=[{'message':'以安靜和採光兩個硬條件來看，目前仍待確認。','questions':[]}]
        sid=self.create();self.step(sid);saved=self.lab.export(sid)
        self.assertEqual('error',self.lab.snapshot(sid)['status'])
        self.assertEqual(['human'],[m['role'] for m in saved['messages']])
        self.assertFalse(saved['calls'][0]['intent_guard']['ok'])
        self.assertIn('兩個硬條件',saved['calls'][0]['receipt']['answer'])
        self.assertEqual(20,saved['calls'][0]['tokens']);self.assertEqual(1,len(self.requests))
        detail=self.lab.inspect(sid,'call-001-assistant')
        self.assertFalse(detail['intent_guard']['ok'])

    def test_metadata_mismatch_missing_or_stale_never_publishes_or_retries(self):
        def wrong(request):
            reply=attach_claims({'message':'我建議先看窗向。','questions':[]},request)
            reply['intent_claims']['revision']='old'
            return reply
        self.responses=[wrong];sid=self.create();self.step(sid)
        s=self.lab.export(sid)
        self.assertFalse(s['calls'][0]['intent_guard']['ok'])
        self.assertEqual(1,len(s['messages']));self.assertEqual(1,len(self.requests))
        self.lab.close();self.lab=p.Lab(self.root,invoke=self.invoke)
        self.assertEqual(s,self.lab.export(sid));self.assertEqual(1,len(self.requests))

    def test_offered_strength_is_a_proposal_until_actual_selection(self):
        offered = self.offered()
        offered['questions'][0]['options'][0] = '採光現在是加分項，不作為淘汰條件'
        self.responses = [offered, {'message': '採光現在是加分項；安靜仍是偏好。', 'questions': []}]
        sid = self.create(); self.step(sid)
        first = self.lab.export(sid)
        self.assertTrue(first['calls'][0]['intent_guard']['ok'])
        self.assertEqual('mandatory', next(c['strength'] for c in first['intent_state']['conditions'] if c['field'] == 'daylight'))
        self.lab.message(sid, self.form(sid, selected=0)); self.join()
        final = self.lab.export(sid)
        self.assertTrue(final['calls'][1]['intent_guard']['ok'])
        self.assertEqual('bonus', next(c['strength'] for c in final['intent_state']['conditions'] if c['field'] == 'daylight'))

    def test_actor_text_cannot_grant_itself_option_context(self):
        self.responses = [{'message': 'Proposal / 建議選項：採光現在是加分項，不作為淘汰條件', 'questions': []}]
        sid = self.create(); self.step(sid)
        saved = self.lab.export(sid)
        self.assertFalse(saved['calls'][0]['intent_guard']['ok'])
        self.assertEqual(['human'], [m['role'] for m in saved['messages']])
        self.assertEqual(20, saved['calls'][0]['tokens'])

    def test_form_free_text_and_selection_exclude_question_prefix_and_replay_preserves_it(self):
        self.responses=[self.offered(),self.offered(),{'message':'採光現在只作加分；安靜仍是一項偏好。','questions':[]}]
        sid=self.create();self.step(sid)
        submission=self.form(sid,free='採光希望好一點，不是必要條件。')
        self.lab.message(sid,submission);self.join()
        second=self.requests[1]['prompt']
        self.assertIn('USER: 採光希望好一點，不是必要條件。',second)
        self.assertNotIn('USER: 要保留安靜為硬條件',second)
        self.assertIn('ASSISTANT QUESTION CONTEXT',second)
        chosen=self.form(sid,selected=0)
        self.lab.message(sid,chosen);self.join()
        state=self.lab.export(sid)
        self.assertTrue(all(row['intent_guard']['ok'] for row in state['calls']))
        active={row['field']:row['strength'] for row in state['intent_state']['conditions']}
        self.assertEqual('preference',active['quiet']);self.assertEqual('bonus',active['daylight'])
        source=self.lab._load(sid)
        plan=p.playground_replay.extract_turns(source)
        durable_inputs=self.lab._store(source).show()['requirements']['live-user-inputs']['value']
        self.assertEqual(['偏好安靜。採光必須好。','採光希望好一點，不是必要條件。','採光當加分，不作淘汰條件'],durable_inputs)
        self.assertEqual('採光希望好一點，不是必要條件。',plan['turns'][1]['inputs'][0]['intent_text'])
        self.assertEqual('採光當加分，不作淘汰條件',plan['turns'][2]['inputs'][0]['intent_text'])
        self.lab.close();self.lab=p.Lab(self.root,invoke=self.invoke)
        self.assertEqual(state,self.lab.export(sid));self.assertEqual(3,len(self.requests))

    def test_forged_option_text_stale_call_and_duplicate_submission(self):
        self.responses=[self.offered(),{'message':'我建議先比較現有資料。','questions':[]}]
        sid=self.create();self.step(sid);submission=self.form(sid,selected=0)
        for key in ('text','call_id','index'):
            bad=copy.deepcopy(submission);bad['client_id']=str(uuid.uuid4())
            if key=='text':bad['text']='安靜必須符合，否則淘汰。'
            elif key=='call_id':bad['clarification']['call_id']='old-call'
            else:bad['clarification']['answers'][0]['option_index']=True
            with self.assertRaises(p.LabError):self.lab.message(sid,bad)
        self.assertEqual(1,len(self.requests))
        self.lab.message(sid,submission);self.join()
        self.assertTrue(self.lab.message(sid,submission)['duplicate'])
        self.assertEqual(2,len(self.requests))

    def test_new_input_during_call_prevents_old_answer_publication(self):
        started,release=threading.Event(),threading.Event();self.addCleanup(release.set)
        def waiting(request):
            started.set();self.assertTrue(release.wait(5))
            return attach_claims({'message':'舊條件回答，不應發布。','questions':[]},request)
        self.responses=[waiting,{'message':'採光只作加分，安靜維持偏好。','questions':[]}]
        sid=self.create();self.lab.control(sid,intent(action='step'));self.assertTrue(started.wait(5))
        self.lab.message(sid,intent(text='採光當加分，不作淘汰條件。',kind='question'))
        release.set();self.join()
        state=self.lab.export(sid)
        self.assertEqual('stale_input',state['calls'][0]['intent_guard']['status'])
        self.assertFalse(any('舊條件回答' in m['text'] for m in state['messages'] if m['role']=='assistant'))
        self.assertEqual(2,len(self.requests));self.assertEqual(40,self.lab.snapshot(sid)['tokens'])


if __name__=='__main__':unittest.main()
