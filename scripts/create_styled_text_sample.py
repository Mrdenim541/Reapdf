"""Public PDF with base fonts, mixed styles and an embedded TrueType subset."""
from pathlib import Path
import sys
import pymupdf as f


def create(path):
    font=Path(__file__).resolve().parent.parent/'resources/fonts/DejaVuSans.ttf'
    with f.open() as d:
        p=d.new_page(width=595,height=842)
        p.insert_text((45,55),'REAPDF / TEXTO CON ESTILOS',fontname='hebo',fontsize=20)
        p.insert_text((45,95),'Prueba el modo Conservar fuente y estilo por fragmentos.',fontsize=11)
        p.insert_text((45,130),'Selecciona una region completa y revisa la vista previa.',fontsize=11)
        p.insert_text((45,220),'Texto original en negrita',fontname='hebo',fontsize=18,color=(.1,.2,.5))
        p.insert_text((45,270),'Estilo cursiva original',fontname='heit',fontsize=16,color=(.6,.1,.2))
        p.insert_font(fontname='FuenteOriginal',fontfile=str(font))
        p.insert_text((45,330),'Fuente incrustada original 12345',fontname='FuenteOriginal',fontsize=15,color=(.1,.4,.2))
        p.insert_text((45,390),'La fuente parcial solo admite sus caracteres disponibles.',fontsize=11)
        p.insert_text((45,430),'Ejemplo compatible: Fuente original 123',fontsize=11)
        d.new_page().insert_text((45,80),'Pagina conservada sin cambios',fontsize=18)
        d.subset_fonts();d.save(path,garbage=4,deflate=True)


if __name__=='__main__':create(Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-texto-con-estilos.pdf'))
