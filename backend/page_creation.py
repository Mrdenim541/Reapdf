"""Duplicar páginas editadas e insertar páginas en blanco sin rasterizar."""
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError, finite, MAX_PAGES
from .merge import merge_pdf


def duplicate_pdf(data, operations, pages, position):
    with open_pdf(data) as doc:
        if not doc.permissions & fitz.PDF_PERM_COPY:
            raise DocumentError('El documento no permite copiar páginas.')
    # Copiar la versión editada, no solo el PDF originalmente abierto.
    edited = export_pdf(data, operations)
    return merge_pdf(data, operations, edited, pages, position, 'Páginas duplicadas')


def blank_pdf(data, operations, position, count, width, height):
    with open_pdf(data) as doc:
        if type(count) is not int or not 1 <= count <= MAX_PAGES - len(doc):
            raise DocumentError('Indica una cantidad de páginas en blanco sin superar 500 páginas en total.')
    if any(not finite(v) or not 10 <= v <= 3000 for v in [width, height]):
        raise DocumentError('El ancho y alto deben estar entre 10 y 3000 puntos PDF.')
    with fitz.open() as incoming:
        for _ in range(count):
            incoming.new_page(width=width, height=height)
        return merge_pdf(data, operations, incoming.tobytes(), list(range(count)), position, 'Páginas en blanco')
