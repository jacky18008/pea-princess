#!/usr/bin/env python3
"""Local public-options feedback staging. No HTTP service, model, or external submit.

Validate/import a public JSON file, search/export unverified counts, pause imports,
and withdraw using a local private receipt. Stdlib only. Run with --help.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import tempfile

if __package__:
    from . import core
else:
    import core


@contextmanager
def private_umask():
    previous = os.umask(0o077)
    try:
        yield
    finally:
        os.umask(previous)


def safe_path(value):
    path = Path(value).expanduser().absolute()
    for ancestor in (path,) + tuple(path.parents):
        if ancestor.is_symlink():
            raise core.Rejected('output_symlink_not_allowed')
    return path.resolve()


def write_private(path, value):
    path = safe_path(path)
    if path.exists() and not path.is_file():
        raise core.Rejected('output_must_be_regular_file')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        descriptor = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


class Store:
    def __init__(self, path, places):
        self.root, self.places = safe_path(path), places
        if self.root.exists() and not self.root.is_dir():
            raise core.Rejected('store_must_be_directory')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        for name in ('records.sqlite3', 'records.sqlite3-journal', 'receipts'):
            safe_path(self.root / name)
        database = self.root / 'records.sqlite3'
        if database.exists() and not database.is_file():
            raise core.Rejected('invalid_store')
        self.db = sqlite3.connect(str(database), timeout=5)
        database.chmod(0o600)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA temp_store=MEMORY')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, payload TEXT NOT NULL, '
                        'withdrawal_hash TEXT NOT NULL, withdrawn INTEGER NOT NULL DEFAULT 0)')
        fingerprint = core.digest(places)
        found = self.db.execute("SELECT value FROM meta WHERE key='catalog_sha256'").fetchone()
        if found and found[0] != fingerprint:
            self.db.close()
            raise core.Rejected('catalog_does_not_match_store')
        self.db.execute("INSERT OR IGNORE INTO meta VALUES ('catalog_sha256', ?)", (fingerprint,))
        self.db.execute("INSERT OR IGNORE INTO meta VALUES ('paused', '0')")
        self.db.commit()

    def close(self):
        self.db.close()

    def receive(self, value):
        value = core.validate(value, self.places)
        identifier = core.digest(value)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute("SELECT value FROM meta WHERE key='paused'").fetchone()[0] != '0':
                raise core.Rejected('imports_paused')
            existing = self.db.execute('SELECT withdrawn FROM reports WHERE id=?', (identifier,)).fetchone()
            if existing:
                self.db.rollback()
                return {'ok': True, 'status': 'withdrawn_duplicate' if existing[0] else 'duplicate',
                        'record_id': identifier, 'unverified': True}
            if self.db.execute('SELECT COUNT(*) FROM reports').fetchone()[0] >= core.MAX_REPORTS:
                raise core.Rejected('store_capacity_exceeded')
            receipt_path = safe_path(self.root / 'receipts' / (identifier + '.json'))
            if receipt_path.exists():
                # A crash before SQL commit may leave a receipt. Reuse its secret.
                receipt = check_receipt(core.load_json(receipt_path))
                if receipt['record_id'] != identifier:
                    raise core.Rejected('invalid_receipt')
            else:
                receipt = {'schema_version': 1, 'record_id': identifier,
                           'withdrawal_token': secrets.token_urlsafe(32)}
                write_private(receipt_path, receipt)
            token_hash = hashlib.sha256(receipt['withdrawal_token'].encode()).hexdigest()
            self.db.execute('INSERT INTO reports VALUES (?, ?, ?, 0)',
                            (identifier, core.canonical(value), token_hash))
            self.db.commit()
            return {'ok': True, 'status': 'imported_local_only', 'record_id': identifier,
                    'unverified': True, 'receipt_saved_locally': True}
        except Exception:
            self.db.rollback()
            raise

    def withdraw(self, receipt):
        receipt = check_receipt(receipt)
        expected = hashlib.sha256(receipt['withdrawal_token'].encode()).hexdigest()
        with self.db:
            found = self.db.execute('SELECT withdrawal_hash FROM reports WHERE id=?', (receipt['record_id'],)).fetchone()
            if not found or not secrets.compare_digest(found[0], expected):
                raise core.Rejected('invalid_receipt')
            self.db.execute('UPDATE reports SET withdrawn=1 WHERE id=?', (receipt['record_id'],))
        return {'ok': True, 'status': 'withdrawn_from_local_index', 'record_id': receipt['record_id'],
                'previous_exports_recalled': False}

    def index(self, place_id=None):
        rows = self.db.execute('SELECT id, payload FROM reports WHERE withdrawn=0 LIMIT ?',
                               (core.MAX_REPORTS + 1,)).fetchall()
        records = []
        for identifier, text in rows:
            if not isinstance(text, str) or len(text.encode()) > core.MAX_PAYLOAD_BYTES:
                raise core.Rejected('invalid_stored_public_record')
            try:
                row = json.loads(text, object_pairs_hook=core._pairs)
                core.validate(row, self.places, allow_older=True)
            except (ValueError, RecursionError, TypeError):
                raise core.Rejected('invalid_stored_public_record') from None
            if identifier != core.digest(row):
                raise core.Rejected('invalid_stored_public_record')
            records.append(row)
        return core.aggregate(records, self.places, place_id)

    def pause(self, value):
        with self.db:
            self.db.execute("UPDATE meta SET value=? WHERE key='paused'", ('1' if value else '0',))
        return {'ok': True, 'imports_paused': value}


def check_receipt(value):
    if not isinstance(value, dict) or set(value) != {'schema_version', 'record_id', 'withdrawal_token'}:
        raise core.Rejected('invalid_receipt')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise core.Rejected('invalid_receipt')
    if not isinstance(value['record_id'], str) or not re.fullmatch('[a-f0-9]{64}', value['record_id']):
        raise core.Rejected('invalid_receipt')
    if not isinstance(value['withdrawal_token'], str) or not re.fullmatch('[A-Za-z0-9_-]{43}', value['withdrawal_token']):
        raise core.Rejected('invalid_receipt')
    return value


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise core.Rejected('invalid_command_arguments')


def parser():
    root = Parser(description=__doc__)
    commands = root.add_subparsers(dest='command', required=True, parser_class=Parser)
    for name in ('validate', 'import', 'search', 'export', 'withdraw', 'pause', 'resume', 'catalog-check'):
        child = commands.add_parser(name)
        child.add_argument('--catalog', default=str(core.HERE / 'catalog.json'))
        if name not in ('validate', 'catalog-check'):
            child.add_argument('--store', required=True)
        if name in ('validate', 'import', 'withdraw'):
            child.add_argument('input')
        if name in ('search', 'export'):
            child.add_argument('--place-id')
        if name == 'export':
            child.add_argument('--out', required=True)
    return root


def main(argv=None):
    store = None
    try:
        with private_umask():
            args = parser().parse_args(argv)
            places = core.load_catalog(args.catalog)
            if args.command == 'catalog-check':
                result = {'ok': True, 'catalog_id': places['catalog_id'], 'demo': places['demo'],
                          'places': len(places['places'])}
            elif args.command == 'validate':
                core.validate(core.load_json(args.input), places)
                result = {'ok': True, 'status': 'valid_public_payload', 'unverified': True}
            else:
                store = Store(args.store, places)
                if args.command == 'import':
                    result = store.receive(core.load_json(args.input))
                elif args.command == 'withdraw':
                    result = store.withdraw(core.load_json(args.input))
                elif args.command in ('pause', 'resume'):
                    result = store.pause(args.command == 'pause')
                else:
                    result = {'ok': True, **store.index(args.place_id)}
                    if args.command == 'export':
                        output = safe_path(args.out)
                        if output.exists():
                            raise core.Rejected('export_destination_exists')
                        if store.root == output or store.root in output.parents:
                            raise core.Rejected('export_must_be_outside_private_store')
                        write_private(output, result)
                        result = {'ok': True, 'status': 'public_index_exported_local_only',
                                  'sample_count': result['sample_count']}
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
    except core.Rejected as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 2
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError, RecursionError):
        # No filename, submitted key/value, database content, or traceback escapes.
        print(json.dumps({'ok': False, 'error': 'local_operation_failed'}))
        return 2
    finally:
        if store is not None:
            store.close()


if __name__ == '__main__':
    sys.exit(main())
