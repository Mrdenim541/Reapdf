import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
export async function runWordSectionsSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(25000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const word=join(tmpdir(),'reapdf-word-sections-042.docx'),bad=join(tmpdir(),'reapdf-word-sections-unsupported-042.docx');
 execFileSync(python,['-c',`from pathlib import Path;import sys
from tests.test_docx_sections import fixture
Path(sys.argv[1]).write_bytes(fixture());Path(sys.argv[2]).write_bytes(fixture(kind='continuous'))`,word,bad]);
 await p.goto(baseUrl);await p.getByRole('button',{name:'Crear PDF desde Word',exact:true}).click();await p.getByLabel('Archivo Word para convertir',{exact:true}).setInputFiles(word);await p.getByRole('button',{name:'Convertir y revisar Word',exact:true}).click();
 await expect(p.getByLabel('Resumen de importación Word',{exact:true})).toContainText('3 secciones');await p.locator('.word-section-report summary').click();await expect(p.locator('.word-section-report')).toContainText('horizontal');await expect(p.locator('.word-section-report')).toContainText('210 × 297 mm');await expect(p.locator('.word-section-report')).toContainText('romana minúscula');await expect(p.locator('.word-section-report')).toContainText('numeración desde 1');
 let wait=p.waitForEvent('download');await p.getByRole('button',{name:'Descargar informe de importación Word',exact:true}).click();const reportFile=join(tmpdir(),'reapdf-word-sections-report-042.json');await(await wait).saveAs(reportFile);const report=JSON.parse(readFileSync(reportFile,'utf8'));assert.equal(report.section_count,3);assert.deepEqual(report.sections.map(s=>s.number_start),[3,4,1]);assert.ok(report.text_check_passed);
 await p.getByRole('dialog').evaluate(el=>el.scrollTop=0);await p.screenshot({path:join(tmpdir(),'reapdf-word-sections-042.png')});
 for(let i=0;i<3;i++){await p.getByLabel('Página de Word importado',{exact:true}).selectOption(String(i));await expect(p.getByLabel(`Revisé Word página ${i+1}`,{exact:true})).toBeEnabled();await p.getByLabel(`Revisé Word página ${i+1}`,{exact:true}).check();if(i===1){const dimensions=await p.getByAltText('Word convertido página 2',{exact:true}).evaluate(el=>({w:el.naturalWidth,h:el.naturalHeight}));assert.ok(dimensions.w>dimensions.h);}}
 await p.setViewportSize({width:600,height:900});assert.ok(await p.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1));await p.screenshot({path:join(tmpdir(),'reapdf-word-sections-mobile-042.png')});await p.setViewportSize({width:1440,height:1080});await p.getByLabel('Aceptar diferencias de importación Word',{exact:true}).check();await p.getByRole('button',{name:'Abrir PDF convertido',exact:true}).click();
 await expect(p.getByLabel('Ir a etiqueta de página',{exact:true})).toContainText('iii · pág. 1');await p.getByLabel('Ir a etiqueta de página',{exact:true}).selectOption('1');await expect(p.locator('.text-layer')).toContainText('Tabla horizontal');await expect(p.locator('.text-layer')).toContainText('Cabecera horizontal iv de 3');await p.getByLabel('Ir a etiqueta de página',{exact:true}).selectOption('2');await expect(p.locator('.text-layer')).toContainText('Cabecera horizontal 1 de 3');
 wait=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const pdf=join(tmpdir(),'reapdf-word-sections-042.pdf');await(await wait).saveAs(pdf);assert.equal(createHash('sha256').update(readFileSync(pdf)).digest('hex'),report.pdf_sha256);
 execFileSync(python,['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as d:
 assert [p.get_label() for p in d]==['iii','iv','1']
 assert d[1].rect.width>d[1].rect.height and d[2].rect.width<d[2].rect.height
 assert all(p.get_links() and not p.get_xobjects() for p in d)`,pdf]);
 wait=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).click();const project=join(tmpdir(),'reapdf-word-sections-042.reapdf');await(await wait).saveAs(project);execFileSync(python,['-c',`import sys,pymupdf as f;from pathlib import Path;from backend.projects import read_project
base,ops,_=read_project(Path(sys.argv[1]).read_bytes())
with f.open(stream=base) as d:assert [p.get_label() for p in d]==['iii','iv','1'] and d[1].rect.width>d[1].rect.height`,project]);
 await p.locator('.file-menu summary').click();await p.getByRole('button',{name:'Crear PDF desde Word',exact:true}).click();await p.getByLabel('Archivo Word para convertir',{exact:true}).setInputFiles(bad);await p.getByRole('button',{name:'Convertir y revisar Word',exact:true}).click();await expect(p.getByRole('dialog').getByRole('alert')).toContainText('página siguiente');await expect(p.getByRole('button',{name:'Abrir PDF convertido',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Cancelar',exact:true}).click();await expect(p.getByLabel('Ir a etiqueta de página',{exact:true})).toContainText('iv · pág. 2');await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await expect(p.getByLabel('Ir a etiqueta de página',{exact:true})).toContainText('iii · pág. 1');await context.close();
}
