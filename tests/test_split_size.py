from io import BytesIO
from zipfile import ZipFile
import json
import pytest
import pymupdf as f
from backend.page_tools import inspect_split,split_pdf
from backend.pages import organize_pdf
from backend.engine import DocumentError
from backend.split_size import groups_by_bytes


def sample(count=7):
    with f.open() as d:
        for i in range(count):
            p=d.new_page(width=250,height=350);p.insert_text((20,50),f'PAGE {i+1} unchanged content');p.set_rotation(90 if i%2 else 0)
        return d.tobytes()


def limit(base):
    with f.open(stream=base) as d:
        return max(1024,max(len(organize_pdf(base,[],[{'page':i,'rotation':p.rotation}],extract=True,partition_tags=True)) for i,p in enumerate(d))+10)


def test_ordered_parts_are_under_actual_limit_with_custom_names_and_receipt():
    base=sample();maximum=limit(base);review=inspect_split(base,[],max_bytes=maximum);assert review['files']>1
    names=[f'1.46 PINTURA {i+1:03d}.pdf' for i in range(review['files'])];groups=[p['pages'] for p in review['parts']]
    checked=inspect_split(base,[],groups=groups,names=names,max_bytes=maximum)
    archive=split_pdf(base,[],groups=groups,names=names,max_bytes=maximum,manifest=True,review_token=checked['review_token'])
    with ZipFile(BytesIO(archive)) as z,f.open(stream=base) as original:
        manifest=json.loads(z.read('reapdf-division.json'));assert manifest['max_bytes_per_pdf']==maximum
        assert [p for part in manifest['parts'] for p in part['source_pages']]==list(range(1,len(original)+1))
        for part in manifest['parts']:
            data=z.read(part['name']);assert len(data)==part['bytes']<=maximum
            with f.open(stream=data) as d:
                for page,number in zip(d,part['source_pages']):assert page.get_pixmap().samples==original[number-1].get_pixmap().samples
        assert set(names)<=set(z.namelist())


@pytest.mark.parametrize('bad',[0,True,False,1023,1.5,'5000',100*1024*1024+1])
def test_bad_limits_fail_before_dividing(bad):
    with pytest.raises(DocumentError):inspect_split(sample(),[],max_bytes=bad)


def test_oversized_page_never_produces_a_partial_archive():
    with f.open() as d:
        import random
        p=d.new_page();pix=f.Pixmap(f.csRGB,128,128,random.Random(41).randbytes(128*128*3),False);p.insert_image(f.Rect(30,60,158,188),pixmap=pix);base=d.tobytes(deflate=False)
    with pytest.raises(DocumentError,match='supera el tamaño máximo'):split_pdf(base,[],max_bytes=1024)


def test_explicit_groups_are_checked_against_limit():
    base=sample();maximum=limit(base)
    with pytest.raises(DocumentError,match='Una parte supera'):inspect_split(base,[],groups=[list(range(7))],max_bytes=maximum)


def test_limit_is_bound_to_review_even_when_groups_stay_equal():
    base=sample(1);first=inspect_split(base,[],max_bytes=5000)
    with pytest.raises(DocumentError,match='cambió'):split_pdf(base,[],groups=[[0]],names=[first['parts'][0]['name']],max_bytes=6000,review_token=first['review_token'])


@pytest.mark.parametrize('options',[{'size':1},{'bookmark_level':1}])
def test_partition_modes_cannot_be_mixed(options):
    with pytest.raises(DocumentError,match='sin mezclar'):inspect_split(sample(),[],max_bytes=5000,**options)


def test_nonconsecutive_atomic_pages_keep_their_whole_interval():
    groups=groups_by_bytes(7,[[0,2],[4,5]],1800,lambda g:200+500*len(g));assert [p for g in groups for p in g]==list(range(7))
    assert any(set([0,2])<=set(g) for g in groups) and any(set([4,5])<=set(g) for g in groups)
    assert all(200+500*len(g)<=1800 for g in groups)


def test_atomic_group_that_cannot_fit_is_not_cut_to_meet_limit():
    with pytest.raises(DocumentError,match='inseparable 1–3'):groups_by_bytes(7,[[0,2]],1500,lambda g:200+500*len(g))


def test_size_is_measured_after_pending_edits():
    base=sample();ops=[{'type':'textbox','page':0,'points':[[20,80],[220,160]],'text':'ADDED CONTENT','font':'helv','size':12,'color':[0,0,0],'align':0}]
    review=inspect_split(base,ops,max_bytes=5000);assert review['complete_partition']
    with ZipFile(BytesIO(split_pdf(base,ops,max_bytes=5000))) as z:
        with f.open(stream=z.read(review['parts'][0]['name'])) as d:assert 'ADDED CONTENT' in d[0].get_text()


def test_tagged_parts_keep_structure_and_actual_size():
    from scripts.create_tagged_paragraph_sample import create
    base=create();maximum=limit(base);review=inspect_split(base,[],max_bytes=maximum);out=split_pdf(base,[],max_bytes=maximum,manifest=True)
    with ZipFile(BytesIO(out)) as z:
        for p in review['parts']:
            data=z.read(p['name']);assert len(data)<=maximum
            with f.open(stream=data) as d:assert d.xref_get_key(d.pdf_catalog(),'StructTreeRoot')[0]!='null'


def test_api_byte_limit_review_download_and_stale_token_are_connected():
    from fastapi.testclient import TestClient
    from backend.app import app
    from scripts.create_byte_split_sample import create
    base=create()
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Sized.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        r=c.post(url+'/split-plan',json={'max_bytes':60000});assert r.status_code==200,r.text
        groups=[p['pages'] for p in r.json()['parts']];names=[f'1.46 PINTURA {i+1:03d}' for i in range(len(groups))]
        config={'groups':groups,'names':names,'max_bytes':60000,'manifest':True};review=c.post(url+'/split-plan',json=config);assert review.status_code==200,review.text
        token=review.json()['review_token'];out=c.post(url+'/split',json={**config,'review_token':token});assert out.status_code==200,out.text
        with ZipFile(BytesIO(out.content)) as z:
            manifest=json.loads(z.read('reapdf-division.json'));assert manifest['max_bytes_per_pdf']==60000
            assert all(len(z.read(p['name']))<=60000 for p in manifest['parts'])
        assert c.post(url+'/export',json={}).content==base
        assert c.post(url+'/split',json={**config,'max_bytes':61000,'review_token':token}).status_code==422
        assert c.post(url+'/split-plan',json={'max_bytes':False}).status_code==422
