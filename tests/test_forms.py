import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.forms import form_model
from backend.engine import export_pdf, DocumentError
from backend.projects import build_project,read_project
from backend.pages import organize_pdf


def source(rotation=0,crop=False):
    with f.open() as doc:
        p=doc.new_page(width=500,height=650);p.insert_text((40,50),'Original conservado')
        for i,(name,kind) in enumerate([('Nombre',f.PDF_WIDGET_TYPE_TEXT),('Acepto',f.PDF_WIDGET_TYPE_CHECKBOX),('Ciudad',f.PDF_WIDGET_TYPE_COMBOBOX),('Lista',f.PDF_WIDGET_TYPE_LISTBOX),('Notas',f.PDF_WIDGET_TYPE_TEXT)]):
            w=f.Widget();w.field_name=name;w.field_type=kind;w.rect=f.Rect(50,80+i*80,350,130+i*80)
            if kind in [f.PDF_WIDGET_TYPE_LISTBOX,f.PDF_WIDGET_TYPE_COMBOBOX]:w.choice_values=[('BOG','Bogotá'),('LIM','Lima')]
            if name=='Notas':w.field_flags=4096
            if name=='Nombre':w.text_maxlen=50
            p.add_widget(w)
        if crop:p.set_cropbox(f.Rect(20,20,480,630))
        p.set_rotation(rotation);doc.new_page().insert_text((40,50),'Otra pagina')
        return doc.tobytes()


def operation(data,**values):
    with f.open(stream=data) as doc:
        return {'type':'form_fill','page':0,'values':[{'page':r['page'],'xref':r['xref'],'value':values[r['name']]} for r in form_model(doc)['fields'] if r['name'] in values]}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_fields_remain_editable_with_values_and_appearances_on_rotated_cropped_pages(rotation,crop):
    data=source(rotation,crop);op=operation(data,Nombre='María Pérez',Acepto=True,Ciudad='BOG',Lista='LIM',Notas='Primera línea\nSegunda línea')
    with f.open(stream=export_pdf(data,[op])) as doc,f.open(stream=data) as original:
        p=doc[0];widgets={w.field_name:w for w in p.widgets()};assert len(widgets)==5
        assert widgets['Nombre'].field_value=='María Pérez' and widgets['Acepto'].field_value==widgets['Acepto'].on_state()
        assert widgets['Ciudad'].field_value=='BOG' and widgets['Lista'].field_value=='LIM'
        assert 'Bogotá' in p.get_textbox(widgets['Ciudad'].rect) and 'BOG' not in p.get_textbox(widgets['Ciudad'].rect)
        assert doc.xref_get_key(widgets['Lista'].xref,'I')[1]=='[1]'
        assert widgets['Notas'].field_value=='Primera línea\nSegunda línea'
        text=p.get_text();assert 'Original conservado' in text and 'María Pérez' in text and 'Primera línea' in text
        assert p.rotation==rotation and not p.get_images()
        assert p.get_pixmap().samples!=original[0].get_pixmap().samples
        assert doc[1].get_pixmap().samples==original[1].get_pixmap().samples
        assert all(doc.xref_get_key(w.xref,'AP/N')[0]!='null' for w in widgets.values())


def test_clear_values_and_uncheck_source_preserve_fields():
    data=source();filled=export_pdf(data,[operation(data,Nombre='Ana',Acepto=True,Ciudad='BOG',Lista='LIM')])
    with f.open(stream=export_pdf(filled,[operation(filled,Nombre='',Acepto=False,Ciudad='',Lista='')])) as doc:
        p=doc[0];widgets={w.field_name:w for w in p.widgets()}
        assert widgets['Nombre'].field_value=='' and widgets['Acepto'].field_value=='Off'
        assert widgets['Ciudad'].field_value=='' and widgets['Lista'].field_value=='' and 'Ana' not in p.get_text()


@pytest.mark.parametrize('name,value',[('Nombre','x'*51),('Nombre','a\nb'),('Nombre','✓'),('Nombre','a\tb'),('Nombre',False),('Acepto','Yes'),('Acepto',1),('Ciudad','UNKNOWN'),('Lista',['BOG']),('Notas','x'*2001)])
def test_invalid_values_fail_before_source_changes(name,value):
    data=source()
    with pytest.raises(DocumentError):export_pdf(data,[operation(data,**{name:value})])
    with f.open(stream=data) as doc:assert all(r['value'] in ['',False] for r in form_model(doc)['fields'])


@pytest.mark.parametrize('values',[[],None,[{}],[{'page':True,'xref':5,'value':'A'}],[{'page':0,'xref':999,'value':'A'}]])
def test_invalid_field_identity_and_config(values):
    with pytest.raises(DocumentError):export_pdf(source(),[{'type':'form_fill','page':0,'values':values}])


def test_duplicate_field_values_and_multiple_configs_are_rejected():
    data=source();op=operation(data,Nombre='Ana')
    with pytest.raises(DocumentError):export_pdf(data,[{**op,'values':op['values']*2}])
    with pytest.raises(DocumentError):export_pdf(data,[op,op])


@pytest.mark.parametrize('option',['readonly','password','rich','parent','shared','script','calc','xfa','font','radio'])
def test_unsupported_fields_are_identified_and_rejected(option):
    with f.open(stream=source()) as doc:
        page=doc[0];w=next(page.widgets())
        if option in ['readonly','password','rich']:
            w.field_flags={'readonly':1,'password':8192,'rich':33554432}[option];w.update()
        if option=='parent':
            parent=doc.get_new_xref();doc.update_object(parent,f'<</T(Root)/Kids[{w.xref} 0 R]>>');doc.xref_set_key(w.xref,'Parent',f'{parent} 0 R')
        if option=='shared':
            other=f.Widget();other.field_name=w.field_name;other.field_type=f.PDF_WIDGET_TYPE_TEXT;other.rect=f.Rect(30,500,200,540);page.add_widget(other)
        if option=='script':doc.xref_set_key(w.xref,'AA','<</K<</S/JavaScript/JS(app.alert(1))>>>>')
        if option=='calc':doc.xref_set_key(doc.pdf_catalog(),'AcroForm/CO',f'[{w.xref} 0 R]')
        if option=='xfa':doc.xref_set_key(doc.pdf_catalog(),'AcroForm/XFA','(test)')
        if option=='font':doc.xref_set_key(w.xref,'DA','(/NonBase 12 Tf 0 g)')
        if option=='radio':doc.xref_set_key(w.xref,'FT','/Btn');doc.xref_set_key(w.xref,'Ff',str(1<<15))
        data=doc.tobytes();row=form_model(doc)['fields'][0];assert not row['editable'] and row['reason']
        op={'type':'form_fill','page':0,'values':[{'page':0,'xref':row['xref'],'value':'A'}]}
    with pytest.raises(DocumentError):export_pdf(data,[op])


def test_permissions_form_only_are_honored_and_signed_documents_blocked():
    with f.open(stream=source()) as doc:
        allowed=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_FORM)
        denied=doc.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_PRINT)
        doc.xref_set_key(doc.pdf_catalog(),'AcroForm/SigFlags','3');signed=doc.tobytes()
    export_pdf(allowed,[operation(allowed,Nombre='Ana')])
    with pytest.raises(DocumentError,match='permite'):export_pdf(denied,[operation(denied,Nombre='Ana')])
    with pytest.raises(DocumentError,match='firmados'):export_pdf(signed,[operation(signed,Nombre='Ana')])


def test_long_text_cannot_silently_disappear_or_become_illegible():
    with f.open(stream=source()) as doc:
        p=doc[0];w=next(p.widgets());w.rect=f.Rect(50,80,70,95);w.text_maxlen=0;w.update();data=doc.tobytes()
    with pytest.raises(DocumentError,match='espacio|cabe'):export_pdf(data,[operation(data,Nombre='Texto largo')])


def test_projects_and_page_organization_keep_values_and_form_structure():
    data=source();op=operation(data,Nombre='Ana',Acepto=True,Ciudad='BOG')
    packed,_=build_project(data,[op],{'name':'Formulario.pdf','page':0,'zoom':1,'base_changes':0})
    base,ops,_=read_project(packed);assert ops==[op] and base==data
    op['values'][0]['value']='Corregido'
    edited=organize_pdf(base,[op],[{'page':1,'rotation':0},{'page':0,'rotation':90}])
    with f.open(stream=edited) as doc:
        rows=form_model(doc)['fields'];assert len(rows)==5 and rows[0]['page']==1 and rows[0]['value']=='Corregido'
        assert doc.xref_get_key(doc.pdf_catalog(),'AcroForm/Fields')[0]!='null'


def test_api_uses_original_xrefs_and_overlays_values_without_mutating_base():
    data=source();op=operation(data,Nombre='Ana',Acepto=True)
    with TestClient(app) as c:
        document=c.post('/api/documents',files={'file':('form.pdf',data)}).json()['id'];url=f'/api/documents/{document}'
        model=c.post(url+'/forms',json={'operations':[op]}).json();r=model['fields'][0]
        assert r['xref']==op['values'][0]['xref'] and r['value']=='Ana' and r['base_value']==''
        assert c.post(url+'/forms',json={}).json()['fields'][0]['value']==''
        response=c.post(url+'/print',json={'operations':[op]});assert response.status_code==200
        with f.open(stream=response.content) as doc:assert 'Ana' in doc[0].get_text()
        response=c.post(url+'/pages/0/preview',json={'operations':[op],'scale':1});assert response.status_code==200 and response.headers['content-type']=='image/png'


def test_malformed_parent_cycle_is_reported_as_document_error():
    with f.open(stream=source()) as doc:
        p=doc[0];w=next(p.widgets());doc.xref_set_key(w.xref,'Parent',f'{w.xref} 0 R')
        with pytest.raises(DocumentError,match='estructura'):form_model(doc)
