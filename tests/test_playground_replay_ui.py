"""Exercise replay controls with the real UI and an offline DOM/network harness."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PlaygroundReplayUI(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node unavailable; UI checks not run")
    def test_preview_creation_comparison_and_draft_isolation(self):
        tests = Path(__file__).parent
        harness = (tests / "test_playground_ui.js").read_text().split("\nasync function main(){", 1)[0]
        checks = r'''
const agentState=id=>({...liveState(id),output_mode:'agent'});
const preview=id=>({source_id:id,source_revision:1,source_sha256:'a'.repeat(64),model:'gpt-6-astra',turn_count:2,
 turns:[{index:1,user_text:'<script>first user</script>',original_reply:'**Old answer** <img src=x>',attachment_count:1},
 {index:2,user_text:'A saved follow-up',original_reply:'A previous follow-up answer',attachment_count:0}],excluded_pending_count:1,note:'Pending input was excluded.'});
const replayState=id=>({...agentState(id),next_actor:null,replay:{source_id:'A',source_sha256:'a'.repeat(64),total:2,completed:0,next_turn:1,modified:false,remaining:2},
 replay_comparison:preview('A').turns.map(turn=>({...turn,new_reply:null,status:'pending'}))});
const ev=()=>({preventDefault(){}});
let override=null;
handler=(url,opts)=>{
 if(override){const value=override(url,opts);if(value!==undefined)return value;}
 const replay=url.match(/^\/api\/session\/([^/]+)\/replay$/);
 if(replay)return response(opts.method==='POST'?{id:'R'}:preview(replay[1]));
 const session=url.match(/^\/api\/session\/([^/]+)$/);if(session)return response(session[1]==='R'?replayState('R'):agentState(session[1]));
 if(url==='/api/attachments')return response({id:'draft-file',name:'私人 草稿.pdf',bytes:8,sha256:'b'.repeat(64)});
};
const posts=suffix=>captured.filter(row=>row.url.endsWith(suffix));
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.equal(captured.length,0);assert.equal(network.some(url=>url.endsWith('/replay')),false);
 await run("select('A')");elements.message.value='未送出的 A 草稿';elements.message.oninput();
 elements['message-path'].value='/Users/example/私人 草稿.pdf';await elements['message-path-add'].onclick();
 elements['initial-path'].value='/Users/example/初始 草稿.pdf';await elements['initial-path-add'].onclick();
 context.historical={...agentState('A'),compatible:false,calls:30};run('render(historical)');
 assert.equal(elements.send.disabled,true);assert.equal(elements['replay-open'].disabled,false,'old runtime/budget does not prevent replay preview');
 await elements['replay-open'].onclick();assert.equal(elements['replay-setup'].hidden,false);
 assert.match(elements['replay-preview-meta'].textContent,/2 輪.*1 則未完成/);assert.match(elements['replay-preview-turns'].textContent,/<script>first user<\/script>/);
 assert.equal(posts('/replay').length,0,'preview is read-only');assert.equal(posts('/control').length,0);
 assert.equal(elements['replay-create'].disabled,false);assert.equal(elements['replay-model'].value,elements.model.value);
 elements['replay-max-calls'].value='0';elements['replay-max-calls'].oninput();await elements['replay-form'].onsubmit(ev());assert.equal(posts('/replay').length,0);
 elements['replay-max-calls'].value='5';elements['replay-max-tokens'].value='90000';elements['replay-max-calls'].oninput();
 let rejectCreate;
 override=(url,opts)=>url==='/api/session/A/replay'&&opts.method==='POST'?new Promise((resolve,reject)=>rejectCreate=reject):undefined;
 const first=elements['replay-form'].onsubmit(ev());await settle();await elements['replay-form'].onsubmit(ev());
 assert.equal(posts('/replay').length,1,'double click sends one create request');assert.equal(elements['replay-create'].disabled,true);
 rejectCreate(Error('uncertain create response'));await first;assert.equal(elements['replay-error'].hidden,false);assert.equal(elements['replay-create'].disabled,false);
 assert.equal(elements['replay-max-calls'].value,'5');assert.equal(elements['message-file-list'].children.length,1);
 override=null;await elements['replay-form'].onsubmit(ev());const clones=posts('/replay');
 assert.equal(clones[0].data.client_id,clones[1].data.client_id);assert.equal(clones[1].data.source_sha256,'a'.repeat(64));assert.equal(clones[1].data.max_calls,5);
 assert.equal(clones[1].data.max_tokens,90000);assert.equal('attachments' in clones[1].data,false);
 assert.equal(posts('/control').length,0,'creating replay never starts it');assert.equal(elements.message.value,'');assert.equal(elements['message-file-list'].children.length,0);
 assert.equal(elements['initial-file-list'].children.length,1,'initial upload draft survives replay creation');
 assert.equal(elements['replay-comparison'].hidden,false);assert.equal(elements['replay-setup'].hidden,true);
 assert.equal(elements.run.hidden,false);assert.equal(elements.run.disabled,false);assert.equal(elements.step.disabled,false);
 assert.equal(elements.run.textContent,'連續重測');assert.equal(elements.step.textContent,'重測下一輪');assert.match(elements['replay-progress'].textContent,/剩下 2 輪/);
 await elements['replay-origin'].onclick();assert.equal(elements.message.value,'未送出的 A 草稿');assert.equal(elements['message-file-list'].children.length,1);
 assert.equal(elements['replay-comparison'].hidden,true);assert.equal(elements.run.hidden,true);
 // Late preview responses cannot reopen an old source or carry drafts into B.
 let resolvePreview;
 override=(url,opts)=>url==='/api/session/A/replay'?new Promise(resolve=>resolvePreview=resolve):undefined;
 const late=elements['replay-open'].onclick();await settle();await run("select('B')");resolvePreview(response(preview('A')));await late;
 assert.equal(elements['replay-setup'].hidden,true);assert.equal(elements.message.value,'');assert.equal(elements['message-file-list'].children.length,0);
 override=null;await run("select('A')");await elements['replay-open'].onclick();
 context.changed={...agentState('A'),revision:2};run('render(changed)');assert.equal(elements['replay-create'].disabled,true);assert.match(elements['replay-error'].textContent,/已更新/);
 const beforeStale=posts('/replay').length;await elements['replay-form'].onsubmit(ev());assert.equal(posts('/replay').length,beforeStale);
 context.busy={...agentState('A'),busy:true,status:'running'};run('render(busy)');const beforeBusy=network.length;await elements['replay-open'].onclick();assert.equal(network.length,beforeBusy);
 assert.equal(elements['replay-open'].disabled,true);
 // A failed GET is visible and cannot enable creation; a fresh preview recovers.
 context.idle=agentState('A');run('render(idle)');override=(url,opts)=>url.endsWith('/replay')?Promise.reject(Error('No completed turns')):undefined;
 await elements['replay-reload'].onclick();assert.match(elements['replay-error'].textContent,/No completed turns/);assert.equal(elements['replay-create'].disabled,true);
 override=null;await elements['replay-reload'].onclick();assert.equal(elements['replay-create'].disabled,false);
 // Changing bounds after an uncertain create creates a distinct intent.
 override=(url,opts)=>url.endsWith('/replay')&&opts.method==='POST'?Promise.reject(Error('uncertain')):undefined;
 await elements['replay-form'].onsubmit(ev());const oldId=posts('/replay').at(-1).data.client_id;
 elements['replay-max-calls'].value='6';await elements['replay-form'].onsubmit(ev());assert.notEqual(posts('/replay').at(-1).data.client_id,oldId);
 // A late successful create cannot navigate away from the user's new selection.
 let resolveCreate;override=(url,opts)=>url.endsWith('/replay')&&opts.method==='POST'?new Promise(resolve=>resolveCreate=resolve):undefined;
 const creating=elements['replay-form'].onsubmit(ev());await settle();await run("select('B')");elements.message.value='B stays selected';
 resolveCreate(response({id:'R'}));await creating;assert.equal(run('selected'),'B');assert.equal(elements.message.value,'B stays selected');
 override=null;await run("select('R')");await elements.step.onclick();assert.equal(posts('/control').at(-1).data.action,'step');
 await elements.run.onclick();assert.equal(posts('/control').at(-1).data.action,'run');
 // The comparison is read-only text/Markdown, preserves expansion, and labels modifications.
 context.progress={...replayState('R'),revision:3,replay:{...replayState('R').replay,completed:1,remaining:1,next_turn:2,modified:true},
 replay_comparison:[{index:1,user_text:'Old input',original_reply:'<script>OLD</script>',new_reply:'<img src=x> New answer',status:'complete'}]};
 run('render(progress)');assert.match(elements['replay-context-note'].textContent,/已加入新訊息/);assert.match(elements['replay-comparison-body'].textContent,/<script>OLD<\/script>/);
 const row=elements['replay-comparison-body'].children[0];row.open=true;row.ontoggle();run('render(progress)');assert.equal(elements['replay-comparison-body'].children[0].open,true);
 assert.equal(elements['replay-comparison-body'].children[0].children[2].children.length,2);
 for(const status of ['error','interrupted','budget']){context.stopped={...context.progress,status};run('render(stopped)');assert.equal(elements.run.disabled,true);assert.equal(elements.step.disabled,true);}
 context.cap={...context.progress,calls:30};run('render(cap)');const beforeCap=posts('/control').length;await elements.run.onclick();await elements.step.onclick();assert.equal(posts('/control').length,beforeCap);
 context.done={...context.progress,status:'paused',replay:{...context.progress.replay,completed:2,remaining:0,next_turn:null}};run('render(done)');assert.equal(elements.run.disabled,true);assert.equal(elements.step.disabled,true);assert.match(elements.status.textContent,/已完成/);
 context.fixture=state('R');run('render(fixture)');assert.equal(elements['replay-open'].hidden,true);assert.equal(elements['replay-comparison'].hidden,true);
 console.log('replay UI checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([shutil.which("node"), "-e", harness + checks], cwd=tests,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("replay UI checks passed", result.stdout)
