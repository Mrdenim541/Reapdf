import {runWordSectionsSmoke} from './smoke-word-sections.mjs';
import {runWordAdvancedSmoke} from './smoke-word-advanced.mjs';
import {runMixedFlowSmoke} from './smoke-mixed-flow.mjs';
import {runRunningFieldsSmoke} from './smoke-running-fields.mjs';
import {runStylesOrganizationSmoke} from './smoke-styles-organization.mjs';
import {runWordRulesSmoke} from './smoke-word-rules.mjs';
import {runFlowCalculationsSmoke} from './smoke-flow-calculations.mjs';
import {runAutomationSmoke} from './smoke-automation.mjs';
import {runCompressionSmoke} from './smoke-compression.mjs';
import {runMultipleEndpointsSmoke} from './smoke-multiple-endpoints.mjs';
import {runImportedHandlesSmoke} from './smoke-imported-handles.mjs';
import {runProfessionalSmoke} from './smoke-professional.mjs';
import {runPrecisionRedactionSmoke} from './smoke-precision-redaction.mjs';
import {runStandardsAccessibilitySmoke} from './smoke-standards-accessibility.mjs';
import {runDigitalSignaturesSmoke} from './smoke-digital-signatures.mjs';
import {runWordFormsSmoke} from './smoke-word-forms.mjs';
import {runReviewDesignSmoke} from './smoke-review-design.mjs';
import {runEditingExpansionSmoke} from './smoke-editing-expansion.mjs';
import {runRotatedTextSmoke} from './smoke-rotated-text.mjs';
import {runParagraphLayoutSmoke} from './smoke-paragraph-layout.mjs';
import {runFormImportSmoke} from './smoke-form-import.mjs';
import {openTool} from './smoke-tool-navigation.mjs';
import {runWorkspaceSmoke} from './smoke-workspace.mjs';
import { runAdvancedFormsSmoke } from './smoke-advanced-forms.mjs';
import { runStyledTextSmoke } from './smoke-styled-text.mjs';
import { runProSmoke } from './smoke-pro.mjs';
import { chromium, expect } from '@playwright/test';
import { execFileSync, spawn } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import assert from 'node:assert/strict';
const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
const sample = process.env.REAPDF_SAMPLE || join(tmpdir(),'reapdf-demo.pdf');
execFileSync(python,['scripts/create_sample.py',sample]);
const baseUrl=process.env.REAPDF_URL || 'http://127.0.0.1:8765';
const recoveryDirectory=mkdtempSync(join(tmpdir(),'reapdf-ui-state-'));
const startServer=()=>spawn(python,['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8765'],{stdio:'ignore',env:{...process.env,REAPDF_DATA_DIR:recoveryDirectory}});
let server=process.env.REAPDF_URL?null:startServer();
let browser, page, failurePage;
try {
 let ready=false;
 for(let i=0;i<50;i++) {
  try { const r=await fetch(baseUrl+'/api/health'); if(r.ok){ready=true;break;} }catch{}
  await new Promise(resolve=>setTimeout(resolve,200));
 }
 if(!ready)throw new Error('El servidor de prueba no inició.');
 browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || (existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined)});
 page = await browser.newPage({viewport:{width:1440,height:1080}});
 failurePage=page;page.setDefaultTimeout(15000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(baseUrl);
 await page.getByLabel('Archivo PDF').setInputFiles(sample);
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Editar texto");
 await page.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await page.getByLabel('Nuevo texto').fill('Texto nuevo');
 await page.getByRole('button',{name:'Aplicar cambio'}).click();
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Lápiz");
 const box=await page.getByLabel('Lienzo de anotaciones').boundingBox();
 await page.mouse.move(box.x+100,box.y+410);await page.mouse.down();
 await page.mouse.move(box.x+250,box.y+470,{steps:12});await page.mouse.up();
 await page.getByText('2 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await page.getByText('1 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await page.getByText('2 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByLabel('Página siguiente').click();
 await page.getByAltText('Página 2 del documento').waitFor();
 await page.getByLabel('Página anterior').click();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByLabel('Reducir zoom').click();
 // Figuras creadas con zoom distinto de 100%; seleccionar y borrar por ratón.
 const draw=async(label,a,b,count)=>{
  await openTool(page,label);
  const bounds=await page.getByLabel('Lienzo de anotaciones').boundingBox();
  const screen=([x,y])=>[bounds.x+x/595*bounds.width,bounds.y+y/842*bounds.height];
  const previewDone=page.waitForResponse(r=>r.url().endsWith('/pages/0/preview') && r.request().postDataJSON()?.operations?.length===count);
  await page.mouse.move(...screen(a)); await page.mouse.down();
  await page.mouse.move(...screen(b),{steps:8});await page.mouse.up();
  await page.getByText(`${count} cambios · sin exportar`,{exact:true}).waitFor();
  await previewDone;
  await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
  await page.getByAltText('Página 1 del documento').waitFor();
 };
 await draw('Línea',[300,390],[440,410],3);
 await draw('Flecha',[300,450],[440,480],4);
 await draw('Rectángulo',[300,520],[450,600],5);
 await openTool(page,"Seleccionar marca");
 const bounds=await page.getByLabel('Lienzo de anotaciones').boundingBox();
 await page.mouse.click(bounds.x+375/595*bounds.width,bounds.y+520/842*bounds.height);
 await page.getByRole('button',{name:'Eliminar marca',exact:true}).click();
 await page.getByText('4 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await page.getByText('5 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await page.getByText('4 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByAltText('Página 1 del documento').waitFor();
 // Lectura: selección nativa de texto, miniaturas y búsqueda sobre el texto editado.
 await openTool(page,"Lectura");
 const textLine=page.locator('.text-layer span').filter({hasText:/^Texto nuevo$/});
 await textLine.dblclick();
 const selectedText=await page.evaluate(()=>window.getSelection().toString());
 assert.ok(['Texto','nuevo'].includes(selectedText));
 await page.context().grantPermissions(['clipboard-read','clipboard-write']);
 await page.keyboard.press(process.platform==='darwin'?'Meta+C':'Control+C');
 assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),selectedText);
 await page.getByRole('button',{name:'Ir a página 2',exact:true}).click();
 await page.getByAltText('Página 2 del documento').waitFor();
 await page.getByRole('tab',{name:'Marcadores',exact:true}).click();
 await page.getByRole('button',{name:'Inicio Pág. 1',exact:true}).click();
 await page.getByAltText('Página 1 del documento').waitFor();
 await page.getByRole('tab',{name:'Buscar',exact:true}).click();
 const query=page.getByRole('searchbox',{name:'Buscar en el documento'});
 await query.fill('pagina');
 await page.getByRole('button',{name:'Buscar texto',exact:true}).click();
 await expect(page.getByText('1 de 2',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Coincidencia siguiente'}).click();
 await expect(page.getByText('2 de 2',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Coincidencia anterior'}).click();
 await expect(page.getByText('1 de 2',{exact:true})).toBeVisible();
 await query.fill('Texto original');
 await page.getByRole('button',{name:'Buscar texto',exact:true}).click();
 await expect(page.getByText('Sin coincidencias',{exact:true})).toBeVisible();
 await query.fill('Texto nuevo');
 await page.getByRole('button',{name:'Buscar texto',exact:true}).click();
 await expect(page.getByText('1 de 1',{exact:true})).toBeVisible();
 await page.getByAltText('Página 1 del documento').waitFor();
 await expect(page.locator('[data-search-hit]')).toHaveCount(1);
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.screenshot({path:process.env.REAPDF_SCREENSHOT || join(tmpdir(),'reapdf-editor.png'),fullPage:true});
 const downloadPromise=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:false}).click();
 const download=await downloadPromise;
 const output=process.env.REAPDF_OUTPUT || join(tmpdir(),'reapdf-ui-export.pdf');
 await download.saveAs(output);
 execFileSync(python,['-c',`import pymupdf as f,sys\nd=f.open(sys.argv[1]); assert len(d)==2; assert 'Texto nuevo' in d[0].get_text(); assert 'Texto original' not in d[0].get_text(); p=d[0]; a=list(p.annots()); assert sorted(x.type[0] for x in a)==[f.PDF_ANNOT_LINE,f.PDF_ANNOT_LINE,f.PDF_ANNOT_INK]; assert sum(x.line_ends==(f.PDF_ANNOT_LE_NONE,f.PDF_ANNOT_LE_CLOSED_ARROW) for x in a if x.type[0]==f.PDF_ANNOT_LINE)==1; assert 'Segunda pagina' in d[1].get_text()`,output]);
 // Organizar conserva las ediciones y el historial anterior.
 const openOrganizer=async()=>{
  await openTool(page,"Organizar páginas");
  return page.getByRole('dialog',{name:'Organizar páginas',exact:true});
 };
 let organizer=await openOrganizer();
 await organizer.getByLabel('Seleccionar todas las páginas',{exact:true}).check();
 await expect(organizer.getByRole('button',{name:'Eliminar selección',exact:true})).toBeDisabled();
 await organizer.getByLabel('Seleccionar todas las páginas',{exact:true}).uncheck();
 await organizer.getByLabel('Seleccionar página 1',{exact:true}).check();
 await organizer.getByRole('button',{name:'Subir página 2',exact:true}).click();
 assert.deepEqual(await organizer.locator('.organizer-card').evaluateAll(cards=>cards.map(card=>Number(card.dataset.sourcePage))),[1,0]);
 await organizer.getByRole('button',{name:'Girar selección 90°',exact:true}).click();
 await page.screenshot({path:join(tmpdir(),'reapdf-organizer.png'),fullPage:true});
 await organizer.getByRole('button',{name:'Aplicar organización',exact:true}).click();
 await expect(organizer).toHaveCount(0);
 await expect(page.locator('.text-layer span').filter({hasText:/^Segunda pagina$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.locator('.text-layer span').filter({hasText:/^Texto nuevo$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.locator('.text-layer span').filter({hasText:/^Segunda pagina$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const organizedDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const organized=join(tmpdir(),'reapdf-organized.pdf');await (await organizedDownload).saveAs(organized);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]); assert len(d)==2; assert 'Segunda pagina' in d[0].get_text(); assert 'Texto nuevo' in d[1].get_text(); assert d[1].rotation==90; p=d[1]; assert len(list(p.annots()))==3; assert d.get_toc()==[[1,'Inicio',2],[1,'Segunda pagina',1]]`,organized]);
 // Extraer la segunda página del orden actual sin cambiar el documento abierto.
 organizer=await openOrganizer();
 await organizer.getByLabel('Seleccionar página 1',{exact:true}).uncheck();
 await organizer.getByLabel('Seleccionar página 2',{exact:true}).check();
 const extractedDownload=page.waitForEvent('download');
 await organizer.getByRole('button',{name:'Extraer selección',exact:true}).click();
 const extracted=join(tmpdir(),'reapdf-extracted.pdf');await (await extractedDownload).saveAs(extracted);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]); assert len(d)==1; assert d[0].rotation==90; assert 'Texto nuevo' in d[0].get_text(); p=d[0]; assert len(list(p.annots()))==3; assert d.get_toc()==[[1,'Inicio',1]]`,extracted]);
 await expect(organizer.getByRole('status')).toBeVisible();
 await organizer.getByRole('button',{name:'Cancelar',exact:true}).click();
 await expect(page.getByRole('form',{name:'Página 1 de 2',exact:true})).toBeVisible();
 // Eliminar y revertir vuelve a la versión anterior, sin perder las anotaciones.
 organizer=await openOrganizer();
 await organizer.getByRole('button',{name:'Eliminar selección',exact:true}).click();
 await organizer.getByLabel('Seleccionar página 2',{exact:true}).check();
 await expect(organizer.getByRole('button',{name:'Eliminar selección',exact:true})).toBeDisabled();
 await organizer.getByRole('button',{name:'Aplicar organización',exact:true}).click();
 await expect(page.getByRole('form',{name:'Página 1 de 1',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Texto nuevo$/})).toBeVisible();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('form',{name:'Página 1 de 2',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Segunda pagina$/})).toBeVisible();
 // Las ediciones posteriores se aplican a la página correcta del nuevo orden.
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(page,"Editar texto");
 await page.getByRole('button',{name:'Editar: Segunda pagina',exact:true}).click();
 await page.getByLabel('Nuevo texto').fill('Pagina dos');
 await page.getByRole('button',{name:'Aplicar cambio',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const finalDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const finalFile=join(tmpdir(),'reapdf-after-organization.pdf');await (await finalDownload).saveAs(finalFile);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]); assert len(d)==2; assert 'Pagina dos' in d[0].get_text(); assert 'Segunda pagina' not in d[0].get_text(); assert 'Texto nuevo' in d[1].get_text(); p=d[1]; assert len(list(p.annots()))==3; assert p.rotation==90`,finalFile]);
 // Insertar rangos no contiguos y conservar el historial y las anotaciones.
 const extra=join(tmpdir(),'reapdf-extra.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open()
for text in ['Anexo uno','Anexo dos','Anexo tres']:
 p=d.new_page(width=400,height=500);p.insert_text((40,80),text,fontsize=16)
d[0].add_text_annot((40,160),'Nota anexo');d[2].set_rotation(270);d.set_toc([[1,'Anexo uno',1],[1,'Anexo tres',3]]);d.save(sys.argv[1])`,extra]);
 const openInserter=async()=>{
  await openTool(page,"Unir o insertar PDF");
  return page.getByRole('dialog',{name:'Unir o insertar PDF',exact:true});
 };
 let inserter=await openInserter();
 await inserter.getByLabel('PDF para insertar',{exact:true}).setInputFiles(extra);
 await expect(inserter.getByText('3 páginas disponibles',{exact:true})).toBeVisible();
 await inserter.getByLabel('Páginas para insertar',{exact:true}).fill('1,1');
 await expect(inserter.getByRole('button',{name:'Insertar páginas',exact:true})).toBeDisabled();
 await expect(inserter.getByText('La página 1 está repetida.',{exact:true})).toBeVisible();
 await inserter.getByLabel('Páginas para insertar',{exact:true}).fill('3,1');
 await inserter.getByLabel('Posición de inserción',{exact:true}).selectOption('1');
 await page.screenshot({path:join(tmpdir(),'reapdf-inserter.png'),fullPage:true});
 await inserter.getByRole('button',{name:'Insertar páginas',exact:true}).click();
 await expect(inserter).toHaveCount(0);
 await expect(page.getByRole('form',{name:'Página 2 de 4',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Anexo tres$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('form',{name:'Página 2 de 2',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Texto nuevo$/})).toBeVisible();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('form',{name:'Página 2 de 4',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Anexo tres$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const insertedDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const inserted=join(tmpdir(),'reapdf-inserted.pdf');await (await insertedDownload).saveAs(inserted);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]); assert len(d)==4; assert 'Pagina dos' in d[0].get_text(); assert 'Anexo tres' in d[1].get_text(); assert d[1].rotation==270; assert 'Anexo uno' in d[2].get_text(); assert 'Texto nuevo' in d[3].get_text(); p=d[3]; assert len(list(p.annots()))==3; p=d[2]; assert next(p.annots()).info['content']=='Nota anexo'; assert d.get_toc()==[[1,'Inicio',4],[1,'Segunda pagina',1],[1,'reapdf-extra.pdf',2],[2,'Anexo uno',3],[2,'Anexo tres',2]]`,inserted]);
 // Unir un documento completo al final mediante los valores por defecto.
 inserter=await openInserter();
 await inserter.getByLabel('PDF para insertar',{exact:true}).setInputFiles(extra);
 await expect(inserter.getByText('3 páginas disponibles',{exact:true})).toBeVisible();
 await expect(inserter.getByLabel('Posición de inserción',{exact:true})).toHaveValue('4');
 await inserter.getByRole('button',{name:'Insertar páginas',exact:true}).click();
 await expect(page.getByRole('form',{name:'Página 5 de 7',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Anexo uno$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const mergedDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const merged=join(tmpdir(),'reapdf-merged.pdf');await (await mergedDownload).saveAs(merged);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]); assert len(d)==7; assert 'Pagina dos' in d[0].get_text(); assert 'Anexo uno' in d[4].get_text(); assert 'Anexo dos' in d[5].get_text(); assert 'Anexo tres' in d[6].get_text(); assert d[6].rotation==270`,merged]);
 // Revisión sobre un documento nuevo: palabras, notas, historial y exportación real.
 const review=join(tmpdir(),'reapdf-review.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open();p=d.new_page(width=400,height=500);p.insert_text((50,80),'Texto original',fontsize=16);p.insert_text((50,130),'Otra linea',fontsize=16);d.save(sys.argv[1])`,review]);
 await page.getByLabel('Archivo PDF').setInputFiles(review);
 await page.getByAltText('Página 1 del documento').waitFor();
 const dragReview=async(label,count)=>{
  await openTool(page,label);
  const bounds=await page.getByLabel('Lienzo de anotaciones').boundingBox();
  await page.mouse.move(bounds.x+40/400*bounds.width,bounds.y+50/500*bounds.height);
  await page.mouse.down();
  await page.mouse.move(bounds.x+200/400*bounds.width,bounds.y+140/500*bounds.height,{steps:8});
  await page.mouse.up();
  await page.getByText(`${count} cambios · sin exportar`,{exact:true}).waitFor();
  await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 };
 await dragReview('Resaltar',1);await dragReview('Subrayar',2);await dragReview('Tachar',3);
 await openTool(page,"Nota");
 let reviewBounds=await page.getByLabel('Lienzo de anotaciones').boundingBox();
 await page.mouse.click(reviewBounds.x+200/400*reviewBounds.width,reviewBounds.y+220/500*reviewBounds.height);
 await page.getByLabel('Contenido de la nota',{exact:true}).fill('Revisar cálculo\nÁrea: 20 m² ✓');
 await page.getByRole('button',{name:'Guardar nota',exact:true}).click();
 await page.getByText('4 cambios · sin exportar',{exact:true}).waitFor();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(page,"Seleccionar marca");
 await page.getByLabel('Marca de la sesión',{exact:true}).selectOption({label:'1. Resaltar'});
 await expect(page.getByRole('button',{name:'Eliminar marca',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:/^Seleccionar Nota /}).click();
 await expect(page.getByLabel('Contenido de la nota',{exact:true})).toHaveValue('Revisar cálculo\nÁrea: 20 m² ✓');
 await page.getByLabel('Contenido de la nota',{exact:true}).fill('Nota corregida ✓');
 await page.getByRole('button',{name:'Guardar nota',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:/^Seleccionar Nota /}).click();
 await expect(page.getByLabel('Contenido de la nota',{exact:true})).toHaveValue('Revisar cálculo\nÁrea: 20 m² ✓');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:/^Seleccionar Tachar /}).locator('rect').first().click();
 await page.getByRole('button',{name:'Eliminar marca',exact:true}).click();
 await page.getByText('3 cambios · sin exportar',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const reviewDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const reviewed=join(tmpdir(),'reapdf-reviewed.pdf');await (await reviewDownload).saveAs(reviewed);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];aa=list(p.annots());assert [a.type[0] for a in aa]==[8,9,11,0];assert all(len(a.vertices)==16 for a in aa[:3]);assert aa[-1].info['content']=='Nota corregida ✓';assert p.get_text()=='Texto original\\nOtra linea\\n'`,reviewed]);
 await page.screenshot({path:join(tmpdir(),'reapdf-review.png'),fullPage:true});
 // Ajustes numéricos y tiradores a zoom 90 %, con historial y validación real.
 await page.getByLabel('Marca de la sesión',{exact:true}).selectOption({label:'1. Resaltar'});
 await page.getByLabel('Posición X',{exact:true}).fill('100');
 await page.getByLabel('Posición Y',{exact:true}).fill('160');
 await page.getByLabel('Ancho de marca',{exact:true}).fill('180');
 await page.getByLabel('Alto de marca',{exact:true}).fill('80');
 await page.getByRole('button',{name:'Aplicar posición y tamaño',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await expect(page.getByLabel('Posición X',{exact:true})).toHaveValue('100');
 // Una posición fuera de página se rechaza y no entra al historial.
 await page.getByLabel('Posición X',{exact:true}).fill('390');
 await page.getByRole('button',{name:'Aplicar posición y tamaño',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('dentro de la página');
 await page.getByRole('button',{name:'Cerrar error',exact:true}).click();
 await expect(page.getByRole('button',{name:'Deshacer',exact:false})).toBeDisabled();
 await page.getByRole('button',{name:'Cancelar posición y tamaño',exact:true}).click();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByLabel('Marca de la sesión',{exact:true}).selectOption({label:'4. Nota'});
 const dragHandle=async(label,dx,dy,cancel=false)=>{
  const bounds=await page.getByLabel('Lienzo de anotaciones').boundingBox();
  const handle=page.getByRole('button',{name:label,exact:true});
  await handle.scrollIntoViewIfNeeded();
  const hb=await handle.boundingBox();
  await page.mouse.move(hb.x+hb.width/2,hb.y+hb.height/2);await page.mouse.down();
  await page.mouse.move(hb.x+hb.width/2+dx/400*bounds.width,hb.y+hb.height/2+dy/500*bounds.height,{steps:8});
  if(cancel)await page.keyboard.press('Escape');
  await page.mouse.up();
  await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 };
 await dragHandle('Tirador para mover marca',40,30);
 await expect(page.getByLabel('Posición X',{exact:true})).toHaveValue('240');
 await expect(page.getByLabel('Posición Y',{exact:true})).toHaveValue('250');
 await dragHandle('Tirador para mover marca',20,20,true);
 await expect(page.getByLabel('Posición X',{exact:true})).toHaveValue('240');
 await expect(page.getByLabel('Ancho de marca',{exact:true})).toBeDisabled();
 await openTool(page,"Rectángulo");
 let tb=await page.getByLabel('Lienzo de anotaciones').boundingBox();
 await page.mouse.move(tb.x+30/400*tb.width,tb.y+300/500*tb.height);await page.mouse.down();
 await page.mouse.move(tb.x+100/400*tb.width,tb.y+360/500*tb.height,{steps:8});await page.mouse.up();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(page,"Seleccionar marca");
 await page.getByLabel('Marca de la sesión',{exact:true}).selectOption({label:'5. Rectángulo'});
 await dragHandle('Tirador para mover marca',20,-20);
 await dragHandle('Redimensionar marca',40,20);
 await expect(page.getByLabel('Posición X',{exact:true})).toHaveValue('50');
 await expect(page.getByLabel('Ancho de marca',{exact:true})).toHaveValue('110');
 await expect(page.getByLabel('Alto de marca',{exact:true})).toHaveValue('80');
 const transformDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const transformed=join(tmpdir(),'reapdf-transformed.pdf');await (await transformDownload).saveAs(transformed);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];aa=list(p.annots());assert [a.type[0] for a in aa]==[8,9,11,0,4];pts=aa[0].vertices;xs=[v[0] for v in pts];ys=[v[1] for v in pts];assert max(abs(a-b) for a,b in zip([min(xs),min(ys),max(xs),max(ys)],[100,160,280,240]))<.02;assert aa[3].info['content']=='Nota corregida ✓';assert abs(aa[3].rect.x0-240)<.02;assert abs(aa[3].rect.y0-250)<.02;assert 'Texto original' in p.get_text();assert max(abs(a-b) for a,b in zip(aa[4].rect,[49,279,161,361]))<.02`,transformed]);
 await page.screenshot({path:join(tmpdir(),'reapdf-transform.png'),fullPage:true});
 // Transformación de una figura en una página girada desde el navegador.
 const rotated=join(tmpdir(),'reapdf-transform-rotated.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open();p=d.new_page(width=400,height=500);p.insert_text((40,80),'Documento girado');p.set_rotation(90);d.save(sys.argv[1])`,rotated]);
 await page.getByLabel('Archivo PDF').setInputFiles(rotated);
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Rectángulo");
 tb=await page.getByLabel('Lienzo de anotaciones').boundingBox();
 await page.mouse.move(tb.x+50/500*tb.width,tb.y+120/400*tb.height);await page.mouse.down();
 await page.mouse.move(tb.x+150/500*tb.width,tb.y+200/400*tb.height,{steps:8});await page.mouse.up();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(page,"Seleccionar marca");
 await page.getByLabel('Marca de la sesión',{exact:true}).selectOption({label:'1. Rectángulo'});
 for(const [label,value] of [['Posición X','200'],['Posición Y','150'],['Ancho de marca','120'],['Alto de marca','60']])await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByRole('button',{name:'Aplicar posición y tamaño',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Tirador para mover marca',exact:true}).focus();
 await page.keyboard.press('ArrowRight');
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await expect(page.getByLabel('Posición X',{exact:true})).toHaveValue('201');
 await page.getByRole('button',{name:'Tirador para mover marca',exact:true}).focus();
 await page.keyboard.press('ArrowLeft');
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const rotatedDownload=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const rotatedOutput=join(tmpdir(),'reapdf-transformed-rotated.pdf');await (await rotatedDownload).saveAs(rotatedOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];a=next(p.annots());assert p.rotation==90;assert 'Documento girado' in p.get_text();r=a.rect*p.rotation_matrix;assert max(abs(a-b) for a,b in zip(r,[199,149,321,211]))<.02`,rotatedOutput]);
 // Pasada de páginas: recortar/restaurar, reemplazar y dividir.
 const batch=join(tmpdir(),'reapdf-page-tools.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open()
for i in range(4):
 p=d.new_page(width=400,height=500);p.insert_text((50,80),f'Lote pagina {i+1}',fontsize=16)
d[0].add_text_annot((120,150),'Nota lote');d[3].set_rotation(90);d.set_toc([[1,'Inicio lote',1],[1,'Final lote',4]]);d.save(sys.argv[1])`,batch]);
 await page.getByLabel('Archivo PDF').setInputFiles(batch);
 await page.getByAltText('Página 1 del documento').waitFor();
 const cropOpen=async()=>{
  await openTool(page,"Recortar páginas");
  return page.getByRole('dialog',{name:'Recortar páginas',exact:true});
 };
 let cropDialog=await cropOpen();
 await cropDialog.getByLabel('Páginas para recortar',{exact:true}).fill('1,4');
 await cropDialog.getByLabel('Margen izquierdo',{exact:true}).fill('500');
 await expect(cropDialog.getByRole('button',{name:'Aplicar recorte',exact:true})).toBeDisabled();
 await cropDialog.getByLabel('Margen izquierdo',{exact:true}).fill('10');
 await cropDialog.getByLabel('Margen superior',{exact:true}).fill('20');
 await cropDialog.getByLabel('Margen derecho',{exact:true}).fill('30');
 await cropDialog.getByLabel('Margen inferior',{exact:true}).fill('40');
 await page.screenshot({path:join(tmpdir(),'reapdf-crop.png'),fullPage:true});
 await cropDialog.getByRole('button',{name:'Aplicar recorte',exact:true}).click();
 await expect(cropDialog).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await expect(page.getByText('360 × 440 pt',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByText('400 × 500 pt',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByText('360 × 440 pt',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const cropDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const cropOutput=join(tmpdir(),'reapdf-cropped.pdf');await (await cropDownload).saveAs(cropOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);assert (d[0].rect.width,d[0].rect.height)==(360,440);assert (d[3].rect.width,d[3].rect.height)==(460,340);assert d[3].rotation==90;assert 'Lote pagina 1' in d[0].get_text();p=d[0];assert next(p.annots()).info['content']=='Nota lote';assert d[1].rect.width==400`,cropOutput]);
 cropDialog=await cropOpen();await cropDialog.getByLabel('Páginas para recortar',{exact:true}).fill('1,4');
 await cropDialog.getByLabel('Modo de recorte',{exact:true}).selectOption('reset');
 await cropDialog.getByRole('button',{name:'Restaurar límites originales',exact:true}).click();
 await expect(cropDialog).toHaveCount(0);
 await expect(page.getByText('400 × 500 pt',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 // Retirar un bloque de dos páginas e importar un rango en orden explícito.
 await openTool(page,"Reemplazar páginas");
 const replacement=page.getByRole('dialog',{name:'Reemplazar páginas',exact:true});
 await replacement.getByLabel('PDF para reemplazar',{exact:true}).setInputFiles(extra);
 await expect(replacement.getByText('3 páginas disponibles',{exact:true})).toBeVisible();
 await replacement.getByLabel('Páginas de reemplazo',{exact:true}).fill('3,1');
 await replacement.getByLabel('Inicio del reemplazo',{exact:true}).selectOption('1');
 await replacement.getByLabel('Cantidad a reemplazar',{exact:true}).fill('2');
 await page.screenshot({path:join(tmpdir(),'reapdf-replace.png'),fullPage:true});
 await replacement.getByRole('button',{name:'Reemplazar páginas',exact:true}).click();
 await expect(replacement).toHaveCount(0);
 await expect(page.getByRole('form',{name:'Página 2 de 4',exact:true})).toBeVisible();
 await expect(page.locator('.text-layer span').filter({hasText:/^Anexo tres$/})).toBeVisible();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.locator('.text-layer span').filter({hasText:/^Lote pagina 2$/})).toBeVisible();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.locator('.text-layer span').filter({hasText:/^Anexo tres$/})).toBeVisible();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 // Dividir no debe marcar los cambios pendientes como exportados.
 await expect(page.getByText(/cambios · sin exportar/)).toBeVisible();
 await openTool(page,"Dividir PDF");
 const splitDialog=page.getByRole('dialog',{name:'Dividir PDF',exact:true});
 await splitDialog.getByLabel('Páginas por archivo',{exact:true}).fill('2');
 await expect(splitDialog.getByText('2 archivos PDF · 4 páginas incluidas',{exact:true})).toBeVisible();
 let zipDownload=page.waitForEvent('download');await splitDialog.getByRole('button',{name:'Descargar partes ZIP',exact:true}).click();
 const blocksZip=join(tmpdir(),'reapdf-split-blocks.zip');await (await zipDownload).saveAs(blocksZip);
 execFileSync(python,['-c',`from zipfile import ZipFile
import pymupdf as f,sys
with ZipFile(sys.argv[1]) as z:
 assert z.namelist()==['parte-001.pdf','parte-002.pdf']
 with f.open(stream=z.read('parte-001.pdf'),filetype='pdf') as d:
  assert len(d)==2;assert 'Lote pagina 1' in d[0].get_text();assert 'Anexo tres' in d[1].get_text();assert d[1].rotation==270
 with f.open(stream=z.read('parte-002.pdf'),filetype='pdf') as d:
  assert 'Anexo uno' in d[0].get_text();assert 'Lote pagina 4' in d[1].get_text();assert d[1].rotation==90`,blocksZip]);
 await splitDialog.getByLabel('Modo de división',{exact:true}).selectOption('groups');
 await splitDialog.getByLabel('Grupos para dividir',{exact:true}).fill('1,2\n2,3,4');
 await expect(splitDialog.getByRole('button',{name:'Descargar partes ZIP',exact:true})).toBeDisabled();
 await splitDialog.getByLabel('Grupos para dividir',{exact:true}).fill('4,1\n3,2');
 await page.screenshot({path:join(tmpdir(),'reapdf-split.png'),fullPage:true});
 zipDownload=page.waitForEvent('download');await splitDialog.getByRole('button',{name:'Descargar partes ZIP',exact:true}).click();
 const groupsZip=join(tmpdir(),'reapdf-split-groups.zip');await (await zipDownload).saveAs(groupsZip);
 execFileSync(python,['-c',`from zipfile import ZipFile
import pymupdf as f,sys
with ZipFile(sys.argv[1]) as z:
 with f.open(stream=z.read('parte-001.pdf'),filetype='pdf') as d:
  assert 'Lote pagina 4' in d[0].get_text();assert 'Lote pagina 1' in d[1].get_text();assert d[0].rotation==90;p=d[1];assert next(p.annots()).info['content']=='Nota lote'
 with f.open(stream=z.read('parte-002.pdf'),filetype='pdf') as d:
  assert 'Anexo uno' in d[0].get_text();assert 'Anexo tres' in d[1].get_text()`,groupsZip]);
 await splitDialog.getByRole('button',{name:'Cerrar',exact:true}).click();
 await expect(page.getByText(/cambios · sin exportar/)).toBeVisible();
 await expect(page.getByRole('form',{name:'Página 2 de 4',exact:true})).toBeVisible();
 // Anotaciones que ya venían en el PDF: propiedades, identidad e historial.
 const annotated=join(tmpdir(),'reapdf-existing.pdf');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open();p=d.new_page(width=400,height=500);p.insert_text((40,80),'Documento anotado',fontsize=16)
a=p.add_text_annot((60,140),'Nota importada');a.set_info(title='Autor externo');a.update()
a=p.add_highlight_annot(p.search_for('Documento',quads=True));a.set_info(title='Otro autor');a.update()
a=p.add_rect_annot(f.Rect(60,240,180,300));a.set_flags(a.flags|f.PDF_ANNOT_IS_LOCKED);a.update()
p.set_rotation(90);d.save(sys.argv[1])`,annotated]);
 page.once('dialog',dialog=>dialog.accept());
 await page.getByLabel('Archivo PDF').setInputFiles(annotated);
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Seleccionar marca");
 await page.getByLabel('Anotación existente',{exact:true}).selectOption({label:'1. Nota'});
 await expect(page.getByLabel('Contenido de nota existente',{exact:true})).toHaveValue('Nota importada');
 await page.getByLabel('Contenido de nota existente',{exact:true}).fill('Nota corregida desde Reapdf ✓');
 await page.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByLabel('Color de marca existente',{exact:true}).fill('#2288dd');
 await page.getByRole('button',{name:'Aplicar propiedades existentes',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByLabel('Anotación existente',{exact:true}).selectOption({label:'1. Nota'});
 await expect(page.getByLabel('Contenido de nota existente',{exact:true})).toHaveValue('Nota corregida desde Reapdf ✓');
 await expect(page.getByLabel('Color de marca existente',{exact:true})).toHaveValue('#ffff00');
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByLabel('Anotación existente',{exact:true}).selectOption({label:'3. Rectángulo · solo lectura'});
 await expect(page.getByText('La anotación está bloqueada o marcada como solo lectura.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Eliminar anotación existente',exact:true})).toHaveCount(0);
 // Selección real sobre el resaltado, incluso con la página girada.
 await page.getByRole('button',{name:/^Seleccionar anotación existente Resaltado /}).click();
 await page.getByRole('button',{name:'Eliminar anotación existente',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:/^Seleccionar anotación existente Resaltado /})).toHaveCount(0);
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:/^Seleccionar anotación existente Resaltado /})).toBeVisible();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const existingDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const existingOutput=join(tmpdir(),'reapdf-existing-edited.pdf');await (await existingDownload).saveAs(existingOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];aa=list(p.annots());assert [a.type[0] for a in aa]==[0,4];assert aa[0].info['content']=='Nota corregida desde Reapdf ✓';assert aa[0].info['title']=='Autor externo';assert max(abs(a-b) for a,b in zip(aa[0].colors['stroke'],[34/255,136/255,221/255]))<.001;assert aa[1].flags&f.PDF_ANNOT_IS_LOCKED;assert p.rotation==90;assert 'Documento anotado' in p.get_text()
s=f.open(sys.argv[2]);q=s[0];old=list(q.annots());assert len(old)==3;assert aa[0].info['id']==old[0].info['id'];assert aa[1].rect==old[2].rect;assert old[0].info['content']=='Nota importada'`,existingOutput,annotated]);
 // Reabrir una exportación debe permitir seguir editando sus anotaciones.
 await page.getByLabel('Archivo PDF').setInputFiles(existingOutput);
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Seleccionar marca");
 await page.getByLabel('Anotación existente',{exact:true}).selectOption({label:'1. Nota'});
 await expect(page.getByLabel('Contenido de nota existente',{exact:true})).toHaveValue('Nota corregida desde Reapdf ✓');
 await page.screenshot({path:join(tmpdir(),'reapdf-existing.png'),fullPage:true});
 // Fuente, tamaño y color: validación del PDF y del historial de estilo.
 await page.getByLabel('Archivo PDF').setInputFiles(sample);
 await page.getByAltText('Página 1 del documento').waitFor();
 await openTool(page,"Editar texto");
 await page.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await page.getByLabel('Nuevo texto',{exact:true}).fill('Nuevo');
 await page.getByLabel('Fuente de texto',{exact:true}).selectOption('tibo');
 await page.getByLabel('Tamaño de texto',{exact:true}).fill('22');
 await page.getByLabel('Color del texto',{exact:true}).fill('#cc2255');
 await page.getByRole('button',{name:'Aplicar cambio',exact:true}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await expect(page.getByLabel('Fuente de texto',{exact:true})).toHaveValue('tibo');
 await expect(page.getByLabel('Tamaño de texto',{exact:true})).toHaveValue('22');
 await expect(page.getByLabel('Color del texto',{exact:true})).toHaveValue('#cc2255');
 await page.getByLabel('Nuevo texto',{exact:true}).fill('Un texto demasiado largo para conservar la caja original');
 await page.getByRole('button',{name:'Aplicar cambio',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('no cabe');
 await page.getByRole('button',{name:'Cerrar error',exact:true}).click();
 await expect(page.getByRole('button',{name:'Deshacer',exact:false})).toBeDisabled();
 await page.getByRole('button',{name:'Cancelar',exact:true}).click();
 await page.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(page.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const styleDownload=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const styleFile=join(tmpdir(),'reapdf-style.pdf');await (await styleDownload).saveAs(styleFile);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];spans=[s for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans']];s=next(s for s in spans if s['text']=='Nuevo');assert s['font']=='Times-Bold';assert s['size']==22;assert s['color']==0xcc2255;assert 'Texto original' not in p.get_text();assert d[1].get_text().startswith('Segunda pagina')`,styleFile]);
 await page.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await page.screenshot({path:join(tmpdir(),'reapdf-text-style.png'),fullPage:true});
 // Nitidez real a DPR 2, zoom sin historial, paneles y borradores claros.
 const sharpContext=await browser.newContext({viewport:{width:1280,height:800},deviceScaleFactor:2});
 const sharp=await sharpContext.newPage();failurePage=sharp;sharp.setDefaultTimeout(20000);
 sharp.on('dialog',d=>d.accept());
 sharp.on('pageerror',e=>errors.push(e.message));
 let textRequests=0;sharp.on('request',r=>{if(r.url().endsWith('/pages/0/text'))textRequests++;});
 await sharp.goto(baseUrl);await sharp.getByLabel('Archivo PDF').setInputFiles(sample);
 const sharpImage=sharp.getByAltText('Página 1 del documento');
 await expect(sharpImage).toHaveAttribute('data-render-scale','2.5');
 await expect.poll(()=>sharpImage.evaluate(img=>img.naturalWidth)).toBeGreaterThanOrEqual(1487);
 const readCount=textRequests;
 await sharp.getByLabel('Nivel de zoom',{exact:true}).selectOption('200');
 await expect(sharpImage).toHaveAttribute('data-render-scale','5');
 await expect.poll(()=>sharpImage.evaluate(img=>img.naturalWidth)).toBe(2975);
 assert.equal(textRequests,readCount,'El zoom no debe volver a extraer el texto.');
 await expect(sharp.getByRole('button',{name:'Deshacer',exact:false})).toBeDisabled();
 await sharp.screenshot({path:join(tmpdir(),'reapdf-zoom-200.png')});
 // Respuestas antiguas no deben sustituir la última escala elegida.
 await sharp.getByLabel('Nivel de zoom',{exact:true}).selectOption('400');
 await sharp.getByLabel('Nivel de zoom',{exact:true}).selectOption('50');
 await sharp.getByLabel('Nivel de zoom',{exact:true}).selectOption('200');
 await expect(sharpImage).toHaveAttribute('data-render-scale','5');
 await sharp.getByRole('button',{name:'Página completa',exact:true}).click();
 await expect.poll(()=>sharpImage.evaluate(img=>img.getBoundingClientRect().height)).toBeLessThan(600);
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const fit=await sharp.locator('.paper-scroll').boundingBox(),paperFit=await sharpImage.boundingBox();
 assert.ok(paperFit.width<=fit.width && paperFit.height<=fit.height);
 assert.ok(await sharp.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+2));
 const undoBox=await sharp.getByRole('button',{name:'Deshacer',exact:false}).boundingBox();assert.ok(undoBox.y+undoBox.height<=800);
 await openTool(sharp,"Editar texto");
 await sharp.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await sharp.getByLabel('Nuevo texto',{exact:true}).fill('Sin aplicar');
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeDisabled();
 await expect(sharp.locator('.tool-guide')).toContainText('sin aplicar');
 await sharp.getByRole('button',{name:'Cancelar',exact:true}).click();
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(sharp,"Nota");
 let markBox=await sharp.getByLabel('Lienzo de anotaciones').boundingBox();
 await sharp.mouse.click(markBox.x+markBox.width/2,markBox.y+markBox.height/2);
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeDisabled();
 await sharp.getByRole('button',{name:'Cancelar nota',exact:true}).click();
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 // Un clic marca una palabra; un gesto horizontal a la altura del texto subraya.
 await openTool(sharp,"Resaltar");
 markBox=await sharp.getByLabel('Lienzo de anotaciones').boundingBox();
 await sharp.mouse.click(markBox.x+75/595*markBox.width,markBox.y+245/842*markBox.height);
 await sharp.getByText('1 cambios · sin exportar',{exact:true}).waitFor();
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await openTool(sharp,"Subrayar");
 markBox=await sharp.getByLabel('Lienzo de anotaciones').boundingBox();
 await sharp.mouse.move(markBox.x+60/595*markBox.width,markBox.y+272/842*markBox.height);await sharp.mouse.down();
 await sharp.mouse.move(markBox.x+200/595*markBox.width,markBox.y+272/842*markBox.height,{steps:8});await sharp.mouse.up();
 await sharp.getByText('2 cambios · sin exportar',{exact:true}).waitFor();
 await expect(sharp.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const sharpDownload=sharp.waitForEvent('download');await sharp.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const sharpOutput=join(tmpdir(),'reapdf-practical.pdf');await (await sharpDownload).saveAs(sharpOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];aa=list(p.annots());assert [a.type[0] for a in aa]==[8,9];assert len(aa[0].vertices)==4;assert 'Texto original' in p.get_text()`,sharpOutput]);
 await sharp.getByRole('button',{name:'Ajustar ancho',exact:true}).click();
 await expect.poll(()=>sharpImage.evaluate(img=>img.getBoundingClientRect().width)).toBeGreaterThan(500);
 await sharp.screenshot({path:join(tmpdir(),'reapdf-usability.png')});
 await sharpContext.close();
 // Imágenes originales: selección, controles, ratón, historial y PDF descargado.
 const imageFile=join(tmpdir(),'reapdf-image.png');
 execFileSync(python,['-c',`import pymupdf as f,sys
p=f.Pixmap(f.csRGB,f.IRect(0,0,160,80),False);p.clear_with(255);p.set_rect(f.IRect(0,0,80,80),(255,0,0));p.set_rect(f.IRect(80,0,160,80),(0,0,255));p.save(sys.argv[1])`,imageFile]);
 const imageContext=await browser.newContext({viewport:{width:1440,height:1080}});
 const imagePage=await imageContext.newPage();failurePage=imagePage;imagePage.setDefaultTimeout(20000);
 imagePage.on('dialog',d=>d.accept());
 imagePage.on('pageerror',e=>errors.push(e.message));
 await imagePage.goto(baseUrl);await imagePage.getByLabel('Archivo PDF').setInputFiles(sample);
 await imagePage.getByAltText('Página 1 del documento').waitFor();
 await openTool(imagePage,"Imágenes");
 await imagePage.getByLabel('Archivo de imagen').setInputFiles(imageFile);
 await expect(imagePage.getByText('1 cambios · sin exportar',{exact:true})).toBeVisible();
 await expect(imagePage.getByLabel('Ancho de marca')).toHaveValue('160');
 await imagePage.getByLabel('Posición X',{exact:true}).fill('60');
 await imagePage.getByLabel('Posición Y',{exact:true}).fill('360');
 await imagePage.getByLabel('Ancho de marca').fill('240');await imagePage.getByLabel('Alto de marca').fill('120');
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeDisabled();
 await imagePage.getByRole('button',{name:'Aplicar posición y tamaño',exact:true}).click();
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 let imageCanvas=await imagePage.getByLabel('Lienzo de anotaciones').boundingBox();
 const mover=imagePage.getByRole('button',{name:'Tirador para mover marca',exact:true});
 let handle=await mover.boundingBox();await imagePage.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await imagePage.mouse.down();
 await imagePage.mouse.move(handle.x+handle.width/2+30/595*imageCanvas.width,handle.y+handle.height/2+20/842*imageCanvas.height,{steps:6});await imagePage.mouse.up();
 await expect.poll(async()=>Number(await imagePage.getByLabel('Posición X',{exact:true}).inputValue())).toBeCloseTo(90,1);
 await expect.poll(async()=>Number(await imagePage.getByLabel('Posición Y',{exact:true}).inputValue())).toBeCloseTo(380,1);
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const resize=imagePage.getByRole('button',{name:'Redimensionar marca',exact:true});
 handle=await resize.boundingBox();await imagePage.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await imagePage.mouse.down();
 await imagePage.mouse.move(handle.x+handle.width/2+40/595*imageCanvas.width,handle.y+handle.height/2+20/842*imageCanvas.height,{steps:6});await imagePage.mouse.up();
 await expect.poll(async()=>Number(await imagePage.getByLabel('Ancho de marca').inputValue())).toBeCloseTo(280,1);
 await expect.poll(async()=>Number(await imagePage.getByLabel('Alto de marca').inputValue())).toBeCloseTo(140,1);
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await imagePage.getByRole('button',{name:'Eliminar imagen',exact:true}).click();
 await expect(imagePage.getByText('0 cambios',{exact:true})).toBeVisible();
 await imagePage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await imagePage.getByLabel('Imagen de la sesión').selectOption({index:1});
 await expect(imagePage.getByLabel('Ancho de marca')).toHaveValue(/279|280/);
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const imageDownload=imagePage.waitForEvent('download');await imagePage.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const imageOutput=join(tmpdir(),'reapdf-inserted-image.pdf');await (await imageDownload).saveAs(imageOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];ii=p.get_images();assert len(ii)==1;assert ii[0][2:4]==(160,80);r=p.get_image_rects(ii[0][0])[0];assert abs(r.x0-90)<.1 and abs(r.y0-380)<.1 and abs(r.width-280)<.1 and abs(r.height-140)<.1;assert 'Texto original' in p.get_text();assert len(d)==2;assert 'Segunda pagina' in d[1].get_text();pix=p.get_pixmap();assert pix.pixel(100,390)==(255,0,0);assert pix.pixel(350,390)==(0,0,255)`,imageOutput]);
 await imagePage.screenshot({path:join(tmpdir(),'reapdf-images.png')});
 // Proyecto descargable, rechazo de archivo dañado y controles editables al volver a abrir.
 const projectDownload=imagePage.waitForEvent('download');
 await imagePage.locator('.session-bar').getByRole('button',{name:'Guardar proyecto',exact:true}).click();
 const projectOutput=join(tmpdir(),'reapdf-work.reapdf');await (await projectDownload).saveAs(projectOutput);
 execFileSync(python,['-c',`from backend.projects import read_project;from pathlib import Path;import sys
base,ops,manifest=read_project(Path(sys.argv[1]).read_bytes());assert len(ops)==1 and ops[0]['type']=='image';assert ops[0]['pixels']==[160,80];assert manifest['state']['zoom']==1`,projectOutput]);
 await imagePage.getByLabel('Archivo de proyecto').setInputFiles({name:'bad.reapdf',mimeType:'application/zip',buffer:Buffer.from('bad project')});
 await expect(imagePage.getByRole('alert').filter({hasText:'proyecto'})).toBeVisible();
 await expect(imagePage.getByLabel('Ancho de marca')).toHaveValue(/279|280/);
 await imagePage.getByLabel('Cerrar error').click();
 await imagePage.getByLabel('Archivo PDF').setInputFiles(sample);
 await expect(imagePage.getByText('0 cambios',{exact:true})).toBeVisible();
 await imagePage.getByLabel('Archivo de proyecto').setInputFiles(projectOutput);
 await openTool(imagePage,"Imágenes");
 await imagePage.getByLabel('Imagen de la sesión').selectOption({index:1});
 await expect(imagePage.getByLabel('Ancho de marca')).toHaveValue(/279|280/);
 await openTool(imagePage,"Editar texto");
 await imagePage.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await imagePage.getByLabel('Nuevo texto').fill('Retomado');await imagePage.getByRole('button',{name:'Aplicar cambio',exact:true}).click();
 await expect(imagePage.locator('.session-bar')).toContainText('Recuperación local actualizada');
 await imagePage.reload();
 await imagePage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();
 await expect(imagePage.getByText('2 cambios · sin exportar',{exact:true})).toBeVisible();
 await openTool(imagePage,"Editar texto");
 await imagePage.getByRole('button',{name:'Editar: Texto original',exact:true}).click();
 await expect(imagePage.getByLabel('Nuevo texto')).toHaveValue('Retomado');
 await imagePage.getByRole('button',{name:'Cancelar',exact:true}).click();
 // Hojas en blanco y duplicación de la versión ya editada, con deshacer/rehacer.
 await openTool(imagePage,"Página en blanco");
 const blankDialog=imagePage.getByRole('dialog',{name:'Insertar páginas en blanco',exact:true});
 await blankDialog.getByLabel('Cantidad de páginas en blanco').fill('2');
 await blankDialog.getByLabel('Tamaño de página en blanco').selectOption('letter');
 await blankDialog.getByLabel('Ubicación de páginas nuevas').selectOption('1');
 await blankDialog.getByRole('button',{name:'Insertar hojas en blanco',exact:true}).click();
 await expect(imagePage.getByRole('form',{name:'Página 2 de 4',exact:true})).toBeVisible();
 await openTool(imagePage,"Duplicar páginas");
 const duplicateDialog=imagePage.getByRole('dialog',{name:'Duplicar páginas',exact:true});
 await duplicateDialog.getByLabel('Páginas para duplicar').fill('1');
 await duplicateDialog.getByLabel('Ubicación de páginas nuevas').selectOption('4');
 await duplicateDialog.getByRole('button',{name:'Aplicar duplicación',exact:true}).click();
 await expect(imagePage.getByRole('form',{name:'Página 5 de 5',exact:true})).toBeVisible();
 await imagePage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(imagePage.getByRole('form',{name:'Página 4 de 4',exact:true})).toBeVisible();
 await imagePage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(imagePage.getByRole('form',{name:'Página 2 de 2',exact:true})).toBeVisible();
 await imagePage.getByRole('button',{name:'Rehacer',exact:false}).click();
 await imagePage.getByRole('button',{name:'Rehacer',exact:false}).click();
 await expect(imagePage.getByRole('form',{name:'Página 2 de 5',exact:true})).toBeVisible();
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 // Ctrl+S guarda un proyecto, no el HTML del navegador.
 const shortcutDownload=imagePage.waitForEvent('download');await imagePage.keyboard.press('Control+s');
 const finalProject=join(tmpdir(),'reapdf-expanded.reapdf');await(await shortcutDownload).saveAs(finalProject);
 // Impresión abre el PDF editado, con las hojas vacías y su copia completa.
 await expect(imagePage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 const printedResponse=imagePage.waitForResponse(r=>r.url().endsWith('/print'));
 const popupEvent=imagePage.waitForEvent('popup');await imagePage.keyboard.press('Control+p');
 const printPopup=await popupEvent;await printPopup.waitForURL(/^blob:/);
 const response=await printedResponse;assert.equal(response.status(),200);
 const printBytes=Buffer.from(await imagePage.evaluate(async url=>Array.from(new Uint8Array(await(await fetch(url)).arrayBuffer())),printPopup.url()));
 assert.ok(printBytes.length>100,'La ventana de impresión debe contener el PDF real.');
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(stream=sys.stdin.buffer.read());assert len(d)==5;assert 'Retomado' in d[0].get_text() and 'Retomado' in d[4].get_text();assert d[0].get_images()[0][2:4]==(160,80) and d[4].get_images()[0][2:4]==(160,80)
for i in [1,2]:
 p=d[i];assert not p.get_text() and not p.get_images();assert (p.rect.width,p.rect.height)==(612,792)`,],{input:printBytes});
 await printPopup.close();
 // Fallo de almacenamiento: conserva la sesión, permite guardar proyecto y reintentar.
 let failCheckpoint=true;
 await imagePage.route('**/api/documents/*/recovery',async route=>{
  if(failCheckpoint){failCheckpoint=false;await route.fulfill({status:507,contentType:'application/json',body:JSON.stringify({detail:'Almacenamiento de prueba lleno.'})});}
  else await route.continue();
 });
 await openTool(imagePage,"Nota");
 const noteCanvas=await imagePage.getByLabel('Lienzo de anotaciones').boundingBox();
 await imagePage.mouse.click(noteCanvas.x+noteCanvas.width*.3,noteCanvas.y+noteCanvas.height*.4);
 await imagePage.getByLabel('Contenido de la nota').fill('Sesión recuperable');
 await imagePage.getByRole('button',{name:'Guardar nota',exact:true}).click();
 await expect(imagePage.locator('.session-bar')).toContainText('Recuperación automática no disponible');
 await expect(imagePage.getByRole('alert').filter({hasText:'Almacenamiento de prueba lleno.'})).toBeVisible();
 const fallbackDownload=imagePage.waitForEvent('download');await imagePage.locator('.session-bar').getByRole('button',{name:'Guardar proyecto',exact:true}).click();
 const fallbackProject=join(tmpdir(),'reapdf-fallback.reapdf');await(await fallbackDownload).saveAs(fallbackProject);
 execFileSync(python,['-c',`from backend.projects import read_project;from pathlib import Path;import sys
base,ops,manifest=read_project(Path(sys.argv[1]).read_bytes());assert ops[0]['type']=='note' and ops[0]['content']=='Sesión recuperable'`,fallbackProject]);
 await imagePage.getByRole('button',{name:'Reintentar recuperación',exact:true}).click();
 await expect(imagePage.locator('.session-bar')).toContainText('Recuperación local actualizada');
 await imagePage.unroute('**/api/documents/*/recovery');
 await imagePage.screenshot({path:join(tmpdir(),'reapdf-session-pages.png')});
 await imageContext.close();
 // Reinicio real del servidor: se eliminan los temporales, se conserva el checkpoint.
 if(server) {
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('El servidor no terminó para probar recuperación.')),10000);server.once('exit',()=>{clearTimeout(timer);resolve();});server.kill('SIGINT');});
  server=startServer();
  let restarted=false;
  for(let i=0;i<50;i++){try{const r=await fetch(baseUrl+'/api/health');if(r.ok){restarted=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,200));}
  assert.ok(restarted);
  const recoveredContext=await browser.newContext({viewport:{width:1440,height:1080}}),recoveredPage=await recoveredContext.newPage();
  failurePage=recoveredPage;recoveredPage.on('pageerror',e=>errors.push(e.message));recoveredPage.on('dialog',d=>d.accept());
  await recoveredPage.goto(baseUrl);await recoveredPage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();
  await expect(recoveredPage.getByRole('form',{name:'Página 2 de 5',exact:true})).toBeVisible();
  await recoveredPage.getByLabel('Página anterior').click();
  await expect(recoveredPage.locator('.text-layer')).toContainText('Retomado');
  await recoveredContext.close();
 }
 // Texto nuevo, sellos y enlaces: interacción, persistencia y PDF nativo.
 const contentContext=await browser.newContext({viewport:{width:1440,height:1080}});
 const contentPage=await contentContext.newPage();failurePage=contentPage;contentPage.setDefaultTimeout(20000);
 contentPage.on('dialog',d=>d.accept());contentPage.on('pageerror',e=>errors.push(e.message));
 await contentPage.goto(baseUrl);await contentPage.getByLabel('Archivo PDF').setInputFiles(sample);
 await contentPage.getByAltText('Página 1 del documento').waitFor();
 const drawContent=async(tool,a,b)=>{
  await openTool(contentPage,tool);
  await expect(contentPage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
  const canvas=await contentPage.getByLabel('Lienzo de anotaciones').boundingBox();
  await contentPage.mouse.move(canvas.x+a[0]/595*canvas.width,canvas.y+a[1]/842*canvas.height);await contentPage.mouse.down();
  await contentPage.mouse.move(canvas.x+b[0]/595*canvas.width,canvas.y+b[1]/842*canvas.height,{steps:6});await contentPage.mouse.up();
 };
 await drawContent('Añadir texto',[60,390],[380,485]);
 await contentPage.getByLabel('Texto de la caja').fill('Texto agregado\nLinea nueva');
 await contentPage.getByLabel('Fuente de texto nuevo').selectOption('tibo');
 await contentPage.getByLabel('Tamaño de texto nuevo').fill('18');
 await contentPage.getByLabel('Alineación de texto nuevo').selectOption('1');
 await expect(contentPage.getByRole('button',{name:'Exportar copia',exact:true})).toBeDisabled();
 await contentPage.getByRole('button',{name:'Aplicar texto nuevo',exact:true}).click();
 await expect(contentPage.getByText('1 cambios · sin exportar',{exact:true})).toBeVisible();
 await contentPage.getByLabel('Texto de la caja').fill('Texto actualizado\nLinea nueva');
 await contentPage.getByLabel('Posición X',{exact:true}).fill('70');
 await contentPage.getByRole('button',{name:'Aplicar texto nuevo',exact:true}).click();
 await expect(contentPage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 // Movimiento con teclado conserva el contenido ya aplicado.
 await contentPage.getByRole('button',{name:'Mover marca',exact:true}).focus();await contentPage.keyboard.press('ArrowRight');
 await expect(contentPage.getByLabel('Posición X',{exact:true})).toHaveValue('71');
 await expect(contentPage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await drawContent('Sellos',[60,530],[300,600]);
 await contentPage.getByLabel('Tipo de sello').selectOption('draft');
 await contentPage.getByRole('button',{name:'Aplicar sello',exact:true}).click();
 await expect(contentPage.getByText('2 cambios · sin exportar',{exact:true})).toBeVisible();
 await drawContent('Enlaces',[60,625],[250,660]);
 await contentPage.getByLabel('Destino del enlace').selectOption('page');
 await contentPage.getByLabel('Página de destino del enlace').selectOption({value:'1'});
 await contentPage.getByRole('button',{name:'Aplicar enlace',exact:true}).click();
 await expect(contentPage.getByText('3 cambios · sin exportar',{exact:true})).toBeVisible();
 await contentPage.getByRole('button',{name:'Crear otro elemento',exact:true}).click();
 let linkCanvas=await contentPage.getByLabel('Lienzo de anotaciones').boundingBox();
 await contentPage.mouse.move(linkCanvas.x+300/595*linkCanvas.width,linkCanvas.y+625/842*linkCanvas.height);await contentPage.mouse.down();
 await contentPage.mouse.move(linkCanvas.x+500/595*linkCanvas.width,linkCanvas.y+660/842*linkCanvas.height,{steps:6});await contentPage.mouse.up();
 await contentPage.getByLabel('Dirección del enlace').fill('https://example.com/reapdf');
 await contentPage.getByRole('button',{name:'Aplicar enlace',exact:true}).click();
 await expect(contentPage.getByText('4 cambios · sin exportar',{exact:true})).toBeVisible();
 await openTool(contentPage,"Lectura");
 await expect(contentPage.getByRole('link',{name:'Abrir enlace: https://example.com/reapdf',exact:true})).toHaveAttribute('rel','noopener noreferrer');
 await contentPage.getByRole('link',{name:'Ir al destino: página 2',exact:true}).click();
 await expect(contentPage.getByRole('form',{name:'Página 2 de 2',exact:true})).toBeVisible();
 await contentPage.getByLabel('Página anterior').click();
 await expect(contentPage.locator('.text-layer')).toContainText('Texto actualizado');
 const contentDownload=contentPage.waitForEvent('download');await contentPage.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const contentOutput=join(tmpdir(),'reapdf-content-tools.pdf');await(await contentDownload).saveAs(contentOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];assert 'Texto actualizado' in p.get_text() and 'Texto original' in p.get_text();assert not p.get_images();aa=list(p.annots());assert len(aa)==1 and aa[0].type[0]==f.PDF_ANNOT_STAMP and 'DRAFT' in aa[0].info['content'];links=p.get_links();assert len(links)==2;assert any(l.get('page')==1 for l in links) and any(l.get('uri')=='https://example.com/reapdf' for l in links);s=next(s for b in p.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='Texto actualizado');assert s['font']=='Times-Bold' and s['size']==18`,contentOutput]);
 const contentProjectDownload=contentPage.waitForEvent('download');await contentPage.locator('.session-bar').getByRole('button',{name:'Guardar proyecto',exact:true}).click();
 const contentProject=join(tmpdir(),'reapdf-content-tools.reapdf');await(await contentProjectDownload).saveAs(contentProject);
 await contentPage.getByLabel('Archivo de proyecto').setInputFiles(contentProject);
 await openTool(contentPage,"Añadir texto");
 await contentPage.getByLabel('Elemento de contenido').selectOption({index:1});
 await expect(contentPage.getByLabel('Texto de la caja')).toHaveValue('Texto actualizado\nLinea nueva');
 await contentPage.getByLabel('Texto de la caja').fill('Retomado nuevo');await contentPage.getByRole('button',{name:'Aplicar texto nuevo',exact:true}).click();
 await expect(contentPage.getByRole('button',{name:'Exportar copia',exact:true})).toBeEnabled();
 await contentPage.getByRole('button',{name:'Eliminar elemento',exact:true}).click();
 await expect(contentPage.getByText('3 cambios · sin exportar',{exact:true})).toBeVisible();
 await contentPage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(contentPage.getByText('4 cambios · sin exportar',{exact:true})).toBeVisible();
 await openTool(contentPage,"Lectura");
 await expect(contentPage.locator('.text-layer')).toContainText('Retomado nuevo');
 await contentPage.screenshot({path:join(tmpdir(),'reapdf-content-tools.png')});
 await expect(contentPage.locator('.session-bar')).toContainText('Recuperación local actualizada');
 await contentPage.reload();await contentPage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();
 await openTool(contentPage,"Enlaces");
 await contentPage.getByLabel('Elemento de contenido').selectOption({index:2});
 await expect(contentPage.getByLabel('Dirección del enlace')).toHaveValue('https://example.com/reapdf');
 await contentContext.close();
 // Marcadores, encabezados y numeración: edición reversible, PDF nativo y proyecto.
 const documentContext=await browser.newContext({viewport:{width:1440,height:1080}});
 const documentPage=await documentContext.newPage();failurePage=documentPage;documentPage.setDefaultTimeout(20000);
 documentPage.on('dialog',d=>d.accept());documentPage.on('pageerror',e=>errors.push(e.message));
 await documentPage.goto(baseUrl);await documentPage.getByLabel('Archivo PDF').setInputFiles(sample);
 await documentPage.getByAltText('Página 1 del documento').waitFor();
 await openTool(documentPage,"Editar marcadores");
 await documentPage.getByLabel('Título del marcador').fill('Resumen');
 await documentPage.getByLabel('Página del marcador').selectOption({value:'1'});
 await documentPage.getByLabel('Marcador en negrita').check();
 await documentPage.getByRole('button',{name:'Añadir submarcador',exact:true}).click();
 await documentPage.getByLabel('Título del marcador').fill('Detalle del informe');
 await documentPage.getByLabel('Página del marcador').selectOption({value:'0'});
 await documentPage.getByRole('button',{name:'Disminuir nivel',exact:true}).click();
 await expect(documentPage.getByRole('button',{name:'Subir rama',exact:true})).toBeEnabled();
 await documentPage.getByRole('button',{name:'Aumentar nivel',exact:true}).click();
 await documentPage.getByRole('button',{name:'Aplicar marcadores',exact:true}).click();
 await expect(documentPage.getByRole('dialog')).toHaveCount(0);
 await documentPage.getByRole('tab',{name:'Marcadores',exact:true}).click();
 await expect(documentPage.getByRole('button',{name:'Resumen Pág. 2',exact:true})).toBeVisible();
 await documentPage.getByRole('button',{name:'Resumen Pág. 2',exact:true}).click();
 await expect(documentPage.getByRole('form',{name:'Página 2 de 2',exact:true})).toBeVisible();
 await documentPage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(documentPage.getByRole('button',{name:'Inicio Pág. 1',exact:true})).toBeVisible();
 await documentPage.getByRole('button',{name:'Rehacer',exact:false}).click();
 await documentPage.getByRole('button',{name:'Detalle del informe Pág. 1',exact:true}).click();
 await expect(documentPage.getByRole('form',{name:'Página 1 de 2',exact:true})).toBeVisible();
 await openTool(documentPage,"Numerar páginas");
 await expect(documentPage.getByLabel('Pie central')).toHaveValue('Página {numero} de {total}');
 let modalSaves=0;documentPage.on('request',r=>{if(r.url().endsWith('/project'))modalSaves++;});
 await documentPage.keyboard.press('Control+s');
 await documentPage.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 assert.equal(modalSaves,0,'No guardar a espaldas de un diálogo con cambios sin aplicar');
 await documentPage.getByLabel('Encabezado central').fill('Informe personal');
 await documentPage.getByLabel('Inicio de numeración').fill('5');
 await documentPage.getByLabel('Dígitos de numeración').fill('3');
 await expect(documentPage.getByRole('button',{name:'Aplicar encabezados y pies',exact:true})).toBeDisabled();
 await documentPage.getByRole('button',{name:'Actualizar vista previa',exact:true}).click();
 await expect(documentPage.getByAltText('Vista previa de encabezados y pies')).toBeVisible();
 await expect(documentPage.getByRole('button',{name:'Aplicar encabezados y pies',exact:true})).toBeEnabled();
 await documentPage.getByLabel('Encabezado central').fill('Informe revisado');
 await expect(documentPage.getByRole('button',{name:'Aplicar encabezados y pies',exact:true})).toBeDisabled();
 await documentPage.getByRole('button',{name:'Actualizar vista previa',exact:true}).click();
 await expect(documentPage.getByRole('button',{name:'Aplicar encabezados y pies',exact:true})).toBeEnabled();
 await expect(documentPage.getByRole('link',{name:'Ampliar vista previa',exact:true})).toHaveAttribute('rel','noopener noreferrer');
 await documentPage.screenshot({path:join(tmpdir(),'reapdf-headers-preview.png')});
 await documentPage.getByRole('button',{name:'Aplicar encabezados y pies',exact:true}).click();
 await expect(documentPage.locator('.text-layer')).toContainText('Informe revisado');
 await expect(documentPage.locator('.text-layer')).toContainText('Página 005 de 2');
 await documentPage.getByLabel('Página siguiente').click();
 await expect(documentPage.locator('.text-layer')).toContainText('Página 006 de 2');
 await openTool(documentPage,"Encabezados y pies");
 await expect(documentPage.getByLabel('Encabezado central')).toHaveValue('Informe revisado');
 await documentPage.getByRole('button',{name:'Quitar configuración de sesión',exact:true}).click();
 await expect(documentPage.locator('.text-layer')).not.toContainText('Página 006 de 2');
 await documentPage.getByRole('button',{name:'Deshacer',exact:false}).click();
 await expect(documentPage.locator('.text-layer')).toContainText('Página 006 de 2');
 const documentDownload=documentPage.waitForEvent('download');await documentPage.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const documentOutput=join(tmpdir(),'reapdf-bookmarks-headers.pdf');await(await documentDownload).saveAs(documentOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);assert d.get_toc()==[[1,'Resumen',2],[2,'Detalle del informe',1],[1,'Segunda pagina',2]];assert d.get_toc(False)[0][3]['bold'];assert d[0].get_text().count('Informe revisado')==1 and 'Página 005 de 2' in d[0].get_text();assert 'Página 006 de 2' in d[1].get_text();assert 'Texto original' in d[0].get_text();assert all(not p.get_images() for p in d)`,documentOutput]);
 const documentProjectDownload=documentPage.waitForEvent('download');await documentPage.locator('.session-bar').getByRole('button',{name:'Guardar proyecto',exact:true}).click();
 const documentProject=join(tmpdir(),'reapdf-bookmarks-headers.reapdf');await(await documentProjectDownload).saveAs(documentProject);
 await documentPage.getByLabel('Archivo de proyecto').setInputFiles(documentProject);
 await expect(documentPage.getByRole('button',{name:'Resumen Pág. 2',exact:true})).toBeVisible();
 await openTool(documentPage,"Encabezados y pies");
 await expect(documentPage.getByLabel('Inicio de numeración')).toHaveValue('5');
 await expect(documentPage.getByLabel('Dígitos de numeración')).toHaveValue('3');
 await documentPage.getByRole('button',{name:'Cancelar',exact:true}).click();
 await openTool(documentPage,"Editar marcadores");
 await expect(documentPage.getByLabel('Título del marcador')).toHaveValue('Resumen');
 await documentPage.getByLabel('Título del marcador').fill('Cambio cancelado');
 await documentPage.getByRole('button',{name:'Cancelar',exact:true}).click();
 await expect(documentPage.getByRole('button',{name:'Resumen Pág. 2',exact:true})).toBeVisible();
 await expect(documentPage.locator('.session-bar')).toContainText('Recuperación local actualizada');
 await documentPage.reload();await documentPage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();
 await documentPage.getByRole('tab',{name:'Marcadores',exact:true}).click();
 await expect(documentPage.getByRole('button',{name:'Resumen Pág. 2',exact:true})).toBeVisible();
 await expect(documentPage.locator('.text-layer')).toContainText('Página 006 de 2');
 await documentPage.screenshot({path:join(tmpdir(),'reapdf-bookmarks-headers.png')});
 await documentContext.close();
 // Formularios: valores PDF reales, apariencia, historial, proyecto y recuperación.
 const formSample=join(tmpdir(),'reapdf-form-ui.pdf');execFileSync(python,['scripts/create_form_sample.py',formSample]);
 const formContext=await browser.newContext({viewport:{width:1440,height:1080}});
 const formPage=await formContext.newPage();failurePage=formPage;formPage.setDefaultTimeout(20000);
 formPage.on('dialog',d=>d.accept());formPage.on('pageerror',e=>errors.push(e.message));
 await formPage.goto(baseUrl);await formPage.getByLabel('Archivo PDF').setInputFiles(formSample);
 await formPage.getByAltText('Página 1 del documento').waitFor();
 await openTool(formPage,"Rellenar formulario");
 await expect(formPage.getByLabel('Campo del formulario')).toHaveValue('0');
 await formPage.getByLabel('Valor del formulario').fill('Ana Pérez');
 await formPage.getByLabel('Campo del formulario').selectOption({value:'1'});await formPage.getByLabel('Casilla del formulario').check();
 await formPage.getByLabel('Campo del formulario').selectOption({value:'2'});await formPage.getByLabel('Valor del formulario').selectOption({value:'BOG'});
 await formPage.getByLabel('Campo del formulario').selectOption({value:'3'});await formPage.getByLabel('Valor del formulario').fill('Primera línea\nSegunda línea');
 await formPage.getByLabel('Campo del formulario').selectOption({value:'4'});
 await expect(formPage.getByRole('dialog').getByRole('status')).toContainText('Campo de solo lectura.');
 await expect(formPage.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeDisabled();
 await formPage.getByRole('button',{name:'Vista previa del formulario',exact:true}).click();
 await expect(formPage.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeEnabled();
 await formPage.screenshot({path:join(tmpdir(),'reapdf-forms-preview.png')});
 await formPage.getByRole('button',{name:'Aplicar formulario',exact:true}).click();
 await expect(formPage.locator('.text-layer')).toContainText('Ana Pérez');
 await formPage.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(formPage.locator('.text-layer')).not.toContainText('Ana Pérez');
 await formPage.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(formPage.locator('.text-layer')).toContainText('Ana Pérez');
 const formPdfDownload=formPage.waitForEvent('download');await formPage.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const formOutput=join(tmpdir(),'reapdf-filled-form.pdf');await(await formPdfDownload).saveAs(formOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);p=d[0];ww={w.field_name:w for w in p.widgets()};assert len(ww)==5 and ww['Nombre'].field_value=='Ana Pérez';assert ww['Acepto'].field_value==ww['Acepto'].on_state();assert ww['Ciudad'].field_value=='BOG';assert ww['Notas'].field_value.splitlines()==['Primera línea','Segunda línea'];assert 'Ana Pérez' in p.get_text();assert ww['Referencia'].field_flags&1;assert not p.get_images()`,formOutput]);
 const formProjectDownload=formPage.waitForEvent('download');await formPage.locator('.session-bar').getByRole('button',{name:'Guardar proyecto',exact:true}).click();
 const formProject=join(tmpdir(),'reapdf-filled-form.reapdf');await(await formProjectDownload).saveAs(formProject);
 await formPage.getByLabel('Archivo de proyecto').setInputFiles(formProject);
 await openTool(formPage,"Rellenar formulario");await expect(formPage.getByLabel('Valor del formulario')).toHaveValue('Ana Pérez');
 await formPage.getByLabel('Valor del formulario').fill('');await formPage.getByRole('button',{name:'Vista previa del formulario',exact:true}).click();
 await expect(formPage.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeEnabled();await formPage.getByRole('button',{name:'Aplicar formulario',exact:true}).click();
 await expect(formPage.locator('.text-layer')).not.toContainText('Ana Pérez');
 await formPage.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(formPage.locator('.text-layer')).toContainText('Ana Pérez');
 await expect(formPage.locator('.session-bar')).toContainText('Recuperación local actualizada');
 await formPage.reload();await formPage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();
 await openTool(formPage,"Rellenar formulario");await expect(formPage.getByLabel('Valor del formulario')).toHaveValue('Ana Pérez');
 await formPage.getByRole('button',{name:'Cancelar',exact:true}).click();
 // Exportar la versión rellena como PNG con medidas y apariencia exactas.
 await openTool(formPage,"Exportar páginas como imágenes");
 await formPage.getByLabel('Resolución de imágenes exportadas').selectOption({value:'72'});
 const formImagesDownload=formPage.waitForEvent('download');await formPage.getByRole('button',{name:'Descargar imágenes en ZIP',exact:true}).click();
 const formImagesOutput=join(tmpdir(),'reapdf-form-images.zip');await(await formImagesDownload).saveAs(formImagesOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys,zipfile
d=f.open(sys.argv[1]);z=zipfile.ZipFile(sys.argv[2]);pix=f.Pixmap(z.read(z.namelist()[0]));assert pix.width==595 and pix.height==842;assert pix.samples==d[0].get_pixmap(alpha=False).samples`,formOutput,formImagesOutput]);
 await formContext.close();
 // Crear PDF desde imágenes, reordenarlas y exportar un rango inverso a JPEG.
 const imageA=join(tmpdir(),'reapdf-create-a.png'),imageB=join(tmpdir(),'reapdf-create-b.jpg');
 execFileSync(python,['-c',`import pymupdf as f,sys
for path,w,h in [(sys.argv[1],600,400),(sys.argv[2],300,500)]:
 p=f.Pixmap(f.csRGB,f.IRect(0,0,w,h),False);p.clear_with(150);p.save(path)`,imageA,imageB]);
 const conversionContext=await browser.newContext({viewport:{width:1440,height:1080}});
 const conversionPage=await conversionContext.newPage();failurePage=conversionPage;conversionPage.setDefaultTimeout(20000);
 conversionPage.on('dialog',d=>d.accept());conversionPage.on('pageerror',e=>errors.push(e.message));
 await conversionPage.goto(baseUrl);await conversionPage.getByRole('button',{name:'Crear PDF desde imágenes',exact:true}).click();
 await conversionPage.getByLabel('Imágenes para crear PDF').setInputFiles([imageA,imageB]);
 await expect(conversionPage.locator('.conversion-file-list li')).toHaveCount(2);
 await conversionPage.getByLabel('Subir imagen 2').click();
 await expect(conversionPage.locator('.conversion-file-list li').first()).toContainText('reapdf-create-b.jpg');
 await conversionPage.getByLabel('Papel del PDF de imágenes').selectOption({value:'image'});
 await conversionPage.getByLabel('Resolución del PDF de imágenes').selectOption({value:'150'});
 await conversionPage.getByLabel('Margen del PDF de imágenes').fill('0');
 await conversionPage.getByRole('button',{name:'Crear y abrir PDF',exact:true}).click();
 await expect(conversionPage.getByRole('form',{name:'Página 1 de 2',exact:true})).toBeVisible();
 const createdDownload=conversionPage.waitForEvent('download');await conversionPage.getByRole('button',{name:'Exportar copia',exact:true}).click();
 const createdOutput=join(tmpdir(),'reapdf-created-images.pdf');await(await createdDownload).saveAs(createdOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open(sys.argv[1]);assert len(d)==2;assert d[0].get_images()[0][2:4]==(300,500);assert d[1].get_images()[0][2:4]==(600,400);assert abs(d[0].rect.width-144)<.001 and abs(d[0].rect.height-240)<.001;assert d.extract_image(d[0].get_images()[0][0])['image']==open(sys.argv[2],'rb').read()`,createdOutput,imageB]);
 await openTool(conversionPage,"Exportar páginas como imágenes");
 await conversionPage.getByLabel('Páginas para exportar imágenes').fill('2, 1');
 await conversionPage.getByLabel('Formato de imágenes exportadas').selectOption({value:'jpeg'});
 await conversionPage.getByLabel('Resolución de imágenes exportadas').selectOption({value:'150'});
 await conversionPage.getByLabel('Calidad JPEG exportada').fill('95');
 const convertedDownload=conversionPage.waitForEvent('download');await conversionPage.getByRole('button',{name:'Descargar imágenes en ZIP',exact:true}).click();
 const convertedOutput=join(tmpdir(),'reapdf-created-image-pages.zip');await(await convertedDownload).saveAs(convertedOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys,zipfile
z=zipfile.ZipFile(sys.argv[1]);names=z.namelist();assert len(names)==2 and 'pagina-002' in names[0] and all(n.endswith('.jpg') for n in names);a=f.Pixmap(z.read(names[0]));b=f.Pixmap(z.read(names[1]));assert (a.width,a.height)==(600,400) and (b.width,b.height)==(300,500);assert a.xres==a.yres==150`,convertedOutput]);
 await conversionPage.screenshot({path:join(tmpdir(),'reapdf-image-conversions.png')});
 await conversionContext.close();
 // Bloque largo: datos, aplanado, creación de campos, marca, propiedades, cifrado y comparación.
 const longForm=join(tmpdir(),'reapdf-long-form.pdf');execFileSync(python,['scripts/create_form_sample.py',longForm]);
 const longContext=await browser.newContext({viewport:{width:1440,height:1080}}),longPage=await longContext.newPage();failurePage=longPage;longPage.setDefaultTimeout(20000);longPage.on('pageerror',e=>errors.push(e.message));longPage.on('dialog',d=>d.accept());
 await longPage.goto(baseUrl);await longPage.getByLabel('Archivo PDF').setInputFiles(longForm);await longPage.getByAltText('Página 1 del documento').waitFor();
 await openTool(longPage,"Datos de formulario");
 const dataDownload=longPage.waitForEvent('download');await longPage.getByRole('button',{name:'Descargar datos JSON',exact:true}).click();
 const dataPath=join(tmpdir(),'reapdf-form-data.json');await(await dataDownload).saveAs(dataPath);
 execFileSync(python,['-c',`import json,sys
p=sys.argv[1];d=json.load(open(p));d['fields'][0]['value']='Importado';open(p,'w').write(json.dumps(d))`,dataPath]);
 await longPage.getByLabel('Datos JSON de formulario').setInputFiles(dataPath);await longPage.getByRole('button',{name:'Importar y aplicar datos',exact:true}).click();
 await expect(longPage.locator('.text-layer')).toContainText('Importado');
 await openTool(longPage,"Aplanar formulario");await longPage.getByLabel('Confirmar aplanado de campos').check();await longPage.getByRole('button',{name:'Aplanar campos',exact:true}).click();
 await openTool(longPage,"Rellenar formulario");await expect(longPage.getByRole('dialog')).toContainText('no contiene campos');await longPage.getByRole('button',{name:'Cancelar',exact:true}).click();
 await longPage.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(longPage.locator('.text-layer')).toContainText('Importado');
 await openTool(longPage,"Marca de agua");await longPage.getByLabel('Texto de marca de agua').fill('BORRADOR');await longPage.getByLabel('Ángulo de marca de agua').selectOption({value:'0'});await longPage.getByRole('button',{name:'Vista previa de marca de agua',exact:true}).click();await expect(longPage.getByRole('button',{name:'Aplicar marca de agua',exact:true})).toBeEnabled();await longPage.getByRole('button',{name:'Aplicar marca de agua',exact:true}).click();
 await expect(longPage.locator('.text-layer')).toContainText('BORRADOR');
 await openTool(longPage,"Propiedades del PDF");await longPage.getByLabel('Propiedad Título',{exact:true}).fill('Informe de prueba');await longPage.getByRole('button',{name:'Aplicar propiedades',exact:true}).click();
 await openTool(longPage,"Optimizar PDF");await longPage.getByRole('button',{name:'Optimizar versión',exact:true}).click();await expect(longPage.locator('.banner')).toContainText('Optimización');
 await openTool(longPage,"Crear o eliminar campos");await longPage.getByLabel('Nombre de campo nuevo').fill('Nuevo');await longPage.getByLabel('Y de campo nuevo',{exact:true}).fill('730');await longPage.getByLabel('Ancho de campo nuevo',{exact:true}).fill('200');await longPage.getByRole('button',{name:'Crear campo en PDF',exact:true}).click();
 await openTool(longPage,"Rellenar formulario");await longPage.getByLabel('Campo del formulario').selectOption({label:'Nuevo · Página 1'});await longPage.getByLabel('Valor del formulario').fill('Campo creado');await longPage.getByRole('button',{name:'Vista previa del formulario',exact:true}).click();await expect(longPage.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeEnabled();await longPage.getByRole('button',{name:'Aplicar formulario',exact:true}).click();
 await openTool(longPage,"Exportar texto");const textDownload=longPage.waitForEvent('download');await longPage.getByRole('button',{name:'Descargar texto TXT',exact:true}).click();const textPath=join(tmpdir(),'reapdf-exported-text.txt');await(await textDownload).saveAs(textPath);execFileSync(python,['-c',`import sys; t=open(sys.argv[1]).read();assert 'Importado' in t and 'Campo creado' in t and 'BORRADOR' in t`,textPath]);
 await openTool(longPage,"Proteger copia");await longPage.getByLabel('Contraseña de apertura',{exact:true}).fill('lectura123');await longPage.getByLabel('Repetir contraseña de apertura',{exact:true}).fill('lectura123');await longPage.getByLabel('Contraseña de propietario',{exact:true}).fill('propietario123');
 const protectedDownload=longPage.waitForEvent('download');await longPage.getByRole('button',{name:'Descargar copia protegida',exact:true}).click();const protectedPath=join(tmpdir(),'reapdf-protected.pdf');await(await protectedDownload).saveAs(protectedPath);execFileSync(python,['-c',`import pymupdf as f,sys;d=f.open(sys.argv[1]);assert d.needs_pass and d.authenticate('lectura123');assert d.metadata['title']=='Informe de prueba';assert 'Importado' in d[0].get_text()`,protectedPath]);
 await openTool(longPage,"Comparar documentos");await longPage.getByLabel('PDF para comparar').setInputFiles(longForm);await expect(longPage.getByRole('dialog').getByRole('status')).toContainText('páginas con diferencias');await expect(longPage.getByAltText('Actual, página 1')).toBeVisible();await longPage.screenshot({path:join(tmpdir(),'reapdf-comparison.png')});await longPage.getByRole('button',{name:'Cerrar',exact:true}).click();
 await longPage.getByLabel('Archivo PDF').setInputFiles(protectedPath);await longPage.getByLabel('Contraseña para abrir PDF').fill('lectura123');await longPage.getByRole('button',{name:'Abrir copia descifrada',exact:true}).click();await expect(longPage.locator('.text-layer')).toContainText('Campo creado');await longContext.close();
 // OCR real sobre escaneado: búsqueda, selección, exportación y preservación de píxeles.
 const scanPath=join(tmpdir(),'reapdf-scan.pdf');execFileSync(python,['-c',`import pymupdf as f,sys
d=f.open();p=d.new_page(width=500,height=650);p.insert_text((45,170),'REAPDF OCR 12345',fontsize=24);pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False);s=f.open();p=s.new_page(width=500,height=650);p.insert_image(p.rect,stream=pix.tobytes('png'));s.save(sys.argv[1])`,scanPath]);
 const ocrContext=await browser.newContext({viewport:{width:1440,height:1080}}),ocrPage=await ocrContext.newPage();failurePage=ocrPage;ocrPage.setDefaultTimeout(30000);ocrPage.on('pageerror',e=>errors.push(e.message));ocrPage.on('dialog',d=>d.accept());
 await ocrPage.goto(baseUrl);await ocrPage.getByLabel('Archivo PDF').setInputFiles(scanPath);await ocrPage.getByAltText('Página 1 del documento').waitFor();
 await openTool(ocrPage,"Reconocer texto (OCR)");await ocrPage.getByRole('button',{name:'Reconocer páginas',exact:true}).click();await expect(ocrPage.locator('.text-layer')).toContainText('12345');
 await ocrPage.getByRole('tab',{name:'Buscar',exact:true}).click();await ocrPage.getByRole('searchbox',{name:'Buscar en el documento'}).fill('12345');await ocrPage.getByRole('button',{name:'Buscar texto',exact:true}).click();await expect(ocrPage.getByText('1 de 1',{exact:true})).toBeVisible();
 const ocrDownload=ocrPage.waitForEvent('download');await ocrPage.getByRole('button',{name:'Exportar copia',exact:true}).click();const ocrOutput=join(tmpdir(),'reapdf-ocr-result.pdf');await(await ocrDownload).saveAs(ocrOutput);execFileSync(python,['-c',`import pymupdf as f,sys;a=f.open(sys.argv[1]);b=f.open(sys.argv[2]);assert '12345' in b[0].get_text();assert a[0].get_pixmap().samples==b[0].get_pixmap().samples`,scanPath,ocrOutput]);
 await ocrPage.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(ocrPage.locator('.text-layer')).not.toContainText('12345');await ocrPage.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(ocrPage.locator('.text-layer')).toContainText('12345');await expect(ocrPage.locator('.session-bar')).toContainText('Recuperación local actualizada');await ocrPage.reload();await ocrPage.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await expect(ocrPage.locator('.text-layer')).toContainText('12345');await ocrPage.screenshot({path:join(tmpdir(),'reapdf-ocr.png')});await ocrContext.close();
 // Imágenes existentes: mover con píxeles originales, vista previa y deshacer.
 const existingImagePath=join(tmpdir(),'reapdf-existing-image.pdf');execFileSync(python,['-c',`import pymupdf as f,sys
pix=f.Pixmap(f.csRGB,f.IRect(0,0,120,80),False);pix.clear_with(140);d=f.open();p=d.new_page();p.insert_text((30,50),'Conservar texto');p.insert_image(f.Rect(40,100,280,260),stream=pix.tobytes('jpeg'));d.save(sys.argv[1])`,existingImagePath]);
 const editImageContext=await browser.newContext({viewport:{width:1440,height:1080}}),editImagePage=await editImageContext.newPage();failurePage=editImagePage;editImagePage.setDefaultTimeout(20000);editImagePage.on('pageerror',e=>errors.push(e.message));editImagePage.on('dialog',d=>d.accept());
 await editImagePage.goto(baseUrl);await editImagePage.getByLabel('Archivo PDF').setInputFiles(existingImagePath);await editImagePage.getByAltText('Página 1 del documento').waitFor();
 await openTool(editImagePage,"Editar imágenes del PDF");await expect(editImagePage.getByLabel('Imagen existente',{exact:true})).toHaveValue('0');
 await editImagePage.getByLabel('X de imagen existente',{exact:true}).fill('100');await editImagePage.getByLabel('Y de imagen existente',{exact:true}).fill('300');await editImagePage.getByLabel('Ancho de imagen existente',{exact:true}).fill('180');await editImagePage.getByLabel('Alto de imagen existente',{exact:true}).fill('120');
 await editImagePage.getByRole('button',{name:'Vista previa de imagen editada',exact:true}).click();await expect(editImagePage.getByRole('button',{name:'Aplicar imagen editada',exact:true})).toBeEnabled();await editImagePage.getByRole('button',{name:'Aplicar imagen editada',exact:true}).click();
 const importedImageOutputDownload=editImagePage.waitForEvent('download');await editImagePage.getByRole('button',{name:'Exportar copia',exact:true}).click();const importedImageOutput=join(tmpdir(),'reapdf-existing-image-edited.pdf');await(await importedImageOutputDownload).saveAs(importedImageOutput);
 execFileSync(python,['-c',`import pymupdf as f,sys
a=f.open(sys.argv[1]);b=f.open(sys.argv[2]);p=b[0];i=next(i for i in p.get_images() if i[2:4]==(120,80));assert b.extract_image(i[0])['image']==a.extract_image(a[0].get_images()[0][0])['image'];r=p.get_image_rects(i[0])[0];assert list(r)==[100,300,280,420];assert 'Conservar texto' in p.get_text()`,existingImagePath,importedImageOutput]);
 await editImagePage.getByRole('button',{name:'Deshacer',exact:false}).click();await editImagePage.getByRole('button',{name:'Rehacer',exact:false}).click();
 await openTool(editImagePage,"Editar imágenes del PDF");await editImagePage.getByLabel('Acción de imagen existente').selectOption({value:'delete'});await editImagePage.getByRole('button',{name:'Vista previa de imagen editada',exact:true}).click();await expect(editImagePage.getByRole('button',{name:'Aplicar imagen editada',exact:true})).toBeEnabled();await editImagePage.getByRole('button',{name:'Aplicar imagen editada',exact:true}).click();
 await openTool(editImagePage,"Editar imágenes del PDF");await expect(editImagePage.getByRole('dialog')).toContainText('No hay imágenes existentes disponibles');await editImagePage.getByRole('button',{name:'Cancelar',exact:true}).click();await editImageContext.close();
 const paragraphContext=await browser.newContext({viewport:{width:1440,height:1080}}),paragraphPage=await paragraphContext.newPage();failurePage=paragraphPage;paragraphPage.setDefaultTimeout(20000);paragraphPage.on('pageerror',e=>errors.push(e.message));paragraphPage.on('dialog',d=>d.accept());
 await paragraphPage.goto(baseUrl);await paragraphPage.getByLabel('Archivo PDF').setInputFiles(sample);await paragraphPage.getByAltText('Página 1 del documento').waitFor();await openTool(paragraphPage,"Reemplazar bloque de texto");
 await paragraphPage.getByLabel('X de bloque de texto',{exact:true}).fill('44');await paragraphPage.getByLabel('Y de bloque de texto',{exact:true}).fill('220');await paragraphPage.getByLabel('Ancho de bloque de texto',{exact:true}).fill('507');await paragraphPage.getByLabel('Alto de bloque de texto',{exact:true}).fill('75');await paragraphPage.getByRole('button',{name:'Leer bloque seleccionado',exact:true}).click();await expect(paragraphPage.getByLabel('Texto del bloque')).toContainText('Texto original');
 await paragraphPage.getByLabel('Texto del bloque').fill('Párrafo corregido con fuente incrustada.\nSegunda línea: αβγ.');await paragraphPage.getByLabel('Tamaño de bloque de texto').fill('14');await paragraphPage.getByRole('button',{name:'Vista previa del bloque',exact:true}).click();await expect(paragraphPage.getByRole('button',{name:'Aplicar párrafo',exact:true})).toBeEnabled();await paragraphPage.getByRole('button',{name:'Aplicar párrafo',exact:true}).click();await expect(paragraphPage.locator('.text-layer')).toContainText('Párrafo corregido');await expect(paragraphPage.locator('.text-layer')).not.toContainText('Texto original');
 const paragraphDownload=paragraphPage.waitForEvent('download');await paragraphPage.getByRole('button',{name:'Exportar copia',exact:true}).click();const paragraphOutput=join(tmpdir(),'reapdf-paragraph-edit.pdf');await(await paragraphDownload).saveAs(paragraphOutput);execFileSync(python,['-c',`import pymupdf as f,sys;d=f.open(sys.argv[1]);t=d[0].get_text();assert 'Párrafo corregido' in t and 'αβγ' in t and 'Texto original' not in t;assert 'Un espacio para tus anotaciones' in t;assert any('DejaVu' in row[3] for row in d[0].get_fonts())`,paragraphOutput]);
 await paragraphPage.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(paragraphPage.locator('.text-layer')).toContainText('Texto original');await paragraphPage.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(paragraphPage.locator('.text-layer')).toContainText('Párrafo corregido');await paragraphPage.screenshot({path:join(tmpdir(),'reapdf-paragraph.png')});await paragraphContext.close();
 await runWorkspaceSmoke(browser,baseUrl,python,errors,next=>failurePage=next);
 await runProSmoke(browser,baseUrl,python,errors,next=>failurePage=next);
 await runWordSectionsSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runWordAdvancedSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runMixedFlowSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runRunningFieldsSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runStylesOrganizationSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runWordRulesSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runFlowCalculationsSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runAutomationSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runCompressionSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runMultipleEndpointsSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runImportedHandlesSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runProfessionalSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runPrecisionRedactionSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runStandardsAccessibilitySmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runDigitalSignaturesSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runWordFormsSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runReviewDesignSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runEditingExpansionSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runRotatedTextSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runParagraphLayoutSmoke(browser,baseUrl,python,errors,p=>{failurePage=p;});
 await runFormImportSmoke(browser,baseUrl,python,errors,next=>failurePage=next);
 await runAdvancedFormsSmoke(browser,baseUrl,python,errors,next=>failurePage=next);
 await runStyledTextSmoke(browser,baseUrl,python,errors,next=>failurePage=next);
 assert.deepEqual(errors,[]);
 console.log('PASS: secciones Word con orientación y márgenes propios, herencia de encabezados, reinicios, etiquetas, enlaces, proyecto y recuperación; campos Word complejos, numeración romana desde 5, etiquetas PDF, tablas con combinaciones horizontales/verticales, informes/hash y recuperación; flujo mixto con estilos, tamaños y colores importados, edición/separación de fragmentos, revisión multipágina, comprobación del PDF y proyecto/historial/recuperación; encabezados/pies y PAGE/NUMPAGES Word con revisión multipágina; cálculos conservados entre inserción, renombrado, reemplazo y duplicación con copias independientes, proyecto y recuperación; estilos heredados y listas DOCX, reglas activas tras ordenar/girar/eliminar páginas con bloqueo de dependencias y recuperación; importación DOCX con revisión multipágina e informe/hash, Word en recetas y cálculos dependientes en proyectos/recuperación; reflujo entre regiones y páginas con revisión completa, historial/recuperación; cálculos decimales de campos sin scripts; enlaces web conservados en Word; recetas configurables con pasos ordenados, guardado/importación/exportación sin credenciales, copias cifradas y TXT, manifiestos con hashes y revisión vigente; compresión de imágenes con DPI/calidad, comparación, copia e informe con hash exacto; extremos independientes de líneas, selección múltiple, alineación/distribución, movimiento y color colectivos, borrado atómico, historial/proyectos/recuperación; tiradores nativos para mover y redimensionar trazos/flechas importados, cuatro giros y recortes, cancelación, teclado, historial y proyecto/recuperación; interfaz profesional, secciones plegables y ayuda persistente, ventanas y adaptación a 600/900/1100/1440 px, movimiento de trazos y flechas importados con historial y exportación; selección por caracteres con vista de arrastre, censura selectiva por búsqueda y manual multipágina con revisión de todas las páginas y extracción independiente; PDF/A y PDF/UA con veraPDF, copia PDF/A-2b validada, comparación visual, título/idioma y diagnóstico de accesibilidad; certificados P12/PFX, firmas SHA-256 sucesivas, confianza explícita, alteraciones, informes y recuperación; Word con imágenes/tablas y revisión de pérdidas; nombres y opciones de campos, valores e historial; comentarios nativos, estados e informes; enlaces existentes, formato/valores iniciales de formularios, tamaño de rectángulos/elipses, lotes TXT/optimización/AES-256 sin modificar la sesión; edición de bloques a 90/180/270° con recortes, formato sugerido, comparación original/resultado y fuentes conservadas; catálogo y comandos, favoritos persistentes, navegación directa, revisión paginada/JSON con reintento, atajos/foco, borradores y tamaños de pantalla; fuentes/estilos originales con TrueType parcial y rechazo de glifos ausentes, historial/proyecto/recuperación; jerarquías, campos compartidos y radios exclusivos, creación/eliminación de grupos, datos/proyectos/aplanado; Bates entre varios archivos, adjuntos Unicode, etiquetas y navegación, tablas CSV protegidas, censura con saneamiento, firmas visuales, movimiento de notas importadas y OCR con giro manual; bloques de texto con fuente incrustada y Unicode, imágenes existentes reversibles; OCR real conservando píxeles, datos/aplanado/creación de campos, marcas de agua, metadatos, optimización, protección/apertura y comparación; formulario nativo editable con valores, vista previa, historial/proyectos/recuperación; creación desde PNG/JPEG y exportación PNG/JPEG con resolución/orden; marcadores editables con jerarquía, encabezados y numeración con vista previa, proyectos y recuperación; texto nuevo, sellos y enlaces editables; proyectos editables, recuperación tras reinicio, páginas nuevas e impresión; imágenes originales, posición/tamaño e historial; zoom nítido DPR 2, controles y borradores, marcado práctico y todos los flujos y exportaciones anteriores.');
} catch(error) {
 if(failurePage&&!failurePage.isClosed()) {console.error((await failurePage.locator('body').innerText()).slice(-3500)); await failurePage.screenshot({path:join(tmpdir(),'reapdf-ui-failure.png'),fullPage:true});}
 throw error;
} finally {if(browser) await browser.close(); if(server) server.kill();rmSync(recoveryDirectory,{recursive:true,force:true});}
