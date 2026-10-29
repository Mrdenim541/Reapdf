import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-workspaces-')),source=join(root,'Origen.pdf'),target=join(root,'Destino.pdf'),layerPdf=join(root,'Capas.pdf'),pack=join(root,'Conjunto.reapdfset'),measured=join(root,'medido.pdf'),layerOut=join(root,'capas-result.pdf');
execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
+for name,repeat in [(sys.argv[1],False),(sys.argv[2],True)]:
+ with f.open() as d:
+  p=d.new_page(width=600,height=800);p.insert_text((40,80),'PLAN-01',fontsize=16)
+  if repeat:p.insert_text((40,160),'PLAN-01',fontsize=16)
+  d.save(name)
+with f.open() as d:
+ p=d.new_page();a=d.add_ocg('Capa A');b=d.add_ocg('Capa B',on=False);p.insert_text((40,80),'VISIBLE A',oc=a);p.insert_text((40,120),'VISIBLE B',oc=b);d.save(sys.argv[3])`.replaceAll('\n+','\n'),source,target,layerPdf]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];page.on('dialog',d=>d.accept());page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.getByLabel('Archivo PDF').setInputFiles(source);await openTool(page,'Vincular documentos');
 await page.getByLabel('PDF para vincular').setInputFiles(target);await expect(page.getByLabel('Documento de destino')).not.toHaveValue('');await page.getByRole('button',{name:'Buscar relaciones',exact:true}).click();
 await expect(page.getByRole('dialog').getByRole('status')).toContainText('1 identificadores comunes');await page.getByLabel('Identificador relacionado').selectOption('PLAN-01');
 await expect(page.getByRole('button',{name:'Crear vínculo revisado',exact:true})).toBeDisabled();await page.getByLabel('Aparición de destino').selectOption({index:2});
 await expect(page.getByRole('button',{name:'Crear vínculo revisado',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Crear vínculo revisado',exact:true}).click();
 await page.getByLabel('Navegar vínculo PLAN-01').click();await expect(page.getByAltText('Documento Origen, página 1')).toBeVisible();await expect(page.getByAltText('Documento Destino, página 1')).toBeVisible();
 for(const preview of await page.locator('.linked-documents .linked-preview').all()){const aligned=await preview.evaluate(node=>{const a=node.querySelector('img').getBoundingClientRect(),b=node.querySelector('svg').getBoundingClientRect();return Math.abs(a.x-b.x)<1&&Math.abs(a.y-b.y)<1&&Math.abs(a.width-b.width)<1&&Math.abs(a.height-b.height)<1;});if(!aligned)throw new Error('Anchor overlay differs from rendered page geometry');}
 let wait=page.waitForEvent('download');await page.getByRole('button',{name:'Guardar conjunto',exact:true}).click();await(await wait).saveAs(pack);
 await page.getByLabel('Conjunto para abrir').setInputFiles(pack);await expect(page.getByLabel('Navegar vínculo PLAN-01')).toBeVisible();await page.getByLabel('Navegar vínculo PLAN-01').click();await expect(page.getByAltText('Documento Destino, página 1')).toBeVisible();
 wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar PDF vinculado',exact:true}).click();await(await wait).saveAs(join(root,'Compilado.pdf'));execFileSync('.venv/bin/python',['-c',"import sys,pymupdf as f;d=f.open(sys.argv[1]);assert len(d)==2 and d[0].get_links()[0]['page']==1",join(root,'Compilado.pdf')]);await page.screenshot({path:join(tmpdir(),'reapdf-document-links.png')});await page.getByRole('dialog').getByRole('button',{name:'Cerrar',exact:true}).click();
 await openTool(page,'Medir planos');const svg=page.getByLabel('Puntos de medición sobre el plano');await expect(page.getByAltText('Plano para medir')).toBeVisible();
 async function point(x,y){const b=await svg.boundingBox();await svg.click({position:{x:x/600*b.width,y:y/800*b.height}});}
 await page.getByRole('button',{name:'Marcar dos puntos de referencia',exact:true}).click();await point(60,60);await point(210,60);await page.getByLabel('Distancia real de referencia').fill('10');await page.getByRole('button',{name:'Usar esta escala',exact:true}).click();
 await point(60,300);await point(135,300);await page.getByRole('button',{name:'Calcular medición',exact:true}).click();await expect(page.getByRole('dialog').getByRole('status')).toContainText('5.000 m');
 await page.screenshot({path:join(tmpdir(),'reapdf-measurement.png')});await page.getByRole('button',{name:'Guardar medición en PDF',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(measured);
 await openTool(page,'Medir planos');await expect(page.getByRole('dialog')).toContainText('Escala calibrada');await page.getByRole('dialog').getByRole('button',{name:'Cerrar',exact:true}).click();
 await page.getByLabel('Archivo PDF').setInputFiles(layerPdf);await openTool(page,'Capas del PDF');await expect(page.getByLabel('Capa Capa A')).toBeChecked();await expect(page.getByLabel('Capa Capa B')).not.toBeChecked();
 await page.getByLabel('Capa Capa A').uncheck();await page.getByLabel('Capa Capa B').check();await page.getByRole('button',{name:'Vista previa de capas',exact:true}).click();await expect(page.getByAltText('Visibilidad de capas')).toBeVisible();await page.getByRole('button',{name:'Guardar visibilidad',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(layerOut);
 execFileSync('.venv/bin/python',['-c',`import sys,pymupdf as f
+from backend.document_sets import read
+from backend.measurements import model
+from backend.layers import model as layers
+from pathlib import Path
+items,links,name=read(Path(sys.argv[1]).read_bytes());assert len(items)==2 and len(links)==1
+measure=model(Path(sys.argv[2]).read_bytes(),[],0);assert abs(measure['measurements'][0]['value']-5)<.01
+states=layers(Path(sys.argv[3]).read_bytes(),[])['layers'];assert {l['name']:l['visible'] for l in states}=={'Capa A':False,'Capa B':True}`.replaceAll('\n+','\n'),pack,measured,layerOut]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: ambiguous links explicitly resolved, portable set saved/reopened and navigated; calibrated measure saved/reopened; layer preview and persisted visibility.');
}finally{await browser.close();}
