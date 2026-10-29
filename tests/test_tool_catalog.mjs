import {test} from 'node:test';
import assert from 'node:assert/strict';
import {areas,tools,groups,searchTools,unavailableReason,parsePageNumber} from '../web/src/tool-catalog.js';
const doc={pages:[{}],can_edit:true,can_annotate:true,can_copy:true,can_fill:true,can_extract:true,can_organize:true};
const tool=id=>tools.find(t=>t.id===id);
test('catalog has unique IDs, known groups and complete descriptions',()=>{assert.equal(new Set(tools.map(t=>t.id)).size,tools.length);for(const t of tools){assert.ok(groups.some(g=>g[0]===t.group));assert.ok(t.description.length>12);assert.equal(unavailableReason(t,doc),'');}});
for(const [query,id] of [['numeracion bates','bates'],['fuentes cursiva','paragraph'],['escaneo','ocr'],['firma','signature'],['excel','tables'],['diagnostico','review'],['hipervinculos existentes','existing_links'],['automatizacion masivo','batch'],['comentarios respuestas','comments'],['word editable','docx'],['formulario obligatorio','field_properties']])test(`task search: ${query}`,()=>assert.ok(searchTools(query).some(t=>t.id===id)));
test('empty queries return complete catalog and impossible queries no results',()=>{assert.equal(searchTools(' ').length,tools.length);assert.deepEqual(searchTools('zzzzzz'),[]);});
test('signed documents preserve reading and copy but block editing',()=>{for(const t of tools)assert.equal(!!unavailableReason(t,{...doc,signed:true}),!['read','copy','sign'].includes(t.permission));});
test('permissions combine copy and edit instead of allowing either',()=>{assert.match(unavailableReason(tool('ocr'),{...doc,can_copy:false}),/permisos/);assert.match(unavailableReason(tool('ocr'),{...doc,can_edit:false}),/permisos/);assert.equal(unavailableReason(tool('review'),{...doc,can_copy:false,can_edit:false}),'');});
test('pending drafts and gestures block document tools with an explanation',()=>{assert.match(unavailableReason(tool('review'),doc,{draft:'pending'}),/pendientes/);assert.match(unavailableReason(tool('view'),doc,{stroke:true}),/termine/);assert.match(unavailableReason(tool('review'),doc,{loading:true}),/prepare/);});
test('blank page limit and empty document are explicit',()=>{assert.match(unavailableReason(tool('blank'),{...doc,pages:Array(500).fill({})}),/500/);assert.match(unavailableReason(tool('view'),null),/Abre/);});
test('page parser rejects empty, fractional, exponential, out-of-range and unsafe values',()=>{for(const value of ['', ' ', '0','-1','2.5','1e1','+2','501','NaN','9007199254740993'])assert.equal(parsePageNumber(value,500),null);assert.equal(parsePageNumber(' 002 ',500),1);assert.equal(parsePageNumber('500',500),499);});

test('every tool has exactly one of the eight work areas',async()=>{const {areas,toolArea}=await import('../web/src/tool-catalog.js');assert.equal(areas.length,8);for(const t of tools){assert.ok(areas.some(a=>a.id===t.area));assert.equal(toolArea(t.id).id,t.area);}assert.equal(toolArea('unknown'),undefined);assert.ok(tools.filter(t=>t.area==='read').length<=6);assert.ok(tools.filter(t=>t.area==='read').length<tools.length/4);});
test('area changes explain why drafts and gestures must finish',async()=>{const {areaChangeReason}=await import('../web/src/tool-catalog.js');assert.equal(areaChangeReason({}),'');assert.match(areaChangeReason({draft:'pending'}),/cambios pendientes/);for(const key of ['busy','stroke','transforming'])assert.match(areaChangeReason({[key]:true}),/termine/);});

test('digital signing requires modify, copy and fill while verification stays readable',()=>{for(const permission of ['can_edit','can_copy','can_fill'])assert.match(unavailableReason(tool('digital_sign'),{...doc,[permission]:false}),/permisos/);assert.equal(unavailableReason(tool('verify_signatures'),{...doc,signed:true,can_edit:false,can_copy:false,can_fill:false}),'');assert.equal(unavailableReason(tool('digital_sign'),{...doc,signed:true}),'');});

test('standards and accessibility tools are searchable and stay available for signed inspection',()=>{for(const [query,id] of [['verapdf','standards'],['pdfa archivo','archive'],['idioma accesible','accessibility']])assert.ok(searchTools(query).some(t=>t.id===id));assert.equal(unavailableReason(tool('standards'),{...doc,signed:true}),'');assert.equal(unavailableReason(tool('accessibility'),{...doc,signed:true}),'');assert.match(unavailableReason(tool('archive'),{...doc,signed:true}),/firmado/);});

// A new catalog entry must never disappear because its visual section is missing.
import {sectionedTools,toolSections} from '../web/src/tool-sections.js';
test('las secciones de tareas distribuyen todas las herramientas exactamente una vez',()=>{
 const ids=[];
 for(const area of areas){
  const sections=sectionedTools(area.id,tools);assert.ok(sections.length>=2);
  for(const section of sections){assert.ok(section.label&&section.items.length);for(const item of section.items){assert.equal(item.area,area.id);ids.push(item.id);}}
 }
 assert.equal(new Set(ids).size,tools.length);assert.deepEqual([...ids].sort(),tools.map(t=>t.id).sort());
 assert.deepEqual(Object.keys(toolSections).sort(),areas.map(a=>a.id).sort());
});

test('flujo y cálculo se buscan por tarea y respetan sus permisos',()=>{
 for(const [query,id] of [['reflujo columnas','flow'],['calculadora promedio','calculate']])assert.ok(searchTools(query).some(t=>t.id===id));
 assert.match(unavailableReason(tool('flow'),{...doc,can_edit:false}),/permisos/);
 assert.match(unavailableReason(tool('calculate'),{...doc,can_fill:false}),/permisos/);
 assert.equal(unavailableReason(tool('calculate'),{...doc,can_edit:false}),'');
});

test('las reglas del proyecto se encuentran y requieren permiso de formulario',()=>{
 assert.ok(searchTools('reglas dependencias').some(t=>t.id==='form_rules'));
 assert.match(unavailableReason(tool('form_rules'),{...doc,can_fill:false}),/permisos/);
 assert.match(unavailableReason(tool('form_rules'),{...doc,signed:true}),/firmado/);
});
