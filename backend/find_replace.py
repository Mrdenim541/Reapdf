"""Literal search with snapshot-bound, atomic replacement of compatible runs."""
import hashlib,json,re
from collections import defaultdict
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .styled_text import inspect_styled,replace_styled

def digest(value):return hashlib.sha256(value).hexdigest()

def inspect(base,ops,query):
    if not isinstance(query,dict) or set(query)!={'text','pages','case_sensitive','whole_word'}:raise DocumentError('Consulta de búsqueda no válida.')
    text=query['text'];pages=query['pages']
    if not isinstance(text,str) or not 1<=len(text)<=200 or any(ord(c)<32 for c in text):raise DocumentError('Busca entre 1 y 200 caracteres, sin saltos de línea.')
    if any(type(query[k]) is not bool for k in ['case_sensitive','whole_word']):raise DocumentError('Opciones de búsqueda no válidas.')
    if not isinstance(pages,list) or not pages or len(pages)>500 or any(type(n) is not int for n in pages) or len(set(pages))!=len(pages):raise DocumentError('Selecciona páginas distintas.')
    snapshot=export_pdf(base,ops)
    receipt=digest(base+json.dumps({'query':query,'operations':ops},sort_keys=True,ensure_ascii=True).encode())
    pattern=re.escape(text)
    if query['whole_word']:pattern=r'(?<!\w)'+pattern+r'(?!\w)'
    regex=re.compile(pattern,0 if query['case_sensitive'] else re.IGNORECASE)
    matches=[];empty=[];characters=0
    with open_pdf(snapshot) as doc:
        if any(not 0<=n<len(doc) for n in pages):raise DocumentError('Página inexistente.')
        for number in pages:
            page=doc[number];page.set_rotation(0);found=False
            for block in page.get_text('dict',flags=f.TEXTFLAGS_TEXT|f.TEXT_INHIBIT_SPACES,sort=True)['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        original=span['text'];characters+=len(original);found|=bool(original.strip())
                        if characters>2_000_000:raise DocumentError('Demasiado texto; reduce las páginas de búsqueda.')
                        hits=list(regex.finditer(original))
                        if not hits:continue
                        if len(matches)+len(hits)>500:raise DocumentError('Más de 500 coincidencias; limita la búsqueda.')
                        bbox=f.Rect(span['bbox']);rect=(bbox+(-.1,-.1,.1,.1))&page.rect
                        box=[rect.x0,rect.y0,rect.width,rect.height]
                        reason='';run=None
                        try:
                            rows=inspect_styled(snapshot,[],number,box)['runs']
                            candidates=[r for r in rows if r['text']==original and r['font']==span['font'] and abs(r['origin'][0]-span['origin'][0])<.01 and abs(r['origin'][1]-span['origin'][1])<.01]
                            if len(candidates)!=1:raise DocumentError('Fragmento ambiguo.')
                            run=candidates[0]
                            if not run['editable']:reason=run['reason']
                        except DocumentError as exc:reason=str(exc)
                        for hit in hits:
                            identity=f'{number}:{span["origin"]}:{original}:{hit.start()}:{hit.end()}'
                            matches.append({'id':digest((receipt+identity).encode())[:24],'page':number,'text':hit[0],'context':original,'start':hit.start(),'end':hit.end(),'box':box,'origin':list(span['origin']),'font':span['font'],'editable':not reason,'reason':reason})
            if not found:empty.append(number)
    return {'receipt':receipt,'matches':matches,'empty_pages':empty,'scope':'Coincidencias dentro de un fragmento de texto digital; no cruza fragmentos ni reconoce escaneados.'}

def plan_token(receipt,selected,replacement):
    return digest(json.dumps([receipt,sorted(selected),replacement],ensure_ascii=True).encode())

def replace(base,ops,query,receipt,selected,replacement):
    if not isinstance(selected,list) or not 1<=len(selected)<=100 or any(not isinstance(i,str) for i in selected) or len(set(selected))!=len(selected):raise DocumentError('Selecciona hasta 100 coincidencias distintas.')
    if not isinstance(replacement,str) or len(replacement)>1000 or any(ord(c)<32 or ord(c)==127 for c in replacement):raise DocumentError('Reemplazo de hasta 1000 caracteres, sin controles.')
    inspection=inspect(base,ops,query)
    if receipt!=inspection['receipt']:raise DocumentError('El documento o la búsqueda cambió. Vuelve a buscar.')
    model={m['id']:m for m in inspection['matches']};groups=defaultdict(list)
    for identity in selected:
        if identity not in model:raise DocumentError('Coincidencia inexistente.')
        m=model[identity]
        if not m['editable']:raise DocumentError(m['reason'])
        groups[(m['page'],tuple(m['origin']),m['context'],m['font'])].append(m)
    if len(groups)>20:raise DocumentError('Hasta 20 fragmentos distintos por operación. Divide la selección.')
    result=export_pdf(base,ops);changes=0
    for (page,origin,original,font),hits in groups.items():
        value=original
        for hit in sorted(hits,key=lambda h:h['start'],reverse=True):value=value[:hit['start']]+replacement+value[hit['end']:]
        if value==original:continue
        box=hits[0]['box'];rows=inspect_styled(result,[],page,box)['runs']
        candidates=[r for r in rows if r['text']==original and r['font']==font and all(abs(a-b)<.01 for a,b in zip(r['origin'],origin))]
        if len(candidates)!=1:raise DocumentError('El fragmento cambió o es ambiguo. No se aplica un reemplazo parcial.')
        try:result=replace_styled(result,[],page,box,[{'id':candidates[0]['id'],'text':value}])
        except DocumentError as exc:raise DocumentError(f'Página {page+1}, «{original[:80]}»: {exc} No se aplicó ningún cambio.') from exc
        changes+=len(hits)
    if not changes:raise DocumentError('El reemplazo no produce cambios.')
    return result,plan_token(receipt,selected,replacement),changes
