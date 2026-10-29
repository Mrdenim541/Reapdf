import React,{useEffect,useRef,useState} from 'react';
import {parsePageRange} from './ranges.js';
import {imageDimensions} from './image-data.js';

function useDialog(){const dialog=useRef(null);useEffect(()=>{dialog.current.showModal();const el=dialog.current;return()=>el.close();},[]);return dialog;}

export function ImagePdfCreator({busy,error,onClose,onCreate}){
  const dialog=useDialog(),input=useRef(null),[files,setFiles]=useState([]),[paper,setPaper]=useState('A4'),[dpi,setDpi]=useState(150),[margin,setMargin]=useState(18),[issue,setIssue]=useState(''),[reading,setReading]=useState(false);
  async function add(selected){
    setIssue('');setReading(true);
    try{
      const next=[...files,...selected];
      if(next.length>30||next.reduce((n,f)=>n+f.size,0)>20*1024*1024)throw new Error('Hasta 30 imágenes y 20 MB en total.');
      for(const file of selected){
        if(!file.size||file.size>2*1024*1024)throw new Error('Cada imagen debe pesar hasta 2 MB.');
        const {width,height}=imageDimensions(new Uint8Array(await file.arrayBuffer()));
        if(width<=0||height<=0||width*height>24_000_000)throw new Error('Cada imagen admite hasta 24 millones de píxeles.');
      }
      setFiles(next);
    }catch(e){setIssue(e.message);}finally{setReading(false);if(input.current)input.current.value='';}
  }
  function move(i,offset){const next=[...files];[next[i],next[i+offset]]=[next[i+offset],next[i]];setFiles(next);}
  const disabled=busy||reading;
  return <dialog ref={dialog} className="organizer conversion-dialog" aria-labelledby="create-images-title" onCancel={e=>{e.preventDefault();if(!disabled)onClose();}}>
    <div className="organizer-heading"><h2 id="create-images-title">Crear PDF desde imágenes</h2><button aria-label="Cerrar creación desde imágenes" disabled={disabled} onClick={onClose}>×</button></div>
    <p>Cada PNG o JPEG se convierte en una página, en el orden de esta lista. Conserva sus píxeles originales y ajusta su proporción al papel.</p>
    <input ref={input} type="file" accept="image/png,image/jpeg" multiple hidden aria-label="Imágenes para crear PDF" onChange={e=>add(Array.from(e.target.files||[]))}/>
    <button disabled={disabled} onClick={()=>input.current.click()}>{reading?'Leyendo imágenes…':'Añadir imágenes'}</button>
    <ol className="conversion-file-list">{files.map((file,i)=><li key={i}><span>{file.name} <small>({Math.ceil(file.size/1024)} KB)</small></span><button aria-label={`Subir imagen ${i+1}`} disabled={disabled||i===0} onClick={()=>move(i,-1)}>↑</button><button aria-label={`Bajar imagen ${i+1}`} disabled={disabled||i===files.length-1} onClick={()=>move(i,1)}>↓</button><button aria-label={`Quitar imagen ${i+1}`} disabled={disabled} onClick={()=>setFiles(files.filter((_,j)=>j!==i))}>Quitar</button></li>)}</ol>
    <div className="conversion-settings"><label>Papel<select aria-label="Papel del PDF de imágenes" value={paper} disabled={disabled} onChange={e=>setPaper(e.target.value)}><option value="A4">A4</option><option value="Letter">Carta</option><option value="image">Tamaño según imagen y resolución</option></select></label>
      <label>Resolución de tamaño (ppp)<select aria-label="Resolución del PDF de imágenes" value={dpi} disabled={disabled||paper!=='image'} onChange={e=>setDpi(Number(e.target.value))}>{[72,150,300,600].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
      <label>Margen (pt)<input aria-label="Margen del PDF de imágenes" type="number" min="0" max="144" value={Number.isNaN(margin)?'':margin} disabled={disabled} onChange={e=>setMargin(e.target.valueAsNumber)}/></label></div>
    <p className="organizer-note">Hasta 30 imágenes, 2 MB y 24 millones de píxeles por imagen, y 20 MB por lote. La resolución define el tamaño físico cuando se elige Tamaño según imagen; no añade detalle. No se realiza OCR ni corrección automática de orientación o color. Crear abre un documento nuevo.</p>
    {(issue||error)&&<p role="alert" className="organizer-error">{issue||error}</p>}
    <div className="organizer-footer"><button disabled={disabled} onClick={onClose}>Cancelar</button><button className="primary" disabled={disabled||!files.length||!Number.isFinite(margin)||margin<0||margin>144} onClick={()=>onCreate({files,paper,dpi,margin})}>Crear y abrir PDF</button></div>
  </dialog>;
}

export function PageImageExporter({doc,page,busy,error,onClose,onExport}){
  const dialog=useDialog(),[range,setRange]=useState(String(page+1)),[dpi,setDpi]=useState(150),[format,setFormat]=useState('png'),[quality,setQuality]=useState(90);
  let pages=[],issue='';try{pages=parsePageRange(range,doc.pages.length);if(pages.length>50)throw new Error('Exporta hasta 50 páginas por lote.');}catch(e){issue=e.message;}
  return <dialog ref={dialog} className="organizer conversion-dialog" aria-labelledby="export-images-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="export-images-title">Exportar páginas como imágenes</h2><button aria-label="Cerrar exportación de imágenes" disabled={busy} onClick={onClose}>×</button></div>
    <p>Descarga un ZIP con las páginas seleccionadas, incluyendo sus cambios aplicados, marcas y valores de formulario.</p>
    <div className="conversion-settings"><label>Páginas<input aria-label="Páginas para exportar imágenes" value={range} disabled={busy} onChange={e=>setRange(e.target.value)}/></label>
      <label>Formato<select aria-label="Formato de imágenes exportadas" value={format} disabled={busy} onChange={e=>setFormat(e.target.value)}><option value="png">PNG · sin pérdida</option><option value="jpeg">JPEG · fondo blanco</option></select></label>
      <label>Resolución (ppp)<select aria-label="Resolución de imágenes exportadas" value={dpi} disabled={busy} onChange={e=>setDpi(Number(e.target.value))}>{[72,150,300,600].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
      {format==='jpeg'&&<label>Calidad JPEG<input aria-label="Calidad JPEG exportada" type="number" min="50" max="100" value={Number.isNaN(quality)?'':quality} disabled={busy} onChange={e=>setQuality(e.target.valueAsNumber)}/></label>}</div>
    <p className="organizer-note">Se conserva el orden del rango. Hasta 50 páginas, 24 millones de píxeles y 8192 px por lado por imagen; 120 millones de píxeles y 100 MB por lote. Si se supera un límite, reduce páginas o resolución: no se baja la calidad automáticamente. Las imágenes no conservan texto seleccionable, campos editables ni firmas digitales.</p>
    {(issue||error)&&<p role="alert" className="organizer-error">{issue||error}</p>}
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={busy||!!issue||(format==='jpeg'&&(!Number.isInteger(quality)||quality<50||quality>100))} onClick={()=>onExport({pages,dpi,format,quality:format==='jpeg'?quality:90})}>{busy?'Preparando…':'Descargar imágenes en ZIP'}</button></div>
  </dialog>;
}
