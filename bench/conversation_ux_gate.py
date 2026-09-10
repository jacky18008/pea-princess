#!/usr/bin/env python3
"""Validate evidence coverage and reduce independent UX judgments, offline.

Python 3.9+, standard library only. This does not semantically grade replies.
The controller supplies an ordered, complete visibility projection and keeps full
raw traces separately. CLI prints one JSON object, never invokes a model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

RUBRIC_PATH = Path(__file__).resolve().parents[1] / 'evals/conversation-acceptance/ux-gate-v1.json'
RUBRIC = json.loads(RUBRIC_PATH.read_text(encoding='utf-8'))
TURN_GATES = tuple(RUBRIC['turn_gates'])
SESSION_GATES = tuple(RUBRIC['session_gates'])


class GateError(ValueError):
    """A malformed or unsupported acceptance record, not a low UX score."""


def loads(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise GateError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise GateError('non-finite JSON value: ' + value)
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (TypeError, json.JSONDecodeError) as error:
        raise GateError('invalid JSON') from error


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise GateError(label + ': unexpected or missing fields')


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise GateError(label + ': nonempty text required')


def packet_digest(packet):
    """Bind grading to the exact canonical projection, including event order."""
    raw = json.dumps(packet, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def validate_packet(packet):
    _keys(packet, ('schema_version', 'session_id', 'user_kind', 'turns'), 'packet')
    if type(packet['schema_version']) is not int or packet['schema_version'] != 1:
        raise GateError('unsupported packet schema')
    _text(packet['session_id'], 'session_id')
    if packet['user_kind'] not in ('human', 'scripted', 'model', 'mixed', 'unknown'):
        raise GateError('unsupported user_kind')
    if not isinstance(packet['turns'], list) or not packet['turns']:
        raise GateError('packet needs turns')
    tids, mids = set(), set()
    for turn in packet['turns']:
        _keys(turn, ('turn_id', 'trace_complete', 'messages'), 'turn')
        _text(turn['turn_id'], 'turn_id')
        if turn['turn_id'] in tids:
            raise GateError('duplicate turn_id')
        tids.add(turn['turn_id'])
        if type(turn['trace_complete']) is not bool or not isinstance(turn['messages'], list):
            raise GateError('turn needs explicit trace completeness and ordered messages')
        for message in turn['messages']:
            _keys(message, ('id', 'role', 'channel', 'visible', 'content'), 'message')
            _text(message['id'], 'message.id')
            if message['id'] in mids:
                raise GateError('duplicate message ID')
            mids.add(message['id'])
            if message['role'] not in ('user', 'assistant', 'tool'):
                raise GateError('unsupported message role')
            _text(message['channel'], 'message.channel')
            if type(message['visible']) is not bool or not isinstance(message['content'], str):
                raise GateError('message needs explicit visibility and text')
    return packet


def first_visible_message(turn):
    """Use saved event order, not channel preference or final-message length."""
    return next((message for message in turn['messages']
                 if message['role'] == 'assistant' and message['visible']
                 and message['content'].strip()), None)


def _gate(value, messages, label, allow_na=False):
    _keys(value, ('status', 'reason', 'evidence'), label)
    if value['status'] not in RUBRIC['statuses']:
        raise GateError(label + ': invalid status')
    if value['status'] == 'not_applicable' and not allow_na:
        raise GateError(label + ': this gate is applicable')
    _text(value['reason'], label + '.reason')
    if not isinstance(value['evidence'], list):
        raise GateError(label + ': evidence must be a list')
    if value['status'] in ('pass', 'fail') and not value['evidence']:
        raise GateError(label + ': observed judgment needs evidence')
    for evidence in value['evidence']:
        _keys(evidence, ('message_id', 'quote'), label + '.evidence')
        _text(evidence['message_id'], 'evidence.message_id')
        _text(evidence['quote'], 'evidence.quote')
        message = messages.get(evidence['message_id'])
        if message is None or not message['visible'] or evidence['quote'] not in message['content']:
            raise GateError(label + ': quote is not in an available visible message')


def _status(states):
    if 'fail' in states:
        return 'fail'
    if 'unknown' in states:
        return 'unknown'
    return 'pass'


def evaluate(packet, judgment, correctness_gates=None, task_outcome='unknown'):
    """Return separate verdicts; never create a semantic score or repair a grade.

correctness_gates is a separately established G1/G2/G3 status map. Omitting it
leaves overall acceptance unknown. This validates declared evidence, not its truth.
"""
    validate_packet(packet)
    _keys(judgment, ('schema_version', 'rubric_id', 'session_id', 'packet_sha256',
                     'turns', 'session_gates'), 'judgment')
    if type(judgment['schema_version']) is not int or judgment['schema_version'] != 1:
        raise GateError('unsupported judgment schema')
    if judgment['rubric_id'] != RUBRIC['rubric_id'] or judgment['session_id'] != packet['session_id']:
        raise GateError('wrong rubric or session')
    if judgment['packet_sha256'] != packet_digest(packet):
        raise GateError('judgment belongs to a different packet')
    if not isinstance(judgment['turns'], list):
        raise GateError('judgment needs all turns')
    wanted = [turn['turn_id'] for turn in packet['turns']]
    if [row.get('turn_id') if isinstance(row, dict) else None for row in judgment['turns']] != wanted:
        raise GateError('judgment must cover every turn exactly once in order')
    all_messages, states, openings = {}, [], []
    for turn, row in zip(packet['turns'], judgment['turns']):
        _keys(row, ('turn_id', 'opening_message_id', 'gates'), 'turn judgment')
        messages = {message['id']: message for message in turn['messages']}
        all_messages.update(messages)
        first = first_visible_message(turn)
        expected = first['id'] if first else None
        if row['opening_message_id'] != expected:
            raise GateError('opening must be the earliest visible assistant message')
        _keys(row['gates'], TURN_GATES, 'turn gates')
        for gid, value in row['gates'].items():
            _gate(value, messages, turn['turn_id'] + '.' + gid)
            states.append(value['status'])
        if first is None:
            if any(value['status'] != 'unknown' for value in row['gates'].values()):
                raise GateError('no visible answer: all turn gates must be unknown')
        elif row['gates']['O1']['status'] in ('pass', 'fail'):
            if not any(item['message_id'] == first['id'] and
                       first['content'].lstrip().startswith(item['quote'])
                       for item in row['gates']['O1']['evidence']):
                raise GateError('opening evidence must quote the start of the first visible message')
        if not turn['trace_complete']:
            states.append('unknown')
        if not any(message['role'] == 'user' and message['visible'] and message['content'].strip()
                   for message in turn['messages']):
            states.append('unknown')
        openings.append({'turn_id': turn['turn_id'], 'message_id': expected,
                         'channel': first['channel'] if first else None,
                         'text': first['content'] if first else None})
    _keys(judgment['session_gates'], SESSION_GATES, 'session gates')
    for gid, value in judgment['session_gates'].items():
        _gate(value, all_messages, gid, allow_na=len(wanted) == 1)
        if len(wanted) == 1 and value['status'] == 'pass':
            raise GateError('one turn cannot establish session-level collaboration')
        if gid == 'C2' and value['status'] in ('pass', 'fail'):
            roles = {all_messages[item['message_id']]['role'] for item in value['evidence']}
            if not {'user', 'assistant'} <= roles:
                raise GateError('user-reaction gate needs both user and assistant evidence')
        states.append(value['status'])
    ux_status = _status(states)
    if correctness_gates is None:
        correctness_gates = dict.fromkeys(('G1', 'G2', 'G3'), 'unknown')
    _keys(correctness_gates, ('G1', 'G2', 'G3'), 'correctness gates')
    if any(value not in ('pass', 'fail', 'unknown') for value in correctness_gates.values()):
        raise GateError('invalid correctness gate status')
    if task_outcome not in ('complete', 'partial', 'failed', 'unknown'):
        raise GateError('invalid task outcome')
    task_status = {'complete': 'pass', 'partial': 'fail', 'failed': 'fail', 'unknown': 'unknown'}[task_outcome]
    correctness_status = _status(list(correctness_gates.values()))
    overall = _status([ux_status, correctness_status, task_status])
    return {'schema_version': 1, 'session_id': packet['session_id'],
            'rubric_id': RUBRIC['rubric_id'], 'packet_sha256': packet_digest(packet),
            'ux_status': ux_status, 'correctness_gates': dict(correctness_gates),
            'correctness_status': correctness_status, 'task_outcome': task_outcome,
            'acceptance_status': overall, 'accepted': overall == 'pass',
            'turn_count': len(wanted), 'user_kind': packet['user_kind'],
            'openings': openings,
            'limits': 'Structure, coverage and exact quotes only; semantic judgments and trace completeness still require independent review. No satisfaction, statistical equivalence or cross-model claim.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', required=True, type=Path)
    parser.add_argument('--judgment', required=True, type=Path)
    parser.add_argument('--correctness', type=Path, help='JSON G1/G2/G3 status map')
    parser.add_argument('--task-outcome', default='unknown', choices=('complete', 'partial', 'failed', 'unknown'))
    args = parser.parse_args(argv)
    try:
        packet, judgment = (loads(path.read_text(encoding='utf-8')) for path in (args.packet, args.judgment))
        correctness = loads(args.correctness.read_text(encoding='utf-8')) if args.correctness else None
        print(json.dumps(evaluate(packet, judgment, correctness, args.task_outcome), ensure_ascii=False, sort_keys=True))
        return 0
    except (GateError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
