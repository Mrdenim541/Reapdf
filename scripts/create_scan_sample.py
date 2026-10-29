"""Escaneado sintético para probar OCR sin documentos personales."""
from pathlib import Path
import sys
import pymupdf as f


def create(path):
    with f.open() as source:
        p=source.new_page(width=595,height=842)
        p.insert_text((45,70),'REAPDF / ESCANEADO DE PRUEBA',fontsize=20)
        p.insert_text((45,140),'Documento de ejemplo para reconocer texto.',fontsize=16)
        p.insert_text((45,190),'Información en español: niño, año, número 12345.',fontsize=16)
        p.insert_text((45,245),'English text: searchable document 67890.',fontsize=16)
        pix=p.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
    with f.open() as doc:
        p=doc.new_page(width=595,height=842);p.insert_image(p.rect,stream=pix.tobytes('png'));doc.save(path)


if __name__=='__main__':
    path=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-escaneado.pdf');create(path);print(path)
