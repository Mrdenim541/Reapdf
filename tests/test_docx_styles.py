"""OOXML fixtures exercise styles and numbering through actual PDF output."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import unicodedata
import pymupdf as f
import pytest
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_import import source,document_xml

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
STYLES=f'''<w:styles xmlns:w="{W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:styleId="Base"><w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="180"/></w:pPr><w:rPr><w:b/><w:color w:val="245588"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:basedOn w:val="Base"/><w:rPr><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="List"><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="7"/></w:numPr></w:pPr></w:style>
<w:style w:type="character" w:styleId="Emphasis"><w:rPr><w:i/></w:rPr></w:style>
</w:styles>'''
NUMBERING=f'''<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="1">
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%1.%2)"/></w:lvl>
</w:abstractNum><w:num w:numId="7"><w:abstractNumId w:val="1"/></w:num><w:num w:numId="8"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="5"/></w:lvlOverride></w:num></w:numbering>'''

def fixture(paragraphs=None,styles=STYLES,numbering=NUMBERING):
    if paragraphs is None:
        paragraphs='''<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>Titulo heredado</w:t></w:r><w:r><w:rPr><w:b w:val="0"/><w:rStyle w:val="Emphasis"/></w:rPr><w:t> distinto</w:t></w:r></w:p>'''+''.join(list_p(text,level,num) for text,level,num in [('Primero',0,7),('Detalle',1,7),('Segundo',0,7),('Reiniciado',1,7),('Desde cinco',0,8)])
    replacements={'word/document.xml':document_xml('Inicio',paragraphs),'word/styles.xml':styles.encode(),'word/numbering.xml':numbering.encode()}
    output=BytesIO()
    with ZipFile(BytesIO(source())) as old,ZipFile(output,'w',ZIP_DEFLATED) as z:
        for name in old.namelist():z.writestr(name,replacements.pop(name,old.read(name)))
        for name,data in replacements.items():z.writestr(name,data)
    return output.getvalue()

def list_p(text,level=0,num=7):return f'<w:p><w:pPr><w:pStyle w:val="List"/><w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="{num}"/></w:numPr></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'

def extracted(pdf):
    with f.open(stream=pdf) as d:
        text=unicodedata.normalize('NFKC','\n'.join(p.get_text() for p in d))
        spans=[s for p in d for b in p.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']]
    return text,spans

def test_inherited_styles_character_styles_direct_override_and_list_restarts(tmp_path):
    pdf,report=import_docx(fixture());text,spans=extracted(pdf)
    assert report['styles_applied']==4 and report['list_items']==5 and report['text_check_passed']
    for marker in ['1. Primero','1.a) Detalle','2. Segundo','2.a) Reiniciado','5. Desde cinco']:assert marker in text
    title=next(s for s in spans if 'Titulo' in s['text']);assert title['flags']&16 and title['size']==18 and title['color']==0x245588
    special=next(s for s in spans if 'distinto' in s['text']);assert special['flags']&2 and not special['flags']&16 and special['size']==18
    # Independent text extraction catches rendered marker omissions.
    import shutil,subprocess
    if shutil.which('pdftotext'):
        path=tmp_path/'styles.pdf';path.write_bytes(pdf)
        assert '2.a) Reiniciado' in subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode()

@pytest.mark.parametrize('kind,markers',[('upperRoman',['I.','II.']),('lowerRoman',['i.','ii.']),('upperLetter',['A.','B.']),('lowerLetter',['a.','b.']),('bullet',['•','•'])])
def test_supported_numbering_formats(kind,markers):
    numbering=NUMBERING.replace('w:val="decimal"',f'w:val="{kind}"').replace('w:val="%1."','w:val="•"' if kind=='bullet' else 'w:val="%1."')
    pdf,r=import_docx(fixture(list_p('Uno')+list_p('Dos'),numbering=numbering));text,_=extracted(pdf)
    assert r['list_items']==2
    assert markers[0]+' Uno' in text and markers[1]+' Dos' in text

@pytest.mark.parametrize('change',['cycle','depth','duplicate','invalidxml','dtd'])
def test_invalid_style_graphs_and_parts_rejected(change):
    styles=STYLES
    if change=='cycle':styles=styles.replace('<w:basedOn w:val="Base"/>','<w:basedOn w:val="Title"/>')
    elif change=='depth':
        styles=f'<w:styles xmlns:w="{W}">'+''.join(f'<w:style w:type="paragraph" w:styleId="S{i}"><w:basedOn w:val="S{i+1}"/></w:style>' for i in range(34))+'<w:style w:type="paragraph" w:styleId="Title"><w:basedOn w:val="S0"/></w:style></w:styles>'
    elif change=='duplicate':styles=styles.replace('</w:styles>','<w:style w:type="paragraph" w:styleId="Title"/></w:styles>')
    elif change=='invalidxml':styles='<invalid'
    else:styles='<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///etc/passwd">]>'+styles
    with pytest.raises(DocumentError):import_docx(fixture(styles=styles))

@pytest.mark.parametrize('change',['absent','unsupported','restart','badlevel','missingancestor'])
def test_unsupported_numbering_is_reported_and_text_is_kept(change):
    numbering=NUMBERING;paragraph=list_p('Conservar contenido')
    if change=='absent':numbering=f'<w:numbering xmlns:w="{W}"/>'
    elif change=='unsupported':numbering=numbering.replace('w:val="decimal"','w:val="chicago"')
    elif change=='restart':numbering=numbering.replace('<w:start w:val="1"/>','<w:lvlRestart w:val="0"/><w:start w:val="1"/>')
    elif change=='badlevel':paragraph=list_p('Conservar contenido',9)
    else:numbering=numbering.replace('w:val="%1."','w:val="%3."')
    pdf,r=import_docx(fixture(paragraph,numbering=numbering));assert r['list_items']==0 and any('numeración/listas' in v for v in r['warnings'])
    assert 'Conservar contenido' in extracted(pdf)[0]

def test_word_style_toggle_semantics_and_direct_false():
    styles=STYLES.replace('<w:sz w:val="36"/>','<w:b/><w:sz w:val="36"/>')
    pdf,r=import_docx(fixture(styles=styles));assert not next(s for s in extracted(pdf)[1] if 'Titulo' in s['text'])['flags']&16
    styles=STYLES.replace('<w:sz w:val="36"/>','<w:b w:val="false"/><w:sz w:val="36"/>')
    pdf,r=import_docx(fixture(styles=styles));assert next(s for s in extracted(pdf)[1] if 'Titulo' in s['text'])['flags']&16

def test_list_inherited_num_id_and_explicit_disable():
    p=list_p('Heredada').replace('<w:numId w:val="7"/>','')+list_p('Sin numero',num=0)
    pdf,r=import_docx(fixture(p));text,_=extracted(pdf);assert '1. Heredada' in text and r['list_items']==1 and 'Sin numero' in text

@pytest.mark.parametrize('attribute',['w:before="-1"','w:before="bad"','w:before="999999"'])
def test_invalid_spacing_fails_before_pdf_is_adopted(attribute):
    with pytest.raises(DocumentError):import_docx(fixture(styles=STYLES.replace('w:before="120"',attribute)))


@pytest.mark.parametrize('marker',['○','▪','-','–'])
def test_supported_bullet_shape_is_preserved(marker):
    numbering=NUMBERING.replace('w:val="decimal"','w:val="bullet"').replace('w:val="%1."',f'w:val="{marker}"')
    pdf,r=import_docx(fixture(list_p('Texto'),numbering=numbering));assert marker+' Texto' in extracted(pdf)[0]


def test_duplicate_level_definitions_are_rejected():
    numbering=NUMBERING.replace('</w:abstractNum>','<w:lvl w:ilvl="0"/></w:abstractNum>')
    with pytest.raises(DocumentError,match='repetidos'):import_docx(fixture(numbering=numbering))


def test_default_paragraph_style_and_inherited_spacing_affect_layout():
    styles=STYLES.replace('w:styleId="Base"','w:styleId="Base" w:default="1"')
    pdf,r=import_docx(fixture(styles=styles));_,spans=extracted(pdf)
    start=next(s for s in spans if s['text']=='Inicio');assert start['flags']&16 and start['color']==0x245588
    assert start['bbox'][0]>150  # Centered by the default paragraph style.
    plain=styles.replace('w:before="120"','w:before="0"')
    _,without=extracted(import_docx(fixture(styles=plain))[0]);assert start['bbox'][1]>next(s for s in without if s['text']=='Inicio')['bbox'][1]+5
