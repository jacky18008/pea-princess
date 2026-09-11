"""Explicit file selections survive turns and become pinned actor inputs."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import persona_playground as p


def intent(**data):
    return dict(client_id=str(uuid.uuid4()),**data)


class FileIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.requests=[]
        def invoke(request,folder):
            self.requests.append(copy.deepcopy(request))
            for file in request.get('input_files',[]):
                raw=Path(file['path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),file['sha256'])
            return {'id':'answer','status':'complete','exit_code':0,'errors':[],
                    'tool_events':[],'malformed_event_lines':0,'terminal_usage_events':1,
                    'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                    'answer':json.dumps({'message':'Read the selected evidence.','questions':[]})}
        self.lab=p.Lab(self.root/'sessions',invoke=invoke);self.addCleanup(self.close)

    def close(self):
        if self.lab.worker:self.lab.worker.join(10)
        self.lab.close()

    def join(self):
        self.lab.worker.join(10);self.assertFalse(self.lab.worker.is_alive())

    def create(self,text='Read the supplied file without browsing.',**extra):
        data=intent(research_mode='live',output_mode='agent',initial_request=text,
                    model='gpt-6-astra',max_calls=4,max_tokens=10000,seed=1)
        data.update(extra)
        return self.lab.create(data)['id']

    def upload(self,name='notes.txt',raw=b'Only this selected document.'):
        return self.lab.upload({'name':name,'content_base64':base64.b64encode(raw).decode()})

    def test_upload_and_create_do_not_dispatch_and_snapshot_survives_original_change(self):
        original=self.root/'租屋 條件.txt';original.write_text('Version one: minimum 47 square metres.')
        record=self.lab.upload({'path':str(original)})
        sid=self.create(attachments=[record['id']]);self.assertEqual([],self.requests)
        original.write_text('Changed outside the test conversation.')
        self.lab.control(sid,intent(action='step'));self.join()
        request=self.requests[0];file=request['input_files'][0]
        self.assertIn('Version one',Path(file['path']).read_text())
        self.assertNotEqual(str(original),file['path'])
        self.assertIn(file['path'],request['prompt'])
        self.assertEqual(record['sha256'],self.lab.snapshot(sid)['messages'][0]['attachments'][0]['sha256'])
        inspected=self.lab.inspect(sid,'call-001-assistant')
        self.assertEqual('bound',inspected['input_files']['status'])

    def test_plain_path_line_and_attachment_only_followup_are_retained_once(self):
        original=self.root/'notes with spaces.txt';original.write_text('Original source bytes.')
        sid=self.create(str(original))
        self.lab.control(sid,intent(action='step'));self.join()
        record=self.upload();message=intent(text='',kind='question',attachments=[record['id']])
        self.lab.message(sid,message);self.join()
        self.lab.message(sid,message)
        self.assertEqual(2,len(self.requests))
        self.assertEqual(2,len(self.requests[-1]['input_files']))
        human=[m for m in self.lab.snapshot(sid)['messages'] if m['role']=='human'][-1]
        self.assertEqual('',human['text']);self.assertEqual(record['id'],human['attachments'][0]['id'])

    def test_attachment_only_opening_works_and_missing_file_does_not_dispatch(self):
        record=self.upload();sid=self.create('',attachments=[record['id']])
        self.assertEqual('',self.lab.snapshot(sid)['messages'][0]['text'])
        self.lab.control(sid,intent(action='step'));self.join();self.assertEqual(1,len(self.requests))
        with self.assertRaises(p.LabError):self.create(str(self.root/'absent.txt'))
        self.assertEqual(1,len(self.requests))

    def test_private_attachment_rejected_for_synthetic_persona(self):
        record=self.upload()
        with self.assertRaises(p.LabError):
            self.lab.create(intent(persona_id='P4',model='gpt-6-astra',max_calls=4,max_tokens=10000,seed=1,attachments=[record['id']]))
        self.assertEqual([],self.requests)

    def test_path_mentioned_in_prose_or_prohibition_is_not_a_file_selection(self):
        original=self.root/'not-selected.txt';original.write_text('Never import this source.')
        for text in ["Do not read '%s'; explain the risk." % original,
                     'A pasted log mentioned:\n'+str(original),
                     'Example: `'+str(original)+'`']:
            sid=self.create(text)
            self.assertNotIn('attachments',self.lab._load(sid))
        self.assertEqual([],self.requests)

    def test_retained_snapshot_tampering_stops_before_dispatch(self):
        record=self.upload();sid=self.create(attachments=[record['id']])
        file=self.lab._load(sid)['attachments'][record['id']]
        path=Path(file['path']);path.chmod(0o600);path.write_text('tampered')
        self.lab.control(sid,intent(action='step'));self.join()
        self.assertEqual([],self.requests);self.assertEqual('error',self.lab.snapshot(sid)['status'])


if __name__=='__main__':unittest.main()
