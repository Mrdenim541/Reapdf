import React,{useEffect,useRef,useState} from 'react';
import {splitGroups,namedParts,numberedPartNames} from './split-plan.js';
export function Splitter({doc,operations,busy,error,onClearError,onClose,onSplit}){
 const dialog=useRef(null),pending=useRef(null);
 const [mode,setMode]=useState('blocks'),[size,setSize]=useState(1),[draft,setDraft]=useState(`1-${doc.pages.length}`),[names,setNames]=useState({});
 const [maximumMb,setMaximumMb]=useState(5),[bytePlan,setBytePlan]=useState(null),[planning,setPlanning]=useState(false);
 const maximumBytes=Number.isFinite(maximumMb)&&maximumMb>=.01&&maximumMb<=100?Math.floor(maximumMb*1000000):null;
 const [prefix,setPrefix]=useState('parte'),[separator,setSeparator]=useState(' '),[start,setStart]=useState(1),[padding,setPadding]=useState(3);
 const [level,setLevel]=useState(1),[bookmarks,setBookmarks]=useState(null),[working,setWorking]=useState(false),[issue,setIssue]=useState(''),[status,setStatus]=useState(''),[receipt,setReceipt]=useState(false),[preserveTags,setPreserveTags]=useState(true);
 const [checked,setChecked]=useState(null),[checking,setChecking]=useState(false);
 const disabled=busy||working;let groups=[],parts=[],generated=[],validation='';
 try{
  if(mode==='bytes'&&maximumBytes===null)throw new Error('Indica un tamaño máximo entre 0,01 y 100 MB.');
  groups=mode==='bytes'?bytePlan?.parts.map(p=>p.pages):mode==='bookmarks'?bookmarks?.parts.map(p=>p.pages):splitGroups(mode,size,draft,doc.pages.length);
  if(!groups){groups=[];if(mode!=='bytes')throw new Error('Prepara las partes desde el nivel de marcadores elegido.');}
  if(groups.length){generated=numberedPartNames(groups.length,{prefix,separator,start,padding});parts=namedParts(groups,Object.fromEntries(generated.map((name,i)=>[i,names[i]??name])));}
 }catch(e){validation=e.message;}
 useEffect(()=>{dialog.current.showModal();return()=>{pending.current?.abort();dialog.current?.close();};},[]);
 useEffect(()=>{
  setBytePlan(null);setPlanning(false);
  if(mode!=='bytes'||maximumBytes===null)return;
  const controller=new AbortController();pending.current?.abort();pending.current=controller;setPlanning(true);setIssue('');
  const timer=setTimeout(async()=>{
   try{
    const r=await fetch(`/api/documents/${doc.id}/split-plan`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,max_bytes:maximumBytes,preserve_tags:preserveTags}),signal:controller.signal}),data=await r.json();
    if(!r.ok)throw new Error(data.detail);
    if(!controller.signal.aborted){setBytePlan(data);setNames({});}
   }catch(e){if(!controller.signal.aborted)setIssue(e.message);}finally{if(!controller.signal.aborted)setPlanning(false);}
  },450);
  return()=>{clearTimeout(timer);controller.abort();};
 },[mode,maximumBytes,doc.id,operations,preserveTags]);
 const reviewKey=JSON.stringify({id:doc.id,operations,groups:parts.map(p=>p.pages),names:parts.map(p=>p.name),preserve_tags:preserveTags,...(mode==='bytes'?{max_bytes:maximumBytes}:{})});
 useEffect(()=>{
  setChecked(null);setIssue('');setStatus('');onClearError?.();
  if(validation||!parts.length){setChecking(false);return;}
  const controller=new AbortController();setChecking(true);
  const timer=setTimeout(async()=>{
   try{
    const config=JSON.parse(reviewKey);
    const response=await fetch(`/api/documents/${config.id}/split-plan`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config),signal:controller.signal});
    const result=await response.json();if(!response.ok)throw new Error(result.detail);
    if(!controller.signal.aborted)setChecked({key:reviewKey,token:result.review_token});
   }catch(e){if(!controller.signal.aborted)setIssue(e.message);}
   finally{if(!controller.signal.aborted)setChecking(false);}
  },350);
  return()=>{clearTimeout(timer);controller.abort();};
 },[reviewKey,validation]);
 async function fromBookmarks(){
  const c=new AbortController();pending.current?.abort();pending.current=c;setWorking(true);setIssue('');setStatus('');
  try{
   const r=await fetch(`/api/documents/${doc.id}/split-plan`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,bookmark_level:level,preserve_tags:preserveTags}),signal:c.signal}),data=await r.json();
   if(!r.ok)throw new Error(data.detail);
   if(!c.signal.aborted){setBookmarks(data);setNames(Object.fromEntries(data.parts.map((p,i)=>[i,p.name])));}
  }catch(e){if(e.name!=='AbortError')setIssue(e.message);}finally{if(!c.signal.aborted)setWorking(false);}
 }
 function generate(){if(generated.length){setNames({});setIssue('');setStatus('');}}
 return <dialog ref={dialog} className="organizer page-tool-dialog" aria-labelledby="split-title" onCancel={e=>{e.preventDefault();if(!disabled)onClose();}}>
  <div className="organizer-heading"><h2 id="split-title">Dividir PDF</h2><button aria-label="Cerrar división" disabled={disabled} onClick={onClose}>×</button></div>
  <p>Genera PDFs independientes con el nombre que elijas. Revisa las páginas de cada archivo y descarga todas las partes en un ZIP. El documento abierto se conserva.</p>
  <div className="page-tool-fields">
   <label>Modo<select aria-label="Modo de división" value={mode} disabled={disabled} onChange={e=>{setMode(e.target.value);setIssue('');setStatus('');}}><option value="blocks">Bloques de tamaño fijo</option><option value="groups">Grupos personalizados</option><option value="bookmarks">Secciones por marcadores</option><option value="bytes">Tamaño máximo por archivo</option></select></label>
   {mode==='bytes'?<><label>Tamaño máximo por PDF (MB)<input aria-label="Tamaño máximo de partes en MB" type="number" min="0.01" max="100" step="0.01" value={Number.isNaN(maximumMb)?'':maximumMb} disabled={disabled} onChange={e=>{setMaximumMb(e.target.valueAsNumber);setStatus('');}}/></label><p>Se calcula con el tamaño real de cada PDF. 1 MB = 1.000.000 bytes. Se conserva el orden y la calidad; un grupo inseparable que exceda el límite detiene la operación.</p></>:mode==='blocks'?<label>Páginas por archivo<input aria-label="Páginas por archivo" type="number" min="1" max={doc.pages.length} value={Number.isNaN(size)?'':size} disabled={disabled} onChange={e=>{setSize(e.target.valueAsNumber);setStatus('');}}/></label>:mode==='groups'?<label>Un archivo por línea<textarea aria-label="Grupos para dividir" rows="4" maxLength="5000" value={draft} disabled={disabled} onChange={e=>{setDraft(e.target.value);setStatus('');}} placeholder={'1-3\n4, 6\n5'}/></label>:<>
    <label>Nivel de marcadores<input aria-label="Nivel de marcadores para dividir" type="number" min="1" max="10" value={Number.isNaN(level)?'':level} disabled={disabled} onChange={e=>{setLevel(e.target.valueAsNumber);setBookmarks(null);}}/></label>
    <button disabled={disabled||!Number.isInteger(level)||level<1||level>10} onClick={fromBookmarks}>{working?'Preparando…':'Preparar desde marcadores'}</button>
    <p>Cada marcador del nivel elegido inicia una parte hasta el siguiente. Las páginas anteriores al primero forman «Inicio». Después puedes cambiar los nombres.</p>
   </>}
  </div>
  {doc.tagged&&<fieldset><legend>Etiquetas de accesibilidad</legend><label className="advanced-check"><input aria-label="Conservar etiquetas al dividir" type="checkbox" checked={preserveTags} disabled={disabled} onChange={e=>{setPreserveTags(e.target.checked);setIssue('');setStatus('');}}/>Conservar etiquetas en las partes</label>
   <p>{preserveTags?'Si la estructura no es compatible, la división se detendrá para evitar partes con etiquetas dañadas.':'Las partes conservarán el texto, las imágenes y la apariencia, sin rasterizar. Se retirarán las etiquetas y las declaraciones PDF/UA y PDF/A; el original no cambia.'}</p></fieldset>}
  {!!groups.length&&<>
   <fieldset><legend>Nombre de los archivos</legend><label>Prefijo<input aria-label="Prefijo de nombres de partes" maxLength="100" value={prefix} disabled={disabled} onChange={e=>{setPrefix(e.target.value);setStatus('');}} placeholder="1.46 PINTURA"/></label>
    <div className="advanced-grid"><label>Separador<select aria-label="Separador de nombres de partes" value={separator} disabled={disabled} onChange={e=>setSeparator(e.target.value)}><option value=" ">Espacio</option><option value="-">Guion (-)</option><option value="_">Guion bajo (_)</option><option value="">Ninguno</option></select></label>
     <label>Comenzar en<input aria-label="Número inicial de partes" type="number" min="0" max="99999999" value={Number.isNaN(start)?'':start} disabled={disabled} onChange={e=>setStart(e.target.valueAsNumber)}/></label>
     <label>Cifras mínimas<input aria-label="Cifras de nombres de partes" type="number" min="1" max="8" value={Number.isNaN(padding)?'':padding} disabled={disabled} onChange={e=>setPadding(e.target.valueAsNumber)}/></label></div>
    {!!generated.length&&<p aria-label="Ejemplo de nombres de partes">{generated.slice(0,3).join(' · ')}{generated.length>3?' · …':''}</p>}
    <button disabled={disabled||!generated.length} onClick={generate}>Generar nombres numerados</button><p>La serie se actualiza al cambiar el formato. Los nombres personalizados se conservan; este botón los reemplaza por la serie.</p>
   </fieldset>
   <p role="status">{groups.length} archivos PDF · {doc.pages.length} páginas incluidas</p>
  </>}
  <div style={{maxHeight:300,overflow:'auto'}} className="page-tool-fields">{groups.map((pages,i)=>({pages,name:names[i]??generated[i]??''})).map((part,i)=><label key={i}>Archivo {i+1} · páginas {part.pages.map(n=>n+1).join(', ')}{mode==='bytes'&&bytePlan?.parts[i]?.bytes!=null?` · ${(bytePlan.parts[i].bytes/1000000).toFixed(3)} MB`:null}<input aria-label={`Nombre de parte ${i+1}`} value={names[i]??part.name} maxLength="120" disabled={disabled} onChange={e=>{setNames({...names,[i]:e.target.value});setStatus('');}}/></label>)}</div>
  <label><input aria-label="Incluir relación de archivos de división" type="checkbox" checked={receipt} disabled={disabled} onChange={e=>setReceipt(e.target.checked)}/>Incluir relación de archivos y páginas en el ZIP</label>
  {(error||issue||validation)&&<p role="alert">{error||issue||validation}</p>}{planning&&<p role="status">Calculando partes según su tamaño real…</p>}{checking&&<p role="status">Comprobando páginas, nombres y etiquetas…</p>}{checked?.key===reviewKey&&<p role="status">Configuración comprobada. Antes de publicar el ZIP se verificará el contenido y la apariencia de cada parte.</p>}{status&&<p role="status">{status}</p>}
  <p className="organizer-note">Se conserva el orden escrito. Cada página debe aparecer una vez; los enlaces a otra parte se retiran. Nombres compatibles con Windows, sin duplicados. Máximo 100 MB de PDF de salida. Los documentos firmados y otras estructuras no compatibles requieren una copia adecuada.</p>
  <div className="organizer-footer"><button disabled={disabled} onClick={onClose}>Cerrar</button><button className="primary" disabled={disabled||!!validation||!parts.length||checked?.key!==reviewKey} onClick={async()=>{setStatus('');if(await onSplit({groups:parts.map(p=>p.pages),names:parts.map(p=>p.name),manifest:receipt,preserve_tags:preserveTags,review_token:checked.token,...(mode==='bytes'?{max_bytes:maximumBytes}:{})}))setStatus('ZIP preparado para descargar. El documento abierto no cambió.');}}>Descargar partes ZIP</button></div>
 </dialog>;
}
