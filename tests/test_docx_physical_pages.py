import pytest
import pymupdf as f
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_columns import source
from tests.test_docx_column_breaks import positions
from tests.test_docx_sections import rewrite,properties,p,W,R,base


def inline(labels,kinds):
    return '<w:p><w:hyperlink w:anchor="dest"><w:r><w:rPr><w:b/><w:color w:val="214EAA"/></w:rPr>'+''.join('<w:t>'+label+'</w:t>'+(f'<w:br w:type="{kinds[i]}"/>' if i<len(kinds) else '') for i,label in enumerate(labels))+'</w:r></w:hyperlink></w:p><w:p><w:bookmarkStart w:id="1" w:name="dest"/><w:r><w:t>DESTINATION</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'


@pytest.mark.parametrize('count',[1,2,3,4])
@pytest.mark.parametrize('initial_columns',[0,1,3])
def test_mixed_page_and_column_breaks_route_physical_pages_and_keep_link_style(count,initial_columns):
    labels=[f'MARK{i}END' for i in range(initial_columns+4)];kinds=['column']*initial_columns+['page','column','page']
    out,r=import_docx(source(f'<w:cols w:num="{count}" w:space="240"/>',body=inline(labels,kinds)))
    logical=0;expected=[logical]
    for kind in kinds:
        logical=logical+1 if kind=='column' else (logical//count+1)*count;expected.append(logical)
    with f.open(stream=out) as d:
        located=positions(d,labels);c=r['sections'][0]['columns'];left=r['sections'][0]['margins'][0]
        for (page,rect),frame in zip(located,expected):
            assert page==frame//count
            assert rect.x0==pytest.approx(left+sum(c['widths'][:frame%count])+sum(c['gaps'][:frame%count]),abs=1)
        assert len(d)==expected[-1]//count+1 and r['physical_page_breaks_verified']==2
        target=positions(d,['DESTINATION'])[0][0];links=[l for page in d for l in page.get_links() if l['kind']==f.LINK_GOTO];assert len(links)==len(labels) and all(l['page']==target for l in links)
        spans=[s for page in d for block in page.get_text('dict')['blocks'] for line in block.get('lines',[]) for s in line['spans'] if 'MARK' in s['text']];assert spans and all('Bold' in s['font'] and s['color']==0x214eaa for s in spans)


@pytest.mark.parametrize('count',[2,3,4])
@pytest.mark.parametrize('breaks',[1,2,3])
def test_leading_consecutive_page_breaks_keep_whole_blank_pages(count,breaks):
    body='<w:p><w:r>'+'<w:br w:type="page"/>'*breaks+'<w:t>AFTERBLANKS</w:t></w:r></w:p>'
    out,r=import_docx(source(f'<w:cols w:num="{count}" w:space="240"/>',body=body))
    with f.open(stream=out) as d:
        assert len(d)==breaks+1 and positions(d,['AFTERBLANKS'])[0][0]==breaks
        assert all(not page.get_text().strip() for page in list(d)[:breaks])


def test_first_page_break_before_and_disabled_before_do_not_add_blank_pages():
    body='<w:p><w:pPr><w:pageBreakBefore/></w:pPr><w:r><w:t>FIRSTMARK</w:t></w:r></w:p><w:p><w:pPr><w:pageBreakBefore w:val="0"/></w:pPr><w:r><w:t>SECONDMARK</w:t></w:r></w:p>'
    out,r=import_docx(source(body=body))
    with f.open(stream=out) as d:assert len(d)==1 and positions(d,['FIRSTMARK','SECONDMARK'])[0][0]==0


@pytest.mark.parametrize('count',[2,3,4])
def test_footnotes_reserve_the_physical_page_after_skipping_columns(count):
    from tests.test_docx_notes import source as notes,reference
    body=p('BEFOREFIRSTPAGE')+inline(['FIRSTLINK','SECONDLINK'],['page'])+reference('footnote',1,'AFTERPAGEREF')+p('Content after reference. '*80)
    out,r=import_docx(notes(body=body,options=f'<w:cols w:num="{count}" w:space="240"/>'))
    with f.open(stream=out) as d:
        ref,note=positions(d,['AFTERPAGEREF','FOOTNOTEALPHA']);assert ref[0]==note[0]==1 and note[1].y0>ref[1].y1
        assert r['text_check_passed'] and r['footnotes']==1


def continuous(body1=None,body2=None,*,cols=2,second=None):
    section=properties().replace('</w:sectPr>',f'<w:cols w:num="{cols}" w:space="240"/></w:sectPr>');last=second or section.replace('nextPage','continuous')
    ending=(body1 or '<w:r><w:t>SECTIONFIRST</w:t></w:r>')
    xml=f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body><w:p><w:pPr>{section}</w:pPr>{ending}</w:p>'+(body2 or p('SECTIONSECOND'))+last+'</w:body></w:document>'
    return rewrite(base(),{'word/document.xml':xml})


@pytest.mark.parametrize('cols',[1,2,3,4])
def test_identical_continuous_sections_continue_on_same_page_without_extra_paragraph(cols):
    out,r=import_docx(continuous(cols=cols));assert r['section_count']==2 and r['layout_section_count']==1 and r['continuous_sections_merged']==1 and r['sections'][0]['source_sections']==[1,2]
    with f.open(stream=out) as d:
        a,b=positions(d,['SECTIONFIRST','SECTIONSECOND']);assert len(d)==1 and a[0]==b[0]==0 and a[1].x0==b[1].x0 and b[1].y0>a[1].y1


@pytest.mark.parametrize('option',['geometry','number','title','notes'])
def test_continuous_sections_with_incompatible_effects_remain_atomic(option):
    second=properties(kind='continuous',start=3 if option=='number' else None,title=option=='title',landscape=option=='geometry').replace('</w:sectPr>','<w:cols w:num="2" w:space="240"/>'+('<w:footnotePr/>' if option=='notes' else '')+'</w:sectPr>')
    with pytest.raises(DocumentError,match='continuas'):import_docx(continuous(second=second))


def test_unequal_columns_and_page_breaks_do_not_reuse_the_previous_width():
    cols='<w:cols w:num="2" w:equalWidth="0"><w:col w:w="3600" w:space="480"/><w:col w:w="5666"/></w:cols>'
    out,r=import_docx(source(cols,body=inline(['ALPHAFIRST','BETASECOND','GAMMATHIRD'],['column','page'])))
    with f.open(stream=out) as d:
        a,b,c=positions(d,['ALPHAFIRST','BETASECOND','GAMMATHIRD']);assert a[0]==b[0]==0 and c[0]==1 and a[1].x0==c[1].x0<b[1].x0


def test_page_break_before_inherited_from_style_starts_a_physical_page():
    body=p('BEFORESTYLE')+'<w:p><w:pPr><w:pStyle w:val="BreakStyle"/></w:pPr><w:r><w:t>AFTERSTYLE</w:t></w:r></w:p>'
    data=rewrite(source(body=body),{'word/styles.xml':f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:styleId="BreakStyle"><w:pPr><w:pageBreakBefore/></w:pPr></w:style></w:styles>'})
    out,r=import_docx(data)
    with f.open(stream=out) as d:assert len(d)==2 and positions(d,['AFTERSTYLE'])[0][0]==1


@pytest.mark.parametrize('kind',['page','before'])
def test_table_physical_breaks_do_not_silently_split_or_clip_cells(kind):
    para='<w:p>'+('<w:pPr><w:pageBreakBefore/></w:pPr>' if kind=='before' else '')+'<w:r>'+('<w:br w:type="page"/>' if kind=='page' else '')+'<w:t>INCELL</w:t></w:r></w:p>'
    with pytest.raises(DocumentError,match='tablas'):import_docx(source(body='<w:tbl><w:tr><w:tc>'+para+'</w:tc></w:tr></w:tbl>'))


def test_physical_page_limit_rejects_excessive_breaks():
    with pytest.raises(DocumentError,match='50 páginas'):import_docx(source(body='<w:p><w:r>'+('<w:br w:type="page"/>'*50)+'<w:t>AFTERLIMIT</w:t></w:r></w:p>'))


def test_continuous_section_with_unchanged_header_page_field_uses_physical_page_count():
    from tests.test_docx_sections import P,field
    from io import BytesIO
    from zipfile import ZipFile
    data=continuous(body2=inline(['CONTINUED','NEXTPAGE'],['page']))
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    xml=xml.replace('<w:sectPr>','<w:sectPr><w:headerReference w:type="default" r:id="sameheader"/>',1)
    files={'word/document.xml':xml,'word/_rels/document.xml.rels':f'<Relationships xmlns="{P}"><Relationship Id="sameheader" Type="{R}/header" Target="header1.xml"/></Relationships>','word/header1.xml':f'<w:hdr xmlns:w="{W}"><w:p><w:r><w:t>HEADER </w:t></w:r>{field("PAGE")}<w:r><w:t> / </w:t></w:r>{field("NUMPAGES")}</w:p></w:hdr>'}
    out,r=import_docx(rewrite(data,files));assert r['continuous_sections_merged']==1
    with f.open(stream=out) as d:assert len(d)==2 and 'HEADER 1 / 2' in d[0].get_text() and 'HEADER 2 / 2' in d[1].get_text()


@pytest.mark.parametrize('split',[False,True])
def test_sectionpages_header_requires_logical_section_layout_instead_of_merging(split):
    from tests.test_docx_sections import P
    data=continuous();header=f'<w:hdr xmlns:w="{W}"><w:p><w:r><w:instrText>SECTION</w:instrText></w:r><w:r><w:instrText>PAGES</w:instrText></w:r></w:p></w:hdr>' if split else f'<w:hdr xmlns:w="{W}"><w:p><w:fldSimple w:instr="SECTIONPAGES"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:hdr>'
    # The instruction may be stored as an attribute, not only text.
    with pytest.raises(DocumentError,match='continuas'):import_docx(rewrite(data,{'word/header1.xml':header}))


def test_api_import_saves_and_reopens_mixed_physical_flow_without_losing_original():
    from fastapi.testclient import TestClient
    from backend.app import app
    from scripts.create_word_manual_columns_sample import create
    data=create()
    with TestClient(app) as client:
        resp=client.post('/api/import/docx',files={'file':('mixed.docx',data,'application/zip')});assert resp.status_code==200;v=resp.json();assert v['report']['pages']==4 and v['report']['continuous_sections_merged']==1
        result=client.post('/api/documents/'+v['document']['id']+'/export',json={'operations':[]});assert result.status_code==200
        with f.open(stream=result.content) as d:assert len(d)==4 and positions(d,['PHYSICALPAGELEFT','NEXTWHOLEPAGE'])[1][0]==3


def test_continuous_chain_retains_all_source_sections_and_order_across_columns():
    from io import BytesIO
    from zipfile import ZipFile
    data=continuous()
    with ZipFile(BytesIO(data)) as z:xml=z.read('word/document.xml').decode()
    last=properties(kind='continuous').replace('</w:sectPr>','<w:cols w:num="2" w:space="240"/></w:sectPr>')
    xml=xml.replace(last,'<w:p><w:pPr>'+last+'</w:pPr><w:r><w:t>SECONDENDING</w:t></w:r></w:p>'+p('CHAINLAST')+last)
    out,r=import_docx(rewrite(data,{'word/document.xml':xml}));assert r['section_count']==3 and r['sections'][0]['source_sections']==[1,2,3] and r['continuous_sections_merged']==2
    with f.open(stream=out) as d:
        text=''.join(page.get_text() for page in d);labels=['SECTIONFIRST','SECTIONSECOND','SECONDENDING','CHAINLAST'];assert [text.index(s) for s in labels]==sorted(text.index(s) for s in labels)


def test_long_paragraph_after_physical_break_can_continue_through_remaining_columns():
    body=p('INITIALPAGE')+'<w:p><w:r><w:br w:type="page"/><w:t>'+('CONTINUECONTENT '*700)+'</w:t></w:r></w:p>'
    out,r=import_docx(source(body=body));assert r['text_check_passed']
    with f.open(stream=out) as d:
        assert len(d)>=3 and d[0].get_text().strip()=='INITIALPAGE'
        assert sum(page.get_text().count('CONTINUECONTENT') for page in d)==700
        left=r['sections'][0]['margins'][0];columns=r['sections'][0]['columns'];boundary=left+columns['widths'][0]+columns['gaps'][0]
        assert {rect.x0>=boundary-1 for rect in d[1].search_for('CONTINUECONTENT')}=={False,True}
        assert all(any(rect.x0>=x-.5 and rect.x1<=x+width+.5 for x,width in [(left,columns['widths'][0]),(boundary,columns['widths'][1])]) for rect in d[1].search_for('CONTINUECONTENT'))
