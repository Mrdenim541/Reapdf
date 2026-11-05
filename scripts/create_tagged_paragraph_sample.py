"""Self-contained tagged styles and Span siblings, without private assets."""
import pymupdf as f


def create():
    d=f.open();p=d.new_page(width=650,height=800);p.insert_font(fontname='hebo');p.insert_font(fontname='heit');p.insert_text((30,740),'NEIGHBOR UNCHANGED')
    x=p.get_contents()[0];d.update_stream(x,b'/P <</MCID 0>> BDC '+d.xref_stream(x)+b' EMC')
    advance=f.Font('hebo').text_length('HELLO ',fontsize=18)
    content=(b'/Span <</MCID 1>> BDC q BT /hebo 18 Tf .8 0 0 rg 1 0 0 1 200 400 Tm (HELLO ) Tj ET Q EMC '+f'/Span <</MCID 2>> BDC q BT /heit 14 Tf 0 0 .8 rg 1 0 .35 1 {200+advance} 400 Tm (TEXT) Tj ET Q EMC'.encode())
    stream=d.get_new_xref();d.update_object(stream,'<<>>');d.update_stream(stream,content);d.xref_set_key(p.xref,'Contents',f'[{x} 0 R {stream} 0 R]');page_xref=p.xref
    root=d.get_new_xref();document=d.get_new_xref();paragraph=d.get_new_xref();neighbor=d.get_new_xref();first=d.get_new_xref();second=d.get_new_xref()
    d.update_object(neighbor,f'<< /Type/StructElem /S/P /P {document} 0 R /Pg {page_xref} 0 R /K 0 >>')
    d.update_object(paragraph,f'<< /Type/StructElem /S/P /P {document} 0 R /Pg {page_xref} 0 R /K [{first} 0 R {second} 0 R] >>')
    for code,identity in [(1,first),(2,second)]:d.update_object(identity,f'<< /Type/StructElem /S/Span /P {paragraph} 0 R /Pg {page_xref} 0 R /K {code} >>')
    d.xref_set_key(page_xref,'StructParents','0')
    other=d.new_page(width=650,height=800);other.insert_text((30,40),'OTHER PAGE UNCHANGED');other_xref=other.xref;other_leaf=d.get_new_xref();d.update_object(other_leaf,f'<< /Type/StructElem /S/P /P {document} 0 R /Pg {other_xref} 0 R /K 0 >>');d.xref_set_key(other_xref,'StructParents','1')
    x=other.get_contents()[0];d.update_stream(x,b'/P <</MCID 0>> BDC '+d.xref_stream(x)+b' EMC')
    d.new_page(width=650,height=800)
    d.update_object(root,f'<< /Type/StructTreeRoot /K [{document} 0 R] /ParentTree << /Nums [0 [{neighbor} 0 R {first} 0 R {second} 0 R] 1 [{other_leaf} 0 R]] >> /ParentTreeNextKey 2 >>')
    d.update_object(document,f'<< /Type/StructElem /S/Document /P {root} 0 R /K [{neighbor} 0 R {paragraph} 0 R {other_leaf} 0 R] >>')
    d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<</Marked true>>');d.xref_set_key(d.pdf_catalog(),'Lang','(es)')
    data=d.tobytes();d.close();return data


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();Path(args.output).write_bytes(create())
