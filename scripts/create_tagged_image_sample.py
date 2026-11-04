"""Self-contained, generic native tagged-image sample for desktop/package checks."""
import pymupdf as f


def create():
    d=f.open();p=d.new_page(width=500,height=400);root=d.get_new_xref();parent=d.get_new_xref();document=d.get_new_xref();attrs=d.get_new_xref();d.update_object(attrs,'<</O /Layout /Width 160 /Height 80 /Placement /Block>>');nodes=[]
    p.insert_text((40,80),'Keep this text',fontsize=14)
    pix=f.Pixmap(f.csRGB,f.IRect(0,0,80,40),False);pix.clear_with(100)
    x=p.insert_image(f.Rect(40,140,200,220),pixmap=pix);p.insert_image(f.Rect(240,140,400,220),xref=x)
    for i,stream in enumerate(p.get_contents()):
        role='P' if i==0 else 'Figure';d.update_stream(stream,f'/{role} <</MCID {i}>> BDC\n'.encode()+d.xref_stream(stream)+b'\nEMC')
        node=d.get_new_xref();nodes.append(node);extra=''
        if i:
            box=[40 if i==1 else 240,180,200 if i==1 else 400,260]
            extra=f'/Alt ({"Original diagram" if i==1 else "Other diagram"}) /A [<</O /Layout /BBox [{" ".join(map(str,box))}]>> {attrs} 0 R 0]'
        d.update_object(node,f'<</Type /StructElem /S /{role} /P {document} 0 R /Pg {p.xref} 0 R /K {i} {extra}>>')
    d.update_object(document,f'<</Type /StructElem /S /Document /P {root} 0 R /K ['+' '.join(f'{n} 0 R' for n in nodes)+']>>')
    d.update_object(parent,'<</Nums [0 ['+' '.join(f'{n} 0 R' for n in nodes)+']]>>')
    d.update_object(root,f'<</Type /StructTreeRoot /K {document} 0 R /ParentTree {parent} 0 R /ParentTreeNextKey 1>>')
    d.xref_set_key(p.xref,'StructParents','0');d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<</Marked true>>')
    d.new_page().insert_text((40,80),'Second page unchanged');result=d.tobytes(garbage=2);d.close();return result


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('output');args=parser.parse_args();Path(args.output).write_bytes(create())
