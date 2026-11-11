// Exercise Word conversion inside the actual compiled Qt window.
import {chromium,expect} from '@playwright/test';
import {readFileSync,writeFileSync} from 'node:fs';
const [endpoint,output,word,mode="columns"]=process.argv.slice(2),browser=await chromium.connectOverCDP(endpoint,{timeout:45000,noDefaults:true});
try{
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:'));if(!page)throw new Error('Embedded Qt target missing');page.setDefaultTimeout(30000);
 await expect(page.locator('.text-layer')).toContainText('Texto original',{timeout:40000});
 await expect(page.locator('.file-menu')).toBeVisible();await page.locator('.file-menu').evaluate(e=>{e.open=true;});await page.getByRole('button',{name:'Crear PDF desde Word',exact:true}).click();
 await page.getByLabel('Archivo Word para convertir',{exact:true}).setInputFiles({name:'Columns.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:readFileSync(word)});
 const response=page.waitForResponse(r=>r.url().endsWith('/api/import/docx')&&r.request().method()==='POST');await page.getByRole('button',{name:'Convertir y revisar Word',exact:true}).click();const r=await response,d=await r.json();if(!r.ok()||!d.document?.id)throw new Error(JSON.stringify(d));
 if(!d.report.text_check_passed||d.report.sections[0].columns.widths.length!==2||d.report.internal_hyperlinks!==(mode==='manual'?2:1)||(mode==='manual'&&(d.report.manual_column_breaks!==4||d.report.manual_page_breaks!==2||d.report.continuous_sections_merged!==1||d.document.pages.length!==4)))throw new Error('Column/bookmark conversion incomplete');
 for(let i=0;i<d.document.pages.length;i++){
  await page.getByLabel('Página de Word importado',{exact:true}).selectOption(String(i));const check=page.getByLabel(`Revisé Word página ${i+1}`,{exact:true});await expect(check).toBeEnabled();await check.check();
 }
 await page.getByLabel('Aceptar diferencias de importación Word',{exact:true}).check();await page.getByRole('button',{name:'Abrir PDF convertido',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.document-bar')).toContainText(d.name);
 const encoded=await page.evaluate(async id=>{const r=await fetch(`/api/documents/${id}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:[]})});if(!r.ok)throw new Error(await r.text());let s='';for(const v of new Uint8Array(await r.arrayBuffer()))s+=String.fromCharCode(v);return btoa(s);},d.document.id);writeFileSync(output,Buffer.from(encoded,'base64'));
 await page.evaluate(()=>{window.__reapdfCloseState={dirty:false,busy:false};});console.log('PASS: compiled Qt imports DOCX with columns and bookmark link, reviews every page, opens and exports through bundled server; no external browser or native save dialog used in this check.');
}finally{await browser.close();}
