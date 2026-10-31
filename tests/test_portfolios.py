from copy import deepcopy
import hashlib
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.portfolios import model,configure
from backend.pro_tools import add_attachment,download_attachment,attachment_pdf,attachment_model
from backend.engine import DocumentError


def source(nested=False):
    with f.open() as d:
        d.new_page().insert_text((40,100),'PORTFOLIO COVER')
        d.embfile_add('uno.txt',b'first payload',filename='uno.txt')
        d.embfile_add('plano.pdf',b'%PDF-private-synthetic',filename='plano.pdf')
        if nested:
            kind,value=d.xref_get_key(d.pdf_catalog(),'Names/EmbeddedFiles');child=d.get_new_xref();d.update_object(child,value);d.xref_set_key(d.pdf_catalog(),'Names/EmbeddedFiles',f'<< /Kids [{child} 0 R] >>')
        return d.tobytes()


def rows(base):return [{'name':r['name'],'title':'Título '+r['name'],'description':'Descripción ñ'} for r in model(base)['files']][::-1]


@pytest.mark.parametrize('view',['details','tiles','hidden'])
@pytest.mark.parametrize('nested',[False,True])
def test_native_collection_metadata_order_payloads_and_page_unchanged(view,nested):
    base=source(nested);files=rows(base);out=configure(base,[],True,view,files);m=model(out)
    assert m['enabled'] and m['supported'] and m['view']==view
    assert [r['name'] for r in m['files']]==[r['name'] for r in files]
    for left,right in zip(m['files'],files):assert left['title']==right['title'] and left['description']==right['description']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert b.xref_get_key(b.pdf_catalog(),'Collection/Type')==('name','/Collection')
        assert b.xref_get_key(b.pdf_catalog(),'Collection/Sort/S')==('name','/ReapdfOrder')
    assert [download_attachment(base,i)[0] for i in range(2)]==[download_attachment(out,i)[0] for i in range(2)]
    disabled=configure(out,[],False)
    assert not model(disabled)['enabled'] and len(attachment_model(disabled))==2
    assert download_attachment(disabled,0)[0]==download_attachment(base,0)[0]


def test_portfolio_attachment_changes_nested_tree_and_metadata_preserved():
    base=source(True);out=configure(base,[],True,files=rows(base));out=add_attachment(out,[],'añadido.txt',b'new')
    assert len(model(out)['files'])==3
    out=attachment_pdf(out,[],0);m=model(out);assert len(m['files'])==2
    assert any(r['title'].startswith('Título') for r in m['files'])


@pytest.mark.parametrize('kind',['duplicate','unknown','missing','control','empty','long','extra','wrongtype'])
def test_invalid_metadata_atomic(kind):
    base=source();files=rows(base)
    if kind=='duplicate':files[1]=deepcopy(files[0])
    if kind=='unknown':files[0]['name']='unknown'
    if kind=='missing':files.pop()
    if kind=='control':files[0]['title']='bad\nvalue'
    if kind=='empty':files[0]['title']=' '
    if kind=='long':files[0]['description']='x'*1001
    if kind=='extra':files[0]['order']=4
    if kind=='wrongtype':files[0]['name']=[]
    with pytest.raises(DocumentError):configure(base,[],True,files=files)
    assert not model(base)['enabled']


def test_external_schema_is_readonly_but_explicit_disable_retains_payloads():
    with f.open(stream=source()) as d:
        d.xref_set_key(d.pdf_catalog(),'Collection','<< /Schema << /Custom << /Subtype /S /N (External) >> >> /View /T >>');base=d.tobytes()
    assert model(base)['enabled'] and not model(base)['supported']
    with pytest.raises(DocumentError,match='externo'):configure(base,[],True,files=rows(base))
    assert not model(configure(base,[],False))['enabled']


def test_nested_tree_cycles_duplicates_and_limits_rejected():
    for mode in ['cycle','duplicate','both']:
        with f.open(stream=source()) as d:
            kind,value=d.xref_get_key(d.pdf_catalog(),'Names/EmbeddedFiles');child=d.get_new_xref();d.update_object(child,value)
            if mode=='cycle':d.update_object(child,f'<< /Kids [{child} 0 R] >>');tree=f'<< /Kids [{child} 0 R] >>'
            elif mode=='duplicate':tree=f'<< /Kids [{child} 0 R {child} 0 R] >>'
            else:tree=f'<< /Kids [{child} 0 R] /Names [] >>'
            d.xref_set_key(d.pdf_catalog(),'Names/EmbeddedFiles',tree);base=d.tobytes()
        with pytest.raises(DocumentError):model(base)


def test_portfolio_api_and_original_not_replaced():
    base=source()
    with TestClient(app) as c:
        info=c.post('/api/documents',files={'file':('portfolio.pdf',base,'application/pdf')}).json();url='/api/documents/'+info['id']
        assert not c.get(url+'/portfolio').json()['enabled']
        response=c.post(url+'/configure-portfolio',json={'enabled':True,'view':'details','files':rows(base)})
        assert response.status_code==200,response.text
        assert c.get('/api/documents/'+response.json()['id']+'/portfolio').json()['enabled']
        assert c.post(url+'/export',json={'operations':[]}).content==base


def test_collection_version_and_independent_parser():
    from io import BytesIO
    from pyhanko.pdf_utils.reader import PdfFileReader
    base=source().replace(b'%PDF-1.7',b'%PDF-1.4',1);files=rows(base);out=configure(base,[],True,'details',files)
    root=PdfFileReader(BytesIO(out)).root;collection=root['/Collection']
    assert root['/Version']=='/1.7' and collection['/Type']=='/Collection'
    assert collection['/Schema']['/ReapdfTitle']['/Subtype']=='/S'
    assert collection['/Sort']['/A']
    names=root['/Names']['/EmbeddedFiles']['/Names']
    values={str(names[i]):names[i+1].get_object()['/CI'] for i in range(0,len(names),2)}
    assert values[files[0]['name']]['/ReapdfTitle']==files[0]['title']
    assert values[files[0]['name']]['/ReapdfOrder']==1


@pytest.mark.parametrize('shared_spec',[False,True])
def test_configure_detaches_imported_shared_metadata(shared_spec):
    with f.open(stream=source()) as d:
        from backend.embedded_files import normalize
        entries=normalize(d);n=f.mupdf;pdf=f._as_pdf_document(d)
        ci=d.get_new_xref();d.update_object(ci,'<< /External (preserved) >>')
        shared=n.pdf_new_indirect(pdf,ci,0)
        for _,spec in entries:n.pdf_dict_puts(spec,'CI',shared)
        if shared_spec:
            flat=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles/Names');n.pdf_array_put(flat,3,entries[0][1])
        base=d.tobytes()
    files=rows(base);files[0]['description']='First independent';files[1]['description']='Second independent'
    out=configure(base,[],True,files=files)
    result=model(out)
    assert [(v['title'],v['description']) for v in result['files']]==[(v['title'],v['description']) for v in files]
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert {name:a.embfile_get(name) for name in a.embfile_names()}=={name:b.embfile_get(name) for name in b.embfile_names()}
        for _,spec in normalize(b):assert n.pdf_to_text_string(n.pdf_dict_gets(n.pdf_dict_gets(spec,'CI'),'External'))=='preserved'
