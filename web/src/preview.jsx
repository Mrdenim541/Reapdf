import {useEffect,useRef,useState} from 'react';

export function usePagePreview(doc,page,operations,zoom,onError) {
  const [density,setDensity]=useState(()=>window.devicePixelRatio||1);
  const [frame,setFrame]=useState(null),[refining,setRefining]=useState(false),[failedKey,setFailedKey]=useState(null),[retry,setRetry]=useState(0);
  const key=JSON.stringify([doc?.id,page,operations]);
  const currentKey=useRef(key);currentKey.current=key;
  const lastUrl=useRef(null);
  useEffect(()=>{
    const update=()=>setDensity(window.devicePixelRatio||1);
    window.addEventListener('resize',update);
    const query=window.matchMedia(`(resolution: ${density}dppx)`);query.addEventListener('change',update);
    return()=>{window.removeEventListener('resize',update);query.removeEventListener('change',update);};
  },[density]);
  const scale=Math.min(16,Math.max(.1,zoom*Math.max(1,density)*1.25));
  useEffect(()=>{
    if(!doc)return;
    const controller=new AbortController();setRefining(true);setFailedKey(null);
    const timer=setTimeout(()=>{
      fetch(`/api/documents/${doc.id}/pages/${page}/preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operations,scale}),signal:controller.signal})
        .then(async response=>{
          if(!response.ok){let detail='No se pudo actualizar la página.';try{detail=(await response.json()).detail||detail;}catch{}throw new Error(detail);}
          return {blob:await response.blob(),limited:response.headers.get('X-Render-Limited')==='true',scale:Number(response.headers.get('X-Render-Scale'))};
        }).then(async({blob,limited,scale:actualScale})=>{
          if(controller.signal.aborted||currentKey.current!==key)return;
          const url=URL.createObjectURL(blob);
          const decoded=new Image();decoded.src=url;
          try{await decoded.decode();}catch(error){URL.revokeObjectURL(url);throw error;}
          if(controller.signal.aborted||currentKey.current!==key){URL.revokeObjectURL(url);return;}
          const previous=lastUrl.current;lastUrl.current=url;
          setFrame({key,url,limited,scale:actualScale});setRefining(false);
          if(previous)URL.revokeObjectURL(previous);
        }).catch(error=>{if(!controller.signal.aborted&&error.name!=='AbortError'){setRefining(false);setFailedKey(key);onError(error.message);}});
    },120);
    return()=>{clearTimeout(timer);controller.abort();};
  },[key,scale,onError,retry]);
  useEffect(()=>()=>{if(lastUrl.current)URL.revokeObjectURL(lastUrl.current);},[]);
  const active=frame?.key===key?frame:null;
  return {src:active?.url||null,loading:!!doc&&!active&&failedKey!==key,refining,failed:failedKey===key,retry:()=>setRetry(n=>n+1),limited:active?.limited||false,scale:active?.scale||0};
}
