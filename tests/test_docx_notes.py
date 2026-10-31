from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
import unicodedata
import pymupdf as f
import pytest
from backend.docx_import import import_docx
from backend.engine import DocumentError
from tests.test_docx_headers import fixture as header_source,W,R,P


def p(text):return '<w:p><w:r><w:t>'+text+'</w:t></w:r></w:p>'
def reference(kind,ident,label):return '<w:p><w:r><w:t>'+label+'</w:t><w:'+kind+'Reference w:id="'+str(ident)+'"/></w:r></w:p>'


def source(body=None,foot='FOOTNOTEALPHA contiene detalle tecnico.',end='ENDNOTEBETA conserva la conclusion.',options='',overrides=None):
    if body is None:body=reference('footnote',1,'FootRefAlpha')+p('Texto de cuerpo y contenido principal. '*60)+reference('endnote',2,'EndRefBeta')
    doc=f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'+body+'<w:sectPr><w:headerReference w:type="default" r:id="h"/><w:footerReference w:type="default" r:id="f"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:left="720" w:right="720" w:top="720" w:bottom="720"/>'+options+'</w:sectPr></w:body></w:document>'
    files={'word/document.xml':doc,'word/footnotes.xml':f'<w:footnotes xmlns:w="{W}" xmlns:r="{R}"><w:footnote w:id="-1" w:type="separator"><w:p/></w:footnote><w:footnote w:id="1"><w:p><w:r><w:footnoteRef/><w:t>'+foot+'</w:t></w:r></w:p></w:footnote></w:footnotes>',
     'word/endnotes.xml':f'<w:endnotes xmlns:w="{W}" xmlns:r="{R}"><w:endnote w:id="2">'+p(end)+'</w:endnote></w:endnotes>'}
    old=header_source(body='BASE')
    with ZipFile(BytesIO(old)) as z:
        rels=z.read('word/_rels/document.xml.rels').decode().replace('</Relationships>',f'<Relationship Id="fn" Type="{R}/footnotes" Target="footnotes.xml"/><Relationship Id="en" Type="{R}/endnotes" Target="endnotes.xml"/></Relationships>');files['word/_rels/document.xml.rels']=rels
    files.update(overrides or {});out=BytesIO()
    with ZipFile(BytesIO(old)) as z,ZipFile(out,'w',ZIP_DEFLATED) as target:
        for name in z.namelist():target.writestr(name,files.pop(name,z.read(name)))
        for name,data in files.items():target.writestr(name,data)
    return out.getvalue()


def test_notes_are_native_selectable_bottom_footnotes_and_editable_endnotes_with_return_links():
    pdf,report=import_docx(source());assert report['footnotes']==1 and report['endnotes']==1 and report['note_references']==2 and report['text_check_passed']
    with f.open(stream=pdf) as d:
        text='\n'.join(p.get_text() for p in d);assert 'FOOTNOTEALPHA' in text and 'ENDNOTEBETA' in text
        refs=[p.number for p in d if p.search_for('FootRefAlpha')];pages=[p.number for p in d if p.search_for('FOOTNOTEALPHA')];assert refs==pages
        page=d[pages[0]];note=page.search_for('FOOTNOTEALPHA')[0];footer=page.search_for('Pagina')[0];assert note.y0>page.rect.height*.6 and note.y1<footer.y0
        links=[link for p in d for link in p.get_links() if link['kind']==f.LINK_GOTO];assert len(links)>=4 and all(0<=l['page']<len(d) for l in links)
        assert not any(p.get_images() for p in d)


@pytest.mark.parametrize('fill',[70,100,140,180])
def test_footnote_follows_its_reference_after_repagination(fill):
    body=p('Texto anterior de prueba. '*fill)+reference('footnote',1,'NEARBOUNDARY')+p('Texto posterior de prueba. '*100)
    pdf,report=import_docx(source(body=body,foot='FOOTNOTEALPHA '+('Nota extensa conservada. '*5)));assert report['text_check_passed']
    with f.open(stream=pdf) as d:
        ref=next(p for p in d if p.search_for('NEARBOUNDARY'));note=next(p for p in d if p.search_for('FOOTNOTEALPHA'));assert ref.number==note.number
        foot=note.search_for('FOOTNOTEALPHA')[0]
        central=[f.Rect(s['bbox']) for b in note.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if s['text'].startswith(('Texto anterior','Texto posterior','NEARBOUNDARY'))]
        assert central and max(r.y1 for r in central)<foot.y0


def test_endnote_can_span_pages_without_losing_content():
    end='ENDNOTEBETA '+('Texto de nota final. '*600)+' LASTENDTOKEN';pdf,report=import_docx(source(body=reference('endnote',2,'EndRefBeta'),end=end));assert report['text_check_passed'] and report['endnotes']==1
    with f.open(stream=pdf) as d:assert len(d)>1 and 'LASTENDTOKEN' in ''.join(p.get_text() for p in d)


def test_note_relationships_are_scoped_and_hyperlinks_remain_clickable():
    note=f'<w:footnotes xmlns:w="{W}" xmlns:r="{R}"><w:footnote w:id="1"><w:p><w:hyperlink r:id="web"><w:r><w:t>NOTEWEBLINK</w:t></w:r></w:hyperlink></w:p></w:footnote></w:footnotes>'
    rel=f'<Relationships xmlns="{P}"><Relationship Id="web" Type="{R}/hyperlink" Target="https://example.com/note" TargetMode="External"/></Relationships>'
    pdf,report=import_docx(source(overrides={'word/footnotes.xml':note,'word/_rels/footnotes.xml.rels':rel}));assert report['text_check_passed']
    with f.open(stream=pdf) as d:assert any(l.get('uri')=='https://example.com/note' for p in d for l in p.get_links())


@pytest.mark.parametrize('kind',['missing','duplicate','nested','revision','external','eachPage','custom','oversize','xml','count'])
def test_unsupported_or_incomplete_notes_are_rejected_before_a_partial_pdf(kind):
    kwargs={};body=None
    if kind=='missing':body=reference('footnote',9,'MISSING')
    elif kind=='duplicate':body=reference('footnote',1,'ONE')+reference('footnote',1,'TWO')
    elif kind=='nested':kwargs={'foot':'</w:t><w:footnoteReference w:id="1"/><w:t>NESTED'}
    elif kind=='revision':kwargs={'foot':'</w:t></w:r><w:del><w:r><w:t>deleted</w:t></w:r></w:del><w:r><w:t>bad'}
    elif kind=='external':kwargs={'overrides':{'word/_rels/document.xml.rels':f'<Relationships xmlns="{P}"><Relationship Id="fn" Type="{R}/footnotes" Target="https://example.com/file" TargetMode="External"/></Relationships>'}}
    elif kind=='eachPage':kwargs={'options':'<w:endnotePr><w:numRestart w:val="eachPage"/></w:endnotePr>'}
    elif kind=='custom':body=reference('footnote',1,'MARK').replace('w:id="1"','w:id="1" w:customMarkFollows="1"')
    elif kind=='oversize':kwargs={'foot':'A long footnote. '*500}
    elif kind=='xml':kwargs={'overrides':{'word/footnotes.xml':'<!DOCTYPE x><broken>'}}
    elif kind=='count':kwargs={'overrides':{'word/footnotes.xml':f'<w:footnotes xmlns:w="{W}">'+''.join(f'<w:footnote w:id="{n}">{p("x")}</w:footnote>' for n in range(204))+'</w:footnotes>'}}
    with pytest.raises(DocumentError):import_docx(source(body=body,**kwargs))


def test_notes_survive_pdf_edit_and_project_persistence():
    from backend.paragraphs import paragraph_blocks,replace_paragraph
    from backend.projects import build_project,read_project
    pdf,report=import_docx(source());blocks=paragraph_blocks(pdf,[],0)['blocks'];body=next(b for b in blocks if b['text'].startswith('Texto de cuerpo'))
    edited=replace_paragraph(pdf,[],0,body['box'],'Contenido central corregido.',size=12)
    archive,_=build_project(edited,[],{'name':'WithNotes.pdf','page':0,'zoom':1,'base_changes':1});base,ops,_=read_project(archive)
    with f.open(stream=base) as d:assert 'Contenido central corregido.' in d[0].get_text() and any(p.search_for('FOOTNOTEALPHA') for p in d) and any(p.search_for('ENDNOTEBETA') for p in d) and any(l['kind']==f.LINK_GOTO for p in d for l in p.get_links())


def test_multiple_sections_restart_numbering_and_preserve_cross_page_links():
    body=reference('footnote',1,'SECTIONONE')+'<w:p><w:pPr><w:sectPr><w:footnotePr><w:numFmt w:val="upperRoman"/><w:numStart w:val="3"/><w:numRestart w:val="eachSect"/></w:footnotePr></w:sectPr></w:pPr><w:r><w:t>FIRSTSECTIONEND</w:t></w:r></w:p>'+reference('footnote',3,'SECTIONTWO')+reference('endnote',2,'ENDOFSECOND')
    feet=f'<w:footnotes xmlns:w="{W}"><w:footnote w:id="1">{p("FIRSTFOOTDATA")}</w:footnote><w:footnote w:id="3">{p("SECONDFOOTDATA")}</w:footnote></w:footnotes>'
    pdf,report=import_docx(source(body=body,options='<w:footnotePr><w:numFmt w:val="upperRoman"/><w:numStart w:val="3"/><w:numRestart w:val="eachSect"/></w:footnotePr>',overrides={'word/footnotes.xml':feet}));assert report['section_count']==2 and report['footnotes']==2 and report['text_check_passed']
    with f.open(stream=pdf) as d:
        for ref,note in [('SECTIONONE','FIRSTFOOTDATA'),('SECTIONTWO','SECONDFOOTDATA')]:assert next(p.number for p in d if p.search_for(ref))==next(p.number for p in d if p.search_for(note))
        assert len([l for p in d for l in p.get_links() if l['kind']==f.LINK_GOTO])>=6


def test_note_image_uses_its_own_local_relationships():
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,20,20));pix.clear_with(120)
    a='http://schemas.openxmlformats.org/drawingml/2006/main';wp='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    note=f'<w:footnotes xmlns:w="{W}" xmlns:r="{R}" xmlns:a="{a}" xmlns:wp="{wp}"><w:footnote w:id="1">{p("IMAGEFOOTNOTE")}<w:p><w:r><w:drawing><a:blip r:embed="pic"/><wp:extent cx="254000" cy="254000"/></w:drawing></w:r></w:p></w:footnote></w:footnotes>'
    rel=f'<Relationships xmlns="{P}"><Relationship Id="pic" Type="{R}/image" Target="media/note.png"/></Relationships>'
    pdf,report=import_docx(source(overrides={'word/footnotes.xml':note,'word/_rels/footnotes.xml.rels':rel,'word/media/note.png':pix.tobytes('png')}));assert report['text_check_passed'] and report['images']>=1
    with f.open(stream=pdf) as d:assert any(p.get_images() for p in d)


def test_reference_does_not_hide_adjacent_source_words_split_by_styling():
    body='<w:p><w:r><w:t>com</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>patible</w:t><w:footnoteReference w:id="1"/></w:r></w:p>'
    pdf,report=import_docx(source(body=body));assert report['text_check_passed']
    with f.open(stream=pdf) as d:assert 'compatible' in d[0].get_text()


def test_note_reference_in_unsupported_wrapper_cannot_be_silently_omitted():
    body='<w:p><w:smartTag><w:r><w:t>WRAPPED</w:t><w:footnoteReference w:id="1"/></w:r></w:smartTag></w:p>'
    with pytest.raises(DocumentError,match='referencias de notas'):import_docx(source(body=body))
