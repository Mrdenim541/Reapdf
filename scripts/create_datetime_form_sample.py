"""Synthetic date/time AcroForm with standard helper code in local PDF streams."""
import pymupdf as f


def create():
    with f.open() as d:
        p=d.new_page(width=500,height=650);p.insert_text((30,40),'DATE AND TIME FORM')
        w=f.Widget();w.field_name='DateTime';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,80,430,120);w.text_font='helv';w.text_fontsize=12;w.field_value='';p.add_widget(w);xref=next(p.widgets()).xref
        aa=[]
        for event,helper in [('F','AFDate_FormatEx'),('K','AFDate_KeystrokeEx')]:
            code=(helper+'("dd/mm/yyyy HH:MM:ss");'+' '*300).encode('ascii');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,code,compress=True);aa.append('/'+event+'<</S/JavaScript/JS '+str(x)+' 0 R>>')
        d.xref_set_key(xref,'AA','<<'+''.join(aa)+'>>');d.new_page().insert_text((30,40),'UNCHANGED OTHER PAGE');return d.tobytes()


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create())
