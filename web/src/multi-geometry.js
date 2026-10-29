const box=a=>a.path_rect||a.rect;
export function selectionBounds(items){if(!items.length)throw new Error('Selecciona al menos una marca.');return [Math.min(...items.map(a=>box(a)[0])),Math.min(...items.map(a=>box(a)[1])),Math.max(...items.map(a=>box(a)[2])),Math.max(...items.map(a=>box(a)[3]))];}
export function translateAnnotation(a,dx,dy){
 if(!a.can_move||!a.visible||!a.editable)throw new Error('La selección incluye una marca que no se puede mover.');
 if(!Number.isFinite(dx)||!Number.isFinite(dy))throw new Error('Indica desplazamientos válidos.');
 const changes=a.line_points?{line_points:a.line_points.map(p=>[p[0]+dx,p[1]+dy])}:a.path_rect?{path_rect:a.path_rect.map((v,i)=>v+(i%2?dy:dx))}:{rect:a.rect.map((v,i)=>v+(i%2?dy:dx))};
 return {xref:a.xref,changes};
}
function validate(items,min=2){if(items.length<min||items.length>50||new Set(items.map(a=>a.xref)).size!==items.length)throw new Error(`Selecciona entre ${min} y 50 marcas distintas.`);}
export function translateSelection(items,dx,dy){validate(items,1);return items.map(a=>translateAnnotation(a,dx,dy));}
export function alignSelection(items,kind,reference='selection'){
 validate(items);if(!['left','center','right','top','middle','bottom'].includes(kind)||!['selection','first'].includes(reference))throw new Error('Alineación no válida.');
 const ref=reference==='first'?box(items[0]):selectionBounds(items),axis=['left','center','right'].includes(kind)?0:1;
 return items.map(a=>{const b=box(a),size=b[axis+2]-b[axis],to=['left','top'].includes(kind)?ref[axis]:['right','bottom'].includes(kind)?ref[axis+2]-size:(ref[axis]+ref[axis+2]-size)/2;return translateAnnotation(a,axis===0?to-b[axis]:0,axis===1?to-b[axis]:0);});
}
export function distributeSelection(items,axis){
 validate(items,3);if(axis!==0&&axis!==1)throw new Error('Distribución no válida.');
 const sorted=items.map((a,i)=>({a,i})).sort((a,b)=>box(a.a)[axis]-box(b.a)[axis]||a.i-b.i).map(v=>v.a),bounds=selectionBounds(items);
 const total=sorted.reduce((n,a)=>n+box(a)[axis+2]-box(a)[axis],0),gap=(bounds[axis+2]-bounds[axis]-total)/(items.length-1);
 if(gap<-.001)throw new Error('No hay espacio para separar las marcas dentro de la selección. Amplía su separación primero.');
 let pos=bounds[axis];return sorted.map(a=>{const b=box(a),delta=pos-b[axis];pos+=b[axis+2]-b[axis]+Math.max(0,gap);return translateAnnotation(a,axis===0?delta:0,axis===1?delta:0);});
}
export function groupOperation(items){const paths=items.flatMap(a=>a.paths||[[[box(a)[0],box(a)[1]],[box(a)[2],box(a)[1]],[box(a)[2],box(a)[3]],[box(a)[0],box(a)[3]],[box(a)[0],box(a)[1]]]]);return {type:'imported_group',paths};}
