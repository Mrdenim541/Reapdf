"""Bounded vector-path tracing with explicit cubic approximation bounds."""
import hashlib,heapq,json,math
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf
from .measurement_geometry import page_at,matrices

LENGTH_TOLERANCE=.019
DEVIATION_TOLERANCE=.049


def _split(c):
    a,b,c,d=c;ab=(a+b)*.5;bc=(b+c)*.5;cd=(c+d)*.5;abc=(ab+bc)*.5;bcd=(bc+cd)*.5;middle=(abc+bcd)*.5
    return (a,ab,abc,middle),(middle,bcd,cd,d)


def _bounds(c):
    lower=abs(c[-1]-c[0]);upper=sum(abs(b-a) for a,b in zip(c,c[1:]));delta=c[-1]-c[0]
    def distance(p):
        if lower<1e-10:return abs(p-c[0])
        v=p-c[0];t=max(0,min(1,(v.x*delta.x+v.y*delta.y)/(lower*lower)))
        return abs(p-(c[0]+delta*t))
    # A capsule around the finite chord is convex and contains the controls;
    # unlike infinite-line distance, this also bounds collinear reversals.
    deviation=max(distance(p) for p in c[1:-1])
    return lower,upper,deviation


def flatten(segments,budget=None):
    leaves={};heap=[];serial=0;gap=0.
    for index,segment in enumerate(segments):
        if budget is not None:
            budget[0]+=1
            if budget[0]>50000:raise DocumentError('Presupuesto de subdivisión geométrica agotado.')
        c=tuple(f.Point(p) for p in segment)
        lower,upper,deviation=_bounds(c) if len(c)==4 else (abs(c[1]-c[0]),)*2+(0.,)
        key=(index,0.);leaves[key]=(c,lower,upper,deviation,0);gap+=upper-lower
        if len(c)==4:heapq.heappush(heap,(-max((upper-lower)/LENGTH_TOLERANCE,deviation/DEVIATION_TOLERANCE),serial,key));serial+=1
    while heap:
        if budget is not None:
            budget[0]+=1
            if budget[0]>50000:raise DocumentError('Presupuesto de subdivisión geométrica agotado.')
        score,_,key=heapq.heappop(heap);c,lower,upper,deviation,depth=leaves[key]
        if gap<=LENGTH_TOLERANCE and -score<=1:break
        if len(leaves)>=199 or depth>=18:break
        del leaves[key];gap-=upper-lower;index,t=key;span=2.**(-depth-1)
        for position,child in [(t,_split(c)[0]),(t+span,_split(c)[1])]:
            lo,hi,dev=_bounds(child);child_key=(index,position);leaves[child_key]=(child,lo,hi,dev,depth+1);gap+=hi-lo
            heapq.heappush(heap,(-max((hi-lo)/LENGTH_TOLERANCE,dev/DEVIATION_TOLERANCE),serial,child_key));serial+=1
    ordered=[v for _,v in sorted(leaves.items())];points=[list(ordered[0][0][0])]+[list(v[0][-1]) for v in ordered]
    if len(points)>200:raise DocumentError('Hasta 200 vértices por trazado.')
    deviation=max(v[3] for v in ordered)
    if gap>1 or deviation>1:raise DocumentError('El trazado supera la aproximación máxima de 1 pt con 200 vértices.')
    return points,{'length_lower_pt':sum(v[1] for v in ordered),'length_upper_pt':sum(v[2] for v in ordered),'length_error_pt':max(0,gap)+.0004,'max_deviation_pt':deviation+.000002,'precision_target_met':gap+.0004<=.02 and deviation+.000002<=.05}


def paths_on_page(doc,page,private=False):
    if doc.get_ocgs():return {'paths':[],'limited':False,'reason':'Los trazados de capas requieren verificar su visibilidad.'}
    rotation=page.rotation;native,rotate=matrices(page);rect=f.Rect(page.rect)
    try:page.set_rotation(0);drawings=page.get_drawings(extended=True)
    finally:page.set_rotation(rotation)
    result=[];skipped=0;levels=[];count=0;vertices=0;limited=len(drawings)>20000;budget=[0];exhausted=False
    def add(segments,closed,curved,index):
        nonlocal skipped,limited,vertices,exhausted
        if not segments:return
        if len(result)>=500:limited=True;exhausted=True;return
        try:
            closed=closed or abs(f.Point(segments[-1][-1])-f.Point(segments[0][0]))<.00001
            if closed and abs(f.Point(segments[-1][-1])-f.Point(segments[0][0]))>1e-10:segments=segments+[(segments[-1][-1],segments[0][0])]
            pts,bounds=flatten(segments,budget)
            pts=[[round(v,6) for v in f.Point(p)*rotate] for p in pts]
            if vertices+len(pts)>20000:limited=True;exhausted=True;return
            if any(not rect.contains(f.Point(p)) for p in pts):raise DocumentError('Trazado parcialmente fuera de vista.')
            if len(pts)<2 or bounds['length_lower_pt']<1:raise DocumentError('Trazado mínimo.')
            source_geometry=[[[round(v,3) for v in f.Point(p)*~native] for p in segment] for segment in segments]
            identity=hashlib.sha256(json.dumps([index,source_geometry,closed],separators=(',',':')).encode()).hexdigest()
            result.append({'id':identity,'points':pts,'closed':closed,'curved':curved,**bounds})
            if private:result[-1]['_segments']=[[[float(v) for v in f.Point(p)*rotate] for p in segment] for segment in segments]
            vertices+=len(pts)
        except DocumentError:
            skipped+=1
            if budget[0]>50000:limited=True;exhausted=True
    for index,drawing in enumerate(drawings[:20000]):
        level=drawing.get('level',0)
        while levels and levels[-1][0]>=level:levels.pop()
        typ=drawing.get('type')
        if typ in ['clip','group']:
            items=drawing.get('items',[]);clip=f.Rect(items[0][1]) if typ=='clip' and len(items)==1 and items[0][0]=='re' else None
            levels.append((level,typ=='clip' or drawing.get('opacity',1)==0,clip));continue
        bounds=f.Rect(drawing.get('rect',f.Rect()));margin=(drawing.get('width') or 0)*.5
        if any(block and (clip is None or not clip.contains(bounds+(-margin,-margin,margin,margin))) for _,block,clip in levels):skipped+=1;continue
        if not any((drawing.get(k) or 0)>0 for k in ['stroke_opacity','fill_opacity']):continue
        segments=[];curved=False
        for item in drawing.get('items',[]):
            count+=1
            if count>20000:limited=True;break
            kind=item[0]
            if kind in ['re','qu']:
                add(segments,False,curved,(index,count));segments=[];curved=False
                q=item[1];corners=[q.tl,q.tr,q.br,q.bl] if kind=='re' else [q.ul,q.ur,q.lr,q.ll]
                add(list(zip(corners,corners[1:]+corners[:1])),True,False,(index,count,'closed'));continue
            if kind not in ['l','c']:
                add(segments,False,curved,(index,count));segments=[];curved=False;skipped+=1;continue
            segment=tuple(item[1:3] if kind=='l' else item[1:5])
            if segments and abs(f.Point(segments[-1][-1])-f.Point(segment[0]))>.00001:
                add(segments,False,curved,(index,count));segments=[];curved=False
            segments.append(segment);curved|=kind=='c'
        add(segments,bool(drawing.get('closePath')),curved,(index,count,'last'))
        if exhausted or limited and (count>20000 or len(result)>=500):break
    return {'paths':result,'limited':limited,'skipped_paths':skipped,'reason':'Se omiten trazados recortados, fuera de página o que superan la precisión/límites; no se reinterpretan como geometría completa.' if skipped or limited else ''}


def model(base,ops,number):
    with open_pdf(export_pdf(base,ops)) as doc:return paths_on_page(doc,page_at(doc,number))


def path_points(path,kind):
    if kind=='area':
        if not path['closed']:raise DocumentError('El área requiere un trazado cerrado.')
        return path['points'][:-1]
    return path['points']


def approximation_for(path,kind,scale,unit,displacement=0):
    from .measurements import UNITS
    factor=scale/UNITS[unit]
    deviation=path['max_deviation_pt']+displacement;length_error=path['length_error_pt']+2*(len(path['points'])-1)*displacement
    error=length_error*factor if kind=='perimeter' else (2*path['length_upper_pt']*deviation+math.pi*deviation**2)*factor**2
    return {'path':path['id'],'method':'bounded_vector_polyline','max_deviation_pt':deviation,'length_error_pt':length_error,'error_bound':error,'unit':unit if kind=='perimeter' else unit+'²'}
