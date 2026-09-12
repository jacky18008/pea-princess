"""Developer sync mechanics, with fake builders/servers and no model/network calls."""
import contextlib
import io
import json
import shutil
import socket
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import playground_dev_sync as sync
import start_playground as launcher
import test_playground_release_freshness as freshness


class DevSyncTests(unittest.TestCase):
    def setUp(self):
        freshness.ReleaseFreshnessTests.setUp(self)
        for name in launcher.REQUIRED:
            if name.endswith('.py'):
                self.write(name, '# Synthetic controller: ' + name)
        self.pack_current()
        self.previous_zip = self.archive.read_bytes()
    git = freshness.ReleaseFreshnessTests.git
    write = freshness.ReleaseFreshnessTests.write
    pack_current = freshness.ReleaseFreshnessTests.pack_current

    def service(self):
        path = self.root / '.pea-playground/dev-service-8765'
        path.mkdir(exist_ok=True)
        return path

    def managed_snapshot(self):
        service = self.service()
        digest = sync.source_digest(self.root)
        result = launcher.freeze(self.root, dev_sync={
            'source_root': str(self.root), 'service_dir': str(service), 'source_digest': digest})
        sync._write(service / 'status.json', {'state': 'ready', 'snapshot': result['snapshot']})
        return result, service

    def test_digest_ignores_generated_private_untracked_and_git_head(self):
        digest = sync.source_digest(self.root)
        self.write(launcher.GENERATED, 'Generated later')
        self.write('dist/pea-princess-skill.zip', 'Generated ZIP later')
        self.write('.pea-playground/old/session.json', 'New private session content')
        self.write('tools/untracked-private.py', 'PRIVATE = 1')
        self.assertEqual(digest, sync.source_digest(self.root))

    def test_public_controller_and_new_indexed_files_change_digest(self):
        previous = sync.source_digest(self.root)
        for name in ('viewer/viewer.html', 'tools/persona_playground.py', 'skills/vet-flat/SKILL.md'):
            self.write(name, 'Changed: ' + name)
            current = sync.source_digest(self.root)
            self.assertNotEqual(previous, current)
            previous = current
        self.write('tools/new.py', 'VALUE = 1')
        self.git('add', 'tools/new.py')
        self.assertNotEqual(previous, sync.source_digest(self.root))

    def test_managed_status_and_dispatch_reject_stale_source_but_keep_history(self):
        receipt, service = self.managed_snapshot()
        before = Path(receipt['manifest']).read_bytes()
        with mock.patch.object(sync, '_service_running', return_value=True):
            self.assertTrue(sync.source_status(receipt['snapshot'])['current'])
            self.write('tools/persona_playground.py', 'New controller')
            status = sync.source_status(receipt['snapshot'])
            self.assertFalse(status['current'])
            with self.assertRaises(sync.SyncError):
                with sync.dispatch_guard(receipt['snapshot']):
                    self.fail('must not dispatch')
        self.assertEqual(before, Path(receipt['manifest']).read_bytes())
        self.assertEqual('Saved historical session bytes.', self.session.read_text())

    def test_state_write_lease_allows_pause_while_stale_but_blocks_restart(self):
        receipt, service = self.managed_snapshot()
        self.write('tools/persona_playground.py', 'Changed while a call runs')
        with sync.operation_guard(receipt['snapshot']):
            with sync.idle_lock(service) as idle:
                self.assertFalse(idle)
        with sync.idle_lock(service) as idle:
            self.assertTrue(idle)
        with self.assertRaises(sync.SyncError):
            with sync.dispatch_guard(receipt['snapshot']):
                self.fail('stale source must not dispatch')

    def test_unavailable_source_or_service_fails_closed(self):
        receipt, service = self.managed_snapshot()
        self.assertFalse(sync.source_status(receipt['snapshot'])['current'], 'no supervisor owns the lock')
        (self.root / 'tools/persona_playground.py').unlink()
        self.assertFalse(sync.source_status(receipt['snapshot'])['current'])
        (service / 'status.json').write_text('{bad json')
        self.assertFalse(sync.source_status(receipt['snapshot'])['current'])

    def test_explicit_archive_stays_pinned_after_source_edits(self):
        receipt = launcher.freeze(self.root, skill_archive=self.archive)
        self.write('tools/persona_playground.py', 'New bytes')
        self.assertEqual('pinned', sync.source_status(receipt['snapshot'])['mode'])
        with sync.dispatch_guard(receipt['snapshot']):
            pass

    def test_dispatch_lease_defers_restart_and_switch_lease_rejects_dispatch(self):
        receipt, service = self.managed_snapshot()
        with mock.patch.object(sync, '_service_running', return_value=True):
            with sync.dispatch_guard(receipt['snapshot']):
                with sync.idle_lock(service) as idle:
                    self.assertFalse(idle)
            with sync.idle_lock(service) as idle:
                self.assertTrue(idle)
                with self.assertRaisesRegex(sync.SyncError, 'switching'):
                    with sync.dispatch_guard(receipt['snapshot']):
                        self.fail('must not dispatch')

    def supervisor(self, builder=None):
        process = mock.Mock(pid=4321)
        process.poll.return_value = None
        process.wait.return_value = 0
        popen = mock.Mock(return_value=process)
        builder = builder or mock.Mock(return_value={'snapshot': '/immutable/new', 'state_dir': str(self.root / '.pea-playground')})
        supervisor = sync.Supervisor(self.root, self.root / '.pea-playground', self.service(), 8765,
                                     builder=builder, popen=popen)
        return supervisor, builder, popen, process

    def test_debounce_publishes_once_and_never_dispatches_a_model(self):
        supervisor, builder, popen, process = self.supervisor()
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(sync, '_port_available'), mock.patch.object(sync, '_wait_server'):
            supervisor.tick(0)
            supervisor.tick(1)
            builder.assert_not_called()
            supervisor.tick(2)
            supervisor.tick(3)
        builder.assert_called_once()
        popen.assert_called_once()
        command = popen.call_args.args[0]
        self.assertTrue(command[2].endswith('/tools/persona_playground.py'))
        self.assertNotIn('codex', command)
        process.terminate.assert_not_called()
        self.assertEqual('ready', sync._json(self.service() / 'status.json')['state'])

    def test_busy_defers_replacement_and_stop_without_interrupting(self):
        supervisor, builder, popen, process = self.supervisor()
        supervisor.process = process
        supervisor.receipt = {'snapshot': '/immutable/old'}
        service = self.service()
        # Simulate the shared worker lease while source changes/build finishes.
        with sync._lock_file(service / 'dispatch.lock') as worker, contextlib.redirect_stdout(io.StringIO()):
            sync.fcntl.flock(worker, sync.fcntl.LOCK_SH)
            supervisor.tick(0)
            supervisor.tick(2)
            self.assertEqual('waiting_for_idle', sync._json(service / 'status.json')['state'])
            process.terminate.assert_not_called()
            popen.assert_not_called()
            supervisor.stopping = True
            self.assertTrue(supervisor.tick(3))
            process.terminate.assert_not_called()
            sync.fcntl.flock(worker, sync.fcntl.LOCK_UN)
            self.assertFalse(supervisor.tick(4))
        process.terminate.assert_called_once()
        popen.assert_not_called()

    def test_failed_build_keeps_old_server_and_does_not_retry_same_input(self):
        builder = mock.Mock(side_effect=sync.SyncError('broken source'))
        supervisor, builder, popen, process = self.supervisor(builder)
        supervisor.process = process
        supervisor.receipt = {'snapshot': '/immutable/old'}
        with contextlib.redirect_stdout(io.StringIO()):
            supervisor.tick(0)
            supervisor.tick(2)
            supervisor.tick(5)
        builder.assert_called_once()
        process.terminate.assert_not_called()
        popen.assert_not_called()
        self.assertEqual('/immutable/old', sync._json(self.service() / 'status.json')['snapshot'])
        self.assertEqual('error', sync._json(self.service() / 'status.json')['state'])

    def test_edits_during_build_are_not_activated(self):
        def build(*args):
            self.write('tools/persona_playground.py', 'Changed during build')
            return {'snapshot': '/immutable/orphan'}
        supervisor, _, popen, process = self.supervisor(build)
        with contextlib.redirect_stdout(io.StringIO()):
            supervisor.tick(0)
            supervisor.tick(2)
        popen.assert_not_called()
        self.assertIsNone(supervisor.pending)

    def test_generated_instructions_are_bound_to_the_same_managed_snapshot(self):
        generated = self.write('.pea-playground/new-build/INSTRUCTIONS.md', 'New generated instructions')
        digest = sync.source_digest(self.root)
        receipt = launcher.freeze(self.root, skill_archive=self.archive, generated_source=generated,
            dev_sync={'source_root': str(self.root), 'service_dir': str(self.service()), 'source_digest': digest})
        self.assertEqual('New generated instructions', (Path(receipt['snapshot']) / launcher.GENERATED).read_text())
        self.assertEqual('Synthetic controller: ' + launcher.GENERATED, (self.root / launcher.GENERATED).read_text())
        self.assertEqual(self.previous_zip, self.archive.read_bytes())

    def test_managed_explicit_build_still_validates_against_current_source(self):
        self.write('skills/vet-flat/SKILL.md', 'Changed after build')
        with self.assertRaisesRegex(launcher.FreezeError, 'stale'):
            launcher.freeze(self.root, skill_archive=self.archive, dev_sync={})

    def test_missing_frozen_manifest_cannot_turn_managed_runtime_into_pinned(self):
        receipt, _ = self.managed_snapshot()
        Path(receipt["manifest"]).unlink()
        self.assertFalse(sync.source_status(receipt["snapshot"])["current"])
        with self.assertRaises(sync.SyncError):
            with sync.dispatch_guard(receipt["snapshot"]):
                self.fail("must not dispatch")

    def test_build_uses_private_output_and_retains_old_zip_and_sessions(self):
        for name in launcher.REQUIRED:
            if name.endswith('.py'):
                self.write(name, '# Valid synthetic Python')
        # Some public scripts were updated; make the synthetic package current.
        self.pack_current()
        self.previous_zip = self.archive.read_bytes()
        real_run = subprocess.run
        def builder(command, **kwargs):
            if "-c" not in command:
                return real_run(command, **kwargs)
            stage = Path(command[-1])
            shutil.copyfile(self.archive, stage / "pea-princess-skill.zip")
            (stage / "prompt-pack").mkdir()
            (stage / "prompt-pack/INSTRUCTIONS.md").write_text("Same-build generated instructions")
            return subprocess.CompletedProcess(command, 0, stdout="built")
        service = self.service()
        with mock.patch.object(sync.subprocess, "run", side_effect=builder):
            receipt = sync.build_snapshot(self.root, self.root / ".pea-playground", service,
                                          sync.source_digest(self.root))
        self.assertEqual(self.previous_zip, self.archive.read_bytes())
        self.assertEqual("Saved historical session bytes.", self.session.read_text())
        self.assertEqual("Same-build generated instructions", (Path(receipt["snapshot"]) / launcher.GENERATED).read_text())
        self.assertEqual([], list(service.glob(".build-*")))

    def test_frozen_controller_syntax_is_checked_without_executing(self):
        self.write("tools/persona_playground.py", "invalid Python source!")
        receipt, _ = self.managed_snapshot()
        # Invalid controller syntax must be rejected before switching.
        with self.assertRaisesRegex(sync.SyncError, 'syntax check failed'):
            sync.validate_snapshot(receipt)
        snapshot = self.root / 'synthetic-snapshot'
        snapshot.mkdir()
        (snapshot / 'danger.py').write_text('raise RuntimeError("do not execute")')
        manifest = snapshot / 'runtime-manifest.json'
        manifest.write_text(json.dumps({'files': {'danger.py': {}}}))
        sync.validate_snapshot({'snapshot': str(snapshot), 'manifest': str(manifest)})

    def test_failed_builder_does_not_freeze_or_replace_any_release(self):
        real_run = subprocess.run
        def fail(command, **kwargs):
            if "-c" not in command:
                return real_run(command, **kwargs)
            return subprocess.CompletedProcess(command, 1, stdout="required instructions too long")
        with mock.patch.object(sync.subprocess, "run", side_effect=fail), mock.patch.object(launcher, "freeze") as freeze:
            with self.assertRaisesRegex(sync.SyncError, "Public build failed"):
                sync.build_snapshot(self.root, self.root / ".pea-playground", self.service(), sync.source_digest(self.root))
        freeze.assert_not_called()
        self.assertEqual(self.previous_zip, self.archive.read_bytes())

    def test_existing_service_cannot_silently_watch_another_repository(self):
        service = self.service()
        sync._write(service / "status.json", {"source_root": "/another/repo"})
        with mock.patch.object(sync, "_service_running", return_value=True):
            with self.assertRaisesRegex(sync.SyncError, "another source root"):
                sync.service_command("start", self.root, self.root / ".pea-playground", 8765)

    def test_new_untracked_import_dependency_blocks_without_reading_or_publishing_it(self):
        self.write('skills/vet-flat/scripts/area_scan.py', 'def run():\n    import local_extra\n')
        self.git('add', 'skills/vet-flat/scripts/area_scan.py')
        digest = sync.source_digest(self.root)
        self.write('skills/vet-flat/scripts/local_extra.py', 'This private untracked content is not valid Python')
        with self.assertRaisesRegex(sync.SyncError, 'review/index intended public files'):
            sync.source_digest(self.root)
        self.assertEqual(self.previous_zip, self.archive.read_bytes())
        (self.root / 'skills/vet-flat/scripts/local_extra.py').unlink()
        self.assertEqual(digest, sync.source_digest(self.root))

    def test_transient_source_failure_recovers_exact_running_generation_without_rebuild(self):
        supervisor, builder, popen, process = self.supervisor()
        source = self.root / 'tools/persona_playground.py'
        original = source.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(sync, '_port_available'), mock.patch.object(sync, '_wait_server'):
            supervisor.tick(0)
            supervisor.tick(2)
            source.unlink()
            supervisor.tick(3)
            self.assertEqual('error', sync._json(self.service() / 'status.json')['state'])
            source.write_bytes(original)
            supervisor.tick(4)
        self.assertEqual('ready', sync._json(self.service() / 'status.json')['state'])
        builder.assert_called_once()
        popen.assert_called_once()
        process.terminate.assert_not_called()

    def test_invalid_public_python_is_a_visible_stale_reason(self):
        receipt, _ = self.managed_snapshot()
        self.write('skills/vet-flat/scripts/session_state.py', 'invalid public Python!')
        status = sync.source_status(receipt['snapshot'])
        self.assertFalse(status['current'])
        self.assertIn('Public dependency check failed', status['reason'])

    def test_busy_refresh_switches_once_after_worker_releases_lease(self):
        supervisor, builder, popen, old_process = self.supervisor()
        supervisor.process = old_process
        supervisor.receipt = {'snapshot': '/immutable/old'}
        new_process = mock.Mock(pid=4322)
        new_process.poll.return_value = None
        popen.return_value = new_process
        with sync._lock_file(self.service() / 'dispatch.lock') as worker, contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(sync, '_port_available'), mock.patch.object(sync, '_wait_server'):
            sync.fcntl.flock(worker, sync.fcntl.LOCK_SH)
            supervisor.tick(0)
            supervisor.tick(2)
            old_process.terminate.assert_not_called()
            sync.fcntl.flock(worker, sync.fcntl.LOCK_UN)
            supervisor.tick(3)
            supervisor.tick(4)
        old_process.terminate.assert_called_once()
        popen.assert_called_once()
        builder.assert_called_once()
        self.assertEqual('/immutable/new', supervisor.receipt['snapshot'])
        self.assertEqual('Saved historical session bytes.', self.session.read_text())

    def test_port_preflight_allows_owned_server_time_wait_after_http_close(self):
        # The HTTP server sets SO_REUSEADDR; accepted connections can remain in
        # TIME_WAIT after its listening socket closes during a normal refresh.
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            listener.listen(1)
            with socket.create_connection(('127.0.0.1', port), timeout=2) as client:
                accepted, _ = listener.accept()
                with accepted:
                    accepted.shutdown(socket.SHUT_WR)
                    self.assertEqual(b'', client.recv(1))
        sync._port_available(port)

    def test_port_preflight_still_rejects_an_actual_listening_server(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            with self.assertRaisesRegex(sync.SyncError, 'Port is occupied'):
                sync._port_available(listener.getsockname()[1])

    def pinned_generation(self):
        receipt, service = self.managed_snapshot()
        pin = {'source_root': str(self.root), 'state_dir': str(self.root / '.pea-playground'),
               'service_dir': str(service), 'source_digest': sync.source_digest(self.root), 'receipt': receipt}
        sync._write(service / 'generation.json', pin)
        return receipt, service, pin

    def test_restart_reuses_verified_generation_without_builder_or_new_manifest(self):
        receipt, service, pin = self.pinned_generation()
        original_manifest = Path(receipt['manifest']).read_bytes()
        sync._write(service / 'status.json', {'state': 'stopped', 'snapshot': '/do/not/trust/status'})
        supervisor, builder, popen, process = self.supervisor()
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(sync, '_port_available'), mock.patch.object(sync, '_wait_server'):
            supervisor.tick(0)
            supervisor.tick(2)
        builder.assert_not_called()
        self.assertEqual(receipt, supervisor.receipt)
        self.assertEqual(original_manifest, Path(receipt['manifest']).read_bytes())
        self.assertEqual(receipt, sync._json(service / 'generation.json')['receipt'])
        self.assertEqual(receipt, sync._json(service / 'status.json')['receipt'])
        self.assertIn(str(Path(receipt['snapshot']) / 'tools/persona_playground.py'), popen.call_args.args[0])

    def test_changed_source_including_helper_does_not_reuse_previous_generation(self):
        receipt, service, pin = self.pinned_generation()
        self.write('tools/playground_dev_sync.py', '# A genuinely new helper version')
        self.assertIsNone(sync.reusable_generation(self.root, self.root / '.pea-playground', service,
                                                  sync.source_digest(self.root)))

    def test_legacy_status_without_generation_receipt_cannot_authorize_reuse(self):
        receipt, service = self.managed_snapshot()
        sync._write(service / 'status.json', {'state': 'ready', 'receipt': receipt})
        self.assertIsNone(sync.reusable_generation(self.root, self.root / '.pea-playground', service,
                                                  sync.source_digest(self.root)))

    def test_reuse_rejects_modified_or_extra_snapshot_files(self):
        for kind in ('changed', 'extra', 'missing', 'symlink'):
            with self.subTest(kind=kind):
                receipt, service, pin = self.pinned_generation()
                path = Path(receipt['snapshot']) / 'tools/persona_playground.py'
                if kind == 'changed':
                    path.chmod(0o600)
                    path.write_text('# Changed frozen bytes')
                elif kind == 'extra':
                    (Path(receipt['snapshot']) / 'tools/injected.py').write_text('# Extra file')
                elif kind == 'missing':
                    path.unlink()
                else:
                    path.unlink()
                    path.symlink_to(self.root / 'tools/persona_playground.py')
                with self.assertRaises(sync.SyncError):
                    sync.reusable_generation(self.root, self.root / '.pea-playground', service, pin['source_digest'])

    def test_reuse_rejects_manifest_tampering_even_if_status_claims_new_hash(self):
        receipt, service, pin = self.pinned_generation()
        path = Path(receipt['manifest'])
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b'\n')
        sync._write(service / 'status.json', {'state': 'ready', 'receipt': dict(receipt, manifest_sha256='forged')})
        with self.assertRaisesRegex(sync.SyncError, 'manifest no longer matches'):
            sync.reusable_generation(self.root, self.root / '.pea-playground', service, pin['source_digest'])

    def test_reuse_rejects_wrong_service_state_or_source_root_binding(self):
        for field in ('source_root', 'state_dir', 'service_dir'):
            with self.subTest(field=field):
                receipt, service, pin = self.pinned_generation()
                pin[field] = '/somewhere/else'
                sync._write(service / 'generation.json', pin)
                with self.assertRaisesRegex(sync.SyncError, 'different source/state/service roots'):
                    sync.reusable_generation(self.root, self.root / '.pea-playground', service, pin['source_digest'])

    def test_corrupted_generation_blocks_restart_without_silent_rebuild(self):
        receipt, service, pin = self.pinned_generation()
        Path(receipt['manifest']).unlink()
        supervisor, builder, popen, process = self.supervisor()
        with contextlib.redirect_stdout(io.StringIO()):
            supervisor.tick(0)
            supervisor.tick(2)
        builder.assert_not_called()
        popen.assert_not_called()
        self.assertEqual('error', sync._json(service / 'status.json')['state'])

    def test_default_launcher_starts_service_without_freezing_in_caller(self):
        with mock.patch.object(sync, 'service_command', return_value={'running': True}) as command, \
                mock.patch.object(launcher, 'freeze') as freeze, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, launcher.main(['--source-root', str(self.root)]))
        self.assertEqual('start', command.call_args.args[0])
        self.assertEqual(self.root, command.call_args.args[1])
        freeze.assert_not_called()


if __name__ == '__main__':
    unittest.main()
