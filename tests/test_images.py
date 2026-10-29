import base64
import struct
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, export_pdf
from backend.images import MAX_IMAGE_BYTES
from backend.pages import organize_pdf
from backend.page_tools import crop_pdf


def picture(kind='png', alpha=False):
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,80,40),alpha)
    pix.clear_with(255)
    if alpha:pix.set_rect(f.IRect(0,0,80,40),(0,0,0,0))
    pix.set_rect(f.IRect(0,0,40,40),(255,0,0,255) if alpha else (255,0,0))
    if not alpha:pix.set_rect(f.IRect(40,0,80,40),(0,0,255))
    return pix.tobytes(kind)


def source(rotation=0,crop=False):
    with f.open() as doc:
        p=doc.new_page(width=400,height=500)
        p.insert_text((30,35),'Texto intacto')
        if crop:p.set_cropbox(f.Rect(20,20,380,480))
        p.set_rotation(rotation)
        doc.new_page().insert_text((30,50),'Segunda pagina')
        return doc.tobytes()


def operation(image_data=None,**changes):
    return {'type':'image','page':0,'points':[[40,60],[200,140]],'data':base64.b64encode(image_data or picture()).decode(),**changes}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_image_orientation_position_resolution_and_other_page_unchanged(rotation,crop):
    original=source(rotation,crop)
    output=export_pdf(original,[operation()])
    with f.open(stream=original) as a,f.open(stream=output) as b:
        assert a[0].get_text()==b[0].get_text()
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        pix=b[0].get_pixmap()
        assert pix.pixel(50,70)==(255,0,0) and pix.pixel(190,70)==(0,0,255)
        assert pix.pixel(39,70)==(255,255,255) and pix.pixel(201,70)==(255,255,255)
        assert b[0].get_images()[0][2:4]==(80,40)
        assert not a[0].get_images()


def test_jpeg_original_encoded_stream_is_preserved():
    image=picture('jpeg')
    with f.open(stream=export_pdf(source(),[operation(image)])) as d:
        xref=d[0].get_images()[0][0]
        assert d.extract_image(xref)['image']==image
        assert d[0].get_images()[0][2:4]==(80,40)


def test_png_transparency_preserves_underlying_content():
    with f.open(stream=export_pdf(source(),[operation(picture(alpha=True))])) as d:
        pix=d[0].get_pixmap()
        assert pix.pixel(50,70)==(255,0,0)
        assert pix.pixel(190,70)==(255,255,255)
        assert d[0].get_images()[0][1]>0


@pytest.mark.parametrize('points',[None,[],[[1,2]],[[1,2],[1,4]],[[10,10],[5,20]],[[0,0],[401,20]],[[0,-1],[20,30]],[[True,0],[20,30]],[[0,0],[float('nan'),30]],[[0,0],[20,30,40]]])
def test_invalid_bounds_fail_without_mutating_original(points):
    data=source()
    with pytest.raises(DocumentError):export_pdf(data,[operation(points=points)])
    with f.open(stream=data) as d:assert not d[0].get_images()


@pytest.mark.parametrize('encoded',[None,1,'','@!','YWJj',base64.b64encode(b'GIF89aBAD').decode(),base64.b64encode(b'\xff\xd8\xff\xe0\x00\x00').decode(),base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()])
def test_invalid_formats(encoded):
    with pytest.raises(DocumentError):export_pdf(source(),[operation(data=encoded)])


def test_oversized_bytes_and_pixel_bomb_rejected_before_decode(monkeypatch):
    oversized=base64.b64encode(b'x'*(MAX_IMAGE_BYTES+1)).decode()
    with pytest.raises(DocumentError):export_pdf(source(),[operation(data=oversized)])
    bomb=bytearray(picture());bomb[16:24]=struct.pack('>II',100000,100000)
    monkeypatch.setattr(f,'Pixmap',lambda *args:pytest.fail('No debe decodificar una imagen gigante'))
    with pytest.raises(DocumentError,match='24 millones'):export_pdf(source(),[operation(bytes(bomb))])


def test_image_total_payload_budget():
    data=picture()+b'\x00'*(1800*1024)
    op=operation(data)
    with pytest.raises(DocumentError,match='4 MB codificados'):export_pdf(source(),[op,op])


def test_permissions_and_signature_restrictions():
    with f.open(stream=source()) as d:
        encrypted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
        with pytest.raises(DocumentError,match='permite modificar'):export_pdf(encrypted,[operation()])
        widget=f.Widget();widget.field_name='Signature';widget.field_type=f.PDF_WIDGET_TYPE_SIGNATURE;widget.rect=f.Rect(20,200,100,230);d[0].add_widget(widget)
        with pytest.raises(DocumentError,match='firmados'):export_pdf(d.tobytes(),[operation()])


def test_api_preview_export_organize_and_crop_preserve_image():
    data=source();op=operation()
    with TestClient(app) as c:
        identity=c.post('/api/documents',files={'file':('image.pdf',data)}).json()['id']
        url=f'/api/documents/{identity}'
        assert c.post(url+'/pages/0/preview',json={'operations':[op],'scale':2}).status_code==200
        exported=c.post(url+'/export',json={'operations':[op]})
        assert exported.status_code==200
        assert c.post(url+'/export',json={}).content==data
        assert c.post(url+'/export',json={'operations':[operation(data='!')]}).status_code==422
    ordered=organize_pdf(data,[op],[{'page':1,'rotation':0},{'page':0,'rotation':90}])
    with f.open(stream=ordered) as d:assert d[1].get_images()[0][2:4]==(80,40)
    cropped=crop_pdf(data,[op],[0],[10,10,10,10])
    with f.open(stream=cropped) as d:assert d[0].get_images()[0][2:4]==(80,40)
