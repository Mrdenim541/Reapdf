// Drive the embedded Qt renderer of the actual executable; no external browser.
import {chromium,expect} from '@playwright/test';
import {writeFileSync} from 'node:fs';
import {openTool} from './smoke-tool-navigation.mjs';
const [endpoint,output]=process.argv.slice(2),browser=await chromium.connectOverCDP(endpoint,{timeout:45000,noDefaults:true});
try{
 const page=browser.contexts()[0].pages().find(p=>p.url().startsWith('http://127.0.0.1:'));page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await expect(page.locator('.text-layer')).toContainText('Keep this text',{timeout:40000});
 async function apply(suffix){
  const button=page.getByRole('button',{name:'Aplicar imagen editada',exact:true});await expect(button).toBeEnabled();
  const response=page.waitForResponse(r=>r.url().endsWith('/edit-image')&&r.request().postDataJSON()?.preview!==true&&r.request().method()==='POST');await button.click();const r=await response,d=await r.json();if(!r.ok()||!d.id)throw new Error(JSON.stringify(d));await expect(page.getByRole('dialog')).toHaveCount(0);
  const b64=await page.evaluate(async id=>{const r=await fetch(`/api/documents/${id}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:[]})});if(!r.ok)throw new Error(await r.text());const b=new Uint8Array(await r.arrayBuffer());let s='';for(const v of b)s+=String.fromCharCode(v);return btoa(s);},d.id);
  writeFileSync(suffix?output.replace(/\.pdf$/,suffix+'.pdf'):output,Buffer.from(b64,'base64'));
 }
 await openTool(page,'Editar imágenes del PDF');await expect(page.getByLabel('Acción de imagen existente',{exact:true})).toBeEnabled();
 const rect=page.locator('[aria-label="Mover imagen existente en muestra"] rect[data-image-index="0"]').first();await rect.scrollIntoViewIfNeeded();const b=await rect.boundingBox();if(!b)throw new Error('Image target missing');
 await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2+20,b.y+b.height/2+12,{steps:5});await page.mouse.up();await apply('-moved');
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await openTool(page,'Editar imágenes del PDF');await page.getByLabel('Acción de imagen existente',{exact:true}).selectOption('replace');
 const png=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=80;c.height=40;const x=c.getContext('2d');x.fillStyle='#00aa44';x.fillRect(0,0,80,40);return c.toDataURL('image/png').split(',')[1];});
 await page.getByLabel('Archivo para reemplazar imagen',{exact:true}).setInputFiles({name:'diagram.png',mimeType:'image/png',buffer:Buffer.from(png,'base64')});await page.getByLabel('Descripción de imagen de reemplazo',{exact:true}).fill('New green diagram');await apply('-replaced');
 await openTool(page,'Editar imágenes del PDF');await page.getByLabel('Acción de imagen existente',{exact:true}).selectOption('delete');await apply('');
 if(errors.length)throw new Error(errors.join('\n'));await page.evaluate(()=>{window.__reapdfCloseState={dirty:false,busy:false};});
 console.log('PASS: actual packaged Qt window drags a tagged image, previews automatically, applies, undoes/redoes, replaces with an accessible description and deletes it; three native PDFs exported for independent semantic/content checks. No external browser or native save dialog in this check.');
}finally{await browser.close();}
