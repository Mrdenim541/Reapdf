"""Edit native web / internal links without replacing unrelated annotation keys."""
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .content_tools import safe_web_url
from .form_structure import pdf_string
from .existing_annotations import LOCKED


def link_model(doc,number):
    if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página de enlace no válida.')
    page=doc[number];items=[];links=page.get_links()
    for link in links[:2000]:
        xref=link.get('xref',0);kind=link.get('kind');reason='';row={'xref':xref,'box':list(link['from'])}
        if doc.get_sigflags()>0 or not doc.permissions&f.PDF_PERM_MODIFY:reason='El documento no permite modificar enlaces.'
        elif not xref:reason='El enlace no tiene una identidad nativa editable.'
        elif any(doc.xref_get_key(xref,key)[0]!='null' for key in ['AA','OC','IRT','Popup']):reason='El enlace contiene acciones adicionales, capas o relaciones no compatibles.'
        elif doc.xref_get_key(xref,'F')[0]=='int' and int(doc.xref_get_key(xref,'F')[1])&LOCKED:reason='El enlace está bloqueado o es de solo lectura.'
        if kind==f.LINK_URI:
            row['destination']='web';row['url']=link.get('uri','')
            try:safe_web_url(row['url'])
            except DocumentError:reason=reason or 'El destino web no es compatible con HTTP/HTTPS.'
            if doc.xref_get_key(xref,'A/Next')[0]!='null':reason=reason or 'El enlace encadena acciones no compatibles.'
        elif kind==f.LINK_GOTO and type(link.get('page')) is int and 0<=link['page']<len(doc):
            row.update(destination='page',target_page=link['page'])
            if doc.xref_get_key(xref,'A/Next')[0]!='null':reason=reason or 'El enlace encadena acciones no compatibles.'
        else:row['destination']='unsupported';reason=reason or 'Destino externo, nombrado o de acción no compatible.'
        if not page.rect.contains(f.Rect(row['box'])):reason=reason or 'El enlace queda fuera de la página visible.'
        row.update(editable=not reason,reason=reason);items.append(row)
    return {'links':items,'truncated':len(links)>2000}


def inspect_links(base,operations,number):
    with open_pdf(export_pdf(base,operations)) as doc:return link_model(doc,number)


def pdf_rectangle(page,box):
    native=box*page.derotation_matrix;rotation=page.rotation
    try:
        page.set_rotation(0)
        return native*~page.transformation_matrix
    finally:page.set_rotation(rotation)


def edit_link(base,operations,number,xref,action,changes=None):
    if type(xref) is not int or action not in ['update','delete']:raise DocumentError('Enlace u operación no válidos.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        model=link_model(doc,number)
        if model['truncated']:raise DocumentError('La página supera el límite de 2000 enlaces para editar.')
        rows=model['links'];row=next((r for r in rows if r['xref']==xref),None)
        if not row or not row['editable']:raise DocumentError(row['reason'] if row else 'El enlace no pertenece a esta página de la versión actual.')
        page=doc[number]
        if action=='delete':
            if changes not in [None,{}]:raise DocumentError('No mezcles eliminación con cambios de propiedades.')
            native=next(v for v in page.get_links() if v['xref']==xref);page.delete_link(native)
        else:
            if not isinstance(changes,dict) or not changes or set(changes)-{'box','destination','url','target_page'}:raise DocumentError('Indica propiedades de enlace compatibles.')
            if 'box' in changes:
                box=changes['box']
                if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Área de enlace no válida.')
                rect=f.Rect(box)
                if min(rect.width,rect.height)<5 or not page.rect.contains(rect):raise DocumentError('El área debe medir al menos 5 × 5 pt y quedar dentro de la página.')
                raw=pdf_rectangle(page,rect);doc.xref_set_key(xref,'Rect','['+' '.join(str(v) for v in raw)+']')
            if any(key in changes for key in ['destination','url','target_page']):
                destination=changes.get('destination')
                if destination=='web' and set(changes)-{'box','destination','url'}==set():
                    url=safe_web_url(changes.get('url'));doc.xref_set_key(xref,'Dest','null');doc.xref_set_key(xref,'A','<< /S /URI /URI '+pdf_string(url)+' >>')
                elif destination=='page' and set(changes)-{'box','destination','target_page'}==set():
                    target=changes.get('target_page')
                    if type(target) is not int or not 0<=target<len(doc):raise DocumentError('Página de destino no válida.')
                    doc.xref_set_key(xref,'A','null');doc.xref_set_key(xref,'Dest',f'[{doc[target].xref} 0 R /Fit]')
                else:raise DocumentError('Selecciona un destino web o una página sin propiedades contradictorias.')
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    with open_pdf(data) as check:
        output=link_model(check,number)['links']
        if len(output)!=len(rows)-(action=='delete'):raise DocumentError('No se pudo verificar la modificación del enlace.')
        if action=='update':
            updated=output[rows.index(row)]
            if 'box' in changes and any(abs(a-b)>.01 for a,b in zip(updated['box'],changes['box'])):raise DocumentError('No se pudo conservar el área solicitada del enlace.')
            if 'destination' in changes and (updated['destination']!=changes['destination'] or any(updated.get(k)!=changes[k] for k in ['url','target_page'] if k in changes)):raise DocumentError('No se pudo conservar el destino solicitado del enlace.')
    return data
