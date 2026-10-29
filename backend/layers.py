"""Inspect and persist default OCG visibility without flattening page content."""
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf
from .document_tools import editable


def model(base,ops):
    with open_pdf(export_pdf(base,ops)) as doc:
        groups=doc.get_ocgs();config=doc.get_layer(-1) if groups else {}
        if len(groups)>200:raise DocumentError('Hasta 200 capas en esta herramienta.')
        locked=set(config.get('locked',[]));on=set(config.get('on',[]));off=set(config.get('off',[]));base_on=config.get('basestate','ON')!='OFF'
        return {'layers':[{'id':xref,'name':g['name'],'visible':xref in on or xref not in off and base_on,'locked':xref in locked} for xref,g in groups.items()],'radio_groups':config.get('rbgroups',[])}


def apply(base,ops,visible):
    info=model(base,ops);groups={r['id']:r for r in info['layers']}
    if not isinstance(visible,list) or any(type(i) is not int or i not in groups for i in visible) or len(set(visible))!=len(visible):raise DocumentError('Selección de capas no válida.')
    chosen=set(visible)
    for row in groups.values():
        if row['locked'] and (row['id'] in chosen)!=row['visible']:raise DocumentError('No se puede cambiar una capa bloqueada.')
    for group in info['radio_groups']:
        if len(chosen.intersection(group))>1:raise DocumentError('Ese grupo de capas permite solo una visible.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if not groups:raise DocumentError('El PDF no contiene capas opcionales.')
        doc.set_layer(-1,on=list(chosen),off=list(set(groups)-chosen))
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
