import React,{useEffect,useRef,useState} from 'react';
export function Layers({doc,page,operations,busy,error,onClose,onAction}){
 const dialog=useRef(null),urls=useRef([]);
 const [layers,setLayers]=useState([]),[visible,setVisible]=useState([]),[groups,setGroups]=useState([]);
 const [preview,setPreview]=useState(null),[issue,setIssue]=useState(''),[working,setWorking]=useState(false),[loaded,setLoaded]=useState(false);
 const [configurations,setConfigurations]=useState([]),[configuration,setConfiguration]=useState(''),[initial,setInitial]=useState([]),[initialGroups,setInitialGroups]=useState([]);
 const [usage,setUsage]=useState([]),[usageSupported,setUsageSupported]=useState(false),[usageEdited,setUsageEdited]=useState(false);
 const [screen,setScreen]=useState([]),[screenSupported,setScreenSupported]=useState(false),[screenEdited,setScreenEdited]=useState(false);
 const [simulate,setSimulate]=useState(false),[zoom,setZoom]=useState('100'),[language,setLanguage]=useState(navigator.language||'es');
 const context=simulate?{zoom:Number(zoom)/100,language}:null;
 const key=JSON.stringify({usage:usageEdited?usage:null,screen:screenEdited?screen:null,context,visible:[...visible].sort((a,b)=>a-b),configuration}),disabled=busy||working;
 useEffect(()=>{
  dialog.current.showModal();const c=new AbortController();
  fetch(`/api/documents/${doc.id}/layers`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations}),signal:c.signal})
   .then(async r=>{const d=await r.json();if(!r.ok)throw new Error(d.detail);return d;})
   .then(d=>{if(c.signal.aborted)return;setUsage(d.usage?.layers||[]);setUsageSupported(d.usage?.supported===true);setScreen(d.screen?.layers||[]);setScreenSupported(d.screen?.supported===true);setLayers(d.layers);setInitial(d.layers);setInitialGroups(d.radio_groups);setConfigurations(d.configurations||[]);setVisible(d.layers.filter(l=>l.visible).map(l=>l.id));setGroups(d.radio_groups);setLoaded(true);})
   .catch(e=>{if(e.name!=='AbortError')setIssue(e.message);});
  return()=>{c.abort();dialog.current?.close();for(const url of urls.current)URL.revokeObjectURL(url);};
 },[doc.id]);
 function toggle(layer){
  if(visible.includes(layer.id))setVisible(visible.filter(i=>i!==layer.id));
  else{const peers=new Set(groups.filter(g=>g.includes(layer.id)).flat());if(layers.some(l=>l.locked&&l.visible&&peers.has(l.id))){setIssue('El grupo contiene una capa visible bloqueada.');return;}setVisible([...visible.filter(i=>!peers.has(i)),layer.id]);}
  setPreview(null);
 }
 function changeScreen(id,patch){setScreen(screen.map(r=>r.id===id?{...r,...patch}:r));setScreenEdited(true);setPreview(null);}
 const payload={visible,usage:usageEdited?usage:undefined,screen:screenEdited?screen:undefined,configuration:configuration===''?null:Number(configuration)};
 async function prepare(){setWorking(true);setIssue('');try{
  const r=await fetch(`/api/documents/${doc.id}/set-layers`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,...payload,page,preview:true,screen_context:context})});
  if(!r.ok)throw new Error((await r.json()).detail);
  const url=URL.createObjectURL(await r.blob());urls.current.push(url);setPreview({url,key});
 }catch(e){setIssue(e.message);}finally{setWorking(false);}}
 return <dialog ref={dialog} className="organizer advanced-dialog" aria-label="Capas del PDF" onCancel={e=>{e.preventDefault();if(!disabled)onClose();}}>
  <h2>Capas del PDF</h2><p>Configura la visibilidad inicial y las preferencias de cada capa. Ocultar una capa conserva su contenido: no es censura.</p>
  {loaded&&!layers.length&&<p>No se encontraron capas opcionales en este PDF.</p>}
  {!!configurations.length&&<label>Configuración<select aria-label="Configuración de capas" value={configuration} disabled={disabled} onChange={e=>{
   const id=e.target.value;setConfiguration(id);setPreview(null);
   if(id===''){setLayers(initial);setVisible(initial.filter(l=>l.visible).map(l=>l.id));setGroups(initialGroups);}
   else{const cfg=configurations.find(c=>c.id===Number(id));setVisible(cfg.visible);setLayers(initial.map(l=>({...l,locked:cfg.locked.includes(l.id),visible:cfg.visible.includes(l.id)})));setGroups(cfg.radio_groups);}
  }}><option value="">Actual del documento</option>{configurations.map(c=><option key={c.id} value={c.id} disabled={!c.supported}>{c.name}{c.supported?'':' · requiere revisión especializada'}</option>)}</select></label>}
  {layers.map(l=><label key={l.id}><input type="checkbox" aria-label={`Capa ${l.name}`} disabled={disabled||l.locked} checked={visible.includes(l.id)} onChange={()=>toggle(l)}/> {l.name}{l.locked?' · bloqueada':''}</label>)}
  {!!layers.length&&<>
   <details><summary>Pantalla, zoom e idioma</summary>
    <p>Guarda condiciones PDF nativas para lectores compatibles. Puedes simularlas aquí. El visor principal de Reapdf aún no cambia automáticamente las capas al variar zoom o idioma; la simulación no cambia la visibilidad inicial guardada.</p>
    {!screenSupported&&<p>Las condiciones existentes requieren otro tratamiento y se conservarán.</p>}
    {screen.map(row=><fieldset key={row.id} disabled={disabled||!screenSupported||layers.find(l=>l.id===row.id)?.locked}>
     <legend>{layers.find(l=>l.id===row.id)?.name}</legend>
     <label>Al abrir<select aria-label={`Pantalla capa ${row.id}`} value={row.view||''} onChange={e=>changeScreen(row.id,{view:e.target.value||null})}><option value="">Sin preferencia</option><option value="ON">Mostrar</option><option value="OFF">Ocultar</option></select></label>
     <label><input aria-label={`Condición de zoom capa ${row.id}`} type="checkbox" checked={row.zoom!==null} onChange={e=>changeScreen(row.id,{zoom:e.target.checked?{min:1,max:null}:null})}/> Mostrar según zoom</label>
     {row.zoom&&<div className="form-row">{[['min','Desde (%)'],['max','Hasta, sin incluir (%)']].map(([bound,label])=><label key={bound}>{label}<input aria-label={`${label} capa ${row.id}`} type="number" min="0" step="1" value={row.zoom[bound]===null?'':row.zoom[bound]*100} onChange={e=>changeScreen(row.id,{zoom:{...row.zoom,[bound]:e.target.value===''?null:Number(e.target.value)/100}})}/></label>)}</div>}
     <label><input aria-label={`Condición de idioma capa ${row.id}`} type="checkbox" checked={row.language!==null} onChange={e=>changeScreen(row.id,{language:e.target.checked?{lang:'es',preferred:false}:null})}/> Mostrar según idioma</label>
     {row.language&&<><label>Idioma de la capa<input aria-label={`Idioma capa ${row.id}`} value={row.language.lang} maxLength="63" placeholder="es-MX" onChange={e=>changeScreen(row.id,{language:{...row.language,lang:e.target.value}})}/></label><label><input aria-label={`Idioma preferido capa ${row.id}`} type="checkbox" checked={row.language.preferred} onChange={e=>changeScreen(row.id,{language:{...row.language,preferred:e.target.checked}})}/> Alternativa preferida si no hay coincidencia exacta</label></>}
    </fieldset>)}
   </details>
   <details><summary>Impresión y exportación de capas</summary><p>Guarda preferencias PDF nativas para lectores compatibles. Reapdf aplica impresión a una copia temporal. Exportar no elimina contenido del PDF guardado.</p>
    {!usageSupported&&<p>Las reglas automáticas existentes requieren otro tratamiento.</p>}
    {usage.map(row=><fieldset key={row.id} disabled={disabled||!usageSupported||layers.find(l=>l.id===row.id)?.locked}><legend>{layers.find(l=>l.id===row.id)?.name}</legend>{[['print','Imprimir'],['export','Exportar']].map(([event,label])=><label key={event}>{label}<select aria-label={`${label} capa ${row.id}`} value={row[event]||''} onChange={e=>{setUsage(usage.map(r=>r.id===row.id?{...r,[event]:e.target.value||null}:r));setUsageEdited(true);setPreview(null);}}><option value="">Sin preferencia explícita</option><option value="ON">Mostrar</option><option value="OFF">Ocultar</option></select></label>)}</fieldset>)}
   </details>
   <fieldset disabled={disabled||!screenSupported}><legend>Comprobar condiciones</legend><label><input type="checkbox" aria-label="Simular condiciones de pantalla" checked={simulate} onChange={e=>{setSimulate(e.target.checked);setPreview(null);}}/> Simular zoom e idioma en la vista previa</label>
    {simulate&&<div className="form-row"><label>Zoom (%)<input aria-label="Zoom de simulación" type="number" min="5" max="1600" value={zoom} onChange={e=>{setZoom(e.target.value);setPreview(null);}}/></label><label>Idioma<input aria-label="Idioma de simulación" value={language} maxLength="63" onChange={e=>{setLanguage(e.target.value);setPreview(null);}}/></label></div>}
   </fieldset>
  </>}
  <button disabled={disabled||!layers.length||doc.signed||!doc.can_edit} onClick={prepare}>Vista previa de capas</button>
  {preview&&<><p>{simulate?'Simulación del contexto indicado. Se guardarán las preferencias y la visibilidad inicial, no este contexto.':'Vista inicial del PDF que se guardará.'}</p><img style={{maxWidth:'100%',maxHeight:'55vh'}} src={preview.url} alt="Visibilidad de capas"/></>}
  {(issue||error)&&<p role="alert">{issue||error}</p>}
  {simulate&&<p>La copia contextual fija la visibilidad de esta simulación y retira sus condiciones de pantalla. Conserva capas, contenido y preferencias de impresión/exportación. Puedes deshacer al abrirla.</p>}
  <div className="organizer-footer"><button disabled={disabled} onClick={onClose}>Cerrar</button>{simulate&&<button disabled={disabled||!preview||preview.key!==key} onClick={()=>onAction('set-layers',{...payload,apply_context:true,screen_context:context})}>Abrir copia contextual</button>}<button className="primary" disabled={disabled||!preview||preview.key!==key} onClick={()=>onAction('set-layers',payload)}>Guardar visibilidad</button></div>
 </dialog>;
}
