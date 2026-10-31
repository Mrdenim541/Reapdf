"""Collection schema authoring must preserve files and compatible foreign data."""
import hashlib
import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.portfolio_metadata import model,edit
from backend.portfolio_schema import configure
from tests.test_portfolio_metadata import sample


def plan(base):return [{k:c[k] for k in ['id','label','type']} for c in model(base)['columns']]


def fingerprints(base):
    with f.open(stream=base) as d:return {name:hashlib.sha256(d.embfile_get(name)).digest() for name in d.embfile_names()},d[0].get_pixmap().samples


def test_create_rename_reorder_and_remove_column_preserves_custom_schema_and_attachments():
    base=sample();columns=plan(base);columns[0]['label']='Identificador';columns=[columns[2],columns[0],columns[1],columns[3],{'id':'new:revision','label':'Revisión','type':'number'}]
    out,report=configure(base,[],columns,True);info=model(out);assert [c['label'] for c in info['columns']]==['Date','Identificador','Amount','Locked','Revisión']
    key=report['created']['new:revision'];out=edit(out,[],[{'name':'One.txt','field':key,'value':7}]);assert model(out)['files'][0]['values'][key]==7
    removed,_=configure(out,[],[r for r in plan(out) if r['id']!=key],True);assert key not in model(removed)['files'][0]['values']
    assert fingerprints(base)==fingerprints(out)==fingerprints(removed)
    with f.open(stream=removed) as d:assert d.xref_get_key(d.pdf_catalog(),'Collection/CustomFlag')==('string','Preserve')


def test_removing_sort_column_keeps_remaining_direction_and_values():
    base=sample()
    with f.open(stream=base) as d:
        d.xref_set_key(d.pdf_catalog(),'Collection/Sort','<< /S [/Amount /Code] /A [false true] >>');base=d.tobytes()
    out,_=configure(base,[],[r for r in plan(base) if r['id']!='Amount'],True)
    with f.open(stream=out) as d:
        assert d.xref_get_key(d.pdf_catalog(),'Collection/Sort/S')==('array','[/Code]')
        assert d.xref_get_key(d.pdf_catalog(),'Collection/Sort/A')==('array','[true]')
        from backend.embedded_files import normalize
        assert all(f.mupdf.pdf_is_null(f.mupdf.pdf_dict_getp(spec,'CI/Amount')) for _,spec in normalize(d))


@pytest.mark.parametrize('kind',['unreviewed','locked','duplicate','duplicate_label','type','unknown','overflow'])
def test_invalid_schema_edits_are_atomic(kind):
    base=sample();columns=plan(base);reviewed=True
    if kind=='unreviewed':reviewed=False
    if kind=='locked':columns=[r for r in columns if r['id']!='Locked']
    if kind=='duplicate':columns.append(columns[0])
    if kind=='duplicate_label':columns[1]['label']=columns[0]['label']
    if kind=='type':columns[0]['type']='number'
    if kind=='unknown':columns.append({'id':'wrong','label':'Other','type':'text'})
    if kind=='overflow':columns+=[{'id':f'new:{i}','label':f'C{i}','type':'text'} for i in range(21)]
    with pytest.raises(DocumentError):configure(base,[],columns,reviewed)


def test_initial_custom_collection_creation_and_empty_attachment_protection():
    with f.open() as d:
        d.new_page();d.embfile_add('One.txt',b'ONE');base=d.tobytes()
    out,report=configure(base,[],[{'id':'new:name','label':'Nombre','type':'text'}],True)
    assert model(out)['columns'][0]['label']=='Nombre' and report['columns']==1
    with f.open() as d:
        d.new_page()
        with pytest.raises(DocumentError):configure(d.tobytes(),[],[{'id':'new:name','label':'Nombre','type':'text'}],True)


def test_native_portfolio_organizer_keeps_new_schema_columns():
    from backend.portfolios import configure as organizer,model as presentation
    with f.open() as d:
        d.new_page();d.embfile_add('One.txt',b'ONE');base=d.tobytes()
    files=[{'name':'One.txt','title':'One','description':'Description'}];base=organizer(base,[],True,files=files)
    out,report=configure(base,[],plan(base)+[{'id':'new:revision','label':'Revisión','type':'text'}],True);key=report['created']['new:revision']
    out=edit(out,[],[{'name':'One.txt','field':key,'value':'A'}]);assert presentation(out)['supported']
    saved=organizer(out,[],True,'tiles',[{'name':'One.txt','title':'New title','description':'New description'}])
    assert model(saved)['files'][0]['values'][key]=='A' and presentation(saved)['view']=='tiles'


def test_schema_api_review_create_and_saved_columns():
    from fastapi.testclient import TestClient
    from backend.app import app
    base=sample()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('Portfolio.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        proposal=plan(base)+[{'id':'new:state','label':'State','type':'text'}]
        assert client.post(url+'/configure-portfolio-schema',json={'columns':proposal}).status_code==422
        response=client.post(url+'/configure-portfolio-schema',json={'columns':proposal,'reviewed':True});assert response.status_code==200,response.text
        saved=response.json();info=client.post('/api/documents/'+saved['id']+'/portfolio-metadata',json={}).json();assert info['columns'][-1]['label']=='State'
        assert client.post(url+'/configure-portfolio-schema',json={'columns':proposal+[{'id':'new:bad','label':'Bad','type':[]}],'reviewed':True}).status_code==422
