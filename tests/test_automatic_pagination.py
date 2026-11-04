import hashlib
import pytest,pymupdf as f
from backend.affine_reflow import reflow
from backend.engine import DocumentError
from tests.test_native_continuation import source,payload


def request(base):
    p=payload(base);p.pop('continuations');p['paginate']=True
    p['runs'][0]['text']='HELLO '*180;p['runs'][1]['text']='TEXT '*120;p['text']=''.join(r['text'] for r in p['runs'])
    return p


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('matrix',[(1,0,0,1),(1,.25,.15,1),(0,1,-1,0)])
def test_automatic_pages_keep_native_text_and_existing_pages(rotation,matrix):
    base=source(matrix,rotation,nested=True);p=request(base);original=hashlib.sha256(base).hexdigest()
    preview=reflow(base,[],preview=True,**p);out,r=reflow(base,[],preview=False,**p)
    assert preview==r and r['automatic_pagination'] and r['added_pages']>=1
    assert sum(v['characters'] for v in r['regions'])==len(p['text'])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert len(b)==len(a)+r['added_pages']
        for n in range(1,len(a)):assert a[n].get_pixmap().samples==b[n].get_pixmap().samples
        text=''.join(''.join(v.get_text().split()) for v in b)
        original_text=''.join(''.join(v.get_text().split()) for v in a)
        assert text.count('HELLO')==original_text.count('HELLO')-1+180 and text.count('TEXT')==original_text.count('TEXT')-1+120
        for n in range(len(a),len(b)):
            assert b[n].rotation==rotation and b[n].get_text().strip() and not b[n].get_images()
            assert b[n].mediabox.width==a[0].cropbox.width and b[n].mediabox.height==a[0].cropbox.height
    assert hashlib.sha256(base).hexdigest()==original


@pytest.mark.parametrize('value',[None,1,'true',{},[]])
def test_invalid_pagination_never_produces_a_copy(value):
    base=source();p=request(base);p['paginate']=value
    with pytest.raises(DocumentError,match='paginación'):reflow(base,[],preview=False,**p)


def test_manual_and_automatic_are_mutually_exclusive():
    base=source();p=payload(base);p['paginate']=True
    with pytest.raises(DocumentError,match='no ambas'):reflow(base,[],preview=False,**p)


def test_small_initial_height_preserves_the_borrowed_draft():
    base=source();p=request(base);p['height']=10
    with pytest.raises(DocumentError,match='alto inicial'):reflow(base,[],preview=False,**p)


def test_api_pagination_preview_apply_and_export():
    from fastapi.testclient import TestClient
    from backend.app import app
    base=source();p=request(base);p['page']=p.pop('number');p['id']=p.pop('identifier');p['ids']=p.pop('identifiers')
    with TestClient(app) as c:
        original=c.post('/api/documents',files={'file':('Example.pdf',base,'application/pdf')}).json()
        url=f"/api/documents/{original['id']}/reflow-affine"
        review=c.post(url,json={**p,'preview':True});assert review.status_code==200 and review.json()['added_pages']>0
        result=c.post(url,json=p);assert result.status_code==200,result.text
        edited=result.json();assert len(edited['pages'])>len(original['pages'])
        download=c.post(f"/api/documents/{edited['id']}/export",json={'operations':[]});assert download.status_code==200
        with f.open(stream=download.content) as d:assert 'TEXT' in d[-1].get_text()
