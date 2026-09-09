"""Offline continuous-persona, interruption, persistence and loopback HTTP tests."""
import copy
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import persona_playground as p

def terminal(answer='Recorded synthetic answer with useful concrete next steps.', tokens=20):
    return {'id':'answer','status':'complete','exit_code':0,'errors':[],'tool_events':[],
            'malformed_event_lines':0,'terminal_usage_events':1,
            'direct_terminal_usage':None if tokens is None else {'input_tokens':tokens-5,'output_tokens':5,'cached_input_tokens':0},
            'answer':answer}

def intent(**data):return dict(client_id=str(uuid.uuid4()),**data)

class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name).resolve();self.prompts=[];self.answers=[]
        def invoke(request,folder):
            self.prompts.append(request['prompt'])
            return terminal(self.answers.pop(0) if self.answers else 'Useful practical answer with independent verification, exact evidence and next steps.')
        self.lab=p.Lab(self.path,invoke=invoke);self.addCleanup(self.close)
    def close(self):
        if self.lab.worker:self.lab.worker.join(10)
        self.lab.close()
    def create(self,pid='P4',**extra):
        data=intent(persona_id=pid,model='gpt-6-astra',max_calls=10,max_tokens=10000,seed=1);data.update(extra)
        return self.lab.create(data)['id']
    def control(self,sid,action):return self.lab.control(sid,intent(action=action))
    def join(self):
        for _ in range(3):
            worker=self.lab.worker
            if worker:worker.join(10);self.assertFalse(worker.is_alive())
            if worker is self.lab.worker:break
    def send(self,sid,text='An extra question',kind='question',**extra):
        data=intent(text=text,kind=kind);data.update(extra);return self.lab.message(sid,data)

    def test_all_sixteen_cards_are_available_without_model_calls(self):
        self.assertEqual(16,len(self.lab.catalog()['personas']))
        for pid in self.lab.cards:
            sid=self.create(pid);s=self.lab.snapshot(sid)
            self.assertEqual(self.lab.cards[pid]['opening_message'],s['messages'][0]['text'])
            self.assertEqual(0,s['calls'])
        self.assertFalse(self.prompts)

    def test_whole_dynamic_session_and_no_hidden_judge(self):
        self.answers=['Do not sign or pay tomorrow. Request written terms first.','What should I ask for?','Ask for the agreement and verify the payment terms independently.','I have enough to act. [END]']
        sid=self.create();self.control(sid,'run');self.join();s=self.lab.snapshot(sid)
        self.assertEqual(['persona','assistant','persona','assistant','persona'],[m['role'] for m in s['messages']])
        self.assertEqual(4,len(self.prompts));self.assertEqual('persona_ended',s['stop_reason'])
        self.assertEqual('not_evaluated',s['quality']);self.assertEqual(80,s['tokens'])
        self.assertIn('Do not sign or pay tomorrow',self.prompts[1])
        self.assertIn('What should I ask for?',self.prompts[2])
        self.assertNotIn('THE CRITERIA',self.prompts[1]);self.assertNotIn('success',self.prompts[0])

    def test_runtime_settings_are_projected_only_to_answerer_without_gold(self):
        sid=self.create();self.answers=['Practical answer.','Thank you. [END]']
        self.control(sid,'run');self.join()
        expected={'budget_mode':'lite','fixed_form':'gate','ask_if_missing':'none'}
        self.assertEqual(expected,self.lab.snapshot(sid)['runtime_settings'])
        self.assertEqual(expected,self.lab.export(sid)['runtime_settings'])
        self.assertIn(json.dumps(expected),self.prompts[0])
        self.assertNotIn('ACTIVE RUNTIME SETTINGS',self.prompts[1])
        for criterion in self.lab.cards['P4']['success']:
            self.assertNotIn(criterion,self.prompts[0]);self.assertNotIn(criterion,self.prompts[1])

    def test_no_early_held_document_is_automatically_given_to_assistant(self):
        sid=self.create('C1');self.control(sid,'step');self.join()
        s=self.lab._load(sid)
        for body in s['fixtures'].values():self.assertNotIn(body,self.prompts[0])

    def test_persona_knows_released_document_bytes_but_not_future_sources(self):
        sid=self.create('C1');self.control(sid,'step');self.join()
        self.answers=['Thank you. [END]'];self.control(sid,'step');self.join()
        s=self.lab._load(sid);released={d['file'] for d in s['controller']['released']}
        self.assertTrue(released);self.assertTrue(set(s['fixtures'])-released)
        for file,body in s['fixtures'].items():
            if file in released:self.assertIn(json.dumps(body,ensure_ascii=False),self.prompts[1])
            else:self.assertNotIn(json.dumps(body,ensure_ascii=False),self.prompts[1])
            self.assertNotIn(body,self.prompts[0])

    def test_fixture_expansion_uses_frozen_content_and_rejects_missing_label(self):
        sid=self.create('C1');s=self.lab._load(sid);c=self.lab._control(s)
        doc=c.documents()[0];c.release(doc,2,'test')
        expanded,_=c.expand('[[PASTE: '+doc['name']+']]',2)
        self.assertIn(s['fixtures'][doc['file']],expanded)
        missing,_=c.expand('[[PASTE: NOT HELD]]',2);self.assertNotIn('[[PASTE',missing);self.assertTrue(c.paste_misses)

    def test_unsupported_persona_number_stops_before_next_assistant(self):
        self.answers=['Obtain the written details before deciding.','The rent is £999,888,777.']
        sid=self.create();self.control(sid,'run');self.join();s=self.lab.snapshot(sid)
        self.assertEqual(2,s['calls']);self.assertEqual('invalid_persona',s['stop_reason'])

    def test_question_during_assistant_is_saved_once_and_prioritized(self):
        started=threading.Event();release=threading.Event();seen=[]
        def invoke(req,folder):
            seen.append(req['prompt'])
            if len(seen)==1:started.set();release.wait(5)
            return terminal('First helpful answer.' if len(seen)==1 else 'Here is the requested comparison.')
        self.lab.invoke=invoke;sid=self.create();self.control(sid,'step');self.assertTrue(started.wait(5))
        data=intent(text='Compare the options before continuing.',kind='question')
        self.lab.message(sid,data);self.lab.message(sid,data)
        self.assertEqual(1,self.lab.snapshot(sid)['pending_count']);self.assertNotIn(data['text'],seen[0])
        release.set();self.join();s=self.lab.snapshot(sid)
        self.assertEqual(['persona','assistant','human','assistant'],[m['role'] for m in s['messages']])
        self.assertEqual(2,s['calls']);self.assertEqual(1,s['persona_turn']);self.assertIn(data['text'],seen[1])

    def test_pause_while_persona_generates_keeps_question_without_purchasing_reply(self):
        self.answers=['Obtain written evidence and confirm identity independently.'];sid=self.create();self.control(sid,'step');self.join()
        started=threading.Event();release=threading.Event()
        def invoke(req,folder):started.set();release.wait(5);return terminal('What should I do next?')
        self.lab.invoke=invoke;self.control(sid,'run');self.assertTrue(started.wait(5));self.control(sid,'pause');release.set();self.join()
        s=self.lab.snapshot(sid);self.assertEqual(2,s['calls']);self.assertEqual('persona',s['messages'][-1]['role']);self.assertEqual('paused',s['status'])

    def test_amendment_is_exact_persistent_and_question_is_not_an_amendment(self):
        sid=self.create();self.control(sid,'step');self.join()
        text='Budget is now £2,300, but only for option A if dry.'
        self.send(sid,text,kind='amendment');self.join()
        s=self.lab._load(sid);state=self.lab._store(s).show()
        self.assertEqual([text],state['requirements']['tester-amendments']['value']);self.assertIn(text,self.prompts[-1])
        self.send(sid,'Why is the first option risky?');self.join()
        self.assertEqual([text],self.lab._load(sid)['amendments']);self.assertTrue(self.lab.snapshot(sid)['amended'])

    def test_partial_input_preparation_reconciles_once_without_extra_capture(self):
        sid=self.create();self.control(sid,'step');self.join();data=intent(text='Budget changes to £2,300 only for the named option.',kind='amendment')
        with self.lab.lock:
            s=self.lab._load(sid);s['queue']=[data];s['preparing_input']=data['client_id'];self.lab._save(s)
            store=self.lab._store(s);rid='human-'+uuid.UUID(data['client_id']).hex
            p.event(store,'request.capture',id=rid,text=data['text'],source='interactive-tester:amendment')
        self.control(sid,'recover');self.control(sid,'step');self.join()
        state=store.show();self.assertEqual(1,len(state['requests']));self.assertEqual('resolved',state['requests'][rid]['status'])
        self.assertEqual([data['text']],state['requirements']['tester-amendments']['value'])

    def test_budget_and_unknown_telemetry_stop_further_calls(self):
        sid=self.create(max_calls=1);self.control(sid,'run');self.join();self.assertEqual('budget',self.lab.snapshot(sid)['status'])
        self.assertEqual(1,len(self.prompts))
        sid2=self.create();self.lab.invoke=lambda *_:terminal(tokens=None);self.control(sid2,'run');self.join()
        s=self.lab.snapshot(sid2);self.assertIsNone(s['tokens']);self.assertEqual(1,s['calls']);self.assertEqual('error',s['status'])

    def test_restart_preserves_transcript_and_does_not_dispatch(self):
        sid=self.create();self.control(sid,'step');self.join();before=self.lab.export(sid)
        self.lab.close();self.lab=p.Lab(self.path,invoke=lambda *_:self.fail('restart must not call a model'))
        self.assertEqual(before,self.lab.export(sid));self.assertEqual('paused',self.lab.snapshot(sid)['status'])

    def test_lost_return_recovers_completed_physical_call_and_leaves_paused(self):
        sid=self.create();original=p.session_runner.run_step
        def lost(*a,**k):original(*a,**k);raise OSError('lost return')
        with mock.patch.object(p.session_runner,'run_step',side_effect=lost):self.control(sid,'step');self.join()
        s=self.lab.snapshot(sid);self.assertEqual(1,s['calls']);self.assertEqual('paused',s['status']);self.assertEqual('assistant',s['messages'][-1]['role'])
        self.assertEqual(20,s['tokens'])

    def test_other_session_busy_rejected_and_queued_capacity_counts(self):
        started=threading.Event();release=threading.Event()
        def invoke(*_):started.set();release.wait(5);return terminal()
        self.lab.invoke=invoke;a=self.create();b=self.create();self.control(a,'step');self.assertTrue(started.wait(5))
        with self.assertRaises(p.LabError):self.send(b)
        self.send(a,'a'*8000,'amendment');self.send(a,'b'*8000,'amendment')
        with self.assertRaises(p.LabError):self.send(a,'c'*8000,'amendment')
        self.control(a,'pause');release.set();self.join();self.assertEqual(2,self.lab.snapshot(a)['pending_count'])

    def test_idempotency_conflict_and_model_allowlist(self):
        data=intent(persona_id='P4',model='gpt-6-astra',max_calls=10,max_tokens=10000,seed=1)
        self.assertEqual(self.lab.create(data),self.lab.create(data))
        with self.assertRaises(p.LabError):self.lab.create(dict(data,max_calls=20))
        with self.assertRaises(p.LabError):self.create(model='claude')
        with self.assertRaises(p.LabError):self.create(max_calls=True)

    def test_source_change_stops_before_model(self):
        sid=self.create()
        with mock.patch.object(p,'source_hashes',return_value={'changed':'yes'}):self.control(sid,'step');self.join()
        self.assertFalse(self.prompts);self.assertEqual('error',self.lab.snapshot(sid)['status'])

    def test_private_permissions_and_integrity(self):
        sid=self.create();folder=self.path/sid
        self.assertEqual(0o700,folder.stat().st_mode&0o777);self.assertEqual(0o600,(folder/'session.json').stat().st_mode&0o777)
        payload=json.loads((folder/'session.json').read_text());payload['value']['model']='changed';(folder/'session.json').write_text(json.dumps(payload))
        with self.assertRaises(p.LabError):self.lab.snapshot(sid)

    def test_second_owner_and_unsafe_paths_rejected(self):
        with self.assertRaises(p.LabError):p.Lab(self.path)
        with self.assertRaises(p.LabError):self.lab.snapshot('../other')
        link=self.path/'linked';link.symlink_to(self.path,target_is_directory=True)
        with self.assertRaises(p.LabError):p.Lab(link)

    def test_extended_prompt_capacity_is_explicit_and_still_bounded(self):
        sid=self.create();self.control(sid,'step');self.join();self.assertGreater(len(self.prompts[0]),32000)
        with self.assertRaises(ValueError):p.session_runner.run_step(self.path/sid,'oversize','conversation','gpt-6-astra','x'*32001,'tokens',invoke=self.lab.invoke)
        with self.assertRaises(ValueError):p.session_runner.run_step(self.path/sid,'oversize2','conversation','gpt-6-astra','x','tokens',invoke=self.lab.invoke,max_prompt_chars=256001)

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.lab=p.Lab(Path(self.temp.name).resolve(),invoke=lambda *_:terminal());self.addCleanup(self.lab.close)
        self.server=p.ThreadingHTTPServer(('127.0.0.1',0),p.Handler);self.server.lab=self.lab
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.shutdown)
    def shutdown(self):self.server.shutdown();self.server.server_close();self.thread.join(3)
    def get(self,path,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        c.request('GET',path,headers=headers or {});r=c.getresponse();body=r.read();result=(r.status,dict(r.getheaders()),body);c.close();return result
    def test_static_asset_no_external_assets_and_security_headers(self):
        status,headers,body=self.get('/');self.assertEqual(200,status);self.assertIn('frame-ancestors',headers['Content-Security-Policy']);self.assertEqual('no-store',headers['Cache-Control'])
        self.assertNotIn(b'https://',body);self.assertIn(b'/app.js',body)
    def test_cross_site_link_can_open_static_page_but_not_read_private_api(self):
        headers={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate'}
        self.assertEqual(200,self.get('/',headers)[0])
        self.assertEqual(403,self.get('/api/sessions',dict(headers,**{'X-Pea-Client':'persona-lab'}))[0])
    def test_api_requires_custom_header_and_rejects_cross_origin(self):
        self.assertEqual(403,self.get('/api/sessions')[0])
        base={'X-Pea-Client':'persona-lab'}
        self.assertEqual(200,self.get('/api/sessions',base)[0])
        for extra in ({'Origin':'https://example.com'},{'Sec-Fetch-Site':'cross-site'},{'Host':'attacker.example'}):
            self.assertEqual(403,self.get('/api/sessions',dict(base,**extra))[0])
    def test_no_file_traversal_or_private_static_serving(self):
        for path in ('/../AGENTS.md','/.pea-state/events.json','/api/session/../../secret','/app.js?other'):
            self.assertEqual(404,self.get(path,{'X-Pea-Client':'persona-lab'})[0])
    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for text in ('{"a":1,"a":2}','{"a":NaN}'):
            with self.assertRaises(p.LabError):p.parse_json(text)

if __name__=='__main__':unittest.main()
