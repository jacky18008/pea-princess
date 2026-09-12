"""Offline continuity and freshness checks, with real private result files."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest import mock
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import persona_playground as p
import area_scan_store as scans


def intent(**fields): return dict(client_id=str(uuid.uuid4()), **fields)
def reply():
    return {'id':'answer','status':'complete','exit_code':0,'errors':[], 'tool_events':[],
            'malformed_event_lines':0,'terminal_usage_events':1,
            'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
            'answer':json.dumps({'message':'A useful comparison.','questions':[]})}


class ResearchHandoff(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.requests=[]
        patch=mock.patch.object(p,'source_hashes',return_value={'fixed':'test'});patch.start();self.addCleanup(patch.stop)
        self.lab=p.Lab(self.root,invoke=self.invoke);self.addCleanup(self.close)
    def close(self):
        self.join();self.lab.close()
    def join(self):
        if self.lab.worker:
            self.lab.worker.join(10);self.assertFalse(self.lab.worker.is_alive())
    def invoke(self,request,folder):
        self.requests.append(copy.deepcopy(request));return reply()
    def create(self):
        return self.lab.create(intent(research_mode='live',output_mode='agent',initial_request='Compare these streets.',model='gpt-5.6-terra',max_calls=4,max_tokens=10000,seed=1))['id']
    def step(self,sid):self.lab.control(sid,intent(action='step'));self.join()
    def save_scan(self,folder):
        target=p.playground_research.from_call(folder)
        out={'schema':'vet-flat/area-scan/2','ok':True,'retrieved_at':'2026-09-12T00:00:00Z','reading':['known observation'],'not_found':[],'sources':[]}
        scans.run(target,{'postcode':'W6 0PJ','depth':'standard','requested_depth':'standard'},'test-source',lambda:out,lambda:'2026-09-12T00:00:00Z')
        return target
    def test_results_survive_restart_and_enter_next_prompt_without_other_sessions(self):
        def first(req,folder):
            self.save_scan(folder);return self.invoke(req,folder)
        self.lab.invoke=first;sid=self.create();self.step(sid)
        exported=self.lab.export(sid);rows=exported['calls'][0]['research_results']['results']
        self.assertEqual(1,len(rows));saved=Path(rows[0]['path']);before=saved.read_bytes()
        self.assertEqual(0o600,saved.stat().st_mode&0o777)
        self.lab.close();self.lab=p.Lab(self.root,invoke=self.invoke)
        self.assertEqual(exported,self.lab.export(sid))
        other=self.create();self.assertEqual([],p.playground_research.index(self.root/other)['results'])
        self.lab.message(sid,intent(text='Budget is now lower; explain the previous noise result, no new search.',kind='amendment'));self.join()
        self.assertEqual(2,len(self.requests));self.assertIn(str(saved),self.requests[-1]['prompt'])
        self.assertIn('2026-09-12T00:00:00Z',self.requests[-1]['prompt'])
        self.assertNotIn(str(self.root/other),self.requests[-1]['prompt'])
        self.assertEqual(before,saved.read_bytes())
        self.assertEqual(rows,self.lab.export(sid)['calls'][1]['research_results']['results'])
    def test_invalid_result_is_a_gap_and_symlink_directory_is_rejected(self):
        sid=self.create();folder=self.root/sid/'.pea-state'/'runs'/'call-001-assistant';folder.mkdir(parents=True)
        target=self.save_scan(folder);entry=next(target.glob('*.json'));entry.write_text('{}')
        packet=p.playground_research.index(self.root/sid)
        self.assertEqual([],packet['results']);self.assertTrue(packet['gaps'])
        other=self.create();(self.root/other/'research-results').symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):p.playground_research.context(self.root/other)
    def test_observation_failure_does_not_strand_valid_paid_reply(self):
        sid=self.create()
        original=p.playground_research.index
        count=[0]
        def fail_after_prepare(session):
            count[0]+=1
            if count[0]>1:raise OSError('disk observation unavailable')
            return original(session)
        with mock.patch.object(p.playground_research,'index',side_effect=fail_after_prepare):self.step(sid)
        saved=self.lab._load(sid)
        self.assertIsNone(saved['pending_call']);self.assertEqual('paused',saved['status'])
        self.assertEqual('assistant',saved['messages'][-1]['role'])
        self.assertEqual('unavailable',saved['calls'][0]['research_results']['observation_status'])
        self.assertEqual(20,self.lab.snapshot(sid)['tokens']);self.assertEqual(1,len(self.requests))
    def test_stale_source_blocks_creation_without_dispatch(self):
        before=set(self.root.iterdir())
        with mock.patch.object(p.playground_dev_sync,'source_status',return_value={'current':False,'reason':'changed'}):
            with self.assertRaises(p.LabError):self.create()
        self.assertEqual(before,set(self.root.iterdir()));self.assertFalse(self.requests)
    def test_source_change_does_not_consume_queued_input_or_start_next_call(self):
        sid=self.create();self.step(sid)
        with mock.patch.object(p.playground_dev_sync,'source_status',return_value={'current':False,'reason':'changed'}):
            self.lab.message(sid,intent(text='Still compare only these two.',kind='question'));self.join()
        saved=self.lab._load(sid)
        self.assertEqual(1,len(self.requests));self.assertEqual(1,len(saved['queue']))
        self.assertEqual('Still compare only these two.',saved['queue'][0]['text'])
        self.assertNotIn('Still compare only these two.',[m['text'] for m in saved['messages']])
    def test_dispatch_lease_covers_receipt_and_final_state_writes(self):
        sid=self.create();exits=[]
        @contextmanager
        def guard(root):
            try:yield
            finally:
                saved=self.lab._load(sid)
                exits.append((self.lab.busy,saved['status'],saved['calls'][0]['receipt']['physical_status']))
        with mock.patch.object(p.playground_dev_sync,'dispatch_guard',guard):self.step(sid)
        self.assertEqual([(None,'paused','complete')],exits)


if __name__=='__main__':unittest.main()
