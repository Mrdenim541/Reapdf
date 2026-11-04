"""Explicit lossy redaction: rebuild every page from censored RGB pixels only.

No source PDF object, text layer, embedded file, structure, action or metadata is
copied into the output. This is an alternative for complex content, not a claim
of lossless native redaction. All visible occurrences must still be selected.
"""
import math
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable


def redact(base,operations,regions,dpi=200):
    if type(dpi) is not int or dpi not in [150,200,300]:raise DocumentError('La copia visual admite 150, 200 o 300 ppp.')
    if not isinstance(regions,list) or not 1<=len(regions)<=100:raise DocumentError('Marca de 1 a 100 regiones para censurar.')
    with open_pdf(base) as original:
        editable(original)
        if not original.permissions&f.PDF_PERM_COPY:raise DocumentError('La copia visual requiere permiso de extracción y modificación.')
    scale=dpi/72;planned={}
    with open_pdf(export_pdf(base,operations)) as source,f.open() as output:
        if len(source)>20:raise DocumentError('La copia visual admite hasta 20 páginas en todo el documento.')
        total=0
        for p in source:
            if list(p.widgets() or []):raise DocumentError('Aplana primero los campos antes de generar la copia visual censurada.')
            if any(a.type[0]==f.PDF_ANNOT_REDACT for a in p.annots() or []):raise DocumentError('Hay censuras previas sin aplicar; resuélvelas antes de generar la copia visual.')
            w,h=math.ceil(p.rect.width*scale),math.ceil(p.rect.height*scale);total+=w*h
            if w*h>24_000_000 or total>64_000_000:raise DocumentError('La copia visual supera 24 MP por página o 64 MP en total; reduce la resolución.')
        for row in regions:
            if not isinstance(row,dict) or set(row)!={'page','box'} or type(row['page']) is not int or not 0<=row['page']<len(source):raise DocumentError('Página de censura visual no válida.')
            box=row['box']
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box) or min(box[2:])<1:raise DocumentError('Región de censura visual no válida.')
            rect=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])
            if not source[row['page']].rect.contains(rect):raise DocumentError('La región de censura visual sale de su página.')
            planned.setdefault(row['page'],[]).append(rect)
        for number,page in enumerate(source):
            pix=page.get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False,annots=False)
            for rect in planned.get(number,[]):
                # Cover all touched pixels, including subpixel edges. Regions
                # are display coordinates, matching the UI on cropped/rotated pages.
                pixel=f.IRect(math.floor(rect.x0*scale),math.floor(rect.y0*scale),math.ceil(rect.x1*scale),math.ceil(rect.y1*scale))&pix.irect
                pix.set_rect(pixel,(0,0,0))
            dest=output.new_page(width=page.rect.width,height=page.rect.height)
            dest.insert_image(dest.rect,pixmap=pix)
        result=output.tobytes(garbage=4,deflate=True)
    if len(result)>100*1024*1024:raise DocumentError('La copia visual supera 100 MB; reduce la resolución.')
    with open_pdf(result) as check:
        if check.embfile_count() or check.get_toc() or any(p.get_text().strip() or list(p.annots() or []) or list(p.widgets() or []) or p.get_links() or len(p.get_images())!=1 for p in check):raise DocumentError('La comprobación de la copia visual detectó contenido adicional; no se publica.')
    return result
