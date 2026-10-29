"""Native centreline geometry, independent of annotation borders and arrow heads."""
import pymupdf as fitz
import math
from .engine import DocumentError, finite

PATH_TYPES = {fitz.PDF_ANNOT_INK, fitz.PDF_ANNOT_LINE}


def line_translation(page,annot,points):
    original=visible_paths(page,annot)[0]
    delta=[points[0][i]-original[0][i] for i in [0,1]]
    return delta if all(abs(points[1][i]-original[1][i]-delta[i])<=.001 for i in [0,1]) else None


def prepare_line_points(doc,page,annot,points):
    if (annot.type[0]!=fitz.PDF_ANNOT_LINE or not isinstance(points,list) or len(points)!=2
            or any(not isinstance(p,list) or len(p)!=2 or any(not finite(v) for v in p) for p in points)):
        raise DocumentError('La línea requiere dos extremos con coordenadas válidas.')
    if any(not page.rect.contains(fitz.Point(p)) for p in points):
        raise DocumentError('Los extremos deben permanecer dentro de la página.')
    translation=line_translation(page,annot,points)
    if math.dist(*points)<1 and translation is None:
        raise DocumentError('Conserva al menos 1 punto de longitud entre extremos.')
    if translation is None:
        verify_standard_appearance(doc,page,annot)


def apply_line_points(page,annot,points):
    delta=line_translation(page,annot,points)
    if delta is not None:
        box=path_box(page,annot)
        apply_path_rect(page,annot,[v+delta[i%2] for i,v in enumerate(box)])
        return
    rotation=page.rotation
    try:
        if rotation:page.set_rotation(0)
        inverse=~page.transformation_matrix
    finally:
        if rotation:page.set_rotation(rotation)
    values=[]
    for point in points:
        p=fitz.Point(point)*page.derotation_matrix*inverse
        values.extend([format(p.x,'.9g'),format(p.y,'.9g')])
    page.parent.xref_set_key(annot.xref,'L','['+' '.join(values)+']')
    updated=page.load_annot(annot.xref);updated.update()
    if not page.rect.contains(updated.rect*page.rotation_matrix):
        raise DocumentError('La punta o el borde de la línea sale de la página.')


def native_paths(annot):
    vertices = annot.vertices
    return vertices if annot.type[0] == fitz.PDF_ANNOT_INK else [vertices]


def visible_paths(page, annot):
    return [[[p.x, p.y] for point in path for p in [fitz.Point(point)*page.rotation_matrix]]
            for path in native_paths(annot)]


def path_box(page, annot):
    points = [p for path in visible_paths(page, annot) for p in path]
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def resized_path(original, target):
    return any(abs((target[i+2]-target[i])-(original[i+2]-original[i])) > .001 for i in [0, 1])


def prepare_path_rect(doc, page, annot, target):
    if not isinstance(target, list) or len(target) != 4 or any(not finite(v) for v in target):
        raise DocumentError('La caja del trazado requiere cuatro coordenadas válidas.')
    original = path_box(page, annot)
    if (target[0] < 0 or target[1] < 0 or target[2] > page.rect.width or target[3] > page.rect.height
            or target[2] < target[0] or target[3] < target[1]):
        raise DocumentError('El trazado debe permanecer dentro de la página.')
    for axis in [0, 1]:
        old, new = original[axis+2]-original[axis], target[axis+2]-target[axis]
        if old == 0:
            if abs(new) > .001:
                raise DocumentError('Una línea horizontal o vertical conserva su dimensión cero.')
        elif abs(new-old) > .001 and new < 1:
            raise DocumentError('Conserva al menos 1 punto en cada dimensión del trazado.')
    if resized_path(original, target):
        verify_standard_appearance(doc, page, annot)


def verify_standard_appearance(doc, page, annot):
    # Regeneration must reproduce the visible source before it is allowed to
    # resize it. This rejects custom appearances instead of silently discarding
    # extra symbols, captions or graphics. Only one page is copied on apply.
    if annot.rect.width*annot.rect.height*4 > 4_000_000:
        raise DocumentError('La marca supera 4 millones de píxeles de comprobación; solo se puede mover.')
    try:
        order = [a.xref for a in page.annots() or []].index(annot.xref)
        with fitz.open() as probe:
            probe.insert_pdf(doc, from_page=page.number, to_page=page.number, annots=True, widgets=False)
            p = probe[0]
            items = list(p.annots() or [])
            if order >= len(items):
                raise DocumentError('No se pudo comprobar la apariencia de esta marca.')
            candidate = items[order]
            if candidate.type != annot.type or candidate.vertices != annot.vertices:
                raise DocumentError('No se pudo identificar la marca para comprobar su apariencia.')
            before_box = tuple(candidate.rect)
            before = candidate.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=True)
            candidate.update()
            after = candidate.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=True)
            if (any(abs(a-b) > .001 for a, b in zip(before_box, candidate.rect))
                    or (before.width, before.height) != (after.width, after.height)
                    or before.samples != after.samples):
                raise DocumentError('Esta apariencia personalizada no se redimensiona con fidelidad. Puedes moverla conservando su aspecto.')
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError('No se pudo comprobar la apariencia; conserva su tamaño y mueve la marca.') from exc


def apply_path_rect(page, annot, target):
    original = path_box(page, annot)
    dx, dy = target[0]-original[0], target[1]-original[1]
    scaling = resized_path(original, target)
    rotation = page.rotation
    try:
        if rotation: page.set_rotation(0)
        inverse = ~page.transformation_matrix
    finally:
        if rotation: page.set_rotation(rotation)
    paths = visible_paths(page, annot)
    def mapped(path):
        values = []
        for point in path:
            visible = ([point[0]+dx,point[1]+dy] if not scaling else
                       [target[i]+(point[i]-original[i])*(target[i+2]-target[i])/(original[i+2]-original[i])
                        if original[i+2]!=original[i] else target[i] for i in [0, 1]])
            p = fitz.Point(visible)*page.derotation_matrix*inverse
            values.extend([format(p.x, '.9g'), format(p.y, '.9g')])
        return '['+' '.join(values)+']'
    key = 'InkList' if annot.type[0] == fitz.PDF_ANNOT_INK else 'L'
    value = '['+' '.join(mapped(path) for path in paths)+']' if key == 'InkList' else mapped(paths[0])
    doc, xref = page.parent, annot.xref
    doc.xref_set_key(xref, key, value)
    if not scaling:
        # A translation keeps the complete original appearance stream, just as
        # the existing Rect-based move. Native point origins include CropBox.
        delta = fitz.Point(dx, dy)*page.derotation_matrix-fitz.Point(0, 0)*page.derotation_matrix
        raw = list(map(float, doc.xref_get_key(xref, 'Rect')[1].strip('[]').split()))
        raw = [raw[0]+delta.x, raw[1]-delta.y, raw[2]+delta.x, raw[3]-delta.y]
        doc.xref_set_key(xref, 'Rect', '['+' '.join(map(str, raw))+']')
    else:
        annot = page.load_annot(xref)
        annot.update()
    annot = page.load_annot(xref)
    if not page.rect.contains(annot.rect*page.rotation_matrix):
        raise DocumentError('El borde o la punta de flecha sale de la página. Reduce o desplaza el trazado.')
    return scaling
