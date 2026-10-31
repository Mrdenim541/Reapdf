from io import BytesIO
from datetime import datetime,timezone,timedelta
from functools import lru_cache
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from asn1crypto import x509 as ax509,keys
from pyhanko.sign import signers
from pyhanko.sign.timestamps import DummyTimeStamper
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko_certvalidator.registry import SimpleCertificateStore
from backend.digital_signatures import verify_signatures
from tests.signature_samples import identity,document


@lru_cache(maxsize=8)
def stamped(wrong_eku=False,future=False,weak_imprint=False):
    now=datetime.now(timezone.utc);rootkey=rsa.generate_private_key(public_exponent=65537,key_size=2048);key=rsa.generate_private_key(public_exponent=65537,key_size=2048);rootname=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic Timestamp Root')]);root=x509.CertificateBuilder().subject_name(rootname).issuer_name(rootname).public_key(rootkey.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=2)).not_valid_after(now+timedelta(days=20)).add_extension(x509.BasicConstraints(ca=True,path_length=1),True).add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),True).sign(rootkey,hashes.SHA256());cert=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Synthetic TSA')])).issuer_name(rootname).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=10)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True).add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),True).add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if wrong_eku else ExtendedKeyUsageOID.TIME_STAMPING]),True).sign(rootkey,hashes.SHA256());asn=lambda c:ax509.Certificate.load(c.public_bytes(serialization.Encoding.DER));store=SimpleCertificateStore();store.register(asn(root));tsa=DummyTimeStamper(asn(cert),keys.PrivateKeyInfo.load(key.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),store,fixed_dt=now+timedelta(hours=1) if future else now)
    p12,signer_root,_=identity();signer=signers.SimpleSigner.load_pkcs12_data(p12,[],passphrase=b'prueba');signed=signers.PdfSigner(signers.PdfSignatureMetadata(field_name='Stamped',md_algorithm='sha256'),signer,timestamper=tsa).sign_pdf(IncrementalPdfFileWriter(BytesIO(document()))).getvalue()
    if weak_imprint:
        import asyncio,hashlib
        from asn1crypto import cms
        from pyhanko.pdf_utils.reader import PdfFileReader
        signature=PdfFileReader(BytesIO(signed)).embedded_signatures[0];old=bytes(signature.sig_object['/Contents']);outer=cms.ContentInfo.load(old);si=outer['content']['signer_infos'][0];tsa.override_md='sha256';token=asyncio.run(tsa.async_timestamp(hashlib.sha1(si['signature'].native).digest(),'sha1'));si['unsigned_attrs'][0]['values'][0]=token;new=outer.dump();assert len(new)<=len(old)
        encoded=old.hex().encode();replacement=new.ljust(len(old),b'\0').hex().encode()
        if encoded not in signed:encoded=encoded.upper();replacement=replacement.upper()
        assert signed.count(encoded)==1;signed=signed.replace(encoded,replacement,1)
    return signed,signer_root,root.public_bytes(serialization.Encoding.PEM)


def test_timestamp_trust_is_separate_from_document_signer_and_never_implicit():
    pdf,signer_root,tsa_root=stamped();plain=verify_signatures(pdf,[])['signatures'][0];assert plain['timestamp_present'] and plain['timestamp']['intact'] and plain['timestamp']['cryptographically_valid'] and not plain['timestamp']['time_accepted_offline']
    only_signer=verify_signatures(pdf,[],signer_root)['signatures'][0];assert only_signer['chain_accepted'] and not only_signer['timestamp']['chain_accepted']
    only_tsa=verify_signatures(pdf,[],tsa_root)['signatures'][0];assert not only_tsa['chain_accepted'] and only_tsa['timestamp']['time_accepted_offline']
    full=verify_signatures(pdf,[],signer_root+tsa_root);row=full['signatures'][0];assert row['chain_accepted'] and row['timestamp']['time_accepted_offline'] and row['timestamp']['certificate']['common_name']=='Synthetic TSA';assert not full['revocation_checked'] and not full['network_used']


def test_unrelated_trust_and_wrong_tsa_usage_never_accredit_timestamp():
    pdf,root,tsa=stamped(True);report=verify_signatures(pdf,[],root+tsa)['signatures'][0];assert report['timestamp_present'] and not report['timestamp']['time_accepted_offline']


def test_timestamp_report_remains_offline(monkeypatch):
    import socket
    pdf,root,tsa=stamped();monkeypatch.setattr(socket,'create_connection',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Network prohibited in offline test')));report=verify_signatures(pdf,[],root+tsa);assert report['signatures'][0]['timestamp']['time_accepted_offline'] and not report['network_used']


def test_modified_timestamp_content_does_not_accredit_time_even_with_trusted_roots():
    from asn1crypto import cms
    from pyhanko.pdf_utils.reader import PdfFileReader
    pdf,root,tsa=stamped();sig=PdfFileReader(BytesIO(pdf)).embedded_signatures[0];old=bytes(sig.sig_object['/Contents']);outer=cms.ContentInfo.load(old);token=outer['content']['signer_infos'][0]['unsigned_attrs'][0]['values'][0];info=token['content']['encap_content_info']['content'].parsed;info['message_imprint']['hashed_message']=b'X'*32;token['content']['encap_content_info']['content']=info;new=outer.dump();assert len(new)<=len(old)
    encoded=old.hex().encode();replacement=new.ljust(len(old),b'\0').hex().encode()
    if encoded not in pdf:encoded=encoded.upper();replacement=replacement.upper()
    assert pdf.count(encoded)==1;changed=pdf.replace(encoded,replacement,1);report=verify_signatures(changed,[],root+tsa)['signatures'][0]
    assert report['intact'] and report['cryptographically_valid'] and report['timestamp_present'];assert not report['timestamp']['time_accepted_offline'] and (not report['timestamp']['intact'] or not report['timestamp']['cryptographically_valid'])


def test_future_timestamp_never_accredits_a_time_ahead_of_the_checking_clock():
    pdf,root,tsa=stamped(future=True);row=verify_signatures(pdf,[],root+tsa)['signatures'][0];assert row['timestamp']['intact'] and row['timestamp']['cryptographically_valid'];assert not row['timestamp']['time_accepted_offline'] and row['timestamp']['certificate_policy_problem']


def test_weak_imprint_does_not_accredit_time_even_with_strong_cms_and_valid_chains():
    pdf,root,tsa=stamped(weak_imprint=True);report=verify_signatures(pdf,[],root+tsa)['signatures'][0];ts=report['timestamp'];assert report['intact'] and ts['intact'] and ts['cryptographically_valid']
    assert ts['digest_algorithm']=='sha256' and ts['imprint_algorithm']=='sha1' and not ts['time_accepted_offline'] and ts['certificate_policy_problem']
