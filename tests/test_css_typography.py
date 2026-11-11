import pytest
import pymupdf as f
from backend.semantic_text import tree
from backend.text_typography import declarations
from backend.native_text import native_model
from backend.engine import DocumentError
from tests.test_paragraph_format import apply
from scripts.create_tagged_paragraph_sample import create


def source(classes=False,unit='pt',extra=''):
    with f.open(stream=create()) as d:
        t=tree(d);n=f.mupdf;root=n.pdf_to_num(t.root)
        for owner,rec in t.records.items():
            if n.pdf_to_name(n.pdf_dict_gets(rec['object'],'S'))!='Span':continue
            attr=f'<</O/CSS-1.00 /font-family(Helvetica)/font-size(18{unit})/font-weight(normal)/font-style(normal){extra}>>'
            if classes:d.xref_set_key(root,'ClassMap','<</Shared '+attr+'>>');d.xref_set_key(owner,'C','/Shared')
            else:d.xref_set_key(owner,'A',attr)
        return d.tobytes()


@pytest.mark.parametrize('classes',[False,True])
@pytest.mark.parametrize('unit',['pt','px'])
@pytest.mark.parametrize('family',['sans','serif','mono'])
def test_css_font_metadata_tracks_native_glyphs_and_preserves_shared_source(classes,unit,family):
    base=source(classes,unit);out,_=apply(base,{'family':family,'style':'bold-italic','size':12})
    with f.open(stream=out) as d,f.open(stream=base) as a:
        n=f.mupdf;t=tree(d);found=0
        for rec in t.records.values():
            for _,_,_,attr in declarations(d,rec['object']):
                if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))!='CSS-1.00':continue
                assert n.pdf_to_text_string(n.pdf_dict_gets(attr,'font-family')).startswith('DejaVu')
                assert n.pdf_to_text_string(n.pdf_dict_gets(attr,'font-size'))==('12pt' if unit=='pt' else '16px')
                assert n.pdf_to_text_string(n.pdf_dict_gets(attr,'font-weight'))=='bold' and n.pdf_to_text_string(n.pdf_dict_gets(attr,'font-style'))=='italic';found+=1
        assert found==2 and a[1].get_pixmap().samples==d[1].get_pixmap().samples
        assert all(r['editable'] and r['size']==pytest.approx(12) for r in native_model(d,0,d[0].rect)[1] if 'HELLO' in r['text'] or 'TEXT' in r['text'])
        if classes:assert a.xref_get_key(n.pdf_to_num(tree(a).root),'ClassMap/Shared')==d.xref_get_key(n.pdf_to_num(t.root),'ClassMap/Shared')


@pytest.mark.parametrize('unit',['pt','px'])
def test_original_family_only_updates_css_size_and_saved_output_can_reflow_again(unit):
    out,_=apply(source(unit=unit),{'family':'original','style':'keep','size':12});again,_=apply(out,{'family':'serif','style':'regular','size':15},words=1)
    with f.open(stream=out) as d:
        for rec in tree(d).records.values():
            for _,_,_,attr in declarations(d,rec['object']):
                if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(attr,'O'))=='CSS-1.00':assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(attr,'font-family'))=='Helvetica'
    with f.open(stream=again) as d:assert 'HELLO' in d[0].get_text()


@pytest.mark.parametrize('property,value',[('font-size','120%'),('font-size','calc(18pt)'),('font-size','-1pt'),('font-size','18em'),('font-weight','bolder'),('font-family','Arial, serif'),('font-family','Arial!important'),('font-style','inherit'),('transform','rotate(10deg)')])
def test_unresolved_css_cascade_units_or_layout_stays_protected(property,value):
    with f.open(stream=source()) as d:
        owner=next(k for k,r in tree(d).records.items() if f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(r['object'],'S'))=='Span');d.xref_set_key(owner,'A/'+property,f.get_pdf_str(value));base=d.tobytes()
    with pytest.raises((DocumentError,AssertionError)):apply(base,{'family':'sans','style':'regular','size':12})


@pytest.mark.parametrize('unit',['pt','px'])
def test_native_single_line_font_change_updates_css_and_keeps_other_content(unit):
    from tests.test_native_format import change
    from scripts.create_semantic_text_sample import source as semantic_source
    with f.open(stream=semantic_source('HELLO',tagged=True)) as d:
        row=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HELLO');d.xref_set_key(row['_semantic_identity'],'A',f'<</O/CSS-1.00 /font-size(18{unit})/font-family(Helvetica)/font-weight(400)/font-style(normal)>>');base=d.tobytes()
    out=change(base,family='sans',style='bold',size=12,text='HOLA')
    with f.open(stream=out) as d:
        row=next(r for r in native_model(d,0,d[0].rect)[1] if r['text']=='HOLA');assert row['format_editable'] and row['size']==pytest.approx(12)
        attr=declarations(d,tree(d).records[row['_semantic_identity']]['object'])[0][-1]
        assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(attr,'font-size'))==('12pt' if unit=='pt' else '16px')
        assert f.mupdf.pdf_to_text_string(f.mupdf.pdf_dict_gets(attr,'font-weight'))=='700'
