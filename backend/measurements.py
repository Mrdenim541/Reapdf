"""Calibrated distances, polylines, areas and counts stored as PDF annotations."""
import json
import math
from uuid import uuid4
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable
from .form_structure import pdf_string

UNITS={'mm':.001,'cm':.01,'m':1.,'in':.0254,'ft':.3048}


def points(value,page,minimum=2):
    if not isinstance(value,list) or not minimum<=len(value)<=200:raise DocumentError('Elige de '+str(minimum)+' a 200 puntos.')
    if any(not isinstance(p,list) or len(p)!=2 or any(not finite(v) for v in p) or not page.rect.contains(f.Point(*p)) for p in value):raise DocumentError('Todos los puntos deben quedar dentro de la página.')
    return [list(p) for p in value]


def calibration(value,page):
    if not isinstance(value,dict) or set(value)!={'points','distance','unit'}:raise DocumentError('Define dos puntos, su distancia conocida y la unidad.')
    pts=points(value['points'],page)
    if len(pts)!=2 or not finite(value['distance']) or not 0<value['distance']<=1e9 or not isinstance(value['unit'],str) or value['unit'] not in UNITS:raise DocumentError('Calibración no válida.')
    length=math.dist(*pts)
    if length<1:raise DocumentError('Los puntos de calibración deben separarse al menos 1 pt.')
    return value['distance']*UNITS[value['unit']]/length


def intersect(a,b,c,d):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    def between(p,q,r):return min(p[0],q[0])-.00001<=r[0]<=max(p[0],q[0])+.00001 and min(p[1],q[1])-.00001<=r[1]<=max(p[1],q[1])+.00001
    x,y,z,w=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
    return x*y<0 and z*w<0 or any(abs(v)<1e-8 and between(p,q,r) for v,p,q,r in [(x,a,b,c),(y,a,b,d),(z,c,d,a),(w,c,d,b)])


def calculate(page,kind,pts,scale,unit):
    if kind not in ['distance','perimeter','area','count'] or not isinstance(unit,str) or unit not in UNITS:raise DocumentError('Medición o unidad no válida.')
    pts=points(pts,page,1 if kind=='count' else 3 if kind=='area' else 2)
    if kind=='distance' and len(pts)!=2:raise DocumentError('La distancia requiere exactamente dos puntos.')
    if len({tuple(p) for p in pts})!=len(pts):raise DocumentError('No repitas puntos de la medición.')
    if kind=='count':return len(pts),pts,''
    if kind=='area':
        n=len(pts)
        for i in range(n):
            for j in range(i+1,n):
                if j==i+1 or (i==0 and j==n-1):continue
                if intersect(pts[i],pts[(i+1)%n],pts[j],pts[(j+1)%n]):raise DocumentError('El polígono se cruza consigo mismo.')
        raw=abs(sum(pts[i][0]*pts[(i+1)%n][1]-pts[(i+1)%n][0]*pts[i][1] for i in range(n)))/2
        if raw<1:raise DocumentError('El área es demasiado pequeña.')
        return raw*(scale/UNITS[unit])**2,pts,unit+'²'
    raw=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]))
    if raw<1:raise DocumentError('La longitud es demasiado pequeña.')
    return raw*scale/UNITS[unit],pts,unit


def read_record(doc,xref,key):
    kind,value=doc.xref_get_key(xref,key)
    if kind!='string' or len(value)>20000:return None
    try:return json.loads(value)
    except (ValueError,TypeError):return None


def model(base,ops,number):
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number];rows=[]
        for annot in page.annots() or []:
            record=read_record(doc,annot.xref,'ReapdfMeasurement')
            if isinstance(record,dict) and type(record.get('version')) is int and record['version']==1 and isinstance(record.get('id'),str) and len(record['id'])==32 and record.get('kind') in ['distance','perimeter','area','count'] and finite(record.get('value')) and isinstance(record.get('unit'),str) and len(record['unit'])<=5:
                if len(rows)>=500:raise DocumentError('Hasta 500 mediciones por página.')
                rows.append({'xref':annot.xref,'id':record.get('id'),'kind':record.get('kind'),'value':record.get('value'),'unit':record.get('unit'),'points':record.get('points'),'label':annot.info.get('content','')[:400]})
        cal=read_record(doc,page.xref,'ReapdfCalibration')
        if cal is not None:
            try:calibration(cal,page)
            except DocumentError:cal=None
        return {'measurements':rows,'calibration':cal}


def measure(base,ops,number,kind,pts,cal,unit='m',preview=False):
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_ANNOTATE:raise DocumentError('El documento no permite anotaciones.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number];scale=1 if kind=='count' else calibration(cal,page)
        value,pts,label_unit=calculate(page,kind,pts,scale,unit)
        label={'distance':'Distancia','perimeter':'Longitud','area':'Área','count':'Cantidad'}[kind]+f': {value:,.3f} {label_unit}'.rstrip()
        if preview:return {'value':value,'unit':label_unit,'label':label,'scale_m_per_pt':scale,'points':pts}
        if sum(1 for a in page.annots() or [] if read_record(doc,a.xref,'ReapdfMeasurement'))>=500:raise DocumentError('Hasta 500 mediciones por página.')
        native=[f.Point(p)*page.derotation_matrix for p in pts]
        if kind=='distance':annot=page.add_line_annot(*native)
        elif kind=='perimeter':annot=page.add_polyline_annot(native)
        elif kind=='area':annot=page.add_polygon_annot(native)
        else:
            paths=[]
            for point in native:
                paths.extend([[list(point+(-2,0)),list(point+(2,0))],[list(point+(0,-2)),list(point+(0,2))]])
            annot=page.add_ink_annot(paths)
        annot.set_colors(stroke=(.08,.42,.34));annot.set_border(width=1);annot.set_info(content=label,title='Reapdf');annot.update()
        identity=uuid4().hex;record={'version':1,'id':identity,'kind':kind,'value':value,'unit':label_unit,'points':pts,'calibration':cal if kind!='count' else None}
        doc.xref_set_key(annot.xref,'ReapdfMeasurement',pdf_string(json.dumps(record,ensure_ascii=False,allow_nan=False)))
        if kind!='count':
            factor=scale/UNITS[unit];fmt=f'<< /Type /NumberFormat /U {pdf_string(unit)} /C {factor:.12g} >>';area=f'<< /Type /NumberFormat /U {pdf_string(unit+"²")} /C {factor*factor:.12g} >>'
            doc.xref_set_key(annot.xref,'Measure',f'<< /Type /Measure /Subtype /RL /R {pdf_string("1 pt = "+str(factor)+" "+unit)} /X [{fmt}] /Y [{fmt}] /D [{fmt}] /A [{area}] >>')
            doc.xref_set_key(page.xref,'ReapdfCalibration',pdf_string(json.dumps(cal,ensure_ascii=False,allow_nan=False)))
        # A linked FreeText label prints with the measurement; deletion removes
        # both by our stable ID. Other annotations are left alone.
        anchor=native[0];width=min(180,page.cropbox.width-4);height=18
        rotation=page.rotation;page.set_rotation(0)
        x=min(max(2,anchor.x),page.rect.width-width-2);y=min(max(2,anchor.y+5),page.rect.height-height-2)
        label_annot=page.add_freetext_annot(f.Rect(x,y,x+width,y+height),label,fontsize=9,text_color=(.08,.32,.26),fill_color=(1,1,1));doc.xref_set_key(label_annot.xref,'ReapdfMeasureLabel',pdf_string(identity));page.set_rotation(rotation)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def delete_measure(base,ops,number,identity):
    if not isinstance(identity,str) or len(identity)!=32:raise DocumentError('Medición no válida.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number];targets=[];found=False
        for annot in page.annots() or []:
            record=read_record(doc,annot.xref,'ReapdfMeasurement');kind,value=doc.xref_get_key(annot.xref,'ReapdfMeasureLabel')
            if isinstance(record,dict) and record.get('id')==identity:found=True;targets.append(annot.xref)
            elif kind=='string' and value==identity:targets.append(annot.xref)
        if not found:raise DocumentError('La medición ya no existe en esta versión.')
        for xref in targets:page.delete_annot(page.load_annot(xref))
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
