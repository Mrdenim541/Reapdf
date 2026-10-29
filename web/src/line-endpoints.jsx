import React,{useEffect,useRef,useState} from 'react';
export function LineEndpoints({points,page,zoom,onApply,onGesture}){
 const gesture=useRef(null),[ghost,setGhost]=useState(null),display=ghost||points,r=6/zoom;
 useEffect(()=>()=>onGesture(false),[onGesture]);
 function coord(e){const b=e.currentTarget.ownerSVGElement.getBoundingClientRect();return [Math.max(0,Math.min(page.width,(e.clientX-b.left)/b.width*page.width)),Math.max(0,Math.min(page.height,(e.clientY-b.top)/b.height*page.height))];}
 function finish(e,cancel=false){const g=gesture.current;if(!g||(e.type!=='keydown'&&e.pointerId!==g.id))return;gesture.current=null;setGhost(null);onGesture(false);if(g.capture.hasPointerCapture(g.id))g.capture.releasePointerCapture(g.id);if(!cancel&&g.last&&JSON.stringify(g.last)!==JSON.stringify(points))onApply(g.last);}
 return <g className="line-endpoint-handles" onPointerMove={e=>{const g=gesture.current;if(!g||g.id!==e.pointerId)return;const p=coord(e),next=points.map((v,i)=>i===g.index?p:v);if(Math.hypot(next[1][0]-next[0][0],next[1][1]-next[0][1])<1)return;g.last=next;setGhost(next);}} onPointerUp={e=>finish(e)} onPointerCancel={e=>finish(e,true)} onLostPointerCapture={e=>finish(e,true)} onKeyDown={e=>{
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();finish(e,true);return;}
  if(!gesture.current&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopPropagation();const index=Number(e.target.dataset.endpoint),step=e.shiftKey?10:1;onApply(points.map((v,i)=>i!==index?v:[v[0]+(e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0),v[1]+(e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0)]));}
 }}>
 <polyline points={display.map(p=>p.join(',')).join(' ')} fill="none" stroke="#2785d2" strokeWidth={1.5/zoom} strokeDasharray={`${4/zoom} ${3/zoom}`} pointerEvents="none"/>
 {display.map((p,index)=><circle key={index} cx={p[0]} cy={p[1]} r={r} fill={index?'#2785d2':'white'} stroke="#2785d2" strokeWidth={2/zoom} style={{cursor:'crosshair'}} role="button" tabIndex="0" aria-label={index?'Mover extremo final de línea':'Mover extremo inicial de línea'} data-endpoint={index} onPointerDown={e=>{if(e.button!==0||gesture.current)return;e.preventDefault();e.stopPropagation();e.currentTarget.focus();e.currentTarget.setPointerCapture(e.pointerId);gesture.current={id:e.pointerId,index,capture:e.currentTarget,last:null};onGesture(true);}}/>)}
 </g>;
}
