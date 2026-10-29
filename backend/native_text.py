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
    if not compatible:raise DocumentError('No se encontró una fuente original compatible en el contenido seleccionado.')
    rows=[]
    for bi,block in enumerate(page.get_text('rawdict',sort=True,flags=f.TEXTFLAGS_TEXT)['blocks']):
        for li,line in enumerate(block.get('lines',[])):
            for si,span in enumerate(line['spans']):
                bounds=f.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                text=''.join(c['c'] for c in span['chars']);reason='';font=None;native=None;spacing=None;actual_size=span['size']
                found=[]
                for obj in objects:
                    face=compatible.get((obj['scope'],obj['font']))
                    if face is None or normal_name(span['font']) not in face.aliases:continue
                    matrix=obj['matrix'];origin=obj['origin']*matrix*page.transformation_matrix;effective_size=obj['size']*obj['factor']
                    if not 0<effective_size<=1000 or abs(effective_size*math.sqrt(obj['spacing']['scale']/100)-span['size'])>=.01 or abs(origin.x-span['origin'][0])>=.02 or abs(origin.y-span['origin'][1])>=.02:continue
                    try:encoded,_=face.encode(text,effective_size)
                    except DocumentError:continue
                    if obj['shows'][0].value==encoded:found.append((face,obj))
                try:
                    if len(found)!=1:raise DocumentError('El texto necesita un grupo original único y verificable; revisa fuentes, objetos o transformaciones.')
                    font,obj=found[0]
                    if any(not (clip+(-.05,-.05,.05,.05)).contains(bounds) for clip in obj['clips']):raise DocumentError('El texto queda parcialmente fuera del recorte Form.')
                    trace=[t for t in traces if ''.join(chr(c[0]) for c in t['chars'])==text and t['chars'] and abs(t['chars'][0][2][0]-span['origin'][0])<.02 and abs(t['chars'][0][2][1]-span['origin'][1])<.02]
                    if len(trace)!=1 or trace[0]['type']!=0 or trace[0]['opacity']!=1 or trace[0]['layer']:raise DocumentError('El texto no tiene una apariencia opaca única y verificable.')
                    if any(c[1] not in ({font.base.has_glyph(c[0],fallback=0)} if font.base else {entry[0] if font.trace_cid else entry[2] for entry in font.options.get(chr(c[0]),[])}) for c in trace[0]['chars']):raise DocumentError('El mapa de glifos no coincide con el texto representado.')
                    from .text_spacing import source_layout
                    actual_size=obj['size']*obj['factor']
                    local={**obj,'spacing':{**obj['spacing'],'char':obj['spacing']['char']*obj['factor'],'word':obj['spacing']['word']*obj['factor']}}
                    width,origins,spacing=source_layout(font,text,actual_size,local)
                    if abs(width-bounds.width)>.3:raise DocumentError('Las anchuras originales no coinciden con el fragmento.')
                    for char,advance in zip(span['chars'],origins):
                        if abs(char['origin'][0]-span['origin'][0]-advance)>.3:raise DocumentError('El espaciado no coincide con los caracteres representados.')
                    show=obj['shows'][0];native=[show.start,show.end,show.kind]
                except DocumentError as exc:reason=str(exc)
                rows.append({'id':f'{bi}:{li}:{si}','text':text,'font':span['font'],'size':actual_size,'display_size':span['size'],'color':span['color'],'origin':list(span['origin']),'bbox':list(bounds),'editable':not reason,'reason':reason,'subset':bool(font and font.restricted),'method':'form-occurrence' if native and obj['path'] else 'direct-content','_font':font,'_native':native,'_spacing':spacing,'_native_path':obj['path'] if native else []})
    if len(rows)>100:raise DocumentError('Hasta 100 fragmentos por región.')
    return rect,rows
