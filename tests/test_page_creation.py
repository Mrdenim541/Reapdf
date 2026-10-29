import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.page_creation import duplicate_pdf,blank_pdf


@pytest.fixture
def source():
    with f.open() as doc:
        for i in range(3):doc.new_page(width=400,height=500).insert_text((30,60),f'Pagina {i+1}')
        doc[0].add_text_annot((40,100),'Comentario')
        w=f.Widget();w.field_name='Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,200,200,230);w.field_value='Dato';doc[0].add_widget(w)
        doc[0].insert_link({'kind':f.LINK_GOTO,'from':f.Rect(30,300,130,320),'page':2,'to':f.Point(20,30)})
        doc[1].set_rotation(90)
        doc.set_toc([[1,'Uno',1],[1,'Tres',3]])
        doc.set_page_labels([{'startpage':0,'prefix':'P-','style':'D','firstpagenum':1}])
        return doc.tobytes()


@pytest.mark.parametrize('position',[0,1,3])
def test_duplicate_keeps_edited_annotations_forms_and_originals(source,position):
    op={'type':'note','page':0,'point':[200,100],'content':'Nueva','color':[1,1,0]}
    output=duplicate_pdf(source,[op],[0,2],position)
    with f.open(stream=output) as doc:
        assert len(doc)==5
        p=doc[position];assert 'Pagina 1' in p.get_text() and len(list(p.annots()))==2
        assert next(p.widgets()).field_value=='Dato'
        original_page=0 if position>0 else 2
        original=doc[original_page];assert len(list(original.annots()))==2
        assert next(original.widgets()).field_name!=next(p.widgets()).field_name
        assert doc[position].get_links()[0]['page']==position+1
        assert [doc[position+i].get_label() for i in range(2)]==['P-1','P-3']
    with f.open(stream=source) as doc:assert len(doc)==3 and len(list(doc[0].annots()))==1


@pytest.mark.parametrize('position',[0,1,3])
def test_blank_insert_preserves_navigation_form_and_dimensions(source,position):
    output=blank_pdf(source,[],position,2,612,792)
    with f.open(stream=output) as doc:
        assert len(doc)==5
        for index in [position,position+1]:
            p=doc[index];assert (p.rect.width,p.rect.height)==(612,792) and not p.get_text() and not p.get_images()
        origin=0 if position>0 else 2;p=doc[origin]
        assert next(p.widgets()).field_value=='Dato'
        assert p.get_links()[0]['page']==(2 if position==3 else 4)
        assert doc.get_toc()[0][2]==origin+1
        assert p.get_label()=='P-1'


@pytest.mark.parametrize('pages,position',[([],0),([True],0),([3],0),([0,0],1),([0],-1),([0],4),([0],True)])
def test_invalid_duplicate_plan(source,pages,position):
    with pytest.raises(DocumentError):duplicate_pdf(source,[],pages,position)


@pytest.mark.parametrize('count,width,height',[(0,400,500),(True,400,500),(498,400,500),(1,0,500),(1,400,3001),(1,float('nan'),500),(1,True,500)])
def test_invalid_blank_plan(source,count,width,height):
    with pytest.raises(DocumentError):blank_pdf(source,[],0,count,width,height)


def test_signed_and_restricted_documents_rejected(source):
    with f.open(stream=source) as doc:
        restricted=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm/SigFlags','3');signed=doc.tobytes()
    for data in [restricted,signed]:
        with pytest.raises(DocumentError):duplicate_pdf(data,[],[0],1)
        with pytest.raises(DocumentError):blank_pdf(data,[],1,1,400,500)


def test_api_creation_reversible_snapshots_and_print_permissions(source):
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('demo.pdf',source)}).json();url=f"/api/documents/{doc['id']}"
        assert doc['can_print']
        duplicated=c.post(url+'/duplicate',json={'pages':[0],'position':1});assert duplicated.status_code==200
        assert len(duplicated.json()['pages'])==4
        blank=c.post(url+'/blank',json={'position':0,'count':1,'width':595,'height':842});assert blank.status_code==200
        assert len(blank.json()['pages'])==4
        op={'type':'note','page':0,'point':[200,100],'content':'Para imprimir','color':[1,1,0]}
        printed=c.post(url+'/print',json={'operations':[op]});assert printed.status_code==200
        assert printed.headers['content-disposition'].startswith('inline') and printed.headers['cache-control']=='no-store'
        with f.open(stream=printed.content) as d:
            p=d[0];assert len(list(p.annots()))==2 and 'Pagina 1' in p.get_text()
        assert c.post(url+'/export',json={}).content==source
        for permissions in [0,f.PDF_PERM_COPY,f.PDF_PERM_PRINT]:
            with f.open(stream=source) as d:locked=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=permissions)
            doc=c.post('/api/documents',files={'file':('locked.pdf',locked)}).json()
            assert not doc['can_print']
            assert c.post(f"/api/documents/{doc['id']}/print",json={}).status_code==403
