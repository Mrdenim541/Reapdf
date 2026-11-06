import pytest
import pymupdf as f
from backend.forms import form_model
from backend.form_actions import actions
from backend.form_structure import field_structure
from tests.test_form_standard_actions import source,fill


def streamed(base,encoding='ascii',compressed=False):
    with f.open(stream=base) as d:
        w=next(d[0].widgets())
        for event in ['F','K']:
            code=d.xref_get_key(w.xref,'AA/'+event+'/JS')[1]+' '*300
            raw=(b'\xfe\xff'+code.encode('utf-16-be') if encoding=='be' else b'\xff\xfe'+code.encode('utf-16-le') if encoding=='le' else b'\xef\xbb\xbf'+code.encode('utf-8') if encoding=='utf8' else code.encode('ascii'))
            x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,raw,compress=compressed);d.xref_set_key(w.xref,'AA/'+event+'/JS',f'{x} 0 R')
            assert d.xref_is_stream(x)
            if compressed:assert d.xref_get_key(x,'Filter')==('name','/FlateDecode')
        return d.tobytes()


@pytest.mark.parametrize('encoding',['ascii','be','le','utf8'])
@pytest.mark.parametrize('compressed',[False,True])
@pytest.mark.parametrize('fmt,key,entered,expected',[
 ('AFNumber_Format(2,1,0,0,"",false);','AFNumber_Keystroke(2,1);','12.5','12.50'),
 ('AFDate_FormatEx("dd/mm/yyyy HH:MM:ss");','AFDate_KeystrokeEx("dd/mm/yyyy HH:MM:ss");','06/11/2026 10:30:45','06/11/2026 10:30:45')])
def test_standard_actions_in_pdf_streams_fill_and_preserve_action_objects(encoding,compressed,fmt,key,entered,expected):
    base=streamed(source(fmt,key,initial=''),encoding,compressed);out=fill(base,entered)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        old=form_model(a)['fields'][0];new=form_model(b)['fields'][0]
        assert old['editable'] and new['editable'] and new['display_value']==expected and expected in b[0].get_text()
        _,own_a,_,_=field_structure(a);_,own_b,_,_=field_structure(b)
        assert actions(a,own_a[old['xref']]['chain'])==actions(b,own_b[new['xref']]['chain'])
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples


@pytest.mark.parametrize('kind',['large','bad_encoding','unknown_filter','additional_script'])
def test_unsupported_or_oversized_action_streams_stay_read_only(kind):
    base=source('AFDate_FormatEx("dd/mm/yyyy HH:MM");','AFDate_KeystrokeEx("dd/mm/yyyy HH:MM");',initial='')
    with f.open(stream=base) as d:
        w=next(d[0].widgets());x=d.get_new_xref();d.update_object(x,'<<>>')
        raw=b'AFDate_FormatEx("dd/mm/yyyy HH:MM");'+(b' '*2500 if kind=='large' else b'\xff' if kind=='bad_encoding' else b' app.alert(1);' if kind=='additional_script' else b'')
        d.update_stream(x,raw,compress=kind=='large')
        if kind=='unknown_filter':d.xref_set_key(x,'Filter','/ASCIIHexDecode')
        d.xref_set_key(w.xref,'AA/F/JS',f'{x} 0 R');base=d.tobytes()
    with f.open(stream=base) as d:assert not form_model(d)['fields'][0]['editable']
