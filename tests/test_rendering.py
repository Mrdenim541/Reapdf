import struct
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.rendering import render_page,MAX_PIXELS,MAX_EDGE


def pdf(width=300,height=400):
    with f.open() as d:
        p=d.new_page(width=width,height=height);p.insert_text((30,80),'Texto vectorial',fontsize=14)
        p.draw_line((30,100),(200,100),width=.5)
        return d.tobytes()


def dimensions(png):return struct.unpack('>II',png[16:24])


def test_zoom_rerasterizes_vector_content_instead_of_stretching_same_bitmap():
    with f.open(stream=pdf(),filetype='pdf') as d:
        low,_=render_page(d[0],1);high,headers=render_page(d[0],3)
        assert dimensions(low)==(300,400)
        assert dimensions(high)==(900,1200)
        assert low!=high and headers['X-Render-Limited']=='false'
        assert float(headers['X-Render-Scale'])==3


@pytest.mark.parametrize('scale',[0,-1,17,True,None,'2',float('nan'),float('inf')])
def test_invalid_scales_rejected(scale):
    with f.open(stream=pdf(),filetype='pdf') as d:
        with pytest.raises(DocumentError):render_page(d[0],scale)


def test_render_memory_budget_and_headers_match_actual_output():
    with f.open(stream=pdf(3000,3000),filetype='pdf') as d:
        image,headers=render_page(d[0],16)
        width,height=dimensions(image)
        assert width*height<=MAX_PIXELS and max(width,height)<=MAX_EDGE
        assert headers['X-Render-Limited']=='true'
        assert width==int(headers['X-Render-Width']) and height==int(headers['X-Render-Height'])


def test_preview_and_image_endpoint_honor_scale_without_changing_original():
    data=pdf()
    with TestClient(app) as c:
        identity=c.post('/api/documents',files={'file':('zoom.pdf',data)}).json()['id'];base=f'/api/documents/{identity}'
        for scale in [1,2,4]:
            r=c.post(base+'/pages/0/preview',json={'operations':[],'scale':scale})
            assert r.status_code==200 and dimensions(r.content)==(300*scale,400*scale)
        r=c.get(base+'/pages/0/image?scale=2');assert dimensions(r.content)==(600,800)
        for scale in [0,17,True,'large']:
            assert c.post(base+'/pages/0/preview',json={'scale':scale}).status_code==422
        assert c.post(base+'/export',json={}).content==data
