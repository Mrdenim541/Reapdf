import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-cff-form-ui-')),cff=join(root,'CFF.pdf'),form=join(root,'Form.pdf'),mixed=join(root,'Mixto.pdf'),cffOut=join(root,'CFF-editado.pdf'),formOut=join(root,'Form-editado.pdf'),mixedOut=join(root,'Mixto-editado.pdf');
execFileSync('.venv/bin/python',['-c',`import sys
from pathlib import Path
from tests.test_cff_forms_mixed import cff_pdf,form_pdf,mixed_pdf
for name,data in zip(sys.argv[1:],[cff_pdf('cid'),form_pdf(),mixed_pdf()]):Path(name).write_bytes(data)`,cff,form,mixed]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:8000');
 async function edit(file,name){await page.getByLabel('Archivo PDF').setInputFiles(file);await expect(page.locator('.document-bar')).toContainText(name);await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: HELLO TEXT',exact:true}).first().click();const input=page.getByLabel('Texto sobre la página',{exact:true});await expect(input).toBeEnabled();await expect.poll(()=>input.evaluate(i=>i.selectionStart===i.selectionEnd)).toBe(true);await input.fill('HELLO TEX');await input.press('Control+Enter');await expect(input).toHaveCount(0);await expect(page.locator('.text-layer')).toContainText('HELLO TEX');}
 async function save(path){const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(path);}
 await edit(cff,'CFF.pdf');await page.getByRole('button',{name:/Deshacer/}).click();await expect(page.locator('.text-layer')).toContainText('HELLO TEXT');await page.getByRole('button',{name:/Rehacer/}).click();await save(cffOut);
 await edit(form,'Form.pdf');await save(formOut);
 await page.getByLabel('Archivo PDF').setInputFiles(mixed);await expect(page.locator('.document-bar')).toContainText('Mixto.pdf');await openTool(page,'Editar texto');await page.getByRole('button',{name:/^Editar en página: HELLO/}).click();await expect(page.getByLabel('Texto sobre la página',{exact:true})).toBeEnabled();await page.getByRole('button',{name:'Editar párrafo',exact:true}).click();await expect(page.getByLabel('Fragmento original 1',{exact:true})).toBeEnabled();await page.getByLabel('Alto del párrafo en página').fill('180');await page.getByLabel('Fragmento original 1',{exact:true}).fill('HELLO HELLO HELLO ');await page.getByLabel('Fragmento original 2',{exact:true}).fill('TEXT TEXT TEXT');await page.getByRole('button',{name:'Comprobar ajuste',exact:true}).click();await expect(page.getByRole('button',{name:'Aplicar párrafo en página',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Aplicar párrafo en página',exact:true}).click();await expect(page.getByLabel('Fragmento original 1',{exact:true})).toHaveCount(0);await save(mixedOut);
 execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 assert b[0].get_text().startswith('HELLO TEX');left=next(i for i in a[0].get_fonts() if i[4]=='Original');right=next(i for i in b[0].get_fonts() if i[4]=='Original');assert a.extract_font(left[0])[3]==b.extract_font(right[0])[3]
with f.open(sys.argv[3]) as a,f.open(sys.argv[4]) as b:
 assert b[0].get_text().splitlines()==['HELLO TEX','HELLO TEXT','ROOT TEXT'] and a[1].get_pixmap().samples==b[1].get_pixmap().samples
with f.open(sys.argv[5]) as d:
 styles={(s['font'],round(s['size']),s['color']) for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']!='UNCHANGED'};assert styles=={('Helvetica-Bold',18,0xcc0000),('Helvetica-Oblique',14,0x0000cc)} and 'UNCHANGED' in d[0].get_text()`,cff,cffOut,form,formOut,mixedOut]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: CFF CID edit with original program and undo/redo; selected shared Form occurrence edited without changing another occurrence/page; mixed original fonts/sizes/colors reflowed on page and exported.');
}finally{await browser.close();}
