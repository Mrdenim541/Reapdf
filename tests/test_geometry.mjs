import test from 'node:test';
import assert from 'node:assert/strict';
import {markBounds,transformMark} from '../web/src/geometry.js';
const page={width:500,height:600,rotation:0};
const fixtures=[
 ...['textbox','stamp','link'].map(type=>({type,points:[[20,30],[60,65]],text:'Conservar contenido',destination:'web',url:'https://example.com',stamp:'approved'})),
 {type:'image',points:[[20,30],[60,65]],data:'original-encoded-pixels',pixels:[800,700]},
 {type:'ink',points:[[20,30],[40,65],[60,50]],width:3,color:[1,0,0]},
 {type:'line',points:[[60,30],[20,65]],width:2},
 {type:'arrow',points:[[20,65],[60,30]],width:2},
 {type:'rectangle',points:[[60,65],[20,30]],width:2},
 ...['highlight','underline','strikeout'].map(type=>({type,quads:[[[20,30],[60,30],[20,40],[60,40]],[[20,50],[45,50],[20,65],[45,65]]],color:[1,1,0]})),
];
for(const fixture of fixtures) {
 test(`mover y escalar ${fixture.type} conserva datos y coordenadas relativas`,()=>{
  const op={...fixture,id:'keep',page:0},pristine=structuredClone(op);
  const target={x:100,y:200,width:80,height:70};
  const result=transformMark(op,target,page);
  assert.deepEqual(markBounds(result),target);
  assert.equal(result.id,op.id);assert.equal(result.data,op.data);assert.deepEqual(result.pixels,op.pixels);assert.equal(result.width,op.width);
  assert.deepEqual(op,pristine);assert.deepEqual(result.color,op.color);
  const before=op.quads?.flat()||op.points,after=result.quads?.flat()||result.points;
  before.forEach(([x,y],i)=>assert.deepEqual(after[i],[100+(x-20)*2,200+(y-30)*2]));
 });
}
for(const rotation of [0,90,180,270]) {
 test(`mover nota en página girada ${rotation} conserva icono y contenido`,()=>{
  const op={type:'note',point:[150,150],content:'Nota ✓',color:[1,1,0]};
  const before=markBounds(op,rotation),target={...before,x:before.x+20,y:before.y+30};
  const result=transformMark(op,target,{...page,rotation});
  assert.deepEqual(markBounds(result,rotation),target);
  assert.deepEqual(result.point,[170,180]);assert.equal(result.content,op.content);
  assert.throws(()=>transformMark(op,{...target,width:30},{...page,rotation}),/tamaño fijo/);
 });
}
for(const [points,target] of [
 [[[30,20],[30,60]],{x:80,y:90,width:0,height:80}],
 [[[20,30],[60,30]],{x:80,y:90,width:80,height:0}],
])test('línea de dimensión cero se mueve y cambia longitud sin NaN',()=>{
 const result=transformMark({type:'line',points},target,page);
 assert.deepEqual(markBounds(result),target);
 assert.ok(result.points.flat().every(Number.isFinite));
});
for(const invalid of [{x:-1},{y:-1},{width:0},{height:.1},{width:600},{height:600},{x:NaN},{y:Infinity}]) {
 test(`rechaza geometría inválida ${JSON.stringify(invalid)}`,()=>{
  assert.throws(()=>transformMark(fixtures[0],{x:20,y:30,width:40,height:35,...invalid},page));
 });
}
test('las marcas giradas conservan el orden orientado de los vértices',()=>{
 const op={type:'highlight',quads:[[[60,20],[60,60],[50,20],[50,60]]]};
 assert.deepEqual(transformMark(op,{x:100,y:120,width:20,height:80},page).quads,
  [[[120,120],[120,200],[100,120],[100,200]]]);
});
test('un trazo muy estrecho puede moverse conservando su tamaño original',()=>{
 const op={type:'ink',points:[[20,30],[20.25,80]]};
 const result=transformMark(op,{x:100,y:100,width:.25,height:50},page);
 assert.deepEqual(result.points,[[100,100],[100.25,150]]);
});

const {selectMarkupWords}=await import('../web/src/geometry.js');
const words=[{text:'Uno',quad:[[10,10],[30,10],[10,25],[30,25]]},{text:'Dos',quad:[[35,10],[55,10],[35,25],[55,25]]},{text:'Tres',quad:[[10,40],[30,40],[10,55],[30,55]]}];
test('resaltar con clic selecciona la palabra completa',()=>assert.deepEqual(selectMarkupWords(words,[20,20],[20,20]).map(w=>w.text),['Uno']));
test('arrastre horizontal junto a la línea base selecciona palabras',()=>assert.deepEqual(selectMarkupWords(words,[15,24],[50,24]).map(w=>w.text),['Uno','Dos']));
test('arrastre inverso multilínea conserva todas las regiones',()=>assert.equal(selectMarkupWords(words,[60,60],[5,5]).length,3));
test('clic fuera del texto no marca una región vacía',()=>assert.equal(selectMarkupWords(words,[100,100],[100,100]).length,0));

// Selection tests cover reversed drags and all visible page rotations.
import {selectMarkupCharacters} from '../web/src/geometry.js';
for(const rotation of [0,90,180,270]){
 test(`selección precisa y compactación por caracteres a ${rotation} grados`,()=>{
  const rotate=([x,y])=>({0:[x,y],90:[100-y,x],180:[100-x,100-y],270:[y,100-x]})[rotation];
  const chars='Texto'.split('').map((text,index)=>({text,group:'line:0',index,quad:[[index*10,20],[index*10+10,20],[index*10,30],[index*10+10,30]].map(rotate)}));
  const before=structuredClone(chars),a=rotate([11,25]),b=rotate([39,25]);
  for(const [start,end] of [[a,b],[b,a]]){
   const selected=selectMarkupCharacters(chars,start,end);assert.equal(selected.length,1);assert.equal(selected[0].text,'ext');
   assert.deepEqual(selected[0].quad,[chars[1].quad[0],chars[3].quad[1],chars[1].quad[2],chars[3].quad[3]]);
  }
  assert.equal(selectMarkupCharacters(chars,rotate([24,25]),rotate([24,25]))[0].text,'x');
  assert.deepEqual(chars,before);
 });
}
test('selección precisa no une espacios, estilos ni líneas; clic fuera queda vacío',()=>{
 const q=x=>[[x,20],[x+10,20],[x,30],[x+10,30]];
 const chars=[{text:'a',quad:q(0),group:'1:0',index:0},{text:'b',quad:q(20),group:'1:0',index:2},{text:'c',quad:q(30),group:'1:1',index:0}];
 assert.equal(selectMarkupCharacters(chars,[0,10],[40,35]).length,3);
 assert.deepEqual(selectMarkupCharacters(chars,[70,70],[70,70]),[]);
 assert.equal(selectMarkupCharacters(chars,[10,25],[10,25]).length,1);
});

import {existingGeometry,importedPathOperation} from '../web/src/existing-geometry.js';
test('trazos importados: cambios absolutos y proyectos antiguos no acumulan escala',()=>{
 const item={rect:[8,18,42,52],path_rect:[10,20,40,50],paths:[[[10,20],[25,45],[40,50]],[[15,30],[35,40]]],color:[1,0,0]};
 const before=structuredClone(item);
 const next=existingGeometry(item,{path_rect:[20,30,80,90],color:[0,1,0]});
 assert.deepEqual(next.paths[0],[[20,30],[50,80],[80,90]]);
 assert.deepEqual(markBounds(importedPathOperation(next)),{x:20,y:30,width:60,height:60});
 assert.deepEqual(existingGeometry(item,{rect:[18,28,52,62]}).path_rect,[20,30,50,60]);
 assert.deepEqual(existingGeometry(item,{path_rect:[20,30,80,90],color:[0,0,1]}).paths,next.paths);
 assert.deepEqual(item,before);
});
test('trazos importados: escala nativa y dimensión cero conservan segmentos y dirección',()=>{
 const op={type:'imported_path',paths:[[[20,30],[20,80]],[[20,40],[20,50]]]};
 const next=transformMark(op,{x:70,y:90,width:0,height:100},page);
 assert.deepEqual(next.paths,[[[70,90],[70,190]],[[70,110],[70,130]]]);
 assert.throws(()=>transformMark(op,{x:70,y:90,width:5,height:100},page));
 const row=existingGeometry({path_rect:[20,30,20,80],rect:[18,28,22,82],paths:op.paths},{path_rect:[70,90,70,190]});
 assert.deepEqual(row.paths,next.paths);
});
test('trazos importados: si faltan puntos, la guía usa los límites disponibles',()=>{
 const row={path_rect:[10,20,60,70],paths:null};
 assert.deepEqual(markBounds(importedPathOperation(row)),{x:10,y:20,width:50,height:50});
});

import {mergeAnnotationChanges,lineInBox} from '../web/src/existing-geometry.js';
import {alignSelection,distributeSelection,translateSelection,selectionBounds,groupOperation} from '../web/src/multi-geometry.js';
const native=(xref,rect)=>({xref,rect,visible:true,editable:true,can_move:true});
test('extremos editados conservan orientación al mover o cambiar la caja después',()=>{
 const original={...native(1,[8,18,82,92]),path_rect:[10,20,80,90],paths:[[[10,20],[80,90]]],line_points:[[10,20],[80,90]]};
 const current=existingGeometry(original,{line_points:[[100,200],[40,220]]});assert.deepEqual(current.path_rect,[40,200,100,220]);
 const next=mergeAnnotationChanges({line_points:current.line_points,color:[1,0,0]},{path_rect:[50,180,170,220]},current);
 assert.deepEqual(next.line_points,[[170,180],[50,220]]);assert.equal(next.path_rect,undefined);assert.deepEqual(next.color,[1,0,0]);
 assert.deepEqual(existingGeometry(original,next).paths,[next.line_points]);
 assert.equal(mergeAnnotationChanges({rect:[0,0,1,1]},{line_points:[[20,30],[50,60]]}).rect,undefined);
 assert.deepEqual(lineInBox([[10,20],[10,50]],[10,20,10,50],[30,40,30,100]),[[30,40],[30,100]]);
});
test('alineación usa límites de selección o primera marca, sin alterar tamaño',()=>{
 const items=[native(1,[10,20,30,40]),native(2,[60,70,100,100]),native(3,[150,140,180,180])],saved=structuredClone(items);
 for(const kind of ['left','center','right','top','middle','bottom']){
  const patches=alignSelection(items,kind),updated=items.map(a=>({...a,...patches.find(p=>p.xref===a.xref).changes}));
  for(let i=0;i<items.length;i++){assert.equal(updated[i].rect[2]-updated[i].rect[0],items[i].rect[2]-items[i].rect[0]);assert.equal(updated[i].rect[3]-updated[i].rect[1],items[i].rect[3]-items[i].rect[1]);}
  const axis=['left','center','right'].includes(kind)?0:1;
  const values=updated.map(a=>['left','top'].includes(kind)?a.rect[axis]:['right','bottom'].includes(kind)?a.rect[axis+2]:(a.rect[axis]+a.rect[axis+2])/2);
  assert.ok(values.every(v=>v===values[0]));
 }
 assert.deepEqual(alignSelection(items,'right','first')[0].changes.rect,items[0].rect);assert.deepEqual(items,saved);
});
test('grupo conserva extremos, traslación y tipo de operación de cada geometría',()=>{
 const line={...native(1,[8,18,82,92]),path_rect:[10,20,80,90],line_points:[[80,20],[10,90]],paths:[[[80,20],[10,90]]]},ink={...native(2,[18,28,52,82]),path_rect:[20,30,50,80],paths:[[[20,30],[50,80]]]};
 const items=[line,ink,native(3,[100,110,130,150])],patches=translateSelection(items,10,-5);
 assert.deepEqual(patches[0].changes.line_points,[[90,15],[20,85]]);assert.deepEqual(patches[1].changes.path_rect,[30,25,60,75]);assert.deepEqual(patches[2].changes.rect,[110,105,140,145]);
 assert.deepEqual(selectionBounds(items),[10,20,130,150]);assert.deepEqual(markBounds(groupOperation(items)),{x:10,y:20,width:120,height:130});
});
test('distribución iguala huecos, conserva bordes extremos y rechaza solapamiento sin espacio',()=>{
 const items=[native(1,[10,20,30,40]),native(2,[35,20,65,40]),native(3,[100,20,140,40])];
 const patches=distributeSelection(items,0);assert.deepEqual(patches.map(p=>p.changes.rect),[[10,20,30,40],[50,20,80,40],[100,20,140,40]]);
 assert.throws(()=>distributeSelection(items.slice(0,2),0));assert.throws(()=>distributeSelection([native(1,[0,0,50,50]),native(2,[5,5,55,55]),native(3,[10,10,60,60])],0));
 assert.throws(()=>alignSelection([items[0],{...items[1],can_move:false}],'left'));
 assert.throws(()=>translateSelection([items[0],items[0]],10,10));assert.throws(()=>translateSelection(items,NaN,0));
});
