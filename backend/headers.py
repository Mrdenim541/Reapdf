"""Encabezados, pies y números vectoriales sobre márgenes visibles."""
import re
import pymupdf as fitz
from .engine import DocumentError,finite
from .content_tools import prepare_content,add_content,text_color
from .text_style import FONT_OPTIONS

SLOT_LABELS=['encabezado izquierdo','encabezado central','encabezado derecho','pie izquierdo','pie central','pie derecho']
SLOTS=['top_left','top_center','top_right','bottom_left','bottom_center','bottom_right']
TOKENS={'pagina','total','numero'}


def roman(number):
    result=''
    for value,symbol in [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
        count,number=divmod(number,value);result+=symbol*count
    return result


def expand_template(template,page,total,sequence,style,padding):
    if style in {'R','r'}:
        if sequence>3999:raise DocumentError('La numeración romana admite números de 1 a 3999.')
        number=roman(sequence);number=number.lower() if style=='r' else number
    else:number=str(sequence).zfill(padding)
    values={'pagina':str(page+1),'total':str(total),'numero':number}
    return re.sub(r'\{([^{}]+)\}',lambda m:values[m[1]],template)


def prepare_headers(doc,op):
    pages=op.get('pages');slots=op.get('slots');font=op.get('font','helv');size=op.get('size',10)
    if not isinstance(pages,list) or not pages or len(pages)>len(doc) or len(set(p for p in pages if type(p) is int))!=len(pages) or any(type(p) is not int or not 0<=p<len(doc) for p in pages):
        raise DocumentError('Elige páginas válidas, sin repeticiones, para encabezados y pies.')
    if not isinstance(slots,dict) or set(slots)!=set(SLOTS) or not any(isinstance(v,str) and v.strip() for v in slots.values()):
        raise DocumentError('Completa al menos una de las seis posiciones.')
    for text in slots.values():
        if not isinstance(text,str) or len(text)>200 or any(ord(c)<32 or ord(c)>255 for c in text):
            raise DocumentError('Cada posición admite una línea de hasta 200 caracteres latinos.')
        if any(token not in TOKENS for token in re.findall(r'\{([^{}]*)\}',text)) or re.sub(r'\{(pagina|total|numero)\}','',text).count('{') or re.sub(r'\{(pagina|total|numero)\}','',text).count('}'):
            raise DocumentError('Usa solo las variables {pagina}, {total} y {numero}, con llaves completas.')
    if not isinstance(font,str) or font not in dict(FONT_OPTIONS) or not finite(size) or not 6<=size<=36:
        raise DocumentError('Elige una fuente base y tamaño entre 6 y 36 puntos.')
    color=text_color(op.get('color'))
    margins=op.get('margins',[20,24,20,24])
    if not isinstance(margins,list) or len(margins)!=4 or any(not finite(v) or not 0<=v<=1000 for v in margins):
        raise DocumentError('Indica márgenes superior, derecho, inferior e izquierdo entre 0 y 1000 puntos.')
    start,style,padding=op.get('start',1),op.get('style','D'),op.get('padding',0)
    if type(start) is not int or not 1<=start<=999999 or type(padding) is not int or not 0<=padding<=8 or not isinstance(style,str) or style not in {'D','R','r'}:
        raise DocumentError('Numeración no válida: inicio 1–999999, ceros 0–8 y formato decimal o romano.')
    if start+len(pages)-1>999999:raise DocumentError('La numeración supera 999999.')
    if style in {'R','r'} and start+len(pages)-1>3999:raise DocumentError('La numeración romana admite números de 1 a 3999.')
    face=fitz.Font(font);band=size*(face.ascender-2*face.descender+.5);result=[]
    for offset,number in enumerate(pages):
        page=doc[number];top,right,bottom,left=margins
        width=(page.rect.width-left-right)/3
        if width<10 or page.rect.height-top-bottom<2*band+5:
            raise DocumentError(f'Los márgenes no dejan espacio suficiente en la página {number+1}.')
        for index,key in enumerate(SLOTS):
            value=slots[key]
            if not value.strip():continue
            text=expand_template(value,number,len(doc),start+offset,style,padding)
            if face.text_length(text,fontsize=size)>width-4:
                raise DocumentError(f'El texto del {SLOT_LABELS[index]} no cabe en la página {number+1}. Acórtalo o reduce su tamaño.')
            x=left+(index%3)*width;y=top if index<3 else page.rect.height-bottom-band
            op_text={'type':'textbox','points':[[x,y],[x+width-4,y+band]],'text':text,'font':font,'size':size,'color':color,'align':index%3}
            result.append((number,prepare_content(doc,page,op_text)))
    return result


def apply_headers(doc,prepared):
    for number,text in prepared:add_content(doc[number],'textbox',text)
