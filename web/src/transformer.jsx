import React, {useEffect,useRef,useState} from 'react';
import {markBounds,transformMark} from './geometry.js';
import {Shape} from './annotations.jsx';

export function TransformForm({op,page,disabled,onApply,onDraftChange}) {
  const [draft,setDraft]=useState(()=>markBounds(op,page.rotation));
  useEffect(()=>setDraft(markBounds(op,page.rotation)),[op,page]);
  const bounds=markBounds(op,page.rotation);
  const changed=Object.keys(bounds).some(key=>draft[key]!==bounds[key]);
  useEffect(()=>{onDraftChange?.(changed);},[changed,onDraftChange]);
  useEffect(()=>()=>onDraftChange?.(false),[onDraftChange]);
  return <form className="transform-form" onSubmit={e=>{e.preventDefault();onApply(draft);}}>
    <p>Posición y tamaño en puntos PDF. También puedes arrastrar el marco azul y el tirador de su esquina.</p>
    {Object.entries({x:'Posición X',y:'Posición Y',width:'Ancho de marca',height:'Alto de marca'}).map(([key,label])=>
      <label key={key}>{label}<input aria-label={label} type="number" step="any" min="0" required
        value={Number.isNaN(draft[key])?'':draft[key]} disabled={disabled||((key==='width'||key==='height')&&(op.type==='note'||bounds[key]===0))}
        onChange={e=>setDraft({...draft,[key]:e.target.valueAsNumber})}/></label>)}
    <button className="primary" disabled={disabled}>Aplicar posición y tamaño</button>
    <button type="button" disabled={disabled||!changed} onClick={()=>setDraft(markBounds(op,page.rotation))}>Cancelar posición y tamaño</button>
    {op.type==='note'&&<small>El icono de nota conserva su tamaño.</small>}
    {op.quads&&<small>Al mover una marca de texto, sus regiones dejan de coincidir automáticamente con las palabras.</small>}
  </form>;
}

export function TransformHandles({op,page,zoom,onApply,onGesture,labels={move:'Mover marca',mover:'Tirador para mover marca',resize:'Redimensionar marca'},canResize=true}) {
  const [ghost,setGhost]=useState(null), gesture=useRef(null);
  // Cancelar el gesto si se desmonta (cambio de página, herramienta o historial).
  useEffect(()=>()=>{onGesture(false);},[onGesture]);
  const displayed=ghost||op, b=markBounds(displayed,page.rotation), r=5/zoom;
  const coord=e=>{
    const rect=e.currentTarget.ownerSVGElement.getBoundingClientRect();
    return [(e.clientX-rect.left)*page.width/rect.width,(e.clientY-rect.top)*page.height/rect.height];
  };
  function start(e,mode) {
    if(e.button!==0||gesture.current)return;
    e.preventDefault();e.stopPropagation();e.currentTarget.focus();e.currentTarget.setPointerCapture(e.pointerId);
    gesture.current={id:e.pointerId,start:coord(e),mode,original:markBounds(op,page.rotation),last:null,capture:e.currentTarget};onGesture(true);
  }
  function move(e) {
    const g=gesture.current;if(!g||e.pointerId!==g.id)return;
    const p=coord(e), dx=p[0]-g.start[0], dy=p[1]-g.start[1], b=g.original;
    let target=g.mode==='move' ? {...b,x:Math.max(0,Math.min(page.width-b.width-.01,b.x+dx)),y:Math.max(0,Math.min(page.height-b.height-.01,b.y+dy))} :
      {...b,width:b.width===0?0:Math.max(1,Math.min(page.width-b.x-.01,b.width+dx)),height:b.height===0?0:Math.max(1,Math.min(page.height-b.y-.01,b.height+dy))};
    if(g.mode==='resize'&&op.type==='image') {
      const factor=Math.max(1/b.width,1/b.height,Math.min(target.width/b.width,target.height/b.height));
      target={...b,width:b.width*factor,height:b.height*factor};
    }
    try {const next=transformMark(op,target,page);g.last=target;setGhost(next);}catch{/* Conservar la última geometría válida. */}
  }
  function finish(e,cancel=false) {
    const g=gesture.current;if(!g||(e.type!=='keydown'&&e.pointerId!==g.id))return;
    gesture.current=null;setGhost(null);onGesture(false);
    if(g.capture.hasPointerCapture(g.id))g.capture.releasePointerCapture(g.id);
    if(!cancel&&g.last&&JSON.stringify(g.last)!==JSON.stringify(g.original))onApply(g.last);
  }
  const handlers={onPointerMove:move,onPointerUp:e=>finish(e),onPointerCancel:e=>finish(e,true),onLostPointerCapture:e=>finish(e,true),onKeyDown:e=>{
    if(e.key==='Escape'){e.preventDefault();finish(e,true);return;}
    if(!gesture.current&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)) {
      e.preventDefault();e.stopPropagation();
      const step=e.shiftKey?10:1,dx=e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0,dy=e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0;
      const resize=e.target.getAttribute('data-transform-mode')==='resize';
      onApply(resize?{...b,width:b.width===0?0:b.width+dx,height:b.height===0?0:b.height+dy}:{...b,x:b.x+dx,y:b.y+dy});
    }
  }};
  return <g className="transform-handles" {...handlers}>
    {ghost&&<g pointerEvents="none" fill="none" stroke="#2785d2" strokeWidth={2/zoom}>
      {ghost.paths?ghost.paths.map((path,i)=><polyline key={i} points={path.map(p=>p.join(',')).join(' ')}/>):['image','textbox','stamp','link'].includes(ghost.type)?<rect x={b.x} y={b.y} width={b.width} height={b.height}/>:ghost.points?<Shape kind={ghost.type} points={ghost.points}/>:ghost.quads?ghost.quads.map((q,i)=><polygon key={i} points={[q[0],q[1],q[3],q[2]].map(p=>p.join(',')).join(' ')}/>):null}
    </g>}
    <rect x={b.x} y={b.y} width={Math.max(b.width,1)} height={Math.max(b.height,1)} fill="none" stroke="#2785d2" strokeWidth={1.5/zoom} strokeDasharray={`${4/zoom} ${3/zoom}`} pointerEvents="stroke" style={{cursor:'move'}}
      aria-label={labels.move} data-transform-mode="move" role="button" tabIndex="0" onPointerDown={e=>start(e,'move')}/>
    <circle cx={b.x+b.width/2} cy={b.y} r={r} fill="#2785d2" stroke="white" strokeWidth={1/zoom} style={{cursor:'move'}}
      aria-label={labels.mover} data-transform-mode="move" role="button" tabIndex="0" onPointerDown={e=>start(e,'move')}/>
    {op.type!=='note'&&canResize&&<rect x={b.x+b.width-r} y={b.y+b.height-r} width={2*r} height={2*r} fill="white" stroke="#2785d2" strokeWidth={2/zoom} style={{cursor:'nwse-resize'}}
      aria-label={labels.resize} data-transform-mode="resize" role="button" tabIndex="0" onPointerDown={e=>start(e,'resize')}/>}
  </g>;
}
