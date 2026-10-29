from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pymupdf as f
import pytest
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_styles import fixture as styled,W
from tests.test_docx_import import document_xml


def cell(text='',span=1,vertical=None,horizontal=None):
    props=(f'<w:gridSpan w:val="{span}"/>' if span!=1 else '')+(f'<w:vMerge w:val="{vertical}"/>' if vertical else '')+(f'<w:hMerge w:val="{horizontal}"/>' if horizontal else '')
    return f'<w:tc><w:tcPr>{props}</w:tcPr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>'
def table(rows,columns=3):return '<w:tbl><w:tblGrid>'+('<w:gridCol w:w="2500"/>'*columns)+'</w:tblGrid>'+''.join('<w:tr>'+''.join(row)+'</w:tr>' for row in rows)+'</w:tbl>'
def combined_table():return table([[cell('Titulo combinado',3)],[cell('Vertical',vertical='restart'),cell('SuperiorA'),cell('SuperiorB')],[cell(vertical='continue'),cell('Inferior combinada',2)],[cell('PieA'),cell('PieB'),cell('PieC')]])
def fixture(content=None):
    base=styled();out=BytesIO()
    xml=document_xml('Informe de tabla',content or combined_table())
    with ZipFile(BytesIO(base)) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for name in old.namelist():z.writestr(name,xml if name=='word/document.xml' else old.read(name))
    return out.getvalue()

def test_horizontal_and_vertical_merges_keep_native_table_geometry_and_every_label(tmp_path):
    pdf,r=import_docx(fixture());assert r['tables']==1 and r['merged_tables']==1 and r['combined_cells']==3 and r['fallback_tables']==0 and r['cells']==9 and r['text_check_passed']
    with f.open(stream=pdf) as d:
        page=d[0];text=page.get_text();assert text.count('Vertical')==1
        for value in ['Titulo combinado','SuperiorA','SuperiorB','Inferior combinada','PieA','PieB','PieC']:assert value in text
        words={w[4]:w for w in page.get_text('words')}
        assert words['SuperiorA'][0]==pytest.approx(words['Inferior'][0],abs=.2)
        assert words['SuperiorA'][0]>words['Vertical'][0]+50 and words['SuperiorB'][0]>words['SuperiorA'][0]+50
        assert words['PieA'][0]==pytest.approx(words['Vertical'][0],abs=.2)
        assert words['Inferior'][1]>words['SuperiorA'][1] and page.get_drawings() and not page.get_images() and not page.get_xobjects()
    import shutil,subprocess
    if shutil.which('pdftotext'):
        path=tmp_path/'merged.pdf';path.write_bytes(pdf);assert 'SuperiorB' in subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode()


def test_legacy_horizontal_merge_keeps_text_of_every_physical_cell():
    content=table([[cell('Uno',horizontal='restart'),cell('Dos',horizontal='continue'),cell('Tres')],[cell('Cuatro'),cell('Cinco'),cell('Seis')]])
    pdf,r=import_docx(fixture(content));assert r['merged_tables']==1 and r['combined_cells']==1 and r['text_check_passed']
    with f.open(stream=pdf) as d:assert all(word in d[0].get_text() for word in ['Uno','Dos','Tres','Cuatro','Cinco','Seis'])

@pytest.mark.parametrize('rows',[
 [[cell('A',vertical='continue'),cell('B'),cell('C')]],
 [[cell('A',vertical='restart'),cell('B'),cell('C')],[cell('Texto retenido',vertical='continue'),cell('D'),cell('E')]],
 [[cell('A',2,vertical='restart'),cell('B')],[cell(vertical='continue'),cell('C'),cell('D')]],
 [[cell('A',horizontal='continue'),cell('B'),cell('C')]],
 [[cell('A'),cell('B')],[cell('C'),cell('D'),cell('E')]],
 [[cell('A',vertical='unknown'),cell('B'),cell('C')]],
])
def test_ambiguous_or_nonempty_continuations_fallback_without_losing_content(rows):
    pdf,r=import_docx(fixture(table(rows)));assert r['merged_tables']==0 and r['fallback_tables']==1 and r['text_check_passed']
    assert any('texto por filas' in w for w in r['warnings'])
    with f.open(stream=pdf) as d:
        text=''.join(p.get_text() for p in d)
        from xml.etree import ElementTree as E
        xml=E.fromstring(f'<root xmlns:w="{W}">{table(rows)}</root>')
        for node in xml.iter('{'+W+'}t'):
            if node.text:assert node.text in text

@pytest.mark.parametrize('span',[0,51,'bad'])
def test_invalid_merge_dimensions_rejected(span):
    with pytest.raises(DocumentError):import_docx(fixture(table([[cell('A',span),cell('B'),cell('C')]])))


def test_merged_table_in_header_repeats_and_reserves_space():
    from tests.test_docx_headers import fixture as header_fixture,texts
    header=f'<w:hdr xmlns:w="{W}">'+table([[cell('Cabecera',3)],[cell('Izquierda'),cell('Centro'),cell('Derecha')]])+'</w:hdr>'
    pdf,r=import_docx(header_fixture(overrides={'word/header1.xml':header}));assert r['merged_tables']==1 and r['text_check_passed']
    assert all('Cabecera' in t and 'Derecha' in t for t in texts(pdf))


def test_text_in_a_merged_cell_can_be_edited_after_import():
    from backend.paragraphs import paragraph_blocks,replace_paragraph
    pdf,_=import_docx(fixture());blocks=paragraph_blocks(pdf,[],0)['blocks']
    # Cell rules are outside the text region; the normal paragraph engine remains usable.
    item=next(b for b in blocks if b['text']=='Titulo combinado')
    result=replace_paragraph(pdf,[],0,item['box'],'Titulo corregido',auto_fit=True,min_size=6)
    with f.open(stream=result) as d:assert 'Titulo corregido' in d[0].get_text() and 'SuperiorA' in d[0].get_text()
