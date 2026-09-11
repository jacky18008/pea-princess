"""Run attachment UI handlers offline in the same DOM harness as the chat checks."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PlaygroundAttachmentUI(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node unavailable; UI checks not run")
    def test_attachment_drafts_uploads_and_submission(self):
        tests = Path(__file__).parent
        # Reuse only the fake DOM/network setup, without the existing main test.
        harness = (tests / "test_playground_ui.js").read_text().split("\nasync function main(){", 1)[0]
        checks = r'''
context.FileReader=class {
 readAsDataURL(file){this.result='data:application/octet-stream;base64,'+Buffer.from(file.contents||'example').toString('base64');setImmediate(()=>this.onload());}
};
const metadata=(id,name='房源資料.pdf')=>({id,name,bytes:7,sha256:'a'.repeat(64),mime_type:'application/pdf'});
const agentState=id=>({...liveState(id),output_mode:'agent'});
const ev=()=>({preventDefault(){}});
const file=(name='房源 資料.pdf',size=7)=>({name,size,contents:'example'});
const postRows=url=>captured.filter(row=>row.url===url);
let attachmentCount=0,override=null;
handler=(url,opts)=>{
 if(override){const value=override(url,opts);if(value!==undefined)return value;}
 if(url==='/api/attachments')return response(metadata('file-'+(++attachmentCount),JSON.parse(opts.body).name||'路徑 文件.txt'));
 const match=url.match(/^\/api\/session\/([^/]+)$/);if(match)return response(agentState(match[1]));
};
async function main(){
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../playground/app.js'),'utf8'),context);await settle();
 assert.equal(captured.length,0,'opening the page must not upload or dispatch');
 assert.equal(elements.create.disabled,true);
 elements['initial-pick'].onclick();elements['initial-files'].files=[file()];await elements['initial-files'].onchange();
 assert.equal(postRows('/api/attachments')[0].data.name,'房源 資料.pdf');
 assert.equal(postRows('/api/attachments')[0].data.content_base64,Buffer.from('example').toString('base64'));
 assert.match(elements['initial-file-list'].textContent,/房源 資料.pdf.*待送出/);
 assert.equal(elements.create.disabled,false,'an attachment alone can start a live session');
 const localPath='/Users/test/租屋 資料/完整 文件.txt';elements['initial-path'].value=localPath;
 await elements['initial-path-add'].onclick();assert.equal(postRows('/api/attachments')[1].data.path,localPath);
 assert.equal(captured.length,2,'uploading and path import must not dispatch');
 let failCreate=true;
 override=(url,opts)=>{if(url==='/api/sessions'&&opts.method==='POST'){if(failCreate){failCreate=false;throw Error('uncertain create');}return response({id:'A'});}};
 await elements.create.onclick();assert.equal(elements['initial-file-list'].children.length,2);
 await elements.create.onclick();const creates=postRows('/api/sessions');
 assert.equal(creates[0].data.client_id,creates[1].data.client_id);assert.deepEqual(creates[1].data.attachments,['file-1','file-2']);
 assert.equal(creates[1].data.initial_request,'');assert.equal(elements['initial-file-list'].children.length,0);
 assert.equal(elements['message-attachments'].hidden,false);
 assert.equal(captured.some(row=>row.url.endsWith('/control')),false);
 override=null;
 // An upload completes into the draft that owned the drop, even after switching.
 elements.message.value='A 的草稿';elements.message.oninput();let resolveUpload;
 override=(url,opts)=>url==='/api/attachments'?new Promise(resolve=>resolveUpload=resolve):undefined;
 const uploading=elements.composer.ondrop({dataTransfer:{files:[file('A 文件.pdf')]},preventDefault(){}});await settle();
 assert.equal(elements.send.disabled,true);assert.match(elements['message-file-list'].textContent,/正在加入/);
 const beforePendingSend=captured.length;await elements.composer.onsubmit(ev());assert.equal(captured.length,beforePendingSend);
 await run("select('B')");assert.equal(elements.message.value,'');assert.equal(elements['message-file-list'].children.length,0);
 elements.message.value='B 的草稿';elements.message.oninput();resolveUpload(response(metadata('A-file','A 文件.pdf')));await uploading;
 assert.equal(elements.message.value,'B 的草稿');assert.equal(elements['message-file-list'].children.length,0);
 override=null;await run("select('A')");assert.equal(elements.message.value,'A 的草稿');assert.match(elements['message-file-list'].textContent,/A 文件.pdf/);
 // Native selection belongs to the session where the chooser was opened.
 elements['message-pick'].onclick();await run("select('B')");elements['message-files'].files=[file('A later.pdf')];await elements['message-files'].onchange();
 assert.equal(elements['message-file-list'].children.length,0);await run("select('A')");assert.equal(elements['message-file-list'].children.length,2);
 let failMessage=true;
 override=(url,opts)=>{if(url==='/api/session/A/message'){if(failMessage){failMessage=false;throw Error('uncertain message');}return response({ok:true});}};
 await elements.composer.onsubmit(ev());assert.equal(elements.message.value,'A 的草稿');assert.equal(elements['message-file-list'].children.length,2);
 await run("select('B')");assert.equal(elements.message.value,'B 的草稿');await run("select('A')");await elements.composer.onsubmit(ev());
 const messagesA=postRows('/api/session/A/message');assert.equal(messagesA[0].data.client_id,messagesA[1].data.client_id);
 assert.deepEqual(messagesA[1].data.attachments,['A-file','file-3']);assert.equal(elements.message.value,'');assert.equal(elements['message-file-list'].children.length,0);
 // A changed attachment set changes the retry fingerprint even with identical text.
 override=null;elements['message-path'].value=localPath;await elements['message-path-add'].onclick();
 override=(url,opts)=>url==='/api/session/A/message'?Promise.reject(Error('uncertain')):undefined;
 await elements.composer.onsubmit(ev());const previous=postRows('/api/session/A/message').at(-1);
 elements['message-file-list'].children[0].children[1].onclick();override=null;
 elements['message-path'].value=localPath;await elements['message-path-add'].onclick();await elements.composer.onsubmit(ev());
 const changed=postRows('/api/session/A/message').at(-1);assert.notEqual(changed.data.client_id,previous.data.client_id);assert.equal(changed.data.text,'');assert.equal(changed.data.attachments.length,1);
 // Removing an upload while HTTP is pending cannot resurrect it.
 override=(url,opts)=>url==='/api/attachments'?new Promise(resolve=>resolveUpload=resolve):undefined;
 const removed=elements.composer.onpaste({clipboardData:{files:[file()]},preventDefault(){}});await settle();
 elements['message-file-list'].children[0].children[1].onclick();resolveUpload(response(metadata('removed')));await removed;
 assert.equal(elements['message-file-list'].children.length,0);assert.equal(elements.send.disabled,false);
 // Oversized files stay removable and never reach the upload API; failed uploads block submit.
 override=null;const beforeLarge=postRows('/api/attachments').length;
 elements['message-files'].files=[file('too-big.pdf',25*1024*1024+1)];await elements['message-files'].onchange();
 assert.equal(postRows('/api/attachments').length,beforeLarge);assert.match(elements['message-file-list'].textContent,/25 MB/);assert.equal(elements.send.disabled,true);
 elements['message-file-list'].children[0].children[1].onclick();
 override=(url,opts)=>url==='/api/attachments'?Promise.reject(Error('檔案不存在')):undefined;
 elements['message-path'].value='/missing 文件.pdf';await elements['message-path-add'].onclick();assert.match(elements['message-file-list'].textContent,/檔案不存在/);
 elements['message-file-list'].children[0].children[1].onclick();override=null;
 // Reserve slots before asynchronous reads so one drop cannot exceed six.
 const beforeMany=postRows('/api/attachments').length;
 await elements.composer.ondrop({dataTransfer:{files:Array.from({length:7},(_,i)=>file(i+'.txt'))},preventDefault(){}});
 assert.equal(postRows('/api/attachments').length-beforeMany,6);assert.equal(elements['message-file-list'].children.length,6);assert.equal(elements['message-pick'].disabled,true);
 for(let i=0;i<6;i++)elements['message-file-list'].children[0].children[1].onclick();
 // Read-only or fixture lanes cannot upload; attachment metadata is always text.
 context.fixture=state('A');run('render(fixture)');assert.equal(elements['message-attachments'].hidden,true);
 const beforeFixture=captured.length;await elements.composer.ondrop({dataTransfer:{files:[file()]},preventDefault(){}});assert.equal(captured.length,beforeFixture);
 context.checked={...agentState('A'),output_mode:'checked'};run('render(checked)');assert.equal(elements['message-attachments'].hidden,true);
 context.safe={...agentState('A'),messages:[{role:'human',text:'',attachments:[metadata('unsafe','<img src=x onerror=alert(1)>.pdf')]}]};run('render(safe)');
 assert.match(elements.messages.textContent,/<img src=x onerror=alert\(1\)>.pdf/);
 // Fixtures omit even an already prepared initial attachment.
 elements['initial-files'].files=[file()];await elements['initial-files'].onchange();elements['research-mode'].value='fixture';elements['research-mode'].onchange();
 override=(url,opts)=>url==='/api/sessions'&&opts.method==='POST'?response({id:'F'}):undefined;
 await elements.create.onclick();assert.equal('attachments' in postRows('/api/sessions').at(-1).data,false);
 assert.equal(elements['initial-file-list'].children.length,1,'fixture creation retains the unused live draft');
 console.log('attachment UI checks passed');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
'''
        # node -e resolves __dirname from cwd, matching the existing JS harness.
        result = subprocess.run([shutil.which("node"), "-e", harness + checks], cwd=tests,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("attachment UI checks passed", result.stdout)
