'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.textContent='';this.value='';this.style={};this.disabled=false;this.hidden=false;this.checked=false;this.scrollHeight=0;this.scrollTop=0;this.clientHeight=0;}
 append(...children){this.children.push(...children);}
 setAttribute(name,value){this[name]=value;}
 replaceChildren(...children){this.children=children;if(this.tag==='select'&&!this.value&&children.length)this.value=children[0].value;}
 get firstChild(){return this.children[0];}
 set innerHTML(_){throw Error('Untrusted HTML must never be rendered');}
 click(){if(this.onclick)return this.onclick();}
}
const ids=[...fs.readFileSync(path.join(__dirname,'../playground/index.html'),'utf8').matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
const elements=Object.fromEntries(ids.map(id=>[id,new Element(['persona','model'].includes(id)?'select':'div')]));
elements['max-calls'].value='30';elements['max-tokens'].value='400000';
const messages=[],captured=[];let handler=null,count=0;
function state(id){return {id,revision:1,persona_id:'P4',name:'Person '+id,model:'gpt-6-astra',status:'paused',auto:false,busy:false,notice:'',phase_label:'',persona_turn:1,patience_turns:3,calls:1,tokens:20,limits:{max_calls:30,max_tokens:400000},actor_calls:{assistant:1,persona:0},messages:[{role:'assistant',text:'<script>PRIVATE</script>'}],pending_count:0,mood:'wary',held_documents:[],events:[],criteria:['Get an actionable response'],pending_call:false};}
function response(value){return {ok:true,json:async()=>value};}
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
 crypto:{randomUUID:()=>`00000000-0000-4000-8000-${String(++count).padStart(12,'0')}`},
 localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,setInterval:()=>0,Blob,
 URL:{createObjectURL:()=> 'blob:private-export',revokeObjectURL(){}},
 fetch:async(url,opts)=>{
  if(opts.body)captured.push({url,data:JSON.parse(opts.body)});
  if(handler){const value=handler(url,opts);if(value!==undefined)return value;}
  if(url==='/api/catalog')return response({models:['gpt-6-astra'],personas:[{id:'P4',name:'Brett',identity:'Viewing tomorrow',language:'en',patience_turns:3,original_harness:'chat'}]});
  if(url==='/api/sessions')return response({sessions:[]});
  const match=url.match(/^\/api\/session\/([^/]+)$/);if(match)return response(state(match[1]));
  return response({ok:true});
 },console});
const run=code=>vm.runInContext(code,context);
const settle=async()=>{for(let i=0;i<8;i++)await new Promise(resolve=>setImmediate(resolve));};
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.equal(elements.connection.textContent,'本機測試台已連接');assert.equal(elements.persona.value,'P4');
 await run("select('A')");assert.equal(elements.title.textContent,'Person A');assert.equal(elements.messages.children[0].children[1].textContent,'<script>PRIVATE</script>');
 let resolveOld;handler=url=>url==='/api/session/A'?new Promise(resolve=>resolveOld=resolve):undefined;
 const old=run('refresh()');await settle();await run("select('B')");
 assert.equal(elements.send.disabled,true);assert.equal(elements.title.textContent,'正在讀取這段對話…');
 resolveOld(response(state('A')));await old;assert.notEqual(elements.title.textContent,'Person A');handler=null;
 await run('refresh()');assert.equal(elements.title.textContent,'Person B');assert.equal(elements.send.disabled,false);
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
 context.choiceState={...state('B'),revision:3,messages:[{role:'assistant',text:'Stored complete reply',display_text:'Two fictional examples: courtyard or station.',questions:[{question:'Which tradeoff fits you?',options:['Quiet courtyard','Closer station']},{question:'Which campus?',options:['I know the campus','Help me find it']}]}]};
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
 context.choiceState.messages.push({role:'human',text:'I prefer the courtyard.'});run('render(choiceState)');
 assert.equal(elements.messages.children[0].children[2].children[0].disabled,true);
 assert.equal(elements.messages.children[0].children[2].children.length,2);
 console.log('playground UI functional checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
