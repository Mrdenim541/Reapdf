import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runImportedHandlesSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 for(const rotation of [0,90,180,270]){
  const fixture=join(tmpdir(),`reapdf-imported-handles-${rotation}.pdf`);execFileSync(python,['-c',`import sys,pymupdf as f
from tests.test_imported_paths import source
with f.open(stream=source(int(sys.argv[2]),True)) as d:
 p=d[0];a=p.add_line_annot((230,200),(320,260));a.set_line_ends(f.PDF_ANNOT_LE_CIRCLE,f.PDF_ANNOT_LE_CLOSED_ARROW);a.set_border(width=2,dashes=[3,2]);a.set_opacity(.6);a.update();d.save(sys.argv[1])`,fixture,String(rotation)]);
  await p.goto(baseUrl);await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);await openTool(p,'Seleccionar marca');const options=await p.getByLabel('Anotación existente',{exact:true}).locator('option').evaluateAll(nodes=>nodes.map(n=>({value:n.value,text:n.textContent})));const ink=options.find(o=>o.text.includes('Lápiz')),line=options.find(o=>o.text.includes('Línea'));
  await p.getByLabel('Anotación existente',{exact:true}).selectOption(ink.value);await p.getByLabel('Nivel de zoom').selectOption('75');await expect(p.getByLabel('Tirador para mover trazado importado',{exact:true})).toBeVisible();
  const drag=async(name,dx,dy,cancel=false)=>{
   const h=p.getByRole('button',{name,exact:true});await h.scrollIntoViewIfNeeded();const r=await h.boundingBox();
   await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.down();await p.mouse.move(r.x+r.width/2+dx,r.y+r.height/2+dy,{steps:7});
   await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeDisabled();await expect(p.locator('.transform-handles polyline')).toHaveCount(2);
   if(cancel)await p.keyboard.press('Escape');await p.mouse.up();
  };
  const x=Number(await p.getByLabel('Posición X de marca existente',{exact:true}).inputValue()),y=Number(await p.getByLabel('Posición Y de marca existente',{exact:true}).inputValue());
  await drag('Tirador para mover trazado importado',15,9,true);await expect(p.locator('.document-bar')).toContainText('0 cambios');await expect(p.getByLabel('Posición X de marca existente',{exact:true})).toHaveValue(String(x));
  await drag('Tirador para mover trazado importado',15,9);await expect(p.locator('.document-bar')).toContainText('1 cambios');await expect(p.getByLabel('Posición X de marca existente',{exact:true})).toHaveValue(String(x+20));await expect(p.getByLabel('Posición Y de marca existente',{exact:true})).toHaveValue(String(y+12));
  const w=Number(await p.getByLabel('Ancho de marca existente',{exact:true}).inputValue()),h=Number(await p.getByLabel('Alto de marca existente',{exact:true}).inputValue());
  await drag('Redimensionar trazado importado',15,9);await expect(p.getByLabel('Ancho de marca existente',{exact:true})).toHaveValue(String(w+20));await expect(p.getByLabel('Alto de marca existente',{exact:true})).toHaveValue(String(h+12));
  // Keyboard handles use the same native geometry and do not flatten the mark.
  await p.getByRole('button',{name:'Redimensionar trazado importado',exact:true}).focus();await p.keyboard.press('ArrowRight');await expect(p.getByLabel('Ancho de marca existente',{exact:true})).toHaveValue(String(w+21));
  await p.getByRole('button',{name:'Tirador para mover trazado importado',exact:true}).focus();await p.keyboard.press('Shift+ArrowDown');await expect(p.getByLabel('Posición Y de marca existente',{exact:true})).toHaveValue(String(y+22));
  await p.getByRole('button',{name:/Deshacer/}).click();await expect(p.getByLabel('Posición Y de marca existente',{exact:true})).toHaveValue(String(y+12));await p.getByRole('button',{name:/Rehacer/}).click();await expect(p.getByLabel('Posición Y de marca existente',{exact:true})).toHaveValue(String(y+22));
  await p.getByLabel('Anotación existente',{exact:true}).selectOption(line.value);const lineW=Number(await p.getByLabel('Ancho de marca existente',{exact:true}).inputValue());await p.getByLabel('Ancho de marca existente',{exact:true}).fill(String(lineW+15));await expect(p.getByRole('button',{name:'Redimensionar trazado importado',exact:true})).toHaveCount(0);await p.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();await expect(p.getByRole('button',{name:'Redimensionar trazado importado',exact:true})).toBeVisible();
  let download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const out=join(tmpdir(),`reapdf-imported-handles-result-${rotation}.pdf`);await(await download).saveAs(out);
  execFileSync(python,['-c',`import sys,pymupdf as f
from backend.path_geometry import path_box
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 p=a[0];q=b[0];old=list(p.annots());new=list(q.annots());assert p.rotation==q.rotation and p.cropbox==q.cropbox
 original=path_box(p,old[0]);actual=path_box(q,new[0]);assert abs(actual[0]-original[0]-20)<.01 and abs(actual[1]-original[1]-22)<.01;assert abs((actual[2]-actual[0])-(original[2]-original[0])-21)<.01;assert abs((actual[3]-actual[1])-(original[3]-original[1])-12)<.01
 r=path_box(q,new[2]);s=path_box(p,old[2]);assert abs((r[2]-r[0])-(s[2]-s[0])-15)<.01
 for i in [0,2]:assert old[i].info==new[i].info and old[i].border==new[i].border and old[i].line_ends==new[i].line_ends and old[i].opacity==new[i].opacity
 assert p.get_text()==q.get_text();assert a[1].get_pixmap().samples==b[1].get_pixmap().samples`,fixture,out]);
  if(rotation===0){await p.screenshot({path:join(tmpdir(),'reapdf-tiradores-importados-033.png')});download=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).last().click();const project=join(tmpdir(),'reapdf-imported-handles.reapdf');await(await download).saveAs(project);execFileSync(python,['-c',`import sys;from pathlib import Path
from backend.projects import read_project
b,ops,_=read_project(Path(sys.argv[1]).read_bytes());assert len(ops)==2 and all('path_rect' in op['changes'] for op in ops)`,project]);await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await openTool(p,'Seleccionar marca');await p.getByLabel('Anotación existente',{exact:true}).selectOption(ink.value);await expect(p.getByLabel('Ancho de marca existente',{exact:true})).toHaveValue(String(w+21));}
 }
 // Standard horizontal lines resize along their nonzero dimension only.
 const axis=join(tmpdir(),'reapdf-imported-horizontal.pdf');execFileSync(python,['-c',`import sys;from pathlib import Path;from tests.test_imported_resize import axis_source;Path(sys.argv[1]).write_bytes(axis_source('horizontal',0))`,axis]);await p.goto(baseUrl);await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(axis);await openTool(p,'Seleccionar marca');await p.getByLabel('Anotación existente',{exact:true}).selectOption({index:1});await expect(p.getByLabel('Alto de marca existente',{exact:true})).toBeDisabled();await p.getByRole('button',{name:'Redimensionar trazado importado',exact:true}).focus();await p.keyboard.press('ArrowRight');await expect(p.getByLabel('Ancho de marca existente',{exact:true})).toHaveValue('101');await expect(p.getByLabel('Alto de marca existente',{exact:true})).toHaveValue('0');
 assert.equal(errors.length,0);await context.close();
}
