from io import BytesIO
from pathlib import Path
import struct
import pymupdf as f
import pytest
from fontTools.ttLib import TTFont,newTable
from fontTools.subset import Subsetter,Options
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from backend.pdf_content import tokens,placements,patch
from backend.styled_text import inspect_styled,replace_styled
from backend.image_editing import image_model,edit_image
from backend.engine import DocumentError

FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'
BOX=[30,50,200,60]


def custom_source(rotation=0):
    chars='ABRNDE 0123456789'
    face=TTFont(FONT);sub=Subsetter(options=Options());sub.populate(text=chars);sub.subset(face)
    old=face.getBestCmap();table=newTable('cmap');table.tableVersion=0
    cmap=CmapSubtable.newSubtable(0);cmap.platformID=1;cmap.platEncID=0;cmap.language=0;cmap.cmap={i+1:old[ord(c)] for i,c in enumerate(chars)};table.tables=[cmap];face['cmap']=table
    buffer=BytesIO();face.save(buffer);program=buffer.getvalue()
    widths=[0]+[face['hmtx'].metrics[old[ord(c)]][0]*1000/face['head'].unitsPerEm for c in chars]
    with f.open() as doc:
        page=doc.new_page();xref=page.insert_font(fontname='Original',fontbuffer=program,set_simple=True)
        doc.xref_set_key(xref,'Encoding','null');descriptor=int(doc.xref_get_key(xref,'FontDescriptor')[1].split()[0]);doc.xref_set_key(descriptor,'Flags','4');doc.xref_set_key(xref,'FirstChar','0');doc.xref_set_key(xref,'LastChar',str(len(chars)))
        doc.xref_set_key(xref,'Widths','['+' '.join(str(v) for v in widths)+']')
        uni=doc.get_new_xref();doc.update_object(uni,'<<>>');doc.update_stream(uni,('1 begincodespacerange <00><ff> endcodespacerange '+str(len(chars))+' beginbfchar '+' '.join(f'<{i+1:02x}><{ord(c):04x}>' for i,c in enumerate(chars))+' endbfchar').encode());doc.xref_set_key(xref,'ToUnicode',f'{uni} 0 R')
        encoded=bytes(chars.index(c)+1 for c in 'BARANDA').hex()
        content=doc.get_new_xref();doc.update_object(content,'<<>>');doc.update_stream(content,('q 0 0 595 842 re W n /P <</MCID 7>> BDC BT 40 762 Td /Original 18 Tf <'+encoded+'> Tj ET EMC Q').encode());page.set_contents(content);page.set_rotation(rotation)
        doc.new_page().insert_text((40,80),'UNCHANGED')
        return doc.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_native_original_font_preserves_marked_bytes_program_and_other_page(rotation):
    base=custom_source(rotation);row=inspect_styled(base,[],0,BOX)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'BARRA'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().strip()=='BARRA' and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert b[0].rotation==rotation
        old=a[0].read_contents();new=b[0].read_contents();s=placements(old)['texts'][0]['shows'][0];t=placements(new)['texts'][0]['shows'][0]
        assert old[:s.start]==new[:t.start] and old[s.end:]==new[t.end:]
        assert a.extract_font(a[0].get_fonts()[0][0])[3]==b.extract_font(b[0].get_fonts()[0][0])[3]


@pytest.mark.parametrize('kind',['missing','wide','actual_text','blend'])
def test_unsupported_native_edits_leave_original_unchanged(kind):
    base=custom_source()
    if kind not in ['missing','wide']:
        with f.open(stream=base) as doc:
            page=doc[0];data=page.read_contents()
            if kind=='actual_text':data=data.replace(b'/MCID 7',b'/MCID 7 /ActualText (BARANDA)')
            elif kind=='blend':
                resources=int(doc.xref_get_key(page.xref,'Resources')[1].split()[0]);doc.xref_set_key(resources,'ExtGState','<</Alpha<</ca 0.5/BM/UnknownBlend>>>>');data=data.replace(b'BT',b'/Alpha gs BT')
            elif kind=='tracking':data=data.replace(b'BT',b'BT 2 Tc')
            else:data=data.replace(b'Tj ET',b'Tj <01> Tj ET')
            doc.update_stream(page.get_contents()[0],data);base=doc.tobytes()
    try:row=inspect_styled(base,[],0,BOX)['runs'][0]
    except DocumentError:
        assert kind in ['actual_text','tracking','two_shows','blend'];return
    if kind in ['missing','wide']:
        with pytest.raises(DocumentError):replace_styled(base,[],0,BOX,[{'id':row['id'],'text':'Z' if kind=='missing' else 'B'*100}])
    else:assert not row['editable']


def picture():
    p=f.Pixmap(f.csRGB,f.IRect(0,0,16,16));p.clear_with(80);return p.tobytes('png')


def image_source(rotation=0):
    with f.open() as doc:
        page=doc.new_page();page.insert_image(f.Rect(40,100,140,200),stream=picture());page.insert_text((40,80),'UNCHANGED')
        data=page.read_contents();xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'q 0 0 595 842 re W n\n'+data+b'\nQ');page.set_contents(xref);page.set_rotation(rotation)
        doc.new_page().insert_text((40,80),'OTHER PAGE');return doc.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('action',['move','delete','replace'])
def test_direct_clipped_image_preserves_text_other_page_and_clipping(rotation,action):
    base=image_source(rotation)
    with f.open(stream=base) as d:row=image_model(d,0)['images'][0]
    assert row['editable'] and row['direct_content']
    rect=row['rect'];box=[rect[0]+2,rect[1]+2,rect[2]-rect[0],rect[3]-rect[1]]
    import base64
    out=edit_image(base,[],0,row['xref'],action,box,data=base64.b64encode(picture()).decode())
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text()==a[0].get_text() and b[1].get_pixmap().samples==a[1].get_pixmap().samples
        assert b[0].rotation==rotation and b'W n' in b[0].read_contents()
        rows=image_model(b,0)['images']
        assert len(rows)==(0 if action=='delete' else 1)
        if action=='move':assert rows[0]['rect']==pytest.approx([box[0],box[1],box[0]+box[2],box[1]+box[3]],abs=.02) and rows[0]['digest']==row['digest']


def test_lexer_does_not_interpret_operator_bytes_inside_strings_comments_or_names():
    data=b'% BI Tj\n/BT (a\\(b\\)\\101\\\nc) Tj <4254> Tj [ (Do) 2 ] TJ'
    assert [t.value for t in tokens(data) if t.kind=='string']==[b'a(b)Ac',b'BT']
    assert patch(b'abcdef',[(1,3,b'X'),(4,5,b'Y')])==b'aXdYf'
    with pytest.raises(DocumentError):placements(b'BI /W 1 ID abc EI')
    with pytest.raises(DocumentError):patch(b'abcdef',[(1,4,b'x'),(2,5,b'y')])
