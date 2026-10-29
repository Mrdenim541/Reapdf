"""PDF geometry, style and atomicity acceptance for split text and larger batches."""
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.find_replace import inspect,replace


def query(text='MMMM',pages=None,whole=False):
    return {'text':text,'pages':[0] if pages is None else pages,'case_sensitive':True,'whole_word':whole}


def source(rotation=0, gap=0, count=1):
    with f.open() as doc:
        page=doc.new_page(width=600,height=1000)
        for i in range(count):
            x,y=40,40+i*18
            for text,font,color in [('MM','helv',(0,0,0)),('MM','hebo',(.2,.3,.5)),(' QQ','heit',(.5,.1,.2))]:
                page.insert_text((x,y),text,fontname=font,fontsize=12,color=color)
                x+=f.get_text_length(text,fontname=font,fontsize=12)+gap
        page.set_rotation(rotation)
        doc.new_page().insert_text((40,80),'NEIGHBOR PAGE')
        return doc.tobytes()


def spans(doc):
    rows=[s for b in doc[0].get_text('dict',flags=f.TEXTFLAGS_TEXT|f.TEXT_INHIBIT_SPACES)['blocks'] for line in b.get('lines',[]) for s in line['spans']]
    return sorted(rows,key=lambda s:(round(s['origin'][1],2),s['origin'][0]))


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_cross_style_match_replaces_both_runs_and_keeps_suffix_and_other_page(rotation):
    base=source(rotation);q=query(whole=True);r=inspect(base,[],q)
    assert len(r['matches'])==1 and r['matches'][0]['split'] and r['matches'][0]['editable']
    out,_,count=replace(base,[],q,r['receipt'],[r['matches'][0]['id']],'NNNN')
    with f.open(stream=base) as a,f.open(stream=out) as b:
        before,after=spans(a),spans(b)
        assert count==1 and [s['text'] for s in after]==['NN','NN',' QQ']
        for old,new in zip(before,after):
            assert (old['font'],old['color'],old['size'])==(new['font'],new['color'],new['size'])
            assert new['origin']==pytest.approx(old['origin'],abs=.01)
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and b[0].rotation==rotation
        assert 'MMMM' not in b[0].get_text().replace('\n','')


@pytest.mark.parametrize('replacement',['X',''])
def test_shorter_and_empty_split_replacement_preserve_outside_text(replacement):
    base=source();q=query();r=inspect(base,[],q)
    out,_,count=replace(base,[],q,r['receipt'],[r['matches'][0]['id']],replacement)
    with f.open(stream=out) as doc:
        assert count==1 and [s['text'] for s in spans(doc)]==([replacement] if replacement else [])+[' QQ']


def test_partial_cross_fragment_match_retains_prefix_and_suffix():
    base=source();q=query('MMM');r=inspect(base,[],q)
    out,_,_=replace(base,[],q,r['receipt'],[r['matches'][0]['id']],'NNN')
    with f.open(stream=out) as doc:assert [s['text'] for s in spans(doc)]==['NN','NM',' QQ']


def test_whole_word_respects_text_outside_run_boundary():
    assert not inspect(source(),[],query('MM',whole=True))['matches']
    assert len(inspect(source(),[],query('MMMM',whole=True))['matches'])==1


def test_does_not_join_columns_or_infer_missing_spaces():
    base=source(gap=25)
    assert not inspect(base,[],query())['matches']
    assert len(inspect(base,[],query('MM'))['matches'])==2
    with f.open() as doc:
        page=doc.new_page();page.insert_text((40,40),'MM');page.insert_text((40,65),'MM');data=doc.tobytes()
    assert not inspect(data,[],query())['matches']


def test_multiple_matches_in_same_group_are_applied_right_to_left():
    with f.open() as doc:
        page=doc.new_page();x=40
        for text,font in [('MMM','helv'),('MMM','hebo')]:
            page.insert_text((x,80),text,fontname=font,fontsize=12)
            x+=f.get_text_length(text,fontname=font,fontsize=12)
        base=doc.tobytes()
    q=query('MM');r=inspect(base,[],q);assert len(r['matches'])==3 and r['matches'][1]['split']
    out,_,_=replace(base,[],q,r['receipt'],[m['id'] for m in r['matches']],'N')
    with f.open(stream=out) as doc:assert ''.join(s['text'] for s in spans(doc))=='NNN'


def test_late_cross_style_overflow_is_atomic():
    base=source(count=3);q=query();r=inspect(base,[],q)
    with pytest.raises(DocumentError,match='No se aplicó ningún cambio'):
        replace(base,[],q,r['receipt'],[m['id'] for m in r['matches']],'MMMMMMMMMMMMM')
    assert len(inspect(base,[],q)['matches'])==3


def test_one_hundred_runs_across_pages_are_written_in_one_snapshot():
    with f.open() as doc:
        for i in range(4):
            page=doc.new_page()
            for row in range(25):page.insert_text((40,30+row*25),'REG',fontsize=12)
        base=doc.tobytes()
    q=query('REG',list(range(4)));r=inspect(base,[],q);assert len(r['matches'])==100
    out,_,count=replace(base,[],q,r['receipt'],[m['id'] for m in r['matches']],'X')
    with f.open(stream=out) as doc:assert count==100 and all(page.get_text().split()==['X']*25 for page in doc)


def test_run_limit_counts_all_touched_parts_not_just_matches():
    base=source(count=51);q=query();r=inspect(base,[],q)
    assert len(r['matches'])==51
    with pytest.raises(DocumentError,match='100 fragmentos'):
        replace(base,[],q,r['receipt'],[m['id'] for m in r['matches']],'NNNN')


def test_search_rejects_del_control():
    with pytest.raises(DocumentError):inspect(source(),[],query('\x7f'))
