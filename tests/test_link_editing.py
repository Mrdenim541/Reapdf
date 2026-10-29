"""Native link edits: visible geometry, destinations, preservation and API."""
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError
from backend.link_editing import inspect_links,edit_link


def source(rotation=0,crop=False):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Documento con enlaces')
        d.new_page(width=500,height=650).insert_text((40,80),'Destino interno')
        p=d[0];p.insert_link({'kind':f.LINK_URI,'from':f.Rect(50,100,200,130),'uri':'https://original.example/test'})
        p.insert_link({'kind':f.LINK_GOTO,'from':f.Rect(50,160,200,190),'page':1,'to':f.Point(0,50),'zoom':1.2})
        p=d.reload_page(p)
        xref=p.get_links()[0]['xref'];d.xref_set_key(xref,'Contents',f.get_pdf_str('Referencia conservada'));d.xref_set_key(xref,'NM','(enlace-identidad)')
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_move_resize_link_preserves_destination_metadata_other_links_and_pixels(rotation,crop):
    base=source(rotation,crop);rows=inspect_links(base,[],0)['links'];row=rows[0];box=row['box'];target=[box[0]+10,box[1]+10,box[2]+30,box[3]+20]
    out=edit_link(base,[],0,row['xref'],'update',{'box':target})
    updated=inspect_links(out,[],0)['links'];assert updated[0]['box']==pytest.approx(target,abs=.002)
    assert updated[0]['url']==row['url'] and updated[1]['box']==rows[1]['box']
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert before[0].rotation==after[0].rotation and before[0].cropbox==after[0].cropbox
        assert [p.get_pixmap().samples for p in before]==[p.get_pixmap().samples for p in after]
        old=before[0].get_links();new=after[0].get_links()
        for key in ['Contents','NM','A','Border']:
            assert before.xref_get_key(old[0]['xref'],key)==after.xref_get_key(new[0]['xref'],key)
        assert old[1]['to']==new[1]['to'] and old[1]['zoom']==new[1]['zoom']


@pytest.mark.parametrize('destination',['web','page'])
def test_destination_change_and_delete_are_native_and_keep_unrelated_link(destination):
    base=source(270,True);rows=inspect_links(base,[],0)['links'];index=0 if destination=='page' else 1
    changes={'destination':destination}|({'target_page':1} if destination=='page' else {'url':'https://nuevo.example/á?x=1&y=2'})
    out=edit_link(base,[],0,rows[index]['xref'],'update',changes)
    updated=inspect_links(out,[],0)['links'];assert updated[index]['destination']==destination
    assert updated[index]['box']==rows[index]['box'] and {k:v for k,v in updated[1-index].items() if k!='xref'}=={k:v for k,v in rows[1-index].items() if k!='xref'}
    if destination=='web':assert updated[index]['url']==changes['url']
    else:assert updated[index]['target_page']==1
    deleted=edit_link(out,[],0,updated[index]['xref'],'delete')
    assert len(inspect_links(deleted,[],0)['links'])==1


@pytest.mark.parametrize('changes',[
 {},{'box':[-1,0,10,20]},{'box':[0,0,1,1]},{'box':[0,0,1000,20]},{'box':[0,0,True,20]},
 {'destination':'web','url':'javascript:alert(1)'},{'destination':'web','url':'https://u:p@host.test'},
 {'destination':'web','url':'file:///tmp/a'},{'destination':'page','target_page':True},
 {'destination':'page','target_page':2},{'destination':'page','target_page':1,'url':'https://x.test'},
 {'url':'https://x.test'},{'unsupported':True},
])
def test_invalid_change_is_rejected(changes):
    base=source();xref=inspect_links(base,[],0)['links'][0]['xref']
    with pytest.raises(DocumentError):edit_link(base,[],0,xref,'update',changes)


@pytest.mark.parametrize('key,value',[
 ('AA','<</E<</S/JavaScript/JS(app.alert(1))>>>>'),('OC','<</Type/OCG/Name(Capa)>>'),
 ('F','128'),('A/Next','<</S/JavaScript/JS(app.alert(1))>>'),
])
def test_unsupported_actions_layers_and_locks_are_protected(key,value):
    base=source();xref=inspect_links(base,[],0)['links'][0]['xref']
    with f.open(stream=base) as d:d.xref_set_key(xref,key,value);data=d.tobytes()
    row=inspect_links(data,[],0)['links'][0];assert not row['editable'] and row['reason']
    for action in ['delete','update']:
        with pytest.raises(DocumentError):edit_link(data,[],0,xref,action,{'box':[20,20,80,40]} if action=='update' else None)


def test_modify_permission_and_encryption_are_respected():
    for permissions in [f.PDF_PERM_MODIFY,f.PDF_PERM_PRINT]:
        with f.open(stream=source()) as d:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=permissions)
        row=inspect_links(base,[],0)['links'][0]
        if permissions==f.PDF_PERM_PRINT:
            assert not row['editable']
            with pytest.raises(DocumentError):edit_link(base,[],0,row['xref'],'delete')
        else:
            out=edit_link(base,[],0,row['xref'],'update',{'destination':'web','url':'https://editado.example'})
            with f.open(stream=out) as d:assert d.metadata['encryption'] and d.permissions&f.PDF_PERM_MODIFY


def test_api_preview_does_not_apply_and_output_has_correct_destination():
    with TestClient(app) as client:
        base=source(90,True);doc=client.post('/api/documents',files={'file':('links.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        rows=client.post(url+'/inspect-links',json={'page':0}).json()['links'];payload={'page':0,'xref':rows[0]['xref'],'action':'update','changes':{'destination':'page','target_page':1}}
        preview=client.post(url+'/edit-link',json=payload|{'preview':True});assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
        assert client.post(url+'/inspect-links',json={'page':0}).json()['links']==rows
        applied=client.post(url+'/edit-link',json=payload);assert applied.status_code==200
        newurl='/api/documents/'+applied.json()['id'];result=client.post(newurl+'/inspect-links',json={'page':0}).json()['links']
        assert result[0]['destination']=='page' and result[0]['target_page']==1
