"""Offline live-lane contracts: real input, bounded calls, receipts and no simulator."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import persona_playground as p
import public_source_snapshot


def intent(**data):
    return dict(client_id=str(uuid.uuid4()), **data)


def terminal(candidates=None, focus_fields=None):
    return {'id':'answer', 'status':'complete', 'exit_code':0, 'errors':[],
            'tool_events':[], 'malformed_event_lines':0, 'terminal_usage_events':1,
            'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
            'answer':json.dumps({'candidates':candidates or [],'focus_fields':focus_fields or []})}


class LiveLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.requests=[]
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request));return terminal()
        self.lab=p.Lab(self.root,invoke=invoke);self.addCleanup(self.close)

    def close(self):
        self.join();self.lab.close()

    def join(self):
        for _ in range(3):
            worker=self.lab.worker
            if worker:worker.join(10);self.assertFalse(worker.is_alive())
            if worker is self.lab.worker:break

    def create(self, **extra):
        data=intent(research_mode='live',initial_request='Find a London home near my university; I have not chosen a campus.',
                    model='gpt-6-astra',max_calls=5,max_tokens=10000,seed=1)
        data.update(extra);return self.lab.create(data)['id']

    def step(self, sid):
        self.lab.control(sid,intent(action='step'));self.join()

    def test_create_uses_exact_human_input_and_current_skill_without_persona(self):
        text='  Help me compare real homes.\nBudget includes bills, but the ceiling is undecided.  '
        with mock.patch.object(p.personas,'fixture_text',side_effect=AssertionError('no fixture')), \
                mock.patch.object(p,'FrozenController',side_effect=AssertionError('no simulator')):
            sid=self.create(initial_request=text)
        s=self.lab._load(sid);view=self.lab.snapshot(sid);state=self.lab._store(s).show()
        self.assertEqual([['user',text]],s['history']);self.assertEqual([],s['persona_history'])
        self.assertEqual(1,s['live_gate_version']);self.assertIsNone(s['current_acceptance'])
        self.assertEqual('not_checked',view['comparison_status']);self.assertIsNone(view['current_comparison'])
        self.assertEqual({},s['fixtures']);self.assertEqual({},s['card'])
        self.assertEqual(['human'],[m['role'] for m in view['messages']])
        self.assertEqual([text],state['requirements']['live-user-inputs']['value'])
        self.assertEqual(text,state['requests']['human-initial']['text'])
        self.assertIn((ROOT/'skills/vet-flat/SKILL.md').read_text(),s['system'])
        for name in ('listing-evidence.md','conversation-quality.md'):
            self.assertIn((ROOT/'skills/vet-flat/references'/name).read_text(),s['system'])
        onboarding=(ROOT/'skills/vet-flat/references/onboarding.md').read_text()
        self.assertIn(onboarding.split('\n## 2b.')[0],s['system'])
        self.assertNotIn('### Worked example (fictional)',s['system'])
        self.assertIn(onboarding,p.live_system('Help me turn my housing history into preferences.'))
        self.assertEqual('live',view['research_mode']);self.assertIsNone(view['persona_id'])
        self.assertIn('廣告刊登不等於已確認可租',view['capability_status'])
        self.assertIn('skills/vet-flat/SKILL.md',s['sources']);self.assertEqual([],self.requests)

    def test_live_fields_reject_fixture_mix_empty_or_invalid_mode_before_writes(self):
        for extra in ({'initial_request':''},{'initial_request':' '*3},{'initial_request':False},
                      {'initial_request':'x'*8001},{'persona_id':'P4'},{'research_mode':'search'},
                      {'max_calls':True}):
            with self.subTest(extra=extra),self.assertRaises(p.LabError):self.create(**extra)
        self.assertEqual([],list(self.root.glob('*/session.json')));self.assertEqual([],self.requests)

    def test_followup_inquiry_survives_actor_omission_export_and_reopen(self):
        urls = ['https://www.getliving.com/apartments/unit-a',
                'https://www.getliving.com/apartments/unit-b']
        def capture(url, folder):
            folder.mkdir(mode=0o700)
            rent = '2,250' if url == urls[0] else '1,800'
            body = ('1 bedroom apartment\nRent: £' + rent + ' per month\nArea: 50 m²\n').encode('utf-8')
            (folder/'text.txt').write_bytes(body)
            return {'source_url':url,'ok':True,'http_status':200,'retrieved_at':'2026-09-11T10:00:00Z',
                    'text_sha256':hashlib.sha256(body).hexdigest()}
        def invoke(request, folder):
            self.requests.append(copy.deepcopy(request))
            return terminal([{'source_url':url,'label':'Discovery only'} for url in urls], ['rent_pcm'])
        self.lab.invoke = invoke
        sid = self.create(initial_request='房租上限 £2300。我要一房。')
        question = '房租上限改成 £2100。暖氣費包含在房租裡嗎？'
        with mock.patch.object(public_source_snapshot, 'capture', side_effect=capture):
            self.step(sid)
            self.lab.message(sid, intent(text=question, kind='question'))
            self.join()
        view = self.lab.snapshot(sid)
        artifact = view['current_comparison']
        self.assertEqual('current', view['comparison_status'], view['notice'])
        self.assertEqual(1, len(artifact['recommendation']['blocked']))
        self.assertEqual(1, len(artifact['recommendation']['ranking']))
        selected = artifact['recommendation']['ranking'][0]['candidate_id']
        self.assertEqual([selected], [row['candidate_id'] for row in artifact['information_todos']])
        self.assertIn('暖氣', artifact['reply']['message'])
        self.assertTrue(any('暖氣' in row for row in artifact['presentation']['todos']))
        self.assertFalse(any(row['field'] == 'heating_included' for row in artifact['constraints']['requirements']))
        exported = self.lab.export(sid)
        self.assertEqual(artifact, exported['current_comparison'])
        self.assertEqual(artifact['reply']['message'], view['messages'][-1]['text'])
        self.assertEqual(question, exported['interventions'][0]['text'])
        self.assertEqual('historical', view['messages'][1]['comparison_status'])
        self.lab.close()
        self.lab = p.Lab(self.root, invoke=lambda *args: self.fail('reopen must not call model'))
        reopened = self.lab.snapshot(sid)
        self.assertEqual(artifact, reopened['current_comparison'])
        self.assertEqual(2, reopened['calls'])
        self.assertEqual(40, reopened['tokens'])

    def test_one_human_step_publishes_host_reply_and_retains_raw_web_events_without_persona(self):
        web={'type':'item.completed','item':{'id':'web1','type':'web_search','query':'permitted public operator'}}
        raw='{"type":"item.completed","item":{"type":"agent_message","text":"Useful progress."}}\n'
        source_url='https://www.getliving.com/apartments/unit-1'
        candidate={'source_url':source_url,'label':'Actor says: guaranteed available and the best choice.'}
        def capture(url,folder):
            self.assertEqual(source_url,url)
            folder.mkdir(mode=0o700)
            body='1 bedroom apartment\nRent: £1,900 per month\nArea: 50 m²\nFirst floor\n'.encode('utf-8')
            (folder/'text.txt').write_bytes(body)
            return {'source_url':url,'ok':True,'http_status':200,'retrieved_at':'2026-09-10T23:00:00Z',
                    'source_claims_verified':False,'text_sha256':hashlib.sha256(body).hexdigest()}
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            result=terminal([candidate],['availability'])
            result.update(tool_events=[web],launch_result={'stdout':raw,'stderr':''});return result
        self.lab.invoke=invoke;sid=self.create()
        with mock.patch.object(p,'FrozenController',side_effect=AssertionError('no simulator')), \
                mock.patch.object(public_source_snapshot,'capture',side_effect=capture) as captured:
            self.step(sid)
        self.assertEqual(1,captured.call_count)
        s=self.lab.snapshot(sid)
        self.assertEqual(1,len(self.requests));self.assertEqual('live_research',self.requests[0]['tool_policy'])
        self.assertEqual(p.LIVE_REPLY_SCHEMA,self.requests[0]['response_schema'])
        self.assertEqual({'candidates','focus_fields'},set(self.requests[0]['response_schema']['properties']))
        self.assertEqual(300,self.requests[0]['timeout_seconds'])
        self.assertIn('Host request time before dispatch:',self.requests[0]['prompt'])
        self.assertIn('not an exact per-source retrieval timestamp',self.requests[0]['prompt'])
        self.assertEqual(['human','assistant'],[m['role'] for m in s['messages']],s['notice'])
        self.assertEqual([],s['messages'][-1]['questions']);self.assertEqual(20,s['tokens'])
        self.assertIsNone(s['next_actor']);self.assertEqual('paused',s['status'])
        self.assertEqual('current',s['comparison_status'])
        self.assertEqual(s['current_comparison']['reply']['message'],s['messages'][-1]['display_text'])
        self.assertEqual(s['current_comparison'],self.lab.export(sid)['current_comparison'])
        self.assertNotIn(candidate['label'],s['messages'][-1]['text'])
        self.assertNotIn('Useful progress.',s['messages'][-1]['text'])
        self.assertIn('1,900',s['messages'][-1]['text'])
        saved=self.lab._load(sid);self.assertIn(source_url,saved['history'][-1][1])
        self.assertEqual('accepted',saved['calls'][0]['acceptance_status'])
        self.assertEqual(candidate,json.loads(saved['calls'][0]['receipt']['answer'])['candidates'][0])
        # The original callback record survives in the physical controller evidence.
        stored='\n'.join(x.read_text() for x in (self.root/sid/'.pea-state/runs').rglob('*.json'))
        self.assertIn('Useful progress.',stored);self.assertIn('web1',stored);self.assertIn(candidate['label'],stored)
        for action in ('run','step'):
            with self.assertRaises(p.LabError):self.lab.control(sid,intent(action=action))
        self.assertEqual(1,len(self.requests))

    def test_followup_during_call_is_exact_deduplicated_and_updates_ordered_inputs(self):
        started=threading.Event();release=threading.Event()
        self.addCleanup(release.set)
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            if len(self.requests)==1:started.set();release.wait(5)
            return terminal()
        self.lab.invoke=invoke;sid=self.create();self.lab.control(sid,intent(action='step'))
        self.assertTrue(started.wait(5))
        change='Keep the old ceiling except option A may be higher only if it is dry.'
        data=intent(text=change,kind='question')
        self.lab.message(sid,data);self.lab.message(sid,data)
        self.assertEqual(1,self.lab.snapshot(sid)['pending_count'])
        release.set();self.join();s=self.lab._load(sid)
        self.assertEqual(2,len(self.requests));self.assertEqual(2,s['persona_turn'])
        self.assertEqual(['human','human','assistant'],[m['role'] for m in s['messages']])
        self.assertEqual(['stale','accepted'],[row['acceptance_status'] for row in s['calls']])
        self.assertEqual(terminal()['answer'],s['calls'][0]['receipt']['answer'])
        self.assertEqual(40,self.lab.snapshot(sid)['tokens'])
        self.assertIn(change,self.requests[-1]['prompt'])
        self.assertEqual([s['history'][0][1],change],self.lab._store(s).show()['requirements']['live-user-inputs']['value'])
        self.assertTrue(all(r['tool_policy']=='live_research' for r in self.requests))
        self.assertIsNone(s['next_actor'])

    def test_caps_invalid_reply_and_restart_do_not_purchase_extra_calls(self):
        sid=self.create(max_calls=1);self.step(sid)
        self.lab.message(sid,intent(text='Please continue the research.',kind='question'));self.join()
        self.assertEqual('budget',self.lab.snapshot(sid)['status']);self.assertEqual(1,len(self.requests))
        sid2=self.create();self.lab.invoke=lambda *_:terminal(
            [{'source_url':'https://www.getliving.com/apartments/%s'%i,'label':'Unit %s'%i} for i in range(4)])
        self.step(sid2);self.assertEqual('error',self.lab.snapshot(sid2)['status'])
        self.assertEqual(20,self.lab.snapshot(sid2)['tokens'])
        before=self.lab.export(sid2);self.lab.close()
        self.lab=p.Lab(self.root,invoke=lambda *_:self.fail('restart must not dispatch'))
        self.assertEqual(before,self.lab.export(sid2))

    def test_actor_message_and_choices_are_rejected_but_preserved_in_raw_receipt(self):
        proposal=json.loads(terminal()['answer'])
        proposal.update(message='Actor says sign this tenancy now.',
                        questions=[{'question':'Pay now?','options':['Yes','Immediately']}])
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            result=terminal();result['answer']=json.dumps(proposal);return result
        self.lab.invoke=invoke;sid=self.create()
        with mock.patch.object(public_source_snapshot,'capture',side_effect=AssertionError('no fetch')) as capture:
            self.step(sid)
        capture.assert_not_called()
        view=self.lab.snapshot(sid);saved=self.lab._load(sid)
        self.assertEqual('error',view['status']);self.assertEqual(20,view['tokens'])
        self.assertEqual(['human'],[m['role'] for m in view['messages']])
        self.assertEqual('rejected',saved['calls'][0]['acceptance_status'])
        self.assertIsNone(view['current_comparison']);self.assertIsNone(saved['current_acceptance'])
        self.assertEqual(proposal,json.loads(saved['calls'][0]['receipt']['answer']))
        self.assertEqual(1,len(self.requests))

    def test_live_source_pins_fail_closed_after_current_skill_changes(self):
        sid=self.create();before=(self.root/sid/'session.json').read_bytes()
        changed=dict(self.lab.runtime_sources,**{'skills/vet-flat/SKILL.md':'changed'})
        with mock.patch.object(p,'source_hashes',return_value=changed):
            with self.assertRaises(p.LabError):self.lab.control(sid,intent(action='step'))
        self.assertEqual(before,(self.root/sid/'session.json').read_bytes());self.assertFalse(self.requests)


class CodexTransportTests(unittest.TestCase):
    def test_live_and_default_argv_and_original_progress_are_retained_without_codex(self):
        for policy,expected in ((None,'disabled'),('live_research','live')):
            with self.subTest(policy=policy),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp).resolve();seen=[]
                def start(command,**kwargs):
                    seen.append(command)
                    self.assertEqual(str(Path(kwargs['cwd'])/'.pea-cache'),kwargs['env']['VETFLAT_CACHE'])
                    self.assertEqual('1',kwargs['env']['PYTHONDONTWRITEBYTECODE'])
                    answer=command[command.index('--output-last-message')+1]
                    code='import sys,json;sys.stdin.read();open(sys.argv[1],"w").write("answer");print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"Visible progress."}}));print(json.dumps({"type":"turn.completed","usage":{"input_tokens":15,"output_tokens":5,"cached_input_tokens":0}}))'
                    return subprocess.Popen([sys.executable,'-c',code,answer],**kwargs)
                request={'prompt':'private stdin text','model':'gpt-6-astra','timeout_seconds':10}
                if policy:request['tool_policy']=policy
                with mock.patch.object(p.shutil,'which',return_value='/fake/codex'),mock.patch.object(p.launch,'start_process',side_effect=start):
                    result=p.codex_invoke(request,folder)
                command=seen[0]
                self.assertIn('web_search="'+expected+'"',command)
                self.assertEqual('workspace-write' if policy=='live_research' else 'read-only',command[command.index('--sandbox')+1])
                self.assertEqual(policy=='live_research','sandbox_workspace_write.network_access=true' in command)
                self.assertIn('skip_host_skill_discovery',command)
                self.assertTrue(any(arg.startswith('skills.config=') and 'enabled=false' in arg for arg in command))
                self.assertEqual(['--','-'],command[-2:]);self.assertNotIn('private stdin text',command)
                self.assertIn('Visible progress.',result['launch_result']['stdout'])
                self.assertEqual(15,result['direct_terminal_usage']['input_tokens'])
                self.assertEqual('answer',result['answer'])


if __name__=='__main__':unittest.main()
