"""Declarative, bounded recipes. No code execution, network or secret persistence."""
import base64
import hashlib
import json
import re
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import pymupdf as f
from .engine import DocumentError, open_pdf, export_pdf
from .document_tools import META_KEYS, editable, metadata_pdf, optimize_pdf, protect_pdf, export_text
from .compression import compress_images
from .form_data import flatten_form

MAX_INPUT=60*1024*1024
MAX_OUTPUT=100*1024*1024
STEP_KEYS={
    'metadata':{'values','remove_xml'}, 'watermark':{'text','size','opacity','angle','color'},
    'numbering':{'template','start','size'}, 'compress':{'dpi','quality'},
    'docx':{'keep_lines','include_images','include_tables','include_links'},
    'optimize':set(), 'flatten':set(), 'text':set(), 'protect':{'allow_copy','allow_print'},
}


def digest(data):return hashlib.sha256(data).hexdigest()


def validate_recipe(recipe):
    if (not isinstance(recipe,dict) or set(recipe)!={'format','version','name','filename','steps'}
            or recipe.get('format')!='reapdf-recipe' or type(recipe.get('version')) is not int or recipe['version']!=1):
        raise DocumentError('Receta no compatible: usa el formato Reapdf versión 1.')
    for key,limit in [('name',80),('filename',160)]:
        value=recipe[key]
        if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 or ord(c)==127 for c in value):
            raise DocumentError('Nombre o plantilla de salida no válidos.')
    pattern=recipe['filename']
    if any(c in pattern for c in '/\\:') or re.sub(r'\{(index|name|recipe)\}','',pattern).count('{') or re.sub(r'\{(index|name|recipe)\}','',pattern).count('}'):
        raise DocumentError('Usa nombres sin rutas y solo {index}, {name} y {recipe}.')
    steps=recipe['steps']
    if not isinstance(steps,list) or not 1<=len(steps)<=8:raise DocumentError('La receta debe contener entre 1 y 8 pasos.')
    seen=set()
    for index,step in enumerate(steps):
        if not isinstance(step,dict) or not isinstance(step.get('type'),str) or step['type'] not in STEP_KEYS:raise DocumentError('Paso de receta no compatible.')
        kind=step['type']
        if kind in seen or set(step)!={'type'}|STEP_KEYS[kind]:raise DocumentError('No repitas tipos de paso ni añadas opciones desconocidas o contraseñas.')
        if kind in {'protect','text','docx'} and index!=len(steps)-1:raise DocumentError('Proteger, extraer texto o convertir a Word debe ser el último paso.')
        if kind=='compress':
            if type(step['dpi']) is not int or not 72<=step['dpi']<=300 or type(step['quality']) is not int or not 40<=step['quality']<=95:raise DocumentError('Compresión: resolución 72–300 DPI y calidad 40–95.')
        if kind=='docx' and any(type(step[k]) is not bool for k in STEP_KEYS['docx']):raise DocumentError('Las opciones de Word deben ser verdaderas o falsas.')
        if kind=='metadata':
            values=step['values']
            if not isinstance(values,dict) or set(values)!=META_KEYS or any(not isinstance(v,str) or len(v)>1000 or any(ord(c)<32 for c in v) for v in values.values()) or type(step['remove_xml']) is not bool:raise DocumentError('Completa los cinco metadatos sin controles; máximo 1000 caracteres.')
        if kind=='protect' and any(type(step[k]) is not bool for k in ['allow_copy','allow_print']):raise DocumentError('Permisos de copia e impresión no válidos.')
        if kind=='numbering':
            from .headers import TOKENS
            template=step['template']
            if not isinstance(template,str) or not template.strip() or len(template)>100 or any(ord(c)<32 or ord(c)>255 for c in template) or any(t not in TOKENS for t in re.findall(r'\{([^{}]*)\}',template)) or re.sub(r'\{(pagina|total|numero)\}','',template).count('{') or re.sub(r'\{(pagina|total|numero)\}','',template).count('}'):
                raise DocumentError('Numeración: usa texto latino y {pagina}, {total} o {numero}.')
            if type(step['start']) is not int or not 1<=step['start']<=999900 or type(step['size']) not in [int,float] or not 6<=step['size']<=20:raise DocumentError('Numeración: inicio 1–999900 y tamaño 6–20 pt.')
        if kind=='watermark':
            from .watermarks import prepare_watermark
            # Validate style/text on a generous page; fit is checked per source.
            with f.open() as scratch:
                scratch.new_page(width=50000,height=50000)
                prepare_watermark(scratch,{'pages':[0],**step})
        seen.add(kind)
    # A JSON round trip returns detached, normalized data without shared objects.
    try:return json.loads(json.dumps(recipe,ensure_ascii=False,allow_nan=False).encode('utf-8'))
    except (ValueError,UnicodeError) as exc:raise DocumentError('La receta contiene texto Unicode o números no válidos.') from exc


def output_name(pattern,name,recipe,index,extension):
    def clean(value):
        value=value.replace('\\','/').rsplit('/',1)[-1]
        value=re.sub(r'[^\w. -]','_',value).strip(' .')[:70]
        while len(value.encode('utf-8'))>200:value=value[:-1]
        return value or 'documento'
    stem=clean(name.rsplit('.',1)[0])
    rendered=re.sub(r'\{(index|name|recipe)\}',lambda m:{'index':f'{index:03d}','name':stem,'recipe':clean(recipe)}[m[1]],pattern)
    # A numeric prefix ensures uniqueness even with identical templates/names.
    return f'{index:03d}-'+clean(rendered)+extension


def _run_step(data,step,secrets):
    kind=step['type'];details={};status='applied'
    with open_pdf(data) as doc:pages=list(range(len(doc)))
    if kind=='metadata':result=metadata_pdf(data,[],step['values'],step['remove_xml']);details={'xml_removed':step['remove_xml']}
    elif kind=='optimize':result,details=optimize_pdf(data,[])
    elif kind=='compress':result,details=compress_images(data,[],step['dpi'],step['quality']);details={k:v for k,v in details.items() if k!='sha256'}
    elif kind=='flatten':
        with open_pdf(data) as doc:count=sum(len(list(p.widgets() or [])) for p in doc)
        result=flatten_form(data,[]) if count else data;details={'fields':count};status='applied' if count else 'skipped'
    elif kind=='watermark':result=export_pdf(data,[{'page':0,'pages':pages,**step}])
    elif kind=='numbering':
        from .headers import SLOTS
        slots={k:'' for k in SLOTS};slots['bottom_center']=step['template']
        result=export_pdf(data,[{'type':'header_footer','page':0,'pages':pages,'slots':slots,'size':step['size'],'start':step['start'],'font':'helv','color':[0,0,0],'margins':[20,24,20,24]}]);details={'restart_per_document':True,'start':step['start']}
    elif kind=='docx':
        from .docx_export import export_docx
        result,details=export_docx(data,[],pages,**{k:step[k] for k in STEP_KEYS['docx']})
    elif kind=='text':result=export_text(data,[],pages);details={'encoding':'UTF-8','ocr':False}
    else:
        result=protect_pdf(data,[],secrets['password'],secrets['owner_password'],step['allow_copy'],step['allow_print']);details={'encryption':'AES-256','allow_copy':step['allow_copy'],'allow_print':step['allow_print']}
    return result,details,status


def process_recipe(items,recipe,secrets=None,review=False):
    recipe=validate_recipe(recipe)
    if type(review) is not bool:raise DocumentError('Revisión no válida.')
    protected=recipe['steps'][-1]['type']=='protect'
    secrets={} if secrets is None else secrets
    if not isinstance(secrets,dict) or set(secrets)!=({'password','owner_password'} if protected else set()):raise DocumentError('Introduce las contraseñas solo en los campos de ejecución.')
    if protected:
        # Validate credentials before any input processing without including them in errors.
        with f.open() as scratch:
            scratch.new_page();protect_pdf(scratch.tobytes(),[],secrets['password'],secrets['owner_password'])
    if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('Selecciona entre 1 y 10 PDF.')
    size=0;pages=0;prepared=[];mutates=any(s['type'] not in {'text','docx'} for s in recipe['steps'])
    for index,item in enumerate(items,1):
        if not isinstance(item,(tuple,list)) or len(item)!=3:raise DocumentError('Documento del lote no válido.')
        name,base,operations=item
        if not isinstance(name,str) or not 1<=len(name)<=255 or any(ord(c)<32 or ord(c)==127 for c in name) or not isinstance(base,bytes):raise DocumentError('Nombre o PDF no válido.')
        try:name.encode('utf-8')
        except UnicodeError as exc:raise DocumentError('Nombre de documento Unicode no válido.') from exc
        size+=len(base)
        if size>MAX_INPUT:raise DocumentError('El lote supera 60 MB de entrada.')
        try:
            with open_pdf(base) as doc:
                pages+=len(doc)
                if pages>100:raise DocumentError('Hasta 100 páginas por lote.')
                if mutates:editable(doc)
                if recipe['steps'][-1]['type'] in {'text','docx'} and not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('No permite copiar texto.')
                prepared.append((name,base,operations,len(doc)))
        except DocumentError as exc:raise DocumentError(f'Documento {index}, validación: {exc}') from exc
    report={'schema':'reapdf-automation-1','recipe':recipe,'pages':pages,'input_bytes':size,'documents':[]};outputs=[];total=0
    for index,(name,base,operations,count) in enumerate(prepared,1):
        step_reports=[]
        try:
            data=export_pdf(base,operations);preview_data=data
            for step_index,step in enumerate(recipe['steps'],1):
                before=data
                data,details,status=_run_step(data,step,secrets)
                if len(data)>MAX_OUTPUT:raise DocumentError('Un resultado intermedio supera 100 MB.')
                step_reports.append({'step':step_index,'type':step['type'],'status':status,'input_bytes':len(before),'output_bytes':len(data),'input_sha256':digest(before),'output_sha256':digest(data),'details':details})
                if step['type'] not in {'protect','text','docx'}:preview_data=data
            total+=len(data)
            if total>MAX_OUTPUT:raise DocumentError('El lote supera 100 MB de salida.')
            extension={'text':'.txt','docx':'.docx'}.get(recipe['steps'][-1]['type'],'.pdf')
            row={'name':name,'file':output_name(recipe['filename'],name,recipe['name'],index,extension),'pages':count,'input_bytes':len(base),'output_bytes':len(data),'input_sha256':digest(base),'output_sha256':digest(data),'includes_applied_operations':bool(operations),'steps':step_reports}
            if review and extension=='.pdf':
                with open_pdf(preview_data) as doc:
                    p=doc[0];scale=min(1,600/max(p.rect.width,p.rect.height));pix=p.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False)
                    row['preview']='data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode()
            report['documents'].append(row)
            if not review:outputs.append((row['file'],data))
        except DocumentError as exc:raise DocumentError(f'Documento {index}, paso {len(step_reports)+1}: {exc}') from exc
    report['output_bytes']=total
    if review:return report
    buffer=BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED) as archive:
        for name,data in outputs:archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8'))
    return buffer.getvalue()
