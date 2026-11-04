"""Copy-on-write Table/Scope attributes for existing standard header tags."""
import pymupdf as f
from .engine import DocumentError


def attributes(doc,identity):
    n=f.mupdf;pdf=f._as_pdf_document(doc);node=n.pdf_load_object(pdf,identity);raw=n.pdf_dict_gets(node,'A')
    if n.pdf_is_null(raw):return n,pdf,node,None,[]
    parts=[n.pdf_array_get(raw,i) for i in range(n.pdf_array_len(raw))] if n.pdf_is_array(raw) else [raw]
    if len(parts)>20:raise DocumentError('La etiqueta tiene demasiados atributos.')
    table=None;previous_dict=False
    for i,part in enumerate(parts):
        if n.pdf_is_int(part) and previous_dict and n.pdf_to_int(part)>=0:previous_dict=False;continue
        if not n.pdf_is_dict(part):raise DocumentError('Los atributos de la cabecera no tienen un formato compatible.')
        previous_dict=True;owner=n.pdf_dict_gets(part,'O')
        if not n.pdf_is_name(owner):raise DocumentError('Un atributo no declara su propietario.')
        if n.pdf_to_name(owner)=='Table':
            if table is not None:raise DocumentError('La cabecera contiene atributos Table repetidos.')
            table=i
    return n,pdf,node,table,parts


def info(doc,identity):
    try:
        n,_,_,index,parts=attributes(doc,identity)
        scope=n.pdf_dict_gets(parts[index],'Scope') if index is not None else None
        if scope is not None and not n.pdf_is_null(scope) and (not n.pdf_is_name(scope) or n.pdf_to_name(scope) not in ['Row','Column','Both']):raise DocumentError('El alcance existente requiere otro tratamiento.')
        if doc.xref_get_key(identity,'NS')[0]!='null':raise DocumentError('El espacio de nombres necesita revisión especializada.')
        return {'scope':n.pdf_to_name(scope) if scope is not None and n.pdf_is_name(scope) else '', 'can_scope':True,'scope_reason':''}
    except DocumentError as e:return {'scope':'','can_scope':False,'scope_reason':str(e)}


def set_scope(doc,identity,scope):
    if scope not in ['Row','Column','Both'] or not info(doc,identity)['can_scope']:raise DocumentError('Elige un alcance de fila, columna o ambos para una cabecera compatible.')
    n,pdf,node,index,parts=attributes(doc,identity)
    table=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(parts[index])) if index is not None else n.pdf_new_dict(pdf,2)
    n.pdf_dict_puts(table,'O',n.pdf_new_name('Table'));n.pdf_dict_puts(table,'Scope',n.pdf_new_name(scope))
    if not parts:n.pdf_dict_puts(node,'A',table)
    elif len(parts)==1 and index==0:n.pdf_dict_puts(node,'A',table)
    else:
        output=n.pdf_new_array(pdf,len(parts)+1)
        for i,part in enumerate(parts):n.pdf_array_push(output,table if i==index else part)
        if index is None:n.pdf_array_push(output,table)
        n.pdf_dict_puts(node,'A',output)
