import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf,DocumentError
from backend.content_tools import safe_web_url,page_links
from backend.viewer import text_items,search_document
from backend.review import review_words
from backend.projects import build_project,read_project
from backend.pages import organize_pdf


def source(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=400,height=500);p.insert_text((30,40),'Original conservado')
        if crop:p.set_cropbox(f.Rect(20,20,380,480))
        p.set_rotation(rotation);d.new_page().insert_text((30,40),'Destino');return d.tobytes()


def textbox(**changes):
    return {'type':'textbox','id':'box','page':0,'points':[[40,90],[280,180]],'text':'Texto nuevo\nSegunda linea','font':'helv','size':14,'align':0,'color':[.2,.3,.6],**changes}


def link(**changes):
    return {'type':'link','id':'link','page':0,'points':[[40,220],[180,250]],'destination':'page','target_page':1,**changes}


def stamp(**changes):
    return {'type':'stamp','id':'stamp','page':0,'points':[[40,270],[240,330]],'stamp':'approved','color':[0,.5,0],**changes}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_text_is_visible_searchable_selectable_in_correct_box_with_crop_and_rotation(rotation,crop):
    data=source(rotation,crop);out=export_pdf(data,[textbox()])
    with f.open(stream=data) as original,f.open(stream=out) as d:
        p=d[0];assert 'Original conservado' in p.get_text() and 'Texto nuevo' in p.get_text()
        assert original[1].get_pixmap().samples==d[1].get_pixmap().samples
        region=search_document(d,'Texto nuevo')['results'][0]['rect']
        assert 39<=region[0] and region[2]<=281 and 89<=region[1] and region[3]<=181
        item=next(item for item in text_items(p) if item['text']=='Texto nuevo')
        assert item['rotation']==0 and 39<=item['x']<=45 and item['width']>40
        word=next(w for w in review_words(p) if w['text']=='nuevo')
        assert 40<=min(pt[0] for pt in word['quad'])<=280
        # Solo se añade texto vectorial: no se rasteriza la hoja.
        assert not p.get_images()


@pytest.mark.parametrize('font',['helv','hebo','tiro','tibi','cour','cobo'])
def test_base_fonts_alignment_and_size_preserved(font):
    with f.open(stream=export_pdf(source(),[textbox(font=font,size=18,align=2)])) as d:
        s=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='Texto nuevo'][0]
        assert s['size']==18 and s['bbox'][0]>40


@pytest.mark.parametrize('patch',[{'text':''},{'text':'Texto ✓'},{'text':'a\tbad'},{'text':'a'*2001},{'size':True},{'size':5},{'size':145},{'font':'unknown'},{'align':True},{'align':3},{'color':[2,0,0]},{'points':[[40,90],[45,96]]},{'points':[[0,0],[500,500]]},{'points':[[0,0],[float('nan'),100]]}])
def test_invalid_text_or_overflow_never_partially_changes_source(patch):
    data=source()
    with pytest.raises(DocumentError):export_pdf(data,[textbox(**patch)])
    with f.open(stream=data) as d:assert 'Texto nuevo' not in d[0].get_text()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_links_visible_coordinates_and_destinations_match_user_area(rotation,crop):
    data=source(rotation,crop)
    with f.open(stream=export_pdf(data,[link(),link(id='web',points=[[40,300],[200,330]],destination='web',url='https://example.com/a?q=1')])) as d:
        links=page_links(d[0])['links'];assert len(links)==2
        assert links[0]['box']==[40,220,180,250] and links[0]['target_page']==1
        assert links[1]['url']=='https://example.com/a?q=1'
        p=d[0];native=p.get_links();assert native[0]['page']==1 and native[1]['uri']=='https://example.com/a?q=1'


@pytest.mark.parametrize('url',['javascript:alert(1)','file:///etc/passwd','mailto:a@b.com','data:text/plain,x','https://user:password@example.com','https://example.com\nx','https://example.com:0','https://example.com:99999','https://','https://example.com\\a',' https://example.com',None,1])
def test_unsafe_or_unsupported_web_destinations_rejected(url):
    with pytest.raises(DocumentError):safe_web_url(url)


@pytest.mark.parametrize('target',[-1,2,True,'1',None])
def test_invalid_internal_destinations_rejected(target):
    with pytest.raises(DocumentError):export_pdf(source(),[link(target_page=target)])


@pytest.mark.parametrize('choice',['approved','draft','confidential','not_approved'])
def test_standard_stamp_is_native_annotation_with_readable_metadata(choice):
    with f.open(stream=export_pdf(source(crop=True),[stamp(stamp=choice)])) as d:
        p=d[0];a=next(p.annots());assert a.type[0]==f.PDF_ANNOT_STAMP and a.info['title']=='Reapdf'
        assert f.Rect(40,270,240,330).contains(a.rect) and a.rect.width>100
        assert not p.get_images() and 'Original conservado' in p.get_text()


@pytest.mark.parametrize('patch',[{'stamp':'bad'},{'stamp':1},{'points':[[40,270],[60,280]]}])
def test_invalid_stamp_rejected(patch):
    with pytest.raises(DocumentError):export_pdf(source(),[stamp(**patch)])


def test_rotated_stamp_limit_is_explicit():
    with pytest.raises(DocumentError,match='sin giro'):export_pdf(source(90),[stamp()])


def test_permissions_signature_and_project_reopening():
    data=source();ops=[textbox(),link(),stamp()]
    state={'name':'Nuevo.pdf','page':0,'zoom':1,'base_changes':0}
    packed,_=build_project(data,ops,state);base,restored,_=read_project(packed);assert restored==ops
    result=organize_pdf(base,restored,[{'page':1,'rotation':0},{'page':0,'rotation':0}])
    with f.open(stream=result) as d:
        assert 'Texto nuevo' in d[1].get_text() and d[1].get_links()[0]['page']==0
        p=d[1];assert next(p.annots()).type[0]==f.PDF_ANNOT_STAMP
    with f.open(stream=data) as d:
        locked=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_ANNOTATE)
        for op in [textbox(),link()]:
            with pytest.raises(DocumentError):export_pdf(locked,[op])
        assert export_pdf(locked,[stamp()])
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>')
        for op in ops:
            with pytest.raises(DocumentError):export_pdf(d.tobytes(),[op])


def test_api_text_search_link_preview_project_and_export():
    data=source();ops=[textbox(),link(),stamp()]
    with TestClient(app) as c:
        document=c.post('/api/documents',files={'file':('demo.pdf',data)}).json();base=f"/api/documents/{document['id']}"
        response=c.post(base+'/pages/0/text',json={'operations':ops});assert response.status_code==200
        assert any(item['text']=='Texto nuevo' for item in response.json()['items']) and response.json()['links'][0]['target_page']==1
        assert c.post(base+'/search',json={'operations':ops,'query':'nuevo'}).json()['results']
        assert c.post(base+'/pages/0/preview',json={'operations':ops}).status_code==200
        assert c.post(base+'/project',json={'operations':ops,'name':'demo.pdf'}).status_code==200
        assert c.post(base+'/export',json={}).content==data


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_internal_self_link_targets_visible_page_origin_after_rotation(rotation):
    with f.open(stream=export_pdf(source(rotation,crop=True),[link(target_page=0)])) as d:
        native=d[0].get_links()[0]
        assert native['page']==0 and abs(native['to'].x)<.01 and abs(native['to'].y)<.01
