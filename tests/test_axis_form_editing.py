import pymupdf as f
import pytest
from backend.styled_text import inspect_styled,replace_styled
from backend.engine import DocumentError
from tests.test_cff_forms_mixed import box_for


def source(sx,sy,rotation=0,form=True):
    with f.open() as d:
        p=d.new_page(width=600,height=750)
        if form:
            with f.open() as other:
                other.new_page(width=250,height=120).insert_text((25,60),'HELLO TEXT',fontsize=18)
                p.show_pdf_page(f.Rect(25,30,25+250*sx,30+120*sy),other,0,keep_proportion=False)
                p.show_pdf_page(f.Rect(25,400,275,520),other,0)
                d.new_page().show_pdf_page(f.Rect(25,30,275,150),other,0)
        else:
            p.insert_text((25,60),'HELLO TEXT',fontsize=18)
            x=p.get_contents()[0];d.update_stream(x,f'q {sx} 0 0 {sy} 0 0 cm '.encode()+d.xref_stream(x)+b' Q')
        d[0].set_rotation(rotation)
        return d.tobytes()


@pytest.mark.parametrize('sx,sy',[(1.6,.7),(.6,1.4),(1.2,1.8)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_nonuniform_form_preserves_transform_font_other_occurrences(sx,sy,rotation):
    base=source(sx,sy,rotation);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0]
    assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().splitlines()==['HELLO TEX','HELLO TEXT']
        assert b[0].rotation==rotation and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        a[0].set_rotation(0);b[0].set_rotation(0)
        left=a[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0];right=b[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
        assert right['origin']==pytest.approx(left['origin']) and right['size']==pytest.approx(left['size'])
        assert a[0].get_fonts()[0][3:5]==b[0].get_fonts()[0][3:5]


def test_nonuniform_direct_text_and_form_expansion_clipping():
    base=source(1.4,.6,form=False);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=out) as d:assert d[0].get_text().strip()=='HELLO TEX'
    base=source(1.,1.);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];box[2]=500
    with pytest.raises(DocumentError,match='recorte'):replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEXT HELLO TEXT HELLO TEXT'}],True)


@pytest.mark.parametrize('kind',['cid','open','truetype'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_nonuniform_form_embedded_programs_are_preserved(kind,rotation):
    from tests.test_cff_forms_mixed import cff_pdf,FONT
    if kind=='truetype':
        with f.open() as s:
            p=s.new_page();p.insert_font(fontname='Original',fontfile=str(FONT));p.insert_text((40,100),'HELLO TEXT',fontname='Original',fontsize=18);p.insert_text((40,300),'UNCHANGED');data=s.tobytes()
    else:data=cff_pdf(kind)
    with f.open(stream=data) as s,f.open() as d:
        d.new_page().show_pdf_page(f.Rect(10,20,426.5,356.8),s,0,keep_proportion=False)
        d.new_page().show_pdf_page(f.Rect(10,20,307.5,441),s,0)
        d[0].set_rotation(rotation);base=d.tobytes()
    box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'HELLO TEX' in b[0].get_text() and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        left=next(i for i in a[0].get_fonts() if i[4]=='Original');right=next(i for i in b[0].get_fonts() if i[4]=='Original')
        assert a.extract_font(left[0])[3]==b.extract_font(right[0])[3]
