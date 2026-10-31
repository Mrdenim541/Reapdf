"""Bounded public CRL/OCSP evidence; verification is strictly offline."""
from asn1crypto import crl,ocsp,pem
from .engine import DocumentError

MAX_EVIDENCE=4*1024*1024
MAX_FILES=20


def parse(files):
    if not isinstance(files,(list,tuple)) or len(files)>MAX_FILES or sum(len(v) for v in files if isinstance(v,bytes))>MAX_EVIDENCE:raise DocumentError('Revocación: hasta 20 archivos y 4 MB en total.')
    crls=[];ocsps=[]
    for raw in files:
        if not isinstance(raw,bytes) or not raw:raise DocumentError('La evidencia de revocación está vacía o no es válida.')
        try:
            if pem.detect(raw):
                if raw.count(b'-----BEGIN ')!=1 or raw.count(b'-----END ')!=1:raise ValueError()
                label,_,raw=pem.unarmor(raw)
                if label not in ['X509 CRL','CRL','OCSP RESPONSE']:raise ValueError()
            else:label=None
            parsed=None
            for kind,klass,target in [('crl',crl.CertificateList,crls),('ocsp',ocsp.OCSPResponse,ocsps)]:
                try:
                    value=klass.load(raw,strict=True);value.native
                    if kind=='crl':
                        value['tbs_cert_list']['issuer'].native
                    elif value['response_status'].native!='successful' or value['response_bytes']['response_type'].native!='basic_ocsp_response':raise ValueError()
                    if label=='OCSP RESPONSE' and kind!='ocsp' or label in ['CRL','X509 CRL'] and kind!='crl':raise ValueError()
                    target.append(value);parsed=True;break
                except (ValueError,TypeError,KeyError):continue
            if not parsed:raise ValueError()
        except Exception:raise DocumentError('Evidencia no válida: usa una CRL completa o respuesta OCSP exitosa en DER/PEM, sin claves privadas.') from None
    return crls,ocsps


def _check(signature,roots,crls,ocsps,now):
    from pyhanko_certvalidator import ValidationContext
    from pyhanko.sign import validation
    from pyhanko.sign.validation.settings import KeyUsageConstraints
    if not crls and not ocsps:return {'status':'not_checked','checked':False,'scope':'Cadena del firmante; no incluye TSA.'}
    try:
        context=ValidationContext(trust_roots=roots,allow_fetching=False,revocation_mode='require',moment=now,crls=crls,ocsps=ocsps)
        result=validation.validate_pdf_signature(signature,signer_validation_context=context,
            ts_validation_context=ValidationContext(trust_roots=roots,allow_fetching=False,moment=now),
            key_usage_settings=KeyUsageConstraints(key_usage={'digital_signature','non_repudiation'},match_all_key_usages=False,extd_key_usage=None))
        problem=getattr(result.trust_problem_indic,'name',None)
        revoked=problem in ['REVOKED','REVOKED_NO_POE','REVOKED_CA_NO_POE']
        accepted=bool(result.trusted) and result.intact and result.valid
        return {'status':'revoked' if revoked else 'accepted_offline' if accepted else 'unknown','checked':bool(revoked or accepted),'problem':problem,'scope':'Cadena del firmante a la fecha de comprobación; no incluye TSA.'}
    except Exception:
        return {'status':'unknown','checked':False,'problem':'Evidencia insuficiente, no vigente o cadena no verificable.','scope':'Cadena del firmante; no incluye TSA.'}


def check(signature,roots,crls,ocsps,now):
    if not crls and not ocsps:return _check(signature,roots,crls,ocsps,now)
    if any(root.sha256==signature.signer_cert.sha256 for root in roots):return {'status':'unknown','checked':False,'problem':'El certificado del firmante se seleccionó como ancla; no se acredita revocación de una cadena independiente.','scope':'Cadena del firmante; no TSA.'}
    results=[]
    if crls:results.append(_check(signature,roots,crls,[],now))
    if ocsps:results.append(_check(signature,roots,[],ocsps,now))
    # Do not let a good OCSP hide a supplied CRL that establishes revocation,
    # or accept partially covered/stale evidence when both kinds are supplied.
    revoked=next((r for r in results if r['status']=='revoked'),None)
    if revoked:return revoked
    return next((r for r in results if r['status']!='accepted_offline'),results[0])
