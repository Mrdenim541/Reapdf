import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';import {mkdtempSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-fonts-ui-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
const cases=[['Type3',0],['Type3Form',1],['CFF2',2]],inputs=cases.map(c=>join(root,c[0]+'.pdf')),outputs=cases.map(c=>join(root,c[0]+'-editado.pdf'));
execFileSync(python,['-c',`from pathlib import Path
import json,sys
from tests.test_type3_fonts import type3_pdf
from tests.test_static_cff2 import source
for (name,kind),path in zip(json.loads(sys.argv[1]),sys.argv[2:]):Path(path).write_bytes(type3_pdf(90,'1 .2 .3 1',kind==1) if kind<2 else source(270,True))`,JSON.stringify(cases),...inputs]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1200}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
 for(let i=0;i<cases.length;i++){
  await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(inputs[i]);await expect(page.locator('.document-bar')).toContainText(cases[i][0]+'.pdf');await openTool(page,'Editar texto');
  const target=page.getByRole('button',{name:'Editar en página: ABC ABC',exact:true}).first();await expect(target).toBeVisible();await expect.poll(()=>target.evaluate(e=>e.tagName.toLowerCase())).toBe('polygon');await target.click();
  const input=page.getByLabel('Texto sobre la página',{exact:true});await expect(input).toBeEnabled();await expect(page.getByLabel('Fuente de edición directa',{exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Editar párrafo',exact:true})).toBeDisabled();await expect(page.locator('.text-edit-outline')).toBeVisible();
  await input.fill('CBA AB');await input.press('Control+Enter');await expect(input).toHaveCount(0);await page.getByRole('button',{name:/Deshacer/}).click();await openTool(page,'Editar texto');await expect(page.getByRole('button',{name:'Editar en página: ABC ABC',exact:true}).first()).toBeVisible();await page.getByRole('button',{name:/Rehacer/}).click();
  const saved=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await saved).saveAs(outputs[i]);
 }
 execFileSync(python,['-c',`import sys,pymupdf as f
for left,right in zip(sys.argv[1::2],sys.argv[2::2]):
 with f.open(left) as a,f.open(right) as b:
  assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox
  assert 'CBA AB' in b[0].get_text()
  if len(a)>1:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
  from tests.test_type3_fonts import glyphs
  assert glyphs(a)==glyphs(b)
  x={v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()};y={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()};assert x==y`,...inputs.flatMap((v,i)=>[v,outputs[i]])]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: Type3 vector fonts and static CFF2 edited on page, shared Forms isolated, original glyph programs, rotation, neighbors and other pages preserved; undo/redo/export.');
}finally{await browser.close();}
