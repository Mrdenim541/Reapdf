from io import BytesIO
import pymupdf as f
import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont,newTable
from backend.cff_fonts import CFFFace
from backend.engine import DocumentError
from backend.styled_text import inspect_styled,replace_styled
from tests.test_cff_forms_mixed import box_for


def program(variable=False):
    b=FontBuilder(1000,isTTF=False);order=['.notdef','A','B','C','space'];b.setupGlyphOrder(order);b.setupCharacterMap({ord(c):c for c in 'ABC'}|{32:'space'});b.setupHorizontalMetrics({n:(600,0) for n in order});b.setupHorizontalHeader(ascent=800,descent=-200);b.setupNameTable({'familyName':'ReapdfCFF2','styleName':'Regular','psName':'ReapdfCFF2'});b.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);b.setupPost();strings={}
    for i,name in enumerate(order):
        p=T2CharStringPen(None,None,CFF2=True)
        if name not in ['.notdef','space']:
            p.moveTo((40,0));p.lineTo((500-i*40,0));p.lineTo((500-i*40,700));p.lineTo((40,700));p.closePath()
        strings[name]=p.getCharString()
    b.setupCFF2(strings)
    if variable:b.setupFvar([('wght',100,400,900,'Weight')],[])
    out=BytesIO();b.save(out);return out.getvalue()


def source(rotation=0,form=False,simple=False):
    with f.open() as d:
        p=d.new_page();p.insert_font(fontname='Original',fontbuffer=program(),set_simple=simple);p.insert_text((50,120),'ABC ABC',fontname='Original',fontsize=20,color=(.2,.4,.8));p.insert_text((40,400),'UNCHANGED');base=d.tobytes()
    if form:
        with f.open(stream=base) as src,f.open() as d:
            p=d.new_page();p.show_pdf_page(p.rect,src,0);d.xref_set_key(p.get_xobjects()[0][0],'Matrix','[1 .1 .1 1 0 0]');d.new_page().show_pdf_page(f.Rect(0,0,595,842),src,0);d[0].set_rotation(rotation);return d.tobytes()
    with f.open(stream=base) as d:d[0].set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form,simple',[(False,False),(False,True),(True,False)])
def test_static_cff2_keeps_program_style_and_page(rotation,form,simple):
    base=source(rotation,form,simple);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and b[0].rotation==rotation
        original=next(v for v in a[0].get_fonts() if v[4]=='Original');edited=next(v for v in b[0].get_fonts() if v[4]=='Original');assert a.extract_font(original[0])[3]==b.extract_font(edited[0])[3]
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':row['id'],'text':'ABC Z'}])


def test_cff2_variable_is_not_silently_read_as_default():
    with pytest.raises(DocumentError,match='variable'):CFFFace(program(True),'OpenType')


def test_cff2_outline_budget_and_raw_subtype():
    face=CFFFace(program(),'OpenType');assert face.has_outline(1);face.remaining=0
    with pytest.raises(DocumentError,match='presupuesto'):face.has_outline(2)
    with pytest.raises(DocumentError):CFFFace(program(),'Type1C')


def test_cff2_variation_store_even_without_fvar_is_refused():
    font=TTFont(BytesIO(program()));top=font['CFF2'].cff.topDictIndex[0]
    from fontTools.cffLib import VarStoreData
    from fontTools.varLib.builder import buildVarStore,buildVarRegionList,buildVarData
    regions=buildVarRegionList([{'wght':(0,1,1)}],['wght']);top.VarStore=VarStoreData(otVarStore=buildVarStore(regions,[buildVarData([0],[[0]])]));out=BytesIO();font.save(out)
    with pytest.raises(DocumentError,match='variaciones'):CFFFace(out.getvalue(),'OpenType')


def test_variable_truetype_requires_a_verified_instance():
    from fontTools.ttLib.tables._f_v_a_r import Axis
    from pathlib import Path
    from backend.styled_text import TrueType
    font=TTFont(Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf');table=newTable('fvar');table.axes=[];table.instances=[]
    axis=Axis();axis.axisTag='wght';axis.minValue=100;axis.defaultValue=400;axis.maxValue=900;axis.flags=0;axis.axisNameID=256;table.axes.append(axis);font['fvar']=table;out=BytesIO();font.save(out)
    with pytest.raises(DocumentError,match='variable'):TrueType(out.getvalue())
