import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-four-blocks-')),python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
const file=name=>join(root,name);
execFileSync(python,['-c',`from pathlib import Path
import sys
from tests.test_four_blocks import variable_pdf,table_pdf,comment_pdf
from tests.test_scan_geometry import scan
from tests.test_form_standard_actions import source
root=Path(sys.argv[1])
for name,data in [('Variable.pdf',variable_pdf()),('Table.pdf',table_pdf()),('Threads.pdf',comment_pdf()),('Scan.pdf',scan()),('Time.pdf',source('AFTime_Format(2);','AFTime_Keystroke(2);',initial=''))]: (root/name).write_bytes(data)`,root]);
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium'});
try{
 const page=await browser.newPage({viewport:{width:1600,height:1150}}),errors=[];page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto(process.env.REAPDF_URL||'http://127.0.0.1:8000');
 async function upload(name){await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(file(name));await expect(page.locator('.document-bar')).toContainText(name);}
 async function save(label,name){const download=page.waitForEvent('download');await page.getByRole('button',{name:label,exact:true}).click();await(await download).saveAs(file(name));}
 await upload('Variable.pdf');await openTool(page,'Preparar fuentes variables');let dialog=page.getByRole('dialog',{name:'Preparar fuentes variables',exact:true});await expect(dialog.getByText(/wght: 400/)).toBeVisible();await dialog.getByLabel('Revisé los ejes de fuentes variables',{exact:true}).check();await dialog.getByRole('button',{name:'Preparar fuentes estáticas',exact:true}).click();await expect(dialog).toHaveCount(0);await save('Exportar copia','Static.pdf');
 await upload('Table.pdf');await openTool(page,'Etiquetas y orden de lectura');dialog=page.getByRole('dialog',{name:'Etiquetas y orden de lectura',exact:true});await dialog.getByRole('button',{name:'Preparar etiquetas iniciales',exact:true}).click();await dialog.getByRole('button',{name:'Sugerir tabla por posición',exact:true}).click();await expect(dialog.getByLabel('Fila del objeto 6',{exact:true})).toHaveValue('3');await expect(dialog.getByLabel('Columna del objeto 6',{exact:true})).toHaveValue('2');await expect(dialog.getByLabel('Revisé etiquetas de página 1',{exact:true})).toBeEnabled();await dialog.getByLabel('Revisé etiquetas de página 1',{exact:true}).check();await dialog.getByRole('button',{name:'Crear etiquetas revisadas',exact:true}).click();await expect(dialog).toHaveCount(0);await save('Exportar copia','Semantic.pdf');
 await upload('Table.pdf');await openTool(page,'Extraer tabla por región');dialog=page.getByRole('dialog',{name:'Extraer tabla por región',exact:true});await dialog.getByRole('button',{name:'Extraer y revisar',exact:true}).click();await expect(dialog.getByLabel('Celda 3, 2',{exact:true})).toHaveValue('200');await expect(dialog.getByText(/Separadores sugeridos por espacios/)).toBeVisible();await save('Exportar CSV revisado','Borderless.csv');await dialog.getByRole('button',{name:'Cerrar',exact:true}).click();
 await upload('Threads.pdf');await openTool(page,'Intercambiar XFDF');dialog=page.getByRole('dialog',{name:'Intercambiar XFDF',exact:true});await save('Exportar XFDF','Threads.xfdf');await expect(dialog.getByRole('status')).toContainText('Exportadas 3 anotaciones');await dialog.getByRole('button',{name:'Cerrar',exact:true}).click();
 await upload('Time.pdf');await openTool(page,'Rellenar formulario');dialog=page.getByRole('dialog',{name:'Rellenar formulario',exact:true});await expect(dialog.getByText('Hora: HH:MM:ss.',{exact:false})).toBeVisible();await dialog.getByLabel('Valor del formulario',{exact:true}).fill('25:00');await expect(dialog.getByRole('alert')).toContainText('hora');await dialog.getByLabel('Valor del formulario',{exact:true}).fill('14:35:20');await expect(dialog.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeEnabled();await dialog.getByRole('button',{name:'Aplicar formulario',exact:true}).click();await expect(dialog).toHaveCount(0);await save('Exportar copia','FilledTime.pdf');
 await upload('Scan.pdf');await openTool(page,'OCR de región');dialog=page.getByRole('dialog',{name:'OCR de región',exact:true});await dialog.getByLabel('Idioma del OCR de región',{exact:true}).selectOption('eng');await dialog.getByRole('button',{name:'Comparar orientaciones OCR',exact:true}).click();await expect(dialog.getByRole('region',{name:'Muestras de orientación OCR'})).toContainText('GEOMETRY TEST 12345');await dialog.getByRole('button',{name:'Usar 0°',exact:true}).click();await dialog.getByRole('button',{name:'Sugerir esquinas del escaneo',exact:true}).click();await expect(dialog.getByRole('status')).toContainText('No hay un borde de papel');await dialog.getByRole('button',{name:'Reconocer esta región',exact:true}).click();await expect(dialog).toHaveCount(0);await save('Exportar copia','Recognized.pdf');
 execFileSync(python,['-c',`from pathlib import Path
import sys,csv,pymupdf as f
from backend.variable_fonts import inspect
from backend.structure_editing import model
from backend.xfdf import parse,tag
root=Path(sys.argv[1]);assert not inspect((root/'Static.pdf').read_bytes(),[])['fonts']
rows=model((root/'Semantic.pdf').read_bytes(),[])['nodes'];assert sum(r['role']=='Table' for r in rows)==1 and sum(r['role']=='TH' for r in rows)==2
with (root/'Borderless.csv').open(encoding='utf-8-sig',newline='') as file:assert list(csv.reader(file))==[['Name','Value'],['Alpha','100'],['Beta','200']]
annots=parse((root/'Threads.xfdf').read_bytes()).find(tag('annots'));assert len(annots)==3 and sum(n.get('inreplyto') is not None for n in annots)==2
with f.open(root/'FilledTime.pdf') as d:assert next(d[0].widgets()).field_value=='14:35:20'
with f.open(root/'Scan.pdf') as a,f.open(root/'Recognized.pdf') as b:assert 'GEOMETRY TEST 12345' in b[0].get_text() and a[0].get_pixmap().samples==b[0].get_pixmap().samples`,root]);
 if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: Chromium visible tools, reviewed variable-font defaults, semantic table cell roles/coordinates, borderless table review/CSV, XFDF replies/states, invalid/valid native time field, four OCR orientation samples, corner abstention and invisible OCR save; outputs reopened and independently inspected.');
}finally{await browser.close();}
