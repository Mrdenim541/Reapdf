"""Offline approval signatures and separate integrity, revision and trust reports."""
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import hashlib
from urllib.parse import urlsplit
import pymupdf as f
from asn1crypto.x509 import Certificate
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from pyhanko.sign import signers,fields,validation
from pyhanko.sign.validation.settings import KeyUsageConstraints
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.text import TextBoxStyle
from pyhanko.pdf_utils.font.opentype import GlyphAccumulatorFactory
from pyhanko import stamp
from pyhanko_certvalidator import ValidationContext
from .certificates import load_identity,certificate_info,trust_certificates
from .engine import open_pdf,export_pdf,DocumentError,finite
from .link_editing import pdf_rectangle

MAX_SIGNATURES=20
MAX_SIGNED_BYTES=40*1024*1024


def reader_for(data):
    if len(data)>MAX_SIGNED_BYTES:raise DocumentError('La revisión de firmas admite PDF de hasta 40 MB.')
    try:
        reader=PdfFileReader(BytesIO(data),strict=True)
        if reader.security_handler is not None:raise DocumentError('Abre una copia autorizada sin cifrado antes de firmar o verificar.')
        embedded=list(reader.embedded_signatures)
        if len(embedded)>MAX_SIGNATURES:raise DocumentError('Se admiten hasta 20 firmas por documento.')
        return reader,embedded
    except DocumentError:raise
    except Exception:raise DocumentError('No se pudo interpretar de forma estricta la estructura de firmas del PDF.') from None


def verify_signatures(base,operations,trust=b'',evidence=()):
    from .local_revocation import parse,check,check_timestamp
    crls,ocsps=parse(evidence)
    data=export_pdf(base,operations)
    with open_pdf(data) as doc:indicators=doc.get_sigflags()>0
    reader,embedded=reader_for(data);roots=trust_certificates(trust);rows=[]
    now=datetime.now(timezone.utc)
    for signature in embedded:
        try:
            ctx=ValidationContext(trust_roots=roots,allow_fetching=False,revocation_mode='soft-fail',moment=now)
            from .timestamp_report import report as timestamp_report
            document_timestamp=signature.sig_object_type=='/DocTimeStamp'
            if document_timestamp:
                result=validation.validate_pdf_timestamp(signature,validation_context=ctx)
                token_info=signature.signed_data['encap_content_info']['content'].parsed;imprint=token_info['message_imprint']['hash_algorithm']['algorithm'].native
                timestamp=timestamp_report(result,now,imprint_algorithm=imprint,token_info=token_info)
                cert=timestamp['certificate'];tsa_certificate=result.signing_cert
                policy=timestamp['certificate_policy_problem'];accepted=timestamp['chain_accepted']
            else:
                result=validation.validate_pdf_signature(signature,signer_validation_context=ctx,ts_validation_context=ctx,
                    key_usage_settings=KeyUsageConstraints(key_usage={'digital_signature','non_repudiation'},match_all_key_usages=False,extd_key_usage=None))
                timestamp=timestamp_report(result.timestamp_validity,now,signature)
                tsa_certificate=result.timestamp_validity.signing_cert if result.timestamp_validity else None
                revocation=check(signature,roots,crls,ocsps,now)
                cert=certificate_info(x509.load_der_x509_certificate(signature.signer_cert.dump()))
                policy=cert['signing_restriction'];accepted=bool(result.trusted) and not policy
            if timestamp:
                tsa_revocation=check_timestamp(signature,tsa_certificate,roots,crls,ocsps,now);timestamp['revocation']=tsa_revocation;timestamp['revocation_checked']=tsa_revocation['checked']
                if not timestamp['intact'] or not timestamp['cryptographically_valid']:timestamp.update(status='integrity_failed',time_accepted_offline=False)
                elif tsa_revocation['status']=='revoked':timestamp.update(status='certificate_revoked',time_accepted_offline=False,chain_accepted=False)
                elif evidence and tsa_revocation['status']!='accepted_offline':timestamp.update(status='revocation_unknown',time_accepted_offline=False)
                elif tsa_revocation['status']=='accepted_offline' and timestamp['time_accepted_offline']:timestamp['status']='chain_accepted_with_local_revocation'
                if document_timestamp:revocation=tsa_revocation;accepted=timestamp['chain_accepted']
            coverage=result.coverage.name;modification=result.modification_level.name if result.modification_level is not None else None
            complete=coverage=='ENTIRE_FILE'
            allowed=modification in [None,'NONE','LTA_UPDATES','FORM_FILLING'] and result.docmdp_ok is not False
            row={'field':signature.field_name,'type':'document_timestamp' if document_timestamp else 'approval','certificate':cert,'intact':bool(result.intact),'cryptographically_valid':bool(result.valid),
                'chain_accepted':accepted,'certificate_policy_problem':policy,'trust_problem':getattr(result.trust_problem_indic,'name',None),
                'coverage':coverage,'covers_current_file':complete,'modification_level':modification,'allowed_changes':allowed,
                'docmdp_ok':result.docmdp_ok,'digest_algorithm':result.md_algorithm,'signature_algorithm':result.pkcs7_signature_mechanism,
                'reported_signing_time':signature.self_reported_timestamp.isoformat() if not document_timestamp and signature.self_reported_timestamp else None,
                'revocation':revocation,'timestamp_present':timestamp is not None,'timestamp':timestamp,'error':None}
            if not row['intact'] or not row['cryptographically_valid']:row['status']='integrity_failed'
            elif not allowed or coverage not in ['ENTIRE_FILE','ENTIRE_REVISION']:row['status']='changes_require_review'
            elif not row['chain_accepted']:row['status']='integrity_only'
            else:row['status']='chain_accepted_offline'
            if revocation['status']=='accepted_offline' and row['status']=='chain_accepted_offline':row['status']='chain_accepted_with_local_revocation'
            if revocation['status']=='revoked':row['status']='certificate_revoked'
            elif evidence and revocation['status']!='accepted_offline' and row['status']=='chain_accepted_offline':row['status']='revocation_unknown'
        except Exception:
            row={'field':signature.field_name,'status':'inconclusive','error':'No se pudo completar la validación de esta firma. No se considera válida.'}
        rows.append(row)
    return {'schema':'reapdf-signatures-1','source_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),'checked_at':now.isoformat(),
        'network_used':False,'revocation_checked':bool(rows) and all(r.get('revocation',{}).get('checked',False) for r in rows),'tsa_revocation_checked':any(r.get('timestamp') for r in rows) and all(r.get('timestamp',{}).get('revocation_checked',False) for r in rows if r.get('timestamp')),'revocation_scope':'Firmantes y TSA con resultados separados a la fecha de comprobación; sin validación histórica.','evidence':{'crls':len(crls),'ocsps':len(ocsps)},'trusted_certificates':[certificate_info(x509.load_der_x509_certificate(c.dump())) for c in roots],
        'signature_indicators':indicators,'signatures':rows,'count':len(rows),
        'scope':'Verificación criptográfica y de revisiones con confianza explícita local, incluidos sellos documentales RFC3161 y tokens de tiempo de firma. Sin consultas de red; revocación con evidencias locales explícitas de firmantes y TSA, con resultados separados a la fecha de comprobación. No acredita validación histórica, jurídica, conservación de archivo ni PAdES-LT/LTA. La fecha del firmante no prueba el momento de firma.'}


def signing_plan(base,operations,config):
    if not isinstance(config,dict) or set(config)-{'visible','page','box','reason','location'}:raise DocumentError('Configuración de firma no válida.')
    visible=config.get('visible',False)
    if type(visible) is not bool:raise DocumentError('La visibilidad debe ser verdadera o falsa.')
    reason=config.get('reason','');location=config.get('location','')
    if any(not isinstance(v,str) or len(v)>200 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in v) for v in [reason,location]):raise DocumentError('Motivo y lugar: hasta 200 caracteres sin controles.')
    with open_pdf(base) as source:
        required=f.PDF_PERM_MODIFY|f.PDF_PERM_FORM|f.PDF_PERM_COPY
        if source.permissions&required!=required:raise DocumentError('El PDF debe permitir modificar, rellenar y copiar para firmar esta copia.')
    data=export_pdf(base,operations);reader,embedded=reader_for(data)
    if len(embedded)>=MAX_SIGNATURES:raise DocumentError('Se alcanzó el límite de 20 firmas.')
    if reader.root.get('/Perms') or any(sig.docmdp_level is not None or sig.fieldmdp is not None for sig in embedded):raise DocumentError('No se añaden firmas a documentos certificados o con restricciones DocMDP/FieldMDP.')
    if embedded:
        report=verify_signatures(data,[])
        if any(integrity_failure(row) for row in report['signatures']):raise DocumentError('Las firmas o sellos existentes no superan la revisión de integridad y cambios. No se añade otra firma ni sello.')
    elif source_indicators(data):raise DocumentError('El PDF tiene indicadores o campos de firma sin una firma interpretable; se conserva sin firmar.')
    box=None;number=config.get('page',0)
    with open_pdf(data) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página de firma no válida.')
        if visible:
            values=config.get('box')
            if not isinstance(values,list) or len(values)!=4 or any(not finite(v) for v in values):raise DocumentError('Posición de firma no válida.')
            x,y,w,h=values;rect=f.Rect(x,y,x+w,y+h);page=doc[number]
            if w<180 or h<65 or not page.rect.contains(rect):raise DocumentError('La firma visible necesita al menos 180 × 65 pt dentro de la página.')
            if page.rotation:raise DocumentError('La firma visible requiere una página sin giro; puedes usar firma sin marca visible.')
            box=tuple(pdf_rectangle(page,rect))
    return data,reader,{'visible':visible,'page':number,'native_box':box,'reason':reason,'location':location,'existing_signatures':len(embedded)}


def source_indicators(data):
    with open_pdf(data) as doc:return doc.get_sigflags()>0


def integrity_failure(row):
    token=row.get('timestamp')
    return row['status'] in ['inconclusive','integrity_failed','changes_require_review'] or bool(token and (not token['intact'] or not token['cryptographically_valid']))


def sign_document(base,operations,identity,password,config,review=False,tsa=None,tsa_trust=b''):
    from .timestamp_authority import VerifiedTimeStamper
    authority=VerifiedTimeStamper(tsa,tsa_trust) if tsa is not None else None
    _,cert,_,info=load_identity(identity,password)
    if not info['can_sign']:raise DocumentError(info['reason'])
    data,reader,plan=signing_plan(base,operations,config)
    report={'schema':'reapdf-signing-plan-1','source_sha256':hashlib.sha256(data).hexdigest(),'certificate':info,
        'visible':plan['visible'],'page':plan['page'],'existing_signatures':plan['existing_signatures'],'digest_algorithm':'sha256','network_used':False,
        'reason':plan['reason'],'location':plan['location'],'revocation_checked':False,'certificate_trust_evaluated':False}
    report['timestamp_requested']=authority is not None
    if authority:report['tsa_host']=urlsplit(authority.url).hostname
    if review:return report
    try:
        signer=signers.SimpleSigner.load_pkcs12_data(identity,[],passphrase=password.encode('utf-8') if password else None)
        name='ReapdfFirma_'+uuid4().hex[:16]
        metadata=signers.PdfSignatureMetadata(field_name=name,md_algorithm='sha256',reason=plan['reason'] or None,location=plan['location'] or None,
            name=info['common_name'],subfilter=fields.SigSeedSubFilter.PADES,certify=False)
        font=GlyphAccumulatorFactory(str(Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'))
        style=stamp.TextStampStyle(stamp_text='Firmado digitalmente\n%(signer)s\n%(ts)s',border_width=1,text_box_style=TextBoxStyle(font=font,font_size=9,leading=12))
        pdf_signer=signers.PdfSigner(metadata,signer,timestamper=authority,stamp_style=style,new_field_spec=fields.SigFieldSpec(name,on_page=plan['page'],box=plan['native_box']))
        output=pdf_signer.sign_pdf(IncrementalPdfFileWriter(BytesIO(data),prev=reader)).getvalue()
    except DocumentError:raise
    except Exception:raise DocumentError('No se pudo completar la firma digital. El documento original permanece intacto.') from None
    if len(output)>MAX_SIGNED_BYTES:raise DocumentError('La copia firmada supera 40 MB.')
    checked=verify_signatures(output,[],tsa_trust if authority else b'')
    if len(checked['signatures'])!=plan['existing_signatures']+1 or any(integrity_failure(row) for row in checked['signatures']):raise DocumentError('La copia firmada no superó la comprobación criptográfica. No se entrega.')
    if authority and not next((r for r in checked['signatures'] if r['field']==name),{}).get('timestamp',{}).get('time_accepted_offline'):raise DocumentError('El sello de la nueva firma no quedó validado con la confianza seleccionada.')
    return output


def timestamp_document(base,operations,tsa,trust,review=False):
    from .timestamp_authority import VerifiedTimeStamper
    from urllib.parse import urlsplit
    authority=VerifiedTimeStamper(tsa,trust);data,reader,plan=signing_plan(base,operations,{'visible':False})
    if review:return {'schema':'reapdf-document-timestamp-plan-1','source_sha256':hashlib.sha256(data).hexdigest(),'existing_signatures':plan['existing_signatures'],'tsa_host':urlsplit(authority.url).hostname,'timestamp_requested':True,'digest_algorithm':'sha256','network_used':False,'revocation_checked':False}
    name='ReapdfTiempo_'+uuid4().hex[:16]
    try:output=signers.PdfTimeStamper(authority,field_name=name).timestamp_pdf(IncrementalPdfFileWriter(BytesIO(data),prev=reader),'sha256').getvalue()
    except DocumentError:raise
    except Exception:raise DocumentError('No se pudo incorporar el sello documental. Se conserva el PDF original.') from None
    if len(output)>MAX_SIGNED_BYTES or not output.startswith(data):raise DocumentError('La copia sellada excede el tamaño o no conserva la revisión original.')
    checked=verify_signatures(output,[],trust);new=next((r for r in checked['signatures'] if r['field']==name),{})
    if len(checked['signatures'])!=plan['existing_signatures']+1 or any(integrity_failure(r) for r in checked['signatures']) or not new.get('timestamp',{}).get('time_accepted_offline'):raise DocumentError('La copia no superó la comprobación del sello y las firmas anteriores. No se entrega.')
    return output
