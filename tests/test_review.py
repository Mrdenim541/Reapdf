import copy
import pymupdf as f
import pytest
from backend.engine import export_pdf, DocumentError, spans
from backend.review import review_words


def source(rotation=0):
    with f.open() as doc:
        p=doc.new_page(width=400,height=500)
        p.insert_text((50,80),'Texto original',fontsize=16)
        p.insert_text((50,130),'Otra linea',fontsize=16)
        p.set_rotation(rotation)
        return doc.tobytes()


def markup(data,kind='highlight'):
    with f.open(stream=data,filetype='pdf') as doc:
        return dict(type=kind,page=0,color=[1,.8,0],quads=[w['quad'] for w in review_words(doc[0])])


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind,code',[('highlight',8),('underline',9),('strikeout',11)])
def test_markup_rotations_preserve_text_and_vertices(rotation,kind,code):
    data=source(rotation); op=markup(data,kind)
    with f.open(stream=data,filetype='pdf') as before, f.open(stream=export_pdf(data,[op]),filetype='pdf') as after:
        p=after[0]; a=next(p.annots())
        assert a.type[0]==code
        assert p.get_text()==before[0].get_text()
        assert p.rotation==rotation
        assert len(a.vertices)==16
        visible=[f.Point(v)*p.rotation_matrix for v in a.vertices]
        expected=[p for q in op['quads'] for p in q]
        for actual,expect in zip(visible,expected):
            assert tuple(actual)==pytest.approx(expect,abs=.001)
        assert len(review_words(p))==4


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_note_unicode_and_rotation(rotation):
    data=source(rotation)
    op=dict(type='note',page=0,point=[100,150],color=[1,.8,0],content='Revisar cálculo\nÁrea: 20 m² ✓')
    with f.open(stream=export_pdf(data,[op]),filetype='pdf') as doc:
        p=doc[0]; a=next(p.annots())
        assert a.type[0]==0
        assert a.info['content']==op['content']
        assert tuple(a.colors['stroke'])==pytest.approx(op['color'])
        assert len(list(p.annots()))==1
        assert 'Texto original' in p.get_text()


@pytest.mark.parametrize('change',[
    {'quads':[]},{'quads':[[[0,0]]*4]}, {'quads':[[[0,0],[40,0],[40,20],[0,20]]]},
    {'quads':[[[-1,0],[30,0],[0,20],[30,20]]]}, {'quads':[[[0,0],[30,0],[0,float('nan')],[30,20]]]},
    {'quads':[[[0,0],[30,0],[0,20],[30,20]]]*501}, {'color':[True,0,0]},
    {'quads':[[[0,0],[30,0],[0,20],[30,21]]]},
])
def test_reject_bad_markup(change):
    data=source();op=markup(data);op.update(change)
    with pytest.raises(DocumentError):export_pdf(data,[op])


@pytest.mark.parametrize('change',[
    {'content':''},{'content':' '*3},{'content':'a'*4001},{'content':'x\x00y'},
    {'point':[float('inf'),10]},{'point':[-1,20]},{'point':[395,495]},
])
def test_reject_bad_notes(change):
    op=dict(type='note',page=0,point=[100,150],color=[1,1,0],content='Nota');op.update(change)
    with pytest.raises(DocumentError):export_pdf(source(),[op])


def test_text_edit_before_markup_and_note():
    data=source()
    with f.open(stream=data,filetype='pdf') as doc: span=spans(doc[0])[0]
    operations=[markup(data),dict(type='text',page=0,span_id=span['id'],text='Texto nuevo'),
                dict(type='note',page=0,point=[100,200],color=[1,1,0],content='Comentario')]
    pristine=copy.deepcopy(operations)
    with f.open(stream=export_pdf(data,operations),filetype='pdf') as doc:
        p=doc[0]
        assert 'Texto nuevo' in p.get_text()
        assert 'Texto original' not in p.get_text()
        assert [a.type[0] for a in p.annots()]==[8,0]
    assert pristine==operations


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_cropped_page_markup_and_note_stay_inside(rotation):
    with f.open() as d:
        p=d.new_page(width=600,height=700)
        p.insert_text((150,180),'Texto visible')
        p.set_cropbox(f.Rect(100,100,500,600));p.set_rotation(rotation)
        data=d.tobytes()
    op=markup(data)
    note=dict(type='note',page=0,point=[150,150],color=[1,1,0],content='Nota recorte')
    with f.open(stream=export_pdf(data,[op,note]),filetype='pdf') as d:
        p=d[0];annotations=list(p.annots())
        assert 'Texto visible' in p.get_text()
        assert p.rect.contains(annotations[-1].rect*p.rotation_matrix)
        for actual,expect in zip(annotations[0].vertices,[v for q in op['quads'] for v in q]):
            assert tuple(f.Point(actual)*p.rotation_matrix)==pytest.approx(expect,abs=.001)


@pytest.mark.parametrize('kind',['highlight','underline','strikeout','note'])
def test_review_rejects_annotation_restrictions_and_signatures(kind):
    data=source();op=markup(data,kind)
    if kind=='note':op=dict(type=kind,page=0,point=[100,200],content='Nota',color=[1,1,0])
    with f.open(stream=data,filetype='pdf') as d:
        restricted=d.tobytes(encryption=f.PDF_ENCRYPT_AES_128,owner_pw='owner',user_pw='',permissions=f.PDF_PERM_COPY)
        d.xref_set_key(d.pdf_catalog(),'AcroForm','<</SigFlags 1>>')
        signed=d.tobytes()
    for guarded in [restricted,signed]:
        with pytest.raises(DocumentError):export_pdf(guarded,[op])


def test_review_annotations_survive_organization_and_merge():
    from backend.pages import organize_pdf
    from backend.merge import merge_pdf
    data=source();operations=[markup(data),dict(type='note',page=0,point=[100,200],color=[1,1,0],content='Nota conservada')]
    organized=organize_pdf(data,operations,[{'page':0,'rotation':90}])
    # La unión debe aceptar estos tipos sin aplanarlos ni perder la nota.
    merged=merge_pdf(organized,[],source(),[0],1,'Anexo')
    with f.open(stream=merged,filetype='pdf') as d:
        p=d[0]; aa=list(p.annots())
        assert [a.type[0] for a in aa]==[8,0]
        assert aa[1].info['content']=='Nota conservada'
        assert p.rotation==90 and len(d)==2


@pytest.mark.parametrize('rotation',[0,90,180,270])
@pytest.mark.parametrize('kind',['highlight','underline','strikeout'])
def test_partial_word_markup_keeps_exact_character_vertices(rotation,kind):
    from backend.review import review_selection
    data=source(rotation)
    with f.open(stream=data) as d:
        chars=review_selection(d[0])['characters'][1:4]
        assert ''.join(c['text'] for c in chars)=='ext'
        quad=[chars[0]['quad'][0],chars[-1]['quad'][1],chars[0]['quad'][2],chars[-1]['quad'][3]]
    op={'type':kind,'page':0,'quads':[quad],'color':[1,.8,0]}
    with f.open(stream=export_pdf(data,[op])) as d:
        p=d[0];a=next(p.annots());actual=[tuple(f.Point(v)*p.rotation_matrix) for v in a.vertices]
        for v,q in zip(actual,quad):assert v==pytest.approx(q,abs=.001)
        assert 'Texto original' in p.get_text() and len(a.vertices)==4
