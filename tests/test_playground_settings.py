"""Configuration reaches the actor and remains auditable; no provider calls."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import persona_playground as p
import playground_settings as settings


def intent(**data):
    return dict(client_id=str(uuid.uuid4()),**data)


class SettingsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.requests=[]
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            return {'id':'answer','status':'complete','exit_code':0,'errors':[],
                    'tool_events':[],'malformed_event_lines':0,'terminal_usage_events':1,
                    'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                    'answer':json.dumps({'message':'先比較價格與空間。','questions':[]})}
        self.lab=p.Lab(self.root,invoke=invoke);self.addCleanup(self.lab.close)

    def create(self,**extra):
        data=intent(research_mode='live',output_mode='agent',initial_request='Compare the supplied homes.',
                    model='gpt-6-astra',max_calls=4,max_tokens=10000,seed=1)
        data.update(extra)
        return self.lab.create(data)['id']

    def step(self,sid):
        self.lab.control(sid,intent(action='step'));self.lab.worker.join(10)
        self.assertFalse(self.lab.worker.is_alive())

    def test_defaults_are_saved_and_reported_before_any_call(self):
        sid=self.create();expected=settings.configured({},'live')
        for data in (self.lab._load(sid),self.lab.snapshot(sid),self.lab.export(sid),self.lab.inspect(sid)['session']):
            self.assertEqual(expected,data['execution_settings'])
        self.assertEqual('standard',expected['research_depth']);self.assertEqual('low',expected['reasoning_effort'])
        self.assertIn('Initial budget_mode: standard',self.lab._load(sid)['system'])
        self.assertEqual([],self.requests)

    def test_selected_settings_reach_prompt_request_and_pinned_call(self):
        sid=self.create(research_depth='deep',reasoning_effort='high');self.step(sid)
        request=self.requests[0];s=self.lab._load(sid);row=s['calls'][0]
        self.assertIn('Initial budget_mode: deep',request['prompt'])
        self.assertEqual('high',request['execution_settings']['reasoning_effort'])
        self.assertEqual(s['execution_settings'],row['execution_settings'])
        path=self.root/sid/'.pea-state/runs'/row['id']/'manifest.json'
        manifest=json.loads(path.read_text())['value']
        self.assertEqual(s['execution_settings'],manifest['request']['execution_settings'])
        self.assertEqual(p._digest(manifest['request']),manifest['request_hash'])
        changed=copy.deepcopy(manifest['request']);changed['execution_settings']['reasoning_effort']='low'
        self.assertNotEqual(p._digest(changed),manifest['request_hash'])

    def test_replay_can_select_different_settings_without_modifying_original(self):
        sid=self.create(research_depth='deep',reasoning_effort='high');self.step(sid)
        original=(self.root/sid/'session.json').read_bytes();preview=self.lab.replay(sid)
        replay=self.lab.replay(sid,intent(source_sha256=preview['source_sha256'],model='gpt-5.6-terra',
                max_calls=2,max_tokens=10000,research_depth='lite',reasoning_effort='medium'))['id']
        self.assertEqual(1,len(self.requests),'replay creation cannot call a model')
        self.step(replay)
        self.assertEqual('lite',self.requests[1]['execution_settings']['research_depth'])
        self.assertEqual('medium',self.requests[1]['execution_settings']['reasoning_effort'])
        self.assertEqual(original,(self.root/sid/'session.json').read_bytes())

    def test_invalid_selection_is_rejected_before_session_creation(self):
        for field,value in [('research_depth','full'),('research_depth',None),('research_depth',True),
                            ('reasoning_effort','anything'),('reasoning_effort',[]),('reasoning_effort',None)]:
            with self.subTest(field=field,value=value),self.assertRaises(p.LabError):
                self.create(**{field:value})
        self.assertEqual([],list(self.root.glob('*/session.json')));self.assertEqual([],self.requests)

    def test_historical_unknowns_are_not_backfilled_and_fixture_values_remain_known(self):
        sid=self.create();s=self.lab._load(sid);s.pop('execution_settings');self.lab._save(s)
        path=self.root/sid/'session.json';before=path.read_bytes()
        for data in (self.lab.snapshot(sid),self.lab.export(sid),self.lab.inspect(sid)['session']):
            self.assertEqual(settings.unknown(),data['execution_settings'])
        self.assertIsNone(self.lab.inspect(sid)['session']['configured_effort'])
        self.assertEqual(before,path.read_bytes());self.assertEqual([],self.requests)
        legacy=settings.read_session({'runtime_settings':{'budget_mode':'lite'}})
        self.assertEqual('lite',legacy['research_depth']);self.assertIsNone(legacy['reasoning_effort'])
        self.assertEqual('legacy_record',legacy['research_depth_source'])

    def test_persona_card_depth_and_explicit_override_remain_distinct(self):
        card=next(iter(self.lab.cards.values()))
        default=settings.configured({},'fixture',card)
        self.assertEqual(card['settings']['budget_mode'],default['research_depth'])
        self.assertEqual('persona_card',default['research_depth_source'])
        selected=settings.configured({'research_depth':'lite','reasoning_effort':'high'},'fixture',card)
        persona=settings.for_call({'execution_settings':selected},'persona')
        self.assertIsNone(persona['research_depth']);self.assertEqual('not_applicable',persona['research_depth_source'])
        self.assertEqual('high',persona['reasoning_effort'])


class SettingsTransportTests(unittest.TestCase):
    def test_configured_effort_is_sent_to_cli_instead_of_hardcoded_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen=[]
            def start(command,**kwargs):
                seen.append(command)
                answer=command[command.index('--output-last-message')+1]
                code='import sys,json;sys.stdin.read();open(sys.argv[1],"w").write("answer");print(json.dumps({"type":"turn.completed","usage":{"input_tokens":15,"output_tokens":5,"cached_input_tokens":0}}))'
                return subprocess.Popen([sys.executable,'-c',code,answer],**kwargs)
            request={'prompt':'synthetic input','model':'gpt-6-astra','timeout_seconds':10,
                     'execution_settings':settings.configured({'reasoning_effort':'high'},'live')}
            with mock.patch.object(p.shutil,'which',return_value='/fake/codex'),mock.patch.object(p.launch,'start_process',side_effect=start):
                result=p.codex_invoke(request,Path(tmp).resolve())
            self.assertIn('model_reasoning_effort="high"',seen[0])
            self.assertNotIn('model_reasoning_effort="low"',seen[0])
            self.assertEqual('answer',result['answer'])


if __name__=='__main__':unittest.main()
