#!/usr/bin/env python3
"""Offline transport validation and descriptive conversation-eval reduction.

No model calls and no semantic/"human-like" scoring. ``resolved_schema(rubric)``
inlines local references and closes the reason map for strict Structured Outputs.
``validate_judgment(obj, rubric)`` validates that strict shape and score/reason
consistency. Use ``loads_judgment`` on raw JSON to reject duplicate object keys.
``summarize(judgments, plan, rubric)`` restores condition labels after blind judging.

OpenAI schema constraints checked 2026-09-09:
https://developers.openai.com/api/docs/guides/structured-outputs
Python 3.9+, standard library only; CLI commands print one JSON object.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import itertools
import json
from pathlib import Path
import sys


class JudgmentError(ValueError):
    """Invalid grading data; never silently repair a paid judgment."""


def _ids(rubric):
    ids = [row['id'] for row in rubric['dimensions']]
    if not ids or len(ids) != len(set(ids)):
        raise JudgmentError('rubric dimension IDs must be nonempty and unique')
    return ids


def resolved_schema(rubric):
    """Return a self-contained strict schema; do not mutate the source rubric.

All dimension reason slots are required: null for scored dimensions; otherwise
``not_applicable: explanation`` or ``not_observable: explanation``. The original
sparse, open-ended map is unsuitable for strict output transport. References may
use $defs or definitions; external, dangling and recursive references are rejected.
This is an offline compatibility transformation, not a provider acceptance test.
"""
    source = deepcopy(rubric['compact_pair_record_schema'])
    ids = _ids(rubric)

    def resolve(node, trail=()):
        if isinstance(node, list):
            return [resolve(value, trail) for value in node]
        if not isinstance(node, dict):
            return node
        if '$ref' in node:
            ref = node['$ref']
            if not isinstance(ref, str) or not ref.startswith('#/') or ref in trail:
                raise JudgmentError('external or recursive schema reference: %r' % ref)
            target = source
            try:
                for part in ref[2:].split('/'):
                    target = target[part.replace('~1', '/').replace('~0', '~')]
            except (KeyError, TypeError) as error:
                raise JudgmentError('unresolved schema reference: ' + ref) from error
            if not isinstance(target, dict):
                raise JudgmentError('schema reference must name an object: ' + ref)
            merged = dict(target)
            merged.update({k: v for k, v in node.items() if k != '$ref'})
            return resolve(merged, trail + (ref,))
        out = {k: resolve(v, trail) for k, v in node.items()
               if k not in ('$defs', 'definitions', '$schema', '$id', 'title')}
        if 'const' in out:
            out['enum'] = [out.pop('const')]
        if 'enum' in out and 'type' not in out:
            if all(isinstance(value, str) for value in out['enum']):
                out['type'] = 'string'
        if out.get('type') == 'object':
            props = out.get('properties')
            if props is None:
                raise JudgmentError('open schema object requires declared properties')
            out['additionalProperties'] = False
            out['required'] = list(props)
        return out

    # Transform the only intentionally dynamic map before resolving its parents.
    def close_reasons(node):
        if isinstance(node, dict):
            props = node.get('properties', {})
            if 'unscored_reasons' in props:
                props['unscored_reasons'] = {
                    'type': 'object', 'additionalProperties': False,
                    'required': ids,
                    'properties': {key: {'type': ['string', 'null']} for key in ids},
                    'description': 'For every dimension: null if scored; otherwise '
                    'not_applicable: explanation or not_observable: explanation.'}
            for value in node.values():
                close_reasons(value)
        elif isinstance(node, list):
            for value in node:
                close_reasons(value)
    close_reasons(source)
    return resolve(source)


def _check(value, schema, path='$'):
    """Validate the small resolved schema subset, not arbitrary JSON Schema."""
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            try:
                _check(value, branch, path)
                return
            except JudgmentError:
                pass
        raise JudgmentError(path + ': does not match any permitted shape')
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    matches = {'null': value is None, 'object': isinstance(value, dict),
               'array': isinstance(value, list), 'string': isinstance(value, str),
               'integer': type(value) is int, 'boolean': type(value) is bool}
    if types and not any(matches.get(t, False) for t in types):
        raise JudgmentError(path + ': wrong value type')
    if 'enum' in schema and value not in schema['enum']:
        raise JudgmentError(path + ': value outside enum')
    if type(value) is int:
        if value < schema.get('minimum', value) or value > schema.get('maximum', value):
            raise JudgmentError(path + ': score outside range')
    if isinstance(value, str) and len(value) < schema.get('minLength', 0):
        raise JudgmentError(path + ': empty string')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', len(value)):
            raise JudgmentError(path + ': wrong number of items')
        for index, item in enumerate(value):
            _check(item, schema.get('items', {}), '%s[%d]' % (path, index))
    if isinstance(value, dict):
        props = schema.get('properties', {})
        missing = set(schema.get('required', ())) - set(value)
        extra = set(value) - set(props)
        if missing or (extra and schema.get('additionalProperties') is False):
            raise JudgmentError('%s: missing=%s extra=%s' % (path, sorted(missing), sorted(extra)))
        for key, item in value.items():
            if key in props:
                _check(item, props[key], path + '.' + key)


def validate_judgment(obj, rubric):
    """Return obj if valid; raise JudgmentError for transport/invariant failures.

This cannot establish whether a quote is true or a subjective score is fair.
Packet availability and exact quote matching are checked separately, where the
transcript/artifact bytes are available. Already-parsed dicts cannot reveal keys
discarded by a permissive JSON parser; use loads_judgment for original bytes.
"""
    _check(obj, resolved_schema(rubric))
    if not obj['pair_id'].strip():
        raise JudgmentError('pair_id must be nonempty')
    for segment_name in ('common_prefix', 'continuation'):
        segment = obj[segment_name]
        if segment is None:
            continue
        for label in ('A', 'B'):
            summary = segment[label]
            prefix = segment_name + '.' + label
            for key, score in summary['scores'].items():
                reason = summary['unscored_reasons'][key]
                if score is not None:
                    if reason is not None:
                        raise JudgmentError(prefix + ': scored dimension has an unscored reason: ' + key)
                elif not isinstance(reason, str) or not any(
                        reason.startswith(kind + ':') and reason.split(':', 1)[1].strip()
                        for kind in ('not_applicable', 'not_observable')):
                    raise JudgmentError(prefix + ': null needs explicit unscored status/reason: ' + key)
            supported = set()
            for evidence in summary['evidence']:
                dimensions = evidence['dimension_ids']
                if not dimensions or len(dimensions) != len(set(dimensions)):
                    raise JudgmentError(prefix + ': evidence dimension IDs must be nonempty and unique')
                if not evidence['message_id'].strip() or not evidence['quote'].strip() or not evidence['note'].strip():
                    raise JudgmentError(prefix + ': evidence needs an ID, exact quote and note')
                supported.update(dimensions)
            needs = {key for key, score in summary['scores'].items() if score in (0, 1)}
            needs.update(key for key, state in summary['gates'].items() if state == 'fail')
            if needs - supported:
                raise JudgmentError(prefix + ': low scores/gate failures lack evidence: ' + ','.join(sorted(needs - supported)))
            if not summary['main_issue'].strip():
                raise JudgmentError(prefix + ': supply a concise assessment basis')
    return obj


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JudgmentError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def loads_judgment(text, rubric):
    """Parse original JSON without losing duplicate A/B or dimension keys."""
    def bad_constant(value):
        raise JudgmentError('non-finite JSON constant: ' + value)
    try:
        obj = json.loads(text, object_pairs_hook=_unique_object, parse_constant=bad_constant)
    except (TypeError, json.JSONDecodeError) as error:
        raise JudgmentError('invalid judgment JSON') from error
    return validate_judgment(obj, rubric)


def display_messages(history):
    """Extract displayed message bodies/choice controls with stable local IDs.

Original histories and tool traces remain the caller's immutable evidence.
No summaries, semantic question counts or style classifications are generated.
"""
    result, seen = [], set()
    for index, message in enumerate(history, 1):
        if not isinstance(message, dict) or message.get('role') not in ('user', 'assistant', 'tool', 'human', 'persona'):
            raise JudgmentError('invalid transcript role at message %d' % index)
        body = message.get('display_text', message.get('text', message.get('content')))
        if not isinstance(body, str):
            raise JudgmentError('message body must be text at message %d' % index)
        mid = message.get('id', 'm%04d' % index)
        if not isinstance(mid, str) or not mid or mid in seen:
            raise JudgmentError('message IDs must be nonempty and unique')
        seen.add(mid)
        row = {'id': mid, 'role': message['role'], 'text': body,
               'turn': message.get('turn'), 'questions': deepcopy(message.get('questions', []))}
        if not isinstance(row['questions'], list):
            raise JudgmentError('questions must be a list')
        for question in row['questions']:
            if not isinstance(question, dict) or not isinstance(question.get('question'), str) or not isinstance(question.get('options'), list) or not all(isinstance(x, str) for x in question['options']):
                raise JudgmentError('invalid displayed question control')
        result.append(row)
    return result


def trace_metrics(history, events=()):
    """Exact representation counts, explicitly not semantic quality scores."""
    rows = display_messages(history)
    roles = Counter(row['role'] for row in rows)
    types = Counter()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get('type'), str):
            raise JudgmentError('trace event needs a type')
        types[event['type']] += 1
    assistants = [row for row in rows if row['role'] == 'assistant']
    return {'messages': len(rows), 'role_counts': dict(roles),
            'assistant_body_characters': sum(len(row['text']) for row in assistants),
            'assistant_question_marks': sum(row['text'].count('?') + row['text'].count('？') for row in assistants),
            'structured_question_controls': sum(len(row['questions']) for row in assistants),
            'choice_label_characters': sum(len(q['question']) + sum(map(len, q['options'])) for row in assistants for q in row['questions']),
            'trace_event_records': sum(types.values()), 'trace_event_types': dict(types),
            'semantic_clarification_decisions': None, 'human_likeness_score': None,
            'physical_provider_requests': None,
            'limits': 'Characters/counts describe saved display representation; question marks are not decisions, and trace events are not provider request counts.'}


def _mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _quality(summary, rubric):
    means = [_mean(summary['scores'][d['id']] for d in rubric['dimensions'] if d['level'] == level)
             for level in ('turn', 'session')]
    return 100 * sum(means) / 6 if all(x is not None for x in means) else None


def _safe_success(summary):
    if 'fail' in summary['gates'].values() or summary['task_outcome'] in ('partial', 'failed'):
        return False
    if 'unknown' in summary['gates'].values() or summary['task_outcome'] == 'not_evaluable':
        return None
    return True


def _condition(session):
    try:
        entry, loading = session['arm'].rsplit('-', 1)
        return {'entry': entry, 'reference_loading': loading, 'model': session['model'],
                'effort': session['effort'], 'research_depth': session['depth']}
    except (KeyError, ValueError, AttributeError) as error:
        raise JudgmentError('session needs model/effort/depth/entry-loading arm') from error


def summarize(judgments, plan, rubric):
    """Pure reducer; judgments is an iterable of validated masked pair objects.

Pair mapping remains private until grading is finished. Raw deltas are matched
on every other factor within the same observed segment. Means are descriptive
over matched cells of one scenario, not independent samples or confidence bounds.
"""
    sessions = {s['id']: s for s in plan['sessions']}
    pairs = {p['id']: p for p in plan['pairs']}
    if len(sessions) != len(plan['sessions']) or len(pairs) != len(plan['pairs']):
        raise JudgmentError('duplicate session/pair IDs in plan')
    assigned = []
    for pair in pairs.values():
        mask = pair['mask']
        if set(mask) != {'A', 'B'} or mask['A'] == mask['B'] or any(s not in sessions for s in mask.values()):
            raise JudgmentError('invalid planned A/B mapping')
        assigned.extend(mask.values())
    if len(assigned) != len(set(assigned)):
        raise JudgmentError('a session appears in more than one planned pair')
    rows, seen, votes = [], set(), []
    for judgment in judgments:
        validate_judgment(judgment, rubric)
        pid = judgment['pair_id']
        if pid not in pairs or pid in seen:
            raise JudgmentError('unknown or duplicate judgment pair: ' + pid)
        seen.add(pid)
        pair = pairs[pid]
        if judgment['continuation'] is not None and not all(sessions[s].get('turns', 3) > 3 for s in pair['mask'].values()):
            raise JudgmentError('continuation comparison requires two extended sessions')
        for segment_name in ('common_prefix', 'continuation'):
            segment = judgment[segment_name]
            if segment is None:
                continue
            votes.append({'pair_id': pid, 'segment': segment_name, 'preferred': segment['preferred'],
                          'preferred_session': pair['mask'].get(segment['preferred']), 'reason': segment['reason']})
            for label in ('A', 'B'):
                sid, summary = pair['mask'][label], segment[label]
                rows.append({'session_id': sid, 'pair_id': pid, 'segment': segment_name,
                             'condition': _condition(sessions[sid]), 'scores': deepcopy(summary['scores']),
                             'quality_index': _quality(summary, rubric), 'gates': deepcopy(summary['gates']),
                             'safe_task_success': _safe_success(summary), 'task_outcome': summary['task_outcome'],
                             'unscored_reasons': deepcopy(summary['unscored_reasons'])})
    metrics = _ids(rubric) + ['quality_index', 'safe_task_success']
    contrasts = []
    for factor in ('entry', 'reference_loading', 'model', 'effort', 'research_depth'):
        blocks = defaultdict(list)
        for row in rows:
            key = (row['segment'], tuple(sorted((k, v) for k, v in row['condition'].items() if k != factor)))
            blocks[key].append(row)
        for (segment, fixed), group in sorted(blocks.items()):
            if len({row['condition'][factor] for row in group}) != len(group):
                raise JudgmentError('duplicate condition cell; repetitions need an explicit replicate key')
            for left, right in itertools.combinations(sorted(group, key=lambda r: r['condition'][factor]), 2):
                deltas = {}
                for metric in metrics:
                    a = left['scores'].get(metric) if metric in left['scores'] else left[metric]
                    b = right['scores'].get(metric) if metric in right['scores'] else right[metric]
                    deltas[metric] = b - a if a is not None and b is not None else None
                contrasts.append({'factor': factor, 'segment': segment, 'fixed': dict(fixed),
                                  'from': left['condition'][factor], 'to': right['condition'][factor],
                                  'from_session': left['session_id'], 'to_session': right['session_id'],
                                  'same_judge_pair': left['pair_id'] == right['pair_id'], 'deltas': deltas})
    groups = defaultdict(list)
    for row in contrasts:
        groups[(row['segment'], row['factor'], row['from'], row['to'])].append(row)
    effects = []
    for (segment, factor, start, end), group in sorted(groups.items()):
        effects.append({'segment': segment, 'factor': factor, 'from': start, 'to': end,
                        'matched_cell_pairs': len(group),
                        'mean_deltas': {key: _mean(r['deltas'][key] for r in group) for key in metrics},
                        'observed_pairs_by_metric': {key: sum(r['deltas'][key] is not None for r in group) for key in metrics}})
    return {'descriptive_only': True, 'independent_scenario_replicates': 1,
            'coverage': {'planned_pairs': len(pairs), 'graded_pairs': len(seen),
                         'missing_pair_ids': sorted(set(pairs) - seen)},
            'rows': rows, 'pair_preferences': votes, 'matched_cell_contrasts': contrasts,
            'main_effects': effects,
            'limitations': ['One scenario per condition; no population confidence intervals or significance claims.',
                           'Diagonal blind-pair grouping can affect absolute judge scores; cross-pair factorial deltas retain that limitation.',
                           'Prefix and continuation are separate; omitted/unknown scores never become zero.',
                           'Interaction preference and quality index do not override failed/unknown task gates.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('schema', 'validate', 'summarize'))
    parser.add_argument('--rubric', required=True, type=Path)
    parser.add_argument('--judgments', nargs='*', type=Path, default=[])
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args(argv)
    try:
        rubric = json.loads(args.rubric.read_text(encoding='utf-8'))
        if args.action == 'schema':
            value = resolved_schema(rubric)
        else:
            judgments = [loads_judgment(p.read_text(encoding='utf-8'), rubric) for p in args.judgments]
            if not judgments:
                raise JudgmentError('at least one explicit judgment file is required')
            if args.action == 'validate':
                value = {'valid': True, 'pairs': [j['pair_id'] for j in judgments]}
            else:
                if args.plan is None:
                    raise JudgmentError('--plan is required for summarize')
                value = summarize(judgments, json.loads(args.plan.read_text(encoding='utf-8')), rubric)
        print(json.dumps(value, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
