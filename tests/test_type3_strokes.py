import pymupdf as f
import pytest
from backend.styled_text import inspect_styled,replace_styled,OriginalFont
from backend.engine import DocumentError
from tests.test_type3_fonts import type3_pdf,mutate
from tests.test_cff_forms_mixed import box_for


def source(colored=False,form=False,rotation=0):
    with f.open(stream=type3_pdf(rotation=rotation,form=form)) as d:
        for x in range(1,d.xref_length()):
            if not d.xref_is_stream(x):continue
            data=d.xref_stream(x)
            if not data.startswith(b'600 0 0 -200 600 800 d1 '):continue
            path=data.split(b'd1 ',1)[1].replace(b' f',b' S');header=b'600 0 d0 ' if colored else b'600 0 0 -200 600 800 d1 '
            d.update_stream(x,header+b'q .9 .05 .02 .9 15 10 cm 12 w 1 J 1 j '+(b'0 0 1 RG ' if colored else b'')+path+b' Q')
        return d.tobytes()


@pytest.mark.parametrize('colored',[False,True])
@pytest.mark.parametrize('form',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_strokes_and_internal_affine_matrices_edit_with_original_program(colored,form,rotation):
    base=source(colored,form,rotation)
    with f.open(stream=base) as d:
        d[0].set_rotation(0);rect=d[0].search_for('ABC ABC')[0]+(-2,-2,2,2);box=[rect.x0,rect.y0,rect.width,rect.height]
    row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and 'UNCHANGED' in b[0].get_text()
        programs=lambda d:{d.xref_stream(x) for x in range(1,d.xref_length()) if d.xref_is_stream(x) and b'12 w 1 J 1 j' in d.xref_stream(x)}
        assert programs(a)==programs(b)
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples


@pytest.mark.parametrize('tail',[
 b'10 w 1 J 1 j 0 0 600 700 re S', # expanded stroke outside glyph box
 b'10 w 50 0 400 700 re S', # inherited cap/join are not guessed
 b'10 w 1 J 0 j 50 0 400 700 re S', # explicit miter required
 b'10 w 3 J 1 j 50 0 400 700 re S',
 b'0 0 0 0 0 0 cm 50 0 400 700 re f',
 b'1 0 0 1 1000 0 cm 50 0 400 700 re f',
 b'50 0 m 1 0 0 1 0 0 cm 400 700 l S',
 b'2 0 0 .1 0 0 cm 20 w 2 J 1 j 250 0 m 288 38 l S', # square cap under anisotropic CTM
 b'Q',b'q 50 0 400 700 re f',b'[3 2] 0 d 50 0 400 700 re S',
])
def test_unbounded_or_inherited_stroke_state_stays_protected(tail):
    bad=mutate(type3_pdf(),None,None,proc=b'600 0 0 -200 600 800 d1 '+tail)
    with f.open(stream=bad) as d:
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


@pytest.mark.parametrize('kind',['hidden','overprint'])
def test_type3_trace_reassembly_does_not_accept_hidden_or_duplicated_text(kind):
    with f.open(stream=source()) as d:
        page=d[0];data=page.read_contents();stream=d.get_new_xref();d.update_object(stream,'<<>>')
        data=data.replace(b'/Custom 20 Tf',b'/Custom 20 Tf 3 Tr') if kind=='hidden' else data+b'\n'+data
        d.update_stream(stream,data);page.set_contents(stream);base=d.tobytes()
    try:rows=inspect_styled(base,[],0,[90,175,110,45])['runs']
    except DocumentError:return
    assert not any(r['editable'] for r in rows)
