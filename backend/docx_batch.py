"""Atomic local DOCX batch conversion with per-file loss reports and digests."""
import base64,hashlib,json
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pymupdf as f
from .engine import DocumentError
from .docx_import import import_docx,read_package
from .automation import output_name


def convert(items,paper='source',review=False):
    if type(review) is not bool or paper not in ['source','A4','Letter']:raise DocumentError('Opciones de conversión Word por lotes no válidas.')
    if not isinstance(items,list) or not 1<=len(items)<=10:raise DocumentError('Selecciona de 1 a 10 archivos DOCX.')
    total=0
    for i,item in enumerate(items,1):
        if not isinstance(item,(tuple,list)) or len(item)!=2 or not isinstance(item[0],str) or not 1<=len(item[0])<=255 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in item[0]) or not isinstance(item[1],bytes):raise DocumentError('Nombre o archivo Word de lote no válido.')
        total+=len(item[1])
        if total>40*1024*1024:raise DocumentError('El lote Word supera 40 MB de entrada.')
        try:read_package(item[1])
        except DocumentError as e:raise DocumentError(f'Word {i}: {e}') from e
    report={'format':'reapdf-docx-batch','version':1,'documents':[],'input_bytes':total,'pages':0,'output_bytes':0,'source_modified':False};outputs=[]
    for i,(name,data) in enumerate(items,1):
        try:pdf,details=import_docx(data,paper)
        except DocumentError as e:raise DocumentError(f'Word {i}: {e}') from e
        report['pages']+=details['pages'];report['output_bytes']+=len(pdf)
        if report['pages']>100 or report['output_bytes']>100*1024*1024:raise DocumentError('El lote convertido supera 100 páginas o 100 MB; no se entrega un resultado parcial.')
        row={'name':name,'file':output_name('{name}',name,'Word',i,'.pdf'),'pages':details['pages'],'input_sha256':hashlib.sha256(data).hexdigest(),'output_sha256':hashlib.sha256(pdf).hexdigest(),'report':details}
        if review:
            with f.open(stream=pdf) as d:
                page=d[0];scale=min(1,600/max(page.rect.width,page.rect.height));row['preview']='data:image/png;base64,'+base64.b64encode(page.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False).tobytes('png')).decode()
        else:outputs.append((row['file'],pdf))
        report['documents'].append(row)
    if review:return report
    stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        for name,data in outputs:archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
    return stream.getvalue()
