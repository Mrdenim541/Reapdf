import pymupdf as f
import pytest
from backend.engine import DocumentError
from backend.structure_editing import model,properties,reading_preview,edit
from tests.test_structure_preflight_regions import tagged


def test_real_marked_content_preview_roles_text_and_geometry():
    base=tagged();report=reading_preview(base,[],0)
    assert len(report['blocks'])==1 and report['blocks'][0]['text']=='PARRAFO'
    assert report['blocks'][0]['roles']==['Document','P'] and report['untagged_blocks']==0
    x,y,w,h=report['blocks'][0]['box'];assert x==40 and 60<y<80 and w>20 and h>10


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_reading_geometry_tracks_rotation_without_inventing_tags(rotation):
    with f.open() as d:
        p=d.new_page(width=400,height=300);p.insert_text((40,80),'UNTAGGED');p.set_rotation(rotation);base=d.tobytes()
    report=reading_preview(base,[],0);assert report['untagged_blocks']==1 and not report['blocks'][0]['roles']
    with f.open(stream=base) as d:
        expected=f.Rect(d[0].get_text('blocks')[0][:4])*d[0].rotation_matrix
        x,y,w,h=report['blocks'][0]['box'];assert abs(f.Rect(x,y,x+w,y+h).tl-expected.tl)<.01


@pytest.mark.parametrize('role',['P','H','H1','H2','H3','H4','H5','H6'])
def test_change_existing_paragraph_role_and_language_preserving_content(role):
    base=tagged();row=next(r for r in model(base,[])['nodes'] if r['role']=='P')
    out=properties(base,[],row['id'],role=role)
    row=next(r for r in model(out,[])['nodes'] if r['role']==role)
    out=properties(out,[],row['id'],language='es-PE')
    assert next(r for r in model(out,[])['nodes'] if r['role']==role)['language']=='es-PE'
    assert reading_preview(out,[],0)['blocks'][0]['roles']==['Document',role]
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_text()==b[0].get_text() and a[0].get_pixmap().samples==b[0].get_pixmap().samples
        assert b.xref_get_key(b[0].xref,'StructParents')[1]=='0'


@pytest.mark.parametrize('kwargs',[{'role':'Figure'},{'role':[]},{'role':'H1','language':'es'},{'language':'not a language'},{'language':''},{}])
def test_invalid_semantic_changes_rejected(kwargs):
    base=tagged();row=next(r for r in model(base,[])['nodes'] if r['role']=='P')
    with pytest.raises(DocumentError):properties(base,[],row['id'],**kwargs)


def test_custom_roles_not_silently_remapped_and_namespace_protected():
    base=tagged();row=next(r for r in model(base,[])['nodes'] if r['role']=='P')
    with f.open(stream=base) as d:
        root=model(base,[])['root'];d.xref_set_key(root,'RoleMap','<</Custom /P>>');d.xref_set_key(row['id'],'S','/Custom');custom=d.tobytes()
    row=next(r for r in model(custom,[])['nodes'] if r['role']=='P')
    with pytest.raises(DocumentError):properties(custom,[],row['id'],role='H1')
    with f.open(stream=base) as d:
        d.xref_set_key(row['id'],'NS','<</Type /Namespace /NS (test)>>');namespaced=d.tobytes()
    with pytest.raises(DocumentError):properties(namespaced,[],row['id'],language='es')


def test_api_reading_preview_and_semantic_changes():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('tagged.pdf',tagged(),'application/pdf')}).json();url='/api/documents/'+doc['id']
        assert c.post(url+'/reading-preview',json={'page':0}).json()['blocks'][0]['text']=='PARRAFO'
        row=next(r for r in c.post(url+'/structure',json={}).json()['nodes'] if r['role']=='P')
        r=c.post(url+'/structure-properties',json={'id':row['id'],'role':'H1'});assert r.status_code==200,r.text
        assert c.post('/api/documents/'+r.json()['id']+'/reading-preview',json={'page':0}).json()['blocks'][0]['roles']==['Document','H1']
        assert c.post(url+'/reading-preview',json={'page':True}).status_code==422


def test_preview_follows_sibling_tag_order_instead_of_painting_order():
    with f.open(stream=tagged()) as d:
        p=d[0];p.insert_text((40,170),'SECOND');stream=p.get_contents()[-1];content=d.xref_stream(stream);d.update_stream(stream,b'/P<</MCID 2>>BDC\n'+content+b'\nEMC')
        parent=next(r for r in model(d.tobytes(),[])['nodes'] if r['role']=='Document');identity=d.get_new_xref()
        d.update_object(identity,f'<</Type/StructElem /S/P /Pg {p.xref} 0 R /K 2 /P {parent["id"]} 0 R>>')
        d.xref_set_key(parent['id'],'K','['+' '.join(f'{i} 0 R' for i in parent['children']+[identity])+']')
        info=model(d.tobytes(),[]);paragraph=next(r for r in info['nodes'] if r['role']=='P');figure=next(r for r in info['nodes'] if r['role']=='Figure');tree=int(d.xref_get_key(info['root'],'ParentTree')[1].split()[0])
        d.xref_set_key(tree,'Nums',f'[0[{paragraph["id"]} 0 R {figure["id"]} 0 R {identity} 0 R]]');base=d.tobytes()
    assert [r['text'] for r in reading_preview(base,[],0)['blocks']]==['PARRAFO','SECOND']
    parent=next(r for r in model(base,[])['nodes'] if r['role']=='Document');out=edit(base,[],parent['id'],order=list(reversed(parent['children'])))
    assert [r['text'] for r in reading_preview(out,[],0)['blocks']]==['SECOND','PARRAFO']
