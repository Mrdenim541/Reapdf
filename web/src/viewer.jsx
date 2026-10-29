import React, { useEffect, useMemo, useRef, useState } from 'react';

async function jsonResponse(response) {
  if (!response.ok) {
    let message = 'No se pudo completar la lectura del documento.';
    try { message = (await response.json()).detail || message; } catch { /* Sin JSON */ }
    throw new Error(message);
  }
  return response;
}

export function useDocumentSearch(doc, operations, setPage) {
  const [draft, setDraft] = useState(''), [request, setRequest] = useState(null);
  const [results, setResults] = useState([]), [active, setActive] = useState(0);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [truncated, setTruncated] = useState(false), [navigationKey, setNavigationKey] = useState(0);
  const navigate = useRef(false);
  useEffect(() => {
    setDraft(''); setRequest(null); setResults([]); setActive(0); setError(''); setBusy(false); setTruncated(false);
  }, [doc?.id]);
  useEffect(() => {
    if (!request || request.docId !== doc?.id) return;
    const controller = new AbortController();
    setBusy(true); setResults([]); setError('');
    fetch(`/api/documents/${doc.id}/search`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: request.query, operations}), signal: controller.signal,
    }).then(jsonResponse).then(r => r.json()).then(data => {
      if (controller.signal.aborted) return;
      setResults(data.results); setTruncated(data.truncated); setActive(0); setBusy(false);
      if (navigate.current && data.results.length) {setPage(data.results[0].page); setNavigationKey(key => key + 1);}
      navigate.current = false;
    }).catch(e => {if (e.name !== 'AbortError') {setError(e.message); setBusy(false);}});
    return () => controller.abort();
  }, [doc?.id, operations, request, setPage]);
  function submit(e) {
    e.preventDefault();
    if (!draft.trim()) {setRequest(null); setResults([]); setError(''); setBusy(false); return;}
    navigate.current = true;
    setRequest({query: draft.trim(), docId: doc.id, nonce: Date.now()});
  }
  function go(index) {
    if (!results.length) return;
    const next = (index + results.length) % results.length;
    setActive(next); setPage(results[next].page); setNavigationKey(key => key + 1);
  }
  return {draft, setDraft, submit, results, active, go, busy, error, truncated,
    navigationKey, searched: !!request && request.docId === doc?.id};
}

export function Thumbnail({docId, page, selected, operations, onClick, rotationDelta = 0, disabled = false}) {
  const container = useRef(null), [visible, setVisible] = useState(false);
  const [src, setSrc] = useState(null), [failed, setFailed] = useState(false);
  const relevant = JSON.stringify(operations.filter(op => op.page === page));
  useEffect(() => {
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) setVisible(true);
    });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController(); let url;
    setSrc(null); setFailed(false);
    fetch(`/api/documents/${docId}/pages/${page}/thumbnail`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({operations: JSON.parse(relevant)}), signal: controller.signal,
    }).then(jsonResponse).then(r => r.blob()).then(blob => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob); setSrc(url);
    }).catch(e => {if (e.name !== 'AbortError') setFailed(true);});
    return () => {controller.abort(); if (url) URL.revokeObjectURL(url);};
  }, [visible, docId, page, relevant]);
  return <button ref={container} className="thumbnail" aria-label={`Ir a página ${page + 1}`}
    aria-current={selected ? 'page' : undefined} disabled={disabled} onClick={onClick}>
    <div className="thumbnail-image">{src ? <img src={src} style={{transform:`rotate(${rotationDelta}deg)`}} alt={`Miniatura página ${page + 1}`}/> :
      <span>{failed ? 'Vista no disponible' : '…'}</span>}</div><span>{page + 1}</span>
  </button>;
}

export function DocumentSidebar({doc, page, operations, onPage, search, disabled, searchFocusRequest=0}) {
  const [tab, setTab] = useState('pages');
  const searchInput=useRef(null);
  useEffect(()=>{if(searchFocusRequest>0)setTab('search');},[searchFocusRequest]);
  useEffect(()=>{if(tab==='search'&&searchFocusRequest>0){searchInput.current?.focus();searchInput.current?.select();}},[tab,searchFocusRequest]);
  return <aside id="document-navigation" className="document-sidebar" aria-label="Navegación del documento">
    <div className="sidebar-tabs" role="tablist" aria-label="Panel del documento">
      <button role="tab" aria-selected={tab === 'pages'} onClick={() => setTab('pages')}>Páginas</button>
      <button role="tab" aria-label="Marcadores" aria-selected={tab === 'bookmarks'} onClick={() => setTab('bookmarks')}>Índice</button>
      <button role="tab" aria-selected={tab === 'search'} onClick={() => setTab('search')}>Buscar</button>
    </div>
    {tab === 'pages' ? <div className={`thumbnails ${disabled ? 'interaction-disabled' : ''}`}>
      {doc.pages.map((_, index) => <Thumbnail key={`${doc.id}:${index}`} docId={doc.id} page={index}
        selected={page === index} disabled={disabled} operations={operations} onClick={() => {if (!disabled) onPage(index);}}/>)}
    </div> : tab === 'bookmarks' ? <div className="bookmarks">
      {doc.bookmarks.length ? doc.bookmarks.map((bookmark,index)=><button key={index}
        style={{paddingLeft: 10 + Math.min(bookmark.level - 1, 5) * 10}}
        disabled={disabled || bookmark.page === null} onClick={() => onPage(bookmark.page)}>
        <span>{bookmark.title}</span><small>{bookmark.page === null ? 'Sin destino local' : `Pág. ${bookmark.page + 1}`}</small>
      </button>) : <p>Este PDF no contiene marcadores.</p>}
      {doc.bookmarks_truncated && <p>Mostrando los primeros 2000 marcadores.</p>}
    </div> : <div className="search-panel">
      <form onSubmit={e=>{if(disabled)e.preventDefault();else search.submit(e);}}><label htmlFor="pdf-search">Buscar en el documento</label>
        <input ref={searchInput} id="pdf-search" disabled={disabled} type="search" maxLength="200" value={search.draft}
          onChange={e => search.setDraft(e.target.value)} placeholder="Palabra o frase"/>
        <button className="primary" disabled={disabled || search.busy}>Buscar texto</button>
      </form>
      {search.error && <p role="alert">{search.error}</p>}
      {search.busy ? <p role="status">Buscando…</p> : search.searched && <>
        <p className="search-count" role="status">{search.results.length ? `${search.active + 1} de ${search.results.length}` : 'Sin coincidencias'}{search.truncated ? ' · primeros 500 resultados' : ''}</p>
        {search.results.length > 0 && <div className="search-navigation"><button aria-label="Coincidencia anterior" disabled={disabled} onClick={() => search.go(search.active - 1)}>↑</button><button aria-label="Coincidencia siguiente" disabled={disabled} onClick={() => search.go(search.active + 1)}>↓</button></div>}
        <div className="search-results">{search.results.map((result, index) =>
          <button key={index} aria-pressed={search.active === index} disabled={disabled}
            onClick={() => search.go(index)}><b>Página {result.page + 1}</b><span>{result.text}</span></button>)}</div>
      </>}
      <p className="search-note">Busca en el texto actual del PDF. Los escaneados necesitan OCR.</p>
    </div>}
  </aside>;
}

export function TextLayer({items, zoom, enabled}) {
  const styles = useMemo(() => {
    const context = document.createElement('canvas').getContext('2d');
    return items.map(item => {
      const fontSize = item.size * zoom;
      context.font = `${fontSize}px sans-serif`;
      const measured = context.measureText(item.text).width || 1;
      return {left: item.x * zoom, top: item.y * zoom, fontSize,
        height: item.height * zoom, lineHeight: `${item.height * zoom}px`,
        transform: `rotate(${item.rotation}deg) scaleX(${item.width * zoom / measured})`};
    });
  }, [items, zoom]);
  return <div className={`text-layer ${enabled ? 'enabled' : ''}`} aria-label="Texto seleccionable de la página" aria-hidden={!enabled}>
    {items.map((item, index) => <span key={index} style={styles[index]}>{item.text}</span>)}
  </div>;
}

export function SearchHighlights({search, page}) {
  const activeRect = useRef(null);
  useEffect(() => {
    const frame = requestAnimationFrame(() => activeRect.current?.scrollIntoView({block: 'center', inline: 'nearest'}));
    return () => cancelAnimationFrame(frame);
  }, [search.navigationKey, page]);
  return <g pointerEvents="none">{search.results.map((result, index) => result.page !== page ? null :
    <rect ref={index === search.active ? activeRect : undefined} key={index} data-search-hit={index} x={result.rect[0]} y={result.rect[1]} width={result.rect[2] - result.rect[0]}
      height={result.rect[3] - result.rect[1]} fill={index === search.active ? '#ffa72e' : '#ffe36d'}
      fillOpacity=".35" stroke={index === search.active ? '#db8a13' : 'none'}/>)}</g>;
}
