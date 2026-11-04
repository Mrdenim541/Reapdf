"""Independent visual/content checks for each native PDF part before publication."""
import hashlib,json,math
import pymupdf as f
from .engine import DocumentError


def scales(doc):
    areas=[p.rect.get_area() for p in doc]
    if any(not math.isfinite(a) or a<=0 for a in areas):raise DocumentError('Una página tiene límites no verificables.')
    common=min(1,math.sqrt(64_000_000/sum(areas)))
    return [min(common,math.sqrt(4_000_000/a)) for a in areas]


def fingerprint(page,scale,labels=False):
    spans=[];chars=0
    for b in page.get_text('dict',flags=f.TEXTFLAGS_TEXT)['blocks']:
        for line in b.get('lines',[]):
            for s in line['spans']:
                chars+=len(s['text'])
                if chars>1_000_000:raise DocumentError('Una página supera el presupuesto de verificación de texto.')
                spans.append([s['text'],s['font'],round(s['size'],3),s['color'],s.get('alpha',255),[round(v,3) for v in s['bbox']],[round(v,3) for v in s['origin']],list(line['dir'])])
    widgets=sorted((w.field_name,w.field_type,str(w.field_value),tuple(round(v,3) for v in w.rect)) for w in page.widgets() or [])
    pix=page.get_pixmap(matrix=f.Matrix(scale,scale),colorspace=f.csRGB,alpha=False,annots=True)
    return {'geometry':[list(page.mediabox),list(page.cropbox),page.rotation],'text':hashlib.sha256(json.dumps(spans,ensure_ascii=True,separators=(',',':')).encode()).hexdigest(),'widgets':widgets,'visual':[pix.width,pix.height,hashlib.sha256(pix.samples_mv).hexdigest()],'label':page.get_label() if labels else None}


def verify(data,expected,group,page_scales,labels=False):
    with f.open(stream=data) as doc:
        if len(doc)!=len(group):raise DocumentError('Una parte tiene un número de páginas distinto del revisado. No se publica el ZIP.')
        for page,number in zip(doc,group):
            if fingerprint(page,page_scales[number],labels)!=expected[number]:raise DocumentError(f'La página {number+1} no conserva el contenido, la apariencia o los campos. No se publica el ZIP.')
        return {'native_content_verified':True,'visual_verification_dpi':[round(72*page_scales[i],2) for i in group],'tagged':doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null'}
