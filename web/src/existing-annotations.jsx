import React,{useEffect,useState} from 'react';

export function ExistingTargets({items,selected,onSelect,outlinePath=false,multiSelected=[]}) {
  return items.filter(a=>a.visible).map(a=><rect key={a.xref} x={(a.path_rect||a.rect)[0]-(a.path_rect?5:0)} y={(a.path_rect||a.rect)[1]-(a.path_rect?5:0)}
    width={Math.max(1,(a.path_rect||a.rect)[2]-(a.path_rect||a.rect)[0])+(a.path_rect?10:0)} height={Math.max(1,(a.path_rect||a.rect)[3]-(a.path_rect||a.rect)[1])+(a.path_rect?10:0)}
    fill="transparent" stroke={multiSelected.includes(a.xref)||selected===a.xref&&(!a.path_rect||outlinePath)?'#2785d2':'transparent'} strokeWidth="2" pointerEvents="all"
    role="button" tabIndex="0" aria-label={`Seleccionar anotación existente ${a.label} ${a.xref}`}
    aria-pressed={multiSelected.includes(a.xref)||selected===a.xref} onClick={e=>onSelect(a.xref,e.shiftKey||e.ctrlKey||e.metaKey)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(a.xref,e.shiftKey||e.ctrlKey||e.metaKey);}}}/>);
}
const hex=color=>'#'+color.map(c=>Math.round(Math.max(0,Math.min(1,c))*255).toString(16).padStart(2,'0')).join('');

function ExistingProperties({annotation:a,disabled,onUpdate,onDelete,onDraftChange,endpointMode,onEndpointMode}) {
  const geometry=a.path_rect||a.rect;
  const [color,setColor]=useState(()=>hex(a.color)),[content,setContent]=useState(a.content),[position,setPosition]=useState(geometry.slice(0,2)),[dimensions,setDimensions]=useState([geometry[2]-geometry[0],geometry[3]-geometry[1]]),[ends,setEnds]=useState(a.line_points||[]);
  useEffect(()=>{setEnds(a.line_points||[]);setColor(hex(a.color));setContent(a.content);setPosition(geometry.slice(0,2));setDimensions([geometry[2]-geometry[0],geometry[3]-geometry[1]]);},[a]);
  const endpointChanged=endpointMode&&JSON.stringify(ends)!==JSON.stringify(a.line_points);
  const colorChanged=color!==hex(a.color),contentChanged=content!==a.content,positionChanged=endpointMode?endpointChanged:position.some((v,i)=>v!==geometry[i])||dimensions.some((v,i)=>v!==geometry[i+2]-geometry[i]);
  useEffect(()=>{onDraftChange?.(colorChanged||contentChanged||positionChanged);},[colorChanged,contentChanged,positionChanged,onDraftChange]);
  useEffect(()=>()=>onDraftChange?.(false),[onDraftChange]);
  return <div className="existing-properties"><b>{a.label}</b>
    {a.author&&<p>Autor: {a.author}</p>}
    {a.reason?<p className="empty-hint">{a.reason}</p>:<form onSubmit={e=>{
      e.preventDefault();const changes={};
      if(colorChanged)changes.color=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255);
      if(contentChanged)changes.content=content;
      if(positionChanged){if(endpointMode)changes.line_points=ends;else changes[a.path_rect?'path_rect':'rect']=[...position,position[0]+dimensions[0],position[1]+dimensions[1]];}
      onUpdate(a.xref,changes);
    }}>
      {a.can_edit_endpoints&&<div className="geometry-mode" role="group" aria-label="Modo de ajuste de línea"><button type="button" aria-pressed={!endpointMode} disabled={disabled||colorChanged||positionChanged} onClick={()=>onEndpointMode(false)}>Ajustar caja</button><button type="button" aria-pressed={endpointMode} disabled={disabled||colorChanged||positionChanged} onClick={()=>onEndpointMode(true)}>Editar extremos</button></div>}
      {endpointMode&&<><p>Mueve cada extremo para cambiar dirección y longitud. El extremo inicial es hueco; el final, sólido. Flechas: 1 pt; Mayús: 10 pt. Escape cancela el arrastre.</p><div className="advanced-grid">{ends.map((point,index)=>point.map((value,axis)=><label key={`${index}-${axis}`}>{index?'Final':'Inicio'} {'XY'[axis]} (pt)<input aria-label={`${index?'Final':'Inicio'} ${'XY'[axis]} de línea`} type="number" step="any" value={Number.isNaN(value)?'':value} disabled={disabled} onChange={e=>setEnds(ends.map((p,i)=>i!==index?p:p.map((v,j)=>j===axis?e.target.valueAsNumber:v)))}/></label>))}</div></>}
      <label>Color de marca existente<input type="color" aria-label="Color de marca existente" value={color} disabled={disabled} onChange={e=>setColor(e.target.value)}/></label>
      {a.can_edit_content&&<label>Contenido de nota existente<textarea aria-label="Contenido de nota existente" maxLength="4000" rows="5" value={content} disabled={disabled} onChange={e=>setContent(e.target.value)}/></label>}
      {a.move_reason&&<p className="empty-hint">Movimiento no disponible: {a.move_reason}</p>}
      {a.can_move&&!endpointMode&&<div className="advanced-grid">{['X','Y'].map((label,i)=><label key={i}>Posición {label} (pt)<input aria-label={`Posición ${label} de marca existente`} type="number" step="0.1" value={Number.isNaN(position[i])?'':position[i]} disabled={disabled} onChange={e=>setPosition(position.map((v,n)=>n===i?e.target.valueAsNumber:v))}/></label>)}</div>}
      {a.can_resize&&!endpointMode&&<div className="advanced-grid">{['Ancho','Alto'].map((label,i)=><label key={label}>{label} (pt)<input aria-label={`${label} de marca existente`} type="number" min={a.path_rect?Math.min(1,geometry[i+2]-geometry[i]):10} step="0.1" value={Number.isNaN(dimensions[i])?'':dimensions[i]} disabled={disabled||(a.path_rect&&geometry[i+2]===geometry[i])} onChange={e=>setDimensions(dimensions.map((v,n)=>n===i?e.target.valueAsNumber:v))}/></label>)}</div>}
      <button className="primary" disabled={disabled||(!colorChanged&&!contentChanged&&!positionChanged)||(a.can_edit_content&&contentChanged&&!content.trim())}>Aplicar propiedades existentes</button>
      <button type="button" disabled={disabled||(!colorChanged&&!contentChanged&&!positionChanged)} onClick={()=>{setEnds(a.line_points||[]);setColor(hex(a.color));setContent(a.content);setPosition(geometry.slice(0,2));setDimensions([geometry[2]-geometry[0],geometry[3]-geometry[1]]);}}>Cancelar cambios de marca</button>
      <button type="button" className="delete-mark" disabled={disabled} onClick={()=>onDelete(a.xref)}>Eliminar anotación existente</button>
    </form>}
    {!a.can_edit_content&&a.content&&<p className="existing-content">{a.content}</p>}
    {a.path_rect?<p>La posición y el tamaño corresponden al trazado, sin el grosor ni la punta de flecha. {a.can_resize?'Arrastra el tirador azul para moverlo y la esquina para cambiar su tamaño.':'Esta marca conserva su tamaño; puedes moverla con el tirador azul.'} Las flechas del teclado ajustan 1 pt; Mayús, 10 pt. Escape cancela el arrastre. {a.can_edit_endpoints?'Ajustar caja mantiene los ejes de una línea horizontal o vertical; Editar extremos permite cambiar su dirección.':'El tamaño se ajusta sin cambiar el número de segmentos del trazado.'} Las apariencias personalizadas pueden impedir cambios de forma o color.</p>:<p>Puedes mover notas, rectángulos y elipses compatibles mediante sus coordenadas y redimensionar rectángulos y elipses estándar. Las notas conservan su tamaño.</p>}
  </div>;
}

export function ExistingPanel({items,selected,truncated,disabled,onSelect,onUpdate,onDelete,onDraftChange,endpointMode=false,onEndpointMode}) {
  const annotation=items.find(a=>a.xref===selected);
  return <section className="existing-panel" aria-label="Anotaciones existentes">
    <h3>Marcas del PDF</h3>
    <label>Anotación existente<select aria-label="Anotación existente" value={selected??''} disabled={disabled||!items.length} onChange={e=>onSelect(e.target.value?Number(e.target.value):null)}>
      <option value="">Seleccionar…</option>{items.map((a,index)=><option key={a.xref} value={a.xref}>{index+1}. {a.label}{a.editable?'':' · solo lectura'}{a.visible?'':' · oculta'}</option>)}
    </select></label>
    {!items.length&&<p>No hay anotaciones existentes en esta página.</p>}
    {truncated&&<p>Mostrando las primeras 2000 anotaciones de la página.</p>}
    {annotation&&<ExistingProperties annotation={annotation} disabled={disabled} onUpdate={onUpdate} onDelete={onDelete} onDraftChange={onDraftChange} endpointMode={endpointMode} onEndpointMode={onEndpointMode}/>}
  </section>;
}
