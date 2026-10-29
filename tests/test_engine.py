import hashlib
import pymupdf as fitz
import pytest
from backend.engine import export_pdf, open_pdf, spans, DocumentError

@pytest.fixture
def source():
    doc=fitz.open()
    p=doc.new_page(width=400, height=500)
    p.draw_rect(fitz.Rect(30,40,300,115), fill=(.85,.85,.85), color=None)
    p.insert_text((50,80), 'Texto original', fontsize=16)
    p.insert_text((50,150), 'Contenido protegido', fontsize=12)
    p=doc.new_page(width=300,height=400)
    p.insert_text((30,70), 'Segunda pagina intacta', fontsize=12)
    data=doc.tobytes();doc.close();return data

def edit(source, text='Texto nuevo'):
    with open_pdf(source) as doc:
        span=spans(doc[0])[0]
    return {'type':'text','page':0,'span_id':span['id'],'text':text}

def ink(page=0):
    return {'type':'ink','page':page,'points':[[40,200],[80,230],[120,200]],'color':[1,0,0],'width':3}

def test_real_text_replacement_preserves_other_content_and_pixels(source):
    digest=hashlib.sha256(source).hexdigest()
    output=export_pdf(source,[edit(source)])
    with open_pdf(source) as original, open_pdf(output) as result:
        assert 'Texto original' not in result[0].get_text()
        assert 'Texto nuevo' in result[0].get_text()
        assert 'Contenido protegido' in result[0].get_text()
        assert len(result)==len(original)
        assert original[1].get_pixmap().samples==result[1].get_pixmap().samples
        a,b=original[0].get_pixmap(),result[0].get_pixmap()
        box=fitz.Rect(spans(original[0])[0]['bbox'])+(-2,-2,2,2)
        # Todos los píxeles fuera de la región de texto deben permanecer idénticos.
        for y in range(a.height):
            rowa=a.samples[y*a.stride:(y+1)*a.stride]
            rowb=b.samples[y*b.stride:(y+1)*b.stride]
            if y<box.y0 or y>box.y1:
                assert rowa==rowb
            else:
                assert rowa[:int(box.x0)*3]==rowb[:int(box.x0)*3]
                assert rowa[int(box.x1+1)*3:]==rowb[int(box.x1+1)*3:]
        # Eliminar la línea debe revelar el fondo gris, no un parche blanco.
    with open_pdf(export_pdf(source,[edit(source,'')])) as cleared:
        pixel=cleared[0].get_pixmap().pixel(60,75)
        assert pixel[0]==pixel[1]==pixel[2] and 210 <= pixel[0] <= 220
    assert hashlib.sha256(source).hexdigest()==digest

def test_ink_is_editable_annotation_not_flattened(source):
    with open_pdf(export_pdf(source,[ink()])) as doc:
        page=doc[0]; annotation=next(page.annots())
        assert annotation.type[0]==fitz.PDF_ANNOT_INK
        assert annotation.vertices[0]==[(40,200),(80,230),(120,200)]
        assert 'Texto original' in page.get_text()
        assert list(doc[1].annots() or [])==[]

def test_rotated_page_ink_coordinates(source):
    with open_pdf(source) as doc:
        doc[0].set_rotation(90); data=doc.tobytes()
    with open_pdf(export_pdf(data,[ink()])) as result:
        page=result[0];annotation=next(page.annots())
        points=[fitz.Point(*p)*page.rotation_matrix for p in annotation.vertices[0]]
        assert [(p.x,p.y) for p in points]==[(40,200),(80,230),(120,200)]

@pytest.mark.parametrize('replacement',['Una frase demasiado larga para el espacio disponible', 'Dos\nlineas', 'Emoji 😀'])
def test_rejects_unfit_text(source,replacement):
    with pytest.raises(DocumentError):export_pdf(source,[edit(source,replacement)])

def test_rejects_corrupt_and_encrypted_files(source):
    with pytest.raises(DocumentError):open_pdf(b'not a pdf')
    with open_pdf(source) as doc:
        encrypted=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,user_pw='secret',owner_pw='owner')
    with pytest.raises(DocumentError,match='contraseña'):open_pdf(encrypted)

def test_blocks_unsupported_fonts_and_pending_redactions(source):
    d=fitz.open();p=d.new_page();p.insert_text((50,50),'Simbolo',fontname='symb');data=d.tobytes();d.close()
    assert not spans(open_pdf(data)[0])[0]['editable']
    with pytest.raises(DocumentError,match='compatible'):export_pdf(data,[edit(data,'Cambio')])
    with open_pdf(source) as doc:
        doc[0].add_redact_annot(fitz.Rect(45,130,250,160));data=doc.tobytes()
    with pytest.raises(DocumentError,match='censuras pendientes'):export_pdf(data,[edit(data)])

@pytest.mark.parametrize('operation',[
    {'type':'unknown','page':0}, {'type':'ink','page':True},
    {'type':'text','page':0,'span_id':[],'text':'x'},
    {**ink(),'points':[[0,0],[9999,9999]]}, {**ink(),'width':float('nan')},
])
def test_invalid_operations(source,operation):
    with pytest.raises(DocumentError):export_pdf(source,[operation])

def test_duplicate_edit_rejected(source):
    with pytest.raises(DocumentError):export_pdf(source,[edit(source),edit(source)])

def test_export_without_operations_preserves_exact_bytes(source):
    assert export_pdf(source,[])==source

def test_document_with_signature_flags_is_not_rewritten(source):
    with open_pdf(source) as doc:
        doc.xref_set_key(doc.pdf_catalog(), "AcroForm", "<< /SigFlags 3 >>")
        data=doc.tobytes()
    assert export_pdf(data,[])==data
    with pytest.raises(DocumentError,match='firmados'):export_pdf(data,[ink()])

def test_edit_permissions_are_respected(source):
    with open_pdf(source) as doc:
        protected=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='',permissions=fitz.PDF_PERM_PRINT)
    with pytest.raises(DocumentError,match='modificar'):export_pdf(protected,[edit(source)])
    with pytest.raises(DocumentError,match='anotaciones'):export_pdf(protected,[ink()])

@pytest.mark.parametrize('kind', ['line', 'arrow', 'rectangle'])
@pytest.mark.parametrize('rotation', [0, 90, 180, 270])
@pytest.mark.parametrize('width', [.5, 3, 12])
def test_figures_preserve_geometry_in_rotated_pages(source, kind, rotation, width):
    with open_pdf(source) as doc:
        doc[0].set_rotation(rotation)
        data=doc.tobytes()
    op={**ink(), 'type':kind, 'points':[[70,200],[180,260]], 'width':width}
    with open_pdf(export_pdf(data,[op])) as result:
        page=result[0]; annotation=next(page.annots())
        if kind=='rectangle':
            assert annotation.type[0]==fitz.PDF_ANNOT_SQUARE
            # /RD identifica el margen entre /Rect y el borde real (PDF, no coordenadas de la interfaz).
            bbox=fitz.Rect(result.xref_get_key(annotation.xref,'Rect')[1].strip('[]').split())
            margins=list(map(float,result.xref_get_key(annotation.xref,'RD')[1].strip('[]').split()))
            bbox=bbox+(margins[0],margins[1],-margins[2],-margins[3])
            bbox=bbox*page.transformation_matrix*page.rotation_matrix
            assert tuple(bbox)==pytest.approx((70,200,180,260),abs=.1)
        else:
            assert annotation.type[0]==fitz.PDF_ANNOT_LINE
            actual=[fitz.Point(*p)*page.rotation_matrix for p in annotation.vertices]
            assert [(p.x,p.y) for p in actual]==[(70,200),(180,260)]
            if kind=='arrow':
                assert annotation.line_ends==(fitz.PDF_ANNOT_LE_NONE,fitz.PDF_ANNOT_LE_CLOSED_ARROW)
        assert annotation.colors['stroke']==[1,0,0]
        assert annotation.border['width']==width
        assert 'Texto original' in page.get_text()

@pytest.mark.parametrize('kind,points',[
    ('line',[[10,10],[10,10]]), ('arrow',[[10,10],[10.2,10.2]]),
    ('rectangle',[[10,10],[10,20]]), ('rectangle',[[10,10],[20,10]]),
    ('rectangle',[[10,10],[20,20],[30,30]]), ('line',[[0,0],[-1,20]]),
])
def test_invalid_figures_are_rejected(source,kind,points):
    with pytest.raises(DocumentError):
        export_pdf(source,[{**ink(),'type':kind,'points':points}])
