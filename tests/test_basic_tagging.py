import hashlib
import pymupdf as f
import pytest
from backend.basic_tagging import candidates,create
from backend.structure_editing import model,reading_preview,edit
from backend.projects import build_project,read_project
from backend.engine import DocumentError


def source(rotation=0,crop=False,pages=2):
    with f.open() as d:
        for i in range(pages):
            p=d.new_page(width=500,height=400);p.insert_text((40,70),f'TITLE {i+1}',fontsize=20);p.insert_text((40,120),f'Body paragraph {i+1}.');p.insert_text((40,180),'Second paragraph.');p.draw_line((40,85),(350,85))
            if crop:p.set_cropbox(f.Rect(10,10,490,390))
            p.set_rotation(rotation)
        return d.tobytes()


def selection(info):return [{'id':e['id'],'role':'H1' if e['text'].startswith('TITLE') else 'P'} for e in info['entries']]


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_initial_tree_mcid_parenttree_text_and_pixels_preserved(rotation,crop):
    base=source(rotation,crop);digest=hashlib.sha256(base).digest();info=candidates(base,[]);out,report=create(base,[],selection(info),'es-PE',True)
    assert report['tagged_objects']==6 and not report['pdf_ua_validated'];assert hashlib.sha256(base).digest()==digest
    with f.open(stream=base) as a,f.open(stream=out) as b:
        for i,(p,q) in enumerate(zip(a,b)):
            assert p.get_text()==q.get_text() and p.get_pixmap().samples==q.get_pixmap().samples
            assert b.xref_get_key(q.xref,'StructParents')[1]==str(i)
            assert b'/MCID 0' in q.read_contents() and b'/Artifact BMC' in q.read_contents()
        root=int(b.xref_get_key(b.pdf_catalog(),'StructTreeRoot')[1].split()[0]);tree=int(b.xref_get_key(root,'ParentTree')[1].split()[0]);assert b.xref_get_key(tree,'Nums')[0]=='array';assert b.xref_get_key(b.pdf_catalog(),'Lang')[1]=='es-PE'
    rows=model(out,[])['nodes'];assert sum(r['role']=='H1' for r in rows)==2 and all(r['parent_valid'] for r in rows)
    preview=reading_preview(out,[],0);assert preview['untagged_blocks']==0 and preview['blocks'][0]['roles']==['Document','Sect','H1']


def test_reviewed_order_is_actual_structure_order_and_survives_project():
    base=source(pages=1);info=candidates(base,[]);entries=selection(info);entries[1:]=reversed(entries[1:]);out,_=create(base,[],entries,reviewed=True)
    assert [b['text'] for b in reading_preview(out,[],0)['blocks']]==['TITLE 1','Second paragraph.','Body paragraph 1.']
    restored,ops,_=read_project(build_project(out,[],{'name':'Tagged.pdf'})[0]);assert restored==out and not ops
    with pytest.raises(DocumentError,match='estructura'):candidates(out,[])


@pytest.mark.parametrize('kind',['review','duplicate','missing','unknown','bad_role','bad_language','page_order'])
def test_review_and_stale_or_invalid_selection_cannot_create_partial_tags(kind):
    base=source();info=candidates(base,[]);entries=selection(info);language='es';reviewed=True
    if kind=='review':reviewed=False
    elif kind=='duplicate':entries[-1]=entries[0]
    elif kind=='missing':entries.pop()
    elif kind=='unknown':entries[0]['id']='stale'
    elif kind=='bad_role':entries[0]['role']='Figure'
    elif kind=='bad_language':language='es /bad'
    elif kind=='page_order':entries.reverse()
    with pytest.raises(DocumentError):create(base,[],entries,language,reviewed)


@pytest.mark.parametrize('kind',['form','annotation','widget','marked','partial','signed','no_copy','no_modify','incomplete','nested','empty','pages'])
def test_unsupported_documents_refused_before_tag_publication(kind):
    with f.open(stream=source(pages=1)) as d:
        p=d[0]
        if kind=='image':
            pix=f.Pixmap(f.csRGB,f.IRect(0,0,10,10),False);pix.clear_with(255);p.insert_image(f.Rect(250,200,300,250),pixmap=pix)
        elif kind=='form':
            with f.open(stream=source(pages=1)) as other:p.show_pdf_page(f.Rect(0,200,200,350),other,0)
        elif kind=='link':p.insert_link({'kind':f.LINK_URI,'from':f.Rect(40,40,100,70),'uri':'https://example.com'})
        elif kind=='annotation':p.add_text_annot((100,100),'note')
        elif kind=='widget':
            w=f.Widget();w.field_name='A';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(100,250,200,280);p.add_widget(w)
        elif kind=='marked':
            x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'/Artifact BMC '+p.read_contents()+b' EMC');p.set_contents(x)
        elif kind=='partial':d.xref_set_key(p.xref,'StructParents','0')
        elif kind=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>')
        elif kind in ['incomplete','nested','empty']:
            x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,{'incomplete':b'BT (A) Tj','nested':b'BT BT (A) Tj ET ET','empty':b'BT /helv 12 Tf ( ) Tj ET'}[kind]);p.set_contents(x)
        elif kind=='pages':
            for _ in range(20):d.new_page()
        if kind in ['no_copy','no_modify']:
            permissions=f.PDF_PERM_MODIFY if kind=='no_copy' else f.PDF_PERM_COPY
            base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner-test',permissions=permissions)
        else:base=d.tobytes()
    with pytest.raises(DocumentError):candidates(base,[])


def test_pending_text_operations_are_tagged_and_old_review_cannot_omit_them():
    base=source(pages=1);info=candidates(base,[])
    operations=[{'type':'textbox','page':0,'points':[[40,250],[240,290]],'text':'New text','size':12,'font':'helv','color':[0,0,0],'align':0}]
    updated=candidates(base,operations);assert len(updated['entries'])==4
    with pytest.raises(DocumentError):create(base,operations,selection(info),reviewed=True)
    out,_=create(base,operations,selection(updated),reviewed=True)
    assert 'New text' in [r['text'] for r in reading_preview(out,[],0)['blocks']]


def test_api_prepare_and_create_versions():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        original=c.post('/api/documents',files={'file':('Plain.pdf',source(pages=1),'application/pdf')}).json();url='/api/documents/'+original['id'];prepared=c.post(url+'/tagging-candidates',json={});assert prepared.status_code==200,prepared.text
        r=c.post(url+'/create-basic-tags',json={'entries':selection(prepared.json()),'reviewed':True,'language':'es'});assert r.status_code==200,r.text
        assert r.json()['id']!=original['id'] and r.json()['tagging_report']['tagged_objects']==3
        report=c.post('/api/documents/'+r.json()['id']+'/reading-preview',json={'page':0}).json();assert report['blocks'][0]['roles'][-1]=='H1'
