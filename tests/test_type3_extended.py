"""Actual Type3 images and font matrices, exercised through on-page editing."""
import zlib
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.styled_text import OriginalFont,inspect_styled,replace_styled
from tests.test_type3_fonts import type3_pdf,mutate,glyphs
from tests.test_cff_forms_mixed import box_for

MATRICES=['[.002 0 0 .001 0 0]','[.001 0 0 .002 0 0]','[.002 0 0 .002 0 0]','[.001 0 0 .001 .1 .1]','[.0005 0 0 .001 -.05 .05]']


def matrix_source(matrix,rotation=0,form=False):
    with f.open(stream=type3_pdf(rotation=rotation,form=form)) as d:
        for x in range(1,d.xref_length()):
            if d.xref_get_key(x,'Subtype')[1]=='/Type3':d.xref_set_key(x,'FontMatrix',matrix)
        return d.tobytes()


@pytest.mark.parametrize('matrix',MATRICES)
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_nonstandard_matrix_edit_and_reopen_preserves_programs(matrix,rotation,form):
    base=matrix_source(matrix,rotation,form);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and b[0].rotation==rotation and glyphs(a)==glyphs(b)
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples and b[0].get_text().count('ABC ABC')==1
        else:
            # Independent expected PDF: keep the original stream/resources,
            # change only its literal show operand and compare rendered pixels.
            for x in a[0].get_contents():a.update_stream(x,a.xref_stream(x).replace(b'(ABC ABC)',b'(CBA AB)'))
            assert a[0].get_pixmap(matrix=f.Matrix(2,2)).samples==b[0].get_pixmap(matrix=f.Matrix(2,2)).samples


def image_source(mask=False,form=False,rotation=0):
    with f.open(stream=type3_pdf(form=form,rotation=rotation)) as d:
        for x in range(1,d.xref_length()):
            if d.xref_get_key(x,'Subtype')[1]!='/Type3':continue
            resources=[]
            for index,name in enumerate(['A','B','C']):
                image=d.get_new_xref();d.update_object(image,'<< /Type/XObject /Subtype/Image /Width 2 /Height 2 /BitsPerComponent '+('1 /ImageMask true' if mask else '8 /ColorSpace/DeviceRGB')+' /Filter/FlateDecode >>')
                masks=[b'\x80\x40',b'\xc0\x80',b'\x40\xc0'];pixels=bytes([255,0,0,0,255,0,0,0,255,255,255,0]);raw=masks[index] if mask else pixels[index*3:]+pixels[:index*3]
                d.update_stream(image,zlib.compress(raw),compress=False);d.xref_set_key(image,'Filter','/FlateDecode');resources.append(f'/Picture{name} {image} 0 R')
                proc=int(d.xref_get_key(x,'CharProcs/'+name)[1].split()[0]);header=b'600 0 0 -200 600 800 d1 ' if mask else b'600 0 d0 '
                d.update_stream(proc,header+b'q 500 0 0 700 50 0 cm /Picture'+name.encode()+b' Do Q')
            d.xref_set_key(x,'Resources','<</XObject<<'+' '.join(resources)+'>>>>')
        return d.tobytes()


@pytest.mark.parametrize('mask',[False,True])
@pytest.mark.parametrize('form',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_image_glyph_edit_without_rasterising_page(mask,form,rotation):
    base=image_source(mask,form,rotation);box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'CBA AB' in b[0].get_text() and glyphs(a)==glyphs(b)
        image_bytes=lambda d:{d.xref_stream_raw(x) for x in range(1,d.xref_length()) if d.xref_get_key(x,'Subtype')[1]=='/Image'}
        assert image_bytes(a)==image_bytes(b)
        if form:assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        else:
            for x in a[0].get_contents():a.update_stream(x,a.xref_stream(x).replace(b'(ABC ABC)',b'(CBA AB)'))
            assert a[0].get_pixmap(matrix=f.Matrix(2,2)).samples==b[0].get_pixmap(matrix=f.Matrix(2,2)).samples


@pytest.mark.parametrize('matrix',['[0 0 0 .001 0 0]','[-.001 0 0 .001 0 0]','[.001 0 .1 .001 0 0]','[.001 0 0 .001 11 0]'])
def test_unverified_matrices_stay_protected(matrix):
    base=matrix_source(matrix)
    with f.open(stream=base) as d:
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


@pytest.mark.parametrize('key,value',[
 ('SMask','1 0 R'),('Mask','[0 0 0 0 0 0]'),('Filter','/DCTDecode'),('Filter','[/FlateDecode]'),
 ('Width','0'),('Width','9000'),('Width','3'),('Height','1000'),('ColorSpace','/DeviceN'),
 ('DecodeParms','<</Predictor 12>>'),('Decode','[0 1]'),('Decode','[0 1 0 1 0 2]'),('ImageMask','7')])
def test_unverified_image_resources_stay_protected(key,value):
    with f.open(stream=image_source()) as d:
        image=next(x for x in range(1,d.xref_length()) if d.xref_get_key(x,'Subtype')[1]=='/Image');d.xref_set_key(image,key,value)
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


def test_colour_image_in_uncoloured_glyph_is_rejected():
    with f.open(stream=image_source()) as d:
        for x in range(1,d.xref_length()):
            if d.xref_is_stream(x) and d.xref_stream(x).startswith(b'600 0 d0 '):d.update_stream(x,d.xref_stream(x).replace(b'600 0 d0 ',b'600 0 0 -200 600 800 d1 '))
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


def test_inflated_image_is_rejected_before_large_decode():
    with f.open(stream=image_source()) as d:
        image=next(x for x in range(1,d.xref_length()) if d.xref_get_key(x,'Subtype')[1]=='/Image');d.update_stream(image,zlib.compress(b'X'*2_000_000),compress=False);d.xref_set_key(image,'Filter','/FlateDecode')
        with pytest.raises(DocumentError):OriginalFont(d,next(v for v in d[0].get_fonts(full=True) if v[2]=='Type3'))


@pytest.mark.parametrize('mask',[False,True])
def test_image_and_nonstandard_matrix_work_together(mask):
    base=mutate(image_source(mask),'FontMatrix','[.002 0 0 .001 .05 -.05]');box=box_for(base,'ABC ABC');row=inspect_styled(base,[],0,box)['runs'][0];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for x in a[0].get_contents():a.update_stream(x,a.xref_stream(x).replace(b'(ABC ABC)',b'(CBA AB)'))
        assert a[0].get_pixmap(matrix=f.Matrix(2,2)).samples==b[0].get_pixmap(matrix=f.Matrix(2,2)).samples
