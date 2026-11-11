import base64,hashlib,struct
import pytest
import pymupdf as f
from PIL import ImageCms
from backend.engine import DocumentError
from backend.press_icc import inspect as icc
from backend.press_prepare import prepare
from backend.preflight import inspect
from backend.press_metadata import claims
from scripts.create_press_sample import create,profile


def config(**kw):return {'profile':'x4-2010','set_boxes':True,'pages':[0,1],'trim_margin_mm':3,'bleed_mm':3,'icc':base64.b64encode(profile()).decode(),'condition':'SYNTHETIC TEST - NOT A REAL PRESS',**kw}
def change(base,**kw):
    p=config(**kw);r=prepare(base,[],p,True);return prepare(base,[],{**p,'review_token':r['review_token'],'acknowledge':True})


def test_pdfx_profiles_detect_real_obstacles_but_never_certify():
    base=create();x4=inspect(base,[],150,'x4-2010')['press_profile'];x1=inspect(base,[],150,'x1a-2001')['press_profile']
    assert x4['status']=='blocked' and x4['compliant'] is None and not x4['validation_complete']
    assert {'output_intent','font_embedding','page_boxes'}<={c['code'] for c in x4['checks'] if c['status']=='error'}
    assert any(c['code']=='color_space' and c['status']=='error' for c in x1['checks'])
    out,r=change(create(embedded=True));p=r['preflight']['press_profile'];assert not p['counts']['error'] and p['status']=='needs_full_validation' and p['compliant'] is None
    assert p['output_profile']['space']=='RGB' and not r['colors_converted'] and not r['standard_conformity_claimed']


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('offset',[False,True])
def test_preparation_preserves_native_objects_visible_crop_rotation_and_other_page(rotation,offset):
    with f.open(stream=create()) as d:
        if offset:d[0].set_mediabox(f.Rect(-20,-30,580,770));d[0].set_cropbox(f.Rect(10,20,550,740))
        d[0].set_rotation(rotation);d[0].set_artbox(d[0].cropbox);base=d.tobytes()
    out,r=change(base,pages=[0],icc='');assert r['native_content_preserved'] and r['changed_pages'][0]['page']==0
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert len(a)==len(b) and a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox and a[0].mediabox==b[0].mediabox
        assert a[0].read_contents()==b[0].read_contents() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert b.xref_get_key(b[0].xref,'ArtBox')[0]=='null' and b.xref_get_key(b[1].xref,'TrimBox')[0]=='null'
        raw=f.mupdf.pdf_dict_gets(f.mupdf.pdf_load_object(f._as_pdf_document(b),b[0].xref),'TrimBox');vals=[f.mupdf.pdf_to_real(f.mupdf.pdf_array_get(raw,i)) for i in range(4)];expected=a[0].mediabox+(3*72/25.4,3*72/25.4,-3*72/25.4,-3*72/25.4)
        assert vals==pytest.approx(list(expected),abs=.001)


@pytest.mark.parametrize('field,value',[('trim_margin_mm',4),('bleed_mm',2),('pages',[1]),('condition','changed'),('profile','x1a-2001')])
def test_review_is_invalidated_by_every_effective_change(field,value):
    base=create();p=config();r=prepare(base,[],p,True)
    with pytest.raises(DocumentError,match='Revisa de nuevo'):prepare(base,[],{**p,field:value,'review_token':r['review_token'],'acknowledge':True})


def test_review_binds_original_and_operations_without_binding_variable_output_ids():
    base=create();p=config();r=prepare(base,[],p,True);again=prepare(base,[],p,True);assert r['review_token']==again['review_token']
    with f.open(stream=base) as d:d[0].insert_text((30,500),'DIFFERENT');other=d.tobytes()
    with pytest.raises(DocumentError,match='Revisa de nuevo'):prepare(other,[],{**p,'review_token':r['review_token'],'acknowledge':True})
    with pytest.raises(DocumentError):prepare(base,[],{**p,'review_token':r['review_token'],'acknowledge':False})


@pytest.mark.parametrize('kw',[{'trim_margin_mm':-1},{'trim_margin_mm':2,'bleed_mm':3},{'bleed_mm':21},{'trim_margin_mm':float('nan')},{'pages':[0,0]},{'pages':[-1]},{'pages':[True]},{'pages':[]},{'set_boxes':False,'icc':''},{'set_boxes':1},{'profile':'fake'}])
def test_invalid_configuration_rejects_before_publishing(kw):
    with pytest.raises(DocumentError):prepare(create(),[],config(**kw),True)


@pytest.mark.parametrize('damage',['size','signature','version','duplicate','offset','channels','display_class','garbage'])
def test_malformed_or_nonprinter_icc_is_rejected(damage):
    data=bytearray(profile())
    if damage=='size':data[0:4]=struct.pack('>I',len(data)+1)
    elif damage=='signature':data[36:40]=b'nope'
    elif damage=='version':data[8]=8
    elif damage=='duplicate':data[144:148]=data[132:136]
    elif damage=='offset':data[136:140]=struct.pack('>I',4)
    elif damage=='channels':data[16:20]=b'CMYK'
    elif damage=='display_class':data[12:16]=b'mntr'
    else:data=b'not a profile'
    with pytest.raises(DocumentError):icc(bytes(data))


def test_x1a_does_not_turn_rgb_into_cmyk_by_assigning_a_profile():
    out,r=change(create(),profile='x1a-2001');p=r['preflight']['press_profile'];assert any(c['code']=='color_space' and c['status']=='error' for c in p['checks']);assert any(c['code']=='output_intent' and c['status']=='error' for c in p['checks'])


def test_metadata_claims_are_withdrawn_without_losing_unknown_namespaces_or_tags():
    from lxml import etree as E
    with f.open(stream=create()) as d:
        d.set_metadata({'title':'Keep title','author':'Personal'});info=int(d.xref_get_key(-1,'Info')[1].split()[0]);d.xref_set_key(info,'GTS_PDFXVersion','(PDF/X-4)');d.xref_set_key(info,'CustomNote','(Keep this)')
        d.set_xml_metadata('<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/" xmlns:own="urn:reapdf:test" pdfaid:part="2" pdfxid:GTS_PDFXVersion="PDF/X-4" own:keep="keep"><own:note><![CDATA[keep <content>]]></own:note></rdf:Description></rdf:RDF></x:xmpmeta>');base=d.tobytes()
    out,r=change(base,icc='');assert len(r['withdrawn_claims'])==3
    with f.open(stream=out) as d:
        assert not claims(d) and d.metadata['title']=='Keep title';assert d.xref_get_key(int(d.xref_get_key(-1,'Info')[1].split()[0]),'CustomNote')==('string','Keep this')
        xml=E.fromstring(d.get_xml_metadata().encode());assert xml.find('.//{urn:reapdf:test}note').text=='keep <content>' and any(el.get('{urn:reapdf:test}keep')=='keep' for el in xml.iter())


@pytest.mark.parametrize('xml',['<!DOCTYPE x [<!ENTITY a "unsafe">]><x>&a;</x>','<unclosed>'])
def test_unreviewable_metadata_is_not_dropped_silently(xml):
    with f.open(stream=create()) as d:d.set_xml_metadata(xml);base=d.tobytes()
    with pytest.raises(DocumentError):prepare(base,[],config(),True)


def test_profile_identity_survives_saved_copy_and_preview_uses_changed_page():
    base=create();p=config(pages=[1]);r=prepare(base,[],p,True);assert r['preview']['page']==1 and r['preview']['overlay']['size']==[600,800]
    out,report=prepare(base,[],{**p,'review_token':r['review_token'],'acknowledge':True})
    with f.open(stream=out) as d:
        n=f.mupdf;root=n.pdf_load_object(f._as_pdf_document(d),d.pdf_catalog());intent=n.pdf_array_get(n.pdf_dict_gets(root,'OutputIntents'),0);x=n.pdf_to_num(n.pdf_dict_gets(intent,'DestOutputProfile'));assert hashlib.sha256(d.xref_stream(x)).hexdigest()==icc(profile())['sha256']


def test_synthetic_cmyk_v2_output_and_cmyk_content_pass_checked_x1a_conditions():
    data=base64.b64encode(profile(True)).decode();out,r=change(create(embedded=True,cmyk=True),profile='x1a-2001',icc=data);p=r['preflight']['press_profile'];assert not p['counts']['error'] and p['output_profile']['space']=='CMYK' and p['output_profile']['major_version']==2 and p['compliant'] is None


@pytest.mark.parametrize('kind',['opacity','softmask','blend_array','group','javascript','attachment','layers','widget'])
def test_profile_finds_transparency_and_interactive_resources(kind):
    with f.open(stream=create()) as d:
        x=d.get_new_xref();d.update_object(x,'<<>>');res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);d.xref_set_key(res,'ExtGState',f'<</Test {x} 0 R>>')
        if kind=='opacity':d.xref_set_key(x,'ca','.5')
        if kind=='softmask':d.xref_set_key(x,'SMask','<</S/Luminosity>>')
        if kind=='blend_array':d.xref_set_key(x,'BM','[/Multiply /Normal]')
        if kind=='group':d.xref_set_key(x,'Group','<</S/Transparency>>')
        if kind=='javascript':d.xref_set_key(d.pdf_catalog(),'OpenAction','<</S/JavaScript/JS(app.alert\\(1\\))>>')
        if kind=='attachment':d.embfile_add('test.txt',b'SYNTHETIC')
        if kind=='layers':d.add_ocg('TestLayer')
        if kind=='widget':
            w=f.Widget();w.field_name='Sample';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(20,200,250,240);d[0].add_widget(w)
        data=d.tobytes()
    r=inspect(data,[],150,'x1a-2001')['press_profile'];expected='transparency' if kind in ['opacity','softmask','blend_array','group'] else {'javascript':'actions','attachment':'attachments','layers':'layers','widget':'interactive_content'}[kind];assert any(c['code']==expected and c['status']=='error' for c in r['checks'])


@pytest.mark.parametrize('protected',['signature','permission'])
def test_signed_or_restricted_sources_cannot_be_prepared(protected):
    with f.open(stream=create()) as d:
        if protected=='signature':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
        else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError):prepare(base,[],config(),True)


def test_review_is_invalidated_by_current_operations_and_icc_bytes():
    base=create();p=config();r=prepare(base,[],p,True);op={'type':'ink','page':0,'points':[[40,200],[80,230],[120,200]],'color':[1,0,0],'width':3}
    with pytest.raises(DocumentError,match='Revisa de nuevo'):prepare(base,[op],{**p,'review_token':r['review_token'],'acknowledge':True})
    other=bytearray(profile());other[4:8]=b'TEST';p['icc']=base64.b64encode(other).decode()
    with pytest.raises(DocumentError,match='Revisa de nuevo'):prepare(base,[],{**p,'review_token':r['review_token'],'acknowledge':True})


def test_unreachable_old_actions_do_not_become_current_blockers_but_direct_resources_do():
    with f.open(stream=create()) as d:
        x=d.get_new_xref();d.update_object(x,'<</S/JavaScript /JS(app.alert\\(1\\))>>');base=d.tobytes()
        res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);d.xref_set_key(res,'ExtGState','<</Direct <</ca .3>>>>');direct=d.tobytes()
    assert not any(c['code']=='actions' for c in inspect(base,[],150,'x1a-2001')['press_profile']['checks'])
    assert any(c['code']=='transparency' for c in inspect(direct,[],150,'x1a-2001')['press_profile']['checks'])


@pytest.mark.parametrize('kind',['tagged','shared_form','object_stream'])
def test_native_tag_graph_widgets_and_compressed_source_objects_are_preserved(kind):
    if kind=='tagged':
        from scripts.create_tagged_paragraph_sample import create as tagged
        base=tagged()
    elif kind=='shared_form':
        from scripts.create_shared_choice_sample import create as form
        base=form()
    else:
        with f.open(stream=create()) as d:base=d.tobytes(use_objstms=1,garbage=4,deflate=True)
    out,r=change(base,icc='');assert r['native_content_preserved']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert len(a)==len(b)
        for pa,pb in zip(a,b):assert pa.read_contents()==pb.read_contents() and pa.get_text()==pb.get_text() and pa.get_pixmap().samples==pb.get_pixmap().samples
        if kind=='tagged':
            from backend.tagged_text_integrity import snapshot
            assert snapshot(a,0)==snapshot(b,0)
        if kind=='shared_form':
            from backend.forms import form_model
            assert form_model(a)==form_model(b)


def test_icc_only_assignment_does_not_introduce_or_change_page_boxes():
    base=create();out,r=change(base,set_boxes=False,pages=None)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for pa,pb in zip(a,b):
            for key in ['MediaBox','CropBox','TrimBox','ArtBox','BleedBox']:assert a.xref_get_key(pa.xref,key)==b.xref_get_key(pb.xref,key)
            assert pa.read_contents()==pb.read_contents()
    assert r['changed_pages']==[]


def test_profile_and_review_apply_endpoints_publish_only_verified_version():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        base=create();doc=client.post('/api/documents',files={'file':('press.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id'];r=client.post(url+'/preflight',json={'operations':[],'profile':'x4-2010'});assert r.status_code==200 and r.json()['press_profile']['compliant'] is None
        p=config();review=client.post(url+'/prepare-print',json={**p,'operations':[],'review':True});assert review.status_code==200;token=review.json()['review_token']
        assert client.post(url+'/prepare-print',json={**p,'operations':[],'acknowledge':True,'review_token':'wrong'}).status_code==422
        applied=client.post(url+'/prepare-print',json={**p,'operations':[],'acknowledge':True,'review_token':token});assert applied.status_code==200 and applied.json()['id']!=doc['id'] and applied.json()['print_report']['native_content_preserved']
        original=client.post(url+'/export',json={'operations':[]});assert original.content==base
        downloaded=client.post('/api/documents/'+applied.json()['id']+'/export',json={'operations':[]});assert downloaded.status_code==200
        with f.open(stream=downloaded.content) as d:assert d.xref_get_key(d[0].xref,'TrimBox')[0]=='array'


@pytest.mark.parametrize('kind',['icc','indexed'])
def test_rgb_in_named_and_indexed_vector_spaces_is_not_missed_by_x1a(kind):
    with f.open(stream=create()) as d:
        p=d[0];res=int(d.xref_get_key(p.xref,'Resources')[1].split()[0]);x=d.get_new_xref();d.update_object(x,'<</N 3>>');d.update_stream(x,profile());space=f'[/ICCBased {x} 0 R]' if kind=='icc' else '[/Indexed /DeviceRGB 1 <000000FF0000>]';d.xref_set_key(res,'ColorSpace','<</Named '+space+'>>');s=d.get_new_xref();d.update_object(s,'<<>>');d.update_stream(s,b'/Named cs 0 0 0 sc 30 30 20 20 re f' if kind=='icc' else b'/Named cs 1 sc 30 30 20 20 re f');p.set_contents(s);base=d.tobytes()
    r=inspect(base,[],150,'x1a-2001')['press_profile'];assert any(c['code']=='color_space' and c['status']=='error' for c in r['checks'])


def test_pdfx_output_stream_channel_mismatch_is_reported():
    out,_=change(create())
    with f.open(stream=out) as d:
        n=f.mupdf;root=n.pdf_load_object(f._as_pdf_document(d),d.pdf_catalog());x=n.pdf_to_num(n.pdf_dict_gets(n.pdf_array_get(n.pdf_dict_gets(root,'OutputIntents'),0),'DestOutputProfile'));d.xref_set_key(x,'N','4');bad=d.tobytes()
    p=inspect(bad,[],150,'x4-2010')['press_profile'];assert any(c['code']=='output_intent' and c['status']=='error' for c in p['checks'])


def test_explicit_icc_preserves_paint_values_but_can_affect_renderer_interpretation():
    base=create(embedded=True);out,r=change(base)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for pa,pb in zip(a,b):
            assert pa.read_contents()==pb.read_contents() and pa.get_text()==pb.get_text()
            assert pa.rect==pb.rect
            assert max(abs(v-w) for v,w in zip(pa.get_pixmap().samples,pb.get_pixmap().samples))<=1
    assert not r['colors_converted'] and r['native_content_preserved']
