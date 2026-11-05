"""Synthetic DOCX with columns, a bookmark and a native internal link."""
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED


def create():
    w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    body='<w:p><w:hyperlink w:anchor="destination"><w:r><w:t>GO_TO_DESTINATION</w:t></w:r></w:hyperlink></w:p>'
    body+=''.join(f'<w:p><w:r><w:t>ITEM{i:03d} '+('Selectable column content. '*6)+'</w:t></w:r></w:p>' for i in range(45))
    body+='<w:p><w:bookmarkStart w:id="1" w:name="destination"/><w:r><w:t>DESTINATIONWORD</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p>'
    body+='<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:left="720" w:right="720" w:top="720" w:bottom="720"/><w:cols w:num="2" w:space="480" w:sep="1"/></w:sectPr>'
    out=BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('word/document.xml',f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
    return out.getvalue()


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();Path(args.output).write_bytes(create())
