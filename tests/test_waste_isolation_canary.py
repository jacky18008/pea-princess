"""No-provider regression checks for the shared post-stop allowance."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bench'))
import waste_isolation_canary as canary
from call_control import CallControlPaused


def success(tokens=20):
    return {'status':'complete','terminal_usage_events':1,
            'direct_terminal_usage':{'input_tokens':tokens,'cached_input_tokens':0,'output_tokens':5},
            'answer':'synthetic answer','errors':[],'tool_events':[],'exit_code':0}


class CanaryBudgetTests(unittest.TestCase):
    def snapshot(self,ids,tokens=100):
        return {'calls':{sid:{'record':{'direct_terminal_usage':{'input_tokens':tokens,'output_tokens':1}},
                             'failure_kind':None} for sid in ids},'skipped':{}}

    def setUp(self):
        self.old=self.snapshot(['p%02d'%n for n in range(1,7)])
        self.old['skipped']={'p07':{},'p08':{}}

    def gate(self,current):
        return canary.combined_gate(Mock(snapshot=lambda:self.old),Mock(snapshot=lambda:current))

    def test_two_canaries_share_original_call_and_token_allowance(self):
        self.assertEqual(606,self.gate(self.snapshot([])))
        self.assertEqual(707,self.gate(self.snapshot(['q01'])))
        with self.assertRaisesRegex(ValueError,'eight-call'):self.gate(self.snapshot(['q01','q02']))
        self.old['calls']['p01']['record']['direct_terminal_usage']['input_tokens']=3000000
        with self.assertRaisesRegex(ValueError,'3M'):self.gate(self.snapshot([]))

    def test_unknown_failed_pending_and_changed_prior_all_stop(self):
        for field,value in [('failure_kind','invalid_direct_usage'),('record',None),
                            ('record',{'direct_terminal_usage':None})]:
            current=self.snapshot(['q01']); current['calls']['q01'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.gate(current)
        self.old['skipped'].pop('p08')
        with self.assertRaisesRegex(ValueError,'stopped six-call'):self.gate(self.snapshot([]))


class CanaryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.prior=self.root/'prior';self.output=self.root/'new'
        original=canary.base.subprocess.check_output
        def checkout(command, **kwargs):
            if command[:2]==['git','ls-files']:return 'skills/vet-flat/SKILL.md\n'
            return original(command, **kwargs)
        with patch.object(canary.base.subprocess,'check_output',side_effect=checkout):
            canary.base.prepare(self.prior)
            old=canary.controller(self.prior,[r['id'] for r in canary.base.layout()])
            for number in range(1,7):
                sid='p%02d'%number
                old.run(sid,sid,'answer','synthetic-prior',success)
            old.skip('p07','Stop synthetic v1.');old.skip('p08','Stop synthetic v1.')
            canary.prepare(self.output,self.prior)
        self.prior_bytes=(self.prior/'controller/checkpoint.json').read_bytes()

    def current(self):
        return canary.controller(self.output,canary.IDS)

    def test_new_reference_is_pinned_even_if_absent_from_original_plan(self):
        added='skills/vet-flat/references/state-sources-api.md'
        self.assertNotIn(added,canary.base.read(self.prior/'plan.json')['source_sha256'])
        target=self.root/'with-new-reference';original=canary.base.subprocess.check_output
        def checkout(command, **kwargs):
            if command[:2]==['git','ls-files']:return 'skills/vet-flat/SKILL.md\n'+added+'\n'
            return original(command, **kwargs)
        with patch.object(canary.base.subprocess,'check_output',side_effect=checkout):
            canary.prepare(target,self.prior)
        plan=canary.base.read(target/'plan.json')
        self.assertEqual(canary.base.sha(canary.base.ROOT/added),plan['source_sha256'][added])
        self.assertTrue((target/'q01/work/skill/references/state-sources-api.md').is_file())
        original_sha=canary.base.sha
        with patch.object(canary.base,'sha',side_effect=lambda p:'changed' if Path(p)==canary.base.ROOT/added else original_sha(p)), \
                patch.object(canary.base.native,'invoke') as physical:
            with self.assertRaisesRegex(ValueError,'canary source changed'):canary.run_one(target)
            physical.assert_not_called()

    def test_first_review_gates_second_then_combined_call_limit_stops(self):
        first_work=self.output/'q01/work';second_work=self.output/'q02/work'
        self.assertEqual(canary.base.native._snapshot(first_work),canary.base.native._snapshot(second_work))
        self.assertEqual(canary.base.LATEST,canary.base.read(first_work/'conversation.json')[-1]['content'])
        prior=canary.controller(self.prior,[r['id'] for r in canary.base.layout()])
        self.assertEqual(14,prior.snapshot()['revision'])
        def invoke(request, folder, work):
            pending=self.current().snapshot()['calls'][work.parent.name]
            self.assertIsNone(pending['record'])
            self.assertEqual(request,canary.base.read(folder/'request.json'))
            self.assertTrue(request['isolate_workspace_reads'])
            self.assertTrue(request['skip_host_skill_discovery'])
            self.assertEqual(300,request['timeout_seconds'])
            self.assertEqual('gpt-5.6-luna',request['model'])
            return success()
        with patch.object(canary.base.native,'invoke',side_effect=invoke) as physical:
            first=canary.run_one(self.output)
            self.assertEqual(('q01',150),(first['id'],first['known_combined_before']))
            with self.assertRaisesRegex(ValueError,'passing critical review'):canary.run_one(self.output)
            canary.base.write(self.output/'first-review.json',{'continue':False})
            with self.assertRaisesRegex(ValueError,'passing critical review'):canary.run_one(self.output)
            self.assertEqual(1,physical.call_count)
            canary.base.write(self.output/'first-review.json',{'continue':True})
            second=canary.run_one(self.output)
            self.assertEqual(('q02',175),(second['id'],second['known_combined_before']))
            with self.assertRaisesRegex(ValueError,'eight-call'):canary.run_one(self.output)
            self.assertEqual(2,physical.call_count)
        self.assertEqual(2,self.current().report()['dispatched_calls'])
        self.assertEqual(self.prior_bytes,(self.prior/'controller/checkpoint.json').read_bytes())

    def test_failed_first_call_survives_restart_without_retry_or_second_call(self):
        failed={'status':'stopped','direct_terminal_usage':None}
        with patch.object(canary.base.native,'invoke',return_value=failed) as physical:
            with self.assertRaises(CallControlPaused):canary.run_one(self.output)
            canary.base.write(self.output/'first-review.json',{'continue':True})
            with self.assertRaisesRegex(ValueError,'unresolved/failed'):canary.run_one(self.output)
            self.assertEqual(1,physical.call_count)
        self.assertEqual(1,self.current().report()['dispatched_calls'])
        self.assertEqual(failed,self.current().record('q01'))

    def test_pending_dispatch_and_terminal_overspend_stop_new_invocations(self):
        current=self.current();current.dispatch('q01','q01','answer','isolated-canary')
        with patch.object(canary.base.native,'invoke') as physical:
            with self.assertRaisesRegex(ValueError,'unresolved/failed'):canary.run_one(self.output)
            physical.assert_not_called()
            current.complete('q01',success(canary.base.LIMIT))
            canary.base.write(self.output/'first-review.json',{'continue':True})
            with self.assertRaisesRegex(ValueError,'3M'):canary.run_one(self.output)
            physical.assert_not_called()

    def test_plan_source_fixture_and_prior_checkpoint_pins_reject_before_dispatch(self):
        with patch.object(canary.base.native,'invoke') as physical:
            original_sha=canary.base.sha
            changed=canary.base.ROOT/'bench/waste_isolation_canary.py'
            with patch.object(canary.base,'sha',side_effect=lambda path:'changed' if Path(path)==changed else original_sha(path)):
                with self.assertRaisesRegex(ValueError,'canary source changed'):canary.run_one(self.output)
            checkpoint=self.prior/'controller/checkpoint.json'
            checkpoint.write_bytes(self.prior_bytes+b'\n')
            with self.assertRaisesRegex(ValueError,'stopped ledger changed'):canary.run_one(self.output)
            checkpoint.write_bytes(self.prior_bytes)
            fixture=self.output/'q01/work/sources.md';before=fixture.read_bytes()
            fixture.write_text('Synthetic fixture changed.')
            with self.assertRaisesRegex(ValueError,'fixture changed'):canary.run_one(self.output)
            fixture.write_bytes(before)
            plan=canary.base.read(self.output/'plan.json');plan['timeout_seconds']=301
            canary.base.write(self.output/'plan.json',plan)
            with self.assertRaisesRegex(ValueError,'frozen canary plan'):canary.run_one(self.output)
            physical.assert_not_called()
        self.assertEqual(0,self.current().report()['dispatched_calls'])


if __name__=='__main__':unittest.main()
