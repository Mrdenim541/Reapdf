"""Transformación conservadora de imágenes existentes directas y no compartidas."""
from collections import Counter
import re
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .images import prepare_image
from .pdf_content import placements,patch,set_content


def image_invocation(page,xref):
    names={i[7] for i in page.get_images(full=True) if i[0]==xref and not i[-1]}
    found=[p for p in placements(page.read_contents())['images'] if p['resource'] in names]
    if len(found)!=1:raise DocumentError('La imagen requiere una invocación directa única.')
    return found[0]


def image_model(doc,number):
    if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
    counts=Counter()
    for page in doc:
        for info in page.get_image_info(xrefs=True):
            counts[info['xref']]+=1
            if sum(counts.values())>2000:raise DocumentError('Este editor admite hasta 2000 apariciones de imágenes.')
    page=doc[number];resources=doc.xref_get_key(page.xref,'Resources/ExtGState')[0]!='null'
    clipping=bool(re.search(rb'(?:^|\s)W\*?(?=\s)',page.read_contents()))
    ocr=any('GlyphLessFont' in font[3] for font in page.get_fonts())
    direct={i[0] for i in page.get_images(full=True) if i[-1]==0}
    items=[]
    for info in page.get_image_info(xrefs=True):
        if min(info['width'],info['height'])<=1:continue
        xref=info['xref'];reason='';a,b,c,d,_,_=info['transform'];box=fitz.Rect(info['bbox'])*page.rotation_matrix
        if doc.get_sigflags()>0 or not doc.permissions & fitz.PDF_PERM_MODIFY:reason='Documento firmado o sin permiso de edición.'
        elif not xref or xref not in direct:reason='Imagen dentro de una estructura o formulario gráfico no compatible.'
        elif counts[xref]!=1:reason='La imagen se comparte entre varias posiciones; no se modifica globalmente.'
        elif doc.xref_get_key(xref,'OC')[0]!='null':reason='Imagen asociada a una capa no compatible.'
        elif ocr:reason='La página tiene una capa OCR; mover la imagen desalinearía el texto.'
        elif abs(b)>.001 or abs(c)>.001 or a<=0 or d<=0:reason='Imagen inclinada, girada internamente o reflejada.'
        elif min(info['width'],info['height'])<=1 or not page.rect.contains(box):reason='Imagen mínima o parcialmente recortada.'
        direct_content=False
        if not reason and (resources or clipping):
            try:
                invocation=image_invocation(page,xref)
                expected=fitz.Rect(0,0,1,1)*invocation['matrix']*page.transformation_matrix
                if any(abs(a-b)>.02 for a,b in zip(expected,info['bbox'])):raise DocumentError('La transformación de imagen no coincide con su posición visible.')
                direct_content=True
            except DocumentError as exc:reason=str(exc)
        items.append({'xref':xref,'width':info['width'],'height':info['height'],'rect':list(box),'digest':info['digest'].hex(),'editable':not reason,'reason':reason,'direct_content':direct_content,'notice':'Se conserva el recorte y la transparencia originales; revisa la vista previa.' if direct_content else ''})
    return {'images':items}


def edit_image(base,operations,number,xref,action,box=None,data=None):
    if type(xref) is not int or action not in ['move','replace','delete']:raise DocumentError('Imagen o acción no válida.')
    with open_pdf(base) as source:
        editable(source);rows=image_model(source,number)['images'];original=next((r for r in rows if r['xref']==xref),None)
        if not original or not original['editable']:raise DocumentError(original['reason'] if original else 'Imagen inexistente.')
    with open_pdf(export_pdf(base,operations)) as doc:
        rows=image_model(doc,number)['images']
        candidates=[r for r in rows if r['digest']==original['digest'] and all(abs(a-b)<.01 for a,b in zip(r['rect'],original['rect']))]
        if len(candidates)!=1 or not candidates[0]['editable']:raise DocumentError('Los cambios previos ya no permiten identificar esta imagen de forma segura.')
        item=candidates[0];page=doc[number]
        rect=fitz.Rect(item['rect'])
        if action=='move':
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Posición y tamaño de imagen no válidos.')
            rect=fitz.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])
            if min(rect.width,rect.height)<1 or not page.rect.contains(rect):raise DocumentError('La imagen debe quedar dentro de la página y medir al menos 1 × 1 pt.')
        replacement=None
        if action=='replace':_,replacement=prepare_image(page,{'data':data,'points':[[rect.x0,rect.y0],[rect.x1,rect.y1]]})
        if item['direct_content']:
            invocation=image_invocation(page,item['xref']);content=page.read_contents()
            if action=='move':
                native=rect*page.derotation_matrix;rotation=page.rotation;page.set_rotation(0)
                target=native*~page.transformation_matrix
                matrix=fitz.Matrix(target.width,0,0,target.height,target.x0,target.y0)*~invocation['matrix']
                value=('q '+' '.join(f'{v:.10f}' for v in matrix)+' cm ').encode()+content[invocation['start']:invocation['end']]+b' Q'
                page.set_rotation(rotation)
            elif action=='delete':value=b''
            else:
                # insert_image imports the replacement and its alpha mask. Keep
                # its new resources, but replace only the original Do location.
                xref=page.insert_image(page.rect,stream=replacement)
                names=[i[7] for i in page.get_images(full=True) if i[0]==xref and not i[-1]]
                if not names or not re.fullmatch(r'[A-Za-z0-9_.-]+',names[-1]):raise DocumentError('No se pudo identificar el recurso de reemplazo.')
                value=('/'+names[-1]+' Do').encode()
            set_content(doc,page,patch(content,[(invocation['start'],invocation['end'],value)]))
            return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        # Copy the complete image object first, including the original filter,
        # color space and alpha mask. No JPEG/PNG decode/re-encode when moving.
        clone=None
        if action=='move':clone=doc.get_new_xref();doc.update_object(clone,'<<>>');doc.xref_copy(item['xref'],clone)
        page.delete_image(item['xref'])
        if action!='delete':
            native=rect*page.derotation_matrix;rotation=page.rotation
            try:
                page.set_rotation(0)
                if action=='move':page.insert_image(native,xref=clone,keep_proportion=False)
                else:page.insert_image(native,stream=replacement,keep_proportion=False)
            finally:page.set_rotation(rotation)
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
