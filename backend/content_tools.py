"""Cajas de texto nuevas, sellos estándar y enlaces en coordenadas visibles."""
from urllib.parse import urlsplit
import pymupdf as fitz
from .engine import DocumentError, finite
from .text_style import FONT_OPTIONS

STAMP_OPTIONS = {'approved': (fitz.STAMP_Approved, 'Aprobado / APPROVED'),
                 'draft': (fitz.STAMP_Draft, 'Borrador / DRAFT'),
                 'confidential': (fitz.STAMP_Confidential, 'Confidencial / CONFIDENTIAL'),
                 'not_approved': (fitz.STAMP_NotApproved, 'No aprobado / NOT APPROVED')}


def visible_box(page, op):
    points = op.get('points')
    if not isinstance(points, list) or len(points) != 2 or any(not isinstance(p, list) or len(p) != 2 or not all(finite(v) for v in p) for p in points):
        raise DocumentError('Define una caja con dos esquinas válidas.')
    rect = fitz.Rect(*points[0], *points[1])
    if rect.width < 5 or rect.height < 5 or not page.rect.contains(rect):
        raise DocumentError('La caja debe medir al menos 5 × 5 puntos y quedar dentro de la página.')
    return rect


def text_color(value):
    if not isinstance(value, list) or len(value) != 3 or any(not finite(c) or not 0 <= c <= 1 for c in value):
        raise DocumentError('Color no válido.')
    return value


def safe_web_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value:
        raise DocumentError('Escribe una dirección http:// o https:// completa, sin espacios.')
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {'https', 'http'} or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.port == 0:
            raise ValueError()
    except ValueError as exc:
        raise DocumentError('Solo se admiten enlaces web HTTP/HTTPS sin credenciales.') from exc
    return value


def prepare_content(doc, page, op):
    box = visible_box(page, op)
    kind = op['type']
    if kind == 'textbox':
        text, font, size, align = op.get('text'), op.get('font', 'helv'), op.get('size', 12), op.get('align', 0)
        if not isinstance(text, str) or not text.strip() or len(text) > 2000 or any((ord(c) < 32 and c != '\n') or ord(c) > 255 for c in text):
            raise DocumentError('Usa entre 1 y 2000 caracteres latinos; se admiten saltos de línea.')
        if not isinstance(font, str) or font not in dict(FONT_OPTIONS) or not finite(size) or not 6 <= size <= 144:
            raise DocumentError('Elige una fuente base y un tamaño entre 6 y 144 puntos.')
        if type(align) is not int or align not in {0, 1, 2}:
            raise DocumentError('Alineación de texto no válida.')
        color = text_color(op.get('color'))
        layout = fitz.Rect(box.x0, box.y0+size*.2, box.x1, box.y1-size*.2)
        if layout.height <= 0:
            raise DocumentError('La caja es demasiado baja para ese tamaño de texto.')
        with fitz.open() as probe:
            p = probe.new_page(width=page.rect.width, height=page.rect.height)
            if p.insert_textbox(layout, text, fontname=font, fontsize=size, color=color, align=align) < -1e-5:
                raise DocumentError('El texto no cabe en la caja. Amplíala, acorta el texto o reduce su tamaño.')
            # PDF floats can exceed a right-aligned edge by a few millionths of a point.
            checked_box = box + (-.001, -.001, .001, .001)
            if any(not checked_box.contains(fitz.Rect(s['bbox'])) for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']):
                raise DocumentError('El texto no cabe completamente en la caja.')
        return {'box': layout, 'text': text, 'font': font, 'size': size, 'color': color, 'align': align}
    if kind == 'stamp':
        choice = op.get('stamp')
        if not isinstance(choice, str) or choice not in STAMP_OPTIONS:
            raise DocumentError('Elige un sello estándar compatible.')
        if page.rotation:
            raise DocumentError('Los sellos nuevos requieren una página sin giro. Vuelve a 0° en Organizar páginas.')
        if box.width < 40 or box.height < 15:
            raise DocumentError('El sello necesita al menos 40 × 15 puntos.')
        return {'box': box, 'stamp': STAMP_OPTIONS[choice][0], 'label': STAMP_OPTIONS[choice][1], 'color': text_color(op.get('color'))}
    if op.get('destination') == 'web':
        return {'box': box, 'kind': fitz.LINK_URI, 'uri': safe_web_url(op.get('url'))}
    if op.get('destination') == 'page':
        target = op.get('target_page')
        if type(target) is not int or not 0 <= target < len(doc):
            raise DocumentError('Selecciona una página de destino válida.')
        return {'box': box, 'kind': fitz.LINK_GOTO, 'page': target, 'to': fitz.Point(0,0) * doc[target].derotation_matrix}
    raise DocumentError('Selecciona un destino web o una página.')


def add_content(page, kind, payload):
    if kind == 'stamp':
        annot = page.add_stamp_annot(payload['box'], stamp=payload['stamp'])
        annot.set_info(title='Reapdf', content=payload['label'])
        annot.set_colors(stroke=payload['color']); annot.update()
        # La apariencia estándar conserva su proporción dentro de la caja elegida.
        return
    rotation = page.rotation
    box = payload['box'] * page.derotation_matrix
    try:
        page.set_rotation(0)
        if kind == 'textbox':
            remaining = page.insert_textbox(box, payload['text'], fontname=payload['font'], fontsize=payload['size'],
                                           color=payload['color'], align=payload['align'], rotate=rotation, overlay=True)
            if remaining < -1e-5:
                raise DocumentError('No se pudo ajustar todo el texto. Amplía su caja.')
        else:
            link = {key: value for key, value in payload.items() if key != 'box'}
            page.insert_link({'from': box, **link})
    finally:
        page.set_rotation(rotation)


def page_links(page):
    items = []
    links = page.get_links()
    for link in links[:2000]:
        box = link['from']
        if not page.rect.intersects(box):
            continue
        if link['kind'] == fitz.LINK_URI:
            try:url = safe_web_url(link.get('uri'))
            except DocumentError:continue
            items.append({'box': list(box), 'destination': 'web', 'url': url})
        elif link['kind'] == fitz.LINK_GOTO and 0 <= link.get('page', -1) < len(page.parent):
            items.append({'box': list(box), 'destination': 'page', 'target_page': link['page']})
    return {'links': items, 'links_truncated': len(links) > 2000}
