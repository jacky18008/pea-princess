"""Public artifact prompt routing and persisted provenance; no provider calls."""
import copy
import json
from agent_reply_fixture import attach_claims
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import persona_playground as p


class PublicSkillIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.skill = self.root/'skills/pea-princess'
        (self.skill/'references').mkdir(parents=True)
        (self.skill/'SKILL.md').write_text('name: pea-princess\nPUBLIC ZIP DISTINCT INSTRUCTIONS')
        for name in p.live_references('compare two homes')+['inputs.md','rules.md']:
            (self.skill/'references'/name).write_text('PUBLIC ZIP REFERENCE '+name+
                ('\n## 2b. Tell me about the places you have lived\nUNREQUESTED STORY' if name=='onboarding.md' else ''))
        self.artifact = {'name':'pea-princess','kind':'public_zip','sha256':'a'*64,
                         'file_count':5,'path':str(self.skill)}
        for patch in (
            mock.patch.object(p.playground_skill, 'artifact_info', return_value=self.artifact),
            mock.patch.object(p.playground_skill, 'skill_root', return_value=self.skill),
            mock.patch.object(p, 'source_hashes', return_value={'release':'a'*64}),
        ):
            patch.start(); self.addCleanup(patch.stop)
        self.calls = []
        def invoke(request, folder):
            self.calls.append(copy.deepcopy(request))
            return {'id':'answer','status':'complete','exit_code':0,'errors':[],
                    'tool_events':[],'malformed_event_lines':0,'terminal_usage_events':1,
                    'direct_terminal_usage':{'input_tokens':15,'output_tokens':5,'cached_input_tokens':0},
                    'answer':json.dumps(attach_claims({'message':'先比較兩間的空間與價格。','questions':[]},request))}
        self.lab = p.Lab(self.root/'state', invoke=invoke)
        self.addCleanup(self.lab.close)

    def create(self):
        return self.lab.create(dict(research_mode='live',output_mode='agent',
            initial_request='compare two homes',model='gpt-6-astra',
            max_calls=2,max_tokens=10000,seed=1,client_id=str(uuid.uuid4())))['id']

    def test_actual_actor_prompt_reads_public_package_and_persists_identity(self):
        sid = self.create()
        self.assertEqual([], self.calls)
        self.lab.control(sid, {'action':'step','client_id':str(uuid.uuid4())})
        self.lab.worker.join(10)
        self.assertFalse(self.lab.worker.is_alive())
        self.assertEqual(1,len(self.calls))
        prompt = self.calls[0]['prompt']
        self.assertIn('PUBLIC ZIP DISTINCT INSTRUCTIONS',prompt)
        self.assertIn(str(self.skill),prompt)
        self.assertNotIn(str(ROOT/'skills/vet-flat'),prompt)
        self.assertIn('PUBLIC ZIP REFERENCE rules.md',prompt)
        self.assertIn('PUBLIC ZIP REFERENCE conversation-quality.md',prompt)
        self.assertNotIn('REFERENCE onboarding.md',prompt)
        self.assertNotIn('LOCAL CONVERSATION POLICY',prompt)
        for data in (self.lab.catalog(),self.lab.snapshot(sid),self.lab.export(sid),self.lab.inspect(sid)['session']):
            self.assertEqual(self.artifact,data['skill_artifact'])

    def test_fixture_uses_same_zip_and_never_legacy_prompt_pack(self):
        card = next(iter(self.lab.cards.values()))
        card = dict(card,references_needed=['references/listing-evidence.md'])
        with mock.patch.object(p.personas,'system_prompt',side_effect=AssertionError('legacy pack')):
            prompt = p.configured_system(card)
        self.assertIn('PUBLIC ZIP DISTINCT INSTRUCTIONS',prompt)
        self.assertIn('PUBLIC ZIP REFERENCE listing-evidence.md',prompt)
        self.assertIn('no live search',prompt)
        self.assertNotIn(str(ROOT/'skills/vet-flat'),prompt)

    def test_old_session_is_not_relabelled_and_reads_do_not_dispatch(self):
        sid = self.create()
        session = self.lab._load(sid)
        session.pop('skill_artifact')
        self.lab._save(session)
        path = self.lab._folder(sid)/'session.json'
        before = path.read_bytes()
        for data in (self.lab.snapshot(sid),self.lab.export(sid),self.lab.inspect(sid)['session']):
            self.assertIsNone(data['skill_artifact'])
        self.assertEqual(before,path.read_bytes())
        self.assertEqual([],self.calls)


if __name__ == '__main__':
    unittest.main()
