"""Fuentes PDF base para edición controlada de líneas horizontales."""
import pymupdf as fitz
from .engine import DocumentError, finite

FONT_OPTIONS = [
    ('helv','Helvetica'),('hebo','Helvetica-Bold'),('heit','Helvetica-Oblique'),('hebi','Helvetica-BoldOblique'),
    ('tiro','Times-Roman'),('tibo','Times-Bold'),('tiit','Times-Italic'),('tibi','Times-BoldItalic'),
    ('cour','Courier'),('cobo','Courier-Bold'),('coit','Courier-Oblique'),('cobi','Courier-BoldOblique')]
SOURCE_FONTS = {name:key for key,name in FONT_OPTIONS}
SOURCE_FONTS.update({'Arial':'helv','ArialMT':'helv','Arial-BoldMT':'hebo',
                     'Arial-ItalicMT':'heit','Arial-BoldItalicMT':'hebi',
                     'TimesNewRomanPSMT':'tiro','TimesNewRomanPS-BoldMT':'tibo',
                     'TimesNewRomanPS-ItalicMT':'tiit','TimesNewRomanPS-BoldItalicMT':'tibi',
                     'CourierNewPSMT':'cour','CourierNewPS-BoldMT':'cobo',
                     'CourierNewPS-ItalicMT':'coit','CourierNewPS-BoldItalicMT':'cobi'})


def prepare_text_style(page, source, replacement, op, all_spans):
    font_key = op.get('font', source['font_key'])
    if not isinstance(font_key, str) or font_key not in dict(FONT_OPTIONS):
        raise DocumentError('Elige una de las fuentes base compatibles.')
    size = op.get('size', source['size'])
    if not finite(size) or not 6 <= size <= 144:
        raise DocumentError('El tamaño de texto debe estar entre 6 y 144 puntos.')
    default_color = [((source['color'] >> shift)&255)/255 for shift in (16,8,0)]
    color = op.get('color', default_color)
    if not isinstance(color, list) or len(color)!=3 or any(not finite(c) or not 0<=c<=1 for c in color):
        raise DocumentError('Color de texto no válido.')
    font = fitz.Font(font_key)
    width = font.text_length(replacement, fontsize=size)
    if width > fitz.Rect(source['bbox']).width + .1:
        raise DocumentError('El texto nuevo no cabe. Acórtalo o reduce su tamaño para conservar el ancho original.')
    x,y = source['origin']
    new_box = fitz.Rect(x,y-font.ascender*size,x+width,y-font.descender*size)
    if replacement:
        if not page.rect.contains(new_box):
            raise DocumentError('El texto nuevo sale de la página. Reduce el tamaño.')
        if any(s['id']!=source['id'] and (new_box & fitz.Rect(s['bbox'])).get_area()>.1 for s in all_spans):
            raise DocumentError('El tamaño nuevo se cruza con otro texto. Redúcelo para mantener la separación.')
    return {**source,'target_font':font_key,'target_size':size,'target_color':color,'new_box':new_box}
