import React,{useEffect,useState} from 'react';
export const contentTools=new Set(['textbox','stamp','link']);
export const contentFonts=[['helv','Helvetica'],['hebo','Helvetica-Bold'],['heit','Helvetica-Oblique'],['hebi','Helvetica-BoldOblique'],['tiro','Times-Roman'],['tibo','Times-Bold'],['tiit','Times-Italic'],['tibi','Times-BoldItalic'],['cour','Courier'],['cobo','Courier-Bold'],['coit','Courier-Oblique'],['cobi','Courier-BoldOblique']];
const labels={textbox:'Texto nuevo',stamp:'Sello',link:'Enlace'};

export function ContentTargets({operations,page,tool,selected,onSelect}) {
  return operations.filter(op=>op.page===page&&op.type===tool).map((op,i)=>
    <rect key={op.id} x={op.points[0][0]} y={op.points[0][1]} width={op.points[1][0]-op.points[0][0]} height={op.points[1][1]-op.points[0][1]}
      fill="transparent" stroke={selected===op.id?'#2785d2':'#2785d288'} strokeWidth="1" pointerEvents="all" role="button" tabIndex="0" aria-label={`Seleccionar ${labels[tool]} ${i+1}`}
      onPointerDown={e=>e.stopPropagation()} onClick={()=>onSelect(op.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(op.id);}}}/>
  );
}

export function ContentForm({tool,op,doc,geometry,disabled,onApply,onCancel,onDraftChange,onOutline}) {
  const [draft,setDraft]=useState(op);
  useEffect(()=>setDraft(op),[op]);
  useEffect(()=>{onOutline({id:op.id,points:draft.points});},[draft.points,op.id,onOutline]);
  useEffect(()=>()=>onOutline(null),[onOutline]);
  const changed=JSON.stringify(draft)!==JSON.stringify(op);
  useEffect(()=>onDraftChange(changed),[changed,onDraftChange]);
  useEffect(()=>()=>onDraftChange(false),[onDraftChange]);
  const field=(key,value)=>setDraft(previous=>({...previous,[key]:value}));
  const color='#'+(draft.color||[0,0,0]).map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join('');
  return <form className="content-form" onSubmit={e=>{e.preventDefault();onApply(draft);}}>
    {tool==='textbox'?<>
      <label>Texto de la caja<textarea aria-label="Texto de la caja" rows="4" maxLength="2000" required value={draft.text} disabled={disabled} onChange={e=>field('text',e.target.value)}/></label>
      <label>Fuente<select aria-label="Fuente de texto nuevo" value={draft.font} disabled={disabled} onChange={e=>field('font',e.target.value)}>{contentFonts.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      <label>Tamaño (pt)<input aria-label="Tamaño de texto nuevo" type="number" min="6" max="144" step="any" required value={Number.isNaN(draft.size)?'':draft.size} disabled={disabled} onChange={e=>field('size',e.target.valueAsNumber)}/></label>
      <label>Alineación<select aria-label="Alineación de texto nuevo" value={draft.align} disabled={disabled} onChange={e=>field('align',Number(e.target.value))}><option value="0">Izquierda</option><option value="1">Centro</option><option value="2">Derecha</option></select></label>
    </>:tool==='stamp'?<><label>Tipo de sello<select aria-label="Tipo de sello" value={draft.stamp} disabled={disabled} onChange={e=>field('stamp',e.target.value)}><option value="approved">Aprobado / APPROVED</option><option value="draft">Borrador / DRAFT</option><option value="confidential">Confidencial / CONFIDENTIAL</option><option value="not_approved">No aprobado / NOT APPROVED</option></select></label><p>La apariencia estándar muestra el nombre en inglés. No es una firma digital ni una aprobación verificable.</p>{geometry.rotation!==0&&<p>Para añadir un sello, vuelve a 0° en Organizar páginas.</p>}</>:<>
      <label>Destino<select aria-label="Destino del enlace" value={draft.destination} disabled={disabled} onChange={e=>field('destination',e.target.value)}><option value="web">Dirección web</option><option value="page">Página del documento</option></select></label>
      {draft.destination==='web'?<label>Dirección web<input aria-label="Dirección del enlace" type="url" placeholder="https://ejemplo.com" maxLength="2048" required value={draft.url} disabled={disabled} onChange={e=>field('url',e.target.value)}/></label>:<label>Página de destino<select aria-label="Página de destino del enlace" value={draft.target_page} disabled={disabled} onChange={e=>field('target_page',Number(e.target.value))}>{doc.pages.map((_,i)=><option key={i} value={i}>{i+1}</option>)}</select></label>}
      <p>El área será invisible en el PDF. Usa Lectura para seguir el enlace después de aplicarlo.</p>
    </>}
    <fieldset className="box-fields"><legend>Área en puntos PDF</legend>{['x','y','width','height'].map((key,i)=>{
      const b=draft.points,value={x:b[0][0],y:b[0][1],width:b[1][0]-b[0][0],height:b[1][1]-b[0][1]}[key];
      const label=['Posición X','Posición Y','Ancho de caja','Alto de caja'][i];
      return <label key={key}>{label}<input aria-label={label} type="number" step="any" min={i<2?0:5} required disabled={disabled} value={Number.isNaN(value)?'':value} onChange={e=>{
        const v=e.target.valueAsNumber,w=b[1][0]-b[0][0],h=b[1][1]-b[0][1];
        field('points',key==='x'?[[v,b[0][1]],[v+w,b[1][1]]]:key==='y'?[[b[0][0],v],[b[1][0],v+h]]:key==='width'?[b[0],[b[0][0]+v,b[1][1]]]:[b[0],[b[1][0],b[0][1]+v]]);
      }}/></label>;
    })}</fieldset>
    {tool!=='link'&&<label>Color<input aria-label="Color de contenido nuevo" type="color" value={color} disabled={disabled} onChange={e=>field('color',[1,3,5].map(i=>parseInt(e.target.value.slice(i,i+2),16)/255))}/></label>}
    <div className="property-actions"><button className="primary" disabled={disabled||(tool==='stamp'&&geometry.rotation!==0)}>Aplicar {labels[tool].toLowerCase()}</button><button type="button" disabled={disabled} onClick={()=>{setDraft(op);onCancel();}}>Cancelar contenido</button></div>
  </form>;
}

export function LinkLayer({links,zoom,onPage}) {
  return <div className="link-layer">{links.map((link,i)=>{
    const style={left:link.box[0]*zoom,top:link.box[1]*zoom,width:(link.box[2]-link.box[0])*zoom,height:(link.box[3]-link.box[1])*zoom};
    return link.destination==='page'?<a key={i} href={`#pagina-${link.target_page+1}`} style={style} aria-label={`Ir al destino: página ${link.target_page+1}`} title={`Página ${link.target_page+1}`} onClick={e=>{e.preventDefault();onPage(link.target_page);}}/>:
      <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" style={style} aria-label={`Abrir enlace: ${link.url}`} title={link.url}/>;
  })}</div>;
}
