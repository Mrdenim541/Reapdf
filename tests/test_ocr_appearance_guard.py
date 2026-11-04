import pymupdf as f
import pytest
from backend.ocr import ocr_pdf
from backend.engine import DocumentError
from tests.test_long_advance import source


def test_real_ocr_reports_checked_appearance_and_preserves_scan_and_grid():
    with f.open(stream=source(scan=True)) as d:
        p=d[0];p.draw_rect(f.Rect(25,100,470,300));p.draw_line((25,200),(470,200));p.add_rect_annot(f.Rect(40,130,220,180)).update();base=d.tobytes()
    result,report=ocr_pdf(base,[],[0,1],'eng',150)
    assert report['appearance_verified_pages']==[0] and report['appearance_verification_dpi']==150
    assert report['skipped']==[1]
    with f.open(stream=base) as a,f.open(stream=result) as b:
        assert a[0].get_pixmap(matrix=f.Matrix(2,2)).samples==b[0].get_pixmap(matrix=f.Matrix(2,2)).samples
        assert [{k:v for k,v in drawing.items() if k!='seqno'} for drawing in a[0].get_drawings()]==[{k:v for k,v in drawing.items() if k!='seqno'} for drawing in b[0].get_drawings()]
        assert [(x['bbox'],x['transform'],x['digest']) for x in a[0].get_image_info(hashes=True)]==[(x['bbox'],x['transform'],x['digest']) for x in b[0].get_image_info(hashes=True) if x['width']>1]


def test_visible_content_from_recognition_is_rejected_before_publication(monkeypatch):
    with f.open() as d:
        d.new_page(width=500,height=650).insert_text((50,50),'ACCIDENTAL VISIBLE CONTENT');bad=d.tobytes()
    monkeypatch.setattr(f.Pixmap,'pdfocr_tobytes',lambda *a,**kw:bad)
    base=source(scan=True)
    with pytest.raises(DocumentError,match='cambió el aspecto'):ocr_pdf(base,[],[0],'eng',150)
    with f.open(stream=base) as original:assert not original[0].get_text()


def test_api_does_not_publish_changed_appearance_and_releases_ocr_lock(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    with f.open() as d:
        d.new_page(width=500,height=650).insert_text((30,30),'WRONG VISIBLE RESULT');bad=d.tobytes()
    monkeypatch.setattr(f.Pixmap,'pdfocr_tobytes',lambda *a,**kw:bad)
    base=source(scan=True)
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Scan.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        for _ in range(2):
            r=c.post(url+'/ocr',json={'pages':[0],'language':'eng','dpi':150});assert r.status_code==422,r.text;assert 'cambió el aspecto' in r.json()['detail']
        assert len(list(app.state.root.glob('*.pdf')))==1
        assert c.post(url+'/export',json={}).content==base
