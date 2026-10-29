from copy import deepcopy
from decimal import Decimal
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.forms import form_model
from backend.engine import DocumentError,export_pdf
from backend.form_calculations import calculate_fields
from backend.projects import build_project,read_project


def source(values=('0,1','0,2','')):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,50),'Calculos de prueba')
        for i,(name,value) in enumerate(zip(['A','B','Total'],values)):
            w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name=name;w.field_value=value;w.text_fontsize=12;w.rect=f.Rect(40,100+i*60,300,130+i*60);p.add_widget(w)
        return d.tobytes()


def config(base,**kwargs):
    with f.open(stream=base) as d:fields=form_model(d)['fields']
    ref=lambda r:{'page':r['page'],'xref':r['xref']}
    return {'operation':'sum','sources':[ref(r) for r in fields[:2]],'target':ref(fields[2]),'decimal':'comma','places':2,'empty_zero':False}|kwargs


@pytest.mark.parametrize('kind,expected',[('sum','0,30'),('product','0,02'),('average','0,15'),('min','0,10'),('max','0,20')])
def test_decimal_operations_native_values_and_form_project_roundtrip(kind,expected):
    base=source();ops,r=calculate_fields(base,[],config(base,operation=kind));assert r['value']==expected and not r['automatic']
    out=export_pdf(base,ops)
    with f.open(stream=out) as d:
        rows=form_model(d)['fields'];assert rows[2]['value']==expected and rows[0]['value']=='0,1'
        assert not any(d.xref_get_key(row['xref'],'AA')[0]!='null' for row in rows)
    view={'name':'Calculos.pdf','page':0,'zoom':1};packed,_=build_project(base,ops,view);original,restored,_=read_project(packed)
    assert original==base and restored==ops


@pytest.mark.parametrize('value,result',[('1.005','1.01'),('-1.005','-1.01'),('-0.001','0.00')])
def test_explicit_dot_separator_and_half_away_from_zero(value,result):
    base=source((value,'0',''));ops,r=calculate_fields(base,[],config(base,decimal='dot'));assert r['value']==result


def test_pending_fills_are_used_and_other_values_preserved_and_noop_is_allowed():
    base=source();cfg=config(base);a=cfg['sources'][0]
    previous=[{'type':'form_fill','page':0,'values':[a|{'value':'4,5'}]}]
    ops,r=calculate_fields(base,previous,cfg);assert r['value']=='4,70' and len(ops[0]['values'])==2
    updated=export_pdf(base,ops);again,_=calculate_fields(updated,[],config(updated));assert again==[]


def test_empty_values_need_explicit_zero_option():
    base=source(('','2',''))
    with pytest.raises(DocumentError,match='número'):calculate_fields(base,[],config(base))
    assert calculate_fields(base,[],config(base,empty_zero=True))[1]['value']=='2,00'


@pytest.mark.parametrize('value',['1.000,25','1,000.25','€ 2','10%','1e2','NaN','Infinity','1000000000001'])
def test_ambiguous_and_oversize_inputs_fail_without_guessing(value):
    base=source((value,'1',''))
    with pytest.raises(DocumentError):calculate_fields(base,[],config(base))


@pytest.mark.parametrize('patch',[
 {'operation':'eval'},{'operation':[]},{'decimal':[]},{'places':True},{'places':7},{'empty_zero':1},
 {'sources':[]},{'sources':[{'page':True,'xref':1}]},{'target':{}},
])
def test_invalid_configuration_rejected(patch):
    base=source()
    with pytest.raises(DocumentError):calculate_fields(base,[],config(base,**patch))


@pytest.mark.parametrize('kind',['duplicate','target_source','readonly','signed','scripts','max_length','overflow'])
def test_constraints_and_unsafe_forms_are_preserved(kind):
    base=source(('999999999999','999999999999','')) if kind=='overflow' else source()
    cfg=config(base)
    if kind=='duplicate':cfg['sources']*=2
    elif kind=='target_source':cfg['target']=cfg['sources'][0]
    else:
        with f.open(stream=base) as d:
            if kind=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>')
            elif kind=='scripts':d.xref_set_key(d.pdf_catalog(),'AcroForm/CO',f"[{cfg['target']['xref']} 0 R]")
            elif kind=='readonly':d.xref_set_key(cfg['target']['xref'],'Ff','1')
            elif kind=='max_length':d.xref_set_key(cfg['target']['xref'],'MaxLen','2')
            base=d.tobytes()
    with pytest.raises(DocumentError):calculate_fields(base,[],cfg)


def test_shared_target_updates_all_widgets_and_sources_cannot_double_count(tmp_path):
    from scripts.create_advanced_form_sample import create
    path=tmp_path/'shared.pdf';create(path)
    with f.open(path) as d:
        p=d[0]
        for i in range(2):
            w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Numero'+str(i);w.field_value=str(i+2);w.rect=f.Rect(50,400+i*50,200,430+i*50);p.add_widget(w)
        base=d.tobytes()
    with f.open(stream=base) as d:fields=form_model(d)['fields']
    refs=lambda rows:[{'page':r['page'],'xref':r['xref']} for r in rows]
    group=[r for r in fields if r['name']=='Datos.Nombre'];numbers=[r for r in fields if r['name'].startswith('Numero')]
    cfg={'operation':'sum','sources':refs(numbers),'target':refs(group)[0],'decimal':'dot','places':2,'empty_zero':False}
    ops,r=calculate_fields(base,[],cfg);assert r['value']=='5.00'
    with f.open(stream=export_pdf(base,ops)) as d:assert all(r['value']=='5.00' for r in form_model(d)['fields'] if r['name']=='Datos.Nombre')
    cfg['sources']=refs(group);cfg['target']=refs(numbers)[0]
    with pytest.raises(DocumentError,match='repitas'):calculate_fields(base,[],cfg)


def test_api_preview_is_read_only_and_calculation_returns_normal_fill_operations():
    base=source()
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('calc.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        payload={'calculation':config(base)};r=c.post(url+'/calculate-fields',json=payload|{'preview':True});assert r.status_code==200,r.text
        assert r.json()['report']['value']=='0,30' and r.json()['preview'].startswith('data:image/png;base64,')
        assert c.post(url+'/export',json={'operations':[]}).content==base
        r=c.post(url+'/calculate-fields',json=payload);assert r.status_code==200 and r.json()['operations'][0]['type']=='form_fill'
