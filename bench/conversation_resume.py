#!/usr/bin/env python3
"""Audited operational resumption of an unchanged native conversation experiment.

The original source tree, plan, prompts, schedule and receipts remain unchanged.
A private immutable amendment permits completing the same 192 CLI invocations
without the original processed-token stop threshold. Actual usage is still
recorded; missing usage, pending calls and failures still stop the frozen runner.
This is an operator assertion of an exact user authorization, not authentication
of that user. It neither adds retries nor authorizes Claude/new experiment cells.
"""
import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import threading


class ResumeError(ValueError):
    pass


class OperatorPaused(Exception):
    pass


_IMPORT_LOCK = threading.RLock()
_DEPENDENCIES = ('call_control', 'report_control', 'launch', 'durable_run',
                 'conversation_native', 'conversation_grading')
_FIELDS = {'version', 'amendment_id', 'operation', 'original_plan_sha256',
           'source_commit', 'original_token_ceiling', 'amended_token_ceiling',
           'max_cli_invocations', 'schedule_sha256', 'automatic_retries',
           'claude_calls', 'previous_amendment_sha256', 'authorization'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _path(path, directory=False):
    path = Path(path)
    if '..' in path.parts:
        raise ResumeError('parent traversal is not allowed')
    path = path.absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ResumeError('operational paths must not contain symlinks; use a canonical path')
    info = path.stat()
    if info.st_uid != os.getuid() or (directory and not stat.S_ISDIR(info.st_mode)):
        raise ResumeError('operational paths must be owned by the current account')
    return path


def _bytes(path, maximum=64 * 1024 * 1024):
    path = _path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise ResumeError('invalid or oversized operational file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(maximum + 1)
        if len(value) > maximum:
            raise ResumeError('operational file exceeds its bound')
        return value
    finally:
        os.close(fd)


def _pairs(rows):
    value = {}
    for key, item in rows:
        if key in value:
            raise ResumeError('duplicate JSON field')
        value[key] = item
    return value


def _read(path):
    try:
        return json.loads(_bytes(path, 4 * 1024 * 1024), object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ResumeError('non-finite JSON value')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ResumeError('invalid operational JSON') from error


def _load_frozen(source):
    """Load every bench dependency from the supplied tree, even in offline tests.

    Temporarily isolate the ordinary module names used by the original sources;
    restore the host interpreter's module table afterwards. Frozen module globals
    retain their own verified dependencies, so the current checkout cannot leak
    an imported controller/transport into the resumed experiment.
    """
    source = _path(source, directory=True)
    with _IMPORT_LOCK:
        previous = {name: sys.modules.get(name) for name in _DEPENDENCIES}
        old_path = list(sys.path)
        try:
            for name in _DEPENDENCIES:
                sys.modules.pop(name, None)
            sys.path.insert(0, str(source / 'bench'))
            spec = importlib.util.spec_from_file_location('_pea_frozen_conversation_ablation', source / 'bench/conversation_ablation.py')
            runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runner)
            origins = {name: Path(sys.modules[name].__file__).absolute() for name in _DEPENDENCIES}
            if any(path != source / 'bench' / (name + '.py') for name, path in origins.items()):
                raise ResumeError('frozen runner imported a dependency from another tree')
            return runner
        finally:
            sys.path[:] = old_path
            for name, module in previous.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


class Resume:
    def __init__(self, source, output, amendment):
        self.source = _path(source, directory=True)
        self.output = _path(output, directory=True)
        self.amendment_path = _path(amendment)
        self.wrapper_sha256 = hashlib.sha256(_bytes(Path(__file__).absolute())).hexdigest()
        self._verify_source_bytes()  # Verify bytes before executing any frozen Python.
        self.runner = _load_frozen(self.source)
        self.original_verify = self.runner.verify_plan
        self._validated()  # Missing/wrong amendment fails before any ledger access.
        self.runner.verify_plan = self._effective_plan

    def _verify_source_bytes(self):
        plan = _read(self.output / 'plan.json')
        frozen = _read(self.output / 'frozen.json')
        if _digest(plan) != frozen.get('plan_sha256'):
            raise ResumeError('original plan integrity differs')
        pins = plan.get('source_sha256')
        required = {'bench/conversation_ablation.py'} | {'bench/' + name + '.py' for name in _DEPENDENCIES}
        if not isinstance(pins, dict) or not required.issubset(pins):
            raise ResumeError('original plan lacks required source pins')
        for name, digest in pins.items():
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ResumeError('unsafe frozen source name')
            if hashlib.sha256(_bytes(self.source / relative)).hexdigest() != digest:
                raise ResumeError('frozen source differs: ' + name)

    def _validated(self):
        self._verify_source_bytes()
        plan = self.original_verify(self.output)
        amendment = _read(self.amendment_path)
        if not isinstance(amendment, dict) or set(amendment) != _FIELDS:
            raise ResumeError('amendment fields differ from the operational contract')
        if type(amendment['version']) is not int or amendment['version'] != 1:
            raise ResumeError('unsupported amendment version')
        if not isinstance(amendment['amendment_id'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', amendment['amendment_id']):
            raise ResumeError('unsafe amendment ID')
        expected = {'operation': 'complete_original_frozen_plan',
                    'original_plan_sha256': _digest(plan), 'source_commit': plan['source_commit'],
                    'original_token_ceiling': plan['processed_token_stop_before_next_call'],
                    'amended_token_ceiling': None, 'max_cli_invocations': 192,
                    'schedule_sha256': _digest(plan['calls']), 'automatic_retries': 0,
                    'claude_calls': 0, 'previous_amendment_sha256': None}
        if any(amendment[key] != value or type(amendment[key]) is not type(value) for key, value in expected.items()):
            raise ResumeError('amendment scope, source, schedule or original budget differs')
        if (len(plan['calls']) != 192 or len({c['id'] for c in plan['calls']}) != 192
                or plan['max_cli_invocations'] != 192 or plan['automatic_retries'] != 0 or plan['claude_calls'] != 0
                or plan['processed_token_stop_before_next_call'] != 6000000):
            raise ResumeError('original plan is not the authorized fixed 192-call schedule')
        auth = amendment['authorization']
        if (not isinstance(auth, dict) or set(auth) != {'actor', 'quote', 'source', 'authorized_at'}
                or auth['actor'] != 'user' or any(not isinstance(auth[k], str) or not auth[k].strip()
                                                for k in ('quote', 'source', 'authorized_at'))):
            raise ResumeError('exact user authorization quote, source and timestamp are required')
        try:
            timestamp = datetime.fromisoformat(auth['authorized_at'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError('timezone missing')
        except ValueError as error:
            raise ResumeError('authorization timestamp must include an ISO-8601 timezone') from error
        audit = {'version': 1, 'amendment_id': amendment['amendment_id'],
                 'amendment_sha256': _digest(amendment), 'amendment_file_sha256': hashlib.sha256(_bytes(self.amendment_path)).hexdigest(),
                 'original_plan_sha256': _digest(plan), 'source_commit': plan['source_commit'],
                 'source_sha256': plan['source_sha256'], 'wrapper_sha256': self.wrapper_sha256,
                 'source_root': str(self.source), 'output_root': str(self.output),
                 'operation': amendment['operation'], 'original_token_ceiling': amendment['original_token_ceiling'],
                 'amended_token_ceiling': None, 'max_cli_invocations': 192,
                 'authorization_quote_sha256': hashlib.sha256(auth['quote'].encode()).hexdigest()}
        self._check_audit(audit, create=False)
        return plan, audit

    def _check_audit(self, audit, create):
        directory = self.output / 'resume-audit'
        path = directory / (audit['amendment_id'] + '.json')
        if directory.exists() or directory.is_symlink():
            _path(directory, directory=True)
            if not path.exists() or _read(path) != audit:
                raise ResumeError('missing or changed immutable resume audit; inspect before resuming')
        elif create:
            directory.mkdir(mode=0o700)
            self.runner.native._write_new(path, _json(audit))

    def _effective_plan(self, output):
        if Path(output).absolute() != self.output:
            raise ResumeError('resume wrapper used for another experiment')
        if (self.output / 'PAUSE_REQUESTED.json').exists():
            raise OperatorPaused()
        plan, audit = self._validated()
        self._check_audit(audit, create=True)  # Original run_next holds experiment.lock here.
        amended = copy.deepcopy(plan)
        # Never serialize infinity or rewrite plan.json. This substitutes only
        # the original runner's stop-before-next-call comparison in memory.
        amended['processed_token_stop_before_next_call'] = math.inf
        return amended

    def status(self):
        self._validated()
        return {**self.runner.status(self.output), 'operational_amendment': _read(self.amendment_path)['amendment_id'],
                'original_token_ceiling': 6000000, 'amended_token_ceiling': None,
                'max_cli_invocations': 192}

    def step(self, roles=('answer', 'judge'), invoke=None):
        try:
            return self.runner.run_next(self.output, roles=roles, invoke=invoke)
        except OperatorPaused:
            return {'operator_paused': True, **self.status()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--amendment', required=True, type=Path)
    parser.add_argument('action', choices=('answers', 'judges', 'status'))
    args = parser.parse_args()
    try:
        resume = Resume(args.source, args.output, args.amendment)
        if args.action == 'status':
            print(json.dumps(resume.status(), ensure_ascii=False)); return 0
        roles = ('answer',) if args.action == 'answers' else ('judge',)
        while True:
            result = resume.step(roles=roles)
            print(json.dumps(result, ensure_ascii=False), flush=True)
            if result.get('complete') or result.get('awaiting_role') or result.get('operator_paused'):
                return 0
    except Exception as error:
        print(json.dumps({'stopped': True, 'error': type(error).__name__, 'message': str(error)}, ensure_ascii=False), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
