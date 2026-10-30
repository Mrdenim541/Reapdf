from io import BytesIO
from zipfile import ZipFile
import json,hashlib
import pymupdf as f
import pytest
from backend.page_tools import split_pdf,inspect_split
from backend.split_plan import filename
from backend.engine import DocumentError,spans
from tests.test_page_tools import make_doc


def source():
    with f.open(stream=make_doc(count=6)) as d:
        d.set_toc([[1,'First section',2],[2,'Subsection',3],[1,'Second/section',5]]);return d.tobytes()


def test_named_independent_pdfs_preserve_pages_form_values_and_pending_edits():
    base=make_doc(widgets=True,rotation=90);names=['Portada','Anexo técnico.PDF'];groups=[[2,0],[1]]
    review=inspect_split(base,[],groups=groups,names=names);assert [p['name'] for p in review['parts']]==['Portada.pdf','Anexo técnico.PDF'] and not review['source_modified']
    archive=split_pdf(base,[],groups=groups,names=names,manifest=True)
    with ZipFile(BytesIO(archive)) as z,f.open(stream=base) as original:
        assert z.namelist()==['Portada.pdf','Anexo técnico.PDF','reapdf-division.json']
        report=json.loads(z.read('reapdf-division.json'));assert report['source_sha256']==hashlib.sha256(base).hexdigest()
        for part,group in zip(report['parts'],groups):
            assert part['source_pages']==[p+1 for p in group] and part['sha256']==hashlib.sha256(z.read(part['name'])).hexdigest()
            with f.open(stream=z.read(part['name'])) as doc:
                assert len(doc)==len(group)
                for p,n in zip(doc,group):assert p.get_pixmap().samples==original[n].get_pixmap().samples
    base=make_doc()
    with f.open(stream=base) as d:span=spans(d[0])[0]
    ops=[{'type':'text','page':0,'span_id':span['id'],'text':'CHANGED'}]
    with ZipFile(BytesIO(split_pdf(base,ops,size=2,names=['Edited','Other']))) as z,f.open(stream=z.read('Edited.pdf')) as d:assert 'CHANGED' in d[0].get_text()


def test_bookmark_sections_include_leading_pages_and_editable_sanitized_names():
    base=source();plan=inspect_split(base,[],bookmark_level=1)
    assert [p['pages'] for p in plan['parts']]==[[0],[1,2,3],[4,5]]
    assert [p['name'] for p in plan['parts']]==['001-Inicio.pdf','002-First section.pdf','003-Second_section.pdf']
    with ZipFile(BytesIO(split_pdf(base,[],bookmark_level=1,names=['Opening','Work A','Work B']))) as z:assert z.namelist()==['Opening.pdf','Work A.pdf','Work B.pdf']


@pytest.mark.parametrize('name',['../outside','folder/file','CON','con.txt','LPT¹','NUL.PDF',' a','a.','a ','','a\x00b','a:b','a\u202eb','x'*121,'é'*100])
def test_unsafe_output_names_fail_before_zip_publication(name):
    with pytest.raises(DocumentError):split_pdf(make_doc(),[],size=3,names=[name])


@pytest.mark.parametrize('names',[['A','a.PDF'],['café','cafe\u0301.PDF'],['Straße','STRASSE'],['Only'],['A',None]])
def test_duplicate_normalized_or_incomplete_name_lists_rejected(names):
    with pytest.raises(DocumentError):split_pdf(make_doc(),[],groups=[[0,1],[2]],names=names)


@pytest.mark.parametrize('level',[True,0,11,1.5,3])
def test_invalid_bookmark_levels_or_missing_level_rejected(level):
    with pytest.raises(DocumentError):inspect_split(source(),[],bookmark_level=level)


def test_ambiguous_bookmark_destinations_and_mixed_modes_rejected():
    with f.open(stream=source()) as d:
        d.set_toc([[1,'A',2],[1,'B',2]]);base=d.tobytes()
    with pytest.raises(DocumentError,match='distintas'):inspect_split(base,[],bookmark_level=1)
    with pytest.raises(DocumentError):inspect_split(source(),[],bookmark_level=1,size=2)
    with pytest.raises(DocumentError):split_pdf(source(),[],size=2,manifest='yes')


def test_api_review_and_named_zip_leave_original_byte_identical():
    from fastapi.testclient import TestClient
    from backend.app import app
    base=source()
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Combined.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=c.post(url+'/split-plan',json={'bookmark_level':1});assert r.status_code==200,r.text;assert r.json()['files']==3
        parts=r.json()['parts'];names=['Personal cover','Record','Plan'];groups=[p['pages'] for p in parts]
        result=c.post(url+'/split',json={'groups':groups,'names':names});assert result.status_code==200,result.text
        with ZipFile(BytesIO(result.content)) as z:assert z.namelist()==[n+'.pdf' for n in names]
        assert c.post(url+'/export',json={}).content==base
        assert c.post(url+'/split',json={'groups':groups,'names':['CON','B','C']}).status_code==422
