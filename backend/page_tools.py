"""Recorte reversible por versiones y división sin alterar la fuente."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError, finite, MAX_PAGES
from .pages import organize_pdf
from .merge import _check_source, _check_bookmarks, _incoming_links

MAX_SPLIT_BYTES = 100 * 1024 * 1024


def _selection(pages, count):
    if not isinstance(pages, list) or not pages or len(pages) > count or any(type(p) is not int or not 0 <= p < count for p in pages) or len(set(pages)) != len(pages):
        raise DocumentError('Selecciona páginas válidas, sin repeticiones.')


def crop_pdf(data, operations, pages, margins=None, *, reset=False):
    with open_pdf(data) as source:
        if source.get_sigflags() > 0:
            raise DocumentError('No se recortan PDF firmados en este prototipo.')
        if not source.permissions & fitz.PDF_PERM_MODIFY:
            raise DocumentError('El documento no permite modificar los límites de página.')
        _selection(pages, len(source))
        if type(reset) is not bool:
            raise DocumentError('Modo de recorte no válido.')
        if not reset:
            if not isinstance(margins, list) or len(margins) != 4 or any(not finite(v) or v < 0 for v in margins):
                raise DocumentError('Indica márgenes superior, derecho, inferior e izquierdo válidos en puntos.')
            top, right, bottom, left = margins
            for number in pages:
                rect = source[number].rect
                if rect.width-left-right < 10 or rect.height-top-bottom < 10:
                    raise DocumentError('El recorte debe conservar al menos 10 × 10 puntos en cada página.')
    edited = export_pdf(data, operations)
    with open_pdf(edited) as output:
        for number in pages:
            page = output[number]
            if reset:
                # CropBox usa el eje Y superior de MuPDF, incluso si MediaBox no empieza en cero.
                media = page.mediabox
                page.set_cropbox(fitz.Rect(media.x0, 0, media.x1, media.height))
            else:
                visible = fitz.Rect(left, top, page.rect.width-right, page.rect.height-bottom)
                native = visible * page.derotation_matrix
                old = page.cropbox
                page.set_cropbox(fitz.Rect(native.x0+old.x0, native.y0+old.y0,
                                           native.x1+old.x0, native.y1+old.y0))
        return output.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4, deflate=True)


def prepare_split(data,operations,*,size=None,groups=None,names=None,bookmark_level=None):
    from .split_plan import plan
    with open_pdf(data) as source:
        if source.get_sigflags()>0:raise DocumentError('Crea una copia de trabajo antes de dividir un PDF firmado; sus firmas no serían válidas en las partes.')
        if not source.permissions&fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite dividir o copiar páginas.')
        _check_source(source);_check_bookmarks(source);_incoming_links(source)
    edited=export_pdf(data,operations)
    with open_pdf(edited) as doc:
        # Pending changes must pass the same partition guards as the original.
        _check_source(doc);_check_bookmarks(doc);_incoming_links(doc)
        from .structure_partition import partition
        partition(doc,[p.xref for p in doc])
        result=plan(doc,size=size,groups=groups,names=names,bookmark_level=bookmark_level)
        result['rotations']=[p.rotation for p in doc]
    return edited,result


def inspect_split(data,operations,**options):
    _,result=prepare_split(data,operations,**options)
    result.pop('rotations');return result


def split_pdf(data, operations, *, size=None, groups=None,names=None,bookmark_level=None,manifest=False):
    import json,hashlib
    if type(manifest) is not bool:raise DocumentError('La opción de relación de archivos debe ser verdadera o falsa.')
    edited,review=prepare_split(data,operations,size=size,groups=groups,names=names,bookmark_level=bookmark_level)
    buffer=BytesIO();total=0;records=[]
    with ZipFile(buffer,'w',ZIP_DEFLATED) as archive:
        for part in review['parts']:
            group=part['pages'];plan=[{'page':p,'rotation':review['rotations'][p]} for p in group]
            result=organize_pdf(edited,[],plan,extract=True,partition_tags=True);total+=len(result)
            if total>MAX_SPLIT_BYTES:raise DocumentError('La división supera 100 MB de PDF de salida. Reduce el documento antes de dividirlo.')
            archive.writestr(part['name'],result)
            records.append({'name':part['name'],'source_pages':[p+1 for p in group],'pages':len(group),'bytes':len(result),'sha256':hashlib.sha256(result).hexdigest()})
        if manifest:archive.writestr('reapdf-division.json',json.dumps({'format':'reapdf-split-receipt','version':1,'source_sha256':hashlib.sha256(edited).hexdigest(),'source_pages':review['pages'],'parts':records},ensure_ascii=False,indent=2).encode('utf-8'))
    return buffer.getvalue()
