"""Offline, private inspection and append-only reviews of selected lab calls.

Reading never invokes recovery, models, network, or project-state writes. Hashes
bind retained evidence, not source truth or answer quality. Hidden reasoning is
excluded. Reviews are caller-labelled human/agent opinions, not authenticated
identities or changes to conversation history, requirements, or quality verdicts.
Python 3.9 standard library; UI/server callers own session access authorization.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid
from session_runner import _input_files, _manifest_tool_policy
from playground_settings import validate as _validate_execution_settings, unknown as _unknown_execution_settings

VERSION = 2
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_BODY_CHARS = 16000
MAX_TOOLS = 200
MAX_REVIEWS = 1000
MAX_CALLS = 1000
MAX_EXPORT_BYTES = 16 * 1024 * 1024
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')
TAGS = {'missed_question', 'condition_loss', 'unsupported_claim', 'process_jargon',
        'no_progress', 'tool_failure', 'cost'}
RATINGS = {'helpful', 'needs_work', 'problem', 'unrated'}
SEVERITIES = {'none', 'low', 'medium', 'high'}
METRICS = ('input_tokens', 'cached_input_tokens', 'uncached_input_tokens',
           'output_tokens', 'processed_tokens', 'seconds')
HIDDEN = {'reasoning', 'thinking', 'analysis', 'agent_message', 'error'}
REVIEW_FIELDS = ('client_id', 'call_id', 'reviewer', 'rating', 'severity', 'tags', 'note')
EXPECTED_SOURCE_FIELDS = ('record_sha256', 'message_sha256', 'displayed_sha256')


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError('invalid call identifier')
    return value


def _path(folder, relative=''):
    root = Path(folder).absolute()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('unsafe evidence path')
    path = root / rel
    for ancestor in (path,) + tuple(path.parents):
        if ancestor.is_symlink():
            raise ValueError('symlink evidence path is not allowed')
    if not root.is_dir():
        raise ValueError('missing session folder')
    return path


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


class _ObjectPairs(list):
    """Keep object keys intact when classifying a rejected telemetry line."""


def _unambiguous_item_envelope(line):
    """Identify a non-terminal envelope without accepting its nested payload.

    Some CLI web-search items repeat an item ID key. That remains an integrity
    gap, but cannot hide another terminal event if the outer object is unique
    and explicitly an item event. Syntax errors, nonfinite numbers and duplicate
    outer keys are never recoverable through this classification.
    """
    try:
        pairs = json.loads(line, object_pairs_hook=_ObjectPairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
        if not isinstance(pairs, _ObjectPairs):
            return False
        envelope = _pairs(pairs)
        return (set(envelope) == {'type', 'item'}
                and envelope.get('type') in ('item.started', 'item.updated', 'item.completed')
                and isinstance(envelope.get('item'), _ObjectPairs))
    except (ValueError, TypeError):
        return False


def _read(folder, relative):
    path = _path(folder, relative)
    descriptor = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_ARTIFACT_BYTES:
            raise ValueError('evidence is not a bounded regular file')
        data = stream.read(MAX_ARTIFACT_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_ARTIFACT_BYTES or (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('evidence changed while reading')
    return json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))


def _envelope(folder, relative, key='value', hash_key='sha256'):
    value = _read(folder, relative)
    if (not isinstance(value, dict) or not isinstance(value.get(key), dict)
            or value.get(hash_key) != _digest(value[key])):
        raise ValueError('checksum mismatch')
    return value[key]


def _block(value, source_path, note=None):
    if value is None:
        return {'text': '', 'total_chars': 0, 'truncated': False, 'sha256': None,
                'source_path': source_path, 'available': False, 'note': note}
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    return {'text': text[:MAX_BODY_CHARS], 'total_chars': len(text),
            'truncated': len(text) > MAX_BODY_CHARS,
            'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'source_path': source_path, 'available': True, 'note': note}


def _calls(session):
    rows = session.get('calls')
    if not isinstance(rows, list) or len(rows) > MAX_CALLS:
        raise ValueError('invalid or oversized session call list')
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('invalid session call row')
    ids = [_identifier(row.get('id')) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate session call identifier')
    return rows


def _tools(events, source_path):
    groups = {}
    for n, event in enumerate(events):
        if not isinstance(event, dict) or event.get('type') not in ('item.started', 'item.updated', 'item.completed'):
            continue
        item = event.get('item')
        if not isinstance(item, dict) or item.get('type') in HIDDEN:
            continue
        # Missing IDs are separate observations; never invent one shared execution.
        key = item.get('id') if isinstance(item.get('id'), str) and item['id'] else '@event-%d' % n
        group = groups.setdefault(key, {'id': key, 'event_count': 0, 'item': {}, 'completed': False})
        group['event_count'] += 1
        if event['type'] == 'item.completed':
            for field in ('aggregated_output', 'output', 'result', 'stdout', 'stderr', 'content', 'error', 'exit_code'):
                group['item'].pop(field, None)
            group['item']['status'] = 'completed'
        if event['type'] == 'item.completed' or not group['completed']:
            group['item'].update(item)
        if event['type'] == 'item.completed':
            group['completed'] = True
    result = []
    for group in groups.values():
        item = group['item']
        failed = (item.get('status') in ('failed', 'error') or bool(item.get('error'))
                  or (type(item.get('exit_code')) is int and item['exit_code'] != 0))
        input_value = {k: item[k] for k in ('command', 'query', 'queries', 'action', 'arguments', 'input', 'url') if k in item}
        output = {k: item[k] for k in ('aggregated_output', 'output', 'result', 'stdout', 'stderr', 'content', 'error', 'exit_code') if k in item}
        result.append({'id': group['id'], 'type': item.get('type', 'unknown'),
                       'status': 'failed' if failed else item.get('status', 'completed' if group['completed'] else 'incomplete'),
                       'event_count': group['event_count'], 'failed': failed,
                       'input': _block(input_value, source_path), 'output': _block(output, source_path),
                       'raw': _block(item, source_path), 'source_path': source_path,
                       'source_claims_verified': False})
    return result


def _usage(record, binding, gaps):
    result = dict.fromkeys(METRICS)
    if not binding or not isinstance(record, dict):
        return result
    launch_result = record.get('launch_result')
    if not isinstance(launch_result, dict):
        gaps.append('missing launch result; direct usage cannot be checked against raw telemetry')
        return result
    seconds = launch_result.get('seconds')
    if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0:
        result['seconds'] = seconds
    else:
        gaps.append('missing or malformed launch duration')
    raw = launch_result.get('stdout')
    if not isinstance(raw, str) or not raw.strip():
        gaps.append('missing raw stdout; usage is unknown')
        return result
    terminals, malformed = [], False
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON number')))
            if not isinstance(event, dict):
                raise ValueError('non-object event')
            if event.get('type') == 'turn.completed':
                terminals.append(event.get('usage'))
        except (ValueError, TypeError):
            if _unambiguous_item_envelope(line):
                gaps.append('raw non-terminal item payload has duplicate JSON keys at stdout line %d; '
                            'tool identity/content is ambiguous; terminal counters checked separately' % line_number)
            else:
                malformed = True
    usage = record.get('direct_terminal_usage')
    fields = ('input_tokens', 'cached_input_tokens', 'output_tokens')
    valid = (not malformed and len(terminals) == 1
             and type(record.get('terminal_usage_events')) is int and record['terminal_usage_events'] == 1
             and isinstance(usage, dict) and isinstance(terminals[0], dict))
    if not valid:
        gaps.append('missing, malformed, or inconsistent direct terminal usage; tokens are unknown')
        return result
    if any(usage.get(k) is not None and terminals[0].get(k) is not None
           and usage[k] != terminals[0][k] for k in fields):
        gaps.append('raw and saved terminal counters conflict; tokens are unknown')
        return result
    for key in fields:
        saved, raw_value = usage.get(key), terminals[0].get(key)
        if type(saved) is int and saved >= 0 and type(raw_value) is int and raw_value == saved:
            result[key] = saved
        else:
            gaps.append('missing or inconsistent ' + key + '; this counter is unknown')
    incoming, cached, outgoing = (result[k] for k in fields)
    if incoming is not None and cached is not None:
        if cached <= incoming:
            result['uncached_input_tokens'] = incoming - cached
        else:
            gaps.append('cached input exceeds inclusive input; cached counter is invalid')
            result['cached_input_tokens'] = None
    if incoming is not None and outgoing is not None:
        result['processed_tokens'] = incoming + outgoing
        total = terminals[0].get('total_tokens')
        if 'total_tokens' in terminals[0] and (type(total) is not int or total != result['processed_tokens']):
            gaps.append('raw total conflicts with direct input/output; tokens are unknown')
            result.update({k: None for k in METRICS if k != 'seconds'})

    return result


def _displayed(session, row, raw_reply):
    messages = [m for m in session.get('messages', []) if isinstance(m, dict)
                and m.get('role') == row.get('actor') and isinstance(m.get('text'), str)]
    anchored = [m for m in messages if m.get('call_id') == row['id'] or m.get('acceptance_id') == row['id']]
    if len(anchored) == 1:
        return anchored[0], 'explicit message/call anchor'
    if len(anchored) > 1:
        return None, 'ambiguous message/call anchors'
    projection = None
    if isinstance(raw_reply, str):
        try:
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict) and isinstance(parsed.get('message'), str):
                projection = parsed['message']
        except ValueError:
            pass
    matches = [m for m in messages if m['text'] == raw_reply
               or (projection is not None and m.get('display_text') == projection)]
    if len(matches) == 1:
        return matches[0], 'unique exact content match; no stored call anchor'
    return None, 'displayed-message association unavailable or ambiguous; raw actor reply remains available'


def _questions(value):
    if not isinstance(value, list) or len(value) > 3:
        raise ValueError('displayed questions must contain at most three questions')
    for row in value:
        if not isinstance(row, dict) or set(row) != {'question', 'options'}:
            raise ValueError('invalid displayed question fields')
        question, options = row['question'], row['options']
        if not isinstance(question, str) or not question.strip() or len(question) > 240:
            raise ValueError('invalid displayed question text')
        if (not isinstance(options, list) or not 2 <= len(options) <= 4
                or any(not isinstance(o, str) or not o.strip() or len(o) > 160 for o in options)
                or len(set(options)) != len(options)):
            raise ValueError('invalid displayed question options')
    return json.loads(_bytes(value))  # Do not expose mutable session objects.


def _display_snapshot(session, row, raw_reply, gaps):
    message, relation = _displayed(session, row, raw_reply)
    text = message.get('display_text', message['text']) if message else None
    if text is not None and not isinstance(text, str):
        gaps.append('invalid displayed reply text')
        text = None
    questions, status = None, 'missing'
    note = 'No retained questions field; choices are not inferred from actor output.'
    if message is not None and 'questions' in message:
        try:
            questions = _questions(message['questions'])
            status, note = 'present', 'Exact saved visible questions and option order.'
        except ValueError as exc:
            status, note = 'invalid', str(exc)
            gaps.append(note)
    question_block = {'available': status == 'present', 'items': questions,
                      'sha256': _digest(questions) if questions is not None else None,
                      'total_chars': len(_bytes(questions).decode('utf-8')) if questions is not None else None,
                      'truncated': False, 'source_path': 'session.messages.questions', 'note': note,
                      'status': status}
    combined = (_digest({'text': text, 'questions': questions, 'questions_status': status})
                if text is not None and status != 'invalid' else None)
    return {'reply': _block(text, 'session.messages', relation),
            'questions': question_block, 'relation': relation, 'sha256': combined}


def _inspect(folder, session, row, detail):
    call_id = row['id']
    base = '.pea-state/runs/' + call_id
    gaps = []
    manifest, record, record_hash, binding = None, None, None, True
    request_binding, files, files_present, files_valid = False, [], False, True
    settings, settings_present, settings_valid = _unknown_execution_settings(), False, True
    receipt = row.get('receipt')
    reply = receipt.get('answer') if isinstance(receipt, dict) else None
    reply_path = 'session.calls[%s].receipt.answer' % call_id
    try:
        manifest = _envelope(folder, base + '/manifest.json')
        request = manifest['request']
        settings_present = 'execution_settings' in request
        if settings_present:
            try:
                settings = _validate_execution_settings(request['execution_settings'])
            except (ValueError, TypeError):
                settings_valid = False
                raise ValueError('invalid execution settings metadata')
        files_present = 'input_files' in request
        if files_present:
            try:
                if request['input_files'] is None:
                    raise ValueError('saved input_files must be a list')
                files = _input_files(request['input_files'])
            except (ValueError, TypeError):
                files_valid = False
                raise ValueError('invalid input file metadata')
        version = manifest.get('version')
        policy = _manifest_tool_policy(manifest)
        if (type(version) is not int or version not in (1, 2) or manifest['id'] != call_id
                or _digest(request) != manifest['request_hash']
                or request['packet_revision'] != manifest['packet']['revision']
                or request['packet_event_hash'] != manifest['packet']['event_hash']
                or policy not in ('text_only', 'live_research')
                or (version == 1 and ('tool_policy' in request or 'tool_policy' in manifest))
                or (version == 2 and request.get('tool_policy') != policy)):
            raise ValueError('manifest request/context binding differs')
        physical = _envelope(folder, base + '/physical/run.json')
        if (type(physical.get('version')) is not int or physical['version'] != 1
                or physical.get('planned_call_ids') != ['answer']
                or physical.get('config') != {'project_step': manifest['request_hash']}
                or physical.get('allow_tools') is not (policy == 'live_research')
                or physical.get('allow_claude') is not False):
            raise ValueError('physical run/manifest binding differs')
        saved_request = _envelope(folder, base + '/physical/requests/' + hashlib.sha256(b'answer').hexdigest() + '.json')
        if saved_request != {'call_id': 'answer', 'family': 'codex', 'request': request}:
            raise ValueError('physical request differs from manifest')
        request_binding = True
    except (OSError, ValueError, KeyError, TypeError) as exc:
        gaps.append('request evidence: ' + str(exc))
        binding = False
    record_path = base + '/physical/control/checkpoint.json'
    try:
        state = _envelope(folder, record_path, 'state', 'state_sha256')
        if (type(state.get('version')) is not int or state['version'] != 1
                or state.get('planned_call_ids') != ['answer']
                or set(state.get('calls', {})) != {'answer'}
                or not isinstance(manifest, dict)
                or state.get('allow_tools') is not (manifest.get('tool_policy', 'text_only') == 'live_research')):
            raise ValueError('physical call ledger is pending or differs')
        saved = state['calls']['answer']
        record = saved['record']
        if not isinstance(record, dict) or _digest(record) != saved['record_sha256']:
            raise ValueError('record checksum differs or call is unresolved')
        record_hash = saved['record_sha256']
        if (not isinstance(manifest, dict) or saved.get('call_id') != 'answer'
                or record.get('id') != 'answer' or saved.get('job_id') != manifest.get('task_id')
                or saved.get('role') != 'agent' or saved.get('phase') != 'project_step'
                or record.get('project_request_hash') != manifest.get('request_hash')):
            raise ValueError('physical record/manifest binding differs')
        if (not isinstance(receipt, dict) or receipt.get('id') != call_id
                or receipt.get('record_sha256') != record_hash
                or receipt.get('answer') != record.get('answer', '')
                or receipt.get('physical_status') != ('failed' if saved.get('failure_kind') else 'complete')):
            raise ValueError('saved session receipt/record binding differs')
        disk_receipt = _read(folder, base + '/receipt.json')
        if (not isinstance(disk_receipt, dict) or any(disk_receipt.get(k) != receipt.get(k)
                for k in ('id', 'record_sha256', 'answer', 'processed_tokens', 'physical_status'))):
            raise ValueError('disk receipt/session receipt binding differs')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        gaps.append('result evidence: ' + str(exc))
        binding = False
    if not isinstance(reply, str):
        reply = record.get('answer') if isinstance(record, dict) and isinstance(record.get('answer'), str) else None
        reply_path = record_path + '#state.calls.answer.record.answer'
    if reply is None:
        # Only explicit message/call anchors are usable; positional alignment is ambiguous.
        messages = [m for m in session.get('messages', []) if isinstance(m, dict)
                    and (m.get('call_id') == call_id or m.get('acceptance_id') == call_id)
                    and isinstance(m.get('text'), str)]
        if len(messages) == 1:
            reply = messages[0]['text']
            reply_path = 'session.messages[explicit call anchor]'
    usage = _usage(record, binding, gaps)
    if binding and isinstance(receipt, dict) and usage['processed_tokens'] is not None and receipt.get('processed_tokens') != usage['processed_tokens']:
        gaps.append('receipt token amount differs from raw telemetry')
        usage = dict.fromkeys(METRICS)
        binding = False
    events = record.get('tool_events') if binding and isinstance(record, dict) else None
    if events is not None and not isinstance(events, list):
        gaps.append('malformed retained tool event list')
        events = None
    filtered, tool_shape_ok = [], True
    for event in events or []:
        if (not isinstance(event, dict) or not isinstance(event.get('item'), dict)
                or not isinstance(event['item'].get('type'), str)
                or event.get('type') not in ('item.started', 'item.updated', 'item.completed')):
            tool_shape_ok = False
            continue
        if event['item']['type'] not in HIDDEN:
            if not isinstance(event['item'].get('id'), str) or not event['item']['id']:
                tool_shape_ok = False
            filtered.append(event)
    if not tool_shape_ok:
        gaps.append('malformed tool observations; invocation count is unknown')
    tools = _tools(filtered, record_path + '#state.calls.answer.record.tool_events')
    message_hash = hashlib.sha256(reply.encode('utf-8')).hexdigest() if reply is not None else None
    request = manifest.get('request') if isinstance(manifest, dict) else None
    request = request if isinstance(request, dict) else {}
    displayed = _display_snapshot(session, row, reply, gaps)
    settings_bound = settings_present and settings_valid and request_binding and binding
    settings_status = ('not_recorded' if not settings_present and request_binding else
                       'invalid' if not settings_valid else 'bound' if settings_bound else 'unbound')
    result = {'call_id': call_id, 'actor': row.get('actor'), 'status': row.get('status', 'unknown'),
              'model': request.get('model'),
              'execution_settings': settings if settings_bound else _unknown_execution_settings(),
              'execution_settings_evidence': {
                  'status': settings_status,
                  'request_sha256': manifest.get('request_hash') if settings_bound else None,
                  'source_path': base + '/manifest.json#value.request.execution_settings',
                  'note': ('These settings are bound to this saved physical-call request; they do not independently prove provider application.' if settings_bound else
                           'This saved request did not record execution settings; current session values and call-row labels are not substituted.' if settings_status == 'not_recorded' else
                           'Execution settings cannot be verified for this call; current session values and call-row labels are not substituted.')},
              'integrity': {'ok': not gaps, 'gaps': gaps}, 'usage': usage,
              'tool_invocation_count': len(tools) if events is not None and tool_shape_ok else None,
              'tool_failed_count': sum(t['failed'] for t in tools) if events is not None and tool_shape_ok else None,
              'source': {'record_sha256': record_hash if binding else None,
                         'message_sha256': message_hash, 'record_path': record_path,
                         'displayed_sha256': displayed['sha256']},
              'quality': 'not_evaluated', 'source_claims_verified': False}
    if detail:
        prompt = request.get('prompt')
        current = None
        if isinstance(prompt, str) and '\n\nCURRENT INPUT TO ANSWER\n' in prompt:
            current = prompt.rsplit('\n\nCURRENT INPUT TO ANSWER\n', 1)[1]
            for marker in ('\n\nAnswer the current input', '\n\nThe tester has changed', '\n\nHOST CHECKED-DELIVERY CONTRACT'):
                current = current.split(marker, 1)[0]
        result.update(prompt=_block(prompt, base + '/manifest.json#value.request.prompt'),
                      input_files={'status': ('not_recorded' if not files_present and request_binding else
                                              'invalid' if not files_valid else
                                              'bound' if request_binding else 'unbound'),
                                   'items': files,
                                   'request_sha256': manifest.get('request_hash') if request_binding else None,
                                   'source_path': base + '/manifest.json#value.request.input_files',
                                   'note': 'Binding status concerns saved supplied metadata only, not proof of delivery, file contents or model reading. image=true marks the current image handoff; false does not mean the file was absent from prior turns.'},
                      current_input=_block(current, base + '/manifest.json#value.request.prompt',
                                           'Extracted prompt span; full prompt is authoritative. No explicit marker means unavailable.'),
                      reply=_block(reply, reply_path, 'Retained reply; integrity or quality failure does not erase it.'),
                      tools=tools[:MAX_TOOLS], tools_truncated=len(tools) > MAX_TOOLS,
                      raw_tool_events=_block(filtered if events is not None else None,
                                             record_path + '#state.calls.answer.record.tool_events',
                                             'Filtered tool events only; hidden reasoning omitted. Completion is not source verification.'))
        result['raw_actor_reply'] = result['reply']
        result['displayed_reply'] = displayed['reply']
        result['displayed_questions'] = displayed['questions']
        result['displayed_reply_relation'] = displayed['relation']
    return result


def build_call(session_folder, session_dict, call_id):
    """Inspect one explicitly selected call, with bounded bodies and no writes."""
    _path(session_folder)
    _identifier(call_id)
    row = next((r for r in _calls(session_dict) if r['id'] == call_id), None)
    if row is None:
        raise ValueError('call does not belong to this session')
    return dict(version=VERSION, session_id=session_dict.get('id'),
                **_inspect(session_folder, session_dict, row, True))


def build_index(session_folder, session_dict):
    """Compact archive index; unknown totals remain null, with known subtotals."""
    _path(session_folder)
    calls = [_inspect(session_folder, session_dict, row, False) for row in _calls(session_dict)]
    totals = {}
    for metric in METRICS + ('tool_invocation_count',):
        values = [r['usage'][metric] if metric in METRICS else r[metric] for r in calls]
        known = sum(v for v in values if v is not None)
        unknown = sum(v is None for v in values)
        totals[metric] = {'value': known if not unknown else None, 'known_sum': known, 'unknown_calls': unknown}
    return {'version': VERSION, 'session_id': session_dict.get('id'), 'calls': calls,
            'totals': totals, 'gaps': [{'call_id': r['call_id'], 'gaps': r['integrity']['gaps']}
                                     for r in calls if r['integrity']['gaps']]}


def _payload(payload):
    required = set(REVIEW_FIELDS)
    if not isinstance(payload, dict) or not required.issubset(payload) or set(payload) - required - {'expected_source'}:
        raise ValueError('invalid review fields')
    value = dict(payload)
    try:
        if str(uuid.UUID(value['client_id'])) != value['client_id']:
            raise ValueError('noncanonical UUID')
    except (ValueError, TypeError, AttributeError):
        raise ValueError('client_id must be a canonical UUID')
    _identifier(value['call_id'])
    if (any(not isinstance(value[k], str) for k in ('reviewer', 'rating', 'severity'))
            or value['reviewer'] not in ('human', 'agent') or value['rating'] not in RATINGS or value['severity'] not in SEVERITIES):
        raise ValueError('invalid review classification')
    if (not isinstance(value['note'], str) or len(value['note']) > 4000
            or not isinstance(value['tags'], list) or len(value['tags']) > len(TAGS)
            or any(not isinstance(tag, str) or tag not in TAGS for tag in value['tags'])
            or len(set(value['tags'])) != len(value['tags'])):
        raise ValueError('invalid review note or tags')
    value['tags'] = sorted(value['tags'])
    if 'expected_source' in value:
        expected = value['expected_source']
        if (not isinstance(expected, dict) or set(expected) != set(EXPECTED_SOURCE_FIELDS)
                or any(v is not None and (not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v))
                       for v in expected.values())):
            raise ValueError('expected_source requires the three exact preview hashes (or null)')
        value['expected_source'] = dict(expected)
    return value


def _check_display_snapshot(snapshot, source):
    if not isinstance(snapshot, dict) or snapshot.get('sha256') != source.get('displayed_sha256'):
        raise ValueError('displayed review snapshot/pin differs')
    reply, questions = snapshot.get('reply'), snapshot.get('questions')
    if not isinstance(reply, dict) or not isinstance(questions, dict) or not isinstance(snapshot.get('relation'), str):
        raise ValueError('invalid displayed review snapshot')
    text, length = reply.get('text'), reply.get('total_chars')
    if (not isinstance(text, str) or len(text) > MAX_BODY_CHARS or type(length) is not int
            or length < len(text) or reply.get('truncated') is not (length > len(text))):
        raise ValueError('invalid bounded displayed reply')
    if reply.get('available') is True:
        if not isinstance(reply.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', reply['sha256']):
            raise ValueError('missing full displayed text hash')
        if not reply['truncated'] and hashlib.sha256(text.encode('utf-8')).hexdigest() != reply['sha256']:
            raise ValueError('displayed text snapshot/hash differs')
    elif text or length or reply.get('sha256') is not None:
        raise ValueError('unavailable displayed text contains data')
    status = questions.get('status')
    if status == 'present':
        items = _questions(questions.get('items'))
        if questions.get('available') is not True or questions.get('sha256') != _digest(items):
            raise ValueError('displayed questions snapshot/hash differs')
    elif status not in ('missing', 'invalid') or questions.get('items') is not None or questions.get('available') is not False:
        raise ValueError('invalid missing displayed questions')
    else:
        items = None
    if reply.get('available') and status != 'invalid':
        if not isinstance(snapshot['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', snapshot['sha256']):
            raise ValueError('missing full displayed content hash')
        if not reply['truncated'] and snapshot['sha256'] != _digest({'text': text, 'questions': items, 'questions_status': status}):
            raise ValueError('displayed content snapshot/hash differs')
    elif snapshot['sha256'] is not None:
        raise ValueError('unavailable display cannot have a complete pin')


def read_reviews(folder):
    """Read verified append-only notes; corruption is explicit and prevents append."""
    directory = _path(folder, 'review-notes')
    if not directory.exists():
        return {'version': VERSION, 'reviews': [], 'gaps': []}
    if not directory.is_dir():
        return {'version': VERSION, 'reviews': [], 'gaps': ['review-notes is not a directory']}
    reviews, gaps, previous, clients = [], [], None, set()
    names = sorted(p.name for p in directory.iterdir() if p.name != '.lock')
    if len(names) > MAX_REVIEWS:
        return {'version': VERSION, 'reviews': [], 'gaps': ['review history exceeds limit']}
    for n, name in enumerate(names, 1):
        try:
            if not re.fullmatch(r'[0-9]{6}-[0-9a-f-]{36}\.json', name):
                raise ValueError('unexpected review artifact')
            review = _envelope(folder, 'review-notes/' + name)
            payload = _payload({k: review[k] for k in REVIEW_FIELDS + ('expected_source',) if k in review})
            if (type(review.get('version')) is not int or review['version'] not in (1, VERSION) or review.get('sequence') != n
                    or review.get('previous_sha256') != previous or review['client_id'] in clients
                    or name != '%06d-%s.json' % (n, review['client_id'])
                    or any(review[k] != v for k, v in payload.items())):
                raise ValueError('review history identity/chain differs')
            if not isinstance(review.get('source'), dict) or not any(review['source'].get(k) for k in ('record_sha256', 'message_sha256')):
                raise ValueError('review has no retained evidence pin')
            if 'expected_source' in payload and any(review['source'].get(k) != v for k, v in payload['expected_source'].items()):
                raise ValueError('saved review differs from its inspected source')
            if review['version'] == VERSION:
                _check_display_snapshot(review.get('displayed_snapshot'), review['source'])
            previous = _digest(review)
            clients.add(review['client_id'])
            reviews.append(review)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            gaps.append(name + ': ' + str(exc))
            break
    return {'version': VERSION, 'reviews': reviews, 'gaps': gaps}


@contextmanager
def _review_lock(folder):
    directory = _path(folder, 'review-notes')
    directory.mkdir(exist_ok=True, mode=0o700)
    path = _path(folder, 'review-notes/.lock')
    descriptor = os.open(str(path), os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(descriptor, 'a+b') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
            raise ValueError('invalid review lock')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield directory
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def save_review(folder, session, payload):
    """Append one immutable opinion; exact UUID retries return its original pin.

    Optional payload.expected_source contains exactly record_sha256,
    message_sha256 and displayed_sha256 from build_call.source, including nulls.
    A new write rejects changed preview evidence. An identical UUID retry returns
    the saved opinion before inspecting current evidence. Older clients may omit
    expected_source and retain their original save-time binding behavior.
    """
    value = _payload(payload)
    _path(folder)
    if value['call_id'] not in {r['id'] for r in _calls(session)}:
        raise ValueError('review call does not belong to this session')
    with _review_lock(folder) as directory:
        history = read_reviews(folder)
        if history['gaps']:
            raise ValueError('review history integrity failure; no append')
        for review in history['reviews']:
            if review['session_id'] != session.get('id'):
                raise ValueError('review history belongs to another session')
            if review['client_id'] == value['client_id']:
                saved_payload = {k: review[k] for k in REVIEW_FIELDS + ('expected_source',) if k in review}
                if saved_payload != value:
                    raise ValueError('review client_id conflicts with saved content')
                return {'ok': True, 'created': False, 'review': review}
        if len(history['reviews']) >= MAX_REVIEWS:
            raise ValueError('review history ceiling reached')
        detail = build_call(folder, session, value['call_id'])
        source = detail['source']
        if 'expected_source' in value and any(source.get(k) != v for k, v in value['expected_source'].items()):
            raise ValueError('review preview changed; inspect the current call before saving')
        if not source['record_sha256'] and not source['message_sha256']:
            raise ValueError('call has no retained record or message to review yet')
        review = dict(value, version=VERSION, sequence=len(history['reviews']) + 1,
                      session_id=session.get('id'), created_at=datetime.now(timezone.utc).isoformat(),
                      previous_sha256=_digest(history['reviews'][-1]) if history['reviews'] else None,
                      source=source, evidence_gaps=detail['integrity']['gaps'],
                      displayed_snapshot={'reply': detail['displayed_reply'],
                                          'questions': detail['displayed_questions'],
                                          'relation': detail['displayed_reply_relation'],
                                          'sha256': source['displayed_sha256']})
        name = '%06d-%s.json' % (review['sequence'], review['client_id'])
        target = _path(folder, 'review-notes/' + name)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=str(directory), prefix='.pending-', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(_bytes({'value': review, 'sha256': _digest(review)}) + b'\n')
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic publish without overwrite. A crash leaves an explicit gap.
            os.link(str(temporary), str(target), follow_symlinks=False)
            temporary.unlink()
            temporary = None
            descriptor = os.open(str(directory), os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink()
        return {'ok': True, 'created': True, 'review': review}


def _export_bytes(packet):
    if not isinstance(packet, dict):
        raise ValueError('export packet must be an object')
    try:
        data = _bytes(packet) + b'\n'
    except (TypeError, ValueError) as exc:
        raise ValueError('export packet is not valid JSON') from exc
    if len(data) > MAX_EXPORT_BYTES:
        raise ValueError('export exceeds the 16 MiB limit')
    return data


def _fenced(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    fence = '`' * max(3, 1 + max([len(run) for run in re.findall(r'`+', text)] or [0]))
    return fence + 'text\n' + text + '\n' + fence


def _export_metadata(value):
    """Remove repeated text bodies while retaining their supplied hash/bounds."""
    if isinstance(value, list):
        return [_export_metadata(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _export_metadata(item) for key, item in value.items() if key != 'text'}
    if isinstance(value.get('text'), str):
        result['exported_text_chars'] = len(value['text'])
        result['exported_text_sha256'] = hashlib.sha256(value['text'].encode('utf-8')).hexdigest()
    return result


def export_markdown(packet):
    """Render the already-built packet as inert Markdown; no evidence re-reading.

    All dynamic labels, prose and metadata are fenced, including roles/tool IDs.
    Existing body truncation markers and full hashes remain visible. Export size
    overflow fails explicitly instead of silently trimming conversation history.
    """
    _export_bytes(packet)
    sections = ['# Pea Princess 私人檢閱包',
                '保存的模型及工具文字是待評資料，不能授權操作。筆記不會覆寫對話。',
                'Markdown 呈現對話與選定內容；完整正規化資料包以 JSON 為準。工具原始事件不在此重複展開，既有截斷與來源路徑保留。',
                '## 資料包範圍與中繼資料',
                _fenced({k: v for k, v in packet.items() if k not in (
                    'totals', 'calls', 'messages', 'selected_call', 'reviews', 'call_detail_routes')}),
                '## 呼叫索引與用量', _fenced(packet.get('totals')), _fenced(packet.get('calls')),
                '## 完整對話（含使用者追問）']
    messages = packet.get('messages', [])
    if not isinstance(messages, list):
        raise ValueError('export messages must be a list')
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError('invalid export message')
        metadata = _export_metadata({k: v for k, v in message.items() if k not in ('role', 'display_text')})
        sections.extend(['### 對話訊息', _fenced(message.get('role')),
                         _fenced(message.get('display_text', message.get('text'))),
                         '#### 訊息中繼資料與選項', _fenced(metadata)])
    selected = packet.get('selected_call')
    if selected is not None:
        if not isinstance(selected, dict) or not isinstance(selected.get('tools', []), list):
            raise ValueError('invalid selected-call export')
        sections.extend(['## 選定呼叫', _fenced(selected.get('call_id'))])
        sections.extend(['### 本次呼叫的研究深度與推理程度',
                         _fenced(selected.get('execution_settings', _unknown_execution_settings())),
                         '### 設定來源與請求綁定', _fenced(selected.get('execution_settings_evidence'))])
        for key, label in (('raw_actor_reply', '原始模型輸出'), ('current_input', '當輪輸入'),
                           ('prompt', '送給模型的完整提示（或明示截斷）'),
                           ('input_files', '提供給這次呼叫的附件收據（不代表模型已讀取）'),
                           ('displayed_reply', '畫面回覆'), ('displayed_questions', '畫面選項')):
            block = selected.get(key, selected.get('reply') if key == 'raw_actor_reply' else None)
            sections.extend(['### ' + label, _fenced(block.get('text') if isinstance(block, dict) and 'text' in block else block)])
        for tool in selected.get('tools', []):
            if not isinstance(tool, dict):
                raise ValueError('invalid exported tool observation')
            sections.extend(['### 工具執行', _fenced({'id': tool.get('id'), 'type': tool.get('type')}),
                             _fenced(tool.get('input', {}).get('text') if isinstance(tool.get('input'), dict) else tool.get('input')),
                             _fenced(tool.get('output', {}).get('text') if isinstance(tool.get('output'), dict) else tool.get('output'))])
        metadata = _export_metadata(selected)
        if isinstance(metadata.get('displayed_questions'), dict):
            metadata['displayed_questions'].pop('items', None)
        sections.extend(['### 選定呼叫中繼資料（關聯、雜湊、截斷、完整性及原始事件路徑）', _fenced(metadata)])
    sections.extend(['## 評閱筆記', _fenced(packet.get('reviews')),
                     '## 其他呼叫的詳細紀錄路徑', _fenced(packet.get('call_detail_routes'))])
    result = '\n\n'.join(sections) + '\n'
    if len(result.encode('utf-8')) > MAX_EXPORT_BYTES:
        raise ValueError('Markdown export exceeds the 16 MiB limit')
    return result


def save_export(folder, packet, format):
    """Save one fresh private JSON/Markdown artifact from an existing packet.

    No models, downloads, content paths, or evidence readers are used. The caller
    receives the absolute local path and exact file digest only after fsync.
    """
    if not isinstance(format, str) or format not in ('json', 'md'):
        raise ValueError('export format must be json or md')
    data = _export_bytes(packet) if format == 'json' else export_markdown(packet).encode('utf-8')
    directory = _path(folder, 'review-exports')
    directory.mkdir(exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    target = _path(folder, 'review-exports/' + str(uuid.uuid4()) + '.' + format)
    try:
        descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    except FileExistsError as exc:
        raise ValueError('export filename already exists; nothing was overwritten') from exc
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(str(directory), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {'path': str(target), 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'format': format}
