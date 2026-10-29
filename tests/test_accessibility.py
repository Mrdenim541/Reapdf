"""Metadata repair, honest diagnostics and bounded tag-tree inspection."""
from lxml import etree
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.accessibility import inspect_accessibility,prepare_accessibility,tagged_structure
from backend.engine import DocumentError
from tests.signature_samples import document


def test_untagged_document_metadata_can_be_prepared_without_claiming_tagging_or_pdfua():
    base=document();before=inspect_accessibility(base,[]);assert {'missing_title','missing_language','missing_tags','display_title'}=={v['code'] for v in before['issues']}
    out=prepare_accessibility(base,[],'Informe técnico','es-PE',True);report=inspect_accessibility(out,[])
    assert report['title']=='Informe técnico' and report['language']=='es-PE' and report['display_document_title']
    assert [v['code'] for v in report['issues']]==['missing_tags'] and not report['tags']['present'] and not report['marked']
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for i in range(len(a)):assert a[i].get_pixmap().samples==b[i].get_pixmap().samples
        assert 'Informe técnico' in b.get_xml_metadata() and b.metadata['title']=='Informe técnico'


@pytest.mark.parametrize('indirect',[False,True])
def test_viewer_preferences_are_preserved_for_direct_and_indirect_dictionaries(indirect):
    with f.open(stream=document()) as d:
        if indirect:
            ref=d.get_new_xref();d.update_object(ref,'<< /HideToolbar true /DisplayDocTitle false >>');d.xref_set_key(d.pdf_catalog(),'ViewerPreferences',f'{ref} 0 R')
        else:d.xref_set_key(d.pdf_catalog(),'ViewerPreferences','<< /HideToolbar true /DisplayDocTitle false >>')
        base=d.tobytes()
    out=prepare_accessibility(base,[],'Informe','es')
    with f.open(stream=out) as d:assert d.xref_get_key(d.pdf_catalog(),'ViewerPreferences/HideToolbar')==('bool','true')


def test_xmp_unrelated_properties_and_translations_are_preserved():
    with f.open(stream=document()) as d:
        d.set_xml_metadata('''<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:mine="urn:private"><rdf:RDF><rdf:Description rdf:about=""><mine:note>Propiedad conservada</mine:note><dc:title><rdf:Alt><rdf:li xml:lang="x-default">Viejo</rdf:li><rdf:li xml:lang="en">Old translated title</rdf:li></rdf:Alt></dc:title></rdf:Description></rdf:RDF></x:xmpmeta>''');base=d.tobytes()
    out=prepare_accessibility(base,[],'Nuevo título','es-PE')
    with f.open(stream=out) as d:
        xml=d.get_xml_metadata();root=etree.fromstring(xml.encode());assert 'Propiedad conservada' in xml and 'Old translated title' in xml and 'Nuevo título' in xml and '>Viejo<' not in xml
        assert root.nsmap['mine']=='urn:private'


@pytest.mark.parametrize('xml',['not xml','<!DOCTYPE x [<!ENTITY ex SYSTEM "file:///etc/passwd">]><x>&ex;</x>'])
def test_malformed_or_entity_xmp_is_not_silently_destroyed(xml):
    with f.open(stream=document()) as d:d.set_xml_metadata(xml);base=d.tobytes()
    with pytest.raises(DocumentError):prepare_accessibility(base,[],'Nuevo','es')


def tagged(repeat=False):
    with f.open(stream=document()) as d:
        root=d.get_new_xref();fig1=d.get_new_xref();fig2=d.get_new_xref();table=d.get_new_xref()
        d.update_object(root,f'<< /Type /StructTreeRoot /K [{fig1} 0 R {fig2} 0 R {table} 0 R] /RoleMap << /CustomFigure /Figure >> >>')
        d.update_object(fig1,f'<< /Type /StructElem /S /Figure /P {root} 0 R /Alt (Diagrama) >>')
        d.update_object(fig2,f'<< /Type /StructElem /S /CustomFigure /P {root} 0 R /Alt null '+(f'/K {root} 0 R ' if repeat else '')+'>>')
        d.update_object(table,f'<< /Type /StructElem /S /Table /P {root} 0 R >>')
        d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<< /Marked true >>');return d.tobytes()


def test_actual_tag_tree_counts_alternative_text_custom_roles_and_tables():
    report=inspect_accessibility(tagged(),[]);t=report['tags'];assert t['present'] and t['figures']==2 and t['figures_without_alt']==1 and t['tables']==1 and t['custom_roles']==1
    assert {'figures_without_alt','custom_roles'}<={v['code'] for v in report['issues']}
    assert inspect_accessibility(tagged(repeat=True),[])['tags']['repeated_nodes']


def test_missing_labels_and_image_only_pages_are_reported_without_values():
    with f.open(stream=document()) as d:
        p=d[0];w=f.Widget();w.field_name='Campo';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.field_value='VALOR PRIVADO';w.rect=f.Rect(40,120,250,150);p.add_widget(w)
        page=d.new_page();pix=f.Pixmap(f.csRGB,(0,0,10,10),False);pix.clear_with(100);page.insert_image(f.Rect(0,0,500,650),stream=pix.tobytes('png'));base=d.tobytes()
    report=inspect_accessibility(base,[]);assert report['pages'][0]['fields_without_label']==1 and any(v['code']=='possible_scan' and v['page']==2 for v in report['issues'])
    assert 'VALOR PRIVADO' not in __import__('json').dumps(report)


@pytest.mark.parametrize('title,lang,display',[('', 'es',True),('A\nB','es',True),('T','invalid_lang',True),('T','',True),('T','es',1),('x'*251,'es',True)])
def test_invalid_preparation_is_rejected(title,lang,display):
    with pytest.raises(DocumentError):prepare_accessibility(document(),[],title,lang,display)


def test_signed_and_restricted_documents_remain_read_only():
    with f.open(stream=document()) as d:d.xref_set_key(d.pdf_catalog(),'AcroForm','<< /SigFlags 3 >>');base=d.tobytes()
    assert not inspect_accessibility(base,[])['can_prepare']
    with pytest.raises(DocumentError):prepare_accessibility(base,[],'Informe','es')


def test_tree_budget_is_enforced(monkeypatch):
    monkeypatch.setattr('backend.accessibility.MAX_NODES',1)
    with pytest.raises(DocumentError,match='2000'):inspect_accessibility(tagged(),[])


def test_api_keeps_source_read_only_and_returns_an_editable_version():
    base=document()
    with TestClient(app) as c:
        d=c.post('/api/documents',files={'file':('title.pdf',base,'application/pdf')}).json();url='/api/documents/'+d['id']
        old=c.post(url+'/accessibility',json={}).json();assert old['title']==''
        updated=c.post(url+'/prepare-accessibility',json={'title':'Nuevo título','language':'es-PE'});assert updated.status_code==200
        assert c.post(url+'/accessibility',json={}).json()['title']==''
        new=c.post('/api/documents/'+updated.json()['id']+'/accessibility',json={}).json();assert new['title']=='Nuevo título' and not new['tags']['present']


def test_missing_struct_tree_set_to_pdf_null_is_untagged_not_an_error():
    with f.open(stream=document()) as d:d.xref_set_key(d.pdf_catalog(),'StructTreeRoot','null');base=d.tobytes()
    assert not inspect_accessibility(base,[])['tags']['present']


def test_preparation_keeps_tag_tree_and_figure_alternatives_without_retagging():
    base=tagged();before=inspect_accessibility(base,[])['tags'];out=prepare_accessibility(base,[],'Diagrama','es');after=inspect_accessibility(out,[])['tags'];assert after==before
    with f.open(stream=out) as d:assert d.xref_get_key(d.pdf_catalog(),'MarkInfo/Marked')==('bool','true')
