import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {openTool} from './smoke-tool-navigation.mjs';
const dir=mkdtempSync(join(tmpdir(),'reapdf-original-flow-')),flow=join(dir,'Flujo.pdf'),portfolio=join(dir,'Portfolio.pdf'),axis=join(dir,'Objeto.pdf'),out=join(dir,'Flujo-editado.pdf'),collection=join(dir,'Portfolio-editado.pdf');
const python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
execFileSync(python,['-c',`import sys
from pathlib import Path
from tests.test_mixed_flow import mixed_source
from tests.test_portfolios import source
from tests.test_axis_form_editing import source as axis
for p,data in zip(sys.argv[1:],[mixed_source(),source(True),axis(1.6,.7)]):Path(p).write_bytes(data)`,flow,portfolio,axis]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1500,height:1800}});const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
 await page.getByLabel('Archivo PDF').setInputFiles(flow);await expect(page.locator('.document-bar')).toContainText('Flujo.pdf');await openTool(page,'Editar texto');await page.getByRole('button',{name:/^Editar en página: Texto/}).first().click();await page.getByRole('button',{name:'Editar párrafo',exact:true}).click();await page.getByLabel('Fragmento original 1',{exact:true}).fill('Texto editado ');await page.getByRole('button',{name:'Continuar en otra región',exact:true}).click();await page.getByRole('button',{name:'Leer regiones y reunir texto',exact:true}).click();await expect(page.getByLabel('Fragmento original del flujo 1',{exact:true})).toHaveValue('Texto editado ');await page.getByRole('button',{name:'Cerrar flujo de texto',exact:true}).click();await openTool(page,'Continuar texto entre regiones');
 const field=name=>page.getByLabel(name+' de región de flujo',{exact:true});
 for(const [label,value] of [['X',20],['Y',40],['Ancho',350],['Alto',80]])await field(label).fill(String(value));
 await page.getByRole('button',{name:'Añadir continuación',exact:true}).click();
 const svg=page.getByLabel('Regiones de flujo en página',{exact:true});await expect(page.getByAltText('Página para elegir regiones de flujo')).toBeVisible();await svg.scrollIntoViewIfNeeded();const b=await svg.boundingBox();await page.mouse.move(b.x+20/400*b.width,b.y+40/500*b.height);await page.mouse.down();await page.mouse.move(b.x+370/400*b.width,b.y+370/500*b.height,{steps:5});await page.mouse.up();
 await expect(field('Ancho')).toHaveValue('350');await expect(field('Alto')).toHaveValue('330');
 await page.getByRole('button',{name:'Leer regiones y reunir texto',exact:true}).click();await page.getByLabel('Conservar fuentes originales del flujo',{exact:true}).check();
 for(let i=1;i<=3;i++){const input=page.getByLabel(`Fragmento original del flujo ${i}`,{exact:true});await input.fill((await input.inputValue()).repeat(12));}
 await page.getByRole('button',{name:'Comparar todas las páginas del flujo',exact:true}).click();await expect(page.getByLabel('Revisé flujo página 2',{exact:true})).toBeVisible();
 await page.getByLabel('Revisé flujo página 1',{exact:true}).check();await page.getByLabel('Revisé flujo página 2',{exact:true}).check();await page.getByRole('button',{name:'Aplicar flujo completo',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);
 async function save(path){const wait=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await wait).saveAs(path);}
 await save(out);await page.getByRole('button',{name:/Deshacer/}).click();await expect(page.locator('.text-layer')).toContainText('Texto');await page.getByRole('button',{name:/Rehacer/}).click();
 await page.getByLabel('Archivo PDF').setInputFiles(portfolio);await expect(page.locator('.document-bar')).toContainText('Portfolio.pdf');await openTool(page,'Portfolio PDF');
 await page.getByLabel('Título del archivo 1',{exact:true}).fill('Documento principal');await page.getByLabel('Descripción del archivo 1',{exact:true}).fill('Descripción revisada ñ');await page.getByRole('button',{name:'Bajar archivo 1',exact:true}).click();await page.getByLabel('Vista inicial del portfolio',{exact:true}).selectOption('tiles');
 await page.getByRole('button',{name:'Aplicar portfolio',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await save(collection);await openTool(page,'Portfolio PDF');await expect(page.getByLabel('Título del archivo 2',{exact:true})).toHaveValue('Documento principal');await expect(page.getByLabel('Vista inicial del portfolio',{exact:true})).toHaveValue('tiles');await page.getByLabel('Buscar archivo del portfolio',{exact:true}).fill('principal');await expect(page.locator('.portfolio-file')).toHaveCount(1);
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Descargar archivo 2',exact:true}).click();await(await download).saveAs(join(dir,'adjunto.txt'));await page.getByRole('button',{name:'Cerrar portfolio',exact:true}).click();
 await page.getByRole('button',{name:/Deshacer/}).click();await openTool(page,'Portfolio PDF');await expect(page.getByRole('dialog').getByRole('status')).toContainText('todavía no tiene');await page.getByRole('button',{name:'Cerrar portfolio',exact:true}).click();
 await page.getByLabel('Archivo PDF').setInputFiles(axis);await expect(page.locator('.document-bar')).toContainText('Objeto.pdf');await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: HELLO TEXT',exact:true}).first().click();const input=page.getByLabel('Texto sobre la página',{exact:true});await expect(input).toBeEnabled();await input.fill('HELLO TEX');await input.press('Control+Enter');await expect(input).toHaveCount(0);await expect(page.locator('.text-layer')).toContainText('HELLO TEX');
 execFileSync(python,['-c',`import sys,re,pymupdf as f
from pathlib import Path
from backend.portfolios import model
from backend.pro_tools import download_attachment
with f.open(sys.argv[1]) as a,f.open(sys.argv[2]) as b:
 assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
 for i in [0,1]:assert 'Pie ' in b[i].get_text()
 programs={a.extract_font(v[0])[3] for v in a[0].get_fonts()};assert programs<={b.extract_font(v[0])[3] for p in b for v in p.get_fonts()}
 c=model(Path(sys.argv[3]).read_bytes());assert c['enabled'] and c['view']=='tiles' and c['files'][1]['title']=='Documento principal';assert Path(sys.argv[4]).read_bytes()==b'first payload'`,flow,out,collection,join(dir,'adjunto.txt')]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: original mixed fonts flowed through mouse-selected regions on two pages, compared/exported with undo/redo; native portfolio metadata/order/view saved, reopened, filtered, downloaded and undone; nonuniform shared Form edited on page.');
}finally{await browser.close();}
