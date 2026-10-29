"""Real synthetic certificates, CMS signatures, incremental revisions and offline trust."""
from io import BytesIO
from pathlib import Path
import json,shutil,socket,subprocess
import pymupdf as f
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography import x509
from fastapi.testclient import TestClient
from pyhanko.sign import signers,fields
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from backend.app import app
from backend.certificates import inspect_identity,trust_certificates
from backend.digital_signatures import sign_document,verify_signatures
from backend.engine import DocumentError,export_pdf
from tests.signature_samples import identity,document


def sign(base=None,config=None,kind='rsa'):
    p12,_,_=identity(kind);return sign_document(base or document(),[],p12,'prueba',config or {})


@pytest.mark.parametrize('kind',['rsa','ec'])
def test_real_signature_verifies_and_trust_is_explicit(kind):
    p12,root,_=identity(kind);base=document();out=sign(base,kind=kind)
    assert out.startswith(base) and out!=base
    report=verify_signatures(out,[]);r=report['signatures'][0]
    assert report['count']==1 and r['intact'] and r['cryptographically_valid'] and r['covers_current_file']
    assert r['status']=='integrity_only' and not r['chain_accepted'] and not report['revocation_checked'] and not report['network_used']
    trusted=verify_signatures(out,[],root)['signatures'][0]
    assert trusted['chain_accepted'] and trusted['status']=='chain_accepted_offline' and trusted['digest_algorithm']=='sha256'
    assert trusted['certificate']['common_name']=='María Pérez · Prueba'
    assert trusted['reported_signing_time'] and not trusted['timestamp_present']
    with f.open(stream=out) as d:
        assert d.get_sigflags()>0 and 'Documento para firmar' in d[0].get_text()
    with pytest.raises(DocumentError):export_pdf(out,[{'type':'note','page':0,'point':[20,20],'content':'No'}])


def test_signing_review_does_not_sign_and_never_returns_key_material():
    p12,_,_=identity(password='SecretoSoloP12_029!');base=document();before=base
    report=sign_document(base,[],p12,'SecretoSoloP12_029!',{'reason':'Aprobación','location':'Lima'},review=True)
    assert report['certificate']['can_sign'] and report['digest_algorithm']=='sha256' and base==before
    text=json.dumps(report);assert 'SecretoSoloP12_029!' not in text and 'PRIVATE KEY' not in text
    assert verify_signatures(base,[])['count']==0


@pytest.mark.parametrize('crop',[False,True])
def test_visible_signature_bounds_unicode_and_unaffected_page(crop):
    base=document(crop=crop);out=sign(base,{'visible':True,'page':0,'box':[40,350,320,90],'reason':'Revisión técnica','location':'Perú'})
    with f.open(stream=base) as a,f.open(stream=out) as b:
        p=b[0];widget=list(p.widgets())[0];assert list(widget.rect)==pytest.approx([40,350,360,440],abs=.01)
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert 'María Pérez' in p.get_text() and 'Firmado digitalmente' in p.get_text()
        assert p.cropbox==a[0].cropbox
    assert verify_signatures(out,[])['signatures'][0]['intact']


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_invisible_signature_supports_rotated_pages_without_changing_pixels(rotation):
    base=document(rotation=rotation);out=sign(base)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[1].get_pixmap().samples==b[1].get_pixmap().samples and b[0].rotation==rotation


def test_second_signature_retains_both_signatures_and_earlier_revision_coverage():
    first=sign();second=sign(first,{'visible':True,'page':1,'box':[50,400,300,80]});report=verify_signatures(second,[],identity()[1])
    assert second.startswith(first) and report['count']==2
    a,b=report['signatures'];assert a['intact'] and b['intact'] and a['chain_accepted'] and b['chain_accepted']
    assert a['coverage']=='ENTIRE_REVISION' and a['modification_level']=='FORM_FILLING' and a['allowed_changes']
    assert b['covers_current_file'] and b['modification_level']=='NONE'


def test_byte_tampering_and_post_signature_content_changes_are_not_accepted():
    first=sign();tampered=first.replace(b'Documento',b'Xocumento',1)
    # Source text may be Flate compressed, so alter an uncompressed signed header byte instead.
    if tampered==first:tampered=first.replace(b'%PDF-1.7',b'%PDF-1.6',1)
    assert tampered!=first
    report=verify_signatures(tampered,[]);assert report['signatures'][0]['status']=='integrity_failed'
    with pytest.raises(DocumentError):sign(tampered)
    writer=IncrementalPdfFileWriter(BytesIO(first));writer.root['/Lang']=__import__('pyhanko.pdf_utils.generic',fromlist=['TextStringObject']).TextStringObject('xx-YY');writer.update_root();stream=BytesIO();writer.write(stream);modified=stream.getvalue()
    row=verify_signatures(modified,[])['signatures'][0];assert not row['covers_current_file'] and row['status'] in ['changes_require_review','inconclusive']
    with pytest.raises(DocumentError):sign(modified)


def test_certified_documents_are_protected_against_new_signatures():
    p12,_,_=identity();signer=signers.SimpleSigner.load_pkcs12_data(p12,[],b'prueba')
    writer=IncrementalPdfFileWriter(BytesIO(document()));out=signers.sign_pdf(writer,signers.PdfSignatureMetadata(field_name='Certificada',certify=True,docmdp_permissions=fields.MDPPerm.NO_CHANGES),signer).getvalue()
    with pytest.raises(DocumentError,match='certificados'):sign(out)


@pytest.mark.parametrize('config',[
 {'visible':1},{'page':True},{'page':2},{'reason':'x\n'},{'location':'x'*201},{'extra':1},
 {'visible':True,'box':[10,10,100,20]},{'visible':True,'box':[450,600,300,80]},
 {'visible':True,'box':[20,20,float('nan'),80]},
])
def test_invalid_signature_settings_are_rejected(config):
    with pytest.raises(DocumentError):sign(config=config)


def test_encrypted_pdf_permissions_rotation_and_signature_limits(monkeypatch):
    base=document(rotation=90)
    with pytest.raises(DocumentError,match='sin giro'):sign(base,{'visible':True,'page':0,'box':[20,20,300,80]})
    with f.open(stream=document()) as d:
        encrypted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner')
        restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_PRINT)
    for data in [encrypted,restricted]:
        with pytest.raises(DocumentError):sign(data)
    monkeypatch.setattr('backend.digital_signatures.MAX_SIGNATURES',1)
    with pytest.raises(DocumentError,match='20 firmas'):sign(sign())


def test_offline_validation_never_fetches_network(monkeypatch):
    data=sign()
    def no_network(*args,**kwargs):raise AssertionError('Network forbidden in offline signature verification')
    monkeypatch.setattr(socket.socket,'connect',no_network);monkeypatch.setattr(socket,'create_connection',no_network)
    assert verify_signatures(data,[],identity()[1])['signatures'][0]['chain_accepted']
    assert verify_signatures(data,[])['signatures'][0]['intact']


def test_poppler_independently_checks_generated_signature(tmp_path):
    if not shutil.which('pdfsig'):pytest.skip('Poppler pdfsig no disponible')
    path=tmp_path/'signed.pdf';path.write_bytes(sign())
    output=subprocess.run(['pdfsig','-nocert',str(path)],capture_output=True,text=True,check=True).stdout
    assert 'Signature is Valid' in output and 'Total document signed' in output


def test_api_certificate_review_sign_verify_and_source_unchanged():
    p12,root,_=identity();base=document()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('source.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        inspected=client.post('/api/certificates/inspect',files={'file':('test.p12',p12)},data={'password':'prueba'});assert inspected.status_code==200 and inspected.json()['can_sign']
        config={'operations':[],'config':{'reason':'Revisión'},'review':True}
        review=client.post(url+'/digital-sign',files={'file':('test.p12',p12)},data={'password':'prueba','payload':json.dumps(config)});assert review.status_code==200
        signed=client.post(url+'/digital-sign',files={'file':('test.p12',p12)},data={'password':'prueba','payload':json.dumps(config|{'review':False})});assert signed.status_code==200 and signed.content.startswith(base)
        assert client.post(url+'/verify-signatures',data={'payload':'{}'}).json()['count']==0
        incoming=client.post('/api/documents',files={'file':('signed.pdf',signed.content,'application/pdf')}).json();assert incoming['signed']
        verified=client.post('/api/documents/'+incoming['id']+'/verify-signatures',files={'trust':('root.pem',root)},data={'payload':'{}'});assert verified.status_code==200 and verified.json()['signatures'][0]['chain_accepted']
        bad=client.post(url+'/digital-sign',files={'file':('test.p12',p12)},data={'password':'incorrecta'});assert bad.status_code==422 and 'incorrecta' not in bad.text
        assert client.post(url+'/verify-signatures',data={'payload':'[]'}).status_code==422


@pytest.mark.parametrize('state,usage,kind,ca',[('expired','sign','rsa',False),('future','sign','rsa',False),('valid','server','rsa',False),('valid','absent','rsa',False),('valid','sign','weak',False),('valid','sign','rsa',True)])
def test_certificate_restrictions_are_reported_and_block_signing(state,usage,kind,ca):
    p12,_,_=identity(kind,state,usage,ca=ca);info=inspect_identity(p12,'prueba');assert not info['can_sign'] and info['reason']
    with pytest.raises(DocumentError):sign_document(document(),[],p12,'prueba',{})


def test_passwordless_and_commitment_certificates_and_invalid_uploads():
    for password,usage in [('', 'sign'),('prueba','commitment')]:
        p12,_,_=identity(password=password,usage=usage);assert inspect_identity(p12,password)['can_sign'];assert verify_signatures(sign_document(document(),[],p12,password,{}),[])['signatures'][0]['intact']
    with pytest.raises(DocumentError):inspect_identity(b'bad','')
    with pytest.raises(DocumentError):inspect_identity(identity()[0],'wrong')
    with pytest.raises(DocumentError):trust_certificates(b'-----BEGIN PRIVATE KEY-----')
    with pytest.raises(DocumentError):trust_certificates(b'invalid')
    cert=x509.load_pem_x509_certificate(identity()[1]);assert len(trust_certificates(cert.public_bytes(serialization.Encoding.DER)))==1


def test_wrong_trust_anchor_never_accepts_chain_even_with_matching_issuer_name():
    data=sign();wrong=identity(kind='ec')[1];row=verify_signatures(data,[],wrong)['signatures'][0]
    assert row['intact'] and row['cryptographically_valid'] and not row['chain_accepted'] and row['status']=='integrity_only'


@pytest.mark.parametrize('state,ca',[('expired',False),('valid',True)])
def test_imported_signatures_with_unsuitable_certificate_do_not_gain_accepted_status(state,ca):
    p12,root,leaf=identity(state=state,ca=ca);signer=signers.SimpleSigner.load_pkcs12_data(p12,[],b'prueba')
    out=signers.sign_pdf(IncrementalPdfFileWriter(BytesIO(document())),signers.PdfSignatureMetadata(field_name='Importada'),signer).getvalue()
    row=verify_signatures(out,[],root+leaf)['signatures'][0]
    assert row['certificate_policy_problem'] and not row['chain_accepted'] and row['status']!='chain_accepted_offline'


def test_pending_text_edits_are_included_before_signing_and_source_remains_unchanged():
    from backend.engine import spans
    base=document()
    with f.open(stream=base) as d:span=spans(d[0])[0]
    operations=[{'type':'text','page':0,'span_id':span['id'],'text':'Documento aprobado'}]
    p12,root,_=identity();out=sign_document(base,operations,p12,'prueba',{})
    with f.open(stream=out) as d:assert 'Documento aprobado' in d[0].get_text() and 'Documento para firmar' not in d[0].get_text()
    with f.open(stream=base) as d:assert 'Documento para firmar' in d[0].get_text()
    assert verify_signatures(out,[],root)['signatures'][0]['chain_accepted']


def test_signed_project_preserves_exact_bytes_and_never_contains_identity(tmp_path):
    from backend.projects import build_project,read_project
    from zipfile import ZipFile
    data=sign();packed,_=build_project(data,[],{'name':'Firmado.pdf','page':0,'zoom':1,'base_changes':0})
    restored,ops,_=read_project(packed);assert restored==data and ops==[]
    assert verify_signatures(restored,[],identity()[1])['signatures'][0]['intact']
    with ZipFile(BytesIO(packed)) as z:
        assert set(z.namelist())=={'base.pdf','manifest.json','operations.json'}
        assert identity()[0] not in packed and b'PRIVATE KEY' not in packed


@pytest.mark.parametrize('which',['identity','trust'])
def test_oversized_credential_material_is_rejected(which):
    if which=='identity':
        with pytest.raises(DocumentError):inspect_identity(b'x'*(2*1024*1024+1),'')
    else:
        with pytest.raises(DocumentError):trust_certificates(b'x'*(512*1024+1))
