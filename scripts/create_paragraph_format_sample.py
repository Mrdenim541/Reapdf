"""Synthetic shared class and per-Span typography, without personal assets."""
import pymupdf as f
from scripts.create_tagged_paragraph_sample import create as source
from backend.semantic_text import tree


def create():
    with f.open(stream=source()) as d:
        t=tree(d);root=f.mupdf.pdf_to_num(t.root);d.xref_set_key(root,'ClassMap','<</Shared <</O/Layout /FontFamily (Helvetica)>>>>')
        for identity,record in t.records.items():
            role=f.mupdf.pdf_to_name(f.mupdf.pdf_dict_gets(record['object'],'S'))
            if role=='Span':d.xref_set_key(identity,'C','/Shared')
        neighbor=t.owners[(d[0].xref,0,0)][0];d.xref_set_key(neighbor,'C','/Shared')
        return d.tobytes()


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create())
