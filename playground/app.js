"use strict";
const $=id=>document.getElementById(id);
let catalog=null, current=null, selected=null, lastRevision=null, polling=false, messageIntent=null, createIntent=null, actionIntent=null, creating=false;
const choiceDrafts=new Map(), choiceIntents=new Map(), choiceSending=new Set(), messageSending=new Set();
const statuses={ready:"等待開始",paused:"已暫停",running:"對話進行中",ended:"Persona 結束",budget:"到達上限",error:"需要處理",interrupted:"待恢復"};
const modeNames={live:"真實找房研究",fixture:"合成人物測試 · 虛構資料"};
const capabilityDefaults={live:"可嘗試查詢公開網頁；能取得哪些資料，以本次研究結果為準。刊登頁面不代表已確認仍可租。",fixture:"合成人物測試；僅使用已提供的虛構材料，不執行即時搜尋。"};
function isLive(s){return s?.research_mode==="live";}
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
// Presentation only: a deliberately small Markdown subset, built with text
// nodes/elements. Unsupported syntax stays visible; source messages never change.
function replyLink(value){
 if(!/^https?:\/\//i.test(value)||/[\s\\\u0000-\u001f\u007f-\u009f]/u.test(value))return null;
 try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&url.hostname?url.href:null;}catch(_){return null;}
}
function closingMark(text,mark,start,budget){
 let previous=start;
 for(let at=text.indexOf(mark,start);at!==-1;at=text.indexOf(mark,at+mark.length)){
  budget.remaining-=at-previous+mark.length;if(budget.remaining<0)return -1;previous=at+mark.length;
  let slashes=0;for(let n=at-1;n>=0&&text[n]==='\\';n--)slashes++;
  if(slashes%2===0)return at;
 }budget.remaining-=text.length-previous;return -1;
}
function linkEnd(text,start,budget){
 let depth=1;
 for(let i=start;i<text.length;i++){
  if(--budget.remaining<0)return -1;
  if(text[i]==='\\'){i++;continue;}
  if(text[i]==='(')depth++;
  if(text[i]===')'&&!--depth)return i;
 }return -1;
}
function replyInline(parent,value,depth=0,links=true,budget={remaining:200000}){
 const text=String(value),flush=()=>{if(plain){parent.append(node('span',plain));plain='';}};let plain='';
 if(depth>=10||text.length>100000){parent.append(node('span',text));return;}
 for(let i=0;i<text.length;){
  if(--budget.remaining<0){plain+=text.slice(i);break;}
  if(text[i]==='\\'&&/[!"#$%&'()*+,\-./:;<=>?@[\]\\^_`{|}~]/.test(text[i+1]||'')){plain+=text[i+1];i+=2;continue;}
  if(text[i]==='`'){
   const mark=text.slice(i).match(/^`+/)[0],end=closingMark(text,mark,i+mark.length,budget);
   if(end!==-1){flush();parent.append(node('code',text.slice(i+mark.length,end)));i=end+mark.length;continue;}
  }
  const image=text[i]==='!'&&text[i+1]==='[',begin=image?i+1:i;
  if(text[begin]==='['){
   const close=closingMark(text,']',begin+1,budget),end=close!==-1&&text[close+1]==='('?linkEnd(text,close+2,budget):-1;
   if(end!==-1){
    const raw=text.slice(i,end+1),href=links&&!image?replyLink(text.slice(close+2,end)):null;
    if(href){flush();const a=node('a');a.href=href;a.target='_blank';a.rel='noopener noreferrer';a.referrerPolicy='no-referrer';replyInline(a,text.slice(begin+1,close),depth+1,false,budget);parent.append(a);}else plain+=raw;
    i=end+1;continue;
   }
  }
  const mark=['***','___','**','__','*','_'].find(m=>text.startsWith(m,i));
  if(mark&&!/\s/.test(text[i+mark.length]||' ')&&!(mark.includes('_')&&/[\p{L}\p{N}]/u.test(text[i-1]||''))){
   const end=closingMark(text,mark,i+mark.length,budget);
   if(end>i+mark.length&&!/\s/.test(text[end-1])){
    flush();const el=node(mark.length===1?'em':'strong');
    if(mark.length===3){const em=node('em');replyInline(em,text.slice(i+mark.length,end),depth+1,links,budget);el.append(em);}else replyInline(el,text.slice(i+mark.length,end),depth+1,links,budget);
    parent.append(el);i=end+mark.length;continue;
   }
  }
  plain+=text[i++];
 }flush();
}
function replyCells(line){
 let value=line.trim();if(value.startsWith('|'))value=value.slice(1);if(value.endsWith('|')&&!value.endsWith('\\|'))value=value.slice(0,-1);
 const cells=[];let cell='',ticks='';
 for(let i=0;i<value.length;i++){
  if(value[i]==='\\'&&i+1<value.length){cell+=value[i]+value[++i];continue;}
  if(value[i]==='`'){const mark=value.slice(i).match(/^`+/)[0];ticks=ticks===mark?'':ticks||mark;cell+=mark;i+=mark.length-1;continue;}
  if(value[i]==='|'&&!ticks){cells.push(cell.trim());cell='';}else cell+=value[i];
 }cells.push(cell.trim());return cells;
}
function replyList(line){return line.match(/^ {0,3}([-+*]|\d{1,9}[.)])\s+(\S.*)$/);}
function replyTable(lines,i){
 if(!lines[i]?.includes('|')||!lines[i+1]?.includes('|'))return false;
 const cells=replyCells(lines[i]),rules=replyCells(lines[i+1]);
 return cells.length>1&&cells.length<=32&&cells.length===rules.length&&rules.every(v=>/^:?-{3,}:?$/.test(v));
}
function renderReply(value){
 const bubble=node('div',undefined,'bubble markdown'),text=String(value??'');
 if(text.length>100000){bubble.append(node('p',text));return bubble;}
 const lines=text.replace(/\r\n?/g,'\n').split('\n');
 for(let i=0;i<lines.length;){
  if(!lines[i].trim()){i++;continue;}
  const fence=lines[i].match(/^ {0,3}(`{3,}|~{3,})([^`]*)$/);
  if(fence){
   let end=i+1;const close=new RegExp('^ {0,3}'+fence[1][0]+'{'+fence[1].length+',}\\s*$');
   while(end<lines.length&&!close.test(lines[end]))end++;
   if(end<lines.length){const pre=node('pre');pre.append(node('code',lines.slice(i+1,end).join('\n')));bubble.append(pre);i=end+1;continue;}
   bubble.append(node('p',lines.slice(i).join('\n')));break;
  }
  const heading=lines[i].match(/^ {0,3}(#{1,6})\s+(.+)$/);
  if(heading){const h=node('h'+Math.min(6,heading[1].length+2));replyInline(h,heading[2]);bubble.append(h);i++;continue;}
  if(replyTable(lines,i)){
   const wrapper=node('div',undefined,'reply-table'),table=node('table'),head=node('thead'),tr=node('tr'),body=node('tbody');
   const names=replyCells(lines[i]);for(const name of names){const th=node('th');th.scope='col';replyInline(th,name);tr.append(th);}head.append(tr);table.append(head,body);i+=2;
   while(i<lines.length&&lines[i].includes('|')){const cells=replyCells(lines[i]);if(cells.length!==names.length)break;const row=node('tr');for(const cell of cells){const td=node('td');replyInline(td,cell);row.append(td);}body.append(row);i++;}
   wrapper.append(table);bubble.append(wrapper);continue;
  }
  const first=replyList(lines[i]);
  if(first){
   const ordered=/^\d/.test(first[1]),list=node(ordered?'ol':'ul');if(ordered)list.start=parseInt(first[1],10);
   while(i<lines.length){const item=replyList(lines[i]);if(!item||/^\d/.test(item[1])!==ordered)break;const li=node('li');if(ordered)li.value=parseInt(item[1],10);const content=[item[2]];i++;
    while(i<lines.length&&/^\s{2,}\S/.test(lines[i])&&!replyList(lines[i]))content.push(lines[i++].trimStart());
    replyInline(li,content.join('\n'));list.append(li);
   }bubble.append(list);continue;
  }
  const content=[lines[i++]];
  while(i<lines.length&&lines[i].trim()&&!replyList(lines[i])&&!/^ {0,3}(?:#{1,6}\s|`{3,}|~{3,})/.test(lines[i])&&!replyTable(lines,i))content.push(lines[i++]);
  const p=node('p');replyInline(p,content.join('\n'));bubble.append(p);
 }return bubble;
}
function limitNotice(s){
 if(!s)return "";
 if(Number.isFinite(s.calls)&&Number.isFinite(s.limits?.max_calls)&&s.calls>=s.limits.max_calls)return "這段對話已達執行次數上限。仍可閱讀、匯出紀錄；未送出的草稿會保留。";
 if(Number.isFinite(s.tokens)&&Number.isFinite(s.limits?.max_tokens)&&s.tokens>=s.limits.max_tokens)return "這段對話已用完 token 額度。仍可閱讀、匯出紀錄；未送出的草稿會保留。";
 return "";
}
function canCompose(s){return Boolean(s&&s.id===selected&&s.compatible!==false&&!limitNotice(s)&&!["error","interrupted","budget"].includes(s.status));}
function canAdvance(s,action){return Boolean(s&&s.id===selected&&!s.busy&&s.compatible!==false&&!limitNotice(s)&&!["error","interrupted","ended","budget"].includes(s.status)&&(!isLive(s)||(action==="step"&&(s.next_actor||s.pending_count>0))));}
function syncComposer(){const blocked=!canCompose(current);$("message").disabled=blocked;$("amendment").disabled=blocked||isLive(current);$("send").disabled=blocked||messageSending.has(selected);}
function canChoose(s,index,id){return canCompose(s)&&s.id===id&&index===s.messages.length-1&&!s.busy&&!s.pending_count&&!choiceSending.has(`${id}:${index}`);}
function clarificationForm(s,m,index){
 const key=`${s.id}:${index}`, form=node("form",undefined,"clarifications");
 const enabled=canChoose(s,index,s.id);
 if(!choiceDrafts.has(key))choiceDrafts.set(key,{});const draft=choiceDrafts.get(key);
 m.questions.forEach((q,qi)=>{const field=node("fieldset"),legend=node("legend",q.question);field.append(legend);field.disabled=!enabled;
   q.options.forEach((label,oi)=>{const row=node("label",undefined,"choice"),input=node("input");input.type="radio";input.name=`choice-${index}-${qi}`;input.value=String(oi);input.checked=draft[qi]?.option===oi;
    input.onchange=()=>{draft[qi]={...(draft[qi]||{}),option:oi};};row.append(input,node("span",label));field.append(row);});
   const custom=node("input");custom.type="text";custom.maxLength=500;custom.placeholder="也可以自己填寫，或補充細節";custom.setAttribute("aria-label",`${q.question}：自行填寫`);custom.value=draft[qi]?.text||"";custom.oninput=()=>{draft[qi]={...(draft[qi]||{}),text:custom.value};};field.append(custom);form.append(field);
 });
 if(enabled){const button=node("button","送出選擇，繼續討論","primary");button.type="submit";form.append(button,node("small","可以只回答部分問題，也可以在下方直接插話。","fine"));
 form.onsubmit=async event=>{event.preventDefault();if(!canChoose(current,index,s.id)){toast(limitNotice(current)||"請先查看最新對話，再送出選擇。");return;}const parts=m.questions.flatMap((q,qi)=>{const d=draft[qi]||{},v=[Number.isInteger(d.option)?q.options[d.option]:"",(d.text||"").trim()].filter(Boolean);return v.length?[q.question+"\n"+v.join("；")]:[];});if(!parts.length){toast("先選一項或填寫你的想法。");return;}button.disabled=true;choiceSending.add(key);const text=parts.join("\n\n"),fingerprint=JSON.stringify([s.id,text]);let intent=choiceIntents.get(key);if(!intent||intent.fingerprint!==fingerprint){intent={fingerprint,id:crypto.randomUUID()};choiceIntents.set(key,intent);}try{await api(`/api/session/${s.id}/message`,{text,kind:"question",client_id:intent.id});choiceDrafts.delete(key);choiceIntents.delete(key);await refresh();}catch(error){toast(error.message);}finally{choiceSending.delete(key);if(current?.id===selected)render(current);}};
 }return form;
}
function toast(text){$("toast").textContent=text;$("toast").hidden=false;setTimeout(()=>$("toast").hidden=true,6000);}
async function api(path,data){const opts={cache:"no-store",headers:{"X-Pea-Client":"persona-lab"}};if(data!==undefined){opts.method="POST";opts.headers["Content-Type"]="application/json";opts.body=JSON.stringify(data);}const r=await fetch(path,opts);const body=await r.json();if(!r.ok)throw Error(body.message||"操作未完成，請查看狀態。");return body;}
function profile(){const p=catalog.personas.find(x=>x.id===$("persona").value);$("profile").replaceChildren(...(p?[node("p",p.identity),node("small",`${p.language} · 耐心 ${p.patience_turns} 回合`)]:[]));}
function creationMode(){
 const live=$("research-mode").value==="live",request=$("initial-request").value;
 $("live-setup").hidden=!live;$("fixture-setup").hidden=live;
 $("create").textContent=live?"保存需求，建立研究":"建立合成測試";
 $("create").disabled=creating||!catalog||(live?(!request.trim()||request.length>8000):!$("persona").value);
 $("call-limit-note").textContent=(live?"":"包含回答與合成人物。")+"每次呼叫之間檢查上限，可能超出一則；不自動重試。思考強度固定 low。";
 if(!current&&!selected){$("session-label").textContent=modeNames[live?"live":"fixture"];$("title").textContent=live?"寫下需求，開始研究":"挑一個合成人物，開始測試";$("run").hidden=live;$("step").textContent=live?"研究並回覆":"下一步";$("capability-status").textContent=capabilityDefaults[live?"live":"fixture"];$("empty-title").textContent=live?"把選項查清楚，再一起決定":"觀察合成人物的多輪對話";$("empty-note").textContent=live?"從大致需求開始，逐步比較來源、費用與取捨。你可以隨時補充問題或修改條件。":"人物會追問、補充虛構材料，也可能失去耐心。你可以中途插話，觀察 Codex 如何接續。";$("turn-label").textContent=live?"真人輸入":"合成人物回合";}
}
function statusLabel(s){return isLive(s)&&s.status==="paused"?(s.next_actor||s.pending_count?"等待研究":"等待你的回覆"):statuses[s.status]||s.status;}
async function list(){const rows=await api("/api/sessions");$("sessions").replaceChildren();for(const s of rows.sessions){const b=node("button",s.name,"session-card"+(s.id===selected?" active":""));b.append(node("small",`${isLive(s)?"真實研究":"合成測試"} · ${statusLabel(s)} · ${s.calls} calls · ${s.tokens===null?"用量未知":s.tokens.toLocaleString()+" tokens"}`));b.onclick=()=>select(s.id);$("sessions").append(b);}}
async function select(id){selected=id;lastRevision=null;current=null;$("title").textContent="正在讀取這段對話…";$("messages").replaceChildren();for(const key of ["step","run","pause","send","message","amendment","export"])$(key).disabled=true;try{localStorage.setItem("pea-lab-session",id);}catch(_){}await refresh();await list();}
function render(s){current=s;const live=isLive(s);$("title").textContent=s.name;$("session-label").textContent=live?`真實找房研究 · ${s.model}`:`合成人物測試 · 虛構資料 · ${s.persona_id} · ${s.model}`;$("status").textContent=statusLabel(s);$("phase").textContent=s.phase_label||"";$("turn-label").textContent=live?"真人輸入":"合成人物回合";$("turn").textContent=live?String(s.persona_turn):`${s.persona_turn}/${s.patience_turns}`;$("calls").textContent=`${s.calls}/${s.limits.max_calls}`;const knownTokens=Number.isFinite(s.tokens);$("tokens").textContent=knownTokens?s.tokens.toLocaleString():(s.busy||s.pending_call?"計算中":"用量未知");$("usage-bar").hidden=!knownTokens;$("usage-bar").style.width=knownTokens?`${Math.max(0,Math.min(100,100*s.tokens/s.limits.max_tokens))}%`:"";$("usage-note").textContent=`上限 ${s.limits.max_tokens.toLocaleString()} · 回答 ${s.actor_calls.assistant} 次`+(live?"":`／合成人物 ${s.actor_calls.persona} 次`);
 const capNotice=limitNotice(s);$("step").textContent=live?"研究並回覆":"下一步";$("step").disabled=!canAdvance(s,"step");$("run").hidden=live;$("run").disabled=!canAdvance(s,"run");$("pause").disabled=!s.busy&&!s.auto;$("export").disabled=false;$("recover").hidden=!(s.pending_call&&!s.busy);$("message-label").textContent=live?"繼續討論":"加入這段對話";$("amendment-label").hidden=live;$("send").textContent=live?"送出並研究 ↑":"插入問題 ↑";syncComposer();$("banner").hidden=!(capNotice||s.notice);$("banner").textContent=[capNotice,s.notice].filter(Boolean).join("\n");$("queue-note").textContent=live?(s.pending_count?`${s.pending_count} 則問題已保存，會依序研究並回覆。`:"送出後繼續研究；研究途中也能補充需求。"):(s.pending_count?`${s.pending_count} 則插話已保存，將於目前這則完成後優先回答。`:"插話會保存，於目前這則完成後優先回答。");
 $("capability-status").textContent=typeof s.capability_status==="string"&&s.capability_status?s.capability_status:capabilityDefaults[live?"live":"fixture"];
 $("fixture-observations").hidden=live;$("criteria").replaceChildren(...s.criteria.map(x=>node("li",x)));$("behavior-title").textContent=live?"研究進度":"行為與補件";
 if(live){$("behavior").replaceChildren(node("p",capNotice?"已達用量上限，可閱讀與匯出已保存的內容。":s.compatible===false?"這段紀錄目前只能閱讀與匯出。":["error","interrupted","budget"].includes(s.status)?"研究尚未完成，請查看上方狀態。":s.busy?"正在研究你的問題。":s.next_actor||s.pending_count?"需求已保存，可以開始研究。":"回答已保存，等你補充問題或調整條件。"));}
 else{$("behavior").replaceChildren(node("p",`情緒：${s.mood} · 尚可 ${Math.max(0,s.patience_turns-s.persona_turn)} 回合`),node("p",`合成人物持有 ${s.held_documents.length} 份文件`));for(const e of s.events.slice(-7))$("behavior").append(node("div",`第 ${e[0]} 回合 · ${e[1]}`,"event"));}
 $("mode-limit-note").textContent=live?"研究結果應附來源連結與查詢時間，並區分刊登資訊、推估及尚未確認的可租狀態。":"合成人物的後續訊息由 Codex 產生，使用分開的歷史。測試僅使用所提供的虛構材料，沒有即時查詢；不代表真實在租房源。";
 const box=$("messages"), nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<180;box.replaceChildren();s.messages.forEach((m,index)=>{const article=node("article",undefined,`message ${m.role}`);article.append(node("div",m.role==="assistant"?"Codex":m.role==="human"?(live?"你":m.kind==="amendment"?"你 · 情境變更":"你 · 插話"):m.role==="persona"?`${s.name} · 合成人物`:"紀錄","speaker"));if(m.pending)article.firstChild.append(node("small","已保存・排隊中"));article.append(renderReply(m.display_text??m.text));if(m.questions?.length)article.append(clarificationForm(s,m,index));box.append(article);});if(s.busy){const pending=node("article",undefined,"message system");pending.append(node("div",s.phase_label+"…","bubble"));box.append(pending);}if(nearBottom||lastRevision===null)box.scrollTop=box.scrollHeight;
}
async function refresh(){if(!selected||polling)return;polling=true;try{const requestedId=selected;const s=await api(`/api/session/${requestedId}`);if(selected!==requestedId)return;if(s.revision!==lastRevision||s.compatible!==current?.compatible){render(s);lastRevision=s.revision;}}catch(e){toast(e.message);}finally{polling=false;}}
async function action(action){if(["step","run"].includes(action)&&!canAdvance(current,action)){if(limitNotice(current))toast(limitNotice(current));return;}try{const id=selected,fingerprint=JSON.stringify([id,action]);if(!actionIntent||actionIntent.fingerprint!==fingerprint)actionIntent={fingerprint,id:crypto.randomUUID()};const intent=actionIntent;await api(`/api/session/${id}/control`,{action,client_id:intent.id});if(actionIntent===intent)actionIntent=null;await refresh();await list();}catch(e){toast(e.message);}}
$("persona").onchange=()=>{profile();creationMode();};$("research-mode").onchange=creationMode;$("initial-request").oninput=creationMode;$("refresh").onclick=()=>list().catch(e=>toast(e.message));$("step").onclick=()=>action("step");$("run").onclick=()=>action("run");$("pause").onclick=()=>action("pause");$("recover").onclick=()=>action("recover");
$("create").onclick=async()=>{if(creating||!catalog)return;const research_mode=$("research-mode").value,live=research_mode==="live",initial_request=$("initial-request").value;if(live&&(!initial_request.trim()||initial_request.length>8000)){toast("請先寫下找房需求，最多 8,000 字。");return;}creating=true;creationMode();try{const settings={research_mode,...(live?{initial_request}:{persona_id:$("persona").value}),model:$("model").value,max_calls:Number($("max-calls").value),max_tokens:Number($("max-tokens").value),seed:1};const fingerprint=JSON.stringify(settings);if(!createIntent||createIntent.fingerprint!==fingerprint)createIntent={fingerprint,id:crypto.randomUUID()};const s=await api("/api/sessions",{...settings,client_id:createIntent.id});createIntent=null;await select(s.id);}catch(e){toast(e.message);}finally{creating=false;creationMode();}};
$("composer").onsubmit=async e=>{e.preventDefault();const text=$("message").value,id=selected;if(!text.trim()||!canCompose(current)||messageSending.has(id))return;const kind=!isLive(current)&&$("amendment").checked?"amendment":"question";messageSending.add(id);syncComposer();try{const fingerprint=JSON.stringify([id,text,kind]);if(!messageIntent||messageIntent.fingerprint!==fingerprint)messageIntent={fingerprint,id:crypto.randomUUID()};const intent=messageIntent;await api(`/api/session/${id}/message`,{text,kind,client_id:intent.id});if(messageIntent===intent)messageIntent=null;if(selected===id&&$("message").value===text){$("message").value="";$("amendment").checked=false;}await refresh();}catch(err){toast(err.message);}finally{messageSending.delete(id);syncComposer();}};
$("export").onclick=async()=>{try{const s=await api(`/api/session/${selected}/export`);const url=URL.createObjectURL(new Blob([JSON.stringify(s,null,2)],{type:"application/json"}));const a=node("a");a.href=url;a.download=isLive(s)?`PRIVATE-research-${s.id.slice(0,8)}.json`:`PRIVATE-persona-${s.persona_id}-${s.id.slice(0,8)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(e.message);}};
async function start(){try{catalog=await api("/api/catalog");const modes=["live","fixture"].filter(mode=>(catalog.research_modes||["fixture"]).includes(mode));$("research-mode").replaceChildren(...modes.map(mode=>{const o=node("option",modeNames[mode]);o.value=mode;return o;}));$("research-mode").value=modes[0]||"fixture";$("persona").replaceChildren(...catalog.personas.map(p=>{const o=node("option",`${p.id} · ${p.name}`);o.value=p.id;return o;}));$("model").replaceChildren(...catalog.models.map(m=>{const o=node("option",m);o.value=m;return o;}));profile();creationMode();$("connection").textContent="本機研究介面已連接";await list();let previous=null;try{previous=localStorage.getItem("pea-lab-session");}catch(_){}if(previous)await select(previous);setInterval(refresh,1200);}catch(e){$("connection").textContent="連線未就緒";toast(e.message);}}
start();
