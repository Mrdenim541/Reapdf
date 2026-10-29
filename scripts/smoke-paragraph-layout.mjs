import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export async function runParagraphLayoutSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(20000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const fixture=join(tmpdir(),'reapdf-paragraph-layout-source.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
with f.open() as d:
 p=d.new_page(width=500,height=650);p.insert_text((40,80),'Texto original primera linea',fontsize=12);p.insert_text((40,100),'Segunda linea',fontsize=12);p.insert_text((40,400),'Conservar fuera del bloque',fontsize=12);d.new_page(width=500,height=650).insert_text((40,80),'Otra pagina intacta',fontsize=12);d.save(sys.argv[1])`,fixture]);
 await p.goto(baseUrl);await p.getByLabel('Archivo PDF').setInputFiles(fixture);await p.getByAltText('Página 1 del documento').waitFor();await openTool(p,'Reemplazar bloque de texto');
 await p.setViewportSize({width:390,height:844});await expect(p.getByRole('dialog')).toBeVisible();const fits=await p.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1);if(!fits)throw new Error('El editor de párrafos desborda horizontalmente en pantalla pequeña.');await p.setViewportSize({width:1440,height:1080});
 await p.getByRole('button',{name:'Detectar bloques de texto',exact:true}).click();await expect(p.getByLabel('Bloque de texto detectado')).toBeVisible();
 await p.getByRole('button',{name:'Seleccionar bloque 1',exact:true}).focus();await p.getByRole('button',{name:'Seleccionar bloque 1',exact:true}).press('Enter');
 await p.getByLabel('Bloque de texto detectado').selectOption('0');
 for(const [label,value] of [['X','30'],['Y','50'],['Ancho','430'],['Alto','130']])await p.getByLabel(`${label} de bloque de texto`,{exact:true}).fill(value);
 await p.getByRole('button',{name:'Leer bloque seleccionado',exact:true}).click();await expect(p.getByLabel('Texto del bloque')).toContainText('Texto original');
 await p.getByLabel('Texto del bloque').fill('Una línea\notra línea\n\nOtro párrafo');await p.getByRole('button',{name:'Unir líneas del párrafo',exact:true}).click();await expect(p.getByLabel('Texto del bloque')).toHaveValue('Una línea otra línea\n\nOtro párrafo');
 await p.getByLabel('Texto del bloque').fill('Párrafo profesional áñ αβ. '.repeat(20));await p.getByLabel('Fuente del párrafo').selectOption('serif');await p.getByLabel('Estilo del párrafo').selectOption('bold-italic');await p.getByLabel('Color del párrafo').fill('#336699');await p.getByLabel('Interlineado del párrafo').fill('1.4');await p.getByLabel('Tamaño de bloque de texto').fill('28');
 await p.getByRole('button',{name:'Vista previa del bloque',exact:true}).click();await expect(p.getByRole('alert')).toContainText('no cabe');await expect(p.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeDisabled();
 await p.getByLabel('Reducir tamaño para ajustar').check();await p.getByLabel('Tamaño mínimo del párrafo').fill('8');await p.getByRole('button',{name:'Vista previa del bloque',exact:true}).click();await expect(p.getByRole('status').filter({hasText:'Vista previa validada'})).toContainText('tamaño reducido desde 28');await expect(p.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeEnabled();
 await p.getByLabel('Alineación de bloque de texto').selectOption('1');await expect(p.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeDisabled();await p.getByRole('button',{name:'Vista previa del bloque',exact:true}).click();await expect(p.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeEnabled();
 await p.getByRole('button',{name:'Ampliar vista previa',exact:true}).click();await p.screenshot({path:join(tmpdir(),'reapdf-paragraph-layout-024.png')});
 await p.getByRole('button',{name:'Aplicar párrafo',exact:true}).click();await expect(p.locator('.text-layer')).toContainText('Párrafo profesional');await expect(p.locator('.text-layer')).toContainText('Conservar fuera del bloque');await expect(p.locator('.text-layer')).not.toContainText('Texto original');
 const download=p.waitForEvent('download');await p.getByRole('button',{name:'Exportar copia',exact:true}).click();const output=join(tmpdir(),'reapdf-paragraph-layout-result.pdf');await(await download).saveAs(output);
 execFileSync(python,['-c',`import pymupdf as f,sys
before=f.open(sys.argv[1]);after=f.open(sys.argv[2]);assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
spans=[s for b in after[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if 'Párrafo profesional' in s['text']];assert spans and all(s['flags']&16 and s['flags']&2 and s['color']==0x336699 and s['size']<28 for s in spans)`,fixture,output]);
 await p.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(p.locator('.text-layer')).toContainText('Texto original');await p.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(p.locator('.text-layer')).toContainText('Párrafo profesional');await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');
 const projectDownload=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).click();const project=join(tmpdir(),'reapdf-paragraph-layout-project.reapdf');await(await projectDownload).saveAs(project);
 execFileSync(python,['-c',`import sys,pymupdf as f;from pathlib import Path;from backend.projects import read_project;from backend.engine import export_pdf
base,ops,_=read_project(Path(sys.argv[1]).read_bytes());d=f.open(stream=export_pdf(base,ops));assert 'Párrafo profesional' in d[0].get_text();spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if 'Párrafo profesional' in s['text']];assert spans and all(s['flags']&16 and s['flags']&2 and s['color']==0x336699 for s in spans)`,project]);
 await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await expect(p.locator('.text-layer')).toContainText('Párrafo profesional');await context.close();
}
