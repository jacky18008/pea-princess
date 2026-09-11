"""Keep the current public archive and each saved session's provenance distinct."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PlaygroundSkillUI(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node unavailable; UI checks not run")
    def test_public_archive_and_historical_provenance(self):
        tests = Path(__file__).parent
        harness = (tests / "test_playground_ui.js").read_text().split("\nasync function main(){", 1)[0]
        checks = r'''
const publicArtifact={name:'pea-princess',kind:'public_zip',sha256:'a'.repeat(64),file_count:99};
const olderArtifact={...publicArtifact,sha256:'b'.repeat(64),file_count:90};
const saved=id=>({...liveState(id),output_mode:'agent',...(id==='A'?{skill_artifact:olderArtifact,compatible:false}:id==='R'?{skill_artifact:publicArtifact}:{})});
let override=null;
handler=(url,opts)=>{
 if(override){const value=override(url,opts);if(value!==undefined)return value;}
 if(url==='/api/catalog')return response({research_modes:['live','fixture'],models:['gpt-6-astra'],skill_artifact:publicArtifact,
 personas:[{id:'P4',name:'Brett',identity:'Viewing tomorrow',language:'en',patience_turns:3}]});
 const match=url.match(/^\/api\/session\/([^/]+)$/);if(match)return response(saved(match[1]));
};
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.match(elements['catalog-skill-label'].textContent,/新對話.*pea-princess 公開 ZIP.*aaaaaaaaaaaa/);
 assert.match(elements['catalog-skill-label'].title,new RegExp('a'.repeat(64)));
 assert.match(elements['catalog-skill-detail'].textContent,/99 個檔案/);assert.match(elements['catalog-skill-detail'].textContent,new RegExp('a'.repeat(64)));
 assert.equal(captured.length,0,'reading provenance cannot dispatch');
 await run("select('A')");assert.match(elements['session-skill-label'].textContent,/此對話.*bbbbbbbbbbbb/);
 assert.equal(elements['session-skill-label'].textContent.includes('aaaaaaaaaaaa'),false,'historical session never inherits catalog hash');
 assert.equal(elements['session-skill-label'].title.includes('a'.repeat(64)),false);
 assert.match(elements['session-skill-detail'].textContent,/90 個檔案/);assert.equal(elements['replay-open'].disabled,false);
 assert.match(elements['catalog-skill-label'].textContent,/aaaaaaaaaaaa/);
 await run("select('B')");assert.match(elements['session-skill-label'].textContent,/舊版或來源未確認/);
 assert.equal(elements['session-skill-label'].title,'');assert.equal(elements['session-skill-detail'].textContent.includes('a'.repeat(64)),false);
 context.bad={...saved('B'),skill_artifact:{...publicArtifact,sha256:'<script>invalid</script>'}};run('render(bad)');
 assert.match(elements['session-skill-label'].textContent,/來源未確認/);assert.equal(elements['session-skill-detail'].textContent.includes('<script>'),false);
 context.bad={...saved('B'),skill_artifact:{...publicArtifact,file_count:null}};run('render(bad)');assert.match(elements['session-skill-label'].textContent,/來源未確認/);
 context.development={...saved('B'),skill_artifact:{name:'pea-princess',kind:'development',sha256:'c'.repeat(64)}};run('render(development)');
 assert.match(elements['session-skill-label'].textContent,/開發版本，未核對公開 ZIP/);assert.equal(elements['session-skill-label'].title,'');
 await run("select('R')");assert.match(elements['session-skill-label'].textContent,/aaaaaaaaaaaa/);
 // Updating creation controls/provenance cannot relabel a loaded session.
 run("catalog.skill_artifact={name:'pea-princess',kind:'development'};creationMode()");
 assert.match(elements['catalog-skill-label'].textContent,/開發版本/);assert.match(elements['session-skill-label'].textContent,/aaaaaaaaaaaa/);
 run('catalog.skill_artifact=null;creationMode()');assert.match(elements['catalog-skill-label'].textContent,/來源未確認/);assert.equal(elements['catalog-skill-label'].title,'');
 // A late response from the previous selection cannot show its pinned hash.
 let resolveOld;override=url=>url==='/api/session/R'?new Promise(resolve=>resolveOld=resolve):undefined;
 const previous=run('refresh()');await settle();await run("select('B')");assert.equal(elements['session-skill'].hidden,true);assert.equal(elements['session-skill-label'].textContent,'');
 resolveOld(response(saved('R')));await previous;assert.equal(elements['session-skill'].hidden,true);
 override=null;await run('refresh()');assert.match(elements['session-skill-label'].textContent,/來源未確認/);assert.equal(elements['session-skill-label'].title,'');
 assert.equal(captured.length,0);console.log('skill provenance UI checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([shutil.which("node"), "-e", harness + checks], cwd=tests,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("skill provenance UI checks passed", result.stdout)
