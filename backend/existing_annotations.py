"""Edición conservadora de anotaciones existentes, identificadas en la fuente."""
import pymupdf as fitz
from .engine import DocumentError, finite
from .path_geometry import path_box,visible_paths,prepare_path_rect,apply_path_rect,prepare_line_points,apply_line_points,verify_standard_appearance

SUPPORTED = {fitz.PDF_ANNOT_TEXT: 'Nota', fitz.PDF_ANNOT_INK: 'Lápiz',
             fitz.PDF_ANNOT_LINE: 'Línea/flecha', fitz.PDF_ANNOT_SQUARE: 'Rectángulo', fitz.PDF_ANNOT_CIRCLE:'Elipse',
             fitz.PDF_ANNOT_HIGHLIGHT: 'Resaltado', fitz.PDF_ANNOT_UNDERLINE: 'Subrayado',
             fitz.PDF_ANNOT_STRIKE_OUT: 'Tachado'}
LOCKED = fitz.PDF_ANNOT_IS_READ_ONLY | fitz.PDF_ANNOT_IS_LOCKED | fitz.PDF_ANNOT_IS_LOCKED_CONTENTS
MAX_LIST = 2000
PATH_TYPES = {fitz.PDF_ANNOT_INK, fitz.PDF_ANNOT_LINE}


def path_move_reason(doc, annot):
    if annot.flags & (fitz.PDF_ANNOT_IS_NO_ROTATE | fitz.PDF_ANNOT_IS_NO_ZOOM):
        return 'La geometría tiene un comportamiento especial de giro o zoom.'
    if any(doc.xref_get_key(annot.xref, key)[0] != 'null'
           for key in ['IT', 'BE', 'Measure', 'A', 'AA', 'Path']):
        return 'La geometría contiene mediciones, acciones o propiedades especiales.'
    vertices = annot.vertices
    paths = vertices if annot.type[0] == fitz.PDF_ANNOT_INK else [vertices]
    if (not paths or any(not path for path in paths)
            or sum(len(path) for path in paths) > 10000
            or any(len(point) != 2 or any(not finite(v) for v in point) for path in paths for point in path)
            or (annot.type[0] == fitz.PDF_ANNOT_LINE and len(vertices) != 2)):
        return 'El trazo requiere vértices válidos y un máximo de 10 000 puntos.'
    return ''


def can_move(doc, annot):
    return (annot.type[0] in {fitz.PDF_ANNOT_TEXT, fitz.PDF_ANNOT_SQUARE, fitz.PDF_ANNOT_CIRCLE}
            or annot.type[0] in PATH_TYPES and not path_move_reason(doc, annot))


def related_annotations(doc):
    """Proteger hilos y grupos, también si el vínculo IRT atraviesa páginas."""
    related = set()
    for page in doc:
        for xref, _, _ in page.annot_xrefs():
            kind, value = doc.xref_get_key(xref, 'IRT')
            if kind != 'null':
                related.add(xref)
                if kind == 'xref':
                    related.add(int(value.split()[0]))
    return related


def restriction(doc, annot, related):
    if doc.get_sigflags() > 0:
        return 'Documento con indicadores de firma: solo lectura.'
    if not doc.permissions & fitz.PDF_PERM_ANNOTATE:
        return 'El documento no permite modificar anotaciones.'
    if annot.type[0] not in SUPPORTED:
        return 'Este tipo de anotación todavía es de solo lectura.'
    if annot.flags & LOCKED:
        return 'La anotación está bloqueada o marcada como solo lectura.'
    if annot.xref in related:
        return 'Las conversaciones y anotaciones agrupadas todavía son de solo lectura.'
    if doc.xref_get_key(annot.xref, 'OC')[0] != 'null':
        return 'Las anotaciones asociadas a capas todavía son de solo lectura.'
    return ''


def display_rgb(color):
    if len(color) == 3:
        return list(color)
    if len(color) == 1:
        return list(color) * 3
    if len(color) == 4:
        return [1-min(1, color[i]+color[3]) for i in range(3)]
    return [0, 0, 0]


def can_resize(doc,annot):
    if annot.type[0] in PATH_TYPES:
        if path_move_reason(doc,annot):return False
        if annot.rect.width*annot.rect.height>1000000:return False
        box=path_box(annot.parent,annot)
        return box[2]>box[0] or box[3]>box[1]
    return (annot.type[0] in {fitz.PDF_ANNOT_SQUARE,fitz.PDF_ANNOT_CIRCLE} and not annot.flags&(fitz.PDF_ANNOT_IS_NO_ROTATE|fitz.PDF_ANNOT_IS_NO_ZOOM)
            and doc.xref_get_key(annot.xref,'BE')[0]=='null'
            and doc.xref_get_key(annot.xref,'IT')[0]=='null')


def list_annotations(doc, number):
    page = doc[number]
    related = related_annotations(doc)
    result = []
    preview_points = 0
    for annot in page.annots() or []:
        if len(result) == MAX_LIST:
            return {'annotations': result, 'annotations_truncated': True}
        reason = restriction(doc, annot, related)
        box = annot.rect * page.rotation_matrix
        visible = not annot.flags & (fitz.PDF_ANNOT_IS_HIDDEN | fitz.PDF_ANNOT_IS_INVISIBLE | fitz.PDF_ANNOT_IS_NO_VIEW)
        path_data = {}
        if not reason and annot.type[0] in PATH_TYPES and not path_move_reason(doc,annot):
            paths = visible_paths(page,annot)
            count = sum(len(p) for p in paths)
            path_data = {'path_rect':path_box(page,annot),'paths':paths if preview_points+count<=100000 else None}
            if annot.type[0]==fitz.PDF_ANNOT_LINE:
                path_data.update({'line_points':paths[0],'can_edit_endpoints':annot.rect.width*annot.rect.height<=1000000})
            preview_points += count
        result.append({**path_data,'xref': annot.xref, 'label': SUPPORTED.get(annot.type[0], annot.type[1]),
                       'kind': annot.type[0], 'rect': list(box), 'visible': bool(visible),
                       'content': annot.info.get('content', ''), 'author': annot.info.get('title', ''),
                       'color': display_rgb(annot.colors.get('stroke') or []),
                       'can_resize':not reason and can_resize(doc,annot),
                       'can_move': not reason and can_move(doc,annot),
                       'move_reason': path_move_reason(doc,annot) if not reason and annot.type[0] in PATH_TYPES else '',
                       'editable': not reason, 'can_edit_content': not reason and annot.type[0] == fitz.PDF_ANNOT_TEXT,
                       'reason': reason})
    return {'annotations': result, 'annotations_truncated': False}


def prepare_existing(doc, page, op, related):
    xref = op.get('xref')
    candidates = {row[0]: row[1] for row in page.annot_xrefs()}
    if type(xref) is not int or xref not in candidates:
        raise DocumentError('La anotación no pertenece a esta página de la versión original.')
    if candidates[xref] not in SUPPORTED:
        raise DocumentError('Este tipo de anotación todavía es de solo lectura.')
    try:
        annot = page.load_annot(xref)
    except Exception as exc:  # MuPDF también usa Exception genérica en esta carga nativa.
        raise DocumentError('Anotación no compatible.') from exc
    if annot is None:
        raise DocumentError('Anotación no encontrada.')
    reason = restriction(doc, annot, related)
    if reason:
        raise DocumentError(reason)
    action = op.get('action')
    if action == 'delete':
        if op.get('changes') not in (None, {}):
            raise DocumentError('No mezcles eliminación y cambios de propiedades.')
        return (xref, action, {})
    changes = op.get('changes')
    if action != 'update' or not isinstance(changes, dict) or not changes or set(changes)-{'color', 'content', 'rect','path_rect','line_points'} or len(set(changes)&{'rect','path_rect','line_points'})>1:
        raise DocumentError('Propiedades de anotación no compatibles.')
    if 'color' in changes:
        color = changes['color']
        if not isinstance(color, list) or len(color) != 3 or any(not finite(c) or not 0 <= c <= 1 for c in color):
            raise DocumentError('Color no válido.')
        if annot.type[0] in PATH_TYPES:
            verify_standard_appearance(doc,page,annot)
    if 'content' in changes:
        content = changes['content']
        if annot.type[0] != fitz.PDF_ANNOT_TEXT:
            raise DocumentError('Solo se modifica el contenido de las notas compatibles.')
        if not isinstance(content, str) or not content.strip() or len(content)>4000 or any(ord(c)<32 and c not in '\n\t' for c in content):
            raise DocumentError('La nota requiere entre 1 y 4000 caracteres sin controles.')
    if 'rect' in changes:
        box=changes['rect']
        if not can_move(doc,annot) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Solo se mueven notas, rectángulos, elipses, trazos y líneas compatibles.')
        target=fitz.Rect(box);original=annot.rect*page.rotation_matrix
        tolerance=.001 if annot.type[0] in PATH_TYPES else .05
        resized=abs(target.width-original.width)>tolerance or abs(target.height-original.height)>tolerance
        if target.is_empty or not page.rect.contains(target):raise DocumentError('La marca debe permanecer dentro de la página.')
        if resized and (annot.type[0] in PATH_TYPES or not can_resize(doc,annot) or min(target.width,target.height)<10):raise DocumentError('El rectángulo exterior solo redimensiona figuras estándar de al menos 10 × 10 pt. Para líneas y lápiz usa la caja del trazado.')
    if 'path_rect' in changes:
        if annot.type[0] not in PATH_TYPES or not can_move(doc,annot):
            raise DocumentError('Esta geometría no permite modificar la caja del trazado.')
        prepare_path_rect(doc,page,annot,changes['path_rect'])
    if 'line_points' in changes:
        if annot.type[0]!=fitz.PDF_ANNOT_LINE or not can_move(doc,annot):
            raise DocumentError('Esta marca no permite editar los extremos de la línea.')
        prepare_line_points(doc,page,annot,changes['line_points'])
    return (xref, action, changes)


def apply_existing(page, payload):
    xref, action, changes = payload
    annot = page.load_annot(xref)
    if action == 'delete':
        page.delete_annot(annot)
        return
    if 'line_points' in changes:
        apply_line_points(page,annot,changes['line_points'])
        annot=page.load_annot(xref)
        if set(changes)=={'line_points'}:return
    if 'path_rect' in changes:
        apply_path_rect(page,annot,changes['path_rect'])
        annot=page.load_annot(xref)
        if set(changes)=={'path_rect'}:
            return
    if 'rect' in changes:
        native=fitz.Rect(changes['rect'])*page.derotation_matrix
        if annot.type[0] in PATH_TYPES:
            # Translate the native path and its Rect together. Keep the appearance
            # stream intact for a pure move, including custom line endings/styles.
            delta=fitz.Point(native.x0-annot.rect.x0,native.y0-annot.rect.y0)
            # MuPDF's page matrix on rotated cropped pages omits the crop
            # translation. Read it in the unrotated coordinate system and restore
            # the page before touching either the path or the appearance.
            rotation=page.rotation
            try:
                if rotation:page.set_rotation(0)
                inverse=~page.transformation_matrix
            finally:
                if rotation:page.set_rotation(rotation)
            def pdf_path(points):
                values=[]
                for point in points:
                    p=(fitz.Point(point)+delta)*inverse
                    values.extend([format(p.x,'.9g'),format(p.y,'.9g')])
                return '['+' '.join(values)+']'
            vertices=annot.vertices
            key='InkList' if annot.type[0]==fitz.PDF_ANNOT_INK else 'L'
            value='['+' '.join(pdf_path(path) for path in vertices)+']' if key=='InkList' else pdf_path(vertices)
            page.parent.xref_set_key(xref,key,value)
        if annot.type[0] in {fitz.PDF_ANNOT_TEXT,fitz.PDF_ANNOT_SQUARE,fitz.PDF_ANNOT_CIRCLE} | PATH_TYPES:
            # Adjust the raw PDF Rect: set_rect re-applies square borders
            # and adjusts NoRotate note icons, changing their visible boxes.
            original=annot.rect
            doc=page.parent;raw=doc.xref_get_key(xref,'Rect')[1]
            coords=list(map(float,raw.strip('[]').split()))
            coords=[coords[0]+native.x0-original.x0,coords[1]-native.y1+original.y1,coords[2]+native.x1-original.x1,coords[3]-native.y0+original.y0]
            doc.xref_set_key(xref,'Rect','['+' '.join(map(str,coords))+']')
            annot=page.load_annot(xref)
        else:annot.set_rect(native)
        if annot.type[0] in PATH_TYPES and set(changes)=={'rect'}:
            return
    if 'color' in changes:
        annot.set_colors(stroke=changes['color'])
    if 'content' in changes:
        annot.set_info(content=changes['content'])
    annot.update()
