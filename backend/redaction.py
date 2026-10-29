"""Copia censurada de regiones explícitas; nunca sustituye la sesión de origen."""
import re
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable


def redact_pdf(base,operations,regions):
    if not isinstance(regions,list) or not 1<=len(regions)<=100:raise DocumentError('Marca de 1 a 100 regiones para censurar.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions & fitz.PDF_PERM_COPY:raise DocumentError('La censura requiere permiso de extracción y modificación.')
    with open_pdf(export_pdf(base,operations)) as doc:
        if doc.get_ocgs() or doc.xref_length()>50000:raise DocumentError('No se censuran documentos con capas o estructuras superiores a 50000 objetos.')
        if any(list(p.widgets() or []) for p in doc):raise DocumentError('Aplana primero el formulario para censurar una copia sin campos.')
        prepared=[];pages=set();total_pixels=0
        for item in regions:
            if not isinstance(item,dict) or type(item.get('page')) is not int or not 0<=item['page']<len(doc):raise DocumentError('Página de censura no válida.')
            box=item.get('box')
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Región de censura no válida.')
            page=doc[item['page']];x,y,w,h=box;rect=fitz.Rect(x,y,x+w,y+h)
            if min(w,h)<1 or not page.rect.contains(rect):raise DocumentError('La región debe medir al menos 1 punto y quedar dentro de la página.')
            prepared.append((item['page'],rect*page.derotation_matrix));pages.add(item['page'])
        if len(pages)>20:raise DocumentError('Hasta 20 páginas por copia censurada.')
        # Restrict the initial implementation to direct content. Tagged replacement
        # text and Form XObjects need a separate audit before being accepted.
        for n in pages:
            page=doc[n]
            if page.get_xobjects():raise DocumentError('Esta página contiene objetos de formulario internos. Esta censura inicial requiere contenido directo.')
            if any(re.search(rb'(?<![A-Za-z])(?:BDC|BMC|BI)(?![A-Za-z])',doc.xref_stream(xref)) for xref in page.get_contents()):raise DocumentError('Esta página contiene contenido marcado o imágenes en línea que todavía no se pueden censurar.')
            if any(doc.xref_get_key(page.xref,key)[0]!='null' for key in ['Resources/Pattern','Resources/Shading']):raise DocumentError('Esta página usa patrones o sombreados que todavía no se pueden censurar.')
            for image in page.get_images(full=True):
                total_pixels+=image[2]*image[3]
                if image[2]*image[3]>24_000_000 or total_pixels>64_000_000:raise DocumentError('Las imágenes de la selección superan los límites de censura (24 MP por imagen, 64 MP por lote).')
                uses=sum(len(p.get_image_rects(image[0])) for p in doc)
                if uses>1:raise DocumentError('La página usa una imagen compartida. No se censura para evitar conservar otra copia del recurso original.')
        for page in doc:
            for annot in list(page.annots() or []):
                if annot.type[0]==fitz.PDF_ANNOT_REDACT:raise DocumentError('Hay censuras previas sin aplicar. Retíralas o usa una copia sin esas marcas.')
        # Remove comments, file-attachment annotations and links throughout this
        # download. None of these objects should leak their original contents.
        for page in doc:
            for annot in list(page.annots() or []):page.delete_annot(annot)
        for n,rect in prepared:doc[n].add_redact_annot(rect,fill=(0,0,0),cross_out=False)
        for n in pages:doc[n].apply_redactions(images=2,graphics=2,text=0)
        doc.set_toc([])
        # hidden_text=False deliberately preserves OCR/text outside the selected
        # regions. Redacting hidden text globally would also erase scan pixels.
        doc.scrub(attached_files=True,clean_pages=True,embedded_files=True,hidden_text=False,javascript=True,metadata=True,redactions=False,remove_links=True,reset_fields=False,reset_responses=True,thumbnails=True,xml_metadata=True)
        for xref in range(1,doc.xref_length()):
            if doc.xref_get_key(xref,'Type')[1]=='/EmbeddedFile':doc.update_stream(xref,b'')
            for key in ['AF','ActualText','Alt','PieceInfo','AA']:
                if doc.xref_get_key(xref,key)[0]!='null':doc.xref_set_key(xref,key,'null')
        for key in ['StructTreeRoot','MarkInfo','OpenAction','Collection','PieceInfo']:
            doc.xref_set_key(doc.pdf_catalog(),key,'null')
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True,clean=True)
