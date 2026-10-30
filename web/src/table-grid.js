export function regularGrid(box,rowCount,columnCount){const [x,y,w,h]=box;return {columns:Array.from({length:columnCount+1},(_,i)=>x+w*i/columnCount),rows:Array.from({length:rowCount+1},(_,i)=>y+h*i/rowCount)};}
export function assignGrid(words,columns,rows){
 if(![columns,rows].every(a=>a.length>=2&&a.every(Number.isFinite)&&a.slice(1).every((v,i)=>v-a[i]>=3)))throw new Error('Los separadores deben dejar al menos 3 pt entre sí.');
 const cells=Array.from({length:rows.length-1},()=>Array.from({length:columns.length-1},()=>[]));let crossing=0;
 for(const word of words){const [x0,y0,x1,y1]=word.bbox,x=(x0+x1)/2,y=(y0+y1)/2,c=columns.findIndex(v=>v>x)-1,r=rows.findIndex(v=>v>y)-1;if(r<0||c<0||r>=cells.length||c>=cells[0].length)continue;if(x0<columns[c]-.8||x1>columns[c+1]+.8||y0<rows[r]-.8||y1>rows[r+1]+.8)crossing++;cells[r][c].push(word);}
 function text(items){const lines=[];for(const word of items.sort((a,b)=>(a.bbox[1]+a.bbox[3]-b.bbox[1]-b.bbox[3])/2||a.bbox[0]-b.bbox[0])){const center=(word.bbox[1]+word.bbox[3])/2,tol=Math.max(2,(word.bbox[3]-word.bbox[1])*.45);if(!lines.length||Math.abs(lines.at(-1)[0]-center)>tol)lines.push([center,[word]]);else lines.at(-1)[1].push(word);}return lines.map(([,line])=>line.sort((a,b)=>a.bbox[0]-b.bbox[0]).map(w=>w.text).join(' ')).join('\n');}
 return {cells:cells.map(row=>row.map(text)),crossing};
}
export function spanMap(cells,spans=[]){
 const covered=new Map(),anchors=new Map(),occupied=new Set();
 for(const span of spans){const {row:r,column:c,rowspan:h,colspan:w}=span;if(![r,c,h,w].every(Number.isInteger)||Math.min(r,c)<0||Math.min(h,w)<1||h*w<2||r+h>cells.length||c+w>cells[0].length)throw new Error('Combinación fuera de la tabla.');
 for(let y=r;y<r+h;y++)for(let x=c;x<c+w;x++){const k=`${y},${x}`;if(occupied.has(k))throw new Error('Las combinaciones se solapan.');occupied.add(k);if(y!==r||x!==c){if(cells[y][x])throw new Error('La combinación ocultaría texto.');covered.set(k,[r,c]);}}anchors.set(`${r},${c}`,span);}
 return {covered,anchors};
}
export function mergeCells(cells,spans,range){
 const [r,c,endR,endC]=range;if(!range.every(Number.isInteger)||r<0||c<0||endR<r||endC<c||endR>=cells.length||endC>=cells[0].length||r===endR&&c===endC)throw new Error('Elige un rectángulo de al menos dos celdas.');
 const {covered,anchors}=spanMap(cells,spans),values=[],next=cells.map(row=>[...row]);
 for(let y=r;y<=endR;y++)for(let x=c;x<=endC;x++){if(covered.has(`${y},${x}`)||anchors.has(`${y},${x}`))throw new Error('Separa la combinación anterior antes de cambiarla.');if(next[y][x])values.push(next[y][x]);next[y][x]='';}
 const text=values.join('\n');if(text.length>4000)throw new Error('La celda combinada supera 4000 caracteres.');next[r][c]=text;
 return {cells:next,spans:[...spans,{row:r,column:c,rowspan:endR-r+1,colspan:endC-c+1}]};
}
