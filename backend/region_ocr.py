"""OCR for selected scanned regions on otherwise digital pages, preserving source images and adding invisible text."""
import math
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .ocr import ocr_status,TESSDATA
from .document_tools import editable


def recognize(base,ops,regions,language='spa+eng',dpi=200,orientation=0,correction=None):
    if language not in ['eng','spa','spa+eng'] or type(dpi) is not int or dpi not in [150,200,300] or type(orientation) is not int or orientation not in [0,90,180,270]:raise DocumentError('Idioma, resolución u orientación OCR no válidos.')
    if any(lang not in ocr_status()['languages'] for lang in language.split('+')):raise DocumentError('Faltan idiomas OCR verificados.')
    if not isinstance(regions,list) or not 1<=len(regions)<=10:raise DocumentError('Hasta 10 regiones OCR por operación.')
    if correction is not None and len(regions)!=1:raise DocumentError('La corrección geométrica se aplica a una región por operación.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite lectura para OCR.')
    with open_pdf(export_pdf(base,ops)) as doc:
        prepared=[];total=0
        for entry in regions:
            if not isinstance(entry,dict) or set(entry)!={'page','box'} or type(entry['page']) is not int or not 0<=entry['page']<len(doc):raise DocumentError('Región OCR no válida.')
            number=entry['page'];page=doc[number];box=entry['box']
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Coordenadas OCR no válidas.')
            x,y,w,h=box;visible=f.Rect(x,y,x+w,y+h)
            if min(w,h)<10 or not page.rect.contains(visible):raise DocumentError('La región OCR debe quedar dentro de la página y medir al menos 10 × 10 pt.')
            if correction is not None:
                from .scan_geometry import corners
                points=corners(visible,correction,page.rect)
                visible=f.Quad(points[0],points[1],points[3],points[2]).rect
            rect=visible*page.derotation_matrix
            if any(n==number and (rect&other).get_area()>.1 for n,other in prepared):raise DocumentError('Las regiones OCR no deben solaparse.')
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    if any(s['text'].strip() and (f.Rect(s['bbox'])&rect).get_area()>.1 for s in line['spans']):raise DocumentError('La región ya contiene texto digital u OCR. Reduce su área para evitar duplicados.')
            if any((widget.rect&rect).get_area()>.1 for widget in page.widgets() or []):raise DocumentError('La región cruza un campo de formulario.')
            pixels=math.ceil(rect.width*dpi/72)*math.ceil(rect.height*dpi/72);total+=pixels
            if pixels>16_000_000 or total>64_000_000 or max(rect.width,rect.height)*dpi/72>8192:raise DocumentError('El OCR supera el presupuesto de resolución; reduce el área o los ppp.')
            prepared.append((number,rect))
        report={'regions':[],'language':language,'dpi':dpi,'orientation':orientation,'words':0,'correction':correction}
        for number,rect in prepared:
            page=doc[number]
            if correction is not None:
                from .scan_geometry import recognize as corrected_ocr,overlay
                words,_=corrected_ocr(page,points,language,dpi,orientation);overlay(page,words)
                report['words']+=len(words);report['regions'].append({'page':number,'rect':list(rect),'words':len(words),'mapped_words':words,'geometry':'projective per word; affine invisible glyph placement'})
                continue
            rotation=page.rotation;page.set_rotation(0)
            try:
                pix=page.get_pixmap(matrix=f.Matrix(dpi/72,dpi/72).prerotate(orientation),clip=rect,alpha=False,annots=False)
                try:data=pix.pdfocr_tobytes(language=language,tessdata=str(TESSDATA))
                except Exception as exc:raise DocumentError('El OCR de región no terminó. No se publicó un resultado parcial.') from exc
                with f.open(stream=data) as textdoc:
                    words=len(textdoc[0].get_text().split())
                    if not words:raise DocumentError('No se reconoció texto en una región. Revisa el área, orientación o resolución.')
                    for image in textdoc[0].get_images():textdoc[0].delete_image(image[0])
                    page.show_pdf_page(rect,textdoc,0,overlay=True,rotate=orientation)
                    report['words']+=words;report['regions'].append({'page':number,'rect':list(rect),'words':words})
            finally:page.set_rotation(rotation)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True),report
