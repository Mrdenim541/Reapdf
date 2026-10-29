"""Recipe contracts: ordered transformations, native artifacts, atomic failures and no secrets."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import shutil
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.automation import validate_recipe,process_recipe
from backend.engine import DocumentError
from tests.test_batch_tools import source


def recipe(*steps):
    return {'format':'reapdf-recipe','version':1,'name':'Flujo ñ','filename':'{name}-{recipe}-{index}','steps':list(steps)}


def rows(archive):
    z=ZipFile(BytesIO(archive));return z,json.loads(z.read('manifest.json'))


def test_ordered_watermark_numbering_metadata_optimization_and_independent_text():
    plan=recipe({'type':'watermark','text':'REVISADO','size':24,'opacity':.2,'angle':0,'color':[.3,.3,.3]},
                {'type':'numbering','template':'Serie {numero}: {pagina}/{total}','start':7,'size':10},
                {'type':'metadata','values':{'title':'Trabajo terminado','author':'Equipo','subject':'','keywords':'','creator':'Reapdf'},'remove_xml':True},
                {'type':'optimize'})
    original=source(pages=2);z,report=rows(process_recipe([('../../á.pdf',original,[]),('á.pdf',original,[])],plan))
    assert len(set(z.namelist()))==3
    for row in report['documents']:
        assert '/' not in row['file'] and '\\' not in row['file']
        data=z.read(row['file']);assert sha256(data).hexdigest()==row['output_sha256']
        with f.open(stream=data) as d:
            assert d.metadata['title']=='Trabajo terminado'
            for index,p in enumerate(d):
                assert 'REVISADO' in p.get_text() and f'Serie {index+7}: {index+1}/2' in p.get_text()
                assert 'Documento de prueba' in p.get_text()
        logs=row['steps'];assert [s['type'] for s in logs]==[s['type'] for s in plan['steps']]
        assert all(a['output_sha256']==b['input_sha256'] for a,b in zip(logs,logs[1:]))
        assert logs[-1]['output_sha256']==row['output_sha256']
    assert len(original)==report['documents'][0]['input_bytes']


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_numbering_and_marks_respect_cropped_rotated_pages(rotation,tmp_path):
    with f.open(stream=source()) as d:
        d[0].set_cropbox(f.Rect(20,20,380,480));d[0].set_rotation(rotation);base=d.tobytes()
    plan=recipe({'type':'numbering','template':'{pagina}/{total}','start':1,'size':10},
                {'type':'watermark','text':'COPIA','size':24,'opacity':.15,'angle':45,'color':[.4,.4,.4]})
    z,report=rows(process_recipe([('rotada.pdf',base,[])],plan));out=z.read(report['documents'][0]['file'])
    with f.open(stream=out) as d,f.open(stream=base) as old:
        assert d[0].rotation==rotation and d[0].cropbox==old[0].cropbox
        assert '1/1' in d[0].get_text() and 'COPIA' in d[0].get_text()
    target=tmp_path/'out.pdf';target.write_bytes(out)
    if shutil.which('pdftotext'):
        independent=subprocess.check_output(['pdftotext','-raw',str(target),'-']).decode()
        assert 'COPIA' in ''.join(independent.split())


def test_review_has_only_first_page_preview_and_archive_manifest_has_no_images():
    plan=recipe({'type':'optimize'});base=source(pages=2)
    report=process_recipe([('a.pdf',base,[])],plan,review=True)
    assert report['documents'][0]['preview'].startswith('data:image/png;base64,')
    z,actual=rows(process_recipe([('a.pdf',base,[])],plan));assert 'preview' not in actual['documents'][0]
    assert actual['documents'][0]['output_sha256']==sha256(z.read(actual['documents'][0]['file'])).hexdigest()


def test_encryption_is_terminal_and_passwords_not_in_manifest_or_recipe():
    plan=recipe({'type':'numbering','template':'{numero}','start':15,'size':10}, {'type':'protect','allow_copy':False,'allow_print':True})
    secrets={'password':'User-pass-2026!','owner_password':'Owner-pass-2026!'};base=source()
    review=process_recipe([('a.pdf',base,[])],plan,secrets,True)
    z,report=rows(process_recipe([('a.pdf',base,[])],plan,secrets))
    for secret in secrets.values():assert secret not in json.dumps(report) and secret not in json.dumps(review)
    with f.open(stream=z.read(report['documents'][0]['file'])) as d:
        assert d.needs_pass and d.authenticate(secrets['password'])
        assert not d.permissions&f.PDF_PERM_COPY and d.permissions&f.PDF_PERM_PRINT
        assert '15' in d[0].get_text()


def test_text_terminal_includes_session_edits_and_prior_steps():
    plan=recipe({'type':'numbering','template':'Folio {numero}','start':10,'size':10},{'type':'text'})
    z,report=rows(process_recipe([('texto.pdf',source(),[{'type':'note','page':0,'point':[100,100],'content':'nota','color':[1,0,0]}])],plan))
    row=report['documents'][0];assert row['file'].endswith('.txt') and row['includes_applied_operations']
    assert 'Folio 10' in z.read(row['file']).decode() and 'Documento de prueba' in z.read(row['file']).decode()
    assert 'preview' not in process_recipe([('a.pdf',source(),[])],plan,review=True)['documents'][0]


def test_flatten_skips_documents_without_fields_and_flattens_supported_fields():
    with f.open(stream=source()) as d:
        w=f.Widget();w.field_name='Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(50,120,250,150);w.field_value='Carolina';d[0].add_widget(w);base=d.tobytes()
    z,report=rows(process_recipe([('sin.pdf',source(),[]),('con.pdf',base,[])],recipe({'type':'flatten'},{'type':'optimize'})))
    assert report['documents'][0]['steps'][0]['status']=='skipped'
    assert report['documents'][1]['steps'][0]['details']['fields']==1
    with f.open(stream=z.read(report['documents'][1]['file'])) as d:assert not list(d[0].widgets() or []) and 'Carolina' in d[0].get_text()


def test_compression_pipeline_applies_before_watermark_and_preserves_text():
    from tests.test_compression import source as image_source
    plan=recipe({'type':'compress','dpi':150,'quality':85},{'type':'watermark','text':'COPIA','size':24,'opacity':.15,'angle':0,'color':[.2,.2,.2]},{'type':'optimize'})
    base=image_source();z,report=rows(process_recipe([('foto.pdf',base,[])],plan))
    row=report['documents'][0];assert row['steps'][0]['details']['changed_images'] and row['output_bytes']<len(base)
    with f.open(stream=z.read(row['file'])) as d:assert 'Texto conservado' in d[0].get_text() and 'COPIA' in d[0].get_text()


@pytest.mark.parametrize('change',[
 lambda r:r.update(version=True),lambda r:r.update(version=2),lambda r:r.update(password='secret'),
 lambda r:r.update(steps=[]),lambda r:r.update(steps=[{'type':'optimize'}]*2),
 lambda r:r.update(steps=[{'type':'protect','allow_copy':True,'allow_print':True},{'type':'optimize'}]),
 lambda r:r.update(steps=[{'type':'text'},{'type':'optimize'}]),
 lambda r:r.update(steps=[{'type':'shell','command':'echo hello'}]),
 lambda r:r.update(steps=[{'type':'optimize','password':'hidden'}]),
 lambda r:r.update(filename='../{name}'),lambda r:r.update(filename='{unknown}'),
 lambda r:r.update(filename='{name'),lambda r:r.update(filename='bad\nname'),
 lambda r:r.update(steps=[{'type':'compress','dpi':True,'quality':85}]),
 lambda r:r.update(steps=[{'type':'compress','dpi':150,'quality':float('nan')}]),
 lambda r:r.update(steps=[{'type':'numbering','template':'{other}','start':1,'size':10}]),
 lambda r:r.update(steps=[{'type':'numbering','template':'{pagina}','start':1,'size':float('inf')}]),
 lambda r:r.update(steps=[{'type':'metadata','values':{},'remove_xml':False}]),
 lambda r:r.update(steps=[{'type':'watermark','text':'a','size':0,'opacity':.15,'angle':0,'color':[0,0,0]}]),
 lambda r:r.update(steps=[{'type':'protect','allow_copy':1,'allow_print':True}]),
])
def test_invalid_untrusted_recipes_are_rejected(change):
    value=recipe({'type':'optimize'});change(value)
    with pytest.raises(DocumentError):validate_recipe(value)


def test_compression_can_follow_a_vector_watermark():
    plan=recipe({'type':'watermark','text':'A','size':12,'opacity':.1,'angle':0,'color':[0,0,0]},{'type':'compress','dpi':150,'quality':85})
    from tests.test_compression import source as image_source
    z,report=rows(process_recipe([('a.pdf',image_source(),[])],plan))
    assert report['documents'][0]['steps'][1]['details']['changed_images']
    with f.open(stream=z.read(report['documents'][0]['file'])) as d:assert 'Texto conservado' in d[0].get_text()


def test_document_specific_failure_is_atomic_and_identifies_step():
    with f.open() as d:d.new_page(width=40,height=40);small=d.tobytes()
    plan=recipe({'type':'optimize'},{'type':'watermark','text':'DEMASIADO LARGO','size':36,'opacity':.15,'angle':0,'color':[0,0,0]})
    with pytest.raises(DocumentError,match='Documento 2, paso 2'):process_recipe([('ok.pdf',source(),[]),('small.pdf',small,[])],plan)
    with pytest.raises(DocumentError,match='Documento 1, paso 1'):process_recipe([('bad.pdf',source(),[{'type':'unknown','page':0}])],recipe({'type':'optimize'}))


@pytest.mark.parametrize('mode',['signed','restricted'])
def test_read_only_sources_allow_only_text_recipe(mode):
    with f.open(stream=source()) as d:
        if mode=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
        else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_COPY)
    assert process_recipe([('a.pdf',base,[])],recipe({'type':'text'}))
    with pytest.raises(DocumentError,match='Documento 2, validación'):process_recipe([('allowed.pdf',source(),[]),('a.pdf',base,[])],recipe({'type':'optimize'}))


def test_permission_limits_and_intermediate_budgets(monkeypatch):
    base=source()
    with pytest.raises(DocumentError,match='100 páginas'):process_recipe([('a.pdf',source(pages=101),[])],recipe({'type':'text'}))
    monkeypatch.setattr('backend.automation.MAX_INPUT',10)
    with pytest.raises(DocumentError,match='entrada'):process_recipe([('a.pdf',base,[])],recipe({'type':'text'}))
    monkeypatch.setattr('backend.automation.MAX_INPUT',1000000);monkeypatch.setattr('backend.automation.MAX_OUTPUT',10)
    with pytest.raises(DocumentError,match='intermedio'):process_recipe([('a.pdf',base,[])],recipe({'type':'optimize'}))


def test_recipe_api_validation_download_and_session_unchanged():
    with TestClient(app) as c:
        base=source();doc=c.post('/api/documents',files={'file':('a.pdf',base,'application/pdf')}).json()
        plan=recipe({'type':'numbering','template':'{pagina}/{total}','start':1,'size':10},{'type':'optimize'})
        assert c.post('/api/recipes/validate',json={'recipe':plan}).json()==plan
        payload={'documents':[{'id':doc['id'],'name':'a.pdf'}],'recipe':plan,'review':True}
        review=c.post('/api/automation',json=payload);assert review.status_code==200 and review.json()['documents'][0]['preview']
        result=c.post('/api/automation',json=payload|{'review':False});assert result.status_code==200 and result.headers['content-type']=='application/zip'
        z,report=rows(result.content);assert report['recipe']==plan
        assert c.post('/api/automation',json=payload|{'documents':payload['documents']*2}).status_code==422
        assert c.post('/api/automation',json=payload|{'secrets':{'password':'unexpected'}}).status_code==422
        assert c.get('/api/documents/'+doc['id']+'/pages/0').status_code==200
        # Source remains unnumbered; downloading a copy cannot mutate its bytes.
        raw=c.post('/api/documents/'+doc['id']+'/export',json={'operations':[]})
        assert raw.content==base


def test_cli_review_actual_download_collision_and_no_partial_file(tmp_path):
    base=tmp_path/'original.pdf';base.write_bytes(source());rp=tmp_path/'recipe.json';rp.write_text(json.dumps(recipe({'type':'numbering','template':'{numero}','start':55,'size':10},{'type':'optimize'})))
    output=tmp_path/'copies.zip';command=[sys.executable,'scripts/run_recipe.py','--recipe',str(rp),'--output',str(output),str(base)]
    assert subprocess.run(command,capture_output=True).returncode==0
    z,report=rows(output.read_bytes());assert len(report['documents'])==1
    old=output.read_bytes();assert subprocess.run(command,capture_output=True).returncode==2 and output.read_bytes()==old
    result=subprocess.run(command[:-1]+['--overwrite',str(base)],capture_output=True);assert result.returncode==0,result.stderr
    review=tmp_path/'review.json';assert subprocess.run([sys.executable,'scripts/run_recipe.py','--recipe',str(rp),'--output',str(review),'--review',str(base)],capture_output=True).returncode==0
    data=json.loads(review.read_text());assert data['review_only'] and 'preview' not in data['documents'][0]
    bad=tmp_path/'bad.pdf';bad.write_bytes(b'broken');failed=tmp_path/'failed.zip'
    assert subprocess.run([sys.executable,'scripts/run_recipe.py','--recipe',str(rp),'--output',str(failed),str(base),str(bad)],capture_output=True).returncode==2
    assert not failed.exists() and not list(tmp_path.glob('.reapdf-*'))
    assert subprocess.run([sys.executable,'scripts/run_recipe.py','--recipe',str(rp),'--output',str(base),'--overwrite',str(base)],capture_output=True).returncode==2


def test_flatten_and_compress_keep_form_values_in_a_fixed_copy():
    from tests.test_compression import source as image_source
    with f.open(stream=image_source()) as d:
        w=f.Widget();w.field_name='Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(50,500,250,530);w.field_value='Carolina';d[0].add_widget(w);base=d.tobytes()
    plan=recipe({'type':'flatten'},{'type':'compress','dpi':150,'quality':90})
    z,report=rows(process_recipe([('form.pdf',base,[])],plan));row=report['documents'][0]
    assert row['steps'][1]['details']['changed_images']
    with f.open(stream=z.read(row['file'])) as d:
        assert not list(d[0].widgets() or []) and 'Carolina' in d[0].get_text() and 'Texto conservado' in d[0].get_text()


def test_cli_protect_requires_interactive_passwords_without_traceback(tmp_path):
    rp=tmp_path/'recipe.json';rp.write_text(json.dumps(recipe({'type':'protect','allow_copy':True,'allow_print':True})))
    base=tmp_path/'a.pdf';base.write_bytes(source());out=tmp_path/'out.zip'
    result=subprocess.run([sys.executable,'scripts/run_recipe.py','--recipe',str(rp),'--output',str(out),str(base)],input=b'',capture_output=True)
    assert result.returncode==2 and b'consola interactiva' in result.stderr and b'Traceback' not in result.stderr and not out.exists()


@pytest.mark.parametrize('where',['name','metadata','document'])
def test_unicode_surrogates_fail_as_validation_errors(where):
    plan=recipe({'type':'optimize'});name='a.pdf'
    if where=='name':plan['name']='invalid\ud800'
    elif where=='metadata':plan['steps']=[{'type':'metadata','values':dict.fromkeys(['title','author','subject','keywords','creator'],'invalid\ud800'),'remove_xml':False}]
    else:name='invalid\ud800.pdf'
    with pytest.raises(DocumentError,match='Unicode'):process_recipe([(name,source(),[])],plan)


def test_long_unicode_output_names_remain_extractable_on_common_filesystems():
    plan=recipe({'type':'optimize'});plan['filename']='{name}{recipe}';plan['name']='𐐀'*70
    z,report=rows(process_recipe([('𐐀'*70+'.pdf',source(),[])],plan));row=report['documents'][0]
    assert len(row['file'].encode('utf-8'))<255 and row['file'] in z.namelist()
