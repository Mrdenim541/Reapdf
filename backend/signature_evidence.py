"""Explicit local DSS preservation. Embedded certificates never become trust roots."""
from io import BytesIO
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils.decode_limits import DecodeLimits,StreamDecodeLimits
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.validation.dss import DocumentSecurityStore
from .engine import DocumentError
from .local_revocation import MAX_EVIDENCE,MAX_FILES,parse


def embedded_evidence(data):
    """Only explicitly requested CRL/OCSP streams, bounded before decompression."""
    try:
        reader=PdfFileReader(BytesIO(data),strict=True,decode_limits=DecodeLimits(per_stream=StreamDecodeLimits(max_output_size=MAX_EVIDENCE),per_purpose={}))
        dss=reader.root.get('/DSS')
        if dss is None:return []
        dss=dss.get_object()
        if not isinstance(dss,generic.DictionaryObject):raise ValueError()
        certs=dss.get('/Certs',[])
        if hasattr(certs,'get_object'):certs=certs.get_object()
        if not isinstance(certs,(list,generic.ArrayObject)) or len(certs)>100:raise ValueError()
        size=0
        from asn1crypto.x509 import Certificate
        for item in certs:
            cert=item.get_object()
            if not isinstance(cert,generic.StreamObject):raise ValueError()
            raw=cert.data;size+=len(raw)
            if len(raw)>65536 or size>MAX_EVIDENCE:raise ValueError()
            Certificate.load(raw,strict=True).native
        files=[];size=0
        for name in ['/CRLs','/OCSPs']:
            rows=dss.get(name,[])
            if hasattr(rows,'get_object'):rows=rows.get_object()
            if not isinstance(rows,(list,generic.ArrayObject)) or len(rows)+len(files)>MAX_FILES:raise ValueError()
            for row in rows:
                obj=row.get_object()
                if not isinstance(obj,generic.StreamObject):raise ValueError()
                raw=obj.data;size+=len(raw)
                if size>MAX_EVIDENCE:raise ValueError()
                crls,ocsps=parse([raw])
                if name=='/CRLs' and not crls or name=='/OCSPs' and not ocsps:raise ValueError()
                files.append(raw)
        return files
    except Exception:raise DocumentError('Las evidencias DSS no son compatibles o superan 20 archivos/4 MB. No se utilizan.') from None


def preserve_evidence(base,operations,trust,evidence,review=False):
    from .digital_signatures import signing_plan,verify_signatures,integrity_failure,MAX_SIGNED_BYTES
    from .certificates import trust_certificates
    if operations:raise DocumentError('La conservación de evidencias requiere el PDF firmado sin cambios pendientes.')
    data,reader,plan=signing_plan(base,[],{'visible':False})
    if not plan['existing_signatures']:raise DocumentError('El PDF no contiene firmas o sellos que conservar.')
    roots=trust_certificates(trust);crls,ocsps=parse(evidence)
    if not roots or not (crls or ocsps):raise DocumentError('Selecciona confianza pública y evidencias CRL/OCSP vigentes.')
    embedded_evidence(data)
    checked=verify_signatures(data,[],trust,evidence)
    for row in checked['signatures']:
        if integrity_failure(row) or row['status']!='chain_accepted_with_local_revocation' or (row.get('timestamp') and (not row['timestamp']['time_accepted_offline'] or row['timestamp']['revocation']['status']!='accepted_offline')):
            raise DocumentError('Todas las firmas y TSA deben superar integridad, confianza y revocación local antes de conservar las evidencias.')
    report={'schema':'reapdf-dss-plan-1','source_sha256':checked['source_sha256'],'signatures':checked['count'],'crls':len(crls),'ocsps':len(ocsps),'network_used':False,'historical_validation':False,'pades_lt_lta_accredited':False}
    if review:return report
    try:
        writer=IncrementalPdfFileWriter(BytesIO(data),prev=reader)
        certs={c.sha256:c for c in roots}
        for signature in reader.embedded_signatures:
            for c in signature.signed_data['certificates']:
                if c.name=='certificate':certs[c.chosen.sha256]=c.chosen
            DocumentSecurityStore.supply_dss_in_writer(writer,signature.sig_object['/Contents'],certs=list(certs.values()),crls=crls,ocsps=ocsps)
        buffer=BytesIO();writer.write(buffer);output=buffer.getvalue()
        if len(output)>MAX_SIGNED_BYTES or not output.startswith(data):raise ValueError()
        after=verify_signatures(output,[],trust,evidence)
        if after['count']!=checked['count'] or any(integrity_failure(r) or r['status']!='chain_accepted_with_local_revocation' for r in after['signatures']):raise ValueError()
        embedded=embedded_evidence(output)
        if not set(c.dump() for c in crls+ocsps).issubset(set(embedded)):raise ValueError()
        return output
    except DocumentError:raise
    except Exception:raise DocumentError('No se pudo conservar y comprobar la evidencia DSS. El original permanece intacto.') from None
