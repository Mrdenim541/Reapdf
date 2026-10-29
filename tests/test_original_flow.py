from copy import deepcopy
import re
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.text_flow import inspect_flow,flow_text
from tests.test_mixed_flow import mixed_source
from tests.test_cff_forms_mixed import cff_pdf,box_for


def regions():return [{'page':0,'box':[20,40,350,80],'replace':True},{'page':1,'box':[20,40,350,330],'replace':False}]


def plans(base,rs):
    m=inspect_flow(base,[],rs);assert m['original_supported'],m['original_reason']
    runs=[{'id':r['id'],'text':r['text']*12} for r in m['original_runs']]
    return runs,''.join(r['text'] for r in runs)


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('align',[0,1,2,3])
def test_original_fonts_cross_pages_without_substitution(rotation,align):
    base=mixed_source(rotation);rs=regions();runs,text=plans(base,rs)
    out,report=flow_text(base,[],rs,text,original_runs=runs,align=align)
    assert report['mode']=='original' and report['complete'] and report['text_verified']
    assert all(r['characters']>0 for r in report['regions'])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[2].get_pixmap().samples==b[2].get_pixmap().samples
        programs={hash(a.extract_font(v[0])[3]) for v in a[0].get_fonts()}
        assert programs <= {hash(b.extract_font(v[0])[3]) for p in b for v in p.get_fonts()}
        styles=[]
        for p in b:
            assert p.rotation==rotation;p.set_rotation(0)
            styles += [(s['font'],round(s['size']),s['color']) for bl in p.get_text('dict')['blocks'] for l in bl.get('lines',[]) for s in l['spans'] if not s['text'].startswith(('Pie ','Otra '))]
        assert len(set(styles))==3
        assert 'Pie original conservado' in b[0].get_text() and 'Pie destino conservado' in b[1].get_text()
        assert re.sub(r'\s+','',b[0].get_text(clip=f.Rect(20,40,370,120))+b[1].get_text(clip=f.Rect(20,40,370,370)))==re.sub(r'\s+','',text)


def test_original_cff_cross_page_program_and_unicode_failure_atomic():
    base=cff_pdf('cid');rs=[{'page':0,'box':box_for(base),'replace':True},{'page':0,'box':[35,350,180,300],'replace':False}];runs,text=plans(base,rs)
    out,r=flow_text(base,[],rs,text,original_runs=runs)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        left=next(i for i in a[0].get_fonts() if i[4]=='Original');right=next(i for i in b[0].get_fonts() if i[4].startswith('ReapdfFlow'))
        assert a.extract_font(left[0])[3]==b.extract_font(right[0])[3]
    runs[0]['text']+='Ω'
    with pytest.raises(DocumentError):flow_text(base,[],rs,text+'Ω',original_runs=runs)
    assert inspect_flow(base,[],rs)['original_supported']


def test_original_flow_overflow_autofit_ids_and_exclusive_modes():
    base=mixed_source();rs=regions()[:1];runs,text=plans(base,rs)
    with pytest.raises(DocumentError,match='no cabe'):flow_text(base,[],rs,text,original_runs=runs)
    out,r=flow_text(base,[],rs,text,original_runs=runs,auto_fit=True,min_size=6)
    assert r['adjusted'] and r['mixed']['min_size']>=6
    bad=deepcopy(runs);bad[0]['id']='unknown'
    with pytest.raises(DocumentError,match='orden'):flow_text(base,[],rs,text,original_runs=bad)
    with pytest.raises(DocumentError,match='solo modo'):flow_text(base,[],rs,text,original_runs=runs,runs=[])


def test_original_flow_preview_api_apply_and_base_preserved():
    base=mixed_source();rs=regions();runs,text=plans(base,rs)
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('mixed.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id'];payload={'regions':rs,'text':text,'original_runs':runs}
        response=c.post(url+'/flow-text',json={**payload,'preview':True});assert response.status_code==200,response.text
        assert response.json()['report']['mode']=='original' and len(response.json()['previews'])==2
        assert c.post(url+'/flow-text',json=payload).status_code==200
        assert c.post(url+'/export',json={'operations':[]}).content==base
