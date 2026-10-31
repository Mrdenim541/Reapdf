"""Edit declared collection columns while preserving foreign schemas and attachments."""
import math,re
from datetime import datetime
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .embedded_files import normalize


def native(doc):
    n=f.mupdf;pdf=f._as_pdf_document(doc);trailer=n.pdf_trailer(pdf)
    return n,pdf,n.pdf_dict_getp(trailer,'Root/Collection/Schema')


def schema(doc):
    n,pdf,fields=native(doc)
    if n.pdf_is_null(fields):return []
    if not n.pdf_is_dict(fields) or n.pdf_dict_len(fields)>20:raise DocumentError('La consulta de columnas admite esquemas de hasta 20 campos.')
    result=[]
    for i in range(n.pdf_dict_len(fields)):
        key=n.pdf_to_name(n.pdf_dict_get_key(fields,i));field=n.pdf_dict_get_val(fields,i)
        if not key or len(key)>100 or any(ord(c)<32 for c in key) or not n.pdf_is_dict(field):raise DocumentError('El esquema contiene una columna no compatible.')
        kind=n.pdf_to_name(n.pdf_dict_gets(field,'Subtype'));label=n.pdf_to_text_string(n.pdf_dict_gets(field,'N')) or key;flag=n.pdf_dict_gets(field,'E')
        result.append({'id':key,'label':label[:200],'position':n.pdf_to_int(n.pdf_dict_gets(field,'O')) if n.pdf_is_int(n.pdf_dict_gets(field,'O')) else i,'type':{'S':'text','N':'number','D':'date'}.get(kind,'readonly'),'editable':kind in ['S','N','D'] and key!='ReapdfOrder' and (n.pdf_to_bool(flag) or key in ['ReapdfTitle','ReapdfDescription','ReapdfOrder'])})
    return sorted(result,key=lambda r:(r['position'],r['id']))


def model(base,ops=()):
    with open_pdf(export_pdf(base,list(ops))) as doc:
        columns=schema(doc);n,_,_=native(doc);files=[]
        for name,spec in normalize(doc):
            values={};prefixes={};complex_fields=[];ci=n.pdf_dict_gets(spec,'CI')
            for field in columns:
                value=n.pdf_dict_gets(ci,field['id'])
                if n.pdf_is_dict(value):
                    keys={n.pdf_to_name(n.pdf_dict_get_key(value,i)) for i in range(n.pdf_dict_len(value))}
                    if not keys<={'D','P'}:complex_fields.append(field['id']);values[field['id']]='Valor complejo';continue
                    prefixes[field['id']]=n.pdf_to_text_string(n.pdf_dict_gets(value,'P'));value=n.pdf_dict_gets(value,'D')
                if n.pdf_is_null(value):values[field['id']]=None
                elif n.pdf_is_string(value):
                    text=n.pdf_to_text_string(value);values[field['id']]=text[:2000]
                    if len(text)>2000:complex_fields.append(field['id'])
                elif n.pdf_is_int(value):values[field['id']]=n.pdf_to_int(value)
                elif n.pdf_is_real(value):values[field['id']]=n.pdf_to_real(value)
                else:values[field['id']]='Valor no editable';complex_fields.append(field['id'])
            files.append({'name':name,'values':values,'prefixes':prefixes,'protected_fields':complex_fields})
        return {'columns':columns,'files':files,'schema_preserved':True,'scope':'Columnas declaradas de texto, número y fecha con edición permitida. No sustituye el esquema ni modifica archivos incrustados. Los campos complejos o declarados de solo lectura se conservan.'}


def encoded(n,value,kind):
    if value is None:return None
    if kind=='number':
        if isinstance(value,str):
            try:value=float(value)
            except ValueError:raise DocumentError('Introduce un número válido para la columna numérica.') from None
        if type(value) not in [int,float] or not math.isfinite(value) or abs(value)>1e12:raise DocumentError('La columna numérica admite valores finitos entre −10¹² y 10¹².')
        return n.pdf_new_int(int(value)) if float(value).is_integer() else n.pdf_new_real(value)
    if not isinstance(value,str) or len(value)>2000 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value):raise DocumentError('La columna admite hasta 2000 caracteres sin controles.')
    if kind=='date':
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
            try:datetime.strptime(value,'%Y-%m-%d')
            except ValueError:raise DocumentError('Fecha no válida; usa AAAA-MM-DD.') from None
            value='D:'+value.replace('-','')
        elif re.fullmatch(r"D:\d{8}(?:\d{6}(?:Z|[+-]\d{2}'\d{2}')?)?",value):
            try:
                datetime.strptime(value[2:16] if len(value)>=16 else value[2:10],'%Y%m%d%H%M%S' if len(value)>=16 else '%Y%m%d')
                if "'" in value and (int(value[-6:-4])>23 or int(value[-3:-1])>59):raise ValueError()
            except ValueError:raise DocumentError('Fecha o zona horaria no válida.') from None
        else:raise DocumentError('Usa AAAA-MM-DD; las fechas PDF completas existentes conservan hora y zona.')
    return n.pdf_new_text_string(value)


def edit(base,ops,changes):
    with open_pdf(base) as source:editable(source)
    info=model(base,ops);fields={c['id']:c for c in info['columns']};files={r['name']:r for r in info['files']}
    if not isinstance(changes,list) or not 1<=len(changes)<=1000:raise DocumentError('Revisa entre 1 y 1000 cambios de columnas.')
    seen=set()
    with open_pdf(export_pdf(base,ops)) as doc:
        n,pdf,_=native(doc);specs=normalize(doc);names=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles/Names');copied={}
        for change in changes:
            if not isinstance(change,dict) or set(change)!={'name','field','value'} or not isinstance(change['name'],str) or not isinstance(change['field'],str):raise DocumentError('Cambio de columna no válido.')
            name,key=change['name'],change['field'];identity=(name,key)
            if identity in seen or name not in files or key not in fields or not fields[key]['editable'] or key in files[name]['protected_fields']:raise DocumentError('Columna repetida, de solo lectura o no compatible.')
            seen.add(identity);value=encoded(n,change['value'],fields[key]['type'])
            if name not in copied:
                index,spec=next((i,s) for i,(label,s) in enumerate(specs) if label==name)
                spec=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(spec));ci=n.pdf_dict_gets(spec,'CI');ci=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(ci)) if n.pdf_is_dict(ci) else n.pdf_new_dict(pdf,3)
                n.pdf_dict_puts(spec,'CI',ci);n.pdf_array_put(names,index*2+1,spec);copied[name]=ci
            ci=copied[name];old=n.pdf_dict_gets(ci,key)
            if value is None:n.pdf_dict_dels(ci,key)
            elif n.pdf_is_dict(old):
                sub=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(old));n.pdf_dict_puts(sub,'D',value);n.pdf_dict_puts(ci,key,sub)
            else:n.pdf_dict_puts(ci,key,value)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
