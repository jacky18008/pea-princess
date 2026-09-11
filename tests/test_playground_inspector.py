"""Inspector HTTP boundaries and read/review operations never dispatch models."""
import copy
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
import uuid
from unittest import mock
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import persona_playground as p


class InspectorHTTP(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.invoked=mock.Mock(side_effect=AssertionError('inspection must not call model'))
        self.lab=p.Lab(Path(self.temp.name).resolve(),invoke=self.invoked);self.addCleanup(self.lab.close)
        self.sid=self.lab.create(dict(client_id=str(uuid.uuid4()),research_mode='live',output_mode='agent',initial_request='Compare my two saved flats.',model='gpt-6-astra',max_calls=3,max_tokens=10000,seed=1))['id']
        s=self.lab._load(self.sid)
        # An incomplete historical record is reviewable as an observed message,
        # but must not acquire fabricated zero usage or a passing integrity badge.
        s['calls'].append({'id':'call-001','actor':'assistant','status':'failed','receipt':{'answer':'<script>untrusted</script>'}})
        self.lab._save(s)
        self.server=p.ThreadingHTTPServer(('127.0.0.1',0),p.Handler);self.server.lab=self.lab
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.shutdown)
    def shutdown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3)
    def request(self,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        h={'X-Pea-Client':'persona-lab'} if headers is None else headers
        if body is not None:h=dict(h,**{'Content-Type':'application/json'})
        c.request('GET' if body is None else 'POST',path,body=json.dumps(body) if body is not None else None,headers=h)
        r=c.getresponse();result=r.status,r.read();c.close();return result
    def test_read_packet_and_note_never_change_conversation_or_dispatch(self):
        before=(self.lab._folder(self.sid)/'session.json').read_bytes()
        base='/api/session/'+self.sid
        for route in ('/inspect','/inspect/call-001','/review-packet','/reviews'):
            code,body=self.request(base+route);self.assertEqual(code,200,body)
        data=json.loads(self.request(base+'/inspect')[1]);self.assertIsNone(data['totals']['processed_tokens']['value']);self.assertEqual(1,data['totals']['processed_tokens']['unknown_calls'])
        payload=dict(client_id=str(uuid.uuid4()),call_id='call-001',reviewer='agent',rating='problem',severity='medium',tags=['missed_question'],note='Did not answer the heating question.')
        first=json.loads(self.request(base+'/reviews',payload)[1]);self.assertTrue(first['created'])
        second=json.loads(self.request(base+'/reviews',payload)[1]);self.assertFalse(second['created'])
        self.assertEqual(first['review'],second['review']);self.assertEqual(before,(self.lab._folder(self.sid)/'session.json').read_bytes());self.invoked.assert_not_called()
        packet=json.loads(self.request(base+'/review-packet')[1]);self.assertEqual(1,len(packet['reviews']['reviews']));self.assertIn('call-001',packet['call_detail_routes'])
        detail=json.loads(self.request(base+'/inspect/call-001')[1])
        expected={k:detail['source'].get(k) for k in ('record_sha256','message_sha256','displayed_sha256')}
        for kind in ('json','md'):
            code,body=self.request(base+'/review-export',dict(call_id='call-001',format=kind,expected_source=expected));self.assertEqual(200,code,body)
            saved=json.loads(body);path=Path(saved['path']);self.assertTrue(path.is_file());self.assertIn('review-exports',path.parts);self.assertEqual(saved['bytes'],path.stat().st_size)
            if kind=='json':self.assertEqual('call-001',json.loads(path.read_text())['selected_call']['call_id'])
        wrong=dict(expected,displayed_sha256='0'*64)
        self.assertEqual(400,self.request(base+'/review-export',dict(call_id='call-001',format='json',expected_source=wrong))[0])
        self.assertEqual(before,(self.lab._folder(self.sid)/'session.json').read_bytes());self.invoked.assert_not_called()
    def test_private_guards_static_allowlist_and_invalid_note(self):
        base='/api/session/'+self.sid
        for path in ('/inspect','/inspect/call-001','/reviews','/review-packet'):
            self.assertEqual(403,self.request(base+path,headers={})[0])
            self.assertEqual(403,self.request(base+path,headers={'X-Pea-Client':'persona-lab','Origin':'https://bad.test'})[0])
        for path in ('/review.js','/review.css'):
            self.assertEqual(200,self.request(path,headers={})[0])
        self.assertEqual(404,self.request(base+'/inspect/../../session.json')[0])
        self.assertEqual(400,self.request(base+'/reviews',{'call_id':'call-001'})[0]);self.invoked.assert_not_called()


class InspectorUI(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node unavailable')
    def test_actual_inspector_handlers(self):
        r=subprocess.run([shutil.which('node'),str(Path(__file__).with_suffix('.js'))],capture_output=True,text=True,timeout=20)
        self.assertEqual(0,r.returncode,r.stdout+r.stderr)
        self.assertIn('inspector functional checks passed',r.stdout)

if __name__=='__main__':unittest.main()
