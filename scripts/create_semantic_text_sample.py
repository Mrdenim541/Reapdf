"""Synthetic ActualText and tagged Form samples, with no external assets."""
import pymupdf as f

def source(actual='HELLO',tagged=False,node=False,visible='HELLO'):
    with f.open() as d:
        p=d.new_page(width=500,height=500);p.insert_text((50,100),visible,fontsize=16);p.insert_text((50,250),'UNCHANGED',fontsize=16)
        x=p.get_contents()[0];prop='' if node else ' /ActualText '+f.get_pdf_str(actual)
        d.update_stream(x,('/P <</MCID 0'+prop+'>> BDC ').encode()+d.xref_stream(x)+b' EMC')
        if tagged:
            root=d.get_new_xref();leaf=d.get_new_xref();d.update_object(root,f'<</Type/StructTreeRoot /K [{leaf} 0 R] /ParentTree <</Nums [0 [{leaf} 0 R]]>>>>');d.update_object(leaf,f'<</Type/StructElem /S/P /P {root} 0 R /Pg {p.xref} 0 R /K 0'+(' /ActualText '+f.get_pdf_str(actual) if node else '')+'>>');d.xref_set_key(p.xref,'StructParents','0');d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<</Marked true>>')
        return d.tobytes()

def form_source(*,stream_owned=True,actual=None,rotation=0,nested=False,shared=False,node_actual=False):
    with f.open() as d:
        p=d.new_page(width=500,height=500);font=p.insert_font(fontname='helv');p.insert_text((50,250),'UNCHANGED',fontsize=16)
        form=d.get_new_xref();d.update_object(form,f'<</Type/XObject /Subtype/Form /BBox [-10 -10 200 40] /Resources <</Font <</helv {font} 0 R>>>>'+(' /StructParents 10' if stream_owned else '')+'>>')
        prop='' if actual is None or node_actual else ' /ActualText '+f.get_pdf_str(actual)
        content=(('/Span <</MCID 0'+prop+'>> BDC ' if stream_owned else '')+'q BT /helv 16 Tf 1 0 0 1 0 0 Tm (HELLO) Tj ET Q'+(' EMC' if stream_owned else '')).encode()
        d.update_stream(form,content);target=form
        if nested:
            target=d.get_new_xref();d.update_object(target,f'<</Type/XObject /Subtype/Form /BBox [-10 -10 200 40] /Resources <</XObject <</Inner {form} 0 R>>>>>>');d.update_stream(target,b'/Inner Do')
        from backend.form_text import clone_dictionary
        resources=clone_dictionary(d,p.xref,'Resources');d.xref_set_key(resources,'XObject',f'<</F {target} 0 R>>');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,(('' if stream_owned else '/P <</MCID 0>> BDC ')+ 'q 1 0 0 1 50 400 cm /F Do Q'+('' if stream_owned else ' EMC')).encode());d.xref_set_key(p.xref,'Contents','['+' '.join(f'{v} 0 R' for v in p.get_contents()+[x])+']')
        root=d.get_new_xref();leaf=d.get_new_xref();pg=p.xref
        k=f'<</Type/MCR /Pg {pg} 0 R /Stm {form} 0 R /MCID 0>>' if stream_owned else '0'
        key=10 if stream_owned else 0
        node_prop=' /ActualText '+f.get_pdf_str(actual) if node_actual and actual is not None else ''
        d.update_object(root,f'<</Type/StructTreeRoot /K [{leaf} 0 R] /ParentTree <</Nums [{key} [{leaf} 0 R]]>>>>');d.update_object(leaf,f'<</Type/StructElem /S/P /P {root} 0 R /Pg {pg} 0 R /K {k}{node_prop}>>');d.xref_set_key(d.pdf_catalog(),'StructTreeRoot',f'{root} 0 R');d.xref_set_key(d.pdf_catalog(),'MarkInfo','<</Marked true>>')
        if not stream_owned:d.xref_set_key(pg,'StructParents','0')
        if shared:
            x2=d.get_new_xref();d.update_object(x2,'<<>>');d.update_stream(x2,b'q 1 0 0 1 200 180 cm /F Do Q');d.xref_set_key(pg,'Contents','['+' '.join(f'{v} 0 R' for v in p.get_contents()+[x2])+']')
        p.set_rotation(rotation);d.new_page(width=500,height=500).insert_text((50,50),'OTHER PAGE')
        return d.tobytes()

def create(kind='stream'):
    if kind=='quick':return source('1000000001',tagged=True,visible='1000000001')
    if kind=='actual':return source('HELLO',tagged=True)
    if kind=='outer':return form_source(stream_owned=False,nested=True,shared=True)
    return form_source(actual='Accessible original')


if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('kind',choices=['stream','outer','actual','quick'],nargs='?',default='stream');args=parser.parse_args();Path(args.output).write_bytes(create(args.kind))
