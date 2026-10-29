import {openTool} from './smoke-tool-navigation.mjs';
import {expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
export async function runStylesOrganizationSmoke(browser,baseUrl,python,errors,onPage){
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),p=await context.newPage();onPage(p);p.setDefaultTimeout(25000);p.on('pageerror',e=>errors.push(e.message));p.on('dialog',d=>d.accept());
 const word=join(tmpdir(),'reapdf-styled-numbered.docx'),project=join(tmpdir(),'reapdf-organizable-rules.reapdf');
 execFileSync(python,['-c',`from pathlib import Path;import sys
from tests.test_docx_styles import fixture
from tests.test_form_rule_organization import multipage
from tests.test_form_rules import configuration
from backend.projects import build_project
Path(sys.argv[1]).write_bytes(fixture())
base=multipage();_,rules=configuration(base)
Path(sys.argv[2]).write_bytes(build_project(base,[rules],{'name':'Calculos.pdf','page':0,'zoom':1})[0])`,word,project]);
 await p.goto(baseUrl);await p.getByRole('button',{name:'Crear PDF desde Word',exact:true}).click();await p.getByLabel('Archivo Word para convertir',{exact:true}).setInputFiles(word);await p.getByRole('button',{name:'Convertir y revisar Word',exact:true}).click();await expect(p.getByRole('dialog')).toContainText('4 estilos · 5 elementos de lista');await expect(p.getByLabel('Revisé Word página 1',{exact:true})).toBeEnabled();await p.getByLabel('Revisé Word página 1',{exact:true}).check();await p.getByLabel('Aceptar diferencias de importación Word',{exact:true}).check();await p.getByRole('dialog').evaluate(el=>{el.scrollTop=0;});await p.screenshot({path:join(tmpdir(),'reapdf-word-estilos-038.png')});await p.getByRole('button',{name:'Abrir PDF convertido',exact:true}).click();await expect(p.locator('.text-layer')).toContainText('Titulo heredado');await expect(p.locator('.text-layer')).toContainText('Reiniciado');
 await p.getByLabel('Archivo de proyecto',{exact:true}).setInputFiles(project);await expect(p.locator('.banner').filter({hasText:'Cálculos automáticos activos'})).toBeVisible();await openTool(p,'Organizar páginas');await expect(p.getByRole('dialog')).toContainText('Cálculos protegidos');await p.getByLabel('Bajar página 1',{exact:true}).click();await p.getByRole('button',{name:'Girar selección 90°',exact:true}).click();await p.getByRole('button',{name:'Aplicar organización',exact:true}).click();await expect(p.getByRole('dialog')).toHaveCount(0);await expect(p.locator('.banner').filter({hasText:'siguen activos'})).toBeVisible();
 await openTool(p,'Rellenar formulario');await p.getByLabel('Valor del formulario',{exact:true}).fill('2');await p.getByRole('button',{name:'Vista previa del formulario',exact:true}).click();await expect(p.getByRole('button',{name:'Aplicar formulario',exact:true})).toBeEnabled();const selector=p.getByLabel('Campo del formulario',{exact:true});await selector.selectOption(await selector.locator('option').filter({hasText:/^Total /}).getAttribute('value'));await expect(p.getByRole('dialog')).toContainText('4,20');await p.getByRole('button',{name:'Aplicar formulario',exact:true}).click();
 // Deleting the referenced page must keep the organizer open and session intact.
 await openTool(p,'Organizar páginas');await p.getByLabel('Seleccionar todas las páginas',{exact:true}).check();await p.getByLabel('Seleccionar todas las páginas',{exact:true}).uncheck();await p.getByLabel('Seleccionar página 2',{exact:true}).check();await p.getByRole('button',{name:'Eliminar selección',exact:true}).click();await p.getByRole('button',{name:'Aplicar organización',exact:true}).click();await expect(p.getByRole('dialog').getByRole('alert')).toContainText('necesario para un cálculo automático');await p.getByRole('dialog').evaluate(el=>{el.scrollTop=0;});await p.screenshot({path:join(tmpdir(),'reapdf-reglas-protegidas-038.png')});await p.getByRole('button',{name:'Cancelar',exact:true}).click();
 // An unrelated page can be removed; the remaining references still recalculate.
 await openTool(p,'Organizar páginas');await p.getByLabel('Seleccionar todas las páginas',{exact:true}).check();await p.getByLabel('Seleccionar todas las páginas',{exact:true}).uncheck();await p.getByLabel('Seleccionar página 1',{exact:true}).check();await p.getByRole('button',{name:'Eliminar selección',exact:true}).click();await p.getByRole('button',{name:'Aplicar organización',exact:true}).click();await expect(p.getByRole('dialog')).toHaveCount(0);
 let wait=p.waitForEvent('download');await p.getByRole('button',{name:'Guardar proyecto',exact:true}).click();const saved=join(tmpdir(),'reapdf-remapped-rules.reapdf');await(await wait).saveAs(saved);execFileSync(python,['-c',`import sys;from pathlib import Path
from backend.projects import read_project
from backend.engine import export_pdf
from tests.test_form_rules import values
base,ops,_=read_project(Path(sys.argv[1]).read_bytes());assert len(ops)==1 and ops[0]['type']=='form_rules';assert values(export_pdf(base,ops))['Total']=='4,20'
assert all(ref['page']==0 for rule in ops[0]['rules'] for ref in rule['sources']+[rule['target']])`,saved]);
 await p.getByRole('button',{name:'Deshacer',exact:false}).click();await expect(p.getByLabel('Página siguiente',{exact:true})).toBeEnabled();await p.getByRole('button',{name:'Rehacer',exact:false}).click();await expect(p.locator('.session-bar')).toContainText('Recuperación local actualizada');await p.reload();await p.getByRole('button',{name:'Recuperar sesión',exact:true}).click();await openTool(p,'Cálculos automáticos del proyecto');await p.getByRole('button',{name:'Validar dependencias y calcular reglas',exact:true}).click();await expect(p.getByRole('dialog')).toContainText('4,20');await p.getByRole('button',{name:'Cancelar',exact:true}).click();
 await p.setViewportSize({width:600,height:900});await openTool(p,'Organizar páginas');assert.ok(await p.getByRole('dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1));await context.close();
}
