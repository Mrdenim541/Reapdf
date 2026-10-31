"""Reviewed collection schema authoring with conservative removal and stable IDs."""
from uuid import uuid4
import re
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .portfolio_metadata import schema,native
from .embedded_files import normalize

TYPES={'text':'S','number':'N','date':'D'}


def prune_sort(n,pdf,collection,removed):
    sort=n.pdf_dict_gets(collection,'Sort')
    if not removed or n.pdf_is_null(sort):return
    keys={n.pdf_to_name(n.pdf_dict_get_key(sort,i)) for i in range(n.pdf_dict_len(sort))}
    if not n.pdf_is_dict(sort) or not keys<={'S','A'}:raise DocumentError('La ordenación externa no permite retirar columnas de forma verificada.')
    names=n.pdf_dict_gets(sort,'S');ascending=n.pdf_dict_gets(sort,'A')
    names=[names] if n.pdf_is_name(names) else [n.pdf_array_get(names,i) for i in range(n.pdf_array_len(names))] if n.pdf_is_array(names) else []
    if not names or any(not n.pdf_is_name(v) for v in names):raise DocumentError('La ordenación del portfolio no tiene un formato compatible.')
    if n.pdf_is_array(ascending):
        if n.pdf_array_len(ascending)!=len(names) or any(not n.pdf_is_bool(n.pdf_array_get(ascending,i)) for i in range(len(names))):raise DocumentError('La dirección de ordenación no coincide con sus columnas.')
        flags=[n.pdf_to_bool(n.pdf_array_get(ascending,i)) for i in range(len(names))]
    elif n.pdf_is_null(ascending) or n.pdf_is_bool(ascending):flags=[True if n.pdf_is_null(ascending) else n.pdf_to_bool(ascending)]*len(names)
    else:raise DocumentError('La dirección de ordenación no es compatible.')
    keep=[(name,flag) for name,flag in zip(names,flags) if n.pdf_to_name(name) not in removed]
    if not keep:n.pdf_dict_dels(collection,'Sort');return
    result=n.pdf_new_dict(pdf,2);s=n.pdf_new_array(pdf,len(keep));a=n.pdf_new_array(pdf,len(keep))
    for name,flag in keep:n.pdf_array_push(s,name);n.pdf_array_push(a,n.PDF_TRUE if flag else n.PDF_FALSE)
    n.pdf_dict_puts(result,'S',s);n.pdf_dict_puts(result,'A',a);n.pdf_dict_puts(collection,'Sort',result)


def configure(base,ops,columns,reviewed=False):
    if reviewed is not True:raise DocumentError('Revisa las columnas y la retirada de sus valores antes de guardar el diseño.')
    if not isinstance(columns,list) or not 1<=len(columns)<=20:raise DocumentError('El portfolio necesita entre 1 y 20 columnas.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        old={c['id']:c for c in schema(doc)};n,pdf,old_schema=native(doc);specs=normalize(doc)
        if not specs:raise DocumentError('Añade al menos un archivo antes de diseñar el portfolio.')
        catalog=n.pdf_dict_gets(n.pdf_trailer(pdf),'Root');collection=n.pdf_dict_gets(catalog,'Collection');collection=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(collection)) if n.pdf_is_dict(collection) else n.pdf_new_dict(pdf,4)
        seen=set();labels=set();planned=[];created={}
        for row in columns:
            if not isinstance(row,dict) or set(row)!={'id','label','type'} or not isinstance(row['id'],str) or not isinstance(row['label'],str) or not isinstance(row['type'],str):raise DocumentError('Diseño de columna no válido.')
            identity=row['id'];label=row['label'].strip();kind=row['type']
            if identity in seen or not label or len(label)>100 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in label) or label.casefold() in labels:raise DocumentError('Usa identificadores únicos y nombres distintos de 1 a 100 caracteres sin controles.')
            seen.add(identity);labels.add(label.casefold())
            if identity in old:
                original=old[identity]
                if kind!=original['type']:raise DocumentError('Conserva el tipo de las columnas existentes. Crea otra columna si necesitas un tipo diferente.')
                field=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(n.pdf_dict_gets(old_schema,identity)))
            else:
                if not re.fullmatch(r'new:[A-Za-z0-9_-]{1,80}',identity) or kind not in TYPES:raise DocumentError('La columna nueva necesita un identificador temporal y un tipo de texto, número o fecha.')
                real='ReapdfColumn'+uuid4().hex;created[identity]=real;identity=real;field=n.pdf_new_dict(pdf,6)
                n.pdf_dict_puts(field,'Subtype',n.pdf_new_name(TYPES[kind]));n.pdf_dict_puts(field,'E',n.PDF_TRUE);n.pdf_dict_puts(field,'V',n.PDF_TRUE)
            n.pdf_dict_puts(field,'Type',n.pdf_new_name('CollectionField'));n.pdf_dict_puts(field,'N',n.pdf_new_text_string(label));n.pdf_dict_puts(field,'O',n.pdf_new_int(len(planned)))
            planned.append((identity,label,kind,field))
        removed=set(old)-seen
        if any(not old[key]['editable'] for key in removed):raise DocumentError('Conserva las columnas de solo lectura o no compatibles; no se retiran sus valores.')
        prune_sort(n,pdf,collection,removed)
        result=n.pdf_new_dict(pdf,len(planned))
        for identity,label,kind,field in planned:n.pdf_dict_puts(result,identity,field)
        n.pdf_dict_puts(collection,'Type',n.pdf_new_name('Collection'));n.pdf_dict_puts(collection,'Schema',result)
        if n.pdf_is_null(n.pdf_dict_gets(collection,'View')):n.pdf_dict_puts(collection,'View',n.pdf_new_name('D'))
        n.pdf_dict_puts(catalog,'Collection',collection)
        try:version=tuple(int(v) for v in doc.metadata['format'].split()[-1].split('.'))
        except (ValueError,KeyError):raise DocumentError('No se pudo comprobar la versión del PDF.') from None
        if version<(1,7):n.pdf_dict_puts(catalog,'Version',n.pdf_new_name('1.7'))
        if removed:
            names=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles/Names')
            for i,(name,spec) in enumerate(specs):
                ci=n.pdf_dict_gets(spec,'CI')
                if not n.pdf_is_dict(ci):continue
                copy=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(spec));ci=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(ci))
                for key in removed:n.pdf_dict_dels(ci,key)
                n.pdf_dict_puts(copy,'CI',ci);n.pdf_array_put(names,i*2+1,copy)
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as saved:
        actual=schema(saved)
        if [(r['id'],r['label'],r['type']) for r in actual]!=[(identity,label,kind) for identity,label,kind,_ in planned]:raise DocumentError('La comprobación del diseño no coincide con las columnas guardadas.')
    return data,{'columns':len(planned),'created':created,'removed':sorted(removed),'attachment_bytes_modified':False}
