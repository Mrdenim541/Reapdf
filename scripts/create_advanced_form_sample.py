"""Ejemplo público: jerarquía real, texto compartido y radio entre páginas."""
from pathlib import Path
import sys
import pymupdf as f


def create(path):
    with f.open() as d:
        refs=[];radio=[]
        for n in range(2):
            p=d.new_page(width=595,height=842);p.insert_text((45,55),'REAPDF / FORMULARIO AVANZADO',fontsize=18)
            p.insert_text((45,95),'Nombre compartido (se sincroniza en ambas paginas):',fontsize=11)
            w=f.Widget();w.field_name='Temporal'+str(n);w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.text_fontsize=12;w.rect=f.Rect(45,110,450,145);w.text_maxlen=100
            refs.append(p.add_widget(w).xref)
            p.insert_text((45,205),'Decision exclusiva para todo el documento:',fontsize=11)
            for i,label in enumerate(['Aprobar','Revisar'] if n==0 else ['Rechazar']):
                y=225+i*40;w=f.Widget();w.field_name=f'Opcion{n}{i}';w.field_label=label;w.field_type=f.PDF_WIDGET_TYPE_RADIOBUTTON;w.field_value=False;w.rect=f.Rect(45,y,63,y+18)
                x=p.add_widget(w).xref;radio.append(x);p.insert_text((72,y+13),label,fontsize=11)
        root=d.get_new_xref();name=d.get_new_xref();decision=d.get_new_xref()
        d.update_object(root,f'<</T(Datos)/Kids[{name} 0 R {decision} 0 R]>>')
        d.update_object(name,f'<</T(Nombre)/FT/Tx/Ff 0/MaxLen 100/DA(/Helv 12 Tf 0 g)/V()/Parent {root} 0 R/Kids['+' '.join(f'{x} 0 R' for x in refs)+']>>')
        d.update_object(decision,f'<</T(Decision)/FT/Btn/Ff 32768/V/Off/Parent {root} 0 R/Kids['+' '.join(f'{x} 0 R' for x in radio)+']>>')
        for x in refs:
            for key in ['T','FT','Ff','V','MaxLen','DA']:d.xref_set_key(x,key,'null')
            d.xref_set_key(x,'Parent',f'{name} 0 R')
        for i,x in enumerate(radio):
            off=d.xref_get_key(x,'AP/N/Off')[1];on=d.xref_get_key(x,'AP/N/Yes')[1]
            d.xref_set_key(x,'AP/N',f'<</Off {off}/opcion_{i+1} {on}>>')
            for key in ['T','FT','Ff','V']:d.xref_set_key(x,key,'null')
            d.xref_set_key(x,'Parent',f'{decision} 0 R')
        d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{root} 0 R]')
        for page in d:
            for xref,kind,_ in page.annot_xrefs():
                if kind==f.PDF_ANNOT_WIDGET:d.xref_set_key(xref,'P',f'{page.xref} 0 R')
        d.save(path,garbage=4,deflate=True)


if __name__=='__main__':
    create(Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/reapdf-formulario-avanzado.pdf'))
