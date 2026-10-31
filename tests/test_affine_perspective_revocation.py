"""Independent source/render, projective OCR and offline PKI checks."""
import hashlib,math,socket
from datetime import datetime,timedelta,timezone
from functools import lru_cache
import pymupdf as f
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID,AuthorityInformationAccessOID
from backend.engine import DocumentError
from backend.affine_reflow import reflow
from backend.native_text import native_model
from backend.digital_signatures import sign_document,verify_signatures
from backend.table_regions import extract
from backend.scan_geometry import homography
from tests.test_table_regions import source,VALUES


def affine(angle=25,reflect=False):
    with f.open() as doc:
        p=doc.new_page(width=650,height=650);p.insert_text((40,55),'Neighbor untouched')
        p.insert_text((170,190),'ALPHA BETA GAMMA',fontsize=14,morph=(f.Point(170,190),f.Matrix(-1 if reflect else 1,0,0,1,0,0)*f.Matrix(angle)))
        doc.new_page().insert_text((40,50),'Other page unchanged');return doc.tobytes()


def target(base):
    with f.open(stream=base) as d:
        _,rows=native_model(d,0,d[0].rect);row=next(r for r in rows if r['text']=='ALPHA BETA GAMMA');r=f.Rect(row['bbox']);return [r.x0,r.y0,r.width,r.height],row['id']


@pytest.mark.parametrize('angle,reflect',[(25,False),(-20,False),(0,True),(15,True),(0,False)])
def test_affine_original_reflow_stays_editable_and_preserves_neighbors(angle,reflect):
    base=affine(angle,reflect);box,ident=target(base);text='ALPHA BETA\nGAMMA ALPHA';data,report=reflow(base,[],0,box,ident,text,110,130)
    assert report['lines']>=2 and report['preserves_affine']
    with f.open(stream=base) as a,f.open(stream=data) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].get_pixmap(clip=f.Rect(0,0,600,90)).samples==b[0].get_pixmap(clip=f.Rect(0,0,600,90)).samples
        _,rows=native_model(b,0,b[0].rect)
        edited=[r for r in rows if r['text'] in ['ALPHA BETA','GAMMA ALPHA']]
        assert len(edited)==2 and all(r['editable'] for r in edited)
        assert b[0].get_fonts()[0][3]==a[0].get_fonts()[0][3]


def test_affine_overflow_and_collision_are_atomic():
    base=affine();box,ident=target(base)
    for text,width,height in [('ALPHA '*30,60,20),('ALPHA',float('nan'),100)]:
        with pytest.raises(DocumentError):reflow(base,[],0,box,ident,text,width,height)
    with f.open(stream=base) as d:
        p=d[0];p.draw_rect(f.Rect(140,200,300,400));blocked=d.tobytes()
    box,ident=target(blocked)
    with pytest.raises(DocumentError,match='cruza'):reflow(blocked,[],0,box,ident,'ALPHA\nBETA\nGAMMA',100,200)


def perspective_table():
    from PIL import Image
    with f.open(stream=source()) as doc:pix=doc[0].get_pixmap(matrix=f.Matrix(2,2),clip=f.Rect(40,80,490,230),alpha=False)
    # Inverse map: page quadrilateral to original rectangular table image.
    points=[[55,90],[490,65],[465,255],[80,235]]
    h=homography([[p[0]*2,p[1]*2] for p in points])
    a,b,c,d,e,g,h6,h7=h
    det=a*(e-g*h7)-b*(d-g*h6)+c*(d*h7-e*h6)
    inv=[(e-g*h7)/det,(c*h7-b)/det,(b*g-c*e)/det,(g*h6-d)/det,(a-c*h6)/det,(c*d-a*g)/det,(d*h7-e*h6)/det,(b*h6-a*h7)/det,(a*e-b*d)/det]
    inv=[v/inv[8] for v in inv]
    coeff=tuple([v*pix.width for v in inv[:3]]+[v*pix.height for v in inv[3:6]]+inv[6:8])
    with Image.frombytes('RGB',(pix.width,pix.height),pix.samples) as img:
        corrected=img.transform((1080,650),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC,fillcolor='white')
        import io
        out=io.BytesIO();corrected.save(out,format='PNG')
    with f.open() as d:
        p=d.new_page(width=540,height=325);p.insert_image(p.rect,stream=out.getvalue());return d.tobytes(),points


def test_real_perspective_ocr_grid_and_source_mapping():
    base,quad=perspective_table();digest=hashlib.sha256(base).digest();r=extract(base,[],0,[40,50,470,220],language='eng',dpi=300,correction={'quad':quad})
    assert r['cells']==VALUES and r['coordinate_space']=='rectified' and r['review_required'] and not r['source_modified']
    assert r['preview'].startswith('data:image/png;base64,') and all(len(w['source_quad'])==4 for w in r['words'])
    assert hashlib.sha256(base).digest()==digest and r['page']==0
    for word in r['words']:
        assert all(40<=x<=510 and 50<=y<=270 for x,y in word['source_quad'])


@pytest.mark.parametrize('quad',[[[10,10]]*4,[[55,90],[490,65],[80,235],[465,255]],[[0,0],[490,65],[465,255],[80,235]]])
def test_perspective_bad_corners_rejected(quad):
    with pytest.raises(DocumentError):extract(source(),[],0,[40,50,470,220],language='eng',correction={'quad':quad})


@lru_cache(maxsize=1)
def pki_material():
    now=datetime.now(timezone.utc);key=rsa.generate_private_key(public_exponent=65537,key_size=2048);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Local evidence test root')])
    root=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=2)).not_valid_after(now+timedelta(days=100)).add_extension(x509.BasicConstraints(ca=True,path_length=1),True).add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True).sign(key,hashes.SHA256())
    leafkey=rsa.generate_private_key(public_exponent=65537,key_size=2048);subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Local evidence signer')])
    leaf=x509.CertificateBuilder().subject_name(subject).issuer_name(name).public_key(leafkey.public_key()).serial_number(37).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=40)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True).add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),True).add_extension(x509.AuthorityInformationAccess([x509.AccessDescription(AuthorityInformationAccessOID.OCSP,x509.UniformResourceIdentifier('http://127.0.0.1:9/ocsp'))]),False).sign(key,hashes.SHA256())
    return key,root,leafkey,leaf


@lru_cache(maxsize=8)
def pki(state='good',proof='crl'):
    now=datetime.now(timezone.utc);key,root,leafkey,leaf=pki_material();name=root.subject
    before=now-timedelta(days=3) if state=='stale' else now-timedelta(minutes=3);after=now-timedelta(days=2) if state=='stale' else now+timedelta(days=1)
    if proof=='crl':
        builder=x509.CertificateRevocationListBuilder().issuer_name(name).last_update(before).next_update(after)
        if state=='revoked':builder=builder.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(37).revocation_date(now-timedelta(hours=1)).build())
        proofdata=builder.sign(key,hashes.SHA256()).public_bytes(serialization.Encoding.DER)
    else:
        from cryptography.x509 import ocsp
        builder=ocsp.OCSPResponseBuilder().add_response(leaf,root,hashes.SHA256(),ocsp.OCSPCertStatus.REVOKED if state=='revoked' else ocsp.OCSPCertStatus.GOOD,before,after,now-timedelta(hours=1) if state=='revoked' else None,x509.ReasonFlags.key_compromise if state=='revoked' else None).responder_id(ocsp.OCSPResponderEncoding.HASH,root)
        proofdata=builder.sign(key,hashes.SHA256()).public_bytes(serialization.Encoding.DER)
    identity=pkcs12.serialize_key_and_certificates(b'test',leafkey,leaf,[root],serialization.NoEncryption())
    return identity,root.public_bytes(serialization.Encoding.PEM),proofdata


@pytest.mark.parametrize('proof',['crl','ocsp'])
@pytest.mark.parametrize('state,expected',[('good','accepted_offline'),('revoked','revoked'),('stale','unknown')])
def test_revocation_real_evidence_freshness_and_no_network(monkeypatch,state,expected,proof):
    identity,trust,evidence=pki(state,proof);base=sign_document(source(),[],identity,'',{})
    def offline(*a,**kw):raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket,'create_connection',offline)
    r=verify_signatures(base,[],trust,[evidence]);row=r['signatures'][0]
    assert row['revocation']['status']==expected,r
    assert r['revocation_checked']==(expected!='unknown') and not r['network_used']
    assert row['intact'] and row['cryptographically_valid']
    if state=='revoked':assert row['status']=='certificate_revoked'
    if state=='stale':assert row['status']=='revocation_unknown'


def test_revocation_untrusted_wrong_issuer_and_tampered_evidence_not_accepted():
    identity,trust,evidence=pki();base=sign_document(source(),[],identity,'',{})
    assert verify_signatures(base,[],b'',[evidence])['signatures'][0]['revocation']['status']=='unknown'
    wrong=pki('stale')[2]
    assert verify_signatures(base,[],trust,[wrong])['signatures'][0]['revocation']['status']=='unknown'
    broken=evidence[:-1]+bytes([evidence[-1]^1])
    assert verify_signatures(base,[],trust,[broken])['signatures'][0]['revocation']['status']=='unknown'
    for raw in [b'garbage',b'-----BEGIN PRIVATE KEY-----\nAA==\n-----END PRIVATE KEY-----',b'']:
        with pytest.raises(DocumentError):verify_signatures(base,[],trust,[raw])


@pytest.mark.parametrize('mode',['form','direct','tm'])
@pytest.mark.parametrize('kind',['base','ttf','cff','cid'])
@pytest.mark.parametrize('linear',[(1,.3,.2,1),(.7,.3,.2,1.4),(0,1,-1,0),(-1,0,0,1)])
def test_affine_reflow_original_font_matrix_and_shared_forms(mode,kind,linear):
    from tests.test_affine_text_editing import source as transformed,box_for
    from backend.styled_text import inspect_styled,replace_styled
    base=transformed(linear,kind,mode);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0]
    out,report=reflow(base,[],0,box,row['id'],'HELLO\nTEXT HELLO',180,160)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].get_text().count('HELLO TEXT')==(1 if mode=='form' else 0)
        assert sorted(a.extract_font(v[0])[3] for v in a[0].get_fonts())==sorted(b.extract_font(v[0])[3] for v in b[0].get_fonts())
        _,rows=native_model(b,0,b[0].rect);edited=next(r for r in rows if r['text']=='TEXT HELLO')
        assert edited['editable'],edited['reason']
        r=f.Rect(edited['bbox']);editbox=[r.x0,r.y0,r.width,r.height]
    again=replace_styled(out,[],0,editbox,[{'id':edited['id'],'text':'TEXT HELL'}])
    with f.open(stream=again) as d:assert 'TEXT HELL' in d[0].get_text()


def test_affine_table_and_evidence_api_roundtrip():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        base=affine();box,ident=target(base);doc=client.post('/api/documents',files={'file':('Affine.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        payload={'page':0,'box':box,'id':ident,'text':'ALPHA\nBETA','width':120,'height':100}
        assert client.post(url+'/reflow-affine',json={**payload,'preview':True}).json()['lines']==2
        edited=client.post(url+'/reflow-affine',json=payload);assert edited.status_code==200,edited.text
        assert edited.json()['id']!=doc['id']
        base,quad=perspective_table();doc=client.post('/api/documents',files={'file':('Perspective.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=client.post(url+'/extract-table-region',json={'page':0,'box':[40,50,470,220],'correction':{'quad':quad},'language':'eng','dpi':300});assert r.status_code==200,r.text
        assert r.json()['cells']==VALUES
        identity,trust,proof=pki();signed=sign_document(source(),[],identity,'',{});doc=client.post('/api/documents',files={'file':('Signed.pdf',signed,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=client.post(url+'/verify-signatures',files=[('trust',('Trust.pem',trust,'application/octet-stream')),('evidence',('Proof.crl',proof,'application/octet-stream'))]);assert r.status_code==200,r.text
        assert r.json()['revocation_checked'] and r.json()['signatures'][0]['revocation']['status']=='accepted_offline'
        assert client.post(url+'/verify-signatures',files={'evidence':('Bad.der',b'Bad','application/octet-stream')}).status_code==422


def test_conflicting_crl_and_ocsp_never_hide_revocation():
    identity,trust,good=pki('good','ocsp');revoked=pki('revoked','crl')[2];base=sign_document(source(),[],identity,'',{})
    r=verify_signatures(base,[],trust,[good,revoked])
    assert r['signatures'][0]['status']=='certificate_revoked'
    assert r['signatures'][0]['revocation']['status']=='revoked'


def test_affine_reflow_rejects_new_overlapping_character_advances():
    with f.open() as d:
        p=d.new_page();p.insert_text((100,150),'WWWW',fontsize=14)
        xref=p.get_contents()[0];d.update_stream(xref,d.xref_stream(xref).replace(b'14 Tf',b'14 Tf -5 Tc'));base=d.tobytes()
        _,rows=native_model(d,0,p.rect);row=rows[0];assert row['editable']
        r=f.Rect(row['bbox']);box=[r.x0,r.y0,r.width,r.height]
    with pytest.raises(DocumentError,match='superpuestos'):reflow(base,[],0,box,row['id'],'WiiW',100,100)
