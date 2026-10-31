"""Synthetic public Type3 fixtures; no personal PDFs."""
from copy import deepcopy
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.styled_text import OriginalFont,inspect_styled,replace_styled,replace_styled_regions
from tests.test_cff_forms_mixed import box_for


def type3_pdf(rotation=0,transform='1 0 0 1',form=False,spacing=False):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,350),'UNCHANGED');font=d.get_new_xref();uni=d.get_new_xref();d.update_object(uni,'<<>>');d.update_stream(uni,b'1 begincodespacerange <00><ff> endcodespacerange 4 beginbfchar <20><0020><41><0041><42><0042><43><0043> endbfchar');procs=[]
        paths={'space':b'', 'A':b'50 0 m 300 700 l 550 0 l h f', 'B':b'50 0 400 700 re f', 'C':b'550 700 m 50 700 l 50 0 l 550 0 l 550 90 l 140 90 l 140 610 l 550 610 l h f'}
        for ch,path in paths.items():
            x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'600 0 0 -200 600 800 d1 '+path);procs.append(f'/{ch} {x} 0 R')
        widths=' '.join('600' for _ in range(68-32))
        d.update_object(font,f'<< /Type/Font /Subtype/Type3 /Name/Custom /FontBBox[0 -200 600 800] /FontMatrix[.001 0 0 .001 0 0] /FirstChar 32 /LastChar 67 /Widths[{widths}] /Encoding<</Type/Encoding /Differences[32 /space 65 /A /B /C]>> /CharProcs<<{" ".join(procs)}>> /Resources<<>> /ToUnicode {uni} 0 R >>');res=int(d.xref_get_key(p.xref,'Resources')[1].split()[0]);d.xref_set_key(res,'Font/Custom',f'{font} 0 R')
        x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,(f'q BT /Custom 20 Tf {"2 Tc 120 Tz" if spacing else ""} {transform} 100 640 Tm (ABC ABC) Tj ET Q').encode());p.set_contents(x);p.insert_text((40,350),'UNCHANGED');p.set_rotation(rotation)
        base=d.tobytes()
    if not form:return base
    with f.open(stream=base) as src,f.open() as d:
        p=d.new_page(width=650,height=1000);src[0].set_rotation(0);p.show_pdf_page(f.Rect(0,0,595,842),src,0);p.show_pdf_page(f.Rect(0,350,595,1192),src,0);d.new_page().show_pdf_page(f.Rect(0,0,595,842),src,0);d[0].set_rotation(rotation);return d.tobytes()


def glyphs(d):
    result={}
    for xref in range(1,d.xref_length()):
        if d.xref_is_stream(xref) and b'd1' in d.xref_stream(xref):result[d.xref_stream(xref)]=True
    return result


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('transform',['1 0 0 1','0 1 -1 0','1 .2 .3 1','-1 0 0 1','1 0 0 -1'])
@pytest.mark.parametrize('form',[False,True])
def test_type3_inline_original_resources_preserved(rotation,transform,form):
    base=type3_pdf(rotation,transform,form);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and b[0].rotation==rotation
        assert glyphs(a)==glyphs(b)
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        if form:
            assert b[0].get_text().count('ABC ABC')==1
            assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':row['id'],'text':'ABC Z'}])


def test_type3_spacing_and_deletion():
    base=type3_pdf(spacing=True);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':''}])
    with f.open(stream=out) as d:assert 'ABC' not in d[0].get_text()


def mutate(base,key,value,proc=None):
    with f.open(stream=base) as d:
        font=next(v[0] for v in d[0].get_fonts() if v[2]=='Type3')
        if proc is not None:
            x=int(d.xref_get_key(font,'CharProcs/A')[1].split()[0]);d.update_stream(x,proc)
        else:d.xref_set_key(font,key,value)
        return d.tobytes()


@pytest.mark.parametrize('key,value',[
 ('FontMatrix','[.002 0 0 .001 0 0]'),('FontBBox','[0 0 0 0]'),('Resources','<</ExtGState<<>>>>'),
 ('Encoding','<</BaseEncoding/WinAnsiEncoding/Differences[65/A/B/C]>>'),('Encoding','<</Differences[65/A 65/B]>>'),
 ('Encoding','<</Differences[256/A]>>'),('ToUnicode','null'),('Widths','[600]'),('FirstChar','-1'),('CharProcs','<<>>')])
def test_invalid_type3_stays_readonly(key,value):
    bad=mutate(type3_pdf(),key,value)
    with f.open(stream=bad) as d:
        item=next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3')
        with pytest.raises(DocumentError):OriginalFont(d,item)


@pytest.mark.parametrize('tail',[
 b'0 0 1 rg 0 0 20 20 re f',b'/X Do',b'BI ID xyz EI',b'BT (A) Tj ET',b'/G gs',b'0 0 m 2000 0 l h f',
 b'0 0 30 30 re S',b'0 0 m',b'0 0 l f',b'0 0 m 10 10 l',b'0 0 m f d1',
 b'0 0 20 20 re W W n',b'0 0 m '+b'1 1 l '*2001+b'f'])
def test_complex_type3_programs_refused(tail):
    bad=mutate(type3_pdf(),None,None,proc=b'600 0 0 -200 600 800 d1 '+tail)
    with f.open(stream=bad) as d:
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


@pytest.mark.parametrize('header',[b'600 0 d0',b'601 0 0 -200 600 800 d1',b'600 1 0 -200 600 800 d1',b'600 0 -10 -200 600 800 d1'])
def test_type3_conflicting_metrics_refused(header):
    bad=mutate(type3_pdf(),None,None,proc=header+b' 50 0 400 700 re f')
    with f.open(stream=bad) as d:
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


def test_shared_type3_batch_is_atomic():
    base=type3_pdf(form=True);regions=[]
    for occurrence,text in [(0,'CBA'),(1,'BAC')]:
        box=box_for(base,'ABC ABC',occurrence);row=inspect_styled(base,[],0,box)['runs'][0];regions.append({'page':0,'box':box,'changes':[{'id':row['id'],'text':text}]})
    out=replace_styled_regions(base,[],regions)
    with f.open(stream=out) as d:assert 'CBA' in d[0].get_text() and 'BAC' in d[0].get_text()
    bad=deepcopy(regions);bad[1]['changes'][0]['text']='Z'
    with pytest.raises(DocumentError):replace_styled_regions(base,[],bad)


@pytest.mark.parametrize('kind',['type3','cff2'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_new_fonts_find_replace_literal_batch(kind,rotation):
    from backend.find_replace import inspect,replace
    from tests.test_static_cff2 import source
    base=type3_pdf(rotation) if kind=='type3' else source(rotation)
    query={'text':'ABC','pages':[0],'case_sensitive':True,'whole_word':True};model=inspect(base,[],query)
    assert len(model['matches'])==2 and all(m['editable'] for m in model['matches'])
    out,_,count=replace(base,[],query,model['receipt'],[m['id'] for m in model['matches']],'CBA')
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert count==2 and 'CBA CBA' in b[0].get_text() and glyphs(a)==glyphs(b)
        assert a[0].rotation==b[0].rotation and a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')


def test_type3_unicode_uses_explicit_map_without_guessing_glyph_names():
    with f.open(stream=type3_pdf()) as d:
        font=next(v[0] for v in d[0].get_fonts() if v[2]=='Type3');uni=int(d.xref_get_key(font,'ToUnicode')[1].split()[0]);d.update_stream(uni,d.xref_stream(uni).replace(b'<0041>',b'<03a9>'));base=d.tobytes()
    box=box_for(base,'ΩBC ΩBC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBΩ ΩB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:assert 'CBΩ ΩB' in b[0].get_text() and glyphs(a)==glyphs(b)


def test_type3_ambiguous_unicode_with_different_glyphs_is_refused():
    with f.open(stream=type3_pdf()) as d:
        font=next(v[0] for v in d[0].get_fonts() if v[2]=='Type3');uni=int(d.xref_get_key(font,'ToUnicode')[1].split()[0]);d.update_stream(uni,d.xref_stream(uni).replace(b'<0042>',b'<0041>'));base=d.tobytes()
    row=inspect_styled(base,[],0,box_for(base,'AAC AAC'))['runs'][0];assert not row['editable']
