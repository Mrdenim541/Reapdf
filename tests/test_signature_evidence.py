from io import BytesIO
import pytest
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from backend.digital_signatures import sign_document,verify_signatures
from backend.signature_evidence import preserve_evidence,embedded_evidence
from backend.engine import DocumentError
from tests.signature_samples import document
from tests.test_affine_perspective_revocation import pki


def signed():
    identity,root,proof=pki();return sign_document(document(),[],identity,'',{}),root,proof


@pytest.mark.parametrize('proof_kind',['crl','ocsp'])
def test_preserve_reopen_explicit_trust_and_opt_in_embedded(proof_kind):
    identity,root,proof=pki(proof=proof_kind);base=sign_document(document(),[],identity,'',{})
    plan=preserve_evidence(base,[],root,[proof],True)
    assert plan['signatures']==1 and not plan['network_used'] and not plan['pades_lt_lta_accredited']
    out=preserve_evidence(base,[],root,[proof]);assert out.startswith(base)
    assert proof in embedded_evidence(out)
    default=verify_signatures(out,[],root)['signatures'][0]
    assert default['revocation']['status']=='not_checked'
    report=verify_signatures(out,[],root,use_embedded=True)
    assert report['evidence']['embedded_files']==1 and report['signatures'][0]['status']=='chain_accepted_with_local_revocation'
    assert report['signatures'][0]['modification_level']=='LTA_UPDATES'
    assert verify_signatures(out,[],use_embedded=True)['signatures'][0]['status']!='chain_accepted_with_local_revocation'


@pytest.mark.parametrize('state',['revoked','stale'])
def test_bad_evidence_never_preserved(state):
    base,root,_=signed();_,_,proof=pki(state=state)
    with pytest.raises(DocumentError):preserve_evidence(base,[],root,[proof])


def test_unsigned_missing_trust_evidence_and_pending_changes_rejected():
    base,root,proof=signed()
    for args in [(document(),[],root,[proof]),(base,[],b'',[proof]),(base,[],root,[]),(base,[{'type':'note'}],root,[proof])]:
        with pytest.raises(DocumentError):preserve_evidence(*args)


def test_dss_stream_expansion_is_bounded():
    writer=IncrementalPdfFileWriter(BytesIO(document()))
    stream=generic.StreamObject(stream_data=b'X'*(4*1024*1024+1));stream.compress()
    writer.root[generic.pdf_name('/DSS')]=generic.DictionaryObject({generic.pdf_name('/CRLs'):generic.ArrayObject([writer.add_object(stream)])});writer.update_root()
    buffer=BytesIO();writer.write(buffer)
    with pytest.raises(DocumentError):embedded_evidence(buffer.getvalue())


def test_api_preserve_and_verify_embedded():
    import json
    from fastapi.testclient import TestClient
    from backend.app import app
    base,root,proof=signed()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('signed.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        files=[('trust',('root.pem',root)),('evidence',('proof.crl',proof))]
        review=client.post(url+'/signature-evidence',files=files,data={'payload':json.dumps({'review':True})})
        assert review.status_code==200 and review.json()['signatures']==1
        copy=client.post(url+'/signature-evidence',files=files)
        assert copy.status_code==200 and copy.content.startswith(base)
        new=client.post('/api/documents',files={'file':('evidence.pdf',copy.content,'application/pdf')}).json()
        report=client.post('/api/documents/'+new['id']+'/verify-signatures',files={'trust':('root.pem',root)},data={'payload':json.dumps({'use_embedded':True})})
        assert report.status_code==200 and report.json()['signatures'][0]['status']=='chain_accepted_with_local_revocation'
        assert client.post(url+'/signature-evidence').status_code==422


def test_embedded_unknown_content_or_too_many_streams_rejected():
    for values in [generic.ArrayObject([generic.NumberObject(7)]),generic.ArrayObject([generic.NullObject()]*21)]:
        writer=IncrementalPdfFileWriter(BytesIO(document()));writer.root[generic.pdf_name('/DSS')]=generic.DictionaryObject({generic.pdf_name('/CRLs'):values});writer.update_root();b=BytesIO();writer.write(b)
        with pytest.raises(DocumentError):embedded_evidence(b.getvalue())
