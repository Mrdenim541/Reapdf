"""Reviewable paper-corner suggestion against a contrasting dark background.

Deliberately abstains on white-on-white scans, touching borders, irregular shapes
or low contrast. Uses one bounded image; no document pixels are rewritten.
"""
from collections import deque
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite


def estimate(pix):
    width,height=pix.width,pix.height;raw=pix.samples;seen=bytearray(width*height);best=None
    if width*height>640000:return None
    border=[raw[x] for x in range(width)]+[raw[(height-1)*width+x] for x in range(width)]+[raw[y*width] for y in range(height)]+[raw[y*width+width-1] for y in range(height)]
    if sum(v<120 for v in border)<len(border)*.85:return None
    for at,value in enumerate(raw):
        if value<220 or seen[at]:continue
        pending=deque([at]);seen[at]=1;count=0;extrema=[None]*4;scores=[float('inf'),-float('inf'),-float('inf'),float('inf')];touch=False
        while pending:
            index=pending.popleft();y,x=divmod(index,width);count+=1
            touch=touch or x<3 or y<3 or x>width-4 or y>height-4
            for k,score in enumerate([x+y,x-y,x+y,x-y]):
                if score<scores[k] if k in [0,3] else score>scores[k]:scores[k]=score;extrema[k]=(x+.5,y+.5)
            for other in [index-1 if x else -1,index+1 if x+1<width else -1,index-width if y else -1,index+width if y+1<height else -1]:
                if other>=0 and not seen[other] and raw[other]>=220:seen[other]=1;pending.append(other)
        if not touch and (best is None or count>best[0]):best=(count,extrema)
    if best is None:return None
    count,quad=best
    if not width*height*.15<=count<=width*height*.9 or len(set(quad))<4:return None
    area=abs(sum(quad[i][0]*quad[(i+1)%4][1]-quad[i][1]*quad[(i+1)%4][0] for i in range(4)))/2
    if not .85<=count/max(1,area)<=1.05:return None
    from .scan_geometry import corners
    try:corners(f.Rect(0,0,width,height),{'quad':[list(p) for p in quad]},f.Rect(0,0,width,height))
    except DocumentError:return None
    return quad


def inspect(base,ops,number,box):
    with open_pdf(base) as source:
        if not source.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite analizar sus imágenes.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Página o área de esquinas no válida.')
        page=doc[number];x,y,w,h=box;rect=f.Rect(x,y,x+w,y+h)
        if min(w,h)<40 or not page.rect.contains(rect):raise DocumentError('Selecciona un área de al menos 40 × 40 pt dentro de la página.')
        if any((v.rect&(rect*page.derotation_matrix)).get_area()>.1 for v in page.widgets() or []):raise DocumentError('El área cruza campos de formulario.')
        scale=min(2,799/max(w,h));pix=page.get_pixmap(matrix=f.Matrix(scale,scale),clip=rect,colorspace=f.csGRAY,alpha=False,annots=False);quad=estimate(pix)
        result=[[round((px+pix.x)/scale,3),round((py+pix.y)/scale,3)] for px,py in quad] if quad else None
        if result:
            from .scan_geometry import corners
            corners(rect,{'quad':result},page.rect)
        return {'page':number,'box':box,'quad':result,'review_required':True,'source_modified':False,'reason':'Revisa las cuatro esquinas y ajústalas antes del OCR.' if result else 'No hay un borde de papel claro contra un fondo oscuro. Usa las cuatro esquinas manuales; no se adivinan los límites.'}
