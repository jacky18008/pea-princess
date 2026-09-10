"""Operator release, durable review and usage gates; no model calls."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'bench'),str(ROOT/'skills/vet-flat/scripts')]
import conversation_acceptance as ca


def fixture(n=1, ceiling=2000):
    text='Monthly total ceiling is GBP %d.'%ceiling
    return {'user':text,'preferences':['quiet first'],
        'constraints':{'schema_version':'vet-flat/eligibility-constraints/1','revision':n,
            'requirements':[{'id':'budget','field':'monthly_total','type':'number','operator':'lte',
                'value':ceiling,'unit':'GBP/month','mandatory':True,'basis':['observed','estimate']}],
            'user_requests':{'u%d'%n:text},'exceptions':[]},
        'evidence':{'schema_version':'vet-flat/eligibility-evidence/1',
            'sources':{'quote':'Monthly total estimated GBP 1950.'},
            'candidates':[{'id':'demo','fields':{'monthly_total':{'value':1950,'unit':'GBP/month',
                'qualifier':'estimate','source_id':'quote','quote':'Monthly total estimated GBP 1950.'}}}]}}


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()

    def test_heldout_shape_and_revisions_fail_closed(self):
        cases=[{'id':k,'turns':[fixture(n) for n in range(1,7)]} for k in 'abc']
        self.assertEqual(len(ca.validate_cases(cases)),3)
        bad=copy.deepcopy(cases);bad[1]['turns'][4]['constraints']['revision']=4
        with self.assertRaisesRegex(ValueError,'revision'):ca.validate_cases(bad)
        with self.assertRaisesRegex(ValueError,'three'):ca.validate_cases(cases[:2])

    def test_release_persists_new_conditions_and_preserves_exact_old_request(self):
        home=self.base/'a';home.mkdir()
        ca.native.prepare_workdir(home/'work',{})
        ca.SessionStore(home/'work').init('release-test')
        first=ca.release(home,fixture(),1)
        second=ca.release(home,fixture(2,1800),2)
        store=ca.SessionStore(home/'work')
        self.assertGreater(second['revision'],first['revision'])
        self.assertEqual(second['requirements']['normalized-intent']['value']['conditions']['requirements'][0]['value'],1800)
        self.assertEqual(ca.read(home/'work/current-context.json'),second)
        events=(home/'work/.pea-state/events.json').read_text()
        self.assertIn('Monthly total ceiling is GBP 2000.',events)
        self.assertIn('Monthly total ceiling is GBP 1800.',events)
        self.assertEqual(second['pending_requests'],{})
        store.verify()

    def test_host_write_rejects_model_symlink_and_hardlink(self):
        target=self.base/'target.json';target.write_text('{}')
        link=self.base/'link.json';link.symlink_to(target)
        with self.assertRaises(ValueError):ca.write(link,{'overwrite':True})
        import os
        hard=self.base/'hard.json';os.link(target,hard)
        with self.assertRaises(ValueError):ca.write(hard,{'overwrite':True})
        self.assertEqual(target.read_text(),'{}')

    def test_failing_check_cannot_be_approved_or_original_review_overwritten(self):
        folder=self.base/'a/turn-01';folder.mkdir(parents=True)
        ca.write(folder/'result.json',{'accepted':False})
        with self.assertRaisesRegex(ValueError,'failed'):ca.review(self.base,'a',1,True,'Looks pleasant')
        ca.review(self.base,'a',1,False,'The numeric condition failed.')
        with self.assertRaisesRegex(ValueError,'original'):ca.review(self.base,'a',1,False,'Replace')

    def test_gate_blocks_unknown_usage_in_other_case(self):
        for key in ('transport','a','b','c'):(self.base/key).mkdir()
        def recover(path):
            return {'blocked':False,'unknown_usage_call_ids':['t01'] if path.parent.name=='b' else [],'dispatched_calls':0}
        with patch.object(ca.continuity,'recover',side_effect=recover):
            with self.assertRaisesRegex(ValueError,'unknown usage'):ca.dispatch_gate(self.base)

    def test_unmaterialized_physical_result_blocks_dispatch(self):
        for key in ('transport','a','b','c'):(self.base/key).mkdir()
        with patch.object(ca.continuity,'recover',return_value={'blocked':False,'unknown_usage_call_ids':[],'dispatched_calls':1}):
            with self.assertRaisesRegex(ValueError,'counts differ'):ca.dispatch_gate(self.base)

    def test_review_is_bound_to_result_and_counter_stop_is_global(self):
        for key in ('transport','a','b','c'):(self.base/key).mkdir()
        folder=self.base/'a/turn-01';folder.mkdir()
        physical=self.base/'a/session/calls/t01';physical.mkdir(parents=True)
        def recover(path):
            active=path.parent.name=='a'
            return {'blocked':False,'unknown_usage_call_ids':[],'dispatched_calls':int(active),
                'thread_uuid':'01234567-89ab-4cde-8fab-0123456789ab' if active else None,
                'calls':[{'turn_id':'t01','status':'complete','record_dir':str(physical)}] if active else []}
        ca.write(folder/'request.json',{'case_id':'a','turn':1,'prompt':'Exact synthetic prompt.'})
        result={'case_id':'a','turn':1,'accepted':True,'record':{'status':'complete',
            'request_sha256':ca._digest({'turn_id':'t01','prompt':'Exact synthetic prompt.'}),
            'direct_terminal_usage':{'input_tokens':7999900,'output_tokens':100}}}
        ca.write(physical/'result.json',result['record'])
        ca.write(folder/'result.json',result)
        ca.review(self.base,'a',1,True,'All actual outputs checked.')
        with patch.object(ca.continuity,'recover',side_effect=recover):
            with self.assertRaisesRegex(ValueError,'stop reached'):ca.dispatch_gate(self.base)
            result['accepted']=False
            ca.write(folder/'result.json',result)
            with self.assertRaisesRegex(ValueError,'result changed'):ca.dispatch_gate(self.base)


if __name__=='__main__':unittest.main()
