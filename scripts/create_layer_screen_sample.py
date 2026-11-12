"""Synthetic two-layer PDF; no user documents are used."""
from pathlib import Path
import sys
import pymupdf as f


def create():
    with f.open() as doc:
        page=doc.new_page();a=doc.add_ocg('A');b=doc.add_ocg('B')
        page.insert_text((50,70),'ONLY A',oc=a);page.insert_text((50,110),'ONLY B',oc=b)
        doc.add_layer('Solo B',on=[b]);return doc.tobytes()


if __name__=='__main__':Path(sys.argv[1]).write_bytes(create())
