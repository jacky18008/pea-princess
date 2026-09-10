"""Native transport regression tests: real local fake processes, no provider calls."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bench'))
import conversation_native as native
from call_control import CallControl, CallControlPaused


USAGE = {'input_tokens': 20, 'cached_input_tokens': 7, 'output_tokens': 5}
TERMINAL = json.dumps({'type': 'turn.completed', 'usage': USAGE})
FAKE_PREFIX = '''import json, os, sys, time
from pathlib import Path
answer = Path(sys.argv[1])
workspace = Path(sys.argv[2])
'''
SUCCESS = '''prompt = sys.stdin.read()
(workspace / 'received.txt').write_text(prompt)
(workspace / 'result.txt').write_text('synthetic artifact')
answer.write_text('Read the fixture and wrote the result.')
print(json.dumps({'type':'item.started', 'item':{'type':'command_execution', 'command':'cat fixture.txt'}}))
print(json.dumps({'type':'item.completed', 'item':{'type':'command_execution', 'command':'cat fixture.txt', 'aggregated_output':'synthetic fixture', 'exit_code':0}}))
print(json.dumps({'type':'item.completed', 'item':{'type':'agent_message', 'text':'Read the fixture and wrote the result.'}}))
print(TERMINAL, flush=True)
print('native diagnostic', file=sys.stderr, flush=True)
'''.replace('TERMINAL', repr(TERMINAL))


class ConversationNativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # /var on macOS is a symlink; callers must use the canonical owned root.
        self.root = Path(self.temp.name).resolve()
        self.workdir = native.prepare_workdir(self.root / 'workspace', {
            'fixture.txt': 'synthetic fixture',
            '.pea-state/synthetic.json': '{"synthetic":true}',
        })
        self.commands = []
        self.processes = []
        self.real_start = native.launch.start_process
        self.request = {'model': 'gpt-6-astra', 'effort': 'low',
                        'prompt': 'Read fixture.txt and write result.txt.\n原生工具可以使用。',
                        'timeout_seconds': 3}

    def folder(self, name='call-1'):
        path = self.root / name
        path.mkdir(mode=0o700)
        return path

    def run_fake(self, script=SUCCESS, request=None, folder=None, start_callback=None):
        folder = folder or self.folder()
        def start(command, **kwargs):
            self.commands.append((command, kwargs.copy()))
            if start_callback:
                start_callback(command, kwargs)
            answer = command[command.index('--output-last-message') + 1]
            proc = self.real_start([sys.executable, '-c', FAKE_PREFIX + script, answer, str(self.workdir)], **kwargs)
            self.processes.append(proc)
            return proc
        with mock.patch.object(native.shutil, 'which', return_value='/fake/codex'), \
                mock.patch.object(native.launch, 'start_process', side_effect=start):
            return native.invoke(request or self.request, folder, self.workdir)

    def assert_no_dispatch(self, request=None, folder=None, workdir=None):
        with mock.patch.object(native.launch, 'start_process') as launched, \
                mock.patch.object(native.shutil, 'which', return_value='/fake/codex'):
            with self.assertRaises((native.NativeError, OSError)):
                native.invoke(request or self.request, folder or self.folder(), workdir or self.workdir)
        launched.assert_not_called()

    def test_native_files_tools_exact_usage_and_unchanged_stdin(self):
        record = self.run_fake()
        self.assertEqual('complete', record['status'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])
        self.assertEqual(2, len(record['tool_events']))
        self.assertEqual('synthetic fixture', record['tool_events'][1]['item']['aggregated_output'])
        self.assertEqual(1, record['launch_result']['attempts'])
        self.assertEqual(self.request['prompt'], (self.workdir / 'received.txt').read_text())
        self.assertEqual('Read the fixture and wrote the result.', record['answer'])
        self.assertNotIn('result.txt', record['workspace_before']['files'])
        self.assertIn('result.txt', record['workspace_after']['files'])
        self.assertIn('.pea-state/synthetic.json', record['workspace_after']['files'])
        command, kwargs = self.commands[0]
        self.assertEqual('workspace-write', command[command.index('--sandbox') + 1])
        self.assertEqual('gpt-6-astra', command[command.index('--model') + 1])
        self.assertIn('model_reasoning_effort="low"', command)
        self.assertIn('project_doc_max_bytes=0', command)
        self.assertIn('--ignore-user-config', command)
        self.assertIn('--ephemeral', command)
        self.assertEqual([
            '/fake/codex', 'exec', '--ignore-user-config', '--ephemeral', '--cd', str(self.workdir),
            '--sandbox', 'workspace-write', '--skip-git-repo-check', '--model', 'gpt-6-astra',
            '-c', 'model_reasoning_effort="low"', '-c', 'project_doc_max_bytes=0',
            '--json', '--output-last-message', str(self.root / 'call-1' / 'native-answer.txt'), '--', '-'], command)
        self.assertEqual(['--', '-'], command[-2:])
        self.assertNotIn(self.request['prompt'], command)
        self.assertEqual(0o077, kwargs['umask'])
        self.assertEqual(str(self.workdir), kwargs['cwd'])
        folder = self.root / 'call-1'
        self.assertEqual(record['launch_result']['stdout'], (folder / 'native-stdout.jsonl').read_text())
        self.assertEqual('native diagnostic\n', (folder / 'native-stderr.txt').read_text())
        for path in folder.iterdir():
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        invocation = json.loads((folder / 'native-invocation.json').read_text())
        self.assertEqual(record['request_sha256'], invocation['request_sha256'])
        self.assertNotIn(self.request['prompt'], json.dumps(invocation))
        self.assertTrue(all(proc.poll() is not None for proc in self.processes))

    def test_optional_discovery_and_history_limits_are_frozen_in_argv_and_receipt(self):
        base_command = self.run_fake()['command']
        cases = [
            ({'isolate_workspace_reads': False}, []),
            ({'skip_host_skill_discovery': False}, []),
            ({'skip_host_skill_discovery': True}, ['--enable', 'skip_host_skill_discovery']),
            ({'tool_output_token_limit': 256}, ['-c', 'tool_output_token_limit=256']),
            ({'tool_output_token_limit': 4000}, ['-c', 'tool_output_token_limit=4000']),
            ({'tool_output_token_limit': 16000}, ['-c', 'tool_output_token_limit=16000']),
            ({'skip_host_skill_discovery': True, 'tool_output_token_limit': 4000},
             ['--enable', 'skip_host_skill_discovery', '-c', 'tool_output_token_limit=4000']),
        ]
        for index, (options, extra_args) in enumerate(cases):
            with self.subTest(options=options):
                folder = self.folder('controls-' + str(index))
                request = self.request | options
                expected_hash = native._digest(request)
                expected_command = base_command[:-2] + extra_args + ['--', '-']
                expected_command[expected_command.index('--output-last-message') + 1] = str(folder / 'native-answer.txt')
                def inspect_and_mutate_caller(command, kwargs):
                    saved = json.loads((folder / 'native-invocation.json').read_text())
                    self.assertEqual(expected_command, command)
                    self.assertEqual(expected_command, saved['command'])
                    self.assertEqual(expected_hash, saved['request_sha256'])
                    request['skip_host_skill_discovery'] = not request.get('skip_host_skill_discovery', False)
                    request['tool_output_token_limit'] = 999
                record = self.run_fake(request=request, folder=folder, start_callback=inspect_and_mutate_caller)
                self.assertEqual('complete', record['status'])
                self.assertEqual(expected_command, record['command'])
                self.assertEqual(expected_hash, record['request_sha256'])
                self.assertEqual(self.request['prompt'], (self.workdir / 'received.txt').read_text())

    def test_isolated_reads_use_only_named_profile_and_freeze_exact_configuration(self):
        request = self.request | {'isolate_workspace_reads': True, 'skip_host_skill_discovery': True}
        expected_hash = native._digest(request)
        synthetic_home = self.root / 'synthetic-home'
        expected_configs = [
            'default_permissions="pea_native_minimal"',
            'permissions.pea_native_minimal.filesystem={":minimal"="read",":workspace_roots"="write",'
            '"/Library/Developer/CommandLineTools/usr/bin"="read",'
            '"/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework"="read"}',
            'permissions.pea_native_minimal.network.enabled=false',
            'shell_environment_policy.inherit="none"',
            'shell_environment_policy.set={PATH="/Library/Developer/CommandLineTools/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin"}',
            'skills.config=[{path=' + json.dumps(str(synthetic_home / '.agents/skills/vet-flat')) + ',enabled=false}]',
            'model_reasoning_effort="low"', 'project_doc_max_bytes=0',
        ]
        folder = self.folder()
        def inspect_and_mutate_caller(command, kwargs):
            saved = json.loads((folder / 'native-invocation.json').read_text())
            self.assertEqual(command, saved['command'])
            self.assertEqual(expected_hash, saved['request_sha256'])
            request['isolate_workspace_reads'] = False
        with mock.patch.object(native.sys, 'platform', 'darwin'), \
                mock.patch.object(native.Path, 'is_dir', return_value=True), \
                mock.patch.object(native.Path, 'home', return_value=synthetic_home):
            record = self.run_fake(request=request, folder=folder, start_callback=inspect_and_mutate_caller)
        command, kwargs = self.commands[0]
        self.assertEqual(expected_configs, [command[i + 1] for i, value in enumerate(command) if value == '-c'])
        self.assertNotIn('--sandbox', command)
        self.assertFalse(any('sandbox_mode' in value for value in command))
        self.assertNotIn('workspace-write', command)
        self.assertEqual(['--enable', 'skip_host_skill_discovery', '--', '-'], command[-4:])
        self.assertNotIn('env', kwargs)
        self.assertEqual('complete', record['status'])
        self.assertEqual(expected_hash, record['request_sha256'])
        self.assertEqual(command, record['command'])

    def test_isolated_reads_fail_before_dispatch_on_unsupported_host_or_missing_runtime(self):
        request = self.request | {'isolate_workspace_reads': True}
        with mock.patch.object(native.sys, 'platform', 'linux'):
            folder = self.folder('unsupported-platform')
            self.assert_no_dispatch(request=request, folder=folder)
            self.assertEqual([], list(folder.iterdir()))
        for index, absent in enumerate(native.ISOLATED_RUNTIME_ROOTS):
            with mock.patch.object(native.sys, 'platform', 'darwin'), \
                    mock.patch.object(native.Path, 'is_dir', autospec=True, side_effect=lambda path: path != absent):
                folder = self.folder('missing-runtime-' + str(index))
                self.assert_no_dispatch(request=request, folder=folder)
                self.assertEqual([], list(folder.iterdir()))

    def test_workspace_is_owned_outside_tree_and_persists_between_calls(self):
        self.assertEqual(self.root, native._marker(self.workdir).parent)
        self.assertNotIn(native._marker(self.workdir).name, native._snapshot(self.workdir)['files'])
        first = self.run_fake()
        second = self.run_fake(folder=self.folder('call-2'), request=self.request | {'model': 'gpt-5.6-luna', 'effort': 'high'})
        self.assertEqual(first['workspace_after'], second['workspace_before'])
        self.assertIn('model_reasoning_effort="high"', second['command'])
        self.assert_no_dispatch(folder=self.root / 'call-1')

    def test_schema_inspectable_copy_and_frozen_request(self):
        schema = {'type': 'object', 'properties': {'answer': {'type': 'string'}}, 'required': ['answer'], 'additionalProperties': False}
        request = self.request | {'response_schema': schema}
        expected_hash = native._digest(request)
        def mutate_caller(command, kwargs):
            schema['properties']['answer']['type'] = 'number'
        record = self.run_fake(request=request, start_callback=mutate_caller)
        self.assertEqual(expected_hash, record['request_sha256'])
        protected = self.root / 'call-1' / 'native-schema.json'
        self.assertEqual('string', json.loads(protected.read_text())['properties']['answer']['type'])
        copy = self.workdir / ('.native-response-schema-' + hashlib.sha256(protected.read_bytes()).hexdigest() + '.json')
        self.assertEqual(protected.read_bytes(), copy.read_bytes())
        self.assertIn(copy.name, record['workspace_before']['files'])
        self.assertEqual(str(protected), record['command'][record['command'].index('--output-schema') + 1])
        restored_request = request | {'response_schema': json.loads(protected.read_text())}
        self.run_fake(request=restored_request, folder=self.folder('call-2'))
        copy.write_text('{}')
        self.assert_no_dispatch(request=restored_request, folder=self.folder('call-3'))

    def test_invalid_requests_are_rejected_without_starting_a_process(self):
        changes = [{'model': 'claude-sonnet'}, {'model': 'arbitrary-proxy'}, {'effort': 'medium'},
                   {'timeout_seconds': True}, {'timeout_seconds': False}, {'timeout_seconds': 0},
                   {'timeout_seconds': -1}, {'timeout_seconds': native.MAX_TIMEOUT_SECONDS + 1},
                   {'timeout_seconds': 1.5}, {'prompt': ' '}, {'prompt': 'a' * (native.MAX_PROMPT_BYTES + 1)},
                   {'response_schema': []}, {'response_schema': {'x': float('nan')}},
                   {'response_schema': {'x': object()}}, {'response_schema': {'x': 'a' * native.MAX_SCHEMA_BYTES}},
                   {'retry': 1}]
        changes.extend({'skip_host_skill_discovery': value} for value in (None, 0, 1, 'true', [], {}))
        changes.extend({'isolate_workspace_reads': value} for value in (None, 0, 1, 'true', [], {}))
        changes.extend({'tool_output_token_limit': value}
                       for value in (None, True, False, -1, 0, 255, 16001, 256.0, '4000', [], {}))
        for index, change in enumerate(changes):
            with self.subTest(change=list(change)):
                self.assert_no_dispatch(request=self.request | change, folder=self.folder('bad-' + str(index)))

    def test_explicit_timeout_boundaries_are_saved_before_dispatch_without_changing_request(self):
        self.assertEqual(1200, native.MAX_TIMEOUT_SECONDS)
        for timeout in (1, 240, 241, 1200):
            with self.subTest(timeout=timeout):
                folder = self.folder('deadline-' + str(timeout))
                request = self.request | {'timeout_seconds': timeout}
                def inspect_receipt(command, kwargs):
                    saved = json.loads((folder / 'native-invocation.json').read_text())
                    self.assertEqual(timeout, saved['timeout_seconds'])
                    self.assertEqual(native._digest(request), saved['request_sha256'])
                record = self.run_fake(request=request, folder=folder, start_callback=inspect_receipt)
                self.assertEqual('complete', record['status'])
                self.assertEqual(native._digest(request), record['request_sha256'])
                self.assertEqual(timeout, request['timeout_seconds'])

    def test_prepare_rejects_real_existing_or_unsafe_paths(self):
        for index, name in enumerate(('../escape', '/absolute', '.git/config', '.')):
            with self.subTest(name=name), self.assertRaises(native.NativeError):
                native.prepare_workdir(self.root / ('unsafe-' + str(index)), {name: 'data'})
        with self.assertRaises(native.NativeError):
            native.prepare_workdir(self.workdir, {})
        with self.assertRaises(native.NativeError):
            native.prepare_workdir(self.root / 'never-created', {'x': Path('not-implicit-source')})
        existing = self.folder('unmarked-repo')
        self.assert_no_dispatch(workdir=existing)
        link = self.root / 'linked-parent'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(native.NativeError):
            native.prepare_workdir(link / 'forbidden', {})
        self.assert_no_dispatch(folder=self.workdir)
        self.assert_no_dispatch(folder=self.workdir / '.pea-state')
        self.assert_no_dispatch(folder=self.root)

    def test_marker_corruption_and_symlink_or_hardlinked_workspace_refuse_dispatch(self):
        marker = native._marker(self.workdir)
        original = marker.read_bytes()
        marker.write_bytes(original.replace(b'deliberately', b'unexpectedly'))
        self.assert_no_dispatch(folder=self.folder('bad-marker'))
        marker.write_bytes(original)
        outside = self.root / 'outside.txt'
        outside.write_text('outside synthetic sentinel')
        link = self.workdir / 'unsafe'
        link.symlink_to(outside)
        self.assert_no_dispatch(folder=self.folder('bad-link'))
        link.unlink()
        os.link(outside, link)
        self.assert_no_dispatch(folder=self.folder('bad-hardlink'))
        link.unlink()
        fifo = self.workdir / 'fifo'
        os.mkfifo(fifo)
        self.assert_no_dispatch(folder=self.folder('bad-fifo'))

    def test_timeout_preserves_available_usage_stops_owned_process_and_never_retries(self):
        script = "sys.stdin.read()\nprint(" + repr(TERMINAL) + ", flush=True)\ntime.sleep(60)\n"
        started = time.monotonic()
        record = self.run_fake(script=script, request=self.request | {'timeout_seconds': 1})
        self.assertLess(time.monotonic() - started, 6)
        self.assertEqual('stopped', record['status'])
        self.assertTrue(record['timeout'])
        self.assertEqual(1, json.loads((self.root / 'call-1/native-invocation.json').read_text())['timeout_seconds'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])
        self.assertEqual(1, len(self.commands))
        self.assertIsNotNone(self.processes[0].poll())
        self.assert_no_dispatch(folder=self.root / 'call-1')

    def test_closed_output_pipes_do_not_escape_timeout_when_stdin_is_blocked(self):
        script = 'os.close(1)\nos.close(2)\ntime.sleep(60)\n'
        started = time.monotonic()
        record = self.run_fake(script=script, request=self.request | {'timeout_seconds': 1, 'prompt': 'x' * 900000})
        self.assertLess(time.monotonic() - started, 6)
        self.assertTrue(record['timeout'])
        self.assertIsNone(record['direct_terminal_usage'])
        self.assertEqual(1, len(self.commands))
        self.assertIsNotNone(self.processes[0].poll())

    def test_output_cap_retains_prefix_and_known_usage_without_retry(self):
        script = "sys.stdin.read()\nprint(" + repr(TERMINAL) + ", flush=True)\ntime.sleep(.1)\nsys.stderr.write('z'*10000)\nsys.stderr.flush()\ntime.sleep(60)\n"
        with mock.patch.object(native, 'MAX_STREAM_BYTES', 512):
            record = self.run_fake(script=script)
        self.assertEqual('stopped', record['status'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])
        self.assertEqual({'stdout': False, 'stderr': True}, record['stream_truncated'])
        self.assertEqual(512, len((self.root / 'call-1' / 'native-stderr.txt').read_bytes()))
        self.assertEqual('output_limit', record['launch_result']['note'])
        self.assertEqual(1, len(self.commands))

    def test_invalid_answer_artifacts_preserve_usage_and_do_not_read_external_targets(self):
        cases = ["pass", "answer.write_bytes(b'\\xff')", "os.mkfifo(answer)",
                 "answer.symlink_to(workspace.parent / 'outside-answer.txt')"]
        (self.root / 'outside-answer.txt').write_text('outside answer sentinel')
        for index, action in enumerate(cases):
            script = "sys.stdin.read()\n" + action + "\nprint(" + repr(TERMINAL) + ", flush=True)\n"
            started = time.monotonic()
            with self.subTest(action=action):
                record = self.run_fake(script=script, folder=self.folder('invalid-answer-' + str(index)))
                self.assertLess(time.monotonic() - started, 4)
                self.assertEqual('stopped', record['status'])
                self.assertEqual('', record['answer'])
                self.assertEqual(USAGE, record['direct_terminal_usage'])
                self.assertIn({'type': 'invalid_answer_artifact'}, record['errors'])

    def test_post_call_unsafe_workspace_retains_raw_evidence_and_usage(self):
        script = SUCCESS + "(workspace / 'outside-link').symlink_to(workspace.parent / 'outside.txt')\n"
        (self.root / 'outside.txt').write_text('never snapshot this sentinel')
        record = self.run_fake(script=script)
        self.assertEqual('stopped', record['status'])
        self.assertIsNone(record['workspace_after'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])
        self.assertIn({'type': 'invalid_workspace_artifact'}, record['errors'])
        self.assertNotIn('never snapshot', json.dumps(record))
        self.assertTrue((self.root / 'call-1' / 'native-stdout.jsonl').exists())

    def test_process_start_failure_is_recorded_once_and_claims_no_known_usage(self):
        folder = self.folder()
        with mock.patch.object(native.shutil, 'which', return_value='/fake/codex'), \
                mock.patch.object(native.launch, 'start_process', side_effect=OSError('offline fake failure')) as launched:
            record = native.invoke(self.request, folder, self.workdir)
        self.assertEqual(1, launched.call_count)
        self.assertEqual('stopped', record['status'])
        self.assertIsNone(record['direct_terminal_usage'])
        self.assertEqual('process_start_error', record['launch_result']['note'])
        self.assertTrue((folder / 'native-invocation.json').exists())
        self.assert_no_dispatch(folder=folder)

    def test_durable_controller_accepts_tools_and_replays_without_second_process(self):
        controller_path = self.root / 'control'
        controller = CallControl(controller_path, ['native-turn'], allow_tools=True)
        callback = mock.Mock(side_effect=self.run_fake)
        first = controller.run('native-turn', 'synthetic-conversation', 'assistant', 'reply', callback)
        restored = CallControl(controller_path, ['native-turn'], allow_tools=True)
        second = restored.run('native-turn', 'synthetic-conversation', 'assistant', 'reply', callback)
        self.assertEqual(first, second)
        self.assertEqual(1, callback.call_count)
        self.assertEqual(1, len(self.commands))
        self.assertEqual(25, restored.report()['usage']['total_tokens'])
        self.assertTrue(restored.report()['plan_complete'])

    def test_bad_telemetry_persists_and_blocks_later_callbacks(self):
        cases = [('missing', ''), ('duplicate', 'print(' + repr(TERMINAL) + ')\n'),
                 ('malformed', "print('not-json')\n")]
        for name, suffix in cases:
            with self.subTest(name=name):
                script = SUCCESS.replace('print(' + repr(TERMINAL) + ', flush=True)', '') if name == 'missing' else SUCCESS + suffix
                controller = CallControl(self.root / ('control-' + name), ['turn-1', 'turn-2'], allow_tools=True)
                with self.assertRaises(CallControlPaused):
                    controller.run('turn-1', 'job', 'assistant', 'reply',
                        lambda: self.run_fake(script=script, folder=self.folder('call-' + name)))
                later = mock.Mock()
                with self.assertRaises(CallControlPaused):
                    controller.run('turn-2', 'job', 'assistant', 'reply', later)
                later.assert_not_called()
                self.assertEqual(1, controller.report()['failed_calls'])
                self.assertTrue((self.root / ('call-' + name) / 'native-stdout.jsonl').exists())
                direct = controller.record('turn-1')['direct_terminal_usage']
                self.assertEqual(USAGE if name == 'malformed' else None, direct)

    def test_workspace_growth_beyond_bound_stops_but_keeps_usage(self):
        script = SUCCESS + "(workspace / 'large.txt').write_text('x' * 1024)\n"
        with mock.patch.object(native, 'MAX_WORKSPACE_BYTES', 512):
            record = self.run_fake(script=script)
        self.assertEqual('stopped', record['status'])
        self.assertIsNone(record['workspace_after'])
        self.assertEqual(USAGE, record['direct_terminal_usage'])

    def test_interruption_record_is_bound_to_caller_dispatch_and_never_retried(self):
        controller = CallControl(self.root / 'control', ['native-turn'], allow_tools=True)
        folder = self.folder()
        with mock.patch.object(native.shutil, 'which', return_value='/fake/codex'), \
                mock.patch.object(native.launch, 'start_process', side_effect=KeyboardInterrupt) as launched:
            with self.assertRaises(KeyboardInterrupt) as caught:
                controller.run('native-turn', 'job', 'assistant', 'reply',
                    lambda: native.invoke(self.request, folder, self.workdir))
        self.assertEqual(1, launched.call_count)
        self.assertIsInstance(caught.exception.record, dict)
        self.assertEqual('stopped', controller.record('native-turn')['status'])
        self.assertEqual(1, controller.report()['failed_calls'])
        self.assert_no_dispatch(folder=folder)


if __name__ == '__main__':
    unittest.main()
