import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';import {mkdtempSync,rmSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-search-curves-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python',file=n=>join(root,n);
execFileSync(python,['-c',`from pathlib import Path
import sys
from tests.test_wildcard_search import sample
from tests.test_measurement_paths import sample as curves,CAL
from backend.measurements import measure
p=Path(sys.argv[1]);(p/'Search.pdf').write_bytes(sample());(p/'Curves.pdf').write_bytes(measure(curves(),[],0,'distance',CAL['points'],CAL))`,root]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1700,height:1150}}),errors=[];page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(file('Search.pdf'));
 await openTool(page,'Buscar y reemplazar');let d=page.getByRole('dialog',{name:'Buscar y reemplazar',exact:true});await d.getByLabel('Modo de búsqueda',{exact:true}).selectOption('wildcard');await d.getByLabel('Texto a buscar',{exact:true}).fill('COD-?');await d.getByLabel('Reemplazar por',{exact:true}).fill('X');await d.getByLabel('Texto a buscar',{exact:true}).press('Enter');await expect(d.getByRole('status')).toContainText('3 coincidencias.');await d.getByRole('button',{name:'Siguiente',exact:true}).click();await d.getByRole('button',{name:'Revisar reemplazo actual',exact:true}).click();await d.getByRole('button',{name:'Aplicar reemplazos',exact:true}).click();await expect(d).toHaveCount(0);
 let download=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await download).saveAs(file('SearchEdited.pdf'));
 await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(file('Curves.pdf'));await openTool(page,'Medir planos');d=page.getByRole('dialog',{name:'Medir planos',exact:true});await d.getByLabel('Tipo de medición',{exact:true}).selectOption('perimeter');await d.getByRole('button',{name:'Seleccionar trazado del PDF',exact:true}).click();
 // Choose the circular outline at its actual visible left boundary, avoiding
 // the interior of the SVG polyline's bounding box.
 const svg=await d.getByLabel('Puntos de medición sobre el plano',{exact:true}).boundingBox();await page.mouse.click(svg.x+240/500*svg.width,svg.y+300/650*svg.height);
 await expect(d.getByLabel('Cerrar recorrido',{exact:true})).toBeChecked();await d.getByRole('button',{name:'Calcular medición',exact:true}).click();await expect(d.locator('.measurement-result')).toContainText('Margen por aproximación');await d.getByRole('button',{name:'Guardar medición en PDF',exact:true}).click();await expect(d).toHaveCount(0);download=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await download).saveAs(file('CurvesMeasured.pdf'));
 execFileSync(python,['-c',`import sys,pymupdf as f
from pathlib import Path
from backend.measurements import model
p=Path(sys.argv[1])
with f.open(p/'SearchEdited.pdf') as d:assert 'COD-1 X COD-3' in d[0].get_text()
r=next(r for r in model((p/'CurvesMeasured.pdf').read_bytes(),[],0)['measurements'] if r['kind']=='perimeter');assert r['trace_source_verified'] and r['approximation']['error_bound']>0 and r['points'][0]==r['points'][-1]
with f.open(p/'Curves.pdf') as a,f.open(p/'CurvesMeasured.pdf') as b:assert a[0].get_pixmap(annots=False).samples==b[0].get_pixmap(annots=False).samples and a[1].get_pixmap().samples==b[1].get_pixmap().samples`,root]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: Chromium wildcard Enter search/current-match review, original-font replacement and export; mouse selection of closed curve, bound shown, save/reopen and underlying plan/other page unchanged.');
}finally{await browser.close();rmSync(root,{recursive:true,force:true});}
