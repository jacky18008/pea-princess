"""Offline process transport and post-call research-observation failure checks."""
import copy
import json
from agent_reply_fixture import attach_claims
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import persona_playground as playground
import area_scan_store as scans


class ResearchTransportTests(unittest.TestCase):
    def test_two_calls_share_only_the_session_result_directory_and_keep_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session = root / ('a' * 32)
            session.mkdir(mode=0o700)
            other = root / ('b' * 32)
            other.mkdir(mode=0o700)
            result_dir = session / 'research-results'
            seen = []
            payload = b'Synthetic retained street evidence.\n'
            # This small Python child replaces Codex; it never uses a model or network.
            child = '''
import json, os, sys
from pathlib import Path
sys.stdin.read()
assert os.environ['VETFLAT_RESEARCH_DEPTH'] == 'deep'
target = Path(os.environ['VETFLAT_SCAN_RESULT_DIR'])
assert str(target) == sys.argv[2]
saved = target / 'retained-evidence.txt'
payload = b'Synthetic retained street evidence.\\n'
if sys.argv[3] == '1':
    descriptor = os.open(str(saved), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(payload)
else:
    assert saved.read_bytes() == payload
Path(sys.argv[1]).write_text('Retained result is available.', encoding='utf-8')
print(json.dumps({'type':'turn.completed','usage':{
    'input_tokens':15,'cached_input_tokens':5,'output_tokens':5}}))
'''

            def start(command, **kwargs):
                seen.append({'command': list(command), 'cwd': Path(kwargs['cwd']),
                             'env': copy.deepcopy(kwargs['env'])})
                answer = command[command.index('--output-last-message') + 1]
                return subprocess.Popen([sys.executable, '-c', child, answer,
                                         str(result_dir), str(len(seen))], **kwargs)

            request = {'model': 'gpt-5.6-terra', 'prompt': 'Private synthetic stdin input.',
                       'tool_policy': 'live_research', 'timeout_seconds': 10,
                       'execution_settings': playground.playground_settings.configured(
                           {'research_depth': 'deep', 'reasoning_effort': 'low'}, 'live')}
            with mock.patch.object(playground.shutil, 'which', return_value='/fake/codex'), \
                    mock.patch.object(playground.launch, 'start_process', side_effect=start), \
                    mock.patch.object(playground.launch, 'run', side_effect=AssertionError('model calls forbidden')), \
                    mock.patch.dict(os.environ, {'VETFLAT_SCAN_RESULT_DIR': str(other),
                                                  'VETFLAT_RESEARCH_DEPTH': 'lite'}):
                for number in (1, 2):
                    folder = session / '.pea-state' / 'runs' / ('call-%03d-assistant' % number)
                    folder.mkdir(parents=True, mode=0o700)
                    result = playground.codex_invoke(copy.deepcopy(request), folder)
                    self.assertEqual(0, result['exit_code'])
                    self.assertEqual('Retained result is available.', result['answer'])
                    self.assertEqual({'input_tokens': 15, 'cached_input_tokens': 5, 'output_tokens': 5},
                                     result['direct_terminal_usage'])
                    self.assertEqual(payload, (result_dir / 'retained-evidence.txt').read_bytes())

            self.assertEqual(2, len(seen))
            self.assertNotEqual(seen[0]['cwd'], seen[1]['cwd'])
            for call in seen:
                command = call['command']
                granted = [command[i + 1] for i, arg in enumerate(command) if arg == '--add-dir']
                self.assertEqual([str(result_dir)], granted)
                for forbidden in (root, session, session / '.pea-state', other):
                    self.assertNotIn(str(forbidden), granted)
                self.assertEqual(['multi_agent'], [command[i + 1] for i, arg in enumerate(command)
                                                   if arg == '--disable'])
                self.assertEqual('workspace-write', command[command.index('--sandbox') + 1])
                self.assertEqual(str(result_dir), call['env']['VETFLAT_SCAN_RESULT_DIR'])
                self.assertEqual('deep', call['env']['VETFLAT_RESEARCH_DEPTH'])
                self.assertEqual(str(call['cwd'] / '.pea-cache'), call['env']['VETFLAT_CACHE'])
                self.assertEqual('1', call['env']['PYTHONDONTWRITEBYTECODE'])
                self.assertNotIn(request['prompt'], command)
                self.assertFalse(call['cwd'].exists(), 'Per-call scratch directory should be removed')
            self.assertEqual(0o700, result_dir.stat().st_mode & 0o777)
            self.assertEqual(0o600, (result_dir / 'retained-evidence.txt').stat().st_mode & 0o777)
            self.assertEqual([], list(other.iterdir()))


class ResearchObservationWriteTests(unittest.TestCase):
    def test_observation_write_failure_keeps_paid_reply_and_original_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            invocations, observation_writes, saved_scans = [], [], []
            answer = json.dumps({'message': 'The saved evidence supports this comparison.', 'questions': []})

            def invoke(request, folder):
                invocations.append(copy.deepcopy(request))
                directory = playground.playground_research.from_call(folder)
                output = {'schema': 'vet-flat/area-scan/2', 'ok': True, 'reading': ['Synthetic observation'],
                          'retrieved_at': '2026-09-12T00:00:00Z', 'not_found': [], 'sources': []}
                saved = scans.run(directory, {'postcode': 'W6 0PJ', 'depth': 'standard',
                                              'requested_depth': 'standard'}, 'synthetic-source',
                                  lambda: output, lambda: '2026-09-12T00:00:00Z')
                path = Path(saved['saved_to'])
                saved_scans.append((path, path.read_bytes()))
                raw = json.dumps({'type': 'turn.completed', 'usage': {
                    'input_tokens': 15, 'cached_input_tokens': 5, 'output_tokens': 5}}) + '\n'
                record = playground.cli_record('answer', playground.launch.LaunchResult(
                    stdout=raw, exit_code=0, seconds=0.01), 'codex')
                return dict(record, answer=json.dumps(attach_claims(json.loads(answer),request)))

            original_write = playground._atomic_json

            def write(path, value):
                if Path(path).parent.name == 'research-observations':
                    observation_writes.append(Path(path))
                    raise OSError('Synthetic observation write failure')
                return original_write(path, value)

            with mock.patch.object(playground, 'source_hashes', return_value={'fixed': 'synthetic'}), \
                    mock.patch.object(playground.launch, 'start_process', side_effect=AssertionError('model calls forbidden')), \
                    mock.patch.object(playground.launch, 'run', side_effect=AssertionError('model calls forbidden')):
                lab = playground.Lab(root, invoke=invoke)
                try:
                    sid = lab.create({'client_id': str(uuid.uuid4()), 'research_mode': 'live',
                                      'output_mode': 'agent', 'initial_request': 'Compare these streets.',
                                      'model': 'gpt-5.6-terra', 'max_calls': 2, 'max_tokens': 10000,
                                      'seed': 1})['id']
                    with mock.patch.object(playground, '_atomic_json', side_effect=write):
                        lab.control(sid, {'client_id': str(uuid.uuid4()), 'action': 'step'})
                        lab.worker.join(10)
                        self.assertFalse(lab.worker.is_alive())
                    saved = lab._load(sid)
                    self.assertEqual(1, len(invocations))
                    self.assertEqual(1, len(observation_writes), 'Observation failure must not cause recovery retries')
                    self.assertIsNone(saved['pending_call'])
                    self.assertEqual('paused', saved['status'])
                    self.assertEqual('assistant', saved['messages'][-1]['role'])
                    self.assertEqual('The saved evidence supports this comparison.', saved['messages'][-1]['display_text'])
                    row = saved['calls'][0]
                    self.assertEqual(attach_claims(json.loads(answer),invocations[0]), json.loads(row['receipt']['answer']))
                    self.assertEqual(20, row['receipt']['processed_tokens'])
                    self.assertEqual(20, lab._store(saved).show()['budgets']['tokens']['spent'])
                    self.assertEqual('unavailable', row['research_results']['observation_status'])
                    self.assertTrue(row['research_results']['gaps'])
                    for path, original in saved_scans:
                        self.assertEqual(original, path.read_bytes())
                    self.assertEqual(1, len(playground.playground_research.index(root / sid)['results']))
                finally:
                    if lab.worker:
                        lab.worker.join(10)
                    lab.close()


if __name__ == '__main__':
    unittest.main()
