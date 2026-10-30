from io import BytesIO
from zipfile import ZipFile
import pymupdf as f
import pytest
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,reading_preview
from backend.page_tools import split_pdf
from backend.projects import build_project,read_project
from backend.engine import DocumentError
from tests.test_basic_tagging import source,selection
from tests.test_media_tagging import source as media,selection as media_selection


def tagged_lists(rotation=0):
    base=source(rotation=rotation);info=candidates(base,[]);entries=selection(info)
    for i in [1,2,4,5]:entries[i]['role']='LI'
    out,report=create(base,[],entries,reviewed=True);return base,out,report


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_semantic_lists_have_real_l_li_lbody_structure_without_paint_changes(rotation):
    base,out,report=tagged_lists(rotation);assert report['list_items']==4
    rows=model(out,[])['nodes'];assert sum(r['role']=='L' for r in rows)==2 and sum(r['role']=='LI' for r in rows)==4 and all(r['parent_valid'] for r in rows)
    assert reading_preview(out,[],0)['blocks'][1]['roles']==['Document','Sect','L','LI','LBody','P']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for p,q in zip(a,b):assert p.get_text()==q.get_text() and p.get_pixmap().samples==q.get_pixmap().samples
    restored,ops,_=read_project(build_project(out,[],{'name':'Lists.pdf'})[0]);assert model(restored,ops)['present']


def test_split_prunes_off_part_tags_and_keeps_only_part_list_content():
    _,base,_=tagged_lists()
    with ZipFile(BytesIO(split_pdf(base,[],size=1,names=['First','Second']))) as z:
        for name in z.namelist():
            part=z.read(name);rows=model(part,[])['nodes'];assert sum(r['role']=='Sect' for r in rows)==1 and sum(r['role']=='LI' for r in rows)==2
            assert all(r['page'] in [0,None] for r in rows)
            assert reading_preview(part,[],0)['untagged_blocks']==0


def test_off_part_private_alternatives_and_annotation_parent_keys_removed():
    a=media(links=False,repeated=False)
    with f.open(stream=a) as d,f.open(stream=a) as other:
        d.insert_pdf(other);base=d.tobytes()
    info=candidates(base,[]);entries=media_selection(info)
    for entry,original in zip(entries,info['entries']):
        if original['kind']=='image':entry['role']='Figure';entry['alt']='SECRET-SECOND' if original['page']==1 else 'FIRST-ONLY'
    tagged,_=create(base,[],entries,reviewed=True)
    with ZipFile(BytesIO(split_pdf(tagged,[],size=1))) as z,f.open(stream=z.read('parte-001.pdf')) as doc:
        strings=' '.join(doc.xref_object(x) for x in range(1,doc.xref_length()));assert 'SECRET-SECOND' not in strings and 'FIRST-ONLY' in strings
    tagged,_=create(media(),[],media_selection(candidates(media(),[])),reviewed=True)
    with ZipFile(BytesIO(split_pdf(tagged,[],size=1))) as z,f.open(stream=z.read('parte-001.pdf')) as doc:
        link=doc[0].get_links()[0];key=doc.xref_get_key(link['xref'],'StructParent');assert key[0]=='int' and doc.xref_get_key(doc[0].xref,'StructParents')[1]=='0'


@pytest.mark.parametrize('feature',['IDTree','ClassMap','Ref','ActualText','cycle'])
def test_unverified_tag_graph_is_not_silently_copied(feature):
    _,base,_=tagged_lists()
    with f.open(stream=base) as d:
        info=model(base,[]);root=info['root'];node=info['nodes'][0]['id']
        if feature in ['IDTree','ClassMap']:d.xref_set_key(root,feature,'<<>>')
        elif feature=='Ref':d.xref_set_key(node,'Ref',f'[{node} 0 R]')
        elif feature=='ActualText':d.xref_set_key(node,'ActualText','(Cross-page replacement text)')
        else:d.xref_set_key(node,'K',f'[{node} 0 R]')
        bad=d.tobytes()
    with pytest.raises(DocumentError):split_pdf(bad,[],size=1)


def test_direct_mcr_content_references_survive_partition():
    _,base,_=tagged_lists()
    with f.open(stream=base) as d:
        row=next(r for r in model(base,[])['nodes'] if r['role']=='H1')
        d.xref_set_key(row['id'],'K',f'<</Type/MCR /Pg {d[0].xref} 0 R /MCID 0>>');base=d.tobytes()
    original=reading_preview(base,[],0)
    with ZipFile(BytesIO(split_pdf(base,[],size=1))) as z:
        data=z.read('parte-001.pdf');report=reading_preview(data,[],0)
        assert [(b['text'],b['roles']) for b in report['blocks']]==[(b['text'],b['roles']) for b in original['blocks']]
        # MuPDF does not expose this MCR's role in the source preview either.
        # Independently verify its native parent key and retained page reference.
        from pyhanko.pdf_utils.reader import PdfFileReader
        reader=PdfFileReader(BytesIO(data));nums=reader.root['/StructTreeRoot']['/ParentTree']['/Nums'];owner=nums[1][0]
        assert str(owner['/S'])=='/H1' and str(owner['/K']['/Type'])=='/MCR' and int(owner['/K']['/MCID'])==0
        page_ref=list.__getitem__(reader.root['/Pages']['/Kids'],0)
        assert owner['/K'].raw_get('/Pg').idnum==page_ref.idnum
