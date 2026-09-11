"""Execution setting choices and recorded provenance through real UI handlers."""
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node unavailable; UI checks not run")
class PlaygroundSettingsUI(unittest.TestCase):
    def run_js(self, harness_name, delimiter, checks):
        tests = Path(__file__).parent
        harness = (tests / harness_name).read_text().split(delimiter, 1)[0]
        result = subprocess.run([shutil.which("node"), "-e", harness + checks], cwd=tests,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_creation_replay_exports_and_unknown_historical_settings(self):
        self.run_js("test_playground_ui.js", "\nasync function main(){", r'''
const options={research_depths:['lite','standard','deep'],reasoning_efforts:['low','medium','high'],defaults:{research_depth:'standard',reasoning_effort:'low'}};
const record=(depth,effort)=>({research_depth:depth,reasoning_effort:effort,research_depth_source:'user_selected',reasoning_effort_source:'user_selected'});
let savedSettings=record('standard','low'),override=null,exported;
context.URL.createObjectURL=blob=>{exported=blob;return 'blob:settings-export';};
handler=(url,opts)=>{
 if(override){const value=override(url,opts);if(value!==undefined)return value;}
 if(url==='/api/catalog')return response({research_modes:['live','fixture'],models:['gpt-6-astra'],execution_options:options,
 personas:[{id:'P4',name:'Standard persona',identity:'Synthetic',runtime_settings:{budget_mode:'deep'}},{id:'P5',name:'Lite persona',identity:'Synthetic',runtime_settings:{budget_mode:'lite'}}]});
 if(url==='/api/sessions'&&opts.method==='POST'){const data=JSON.parse(opts.body);savedSettings=record(data.research_depth,data.reasoning_effort);return response({id:'L'});}
 if(url.endsWith('/replay'))return response(opts.method==='POST'?{id:'R'}:{source_id:'L',source_revision:1,source_sha256:'a'.repeat(64),model:'gpt-6-astra',turn_count:1,turns:[{index:1,user_text:'Saved input',original_reply:'Saved reply',attachment_count:0}],excluded_pending_count:0});
 if(url==='/api/session/L/export')return response({...liveState('L'),execution_settings:savedSettings});
 const match=url.match(/^\/api\/session\/([^/]+)$/);if(match)return response({...liveState(match[1]),output_mode:'agent',execution_settings:savedSettings});
};
const ev=()=>({preventDefault(){}}),posts=suffix=>captured.filter(row=>row.url.endsWith(suffix));
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.equal(elements['research-depth'].value,'standard');assert.equal(elements['reasoning-effort'].value,'low');assert.equal(captured.length,0);
 assert.equal(elements['research-depth'].children.length,3);assert.equal(elements['reasoning-effort'].disabled,false);
 elements['initial-request'].value='Compare the supplied choices.';elements['initial-request'].oninput();
 elements['research-depth'].value='deep';elements['research-depth'].onchange();elements['reasoning-effort'].value='high';elements['reasoning-effort'].onchange();
 override=(url,opts)=>url==='/api/sessions'&&opts.method==='POST'?Promise.reject(Error('uncertain create')):undefined;
 await elements.create.onclick();await elements.create.onclick();const initial=posts('/api/sessions');
 assert.equal(initial[0].data.research_depth,'deep');assert.equal(initial[0].data.reasoning_effort,'high');assert.equal(initial[0].data.client_id,initial[1].data.client_id);
 elements['reasoning-effort'].value='medium';elements['reasoning-effort'].onchange();await elements.create.onclick();assert.notEqual(posts('/api/sessions').at(-1).data.client_id,initial[0].data.client_id);
 override=null;await elements.create.onclick();assert.match(elements['session-execution'].textContent,/深入（deep）.*中（medium）/);assert.match(elements['session-execution'].title,/使用者選擇/);
 await elements.export.onclick();assert.deepEqual(JSON.parse(await exported.text()).execution_settings,record('deep','medium'));
 // Saved settings remain independent of the current form, including old unknowns.
 elements['research-depth'].value='lite';elements['research-depth'].onchange();assert.match(elements['session-execution'].textContent,/深入（deep）/);
 context.unknown={...liveState('L'),effort:'low',configured_effort:'low',execution_settings:{research_depth:null,reasoning_effort:null,research_depth_source:'unrecorded',reasoning_effort_source:'unrecorded'}};run('render(unknown)');
 assert.equal(elements['session-execution'].textContent,'研究深度基準：未記錄 · 模型思考強度：未記錄');
 // Replay is initialized from the current catalog, not this unknown historical source or the modified form.
 await elements['replay-open'].onclick();assert.equal(elements['replay-research-depth'].value,'standard');assert.equal(elements['replay-reasoning-effort'].value,'low');
 elements['replay-research-depth'].value='lite';elements['replay-reasoning-effort'].value='high';elements['replay-reasoning-effort'].onchange();
 override=(url,opts)=>url.endsWith('/replay')&&opts.method==='POST'?Promise.reject(Error('uncertain replay')):undefined;
 await elements['replay-form'].onsubmit(ev());await elements['replay-form'].onsubmit(ev());const replay=posts('/replay');
 assert.equal(replay[0].data.research_depth,'lite');assert.equal(replay[0].data.reasoning_effort,'high');assert.equal(replay[0].data.client_id,replay[1].data.client_id);
 elements['replay-research-depth'].value='deep';await elements['replay-form'].onsubmit(ev());assert.notEqual(posts('/replay').at(-1).data.client_id,replay[0].data.client_id);
 // Unsupported DOM values cannot enter create/replay payloads.
 elements['replay-reasoning-effort'].value='unsupported';elements['replay-reasoning-effort'].onchange();const count=posts('/replay').length;await elements['replay-form'].onsubmit(ev());assert.equal(posts('/replay').length,count);
 override=null;elements['replay-close'].onclick();elements['research-mode'].value='fixture';elements['research-mode'].onchange();assert.equal(elements['research-depth'].value,'deep');
 elements['research-depth'].value='standard';elements['research-depth'].onchange();await elements.create.onclick();assert.equal(posts('/api/sessions').at(-1).data.research_depth,'standard');
 elements.persona.value='P5';elements.persona.onchange();assert.equal(elements['research-depth'].value,'lite');await elements.create.onclick();assert.equal(posts('/api/sessions').at(-1).data.research_depth,'lite');
 elements['research-mode'].value='live';elements['research-mode'].onchange();assert.equal(elements['research-depth'].value,'standard');
 elements['research-depth'].value='unsupported';elements['research-depth'].onchange();const creates=posts('/api/sessions').length;await elements.create.onclick();assert.equal(posts('/api/sessions').length,creates);
 assert.equal(posts('/control').length,0);console.log('execution settings UI checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
''')

    def test_inspector_shows_only_recorded_session_and_bound_call_settings(self):
        self.run_js("test_playground_inspector.js", "\n(async()=>{", r'''
const settings=(depth,effort,source)=>({research_depth:depth,reasoning_effort:effort,research_depth_source:source,reasoning_effort_source:source});
const callSettings=()=>elements['review-detail'].querySelectorAll('*').find(item=>item.className==='review-execution-settings');
(async()=>{
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/review.js'),'utf8'),context);
 await elements['show-review'].onclick();await settle();
 assert.match(elements['review-session-settings'].textContent,/研究深度基準：未記錄.*模型思考強度：未記錄/);
 assert.equal(elements['review-meta'].textContent.includes('low'),false,'old broad effort field does not establish recorded settings');
 assert.match(callSettings().textContent,/研究深度基準：未記錄.*模型思考強度：未記錄/);
 idx.session.execution_settings=settings('deep','high','user_selected');
 detail.execution_settings=settings('lite','medium','legacy_record');detail.execution_settings_evidence={status:'bound',source_path:'manifest.json#request.execution_settings',request_sha256:'d'.repeat(64)};
 await elements['review-refresh'].onclick();await settle();
 assert.match(elements['review-session-settings'].textContent,/深入（deep）.*使用者選擇.*高（high）/);
 assert.match(callSettings().textContent,/精簡（lite）.*舊版紀錄.*中（medium）/);assert.match(callSettings().textContent,/已綁定保存請求/);
 assert.equal(callSettings().textContent.includes('深入（deep）'),false,'session settings never replace call settings');
 detail.execution_settings={research_depth:null,reasoning_effort:'low',research_depth_source:'not_applicable',reasoning_effort_source:'user_selected'};
 await elements['review-refresh'].onclick();await settle();assert.match(callSettings().textContent,/研究深度基準：不適用（模擬使用者）.*模型思考強度：低（low）/);
 for(const status of ['not_recorded','unbound','invalid']){detail.execution_settings_evidence.status=status;await elements['review-refresh'].onclick();await settle();assert.match(callSettings().textContent,/研究深度基準：未記錄.*模型思考強度：未記錄/);assert.equal(callSettings().textContent.includes('medium'),false);}
 delete idx.session.execution_settings;delete detail.execution_settings;delete detail.execution_settings_evidence;
 await elements['review-refresh'].onclick();await settle();assert.match(elements['review-session-settings'].textContent,/研究深度基準：未記錄/);assert.match(callSettings().textContent,/無法確認/);
 assert.equal(requests.filter(r=>r.data).length,0);assert.equal(requests.filter(r=>/\/(message|control)$/.test(r.route)).length,0);
 console.log('Inspector execution settings checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
''')
