"""Field identity and choice changes preserve grouping, values and PDF reset semantics."""
from pathlib import Path
import pymupdf as f
import pytest
from backend.field_properties import inspect_properties,edit_properties
from backend.form_data import flatten_form,export_form_data
from backend.forms import form_model
from backend.engine import DocumentError,export_pdf
from backend.projects import build_project,read_project
from scripts.create_advanced_form_sample import create
from tests.test_field_properties import simple,row


@pytest.mark.parametrize('kind',['text','multiline','checkbox','choice','radio'])
def test_rename_changes_identity_while_preserving_value_and_appearance(kind):
    base=simple(kind);r=row(base);out=edit_properties(base,[],0,r['xref'],{'partial_name':'Solicitante_Á'})
    new=row(out,'Solicitante_Á');assert new['value']==r['value'] and new['group_size']==r['group_size']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[1].get_pixmap().samples==b[1].get_pixmap().samples


def test_shared_hierarchical_rename_keeps_parent_and_can_still_fill_all_positions(tmp_path):
    path=tmp_path/'shared.pdf';create(path);base=path.read_bytes();r=row(base,'Datos.Nombre')
    out=edit_properties(base,[],r['page'],r['xref'],{'partial_name':'Solicitante'})
    rows=[v for v in inspect_properties(out,[])['fields'] if v['name']=='Datos.Solicitante'];assert len(rows)==2
    assert not any(v['name']=='Datos.Nombre' for v in inspect_properties(out,[])['fields'])
    filled=export_pdf(out,[{'type':'form_fill','page':rows[0]['page'],'values':[{'page':rows[0]['page'],'xref':rows[0]['xref'],'value':'María'}]}])
    with f.open(stream=filled) as d:
        members=[v for v in form_model(d)['fields'] if v['name']=='Datos.Solicitante'];assert len(members)==2 and all(v['value']=='María' for v in members)
        assert all('María' in d[v['page']].get_text() for v in members)
    packed,_=build_project(filled,[],{'name':'Identidad.pdf','page':0,'zoom':1,'base_changes':1});restored,ops,_=read_project(packed)
    assert row(restored,'Datos.Solicitante')['value']=='María'


@pytest.mark.parametrize('name',['','a.b',' a','a ','a\n','a\x00','a'*101,None,12])
def test_invalid_partial_names_are_rejected(name):
    base=simple();r=row(base)
    with pytest.raises(DocumentError):edit_properties(base,[],0,r['xref'],{'partial_name':name})


def test_collision_with_sibling_field_or_container_is_rejected(tmp_path):
    path=tmp_path/'shared.pdf';create(path);base=path.read_bytes();r=row(base,'Datos.Nombre')
    with f.open(stream=base) as d:
        owner=r['group'];parent=int(d.xref_get_key(owner,'Parent')[1].split()[0]);kids=d.xref_get_key(parent,'Kids')[1]
        refs=[int(v) for v in __import__('re').findall(r'(\d+) 0 R',kids) if int(v)!=owner];assert refs
        collision=d.xref_get_key(refs[0],'T')[1]
    with pytest.raises(DocumentError,match='hermano'):edit_properties(base,[],r['page'],r['xref'],{'partial_name':collision})


def test_choice_export_values_and_display_labels_reorder_without_changing_value_or_default():
    with f.open(stream=simple('choice')) as d:
        r=row(d.tobytes());d.xref_set_key(r['group'],'DV','(Eva)');base=d.tobytes()
    r=row(base);options=[{'value':'Eva','label':'Evaluadora'},{'value':'Ana','label':'Solicitante'},{'value':'Luis','label':'Supervisor'}]
    out=edit_properties(base,[],0,r['xref'],{'partial_name':'Rol','options':options});new=row(out,'Rol')
    assert new['value']=='Ana' and new['choices']==options and new['properties']['options']==options
    with f.open(stream=out) as d:
        assert d.xref_get_key(new['group'],'DV')==('string','Eva') and d.xref_get_key(new['group'],'I')[1]=='[1]'
    with f.open(stream=flatten_form(out,[])) as d:assert 'Solicitante' in d[0].get_text()
    changed=export_pdf(out,[{'type':'form_fill','page':0,'values':[{'page':0,'xref':new['xref'],'value':'Luis'}]}])
    assert row(changed,'Rol')['value']=='Luis'


@pytest.mark.parametrize('options',[
 [],[{'value':'Eva','label':'Eva'}],
 [{'value':'Ana','label':'A'},{'value':'Ana','label':'B'}],
 [{'value':'','label':'Vacia'}],[{'value':'Ana','label':'😀'}],
 [{'value':'Ana','label':'A\nB'}],[{'value':'Ana','label':' '}],
 [{'value':'Ana','label':'A','extra':1}],['Ana'],
])
def test_invalid_or_destructive_options_are_rejected(options):
    base=simple('choice');r=row(base)
    with pytest.raises(DocumentError):edit_properties(base,[],0,r['xref'],{'options':options})


def test_reset_value_cannot_be_removed_even_when_it_is_not_current_value():
    with f.open(stream=simple('choice')) as d:
        r=row(d.tobytes());d.xref_set_key(r['group'],'DV','(Eva)');base=d.tobytes()
    with pytest.raises(DocumentError,match='restablecimiento'):edit_properties(base,[],0,row(base)['xref'],{'options':[{'value':'Ana','label':'Ana'}]})


def test_actions_elsewhere_in_form_protect_against_breaking_name_references(tmp_path):
    path=tmp_path/'shared.pdf';create(path)
    with f.open(path) as d:
        rows=form_model(d)['fields'];selected=next(v for v in rows if v['name']=='Datos.Nombre');other=next(v for v in rows if v['group']!=selected['group'])
        d.xref_set_key(other['group'],'AA','<</K<</S/JavaScript/JS(this.getField(\\(Datos.Nombre\\)))>>>>');base=d.tobytes()
    r=row(base,'Datos.Nombre')
    with pytest.raises(DocumentError,match='acciones'):edit_properties(base,[],r['page'],r['xref'],{'partial_name':'Nuevo'})


def test_options_on_text_are_rejected_and_readonly_choices_can_be_edited():
    base=simple();r=row(base)
    with pytest.raises(DocumentError):edit_properties(base,[],0,r['xref'],{'options':[{'value':'Ana','label':'A'}]})
    base=simple('choice');r=row(base);locked=edit_properties(base,[],0,r['xref'],{'readonly':True});r=row(locked)
    out=edit_properties(locked,[],0,r['xref'],{'options':[{'value':'Ana','label':'Solicitante'},{'value':'Eva','label':'Evaluadora'}]})
    assert row(out)['value']=='Ana' and row(out)['properties']['readonly']


@pytest.mark.parametrize('protection',['script','advanced_flags','font'])
def test_own_readonly_cannot_hide_other_restrictions(protection):
    with f.open(stream=simple()) as d:
        r=row(d.tobytes());owner=r['group']
        d.xref_set_key(owner,'Ff','1')
        if protection=='script':d.xref_set_key(owner,'AA','<</K<</S/JavaScript/JS(test)>>>>')
        elif protection=='advanced_flags':d.xref_set_key(owner,'Ff',str(1|8192))
        else:d.xref_set_key(owner,'DA','(/unknown 12 Tf 0 g)')
        base=d.tobytes()
    r=row(base);assert not r['can_design']
    with pytest.raises(DocumentError):edit_properties(base,[],0,r['xref'],{'readonly':False})


def test_listbox_reordering_retains_selected_export_value_and_display_labels():
    with f.open(stream=simple('choice')) as d:
        r=row(d.tobytes());d.xref_set_key(r['group'],'Ff','0');base=d.tobytes()
    r=row(base);options=[{'value':'Eva','label':'Evaluadora'},{'value':'Ana','label':'Solicitante'}]
    out=edit_properties(base,[],0,r['xref'],{'options':options});new=row(out)
    assert new['value']=='Ana' and new['choices']==options
    with f.open(stream=out) as d:
        p=d[0];w=p.load_widget(new['xref']);assert w.field_type==f.PDF_WIDGET_TYPE_LISTBOX
        assert d.xref_get_key(new['group'],'I')[1]=='[1]'
    with f.open(stream=flatten_form(out,[])) as d:assert 'Solicitante' in d[0].get_text()
