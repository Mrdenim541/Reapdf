from io import BytesIO
import xml.etree.ElementTree as E
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import xfdf,working_copy
from backend.engine import DocumentError,export_pdf
from backend.digital_signatures import sign_document,verify_signatures
from tests.signature_samples import identity,document


def source(rotation=0,crop=False,annots=True):
    with f.open() as doc:
        p=doc.new_page(width=600,height=800);p.insert_text((40,80),'Original text')
        w=f.Widget();w.field_name='Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(40,250,260,280);w.text_font='Helv';w.text_fontsize=12;w.field_value='Original';p.add_widget(w)
        w=f.Widget();w.field_name='Aceptar';w.field_type=f.PDF_WIDGET_TYPE_CHECKBOX;w.rect=f.Rect(300,250,320,270);p.add_widget(w)
        if annots:
            p.add_text_annot((40,100),'Nota');p.add_rect_annot(f.Rect(100,100,180,180));p.add_circle_annot(f.Rect(200,100,250,160));p.add_line_annot((40,200),(200,200));p.add_ink_annot([[[350,100],[390,120],[380,160]]]);p.add_highlight_annot(p.search_for('Original'))
        if crop:p.set_cropbox(f.Rect(20,20,580,780))
        p.set_rotation(rotation);doc.new_page().insert_text((40,80),'Other page');return doc.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_xfdf_export_dedup_fields_and_geometry_import(rotation,crop):
    base=source(rotation,crop);data,report=xfdf.export(base,[]);assert report['annotations']==6 and report['fields']==2
    preview=xfdf.import_data(base,[],data,preview=True);assert preview=={'annotations':0,'duplicates':6,'fields':2}
    target=source(rotation,crop,annots=False)
    with pytest.raises(DocumentError,match='otro origen'):xfdf.import_data(target,[],data)
    out,report=xfdf.import_data(target,[],data,confirm=True);assert report['annotations']==6
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_text()==b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].rotation==rotation and b[0].cropbox==a[0].cropbox
        assert sorted(v.type[0] for v in a[0].annots())==sorted(v.type[0] for v in b[0].annots())
    again=xfdf.import_data(out,[],data,confirm=True,preview=True);assert again['annotations']==0 and again['duplicates']==6


def test_field_values_apply_in_snapshot_with_names_checkbox_and_unknown_field_rejection():
    base=source();data,_=xfdf.export(base,[]);root=E.fromstring(data)
    for node in root.findall('./'+xfdf.tag('fields')+'/'+xfdf.tag('field')):
        if node.get('name')=='Nombre':node.find(xfdf.tag('value')).text='Actualizado'
        if node.get('name')=='Aceptar':node.find(xfdf.tag('value')).text='Yes'
    modified=E.tostring(root);out,report=xfdf.import_data(base,[],modified)
    with f.open(stream=out) as doc:
        values={w.field_name:w.field_value for p in doc for w in p.widgets() or []};assert values['Nombre']=='Actualizado' and values['Aceptar']=='Yes'
    node=root.find('./'+xfdf.tag('fields')+'/'+xfdf.tag('field'));node.set('name','Does not exist')
    with pytest.raises(DocumentError):xfdf.import_data(base,[],E.tostring(root))


@pytest.mark.parametrize('kind',['dtd','entity','utf16','badpage','badcoords','unknown','conflict','richtext'])
def test_xfdf_rejects_untrusted_or_incompatible_content_without_partial_import(kind):
    base=source();data,_=xfdf.export(base,[])
    if kind in ['dtd','entity']:
        raw=b'<!DOCTYPE xfdf [<!ENTITY x "bad">]>'+data if kind=='entity' else b'<!DOCTYPE xfdf>'+data
    elif kind=='utf16':raw=data.decode().encode('utf-16')
    else:
        root=E.fromstring(data);node=root.find('./'+xfdf.tag('annots')+'/*')
        if kind=='badpage':node.set('page','99')
        if kind=='badcoords':node.set('rect','NaN,1,2,3')
        if kind=='unknown':node.tag=xfdf.tag('screen')
        if kind=='conflict':node.find(xfdf.tag('contents')).text='Changed original content'
        if kind=='richtext':E.SubElement(node,xfdf.tag('contents-richtext')).text='<script>bad</script>'
        raw=E.tostring(root)
    with pytest.raises(DocumentError):xfdf.import_data(base,[],raw,confirm=True)
    with f.open(stream=base) as doc:assert len(list(doc[0].annots()))==6


def signed():
    p12,_,_=identity();return sign_document(document(),[],p12,'prueba',{'visible':True,'page':0,'box':[40,350,320,90]})


def test_unsigned_working_copy_preserves_original_valid_signature_and_can_be_edited():
    base=signed();copy,report=working_copy.create(base,True)
    assert report['original_untouched'] and not report['digital_signatures_retained'] and report['signature_widgets']==1
    assert verify_signatures(base,[])['signatures'][0]['intact'] and verify_signatures(copy,[])['count']==0
    with f.open(stream=copy) as doc:
        assert doc.get_sigflags()<=0 and all(working_copy.LABEL in p.get_text() for p in doc)
        assert all(not list(p.widgets() or []) for p in doc)
        assert 'María Pérez' in doc[0].get_text() # appearance, explicitly unsigned copy
    edited=export_pdf(copy,[{'type':'note','page':0,'point':[30,30],'content':'Editable copy','color':[1,0,0]}])
    with f.open(stream=edited) as doc:assert any(a.info['content']=='Editable copy' for a in doc[0].annots())
    with pytest.raises(DocumentError):working_copy.create(base)
    with pytest.raises(DocumentError):working_copy.create(source(),True)


def test_api_xfdf_preview_apply_and_copy_requires_explicit_ack(tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path))
    with TestClient(app) as client:
        base=source();doc=client.post('/api/documents',files={'file':('form.pdf',base)}).json();url='/api/documents/'+doc['id']
        response=client.post(url+'/xfdf/export',json={});assert response.status_code==200,response.text
        preview=client.post(url+'/xfdf/import',json={'xml':response.content.decode(),'preview':True});assert preview.status_code==200 and preview.json()['duplicates']==6
        original=signed();doc=client.post('/api/documents',files={'file':('signed.pdf',original)}).json();url='/api/documents/'+doc['id']
        assert client.post(url+'/working-copy',json={}).status_code==422
        result=client.post(url+'/working-copy',json={'acknowledge':True});assert result.status_code==200,result.text
        assert not result.json()['signed'] and result.json()['working_copy']
        preserved=client.post(url+'/export',json={});assert preserved.content==original
