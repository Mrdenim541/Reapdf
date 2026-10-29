"""Imported ink/line moves keep native geometry and appearance, not a flattened copy."""
import copy
import pymupdf as f
import pytest
from backend.engine import export_pdf,DocumentError
from backend.existing_annotations import list_annotations


def source(rotation=0,crop=False,kind='ink'):
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((50,80),'Contenido conservado')
        if kind=='ink':a=p.add_ink_annot([[(80,200),(120,225),(160,205)],[(90,245),(150,255)]])
        else:
            a=p.add_line_annot((80,200),(180,240));a.set_line_ends(f.PDF_ANNOT_LE_CIRCLE,f.PDF_ANNOT_LE_CLOSED_ARROW)
        a.set_info(title='Autor original',content='Revisar geometría',subject='Revisión');a.set_border(width=2,dashes=[3,2]);a.set_colors(stroke=(.2,.4,.6));a.set_opacity(.6);a.update()
        p.add_text_annot((350,350),'Nota intacta')
        if crop:p.set_cropbox(f.Rect(20,30,480,620))
        p.set_rotation(rotation);d.new_page().insert_text((50,80),'Otra página intacta');return d.tobytes()


def move(base,dx=10,dy=12):
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];target=[v+(dx if i%2==0 else dy) for i,v in enumerate(row['rect'])]
    return {'type':'existing_annot','page':0,'xref':row['xref'],'action':'update','changes':{'rect':target}}


@pytest.mark.parametrize('kind',['ink','line'])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('crop',[False,True])
def test_move_keeps_path_style_appearance_other_content_and_rotation(kind,rotation,crop):
    base=source(rotation,crop,kind);op=move(base);pristine=copy.deepcopy(op)
    with f.open(stream=base) as before,f.open(stream=export_pdf(base,[op])) as after:
        p=before[0];q=after[0];old=next(p.annots());new=next(q.annots())
        assert list_annotations(before,0)['annotations'][0]['can_move']
        assert list_annotations(before,0)['annotations'][0]['can_resize']
        assert list(new.rect*q.rotation_matrix)==pytest.approx(op['changes']['rect'],abs=.001)
        original=old.vertices if kind=='line' else [v for path in old.vertices for v in path]
        translated=new.vertices if kind=='line' else [v for path in new.vertices for v in path]
        for a,b in zip(original,translated):
            a=f.Point(a)*p.rotation_matrix;b=f.Point(b)*q.rotation_matrix
            assert tuple(b-a)==pytest.approx((10,12),abs=.001)
        assert old.info==new.info and old.flags==new.flags and old.border==new.border
        assert old.colors==new.colors and old.opacity==new.opacity and old.line_ends==new.line_ends
        old_ap=int(before.xref_get_key(old.xref,'AP/N')[1].split()[0]);new_ap=int(after.xref_get_key(new.xref,'AP/N')[1].split()[0])
        assert before.xref_stream(old_ap)==after.xref_stream(new_ap)
        assert old.get_pixmap().samples==new.get_pixmap().samples
        assert p.get_text()==q.get_text() and p.cropbox==q.cropbox and p.rotation==q.rotation
        assert before[1].get_pixmap().samples==after[1].get_pixmap().samples
        old_note=list(p.annots())[1];new_note=list(q.annots())[1];assert old_note.info==new_note.info and old_note.rect==new_note.rect
    assert op==pristine


@pytest.mark.parametrize('kind',['ink','line'])
def test_combined_move_and_color_keeps_vertices_and_endings(kind):
    base=source(90,True,kind);op=move(base);op['changes']['color']=[.7,.2,.3]
    with f.open(stream=base) as before,f.open(stream=export_pdf(base,[op])) as after:
        p=before[0];q=after[0];old=next(p.annots());new=next(q.annots())
        assert new.colors['stroke']==pytest.approx([.7,.2,.3]) and old.line_ends==new.line_ends
        assert list(new.rect*q.rotation_matrix)==pytest.approx(op['changes']['rect'],abs=.001)
        assert old.border==new.border and old.info==new.info


@pytest.mark.parametrize('key,value',[
 ('F','16'),('F','8'),('IT','/LineDimension'),('Measure','<</Type/Measure>>'),
 ('BE','<</S/C/I 2>>'),('A','<</S/URI/URI(https://example.org)>>'),('AA','<<>>'),('Path','[]'),
])
@pytest.mark.parametrize('kind',['ink','line'])
def test_special_geometries_cannot_move_but_remain_inspectable(key,value,kind):
    with f.open(stream=source(kind=kind)) as d:
        p=d[0];a=next(p.annots());d.xref_set_key(a.xref,key,value);base=d.tobytes()
    with f.open(stream=base) as d:
        row=list_annotations(d,0)['annotations'][0];assert not row['can_move'] and row['move_reason']
    with pytest.raises(DocumentError):export_pdf(base,[move(base)])


@pytest.mark.parametrize('kind',['ink','line'])
@pytest.mark.parametrize('invalid',['resize','tiny_resize','outside','locked','signed','permission'])
def test_invalid_geometry_permissions_and_signatures_rejected(kind,invalid):
    base=source(kind=kind);op=move(base)
    if invalid=='resize':op['changes']['rect'][2]+=20
    elif invalid=='tiny_resize':op['changes']['rect'][2]+=.01
    elif invalid=='outside':op['changes']['rect'][0]=-1
    else:
        with f.open(stream=base) as d:
            if invalid=='locked':
                p=d[0];a=next(p.annots());a.set_flags(a.flags|f.PDF_ANNOT_IS_LOCKED);base=d.tobytes()
            elif invalid=='signed':d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 3>>');base=d.tobytes()
            else:base=d.tobytes(encryption=f.PDF_ENCRYPT_AES_256,user_pw='',owner_pw='owner',permissions=f.PDF_PERM_COPY)
    with pytest.raises(DocumentError):export_pdf(base,[op])
