import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';import {mkdtempSync} from 'node:fs';import {join} from 'node:path';import {tmpdir} from 'node:os';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-states-ui-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
const cases=[['Transparente',0],['GrupoCFF',1],['GrupoType3',2],['GrupoCFF2',3],['GrupoOpaco',4]],inputs=cases.map(c=>join(root,c[0]+'.pdf')),outputs=cases.map(c=>join(root,c[0]+'-editado.pdf'));
execFileSync(python,['-c',`from pathlib import Path
import json,sys
from tests.test_text_states_compositing import source
for (name,kind),path in zip(json.loads(sys.argv[1]),sys.argv[2:]):Path(path).write_bytes(source(['base','cff','type3','cff2','base'][kind],1 if kind==4 else .45,kind>0,90 if kind%2 else 0))`,JSON.stringify(cases),...inputs]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1200}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
 for(let i=0;i<cases.length;i++){
  await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(inputs[i]);await expect(page.locator('.document-bar')).toContainText(cases[i][0]+'.pdf');await openTool(page,'Editar texto');
  const target=page.getByRole('button',{name:'Editar en página: ABC ABC',exact:true}).first();await expect(target).toBeVisible();await expect.poll(()=>target.evaluate(e=>e.tagName.toLowerCase())).toBe('polygon');await target.click();
  const input=page.getByLabel('Texto sobre la página',{exact:true});await expect(input).toBeEnabled();await expect(page.getByLabel('Fuente de edición directa',{exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'Editar párrafo',exact:true})).toBeDisabled();await expect(page.locator('.text-edit-outline')).toBeVisible();await expect(page.locator('.inline-text-status')).toContainText('Conserva la transparencia');
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
  from backend.engine import spans
  a[0].set_rotation(0);b[0].set_rotation(0)
  old=next(s for s in spans(a[0]) if s['text']=='ABC ABC');new=next(s for s in spans(b[0]) if s['text']=='CBA AB');assert old['alpha']==new['alpha']
  if 'GrupoOpaco' not in left:assert new['alpha']<255
  for text in ['BAC BAC','CAB CAB']:assert a[0].search_for(text)==b[0].search_for(text)
  x={v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()};y={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()};assert x==y`,...inputs.flatMap((v,i)=>[v,outputs[i]])]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: Intermediate font/color/alpha/absolute positions and isolated transparency groups edited on page; opacity/original programs/neighbors/shared occurrences preserved, undo/redo/export.');
}finally{await browser.close();}
