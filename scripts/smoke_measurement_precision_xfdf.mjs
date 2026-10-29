import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-precision-')),source=join(root,'Plano.pdf'),annotations=join(root,'Marcas.pdf'),empty=join(root,'Destino.pdf'),saved=join(root,'Medicion.pdf'),edited=join(root,'Medicion-editada.pdf'),xml=join(root,'Marcas.xfdf'),imported=join(root,'Importado.pdf'),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
execFileSync(python,['-c',`from pathlib import Path
import sys
from tests.test_measurement_precision import source
from tests.test_xfdf_appearance import source as marks,blank
for p,data in zip(sys.argv[1:],[source(),marks(),blank()]):Path(p).write_bytes(data)`,source,annotations,empty]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1550,height:1100}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
 async function load(file,name){await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(file);await expect(page.locator('.document-bar')).toContainText(name);}
 async function save(path){const d=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await d).saveAs(path);}
 const svg=()=>page.getByLabel('Puntos de medición sobre el plano',{exact:true});
 async function point(x,y){await expect(svg()).toBeVisible();await svg().scrollIntoViewIfNeeded();const b=await svg().boundingBox();await page.mouse.click(b.x+x/500*b.width,b.y+y/600*b.height);}
 await load(source,'Plano.pdf');await openTool(page,'Medir planos');await page.getByRole('button',{name:'Marcar dos puntos de referencia',exact:true}).click();await point(41,81);await point(199,81);await page.getByLabel('Distancia real de referencia',{exact:true}).fill('16');await page.getByRole('button',{name:'Usar esta escala',exact:true}).click();
 await page.getByText('Guardar una escala por región',{exact:true}).click();await page.getByLabel('Nombre de escala regional',{exact:true}).fill('Detalle A');for(const [name,value] of [['X',20],['Y',40],['Ancho',220],['Alto',240]])await page.getByLabel(`${name} de región de escala`,{exact:true}).fill(String(value));await page.getByRole('button',{name:'Guardar escala regional',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 await openTool(page,'Medir planos');await point(41,81);await point(199,81);await expect(page.getByLabel('Escala de trabajo',{exact:true})).not.toHaveValue('');await page.getByRole('button',{name:'Calcular medición',exact:true}).click();await expect(page.locator('.measurement-result')).toContainText('16.000 m');await page.getByRole('button',{name:'Guardar medición en PDF',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await save(saved);
 await openTool(page,'Medir planos');await page.getByText('Mediciones guardadas (1)',{exact:true}).click();await page.getByRole('button',{name:/^Editar medición /}).click();await expect(page.getByLabel('Tipo de medición',{exact:true})).toBeDisabled();await svg().scrollIntoViewIfNeeded();const b=await svg().boundingBox();await page.mouse.move(b.x+200/500*b.width,b.y+80/600*b.height);await page.mouse.down();await page.mouse.move(b.x+200/500*b.width,b.y+250/600*b.height,{steps:8});await page.mouse.up();await expect(page.getByLabel('Y del vértice seleccionado',{exact:true})).toHaveValue('250');await page.getByRole('button',{name:'Calcular medición',exact:true}).click();await expect(page.locator('.measurement-result')).toContainText('23.345 m');await page.getByRole('button',{name:'Guardar cambios de medición',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await save(edited);await page.getByRole('button',{name:/Deshacer/}).click();await page.getByRole('button',{name:/Rehacer/}).click();
 await load(annotations,'Marcas.pdf');await openTool(page,'Intercambiar XFDF');let download=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar XFDF',exact:true}).click();await(await download).saveAs(xml);await expect(page.getByRole('dialog')).toContainText('Exportadas 5 anotaciones');await page.getByRole('button',{name:'Cerrar',exact:true}).click();
 await load(empty,'Destino.pdf');await openTool(page,'Intercambiar XFDF');await page.getByLabel('Archivo XFDF',{exact:true}).setInputFiles(xml);await page.getByLabel('Confirmar correspondencia del PDF',{exact:true}).check();await page.getByRole('button',{name:'Revisar importación XFDF',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('Se importarán 5 anotaciones');await page.getByRole('button',{name:'Aplicar importación XFDF',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await save(imported);
 execFileSync(python,['-c',`import sys,math,pymupdf as f
from pathlib import Path
from backend.measurements import model
from backend.xfdf import export
left=model(Path(sys.argv[1]).read_bytes(),[],0);right=model(Path(sys.argv[2]).read_bytes(),[],0);assert left['measurements'][0]['id']==right['measurements'][0]['id'];assert left['measurements'][0]['value']==16;assert abs(right['measurements'][0]['value']-math.hypot(160,170)*.1)<1e-5;assert right['measurements'][0]['points']==[[40,80],[200,250]] and len(right['scales'])==1
with f.open(sys.argv[2]) as d:assert len(list(d[0].annots()))==2 and 'PRESERVED' in d[0].get_text()
_,report=export(Path(sys.argv[3]).read_bytes(),[]);assert report['annotations']==5 and not report['skipped_annotations']`,saved,edited,imported]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: vector snapping, saved regional scale, automatic scale choice, distance calculation, vertex drag/edit with stable identity and label, export/undo/redo; extended XFDF exported, reviewed, imported and independently reread.');
}finally{await browser.close();}
