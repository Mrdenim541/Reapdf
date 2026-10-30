import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.region_ocr import recognize
from backend.scan_geometry import corners,homography,project


def scan(angle=0,rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=600,height=450)
        p.insert_text((130,180),'GEOMETRY TEST 12345',fontsize=24,morph=(f.Point(300,200),f.Matrix(-angle)))
        pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
        with f.open() as out:
            q=out.new_page(width=600,height=450);q.insert_image(q.rect,stream=pix.tobytes('png'))
            if crop:q.set_cropbox(f.Rect(10,20,590,430))
            q.set_rotation(rotation);return out.tobytes()


@pytest.mark.parametrize('angle',[-8,0,7])
def test_actual_inclined_scan_is_recognized_and_pixels_preserved(angle):
    base=scan(angle);out,report=recognize(base,[],[{'page':0,'box':[80,110,450,160]}],language='eng',correction={'angle':angle})
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().split()==['GEOMETRY','TEST','12345']
        assert a[0].get_pixmap(matrix=f.Matrix(1.5,1.5)).samples==b[0].get_pixmap(matrix=f.Matrix(1.5,1.5)).samples
        words=b[0].get_text('words');mapped=report['regions'][0]['mapped_words'];assert len(words)==len(mapped)==3
        for actual,expected in zip(words,mapped):
            rect=f.Quad(expected['quad'][0],expected['quad'][1],expected['quad'][3],expected['quad'][2]).rect
            assert (f.Rect(actual[:4])&rect).get_area()/rect.get_area()>.8


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_visible_geometry_handles_page_rotation_and_crop(rotation,crop):
    base=scan(rotation=rotation,crop=crop)
    with f.open(stream=base) as d:
        rect=f.Rect(60-(10 if crop else 0),100-(20 if crop else 0),550-(10 if crop else 0),300-(20 if crop else 0))*d[0].rotation_matrix
    # Orientation is corrected relative to the displayed scan.
    out,report=recognize(base,[],[{'page':0,'box':[rect.x0,rect.y0,rect.width,rect.height]}],language='eng',orientation=(360-rotation)%360,correction={'angle':0})
    with f.open(stream=out) as d:
        assert d[0].get_text().strip()=='GEOMETRY TEST 12345'
        assert d[0].rotation==rotation
        for word in d[0].get_text('words'):assert f.Rect(110,110,460,220).contains(f.Rect(word[:4]))
    with f.open(stream=base) as a,f.open(stream=out) as b:assert a[0].get_pixmap().samples==b[0].get_pixmap().samples


def test_quadrilateral_rectification_reports_exact_projective_word_corners():
    base=scan();quad=[[80,95],[540,110],[515,290],[90,285]]
    out,report=recognize(base,[],[{'page':0,'box':[80,95,460,195]}],language='eng',correction={'quad':quad})
    with f.open(stream=out) as d:assert d[0].get_text().strip()=='GEOMETRY TEST 12345'
    assert all(len(w['quad'])==4 for w in report['regions'][0]['mapped_words'])
    h=homography(quad)
    for uv,p in zip([(0,0),(1,0),(1,1),(0,1)],quad):assert abs(project(h,*uv)-f.Point(p))<1e-7
    center=project(h,.5,.5);assert abs(center-f.Point(306.25,195))>1


@pytest.mark.parametrize('correction',[
 {},{'angle':True},{'angle':float('nan')},{'angle':16},{'angle':0,'quad':[]},
 {'quad':[]},{'quad':[[0,0],[100,100],[100,0],[0,100]]},
 {'quad':[[0,0],[1,0],[1,20],[0,20]]},{'quad':[[0,0],[100,0],[20,20],[0,100]]},
 {'quad':[[-1,0],[100,0],[100,100],[0,100]]},{'quad':[[0,0],[100,0],[100,float('inf')],[0,100]]},
 ])
def test_invalid_or_degenerate_geometry_fails_without_modification(correction):
    with pytest.raises(DocumentError):recognize(scan(),[],[{'page':0,'box':[80,110,450,160]}],language='eng',correction=correction)


def test_corrected_ocr_refuses_duplicates_and_multiple_regions():
    base=scan();out,_=recognize(base,[],[{'page':0,'box':[80,110,450,160]}],language='eng',correction={'angle':0})
    with pytest.raises(DocumentError,match='texto digital'):recognize(out,[],[{'page':0,'box':[80,110,450,160]}],language='eng',correction={'angle':0})
    with pytest.raises(DocumentError,match='una región'):recognize(base,[],[{'page':0,'box':[80,110,450,160]}]*2,language='eng',correction={'angle':0})


def test_api_corrected_ocr_and_project_roundtrip():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('scan.pdf',scan(),'application/pdf')}).json();r=c.post('/api/documents/'+doc['id']+'/ocr-regions',json={'regions':[{'page':0,'box':[80,110,450,160]}],'language':'eng','correction':{'angle':0}})
        assert r.status_code==200,r.text
        assert r.json()['ocr_report']['words']==3 and r.json()['id']!=doc['id']


def test_corrected_pdf_survives_project_without_reprocessing_ocr():
    from backend.projects import build_project,read_project
    base,_=recognize(scan(7),[],[{'page':0,'box':[80,110,450,160]}],language='eng',correction={'angle':7})
    restored,ops,_=read_project(build_project(base,[],{'name':'Corrected.pdf'})[0])
    assert restored==base and not ops
    with f.open(stream=restored) as doc:assert doc[0].get_text().split()==['GEOMETRY','TEST','12345']


def test_projective_image_and_text_coordinates_agree_under_strong_perspective():
    from backend.scan_geometry import rectify
    points=[[40,40],[360,70],[280,260],[70,240]];h=homography(points)
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,400,300),False);pix.clear_with(255)
    samples=[(.2,.2),(.5,.5),(.8,.8)]
    for u,v in samples:
        p=project(h,u,v)
        for y in range(round(p.y)-2,round(p.y)+3):
            for x in range(round(p.x)-2,round(p.x)+3):pix.set_pixel(x,y,(0,0,0))
    corrected=rectify(pix,points,320,220,200)
    for u,v in samples:
        hits=[(x,y) for y in range(round(v*220)-4,round(v*220)+5) for x in range(round(u*320)-4,round(u*320)+5) if corrected.pixel(x,y)[0]<100]
        assert hits
        assert abs(sum(x for x,y in hits)/len(hits)-u*320)<2 and abs(sum(y for x,y in hits)/len(hits)-v*220)<2
