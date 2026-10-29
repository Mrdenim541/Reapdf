import React, { useEffect, useRef, useState } from 'react';
import { Thumbnail } from './viewer.jsx';
import { parsePageRange } from './ranges.js';

const release = id => fetch(`/api/documents/${id}`, {method:'DELETE'}).catch(()=>{});

export function Inserter({doc, busy, error, onClearError, onClose, onApply, mode='insert', currentPage=0}) {
  const replacing=mode==='replace';
  const dialog=useRef(null), fileInput=useRef(null), sourceRef=useRef(null);
  const [source,setSource]=useState(null), [sourceBusy,setSourceBusy]=useState(false);
  const [sourceError,setSourceError]=useState(''), [range,setRange]=useState('');
  const [position,setPosition]=useState(replacing?currentPage:doc.pages.length);
  const [replaceCount,setReplaceCount]=useState(1);
  const blocked=busy||sourceBusy;
  let pages=[], rangeError='';
  if(source) {
    try {pages=parsePageRange(range,source.pages.length);} catch(e) {rangeError=e.message;}
  }
  const countValid=!replacing || (Number.isInteger(replaceCount)&&replaceCount>=1&&replaceCount<=doc.pages.length-position);
  const total=doc.pages.length+pages.length-(replacing?replaceCount:0);
  const incompatible=source && (source.signed ? 'El PDF tiene indicadores de firma. Su importación no está disponible en esta versión.' : !source.can_extract ? 'El PDF de origen no permite copiar páginas.' : '');
  useEffect(()=>{
    const element=dialog.current; element.showModal();
    return ()=>{element.close(); if(sourceRef.current)release(sourceRef.current);};
  },[]);
  async function load(file) {
    if(!file)return;
    setSourceBusy(true);setSourceError('');onClearError();
    try {
      const form=new FormData();form.append('file',file);
      const response=await fetch('/api/documents',{method:'POST',body:form});
      if(!response.ok) {const data=await response.json();throw new Error(data.detail || 'No se pudo abrir el PDF.');}
      const data=await response.json();
      const previous=sourceRef.current;sourceRef.current=data.id;
      setSource({...data,name:file.name});setRange(data.pages.length===1?'1':`1-${data.pages.length}`);
      if(previous)release(previous);
    }catch(e){setSourceError(e.message);}finally{setSourceBusy(false);if(fileInput.current)fileInput.current.value='';}
  }
  return <dialog ref={dialog} className="organizer inserter" aria-labelledby="insert-title" onCancel={e=>{e.preventDefault();if(!blocked)onClose();}}>
    <div className="organizer-heading"><div><div className="eyebrow">COMBINAR DOCUMENTOS</div><h2 id="insert-title">{replacing?'Reemplazar páginas':'Unir o insertar PDF'}</h2></div><button aria-label="Cerrar inserción" disabled={blocked} onClick={onClose}>×</button></div>
    <p className="organizer-intro">{replacing?'Sustituye un bloque de páginas por una selección de otro PDF. Puedes deshacer la operación.':'Añade otro PDF al final o elige sus páginas y la posición de inserción. Puedes deshacer la operación.'}</p>
    {doc&&<p className="organizer-note">Las reglas de cálculo del proyecto se conservan en los campos originales supervivientes. Las copias importadas tienen valores independientes. Si el reemplazo elimina un campo necesario, se cancela el cambio.</p>}
    <input hidden ref={fileInput} type="file" aria-label={replacing?'PDF para reemplazar':'PDF para insertar'} accept=".pdf,application/pdf" onChange={e=>load(e.target.files[0])}/>
    <div className="source-picker"><div><b>{source?source.name:'Selecciona otro documento'}</b><p>{source?`${source.pages.length} páginas disponibles`:'Hasta 30 MB por archivo. El documento abierto conserva sus cambios.'}</p></div><button disabled={blocked} onClick={()=>fileInput.current.click()}>{sourceBusy?'Abriendo…':source?'Cambiar PDF':'Seleccionar PDF'}</button></div>
    {replacing&&!countValid&&<p className="organizer-error" role="alert">Indica entre 1 y {doc.pages.length-position} páginas originales para retirar.</p>}
    {(sourceError||error||incompatible)&&<p className="organizer-error" role="alert">{sourceError||error||incompatible}</p>}
    {source&&<div className="insert-options">
      <div className="insert-preview">{pages.length>0&&<Thumbnail key={`${source.id}:${pages[0]}`} docId={source.id} page={pages[0]} operations={[]} selected={false} onClick={()=>{}}/>}<span>Primera página de la selección</span></div>
      <div className="insert-fields">
        <label>Páginas del PDF de origen<input aria-label={replacing?'Páginas de reemplazo':'Páginas para insertar'} value={range} maxLength="2000" disabled={blocked} onChange={e=>{setRange(e.target.value);onClearError();}} placeholder="Ejemplo: 1-3, 5"/></label>
        <div className="range-help">Rangos y páginas separados por comas. Se respeta el orden escrito.</div>
        {rangeError&&<p role="alert" className="range-error">{rangeError}</p>}
        <label>{replacing?'Inicio del bloque a reemplazar':'Posición de inserción'}<select aria-label={replacing?'Inicio del reemplazo':'Posición de inserción'} value={position} disabled={blocked} onChange={e=>{const next=Number(e.target.value);setPosition(next);setReplaceCount(n=>Math.min(n,doc.pages.length-next));onClearError();}}>
          {replacing?doc.pages.map((_,i)=><option key={i} value={i}>Desde página {i+1}</option>):<><option value={0}>Al principio</option>{Array.from({length:doc.pages.length-1},(_,i)=><option key={i+1} value={i+1}>Después de página {i+1}</option>)}<option value={doc.pages.length}>Al final</option></>}
        </select></label>
        {replacing&&<label>Páginas originales que se retirarán<input aria-label="Cantidad a reemplazar" type="number" min="1" max={doc.pages.length-position} value={Number.isNaN(replaceCount)?'':replaceCount} disabled={blocked} onChange={e=>{setReplaceCount(e.target.valueAsNumber);onClearError();}}/></label>}
        <p className={`insertion-summary ${total>500?'range-error':''}`} role="status">{pages.length} páginas para importar{replacing?` · ${countValid?replaceCount:'?'} para retirar`:''} · {Number.isFinite(total)?total:'?'} páginas en el resultado{total>500?' · máximo 500':''}</p>
      </div>
    </div>}
    {replacing&&<p className="organizer-note">Se retiran las páginas originales completas, incluidas sus marcas y campos. Los enlaces y marcadores con destino a páginas retiradas se eliminan. Las etiquetas de las páginas importadas sustituyen a las del bloque.</p>}
    <p className="organizer-note">Se importan páginas y sus anotaciones. Los formularios jerárquicos compatibles conservan sus grupos. Si un nombre raíz coincide, la copia recibe un sufijo como «(2)»; sus valores siguen siendo independientes del original. Los marcadores de origen se agrupan por archivo. Los PDF con capas o formularios con scripts todavía no se pueden importar.</p>
    <div className="organizer-footer"><button disabled={blocked} onClick={onClose}>Cancelar</button><button className="primary" disabled={blocked||!source||!pages.length||!!rangeError||!!incompatible||total>500||!countValid} onClick={()=>onApply({source_id:source.id,pages,position,source_name:source.name.slice(0,200),...(replacing?{replace_count:replaceCount}:{})})}>{busy?'Procesando…':replacing?'Reemplazar páginas':'Insertar páginas'}</button></div>
  </dialog>;
}
