"""Synthetic/offline regression for the one supported interrupted persona pattern."""
import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import call_control
import durable_run
import launch
import legacy_control
import persona_recovery as recovery
import personas


def claude(text='你的學校在哪裡？你的預算包括帳單嗎？'):
    usage = {'input_tokens': 2, 'cache_read_input_tokens': 3,
             'cache_creation_input_tokens': 5, 'output_tokens': 4}
    raw = json.dumps({'type': 'result', 'is_error': False, 'result': text,
                      'session_id': 'synthetic-original-session', 'usage': usage})
    return launch.LaunchResult(text=text, usage=usage, seconds=27.94, exit_code=0,
                               session_id='synthetic-original-session', stdout=raw,
                               attempt_records=[{'attempt': 1, 'usage': usage, 'exit_code': 0}])


def codex(text):
    usage = {'input_tokens': 20, 'cached_input_tokens': 3, 'output_tokens': 4}
    raw = '\n'.join(json.dumps(e, ensure_ascii=False) for e in [
        {'type': 'thread.started', 'thread_id': 'synthetic-new-session'},
        {'type': 'turn.started'},
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}},
        {'type': 'turn.completed', 'usage': usage}])
    return launch.LaunchResult(text=raw, stdout=raw, usage=usage, seconds=1.2,
                               exit_code=0, attempt_records=[{'attempt': 1, 'usage': usage, 'exit_code': 0}])


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'evals').mkdir()
        shutil.copyfile(ROOT / 'evals/personas.json', self.root / 'evals/personas.json')
        shutil.copytree(ROOT / 'evals/personas/fixtures/C1', self.root / 'evals/personas/fixtures/C1')
        (self.root / '.pea-playground').mkdir(mode=0o700)
        self.source = self.root / '.pea-playground/original'
        self.destination = self.root / '.pea-playground/recovered'
        self.stack = ExitStack()
        self.stack.enter_context(mock.patch.object(recovery, 'ROOT', self.root))
        self.stack.enter_context(mock.patch.object(legacy_control, 'ROOT', self.root))
        self.stack.enter_context(mock.patch.object(personas, 'FIXTURES', str(self.root / 'evals/personas/fixtures')))
        self.stack.enter_context(mock.patch.dict(os.environ, {k: '' for k in recovery.ENV}))
        self.addCleanup(self.stack.close)
        self.addCleanup(self.temp.cleanup)
        args = personas.build_parser().parse_args([
            '--persona', 'C1', '--seed', '1', '--model', 'claude-sonnet-5',
            '--persona-model', 'gpt-5.6-terra', '--judge-model', 'gpt-5.6-sol',
            '--personas', str(self.root / 'evals/personas.json'), '--timeout', '900',
            '--durable-dir', str(self.source), '--max-calls', '30',
            '--max-total-tokens', '1500000', '--allow-claude'])
        session = legacy_control.Session(args, 'personas.py')
        session.ensure()
        card = personas.variant_of(personas.card_by_id(personas.load_personas(args.personas), 'C1'), False)
        seen = []
        def invoke(command, cwd, timeout, family, **kwargs):
            seen.append(command)
            if len(seen) == 1:
                return claude()
            error = "[Errno 2] No such file or directory: '%s'" % cwd
            return launch.LaunchResult(note="could not start 'codex': " + error,
                attempt_records=[{'attempt': 1, 'usage': None, 'exit_code': None,
                                  'start_error': error, 'timeout': False}])
        with mock.patch.object(legacy_control, '_ACTIVE', session), \
                mock.patch.object(personas, 'system_prompt', return_value='FROZEN ORIGINAL SYSTEM'), \
                mock.patch.object(personas.journeys, 'claude_supports_resume', return_value=(True, 'synthetic')), \
                mock.patch.object(launch, 'run', side_effect=invoke), redirect_stdout(io.StringIO()):
            with self.assertRaises(call_control.CallControlPaused):
                personas.play(card, args, 'baseline', 1)
        self.original_inventory = recovery._inventory(self.source)

    def prepare(self):
        with mock.patch.object(launch, 'run', side_effect=AssertionError('offline prepare dispatched')), redirect_stderr(io.StringIO()):
            result = recovery.prepare(self.source, self.destination)
        self.assertTrue(result['ok'])
        return result

    def test_offline_prepare_replays_controller_and_pins_exact_helper(self):
        result = self.prepare()
        self.assertEqual(result['new_max_calls'], 28)
        self.assertEqual(result['remaining_known_token_allowance'], 1500000 - 14)
        self.assertEqual(recovery._inventory(self.source), self.original_inventory)
        self.assertEqual(recovery._inventory(self.destination / 'original'), self.original_inventory)
        proof = json.loads((self.destination / 'reconstruction.json').read_text())
        self.assertIn('first_persona_request_sha256', proof)
        state = recovery._envelope(self.destination / 'continuation/control/checkpoint.json', 'state', 'state_sha256')
        self.assertEqual(state['calls'], {})
        self.assertEqual(len(state['planned_call_ids']), 28)
        self.assertEqual((self.destination / 'recovery.json').stat().st_mode & 0o777, 0o600)

    def test_reuses_first_reply_once_then_new_claude_full_transcript(self):
        self.prepare()
        commands = []
        responses = iter([codex('謝謝，請先說明找房步驟。'), claude('先確認合約與預算。'),
                          codex('4\n暫時沒有'), codex('{"criteria": [], "summary": "synthetic"}')])
        def invoke(command, cwd, timeout, family, **kwargs):
            self.assertTrue(Path(cwd).is_dir())
            self.assertEqual(kwargs['attempts'], 1)
            commands.append(command)
            return next(responses)
        with mock.patch.object(launch, 'run', side_effect=invoke), redirect_stderr(io.StringIO()):
            result = recovery.run(self.destination, True)
        self.assertTrue(result['ok'], result.get('error'))
        self.assertEqual(result['new_calls'], 4)
        self.assertEqual(result['combined_calls'], 6)
        self.assertEqual(result['conversation_outcome'], 'abandoned')
        self.assertEqual(commands[0][0], 'codex')
        agent = commands[1]
        self.assertNotIn('--resume', agent)
        self.assertNotIn('--session-id', agent)
        self.assertEqual(agent[agent.index('--append-system-prompt') + 1], 'FROZEN ORIGINAL SYSTEM')
        self.assertIn(claude().text, agent[-1])
        self.assertIn('謝謝，請先說明找房步驟。', agent[-1])
        self.assertIsNone(result['combined_usage']['total_tokens'])
        self.assertEqual(result['combined_usage']['unknown_input_tokens_requests'], 1)
        self.assertEqual(result['combined_usage']['known_input_tokens'], 10 + 3 * 20 + 10)
        record = json.loads((self.destination / 'conversation.json').read_text())
        self.assertEqual(record['dialogue'][0]['assistant'], claude().text)
        self.assertIn('old frozen-system', record['recovery']['quality_scope'])
        with self.assertRaises(ValueError), mock.patch.object(launch, 'run') as dispatch:
            recovery.run(self.destination, True)
        dispatch.assert_not_called()
        self.assertEqual(recovery._inventory(self.source), self.original_inventory)

    def test_failure_stops_without_retry_and_keeps_incremental_trace(self):
        self.prepare()
        failure = launch.LaunchResult(provider_error=True, exit_code=1,
            stderr='rate limit', note='rate limit', attempts=1,
            attempt_records=[{'attempt': 1, 'usage': None, 'exit_code': 1}])
        with mock.patch.object(launch, 'run', return_value=failure) as dispatch, redirect_stderr(io.StringIO()):
            result = recovery.run(self.destination, True)
        self.assertFalse(result['ok'])
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(result['combined_calls'], 3)
        self.assertEqual(result['combined_usage']['unknown_input_tokens_requests'], 2)
        self.assertIn(claude().text, (self.destination / 'conversation-trace.md').read_text())
        self.assertTrue((self.destination / 'actor-trace/0002-result.json').is_file())
        self.assertEqual(recovery._inventory(self.source), self.original_inventory)

    def test_requires_explicit_claude_permission(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, 'allow-claude'), mock.patch.object(launch, 'run') as dispatch:
            recovery.run(self.destination)
        dispatch.assert_not_called()
        self.assertFalse((self.destination / 'run-started.json').exists())

    def test_deleted_future_fixture_rejected_before_prepare(self):
        (self.root / 'evals/personas/fixtures/C1/listing-full.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'fixture file set'), mock.patch.object(launch, 'run') as dispatch:
            recovery.prepare(self.source, self.destination)
        dispatch.assert_not_called()
        self.assertFalse(self.destination.exists())

    def test_changed_fixture_and_added_file_rejected(self):
        target = self.root / 'evals/personas/fixtures/C1/listing-full.txt'
        target.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'fixture changed'):
            recovery.prepare(self.source, self.destination)

    def test_snapshot_changed_between_calls_stops_and_is_not_success(self):
        self.prepare()
        def invoke(*args, **kwargs):
            (self.destination / 'original/run.lock').write_text('changed')
            return codex('謝謝，請先說明找房步驟。')
        with mock.patch.object(launch, 'run', side_effect=invoke) as dispatch, redirect_stderr(io.StringIO()):
            result = recovery.run(self.destination, True)
        self.assertFalse(result['ok'])
        self.assertFalse(result['original_unchanged'])
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(recovery._inventory(self.source), self.original_inventory)

    def test_pending_new_physical_record_is_never_retried(self):
        self.prepare()
        # A crashed physical dispatch with no completion remains unknown.
        args = recovery._args(recovery._envelope(self.destination / 'recovery.json'), self.destination)
        session = legacy_control.Session(args, 'persona_recovery.py')
        session.ensure()
        session.controller.control.dispatch('call-000001', recovery.JOB, 'turn 2 persona', 'legacy')
        with mock.patch.object(launch, 'run') as dispatch:
            with self.assertRaisesRegex(ValueError, 'already dispatched'):
                recovery.run(self.destination, True)
        dispatch.assert_not_called()

    def test_changed_original_and_snapshot_block_run(self):
        self.prepare()
        (self.source / 'run.lock').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'original evidence'), mock.patch.object(launch, 'run') as dispatch:
            recovery.run(self.destination, True)
        dispatch.assert_not_called()

    def test_command_mismatch_fails_before_dispatch(self):
        # Controller drift is detected in offline reconstruction, including latency effects.
        original = personas.persona_prompt
        with mock.patch.object(personas, 'persona_prompt', side_effect=lambda *a: original(*a) + ' changed'), \
                mock.patch.object(launch, 'run') as dispatch, redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'reconstructed original request'):
                recovery.prepare(self.source, self.destination)
        dispatch.assert_not_called()

    def test_corrupt_record_and_unsupported_plan_rejected(self):
        path = self.source / 'control/checkpoint.json'
        envelope = json.loads(path.read_text())
        envelope['state']['calls']['call-000001']['record']['launch_result']['text'] = 'corrupted'
        path.write_text(json.dumps(envelope))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            recovery.prepare(self.source, self.destination)

    def test_validly_hashed_multi_job_manifest_is_not_supported(self):
        path = self.source / 'run.json'
        value = recovery._envelope(path)
        value['config']['arguments']['matrix'] = 'pilot'
        path.write_text(json.dumps({'value': value, 'sha256': call_control._digest(value)}))
        with self.assertRaisesRegex(ValueError, 'unsupported persona'), mock.patch.object(launch, 'run') as dispatch:
            recovery.prepare(self.source, self.destination)
        dispatch.assert_not_called()

    def test_new_destination_only_and_no_symlinks(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(ValueError, 'new private'):
            recovery.prepare(self.source, self.destination)
        alias = self.root / '.pea-playground/alias'
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            recovery.prepare(alias, self.root / '.pea-playground/other')


if __name__ == '__main__':
    unittest.main()
