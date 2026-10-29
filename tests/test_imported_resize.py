"""Imported path resizing is independent of appearance borders and arrowheads."""
import copy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf,DocumentError
from backend.existing_annotations import list_annotations
from backend.path_geometry import path_box,visible_paths
from tests.test_imported_paths import source


def edit(base,target=None,**extra):
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];box=row['path_rect']
        if target is None:target=[box[0]+10,box[1]+12,box[2]+40,box[3]+32]
        return {'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'path_rect':target,**extra}}


@pytest.mark.parametrize('kind',['ink','line'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_resize_native_points_keeps_style_identity_text_other_page_and_bounds(kind,rotation,crop):
    base=source(rotation,crop,kind);op=edit(base);saved=copy.deepcopy(op);output=export_pdf(base,[op])
    with f.open(stream=base) as before,f.open(stream=output) as after:
        p=before[0];q=after[0];a=next(p.annots());b=next(q.annots())
        row=list_annotations(after,0)['annotations'][0];assert row['can_resize']
        assert row['path_rect']==pytest.approx(op['changes']['path_rect'],abs=.002)
        old=path_box(p,a);target=op['changes']['path_rect']
        for old_path,new_path in zip(visible_paths(p,a),visible_paths(q,b)):
            assert len(old_path)==len(new_path)
            for v,w in zip(old_path,new_path):
                expected=[target[i]+(v[i]-old[i])*(target[i+2]-target[i])/(old[i+2]-old[i]) for i in [0,1]]
                assert w==pytest.approx(expected,abs=.002)
        assert a.info==b.info and a.flags==b.flags and a.border==b.border
        assert a.opacity==b.opacity and a.colors==b.colors and a.line_ends==b.line_ends
        assert p.rotation==q.rotation and p.cropbox==q.cropbox and p.get_text()==q.get_text()
        assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
        assert q.rect.contains(b.rect*q.rotation_matrix)
        assert list(p.annots())[1].info==list(q.annots())[1].info
    assert op==saved


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind',['ink','line'])
def test_path_box_move_preserves_original_appearance_bytes(rotation,kind):
    base=source(rotation,True,kind)
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];target=[v+(10 if i%2==0 else 12) for i,v in enumerate(row['path_rect'])]
    out=export_pdf(base,[edit(base,target)])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        p=a[0];q=b[0];old=next(p.annots());new=next(q.annots())
        x=int(a.xref_get_key(old.xref,'AP/N')[1].split()[0]);y=int(b.xref_get_key(new.xref,'AP/N')[1].split()[0])
        assert a.xref_stream(x)==b.xref_stream(y)
        assert old.get_pixmap().samples==new.get_pixmap().samples
        assert path_box(q,new)==pytest.approx(target,abs=.002)


def axis_source(axis,rotation):
    with f.open() as d:
        p=d.new_page(width=500,height=650)
        a=p.add_line_annot((120,200),(220,200) if axis=='horizontal' else (120,300))
        a.set_line_ends(0,f.PDF_ANNOT_LE_CLOSED_ARROW);a.set_border(width=2);a.update()
        p.set_cropbox(f.Rect(20,30,480,620));p.set_rotation(rotation);return d.tobytes()


@pytest.mark.parametrize('axis',['horizontal','vertical'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_axis_aligned_lines_resize_only_nonzero_dimension(axis,rotation):
    base=axis_source(axis,rotation)
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];old=row['path_rect'];target=old.copy();assert row['can_resize']
        zero=0 if old[0]==old[2] else 1
        target[3-zero]+=35
        invalid=target.copy();invalid[zero+2]+=5
    out=export_pdf(base,[edit(base,target)])
    with f.open(stream=out) as d:
        p=d[0];a=next(p.annots());assert path_box(p,a)==pytest.approx(target,abs=.001)
        assert a.line_ends==(0,f.PDF_ANNOT_LE_CLOSED_ARROW)
    with pytest.raises(DocumentError,match='dimensión cero'):export_pdf(base,[edit(base,invalid)])


@pytest.mark.parametrize('target',[None,[],[1,2,3],[False,10,100,200],[10,10,float('nan'),200],[-1,10,120,200],[20,20,510,200],[120,200,110,250],[60,170,60.5,200]])
def test_invalid_path_boxes_rejected(target):
    base=source();op=edit(base);op['changes']['path_rect']=target
    with pytest.raises(DocumentError):export_pdf(base,[op])


def test_mixed_geometry_wrong_type_and_special_properties_rejected():
    base=source();op=edit(base);op['changes']['rect']=[20,20,100,100]
    with pytest.raises(DocumentError):export_pdf(base,[op])
    with f.open(stream=base) as d:
        p=d[0];a=next(p.annots());d.xref_set_key(a.xref,'Measure','<</Type/Measure>>');special=d.tobytes()
    with pytest.raises(DocumentError):export_pdf(special,[edit(base)])
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][1]
    op=edit(base);op['xref']=row['xref']
    with pytest.raises(DocumentError):export_pdf(base,[op])


def test_custom_appearance_rejects_resize_but_still_moves_without_loss():
    with f.open(stream=source()) as d:
        p=d[0];a=next(p.annots());xref=int(d.xref_get_key(a.xref,'AP/N')[1].split()[0])
        d.update_stream(xref,d.xref_stream(xref)+b'\n0 1 0 rg 85 400 35 20 re f\n');base=d.tobytes()
    with pytest.raises(DocumentError,match='apariencia personalizada'):export_pdf(base,[edit(base)])
    with f.open(stream=base) as d:
        box=list_annotations(d,0)['annotations'][0]['path_rect'];target=[v+10 for v in box]
    out=export_pdf(base,[edit(base,target)])
    with f.open(stream=base) as a,f.open(stream=out) as b:
        p=a[0];q=b[0];assert next(p.annots()).get_pixmap().samples==next(q.annots()).get_pixmap().samples


def test_actual_arrowhead_must_fit_page_and_error_leaves_source_unchanged():
    base=source(kind='line');op=edit(base,[350,600,499,649]);original=bytes(base)
    with pytest.raises(DocumentError,match='borde|punta'):export_pdf(base,[op])
    assert base==original


def test_color_and_resize_together_then_serialization_and_project(tmp_path):
    from backend.projects import build_project,read_project
    base=source(270,True,'line');op=edit(base,color=[.1,.6,.3])
    out=export_pdf(base,[op])
    with f.open(stream=out) as d:
        p=d[0];a=next(p.annots());assert a.colors['stroke']==pytest.approx([.1,.6,.3]);assert path_box(p,a)==pytest.approx(op['changes']['path_rect'],abs=.002)
    # Projects already store the native annotation operation; no flattened copy.
    project,_=build_project(base,[op],{'name':'paths.pdf','page':0,'zoom':1})
    restored,ops,_=read_project(project)
    with f.open(stream=export_pdf(restored,ops)) as d:
        p=d[0];assert path_box(p,next(p.annots()))==pytest.approx(op['changes']['path_rect'],abs=.002)


def test_api_lists_paths_and_accepts_resize_without_modifying_original(monkeypatch,tmp_path):
    monkeypatch.setenv('REAPDF_DATA_DIR',str(tmp_path/'recovery'))
    with TestClient(app) as c:
        base=source();info=c.post('/api/documents',files={'file':('paths.pdf',base,'application/pdf')}).json();url=f"/api/documents/{info['id']}"
        data=c.get(url+'/pages/0').json()['annotations'][0];assert data['can_resize'] and len(data['paths'])==2
        op=edit(base);r=c.post(url+'/export',json={'operations':[op]});assert r.status_code==200
        with f.open(stream=r.content) as d:
            p=d[0];assert path_box(p,next(p.annots()))==pytest.approx(op['changes']['path_rect'],abs=.002)
        assert c.get(url+'/pages/0').json()['annotations'][0]['path_rect']==data['path_rect']
        op['changes']['path_rect'][0]=-1
        assert c.post(url+'/export',json={'operations':[op]}).status_code==422


def test_poppler_independently_renders_resized_path_at_expected_position(tmp_path):
    import subprocess
    base=source(kind='line');op=edit(base,[200,300,380,400]);out=export_pdf(base,[op]);target=tmp_path/'resized.pdf';target.write_bytes(out)
    subprocess.run(['pdftoppm','-f','1','-l','1','-r','72','-singlefile','-png',str(target),str(tmp_path/'render')],check=True,capture_output=True)
    pix=f.Pixmap(str(tmp_path/'render.png'));samples=pix.samples;found=[]
    for y in range(275,430):
        for x in range(175,410):
            at=(y*pix.width+x)*pix.n;r,g,b=samples[at:at+3]
            if r<220 and g>r+10 and b>g+10:found.append((x,y))
    assert len(found)>100
    with f.open(stream=out) as d:
        p=d[0];rect=next(p.annots()).rect
        assert all(rect.x0-2<=x<=rect.x1+2 and rect.y0-2<=y<=rect.y1+2 for x,y in found)
    text=subprocess.check_output(['pdftotext',str(target),'-']).decode()
    assert 'Contenido conservado' in text and 'Otra página intacta' in text


def test_almost_horizontal_line_moves_without_collapsing_and_can_resize():
    with f.open() as d:
        p=d.new_page(width=500,height=650);a=p.add_line_annot((80,200),(180,200.0003));a.update();base=d.tobytes()
    with f.open(stream=base) as d:
        p=d[0];box=path_box(p,next(p.annots()));assert 0<box[3]-box[1]<.001
    moved=[box[0]+10,box[1]+10,box[2]+10,box[3]+10]
    with f.open(stream=export_pdf(base,[edit(base,moved)])) as d:
        p=d[0];points=visible_paths(p,next(p.annots()))[0]
        assert 0<points[1][1]-points[0][1]<.001
    target=[80,200,200,220]
    with f.open(stream=export_pdf(base,[edit(base,target)])) as d:
        p=d[0];assert path_box(p,next(p.annots()))==pytest.approx(target,abs=.002)
