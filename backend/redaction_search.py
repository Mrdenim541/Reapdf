"""Búsqueda acotada para preparar censuras; nunca detecta todo dato sensible."""
import hashlib
import json
import re
import pymupdf as fitz
from .engine import DocumentError, open_pdf, export_pdf
from .document_tools import editable, selected_pages
from .redaction import redact_pdf

MAX_MATCHES = 500
MAX_CHARACTERS = 500000
EMAIL = re.compile(r"(?<![\w.!#$%&'*+/=?^_`{|}~-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\.[A-Za-z]{2,63}(?![\w.-])")


def search_redactions(base, operations, query):
    if not isinstance(query, dict) or set(query) != {'terms', 'emails', 'case_sensitive', 'pages'}:
        raise DocumentError('Completa términos, correos, mayúsculas y páginas de búsqueda.')
    terms = query['terms']
    if (not isinstance(terms, list) or len(terms) > 20
            or any(not isinstance(t, str) or not 1 <= len(t.strip()) <= 160
                   or any(ord(c) < 32 for c in t) for t in terms)
            or type(query['emails']) is not bool or type(query['case_sensitive']) is not bool
            or (not terms and not query['emails'])):
        raise DocumentError('Usa hasta 20 términos de 1–160 caracteres sin saltos, o activa correos.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions & fitz.PDF_PERM_COPY:
            raise DocumentError('La búsqueda para censura requiere permiso de extracción.')
        selected_pages(source, query['pages'])
        if len(query['pages']) > 20:
            raise DocumentError('Busca en un máximo de 20 páginas por lote de censura.')
    # Bind the inspection to the immutable original, applied edits and exact query.
    # Serialised PDF IDs may vary between exports, so do not hash a rebuilt PDF.
    try:
        receipt = hashlib.sha256(base + json.dumps([operations, query], sort_keys=True,
                                    ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    except (ValueError, TypeError) as exc:
        raise DocumentError('La búsqueda o las ediciones contienen valores no válidos.') from exc
    candidates, empty_pages, unsupported_pages, seen = [], [], [], set()
    total = 0
    with open_pdf(export_pdf(base, operations)) as doc:
        if doc.xref_length() > 50000:
            raise DocumentError('La búsqueda admite hasta 50 000 objetos internos.')
        for number in query['pages']:
            page, found_text, unsupported = doc[number], False, False
            raw = page.get_text('rawdict', sort=True,
                                flags=fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES)
            for block in raw['blocks']:
                for line in block.get('lines', []):
                    chars = [c for span in line['spans'] for c in span['chars']]
                    total += sum(len(c['c']) for c in chars)
                    if total > MAX_CHARACTERS:
                        raise DocumentError('La búsqueda supera 500 000 caracteres; reduce las páginas.')
                    found_text |= any(c['c'].strip() for c in chars)
                    # Do not derive broad rectangular redactions from skewed text.
                    if tuple(line['dir']) not in {(1., 0.), (0., 1.), (-1., 0.), (0., -1.)}:
                        unsupported = True
                        continue
                    text, mapping, original = '', [], ''.join(c['c'] for c in chars)
                    for index, char in enumerate(chars):
                        value = char['c'] if query['case_sensitive'] else char['c'].casefold()
                        text += value
                        mapping.extend([index] * len(value))
                    hits = []
                    for term in terms:
                        needle = term.strip() if query['case_sensitive'] else term.strip().casefold()
                        start = 0
                        while (start := text.find(needle, start)) >= 0:
                            hits.append((mapping[start], mapping[start+len(needle)-1]+1, 'term'))
                            start += 1  # Include overlapping terms; never silently skip a match.
                            if len(hits) > MAX_MATCHES:
                                raise DocumentError('Más de 500 coincidencias; reduce términos o páginas.')
                    if query['emails']:
                        original_map = [i for i, c in enumerate(chars) for _ in c['c']]
                        for match in EMAIL.finditer(original):
                            hits.append((original_map[match.start()], original_map[match.end()-1]+1, 'email'))
                            if len(hits) > MAX_MATCHES:
                                raise DocumentError('Más de 500 coincidencias; reduce términos o páginas.')
                    for start, end, kind in sorted(hits):
                        rect = fitz.Rect(chars[start]['bbox'])
                        for char in chars[start+1:end]:
                            rect |= fitz.Rect(char['bbox'])
                        rect = rect * page.rotation_matrix
                        rect = (rect + (-.5, -.5, .5, .5)) & page.rect
                        if rect.is_empty or min(rect.width, rect.height) < 1:
                            continue
                        box = [rect.x0, rect.y0, rect.width, rect.height]
                        identity = (number, *(round(v, 4) for v in box))
                        if identity in seen:
                            continue
                        seen.add(identity)
                        if len(candidates) == MAX_MATCHES:
                            raise DocumentError('Más de 500 coincidencias; reduce términos o páginas.')
                        candidate_id = hashlib.sha256((receipt+repr(identity)).encode()).hexdigest()[:24]
                        candidates.append({'id': candidate_id, 'page': number, 'box': box,
                                           'text': ''.join(c['c'] for c in chars[start:end]), 'kind': kind})
            if not found_text:
                empty_pages.append(number)
            if unsupported:
                unsupported_pages.append(number)
    return {'receipt': receipt, 'candidates': candidates, 'pages': query['pages'],
            'empty_pages': empty_pages, 'unsupported_pages': unsupported_pages}


def redact_search(base, operations, query, receipt, selected):
    if (not isinstance(selected, list) or not 1 <= len(selected) <= 100
            or any(not isinstance(i, str) for i in selected) or len(set(selected)) != len(selected)):
        raise DocumentError('Selecciona de 1 a 100 coincidencias sin repeticiones.')
    inspection = search_redactions(base, operations, query)
    if not isinstance(receipt, str) or inspection['receipt'] != receipt:
        raise DocumentError('La búsqueda cambió. Repite la revisión antes de censurar.')
    known = {c['id']: c for c in inspection['candidates']}
    if any(i not in known for i in selected):
        raise DocumentError('Hay coincidencias que no pertenecen a esta búsqueda.')
    regions = [{'page': known[i]['page'], 'box': known[i]['box']} for i in selected]
    result = redact_pdf(base, operations, regions)
    return result, sorted({r['page'] for r in regions})
