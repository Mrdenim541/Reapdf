"""Real independent veraPDF checks and fail-closed PDF/A copy generation."""
from pathlib import Path
from io import BytesIO
import hashlib,json,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.standards import standard_status,validate_standard,archival_copy,parse_validation
from tests.signature_samples import document,identity


@pytest.fixture(scope='module')
def archive():
    if not standard_status()['conversion_available']:pytest.skip('Ghostscript/Java/veraPDF no disponibles')
    return archival_copy(document(),[])


def test_actual_noncompliant_source_has_rules_without_content_or_temp_paths():
    if not standard_status()['validation_available']:pytest.skip('Java/veraPDF no disponibles')
    base=document();report=validate_standard(base,[])
    assert not report['compliant'] and report['complete'] and report['failed_rules']>0 and len(report['rules'])==report['failed_rules']
    encoded=json.dumps(report);assert 'Documento para firmar' not in encoded and '/tmp/' not in encoded and 'document.pdf' not in encoded
    assert report['source_sha256']==hashlib.sha256(base).hexdigest()


def test_real_archival_output_is_accepted_by_independent_validator_and_remains_searchable(archive):
    data,report=archive
    assert report['validation']['compliant'] and report['output_sha256']==hashlib.sha256(data).hexdigest()
    actual=validate_standard(data,[],'2b');assert actual['compliant'] and actual['failed_rules']==0
    with f.open(stream=data) as d:
        assert len(d)==2 and 'Documento para firmar' in d[0].get_text() and 'Segunda pagina intacta' in d[1].get_text()
        assert d.xref_get_key(d.pdf_catalog(),'OutputIntents')[0]=='array'
        assert 'pdfaid:part' in d.get_xml_metadata() and not d.metadata.get('encryption')


def test_pdfua_validation_does_not_accept_untagged_pdfa_as_accessible(archive):
    data,_=archive;report=validate_standard(data,[],'ua1')
    assert not report['compliant'] and report['failed_rules']>0 and report['profile']=='ua1'


def test_api_review_download_and_final_receipt_describe_actual_downloaded_bytes():
    if not standard_status()['conversion_available']:pytest.skip('Herramientas no disponibles')
    base=document()
    with TestClient(app) as c:
        status=c.get('/api/standards/status').json();assert status['validation_available']
        doc=c.post('/api/documents',files={'file':('archive.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=c.post(url+'/archive-pdfa',json={'review':True});assert r.status_code==200 and r.json()['validation']['compliant']
        out=c.post(url+'/archive-pdfa',json={});assert out.status_code==200
        receipt=json.loads(out.headers['X-Reapdf-Archive-Report']);assert receipt['output_sha256']==hashlib.sha256(out.content).hexdigest() and receipt['validation']['compliant']
        assert c.post(url+'/validate-standard',json={'profile':'2b'}).json()['compliant'] is False


@pytest.mark.parametrize('item',['annotations','link','field','attachment','tags','layer','signed','encrypted'])
def test_interactivity_tagged_sources_signatures_and_encryption_are_protected(item):
    if not standard_status()['conversion_available']:pytest.skip('Herramientas no disponibles')
    with f.open(stream=document()) as d:
        p=d[0]
        if item=='annotations':p.add_text_annot((40,100),'No retirar silenciosamente')
        elif item=='link':p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,100,180,125),'uri':'https://example.com'})
        elif item=='field':
            w=f.Widget();w.field_name='Cliente';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(40,100,180,125);p.add_widget(w)
        elif item=='attachment':d.embfile_add('nota.txt',b'nota')
        elif item=='tags':d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','<< /Type /StructTreeRoot /K [] >>')
        elif item=='layer':d.add_ocg('Capa')
        elif item=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>')
        if item=='encrypted':base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='')
        else:base=d.tobytes()
    with pytest.raises(DocumentError):archival_copy(base,[])


@pytest.mark.parametrize('profile',['0','4',None,[],1])
def test_invalid_profiles_rejected(profile):
    with pytest.raises(DocumentError):validate_standard(document(),[],profile)


def test_unavailable_resources_and_busy_process_never_claim_compliance(monkeypatch):
    import backend.standards as s
    monkeypatch.setattr(s.shutil,'which',lambda name:None)
    assert not s.standard_status()['validation_available']
    with pytest.raises(DocumentError):s.validate_standard(document(),[])
    with pytest.raises(DocumentError):s.archival_copy(document(),[])


def test_process_lock_is_bounded_and_released_on_timeout(monkeypatch):
    import backend.standards as s
    if not s.standard_status()['validation_available']:pytest.skip('Herramientas no disponibles')
    assert s.PROCESS_LOCK.acquire(False)
    try:
        with pytest.raises(DocumentError,match='en curso'):s.validate_standard(document(),[])
    finally:s.PROCESS_LOCK.release()
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired(args[0],90)
    monkeypatch.setattr(s.subprocess,'run',timeout)
    with pytest.raises(DocumentError,match='90 segundos'):s.validate_standard(document(),[])
    assert s.PROCESS_LOCK.acquire(False);s.PROCESS_LOCK.release()


def test_page_budget_is_enforced_before_external_processing():
    if not standard_status()['validation_available']:pytest.skip('Herramientas no disponibles')
    with f.open() as d:
        for _ in range(51):d.new_page()
        base=d.tobytes()
    with pytest.raises(DocumentError,match='50 páginas'):validate_standard(base,[])


@pytest.mark.parametrize('mutation',['failed_job','inconsistent','not_normal','missing_rule','truncated','wrong_profile'])
def test_incomplete_or_inconsistent_validator_report_never_counts_as_success(mutation):
    xml='''<report><jobs><job><validationReport jobEndStatus="normal" profileName="PDF/A-2b validation profile" isCompliant="true"><details passedRules="1" failedRules="0" passedChecks="1" failedChecks="0"/></validationReport></job></jobs><batchSummary totalJobs="1" failedToParse="0" encrypted="0" outOfMemory="0" veraExceptions="0"><validationReports failedJobs="0" compliant="1" nonCompliant="0"/></batchSummary></report>'''
    if mutation=='failed_job':xml=xml.replace('failedJobs="0"','failedJobs="1"')
    elif mutation=='inconsistent':xml=xml.replace('failedChecks="0"','failedChecks="1"')
    elif mutation=='not_normal':xml=xml.replace('jobEndStatus="normal"','jobEndStatus="aborted"')
    elif mutation=='missing_rule':xml=xml.replace('failedRules="0"','failedRules="1"').replace('failedChecks="0"','failedChecks="1"').replace('isCompliant="true"','isCompliant="false"')
    elif mutation=='wrong_profile':xml=xml.replace('PDF/A-2b validation profile','PDF/A-1b validation profile')
    else:xml=xml[:-20]
    with pytest.raises(DocumentError):parse_validation(xml.encode(),'2b')


def test_pdfa_copy_refuses_output_that_fails_validation(monkeypatch):
    import backend.standards as s
    if not standard_status()['conversion_available']:pytest.skip('Herramientas no disponibles')
    monkeypatch.setattr(s,'validate_file',lambda *args:{'compliant':False})
    with pytest.raises(DocumentError,match='no cumple'):s.archival_copy(document(),[])


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_archival_copy_keeps_visible_dimensions_and_text_on_rotated_cropped_pages(rotation,crop):
    if not standard_status()['conversion_available']:pytest.skip('Herramientas no disponibles')
    base=document(rotation=rotation,crop=crop);out,report=archival_copy(base,[])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert list(a[0].rect)==pytest.approx(list(b[0].rect),abs=.1)
        assert a[0].get_text().strip()==b[0].get_text().strip()
    assert report['visible_sizes_preserved'] and report['preview']['source'].startswith('data:image/png;base64,')


def test_archival_unicode_embedded_fonts_and_alpha_image_remain_searchable_at_native_resolution():
    if not standard_status()['conversion_available']:pytest.skip('Herramientas no disponibles')
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='Unicode',fontfile=str(Path('resources/fonts/DejaVuSans.ttf').resolve()));p.insert_text((40,80),'Revisión técnica Ω',fontname='Unicode')
        pix=f.Pixmap(f.csRGB,(0,0,120,80),True);pix.clear_with(180);pix.set_alpha(bytes([128])*(120*80));p.insert_image(f.Rect(40,120,280,280),stream=pix.tobytes('png'));base=d.tobytes()
    out,report=archival_copy(base,[])
    with f.open(stream=out) as d:
        assert 'Revisión técnica Ω' in d[0].get_text() and any(row[2:4]==(120,80) for row in d[0].get_images())
    assert report['validation']['compliant']
