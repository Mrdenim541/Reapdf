from decimal import Decimal
import pymupdf as f
import pytest
from backend.engine import DocumentError,export_pdf
from backend.forms import form_model
from backend.form_actions import call,policy,value


def source(fmt='AFNumber_Format(2, 2, 0, 0, "EUR ", true);',key='AFNumber_Keystroke(2, 2);',valid=None,initial='12.5',shared=False):
    with f.open() as d:
        p=d.new_page();p.insert_text((30,40),'FORM SAMPLE');w=f.Widget();w.field_name='Amount';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,80,400,120);w.text_font='helv';w.text_fontsize=12;w.field_value=initial;w.field_flags=2;p.add_widget(w);xref=next(p.widgets()).xref
        aa=[]
        for event,code in [('F',fmt),('K',key),('V',valid)]:
            if code is not None:aa.append('/'+event+'<</S/JavaScript/JS '+f.get_pdf_str(code)+'>>')
        d.xref_set_key(xref,'AA','<<'+''.join(aa)+'>>')
        d.new_page().insert_text((30,40),'UNCHANGED')
        return d.tobytes()


def fill(base,text):
    with f.open(stream=base) as d:row=form_model(d)['fields'][0];assert row['editable'],row['reason']
    return export_pdf(base,[{'type':'form_fill','page':0,'values':[{'page':row['page'],'xref':row['xref'],'value':text}]}])


@pytest.mark.parametrize('fmt,key,text,canonical,display',[
 ('AFNumber_Format(2,0,0,0,"$",true);','AFNumber_Keystroke(2,0);','1234.5','1234.5','$1,234.50'),
 ('AFNumber_Format(2,2,2,0," EUR",false);','AFNumber_Keystroke(2,2);','-1.234,5','-1234.5','(1.234,50 EUR)'),
 ('AFPercent_Format(1,3);','AFPercent_Keystroke(1,3);','0,125','0.125','12,5%'),
 ('AFDate_FormatEx("dd/mm/yyyy");','AFDate_KeystrokeEx("dd/mm/yyyy");','29/02/2024','29/02/2024','29/02/2024'),
 ('AFDate_FormatEx("yyyy-mm-dd");','AFDate_KeystrokeEx("yyyy-mm-dd");','2026-10-30','2026-10-30','2026-10-30'),
 ])
def test_known_native_formats_keep_raw_values_appearances_and_original_actions(fmt,key,text,canonical,display):
    base=source(fmt,key,initial='');out=fill(base,text)
    with f.open(stream=base) as a,f.open(stream=out) as b:
        row=form_model(b)['fields'][0];w=next(b[0].widgets());assert w.field_value==canonical and row['display_value']==display and row['required']
        assert display in b[0].get_text()
        old=next(a[0].widgets());assert a.xref_get_key(old.xref,'AA/F/JS')==b.xref_get_key(w.xref,'AA/F/JS') and a.xref_get_key(old.xref,'AA/K/JS')==b.xref_get_key(w.xref,'AA/K/JS')
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
    out2=fill(out,text)
    with f.open(stream=out2) as b:assert next(b[0].widgets()).field_value==canonical


@pytest.mark.parametrize('text',['0','100','50.5'])
def test_range_inclusive_standard_validator(text):
    base=source('AFNumber_Format(2,1,0,0,"",false);','AFNumber_Keystroke(2,1);','AFRange_Validate(true,0,true,100);',initial='0');out=fill(base,text)
    with f.open(stream=out) as d:assert next(d[0].widgets()).field_value==text


@pytest.mark.parametrize('text',['-0.01','100.01','abc','1,200'])
def test_range_or_locale_invalid_input_is_atomic(text):
    base=source('AFNumber_Format(2,1,0,0,"",false);','AFNumber_Keystroke(2,1);','AFRange_Validate(true,0,true,100);',initial='0')
    with pytest.raises(DocumentError):fill(base,text)
    with f.open(stream=base) as d:assert next(d[0].widgets()).field_value=='0'


@pytest.mark.parametrize('text',['29/02/2023','31/04/2024','1/01/2024','2024-01-01'])
def test_invalid_dates_are_rejected(text):
    with pytest.raises(DocumentError):fill(source('AFDate_FormatEx("dd/mm/yyyy");','AFDate_KeystrokeEx("dd/mm/yyyy");',initial=''),text)


@pytest.mark.parametrize('code',[
 'AFNumber_Format(2,0,0,0,"",true); evil();','AFNumber_Format(2+1,0,0,0,"",true);',
 'AFNumber_Format(2,0,1,0,"",true);','AFNumber_Format(2,0,0,0,app.alert(1),true);',
 'AFNumber_Format(2,0,0,0,"",true,);','event.value="abc";', 'AFDate_FormatEx("unknown");',
 'AFNumber_Format(2,4,0,0,"",true);','AFNumber_Format(2,0,0,0,"",1);','AFNumber_Format(200,0,0,0,"",true);',
 ])
def test_unknown_or_executable_actions_stay_protected(code):
    with f.open(stream=source(code,None)) as d:
        row=form_model(d)['fields'][0];assert not row['editable'] and row['reason']


def test_action_chains_streams_and_other_events_are_not_evaluated():
    base=source()
    for property,value_ in [('AA/F/Next','<</S/JavaScript/JS(app.alert(1))>>'),('AA/E','<</S/JavaScript/JS(app.alert(1))>>')]:
        with f.open(stream=base) as d:
            w=next(d[0].widgets());d.xref_set_key(w.xref,property,value_);assert not form_model(d)['fields'][0]['editable']


def test_empty_formatted_field_can_be_saved_and_corrected():
    base=source(initial='not-number')
    with f.open(stream=base) as d:row=form_model(d)['fields'][0];assert row['editable'] and row['format_issue']
    out=fill(base,'15,25');out=fill(out,'')
    with f.open(stream=out) as d:assert next(d[0].widgets()).field_value==''


def test_parser_accepts_bounded_quotes_without_executing_anything():
    assert call("AFDate_FormatEx('dd/mm/yyyy');")==('AFDate_FormatEx',['dd/mm/yyyy'])
    with pytest.raises(DocumentError):call('AFDate_FormatEx("dd/mm/yyyy");\n app.alert(1)')


def test_form_api_formats_pending_values_and_preserves_base_identity():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        response=client.post('/api/documents',files={'file':('Formats.pdf',source(initial=''),'application/pdf')});url='/api/documents/'+response.json()['id']
        model=client.post(url+'/forms',json={'operations':[]}).json();row=model['fields'][0];assert row['required'] and row['format']['kind']=='number'
        ops=[{'type':'form_fill','page':0,'values':[{'page':0,'xref':row['xref'],'value':'1500,25'}]}]
        filled=client.post(url+'/forms',json={'operations':ops});assert filled.status_code==200,filled.text
        entry=filled.json()['fields'][0];assert entry['display_value']=='EUR 1.500,25' and entry['value']=='1500,25' and entry['base_value']=='' and entry['xref']==row['xref']
        assert client.post(url+'/pages/0/preview',json={'operations':ops,'scale':1}).status_code==200


def test_action_on_shared_logical_field_syncs_both_appearances():
    with f.open(stream=source(initial='0')) as d:
        first=next(d[0].widgets());xref=first.xref;aa=d.xref_get_key(xref,'AA')[1]
        p=d[1];w=f.Widget();w.field_name='Other';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,80,400,120);w.text_font='helv';w.text_fontsize=12;p.add_widget(w);other=next(p.widgets()).xref
        owner=d.get_new_xref();d.update_object(owner,f'<</T(Amount)/FT/Tx/Ff 2/V(0)/Kids[{xref} 0 R {other} 0 R]/AA {aa}>>')
        for child in [xref,other]:
            for key in ['T','FT','Ff','V','AA']:d.xref_set_key(child,key,'null')
            d.xref_set_key(child,'Parent',f'{owner} 0 R')
        d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{owner} 0 R]');base=d.tobytes()
    out=fill(base,'1200,25')
    with f.open(stream=out) as d:
        rows=form_model(d)['fields'];assert len(rows)==2 and all(r['editable'] and r['value']=='1200,25' for r in rows)
        assert all('EUR 1.200,25' in p.get_text() for p in d)
        assert all(d.xref_get_key(r['group'],'AA/F/JS')[0]=='string' for r in rows)


def test_max_length_limits_raw_value_without_truncating_formatted_appearance():
    with f.open(stream=source(initial='')) as d:
        w=next(d[0].widgets());d.xref_set_key(w.xref,'MaxLen','6');base=d.tobytes()
    with f.open(stream=fill(base,'1234,5')) as d:assert next(d[0].widgets()).field_value=='1234.5' and 'EUR 1.234,50' in d[0].get_text()
