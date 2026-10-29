"""Controlled downsampling of RGB/gray/CMYK images, including nested forms; always a separate copy."""
import hashlib
import math
import pymupdf as fitz
from .engine import DocumentError,open_pdf,export_pdf
from .document_tools import editable


def compress_images(base,operations,dpi,quality):
    if type(dpi) is not int or not 72<=dpi<=300 or type(quality) is not int or not 40<=quality<=95:
        raise DocumentError('Usa resolución entre 72 y 300 DPI y calidad JPEG entre 40 y 95.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&fitz.PDF_PERM_COPY:raise DocumentError('La compresión requiere permiso de modificación y extracción.')
    edited=export_pdf(base,operations);changes=[];skipped=[];pixels=0
    with open_pdf(edited) as doc:
        if len(doc)>30 or doc.xref_length()>50000:raise DocumentError('La compresión admite hasta 30 páginas y 50 000 objetos.')
        if doc.get_ocgs():raise DocumentError('La compresión de documentos con capas todavía no se verifica.')
        if any(list(p.widgets() or []) or list(p.annots() or []) for p in doc):
            raise DocumentError('Esta compresión requiere una copia sin campos ni anotaciones.')
        if len({item[0] for p in doc for item in p.get_xobjects()})>200:
            raise DocumentError('Hasta 200 Form XObjects por copia comprimida.')
        original_text=[p.get_text() for p in doc];geometry=[(tuple(p.rect),tuple(p.cropbox),p.rotation) for p in doc]
        images={}
        for page in doc:
            for item in page.get_images(full=True):images.setdefault(item[0],item)
        if len(images)>50:raise DocumentError('Hasta 50 imágenes distintas por copia comprimida.')
        # get_image_rects may decode/hash every image on the page internally.
        # Bound all resources before asking for placements, including skipped
        # formats, rather than only bounding images selected for resampling.
        if any(item[2]<1 or item[3]<1 or item[2]*item[3]>24_000_000 for item in images.values()):
            raise DocumentError('Límite de 24 MP por imagen inspeccionada.')
        if sum(item[2]*item[3] for item in images.values())>64_000_000:
            raise DocumentError('Límite de 64 MP de imágenes inspeccionadas por copia.')
        plans=[]
        for xref,item in images.items():
            _,smask,width,height,bpc,space,*_=item
            if smask or bpc!=8 or space not in {'DeviceRGB','DeviceGray','DeviceCMYK','ICCBased'} or any(doc.xref_get_key(xref,key)[0]!='null' for key in ['Mask','Decode']):
                skipped.append({'image':len(plans)+len(skipped)+1,'reason':'Transparencia, máscara, color o profundidad no compatibles.'});continue
            placements=[];pages=[];first=None
            for page in doc:
                rects=page.get_image_rects(xref,transform=True)
                if rects:first=page.number if first is None else first;pages.append(page.number)
                for _,m in rects:
                    w,h=math.hypot(m.a,m.b),math.hypot(m.c,m.d)
                    if min(w,h)<=0 or not all(math.isfinite(v) for v in [w,h]) or abs(m.a*m.c+m.b*m.d)>w*h*.0001:
                        raise DocumentError('Una imagen tiene una transformación oblicua o degenerada no compatible.')
                    placements.append((w,h))
            if not placements:skipped.append({'image':len(plans)+len(skipped)+1,'reason':'Recurso sin colocación visible identificable.'});continue
            effective=min(min(width/w*72,height/h*72) for w,h in placements)
            if effective<=dpi*1.1:skipped.append({'image':len(plans)+len(skipped)+1,'reason':'Su resolución ya está cerca o por debajo del objetivo.'});continue
            pixels+=width*height
            if width*height>24_000_000 or pixels>64_000_000:raise DocumentError('Límite de 24 MP por imagen y 64 MP por copia comprimida.')
            factor=dpi/effective;target=[max(1,math.ceil(width*factor)),max(1,math.ceil(height*factor))]
            plans.append((xref,first,width,height,target,pages,effective))
        for xref,first,width,height,target,pages,effective in plans:
            pix=fitz.Pixmap(doc,xref)
            if pix.alpha or pix.n not in [1,3,4]:
                skipped.append({'image':len(changes)+len(skipped)+1,'reason':'Color o canales no compatibles.'});continue
            color_space=doc.xref_get_key(xref,'ColorSpace')[1]
            scaled=fitz.Pixmap(pix,target[0],target[1],None)
            doc[first].replace_image(xref,stream=scaled.tobytes('jpeg',jpg_quality=quality))
            # Resampling/JPEG keep the source RGB/gray/CMYK samples. Retain its PDF
            # colour space/profile instead of relabelling custom ICC samples.
            doc.xref_set_key(xref,'ColorSpace',color_space)
            if pix.n==4:
                # MuPDF's JPEG encoder writes native CMYK samples. The generic
                # JPEG importer adds an Adobe inversion Decode array, which
                # would invert these samples a second time.
                doc.xref_set_key(xref,'Decode','null')
            changes.append({'pages':pages,'before':[width,height],'after':target,'source_min_dpi':round(effective,2)})
        candidate=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True) if changes else edited
    with open_pdf(candidate) as after:
        if (original_text!=[p.get_text() for p in after]
                or geometry!=[(tuple(p.rect),tuple(p.cropbox),p.rotation) for p in after]):
            raise DocumentError('La comprobación de texto o geometría no coincide; no se entrega la copia.')
    reduced=len(candidate)<len(edited) and bool(changes)
    result=candidate if reduced else edited
    report={'before_bytes':len(edited),'after_bytes':len(result),'saved_bytes':len(edited)-len(result),'dpi':dpi,'quality':quality,
            'changed_images':changes if reduced else [],'skipped':skipped,'text_preserved':True,'reduced':reduced,
            'sha256':hashlib.sha256(result).hexdigest(),'pages':len(geometry),
            'notice':'La reducción JPEG puede perder detalles. Revisa la copia antes de compartirla.' if reduced else 'No se obtuvo una copia menor; se conserva la versión con las ediciones aplicadas.'}
    return result,report
