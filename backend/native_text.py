"""Byte-preserving edits of bounded, consecutive original text groups.

Supports verified base fonts, TrueType/CFF subsets and isolated Form invocations. Marked-content and clip
operators are untouched. No redaction, resource replacement or tag rewriting.
"""
import math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import placements


def trace_index(traces):
    index={}
    for t,trace in enumerate(traces):
        for at,char in enumerate(trace['chars']):
            x,y=char[2]
            if math.isfinite(x) and math.isfinite(y):index.setdefault((char[0],math.floor(x*50),math.floor(y*50)),[]).append((t,at))
    return index


def matching_traces(traces,text,origin,index=None):
    result=[]
    if not text:return result
    if index is not None:
        x,y=origin;candidates=[]
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:candidates.extend(index.get((ord(text[0]),math.floor(x*50)+dx,math.floor(y*50)+dy),[]))
        for t,at in candidates:
            trace=traces[t];sample=trace['chars'][at:at+len(text)]
            if math.dist(trace['chars'][at][2],origin)<.02 and ''.join(chr(c[0]) for c in sample)==text:result.append({**trace,'chars':sample})
        return result
    for trace in traces:
        chars=trace['chars']
        for at,char in enumerate(chars):
            if char[0]!=ord(text[0]) or math.dist(char[2],origin)>=.02:continue
            sample=chars[at:at+len(text)]
            if ''.join(chr(c[0]) for c in sample)==text:result.append({**trace,'chars':sample})
    return result


def native_model(doc,number,rect,font_cache=None,*,context=False):
    from .styled_text import OriginalFont,normal_name
    page=doc[number]
    if doc.get_ocgs():raise DocumentError('El texto asociado a capas todavía requiere otra edición.')
    content=page.read_contents();cache={} if font_cache is None else font_cache
    from .pdf_content import names
    if '_structure' not in cache:
        from .form_text import structure
        cache['_structure']=(structure(doc,page),page.get_fonts(full=True),page.get_texttrace())
    objects,fonts,traces=cache['_structure']
    if '_semantic_text' not in cache:
        from .semantic_text import Index
        cache['_semantic_text']=Index(doc,number,objects)
    if type(context) is not bool:raise DocumentError('Modo de inspección de texto no válido.')
    if '_obstacles' not in cache:
        from .affine_text import obstacles
        cache['_obstacles']=obstacles(page)
    if len(fonts)>20 or sum(len(t['chars']) for t in traces)>100000:raise DocumentError('La página supera los límites de fuentes o texto del editor.')
    # Only direct, unambiguous page text with verified font maps is editable.
    # Marked content and clipping remain byte-for-byte intact.
    compatible={};metadata={item[0]:item for item in fonts}
    for scope,resource in {(obj['scope'],obj['font']) for obj in objects}:
        from .form_text import SAFE
        if not SAFE.fullmatch(resource):continue
        owner=scope or page.xref
        for _ in range(20):
            kind,value=doc.xref_get_key(owner,'Resources/Font/'+resource)
            if kind=='xref':break
            if scope or doc.xref_get_key(owner,'Resources')[0]!='null':break
            kind,value=doc.xref_get_key(owner,'Parent')
            if kind!='xref':break
            owner=int(value.split()[0])
        else:continue
        if kind!='xref':continue
        xref=int(value.split()[0]);item=metadata.get(xref)
        if item is None:
            try:name,ext,kind,_=doc.extract_font(xref)
            except (ValueError,RuntimeError):continue
            item=(xref,ext,kind,name,resource,'',scope)
        if xref not in cache:
            try:cache[xref]=OriginalFont(doc,item)
            except (DocumentError,ValueError,UnicodeError) as exc:cache[xref]=str(exc)
        if isinstance(cache[xref],OriginalFont):compatible[(scope,resource)]=cache[xref]
    if len(compatible)>100 or sum(font.program_bytes for font in {v.xref:v for v in compatible.values()}.values())>64*1024*1024:raise DocumentError('Los recursos de fuente superan el presupuesto de edición.')
    if not compatible:
        reasons=list(dict.fromkeys(cache[xref] for xref in metadata if isinstance(cache.get(xref),str)))
        detail=' '+reasons[0] if len(reasons)==1 else ''
        raise DocumentError('No se encontró una fuente original compatible en el contenido seleccionado.'+detail)
    # Context scans protect/locate neighbors and complete objects on dense pages;
    # they are not an editable selection. Keep the selection limit at 100 while
    # retaining the existing hard bounds of 5000 source groups/100000 characters.
    limit=5000 if context else 100
    if '_trace_index' not in cache:cache['_trace_index']=trace_index(traces)
    if '_origin_objects' not in cache:
        origin_objects={}
        for obj in objects:
            if (obj['scope'],obj['font']) not in compatible:continue
            point=obj['origin']*obj['matrix']*page.transformation_matrix
            if all(math.isfinite(v) for v in point):origin_objects.setdefault((math.floor(point.x*50),math.floor(point.y*50)),[]).append((obj,point))
        cache['_origin_objects']=origin_objects
    rows=[]
    from .type3_text import merge_lines,trace as type3_trace
    blocks=merge_lines(doc,page,page.get_text('rawdict',sort=True,flags=f.TEXTFLAGS_TEXT|f.TEXT_IGNORE_ACTUALTEXT)['blocks'],objects,list(compatible.values()))
    for bi,block in enumerate(blocks):
        for li,line in enumerate(block.get('lines',[])):
            for si,span in enumerate(line['spans']):
                bounds=f.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                text=''.join(c['c'] for c in span['chars']);reason='';font=None;native=None;spacing=None;actual_size=span['size']
                found=[];g=None
                from .affine_text import geometry,polygon,contains,rectangle,overlap
                px,py=span['origin'];nearby=[]
                if not math.isfinite(px) or not math.isfinite(py):raise DocumentError('La página contiene posiciones de texto no finitas; no se edita.')
                for dx in [-1,0,1]:
                    for dy in [-1,0,1]:nearby.extend(cache['_origin_objects'].get((math.floor(px*50)+dx,math.floor(py*50)+dy),[]))
                for obj,origin in nearby:
                    face=compatible.get((obj['scope'],obj['font']))
                    if face is None or normal_name(span['font']) not in face.aliases:continue
                    if math.dist(origin,span['origin'])>.02:continue
                    try:
                        candidate=geometry(obj,page,span)
                        if math.dist(candidate['direction'],line['dir'])>.001:continue
                        encoded,_=face.encode(text,candidate['size'])
                    except DocumentError:continue
                    if obj['shows'][0].value==encoded:found.append((face,obj,candidate))
                try:
                    if len(found)!=1:raise DocumentError('El texto necesita un grupo original único y verificable; revisa fuentes, objetos o transformaciones.')
                    font,obj,g=found[0]
                    if not (rect+(-.05,-.05,.05,.05)).contains(bounds):raise DocumentError('La región corta este fragmento de texto.')
                    if line.get('wmode',0)!=0:raise DocumentError('La escritura vertical requiere otro tratamiento.')
                    trace=matching_traces(traces,text,span['origin'],cache['_trace_index'])
                    if font.type=='Type3':
                        verified=type3_trace(font,span,traces)
                        trace=[verified] if verified else []
                    if len(trace)!=1 or trace[0]['type']!=0 or not 0<trace[0]['opacity']<=1 or trace[0]['layer']:raise DocumentError('El texto no tiene una apariencia visible única y verificable.')
                    if any(c[1] not in ({font.base.has_glyph(c[0],fallback=0)} if font.base else {entry[0] if font.trace_cid else entry[2] for entry in font.options.get(chr(c[0]),[])}) for c in trace[0]['chars']):raise DocumentError('El mapa de glifos no coincide con el texto representado.')
                    from .text_spacing import source_layout
                    actual_size=g['size']
                    local={**obj,'spacing':{**obj['spacing'],'char':obj['spacing']['char']*g['factor'],'word':obj['spacing']['word']*g['factor'],'scale':obj['spacing']['scale']*g['horizontal']}}
                    width,origins,spacing=source_layout(font,text,actual_size,local);g=geometry(obj,page,span,width);cell=polygon(g)
                    for char,advance in zip(span['chars'],origins):
                        expected=[span['origin'][i]+g['direction'][i]*advance for i in [0,1]]
                        if math.dist(char['origin'],expected)>.3:raise DocumentError('El espaciado no coincide con los caracteres representados.')
                    if any(not contains(clip,cell) for clip in obj['clips']):raise DocumentError('El texto queda parcialmente fuera del recorte Form.')
                    if any(overlap(cell,obstacle)>.1 for obstacle in cache['_obstacles']):raise DocumentError('El fragmento cruza una imagen, campo o anotación.')
                    show=obj['shows'][0];native=[show.start,show.end,show.kind]
                except DocumentError as exc:reason=str(exc)
                from .text_compositing import original_only
                row={'original_only':bool(native and (trace[0]['opacity']<1 or original_only(doc,obj))),'id':f'{bi}:{li}:{si}','text':text,'font':span['font'],'size':actual_size,'display_size':span['size'],'color':span['color'],'alpha':span.get('alpha',255),'opacity':trace[0]['opacity'] if native else None,'origin':list(span['origin']),'bbox':list(bounds),'editable':not reason,'reason':reason,'subset':bool(font and font.restricted),'method':'form-occurrence' if native and obj['path'] else 'direct-content','_font':font,'_font_resource':obj['font'] if native else None,'_native':native,'_spacing':spacing,'_native_path':obj['path'] if native else [],'_clips':obj['clips'] if native else [],'_obstacles':cache['_obstacles'],'_text_object':obj['object'] if native else None,'_line_matrix':list(obj['line_matrix']) if native else None,'_geometry':g if native else None,'quad':polygon(g) if g else None,'transformed':g['transformed'] if g else tuple(line['dir'])!=(1.,0.)}
                if native is not None and row['editable']:
                    try:cache['_semantic_text'].probe(row)
                    except DocumentError as exc:row.update(editable=False,reason=str(exc))
                from .native_format import availability as format_availability
                row['_format_page']=number
                format_reason=format_availability(doc,row)
                row.update(format_editable=not format_reason,format_reason=format_reason)
                if native is None:row.pop('_geometry')
                rows.append(row)
                if len(rows)>limit:raise DocumentError('Hasta 5000 fragmentos de contexto por página.' if context else 'Hasta 100 fragmentos por región.')
    return rect,rows
