// One semantic candidate per cell; suggest only complete, aligned rectangular rows.
// This changes the review draft, never the PDF. Every page still requires review.
export function suggestTable(entries){
 if(!Array.isArray(entries)||entries.length<4||entries.length>500||entries.some(e=>e.kind!=='text'||!Array.isArray(e.box)||e.box.length!==4||e.box.some(v=>!Number.isFinite(v))||Math.min(e.box[2],e.box[3])<=0))throw new Error('La sugerencia necesita objetos de texto separados para cada celda. Ajusta la tabla manualmente.');
 const heights=entries.map(e=>e.box[3]).sort((a,b)=>a-b),tolerance=Math.max(2,heights[Math.floor(heights.length/2)]*.45),rows=[];
 for(const entry of [...entries].sort((a,b)=>a.box[1]+a.box[3]/2-b.box[1]-b.box[3]/2||a.box[0]-b.box[0])){
  const center=entry.box[1]+entry.box[3]/2;
  if(!rows.length||Math.abs(rows.at(-1).center-center)>tolerance)rows.push({center,cells:[entry]});else rows.at(-1).cells.push(entry);
 }
 const count=rows[0].cells.length;
 if(rows.length<2||rows.length>100||count<2||count>30||rows.some(row=>row.cells.length!==count))throw new Error('No se encontró una tabla rectangular completa. Revisa roles, filas y columnas manualmente.');
 rows.forEach(row=>row.cells.sort((a,b)=>a.box[0]-b.box[0]));
 const reference=rows[0].cells;
 if(rows.some(row=>row.cells.some((cell,c)=>Math.abs(cell.box[0]-reference[c].box[0])>Math.max(5,Math.min(cell.box[2],reference[c].box[2])*.25)||c>0&&cell.box[0]<row.cells[c-1].box[0]+row.cells[c-1].box[2]+2)))throw new Error('Las columnas se cruzan o no están alineadas. Usa la revisión manual.');
 return rows.flatMap((row,r)=>row.cells.map((entry,c)=>({id:entry.id,role:r===0?'TH':'TD',table:1,row:r+1,column:c+1,rowspan:1,colspan:1,scope:'Column'})));
}
