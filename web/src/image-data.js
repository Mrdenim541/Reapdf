// Leer dimensiones antes de decodificar: un archivo pequeño puede expandirse mucho.
export function imageDimensions(bytes) {
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  if([137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v)) {
    if(bytes.length<33||view.getUint32(8)!==13||view.getUint32(12)!==0x49484452)throw new Error('Cabecera PNG no válida.');
    return {width:view.getUint32(16),height:view.getUint32(20),mime:'image/png'};
  }
  if(bytes[0]===255&&bytes[1]===216&&bytes[2]===255) {
    let offset=2;
    while(offset<bytes.length&&bytes[offset]===255) {
      while(offset<bytes.length&&bytes[offset]===255)offset++;
      if(offset>=bytes.length)break;
      const marker=bytes[offset++];
      if(marker===216||marker===1||(marker>=208&&marker<=215))continue;
      if(marker===217||marker===218||offset+2>bytes.length)break;
      const length=view.getUint16(offset);
      if(length<2||offset+length>bytes.length)break;
      if([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)) {
        if(length<8)break;
        return {width:view.getUint16(offset+5),height:view.getUint16(offset+3),mime:'image/jpeg'};
      }
      offset+=length;
    }
    throw new Error('Cabecera JPEG no válida.');
  }
  throw new Error('Solo se admiten imágenes PNG o JPEG.');
}
