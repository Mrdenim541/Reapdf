import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, export_pdf
from backend.bookmarks import bookmark_model
from backend.headers import SLOTS
from backend.projects import build_project, read_project, RecoveryStore
from backend.pages import organize_pdf
from backend.viewer import search_document


def source(rotation=0,crop=False):
    with f.open() as d:
        for i in range(3):
            p=d.new_page(width=595,height=842);p.insert_text((70,180),f'Original {i+1}')
            if crop:p.set_cropbox(f.Rect(20,30,575,812))
            p.set_rotation(rotation)
        d.set_toc([[1,'Inicio',1],[2,'Detalle',2],[1,'Final',3]])
        return d.tobytes()


def bookmarks(**patch):
    return {'type':'bookmarks','page':0,'items':[
        {'level':1,'title':'Resumen 日本語','page':1,'to':[40,90],'zoom':1.5,'bold':True,'italic':True,'color':[.2,.4,.6],'collapse':True},
        {'level':2,'title':'Hijo','page':0},
        {'level':1,'title':'Cierre','page':2}],**patch}


def headers(**patch):
    return {'type':'header_footer','page':0,'pages':[0,1,2],
            'slots':{**dict.fromkeys(SLOTS,''),'top_left':'Informe','bottom_center':'Pág. {numero} / {total}'},
            'font':'helv','size':10,'color':[.2,.3,.4],'margins':[20,24,20,24],'start':1,'style':'D','padding':0,**patch}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_bookmark_roundtrip_keeps_point_styles_hierarchy_and_page_pixels(rotation,crop):
    data=source(rotation,crop)
    with f.open(stream=data) as original,f.open(stream=export_pdf(data,[bookmarks()])) as d:
        model=bookmark_model(d);assert model['editable']
        item=model['items'][0];assert item['title']=='Resumen 日本語' and item['page']==1
        assert item['to']==pytest.approx([40,90]) and item['zoom']==pytest.approx(1.5)
        assert item['bold'] and item['italic'] and item['collapse'] and item['color']==pytest.approx([.2,.4,.6])
        assert [i['level'] for i in model['items']]==[1,2,1]
        for a,b in zip(original,d):assert a.get_pixmap().samples==b.get_pixmap().samples
        # The editor sends back exactly these coordinates, including rotated/cropped targets.
        again=export_pdf(d.tobytes(),[{'type':'bookmarks','page':0,'items':model['items']}])
    with f.open(stream=again) as d:assert bookmark_model(d)['items'][0]['to']==pytest.approx([40,90])


def test_empty_index_removes_all_and_source_unchanged():
    data=source()
    with f.open(stream=export_pdf(data,[bookmarks(items=[])])) as d:assert d.get_toc()==[]
    with f.open(stream=data) as d:assert len(d.get_toc())==3


@pytest.mark.parametrize('patch',[
    {'level':0},{'level':2},{'level':True},{'title':''},{'title':'x'*301},{'title':'a\nb'},
    {'page':-1},{'page':3},{'page':True},{'to':[0]},{'to':[0,float('nan')]},{'zoom':True},{'zoom':65},
    {'color':[1,2,0]},{'color':[0,0]},{'bold':1},{'collapse':'yes'}])
def test_bad_bookmark_rejected(patch):
    op=bookmarks();op['items'][0].update(patch)
    with pytest.raises(DocumentError):export_pdf(source(),[op])


@pytest.mark.parametrize('items',[None,{},[None],[],[{'level':1,'title':'Valid','page':0}]*2001])
def test_bookmark_list_limits(items):
    if items==[]:
        with f.open(stream=export_pdf(source(),[bookmarks(items=items)])) as d:assert not d.get_toc()
    else:
        with pytest.raises(DocumentError):export_pdf(source(),[bookmarks(items=items)])


def test_special_outline_actions_are_read_only_and_preserved():
    with f.open(stream=source()) as d:
        d.set_toc([[1,'Web',-1,{'kind':f.LINK_URI,'uri':'https://example.com'}]])
        data=d.tobytes();model=bookmark_model(d)
        assert not model['editable'] and 'especiales' in model['reason']
    with pytest.raises(DocumentError,match='especiales'):export_pdf(data,[bookmarks(items=[])])
    with f.open(stream=export_pdf(data,[headers()])) as d:assert d.get_toc(False)[0][3]['uri']=='https://example.com'


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_headers_all_slots_are_vector_text_in_visible_margin_with_crop_and_rotation(rotation,crop):
    slots={key:f'{i+1} numero {{numero}}' for i,key in enumerate(SLOTS)}
    data=source(rotation,crop)
    with f.open(stream=export_pdf(data,[headers(slots=slots)])) as d:
        for number,p in enumerate(d):
            assert f'Original {number+1}' in p.get_text() and not p.get_images()
            for index in range(6):
                text=f'{index+1} numero {number+1}'
                result=next(r for r in search_document(d,text)['results'] if r['page']==number)
                x0,y0,x1,y1=result['rect'];assert 20<=x0<x1<=p.rect.width-20
                if index<3:assert 19<=y0<y1<65
                else:assert p.rect.height-65<y0<y1<=p.rect.height-19


@pytest.mark.parametrize('style,start,padding,expected',[('D',7,3,['007','008']),('R',9,0,['IX','X']),('r',39,0,['xxxix','xl'])])
def test_selected_page_order_sequence_page_position_and_total_are_independent(style,start,padding,expected):
    slots={**dict.fromkeys(SLOTS,''),'bottom_center':'{numero}:{pagina}:{total}'}
    with f.open(stream=export_pdf(source(),[headers(pages=[2,0],slots=slots,style=style,start=start,padding=padding)])) as d:
        assert f'{expected[0]}:3:3' in d[2].get_text() and f'{expected[1]}:1:3' in d[0].get_text()
        assert d[1].get_text().strip()=='Original 2'


@pytest.mark.parametrize('patch',[
    {'pages':[]},{'pages':[0,0]},{'pages':[True]},{'pages':[3]},{'pages':[[0]]},
    {'slots':{}},{'slots':dict.fromkeys(SLOTS,'')},
    *[{'slots':{**dict.fromkeys(SLOTS,''),'top_left':text}} for text in ['x'*201,'a\nb','✓','{bad}','{{numero}}','{numero','numero}','{}']],
    {'font':[]},{'font':'bad'},{'size':True},{'size':5},{'size':37},{'color':[0,2,0]},
    {'margins':[0]},{'margins':[0,0,-1,0]},{'margins':[500,500,500,500]},
    {'start':0},{'start':True},{'start':999999},{'style':[]},{'style':'bad'},{'padding':9},
    {'style':'R','start':3998},
    {'slots':{**dict.fromkeys(SLOTS,''),'top_left':'Texto demasiado largo para un tercio de la página '*3}}])
def test_bad_header_settings_rejected_before_any_modification(patch):
    data=source()
    with pytest.raises(DocumentError):export_pdf(data,[headers(**patch)])
    with f.open(stream=data) as d:assert d[0].get_text().strip()=='Original 1'


@pytest.mark.parametrize('op',[bookmarks(),headers()])
def test_single_config_permissions_and_signed_documents(op):
    with pytest.raises(DocumentError,match='consolidada'):export_pdf(source(),[op,op])
    with f.open(stream=source()) as d:
        restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');signed=d.tobytes()
    with pytest.raises(DocumentError,match='permite'):export_pdf(restricted,[op])
    with pytest.raises(DocumentError,match='firmados'):export_pdf(signed,[op])


def test_project_checkpoint_reopen_and_page_snapshot_preserve_document_tools(tmp_path):
    data=source();ops=[bookmarks(),headers(start=5,padding=3)]
    packed,_=build_project(data,ops,{'name':'Prueba.pdf','page':0,'zoom':1,'base_changes':0})
    store=RecoveryStore(tmp_path);revision=store.save(packed,None)
    base,restored,manifest=store.read(revision);assert base==data and restored==ops
    result=organize_pdf(base,restored,[{'page':2,'rotation':0},{'page':1,'rotation':0},{'page':0,'rotation':0}])
    with f.open(stream=result) as d:
        assert '007 / 3' in d[0].get_text() and '005 / 3' in d[2].get_text()
        assert d.get_toc()[0][:3]==[1,'Resumen 日本語',2] and d.get_toc()[-1][:3]==[1,'Cierre',1]
    # Replacing the session configuration regenerates from the original, without duplicated text.
    with f.open(stream=export_pdf(base,[restored[0],headers(start=10)])) as d:
        assert '10 / 3' in d[0].get_text() and '005 / 3' not in d[0].get_text()


def test_api_reads_current_index_without_mutating_base_and_prints_current_headers():
    with TestClient(app) as c:
        data=source();r=c.post('/api/documents',files={'file':('tools.pdf',data,'application/pdf')});assert r.status_code==200
        document=r.json()['id'];url=f'/api/documents/{document}';ops=[bookmarks(),headers()]
        r=c.post(url+'/bookmarks',json={'operations':ops});assert r.status_code==200 and r.json()['items'][0]['title']=='Resumen 日本語'
        assert c.post(url+'/bookmarks',json={}).json()['items'][0]['title']=='Inicio'
        r=c.post(url+'/print',json={'operations':ops});assert r.status_code==200
        with f.open(stream=r.content) as d:assert '1 / 3' in d[0].get_text() and d.get_toc()[0][1]=='Resumen 日本語'
        r=c.post(url+'/pages/0/preview',json={'operations':[headers(size=36,slots={**dict.fromkeys(SLOTS,''),'top_left':'Un encabezado que claramente no cabe en esta columna'})],'scale':1})
        assert r.status_code==422  # A long footer must fail visibly rather than silently disappear.


@pytest.mark.parametrize('destination',['/Fit','/FitH 700','/XYZ null 700 0'])
def test_special_destination_modes_are_not_silently_converted(destination):
    with f.open(stream=source()) as d:
        d.xref_set_key(d.get_outline_xrefs()[0],'A',f'<</S/GoTo/D[{d.page_xref(0)} 0 R {destination}]>>')
        assert not bookmark_model(d)['editable']
        with pytest.raises(DocumentError,match='especiales'):export_pdf(d.tobytes(),[bookmarks(items=[])])


def test_chained_outline_actions_are_read_only():
    with f.open(stream=source()) as d:
        d.xref_set_key(d.get_outline_xrefs()[0],'A/Next','<</S/URI/URI(https://example.com)>>')
        assert not bookmark_model(d)['editable']


@pytest.mark.parametrize('font',['helv','hebo','heit','hebi','tiro','tibo','tiit','tibi','cour','cobo','coit','cobi'])
def test_all_twelve_base_fonts_support_header_alignment(font):
    op=headers(font=font,slots={key:'Margen' for key in SLOTS})
    with f.open(stream=export_pdf(source(crop=True),[op])) as d:
        assert d[0].get_text().count('Margen')==6
