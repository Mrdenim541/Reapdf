// Current UI acceptance for the everyday subset of the historical full smoke.
// The historical extended smoke remains separate and is not certified by this.
import {chromium,expect} from '@playwright/test';
import {execFileSync,spawn} from 'node:child_process';
import {mkdtempSync,existsSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-core-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python',input=join(root,'Core.pdf'),output=join(root,'Editado.pdf'),organized=join(root,'Organizado.pdf');
execFileSync(python,['scripts/create_sample.py',input]);
const url=process.env.REAPDF_URL||'http://127.0.0.1:8766',server=process.env.REAPDF_URL?null:spawn(python,['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8766'],{stdio:'ignore',env:{...process.env,REAPDF_DATA_DIR:join(root,'state')}});
let browser,page;
try{
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch(url+'/api/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready)throw new Error('Core server failed');
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined)});page=await browser.newPage({viewport:{width:1600,height:1150}});page.setDefaultTimeout(20000);const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(url);
 await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(input);await expect(page.locator('.document-bar')).toContainText('Core.pdf');await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: Texto original',exact:true}).click();const entry=page.getByLabel('Texto sobre la página',{exact:true});await expect(entry).toBeEnabled();await entry.fill('Texto nuevo');await entry.press('Control+Enter');await expect(entry).toHaveCount(0);
 await openTool(page,'Lápiz');let canvas=await page.getByLabel('Lienzo de anotaciones').boundingBox();await page.mouse.move(canvas.x+canvas.width*100/595,canvas.y+canvas.height*410/842);await page.mouse.down();await page.mouse.move(canvas.x+canvas.width*250/595,canvas.y+canvas.height*470/842,{steps:10});await page.mouse.up();await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:/Deshacer/}).click();await expect(page.getByRole('button',{name:/Rehacer/})).toBeEnabled();await page.getByRole('button',{name:/Rehacer/}).click();await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByLabel('Página siguiente',{exact:true}).click();await expect(page.getByAltText('Página 2 del documento')).toBeVisible();await page.getByLabel('Página anterior',{exact:true}).click();await expect(page.getByAltText('Página 1 del documento')).toBeVisible();await page.getByLabel('Reducir zoom',{exact:true}).click();
 await openTool(page,'Lectura');const line=page.locator('.text-layer span').filter({hasText:/^Texto nuevo$/});await expect(line).toBeVisible();await line.dblclick();await expect.poll(()=>page.evaluate(()=>window.getSelection().toString())).toMatch(/Texto|nuevo/);
 await page.getByRole('tab',{name:'Buscar',exact:true}).click();await page.getByRole('searchbox',{name:'Buscar en el documento'}).fill('Texto nuevo');await page.getByRole('button',{name:'Buscar texto',exact:true}).click();await expect(page.getByText('1 de 1',{exact:true})).toBeVisible();await expect(page.locator('[data-search-hit]')).toHaveCount(1);
 let download=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await download).saveAs(output);
 execFileSync(python,['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as d:
 assert len(d)==2 and 'Texto nuevo' in d[0].get_text() and 'Texto original' not in d[0].get_text()
 assert 'Segunda pagina' in d[1].get_text()
 assert [a.type[0] for a in d[0].annots()]==[f.PDF_ANNOT_INK]`,output]);
 await openTool(page,'Organizar páginas');const dialog=page.getByRole('dialog',{name:'Organizar páginas',exact:true});await dialog.getByLabel('Seleccionar todas las páginas',{exact:true}).check();await expect(dialog.getByRole('button',{name:'Eliminar selección',exact:true})).toBeDisabled();await dialog.getByLabel('Seleccionar todas las páginas',{exact:true}).uncheck();await dialog.getByLabel('Seleccionar página 1',{exact:true}).check();await dialog.getByRole('button',{name:'Subir página 2',exact:true}).click();await dialog.getByRole('button',{name:'Girar selección 90°',exact:true}).click();await dialog.getByRole('button',{name:'Aplicar organización',exact:true}).click();await expect(dialog).toHaveCount(0);await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 download=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await download).saveAs(organized);
 execFileSync(python,['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as d:
 assert 'Segunda pagina' in d[0].get_text() and 'Texto nuevo' in d[1].get_text() and d[1].rotation==90
 assert len(list(d[1].annots()))==1 and d.get_toc()==[[1,'Inicio',2],[1,'Segunda pagina',1]]`,organized]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: migrated everyday UI: open, on-page edit, ink, undo/redo, page navigation, zoom, text selection, search, export, page reorder/rotation and bookmark/annotation preservation. Extended historical UI smoke remains pending.');
}catch(e){if(page&&!page.isClosed())console.error((await page.locator('body').innerText()).slice(-2500));throw e;}finally{if(browser)await browser.close();if(server){server.kill();await new Promise(r=>server.once('exit',r));}rmSync(root,{recursive:true,force:true});}
