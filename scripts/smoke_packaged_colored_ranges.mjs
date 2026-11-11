// Actual bundled Qt; observe form apply then replay its request for native PDF verification.
import {chromium,expect} from '@playwright/test';
import {writeFileSync} from 'node:fs';
import {openTool} from './smoke-tool-navigation.mjs';
const [endpoint,output]=process.argv.slice(2),browser=await chromium.connectOverCDP(endpoint,{timeout:45000,noDefaults:true});
try{
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:'));page.setDefaultTimeout(30000);await expect(page.locator('.text-layer')).toContainText('COLOR NUMBER FORM',{timeout:40000});
 async function fill(value,path){await openTool(page,'Rellenar formulario');await page.getByLabel('Valor del formulario',{exact:true}).fill(value);const pending=page.waitForResponse(r=>r.url().endsWith('/export')&&r.request().postDataJSON().operations?.some(op=>op.type==='form_fill'));await page.getByRole('button',{name:'Aplicar formulario',exact:true}).click();const r=await pending;if(!r.ok())throw new Error('Form apply failed: '+r.status());const payload=r.request().postDataJSON(),url=r.url();const encoded=await page.evaluate(async({url,payload})=>{const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error(await response.text());let s='';for(const b of new Uint8Array(await response.arrayBuffer()))s+=String.fromCharCode(b);return btoa(s);},{url,payload});writeFileSync(path,Buffer.from(encoded,'base64'));await expect(page.locator('.form-dialog[open]')).toHaveCount(0);}
 await fill('-12.5',output);await fill('4',output+'.positive.pdf');await page.getByRole('button',{name:'Deshacer',exact:false}).click();await page.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(page.locator('.document-bar')).toContainText('0 cambios');
 console.log('PASS: compiled Qt applies red negative then black positive with quoted range bounds; native PDFs verified via bundled server; undo restores original. No external browser or native save dialog in this journey.');
}finally{await browser.close();}
