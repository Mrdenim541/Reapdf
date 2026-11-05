import React,{useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import './quick-text.css';

export function TextContextMenu({target,onEdit,onDelete,onClose}){
 const menu=useRef(null);
 useEffect(()=>{
  menu.current?.querySelector('button')?.focus();
  const outside=e=>{if(!menu.current?.contains(e.target))onClose();},key=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();onClose();}},close=()=>onClose();
  document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key);window.addEventListener('resize',close);window.addEventListener('scroll',close,true);
  return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key);window.removeEventListener('resize',close);window.removeEventListener('scroll',close,true);};
 },[target]);
 return createPortal(<div ref={menu} className="text-context-menu" role="menu" aria-label="Opciones del texto seleccionado" style={{left:Math.max(8,Math.min(target.x,window.innerWidth-188)),top:Math.max(8,Math.min(target.y,window.innerHeight-140))}} onKeyDown={e=>{if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();const buttons=[...menu.current.querySelectorAll('button')],current=buttons.indexOf(document.activeElement),index=e.key==='Home'?0:e.key==='End'?buttons.length-1:(current+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length;buttons[index]?.focus();}}}>
  <button role="menuitem" onClick={onEdit}>Editar</button><button role="menuitem" onClick={onDelete}>Eliminar</button><button role="menuitem" onClick={onClose}>Cerrar menú</button>
 </div>,document.body);
}

export function QuickTextDialog({doc,page,operations,span,remove=false,busy,error,onApply,onClose}){
 const dialog=useRef(null),input=useRef(null),started=useRef(false),[row,setRow]=useState(null),[loading,setLoading]=useState(true),[saving,setSaving]=useState(false),[issue,setIssue]=useState(''),[value,setValue]=useState(span.text),[accessible,setAccessible]=useState(''),[same,setSame]=useState(false),[family,setFamily]=useState('original'),[style,setStyle]=useState('regular'),[size,setSize]=useState(span.size);
 const g=doc.pages[page],width=g.rotation%180?g.height:g.width,height=g.rotation%180?g.width:g.height;
 const box=[Math.max(0,span.bbox[0]),Math.max(0,span.bbox[1]),Math.min(width,span.bbox[2])-Math.max(0,span.bbox[0]),Math.min(height,span.bbox[3])-Math.max(0,span.bbox[1])],disabled=busy||loading||saving;
 useEffect(()=>{dialog.current.showModal();const c=new AbortController();fetch(`/api/documents/${doc.id}/inspect-styled-text`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,page,box}),signal:c.signal}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.detail);return data;}).then(data=>{if(c.signal.aborted)return;const rows=data.runs.filter(r=>r.text===span.text&&Math.abs(r.origin[0]-span.origin[0])<.1&&Math.abs(r.origin[1]-span.origin[1])<.1);if(rows.length!==1)throw new Error('El texto seleccionado no se identifica de forma única.');setRow(rows[0]);setSize(rows[0].size);setAccessible(rows[0].accessible_text||'');setSame(rows[0].alternative_follows_text===true);}).catch(e=>{if(e.name!=='AbortError')setIssue(e.message);}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>{c.abort();dialog.current?.close();};},[doc.id,page,span.id]);
 useEffect(()=>{if(!loading&&!remove){input.current?.focus();input.current?.select();}},[loading]);
 useEffect(()=>{if(remove&&!loading&&!busy&&row?.editable&&!started.current){started.current=true;submit(true);}},[row,remove,loading,busy]);
 const formatChanged=!!row?.format_editable&&(family!=='original'||size!==row.size),changed=value!==span.text||formatChanged||!!row?.has_actual_text&&(same?value:accessible)!==row.accessible_text;
 async function submit(deleting=remove){
  if(busy||loading||saving||!row?.editable||!deleting&&!changed)return;setSaving(true);setIssue('');const text=deleting?'':value;
  try{const change={id:row.id,text,...(!deleting&&formatChanged?{format:{family,style:family==='original'?'original':style,size}}:{}),...(row.has_actual_text?{accessible_text:deleting?'':same?text:accessible}:{})};if(await onApply('replace-styled-text',{page,box,changes:[change],expand:false}))onClose();}catch(e){setIssue(e.message);}finally{setSaving(false);}
 }
 return createPortal(<dialog ref={dialog} className="quick-text-dialog" aria-labelledby="quick-text-title" onCancel={e=>{e.preventDefault();if(!busy&&!saving)onClose();}} onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)&&!disabled){e.preventDefault();submit();}}}>
  <h2 id="quick-text-title">{remove?'Eliminar texto':'Editar texto'}</h2>
  {!remove&&<label>Texto<textarea ref={input} aria-label="Texto de edición rápida" value={value} rows="3" maxLength="4000" disabled={disabled||!row?.editable} onChange={e=>setValue(e.target.value.replace(/[\r\n]+/g,' '))}/></label>}
  {!remove&&row?.format_editable&&<details className="quick-text-format"><summary>Fuente y tamaño</summary><div className="quick-format-controls"><label>Fuente<select aria-label="Fuente de edición rápida" value={family} disabled={disabled} onChange={e=>setFamily(e.target.value)}><option value="original">Original · {span.font}</option><option value="sans">DejaVu Sans</option><option value="serif">DejaVu Serif</option><option value="mono">DejaVu Sans Mono</option></select></label>{family!=='original'&&<label>Estilo<select aria-label="Estilo de edición rápida" value={style} disabled={disabled} onChange={e=>setStyle(e.target.value)}><option value="regular">Regular</option><option value="bold">Negrita</option><option value="italic">Cursiva</option><option value="bold-italic">Negrita y cursiva</option></select></label>}<label>Tamaño (pt)<input aria-label="Tamaño de edición rápida" type="number" min="6" max="144" step=".5" value={size} disabled={disabled} onChange={e=>setSize(e.target.valueAsNumber)}/></label></div></details>}
  {!remove&&row?.has_actual_text&&<details open={!same}><summary>Lectura accesible</summary><label><input type="checkbox" checked={same} disabled={disabled} onChange={e=>setSame(e.target.checked)}/> Usar el mismo texto visible</label>{!same&&<textarea aria-label="Lectura accesible de edición rápida" rows="2" maxLength="4000" value={accessible} disabled={disabled} onChange={e=>setAccessible(e.target.value)}/>}</details>}
  <p className="quick-text-hint">{loading?'Preparando texto…':remove?saving?'Eliminando…':'Puedes deshacer la eliminación.':formatChanged?'Conserva posición, color y etiquetas. Ctrl+Enter para aplicar.':'Conserva la fuente y la posición. Ctrl+Enter para aplicar.'}</p>
  {(issue||error||row&&!row.editable)&&<p role="alert">{issue||error||row.reason}</p>}
  <div className="quick-text-actions"><button disabled={busy||saving} onClick={onClose}>Cancelar</button><button className="primary" disabled={disabled||!row?.editable||(!remove&&!changed)} onClick={()=>submit()}>{remove?'Eliminar':'Aplicar'}</button></div>
 </dialog>,document.body);
}
