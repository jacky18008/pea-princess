"""Offline operational amendment tests against real frozen source and ledger code."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bench'))
import conversation_ablation as current_runner
import conversation_resume as operational


def paid(tokens=110):
    return {'status': 'complete', 'exit_code': 0, 'timeout': False,
            'errors': [], 'tool_events': [], 'malformed_event_lines': 0,
            'terminal_usage_events': 1, 'direct_terminal_usage': {
                'input_tokens': tokens - 10, 'cached_input_tokens': 0, 'output_tokens': 10},
            'answer': 'Synthetic response saved for the offline experiment.'}


class ConversationResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'frozen-source'
        self.source.mkdir()
        for name in current_runner.SOURCES:
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if name != 'dist/pea-princess-skill.zip':
                shutil.copyfile(ROOT / name, target)
        with zipfile.ZipFile(self.source / 'dist/pea-princess-skill.zip', 'w') as archive:
            archive.writestr('pea-princess/SKILL.md', 'Synthetic public skill entry\n')
            archive.writestr('pea-princess/references/inputs.md', 'Synthetic input guide\n')
            archive.writestr('pea-princess/references/onboarding.md', 'Synthetic onboarding guide\n')
        self.original = operational._load_frozen(self.source)
        self.output = self.root / 'run'
        with mock.patch.object(self.original.subprocess, 'check_output', return_value='e' * 40 + '\n'):
            self.original.prepare(self.output)
        self.plan = self.original.read(self.output / 'plan.json')
        self.amendment_path = self.root / 'budget-0001.json'
        self.amendment = {'version': 1, 'amendment_id': 'budget-0001',
            'operation': 'complete_original_frozen_plan', 'original_plan_sha256': operational._digest(self.plan),
            'source_commit': self.plan['source_commit'], 'original_token_ceiling': 6000000,
            'amended_token_ceiling': None, 'max_cli_invocations': 192,
            'schedule_sha256': operational._digest(self.plan['calls']), 'automatic_retries': 0,
            'claude_calls': 0, 'previous_amendment_sha256': None,
            'authorization': {'actor': 'user', 'quote': 'Offline exact user authorization fixture.\nKeep this newline.',
                              'source': 'offline-user-request', 'authorized_at': '2026-09-09T20:00:00+01:00'}}
        self.write_amendment(self.amendment)

    def write_amendment(self, value):
        self.amendment_path.write_bytes(operational._json(value))

    def resume(self):
        return operational.Resume(self.source, self.output, self.amendment_path)

    def originals(self):
        names = ['plan.json', 'frozen.json', 'scenario.json', 'rubric.json']
        return {name: (self.output / name).read_bytes() for name in names}

    def test_resume_crosses_old_threshold_keeps_exact_request_receipt_and_original_manifests(self):
        first = self.original.run_next(self.output, invoke=mock.Mock(return_value=paid(6000000)))
        first_id = first['just_completed']
        receipt = self.output / 'records' / first_id / 'native-record.json'
        old_receipt = receipt.read_bytes()
        originals = self.originals()
        blocked = mock.Mock(side_effect=AssertionError('old runner must stop at its original ceiling'))
        with self.assertRaises(ValueError):
            self.original.run_next(self.output, invoke=blocked)
        blocked.assert_not_called()
        next_call = self.plan['calls'][1]
        expected, _, _ = self.original.answer_request(self.output, self.plan, next_call)
        captured = []
        def fake(request, folder, work):
            captured.append(copy.deepcopy(request))
            self.assertTrue((self.output / 'resume-audit/budget-0001.json').exists())
            return paid()
        resumed = self.resume()
        result = resumed.step(invoke=fake)
        self.assertEqual([expected], captured)
        self.assertEqual(next_call['id'], result['just_completed'])
        self.assertEqual(6000110, result['usage']['total_tokens'])
        self.assertEqual(2, result['dispatched_calls'])
        self.assertEqual(192, result['planned_calls'])
        self.assertEqual(originals, self.originals())
        self.assertEqual(old_receipt, receipt.read_bytes())
        self.assertEqual(6000000, json.loads(originals['plan.json'])['processed_token_stop_before_next_call'])
        audit = self.original.read(self.output / 'resume-audit/budget-0001.json')
        self.assertIsNone(audit['amended_token_ceiling'])
        self.assertEqual(operational._digest(self.amendment), audit['amendment_sha256'])
        self.assertNotIn(self.amendment['authorization']['quote'], json.dumps(audit))
        self.assertEqual(0o600, (self.output / 'resume-audit/budget-0001.json').stat().st_mode & 0o777)

    def test_wrong_or_missing_amendments_fail_before_ledger_access(self):
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        changes = [{'original_plan_sha256': '0' * 64}, {'source_commit': '0' * 40},
                   {'original_token_ceiling': 6000001}, {'amended_token_ceiling': 60000000},
                   {'max_cli_invocations': 193}, {'schedule_sha256': '0' * 64},
                   {'automatic_retries': 1}, {'claude_calls': 1}, {'amendment_id': '../escape'},
                   {'authorization': self.amendment['authorization'] | {'quote': ''}},
                   {'authorization': self.amendment['authorization'] | {'actor': 'tool'}},
                   {'authorization': self.amendment['authorization'] | {'authorized_at': '2026-09-09T20:00:00'}}]
        for change in changes:
            with self.subTest(change=list(change)):
                self.write_amendment(self.amendment | change)
                with self.assertRaises(operational.ResumeError):
                    self.resume()
                self.assertEqual(before, checkpoint.read_bytes())
        self.amendment_path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.resume()
        self.assertEqual(before, checkpoint.read_bytes())
        self.assertFalse((self.output / 'resume-audit').exists())

    def test_pause_blocks_callback_and_audit_creation_without_rewriting_ledger(self):
        (self.output / 'PAUSE_REQUESTED.json').write_text('{}')
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        fake = mock.Mock(side_effect=AssertionError('paused resume must not invoke'))
        result = self.resume().step(invoke=fake)
        self.assertTrue(result['operator_paused'])
        fake.assert_not_called()
        self.assertEqual(before, checkpoint.read_bytes())
        self.assertFalse((self.output / 'resume-audit').exists())

    def test_external_pause_guard_works_for_source_without_builtin_pause_branch(self):
        resumed = self.resume()
        # The original e001e06 runner reaches verify_plan inside its exclusive
        # lock. Simulate that entry without the later built-in pause-file guard.
        def original_entry(output, roles, invoke):
            with resumed.runner.exclusive(output):
                resumed.runner.verify_plan(output)
                return invoke({}, None, None)
        resumed.runner.run_next = original_entry
        (self.output / 'PAUSE_REQUESTED.json').write_text('{}')
        fake = mock.Mock(side_effect=AssertionError('external pause must stop old runner'))
        result = resumed.step(invoke=fake)
        self.assertTrue(result['operator_paused'])
        fake.assert_not_called()

    def test_pending_or_failed_invocation_is_never_retried(self):
        first = self.plan['calls'][0]
        control = self.original.CallControl(self.output / 'controller', [c['id'] for c in self.plan['calls']], allow_tools=True)
        control.dispatch(first['id'], first['session'], first['role'], 'native')
        fake = mock.Mock(side_effect=AssertionError('pending invocation must not repeat'))
        resumed = self.resume()
        with self.assertRaises(ValueError):
            resumed.step(invoke=fake)
        fake.assert_not_called()
        control.complete(first['id'], paid() | {'status': 'stopped', 'errors': [{'type': 'offline-failure'}]})
        with self.assertRaises(ValueError):
            self.resume().step(invoke=fake)
        fake.assert_not_called()
        self.assertEqual(1, control.report()['dispatched_calls'])

    def test_unknown_usage_still_blocks_after_token_ceiling_is_removed(self):
        resumed = self.resume()
        fake = mock.Mock(return_value=paid() | {'terminal_usage_events': 0, 'direct_terminal_usage': None})
        with self.assertRaises(Exception):
            resumed.step(invoke=fake)
        with self.assertRaises(ValueError):
            self.resume().step(invoke=fake)
        self.assertEqual(1, fake.call_count)
        self.assertIsNone(resumed.status()['usage']['total_tokens'])

    def test_amendment_change_after_first_dispatch_is_rejected(self):
        resumed = self.resume()
        resumed.step(invoke=mock.Mock(return_value=paid()))
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        changed = copy.deepcopy(self.amendment)
        changed['authorization']['quote'] += ' changed'
        self.write_amendment(changed)
        fake = mock.Mock(side_effect=AssertionError('changed amendment must block'))
        with self.assertRaises(operational.ResumeError):
            resumed.step(invoke=fake)
        fake.assert_not_called()
        self.assertEqual(before, checkpoint.read_bytes())

    def test_missing_audit_after_creation_fails_closed(self):
        resumed = self.resume()
        resumed.step(invoke=mock.Mock(return_value=paid()))
        (self.output / 'resume-audit/budget-0001.json').unlink()
        with self.assertRaises(operational.ResumeError):
            self.resume()

    def test_frozen_imports_do_not_use_already_imported_current_checkout(self):
        before = sys.modules['conversation_native']
        resumed = self.resume()
        self.assertIs(before, sys.modules['conversation_native'])
        self.assertIsNot(before, resumed.runner.native)
        self.assertEqual(self.source / 'bench/conversation_native.py', Path(resumed.runner.native.__file__))
        source = self.source / 'bench/launch.py'
        source.write_text(source.read_text() + '\n# unexpected source change\n')
        with self.assertRaises(operational.ResumeError):
            self.resume()

    def test_status_is_offline_and_does_not_create_audit_or_rewrite_originals(self):
        originals = self.originals()
        checkpoint = self.output / 'controller/checkpoint.json'
        before = checkpoint.read_bytes()
        resumed = self.resume()
        with mock.patch.object(resumed.runner.native, 'invoke', side_effect=AssertionError('status is offline')):
            result = resumed.status()
        self.assertEqual(0, result['dispatched_calls'])
        self.assertEqual('budget-0001', result['operational_amendment'])
        self.assertIsNone(result['amended_token_ceiling'])
        self.assertEqual(before, checkpoint.read_bytes())
        self.assertEqual(originals, self.originals())
        self.assertFalse((self.output / 'resume-audit').exists())


if __name__ == '__main__':
    unittest.main()
