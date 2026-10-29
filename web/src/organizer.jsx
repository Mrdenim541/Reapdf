import React, { useEffect, useRef, useState } from 'react';
import { Thumbnail } from './viewer.jsx';

export function Organizer({doc, currentPage, operations, busy, error, onClose, onApply, onExtract}) {
  const dialog = useRef(null);
  const initial = () => doc.pages.map((page,index) => ({page:index, rotation:page.rotation}));
  const [rows, setRows] = useState(initial);
  const [selected, setSelected] = useState(new Set([currentPage]));
  const [status, setStatus] = useState('');
  const mayOrganize = !doc.signed && doc.can_organize;
  const mayExtract = !doc.signed && doc.can_extract;
  const changed = rows.length !== doc.pages.length || rows.some((row,i) => row.page !== i || row.rotation !== doc.pages[i]?.rotation);
  useEffect(() => {
    const element=dialog.current;
    element.showModal();
    return () => element.close();
  }, []);
  function toggle(page) {
    setSelected(old => {const next=new Set(old); if(next.has(page)) next.delete(page); else next.add(page); return next;});
  }
  function move(index,delta) {
    setRows(old => {const next=[...old]; [next[index],next[index+delta]]=[next[index+delta],next[index]]; return next;});
  }
  function remove() {setRows(rows.filter(row => !selected.has(row.page))); setSelected(new Set());}
  return <dialog ref={dialog} className="organizer" aria-labelledby="organizer-title"
    onCancel={e => {e.preventDefault(); if(!busy) onClose();}}>
    <div className="organizer-heading"><div><div className="eyebrow">PÁGINAS DEL DOCUMENTO</div><h2 id="organizer-title">Organizar páginas</h2></div><button aria-label="Cerrar organizador" disabled={busy} onClick={onClose}>×</button></div>
    <p className="organizer-intro">Cambia el orden, gira páginas o elimina las que no necesitas. También puedes extraer la selección en un PDF aparte.</p>
    {operations.some(op=>op.type==='form_rules')&&<p className="organizer-note" role="status">Cálculos protegidos: se actualizarán sus referencias al cambiar el orden o el giro. Si una eliminación retira un campo necesario, se cancelará el cambio y se indicará qué campo debes conservar.</p>}
    <div className="organizer-actions">
      <label><input type="checkbox" aria-label="Seleccionar todas las páginas" disabled={busy} checked={selected.size===rows.length} onChange={() => setSelected(selected.size===rows.length ? new Set() : new Set(rows.map(row=>row.page)))}/> Todas</label>
      <span>{selected.size} seleccionadas · {rows.length} páginas</span>
      <button disabled={busy||!selected.size||!mayOrganize} onClick={()=>setRows(rows.map(row=>selected.has(row.page)?{...row,rotation:(row.rotation+90)%360}:row))}>Girar selección 90°</button>
      <button disabled={busy||!selected.size||selected.size===rows.length||!mayOrganize} onClick={remove}>Eliminar selección</button>
      <button disabled={busy} onClick={()=>{setRows(initial());setSelected(new Set([currentPage]));setStatus('');}}>Restablecer</button>
    </div>
    {error && <p role="alert" className="organizer-error">{error}</p>}
    {status && <p role="status">{status}</p>}
    <div className="organizer-grid">
      {rows.map((row,index)=><article key={row.page} className={`organizer-card ${selected.has(row.page)?'chosen':''}`} data-source-page={row.page}>
        <label className="organizer-select"><input type="checkbox" aria-label={`Seleccionar página ${row.page+1}`} checked={selected.has(row.page)} disabled={busy} onChange={()=>toggle(row.page)}/> Página {row.page+1}</label>
        <Thumbnail docId={doc.id} page={row.page} selected={selected.has(row.page)} operations={operations} onClick={()=>{if(!busy)toggle(row.page);}} rotationDelta={row.rotation-doc.pages[row.page].rotation}/>
        <div className="page-position">Posición {index+1} · {row.rotation}°</div>
        <div className="page-move"><button aria-label={`Subir página ${row.page+1}`} disabled={busy||index===0||!mayOrganize} onClick={()=>move(index,-1)}>←</button><button aria-label={`Bajar página ${row.page+1}`} disabled={busy||index===rows.length-1||!mayOrganize} onClick={()=>move(index,1)}>→</button></div>
      </article>)}
    </div>
    <p className="organizer-note">Puedes deshacer la organización. Las marcas previas quedarán guardadas en la nueva versión; deshaz la organización para volver a editarlas en su sesión anterior. Debes conservar al menos una página.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button>
      <button disabled={busy||!selected.size||!mayExtract} onClick={async()=>{setStatus(''); if(await onExtract(rows.filter(row=>selected.has(row.page))))setStatus('PDF de la selección preparado para descargar. El documento abierto no cambió.');}}>Extraer selección</button>
      <button className="primary" disabled={busy||!changed||!mayOrganize} onClick={()=>onApply(rows)}>{busy?'Procesando…':'Aplicar organización'}</button>
    </div>
  </dialog>;
}
