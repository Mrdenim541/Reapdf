import json,math
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import measurements as m
from backend.measurement_geometry import configure_profile,targets,transform
from backend.engine import DocumentError
from backend.form_structure import pdf_string
from backend.projects import build_project,read_project

CAL={'points':[[40,80],[140,80]],'distance':10,'unit':'m'}


def source(rotation=0):
    with f.open() as d:
        p=d.new_page(width=500,height=600);p.draw_rect(f.Rect(40,80,200,250));p.draw_line((40,80),(200,250));p.insert_text((40,500),'PRESERVED')
        d.new_page().insert_text((40,80),'OTHER PAGE');d[0].set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind,pts',[('distance',[[50,100],[150,100]]),('perimeter',[[50,100],[150,100],[150,200]]),('area',[[50,100],[150,100],[150,200],[50,200]]),('count',[[50,100],[150,100]])])
def test_edit_vertices_stable_identity_recalculation_label_and_project(rotation,kind,pts):
    base=source(rotation);out=m.measure(base,[],0,kind,pts,CAL);row=m.model(out,[],0)['measurements'][0];assert row['editable'] and not row['legacy']
    changed=[list(p) for p in pts];changed[-1][0]+=20
    result=m.measure(out,[],0,kind,changed,None,identity=row['id']);after=m.model(result,[],0)['measurements'][0]
    assert after['id']==row['id'] and after['points']==changed
    if kind!='count':assert after['value']!=row['value']
    with f.open(stream=result) as d,f.open(stream=base) as a:
        assert len(list(d[0].annots()))==2 and d[0].rotation==rotation
        labels=[v for v in d[0].annots() if d.xref_get_key(v.xref,'ReapdfMeasureLabel')[0]=='string'];assert len(labels)==1 and after['label']==labels[0].info['content']
        assert d[1].get_pixmap().samples==a[1].get_pixmap().samples
    archive,_=build_project(result,[],{'name':'precision.pdf'});saved,_,_=read_project(archive);assert m.model(saved,[],0)==m.model(result,[],0)


@pytest.mark.parametrize('initial',[0,90,180,270])
@pytest.mark.parametrize('final',[0,90,180,270])
def test_pdf_anchoring_after_rotation_and_crop(initial,final):
    data=m.measure(source(initial),[],0,'distance',[[60,120],[160,120]],CAL)
    with f.open(stream=data) as d:
        original=m.read_record(d,next(d[0].annots()).xref,'ReapdfMeasurement')['points'];p=d[0];p.set_rotation(final);p.set_cropbox(f.Rect(20,30,480,570));edited=d.tobytes();expected=transform(p,original)
    row=m.model(edited,[],0)['measurements'][0];assert row['value']==pytest.approx(10) and row['points']==expected
    with f.open(stream=edited) as d:
        page=d[0];a=next(page.annots());native=[list(f.Point(p)*page.rotation_matrix) for p in a.vertices]
    for a,b in zip(native,expected):assert a==pytest.approx(b,abs=1e-4)


def test_profiles_different_scales_bounds_update_remove_and_persistence():
    base=source();out=configure_profile(base,[],0,'Detalle A',[20,40,200,240],CAL);first=m.model(out,[],0)['scales'][0]
    second_cal={'points':[[280,80],[380,80]],'distance':2,'unit':'m'}
    out=configure_profile(out,[],0,'Detalle B',[260,40,200,240],second_cal);scales=m.model(out,[],0)['scales'];assert len(scales)==2
    for row,pts,value in [(scales[0],[[50,120],[150,120]],10),(scales[1],[[280,120],[380,120]],2)]:
        preview=m.measure(out,[],0,'distance',pts,None,preview=True,profile=row['id']);assert preview['value']==pytest.approx(value)
    with pytest.raises(DocumentError,match='límite'):m.measure(out,[],0,'distance',[[50,120],[300,120]],None,profile=first['id'])
    with pytest.raises(DocumentError,match='solaparse'):configure_profile(out,[],0,'Overlap',[100,50,200,200],{**CAL,'points':[[120,80],[220,80]]})
    out=configure_profile(out,[],0,'Renombrada',[20,40,200,240],{**CAL,'distance':20},first['id']);assert len(m.model(out,[],0)['scales'])==2
    out=configure_profile(out,[],0,identity=first['id'],remove=True);assert len(m.model(out,[],0)['scales'])==1


def test_profile_rotated_cropped_and_used_when_reference_is_offscreen():
    out=configure_profile(source(),[],0,'Detalle',[20,40,200,240],CAL);identity=m.model(out,[],0)['scales'][0]['id']
    with f.open(stream=out) as d:d[0].set_cropbox(f.Rect(100,100,480,570));d[0].set_rotation(90);out=d.tobytes()
    profile=m.model(out,[],0)['scales'][0];assert profile['visible']
    with f.open(stream=out) as d:pts=transform(d[0],[[120,450],[180,450]])
    # PDF-space y=450 corresponds to native y=150, inside the surviving region.
    result=m.measure(out,[],0,'distance',pts,None,preview=True,profile=identity);assert result['value']==pytest.approx(6)


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_snaps_match_rendered_vector_geometry(rotation):
    base=source(rotation);data=targets(base,[],0);assert len(data['points'])==4 and not data['limited']
    with f.open(stream=base) as d:expected=[list(f.Point(p)*d[0].rotation_matrix) for p in [(40,80),(200,80),(200,250),(40,250)]]
    assert {tuple(p['point']) for p in data['points']}=={tuple(p) for p in expected}


def test_duplicate_identity_or_changed_geometry_fails_without_publishing():
    base=m.measure(source(),[],0,'distance',[[50,100],[150,100]],CAL);identity=m.model(base,[],0)['measurements'][0]['id']
    with f.open(stream=base) as d:
        record=m.read_record(d,next(d[0].annots()).xref,'ReapdfMeasurement');other=d[0].add_line_annot((50,100),(150,100));d.xref_set_key(other.xref,'ReapdfMeasurement',pdf_string(json.dumps(record)));bad=d.tobytes()
    with pytest.raises(DocumentError,match='ambiguo'):m.measure(bad,[],0,'distance',[[50,100],[170,100]],None,identity=identity)
    assert len(m.model(base,[],0)['measurements'])==1


def test_api_scale_snap_and_edit_preview():
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('precision.pdf',source(),'application/pdf')}).json();url='/api/documents/'+doc['id']
        assert len(c.post(url+'/measurement-targets',json={'page':0}).json()['points'])==4
        response=c.post(url+'/measurement-scale',json={'page':0,'name':'Detalle','box':[20,40,200,240],'calibration':CAL});assert response.status_code==200,response.text
        after='/api/documents/'+response.json()['id'];profile=c.get(after+'/measurements').json()['scales'][0]
        response=c.post(after+'/measure',json={'page':0,'kind':'distance','points':[[50,120],[150,120]],'profile':profile['id'],'preview':True});assert response.status_code==200 and response.json()['value']==10


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_pdf_user_unit_and_crop_keep_scale_and_coordinates(rotation):
    with f.open(stream=source()) as d:
        d.xref_set_key(d[0].xref,'UserUnit','2');base=d.tobytes()
    data=m.measure(base,[],0,'distance',[[60,120],[160,120]],CAL)
    with f.open(stream=data) as d:
        p=d[0];a=next(p.annots());original=m.read_record(d,a.xref,'ReapdfMeasurement')['points'];p.set_cropbox(f.Rect(10,20,490,580));p.set_rotation(rotation);expected=transform(p,original);data=d.tobytes()
    row=m.model(data,[],0)['measurements'][0];assert row['points']==expected and row['value']==pytest.approx(10)


def test_external_geometry_change_is_reported_not_silently_recomputed():
    data=m.measure(source(),[],0,'distance',[[50,100],[150,100]],CAL)
    with f.open(stream=data) as d:
        page=d[0];a=next(page.annots());d.xref_set_key(a.xref,'L','[50 500 200 500]');data=d.tobytes()
    state=m.model(data,[],0);assert not state['measurements'] and state['invalid_measurements']==1


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_image_corner_snaps_in_scaled_user_space(rotation):
    with f.open(stream=source()) as d:
        page=d[0];pix=f.Pixmap(f.csRGB,f.IRect(0,0,10,10),False);pix.clear_with(200);page.insert_image(f.Rect(300,300,400,350),pixmap=pix,keep_proportion=False);d.xref_set_key(page.xref,'UserUnit','2');page.set_rotation(rotation);data=d.tobytes()
    result=targets(data,[],0);actual={tuple(row['point']) for row in result['points'] if row['source']=='image'}
    rotate={0:f.Matrix(1,1),90:f.Matrix(0,1,-1,0,1200,0),180:f.Matrix(-1,0,0,-1,1000,1200),270:f.Matrix(0,-1,1,0,0,1000)}[rotation]
    expected={tuple(f.Point(x*2,y*2)*rotate) for x,y in [(300,300),(400,300),(400,350),(300,350)]};assert actual==expected


@pytest.mark.parametrize('user_unit',[1,2])
def test_independent_parser_confirms_native_measure_scale_and_label_size(user_unit):
    from io import BytesIO
    from pyhanko.pdf_utils.reader import PdfFileReader
    with f.open(stream=source()) as d:d.xref_set_key(d[0].xref,'UserUnit',str(user_unit));base=d.tobytes()
    data=m.measure(base,[],0,'distance',[[60,120],[160,120]],CAL)
    root=PdfFileReader(BytesIO(data)).root;page=root['/Pages']['/Kids'][0].get_object();annots=[r.get_object() for r in page['/Annots']];line=next(a for a in annots if a['/Subtype']=='/Line');label=next(a for a in annots if a['/Subtype']=='/FreeText');coords=[float(v) for v in line['/L']];factor=float(line['/Measure']['/D'][0]['/C'])
    assert math.dist(coords[:2],coords[2:])*factor==pytest.approx(10)
    assert float(str(label['/DA']).split()[-2])==pytest.approx(9/user_unit)
