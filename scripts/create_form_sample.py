"""Formulario sintético público para comprobar valores y apariencias."""
from pathlib import Path
import sys
import pymupdf as f


def create(path):
    with f.open() as doc:
        page=doc.new_page(width=595,height=842)
        page.insert_text((45,55),'REAPDF / FORMULARIO DE PRUEBA',fontsize=18)
        fields=[('Nombre',f.PDF_WIDGET_TYPE_TEXT),('Acepto',f.PDF_WIDGET_TYPE_CHECKBOX),
                ('Ciudad',f.PDF_WIDGET_TYPE_COMBOBOX),('Notas',f.PDF_WIDGET_TYPE_TEXT),('Referencia',f.PDF_WIDGET_TYPE_TEXT)]
        for i,(name,kind) in enumerate(fields):
            y=110+i*110;page.insert_text((45,y),name,fontsize=12)
            widget=f.Widget();widget.field_name=name;widget.field_type=kind;widget.text_fontsize=12
            widget.rect=f.Rect(45,y+10,550 if name!='Acepto' else 70,y+65)
            if name=='Nombre':widget.text_maxlen=100
            if name=='Ciudad':widget.choice_values=[('BOG','Bogotá'),('LIM','Lima')]
            if name=='Notas':widget.field_flags=4096
            if name=='Referencia':widget.field_flags=1;widget.field_value='Solo lectura'
            page.add_widget(widget)
        page=doc.new_page();page.insert_text((45,70),'Segunda pagina conservada',fontsize=18)
        doc.save(path)


if __name__=='__main__':
    path=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-formulario.pdf');create(path);print(path)
