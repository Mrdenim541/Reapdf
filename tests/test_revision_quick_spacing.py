from copy import deepcopy
import pymupdf as f
import pytest
from backend import document_sets as sets
from backend.engine import DocumentError
from backend.styled_text import inspect_styled,replace_styled
from backend.quick_text import insert
from tests.test_document_workspaces import item,pdf,relation


def revision_source(kind):
    with f.open() as d:
        p=d.new_page(width=600,height=800)
        if kind=='moved':p=d.new_page(width=600,height=800)
        if kind!='missing':p.insert_text((40,80),'PLAN-01',fontsize=16)
        if kind=='ambiguous':p.insert_text((40,150),'PLAN-01',fontsize=16)
        return d.tobytes()


@pytest.mark.parametrize('kind',['same_location','moved','missing','ambiguous'])
def test_revision_requires_review_and_preserves_original_set(kind):
    a=item(pdf());b=item(pdf(),'Destino');r=relation(a,b);original=sets.build([a,b],[r],'Anterior');replacement=item(revision_source(kind),'Revision')
    report=sets.revision([a,b],[r],b['id'],replacement);row=report['affected'][0];assert row['status']==kind
    with pytest.raises(DocumentError):sets.revision([a,b],[r],b['id'],replacement,{})
    with pytest.raises(DocumentError):sets.revision([a,b],[r],b['id'],replacement,{r['id']:'inventado'})
    choice=None if kind=='missing' else row['candidates'][-1]['id'];docs,links,summary=sets.revision([a,b],[r],b['id'],replacement,{r['id']:choice})
    assert docs[1]['role']==b['role'] and docs[1]['id']==replacement['id']
    assert len(links)==(0 if kind=='missing' else 1)
    if links:assert links[0]['target']['id']==choice
    reopened,old_links,_=sets.read(original);assert reopened[1]['data']==b['data'] and old_links==[r]
    packed=sets.build(docs,links,'Revision');assert len(sets.read(packed)[0])==2


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_quick_text_auto_height_unicode_rotation_original_content(rotation):
    base=pdf('ORIGINAL',rotation=rotation)
    preview=insert(base,[],0,[50,220],'Texto nuevo á ñ Ω\nSegunda línea',14,width=150,preview=True)
    out,report=insert(base,[],0,[50,220],'Texto nuevo á ñ Ω\nSegunda línea',14,width=150)
    assert report==preview and report['lines']>=2
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation and 'Ω' in b[0].get_text() and 'ORIGINAL' in b[0].get_text()
        area=f.Rect(report['box']);matches=b[0].search_for('Texto nuevo')
        assert matches and area.contains(matches[0]*b[0].rotation_matrix)
        # All source content streams remain present unchanged.
        assert all(a.xref_stream(x) in [b.xref_stream(y) for y in b[0].get_contents()] for x in a[0].get_contents())
        if rotation==0:
            boxes=b[0].get_text('blocks');new=next(v for v in boxes if 'Texto nuevo' in v[4]);rect=f.Rect(new[:4])+(-2,-2,2,2)
            rows=inspect_styled(out,[],0,[rect.x0,rect.y0,rect.width,rect.height])['runs'];assert all(r['editable'] for r in rows)


@pytest.mark.parametrize('point,text,width', [([40,60],'Cruza texto',200),([590,220],'Borde',200),([40,790],'Muy bajo',200),([40,220],'X'*4001,200),([40,220],'Sin ancho',1)])
def test_quick_text_rejects_overlap_overflow_and_invalid_inputs(point,text,width):
    base=pdf('ORIGINAL')
    with pytest.raises(DocumentError):insert(base,[],0,point,text,width=width)


def spaced_source(char=0,word=0,kerning=50):
    with f.open() as d:
        p=d.new_page();p.insert_text((40,80),'AVATAR TEST',fontsize=18);p.insert_text((40,200),'NEIGHBOR')
        x=p.get_contents()[0];data=d.xref_stream(x).replace(b'BT',f'BT {char} Tc {word} Tw'.encode()).replace(b'[<4156415441522054455354>]TJ',f'[<4156> {kerning} <415441522054455354>]TJ'.encode());d.update_stream(x,data)
        return d.tobytes()


@pytest.mark.parametrize('char,word,kerning',[(0,0,50),(1,1,-80),(.5,1,0),(0,0,-60)])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_tj_spacing_original_positions_and_non_text_operators_preserved(char,word,kerning,rotation):
    base=spaced_source(char,word,kerning)
    with f.open(stream=base) as d:d[0].set_rotation(rotation);base=d.tobytes()
    row=inspect_styled(base,[],0,[35,55,300,40])['runs'][0];assert row['editable'],row['reason']
    out=replace_styled(base,[],0,[35,55,300,40],[{'id':row['id'],'text':'AVATAR TES'}])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert b[0].rotation==rotation
        before=a[0].get_text('rawdict')['blocks'][0]['lines'][0]['spans'][0]['chars'];after=b[0].get_text('rawdict')['blocks'][0]['lines'][0]['spans'][0]['chars']
        assert ''.join(c['c'] for c in after)=='AVATAR TES'
        assert [c['origin'] for c in after]==pytest.approx([c['origin'] for c in before[:-1]])
        assert b[0].search_for('NEIGHBOR')==a[0].search_for('NEIGHBOR')
        assert f'{char} Tc {word} Tw'.encode() in b[0].read_contents()


def test_spacing_state_restored_by_q_and_unreliable_positions_refused():
    base=spaced_source(2,0,50)
    with f.open(stream=base) as d:
        p=d[0];x=p.get_contents()[0];d.update_stream(x,d.xref_stream(x).replace(b'2 Tc 0 Tw',b'2 Tc q 0 Tc Q 0 Tw'));base=d.tobytes()
    row=inspect_styled(base,[],0,[35,55,300,40])['runs'][0];assert row['editable']
    with f.open(stream=base) as d:
        p=d[0];x=p.get_contents()[0];d.update_stream(x,d.xref_stream(x).replace(b' 50 ',b' 12000 '));bad=d.tobytes()
    assert not inspect_styled(bad,[],0,[35,55,300,40])['runs'][0]['editable']


def test_new_endpoints_preview_apply_and_stale_review(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import app
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'state'))
    with TestClient(app) as client:
        a=client.post('/api/document-sets/file',files={'file':('A.pdf',pdf())}).json();b=client.post('/api/document-sets/file',files={'file':('B.pdf',pdf())}).json();c=client.post('/api/document-sets/file',files={'file':('C.pdf',revision_source('moved'))}).json()
        descriptor=lambda d:{k:d[k] for k in ['id','name','role','sha256']}
        docs=[descriptor(a),descriptor(b)];analysis=client.post('/api/document-sets/analyze',json={'documents':docs,'source':a['id'],'target':b['id']}).json()['candidates'][0]
        from uuid import uuid4
        r={'id':uuid4().hex,'code':analysis['code'],'source':analysis['source'][0],'target':analysis['target'][0]};payload={'documents':docs,'relations':[r],'old':b['id'],'replacement':descriptor(c)}
        plan=client.post('/api/document-sets/revision',json=payload);assert plan.status_code==200
        choice=plan.json()['affected'][0]['candidates'][0]['id'];apply={**payload,'apply':True,'choices':{r['id']:choice}}
        assert client.post('/api/document-sets/revision',json=apply).status_code==422
        out=client.post('/api/document-sets/revision',json={**apply,'acknowledge':True});assert out.status_code==200 and out.json()['relations'][0]['target']['page']==1
        quick={'page':0,'point':[50,220],'text':'Texto á Ω','preview':True};route=f"/api/documents/{a['id']}/insert-text-auto";preview=client.post(route,json=quick);assert preview.status_code==200 and preview.json()['lines']==1
        quick['preview']=False;out=client.post(route,json=quick);assert out.status_code==200 and out.json()['id']!=a['id']
        assert client.post(route,json={**quick,'point':[40,60]}).status_code==422


def test_synthetic_spaces_are_not_guessed_and_unrelated_content_is_not_rewritten():
    # MuPDF can infer a space from a large kerning gap. Such a display string
    # cannot be mapped byte-for-byte to the source and must remain read-only.
    base=spaced_source(2,3,-80);row=inspect_styled(base,[],0,[35,55,300,40])['runs'][0]
    assert not row['editable']
    with pytest.raises(DocumentError):replace_styled(base,[],0,[35,55,300,40],[{'id':row['id'],'text':'AVATAR'}])
