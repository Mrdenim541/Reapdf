import React,{useEffect,useRef,useState} from 'react';
import {branchEnd,moveBranch,indentBranch,validateBookmarks} from './bookmark-data.js';

export function BookmarkEditor({doc,page,operations,busy,error,onClose,onApply}) {
  const dialog=useRef(null),[items,setItems]=useState([]),[original,setOriginal]=useState([]),[selected,setSelected]=useState(-1);
  const [reading,setReading]=useState(true),[loadError,setLoadError]=useState(''),[editable,setEditable]=useState(false);
  useEffect(()=>{const el=dialog.current;el.showModal();return()=>el.close();},[]);
  useEffect(()=>{
    const controller=new AbortController();
    fetch(`/api/documents/${doc.id}/bookmarks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations}),signal:controller.signal})
      .then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||'No se pudo leer el índice.');return r.json();})
      .then(data=>{if(controller.signal.aborted)return;const rows=data.items.map(item=>({...item,id:crypto.randomUUID()}));setItems(rows);setOriginal(rows);setSelected(rows.length?0:-1);setEditable(data.editable);setLoadError(data.reason);setReading(false);})
      .catch(e=>{if(e.name!=='AbortError'){setLoadError(e.message);setReading(false);}});
    return()=>controller.abort();
  },[doc.id,operations]);
  const current=items[selected],disabled=busy||reading||!editable;
  const changed=JSON.stringify(items)!==JSON.stringify(original),validation=validateBookmarks(items,doc.pages.length);
  function patch(changes){setItems(items.map((item,i)=>i===selected?{...item,...changes}:item));}
  function rearrange(change){setItems(change.items);setSelected(change.index);}
  function add(child=false){
    let position=current?branchEnd(items,selected):items.length;
    if(current&&!child){let root=selected;while(root>0&&items[root].level>1)root--;position=branchEnd(items,root);}
    const item={id:crypto.randomUUID(),level:child?current.level+1:1,title:'Nuevo marcador',page,to:[0,0],zoom:0,color:[0,0,0],bold:false,italic:false,collapse:false};
    setItems([...items.slice(0,position),item,...items.slice(position)]);setSelected(position);
  }
  return <dialog ref={dialog} className="organizer bookmarks-dialog" aria-labelledby="bookmark-title" onCancel={e=>{e.preventDefault();if(!busy)onClose();}}>
    <div className="organizer-heading"><h2 id="bookmark-title">Editar marcadores</h2><button aria-label="Cerrar edición de marcadores" disabled={busy} onClick={onClose}>×</button></div>
    <p>Crea un índice con destinos internos. Los botones de movimiento y nivel actúan sobre la rama completa.</p>
    <div className="bookmark-actions"><button disabled={disabled||items.length>=2000} onClick={()=>add()}>Añadir marcador</button><button disabled={disabled||!current||current.level>=10||items.length>=2000} onClick={()=>add(true)}>Añadir submarcador</button><button disabled={disabled||!current} onClick={()=>{setItems([...items.slice(0,selected),...items.slice(branchEnd(items,selected))]);setSelected(-1);}}>Eliminar rama</button><button disabled={disabled} onClick={()=>{setItems(original);setSelected(original.length?0:-1);}}>Restablecer índice</button></div>
    {reading&&<p role="status">Leyendo índice…</p>}
    <div className="bookmark-workspace"><div className="bookmark-list" aria-label="Lista de marcadores editables">{items.map((item,i)=><button key={item.id} aria-pressed={i===selected} style={{paddingLeft:10+Math.min(item.level-1,10)*12}} disabled={busy||reading} onClick={()=>setSelected(i)}><b>{item.title||'(Sin título)'}</b><small>Nivel {item.level} · Página {item.page+1}</small></button>)}{!items.length&&!reading&&<p>El índice está vacío. Añade el primer marcador.</p>}</div>
      <div className="bookmark-properties">{current&&<>
        <label>Título<input aria-label="Título del marcador" value={current.title} maxLength="300" disabled={disabled} onChange={e=>patch({title:e.target.value})}/></label>
        <label>Página de destino<select aria-label="Página del marcador" value={current.page} disabled={disabled} onChange={e=>patch({page:Number(e.target.value),to:[0,0],zoom:0})}>{doc.pages.map((_,i)=><option key={i} value={i}>{i+1}</option>)}</select></label>
        <div className="bookmark-actions"><button disabled={disabled||moveBranch(items,selected,-1).items===items} onClick={()=>rearrange(moveBranch(items,selected,-1))}>Subir rama</button><button disabled={disabled||moveBranch(items,selected,1).items===items} onClick={()=>rearrange(moveBranch(items,selected,1))}>Bajar rama</button><button disabled={disabled||indentBranch(items,selected,1).items===items} onClick={()=>rearrange(indentBranch(items,selected,1))}>Aumentar nivel</button><button disabled={disabled||current.level===1} onClick={()=>rearrange(indentBranch(items,selected,-1))}>Disminuir nivel</button></div>
        <label className="checkbox-label"><input aria-label="Marcador en negrita" type="checkbox" checked={current.bold} disabled={disabled} onChange={e=>patch({bold:e.target.checked})}/> Negrita</label><label className="checkbox-label"><input aria-label="Marcador en cursiva" type="checkbox" checked={current.italic} disabled={disabled} onChange={e=>patch({italic:e.target.checked})}/> Cursiva</label>
        <label>Color<input aria-label="Color del marcador" type="color" disabled={disabled} value={'#'+current.color.map(c=>Math.round(c*255).toString(16).padStart(2,'0')).join('')} onChange={e=>patch({color:[1,3,5].map(i=>parseInt(e.target.value.slice(i,i+2),16)/255)})}/></label>
      </>}</div>
    </div>
    {(error||loadError||validation)&&<p role="alert" className="organizer-error">{error||loadError||validation}</p>}
    <p className="organizer-note">Cambiar un destino lo lleva al inicio de la página. Renombrar conserva su punto y estilo. Se puede deshacer el índice aplicado; Cancelar descarta lo hecho en este diálogo.</p>
    <div className="organizer-footer"><button disabled={busy} onClick={onClose}>Cancelar</button><button className="primary" disabled={disabled||!changed||!!validation} onClick={()=>onApply({type:'bookmarks',page:0,items:items.map(({id,...item})=>item)})}>Aplicar marcadores</button></div>
  </dialog>;
}
