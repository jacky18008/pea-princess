/* Public choices and private device notes are separate data flows. No transport. */
(function (root) {
  'use strict';
  const NOTE_KEY = 'pea-princess:private-note:v1';
  const NOTE_LIMIT = 8000;
  const LABELS = {
    lived: '親身入住', visited: '親自到訪', hearsay: '轉述', undisclosed: '不願透露',
    very_bad: '很差', bad: '偏差', mixed: '好壞參半', good: '不錯', very_good: '很好',
    unknown: '不知道', not_applicable: '不適用', would_return: '願意再次入住',
    would_not_return: '不願再次入住', unsure: '還不確定'
  };
  const FIELD_LABELS = {
    place_id: '場所', experience_month: '經驗月份', experience_kind: '經驗性質',
    cleanliness: '清潔', noise: '安靜程度', transport: '交通便利',
    facilities: '設備', maintenance: '維修服務', overall: '整體感受'
  };
  function completedMonths(now) {
    const date = now || new Date();
    const current = date.getUTCFullYear() * 12 + date.getUTCMonth();
    return Array.from({length: 60}, (_, index) => {
      const value = current - index - 1;
      return String(Math.floor(value / 12)).padStart(4, '0') + '-' + String(value % 12 + 1).padStart(2, '0');
    });
  }
  function validatePublic(value, schema, catalog, now) {
    if (!value || typeof value !== 'object' || Array.isArray(value) ||
        Object.keys(value).length !== schema.required.length ||
        Object.keys(value).some(key => !schema.required.includes(key))) {
      throw new Error('invalid_public_fields');
    }
    const clean = {};
    schema.required.forEach(key => {
      const spec = schema.properties[key];
      const item = value[key];
      const validType = spec.type === 'integer' ? Number.isInteger(item) : typeof item === spec.type;
      if (!validType || (Object.hasOwn(spec, 'const') && item !== spec.const) ||
          (spec.enum && !spec.enum.includes(item))) throw new Error('invalid_public_choice');
      clean[key] = item;
    });
    if (!catalog.places.some(place => place.place_id === clean.place_id) ||
        !completedMonths(now).includes(clean.experience_month)) throw new Error('invalid_public_choice');
    return clean;
  }
  function publicJSON(value, schema, catalog, now) {
    return JSON.stringify(validatePublic(value, schema, catalog, now), null, 2) + '\n';
  }
  function saveNote(storage, note) {
    if (typeof note !== 'string' || note.length > NOTE_LIMIT) throw new Error('private_note_limit');
    storage.setItem(NOTE_KEY, note);
    if (storage.getItem(NOTE_KEY) !== note) throw new Error('private_storage_unavailable');
  }
  function loadNote(storage) {
    const value = storage.getItem(NOTE_KEY);
    if (value === null) return '';
    if (typeof value !== 'string' || value.length > NOTE_LIMIT) throw new Error('private_storage_unavailable');
    return value;
  }
  function deleteNote(storage) {
    storage.removeItem(NOTE_KEY);
    if (storage.getItem(NOTE_KEY) !== null) throw new Error('private_storage_unavailable');
  }
  function download(name, text, mime) {
    const blob = new Blob([text], {type: mime});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function mount(doc, options) {
    options = options || {};
    const schema = options.schema || JSON.parse(doc.getElementById('public-schema').textContent);
    const catalog = options.catalog || JSON.parse(doc.getElementById('place-catalog').textContent);
    const now = options.now || (() => new Date());
    const saveFile = options.download || download;
    const storage = () => options.storage || root.localStorage;
    const get = id => doc.getElementById(id);
    const publicStatus = text => { get('public-status').textContent = text; };
    const privateStatus = text => { get('private-status').textContent = text; };
    const publicFields = schema.required.filter(key => !['schema_version', 'consent', 'license'].includes(key));
    const controls = {};
    publicFields.forEach(key => {
      const label = doc.createElement('label');
      label.textContent = FIELD_LABELS[key];
      const select = doc.createElement('select');
      select.id = key;
      select.name = key;
      select.required = true;
      const entries = key === 'place_id' ? catalog.places.map(p => [p.place_id, p.name]) :
        key === 'experience_month' ? completedMonths(now()).map(month => [month, month]) :
        schema.properties[key].enum.map(value => [value, LABELS[value] || value]);
      const placeholder = doc.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '請選擇';
      select.appendChild(placeholder);
      entries.forEach(([value, text]) => {
        const option = doc.createElement('option');
        option.value = value;
        option.textContent = text;
        select.appendChild(option);
      });
      label.appendChild(select);
      get('choice-fields').appendChild(label);
      controls[key] = select;
      select.addEventListener('change', invalidatePreview);
    });
    get('catalog-state').textContent = catalog.demo ?
      '示範目錄：全部場所均為虛構，這裡沒有真實住戶評價。' :
      '營運者維護的場所目錄；投稿者不能自填場所名稱。';
    let reviewed = null;
    function invalidatePreview() {
      reviewed = null;
      get('download-public').disabled = true;
      get('public-preview').textContent = '更改選項後，請重新產生公開預覽。';
      publicStatus('尚未產生可下載的公開資料。');
    }
    function choices() {
      const value = {schema_version: 1, consent: get('consent').checked, license: 'CC0-1.0'};
      publicFields.forEach(key => { value[key] = controls[key].value; });
      return value;
    }
    get('consent').addEventListener('change', invalidatePreview);
    get('public-form').addEventListener('submit', event => {
      event.preventDefault();
      try {
        reviewed = publicJSON(choices(), schema, catalog, now());
        get('public-preview').textContent = reviewed;
        get('download-public').disabled = false;
        publicStatus('請核對下方 JSON。私人筆記不在這份資料內；下載不會投稿到網路。');
      } catch (_) {
        reviewed = null;
        get('download-public').disabled = true;
        get('public-preview').textContent = '尚無有效公開資料。';
        publicStatus('請完成所有選項並確認公開資料授權。');
      }
    });
    get('download-public').addEventListener('click', () => {
      try {
        const current = publicJSON(choices(), schema, catalog, now());
        if (!reviewed || current !== reviewed) throw new Error('review_required');
        saveFile('community-public.json', reviewed, 'application/json');
        publicStatus('已建立公開 JSON 下載；尚未發佈。請只將這個檔案交給本機匯入工具。');
      } catch (_) {
        invalidatePreview();
        publicStatus('下載未完成。請重新核對公開選項與預覽。');
      }
    });
    const note = get('private-note');
    note.maxLength = NOTE_LIMIT;
    try {
      note.value = loadNote(storage());
      privateStatus(note.value ? '已從此瀏覽器載入私人筆記。' : '尚未保存私人筆記。');
    } catch (_) {
      privateStatus('瀏覽器儲存不可用；筆記只在目前頁面，關閉前請自行下載。');
    }
    note.addEventListener('input', () => privateStatus('有未保存的修改；請按「存到此瀏覽器」。'));
    get('save-note').addEventListener('click', () => {
      try {
        saveNote(storage(), note.value);
        privateStatus('已存到此瀏覽器。沒有上傳，也沒有包含在公開 JSON。');
      } catch (_) {
        privateStatus('未能保存。請縮短至 8,000 字內，或自行下載後保管。');
      }
    });
    get('copy-note').addEventListener('click', async () => {
      try {
        if (note.value.length > NOTE_LIMIT) throw new Error('private_note_limit');
        if (options.copy) await options.copy(note.value);
        else await root.navigator.clipboard.writeText(note.value);
        privateStatus('私人筆記已複製到剪貼簿；請自行決定分享對象。');
      } catch (_) {
        note.focus();
        note.select();
        privateStatus('未能自動複製；已選取筆記，請使用系統複製功能。');
      }
    });
    get('download-note').addEventListener('click', () => {
      try {
        if (note.value.length > NOTE_LIMIT) throw new Error('private_note_limit');
        saveFile('PRIVATE-community-note.txt', note.value, 'text/plain;charset=utf-8');
        privateStatus('已建立私人筆記下載。這個檔案不要交給公開匯入工具。');
      } catch (_) {
        privateStatus('私人筆記下載未完成。');
      }
    });
    get('delete-note').addEventListener('click', () => {
      note.value = '';
      try {
        deleteNote(storage());
        note.value = '';
        privateStatus('已刪除此瀏覽器的筆記。先前下載、剪貼簿或自行分享的副本不會被刪除。');
      } catch (_) {
        privateStatus('已清除頁面上的筆記，但未能確認瀏覽器儲存已刪除；請使用清除網站資料功能。');
      }
    });
    return {controls, invalidatePreview};
  }
  const api = {completedMonths, validatePublic, publicJSON, saveNote, loadNote, deleteNote,
               mount, NOTE_KEY, NOTE_LIMIT};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else {
    root.CommunityFeedback = api;
    document.addEventListener('DOMContentLoaded', () => mount(document));
  }
})(typeof globalThis !== 'undefined' ? globalThis : this);
