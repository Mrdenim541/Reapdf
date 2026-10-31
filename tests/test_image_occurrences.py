"""Real rendered checks of isolated image and nested shared Form edits."""
import base64
import pymupdf as f
import pytest
from backend.image_editing import image_model,edit_image
from backend.engine import DocumentError


def picture(value=130,alpha=False):
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,32,24),alpha);pix.clear_with(value)
    return pix.tobytes('png')


def fixture(*,forms=False,rotation=0,crop=False,affine=False,overlap=False,inherited=False):
    with f.open() as image_doc:
        p=image_doc.new_page(width=240,height=240);p.insert_text((20,30),'Preserve text')
        image=p.insert_image(f.Rect(40,60,120,120),stream=picture(alpha=True))
        if not forms:p.insert_image(f.Rect(40 if overlap else 140,60,120 if overlap else 220,120),xref=image)
        if affine:
            content=p.read_contents().replace(b'80 0 0 60 40 120 cm',b'70 20 -10 50 50 120 cm')
            x=image_doc.get_new_xref();image_doc.update_object(x,'<<>>');image_doc.update_stream(x,content);p.set_contents(x)
        with f.open() as d:
            if forms:
                p=d.new_page(width=600,height=650)
                p.show_pdf_page(f.Rect(30,30,270,270),image_doc,0)
                p.show_pdf_page(f.Rect(300,300,540,540),image_doc,0)
            else:
                d.insert_pdf(image_doc);p=d[0]
            if crop:p.set_cropbox(f.Rect(10,10,p.rect.width-10,p.rect.height-10))
            p.set_rotation(rotation)
            if inherited:
                kind,resources=d.xref_get_key(p.xref,'Resources');parent=int(d.xref_get_key(p.xref,'Parent')[1].split()[0])
                d.xref_set_key(parent,'Resources',resources);d.xref_set_key(p.xref,'Resources','null')
            d.new_page().insert_text((30,60),'Untouched page')
            return d.tobytes()


@pytest.mark.parametrize('forms',[False,True])
@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('action',['move','replace','delete'])
def test_shared_appearance_changes_once_and_preserves_other_pixels(forms,rotation,action):
    base=fixture(forms=forms,rotation=rotation,crop=True)
    with f.open(stream=base) as d:
        rows=image_model(d,0)['images'];assert len(rows)==2 and all(r['editable'] for r in rows)
        row=rows[0];other=rows[1];page=d[0];other_clip=f.Rect(other['rect'])
        other_pixels=page.get_pixmap(clip=other_clip).samples;other_page=d[1].get_pixmap().samples
        original_image=d.extract_image(row['xref'])['image'];original_text=page.get_text()
    x,y,x1,y1=row['rect'];box=[x+3,y+3,(x1-x)*.8,(y1-y)*.8]
    out=edit_image(base,[],0,row['xref'],action,box,base64.b64encode(picture(70)).decode(),row['occurrence'])
    with f.open(stream=out) as d:
        rows=image_model(d,0)['images'];assert len(rows)==(1 if action=='delete' else 2)
        assert d[0].get_text()==original_text
        assert d[0].get_pixmap(clip=other_clip).samples==other_pixels
        assert d[1].get_pixmap().samples==other_page
        if action=='move':
            changed=next(r for r in rows if r['rect']!=pytest.approx(other['rect']))
            assert changed['rect']==pytest.approx([box[0],box[1],box[0]+box[2],box[1]+box[3]],abs=.02)
            assert d.extract_image(changed['xref'])['image']==original_image


@pytest.mark.parametrize('action',['move','replace','delete'])
def test_overlapping_occurrences_select_by_identity(action):
    base=fixture(overlap=True)
    with f.open(stream=base) as d:rows=image_model(d,0)['images']
    assert rows[0]['occurrence']!=rows[1]['occurrence']
    with pytest.raises(DocumentError,match='comparte'):edit_image(base,[],0,rows[0]['xref'],action)
    out=edit_image(base,[],0,rows[1]['xref'],action,[42,62,60,40],base64.b64encode(picture(40)).decode(),rows[1]['occurrence'])
    with f.open(stream=out) as d:assert len(image_model(d,0)['images'])==(1 if action=='delete' else 2)


@pytest.mark.parametrize('forms',[False,True])
@pytest.mark.parametrize('action',['move','replace','delete'])
def test_inherited_resources_and_shared_forms_keep_fonts_and_other_uses(forms,action):
    base=fixture(forms=forms,inherited=True)
    with f.open(stream=base) as d:row=image_model(d,0)['images'][0];text=d[0].get_text();pixels=d[1].get_pixmap().samples
    r=row['rect'];out=edit_image(base,[],0,row['xref'],action,[r[0]+2,r[1]+2,60,40],base64.b64encode(picture(55)).decode(),row['occurrence'])
    with f.open(stream=out) as d:assert d[0].get_text()==text and d[1].get_pixmap().samples==pixels


@pytest.mark.parametrize('forms',[False,True])
def test_affine_image_keeps_orientation_and_other_appearance(forms):
    base=fixture(forms=forms,affine=True)
    with f.open(stream=base) as d:row=image_model(d,0)['images'][0];assert row['editable'],row['reason'];before=d[0].get_image_info(xrefs=True)[0]['transform']
    r=row['rect'];box=[r[0]+2,r[1]+2,(r[2]-r[0])*.8,(r[3]-r[1])*.8]
    out=edit_image(base,[],0,row['xref'],'move',box,occurrence=row['occurrence'])
    with f.open(stream=out) as d:
        transform=d[0].get_image_info(xrefs=True)[0]['transform']
        assert transform[:4]==pytest.approx([v*.8 for v in before[:4]],abs=.01)


def test_outside_form_clip_and_stale_occurrence_refuse_without_changing_source():
    base=fixture(forms=True)
    with f.open(stream=base) as d:row=image_model(d,0)['images'][0]
    with pytest.raises(DocumentError,match='recorte'):edit_image(base,[],0,row['xref'],'move',[400,30,60,40],occurrence=row['occurrence'])
    with pytest.raises(DocumentError,match='inexistente'):edit_image(base,[],0,row['xref'],'delete',occurrence='0'*64)
    with f.open(stream=base) as d:assert len(d[0].get_image_info())==2
