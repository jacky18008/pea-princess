#!/usr/bin/env python3
"""Local developer supervisor and dispatch freshness lease; never calls a model.

Indexed public/controller working bytes are the inputs. Generated outputs, private
sessions, and Git commit timestamps do not trigger refresh. Explicit archives are
pinned. A managed server must hold dispatch_guard throughout each worker.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time


class SyncError(ValueError):
    pass


def _launcher():
    import start_playground
    return start_playground


def source_digest(root):
    """Fingerprint exact indexed inputs; reject unstable reads and missing files."""
    root = Path(root).resolve()
    launcher = _launcher()
    def names():
        return sorted(set(launcher.tracked(root)) |
                      {rel for _, rel in launcher.build_dist.public_members(root)})
    selected = names()
    # A newly present untracked sibling can shadow an import. Reject its omission
    # without reading/publishing that private file or automatically changing Git.
    try:
        launcher.build_dist.check_script_dependencies(launcher.build_dist.public_members(root), root=root)
    except (ValueError, SyntaxError) as error:
        raise SyncError('Public dependency check failed; review/index intended public files: ' + str(error)) from error
    records = {}
    for name in selected:
        # Even an accidentally indexed generated pack cannot cause rebuild loops.
        if name == launcher.GENERATED:
            continue
        body, _ = launcher.read_source(root, name)
        records[name] = hashlib.sha256(body).hexdigest()
    if selected != names():
        raise SyncError('Indexed source paths changed while checking freshness.')
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write(path, value):
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix='.status-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _config(runtime_root):
    path = Path(runtime_root) / 'runtime-manifest.json'
    if not path.exists():
        if path.parent.parent.name == 'runtime':
            raise SyncError('Frozen runtime manifest is missing.')
        return None
    return _json(path).get('dev_sync')


def source_status(runtime_root):
    """Read-only catalog/preflight result. current is a byte check, not quality."""
    result = {'mode': 'managed', 'current': False, 'source_digest': None,
              'runtime_digest': None, 'reason': None}
    try:
        config = _config(runtime_root)
        if config is None:
            return dict(result, mode='pinned', current=True,
                        reason='Pinned or unmanaged runtime; automatic source synchronization is disabled.')
        result['runtime_digest'] = config['source_digest']
        result['source_digest'] = source_digest(config['source_root'])
        if result['source_digest'] != result['runtime_digest']:
            result['reason'] = 'Source changed; wait for the developer service to publish a fresh runtime.'
            return result
        status = _json(Path(config['service_dir']) / 'status.json')
        if status.get('state') != 'ready' or status.get('snapshot') != str(Path(runtime_root).resolve()):
            result['reason'] = 'Developer service is not ready for this runtime: ' + str(status.get('state'))
            return result
        if not _service_running(Path(config['service_dir'])):
            result['reason'] = 'Developer supervisor is not running.'
            return result
        result.update(current=True, reason='Current indexed public and controller bytes match this runtime.')
    except (OSError, ValueError, KeyError, TypeError) as error:
        result['reason'] = 'Cannot verify developer source freshness: ' + str(error)
    return result


@contextmanager
def operation_guard(runtime_root):
    """Protect state writes from restart; pause/review remain usable while stale."""
    try:
        config = _config(runtime_root)
    except (OSError, ValueError, TypeError) as error:
        raise SyncError('Cannot read runtime synchronization identity: ' + str(error)) from error
    if config is None:
        yield
        return
    service_dir = Path(config['service_dir'])
    with _lock_file(service_dir / 'dispatch.lock') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SyncError('Developer runtime is switching; wait for the service to become ready.') from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def dispatch_guard(runtime_root):
    """Hold across preparation, calls and finalization; require current sources."""
    with operation_guard(runtime_root):
        status = source_status(runtime_root)
        if not status['current']:
            raise SyncError(status['reason'])
        yield


def _lock_file(path):
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    return os.fdopen(fd, 'a+')


@contextmanager
def idle_lock(service_dir):
    """Nonblocking exclusive lease; False means leave the current server alone."""
    with _lock_file(Path(service_dir) / 'dispatch.lock') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _port_available(port):
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    except OSError as error:
        raise SyncError('Port is occupied; stop the previous lab deliberately before starting this service.') from error


def _wait_server(process, port):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SyncError('Owned server exited before listening; see service.log.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise SyncError('Owned server did not listen within 10 seconds; see service.log.')


def validate_snapshot(receipt):
    """Syntax-check frozen Python without importing or executing actor/controller code."""
    snapshot = Path(receipt['snapshot'])
    manifest = _json(receipt['manifest'])
    for name in manifest['files']:
        if name.endswith('.py'):
            try:
                compile((snapshot / name).read_bytes(), name, 'exec', dont_inherit=True)
            except (SyntaxError, ValueError) as error:
                raise SyncError('Frozen Python syntax check failed: ' + str(error)) from error


def build_snapshot(root, state_dir, service_dir, expected):
    """Build off to the side; freeze validates archive equality before publication.

    No repository dist output is replaced. The existing builder's transaction,
    AST dependency checks and prompt-size checks run against current source.
    """
    launcher = _launcher()
    if source_digest(root) != expected:
        raise SyncError('Source changed before build; waiting for stable edits.')
    with tempfile.TemporaryDirectory(prefix='.build-', dir=str(service_dir)) as temp:
        program = ("import runpy,sys; d=runpy.run_path(sys.argv[1]); "
                   "d['main'].__globals__['DIST']=sys.argv[2]; d['main']()")
        result = subprocess.run([sys.executable, '-B', '-c', program,
                                 str(Path(root) / 'tools/build_dist.py'), temp],
                                cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=120, check=False)
        if result.returncode:
            raise SyncError('Public build failed: ' + result.stdout[-4000:])
        if source_digest(root) != expected:
            raise SyncError('Source changed during build; no runtime activated.')
        receipt = launcher.freeze(root, state_dir, Path(temp) / 'pea-princess-skill.zip',
            generated_source=Path(temp) / 'prompt-pack/INSTRUCTIONS.md',
            dev_sync={'source_root': str(Path(root).resolve()), 'source_digest': expected,
                      'service_dir': str(Path(service_dir).resolve())})
        validate_snapshot(receipt)
        if source_digest(root) != expected:
            # The immutable orphan is retained as evidence, never activated.
            raise SyncError('Source changed during freeze; no runtime activated.')
        return receipt


class Supervisor:
    """One owned child, immutable generations, stable-input debounce and idle switch."""
    def __init__(self, root, state_dir, service_dir, port, debounce=2.0,
                 builder=build_snapshot, popen=subprocess.Popen):
        self.root, self.state_dir, self.service_dir = map(Path, (root, state_dir, service_dir))
        self.port, self.debounce = port, debounce
        self.builder, self.popen = builder, popen
        self.process = None
        self.receipt = None
        self.active_digest = None
        self.observed = None
        self.since = None
        self.attempted = None
        self.pending = None
        self.stopping = False
        self.last_state = None

    def publish(self, state, **extra):
        data = {'state': state, 'pid': os.getpid(), 'server_pid': self.process.pid if self.process else None,
                'source_root': str(self.root), 'state_dir': str(self.state_dir), 'port': self.port,
                'snapshot': self.receipt['snapshot'] if self.receipt else None,
                'source_digest': self.observed, 'updated_at': time.time()}
        data.update(extra)
        _write(self.service_dir / 'status.json', data)
        transition = (state, extra.get('error'), self.observed)
        if transition != self.last_state:
            print(json.dumps(data, ensure_ascii=False), flush=True)
            self.last_state = transition

    def _stop_child(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Exclusive dispatch lock is held; no worker can be running.
                    self.process.kill()
                    self.process.wait(timeout=10)
            self.process = None

    def tick(self, now=None):
        now = time.monotonic() if now is None else now
        if self.stopping or (self.service_dir / 'stop.request').exists():
            with idle_lock(self.service_dir) as idle:
                if not idle:
                    self.publish('stop_waiting_for_idle')
                    return True
                self._stop_child()
                self.publish('stopped')
                return False
        try:
            digest = source_digest(self.root)
            if digest != self.observed:
                self.observed, self.since, self.pending = digest, now, None
                self.publish('debouncing')
                return True
            if now - self.since < self.debounce:
                return True
            if digest == self.active_digest and self.process is not None and self.process.poll() is None:
                # A transient missing file or reverted edit does not strand the
                # exact still-running generation in an error/debouncing state.
                self.publish('ready', receipt=self.receipt)
                return True
            if self.pending is None and digest != self.attempted:
                self.attempted = digest
                self.publish('building')
                self.pending = self.builder(self.root, self.state_dir, self.service_dir, digest)
            if self.pending is not None:
                with idle_lock(self.service_dir) as idle:
                    if not idle:
                        self.publish('waiting_for_idle')
                        return True
                    if source_digest(self.root) != digest:
                        self.pending = None
                        return True
                    self.publish('switching')
                    self._stop_child()
                    _port_available(self.port)
                    command = _launcher().server_command(self.pending['snapshot'], self.state_dir, self.port)
                    self.process = self.popen(command, stdin=subprocess.DEVNULL,
                                              cwd=str(self.root), close_fds=True)
                    _wait_server(self.process, self.port)
                    self.receipt, self.pending = self.pending, None
                    self.active_digest = digest
                    self.publish('ready', receipt=self.receipt)
            elif self.process is not None and self.process.poll() is not None:
                self.publish('error', error='Owned server exited; no automatic call or process retry. Stop/start the service to recover.')
            return True
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self.pending = None
            self.publish('error', error=str(error))
            return True


def _service_running(service_dir):
    path = service_dir / 'service.lock'
    if not path.exists():
        return False
    with _lock_file(path) as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False


def service_command(action, root, state_dir, port):
    root = Path(root).resolve()
    state_dir = _launcher().private_directory(state_dir)
    service_dir = _launcher().private_directory(state_dir / ('dev-service-%d' % port))
    running = _service_running(service_dir)
    if action == 'start' and running:
        previous = _json(service_dir / 'status.json')
        if previous.get('source_root') != str(root):
            raise SyncError('This service watches another source root; stop it before changing repositories.')
    if action == 'start' and not running:
        (service_dir / 'stop.request').unlink(missing_ok=True)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'run',
                   '--source-root', str(root), '--state-dir', str(state_dir), '--port', str(port)]
        with _lock_file(service_dir / 'service.log') as log:
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                             start_new_session=True, close_fds=True, cwd=str(root))
        # Wait only for lock ownership, not a build, server, or model response.
        for _ in range(40):
            if _service_running(service_dir):
                running = True
                break
            time.sleep(0.05)
    elif action == 'stop':
        _write(service_dir / 'stop.request', {'requested_at': time.time()})
    status_path = service_dir / 'status.json'
    result = {'running': running, 'service_dir': str(service_dir),
              'log': str(service_dir / 'service.log'), 'url': 'http://127.0.0.1:%d' % port,
              'status': _json(status_path) if status_path.exists() else None}
    if action == 'logs':
        log = service_dir / 'service.log'
        if log.exists():
            with log.open('rb') as handle:
                handle.seek(max(0, log.stat().st_size - 12000))
                result['tail'] = handle.read().decode('utf-8', errors='replace')
    if action == 'start' and running:
        previous = _json(service_dir / 'status.json')
        if previous.get('source_root') != str(root):
            raise SyncError('This service watches another source root; stop it before changing repositories.')
    if action == 'start' and not running:
        raise SyncError('Developer supervisor did not start; inspect ' + result['log'])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run',))
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    root = args.source_root.resolve()
    state = _launcher().private_directory(args.state_dir)
    service = _launcher().private_directory(state / ('dev-service-%d' % args.port))
    with _lock_file(service / 'service.lock') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        supervisor = Supervisor(root, state, service, args.port)
        def stop(signum, frame):
            supervisor.stopping = True
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        supervisor.publish('starting')
        while supervisor.tick():
            time.sleep(0.5)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
