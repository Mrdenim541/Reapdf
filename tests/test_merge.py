import hashlib
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, spans
from backend.merge import merge_pdf


def make_document(prefix, *, widgets=False):
    with fitz.open() as doc:
        for number in range(3):
            p=doc.new_page(width=400,height=500)
            p.draw_rect(fitz.Rect(30,40,280,110),fill=(.9,.9,.9),color=None)
            p.insert_text((40,80),f'{prefix} pagina {number+1}',fontsize=16)
        doc[0].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,120,170,140),'page':2,'to':fitz.Point(50,80)})
        doc[1].insert_link({'kind':fitz.LINK_GOTO,'from':fitz.Rect(40,120,170,140),'page':0,'to':fitz.Point(40,80)})
        doc[0].insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(40,150,170,170),'uri':'https://example.com'})
        doc[0].add_text_annot((40,200),f'Nota {prefix}')
        doc[2].set_rotation(90)
        doc.set_toc([[1,f'{prefix} inicio',1],[2,f'{prefix} detalle',3]])
        doc.set_page_labels([{'startpage':0,'prefix':f'{prefix}-','style':'D','firstpagenum':1}])
        if widgets:
            w=fitz.Widget();w.field_name='Nombre';w.field_type=fitz.PDF_WIDGET_TYPE_TEXT
            w.field_value=prefix;w.rect=fitz.Rect(40,250,200,280);doc[0].add_widget(w)
        return doc.tobytes()

@pytest.fixture
def base():return make_document('Base')

@pytest.fixture
def incoming():return make_document('Extra')

@pytest.mark.parametrize('position',[0,1,3])
def test_insert_preserves_content_labels_and_remaps_both_link_sets(base,incoming,position):
    base_hash=hashlib.sha256(base).hexdigest();incoming_hash=hashlib.sha256(incoming).hexdigest()
    result=merge_pdf(base,[],incoming,[0,1,2],position,'Archivo extra')
    with fitz.open(stream=base,filetype='pdf') as old, fitz.open(stream=incoming,filetype='pdf') as other, fitz.open(stream=result,filetype='pdf') as doc:
        assert len(doc)==6
        def shifted(index):return index+3 if index>=position else index
        for index in range(3):
            assert doc[shifted(index)].get_pixmap().samples==old[index].get_pixmap().samples
            assert doc[position+index].get_pixmap().samples==other[index].get_pixmap().samples
            assert doc[position+index].get_label()==f'Extra-{index+1}'
            assert doc[shifted(index)].get_label()==f'Base-{index+1}'
        base_link=next(link for link in doc[shifted(0)].get_links() if link['kind']==fitz.LINK_GOTO)
        assert base_link['page']==shifted(2)
        assert base_link['to']==next(link for link in old[0].get_links() if link['kind']==fitz.LINK_GOTO)['to']
        source_link=next(link for link in doc[position].get_links() if link['kind']==fitz.LINK_GOTO)
        assert source_link['page']==position+2
        assert source_link['to']==next(link for link in other[0].get_links() if link['kind']==fitz.LINK_GOTO)['to']
        assert any(link.get('uri')=='https://example.com' for link in doc[position].get_links())
        assert doc.get_toc()==[[1,'Base inicio',shifted(0)+1],[2,'Base detalle',shifted(2)+1],
                              [1,'Archivo extra',position+1],[2,'Extra inicio',position+1],[3,'Extra detalle',position+3]]
    assert hashlib.sha256(base).hexdigest()==base_hash and hashlib.sha256(incoming).hexdigest()==incoming_hash


def test_subset_order_filters_destinations_and_preserves_current_edits(base,incoming):
    with fitz.open(stream=base,filetype='pdf') as doc:span=spans(doc[0])[0]
    op={'type':'text','page':0,'span_id':span['id'],'text':'Base editada'}
    result=merge_pdf(base,[op],incoming,[1,0],1)
    with fitz.open(stream=result,filetype='pdf') as doc:
        assert len(doc)==5 and 'Base editada' in doc[0].get_text()
        assert 'Extra pagina 2' in doc[1].get_text() and 'Extra pagina 1' in doc[2].get_text()
        assert doc[1].get_links()[0]['page']==2
        # La página de destino 3 de Extra no fue importada: no dejar enlace roto.
        assert all(link['kind']!=fitz.LINK_GOTO for link in doc[2].get_links())
        assert [p.get_label() for p in doc]==['Base-1','Extra-2','Extra-1','Base-2','Base-3']


def test_duplicate_form_names_remain_independent():
    base=make_document('Base',widgets=True);incoming=make_document('Extra',widgets=True)
    result=merge_pdf(base,[],incoming,[0],1)
    with fitz.open(stream=result,filetype='pdf') as doc:
        fields=[(w.field_name,w.field_value) for p in doc for w in p.widgets() or []]
        assert len(fields)==2 and len(set(name for name,_ in fields))==2
        assert set(value for _,value in fields)=={'Base','Extra'}
        p=doc[1];w=next(p.widgets());w.field_value='Solo extra';w.update()
        saved=doc.tobytes()
    with fitz.open(stream=saved,filetype='pdf') as doc:
        p=doc[0];assert next(p.widgets()).field_value=='Base'
        p=doc[1];assert next(p.widgets()).field_value=='Solo extra'

@pytest.mark.parametrize('selection,position',[([],0),([True],0),([0,0],0),([-1],0),([3],0),([0],True),([0],-1),([0],4),('1-3',0)])
def test_invalid_insertion_rejected(base,incoming,selection,position):
    with pytest.raises(DocumentError):merge_pdf(base,[],incoming,selection,position)


def test_page_limit(base):
    with fitz.open() as doc:
        for _ in range(500):doc.new_page()
        incoming=doc.tobytes()
    with pytest.raises(DocumentError,match='500'):merge_pdf(base,[],incoming,list(range(500)),0)


def test_source_with_layers_or_scripts_is_rejected(base):
    with fitz.open(stream=make_document('Extra',widgets=True),filetype='pdf') as doc:
        p=doc[0];w=next(p.widgets());w.script_calc='event.value = 42;';w.update();scripted=doc.tobytes()
    with pytest.raises(DocumentError,match='scripts'):merge_pdf(base,[],scripted,[0],0)
    with fitz.open() as doc:
        doc.new_page();doc.add_ocg('Capa');layered=doc.tobytes()
    with pytest.raises(DocumentError,match='capas'):merge_pdf(base,[],layered,[0],0)


def test_signed_and_copy_restricted_sources_rejected(base,incoming):
    with fitz.open(stream=incoming,filetype='pdf') as doc:
        locked=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=fitz.PDF_PERM_PRINT)
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>');signed=doc.tobytes()
    for source in [locked,signed]:
        with pytest.raises(DocumentError):merge_pdf(base,[],source,[0],0)


def test_api_keeps_inputs_available_for_undo(base,incoming):
    with TestClient(app) as client:
        a=client.post('/api/documents',files={'file':('base.pdf',base)}).json()
        b=client.post('/api/documents',files={'file':('extra.pdf',incoming)}).json()
        path=f"/api/documents/{a['id']}"
        response=client.post(path+'/insert',json={'source_id':b['id'],'pages':[2,0],'position':1,'operations':[],'source_name':'Extra'})
        assert response.status_code==200
        info=response.json();assert info['id'] not in {a['id'],b['id']} and len(info['pages'])==5
        assert client.post(path+'/export',json={'operations':[]}).content==base
        assert client.post(f"/api/documents/{b['id']}/export",json={'operations':[]}).content==incoming
        assert client.post(path+'/insert',json={'source_id':[], 'pages':[0],'position':0}).status_code==422

@pytest.mark.parametrize('rotation',[90,180,270])
def test_rotated_link_origins_and_target_coordinates_are_preserved(base,incoming,rotation):
    with fitz.open(stream=incoming,filetype='pdf') as source:
        source[0].set_rotation(rotation);incoming=source.tobytes()
    result=merge_pdf(base,[],incoming,[0,2],1)
    with fitz.open(stream=incoming,filetype='pdf') as before, fitz.open(stream=result,filetype='pdf') as after:
        original=next(link for link in before[0].get_links() if link['kind']==fitz.LINK_GOTO)
        copied=next(link for link in after[1].get_links() if link['kind']==fitz.LINK_GOTO)
        assert copied['page']==2
        assert tuple(copied['from'])==pytest.approx(tuple(original['from']))
        assert tuple(copied['to'])==pytest.approx(tuple(original['to']))


def test_link_color_and_border_survive_import(base,incoming):
    with fitz.open(stream=incoming,filetype='pdf') as source:
        link=next(link for link in source[0].get_links() if link['kind']==fitz.LINK_URI)
        source.xref_set_key(link['xref'],'C','[1 0 0]')
        source.xref_set_key(link['xref'],'Border','[0 0 2]')
        source.xref_set_key(link['xref'],'H','/I')
        incoming=source.tobytes()
    output=merge_pdf(base,[],incoming,[0,2],0)
    with fitz.open(stream=output,filetype='pdf') as doc:
        link=next(link for link in doc[0].get_links() if link['kind']==fitz.LINK_URI)
        assert doc.xref_get_key(link['xref'],'C')[1]=='[1 0 0]'
        assert doc.xref_get_key(link['xref'],'Border')[1]=='[0 0 2]'
        assert doc.xref_get_key(link['xref'],'H')[1]=='/I'


def test_special_file_links_are_rejected_explicitly(base,incoming):
    with fitz.open(stream=incoming,filetype='pdf') as source:
        source[0].insert_link({'kind':fitz.LINK_LAUNCH,'from':fitz.Rect(40,300,200,320),'file':'another.pdf'})
        incoming=source.tobytes()
    with pytest.raises(DocumentError,match='otro tipo de enlace'):merge_pdf(base,[],incoming,[0],0)


def test_quota_error_keeps_both_sources_unchanged(base,incoming,monkeypatch):
    import importlib
    module=importlib.import_module('backend.app')
    monkeypatch.setattr(module,'MAX_STORE',len(base)+len(incoming)+1)
    with TestClient(app) as client:
        a=client.post('/api/documents',files={'file':('base.pdf',base)}).json()
        b=client.post('/api/documents',files={'file':('extra.pdf',incoming)}).json()
        r=client.post(f"/api/documents/{a['id']}/insert",json={'source_id':b['id'],'pages':[0,1],'position':1,'operations':[]})
        assert r.status_code==413
        assert len(list(app.state.root.glob('*.pdf')))==2
        for info,data in [(a,base),(b,incoming)]:
            assert client.post(f"/api/documents/{info['id']}/export",json={'operations':[]}).content==data


def test_calculation_order_without_visible_script_is_rejected(base):
    with fitz.open(stream=make_document('Extra',widgets=True),filetype='pdf') as doc:
        p=doc[0];xref=next(p.widgets()).xref
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm/CO',f'[{xref} 0 R]')
        incoming=doc.tobytes()
    with pytest.raises(DocumentError,match='cálculos'):merge_pdf(base,[],incoming,[0],0)
