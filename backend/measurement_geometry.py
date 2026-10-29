"""Measurement coordinates anchored to PDF space, bounded regional scales and snaps."""
import json,math,re
from uuid import uuid4
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable
from .form_structure import pdf_string


def page_at(doc,number):
    if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
    return doc[number]


def matrices(page):
    # MuPDF's rotated transformation/rotation matrices omit crop offsets and
    # UserUnit in some combinations. Derive display rotation from the real,
    # unrotated page dimensions instead.
    rotation=page.rotation
    try:
        page.set_rotation(0);native=f.Matrix(page.transformation_matrix);w,h=page.rect.width,page.rect.height
    finally:page.set_rotation(rotation)
    rotate={0:f.Matrix(1,1),90:f.Matrix(0,1,-1,0,h,0),180:f.Matrix(-1,0,0,-1,w,h),270:f.Matrix(0,-1,1,0,0,w)}[rotation]
    return native,rotate


def transform(page,pts,to_pdf=False):
    native,rotate=matrices(page);matrix=~rotate*~native if to_pdf else native*rotate
    return [[round(v,6) for v in f.Point(p)*matrix] for p in pts]


def raw_points(pts,minimum=2):
    if not isinstance(pts,list) or not minimum<=len(pts)<=200 or any(not isinstance(p,list) or len(p)!=2 or any(not finite(v) or abs(v)>1e7 for v in p) for p in pts):raise DocumentError('Coordenadas de medición no válidas.')
    return pts


def cal_to_pdf(page,cal):return {**cal,'points':transform(page,cal['points'],True)}
def cal_to_view(page,cal):
    if not isinstance(cal,dict) or set(cal)!={'points','distance','unit'} or len(raw_points(cal['points']))!=2:raise DocumentError('Calibración guardada no válida.')
    return {**cal,'points':transform(page,cal['points'])}


def decode(page,record):
    from .measurements import calibration,calculate,UNITS
    if not isinstance(record,dict) or type(record.get('version')) is not int or record['version'] not in [1,2] or not isinstance(record.get('id'),str) or not re.fullmatch(r'[0-9a-f]{32}',record['id']):raise DocumentError('Registro de medición no compatible.')
    pts=raw_points(record.get('points'),1)
    if record['version']==2:pts=transform(page,pts)
    cal=record.get('calibration')
    if cal is not None:
        if record['version']==2:cal=cal_to_view(page,cal)
        calibration(cal,page,allow_outside=True)
    kind=record.get('kind');unit=record.get('unit');value=record.get('value')
    if kind not in ['distance','perimeter','area','count'] or not isinstance(unit,str) or not finite(value) or value<0:raise DocumentError('Registro de medición no válido.')
    result_unit='' if kind=='count' else unit.removesuffix('²')
    if kind=='count' and unit!='' or kind!='count' and result_unit not in UNITS:raise DocumentError('Unidad de medición guardada no válida.')
    if kind!='count' and cal is None:raise DocumentError('Falta la escala original de la medición.')
    inside=all(page.rect.contains(f.Point(p)) for p in pts)
    if inside:
        actual,_,label_unit=calculate(page,kind,pts,1 if kind=='count' else calibration(cal,page,allow_outside=True),result_unit or 'm')
        if label_unit!=unit or not math.isclose(actual,value,rel_tol=1e-5,abs_tol=1e-5):raise DocumentError('La geometría y el valor de la medición no coinciden.')
    return {**record,'points':pts,'calibration':cal,'editable':inside,'result_unit':result_unit or 'm'}


def read_profiles(doc,page):
    from .measurements import read_record,calibration
    data=read_record(doc,page.xref,'ReapdfMeasurementScales')
    if data is None:
        if doc.xref_get_key(page.xref,'ReapdfMeasurementScales')[0]!='null':raise DocumentError('Las escalas guardadas no se pueden leer; no se sobrescriben.')
        return []
    if not isinstance(data,dict) or type(data.get('version')) is not int or data.get('version')!=1 or not isinstance(data.get('profiles'),list) or len(data['profiles'])>20:raise DocumentError('Las escalas regionales no tienen un formato compatible.')
    result=[];seen=set()
    for row in data['profiles']:
        if not isinstance(row,dict) or set(row)!={'id','name','corners','calibration'} or not isinstance(row['id'],str) or not re.fullmatch(r'[0-9a-f]{32}',row['id']) or row['id'] in seen or not isinstance(row['name'],str) or not 1<=len(row['name'])<=80:raise DocumentError('Perfil de escala no válido.')
        corners=raw_points(row['corners']);cal=cal_to_view(page,row['calibration']);calibration(cal,page,allow_outside=True)
        if len(corners)!=4:raise DocumentError('Región de escala no válida.')
        bounds=f.Rect(transform(page,corners)[0],transform(page,corners)[2]);bounds.normalize()
        if bounds.width<1 or bounds.height<1:raise DocumentError('Región de escala vacía.')
        seen.add(row['id']);result.append({**row,'box':[bounds.x0,bounds.y0,bounds.width,bounds.height],'calibration':cal,'visible':(bounds&page.rect).get_area()>0})
    return result


def configure_profile(base,ops,number,name=None,box=None,cal=None,identity=None,remove=False):
    from .measurements import calibration,read_record
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        page=page_at(doc,number);profiles=read_profiles(doc,page)
        if type(remove) is not bool or identity is not None and (not isinstance(identity,str) or not any(p['id']==identity for p in profiles)):raise DocumentError('La escala regional ya no existe.')
        if remove:
            if identity is None:raise DocumentError('Elige la escala que vas a retirar.')
            profiles=[p for p in profiles if p['id']!=identity]
        else:
            if not isinstance(name,str) or not name.strip() or len(name)>80 or any(ord(c)<32 or ord(c)==127 for c in name):raise DocumentError('Usa un nombre de escala de 1 a 80 caracteres.')
            if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Región de escala no válida.')
            x,y,w,h=box;rect=f.Rect(x,y,x+w,y+h)
            if min(w,h)<10 or not page.rect.contains(rect):raise DocumentError('La región de escala debe quedar en la página y medir al menos 10 × 10 pt.')
            calibration(cal,page)
            if any(not rect.contains(f.Point(p)) for p in cal['points']):raise DocumentError('Los puntos de referencia deben quedar en su región de escala.')
            if any(p['id']!=identity and (f.Rect(p['box'][0],p['box'][1],p['box'][0]+p['box'][2],p['box'][1]+p['box'][3])&rect).get_area()>.01 for p in profiles):raise DocumentError('Las regiones de escala no pueden solaparse.')
            if identity is None and len(profiles)>=20:raise DocumentError('Hasta 20 escalas regionales por página.')
            record={'id':identity or uuid4().hex,'name':name.strip(),'corners':transform(page,[list(rect.tl),list(rect.tr),list(rect.br),list(rect.bl)],True),'calibration':cal_to_pdf(page,cal)}
            profiles=[p for p in profiles if p['id']!=identity]+[record]
        stored=[]
        for row in profiles:
            # Existing profiles were decoded to view coordinates by read_profiles.
            if 'box' in row:row={k:v for k,v in row.items() if k in ['id','name','corners','calibration']};row['calibration']=cal_to_pdf(page,row['calibration'])
            stored.append(row)
        doc.xref_set_key(page.xref,'ReapdfMeasurementScales',pdf_string(json.dumps({'version':1,'profiles':stored},ensure_ascii=False,allow_nan=False)))
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def targets(base,ops,number):
    with open_pdf(export_pdf(base,ops)) as doc:
        page=page_at(doc,number)
        if doc.get_ocgs():return {'points':[],'limited':False,'reason':'El ajuste a geometría de capas requiere verificar su visibilidad.'}
        _,rotate=matrices(page);view_rect=f.Rect(page.rect);page.set_rotation(0)
        drawings=page.get_drawings();result=[];seen=set();limited=len(drawings)>20000
        def add(point,kind):
            nonlocal limited
            p=f.Point(point)*rotate;key=(round(p.x,5),round(p.y,5))
            if key in seen or not view_rect.contains(p):return
            if len(result)>=10000:limited=True;return
            seen.add(key);result.append({'point':list(p),'source':kind})
        for drawing in drawings[:20000]:
            if not any((drawing.get(k) or 0)>0 for k in ['stroke_opacity','fill_opacity']):continue
            for item in drawing['items']:
                if item[0]=='l':pts=item[1:3]
                elif item[0]=='re':r=item[1];pts=[r.tl,r.tr,r.br,r.bl]
                elif item[0]=='qu':q=item[1];pts=[q.ul,q.ur,q.lr,q.ll]
                elif item[0]=='c':pts=[item[1],item[4]]
                else:continue
                for p in pts:add(p,'vector')
                if limited and len(result)>=10000:break
            if len(result)>=10000:break
        images=page.get_image_info()
        if len(images)>1000:limited=True
        for info in images[:1000]:
            matrix=f.Matrix(*info['transform'])
            for p in [(0,0),(1,0),(1,1),(0,1)]:add(f.Point(p)*matrix,'image')
        return {'points':result,'limited':limited,'reason':''}


def native_vertices(page,annot,kind):
    expected={'distance':f.PDF_ANNOT_LINE,'perimeter':f.PDF_ANNOT_POLY_LINE,'area':f.PDF_ANNOT_POLYGON,'count':f.PDF_ANNOT_INK}
    if annot.type[0]!=expected.get(kind):raise DocumentError('El tipo de anotación y la medición no coinciden.')
    _,rotate=matrices(page);rotation=page.rotation
    try:page.set_rotation(0);vertices=annot.vertices or []
    finally:page.set_rotation(rotation)
    if kind=='count':
        if len(vertices)%2:raise DocumentError('Las marcas de conteo no son compatibles.')
        pts=[]
        for i in range(0,len(vertices),2):
            a,b=vertices[i:i+2]
            if len(a)!=2 or len(b)!=2:raise DocumentError('Las marcas de conteo no son compatibles.')
            center=(f.Point(a[0])+f.Point(a[1]))*.5;other=(f.Point(b[0])+f.Point(b[1]))*.5
            if abs(center-other)>.01:raise DocumentError('El conteo contiene marcas desplazadas.')
            pts.append(center)
    else:pts=vertices
    return [list(f.Point(p)*rotate) for p in pts]
