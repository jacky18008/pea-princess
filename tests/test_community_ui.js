'use strict';
// Execute the actual DOM handlers with isolated in-memory browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ui = require('../community/form.js');
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../community/catalog.json')));
const schema = JSON.parse(fs.readFileSync(path.join(__dirname, '../community/public-schema.json')));
const SECRET = 'PRIVATE-NOTE-</script>-address-bank-password';
const now = new Date('2026-09-09T00:00:00Z');
class Element {
  constructor(tag='div') { this.tagName=tag; this.value=''; this.checked=false; this.children=[]; this.textContent=''; this.events={}; }
  appendChild(child) { this.children.push(child); }
  addEventListener(name, handler) { this.events[name]=handler; }
  focus() {}
  select() {}
  async fire(name) { if (this.events[name]) await this.events[name]({preventDefault(){}}); }
}
function setup(storageOverride) {
  const elements = {};
  ['choice-fields','catalog-state','public-status','private-status','download-public','public-preview',
   'consent','public-form','private-note','save-note','copy-note','download-note','delete-note'].forEach(id => elements[id]=new Element());
  const doc = {getElementById: id => elements[id], createElement: tag => new Element(tag)};
  const saved = new Map();
  const storage = storageOverride || {getItem:k=>saved.has(k)?saved.get(k):null, setItem:(k,v)=>saved.set(k,v), removeItem:k=>saved.delete(k)};
  const downloads=[], copies=[];
  const mounted = ui.mount(doc,{schema,catalog,storage,now:()=>now,
    download:(name,text,mime)=>downloads.push({name,text,mime}),copy:async text=>copies.push(text)});
  return {elements, saved, downloads, copies, mounted, storage};
}
const value = {schema_version:1,place_id:'demo-orchid-court',experience_month:'2026-08',experience_kind:'lived',
 cleanliness:'good',noise:'good',transport:'good',facilities:'good',maintenance:'good',overall:'would_return',consent:true,license:'CC0-1.0'};
async function main() {
  assert.deepEqual(ui.validatePublic(value,schema,catalog,now),value);
  for (const bad of [{...value,note:SECRET},{...value,place_id:SECRET},{...value,consent:false},
                      {...value,experience_month:'2026-09'},{...value,schema_version:true},
                      {...value,noise:SECRET},{...value,license:'MIT'}]) {
    assert.throws(()=>ui.publicJSON(bad,schema,catalog,now),error=>!error.message.includes(SECRET));
  }
  assert.equal(ui.completedMonths(new Date('2026-01-01T00:00:00Z'))[0],'2025-12');
  const app=setup(), e=app.elements;
  Object.entries(app.mounted.controls).forEach(([key,element])=>element.value=value[key]);
  e['private-note'].value=SECRET;
  await e['save-note'].fire('click');
  assert.equal(app.saved.get(ui.NOTE_KEY),SECRET);
  e.consent.checked=true;
  await e['public-form'].fire('submit');
  assert.equal(e['download-public'].disabled,false);
  assert.deepEqual(JSON.parse(e['public-preview'].textContent),value);
  assert(!e['public-preview'].textContent.includes(SECRET));
  await e['download-public'].fire('click');
  assert.equal(app.downloads.length,1);
  assert.deepEqual(JSON.parse(app.downloads[0].text),value);
  assert(!JSON.stringify(app.downloads).includes(SECRET));
  // A synthetic field edit without a change event still cannot download unreviewed content.
  app.mounted.controls.noise.value='mixed';
  await e['download-public'].fire('click');
  assert.equal(app.downloads.length,1);
  assert.equal(e['download-public'].disabled,true);
  await e['public-form'].fire('submit');
  await e['copy-note'].fire('click');
  await e['download-note'].fire('click');
  assert.equal(app.copies[0],SECRET);
  assert.equal(app.downloads[1].name,'PRIVATE-community-note.txt');
  assert.equal(app.downloads[1].text,SECRET);
  for (const id of ['public-status','private-status','public-preview']) assert(!e[id].textContent.includes(SECRET));
  await e['delete-note'].fire('click');
  assert.equal(e['private-note'].value,'');
  assert.equal(app.saved.has(ui.NOTE_KEY),false);
  const broken=setup({getItem(){throw Error(SECRET)},setItem(){throw Error(SECRET)},removeItem(){throw Error(SECRET)}});
  broken.elements['private-note'].value=SECRET;
  for (const id of ['save-note','delete-note']) await broken.elements[id].fire('click');
  assert(!broken.elements['private-status'].textContent.includes(SECRET));
  assert(!broken.elements['private-status'].textContent.includes('已存到'));
  assert.throws(()=>ui.saveNote(app.storage,'x'.repeat(ui.NOTE_LIMIT+1)));
  const hostile=JSON.parse(JSON.stringify(catalog));
  hostile.places[0].name='<img src=x onerror=alert(1)>';
  const html=fs.readFileSync(path.join(__dirname,'../community/index.html'),'utf8');
  assert(!/\b(?:fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(/.test(fs.readFileSync(path.join(__dirname,'../community/form.js'),'utf8')));
  assert(html.includes("connect-src 'none'"));
  assert(html.includes('没有')===false);
  console.log('community DOM/privacy functional checks passed');
}
main().catch(()=>{console.error('community UI functional checks failed');process.exitCode=1;});
