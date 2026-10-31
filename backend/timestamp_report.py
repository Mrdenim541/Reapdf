"""Expose validated embedded signature timestamps without online or LT claims."""
from datetime import datetime,timezone,timedelta
from cryptography import x509
from .certificates import certificate_info


def report(status,checked_at=None,signature=None):
    if status is None:return None
    intact=bool(status.intact);valid=bool(status.valid);trusted=bool(status.trusted)
    result={'status':'integrity_failed' if not intact or not valid else 'chain_accepted_offline' if trusted else 'integrity_only','intact':intact,'cryptographically_valid':valid,'chain_accepted':trusted,'time':status.timestamp.isoformat(),'digest_algorithm':status.md_algorithm,'trust_problem':getattr(status.trust_problem_indic,'name',None),'revocation_checked':False,'network_used':False}
    policy=''
    if status.signing_cert is not None:
        cert=x509.load_der_x509_certificate(status.signing_cert.dump());info=certificate_info(cert);info.pop('signing_restriction',None);result['certificate']=info
        try:eku=cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        except x509.ExtensionNotFound:eku=None
        if eku is None or not eku.critical or {v.dotted_string for v in eku.value}!={'1.3.6.1.5.5.7.3.8'} or info['is_ca']:policy='El certificado no declara exclusivamente sellado de tiempo con extensión crítica.'
        elif info['key_algorithm']=='RSA' and not 2048<=info['key_bits']<=8192 or info['key_algorithm']=='EC' and info['curve'] not in ['secp256r1','secp384r1','secp521r1'] or info['key_algorithm'] not in ['RSA','EC']:policy='La clave de la autoridad de tiempo queda fuera del alcance admitido.'
        elif not cert.not_valid_before_utc<=status.timestamp<=cert.not_valid_after_utc:policy='La fecha del token queda fuera de la vigencia de su certificado.'
    else:policy='No se identificó el certificado de la autoridad de tiempo.'
    imprint=None
    try:
        attrs=[a for a in signature.signer_info['unsigned_attrs'] if a['type'].native=='signature_time_stamp_token']
        if len(attrs)==1 and len(attrs[0]['values'])==1:imprint=attrs[0]['values'][0]['content']['encap_content_info']['content'].parsed['message_imprint']['hash_algorithm']['algorithm'].native
    except (ValueError,TypeError,KeyError,AttributeError):pass
    result['imprint_algorithm']=imprint
    if imprint not in ['sha256','sha384','sha512'] or status.md_algorithm not in ['sha256','sha384','sha512']:policy='El token necesita SHA-256, SHA-384 o SHA-512 tanto en el imprint como en su firma CMS.'
    if status.timestamp>(checked_at or datetime.now(timezone.utc))+timedelta(minutes=5):policy='La fecha del token es posterior al reloj de comprobación; revisa ambos relojes.'
    result['certificate_policy_problem']=policy
    result['chain_accepted']=trusted and not policy
    if intact and valid and policy:result['status']='integrity_only'
    result['time_accepted_offline']=intact and valid and result['chain_accepted']
    return result
