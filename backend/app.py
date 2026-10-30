from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from contextlib import asynccontextmanager
import json
import base64
import pymupdf
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .engine import open_pdf, metadata, spans, export_pdf, DocumentError
from .viewer import text_items, search_document
from .review import review_selection
from .content_tools import page_links
from .link_editing import inspect_links,edit_link
from .batch_tools import process_batch,MAX_INPUT as MAX_BATCH_INPUT
from .automation import process_recipe,validate_recipe
from .field_properties import inspect_properties,edit_properties
from .comments import inspect_comments,edit_comment,comment_report
from .docx_export import export_docx
from .standards import standard_status,validate_standard,archival_copy
from .accessibility import inspect_accessibility,prepare_accessibility
from .bookmarks import bookmark_model
from .forms import form_model
from .form_structure import expand_values
from .conversions import images_to_pdf, export_page_images, MAX_FILES, MAX_INPUT
from .images import MAX_IMAGE_BYTES
from fastapi import Form
from starlette.concurrency import run_in_threadpool
from threading import Lock
from .form_data import export_form_data, import_form_data, flatten_form
from .ocr import ocr_status, ocr_pdf
from .form_design import create_field,delete_field
from .signature import visual_signature
from .certificates import inspect_identity,MAX_IDENTITY,MAX_TRUST
from .digital_signatures import sign_document,verify_signatures
from .compression import compress_images
from .redaction import redact_pdf
from .redaction_search import search_redactions,redact_search
from .find_replace import inspect as inspect_replace,replace as batch_replace,plan_token
from .pro_tools import label_rules, labels_pdf, attachment_model, add_attachment, attachment_pdf, download_attachment, extract_tables, tables_zip, bates_batch
from .comparison import compare_pdf
from .image_editing import image_model,edit_image
from . import measurements,layers,document_sets,xfdf,working_copy,structure_editing,preflight,region_ocr
from .paragraphs import inspect_paragraph,replace_paragraph,paragraph_blocks,paragraph_preview
from .text_flow import inspect_flow,flow_text
from .form_calculations import calculate_fields
from .form_rules import resolve_rules
from .docx_import import import_docx,MAX_INPUT as MAX_DOCX_INPUT
from .styled_text import inspect_styled,replace_styled
from .document_review import review_document
from .document_tools import export_text, read_metadata, metadata_pdf, optimize_pdf, protect_pdf, unlock_pdf, PasswordRequired
OCR_LOCK=Lock()
from .existing_annotations import list_annotations
from .text_style import FONT_OPTIONS
from .rendering import render_page
from .pages import organize_pdf
from .page_creation import duplicate_pdf, blank_pdf
from .projects import build_project, read_project, RecoveryStore, RecoveryConflict, data_directory, MAX_PROJECT
from .merge import merge_pdf
from .page_tools import crop_pdf, split_pdf

MAX_UPLOAD = 30 * 1024 * 1024
MAX_STORE = 300 * 1024 * 1024

@asynccontextmanager
async def lifespan(app):
    with TemporaryDirectory(prefix="reapdf-") as temp:
        app.state.root = Path(temp)
        app.state.recovery = RecoveryStore(data_directory())
        yield

app = FastAPI(title="Reapdf local", lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

@app.middleware("http")
async def local_only(request: Request, call_next):
    # El prototipo se sirve exclusivamente en loopback, sin CORS abierto.
    if request.method not in {"GET", "HEAD"}:
        origin = request.headers.get("origin")
        if origin and origin not in {str(request.base_url).rstrip("/"), "http://127.0.0.1:5173", "http://localhost:5173"}:
            return JSONResponse({"detail": "Origen no permitido."}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.exception_handler(DocumentError)
async def document_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=422)

@app.exception_handler(RecoveryConflict)
async def recovery_conflict(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=409)

@app.exception_handler(OSError)
async def storage_error(request, exc):
    return JSONResponse({"detail": "No se pudo leer o escribir el almacenamiento local. Comprueba espacio y permisos; conserva una copia PDF o un proyecto."}, status_code=507)

def document_path(doc_id):
    if len(doc_id) != 32 or any(c not in "0123456789abcdef" for c in doc_id):
        raise HTTPException(404, "Documento no encontrado.")
    path = app.state.root / f"{doc_id}.pdf"
    if not path.is_file():
        raise HTTPException(404, "Documento no encontrado o sesión finalizada.")
    return path

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.43.0"}

def set_items(descriptors):
    if not isinstance(descriptors,list) or not 1<=len(descriptors)<=10:raise DocumentError('Hasta 10 documentos por conjunto.')
    items=[]
    for item in descriptors:
        if not isinstance(item,dict) or set(item)!={'id','name','role','sha256'}:raise DocumentError('Documento del conjunto no válido.')
        if not isinstance(item['id'],str):raise DocumentError('Identidad PDF no válida.')
        items.append({**item,'data':document_path(item['id']).read_bytes()})
    return document_sets.documents(items)

@app.post('/api/document-sets/current/{doc_id}')
async def current_set_document(doc_id:str,request:Request):
    p=await read_payload(request);data=await run_in_threadpool(export_pdf,document_path(doc_id).read_bytes(),p.get('operations',[]))
    with open_pdf(data) as source:
        if not source.permissions&pymupdf.PDF_PERM_COPY:raise DocumentError('El documento no permite esta copia.')
    name=document_sets.text(p.get('name'),200)
    return {**store_document(data),'name':name,'role':'Origen','sha256':document_sets.digest(data)}

@app.post('/api/document-sets/file')
async def add_set_document(file:UploadFile):
    data=await file.read(MAX_UPLOAD+1);await file.close()
    if not data or len(data)>MAX_UPLOAD:raise DocumentError('Añade un PDF de hasta 30 MB.')
    with open_pdf(data) as source:
        if not source.permissions&pymupdf.PDF_PERM_COPY:raise DocumentError('El PDF no permite incorporarlo al conjunto.')
    name=document_sets.text(Path(file.filename or 'Documento.pdf').name,200)
    return {**store_document(data),'name':name,'role':'Destino','sha256':document_sets.digest(data)}

@app.post('/api/document-sets/analyze')
async def analyze_set(request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(document_sets.analyze,set_items(p.get('documents')),p.get('source'),p.get('target'),p.get('codes'))

@app.post('/api/document-sets/manual-anchor')
async def create_manual_anchor(request:Request):
    p=await read_payload(request);item=set_items([p.get('document')])[0]
    return await run_in_threadpool(document_sets.manual_anchor,item,p.get('code'),p.get('page'),p.get('rect'))

@app.post('/api/document-sets/revision')
async def revise_set(request:Request):
    p=await read_payload(request);items=set_items(p.get('documents'));replacement=set_items([p.get('replacement')])[0]
    apply=p.get('apply') is True
    if apply and p.get('acknowledge') is not True:raise DocumentError('Confirma la revisión de todos los vínculos afectados.')
    result=await run_in_threadpool(document_sets.revision,items,p.get('relations',[]),p.get('old'),replacement,p.get('choices',{}) if apply else None)
    if not apply:return result
    docs,relations,report=result
    return {'documents':[{k:v for k,v in d.items() if k!='data'} for d in docs],'relations':relations,'report':report}

@app.post('/api/document-sets/export')
async def export_set(request:Request):
    p=await read_payload(request)
    data=await run_in_threadpool(document_sets.build,set_items(p.get('documents')),p.get('relations',[]),p.get('name'))
    return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename="Documentos.reapdfset"'})

@app.post('/api/document-sets/compile')
async def compile_set(request:Request):
    p=await read_payload(request)
    data,report=await run_in_threadpool(document_sets.compile_pdf,set_items(p.get('documents')),p.get('relations',[]),p.get('name'))
    return Response(data,media_type='application/pdf',headers={'X-Reapdf-Compilation':json.dumps(report),'Content-Disposition':'attachment; filename="Documentos-vinculados.pdf"'})

@app.post('/api/document-sets/import')
async def import_set(file:UploadFile):
    data=await file.read(70*1024*1024+1);await file.close()
    items,relations,name=await run_in_threadpool(document_sets.read,data)
    if sum(p.stat().st_size for p in app.state.root.glob('*.pdf'))+sum(len(i['data']) for i in items)>MAX_STORE:raise HTTPException(413,'Almacenamiento temporal insuficiente para abrir el conjunto.')
    created=[];mapping={}
    try:
        for item in items:
            version=store_document(item['data']);mapping[item['id']]=version['id'];created.append({**version,'name':item['name'],'role':item['role'],'sha256':item['sha256']})
        for relation in relations:
            for side in ['source','target']:relation[side]['document']=mapping[relation[side]['document']]
        return {'name':name,'documents':created,'relations':relations}
    except Exception:
        for item in created:(app.state.root/(item['id']+'.pdf')).unlink(missing_ok=True)
        raise

@app.post('/api/documents/{doc_id}/inline-block')
async def inspect_inline_block(doc_id:str,request:Request):
    from .original_reflow import inspect
    p=await read_payload(request)
    return await run_in_threadpool(inspect,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('origin'),p.get('text'))

@app.post('/api/documents/{doc_id}/reflow-original')
async def reflow_original(doc_id:str,request:Request):
    from .original_reflow import reflow
    p=await read_payload(request)
    result=await run_in_threadpool(reflow,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('box'),p.get('text'),p.get('preview') is True,p.get('source_box'),p.get('runs'))
    if p.get('preview') is True:return result
    data,report=result
    return {**store_document(data),'reflow_report':report}

@app.post('/api/documents/{doc_id}/insert-text-auto')
async def insert_quick_text(doc_id:str,request:Request):
    from .quick_text import insert
    p=await read_payload(request)
    result=await run_in_threadpool(insert,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('point'),p.get('text'),p.get('size',12),p.get('family','sans'),p.get('style','regular'),p.get('color'),p.get('width',240),p.get('preview') is True)
    if p.get('preview') is True:return result
    data,report=result
    return {**store_document(data),'insertion_report':report}

@app.post('/api/documents/{doc_id}/xfdf/export')
async def export_xfdf(doc_id:str,request:Request):
    p=await read_payload(request)
    if type(p.get('annotations',True)) is not bool or type(p.get('fields',True)) is not bool:raise DocumentError('Opciones XFDF no válidas.')
    data,report=await run_in_threadpool(xfdf.export,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('annotations',True),p.get('fields',True))
    return Response(data,media_type='application/vnd.adobe.xfdf',headers={'X-Reapdf-XFDF':json.dumps(report),'Content-Disposition':'attachment; filename="Datos.xfdf"'})

@app.post('/api/documents/{doc_id}/xfdf/import')
async def import_xfdf(doc_id:str,request:Request):
    p=await read_payload(request);xml=p.get('xml')
    if not isinstance(xml,str) or len(xml)>xfdf.MAX_XML:raise DocumentError('XFDF no válido o demasiado grande.')
    try:data=xml.encode('utf-8')
    except UnicodeError as exc:raise DocumentError('XML UTF-8 no válido.') from exc
    result=await run_in_threadpool(xfdf.import_data,document_path(doc_id).read_bytes(),p.get('operations',[]),data,p.get('confirm',False),p.get('preview') is True)
    if p.get('preview') is True:return result
    data,report=result
    return {**store_document(data),'xfdf_report':report}

@app.post('/api/documents/{doc_id}/working-copy')
async def create_working_copy(doc_id:str,request:Request):
    p=await read_payload(request)
    if p.get('operations',[]):raise DocumentError('Crea la copia desde el original firmado, sin operaciones pendientes.')
    data,report=await run_in_threadpool(working_copy.create,document_path(doc_id).read_bytes(),p.get('acknowledge',False))
    return {**store_document(data),'working_copy':True,'copy_report':report}

@app.post('/api/documents/{doc_id}/structure')
async def inspect_structure(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(structure_editing.model,document_path(doc_id).read_bytes(),p.get('operations',[]))

@app.post('/api/documents/{doc_id}/tagging-candidates')
async def tagging_candidates(doc_id:str,request:Request):
    from .basic_tagging import candidates
    p=await read_payload(request)
    return await run_in_threadpool(candidates,document_path(doc_id).read_bytes(),p.get('operations',[]))

@app.post('/api/documents/{doc_id}/create-basic-tags')
async def create_basic_tags(doc_id:str,request:Request):
    from .basic_tagging import create
    p=await read_payload(request)
    data,report=await run_in_threadpool(create,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('entries'),p.get('language','es'),p.get('reviewed',False))
    return {**store_document(data),'tagging_report':report}

@app.post('/api/documents/{doc_id}/reading-preview')
async def reading_preview(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(structure_editing.reading_preview,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'))

@app.post('/api/documents/{doc_id}/structure-properties')
async def structure_properties(doc_id:str,request:Request):
    p=await read_payload(request)
    data=await run_in_threadpool(structure_editing.properties,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('id'),p.get('role'),p.get('language'))
    return store_document(data)

@app.post('/api/documents/{doc_id}/structure/{action}')
async def edit_structure(doc_id:str,action:str,request:Request):
    p=await read_payload(request)
    if action not in ['alt','order']:raise DocumentError('Cambio de estructura no válido.')
    data=await run_in_threadpool(structure_editing.edit,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('id'),p.get('alt') if action=='alt' else None,p.get('order') if action=='order' else None)
    return store_document(data)

@app.post('/api/documents/{doc_id}/preflight')
async def inspect_print(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(preflight.inspect,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('min_dpi',150))

@app.post('/api/documents/{doc_id}/extract-table-region')
async def extract_table_region(doc_id:str,request:Request):
    from .table_regions import extract
    p=await read_payload(request)
    if not OCR_LOCK.acquire(blocking=False):raise DocumentError('Ya hay un reconocimiento en curso. Espera a que termine.')
    try:return await run_in_threadpool(extract,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('box'),p.get('grid'),p.get('mode','auto'),p.get('language','spa+eng'),p.get('dpi',200),p.get('orientation',0),p.get('detect_merges',False))
    finally:OCR_LOCK.release()


@app.post('/api/documents/{doc_id}/export-region-table')
async def export_region_table(doc_id:str,request:Request):
    from .table_regions import csv_bytes,docx_bytes
    p=await read_payload(request)
    with open_pdf(document_path(doc_id).read_bytes()) as doc:
        if not doc.permissions & pymupdf.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer tablas.')
    if p.get('format')=='csv':data=csv_bytes(p.get('cells'),p.get('spans'));mime='text/csv; charset=utf-8';ext='csv'
    elif p.get('format')=='docx':data=docx_bytes(p.get('cells'),p.get('header',True),p.get('spans'));mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document';ext='docx'
    else:raise DocumentError('Elige CSV o Word para exportar la tabla revisada.')
    return Response(data,media_type=mime,headers={'Content-Disposition':f'attachment; filename="reapdf-tabla.{ext}"'})


@app.post('/api/documents/{doc_id}/detect-skew')
async def detect_skew(doc_id:str,request:Request):
    from .deskew import inspect
    p=await read_payload(request)
    if not OCR_LOCK.acquire(blocking=False):raise DocumentError('Ya hay un reconocimiento en curso. Espera a que termine.')
    try:return await run_in_threadpool(inspect,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('box'),p.get('orientation',0))
    finally:OCR_LOCK.release()

@app.post('/api/documents/{doc_id}/ocr-regions')
async def recognize_regions(doc_id:str,request:Request):
    p=await read_payload(request)
    if not OCR_LOCK.acquire(blocking=False):raise DocumentError('Ya hay un OCR en curso. Espera a que termine.')
    try:data,report=await run_in_threadpool(region_ocr.recognize,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('regions'),p.get('language','spa+eng'),p.get('dpi',200),p.get('orientation',0),p.get('correction'))
    finally:OCR_LOCK.release()
    return {**store_document(data),'ocr_report':report}

@app.get('/api/documents/{doc_id}/measurements')
def measurement_list(doc_id:str,page:int=0):
    return measurements.model(document_path(doc_id).read_bytes(),[],page)

@app.post('/api/documents/{doc_id}/measure')
async def add_measurement(doc_id:str,request:Request):
    p=await read_payload(request)
    result=await run_in_threadpool(measurements.measure,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('kind'),p.get('points'),p.get('calibration'),p.get('unit','m'),p.get('preview') is True,p.get('id'),p.get('profile'))
    return result if p.get('preview') is True else store_document(result)

@app.post('/api/documents/{doc_id}/measurement-model')
async def measurement_model(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(measurements.model,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'))

@app.post('/api/documents/{doc_id}/measurement-targets')
async def measurement_targets(doc_id:str,request:Request):
    from .measurement_geometry import targets
    p=await read_payload(request)
    return await run_in_threadpool(targets,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'))

@app.post('/api/documents/{doc_id}/measurement-scale')
async def measurement_scale(doc_id:str,request:Request):
    from .measurement_geometry import configure_profile
    p=await read_payload(request)
    result=await run_in_threadpool(configure_profile,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('name'),p.get('box'),p.get('calibration'),p.get('id'),p.get('remove',False))
    return store_document(result)

@app.post('/api/documents/{doc_id}/delete-measurement')
async def remove_measurement(doc_id:str,request:Request):
    p=await read_payload(request)
    return store_document(await run_in_threadpool(measurements.delete_measure,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('page'),p.get('id')))

@app.post('/api/documents/{doc_id}/layers')
async def inspect_layers(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(layers.model,document_path(doc_id).read_bytes(),p.get('operations',[]))

@app.post('/api/documents/{doc_id}/set-layers')
async def change_layers(doc_id:str,request:Request):
    p=await read_payload(request)
    result=await run_in_threadpool(layers.apply,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('visible'))
    if p.get('preview') is True:
        image,_=await run_in_threadpool(paragraph_preview,result,[],p.get('page',0),1)
        return Response(image,media_type='image/png')
    return store_document(result)

@app.post("/api/documents")
async def upload(file: UploadFile, password: str = Form('')):
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "El límite inicial es 30 MB por PDF.")
    try:result,unlocked=unlock_pdf(data,password)
    except PasswordRequired as exc:raise HTTPException(401,str(exc)) from exc
    return {**store_document(result),'opened_encrypted':unlocked}


def store_project_version(base, operations, result, page_map=None):
    from .form_rules import remap_rules
    project_operations = remap_rules(base,operations,result,page_map)
    return {**store_document(result), 'project_operations': project_operations}


def store_document(data):
    if sum(p.stat().st_size for p in app.state.root.glob("*.pdf")) + len(data) > MAX_STORE:
        raise HTTPException(413, "Almacenamiento temporal lleno. Abre un documento nuevo o reinicia la aplicación para liberar el historial.")
    with open_pdf(data) as doc:
        info = metadata(doc)
    doc_id = uuid4().hex
    (app.state.root / f"{doc_id}.pdf").write_bytes(data)
    return {"id": doc_id, **info}

@app.delete("/api/documents/{doc_id}")
def close(doc_id: str):
    document_path(doc_id).unlink()
    return {"closed": True}

@app.get("/api/documents/{doc_id}/pages/{number}")
def page_info(doc_id: str, number: int):
    with open_pdf(document_path(doc_id).read_bytes()) as doc:
        if not 0 <= number < len(doc):
            raise HTTPException(404, "Página no encontrada.")
        return {"spans": spans(doc[number]), **list_annotations(doc, number), "text_fonts": [{"value":key,"label":name} for key,name in FONT_OPTIONS]}

@app.get("/api/documents/{doc_id}/pages/{number}/image")
def page_image(doc_id: str, number: int, scale: float = 1.5):
    with open_pdf(document_path(doc_id).read_bytes()) as doc:
        if not 0 <= number < len(doc):
            raise HTTPException(404, "Página no encontrada.")
        page = doc[number]
        image, headers = render_page(page, scale)
        return Response(image, media_type="image/png", headers=headers)

async def read_payload(request: Request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 5 * 1024 * 1024:
            raise HTTPException(413, "Demasiados datos de edición.")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Solicitud no válida.")
    if not isinstance(payload, dict):
        raise HTTPException(422, "Solicitud no válida.")
    return payload

@app.post('/api/create/images')
async def create_from_images(files: list[UploadFile], paper: str = Form('A4'), dpi: int = Form(150), margin: float = Form(18)):
    images=[];total=0
    try:
        if not 1<=len(files)<=MAX_FILES:raise DocumentError('Selecciona de 1 a 30 imágenes.')
        for file in files:
            data=await file.read(MAX_IMAGE_BYTES+1);total+=len(data)
            if len(data)>MAX_IMAGE_BYTES or total>MAX_INPUT:raise DocumentError('Hasta 2 MB por imagen y 20 MB por lote.')
            images.append(data)
        return store_document(images_to_pdf(images,paper,dpi,margin))
    finally:
        for file in files:await file.close()


@app.post('/api/documents/{doc_id}/forms')
async def read_forms(doc_id: str, request: Request):
    payload=await read_payload(request);data=document_path(doc_id).read_bytes();operations=payload.get('operations',[])
    export_pdf(data,operations)  # Validar sin usar los xref renumerados de la copia exportada.
    with open_pdf(data) as doc:model=form_model(doc)
    effective,reports,targets=resolve_rules(data,operations)
    fill=next((op for op in effective if op.get('type')=='form_fill'),None)
    for row in model['fields']:row['base_value']=row['value']
    from .native_calculations import resolve as native_values
    recalculate=any(op.get('type')=='form_recalculate' for op in effective)
    native_reports=[]
    if fill or recalculate:
        with open_pdf(data) as source:resolved,native_reports=native_values(source,model,fill['values'] if fill else [],recalculate)
        values={(entry['page'],entry['xref']):entry['value'] for entry in resolved}
        for row in model['fields']:row['value']=values.get((row['page'],row['xref']),row['value'])
    from .form_actions import value as formatted_value
    for row in model['fields']:
        if row.get('format') and (fill or recalculate) and (row['page'],row['xref']) in values and isinstance(row['value'],str):
            row['display_value']=formatted_value(row['format'],row['value'])[1];row['format_issue']=''
        row['base_editable']=row['editable'];row['calculated']=row.get('native_calculated',False) or row['group'] in targets
        if row['group'] in targets:row.update(editable=False,reason='Campo calculado por reglas de este proyecto. Cambia sus fuentes o edita las reglas.')
    model['native_calculation_reports']=native_reports
    model['calculation_reports']=reports
    return model


@app.post('/api/documents/{doc_id}/export-images')
async def download_images(doc_id: str, request: Request):
    payload=await read_payload(request)
    data=export_page_images(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('pages'),payload.get('dpi',150),payload.get('format','png'),payload.get('quality',90))
    return Response(data,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="reapdf-imagenes.zip"'})


@app.post('/api/documents/{doc_id}/review')
async def document_review(doc_id: str, request: Request):
    payload = await read_payload(request)
    return await run_in_threadpool(review_document, document_path(doc_id).read_bytes(),
                                   payload.get('operations', []), payload.get('offset', 0), payload.get('limit', 20))

def batch_sources(payload):
    entries=payload.get('documents')
    if not isinstance(entries,list) or not 1<=len(entries)<=10:raise DocumentError('Selecciona entre 1 y 10 PDF para el lote.')
    sources=[];size=0;seen=set()
    for entry in entries:
        if not isinstance(entry,dict) or not isinstance(entry.get('id'),str) or entry['id'] in seen:raise DocumentError('Documentos del lote inexistentes o repetidos.')
        seen.add(entry['id']);path=document_path(entry['id']);size+=path.stat().st_size
        if size>MAX_BATCH_INPUT:raise DocumentError('El lote supera 60 MB de entrada.')
        sources.append((entry.get('name','Documento.pdf'),path,entry.get('operations',[])))
    return [(name,path.read_bytes(),ops) for name,path,ops in sources]


@app.post('/api/recipes/validate')
async def recipe_validation(request: Request):
    payload=await read_payload(request)
    return validate_recipe(payload.get('recipe'))


@app.post('/api/automation')
async def document_automation(request: Request):
    payload=await read_payload(request);items=batch_sources(payload);review=payload.get('review',False)
    result=await run_in_threadpool(process_recipe,items,payload.get('recipe'),payload.get('secrets'),review)
    if review:return result
    return Response(result,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="Reapdf-receta.zip"'})


@app.post('/api/batch')
async def document_batch(request: Request):
    payload=await read_payload(request);items=batch_sources(payload)
    review=payload.get('review',False)
    result=await run_in_threadpool(process_batch,items,payload.get('action'),payload.get('settings',{}),review)
    if review:return result
    return Response(result,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="Reapdf-lote.zip"'})


@app.post('/api/documents/{doc_id}/inspect-links')
async def existing_link_source(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_links,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'))


@app.post('/api/documents/{doc_id}/edit-link')
async def change_existing_link(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(edit_link,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('xref'),payload.get('action'),payload.get('changes'))
    if payload.get('preview') is True:
        with open_pdf(result) as doc:image,headers=render_page(doc[payload['page']],1.5)
        return Response(image,media_type='image/png',headers=headers)
    return store_document(result)


@app.post('/api/documents/{doc_id}/paragraph-preview')
async def text_editing_preview(doc_id: str, request: Request):
    payload=await read_payload(request)
    image,headers=await run_in_threadpool(paragraph_preview,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('scale',1))
    return Response(image,media_type='image/png',headers=headers)


@app.post('/api/documents/{doc_id}/paragraph-blocks')
async def detect_paragraphs(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(paragraph_blocks,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'))


@app.post('/api/documents/{doc_id}/inspect-paragraph')
async def paragraph_source(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_paragraph,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('box'))


@app.post('/api/documents/{doc_id}/inspect-styled-text')
async def styled_text_source(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_styled,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('box'))

@app.post('/api/documents/{doc_id}/find-replace')
async def find_replace_source(doc_id:str,request:Request):
    p=await read_payload(request)
    return await run_in_threadpool(inspect_replace,document_path(doc_id).read_bytes(),p.get('operations',[]),p.get('query'))

@app.post('/api/documents/{doc_id}/find-replace/apply')
async def find_replace_apply(doc_id:str,request:Request):
    p=await read_payload(request);base=document_path(doc_id).read_bytes()
    result,token,count=await run_in_threadpool(batch_replace,base,p.get('operations',[]),p.get('query'),p.get('receipt'),p.get('selected'),p.get('replacement'))
    if p.get('preview') is True:
        inspection=await run_in_threadpool(inspect_replace,base,p.get('operations',[]),p.get('query'))
        pages=sorted({m['page'] for m in inspection['matches'] if m['id'] in p['selected']})
        images=[]
        for number in pages[:3]:
            image,_=await run_in_threadpool(paragraph_preview,result,[],number,1)
            images.append({'page':number,'image':base64.b64encode(image).decode()})
        return {'token':token,'count':count,'images':images,'previewed_pages':pages[:3],'total_pages':len(pages)}
    if p.get('preview_token')!=token:raise DocumentError('Prepara de nuevo la vista previa del reemplazo.')
    return store_document(result)

@app.post('/api/documents/{doc_id}/replace-styled-text')
async def change_styled_text(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(replace_styled,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('box'),payload.get('changes'),payload.get('expand',False))
    if payload.get('preview') is True:
        image,headers=await run_in_threadpool(paragraph_preview,result,[],payload['page'],1.5)
        return Response(image,media_type='image/png',headers=headers)
    return store_document(result)

@app.post('/api/documents/{doc_id}/inspect-flow')
async def inspect_text_flow(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_flow,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('regions'))


@app.post('/api/documents/{doc_id}/flow-text')
async def apply_text_flow(doc_id: str, request: Request):
    payload=await read_payload(request);base=document_path(doc_id).read_bytes();ops=payload.get('operations',[])
    result,report=await run_in_threadpool(flow_text,base,ops,payload.get('regions'),payload.get('text'),payload.get('size',12),payload.get('family','sans'),payload.get('style','regular'),payload.get('color'),payload.get('align',0),payload.get('line_height',1.2),payload.get('auto_fit',False),payload.get('min_size',8),payload.get('runs'),payload.get('original_runs'))
    if payload.get('preview') is True:
        def previews():
            rows=[]
            with open_pdf(export_pdf(base,ops)) as old,open_pdf(result) as after:
                for number in report['pages']:
                    row={'page':number}
                    for label,doc in [('original',old),('result',after)]:
                        page=doc[number];page.set_rotation(0);scale=min(1,600/max(page.rect.width,page.rect.height))
                        row[label]='data:image/png;base64,'+base64.b64encode(page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False).tobytes('png')).decode()
                    rows.append(row)
            return rows
        return {'report':report,'previews':await run_in_threadpool(previews)}
    return store_document(result)


@app.post('/api/import/docx')
async def import_word(file: UploadFile, paper: str=Form('source')):
    data=await file.read(MAX_DOCX_INPUT+1);name=file.filename or 'Word.docx';await file.close()
    result,report=await run_in_threadpool(import_docx,data,paper)
    return {'document':store_document(result),'report':report,'name':Path(name).stem[:160]+'.pdf'}


@app.post('/api/documents/{doc_id}/review-form-rules')
async def review_form_rules(doc_id: str, request: Request):
    payload=await read_payload(request);base=document_path(doc_id).read_bytes();ops=payload.get('operations',[])
    if not isinstance(ops,list):raise DocumentError('Operaciones no válidas.')
    rules=payload.get('rules');next_ops=[op for op in ops if not isinstance(op,dict) or op.get('type')!='form_rules']
    if rules!=[]:next_ops.append({'type':'form_rules','page':0,'version':1,'rules':rules})
    effective,reports,targets=await run_in_threadpool(resolve_rules,base,next_ops)
    await run_in_threadpool(export_pdf,base,next_ops)
    return {'reports':reports,'target_groups':sorted(targets),'operations':next_ops}


@app.post('/api/documents/{doc_id}/repair-calculation-order')
async def repair_native_calculation_order(doc_id:str,request:Request):
    from .native_calculations import repair_order
    payload=await read_payload(request)
    data,report=await run_in_threadpool(repair_order,document_path(doc_id).read_bytes(),payload.get('operations',[]))
    return {**store_document(data),'calculation_order_report':report}


@app.post('/api/documents/{doc_id}/calculate-fields')
async def calculate_form_fields(doc_id: str, request: Request):
    payload=await read_payload(request);base=document_path(doc_id).read_bytes()
    operations,report=await run_in_threadpool(calculate_fields,base,payload.get('operations',[]),payload.get('calculation'))
    if payload.get('preview') is True:
        number=payload['calculation']['target']['page']
        with open_pdf(export_pdf(base,operations)) as doc:image,_=render_page(doc[number],1)
        return {'report':report,'preview':'data:image/png;base64,'+base64.b64encode(image).decode()}
    return {'operations':operations,'report':report}


@app.post('/api/documents/{doc_id}/replace-paragraph')
async def change_paragraph(doc_id: str, request: Request):
    payload=await read_payload(request)
    result,report=await run_in_threadpool(replace_paragraph,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('box'),payload.get('text'),payload.get('size',12),payload.get('color'),payload.get('align',0),payload.get('family','sans'),payload.get('style','regular'),payload.get('line_height',1.2),payload.get('auto_fit',False),payload.get('min_size',6),True)
    if payload.get('preview') is True:
        image,headers=await run_in_threadpool(paragraph_preview,result,[],payload['page'],1.5)
        headers['X-Reapdf-Layout']=json.dumps(report)
        return Response(image,media_type='image/png',headers=headers)
    return store_document(result)


@app.get('/api/documents/{doc_id}/pages/{number}/existing-images')
def existing_images(doc_id: str, number: int):
    with open_pdf(document_path(doc_id).read_bytes()) as doc:return image_model(doc,number)


@app.post('/api/documents/{doc_id}/edit-image')
async def change_existing_image(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=edit_image(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('xref'),payload.get('action'),payload.get('box'),payload.get('data'))
    if payload.get('preview') is True:
        with open_pdf(result) as doc:
            image,headers=render_page(doc[payload['page']],1.5)
        return Response(image,media_type='image/png',headers=headers)
    return store_document(result)


@app.get('/api/standards/status')
def standards_capabilities():return standard_status()


@app.post('/api/documents/{doc_id}/validate-standard')
async def standards_validation(doc_id: str,request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(validate_standard,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('profile','2b'))


@app.post('/api/documents/{doc_id}/archive-pdfa')
async def archive_pdf(doc_id: str,request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(archival_copy,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('review') is True)
    if payload.get('review') is True:return result
    content,report=result
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="Reapdf-archivo-PDFA-2b.pdf"','X-Reapdf-Archive-Report':json.dumps({k:v for k,v in report.items() if k!='preview'},separators=(',',':'),ensure_ascii=True)})


@app.post('/api/documents/{doc_id}/accessibility')
async def accessibility_review(doc_id: str,request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_accessibility,document_path(doc_id).read_bytes(),payload.get('operations',[]))


@app.post('/api/documents/{doc_id}/prepare-accessibility')
async def accessibility_prepare(doc_id: str,request: Request):
    payload=await read_payload(request)
    content=await run_in_threadpool(prepare_accessibility,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('title'),payload.get('language'),payload.get('display_title',True))
    return store_document(content)


@app.post('/api/documents/{doc_id}/export-docx')
async def export_word_document(doc_id: str, request: Request):
    payload=await read_payload(request)
    result,report=await run_in_threadpool(export_docx,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('pages'),payload.get('keep_lines',True),payload.get('include_images',False),payload.get('include_tables',False),payload.get('include_links',False))
    if payload.get('review') is True:return report
    return Response(result,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':'attachment; filename="Reapdf-texto.docx"'})


@app.post('/api/documents/{doc_id}/comments')
async def review_comments(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_comments,document_path(doc_id).read_bytes(),payload.get('operations',[]))


@app.post('/api/documents/{doc_id}/edit-comment')
async def change_review_comment(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(edit_comment,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('xref'),payload.get('action'),payload.get('content'),payload.get('author',''),payload.get('state'))
    return store_document(result)


@app.post('/api/documents/{doc_id}/comment-report')
async def export_review_comments(doc_id: str, request: Request):
    payload=await read_payload(request);format=payload.get('format','json')
    result=await run_in_threadpool(comment_report,document_path(doc_id).read_bytes(),payload.get('operations',[]),format)
    return Response(result,media_type='application/json' if format=='json' else 'text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="Reapdf-comentarios.{format}"'})


@app.post('/api/documents/{doc_id}/field-properties')
async def field_property_source(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(inspect_properties,document_path(doc_id).read_bytes(),payload.get('operations',[]))


@app.post('/api/documents/{doc_id}/edit-field-properties')
async def change_field_properties(doc_id: str, request: Request):
    payload=await read_payload(request)
    base=document_path(doc_id).read_bytes();operations=payload.get('operations',[])
    result=await run_in_threadpool(edit_properties,base,operations,payload.get('page'),payload.get('xref'),payload.get('changes'))
    from .form_rules import remap_field_rules
    project_operations=remap_field_rules(base,operations,result,payload.get('page'),payload.get('xref'),payload.get('changes'))
    if payload.get('preview') is True:
        with open_pdf(result) as doc:image,headers=render_page(doc[payload['page']],1.5)
        return Response(image,media_type='image/png',headers=headers)
    return {**store_document(result),'project_operations':project_operations}


@app.post('/api/documents/{doc_id}/create-field')
async def add_form_field(doc_id: str, request: Request):
    payload=await read_payload(request)
    base=document_path(doc_id).read_bytes();operations=payload.get('operations',[])
    result=await run_in_threadpool(create_field,base,operations,payload.get('config'))
    from .form_rules import remap_rules
    project_operations=remap_rules(base,operations,result)
    if payload.get('preview') is True:
        with open_pdf(result) as doc:image,headers=render_page(doc[payload['config']['page']],1.5)
        return Response(image,media_type='image/png',headers=headers)
    return {**store_document(result),'project_operations':project_operations}


@app.post('/api/documents/{doc_id}/delete-field')
async def remove_form_field(doc_id: str, request: Request):
    payload=await read_payload(request)
    base=document_path(doc_id).read_bytes();operations=payload.get('operations',[])
    result=delete_field(base,operations,payload.get('page'),payload.get('xref'))
    return store_project_version(base,operations,result)


@app.post('/api/documents/{doc_id}/compare')
async def compare_documents(doc_id: str, request: Request):
    payload=await read_payload(request);reference=payload.get('reference_id')
    if not isinstance(reference,str):raise DocumentError('Elige un PDF de referencia.')
    return await run_in_threadpool(compare_pdf,document_path(doc_id).read_bytes(),payload.get('operations',[]),document_path(reference).read_bytes())



async def read_signature_upload(file,limit,label):
    try:data=await file.read(limit+1)
    finally:await file.close()
    if not data or len(data)>limit:raise DocumentError(f'{label}: archivo vacío o superior al límite permitido.')
    return data


def signature_payload(payload):
    if not isinstance(payload,str) or len(payload)>5*1024*1024:raise DocumentError('Demasiados datos de firma.')
    try:value=json.loads(payload)
    except (ValueError,TypeError):raise DocumentError('Solicitud de firma no válida.') from None
    if not isinstance(value,dict):raise DocumentError('Solicitud de firma no válida.')
    return value


@app.post('/api/certificates/inspect')
async def certificate_details(file: UploadFile,password: str=Form('')):
    data=await read_signature_upload(file,MAX_IDENTITY,'Certificado P12/PFX')
    return await run_in_threadpool(inspect_identity,data,password)


@app.post('/api/documents/{doc_id}/digital-sign')
async def digital_signature(doc_id: str,file: UploadFile,password: str=Form(''),payload: str=Form('{}')):
    data=await read_signature_upload(file,MAX_IDENTITY,'Certificado P12/PFX');config=signature_payload(payload)
    result=await run_in_threadpool(sign_document,document_path(doc_id).read_bytes(),config.get('operations',[]),data,password,config.get('config',{}),config.get('review') is True)
    if config.get('review') is True:return result
    return Response(result,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="Reapdf-firmado.pdf"'})


@app.post('/api/documents/{doc_id}/verify-signatures')
async def signature_verification(doc_id: str,payload: str=Form('{}'),trust: UploadFile | None=None):
    config=signature_payload(payload)
    anchors=await read_signature_upload(trust,MAX_TRUST,'Certificados públicos de confianza') if trust else b''
    return await run_in_threadpool(verify_signatures,document_path(doc_id).read_bytes(),config.get('operations',[]),anchors)


@app.post('/api/documents/{doc_id}/visual-signature')
async def signature(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=visual_signature(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('page'),payload.get('box'),payload.get('strokes'),payload.get('name',''))
    if payload.get('preview') is True:
        with open_pdf(result) as doc:
            png,headers=render_page(doc[payload['page']],1.5)
            return Response(png,media_type='image/png',headers=headers)
    return store_document(result)

@app.post('/api/documents/{doc_id}/compress-images')
async def compressed_images(doc_id: str, request: Request):
    payload=await read_payload(request)
    result,report=await run_in_threadpool(compress_images,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('dpi'),payload.get('quality'))
    if payload.get('preview') is True:
        number=payload.get('page',0)
        with open_pdf(result) as doc:
            if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página de comparación no válida.')
            png,_=render_page(doc[number],1.5)
        import base64
        return {**report,'preview':'data:image/png;base64,'+base64.b64encode(png).decode()}
    return Response(result,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="reapdf-comprimido.pdf"','X-PDF-SHA256':report['sha256']})

@app.post('/api/documents/{doc_id}/redact')
async def redaction(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(redact_pdf,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('regions'))
    if payload.get('preview') is True:
        with open_pdf(result) as doc:
            number=payload.get('preview_page',payload['regions'][0]['page'])
            if type(number) is not int or number not in {r['page'] for r in payload['regions']}:
                raise DocumentError('Selecciona una página con regiones de censura para revisar.')
            png,headers=render_page(doc[number],1.5)
            return Response(png,media_type='image/png',headers=headers)
    return Response(result,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="reapdf-censurado.pdf"'})

@app.post('/api/documents/{doc_id}/redact/search')
async def redaction_candidates(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(search_redactions,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('query'))

@app.post('/api/documents/{doc_id}/redact/search/apply')
async def redaction_matches(doc_id: str, request: Request):
    payload=await read_payload(request)
    result,pages=await run_in_threadpool(redact_search,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('query'),payload.get('receipt'),payload.get('selected'))
    if payload.get('preview') is True:
        number=payload.get('preview_page')
        if type(number) is not int or number not in pages:
            raise DocumentError('Selecciona una página con coincidencias elegidas para revisar.')
        with open_pdf(result) as doc:
            png,headers=render_page(doc[number],1.5)
            return Response(png,media_type='image/png',headers=headers)
    return Response(result,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="reapdf-censurado.pdf"'})

@app.get('/api/documents/{doc_id}/labels')
def get_labels(doc_id: str):return {'rules':label_rules(document_path(doc_id).read_bytes())}

@app.post('/api/documents/{doc_id}/labels')
async def set_labels(doc_id: str, request: Request):
    payload=await read_payload(request)
    return store_document(labels_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('rules')))

@app.get('/api/documents/{doc_id}/portfolio')
def portfolio_info(doc_id: str):
    from .portfolios import model
    return model(document_path(doc_id).read_bytes())

@app.post('/api/documents/{doc_id}/configure-portfolio')
async def configure_portfolio(doc_id: str, request: Request):
    from .portfolios import configure
    payload=await read_payload(request)
    result=await run_in_threadpool(configure,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('enabled'),payload.get('view','details'),payload.get('files'))
    return store_document(result)

@app.get('/api/documents/{doc_id}/attachments')
def attachments(doc_id: str):return {'files':attachment_model(document_path(doc_id).read_bytes())}

@app.post('/api/documents/{doc_id}/add-attachment')
async def attach(doc_id: str, file: UploadFile, operations: str = Form('[]')):
    data=await file.read(8*1024*1024+1);await file.close()
    try:ops=json.loads(operations)
    except ValueError as exc:raise DocumentError('Operaciones no válidas.') from exc
    return store_document(add_attachment(document_path(doc_id).read_bytes(),ops,file.filename,data))

@app.post('/api/documents/{doc_id}/delete-attachment')
async def detach(doc_id: str, request: Request):
    payload=await read_payload(request)
    return store_document(attachment_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('index')))

@app.get('/api/documents/{doc_id}/attachments/{index}')
def attachment_download(doc_id: str, index: int):
    from urllib.parse import quote
    data,name=download_attachment(document_path(doc_id).read_bytes(),index)
    return Response(data,media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename=adjunto; filename*=UTF-8''"+quote(name),'X-Content-Type-Options':'nosniff'})

@app.post('/api/documents/{doc_id}/tables')
async def tables(doc_id: str, request: Request):
    payload=await read_payload(request)
    return await run_in_threadpool(extract_tables,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('pages'),payload.get('strategy','lines'))

@app.post('/api/documents/{doc_id}/export-tables')
async def table_download(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=await run_in_threadpool(extract_tables,document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('pages'),payload.get('strategy','lines'))
    return Response(tables_zip(result),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="reapdf-tablas.zip"'})

@app.post('/api/bates')
async def bates(request: Request):
    payload=await read_payload(request);entries=payload.get('items')
    if not isinstance(entries,list) or not 1<=len(entries)<=10:raise DocumentError('Selecciona de 1 a 10 documentos para Bates.')
    items=[];seen=set()
    for item in entries:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('name'),str) or item['id'] in seen:raise DocumentError('Lote no válido o documento repetido.')
        seen.add(item['id']);items.append((item['name'],document_path(item['id']).read_bytes(),item.get('operations',[])))
    result=await run_in_threadpool(bates_batch,items,payload.get('prefix',''),payload.get('suffix',''),payload.get('start',1),payload.get('padding',6))
    if payload.get('preview') is True:
        from io import BytesIO
        from zipfile import ZipFile
        with ZipFile(BytesIO(result)) as archive:
            with open_pdf(archive.read(archive.namelist()[0])) as doc:
                png,headers=render_page(doc[0],1.5)
                return Response(png,media_type='image/png',headers=headers)
    return Response(result,media_type='application/zip',headers={'Content-Disposition':'attachment; filename="reapdf-bates.zip"'})

@app.get('/api/ocr')
def available_ocr():return ocr_status()


@app.post('/api/documents/{doc_id}/form-data')
async def download_form_data(doc_id: str, request: Request):
    payload=await read_payload(request)
    data=export_form_data(document_path(doc_id).read_bytes(),payload.get('operations',[]))
    return Response(json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8'),media_type='application/json',headers={'Content-Disposition':'attachment; filename="reapdf-formulario.json"'})


@app.post('/api/documents/{doc_id}/import-form-data')
async def load_form_data(doc_id: str, request: Request):
    payload=await read_payload(request)
    return {'operations':import_form_data(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('data'))}


@app.post('/api/documents/{doc_id}/flatten-form')
async def bake_form(doc_id: str, request: Request):
    payload=await read_payload(request)
    return store_document(flatten_form(document_path(doc_id).read_bytes(),payload.get('operations',[])))


@app.post('/api/documents/{doc_id}/ocr')
async def recognize(doc_id: str, request: Request):
    payload=await read_payload(request);base=document_path(doc_id).read_bytes()
    if not OCR_LOCK.acquire(blocking=False):raise HTTPException(409,'Ya hay un reconocimiento OCR en curso. Espera a que termine.')
    try:
        result,report=await run_in_threadpool(ocr_pdf,base,payload.get('operations',[]),payload.get('pages'),payload.get('language','spa+eng'),payload.get('dpi',200),payload.get('orientation',0))
        return {'document':store_document(result) if report['processed'] else None,'report':report}
    finally:OCR_LOCK.release()


@app.post('/api/documents/{doc_id}/export-text')
async def download_text(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=export_text(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('pages'))
    return Response(result,media_type='text/plain; charset=utf-8',headers={'Content-Disposition':'attachment; filename="reapdf-texto.txt"'})


@app.get('/api/documents/{doc_id}/metadata')
def document_metadata(doc_id: str):return read_metadata(document_path(doc_id).read_bytes())


@app.post('/api/documents/{doc_id}/metadata')
async def change_metadata(doc_id: str, request: Request):
    payload=await read_payload(request)
    return store_document(metadata_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('values'),payload.get('remove_xml',False)))


@app.post('/api/documents/{doc_id}/optimize')
async def optimize_document(doc_id: str, request: Request):
    payload=await read_payload(request)
    result,report=optimize_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]))
    return {'document':store_document(result),'report':report}


@app.post('/api/documents/{doc_id}/protect')
async def protected_copy(doc_id: str, request: Request):
    payload=await read_payload(request)
    result=protect_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]),payload.get('password'),payload.get('owner_password'),payload.get('allow_copy',True),payload.get('allow_print',True))
    return Response(result,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="reapdf-protegido.pdf"'})


@app.post("/api/documents/{doc_id}/bookmarks")
async def editable_bookmarks(doc_id: str, request: Request):
    payload=await read_payload(request)
    data=export_pdf(document_path(doc_id).read_bytes(),payload.get('operations',[]))
    with open_pdf(data) as doc:return bookmark_model(doc)

@app.post("/api/documents/{doc_id}/search")
async def search(doc_id: str, request: Request):
    payload = await read_payload(request)
    data = export_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []))
    with open_pdf(data) as doc:
        return search_document(doc, payload.get("query"))

@app.post("/api/documents/{doc_id}/pages/{number}/text")
async def selectable_text(doc_id: str, number: int, request: Request):
    payload = await read_payload(request)
    data = export_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []))
    with open_pdf(data) as doc:
        if not 0 <= number < len(doc):
            raise HTTPException(404, "Página no encontrada.")
        return {"items": text_items(doc[number]), **review_selection(doc[number]), **page_links(doc[number])}

@app.post("/api/documents/{doc_id}/pages/{number}/thumbnail")
async def thumbnail(doc_id: str, number: int, request: Request):
    payload = await read_payload(request)
    data = export_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []))
    with open_pdf(data) as doc:
        if not 0 <= number < len(doc):
            raise HTTPException(404, "Página no encontrada.")
        import pymupdf
        page = doc[number]
        scale = min(150 / page.rect.width, 200 / page.rect.height)
        return Response(page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png"), media_type="image/png")

@app.post("/api/documents/{doc_id}/pages/{number}/preview")
async def preview(doc_id: str, number: int, request: Request):
    payload = await read_payload(request)
    data = export_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []))
    with open_pdf(data) as doc:
        if not 0 <= number < len(doc):
            raise HTTPException(404, "Página no encontrada.")
        image, headers = render_page(doc[number], payload.get('scale', 1.5))
        return Response(image, media_type="image/png", headers=headers)

def project_state(payload):
    return {key: payload.get(key, default) for key, default in
            [('name', 'Documento.pdf'), ('page', 0), ('zoom', 1), ('base_changes', 0)]}


def restored_document(base, operations, manifest):
    return {"document": store_document(base), "operations": operations, "state": manifest['state']}


@app.post("/api/projects/open")
async def open_project(file: UploadFile):
    data = await file.read(MAX_PROJECT + 1)
    await file.close()
    base, operations, manifest = read_project(data)
    return restored_document(base, operations, manifest)


@app.post("/api/documents/{doc_id}/project")
async def save_project(doc_id: str, request: Request):
    payload = await read_payload(request)
    data, _ = build_project(document_path(doc_id).read_bytes(), payload.get('operations', []), project_state(payload))
    return Response(data, media_type='application/zip', headers={'Content-Disposition': 'attachment; filename="proyecto.reapdf"', 'Cache-Control': 'no-store'})


@app.get("/api/recovery")
def recovery_status():
    return app.state.recovery.status()


@app.post("/api/documents/{doc_id}/recovery")
async def save_recovery(doc_id: str, request: Request):
    payload = await read_payload(request)
    data, manifest = build_project(document_path(doc_id).read_bytes(), payload.get('operations', []), project_state(payload))
    revision = app.state.recovery.save(data, payload.get('revision'))
    return {'revision': revision, 'saved_at': manifest['saved_at']}


@app.post("/api/recovery/restore")
async def restore_recovery(request: Request):
    payload = await read_payload(request)
    base, operations, manifest = app.state.recovery.read(payload.get('revision'))
    return restored_document(base, operations, manifest)


@app.delete("/api/recovery")
async def delete_recovery(request: Request):
    payload = await read_payload(request)
    app.state.recovery.delete(payload.get('revision'))
    return {'available': False, 'revision': None}


@app.post("/api/documents/{doc_id}/duplicate")
async def duplicate(doc_id: str, request: Request):
    payload = await read_payload(request)
    base = document_path(doc_id).read_bytes()
    operations = payload.get("operations", [])
    result = duplicate_pdf(base, operations, payload.get('pages'), payload.get('position'))
    from .form_rules import splice_page_map
    return store_project_version(base, operations, result, splice_page_map(base, payload['position'], 0, len(payload['pages'])))


@app.post("/api/documents/{doc_id}/blank")
async def add_blank(doc_id: str, request: Request):
    payload = await read_payload(request)
    base = document_path(doc_id).read_bytes()
    operations = payload.get("operations", [])
    result = blank_pdf(base, operations, payload.get('position'),
                       payload.get('count'), payload.get('width'), payload.get('height'))
    from .form_rules import splice_page_map
    return store_project_version(base, operations, result, splice_page_map(base, payload['position'], 0, payload.get('count')))


@app.post("/api/documents/{doc_id}/print")
async def print_document(doc_id: str, request: Request):
    payload = await read_payload(request)
    data = document_path(doc_id).read_bytes()
    with open_pdf(data) as doc:
        if not (doc.permissions & pymupdf.PDF_PERM_PRINT and doc.permissions & pymupdf.PDF_PERM_PRINT_HQ):
            raise HTTPException(403, 'El documento no permite impresión de alta calidad. La impresión con permisos de baja resolución sigue pendiente.')
    result = export_pdf(data, payload.get('operations', []))
    return Response(result, media_type='application/pdf', headers={'Content-Disposition': 'inline; filename="reapdf-impresion.pdf"', 'Cache-Control': 'no-store'})


@app.post("/api/documents/{doc_id}/organize")
async def organize(doc_id: str, request: Request):
    payload = await read_payload(request)
    from .form_rules import remap_organized_rules
    base = document_path(doc_id).read_bytes()
    operations, pages = payload.get("operations", []), payload.get("pages")
    result = organize_pdf(base, operations, pages)
    project_operations = remap_organized_rules(base, operations, result, pages)
    return {**store_document(result), 'project_operations': project_operations}

@app.post("/api/documents/{doc_id}/insert")
async def insert(doc_id: str, request: Request):
    payload = await read_payload(request)
    base = document_path(doc_id).read_bytes()
    operations = payload.get("operations", [])
    source_id = payload.get("source_id")
    if not isinstance(source_id, str):
        raise HTTPException(422, "Selecciona un PDF de origen válido.")
    result = merge_pdf(base, operations,
                       document_path(source_id).read_bytes(), payload.get("pages"),
                       payload.get("position"), payload.get("source_name", "Documento insertado"))
    from .form_rules import splice_page_map
    return store_project_version(base, operations, result, splice_page_map(base, payload['position'], 0, len(payload['pages'])))

@app.post("/api/documents/{doc_id}/replace")
async def replace(doc_id: str, request: Request):
    payload = await read_payload(request)
    base = document_path(doc_id).read_bytes()
    operations = payload.get("operations", [])
    source_id, count = payload.get("source_id"), payload.get("replace_count")
    if not isinstance(source_id, str) or type(count) is not int or count < 1:
        raise DocumentError("Selecciona el PDF de origen y cuántas páginas quieres reemplazar.")
    result = merge_pdf(base, operations,
                       document_path(source_id).read_bytes(), payload.get("pages"),
                       payload.get("position"), payload.get("source_name", "Documento de reemplazo"), replace_count=count)
    from .form_rules import splice_page_map
    return store_project_version(base, operations, result, splice_page_map(base, payload['position'], count, len(payload['pages'])))

@app.post("/api/documents/{doc_id}/crop")
async def crop(doc_id: str, request: Request):
    payload = await read_payload(request)
    base = document_path(doc_id).read_bytes()
    operations = payload.get("operations", [])
    result = crop_pdf(base, operations,
                      payload.get("pages"), payload.get("margins"), reset=payload.get("reset", False))
    return store_project_version(base, operations, result)

@app.post('/api/documents/{doc_id}/split-plan')
async def split_plan(doc_id:str,request:Request):
    from .page_tools import inspect_split
    p=await read_payload(request)
    return await run_in_threadpool(inspect_split,document_path(doc_id).read_bytes(),p.get('operations',[]),size=p.get('size'),groups=p.get('groups'),names=p.get('names'),bookmark_level=p.get('bookmark_level'))

@app.post("/api/documents/{doc_id}/split")
async def split(doc_id: str, request: Request):
    payload = await read_payload(request)
    result = await run_in_threadpool(split_pdf,document_path(doc_id).read_bytes(), payload.get("operations", []),
                       size=payload.get("size"), groups=payload.get("groups"),names=payload.get("names"),bookmark_level=payload.get("bookmark_level"),manifest=payload.get("manifest",False))
    return Response(result, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="reapdf-dividido.zip"'})

@app.post("/api/documents/{doc_id}/extract")
async def extract(doc_id: str, request: Request):
    payload = await read_payload(request)
    result = organize_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []), payload.get("pages"), extract=True)
    return Response(result, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="reapdf-extraido.pdf"'})

@app.post("/api/documents/{doc_id}/export")
async def export(doc_id: str, request: Request):
    payload = await read_payload(request)
    result = export_pdf(document_path(doc_id).read_bytes(), payload.get("operations", []))
    return Response(result, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="reapdf-editado.pdf"'})

DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

@app.get("/")
def index():
    if not (DIST / "index.html").exists():
        raise HTTPException(503, "Ejecuta npm run build para preparar la interfaz.")
    return FileResponse(DIST / "index.html")
