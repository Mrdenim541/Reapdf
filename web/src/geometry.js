// Geometría visible en puntos PDF; los datos originales nunca se mutan.
export function markBounds(op, rotation = 0) {
  let points;
  if (op.type === 'note') {
    const offsets = {0:[0,0],90:[-20,0],180:[-20,-20],270:[0,-20]}[rotation];
    const x=op.point[0]+offsets[0], y=op.point[1]+offsets[1];
    return {x,y,width:20,height:20};
  }
  points=op.quads ? op.quads.flat() : op.paths ? op.paths.flat() : op.points;
  const xs=points.map(p=>p[0]), ys=points.map(p=>p[1]);
  const x=Math.min(...xs), y=Math.min(...ys);
  return {x,y,width:Math.max(...xs)-x,height:Math.max(...ys)-y};
}

export function transformMark(op, target, page) {
  const old=markBounds(op,page.rotation);
  const {x,y,width,height}=target;
  if (![x,y,width,height].every(Number.isFinite) || x<0 || y<0 || width<0 || height<0 ||
      x+width>=page.width || y+height>=page.height) throw new Error('La marca debe permanecer dentro de la página.');
  if (op.type==='note' && (width!==20 || height!==20)) throw new Error('El icono de nota tiene tamaño fijo.');
  if ((old.width===0 && width!==0) || (old.height===0 && height!==0) ||
      (old.width>0 && width!==old.width && width<1) || (old.height>0 && height!==old.height && height<1)) throw new Error('Conserva al menos 1 punto en cada dimensión existente.');
  const map=([px,py])=>[x+(old.width ? (px-old.x)*width/old.width : 0),y+(old.height ? (py-old.y)*height/old.height : 0)];
  if(op.type==='note') return {...op,point:[op.point[0]+x-old.x,op.point[1]+y-old.y]};
  if(op.quads) return {...op,quads:op.quads.map(q=>q.map(map))};
  if(op.paths) return {...op,paths:op.paths.map(path=>path.map(map))};
  return {...op,points:op.points.map(map)};
}

export function selectMarkupWords(words,start,end) {
  const click=Math.hypot(end[0]-start[0],end[1]-start[1])<3;
  const left=Math.min(start[0],end[0])-(click?0:3),right=Math.max(start[0],end[0])+(click?0:3);
  const top=Math.min(start[1],end[1])-(click?0:3),bottom=Math.max(start[1],end[1])+(click?0:3);
  return words.filter(word=>{
    const xs=word.quad.map(p=>p[0]),ys=word.quad.map(p=>p[1]);
    return Math.max(...xs)>=left&&Math.min(...xs)<=right&&Math.max(...ys)>=top&&Math.min(...ys)<=bottom;
  });
}

// Character centres determine the selection. No three-point expansion: dragging
// over a fragment must not silently include its neighbouring letters.
export function selectMarkupCharacters(characters,start,end) {
  const click=Math.hypot(end[0]-start[0],end[1]-start[1])<3;
  const bounds=char=>{
    const xs=char.quad.map(p=>p[0]),ys=char.quad.map(p=>p[1]);
    return [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  };
  let picked;
  if(click){
    picked=characters.filter(char=>{const [x,y,r,b]=bounds(char);return start[0]>=x&&start[0]<=r&&start[1]>=y&&start[1]<=b;});
    picked.sort((a,b)=>{const dist=c=>{const [x,y,r,h]=bounds(c);return Math.hypot((x+r)/2-start[0],(y+h)/2-start[1]);};return dist(a)-dist(b);});
    picked=picked.slice(0,1);
  }else{
    const left=Math.min(start[0],end[0]),right=Math.max(start[0],end[0]);
    const top=Math.min(start[1],end[1]),bottom=Math.max(start[1],end[1]);
    picked=characters.filter(char=>{
      const [x,y,r,b]=bounds(char),q=char.quad;
      const horizontal=Math.abs(q[1][0]-q[0][0])>=Math.abs(q[1][1]-q[0][1]);
      return horizontal?(x+r)/2>=left&&(x+r)/2<=right&&b>=top&&y<=bottom
        :(y+b)/2>=top&&(y+b)/2<=bottom&&r>=left&&x<=right;
    });
  }
  const result=[];
  for(const char of picked){
    const last=result.at(-1);
    if(last&&last.group===char.group&&last.index+1===char.index){
      last.quad=[last.quad[0],char.quad[1],last.quad[2],char.quad[3]];
      last.text+=char.text;last.index=char.index;
    }else result.push({...char,quad:char.quad.map(p=>[...p])});
  }
  return result;
}
