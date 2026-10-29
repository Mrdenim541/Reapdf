import math
from pathlib import Path
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.styled_text import inspect_styled,replace_styled
from backend.pdf_content import placements
FONT=Path(__file__).resolve().parents[1]/'resources/fonts/DejaVuSans.ttf'


def source(scale=80,kind='base',grouped=True,rotation=0):
    with f.open() as d:
        p=d.new_page();resource='helv'
        if kind!='base':
            resource='Original';p.insert_font(fontname=resource,fontfile=str(FONT),set_simple=kind=='simple')
        p.insert_text((40,100),'AVATAR TEST',fontname=resource,fontsize=18)
        x=p.get_contents()[0];old=d.xref_stream(x)
        token=placements(old)['texts'][0]['shows'][0];raw=token.value;step=len(raw)//len('AVATAR TEST')
        a,b,c=[raw[i*step:j*step].hex().encode() for i,j in [(0,2),(2,4),(4,11)]]
        expression=b'[<'+a+b'> 25 <'+b+b'>] TJ <'+c+b'> Tj' if grouped else b'[<'+a+b'> 25 <'+b+c+b'>] TJ'
        # Replace operand plus its operator as a unit.
        pos=old.index(b'TJ',token.end);new=old[:token.start]+expression+old[pos+2:]
        new=new.replace(b'BT',f'BT {scale} Tz 0.25 Tc 0.5 Tw'.encode());d.update_stream(x,new)
        p.insert_text((40,300),'UNCHANGED');p.set_rotation(rotation);return d.tobytes()


def region(base):
    with f.open(stream=base) as d:
        span=d[0].get_text('dict')['blocks'][0]['lines'][0]['spans'][0];r=f.Rect(span['bbox'])+(-2,-2,2,2)
        return [r.x0,r.y0,r.width,r.height]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind',['base','simple','identity'])
@pytest.mark.parametrize('scale',[40,80,125,200])
def test_grouped_scaled_text_keeps_font_scale_positions_and_other_content(scale,kind,rotation):
    base=source(scale,kind,True,rotation);box=region(base);row=inspect_styled(base,[],0,box)['runs'][0]
    assert row['editable'],row['reason'];assert row['size']==pytest.approx(18,abs=.001)
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'AVATAR TES'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and 'AVATAR TES' in b[0].get_text()
        assert a[0].search_for('UNCHANGED')==b[0].search_for('UNCHANGED')
        sa=a[0].get_text('rawdict')['blocks'][0]['lines'][0]['spans'][0];sb=b[0].get_text('rawdict')['blocks'][0]['lines'][0]['spans'][0]
        for old,new in zip(sa['chars'],sb['chars']):assert new['origin']==pytest.approx(old['origin'],abs=.02)
        assert abs(sa['size']-18*math.sqrt(scale/100))<.02 and abs(sb['size']-sa['size'])<.02
        old=a[0].read_contents();new=b[0].read_contents();left=placements(old)['texts'][0]['shows'][0];right=placements(new)['texts'][0]['shows'][0]
        assert old[:left.start]==new[:right.start] and old[left.end:]==new[placements(new)['texts'][0]['show_ends'][-1]:]
        if kind!='base':
            old_font=next(i for i in a[0].get_fonts() if i[4]=='Original');new_font=next(i for i in b[0].get_fonts() if i[4]=='Original')
            assert a.extract_font(old_font[0])[3]==b.extract_font(new_font[0])[3]


@pytest.mark.parametrize('scale',[40,80,125,200])
def test_single_show_scaling_roundtrip_and_overflow_atomic(scale):
    base=source(scale,grouped=False);box=region(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    with pytest.raises(DocumentError):replace_styled(base,[],0,box,[{'id':row['id'],'text':'A'*100}])
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'AVATAR TES'}]);assert inspect_styled(out,[],0,region(out))['runs'][0]['editable']


@pytest.mark.parametrize('mutation',[b'1 0 0 rg',b'1 Tc',b'/helv 18 Tf',b'10 0 Td',b'/P BMC',b'q'])
def test_intervening_state_or_mark_changes_are_not_absorbed(mutation):
    base=source(100)
    with f.open(stream=base) as d:
        p=d[0];x=p.get_contents()[0];data=d.xref_stream(x).replace(b'TJ <',b'TJ '+mutation+b' <')
        if mutation==b'/P BMC':data=data.replace(b' ET',b' EMC ET')
        if mutation==b'q':data=data.replace(b' ET',b' Q ET')
        d.update_stream(x,data);bad=d.tobytes()
    try:rows=inspect_styled(bad,[],0,region(bad))['runs']
    except DocumentError:return
    assert not rows[0]['editable']


@pytest.mark.parametrize('scale',[10,400])
def test_supported_scale_boundaries(scale):
    base=source(scale,grouped=True);box=region(base);row=inspect_styled(base,[],0,box)['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,box,[{'id':row['id'],'text':'AVATAR TES'}]);assert inspect_styled(out,[],0,region(out))['runs'][0]['editable']


@pytest.mark.parametrize('scale',[5,401])
def test_unsupported_scale_stays_readonly(scale):
    base=source(scale,grouped=True)
    assert not inspect_styled(base,[],0,region(base))['runs'][0]['editable']
