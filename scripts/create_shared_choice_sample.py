"""Standalone synthetic inherited combo/list fields, without private data."""
import pymupdf as f


def create(kind='combo',rotation=0,crop=False):
    with f.open() as d:
        widgets=[]
        for i in range(2):
            p=d.new_page(width=500,height=650);p.insert_text((30,45),'SHARED CHOICE FORM');w=f.Widget();w.field_name='Temporary'+str(i);w.field_type=f.PDF_WIDGET_TYPE_COMBOBOX if kind=='combo' else f.PDF_WIDGET_TYPE_LISTBOX;w.rect=f.Rect(40,100,350,180);w.text_font='helv';w.text_fontsize=12;w.choice_values=[('BOG','Bogotá'),('LIM','Lima'),('CUS','Cusco')];w.field_value='BOG';widgets.append(p.add_widget(w).xref)
            if crop:p.set_cropbox(f.Rect(10,10,480,620))
            p.set_rotation(rotation)
        root=d.get_new_xref();field=d.get_new_xref();d.update_object(root,f'<</T(Datos)/Kids[{field} 0 R]>>');d.update_object(field,f'<</T(Ciudad)/FT/Ch/Ff {131072 if kind=="combo" else 0}/DA(/Helv 12 Tf 0 g)/Opt[[(BOG)(Bogot\\341)][(LIM)(Lima)][(CUS)(Cusco)]]/V(BOG)/I[0]/Parent {root} 0 R/Kids['+' '.join(f'{x} 0 R' for x in widgets)+']>>')
        for page,x in zip(d,widgets):
            for key in ['T','FT','Ff','V','I','Opt','DA']:d.xref_set_key(x,key,'null')
            d.xref_set_key(x,'Parent',f'{field} 0 R');d.xref_set_key(x,'P',f'{page.xref} 0 R')
        d.xref_set_key(d.pdf_catalog(),'AcroForm/Fields',f'[{root} 0 R]');d.new_page(width=500,height=650).insert_text((30,45),'OTHER PAGE UNCHANGED')
        return d.tobytes(garbage=4,deflate=True)


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create())
