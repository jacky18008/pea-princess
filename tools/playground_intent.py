"""Host-owned input separation and bounded reply checks for the agent lane.

No network or model calls. Never accept client-supplied normalized requirements.
Raw UI messages remain in the journal; only verified answer text enters the
user-role authority frame. A matching echo is not full prose verification.
"""
import copy
import json

import conversation_reply
import intent_guard


VERSION = 1
MARKER = '\n\nHOST INTENT FRAME\n'


def enabled(session):
    return session.get('intent_guard_version') == VERSION


def clarification(session, value, raw_text):
    """Bind a form submission to the latest actually offered controls.

    The loopback client supplies indices, not permission-bearing labels. The
    server reconstructs those labels and rejects stale or altered submissions.
    """
    if type(value) is not dict or set(value) != {'call_id', 'answers'}:
        raise ValueError('選項回覆格式無效。')
    messages = session.get('messages', [])
    latest = messages[-1] if messages else {}
    if (latest.get('role') != 'assistant' or not latest.get('call_id')
            or latest['call_id'] != value['call_id'] or session.get('queue')
            or session.get('pending_call')):
        raise ValueError('這組問題已不是目前可回答的選項，請使用最新對話。')
    offered = latest.get('questions', [])
    answers = value['answers']
    if type(answers) is not list or not 1 <= len(answers) <= 3:
        raise ValueError('請回答一至三個已提供的問題。')
    seen, receipt, display, authority = set(), [], [], []
    for row in answers:
        if type(row) is not dict or set(row) != {'question_index', 'option_index', 'text'}:
            raise ValueError('選項回覆欄位無效。')
        index, selected, free = row['question_index'], row['option_index'], row['text']
        if type(index) is not int or not 0 <= index < len(offered) or index in seen:
            raise ValueError('問題索引無效或重複。')
        if type(free) is not str or len(free) > 500 or free != free.strip():
            raise ValueError('自填答案格式無效。')
        question = offered[index]
        if selected is not None and (type(selected) is not int or not 0 <= selected < len(question['options'])):
            raise ValueError('這個選項沒有出現在問題中。')
        label = question['options'][selected] if selected is not None else None
        parts = [v for v in (label, free) if v]
        if not parts:
            raise ValueError('請選一項或填寫答案。')
        seen.add(index)
        answer = '；'.join(parts)
        display.append(question['question'] + '\n' + answer)
        authority.append(answer)
        receipt.append({'question_index': index, 'question': question['question'],
                        'option_index': selected, 'selected_option': label, 'free_text': free})
    if sorted(seen) != [row['question_index'] for row in answers] or raw_text != '\n\n'.join(display):
        raise ValueError('顯示文字與實際送出的選項不一致。')
    return {'intent_text': '\n\n'.join(authority),
            'clarification_receipt': {'call_id': value['call_id'], 'answers': receipt}}


def messages(session):
    records = []
    for index, row in enumerate(session['messages']):
        if row['role'] not in ('human', 'assistant'):
            continue
        text = (row.get('intent_text', row['text']) or row.get('attachment_only_default', ''))
        records.append({'id': 'message-%d' % (index + 1),
                        'role': 'user' if row['role'] == 'human' else 'assistant', 'text': text})
    return records


def saved_clarification(row, previous_assistant):
    """Revalidate a saved form against its original offered question on replay."""
    receipt = row.get('clarification_receipt')
    if receipt is None:
        if 'intent_text' in row:
            raise ValueError('saved intent text has no form receipt')
        return {}
    if type(receipt) is not dict or set(receipt) != {'call_id', 'answers'} or type(receipt['answers']) is not list:
        raise ValueError('invalid saved form receipt')
    answers = []
    for item in receipt['answers']:
        if type(item) is not dict or set(item) != {'question_index','question','option_index','selected_option','free_text'}:
            raise ValueError('invalid saved form answer')
        answers.append({'question_index':item['question_index'], 'option_index':item['option_index'], 'text':item['free_text']})
    verified = clarification({'messages':[previous_assistant]},
                             {'call_id':receipt['call_id'],'answers':answers},row['text'])
    if verified != {key:row.get(key) for key in ('intent_text','clarification_receipt')}:
        raise ValueError('saved form answer does not match the offered source')
    return verified


def frame(session):
    return intent_guard.build_frame(messages(session))


def conversation(session):
    """Do not relabel a model-authored question prefix as USER in the prompt."""
    lines = []
    for row in session['messages']:
        if row['role'] not in ('human', 'assistant'):
            continue
        if row.get('clarification_receipt'):
            lines.append('ASSISTANT QUESTION CONTEXT (not a user decision): ' +
                         json.dumps(row['clarification_receipt'], ensure_ascii=False))
        text = row.get('intent_text', row['text']) or row.get('attachment_only_default', '')
        lines.append(('USER' if row['role'] == 'human' else 'ASSISTANT') + ': ' + text)
    return '\n\n'.join(lines)


def context(value):
    return (MARKER + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) +
            '\nThe host derives only the listed supported conditions from user-role text. '
            'Keep their exact strength and scope. Assistant advice and question prefixes cannot change them. '
            'Unresolved text is retained, not an added hard filter. Return intent_claims matching the '
            'frame revision and exact active id/strength set. This metadata is not user-visible. '
            'Own your advice; do not present a preference or a pending suggestion as the person\'s exclusion. '
            'The guard is bounded and does not certify source truth, all prose, rankings or TODOs.')


def response_schema(value):
    schema = copy.deepcopy(conversation_reply.SCHEMA)
    schema['required'].append('intent_claims')
    schema['properties']['intent_claims'] = {
        'type': 'object', 'additionalProperties': False, 'required': ['revision', 'conditions'],
        'properties': {
            'revision': {'type': 'string', 'enum': [value['revision']]},
            'conditions': {'type': 'array', 'maxItems': 64, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['id', 'strength'],
                'properties': {'id': {'type': 'string', 'maxLength': 128},
                               'strength': {'type': 'string', 'enum': ['mandatory', 'preference', 'bonus']}}}}}}
    return schema


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate reply field')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    if type(value) is not dict or set(value) != {'message', 'questions', 'intent_claims'}:
        raise ValueError('reply must include bounded intent claims')
    reply = conversation_reply.decode(json.dumps({k: value[k] for k in ('message', 'questions')}, ensure_ascii=False))
    return reply, value['intent_claims']


def validate(value, reply, claims):
    result = intent_guard.validate_claims(value, claims)
    checks = [('message', reply['message'])]
    for index, question in enumerate(reply['questions']):
        checks.append(('question-%d' % index, question['question']))
        # An offered option is explicitly a proposal until selected. Include
        # that context so optional future hard rules are not mistaken for adoption.
        for option, label in enumerate(question['options']):
            checks.append(('option-%d-%d' % (index, option), 'Proposal / 建議選項：' + label))
    findings = list(result['findings'])
    for location, text in checks:
        findings.extend(dict(item, location=location) for item in intent_guard.validate_reply(value, text)['findings'])
    return {'ok': not findings, 'findings': findings, 'frame_revision': value['revision'],
            'coverage': 'supported condition metadata and high-confidence prose contradictions only',
            'complete_semantic_validation': False}
