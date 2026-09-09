"""Durable, serial execution boundary for the legacy benchmark entrypoints.

Dry runs and offline grading keep their old CLI. Live invocations require an owned
output directory and explicit physical-call and processed-token ceilings. Nested
A/B jobs share one ledger in-process; raw result files are never resume authority.
"""
import functools
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
_ACTIVE = None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def add_arguments(parser):
    parser.add_argument('--durable-dir', '--control-dir', dest='durable_dir',
                        help='owned durable directory for this bounded live invocation')
    parser.add_argument('--max-calls', type=int, help='explicit ceiling on physical model calls')
    parser.add_argument('--max-processed-tokens', '--max-total-tokens', dest='max_total_tokens', type=int,
                        help='explicit processed-token ceiling; usage is checked after each call')
    parser.add_argument('--allow-claude', action='store_true',
                        help='explicitly unpause Claude for this new invocation; default paused')


def active():
    return _ACTIVE is not None and not _ACTIVE.offline


def offline_args(args):
    regrade = getattr(args, 'regrade', None)
    offline_regrade = regrade and (not hasattr(args, 'rules_only') or args.rules_only)
    return bool(getattr(args, 'dry_run', False) or offline_regrade
                or getattr(args, 'check', False) or getattr(args, 'menu_probe', False))


def _fingerprints(args):
    """Bind selected inputs and the implementation without storing their contents."""
    paths = set()
    for folder in ('skills/vet-flat', 'bench/ab/configs', 'dist/prompt-pack'):
        paths.update(p for p in (ROOT / folder).rglob('*') if p.is_file())
    for name in ('VETFLAT_SKILL_DIR', 'VETFLAT_SKILL_MD_OVERRIDE'):
        value = os.environ.get(name)
        if value:
            source = Path(value)
            if source.is_file():
                paths.add(source)
            elif source.is_dir():
                paths.update(p for p in source.rglob('*') if p.is_file())
            else:
                raise ValueError('missing pinned skill input: ' + name)
    paths.update((ROOT / 'bench').glob('*.py'))
    paths.update((ROOT / 'bench/ab').glob('*.py'))
    for key in ('cases', 'evals', 'journeys', 'personas', 'tasks', 'config', 'config_dir', 'regrade', 'retry_failed'):
        value = getattr(args, key, None)
        if value:
            source = Path(value)
            if source.is_file():
                paths.add(source)
            elif source.is_dir():
                paths.update(p for p in source.rglob('*') if p.is_file())
    # Referenced profiles/documents are inputs too, including private task files.
    for path in tuple(paths):
        if path.suffix in ('.yaml', '.yml'):
            for match in re.finditer(r'(?m)^skill_md_override:\s*[\"\']?([^\n\"\']+)', path.read_text()):
                value = match.group(1).strip()
                source = Path(value) if Path(value).is_absolute() else ROOT / value
                if not source.is_file():
                    raise ValueError('missing configured skill override: ' + str(source))
                paths.add(source)
        if path.suffix != '.json':
            continue
        try:
            value = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        def visit(node):
            if isinstance(node, dict):
                for key, item in node.items():
                    if key == 'files' and isinstance(item, list):
                        for rel in item:
                            if isinstance(rel, str):
                                source = path.parent / rel
                                if source.is_file():
                                    paths.add(source)
                    if key in ('input_path', 'profile', 'path', 'source', 'src', 'file', 'raw', 'redundancy_raw') and isinstance(item, str):
                        for candidate in (Path(item), path.parent / item, ROOT / item, ROOT / 'evals/personas/fixtures' / item):
                            if candidate.is_file():
                                paths.add(candidate)
                    visit(item)
            elif isinstance(node, list):
                for item in node:
                    visit(item)
        visit(value)
    out = {}
    for path in sorted(paths):
        if any(part in ('.git', '.cache', '__pycache__') or part == '.env'
               for part in path.parts) or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('durable input cannot be a symlink: ' + str(path))
        out[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class Session:
    def __init__(self, args, identity):
        self.args, self.identity = args, identity
        self.offline = offline_args(args)
        self.controller = None
        self.ordinal = 0
        self.job_id = identity
        self.config = None

    def ensure(self):
        if self.offline:
            raise ValueError('offline invocation cannot dispatch a model')
        if self.controller is None:
            from durable_run import DurableRun
            folder = getattr(self.args, 'durable_dir', None)
            calls = getattr(self.args, 'max_calls', None)
            tokens = getattr(self.args, 'max_total_tokens', None)
            if not folder or type(calls) is not int or calls <= 0 or type(tokens) is not int or tokens <= 0:
                raise ValueError('live legacy runs require --durable-dir, --max-calls > 0 and '
                                 '--max-processed-tokens > 0; Claude remains paused by default')
            values = {k: v for k, v in vars(self.args).items() if not k.startswith('_')}
            self.config = {'runner': self.identity, 'arguments': values,
                           'input_sha256': _fingerprints(self.args), 'physical_calls_serial': True,
                           'environment': {k: os.environ.get(k) for k in (
                               'VETFLAT_SKILL_DIR', 'VETFLAT_SKILL_MD_OVERRIDE', 'VETFLAT_CLAUDE_RESUME')}}
            self.controller = DurableRun(folder, ['call-%06d' % n for n in range(1, calls + 1)],
                                         self.config, allow_tools=True,
                                         allow_claude=bool(getattr(self.args, 'allow_claude', False)),
                                         max_total_tokens=tokens)
        return self.controller

    def next_call(self):
        controller = self.ensure()
        self.ordinal += 1
        if self.ordinal > self.args.max_calls:
            raise ValueError('physical-call ceiling reached; no additional model call may start')
        return controller, 'call-%06d' % self.ordinal

    def finished(self, code):
        if self.controller is None:
            return
        report = self.controller.report()
        if report.get('paused') or report.get('pending_call_ids') or report.get('failed_calls'):
            from call_control import CallControlError
            raise CallControlError('cannot finalize an unresolved or failed physical-call ledger')
        for n in range(self.ordinal + 1, self.args.max_calls + 1):
            self.controller.skip('call-%06d' % n, 'runner finished without this optional call')
        from call_control import _atomic_json
        result = {'exit_code': code, 'config_sha256': digest(self.config)}
        _atomic_json(Path(self.args.durable_dir) / 'legacy-completed.json',
                     {'result': result, 'sha256': digest(result)})

    def completed(self):
        self.ensure()
        path = Path(self.args.durable_dir) / 'legacy-completed.json'
        if not path.exists():
            return None
        envelope = json.loads(path.read_text())
        result = envelope['result']
        if envelope['sha256'] != digest(result) or result['config_sha256'] != digest(self.config):
            raise ValueError('completed legacy run metadata differs')
        report = self.controller.report()
        if not report.get('plan_complete') or report.get('paused') or report.get('failed_calls'):
            raise ValueError('completed marker has no matching complete physical-call ledger')
        return result['exit_code']


def entrypoint(function):
    @functools.wraps(function)
    def wrapped(argv=None):
        global _ACTIVE
        # run_ab invokes child mains in-process so all calls share one ceiling.
        if _ACTIVE is not None:
            return function(argv)
        args = function.__globals__['build_parser']().parse_args(argv)
        session = Session(args, Path(function.__globals__['__file__']).name)
        _ACTIVE = session
        original_override = os.environ.get('VETFLAT_SKILL_MD_OVERRIDE')
        try:
            # Do not create a durable run for malformed commands; the existing main
            # reports its own usage errors. Completed calls replay through the ledger.
            effective_argv = list(sys.argv[1:] if argv is None else argv)
            if active() and getattr(args, 'durable_dir', None):
                session.completed()  # validate any marker, then replay every frozen call below
                # Outputs belong to this new run, never to historical result folders.
                root = Path(args.durable_dir).resolve()
                results = Path(args.results).resolve() if getattr(args, 'results', None) else root / 'results'
                owned_path(results, root)
                reject_links(results)
                if not getattr(args, 'results', None):
                    effective_argv += ['--results', str(results)]
                for flag in ('regrade', 'retry_failed'):
                    source = getattr(args, flag, None)
                    if source:
                        recovered = recovery_copy(source, root / 'results' / (Path(source).name + '-' + flag))
                        effective_argv += ['--' + flag.replace('_', '-'), recovered]
                if hasattr(args, 'day') and not args.day:
                    # Replaying across midnight must address the same logical outputs.
                    effective_argv += ['--day', 'durable']
            code = function(effective_argv)
            if not session.offline:
                session.finished(code)
            return code
        except Exception as exc:
            from call_control import CallControlError
            if isinstance(exc, (CallControlError, ValueError)):
                print('durable execution stopped: %s' % exc, file=sys.stderr)
                return 2
            raise
        finally:
            if original_override is None:
                os.environ.pop('VETFLAT_SKILL_MD_OVERRIDE', None)
            else:
                os.environ['VETFLAT_SKILL_MD_OVERRIDE'] = original_override
            _ACTIVE = None
    return wrapped


def job(label):
    if active():
        _ACTIVE.job_id = str(label)


def workdir(requested=None):
    if not active():
        return requested
    _ACTIVE.ensure()
    root = Path(_ACTIVE.args.durable_dir).resolve()
    suffix = re.sub(r'[^A-Za-z0-9_.-]+', '-', _ACTIVE.job_id)[:80] + '-' + digest(_ACTIVE.job_id)[:12]
    path = root / 'workdirs' / suffix
    if requested and Path(requested).resolve() != path:
        raise ValueError('live workdirs are owned by --durable-dir; omit --workdir')
    owned_path(path, root)
    reject_links(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return str(path)


def session_id(label='claude'):
    if not active():
        return str(uuid.uuid4())
    # Stable without writing a mutable file into a workdir snapshot.
    _ACTIVE.ensure()
    return str(uuid.uuid5(uuid.NAMESPACE_URL,
                         str(Path(_ACTIVE.args.durable_dir).resolve()) + '/' + _ACTIVE.job_id + '/' + label))


def run_cli(cmd, cwd, timeout, family, **kwargs):
    if not active():
        raise ValueError('model calls require a durable legacy invocation')
    if family not in ('claude', 'codex'):
        raise ValueError('live telemetry is not supported for backend ' + str(family))
    options = list(cmd[:cmd.index('--')]) if '--' in cmd else list(cmd)
    if family == 'codex' and '--json' not in options:
        raise ValueError('Codex calls require --json telemetry before dispatch')
    if family == 'claude':
        formats = [options[n + 1] for n, item in enumerate(options[:-1]) if item == '--output-format']
        if formats != ['json']:
            raise ValueError('Claude calls require --output-format json telemetry before dispatch')
    models = [options[n + 1] for n, flag in enumerate(options[:-1]) if flag in ('--model', '-m')]
    models += [flag.split('=', 1)[1] for flag in options if str(flag).startswith('--model=')]
    if len(models) != 1:
        raise ValueError('new live calls require exactly one explicit --model/-m')
    require_model(models[0], family)
    controller, call_id = _ACTIVE.next_call()
    label = kwargs.pop('label', None) or 'model'
    return controller.run_cli(call_id, _ACTIVE.job_id, str(label), 'legacy', cmd, cwd,
                              timeout, family, **kwargs)


def run_api(callback, model, request):
    if not active():
        raise ValueError('API model calls require a durable legacy invocation')
    require_model(model)
    request = dict(request, endpoint_sha256=hashlib.sha256(
        os.environ.get('OPENAI_BASE_URL', '').encode()).hexdigest())
    controller, call_id = _ACTIVE.next_call()
    return controller.run_api(call_id, _ACTIVE.job_id, 'api', 'legacy', callback,
                              model=model, request_identity=request)


def require_model(model, family=None):
    if not active():
        return
    if not isinstance(model, str) or not model.strip() or model.lower() in {
            'sonnet', 'opus', 'haiku', 'default', 'latest', 'auto'} or model.lower().endswith('-latest'):
        raise ValueError('new live runs require an explicit model name, not a default/latest alias')
    if (family == 'claude' or 'claude' in model.lower()) and not _ACTIVE.args.allow_claude:
        raise ValueError('Claude remains paused; --allow-claude explicitly opts in for a new run')


def result_day(default):
    return 'durable' if active() else default


def recovery_copy(source, destination):
    """Reset derived recovery outputs from read-only historical evidence on replay."""
    source, destination = Path(source), Path(destination)
    if not source.is_dir() or source.is_symlink():
        raise ValueError('recovery source must be a real directory')
    root = Path(_ACTIVE.args.durable_dir).resolve()
    resolved_source = source.resolve()
    if (root == resolved_source or root in resolved_source.parents or resolved_source in root.parents):
        raise ValueError('recovery source and this new durable run must not contain each other')
    owned_path(destination, root)
    reject_links(destination)
    files, size = [], 0
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('recovery source contains a symlink')
        if not path.is_dir() and not path.is_file():
            raise ValueError('recovery source contains a non-regular artifact')
        if path.is_file():
            files.append(path)
            size += path.stat().st_size
    if len(files) > 2000 or size > 32 * 1024 * 1024:
        raise ValueError('recovery source exceeds 2000 files / 32 MiB')
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError('recovery output must be an owned directory')
        shutil.rmtree(destination)
    destination.mkdir(parents=True, mode=0o700)
    for path in files:
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(path.read_bytes())
        target.chmod(0o600)
    return str(destination)


def reply_text(result, family):
    if family != 'codex':
        return result.text
    messages = []
    for line in (result.stdout or result.text or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get('item') if isinstance(event, dict) else None
        if (isinstance(event, dict) and event.get('type') == 'item.completed' and isinstance(item, dict)
                and item.get('type') == 'agent_message' and isinstance(item.get('text'), str)):
            messages.append(item['text'])
    return messages[-1] if messages else ('' if active() else result.text)


def owned_path(path, root):
    path, root = Path(path), Path(root).resolve()
    if root not in path.resolve().parents:
        raise ValueError('live outputs must remain strictly inside --durable-dir')
    for ancestor in (path,) + tuple(path.parents):
        if ancestor == root:
            break
        if ancestor.is_symlink():
            raise ValueError('owned output path contains a symlink')


def reject_links(path):
    path = Path(path)
    if not path.exists():
        return
    for candidate in [path] + list(path.rglob('*') if path.is_dir() else []):
        if candidate.is_symlink() or not (candidate.is_dir() or candidate.is_file()):
            raise ValueError('owned output contains a symlink or non-regular artifact')
