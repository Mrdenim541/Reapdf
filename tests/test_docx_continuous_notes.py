"""Synthetic logical note boundaries and physical continuous-column reserves."""
from io import BytesIO
from zipfile import ZipFile
import pymupdf as f
import pytest
from tests.test_docx_sections import properties,p,rewrite,W,R
from tests.test_docx_notes import source as notes,reference
from tests.test_docx_column_breaks import positions
from backend.docx_import import import_docx
from backend.engine import DocumentError


def fixture(*,restart='continuous',fmt='decimal',counts=(8,8,8),columns=(2,3,1),custom=False,end_position='docEnd',include_end=False):
    default=properties();props='<w:footnotePr><w:numFmt w:val="'+fmt+'"/><w:numStart w:val="3"/><w:numRestart w:val="'+restart+'"/></w:footnotePr>'
    props+='<w:endnotePr><w:numFmt w:val="lowerRoman"/><w:numStart w:val="2"/><w:numRestart w:val="eachSect"/><w:pos w:val="'+end_position+'"/></w:endnotePr>' if include_end else ''
    body=[];definitions=[];ends=[]
    for index,(count,col) in enumerate(zip(counts,columns),1):
        body.extend(p(f'S{index}ROW{row:03d}') for row in range(count))
        ref=reference('footnote',index,f'FOOTREF{index}MARK')
        if custom:ref=ref.replace(f'w:id="{index}"/>',f'w:id="{index}" w:customMarkFollows="1"/><w:t>*</w:t>')
        body.append(ref)
        if include_end:
            body.append(reference('endnote',index,f'ENDREF{index}MARK'));ends.append(f'<w:endnote w:id="{index}">{p(f"ENDNOTE{index}BODY")}</w:endnote>')
        section=default.replace('</w:sectPr>',f'<w:cols w:num="{col}" w:space="240" w:sep="1"/>'+props+'</w:sectPr>')
        if index>1:section=section.replace('nextPage','continuous')
        if index<len(columns):body.append('<w:p><w:pPr>'+section+'</w:pPr><w:r><w:t>SECTIONENDING'+str(index)+'</w:t></w:r></w:p>')
        else:body.append(section)
        definitions.append(f'<w:footnote w:id="{index}">{p(f"FOOTNOTE{index}BODY")}</w:footnote>')
    files={'word/document.xml':f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'+''.join(body)+'</w:body></w:document>','word/footnotes.xml':f'<w:footnotes xmlns:w="{W}">'+''.join(definitions)+'</w:footnotes>'}
    if include_end:files['word/endnotes.xml']=f'<w:endnotes xmlns:w="{W}">'+''.join(ends)+'</w:endnotes>'
    return rewrite(notes(),files)


def foot_labels(doc):
    # A note's label is an independent native link returning to its reference.
    values={}
    for page in doc:
        for link in page.get_links():
            if link['kind']!=f.LINK_GOTO:continue
            area=f.Rect(link['from']);text=page.get_textbox(area+(-.3,-.3,.3,.3)).strip()
            if text in ['3.','4.','5.','iii.','iv.','v.','*.']:values.setdefault(page.number,[]).append(text)
    return values


@pytest.mark.parametrize('restart',['continuous','eachPage','eachSect'])
@pytest.mark.parametrize('columns',[(1,2,3),(2,3,1),(4,2,3),(2,2,2)])
@pytest.mark.parametrize('counts',[(5,5,5),(80,80,80)])
def test_footnotes_match_physical_reference_pages_and_logical_numbering(restart,columns,counts):
    data=fixture(restart=restart,columns=columns,counts=counts);output,r=import_docx(data)
    assert r['footnotes']==3 and r['continuous_footnote_references']==3 and r['text_check_passed']
    with f.open(stream=output) as doc:
        for index in range(1,4):
            ref,note=positions(doc,[f'FOOTREF{index}MARK',f'FOOTNOTE{index}BODY']);assert ref[0]==note[0] and note[1].y0>ref[1].y1
            for word in doc[note[0]].get_text('words'):
                if word[4].startswith(('S1ROW','S2ROW','S3ROW','SECTIONENDING')):assert word[3]<note[1].y0
        text=''.join(page.get_text() for page in doc)
        for index,count in enumerate(counts,1):
            for row in range(count):assert text.count(f'S{index}ROW{row:03d}')==1
        labels=foot_labels(doc)
        if restart=='eachSect':assert sum(v.count('3.') for v in labels.values())==3
        elif restart=='continuous':assert sorted(v for values in labels.values() for v in values)==['3.','4.','5.']
        else:assert all('3.' in v for v in labels.values())
        assert all(not page.get_xobjects() for page in doc)


@pytest.mark.parametrize('position',['docEnd','sectEnd'])
def test_endnotes_are_at_document_or_original_logical_section_end(position):
    output,r=import_docx(fixture(include_end=True,end_position=position));assert r['endnotes']==3 and r['text_check_passed']
    with f.open(stream=output) as doc:
        text=''.join(page.get_text() for page in doc)
        assert all(text.count(f'ENDNOTE{i}BODY')==1 for i in range(1,4))
        if position=='sectEnd':assert text.index('ENDNOTE1BODY')<text.index('S2ROW000') and text.index('ENDNOTE2BODY')<text.index('S3ROW000')
        else:assert all(text.index(f'ENDNOTE{i}BODY')>text.index('S3ROW007') for i in range(1,4))
        assert len([l for page in doc for l in page.get_links() if l['kind']==f.LINK_GOTO])==12


@pytest.mark.parametrize('fmt',['decimal','lowerRoman','upperRoman','lowerLetter','upperLetter'])
def test_supported_note_numbering_formats_work_across_column_changes(fmt):
    output,r=import_docx(fixture(fmt=fmt));assert r['text_check_passed'] and r['footnotes']==3
    with f.open(stream=output) as doc:assert all(positions(doc,[f'FOOTNOTE{i}BODY']) for i in range(1,4))


def test_custom_marks_do_not_consume_counter_or_lose_return_links():
    output,r=import_docx(fixture(custom=True));assert r['custom_note_marks']==3 and r['text_check_passed']
    with f.open(stream=output) as doc:assert len([l for p in doc for l in p.get_links() if l['kind']==f.LINK_GOTO])==6


@pytest.mark.parametrize('restart',['continuous','eachSect'])
def test_note_counter_continues_to_a_later_noncontinuous_section(restart):
    from backend.docx_fields import number_label
    data=fixture(restart=restart,counts=(3,3,3))
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode();definitions=z.read('word/footnotes.xml').decode()
    # The last section starts a new physical group, while the first two stay continuous.
    end=xml.rfind('<w:type w:val="continuous"/>');xml=xml[:end]+xml[end:].replace('<w:type w:val="continuous"/>','<w:type w:val="nextPage"/>',1)
    output,r=import_docx(rewrite(data,{'word/document.xml':xml}));assert r['text_check_passed']
    with f.open(stream=output) as doc:
        labels=foot_labels(doc);assert sum(values.count('3.') for values in labels.values())==(3 if restart=='eachSect' else 1)
        assert positions(doc,['FOOTREF3MARK'])[0][0]>positions(doc,['FOOTREF2MARK'])[0][0]


def test_headers_and_page_numbers_remain_physical_across_continuous_notes():
    from tests.test_docx_sections import field,P
    data=fixture(counts=(75,75,75))
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode();rels=z.read('word/_rels/document.xml.rels').decode()
    xml=xml.replace('<w:sectPr>','<w:sectPr><w:headerReference w:type="default" r:id="commonheader"/>')
    rels=rels.replace('</Relationships>',f'<Relationship Id="commonheader" Type="{R}/header" Target="commonheader.xml"/></Relationships>')
    header=f'<w:hdr xmlns:w="{W}"><w:p><w:r><w:t>COMMONHEADER </w:t></w:r>{field("PAGE")}<w:r><w:t> / </w:t></w:r>{field("NUMPAGES")}</w:p></w:hdr>'
    output,r=import_docx(rewrite(data,{'word/document.xml':xml,'word/_rels/document.xml.rels':rels,'word/commonheader.xml':header}));assert r['text_check_passed']
    with f.open(stream=output) as doc:
        for index,page in enumerate(doc,1):assert f'COMMONHEADER {index} / {len(doc)}' in page.get_text()


def test_oversized_note_is_rejected_before_a_partial_pdf_is_returned():
    data=fixture()
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/footnotes.xml').decode()
    xml=xml.replace('FOOTNOTE2BODY','FOOTNOTE2BODY '+('LONGNOTEBODY '*1200))
    with pytest.raises(DocumentError,match='notas'):import_docx(rewrite(data,{'word/footnotes.xml':xml}))


def test_different_note_properties_still_require_a_separate_compatible_section():
    data=fixture()
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    first=xml.index('<w:numStart w:val="3"/>');second=xml.index('<w:numStart w:val="3"/>',first+1)
    xml=xml[:second]+xml[second:].replace('<w:numStart w:val="3"/>','<w:numStart w:val="5"/>',1)
    with pytest.raises(DocumentError,match='propiedades'):import_docx(rewrite(data,{'word/document.xml':xml}))


def test_import_api_and_export_reopen_keep_visible_notes_and_native_links():
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        response=client.post('/api/import/docx',data={'balance_columns':'true'},files={'file':('notes.docx',fixture(include_end=True,end_position='sectEnd'),'application/zip')});assert response.status_code==200,response.text
        result=response.json();assert result['report']['footnotes']==3 and result['report']['endnotes']==3 and result['report']['continuous_footnote_groups']==1
        output=client.post('/api/documents/'+result['document']['id']+'/export',json={'operations':[]});assert output.status_code==200
        with f.open(stream=output.content) as doc:assert len([l for page in doc for l in page.get_links() if l['kind']==f.LINK_GOTO])==12


def test_empty_last_continuous_section_does_not_drop_preceding_footnote_or_add_page():
    data=fixture(counts=(1,1,1))
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    # Add a final empty logical section with different columns.
    end=xml.rfind('<w:sectPr>');last=xml[end:xml.index('</w:sectPr>',end)+len('</w:sectPr>')]
    xml=xml[:end]+'<w:p><w:pPr>'+last+'</w:pPr><w:r><w:t>BEFOREEMPTYSECTION</w:t></w:r></w:p>'+last.replace('w:num="1"','w:num="4"')+'</w:body></w:document>'
    output,r=import_docx(rewrite(data,{'word/document.xml':xml}));assert r['text_check_passed'] and r['footnotes']==3 and r['section_count']==4
    with f.open(stream=output) as doc:assert len(doc)==1 and positions(doc,['FOOTREF3MARK'])[0][0]==positions(doc,['FOOTNOTE3BODY'])[0][0]


def test_empty_band_cannot_bypass_exhausted_page_budget():
    from backend.docx_balance import continuous_plan
    with pytest.raises(DocumentError,match='50 páginas'):
        continuous_plan([{'content':'','columns':{'widths':[200,200],'gaps':[20],'separator':False},'source_sections':[1]}],'',None,(500,700,40,40,40,40),0)
