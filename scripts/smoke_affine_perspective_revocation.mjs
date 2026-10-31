import {chromium,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';import {tmpdir} from 'node:os';
import {openTool} from './smoke-tool-navigation.mjs';
const root=mkdtempSync(join(tmpdir(),'reapdf-affine-perspective-')),file=n=>join(root,n);
execFileSync('.venv/bin/python',['-c',`from pathlib import Path
import sys,json
from tests.test_affine_perspective_revocation import affine,perspective_table,pki
from tests.test_table_regions import source
from backend.digital_signatures import sign_document
root=Path(sys.argv[1]);table,quad=perspective_table();identity,trust,proof=pki()
for name,data in [('Affine.pdf',affine()),('Perspective.pdf',table),('Signed.pdf',sign_document(source(),[],identity,'',{})),('Trust.pem',trust),('Proof.crl',proof)]:(root/name).write_bytes(data)
(root/'quad.json').write_text(json.dumps(quad))`,root]);
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium'});
try{
const page=await browser.newPage({viewport:{width:1700,height:1150}});page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());await page.goto('http://127.0.0.1:8000');
async function upload(n){await page.getByLabel('Archivo PDF',{exact:true}).setInputFiles(file(n));await expect(page.locator('.document-bar')).toContainText(n);}
await upload('Affine.pdf');await openTool(page,'Editar texto');await page.getByRole('button',{name:'Editar en página: ALPHA BETA GAMMA',exact:true}).click();await expect(page.getByLabel('Texto sobre la página',{exact:true})).toBeEnabled();await page.getByRole('button',{name:'Distribuir en líneas',exact:true}).click();await page.getByLabel('Ancho de reflujo afín').fill('110');await page.getByLabel('Alto de reflujo afín').fill('130');await page.getByLabel('Texto sobre la página',{exact:true}).fill('ALPHA BETA\nGAMMA ALPHA');await page.getByRole('button',{name:'Aplicar',exact:true}).click();await expect(page.getByLabel('Texto sobre la página',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Editar en página: GAMMA ALPHA',exact:true})).toHaveCount(1);
let saved=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();await(await saved).saveAs(file('Reflow.pdf'));
await upload('Perspective.pdf');await openTool(page,'Extraer tabla por región');let dialog=page.getByRole('dialog',{name:'Extraer tabla por región',exact:true});await dialog.getByText('Área en puntos PDF',{exact:true}).click();for(const [label,value]of [['X','40'],['Y','50'],['Ancho','470'],['Alto','220']])await dialog.getByLabel(label+' de tabla',{exact:true}).fill(value);await dialog.getByLabel('Corregir perspectiva de tabla').check();await dialog.getByText('Opciones de reconocimiento',{exact:true}).click();await dialog.getByLabel('Idioma OCR de tabla').selectOption('eng');await dialog.getByLabel('Resolución OCR de tabla').selectOption('300');
const svg=dialog.getByLabel('Seleccionar tabla y separadores'),quad=JSON.parse(execFileSync('cat',[file('quad.json')],{encoding:'utf8'}));for(let i=0;i<4;i++){const corner=svg.locator(`circle[data-corner="${i}"]`),b=await corner.boundingBox(),s=await svg.boundingBox();await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(s.x+quad[i][0]/540*s.width,s.y+quad[i][1]/325*s.height,{steps:8});await page.mouse.up();}
await dialog.getByRole('button',{name:'Extraer y revisar',exact:true}).click();await expect(dialog.getByLabel('Celda 2, 1',{exact:true})).toHaveValue('BOLT');await expect(dialog.getByAltText('Tabla rectificada para revisar')).toBeVisible();await dialog.getByLabel('Celda 2, 1',{exact:true}).fill('REVIEWED');saved=page.waitForEvent('download');await dialog.getByRole('button',{name:'Exportar CSV revisado',exact:true}).click();await(await saved).saveAs(file('Table.csv'));await dialog.getByRole('button',{name:'Cerrar',exact:true}).click();
await upload('Signed.pdf');await openTool(page,'Verificar firmas digitales');dialog=page.getByRole('dialog',{name:'Verificar firmas digitales',exact:true});await dialog.getByLabel('Certificados de confianza para verificar').setInputFiles(file('Trust.pem'));await dialog.getByText('Revocación con evidencias locales (opcional)',{exact:true}).click();await dialog.getByLabel('Evidencias locales de revocación').setInputFiles(file('Proof.crl'));await dialog.getByRole('button',{name:'Comprobar firmas',exact:true}).click();await expect(dialog).toContainText('cadena comprobada con evidencias vigentes locales');await expect(dialog).toContainText('Cadena y revocación aceptadas con evidencia local');
execFileSync('.venv/bin/python',['-c',`from pathlib import Path
import sys,pymupdf as f
root=Path(sys.argv[1])
with f.open(root/'Reflow.pdf') as d:assert 'GAMMA ALPHA' in d[0].get_text()
assert 'REVIEWED' in (root/'Table.csv').read_text(encoding='utf-8-sig')`,root]);
if(errors.length)throw new Error(errors.join('\n'));console.log('PASS: Chromium direct affine multiline reflow and export; four corners dragged, perspective OCR reviewed/corrected/exported; local CRL and explicit trust verification.');
}finally{await browser.close();}
