"""Durable fixed-input replay boundaries, without model/network calls."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import persona_playground as p
from test_persona_playground import intent, actor_terminal

class ReplayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.requests=[]
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            return actor_terminal(request,'Fresh answer %s'%len(self.requests))
        self.lab=p.Lab(self.root/'sessions',invoke=invoke);self.addCleanup(self.close)
    def close(self):
        if self.lab.worker:self.lab.worker.join(10)
        self.lab.close()
    def join(self):
        for _ in range(4):
            worker=self.lab.worker
            if worker:worker.join(10);self.assertFalse(worker.is_alive())
            if worker is self.lab.worker:break
    def source(self,with_files=False):
        data=intent(research_mode='live',output_mode='agent',initial_request='Initial human request',model='gpt-6-astra',max_calls=5,max_tokens=10000,seed=1)
        if with_files:
            self.original=self.root/'selected.txt';self.original.write_text('FROZEN FIRST FILE')
            data['initial_request']=str(self.original)
        sid=self.lab.create(data)['id']
        self.lab.control(sid,intent(action='step'));self.join()
        second=intent(text='FOLLOWUP FUTURE sentinel; budget reduced.',kind='amendment')
        if with_files:
            f=self.lab.upload({'name':'later.txt','content_base64':base64.b64encode(b'FUTURE FILE').decode()})
            second['attachments']=[f['id']]
        self.lab.message(sid,second);self.join()
        self.requests.clear()
        return sid
    def clone(self,sid,**extra):
        preview=self.lab.replay(sid)
        data=intent(source_sha256=preview['source_sha256'],model='gpt-5.6-terra',max_calls=8,max_tokens=10000)
        data.update(extra)
        return self.lab.replay(sid,data)['id'],data
    def test_clone_old_runtime_no_dispatch_and_idempotence(self):
        sid=self.source();s=self.lab._load(sid);s['sources']={'old':'version'};self.lab._save(s)
        old=(self.lab._folder(sid)/'session.json').read_bytes()
        replay,data=self.clone(sid)
        self.assertEqual(replay,self.lab.replay(sid,data)['id']);self.assertEqual([],self.requests)
        self.assertEqual([],self.lab.snapshot(replay)['messages']);self.assertTrue(self.lab.snapshot(replay)['compatible'])
        self.assertEqual(old,(self.lab._folder(sid)/'session.json').read_bytes())
        with self.assertRaises(p.LabError):self.lab.replay(sid,dict(data,model='gpt-6-astra'))
    def test_step_then_run_regenerates_new_prefix_without_old_answers_or_future(self):
        sid=self.source();r,_=self.clone(sid)
        self.lab.control(r,intent(action='step'));self.join()
        self.assertEqual(1,len(self.requests));self.assertNotIn('FOLLOWUP FUTURE',self.requests[0]['prompt'])
        self.assertNotIn('Fresh answer 1',self.requests[0]['prompt']);self.assertNotIn('Fresh answer 2',self.requests[0]['prompt'])
        self.lab.control(r,intent(action='run'));self.join()
        self.assertEqual(2,len(self.requests));self.assertIn('FOLLOWUP FUTURE',self.requests[1]['prompt'])
        self.assertIn('Fresh answer 1',self.requests[1]['prompt']);self.assertNotIn('Fresh answer 2',self.requests[1]['prompt'])
        s=self.lab.snapshot(r);self.assertEqual(0,s['replay']['remaining']);self.assertEqual(2,s['replay']['completed'])
        self.assertEqual(['complete','complete'],[x['status'] for x in s['replay_comparison']])
        self.assertEqual('gpt-5.6-terra',self.lab._load(r)['model'])
        self.assertEqual(['Initial human request','FOLLOWUP FUTURE sentinel; budget reduced.'],self.lab._store(self.lab._load(r)).show()['requirements']['live-user-inputs']['value'])
        self.assertEqual(40,s['tokens'])
        self.assertEqual(2,len(self.lab.inspect(r,packet=True)['replay_comparison']))
    def test_changed_original_and_later_source_deletion_do_not_change_selected_snapshots(self):
        sid=self.source(True);r,_=self.clone(sid)
        self.original.write_text('EXTERNAL CHANGE')
        for f in self.lab._load(sid)['attachments'].values():Path(f['path']).unlink()
        self.lab.control(r,intent(action='step'));self.join()
        self.assertEqual(1,len(self.requests));self.assertEqual(1,len(self.requests[0]['input_files']))
        self.assertEqual('FROZEN FIRST FILE',Path(self.requests[0]['input_files'][0]['path']).read_text())
        self.assertNotIn('later.txt',self.requests[0]['prompt'])
        self.lab.control(r,intent(action='step'));self.join()
        self.assertEqual(2,len(self.requests[-1]['input_files']))
        self.assertIn('FUTURE FILE',[Path(f['path']).read_text() for f in self.requests[-1]['input_files']])
    def test_changed_source_pin_or_attachment_fails_before_any_dispatch(self):
        sid=self.source(True);preview=self.lab.replay(sid)
        data=intent(source_sha256=preview['source_sha256'],model='gpt-6-astra',max_calls=3,max_tokens=10000)
        s=self.lab._load(sid);self.lab._save(s)
        with self.assertRaises(p.LabError):self.lab.replay(sid,data)
        file=Path(next(iter(s['attachments'].values()))['path']);file.chmod(0o600);file.write_text('broken')
        with self.assertRaises(ValueError):self.clone(sid)
        self.assertEqual([],self.requests);self.assertEqual(1,len(self.lab.list()['sessions']))
    def test_budget_does_not_release_or_buy_next_turn(self):
        sid=self.source();r,_=self.clone(sid,max_calls=1)
        self.lab.control(r,intent(action='run'));self.join()
        s=self.lab.snapshot(r);self.assertEqual(1,len(self.requests));self.assertEqual('budget',s['status']);self.assertEqual(1,s['replay']['remaining'])
        self.assertNotIn('FOLLOWUP FUTURE',[m['text'] for m in s['messages']])
    def test_failure_unknown_usage_never_retries(self):
        sid=self.source();r,_=self.clone(sid)
        seen=[]
        def invoke(request,folder):seen.append(request);return actor_terminal(request,'Unknown spending',tokens=None)
        self.lab.invoke=invoke;self.lab.control(r,intent(action='run'));self.join()
        self.assertEqual(1,len(seen));s=self.lab.snapshot(r);self.assertIn(s['status'],('error','budget'));self.assertIsNone(s['tokens'])
        with self.assertRaises(p.LabError):self.lab.control(r,intent(action='run'))
        self.assertEqual(1,len(seen))
    def test_pause_and_restart_preserve_progress_without_calls(self):
        sid=self.source();r,_=self.clone(sid)
        started=threading.Event();release=threading.Event();seen=[]
        def invoke(request,folder):seen.append(request);started.set();release.wait(5);return actor_terminal(request,'New response')
        self.lab.invoke=invoke;self.lab.control(r,intent(action='run'));self.assertTrue(started.wait(5))
        self.lab.control(r,intent(action='pause'));release.set();self.join()
        self.assertEqual(1,len(seen));self.assertEqual(1,self.lab.snapshot(r)['replay']['completed'])
        self.lab.close();self.lab=p.Lab(self.root/'sessions',invoke=invoke)
        self.assertEqual(1,len(seen));self.assertEqual(1,self.lab.snapshot(r)['replay']['remaining'])
    def test_human_intervention_stops_auto_and_is_recorded_as_modified(self):
        sid=self.source();r,_=self.clone(sid)
        started=threading.Event();release=threading.Event();seen=[]
        def invoke(request,folder):
            seen.append(request)
            if len(seen)==1:started.set();release.wait(5)
            return actor_terminal(request,'New response')
        self.lab.invoke=invoke;self.lab.control(r,intent(action='run'));self.assertTrue(started.wait(5))
        self.lab.message(r,intent(text='LIVE INTERRUPTION without historic follow-up.',kind='question'))
        release.set();self.join()
        self.assertEqual(2,len(seen));self.assertIn('LIVE INTERRUPTION',seen[1]['prompt']);self.assertNotIn('FOLLOWUP FUTURE',seen[1]['prompt'])
        s=self.lab.snapshot(r);self.assertTrue(s['replay']['modified']);self.assertEqual(1,s['replay']['remaining'])
    def test_legacy_grouping_is_one_call_and_never_imports_path_text(self):
        sid=self.source();s=self.lab._load(sid)
        s['output_mode']='checked';s['messages']=[{'role':'human','text':'/missing/legacy/no-selected-file.txt'}, {'role':'human','text':'Additional constraint','kind':'amendment'}, {'role':'assistant','text':'LEGACY original answer','call_id':'call-001-assistant'}, {'role':'human','text':'Unanswered message'}]
        s['queue']=[intent(text='Queued not answered',kind='question')];self.lab._save(s)
        self.assertEqual(2,self.lab.replay(sid)['excluded_pending_count'])
        r,_=self.clone(sid);self.lab.control(r,intent(action='run'));self.join()
        self.assertEqual(1,len(self.requests));self.assertIn('/missing/legacy/no-selected-file.txt',self.requests[0]['prompt']);self.assertIn('Additional constraint',self.requests[0]['prompt'])
        self.assertNotIn('LEGACY original answer',self.requests[0]['prompt']);self.assertNotIn('Unanswered message',self.requests[0]['prompt'])
        self.assertEqual(2,len([m for m in self.lab.snapshot(r)['messages'] if m['role']=='human']))
    def test_busy_pending_fixture_and_invalid_settings_are_rejected(self):
        sid=self.source();self.lab.busy=sid
        with self.assertRaises(p.LabError):self.lab.replay(sid)
        self.lab.busy=None
        for extra in ({'max_calls':0},{'max_tokens':True},{'model':'claude-opus-5'}):
            with self.assertRaises(p.LabError):self.clone(sid,**extra)
        fixture=self.lab.create(intent(persona_id='P4',model='gpt-6-astra',max_calls=4,max_tokens=10000,seed=1))['id']
        with self.assertRaises(p.LabError):self.lab.replay(fixture)
        self.assertEqual([],self.requests)

    def test_incomplete_creation_cannot_be_reused_or_dispatched(self):
        sid=self.source();r,data=self.clone(sid)
        s=self.lab._load(r);s['replay']['initialized']=False;s['status']='interrupted';self.lab._save(s)
        with self.assertRaises(p.LabError):self.lab.replay(sid,data)
        with self.assertRaises(p.LabError):self.lab.control(r,intent(action='run'))
        self.assertEqual([],self.requests)

    def test_attachment_only_comparison_retains_selection_and_empty_original_text(self):
        f=self.lab.upload({'name':'brief.txt','content_base64':base64.b64encode(b'Brief source.').decode()})
        sid=self.lab.create(intent(research_mode='live',output_mode='agent',initial_request='',attachments=[f['id']],model='gpt-6-astra',max_calls=2,max_tokens=10000,seed=1))['id']
        self.lab.control(sid,intent(action='step'));self.join();self.requests.clear()
        r,_=self.clone(sid);self.lab.control(r,intent(action='step'));self.join()
        s=self.lab.snapshot(r)
        self.assertEqual('',s['messages'][0]['text']);self.assertEqual(1,s['replay_comparison'][0]['attachment_count'])
        self.assertEqual(1,len(self.requests[0]['input_files']))

    def test_implementation_update_stops_before_releasing_next_input(self):
        sid=self.source();r,_=self.clone(sid)
        self.lab.control(r,intent(action='step'));self.join()
        with mock.patch.object(p,'source_hashes',return_value={'updated':'version'}):
            with self.assertRaises(p.LabError):self.lab.control(r,intent(action='run'))
        self.assertEqual(1,len(self.requests));self.assertEqual(1,self.lab.snapshot(r)['replay']['remaining'])

if __name__=='__main__':unittest.main()
