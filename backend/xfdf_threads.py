"""Bounded, same-page XFDF reply and review-state graphs."""
import pymupdf as f
from .engine import DocumentError

STATES={'Review':{'Accepted','Rejected','Cancelled','Completed','None'},'Marked':{'Marked','Unmarked'}}


def attributes(doc,page,a):
    from .xfdf import clean
    result={};kind,parent=doc.xref_get_key(a.xref,'IRT');rt=doc.xref_get_key(a.xref,'RT')
    if kind!='null':
        if kind!='xref' or rt not in [('null','null'),('name','/R'),('name','/Group')] or rt!=('name','/Group') and a.type[0]!=f.PDF_ANNOT_TEXT:raise DocumentError('La respuesta necesita otro intercambio.')
        target=int(parent.split()[0]);names={v.xref:v.info.get('id','') or 'reapdf-'+str(v.xref) for v in page.annots() or []}
        if target==a.xref or target not in names:raise DocumentError('La respuesta no tiene un padre único en su página.')
        result.update(inreplyto=clean(names[target],100),replyType='Group' if rt==('name','/Group') else 'R')
    elif rt[0]!='null':raise DocumentError('Tipo de respuesta sin padre.')
    model=doc.xref_get_key(a.xref,'StateModel');state=doc.xref_get_key(a.xref,'State')
    if model[0]!='null' or state[0]!='null':
        if a.type[0]!=f.PDF_ANNOT_TEXT or model[0]!='string' or state[0]!='string' or state[1] not in STATES.get(model[1],set()) or kind=='null' or rt==('name','/Group'):raise DocumentError('Estado de revisión sin respuesta o modelo compatible.')
        result.update(statemodel=model[1],state=state[1])
    return result


def ordered(nodes,existing):
    from .xfdf import clean,tag
    incoming={};result=[];pending=[]
    for node in nodes:
        try:page=int(node.get('page',''))
        except ValueError as exc:raise DocumentError('Página XFDF no válida.') from exc
        name=clean(node.get('name',''),100);parent=node.get('inreplyto');rt=node.get('replyType');model=node.get('statemodel');state=node.get('state')
        if parent is not None:
            parent=clean(parent,100)
            if not parent or not name or parent==name or rt not in [None,'R','Group'] or rt!='Group' and node.tag!=tag('text'):raise DocumentError('Respuesta XFDF sin nombre/padre válido o de tipo no compatible.')
        elif rt is not None:raise DocumentError('Tipo de respuesta sin padre XFDF.')
        if model is not None or state is not None:
            if not parent or rt=='Group' or node.tag!=tag('text') or state not in STATES.get(model,set()):raise DocumentError('Estado XFDF fuera de los modelos Review/Marked compatibles.')
        if name:
            key=(page,name)
            if key in incoming:raise DocumentError('Existe más de una anotación XFDF con el mismo nombre en el lote.')
            incoming[key]=node
        pending.append((page,name,parent,node))
    emitted=set()
    for _ in range(501):
        if not pending:return result
        ready=[v for v in pending if v[2] is None or (v[0],v[2]) in emitted or (v[0],v[2]) in existing and (v[0],v[2]) not in incoming]
        if not ready:raise DocumentError('Respuestas XFDF con ciclo o padre ausente en la misma página.')
        for page,name,parent,node in ready:
            result.append(node);emitted.add((page,name));pending.remove((page,name,parent,node))
    raise DocumentError('El hilo XFDF supera 500 respuestas.')


def apply(doc,a,node,parents,page):
    from .form_structure import pdf_string
    parent=node.get('inreplyto')
    if parent is not None:
        ref=parents.get((page,parent))
        if ref is None:raise DocumentError('No se pudo asociar el padre de la respuesta XFDF.')
        doc.xref_set_key(a.xref,'IRT',f'{ref} 0 R');doc.xref_set_key(a.xref,'RT','/Group' if node.get('replyType')=='Group' else '/R')
    for attr,key in [('statemodel','StateModel'),('state','State')]:
        if node.get(attr) is not None:doc.xref_set_key(a.xref,key,pdf_string(node.get(attr)))
