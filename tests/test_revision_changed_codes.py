from uuid import uuid4
import pytest,pymupdf as f
from backend.document_sets import revision,build,read,compile_pdf,validate_relations
from backend.engine import DocumentError
from tests.test_document_workspaces import item,pdf,relation


def setup():
    a=item(pdf('PLAN-01'));b=item(pdf('PLAN-01'),'Destination');r=relation(a,b);new=item(pdf('PLAN-02'),'Revision');return a,b,r,new


def test_changed_identifier_is_explicit_preserves_label_and_roundtrips():
    a,b,r,new=setup();mapping={r['id']:'PLAN-02'}
    p=revision([a,b],[r],b['id'],new,remap=mapping);row=p['affected'][0]
    assert row['code']=='PLAN-01' and row['matched_code']=='PLAN-02' and len(row['candidates'])==1
    docs,links,report=revision([a,b],[r],b['id'],new,{r['id']:row['candidates'][0]['id']},mapping)
    assert links[0]['code']=='PLAN-01' and links[0]['target']['matched_code']=='PLAN-02'
    data=build(docs,links,'Reviewed');restored,relations,name=read(data);assert relations==links
    output=compile_pdf(restored,relations,name)
    # compile_pdf can include a diagnostics report as the second tuple element.
    output=output[0] if isinstance(output,tuple) else output
    with f.open(stream=output) as d:assert 'PLAN-02' in ''.join(p.get_text() for p in d) and any(p.get_links() for p in d)
    latest=item(pdf('PLAN-02'),'Next revision');again=revision(docs,links,new['id'],latest)
    assert again['affected'][0]['matched_code']=='PLAN-02' and len(again['affected'][0]['candidates'])==1


def test_mapping_never_authorizes_an_ambiguous_or_stale_anchor():
    a,b,r,new=setup();mapping={r['id']:'PLAN-02'}
    row=revision([a,b],[r],b['id'],new,remap=mapping)['affected'][0]
    with pytest.raises(DocumentError):revision([a,b],[r],b['id'],new,{r['id']:'forged'},mapping)
    with pytest.raises(DocumentError):revision([a,b],[r],b['id'],new,{r['id']:row['candidates'][0]['id']})
    docs,links,_=revision([a,b],[r],b['id'],new,{r['id']:row['candidates'][0]['id']},mapping)
    links[0]['target']['matched_code']='PLAN-03'
    with pytest.raises(DocumentError):validate_relations(docs,links)


@pytest.mark.parametrize('remap',[[],{'missing':'PLAN-02'},{'id':{}},None])
def test_invalid_remap_or_unmapped_missing_code_does_not_change_documents(remap):
    a,b,r,new=setup()
    if remap is None:
        assert not revision([a,b],[r],b['id'],new)['affected'][0]['candidates']
    else:
        with pytest.raises(DocumentError):revision([a,b],[r],b['id'],new,remap=remap)
