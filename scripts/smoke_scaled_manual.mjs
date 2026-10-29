import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-scaled-manual-')),scaled=join(root,'Escalado.pdf'),source=join(root,'Origen.pdf'),target=join(root,'Destino.pdf'),revision=join(root,'Revision.pdf'),pack=join(root,'Areas.reapdfset'),out=join(root,'Escalado-editado.pdf');
execFileSync('.venv/bin/python',['-c',`import sys
from pathlib import Path
import pymupdf as f
from tests.test_scaled_groups import source
from tests.test_manual_document_links import scan
Path(sys.argv[1]).write_bytes(source(80,'identity',True));Path(sys.argv[2]).write_bytes(scan());Path(sys.argv[3]).write_bytes(scan())
with f.open(stream=scan()) as d:
 with f.open(stream=scan()) as a:d.insert_pdf(a)
 d.save(sys.argv[4])`,scaled,source,target,revision]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1200}}),errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(scaled);await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: AVATAR TEST',exact:true}).click();const input=page.getByLabel('Texto sobre la página',{exact:true});await expect(input).toBeEnabled();await input.fill('AVATAR TES');await input.press('Control+Enter');await expect(input).toHaveCount(0);await expect(page.locator('.text-layer')).toContainText('AVATAR TES');let wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(out);
 await page.getByLabel('Archivo PDF').setInputFiles(source);await expect(page.locator('.document-bar')).toContainText('Origen.pdf');await openTool(page,'Vincular documentos');await page.getByLabel('PDF para vincular').setInputFiles(target);await expect(page.getByLabel('Documento de destino')).not.toHaveValue('');await page.locator('.manual-links summary').click();await page.getByLabel('Referencia del vínculo manual').fill('ZONA-01');
 async function draw(label){const svg=page.getByLabel(`Área de ${label}`,{exact:true});await expect(page.getByAltText(`Marcar ${label}`)).toBeVisible();await svg.scrollIntoViewIfNeeded();const box=await svg.boundingBox();await page.mouse.move(box.x+.30*box.width,box.y+.40*box.height);await page.mouse.down();await page.mouse.move(box.x+.50*box.width,box.y+.50*box.height,{steps:5});await page.mouse.up();}
 await draw('origen manual');await draw('destino manual');await expect(page.getByRole('button',{name:'Crear vínculo entre áreas',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Crear vínculo entre áreas',exact:true}).click();await expect(page.getByLabel('Navegar vínculo ZONA-01')).toBeVisible();
 await page.locator('.document-revision summary').click();await page.getByLabel('Documento para revisar').selectOption({index:2});await page.getByLabel('Nueva revisión PDF').setInputFiles(revision);await expect(page.locator('.document-revision')).toContainText('Volver a marcar área');await expect(page.getByRole('button',{name:'Aplicar revisión al conjunto',exact:true})).toBeDisabled();await page.getByLabel('Página de área revisada').selectOption('1');await draw('área revisada');await page.getByLabel('Confirmar revisión de vínculos').check();await page.getByRole('button',{name:'Aplicar revisión al conjunto',exact:true}).click();await expect(page.getByLabel('Navegar vínculo ZONA-01')).toContainText('→ 2');
 wait=page.waitForEvent('download');await page.getByRole('button',{name:'Guardar conjunto',exact:true}).click();await(await wait).saveAs(pack);await page.getByLabel('Conjunto para abrir').setInputFiles(pack);await expect(page.getByLabel('Navegar vínculo ZONA-01')).toContainText('→ 2');await page.getByLabel('Navegar vínculo ZONA-01').click();await expect(page.getByAltText('Documento Destino, página 2')).toBeVisible();
 execFileSync('.venv/bin/python',['-c',`from pathlib import Path
import sys,pymupdf as f
from backend.document_sets import read
with f.open(sys.argv[1]) as d:
 assert 'AVATAR TES' in d[0].get_text() and 'UNCHANGED' in d[0].get_text()
 spans=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'];assert abs(spans[0]['size']-18*(.8**.5))<.02
items,links,_=read(Path(sys.argv[2]).read_bytes());assert links[0]['source']['kind']==links[0]['target']['kind']=='manual' and links[0]['target']['page']==1`,out,pack]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: on-page grouped/scaled Identity-H edit and exported scale; manually selected scan areas linked, revision requires new area/page, set saved/reopened and destination navigated.');
}finally{await browser.close();}
