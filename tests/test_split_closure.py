from io import BytesIO
import json
from zipfile import ZipFile
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.page_tools import inspect_split,split_pdf
from scripts.create_split_sample import create


def test_large_tagged_document_all_42_parts_verified_without_removing_tags():
    data=create();names=[f'1.46 PINTURA {i:03d}' for i in range(1,43)]
    review=inspect_split(data,[],size=1,names=names)
    assert review['structure_nodes']>2000
    with ZipFile(BytesIO(split_pdf(data,[],size=1,names=names,manifest=True,review_token=review['review_token']))) as z,f.open(stream=data) as source:
        receipt=json.loads(z.read('reapdf-division.json'));assert receipt['native_content_verified']
        for i,record in enumerate(receipt['parts']):
            assert record['name']==names[i]+'.pdf' and record['tagged'] and record['native_content_verified']
            with f.open(stream=z.read(record['name'])) as part:
                assert len(part)==1 and part[0].get_text()==source[i].get_text()
                assert part[0].get_pixmap().samples==source[i].get_pixmap().samples
                assert part[0].get_label()==f'P-{i+1}'
                objects=' '.join(part.xref_object(x) for x in range(1,part.xref_length()))
                assert '/ActualText' in objects and '/Layout' in objects


def test_cross_page_alternative_rejected_during_preflight_but_group_can_stay_whole():
    with f.open(stream=create(2,2)) as doc:
        root=int(doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[1].split()[0]);node=int(doc.xref_get_key(root,'K')[1].split()[0]);doc.xref_set_key(node,'ActualText','(Whole document alternative)');data=doc.tobytes()
    with pytest.raises(DocumentError,match='distintas partes'):inspect_split(data,[],size=1)
    assert len(inspect_split(data,[],size=2)['parts'])==1
    assert len(inspect_split(data,[],size=1,preserve_tags=False)['parts'])==2


def test_review_token_stable_and_rejects_changed_configuration():
    data=create(2,2);review=inspect_split(data,[],size=1)
    assert inspect_split(data,[],size=1)['review_token']==review['review_token']
    with pytest.raises(DocumentError,match='cambió'):split_pdf(data,[],size=2,review_token=review['review_token'])
    assert inspect_split(data,[],size=1,preserve_tags=False)['review_token']==inspect_split(data,[],size=1,preserve_tags=False)['review_token']


def test_corrupt_generated_part_is_not_published(monkeypatch):
    from backend import page_tools
    data=create(2,2)
    original=page_tools.organize_pdf
    def corrupt(*a,**kw):
        part=original(*a,**kw)
        with f.open(stream=part) as doc:doc[0].insert_text((100,100),'Unexpected content');return doc.tobytes()
    monkeypatch.setattr(page_tools,'organize_pdf',corrupt)
    with pytest.raises(DocumentError,match='No se publica'):split_pdf(data,[],size=1)


@pytest.mark.parametrize('value',['<</O /Layout /BBox [0 0 -1 2]>>','<</O /Layout /Unknown 1>>','[<</O /Layout>> -1]'])
def test_invalid_layout_attributes_still_rejected(value):
    with f.open(stream=create(1,2)) as doc:
        target=next(x for x in range(1,doc.xref_length()) if doc.xref_get_key(x,'S')==('name','/P'));doc.xref_set_key(target,'A',value);data=doc.tobytes()
    with pytest.raises(DocumentError):inspect_split(data,[],size=1)


def test_layout_bounding_box_is_retained_on_its_own_page():
    with f.open(stream=create(2,2)) as doc:
        target=next(x for x in range(1,doc.xref_length()) if doc.xref_get_key(x,'S')==('name','/P'))
        doc.xref_set_key(target,'A','<</O /Layout /BBox [10 20 100 50] /Placement /Block /Width 90 /Height 30 /Color [0.2 0.3 0.4]>>');data=doc.tobytes()
    with ZipFile(BytesIO(split_pdf(data,[],size=1))) as z,f.open(stream=z.read('parte-001.pdf')) as doc:
        objects=' '.join(doc.xref_object(x) for x in range(1,doc.xref_length()))
        assert '/BBox [ 10 20 100 50 ]' in objects and '/Placement /Block' in objects
