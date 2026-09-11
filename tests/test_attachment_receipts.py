"""Attachment metadata is request-bound evidence, never an assertion of reading."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'skills/vet-flat/scripts')]
import session_runner as runner
import playground_review as review
from session_state import SessionStore


class AttachmentReceiptTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name).resolve()
        self.store = SessionStore(self.folder)
        self.store.init('attachment-offline')
        for event in [
            {'op': 'budget.set', 'id': 'tokens', 'scope': 'api_tokens', 'limit': 10000,
             'unit': 'tokens', 'provenance': {'actor': 'user', 'authorized': True,
                 'source_id': 'synthetic-user', 'quote': 'Allow 10000 synthetic tokens'}},
            {'op': 'task.add', 'id': 'check', 'title': 'Inspect supplied evidence',
             'acceptance': ['Preserve attachment receipts'], 'budget_ids': ['tokens']}]:
            self.store.apply(event, self.store.show()['revision'])
        self.files = [dict(id='upload-1', name='房源 <script>alert(1)</script>.png',
                           bytes=123, sha256='a' * 64, path='/not-opened/current.png',
                           image=True, source_kind='upload', mime_type='image/png'),
                      dict(id='upload-2', name='prior.pdf', bytes=456, sha256='b' * 64,
                           path='/not-opened/copied.pdf', original_path='/not-opened/original.pdf',
                           image=False, source_kind='local_path')]
        usage = {'input_tokens': 15, 'cached_input_tokens': 5, 'output_tokens': 5}
        raw = '\n'.join(json.dumps(e) for e in [
            {'type': 'thread.started', 'thread_id': 'synthetic'}, {'type': 'turn.started'},
            {'type': 'item.completed', 'item': {'id': 'message', 'type': 'agent_message', 'text': 'Saved answer'}},
            {'type': 'turn.completed', 'usage': usage}])
        self.record = runner.cli_record('answer', runner.launch.LaunchResult(stdout=raw, exit_code=0), 'codex')
        self.record['answer'] = 'Saved answer'
        patch = mock.patch('durable_run.source_fingerprint', return_value={'synthetic.py': 'frozen'})
        patch.start(); self.addCleanup(patch.stop)
        patch = mock.patch.object(runner.launch, 'run', side_effect=AssertionError('No real model call'))
        patch.start(); self.addCleanup(patch.stop)
        self.session = {'id': 'synthetic-session', 'calls': [], 'messages': []}

    def run_step(self, **changes):
        options = dict(project=self.folder, call_id='check-1', task_id='check', model='synthetic-model',
                       prompt='Inspect provided evidence', token_budget_id='tokens',
                       tool_policy='live_research', input_files=self.files,
                       invoke=lambda *_: copy.deepcopy(self.record))
        options.update(changes)
        receipt = runner.run_step(**options)
        self.session['calls'].append({'id': 'check-1', 'actor': 'assistant', 'status': 'complete', 'receipt': receipt})
        self.session['messages'].append({'role': 'assistant', 'call_id': 'check-1', 'text': 'Saved answer'})
        return receipt

    def manifest_path(self):
        return self.folder / '.pea-state/runs/check-1/manifest.json'

    def detail(self):
        return review.build_call(self.folder, self.session, 'check-1')

    def test_request_and_physical_identity_include_metadata_before_invoke(self):
        expected = copy.deepcopy(self.files)
        def invoke(request, folder):
            saved = json.loads((folder / 'manifest.json').read_text())['value']
            self.assertEqual(expected, request['input_files'])
            self.assertEqual(saved['request_hash'], runner._digest(request))
            name = hashlib.sha256(b'answer').hexdigest() + '.json'
            physical = json.loads((folder / 'physical/requests' / name).read_text())['value']
            self.assertEqual(request, physical['request'])
            # The caller's original list cannot mutate the already copied request.
            self.files[0]['name'] = 'caller changed its object'
            self.assertEqual(expected, request['input_files'])
            return copy.deepcopy(self.record)
        receipt = self.run_step(invoke=invoke)
        self.assertEqual('complete', receipt['physical_status'])
        attachment = self.detail()['input_files']
        self.assertEqual('bound', attachment['status'])
        self.assertEqual(expected, attachment['items'])
        self.assertIn('not proof', attachment['note'])
        self.assertFalse(Path(expected[0]['path']).exists())
        self.assertEqual(20, self.store.show()['budgets']['tokens']['spent'])
        runner.recover(self.folder, 'check-1')
        self.assertEqual(20, self.store.show()['budgets']['tokens']['spent'])

    def test_defaults_and_empty_files_preserve_old_request_shape(self):
        self.run_step(input_files=[])
        self.assertNotIn('input_files', json.loads(self.manifest_path().read_text())['value']['request'])
        self.assertEqual('not_recorded', self.detail()['input_files']['status'])
        self.assertEqual('text_only', runner._manifest_tool_policy({'version': 1, 'request': {}}))
        with self.assertRaises(ValueError):
            runner._manifest_tool_policy({'version': 1, 'request': {'input_files': []}})

    def test_default_adapter_and_text_only_reject_before_state_or_invocation(self):
        invoke = mock.Mock(return_value=self.record)
        for changes in ({'invoke': None}, {'invoke': invoke, 'tool_policy': 'text_only'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'custom invoke'):
                self.run_step(**changes)
        invoke.assert_not_called()
        self.assertEqual({}, self.store.show()['dispatches'])
        self.assertFalse(self.manifest_path().exists())

    def test_invalid_metadata_never_dispatches(self):
        bad_rows = [dict(self.files[0], bytes=True), dict(self.files[0], bytes=-1),
                    dict(self.files[0], bytes=2 ** 53), dict(self.files[0], image=1),
                    dict(self.files[0], sha256='A' * 64), dict(self.files[0], path='relative.png'),
                    dict(self.files[0], path='/tmp/../outside'), dict(self.files[0], original_path='relative'),
                    dict(self.files[0], name='x' * 256), dict(self.files[0], name='bad\nname'),
                    dict(self.files[0], source_kind=''), dict(self.files[0], mime_type=4),
                    dict(self.files[0], id='../id'), dict(self.files[0], unknown='extra')]
        invoke = mock.Mock(return_value=self.record)
        for files in [[row] for row in bad_rows] + [[self.files[0]] * 2, [self.files[0]] * 49, {}, 'files']:
            with self.subTest(files=files), self.assertRaises(ValueError):
                self.run_step(input_files=files, invoke=invoke)
        invoke.assert_not_called()
        self.assertFalse(self.store.show()['dispatches'])

    def test_48_files_and_prior_image_flag_are_supported(self):
        rows = [dict(self.files[0], id='file-%d' % n, image=n == 0) for n in range(48)]
        self.run_step(input_files=rows)
        result = self.detail()['input_files']
        self.assertEqual(48, len(result['items']))
        self.assertEqual(1, sum(row['image'] for row in result['items']))

    def test_original_path_keeps_explicit_parent_segments_as_provenance(self):
        self.files[1]['original_path'] = '/not-opened/folder/../original.pdf'
        self.run_step()
        attachment = self.detail()['input_files']
        self.assertEqual('bound', attachment['status'])
        self.assertEqual(self.files, attachment['items'])
        self.assertEqual('/not-opened/folder/../original.pdf',
                         attachment['items'][1]['original_path'])
        runner.recover(self.folder, 'check-1')
        self.assertEqual(20, self.store.show()['budgets']['tokens']['spent'])

    def test_attachment_tampering_cannot_preserve_request_binding(self):
        self.run_step()
        saved = json.loads(self.manifest_path().read_text())
        saved['value']['request']['input_files'][0]['sha256'] = 'c' * 64
        saved['sha256'] = runner._digest(saved['value'])
        self.manifest_path().write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError, 'request integrity'):
            runner.recover(self.folder, 'check-1')
        detail = self.detail()
        self.assertFalse(detail['integrity']['ok'])
        self.assertEqual('unbound', detail['input_files']['status'])
        self.assertIsNone(detail['input_files']['request_sha256'])

    def test_rehashing_manifest_still_conflicts_with_physical_request(self):
        self.run_step()
        saved = json.loads(self.manifest_path().read_text())
        saved['value']['request']['input_files'][0]['name'] = 'changed'
        saved['value']['request_hash'] = runner._digest(saved['value']['request'])
        saved['sha256'] = runner._digest(saved['value'])
        self.manifest_path().write_text(json.dumps(saved))
        with self.assertRaises(ValueError):
            runner.recover(self.folder, 'check-1')
        self.assertEqual('unbound', self.detail()['input_files']['status'])

    def test_invalid_saved_metadata_is_not_exposed_as_trusted_items(self):
        self.run_step()
        saved = json.loads(self.manifest_path().read_text())
        saved['value']['request']['input_files'][0]['image'] = 'true'
        saved['sha256'] = runner._digest(saved['value'])
        self.manifest_path().write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError, 'image'):
            runner.recover(self.folder, 'check-1')
        self.assertEqual('invalid', self.detail()['input_files']['status'])
        self.assertEqual([], self.detail()['input_files']['items'])

    def test_json_and_markdown_exports_preserve_inert_metadata(self):
        self.run_step()
        packet = {'messages': [{'role': 'human', 'text': 'See this file', 'attachments': self.files}],
                  'selected_call': self.detail()}
        raw = review._export_bytes(packet)
        self.assertEqual(self.files, json.loads(raw)['selected_call']['input_files']['items'])
        self.assertEqual(self.files, json.loads(raw)['messages'][0]['attachments'])
        markdown = review.export_markdown(packet)
        self.assertIn('附件收據（不代表模型已讀取）', markdown)
        self.assertIn(self.files[0]['name'], markdown)
        self.assertIn('/not-opened/original.pdf', markdown)
        self.assertIn('"status": "bound"', markdown)

    @unittest.skipUnless(shutil.which('node'), 'Node is unavailable')
    def test_actual_attachment_renderer_uses_only_inert_text_nodes(self):
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
class Element{constructor(tag,text){this.tag=tag;this.textContent=text;this.children=[];}append(...nodes){this.children.push(...nodes);}set innerHTML(_){throw Error('HTML parsing forbidden');}}
const context=vm.createContext({node:(tag,text)=>new Element(tag,text),numbers:v=>String(v)});
vm.runInContext(source.slice(source.indexOf(' function attachmentList('),source.indexOf(' function stash(')),context);
context.receipt={status:'bound',items:[{name:'<img src=x onerror=evil()>',path:'javascript:evil()',bytes:1,source_kind:'<script>evil()</script>',sha256:'a'.repeat(64),image:true}]};
const result=vm.runInContext('attachmentList(receipt)',context);
const nodes=n=>[n,...n.children.flatMap(nodes)];const all=nodes(result);
assert(all.every(n=>['div','h4','p','ul','li','strong','span','code'].includes(n.tag)));
assert(all.some(n=>n.textContent==='<img src=x onerror=evil()>'));
assert(all.some(n=>String(n.textContent).includes('不代表模型已讀取')));
assert(source.includes('attachmentList(d.input_files)'));
context.receipt.status='message_metadata';
const message=nodes(vm.runInContext('attachmentList(receipt)',context));
assert(message.some(n=>n.textContent==='訊息附件'));
assert(message.some(n=>String(n.textContent).includes('不代表某次模型呼叫已收到或讀取')));
assert(!message.some(n=>String(n.textContent).includes('本次標記為圖片輸入')));
assert(source.includes("attachmentList({status:'message_metadata',items:m.attachments})"));
console.log('attachment renderer safe');
'''
        result = subprocess.run([shutil.which('node'), '-e', script, str(ROOT / 'playground/review.js')],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
