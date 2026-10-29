import copy
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, export_pdf
from backend.redaction_search import search_redactions, redact_search


def source(rotation=0, crop=False):
    with f.open() as d:
        for i in range(3):
            p=d.new_page(width=500,height=650)
            p.insert_text((60,100),'Secret-93847 KEEP-58291',fontsize=16)
            p.insert_text((60,160),'ana@example.org',fontsize=16)
            p.insert_text((60,220),'STRASSE / Stra\u00dfe',fontsize=16)
            p.insert_text((60,280),'secret-93847',fontsize=16)
            if crop:p.set_cropbox(f.Rect(20,30,480,620))
            p.set_rotation(rotation)
        d.set_metadata({'title':'Private title'})
        return d.tobytes()


def query(**kwargs):
    return {'terms':['Secret-93847'],'emails':False,'case_sensitive':False,'pages':[0,1],**kwargs}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_search_rotations_crop_selective_redaction_and_independent_extraction(rotation,crop,tmp_path):
    base=source(rotation,crop);q=query(terms=['Secret-93847','KEEP-58291'],emails=True)
    pristine=copy.deepcopy(q);report=search_redactions(base,[],q)
    assert len(report['candidates'])==8 and report['empty_pages']==[]
    assert report==search_redactions(base,[],q) and q==pristine
    chosen=[c for c in report['candidates'] if c['text']=='Secret-93847' or c['kind']=='email']
    result,pages=redact_search(base,[],q,report['receipt'],[c['id'] for c in chosen])
    assert pages==[0,1]
    with f.open(stream=base) as before,f.open(stream=result) as after:
        for n in pages:
            p=after[n];text=p.get_text()
            assert 'Secret-93847' not in text and '@' not in text
            assert 'KEEP-58291' in text and 'secret-93847' in text
            assert p.rotation==rotation and p.cropbox==before[n].cropbox
            for c in [c for c in chosen if c['page']==n]:
                x,y,w,h=c['box'];rect=f.Rect(x,y,x+w,y+h)*p.derotation_matrix
                assert not p.get_textbox(rect).strip()
        assert before[2].get_pixmap().samples==after[2].get_pixmap().samples
        assert 'Secret-93847' in after[2].get_text()
        assert not after.metadata.get('title')
    target=tmp_path/'redacted.pdf';target.write_bytes(result)
    text=subprocess.check_output(['pdftotext','-f','1','-l','2',str(target),'-']).decode()
    assert 'Secret-93847' not in text and 'ana@example.org' not in text and 'KEEP-58291' in text


def test_casefold_preserves_character_mapping_and_deduplicates():
    base=source();q=query(terms=['STRASSE','strasse','Straße'],pages=[0])
    r=search_redactions(base,[],q)
    assert [c['text'] for c in r['candidates']]==['STRASSE','Straße']
    out,_=redact_search(base,[],q,r['receipt'],[c['id'] for c in r['candidates']])
    with f.open(stream=out) as d:assert 'STRASSE' not in d[0].get_text() and 'Straße' not in d[0].get_text()
    assert len(search_redactions(base,[],query(terms=['Secret-93847'],case_sensitive=True))['candidates'])==2


def test_literal_search_not_regex_and_not_across_lines():
    q=query(terms=['.*','Secret-93847 KEEP-58291 ana@example.org'])
    assert search_redactions(source(),[],q)['candidates']==[]


def test_search_current_applied_edits_and_rejects_changed_inspection():
    base=source();op={'type':'textbox','page':0,'points':[[60,350],[280,400]],'text':'Pending-4271','font':'helv','size':14,'align':0,'color':[0,0,0]}
    q=query(terms=['Pending-4271'],pages=[0]);ops=[op];r=search_redactions(base,ops,q)
    assert len(r['candidates'])==1
    out,_=redact_search(base,ops,q,r['receipt'],[r['candidates'][0]['id']])
    with f.open(stream=out) as d:assert 'Pending-4271' not in d[0].get_text() and 'KEEP-58291' in d[0].get_text()
    for changed_base,changed_ops,changed_q in [(base,[],q),(base,ops,query(terms=['Pending-4271'],case_sensitive=True,pages=[0])),(export_pdf(base,ops),[],q)]:
        with pytest.raises(DocumentError,match='cambió'):redact_search(changed_base,changed_ops,changed_q,r['receipt'],[r['candidates'][0]['id']])


@pytest.mark.parametrize('change',[
 {'terms':[]},{'terms':['']},{'terms':['  ']},{'terms':['a\nb']},{'terms':['x'*161]},
 {'terms':['a']*21},{'terms':[True]},{'terms':'secret'}, {'emails':1},{'case_sensitive':None},
 {'pages':[]},{'pages':[0,0]},{'pages':[True]},{'pages':[99]}, {'unknown':True},
])
def test_invalid_search_rejected(change):
    with pytest.raises(DocumentError):search_redactions(source(),[],query(**change))


@pytest.mark.parametrize('selected',[[],['unknown'],['unknown','unknown'],[True],['x']*101,None])
def test_forged_and_invalid_selection(selected):
    base=source();q=query();r=search_redactions(base,[],q)
    with pytest.raises(DocumentError):redact_search(base,[],q,r['receipt'],selected)


def test_no_text_and_skew_reported():
    with f.open() as d:
        d.new_page()
        p=d.new_page();p.insert_text((80,100),'Secret-93847',morph=(f.Point(80,100),f.Matrix(1,.2,0,1,0,0)))
        base=d.tobytes()
    r=search_redactions(base,[],query())
    assert r['empty_pages']==[0] and r['unsupported_pages']==[1] and not r['candidates']


def test_limits_fail_without_partial_results(monkeypatch):
    import backend.redaction_search as m
    with monkeypatch.context() as patch:
        patch.setattr(m,'MAX_MATCHES',1)
        with pytest.raises(DocumentError,match='500 coincidencias'):search_redactions(source(),[],query())
    with monkeypatch.context() as patch:
        patch.setattr(m,'MAX_CHARACTERS',10)
        with pytest.raises(DocumentError,match='500 000'):search_redactions(source(),[],query())
    with f.open() as d:
        for _ in range(21):d.new_page()
        with pytest.raises(DocumentError,match='20 páginas'):search_redactions(d.tobytes(),[],query(pages=list(range(21))))


@pytest.mark.parametrize('protected',['signed','no_copy','no_modify'])
def test_source_permissions_and_signatures(protected):
    with f.open(stream=source()) as d:
        if protected=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
        else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_MODIFY if protected=='no_copy' else f.PDF_PERM_COPY)
    with pytest.raises(DocumentError):search_redactions(base,[],query())


def test_search_does_not_bypass_complex_source_redaction_guards():
    with f.open(stream=source()) as d:
        p=d[0];w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='protected';w.rect=f.Rect(50,400,200,430);p.add_widget(w);base=d.tobytes()
    q=query();r=search_redactions(base,[],q)
    with pytest.raises(DocumentError,match='Aplana primero'):redact_search(base,[],q,r['receipt'],[r['candidates'][0]['id']])


def test_search_api_and_manual_preview_page_validation(monkeypatch,tmp_path):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'recovery'))
    with TestClient(app) as c:
        base=source();info=c.post('/api/documents',files={'file':('private.pdf',base,'application/pdf')}).json();url=f"/api/documents/{info['id']}"
        q=query();r=c.post(url+'/redact/search',json={'query':q});assert r.status_code==200;r=r.json()
        payload={'query':q,'receipt':r['receipt'],'selected':[x['id'] for x in r['candidates'] if x['page']==1]}
        assert c.post(url+'/redact/search/apply',json={**payload,'preview':True,'preview_page':True}).status_code==422
        assert c.post(url+'/redact/search/apply',json={**payload,'preview':True,'preview_page':0}).status_code==422
        preview=c.post(url+'/redact/search/apply',json={**payload,'preview':True,'preview_page':1});assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        result=c.post(url+'/redact/search/apply',json=payload);assert result.status_code==200 and result.content.startswith(b'%PDF')
        with f.open(stream=result.content) as d:assert 'Secret-93847' in d[0].get_text() and 'Secret-93847' not in d[1].get_text()
        assert c.post(url+'/redact/search',json={'query':None}).status_code==422
        regions=[{'page':1,'box':[50,70,300,40]}]
        assert c.post(url+'/redact',json={'regions':regions,'preview':True,'preview_page':0}).status_code==422
        assert c.post(url+'/redact',json={'regions':regions,'preview':True,'preview_page':1}).status_code==200
        text=c.post(url+'/pages/0/text',json={'operations':[]}).json()
        assert text['characters'] and text['words'] and not text['characters_truncated']
