import pymupdf as f
import pytest
from backend.pdf_content import placements
from backend.styled_text import inspect_styled,replace_styled
from tests.test_cff_forms_mixed import box_for


def source():
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='helv');p.insert_font(fontname='cour');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'BT /helv 14 Tf 1 0 0 1 40 740 Tm (FIRST) Tj ET BT 1 0 0 1 40 700 Tm (SECOND) Tj ET q BT /cour 18 Tf 1 0 0 1 40 660 Tm (THIRD) Tj ET Q BT 1 0 0 1 40 620 Tm (FOURTH) Tj ET');p.set_contents(x);return d.tobytes()


def test_text_font_and_size_persist_bt_et_and_restore_q_Q():
    with f.open(stream=source()) as d:objects=placements(d[0].read_contents())['texts']
    assert [(o['font'],o['size']) for o in objects]==[('helv',14),('helv',14),('cour',18),('helv',14)]


@pytest.mark.parametrize('text,new',[('SECOND','SECON'),('THIRD','THIR'),('FOURTH','FOURT')])
def test_inherited_original_font_can_be_edited_on_page(text,new):
    base=source();box=box_for(base,text);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':new}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert new in b[0].get_text()
        for neighbor in ['FIRST','SECOND','THIRD','FOURTH']:
            if neighbor!=text:assert a[0].search_for(neighbor)==b[0].search_for(neighbor)
        assert [(s['font'],s['size']) for bl in a[0].get_text('dict',sort=True)['blocks'] for l in bl['lines'] for s in l['spans']]==[(s['font'],s['size']) for bl in b[0].get_text('dict',sort=True)['blocks'] for l in bl['lines'] for s in l['spans']]


@pytest.mark.parametrize('second,expected',[('1 0 0 1',True),('-1 0 0 1',False),('1 .2 0 1',False),('0 1 -1 0',False)])
def test_multi_show_orientation_proof_checks_every_text_matrix(second,expected):
    from backend.affine_text import horizontal_content
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='helv');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,('BT /helv 14 Tf 1 0 0 1 40 740 Tm (FIRST) Tj '+second+' 100 600 Tm (SECOND) Tj ET').encode());p.set_contents(x)
        assert horizontal_content(p) is expected
