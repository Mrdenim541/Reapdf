from copy import deepcopy
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile,ZIP_DEFLATED
import json
import pymupdf as f
import pytest
from backend import document_sets as sets
from backend.engine import DocumentError
from tests.test_document_workspaces import item,pdf


def scan(rotation=0):
    with f.open() as d:
        p=d.new_page(width=600,height=800);pix=f.Pixmap(f.csRGB,f.IRect(0,0,50,50));pix.clear_with(190);p.insert_image(p.rect,stream=pix.tobytes('png'));p.set_rotation(rotation);return d.tobytes()


def manual_relation(a,b):
    return {'id':uuid4().hex,'code':'ZONA-01','source':sets.manual_anchor(a,'zona-01',0,[40,60,140,120]),'target':sets.manual_anchor(b,'ZONA-01',0,[50,130,160,200])}


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_manual_regions_on_scan_archive_compile_keep_originals(rotation):
    a=item(scan(rotation));b=item(scan(rotation),'Destino');r=manual_relation(a,b)
    assert not sets.index(a)
    blob=sets.build([a,b],[r],'Áreas relacionadas')
    with ZipFile(BytesIO(blob)) as z:assert json.loads(z.read('manifest.json'))['version']==2
    docs,relations,_=sets.read(blob);assert docs[0]['data']==a['data'] and relations==[r]
    out,report=sets.compile_pdf(docs,relations,'Vínculos manuales');assert report['links']==1
    with f.open(stream=out) as d:
        links=d[0].get_links();assert links[0]['page']==1;assert list(links[0]['from'])==pytest.approx(r['source']['rect'],abs=.02)
        assert not d[0].get_text() and len(d[0].get_images())==1


@pytest.mark.parametrize('kind',['rect','id','code','page','type','size','nan'])
def test_manual_anchors_reject_tampering_and_bad_geometry(kind):
    a=item(scan());b=item(scan(),'Destino');r=manual_relation(a,b);anchor=r['target']
    if kind=='rect':anchor['rect'][0]+=1
    if kind=='id':anchor['id']='f'*24
    if kind=='code':anchor['code']='OTRO-01'
    if kind=='page':anchor['page']=50
    if kind=='type':anchor['kind']='automatic'
    if kind=='size':anchor['rect']=[0,0,1,1]
    if kind=='nan':anchor['rect'][0]=float('nan')
    with pytest.raises(DocumentError):sets.build([a,b],[r],'Test')


def test_manual_revision_cannot_reuse_old_coordinates_or_follow_printed_code():
    a=item(scan());b=item(scan(),'Destino');r=manual_relation(a,b);new=item(pdf('ZONA-01'),'Revisión')
    plan=sets.revision([a,b],[r],b['id'],new);row=plan['affected'][0]
    assert row['status']=='manual_review' and row['candidates']==[] and not row['suggested']
    with pytest.raises(DocumentError):sets.revision([a,b],[r],b['id'],new,{r['id']:r['target']['id']})
    docs,relations,_=sets.revision([a,b],[r],b['id'],new,{r['id']:{'page':0,'rect':[100,250,240,330]}})
    assert relations[0]['target']['document']==new['id'] and relations[0]['target']['rect']==[100,250,240,330]
    assert sets.read(sets.build(docs,relations,'Revisado'))[1]==relations
    docs,relations,report=sets.revision([a,b],[r],b['id'],new,{r['id']:None});assert not relations and report['removed']==1


def test_legacy_format_stays_one_and_manual_cannot_be_downgraded():
    a=item(pdf());b=item(pdf(),'Destino');blob=sets.build([a,b],[],'Viejo')
    with ZipFile(BytesIO(blob)) as z:assert json.loads(z.read('manifest.json'))['version']==1
    r=manual_relation(a,b);blob=sets.build([a,b],[r],'Nuevo')
    with ZipFile(BytesIO(blob)) as z:entries={n:z.read(n) for n in z.namelist()}
    manifest=json.loads(entries['manifest.json']);manifest['version']=1;entries['manifest.json']=json.dumps(manifest).encode();stream=BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as z:
        for name,data in entries.items():z.writestr(name,data)
    with pytest.raises(DocumentError):sets.read(stream.getvalue())


def test_manual_api_roundtrip_remaps_document_ids(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    with TestClient(app) as c:
        docs=[c.post('/api/document-sets/file',files={'file':(name,scan())}).json() for name in ['A.pdf','B.pdf']]
        descriptors=[{k:d[k] for k in ['id','name','role','sha256']} for d in docs]
        anchors=[]
        for d in descriptors:
            response=c.post('/api/document-sets/manual-anchor',json={'document':d,'code':'ZONA-01','page':0,'rect':[40,60,150,120]});assert response.status_code==200;anchors.append(response.json())
        r={'id':uuid4().hex,'code':'ZONA-01','source':anchors[0],'target':anchors[1]};blob=c.post('/api/document-sets/export',json={'documents':descriptors,'relations':[r],'name':'Áreas'});assert blob.status_code==200
        loaded=c.post('/api/document-sets/import',files={'file':('Areas.reapdfset',blob.content)});assert loaded.status_code==200
        new=loaded.json();assert new['relations'][0]['source']['document']!=r['source']['document']
        assert new['relations'][0]['source']['id']==r['source']['id']
        descriptors=[{k:d[k] for k in ['id','name','role','sha256']} for d in new['documents']]
        assert c.post('/api/document-sets/compile',json={'documents':descriptors,'relations':new['relations'],'name':'Compilado'}).status_code==200
