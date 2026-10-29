"""Resizing imported standard squares preserves identity, style and PDF content."""
import pymupdf as f
import pytest
from backend.engine import export_pdf,DocumentError
from backend.existing_annotations import list_annotations


def source(rotation=0,crop=False,kind='rectangle'):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((40,80),'Contenido original conservado')
        a=(p.add_rect_annot if kind=='rectangle' else p.add_circle_annot)(f.Rect(100,200,220,270));a.set_info(title='Autor',content='Rectángulo de revisión',subject='Prueba');a.set_colors(stroke=(.2,.4,.6),fill=(.95,.9,.8));a.set_border(width=2,dashes=[3,2]);a.set_opacity(.6);a.update()
        p.add_text_annot((350,350),'Nota conservada')
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((40,80),'Otra pagina');return d.tobytes()


@pytest.mark.parametrize('kind',['rectangle','ellipse'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_resize_moves_visible_box_exactly_and_keeps_identity_and_style(rotation,crop,kind):
    base=source(rotation,crop,kind)
    with f.open(stream=base) as before:
        page=before[0];row=list_annotations(before,0)['annotations'][0];assert row['can_resize']
        box=row['rect'];target=[box[0]+10,box[1]+10,box[2]+40,box[3]+30]
        out=export_pdf(base,[{'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'rect':target}}])
        with f.open(stream=out) as after:
            q=after[0];a=next(page.annots());b=next(q.annots())
            assert list_annotations(after,0)['annotations'][0]['rect']==pytest.approx(target,abs=.01)
            assert a.info==b.info and a.border==b.border and a.colors==b.colors and a.flags==b.flags and a.opacity==b.opacity
            assert before[0].get_text()==after[0].get_text()
            assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
            arow=list_annotations(before,0)['annotations'][1];brow=list_annotations(after,0)['annotations'][1]
            assert {k:v for k,v in arow.items() if k!='xref'}=={k:v for k,v in brow.items() if k!='xref'}
            assert before[0].rotation==after[0].rotation and before[0].cropbox==after[0].cropbox


@pytest.mark.parametrize('key,value',[('BE','<</S/C/I 2>>'),('IT','/SquareDimension'),('F','16'),('F','8')])
def test_special_square_geometry_is_not_resized(key,value):
    with f.open(stream=source()) as d:
        p=d[0];a=next(p.annots());xref=a.xref;d.xref_set_key(xref,key,value);base=d.tobytes()
    with f.open(stream=base) as d:row=list_annotations(d,0)['annotations'][0];assert not row['can_resize']
    box=row['rect'];box[2]+=20
    with pytest.raises(DocumentError):export_pdf(base,[{'type':'existing_annot','page':0,'xref':xref,'action':'update','changes':{'rect':box}}])


@pytest.mark.parametrize('box',[[10,10,15,15],[-1,30,80,90],[10,20,800,900],[10,20,False,100]])
def test_invalid_square_geometry_rejected(box):
    base=source()
    with f.open(stream=base) as d:xref=list_annotations(d,0)['annotations'][0]['xref']
    with pytest.raises(DocumentError):export_pdf(base,[{'type':'existing_annot','page':0,'xref':xref,'action':'update','changes':{'rect':box}}])


def test_note_cannot_be_resized_and_square_resize_requires_annotate_permission():
    base=source()
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][1];box=row['rect'];box[2]+=20
        locked=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_PRINT)
    with pytest.raises(DocumentError):export_pdf(base,[{'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'rect':box}}])
    with f.open(stream=locked) as d:row=list_annotations(d,0)['annotations'][0];assert not row['can_resize']
    with pytest.raises(DocumentError):export_pdf(locked,[{'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'rect':[120,200,300,310]}}])
