from copy import deepcopy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf
from backend.projects import build_project,read_project
from tests.test_form_rules import configuration,values
from tests.test_form_rule_organization import multipage


def upload(c,data):return c.post('/api/documents',files={'file':('Documento.pdf',data,'application/pdf')}).json()['id']
def forms(c,info):return c.post('/api/documents/'+info['id']+'/forms',json={'operations':info['project_operations']}).json()['fields']
def ref(row):return {'page':row['page'],'xref':row['xref']}

def verify_edit(c,info,source='A',target='Total',expected='4,20'):
    fields=forms(c,info);a=next(r for r in fields if r['name']==source)
    ops=info['project_operations']+[{'type':'form_fill','page':0,'values':[ref(a)|{'value':'2'}]}]
    result=c.post('/api/documents/'+info['id']+'/export',json={'operations':ops});assert result.status_code==200,result.text
    assert values(result.content)[target]==expected
    return fields

@pytest.mark.parametrize('route,params,expected_page',[
 ('insert',{'position':0,'pages':[0]},1),('insert',{'position':1,'pages':[0]},0),
 ('replace',{'position':1,'replace_count':1,'pages':[0]},0),
 ('duplicate',{'position':0,'pages':[0]},1),('duplicate',{'position':2,'pages':[0]},0),
 ('blank',{'position':0,'count':2,'width':500,'height':650},2),
 ('crop',{'pages':[0],'margins':[5,5,5,5]},0),('crop',{'pages':[0],'reset':True},0),
])
def test_page_transforms_preserve_active_rules_and_recalculate_after_input_change(route,params,expected_page):
    base=multipage();_,rules=configuration(base)
    with TestClient(app) as c:
        identity=upload(c,base);extra=upload(c,base);payload={'operations':[rules],**params}
        if route in ['insert','replace']:payload['source_id']=extra
        r=c.post(f'/api/documents/{identity}/{route}',json=payload);assert r.status_code==200,r.text
        info=r.json();assert len(info['project_operations'])==1
        fields=verify_edit(c,info);assert next(r for r in fields if r['name']=='A')['page']==expected_page
        # Imported/duplicated fields retain numeric values and no project rules.
        assert all(not r.get('calculated') for r in fields if r['name'] not in ['Subtotal','Total'])
        if route in ['insert','duplicate']:
            copies=[r for r in fields if r['name'] not in ['A','B','Subtotal','Total']];assert copies and not any(r['calculated'] for r in copies)

@pytest.mark.parametrize('kind',['replacement','crop'])
def test_dangerous_transform_is_atomic_and_cannot_rebind_to_replacement_copy(kind):
    base=multipage();_,rules=configuration(base)
    with TestClient(app) as c:
        identity=upload(c,base);other=upload(c,base);before=set(app.state.root.glob('*.pdf'))
        if kind=='crop':route='crop';params={'pages':[0],'margins':[0,0,0,150]}
        else:route='replace';params={'position':0,'replace_count':1,'pages':[0],'source_id':other}
        response=c.post(f'/api/documents/{identity}/{route}',json={'operations':[rules],**params})
        assert response.status_code==422,response.text
        assert set(app.state.root.glob('*.pdf'))==before
        assert values(c.post(f'/api/documents/{identity}/export',json={'operations':[rules]}).content)['Total']=='0,40'

@pytest.mark.parametrize('name,new_name',[('A','Importe'),('Subtotal','Parcial'),('Total','Resultado')])
def test_renaming_sources_intermediate_and_final_targets_preserves_graph(name,new_name):
    base=multipage();_,rules=configuration(base)
    with TestClient(app) as c:
        identity=upload(c,base);old=c.post(f'/api/documents/{identity}/field-properties',json={'operations':[rules]}).json()['fields'];row=next(r for r in old if r['name']==name)
        payload={'operations':[rules],**ref(row),'changes':{'partial_name':new_name,'label':'Campo actualizado','font':'cour','size':11}}
        preview=c.post(f'/api/documents/{identity}/edit-field-properties',json=payload|{'preview':True});assert preview.status_code==200 and preview.headers['content-type']=='image/png'
        response=c.post(f'/api/documents/{identity}/edit-field-properties',json=payload);assert response.status_code==200,response.text
        info=response.json();fields=verify_edit(c,info,source=new_name if name=='A' else 'A',target=new_name if name=='Total' else 'Total')
        assert not any(r['name']==name for r in fields) and any(r['name']==new_name for r in fields)
        pdf=c.post('/api/documents/'+info['id']+'/export',json={'operations':[]}).content
        packed,_=build_project(pdf,info['project_operations'],{'name':'Renombrado.pdf','page':0,'zoom':1});restored,ops,_=read_project(packed)
        assert values(export_pdf(restored,ops))[new_name if name=='Total' else 'Total']=='0,40'

@pytest.mark.parametrize('change',[{'readonly':True},{'max_length':1},{'box':[40,70,15,15]}])
def test_incompatible_source_properties_rejected_in_preview_and_apply(change):
    base=multipage();refs,rules=configuration(base)
    with TestClient(app) as c:
        identity=upload(c,base);before=set(app.state.root.glob('*.pdf'))
        for preview in [True,False]:
            r=c.post(f'/api/documents/{identity}/edit-field-properties',json={'operations':[rules],**refs['A'],'changes':change,'preview':preview})
            assert r.status_code==422,r.text
        assert set(app.state.root.glob('*.pdf'))==before


def test_new_field_and_removing_unused_field_keep_rules_but_required_deletion_is_blocked():
    base=multipage();_,rules=configuration(base)
    with TestClient(app) as c:
        identity=upload(c,base)
        r=c.post(f'/api/documents/{identity}/create-field',json={'operations':[rules],'config':{'name':'Extra','kind':'text','page':1,'box':[40,100,200,35],'value':'7'}});assert r.status_code==200,r.text
        info=r.json();fields=verify_edit(c,info);unused=next(r for r in fields if r['name']=='Extra')
        removed=c.post('/api/documents/'+info['id']+'/delete-field',json={'operations':info['project_operations'],**ref(unused)});assert removed.status_code==200,removed.text
        info=removed.json();fields=verify_edit(c,info);target=next(r for r in fields if r['name']=='Total');before=set(app.state.root.glob('*.pdf'))
        rejected=c.post('/api/documents/'+info['id']+'/delete-field',json={'operations':info['project_operations'],**ref(target)})
        assert rejected.status_code==422 and set(app.state.root.glob('*.pdf'))==before


@pytest.mark.parametrize('selected_page',[0,1])
def test_shared_hierarchical_target_rename_keeps_both_widgets_and_recalculates(tmp_path,selected_page):
    from scripts.create_advanced_form_sample import create
    from backend.forms import form_model
    path=tmp_path/'shared.pdf';create(path)
    with f.open(path) as d:
        page=d[0];w=f.Widget();w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_name='Numero';w.field_value='2';w.rect=f.Rect(40,600,250,635);page.add_widget(w);base=d.tobytes()
    with f.open(stream=base) as d:rows=form_model(d)['fields']
    number=next(r for r in rows if r['name']=='Numero');target=next(r for r in rows if r['name']=='Datos.Nombre')
    rule={'type':'form_rules','page':0,'version':1,'rules':[{'operation':'sum','sources':[ref(number)],'target':ref(target),'decimal':'dot','places':2,'empty_zero':False}]}
    with TestClient(app) as c:
        identity=upload(c,base);inspected=c.post(f'/api/documents/{identity}/field-properties',json={'operations':[rule]}).json()['fields'];selected=next(r for r in inspected if r['name']=='Datos.Nombre' and r['page']==selected_page)
        response=c.post(f'/api/documents/{identity}/edit-field-properties',json={'operations':[rule],**ref(selected),'changes':{'partial_name':'Cliente'}});assert response.status_code==200,response.text
        info=response.json();rows=forms(c,info);shared=[r for r in rows if r['name']=='Datos.Cliente'];assert len(shared)==2 and all(r['calculated'] and r['value']=='2.00' for r in shared)
        verify_edit(c,info,source='Numero',target='Datos.Cliente',expected='2.00')
