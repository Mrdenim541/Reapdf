import {chromium,expect} from '@playwright/test';
import {execFileSync,spawn} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-image-occurrences-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python',source=join(root,'Shared.pdf'),output=join(root,'Edited.pdf');
execFileSync(python,['-c','from tests.test_image_occurrences import fixture;from pathlib import Path;import sys;Path(sys.argv[1]).write_bytes(fixture(forms=True))',source]);
const url='http://127.0.0.1:8768',server=spawn(python,['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8768'],{stdio:'ignore',env:{...process.env,REAPDF_DATA_DIR:join(root,'state')}});let browser;
try{
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch(url+'/api/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready)throw new Error('Server not ready');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});const page=await browser.newPage({viewport:{width:1600,height:1150}}),errors=[];page.setDefaultTimeout(25000);page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(url);await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(source);await openTool(page,'Editar imágenes del PDF');
 let d=page.getByRole('dialog',{name:'Editar imágenes del PDF',exact:true});await expect(d.getByLabel('Imagen existente',{exact:true})).toHaveValue('0');
 await d.getByRole('button',{name:'Seleccionar imagen 2 en página',exact:true}).click();await expect(d.getByLabel('Imagen existente',{exact:true})).toHaveValue('1');
 await d.getByLabel('X de imagen existente',{exact:true}).fill('350');await d.getByRole('button',{name:'Vista previa de imagen editada',exact:true}).click();await expect(d.getByRole('button',{name:'Aplicar imagen editada',exact:true})).toBeEnabled();await d.getByRole('button',{name:'Aplicar imagen editada',exact:true}).click();await expect(d).toHaveCount(0);
 await page.getByRole('button',{name:/Deshacer/}).click();await page.getByRole('button',{name:/Rehacer/}).click();let pending=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await pending).saveAs(output);
 execFileSync(python,['-c',`import sys,pymupdf as f
from backend.image_editing import image_model
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 old=image_model(a,0)['images'];new=image_model(b,0)['images'];assert len(new)==2
 assert new[0]['rect']==old[0]['rect'] and abs(new[1]['rect'][0]-350)<.02
 assert b[0].get_pixmap(clip=f.Rect(old[0]['rect'])).samples==a[0].get_pixmap(clip=f.Rect(old[0]['rect'])).samples
 assert b[1].get_pixmap().samples==a[1].get_pixmap().samples
 assert a[0].get_text()==b[0].get_text()`,source,output]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: visual selection of a shared nested Form image, isolated move, preview, apply, undo/redo and export preserve other appearance, text and page.');
}finally{if(browser)await browser.close();server.kill();await new Promise(r=>server.once('exit',r));rmSync(root,{recursive:true,force:true});}
