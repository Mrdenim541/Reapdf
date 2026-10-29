"""Bounded, atomic multi-document processing with inspectable output manifests."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,re
from pymupdf import PDF_PERM_COPY
from .engine import open_pdf,DocumentError
from .document_tools import optimize_pdf,export_text,protect_pdf

MAX_INPUT=60*1024*1024
MAX_OUTPUT=100*1024*1024


def process_batch(items,action,settings=None,review=False):
    if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('Selecciona entre 1 y 10 PDF para el lote.')
    if action not in ['optimize','text','protect']:raise DocumentError('Elige optimizar, extraer texto o proteger copias.')
    if settings is None:settings={}
    if not isinstance(settings,dict) or set(settings)-({'password','owner_password','allow_copy','allow_print'} if action=='protect' else set()):raise DocumentError('Configuración de lote no compatible.')
    if type(review) is not bool:raise DocumentError('Revisión de lote no válida.')
    total_input=0;total_pages=0;prepared=[]
    # Validate all sources and budgets before doing work. Errors never produce a ZIP.
    for index,item in enumerate(items):
        if not isinstance(item,(tuple,list)) or len(item)!=3:raise DocumentError('Documento del lote no válido.')
        name,base,operations=item
        if not isinstance(name,str) or not 1<=len(name)<=255 or any(ord(c)<32 or ord(c)==127 for c in name) or not isinstance(base,bytes):raise DocumentError('Nombre o archivo del lote no válido.')
        total_input+=len(base)
        if total_input>MAX_INPUT:raise DocumentError('El lote supera 60 MB de entrada.')
        with open_pdf(base) as doc:
            pages=len(doc);total_pages+=pages
            if total_pages>100:raise DocumentError('El lote admite hasta 100 páginas en total.')
            if action=='text' and not doc.permissions&PDF_PERM_COPY:raise DocumentError(f'Documento {index+1}: no permite copiar texto.')
            if action!='text':
                from .document_tools import editable
                editable(doc)
        prepared.append((name,base,operations,pages))
    outputs=[];manifest={'schema':'reapdf-batch-1','action':action,'documents':[],'pages':total_pages,'input_bytes':total_input};total_output=0
    for index,(name,base,operations,pages) in enumerate(prepared):
        try:
            if action=='optimize':data,details=optimize_pdf(base,operations)
            elif action=='text':data=export_text(base,operations,list(range(pages)));details={'encoding':'UTF-8','layout':'reading-order','ocr':False}
            else:
                data=protect_pdf(base,operations,settings.get('password'),settings.get('owner_password'),settings.get('allow_copy',True),settings.get('allow_print',True))
                details={'encryption':'AES-256','allow_copy':settings.get('allow_copy',True),'allow_print':settings.get('allow_print',True)}
        except DocumentError as exc:raise DocumentError(f'Documento {index+1}: {exc}') from exc
        total_output+=len(data)
        if total_output>MAX_OUTPUT:raise DocumentError('El lote supera 100 MB de salida.')
        stem=name.replace('\\','/').rsplit('/',1)[-1].rsplit('.',1)[0]
        stem=re.sub(r'[^\w. -]','_',stem)[:80] or 'documento';output=f'{index+1:03d}-{stem}'+('.txt' if action=='text' else '.pdf')
        manifest['documents'].append({'name':name,'file':output,'pages':pages,'input_bytes':len(base),'output_bytes':len(data),'input_sha256':hashlib.sha256(base).hexdigest(),'output_sha256':hashlib.sha256(data).hexdigest(),'includes_applied_operations':bool(operations),'details':details})
        if not review:outputs.append((output,data))
    manifest['output_bytes']=total_output
    if review:return manifest
    stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        for name,data in outputs:archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    return stream.getvalue()
