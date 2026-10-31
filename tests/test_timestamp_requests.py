import asyncio,hashlib
from io import BytesIO
import pymupdf as f
import pytest
from pyhanko.pdf_utils.reader import PdfFileReader
from backend import timestamp_authority as module
from backend.timestamp_authority import VerifiedTimeStamper,settings
from backend.digital_signatures import sign_document,verify_signatures,timestamp_document
from backend.engine import DocumentError
from tests.signature_samples import document,identity
from tests.timestamp_samples import authority,transport

URL={'url':'https://tsa.synthetic.invalid/rfc3161'}


def test_document_stamp_request_validation_incremental_bytes_and_explicit_trust(monkeypatch):
 tsa,root=authority();requests=[];monkeypatch.setattr(module,'exchange',transport(tsa,requests));base=document()
 plan=timestamp_document(base,[],URL,root,True);assert plan['network_used'] is False and not requests
 result=timestamp_document(base,[],URL,root);assert result.startswith(base) and len(requests)==2
 for req in requests:
  assert req['nonce'].native.bit_length()==128 and req['message_imprint']['hash_algorithm']['algorithm'].native=='sha256' and len(req['message_imprint']['hashed_message'].native)==32
 report=verify_signatures(result,[],root);row=report['signatures'][0];assert row['type']=='document_timestamp' and row['intact'] and row['timestamp']['time_accepted_offline']
 assert row['coverage']=='ENTIRE_FILE' and not report['network_used'] and not row['timestamp']['revocation_checked']
 with f.open(stream=base) as a,f.open(stream=result) as b:assert [p.get_pixmap().samples for p in a]==[p.get_pixmap().samples for p in b]
 assert not verify_signatures(result,[])['signatures'][0]['timestamp']['time_accepted_offline']


def test_sign_with_timestamp_and_append_document_stamp_preserve_prior_approval(monkeypatch):
 tsa,root=authority();monkeypatch.setattr(module,'exchange',transport(tsa));p12,signer_root,_=identity();base=document()
 result=sign_document(base,[],p12,'prueba',{},tsa=URL,tsa_trust=root)
 row=verify_signatures(result,[],root+signer_root)['signatures'][0];assert row['chain_accepted'] and row['timestamp']['time_accepted_offline']
 stamped=timestamp_document(result,[],URL,root);assert stamped.startswith(result)
 report=verify_signatures(stamped,[],root+signer_root);assert len(report['signatures'])==2 and all(r['intact'] and r['cryptographically_valid'] for r in report['signatures'])
 assert report['signatures'][0]['coverage']=='ENTIRE_REVISION' and report['signatures'][1]['coverage']=='ENTIRE_FILE'


@pytest.mark.parametrize('mutation',['nonce','imprint','algorithm','signature','reject'])
def test_invalid_responses_never_produce_output(monkeypatch,mutation):
 tsa,root=authority();monkeypatch.setattr(module,'exchange',transport(tsa,mutation=mutation))
 with pytest.raises(DocumentError):timestamp_document(document(),[],URL,root)


@pytest.mark.parametrize('kind',['trust','eku','future'])
def test_tsa_certificate_and_clock_policy_are_enforced(monkeypatch,kind):
 tsa,root=authority(wrong_eku=kind=='eku',future=kind=='future');monkeypatch.setattr(module,'exchange',transport(tsa))
 if kind=='trust':root=identity()[1]
 with pytest.raises(DocumentError):timestamp_document(document(),[],URL,root)


@pytest.mark.parametrize('url',['http://example.com','https://localhost/','https://127.0.0.1/','https://[::1]/','https://192.168.1.2/','https://169.254.169.254/','https://user:secret@example.com/','https://example.com/#fragment','https://example.com:99999/','https://example.com/\n'])
def test_unsafe_endpoints_rejected_without_network(url):
 with pytest.raises(DocumentError):settings({'url':url},authority()[1])


def test_malformed_large_response_and_request_limits(monkeypatch):
 async def bad(*a):return b'not ASN1'
 monkeypatch.setattr(module,'exchange',bad);tsa=VerifiedTimeStamper(URL,authority()[1])
 for _ in range(3):
  with pytest.raises(DocumentError):asyncio.run(tsa.async_timestamp(hashlib.sha256(b'x').digest(),'sha256'))
 with pytest.raises(DocumentError,match='límite'):asyncio.run(tsa.async_timestamp(hashlib.sha256(b'x').digest(),'sha256'))
 with pytest.raises(DocumentError):settings(URL,b'')


def test_document_seal_chain_and_changed_content_never_get_false_current_coverage(monkeypatch):
 tsa,root=authority();monkeypatch.setattr(module,'exchange',transport(tsa));base=document()
 first=timestamp_document(base,[],URL,root);second=timestamp_document(first,[],URL,root)
 assert second.startswith(first)
 rows=verify_signatures(second,[],root)['signatures'];assert len(rows)==2 and rows[-1]['covers_current_file'] and not rows[0]['covers_current_file']
 changed=bytearray(second);changed[7]=ord('6') if changed[7]!=ord('6') else ord('7')
 report=verify_signatures(bytes(changed),[],root);assert any(r.get('intact') is False for r in report['signatures'])


def test_api_timestamp_review_has_no_network_and_signing_accepts_explicit_tsa(monkeypatch):
 import json
 from fastapi.testclient import TestClient
 from backend.app import app
 tsa,root=authority();calls=[];monkeypatch.setattr(module,'exchange',transport(tsa,calls));p12,_,_=identity()
 with TestClient(app) as client:
  doc=client.post('/api/documents',files={'file':('input.pdf',document(),'application/pdf')}).json();url='/api/documents/'+doc['id']
  payload={'tsa':URL,'review':True}
  reviewed=client.post(url+'/document-timestamp',files={'tsa_trust':('tsa.pem',root)},data={'payload':json.dumps(payload)})
  assert reviewed.status_code==200 and reviewed.json()['network_used'] is False and not calls
  result=client.post(url+'/document-timestamp',files={'tsa_trust':('tsa.pem',root)},data={'payload':json.dumps({**payload,'review':False})})
  assert result.status_code==200 and len(calls)==2 and verify_signatures(result.content,[],root)['signatures'][0]['timestamp']['time_accepted_offline']
  signed=client.post(url+'/digital-sign',files={'file':('identity.p12',p12),'tsa_trust':('tsa.pem',root)},data={'password':'prueba','payload':json.dumps({'tsa':URL})})
  assert signed.status_code==200 and verify_signatures(signed.content,[],root)['signatures'][0]['timestamp']['time_accepted_offline']
  assert client.post(url+'/document-timestamp',data={'payload':json.dumps(payload)}).status_code==422


def test_transport_global_timeout_also_covers_resolution(monkeypatch):
 import time
 async def slow(*a):await asyncio.sleep(1)
 monkeypatch.setattr(module,'_check_public_host',slow);monkeypatch.setattr(module,'REQUEST_TIMEOUT',.02);start=time.monotonic()
 with pytest.raises(DocumentError,match='HTTPS'):asyncio.run(module.exchange(URL['url'],b'request'))
 assert time.monotonic()-start<1


def test_actual_https_transport_requires_tls_trust_and_validates_rfc3161(monkeypatch,tmp_path):
 import ssl,threading,ipaddress
 from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
 from datetime import datetime,timezone,timedelta
 from cryptography import x509
 from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
 from cryptography.hazmat.primitives import hashes,serialization
 from cryptography.hazmat.primitives.asymmetric import rsa
 import aiohttp
 tsa,tsa_root=authority();now=datetime.now(timezone.utc);key=rsa.generate_private_key(public_exponent=65537,key_size=2048);name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Local test HTTPS server')])
 cert=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True,path_length=None),True).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),False).sign(key,hashes.SHA256())
 certfile=tmp_path/'tls.pem';keyfile=tmp_path/'tls-key.pem';certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM));keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
 response=transport(tsa)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_POST(self):
   raw=self.rfile.read(int(self.headers['Content-Length']));assert self.headers['Content-Type']=='application/timestamp-query'
   data=asyncio.run(response('',raw));self.send_response(200);self.send_header('Content-Type','application/timestamp-reply');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(certfile,keyfile);server.socket=ctx.wrap_socket(server.socket,server_side=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 async def local_test_only(*a):return None
 monkeypatch.setattr(module,'_check_public_host',local_test_only);monkeypatch.setenv('NO_PROXY','127.0.0.1,localhost')
 stamper=VerifiedTimeStamper(URL,tsa_root);stamper.url=f'https://127.0.0.1:{server.server_port}/rfc3161'
 try:
  with pytest.raises(DocumentError,match='HTTPS'):asyncio.run(stamper.async_timestamp(hashlib.sha256(b'tls test').digest(),'sha256'))
  original=aiohttp.ClientSession;clientctx=ssl.create_default_context(cafile=str(certfile))
  monkeypatch.setattr(aiohttp,'ClientSession',lambda **kw:original(connector=aiohttp.TCPConnector(ssl=clientctx),**kw))
  token=asyncio.run(stamper.async_timestamp(hashlib.sha256(b'tls test').digest(),'sha256'))
  assert token and stamper.last_report['time_accepted_offline'] and stamper.last_report['request_nonce_checked'] and not stamper.last_report['revocation_checked']
 finally:server.shutdown();server.server_close();thread.join(timeout=3)


@pytest.mark.parametrize('kind',['redirect','html','compressed','length','chunks'])
def test_https_transport_rejects_redirects_wrong_content_and_oversized_reply(monkeypatch,kind):
 async def public(*a):pass
 class Content:
  async def iter_chunked(self,size):yield b'x'*(module.MAX_RESPONSE+1 if kind=='chunks' else 1)
 class Response:
  status=302 if kind=='redirect' else 200
  headers={'Content-Type':'text/html' if kind=='html' else 'application/timestamp-reply','Content-Encoding':'gzip' if kind=='compressed' else 'identity'}
  content_length=module.MAX_RESPONSE+1 if kind=='length' else None
  content=Content()
  async def __aenter__(self):return self
  async def __aexit__(self,*a):pass
 class Session:
  def __init__(self,**kw):assert kw['trust_env'] and kw['auto_decompress'] is False
  async def __aenter__(self):return self
  async def __aexit__(self,*a):pass
  def post(self,*a,**kw):assert kw['allow_redirects'] is False and kw['headers']['Content-Type']=='application/timestamp-query';return Response()
 monkeypatch.setattr(module,'_check_public_host',public);monkeypatch.setattr(module.aiohttp,'ClientSession',Session)
 with pytest.raises(DocumentError):asyncio.run(module.exchange(URL['url'],b'request'))


def test_public_hostname_resolving_to_private_address_is_rejected(monkeypatch):
 async def run():
  loop=asyncio.get_running_loop()
  async def resolve(*a,**kw):return [(2,1,6,'',('127.0.0.1',443))]
  monkeypatch.setattr(loop,'getaddrinfo',resolve)
  await module._check_public_host('public-name.example',443)
 with pytest.raises(DocumentError,match='local|reservada'):asyncio.run(run())


def test_strong_imprint_with_weak_cms_digest_is_not_accepted(monkeypatch):
 tsa,root=authority();monkeypatch.setattr(tsa,'override_md','sha1');monkeypatch.setattr(module,'exchange',transport(tsa))
 with pytest.raises(DocumentError):timestamp_document(document(),[],URL,root)


@pytest.mark.parametrize('document_seal',[False,True])
@pytest.mark.parametrize('kind',['crl','ocsp'])
@pytest.mark.parametrize('state,expected',[('good','accepted_offline'),('revoked','revoked'),('stale','unknown')])
def test_tsa_local_revocation_is_separate_fresh_and_offline(monkeypatch,document_seal,kind,state,expected):
 import socket
 from tests.timestamp_samples import revocation
 tsa,root=authority();monkeypatch.setattr(module,'exchange',transport(tsa))
 pdf=timestamp_document(document(),[],URL,root) if document_seal else sign_document(document(),[],identity()[0],'prueba',{},tsa=URL,tsa_trust=root)
 proof=revocation(state,kind)
 monkeypatch.setattr(socket,'create_connection',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Network forbidden')))
 report=verify_signatures(pdf,[],root,[proof]);ts=report['signatures'][0]['timestamp']
 assert ts['revocation']['status']==expected
 assert ts['revocation_checked']==(expected in ['accepted_offline','revoked'])
 assert ts['time_accepted_offline']==(expected=='accepted_offline')
 assert not report['network_used']
 if not document_seal:assert report['signatures'][0]['revocation']['status']=='unknown'


def test_conflicting_tsa_evidence_never_hides_revocation(monkeypatch):
 from tests.timestamp_samples import revocation
 tsa,root=authority();monkeypatch.setattr(module,'exchange',transport(tsa));pdf=timestamp_document(document(),[],URL,root)
 row=verify_signatures(pdf,[],root,[revocation('good','ocsp'),revocation('revoked','crl')])['signatures'][0]
 assert row['status']=='certificate_revoked' and row['timestamp']['revocation']['status']=='revoked' and not row['timestamp']['time_accepted_offline']


def test_bad_embedded_timestamp_cannot_be_hidden_by_revocation_or_resigned(monkeypatch):
 from asn1crypto import cms
 from tests.timestamp_samples import revocation
 tsa,root=authority();requests=[];monkeypatch.setattr(module,'exchange',transport(tsa,requests));p12,signer_root,_=identity()
 pdf=sign_document(document(),[],p12,'prueba',{},tsa=URL,tsa_trust=root)
 signature=PdfFileReader(BytesIO(pdf)).embedded_signatures[0];old=bytes(signature.sig_object['/Contents']);outer=cms.ContentInfo.load(old)
 token=outer['content']['signer_infos'][0]['unsigned_attrs'][0]['values'][0];si=token['content']['signer_infos'][0];value=si['signature'].native;si['signature']=bytes([value[0]^1])+value[1:]
 encoded=old.hex().encode();replacement=outer.dump().ljust(len(old),b'\0').hex().encode()
 if encoded not in pdf:encoded=encoded.upper();replacement=replacement.upper()
 assert pdf.count(encoded)==1;changed=pdf.replace(encoded,replacement,1)
 row=verify_signatures(changed,[],root+signer_root,[revocation()])['signatures'][0]
 assert row['intact'] and row['cryptographically_valid'] and row['timestamp']['status']=='integrity_failed'
 with pytest.raises(DocumentError,match='firmas o sellos'):timestamp_document(changed,[],URL,root,True)
 with pytest.raises(DocumentError,match='firmas o sellos'):sign_document(changed,[],p12,'prueba',{},review=True)
 assert len(requests)==2
