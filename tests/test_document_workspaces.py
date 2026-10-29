from copy import deepcopy
from io import BytesIO
import json
from uuid import uuid4
from zipfile import ZipFile,ZIP_DEFLATED
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend import document_sets as sets,measurements as measure,layers
from backend.projects import build_project,read_project


def pdf(text='PLAN-01',repeat=False,rotation=0):
    with f.open() as d:
        p=d.new_page(width=600,height=800);p.insert_text((40,80),text,fontsize=16)
        if repeat:p.insert_text((40,150),text,fontsize=16)
        p.set_rotation(rotation);return d.tobytes()


def item(data,role='Origen'):
    return {'id':uuid4().hex,'data':data,'name':role+'.pdf','role':role,'sha256':sets.digest(data)}


def relation(a,b):
    report=sets.analyze([a,b],a['id'],b['id']);row=report['candidates'][0]
    return {'id':uuid4().hex,'code':row['code'],'source':row['source'][0],'target':row['target'][0]}


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_document_set_ambiguity_anchors_archive_and_byte_integrity(rotation):
    a=item(pdf('PLAN-01 PLAN-010',rotation=rotation));b=item(pdf('PLAN-01',repeat=True),'Destino')
    report=sets.analyze([a,b],a['id'],b['id']);assert len(report['candidates'])==1 and report['candidates'][0]['ambiguous']
    assert len(report['candidates'][0]['source'])==1 and len(report['candidates'][0]['target'])==2
    r=relation(a,b);data=sets.build([a,b],[r],'Mis documentos');items,relations,name=sets.read(data)
    assert name=='Mis documentos' and relations==[r] and [i['data'] for i in items]==[a['data'],b['data']]
    with f.open(stream=a['data']) as d:assert d[0].rect.contains(f.Rect(r['source']['rect']))


def test_manual_literal_identifiers_boundaries_and_column_gaps():
    a=item(pdf('COD COD-1 COD-10'));b=item(pdf('COD COD-1'),'Destino')
    r=sets.analyze([a,b],a['id'],b['id'],['COD','COD-1']);assert [c['code'] for c in r['candidates']]==['COD','COD-1']
    assert all(len(c['source'])==1 for c in r['candidates'])
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'PLAN-');p.insert_text((200,80),'01');a=item(d.tobytes())
    assert not sets.analyze([a,b],a['id'],b['id'],['PLAN-01'])['candidates']


@pytest.mark.parametrize('kind',['hash','rect','page','duplicate','code','unknown_document'])
def test_set_rejects_stale_or_forged_links(kind):
    a=item(pdf());b=item(pdf(),'Destino');r=relation(a,b);rows=[r]
    if kind=='hash':a['sha256']='0'*64
    if kind=='rect':r['source']['rect'][0]+=1
    if kind=='page':r['target']['page']=99
    if kind=='duplicate':rows.append({**deepcopy(r),'id':uuid4().hex})
    if kind=='code':r['code']='OTHER-01'
    if kind=='unknown_document':r['target']['document']=uuid4().hex
    with pytest.raises(DocumentError):sets.build([a,b],rows,'Test')


@pytest.mark.parametrize('kind',['extra','duplicate','tampered','version','traversal'])
def test_archive_is_verified_before_import(kind):
    a=item(pdf());data=sets.build([a],[],'Test')
    with ZipFile(BytesIO(data)) as source:entries={n:source.read(n) for n in source.namelist()}
    if kind in ['extra','traversal']:entries['../outside.pdf' if kind=='traversal' else 'extra.txt']=b'x'
    if kind=='tampered':entries['documents/'+a['id']+'.pdf']=pdf('OTHER-01')
    if kind=='version':
        manifest=json.loads(entries['manifest.json']);manifest['version']=99;entries['manifest.json']=json.dumps(manifest).encode()
    out=BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as archive:
        for n,data in entries.items():archive.writestr(n,data)
        if kind=='duplicate':archive.writestr('manifest.json',entries['manifest.json'])
    with pytest.raises(DocumentError):sets.read(out.getvalue())


CAL={'points':[[40,40],[140,40]],'distance':10,'unit':'m'}
@pytest.mark.parametrize('kind,pts,value,unit',[
 ('distance',[[40,100],[90,100]],5,'m'),('perimeter',[[40,100],[90,100],[90,150]],10,'m'),
 ('area',[[40,100],[140,100],[140,150],[40,150]],50,'m²'),('count',[[40,100],[90,100]],2,''),
])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_measurements_units_annotation_persistence_delete_and_project(kind,pts,value,unit,rotation):
    base=pdf(rotation=rotation);result=measure.measure(base,[],0,kind,pts,CAL,'m',True);assert result['value']==pytest.approx(value) and result['unit']==unit
    out=measure.measure(base,[],0,kind,pts,CAL,'m');rows=measure.model(out,[],0);assert len(rows['measurements'])==1 and rows['measurements'][0]['value']==pytest.approx(value)
    project,_=build_project(out,[],{'name':'Mediciones.pdf'});restored,_,_=read_project(project);assert measure.model(restored,[],0)['measurements']==rows['measurements']
    removed=measure.delete_measure(out,[],0,rows['measurements'][0]['id']);assert not measure.model(removed,[],0)['measurements']
    with f.open(stream=base) as a,f.open(stream=removed) as b:assert a[0].get_text()==b[0].get_text() and a[0].get_pixmap().samples==b[0].get_pixmap().samples


def test_measurement_converts_units_and_rejects_self_intersection_or_zero_scale():
    assert measure.measure(pdf(),[],0,'distance',[[40,100],[90,100]],CAL,'cm',True)['value']==pytest.approx(500)
    with pytest.raises(DocumentError):measure.measure(pdf(),[],0,'area',[[40,100],[140,150],[140,100],[40,150]],CAL)
    with pytest.raises(DocumentError):measure.measure(pdf(),[],0,'distance',[[40,100],[90,100]],{**CAL,'distance':0})
    with pytest.raises(DocumentError):measure.measure(pdf(),[],0,'distance',[[40,100],[90,100]],{**CAL,'unit':[]})


def layer_source():
    with f.open() as d:
        p=d.new_page();a=d.add_ocg('A');b=d.add_ocg('B',on=False);p.insert_text((40,80),'LAYER A',oc=a);p.insert_text((40,120),'LAYER B',oc=b);p.insert_text((40,160),'BASE');return d.tobytes(),a,b


def test_layer_visibility_survives_save_without_removing_text_and_preserves_locks():
    base,a,b=layer_source();out=layers.apply(base,[],[b]);info=layers.model(out,[]);assert {r['id']:r['visible'] for r in info['layers']}=={a:False,b:True}
    with f.open(stream=base) as x,f.open(stream=out) as y:
        assert x[0].get_pixmap().samples!=y[0].get_pixmap().samples
        assert b'LAYER' not in y[0].read_contents() # original font-encoded streams retained
        assert x[0].read_contents()==y[0].read_contents()
    restored=layers.apply(out,[],[a])
    with f.open(stream=base) as x,f.open(stream=restored) as y:assert x[0].get_pixmap().samples==y[0].get_pixmap().samples
    with f.open(stream=base) as d:d.set_layer(-1,locked=[a]);locked=d.tobytes()
    with pytest.raises(DocumentError):layers.apply(locked,[],[b])


def test_api_set_roundtrip_and_measurement_layer_preview(tmp_path,monkeypatch):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path))
    with TestClient(app) as c:
        doc=c.post('/api/documents',files={'file':('Original.pdf',pdf())}).json()
        a=c.post('/api/document-sets/current/'+doc['id'],json={'operations':[],'name':'Original.pdf'}).json()
        b=c.post('/api/document-sets/file',files={'file':('Plano.pdf',pdf(repeat=True))}).json()
        desc=lambda v:{k:v[k] for k in ['id','name','role','sha256']}
        payload={'documents':[desc(a),desc(b)],'source':a['id'],'target':b['id']}
        r=c.post('/api/document-sets/analyze',json=payload);assert r.status_code==200,r.text
        row=r.json()['candidates'][0];link={'id':uuid4().hex,'code':row['code'],'source':row['source'][0],'target':row['target'][0]}
        pack=c.post('/api/document-sets/export',json={**payload,'relations':[link],'name':'Conjunto'});assert pack.status_code==200,pack.text
        loaded=c.post('/api/document-sets/import',files={'file':('Test.reapdfset',pack.content)});assert loaded.status_code==200,loaded.text
        loaded=loaded.json();assert len(loaded['documents'])==2 and len(loaded['relations'])==1 and loaded['documents'][0]['id']!=a['id']
        data={'page':0,'kind':'distance','points':[[40,100],[90,100]],'calibration':CAL,'unit':'m'}
        preview=c.post('/api/documents/'+doc['id']+'/measure',json={**data,'preview':True});assert preview.status_code==200 and preview.json()['value']==5
        done=c.post('/api/documents/'+doc['id']+'/measure',json=data);assert done.status_code==200,done.text
        assert len(c.get('/api/documents/'+done.json()['id']+'/measurements').json()['measurements'])==1
