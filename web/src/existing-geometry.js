// Merge edits against the original vertices, including Rect moves in older
// projects. Never scale a patched path twice when changing its colour or size.
export function existingGeometry(item,changes={}) {
  const result={...item,...changes};
  if(!item.path_rect)return result;
  const from=item.path_rect;
  const target=changes.line_points?lineBounds(changes.line_points):changes.path_rect||from.map((v,i)=>v+(changes.rect?changes.rect[i%2]-item.rect[i%2]:0));
  const map=p=>p.map((v,i)=>target[i]+(from[i+2]===from[i]?0:(v-from[i])*(target[i+2]-target[i])/(from[i+2]-from[i])));
  const paths=changes.line_points?[changes.line_points]:item.paths?.map(path=>path.map(map));
  const line_points=changes.line_points||item.line_points?.map(map);
  return {...result,path_rect:target,paths,...(line_points?{line_points}:{}),
    rect:[target[0]+item.rect[0]-from[0],target[1]+item.rect[1]-from[1],target[2]+item.rect[2]-from[2],target[3]+item.rect[3]-from[3]]};
}

export function importedPathOperation(annotation) {
  const b=annotation.path_rect;
  return {type:'imported_path',paths:annotation.paths||[[[b[0],b[1]],[b[2],b[3]]]]};
}

export function lineBounds(points){return [Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))];}
export function lineInBox(points,from,target){return points.map(p=>p.map((v,i)=>target[i]+(from[i+2]===from[i]?0:(v-from[i])*(target[i+2]-target[i])/(from[i+2]-from[i]))));}
// Keep exactly one geometry representation per operation, including legacy moves.
export function mergeAnnotationChanges(previous={},changes={},current){
 const next={...previous,...changes};
 if(changes.line_points){delete next.rect;delete next.path_rect;}
 else if(changes.path_rect){
  delete next.rect;
  if(previous.line_points&&current?.line_points){next.line_points=lineInBox(current.line_points,current.path_rect,changes.path_rect);delete next.path_rect;}
 }
 return next;
}
