import hashlib,math
import pytest,pymupdf as f
from backend.redaction import redact_pdf
from backend.engine import DocumentError


def source(rotation=0,crop=False):
    with f.open() as inner,f.open() as d:
        q=inner.new_page(width=300,height=400);q.insert_text((50,100),'HIDDEN-93427',fontsize=18);q.insert_text((50,160),'PUBLIC-58291',fontsize=18)
        p=d.new_page(width=400,height=500);p.show_pdf_page(f.Rect(0,0,300,400),inner,0)
        x=p.get_contents()[-1];d.update_stream(x,b'/Span <</ActualText (SECRET-STRUCTURE)>> BDC '+d.xref_stream(x)+b' EMC')
        p.add_text_annot((330,40),'SECRET-COMMENT');p.insert_link({'kind':f.LINK_URI,'from':f.Rect(310,100,380,125),'uri':'https://example.com/SECRET-LINK'})
        if crop:p.set_cropbox(f.Rect(20,30,380,470))
        p.set_rotation(rotation)
        d.embfile_add('Secret.txt',b'SECRET-ATTACHMENT');d.set_metadata({'title':'SECRET-METADATA'})
        d.new_page(width=400,height=500).insert_text((30,60),'PUBLIC-SECOND-PAGE')
        return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_complex_copy_contains_only_redacted_pixels_and_no_original_objects(rotation,crop):
    base=source(rotation,crop);digest=hashlib.sha256(base).hexdigest();dpi=150
    with f.open(stream=base) as a:
        rect=f.Rect(40-(20 if crop else 0),75-(30 if crop else 0),220-(20 if crop else 0),110-(30 if crop else 0))*a[0].rotation_matrix
        box=[rect.x0,rect.y0,rect.width,rect.height]
    out=redact_pdf(base,[],[{'page':0,'box':box}],'raster',dpi)
    with f.open(stream=out) as d,f.open(stream=base) as a:
        assert len(d)==2 and not d.embfile_count() and not d.metadata['title']
        for p in d:
            assert not p.get_text() and not p.get_links() and not list(p.annots() or []) and not p.get_xobjects() and len(p.get_images())==1
        assert d[0].rect==a[0].rect
        pix=d[0].get_pixmap(matrix=f.Matrix(dpi/72,dpi/72),alpha=False)
        center=rect.tl+(rect.br-rect.tl)/2
        assert pix.pixel(int(center.x*dpi/72),int(center.y*dpi/72))==(0,0,0)
        all_data=b' '.join(d.xref_stream(x) if d.xref_is_stream(x) else d.xref_object(x).encode() for x in range(1,d.xref_length()))
        assert not any(v in all_data for v in [b'SECRET',b'HIDDEN',b'/ActualText',b'/StructTreeRoot'])
        # A second page has no regions and retains all visible pixels at the chosen resolution.
        old=a[1].get_pixmap(matrix=f.Matrix(dpi/72,dpi/72),alpha=False)
        new=d[1].get_pixmap(matrix=f.Matrix(dpi/72,dpi/72),alpha=False)
        assert old.width==new.width and old.height==new.height
        assert sum(abs(a-b) for a,b in zip(old.samples,new.samples))/len(old.samples)<1
    assert hashlib.sha256(base).hexdigest()==digest


@pytest.mark.parametrize('dpi',[True,0,72,400,None])
def test_invalid_resolution_is_rejected(dpi):
    with pytest.raises(DocumentError):redact_pdf(source(),[],[{'page':0,'box':[20,20,30,30]}],'raster',dpi)


def test_large_visual_copy_and_out_of_bounds_regions_are_rejected():
    with f.open() as d:
        for _ in range(21):d.new_page()
        base=d.tobytes()
    with pytest.raises(DocumentError,match='20 páginas'):redact_pdf(base,[],[{'page':0,'box':[20,20,30,30]}],'raster')
    with pytest.raises(DocumentError,match='sale'):redact_pdf(source(),[],[{'page':0,'box':[2000,20,30,30]}],'raster')


def test_visual_copy_api_preview_and_download_are_independent_of_original():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Example.pdf',source(),'application/pdf')}).json();url=f"/api/documents/{doc['id']}/redact"
        payload={'operations':[],'regions':[{'page':0,'box':[40,75,180,35]}],'method':'raster','dpi':150}
        r=c.post(url,json={**payload,'preview':True,'preview_page':0});assert r.status_code==200 and r.headers['content-type']=='image/png'
        r=c.post(url,json=payload);assert r.status_code==200
        with f.open(stream=r.content) as d:assert not d[0].get_text()
