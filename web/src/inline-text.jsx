import React,{useEffect,useRef,useState} from 'react';
import './inline-text.css';
export function visibleTextBox(span,geometry){
 const [x0,y0,x1,y1]=span.bbox,w=x1-x0,h=y1-y0;
 if(geometry.rotation===90)return [geometry.width-y1,x0,h,w];
 if(geometry.rotation===180)return [geometry.width-x1,geometry.height-y1,w,h];
 if(geometry.rotation===270)return [y0,geometry.height-x1,h,w];
 return [x0,y0,w,h];
}
export function InlineTextEditor({doc,page,operations,span,zoom,busy,onApply,onCancel,error}){
 const input=useRef(null),[value,setValue]=useState(span.text),[row,setRow]=useState(null),[issue,setIssue]=useState(''),[loading,setLoading]=useState(true),[family,setFamily]=useState('original'),[size,setSize]=useState(Math.max(6,Math.min(72,span.size))),[color,setColor]=useState('#'+span.color.toString(16).padStart(6,'0')),[style,setStyle]=useState('regular');
 const g=doc.pages[page],nativeWidth=g.rotation%180?g.height:g.width,nativeHeight=g.rotation%180?g.width:g.height;
 const x=Math.max(0,span.bbox[0]-2),y=Math.max(0,span.bbox[1]-2),box=[x,y,Math.min(nativeWidth-x,Math.max(10,span.bbox[2]-x+2)),Math.min(nativeHeight-y,Math.max(10,span.bbox[3]-y+2))];
 const [vx,vy,vw]=visibleTextBox(span,g),left=vx*zoom,top=vy*zoom;
 useEffect(()=>{
  const c=new AbortController();fetch(`/api/documents/${doc.id}/inspect-styled-text`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,page,box}),signal:c.signal}).then(async r=>{const data=await r.json();if(!r.ok)throw new Error(data.detail);if(c.signal.aborted)return;const rows=data.runs.filter(r=>r.text===span.text&&Math.abs(r.origin[0]-span.origin[0])<.1&&Math.abs(r.origin[1]-span.origin[1])<.1);if(rows.length!==1)throw new Error('El fragmento no se identifica de forma única.');setRow(rows[0]);}).catch(e=>{if(e.name!=='AbortError')setIssue(e.message);}).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
 },[doc.id,page,span.id]);
 useEffect(()=>{if(!loading){input.current?.focus();input.current?.select();}},[loading]);
 const original=family==='original',allowed=!original||row?.editable;
 async function apply(){if(busy||loading||!allowed)return;const ok=await onApply(original?'replace-styled-text':'replace-paragraph',original?{page,box,changes:[{id:row.id,text:value}],expand:false}:{page,box,text:value,family,style,size,color:[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255),align:0,line_height:1,auto_fit:false,min_size:6});if(ok)onCancel();}
 return <section className="inline-text-editor" aria-label="Edición de texto sobre la página" style={{left,top,width:Math.max(80,vw*zoom+6)}} onPointerDown={e=>e.stopPropagation()} onKeyDown={e=>{if(e.key==='Escape'&&!busy){e.preventDefault();e.stopPropagation();onCancel();}else if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();e.stopPropagation();apply();}}}>
 <div className="inline-text-toolbar" style={{left:-Math.min(left,Math.max(0,left+520-g.width*zoom)),top:top<64?Math.max(30,span.size*zoom+8):-58}}>
 <label>Fuente<select aria-label="Fuente de edición directa" value={family} disabled={busy||loading} onChange={e=>setFamily(e.target.value)}><option value="original">Original · {span.font}</option><option value="sans">DejaVu Sans</option><option value="serif">DejaVu Serif</option><option value="mono">DejaVu Sans Mono</option></select></label>
 {!original&&<><label>Estilo<select aria-label="Estilo de edición directa" value={style} disabled={busy} onChange={e=>setStyle(e.target.value)}><option value="regular">Regular</option><option value="bold">Negrita</option><option value="italic">Cursiva</option><option value="bold-italic">Negrita y cursiva</option></select></label><label>pt<input aria-label="Tamaño de edición directa" type="number" min="6" max="72" step=".5" value={size} disabled={busy} onChange={e=>setSize(e.target.valueAsNumber)}/></label><input aria-label="Color de edición directa" type="color" value={color} disabled={busy} onChange={e=>setColor(e.target.value)}/></>}
 <button className="primary" disabled={busy||loading||!allowed||(value===span.text&&original)} onClick={apply}>Aplicar</button><button disabled={busy} onClick={onCancel}>Cancelar</button></div>
 <textarea ref={input} className="inline-text-entry" aria-label="Texto sobre la página" value={value} maxLength="4000" disabled={loading||busy||!allowed} rows="1" style={{fontSize:Math.max(10,(original?span.size:size)*zoom),color,fontFamily:family==='serif'?'serif':family==='mono'?'monospace':'sans-serif',height:Math.max(24,span.size*zoom*1.6)}} onChange={e=>setValue(e.target.value.replace(/[\r\n]/g,''))}/>
 <div className="inline-text-status" role={error||issue?'alert':'status'}>{loading?'Preparando edición…':error||(!allowed?(issue||row?.reason):original?'Ctrl+Enter: aplicar · Esc: cancelar':'Se usará una fuente incluida. Ctrl+Enter: aplicar')}{!loading&&!allowed&&<button onClick={()=>setFamily('sans')}>Usar fuente incluida</button>}</div>
 </section>;
}
