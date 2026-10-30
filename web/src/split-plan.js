import {parsePageRange} from './ranges.js';
export function pdfPartName(value){
 if(typeof value!=='string')throw new Error('Cada parte necesita un nombre.');let name=value.normalize('NFC');
 if(!name||name!==name.replace(/^[ .]+|[ .]+$/g,'')||/[\\/:*?"<>|\p{C}]/u.test(name))throw new Error('Usa nombres sin rutas ni caracteres reservados y sin espacios o puntos en los extremos.');
 if(!/\.pdf$/i.test(name))name+='.pdf';const stem=name.slice(0,-4);
 if(!stem||/[ .]$/.test(stem)||/^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$/i.test(stem.split('.')[0])||Array.from(name).length>120||new TextEncoder().encode(name).length>180)throw new Error('Nombre vacío, reservado por Windows o demasiado largo.');
 return name;
}
export function splitGroups(mode,size,draft,count){
 let groups;if(mode==='blocks'){if(!Number.isInteger(size)||size<1||size>count)throw new Error('Indica un tamaño de bloque válido.');groups=Array.from({length:Math.ceil(count/size)},(_,i)=>Array.from({length:Math.min(size,count-i*size)},(_,j)=>i*size+j));}
 else groups=draft.split('\n').map(line=>parsePageRange(line,count));
 const flat=groups.flat();if(flat.length!==count||new Set(flat).size!==count)throw new Error('Incluye cada página exactamente una vez.');return groups;
}
export function namedParts(groups,names){
 const seen=new Set();return groups.map((pages,i)=>{const name=pdfPartName(names[i]??`parte-${String(i+1).padStart(3,'0')}.pdf`),key=name.toLocaleLowerCase('und');if(seen.has(key))throw new Error('Dos partes tienen el mismo nombre.');seen.add(key);return {pages,name};});
}
