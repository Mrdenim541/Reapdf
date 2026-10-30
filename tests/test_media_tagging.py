from io import BytesIO
import pymupdf as f
import pytest
from pyhanko.pdf_utils.reader import PdfFileReader
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,reading_preview
from backend.projects import build_project,read_project
from backend.engine import DocumentError


def source(rotation=0,crop=False,links=True,repeated=True,only_image=False,goto=False):
    with f.open() as d:
        p=d.new_page(width=500,height=400)
        if not only_image:
            p.insert_text((40,70),'TITLE');p.insert_text((40,120),'VISIT OUR PAGE')
            if links:p.insert_link({'kind':f.LINK_GOTO,'from':f.Rect(35,100,200,130),'page':0,'to':f.Point(0,0)} if goto else {'kind':f.LINK_URI,'from':f.Rect(35,100,200,130),'uri':'https://example.com/document'})
        pix=f.Pixmap(f.csRGB,f.IRect(0,0,120,80),False);pix.clear_with(150);x=p.insert_image(f.Rect(40,160,220,280),pixmap=pix)
        if repeated:p.insert_image(f.Rect(270,160,450,280),xref=x)
        if crop:p.set_cropbox(f.Rect(10,10,490,390))
        p.set_rotation(rotation);return d.tobytes()


def selection(info):
    return [{'id':e['id'],'role':'Artifact' if e['kind']=='image' and i==len(info['entries'])-1 else e['role'],'alt':'Picture of equipment' if e['kind']=='image' else 'Visit documentation' if e['kind']=='link' else ''} for i,e in enumerate(info['entries'])]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_image_occurrences_and_real_link_parenttree_are_independent_and_preserve_source(rotation,crop):
    base=source(rotation,crop);info=candidates(base,[]);assert [e['kind'] for e in info['entries']]==['text','link','image','image']
    assert info['entries'][2]['id']!=info['entries'][3]['id']
    out,report=create(base,[],selection(info),reviewed=True);assert report['figures']==report['links']==report['decorative_images']==1 and report['tagged_objects']==3
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[0].get_text()==b[0].get_text()
        assert len(b[0].get_image_info())==2 and len(b[0].get_links())==1
        assert b[0].get_links()[0]['uri']==a[0].get_links()[0]['uri']
        assert b.xref_get_key(b[0].xref,'Tabs')[1]=='/S'
    rows=model(out,[])['nodes'];assert [r['alt'] for r in rows if r['role']=='Figure']==['Picture of equipment']
    # Independent reader proves that the annotation key points to its Link,
    # and OBJR resolves back to that same annotation (not a painted lookalike).
    reader=PdfFileReader(BytesIO(out));root=reader.root['/StructTreeRoot'];numbers=root['/ParentTree']['/Nums'];pairs={int(numbers[i]):numbers[i+1] for i in range(0,len(numbers),2)}
    annotations=reader.root['/Pages']['/Kids'][0]['/Annots'];annotation_ref=list.__getitem__(annotations,0);annotation=annotation_ref.get_object();key=int(annotation['/StructParent']);link=pairs[key]
    assert str(link['/S'])=='/Link' and str(link['/Alt'])=='Visit documentation'
    objr=link['/K'][1];assert objr.raw_get('/Obj').idnum==annotation_ref.idnum and objr.raw_get('/Obj').generation==annotation_ref.generation
    assert int(link['/K'][0])==1 and str(annotation['/Contents'])=='Visit documentation'
    restored,ops,_=read_project(build_project(out,[],{'name':'Media.pdf'})[0]);assert restored==out and not ops


def test_internal_link_destination_preserved():
    base=source(goto=True);out,_=create(base,[],selection(candidates(base,[])),reviewed=True)
    with f.open(stream=out) as d:assert d[0].get_links()[0]['kind']==f.LINK_GOTO and d[0].get_links()[0]['page']==0


def test_image_only_document_and_decorative_images_need_no_ocr():
    base=source(links=False,repeated=False,only_image=True);info=candidates(base,[]);assert len(info['entries'])==1 and info['entries'][0]['kind']=='image'
    entry={'id':info['entries'][0]['id'],'role':'Figure','alt':'Diagram'};out,_=create(base,[],[entry],reviewed=True);assert any(r['role']=='Figure' for r in model(out,[])['nodes'])
    entry['role']='Artifact';out,report=create(base,[],[entry],reviewed=True);assert report['tagged_objects']==0 and report['decorative_images']==1
    assert not any(r['role']=='Figure' for r in model(out,[])['nodes'])


@pytest.mark.parametrize('kind',['missing_alt','bad_alt','wrong_role','alt_control','link_wrong_role'])
def test_unreviewed_media_semantics_cannot_be_published(kind):
    base=source();info=candidates(base,[]);entries=selection(info)
    if kind=='missing_alt':entries[2].pop('alt')
    elif kind=='bad_alt':entries[2]['alt']=' '
    elif kind=='wrong_role':entries[2]['role']='P'
    elif kind=='alt_control':entries[2]['alt']='bad\x00text'
    elif kind=='link_wrong_role':entries[1]['role']='P'
    with pytest.raises(DocumentError):create(base,[],entries,reviewed=True)


@pytest.mark.parametrize('kind',['partial','multiple','duplicate','over_image','javascript','chained','locked','prior_parent'])
def test_ambiguous_or_special_links_remain_protected(kind):
    with f.open(stream=source()) as d:
        p=d[0];link=p.get_links()[0];x=link['xref']
        if kind=='partial':p.delete_link(link);p.insert_link({'kind':f.LINK_URI,'from':f.Rect(50,110,90,125),'uri':'https://example.com'})
        elif kind=='multiple':p.delete_link(link);p.insert_link({'kind':f.LINK_URI,'from':f.Rect(30,40,200,130),'uri':'https://example.com'})
        elif kind=='duplicate':p.insert_link({'kind':f.LINK_URI,'from':link['from'],'uri':'https://example.com/again'})
        elif kind=='over_image':p.delete_link(link);p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,160,220,280),'uri':'https://example.com'})
        elif kind=='javascript':d.xref_set_key(x,'AA','<</E<</S/JavaScript/JS(alert)>> >>')
        elif kind=='chained':d.xref_set_key(x,'A/Next','<</S/JavaScript/JS(alert)>>')
        elif kind=='locked':d.xref_set_key(x,'F','128')
        elif kind=='prior_parent':d.xref_set_key(x,'StructParent','99')
        base=d.tobytes()
    with pytest.raises(DocumentError):candidates(base,[])


def test_api_media_review_and_creation():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Media.pdf',source(),'application/pdf')}).json();url='/api/documents/'+doc['id']
        info=c.post(url+'/tagging-candidates',json={}).json();result=c.post(url+'/create-basic-tags',json={'entries':selection(info),'reviewed':True});assert result.status_code==200,result.text
        assert result.json()['tagging_report']['figures']==1 and result.json()['tagging_report']['links']==1
