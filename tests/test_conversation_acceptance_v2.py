"""V2 allocation and frozen-parent gates using only synthetic local processes."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'bench'), str(ROOT / 'skills/vet-flat/scripts')]
import conversation_acceptance as ca
from call_control import CallControlPaused
from test_conversation_acceptance import fixture

USAGE = {'input_tokens': 13, 'cached_input_tokens': 3, 'output_tokens': 4}
PARENT_COUNTS = [('transport', 2), ('a', 6), ('b', 3)]


class AcceptanceV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.parent = self.base / 'parent-v1'
        self.output = self.base / 'study-v2'
        self.runtime = self.base / 'fake-codex'
        self.runtime.write_text('synthetic offline executable')
        self.runtime.chmod(0o700)
        identity = {'path': str(self.runtime), 'sha256': ca.continuity._file_hash(self.runtime),
                    'version': 'codex-cli offline-test'}
        runtime_patch = patch.object(ca.continuity, '_runtime_identity', return_value=identity)
        runtime_patch.start()
        self.addCleanup(runtime_patch.stop)
        self.actual_start = ca.native.launch.start_process
        self.commands = []
        self.v1_fixtures = self.write_fixtures('v1-cases.json', 6)
        self.v2_fixtures = self.write_fixtures('v2-cases.json', 5)
        self.stop_path = self.parent / 'v1-stop.json'
        self.amendment_path = self.base / 'v2-amendment.json'

    def write_fixtures(self, name, count):
        path = self.base / name
        path.write_text(json.dumps([{'id': key, 'turns': [fixture(n) for n in range(1, count + 1)]}
                                    for key in 'abc']))
        return path

    def fake_start(self, command, **kwargs):
        self.commands.append(copy.deepcopy(command))
        answer = command[command.index('--output-last-message') + 1]
        thread = str(uuid.uuid5(uuid.NAMESPACE_URL, str(Path(kwargs['cwd']).resolve())))
        script = '''import hashlib,json,sys
from pathlib import Path
sys.stdin.read()
def read(name): return json.loads(Path(name).read_text())
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
if Path('constraints.json').exists():
    constraints,evidence=read('constraints.json'),read('evidence.json')
    binding={'revision':constraints['revision'],'constraints_sha256':digest(constraints),'evidence_sha256':digest(evidence)}
    recommendation={'schema_version':'vet-flat/eligibility-recommendation/1','binding':binding,
        'first_choice':'demo','ranking':[{'candidate_id':'demo','status':'needs_evidence',
        'open_requirement_ids':['budget'],'exception_ids':[]}],'backups':[],'blocked':[],'not_selected':[],
        'todos':[{'id':'verify-demo','candidate_id':'demo','action':'investigate','requirement_ids':['budget'],'binding':binding}]}
    Path('recommendation.json').write_text(json.dumps(recommendation))
    Path('comparison.md').write_text('Fictional demo has an estimate below the ceiling; actual cost is unconfirmed.')
    Path('next-steps.md').write_text('Verify the fictional option monthly total before promoting it.')
else:
    Path('note.txt').write_text('violet teacup 583 continued')
Path(sys.argv[1]).write_text('Synthetic local result: violet teacup 583')
'''
        terminal_usage = dict(getattr(self, 'next_usage', USAGE),
                              cache_write_input_tokens=0, reasoning_output_tokens=2)
        events = [{'type': 'thread.started', 'thread_id': thread},
                  {'type': 'turn.completed', 'usage': terminal_usage}]
        script += '\n'.join('print(' + repr(json.dumps(event)) + ',flush=True)' for event in events)
        return self.actual_start([sys.executable, '-B', '-c', script, answer], **kwargs)

    def run_turn(self, output, case, approve=True):
        with patch.object(ca.native.launch, 'start_process', side_effect=self.fake_start):
            result = ca.run_one(output, case)
        self.assertTrue(result['structural_checks_passed'], result)
        ca.review(output, case, result['turn'], approve, 'Reviewed synthetic fake-process artifacts.')
        return result

    def build_parent(self, source_mismatch=False):
        ca.prepare(self.parent, self.v1_fixtures)
        for case, count in PARENT_COUNTS:
            for _ in range(count):
                self.run_turn(self.parent, case)
        if source_mismatch:
            plan = ca.read(self.parent / 'plan.json')
            plan['source_sha256']['bench/conversation_acceptance.py'] = '0' * 64
            ca.write(self.parent / 'plan.json', plan)
            ca.write(self.parent / 'frozen.json', {'plan_sha256': ca._digest(plan)})
        self.write_stop_and_amendment()

    def write_stop_and_amendment(self):
        rows = []
        for case, count in PARENT_COUNTS:
            for turn in range(1, count + 1):
                rows.append(dict(USAGE, case=case, turn=turn))
        ca.write(self.stop_path, {
            'status': 'stopped_for_shared_evidence_scope_defect',
            'physical_calls': 11, 'raw_counter_sum': 187, 'usage_scope_qualified': False,
            'rows': rows, 'unexecuted_core': ['b4', 'b5', 'b6'] + ['c%d' % n for n in range(1, 7)],
            'remaining_global_call_slots': 15,
            'original_source_commit': ca.read(self.parent / 'plan.json')['source_commit']})
        ca.write(self.amendment_path, {
            'version': 2, 'parent_stop_sha256': ca.sha(self.stop_path),
            'parent_physical_calls': 11, 'new_call_slots': 15, 'global_max_calls': 26,
            'raw_counter_stop': 8000000, 'reallocated_unexecuted_core': 9,
            'reallocated_reserved': 6,
            'reason': 'Synthetic correction for explicit evidence scope; no model calls in this test.'})

    def prepare_v2(self):
        return ca.prepare_v2(self.output, self.v2_fixtures, self.parent, self.amendment_path)

    def parent_bytes(self):
        return {str(path.relative_to(self.parent)): path.read_bytes()
                for path in self.parent.rglob('*') if path.is_file()}

    def assert_v2_gate(self, calls, counter):
        gate = ca.dispatch_gate(self.output)
        self.assertEqual(calls, gate['recorded_calls'])
        self.assertEqual(counter, gate['summed_raw_counter'])
        self.assertEqual(11, gate['parent_recorded_calls'])
        self.assertEqual(calls - 11, gate['new_recorded_calls'])
        self.assertEqual(26 - calls, gate['remaining_global_calls'])

    def test_v2_first_turn_needs_no_transport_and_fresh_owned_uuid(self):
        self.build_parent()
        before = self.parent_bytes()
        with patch.object(ca.native.launch, 'start_process') as start:
            result = self.prepare_v2()
            start.assert_not_called()
        self.assertEqual(0, result['model_calls'])
        self.assertFalse((self.output / 'transport').exists())
        self.assert_v2_gate(11, 187)
        for case in 'abc':
            plan, _ = ca.continuity._read_envelope(self.output / case / 'session/plan.json')
            self.assertEqual(['t%02d' % n for n in range(1, 6)], plan['turn_ids'])
        self.run_turn(self.output, 'a')
        self.assertNotIn('resume', self.commands[-1])
        old = ca.continuity.recover(self.parent / 'a/session')['thread_uuid']
        new = ca.continuity.recover(self.output / 'a/session')['thread_uuid']
        self.assertNotEqual(old, new)
        self.assert_v2_gate(12, 204)
        self.run_turn(self.output, 'a')
        self.assertEqual([new, '-'], self.commands[-1][-2:])
        self.assertEqual(before, self.parent_bytes())

    def test_fifteen_new_turns_hit_shared_twenty_six_call_ceiling(self):
        self.build_parent()
        self.prepare_v2()
        for case in 'abc':
            for _ in range(5):
                self.run_turn(self.output, case)
            if case != 'c':
                with patch.object(ca.native.launch, 'start_process') as start:
                    with self.assertRaisesRegex(ValueError, 'complete'):
                        ca.run_one(self.output, case)
                    start.assert_not_called()
        self.assertEqual(26, len(self.commands))
        with patch.object(ca.native.launch, 'start_process') as start:
            with self.assertRaisesRegex(ValueError, 'stop|ceiling|exhaust'):
                ca.dispatch_gate(self.output)
            with self.assertRaises(ValueError):
                ca.run_one(self.output, 'c')
            with self.assertRaises(ValueError):
                ca.run_one(self.output, 'transport')
            start.assert_not_called()

    def test_parent_source_mismatch_is_historical_and_parent_is_read_only(self):
        self.build_parent(source_mismatch=True)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            ca.verify_plan(self.parent)
        before = self.parent_bytes()
        self.prepare_v2()
        self.assertEqual(11, ca.dispatch_gate(self.output)['recorded_calls'])
        self.assertEqual(before, self.parent_bytes())

    def test_raw_counter_stop_includes_frozen_parent_usage(self):
        self.build_parent()
        self.prepare_v2()
        self.next_usage = dict(USAGE, input_tokens=7999809)
        self.run_turn(self.output, 'a')
        self.assertEqual(12, len(self.commands))
        with patch.object(ca.native.launch, 'start_process') as start:
            with self.assertRaisesRegex(ValueError, 'stop'):
                ca.dispatch_gate(self.output)
            with self.assertRaisesRegex(ValueError, 'stop'):
                ca.run_one(self.output, 'b')
            start.assert_not_called()

    def test_amendment_must_authorize_exact_remaining_allocation(self):
        self.build_parent()
        original = ca.read(self.amendment_path)
        changes = {'new_call_slots': 16, 'global_max_calls': 27, 'raw_counter_stop': 8000001,
                   'parent_physical_calls': 10, 'reallocated_unexecuted_core': 8,
                   'reallocated_reserved': 7, 'parent_stop_sha256': '0' * 64, 'reason': ' '}
        for field, value in changes.items():
            ca.write(self.amendment_path, dict(original, **{field: value}))
            with self.subTest(field=field), patch.object(ca.native.launch, 'start_process') as start:
                with self.assertRaises(ValueError):
                    self.prepare_v2()
                start.assert_not_called()
                self.assertFalse(self.output.exists())
        ca.write(self.amendment_path, original)
        self.prepare_v2()
        self.assertEqual(11, ca.dispatch_gate(self.output)['recorded_calls'])

    def test_external_explicit_stop_receipt_is_frozen_without_parent_writes(self):
        self.build_parent()
        external = self.base / 'v1-stop.json'
        self.stop_path.rename(external)
        before = self.parent_bytes()
        original = external.read_bytes()
        ca.prepare_v2(self.output, self.v2_fixtures, self.parent, self.amendment_path,
                      parent_stop_path=external)
        self.assertEqual(11, ca.dispatch_gate(self.output)['recorded_calls'])
        self.assertEqual(before, self.parent_bytes())
        self.assertEqual(original, external.read_bytes())
        external.write_bytes(original + b'\n')
        with patch.object(ca.native.launch, 'start_process') as start:
            with self.assertRaises(ValueError):
                ca.run_one(self.output, 'a')
            start.assert_not_called()

    def test_parent_stop_or_raw_artifact_change_blocks_before_new_dispatch(self):
        self.build_parent()
        self.prepare_v2()
        targets = [self.stop_path, self.parent / 'b/session/calls/t03/native-stdout.jsonl']
        for target in targets:
            original = target.read_bytes()
            target.write_bytes(original + b'\n')
            try:
                with self.subTest(path=str(target)), patch.object(ca.native.launch, 'start_process') as start:
                    with self.assertRaises(ValueError):
                        ca.run_one(self.output, 'a')
                    start.assert_not_called()
            finally:
                target.write_bytes(original)
        self.assertEqual(11, ca.dispatch_gate(self.output)['recorded_calls'])

    def test_parent_added_durable_call_blocks_before_new_dispatch(self):
        self.build_parent()
        self.prepare_v2()
        home = self.parent / 'b'
        folder = home / 'turn-04'
        folder.mkdir()
        turn = fixture(4)
        packet = ca.release(home, turn, 4)
        prompt = 'Additional synthetic parent turn after the parent was frozen.'
        ca.write(folder / 'request.json', {'case_id': 'b', 'turn': 4, 'prompt': prompt})
        with patch.object(ca.native.launch, 'start_process', side_effect=self.fake_start):
            record = ca.continuity.invoke({'turn_id': 't04', 'prompt': prompt},
                                         home / 'session/calls/t04', home / 'work', home / 'session')
        self.assertTrue(ca.finish_turn(home, folder, 'b', 4, record, turn, packet)['structural_checks_passed'])
        ca.review(self.parent, 'b', 4, True, 'Synthetic extra-call rejection test.')
        with patch.object(ca.native.launch, 'start_process') as start:
            with self.assertRaises(ValueError):
                ca.run_one(self.output, 'a')
            start.assert_not_called()

    def test_unknown_parent_usage_cannot_create_a_v2_allocation(self):
        ca.prepare(self.parent, self.v1_fixtures)
        for case, count in [('transport', 2), ('a', 6), ('b', 2)]:
            for _ in range(count):
                self.run_turn(self.parent, case)
        self.next_usage = {'input_tokens': 13, 'cached_input_tokens': 3}
        with patch.object(ca.native.launch, 'start_process', side_effect=self.fake_start):
            with self.assertRaises(CallControlPaused):
                ca.run_one(self.parent, 'b')
        self.write_stop_and_amendment()
        before = self.parent_bytes()
        with patch.object(ca.native.launch, 'start_process') as start:
            with self.assertRaises(ValueError):
                self.prepare_v2()
            start.assert_not_called()
        self.assertEqual(before, self.parent_bytes())
        self.assertFalse(self.output.exists())

    def test_v1_default_allocation_stays_six_core_and_two_transport_turns(self):
        result = ca.prepare(self.parent, self.v1_fixtures)
        self.assertEqual((18, 2, 0), (result['core_calls'], result['qualification_calls'], result['model_calls']))
        for case, count in [('transport', 2), ('a', 6), ('b', 6), ('c', 6)]:
            plan, _ = ca.continuity._read_envelope(self.parent / case / 'session/plan.json')
            self.assertEqual(count, len(plan['turn_ids']))
        with self.assertRaisesRegex(ValueError, 'six|6'):
            ca.validate_cases(ca.read(self.v2_fixtures))
        self.assertEqual([], self.commands)


if __name__ == '__main__':
    unittest.main()
