"""Small public document for the workspace tour and structural review."""
from pathlib import Path
import sys
import pymupdf as f


def create(path, pages=4):
    with f.open() as doc:
        for _ in range(pages):doc.new_page(width=595,height=842)
        p=doc[0];p.insert_text((45,65),'REAPDF / RECORRIDO DEL ESPACIO',fontname='hebo',fontsize=19)
        p.insert_text((45,110),'Busca herramientas con Ctrl+K. Guarda favoritos con la estrella.',fontsize=11)
        p.insert_text((45,145),'Abre Revisar documento para localizar notas, campos y escaneados.',fontsize=11)
        p.add_text_annot((45,190),'Nota de ejemplo para revisar antes de exportar.')
        p.insert_link({'kind':f.LINK_GOTO,'from':f.Rect(45,220,260,245),'page':2,'to':f.Point(0,0)})
        p.insert_text((45,237),'Enlace a la pagina de formulario',color=(0,.35,.25),fontsize=12)
        with f.open() as scan:
            q=scan.new_page(width=595,height=842);q.insert_text((50,100),'PAGINA DE PRUEBA PARA OCR',fontname='hebo',fontsize=21)
            q.insert_text((50,160),'Texto rasterizado: revisar el reconocimiento 12345.',fontsize=15)
            doc[1].insert_image(doc[1].rect,stream=q.get_pixmap(matrix=f.Matrix(1.5,1.5)).tobytes('png'))
        p=doc[2];p.insert_text((45,65),'FORMULARIO DE EJEMPLO',fontname='hebo',fontsize=19)
        p.insert_text((45,115),'Nombre:',fontsize=12);w=f.Widget();w.field_name='Nombre';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(45,130,360,160);p.add_widget(w)
        doc[3].set_rotation(90)
        doc.set_page_labels([{'startpage':0,'prefix':'Guia-','style':'D','firstpagenum':1}])
        doc.save(path,garbage=4,deflate=True)


if __name__=='__main__':create(Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-recorrido.pdf'),int(sys.argv[2]) if len(sys.argv)>2 else 4)
