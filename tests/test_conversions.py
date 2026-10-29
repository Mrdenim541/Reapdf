from io import BytesIO
from zipfile import ZipFile
import struct
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.conversions import images_to_pdf, export_page_images
from backend.engine import DocumentError
from backend.images import image_dimensions


def image(width=60,height=90,format='png',alpha=False):
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,width,height),alpha);pix.clear_with(170)
    return pix.tobytes(format)


def source(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=400,height=500);p.insert_text((40,80),'Original')
        if crop:p.set_cropbox(f.Rect(20,20,380,480))
        p.set_rotation(rotation);d.new_page(width=300,height=400);return d.tobytes()


@pytest.mark.parametrize('paper',['A4','Letter','image'])
@pytest.mark.parametrize('format',['png','jpeg'])
def test_create_pages_in_input_order_without_resampling_original_pixels(paper,format):
    pictures=[image(60,90,format),image(80,40,format)]
    with f.open(stream=images_to_pdf(pictures,paper=paper,dpi=150,margin=18)) as doc:
        assert len(doc)==2
        for p,data in zip(doc,pictures):
            item=p.get_images()[0];assert item[2:4]==image_dimensions(data)
            extracted=doc.extract_image(item[0]);pix=f.Pixmap(extracted['image']);original=f.Pixmap(data)
            assert pix.samples==original.samples
            if format=='jpeg':assert extracted['image']==data
            if paper=='image':assert p.rect.width==pytest.approx(original.width*72/150+36)
            else:assert tuple(p.rect)[2:]==pytest.approx(f.paper_size(paper))
            box=p.get_image_rects(item[0])[0];assert box.width/box.height==pytest.approx(original.width/original.height)


def test_transparent_png_remains_transparent_pdf_with_white_page_background():
    with f.open(stream=images_to_pdf([image(alpha=True)])) as doc:assert doc[0].get_images()[0][1]>0


@pytest.mark.parametrize('patch',[{'images':[]},{'images':[b'bad']},{'images':[b'a'*(2*1024*1024+1)]},{'images':[image()]*31},
    {'paper':'bad'},{'paper':[]},{'dpi':True},{'dpi':71},{'dpi':601},{'margin':True},{'margin':-1},{'margin':145}])
def test_bad_creation_parameters_are_rejected(patch):
    with pytest.raises(DocumentError):images_to_pdf(**{'images':[image()],**patch})


def test_input_pixel_and_natural_page_dimensions_are_bounded_before_decoding():
    picture=bytearray(image());picture[16:24]=struct.pack('>II',50000,50000)
    with pytest.raises(DocumentError,match='píxeles'):images_to_pdf([bytes(picture)])
    with pytest.raises(DocumentError,match='página'):images_to_pdf([image(3100,10)],paper='image',dpi=72,margin=0)


@pytest.mark.parametrize('format',['png','jpeg'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_export_dimensions_dpi_page_order_and_edited_content(format,rotation,crop):
    data=source(rotation,crop)
    ops=[{'type':'textbox','page':0,'points':[[40,120],[230,200]],'text':'Editado','font':'helv','size':14,'align':0,'color':[0,0,0]}]
    result=export_page_images(data,ops,[1,0],dpi=144,format=format,quality=95)
    with ZipFile(BytesIO(result)) as z,f.open(stream=data) as doc:
        assert len(z.namelist())==2 and 'pagina-002' in z.namelist()[0] and 'pagina-001' in z.namelist()[1]
        for name,number in zip(z.namelist(),[1,0]):
            pix=f.Pixmap(z.read(name));page=doc[number]
            assert (pix.width,pix.height)==(int(page.rect.width*2),int(page.rect.height*2))
            assert pix.alpha==0 and pix.xres==pix.yres==144
            if number==0:assert pix.samples!=page.get_pixmap(matrix=f.Matrix(2,2)).samples


@pytest.mark.parametrize('patch',[{'pages':[]},{'pages':[0,0]},{'pages':[2]},{'pages':[True]},{'pages':[[0]]},
    {'dpi':True},{'dpi':71},{'dpi':601},{'format':'webp'},{'format':[]},{'quality':49},{'quality':101}])
def test_bad_export_parameters_are_rejected(patch):
    with pytest.raises(DocumentError):export_page_images(**{'data':source(),'operations':[],'pages':[0],**patch})


def test_resolution_limits_fail_explicitly_instead_of_downsampling():
    with f.open() as doc:
        doc.new_page(width=3000,height=3000);data=doc.tobytes()
    with pytest.raises(DocumentError,match='Reduce'):export_page_images(data,[],[0],dpi=300)
    with f.open() as doc:
        for _ in range(15):doc.new_page(width=3000,height=3000)
        data=doc.tobytes()
    with pytest.raises(DocumentError,match='lote'):export_page_images(data,[],list(range(15)),dpi=72)


def test_copy_permission_required_even_if_printing_is_permitted():
    with f.open(stream=source()) as doc:data=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT|f.PDF_PERM_PRINT_HQ)
    with pytest.raises(DocumentError,match='extraer'):export_page_images(data,[],[0])


def test_http_creation_export_download_and_invalid_input_do_not_replace_original():
    with TestClient(app) as c:
        r=c.post('/api/create/images',files=[('files',('one.png',image(),'image/png')),('files',('two.jpg',image(80,40,'jpeg'),'image/jpeg'))],data={'paper':'image','dpi':150,'margin':0})
        assert r.status_code==200 and len(r.json()['pages'])==2;docid=r.json()['id']
        r=c.post(f'/api/documents/{docid}/export-images',json={'pages':[1,0],'dpi':150,'format':'jpeg'});assert r.status_code==200
        with ZipFile(BytesIO(r.content)) as z:assert len(z.namelist())==2 and all(name.endswith('.jpg') for name in z.namelist())
        assert c.post('/api/create/images',files={'files':('bad.png',b'bad')}).status_code==422
        assert c.get(f'/api/documents/{docid}/pages/1').status_code==200
