import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {readFileSync,writeFileSync} from 'node:fs';
export async function runAutomationSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-recipe-source.pdf');execFileSync(python,['-c',`from pathlib import Path;from tests.test_batch_tools import source;import sys;Path(sys.argv[1]).write_bytes(source(pages=2))`,fixture]);
 await p.goto(baseUrl);await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);await openTool(p,'Recetas de trabajo');
 const review=p.getByRole('button',{name:'Revisar receta y documentos',exact:true}),download=p.getByRole('button',{name:'Descargar copias y manifiesto',exact:true});
 await expect(download).toBeDisabled();await p.getByLabel('Plantilla de receta',{exact:true}).selectOption('1');await p.getByLabel('Nombre de receta',{exact:true}).fill('Revisión personal');await p.getByRole('button',{name:'2. Pasos',exact:true}).click();await p.getByLabel('Texto de marca de receta',{exact:true}).fill('REVISADO');
 // Ordered steps are inspected server-side before any output.
 await p.getByLabel('Paso para añadir',{exact:true}).selectOption('protect');await p.getByRole('button',{name:'Añadir paso',exact:true}).click();await p.getByLabel('Subir paso 4',{exact:true}).click();await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await review.click();await expect(p.getByRole('alert')).toContainText('último paso');await p.getByRole('button',{name:'2. Pasos',exact:true}).click();await p.getByLabel('Bajar paso 3',{exact:true}).click();
 await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await p.getByLabel('Contraseña de apertura de receta',{exact:true}).fill('User-recipe-2026!');await p.getByLabel('Contraseña de propietario de receta',{exact:true}).fill('Owner-recipe-2026!');
 await p.getByRole('button',{name:'1. Receta',exact:true}).click();await p.getByRole('button',{name:'Guardar receta',exact:true}).click();await expect(p.locator('.automation-dialog')).toContainText('Receta guardada');
 let wait=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar receta JSON',exact:true}).click();const rp=join(tmpdir(),'reapdf-recipe-export.json');await(await wait).saveAs(rp);const recipe=JSON.parse(readFileSync(rp,'utf8'));assert.equal(recipe.steps.length,4);assert.equal(recipe.steps[3].type,'protect');assert.ok(!readFileSync(rp,'utf8').includes('recipe-2026'));
 const stored=await p.evaluate(()=>localStorage.getItem('reapdf.recipes.v1'));assert.ok(stored.includes('Revisión personal')&&!stored.includes('recipe-2026'));
 await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await p.getByLabel('PDF adicionales de receta',{exact:true}).setInputFiles(fixture);await expect(p.getByRole('dialog')).toContainText('2 documentos · 4 páginas');await review.click();await expect(p.getByAltText('Primera página de resultado 1',{exact:true})).toBeVisible();await expect(download).toBeDisabled();await p.getByLabel('Aceptar resultados de receta',{exact:true}).check();await expect(download).toBeEnabled();
 await p.getByRole('button',{name:'2. Pasos',exact:true}).click();await p.getByLabel('Inicio de numeración de receta',{exact:true}).fill('20');await expect(download).toBeDisabled();await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await review.click();await expect(p.locator('.automation-dialog')).toContainText('Revisión vigente');await expect(p.getByLabel('Aceptar resultados de receta',{exact:true})).not.toBeChecked();await p.getByLabel('Aceptar resultados de receta',{exact:true}).check();
 await p.locator('.automation-dialog').evaluate(el=>{el.scrollTop=0;});await p.screenshot({path:join(tmpdir(),'reapdf-recetas-resultados-035.png')});
 wait=p.waitForEvent('download');await download.click();const zip=join(tmpdir(),'reapdf-recipe-results.zip');await(await wait).saveAs(zip);
 execFileSync(python,['-c',`import sys,json,hashlib,pymupdf as f;from zipfile import ZipFile
with ZipFile(sys.argv[1]) as z:
 r=json.loads(z.read('manifest.json'));assert len(r['documents'])==2;assert len(z.namelist())==3
 assert 'User-recipe' not in str(r) and 'Owner-recipe' not in str(r)
 for row in r['documents']:
  data=z.read(row['file']);assert hashlib.sha256(data).hexdigest()==row['output_sha256'];assert 'preview' not in row
  with f.open(stream=data) as d:
   assert d.needs_pass and d.authenticate('User-recipe-2026!');assert 'REVISADO' in d[0].get_text();assert '20' in d[0].get_text() and '21' in d[1].get_text()
 assert len(set(z.namelist()))==3`,zip]);
 await p.getByRole('button',{name:'Cerrar',exact:true}).click();await expect(p.locator('.document-bar')).toContainText('0 cambios');
 // A saved recipe survives reload, but credentials do not.
 await p.reload();await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);await openTool(p,'Recetas de trabajo');await p.getByLabel('Recetas guardadas',{exact:true}).selectOption('0');await expect(p.getByLabel('Nombre de receta',{exact:true})).toHaveValue('Revisión personal');await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await expect(p.getByLabel('Contraseña de apertura de receta',{exact:true})).toHaveValue('');await p.getByRole('button',{name:'1. Receta',exact:true}).click();
 // Import is validated; unknown fields and credentials cannot be stored.
 const bad=join(tmpdir(),'reapdf-invalid-recipe.json');writeFileSync(bad,JSON.stringify({...recipe,password:'never-store-me'}));await p.getByLabel('Importar receta JSON',{exact:true}).setInputFiles(bad);await expect(p.getByRole('alert')).toContainText('Receta no compatible');await p.getByLabel('Importar receta JSON',{exact:true}).setInputFiles(rp);await expect(p.locator('.automation-dialog')).toContainText('Receta importada');
 // Text recipe produces a real TXT, rather than accidentally a PDF or preview.
 await p.getByLabel('Plantilla de receta',{exact:true}).selectOption('3');await p.getByRole('button',{name:'3. Documentos',exact:true}).click();await review.click();await expect(p.locator('.automation-dialog')).toContainText('Revisión vigente');await expect(p.getByAltText('Primera página de resultado 1',{exact:true})).toHaveCount(0);await p.getByLabel('Aceptar resultados de receta',{exact:true}).check();wait=p.waitForEvent('download');await download.click();const textZip=join(tmpdir(),'reapdf-recipe-text.zip');await(await wait).saveAs(textZip);execFileSync(python,['-c',`import sys,json;from zipfile import ZipFile
with ZipFile(sys.argv[1]) as z:
 row=json.loads(z.read('manifest.json'))['documents'][0];assert row['file'].endswith('.txt');assert 'Documento de prueba' in z.read(row['file']).decode('utf-8')`,textZip]);
 await p.getByRole('button',{name:'Cerrar',exact:true}).click();
 // The same editor works on a narrower window without horizontal overflow.
 await p.setViewportSize({width:600,height:900});await openTool(p,'Recetas de trabajo');await p.getByLabel('Plantilla de receta',{exact:true}).selectOption('1');await p.locator('.automation-dialog').evaluate(el=>{el.scrollTop=0;});await expect(p.getByRole('dialog')).toBeVisible();assert.ok(await p.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1));await p.screenshot({path:join(tmpdir(),'reapdf-recetas-compacto-035.png')});await context.close();
}
