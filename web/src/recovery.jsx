import {useCallback,useEffect,useRef,useState} from 'react';

export function projectPayload(doc,operations,page,zoom) {
  return {operations,name:doc.name.slice(0,200),page,zoom,base_changes:doc.baseChanges||0};
}

async function result(response) {
  if(!response.ok){let detail='No se pudo guardar la recuperación local.';try{detail=(await response.json()).detail||detail;}catch{}throw new Error(detail);}
  return response.json();
}

export function useRecovery(doc,operations,page,zoom) {
  const [info,setInfo]=useState(null),[ready,setReady]=useState(false),[error,setError]=useState('');
  const [saving,setSaving]=useState(false),[savedKey,setSavedKey]=useState('');
  const infoRef=useRef(null),initial=useRef(null);
  const revision=useRef(null),queue=useRef(Promise.resolve()),mounted=useRef(true);
  const key=JSON.stringify([doc?.id,operations]);
  const latest=useRef(null);latest.current={doc,operations,page,zoom,key};
  const refresh=useCallback(async()=>{
    try {
      const next=await result(await fetch('/api/recovery',{cache:'no-store'}));
      if(!mounted.current)return;
      revision.current=next.revision;infoRef.current=next;setInfo(next);setError(next.error||'');setReady(!next.error);return next;
    }catch(e){if(mounted.current){setError(e.message);setReady(false);}return {available:false,error:e.message};}
  },[]);
  useEffect(()=>{mounted.current=true;initial.current=refresh();return()=>{mounted.current=false;};},[refresh]);
  const saveNow=useCallback(()=>{
    const requested=latest.current;
    if(!ready||!requested.doc)return Promise.resolve();
    queue.current=queue.current.catch(()=>{}).then(async()=>{
      // Serializar escrituras impide que una respuesta vieja reemplace el documento nuevo.
      if(latest.current.key!==requested.key||!mounted.current)return;
      setSaving(true);
      try {
        const payload={...projectPayload(requested.doc,requested.operations,requested.page,requested.zoom),revision:revision.current};
        const next=await result(await fetch(`/api/documents/${requested.doc.id}/recovery`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}));
        revision.current=next.revision;
        if(mounted.current){setSavedKey(requested.key);setError('');infoRef.current={available:true,...next,state:{name:payload.name}};setInfo(infoRef.current);}
      }catch(e){if(mounted.current&&latest.current.key===requested.key){setError(e.message);setReady(false);}}
      finally{if(mounted.current)setSaving(false);}
    });
    return queue.current;
  },[ready]);
  useEffect(()=>{
    if(!doc||!ready)return;
    const timer=setTimeout(saveNow,1000);
    return()=>clearTimeout(timer);
  },[key,ready,saveNow]);
  async function discard() {
    await queue.current;
    const next=await result(await fetch('/api/recovery',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:revision.current})}));
    revision.current=null;infoRef.current=next;setInfo(next);setError('');setReady(true);setSavedKey('');
  }
  return {info,ready,error,saving,initialInfo:async()=>infoRef.current||await(initial.current||(initial.current=refresh())),revision:()=>revision.current,refresh,discard,saveNow,
    status:error?'Recuperación automática no disponible':saving?'Guardando recuperación local…':savedKey===key?'Recuperación local actualizada':'Cambios pendientes de recuperación'};
}
