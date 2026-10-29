import React,{useEffect,useRef,useState} from 'react';
import {parsePageRange} from './ranges.js';

function CropPreview({doc,number,operations,margins}) {
  const [src,setSrc]=useState(null),[error,setError]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();let url;setSrc(null);setError(false);
    fetch(`/api/documents/${doc.id}/pages/${number}/preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations}),signal:controller.signal})
      .then(r=>{if(!r.ok)throw new Error();return r.blob();}).then(blob=>{if(!controller.signal.aborted){url=URL.createObjectURL(blob);setSrc(url);}})
      .catch(e=>{if(e.name!=='AbortError')setError(true);});
    return ()=>{controller.abort();if(url)URL.revokeObjectURL(url);};
  },[doc.id,number,operations]);
  const p=doc.pages[number],[top,right,bottom,left]=margins;
  return <div className="crop-preview"><svg viewBox={`0 0 ${p.width} ${p.height}`} aria-label="Vista previa del área de recorte">
    {src&&<image href={src} width={p.width} height={p.height}/>}
    {[top,right,bottom,left].every(Number.isFinite)&&<path d={`M0 0H${p.width}V${p.height}H0Z M${left} ${top}H${p.width-right}V${p.height-bottom}H${left}Z`} fill="#d0533260" fillRule="evenodd"/>}
    {[top,right,bottom,left].every(Number.isFinite)&&p.width>left+right&&p.height>top+bottom&&<rect x={left} y={top} width={p.width-left-right} height={p.height-top-bottom} fill="none" stroke="#205f47" strokeWidth={Math.max(p.width,p.height)/150}/>}
  </svg><small>{error?'No se pudo cargar la vista previa.':`Área delimitada en página ${number+1}; los márgenes se aplican a toda la selección.`}</small></div>;
}

export function Cropper({doc,currentPage,operations,busy,error,onClose,onApply}) {
  const dialog=useRef(null),[range,setRange]=useState(String(currentPage+1)),[margins,setMargins]=useState([20,20,20,20]),[reset,setReset]=useState(false);
  let pages=[],validation='';
  try {
    pages=parsePageRange(range,doc.pages.length);
    if(!reset) {
      if(margins.some(v=>!Number.isFinite(v)||v<0))throw new Error('Los márgenes deben ser números mayores o iguales a cero.');
      if(pages.some(n=>doc.pages[n].width-margins[1]-margins[3]<10||doc.pages[n].height-margins[0]-margins[2]<10))throw new Error('Conserva al menos 10 × 10 puntos en cada página.');
    }
  }catch(e){validation=e.message;}
  useEffect(()=>{dialog.current.showModal();const el=dialog.current;return()=>el.close();},[]);
  return <dialog ref={dialog} className="organizer page-tool-dialog" aria-labelledby="crop-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="crop-title">Recortar páginas</h2><button aria-label="Cerrar recorte" disabled={busy} onClick={onClose}>×</button></div>
    <p className="organizer-intro">Oculta los márgenes sin eliminar su contenido. Puedes deshacer o restaurar la página completa.</p>
    <div className="page-tool-fields"><label>Páginas<input aria-label="Páginas para recortar" value={range} maxLength="2000" disabled={busy} onChange={e=>setRange(e.target.value)}/></label>
      <label>Operación<select aria-label="Modo de recorte" value={reset?'reset':'crop'} disabled={busy} onChange={e=>setReset(e.target.value==='reset')}><option value="crop">Recortar márgenes visibles</option><option value="reset">Restaurar página completa</option></select></label>
      {!reset&&<div className="margin-fields">{['Superior','Derecho','Inferior','Izquierdo'].map((label,i)=><label key={label}>Margen {label.toLowerCase()} (pt)<input type="number" aria-label={`Margen ${label.toLowerCase()}`} min="0" step="any" value={Number.isNaN(margins[i])?'':margins[i]} disabled={busy} onChange={e=>setMargins(values=>values.map((v,j)=>j===i?e.target.valueAsNumber:v))}/></label>)}</div>}
    </div>
    {!reset&&pages.length>0&&<CropPreview doc={doc} number={pages[0]} operations={operations} margins={margins}/>}
    {(error||validation)&&<p role="alert" className="organizer-error">{error||validation}</p>}
    <p className="organizer-note">Los márgenes se miden sobre la orientación visible de cada página. Las marcas quedan guardadas en la nueva versión. El recorte no es una herramienta de censura.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy||!!validation||!pages.length} onClick={()=>onApply({pages,margins,reset})}>{reset?'Restaurar límites originales':'Aplicar recorte'}</button></div>
  </dialog>;
}

export function Splitter({doc,busy,error,onClose,onSplit}) {
  const dialog=useRef(null),[mode,setMode]=useState('blocks'),[size,setSize]=useState(1),[draft,setDraft]=useState(`1-${doc.pages.length}`),[status,setStatus]=useState('');
  let groups=[],validation='';
  try {
    if(mode==='blocks') {
      if(!Number.isInteger(size)||size<1||size>doc.pages.length)throw new Error('Indica un tamaño de bloque válido.');
      groups=Array.from({length:Math.ceil(doc.pages.length/size)},(_,i)=>Array.from({length:Math.min(size,doc.pages.length-i*size)},(_,j)=>i*size+j));
    }else {
      groups=draft.split('\n').map(line=>parsePageRange(line,doc.pages.length));
      const flat=groups.flat();
      if(flat.length!==doc.pages.length||new Set(flat).size!==doc.pages.length)throw new Error('Incluye cada página exactamente una vez entre todos los grupos.');
    }
  }catch(e){validation=e.message;}
  useEffect(()=>{dialog.current.showModal();const el=dialog.current;return()=>el.close();},[]);
  return <dialog ref={dialog} className="organizer page-tool-dialog" aria-labelledby="split-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="split-title">Dividir PDF</h2><button aria-label="Cerrar división" disabled={busy} onClick={onClose}>×</button></div>
    <p className="organizer-intro">Descarga las partes en un ZIP. El documento abierto y su historial se conservan.</p>
    <div className="page-tool-fields"><label>Modo<select aria-label="Modo de división" value={mode} disabled={busy} onChange={e=>{setMode(e.target.value);setStatus('');}}><option value="blocks">Bloques de tamaño fijo</option><option value="groups">Grupos personalizados</option></select></label>
    {mode==='blocks'?<label>Páginas por archivo<input aria-label="Páginas por archivo" type="number" min="1" max={doc.pages.length} value={Number.isNaN(size)?'':size} disabled={busy} onChange={e=>{setSize(e.target.valueAsNumber);setStatus('');}}/></label>:<label>Un archivo por línea<textarea aria-label="Grupos para dividir" rows="5" maxLength="5000" value={draft} disabled={busy} onChange={e=>{setDraft(e.target.value);setStatus('');}} placeholder={'1-3\n4, 6\n5'}/></label>}</div>
    {(error||validation)&&<p role="alert" className="organizer-error">{error||validation}</p>}
    {!validation&&<p role="status">{groups.length} archivos PDF · {doc.pages.length} páginas incluidas</p>}
    {status&&<p role="status">{status}</p>}
    <p className="organizer-note">Los grupos personalizados deben cubrir todas las páginas, sin repetirlas. Se conserva el orden escrito en cada grupo. Los enlaces a páginas de otra parte se retiran. Máximo 100 MB de PDF de salida.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cerrar</button><button className="primary" disabled={busy||!!validation} onClick={async()=>{setStatus('');if(await onSplit(mode==='blocks'?{size}:{groups}))setStatus('ZIP preparado para descargar. El documento abierto no cambió.');}}>Descargar partes ZIP</button></div>
  </dialog>;
}
