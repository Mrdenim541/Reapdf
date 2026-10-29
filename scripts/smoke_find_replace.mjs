import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-find-replace-')),source=join(root,'original.pdf'),out=join(root,'result.pdf');
execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
d=f.open();d.new_page().insert_text((40,80),'REG-01 REG-01',fontsize=18);d.new_page().insert_text((40,80),'REG-01',fontsize=18);d.save(sys.argv[1])`,source]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage();page.on('dialog',d=>d.accept());const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(source);await openTool(page,'Buscar y reemplazar');
 await page.getByRole('dialog').getByRole('button',{name:'Cancelar',exact:true}).click();await page.keyboard.press('Control+h');await expect(page.getByRole('dialog',{name:'Buscar y reemplazar'})).toBeVisible();
 await page.getByLabel('Texto a buscar').fill('REG-01');await page.getByLabel('Reemplazar por',{exact:true}).fill('R-1');
 await page.getByLabel('Ámbito de búsqueda').selectOption('range');await page.getByLabel('Rango de páginas').fill('2');
 await page.getByRole('button',{name:'Buscar coincidencias',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('1 coincidencias');
 await page.getByLabel('Ámbito de búsqueda').selectOption('document');await page.getByRole('button',{name:'Buscar coincidencias',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('3 coincidencias');
 await page.getByRole('button',{name:'Seleccionar todas compatibles',exact:true}).click();await expect(page.getByRole('button',{name:'Aplicar reemplazos',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Preparar vista previa',exact:true}).click();await expect(page.getByRole('button',{name:'Aplicar reemplazos',exact:true})).toBeEnabled();
 await expect(page.getByAltText('Reemplazo en página 1')).toBeVisible();
 await page.screenshot({path:join(tmpdir(),'reapdf-find-replace.png')});
 await page.getByLabel('Reemplazar por',{exact:true}).fill('X');await expect(page.getByRole('button',{name:'Aplicar reemplazos',exact:true})).toBeDisabled();
 await page.getByLabel('Reemplazar por',{exact:true}).fill('R-1');await page.getByRole('button',{name:'Preparar vista previa',exact:true}).click();await expect(page.getByRole('button',{name:'Aplicar reemplazos',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Aplicar reemplazos',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.text-layer')).toContainText('R-1 R-1');
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('REG-01 REG-01');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(page.locator('.text-layer')).toContainText('R-1 R-1');
 const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(out);
 execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as d:assert d[0].get_text().strip()=='R-1 R-1' and d[1].get_text().strip()=='R-1'`,out]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: ranged/document search, selection, preview invalidation, batch replace, undo/redo and exported PDF.');
}finally{await browser.close();}
