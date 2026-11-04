"""Generic tagged PDF for exercising native split; contains no personal data."""
import argparse
import pymupdf as f


def create(pages=42,rows=60):
    doc=f.open();root=doc.get_new_xref();parent=doc.get_new_xref();document=doc.get_new_xref();sections=[];pairs=[]
    for i in range(pages):
        page=doc.new_page();section=doc.get_new_xref();sections.append(section);children=[]
        for j in range(rows):
            page.insert_text((35,35+j*11),f'Page {i+1:03d} row {j+1:03d}',fontsize=8)
            stream=page.get_contents()[-1];doc.update_stream(stream,f'/P <</MCID {j}>> BDC\n'.encode()+doc.xref_stream(stream)+b'\nEMC')
            node=doc.get_new_xref();children.append(node)
            attrs='/A [<</O /Layout /TextAlign /Start /SpaceAfter 0>> 0]'
            actual='/ActualText (Page-specific alternative)' if j==0 else ''
            doc.update_object(node,f'<</Type /StructElem /S /P /P {section} 0 R /Pg {page.xref} 0 R /K {j} {attrs} {actual}>>')
        doc.update_object(section,f'<</Type /StructElem /S /Sect /P {document} 0 R /Pg {page.xref} 0 R /K ['+' '.join(f'{x} 0 R' for x in children)+']>>')
        doc.xref_set_key(page.xref,'StructParents',str(i));pairs.append(str(i)+' ['+' '.join(f'{x} 0 R' for x in children)+']')
    doc.update_object(document,f'<</Type /StructElem /S /Document /P {root} 0 R /K ['+' '.join(f'{x} 0 R' for x in sections)+']>>')
    doc.update_object(parent,'<</Nums ['+' '.join(pairs)+']>>')
    doc.update_object(root,f'<</Type /StructTreeRoot /K {document} 0 R /ParentTree {parent} 0 R /ParentTreeNextKey {pages}>>')
    doc.xref_set_key(doc.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');doc.xref_set_key(doc.pdf_catalog(),'MarkInfo','<</Marked true>>')
    doc.set_page_labels([{'startpage':0,'prefix':'P-','style':'D','firstpagenum':1}]);doc.set_toc([[1,f'Section {i//14+1}',i+1] for i in range(0,pages,14)])
    result=doc.tobytes(deflate=True);doc.close();return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args()
    from pathlib import Path
    Path(args.output).write_bytes(create())
