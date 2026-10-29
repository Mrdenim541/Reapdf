"""Índice editable de destinos internos directos; conserva estilos y puntos."""
import re
import pymupdf as fitz
from .engine import DocumentError, finite

MAX_BOOKMARKS = 2000
MAX_LEVEL = 10


def bookmark_model(doc):
    toc = doc.get_toc(False)
    reason = ''
    if len(toc) > MAX_BOOKMARKS:
        reason = 'El índice supera 2000 marcadores; se conserva para lectura.'
    items = []
    for row in toc[:MAX_BOOKMARKS]:
        level, title, number, details = row
        if details.get('kind') != fitz.LINK_GOTO or not 1 <= number <= len(doc) or not 1 <= level <= MAX_LEVEL:
            reason = 'El índice contiene destinos especiales o niveles no compatibles; no se reemplazará.'
        # get_toc normalizes Fit/named/null-coordinate destinations and drops
        # chained actions. Editing those would change their behavior silently.
        xref=details.get('xref',0)
        destination=doc.xref_get_key(xref,'A/D') if xref else ('null','null')
        if destination[0]=='null' and xref:destination=doc.xref_get_key(xref,'Dest')
        xyz=r'\[\s*\d+\s+\d+\s+R\s*/XYZ\s+[-+0-9.]+\s+[-+0-9.]+\s+[-+0-9.]+\s*\]'
        if not re.fullmatch(xyz,destination[1]) or doc.xref_get_key(xref,'A/Next')[0]!='null' or doc.xref_get_key(xref,'AA')[0]!='null':
            reason='El índice contiene destinos especiales o acciones no compatibles; se conserva para lectura.'
        target = details.get('to', fitz.Point(0,0))
        items.append({'level': level, 'title': title, 'page': number-1,
                      'to': [target.x,target.y] if isinstance(target,fitz.Point) else [0,0],
                      'zoom': details.get('zoom',0), 'bold': bool(details.get('bold',False)),
                      'italic': bool(details.get('italic',False)), 'collapse': bool(details.get('collapse',False)),
                      'color': list(details.get('color',(0,0,0)))})
    return {'items': items, 'editable': not reason and doc.get_sigflags()<=0 and bool(doc.permissions & fitz.PDF_PERM_MODIFY),
            'reason': reason or ('El documento está firmado o no permite modificar el índice.' if doc.get_sigflags()>0 or not doc.permissions & fitz.PDF_PERM_MODIFY else '')}


def prepare_bookmarks(doc, items):
    model = bookmark_model(doc)
    if not model['editable']:
        raise DocumentError(model['reason'])
    if not isinstance(items,list) or len(items)>MAX_BOOKMARKS:
        raise DocumentError('El índice admite hasta 2000 marcadores.')
    result=[];previous=0
    for item in items:
        if not isinstance(item,dict):raise DocumentError('Marcador no válido.')
        level,title,number=item.get('level'),item.get('title'),item.get('page')
        if type(level) is not int or not 1<=level<=MAX_LEVEL or level>previous+1:
            raise DocumentError('El índice debe empezar en nivel 1 y avanzar de un nivel en uno.')
        if not isinstance(title,str) or not 1<=len(title.strip())<=300 or any(ord(c)<32 or ord(c)==127 for c in title):
            raise DocumentError('Cada marcador necesita un título de 1 a 300 caracteres, sin controles.')
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Destino de marcador no válido.')
        point,zoom,color=item.get('to',[0,0]),item.get('zoom',0),item.get('color',[0,0,0])
        if not isinstance(point,list) or len(point)!=2 or any(not finite(v) or abs(v)>1_000_000 for v in point):
            raise DocumentError('Punto de destino no válido.')
        if not finite(zoom) or not 0<=zoom<=64:raise DocumentError('Zoom de destino no válido.')
        if not isinstance(color,list) or len(color)!=3 or any(not finite(v) or not 0<=v<=1 for v in color):raise DocumentError('Color de marcador no válido.')
        if any(type(item.get(key,False)) is not bool for key in ['bold','italic','collapse']):raise DocumentError('Estilo de marcador no válido.')
        result.append([level,title.strip(),number+1,{'kind':fitz.LINK_GOTO,'page':number,'to':fitz.Point(*point),'zoom':zoom,
                                                  'color':color,'bold':item.get('bold',False),'italic':item.get('italic',False),
                                                  'collapse':item.get('collapse',False)}])
        previous=level
    return result


def apply_bookmarks(doc,toc):
    # Build the tree and styles, then set destinations directly. In pinned MuPDF,
    # set_toc / set_toc_item do not roundtrip visible coordinates on rotated and
    # cropped pages. PDF XYZ uses unrotated, bottom-origin coordinates.
    doc.set_toc([[level,title,page,{**details,'collapse':False}]
                 for level,title,page,details in toc],collapse=0)
    for xref,row in zip(doc.get_outline_xrefs(),toc):
        details=row[3];page=doc[row[2]-1]
        point=fitz.Point(details['to'])*page.derotation_matrix
        rotation=page.rotation
        try:
            page.set_rotation(0)
            point=point*~page.transformation_matrix
        finally:page.set_rotation(rotation)
        doc.xref_set_key(xref,'A',f"<</S/GoTo/D[{page.xref} 0 R/XYZ {point.x:.9g} {point.y:.9g} {details['zoom']:.9g}]>>")
        kind,count=doc.xref_get_key(xref,'Count')
        if kind=='int' and int(count):
            doc.xref_set_key(xref,'Count',str(-abs(int(count)) if details['collapse'] else abs(int(count))))
