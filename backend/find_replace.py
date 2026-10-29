"""Literal search and atomic replacement across contiguous digital text runs."""
import hashlib
import json
import re
from collections import defaultdict

import pymupdf as f

from .engine import open_pdf, export_pdf, DocumentError
from .document_tools import editable
from .styled_text import styled_model, replace_styled_regions


def digest(value):
    return hashlib.sha256(value).hexdigest()


def region_box(page, spans):
    rect = f.Rect(spans[0]['bbox'])
    for span in spans[1:]:
        rect |= f.Rect(span['bbox'])
    rect = (rect + (-.1, -.1, .1, .1)) & page.rect
    # Blocks require 10 pt; region_model still rejects cuts into neighbors.
    if rect.width < 10:
        rect.x1 = min(page.rect.x1, rect.x0 + 10)
        rect.x0 = max(page.rect.x0, rect.x1 - 10)
    if rect.height < 10:
        rect.y1 = min(page.rect.y1, rect.y0 + 10)
        rect.y0 = max(page.rect.y0, rect.y1 - 10)
    return [rect.x0, rect.y0, rect.width, rect.height]


def contiguous_groups(line):
    """Join explicit text only; never invent spaces across visual gaps."""
    group = []
    for span in line['spans']:
        if group:
            previous = group[-1]
            gap = span['bbox'][0] - previous['bbox'][2]
            aligned = abs(span['origin'][1] - previous['origin'][1]) <= .3
            if tuple(line['dir']) != (1., 0.) or not aligned or not -.1 <= gap <= .5:
                yield group
                group = []
        group.append(span)
    if group:
        yield group


def inspect(base, ops, query):
    if not isinstance(query, dict) or set(query) != {'text', 'pages', 'case_sensitive', 'whole_word'}:
        raise DocumentError('Consulta de búsqueda no válida.')
    text, pages = query['text'], query['pages']
    if not isinstance(text, str) or not 1 <= len(text) <= 200 or any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise DocumentError('Busca entre 1 y 200 caracteres, sin controles.')
    if any(type(query[k]) is not bool for k in ['case_sensitive', 'whole_word']):
        raise DocumentError('Opciones de búsqueda no válidas.')
    if not isinstance(pages, list) or not pages or len(pages) > 500 or any(type(n) is not int for n in pages) or len(set(pages)) != len(pages):
        raise DocumentError('Selecciona páginas distintas.')
    snapshot = export_pdf(base, ops)
    receipt = digest(base + json.dumps({'query': query, 'operations': ops}, sort_keys=True, ensure_ascii=True).encode())
    pattern = re.escape(text)
    if query['whole_word']:
        pattern = r'(?<!\w)' + pattern + r'(?!\w)'
    regex = re.compile(pattern, 0 if query['case_sensitive'] else re.IGNORECASE)
    matches, empty, characters = [], [], 0
    try:
        with open_pdf(base) as source:
            editable(source)
        protected = ''
    except DocumentError as exc:
        protected = str(exc)
    with open_pdf(snapshot) as doc:
        if any(not 0 <= n < len(doc) for n in pages):
            raise DocumentError('Página inexistente.')
        for number in pages:
            page = doc[number]
            page.set_rotation(0)
            found = False
            font_cache = {}
            for block in page.get_text('dict', flags=f.TEXTFLAGS_TEXT, sort=True)['blocks']:
                for line in block.get('lines', []):
                    for spans in contiguous_groups(line):
                        original = ''.join(s['text'] for s in spans)
                        characters += len(original)
                        found |= bool(original.strip())
                        if characters > 2_000_000:
                            raise DocumentError('Demasiado texto; reduce las páginas de búsqueda.')
                        hits = list(regex.finditer(original))
                        if not hits:
                            continue
                        if len(matches) + len(hits) > 500:
                            raise DocumentError('Más de 500 coincidencias; limita la búsqueda.')
                        box = region_box(page, spans)
                        reason, rows = protected, []
                        if not reason:
                            try:
                                _, rows = styled_model(doc, number, box, font_cache)
                            except DocumentError as exc:
                                reason = str(exc)
                        parts, offset = [], 0
                        for span in spans:
                            candidates = [r for r in rows if r['text'] == span['text'] and r['font'] == span['font'] and all(abs(a-b) < .01 for a, b in zip(r['origin'], span['origin']))]
                            row = candidates[0] if len(candidates) == 1 else None
                            parts.append({'id': row['id'] if row else None, 'text': span['text'], 'start': offset, 'end': offset + len(span['text']), 'editable': bool(row and row['editable']), 'reason': row['reason'] if row else 'Fragmento ambiguo o no compatible.'})
                            offset += len(span['text'])
                        for hit in hits:
                            touched = [p for p in parts if p['end'] > hit.start() and p['start'] < hit.end()]
                            failure = reason or next((p['reason'] for p in touched if not p['editable']), '')
                            identity = f'{number}:{spans[0]["origin"]}:{original}:{hit.start()}:{hit.end()}'
                            matches.append({'id': digest((receipt + identity).encode())[:24], 'page': number, 'text': hit[0], 'context': original, 'start': hit.start(), 'end': hit.end(), 'box': box, 'origin': list(spans[0]['origin']), 'font': spans[0]['font'], 'parts': parts, 'split': len(touched) > 1, 'editable': not failure, 'reason': failure})
            if not found:
                empty.append(number)
    return {'receipt': receipt, 'matches': matches, 'empty_pages': empty, 'limits': {'matches': 100, 'runs': 100}, 'scope': 'Fragmentos contiguos de una misma línea digital; conserva el estilo de cada fragmento. No cruza líneas ni reconoce escaneados.'}


def plan_token(receipt, selected, replacement):
    return digest(json.dumps([receipt, sorted(selected), replacement], ensure_ascii=True).encode())


def changes_for_group(parts, hits, replacement):
    """Distribute by original character counts, keeping each run's style.

    Extra characters go into the last touched run. Prefixes and suffixes outside
    matches remain in their original run and position.
    """
    values = {p['start']: p['text'] for p in parts}
    for hit in sorted(hits, key=lambda h: h['start'], reverse=True):
        touched = [p for p in parts if p['end'] > hit['start'] and p['start'] < hit['end']]
        remaining = replacement
        for index, part in enumerate(touched):
            start = max(hit['start'], part['start']) - part['start']
            end = min(hit['end'], part['end']) - part['start']
            chunk = remaining if index == len(touched)-1 else remaining[:end-start]
            remaining = remaining[len(chunk):]
            values[part['start']] = values[part['start']][:start] + chunk + values[part['start']][end:]
    return [{'id': p['id'], 'text': values[p['start']]} for p in parts if values[p['start']] != p['text']]


def replace(base, ops, query, receipt, selected, replacement):
    if not isinstance(selected, list) or not 1 <= len(selected) <= 100 or any(not isinstance(i, str) for i in selected) or len(set(selected)) != len(selected):
        raise DocumentError('Selecciona hasta 100 coincidencias distintas.')
    if not isinstance(replacement, str) or len(replacement) > 1000 or any(ord(c) < 32 or ord(c) == 127 for c in replacement):
        raise DocumentError('Reemplazo de hasta 1000 caracteres, sin controles.')
    inspection = inspect(base, ops, query)
    if receipt != inspection['receipt']:
        raise DocumentError('El documento o la búsqueda cambió. Vuelve a buscar.')
    model = {m['id']: m for m in inspection['matches']}
    groups = defaultdict(list)
    for identity in selected:
        if identity not in model:
            raise DocumentError('Coincidencia inexistente.')
        match = model[identity]
        if not match['editable']:
            raise DocumentError(match['reason'])
        groups[(match['page'], tuple(match['box']))].append(match)
    regions, count = [], 0
    for (page, box), hits in groups.items():
        changes = changes_for_group(hits[0]['parts'], hits, replacement)
        if changes:
            regions.append({'page': page, 'box': list(box), 'changes': changes})
            count += sum(h['text'] != replacement for h in hits)
    if not regions:
        raise DocumentError('El reemplazo no produce cambios.')
    result = replace_styled_regions(base, ops, regions)
    return result, plan_token(receipt, selected, replacement), count
