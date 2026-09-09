#!/usr/bin/env python3
"""Read-only aggregate of frozen native conversation experiments; no model calls.

python3 bench/conversation_report.py --run RUN --output REPORT_DIR [--overwrite]
Only aggregate JSON/Markdown are published. Raw answers, evidence quotes, prompts,
tool commands and judge reasons remain in the original private run.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

import conversation_grading as grading

FIELDS = ('input_tokens', 'cached_input_tokens', 'output_tokens')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$')
LIMITATIONS = [
    'Incomplete or unpaired observations cannot establish treatment effects; available contrasts are descriptive.',
    'One authored scenario per condition (n=1); no population equivalence, confidence intervals or real human-satisfaction claim.',
    'Entry changes bundle deduplication with procedural changes. Diagonal judge pairing can affect cross-pair score comparisons.',
    'Native tools ran in fresh ephemeral invocations with message replay and a T6 file-resume challenge; native persistent continuation/compaction was not tested.',
    'Input includes cached input. Processed tokens are input plus output, not a monetary bill or a subscription rate-limit calculation.',
    'CLI dispatches and launcher attempts are separate from underlying provider requests, whose count is unknown.',
    'Extension cost is T4–9 only; nine-turn totals also include T1–3 and must not be added to the other cost segments.',
    'First useful turn is not collected by the current rubric and remains unknown; no semantic scoring is performed here.',
    'Structural/hash validation does not establish source truth or judge correctness. No private quotations or rationale are included.',
    'Execution deadlines are explicit request/invocation settings, not elapsed time. Missing settings remain unknown; unstarted slots have no observed deadline.',
    'Deadline classifications describe observed settings and segment completeness, not identical runtime environments or causal comparability. Existing descriptive quality contrasts remain pooled unless separately analyzed.',
]


class ReportError(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReportError('duplicate JSON key')
        value[key] = item
    return value


def _parse(data):
    def invalid(_):
        raise ReportError('nonfinite JSON value')
    return json.loads(data, object_pairs_hook=_unique, parse_constant=invalid)


def _safe_root(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ReportError('parent traversal is not permitted')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ReportError('use a canonical directory without symlinks')
    if not path.is_dir():
        raise ReportError('directory does not exist')
    return path


def _read(root, relative, optional=False, limit=512 * 1024 * 1024):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ReportError('unsafe input path')
    path = root / relative
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ReportError('input parent is a symlink')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if optional:
            return None
        raise ReportError('required run artifact is missing: ' + str(relative))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ReportError('input is not a bounded regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ReportError('input exceeds size limit')
        return data
    finally:
        os.close(fd)


def _label(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ReportError('invalid condition or artifact ID')
    return value


def _number(value):
    return type(value) is int and value >= 0


def _validate_plan(plan):
    sessions, calls, pairs = {}, {}, {}
    for row in plan['sessions']:
        sid = _label(row['id'])
        if sid in sessions or row['turns'] not in (3, 9):
            raise ReportError('duplicate session or unsupported turn schedule')
        for field in ('model', 'effort', 'depth', 'arm'):
            _label(row[field])
        if row['arm'] not in ('existing-bulk', 'existing-routed', 'outcome-bulk', 'outcome-routed'):
            raise ReportError('unknown instruction arm')
        sessions[sid] = row
    for row in plan['pairs']:
        pid = _label(row['id'])
        if pid in pairs:
            raise ReportError('duplicate pair ID')
        mask = row.get('mask')
        if (not isinstance(mask, dict) or set(mask) != {'A', 'B'}
                or any(sid not in sessions for sid in mask.values()) or len(set(mask.values())) != 2):
            raise ReportError('invalid pair candidate mapping')
        pairs[pid] = row
    for row in plan['calls']:
        cid = _label(row['id'])
        if cid in calls:
            raise ReportError('duplicate call ID')
        if row['role'] == 'answer':
            if row['session'] not in sessions or type(row['turn']) is not int or not 1 <= row['turn'] <= sessions[row['session']]['turns']:
                raise ReportError('invalid answer schedule')
        elif row['role'] != 'judge' or row['pair'] not in pairs:
            raise ReportError('invalid judge schedule')
        calls[cid] = row
    for session in sessions.values():
        turns = sorted(c['turn'] for c in calls.values() if c.get('session') == session['id'])
        if turns != list(range(1, session['turns'] + 1)):
            raise ReportError('answer schedule has duplicate or missing turns')
    if Counter(c['pair'] for c in calls.values() if c['role'] == 'judge') != Counter({p: 1 for p in pairs}):
        raise ReportError('judge schedule differs from pairs')
    _label(plan['judge_model']); _label(plan['judge_effort'])
    return sessions, calls, pairs


def _totals(rows):
    dispatched = [row for row in rows if row['status'] not in ('not_dispatched', 'skipped')]
    result = {'planned_cli_invocations': len(rows), 'dispatched_cli_invocations': len(dispatched),
              'statuses': dict(sorted(Counter(row['status'] for row in rows).items())),
              'physical_provider_requests': None}
    usage = {}
    for field in FIELDS:
        values = [r['usage'][field] for r in dispatched]
        known = sum(v for v in values if v is not None)
        unknown = sum(v is None for v in values)
        usage[field] = None if unknown else known
        usage['known_' + field] = known
        usage['unknown_' + field + '_invocations'] = unknown
    usage['processed_tokens'] = None if usage['input_tokens'] is None or usage['output_tokens'] is None else usage['input_tokens'] + usage['output_tokens']
    usage['known_processed_tokens'] = usage['known_input_tokens'] + usage['known_output_tokens']
    usage['noncached_input_tokens'] = None if usage['input_tokens'] is None or usage['cached_input_tokens'] is None else usage['input_tokens'] - usage['cached_input_tokens']
    result['usage'] = usage
    for field in ('launcher_attempts', 'command_started_events', 'command_completed_events', 'completed_tool_event_records', 'tool_output_characters', 'wall_seconds'):
        values = [r[field] for r in dispatched]
        result[field] = None if any(v is None for v in values) else sum(values)
        result['known_' + field] = sum(v for v in values if v is not None)
        result['unknown_' + field + '_invocations'] = sum(v is None for v in values)
    return result


def _tool_counts(record):
    fields = ('command_started_events', 'command_completed_events', 'completed_tool_event_records', 'tool_output_characters')
    if record is None or not isinstance(record.get('tool_events'), list):
        return dict.fromkeys(fields)
    values = dict.fromkeys(fields, 0)
    for event in record['tool_events']:
        if not isinstance(event, dict) or not isinstance(event.get('item'), dict):
            return dict.fromkeys(fields)
        item = event['item']
        if event.get('type') == 'item.completed':
            values['completed_tool_event_records'] += 1
        if item.get('type') == 'command_execution':
            if event.get('type') == 'item.started':
                values['command_started_events'] += 1
            elif event.get('type') == 'item.completed':
                values['command_completed_events'] += 1
                output = item.get('aggregated_output')
                if isinstance(output, str):
                    if values['tool_output_characters'] is not None:
                        values['tool_output_characters'] += len(output)
                else:
                    values['tool_output_characters'] = None
    return values


def _deadline(request, invocation):
    """Read declared settings only; hash bindings are validated before use."""
    if invocation is not None:
        if (not isinstance(invocation, dict) or type(invocation.get('version')) is not int
                or invocation['version'] != 1 or invocation.get('request_sha256') != request['request_sha256']):
            raise ReportError('native invocation is not bound to its frozen request')
    values = {}
    for source, value in (('hashed_request', request['request']), ('invocation_receipt', invocation)):
        if value is not None and 'timeout_seconds' in value:
            deadline = value['timeout_seconds']
            if type(deadline) is not int or deadline <= 0:
                raise ReportError('execution deadline must be an explicit positive integer')
            values[source] = deadline
    if len(set(values.values())) > 1:
        raise ReportError('request and invocation execution deadlines disagree')
    return (next(iter(values.values())) if values else None,
            'hashed_request_and_invocation' if len(values) == 2 else next(iter(values), 'unknown'))


def _execution_segment(rows):
    """Retain the entire ordered vector, including missing and failed slots."""
    if not rows:
        return None  # An unplanned extension is not an incomplete experiment.
    known = sorted({r['deadline_seconds'] for r in rows if r['deadline_seconds'] is not None})
    finished = all(r['status'] == 'complete' for r in rows)
    all_known = all(r['deadline_seconds'] is not None for r in rows)
    classification = 'incomplete' if not finished or not all_known else ('same_uniform' if len(known) == 1 else 'mixed')
    return {'classification': classification, 'planned_slots': len(rows),
            'dispatched_slots': sum(r['status'] not in ('not_dispatched', 'skipped') for r in rows),
            'complete_slots': sum(r['status'] == 'complete' for r in rows),
            'outcomes_complete': finished, 'deadline_evidence_complete': all_known,
            'observed_deadline_seconds': known, 'has_mixed_observed_deadlines': len(known) > 1,
            'uniform_deadline_seconds': known[0] if classification == 'same_uniform' else None,
            'slot_ids': [r['slot_id'] for r in rows],
            'deadline_vector_seconds': [r['deadline_seconds'] for r in rows],
            'status_vector': [r['status'] for r in rows],
            'incomplete_slot_ids': [r['slot_id'] for r in rows if r['status'] != 'complete'],
            'unknown_deadline_slot_ids': [r['slot_id'] for r in rows if r['deadline_seconds'] is None]}


def _execution_policies(observations, sessions, pairs):
    by_session = {sid: sorted((r for r in observations if r['session_id'] == sid), key=lambda r: r['turn'])
                  for sid in sessions}
    segment_rows = lambda rows: {'prefix_turns_1_3': [r for r in rows if r['turn'] <= 3],
                                 'extension_turns_4_9': [r for r in rows if r['turn'] >= 4],
                                 'configured_session': rows}
    session_policies = []
    for sid, session in sessions.items():
        session_policies.append({'session_id': sid, 'configured_turns': session['turns'],
                                 'segments': {key: _execution_segment(rows)
                                              for key, rows in segment_rows(by_session[sid]).items()}})
    pair_policies = []
    for pid, pair in pairs.items():
        candidates = {label: segment_rows(by_session[sid]) for label, sid in pair['mask'].items()}
        segments = {}
        for name in ('prefix_turns_1_3', 'extension_turns_4_9', 'configured_session'):
            selected = {label: rows[name] for label, rows in candidates.items()}
            combined = _execution_segment([r for rows in selected.values() for r in rows])
            if combined is not None:
                combined['candidates'] = {label: _execution_segment(rows) for label, rows in selected.items()}
                same_length = len({len(rows) for rows in selected.values()}) == 1
                if any(not rows for rows in selected.values()) or not same_length:
                    combined['classification'] = 'incomplete'
                    combined['uniform_deadline_seconds'] = None
                combined['both_candidates_planned'] = all(bool(rows) for rows in selected.values())
                combined['candidate_turn_counts_match'] = same_length
            segments[name] = combined
        judge = next(r for r in observations if r['pair_id'] == pid)
        pair_policies.append({'pair_id': pid, 'candidate_session_ids': pair['mask'], 'segments': segments,
                              'judge_slot_id': judge['slot_id'], 'judge_deadline_seconds': judge['deadline_seconds'],
                              'judge_status': judge['status']})
    return session_policies, pair_policies


def _public_quality(judgments, plan, rubric):
    reduced = grading.summarize(judgments, plan, rubric)
    rows = []
    for row in reduced['rows']:
        rows.append({key: row[key] for key in ('session_id', 'pair_id', 'segment', 'condition', 'scores', 'quality_index',
                                             'gates', 'safe_task_success', 'task_outcome')})
    segments = {}
    for name in ('common_prefix', 'continuation'):
        selected = [r for r in rows if r['segment'] == name]
        values = [r['quality_index'] for r in selected if r['quality_index'] is not None]
        segments[name] = {'graded_sessions': len(selected),
                          'quality_index_mean': sum(values) / len(values) if values else None,
                          'quality_index_observed_sessions': len(values),
                          'safe_task_success': {'true': sum(r['safe_task_success'] is True for r in selected),
                                                'false': sum(r['safe_task_success'] is False for r in selected),
                                                'unknown': sum(r['safe_task_success'] is None for r in selected)},
                          'first_useful_turn': None,
                          'first_useful_turn_source': 'not_collected_by_current_rubric'}
    return {'reducer': 'conversation_grading.summarize', 'descriptive_only': True,
            'planned_pairs': reduced['coverage']['planned_pairs'],
            'graded_pairs': reduced['coverage']['graded_pairs'],
            'missing_pairs': len(reduced['coverage']['missing_pair_ids']),
            'segments': segments, 'condition_rows': rows,
            'descriptive_main_effects': reduced['main_effects']}


def aggregate(run):
    """Read a consistent snapshot without creating locks or rewriting progress."""
    run = _safe_root(run)
    captured = {}
    def read(relative, optional=False):
        data = _read(run, relative, optional=optional)
        captured[str(relative)] = hashlib.sha256(data).hexdigest() if data is not None else None
        if data is not None:
            return _parse(data)
        return None
    plan, frozen = read('plan.json'), read('frozen.json')
    if _digest(plan) != frozen['plan_sha256']:
        raise ReportError('frozen plan checksum differs')
    rubric = read('rubric.json')
    if captured['rubric.json'] != frozen['rubric_sha256']:
        raise ReportError('frozen rubric checksum differs')
    scenario = _read(run, 'scenario.json')  # Hash only; no conversation/scenario parsing.
    captured['scenario.json'] = hashlib.sha256(scenario).hexdigest()
    if hashlib.sha256(scenario).hexdigest() != frozen['scenario_sha256']:
        raise ReportError('frozen scenario checksum differs')
    del scenario
    sessions, calls, pairs = _validate_plan(plan)
    envelope = read('controller/checkpoint.json')
    state = envelope['state']
    if _digest(state) != envelope['state_sha256'] or state['planned_call_ids'] != list(calls):
        raise ReportError('controller checksum or schedule differs')
    ledger, usage_ledger = state['calls'], state['reducer_state']['requests']
    if set(ledger) != set(usage_ledger) or not set(ledger).issubset(calls):
        raise ReportError('controller request ledger differs')
    skipped = state.get('skipped', {})
    if not set(skipped).issubset(calls) or set(skipped) & set(ledger):
        raise ReportError('invalid skipped-call ledger')
    observations, settled, candidate_judgments = [], set(), []
    for cid, call in calls.items():
        folder = 'records/' + cid + '/'
        row = {'slot_id': cid, 'attempt_id': cid if cid in ledger else None,
               'session_id': call.get('session'), 'pair_id': call.get('pair'),
               'role': call['role'], 'status': 'skipped' if cid in skipped else 'not_dispatched',
               'usage': dict.fromkeys(FIELDS), 'launcher_attempts': None, 'wall_seconds': None,
               'deadline_seconds': None, 'deadline_source': 'unknown', 'request_sha256': None,
               'invocation_receipt_sha256': None, 'receipt_sha256': None,
               'timed_out': None, 'final_answer_present': None,
               **_tool_counts(None)}
        if call['role'] == 'answer':
            session = sessions[call['session']]
            row.update({k: session[k] for k in ('model', 'effort', 'depth', 'arm')})
            row.update(turn=call['turn'], session_turns=session['turns'])
        else:
            row.update(model=plan['judge_model'], effort=plan['judge_effort'], depth=None, arm=None)
        completion = read(folder + 'finished.json', optional=True)
        if cid in ledger:
            saved = ledger[cid]
            record = saved['record']
            if saved['call_id'] != cid or saved['role'] != call['role']:
                raise ReportError('call metadata differs from plan')
            expected_job = call.get('session', cid)
            if saved['job_id'] != expected_job:
                raise ReportError('call job identity differs')
            request = read(folder + 'request.json')
            if _digest(request['request']) != request['request_sha256'] or request['call'] != call:
                raise ReportError('frozen request differs')
            if any(request['request'].get(k) != row[k] for k in ('model', 'effort')):
                raise ReportError('invoked model/effort differs from condition')
            invocation = read(folder + 'native-invocation.json', optional=True)
            if captured[folder + 'native-invocation.json'] is not None and invocation is None:
                raise ReportError('native invocation receipt must be an object, not null')
            row['deadline_seconds'], row['deadline_source'] = _deadline(request, invocation)
            row['request_sha256'] = request['request_sha256']
            row['invocation_receipt_sha256'] = captured[folder + 'native-invocation.json']
            if record is None:
                row['status'] = 'pending'
            else:
                if _digest(record) != saved['record_sha256'] or record.get('id') != cid:
                    raise ReportError('original receipt checksum or identity differs')
                if record.get('request_sha256', request['request_sha256']) != request['request_sha256']:
                    raise ReportError('receipt request identity differs')
                row['receipt_sha256'] = saved['record_sha256']
                if type(record.get('timeout')) is bool:
                    row['timed_out'] = record['timeout']
                if isinstance(record.get('answer'), str):
                    row['final_answer_present'] = bool(record['answer'].strip())
                row['status'] = 'failed' if saved['failure_kind'] else 'complete_unsettled'
                row.update(_tool_counts(record))
                launch = record.get('launch_result', {})
                if not isinstance(launch, dict):
                    launch = {}
                if _number(launch.get('attempts')):
                    row['launcher_attempts'] = launch['attempts']
                seconds = launch.get('seconds')
                if type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0:
                    row['wall_seconds'] = seconds
            accepted = usage_ledger[cid]['usage']
            for field in FIELDS:
                value = accepted.get(field)
                if value is not None and not _number(value):
                    raise ReportError('invalid accepted usage')
                if value is not None and (record is None or record.get('terminal_usage_events') != 1 or
                                           not isinstance(record.get('direct_terminal_usage'), dict) or
                                           record['direct_terminal_usage'].get(field) != value):
                    raise ReportError('accepted usage differs from original receipt')
                row['usage'][field] = value
            if all(row['usage'][k] is not None for k in FIELDS[:2]) and row['usage']['cached_input_tokens'] > row['usage']['input_tokens']:
                raise ReportError('cached input exceeds input')
            if completion is not None:
                if row['status'] != 'complete_unsettled' or completion['record_sha256'] != saved['record_sha256'] or completion['request_sha256'] != request['request_sha256']:
                    raise ReportError('finished flag is not bound to a successful receipt')
                row['status'] = 'complete'; settled.add(cid)
                if call['role'] == 'judge':
                    judgment = read(folder + 'judgment.json')
                    original = grading.loads_judgment(record['answer'], rubric)
                    if judgment != original or judgment['pair_id'] != call['pair']:
                        raise ReportError('judgment differs from original paid answer')
                    candidate_judgments.append(judgment)
        elif completion is not None:
            raise ReportError('finished flag has no dispatched receipt')
        observations.append(row)
    judgments = []
    for judgment in candidate_judgments:
        pair = pairs[judgment['pair_id']]
        needed_turn = 9 if judgment['continuation'] is not None else 3
        for sid in pair['mask'].values():
            required = [c['id'] for c in calls.values() if c.get('session') == sid and c['turn'] <= needed_turn]
            if not required or any(cid not in settled for cid in required):
                raise ReportError('judgment depends on unfinished answer turns')
        judgments.append(judgment)
    quality = _public_quality(judgments, plan, rubric)
    grouped = defaultdict(list)
    for row in observations:
        if row['role'] != 'answer':
            continue
        key = tuple(row[k] for k in ('model', 'effort', 'depth', 'arm'))
        grouped[('prefix_turns_1_3' if row['turn'] <= 3 else 'extension_turns_4_9', *key)].append(row)
        if row['session_turns'] == 9:
            grouped[('long_session_turns_1_9', *key)].append(row)
    costs = [dict(zip(('segment', 'model', 'effort', 'depth', 'arm'), key), **_totals(rows))
             for key, rows in sorted(grouped.items())]
    for cost, (_key, rows) in zip(costs, sorted(grouped.items())):
        cost['execution_deadline_summary'] = _execution_segment(rows)
    by_deadline = defaultdict(list)
    for row in observations:
        by_deadline[row['deadline_seconds']].append(row)
    deadline_costs = [{'deadline_seconds': deadline, **_totals(rows)} for deadline, rows in
                      sorted(by_deadline.items(), key=lambda item: (item[0] is None, item[0] or 0))]
    session_policies, pair_policies = _execution_policies(observations, sessions, pairs)
    totals = _totals(observations)
    complete = all(row['status'] == 'complete' for row in observations)
    # Refuse a mixed-time snapshot if the controller advanced while files were read.
    for name, digest in captured.items():
        current = _read(run, name, optional=digest is None)
        if (hashlib.sha256(current).hexdigest() if current is not None else None) != digest:
            raise ReportError('run changed while reading; regenerate from a stable snapshot')
    return {'schema_version': 2, 'report_kind': 'public_aggregate_no_private_text',
            'snapshot': {'source_commit': _label(plan['source_commit']),
                         'plan_sha256': frozen['plan_sha256'],
                         'controller_sha256': captured['controller/checkpoint.json'],
                         'controller_revision': state['revision'],
                         'rubric_sha256': frozen['rubric_sha256'],
                         'reporter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         'grading_reducer_sha256': hashlib.sha256(Path(grading.__file__).read_bytes()).hexdigest()},
            'complete': complete, 'pending_local_settlements': sum(r['status'] == 'complete_unsettled' for r in observations),
            'observed_cost': totals,
            'full_run_processed_tokens': totals['usage']['processed_tokens'] if complete else None,
            'cost_by_role': {role: _totals([r for r in observations if r['role'] == role]) for role in ('answer', 'judge')},
            'cost_by_condition': costs, 'cost_by_execution_deadline': deadline_costs,
            'original_slots': observations, 'session_execution_policies': session_policies,
            'pair_execution_policies': pair_policies,
            'quality': quality, 'limitations': LIMITATIONS}


def _cell(value):
    if value is None:
        return 'unknown'
    if type(value) is float:
        return '%.2f' % value
    if type(value) is int:
        return format(value, ',')
    return str(value).replace('|', '\\|').replace('\n', ' ')


def markdown(report):
    cost = report['observed_cost']; usage = cost['usage']; quality = report['quality']
    lines = ['# Conversation ablation aggregate', '',
             '**%s** snapshot; %s of %s CLI invocation slots dispatched. Underlying provider requests: unknown.' %
             ('Complete' if report['complete'] else 'Incomplete', cost['dispatched_cli_invocations'], cost['planned_cli_invocations']), '',
             'Observed processed tokens: **%s**; known input/output subtotal: %s. Input includes cached input; cached tokens are not added again.' % (_cell(usage['processed_tokens']), _cell(usage['known_processed_tokens'])), '',
             '| Input | Cached input (subset) | Noncached input | Output | Started command events | Completed command events |',
             '| ---: | ---: | ---: | ---: | ---: | ---: |',
             '| %s |' % ' | '.join(_cell(v) for v in (usage['input_tokens'], usage['cached_input_tokens'], usage['noncached_input_tokens'], usage['output_tokens'], cost['command_started_events'], cost['command_completed_events'])), '',
             'Missing input/output counters: %s / %s dispatched invocations. Successful receipts awaiting local settlement: %s.' %
             (usage['unknown_input_tokens_invocations'], usage['unknown_output_tokens_invocations'], report['pending_local_settlements']), '',
             '## Costs by condition', '',
             'Prefix = T1–3; extension = T4–9 only; long-session total = T1–9. Long-session totals overlap the other rows. Judge costs are separate.', '',
             '| Segment | Model | Effort | Depth | Arm | Dispatched / planned | Processed | Known subtotal | Command completions |',
             '| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in report['cost_by_condition']:
        cells = [row[k] for k in ('segment', 'model', 'effort', 'depth', 'arm')]
        cells += ['%s / %s' % (row['dispatched_cli_invocations'], row['planned_cli_invocations']), row['usage']['processed_tokens'], row['usage']['known_processed_tokens'], row['command_completed_events']]
        lines.append('| %s |' % ' | '.join(_cell(v) for v in cells))
    lines += ['', 'Judge processed tokens: %s (%s dispatched invocations).' %
              (_cell(report['cost_by_role']['judge']['usage']['processed_tokens']), report['cost_by_role']['judge']['dispatched_cli_invocations']), '',
              '## Execution deadline strata', '',
              'These are declared request/invocation settings, not elapsed time. Missing evidence stays unknown; unstarted slots are not assigned a future policy. Input includes cached input.', '',
              '| Deadline seconds | Dispatched / planned slots | Complete / failed / pending | Processed | Known subtotal | Unknown input / output invocations |',
              '| ---: | ---: | --- | ---: | ---: | --- |']
    for row in report['cost_by_execution_deadline']:
        usage = row['usage']; statuses = row['statuses']
        cells = [_cell(row['deadline_seconds']), '%s / %s' % (row['dispatched_cli_invocations'], row['planned_cli_invocations']),
                 '%s / %s / %s' % tuple(statuses.get(key, 0) for key in ('complete', 'failed', 'pending')),
                 _cell(usage['processed_tokens']), _cell(usage['known_processed_tokens']),
                 '%s / %s' % (usage['unknown_input_tokens_invocations'], usage['unknown_output_tokens_invocations'])]
        lines.append('| %s |' % ' | '.join(cells))
    vector = lambda segment: 'not planned' if segment is None else '[' + ', '.join('?' if v is None else str(v) for v in segment['deadline_vector_seconds']) + ']'
    classification = lambda segment: 'not planned' if segment is None else segment['classification']
    lines += ['', '## Session deadline vectors', '',
              'Vectors preserve every original turn. `?` means no observed deadline. `incomplete` means an unfinished outcome or missing deadline evidence; observed mixtures remain visible in the vector. No final/max-deadline substitution.', '',
              '| Session | Prefix T1–3 seconds | Extension T4–9 seconds | Configured session classification |',
              '| --- | --- | --- | --- |']
    for row in report['session_execution_policies']:
        segments = row['segments']
        lines.append('| %s | %s | %s | %s |' % (row['session_id'], vector(segments['prefix_turns_1_3']),
                     vector(segments['extension_turns_4_9']), classification(segments['configured_session'])))
    lines += ['', '## Pair deadline comparability', '',
              '`same_uniform` requires both completed same-length segments and one shared known deadline; `mixed` requires complete observed same-length segments with differing deadlines. Unknown/incomplete cases are not uniform comparisons. Full vectors, statuses, hashes and every original slot are retained in report.json.', '',
              '| Pair | Segment | Classification | A deadline vector | B deadline vector |',
              '| --- | --- | --- | --- | --- |']
    for row in report['pair_execution_policies']:
        for name in ('prefix_turns_1_3', 'extension_turns_4_9'):
            segment = row['segments'][name]
            if segment is not None:
                lines.append('| %s | %s | %s | %s | %s |' % (row['pair_id'], name, segment['classification'],
                             vector(segment['candidates']['A']), vector(segment['candidates']['B'])))
    lines += ['',
              '## Existing judge scores', '',
              '%s / %s planned pairs graded. Scores come only from conversation_grading.summarize; this report does not evaluate text.' %
              (quality['graded_pairs'], quality['planned_pairs']), '',
              '| Segment | Graded sessions | Quality index mean | Safe success / failure / unknown | First useful turn |',
              '| --- | ---: | ---: | --- | --- |']
    for name, row in quality['segments'].items():
        success = row['safe_task_success']
        lines.append('| %s | %s | %s | %s / %s / %s | unknown (not collected) |' %
                     (name, row['graded_sessions'], _cell(row['quality_index_mean']), success['true'], success['false'], success['unknown']))
    lines += ['', 'Condition-level scores and available descriptive matched contrasts are in report.json. Missing judgments and null scores are not zeros. These existing score summaries are pooled; use session/pair deadline metadata to identify mixed-policy comparisons before attributing differences.', '',
              '## Limits', ''] + ['- ' + value for value in report['limitations']]
    lines += ['', 'Frozen plan hash: `%s`. Controller snapshot hash: `%s`.' %
              (report['snapshot']['plan_sha256'], report['snapshot']['controller_sha256']), '']
    return '\n'.join(lines)


def publish(run, output, overwrite=False):
    """Publish only named aggregate files outside the run; do not replace others."""
    run = _safe_root(run)
    output = Path(output).absolute()
    if '..' in output.parts:
        raise ReportError('parent traversal is not permitted')
    if output == run or run in output.parents:
        raise ReportError('report output must be outside the original run')
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ReportError('output may not contain symlinks')
    if output.exists() and not output.is_dir():
        raise ReportError('output is not a directory')
    targets = [output / 'report.json', output / 'report.md']
    for target in targets:
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not target.is_file() or target.stat().st_nlink != 1:
                raise ReportError('refuse unsafe output artifact')
            if not overwrite:
                raise ReportError('report exists; use --overwrite explicitly')
    report = aggregate(run)
    payloads = [json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', markdown(report)]
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = []
    try:
        for target, payload in zip(targets, payloads):
            fd, name = tempfile.mkstemp(prefix='.aggregate-', dir=output)
            temporary.append(Path(name))
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            if overwrite:
                os.replace(name, target)
            else:
                os.link(name, target, follow_symlinks=False)
                Path(name).unlink()
    finally:
        for path in temporary:
            if path.exists():
                path.unlink()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    try:
        report = publish(args.run, args.output, args.overwrite)
        print(json.dumps({'written': ['report.json', 'report.md'], 'complete': report['complete']}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Aggregate refused: ' + type(error).__name__, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
