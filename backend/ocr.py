"""OCR local: superpone solo texto invisible y conserva imágenes/contenido originales."""
from pathlib import Path
from hashlib import sha256
import json
import math
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError

TESSDATA=Path(__file__).resolve().parent.parent/'resources'/'tessdata'


def ocr_status():
    available=[]
    try:
        manifest=json.loads((TESSDATA/'manifest.json').read_text())
        for item in manifest['files']:
            lang=item['language']
            if lang in {'eng','spa'} and sha256((TESSDATA/f'{lang}.traineddata').read_bytes()).hexdigest()==item['sha256']:available.append(lang)
    except (OSError,ValueError,KeyError,TypeError):pass
    return {'languages':available,'max_pages':10,'max_pixels':16_000_000}


def ocr_pdf(base,operations,pages,language='spa+eng',dpi=200,orientation=0):
    if language not in ['eng','spa','spa+eng'] or type(dpi) is not int or dpi not in [150,200,300]:raise DocumentError('Elige español, inglés o ambos, a 150, 200 o 300 ppp.')
    if type(orientation) is not int or orientation not in [0,90,180,270]:raise DocumentError('Corrección de orientación OCR: 0, 90, 180 o 270 grados.')
    available=ocr_status()['languages']
    if any(lang not in available for lang in language.split('+')):raise DocumentError('Faltan datos OCR verificados. Revisa la distribución de idiomas del programa.')
    with open_pdf(base) as source:
        if source.get_sigflags()>0 or not source.permissions & fitz.PDF_PERM_MODIFY or not source.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento está firmado o no permite lectura y modificación para OCR.')
        if not isinstance(pages,list) or not 1<=len(pages)<=10 or any(type(n) is not int or not 0<=n<len(source) for n in pages) or len(set(pages))!=len(pages):raise DocumentError('Selecciona de 1 a 10 páginas distintas por lote OCR.')
        total=0
        for n in pages:
            page=source[n];pixels=math.ceil(page.rect.width*dpi/72)*math.ceil(page.rect.height*dpi/72);total+=pixels
            if pixels>16_000_000 or max(page.rect.width,page.rect.height)*dpi/72>8192:raise DocumentError('Una página OCR supera el límite de resolución. Reduce los ppp.')
        if total>64_000_000:raise DocumentError('El lote OCR supera 64 millones de píxeles. Reduce páginas o resolución.')
    edited=export_pdf(base,operations);report={'processed':[],'skipped':[],'language':language,'dpi':dpi,'orientation':orientation,'words':0}
    with open_pdf(edited) as doc:
        for number in pages:
            page=doc[number]
            if page.get_text().strip():report['skipped'].append(number);continue
            if list(page.widgets() or []):raise DocumentError('Una página OCR contiene campos de formulario. No se reconocerá como un escaneado.')
            rotation=page.rotation
            try:
                # Recognize the unrotated page coordinates. A PDF /Rotate must
                # not make Tesseract read sideways; restore it for the viewer.
                page.set_rotation(0)
                pix=page.get_pixmap(matrix=fitz.Matrix(dpi/72,dpi/72).prerotate(orientation),alpha=False,annots=False)
                try:recognized=pix.pdfocr_tobytes(language=language,tessdata=str(TESSDATA))
                except Exception as exc:raise DocumentError('No se pudo completar el OCR local. El PDF original se conserva.') from exc
                with fitz.open(stream=recognized) as textdoc:
                    report['words']+=len(textdoc[0].get_text().split())
                    for image in textdoc[0].get_images():textdoc[0].delete_image(image[0])
                    page.show_pdf_page(page.rect,textdoc,0,overlay=True,rotate=orientation)
            finally:page.set_rotation(rotation)
            report['processed'].append(number)
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True) if report['processed'] else edited,report
