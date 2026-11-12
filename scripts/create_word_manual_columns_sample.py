"""Synthetic manual column breaks and a hyperlink spanning column frames."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED


def create(changing=False,with_notes=False):
    w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    body='<w:p><w:pPr><w:ind w:firstLine="360"/></w:pPr><w:hyperlink w:anchor="destination"><w:r><w:rPr><w:b/><w:color w:val="214EAA"/></w:rPr><w:t>FIRSTCOLLINK</w:t><w:br w:type="column"/><w:t>SECONDCOLLINK</w:t></w:r></w:hyperlink></w:p>'
    body+='<w:p><w:r><w:br w:type="column"/><w:t>NEXTPAGELEFT</w:t><w:br w:type="column"/><w:t>NEXTPAGERIGHT</w:t></w:r></w:p>'
    body+='<w:p><w:bookmarkStart w:id="1" w:name="destination"/><w:r><w:t>DESTINATIONWORD</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    extra='<w:p><w:pPr><w:pageBreakBefore/></w:pPr><w:hyperlink w:anchor="destination"><w:r><w:t>PHYSICALPAGELEFT</w:t><w:br w:type="column"/><w:t>PHYSICALPAGERIGHT</w:t><w:br w:type="page"/><w:t>NEXTWHOLEPAGE</w:t></w:r></w:hyperlink></w:p>'
    section='<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:left="720" w:right="720" w:top="720" w:bottom="720"/><w:cols w:num="2" w:space="480" w:sep="1"/></w:sectPr>'
    body+='<w:p><w:pPr>'+section+'</w:pPr><w:r><w:t>CONTINUOUSFIRST</w:t></w:r></w:p>'+extra+'<w:p><w:r><w:t>CONTINUOUSLAST</w:t></w:r></w:p>'
    body+='<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:left="720" w:right="720" w:top="720" w:bottom="720"/><w:cols w:num="2" w:space="480" w:sep="1"/></w:sectPr>'
    if changing:
        continuous=section.replace('<w:sectPr>','<w:sectPr><w:type w:val="continuous"/>')
        # End the two-column section, then use three and one columns on the same page.
        body=body[:-len(continuous)]+'<w:p><w:pPr>'+continuous+'</w:pPr><w:r><w:t>BEFORECOLUMNCHANGE</w:t></w:r></w:p>'
        three=continuous.replace('w:num="2"','w:num="3"')
        body+='<w:p><w:pPr>'+three+'</w:pPr><w:hyperlink w:anchor="destination"><w:r><w:t>BANDTHREEA</w:t><w:br w:type="column"/><w:t>BANDTHREEB</w:t><w:br w:type="column"/><w:t>BANDTHREEC</w:t></w:r></w:hyperlink></w:p><w:p><w:r><w:t>BANDONEFINAL</w:t></w:r></w:p>'+continuous.replace('w:num="2"','w:num="1"')
    if with_notes:
        if not changing:raise ValueError('The notes fixture requires the changing column bands.')
        body=body.replace('<w:t>CONTINUOUSLAST</w:t>','<w:t>CONTINUOUSLAST</w:t><w:footnoteReference w:id="1"/>')
        close='<w:t>BANDTHREEC</w:t></w:r></w:hyperlink>'
        body=body.replace(close,close+'<w:r><w:footnoteReference w:id="2"/><w:endnoteReference w:id="4"/></w:r>')
        body=body.replace('<w:t>BANDONEFINAL</w:t>','<w:t>BANDONEFINAL</w:t><w:footnoteReference w:id="3"/>')
    out=BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'+('<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/><Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>' if with_notes else '')+'</Types>'))
        z.writestr('word/document.xml',f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
        if with_notes:
            rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="main" Type="'+rel+'/officeDocument" Target="word/document.xml"/></Relationships>')
            z.writestr('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="fn" Type="'+rel+'/footnotes" Target="footnotes.xml"/><Relationship Id="en" Type="'+rel+'/endnotes" Target="endnotes.xml"/></Relationships>')
            z.writestr('word/settings.xml',f'<w:settings xmlns:w="{w}"><w:footnotePr><w:numStart w:val="3"/><w:numRestart w:val="eachSect"/></w:footnotePr><w:endnotePr><w:numStart w:val="2"/><w:numRestart w:val="eachSect"/><w:pos w:val="sectEnd"/></w:endnotePr></w:settings>')
            z.writestr('word/footnotes.xml',f'<w:footnotes xmlns:w="{w}">'+''.join(f'<w:footnote w:id="{i}"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:footnote>' for i,text in enumerate(['COLUMNFOOTONE','COLUMNFOOTTWO','COLUMNFOOTTHREE'],1))+'</w:footnotes>')
            z.writestr('word/endnotes.xml',f'<w:endnotes xmlns:w="{w}"><w:endnote w:id="4"><w:p><w:r><w:t>ENDCOLUMNSECTION</w:t></w:r></w:p></w:endnote></w:endnotes>')
    return out.getvalue()


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create(changing='--changing' in sys.argv,with_notes='--notes' in sys.argv))
