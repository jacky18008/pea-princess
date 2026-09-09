"""Offline migration regressions: real durable ledgers, no model or HTTP transport."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
sys.path.insert(0, str(ROOT / 'bench' / 'ab'))
import legacy_control as lc
import durable_run
import launch
import run as onboarding
import journeys
import personas
import worker_eval

USAGE = {'input_tokens': 10, 'cached_input_tokens': 2, 'output_tokens': 3}


def result(text='answer', usage=None, **kwargs):
    raw = '\n'.join(json.dumps(x) for x in [
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}},
        {'type': 'turn.completed', 'usage': USAGE if usage is None else usage}])
    return launch.LaunchResult(text=raw, stdout=raw, usage=USAGE, seconds=4,
                               exit_code=0, attempts=1, **kwargs)


class LegacyBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.out = self.root / 'durable'
        self.addCleanup(lambda: setattr(lc, '_ACTIVE', None))
        for target, name in ((lc, '_fingerprints'), (durable_run, 'source_fingerprint')):
            patcher = mock.patch.object(target, name, return_value={})
            patcher.start()
            self.addCleanup(patcher.stop)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        for redirect in (contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr)):
            redirect.__enter__()
            self.addCleanup(redirect.__exit__, None, None, None)

    def args(self, *extra):
        return ['--durable-dir', str(self.out), '--max-calls', '3',
                '--max-processed-tokens', '1000'] + list(extra)

    def entry(self, body):
        module = types.ModuleType('legacy_test')
        module.__file__ = 'fake_runner.py'
        module.body = body
        exec('''import argparse
import legacy_control as lc
def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('--model', default='gpt-5.6-terra')
    p.add_argument('--results')
    p.add_argument('--day')
    p.add_argument('--regrade')
    p.add_argument('--retry-failed')
    p.add_argument('--rules-only', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    lc.add_arguments(p)
    return p
@lc.entrypoint
def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.dry_run:
        return 0
    return body(a)
''', module.__dict__)
        return module.main

    def cli(self, prompt='prompt', model='gpt-5.6-terra'):
        lc.job('case-one')
        workdir = lc.workdir()
        return lc.run_cli(['codex', 'exec', '--json', '--model', model, '--', prompt],
                          workdir, 10, 'codex', label='target')

    def test_replay_restores_artifacts_without_a_second_paid_call(self):
        def invoke(cmd, cwd, *args, **kwargs):
            (Path(cwd) / 'profile.yaml').write_text('recorded answer')
            return result()
        seen = []
        def body(args):
            res = self.cli()
            seen.append((lc.reply_text(res, 'codex'), (Path(lc.workdir()) / 'profile.yaml').read_text()))
            self.assertEqual(str(self.out / 'results'), args.results)
            self.assertEqual('durable', args.day)
            return 0
        main = self.entry(body)
        with mock.patch.object(launch, 'run', side_effect=invoke) as paid:
            self.assertEqual(0, main(self.args()))
            saved = next((self.out / 'workdirs').iterdir()) / 'profile.yaml'
            saved.write_text('tampered after completion')
            self.assertEqual(0, main(self.args()))
        self.assertEqual(1, paid.call_count)
        self.assertEqual([('answer', 'recorded answer')] * 2, seen)
        self.assertTrue(json.loads((self.out / 'control' / 'checkpoint.json').read_text()))

    def test_unknown_usage_pauses_batch_and_replay_never_rebuys(self):
        def body(args):
            self.cli('first')
            self.cli('second')
            return 0
        main = self.entry(body)
        with mock.patch.object(launch, 'run', return_value=result(usage={'input_tokens': 10, 'output_tokens': 3})) as paid:
            self.assertEqual(2, main(self.args()))
            self.assertEqual(2, main(self.args()))
        self.assertEqual(1, paid.call_count)
        self.assertFalse((self.out / 'legacy-completed.json').exists())

    def test_missing_checkpoint_cannot_be_hidden_by_completed_marker(self):
        main = self.entry(lambda args: (self.cli(), 0)[1])
        with mock.patch.object(launch, 'run', return_value=result()) as paid:
            self.assertEqual(0, main(self.args()))
            (self.out / 'control' / 'checkpoint.json').unlink()
            self.assertEqual(2, main(self.args()))
        self.assertEqual(1, paid.call_count)

    def test_changed_request_refuses_replay(self):
        prompt = ['before']
        main = self.entry(lambda args: (self.cli(prompt[0]), 0)[1])
        with mock.patch.object(launch, 'run', return_value=result()) as paid:
            self.assertEqual(0, main(self.args()))
            prompt[0] = 'changed'
            self.assertEqual(2, main(self.args()))
        self.assertEqual(1, paid.call_count)

    def test_no_bounds_no_model_alias_or_claude_without_opt_in(self):
        main = self.entry(lambda args: (self.cli(model=args.model), 0)[1])
        with mock.patch.object(launch, 'run') as paid:
            self.assertEqual(2, main([]))
            self.assertEqual(2, main(self.args('--model', 'opus')))
            lc._ACTIVE = lc.Session(argparse.Namespace(durable_dir=str(self.root / 'c'), max_calls=1,
                max_total_tokens=100, allow_claude=False), 'test')
            with self.assertRaisesRegex(ValueError, 'paused'):
                lc.require_model('claude-sonnet-4-20250514', 'claude')
        paid.assert_not_called()

    def test_call_and_token_ceiling_stop_before_the_next_dispatch(self):
        def body(args):
            self.cli('first')
            self.cli('second')
            return 0
        main = self.entry(body)
        with mock.patch.object(launch, 'run', return_value=result()) as paid:
            self.assertEqual(2, main(['--durable-dir', str(self.out), '--max-calls', '1',
                                     '--max-processed-tokens', '100']))
        self.assertEqual(1, paid.call_count)
        self.out = self.root / 'token-capped'
        with mock.patch.object(launch, 'run', return_value=result()) as paid:
            self.assertEqual(2, main(self.args('--max-processed-tokens', '12')))
        self.assertEqual(1, paid.call_count)

    def test_recovery_writes_owned_copy_and_preserves_history_on_replay(self):
        source = self.root / 'history'
        (source / 'raw').mkdir(parents=True)
        original = source / 'raw' / 'row.json'
        original.write_text('historical failure')
        seen = []
        def body(args):
            copied = Path(args.retry_failed)
            seen.append((copied, (copied / 'raw' / 'row.json').read_text()))
            self.cli()
            (copied / 'raw' / 'row.json').write_text('new derived result')
            return 0
        main = self.entry(body)
        with mock.patch.object(launch, 'run', return_value=result()) as paid:
            self.assertEqual(0, main(self.args('--retry-failed', str(source))))
            self.assertEqual(0, main(self.args('--retry-failed', str(source))))
        self.assertEqual('historical failure', original.read_text())
        self.assertEqual(['historical failure'] * 2, [x[1] for x in seen])
        self.assertTrue(all(self.out in x[0].parents for x in seen))
        self.assertEqual(1, paid.call_count)

    def test_model_regrade_is_live_rules_regrade_is_offline(self):
        args = personas.build_parser().parse_args(['--regrade', '/saved'])
        self.assertFalse(lc.offline_args(args))
        args.rules_only = True
        self.assertTrue(lc.offline_args(args))
        args.rules_only, args.dry_run = False, True
        self.assertTrue(lc.offline_args(args))

    def test_actual_api_payload_is_frozen_and_dispatched_once(self):
        case = {'id': 'one', 'kind': 'conversation', 'prompt': 'hello'}
        system = ['frozen system']
        seen = []
        def submit(payload, timeout):
            seen.append(payload)
            return 'answer', {'prompt_tokens': 10, 'prompt_tokens_details': {'cached_tokens': 2},
                               'completion_tokens': 3}, None
        def body(args):
            self.assertEqual('answer', onboarding.run_api(case, args.model, '/unused', 10, conversation=True)[0])
            return 0
        main = self.entry(body)
        with mock.patch.object(onboarding, 'system_prompt', side_effect=lambda: list(system)), \
                mock.patch.object(onboarding, '_submit_api', side_effect=submit) as paid:
            self.assertEqual(0, main(self.args()))
            self.assertEqual(0, main(self.args()))
            system[0] = 'changed actual system message'
            self.assertEqual(2, main(self.args()))
        self.assertEqual(1, paid.call_count)
        self.assertIn('frozen system', seen[0]['messages'][0]['content'])

    def test_codex_reply_uses_assistant_text_not_usage_json(self):
        lc._ACTIVE = lc.Session(argparse.Namespace(), 'test')
        self.assertIn('--json', journeys.codex_command('q', '/tmp', 'gpt-5.6-terra'))
        self.assertIn('--json', personas.helper_command('codex', 'q', '/tmp', 'gpt-5.6-terra'))
        self.assertEqual('answer', lc.reply_text(result(), 'codex'))
        terminal = json.dumps({'type': 'turn.completed', 'usage': USAGE})
        self.assertEqual('', lc.reply_text(launch.LaunchResult(text=terminal, stdout=terminal), 'codex'))
        self.assertEqual('', lc.reply_text(launch.LaunchResult(text='[]', stdout='[]'), 'codex'))

    def test_missing_structured_telemetry_flags_stop_before_dispatch(self):
        def body(args):
            lc.job('preflight')
            lc.run_cli(['codex', 'exec', '--model', args.model, '--', '--json'],
                       lc.workdir(), 10, 'codex')
            return 0
        with mock.patch.object(launch, 'run') as paid:
            self.assertEqual(2, self.entry(body)(self.args()))
        paid.assert_not_called()
        self.assertEqual({}, json.loads((self.out / 'control' / 'checkpoint.json').read_text())['state']['calls'])

    def test_owned_path_ancestor_symlink_cannot_delete_or_create_outside(self):
        outside = self.root / 'outside'
        (outside / 'history-retry_failed').mkdir(parents=True)
        sentinel = outside / 'history-retry_failed' / 'keep.txt'
        sentinel.write_text('must survive')
        history = self.root / 'history'
        history.mkdir()
        (history / 'row.json').write_text('saved')
        self.out.mkdir()
        (self.out / 'results').symlink_to(outside, target_is_directory=True)
        main = self.entry(lambda args: self.fail('output symlink passed preflight'))
        self.assertEqual(2, main(self.args('--retry-failed', str(history))))
        self.assertEqual('must survive', sentinel.read_text())
        self.assertEqual(['history-retry_failed'], sorted(x.name for x in outside.iterdir()))
        (self.out / 'results').unlink()
        (self.out / 'workdirs').symlink_to(outside, target_is_directory=True)
        lc._ACTIVE = lc.Session(argparse.Namespace(durable_dir=str(self.root / 'fresh'), max_calls=1,
            max_total_tokens=100, allow_claude=False), 'owned')
        fresh = self.root / 'fresh'
        fresh.mkdir()
        (fresh / 'workdirs').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'inside|symlink'):
            lc.workdir()
        self.assertEqual(['history-retry_failed'], sorted(x.name for x in outside.iterdir()))

    def test_recovery_source_cannot_equal_or_contain_durable_directory(self):
        self.out.mkdir()
        lc._ACTIVE = lc.Session(argparse.Namespace(durable_dir=str(self.out), max_calls=1,
            max_total_tokens=100, allow_claude=False), 'owned')
        for source in (self.out, self.root):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'contain each other'):
                lc.recovery_copy(source, self.out / 'results' / 'copy')

    def test_real_onboarding_codex_entrypoint_replays_to_one_owned_scorecard_row(self):
        cases = self.root / 'cases.json'
        cases.write_text(json.dumps({'evals': [{'id': 'one', 'kind': 'conversation', 'prompt': 'hello',
                                               'files': [], 'expected_facts': {}}]}))
        argv = self.args('--agent', 'codex', '--model', 'gpt-5.6-terra', '--case', 'one', '--cases', str(cases))
        def invoke(cmd, cwd, *args, **kwargs):
            self.assertIn('--json', cmd)
            self.assertTrue(self.out in Path(cwd).parents)
            return result('plain assistant answer')
        old_results = onboarding.RESULTS
        self.addCleanup(setattr, onboarding, 'RESULTS', old_results)
        with mock.patch.object(launch, 'run', side_effect=invoke) as paid, \
                mock.patch.object(onboarding.grader, 'grade_conversation', return_value={'summary': 'ok'}):
            self.assertEqual(0, onboarding.main(argv))
            self.assertEqual(0, onboarding.main(argv))
        self.assertEqual(1, paid.call_count)
        card = self.out / 'results' / 'durable' / 'scorecard.json'
        self.assertEqual(1, len(json.loads(card.read_text())))
        answer = next((self.out / 'workdirs').iterdir()) / 'answer.txt'
        self.assertEqual('plain assistant answer', answer.read_text())

    def test_persona_latency_branch_is_identical_when_completed_calls_replay_fast(self):
        argv = self.args('--persona', 'C1', '--agent', 'codex', '--model', 'gpt-5.6-terra',
                         '--persona-agent', 'codex', '--persona-model', 'gpt-5.6-terra',
                         '--rules-only')
        slow = result('We can check the saved evidence.')._replace(seconds=11)
        with mock.patch.object(launch, 'run', return_value=slow) as paid, \
                mock.patch.object(personas, 'HARD_SESSION_TIMEOUT_S', 10), \
                mock.patch.object(personas, 'HARD_REPLY_TIMEOUT_S', 10000):
            self.assertEqual(1, personas.main(argv))
            count = paid.call_count
            first = json.loads(next((self.out / 'results' / 'personas-durable' / 'cards').glob('*.json')).read_text())
            self.assertEqual(1, personas.main(argv))
            second = json.loads(next((self.out / 'results' / 'personas-durable' / 'cards').glob('*.json')).read_text())
        self.assertEqual(2, count)  # target plus satisfaction; no persona continuation
        self.assertEqual(count, paid.call_count)
        self.assertEqual('timeout', first['outcome'])
        self.assertEqual(first['outcome'], second['outcome'])
        self.assertEqual(first['cost']['wall_time_s'], second['cost']['wall_time_s'])

    def test_ab_children_share_one_ledger_and_raw_files_cannot_skip_paid_failure(self):
        import run_ab
        import run_codex
        cases = self.root / 'cases.json'
        cases.write_text(json.dumps({'evals': [{'id': 'one', 'prompt': 'question', 'files': []}]}))
        configs = []
        for name in ('a', 'b'):
            path = self.root / (name + '.yaml')
            path.write_text('name: %s\nagent: codex\nmain_model: gpt-5.6-terra\n' % name)
            configs.append(str(path))
        argv = self.args('--configs', ','.join(configs), '--cases', str(cases), '--runs', '1', '--no-grade')
        children = []
        def child(argv):
            label = argv[argv.index('--config') + 1]
            children.append(label)
            self.cli(label)
            return 0
        with mock.patch.object(run_codex, 'main', side_effect=child), \
                mock.patch.object(run_ab.runner, 'raw_exists', return_value=True) as raw_exists, \
                mock.patch.object(launch, 'run', return_value=result(usage={'input_tokens': 10})) as paid:
            self.assertEqual(2, run_ab.main(argv))
            self.assertEqual(2, run_ab.main(argv))
        self.assertEqual(1, paid.call_count)
        self.assertEqual([configs[0], configs[0]], children)
        raw_exists.assert_not_called()

    def test_worker_live_cli_has_no_implicit_models_or_result_directory(self):
        args = worker_eval.build_parser().parse_args([])
        self.assertIsNone(args.models)
        self.assertIsNone(args.results)

    def test_source_fingerprints_include_referenced_documents_and_skill_override(self):
        # Restore the implementation for this focused input-inventory check.
        # The patcher's saved wrapped method is unavailable; inspect via a fresh isolated module.
        import importlib.util
        spec = importlib.util.spec_from_file_location('fingerprint_inventory', ROOT / 'bench' / 'legacy_control.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = self.root / 'document.txt'
        source.write_text('private input')
        tasks = self.root / 'tasks.json'
        tasks.write_text(json.dumps({'tasks': [{'input_path': str(source)}]}))
        skill = self.root / 'override.md'
        skill.write_text('pinned instructions')
        with mock.patch.dict('os.environ', {'VETFLAT_SKILL_MD_OVERRIDE': str(skill)}):
            fingerprints = module._fingerprints(argparse.Namespace(tasks=str(tasks)))
        self.assertIn(str(source), fingerprints)
        self.assertIn(str(skill), fingerprints)


if __name__ == '__main__':
    unittest.main()
