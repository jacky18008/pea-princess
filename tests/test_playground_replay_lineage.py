"""Historical form answers retain their original controls through repeated replay."""
import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'skills/vet-flat/scripts')]
import playground_intent as intent
import playground_replay as replay


class ReplayClarificationLineage(unittest.TestCase):
    def source(self):
        assistant = {'role': 'assistant', 'call_id': 'call-001-assistant',
                     'text': 'Original reply', 'questions': [
                         {'question': '原來的採光問題？',
                          'options': ['採光當加分', '採光仍是必要條件']}]}
        raw = '原來的採光問題？\n採光當加分；其他要求不變'
        verified = intent.clarification({'messages': [assistant]},
            {'call_id': assistant['call_id'], 'answers': [
                {'question_index': 0, 'option_index': 0, 'text': '其他要求不變'}]}, raw)
        return {'research_mode': 'live', 'output_mode': 'agent', 'queue': [], 'messages': [
            {'role': 'human', 'text': '偏好安靜，採光必須好。'}, assistant,
            dict(role='human', text=raw, kind='question', **verified),
            {'role': 'assistant', 'call_id': 'call-002-assistant',
             'text': 'Original continuation', 'questions': []}]}

    def replayed(self, source, label='First replay'):
        plan = replay.extract_turns(source)
        session = {'research_mode': 'live', 'output_mode': 'agent', 'queue': [],
                   'replay': copy.deepcopy(plan), 'messages': []}
        for turn in plan['turns']:
            # Mirror host release: controls remain in the frozen replay plan,
            # while the original text and receipt go into actual messages.
            inputs = replay.clone_input_files('/unused/source', '/unused/target', turn['inputs'])
            for item in inputs:
                row = {'role': 'human', 'replay_turn': turn['index']}
                row.update({key: copy.deepcopy(item[key]) for key in
                            ('text', 'kind', 'intent_text', 'clarification_receipt') if key in item})
                session['messages'].append(row)
            session['messages'].append({'role': 'assistant', 'text': label,
                'call_id': 'call-%03d-assistant' % turn['index'],
                'questions': [{'question': label + ' changed the question?',
                               'options': ['Require quiet', 'Another new option']}]})
        return session

    def test_repeated_replay_preserves_original_controls_and_answer(self):
        source = self.source()
        original = copy.deepcopy(source)
        first = self.replayed(source)
        second = self.replayed(first, 'Second replay')
        with mock.patch.object(replay.os, 'open', side_effect=AssertionError('pure extraction')):
            plan = replay.extract_turns(second)
        item = plan['turns'][1]['inputs'][0]
        self.assertEqual(source['messages'][1]['questions'], item['clarification_source']['questions'])
        self.assertEqual('採光當加分；其他要求不變', item['intent_text'])
        self.assertEqual(source['messages'][2]['clarification_receipt'], item['clarification_receipt'])
        self.assertEqual(original, source)
        self.assertNotIn('Require quiet', str(item))

    def test_original_forged_receipt_or_client_controls_are_rejected(self):
        for mutation in ('receipt', 'raw', 'controls'):
            with self.subTest(mutation=mutation):
                source = self.source()
                row = source['messages'][2]
                if mutation == 'receipt':
                    row['clarification_receipt']['answers'][0]['selected_option'] = 'Require quiet'
                elif mutation == 'raw':
                    row['text'] = 'Changed answer'
                else:
                    row['clarification_source'] = {key: source['messages'][1][key]
                                                   for key in ('call_id', 'questions')}
                with self.assertRaises(replay.ReplayError):
                    replay.extract_turns(source)

    def test_replay_message_must_match_its_frozen_input(self):
        for field in ('text', 'intent_text', 'kind', 'clarification_receipt', 'replay_turn'):
            with self.subTest(field=field):
                session = self.replayed(self.source())
                row = session['messages'][2]
                if field == 'clarification_receipt':
                    row[field]['answers'][0]['free_text'] = 'Changed choice'
                else:
                    row[field] = 1 if field == 'replay_turn' else 'Changed'
                with self.assertRaises(replay.ReplayError):
                    replay.extract_turns(session)

    def test_missing_or_forged_original_controls_do_not_use_new_questions(self):
        for mutation in ('missing', 'question', 'option', 'call_id'):
            with self.subTest(mutation=mutation):
                source = self.source()
                session = self.replayed(source)
                # Even identical new controls cannot substitute for missing lineage.
                session['messages'][1] = copy.deepcopy(source['messages'][1])
                item = session['replay']['turns'][1]['inputs'][0]
                if mutation == 'missing':
                    del item['clarification_source']
                elif mutation == 'question':
                    item['clarification_source']['questions'][0]['question'] = 'Forged question?'
                elif mutation == 'option':
                    item['clarification_source']['questions'][0]['options'][0] = 'Forged option'
                else:
                    item['clarification_source']['call_id'] = 'different-call'
                with self.assertRaises(replay.ReplayError):
                    replay.extract_turns(session)


if __name__ == '__main__':
    unittest.main()
