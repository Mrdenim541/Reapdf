import React,{useEffect,useRef,useState} from 'react';

export function FormEditor({doc,operations,busy,error,onClose,onApply,onAction}) {
  const dialog=useRef(null),pending=useRef(null),lastUrl=useRef(null);
  const [fields,setFields]=useState([]),[initial,setInitial]=useState(''),[selected,setSelected]=useState(0);
  const initialRecalculate=useRef(operations.some(op=>op.type==='form_recalculate'));
  const [recalculate,setRecalculate]=useState(initialRecalculate.current),[nativeInfo,setNativeInfo]=useState(null);
  const [reading,setReading]=useState(true),[working,setWorking]=useState(false),[issue,setIssue]=useState(''),[preview,setPreview]=useState(null);
  useEffect(()=>{const el=dialog.current;el.showModal();return()=>{el.close();pending.current?.abort();if(lastUrl.current)URL.revokeObjectURL(lastUrl.current);};},[]);
  useEffect(()=>{
    const controller=new AbortController();
    fetch(`/api/documents/${doc.id}/forms`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations}),signal:controller.signal})
      .then(async r=>{if(!r.ok)throw new Error((await r.json()).detail);return r.json();})
      .then(data=>{if(controller.signal.aborted)return;setFields(data.fields);setNativeInfo({rules:data.native_calculations||[],error:data.native_calculation_error,orderIssue:data.native_order_issue});setInitial(JSON.stringify(data.fields.map(f=>f.value)));setReading(false);})
      .catch(e=>{if(e.name!=='AbortError'){setIssue(e.message);setReading(false);}});
    return()=>controller.abort();
  },[doc.id,operations]);
  const field=fields[selected],changed=JSON.stringify(fields.map(f=>f.value))!==initial||recalculate!==initialRecalculate.current;
  const values=fields.filter(f=>f.editable&&JSON.stringify(f.value)!==JSON.stringify(f.base_value)).map(f=>({page:f.page,xref:f.xref,value:f.value}));
  const plan=values.length?{type:'form_fill',page:0,values}:recalculate?{type:'form_recalculate',page:0}:null;
  const next=[...operations.filter(op=>!['form_fill','form_recalculate'].includes(op.type)),...(plan?[plan]:[])];
  const key=JSON.stringify(next)+':'+field?.page,ready=preview?.key===key;
  const disabled=busy||working||reading;
  const missing=fields.filter((f,i)=>f.required&&(!f.value||typeof f.value==='string'&&!f.value.trim())&&fields.findIndex(v=>v.group===f.group)===i);
  useEffect(()=>{if(reading||!fields.length||busy)return;const timer=setTimeout(showPreview,450);return()=>clearTimeout(timer);},[key,reading,fields.length,busy]);
  function change(value){setFields(fields.map(f=>f.group===field.group?{...f,value}:f));}
  function changeRadio(option){change(option.value);const index=fields.findIndex(f=>f.group===field.group&&f.radio_state===option.value);if(index>=0)setSelected(index);}
  async function showPreview(){
    pending.current?.abort();const controller=new AbortController();pending.current=controller;setWorking(true);setIssue('');let url;
    try{
      const response=await fetch(`/api/documents/${doc.id}/pages/${field.page}/preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:next,scale:1.5}),signal:controller.signal});
      if(!response.ok)throw new Error((await response.json()).detail||'No se pudo mostrar el formulario.');
      const blob=await response.blob();if(controller.signal.aborted)return;
      url=URL.createObjectURL(blob);const image=new Image();image.src=url;await image.decode();
      if(controller.signal.aborted){URL.revokeObjectURL(url);return;}
      const modelResponse=await fetch(`/api/documents/${doc.id}/forms`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations:next}),signal:controller.signal});
      if(!modelResponse.ok)throw new Error((await modelResponse.json()).detail);
      const model=await modelResponse.json();if(controller.signal.aborted){URL.revokeObjectURL(url);return;}
      setFields(previous=>previous.map(f=>{const row=model.fields.find(row=>row.page===f.page&&row.xref===f.xref);return row?{...f,display_value:row.display_value,format_issue:row.format_issue,...(f.calculated?{value:row.value}:{})}:f;}));
      const old=lastUrl.current;lastUrl.current=url;setPreview({key,url,page:field.page});if(old)URL.revokeObjectURL(old);
    }catch(e){if(url)URL.revokeObjectURL(url);if(e.name!=='AbortError'&&!controller.signal.aborted)setIssue(e.message);}
    finally{if(!controller.signal.aborted)setWorking(false);}
  }
  return <dialog ref={dialog} className="organizer form-dialog" aria-labelledby="form-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="form-title">Rellenar formulario</h2><button aria-label="Cerrar formulario" disabled={busy} onClick={onClose}>×</button></div>
    <p>Selecciona un campo en la página o en la lista. La vista previa se actualiza al escribir. Los cambios se guardan como campos PDF editables.</p>
    {reading&&<p role="status">Leyendo campos…</p>}
    {!reading&&!fields.length&&!issue&&<p>Este documento no contiene campos de formulario. El texto impreso de una plantilla no es un campo; puedes usar Añadir texto.</p>}
    {nativeInfo?.error&&<p role="status">{nativeInfo.error}</p>}
    {nativeInfo?.orderIssue&&<button disabled={disabled||!doc.can_edit} onClick={()=>onAction('repair-calculation-order',{})}>Corregir orden de cálculo del PDF</button>}
    {!!nativeInfo?.rules.length&&<div className="form-native-calculations"><p>Este PDF contiene {nativeInfo.rules.length} cálculos estándar. Se actualizan al modificar sus fuentes y se conservan en el PDF exportado.</p><button disabled={disabled} onClick={()=>setRecalculate(true)}>Actualizar cálculos del PDF</button></div>}
    {!!missing.length&&<details className="form-required-review"><summary>Faltan {missing.length} campos obligatorios · puedes guardar un borrador</summary>{missing.map(f=><button key={f.group} disabled={disabled} onClick={()=>setSelected(fields.indexOf(f))}>{f.label} · página {f.page+1}</button>)}</details>}
    {!!fields.length&&<>
      <label>Campo<select aria-label="Campo del formulario" disabled={disabled} value={selected} onChange={e=>setSelected(Number(e.target.value))}>{fields.map((f,i)=><option key={`${f.page}:${f.xref}`} value={i}>{f.label||`Campo ${i+1}`} · Página {f.page+1}{f.editable?'':' · Solo lectura'}</option>)}</select></label>
      <p className="form-field-info">Página {field.page+1} · {field.name} · {field.kind==='text'?'Texto':field.kind==='checkbox'?'Casilla':field.kind==='choice'?'Lista':field.kind==='radio'?'Grupo de radio':'Tipo no compatible'}</p>
      {field.required&&<p>Campo obligatorio.</p>}
      {field.format&&<p role="status">{field.format.kind==='date'?`Fecha: ${field.format.pattern}`:field.format.kind==='percent'?`Porcentaje: introduce una fracción (${'separator' in field.format&&[2,3].includes(field.format.separator)?'0,125 equivale a 12,5':'0.125 equivale a 12.5'} %).`:`Número: separador decimal ${[2,3].includes(field.format.separator)?'coma':'punto'}.`}{field.format.minimum!=null?` Mínimo ${field.format.minimum}.`:''}{field.format.maximum!=null?` Máximo ${field.format.maximum}.`:''} {field.display_value&&<>Se mostrará: <strong>{field.display_value}</strong></>}</p>}
      {field.format_issue&&<p role="status">{field.format_issue} Puedes corregir este valor.</p>}
      {field.group_size>1&&<p role="status">Campo compartido en {field.group_size} posiciones. Cambiarlo sincroniza todas sus apariencias.</p>}
      {field.calculated&&<p role="status">{field.native_calculated?'Resultado nativo del PDF:':'Resultado calculado:'} <strong>{field.value}</strong>. Cambia sus fuentes y compara para actualizar.</p>}
      {!field.editable?<p role="status">{field.reason}</p>:field.kind==='checkbox'?<label className="form-check"><input aria-label="Casilla del formulario" type="checkbox" checked={field.value} disabled={disabled} onChange={e=>change(e.target.checked)}/> Activada</label>:
        field.kind==='radio'?<fieldset className="radio-options"><legend>Opción del grupo</legend>{[{value:'',label:'Sin selección'},...field.choices].map(c=><label className="form-check" key={c.value}><input type="radio" name="form-radio-value" aria-label={`Opción de radio: ${c.label}`} checked={field.value===c.value} disabled={disabled||(!c.value&&!field.can_clear&&!!field.base_value)} onChange={()=>changeRadio(c)}/>{c.label}{c.page!==undefined?` · Página ${c.page+1}`:''}</label>)}</fieldset>:field.kind==='choice'?<label>Valor<select aria-label="Valor del formulario" value={field.value} disabled={disabled} onChange={e=>change(e.target.value)}><option value="">Sin selección</option>{field.choices.filter(c=>c.value!=='').map(c=><option key={c.value} value={c.value}>{c.label}</option>)}</select></label>:
        <label>{field.multiline?'Texto de varias líneas':'Texto'}<textarea aria-label="Valor del formulario" rows={field.multiline?5:2} maxLength={field.max_length} value={field.value} disabled={disabled} onChange={e=>change(e.target.value)}/><small>Hasta {field.max_length} caracteres latinos. {field.multiline?'Se admiten saltos de línea.':'Una sola línea.'}</small></label>}
      <button disabled={disabled} onClick={showPreview}>{working?'Preparando…':'Vista previa del formulario'}</button>
      {preview&&preview.page===field.page&&<div className="form-page-preview field-placement"><img className="header-preview" src={preview.url} alt="Vista previa del formulario"/><svg aria-label="Campos sobre la página" viewBox={`0 0 ${doc.pages[field.page].width} ${doc.pages[field.page].height}`}>{fields.map((f,i)=>f.page===field.page&&<rect key={`${f.page}:${f.xref}`} role="button" tabIndex="0" aria-label={`Seleccionar campo: ${f.label}`} x={f.rect[0]} y={f.rect[1]} width={f.rect[2]-f.rect[0]} height={f.rect[3]-f.rect[1]} fill={i===selected?'#16765c22':'transparent'} stroke={i===selected?'#16765c':'#62777e'} onClick={()=>{if(!disabled)setSelected(i);}} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSelected(i);}}}/>)}</svg></div>}
      {ready&&<a className="header-preview-link" href={preview.url} target="_blank" rel="noopener noreferrer">Ampliar formulario</a>}
      {!ready&&preview&&<p role="status">Actualiza la vista previa con los valores actuales antes de aplicar.</p>}
    </>}
    {(error||issue)&&<p role="alert" className="organizer-error">{error||issue}</p>}
    <p className="organizer-note">Se admiten texto, casillas, listas y radios estándar, además de campos compartidos y jerarquías compatibles. Los formatos estándar compatibles se conservan. Scripts y cálculos no reconocidos, y estructuras especiales quedan protegidos. Cancelar descarta los valores de este diálogo.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={disabled||!changed||!ready} onClick={()=>onApply(plan)}>Aplicar formulario</button></div>
  </dialog>;
}
