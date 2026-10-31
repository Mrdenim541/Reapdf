"""Four bounded local OCR trials, presented for review without confidence claims."""
import math
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .ocr import ocr_status,TESSDATA


def inspect(base,ops,number,box,language='spa+eng'):
    if language not in ['eng','spa','spa+eng'] or any(x not in ocr_status()['languages'] for x in language.split('+')):raise DocumentError('Idioma OCR no disponible o no verificado.')
    with open_pdf(base) as doc:
        if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite analizar su contenido.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Página o región OCR no válida.')
        page=doc[number];x,y,w,h=box;rect=f.Rect(x,y,x+w,y+h)
        if min(w,h)<40 or not page.rect.contains(rect):raise DocumentError('Selecciona una región de al menos 40 × 40 pt dentro de la página.')
        if any((v.rect&(rect*page.derotation_matrix)).get_area()>.1 for v in page.widgets() or []):raise DocumentError('La región cruza campos de formulario.')
        scale=min(150/72,math.sqrt(4_000_000/(w*h)),4000/max(w,h));trials=[]
        for orientation in [0,90,180,270]:
            pix=page.get_pixmap(matrix=f.Matrix(scale,scale).prerotate(orientation),clip=rect,colorspace=f.csRGB,alpha=False,annots=False);pix.set_dpi(round(scale*72),round(scale*72))
            try:data=pix.pdfocr_tobytes(language=language,tessdata=str(TESSDATA))
            except Exception as exc:raise DocumentError('No se completó la comparación OCR local. Se conserva el original.') from exc
            with f.open(stream=data) as recognized:words=recognized[0].get_text().split()
            text=' '.join(words)
            if len(text)>100000:raise DocumentError('La comparación OCR supera el límite de texto.')
            readable=[word for word in words if len(word)>=2 and all(c.isalnum() or c in '-.,:/()' for c in word) and any(c.isalpha() for c in word)]
            score=sum(sum(c.isalnum() for c in word) for word in readable)
            trials.append({'orientation':orientation,'sample':text[:1000],'recognized_words':len(words),'readable_characters':score})
        ranked=sorted(trials,key=lambda t:t['readable_characters'],reverse=True);best,second=ranked[:2]
        chosen=best['orientation'] if best['readable_characters']>=10 and best['recognized_words']>=2 and best['readable_characters']>=max(1,second['readable_characters'])*1.35 else None
        return {'page':number,'box':box,'orientation':chosen,'trials':trials,'review_required':True,'source_modified':False,'reason':'Compara las muestras y confirma la orientación antes de reconocer. El recuento de caracteres es una heurística, no una confianza de Tesseract.'}
