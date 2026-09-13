'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.textContent='';this.value='';this.style={};this.disabled=false;this.hidden=false;this.checked=false;this.scrollHeight=0;this.scrollTop=0;this.clientHeight=0;}
 append(...children){this.children.push(...children);}
 set textContent(value){this._text=String(value);this.children=[];}
 get textContent(){return this._text+this.children.map(child=>child.textContent).join('');}
 setAttribute(name,value){this[name]=value;}
 replaceChildren(...children){this._text='';this.children=children;if(this.tag==='select'&&!this.value&&children.length)this.value=children[0].value;}
 get firstChild(){return this.children[0];}
 set innerHTML(_){throw Error('Untrusted HTML must never be rendered');}
 click(){if(this.onclick)return this.onclick();}
}
const ids=[...fs.readFileSync(path.join(__dirname,'../playground/index.html'),'utf8').matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
const elements=Object.fromEntries(ids.map(id=>[id,new Element(['persona','model','research-mode'].includes(id)?'select':'div')]));
elements['max-calls'].value='30';elements['max-tokens'].value='400000';
const messages=[],captured=[],network=[];let handler=null,count=0;
function state(id){return {id,revision:1,persona_id:'P4',name:'Person '+id,model:'gpt-6-astra',status:'paused',auto:false,busy:false,notice:'',phase_label:'',persona_turn:1,patience_turns:3,calls:1,tokens:20,limits:{max_calls:30,max_tokens:400000},actor_calls:{assistant:1,persona:0},messages:[{role:'assistant',text:'<script>PRIVATE</script>'}],pending_count:0,mood:'wary',held_documents:[],events:[],criteria:['Get an actionable response'],pending_call:false};}
function liveState(id){return {...state(id),research_mode:'live',persona_id:null,name:'真實找房研究',status:'ready',next_actor:'assistant',patience_turns:null,calls:0,tokens:0,actor_calls:{assistant:0,persona:0},criteria:[],events:[],messages:[{role:'human',text:'Find an actual listing.',kind:'question'}],capability_status:'可嘗試唯讀公開網頁研究；廣告刊登不等於已確認可租。'};}
function response(value){return {ok:true,json:async()=>value};}
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
 crypto:{randomUUID:()=>`00000000-0000-4000-8000-${String(++count).padStart(12,'0')}`},
 localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,setInterval:()=>0,Blob,
 URL:class extends URL{static createObjectURL(){return 'blob:private-export';}static revokeObjectURL(){}},
 fetch:async(url,opts)=>{
  network.push(url);
  if(opts.body)captured.push({url,data:JSON.parse(opts.body)});
  if(handler){const value=handler(url,opts);if(value!==undefined)return value;}
  if(url==='/api/catalog')return response({research_modes:['live','fixture'],models:['gpt-6-astra'],personas:[{id:'P4',name:'Brett',identity:'Viewing tomorrow',language:'en',patience_turns:3,original_harness:'chat'}]});
  if(url==='/api/sessions')return response({sessions:[]});
  const match=url.match(/^\/api\/session\/([^/]+)$/);if(match)return response(state(match[1]));
  return response({ok:true});
 },console});
const run=code=>vm.runInContext(code,context);
const settle=async()=>{for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));};
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.equal(elements.connection.textContent,'本機研究介面已連接');assert.equal(elements.persona.value,'P4');
 // New work defaults to genuine human input; loading the UI or creating a
 // session never requests a model action. These responses are offline stubs.
 assert.equal(elements['research-mode'].value,'live');assert.equal(elements['fixture-setup'].hidden,true);assert.equal(elements['live-setup'].hidden,false);
 assert.equal(elements.create.disabled,true);assert.equal(captured.length,0);
 elements['initial-request'].value='  \n ';elements['initial-request'].oninput();await elements.create.onclick();assert.equal(captured.length,0);
 elements['initial-request'].value='x'.repeat(8001);elements['initial-request'].oninput();assert.equal(elements.create.disabled,true);await elements.create.onclick();assert.equal(captured.length,0);
 elements['initial-request'].value='x'.repeat(8000);elements['initial-request'].oninput();assert.equal(elements.create.disabled,false);
 const initial='  Find a quiet flat.\nPlease compare real source links.  ';
 elements['initial-request'].value=initial;elements['initial-request'].oninput();
 let failCreate=true,live=liveState('L');live.messages[0].text=initial;
 handler=(url,opts)=>{if(url==='/api/sessions'&&opts.method==='POST'){if(failCreate){failCreate=false;throw Error('uncertain create response');}return response({id:'L'});}if(url==='/api/session/L')return response(live);};
 await elements.create.onclick();assert.equal(elements['initial-request'].value,initial);assert.equal(elements.create.disabled,false);
 await elements.create.onclick();const creates=captured.filter(x=>x.url==='/api/sessions');
 assert.equal(creates.length,2);assert.equal(creates[0].data.client_id,creates[1].data.client_id);
 assert.equal(creates[1].data.research_mode,'live');assert.equal(creates[1].data.initial_request,initial);assert.equal('persona_id' in creates[1].data,false);
 assert.equal(creates[1].data.max_calls,30);assert.equal(creates[1].data.max_tokens,400000);
 assert.equal(captured.filter(x=>x.url.endsWith('/control')).length,0);
 assert.equal(elements.messages.children.length,1);assert.equal(elements.messages.children[0].firstChild.textContent,'你');assert.equal(elements.messages.children[0].children[1].textContent,initial);
 assert.equal(elements.step.textContent,'研究並回覆');assert.equal(elements.step.disabled,false);assert.equal(elements.run.hidden,true);assert.equal(elements.run.disabled,true);
 assert.equal(elements['turn-label'].textContent,'真人輸入');assert.equal(elements.turn.textContent,'1');assert.equal(elements['fixture-observations'].hidden,true);
 assert.equal(elements['amendment-label'].hidden,true);assert.ok(!elements.behavior.textContent.includes('耐心'));assert.ok(!elements['usage-note'].textContent.includes('persona'));
 assert.match(elements['capability-status'].textContent,/廣告刊登不等於已確認可租/);assert.match(elements['mode-limit-note'].textContent,/來源連結與查詢時間/);
 const beforeLiveRefresh=captured.length;await run('refresh()');await run("action('run')");assert.equal(captured.length,beforeLiveRefresh);
 handler=(url,opts)=>{if(url==='/api/session/L/control'){live={...live,revision:2,status:'paused',next_actor:null,calls:1,actor_calls:{assistant:1,persona:0},messages:[...live.messages,{role:'assistant',text:'Check the [source](https://example.test/listing). Retrieved 2026-09-10; availability unconfirmed.'}]};return response({ok:true});}if(url==='/api/session/L')return response(live);};
 await elements.step.onclick();assert.equal(captured.at(-1).data.action,'step');assert.equal(elements.step.disabled,true);assert.equal(elements.status.textContent,'等待你的回覆');
 assert.equal(elements.messages.children.length,2);assert.match(elements.messages.textContent,/Retrieved 2026-09-10; availability unconfirmed/);
 const afterLiveAnswer=captured.length;await elements.step.onclick();await run("action('run')");await run('refresh()');assert.equal(captured.length,afterLiveAnswer,'idle live session cannot generate another turn');
 // Live follow-ups preserve text and run through the human inbox. A hidden
 // fixture checkbox cannot silently change the kind of the new input.
 const followup='  Now compare the journey.\nMy budget changed.  ';elements.message.value=followup;elements.amendment.checked=true;
 handler=(url,opts)=>{if(url==='/api/session/L/message'){live={...live,revision:3,status:'running',busy:true,persona_turn:2,pending_count:1,messages:[...live.messages,{role:'human',text:followup,pending:true}]};return response({ok:true});}if(url==='/api/session/L')return response(live);};
 await elements.composer.onsubmit({preventDefault(){}});assert.equal(captured.at(-1).data.text,followup);assert.equal(captured.at(-1).data.kind,'question');
 assert.equal(elements.message.value,'');assert.equal(elements.send.disabled,false);assert.equal(elements.step.disabled,true);assert.equal(elements.turn.textContent,'2');assert.match(elements['queue-note'].textContent,/1 則問題已保存/);
 context.queuedLive={...live,busy:false,status:'paused',next_actor:null};run('render(queuedLive)');assert.equal(elements.step.disabled,false,'a queued live input enables one step');assert.equal(elements.run.disabled,true);
 context.cappedLive={...context.queuedLive,calls:30};run('render(cappedLive)');assert.equal(elements.step.disabled,true);assert.equal(elements.send.disabled,true);assert.equal(elements.export.disabled,false);
 // Deliberately choosing the old lane keeps the synthetic identity and payload.
 elements['research-mode'].value='fixture';elements['research-mode'].onchange();assert.equal(elements['fixture-setup'].hidden,false);assert.equal(elements['live-setup'].hidden,true);
 handler=(url,opts)=>url==='/api/sessions'&&opts.method==='POST'?response({id:'F'}):undefined;
 await elements.create.onclick();const fixtureCreate=captured.filter(x=>x.url==='/api/sessions').at(-1).data;
 assert.equal(fixtureCreate.research_mode,'fixture');assert.equal(fixtureCreate.persona_id,'P4');assert.equal('initial_request' in fixtureCreate,false);
 assert.equal(elements.run.hidden,false);assert.equal(elements.run.disabled,false);assert.equal(elements.step.textContent,'下一步');assert.equal(elements['fixture-observations'].hidden,false);assert.equal(elements['amendment-label'].hidden,false);
 assert.match(elements['session-label'].textContent,/合成人物測試 · 虛構資料/);assert.match(elements['capability-status'].textContent,/虛構材料/);
 handler=null;captured.length=0;
 await run("select('A')");assert.equal(elements.title.textContent,'Person A');assert.equal(elements.messages.children[0].children[1].textContent,'<script>PRIVATE</script>');
 // Exercise the actual DOM renderer, including untrusted syntax. No HTML parser,
 // resource elements or network calls are permitted during presentation.
 const descendants=root=>[root,...root.children.flatMap(descendants)],tags=(root,name)=>descendants(root).filter(el=>el.tag===name);
 const reply=text=>{context.replyText=text;return run('renderReply(replyText)');};
 const networkBefore=network.length;
 let formatted=reply('先比較 **安靜** 和 *通勤*，再看 `rent_total`。\n\n1. **河邊**：£2,100\n2. 車站：£2,200\n\n- 可洗衣\n- 有採光');
 assert.equal(tags(formatted,'p').length,1);assert.equal(tags(formatted,'strong').length,2);assert.equal(tags(formatted,'em').length,1);
 assert.equal(tags(formatted,'code')[0].textContent,'rent_total');assert.equal(tags(formatted,'ol').length,1);assert.equal(tags(formatted,'ul').length,1);
 assert.equal(tags(formatted,'li').length,4);assert.ok(!formatted.textContent.includes('**'));assert.ok(formatted.textContent.includes('£2,100'));
 formatted=reply('### 下一步\n\n5. 保留原編號\n9. 不改成第六\n\n```html\n<img src="x" onerror="bad()">\n**literal code**\n```');
 assert.equal(tags(formatted,'h5')[0].textContent,'下一步');assert.equal(tags(formatted,'ol')[0].start,5);assert.equal(tags(formatted,'li')[1].value,9);
 assert.equal(tags(formatted,'pre')[0].textContent,'<img src="x" onerror="bad()">\n**literal code**');assert.equal(tags(formatted,'img').length,0);
 formatted=reply('| 選項 | 費用 |\n| :--- | ---: |\n| **A** | £2,100 |\n| B \\| C | `a|b` |');
 assert.equal(tags(formatted,'table').length,1);assert.equal(tags(formatted,'th').length,2);assert.equal(tags(formatted,'td').length,4);
 assert.equal(tags(formatted,'td')[2].textContent,'B | C');assert.equal(tags(formatted,'td')[3].textContent,'a|b');
 const hostile='<script>alert(1)</script> <img src=https://tracker.test/pixel onerror=bad()> <iframe src=x></iframe>\n\n![tracking](https://tracker.test/pixel)';
 formatted=reply(hostile);for(const tag of ['script','img','iframe','svg','object','style','link'])assert.equal(tags(formatted,tag).length,0);
 assert.ok(formatted.textContent.includes('<script>alert(1)</script>'));assert.ok(formatted.textContent.includes('![tracking](https://tracker.test/pixel)'));
 const badLinks=['javascript:alert(1)','data:text/html,hello','file:///private/info','//tracker.test/path','https:\\tracker.test/path','https://example.test/a\nb'];
 for(const url of badLinks){const source=`[keep label](${url})`;formatted=reply(source);assert.equal(tags(formatted,'a').length,0);assert.equal(formatted.textContent,source);}
 formatted=reply('[**Official** source](https://example.test/path_(a)?x=1&y=2) and [HTTP](http://example.test/)');
 const anchors=tags(formatted,'a');assert.equal(anchors.length,2);assert.equal(anchors[0].href,'https://example.test/path_(a)?x=1&y=2');assert.equal(anchors[0].textContent,'Official source');
 for(const a of anchors){assert.equal(a.target,'_blank');assert.equal(a.rel,'noopener noreferrer');assert.equal(a.referrerPolicy,'no-referrer');}
 const unsupported='> quoted text\n[reference][missing]\n~~not implemented~~\n\\*\\*literal stars\\*\\*\nflat_name';
 formatted=reply(unsupported);assert.equal(tags(formatted,'strong').length,0);assert.equal(tags(formatted,'em').length,0);assert.ok(formatted.textContent.includes('[reference][missing]'));assert.ok(formatted.textContent.includes('**literal stars**'));
 for(const text of ['```unclosed\nKeep every byte **here**','[x]('.repeat(20000),'x'.repeat(100001)])assert.equal(reply(text).textContent,text);
 assert.equal(network.length,networkBefore,'formatting must not fetch any resource');
 context.markdownState={...state('A'),messages:[{role:'assistant',text:'ORIGINAL **kept**',display_text:'Visible **reply**'},{role:'human',text:'[do not execute](javascript:bad())'}]};
 const sourceBefore=JSON.stringify(context.markdownState);run('render(markdownState)');assert.equal(JSON.stringify(context.markdownState),sourceBefore,'source messages and display_text remain untouched');
 assert.equal(tags(elements.messages.children[0],'strong')[0].textContent,'reply');assert.equal(elements.messages.children[1].children[1].textContent,'[do not execute](javascript:bad())');
 // The current comparison uses the host artifact's request, unresolved-intent
 // and presentation fields. Preserve long original text without HTML parsing.
 const longRequest='請完整保留：<script>evil()</script> <img src=https://tracker.test/request onerror=evil()> [不可執行](javascript:evil()) **原話**\n'+'要求未更動。'.repeat(1100);
 const unresolved='<svg onload=evil()> Ground floor only if entirely dry. </svg>';
 const todo='房源 A：查證每月總花費不超過 £2,200、指定入住日期的可租性';
 const artifact={schema_version:'vet-flat/live-eligibility/1',
  constraints:{user_requests:{'input-1':longRequest,'input-2':unresolved}},
  normalization:{unresolved_intent:[unresolved]},
  presentation:{conditions:['每月總花費不超過 £2,200'],todos:[todo]}};
 context.checkedLive={...liveState('A'),revision:2,status:'paused',next_actor:null,
  comparison_status:'current',current_comparison:artifact,
  messages:[{role:'assistant',text:'房源 A 尚有條件待查證。',comparison_status:'current'}]};
 const artifactBefore=JSON.stringify(artifact);let gateSnapshot=context.checkedLive;
 handler=url=>url==='/api/session/A'?response(gateSnapshot):undefined;
 await run('refresh()');
 const checkPanel=elements['current-checks'],checkBody=elements['current-checks-body'];
 assert.equal(checkPanel.hidden,false);assert.ok(longRequest.length>6000&&longRequest.length<=8000);
 const requestDetails=tags(checkBody,'details')[0];
 assert.equal(tags(requestDetails,'summary')[0].textContent,'已保存的需求與追問');
 assert.deepEqual(tags(requestDetails,'li').map(el=>el.textContent),[longRequest,unresolved]);
 const sectionRows=heading=>{const index=checkBody.children.findIndex(el=>el.tag==='h3'&&el.textContent===heading);assert.ok(index>=0);const list=checkBody.children[index+1];assert.equal(list.tag,'ul');return tags(list,'li').map(el=>el.textContent);};
 assert.deepEqual(sectionRows('尚待釐清的原話'),[unresolved]);
 assert.deepEqual(sectionRows('目前待辦'),[todo]);
 for(const tag of ['script','img','iframe','svg','object','style','link','a','strong'])assert.equal(tags(checkBody,tag).length,0,tag+' cannot be created by original request text');
 assert.equal(tags(requestDetails,'li')[0].children.length,0,'the original request is literal text, not parsed markup');
 const beforeChecksRender=network.length;run('render(checkedLive)');assert.equal(network.length,beforeChecksRender,'presenting a comparison cannot fetch resources');
 assert.equal(JSON.stringify(artifact),artifactBefore,'presenting the comparison cannot rewrite its artifact');
 // Source integrity can change without a session revision. The status alone
 // must remove the old result, including all hidden body content.
 for(const status of ['stale','historical','invalid']){
  gateSnapshot={...context.checkedLive,comparison_status:status};await run('refresh()');
  assert.equal(checkPanel.hidden,true,status+' comparison is unavailable');assert.equal(checkBody.children.length,0);assert.equal(checkBody.textContent,'');
  gateSnapshot=context.checkedLive;await run('refresh()');assert.equal(checkPanel.hidden,false);
 }
 context.missingComparison={...context.checkedLive,comparison_status:'not_checked',current_comparison:null};run('render(missingComparison)');
 assert.equal(checkPanel.hidden,true);assert.equal(checkBody.textContent,'');
 context.fixtureWithComparison={...state('A'),research_mode:'fixture',comparison_status:'current',current_comparison:artifact};
 run('render(fixtureWithComparison)');assert.equal(checkPanel.hidden,true,'the synthetic lane never displays live checks');assert.equal(checkBody.children.length,0);
 run('render(checkedLive)');assert.equal(checkPanel.hidden,false);
 let resolveOld;handler=url=>url==='/api/session/A'?new Promise(resolve=>resolveOld=resolve):undefined;
 const old=run('refresh()');await settle();await run("select('B')");
 assert.equal(elements.send.disabled,true);assert.equal(elements.title.textContent,'正在讀取這段對話…');
 assert.equal(checkPanel.hidden,true,'selection removes the old comparison before the next session loads');assert.equal(checkBody.textContent,'');
 resolveOld(response(context.checkedLive));await old;assert.notEqual(elements.title.textContent,'真實找房研究');
 assert.equal(checkPanel.hidden,true,'a late response cannot restore the previous session comparison');assert.equal(checkBody.children.length,0);handler=null;
 await run('refresh()');assert.equal(elements.title.textContent,'Person B');assert.equal(elements.send.disabled,false);
 assert.equal(checkPanel.hidden,true);assert.equal(checkBody.textContent,'');
 let fail=true;handler=(url,opts)=>{if(url.endsWith('/message')&&opts.method==='POST'){if(fail){fail=false;throw Error('uncertain response');}return response({ok:true});}};
 elements.message.value='Preserve this exact question.';
 await elements.composer.onsubmit({preventDefault(){}});assert.equal(elements.message.value,'Preserve this exact question.');
 await elements.composer.onsubmit({preventDefault(){}});const sent=captured.filter(x=>x.url.endsWith('/message'));
 assert.equal(sent.length,2);assert.equal(sent[0].data.client_id,sent[1].data.client_id);assert.equal(elements.message.value,'');
 fail=true;handler=(url,opts)=>{if(url.endsWith('/control')){if(fail){fail=false;throw Error('uncertain response');}return response({ok:true});}};
 await run("action('step')");await run("action('step')");const controls=captured.filter(x=>x.url.endsWith('/control'));
 assert.equal(controls[0].data.client_id,controls[1].data.client_id);
 handler=null;context.recoveredState={...state('B'),revision:2,status:'interrupted',pending_call:true};run('render(recoveredState)');
 assert.equal(elements.recover.hidden,false);assert.equal(elements.step.disabled,true);await elements.recover.onclick();
 assert.equal(captured.at(-1).data.action,'recover');
 context.choiceState={...state('B'),intent_guard_version:1,revision:3,messages:[{role:'assistant',call_id:'call-001-assistant',text:'Stored complete reply',display_text:'Two fictional examples: courtyard or station.',questions:[{question:'Which tradeoff fits you?',options:['Quiet courtyard','Closer station']},{question:'Which campus?',options:['I know the campus','Help me find it']}]}]};
 run('render(choiceState)');let form=elements.messages.children[0].children[2];
 assert.equal(form.children.length,4);assert.equal(form.children[0].children[1].children[0].checked,false);
 assert.equal(form.children[0].children[2].children[0].checked,false);
 form.children[0].children[1].children[0].onchange();
 const custom=form.children[0].children.at(-1);custom.value='<img src=x onerror=alert(1)> but flexible';custom.oninput();
 run('render(choiceState)');form=elements.messages.children[0].children[2];assert.equal(form.children[0].children[1].children[0].checked,true);
 fail=true;handler=(url,opts)=>{if(url.endsWith('/message')&&opts.method==='POST'){if(fail){fail=false;throw Error('uncertain response');}return response({ok:true});}};
 await form.onsubmit({preventDefault(){}});await form.onsubmit({preventDefault(){}});
 const choiceSends=captured.filter(x=>x.url.endsWith('/message')).slice(-2);
 assert.equal(choiceSends[0].data.client_id,choiceSends[1].data.client_id);
 assert.equal(choiceSends[1].data.text,'Which tradeoff fits you?\nQuiet courtyard；<img src=x onerror=alert(1)> but flexible');
 assert.equal(choiceSends[1].data.kind,'question');
 assert.deepEqual(choiceSends[1].data.clarification,{call_id:'call-001-assistant',answers:[{question_index:0,option_index:0,text:'<img src=x onerror=alert(1)> but flexible'}]});
 context.choiceState.messages.push({role:'human',text:'I prefer the courtyard.'});run('render(choiceState)');
 assert.equal(elements.messages.children[0].children[2].children[0].disabled,true);
 assert.equal(elements.messages.children[0].children[2].children.length,2);
 // A completed last slot must disable every path even before the backend
 // changes status from paused to budget. Drafts and read/export remain available.
 handler=null;
 context.withChoices={...state('B'),revision:10,messages:[{role:'assistant',text:'Choose one',questions:[{question:'Next preference?',options:['Quiet','Central']}]}]};
 run('render(withChoices)');let staleChoice=elements.messages.children[0].children[2];
 staleChoice.children[0].children[1].children[0].onchange();
 elements.message.value='Keep my unsent draft.';elements.amendment.checked=true;
 context.callCap={...context.withChoices,revision:11,limits:{max_calls:1,max_tokens:400000}};
 run('render(callCap)');
 for(const key of ['run','step','message','send','amendment'])assert.equal(elements[key].disabled,true,key+' at call cap');
 assert.equal(elements.export.disabled,false);assert.equal(elements.banner.hidden,false);assert.match(elements.banner.textContent,/執行次數上限/);
 assert.equal(elements.message.value,'Keep my unsent draft.');assert.equal(elements.amendment.checked,true);
 form=elements.messages.children[0].children[2];assert.equal(form.children[0].disabled,true);assert.equal(form.children[0].children[1].children[0].checked,true);
 const beforeCap=captured.length;
 await elements.composer.onsubmit({preventDefault(){}});await staleChoice.onsubmit({preventDefault(){}});
 await run("action('step')");await run("action('run')");assert.equal(captured.length,beforeCap,'disabled handlers cannot POST through stale references');
 let exported=0;handler=url=>{if(url==='/api/session/B/export'){exported++;return response({id:'B',persona_id:'P4'});}};
 await elements.export.onclick();assert.equal(exported,1);
 // The same guard uses known finite usage; null while pending is neither zero
 // usage nor a new failure, and human interruptions remain possible under cap.
 context.tokenCap={...state('B'),revision:12,tokens:100,limits:{max_calls:30,max_tokens:100}};run('render(tokenCap)');
 assert.equal(elements.run.disabled,true);assert.equal(elements.step.disabled,true);assert.equal(elements.send.disabled,true);assert.match(elements.banner.textContent,/token 額度/);
 const beforeTokens=captured.length;await elements.composer.onsubmit({preventDefault(){}});await run("action('run')");assert.equal(captured.length,beforeTokens);
 context.unknownPending={...state('B'),revision:13,status:'running',busy:true,pending_call:true,tokens:null};run('render(unknownPending)');
 assert.equal(elements.send.disabled,false);assert.equal(elements.message.disabled,false);assert.equal(elements.tokens.textContent,'計算中');assert.equal(elements['usage-bar'].hidden,true);
 assert.equal(elements.banner.hidden,true);assert.equal(elements.run.disabled,true);
 context.unknownIdle={...state('B'),revision:14,tokens:null};run('render(unknownIdle)');assert.equal(elements.send.disabled,false);assert.equal(elements.tokens.textContent,'用量未知');
 for(const status of ['error','interrupted']){context.failedStatus={...context.unknownIdle,status};run('render(failedStatus)');assert.equal(elements.send.disabled,true);assert.equal(elements.step.disabled,true);}
 context.ended={...state('B'),revision:15,status:'ended'};run('render(ended)');assert.equal(elements.run.disabled,true);assert.equal(elements.send.disabled,false);
 handler=null;elements.message.value='A human follow-up after the persona ends.';
 await elements.composer.onsubmit({preventDefault(){}});assert.equal(captured.at(-1).url,'/api/session/B/message');
 // Successful submit -> refresh reaches the cap -> finally must not re-enable.
 context.beforeLast={...state('B'),revision:16};run('render(beforeLast)');elements.message.value='Use the last remaining answer.';
 handler=(url,opts)=>url==='/api/session/B'?response({...state('B'),revision:17,calls:30}):undefined;
 await elements.composer.onsubmit({preventDefault(){}});assert.equal(elements.message.value,'');assert.equal(elements.send.disabled,true);assert.equal(elements.message.disabled,true);
 // An uncertain POST arriving after the cap preserves the draft and stable
 // intent; it must not enable a forbidden retry while the cap remains known.
 handler=null;run('render(beforeLast)');elements.message.value='Keep this uncertain submission.';
 let rejectMessage;handler=(url,opts)=>url.endsWith('/message')&&opts.method==='POST'?new Promise((resolve,reject)=>rejectMessage=reject):undefined;
 const uncertain=elements.composer.onsubmit({preventDefault(){}});await settle();run('render(callCap)');
 rejectMessage(Error('uncertain response after cap'));await uncertain;
 assert.equal(elements.message.value,'Keep this uncertain submission.');assert.equal(elements.send.disabled,true);
 const afterUncertain=captured.length;await elements.composer.onsubmit({preventDefault(){}});assert.equal(captured.length,afterUncertain);
 // The same late-error rule applies to structured clarification choices.
 handler=null;run('render(withChoices)');staleChoice=elements.messages.children[0].children[2];staleChoice.children[0].children[1].children[0].onchange();
 let rejectChoice;handler=(url,opts)=>url.endsWith('/message')&&opts.method==='POST'?new Promise((resolve,reject)=>rejectChoice=reject):undefined;
 const choosing=staleChoice.onsubmit({preventDefault(){}});await settle();run('render(callCap)');rejectChoice(Error('uncertain choice response'));await choosing;
 form=elements.messages.children[0].children[2];assert.equal(form.children[0].disabled,true);assert.equal(form.children[0].children[1].children[0].checked,true);
 // A response from B cannot clear or enable C's composer after selection changes.
 handler=null;run('render(beforeLast)');elements.message.value='Older B request.';
 let resolveMessage;handler=(url,opts)=>url==='/api/session/B/message'?new Promise(resolve=>resolveMessage=resolve):undefined;
 const oldMessage=elements.composer.onsubmit({preventDefault(){}});await settle();await run("select('C')");
 elements.message.value='New C draft stays here.';context.capC={...state('C'),revision:20,calls:30};run('render(capC)');
 handler=url=>url==='/api/session/C'?response(context.capC):undefined;
 resolveMessage(response({ok:true}));await oldMessage;
 assert.equal(elements.title.textContent,'Person C');assert.equal(elements.message.value,'New C draft stays here.');assert.equal(elements.send.disabled,true);
 assert.equal(elements.export.disabled,false);
 console.log('playground UI functional checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
