from copy import deepcopy
import re
import pymupdf as f
import pytest
from backend.engine import DocumentError,spans
from backend.pdf_content import placements
from backend.styled_text import inspect_styled,replace_styled,replace_styled_regions
from backend.paragraphs import replace_paragraph
from tests.test_cff_forms_mixed import cff_pdf,box_for,FONT
from tests.test_type3_fonts import type3_pdf,glyphs
from tests.test_static_cff2 import source as cff2_source


def source(kind='base',alpha=.5,form=False,rotation=0):
    if kind=='type3':base=type3_pdf()
    elif kind=='cff2':base=cff2_source()
    elif kind=='cff':base=cff_pdf()
    else:
        with f.open() as d:
            p=d.new_page()
            if kind=='ttf':p.insert_font(fontname='Original',fontfile=str(FONT))
            else:p.insert_font(fontname='helv')
            base=d.tobytes()
    with f.open(stream=base) as d:
        p=d[0];resource=next(v[4] for v in p.get_fonts() if v[2]=='Type3') if kind=='type3' else 'Original' if kind in ['cff','cff2','ttf'] else 'helv'
        font=next(v for v in p.get_fonts(full=True) if v[4]==resource)
        from backend.styled_text import OriginalFont
        face=OriginalFont(d,font);encoded=face.encode('ABC ABC',18)[0].hex();last=face.encode('CAB CAB',18)[0].hex();p.insert_font(fontname='hebo');res=int(d.xref_get_key(p.xref,'Resources')[1].split()[0]);d.xref_set_key(res,'ExtGState',f'<</Fade<</ca {alpha}/BM/Normal/SMask/None>> /Full<</ca 1>> /Fade2<</ca {alpha/2}>>>>')
        data=f'q /Fade gs BT /{resource} 18 Tf 1 0 0 1 80 700 Tm <{encoded}> Tj 0 0 .8 rg /hebo 14 Tf /Full gs 1 0 0 1 80 600 Tm (BAC BAC) Tj /{resource} 18 Tf 0 .5 0 rg /Fade2 gs 1 .1 .15 1 80 500 Tm <{last}> Tj ET Q'.encode()
        x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,data);p.set_contents(x);p.set_rotation(rotation);base=d.tobytes()
    if not form:return base
    with f.open(stream=base) as src,f.open() as d:
        src[0].set_rotation(0);p=d.new_page(width=800,height=1000);p.show_pdf_page(f.Rect(0,0,595,842),src,0);p.show_pdf_page(f.Rect(450,600,747.5,1021),src,0)
        for obj in p.get_xobjects():
            if obj[2]==0:d.xref_set_key(obj[0],'Group','<</S/Transparency/I true/K false/CS/DeviceRGB>>')
        d.new_page().show_pdf_page(f.Rect(0,0,595,842),src,0);d[0].set_rotation(rotation);return d.tobytes()


def row_for(base,text='ABC ABC',occ=0):
    box=box_for(base,text,occ);row=inspect_styled(base,[],0,box)['runs'][0];return box,row


@pytest.mark.parametrize('kind',['base','ttf','cff','type3','cff2'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('form',[False,True])
def test_intermediate_fonts_colors_alpha_positions_and_shared_group(kind,rotation,form):
    base=source(kind,.45,form,rotation);box,row=row_for(base);assert row['editable'],row['reason'];assert row['method']==('form-occurrence' if form else 'direct-content');assert row['alpha']<255
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'CBA AB'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and 'CBA AB' in b[0].get_text();assert glyphs(a)==glyphs(b)
        assert {v[3]:a.extract_font(v[0])[3] for v in a[0].get_fonts()}=={v[3]:b.extract_font(v[0])[3] for v in b[0].get_fonts()}
        a[0].set_rotation(0);b[0].set_rotation(0)
        for text in ['BAC BAC','CAB CAB']:
            aa=a[0].search_for(text);bb=b[0].search_for(text);assert aa==bb
            for rect in aa:assert a[0].get_pixmap(clip=rect).samples==b[0].get_pixmap(clip=rect).samples
        old=[s for s in spans(a[0]) if s['text']=='ABC ABC'][0];new=[s for s in spans(b[0]) if s['text']=='CBA AB'][0];assert new['alpha']==old['alpha'] and new['color']==old['color']
        if form:assert b[0].get_text().count('ABC ABC')==1 and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        else:
            left=a[0].read_contents();right=b[0].read_contents();obj=placements(left)['texts'][0];show=obj['shows'][0];assert left[:show.start]==right[:show.start]
            # Every non-show instruction, including gs/Tf/Tm/color, is unchanged.
            from backend.pdf_content import operations
            def states(data):return [(op,[t.value for t in args]) for op,args,_ in operations(data) if op not in ['Tj','TJ']]
            assert states(left)==states(right)


@pytest.mark.parametrize('text,new',[('ABC ABC','CBA AB'),('BAC BAC','CAB CA'),('CAB CAB','ABC AB')])
def test_each_absolute_segment_is_independently_editable(text,new):
    base=source();box,row=row_for(base,text);assert row['editable'],row['reason'];out=replace_styled(base,[],0,box,[{'id':row['id'],'text':new}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        before=next(s for s in spans(a[0]) if s['text']==text);after=next(s for s in spans(b[0]) if s['text']==new)
        assert (before['font'],before['color'],before['alpha'],before['origin'])==(after['font'],after['color'],after['alpha'],after['origin'])


def test_translucent_source_cannot_be_rewritten_as_opaque_paragraph():
    base=source();box,_=row_for(base)
    with pytest.raises(DocumentError,match='transparente'):replace_paragraph(base,[],0,box,'CBA',size=18)


@pytest.mark.parametrize('state',['<</ca 0>>','<</ca 1.1>>','<</ca .5/BM/Unknown>>','<</ca .5/SMask<</S/Alpha>>>>','<</ca .5/Font[/helv 18]>>','<</ca .5/AIS true>>'])
def test_unverified_graphics_states_stay_readonly(state):
    base=source()
    with f.open(stream=base) as d:
        res=int(d.xref_get_key(d[0].xref,'Resources')[1].split()[0]);d.xref_set_key(res,'ExtGState/Fade',state);bad=d.tobytes()
    with pytest.raises(DocumentError):row_for(bad)


@pytest.mark.parametrize('group',['<</S/Transparency/I /Bad>>','<</S/Transparency/I true/K true>>','<</S/Transparency/I true/CS/DeviceCMYK>>','<</S/Transparency/I true/CS[/ICCBased 99 0 R]>>','<</S/Transparency/I true/Extra true>>'])
def test_knockout_invalid_flags_or_complex_color_group_stays_readonly(group):
    base=source(form=True)
    with f.open(stream=base) as d:
        obj=next(x[0] for x in d[0].get_xobjects() if x[2]==0);d.xref_set_key(obj,'Group',group);bad=d.tobytes()
    try:_,row=row_for(bad)
    except DocumentError:return
    assert not row['editable']


def test_transparent_batch_three_segments_atomic_and_empty_edit():
    base=source(form=True);regions=[]
    for text,new in [('ABC ABC','CBA AB'),('BAC BAC','CAB CA'),('CAB CAB','')]:
        box,row=row_for(base,text);regions.append({'page':0,'box':box,'changes':[{'id':row['id'],'text':new}]})
    out=replace_styled_regions(base,[],regions)
    with f.open(stream=out) as d:assert 'CBA AB' in d[0].get_text() and 'CAB CA' in d[0].get_text() and d[0].get_text().count('CAB CAB')==1
    bad=deepcopy(regions);bad[-1]['changes'][0]['text']='C'*200
    with pytest.raises(DocumentError):replace_styled_regions(base,[],bad)


def test_state_change_without_absolute_reset_does_not_shift_dependent_text():
    data=b'BT /F 18 Tf 1 0 0 1 40 700 Tm (ABC) Tj /F 14 Tf (CAB) Tj ET'
    assert not placements(data)['texts']


def test_opaque_isolated_group_still_requires_original_composition():
    base=source(alpha=1,form=True);box,row=row_for(base);assert row['editable'] and row['alpha']==255 and row['original_only']
    with f.open(stream=base) as d:assert next(v for v in spans(d[0]) if v['text']=='ABC ABC')['original_only']
    with pytest.raises(DocumentError,match='transparencia'):replace_paragraph(base,[],0,box,'CBA',size=18)
