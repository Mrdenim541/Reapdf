import pytest
import pymupdf as f
from backend.engine import DocumentError
from backend.forms import form_model
from backend.form_data import flatten_form
from tests.test_form_standard_actions import source,fill


@pytest.mark.parametrize('style',[1,3])
@pytest.mark.parametrize('separator',[0,1,2,3])
def test_red_negative_styles_store_signed_value_and_reset_color_after_reopen(style,separator):
    base=source(f'AFNumber_Format(2,{separator},{style},0," EUR",false);',f'AFNumber_Keystroke(2,{separator});',initial='')
    for value,stored,red in [('-12,5' if separator in [2,3] else '-12.5','-12.5',True),('4','4',False),('','',False)]:
        if not value:red=False
        base=fill(base,value)
        with f.open(stream=base) as d:
            row=form_model(d)['fields'][0];assert row['value']==(stored.replace('.',',') if separator in [2,3] else stored)
            w=next(d[0].widgets());assert w.field_value==stored and tuple(w.text_color)==((1,0,0) if red else (0,0,0))
            if value:
                expected=('12,50' if separator in [2,3] else '12.50')+' EUR' if red else ('4,00' if separator in [2,3] else '4.00')+' EUR'
                if red and style==3:expected='('+expected+')'
                assert row['display_value']==expected
                spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if expected in s['text']];assert spans and all(s['color']==(0xff0000 if red else 0) for s in spans)
                with f.open(stream=flatten_form(base,[])) as flat:assert expected in flat[0].get_text()


@pytest.mark.parametrize('valid',[ 'AFRange_Validate(true,"-10",true,"10.5");','AFRange_Validate(true,\'-10\',true,\'10.5\');','AFRange_Validate(false,"unused",true,"10.5");','AFRange_Validate(true,"-10",false,"");'])
def test_literal_string_bounds_work_without_executing_javascript(valid):
    base=source('AFNumber_Format(2,1,0,0,"",false);','AFNumber_Keystroke(2,1);',valid,initial='0');out=fill(base,'5')
    with f.open(stream=out) as d:assert next(d[0].widgets()).field_value=='5'


@pytest.mark.parametrize('bound',['NaN','Infinity','1+1','1,000','1000000000001',''])
def test_invalid_active_bound_is_protected(bound):
    base=source(valid=f'AFRange_Validate(true,"{bound}",true,"100");')
    with f.open(stream=base) as d:assert not form_model(d)['fields'][0]['editable']


def test_outside_string_bounds_is_rejected_atomically():
    base=source(valid='AFRange_Validate(true,"0",true,"10");',initial='5')
    with pytest.raises(DocumentError):fill(base,'11')
    with f.open(stream=base) as d:assert next(d[0].widgets()).field_value=='5'


def test_shared_numeric_widgets_regenerate_red_appearances_without_child_value_overrides(tmp_path):
    from scripts.create_advanced_form_sample import create
    from backend.engine import export_pdf
    path=tmp_path/'shared.pdf';create(path)
    with f.open(path) as d:
        r=next(r for r in form_model(d)['fields'] if r['kind']=='text');d.xref_set_key(r['group'],'AA','<</F<</S/JavaScript/JS(AFNumber_Format\\(2,1,3,0,\"\",false\\);)>>/K<</S/JavaScript/JS(AFNumber_Keystroke\\(2,1\\);)>>>>');base=d.tobytes()
    with f.open(stream=base) as d:r=next(r for r in form_model(d)['fields'] if r['kind']=='text');assert r['editable'],r['reason']
    out=export_pdf(base,[{'type':'form_fill','page':0,'values':[{'page':r['page'],'xref':r['xref'],'value':'-12.5'}]}])
    with f.open(stream=out) as d:
        rows=[r for r in form_model(d)['fields'] if r['kind']=='text'];assert len(rows)==2 and all(r['value']=='-12.5' for r in rows)
        for r in rows:
            w=d[r['page']].load_widget(r['xref']);assert tuple(w.text_color)==(1,0,0) and '(12.50)' in d[r['page']].get_text();assert d.xref_get_key(r['xref'],'V')[0]=='null'


@pytest.mark.parametrize('style',[1,3])
def test_rounded_negative_keeps_its_red_sign_and_actual_zero_resets_black(style):
    base=source(f'AFNumber_Format(2,1,{style},0,"",false);','AFNumber_Keystroke(2,1);',initial='');out=fill(base,'-0.001')
    with f.open(stream=out) as d:
        row=form_model(d)['fields'][0];assert row['display_value']==('(0.00)' if style==3 else '0.00') and row['value']=='-0.001';assert tuple(next(d[0].widgets()).text_color)==(1,0,0)
    zero=fill(out,'0')
    with f.open(stream=zero) as d:assert form_model(d)['fields'][0]['display_value']=='0.00' and tuple(next(d[0].widgets()).text_color)==(0,0,0)
