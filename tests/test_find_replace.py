from copy import deepcopy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.find_replace import inspect,replace


def source(rotation=0):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'COD-1 COD-1 cod-1 COD-10',fontsize=16)
        p.insert_text((40,160),'OTRO TEXTO',fontname='hebo',fontsize=18);p.set_rotation(rotation)
        p=d.new_page();p.insert_text((40,80),'COD-1',fontsize=16)
        d.new_page();return d.tobytes()

def query(**kwargs):return {'text':'COD-1','pages':[0,1,2],'case_sensitive':False,'whole_word':True,**kwargs}

@pytest.mark.parametrize('sensitive,whole,count',[(False,True,4),(True,True,3),(False,False,5),(True,False,4)])
def test_literal_case_words_pages_and_empty_pages(sensitive,whole,count):
    r=inspect(source(),[],query(case_sensitive=sensitive,whole_word=whole))
    assert len(r['matches'])==count and r['empty_pages']==[2] and all(m['editable'] for m in r['matches'])

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_selective_atomic_replacement_repeats_within_run_and_preserves_other_pages(rotation):
    base=source(rotation);q=query();r=inspect(base,[],q)
    selected=[m['id'] for m in r['matches'] if m['page']==0][:2]
    out,token,count=replace(base,[],q,r['receipt'],selected,'X')
    assert count==2 and token
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert 'X X cod-1 COD-10' in after[0].get_text() and 'OTRO TEXTO' in after[0].get_text()
        assert before[1].get_pixmap().samples==after[1].get_pixmap().samples and after[0].rotation==rotation

@pytest.mark.parametrize('kind',['receipt','id','duplicate','replacement','overflow'])
def test_invalid_or_stale_plan_does_not_modify_source(kind):
    base=source();q=query();r=inspect(base,[],q);receipt=r['receipt'];selected=[r['matches'][0]['id']];value='X'
    if kind=='receipt':receipt='stale'
    if kind=='id':selected=['unknown']
    if kind=='duplicate':selected*=2
    if kind=='replacement':value='x\ny'
    if kind=='overflow':value='X'*1000
    with pytest.raises(DocumentError):replace(base,[],q,receipt,selected,value)
    assert len(inspect(base,[],q)['matches'])==4

def test_empty_replacement_and_receipt_binds_pending_operations():
    base=source();q=query();ops=[{'type':'text','page':1,'span_id':'0:0:0','text':'COD-2'}]
    r=inspect(base,ops,q);assert len(r['matches'])==3 and r['receipt']==inspect(base,ops,q)['receipt']
    with pytest.raises(DocumentError):replace(base,[],q,r['receipt'],[r['matches'][0]['id']],'')
    out,_,_=replace(base,ops,q,r['receipt'],[m['id'] for m in r['matches']],'')
    with f.open(stream=out) as d:assert 'COD-2' in d[1].get_text() and 'COD-10' in d[0].get_text()

def test_layer_page_is_searchable_but_not_replaceable():
    with f.open(stream=source()) as d:d.add_ocg('Layer');base=d.tobytes()
    r=inspect(base,[],query());assert r['matches'] and not any(m['editable'] for m in r['matches'])

@pytest.mark.parametrize('change',[{'text':''},{'pages':[-1]},{'pages':[0,0]},{'case_sensitive':'yes'},{'whole_word':1},{'text':'x\ny'}])
def test_invalid_search_options(change):
    with pytest.raises(DocumentError):inspect(source(),[],query(**change))

def test_api_preview_token_and_exported_content():
    with TestClient(app) as client:
        uploaded=client.post('/api/documents',files={'file':('test.pdf',source(),'application/pdf')});assert uploaded.status_code==200
        identity=uploaded.json()['id'];url=f'/api/documents/{identity}/find-replace';q=query()
        r=client.post(url,json={'query':q}).json();payload={'query':q,'receipt':r['receipt'],'selected':[m['id'] for m in r['matches']],'replacement':'X'}
        assert client.post(url+'/apply',json=payload).status_code==422
        preview=client.post(url+'/apply',json={**payload,'preview':True});assert preview.status_code==200,preview.text
        p=preview.json();assert p['count']==4 and len(p['images'])==2
        assert client.post(url+'/apply',json={**payload,'replacement':'Y','preview_token':p['token']}).status_code==422
        done=client.post(url+'/apply',json={**payload,'preview_token':p['token']});assert done.status_code==200,done.text
        export=client.post(f'/api/documents/{done.json()["id"]}/export',json={'operations':[]})
        with f.open(stream=export.content) as d:assert 'X X X COD-10' in d[0].get_text() and d[1].get_text().strip()=='X'
