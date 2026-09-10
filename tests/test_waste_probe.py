"""Offline experiment guards; no provider calls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bench'))
import waste_probe as probe
from call_control import CallControl, CallControlPaused


def success(tokens=20):
    return {'status':'complete','terminal_usage_events':1,
            'direct_terminal_usage':{'input_tokens':tokens,'cached_input_tokens':0,'output_tokens':5},
            'answer':'synthetic answer','errors':[],'tool_events':[],'exit_code':0}


class WasteProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name).resolve()/'probe'
        # Real synthetic state creation, reduced public file bundle for speed.
        original=probe.subprocess.check_output
        def checkout(command, **kwargs):
            if command[:2]==['git','ls-files']:
                return 'skills/vet-flat/SKILL.md\n'
            return original(command, **kwargs)
        with mock.patch.object(probe.subprocess,'check_output',side_effect=checkout):
            probe.prepare(self.output)

    def control(self):
        return CallControl(self.output/'controller',[r['id'] for r in probe.layout()],allow_tools=True)

    def test_paired_inputs_identical_and_latest_instruction_preserved(self):
        states=[]
        for row in probe.layout():
            work=self.output/row['id']/'work'
            states.append(probe.native._snapshot(work))
            packet=probe.SessionStore(work).context(max_chars=32000)
            self.assertEqual(2250,packet['requirements']['monthly-total']['value'])
            self.assertEqual(probe.LATEST,probe.read(work/'conversation.json')[-1]['content'])
        self.assertTrue(all(s==states[0] for s in states))
        self.assertEqual(8,len(states))

    def test_two_calls_then_root_gate_and_no_automatic_expansion(self):
        with mock.patch.object(probe.native,'invoke',return_value=success()) as invoke:
            probe.run_one(self.output); self.assertEqual(1,invoke.call_count)
            probe.run_one(self.output); self.assertEqual(2,invoke.call_count)
            with self.assertRaisesRegex(ValueError,'canary'):
                probe.run_one(self.output)
            self.assertEqual(2,invoke.call_count)
            first,second=[c.args[0] for c in invoke.call_args_list]
            self.assertEqual(probe.COMMON,first['prompt'])
            self.assertEqual(probe.COMMON+probe.TREATMENT,second['prompt'])
            self.assertTrue(first['skip_host_skill_discovery'])
            self.assertNotIn('tool_output_token_limit',second)

    def test_failed_or_pending_dispatch_cannot_be_retried(self):
        with mock.patch.object(probe.native,'invoke',return_value={'status':'stopped','direct_terminal_usage':None}) as invoke:
            with self.assertRaises(CallControlPaused): probe.run_one(self.output)
            with self.assertRaisesRegex(ValueError,'pending/failed'): probe.run_one(self.output)
            self.assertEqual(1,invoke.call_count)
        self.assertEqual(1,self.control().report()['dispatched_calls'])

    def test_cost_limit_stops_before_next_call_without_calling_usage_zero(self):
        with mock.patch.object(probe.native,'invoke',return_value=success(probe.LIMIT)) as invoke:
            probe.run_one(self.output)
            with self.assertRaisesRegex(ValueError,'token stop'): probe.run_one(self.output)
            self.assertEqual(1,invoke.call_count)

    def test_fixture_plan_and_source_tampering_fail_before_dispatch(self):
        with mock.patch.object(probe.native,'invoke') as invoke:
            with mock.patch.object(probe,'sha',return_value='changed'):
                with self.assertRaisesRegex(ValueError,'source changed'): probe.run_one(self.output)
            source=self.output/'p01/work/sources.md'; source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'fixture differs'): probe.run_one(self.output)
            plan=probe.read(self.output/'plan.json'); plan['max_calls']=999
            probe.write(self.output/'plan.json',plan)
            with self.assertRaisesRegex(ValueError,'frozen plan'): probe.run_one(self.output)
            invoke.assert_not_called()


if __name__=='__main__': unittest.main()
