import copy
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.engine import export_pdf, DocumentError, spans
from backend.existing_annotations import list_annotations
from backend.pages import organize_pdf


def fixture(rotation=0):
    with f.open() as d:
        p=d.new_page(width=400,height=500);p.insert_text((40,80),'Texto original',fontsize=16)
        annotations=[p.add_text_annot((40,120),'Nota original ✓'),p.add_ink_annot([[(50,160),(100,180),(140,165)]]),
                     p.add_line_annot((50,210),(150,230)),p.add_rect_annot(f.Rect(50,260,160,300))]
        for method in [p.add_highlight_annot,p.add_underline_annot,p.add_strikeout_annot]:
            annotations.append(method(p.search_for('Texto',quads=True)))
        for a in annotations:
            a.set_info(title='Autor original',subject='Tema original',creationDate='D:20260101120000Z')
            a.set_opacity(.6);a.update()
        p.set_rotation(rotation);d.new_page(width=300,height=400).insert_text((40,80),'Otra pagina')
        return d.tobytes()


def patch(xref,**changes):
    return {'type':'existing_annot','page':0,'xref':xref,'action':'update','changes':changes}



@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_listing_rotations_identity_and_supported_types(rotation):
    with f.open(stream=fixture(rotation),filetype='pdf') as d:
        info=list_annotations(d,0);assert len(info['annotations'])==7 and not info['annotations_truncated']
        for item,a in zip(info['annotations'],d[0].annots()):
            assert item['xref']==a.xref
            assert item['rect']==list(a.rect*d[0].rotation_matrix)
            assert item['editable'] and item['visible']
            assert item['can_edit_content']==(a.type[0]==f.PDF_ANNOT_TEXT)
            assert item['author']=='Autor original'


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('number',range(7))
def test_color_change_preserves_native_identity_geometry_and_others(rotation,number):
    data=fixture(rotation)
    with f.open(stream=data,filetype='pdf') as before:
        p=before[0];original=list(p.annots());target=original[number]
        op=patch(target.xref,color=[.1,.3,.8]);pristine=copy.deepcopy(op)
        output=export_pdf(data,[op])
        with f.open(stream=output,filetype='pdf') as after:
            q=after[0];aa=list(q.annots())
            assert len(aa)==len(original)
            for index,(old,new) in enumerate(zip(original,aa)):
                assert new.info==old.info
                assert new.rect==old.rect and new.vertices==old.vertices
                assert new.flags==old.flags and new.border==old.border
                assert new.opacity==pytest.approx(old.opacity)
                assert new.type==old.type
                if index==number:assert new.colors['stroke']==pytest.approx([.1,.3,.8])
                else:assert new.colors==old.colors
            assert after[1].get_pixmap().samples==before[1].get_pixmap().samples
            assert after[0].get_text()==before[0].get_text()
        assert op==pristine


def test_note_content_keeps_author_identifier_popup_and_color_space():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=next(p.annots());a.set_colors(stroke=[.4]);a.update();xref=a.xref
        original_info=a.info;data=d.tobytes()
    output=export_pdf(data,[patch(xref,content='Comentario corregido\nÁrea: 20 m² ✓')])
    with f.open(stream=output,filetype='pdf') as d:
        p=d[0];a=next(p.annots())
        assert a.info['content']=='Comentario corregido\nÁrea: 20 m² ✓'
        assert a.info['title']==original_info['title'] and a.info['id']==original_info['id']
        assert a.popup_xref>0 and a.colors['stroke']==pytest.approx([.4])


def test_delete_removes_only_target_and_its_popup():
    data=fixture()
    with f.open(stream=data,filetype='pdf') as d:
        p=d[0];old_ids={a.info['id'] for a in p.annots()};note=next(p.annots());xref=note.xref;removed_id=note.info['id']
    out=export_pdf(data,[{'type':'existing_annot','page':0,'xref':xref,'action':'delete'}])
    with f.open(stream=out,filetype='pdf') as d:
        p=d[0];assert {a.info['id'] for a in p.annots()}==old_ids-{removed_id}
        assert all(kind!=f.PDF_ANNOT_POPUP for _,kind,_ in p.annot_xrefs())
        assert 'Texto original' in p.get_text()


@pytest.mark.parametrize('flag',[f.PDF_ANNOT_IS_READ_ONLY,f.PDF_ANNOT_IS_LOCKED,f.PDF_ANNOT_IS_LOCKED_CONTENTS])
def test_locked_annotations_are_listed_but_cannot_change_or_delete(flag):
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=next(p.annots());a.set_flags(a.flags|flag);xref=a.xref;data=d.tobytes()
        assert not list_annotations(d,0)['annotations'][0]['editable']
    for op in [patch(xref,color=[1,0,0]),{'type':'existing_annot','page':0,'xref':xref,'action':'delete'}]:
        with pytest.raises(DocumentError,match='bloqueada'):export_pdf(data,[op])


def test_replies_groups_and_optional_layers_are_protected():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=next(p.annots());parent=a.xref
        reply=p.add_text_annot((200,120),'Respuesta');reply.set_irt_xref(parent);child=reply.xref
        # Un vínculo de respuesta puede atravesar páginas: debe proteger al padre.
        q=d[1];cross=q.add_text_annot((100,100),'Otra respuesta');cross.set_irt_xref(parent)
        protected=[item for item in list_annotations(d,0)['annotations'] if item['xref'] in {parent,child}]
        assert all(not item['editable'] for item in protected)
        data=d.tobytes()
    with pytest.raises(DocumentError,match='conversaciones'):export_pdf(data,[patch(parent,content='Cambio')])
    with pytest.raises(DocumentError):export_pdf(data,[{'type':'existing_annot','page':0,'xref':child,'action':'delete'}])
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=next(p.annots());layer=d.add_ocg('Capa');a.set_oc(layer);xref=a.xref;data=d.tobytes()
        assert not list_annotations(d,0)['annotations'][0]['editable']
    with pytest.raises(DocumentError,match='capas'):export_pdf(data,[patch(xref,color=[1,0,0])])


def test_unsupported_censor_and_polyline_and_cross_page_xref_rejected():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=p.add_redact_annot(f.Rect(200,200,250,220));redact=a.xref
        a=p.add_polyline_annot([(200,250),(250,300),(260,280)]);circle=a.xref
        a=d[1].add_text_annot((50,100),'Otra');other=a.xref;data=d.tobytes()
        assert all(not item['editable'] for item in list_annotations(d,0)['annotations'] if item['xref'] in {redact,circle})
    for xref in [redact,circle,other,999999,True]:
        with pytest.raises(DocumentError):export_pdf(data,[patch(xref,color=[1,0,0])])


@pytest.mark.parametrize('changes',[{}, {'content':''},{'content':' '*3},{'content':'x'*4001},{'content':'a\x00b'},
 {'color':[True,0,0]},{'color':[float('nan'),0,0]},{'color':[2,0,0]},{'color':[1,0]}, {'rect':[0,0,20,20]}])
def test_invalid_changes_rejected(changes):
    data=fixture()
    with f.open(stream=data,filetype='pdf') as d:xref=next(d[0].annots()).xref
    with pytest.raises(DocumentError):export_pdf(data,[patch(xref,**changes)])


def test_duplicate_edits_and_non_note_content_rejected():
    data=fixture()
    with f.open(stream=data,filetype='pdf') as d:
        p=d[0];aa=list(p.annots());note,ink=aa[0].xref,aa[1].xref
    with pytest.raises(DocumentError):export_pdf(data,[patch(note,color=[1,0,0]),patch(note,content='Nuevo')])
    with pytest.raises(DocumentError):export_pdf(data,[patch(ink,content='Nuevo')])


def test_existing_changes_combine_with_text_session_marks_and_organization():
    data=fixture()
    with f.open(stream=data,filetype='pdf') as d:
        p=d[0];xref=next(p.annots()).xref;span=spans(p)[0]
    ops=[patch(xref,content='Nota actualizada'),{'type':'text','page':0,'span_id':span['id'],'text':'Texto nuevo'},
         {'type':'rectangle','page':0,'id':'new','points':[[200,320],[250,380]],'color':[1,0,0],'width':2}]
    output=organize_pdf(data,ops,[{'page':1,'rotation':0},{'page':0,'rotation':90}])
    with f.open(stream=output,filetype='pdf') as d:
        p=d[1];assert 'Texto nuevo' in p.get_text();assert len(list(p.annots()))==8
        assert next(p.annots()).info['content']=='Nota actualizada'
    # Una versión consolidada vuelve a ofrecer las anotaciones con sus identidades nuevas.
    with f.open(stream=output,filetype='pdf') as d:
        item=list_annotations(d,1)['annotations'][0]
    op=patch(item['xref'],content='Segunda edición');op['page']=1
    with f.open(stream=export_pdf(output,[op]),filetype='pdf') as d:
        p=d[1];assert next(p.annots()).info['content']=='Segunda edición'


@pytest.mark.parametrize('guard',['signed','permissions'])
def test_document_restrictions(guard):
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];xref=next(p.annots()).xref
        if guard=='signed':
            d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 1>>');data=d.tobytes()
        else:data=d.tobytes(encryption=f.PDF_ENCRYPT_AES_128,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_COPY)
    with f.open(stream=data,filetype='pdf') as d:assert not list_annotations(d,0)['annotations'][0]['editable']
    with pytest.raises(DocumentError):export_pdf(data,[patch(xref,content='Cambio')])


def test_existing_annotations_api_preview_export_and_source_integrity():
    data=fixture()
    with TestClient(app) as c:
        uploaded=c.post('/api/documents',files={'file':('anotado.pdf',data)}).json();base=f"/api/documents/{uploaded['id']}"
        item=c.get(base+'/pages/0').json()['annotations'][0]
        ops=[patch(item['xref'],content='Desde API ✓',color=[0,.5,1])]
        assert c.post(base+'/pages/0/preview',json={'operations':ops}).status_code==200
        exported=c.post(base+'/export',json={'operations':ops});assert exported.status_code==200
        with f.open(stream=exported.content,filetype='pdf') as d:
            p=d[0];a=next(p.annots());assert a.info['content']=='Desde API ✓'
        assert c.get(base+'/pages/0').json()['annotations'][0]['content']=='Nota original ✓'
        assert c.post(base+'/export',json={}).content==data
        ops[0]['xref']=999999
        assert c.post(base+'/export',json={'operations':ops}).status_code==422


def test_custom_arrow_border_fill_endings_and_opacity_are_preserved():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=list(p.annots())[2];a.set_line_ends(f.PDF_ANNOT_LE_CIRCLE,f.PDF_ANNOT_LE_CLOSED_ARROW)
        a.set_border(width=4,dashes=[3,2]);a.set_colors(stroke=[.2],fill=[0,.7,0]);a.update()
        xref=a.xref;original=(a.line_ends,a.border,a.colors['fill'],a.opacity,a.vertices);data=d.tobytes()
    with f.open(stream=export_pdf(data,[patch(xref,color=[.8,0,.5])]),filetype='pdf') as d:
        p=d[0];a=list(p.annots())[2]
        assert (a.line_ends,a.border,a.colors['fill'],a.opacity,a.vertices)==original


def test_hidden_annotation_is_listed_without_canvas_target_and_stays_hidden():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];a=next(p.annots());a.set_flags(a.flags|f.PDF_ANNOT_IS_HIDDEN);xref=a.xref;data=d.tobytes()
        assert not list_annotations(d,0)['annotations'][0]['visible']
        rendered=p.get_pixmap().samples
    with f.open(stream=export_pdf(data,[patch(xref,content='Oculta editada')]),filetype='pdf') as d:
        p=d[0];a=next(p.annots());assert a.flags&f.PDF_ANNOT_IS_HIDDEN
        assert p.get_pixmap().samples==rendered


def test_listing_truncation_is_explicit(monkeypatch):
    monkeypatch.setattr('backend.existing_annotations.MAX_LIST',2)
    with f.open(stream=fixture(),filetype='pdf') as d:
        info=list_annotations(d,0)
        assert len(info['annotations'])==2 and info['annotations_truncated']


def test_popups_and_form_fields_cannot_be_edited_as_review_annotations():
    with f.open(stream=fixture(),filetype='pdf') as d:
        p=d[0];popup=next(p.annots()).popup_xref
        w=f.Widget();w.field_name='Campo';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(200,220,280,250);p.add_widget(w)
        field=next(p.widgets()).xref;data=d.tobytes()
    for xref in [popup,field]:
        with pytest.raises(DocumentError):export_pdf(data,[patch(xref,color=[1,0,0])])
