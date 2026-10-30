import pymupdf as f
import pytest
from backend.styled_text import OriginalFont,inspect_styled,replace_styled
from backend.engine import DocumentError
from tests.test_type3_fonts import type3_pdf
from tests.test_cff_forms_mixed import box_for


def source(rotation=0,form=False,transform='1 0 0 1',tail=None):
    with f.open(stream=type3_pdf(rotation,transform,form)) as d:
        for x in range(1,d.xref_length()):
            if d.xref_is_stream(x):
                data=d.xref_stream(x)
                if data.startswith(b'600 0 0 -200 600 800 d1 '):
                    path=data.split(b'd1 ',1)[1]
                    d.update_stream(x,b'600 0 d0 '+(tail if tail is not None else b'q 1 0 0 rg '+path+b' Q'))
        return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
@pytest.mark.parametrize('transform',['1 0 0 1','1 .2 .3 1'])
def test_original_colored_vectors_edit_in_page_and_isolate_forms(rotation,form,transform):
    base=source(rotation,form,transform);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and 'UNCHANGED' in b[0].get_text()
        before={a.xref_stream(x) for x in range(1,a.xref_length()) if a.xref_is_stream(x) and b'd0' in a.xref_stream(x)}
        after={b.xref_stream(x) for x in range(1,b.xref_length()) if b.xref_is_stream(x) and b'd0' in b.xref_stream(x)};assert before==after
        pix=b[0].get_pixmap();raw=pix.samples;assert any(raw[i]>180 and raw[i+1]<100 and raw[i+2]<100 for i in range(0,len(raw),pix.n))
        if form:assert 'ABC ABC' in b[1].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples


@pytest.mark.parametrize('tail',[b'2 0 0 rg 0 0 100 100 re f',b'0 0 100 100 re f',b'q 1 0 0 rg 0 0 10 10 re f',b'Q',b'0 0 1 rg /G gs',b'0 0 1 rg /X Do',b'0 0 1 rg 0 0 10 10 re S',b'0 0 1 rg 0 0 2000 20 re f'])
def test_unverified_colored_program_stays_protected(tail):
    with f.open(stream=source(tail=tail)) as d:
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))
