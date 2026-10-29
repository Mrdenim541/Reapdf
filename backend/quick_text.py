"""Click-to-type text with automatic height and an explicit wrap width."""
import unicodedata
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .paragraphs import paragraph_font
from .content_tools import text_color
from .text_flow import next_line


def insert(base,ops,number,point,text,size=12,family='sans',style='regular',color=None,width=240,preview=False):
    if not isinstance(text,str) or not text.strip() or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Escribe de 1 a 4000 caracteres, sin controles ni escritura de derecha a izquierda.')
    if not finite(size) or not 6<=size<=72 or not finite(width) or not 20<=width<=6000:raise DocumentError('Tamaño 6–72 pt y ancho mínimo de 20 pt.')
    font=paragraph_font(family,style);color=text_color([0,0,0] if color is None else color)
    if any(c!='\n' and not font.has_glyph(ord(c),fallback=0) for c in text):raise DocumentError('La fuente incluida no contiene alguno de los caracteres.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,ops)) as doc:
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
        page=doc[number]
        if not isinstance(point,list) or len(point)!=2 or any(not finite(v) for v in point) or not page.rect.contains(f.Point(point)):raise DocumentError('Pulsa un punto dentro de la página.')
        x,y=point;width=min(width,page.rect.width-x-2)
        if width<20:raise DocumentError('Pulsa más lejos del borde derecho de la página.')
        prefix=[0.]
        for value in font.char_lengths(text,fontsize=size):prefix.append(prefix[-1]+value)
        cursor=0;baseline=y+font.ascender*size;lines=[]
        while cursor<len(text):
            line,cursor,_=next_line(text,cursor,width,prefix);lines.append((line,baseline));baseline+=size*1.35
        bottom=lines[-1][1]-font.descender*size
        if bottom>page.rect.height-1:raise DocumentError('El texto sale de la página. Amplía el ancho, reduce su tamaño o elige un punto más alto.')
        box=f.Rect(x,y,x+width,bottom);native=box*page.derotation_matrix
        for block in page.get_text('dict',flags=f.TEXTFLAGS_TEXT)['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    if (f.Rect(span['bbox'])&native).get_area()>.1:raise DocumentError('El área automática cruza texto existente. Cambia el punto o el ancho para no taparlo.')
        if any((a.rect&native).get_area()>.1 for a in page.annots() or []) or any((w.rect&native).get_area()>.1 for w in page.widgets() or []):raise DocumentError('El área cruza campos o anotaciones.')
        report={'box':list(box),'lines':len(lines),'size':size,'width':width}
        if preview:return report
        if not page.rotation:
            writer=f.TextWriter(page.rect)
            for line,baseline in lines:
                if line:writer.append((x,baseline),line,font=font,fontsize=size)
            writer.write_text(page,color=color)
        else:
            # Visible coordinates for a rotated page require an oriented overlay.
            with f.open() as overlay:
                target=overlay.new_page(width=page.rect.width,height=page.rect.height);writer=f.TextWriter(target.rect)
                for line,baseline in lines:
                    if line:writer.append((x,baseline),line,font=font,fontsize=size)
                writer.write_text(target,color=color);rotation=page.rotation;rect=page.rect*page.derotation_matrix;page.set_rotation(0)
                try:page.show_pdf_page(rect,overlay,0,rotate=rotation,overlay=True)
                finally:page.set_rotation(rotation)
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True),report
