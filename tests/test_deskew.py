import pymupdf as f
import pytest
from backend.deskew import inspect
from backend.region_ocr import recognize
from backend.engine import DocumentError
from tests.test_scan_geometry import scan


@pytest.mark.parametrize('angle',[-12,-8,-3.5,0,4,7,12])
def test_angle_from_real_scan_can_be_reviewed_and_used_without_changing_pixels(angle):
    base=scan(angle);box=[80,90,450,200];report=inspect(base,[],0,box)
    assert report['angle'] is not None and abs(report['angle']-angle)<=.4 and report['review_required'] and not report['source_modified']
    out,_=recognize(base,[],[{'page':0,'box':box}],language='eng',correction={'angle':report['angle']})
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().split()==['GEOMETRY','TEST','12345']
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples


@pytest.mark.parametrize('rotation',[90,180,270])
def test_orthogonal_orientation_and_crop_keep_small_angle(rotation):
    base=scan(7,rotation,True)
    with f.open(stream=base) as d:r=f.Rect(70,70,520,270)*d[0].rotation_matrix
    report=inspect(base,[],0,[r.x0,r.y0,r.width,r.height],(360-rotation)%360)
    assert report['angle'] is not None and abs(report['angle']-7)<=.4


@pytest.mark.parametrize('dark',[False,True])
def test_no_suggestion_for_empty_or_solid_region(dark):
    with f.open() as d:
        p=d.new_page(width=300,height=300)
        if dark:p.draw_rect(p.rect,fill=(0,0,0))
        base=d.tobytes()
    report=inspect(base,[],0,[20,20,260,260]);assert report['angle'] is None and report['reason']


@pytest.mark.parametrize('number,box,orientation',[(True,[0,0,100,100],0),(0,[0,0,10,10],0),(0,[0,0,800,800],0),(0,[0,0,float('nan'),100],0),(0,[0,0,200,200],True)])
def test_invalid_detection_input_refused(number,box,orientation):
    with pytest.raises(DocumentError):inspect(scan(),[],number,box,orientation)


def test_api_detection_is_read_only_and_does_not_create_document():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        original=client.post('/api/documents',files={'file':('Scan.pdf',scan(7),'application/pdf')}).json()
        r=client.post('/api/documents/'+original['id']+'/detect-skew',json={'page':0,'box':[80,90,450,200]});assert r.status_code==200,r.text
        assert abs(r.json()['angle']-7)<=.4 and 'id' not in r.json() and not r.json()['source_modified']
