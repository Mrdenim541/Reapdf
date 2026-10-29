from copy import deepcopy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf,DocumentError
from backend.pages import organize_pdf
from backend.form_rules import remap_organized_rules
from backend.forms import form_model
from backend.projects import build_project,read_project
from tests.test_form_rules import source,configuration,values


def multipage():
    with f.open(stream=source()) as d:
        d.new_page().insert_text((40,50),'Pagina independiente')
        return d.tobytes()

@pytest.mark.parametrize('pages',[
    [{'page':1,'rotation':0},{'page':0,'rotation':0}],
    [{'page':0,'rotation':90},{'page':1,'rotation':270}],
    [{'page':0,'rotation':180}],
])
def test_rules_stay_active_after_reorder_rotation_and_deleting_unrelated_page(pages):
    base=multipage();refs,rules=configuration(base);operations=[rules,{'type':'form_fill','page':0,'values':[refs['A']|{'value':'1,5'}]}]
    before=deepcopy(operations);out=organize_pdf(base,operations,pages);mapped=remap_organized_rules(base,operations,out,pages)
    assert operations==before and len(mapped)==1 and values(export_pdf(out,mapped))['Total']=='3,20'
    with f.open(stream=out) as d:fields=form_model(d)['fields']
    a=next(r for r in fields if r['name']=='A');assert a['page']==next(i for i,r in enumerate(pages) if r['page']==0)
    changed=mapped+[{'type':'form_fill','page':0,'values':[{'page':a['page'],'xref':a['xref'],'value':'2'}]}]
    assert values(export_pdf(out,changed))['Total']=='4,20'
    packed,_=build_project(out,changed,{'name':'Organizado.pdf','page':0,'zoom':1});restored,ops,_=read_project(packed)
    assert values(export_pdf(restored,ops))['Total']=='4,20'


def test_deleting_a_required_field_rejects_without_storing_new_version():
    base=multipage();_,rules=configuration(base)
    with TestClient(app) as c:
        info=c.post('/api/documents',files={'file':('reglas.pdf',base,'application/pdf')}).json();url='/api/documents/'+info['id']
        stored=set(app.state.root.glob('*.pdf'))
        response=c.post(url+'/organize',json={'operations':[rules],'pages':[{'page':1,'rotation':0}]})
        assert response.status_code==422 and 'necesario' in response.json()['detail']
        assert set(app.state.root.glob('*.pdf'))==stored
        assert values(c.post(url+'/export',json={'operations':[rules]}).content)['Total']=='0,40'


def test_api_returns_only_remapped_project_rules_other_edits_materialized():
    base=multipage();refs,rules=configuration(base)
    with TestClient(app) as c:
        info=c.post('/api/documents',files={'file':('reglas.pdf',base,'application/pdf')}).json();url='/api/documents/'+info['id']
        response=c.post(url+'/organize',json={'operations':[rules,{'type':'form_fill','page':0,'values':[refs['A']|{'value':'1,5'}]}],'pages':[{'page':1,'rotation':0},{'page':0,'rotation':90}]})
        assert response.status_code==200,response.text
        next_doc=response.json();assert [op['type'] for op in next_doc['project_operations']]==['form_rules']
        model=c.post('/api/documents/'+next_doc['id']+'/forms',json={'operations':next_doc['project_operations']}).json()
        assert next(r for r in model['fields'] if r['name']=='Total')['calculated']
        assert next(r for r in model['fields'] if r['name']=='Total')['value']=='3,20'


def test_no_rule_operation_preserves_legacy_response_behavior():
    base=multipage();assert remap_organized_rules(base,[],base,[{'page':0,'rotation':0},{'page':1,'rotation':0}])==[]


@pytest.mark.parametrize('keep',[0,1])
def test_shared_referenced_widget_can_be_removed_if_its_logical_field_survives(tmp_path,keep):
    from scripts.create_advanced_form_sample import create
    path=tmp_path/'shared.pdf';create(path)
    with f.open(path) as d:
        for i in range(2):
            p=d[i];w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Input'+str(i);w.field_value='2';w.rect=f.Rect(50,600,200,630);p.add_widget(w)
        base=d.tobytes()
    with f.open(stream=base) as d:rows=form_model(d)['fields']
    ref=lambda r:{'page':r['page'],'xref':r['xref']}
    target=next(r for r in rows if r['name']=='Datos.Nombre' and r['page']!=keep)
    source_row=next(r for r in rows if r['name']=='Input'+str(keep))
    rules={'type':'form_rules','page':0,'version':1,'rules':[{'operation':'sum','sources':[ref(source_row)],'target':ref(target),'decimal':'dot','places':2,'empty_zero':False}]}
    pages=[{'page':keep,'rotation':90}];out=organize_pdf(base,[rules],pages);mapped=remap_organized_rules(base,[rules],out,pages)
    assert mapped[0]['rules'][0]['target']['page']==0
    assert values(export_pdf(out,mapped))['Datos.Nombre']=='2.00'


def test_ambiguous_destination_name_is_not_guessed():
    base=multipage();_,rules=configuration(base);pages=[{'page':0,'rotation':0},{'page':1,'rotation':0}]
    out=organize_pdf(base,[rules],pages)
    with f.open(stream=out) as d:
        p=d[1];w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Total';w.field_value='0';w.rect=f.Rect(50,100,200,130);p.add_widget(w);out=d.tobytes()
    with pytest.raises(DocumentError,match='certeza'):remap_organized_rules(base,[rules],out,pages)
