import React,{useEffect,useRef,useState} from 'react';
import {parsePageRange} from './ranges.js';
import {contentFonts} from './content-tools.jsx';
const slots=['top_left','top_center','top_right','bottom_left','bottom_center','bottom_right'];
const labels=['Encabezado izquierdo','Encabezado central','Encabezado derecho','Pie izquierdo','Pie central','Pie derecho'];

export function HeaderFooterEditor({doc,page,operations,numbering,busy,error,onClose,onApply}) {
  const existing=operations.find(op=>op.type==='header_footer');
  const dialog=useRef(null),pending=useRef(null),lastUrl=useRef(null);
  const [range,setRange]=useState(existing?existing.pages.map(n=>n+1).join(', '):`1-${doc.pages.length}`);
  const [config,setConfig]=useState(()=>({type:'header_footer',page:0,font:'helv',size:10,color:[0,0,0],margins:[20,24,20,24],start:1,style:'D',padding:0,...existing,
    slots:{...Object.fromEntries(slots.map(key=>[key,''])),...existing?.slots,...(numbering&&!existing?.slots.bottom_center?{bottom_center:'Página {numero} de {total}'}:{})}}));
  const [previewPage,setPreviewPage]=useState(page),[preview,setPreview]=useState(null),[working,setWorking]=useState(false),[previewError,setPreviewError]=useState('');
  let pages=[],validation='';
  try{pages=parsePageRange(range,doc.pages.length);if(!Object.values(config.slots).some(text=>text.trim()))throw new Error('Completa una posición o elige una plantilla de numeración.');if(![config.size,...config.margins,config.start,config.padding].every(Number.isFinite))throw new Error('Completa las medidas y la numeración con números válidos.');}catch(e){validation=e.message;}
  const plan={...config,pages},effectivePage=pages.includes(previewPage)?previewPage:(pages[0]??0);
  const key=JSON.stringify(plan)+':'+effectivePage,ready=preview?.key===key;
  useEffect(()=>{const el=dialog.current;el.showModal();return()=>{el.close();pending.current?.abort();if(lastUrl.current)URL.revokeObjectURL(lastUrl.current);};},[]);
  function field(name,value){setConfig(old=>({...old,[name]:value}));}
  async function showPreview() {
    pending.current?.abort();const controller=new AbortController();pending.current=controller;setWorking(true);setPreviewError('');
    let url;
    try {
      const next=[...operations.filter(op=>op.type!=='header_footer'),plan];
      const r=await fetch(`/api/documents/${doc.id}/pages/${effectivePage}/preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:next,scale:1.5}),signal:controller.signal});
      if(!r.ok)throw new Error((await r.json()).detail||'No se pudo preparar la vista previa.');
      const blob=await r.blob();if(controller.signal.aborted)return;
      url=URL.createObjectURL(blob);const image=new Image();image.src=url;await image.decode();
      if(controller.signal.aborted){URL.revokeObjectURL(url);return;}
      const old=lastUrl.current;lastUrl.current=url;setPreview({key,url});if(old)URL.revokeObjectURL(old);
    }catch(e){if(url)URL.revokeObjectURL(url);if(e.name!=='AbortError'&&!controller.signal.aborted)setPreviewError(e.message);}
    finally{if(!controller.signal.aborted)setWorking(false);}
  }
  const disabled=busy||working;
  return <dialog ref={dialog} className="organizer headers-dialog" aria-labelledby="headers-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="headers-title">{numbering?'Numerar páginas':'Encabezados y pies'}</h2><button aria-label="Cerrar encabezados y pies" disabled={busy} onClick={onClose}>×</button></div>
    <p>Añade texto en los márgenes. Cada posición dispone de un tercio del ancho útil; revisa la vista previa antes de aplicar.</p>
    <div className="header-slots">{slots.map((key,i)=><label key={key}>{labels[i]}<input aria-label={labels[i]} maxLength="200" value={config.slots[key]} disabled={disabled} onChange={e=>field('slots',{...config.slots,[key]:e.target.value})}/></label>)}</div>
    <div className="header-presets"><button disabled={disabled} onClick={()=>field('slots',{...config.slots,bottom_center:'{numero}'})}>Número en pie central</button><button disabled={disabled} onClick={()=>field('slots',{...config.slots,bottom_center:'Página {numero} de {total}'})}>Página X de Y</button></div>
    <p className="template-help">{'Variables: {pagina} = posición en el PDF; {total} = total del PDF; {numero} = secuencia según el orden del rango.'}</p>
    <div className="header-settings">
      <label>Páginas<input aria-label="Páginas para encabezados" maxLength="2000" value={range} disabled={disabled} onChange={e=>setRange(e.target.value)}/></label>
      <label>Fuente<select aria-label="Fuente de encabezados" value={config.font} disabled={disabled} onChange={e=>field('font',e.target.value)}>{contentFonts.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label>Tamaño (pt)<input aria-label="Tamaño de encabezados" type="number" min="6" max="36" step="any" value={Number.isNaN(config.size)?'':config.size} disabled={disabled} onChange={e=>field('size',e.target.valueAsNumber)}/></label>
      <label>Color<input aria-label="Color de encabezados" type="color" disabled={disabled} value={'#'+config.color.map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join('')} onChange={e=>field('color',[1,3,5].map(i=>parseInt(e.target.value.slice(i,i+2),16)/255))}/></label>
      <label>Inicio de secuencia<input aria-label="Inicio de numeración" type="number" min="1" max="999999" value={Number.isNaN(config.start)?'':config.start} disabled={disabled} onChange={e=>field('start',e.target.valueAsNumber)}/></label>
      <label>Formato<select aria-label="Formato de numeración" value={config.style} disabled={disabled} onChange={e=>field('style',e.target.value)}><option value="D">Decimal</option><option value="R">Romano MAYÚSCULAS</option><option value="r">Romano minúsculas</option></select></label>
      <label>Dígitos mínimos<input aria-label="Dígitos de numeración" type="number" min="0" max="8" value={Number.isNaN(config.padding)?'':config.padding} disabled={disabled||config.style!=='D'} onChange={e=>field('padding',e.target.valueAsNumber)}/></label>
      {['Superior','Derecho','Inferior','Izquierdo'].map((label,i)=><label key={label}>Margen {label.toLowerCase()} (pt)<input aria-label={`Margen de encabezados ${label.toLowerCase()}`} type="number" min="0" max="1000" step="any" value={Number.isNaN(config.margins[i])?'':config.margins[i]} disabled={disabled} onChange={e=>field('margins',config.margins.map((v,j)=>j===i?e.target.valueAsNumber:v))}/></label>)}
    </div>
    <div className="header-preview-controls"><label>Página de muestra<select aria-label="Página de vista previa de encabezados" value={effectivePage} disabled={disabled||!!validation} onChange={e=>setPreviewPage(Number(e.target.value))}>{pages.map(n=><option key={n} value={n}>{n+1}</option>)}</select></label><button disabled={disabled||!!validation} onClick={showPreview}>{working?'Preparando…':'Actualizar vista previa'}</button></div>
    {preview&&<img className="header-preview" src={preview.url} alt="Vista previa de encabezados y pies"/>}
    {ready&&<a className="header-preview-link" href={preview.url} target="_blank" rel="noopener noreferrer">Ampliar vista previa</a>}
    {!ready&&preview&&<p role="status">Cambiaste la configuración. Actualiza la vista previa para poder aplicar.</p>}
    {(error||previewError||validation)&&<p role="alert" className="organizer-error">{error||previewError||validation}</p>}
    <p className="organizer-note">Reemplaza la configuración de esta sesión; no borra texto incorporado al PDF. Ordena e inserta las páginas antes de numerar: al organizar después, estos textos quedan fijos en cada hoja.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button>{existing&&<button disabled={disabled} onClick={()=>onApply(null)}>Quitar configuración de sesión</button>}<button className="primary" disabled={disabled||!!validation||!ready} onClick={()=>onApply(plan)}>Aplicar encabezados y pies</button></div>
  </dialog>;
}
