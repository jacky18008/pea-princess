"""Offline bounded clarification parsing and immutable schema recovery checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'skills/vet-flat/scripts')]
import conversation_reply as reply
import session_runner as runner
from session_state import SessionStore


class ReplyContractTests(unittest.TestCase):
    def test_zero_or_three_questions_round_trip_with_visible_options(self):
        for count in (0,3):
            value={'message':'Consider the stated tradeoffs.','questions':[
                {'question':'Which direction %d?'%i,'options':['Courtyard','Near transport','More detail','Unsure']} for i in range(count)]}
            decoded=reply.decode(json.dumps(value))
            self.assertEqual(value,decoded)
            transcript=reply.transcript(decoded)
            self.assertTrue(transcript.startswith(value['message']))
            for row in value['questions']:
                self.assertIn(row['question'],transcript)
                for option in row['options']:self.assertIn(option,transcript)

    def test_four_questions_duplicate_keys_and_duplicate_options_rejected(self):
        values=[json.dumps({'message':'Choose.','questions':[{'question':'Which?','options':['A','B']}]*4}),
                '{"message":"First","message":"Second","questions":[]}',
                '{"message":"Choose.","questions":[{"question":"A?","question":"B?","options":["A","B"]}]}',
                json.dumps({'message':'Choose.','questions':[{'question':'Which?','options':['Same','Same']}]})]
        for raw in values:
            with self.subTest(raw=raw),self.assertRaises(ValueError):reply.decode(raw)

    def test_empty_overlong_extra_or_nonstring_fields_cannot_reach_choice_display(self):
        base={'message':'Choose a direction.','questions':[{'question':'Which?','options':['A','B']}]}
        invalid=[{'message':' ','questions':[]},{'message':'x'*2401,'questions':[]},
                 {'message':'Choose.','questions':[],'tool_call':'run something'},
                 {'message':'Choose.','questions':[{'question':' ','options':['A','B']}]},
                 {'message':'Choose.','questions':[{'question':'Which?','options':['A']}]},
                 {'message':'Choose.','questions':[{'question':'Which?','options':['A',True]}]},
                 {'message':'Choose.','questions':[{'question':'Which?','options':['A','B','C','D','E']}]},
                 {'message':'Choose.','questions':[dict(base['questions'][0],selected='A')]}]
        for value in invalid:
            with self.subTest(value=value),self.assertRaises(ValueError):reply.decode(json.dumps(value))


class SchemaRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.store=SessionStore(self.root);self.store.init('schema-test')
        provenance={'actor':'user','authorized':True,'source_id':'offline-fixture','quote':'Allow 1000 test tokens.'}
        self.apply({'op':'budget.set','id':'tokens','scope':'api_tokens','unit':'tokens','limit':1000,'provenance':provenance})
        self.apply({'op':'task.add','id':'reply','title':'One synthetic reply','budget_ids':['tokens'],'acceptance':['Persist observed reply.']})
        patch=mock.patch('durable_run.source_fingerprint',return_value={'test':'frozen'});patch.start();self.addCleanup(patch.stop)

    def apply(self,event):return self.store.apply(event,self.store.show()['revision'])

    def test_default_transport_passes_saved_schema_before_prompt_delimiter(self):
        answer=json.dumps({'message':'Synthetic structured reply.','questions':[]})
        def launch(command,cwd,timeout,family,attempts):
            self.assertEqual(1,attempts);self.assertEqual('codex',family)
            index=command.index('--output-schema')
            self.assertLess(index,command.index('--'))
            schema=Path(command[index+1])
            self.assertEqual(reply.SCHEMA,json.loads(schema.read_text()))
            self.assertEqual(0o600,schema.stat().st_mode&0o777)
            Path(command[command.index('--output-last-message')+1]).write_text(answer)
            event={'type':'turn.completed','usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0}}
            return runner.launch.LaunchResult(stdout=json.dumps(event),exit_code=0)
        with mock.patch.object(runner.launch,'run',side_effect=launch) as mocked:
            result=runner.run_step(self.root,'transport','reply','test-model','Answer.','tokens',response_schema=reply.SCHEMA)
        mocked.assert_called_once();self.assertEqual(answer,result['answer']);self.assertEqual(20,result['processed_tokens'])

    def test_caller_schema_mutation_cannot_change_frozen_callback_request(self):
        schema=copy.deepcopy(reply.SCHEMA)
        def invoke(request,folder):
            schema['properties']['questions']['maxItems']=4
            self.assertEqual(3,request['response_schema']['properties']['questions']['maxItems'])
            return {'id':'answer','status':'complete','exit_code':0,'errors':[],'tool_events':[],
                    'malformed_event_lines':0,'terminal_usage_events':1,
                    'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                    'answer':json.dumps({'message':'Synthetic reply.','questions':[]})}
        runner.run_step(self.root,'copied','reply','test-model','Answer.','tokens',invoke=invoke,response_schema=schema)
        manifest=json.loads((self.root/'.pea-state/runs/copied/manifest.json').read_text())['value']
        self.assertEqual(3,manifest['request']['response_schema']['properties']['questions']['maxItems'])

    def test_rehashed_schema_tamper_cannot_recover_or_charge_again(self):
        calls=[]
        def invoke(request,folder):
            calls.append(copy.deepcopy(request))
            return {'id':'answer','status':'complete','exit_code':0,'errors':[],'tool_events':[],
                    'malformed_event_lines':0,'terminal_usage_events':1,
                    'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                    'answer':json.dumps({'message':'Synthetic reply.','questions':[]})}
        schema=copy.deepcopy(reply.SCHEMA)
        result=runner.run_step(self.root,'step','reply','test-model','Answer the fixture.','tokens',invoke=invoke,
                               response_schema=schema,presentation='conversation')
        self.assertEqual('recorded',result['status']);self.assertEqual(schema,calls[0]['response_schema'])
        self.assertEqual(20,self.store.show()['budgets']['tokens']['spent'])
        path=self.root/'.pea-state/runs/step/manifest.json';saved=json.loads(path.read_text())
        saved['value']['request']['response_schema']['properties']['questions']['maxItems']=4
        saved['sha256']=runner._digest(saved['value']);path.write_text(json.dumps(saved))
        with self.assertRaises(ValueError):runner.recover(self.root,'step')
        self.assertEqual(1,len(calls));self.assertEqual(20,self.store.show()['budgets']['tokens']['spent'])


if __name__=='__main__':unittest.main()
