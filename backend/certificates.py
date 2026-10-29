"""In-memory PKCS#12 inspection and explicit, session-only trust material."""
from datetime import datetime,timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,ec
from cryptography.hazmat.primitives.serialization import pkcs12
from .engine import DocumentError

MAX_IDENTITY=2*1024*1024
MAX_TRUST=512*1024
DOCUMENT_EKUS={'2.5.29.37.0','1.3.6.1.5.5.7.3.36','1.3.6.1.4.1.311.10.3.12','1.2.840.113583.1.1.5'}


def certificate_info(cert):
    now=datetime.now(timezone.utc);key=cert.public_key()
    try:usage=cert.extensions.get_extension_for_class(x509.KeyUsage).value;usages=[n for n in ['digital_signature','content_commitment','key_cert_sign','crl_sign','key_encipherment'] if getattr(usage,n)]
    except x509.ExtensionNotFound:usages=[]
    try:eku=[v.dotted_string for v in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value]
    except x509.ExtensionNotFound:eku=[]
    try:is_ca=cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    except x509.ExtensionNotFound:is_ca=False
    common=cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    algorithm='RSA' if isinstance(key,rsa.RSAPublicKey) else 'EC' if isinstance(key,ec.EllipticCurvePublicKey) else type(key).__name__
    info={'subject':cert.subject.rfc4514_string(),'issuer':cert.issuer.rfc4514_string(),'common_name':common[0].value if common else cert.subject.rfc4514_string(),
        'serial':format(cert.serial_number,'X'),'sha256':cert.fingerprint(hashes.SHA256()).hex(),'not_before':cert.not_valid_before_utc.isoformat(),'not_after':cert.not_valid_after_utc.isoformat(),
        'valid_now':cert.not_valid_before_utc<=now<=cert.not_valid_after_utc,'is_ca':is_ca,'self_issued':cert.subject==cert.issuer,
        'key_algorithm':algorithm,'key_bits':getattr(key,'key_size',None),'curve':getattr(getattr(key,'curve',None),'name',None),'key_usage':usages,'extended_key_usage':eku}
    problem=''
    if not info['valid_now']:problem='El certificado está caducado o aún no es vigente.'
    elif is_ca:problem='Un certificado de autoridad no acredita una firma personal de documento.'
    elif isinstance(key,rsa.RSAPublicKey) and not 2048<=key.key_size<=8192:problem='Clave RSA fuera del rango admitido (2048–8192 bits).'
    elif isinstance(key,ec.EllipticCurvePublicKey) and key.curve.name not in ['secp256r1','secp384r1','secp521r1']:problem='Curva elíptica no admitida.'
    elif not isinstance(key,(rsa.RSAPublicKey,ec.EllipticCurvePublicKey)):problem='Algoritmo de clave no admitido en este alcance.'
    elif not set(usages)&{'digital_signature','content_commitment'}:problem='No declara uso de firma de documento.'
    elif eku and not set(eku)&DOCUMENT_EKUS:problem='El uso extendido no permite firma de documentos.'
    info['signing_restriction']=problem
    return info


def load_identity(data,password):
    if not isinstance(data,bytes) or not data or len(data)>MAX_IDENTITY:raise DocumentError('Selecciona un P12/PFX de hasta 2 MB.')
    if not isinstance(password,str) or len(password)>256 or any(0xd800<=ord(c)<=0xdfff for c in password):raise DocumentError('La contraseña del certificado no es válida (hasta 256 caracteres).')
    try:key,cert,chain=pkcs12.load_key_and_certificates(data,password.encode('utf-8') if password else None)
    except (ValueError,TypeError):raise DocumentError('No se pudo abrir el P12/PFX. Revisa archivo y contraseña.') from None
    if not key or not cert:raise DocumentError('El P12/PFX debe contener certificado y clave privada.')
    if len(chain)>20:raise DocumentError('El certificado contiene más de 20 certificados auxiliares.')
    public=lambda k:k.public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    if public(key.public_key())!=public(cert.public_key()):raise DocumentError('La clave privada no corresponde al certificado.')
    info=certificate_info(cert);reason=''
    if not info['valid_now']:reason='El certificado está caducado o aún no es vigente.'
    elif info['is_ca']:reason='No se utiliza un certificado de autoridad para firmar documentos personales.'
    elif isinstance(key,rsa.RSAPrivateKey) and not 2048<=key.key_size<=8192:reason='La clave RSA debe tener entre 2048 y 8192 bits.'
    elif isinstance(key,ec.EllipticCurvePrivateKey) and key.curve.name not in ['secp256r1','secp384r1','secp521r1']:reason='La curva elíptica no está admitida para firmar.'
    elif not isinstance(key,(rsa.RSAPrivateKey,ec.EllipticCurvePrivateKey)):reason='Solo se admiten claves RSA y curvas elípticas compatibles.'
    elif not set(info['key_usage'])&{'digital_signature','content_commitment'}:reason='El certificado no declara uso de firma digital o compromiso de contenido.'
    elif info['extended_key_usage'] and not set(info['extended_key_usage'])&DOCUMENT_EKUS:reason='El uso extendido del certificado no permite firma de documentos.'
    info.update(can_sign=not reason,reason=reason,chain_certificates=len(chain),trust_evaluated=False,revocation_checked=False)
    return key,cert,chain,info


def inspect_identity(data,password):return load_identity(data,password)[3]


def trust_certificates(data=b''):
    if not isinstance(data,bytes) or len(data)>MAX_TRUST:raise DocumentError('Usa certificados públicos PEM/DER de hasta 512 KB.')
    if not data:return []
    if b'PRIVATE KEY' in data:raise DocumentError('La confianza solo admite certificados públicos, sin claves privadas.')
    try:certs=x509.load_pem_x509_certificates(data) if b'-----BEGIN CERTIFICATE-----' in data else [x509.load_der_x509_certificate(data)]
    except ValueError:raise DocumentError('No se pudieron leer los certificados públicos PEM/DER.') from None
    if not 1<=len(certs)<=20:raise DocumentError('Selecciona de 1 a 20 certificados públicos de confianza.')
    from asn1crypto.x509 import Certificate
    return [Certificate.load(cert.public_bytes(serialization.Encoding.DER)) for cert in certs]
