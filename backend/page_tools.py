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


def split_pdf(data, operations, *, size=None, groups=None):
    with open_pdf(data) as source:
        if source.get_sigflags() > 0 or not source.permissions & fitz.PDF_PERM_COPY:
            raise DocumentError('El documento no permite dividir páginas o contiene indicadores de firma.')
        _check_source(source)
        _check_bookmarks(source)
        _incoming_links(source)  # Rechazar acciones no verificadas antes de producir partes.
        count = len(source)
        rotations = [p.rotation for p in source]
        if groups is None:
            if type(size) is not int or not 1 <= size <= count:
                raise DocumentError('El tamaño del bloque debe estar entre 1 y el número de páginas.')
            groups = [list(range(start, min(start+size, count))) for start in range(0, count, size)]
        else:
            if size is not None or not isinstance(groups, list) or not 1 <= len(groups) <= MAX_PAGES:
                raise DocumentError('Configura bloques o grupos de páginas, sin mezclar ambos modos.')
            for group in groups:
                _selection(group, count)
            flattened = [p for group in groups for p in group]
            if sorted(flattened) != list(range(count)):
                raise DocumentError('Los grupos deben incluir cada página del documento exactamente una vez.')
    edited = export_pdf(data, operations)
    buffer = BytesIO()
    total = 0
    with ZipFile(buffer, 'w', ZIP_DEFLATED) as archive:
        for index, group in enumerate(groups, 1):
            plan = [{'page': p, 'rotation': rotations[p]} for p in group]
            result = organize_pdf(edited, [], plan, extract=True)
            total += len(result)
            if total > MAX_SPLIT_BYTES:
                raise DocumentError('La división supera 100 MB de PDF de salida. Reduce el documento antes de dividirlo.')
            archive.writestr(f'parte-{index:03d}.pdf', result)
    return buffer.getvalue()
