from io import BytesIO
from copy import deepcopy
from pathlib import Path
import hashlib,re
import pymupdf as f
import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from fontTools.cffLib import FDArrayIndex,FontDict,FDSelect
from backend.engine import DocumentError
from backend.styled_text import inspect_styled,replace_styled,replace_styled_regions
from backend.original_reflow import inspect as inspect_block,reflow
from backend.cff_fonts import CFFFace

CHARS=' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'


def cff_program():
    order=['.notdef']+['space' if c==' ' else c for c in CHARS];builder=FontBuilder(1000,isTTF=False);builder.setupGlyphOrder(order);builder.setupCharacterMap({ord(c):name for c,name in zip(CHARS,order[1:])});strings={}
    for name in order:
        pen=T2CharStringPen(600,None)
        if name not in ['space','.notdef']:
            pen.moveTo((40,0));pen.lineTo((500,0));pen.lineTo((500,700));pen.lineTo((40,700));pen.closePath()
        strings[name]=pen.getCharString()
    builder.setupCFF('ReapdfCFF',{'FullName':'Reapdf CFF','FamilyName':'Reapdf CFF','Weight':'Regular'},strings,{})
    builder.setupHorizontalMetrics({name:(600,40) for name in order});builder.setupHorizontalHeader(ascent=800,descent=-200);builder.setupNameTable({'familyName':'Reapdf CFF','styleName':'Regular','uniqueFontIdentifier':'Reapdf CFF','fullName':'Reapdf CFF','psName':'ReapdfCFF'});builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);builder.setupPost();stream=BytesIO();builder.save(stream);return stream.getvalue()


def cff_pdf(kind='open',rotation=0,marked=False):
    program=cff_program();simple=kind in ['simple','raw-simple']
    with f.open() as d:
        p=d.new_page();font=p.insert_font(fontname='Original',fontbuffer=program,set_simple=simple);p.insert_text((40,100),'HELLO TEXT',fontname='Original',fontsize=18);p.insert_text((40,300),'UNCHANGED')
        if kind=='raw-simple':
            rawfont=TTFont(BytesIO(program));cff=rawfont['CFF '].cff;stream=BytesIO();cff.compile(stream,rawfont);ref=int(d.xref_get_key(font,'FontDescriptor/FontFile3')[1].split()[0]);d.update_stream(ref,stream.getvalue());d.xref_set_key(ref,'Subtype','/Type1C')
        if kind=='cid':
            rawfont=TTFont(BytesIO(program));cff=rawfont['CFF '].cff;top=cff[cff.fontNames[0]];old=list(top.charset);renamed=['.notdef']+[f'cid{i*2:05d}' for i in range(1,len(old))]
            top.ROS=('Adobe','Identity',0);top.CIDCount=len(old)*2;fd=FontDict();fd.Private=top.Private;top.FDArray=FDArrayIndex();top.FDArray.append(fd);top.FDSelect=FDSelect(format=3);top.FDSelect.gidArray=[0]*len(old);del top.Private
            top.CharStrings.charStrings={new:top.CharStrings.charStrings[name] for name,new in zip(old,renamed)};top.charset=renamed;rawfont.setGlyphOrder(renamed);stream=BytesIO();cff.compile(stream,rawfont)
            desc=int(d.xref_get_key(font,'DescendantFonts')[1].strip('[]').split()[0]);ref=int(d.xref_get_key(desc,'FontDescriptor/FontFile3')[1].split()[0]);d.update_stream(ref,stream.getvalue());d.xref_set_key(ref,'Subtype','/CIDFontType0C');uni=int(d.xref_get_key(font,'ToUnicode')[1].split()[0]);d.update_stream(uni,('1 begincodespacerange <0000><ffff> endcodespacerange '+str(len(CHARS))+' beginbfchar '+' '.join(f'<{(i+1)*2:04x}><{ord(c):04x}>' for i,c in enumerate(CHARS))+' endbfchar').encode());d.xref_set_key(desc,'W','[2 72 600]')
            x=p.get_contents()[0];data=d.xref_stream(x);data=re.sub(rb'<([0-9A-Fa-f]+)>',lambda m:b'<'+b''.join(f'{int(m[1][i:i+4],16)*2:04x}'.encode() for i in range(0,len(m[1]),4))+b'>',data);d.update_stream(x,data)
        if marked:
            x=p.get_contents()[0];d.update_stream(x,b'q 0 0 595 842 re W n /P <</MCID 2>> BDC '+d.xref_stream(x)+b' EMC Q')
        p.set_rotation(rotation);return d.tobytes()


def box_for(base,text='HELLO TEXT',occurrence=0):
    with f.open(stream=base) as d:
        d[0].set_rotation(0);span=[s for b in d[0].get_text('dict',sort=True)['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']==text][occurrence];r=f.Rect(span['bbox'])+(-2,-2,2,2)
    return [r.x0,r.y0,r.width,r.height]


@pytest.mark.parametrize('kind',['open','simple','raw-simple','cid'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('marked',[False,True])
def test_cff_original_program_kept(kind,rotation,marked):
    base=cff_pdf(kind,rotation,marked);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert 'HELLO TEX' in b[0].get_text() and a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED') and b[0].rotation==rotation
        left=next(i for i in a[0].get_fonts() if i[4]=='Original');right=next(i for i in b[0].get_fonts() if i[4]=='Original');assert a.extract_font(left[0])[3]==b.extract_font(right[0])[3]
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO Ω'}])


def test_cff_parser_limits_and_subtype_mismatch():
    program=cff_program();face=CFFFace(program,'OpenType');face.remaining=0
    with pytest.raises(DocumentError,match='presupuesto'):face.has_outline(2)
    with pytest.raises(DocumentError):CFFFace(program,'Type1C')
    with pytest.raises(DocumentError):CFFFace(b'not-font','OpenType')
    rawfont=TTFont(BytesIO(program));stream=BytesIO();rawfont['CFF '].cff.compile(stream,rawfont)
    with pytest.raises(DocumentError):CFFFace(stream.getvalue(),'CIDFontType0C')


def form_pdf(rotation=0,scale=.7,cff=False):
    source=cff_pdf() if cff else None
    with f.open() as text:
        text.new_page(width=300,height=150).insert_text((30,70),'HELLO TEXT',fontsize=18)
        if cff:text.close();text=f.open(stream=source)
        with f.open() as d:
            p=d.new_page();r=f.Rect(25,35,25+300*scale,35+150*scale);p.show_pdf_page(r,text,0,keep_proportion=False)
            # Reuses the same imported fullpage object in a second occurrence.
            p.show_pdf_page(r+(0,300,0,300),text,0,keep_proportion=False);p.insert_text((40,720),'ROOT TEXT',fontname='cour');p.set_rotation(rotation)
            other=d.new_page();other.show_pdf_page(other.rect,text,0)
            return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('scale',[.7,1.,1.2])
def test_shared_form_only_selected_occurrence_changes(rotation,scale):
    base=form_pdf(rotation,scale);box=box_for(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason'];assert row['method']=='form-occurrence'
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].get_text().splitlines()[:2]==['HELLO TEX','HELLO TEXT'];assert b[0].rotation==rotation
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].search_for('ROOT TEXT')==b[0].search_for('ROOT TEXT')
        # Every original stream object still exists byte-for-byte or is unused,
        # never mutated globally when the shared leaf is detached.
        for xref in [i[0] for i in a[0].get_xobjects()]:
            original=a.xref_stream(xref);assert any(b.xref_stream(i[0])==original for i in b[1].get_xobjects())


def test_form_batch_two_occurrences_and_root_is_atomic():
    base=form_pdf();regions=[]
    for value,occ,new in [('HELLO TEXT',0,'HELLO TEX'),('HELLO TEXT',1,'HELLO TE'),('ROOT TEXT',0,'ROOT TEX')]:
        box=box_for(base,value,occ);row=inspect_styled(base,[],0,box)['runs'][0];regions.append({'page':0,'box':box,'changes':[{'id':row['id'],'text':new}]})
    out=replace_styled_regions(base,[],regions)
    with f.open(stream=out) as d:assert d[0].get_text().splitlines()==['HELLO TEX','HELLO TE','ROOT TEX']
    bad=deepcopy(regions);bad[-1]['changes'][0]['text']='ROOT Ω'
    with pytest.raises(DocumentError):replace_styled_regions(base,[],bad)


@pytest.mark.parametrize('kind',['group','oc','structure','matrix','cycle'])
def test_incompatible_forms_stay_readonly(kind):
    base=form_pdf()
    with f.open(stream=base) as d:
        wrappers=[i[0] for i in d[0].get_xobjects() if i[2]==0];target=wrappers[0]
        if kind=='group':d.xref_set_key(target,'Group','<</S/Transparency>>')
        if kind=='oc':d.xref_set_key(target,'OC','<</Type/OCG/Name(Hidden)>>')
        if kind=='structure':d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','<</Type/StructTreeRoot/K[]>>')
        if kind=='matrix':d.xref_set_key(target,'Matrix','[1 .1 0 1 0 0]')
        if kind=='cycle':d.xref_set_key(target,'Resources/XObject/fullpage',f'{target} 0 R')
        bad=d.tobytes()
    try:rows=inspect_styled(bad,[],0,box_for(base))['runs']
    except DocumentError:return
    assert not rows or not rows[0]['editable']


def mixed_pdf(rotation=0):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'HELLO ',fontname='hebo',fontsize=18,color=(.8,0,0));p.insert_text((107,80),'TEXT',fontname='heit',fontsize=14,color=(0,0,.8));p.insert_text((40,400),'UNCHANGED');p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_mixed_original_reflow_keeps_fonts_sizes_colors(rotation):
    base=mixed_pdf(rotation)
    with f.open(stream=base) as d:s=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
    model=inspect_block(base,[],0,list(s['origin']),s['text']);assert model['original_available'] and model['mixed']
    runs=[{'id':r['id'],'text':r['text']*3} for r in model['runs']];text=''.join(r['text'] for r in runs);box=[*model['box'][:3],150]
    out,report=reflow(base,[],0,box,text,source_box=model['box'],runs=runs);assert report['lines']>=2
    with f.open(stream=out) as d:
        spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']!='UNCHANGED'];styles={(s['font'],round(s['size']),s['color']) for s in spans}
        assert styles=={('Helvetica-Bold',18,0xcc0000),('Helvetica-Oblique',14,0x0000cc)} and d[0].rotation==rotation
        assert 'UNCHANGED' in d[0].get_text()
    bad=deepcopy(runs);bad[0]['id']='fake'
    with pytest.raises(DocumentError):reflow(base,[],0,box,text,source_box=model['box'],runs=bad)


def test_cff_inside_shared_form_preserves_other_page():
    with f.open(stream=cff_pdf()) as source,f.open() as d:
        p=d.new_page();p.show_pdf_page(p.rect,source,0);p=d.new_page();p.show_pdf_page(p.rect,source,0);base=d.tobytes()
    row=inspect_styled(base,[],0,box_for(base))['runs'][0];assert row['editable'];out=replace_styled(base,[],0,box_for(base),[{'id':row['id'],'text':'HELLO TEX'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:assert b[0].get_text().startswith('HELLO TEX') and b[1].get_pixmap().samples==a[1].get_pixmap().samples


def test_mixed_reflow_api_and_bad_font_program_are_atomic(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'));base=mixed_pdf()
    with f.open(stream=base) as d:s=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0]
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Mixto.pdf',base)}).json();route=f"/api/documents/{doc['id']}"
        model=c.post(route+'/inline-block',json={'page':0,'origin':list(s['origin']),'text':s['text']}).json();assert model['mixed']
        runs=[{'id':r['id'],'text':r['text']*2} for r in model['runs']];payload={'page':0,'box':[*model['box'][:3],150],'source_box':model['box'],'text':''.join(r['text'] for r in runs),'runs':runs}
        assert c.post(route+'/reflow-original',json={**payload,'preview':True}).json()['mode']=='mixed-original'
        response=c.post(route+'/reflow-original',json=payload);assert response.status_code==200
        payload['runs'][0]['text']='MISMATCH';assert c.post(route+'/reflow-original',json=payload).status_code==422
        assert c.post(route+'/export',json={'operations':[]}).content==base
    base=cff_pdf('simple')
    with f.open(stream=base) as d:
        font=d[0].get_fonts()[0][0];xref=int(d.xref_get_key(font,'FontDescriptor/FontFile3')[1].split()[0]);d.update_stream(xref,b'broken font program');bad=d.tobytes()
    try:rows=inspect_styled(bad,[],0,[35,70,180,45])['runs']
    except DocumentError:return
    assert not rows or not rows[0]['editable']


def test_adjacent_styles_and_narrow_span_can_be_selected_without_neighbor():
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'I',fontsize=8);p.insert_text((43,80),'NEXT',fontsize=8,fontname='hebo');base=d.tobytes();span=p.get_text('dict')['blocks'][0]['lines'][0]['spans'][0];rect=f.Rect(span['bbox']);box=[rect.x0,rect.y0,rect.width,rect.height]
    assert rect.width<10
    rows=inspect_styled(base,[],0,box)['runs'];assert len(rows)==1 and rows[0]['editable'];out=replace_styled(base,[],0,box,[{'id':rows[0]['id'],'text':''}])
    with f.open(stream=out) as d:assert d[0].get_text().strip()=='NEXT'


def test_named_alternative_text_is_not_left_stale():
    base=cff_pdf()
    with f.open(stream=base) as d:
        p=d[0];resources=int(d.xref_get_key(p.xref,'Resources')[1].split()[0]);d.xref_set_key(resources,'Properties','<</Pr0<</ActualText(HELLO TEXT)>>>>');xref=p.get_contents()[0];d.update_stream(xref,b'/Span /Pr0 BDC '+d.xref_stream(xref)+b' EMC');bad=d.tobytes()
    with pytest.raises(DocumentError,match='propiedades'):inspect_styled(bad,[],0,[35,70,180,45])


def test_form_write_budget_rejects_before_mutating_source_copy():
    from backend.styled_text import styled_model,prepare_changes,write_changes
    base=form_pdf();box=box_for(base)
    with f.open(stream=base) as d:
        page=d[0];rect,rows=styled_model(d,0,box);prepared=prepare_changes(d,0,rect,rows,[{'id':rows[0]['id'],'text':'HELLO TEX'}]);original=page.read_contents();d._reapdf_form_write_bytes=64*1024*1024
        with pytest.raises(DocumentError,match='64 MB'):write_changes(d,0,prepared)
        assert page.read_contents()==original and page.get_text().splitlines()[:2]==['HELLO TEXT','HELLO TEXT']
