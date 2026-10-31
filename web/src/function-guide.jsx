import React,{useState} from 'react';
import guide from '../../docs/funciones-uso.json';
import {areas} from './tool-catalog.js';
const normal=s=>s.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLocaleLowerCase();
export default function FunctionGuide(){
 const [query,setQuery]=useState(''),[area,setArea]=useState('all'),needle=normal(query.trim());
 const all=[...(guide.general_functions||[]),...guide.functions],entries=all.filter(e=>(area==='all'||e.area===area)&&(!needle||normal([e.label,...e.steps,e.expected,e.limits].join(' ')).includes(needle)));
 return <section className="function-guide" aria-label="Manual por función"><h3>Manual por función</h3><div className="function-guide-filters"><label>Buscar<input type="search" aria-label="Buscar en el manual" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Herramienta o tarea"/></label><label>Área<select aria-label="Área del manual" value={area} onChange={e=>setArea(e.target.value)}><option value="all">Todas las áreas</option>{areas.map(a=><option key={a.id} value={a.id}>{a.label}</option>)}</select></label></div><p role="status">{entries.length} de {all.length} funciones.</p><div className="function-guide-list">{entries.map(e=><details key={e.id} open={entries.length===1}><summary>{e.label} · {areas.find(a=>a.id===e.area)?.label}</summary><article aria-label={`Manual: ${e.label}`}><p><strong>Acceso:</strong> {e.access||`${areas.find(a=>a.id===e.area)?.label} → ${e.label}` }.</p><ol>{e.steps.map((s,i)=><li key={i}>{s}</li>)}</ol><p><strong>Resultado esperado:</strong> {e.expected}</p><p><strong>Compatibilidad:</strong> {e.limits}</p></article></details>)}</div>{!entries.length&&<p>No hay coincidencias. Prueba otro término o selecciona todas las áreas.</p>}</section>;
}
