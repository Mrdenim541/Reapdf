import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runProfessionalSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-professional-source.pdf');execFileSync(python,['-c',`import sys,pymupdf as f
from tests.test_imported_paths import source
with f.open(stream=source(crop=True)) as d:
 p=d[0];a=p.add_line_annot((230,200),(300,260));a.set_line_ends(0,f.PDF_ANNOT_LE_CLOSED_ARROW);a.update();d.save(sys.argv[1])`,fixture]);
 await p.goto(baseUrl);await p.screenshot({path:join(tmpdir(),'reapdf-inicio-profesional-032.png')});
 await p.getByLabel('Archivo PDF',{exact:true}).setInputFiles(fixture);await expect(p.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();

 // Readability checks use the rendered colours, including inherited surfaces.
 const contrast=await p.evaluate(()=>{
  const rgb=value=>value.match(/[\d.]+/g).map(Number);
  const light=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  return ['.header-actions .primary','.catalog-heading h2','.area-description','.tool-section summary'].map(selector=>{
   const el=document.querySelector(selector);const front=rgb(getComputedStyle(el).color);let node=el,back;
   while(node){const c=rgb(getComputedStyle(node).backgroundColor);if(c.length<4||c[3]===1){back=c;break;}node=node.parentElement;}
   const a=light(front),b=light(back||[255,255,255]);return {selector,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
  });
 });for(const c of contrast)assert.ok(c.ratio>=4.5,`${c.selector} contraste ${c.ratio}`);
 await p.getByRole('tab',{name:'Comentar',exact:true}).click();await expect(p.locator('.catalog-action small:visible')).toHaveCount(0);await p.locator('.tool-section summary').filter({hasText:'Dibujar'}).click();await expect(p.getByRole('button',{name:'Lápiz',exact:true})).toBeHidden();await p.locator('.tool-section summary').filter({hasText:'Dibujar'}).focus();await p.keyboard.press('Enter');await expect(p.getByRole('button',{name:'Lápiz',exact:true})).toBeVisible();
 await p.getByLabel('Mostrar descripciones de herramientas').click();assert.ok(await p.locator('.catalog-action small:visible').count()>5);await p.getByLabel('Mostrar descripciones de herramientas').click();await expect(p.locator('.catalog-action small:visible')).toHaveCount(0);
 await openTool(p,'Seleccionar marca');const options=await p.getByLabel('Anotación existente',{exact:true}).locator('option').evaluateAll(nodes=>nodes.map(n=>({value:n.value,text:n.textContent})));const ink=options.find(o=>o.text.includes('Lápiz')),line=options.find(o=>o.text.includes('Línea'));
 await p.getByLabel('Anotación existente',{exact:true}).selectOption(ink.value);const oldX=Number(await p.getByLabel('Posición X de marca existente',{exact:true}).inputValue());await p.getByLabel('Posición X de marca existente',{exact:true}).fill(String(oldX+20));await expect(p.getByRole('tab',{name:'Leer',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();await expect(p.locator('.document-bar')).toContainText('1 cambios');
 await p.getByLabel('Anotación existente',{exact:true}).selectOption(line.value);const oldY=Number(await p.getByLabel('Posición Y de marca existente',{exact:true}).inputValue());await p.getByLabel('Posición Y de marca existente',{exact:true}).fill(String(oldY+15));await p.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();await expect(p.locator('.document-bar')).toContainText('2 cambios');
 await p.getByRole('button',{name:/Deshacer/}).click();await expect(p.locator('.document-bar')).toContainText('1 cambios');await p.getByRole('button',{name:/Rehacer/}).click();await expect(p.locator('.document-bar')).toContainText('2 cambios');
 let download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const output=join(tmpdir(),'reapdf-imported-path-result.pdf');await(await download).saveAs(output);execFileSync(python,['-c',`import sys,pymupdf as f
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 p=a[0];q=b[0];old=list(p.annots());new=list(q.annots());assert len(old)==len(new)==3
 for index,delta in [(0,(20,0)),(2,(0,15))]:
  av=old[index].vertices;bv=new[index].vertices
  if index==0:av=[v for path in av for v in path];bv=[v for path in bv for v in path]
  for v,w in zip(av,bv):assert abs(w[0]-v[0]-delta[0])<.01 and abs(w[1]-v[1]-delta[1])<.01
  assert old[index].line_ends==new[index].line_ends and old[index].info==new[index].info
 assert old[1].rect==new[1].rect;assert p.get_text()==q.get_text()`,fixture,output]);
 await p.screenshot({path:join(tmpdir(),'reapdf-interfaz-profesional-032.png')});
 await openTool(p,'Censurar y sanear copia');await p.getByRole('dialog').evaluate(el=>{el.scrollTop=el.scrollHeight;});const title=await p.getByRole('heading',{name:'Censurar regiones y sanear copia',exact:true}).boundingBox();assert.ok(title.y>=0&&title.y+title.height<=1080);await p.getByRole('button',{name:'Cerrar',exact:true}).click();
 await p.getByRole('tab',{name:'Editar',exact:true}).click();await p.screenshot({path:join(tmpdir(),'reapdf-distribucion-editar-032.png')});
 for(const [width,height] of [[1100,800],[900,800],[600,900]]){await p.setViewportSize({width,height});assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));if(width>700)assert.ok(await p.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1));await p.screenshot({path:join(tmpdir(),`reapdf-interfaz-${width}-032.png`),fullPage:width<=700});}
 await p.setViewportSize({width:1440,height:1080});await p.getByLabel('Mostrar descripciones de herramientas').click();await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await expect(p.getByLabel('Mostrar descripciones de herramientas')).toHaveAttribute('aria-pressed','true');await expect(p.locator('.document-bar')).toContainText('2 cambios');await context.close();
}
