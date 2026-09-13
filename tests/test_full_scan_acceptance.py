"""Offline coordinator transactions; all HTTP and actor results are synthetic."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import full_scan_acceptance as coordinator


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n', encoding='utf-8')
    return path


class SyntheticHost:
    """Stateful HTTP double: one explicit POST buys at most one physical call."""

    def __init__(self, case):
        self.case = case
        self.requests = []
        self.sessions = {}
        self.uploads = []
        self.upload_sha256_override = None
        self.before_dispatch = None
        self.after_dispatch = None
        self.after_create = None
        self.next_usage = None
        self.dispatches = 0

    @property
    def posts(self):
        return [row for row in self.requests if row['method'] == 'POST']

    def settings(self):
        return {'research_depth': 'standard', 'reasoning_effort': 'low',
                'research_depth_source': 'user_selected',
                'reasoning_effort_source': 'user_selected'}

    def snapshot(self, sid):
        session = self.sessions[sid]
        values = [row['tokens'] for row in session['calls']]
        result = {'id': sid, 'model': 'gpt-5.6-terra', 'research_mode': 'live',
                'output_mode': 'agent', 'execution_settings': self.settings(),
                'status': 'paused', 'busy': False, 'compatible': True,
                'calls': len(session['calls']),
                'tokens': None if None in values else sum(values),
                'pending_call': False, 'pending_count': 0, 'auto': False,
                'limits': session['limits'], 'next_actor': 'assistant' if not values else None,
                'messages': copy.deepcopy(session['messages']), 'stop_reason': None,
                'skill_artifact': session.get('skill_artifact')}
        result.update(session.get('snapshot_override', {}))
        return result

    def exported(self, sid):
        result = self.snapshot(sid)
        result.update(calls=copy.deepcopy(self.sessions[sid]['calls']),
                      pending_messages=[], actions=[], private=True)
        return result

    def complete(self, sid, text=None):
        session = self.sessions[sid]
        call_id = 'call-%d' % (len(session['calls']) + 1)
        usage = self.next_usage or {
            'input_tokens': 100, 'cached_input_tokens': 25, 'output_tokens': 20,
            'uncached_input_tokens': 75, 'processed_tokens': 120, 'seconds': 0.1}
        self.next_usage = None
        self.dispatches += 1
        if text is not None:
            session['messages'].append({'role': 'human', 'text': text})
        record_hash = digest((sid + call_id).encode())
        session['calls'].append({
            'id': call_id, 'actor': 'assistant', 'status': 'complete',
            'tokens': usage['processed_tokens'], 'execution_settings': self.settings(),
            'receipt': {'id': call_id, 'status': 'recorded', 'physical_status': 'complete',
                        'processed_tokens': usage['processed_tokens'],
                        'record_sha256': record_hash}})
        session['messages'].append({'role': 'assistant', 'call_id': call_id,
                                    'text': 'Synthetic retained response.',
                                    'display_text': 'Synthetic retained response.',
                                    'questions': [{'question': 'Which scope?',
                                                   'options': ['Full scan', 'Advice only']}]})
        session['details'][call_id] = {
            'version': 1, 'session_id': sid, 'call_id': call_id, 'actor': 'assistant',
            'status': 'complete', 'model': 'gpt-5.6-terra',
            'execution_settings': self.settings(),
            'execution_settings_evidence': {'status': 'bound'},
            'integrity': {'ok': True, 'gaps': []}, 'usage': copy.deepcopy(usage),
            'source': {'record_sha256': record_hash,
                       'message_sha256': digest(b'Synthetic retained response.'),
                       'displayed_sha256': digest(b'Synthetic display')},
            'tool_invocation_count': 0, 'tool_failed_count': 0,
            'displayed_questions': {'available': True, 'status': 'present',
                                    'items': session['messages'][-1]['questions'],
                                    'truncated': False},
            'current_input': {'text': text or session['messages'][0]['text'],
                              'available': True, 'truncated': False},
            'raw_actor_reply': {'text': 'Synthetic retained response.',
                                'available': True, 'truncated': False}}
        return call_id

    def request(self, out, state, arm, method, path, body=None):
        self.requests.append({'arm': arm, 'method': method, 'path': path,
                              'body': copy.deepcopy(body)})
        manifest_path = Path(arm['runtime_manifest'])
        manifest = json.loads(manifest_path.read_text())
        package = {'kind': 'public_zip',
                   'sha256': manifest['public_skill']['archive_sha256'],
                   'path': str(manifest_path.parent / manifest['public_skill']['skill_path'])}
        if method == 'GET' and path == '/api/catalog':
            return {'skill_artifact': package, 'source_sync': {'current': True}}
        if method == 'POST' and path == '/api/attachments':
            item = {'id': uuid.uuid4().hex, 'path': body['path'],
                    'sha256': self.upload_sha256_override or digest(Path(body['path']).read_bytes())}
            self.uploads.append(item)
            return copy.deepcopy(item)
        if method == 'POST' and path == '/api/sessions':
            sid = uuid.uuid5(uuid.NAMESPACE_URL,
                             'pea-persona-lab/' + body['client_id']).hex
            if sid in self.sessions:
                self.case.assertEqual(self.sessions[sid]['creation'], body)
            else:
                self.sessions[sid] = {
                    'calls': [], 'details': {}, 'limits': {
                        'max_calls': body['max_calls'], 'max_tokens': body['max_tokens']},
                    'messages': [{'role': 'human', 'text': body['initial_request']}],
                    'skill_artifact': package, 'creation': copy.deepcopy(body)}
            if self.after_create:
                self.after_create()
            return {'id': sid}
        if method == 'GET' and path == '/api/sessions':
            return {'sessions': [self.snapshot(sid) for sid in self.sessions]}
        parts = path.strip('/').split('/')
        if len(parts) < 3 or parts[:2] != ['api', 'session']:
            raise AssertionError('Unexpected offline HTTP route: ' + path)
        sid = parts[2]
        suffix = parts[3:]
        if method == 'GET' and not suffix:
            return self.snapshot(sid)
        if method == 'GET' and suffix == ['export']:
            return self.exported(sid)
        if method == 'GET' and suffix == ['inspect']:
            return {'version': 1, 'session_id': sid,
                    'calls': list(copy.deepcopy(self.sessions[sid]['details']).values())}
        if method == 'GET' and len(suffix) == 2 and suffix[0] == 'inspect':
            return copy.deepcopy(self.sessions[sid]['details'][suffix[1]])
        if method == 'POST' and suffix in (['control'], ['message']):
            if suffix == ['control']:
                self.case.assertEqual('step', body['action'])
            if self.before_dispatch:
                self.before_dispatch(out, state, arm, method, path, body)
            self.complete(sid, text=body.get('text'))
            if self.after_dispatch:
                self.after_dispatch(out, state, arm, method, path, body)
            return {'ok': True}
        raise AssertionError('Unexpected offline HTTP operation: %s %s' % (method, path))


class FullScanAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.out = self.root / 'study'
        self.runtime_paths = {}
        arms = {}
        for index, arm in enumerate(('A', 'B')):
            runtime = self.root / ('runtime-' + arm)
            source = runtime / 'tools' / 'synthetic.py'
            source.parent.mkdir(parents=True)
            source.write_bytes(('FROZEN_ARM = %r\n' % arm).encode())
            skill = runtime / 'skills' / 'pea-princess' / 'SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_bytes(('Synthetic frozen public skill ' + arm).encode())
            archive = runtime / 'public-skill.zip'
            archive.write_bytes(('Synthetic public archive bytes ' + arm).encode())
            files = {}
            for path in (source, skill, archive):
                files[str(path.relative_to(runtime))] = {
                    'sha256': digest(path.read_bytes()), 'bytes': path.stat().st_size,
                    'origin': 'synthetic-test-fixture'}
            manifest = save_json(runtime / 'runtime-manifest.json', {
                'schema_version': 1, 'snapshot_id': 'synthetic-' + arm,
                'files': files, 'public_skill': {
                    'archive_sha256': digest(archive.read_bytes()),
                    'skill_path': 'skills/pea-princess'}})
            self.runtime_paths[arm] = source
            arms[arm] = {'url': 'http://127.0.0.1:%d' % (18765 + index),
                         'runtime_manifest': str(manifest),
                         'runtime_manifest_sha256': digest(manifest.read_bytes())}
        self.plan = {'version': 1, 'global_max_tokens': 4_000_000,
                     'model': 'gpt-5.6-terra', 'research_depth': 'standard',
                     'reasoning_effort': 'low', 'arms': arms,
                     'cases': {'case': {'turns': [
                         {'mode': 'fixed', 'text': 'T1: perform the full scan.'},
                         {'mode': 'choice', 'text': 'Add these details.',
                          'option_policy': 'Choose the option that retains full scope.'},
                         {'mode': 'fixed', 'text': 'T3: keep the original conditions.'},
                         {'mode': 'choice',
                          'option_policy': 'Choose the option that preserves existing conditions.'}],
                         'attachments': []}},
                     'sessions': [
                         {'id': 'A-r1', 'arm': 'A', 'case_id': 'case',
                          'max_tokens': 700_000, 'seed': 1},
                         {'id': 'B-r1', 'arm': 'B', 'case_id': 'case',
                          'max_tokens': 700_000, 'seed': 1}]}
        self.plan_path = save_json(self.root / 'plan-source.json', self.plan)
        self.host = SyntheticHost(self)
        patch = mock.patch.object(coordinator, '_request', side_effect=self.host.request)
        patch.start()
        self.addCleanup(patch.stop)

    def prepare(self):
        save_json(self.plan_path, self.plan)
        return coordinator.prepare(self.out, self.plan_path)

    def create(self, key='A-r1'):
        coordinator.create(self.out, key)
        return next(reversed(self.host.sessions))

    def first_call(self, key='A-r1'):
        sid = self.create(key)
        coordinator.step(self.out, key)
        coordinator.record_observed(self.out, key)
        return sid

    def prepare_fourth_choice(self, questions=True):
        self.plan['cases']['case']['turns'][1] = {
            'mode': 'fixed', 'text': 'T2: frozen preparation details.'}
        self.plan['cases']['case']['turns'][3]['fallback_text'] = 'Preserve all original conditions.'
        self.prepare()
        sid = self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed first-call cost.')
        for _ in range(2):
            coordinator.send(self.out, 'A-r1')
            coordinator.record_observed(self.out, 'A-r1')
        if not questions:
            self.host.sessions[sid]['messages'][-1]['questions'] = []
        return sid

    def assert_blocked_without_post(self, operation):
        before = copy.deepcopy(self.host.posts)
        with self.assertRaises(coordinator.CoordinatorError):
            operation()
        self.assertEqual(before, self.host.posts)

    def test_prepare_freezes_dynamic_plan_without_http_or_model_dispatch(self):
        self.plan['cases']['case']['turns'] = self.plan['cases']['case']['turns'][:3]
        result = self.prepare()
        self.assertEqual(6, result['planned_calls'])
        self.assertEqual(0, result['recorded_calls'])
        self.assertEqual(0, result['processed_tokens'])
        self.assertFalse(result['pending'])
        self.assertEqual([], self.host.requests)
        self.assertEqual(0, self.host.dispatches)

    def test_create_uses_frozen_settings_and_exact_opening_without_dispatch(self):
        self.prepare()
        self.plan['cases']['case']['turns'][0]['text'] = 'Later mutable source text.'
        save_json(self.plan_path, self.plan)
        sid = self.create()
        body = self.host.posts[0]['body']
        self.assertEqual('T1: perform the full scan.', body['initial_request'])
        self.assertEqual('gpt-5.6-terra', body['model'])
        self.assertEqual('standard', body['research_depth'])
        self.assertEqual('low', body['reasoning_effort'])
        self.assertEqual('live', body['research_mode'])
        self.assertEqual('agent', body['output_mode'])
        self.assertEqual(4, body['max_calls'])
        self.assertEqual(700_000, body['max_tokens'])
        self.assertEqual([], self.host.sessions[sid]['calls'])
        self.assertEqual(0, self.host.dispatches)

    def test_changed_manifest_bytes_are_rejected_before_any_http(self):
        self.prepare()
        path = Path(self.plan['arms']['A']['runtime_manifest'])
        path.write_bytes(path.read_bytes() + b' ')
        self.assert_blocked_without_post(lambda: self.create())
        self.assertEqual([], self.host.requests)

    def test_lost_create_ack_reuses_uploaded_files_and_exact_saved_create_body(self):
        evidence = self.root / 'synthetic-evidence.txt'
        evidence.write_bytes(b'Synthetic selected property facts.\n')
        self.plan['cases']['case']['files'] = [{
            'path': str(evidence), 'sha256': digest(evidence.read_bytes())}]
        self.prepare()
        def lost_ack():
            raise OSError('synthetic create acknowledgement lost')
        self.host.after_create = lost_ack
        with self.assertRaises((coordinator.CoordinatorError, OSError)):
            coordinator.create(self.out, 'A-r1')
        original = copy.deepcopy([r['body'] for r in self.host.posts
                                  if r['path'] == '/api/sessions'])
        self.assertEqual(1, len(original))
        self.assertEqual([self.host.uploads[0]['id']], original[0]['attachments'])
        self.host.after_create = None
        coordinator.create(self.out, 'A-r1')
        requests = [r['body'] for r in self.host.posts if r['path'] == '/api/sessions']
        self.assertEqual([original[0], original[0]], requests)
        self.assertEqual(1, len(self.host.uploads))
        self.assertEqual(1, len(self.host.sessions))
        self.assertEqual(0, self.host.dispatches)

    def test_uploaded_hash_mismatch_blocks_session_creation(self):
        evidence = self.root / 'synthetic-evidence.txt'
        evidence.write_bytes(b'Synthetic pinned property evidence.\n')
        self.plan['cases']['case']['files'] = [{
            'path': str(evidence), 'sha256': digest(evidence.read_bytes())}]
        self.prepare()
        self.host.upload_sha256_override = '0' * 64
        with self.assertRaises(coordinator.CoordinatorError):
            coordinator.create(self.out, 'A-r1')
        self.assertEqual(1, len(self.host.uploads))
        self.assertFalse(any(row['path'] == '/api/sessions' for row in self.host.posts))
        self.assertEqual({}, self.host.sessions)
        self.assertEqual(0, self.host.dispatches)

    def test_changed_runtime_file_is_rejected_even_when_manifest_is_unchanged(self):
        self.prepare()
        self.runtime_paths['A'].write_bytes(b'FROZEN_ARM = "tampered"\n')
        self.assert_blocked_without_post(lambda: self.create())
        self.assertEqual([], self.host.requests)

    def test_runtime_change_after_creation_blocks_dispatch(self):
        self.prepare()
        self.create()
        self.runtime_paths['A'].write_bytes(b'changed after create\n')
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.assertEqual(0, self.host.dispatches)

    def test_dispatch_reservation_survives_lost_http_response_and_cannot_retry(self):
        self.prepare()
        self.create()
        def lost_response(*args):
            raise OSError('synthetic response lost after remote commit')
        self.host.after_dispatch = lost_response
        with self.assertRaises((coordinator.CoordinatorError, OSError)):
            coordinator.step(self.out, 'A-r1')
        state = coordinator.report(self.out)
        self.assertTrue(state['pending'])
        self.assertIsNone(state['processed_tokens'])
        self.assertEqual(0, state['known_processed_tokens'])
        self.assertEqual(1, self.host.dispatches)
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.host.after_dispatch = None
        before = len(self.host.posts)
        coordinator.record_observed(self.out, 'A-r1')
        result = coordinator.report(self.out)
        self.assertFalse(result['pending'])
        self.assertEqual(1, result['recorded_calls'])
        self.assertEqual(120, result['processed_tokens'])
        self.assertEqual(before, len(self.host.posts))
        self.assertEqual(1, self.host.dispatches)

    def test_pending_reservation_is_durable_before_dispatch_post(self):
        self.prepare()
        self.create()
        seen = []
        def inspect_reservation(*args):
            state = json.loads((self.out / 'state.json').read_text())['value']
            self.assertTrue(state['pending'])
            self.assertEqual(0, len(state['calls']))
            seen.append(True)
        self.host.before_dispatch = inspect_reservation
        coordinator.step(self.out, 'A-r1')
        self.assertEqual([True], seen)
        self.assertEqual(1, self.host.dispatches)

    def test_first_completed_call_requires_global_cost_acknowledgement(self):
        self.prepare()
        self.create('B-r1')
        self.first_call()
        result = coordinator.report(self.out)
        self.assertTrue(result['cost_checkpoint'])
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'B-r1'))
        coordinator.acknowledge_cost(self.out, 'Reviewed retained first-call cost.')
        self.assertFalse(coordinator.report(self.out)['cost_checkpoint'])
        coordinator.step(self.out, 'B-r1')
        self.assertEqual(2, self.host.dispatches)

    def test_cost_acknowledgement_cannot_clear_an_unresolved_dispatch(self):
        self.prepare()
        self.create()
        coordinator.step(self.out, 'A-r1')
        before = coordinator.report(self.out)
        self.assert_blocked_without_post(lambda: coordinator.acknowledge_cost(
            self.out, 'This note cannot stand in for a retained receipt.'))
        self.assertEqual(before['pending'], coordinator.report(self.out)['pending'])

    def test_local_report_is_available_during_disconnect_without_reprepare(self):
        self.prepare()
        self.create()
        coordinator.step(self.out, 'A-r1')
        before = coordinator.report(self.out)
        with mock.patch.object(coordinator, '_request', side_effect=OSError('offline')) as offline:
            after = coordinator.report(self.out)
        offline.assert_not_called()
        self.assertEqual(before['pending'], after['pending'])
        self.assertEqual(before['planned_calls'], after['planned_calls'])
        self.assertTrue((self.out / 'RESUME.md').is_file())

    def test_recording_does_not_double_count_a_completed_physical_call(self):
        self.prepare()
        self.first_call()
        before = coordinator.report(self.out)
        posts = copy.deepcopy(self.host.posts)
        try:
            coordinator.record_observed(self.out, 'A-r1')
        except coordinator.CoordinatorError:
            pass  # Refusing a duplicate and an idempotent read are both safe.
        after = coordinator.report(self.out)
        self.assertEqual(before['recorded_calls'], after['recorded_calls'])
        self.assertEqual(before['processed_tokens'], after['processed_tokens'])
        self.assertEqual(posts, self.host.posts)

    def test_unknown_inspector_usage_never_falls_back_to_snapshot_token_total(self):
        self.prepare()
        self.create('B-r1')
        sid = self.create()
        coordinator.step(self.out, 'A-r1')
        detail = self.host.sessions[sid]['details']['call-1']
        detail['usage'].update(input_tokens=None, uncached_input_tokens=None,
                               processed_tokens=None)
        self.assertEqual(120, self.host.snapshot(sid)['tokens'])
        try:
            coordinator.record_observed(self.out, 'A-r1')
        except coordinator.CoordinatorError:
            pass
        state = coordinator.report(self.out)
        self.assertIsNone(state['processed_tokens'])
        self.assertTrue(state['halted'] or state['pending'])
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'B-r1'))
        self.assertEqual(1, self.host.dispatches)

    def test_null_inspector_usage_is_recorded_unknown_and_halts_without_crashing(self):
        self.prepare()
        sid = self.create()
        coordinator.step(self.out, 'A-r1')
        self.host.sessions[sid]['details']['call-1']['usage'] = None
        coordinator.record_observed(self.out, 'A-r1')
        result = coordinator.report(self.out)
        self.assertEqual(1, result['recorded_calls'])
        self.assertIsNone(result['processed_tokens'])
        self.assertTrue(result['halted'])
        self.assertEqual(1, self.host.dispatches)

    def test_guarded_choice_preserves_raw_question_but_validates_answer_only_authority(self):
        question = 'Which scope?'
        pending = {'questions': [{'question': question, 'options': ['Full scan', 'Advice only']}],
                   'intent_guard_version': 1, 'source_call_id': 'call-1'}
        spec = {'text': 'Add these details.'}
        actual = question + '\nAdd these details.'
        submission = {'question': question, 'option': '', 'free_text': spec['text'], 'text': actual}
        receipt = {'call_id': 'call-1', 'answers': [{'question_index': 0, 'question': question,
                    'option_index': None, 'selected_option': None, 'free_text': spec['text']}]}
        row = {'text': actual, 'intent_text': spec['text'], 'clarification_receipt': receipt}
        result = coordinator._choice(spec, pending, submission, actual, row)
        self.assertEqual(actual, result['text'])
        self.assertEqual(spec['text'], result['intent_text'])
        self.assertEqual(receipt, result['clarification_receipt'])
        for bad in ({}, dict(row, intent_text=actual), dict(row, clarification_receipt=dict(receipt, call_id='stale'))):
            with self.subTest(bad=bad), self.assertRaises(coordinator.CoordinatorError):
                coordinator._choice(spec, pending, submission, actual, bad)

    def test_guarded_actual_option_receipt_cannot_select_an_unoffered_control(self):
        question = 'Which scope?'
        pending = {'questions': [{'question': question, 'options': ['Full scan', 'Advice only']}],
                   'intent_guard_version': 1, 'source_call_id': 'call-1'}
        actual = question + '\nAdvice only'
        submission = {'question': question, 'option': 'Advice only', 'free_text': '', 'text': actual,
                      'selection_reason': 'The actual option matches the frozen advice-only policy.'}
        answer = {'question_index': 0, 'question': question, 'option_index': 1, 'selected_option': 'Advice only', 'free_text': ''}
        row = {'text': actual, 'intent_text': 'Advice only', 'clarification_receipt': {'call_id': 'call-1', 'answers': [answer]}}
        result = coordinator._choice({}, pending, submission, actual, row)
        self.assertEqual('actual_option', result['choice_coverage'])
        row['clarification_receipt']['answers'][0]['option_index'] = 0
        with self.assertRaises(coordinator.CoordinatorError):
            coordinator._choice({}, pending, submission, actual, row)

    def test_cached_input_is_inclusive_and_is_not_counted_twice(self):
        self.prepare()
        self.first_call()
        state = coordinator.report(self.out)
        self.assertEqual(120, state['processed_tokens'])
        self.assertEqual(120, state['known_processed_tokens'])

    def test_unrecorded_call_in_other_created_arm_blocks_dispatch(self):
        self.prepare()
        sid_b = self.create('B-r1')
        self.create()
        self.host.complete(sid_b)
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.assertEqual(1, self.host.dispatches)

    def test_busy_other_created_arm_blocks_dispatch_without_local_reservation(self):
        self.prepare()
        sid_b = self.create('B-r1')
        self.create()
        self.host.sessions[sid_b]['snapshot_override'] = {'busy': True, 'status': 'running'}
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.assertEqual(0, self.host.dispatches)

    def test_multiple_unrecorded_physical_calls_quarantine_without_retry(self):
        self.prepare()
        sid = self.create()
        coordinator.step(self.out, 'A-r1')
        self.host.complete(sid, 'Synthetic out-of-band second request.')
        try:
            coordinator.record_observed(self.out, 'A-r1')
        except coordinator.CoordinatorError:
            pass
        result = coordinator.report(self.out)
        self.assertTrue(result['halted'] or result['pending'])
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.assertEqual(2, self.host.dispatches)

    def test_fixed_send_preserves_frozen_turn_and_call_ceiling(self):
        self.plan['cases']['case']['turns'] = [
            {'mode': 'fixed', 'text': 'T1: original question.'},
            {'mode': 'fixed', 'text': 'T2: exact frozen follow-up.'}]
        self.prepare()
        self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed 120 retained tokens.')
        coordinator.send(self.out, 'A-r1')
        body = self.host.posts[-1]['body']
        self.assertEqual('T2: exact frozen follow-up.', body['text'])
        self.assertEqual('question', body['kind'])
        coordinator.record_observed(self.out, 'A-r1')
        self.assert_blocked_without_post(lambda: coordinator.send(self.out, 'A-r1'))
        self.assertEqual(2, self.host.dispatches)

    def test_choice_turn_requires_ui_reservation_and_reservation_does_not_dispatch(self):
        self.prepare()
        self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed first-call cost.')
        self.assert_blocked_without_post(lambda: coordinator.send(self.out, 'A-r1'))
        before = copy.deepcopy(self.host.posts)
        coordinator.reserve_ui(self.out, 'A-r1')
        self.assertEqual(before, self.host.posts)
        state = coordinator.report(self.out)
        self.assertTrue(state['pending'])
        self.assertIsNone(state['processed_tokens'])
        self.assertEqual(120, state['known_processed_tokens'])
        self.assertEqual(1, self.host.dispatches)

    def test_reserved_native_free_text_reconciles_with_missing_option_coverage(self):
        self.prepare()
        sid = self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed first-call cost.')
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Which scope?\nAdd these details.'
        self.host.complete(sid, actual)
        before = copy.deepcopy(self.host.posts)
        submission = {'question': 'Which scope?', 'option': '',
                      'free_text': 'Add these details.', 'text': actual}
        result = coordinator.record_observed(self.out, 'A-r1', submission)
        self.assertEqual(2, result['recorded_calls'])
        self.assertEqual(240, result['processed_tokens'])
        self.assertFalse(result['pending'])
        self.assertFalse(result['halted'])
        self.assertEqual(before, self.host.posts)
        receipt = json.loads((self.out / 'receipts' / 'A-r1-t2.json').read_text())
        self.assertEqual({**submission, 'choice_coverage': 'missing',
                          'native_question': True}, receipt['submission'])

    def test_frozen_native_free_text_cannot_add_an_extra_model_authored_option(self):
        self.prepare()
        sid = self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed first-call cost.')
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Which scope?\nFull scan；Add these details.'
        self.host.complete(sid, actual)
        submission = {'question': 'Which scope?', 'option': 'Full scan',
                      'free_text': 'Add these details.', 'text': actual,
                      'selection_reason': 'This extra model option was not part of frozen T2.'}
        self.assert_blocked_without_post(lambda: coordinator.record_observed(
            self.out, 'A-r1', submission))
        result = coordinator.report(self.out)
        self.assertEqual(1, result['recorded_calls'])
        self.assertTrue(result['pending'])
        self.assertEqual(2, self.host.dispatches)

    def test_fourth_turn_plain_fallback_retains_missing_native_question_coverage(self):
        sid = self.prepare_fourth_choice(questions=False)
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Preserve all original conditions.'
        self.host.complete(sid, actual)
        before = copy.deepcopy(self.host.posts)
        submission = {'text': actual, 'question': '', 'option': '', 'free_text': actual}
        result = coordinator.record_observed(self.out, 'A-r1', submission)
        self.assertEqual(4, result['recorded_calls'])
        self.assertEqual(480, result['processed_tokens'])
        self.assertFalse(result['halted'])
        self.assertEqual(before, self.host.posts)
        receipt = json.loads((self.out / 'receipts' / 'A-r1-t4.json').read_text())
        self.assertEqual('missing', receipt['submission']['choice_coverage'])
        self.assertFalse(receipt['submission']['native_question'])

    def test_fourth_turn_actual_option_retains_successful_choice_coverage(self):
        sid = self.prepare_fourth_choice()
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Which scope?\nFull scan'
        self.host.complete(sid, actual)
        submission = {'text': actual, 'question': 'Which scope?',
                      'option': 'Full scan', 'free_text': '',
                      'selection_reason': 'The actual option preserves the frozen scope.'}
        result = coordinator.record_observed(self.out, 'A-r1', submission)
        self.assertEqual(4, result['recorded_calls'])
        receipt = json.loads((self.out / 'receipts' / 'A-r1-t4.json').read_text())
        self.assertEqual('actual_option', receipt['submission']['choice_coverage'])
        self.assertTrue(receipt['submission']['native_question'])

    def test_fourth_turn_unfrozen_fallback_stays_pending_without_retry(self):
        sid = self.prepare_fourth_choice(questions=False)
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Different operator-authored conditions.'
        self.host.complete(sid, actual)
        submission = {'text': actual, 'question': '', 'option': '', 'free_text': actual}
        self.assert_blocked_without_post(lambda: coordinator.record_observed(
            self.out, 'A-r1', submission))
        result = coordinator.report(self.out)
        self.assertEqual(3, result['recorded_calls'])
        self.assertTrue(result['pending'])
        self.assertEqual(4, self.host.dispatches)

    def test_invented_ui_option_is_not_accepted_or_automatically_resubmitted(self):
        self.prepare()
        sid = self.first_call()
        coordinator.acknowledge_cost(self.out, 'Reviewed first-call cost.')
        coordinator.reserve_ui(self.out, 'A-r1')
        actual = 'Which scope?\nInvented scope；Add these details.'
        self.host.complete(sid, actual)
        submission = {'question': 'Which scope?', 'option': 'Invented scope',
                      'free_text': 'Add these details.', 'text': actual,
                      'selection_reason': 'The control was not actually available.'}
        self.assert_blocked_without_post(lambda: coordinator.record_observed(
            self.out, 'A-r1', submission))
        result = coordinator.report(self.out)
        self.assertEqual(1, result['recorded_calls'])
        self.assertTrue(result['pending'])
        self.assert_blocked_without_post(lambda: coordinator.send(self.out, 'A-r1'))
        self.assertEqual(2, self.host.dispatches)

    def test_call_setting_binding_failure_retains_evidence_and_stops(self):
        self.prepare()
        sid = self.create()
        coordinator.step(self.out, 'A-r1')
        self.host.sessions[sid]['details']['call-1']['execution_settings_evidence']['status'] = 'unbound'
        result = coordinator.record_observed(self.out, 'A-r1')
        self.assertEqual(1, result['recorded_calls'])
        self.assertTrue(result['halted'])
        self.assertTrue((self.out / 'receipts' / 'A-r1-t1.json').is_file())
        self.assert_blocked_without_post(lambda: coordinator.acknowledge_cost(
            self.out, 'Cannot override the unbound call settings with a cost note.'))

    def test_wrong_frozen_model_is_blocked_before_post(self):
        self.prepare()
        sid = self.create()
        self.host.sessions[sid]['snapshot_override'] = {'model': 'gpt-6-astra'}
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'A-r1'))
        self.assertEqual(0, self.host.dispatches)

    def test_global_token_limit_blocks_new_arm_after_one_call_overshoot(self):
        self.plan['global_max_tokens'] = 10_000
        for session in self.plan['sessions']:
            session['max_tokens'] = 10_000
        self.prepare()
        self.create('B-r1')
        self.host.next_usage = {'input_tokens': 10_000, 'cached_input_tokens': 2_000,
                                'output_tokens': 10, 'uncached_input_tokens': 8_000,
                                'processed_tokens': 10_010, 'seconds': 0.1}
        self.first_call()
        try:
            coordinator.acknowledge_cost(self.out, 'Observed bounded single-call overshoot.')
        except coordinator.CoordinatorError:
            pass
        self.assertEqual(10_010, coordinator.report(self.out)['processed_tokens'])
        self.assert_blocked_without_post(lambda: coordinator.step(self.out, 'B-r1'))
        self.assertEqual(1, self.host.dispatches)

    def test_session_token_limit_blocks_followup_below_global_limit(self):
        self.plan['sessions'][0]['max_tokens'] = 10_000
        self.plan['cases']['case']['turns'][1] = {'mode': 'fixed', 'text': 'Do more.'}
        self.prepare()
        self.host.next_usage = {'input_tokens': 9_990, 'cached_input_tokens': 2_000,
                                'output_tokens': 10, 'uncached_input_tokens': 7_990,
                                'processed_tokens': 10_000, 'seconds': 0.1}
        self.first_call()
        try:
            coordinator.acknowledge_cost(self.out, 'Observed the session ceiling.')
        except coordinator.CoordinatorError:
            pass
        self.assertLess(coordinator.report(self.out)['processed_tokens'],
                        self.plan['global_max_tokens'])
        self.assert_blocked_without_post(lambda: coordinator.send(self.out, 'A-r1'))
        self.assertEqual(1, self.host.dispatches)


class FullScanHttpArchiveTests(unittest.TestCase):
    """Exercise the real archive boundary around a connection mock, never sockets."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name).resolve()
        self.arm = {'url': 'http://127.0.0.1:18765'}
        self.connection = mock.MagicMock()
        self.response = self.connection.getresponse.return_value
        self.response.status = 200
        self.response.getheaders.return_value = [('Content-Type', 'application/json')]
        self.response.read.return_value = b'{"ok":true}'
        patch = mock.patch.object(coordinator.http.client, 'HTTPConnection',
                                  return_value=self.connection)
        self.factory = patch.start()
        self.addCleanup(patch.stop)

    def archived(self):
        files = list((self.out / 'http').glob('*.json'))
        self.assertEqual(1, len(files))
        return json.loads(files[0].read_text())

    def test_exact_request_is_saved_before_connection_and_raw_response_is_retained(self):
        body = {'text': 'Exact synthetic input.\nSecond line.', 'client_id': str(uuid.uuid4())}
        def before_connection(*args, **kwargs):
            saved = self.archived()
            self.assertEqual(body, saved['request'])
            self.assertIsNone(saved['response'])
        self.connection.request.side_effect = before_connection
        result = coordinator._request(self.out, {}, self.arm, 'POST', '/api/sessions', body)
        self.assertEqual({'ok': True}, result)
        self.assertEqual('{"ok":true}', self.archived()['response'])
        self.factory.assert_called_once_with('127.0.0.1', 18765, timeout=15)
        self.connection.request.assert_called_once()
        self.connection.close.assert_called_once()

    def test_disconnected_response_preserves_attempt_and_never_retries_connection(self):
        self.connection.getresponse.side_effect = OSError('synthetic disconnect')
        body = {'action': 'step', 'client_id': str(uuid.uuid4())}
        with self.assertRaisesRegex(coordinator.CoordinatorError, 'no retry'):
            coordinator._request(self.out, {}, self.arm, 'POST', '/api/session/abc/control', body)
        saved = self.archived()
        self.assertEqual(body, saved['request'])
        self.assertIn('synthetic disconnect', saved['error'])
        self.assertIsNone(saved['response'])
        self.factory.assert_called_once()
        self.connection.request.assert_called_once()
        self.connection.close.assert_called_once()

    def test_redirect_is_retained_as_failure_without_following_it(self):
        self.response.status = 307
        self.response.getheaders.return_value = [('Location', 'https://example.invalid/replacement')]
        self.response.read.return_value = b'{"message":"redirect refused"}'
        with self.assertRaises(coordinator.CoordinatorError):
            coordinator._request(self.out, {}, self.arm, 'GET', '/api/catalog')
        saved = self.archived()
        self.assertEqual(307, saved['status'])
        self.assertEqual('{"message":"redirect refused"}', saved['response'])
        self.factory.assert_called_once()
        self.connection.request.assert_called_once()


if __name__ == '__main__':
    unittest.main()
