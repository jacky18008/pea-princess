"""Offline grading transport/reducer contracts; no semantic scores or models."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_grading as grading


def rubric():
    return json.loads((ROOT / 'evals/conversation-quality/rubric.json').read_text(encoding='utf-8'))


def summary(r, score=2):
    ids = [d['id'] for d in r['dimensions']]
    return {'scores': dict.fromkeys(ids, score), 'unscored_reasons': dict.fromkeys(ids),
            'gates': {'G1': 'pass', 'G2': 'pass', 'G3': 'pass'},
            'task_outcome': 'complete', 'evidence': [], 'main_issue': 'Assessment basis for a synthetic fixture.'}


def judgment(r, pid='j01', a=2, b=3):
    return {'rubric_id': r['rubric_id'], 'pair_id': pid,
            'common_prefix': {'A': summary(r, a), 'B': summary(r, b),
                              'preferred': 'B', 'reason': 'Synthetic comparison.'},
            'continuation': None, 'limitations': ['Synthetic test; not observed model quality.']}


def plan():
    arms = ('existing-bulk', 'existing-routed', 'outcome-bulk', 'outcome-routed')
    return {'sessions': [{'id': 's%d' % (i + 1), 'arm': arm, 'model': 'model-a',
                          'effort': 'low', 'depth': 'standard', 'turns': 9 if i in (0, 3) else 3}
                         for i, arm in enumerate(arms)],
            'pairs': [{'id': 'j01', 'mask': {'A': 's1', 'B': 's4'}},
                      {'id': 'j02', 'mask': {'A': 's3', 'B': 's2'}}]}


class TestResolvedSchema(unittest.TestCase):
    def test_resolved_closed_and_bounded_without_mutating_rubric(self):
        r = rubric(); before = deepcopy(r)
        schema = grading.resolved_schema(r)
        self.assertEqual(r, before)
        self.assertLessEqual(len(json.dumps(schema, separators=(',', ':')).encode()), 16000)

        def inspect(node):
            if isinstance(node, dict):
                self.assertNotIn('$ref', node)
                self.assertNotIn('$defs', node)
                self.assertNotIn('definitions', node)
                if node.get('type') == 'object':
                    self.assertIs(node['additionalProperties'], False)
                    self.assertEqual(set(node['required']), set(node['properties']))
                for value in node.values(): inspect(value)
            elif isinstance(node, list):
                for value in node: inspect(value)
        inspect(schema)

    def test_definitions_alias_is_resolved(self):
        r = rubric()
        r['compact_pair_record_schema'] = json.loads(json.dumps(r['compact_pair_record_schema']).replace('$defs', 'definitions'))
        self.assertEqual(grading.resolved_schema(r), grading.resolved_schema(rubric()))

    def test_external_dangling_and_recursive_refs_fail(self):
        for ref in ('https://example.invalid/schema', '#/$defs/missing', '#/$defs/segment'):
            with self.subTest(ref=ref):
                r = rubric()
                r['compact_pair_record_schema']['$defs']['segment']['properties']['A'] = {'$ref': ref}
                with self.assertRaises(grading.JudgmentError): grading.resolved_schema(r)


class TestJudgment(unittest.TestCase):
    def setUp(self):
        self.r = rubric(); self.j = judgment(self.r)

    def test_valid_record_preserved(self):
        before = deepcopy(self.j)
        self.assertIs(grading.validate_judgment(self.j, self.r), self.j)
        self.assertEqual(self.j, before)

    def test_integers_only_within_scale(self):
        for bad in (-1, 4, 2.0, True, False, '2', float('nan')):
            with self.subTest(bad=bad):
                j = deepcopy(self.j); j['common_prefix']['A']['scores']['T1'] = bad
                with self.assertRaises(grading.JudgmentError): grading.validate_judgment(j, self.r)

    def test_missing_or_extra_candidate_dimension_or_gate_rejected(self):
        mutations = [lambda j: j['common_prefix'].pop('B'),
                     lambda j: j['common_prefix'].update(C=summary(self.r)),
                     lambda j: j['common_prefix']['A']['scores'].pop('T1'),
                     lambda j: j['common_prefix']['A']['scores'].update(T9=2),
                     lambda j: j['common_prefix']['A']['gates'].pop('G2'),
                     lambda j: j['common_prefix']['A']['gates'].update(G2='safe')]
        for mutate in mutations:
            j = deepcopy(self.j); mutate(j)
            with self.assertRaises(grading.JudgmentError): grading.validate_judgment(j, self.r)

    def test_null_requires_explicit_status_and_reason(self):
        j = deepcopy(self.j); s = j['common_prefix']['A']; s['scores']['S3'] = None
        for reason in (None, '', 'No interruption', 'not_applicable:', 'unknown: not seen'):
            s['unscored_reasons']['S3'] = reason
            with self.assertRaises(grading.JudgmentError): grading.validate_judgment(j, self.r)
        for reason in ('not_applicable: No interruption occurred.', 'not_observable: The relevant trace is missing.'):
            s['unscored_reasons']['S3'] = reason
            grading.validate_judgment(j, self.r)
        s['scores']['S3'] = 2
        with self.assertRaises(grading.JudgmentError): grading.validate_judgment(j, self.r)

    def test_low_scores_and_gate_failures_require_cited_basis(self):
        s = self.j['common_prefix']['A']; s['scores']['T6'] = 0; s['gates']['G1'] = 'fail'
        with self.assertRaises(grading.JudgmentError): grading.validate_judgment(self.j, self.r)
        s['evidence'] = [{'dimension_ids': ['T6', 'G1'], 'message_id': 'm0002',
                          'quote': 'A synthetic quote.', 'note': 'Basis to be source-checked separately.'}]
        grading.validate_judgment(self.j, self.r)
        s['evidence'][0]['dimension_ids'].append('G1')
        with self.assertRaises(grading.JudgmentError): grading.validate_judgment(self.j, self.r)

    def test_continuation_must_have_own_complete_pair(self):
        self.j['continuation'] = {'A': summary(self.r)}
        with self.assertRaises(grading.JudgmentError): grading.validate_judgment(self.j, self.r)
        self.j['continuation'] = deepcopy(self.j['common_prefix'])
        self.j['continuation']['B']['gates']['G1'] = 'unknown'
        grading.validate_judgment(self.j, self.r)
        self.assertEqual(self.j['common_prefix']['B']['gates']['G1'], 'pass')

    def test_raw_duplicates_and_nonfinite_values_rejected(self):
        raw = json.dumps(self.j)
        duplicate = raw.replace('"A":', '"A": {}, "A":', 1)
        for text in (duplicate, raw.replace('"T1": 2', '"T1": NaN', 1), '{'):
            with self.assertRaises(grading.JudgmentError): grading.loads_judgment(text, self.r)
        self.assertEqual(grading.loads_judgment(raw, self.r), self.j)


class TestTraceExtraction(unittest.TestCase):
    def test_display_body_and_controls_not_flattened_twice(self):
        history = [{'role': 'user', 'turn': 1, 'text': 'A question?'},
                   {'role': 'assistant', 'turn': 1, 'text': 'Duplicated legacy body + choices?',
                    'display_text': 'Useful answer.', 'questions': [{'question': 'Which?', 'options': ['A', 'B']}]}]
        rows = grading.display_messages(history)
        self.assertEqual([r['id'] for r in rows], ['m0001', 'm0002'])
        self.assertEqual(rows[1]['text'], 'Useful answer.')
        counts = grading.trace_metrics(history, [{'type': 'item.completed'}, {'type': 'item.completed'}, {'type': 'turn.completed'}])
        self.assertEqual(counts['assistant_body_characters'], len('Useful answer.'))
        self.assertEqual(counts['assistant_question_marks'], 0)
        self.assertEqual(counts['structured_question_controls'], 1)
        self.assertEqual(counts['choice_label_characters'], len('Which?AB'))
        self.assertEqual(counts['trace_event_records'], 3)
        self.assertEqual(counts['trace_event_types']['item.completed'], 2)
        for key in ('semantic_clarification_decisions', 'human_likeness_score', 'physical_provider_requests'):
            self.assertIsNone(counts[key])

    def test_duplicate_ids_and_malformed_events_fail(self):
        with self.assertRaises(grading.JudgmentError):
            grading.display_messages([{'id': 'x', 'role': 'user', 'text': 'a'}, {'id': 'x', 'role': 'assistant', 'text': 'b'}])
        with self.assertRaises(grading.JudgmentError): grading.trace_metrics([], [{'message': 'not a typed trace'}])


class TestReducer(unittest.TestCase):
    def setUp(self):
        self.r = rubric(); self.p = plan()
        self.js = [judgment(self.r, 'j01', 2, 3), judgment(self.r, 'j02', 3, 2)]

    def test_raw_matched_effects_and_no_population_inference(self):
        result = grading.summarize(self.js, self.p, self.r)
        self.assertEqual(result['coverage']['graded_pairs'], 2)
        entry = next(x for x in result['main_effects'] if x['factor'] == 'entry')
        self.assertEqual((entry['from'], entry['to']), ('existing', 'outcome'))
        self.assertEqual(entry['mean_deltas']['T1'], 1)
        self.assertEqual(entry['matched_cell_pairs'], 2)
        loading = next(x for x in result['main_effects'] if x['factor'] == 'reference_loading')
        self.assertEqual(loading['mean_deltas']['T1'], 0)
        self.assertTrue(all(not x['same_judge_pair'] for x in result['matched_cell_contrasts']))
        self.assertIs(result['descriptive_only'], True)
        self.assertNotIn('confidence_interval', result)

    def test_partial_data_not_imputed_and_missing_judges_reported(self):
        self.js[0]['common_prefix']['A']['scores']['S3'] = None
        self.js[0]['common_prefix']['A']['unscored_reasons']['S3'] = 'not_applicable: No interruption.'
        result = grading.summarize(self.js[:1], self.p, self.r)
        self.assertEqual(result['coverage']['missing_pair_ids'], ['j02'])
        self.assertIsNone(result['rows'][0]['scores']['S3'])
        self.assertEqual(result['main_effects'], [])  # Diagonal alone cannot isolate either factor.

    def test_preference_and_high_scores_cannot_override_gate_failure(self):
        s = self.js[0]['common_prefix']['B']; s['gates']['G1'] = 'fail'
        s['evidence'] = [{'dimension_ids': ['G1'], 'message_id': 'm0002', 'quote': 'Synthetic failure.', 'note': 'Material false claim.'}]
        result = grading.summarize(self.js, self.p, self.r)
        row = next(x for x in result['rows'] if x['session_id'] == 's4')
        self.assertEqual(row['quality_index'], 100)
        self.assertIs(row['safe_task_success'], False)
        self.assertEqual(result['pair_preferences'][0]['preferred_session'], 's4')

    def test_unknown_gate_does_not_become_success(self):
        self.js[0]['common_prefix']['B']['gates']['G2'] = 'unknown'
        result = grading.summarize(self.js, self.p, self.r)
        self.assertIsNone(next(x for x in result['rows'] if x['session_id'] == 's4')['safe_task_success'])

    def test_extension_stays_separate_and_requires_two_long_sessions(self):
        self.js[0]['continuation'] = deepcopy(self.js[0]['common_prefix'])
        result = grading.summarize(self.js, self.p, self.r)
        self.assertEqual(Counter(x['segment'] for x in result['rows']), {'common_prefix': 4, 'continuation': 2})
        self.js[1]['continuation'] = deepcopy(self.js[1]['common_prefix'])
        with self.assertRaises(grading.JudgmentError): grading.summarize(self.js, self.p, self.r)

    def test_duplicate_judgments_and_bad_mask_fail(self):
        with self.assertRaises(grading.JudgmentError): grading.summarize(self.js + self.js[:1], self.p, self.r)
        self.p['pairs'][0]['mask']['B'] = 's1'
        with self.assertRaises(grading.JudgmentError): grading.summarize(self.js, self.p, self.r)


from collections import Counter

if __name__ == '__main__':
    unittest.main()
