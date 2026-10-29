from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import pymupdf as f
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_headers import fixture as running_fixture,texts,W,p


def complex_field(instruction='PAGE',cached='777',style=''):
    split=len(instruction)//2
    return f'<w:r>{style}<w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve">{instruction[:split]}</w:instrText></w:r><w:r><w:instrText xml:space="preserve">{instruction[split:]}</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r>{style}<w:t>{cached}</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'

def rewrite(data,name,transform):
    out=BytesIO()
    with ZipFile(BytesIO(data)) as old,ZipFile(out,'w',ZIP_DEFLATED) as z:
        for path in old.namelist():z.writestr(path,transform(old.read(path)) if path==name else old.read(path))
    return out.getvalue()

def fixture(instruction='PAGE',start=1,fmt='decimal',cached='777',extra='',style=''):
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:r><w:t>Pagina </w:t></w:r>{complex_field(instruction,cached,style)}<w:r><w:t> Fin</w:t></w:r>{extra}</w:p></w:ftr>'
    data=running_fixture(overrides={'word/footer1.xml':footer})
    return rewrite(data,'word/document.xml',lambda xml:xml.replace(b'</w:sectPr>',f'<w:pgNumType w:start="{start}" w:fmt="{fmt}"/></w:sectPr>'.encode()))

@pytest.mark.parametrize('fmt,expected',[('decimal',['5','6']),('upperRoman',['V','VI']),('lowerRoman',['v','vi']),('upperLetter',['E','F']),('lowerLetter',['e','f'])])
def test_complex_page_fields_use_numbering_start_and_format(fmt,expected):
    pdf,r=import_docx(fixture(start=5,fmt=fmt));pages=texts(pdf);assert len(pages)==2
    assert r['complex_fields']==1 and r['complex_page_fields']==1 and r['page_fields']==1 and r['cached_fields']==0 and r['text_check_passed']
    for index,t in enumerate(pages):assert f'Pagina {expected[index]} Fin' in t and '777' not in t
    assert r['page_number_start']==5 and r['page_number_format']==fmt

@pytest.mark.parametrize('instruction,expected',[(r'PAGE \* ROMAN',['V','VI']),(r'PAGE \* roman',['v','vi']),(r'PAGE \* ALPHABETIC',['E','F']),(r'PAGE \* alphabetic',['e','f']),(r'PAGE \* Arabic \* MERGEFORMAT',['5','6']),(r'NUMPAGES \* ROMAN',['II','II']),(r'NUMPAGES \* roman \* CHARFORMAT',['ii','ii'])])
def test_numeric_switches_override_section_format_without_executing_other_code(instruction,expected):
    pdf,r=import_docx(fixture(instruction,start=5));pages=texts(pdf)
    for index,t in enumerate(pages):assert f'Pagina {expected[index]} Fin' in t
    assert r['complex_page_fields']==1 and r['text_check_passed']


def test_complex_boundaries_in_one_run_preserve_surrounding_text_and_style():
    props='<w:rPr><w:b/><w:sz w:val="18"/><w:color w:val="336699"/></w:rPr>'
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:r>{props}<w:t>Antes </w:t><w:fldChar w:fldCharType="begin"/><w:instrText> PA</w:instrText><w:instrText>GE </w:instrText><w:fldChar w:fldCharType="separate"/><w:t>777</w:t><w:fldChar w:fldCharType="end"/><w:t> Despues</w:t></w:r></w:p></w:ftr>'
    pdf,r=import_docx(running_fixture(overrides={'word/footer1.xml':footer}));assert r['complex_page_fields']==1 and r['text_check_passed']
    with f.open(stream=pdf) as d:
        assert 'Antes 1 Despues' in d[0].get_text()
        spans=[s for b in d[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if 'Antes' in s['text'] or s['text']=='1']
        assert spans and all(s['flags']&16 and s['color']==0x336699 and abs(s['size']-9)<.01 for s in spans)


def test_unsupported_outer_field_keeps_cached_inner_value_and_does_not_recalculate_it():
    inner=complex_field('PAGE','17')
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:r><w:fldChar w:fldCharType="begin"/><w:instrText>IF 1 = 1</w:instrText><w:fldChar w:fldCharType="separate"/></w:r>{inner}<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'
    pdf,r=import_docx(running_fixture(overrides={'word/footer1.xml':footer}));assert r['complex_fields']==2 and r['complex_page_fields']==0 and r['cached_fields']==2
    assert all('17' in t for t in texts(pdf)) and any('sin actualización' in v for v in r['warnings'])

@pytest.mark.parametrize('instruction',['DATE',r'PAGE \# 000',r'PAGE \* Unknown',r'PAGE \* ROMAN \* roman','INCLUDETEXT &quot;https://example.com&quot;'])
def test_unknown_commands_or_switches_use_saved_results(instruction):
    pdf,r=import_docx(fixture(instruction,cached='Guardado'));assert r['complex_page_fields']==0 and r['cached_fields']==1 and all('Guardado' in t for t in texts(pdf))

@pytest.mark.parametrize('content',[
 '<w:r><w:fldChar w:fldCharType="begin"/><w:instrText>PAGE</w:instrText></w:r>',
 '<w:r><w:fldChar w:fldCharType="end"/></w:r>',
 '<w:r><w:fldChar w:fldCharType="separate"/></w:r>',
 '<w:r><w:instrText>PAGE</w:instrText></w:r>',
 '<w:r><w:fldChar w:fldCharType="begin"/><w:fldChar w:fldCharType="separate"/><w:fldChar w:fldCharType="separate"/><w:fldChar w:fldCharType="end"/></w:r>',
 complex_field('X'*2001),
])
def test_incomplete_or_oversized_fields_rejected_before_storage(content):
    footer=f'<w:ftr xmlns:w="{W}"><w:p>{content}</w:p></w:ftr>'
    with TestClient(app) as c:
        before=set(app.state.root.glob('*.pdf'));r=c.post('/api/import/docx',files={'file':('campos.docx',running_fixture(overrides={'word/footer1.xml':footer}),'application/zip')})
        assert r.status_code==422,r.text
        assert set(app.state.root.glob('*.pdf'))==before

@pytest.mark.parametrize('start,fmt',[(0,'decimal'),(10000,'decimal'),('bad','decimal'),(4000,'upperRoman'),(1,'chicago')])
def test_invalid_section_numbering_is_rejected(start,fmt):
    with pytest.raises(DocumentError):import_docx(fixture(start=start,fmt=fmt))


def test_field_without_cached_result_uses_its_start_run_format():
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:r><w:rPr><w:i/><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="begin"/><w:instrText>PAGE</w:instrText><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>'
    pdf,r=import_docx(running_fixture(overrides={'word/footer1.xml':footer}));assert r['complex_page_fields']==1
    with f.open(stream=pdf) as d:
        spans=[s for b in d[0].get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['text']=='1'];assert spans and spans[0]['flags']&2 and spans[0]['size']==9


@pytest.mark.parametrize('fmt,labels',[('decimal',['5','6']),('upperRoman',['V','VI']),('lowerLetter',['e','f'])])
def test_pdf_page_labels_match_section_numbering_and_api_navigation(fmt,labels):
    pdf,r=import_docx(fixture(start=5,fmt=fmt));assert r['page_labels_preserved']
    with f.open(stream=pdf) as d:assert [p.get_label() for p in d]==labels
    with TestClient(app) as c:
        response=c.post('/api/import/docx',files={'file':('numero.docx',fixture(start=5,fmt=fmt),'application/zip')});assert response.status_code==200,response.text
        assert [p['label'] for p in response.json()['document']['pages']]==labels

@pytest.mark.parametrize('kind',['depth','count'])
def test_complex_field_resource_limits(kind):
    if kind=='count':content=complex_field()*501
    else:content='<w:r>'+('<w:fldChar w:fldCharType="begin"/>'*17)+('<w:fldChar w:fldCharType="end"/>'*17)+'</w:r>'
    footer=f'<w:ftr xmlns:w="{W}"><w:p>{content}</w:p></w:ftr>'
    with pytest.raises(DocumentError):import_docx(running_fixture(overrides={'word/footer1.xml':footer}))


def test_nested_instruction_does_not_turn_outer_field_into_a_page_command():
    content='<w:r><w:fldChar w:fldCharType="begin"/><w:instrText>PAGE</w:instrText></w:r>'+complex_field('PAGE','17')+'<w:r><w:fldChar w:fldCharType="separate"/><w:t>Guardado</w:t><w:fldChar w:fldCharType="end"/></w:r>'
    footer=f'<w:ftr xmlns:w="{W}"><w:p>{content}</w:p></w:ftr>'
    pdf,r=import_docx(running_fixture(overrides={'word/footer1.xml':footer}));assert r['complex_fields']==2 and r['complex_page_fields']==0 and all('Guardado' in t for t in texts(pdf))


def combined_fixture():
    from xml.etree import ElementTree as E
    from tests.test_docx_merged_tables import combined_table
    footer=f'<w:ftr xmlns:w="{W}"><w:p><w:r><w:t>Pagina </w:t></w:r>{complex_field("PAGE")}<w:r><w:t> de </w:t></w:r>{complex_field(r"NUMPAGES \* ROMAN")}</w:p></w:ftr>'
    data=running_fixture(overrides={'word/footer1.xml':footer})
    def change(xml):
        root=E.fromstring(xml);body=root.find('{'+W+'}body');body.find('.//{'+W+'}t').text='Informe combinado'
        wrapper=E.fromstring(f'<root xmlns:w="{W}">{combined_table()}</root>');body.insert(1,wrapper[0])
        para=E.Element('{'+W+'}p');run=E.SubElement(para,'{'+W+'}r');E.SubElement(run,'{'+W+'}t').text='Contenido revisado. '*400;body.insert(2,para)
        E.SubElement(body.find('{'+W+'}sectPr'),'{'+W+'}pgNumType',{'{'+W+'}start':'5','{'+W+'}fmt':'upperRoman'})
        return E.tostring(root,encoding='utf-8')
    return rewrite(data,'word/document.xml',change)


def test_combined_fields_numbering_labels_and_merged_table_work_together():
    pdf,r=import_docx(combined_fixture());assert r['complex_page_fields']==2 and r['merged_tables']==1 and r['combined_cells']==3 and r['page_labels_preserved'] and r['text_check_passed']
    with f.open(stream=pdf) as d:
        labels=['V','VI','VII','VIII','IX'];totals={2:'II',3:'III',4:'IV',5:'V'};assert 2<=len(d)<=5
        for i,page in enumerate(d):assert page.get_label()==labels[i] and f'Pagina {labels[i]} de {totals[len(d)]}' in page.get_text()
        assert 'Titulo combinado' in d[0].get_text() and 'Inferior combinada' in d[0].get_text()


@pytest.mark.parametrize('charformat',[True,False])
def test_charformat_uses_first_instruction_letter_while_mergeformat_keeps_cached_style(charformat):
    switch='CHARFORMAT' if charformat else 'MERGEFORMAT'
    code='<w:rPr><w:i/><w:sz w:val="18"/><w:color w:val="336699"/></w:rPr>'
    cached='<w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="AA2222"/></w:rPr>'
    body=f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r>{code}<w:instrText>PAGE \\* {switch}</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r>{cached}<w:t>777</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
    footer=f'<w:ftr xmlns:w="{W}"><w:p>{body}</w:p></w:ftr>'
    pdf,r=import_docx(running_fixture(overrides={'word/footer1.xml':footer}));assert r['complex_page_fields']==1
    with f.open(stream=pdf) as d:
        spans=[s for b in d[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if s['text']=='1'];assert len(spans)==1
        span=spans[0]
        if charformat:assert span['flags']&2 and not span['flags']&16 and span['size']==9 and span['color']==0x336699
        else:assert span['flags']&16 and span['size']==14 and span['color']==0xAA2222
