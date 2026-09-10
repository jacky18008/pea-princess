"""Private Claude-history export contracts using synthetic temporary JSONL only."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import import_claude_history as importer


def record(uid, role='user', content='Synthetic human request.', parent=None, **extra):
    value = {'type': role, 'uuid': uid, 'parentUuid': parent,
             'timestamp': '2026-01-02T03:04:05Z',
             'message': {'role': role, 'content': content}}
    value.update(extra)
    return value


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def fenced_blocks(markdown):
    fence = None
    body = []
    for line in markdown.splitlines(keepends=True):
        if fence is None:
            match = re.match(r'^(`{3,})[^`\n]*\n?$', line)
            if match:
                fence = match.group(1)
                body = []
        elif re.fullmatch(r'`{%d,}\s*' % len(fence), line):
            yield fence, ''.join(body)
            fence = None
        else:
            body.append(line)


class ImportClaudeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'synthetic-source.jsonl'
        self.manifest = self.base / 'sources.json'
        self.output = self.base / 'private-export'

    def write_source(self, rows, path=None):
        path = path or self.source
        path.write_bytes(b''.join(json.dumps(row, ensure_ascii=False).encode('utf-8') + b'\n'
                                  for row in rows))
        return path

    def write_manifest(self, sources=None):
        sources = sources or [{'path': self.source.name, 'session_id': 'session-one'}]
        self.manifest.write_text(json.dumps({'sources': sources}), encoding='utf-8')
        return self.manifest

    def export(self, rows=None):
        if rows is not None:
            self.write_source(rows)
        self.write_manifest()
        return importer.export_history(self.manifest, self.output)

    def session(self, name='session-one'):
        return self.output / 'sessions' / name

    def read_json(self, path):
        return json.loads(path.read_text(encoding='utf-8'))

    def read_jsonl(self, path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]

    def assert_failed_export(self, new_destination=False):
        if new_destination:
            self.rejection_number = getattr(self, 'rejection_number', 0) + 1
            self.output = self.base / ('rejected-export-%d' % self.rejection_number)
        with self.assertRaises((ValueError, OSError)):
            importer.export_history(self.manifest, self.output)
        audit = self.output / 'audit.json'
        if audit.exists():
            self.assertIsNot(self.read_json(audit).get('complete'), True)

    def test_mixed_visible_messages_and_machine_controls_stay_separate(self):
        queued = 'Queued human input, retained once as visible text.'
        unknown = 'Queued input whose origin was not recorded.'
        queued_control = '<task-notification>Queued machine completion.</task-notification>'
        rows = [
            record('u1', content='Original human request.'),
            record('a1', 'assistant', [{'type': 'thinking', 'thinking': 'Private reasoning trace.'},
                                      {'type': 'tool_use', 'id': 'tool-1', 'name': 'Read',
                                       'input': {'file_path': 'synthetic.txt'}},
                                      {'type': 'text', 'text': 'Visible assistant answer.'}], parent='u1'),
            record('tool-result', content=[{'type': 'tool_result', 'tool_use_id': 'tool-1',
                                           'content': 'Tool result, not a human request.'}], parent='a1'),
            record('meta', content='Internal meta instruction.', isMeta=True),
            record('compact-summary', content='Compacted earlier conversation.', isCompactSummary=True),
            record('api-error', 'assistant', 'Synthetic API failure.', isApiErrorMessage=True),
            record('notification', content='Background task completed.', origin={'kind': 'task-notification'}),
            record('sidechain', content='Private sidechain input.', isSidechain=True),
            record('command', content='<command-name>/clear</command-name>'),
            {'type': 'system', 'uuid': 'system', 'content': 'System-only data.'},
            {'type': 'queue-operation', 'uuid': 'enqueue', 'operation': 'enqueue', 'content': queued},
            {'type': 'attachment', 'uuid': 'queued-human', 'parentUuid': 'a1',
             'attachment': {'type': 'queued_command', 'prompt': queued, 'commandMode': 'prompt',
                            'origin': {'kind': 'human'}, 'timestamp': '2026-01-02T03:05:00Z'}},
            {'type': 'queue-operation', 'uuid': 'remove', 'operation': 'remove', 'content': queued},
            {'type': 'attachment', 'uuid': 'queued-unknown', 'parentUuid': 'a1',
             'attachment': {'type': 'queued_command', 'prompt': unknown, 'commandMode': 'prompt',
                            'source_uuid': 'u1'}},
            {'type': 'attachment', 'uuid': 'queued-machine-marker', 'parentUuid': 'a1',
             'attachment': {'type': 'queued_command', 'prompt': queued_control,
                            'commandMode': 'prompt', 'source_uuid': 'a1'}}]
        self.export(rows)
        messages = self.read_jsonl(self.session() / 'messages.jsonl')
        controls = self.read_jsonl(self.session() / 'controls.jsonl')
        visible = [entry.get('text') for entry in messages if isinstance(entry.get('text'), str)]
        self.assertEqual(['Original human request.', 'Visible assistant answer.', queued, unknown], visible)
        self.assertEqual(1, visible.count(queued))
        unknown_entry = next(entry for entry in messages if entry.get('text') == unknown)
        self.assertEqual('queued_input_unknown', unknown_entry['kind'])
        self.assertEqual('u1', unknown_entry['source_uuid'])
        self.assertIsNot(unknown_entry.get('independent_input'), True)
        retained = list(strings(controls))
        for text in ('Private reasoning trace.', 'Tool result, not a human request.',
                     'Internal meta instruction.', 'Compacted earlier conversation.',
                     'Synthetic API failure.', 'Background task completed.', queued,
                     'Private sidechain input.', queued_control):
            self.assertIn(text, retained)
        sidechain = next(entry for entry in controls if entry.get('text') == 'Private sidechain input.')
        self.assertIs(sidechain['isSidechain'], True)
        for entry in messages + controls:
            self.assertIn('source_line', entry)
            self.assertIn('kind', entry)
            self.assertIn('confidence', entry)
        self.assertTrue(self.read_json(self.session() / 'audit.json')['complete'])

    def test_repeated_message_id_retains_distinct_records_blocks_and_metadata(self):
        first = record('a1', 'assistant', [{'type': 'text', 'text': 'First block.'},
                                          {'type': 'text', 'text': 'Second block.'}], parent='missing',
                       logicalParentUuid='logical-parent', apiBlockIndex=7, effort='high')
        first['message'].update(id='same-message', model='synthetic-model')
        second = record('a2', 'assistant', [{'type': 'text', 'text': 'First block.'}], parent='a1',
                        apiBlockIndex=8, effort='high')
        second['message'].update(id='same-message', model='synthetic-model')
        self.export([first, second])
        entries = self.read_jsonl(self.session() / 'messages.jsonl')
        self.assertEqual(['a1', 'a1', 'a2'], [entry['uuid'] for entry in entries])
        self.assertEqual([0, 1, 0], [entry['block_index'] for entry in entries])
        self.assertEqual([1, 1, 2], [entry['source_line'] for entry in entries])
        self.assertEqual(['same-message'] * 3, [entry['message_id'] for entry in entries])
        self.assertEqual([7, 7, 8], [entry['apiBlockIndex'] for entry in entries])
        self.assertEqual('logical-parent', entries[0]['logicalParentUuid'])
        for entry in entries:
            self.assertEqual('synthetic-model', entry['model'])
            self.assertEqual('high', entry['effort'])
            self.assertEqual('2026-01-02T03:04:05Z', entry['timestamp'])

    def test_forks_gaps_compaction_and_logical_parent_are_descriptive(self):
        segment = {'headUuid': 'left', 'tailUuid': 'right', 'anchorUuid': 'root'}
        rows = [record('root'), record('left', 'assistant', 'Left sibling.', parent='root'),
                record('right', 'assistant', 'Right sibling.', parent='root'),
                record('gap', content='Missing-parent record.', parent='absent'),
                {'type': 'system', 'subtype': 'compact_boundary', 'uuid': 'compact',
                 'parentUuid': 'right', 'logicalParentUuid': 'root',
                 'compactMetadata': {'trigger': 'auto', 'preTokens': 100, 'preservedSegment': segment}},
                record('after', content='After compaction.', parent='compact'),
                record('cycle-one', parent='cycle-two'), record('cycle-two', parent='cycle-one')]
        self.export(rows)
        lineage = self.read_json(self.session() / 'lineage.json')
        for key in ('nodes', 'edges', 'roots', 'forks', 'missing_parents', 'compact_boundaries',
                    'message_id_groups', 'cycles', 'interpretation'):
            self.assertIn(key, lineage)
        self.assertTrue(lineage['forks'])
        self.assertIn('root', list(strings(lineage['roots'])))
        self.assertIn('absent', list(strings(lineage['missing_parents'])))
        self.assertTrue(lineage['compact_boundaries'])
        self.assertTrue(lineage['cycles'])
        self.assertIn(segment, [value.get('preservedSegment') for value in lineage['nodes']
                                if isinstance(value, dict)])
        all_strings = list(strings(lineage))
        self.assertIn('left', all_strings)
        self.assertIn('right', all_strings)
        self.assertIn('logicalParentUuid', json.dumps(lineage))
        self.assertNotIn('canonical_branch', lineage)
        self.assertNotIn('selected_branch', lineage)
        self.assertTrue(lineage['interpretation'])

    def test_binary_attachments_are_metadata_only_outside_raw_copy(self):
        payload = 'U1lOVEhFVElDX0JJTkFSWV9QQVlMT0FEX09OTFk='
        rows = [record('with-image', content=[{'type': 'text', 'text': 'Please inspect the attached example.'},
                    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': payload}},
                    {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': payload}}])]
        self.export(rows)
        raw = self.session() / 'raw/source.jsonl'
        self.assertIn(payload.encode(), raw.read_bytes())
        messages = self.read_jsonl(self.session() / 'messages.jsonl')
        self.assertGreaterEqual(len(messages), 3)
        metadata = list(strings(messages))
        self.assertIn('image/png', metadata)
        self.assertIn('application/pdf', metadata)
        for path in self.output.rglob('*'):
            if path.is_file() and path != raw:
                self.assertNotIn(payload.encode(), path.read_bytes(), str(path))

    def test_queued_block_lists_preserve_text_metadata_and_control_scope(self):
        payload = 'UVVFVUVEX0JJTkFSWV9QQVlMT0FEX1JBV19PTkxZ'
        image = {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': payload}}
        document = {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf',
                                                 'data': payload}}
        first_text = 'Queued human text exactly as supplied.'
        second_text = 'Second human block.\nKeep this line break.'
        unknown_text = 'Queued text whose origin is missing.'
        marker = '<task-notification>Machine result.</task-notification>'
        def queued(uid, blocks, origin=None):
            attachment = {'type': 'queued_command', 'prompt': blocks, 'commandMode': 'prompt',
                          'source_uuid': 'original-input', 'timestamp': '2026-01-02T03:05:00Z'}
            if origin is not None:
                attachment['origin'] = origin
            return {'type': 'attachment', 'uuid': uid, 'parentUuid': 'original-input',
                    'attachment': attachment}
        self.export([
            record('original-input', content='Original input representation.'),
            queued('queued-human-list', [{'type': 'text', 'text': first_text}, image,
                                        {'type': 'text', 'text': second_text}, document], {'kind': 'human'}),
            queued('queued-unknown-list', [{'type': 'text', 'text': unknown_text}, image]),
            queued('queued-marker-list', [{'type': 'text', 'text': marker}, document,
                                         {'type': 'text', 'text': 'Further machine detail.'}])])
        messages = self.read_jsonl(self.session() / 'messages.jsonl')
        controls = self.read_jsonl(self.session() / 'controls.jsonl')
        human = [entry for entry in messages if entry['uuid'] == 'queued-human-list']
        unknown = [entry for entry in messages if entry['uuid'] == 'queued-unknown-list']
        machine = [entry for entry in controls if entry['uuid'] == 'queued-marker-list']
        self.assertEqual([0, 1, 2, 3], [entry['block_index'] for entry in human])
        self.assertEqual([first_text, second_text], [entry['text'] for entry in human if 'text' in entry])
        self.assertEqual([0, 1], [entry['block_index'] for entry in unknown])
        self.assertEqual(unknown_text, unknown[0]['text'])
        self.assertEqual('queued_input_unknown', unknown[0]['kind'])
        self.assertEqual([0, 1, 2], [entry['block_index'] for entry in machine])
        self.assertEqual([marker, 'Further machine detail.'],
                         [entry['text'] for entry in machine if 'text' in entry])
        self.assertFalse(any(entry['uuid'] == 'queued-marker-list' for entry in messages))
        for entry in human:
            self.assertEqual({'kind': 'human'}, entry['origin'])
        for entry in unknown:
            self.assertIn(entry.get('origin'), (None, {}))
            self.assertIsNot(entry.get('independent_input'), True)
        for entry in human + unknown + machine:
            self.assertEqual('original-input', entry['source_uuid'])
            self.assertEqual('2026-01-02T03:05:00Z', entry['attachment_timestamp'])
        self.assertIn('image/png', list(strings(human)))
        self.assertIn('application/pdf', list(strings(human)))
        raw = self.session() / 'raw/source.jsonl'
        self.assertIn(payload.encode(), raw.read_bytes())
        for path in self.output.rglob('*'):
            if path.is_file() and path != raw:
                self.assertNotIn(payload.encode(), path.read_bytes(), str(path))
        self.assertEqual(2, self.read_json(self.output / 'audit.json')['schema_version'])

    def test_source_text_is_exact_and_html_backticks_remain_fenced(self):
        text = 'Literal <img src=x onerror=alert(1)>\n```````````\n# Not a heading\n&amp; $HOME'
        self.export([record('literal', content=text)])
        entries = self.read_jsonl(self.session() / 'messages.jsonl')
        self.assertEqual(text, entries[0]['text'])
        markdown = (self.session() / 'conversation.md').read_text(encoding='utf-8')
        containing = [(fence, body) for fence, body in fenced_blocks(markdown) if text in body]
        self.assertEqual(1, len(containing))
        self.assertGreater(len(containing[0][0]), 11)

    def test_malformed_json_invalid_utf8_and_nonobjects_are_not_silently_skipped(self):
        valid = json.dumps(record('valid')).encode() + b'\n'
        original = valid + b'{bad json\n' + b'\xff\xfe\n' + b'[]\n'
        self.source.write_bytes(original)
        self.export()
        self.assertEqual(original, self.source.read_bytes())
        self.assertEqual(original, (self.session() / 'raw/source.jsonl').read_bytes())
        audit = self.read_json(self.session() / 'audit.json')
        self.assertFalse(audit['complete'])
        self.assertEqual([2, 3, 4], [entry['source_line'] for entry in audit['malformed_lines']])
        controls = self.read_jsonl(self.session() / 'controls.jsonl')
        self.assertTrue({2, 3, 4}.issubset({entry['source_line'] for entry in controls}))
        self.assertFalse(self.read_json(self.output / 'audit.json')['complete'])

    def test_empty_source_is_explicitly_incomplete_and_export_is_private(self):
        self.source.write_bytes(b'')
        self.export()
        expected = ['README.md', 'index.md', 'audit.json', 'selected-sources.json',
                    'sessions/session-one/raw/source.jsonl', 'sessions/session-one/conversation.md',
                    'sessions/session-one/messages.jsonl', 'sessions/session-one/controls.jsonl',
                    'sessions/session-one/lineage.json', 'sessions/session-one/audit.json']
        self.assertTrue(all((self.output / name).is_file() for name in expected))
        self.assertFalse(self.read_json(self.output / 'audit.json')['complete'])
        self.assertFalse(self.read_json(self.session() / 'audit.json')['complete'])
        for path in [self.output, *self.output.rglob('*')]:
            self.assertEqual(0o700 if path.is_dir() else 0o600, stat.S_IMODE(path.stat().st_mode), str(path))

    def test_duplicate_ids_source_paths_and_record_uuids_are_rejected(self):
        self.write_source([record('u1')])
        cases = [[{'path': self.source.name, 'session_id': 'same'},
                  {'path': self.source.name, 'session_id': 'same'}],
                 [{'path': self.source.name, 'session_id': 'one'},
                  {'path': str(self.source), 'session_id': 'two'}]]
        for sources in cases:
            with self.subTest(sources=sources):
                self.write_manifest(sources)
                self.assert_failed_export(new_destination=True)
        other = self.write_source([record('different')], self.base / 'other.jsonl')
        self.write_manifest([{'path': self.source.name, 'session_id': 'same'},
                             {'path': other.name, 'session_id': 'same'}])
        self.assert_failed_export(new_destination=True)
        self.write_source([record('duplicate'), record('duplicate', content='Different text, same UUID.')])
        self.write_manifest()
        self.assert_failed_export(new_destination=True)

    def test_unsafe_ids_symlink_sources_and_existing_destinations_are_rejected(self):
        self.write_source([record('u1')])
        for uid in ('', '.', '..', '../escape', 'bad/name', '/absolute'):
            with self.subTest(session_id=uid):
                self.write_manifest([{'path': self.source.name, 'session_id': uid}])
                self.assert_failed_export(new_destination=True)
        alias = self.base / 'alias.jsonl'
        alias.symlink_to(self.source)
        self.write_manifest([{'path': alias.name, 'session_id': 'one'}])
        self.assert_failed_export(new_destination=True)
        source_dir = self.base / 'real-source-dir'
        source_dir.mkdir()
        nested = self.write_source([record('u2')], source_dir / 'source.jsonl')
        directory_alias = self.base / 'directory-alias'
        directory_alias.symlink_to(source_dir, target_is_directory=True)
        self.write_manifest([{'path': str(directory_alias / nested.name), 'session_id': 'one'}])
        self.assert_failed_export(new_destination=True)
        self.write_manifest()
        self.output.mkdir(exist_ok=True)
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('Unchanged existing destination.')
        self.assert_failed_export()
        self.assertEqual('Unchanged existing destination.', sentinel.read_text())
        target_directory = self.output
        self.output = self.base / 'destination-link'
        self.output.symlink_to(target_directory, target_is_directory=True)
        self.assert_failed_export()
        self.assertEqual('Unchanged existing destination.', sentinel.read_text())
        parent_directory = self.base / 'real-export-parent'
        parent_directory.mkdir()
        parent_alias = self.base / 'export-parent-link'
        parent_alias.symlink_to(parent_directory, target_is_directory=True)
        self.output = parent_alias / 'new-export'
        self.assert_failed_export()
        self.assertFalse((parent_directory / 'new-export').exists())

    def test_stream_copy_detects_source_change_and_never_marks_export_complete(self):
        self.write_source([record('changing')])
        self.write_manifest()
        original_copy = importer._copy_stream
        source_copies = []
        def mutate_after_copy(source_stream, destination_stream):
            result = original_copy(source_stream, destination_stream)
            if os.fstat(source_stream.fileno()).st_ino == self.source.stat().st_ino:
                source_copies.append(True)
                with self.source.open('ab') as stream:
                    stream.write(b'changed after the streamed copy\n')
            return result
        with patch.object(importer, '_copy_stream', side_effect=mutate_after_copy) as copy_stream:
            self.assert_failed_export()
            self.assertEqual(1, len(source_copies))
            self.assertGreaterEqual(copy_stream.call_count, 2)

    def test_git_destination_requires_ignored_playground_and_no_tracked_entries(self):
        self.write_source([record('u1')])
        self.write_manifest()
        repo = self.base / 'synthetic-repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
        self.output = repo / '.pea-playground/export'
        self.assert_failed_export()
        (repo / '.gitignore').write_text('.pea-playground/\nother-private/\n')
        self.output = repo / 'other-private/export'
        self.assert_failed_export()
        self.output = repo / '.pea-playground/good'
        importer.export_history(self.manifest, self.output)
        self.assertTrue((self.output / 'audit.json').is_file())
        tracked = repo / '.pea-playground/tracked/history.jsonl'
        tracked.parent.mkdir()
        tracked.write_text('Synthetic tracked placeholder.')
        subprocess.run(['git', '-C', str(repo), 'add', '-f', str(tracked)], check=True, capture_output=True)
        tracked.unlink()
        tracked.parent.rmdir()
        self.output = tracked.parent
        self.assert_failed_export()

    def test_cli_exports_selected_absolute_source_without_changing_original(self):
        self.write_source([record('u1', content='Synthetic CLI export.')])
        original = self.source.read_bytes()
        before = hashlib.sha256(original).hexdigest()
        self.write_manifest([{'path': str(self.source), 'session_id': 'explicit-session'}])
        run = subprocess.run([sys.executable, str(ROOT / 'tools/import_claude_history.py'),
                              '--sources', str(self.manifest), '--output', str(self.output)],
                             check=False, capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertIsInstance(json.loads(run.stdout), dict)
        self.assertEqual(before, hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(original, (self.session('explicit-session') / 'raw/source.jsonl').read_bytes())
        audit = self.read_json(self.output / 'audit.json')
        self.assertTrue(audit['complete'])
        self.assertIsNot(audit.get('visibility_complete'), True)


if __name__ == '__main__':
    unittest.main()
