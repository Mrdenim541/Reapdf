"""Synthetic two-layer PDF; no user documents are used."""
from pathlib import Path
import sys
import pymupdf as f


def create():
    with f.open() as doc:
        page=doc.new_page();a=doc.add_ocg('A');b=doc.add_ocg('B')
        page.insert_text((50,70),'ONLY A',oc=a);page.insert_text((50,110),'ONLY B',oc=b)
        doc.add_layer('Solo B',on=[b])
        doc.xref_set_key(a,'Usage','<< /Print << /PrintState /ON >> /Export << /ExportState /OFF >> >>')
        doc.xref_set_key(b,'Usage','<< /Print << /PrintState /OFF >> /Export << /ExportState /ON >> >>')
        doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS',f'[<< /Event /Print /Category[/Print] /OCGs[{a} 0 R {b} 0 R] >> << /Event /Export /Category[/Export] /OCGs[{a} 0 R {b} 0 R] >>]')
        n=f.mupdf;root=n.pdf_dict_getp(n.pdf_trailer(f._as_pdf_document(doc)),'Root/OCProperties');alternate=n.pdf_array_get(n.pdf_dict_gets(root,'Configs'),0)
        n.pdf_dict_puts(alternate,'AS',n.pdf_deep_copy_obj(n.pdf_dict_gets(n.pdf_dict_gets(root,'D'),'AS')))
        return doc.tobytes()


if __name__=='__main__':Path(sys.argv[1]).write_bytes(create())
