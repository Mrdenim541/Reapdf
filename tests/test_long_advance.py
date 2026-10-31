from io import BytesIO
from copy import deepcopy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf,DocumentError
from backend.form_data import export_form_data,import_form_data,flatten_form
from backend.document_tools import export_text,metadata_pdf,read_metadata,optimize_pdf,protect_pdf
from backend.ocr import ocr_pdf,ocr_status
from tests.test_forms import source as form_source,operation


def source(rotation=0,crop=False,scan=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((50,170),'REAPDF DOCUMENTO 12345',fontsize=22)
        if scan:
            pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False);d=f.open();p=d.new_page(width=500,height=650);p.insert_image(p.rect,stream=pix.tobytes('png'))
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((30,60),'Otra pagina')
        d.set_toc([[1,'Primera',1],[1,'Otra',2]]);return d.tobytes()


def watermark(**patch):return {'type':'watermark','page':0,'pages':[0],'text':'BORRADOR','size':36,'opacity':.2,'angle':45,'color':[.4,.2,.2],**patch}


def test_form_data_roundtrip_merges_reverts_and_preserves_other_operations():
    data=form_source();op=operation(data,Nombre='Ana',Acepto=True);values=export_form_data(data,[op])
    ops=import_form_data(data,[],values);assert export_form_data(data,ops)==values
    values['fields'][0]['value']='';values['fields'][1]['value']=False
    assert import_form_data(data,ops,values)==[]
    assert data.startswith(b'%PDF')


@pytest.mark.parametrize('patch',[{'source_sha256':'bad'},{'format':'xfdf'},{'version':True},{'fields':[]},{'fields':[{}]}])
def test_wrong_form_data_cannot_change_document(patch):
    data=form_source();payload=export_form_data(data,[]);payload.update(patch)
    with pytest.raises(DocumentError):import_form_data(data,[],payload)


def test_wrong_field_name_type_value_and_duplicate_are_rejected_atomically():
    data=form_source();payload=export_form_data(data,[])
    for key,value in [('name','Other'),('kind','checkbox'),('value','X'*5000)]:
        bad=deepcopy(payload);bad['fields'][0][key]=value
        with pytest.raises(DocumentError):import_form_data(data,[],bad)
    payload['fields'].append(payload['fields'][0])
    with pytest.raises(DocumentError):import_form_data(data,[],payload)


def test_flatten_preserves_pixels_text_and_separate_annotations_with_undo_source():
    data=form_source();ops=[operation(data,Nombre='Ana',Acepto=True,Ciudad='BOG'),{'type':'note','page':0,'point':[400,500],'content':'Conservar','color':[1,1,0]}]
    original=export_pdf(data,ops);out=flatten_form(data,ops)
    with f.open(stream=original) as a,f.open(stream=out) as b:
        for p,q in zip(a,b):assert p.get_pixmap().samples==q.get_pixmap().samples
        p=b[0];assert not list(p.widgets() or []) and len(list(p.annots()))==1 and 'Ana' in p.get_text()
        assert 'Bogotá' in p.get_text()
    with f.open(stream=data) as d:assert len(list(d[0].widgets()))==5


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_ocr_real_adds_searchable_text_without_altering_scan_pixels(rotation,crop):
    data=source(rotation,crop,True);out,report=ocr_pdf(data,[],[0,1],'spa+eng',200)
    assert report['processed']==[0] and report['skipped']==[1] and report['words']>=2
    with f.open(stream=data) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert '12345' in b[0].get_text() and b[0].search_for('12345')
        region=b[0].search_for('12345')[0]
        expected=50+f.get_text_length('REAPDF DOCUMENTO ',fontsize=22)-(20 if crop else 0)
        assert abs(region.x0-expected)<10 and abs(region.y1-(170-(30 if crop else 0)))<10
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and a.get_toc()==b.get_toc()
        # The native scan stream stays byte-identical.
        original=a.extract_image(a[0].get_images()[0][0])['image'];assert any(b.extract_image(i[0])['image']==original for i in b[0].get_images())
    out2,again=ocr_pdf(out,[],[0],'eng',150);assert not again['processed'] and again['skipped']==[0] and out2==out


@pytest.mark.parametrize('patch',[{'pages':[]},{'pages':[0,0]},{'pages':[True]},{'pages':[2]},{'dpi':72},{'dpi':True},{'language':'fra'},{'language':[]}])
def test_invalid_ocr_settings_fail_before_work(patch):
    with pytest.raises(DocumentError):ocr_pdf(**{'base':source(scan=True),'operations':[],'pages':[0],**patch})


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_vector_watermark_keeps_content_page_geometry_and_history_source(rotation,crop):
    data=source(rotation,crop);out=export_pdf(data,[watermark()])
    with f.open(stream=data) as a,f.open(stream=out) as b:
        assert 'BORRADOR' in b[0].get_text() and 'REAPDF' in b[0].get_text()
        assert not b[0].get_images() and b[0].rotation==a[0].rotation
        assert b[0].get_pixmap().samples!=a[0].get_pixmap().samples and b[1].get_pixmap().samples==a[1].get_pixmap().samples
        assert b[0].rect==a[0].rect


@pytest.mark.parametrize('patch',[{'text':''},{'text':'✓'},{'text':'a'*121},{'size':10},{'opacity':1},{'angle':90},{'pages':[0,0]},{'text':'W'*100,'size':144}])
def test_watermark_validation(patch):
    with pytest.raises(DocumentError):export_pdf(source(),[watermark(**patch)])


def test_text_export_in_range_order_and_metadata_optimization_preserve_content():
    data=source();values={'title':'Informe ñ','author':'Ana','subject':'Tema','keywords':'uno,dos','creator':'Reapdf'}
    text=export_text(data,[],[1,0]).decode();assert text.index('Otra pagina')<text.index('REAPDF')
    updated=metadata_pdf(data,[],values,True);assert read_metadata(updated)==values
    optimized,report=optimize_pdf(updated,[]);assert report['after']<=report['before'] and report['saved']>=0
    with f.open(stream=updated) as a,f.open(stream=optimized) as b:
        assert a.metadata==b.metadata and a.get_toc()==b.get_toc()
        assert all(p.get_pixmap().samples==q.get_pixmap().samples for p,q in zip(a,b))


def test_aes256_protection_authentication_and_permissions_source_unchanged():
    data=source();out=protect_pdf(data,[],'read12345','owner12345',False,False)
    with f.open(stream=out) as d:
        assert d.needs_pass and not d.authenticate('wrong') and d.authenticate('read12345')==2
        assert not d.permissions & f.PDF_PERM_COPY and not d.permissions & f.PDF_PERM_PRINT
        assert 'REAPDF' in d[0].get_text() and '256-bit AES' in d.metadata['encryption']
    with f.open(stream=out) as d:assert d.authenticate('owner12345')&4
    with f.open(stream=data) as d:assert not d.needs_pass


def test_signed_and_restricted_modifications_are_blocked():
    with f.open(stream=source()) as d:
        restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');signed=d.tobytes()
    for data in [restricted,signed]:
        for work in [lambda:optimize_pdf(data,[]),lambda:protect_pdf(data,[],'read12345','owner12345'),lambda:export_pdf(data,[watermark()]),lambda:ocr_pdf(data,[],[0])]:
            with pytest.raises(DocumentError):work()


def test_http_tools_roundtrip():
    with TestClient(app) as c:
        data=form_source();docid=c.post('/api/documents',files={'file':('form.pdf',data)}).json()['id'];url=f'/api/documents/{docid}'
        values=c.post(url+'/form-data',json={}).json();assert values['format']=='reapdf-form-data'
        values['fields'][0]['value']='Ana';r=c.post(url+'/import-form-data',json={'data':values});assert r.status_code==200
        ops=r.json()['operations'];assert c.post(url+'/flatten-form',json={'operations':ops}).status_code==200
        assert 'Ana' in c.post(url+'/export-text',json={'operations':ops,'pages':[0]}).text
        assert set(c.get('/api/ocr').json()['languages'])=={'eng','spa'}
        assert c.post(url+'/optimize',json={'operations':ops}).status_code==200


@pytest.mark.parametrize('copy,printing',[(True,True),(False,True),(True,False),(False,False)])
def test_unlock_requires_owner_for_restrictions_and_keeps_original_bytes(copy,printing):
    from backend.document_tools import unlock_pdf,PasswordRequired
    base=source();encrypted=protect_pdf(base,[],'read12345','owner12345',copy,printing)
    for pw in ['', 'wrong']:
        with pytest.raises(PasswordRequired):unlock_pdf(encrypted,pw)
    if copy and printing:
        data,opened=unlock_pdf(encrypted,'read12345');assert opened
    else:
        with pytest.raises(PasswordRequired,match='propietario'):unlock_pdf(encrypted,'read12345')
    data,opened=unlock_pdf(encrypted,'owner12345')
    with f.open(stream=data) as d:assert not d.needs_pass and 'REAPDF' in d[0].get_text()
    with f.open(stream=encrypted) as d:assert d.needs_pass


def test_http_password_challenge_and_authorized_open():
    base=source();encrypted=protect_pdf(base,[],'read12345','owner12345')
    with TestClient(app) as c:
        assert c.post('/api/documents',files={'file':('secret.pdf',encrypted)}).status_code==401
        r=c.post('/api/documents',files={'file':('secret.pdf',encrypted)},data={'password':'read12345'})
        assert r.status_code==200 and r.json()['opened_encrypted']


@pytest.mark.parametrize('kind',['text','multiline','checkbox','choice'])
def test_create_fill_delete_field_as_real_acroform(kind):
    from backend.form_design import create_field,delete_field
    from backend.forms import form_model
    base=source();out=create_field(base,[],{'name':'Nuevo','kind':kind,'page':0,'box':[30,300,200,60],'options':['Uno','Dos']})
    with f.open(stream=out) as d:
        row=form_model(d)['fields'][0];assert row['name']=='Nuevo' and row['editable']
    value=True if kind=='checkbox' else 'Uno' if kind=='choice' else 'Rellenado'
    op={'type':'form_fill','page':0,'values':[{'page':0,'xref':row['xref'],'value':value}]}
    with f.open(stream=export_pdf(out,[op])) as d:assert form_model(d)['fields'][0]['value']==value
    removed=delete_field(out,[op],0,row['xref'])
    with f.open(stream=removed) as d:assert form_model(d)['fields']==[] and 'REAPDF' in d[0].get_text()


@pytest.mark.parametrize('patch',[{'name':''},{'kind':'radio'},{'box':[0,0,2,2]},{'box':[400,600,200,100]},{'kind':'choice','options':['A','A']},{'page':True}])
def test_create_field_invalid_geometry_names_types(patch):
    from backend.form_design import create_field
    with pytest.raises(DocumentError):create_field(source(),[],{'name':'Nuevo','kind':'text','page':0,'box':[30,300,200,60],**patch})


def test_compare_identical_text_visual_and_added_pages():
    from backend.comparison import compare_pdf
    base=source();assert compare_pdf(base,[],base)['changed_pages']==0
    changed=export_pdf(base,[watermark()]);report=compare_pdf(base,[],changed)
    assert report['changed_pages']==1 and report['changes'][0]['visual_changed'] and report['changes'][0]['text_changed']
    assert any('BORRADOR' in line for line in report['changes'][0]['diff'])
    with f.open(stream=base) as d:d.new_page();more=d.tobytes()
    report=compare_pdf(base,[],more);assert report['changes'][-1]['missing_current'] and report['reference_pages']==3


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_existing_image_move_replace_delete_preserve_pixels_and_other_content(rotation,crop):
    from backend.image_editing import image_model,edit_image
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,80,40),False);pix.clear_with(150);jpeg=pix.tobytes('jpeg')
    with f.open() as doc:
        p=doc.new_page(width=500,height=650);p.insert_text((30,45),'Conservar');p.insert_image(f.Rect(100,100,260,180),stream=jpeg)
        if crop:p.set_cropbox(f.Rect(20,20,480,630))
        p.set_rotation(rotation);doc.new_page();base=doc.tobytes();row=image_model(doc,0)['images'][0];assert row['editable']
    box=[40,300,100,80]
    moved=edit_image(base,[],0,row['xref'],'move',box)
    with f.open(stream=moved) as d:
        item=next(i for i in d[0].get_image_info(xrefs=True) if i['width']==80)
        assert d.extract_image(item['xref'])['image']==jpeg
        visible=f.Rect(item['bbox'])*d[0].rotation_matrix;assert list(visible)==pytest.approx([40,300,140,380])
        assert 'Conservar' in d[0].get_text()
    deleted=edit_image(base,[],0,row['xref'],'delete')
    with f.open(stream=deleted) as d:assert not any(i['width']==80 for i in d[0].get_image_info()) and 'Conservar' in d[0].get_text()
    import base64
    replacement=base64.b64encode(pix.tobytes('png')).decode()
    replaced=edit_image(base,[],0,row['xref'],'replace',data=replacement)
    with f.open(stream=replaced) as d:assert any(i['width']==80 for i in d[0].get_image_info())


def test_shared_images_require_an_explicit_occurrence():
    from backend.image_editing import image_model,edit_image
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,20,20),False);pix.clear_with(150)
    with f.open() as d:
        p=d.new_page();xref=p.insert_image(f.Rect(30,30,100,100),stream=pix.tobytes('png'));p.insert_image(f.Rect(130,30,200,100),xref=xref)
        rows=image_model(d,0)['images'];assert all(r['editable'] for r in rows);base=d.tobytes()
    with pytest.raises(DocumentError,match='comparte'):edit_image(base,[],0,xref,'delete')


def test_existing_alpha_image_preserves_mask_and_applied_edits():
    from backend.image_editing import image_model,edit_image
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,40,30),True);pix.clear_with(140)
    with f.open() as d:
        p=d.new_page();xref=p.insert_image(f.Rect(40,80,200,200),stream=pix.tobytes('png'));base=d.tobytes()
        mask=p.get_images()[0][1];assert mask
        original_stream=d.xref_stream(xref);original_mask=d.xref_stream(mask)
        row=image_model(d,0)['images'][0];assert row['editable']
    moved=edit_image(base,[watermark(size=24)],0,xref,'move',[60,250,160,120])
    with f.open(stream=moved) as d:
        p=d[0];assert 'BORRADOR' in p.get_text()
        images=[i for i in p.get_images() if i[2:4]==(40,30)];assert len(images)==1
        assert d.xref_stream(images[0][0])==original_stream and d.xref_stream(images[0][1])==original_mask
    with pytest.raises(DocumentError):edit_image(base,[],0,xref,'move',[-1,0,100,100])


def test_multi_span_paragraph_replacement_embeds_unicode_font_and_preserves_outside():
    from backend.paragraphs import inspect_paragraph,replace_paragraph
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Primera parte ',fontname='helv',fontsize=14);p.insert_text((140,80),'en negrita',fontname='hebo',fontsize=14);p.insert_text((40,105),'Segunda linea de parrafo',fontname='tiro',fontsize=14);p.insert_text((40,400),'Conservar fuera',fontsize=14);base=d.tobytes()
    region=[30,55,400,100];model=inspect_paragraph(base,[],0,region);assert 'Primera parte' in model['text'] and 'Segunda' in model['text']
    out=replace_paragraph(base,[],0,region,'Nuevo párrafo: αβγ, Привет.\nSegunda línea.',size=14,color=[.1,.2,.3],align=0)
    with f.open(stream=out) as d:
        text=d[0].get_text();assert 'Primera parte' not in text and 'Segunda linea de parrafo' not in text
        assert 'Nuevo párrafo' in text and 'αβγ' in text and 'Привет' in text and 'Conservar fuera' in text
        assert any('DejaVu' in row[3] for row in d[0].get_fonts())
    with pytest.raises(DocumentError,match='cabe'):replace_paragraph(base,[],0,region,'Mucho texto '*200,size=60,color=[0,0,0])
    with pytest.raises(DocumentError,match='corta'):inspect_paragraph(base,[],0,[60,55,100,40])


def test_blank_password_restrictions_survive_edits_versions_and_optimization():
    from backend.pages import organize_pdf
    from backend.page_tools import crop_pdf
    with f.open(stream=source()) as doc:
        base=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_MODIFY|f.PDF_PERM_ASSEMBLE|f.PDF_PERM_FORM)
    values={'title':'Título','author':'','subject':'','keywords':'','creator':''}
    versions=[export_pdf(base,[watermark()]),metadata_pdf(base,[],values),optimize_pdf(base,[])[0],
              organize_pdf(base,[],[{'page':1,'rotation':0},{'page':0,'rotation':0}]),crop_pdf(base,[],[0],[10,10,10,10])]
    for data in versions:
        with f.open(stream=data) as doc:
            assert not doc.needs_pass and not doc.permissions & f.PDF_PERM_COPY and not doc.permissions & f.PDF_PERM_PRINT
            assert doc.metadata['encryption']
