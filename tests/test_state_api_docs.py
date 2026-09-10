"""Run the shipped state API examples using a detached synthetic installation."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/vet-flat'
DOC = SKILL / 'references/state-api.md'


class StateApiDocumentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.skill = self.root / 'detached skill'
        self.project = self.root / 'private rental project'
        self.project.mkdir()
        for relative in ('scripts/session_state.py', 'references/state-api.md',
                         'references/session-harness.md'):
            target = self.skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SKILL / relative, target)
        self.env = dict(os.environ, PEA_SKILL=str(self.skill), PEA_PROJECT=str(self.project))
        self.doc = (self.skill / 'references/state-api.md').read_text()

    def blocks(self, language, count):
        blocks = re.findall(r'^```' + language + r'\n(.*?)^```', self.doc, re.M | re.S)
        self.assertEqual(len(blocks), count)
        return blocks

    def block(self, language):
        return self.blocks(language, 1)[0]

    def invoke(self, command, input_text=None, expected=0):
        result = subprocess.run(command, cwd=self.project, env=self.env, input=input_text,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stderr)
        return json.loads(result.stdout if expected == 0 else result.stderr)

    def cli(self, *args, **kwargs):
        return self.invoke([sys.executable, str(self.skill / 'scripts/session_state.py'),
                            '--project', str(self.project), *args], **kwargs)

    def test_python_example_preserves_updates_conditional_scope_and_raw_requests(self):
        packet = self.invoke([sys.executable, '-c', self.block('python')])
        rows = packet['requirements']
        self.assertEqual(rows['monthly-total']['value'],
                         {'amount': 1600, 'currency': 'GBP', 'period': 'month'})
        self.assertEqual(rows['monthly-total']['budget_scope'], 'rental')
        self.assertEqual(rows['floor']['strength'], 'prohibit')
        self.assertEqual(rows['floor']['scope'], 'all candidates')
        self.assertEqual(rows['floor']['exceptions'], [
            'Only candidate demo-flat may be ground floor if an independent inspection confirms it is dry.'])
        self.assertEqual(rows['floor-demo']['strength'], 'conditional')
        self.assertEqual(rows['floor-demo']['scope'], 'candidate:demo-flat')
        self.assertEqual(rows['floor-demo']['predicate'],
                         'An independent inspection confirms candidate demo-flat is dry.')
        self.assertEqual(packet['pending_requests'], {})
        self.assertEqual(packet['budgets'], {})
        self.assertEqual(packet['decisions'], {})
        self.assertEqual(self.cli('context', '--max-chars', '32000'), packet)
        state = self.cli('show')
        self.assertEqual(state['requests']['u1']['text'],
                         'Monthly total at most GBP 1500. No ground-floor homes.')
        self.assertEqual(state['requests']['u2']['resolution'], 'applied')
        journal = json.loads((self.project / '.pea-state/events.json').read_text())
        amounts = [entry['event'].get('value', entry['event'].get('changes', {}).get('value'))['amount']
                   for entry in journal['events'] if entry['event'].get('id') == 'monthly-total']
        self.assertEqual(amounts, [1500, 1600])
        manifest = json.loads((self.project / '.pea-state/checkpoint.json').read_text())
        self.assertEqual(manifest['packet'], packet)
        self.assertEqual(manifest['revision'], state['revision'])
        self.assertTrue(self.cli('verify')['checkpoint']['current'])
        self.assertFalse((self.skill / '.pea-state').exists())

    def test_cli_examples_apply_one_event_with_observed_revision_and_support_stdin(self):
        commands = [line for line in self.blocks('bash', 2)[0].splitlines() if line.strip()]
        self.assertEqual(len(commands), 5)
        initial = self.invoke(['bash', '-c', commands[0]])
        packet = self.invoke(['bash', '-c', commands[1]])
        self.assertEqual(packet['revision'], initial['revision'])
        raw = 'Keep this exact text: £2,250; literal $(never-run) and `never-run`.\nDo not normalize it. '
        event = {'op': 'request.capture', 'id': 'cli-u1', 'source': 'synthetic-user', 'text': raw}
        event_path = self.project / 'private event.json'
        event_path.write_text(json.dumps(event, ensure_ascii=False))
        self.env.update(PEA_REVISION=str(packet['revision']), PEA_EVENT_FILE=str(event_path))
        captured = self.invoke(['bash', '-c', commands[2]])
        self.assertEqual(captured['requests']['cli-u1']['text'], raw)
        resolved = self.cli('apply', '--expected-revision', str(captured['revision']),
                            input_text=json.dumps({'op': 'request.resolve', 'id': 'cli-u1',
                                                   'resolution': 'no_change',
                                                   'note': 'This synthetic parser check contains no rental update.'}))
        manifest = self.invoke(['bash', '-c', commands[3]])
        checked = self.invoke(['bash', '-c', commands[4]])
        self.assertEqual(manifest['revision'], resolved['revision'])
        self.assertEqual(checked['revision'], resolved['revision'])
        self.assertTrue(checked['checkpoint']['current'])
        event['id'] = 'cli-u2'
        rejected = self.cli('apply', '--expected-revision', str(initial['revision']),
                            input_text=json.dumps(event), expected=2)
        self.assertEqual(rejected['error'], 'RevisionConflict')
        self.assertEqual(self.cli('show')['revision'], resolved['revision'])

    def test_receipt_example_uses_observed_revision_then_returns_complete_context(self):
        before = self.invoke([sys.executable, '-c', self.block('python')])
        commands = [line for line in self.blocks('bash', 2)[1].splitlines() if line.strip()]
        self.assertEqual(len(commands), 2)
        raw = 'Keep every current condition, including the conditional dryness check.'
        event = {'op': 'request.capture', 'id': 'receipt-u1', 'source': 'synthetic-user', 'text': raw}
        event_path = self.project / 'private receipt event.json'
        event_path.write_text(json.dumps(event, ensure_ascii=False))
        self.env.update(PEA_REVISION=str(before['revision']), PEA_EVENT_FILE=str(event_path))
        receipt = self.invoke(['bash', '-c', commands[0]])
        packet = self.invoke(['bash', '-c', commands[1]])
        self.assertEqual(receipt, dict(ok=True, schema_version=packet['schema_version'],
                                      project_id=packet['project_id'], revision=packet['revision'],
                                      event_hash=packet['event_hash']))
        self.assertEqual(receipt['revision'], before['revision'] + 1)
        self.assertNotIn(raw, json.dumps(receipt))
        self.assertEqual(packet, self.cli('context', '--max-chars', '32000'))
        self.assertEqual(packet['requirements'], before['requirements'])
        self.assertEqual(packet['pending_requests']['receipt-u1']['text'], raw)
        self.assertEqual(packet['requirements']['floor-demo']['predicate'],
                         'An independent inspection confirms candidate demo-flat is dry.')
        checked = self.cli('verify')
        self.assertTrue(checked['ok'])
        self.assertEqual(checked['revision'], receipt['revision'])
        self.assertEqual(checked['event_hash'], receipt['event_hash'])
        self.assertFalse((self.skill / '.pea-state').exists())

    def test_todo_event_is_valid_after_the_documented_requirement_sequence(self):
        self.invoke([sys.executable, '-c', self.block('python')])
        matched = re.findall(r'`(\{"op":"task\.add"[^`]+\})`', self.doc)
        self.assertEqual(len(matched), 1)
        state = self.cli('show')
        result = self.cli('apply', '--expected-revision', str(state['revision']), input_text=matched[0])
        task = result['tasks']['check-demo']
        self.assertEqual(task['requirement_ids'], ['floor-demo'])
        self.assertEqual(task['status'], 'pending')
        self.assertFalse(task['valid'])

    def test_portable_reference_links_resolve_without_repository_docs(self):
        self.assertFalse((self.root / 'docs').exists())
        for name in ('state-api.md', 'session-harness.md'):
            source = self.skill / 'references' / name
            links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', source.read_text())
            self.assertTrue(links)
            for link in links:
                if '://' not in link:
                    target = (source.parent / link).resolve()
                    self.assertTrue(target.is_file(), link)
                    self.assertTrue(self.skill in target.parents)
        protocol = (self.skill / 'references/session-harness.md').read_text()
        self.assertIn('[state-api.md](state-api.md)', protocol)
        self.assertNotIn('complete usage guide is `docs/session-harness.md`', protocol)


if __name__ == '__main__':
    unittest.main()
