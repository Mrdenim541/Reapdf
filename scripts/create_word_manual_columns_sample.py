"""Synthetic manual column breaks and a hyperlink spanning column frames."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED


def create(changing=False):
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
    out=BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('word/document.xml',f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
    return out.getvalue()


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create(changing='--changing' in sys.argv))
