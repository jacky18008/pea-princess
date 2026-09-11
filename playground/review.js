/* Inspection reads saved evidence; it never dispatches or changes a model run. */
(() => {
 'use strict';
 const el=id=>document.getElementById(id);
 const tags={missed_question:'沒有回答當下問題',condition_loss:'條件遺失或漂移',unsupported_claim:'說法缺乏證據',process_jargon:'內部術語干擾',no_progress:'沒有推進',tool_failure:'工具失敗',cost:'用量或重複工作'};
 const ratings={helpful:'有幫助',needs_work:'可以改善',problem:'有明顯問題',unrated:'未評分'};
 const numbers=v=>Number.isFinite(v)?v.toLocaleString(undefined,{maximumFractionDigits:2}):'未記錄';
 let sid=null,callId=null,index=null,detail=null,reviews=[],generation=0,visible=false,saving=false;
 const drafts=new Map(), intents=new Map();
 const key=()=>`${sid}:${callId}`;
 function total(v){return v?.value===null?`${numbers(v.known_sum)} 已知 · ${v.unknown_calls} 次未記錄`:numbers(v?.value);}
 function card(title){const c=node('section',undefined,'review-card');c.append(node('h3',title));return c;}
 function disclosure(title,block){
  const d=node('details',undefined,'review-disclosure');d.append(node('summary',title));
  d.append(node('pre',block?.sha256?block.text:'未記錄'));
  d.append(node('p',`${block?.truncated?'顯示前段；完整內容共 '+numbers(block.total_chars)+' 字。 ':''}${block?.source_path||''}`, 'fine'));
  if(block?.sha256)d.append(node('code',`SHA-256 ${block.sha256}`));return d;
 }
 function attachmentList(receipt){
  const section=node('div',undefined,'review-attachments');section.append(node('h4',receipt?.status==='message_metadata'?'訊息附件':'附件收據'));
  const status=receipt?.status;
  section.append(node('p',status==='message_metadata'?'這則訊息保存的附件資料；不代表某次模型呼叫已收到或讀取。':status==='bound'?'以下附件資料已綁定這次保存的請求；不代表模型已讀取或內容已核實。':status==='not_recorded'?'這份舊請求沒有附件欄位；不能推定當時未提供其他材料。':'附件收據缺少有效的請求關聯，不能當成已送交或已讀的證據。','fine'));
  const list=node('ul');for(const file of receipt?.items||[]){
   const row=node('li');row.append(node('strong',file.name),node('span',` · ${numbers(file.bytes)} bytes · ${file.source_kind||'使用者提供'}`),node('code',`ID ${file.id}`));
   if(status!=='message_metadata')row.append(node('span',file.image?' · 本次標記為圖片輸入':' · 供應材料紀錄（未標記為本次圖片輸入）'));
   row.append(node('p',file.path,'fine'),node('code',`SHA-256 ${file.sha256}`));
   if(file.original_path)row.append(node('p','原始路徑：'+file.original_path,'fine'));
   if(file.mime_type)row.append(node('p',file.mime_type,'fine'));list.append(row);
  }section.append(list);return section;
 }
 function stash(){if(!sid||!callId)return;drafts.set(key(),{rating:el('review-rating').value,severity:el('review-severity').value,note:el('review-note').value,tags:[...el('review-tags').querySelectorAll('input:checked')].map(x=>x.value)});}
 function restore(){const d=drafts.get(key())||{rating:'unrated',severity:'none',note:'',tags:[]};el('review-rating').value=d.rating;el('review-severity').value=d.severity;el('review-note').value=d.note;for(const x of el('review-tags').querySelectorAll('input'))x.checked=d.tags.includes(x.value);}
 function renderNotes(){
  const box=el('review-history');box.replaceChildren();for(const r of reviews.filter(r=>r.call_id===callId)){
   const c=card(`${r.reviewer==='agent'?'標記為 Agent':'標記為人類'} · ${ratings[r.rating]||r.rating}`);
   c.append(node('p',r.note||'僅標記分類'),node('p',`${r.created_at} · ${r.severity} · ${(r.tags||[]).map(x=>tags[x]||x).join('、')}`,'fine'));
   const source=node('details');source.append(node('summary','意見所對應的原始紀錄與畫面快照'),node('pre',JSON.stringify({source:r.source,displayed_snapshot:r.displayed_snapshot??null},null,2)));c.append(source);box.append(c);
  }
 }
 function renderCalls(){
  const box=el('review-calls');box.replaceChildren();for(const c of index?.calls||[]){
   const b=node('button',`${c.call_id} · ${c.actor==='persona'?'合成人物':'回答者'}`,'session-card'+(c.call_id===callId?' active':''));
   b.append(node('small',`${c.status} · ${numbers(c.usage?.processed_tokens)} tokens`),node('small',`${numbers(c.tool_invocation_count)} 個工具執行${c.integrity.ok?'':' · 紀錄缺口'}`));
   b.onclick=()=>loadCall(c.call_id);box.append(b);
  }if(!index?.calls.length)box.append(node('p','還沒有模型呼叫紀錄。','fine'));
 }
 function renderDetail(d){
  const box=el('review-detail');box.replaceChildren();
  const head=card('01 · 使用者看到的回覆');
  const displayed=d.displayed_reply;
  if(d.displayed_reply_relation)head.append(node('p','畫面關聯：'+d.displayed_reply_relation,'fine'));
  if(displayed?.sha256){head.append(renderReply(displayed.text));if(displayed.truncated)head.append(node('p','回覆過長，這裡僅顯示前段；完整內容請查保存檔。','fine'));}
  else{head.append(node('p','無法確定這次呼叫對應哪則畫面回覆；下方保留模型原始輸出。','review-notice'));head.append(disclosure('模型原始回覆',d.raw_actor_reply||d.reply));}
  if(d.displayed_questions?.status!=='present')head.append(node('p','選項未完整記錄，不能推定當時沒有提問。','fine'));
  for(const q of d.displayed_questions?.items||[]){const choices=node('div',undefined,'review-choices');choices.append(node('strong',q.question));const list=node('ul');for(const option of q.options||[])list.append(node('li',option));choices.append(list);head.append(choices);}
  head.append(node('p',`執行狀態：${d.status} · 品質尚未自動驗收。工具完成不代表來源說法已核實。`,'fine'));
  if(d.integrity.gaps.length)head.append(node('pre',d.integrity.gaps.join('\n')));
  box.append(head);
  const usage=card('02 · 這次呼叫的用量');const grid=node('div',undefined,'review-totals');
  for(const [k,label] of [['input_tokens','輸入（含快取）'],['cached_input_tokens','其中快取輸入'],['uncached_input_tokens','非快取輸入'],['output_tokens','輸出'],['processed_tokens','合計 tokens'],['seconds','耗時（秒）']]){const cell=node('div');cell.append(node('strong',numbers(d.usage[k])),node('small',label));grid.append(cell);}usage.append(grid,node('p','合計＝輸入＋輸出，快取不重複加計。這是 provider 回報的 token 用量，並非帳單金額。','fine'));box.append(usage);
  const inputs=card('03 · 輸入與送給模型的內容');inputs.append(disclosure('這次要回答的輸入',d.current_input),disclosure('實際完整提示內容（含注入的條件與歷史）',d.prompt),attachmentList(d.input_files));box.append(inputs);
  const tools=card('04 · 工具與研究過程');
  tools.append(node('p',d.tool_invocation_count===null?'工具紀錄未取得；不能推定沒有使用工具。':d.tool_invocation_count===0?'已保存紀錄中沒有工具執行。':`${d.tool_invocation_count} 次工具執行；${d.tool_failed_count} 次失敗。同一工具的開始與完成事件只計一次。`,'fine'));
  for(const t of d.tools||[]){const c=node('details',undefined,'review-tool');c.append(node('summary',`${t.id} · ${t.type} · ${t.status}`),disclosure('工具輸入',t.input),disclosure('工具輸出',t.output),disclosure('原始工具事件內容',t.raw));tools.append(c);}if(d.tools_truncated)tools.append(node('p','工具清單超過顯示上限，請查原始保存檔。','review-notice'));tools.append(disclosure('保存的工具事件（不含隱藏推理）',d.raw_tool_events));box.append(tools);
  const provenance=card('05 · 模型原始輸出與版本依據');provenance.append(disclosure('後處理前的模型輸出',d.raw_actor_reply||d.reply));
  const raw=node('details');raw.append(node('summary','呼叫來源、關聯方式與版本雜湊'),node('pre',JSON.stringify({source:d.source,displayed_reply_relation:d.displayed_reply_relation,session:d.session},null,2)));provenance.append(raw);box.append(provenance);
  el('review-save').disabled=saving||!(d.source?.record_sha256||d.source?.message_sha256);el('review-json').disabled=false;el('review-md').disabled=false;
 }
 async function loadCall(id){
  stash();const request=++generation;callId=id;detail=null;restore();renderCalls();renderNotes();el('review-save').disabled=true;el('review-json').disabled=true;el('review-md').disabled=true;el('review-detail').replaceChildren(node('p','讀取這次呼叫的保存紀錄…','fine'));
  try{const d=await api(`/api/session/${sid}/inspect/${id}`);if(request!==generation)return;detail=d;renderDetail(d);location.hash=`review/${sid}/${id}`;}catch(e){if(request===generation)el('review-detail').replaceChildren(node('p',e.message,'review-notice'));}
 }
 async function loadSession(id,preferred){
  stash();const request=++generation;sid=id;callId=null;index=null;detail=null;reviews=[];restore();el('review-export-result').replaceChildren();el('review-conversation').open=false;el('review-conversation-body').replaceChildren();el('review-save').disabled=true;el('review-json').disabled=true;el('review-md').disabled=true;el('review-detail').replaceChildren();el('review-calls').replaceChildren();el('review-totals').replaceChildren();el('review-history').replaceChildren();el('review-notice').textContent='讀取已保存的呼叫；執行中的工具要等該次呼叫完成才會出現。';
  try{const [data,notes]=await Promise.all([api(`/api/session/${id}/inspect`),api(`/api/session/${id}/reviews`)]);if(request!==generation)return;index=data;reviews=notes.reviews;el('review-session').value=id;
   el('review-title').textContent=data.session.name||id;el('review-meta').textContent=`${data.session.model||'模型未記錄'} · 設定思考強度 ${data.session.configured_effort||data.session.effort} · ${data.session.output_mode||data.session.research_mode} · ${data.session.created_at?new Date(data.session.created_at*1000).toLocaleString():'時間未記錄'} · ${id}`;
   const totals=el('review-totals');for(const [k,label] of [['processed_tokens','整段合計 tokens'],['cached_input_tokens','其中快取輸入'],['tool_invocation_count','工具執行'],['seconds','累計耗時（秒）']]){const cell=node('div');cell.append(node('strong',total(data.totals[k])),node('small',label));totals.append(cell);}
   el('review-notice').textContent=`這是保存當時的版本；查看不會重跑模型。${data.gaps.length?'部分呼叫的紀錄有缺口，請逐次查看。':''}${notes.gaps.length?'評閱筆記有完整性缺口：'+notes.gaps.join('；'):''}`;
   renderCalls();const chosen=data.calls.find(c=>c.call_id===preferred)||data.calls[data.calls.length-1];if(chosen)await loadCall(chosen.call_id);
  }catch(e){if(request===generation)el('review-notice').textContent=e.message;}
 }
 async function open(){
  visible=true;el('chat-view').hidden=true;el('review-view').hidden=false;el('show-chat').setAttribute('aria-pressed','false');el('show-review').setAttribute('aria-pressed','true');
  try{const data=await api('/api/sessions');el('review-session').replaceChildren(...data.sessions.map(s=>{const o=node('option',`${s.name} · ${s.id.slice(0,8)}`);o.value=s.id;return o;}));
   const match=location.hash.match(/^#review\/([a-f0-9]{32})(?:\/([A-Za-z0-9_-]+))?$/);const preferred=match?.[1]||sid||(typeof selected==='string'?selected:null);const id=data.sessions.find(s=>s.id===preferred)?.id||data.sessions[0]?.id;if(id)await loadSession(id,match?.[2]||callId);else el('review-notice').textContent='先建立對話並完成一次回答，再來檢閱。';
  }catch(e){el('review-notice').textContent=e.message;}
 }
 async function download(kind){const requested=sid,d=detail;if(!d)return;el('review-json').disabled=true;el('review-md').disabled=true;try{const receipt=await api(`/api/session/${requested}/review-export`,{call_id:d.call_id,format:kind,expected_source:Object.fromEntries(['record_sha256','message_sha256','displayed_sha256'].map(k=>[k,d.source[k]??null]))});el('review-export-result').replaceChildren(node('span','已保存私人檢閱包：'),node('code',receipt.path),node('span',` (${numbers(receipt.bytes)} bytes)`));toast('檢閱包已保存到本機；可將顯示的路徑交給 review agent。');}catch(e){toast(e.message);}finally{el('review-json').disabled=!detail;el('review-md').disabled=!detail;}}
 for(const [value,label] of Object.entries(tags)){const row=node('label'),input=node('input');input.type='checkbox';input.value=value;row.append(input,node('span',label));el('review-tags').append(row);}
 el('review-form').onsubmit=async event=>{event.preventDefault();if(!detail||saving)return;stash();const savedKey=key(),savedSid=sid,payload={...drafts.get(savedKey),call_id:callId,reviewer:'human',expected_source:Object.fromEntries(['record_sha256','message_sha256','displayed_sha256'].map(k=>[k,detail.source[k]??null]))};const fingerprint=JSON.stringify(payload);let intent=intents.get(savedKey);if(!intent||intent.fingerprint!==fingerprint){intent={fingerprint,id:crypto.randomUUID()};intents.set(savedKey,intent);}saving=true;el('review-save').disabled=true;
  try{await api(`/api/session/${savedSid}/reviews`,{...payload,client_id:intent.id});intents.delete(savedKey);drafts.delete(savedKey);const notes=await api(`/api/session/${savedSid}/reviews`);if(sid===savedSid){reviews=notes.reviews;renderNotes();if(key()===savedKey)restore();}toast('評閱已保存，原始對話沒有變更。');}catch(e){toast(e.message);}finally{saving=false;el('review-save').disabled=!detail||!(detail.source?.record_sha256||detail.source?.message_sha256);}
 };
 el('review-conversation').ontoggle=async()=>{if(!el('review-conversation').open||!sid)return;const requested=sid,request=generation;el('review-conversation-body').replaceChildren(node('p','讀取完整對話…','fine'));try{const packet=await api(`/api/session/${requested}/review-packet`);if(request!==generation||requested!==sid)return;const body=el('review-conversation-body');body.replaceChildren();for(const m of packet.messages){const c=card(m.role==='human'?'使用者':m.role==='persona'?'合成人物':m.role==='assistant'?'回答者':'紀錄');c.append(renderReply(m.display_text??m.text));if(m.attachments?.length)c.append(attachmentList({status:'message_metadata',items:m.attachments}));for(const q of m.questions||[]){c.append(node('p',q.question));const list=node('ul');for(const option of q.options||[])list.append(node('li',option));c.append(list);}body.append(c);}}catch(e){if(request===generation)el('review-conversation-body').replaceChildren(node('p',e.message));}};
 el('show-review').onclick=open;el('show-chat').onclick=()=>{stash();visible=false;el('chat-view').hidden=false;el('review-view').hidden=true;el('show-chat').setAttribute('aria-pressed','true');el('show-review').setAttribute('aria-pressed','false');if(location.hash.startsWith('#review/'))history.replaceState(null,'',location.pathname);};
 el('review-session').onchange=()=>loadSession(el('review-session').value);el('review-refresh').onclick=()=>sid?loadSession(sid,callId):open();el('review-json').onclick=()=>download('json');el('review-md').onclick=()=>download('md');
 window.PeaReview={sessionUpdated(s){if(visible&&s.id===sid)el('review-notice').textContent=s.busy?'模型執行中。完成後按「重新讀取紀錄」查看工具與用量。':'查看的是已保存快照；可按「重新讀取紀錄」取得最新內容。';}};
 if(location.hash.startsWith('#review/'))open();
})();
