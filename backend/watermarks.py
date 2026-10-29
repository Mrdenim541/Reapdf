"""Marca de agua vectorial en coordenadas visibles, sin rasterizar el PDF."""
import math
import pymupdf as fitz
from .engine import DocumentError,finite
from .document_tools import selected_pages
from .content_tools import text_color


def prepare_watermark(doc,op):
    pages=selected_pages(doc,op.get('pages'));text=op.get('text');size=op.get('size',48);opacity=op.get('opacity',.15);angle=op.get('angle',45);color=text_color(op.get('color'))
    if not isinstance(text,str) or not text.strip() or len(text)>120 or any(ord(c)<32 or ord(c)>255 for c in text):raise DocumentError('La marca de agua admite una línea de 1 a 120 caracteres latinos.')
    if not finite(size) or not 12<=size<=144 or not finite(opacity) or not .05<=opacity<=.75 or type(angle) is not int or angle not in [-45,0,45]:raise DocumentError('Elige tamaño 12–144 pt, opacidad 5–75 % y ángulo -45, 0 o 45 grados.')
    face=fitz.Font('hebo');width=face.text_length(text,fontsize=size);height=size*(face.ascender-face.descender)
    for n in pages:
        rect=doc[n].rect;a=math.radians(angle)
        if abs(width*math.cos(a))+abs(height*math.sin(a))>rect.width-20 or abs(width*math.sin(a))+abs(height*math.cos(a))>rect.height-20:
            raise DocumentError(f'La marca de agua no cabe en la página {n+1}. Reduce texto o tamaño.')
    return pages,text,size,opacity,angle,color


def apply_watermark(doc,prepared):
    pages,text,size,opacity,angle,color=prepared
    for n in pages:
        page=doc[n];visible=page.rect
        with fitz.open() as template:
            p=template.new_page(width=visible.width,height=visible.height)
            width=fitz.Font('hebo').text_length(text,fontsize=size)
            center=fitz.Point(visible.width/2,visible.height/2)
            origin=fitz.Point(center.x-width/2,center.y+size*.35)
            p.insert_text(origin,text,fontname='hebo',fontsize=size,color=color,fill_opacity=opacity,morph=(center,fitz.Matrix(angle)))
            rotation=page.rotation;target=visible*page.derotation_matrix
            try:
                page.set_rotation(0);page.show_pdf_page(target,template,0,rotate=rotation,overlay=True)
            finally:page.set_rotation(rotation)
