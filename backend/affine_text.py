"""Bounded affine text frames and convex-cell checks in unrotated page space."""
import math
import pymupdf as f
from .engine import DocumentError,finite


def frame(matrix,origin):
    a,b,c,d,_,_=matrix;length=math.hypot(a,b);det=a*d-b*c
    if not all(finite(v) for v in matrix) or length<1e-5 or abs(det)<1e-8 or (a*a+b*b+c*c+d*d)/abs(det)>100:raise DocumentError('La matriz de texto es singular o demasiado deformada.')
    factor=abs(det)/length
    return {'matrix':[a/length,b/length,c/factor,d/factor,origin.x,origin.y],'factor':factor,'horizontal':length/factor,'direction':[a/length,b/length]}


def polygon(geometry,width=None):
    width=geometry['width'] if width is None else width;m=f.Matrix(*geometry['matrix'])
    return [list(f.Point(p)*m) for p in [(0,geometry['ascent']),(width,geometry['ascent']),(width,geometry['descent']),(0,geometry['descent'])]]


def bounds(poly):
    return f.Rect(min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly))


def rectangle(rect):return [list(rect.tl),list(rect.tr),list(rect.br),list(rect.bl)]
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def signed(poly):return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2


def contains(container,poly,tolerance=.05):
    if len(container)<3 or abs(signed(container))<1e-8 or any(not finite(v) for p in container+poly for v in p):return False
    sign=1 if signed(container)>0 else -1
    return all(sign*cross(a,b,p)>=-tolerance*math.dist(a,b) for p in poly for a,b in zip(container,container[1:]+container[:1]))


def overlap(left,right):
    # Sutherland-Hodgman intersection; rectangles and text/Form cells are convex.
    if any(not finite(v) for p in left+right for v in p):return math.inf
    if abs(signed(left))<1e-8 or abs(signed(right))<1e-8:return 0
    result=[list(p) for p in left];sign=1 if signed(right)>0 else -1
    for a,b in zip(right,right[1:]+right[:1]):
        source=result;result=[]
        if not source:break
        for start,end in zip(source[-1:]+source[:-1],source):
            v=sign*cross(a,b,start);w=sign*cross(a,b,end);inside=v>=-1e-8;next_inside=w>=-1e-8
            if inside!=next_inside:
                ratio=v/(v-w);result.append([start[i]+ratio*(end[i]-start[i]) for i in [0,1]])
            if next_inside:result.append(end)
    return abs(signed(result)) if len(result)>=3 else 0


def geometry(obj,page,span,width=None):
    matrix=obj['matrix']*page.transformation_matrix;origin=obj['origin']*matrix;value=frame(matrix,origin);size=obj['size']*value['factor']
    if not 0<size<=1000 or abs(size*math.sqrt(obj['spacing']['scale']/100*value['horizontal'])-span['size'])>.02:raise DocumentError('El tamaño original no coincide con su transformación.')
    ascent=span.get('ascender');descent=span.get('descender')
    if not finite(ascent) or not finite(descent) or not -10<=descent<ascent<=10:raise DocumentError('Las métricas verticales de la fuente no son verificables.')
    value.update(ascent=ascent*size,descent=descent*size,size=size)
    if width is None:
        # Used for pointer targets only. Actual edits validate encoded font
        # widths and every character origin, rather than trusting this estimate.
        axis=0 if abs(value['direction'][0])>=abs(value['direction'][1]) else 1
        extent=span['bbox'][axis+2]-span['bbox'][axis];vertical=abs(value['matrix'][axis+2])*(value['ascent']-value['descent'])
        width=(extent-vertical)/abs(value['direction'][axis])
    if not finite(width) or width<0:raise DocumentError('No se pudo verificar la anchura transformada.')
    value['width']=width;poly=polygon(value);expected=bounds(poly)
    if max(abs(a-b) for a,b in zip(expected,span['bbox']))>.3:raise DocumentError('La caja del texto no coincide con la matriz y las métricas originales.')
    value['transformed']=max(abs(a-b) for a,b in zip(value['matrix'][:4],[1,0,0,-1]))>1e-5
    return value


def pointer_targets(page,spans):
    """Best-effort hit cells. Editing independently verifies fonts and codes."""
    from .form_text import structure
    rotation=page.rotation;result={}
    try:
        page.set_rotation(0);objects=structure(page.parent,page);index={}
        for obj in objects:
            point=obj['origin']*obj['matrix']*page.transformation_matrix
            index.setdefault((math.floor(point.x),math.floor(point.y)),[]).append(obj)
        for key,span,direction in spans:
            x,y=span['origin'];candidates=[]
            for dx in [-1,0,1]:
                for dy in [-1,0,1]:
                    for obj in index.get((math.floor(x)+dx,math.floor(y)+dy),[]):
                        origin=obj['origin']*obj['matrix']*page.transformation_matrix
                        if abs(origin.x-x)>.02 or abs(origin.y-y)>.02:continue
                        try:g=geometry(obj,page,span)
                        except DocumentError:continue
                        if math.dist(g['direction'],direction)<.001:
                            from .text_compositing import original_only
                            g['original_only']=original_only(page.parent,obj);candidates.append(g)
            unique={tuple(round(v,5) for v in g['matrix']):g for g in candidates}
            if len(unique)==1:
                g=next(iter(unique.values()));result[key]={'quad':polygon(g),'transformed':g['transformed'],'original_only':any(v.get('original_only') for v in candidates)}
    except (DocumentError,ValueError,RuntimeError):pass
    finally:page.set_rotation(rotation)
    return result


def verify(data,prepared):
    from .engine import open_pdf
    from .styled_text import normal_name
    with open_pdf(data) as doc:
        for number,rows in prepared.items():
            page=doc[number];page.set_rotation(0);traces=page.get_texttrace()
            from .type3_text import merge_lines,trace as type3_trace
            blocks=merge_lines(doc,page,page.get_text('rawdict')['blocks']);spans=[{**s,'text':''.join(c['c'] for c in s['chars'])} for b in blocks for line in b.get('lines',[]) for s in line['spans']]
            for row,_ in rows:
                if '_geometry' not in row:continue
                matches=[s for s in spans if math.dist(s['origin'],row['origin'])<.02 and normal_name(s['font'])==normal_name(row['font'])]
                text=row['_replacement_text']
                if not text:
                    if matches:raise DocumentError('La comprobación detectó texto residual. No se publicó el cambio.')
                    continue
                if len(matches)!=1 or matches[0]['text']!=text:raise DocumentError('La comprobación del texto transformado detectó diferencias. No se publicó el cambio.')
                if row.get('opacity') is not None:
                    from .native_text import matching_traces
                    appearances=matching_traces(traces,text,row['origin'])
                    if row['_font'].type=='Type3':
                        checked=type3_trace(row['_font'],matches[0],traces);appearances=[checked] if checked else []
                    if len(appearances)!=1 or appearances[0]['type']!=0 or abs(appearances[0]['opacity']-row['opacity'])>1e-6:raise DocumentError('La transparencia del texto cambió al guardar. No se publicó el cambio.')
                expected=bounds(polygon(row['_geometry'],row['_replacement_width']))
                if max(abs(a-b) for a,b in zip(expected,matches[0]['bbox']))>.3 or matches[0]['color']!=row['color'] or matches[0].get('alpha',255)!=row.get('alpha',255):raise DocumentError('La geometría o el color cambió después de guardar. No se publicó el cambio.')


def obstacles(page):
    result=[]
    for info in page.get_image_info():
        matrix=f.Matrix(*info['transform']);result.append([list(f.Point(p)*matrix) for p in [(0,0),(1,0),(1,1),(0,1)]])
    result.extend(rectangle(a.rect) for a in page.annots() or [])
    result.extend(rectangle(w.rect) for w in page.widgets() or [])
    if len(result)>10000:raise DocumentError('La página supera el límite de imágenes o anotaciones para editar texto.')
    return result


def horizontal_content(page):
    """Prove all direct text orientations, including multiple Tm/Tf per BT.

    This proof permits paragraph substitution only; it grants no native byte
    editing and never infers glyph positions after intermediate text operators.
    """
    from .pdf_content import operations,numbers
    if page.get_xobjects():return False
    matrix=f.Matrix(1,1);tm=f.Matrix(1,1);stack=[];scale=100;inside=False;seen=False
    for op,args,_ in operations(page.read_contents()):
        if op=='q':
            stack.append((f.Matrix(matrix),scale))
            if len(stack)>100:return False
        elif op=='Q':
            if not stack:return False
            matrix,scale=stack.pop()
        elif op=='cm':matrix=f.Matrix(*numbers(args,6))*matrix
        elif op=='BT':
            if inside:return False
            inside=True;tm=f.Matrix(1,1)
        elif op=='ET':
            if not inside:return False
            inside=False
        elif op=='Tm':
            if not inside:return False
            tm=f.Matrix(*numbers(args,6))
        elif op=='Tz':scale=numbers(args,1)[0]
        elif op in ['Tj','TJ',"'",'"']:
            if not inside or not 10<=scale<=400:return False
            g=frame(tm*matrix*page.transformation_matrix,f.Point(0,0));seen=True
            if max(abs(a-b) for a,b in zip(g['matrix'][:4],[1,0,0,-1]))>1e-5:return False
    return seen and not inside and not stack


def require_horizontal(page,spans):
    """A paragraph rewrite must not silently remove an unverified text matrix."""
    from .pdf_content import placements,operations
    from .text_compositing import graphics
    try:original_composition=graphics(page.parent,page.xref,page.read_contents())
    except DocumentError as exc:raise DocumentError('No se pudo verificar la geometría y la composición del bloque para sustituir su fuente.') from exc
    if original_composition:raise DocumentError('El modo de mezcla requiere editar con la fuente original para conservar su composición.')
    cells=pointer_targets(page,spans)
    if any(g.get('original_only') for g in cells.values()):raise DocumentError('El grupo de transparencia requiere editar con su fuente original para conservar la composición.')
    if any(g['transformed'] for g in cells.values()):raise DocumentError('El bloque usa giro, inclinación o reflexión. Edita su línea con la fuente original para conservar la geometría.')
    if all(key in cells for key,_,_ in spans):return
    content=page.read_contents()
    try:
        objects=placements(content)['texts'];unsafe=any((op=='Tm' and [t.value for t in args[:4]]!=[1,0,0,1]) or op=='cm' and [t.value for t in args[:4]]!=[1,0,0,1] for op,args,_ in operations(content))
    except DocumentError as exc:raise DocumentError('No se pudo verificar la geometría del bloque para sustituir su fuente.') from exc
    if horizontal_content(page):return
    for key,span,_ in spans:
        if key in cells:continue
        matched=False
        for obj in objects:
            matrix=obj['matrix']*page.transformation_matrix;origin=obj['origin']*matrix
            if math.dist(origin,span['origin'])>.02:continue
            try:g=frame(matrix,origin)
            except DocumentError:continue
            expected=obj['size']*g['factor']*math.sqrt(obj['spacing']['scale']/100*g['horizontal'])
            if abs(expected-span['size'])>.02:continue
            matched=True
            if max(abs(a-b) for a,b in zip(g['matrix'][:4],[1,0,0,-1]))>1e-5:raise DocumentError('La sustitución no conserva la transformación original. Usa la edición con fuente original.')
        if not matched and (unsafe or page.get_xobjects()):raise DocumentError('El bloque tiene una transformación no verificable para sustitución de fuente.')
