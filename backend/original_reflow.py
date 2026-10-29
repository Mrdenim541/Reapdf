"""Uniform original-font paragraph reflow in explicit, untagged text regions."""
import re,unicodedata
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .paragraphs import prepare_text_page,region_model
from .styled_text import styled_model,clone_resources
from .text_flow import next_line


def compatible_page(doc,page):
    from .pdf_content import names,operations
    if doc.get_ocgs() or page.get_xobjects() or doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('El reflujo original requiere una página sin capas, objetos Form ni árbol de etiquetas.')
    if 'ActualText' in names(page.read_contents()) or any(op in ['BDC','BMC','W','W*'] for op,_,_ in operations(page.read_contents())):raise DocumentError('El reflujo no reescribe texto marcado ni recortes. Usa la edición de una línea compatible.')


def uniform(doc,number,box):
    page=doc[number];compatible_page(doc,page);rect,rows=styled_model(doc,number,box)
    if not rows or any(not r['editable'] for r in rows):raise DocumentError('El bloque contiene una fuente o espaciado no verificable para reflujo original.')
    first=rows[0]
    if any(r.get('_spacing',{}).get('state',{}).get('scale',100)!=100 for r in rows):raise DocumentError('El reflujo de un bloque escalado requiere otra disposición. Puedes editar su línea conservando la escala.')
    if any(r['_font'].xref!=first['_font'].xref or abs(r['size']-first['size'])>.01 or r['color']!=first['color'] for r in rows):raise DocumentError('El reflujo original requiere un solo tamaño, color y fuente. Para formato mixto utiliza el editor de flujo.')
    return rect,rows


def inspect(base,ops,number,origin,text):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        page,_=prepare_text_page(doc,number);compatible_page(doc,page);matches=[]
        for block in page.get_text('dict',sort=True,flags=f.TEXTFLAGS_TEXT)['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if list(span['origin'])==origin and span['text']==text:matches.append(block)
        if len(matches)!=1:raise DocumentError('El párrafo no se identifica de forma única.')
        block=matches[0];rect=(f.Rect(block['bbox'])+(-2,-2,2,2))&page.rect;box=[rect.x0,rect.y0,rect.width,rect.height];_,value=region_model(doc,number,box)
        reason=''
        try:_,rows=uniform(doc,number,box);font=rows[0]['font']
        except DocumentError as exc:reason=str(exc);font=''
        return {'box':box,'text':value,'original_available':not reason,'reason':reason,'font':font}


def reflow(base,ops,number,box,text,preview=False,source_box=None):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa de 1 a 4000 caracteres, sin controles ni escritura de derecha a izquierda.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        page,rotation=prepare_text_page(doc,number);rect,rows=uniform(doc,number,box)
        if source_box is not None:
            source_rect,source_rows=uniform(doc,number,source_box)
            if not rect.contains(source_rect) or {r['id'] for r in rows}!={r['id'] for r in source_rows}:raise DocumentError('El área ampliada cruza otro texto o corta el párrafo original.')
        first=rows[0];font=first['_font'];size=first['size'];padding=2
        # Do not overwrite a frame, figure, or ruled table when the box grows.
        if any(((f.Rect(d['rect'])+(-.5,-.5,.5,.5))&rect).get_area()>.1 for d in page.get_drawings()):raise DocumentError('El área cruza dibujos o bordes. Ajusta el párrafo dentro de una región libre.')
        if any((f.Rect(link['from'])&rect).get_area()>.1 for link in page.get_links()):raise DocumentError('El área cruza un enlace.')
        prefix=[0.]
        for char in text:prefix.append(prefix[-1]+(0 if char=='\n' else font.encode(char,size)[1]))
        ascent=first['origin'][1]-first['bbox'][1];descent=first['bbox'][3]-first['origin'][1];leading=max(size*1.35,ascent+descent)
        cursor=0;baseline=rect.y0+padding+ascent;lines=[]
        while cursor<len(text):
            line,after,_=next_line(text,cursor,rect.width-2*padding,prefix)
            if baseline+descent>rect.y1-padding+.01:raise DocumentError('El párrafo no cabe. Amplía el alto o el ancho; no se elimina texto parcialmente.')
            lines.append((line,baseline));cursor=after;baseline+=leading
        report={'lines':len(lines),'font':first['font'],'size':size,'source_lines':len(rows),'box':list(rect)}
        if preview:return report
        clone_resources(doc,page)
        for row in rows:page.add_redact_annot(f.Rect(row['bbox']),fill=False,cross_out=False)
        page.apply_redactions(images=0,graphics=0,text=0);page.wrap_contents();resources=clone_resources(doc,page);alias='ReapdfReflowOriginal'
        while doc.xref_get_key(resources,alias)[0]!='null':alias+='x'
        doc.xref_set_key(resources,alias,f'{font.xref} 0 R');color=[((first['color']>>v)&255)/255 for v in [16,8,0]];snippets=[]
        for line,baseline in lines:
            if not line:continue
            encoded=font.encode(line,size)[0];point=f.Point(rect.x0+padding,baseline)*~page.transformation_matrix
            snippets.append(f"q BT 0 Tc 0 Tw 100 Tz 0 Tr 0 Ts /{alias} {size:.8f} Tf {' '.join(f'{v:.8f}' for v in color)} rg 1 0 0 1 {point.x:.8f} {point.y:.8f} Tm <{encoded.hex()}> Tj ET Q")
        xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,'\n'.join(snippets).encode());doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in page.get_contents()+[xref])+']');page.set_rotation(rotation);data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as check:
        check[number].set_rotation(0);actual=check[number].get_text(clip=rect,sort=True)
        clean=lambda v:re.sub(r'\s+','',v)
        if clean(actual)!=clean(text):raise DocumentError('La comprobación del párrafo detectó diferencias. No se publicó la edición.')
    return data,report
