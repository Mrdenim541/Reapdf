"""PDF-native conversations, review state records, preservation and export safety."""
from io import StringIO
import csv,json
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.comments import inspect_comments,edit_comment,comment_report
from backend.existing_annotations import list_annotations
from backend.engine import DocumentError,export_pdf
from backend.projects import build_project,read_project


def source(rotation=0,crop=False,kind='note'):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Contenido conservado')
        a=p.add_text_annot((100,180),'Nota inicial ñ') if kind=='note' else p.add_rect_annot(f.Rect(100,180,200,230))
        a.set_info(title='Autor inicial',content='Nota inicial ñ',subject='Tema');a.update()
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((40,80),'Otra pagina');return d.tobytes()


def model(data):return inspect_comments(data,[])['comments']


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_native_reply_and_nested_reply_preserve_parent_and_other_page(rotation,crop):
    base=source(rotation,crop);root=model(base)[0]
    out=edit_comment(base,[],0,root['xref'],'reply','Revisar área: 20 m² ✓','Ana')
    rows=model(out);assert len(rows)==2 and rows[1]['parent']==rows[0]['xref'] and rows[1]['root']==rows[0]['xref'] and rows[1]['depth']==1
    out2=edit_comment(out,[],0,rows[1]['xref'],'reply','Corregido y revisado','Luis')
    rows2=model(out2);assert rows2[2]['parent']==rows2[1]['xref'] and rows2[2]['depth']==2 and len({v['root'] for v in rows2})==1
    with f.open(stream=base) as before,f.open(stream=out2) as after:
        assert before[0].get_text()==after[0].get_text() and before[1].get_pixmap().samples==after[1].get_pixmap().samples
        assert before[0].rotation==after[0].rotation and before[0].cropbox==after[0].cropbox
        assert not list_annotations(after,0)['annotations'][0]['editable']
        p=after[0];parent=next(p.annots());assert parent.info['title']=='Autor inicial' and parent.info['content']=='Nota inicial ñ'
    assert rows2[1]['author']=='Ana' and rows2[2]['author']=='Luis'


@pytest.mark.parametrize('state',['None','Accepted','Rejected','Cancelled','Completed'])
def test_state_is_native_string_hidden_and_does_not_change_page_pixels(state):
    base=source(kind='rectangle');root=model(base)[0]
    out=edit_comment(base,[],0,root['xref'],'state',author='Revisor',state=state)
    rows=model(out);assert rows[0]['status']==state and rows[1]['state']==state and not rows[1]['can_delete']
    with f.open(stream=base) as before,f.open(stream=out) as after:
        assert before[0].get_pixmap().samples==after[0].get_pixmap().samples
        assert after.xref_get_key(rows[1]['xref'],'StateModel')==('string','Review') and after.xref_get_key(rows[1]['xref'],'State')==('string',state)
    if state!='None':
        reset=edit_comment(out,[],0,rows[0]['xref'],'state',author='Revisor',state='None');assert model(reset)[0]['status']=='None'


def test_edit_metadata_on_rectangle_preserves_appearance_geometry_and_style():
    base=source(kind='rectangle');root=model(base)[0]
    out=edit_comment(base,[],0,root['xref'],'update','Comentario corregido','Ana Pérez')
    with f.open(stream=base) as a,f.open(stream=out) as b:
        assert a[0].get_pixmap().samples==b[0].get_pixmap().samples and a[1].get_pixmap().samples==b[1].get_pixmap().samples
        p=a[0];q=b[0];old=next(p.annots());new=next(q.annots());assert old.rect==new.rect and old.border==new.border and old.colors==new.colors
    assert model(out)[0]['content']=='Comentario corregido' and model(out)[0]['author']=='Ana Pérez'


def test_deletion_only_leaf_notes_replies_and_state_history_preserved():
    base=source();out=edit_comment(base,[],0,model(base)[0]['xref'],'reply','Respuesta','Ana');rows=model(out)
    assert not rows[0]['can_delete'] and rows[1]['can_delete']
    with pytest.raises(DocumentError):edit_comment(out,[],0,rows[0]['xref'],'delete')
    removed=edit_comment(out,[],0,rows[1]['xref'],'delete');assert len(model(removed))==1
    empty=edit_comment(removed,[],0,model(removed)[0]['xref'],'delete');assert model(empty)==[]
    state=edit_comment(base,[],0,model(base)[0]['xref'],'state',author='Ana',state='Completed')
    with pytest.raises(DocumentError):edit_comment(state,[],0,model(state)[1]['xref'],'update','Cambio','Ana')


@pytest.mark.parametrize('kind',['lock','layer','action','cycle','group','crosspage'])
def test_incompatible_conversations_are_read_only(kind):
    with f.open(stream=source()) as d:
        p=d[0];a=next(p.annots());xref=a.xref
        if kind=='lock':a.set_flags(a.flags|f.PDF_ANNOT_IS_LOCKED)
        elif kind=='layer':d.xref_set_key(xref,'OC','<</Type/OCG/Name(Capa)>>')
        elif kind=='action':d.xref_set_key(xref,'AA','<</E<</S/JavaScript/JS(app.alert(1))>>>>')
        elif kind=='cycle':d.xref_set_key(xref,'IRT',f'{xref} 0 R')
        else:
            q=d[1] if kind=='crosspage' else p;r=q.add_text_annot((50,100),'Respuesta');d.xref_set_key(r.xref,'IRT',f'{xref} 0 R')
            if kind=='group':d.xref_set_key(r.xref,'RT','/Group')
        base=d.tobytes()
    rows=model(base);assert all(not row['editable'] and row['reason'] for row in rows)
    with pytest.raises(DocumentError):edit_comment(base,[],0,xref,'reply','Nuevo','Ana')


@pytest.mark.parametrize('kwargs',[
 {'content':''},{'content':'x'*4001},{'content':'bad\x00'},{'author':'x'*101},{'author':'bad\nname'},
])
def test_invalid_content_or_author_rejected(kwargs):
    base=source();params={'content':'Respuesta','author':'Ana'}|kwargs
    with pytest.raises(DocumentError):edit_comment(base,[],0,model(base)[0]['xref'],'reply',**params)


def test_reports_are_copy_permission_aware_and_csv_neutralizes_formulas():
    base=source();base=edit_comment(base,[],0,model(base)[0]['xref'],'update','=1+2','@AUTOR')
    report=json.loads(comment_report(base,[]));assert report['schema']=='reapdf-review-1' and report['comments'][0]['content']=='=1+2'
    rows=list(csv.reader(StringIO(comment_report(base,[],'csv').decode('utf-8-sig'))));assert rows[1][6]=="'@AUTOR" and rows[1][7]=="'=1+2"
    with f.open(stream=base) as d:restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_ANNOTATE)
    assert model(restricted)[0]['editable']
    with pytest.raises(DocumentError):comment_report(restricted,[])


def test_api_history_project_and_source_unchanged():
    base=source()
    with TestClient(app) as client:
        doc=client.post('/api/documents',files={'file':('review.pdf',base,'application/pdf')}).json();url='/api/documents/'+doc['id']
        row=client.post(url+'/comments',json={}).json()['comments'][0]
        result=client.post(url+'/edit-comment',json={'page':0,'xref':row['xref'],'action':'reply','content':'Revisado','author':'Ana'})
        assert result.status_code==200 and len(client.post(url+'/comments',json={}).json()['comments'])==1
        report=client.post('/api/documents/'+result.json()['id']+'/comment-report',json={'format':'csv'});assert report.status_code==200 and 'Revisado' in report.content.decode('utf-8-sig')
    out=edit_comment(base,[],0,model(base)[0]['xref'],'reply','Revisado','Ana')
    project,_=build_project(out,[],{'name':'Revisión.pdf','page':0,'zoom':1,'base_changes':1});restored,ops,_=read_project(project)
    assert len(inspect_comments(restored,ops)['comments'])==2


def test_review_state_keeps_poppler_appearance_unchanged(tmp_path):
    import shutil,subprocess
    if not shutil.which('pdftoppm'):pytest.skip('Poppler no disponible')
    base=source(kind='rectangle');out=edit_comment(base,[],0,model(base)[0]['xref'],'state',author='Ana',state='Completed')
    images=[]
    for name,data in [('before',base),('after',out)]:
        path=tmp_path/(name+'.pdf');path.write_bytes(data);prefix=tmp_path/name
        subprocess.run(['pdftoppm','-f','1','-l','1','-scale-to','700','-singlefile','-png',str(path),str(prefix)],check=True,capture_output=True)
        images.append(prefix.with_suffix('.png').read_bytes())
    assert images[0]==images[1]
