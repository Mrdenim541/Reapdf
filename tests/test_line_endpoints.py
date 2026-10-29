import copy
import subprocess
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import DocumentError,export_pdf
from backend.existing_annotations import list_annotations
from backend.path_geometry import visible_paths
from tests.test_imported_paths import source


def edit(base,points=None,**changes):
    with f.open(stream=base) as d:
        p=d[0];row=list_annotations(d,0)['annotations'][0]
        points=points or [[100,150],[250,300]]
        return {'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'line_points':points,**changes}}


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_endpoints_change_direction_preserve_order_style_others_and_rotation(rotation,crop,reverse):
    base=source(rotation,crop,'line');points=[[100,150],[250,300]]
    if reverse:points.reverse()
    op=edit(base,points);saved=copy.deepcopy(op)
    with f.open(stream=base) as before,f.open(stream=export_pdf(base,[op])) as after:
        p=before[0];q=after[0];a=next(p.annots());b=next(q.annots());actual=visible_paths(q,b)[0]
        for expected,got in zip(points,actual):assert got==pytest.approx(expected,abs=.002)
        assert a.info==b.info and a.flags==b.flags and a.border==b.border
        assert a.line_ends==b.line_ends and a.colors==b.colors and a.opacity==b.opacity
        assert p.get_text()==q.get_text() and p.cropbox==q.cropbox and p.rotation==q.rotation
        assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
        assert list(p.annots())[1].rect==list(q.annots())[1].rect
    assert op==saved


@pytest.mark.parametrize('ending',range(10))
def test_all_native_line_endings_kept(ending):
    with f.open(stream=source(kind='line')) as d:
        p=d[0];a=next(p.annots());a.set_line_ends(ending,ending);a.update();base=d.tobytes()
    with f.open(stream=export_pdf(base,[edit(base)])) as d:
        p=d[0];assert next(p.annots()).line_ends==(ending,ending)


@pytest.mark.parametrize('points',[None,[],[[1,2]],[[1,2],[1,2]],[[1,2],[1.1,2]],[[False,30],[100,100]],[[-1,30],[100,100]],[[1,30],[100,900]],[[1,30],[float('nan'),90]],'invalid'])
def test_invalid_endpoints_rejected(points):
    base=source(kind='line');op=edit(base);op['changes']['line_points']=points
    with pytest.raises(DocumentError):export_pdf(base,[op])


@pytest.mark.parametrize('kind',['ink','note','mixed','outside_arrow','locked','signed','permission'])
def test_unsupported_shapes_permissions_and_actual_appearance_bounds(kind):
    base=source(kind='line');op=edit(base)
    if kind=='ink':base=source(kind='ink');op=edit(base)
    elif kind=='note':
        with f.open(stream=base) as d:op['xref']=list_annotations(d,0)['annotations'][1]['xref']
    elif kind=='mixed':op['changes']['path_rect']=[10,20,100,100]
    elif kind=='outside_arrow':op['changes']['line_points']=[[10,10],[499,649]]
    else:
        with f.open(stream=base) as d:
            if kind=='locked':
                p=d[0];a=next(p.annots());a.set_flags(a.flags|f.PDF_ANNOT_IS_LOCKED);base=d.tobytes()
            elif kind=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
            else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_COPY)
    with pytest.raises(DocumentError):export_pdf(base,[op])


def test_custom_appearance_allows_translation_but_rejects_direction_and_color():
    with f.open(stream=source(kind='line')) as d:
        p=d[0];a=next(p.annots());xref=int(d.xref_get_key(a.xref,'AP/N')[1].split()[0]);d.update_stream(xref,d.xref_stream(xref)+b'\n0 1 0 rg 90 410 20 15 re f\n');base=d.tobytes();points=visible_paths(p,a)[0]
    for changes in [{'line_points':[[100,150],[250,300]]},{'color':[.1,.5,.4]}]:
        op=edit(base);op['changes']=changes
        with pytest.raises(DocumentError,match='apariencia personalizada'):export_pdf(base,[op])
    op=edit(base,[[x+10,y+10] for x,y in points])
    with f.open(stream=base) as before,f.open(stream=export_pdf(base,[op])) as after:
        p=before[0];q=after[0];assert next(p.annots()).get_pixmap().samples==next(q.annots()).get_pixmap().samples


def test_batch_export_is_atomic_if_one_selected_mark_is_protected():
    base=source(kind='line')
    with f.open(stream=base) as d:
        p=d[0];note=list(p.annots())[1];note.set_flags(note.flags|f.PDF_ANNOT_IS_LOCKED);xref=note.xref;base=d.tobytes()
    good=edit(base);bad={'type':'existing_annot','page':0,'xref':xref,'action':'delete'}
    with pytest.raises(DocumentError):export_pdf(base,[good,bad])
    with f.open(stream=base) as d:
        p=d[0];assert visible_paths(p,next(p.annots()))[0]!=good['changes']['line_points'];assert len(list(p.annots()))==2


def test_api_project_and_independent_render(monkeypatch,tmp_path):
    from backend.projects import build_project,read_project
    base=source(90,True,'line');op=edit(base,[[100,120],[300,250]],color=[.6,.2,.1]);encoded,_=build_project(base,[op],{'name':'endpoints.pdf','page':0,'zoom':1});b,ops,_=read_project(encoded)
    output=export_pdf(b,ops);target=tmp_path/'endpoints.pdf';target.write_bytes(output)
    subprocess.run(['pdftoppm','-cropbox','-f','1','-l','1','-r','72','-singlefile','-png',str(target),str(tmp_path/'render')],capture_output=True,check=True)
    pix=f.Pixmap(str(tmp_path/'render.png'));assert pix.width==590 and pix.height==460
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'recovery'))
    with TestClient(app) as c:
        info=c.post('/api/documents',files={'file':('lines.pdf',base,'application/pdf')}).json();url=f"/api/documents/{info['id']}";r=c.get(url+'/pages/0').json()['annotations'][0];assert r['line_points'] and r['can_edit_endpoints']
        out=c.post(url+'/export',json={'operations':[op]});assert out.status_code==200
        with f.open(stream=out.content) as d:
            p=d[0];actual=visible_paths(p,next(p.annots()))[0]
            for a,e in zip(actual,op['changes']['line_points']):assert a==pytest.approx(e,abs=.002)
        assert c.get(url+'/pages/0').json()['annotations'][0]['line_points']==r['line_points']


def test_short_existing_line_can_move_with_group_without_changing_its_length():
    with f.open() as d:
        p=d.new_page();a=p.add_line_annot((80,150),(80.5,150));a.update();base=d.tobytes()
    op=edit(base,[[100,180],[100.5,180]])
    with f.open(stream=export_pdf(base,[op])) as d:
        p=d[0];assert visible_paths(p,next(p.annots()))[0]==[[100,180],[100.5,180]]
