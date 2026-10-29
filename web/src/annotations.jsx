import React from 'react';

export const drawingTools = new Set(['ink', 'line', 'arrow', 'rectangle']);
export const markupTools = new Set(['highlight', 'underline', 'strikeout']);
export const toolNames = {textbox:'Añadir texto',stamp:'Sellos',link:'Enlaces',ink: 'Lápiz', line: 'Línea', arrow: 'Flecha', rectangle: 'Rectángulo', highlight: 'Resaltar', underline: 'Subrayar', strikeout: 'Tachar', note: 'Nota'};

export function Shape({kind, points, ...props}) {
  if (kind === 'rectangle') {
    const [a, b] = points;
    if (!b) return null;
    return <rect x={Math.min(a[0], b[0])} y={Math.min(a[1], b[1])}
      width={Math.abs(a[0] - b[0])} height={Math.abs(a[1] - b[1])} {...props}/>;
  }
  return <polyline points={points.map(p => p.join(',')).join(' ')} {...props}/>;
}

export function MarkTargets({operations, page, selectedId, onSelect, onDelete}) {
  return operations.filter(op => op.page === page && drawingTools.has(op.type)).map(op => (
    <Shape key={op.id} kind={op.type} points={op.points} fill="none"
      stroke={selectedId === op.id ? '#338bff' : 'transparent'}
      strokeWidth={Math.max(op.width + 8, 10)} strokeOpacity=".45" pointerEvents="stroke"
      role="button" tabIndex="0" aria-label={`Seleccionar ${toolNames[op.type]} ${op.id}`}
      onClick={() => onSelect(op.id)} onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(op.id); }
        if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); onDelete(op.id); }
      }}/>
  ));
}

export function ReviewTargets({operations, page, selectedId, onSelect, onDelete}) {
  return operations.filter(op => op.page === page && (markupTools.has(op.type) || op.type === 'note')).map(op => {
    const regions = op.type === 'note' ? [[[op.point[0]-20,op.point[1]-20],[op.point[0]+20,op.point[1]+20]]] : op.quads;
    return <g key={op.id} role="button" tabIndex="0" aria-label={`Seleccionar ${toolNames[op.type]} ${op.id}`}
      onClick={()=>onSelect(op.id)} onKeyDown={e=>{
        if(e.key==='Enter'||e.key===' ') {e.preventDefault();onSelect(op.id);}
        if(e.key==='Delete'||e.key==='Backspace') {e.preventDefault();onDelete(op.id);}
      }}>{regions.map((q,index)=>{
        const xs=q.map(p=>p[0]), ys=q.map(p=>p[1]);
        return <rect key={index} x={Math.min(...xs)} y={Math.min(...ys)} width={Math.max(...xs)-Math.min(...xs)} height={Math.max(...ys)-Math.min(...ys)}
          fill="transparent" stroke={selectedId===op.id?'#338bff':'transparent'} strokeWidth="2" pointerEvents="all"/>;
      })}</g>;
  });
}

export function NoteForm({value,onChange,onSubmit,disabled}) {
  return <form onSubmit={onSubmit}><label>Contenido de la nota<textarea aria-label="Contenido de la nota" value={value}
    onChange={e=>onChange(e.target.value)} maxLength="4000" rows="5"/></label>
    <button className="primary" disabled={disabled || !value.trim()}>Guardar nota</button></form>;
}
