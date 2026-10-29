"""Synthetic identities only; never real personal certificates."""
from datetime import datetime,timezone,timedelta
from functools import lru_cache
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID,AuthorityInformationAccessOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ec
from cryptography.hazmat.primitives.serialization import pkcs12
import pymupdf as f


@lru_cache(maxsize=16)
def _identity(kind,state,usage,password,ca):
    now=datetime.now(timezone.utc)
    rootkey=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    rootname=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Reapdf CA de pruebas')])
    root=x509.CertificateBuilder().subject_name(rootname).issuer_name(rootname).public_key(rootkey.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=2)).not_valid_after(now+timedelta(days=365)).add_extension(x509.BasicConstraints(ca=True,path_length=1),critical=True).add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),critical=True).sign(rootkey,hashes.SHA256())
    key=ec.generate_private_key(ec.SECP256R1()) if kind=='ec' else rsa.generate_private_key(public_exponent=65537,key_size=1024 if kind=='weak' else 2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'María Pérez · Prueba')])
    before=now+timedelta(days=2) if state=='future' else now-timedelta(days=10)
    after=now-timedelta(days=1) if state=='expired' else now+timedelta(days=60)
    builder=x509.CertificateBuilder().subject_name(subject).issuer_name(rootname).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(before).not_valid_after(after).add_extension(x509.BasicConstraints(ca=ca,path_length=None),critical=True)
    if usage!='absent':builder=builder.add_extension(x509.KeyUsage(usage=='sign',usage=='commitment',False,usage=='server',False,ca,ca,False,False),critical=True)
    if usage=='server':builder=builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
    builder=builder.add_extension(x509.AuthorityInformationAccess([x509.AccessDescription(AuthorityInformationAccessOID.OCSP,x509.UniformResourceIdentifier('http://127.0.0.1:9/ocsp')),x509.AccessDescription(AuthorityInformationAccessOID.CA_ISSUERS,x509.UniformResourceIdentifier('http://127.0.0.1:9/ca.cer'))]),critical=False)
    cert=builder.sign(rootkey,hashes.SHA256())
    encrypted=serialization.BestAvailableEncryption(password.encode()) if password else serialization.NoEncryption()
    data=pkcs12.serialize_key_and_certificates(b'Reapdf prueba',key,cert,[root],encrypted)
    return data,root.public_bytes(serialization.Encoding.PEM),cert.public_bytes(serialization.Encoding.PEM)


def document(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Documento para firmar',fontsize=14)
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((40,80),'Segunda pagina intacta');return d.tobytes()


def identity(kind='rsa',state='valid',usage='sign',password='prueba',ca=False):
    return _identity(kind,state,usage,password,ca)
