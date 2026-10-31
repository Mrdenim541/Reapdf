// Connect to the Qt window started by the compiled Windows launcher. This never
// launches a browser; CDP is enabled only in the verifier's child environment.
import {chromium,expect} from '@playwright/test';
import {writeFileSync} from 'node:fs';
import {openTool} from './smoke-tool-navigation.mjs';
const [endpoint,output]=process.argv.slice(2);
const browser=await chromium.connectOverCDP(endpoint,{timeout:45000});
try{
 const contexts=browser.contexts();if(contexts.length!==1)throw new Error('Expected one embedded Qt context');
 const page=contexts[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:'));if(!page)throw new Error('Embedded application target missing');
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await expect(page.locator('.text-layer')).toContainText('Texto original',{timeout:40000});
 if(!await page.evaluate(async()=>typeof(await window.reapdfDesktop)?.saveFile==='function'))throw new Error('Native QWebChannel save bridge missing');
 await openTool(page,'Editar texto');
 await page.getByRole('button',{name:'Editar en página: Texto original',exact:true}).click();
 await page.getByLabel('Texto sobre la página',{exact:true}).fill('Ejecutable');
 const edited=page.waitForResponse(r=>/\/(replace-styled-text|replace-paragraph)$/.test(r.url())&&r.request().method()==='POST');
 await page.getByLabel('Texto sobre la página',{exact:true}).press('Control+Enter');
 const adopted=await(await edited).json();if(!adopted.id)throw new Error('Edited version was not adopted');
 await expect(page.locator('.text-layer')).toContainText('Ejecutable');
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('Texto original');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('Ejecutable');
 // Export the adopted version through its actual server; native dialog/atomic
 // save are tested separately. Do not label this as a native disk-save test.
 const encoded=await page.evaluate(async id=>{
  const r=await fetch(`/api/documents/${id}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:[]})});if(!r.ok)throw new Error(await r.text());
  const bytes=new Uint8Array(await r.arrayBuffer());let s='';for(const b of bytes)s+=String.fromCharCode(b);return btoa(s);
 },adopted.id);
 writeFileSync(output,Buffer.from(encoded,'base64'));
 if(errors.length)throw new Error(errors.join('\n'));
 await page.evaluate(()=>{window.__reapdfCloseState={dirty:false,busy:false};});
 console.log('PASS: compiled Reapdf.exe opens its Qt window, loads PDF, edits text on page, undoes/redoes and exports through the bundled server.');
}finally{await browser.close();}
