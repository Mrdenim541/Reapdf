"""Synthetic standard red-number formatter with quoted numeric range bounds."""
import pymupdf as f


def create():
    with f.open() as d:
        p=d.new_page();p.insert_text((30,40),'COLOR NUMBER FORM');w=f.Widget();w.field_name='Amount';w.field_type=f.PDF_WIDGET_TYPE_TEXT;w.rect=f.Rect(30,80,400,125);w.text_font='helv';w.text_fontsize=12;w.text_color=(0,0,1);w.field_value='12.5';x=p.add_widget(w).xref
        events={'F':'AFNumber_Format(2,1,3,0," EUR",false);','K':'AFNumber_Keystroke(2,1);','V':'AFRange_Validate(true,"-100",true,"100");'}
        d.xref_set_key(x,'AA','<<'+' '.join('/'+event+'<</S/JavaScript/JS '+f.get_pdf_str(code)+'>>' for event,code in events.items())+'>>');d.new_page().insert_text((30,40),'OTHER PAGE UNCHANGED');return d.tobytes()


if __name__=='__main__':
    import sys
    from pathlib import Path
    Path(sys.argv[1]).write_bytes(create())
