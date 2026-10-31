"""Native PDF Collection dictionaries, with bounded embedded-file metadata."""
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .embedded_files import normalize
from .pro_tools import attachment_info

FIELDS={'ReapdfTitle':('Título','S',0),'ReapdfDescription':('Descripción','S',1),'ReapdfOrder':('Orden','N',2)}
VIEWS={'details':'D','tiles':'T','hidden':'H'}


def keys(obj):
    n=f.mupdf
    return {n.pdf_to_name(n.pdf_dict_get_key(obj,i)) for i in range(n.pdf_dict_len(obj))}


def supported(doc):
    n=f.mupdf;collection=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(doc)),'Root/Collection')
    if n.pdf_is_null(collection):return True
    if not n.pdf_is_dict(collection) or not keys(collection)<={'Type','Schema','Sort','View','D'}:return False
    schema=n.pdf_dict_gets(collection,'Schema')
    if not n.pdf_is_dict(schema) or not set(FIELDS)<=keys(schema) or n.pdf_dict_len(schema)>20:return False
    for key,(_,kind,_) in FIELDS.items():
        field=n.pdf_dict_gets(schema,key)
        if not n.pdf_is_dict(field) or n.pdf_to_name(n.pdf_dict_gets(field,'Subtype'))!=kind:return False
    return True


def model(base):
    with open_pdf(base) as doc:
        specs=normalize(doc);n=f.mupdf;collection=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(doc)),'Root/Collection');enabled=not n.pdf_is_null(collection);can_configure=supported(doc);files=[]
        for index,(name,spec) in enumerate(specs):
            ci=n.pdf_dict_gets(spec,'CI');title=n.pdf_dict_gets(ci,'ReapdfTitle');description=n.pdf_dict_gets(ci,'ReapdfDescription');order=n.pdf_dict_gets(ci,'ReapdfOrder');info=attachment_info(doc,index)
            files.append({'index':index,'name':name,'filename':info.get('ufilename') or info.get('filename') or name,'size':info.get('size'),'title':n.pdf_to_text_string(title) if n.pdf_is_string(title) else name,'description':n.pdf_to_text_string(description) if n.pdf_is_string(description) else '', 'order':n.pdf_to_int(order) if n.pdf_is_int(order) else index+1})
        view=n.pdf_to_name(n.pdf_dict_gets(collection,'View')) if enabled else 'D'
        return {'enabled':enabled,'supported':can_configure,'reason':'' if can_configure else 'Este portfolio tiene un esquema externo. Puedes consultar y descargar sus adjuntos; no se reemplaza su estructura personalizada.','view':next((k for k,v in VIEWS.items() if v==view),'details'),'files':sorted(files,key=lambda r:(r['order'],r['name']))}


def configure(base,operations,enabled,view='details',files=None):
    if type(enabled) is not bool or not isinstance(view,str) or view not in VIEWS:raise DocumentError('Vista o estado de portfolio no válido.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        specs=normalize(doc)
        if not enabled:
            doc.xref_set_key(doc.pdf_catalog(),'Collection','null')
            return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        if not supported(doc):raise DocumentError('El portfolio externo tiene un esquema que no se sobrescribe automáticamente.')
        if not specs:raise DocumentError('Adjunta al menos un archivo antes de crear el portfolio.')
        if not isinstance(files,list) or len(files)!=len(specs):raise DocumentError('Revisa todos los archivos del portfolio.')
        names={name:spec for name,spec in specs};seen=set()
        for row in files:
            if not isinstance(row,dict) or set(row)!={'name','title','description'} or not isinstance(row['name'],str) or row['name'] not in names or row['name'] in seen:raise DocumentError('Los archivos del portfolio cambiaron o están repetidos.')
            seen.add(row['name'])
            for key,maximum in [('title',200),('description',1000)]:
                value=row[key]
                if not isinstance(value,str) or len(value)>maximum or key=='title' and not value.strip() or any(ord(c)<32 or ord(c)==127 for c in value):raise DocumentError('Título o descripción de portfolio no válido.')
        n=f.mupdf;pdf=f._as_pdf_document(doc)
        schema='<<'+' '.join('/'+key+' << /Type /CollectionField /N '+f.get_pdf_str(label)+f' /Subtype /{kind} /O {order} >>' for key,(label,kind,order) in FIELDS.items())+'>>'
        # Collections require PDF 1.7; do not lower a newer effective version.
        try:version=tuple(int(v) for v in doc.metadata['format'].split()[-1].split('.'))
        except (ValueError,KeyError):raise DocumentError('No se pudo determinar la versión PDF para el portfolio.')
        if version<(1,7):doc.xref_set_key(doc.pdf_catalog(),'Version','/1.7')
        if doc.xref_get_key(doc.pdf_catalog(),'Collection')[0]=='null':
            doc.xref_set_key(doc.pdf_catalog(),'Collection',f'<< /Type /Collection /View /{VIEWS[view]} /Schema {schema} /Sort << /S /ReapdfOrder /A true >> >>')
        else:
            doc.xref_set_key(doc.pdf_catalog(),'Collection/View','/'+VIEWS[view]);doc.xref_set_key(doc.pdf_catalog(),'Collection/Sort','<< /S /ReapdfOrder /A true >>')
        # xref_set_key reparses direct catalog children; reacquire file specs.
        entries=normalize(doc);names={name:(i,spec) for i,(name,spec) in enumerate(entries)}
        flat=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles/Names')
        for index,row in enumerate(files,1):
            position,spec=names[row['name']]
            # Imported portfolios can share both the FileSpec and CI objects.
            # Edit the selected entry's metadata without collapsing its peers.
            spec=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(spec));ci=n.pdf_dict_gets(spec,'CI')
            ci=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(ci)) if n.pdf_is_dict(ci) else n.pdf_new_dict(pdf,3)
            n.pdf_dict_puts(spec,'CI',ci);n.pdf_array_put(flat,position*2+1,spec)
            n.pdf_dict_puts(ci,'ReapdfTitle',n.pdf_new_text_string(row['title']));n.pdf_dict_puts(ci,'ReapdfDescription',n.pdf_new_text_string(row['description']));n.pdf_dict_puts(ci,'ReapdfOrder',n.pdf_new_int(index))
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    check=model(data)
    if not check['enabled'] or [r['name'] for r in check['files']]!=[r['name'] for r in files] or any((r['title'],r['description'])!=(v['title'],v['description']) for r,v in zip(check['files'],files)):raise DocumentError('La verificación del portfolio detectó diferencias. No se publicó el cambio.')
    return data
