from copy import deepcopy
from pathlib import Path
from io import BytesIO
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from scripts.create_advanced_form_sample import create
from backend.app import app
from backend.engine import DocumentError,export_pdf
from backend.forms import form_model
from backend.form_structure import field_structure
from backend.form_data import export_form_data,import_form_data,flatten_form
from backend.form_design import create_field,delete_field
from backend.projects import build_project,read_project
from backend.pages import organize_pdf


@pytest.fixture
def source(tmp_path):
    path=tmp_path/'groups.pdf';create(path);return path.read_bytes()


def model(data):
    with f.open(stream=data) as d:return form_model(d)['fields']


def op(data,name,value):
    row=next(r for r in model(data) if r['name']==name)
    return {'type':'form_fill','page':0,'values':[{'page':row['page'],'xref':row['xref'],'value':value}]}


def fill(data,text='María Pérez',radio='opcion_3'):
    a=op(data,'Datos.Nombre',text);b=op(data,'Datos.Decision',radio)
    return export_pdf(data,[{**a,'values':a['values']+b['values']}])


def test_real_tree_uses_ownership_instead_of_equal_names(source):
    rows=model(source);assert len(rows)==5 and all(r['editable'] for r in rows)
    assert [r['group_size'] for r in rows]==[2,3,3,2,3]
    assert [r['kind'] for r in rows]==['text','radio','radio','text','radio']
    with f.open(stream=source) as d:
        _,structure,groups,reason=field_structure(d);assert not reason and len(groups)==2
        assert all(len(r['chain'])==3 for r in structure.values())


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_shared_text_and_radio_survive_export_with_native_values_and_geometry(source,rotation,crop,tmp_path):
    with f.open(stream=source) as d:
        for p in d:
            if crop:p.set_cropbox(f.Rect(20,20,570,820))
            p.set_rotation(rotation)
        base=d.tobytes()
    out=fill(base)
    rows=model(out);assert all(r['editable'] for r in rows)
    assert [r['value'] for r in rows]==['María Pérez','opcion_3','opcion_3','María Pérez','opcion_3']
    with f.open(stream=out) as d,f.open(stream=base) as original:
        _,structure,groups,reason=field_structure(d);assert not reason
        radio=next(r for r in rows if r['kind']=='radio');assert d.xref_get_key(radio['group'],'V')==('name','/opcion_3')
        assert sum(d.xref_get_key(r['xref'],'AS')[1]!='/Off' for r in rows if r['kind']=='radio')==1
        for p,q in zip(d,original):
            assert p.rotation==rotation and 'María Pérez' in p.get_text() and not p.get_images()
            assert [w.rect for w in p.widgets()]==[w.rect for w in q.widgets()]
        for row in rows:
            assert d.xref_get_key(row['xref'],'T')[0]=='null'
            assert d.xref_get_key(row['xref'],'V')[0]=='null'
        if shutil.which('pdftotext'):
            target=tmp_path/'filled.pdf';target.write_bytes(out);text=subprocess.check_output(['pdftotext',str(target),'-']).decode();assert text.count('María Pérez')==2


def test_radio_switches_and_clears_exclusively_without_regenerating_appearances(source):
    initial=source
    for value in ['opcion_1','opcion_3','opcion_2','']:
        out=export_pdf(initial,[op(initial,'Datos.Decision',value)])
        with f.open(stream=initial) as a,f.open(stream=out) as b:
            old=[p.get_pixmap().samples for p in a];new=[p.get_pixmap().samples for p in b]
            assert old!=new or not value
            radio=[r for r in model(out) if r['kind']=='radio'];assert all(r['value']==value and r['editable'] for r in radio)
            for r in radio:
                assert b.xref_get_key(r['xref'],'AS')[1]=='/'+(r['radio_state'] if r['radio_state']==value else 'Off')
            # AP stream bytes are unchanged; switching chooses existing states.
            old_streams=sorted(a.xref_stream(x) for p in a for w in p.widgets() if w.field_type==5 for key in ['Off','opcion_1','opcion_2','opcion_3'] if (v:=a.xref_get_key(w.xref,'AP/N/'+key))[0]=='xref' for x in [int(v[1].split()[0])])
            new_streams=sorted(b.xref_stream(x) for p in b for w in p.widgets() if w.field_type==5 for key in ['Off','opcion_1','opcion_2','opcion_3'] if (v:=b.xref_get_key(w.xref,'AP/N/'+key))[0]=='xref' for x in [int(v[1].split()[0])])
            assert old_streams==new_streams
        initial=out


def test_shared_text_clear_cannot_leave_old_values_or_child_overrides(source):
    out=fill(source);cleared=export_pdf(out,[op(out,'Datos.Nombre','')])
    assert all(r['value']=='' for r in model(cleared) if r['kind']=='text')
    with f.open(stream=cleared) as d:assert all('María Pérez' not in p.get_text() for p in d)


def test_conflicting_group_entries_fail_atomically(source):
    rows=[r for r in model(source) if r['kind']=='radio']
    values=[{'page':r['page'],'xref':r['xref'],'value':'opcion_'+str(i+1)} for i,r in enumerate(rows)]
    with pytest.raises(DocumentError,match='contradictorios'):export_pdf(source,[{'type':'form_fill','page':0,'values':values}])
    assert all(r['value']=='' for r in model(source))


@pytest.mark.parametrize('value',['unknown',True,None,1,[],{}])
def test_invalid_radio_values(source,value):
    with pytest.raises(DocumentError):export_pdf(source,[op(source,'Datos.Decision',value)])


@pytest.mark.parametrize('mutation',['parent_script','parent_readonly','child_locked','inconsistent_as','duplicate_on','wrong_parent','wrong_page','mixed_type','child_value'])
def test_unsafe_groups_protect_every_member(source,mutation):
    rows=model(source);radio=next(r for r in rows if r['kind']=='radio');owner=radio['group']
    with f.open(stream=source) as d:
        if mutation=='parent_script':d.xref_set_key(owner,'AA','<</V<</S/JavaScript/JS(app.alert(1))>>>>')
        elif mutation=='parent_readonly':d.xref_set_key(owner,'Ff',str(32768|1))
        elif mutation=='child_locked':d.xref_set_key(radio['xref'],'Ff','32769')
        elif mutation=='inconsistent_as':d.xref_set_key(radio['xref'],'AS','/opcion_1')
        elif mutation=='duplicate_on':
            other=[r for r in rows if r['kind']=='radio'][1];d.xref_set_key(other['xref'],'AP/N',d.xref_get_key(radio['xref'],'AP/N')[1])
        elif mutation=='wrong_parent':d.xref_set_key(radio['xref'],'Parent',f"{next(r for r in rows if r['kind']=='text')['group']} 0 R")
        elif mutation=='wrong_page':d.xref_set_key(radio['xref'],'P',f'{d[1].xref} 0 R')
        elif mutation=='mixed_type':d.xref_set_key(radio['xref'],'FT','/Tx')
        else:d.xref_set_key(radio['xref'],'V','/opcion_2')
        data=d.tobytes()
    affected=[r for r in model(data) if r['name']=='Datos.Decision']
    assert affected and all(not r['editable'] for r in affected)
    with pytest.raises(DocumentError):export_pdf(data,[op(data,'Datos.Decision','opcion_3')])


def test_no_toggle_to_off_is_honored(source):
    with f.open(stream=fill(source)) as d:
        r=next(r for r in model(fill(source)) if r['kind']=='radio');d.xref_set_key(r['group'],'Ff',str(32768|16384));base=d.tobytes()
    with pytest.raises(DocumentError,match='retirar'):export_pdf(base,[op(base,'Datos.Decision','')])
    assert all(r['value']=='opcion_1' for r in model(export_pdf(base,[op(base,'Datos.Decision','opcion_1')])) if r['kind']=='radio')


def test_group_data_roundtrip_partial_import_and_conflicts(source):
    operations=[{**op(source,'Datos.Nombre','Ana'),'values':op(source,'Datos.Nombre','Ana')['values']+op(source,'Datos.Decision','opcion_2')['values']}]
    data=export_form_data(source,operations);assert len(data['fields'])==5
    assert [r['value'] for r in data['fields']]==['Ana','opcion_2','opcion_2','Ana','opcion_2']
    imported=import_form_data(source,[],data);assert export_form_data(source,imported)==data
    partial=deepcopy(data);partial['fields']=[partial['fields'][-1]];partial['fields'][0]['value']='opcion_3'
    changed=import_form_data(source,imported,partial);assert all(r['value']=='opcion_3' for r in export_form_data(source,changed)['fields'] if r['kind']=='radio')
    data['fields'][1]['value']='opcion_1'
    with pytest.raises(DocumentError,match='contradictorios'):import_form_data(source,[],data)


def test_group_project_flatten_and_organization(source):
    operations=[{**op(source,'Datos.Nombre','Ana'),'values':op(source,'Datos.Nombre','Ana')['values']+op(source,'Datos.Decision','opcion_3')['values']}]
    project,_=build_project(source,operations,{'name':'advanced.pdf','page':1,'zoom':1,'base_changes':0});base,ops,_=read_project(project);assert base==source and ops==operations
    flat=flatten_form(base,ops)
    with f.open(stream=export_pdf(base,ops)) as a,f.open(stream=flat) as b:
        assert all(not list(p.widgets() or []) for p in b)
        assert all(p.get_pixmap().samples==q.get_pixmap().samples for p,q in zip(a,b))
    organized=organize_pdf(base,ops,[{'page':1,'rotation':90},{'page':0,'rotation':0}]);assert all(r['editable'] for r in model(organized))
    out=export_pdf(organized,[op(organized,'Datos.Decision','opcion_2')]);assert all(r['value']=='opcion_2' for r in model(out) if r['kind']=='radio')


@pytest.mark.parametrize('keep,expected',[(0,''),(1,'opcion_3')])
def test_extracting_pages_prunes_group_and_clears_only_lost_radio_selection(source,keep,expected):
    edited=fill(source);result=organize_pdf(edited,[],[{'page':keep,'rotation':0}],extract=True);rows=model(result)
    assert all(r['editable'] for r in rows)
    assert all(r['value']==expected for r in rows if r['kind']=='radio')
    assert next(r for r in rows if r['kind']=='text')['value']=='María Pérez'


@pytest.mark.parametrize('name',['Datos.Nombre','Datos.Decision'])
def test_delete_removes_whole_logical_field_across_pages_and_prunes_ancestors(source,name):
    row=next(r for r in model(source) if r['name']==name);result=delete_field(source,[],row['page'],row['xref'])
    rows=model(result);assert rows and all(r['name']!=name and r['editable'] for r in rows)
    remaining=rows[0];empty=delete_field(result,[],remaining['page'],remaining['xref']);assert not model(empty)
    with f.open(stream=empty) as d:assert 'Aprobar' in d[0].get_text()


def test_create_radio_field_and_delete_with_static_option_labels(source):
    result=create_field(source,[],{'name':'Nuevo','kind':'radio','page':0,'box':[50,450,300,100],'options':['Sí','No','Revisar']})
    rows=[r for r in model(result) if r['name']=='Nuevo'];assert len(rows)==3 and all(r['editable'] for r in rows)
    out=export_pdf(result,[op(result,'Nuevo','opcion_2')]);assert all(r['value']=='opcion_2' for r in model(out) if r['name']=='Nuevo')
    row=next(r for r in model(out) if r['name']=='Nuevo');removed=delete_field(out,[],row['page'],row['xref']);assert all(r['name']!='Nuevo' for r in model(removed))
    with f.open(stream=removed) as d:assert 'Sí' in d[0].get_text()


@pytest.mark.parametrize('options',[[],['One'],['A']*2,[[],[]],['A','✓'],['A','B']*6])
def test_invalid_radio_design_options_fail_before_modifying_document(source,options):
    with pytest.raises(DocumentError):create_field(source,[],{'name':'Nuevo','kind':'radio','page':0,'box':[50,450,300,100],'options':options})


def test_api_group_overlay_uses_all_members_and_preserves_original(source,tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    operation=op(source,'Datos.Decision','opcion_3')
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('groups.pdf',source)}).json();url='/api/documents/'+doc['id']
        response=c.post(url+'/forms',json={'operations':[operation]});assert response.status_code==200
        assert [r['value'] for r in response.json()['fields'] if r['kind']=='radio']==['opcion_3']*3
        assert all(not r['value'] for r in c.post(url+'/forms',json={}).json()['fields'])
        assert c.post(url+'/pages/1/preview',json={'operations':[operation]}).headers['content-type']=='image/png'


def test_shared_checkboxes_sync_and_uncheck_all_appearances(source):
    rows=model(source);radio=[r for r in rows if r['kind']=='radio'];owner=radio[0]['group']
    with f.open(stream=source) as d:
        d.xref_set_key(owner,'Ff','0')
        for r in radio:
            off=d.xref_get_key(r['xref'],'AP/N/Off')[1];on=d.xref_get_key(r['xref'],'AP/N/'+r['radio_state'])[1]
            d.xref_set_key(r['xref'],'AP/N',f'<</Off {off}/Yes {on}>>')
        base=d.tobytes()
    for value in [True,False]:
        base=export_pdf(base,[op(base,'Datos.Decision',value)]);items=[r for r in model(base) if r['kind']=='checkbox']
        assert len(items)==3 and all(r['editable'] and r['value']==value for r in items)
        with f.open(stream=base) as d:assert all(d.xref_get_key(r['xref'],'AS')[1]==('/Yes' if value else '/Off') for r in items)


def test_shared_field_validates_fit_in_every_widget_before_changing_any(source):
    rows=model(source);second=[r for r in rows if r['kind']=='text'][1]
    with f.open(stream=source) as d:
        p=d[second['page']];w=p.load_widget(second['xref']);w.rect=f.Rect(45,110,75,135);w.update();d.xref_set_key(w.xref,'V','null');base=d.tobytes()
    with pytest.raises(DocumentError,match='cabe|espacio'):export_pdf(base,[op(base,'Datos.Nombre','Un nombre que no cabe')])
    assert all(r['value']=='' for r in model(source) if r['kind']=='text')


def test_a_hierarchical_single_choice_preserves_export_value_label_and_parent(source):
    with f.open(stream=source) as d:
        p=d[0];w=f.Widget();w.field_name='Ciudad';w.field_type=f.PDF_WIDGET_TYPE_COMBOBOX;w.text_fontsize=12;w.choice_values=[('BOG','Bogotá'),('LIM','Lima')];w.rect=f.Rect(40,400,300,440)
        x=p.add_widget(w).xref;root=field_structure(d)[1][model(source)[0]['xref']]['chain'][0]
        kids=d.xref_get_key(root,'Kids')[1];d.xref_set_key(root,'Kids',kids[:-1]+f' {x} 0 R]');d.xref_set_key(x,'Parent',f'{root} 0 R')
        roots=d.xref_get_key(d.pdf_catalog(),'AcroForm/Fields')[1];d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{root} 0 R]');base=d.tobytes()
    out=export_pdf(base,[op(base,'Datos.Ciudad','BOG')]);row=next(r for r in model(out) if r['name']=='Datos.Ciudad');assert row['value']=='BOG' and row['editable']
    with f.open(stream=out) as d:assert 'Bogotá' in d[0].get_text()


@pytest.mark.parametrize('permissions',[f.PDF_PERM_FORM,f.PDF_PERM_PRINT])
def test_advanced_fields_preserve_encryption_and_form_permissions(source,permissions):
    with f.open(stream=source) as d:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner1234',user_pw='',permissions=permissions)
    if permissions==f.PDF_PERM_PRINT:
        with pytest.raises(DocumentError):fill(base)
    else:
        with f.open(stream=fill(base)) as d:
            assert d.permissions&f.PDF_PERM_FORM and not d.permissions&f.PDF_PERM_COPY and not d.permissions&f.PDF_PERM_PRINT
            assert 'AES' in d.metadata['encryption']


def test_poppler_renders_the_selected_radio_on_the_other_page(source,tmp_path):
    if not shutil.which('pdftoppm'):pytest.skip('Poppler no disponible')
    edited=export_pdf(source,[op(source,'Datos.Decision','opcion_3')]);images=[]
    for name,data in [('before',source),('after',edited),('flat',flatten_form(edited,[]))]:
        pdf=tmp_path/(name+'.pdf');pdf.write_bytes(data);prefix=tmp_path/name
        subprocess.run(['pdftoppm','-f','2','-l','2','-r','72','-singlefile','-png',str(pdf),str(prefix)],check=True,capture_output=True)
        images.append(f.Pixmap(str(prefix)+'.png'))
    def area(pix):return [pix.pixel(x,y) for y in range(225,244) for x in range(45,64)]
    assert area(images[0])!=area(images[1]) and area(images[1])==area(images[2])


def test_creation_rejects_container_name_collision(source):
    with pytest.raises(DocumentError,match='contenedor'):create_field(source,[],{'name':'Datos','kind':'text','page':0,'box':[45,450,300,50]})


def test_creation_blocks_xfa_even_when_document_has_no_widgets():
    with f.open() as d:
        d.new_page();d.xref_set_key(d.pdf_catalog(),'AcroForm','<</XFA(test)>>');data=d.tobytes()
    with pytest.raises(DocumentError,match='XFA'):create_field(data,[],{'name':'Nuevo','kind':'text','page':0,'box':[45,100,300,50]})


@pytest.mark.parametrize('duplicate',[False,True])
def test_advanced_source_copy_keeps_both_trees_editable(source,duplicate):
    from backend.merge import merge_pdf
    from backend.page_creation import duplicate_pdf
    result=duplicate_pdf(source,[],[0,1],2) if duplicate else merge_pdf(source,[],source,[0,1],2)
    assert len(model(result))==10 and all(r['editable'] for r in model(result))
    assert {r['name'] for r in model(result)}=={'Datos.Nombre','Datos.Decision','Datos (2).Nombre','Datos (2).Decision'}
    assert all(r['editable'] for r in model(source))


def test_inserting_plain_pdf_into_advanced_base_keeps_original_groups_editable(source):
    from backend.merge import merge_pdf
    with f.open() as d:d.new_page();plain=d.tobytes()
    result=merge_pdf(source,[],plain,[0],2);assert all(r['editable'] for r in model(result))
    result=fill(result);assert all(r['value']=='María Pérez' for r in model(result) if r['kind']=='text')
