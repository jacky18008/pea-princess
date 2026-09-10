"""Offline acceptance evidence/aggregation tests; no lexical style classifier."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_ux_gate as gate


def fixture():
    packet = {'schema_version': 1, 'session_id': 'synthetic', 'user_kind': 'scripted', 'turns': []}
    for n in (1, 2):
        packet['turns'].append({'turn_id': 't%d' % n, 'trace_complete': True, 'messages': [
            {'id': 'u%d' % n, 'role': 'user', 'channel': 'message', 'visible': True,
             'content': 'Compare the stated tradeoffs.' if n == 1 else 'Prioritize the shorter journey.'},
            {'id': 'h%d' % n, 'role': 'assistant', 'channel': 'analysis', 'visible': False,
             'content': 'Private placeholder; never shown.'},
            {'id': 'p%d' % n, 'role': 'assistant', 'channel': 'commentary', 'visible': True,
             'content': 'The stated options trade space for travel time. I will check the supplied figures.'},
            {'id': 'a%d' % n, 'role': 'assistant', 'channel': 'final', 'visible': True,
             'content': 'The closer option reduces the stated journey; the larger option gives more room.'}
        ]})
    judgment = {'schema_version': 1, 'rubric_id': gate.RUBRIC['rubric_id'],
                'session_id': packet['session_id'], 'packet_sha256': gate.packet_digest(packet),
                'turns': [], 'session_gates': {}}
    for turn in packet['turns']:
        first = gate.first_visible_message(turn)
        row = {'turn_id': turn['turn_id'], 'opening_message_id': first['id'], 'gates': {}}
        for gid in gate.TURN_GATES:
            row['gates'][gid] = {'status': 'pass', 'reason': 'Synthetic evaluator assertion for reducer testing.',
                                 'evidence': [{'message_id': first['id'],
                                               'quote': 'The stated options trade space for travel time.'}]}
        judgment['turns'].append(row)
    for gid in gate.SESSION_GATES:
        judgment['session_gates'][gid] = {'status': 'pass', 'reason': 'Synthetic observation with both roles.',
            'evidence': [{'message_id': 'u2', 'quote': 'Prioritize the shorter journey.'},
                         {'message_id': 'a2', 'quote': 'The closer option reduces the stated journey;'}]}
    return packet, judgment


class UXGateTests(unittest.TestCase):
    def test_first_visible_progress_wins_over_later_final_and_hidden_message(self):
        packet, judgment = fixture()
        result = gate.evaluate(packet, judgment, dict.fromkeys(('G1', 'G2', 'G3'), 'pass'), 'complete')
        self.assertTrue(result['accepted'])
        self.assertEqual('p1', result['openings'][0]['message_id'])
        self.assertEqual('commentary', result['openings'][0]['channel'])
        judgment['turns'][0]['opening_message_id'] = 'a1'
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_later_sentence_quote_cannot_stand_in_for_opening(self):
        packet, judgment = fixture()
        judgment['turns'][0]['gates']['O1']['evidence'][0]['quote'] = 'I will check the supplied figures.'
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_ux_failure_is_veto_even_when_correctness_and_task_pass(self):
        packet, judgment = fixture()
        judgment['turns'][0]['gates']['O1']['status'] = 'fail'
        result = gate.evaluate(packet, judgment, dict.fromkeys(('G1', 'G2', 'G3'), 'pass'), 'complete')
        self.assertEqual('fail', result['ux_status'])
        self.assertEqual('pass', result['correctness_status'])
        self.assertEqual('fail', result['acceptance_status'])
        self.assertFalse(result['accepted'])

    def test_polished_ux_does_not_override_hard_condition_or_incomplete_task(self):
        packet, judgment = fixture()
        result = gate.evaluate(packet, judgment, {'G1': 'pass', 'G2': 'pass', 'G3': 'fail'}, 'complete')
        self.assertEqual('pass', result['ux_status'])
        self.assertEqual('fail', result['acceptance_status'])
        result = gate.evaluate(packet, judgment, dict.fromkeys(('G1', 'G2', 'G3'), 'pass'), 'partial')
        self.assertFalse(result['accepted'])

    def test_missing_correctness_unknown_judgment_or_incomplete_trace_never_pass(self):
        packet, judgment = fixture()
        self.assertEqual('unknown', gate.evaluate(packet, judgment)['acceptance_status'])
        judgment['turns'][1]['gates']['U2']['status'] = 'unknown'
        self.assertEqual('unknown', gate.evaluate(packet, judgment)['ux_status'])
        packet, judgment = fixture()
        packet['turns'][0]['trace_complete'] = False
        judgment['packet_sha256'] = gate.packet_digest(packet)
        self.assertEqual('unknown', gate.evaluate(packet, judgment)['ux_status'])

    def test_omitted_reordered_or_duplicate_turns_are_rejected(self):
        for mutate in (lambda rows: rows.pop(), lambda rows: rows.reverse(), lambda rows: rows.append(copy.deepcopy(rows[0]))):
            packet, judgment = fixture()
            mutate(judgment['turns'])
            with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_changed_packet_or_wrong_session_does_not_reuse_a_grade(self):
        packet, judgment = fixture()
        packet['turns'][0]['messages'][0]['content'] += ' Changed.'
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)
        packet, judgment = fixture()
        judgment['session_id'] = 'another'
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_invented_future_hidden_and_other_turn_quotes_are_rejected(self):
        for item in ({'message_id': 'a1', 'quote': 'Invented quote'},
                     {'message_id': 'future', 'quote': 'Not yet available'},
                     {'message_id': 'h1', 'quote': 'Private placeholder; never shown.'},
                     {'message_id': 'a2', 'quote': 'The closer option reduces the stated journey;'}):
            packet, judgment = fixture()
            judgment['turns'][0]['gates']['U1']['evidence'] = [item]
            with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_user_reaction_gate_requires_actual_user_and_assistant_evidence(self):
        packet, judgment = fixture()
        judgment['session_gates']['C2']['evidence'].pop(0)
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_no_visible_answer_cannot_receive_observed_pass(self):
        packet, judgment = fixture()
        packet['turns'][0]['messages'] = packet['turns'][0]['messages'][:1]
        judgment['packet_sha256'] = gate.packet_digest(packet)
        row = judgment['turns'][0]
        row['opening_message_id'] = None
        for value in row['gates'].values():
            value['status'], value['evidence'] = 'unknown', []
        self.assertEqual('unknown', gate.evaluate(packet, judgment)['ux_status'])
        row['gates']['U1'] = {'status': 'pass', 'reason': 'Claimed without output.',
                             'evidence': [{'message_id': 'u1', 'quote': 'Compare the stated tradeoffs.'}]}
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_one_turn_cannot_establish_session_quality_but_can_be_ux_checked(self):
        packet, judgment = fixture()
        packet['turns'].pop(); judgment['turns'].pop()
        judgment['packet_sha256'] = gate.packet_digest(packet)
        for value in judgment['session_gates'].values():
            value.update(status='not_applicable', reason='Only one turn observed.', evidence=[])
        self.assertEqual('pass', gate.evaluate(packet, judgment)['ux_status'])
        judgment['turns'][0]['gates']['O1']['status'] = 'not_applicable'
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)

    def test_schema_duplicate_ids_keys_missing_gates_and_implicit_visibility_rejected(self):
        with self.assertRaises(gate.GateError): gate.loads('{"a": 1, "a": 2}')
        with self.assertRaises(gate.GateError): gate.loads('{"a": NaN}')
        packet, judgment = fixture()
        packet['turns'][1]['messages'][0]['id'] = 'u1'
        with self.assertRaises(gate.GateError): gate.validate_packet(packet)
        packet, judgment = fixture()
        del judgment['turns'][0]['gates']['U3']
        with self.assertRaises(gate.GateError): gate.evaluate(packet, judgment)
        packet, judgment = fixture()
        del packet['turns'][0]['messages'][0]['visible']
        with self.assertRaises(gate.GateError): gate.validate_packet(packet)

    def test_no_text_heuristic_regrades_evaluator_and_inputs_are_immutable(self):
        packet, judgment = fixture()
        before = copy.deepcopy((packet, judgment))
        result = gate.evaluate(packet, judgment)
        self.assertEqual(before, (packet, judgment))
        self.assertEqual('pass', result['ux_status'])
        self.assertNotIn('score', result)
        self.assertNotIn('satisfaction', result)

    def test_cli_returns_one_json_record_and_invalid_input_exit_two(self):
        packet, judgment = fixture()
        with tempfile.TemporaryDirectory() as temp:
            p, j = Path(temp)/'packet.json', Path(temp)/'judgment.json'
            p.write_text(json.dumps(packet)); j.write_text(json.dumps(judgment))
            command = [sys.executable, str(ROOT/'bench/conversation_ux_gate.py'), '--packet', str(p), '--judgment', str(j)]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual('pass', json.loads(completed.stdout)['ux_status'])
            j.write_text('{"bad":true}')
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(2, completed.returncode)
            self.assertEqual('', completed.stdout)


if __name__ == '__main__': unittest.main()
