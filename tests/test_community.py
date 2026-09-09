"""Offline privacy, schema, local lifecycle and output-boundary regression tests."""
import contextlib
import datetime
import io
import json
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest import mock

from community import build, core, feedback

NOW = datetime.date(2026, 9, 9)
SECRET = 'PRIVATE-NOTE-never-publish-address-bank-password'


def example(month=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    index = now.year * 12 + now.month - 2
    month = month or '%04d-%02d' % (index // 12, index % 12 + 1)
    return {'schema_version': 1, 'place_id': 'demo-orchid-court', 'experience_month': month,
            'experience_kind': 'lived', **{key: 'good' for key in core.DIMENSIONS},
            'overall': 'would_return', 'consent': True, 'license': core.LICENSE}


class PublicSchema(unittest.TestCase):
    def setUp(self):
        self.places = core.load_catalog()

    def test_exact_schema_types_enums_and_catalog_ids(self):
        self.assertEqual(example('2026-08'), core.validate(example('2026-08'), self.places, NOW))
        for field, value in [('consent', False), ('schema_version', True), ('schema_version', 1.0),
                             ('place_id', SECRET), ('overall', 'other: ' + SECRET),
                             ('experience_kind', {'note': SECRET}), ('cleanliness', 5),
                             ('license', 'MIT')]:
            with self.subTest(field=field), self.assertRaises(core.Rejected):
                core.validate(dict(example('2026-08'), **{field: value}), self.places, NOW)
        for key in ('note', 'comment', 'name', 'author_id', 'address', 'url', '__proto__', SECRET):
            with self.subTest(key=key), self.assertRaises(core.Rejected) as error:
                core.validate(dict(example('2026-08'), **{key: SECRET}), self.places, NOW)
            self.assertNotIn(SECRET, str(error.exception))
        missing = example('2026-08')
        missing.pop('noise')
        with self.assertRaises(core.Rejected):
            core.validate(missing, self.places, NOW)

    def test_only_completed_months_within_ingestion_window(self):
        for month in ('2026-09', '2026-10', '2021-08', '2026-00', '2026-13', '2026-8',
                      '2026-08-01', SECRET):
            with self.subTest(month=month), self.assertRaises(core.Rejected):
                core.validate(example(month), self.places, NOW)
        core.validate(example('2021-09'), self.places, NOW)
        # Accepted records do not break the entire index when they age past five years.
        result = core.aggregate([example('2021-09')], self.places, today=datetime.date(2027, 9, 9))
        self.assertEqual(1, result['sample_count'])

    def test_catalog_requires_curated_unique_ids_without_unknown_fields(self):
        for mutate in (lambda c: c.update(note=SECRET),
                       lambda c: c['places'].append(c['places'][0]),
                       lambda c: c['places'][0].update(url=SECRET),
                       lambda c: c['places'][0].update(place_id='somewhere-real'),
                       lambda c: c['places'][0].update(name='name\n' + SECRET)):
            value = json.loads(json.dumps(self.places))
            mutate(value)
            with self.assertRaises(core.Rejected):
                core.catalog(value)

    def test_json_schema_matches_runtime_keys_and_is_generated_reproducibly(self):
        self.assertEqual(core.schema(self.places), json.loads((core.HERE / 'public-schema.json').read_text()))
        self.assertEqual(set(example()), set(core.schema(self.places)['required']))
        self.assertFalse(core.schema(self.places)['additionalProperties'])
        self.assertEqual(build.render(self.places), (core.HERE / 'index.html').read_text())

    def test_catalog_active_content_is_inert_in_built_document(self):
        malicious = json.loads(json.dumps(self.places))
        malicious['places'][0]['name'] = '</script><script>alert(1)</script>&\u2028'
        text = build.render(malicious)
        self.assertNotIn('</script><script>alert(1)', text)
        self.assertIn('\\u003c/script\\u003e', text)
        self.assertIn("connect-src 'none'", text)
        self.assertIn("form-action 'none'", text)
        self.assertNotIn("'unsafe-inline'", text)


class LocalLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.store = self.root / 'private-store'
        self.payload = self.root / 'public.json'
        self.payload.write_text(json.dumps(example()))

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = feedback.main(list(args))
        self.assertEqual('', err.getvalue())
        self.assertNotIn(SECRET, out.getvalue())
        return code, json.loads(out.getvalue())

    def import_one(self):
        code, value = self.cli('import', str(self.payload), '--store', str(self.store))
        self.assertEqual(0, code)
        return value

    def test_import_dedupe_search_and_withdraw_are_local_and_public_only(self):
        first = self.import_one()
        self.assertEqual('imported_local_only', first['status'])
        self.assertEqual('duplicate', self.import_one()['status'])
        receipt = self.store / 'receipts' / (first['record_id'] + '.json')
        private = json.loads(receipt.read_text())
        self.assertNotIn(private['withdrawal_token'], json.dumps(first))
        code, index = self.cli('search', '--store', str(self.store))
        self.assertEqual(0, code)
        self.assertEqual(1, index['sample_count'])
        self.assertTrue(index['demo'])
        self.assertTrue(index['unverified'])
        self.assertNotIn('withdrawal_token', json.dumps(index))
        self.assertNotIn(first['record_id'], json.dumps(index))
        public_index = self.root / 'index.json'
        self.assertEqual(0, self.cli('export', '--store', str(self.store), '--out', str(public_index))[0])
        original_export = public_index.read_bytes()
        self.assertEqual(0, self.cli('withdraw', str(receipt), '--store', str(self.store))[0])
        self.assertEqual(0, self.cli('withdraw', str(receipt), '--store', str(self.store))[0])
        self.assertEqual(0, self.cli('search', '--store', str(self.store))[1]['sample_count'])
        self.assertEqual('withdrawn_duplicate', self.import_one()['status'])
        self.assertEqual(original_export, public_index.read_bytes())
        self.assertEqual(2, self.cli('export', '--store', str(self.store), '--out', str(public_index))[0])

    def test_interrupted_import_reuses_saved_receipt_without_counting_twice(self):
        places = core.load_catalog()
        with feedback.private_umask():
            store = feedback.Store(self.store, places)
            self.addCleanup(store.close)
            original = core.canonical
            def fail_payload(value):
                # Digest is needed first; fail the later payload serialization after receipt creation.
                fail_payload.count += 1
                if fail_payload.count == 2:
                    raise ValueError('synthetic interrupted write')
                return original(value)
            fail_payload.count = 0
            with mock.patch.object(core, 'canonical', side_effect=fail_payload), self.assertRaises(ValueError):
                store.receive(example())
            receipts = list((self.store / 'receipts').glob('*.json'))
            self.assertEqual(1, len(receipts))
            saved = receipts[0].read_bytes()
            self.assertEqual(0, store.index()['sample_count'])
            self.assertEqual('imported_local_only', store.receive(example())['status'])
            self.assertEqual(saved, receipts[0].read_bytes())
            self.assertEqual(1, store.index()['sample_count'])

    def test_pause_blocks_new_imports_but_not_search_and_withdraw(self):
        first = self.import_one()
        self.cli('pause', '--store', str(self.store))
        self.assertEqual('imports_paused', self.cli('import', str(self.payload), '--store', str(self.store))[1]['error'])
        self.assertEqual(1, self.cli('search', '--store', str(self.store))[1]['sample_count'])
        receipt = self.store / 'receipts' / (first['record_id'] + '.json')
        self.assertEqual(0, self.cli('withdraw', str(receipt), '--store', str(self.store))[0])
        self.cli('resume', '--store', str(self.store))
        changed = example()
        changed['overall'] = 'unsure'
        self.payload.write_text(json.dumps(changed))
        self.assertEqual('imported_local_only', self.import_one()['status'])

    def test_wrong_withdrawal_receipt_does_not_remove_other_reports(self):
        first = self.import_one()
        receipt = json.loads((self.store / 'receipts' / (first['record_id'] + '.json')).read_text())
        receipt['withdrawal_token'] = 'x' * 43
        bad = self.root / 'bad-receipt.json'
        bad.write_text(json.dumps(receipt))
        self.assertEqual('invalid_receipt', self.cli('withdraw', str(bad), '--store', str(self.store))[1]['error'])
        self.assertEqual(1, self.cli('search', '--store', str(self.store))[1]['sample_count'])

    def test_private_note_rejected_at_all_public_entry_and_error_paths(self):
        for value in (dict(example(), note=SECRET), {'comment': SECRET}, SECRET,
                      dict(example(), place_id=SECRET), {SECRET: SECRET}):
            self.payload.write_text(json.dumps(value))
            self.assertEqual(2, self.cli('validate', str(self.payload))[0])
            self.assertEqual(2, self.cli('import', str(self.payload), '--store', str(self.store))[0])
        self.assertEqual(0, self.cli('search', '--store', str(self.store))[1]['sample_count'])
        self.assertEqual(2, self.cli('search', '--store', str(self.store), '--place-id', SECRET)[0])
        self.assertEqual(2, self.cli('--' + SECRET)[0])
        self.assertEqual(2, self.cli('validate', str(self.root / SECRET))[0])

    def test_duplicate_keys_deep_json_nonfinite_and_oversize_inputs_fail_without_echo(self):
        for raw in ('{"note":"%s","note":"%s"}' % (SECRET, SECRET), '[' * 3000 + ']' * 3000,
                    '{"note":NaN}', SECRET * core.MAX_PAYLOAD_BYTES):
            self.payload.write_text(raw)
            self.assertEqual(2, self.cli('validate', str(self.payload))[0])

    def test_private_permissions_and_input_output_symlinks(self):
        first = self.import_one()
        for path, mode in ((self.store, 0o700), (self.store / 'records.sqlite3', 0o600),
                           (self.store / 'receipts' / (first['record_id'] + '.json'), 0o600)):
            self.assertEqual(mode, stat.S_IMODE(path.stat().st_mode))
        alias = self.root / 'alias'
        alias.symlink_to(self.store, target_is_directory=True)
        self.assertEqual(2, self.cli('search', '--store', str(alias))[0])
        linked = self.root / 'linked.json'
        linked.symlink_to(self.payload)
        self.assertEqual(2, self.cli('validate', str(linked))[0])
        self.assertEqual(2, self.cli('export', '--store', str(self.store), '--out', str(alias / 'export.json'))[0])
        self.assertFalse((self.store / 'export.json').exists())

    def test_dotdot_store_alias_cannot_bypass_public_export_separation(self):
        self.import_one()
        alias = self.root / 'unused' / '..' / 'private-store'
        (self.root / 'unused').mkdir()
        output = self.store / 'misplaced-public.json'
        code, result = self.cli('export', '--store', str(alias), '--out', str(output))
        self.assertEqual(2, code)
        self.assertEqual('export_must_be_outside_private_store', result['error'])
        self.assertFalse(output.exists())

    def test_tampered_stored_payload_cannot_leak_through_index_or_error(self):
        first = self.import_one()
        tainted = dict(example(), note=SECRET)
        with sqlite3.connect(str(self.store / 'records.sqlite3')) as db:
            db.execute('UPDATE reports SET id=?, payload=? WHERE id=?',
                       (core.digest(tainted), core.canonical(tainted), first['record_id']))
        code, result = self.cli('search', '--store', str(self.store))
        self.assertEqual(2, code)
        self.assertEqual('invalid_stored_public_record', result['error'])
        public_index = self.root / 'tainted.json'
        self.assertEqual(2, self.cli('export', '--store', str(self.store), '--out', str(public_index))[0])
        self.assertFalse(public_index.exists())

    def test_catalog_changes_cannot_silently_relabel_stored_places(self):
        self.import_one()
        catalog = core.load_catalog()
        catalog['places'][0]['name'] = 'different operator label'
        file = self.root / 'changed-catalog.json'
        file.write_text(json.dumps(catalog))
        result = self.cli('search', '--store', str(self.store), '--catalog', str(file))
        self.assertEqual(2, result[0])
        self.assertEqual('catalog_does_not_match_store', result[1]['error'])

    def test_capacity_is_bounded_and_duplicate_does_not_buy_another_sample(self):
        with mock.patch.object(core, 'MAX_REPORTS', 1):
            self.import_one()
            self.assertEqual('duplicate', self.import_one()['status'])
            self.payload.write_text(json.dumps(dict(example(), overall='unsure')))
            self.assertEqual('store_capacity_exceeded', self.cli('import', str(self.payload), '--store', str(self.store))[1]['error'])

    def test_build_will_not_overwrite_its_catalog_input(self):
        catalog = self.root / 'catalog.json'
        catalog.write_bytes((core.HERE / 'catalog.json').read_bytes())
        before = catalog.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            code = build.main(['--catalog', str(catalog), '--out', str(self.root / 'form.html'), '--schema-out', str(catalog)])
        self.assertEqual(2, code)
        self.assertEqual(before, catalog.read_bytes())


if __name__ == '__main__':
    unittest.main()
