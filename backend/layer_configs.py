"""Read and select native OCG configurations without flattening their content."""
import pymupdf as f
from .engine import DocumentError


def collection(doc):
    n=f.mupdf;root=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(doc)),'Root/OCProperties')
    return n,root,n.pdf_dict_gets(root,'Configs')


def describe(doc):
    n,root,configs=collection(doc);known=set(doc.get_ocgs());result=[]
    if n.pdf_array_len(configs)>50:raise DocumentError('Hasta 50 configuraciones de capas por documento.')
    def refs(value):
        if not n.pdf_is_null(value) and not n.pdf_is_array(value) or n.pdf_array_len(value)>200:raise DocumentError('La configuración contiene una lista de capas no compatible.')
        return [n.pdf_to_num(n.pdf_array_get(value,i)) for i in range(n.pdf_array_len(value))]
    for index in range(n.pdf_array_len(configs)):
        config=n.pdf_array_get(configs,index);keys={n.pdf_to_name(n.pdf_dict_get_key(config,i)) for i in range(n.pdf_dict_len(config))}
        on=refs(n.pdf_dict_gets(config,'ON'));off=refs(n.pdf_dict_gets(config,'OFF'));locked=refs(n.pdf_dict_gets(config,'Locked'));groups=n.pdf_dict_gets(config,'RBGroups');radio=[refs(n.pdf_array_get(groups,i)) for i in range(n.pdf_array_len(groups))]
        base=n.pdf_to_name(n.pdf_dict_gets(config,'BaseState')) or 'ON';enabled=n.pdf_is_dict(config) and keys<={'Name','Creator','BaseState','ON','OFF','Locked','RBGroups','Order','Intent','ListMode'} and base in ['ON','OFF'] and all(v in known for v in on+off+locked+sum(radio,[])) and not set(on)&set(off)
        name=n.pdf_to_text_string(n.pdf_dict_gets(config,'Name')) or f'Configuración {index+1}'
        visible=sorted(set(on)|(known-set(off) if base=='ON' else set()))
        if any(len(set(group)&set(visible))>1 for group in radio):enabled=False
        result.append({'id':index,'name':name[:200],'supported':enabled,'visible':visible,'locked':locked,'radio_groups':radio,'reason':'' if enabled else 'Configuración con reglas automáticas o estructura no compatible; se conserva sin reemplazar.'})
    return result


def select(doc,index):
    configs=describe(doc);matches=[c for c in configs if c['id']==index and c['supported']]
    if type(index) is not int or len(matches)!=1:raise DocumentError('Elige una configuración de capas compatible.')
    n,root,array=collection(doc);config=n.pdf_array_get(array,index)
    n.pdf_dict_puts(root,'D',n.pdf_deep_copy_obj(config))
