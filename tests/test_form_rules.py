from copy import deepcopy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf,DocumentError
from backend.form_rules import resolve_rules
from backend.form_data import export_form_data
from backend.projects import build_project,read_project
from backend.forms import form_model


def source():
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        for i,(name,value) in enumerate([('A','0,1'),('B','0,2'),('Subtotal',''),('Total','')]):
            p.insert_text((40,60+i*80),name);w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name=name;w.field_value=value;w.text_fontsize=12;w.rect=f.Rect(40,70+i*80,300,100+i*80);p.add_widget(w)
        return d.tobytes()


def configuration(base):
    with f.open(stream=base) as d:rows=form_model(d)['fields']
    refs={r['name']:{'page':r['page'],'xref':r['xref']} for r in rows}
    rule=lambda sources,target:{'operation':'sum','sources':[refs[n] for n in sources],'target':refs[target],'decimal':'comma','places':2,'empty_zero':False}
    return refs,{'type':'form_rules','page':0,'version':1,'rules':[rule(['Subtotal','A'],'Total'),rule(['A','B'],'Subtotal')]}


def values(data):
    with f.open(stream=data) as d:return {r['name']:r['value'] for r in form_model(d)['fields']}


def test_dependency_order_recalculates_every_export_and_project_preserves_rules():
    base=source();refs,rules=configuration(base);ops=[rules]
    assert values(export_pdf(base,ops))['Total']=='0,40'
    effective,reports,targets=resolve_rules(base,ops);assert [r['rule'] for r in reports]==[2,1]
    assert len(targets)==2
    changed=ops+[{'type':'form_fill','page':0,'values':[refs['A']|{'value':'1,5'}]}]
    assert values(export_pdf(base,changed))=={'A':'1,5','B':'0,2','Subtotal':'1,70','Total':'3,20'}
    packed,_=build_project(base,changed,{'name':'Reglas.pdf','page':0,'zoom':1})
    old,restored,_=read_project(packed);assert restored==changed and values(export_pdf(old,restored))['Total']=='3,20'
    # PDF bytes contain values, not native JS/actions or persisted formulas.
    exported=export_pdf(base,changed)
    with f.open(stream=exported) as d:assert d.xref_get_key(d.pdf_catalog(),'AcroForm/CO')[0]=='null'
    assert values(exported)['Total']=='3,20' and values(base)['Total']==''


@pytest.mark.parametrize('kind',['cycle','duplicate','self','missing','limit','badversion','invalidnumber'])
def test_invalid_rules_fail_atomically(kind):
    base=source();refs,rules=configuration(base)
    if kind=='cycle':rules['rules'][1]['sources']=[refs['Total']]
    elif kind=='duplicate':rules['rules'][1]['target']=refs['Total']
    elif kind=='self':rules['rules'][0]['sources']=[refs['Total']]
    elif kind=='missing':rules['rules'][0]['target']={'page':0,'xref':999999}
    elif kind=='limit':rules['rules']*=6
    elif kind=='badversion':rules['version']=True
    else:rules['rules'][1]['decimal']='dot'
    with pytest.raises(DocumentError):export_pdf(base,[rules])
    assert values(base)['Total']==''


def test_pending_rule_target_overrides_cannot_mask_calculation_and_json_export_matches_pdf():
    base=source();refs,rules=configuration(base)
    ops=[rules,{'type':'form_fill','page':0,'values':[refs['Total']|{'value':'999'}]}]
    assert values(export_pdf(base,ops))['Total']=='0,40'
    data=export_form_data(base,ops);assert next(r for r in data['fields'] if r['name']=='Total')['value']=='0,40'


def test_rules_are_independent_of_manual_fill_order_and_removal_restores_session_values():
    base=source();refs,rules=configuration(base);fill={'type':'form_fill','page':0,'values':[refs['A']|{'value':'2'}]}
    assert values(export_pdf(base,[rules,fill]))==values(export_pdf(base,[fill,rules]))
    assert values(export_pdf(base,[fill]))['Total']==''


def test_rule_values_and_readonly_targets_are_exposed_by_api_without_modifying_source():
    base=source();refs,rules=configuration(base)
    with TestClient(app) as c:
        d=c.post('/api/documents',files={'file':('rules.pdf',base,'application/pdf')}).json();url='/api/documents/'+d['id']
        reviewed=c.post(url+'/review-form-rules',json={'operations':[],'rules':rules['rules']});assert reviewed.status_code==200,reviewed.text
        assert reviewed.json()['reports'][-1]['value']=='0,40'
        model=c.post(url+'/forms',json={'operations':[rules]}).json()
        total=next(r for r in model['fields'] if r['name']=='Total');assert total['calculated'] and not total['editable'] and total['base_editable'] and total['value']=='0,40'
        assert c.post(url+'/export',json={'operations':[]}).content==base
        assert c.post(url+'/review-form-rules',json={'operations':[rules],'rules':[]}).json()['operations']==[]


def test_point_calculations_use_rule_results_and_cannot_override_rule_targets():
    from backend.form_calculations import calculate_fields
    base=source();refs,rules=configuration(base)
    config={'operation':'sum','sources':[refs['Total']],'target':refs['B'],'decimal':'comma','places':2,'empty_zero':False}
    # A non-rule destination can use the current calculated value as input.
    ops,report=calculate_fields(base,[rules],config);assert report['value']=='0,40'
    assert any(op['type']=='form_rules' for op in ops)
    with pytest.raises(DocumentError,match='destino'):calculate_fields(base,[rules],config|{'target':refs['Subtotal']})


def test_structural_versions_conserve_values_and_project_can_restore_active_rules():
    from backend.pages import organize_pdf
    base=source();refs,rules=configuration(base)
    changed=organize_pdf(base,[rules],[{'page':0,'rotation':90}])
    assert values(changed)['Total']=='0,40'
    packed,_=build_project(base,[rules],{'name':'Antes de organizar.pdf','page':0,'zoom':1})
    old,ops,_=read_project(packed);assert ops[0]['type']=='form_rules' and values(export_pdf(old,ops))['Total']=='0,40'
