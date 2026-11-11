"""Absolute CSS-1.00 font declarations, without a CSS evaluator or cascade."""
import re
from decimal import Decimal
import pymupdf as f
from .engine import DocumentError
OWNERS={'CSS-1.00'}
PROPERTIES={'font-family','font-size','font-weight','font-style'}


def fail():raise DocumentError('La tipografía CSS requiere propiedades de fuente explícitas y tamaño absoluto en pt o px; otras reglas necesitan composición adicional.')


def read(attr):
    n=f.mupdf;keys={n.pdf_to_name(n.pdf_dict_get_key(attr,i)) for i in range(n.pdf_dict_len(attr))}
    if keys-{'O'}-PROPERTIES:fail()
    result={}
    for key in keys&PROPERTIES:
        value=n.pdf_dict_gets(attr,key)
        if not n.pdf_is_string(value):fail()
        text=n.pdf_to_text_string(value)
        if len(text)>200 or any(ord(c)<32 for c in text):fail()
        if key=='font-family':
            family=text[1:-1] if len(text)>1 and text[0] in [chr(34),chr(39)] and text[-1]==text[0] else text
            if not re.fullmatch(r'[\w-](?:[\w -]*[\w-])?',family):fail()
        elif key=='font-size':
            match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(pt|px)',text)
            if not match or not 0<Decimal(match[1])<=1000:fail()
        elif key=='font-weight':
            if text not in ['normal','bold',*[str(v) for v in range(100,901,100)]]:fail()
        elif text not in ['normal','italic','oblique']:fail()
        result[key]=text
    return result


def requested(row,attr):
    values=read(attr);options=row['_format_options'];original=options['family']=='original';result={}
    for key,old in values.items():
        if original and key!='font-size':continue
        if key=='font-family':new={'sans':'DejaVu Sans','serif':'DejaVu Serif','mono':'DejaVu Sans Mono'}[options['family']]
        elif key=='font-size':
            if abs(row['_geometry']['factor']-1)>1e-5:fail()
            unit='px' if old.endswith('px') else 'pt';size=Decimal(str(row['size']))*(Decimal(4)/3 if unit=='px' else 1)
            new=format(size.quantize(Decimal('.000001')),'f').rstrip('0').rstrip('.')+unit
        elif key=='font-weight':new=('bold' if 'bold' in options['style'] else 'normal') if old in ['normal','bold'] else ('700' if 'bold' in options['style'] else '400')
        else:new='italic' if 'italic' in options['style'] else 'normal'
        result[key]=f.get_pdf_str(new)
    return result
