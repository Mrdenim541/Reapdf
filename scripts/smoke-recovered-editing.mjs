import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-recovered-edit-'));
const source=join(root,'source.pdf'),output=join(root,'output.pdf');
const simple=process.env.REAPDF_SIMPLE_FONT==='1';
execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
d=f.open();p=d.new_page();p.insert_font(fontname='Original',fontfile='resources/fonts/DejaVuSans.ttf',set_simple=${simple?'True':'False'});p.insert_text((45,100),'Texto original largo',fontname='Original',fontsize=18);p.insert_text((45,250),'CONTENIDO CONSERVADO');d.save(sys.argv[1])`,source]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage();page.on('dialog',d=>d.message().startsWith('Cambiar de modo')?d.dismiss():d.accept());const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(source);await openTool(page,'Editar texto');
 await page.getByRole('button',{name:'Editar en página: Texto original largo',exact:true}).click();
 await expect(page.getByLabel('Texto sobre la página',{exact:true})).toBeEnabled();
 await expect(page.locator('#tool-properties')).toBeHidden();
 await page.getByLabel('Texto sobre la página',{exact:true}).fill('Texto nuevo');
 await page.getByLabel('Texto sobre la página',{exact:true}).press('Control+Enter');
 await expect(page.getByLabel('Texto sobre la página',{exact:true})).toHaveCount(0);
 await expect(page.locator('.text-layer')).toContainText('Texto nuevo');
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('Texto original largo');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('Texto nuevo');
 const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(output);
 execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as d:
 text=d[0].get_text();assert 'Texto nuevo' in text and 'Texto original largo' not in text and 'CONTENIDO CONSERVADO' in text
 assert any(font[1]=='ttf' for font in d[0].get_fonts())`,output]);
 if(errors.length)throw new Error(errors.join('\n'));
 console.log(`PASS: selección directa TrueType ${simple?'WinAnsi simple':'Identity-H'}, fuente original, vista previa, aplicar, deshacer/rehacer y exportar.`);
}finally{await browser.close();}
