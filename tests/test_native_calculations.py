import hashlib,json
import pymupdf as f
import pytest
from backend.engine import DocumentError,export_pdf
from backend.forms import form_model
from backend.native_calculations import parse,repair_order


def source(operation='SUM',literal='array',order=None,cycle=False,readonly=True):
    with f.open() as d:
        refs={}
        for page,names in enumerate([['A','B','Total'],['Factor','Final']]):
            p=d.new_page()
            p.insert_text((30,30),'PAGE '+str(page+1))
            for index,name in enumerate(names):
                w=f.Widget();w.field_name=name;w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,70+index*70,400,110+index*70);w.text_font='helv';w.text_fontsize=12;w.field_value={'A':'1.25','B':'2.75','Factor':'2'}.get(name,'0');w.field_flags=1 if readonly and name in ['Total','Final'] else 0;p.add_widget(w);refs[name]=list(p.widgets())[-1].xref
        for name,kind,inputs in [('Total',operation,['Final','B'] if cycle else ['A','B']),('Final','PRD',['Total','Factor'])]:
            args=','.join(json.dumps(v) for v in inputs);items='new Array('+args+')' if literal=='array' else '['+args+']';code='AFSimple_Calculate('+json.dumps(kind)+','+items+');'
            aa='/C<</S/JavaScript/JS '+f.get_pdf_str(code)+'>>/F<</S/JavaScript/JS '+f.get_pdf_str('AFNumber_Format(2,2,0,0,"",true);')+'>>/K<</S/JavaScript/JS '+f.get_pdf_str('AFNumber_Keystroke(2,2);')+'>>'
            d.xref_set_key(refs[name],'AA','<<'+aa+'>>')
        d.xref_set_key(d.pdf_catalog(),'AcroForm/CO','['+' '.join(str(refs[n])+' 0 R' for n in (order or ['Total','Final']))+']');return d.tobytes()


def values(data):
    with f.open(stream=data) as d:return {w.field_name:w.field_value for p in d for w in p.widgets() or []}


def fill(base,name,value):
    with f.open(stream=base) as d:row=next(r for r in form_model(d)['fields'] if r['name']==name)
    return [{'type':'form_fill','page':0,'values':[{'page':row['page'],'xref':row['xref'],'value':value}]}]


@pytest.mark.parametrize('operation,expected',[('SUM','4'),('PRD','3.4375'),('AVG','2'),('MIN','1.25'),('MAX','2.75')])
@pytest.mark.parametrize('literal',['array','list'])
def test_standard_native_calculations_recalculate_and_keep_actions_order_and_formats(operation,expected,literal):
    base=source(operation,literal);out=export_pdf(base,[{'type':'form_recalculate','page':0}]);assert values(out)['Total']==expected
    with f.open(stream=base) as a,f.open(stream=out) as b:
        rows=form_model(b);assert not rows['native_calculation_error'] and len(rows['native_calculations'])==2
        assert all(not r['editable'] and r['native_fillable'] for r in rows['fields'] if r['name'] in ['Total','Final'])
        assert ','.join(r['name'] for r in rows['native_calculations'])=='Total,Final'
        original={w.field_name:a.xref_get_key(w.xref,'AA/C/JS') for p in a for w in p.widgets() or []}
        assert original=={w.field_name:b.xref_get_key(w.xref,'AA/C/JS') for p in b for w in p.widgets() or []}
        assert a[0].search_for('PAGE 1')==b[0].search_for('PAGE 1')
    with pytest.raises(DocumentError):export_pdf(base,fill(base,'Total','123'))


def test_changed_input_recalculates_dependent_fields_on_other_page():
    base=source();out=export_pdf(base,fill(base,'A','10.25'));assert values(out)['Total']=='13' and values(out)['Final']=='26'
    with f.open(stream=out) as d:assert '13,00' in d[0].get_text() and '26,00' in d[1].get_text()
    assert export_pdf(base,[])==base


def test_order_repair_is_explicit_and_preserves_codes_values_and_programs():
    base=source(order=['Final','Total'])
    with f.open(stream=base) as d:assert form_model(d)['native_order_issue'] and form_model(d)['native_calculation_error']
    with pytest.raises(DocumentError):export_pdf(base,fill(base,'A','3'))
    repaired,report=repair_order(base,[]);assert report['order']==['Total','Final'] and values(base)==values(repaired)
    assert values(export_pdf(repaired,[{'type':'form_recalculate','page':0}]))['Final']=='8'


def test_cycles_missing_order_and_arbitrary_scripts_block_without_partial_results():
    for base in [source(cycle=True),source(order=['Total']),source(order=['Total','Total'])]:
        with f.open(stream=base) as d:assert form_model(d)['native_calculation_error'] and all(not r['editable'] for r in form_model(d)['fields'])
        with pytest.raises(DocumentError):export_pdf(base,[{'type':'form_recalculate','page':0}])
        with pytest.raises(DocumentError):repair_order(base,[])


@pytest.mark.parametrize('code',[
 'AFSimple_Calculate("SUM", new Array("A",getField("B")));','AFSimple_Calculate("SUM", ["A"]);app.alert(1);',
 'AFSimple_Calculate("OTHER", ["A"]);','AFSimple_Calculate("SUM", []);','AFSimple_Calculate("SUM", ["A","A"]);',
 'AFSimple_Calculate("SUM", ["A",]);','event.value=app.alert(1);',
 ])
def test_no_general_script_or_expression_evaluation(code):
    with pytest.raises(DocumentError):parse(code)


def test_project_and_recovery_state_keep_declarative_native_operation():
    from backend.projects import build_project,read_project
    base=source();ops=fill(base,'A','7.25');data,_=build_project(base,ops,{'name':'Native.pdf','page':1,'zoom':1,'base_changes':0});saved_base,saved_ops,_=read_project(data)
    assert values(export_pdf(saved_base,saved_ops))['Final']=='20'
    data,_=build_project(base,[{'type':'form_recalculate','page':0}],{'name':'Native.pdf','page':0,'zoom':1,'base_changes':0});saved_base,saved_ops,_=read_project(data);assert values(export_pdf(saved_base,saved_ops))['Final']=='8'


def test_page_selection_preserves_dependencies_or_rejects_missing_input():
    from backend.pages import organize_pdf
    base=source();ordered=organize_pdf(base,fill(base,'A','7.25'),[{'page':1,'rotation':90},{'page':0,'rotation':0}]);assert values(ordered)['Final']=='20'
    with f.open(stream=ordered) as d:assert not form_model(d)['native_calculation_error']
    with pytest.raises(DocumentError,match='fuente'):organize_pdf(base,[],[{'page':1,'rotation':0}])


def test_native_calculation_api_projection_recalculation_and_repair():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        base=source();doc=client.post('/api/documents',files={'file':('Native.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id'];ops=fill(base,'A','7.25')
        response=client.post(url+'/forms',json={'operations':ops});assert response.status_code==200,response.text
        model=response.json();rows={r['name']:r for r in model['fields']};assert rows['Final']['value']=='20' and rows['Final']['calculated'] and not rows['Final']['editable'] and rows['Final']['display_value']=='20,00'
        model=client.post(url+'/forms',json={'operations':[{'type':'form_recalculate','page':0}]}).json();assert next(r for r in model['fields'] if r['name']=='Final')['value']=='8'
        bad=client.post('/api/documents',files={'file':('WrongOrder.pdf',source(order=['Final','Total']),'application/pdf')}).json();fix=client.post('/api/documents/'+bad['id']+'/repair-calculation-order',json={'operations':[]});assert fix.status_code==200,fix.text;assert fix.json()['calculation_order_report']['order']==['Total','Final'] and fix.json()['id']!=bad['id']


def test_form_data_roundtrip_updates_inputs_and_recomputes_native_outputs():
    from backend.form_data import export_form_data,import_form_data
    base=source();data=export_form_data(base,fill(base,'A','7.25'));assert {v['name'] for v in data['fields']}=={'A','B','Factor'}
    ops=import_form_data(base,[{'type':'form_recalculate','page':0}],data);assert values(export_pdf(base,ops))['Final']=='20'


def test_readonly_source_with_unrecognized_actions_is_not_treated_as_constant():
    with f.open(stream=source()) as d:
        w=next(w for w in d[0].widgets() if w.field_name=='A');d.xref_set_key(w.xref,'Ff','1');d.xref_set_key(w.xref,'AA','<</F<</S/JavaScript/JS(event.value=app.alert(1);)>>>>');bad=d.tobytes()
    with f.open(stream=bad) as d:assert form_model(d)['native_calculation_error']
    with pytest.raises(DocumentError):export_pdf(bad,[{'type':'form_recalculate','page':0}])


@pytest.mark.parametrize('text',['not a number','1000000000001'])
def test_invalid_source_and_overflow_fail_before_updating_any_appearance(text):
    base=source();ops=fill(base,'A',text)
    with pytest.raises(DocumentError):export_pdf(base,ops)
    assert values(base)['Total']=='0' and values(base)['Final']=='0'


def test_native_dependencies_cannot_be_deleted_and_flattening_recomputes_values():
    from backend.form_design import delete_field
    from backend.form_data import flatten_form
    base=source()
    with f.open(stream=base) as d:
        rows=form_model(d)['fields'];assert not any(r['can_delete'] for r in rows);a=next(r for r in rows if r['name']=='A')
    with pytest.raises(DocumentError):delete_field(base,[],a['page'],a['xref'])
    out=flatten_form(base,fill(base,'A','7.25'))
    with f.open(stream=out) as d:
        assert not any(list(p.widgets() or []) for p in d) and '20,00' in d[1].get_text() and d.xref_get_key(d.pdf_catalog(),'AcroForm')[0]=='null'


@pytest.mark.parametrize('incoming',[None,[],False,'bad'])
def test_implicit_empty_fill_cannot_replace_explicit_native_recalculate(incoming):
    with pytest.raises(DocumentError):export_pdf(source(),[{'type':'form_fill','page':0,'values':incoming}])


def test_shared_native_result_updates_both_widgets_with_one_owner_and_original_action():
    from backend.form_fields import _references,set_form_key,_array
    with f.open(stream=source()) as d:
        total=next(w for w in d[0].widgets() if w.field_name=='Total');old=total.xref;actions=d.xref_get_key(old,'AA')[1]
        p=d[1];w=f.Widget();w.field_name='TemporaryTotal';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,350,400,390);w.text_font='helv';w.text_fontsize=12;p.add_widget(w);other=list(p.widgets())[-1].xref
        owner=d.get_new_xref();d.update_object(owner,f'<</T(Total)/FT/Tx/Ff 1/V(0)/Kids[{old} 0 R {other} 0 R]/AA {actions}>>')
        for child in [old,other]:
            for key in ['T','FT','Ff','V','AA']:d.xref_set_key(child,key,'null')
            d.xref_set_key(child,'Parent',f'{owner} 0 R')
        roots=[ref for ref in _references(d,d.pdf_catalog(),'AcroForm/Fields') if ref[0] not in [old,other]];set_form_key(d,'Fields',_array(roots+[(owner,0)]))
        final=next(w.xref for w in d[1].widgets() if w.field_name=='Final');set_form_key(d,'CO',f'[{owner} 0 R {final} 0 R]');base=d.tobytes()
    out=export_pdf(base,fill(base,'A','7.25'))
    with f.open(stream=out) as d:
        rows=[r for r in form_model(d)['fields'] if r['name']=='Total'];assert len(rows)==2 and len({r['group'] for r in rows})==1 and all(r['value']=='10' and r['native_calculated'] for r in rows)
        assert all('10,00' in d[r['page']].get_text() for r in rows)
        assert all(d.xref_get_key(r['xref'],'V')[0]=='null' for r in rows) and d.xref_get_key(rows[0]['group'],'AA/C/JS')[0]=='string'
        assert values(out)['Final']=='20'
