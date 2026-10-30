"""Bounded projection-profile deskew suggestion; never changes the source PDF."""
import math
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite


def estimate(pix):
    from PIL import Image
    # A bounded binary sample, nearest-neighbour rotations and row concentration.
    # Orthogonal orientation and perspective remain explicit separate choices.
    with Image.frombytes('L',(pix.width,pix.height),pix.samples) as gray:
        gray.thumbnail((800,800));mask=gray.point(lambda v:255 if v<150 else 0)
        raw=mask.tobytes();ink=sum(raw)//255;area=mask.width*mask.height
        if ink<150 or not .002<=ink/area<=.35:return {'angle':None,'reason':'No hay suficiente tinta de texto o el área contiene demasiado contenido oscuro.'}
        def score(angle):
            with mask.rotate(angle,resample=Image.Resampling.NEAREST,expand=True,fillcolor=0) as rotated:
                # BOX downsampling integrates each row without Python pixel loops.
                with rotated.resize((1,rotated.height),Image.Resampling.BOX) as profile:
                    values=list(profile.tobytes());return sum((a-b)**2 for a,b in zip(values,values[1:]))
        coarse=[(score(a),a) for a in range(-15,16)];best=max(coarse);fine=[(score(best[1]+i*.1),best[1]+i*.1) for i in range(-10,11) if abs(best[1]+i*.1)<=15];value,angle=max(fine)
        # Separate the peak from alternatives a full degree away; this measures
        # a geometric profile, not OCR recognition confidence.
        others=[s for s,a in coarse if abs(a-angle)>=2];baseline=sorted(s for s,a in coarse)[len(coarse)//2]
        if abs(angle)>=14.8 or value<max(1,baseline)*1.3 or others and value<max(others)*1.05:return {'angle':None,'reason':'La inclinación es ambigua o está fuera del intervalo de ±15°. Usa el ajuste manual.'}
        return {'angle':round(angle,1),'reason':'Sugerencia por concentración de líneas. Revisa el contorno antes de reconocer.'}


def inspect(base,ops,number,box,orientation=0):
    if type(orientation) is not int or orientation not in [0,90,180,270]:raise DocumentError('Orientación de inclinación no válida.')
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite analizar su contenido.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Página o región de inclinación no válida.')
        x,y,w,h=box;page=doc[number];rect=f.Rect(x,y,x+w,y+h)
        if min(w,h)<40 or not page.rect.contains(rect):raise DocumentError('Selecciona un área de al menos 40 × 40 pt dentro de la página.')
        if any((widget.rect&(rect*page.derotation_matrix)).get_area()>.1 for widget in page.widgets() or []):raise DocumentError('El área cruza un campo de formulario.')
        scale=min(2,800/max(w,h));pix=page.get_pixmap(matrix=f.Matrix(scale,scale).prerotate(orientation),clip=rect,colorspace=f.csGRAY,alpha=False,annots=False)
        return {**estimate(pix),'page':number,'box':box,'orientation':orientation,'source_modified':False,'review_required':True,'method':'bounded horizontal projection profile'}
