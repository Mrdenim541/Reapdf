import pytest,pymupdf as f
from backend.automation import validate_recipe,process_recipe
from backend.page_ranges import parse
from backend.engine import DocumentError
from tests.test_automation import recipe,rows
from tests.test_batch_tools import source


@pytest.mark.parametrize('value,expected',[('1-9/2',[0,2,4,6,8]),('3, 1-2',[2,0,1]),('2-8/3',[1,4,7])])
def test_page_range_strides_and_order(value,expected):assert parse(value,9)==expected


@pytest.mark.parametrize('value',['1/2','1-9/0','1-9/10','1-9/1.5','1-9/2,3','2-1','10','0',''])
def test_invalid_ranges_and_duplicates_are_rejected(value):
    with pytest.raises(DocumentError):parse(value,9)


def test_different_pages_for_numbering_and_watermark_and_manifest():
    plan=recipe({'type':'watermark','text':'REVISADO','size':24,'opacity':.2,'angle':0,'color':[.3,.3,.3],'pages':'1-3/2'}, {'type':'numbering','template':'N {numero}','start':7,'size':10,'pages':'2'})
    z,r=rows(process_recipe([('Example.pdf',source(pages=3),[])],plan));row=r['documents'][0]
    with f.open(stream=z.read(row['file'])) as d:
        assert 'REVISADO' in d[0].get_text() and 'REVISADO' not in d[1].get_text() and 'REVISADO' in d[2].get_text()
        assert 'N 7' in d[1].get_text() and 'N 7' not in d[0].get_text()
    assert row['steps'][0]['details']['selected_pages']==[0,2] and row['steps'][1]['details']['selected_pages']==[1]


def test_out_of_range_in_later_document_is_atomic():
    plan=recipe({'type':'text','pages':'2'})
    with pytest.raises(DocumentError,match='Documento 2'):process_recipe([('Two.pdf',source(pages=2),[]),('One.pdf',source(),[])],plan)


def test_global_transform_does_not_accept_a_page_subset():
    with pytest.raises(DocumentError):validate_recipe(recipe({'type':'optimize','pages':'1'}))
