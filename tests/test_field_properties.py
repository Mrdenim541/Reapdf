"""Group-aware field design, inherited properties, geometry and appearance safety."""
from pathlib import Path
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.field_properties import inspect_properties,edit_properties
from backend.form_design import create_field
from backend.forms import form_model
from backend.form_data import flatten_form
from backend.engine import DocumentError,export_pdf
from scripts.create_advanced_form_sample import create


def simple(kind='text',rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Contenido conservado');d.new_page().insert_text((40,80),'Otra pagina');base=d.tobytes()
    base=create_field(base,[],{'name':'Cliente','kind':kind,'page':0,'box':[60,180,300,70],'value':True if kind=='checkbox' else 'Ana' if kind in ['text','multiline','choice'] else 'opcion_2','options':['Ana','Eva']})
    with f.open(stream=base) as d:
        p=d[0]
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);return d.tobytes()


def row(data,name='Cliente'):
    return next(v for v in inspect_properties(data,[])['fields'] if v['name']==name)


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_geometry_and_style_retains_values_and_other_page(rotation,crop):
    base=simple(rotation=rotation,crop=crop);r=row(base);box=r['box'];target=[box[0]+10,box[1]+10,box[2]+10,box[3]+10]
    out=edit_properties(base,[],0,r['xref'],{'box':target,'font':'cour','size':14,'color':[.2,.4,.6],'label':'Nombre completo','required':True,'max_length':60,'fill_color':[.9,.95,1]})
    new=row(out);assert new['box']==pytest.approx(target,abs=.01) and new['value']=='Ana' and new['name']=='Cliente'
    assert new['properties']['font']=='cour' and new['properties']['required'] and new['properties']['max_length']==60 and new['properties']['label']=='Nombre completo'
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[1].get_pixmap().samples==b[1].get_pixmap().samples
        assert a[0].rotation==b[0].rotation and a[0].cropbox==b[0].cropbox
        flat=flatten_form(out,[])
        with f.open(stream=flat) as c:assert c[0].get_pixmap().samples==b[0].get_pixmap().samples and 'Ana' in c[0].get_text()


@pytest.mark.parametrize('kind',['text','multiline','checkbox','choice','radio'])
def test_readonly_lock_and_unlock_keeps_native_values(kind):
    base=simple(kind);r=row(base)
    locked=edit_properties(base,[],0,r['xref'],{'readonly':True,'required':True})
    lr=row(locked);assert lr['properties']['readonly'] and lr['can_design'] and not lr['editable'] and lr['value']==r['value']
    unlocked=edit_properties(locked,[],0,lr['xref'],{'readonly':False})
    ur=row(unlocked);assert ur['editable'] and not ur['properties']['readonly'] and ur['value']==r['value']
    if kind=='radio':assert ur['choices']==r['choices']


def test_shared_text_updates_all_formats_but_moves_only_selected_widget(tmp_path):
    path=tmp_path/'group.pdf';create(path);base=path.read_bytes()
    rows=inspect_properties(base,[])['fields'];selected=next(v for v in rows if v['name']=='Datos.Nombre')
    values=[{'page':selected['page'],'xref':selected['xref'],'value':'María Pérez'}]
    base=export_pdf(base,[{'type':'form_fill','page':0,'values':values}]);rows=inspect_properties(base,[])['fields'];selected=next(v for v in rows if v['name']=='Datos.Nombre');old={v['page']:v for v in rows if v['group']==selected['group']}
    box=selected['box'];target=[box[0]+10,box[1]+10,box[2]+10,box[3]+10]
    out=edit_properties(base,[],selected['page'],selected['xref'],{'box':target,'font':'tiro','size':11,'label':'Nombre del solicitante','required':True,'max_length':80})
    matches=[v for v in inspect_properties(out,[])['fields'] if v['name']=='Datos.Nombre']
    assert len(matches)==2 and all(v['value']=='María Pérez' and v['properties']['font']=='tiro' and v['properties']['label']=='Nombre del solicitante' and v['properties']['required'] and v['properties']['max_length']==80 for v in matches)
    for v in matches:assert v['box']==pytest.approx(target if v['page']==selected['page'] else old[v['page']]['box'],abs=.01)
    other_before=[v for v in rows if v['name']!='Datos.Nombre'];other_after=[v for v in inspect_properties(out,[])['fields'] if v['name']!='Datos.Nombre']
    assert [(v['name'],v['value'],v['box'],v['properties']) for v in other_before]==[(v['name'],v['value'],v['box'],v['properties']) for v in other_after]


@pytest.mark.parametrize('changes',[
 {'box':[-1,20,200,50]},{'box':[20,20,10,10]},{'box':[20,20,1000,100]},
 {'max_length':2},{'font':'hebo'},{'size':72,'box':[60,180,30,20]},
 {'readonly':1},{'required':'yes'},{'label':'x\nbad'},{'unsupported':True},
])
def test_invalid_or_nonfitting_changes_rejected(changes):
    base=simple();r=row(base)
    with pytest.raises(DocumentError):edit_properties(base,[],0,r['xref'],changes)


@pytest.mark.parametrize('kind',['script','container_readonly','internal_rotation','locked_widget'])
def test_advanced_properties_remain_protected(kind,tmp_path):
    path=tmp_path/'group.pdf';create(path)
    with f.open(path) as d:
        r=next(v for v in form_model(d)['fields'] if v['name']=='Datos.Nombre');owner=r['group']
        if kind=='script':d.xref_set_key(owner,'AA','<</K<</S/JavaScript/JS(app.alert(1))>>>>')
        elif kind=='locked_widget':d.xref_set_key(r['xref'],'F','128')
        elif kind=='internal_rotation':d.xref_set_key(r['xref'],'MK/R','90')
        else:
            parent=int(d.xref_get_key(owner,'Parent')[1].split()[0]);d.xref_set_key(parent,'Ff','1')
        base=d.tobytes()
    r=next(v for v in inspect_properties(base,[])['fields'] if v['name']=='Datos.Nombre');assert not r['can_design']
    with pytest.raises(DocumentError):edit_properties(base,[],r['page'],r['xref'],{'label':'Nuevo'})


def test_api_preview_is_read_only_and_poppler_sees_filled_text(tmp_path):
    base=simple()
    with TestClient(app) as client:
        d=client.post('/api/documents',files={'file':('field.pdf',base,'application/pdf')}).json();url='/api/documents/'+d['id']
        source=client.post(url+'/field-properties',json={}).json()['fields'][0];payload={'page':0,'xref':source['xref'],'changes':{'label':'Cliente revisado','font':'tiro','size':14}}
        preview=client.post(url+'/edit-field-properties',json=payload|{'preview':True});assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        assert client.post(url+'/field-properties',json={}).json()['fields'][0]['properties']['label']==source['properties']['label']
        result=client.post(url+'/edit-field-properties',json=payload);assert result.status_code==200
    out=edit_properties(base,[],0,row(base)['xref'],payload['changes'])
    if shutil.which('pdftotext'):
        p=tmp_path/'flat.pdf';p.write_bytes(flatten_form(out,[]));assert 'Ana' in subprocess.check_output(['pdftotext',str(p),'-']).decode()
