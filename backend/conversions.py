"""Conversión local entre imágenes y PDF con límites explícitos de resolución."""
import base64
from io import BytesIO
import math
from zipfile import ZipFile, ZIP_STORED
import pymupdf as fitz
from .engine import DocumentError, open_pdf, export_pdf, finite
from .images import prepare_image, image_dimensions, MAX_IMAGE_BYTES

MAX_FILES=30
MAX_INPUT=20*1024*1024
MAX_OUTPUT=100*1024*1024
MAX_TOTAL_PIXELS=120_000_000


def images_to_pdf(images, paper='A4', dpi=150, margin=18):
    if not isinstance(images,list) or not 1<=len(images)<=MAX_FILES or any(not isinstance(data,bytes) or not data or len(data)>MAX_IMAGE_BYTES for data in images):
        raise DocumentError('Selecciona de 1 a 30 imágenes PNG/JPEG, hasta 2 MB por imagen.')
    if sum(map(len,images))>MAX_INPUT:raise DocumentError('Las imágenes superan 20 MB en total.')
    if not isinstance(paper,str) or paper not in {'A4','Letter','image'} or type(dpi) is not int or not 72<=dpi<=600 or not finite(margin) or not 0<=margin<=144:
        raise DocumentError('Elige A4, Carta o tamaño de imagen, resolución de 72–600 ppp y margen de 0–144 pt.')
    with fitz.open() as doc:
        for data in images:
            if not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):raise DocumentError('Solo se admiten archivos PNG o JPEG.')
            width,height=image_dimensions(data)
            if width<=0 or height<=0 or width*height>24_000_000:raise DocumentError('La imagen supera 24 millones de píxeles o no es válida.')
            page_width,page_height=(width*72/dpi+2*margin,height*72/dpi+2*margin) if paper=='image' else fitz.paper_size(paper)
            if max(page_width,page_height)>3000 or min(page_width,page_height)<10 or min(page_width,page_height)<=2*margin+1:
                raise DocumentError('El tamaño o margen no deja una página válida (10–3000 pt).')
            page=doc.new_page(width=page_width,height=page_height)
            page_width,page_height=page.rect.width,page.rect.height
            factor=min((page_width-2*margin)/width,(page_height-2*margin)/height)
            w,h=width*factor,height*factor;x,y=(page_width-w)/2,(page_height-h)/2
            _,checked=prepare_image(page,{'data':base64.b64encode(data).decode(),'points':[[x,y],[x+w,y+h]]})
            # El JPEG mantiene su flujo comprimido; no se redimensionan píxeles.
            page.insert_image(fitz.Rect(x,y,x+w,y+h),stream=checked,keep_proportion=True)
        return doc.tobytes(garbage=4,deflate=True)


def export_page_images(data,operations,pages,dpi=150,format='png',quality=90):
    if type(dpi) is not int or not 72<=dpi<=600 or not isinstance(format,str) or format not in {'png','jpeg'} or type(quality) is not int or not 50<=quality<=100:
        raise DocumentError('Elige PNG o JPEG, resolución de 72–600 ppp y calidad JPEG de 50–100.')
    with open_pdf(data) as source:
        if not source.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer su contenido como imágenes.')
        if not isinstance(pages,list) or not 1<=len(pages)<=50 or any(type(n) is not int or not 0<=n<len(source) for n in pages) or len(set(pages))!=len(pages):
            raise DocumentError('Elige de 1 a 50 páginas válidas sin repeticiones.')
        total=0
        for number in pages:
            page=source[number];width=math.ceil(page.rect.width*dpi/72);height=math.ceil(page.rect.height*dpi/72)
            if max(width,height)>8192 or width*height>24_000_000:raise DocumentError(f'La página {number+1} supera 24 millones de píxeles u 8192 px por lado. Reduce la resolución.')
            total+=width*height
        if total>MAX_TOTAL_PIXELS:raise DocumentError('El lote supera 120 millones de píxeles. Reduce páginas o resolución.')
    edited=export_pdf(data,operations)
    output=BytesIO()
    with open_pdf(edited) as doc,ZipFile(output,'w',ZIP_STORED) as archive:
        for index,number in enumerate(pages):
            pix=doc[number].get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72),alpha=False,annots=True)
            pix.set_dpi(dpi,dpi)
            encoded=pix.tobytes('png') if format=='png' else pix.tobytes('jpeg',jpg_quality=quality)
            if output.tell()+len(encoded)>MAX_OUTPUT:raise DocumentError('El archivo supera 100 MB. Reduce páginas o resolución.')
            archive.writestr(f'{index+1:03d}-pagina-{number+1:03d}.{format if format=="png" else "jpg"}',encoded)
    return output.getvalue()
