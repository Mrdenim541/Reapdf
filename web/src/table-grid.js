export function regularGrid(box,rowCount,columnCount){const [x,y,w,h]=box;return {columns:Array.from({length:columnCount+1},(_,i)=>x+w*i/columnCount),rows:Array.from({length:rowCount+1},(_,i)=>y+h*i/rowCount)};}
export function assignGrid(words,columns,rows){
 if(![columns,rows].every(a=>a.length>=2&&a.every(Number.isFinite)&&a.slice(1).every((v,i)=>v-a[i]>=3)))throw new Error('Los separadores deben dejar al menos 3 pt entre sí.');
 const cells=Array.from({length:rows.length-1},()=>Array.from({length:columns.length-1},()=>[]));let crossing=0;
 for(const word of words){const [x0,y0,x1,y1]=word.bbox,x=(x0+x1)/2,y=(y0+y1)/2,c=columns.findIndex(v=>v>x)-1,r=rows.findIndex(v=>v>y)-1;if(r<0||c<0||r>=cells.length||c>=cells[0].length)continue;if(x0<columns[c]-.8||x1>columns[c+1]+.8||y0<rows[r]-.8||y1>rows[r+1]+.8)crossing++;cells[r][c].push(word);}
 function text(items){const lines=[];for(const word of items.sort((a,b)=>(a.bbox[1]+a.bbox[3]-b.bbox[1]-b.bbox[3])/2||a.bbox[0]-b.bbox[0])){const center=(word.bbox[1]+word.bbox[3])/2,tol=Math.max(2,(word.bbox[3]-word.bbox[1])*.45);if(!lines.length||Math.abs(lines.at(-1)[0]-center)>tol)lines.push([center,[word]]);else lines.at(-1)[1].push(word);}return lines.map(([,line])=>line.sort((a,b)=>a.bbox[0]-b.bbox[0]).map(w=>w.text).join(' ')).join('\n');}
 return {cells:cells.map(row=>row.map(text)),crossing};
}
