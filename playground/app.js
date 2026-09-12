"use strict";
const $=id=>document.getElementById(id);
let catalog=null, current=null, selected=null, lastRevision=null, polling=false, createIntent=null, actionIntent=null, creating=false;
const choiceDrafts=new Map(), choiceIntents=new Map(), choiceSending=new Set(), messageSending=new Set();
let booted=false,catalogPolling=false;
let replayPreview=null,replayLoading=false,replayCreating=false,replayPreviewRequest=0;
const replayIntents=new Map(),replayComparisonOpen=new Map();
// Drafts remain in memory only. Uploaded bytes never enter browser storage or exports.
const initialDraft={attachments:[],path:""},messageDrafts=new Map(),messageIntents=new Map(),pickerTargets=new Map();
const INITIAL_DRAFT="initial",MAX_ATTACHMENT_BYTES=25*1024*1024,MAX_ATTACHMENTS=6;
const statuses={ready:"等待開始",paused:"已暫停",running:"對話進行中",ended:"Persona 結束",budget:"到達上限",error:"需要處理",interrupted:"待恢復"};
const modeNames={live:"Agent 對話測試",fixture:"合成人物測試 · 虛構資料"};
const capabilityDefaults={live:"顯示模型原始回覆，保存你的追問與條件變更；房源資料可直接貼入。",fixture:"合成人物測試；僅使用已提供的虛構材料，不執行即時搜尋。"};
const executionLabels={research_depth:{lite:"精簡（lite）",standard:"標準（standard）",deep:"深入（deep）"},reasoning_effort:{low:"低（low）",medium:"中（medium）",high:"高（high）"}};
const executionSources={user_selected:"使用者選擇",host_default:"主機預設",persona_card:"人物卡",legacy_record:"舊版紀錄",unrecorded:"未記錄"};
function executionOptions(key){const field=key==="research_depth"?"research_depths":"reasoning_efforts",values=catalog?.execution_options?.[field];return Array.isArray(values)?values.filter(value=>Object.hasOwn(executionLabels[key],value)):[];}
function executionDefault(key){const values=executionOptions(key),preferred=catalog?.execution_options?.defaults?.[key];return values.includes(preferred)?preferred:values.includes(key==="research_depth"?"standard":"low")?(key==="research_depth"?"standard":"low"):values[0]||"";}
function executionSelections(prefix=""){const result={};for(const key of Object.keys(executionLabels))if(executionOptions(key).length)result[key]=$(prefix+key.replaceAll("_","-")).value;return result;}
function validExecutionSelections(values){return Object.keys(executionLabels).every(key=>!executionOptions(key).length||executionOptions(key).includes(values[key]));}
function initializeExecutionSelectors(prefix=""){for(const key of Object.keys(executionLabels)){const select=$(prefix+key.replaceAll("_","-")),values=executionOptions(key);select.replaceChildren(...(values.length?values:[""]).map(value=>{const option=node("option",executionLabels[key][value]||"未提供可選設定");option.value=value;return option;}));select.value=executionDefault(key);select.disabled=!values.length;}}
function resetCreationDepth(){const persona=catalog?.personas.find(item=>item.id===$("persona").value),value=$("research-mode").value==="fixture"?persona?.runtime_settings?.budget_mode:null;$("research-depth").value=executionOptions("research_depth").includes(value)?value:executionDefault("research_depth");}
function recordedExecutionLabel(labels,value){return Object.hasOwn(labels,value)?labels[value]:"未記錄";}
function executionValue(settings,key){return recordedExecutionLabel(executionLabels[key],settings?.[key]);}
function renderSessionExecution(settings){$("session-execution").hidden=false;$("session-execution").textContent=`研究深度基準：${executionValue(settings,"research_depth")} · 模型思考強度：${executionValue(settings,"reasoning_effort")}`;$("session-execution").title=`研究深度來源：${recordedExecutionLabel(executionSources,settings?.research_depth_source)}；思考強度來源：${recordedExecutionLabel(executionSources,settings?.reasoning_effort_source)}。設定基準不代表已確認實際研究涵蓋程度；追加要求保留在對話中。`;}
function isLive(s){return s?.research_mode==="live";}
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function renderSkillArtifact(prefix,artifact){
 const label=$(prefix+"-label"),detail=$(prefix+"-detail"),scope=prefix==="catalog-skill"?"新對話":"此對話";
 const published=artifact?.name==="pea-princess"&&artifact.kind==="public_zip"&&typeof artifact.sha256==="string"&&/^[0-9a-f]{64}$/i.test(artifact.sha256)&&Number.isSafeInteger(artifact.file_count)&&artifact.file_count>0;
 detail.replaceChildren();label.title="";
 if(published){const hash=artifact.sha256.toLowerCase();label.textContent=`${scope} · pea-princess 公開 ZIP · ${hash.slice(0,12)}`;label.title=`pea-princess 公開 ZIP\nSHA-256: ${hash}\n${artifact.file_count} 個檔案`;detail.append(node("p",`${artifact.file_count} 個檔案 · SHA-256`),node("code",hash));}
 else if(["development","development_tree"].includes(artifact?.kind)){label.textContent=`${scope} · 開發版本，未核對公開 ZIP`;detail.append(node("p","目前沒有已核對的公開 ZIP 指紋。"));}
 else{label.textContent=prefix==="catalog-skill"?"新對話 · skill 來源未確認":"此對話 · 舊版或來源未確認";detail.append(node("p",prefix==="catalog-skill"?"目前沒有完整的公開 ZIP 版本紀錄。":"這段紀錄沒有可確認的公開 ZIP 指紋。"));}
}
function renderSourceSync(){
 const sync=catalog?.source_sync,target=$("source-sync");
 if(!sync){target.textContent="尚未確認來源同步狀態";return;}
 target.textContent=sync.mode==="managed"?(sync.current?`公開來源已同步 · ${sync.runtime_digest?.slice(0,12)||""}`:"公開來源有更新，正在同步；完成後可建立新測試。") :"固定版本測試 · 不自動跟隨來源更新";
 target.title=sync.reason||"";
}
async function refreshCatalog(){
 if(catalogPolling)return;catalogPolling=true;
 try{if(!booted){await start();return;}catalog=await api("/api/catalog");$("connection").textContent="本機研究介面已連接";renderSourceSync();creationMode();syncReplayControls();}
 catch(error){if(catalog)catalog={...catalog,source_sync:{mode:"managed",current:false,reason:"等待測試台連線恢復"}};$("connection").textContent="等待測試台重新連線";renderSourceSync();creationMode();}
 finally{catalogPolling=false;}
}
function attachmentDraft(key){if(key===INITIAL_DRAFT)return initialDraft;if(!messageDrafts.has(key))messageDrafts.set(key,{text:"",amendment:false,path:"",attachments:[]});return messageDrafts.get(key);}
function saveComposerDraft(){if(!selected)return;const draft=attachmentDraft(selected);draft.text=$("message").value;draft.amendment=$("amendment").checked;draft.path=$("message-path").value;}
function restoreComposerDraft(){const draft=selected?attachmentDraft(selected):{text:"",amendment:false,path:""};$("message").value=draft.text;$("amendment").checked=draft.amendment;$("message-path").value=draft.path;}
function acceptsAttachments(s){return isLive(s)&&s.output_mode==="agent";}
function attachmentTarget(prefix){return prefix==="initial"?(!creating&&catalog&&$("research-mode").value==="live"?INITIAL_DRAFT:null):(canCompose(current)&&acceptsAttachments(current)&&!messageSending.has(selected)?selected:null);}
function attachmentIds(draft){return draft.attachments.filter(item=>item.state==="ready").map(item=>item.meta.id);}
function attachmentPending(draft){return draft.attachments.some(item=>item.state!=="ready");}
function fileSize(bytes){return Number.isFinite(bytes)?(bytes<1024?`${bytes} B`:bytes<1024*1024?`${Math.ceil(bytes/1024)} KB`:`${(bytes/1024/1024).toFixed(1)} MB`):"";}
function renderAttachmentDraft(prefix,key){
 const area=$(prefix+"-attachments"),list=$(prefix+"-file-list"),draft=key?attachmentDraft(key):{attachments:[]};
 area.hidden=prefix==="initial"?$("research-mode").value!=="live":!acceptsAttachments(current);
 const allowed=attachmentTarget(prefix)!==null,full=draft.attachments.length>=MAX_ATTACHMENTS;
 for(const suffix of ["pick","files","path","path-add"])$(prefix+"-"+suffix).disabled=!allowed||full;
 list.replaceChildren();for(const item of draft.attachments){
  const row=node("div",undefined,"attachment-chip"+(item.state==="error"?" attachment-error":"")),info=node("div",undefined,"attachment-info");
  info.append(node("span",item.meta?.name||item.name,"attachment-name"),node("small",item.state==="uploading"?"正在加入…":item.state==="error"?item.error:[fileSize(item.meta.bytes),"待送出"].filter(Boolean).join(" · ")));
  const remove=node("button","×");remove.type="button";remove.disabled=prefix==="initial"?creating:messageSending.has(key);remove.setAttribute("aria-label",`移除 ${item.meta?.name||item.name}`);
  remove.onclick=()=>{if(prefix==="initial"?creating:messageSending.has(key))return;draft.attachments=draft.attachments.filter(value=>value!==item);attachmentsUpdated(key);};row.append(info,remove);list.append(row);
 }
}
function attachmentsUpdated(key){if(key===INITIAL_DRAFT)creationMode();else if(key===selected)syncComposer();}
function readFileBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error("無法讀取檔案，請重新選擇。"));reader.onabort=()=>reject(Error("檔案讀取已取消。"));reader.onload=()=>{const value=String(reader.result||""),comma=value.indexOf(",");if(comma<0)reject(Error("無法讀取檔案，請重新選擇。"));else resolve(value.slice(comma+1));};reader.readAsDataURL(file);});}
async function addAttachment(key,source){
 const draft=attachmentDraft(key);if(draft.attachments.length>=MAX_ATTACHMENTS){toast("每則最多加入 6 份檔案，請先移除一份。");return;}
 const item={key:crypto.randomUUID(),name:source.file?.name||source.path,state:"uploading"};draft.attachments.push(item);attachmentsUpdated(key);
 try{
  if(source.file&&source.file.size>MAX_ATTACHMENT_BYTES)throw Error("檔案超過 25 MB，請選擇較小的檔案。");
  const payload=source.file?{name:source.file.name,content_base64:await readFileBase64(source.file)}:{path:source.path};
  if(!draft.attachments.includes(item))return;
  const meta=await api("/api/attachments",payload);if(!meta||typeof meta.id!=="string"||!meta.id)throw Error("檔案未加入，請移除後再試一次。");
  item.meta=meta;item.state="ready";
 }catch(error){item.state="error";item.error=error.message||"檔案未加入，請移除後再試一次。";}finally{attachmentsUpdated(key);}
}
function addFiles(key,files){return Promise.all(Array.from(files).map(file=>addAttachment(key,{file})));}
function wireAttachments(prefix,dropId){
 const picker=$(prefix+"-files"),path=$(prefix+"-path"),drop=$(dropId);
 $(prefix+"-pick").onclick=()=>{const key=attachmentTarget(prefix);if(key===null)return;pickerTargets.set(prefix,key);picker.value="";picker.click();};
 picker.onchange=()=>{const key=pickerTargets.get(prefix)??attachmentTarget(prefix);pickerTargets.delete(prefix);const files=Array.from(picker.files||[]);picker.value="";if(key!==null)return addFiles(key,files);};
 path.oninput=()=>{const key=prefix==="initial"?INITIAL_DRAFT:selected;if(key)attachmentDraft(key).path=path.value;};
 const addPath=()=>{const key=attachmentTarget(prefix),value=path.value.trim();if(key===null||!value)return;const draft=attachmentDraft(key);if(draft.attachments.length>=MAX_ATTACHMENTS){toast("每則最多加入 6 份檔案，請先移除一份。");return;}draft.path="";path.value="";return addAttachment(key,{path:value});};
 $(prefix+"-path-add").onclick=addPath;path.onkeydown=event=>{if(event.key==="Enter"){event.preventDefault();return addPath();}};
 const hasFiles=event=>Array.from(event.dataTransfer?.types||[]).includes("Files");
 drop.ondragover=event=>{if(!hasFiles(event))return;event.preventDefault();if(attachmentTarget(prefix)!==null){event.dataTransfer.dropEffect="copy";drop.setAttribute("data-file-drag","true");}};
 drop.ondragleave=()=>drop.setAttribute("data-file-drag","false");
 drop.ondrop=event=>{drop.setAttribute("data-file-drag","false");const files=event.dataTransfer?.files;if(!files?.length)return;event.preventDefault();const key=attachmentTarget(prefix);if(key!==null)return addFiles(key,files);};
 drop.onpaste=event=>{const files=event.clipboardData?.files;if(!files?.length)return;const key=attachmentTarget(prefix);if(key===null)return;event.preventDefault();return addFiles(key,files);};
}
function renderMessageAttachments(items){const list=node("div",undefined,"message-attachments");for(const meta of items){if(!meta||typeof meta.name!=="string")continue;const row=node("div",undefined,"attachment-chip");row.append(node("span",meta.name,"attachment-name"),node("small",fileSize(meta.bytes)));list.append(row);}return list;}
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
 if(Number.isFinite(s.calls)&&Number.isFinite(s.limits?.max_calls)&&s.calls>=s.limits.max_calls)return "這段對話已達執行次數上限。仍可閱讀、匯出紀錄；請建立新對話繼續測試。";
 if(Number.isFinite(s.tokens)&&Number.isFinite(s.limits?.max_tokens)&&s.tokens>=s.limits.max_tokens)return "這段對話已用完 token 額度。仍可閱讀、匯出紀錄；請建立新對話繼續測試。";
 return "";
}
function canCompose(s){return Boolean(s&&s.id===selected&&s.compatible!==false&&!limitNotice(s)&&!["error","interrupted","budget"].includes(s.status));}
function canAdvance(s,action){return Boolean(s&&s.id===selected&&!s.busy&&s.compatible!==false&&!limitNotice(s)&&!["error","interrupted","ended","budget"].includes(s.status)&&(!isLive(s)||(s.replay?.remaining>0)||(action==="step"&&(s.next_actor||s.pending_count>0))));}
function syncComposer(){const blocked=!canCompose(current);$("message").disabled=blocked;$("amendment").disabled=blocked||isLive(current);$("send").disabled=blocked||messageSending.has(selected)||(selected&&attachmentPending(attachmentDraft(selected)));renderAttachmentDraft("message",selected);}
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
 renderSkillArtifact("catalog-skill",catalog?.skill_artifact);
 $("live-setup").hidden=!live;$("fixture-setup").hidden=live;
 $("create").textContent=live?"建立測試對話":"建立合成測試";
 $("create").disabled=creating||!catalog||catalog.source_sync?.current===false||!validExecutionSelections(executionSelections())||(live?((!request.trim()&&!attachmentIds(initialDraft).length)||request.length>8000||attachmentPending(initialDraft)):!$("persona").value);
 for(const key of Object.keys(executionLabels))$(key.replaceAll("_","-")).disabled=creating||!executionOptions(key).length;
 renderAttachmentDraft("initial",INITIAL_DRAFT);
 $("call-limit-note").textContent=(live?"":"包含回答與合成人物。")+"每次呼叫之間檢查上限，可能超出一則；不自動重試。";
 if(!current&&!selected){$("session-label").textContent=modeNames[live?"live":"fixture"];$("title").textContent=live?"寫下需求，開始研究":"挑一個合成人物，開始測試";$("run").hidden=live;$("step").textContent=live?"研究並回覆":"下一步";$("capability-status").textContent=capabilityDefaults[live?"live":"fixture"];$("empty-title").textContent=live?"把選項查清楚，再一起決定":"觀察合成人物的多輪對話";$("empty-note").textContent=live?"從大致需求開始，逐步比較來源、費用與取捨。你可以隨時補充問題或修改條件。":"人物會追問、補充虛構材料，也可能失去耐心。你可以中途插話，觀察 Codex 如何接續。";$("turn-label").textContent=live?"真人輸入":"合成人物回合";}
}
function canPreviewReplay(){return Boolean(current?.id===selected&&isLive(current)&&!current.busy&&!current.pending_call&&catalog&&catalog.source_sync?.current!==false);}
function replaySettings(){return {model:$("replay-model").value,max_calls:Number($("replay-max-calls").value),max_tokens:Number($("replay-max-tokens").value),...executionSelections("replay-")};}
function validReplaySettings(settings){return catalog?.models.includes(settings.model)&&Number.isInteger(settings.max_calls)&&settings.max_calls>=1&&settings.max_calls<=80&&Number.isInteger(settings.max_tokens)&&settings.max_tokens>=10000&&settings.max_tokens<=2000000&&validExecutionSelections(settings);}
function syncReplayControls(){
 $("replay-open").hidden=!isLive(current);$("replay-open").disabled=!canPreviewReplay()||replayCreating||replayLoading;
 const ready=replayPreview?.source_id===selected&&canPreviewReplay()&&!replayLoading&&!replayCreating;
 const stale=ready&&current.revision!==replayPreview.source_revision;
 $("replay-create").disabled=!ready||stale||!replayPreview.turn_count||!validReplaySettings(replaySettings());
 for(const key of ["replay-model","replay-max-calls","replay-max-tokens"])$(key).disabled=!ready;
 for(const key of Object.keys(executionLabels))$("replay-"+key.replaceAll("_","-")).disabled=!ready||!executionOptions(key).length;
 $("replay-reload").disabled=!canPreviewReplay()||replayLoading||replayCreating;$("replay-close").disabled=replayCreating;
 if(stale){$("replay-error").textContent="原對話已更新，請重新預覽後建立重測。";$("replay-error").hidden=false;}
}
function closeReplayPreview(){replayPreviewRequest++;replayLoading=false;replayPreview=null;$("replay-setup").hidden=true;$("replay-preview-turns").replaceChildren();$("replay-error").hidden=true;syncReplayControls();}
function replayInput(text,count){return node("p",text||((count||0)>0?`（僅附件，共 ${count} 份）`:"（空白輸入）"),"replay-input");}
function replayAnswer(label,text,empty){const box=node("section",undefined,"replay-answer");box.append(node("h4",label));box.append(typeof text==="string"&&text?renderReply(text):node("p",empty,"fine"));return box;}
async function openReplayPreview(){
 if(!canPreviewReplay()||replayCreating||replayLoading)return;
 const id=selected,request=++replayPreviewRequest;replayLoading=true;replayPreview=null;$("replay-setup").hidden=false;$("replay-preview-turns").replaceChildren();$("replay-preview-meta").textContent="正在讀取已完成的歷史回合…";$("replay-preview-note").textContent="";$("replay-error").hidden=true;syncReplayControls();
 try{
  const preview=await api(`/api/session/${id}/replay`);if(request!==replayPreviewRequest||selected!==id)return;
  if(preview.source_id!==id||!Array.isArray(preview.turns)||typeof preview.source_sha256!=="string")throw Error("重測預覽不完整，請重新讀取。");
  replayPreview=preview;
  $("replay-model").replaceChildren(...catalog.models.map(model=>{const option=node("option",model);option.value=model;return option;}));
  $("replay-model").value=catalog.models.includes($("model").value)?$("model").value:catalog.models[0];
  $("replay-max-calls").value=$("max-calls").value;$("replay-max-tokens").value=$("max-tokens").value;
  initializeExecutionSelectors("replay-");
  $("replay-preview-meta").textContent=`${preview.turn_count} 輪已完成的輸入與回答 · 原模型 ${preview.model}`+(preview.excluded_pending_count?` · ${preview.excluded_pending_count} 則未完成輸入未納入`:"");
  $("replay-preview-note").textContent=typeof preview.note==="string"?preview.note:"";
  preview.turns.forEach((turn,index)=>{const row=node("details",undefined,"replay-turn");row.append(node("summary",`第 ${index+1} 輪${turn.attachment_count?` · ${turn.attachment_count} 份附件`:""}`),replayInput(turn.user_text,turn.attachment_count),replayAnswer("原回答",turn.original_reply,"尚無原回答紀錄。"));$("replay-preview-turns").append(row);});
 }catch(error){if(request===replayPreviewRequest&&selected===id){$("replay-preview-meta").textContent="未能讀取重測內容。";$("replay-error").textContent=error.message;$("replay-error").hidden=false;}}
 finally{if(request===replayPreviewRequest){replayLoading=false;syncReplayControls();}}
}
async function createReplay(event){
 event.preventDefault();const preview=replayPreview;if(!preview||preview.source_id!==selected||!canPreviewReplay()||replayLoading||replayCreating)return;
 const settings=replaySettings();if(!validReplaySettings(settings)||!preview.turn_count){$("replay-error").textContent="請選擇模型與有效用量上限，並確認有可重測的回合。";$("replay-error").hidden=false;return;}
 if(current.revision!==preview.source_revision){syncReplayControls();return;}
 const data={source_sha256:preview.source_sha256,...settings},fingerprint=JSON.stringify([preview.source_id,data]);let intent=replayIntents.get(fingerprint);
 if(!intent){intent={id:crypto.randomUUID()};replayIntents.set(fingerprint,intent);}replayCreating=true;$("replay-error").hidden=true;syncReplayControls();
 try{
  const result=await api(`/api/session/${preview.source_id}/replay`,{...data,client_id:intent.id});if(!result||typeof result.id!=="string"||!result.id)throw Error("尚未確認建立結果；請以相同設定再試一次。");
  replayIntents.delete(fingerprint);
  if(selected===preview.source_id&&replayPreview===preview)await select(result.id);else{await list();toast("重測已建立，可從已保存的對話開啟。");}
 }catch(error){if(replayPreview===preview){$("replay-error").textContent=error.message;$("replay-error").hidden=false;}else toast(error.message);}
 finally{replayCreating=false;syncReplayControls();}
}
function renderReplay(s){
 syncReplayControls();const panel=$("replay-comparison"),body=$("replay-comparison-body"),replay=s.replay;panel.hidden=!replay;body.replaceChildren();if(!replay)return;
 $("replay-comparison-summary").textContent=`重測對照 · ${replay.completed}/${replay.total} 輪`;
 $("replay-progress").textContent=replay.remaining>0?`已完成 ${replay.completed} 輪，剩下 ${replay.remaining} 輪。`:`${replay.total} 輪重測已完成。`;
 $("replay-context-note").textContent=(replay.modified?"你已加入新訊息；這段重測包含後續修改，繼續歷史回合需按下一輪或連續重測。":"使用固定歷史輸入重測；這些輸入不是對新回答的即時反饋。")+" 原回答僅供對照，不會交給新模型；公開資料可能已改變。";
 $("replay-origin").disabled=!replay.source_id;$("replay-origin").onclick=()=>select(replay.source_id);
 $("step").textContent=replay.remaining>0?"重測下一輪":"研究並回覆";$("run").hidden=false;$("run").textContent="連續重測";
 $("turn-label").textContent="已重測回合";$("turn").textContent=`${replay.completed}/${replay.total}`;
 $("queue-note").textContent="可補充新問題；送出會標記此輪重測已修改，並暫停後續歷史回合。";
 for(const [position,turn] of (s.replay_comparison||[]).entries()){
  const key=`${s.id}:${turn.index??position}`,row=node("details",undefined,"replay-turn"),answers=node("div",undefined,"replay-answers");
  const status=typeof turn.new_reply==="string"&&turn.new_reply?"已回覆":({running:"進行中",pending:"等待重測",error:"未完成",failed:"未完成",interrupted:"待恢復"}[turn.status]||"等待重測");
  row.open=replayComparisonOpen.get(key)||false;row.ontoggle=()=>replayComparisonOpen.set(key,row.open);
  row.append(node("summary",`第 ${position+1} 輪 · ${status}`),replayInput(turn.user_text,turn.attachment_count));
  answers.append(replayAnswer("原回答",turn.original_reply,"尚無原回答紀錄。"),replayAnswer("本次回答",turn.new_reply,status));row.append(answers);body.append(row);
 }
}
function statusLabel(s){if(s.replay&&["ready","paused","ended"].includes(s.status))return s.replay.remaining>0?"等待重測":"重測已完成";return isLive(s)&&s.status==="paused"?(s.next_actor||s.pending_count?"等待研究":"等待你的回覆"):statuses[s.status]||s.status;}
function currentChecks(s){
 const panel=$("current-checks"), body=$("current-checks-body"), a=s.current_comparison;
 if(!panel||!body)return;
 panel.hidden=!isLive(s)||s.comparison_status!=="current"||!a;body.replaceChildren();if(panel.hidden)return;
 body.append(node("p","比較、排序及待辦依照已保存需求重新核對；廣告中的資訊仍需要查證。","fine"));
 if(a.presentation?.conditions?.length){body.append(node("h3","目前採用的條件"));const list=node("ul");for(const text of a.presentation.conditions)list.append(node("li",text));body.append(list);}
 const inputs=node("details"), requestList=node("ol");inputs.append(node("summary","已保存的需求與追問"));
 for(const text of Object.values(a.constraints.user_requests))requestList.append(node("li",text));inputs.append(requestList);body.append(inputs);
 if(a.normalization.unresolved_intent.length){body.append(node("h3","尚待釐清的原話"));const list=node("ul");for(const text of a.normalization.unresolved_intent)list.append(node("li",text));body.append(list);}
 if(a.presentation?.todos?.length){body.append(node("h3","目前待辦"));const list=node("ul");for(const text of a.presentation.todos)list.append(node("li",text));body.append(list);}
}
async function list(){const rows=await api("/api/sessions");$("sessions").replaceChildren();for(const s of rows.sessions){const b=node("button",s.name,"session-card"+(s.id===selected?" active":""));b.append(node("small",`${isLive(s)?"真實研究":"合成測試"} · ${statusLabel(s)} · ${s.calls} calls · ${s.tokens===null?"用量未知":s.tokens.toLocaleString()+" tokens"}`));b.onclick=()=>select(s.id);$("sessions").append(b);}}
async function select(id){saveComposerDraft();selected=id;lastRevision=null;current=null;$("session-execution").hidden=true;$("session-execution").textContent="";$("session-execution").title="";$("session-skill").hidden=true;$("session-skill-label").textContent="";$("session-skill-label").title="";$("session-skill-detail").replaceChildren();closeReplayPreview();$("replay-comparison").hidden=true;$("replay-comparison").open=false;$("replay-comparison-body").replaceChildren();restoreComposerDraft();syncComposer();$("title").textContent="正在讀取這段對話…";$("messages").replaceChildren();if($("current-checks"))$("current-checks").hidden=true;if($("current-checks-body"))$("current-checks-body").replaceChildren();for(const key of ["step","run","pause","send","message","amendment","export"])$(key).disabled=true;try{localStorage.setItem("pea-lab-session",id);}catch(_){}await refresh();await list();}
function render(s){current=s;renderSessionExecution(s.execution_settings);$("session-skill").hidden=false;renderSkillArtifact("session-skill",s.skill_artifact);globalThis.PeaReview?.sessionUpdated(s);currentChecks(s);const live=isLive(s);$("title").textContent=s.name;$("session-label").textContent=live?`${s.output_mode==="agent"?"Agent 對話測試":"真實找房研究"} · ${s.model}`:`合成人物測試 · 虛構資料 · ${s.persona_id} · ${s.model}`;$("status").textContent=statusLabel(s);$("phase").textContent=s.phase_label||"";$("turn-label").textContent=live?"真人輸入":"合成人物回合";$("turn").textContent=live?String(s.persona_turn):`${s.persona_turn}/${s.patience_turns}`;$("calls").textContent=`${s.calls}/${s.limits.max_calls}`;const knownTokens=Number.isFinite(s.tokens);$("tokens").textContent=knownTokens?s.tokens.toLocaleString():(s.busy||s.pending_call?"計算中":"用量未知");$("usage-bar").hidden=!knownTokens;$("usage-bar").style.width=knownTokens?`${Math.max(0,Math.min(100,100*s.tokens/s.limits.max_tokens))}%`:"";$("usage-note").textContent=`上限 ${s.limits.max_tokens.toLocaleString()} · 回答 ${s.actor_calls.assistant} 次`+(live?"":`／合成人物 ${s.actor_calls.persona} 次`);
 const capNotice=limitNotice(s);$("step").textContent=live?"研究並回覆":"下一步";$("step").disabled=!canAdvance(s,"step");$("run").hidden=live;$("run").textContent="連續對話";$("run").disabled=!canAdvance(s,"run");$("pause").disabled=!s.busy&&!s.auto;$("export").disabled=false;$("recover").hidden=!(s.pending_call&&!s.busy);$("message-label").textContent=live?"繼續討論":"加入這段對話";$("amendment-label").hidden=live;$("send").textContent=live?"送出並研究 ↑":"插入問題 ↑";syncComposer();$("banner").hidden=!(capNotice||s.notice);$("banner").textContent=[capNotice,s.notice].filter(Boolean).join("\n");$("queue-note").textContent=live?(s.pending_count?`${s.pending_count} 則問題已保存，會依序研究並回覆。`:"送出後繼續研究；研究途中也能補充需求。"):(s.pending_count?`${s.pending_count} 則插話已保存，將於目前這則完成後優先回答。`:"插話會保存，於目前這則完成後優先回答。");
 $("capability-status").textContent=typeof s.capability_status==="string"&&s.capability_status?s.capability_status:capabilityDefaults[live?"live":"fixture"];
 $("fixture-observations").hidden=live;$("criteria").replaceChildren(...s.criteria.map(x=>node("li",x)));$("behavior-title").textContent=live?"研究進度":"行為與補件";
 if(live){$("behavior").replaceChildren(node("p",capNotice?"已達用量上限，可閱讀與匯出已保存的內容。":s.compatible===false?"這段紀錄目前只能閱讀與匯出。":["error","interrupted","budget"].includes(s.status)?"研究尚未完成，請查看上方狀態。":s.busy?"正在研究你的問題。":s.next_actor||s.pending_count?"需求已保存，可以開始研究。":"回答已保存，等你補充問題或調整條件。"));}
 else{$("behavior").replaceChildren(node("p",`情緒：${s.mood} · 尚可 ${Math.max(0,s.patience_turns-s.persona_turn)} 回合`),node("p",`合成人物持有 ${s.held_documents.length} 份文件`));for(const e of s.events.slice(-7))$("behavior").append(node("div",`第 ${e[0]} 回合 · ${e[1]}`,"event"));}
 $("mode-limit-note").textContent=live?(s.output_mode==="agent"?"這裡顯示模型原始回答供測試；不代表已通過房源條件核對。完整輸入、回答、工具紀錄與用量保存在本機。":"研究結果應附來源連結與查詢時間，並區分刊登資訊、推估及尚未確認的可租狀態。"):"合成人物的後續訊息由 Codex 產生，使用分開的歷史。測試僅使用所提供的虛構材料，沒有即時查詢；不代表真實在租房源。";
 const box=$("messages"), nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<180;box.replaceChildren();s.messages.forEach((m,index)=>{const article=node("article",undefined,`message ${m.role}`);article.append(node("div",m.role==="assistant"?"Codex":m.role==="human"?(live?"你":m.kind==="amendment"?"你 · 情境變更":"你 · 插話"):m.role==="persona"?`${s.name} · 合成人物`:"紀錄","speaker"));if(m.pending)article.firstChild.append(node("small","已保存・排隊中"));if(m.comparison_status==="historical")article.append(node("small","先前的比較；目前條件或來源已更新。","fine"));article.append(renderReply(m.display_text??m.text));if(Array.isArray(m.attachments)&&m.attachments.length)article.append(renderMessageAttachments(m.attachments));if(m.questions?.length)article.append(clarificationForm(s,m,index));box.append(article);});if(s.busy){const pending=node("article",undefined,"message system");pending.append(node("div",s.phase_label+"…","bubble"));box.append(pending);}if(nearBottom||lastRevision===null)box.scrollTop=box.scrollHeight;
 renderReplay(s);
}
async function refresh(){if(!selected||polling)return;polling=true;try{const requestedId=selected;const s=await api(`/api/session/${requestedId}`);if(selected!==requestedId)return;if(s.revision!==lastRevision||s.compatible!==current?.compatible||s.comparison_status!==current?.comparison_status||s.notice!==current?.notice){render(s);lastRevision=s.revision;}}catch(e){toast(e.message);}finally{polling=false;}}
async function action(action){if(["step","run"].includes(action)&&!canAdvance(current,action)){if(limitNotice(current))toast(limitNotice(current));return;}try{const id=selected,fingerprint=JSON.stringify([id,action]);if(!actionIntent||actionIntent.fingerprint!==fingerprint)actionIntent={fingerprint,id:crypto.randomUUID()};const intent=actionIntent;await api(`/api/session/${id}/control`,{action,client_id:intent.id});if(actionIntent===intent)actionIntent=null;await refresh();await list();}catch(e){toast(e.message);}}
$("persona").onchange=()=>{profile();resetCreationDepth();creationMode();};$("research-mode").onchange=()=>{resetCreationDepth();creationMode();};$("research-depth").onchange=creationMode;$("reasoning-effort").onchange=creationMode;$("initial-request").oninput=creationMode;$("refresh").onclick=()=>list().catch(e=>toast(e.message));$("step").onclick=()=>action("step");$("run").onclick=()=>action("run");$("pause").onclick=()=>action("pause");$("recover").onclick=()=>action("recover");
$("replay-open").onclick=openReplayPreview;$("replay-reload").onclick=openReplayPreview;$("replay-close").onclick=()=>{if(!replayCreating)closeReplayPreview();};$("replay-form").onsubmit=createReplay;
for(const key of ["replay-model","replay-max-calls","replay-max-tokens","replay-research-depth","replay-reasoning-effort"]){$(key).oninput=syncReplayControls;$(key).onchange=syncReplayControls;}
wireAttachments("initial","live-setup");wireAttachments("message","composer");
$("message").oninput=saveComposerDraft;$("amendment").onchange=saveComposerDraft;
$("create").onclick=async()=>{
 if(creating||!catalog)return;if(!validExecutionSelections(executionSelections())){toast("請選擇可用的研究深度與模型思考強度。");return;}const research_mode=$("research-mode").value,live=research_mode==="live",initial_request=$("initial-request").value,attachments=live?attachmentIds(initialDraft):[];
 if(live&&((!initial_request.trim()&&!attachments.length)||initial_request.length>8000)){toast("請寫下找房需求或加入檔案，文字最多 8,000 字。");return;}
 if(live&&attachmentPending(initialDraft)){toast("請等檔案加入完成，或移除未成功的檔案。");return;}
 creating=true;creationMode();try{
  const settings={research_mode,...executionSelections(),...(live?{initial_request,output_mode:"agent",attachments}:{persona_id:$("persona").value}),model:$("model").value,max_calls:Number($("max-calls").value),max_tokens:Number($("max-tokens").value),seed:1};
  const fingerprint=JSON.stringify(settings);if(!createIntent||createIntent.fingerprint!==fingerprint)createIntent={fingerprint,id:crypto.randomUUID()};
  const s=await api("/api/sessions",{...settings,client_id:createIntent.id});createIntent=null;initialDraft.attachments=initialDraft.attachments.filter(item=>!attachments.includes(item.meta?.id));await select(s.id);
 }catch(e){toast(e.message);}finally{creating=false;creationMode();}
};
$("composer").onsubmit=async e=>{
 e.preventDefault();const text=$("message").value,id=selected;if(!canCompose(current)||messageSending.has(id))return;
 saveComposerDraft();const draft=attachmentDraft(id),attachments=acceptsAttachments(current)?attachmentIds(draft):[];
 if((!text.trim()&&!attachments.length)||attachmentPending(draft))return;
 const kind=!isLive(current)&&$("amendment").checked?"amendment":"question";messageSending.add(id);syncComposer();try{
  const fingerprint=JSON.stringify([id,text,kind,attachments]);let intent=messageIntents.get(id);if(!intent||intent.fingerprint!==fingerprint){intent={fingerprint,id:crypto.randomUUID()};messageIntents.set(id,intent);}
  await api(`/api/session/${id}/message`,{text,kind,attachments,client_id:intent.id});if(messageIntents.get(id)===intent)messageIntents.delete(id);
  draft.attachments=draft.attachments.filter(item=>!attachments.includes(item.meta?.id));if(draft.text===text){draft.text="";draft.amendment=false;}
  if(selected===id&&$("message").value===text){$("message").value="";$("amendment").checked=false;}await refresh();
 }catch(err){toast(err.message);}finally{messageSending.delete(id);syncComposer();}
};
$("export").onclick=async()=>{try{const s=await api(`/api/session/${selected}/export`);const url=URL.createObjectURL(new Blob([JSON.stringify(s,null,2)],{type:"application/json"}));const a=node("a");a.href=url;a.download=isLive(s)?`PRIVATE-research-${s.id.slice(0,8)}.json`:`PRIVATE-persona-${s.persona_id}-${s.id.slice(0,8)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(e.message);}};
async function start(){try{catalog=await api("/api/catalog");const modes=["live","fixture"].filter(mode=>(catalog.research_modes||["fixture"]).includes(mode));$("research-mode").replaceChildren(...modes.map(mode=>{const o=node("option",modeNames[mode]);o.value=mode;return o;}));$("research-mode").value=modes[0]||"fixture";$("persona").replaceChildren(...catalog.personas.map(p=>{const o=node("option",`${p.id} · ${p.name}`);o.value=p.id;return o;}));$("model").replaceChildren(...catalog.models.map(m=>{const o=node("option",m);o.value=m;return o;}));initializeExecutionSelectors();resetCreationDepth();profile();creationMode();renderSourceSync();booted=true;$("connection").textContent="本機研究介面已連接";await list();let previous=null;try{previous=localStorage.getItem("pea-lab-session");}catch(_){}if(previous)await select(previous);}catch(e){$("connection").textContent="連線未就緒";toast(e.message);}}
start();
setInterval(()=>{if(booted)refresh();},1200);
setInterval(refreshCatalog,3000);
