import React,{useEffect,useRef,useState} from 'react';
import {parsePageRange} from './ranges.js';

export function PageCreation({mode,doc,currentPage,busy,error,onClose,onApply}) {
  const dialog=useRef(null),blank=mode==='blank';
  const [range,setRange]=useState(String(currentPage+1)),[position,setPosition]=useState(currentPage+1),[count,setCount]=useState(1);
  const [width,setWidth]=useState(doc.pages[currentPage].width),[height,setHeight]=useState(doc.pages[currentPage].height),[preset,setPreset]=useState('current');
  let pages=[],validation='';
  try {
    if(blank) {
      if(!Number.isInteger(count)||count<1||count+doc.pages.length>500)throw new Error('Indica una cantidad sin superar 500 páginas en total.');
      if(![width,height].every(v=>Number.isFinite(v)&&v>=10&&v<=3000))throw new Error('Ancho y alto deben estar entre 10 y 3000 puntos.');
    } else {
      pages=parsePageRange(range,doc.pages.length);
      if(pages.length+doc.pages.length>500)throw new Error('La duplicación no puede superar 500 páginas en total.');
    }
  }catch(e){validation=e.message;}
  useEffect(()=>{const el=dialog.current;el.showModal();return()=>el.close();},[]);
  function choosePreset(value) {
    setPreset(value);
    const sizes={current:[doc.pages[currentPage].width,doc.pages[currentPage].height],a4:[595.276,841.89],a4land:[841.89,595.276],letter:[612,792],letterland:[792,612]};
    if(sizes[value]){setWidth(sizes[value][0]);setHeight(sizes[value][1]);}
  }
  const title=blank?'Insertar páginas en blanco':'Duplicar páginas';
  return <dialog ref={dialog} className="organizer page-tool-dialog" aria-labelledby="creation-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="creation-title">{title}</h2><button aria-label="Cerrar creación de páginas" disabled={busy} onClick={onClose}>×</button></div>
    <p>{blank?'Añade hojas vacías con el tamaño que necesites.':'Copia las páginas elegidas con sus cambios aplicados. Los campos compatibles se copian como grupos independientes: rellenar la copia no cambia el original. Puedes deshacer la duplicación.'}</p>
    <div className="page-tool-fields">
      {blank?<><label>Cantidad<input aria-label="Cantidad de páginas en blanco" type="number" min="1" max={500-doc.pages.length} value={Number.isNaN(count)?'':count} disabled={busy} onChange={e=>setCount(e.target.valueAsNumber)}/></label>
      <label>Tamaño<select aria-label="Tamaño de página en blanco" value={preset} disabled={busy} onChange={e=>choosePreset(e.target.value)}><option value="current">Igual a la página actual</option><option value="a4">A4 vertical</option><option value="a4land">A4 horizontal</option><option value="letter">Carta vertical</option><option value="letterland">Carta horizontal</option><option value="custom">Personalizado</option></select></label>
      <label>Ancho (pt)<input aria-label="Ancho de página en blanco" type="number" min="10" max="3000" step="any" disabled={busy} value={Number.isNaN(width)?'':width} onChange={e=>{setPreset('custom');setWidth(e.target.valueAsNumber);}}/></label>
      <label>Alto (pt)<input aria-label="Alto de página en blanco" type="number" min="10" max="3000" step="any" disabled={busy} value={Number.isNaN(height)?'':height} onChange={e=>{setPreset('custom');setHeight(e.target.valueAsNumber);}}/></label></>:<label>Páginas para duplicar<input aria-label="Páginas para duplicar" maxLength="2000" disabled={busy} value={range} placeholder="1-3, 5" onChange={e=>setRange(e.target.value)}/></label>}
      <label>Ubicación<select aria-label="Ubicación de páginas nuevas" value={position} disabled={busy} onChange={e=>setPosition(Number(e.target.value))}><option value="0">Al inicio</option>{doc.pages.map((_,i)=><option key={i} value={i+1}>Después de la página {i+1}{i===doc.pages.length-1?' (al final)':''}</option>)}</select></label>
    </div>
    {(validation||error)&&<p className="organizer-error" role="alert">{error||validation}</p>}
    {!validation&&<p role="status">{doc.pages.length+(blank?count:pages.length)} páginas en el resultado.</p>}
    <p className="organizer-note">La operación crea una versión nueva y se puede deshacer. Las marcas e imágenes anteriores quedan incorporadas en el PDF; deshaz la operación para recuperar sus controles de sesión.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy||!!validation} onClick={()=>onApply(blank?{position,count,width,height}:{position,pages})}>{blank?'Insertar hojas en blanco':'Aplicar duplicación'}</button></div>
  </dialog>;
}
