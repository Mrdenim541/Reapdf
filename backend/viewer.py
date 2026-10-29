"""Datos de lectura y búsqueda expresados en coordenadas de la página visible."""
import math
import pymupdf as fitz
from .engine import DocumentError

MAX_SEARCH_RESULTS = 500


def text_items(page):
    items = []
    for block in page.get_text('dict', sort=True)['blocks']:
        for line in block.get('lines', []):
            # Texto alineado con los ejes, compensando giro de línea y de página.
            if tuple(line['dir']) not in {(1.,0.),(0.,1.),(-1.,0.),(0.,-1.)}:
                continue
            for span in line['spans']:
                if not span['text']:
                    continue
                quad = fitz.recover_quad(line['dir'], span)
                anchor = quad.ul * page.rotation_matrix
                angle = round(math.degrees(math.atan2(line['dir'][1],line['dir'][0])))
                items.append({'text': span['text'], 'x': anchor.x, 'y': anchor.y,
                              'width': quad.width, 'height': quad.height,
                              'size': span['size'], 'rotation': (page.rotation+angle)%360})
    return items


def search_document(doc, query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 200:
        raise DocumentError('Escribe entre 1 y 200 caracteres para buscar.')
    query = query.strip()
    results = []
    for number, page in enumerate(doc):
        for quad in page.search_for(query, quads=True):
            if len(results) == MAX_SEARCH_RESULTS:
                return {'results': results, 'truncated': True}
            source_rect = quad.rect
            rect = source_rect * page.rotation_matrix
            results.append({'page': number, 'rect': list(rect),
                            'text': page.get_textbox(source_rect).strip()})
    return {'results': results, 'truncated': False}
