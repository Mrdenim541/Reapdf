"""Generated test-only RFC3161 authority; no production keys or service calls."""
from datetime import datetime,timezone,timedelta
from functools import lru_cache
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from asn1crypto import x509 as ax509,keys,tsp
from pyhanko.sign.timestamps import DummyTimeStamper
from pyhanko_certvalidator.registry import SimpleCertificateStore

@lru_cache(maxsize=8)
def materials(wrong_eku=False,future=False):
 now=datetime.now(timezone.utc);rk=rsa.generate_private_key(public_exponent=65537,key_size=2048);key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
 name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic RFC3161 Root')])
 root=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(rk.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=30)).add_extension(x509.BasicConstraints(ca=True,path_length=1),True).add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True).sign(rk,hashes.SHA256())
 leaf=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic RFC3161 TSA')])).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(hours=2)).not_valid_after(now+timedelta(days=10)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True).add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),True).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if wrong_eku else ExtendedKeyUsageOID.TIME_STAMPING]),True).sign(rk,hashes.SHA256())
 asn=lambda c:ax509.Certificate.load(c.public_bytes(serialization.Encoding.DER));store=SimpleCertificateStore();store.register(asn(root))
 stamper=DummyTimeStamper(asn(leaf),keys.PrivateKeyInfo.load(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),store,fixed_dt=now+timedelta(hours=1) if future else now)
 return stamper,root.public_bytes(serialization.Encoding.PEM),rk,root,leaf


def authority(wrong_eku=False,future=False):
 return materials(wrong_eku,future)[:2]


def revocation(state='good',kind='crl'):
 _,_,key,root,leaf=materials(False,False);now=datetime.now(timezone.utc);before=now-timedelta(days=3) if state=='stale' else now-timedelta(minutes=2);after=now-timedelta(days=2) if state=='stale' else now+timedelta(days=1)
 if kind=='crl':
  builder=x509.CertificateRevocationListBuilder().issuer_name(root.subject).last_update(before).next_update(after)
  if state=='revoked':builder=builder.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(leaf.serial_number).revocation_date(now-timedelta(minutes=10)).build())
  return builder.sign(key,hashes.SHA256()).public_bytes(serialization.Encoding.DER)
 from cryptography.x509 import ocsp
 builder=ocsp.OCSPResponseBuilder().add_response(leaf,root,hashes.SHA256(),ocsp.OCSPCertStatus.REVOKED if state=='revoked' else ocsp.OCSPCertStatus.GOOD,before,after,now-timedelta(minutes=10) if state=='revoked' else None,x509.ReasonFlags.key_compromise if state=='revoked' else None).responder_id(ocsp.OCSPResponderEncoding.HASH,root)
 return builder.sign(key,hashes.SHA256()).public_bytes(serialization.Encoding.DER)


def transport(stamper,requests=None,mutation=None):
 async def exchange(url,raw):
  req=tsp.TimeStampReq.load(raw,strict=True)
  if requests is not None:requests.append(req)
  response=await stamper.async_request_tsa_response(req)
  if mutation=='reject':return tsp.TimeStampResp({'status':{'status':'rejection'}}).dump()
  info=response['time_stamp_token']['content']['encap_content_info']['content'].parsed
  if mutation=='nonce':info['nonce']=req['nonce'].native+1
  if mutation=='imprint':info['message_imprint']['hashed_message']=b'X'*32
  if mutation=='algorithm':info['message_imprint']['hash_algorithm']['algorithm']='sha1'
  if mutation in ['nonce','imprint','algorithm']:response['time_stamp_token']['content']['encap_content_info']['content']=info
  if mutation=='signature':
   si=response['time_stamp_token']['content']['signer_infos'][0];sig=si['signature'].native;si['signature']=bytes([sig[0]^1])+sig[1:]
  return response.dump()
 return exchange
