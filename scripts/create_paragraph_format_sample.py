"""Synthetic typography fixture, runnable by the isolated bundled interpreter."""
from pathlib import Path
import runpy
import pymupdf as f


def create(geometry=False,css=False):
    source=runpy.run_path(str(Path(__file__).with_name('create_tagged_paragraph_sample.py')))['create']
    with f.open(stream=source()) as d:
        n=f.mupdf;pdf=f._as_pdf_document(d);root=n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_trailer(pdf),'Root'),'StructTreeRoot');identity=n.pdf_to_num(root)
        d.xref_set_key(identity,'ClassMap','<</Shared <</O/Layout /FontFamily (Helvetica)>>>>')
        def walk(obj):
            if n.pdf_is_array(obj):
                for i in range(n.pdf_array_len(obj)):walk(n.pdf_array_get(obj,i))
            elif n.pdf_is_dict(obj):
                if n.pdf_to_name(n.pdf_dict_gets(obj,'S'))=='Span':d.xref_set_key(n.pdf_to_num(obj),'C','/Shared')
                walk(n.pdf_dict_gets(obj,'K'))
        walk(n.pdf_dict_gets(root,'K'))
        first=n.pdf_array_get(n.pdf_dict_gets(n.pdf_dict_gets(root,'ParentTree'),'Nums'),1);neighbor=n.pdf_to_num(n.pdf_array_get(first,0));d.xref_set_key(neighbor,'C','/Shared')
        if geometry:
            spans=[s for b in d[0].get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans'] if s['text'].strip() in ['HELLO','TEXT']]
            for code,span in zip([1,2],spans):
                leaf=n.pdf_to_num(n.pdf_array_get(first,code));box=(f.Rect(span['bbox'])+(-1,-1,1,1))*~d[0].transformation_matrix
                d.xref_set_key(leaf,'A','<</O/Layout /BBox ['+' '.join(str(v) for v in box)+f'] /Width {box.width} /Height {box.height}>>')
        if css:
            d.xref_set_key(identity,'ClassMap','<</Shared <</O/CSS-1.00 /font-family(Helvetica)>>>>')
            for code,size,weight,style in [(1,18,'bold','normal'),(2,14,'normal','italic')]:
                leaf=n.pdf_to_num(n.pdf_array_get(first,code)) if geometry else None
                if leaf is None:
                    parent=n.pdf_dict_gets(root,'ParentTree');arr=n.pdf_array_get(n.pdf_dict_gets(parent,'Nums'),1);leaf=n.pdf_to_num(n.pdf_array_get(arr,code))
                old=d.xref_get_key(leaf,'A');attr=f'<</O/CSS-1.00 /font-size({size*4/3:.6f}px)/font-weight({weight})/font-style({style})>>'
                d.xref_set_key(leaf,'A','['+old[1]+' '+attr+']' if old[0]!='null' else attr)
        return d.tobytes()


if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_bytes(create(geometry='--geometry' in sys.argv,css='--css' in sys.argv))
