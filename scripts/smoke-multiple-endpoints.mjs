import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runMultipleEndpointsSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-multiple-endpoints.pdf');execFileSync(python,['-c',`import sys,pymupdf as f
with f.open() as d:
 p=d.new_page(width=500,height=650);p.insert_text((50,70),'Contenido conservado')
 a=p.add_line_annot((80,150),(190,150));a.set_line_ends(f.PDF_ANNOT_LE_CIRCLE,f.PDF_ANNOT_LE_CLOSED_ARROW);a.set_colors(stroke=(.2,.4,.6));a.set_border(width=2);a.update()
 p.add_rect_annot(f.Rect(90,260,150,300)).update();p.add_rect_annot(f.Rect(240,300,300,340)).update();p.add_rect_annot(f.Rect(350,360,410,400)).update();d.new_page().insert_text((50,70),'Otra pagina');d.save(sys.argv[1])`,fixture]);
 await p.goto(baseUrl);const upload=p.waitForResponse(r=>r.url().endsWith('/api/documents')&&r.request().method()==='POST');await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);const doc=await(await upload).json();await openTool(p,'Seleccionar marca');await p.getByLabel('Anotación existente',{exact:true}).selectOption({index:1});await p.getByRole('button',{name:'Editar extremos',exact:true}).click();await expect(p.getByRole('button',{name:'Mover extremo final de línea',exact:true})).toBeVisible();
 const dragEnd=async(cancel)=>{const h=p.getByRole('button',{name:'Mover extremo final de línea',exact:true}),r=await h.boundingBox();await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.down();await p.mouse.move(r.x+r.width/2+30,r.y+r.height/2+40,{steps:7});await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeDisabled();if(cancel)await p.keyboard.press('Escape');await p.mouse.up();};
 await dragEnd(true);await expect(p.locator('.document-bar')).toContainText('0 cambios');await dragEnd(false);await expect(p.getByLabel('Final X de línea',{exact:true})).toHaveValue('220');await expect(p.getByLabel('Final Y de línea',{exact:true})).toHaveValue('190');
 await p.getByRole('button',{name:'Mover extremo inicial de línea',exact:true}).focus();await p.keyboard.press('Shift+ArrowDown');await expect(p.getByLabel('Inicio Y de línea',{exact:true})).toHaveValue('160');await p.getByRole('button',{name:/Deshacer/}).click();await expect(p.getByLabel('Inicio Y de línea',{exact:true})).toHaveValue('150');await p.getByRole('button',{name:/Rehacer/}).click();await expect(p.getByLabel('Inicio Y de línea',{exact:true})).toHaveValue('160');
 await p.screenshot({path:join(tmpdir(),'reapdf-extremos-034.png')});
 await p.getByRole('button',{name:'Ajustar caja',exact:true}).click();const width=Number(await p.getByLabel('Ancho de marca existente',{exact:true}).inputValue());await p.getByLabel('Ancho de marca existente',{exact:true}).fill(String(width+20));await p.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();await expect(p.getByLabel('Ancho de marca existente',{exact:true})).toHaveValue(String(width+20));await p.getByRole('button',{name:'Editar extremos',exact:true}).click();await expect(p.getByLabel('Final X de línea',{exact:true})).toHaveValue('240');await expect(p.getByLabel('Inicio X de línea',{exact:true})).toHaveValue('80');
 const metadata=await(await p.request.get(`${baseUrl}/api/documents/${doc.id}/pages/0`)).json(),rectangles=metadata.annotations.filter(a=>a.label==='Rectángulo');
 await p.getByRole('button',{name:'Selección múltiple',exact:true}).click();for(const a of rectangles)await p.getByLabel(`Seleccionar marca ${a.xref} en grupo`,{exact:true}).check();await expect(p.getByRole('heading',{name:'3 marcas seleccionadas',exact:true})).toBeVisible();
 await p.getByRole('button',{name:'Alinear marcas: Arriba',exact:true}).click();await expect(p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true})).toBeVisible();
 await p.getByRole('button',{name:'Distribuir marcas: Horizontal',exact:true}).click();await expect(p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true})).toBeVisible();
 const moveGroup=async(cancel)=>{const h=p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true}),r=await h.boundingBox();await p.mouse.move(r.x+r.width/2,r.y+r.height/2);await p.mouse.down();await p.mouse.move(r.x+r.width/2+6,r.y+r.height/2+4,{steps:5});await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeDisabled();if(cancel)await p.keyboard.press('Escape');await p.mouse.up();};
 await moveGroup(true);await expect(p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true})).toBeVisible();await moveGroup(false);await expect(p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true})).toBeVisible();
 await p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true}).focus();await p.keyboard.press('ArrowDown');await expect(p.getByRole('button',{name:'Tirador para mover grupo de anotaciones',exact:true})).toBeVisible();
 await p.getByLabel('Desplazamiento X del grupo',{exact:true}).fill('10');await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeDisabled();await expect(p.getByRole('button',{name:'Alinear marcas: Arriba',exact:true})).toBeDisabled();await p.getByLabel('Cambiar color de selección',{exact:true}).check();await p.getByLabel('Color de selección múltiple',{exact:true}).fill('#246951');await p.getByRole('button',{name:'Aplicar cambios al grupo',exact:true}).click();await expect(p.getByLabel('Desplazamiento X del grupo',{exact:true})).toHaveValue('0');await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeEnabled();
 await expect(p.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();await p.locator('.properties').evaluate(el=>{el.scrollTop=0;});await p.screenshot({path:join(tmpdir(),'reapdf-seleccion-multiple-034.png')});
 let download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const out=join(tmpdir(),'reapdf-multiple-endpoints-result.pdf');await(await download).saveAs(out);
 execFileSync(python,['-c',`import sys,pymupdf as f
from backend.path_geometry import visible_paths
with f.open(sys.argv[1]) as d:
 p=d[0];ann=list(p.annots());ends=visible_paths(p,ann[0])[0];assert ends==[[80,160],[240,190]];rects=[a.rect for a in ann[1:]];assert max(r.y0 for r in rects)-min(r.y0 for r in rects)<.01
 gaps=[rects[i+1].x0-rects[i].x1 for i in range(2)];assert abs(gaps[0]-gaps[1])<.01
 for a in ann[1:]:assert all(abs(a.colors['stroke'][i]-[36/255,105/255,81/255][i])<.001 for i in range(3))
 assert 'Contenido conservado' in p.get_text() and len(d)==2`,out]);
 await p.getByRole('button',{name:'Eliminar 3 marcas seleccionadas',exact:true}).click();await expect(p.getByRole('heading',{name:'0 marcas seleccionadas',exact:true})).toBeVisible();await p.getByRole('button',{name:/Deshacer/}).click();await expect(p.getByRole('heading',{name:'3 marcas seleccionadas',exact:true})).toBeVisible();
 download=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).last().click();const project=join(tmpdir(),'reapdf-multiple-endpoints.reapdf');await(await download).saveAs(project);execFileSync(python,['-c',`import sys;from pathlib import Path;from backend.projects import read_project;from backend.engine import export_pdf
base,ops,_=read_project(Path(sys.argv[1]).read_bytes());assert len(ops)==4 and 'line_points' in ops[0]['changes'];export_pdf(base,ops)`,project]);
 await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await openTool(p,'Seleccionar marca');await p.getByLabel('Anotación existente',{exact:true}).selectOption({index:1});await p.getByRole('button',{name:'Editar extremos',exact:true}).click();await expect(p.getByLabel('Final X de línea',{exact:true})).toHaveValue('240');
 assert.equal(errors.length,0);await context.close();
}
