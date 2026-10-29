import hashlib
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, spans, export_pdf
from backend.pages import organize_pdf

@pytest.fixture
def source():
    with fitz.open() as doc:
        for i in range(3):
            p=doc.new_page(width=400+i*20,height=500+i*10)
            p.insert_text((40,80),f'Pagina {i+1} original',fontsize=16)
            p.draw_rect(fitz.Rect(40,120,250,200),color=None,fill=(.8,.9,.8))
        doc.set_toc([[1,'Uno',1],[2,'Dos',2],[1,'Tres',3]])
        doc[0].add_text_annot((100,220),'Nota original')
        doc[0].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,250,180,270),'page':2,'to':fitz.Point(40,80)})
        doc[0].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,280,180,300),'uri':'https://example.com'})
        doc[2].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,250,180,270),'page':1,'to':fitz.Point(40,80)})
        doc.set_page_labels([{'startpage':0,'prefix':'A-','style':'D','firstpagenum':1}])
        doc[2].set_rotation(90)
        return doc.tobytes()


def test_reordering_preserves_render_annotations_links_labels_and_bookmarks(source):
    digest=hashlib.sha256(source).hexdigest()
    plan=[{'page':2,'rotation':90},{'page':0,'rotation':0}]
    result=organize_pdf(source,[],plan)
    with fitz.open(stream=source,filetype='pdf') as before, fitz.open(stream=result,filetype='pdf') as after:
        assert len(after)==2
        assert 'Pagina 3' in after[0].get_text() and 'Pagina 1' in after[1].get_text()
        assert after[0].get_pixmap().samples==before[2].get_pixmap().samples
        # El vínculo a una página eliminada desaparece, sin apuntar a otra por error.
        assert after[0].get_links()==[]
        assert after[1].get_pixmap().samples==before[0].get_pixmap().samples
        assert [after[i].get_label() for i in range(2)]==['A-3','A-1']
        assert after.get_toc()==[[1,'Uno',2],[1,'Tres',1]]
        links=after[1].get_links()
        local=next(link for link in links if link['kind']==fitz.LINK_GOTO)
        old_local=next(link for link in before[0].get_links() if link['kind']==fitz.LINK_GOTO)
        assert local['page']==0 and local['to']==old_local['to']
        assert any(link.get('uri')=='https://example.com' for link in links)
        p=after[1]; assert next(p.annots()).info['content']=='Nota original'
    assert hashlib.sha256(source).hexdigest()==digest

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_rotation_applies_after_existing_edits(source,rotation):
    with fitz.open(stream=source,filetype='pdf') as doc:
        line=spans(doc[0])[0]
    operations=[{'type':'text','page':0,'span_id':line['id'],'text':'Texto nuevo'},
                {'type':'ink','page':0,'points':[[40,310],[120,340]],'color':[1,0,0],'width':2}]
    edited=export_pdf(source,operations)
    result=organize_pdf(source,operations,[{'page':0,'rotation':rotation}])
    with fitz.open(stream=edited,filetype='pdf') as expected, fitz.open(stream=result,filetype='pdf') as after:
        expected[0].set_rotation(rotation)
        assert after[0].get_pixmap().samples==expected[0].get_pixmap().samples
        assert after[0].rotation==rotation
        assert 'Texto nuevo' in after[0].get_text() and 'original' not in after[0].get_text()
        assert len(list(after[0].annots()))==2

@pytest.mark.parametrize('pages',[None, [], [0], [{'page':True,'rotation':0}], [{'page':0,'rotation':True}],
    [{'page':-1,'rotation':0}], [{'page':3,'rotation':0}], [{'page':0,'rotation':45}],
    [{'page':0}], [{'page':0,'rotation':0},{'page':0,'rotation':90}]])
def test_invalid_plans_are_rejected(source,pages):
    with pytest.raises(DocumentError):organize_pdf(source,[],pages)


def test_extraction_does_not_change_source_and_preserves_widgets(source):
    with fitz.open(stream=source,filetype='pdf') as doc:
        widget=fitz.Widget();widget.field_name='Nombre';widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
        widget.rect=fitz.Rect(40,350,200,380);widget.field_value='Dato conservado'
        doc[0].add_widget(widget);data=doc.tobytes()
    output=organize_pdf(data,[],[{'page':0,'rotation':0}],extract=True)
    with fitz.open(stream=output,filetype='pdf') as doc:
        assert len(doc)==1 and doc.is_form_pdf
        page=doc[0]; assert next(page.widgets()).field_value=='Dato conservado'
    with fitz.open(stream=data,filetype='pdf') as doc:assert len(doc)==3


def test_permissions_and_signature_flags_are_respected(source):
    with fitz.open(stream=source,filetype='pdf') as doc:
        locked=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=fitz.PDF_PERM_PRINT)
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>');signed=doc.tobytes()
    plan=[{'page':0,'rotation':0}]
    for data in [locked,signed]:
        with pytest.raises(DocumentError):organize_pdf(data,[],plan)
        with pytest.raises(DocumentError):organize_pdf(data,[],plan,extract=True)


def test_api_creates_reversible_snapshot_and_extracts_without_changing_it(source):
    with TestClient(app) as client:
        original=client.post('/api/documents',files={'file':('demo.pdf',source)}).json()
        base=f"/api/documents/{original['id']}"
        body={'operations':[],'pages':[{'page':2,'rotation':180},{'page':0,'rotation':0}]}
        response=client.post(base+'/organize',json=body)
        assert response.status_code==200
        new=response.json(); assert new['id']!=original['id']
        assert len(new['pages'])==2 and new['pages'][0]['rotation']==180
        assert new['bookmarks'][0]['page']==1
        assert client.post(base+'/export',json={'operations':[]}).content==source
        result=client.post(f"/api/documents/{new['id']}/extract",json={'operations':[], 'pages':[{'page':1,'rotation':0}]})
        assert result.status_code==200
        with fitz.open(stream=result.content,filetype='pdf') as doc:
            assert len(doc)==1 and 'Pagina 1' in doc[0].get_text()
        assert len(client.post(f"/api/documents/{new['id']}/export",json={'operations':[]}).content)>0
        assert client.post(base+'/organize',json={'pages':[]}).status_code==422


def test_snapshot_quota_failure_does_not_damage_original(source,monkeypatch):
    import importlib
    module=importlib.import_module('backend.app')
    monkeypatch.setattr(module,'MAX_STORE',len(source)+1)
    with TestClient(app) as client:
        original=client.post('/api/documents',files={'file':('demo.pdf',source)})
        assert original.status_code==200
        base=f"/api/documents/{original.json()['id']}"
        result=client.post(base+'/organize',json={'operations':[], 'pages':[{'page':0,'rotation':90}]})
        assert result.status_code==413
        assert client.post(base+'/export',json={'operations':[]}).content==source
        assert len(list(app.state.root.glob('*.pdf')))==1


def test_select_prunes_deleted_form_fields_and_preserves_retained_registration():
    with fitz.open() as doc:
        doc.new_page();doc.new_page()
        for i in range(2):
            w=fitz.Widget();w.field_name=f'Campo{i}';w.field_type=fitz.PDF_WIDGET_TYPE_TEXT
            w.rect=fitz.Rect(30,30,200,60);w.field_value=f'Valor {i}';doc[i].add_widget(w)
        data=doc.tobytes()
    result=organize_pdf(data,[],[{'page':1,'rotation':0}],extract=True)
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert doc.is_form_pdf
        p=doc[0]; fields=list(p.widgets());assert len(fields)==1
        assert fields[0].field_name=='Campo1' and fields[0].field_value=='Valor 1'
        root_fields=doc.xref_get_key(doc.pdf_catalog(),'AcroForm/Fields')[1]
        assert len(root_fields.split(' R'))-1==1
        fields[0].field_value='Modificado';fields[0].update();saved=doc.tobytes()
    with fitz.open(stream=saved,filetype='pdf') as doc:
        p=doc[0];assert next(p.widgets()).field_value=='Modificado'


def test_nested_form_field_tree_is_retained_after_extraction():
    with fitz.open() as doc:
        doc.new_page();doc.new_page();children=[]
        for i in range(2):
            w=fitz.Widget();w.field_name=f'Campo{i}';w.field_type=fitz.PDF_WIDGET_TYPE_TEXT
            w.rect=fitz.Rect(30,30,200,60);w.field_value=f'Valor {i}'
            children.append(doc[i].add_widget(w).xref)
        parent=doc.get_new_xref()
        doc.update_object(parent,'<< /T (Grupo) /Kids ['+' '.join(f'{xref} 0 R' for xref in children)+'] >>')
        for xref in children:doc.xref_set_key(xref,'Parent',f'{parent} 0 R')
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm/Fields',f'[{parent} 0 R]')
        data=doc.tobytes()
    result=organize_pdf(data,[],[{'page':1,'rotation':0}],extract=True)
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert doc.is_form_pdf
        p=doc[0];fields=list(p.widgets())
        assert len(fields)==1 and fields[0].field_name=='Grupo.Campo1'
        assert fields[0].field_value=='Valor 1'
