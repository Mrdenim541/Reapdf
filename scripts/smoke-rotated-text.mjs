import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runRotatedTextSmoke(browser,baseUrl,python,errors,onPage){
 for(const angle of [90,180,270])for(const mode of ['reflow','original']){
  const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
  const fixture=join(tmpdir(),`reapdf-rotated-${angle}-${mode}.pdf`);
  execFileSync(python,['-c',`import pymupdf as f,sys
from pathlib import Path
with f.open() as d:
 p=d.new_page(width=500,height=650);p.insert_font(fontname='Original',fontfile='resources/fonts/DejaVuSans-Bold.ttf');p.insert_text((40,80),'Texto digital original largo',fontname='Original',fontsize=14,color=(.2,.4,.6));p.insert_text((40,400),'Fuera del bloque',fontname='tiro');p.set_cropbox(f.Rect(20,30,480,620));p.set_rotation(int(sys.argv[2]));d.new_page().insert_text((40,80),'Otra pagina intacta');d.subset_fonts();d.save(sys.argv[1])`,fixture,String(angle)]);
  await p.goto(baseUrl);await p.getByLabel('Archivo PDF').setInputFiles(fixture);await p.getByAltText('Página 1 del documento').waitFor();await openTool(p,'Reemplazar bloque de texto');
  await expect(p.getByRole('status').filter({hasText:'Vista de edición enderezada'})).toContainText(`${angle}°`);
  const image=p.getByAltText('Página para editar bloque de texto');await expect(image).toBeVisible();const dimensions=await image.evaluate(el=>[el.naturalWidth,el.naturalHeight]);if(dimensions[0]!==460||dimensions[1]!==590)throw new Error('La vista de edición no usa las dimensiones nativas del CropBox.');const sourceImage=await image.getAttribute('src');
  await p.getByRole('button',{name:'Detectar bloques de texto',exact:true}).click();await p.getByLabel('Bloque de texto detectado').selectOption('0');
  for(const [label,value] of [['X','10'],['Y','20'],['Ancho','440'],['Alto','140']])await p.getByLabel(`${label} de bloque de texto`,{exact:true}).fill(value);
  await p.getByLabel('Modo de edición del bloque').selectOption(mode);await p.getByRole('button',{name:'Leer bloque seleccionado',exact:true}).click();
  if(mode==='reflow'){
   await expect(p.getByLabel('Tamaño de bloque de texto')).toHaveValue('14');await expect(p.getByLabel('Estilo del párrafo')).toHaveValue('bold');await expect(p.getByLabel('Color del párrafo')).toHaveValue('#336699');
   await p.getByLabel('Texto del bloque').fill('Corrección en página girada áñ αβ');await p.getByLabel('Fuente del párrafo').selectOption('serif');await p.getByLabel('Estilo del párrafo').selectOption('bold-italic');await p.getByRole('button',{name:'Vista previa del bloque',exact:true}).click();
  }else{await p.getByLabel('Texto del fragmento 1',{exact:true}).fill('Texto original');await p.getByRole('button',{name:'Vista previa conservando estilo',exact:true}).click();}
  await expect(p.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeEnabled();const resultImage=await image.getAttribute('src');if(resultImage===sourceImage)throw new Error('La vista previa no se actualizó.');
  await p.getByRole('button',{name:'Ver original',exact:true}).click();await expect(image).toHaveAttribute('src',sourceImage);await p.getByRole('button',{name:'Ver resultado',exact:true}).click();await expect(image).toHaveAttribute('src',resultImage);
  if(angle===270&&mode==='reflow')await p.screenshot({path:join(tmpdir(),'reapdf-edicion-girada-025.png')});
  await p.getByRole('button',{name:'Aplicar párrafo',exact:true}).click();const target=mode==='reflow'?'Corrección en página girada':'Texto original';await expect(p.locator('.text-layer')).toContainText(target);await expect(p.locator('.text-layer')).not.toContainText('Texto digital original largo');
  const download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const output=join(tmpdir(),`reapdf-rotated-result-${angle}-${mode}.pdf`);await(await download).saveAs(output);
  execFileSync(python,['-c',`import pymupdf as f,sys,hashlib
before=f.open(sys.argv[1]);after=f.open(sys.argv[2]);assert after[0].rotation==int(sys.argv[3]);assert after[0].cropbox==before[0].cropbox;assert after[1].get_pixmap().samples==before[1].get_pixmap().samples;assert sys.argv[4] in after[0].get_text()
if sys.argv[5]=='original':
 fonts=lambda d:{hashlib.sha256(d.extract_font(row[0])[3]).hexdigest() for row in d[0].get_fonts() if row[1]=='ttf'}
 assert fonts(before)==fonts(after)`,fixture,output,String(angle),target,mode]);
  await p.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(p.locator('.text-layer')).toContainText('Texto digital original largo');await p.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(p.locator('.text-layer')).toContainText(target);
  if(angle===90&&mode==='reflow'){
   const download=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).click();const project=join(tmpdir(),'reapdf-rotated-project.reapdf');await(await download).saveAs(project);
   execFileSync(python,['-c',`import sys,pymupdf as f;from pathlib import Path;from backend.projects import read_project;from backend.engine import export_pdf
base,ops,_=read_project(Path(sys.argv[1]).read_bytes());d=f.open(stream=export_pdf(base,ops));assert d[0].rotation==90 and 'Corrección en página girada' in d[0].get_text()`,project]);
   await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await expect(p.locator('.text-layer')).toContainText(target);
  }
  await context.close();
 }
}
