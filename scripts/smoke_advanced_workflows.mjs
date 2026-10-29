import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-advanced-')),form=join(root,'Formulario.pdf'),xml=join(root,'Datos.xfdf'),signed=join(root,'Firmado.pdf'),tagged=join(root,'Etiquetas.pdf'),mixed=join(root,'Mixto.pdf'),large=join(root,'A0.pdf'),copy=join(root,'copia.pdf'),tagOut=join(root,'etiquetas-result.pdf');
execFileSync('.venv/bin/python',['-c',`from pathlib import Path
import sys,pymupdf as f,xml.etree.ElementTree as E
from tests.test_xfdf_working_copy import source,signed as create_signed
from tests.test_structure_preflight_regions import tagged,mixed_scan
from backend import xfdf
base=source();Path(sys.argv[1]).write_bytes(base);data,_=xfdf.export(base,[]);tree=E.fromstring(data)
for node in tree.findall('./'+xfdf.tag('fields')+'/'+xfdf.tag('field')):
 if node.get('name')=='Nombre':node.find(xfdf.tag('value')).text='Actualizado'
Path(sys.argv[2]).write_bytes(E.tostring(tree));Path(sys.argv[3]).write_bytes(create_signed());Path(sys.argv[4]).write_bytes(tagged());Path(sys.argv[5]).write_bytes(mixed_scan())
with f.open() as d:d.new_page(width=2384,height=3370).insert_text((40,80),'PLANO A0');d.save(sys.argv[6])`,form,xml,signed,tagged,mixed,large]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(form);await openTool(page,'Intercambiar XFDF');await page.getByLabel('Archivo XFDF').setInputFiles(xml);await page.getByRole('button',{name:'Revisar importación XFDF',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('2 campos');await page.getByRole('button',{name:'Aplicar importación XFDF',exact:true}).click();await expect(page.locator('.text-layer')).toContainText('Actualizado');
 await page.getByLabel('Archivo PDF').setInputFiles(signed);await openTool(page,'Copia de trabajo sin firmas');await expect(page.getByRole('button',{name:'Crear copia editable identificada',exact:true})).toBeDisabled();await page.getByLabel('Aceptar copia sin firmas digitales').check();await page.getByRole('button',{name:'Crear copia editable identificada',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.document-bar')).toContainText('copia-trabajo.pdf');
 await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: Documento para firmar',exact:true}).click();await expect(page.getByLabel('Texto sobre la página',{exact:true})).toBeEnabled();await page.getByLabel('Texto sobre la página',{exact:true}).fill('Documento editable');await page.getByLabel('Texto sobre la página',{exact:true}).press('Control+Enter');await expect(page.locator('.text-layer')).toContainText('Documento editable');
 let wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(copy);
 await page.getByLabel('Archivo PDF').setInputFiles(tagged);await openTool(page,'Etiquetas y orden de lectura');let select=page.getByLabel('Etiqueta de estructura');await expect(select).toBeVisible();await expect(select.locator('option')).not.toHaveCount(1);const figure=await select.locator('option').evaluateAll(items=>items.find(o=>o.textContent.includes('Figure')).value);await select.selectOption(figure);await page.getByLabel('Alternativa de figura').fill('Esquema de prueba descrito');await page.getByRole('button',{name:'Guardar alternativa',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 await openTool(page,'Etiquetas y orden de lectura');select=page.getByLabel('Grupo del orden de lectura');await expect(select.locator('option')).not.toHaveCount(1);await select.selectOption({index:1});await page.getByLabel('Bajar etiqueta 1').click();await page.getByRole('button',{name:'Guardar orden de lectura',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(tagOut);
 await openTool(page,'Inspección de impresión');await page.getByRole('button',{name:'Inspeccionar PDF',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('1 páginas');await page.getByRole('dialog').getByRole('button',{name:'Cerrar',exact:true}).click();
 await page.getByLabel('Archivo PDF').setInputFiles(mixed);await openTool(page,'OCR de región');await page.getByRole('dialog').locator('summary').filter({hasText:'Área en puntos PDF'}).click();for(const [label,value] of [['X',40],['Y',150],['Ancho',400],['Alto',120]])await page.getByLabel(`${label} de región OCR`,{exact:true}).fill(String(value));await page.getByLabel('Idioma del OCR de región').selectOption('eng');await page.getByRole('button',{name:'Reconocer esta región',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0,{timeout:30000});await expect(page.locator('.text-layer')).toContainText('123');
 await page.getByLabel('Archivo PDF').setInputFiles(large);await expect(page.getByAltText('Página 1 del documento')).toBeVisible();await expect(page.locator('.page-dimensions')).toContainText('3370');await page.getByLabel('Nivel de zoom').selectOption('400');await expect(page.locator('.render-status')).toContainText('Resolución limitada',{timeout:20000});const pixels=await page.getByAltText('Página 1 del documento').evaluate(i=>i.naturalWidth*i.naturalHeight);if(pixels>24000000)throw new Error('Render exceeded pixel budget');
 execFileSync('.venv/bin/python',['-c',`from pathlib import Path
import sys,pymupdf as f
from backend.digital_signatures import verify_signatures
from backend.structure_editing import model
with f.open(sys.argv[1]) as d:assert d.get_sigflags()<=0 and 'Documento editable' in d[0].get_text()
assert verify_signatures(Path(sys.argv[2]).read_bytes(),[])['signatures'][0]['intact']
structure=model(Path(sys.argv[3]).read_bytes(),[]);assert [n['role'] for n in structure['nodes']]==['Document','P','Figure'] and structure['nodes'][-1]['alt']=='Esquema de prueba descrito'`,copy,signed,tagOut]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: XFDF fields preview/import, identified unsigned copy edited inline while signed original stays intact, figure alternative/reading order, print inspection, mixed-page region OCR and A0 zoom pixel budget.');
}finally{await browser.close();}
