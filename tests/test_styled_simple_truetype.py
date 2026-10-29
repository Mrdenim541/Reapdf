"""Original single-byte TrueType programs, explicit encoding and rejection cases."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import pymupdf as f
import pytest
from backend.styled_text import inspect_styled,replace_styled,unicode_cmap,OriginalFont
from backend.find_replace import inspect,replace
from backend.engine import DocumentError
from backend.paragraphs import inspect_paragraph

FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'
BOX=[30,40,450,70]


def source(subset=False,rotation=0,crop=False):
    with f.open() as doc:
        page=doc.new_page();page.insert_font(fontname='OriginalSimple',fontfile=str(FONT),set_simple=True)
        page.insert_text((40,80),'Texto original útil 123 €',fontname='OriginalSimple',fontsize=17,color=(.1,.3,.5))
        # insert_text uses Latin-1 for simple fonts. Encode Euro explicitly as
        # WinAnsi 0x80 so the fixture actually contains the glyph being tested.
        for xref in page.get_contents():doc.update_stream(xref,doc.xref_stream(xref).replace(b'b7>',b'80>'))
        page.set_rotation(rotation)
        if crop:page.set_cropbox(f.Rect(10,10,585,832))
        doc.new_page().insert_text((40,80),'NEIGHBOR')
        if subset:doc.subset_fonts()
        return doc.tobytes()


def row(base,box=BOX):return inspect_styled(base,[],0,box)['runs'][0]


@pytest.mark.parametrize('subset',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_simple_font_edit_preserves_program_style_rotation_and_other_page(subset,rotation,tmp_path):
    base=source(subset,rotation);before=row(base);assert before['editable'],before['reason']
    out=replace_styled(base,[],0,BOX,[{'id':before['id'],'text':'Texto útil 12 €'}]);after=row(out)
    assert after['text']=='Texto útil 12 €' and after['editable']
    assert (before['font'],before['size'],before['color'])==(after['font'],after['size'],after['color'])
    assert after['origin']==pytest.approx(before['origin'],abs=.01)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        programs=lambda doc:{hashlib.sha256(doc.extract_font(i[0])[3]).hexdigest() for i in doc[0].get_fonts()}
        assert programs(a)==programs(b) and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].rotation==rotation and 'original' not in b[0].get_text()
    if shutil.which('pdftotext'):
        path=tmp_path/'simple.pdf';path.write_bytes(out)
        assert 'Texto útil 12 €' in subprocess.check_output(['pdftotext',str(path),'-']).decode()


def test_cropbox_and_find_replace_work_with_simple_truetype():
    base=source(crop=True);q={'text':'original','pages':[0],'case_sensitive':True,'whole_word':True};r=inspect(base,[],q)
    assert len(r['matches'])==1 and r['matches'][0]['editable']
    out,_,_=replace(base,[],q,r['receipt'],[r['matches'][0]['id']],'útil')
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].cropbox==a[0].cropbox and 'Texto útil útil 123 €' in b[0].get_text()


@pytest.mark.parametrize('kind',['no_encoding','differences','symbolic','no_flags','no_program','no_widths','bad_range','conflicting_unicode','wrong_code_bytes'])
def test_ambiguous_or_incomplete_simple_resources_remain_readonly(kind):
    with f.open(stream=source()) as doc:
        xref=doc[0].get_fonts()[0][0]
        if kind=='no_encoding':doc.xref_set_key(xref,'Encoding','null')
        if kind=='differences':doc.xref_set_key(xref,'Encoding','<</Type/Encoding/BaseEncoding/WinAnsiEncoding/Differences[65/B]>>')
        if kind=='symbolic':doc.xref_set_key(xref,'FontDescriptor/Flags','4')
        if kind=='no_flags':doc.xref_set_key(xref,'FontDescriptor/Flags','null')
        if kind=='no_program':doc.xref_set_key(xref,'FontDescriptor/FontFile2','null')
        if kind=='no_widths':doc.xref_set_key(xref,'Widths','null')
        if kind=='bad_range':doc.xref_set_key(xref,'LastChar','999')
        if kind in ['conflicting_unicode','wrong_code_bytes']:
            data=b'1 begincodespacerange <00><ff> endcodespacerange 1 beginbfchar <41><0042> endbfchar' if kind=='conflicting_unicode' else b'1 begincodespacerange <0000><ffff> endcodespacerange 1 beginbfchar <0041><0041> endbfchar'
            ref=doc.get_new_xref();doc.update_object(ref,'<<>>');doc.update_stream(ref,data);doc.xref_set_key(xref,'ToUnicode',f'{ref} 0 R')
        base=doc.tobytes()
    if kind=='bad_range':
        with f.open(stream=base) as doc:
            with pytest.raises(DocumentError,match='anchuras'):OriginalFont(doc,doc[0].get_fonts(full=True)[0])
        with pytest.raises(DocumentError):row(base)
        return
    found=row(base);assert not found['editable'] and found['reason']
    with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':found['id'],'text':'Texto'}])


def test_simple_unicode_map_agreeing_with_winansi_is_accepted():
    with f.open(stream=source()) as doc:
        ref=doc.get_new_xref();doc.update_object(ref,'<<>>')
        doc.update_stream(ref,b'1 begincodespacerange <00><ff> endcodespacerange 2 beginbfrange <20><7e><0020> <a0><ff><00a0> endbfrange 1 beginbfchar <80><20ac> endbfchar')
        doc.xref_set_key(doc[0].get_fonts()[0][0],'ToUnicode',f'{ref} 0 R');base=doc.tobytes()
    assert row(base)['editable']
    assert unicode_cmap(b'1 begincodespacerange <00><ff> endcodespacerange 1 beginbfchar <80><20ac> endbfchar',1)=={128:'€'}


def test_non_winansi_character_is_rejected_before_source_changes():
    base=source();found=row(base)
    with pytest.raises(DocumentError,match='carácter'):
        replace_styled(base,[],0,BOX,[{'id':found['id'],'text':'α'}])
    assert row(base)['text']==found['text']


@pytest.mark.parametrize('filename,family',[('DejaVuSans.ttf','sans'),('DejaVuSansMono.ttf','mono'),('DejaVuSerif.ttf','serif')])
def test_paragraph_fallback_uses_known_family_despite_simple_font_serif_flag(filename,family):
    with f.open() as doc:
        page=doc.new_page();page.insert_font(fontname='Original',fontfile=str(FONT.with_name(filename)),set_simple=True)
        page.insert_text((40,80),'Texto original',fontname='Original');base=doc.tobytes()
    assert inspect_paragraph(base,[],0,BOX)['format']['family']==family
