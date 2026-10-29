import React from 'react';
import {imageDimensions} from './image-data.js';

export async function readImage(file) {
  if(!file||file.size>2*1024*1024)throw new Error('Selecciona una imagen PNG o JPEG de hasta 2 MB.');
  const bytes=new Uint8Array(await file.arrayBuffer());
  const {width,height,mime}=imageDimensions(bytes);
  if(width<1||height<1||width*height>24_000_000)throw new Error('La imagen debe tener entre 1 y 24 millones de píxeles.');
  const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('No se pudo leer la imagen.'));reader.readAsDataURL(file);});
  const image=new Image();image.src=`data:${mime};base64,${data}`;
  await image.decode();
  if(image.naturalWidth!==width||image.naturalHeight!==height)throw new Error('Dimensiones de imagen inconsistentes.');
  return {data,name:file.name.slice(0,180),pixels:[image.naturalWidth,image.naturalHeight]};
}

export function ImageTargets({operations,page,selectedId,onSelect}) {
  return operations.filter(op=>op.type==='image'&&op.page===page).map((op,index)=>
    <rect key={op.id} x={op.points[0][0]} y={op.points[0][1]} width={op.points[1][0]-op.points[0][0]} height={op.points[1][1]-op.points[0][1]}
      fill="transparent" stroke={selectedId===op.id?'#2785d2':'#2785d288'} strokeWidth="1" role="button" tabIndex="0"
      aria-label={`Seleccionar imagen ${index+1}: ${op.name}`} style={{cursor:'pointer'}}
      onPointerDown={e=>e.stopPropagation()} onClick={()=>onSelect(op.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(op.id);}}}/>
  );
}
