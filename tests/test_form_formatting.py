"""Created AcroForms retain typography, styles, values and constraints."""
from pathlib import Path
import shutil,subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError,export_pdf
from backend.form_design import create_field
from backend.forms import form_model
from backend.form_data import flatten_form
from backend.pages import organize_pdf


def source():
    with f.open() as d:
        d.new_page(width=500,height=650).insert_text((40,80),'Formulario con formato')
        d.new_page().insert_text((40,80),'Otra pagina sin cambios');return d.tobytes()


def config(**kwargs):return {'name':'Cliente','page':0,'kind':'text','box':[40,120,350,75]}|kwargs

@pytest.mark.parametrize('font',['helv','tiro','cour'])
def test_three_families_initial_value_tooltip_flags_colors_and_other_page(font):
    base=source();out=create_field(base,[],config(font=font,size=14,label='Nombre y apellidos · cliente',required=True,max_length=50,value='María Pérez',color=[.2,.4,.6],border_color=[.4,.2,.1],fill_color=[.9,.95,1],border_width=2,border_style='D'))
    with f.open(stream=base) as before,f.open(stream=out) as d:
        p=d[0];w=next(p.widgets());assert w.text_font.lower()==font and w.text_fontsize==14 and w.field_flags&2
        assert w.field_label=='Nombre y apellidos · cliente' and w.field_value=='María Pérez' and w.text_maxlen==50
        assert w.text_color==pytest.approx([.2,.4,.6]) and w.fill_color==pytest.approx([.9,.95,1]) and w.border_width==2 and w.border_style=='Dashed'
        row=form_model(d)['fields'][0];assert row['editable'] and row['value']=='María Pérez'
        assert before[1].get_pixmap().samples==d[1].get_pixmap().samples
        flat=flatten_form(out,[])
        with f.open(stream=flat) as other:assert other[0].get_pixmap().samples==d[0].get_pixmap().samples and 'María Pérez' in other[0].get_text()


@pytest.mark.parametrize('kind,value,options',[('multiline','Línea 1\nLínea 2',[]),('choice','Dos',['Uno','Dos']),('checkbox',True,[])])
def test_values_and_styles_survive_fill_and_page_rotation(kind,value,options):
    out=create_field(source(),[],config(kind=kind,value=value,options=options,required=True,label='Información',border_style='U',size=0))
    with f.open(stream=out) as d:
        row=form_model(d)['fields'][0];assert row['editable'] and row['value']==value
        w=next(d[0].widgets());assert w.border_style=='Underline' and w.field_flags&2
    rotated=organize_pdf(out,[],[{'page':0,'rotation':90},{'page':1,'rotation':0}])
    with f.open(stream=rotated) as d:assert form_model(d)['fields'][0]['value']==value


@pytest.mark.parametrize('kwargs',[
 {'font':'unknown'},{'font':'hebo'},{'font':'tibi'},{'size':4},{'size':73},{'size':True},{'border_width':6},{'border_width':True},
 {'label':'bad\nlabel'},{'label':'x'*251},{'required':1},{'max_length':0},{'max_length':True},
 {'color':[2,0,0]},{'fill_color':'white'},{'border_style':'X'},
 {'value':'漢字'},{'value':'x'*51,'max_length':50},{'value':'No cabe '*100,'size':72},
])
def test_invalid_format_or_initial_value_rejected(kwargs):
    with pytest.raises(DocumentError):create_field(source(),[],config(**kwargs))


def test_radio_group_description_and_required_flag():
    out=create_field(source(),[],config(kind='radio',options=['Sí','No'],box=[40,120,350,100],required=True,label='Decisión de revisión',value='opcion_2'))
    with f.open(stream=out) as d:
        rows=form_model(d)['fields'];assert len(rows)==2 and all(r['editable'] and r['value']=='opcion_2' for r in rows)
        group=rows[0]['group'];assert d.xref_get_key(group,'TU')==('string','Decisión de revisión') and int(d.xref_get_key(group,'Ff')[1])&2


def test_creation_preview_is_read_only_and_rejects_overflow_before_applying():
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('form.pdf',source(),'application/pdf')}).json();url='/api/documents/'+doc['id']
        payload={'config':config(value='María',font='tiro',required=True)}
        preview=client.post(url+'/create-field',json=payload|{'preview':True});assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        assert client.post(url+'/forms',json={}).json()['fields']==[]
        applied=client.post(url+'/create-field',json=payload);assert applied.status_code==200
        rows=client.post('/api/documents/'+applied.json()['id']+'/forms',json={}).json()['fields'];assert rows[0]['value']=='María'


def test_poppler_renders_visible_initial_value_and_other_page_unchanged(tmp_path):
    if not shutil.which('pdftotext') or not shutil.which('pdftoppm'):pytest.skip('Poppler no disponible')
    out=create_field(source(),[],config(value='María Pérez',font='tiro',required=True,fill_color=[.9,.95,1]))
    path=tmp_path/'created.pdf';path.write_bytes(flatten_form(out,[]))
    text=subprocess.check_output(['pdftotext',str(path),'-']).decode();assert 'María Pérez' in text and 'Otra pagina sin cambios' in text
    subprocess.run(['pdftoppm','-f','1','-l','1','-scale-to','600','-singlefile','-png',str(path),str(tmp_path/'field')],check=True,capture_output=True)
    assert (tmp_path/'field.png').stat().st_size>1000
