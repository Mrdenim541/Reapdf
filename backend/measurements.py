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


def calibration(value,page,allow_outside=False):
    if not isinstance(value,dict) or set(value)!={'points','distance','unit'}:raise DocumentError('Define dos puntos, su distancia conocida y la unidad.')
    from .measurement_geometry import raw_points
    pts=raw_points(value['points']) if allow_outside else points(value['points'],page)
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
    if kind not in ['distance','perimeter','area','count','angle'] or not isinstance(unit,str) or unit not in (['deg','rad'] if kind=='angle' else UNITS):raise DocumentError('Medición o unidad no válida.')
    pts=points(pts,page,1 if kind=='count' else 3 if kind in ['area','angle'] else 2)
    if kind=='distance' and len(pts)!=2:raise DocumentError('La distancia requiere exactamente dos puntos.')
    if len({tuple(p) for p in pts})!=len(pts):raise DocumentError('No repitas puntos de la medición.')
    if kind=='angle':
        if len(pts)!=3:raise DocumentError('El ángulo necesita exactamente tres puntos: extremo, vértice y extremo.')
        a,b,c=[f.Point(p) for p in pts];u=a-b;v=c-b
        if min(abs(u),abs(v))<1:raise DocumentError('Cada brazo del ángulo debe medir al menos 1 pt.')
        angle=math.atan2(abs(u.x*v.y-u.y*v.x),u.x*v.x+u.y*v.y)
        return (math.degrees(angle) if unit=='deg' else angle),pts,'°' if unit=='deg' else 'rad'
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
    except (ValueError,TypeError,RecursionError):return None


def model(base,ops,number):
    from .measurement_geometry import page_at,decode,read_profiles,cal_to_view,native_vertices
    with open_pdf(export_pdf(base,ops)) as doc:
        page=page_at(doc,number);rows=[];invalid=0
        for annot in page.annots() or []:
            record=read_record(doc,annot.xref,'ReapdfMeasurement')
            if record is None:
                if doc.xref_get_key(annot.xref,'ReapdfMeasurement')[0]!='null':invalid+=1
                continue
            try:
                row=decode(page,record);native_pts=native_vertices(page,annot,row['kind'])
                if record['version']==2 and (len(native_pts)!=len(row['points']) or any(math.dist(a,b)>.02 for a,b in zip(native_pts,row['points']))):raise DocumentError('La medición y su geometría nativa no coinciden.')
                if record['version']==1:row['points']=native_pts;row['editable']=False
            except (DocumentError,KeyError,TypeError,ValueError):invalid+=1;continue
            if len(rows)>=500:raise DocumentError('Hasta 500 mediciones por página.')
            rows.append({k:row[k] for k in ['id','kind','value','unit','points','calibration','editable','result_unit']}|{'xref':annot.xref,'label':annot.info.get('content','')[:400],'profile':record.get('profile'),'legacy':record['version']==1,'can_migrate':record['version']==1 and all(page.rect.contains(f.Point(p)) for p in native_pts)})
        cal=read_record(doc,page.xref,'ReapdfCalibration')
        if cal is not None:
            try:
                if isinstance(cal,dict) and cal.get('version')==2:cal=cal_to_view(page,cal['calibration'])
                else:cal=None;raise DocumentError('La escala antigua necesita una nueva referencia.')
                calibration(cal,page,allow_outside=True)
            except (DocumentError,KeyError,TypeError,ValueError):cal=None
        return {'measurements':rows,'invalid_measurements':invalid,'calibration':cal,'scales':[{k:p[k] for k in ['id','name','box','calibration','visible']} for p in read_profiles(doc,page)]}


def measure(base,ops,number,kind,pts,cal,unit='m',preview=False,identity=None,profile=None,migrate=False):
    if type(migrate) is not bool or migrate and identity is None:raise DocumentError('La actualización de referencia requiere una medición antigua identificada.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_ANNOTATE:raise DocumentError('El documento no permite anotaciones.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number]
        from .measurement_geometry import transform,cal_to_pdf,cal_to_view,decode,read_profiles,native_vertices,matrices
        allow_outside=False
        if identity is not None:
            targets=[a for a in page.annots() or [] if isinstance(read_record(doc,a.xref,'ReapdfMeasurement'),dict) and read_record(doc,a.xref,'ReapdfMeasurement').get('id')==identity]
            if len(targets)!=1:raise DocumentError('La medición ya no existe o su identificador es ambiguo.')
            original=decode(page,read_record(doc,targets[0].xref,'ReapdfMeasurement'))
            actual_pts=native_vertices(page,targets[0],kind)
            if migrate:
                if original['version']!=1 or cal is None or kind!=original['kind'] or not isinstance(pts,list) or len(pts)!=len(actual_pts) or any(not isinstance(p,list) or len(p)!=2 or any(not finite(v) for v in p) or math.dist(p,q)>.02 for p,q in zip(pts,actual_pts)):raise DocumentError('Actualiza una medición antigua con una nueva referencia, conservando sus vértices nativos. Después podrás editarlos.')
            else:
                if len(actual_pts)!=len(original['points']) or any(math.dist(a,b)>.02 for a,b in zip(actual_pts,original['points'])):raise DocumentError('La geometría nativa de la medición cambió fuera de este editor.')
                if original['version']!=2 or not original['editable']:raise DocumentError('Esta medición antigua o recortada necesita una nueva referencia antes de editar sus vértices.')
                if kind!=original['kind']:raise DocumentError('Conserva el tipo de la medición al editar sus vértices.')
            if cal is None:cal=original['calibration'];allow_outside=True
        if profile is not None:
            matches=[r for r in read_profiles(doc,page) if r['id']==profile]
            if len(matches)!=1:raise DocumentError('La escala regional ya no existe.')
            selected=matches[0];x,y,w,h=selected['box'];region=f.Rect(x,y,x+w,y+h)
            if any(not region.contains(f.Point(p)) for p in points(pts,page,1)):raise DocumentError('La medición cruza el límite de su región de escala. Divídela en mediciones separadas.')
            cal=selected['calibration'];allow_outside=True
        scale=1 if kind in ['count','angle'] else calibration(cal,page,allow_outside)
        value,pts,label_unit=calculate(page,kind,pts,scale,unit)
        label={'distance':'Distancia','perimeter':'Longitud','area':'Área','count':'Cantidad','angle':'Ángulo'}[kind]+f': {value:,.3f} {label_unit}'.rstrip()
        if preview:return {'value':value,'unit':label_unit,'label':label,'scale_m_per_pt':scale,'points':pts}
        if identity is None and sum(1 for a in page.annots() or [] if read_record(doc,a.xref,'ReapdfMeasurement'))>=500:raise DocumentError('Hasta 500 mediciones por página.')
        if identity is not None:remove_from_page(doc,page,identity)
        _,rotate=matrices(page);native=[f.Point(p)*~rotate for p in pts];pdf_pts=transform(page,pts,True);cal_pdf=cal_to_pdf(page,cal) if kind not in ['count','angle'] else None;rotation=page.rotation;page.set_rotation(0)
        if kind=='distance':annot=page.add_line_annot(*native)
        elif kind in ['perimeter','angle']:annot=page.add_polyline_annot(native)
        elif kind=='area':annot=page.add_polygon_annot(native)
        else:
            paths=[]
            for point in native:
                paths.extend([[list(point+(-2,0)),list(point+(2,0))],[list(point+(0,-2)),list(point+(0,2))]])
            annot=page.add_ink_annot(paths)
        annot.set_colors(stroke=(.08,.42,.34));annot.set_border(width=1);annot.set_info(content=label,title='Reapdf');annot.update()
        identity=identity or uuid4().hex;record={'version':2,'id':identity,'kind':kind,'value':value,'unit':label_unit,'points':pdf_pts,'calibration':cal_pdf,'profile':profile}
        doc.xref_set_key(annot.xref,'NM',pdf_string('reapdf-measure-'+identity))
        doc.xref_set_key(annot.xref,'ReapdfMeasurement',pdf_string(json.dumps(record,ensure_ascii=False,allow_nan=False)))
        if kind not in ['count','angle']:
            factor=cal['distance']*UNITS[cal['unit']]/math.dist(*cal_pdf['points'])/UNITS[unit];fmt=f'<< /Type /NumberFormat /U {pdf_string(unit)} /C {factor:.12g} >>';area=f'<< /Type /NumberFormat /U {pdf_string(unit+"²")} /C {factor*factor:.12g} >>'
            doc.xref_set_key(annot.xref,'Measure',f'<< /Type /Measure /Subtype /RL /R {pdf_string("1 pt = "+str(factor)+" "+unit)} /X [{fmt}] /Y [{fmt}] /D [{fmt}] /A [{area}] >>')
            doc.xref_set_key(page.xref,'ReapdfCalibration',pdf_string(json.dumps({'version':2,'calibration':cal_pdf},ensure_ascii=False,allow_nan=False)))
        # A linked FreeText label prints with the measurement; deletion removes
        # both by our stable ID. Other annotations are left alone.
        anchor=native[0];width=min(180,page.cropbox.width-4);height=18
        x=min(max(2,anchor.x),page.rect.width-width-2);y=min(max(2,anchor.y+5),page.rect.height-height-2)
        label_annot=page.add_freetext_annot(f.Rect(x,y,x+width,y+height),label,fontsize=9/max(.0001,abs(matrices(page)[0].a)),text_color=(.08,.32,.26),fill_color=(1,1,1));doc.xref_set_key(label_annot.xref,'ReapdfMeasureLabel',pdf_string(identity));doc.xref_set_key(label_annot.xref,'NM',pdf_string('reapdf-measure-label-'+identity));page.set_rotation(rotation)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)


def remove_from_page(doc,page,identity):
    targets=[];found=0
    for annot in page.annots() or []:
        record=read_record(doc,annot.xref,'ReapdfMeasurement');kind,value=doc.xref_get_key(annot.xref,'ReapdfMeasureLabel')
        if isinstance(record,dict) and record.get('id')==identity:found+=1;targets.append(annot.xref)
        elif kind=='string' and value==identity:targets.append(annot.xref)
    if found!=1:raise DocumentError('La medición ya no existe o tiene un identificador ambiguo.')
    for xref in targets:page.delete_annot(page.load_annot(xref))


def delete_measure(base,ops,number,identity):
    if not isinstance(identity,str) or len(identity)!=32:raise DocumentError('Medición no válida.')
    with open_pdf(base) as source:
        editable(source)
        if not source.permissions&f.PDF_PERM_ANNOTATE:raise DocumentError('El documento no permite anotaciones.')
    with open_pdf(export_pdf(base,ops)) as doc:
        from .measurement_geometry import page_at
        page=page_at(doc,number);remove_from_page(doc,page,identity)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
