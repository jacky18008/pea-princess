"""Owned acceptance crash/receipt recovery with synthetic fake processes only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'bench'),str(ROOT/'skills/vet-flat/scripts')]
import conversation_acceptance as ca
from test_conversation_acceptance import fixture

THREAD = '01234567-89ab-4cde-8fab-0123456789ab'
USAGE = {'input_tokens':13,'cached_input_tokens':3,'output_tokens':4}


class AcceptanceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.output = self.base/'study'
        source = self.base/'cases.json'
        source.write_text(json.dumps([{'id':k,'turns':[fixture(n) for n in range(1,7)]} for k in 'abc']))
        runtime = self.base/'fake-codex'; runtime.write_text('offline fake'); runtime.chmod(0o700)
        identity = {'path':str(runtime),'sha256':ca.continuity._file_hash(runtime),'version':'codex-cli offline-test'}
        with patch.object(ca.continuity,'_runtime_identity',return_value=identity):
            ca.prepare(self.output,source)
        self.actual_start = ca.native.launch.start_process
        self.commands = []

    def fake_start(self, command, **kwargs):
        self.commands.append(copy.deepcopy(command))
        answer = command[command.index('--output-last-message')+1]
        script = '''import json,sys
from pathlib import Path
sys.stdin.read()
Path('note.txt').write_text('violet teacup 583 continued')
Path(sys.argv[1]).write_text('violet teacup 583')
'''
        script += 'print('+repr(json.dumps({'type':'thread.started','thread_id':THREAD}))+',flush=True)\n'
        script += 'print('+repr(json.dumps({'type':'turn.completed','usage':USAGE}))+',flush=True)\n'
        return self.actual_start([sys.executable,'-c',script,answer],**kwargs)

    def run_transport(self):
        with patch.object(ca.native.launch,'start_process',side_effect=self.fake_start):
            return ca.run_one(self.output,'transport')

    def crash_after_physical(self):
        with patch.object(ca,'finish_turn',side_effect=OSError('synthetic post-commit crash')):
            with self.assertRaisesRegex(OSError,'post-commit'):
                self.run_transport()
        self.assertEqual(1,len(self.commands))

    def test_completed_physical_call_recovers_without_launch_then_exact_resume(self):
        self.crash_after_physical()
        with self.assertRaisesRegex(ValueError,'counts differ'):
            ca.dispatch_gate(self.output)
        with patch.object(ca.native.launch,'start_process') as start:
            result = ca.recover_turn(self.output,'transport',1)
            self.assertTrue(result['structural_checks_passed']); self.assertEqual(0,result['model_calls'])
            start.assert_not_called()
        with self.assertRaisesRegex(ValueError,'root review'):
            ca.dispatch_gate(self.output)
        ca.review(self.output,'transport',1,True,'Verified exact owned transport output.')
        self.assertEqual({'recorded_calls':1,'summed_raw_counter':17},ca.dispatch_gate(self.output))
        result = self.run_transport()
        self.assertTrue(result['structural_checks_passed'])
        self.assertEqual([THREAD,'-'],self.commands[-1][-2:])
        self.assertEqual(2,len(self.commands))

    def test_changed_review_usage_or_saved_prompt_cannot_replace_physical_receipt(self):
        self.run_transport()
        folder = self.output/'transport/turn-01'
        original = ca.read(folder/'result.json'); altered = copy.deepcopy(original)
        altered['record']['direct_terminal_usage']['input_tokens'] = 0
        ca.write(folder/'result.json',altered)
        with self.assertRaisesRegex(ValueError,'exact owned physical'):
            ca.dispatch_gate(self.output)
        with patch.object(ca.native.launch,'start_process') as start:
            with self.assertRaisesRegex(ValueError,'exact owned physical'):
                ca.recover_turn(self.output,'transport',1)
            start.assert_not_called()
        ca.write(folder/'result.json',original)
        request = ca.read(folder/'request.json'); request['prompt'] += ' altered'
        ca.write(folder/'request.json',request)
        with self.assertRaisesRegex(ValueError,'saved user request differs'):
            ca.dispatch_gate(self.output)

    def test_native_uuid_cannot_be_shared_by_separate_owned_cases(self):
        self.run_transport()
        home = self.output/'a'; folder = home/'turn-01'; folder.mkdir()
        prompt = 'Only a synthetic fake-process test.'
        ca.write(folder/'request.json',{'case_id':'a','turn':1,'prompt':prompt})
        with patch.object(ca.native.launch,'start_process',side_effect=self.fake_start):
            record = ca.continuity.invoke({'turn_id':'t01','prompt':prompt},home/'session/calls/t01',home/'work',home/'session')
        ca.write(folder/'result.json',{'case_id':'a','turn':1,'record':record,'accepted':False})
        with self.assertRaisesRegex(ValueError,'UUID is shared'):
            ca.dispatch_gate(self.output)

    def test_changed_workspace_after_crash_retains_spend_but_cannot_pass(self):
        self.crash_after_physical()
        (self.output/'transport/work/note.txt').write_text('Changed after physical completion')
        with patch.object(ca.native.launch,'start_process') as start:
            result = ca.recover_turn(self.output,'transport',1)
            start.assert_not_called()
        self.assertFalse(result['structural_checks_passed'])
        self.assertIn('recovery is ambiguous',result['checks']['failure'])
        saved = ca.read(self.output/'transport/turn-01/result.json')
        self.assertEqual(USAGE,saved['record']['direct_terminal_usage'])
        with self.assertRaisesRegex(ValueError,'failed'):
            ca.review(self.output,'transport',1,True,'Should fail.')

    def test_partial_archive_repair_and_saved_review_remain_record_only(self):
        self.crash_after_physical()
        folder = self.output/'transport/turn-01'
        archive = folder/'workspace'; archive.mkdir()
        (archive/'note.txt').write_bytes((self.output/'transport/work/note.txt').read_bytes())
        with patch.object(ca.native.launch,'start_process') as start:
            self.assertTrue(ca.recover_turn(self.output,'transport',1)['structural_checks_passed'])
            ca.review(self.output,'transport',1,True,'Actual saved output checked.')
            result_bytes = (folder/'result.json').read_bytes()
            review_bytes = (folder/'review.json').read_bytes()
            result = ca.recover_turn(self.output,'transport',1)
            self.assertTrue(result['preserved_saved_result'])
            self.assertEqual(result_bytes,(folder/'result.json').read_bytes())
            self.assertEqual(review_bytes,(folder/'review.json').read_bytes())
            start.assert_not_called()

    def test_protected_host_files_and_skill_deletions_fail_and_archive_readable_outcome(self):
        home = self.output/'a'; folder = home/'turn-test'; folder.mkdir()
        before = ca.native._snapshot(home/'work')
        for name in ('source-notes.md','current-request.json','skill/SKILL.md'):
            with self.subTest(name=name):
                target = home/'work'/name; previous = target.read_bytes(); target.unlink()
                record = {'status':'complete','workspace_before':before,'workspace_after':ca.native._snapshot(home/'work'),
                          'direct_terminal_usage':USAGE}
                result = ca.finish_turn(home,folder,'a',1,record,fixture())
                self.assertFalse(result['structural_checks_passed'])
                self.assertIn('protected authoritative',result['checks']['failure'])
                target.write_bytes(previous)
        self.assertTrue((folder/'workspace/constraints.json').is_file())

    def test_unresolved_native_call_cannot_be_recovered_or_retried(self):
        with patch.object(ca.continuity,'recover',return_value={'blocked':True}), \
             patch.object(ca.native.launch,'start_process') as start:
            with self.assertRaisesRegex(ValueError,'unresolved'):
                ca.recover_turn(self.output,'transport',1)
            start.assert_not_called()


if __name__ == '__main__': unittest.main()
