"""Byte-preserving edits of bounded, single-show original text objects.

Supports verified base fonts, simple TrueType and Identity-H subsets. Marked-content and clip
operators are untouched. No redaction, resource replacement or tag rewriting.
"""
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
        cache['_structure']=(placements(content)['texts'],page.get_fonts(full=True),page.get_texttrace())
    objects,fonts,traces=cache['_structure']
    if len(fonts)>20 or sum(len(t['chars']) for t in traces)>100000:raise DocumentError('La página supera los límites de fuentes o texto del editor.')
    # Only direct, unambiguous page text with verified font maps is editable.
    # Marked content and clipping remain byte-for-byte intact.
    compatible={}
    for item in fonts:
        if item[-1]:continue
        if item[0] not in cache:
            try:cache[item[0]]=OriginalFont(doc,item)
            except (DocumentError,ValueError,UnicodeError) as exc:cache[item[0]]=str(exc)
        if isinstance(cache[item[0]],OriginalFont):compatible[item[4]]=cache[item[0]]
    if sum(font.program_bytes for font in compatible.values())>64*1024*1024:raise DocumentError('Los programas de fuente superan 64 MB.')
    if not compatible:raise DocumentError('El contenido marcado o recortado todavía no es compatible con este modo.')
    rows=[]
    for bi,block in enumerate(page.get_text('rawdict',sort=True,flags=f.TEXTFLAGS_TEXT)['blocks']):
        for li,line in enumerate(block.get('lines',[])):
            for si,span in enumerate(line['spans']):
                bounds=f.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                text=''.join(c['c'] for c in span['chars']);reason='';font=None;native=None
                candidates=[(resource,face) for resource,face in compatible.items() if normal_name(span['font']) in face.aliases]
                if len(candidates)!=1:reason='No se pudo identificar un subconjunto integrado único.'
                else:
                    resource,font=candidates[0]
                    try:
                        encoded,width=font.encode(text,span['size'])
                        found=[]
                        for obj in objects:
                            matrix=obj['matrix'];origin=obj['origin']*matrix*page.transformation_matrix
                            if obj['font']==resource and abs(obj['size']-span['size'])<.005 and abs(origin.x-span['origin'][0])<.02 and abs(origin.y-span['origin'][1])<.02:
                                if tuple(matrix)[:4]!=(1.,0.,0.,1.) or obj['shows'][0].value!=encoded:continue
                                found.append(obj['shows'][0])
                        if len(found)!=1:raise DocumentError('El texto necesita un objeto Tj único sin transformaciones ni espaciados especiales.')
                        trace=[t for t in traces if ''.join(chr(c[0]) for c in t['chars'])==text and t['chars'] and abs(t['chars'][0][2][0]-span['origin'][0])<.02 and abs(t['chars'][0][2][1]-span['origin'][1])<.02]
                        if len(trace)!=1 or trace[0]['type']!=0 or trace[0]['opacity']!=1 or trace[0]['layer']:raise DocumentError('El texto no tiene una apariencia opaca única y verificable.')
                        if any(c[1] not in ({font.base.has_glyph(c[0],fallback=0)} if font.base else {entry[2] for entry in font.options.get(chr(c[0]),[])}) for c in trace[0]['chars']):raise DocumentError('El mapa de glifos no coincide con el texto representado.')
                        if abs(width-bounds.width)>.3:raise DocumentError('Las anchuras originales no coinciden con el fragmento.')
                        advance=0
                        for char in span['chars']:
                            if abs(char['origin'][0]-span['origin'][0]-advance)>.3:raise DocumentError('El fragmento contiene ajustes de posición no compatibles.')
                            _,step=font.encode(char['c'],span['size']);advance+=step
                        native=[found[0].start,found[0].end,found[0].kind]
                    except DocumentError as exc:reason=str(exc)
                rows.append({'id':f'{bi}:{li}:{si}','text':text,'font':span['font'],'size':span['size'],'color':span['color'],'origin':list(span['origin']),'bbox':list(bounds),'editable':not reason,'reason':reason,'subset':bool(font and font.restricted),'method':'direct-content','_font':font,'_native':native})
    if len(rows)>100:raise DocumentError('Hasta 100 fragmentos por región.')
    return rect,rows
