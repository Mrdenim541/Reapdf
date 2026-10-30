import {chromium,expect} from '@playwright/test';import {execFileSync} from 'node:child_process';import {mkdtempSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-named-split-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python',combined=join(root,'Combined.pdf'),plain=join(root,'Lists.pdf'),named=join(root,'Named.zip'),book=join(root,'Bookmarks.zip'),tagged=join(root,'Tagged.pdf'),partition=join(root,'TaggedParts.zip');
execFileSync(python,['-c',`from pathlib import Path
import sys
from tests.test_named_split import source
from tests.test_basic_tagging import source as plain
Path(sys.argv[1]).write_bytes(source());Path(sys.argv[2]).write_bytes(plain())`,combined,plain]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{const page=await browser.newPage({viewport:{width:1600,height:1150}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());page.setDefaultTimeout(30000);await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
async function save(label,path){const saved=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();await(await saved).saveAs(path);}
await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(combined);await openTool(page,'Dividir PDF');let dialog=page.getByRole('dialog',{name:'Dividir PDF',exact:true});await dialog.getByLabel('Modo de división',{exact:true}).selectOption('groups');await dialog.getByLabel('Grupos para dividir',{exact:true}).fill('1-2\n3,5\n4,6');for(const [i,name] of ['Portada','Documento A','Plano de ubicación'].entries())await dialog.getByLabel(`Nombre de parte ${i+1}`,{exact:true}).fill(name);await dialog.getByLabel('Nombre de parte 2',{exact:true}).fill('portada.PDF');await expect(dialog.getByRole('button',{name:'Descargar partes ZIP',exact:true})).toBeDisabled();await dialog.getByLabel('Nombre de parte 2',{exact:true}).fill('Documento A');await dialog.getByLabel('Incluir relación de archivos de división',{exact:true}).check();await save('Descargar partes ZIP',named);await dialog.getByLabel('Modo de división',{exact:true}).selectOption('bookmarks');await dialog.getByRole('button',{name:'Preparar desde marcadores',exact:true}).click();await expect(dialog.getByLabel('Nombre de parte 1',{exact:true})).toHaveValue('001-Inicio.pdf');await expect(dialog.getByLabel('Nombre de parte 3',{exact:true})).toHaveValue('003-Second_section.pdf');await dialog.getByLabel('Nombre de parte 2',{exact:true}).fill('Chapter personal');await save('Descargar partes ZIP',book);await dialog.getByRole('button',{name:'Cerrar',exact:true}).click();
await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(plain);await openTool(page,'Etiquetas y orden de lectura');dialog=page.getByRole('dialog',{name:'Etiquetas y orden de lectura',exact:true});await dialog.getByRole('button',{name:'Preparar etiquetas iniciales',exact:true}).click();for(const p of [0,1]){if(p)await dialog.getByLabel('Página de etiquetado inicial',{exact:true}).selectOption({value:String(p)});await expect(dialog.getByLabel(`Revisé etiquetas de página ${p+1}`,{exact:true})).toBeVisible();await dialog.getByLabel('Rol del objeto 1',{exact:true}).selectOption('H1');for(const i of [2,3])await dialog.getByLabel(`Rol del objeto ${i}`,{exact:true}).selectOption('LI');await expect(dialog.getByLabel(`Revisé etiquetas de página ${p+1}`,{exact:true})).toBeEnabled();await dialog.getByLabel(`Revisé etiquetas de página ${p+1}`,{exact:true}).check();}await dialog.getByRole('button',{name:'Crear etiquetas revisadas',exact:true}).click();await expect(dialog).toHaveCount(0);await save('Exportar copia',tagged);await openTool(page,'Dividir PDF');dialog=page.getByRole('dialog',{name:'Dividir PDF',exact:true});await dialog.getByLabel('Nombre de parte 1',{exact:true}).fill('First list');await dialog.getByLabel('Nombre de parte 2',{exact:true}).fill('Second list');await save('Descargar partes ZIP',partition);await dialog.getByRole('button',{name:'Cerrar',exact:true}).click();
execFileSync(python,['-c',`from zipfile import ZipFile
import sys,json,pymupdf as f
from backend.structure_editing import model,reading_preview
with f.open(sys.argv[1]) as original,ZipFile(sys.argv[2]) as z:
 assert z.namelist()==['Portada.pdf','Documento A.pdf','Plano de ubicación.pdf','reapdf-division.json']
 groups=[[0,1],[2,4],[3,5]]
 for name,group in zip(z.namelist(),groups):
  with f.open(stream=z.read(name)) as part:
   assert len(part)==len(group)
   for p,n in zip(part,group):assert p.get_text()==original[n].get_text() and p.get_pixmap().samples==original[n].get_pixmap().samples
 assert json.loads(z.read('reapdf-division.json'))['parts'][1]['source_pages']==[3,5]
with ZipFile(sys.argv[3]) as z:assert z.namelist()==['001-Inicio.pdf','Chapter personal.pdf','003-Second_section.pdf','reapdf-division.json']
with ZipFile(sys.argv[5]) as z:
 assert z.namelist()==['First list.pdf','Second list.pdf']
 for name in z.namelist():
  data=z.read(name);rows=model(data,[])['nodes'];assert sum(r['role']=='LI' for r in rows)==2 and sum(r['role']=='Sect' for r in rows)==1;assert reading_preview(data,[],0)['untagged_blocks']==0`,combined,named,book,tagged,partition]);if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: actual Chromium custom ordered ranges and personalized PDF names, duplicate-name validation, ZIP receipt, bookmark sections with editable titles; reviewed real list tags, exported and split with off-part nodes removed and retained parent keys/read order valid.');
}finally{await browser.close();}
