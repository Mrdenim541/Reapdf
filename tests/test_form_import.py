"""Imports must preserve native groups and appearance while keeping copies independent."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError, export_pdf
from backend.merge import merge_pdf
from backend.page_creation import duplicate_pdf
from backend.forms import form_model
from backend.form_structure import field_structure, pdf_string
from backend.form_fields import select_pages
from backend.form_data import flatten_form, export_form_data, import_form_data
from backend.form_design import delete_field
from backend.projects import build_project, read_project
from scripts.create_advanced_form_sample import create


def rows(data):
    with f.open(stream=data) as d:return form_model(d)['fields']


def change(data,name,value):
    r=next(r for r in rows(data) if r['name']==name)
    return {'type':'form_fill','page':0,'values':[{'page':r['page'],'xref':r['xref'],'value':value}]}


def filled(data,text='Original',radio='opcion_3'):
    a=change(data,'Datos.Nombre',text);a['values']+=change(data,'Datos.Decision',radio)['values']
    return export_pdf(data,[a])


@pytest.fixture
def source(tmp_path):
    p=tmp_path/'advanced.pdf';create(p);return filled(p.read_bytes())


def assert_values(data,name,value):
    selected=[r for r in rows(data) if r['name']==name];assert selected and all(r['value']==value for r in selected)


@pytest.mark.parametrize('position',[0,1,2])
@pytest.mark.parametrize('pages',[[0,1],[1,0],[0],[1]])
def test_merge_keeps_source_pixels_groups_values_and_originals(source,position,pages):
    incoming=filled(source,'Importado','opcion_2');hashes=[hashlib.sha256(b).hexdigest() for b in [source,incoming]]
    out=merge_pdf(source,[],incoming,pages,position)
    assert len(rows(out))==5+sum(3 if p==0 else 2 for p in pages) and all(r['editable'] for r in rows(out))
    assert_values(out,'Datos.Nombre','Original');assert_values(out,'Datos (2).Nombre','Importado')
    assert_values(out,'Datos.Decision','opcion_3');assert_values(out,'Datos (2).Decision','opcion_2' if 0 in pages else '')
    with f.open(stream=source) as a,f.open(stream=incoming) as b,f.open(stream=out) as c:
        expected=[a[i].get_pixmap().samples for i in range(2)];expected[position:position]=[b[i].get_pixmap().samples for i in pages]
        assert [p.get_pixmap().samples for p in c]==expected
        assert not field_structure(c)[3]
    assert [hashlib.sha256(b).hexdigest() for b in [source,incoming]]==hashes


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_imported_fields_keep_geometry_and_can_be_filled_after_rotate_crop(source,rotation,crop):
    with f.open(stream=source) as d:
        for p in d:
            if crop:p.set_cropbox(f.Rect(20,20,570,820))
            p.set_rotation(rotation)
        incoming=d.tobytes()
    out=merge_pdf(source,[],incoming,[1,0],2)
    with f.open(stream=incoming) as a,f.open(stream=out) as b:
        for old,new in [(1,2),(0,3)]:
            assert b[new].rotation==rotation and b[new].cropbox==a[old].cropbox
            assert b[new].get_pixmap().samples==a[old].get_pixmap().samples
            assert [w.rect for w in b[new].widgets()]==[w.rect for w in a[old].widgets()]
    out=export_pdf(out,[change(out,'Datos (2).Nombre','Solo copia')]);assert_values(out,'Datos.Nombre','Original');assert_values(out,'Datos (2).Nombre','Solo copia')


def test_independent_shared_text_and_radio_survive_projects_data_flatten_and_delete(source):
    out=duplicate_pdf(source,[],[0,1],2)
    a=change(out,'Datos (2).Nombre','Solo copia');a['values']+=change(out,'Datos (2).Decision','opcion_1')['values'];operations=[a]
    edited=export_pdf(out,operations);assert_values(edited,'Datos.Nombre','Original');assert_values(edited,'Datos.Decision','opcion_3')
    assert_values(edited,'Datos (2).Nombre','Solo copia');assert_values(edited,'Datos (2).Decision','opcion_1')
    project,_=build_project(out,operations,{'name':'imported.pdf','page':3,'zoom':1,'base_changes':1});base,ops,_=read_project(project)
    assert rows(export_pdf(base,ops))==rows(edited)
    # Data round trips operate on the combined document and preserve group identity.
    data=export_form_data(out,operations);restored=export_pdf(out,import_form_data(out,[],data));assert [r['value'] for r in rows(restored)]==[r['value'] for r in rows(edited)]
    flat=flatten_form(out,operations)
    with f.open(stream=edited) as a,f.open(stream=flat) as b:
        assert all(not list(p.widgets() or []) for p in b)
        assert all(p.get_pixmap().samples==q.get_pixmap().samples for p,q in zip(a,b))
    r=next(r for r in rows(edited) if r['name']=='Datos (2).Nombre');removed=delete_field(edited,[],r['page'],r['xref'])
    assert_values(removed,'Datos.Nombre','Original');assert not any(r['name']=='Datos (2).Nombre' for r in rows(removed))


@pytest.mark.parametrize('position,count',[(0,1),(0,2),(1,1)])
def test_replace_base_pages_prunes_groups_without_changing_imported_values(source,position,count):
    incoming=filled(source,'Nuevo','opcion_1');out=merge_pdf(source,[],incoming,[0,1],position,replace_count=count)
    assert all(r['editable'] for r in rows(out));assert_values(out,'Datos (2).Nombre','Nuevo');assert_values(out,'Datos (2).Decision','opcion_1')
    if count==2:assert not any(r['name']=='Datos.Nombre' for r in rows(out))
    else:
        assert_values(out,'Datos.Nombre','Original');assert_values(out,'Datos.Decision','opcion_3' if position==0 else '')


def test_repeated_duplicates_get_predictable_names_without_accidental_sync(source):
    first=duplicate_pdf(source,[],[0,1],2);second=duplicate_pdf(first,[],[0,1],4)
    assert {r['name'] for r in rows(second)}=={f'{root}.{name}' for root in ['Datos','Datos (2)','Datos (3)'] for name in ['Nombre','Decision']}
    second=export_pdf(second,[change(second,'Datos (3).Nombre','Tercero')]);assert_values(second,'Datos.Nombre','Original');assert_values(second,'Datos (2).Nombre','Original');assert_values(second,'Datos (3).Nombre','Tercero')


def test_colliding_dotted_names_and_unicode_root_names_are_escaped_correctly(source):
    with f.open(stream=source) as d:
        root=field_structure(d)[1][next(iter(field_structure(d)[1]))]['chain'][0]
        d.xref_set_key(root,'T',pdf_string('Datos ñ/(A)'));unicode=d.tobytes()
    out=merge_pdf(unicode,[],unicode,[0,1],2);assert_values(out,'Datos ñ/(A) (2).Nombre','Original')
    with f.open() as d:
        p=d.new_page();w=f.Widget();w.field_name='Datos.Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,50,200,80);p.add_widget(w);flat=d.tobytes()
    out=merge_pdf(flat,[],source,[0,1],1);assert_values(out,'Datos (2).Nombre','Original')


def test_source_global_default_appearance_does_not_inherit_target_default(source):
    with f.open(stream=source) as d:
        for node in {n for row in field_structure(d)[1].values() for n in row['chain']}:
            if d.xref_get_key(node,'FT')[1]=='/Tx':d.xref_set_key(node,'DA','null')
        d.xref_set_key(d.pdf_catalog(),'AcroForm/DA',pdf_string('/Helv 12 Tf 0 g'));d.xref_set_key(d.pdf_catalog(),'AcroForm/Q','2');incoming=d.tobytes()
    with f.open(stream=source) as d:
        d.xref_set_key(d.pdf_catalog(),'AcroForm/DA',pdf_string('/Cour 17 Tf 1 0 0 rg'));base=d.tobytes()
    out=merge_pdf(base,[],incoming,[0,1],2);assert all(r['editable'] for r in rows(out))
    with f.open(stream=out) as d:
        fields=field_structure(d)[1];r=next(row for row in fields.values() if row['name']=='Datos (2).Nombre')
        assert d.xref_get_key(r['chain'][0],'DA')[1]=='/Helv 12 Tf 0 g' and d.xref_get_key(r['chain'][0],'Q')[1]=='2'


@pytest.mark.parametrize('key',['AA','A','OC'])
def test_ancestor_actions_are_rejected_before_native_copy(source,key):
    with f.open(stream=source) as d:
        d.xref_set_key(next(iter(field_structure(d)[2])),key,'<</S/JavaScript/JS(test)>>');bad=d.tobytes()
    with pytest.raises(DocumentError,match='scripts'):merge_pdf(source,[],bad,[0],2)


def test_cycles_and_missing_parent_are_rejected_without_changing_sources(source):
    for key,value in [('Parent','21 0 R'),('Kids','[]')]:
        with f.open(stream=source) as d:
            root=next(iter(field_structure(d)[1].values()))['chain'][0];d.xref_set_key(root,key,value);bad=d.tobytes()
        with pytest.raises(DocumentError):merge_pdf(source,[],bad,[0],2)


@pytest.mark.parametrize('corruption',['value','appearance','base','missing'])
def test_corrupt_native_copy_is_rejected_atomically(source,monkeypatch,corruption):
    original=f.Document.insert_pdf
    def corrupt(doc,incoming,*args,**kwargs):
        original(doc,incoming,*args,**kwargs);p=doc[kwargs['start_at']];xref=next(x for x,k,_ in p.annot_xrefs() if k==f.PDF_ANNOT_WIDGET)
        if corruption=='value':doc.xref_set_key(xref,'V','(Incorrecto)')
        elif corruption=='appearance':doc.xref_set_key(xref,'AP','null')
        elif corruption=='base':doc.xref_set_key(22,'V','(Alterado)')
        else:doc.xref_set_key(p.xref,'Annots','[]')
    monkeypatch.setattr(f.Document,'insert_pdf',corrupt)
    with pytest.raises(DocumentError):merge_pdf(source,[],source,[0,1],2)
    assert_values(source,'Datos.Nombre','Original')


def test_copy_requires_copy_permission_and_preserves_destination_encryption(source):
    with f.open(stream=source) as d:
        denied=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner-pass',user_pw='',permissions=f.PDF_PERM_PRINT)
        base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,owner_pw='owner-pass',user_pw='',permissions=f.PDF_PERM_ASSEMBLE|f.PDF_PERM_FORM)
    with pytest.raises(DocumentError,match='copiar'):merge_pdf(source,[],denied,[0],2)
    out=merge_pdf(base,[],source,[0,1],2)
    with f.open(stream=out) as d:assert d.metadata['encryption'] and not d.permissions&f.PDF_PERM_COPY


def test_api_import_duplicate_and_replace_remain_separate_versions(source,tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    with TestClient(app) as c:
        a=c.post('/api/documents',files={'file':('base.pdf',source)}).json();b=c.post('/api/documents',files={'file':('source.pdf',filled(source,'Otro'))}).json()
        body={'operations':[],'source_id':b['id'],'pages':[0,1],'position':2,'source_name':'Formulario'}
        for action,payload in [('insert',body),('duplicate',{'operations':[],'pages':[0,1],'position':2}),('replace',{**body,'position':0,'replace_count':1})]:
            r=c.post(f"/api/documents/{a['id']}/{action}",json=payload);assert r.status_code==200,r.text
            assert r.json()['id']!=a['id'];model=c.post(f"/api/documents/{r.json()['id']}/forms",json={}).json()['fields'];assert all(row['editable'] for row in model)
        old=c.post(f"/api/documents/{a['id']}/forms",json={}).json()['fields'];assert len(old)==5 and all(r['name'].startswith('Datos.') for r in old)


def test_poppler_render_and_text_match_before_and_after_import(source,tmp_path):
    if not shutil.which('pdftoppm') or not shutil.which('pdftotext'):pytest.skip('Poppler no disponible')
    out=merge_pdf(source,[],source,[0,1],2)
    for name,data,page in [('source',source,1),('imported',out,3)]:
        path=tmp_path/(name+'.pdf');path.write_bytes(data);prefix=tmp_path/name
        subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r','72','-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True)
        text=subprocess.run(['pdftotext','-f',str(page),'-l',str(page),str(path),'-'],check=True,capture_output=True,text=True).stdout
        assert 'Original' in text
    assert f.Pixmap(str(tmp_path/'source.png')).samples==f.Pixmap(str(tmp_path/'imported.png')).samples


def test_deeper_ancestors_remain_logical_and_independent(source):
    with f.open(stream=source) as d:
        root=next(iter(field_structure(d)[1].values()))['chain'][0];top=d.get_new_xref()
        d.update_object(top,f'<</T(Cliente)/Kids[{root} 0 R]>>');d.xref_set_key(root,'Parent',f'{top} 0 R');d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{top} 0 R]');deep=d.tobytes()
    out=merge_pdf(deep,[],deep,[0,1],2);assert_values(out,'Cliente (2).Datos.Nombre','Original');assert all(r['editable'] for r in rows(out))
    out=export_pdf(out,[change(out,'Cliente (2).Datos.Nombre','Copia')]);assert_values(out,'Cliente.Datos.Nombre','Original')


def test_readonly_fields_can_be_copied_without_becoming_editable(source):
    with f.open(stream=source) as d:
        name=next(r for r in form_model(d)['fields'] if r['name']=='Datos.Nombre');d.xref_set_key(name['group'],'Ff','1');readonly=d.tobytes()
    out=merge_pdf(source,[],readonly,[0,1],2)
    copies=[r for r in rows(out) if r['name']=='Datos (2).Nombre'];assert copies and all(not r['editable'] and 'solo lectura' in r['reason'] for r in copies)


@pytest.mark.parametrize('key,value',[('DA','42'),('Q','4')])
def test_invalid_global_form_defaults_are_rejected(source,key,value):
    with f.open(stream=source) as d:d.xref_set_key(d.pdf_catalog(),'AcroForm/'+key,value);bad=d.tobytes()
    with pytest.raises(DocumentError,match='predeterminados'):merge_pdf(source,[],bad,[0],2)


def test_empty_root_names_are_rejected(source):
    with f.open(stream=source) as d:
        root=next(iter(field_structure(d)[1].values()))['chain'][0];d.xref_set_key(root,'T','()');bad=d.tobytes()
    with pytest.raises(DocumentError,match='no vacíos'):merge_pdf(source,[],bad,[0],2)


def test_final_field_limit_allows_replacement_but_rejects_overflow():
    with f.open() as d:
        p=d.new_page()
        for i in range(251):
            w=f.Widget();w.field_name=f'Campo {i}';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,50,180,75);p.add_widget(w)
        source=d.tobytes()
    with pytest.raises(DocumentError,match='500 campos'):merge_pdf(source,[],source,[0],1)
    out=merge_pdf(source,[],source,[0],0,replace_count=1);assert len(rows(out))==251 and all(r['editable'] for r in rows(out))


def test_document_with_multiple_imported_trees_can_be_imported_again(source):
    combined=duplicate_pdf(source,[],[0,1],2)
    with f.open() as d:d.new_page();plain=d.tobytes()
    out=merge_pdf(plain,[],combined,[0,1,2,3],1)
    assert len(rows(out))==10 and all(r['editable'] for r in rows(out));assert_values(out,'Datos.Nombre','Original');assert_values(out,'Datos (2).Nombre','Original')


def test_shared_checkboxes_keep_one_value_per_tree(source):
    with f.open(stream=source) as d:
        radio=[r for r in form_model(d)['fields'] if r['kind']=='radio'];d.xref_set_key(radio[0]['group'],'Ff','0');d.xref_set_key(radio[0]['group'],'V','/Off')
        for r in radio:
            off=d.xref_get_key(r['xref'],'AP/N/Off')[1];on=d.xref_get_key(r['xref'],'AP/N/'+r['radio_state'])[1];d.xref_set_key(r['xref'],'AP/N',f'<</Off {off}/Yes {on}>>');d.xref_set_key(r['xref'],'AS','/Off')
        base=d.tobytes()
    base=export_pdf(base,[change(base,'Datos.Decision',True)]);out=duplicate_pdf(base,[],[0,1],2)
    out=export_pdf(out,[change(out,'Datos (2).Decision',False)]);assert_values(out,'Datos.Decision',True);assert_values(out,'Datos (2).Decision',False)


def test_duplicate_uses_current_applied_values_for_both_original_and_copy(source):
    operation=change(source,'Datos.Nombre','Corregido');out=duplicate_pdf(source,[operation],[0,1],2)
    assert_values(out,'Datos.Nombre','Corregido');assert_values(out,'Datos (2).Nombre','Corregido')


def test_mixed_named_widgets_and_shared_groups_keep_their_common_ancestor(source):
    with f.open(stream=source) as d:
        root=next(iter(field_structure(d)[1].values()))['chain'][0];p=d[0];w=f.Widget();w.field_name='Ciudad';w.field_type=f.PDF_WIDGET_TYPE_COMBOBOX;w.text_fontsize=12;w.choice_values=[('BOG','Bogotá'),('LIM','Lima')];w.rect=f.Rect(45,400,350,435);xref=p.add_widget(w).xref
        children=d.xref_get_key(root,'Kids')[1];d.xref_set_key(root,'Kids',children[:-1]+f' {xref} 0 R]');d.xref_set_key(xref,'Parent',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{root} 0 R]');base=d.tobytes()
    base=export_pdf(base,[change(base,'Datos.Ciudad','BOG')]);out=duplicate_pdf(base,[],[0,1],2)
    assert all(r['editable'] for r in rows(out));assert_values(out,'Datos (2).Ciudad','BOG')
    out=export_pdf(out,[change(out,'Datos (2).Ciudad','LIM')]);assert_values(out,'Datos.Ciudad','BOG');assert_values(out,'Datos (2).Ciudad','LIM')


@pytest.mark.parametrize('base_indirect',[False,True])
@pytest.mark.parametrize('source_indirect',[False,True])
def test_indirect_acroforms_keep_real_fields_instead_of_nested_setter_placeholder(source,base_indirect,source_indirect):
    def indirect(data,enabled):
        if not enabled:return data
        with f.open(stream=data) as d:
            obj=d.get_new_xref();d.update_object(obj,d.xref_get_key(d.pdf_catalog(),'AcroForm')[1]);d.xref_set_key(d.pdf_catalog(),'AcroForm',f'{obj} 0 R');return d.tobytes()
    base=indirect(source,base_indirect);incoming=indirect(source,source_indirect);out=merge_pdf(base,[],incoming,[0,1],2)
    assert all(r['editable'] for r in rows(out)) and len(rows(out))==10
    from backend.form_design import create_field
    out=create_field(out,[],{'name':'Nuevo','kind':'radio','page':0,'box':[45,450,350,70],'options':['Sí','No']})
    assert len(rows(out))==12 and all(r['editable'] for r in rows(out))
    chosen=next(r for r in rows(out) if r['name']=='Nuevo');out=delete_field(out,[],chosen['page'],chosen['xref'])
    assert len(rows(out))==10 and all(r['editable'] for r in rows(out))


def test_large_shared_values_are_rejected_before_building_a_large_copy(source):
    with f.open(stream=source) as d:
        group=next(r['group'] for r in form_model(d)['fields'] if r['name']=='Datos.Nombre');d.xref_set_key(group,'V',pdf_string('a'*2001));large=d.tobytes()
    with pytest.raises(DocumentError,match='2000 caracteres'):merge_pdf(source,[],large,[0,1],2)


def test_total_form_data_budget_is_explicit_and_atomic(source,monkeypatch):
    import backend.form_import as module
    monkeypatch.setattr(module,'MAX_SIGNATURE_CHARS',10)
    with pytest.raises(DocumentError,match='datos de formulario'):merge_pdf(source,[],source,[0,1],2)
    assert_values(source,'Datos.Nombre','Original')
