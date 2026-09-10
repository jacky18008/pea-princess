"""Independent source capture stays separate from the model's claims and trace."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import persona_playground as p
import public_source_snapshot

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.lab=p.Lab(Path(self.tmp.name).resolve(),invoke=lambda *_:self.fail('no model'))
        self.addCleanup(self.lab.close)
        sid=self.lab.create(dict(research_mode='live',initial_request='Find a home.',model='gpt-6-astra',max_calls=2,max_tokens=10000,seed=1,client_id=str(uuid.uuid4())))['id']
        self.s=self.lab._load(sid);self.s['calls']=[{'id':'call-001-assistant'}]
    def receipt(self,message):
        return {'status':'recorded','physical_status':'complete','answer':json.dumps({'message':message,'questions':[]})}
    def capture(self,url,folder):
        folder.mkdir(mode=0o700);raw=b'Advertised rent: 2000. Availability for this person: unconfirmed.'
        (folder/'text.txt').write_bytes(raw)
        return {'source_url':url,'ok':True,'http_status':200,'retrieved_at':'2026-09-10T23:00:00Z','role':'independent_host_capture_after_actor','source_claims_verified':False,'text_sha256':hashlib.sha256(raw).hexdigest()}
    def test_cited_sources_deduplicated_bounded_retained_and_reloaded_without_fetch(self):
        message=' '.join('[source](https://www.foxtons.co.uk/unit/%s)'%i for i in (1,1,2,3,4))
        with mock.patch.object(public_source_snapshot,'capture',side_effect=self.capture) as capture:
            self.lab._capture_sources(self.s,'call-001-assistant',self.receipt(message))
            self.assertEqual(3,capture.call_count)
            self.lab._capture_sources(self.s,'call-001-assistant',self.receipt(message))
            self.assertEqual(3,capture.call_count)
        rows=self.lab._read_snapshots(self.s,'call-001-assistant')
        self.assertEqual(4,len(rows));self.assertFalse(rows[0]['source_claims_verified'])
        self.assertIn('capture limit',rows[-1]['note'])
        context=self.lab._source_context(self.s)
        self.assertIn('Advertised rent: 2000.',context);self.assertIn('not the original model tool result',context)
        # Source contents cannot turn into author instructions or availability confirmation.
        self.assertIn('untrusted evidence',context)
    def test_invalid_response_or_failed_call_never_triggers_fetch(self):
        with mock.patch.object(public_source_snapshot,'capture',side_effect=AssertionError('no fetch')):
            self.lab._capture_sources(self.s,'bad',{'status':'failed','physical_status':'failed'})
            r=self.receipt('');r['answer']='not a response object'
            self.lab._capture_sources(self.s,'bad',r)
        self.assertFalse(self.lab._snapshot_index(self.s,'bad').exists())
    def test_source_failure_preserved_without_reclassifying_answer(self):
        r=self.receipt('[source](https://www.foxtons.co.uk/unit/1)')
        with mock.patch.object(public_source_snapshot,'capture',side_effect=TimeoutError('private internal error')):
            self.lab._capture_sources(self.s,'call-001-assistant',r)
        saved=self.lab._read_snapshots(self.s,'call-001-assistant')[0]
        self.assertFalse(saved['ok']);self.assertEqual('recorded',r['status'])
        self.assertNotIn('private internal error',json.dumps(saved))
    def test_corrupt_or_oversize_body_is_explicitly_omitted_without_silent_clipping(self):
        with mock.patch.object(public_source_snapshot,'capture',side_effect=self.capture):
            self.lab._capture_sources(self.s,'call-001-assistant',self.receipt('[source](https://www.foxtons.co.uk/unit/1)'))
        path=self.lab._snapshot_index(self.s,'call-001-assistant').parent/'0/text.txt'
        path.write_text('tampered')
        self.assertIn('integrity invalid',self.lab._source_context(self.s))
        raw=('x'*17000).encode();path.write_bytes(raw)
        index=self.lab._snapshot_index(self.s,'call-001-assistant');saved=json.loads(index.read_text());saved['value'][0]['text_sha256']=hashlib.sha256(raw).hexdigest();saved['sha256']=p._digest(saved['value']);index.write_text(json.dumps(saved))
        context=self.lab._source_context(self.s)
        self.assertIn('due to source-text budget',context);self.assertNotIn('x'*100,context)

if __name__=='__main__':unittest.main()
