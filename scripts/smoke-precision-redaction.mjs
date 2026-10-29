import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runPrecisionRedactionSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-precision-redaction-source.pdf');execFileSync(python,['-c',`from pathlib import Path;import sys
from tests.test_redaction_search import source
Path(sys.argv[1]).write_bytes(source())`,fixture]);
 await p.goto(baseUrl);const uploaded=p.waitForResponse(r=>r.url().endsWith('/api/documents')&&r.request().method()==='POST');await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);const doc=await(await uploaded).json();await p.getByAltText('Página 1 del documento').waitFor();
 await openTool(p,'Resaltar');await p.getByLabel('Precisión de selección').selectOption('characters');
 const r=await p.request.post(`${baseUrl}/api/documents/${doc.id}/pages/0/text`,{data:{operations:[]}}),data=await r.json(),chars=data.characters.slice(1,4);
 const box=await p.getByLabel('Lienzo de anotaciones').boundingBox(),screen=([x,y])=>[box.x+x/doc.pages[0].width*box.width,box.y+y/doc.pages[0].height*box.height];
 const a=[chars[0].quad[0][0]+.5,(chars[0].quad[0][1]+chars[0].quad[2][1])/2],b=[chars.at(-1).quad[1][0]-.5,a[1]];
 await p.mouse.move(...screen(a));await p.mouse.down();await p.mouse.move(...screen(b),{steps:8});await expect(p.locator('polygon')).toHaveCount(1);await p.mouse.up();await expect(p.locator('.document-bar')).toContainText('1 cambios');await expect(p.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await p.screenshot({path:join(tmpdir(),'reapdf-seleccion-precisa-031.png')});let download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const marked=join(tmpdir(),'reapdf-partial-mark-result.pdf');await(await download).saveAs(marked);
 execFileSync(python,['-c',`import sys,pymupdf as f
from backend.review import review_selection
with f.open(sys.argv[1]) as d:
 p=d[0];a=next(p.annots());chars=review_selection(p)['characters'][1:4];assert ''.join(c['text'] for c in chars)=='ecr';assert len(a.vertices)==4;assert abs(a.vertices[0][0]-chars[0]['quad'][0][0])<.01;assert abs(a.vertices[1][0]-chars[-1]['quad'][1][0])<.01;assert 'Secret-93847 KEEP-58291' in p.get_text()`,marked]);
 await p.getByRole('button',{name:/Deshacer/}).click();await expect(p.locator('.document-bar')).toContainText('0 cambios');
 await openTool(p,'Censurar y sanear copia');await p.getByLabel('Método de censura').selectOption('search');await p.getByLabel('Términos para censurar').fill('Secret-93847');await p.getByLabel('Buscar correos para censurar').check();await p.getByLabel('Páginas de búsqueda para censura').fill('1-2');await p.getByRole('button',{name:'Buscar coincidencias para censura',exact:true}).click();
 await expect(p.getByRole('region',{name:'Resultados de búsqueda para censura'})).toContainText('6 coincidencias encontradas · 0 elegidas');await p.getByLabel('Censurar coincidencia 1',{exact:true}).check();await p.getByLabel('Censurar coincidencia 5',{exact:true}).check();await p.getByLabel('Confirmar alcance de copia censurada').check();
 await p.getByRole('button',{name:'Vista previa de censura',exact:true}).click();await expect(p.getByRole('dialog')).toContainText('1 de 2 páginas afectadas revisadas');await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeDisabled();await p.getByLabel('Página para revisar censura').selectOption('1');await p.getByRole('button',{name:'Vista previa de censura',exact:true}).click();await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeEnabled();
 // Any change invalidates every page, even if the same selection is restored.
 await p.getByLabel('Censurar coincidencia 6',{exact:true}).check();await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeDisabled();await p.getByLabel('Censurar coincidencia 6',{exact:true}).uncheck();await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Vista previa de censura',exact:true}).click();await p.getByLabel('Página para revisar censura').selectOption('0');await p.getByRole('button',{name:'Vista previa de censura',exact:true}).click();await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeEnabled();
 await p.screenshot({path:join(tmpdir(),'reapdf-busqueda-censura-031.png')});download=p.waitForEvent('download');await p.getByRole('button',{name:'Descargar PDF censurado',exact:true}).click();const output=join(tmpdir(),'reapdf-searched-redaction-result.pdf');await(await download).saveAs(output);
 execFileSync(python,['-c',`import sys,subprocess,pymupdf as f
with f.open(sys.argv[1]) as d:
 assert 'Secret-93847' not in d[0].get_text() and 'ana@example.org' in d[0].get_text();assert 'Secret-93847' in d[1].get_text() and 'ana@example.org' not in d[1].get_text();assert 'KEEP-58291' in d[0].get_text();assert 'secret-93847' in d[0].get_text();assert 'Secret-93847' in d[2].get_text()
t=subprocess.check_output(['pdftotext','-f','1','-l','1',sys.argv[1],'-']).decode();assert 'Secret-93847' not in t and 'KEEP-58291' in t`,output]);
 await p.getByLabel('Términos para censurar').fill('KEEP-58291');await expect(p.getByRole('region',{name:'Resultados de búsqueda para censura'})).toHaveCount(0);await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeDisabled();
 // Manual regions work across pages, with individual removal and review gating.
 await p.getByLabel('Método de censura').selectOption('manual');for(const [label,value] of [['X','50'],['Y','70'],['Ancho','320'],['Alto','45']])await p.getByLabel(`${label} de región censurada`,{exact:true}).fill(value);await p.getByRole('button',{name:'Añadir región a censura',exact:true}).click();await p.getByLabel('Página para revisar censura').selectOption('1');await p.getByRole('button',{name:'Añadir región a censura',exact:true}).click();await expect(p.getByRole('dialog')).toContainText('2 regiones preparadas en 2 páginas');await p.getByLabel('Eliminar región de censura 2',{exact:true}).click();await expect(p.getByRole('dialog')).toContainText('1 regiones preparadas en 1 páginas');await expect(p.getByRole('button',{name:'Descargar PDF censurado',exact:true})).toBeDisabled();
 await p.getByRole('button',{name:'Cerrar',exact:true}).click();await expect(p.locator('.text-layer')).toContainText('Secret-93847');await expect(p.locator('.document-bar')).toContainText('0 cambios');await context.close();
}
