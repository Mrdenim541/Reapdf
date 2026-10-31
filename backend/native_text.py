"""Byte-preserving edits of bounded, consecutive original text groups.

Supports verified base fonts, TrueType/CFF subsets and isolated Form invocations. Marked-content and clip
operators are untouched. No redaction, resource replacement or tag rewriting.
"""
import math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import placements


def native_model(doc,number,rect,font_cache=None):
    from .styled_text import OriginalFont,normal_name
    page=doc[number]
    if doc.get_ocgs():raise DocumentError('El texto asociado a capas todavía requiere otra edición.')
    content=page.read_contents();cache={} if font_cache is None else font_cache
    from .pdf_content import names
    if '_structure' not in cache:
        if 'ActualText' in names(content):raise DocumentError('El texto alternativo ActualText requiere actualización conjunta antes de editar.')
        from .form_text import structure
        cache['_structure']=(structure(doc,page),page.get_fonts(full=True),page.get_texttrace())
    objects,fonts,traces=cache['_structure']
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
    rows=[]
    from .type3_text import merge_lines,trace as type3_trace
    blocks=merge_lines(doc,page,page.get_text('rawdict',sort=True,flags=f.TEXTFLAGS_TEXT)['blocks'],objects,list(compatible.values()))
    for bi,block in enumerate(blocks):
        for li,line in enumerate(block.get('lines',[])):
            for si,span in enumerate(line['spans']):
                bounds=f.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                text=''.join(c['c'] for c in span['chars']);reason='';font=None;native=None;spacing=None;actual_size=span['size']
                found=[];g=None
                from .affine_text import geometry,polygon,contains,rectangle,overlap
                for obj in objects:
                    face=compatible.get((obj['scope'],obj['font']))
                    if face is None or normal_name(span['font']) not in face.aliases:continue
                    origin=obj['origin']*obj['matrix']*page.transformation_matrix
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
                    trace=[t for t in traces if ''.join(chr(c[0]) for c in t['chars'])==text and t['chars'] and math.dist(t['chars'][0][2],span['origin'])<.02]
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
                row={'original_only':bool(native and (trace[0]['opacity']<1 or original_only(doc,obj))),'id':f'{bi}:{li}:{si}','text':text,'font':span['font'],'size':actual_size,'display_size':span['size'],'color':span['color'],'alpha':span.get('alpha',255),'opacity':trace[0]['opacity'] if native else None,'origin':list(span['origin']),'bbox':list(bounds),'editable':not reason,'reason':reason,'subset':bool(font and font.restricted),'method':'form-occurrence' if native and obj['path'] else 'direct-content','_font':font,'_native':native,'_spacing':spacing,'_native_path':obj['path'] if native else [],'_clips':obj['clips'] if native else [],'_obstacles':cache['_obstacles'],'_line_matrix':list(obj['line_matrix']) if native else None,'_geometry':g if native else None,'quad':polygon(g) if g else None,'transformed':g['transformed'] if g else tuple(line['dir'])!=(1.,0.)}
                if native is None:row.pop('_geometry')
                rows.append(row)
    if len(rows)>100:raise DocumentError('Hasta 100 fragmentos por región.')
    return rect,rows
