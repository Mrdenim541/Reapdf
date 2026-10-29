"""Reemplazo explícito de bloques digitales con fuente libre y control de espacio."""
from pathlib import Path
import pymupdf as fitz
from .engine import open_pdf,export_pdf,DocumentError,finite
from .document_tools import editable
from .content_tools import text_color
FONT_DIR=Path(__file__).resolve().parent.parent/'resources'/'fonts'
FONT_FILE=FONT_DIR/'DejaVuSans.ttf'
FAMILIES={'sans':'DejaVuSans','serif':'DejaVuSerif','mono':'DejaVuSansMono'}


def prepare_text_page(doc,number):
    """Edit in native, unrotated CropBox coordinates on an expendable snapshot.

    Callers that serialize must restore the returned rotation first. This keeps
    original text/font geometry and avoids rotating or rasterizing PDF content.
    """
    if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página no válida.')
    page=doc[number];rotation=page.rotation
    page.set_rotation(0)
    return page,rotation


def paragraph_preview(base,operations,number,scale=1):
    from .rendering import render_page
    with open_pdf(export_pdf(base,operations)) as doc:
        page,rotation=prepare_text_page(doc,number)
        image,headers=render_page(page,scale)
        headers['X-Page-Rotation']=str(rotation)
        return image,headers


def paragraph_format(page,rect):
    spans=[s for b in page.get_text('dict',flags=fitz.TEXTFLAGS_TEXT,sort=True)['blocks'] for line in b.get('lines',[]) for s in line['spans'] if rect.contains(fitz.Rect(s['bbox'])) and s['text'].strip()]
    if not spans:return None
    def model(span):
        flags=span['flags'];bold=bool(flags&16);italic=bool(flags&2)
        # Some producers mark embedded Sans resources as serif. Prefer known
        # family names when choosing an explicitly approximate bundled font.
        name=span['font'].lower().replace(' ','').replace('-','')
        mono=bool(flags&8) or any(value in name for value in ['courier','mono'])
        sans=any(value in name for value in ['dejavusans','liberationsans','notosans','helvetica','arial','calibri','aptos'])
        family='mono' if mono else 'sans' if sans else 'serif' if flags&4 else 'sans'
        return {'size':max(6,min(72,round(span['size'],2))), 'color':'#'+format(span['color'],'06x'),
                'family':family,
                'style':'bold-italic' if bold and italic else 'bold' if bold else 'italic' if italic else 'regular'}
    first=model(spans[0]);return first|{'mixed':any(model(v)!=first for v in spans[1:])}


def paragraph_blocks(base,operations,number):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        page,_=prepare_text_page(doc,number);result=[]
        for block in page.get_text('dict',flags=fitz.TEXTFLAGS_TEXT,sort=True)['blocks']:
            if block.get('type')!=0:continue
            rect=(fitz.Rect(block['bbox'])+(-2,-2,2,2))&page.rect
            box=[rect.x0,rect.y0,rect.width,rect.height]
            try:_,text=region_model(doc,number,box)
            except DocumentError:continue
            result.append({'box':box,'text':text[:160]})
            if len(result)>=100:break
        return {'blocks':result}


def paragraph_font(family,style):
    if not isinstance(family,str) or family not in FAMILIES or not isinstance(style,str) or style not in ['regular','bold','italic','bold-italic']:
        raise DocumentError('Familia o estilo de párrafo no válido.')
    italic='Italic' if family=='serif' else 'Oblique'
    suffix={'regular':'','bold':'-Bold','italic':'-'+italic,'bold-italic':'-Bold'+italic}[style]
    return fitz.Font(fontfile=str(FONT_DIR/(FAMILIES[family]+suffix+'.ttf')))


def paragraph_layout(page,rect,text,font,size,align,line_height,auto_fit,min_size):
    if not finite(line_height) or not 1<=line_height<=2.5:raise DocumentError('El interlineado debe estar entre 1 y 2,5.')
    if type(auto_fit) is not bool or not finite(min_size) or not 6<=min_size<=72 or (auto_fit and min_size>size):raise DocumentError('El tamaño mínimo debe estar entre 6 pt y el tamaño solicitado.')
    # A bounded descending grid avoids relying on monotonic wrapping at word boundaries.
    sizes=[size]
    if auto_fit:
        sizes += [round(size-i*.25,4) for i in range(1,int((size-min_size)/.25)+1)]
        if sizes[-1]!=min_size:sizes.append(min_size)
    for chosen in sizes:
        writer=fitz.TextWriter(page.rect)
        try:overflow=writer.fill_textbox(rect+(2,2,-2,-2),text,font=font,fontsize=chosen,align=align,lineheight=line_height,warn=None) if text else []
        except ValueError:continue
        if not overflow:
            return writer,{'requested_size':size,'size':chosen,'adjusted':chosen!=size,'line_height':line_height}
    raise DocumentError('El párrafo no cabe. Amplía la región, reduce tamaño o acorta el texto.')


def region_model(doc,number,box):
    if type(number) is not int or not 0<=number<len(doc) or not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Página o región de párrafo no válida.')
    page=doc[number];x,y,w,h=box;rect=fitz.Rect(x,y,x+w,y+h)
    if page.rotation or min(w,h)<10 or not page.rect.contains(rect):raise DocumentError('Elige un bloque dentro de una página sin giro, de al menos 10 × 10 pt.')
    if any(a.type[0]==fitz.PDF_ANNOT_REDACT for a in page.annots() or []):raise DocumentError('La página contiene censuras pendientes. Resuélvelas antes de editar el bloque.')
    if any((fitz.Rect(info['bbox'])&rect).get_area()>.1 for info in page.get_image_info()):raise DocumentError('El bloque cruza una imagen o escaneado. No se reemplazará su texto como párrafo digital.')
    if any((a.rect&rect).get_area()>.1 for a in page.annots() or []) or any((w.rect&rect).get_area()>.1 for w in page.widgets() or []):raise DocumentError('El bloque cruza campos o anotaciones. No se modificará.')
    lines=[]
    for block in page.get_text('dict',flags=fitz.TEXTFLAGS_TEXT,sort=True)['blocks']:
        for line in block.get('lines',[]):
            selected=[]
            for span in line['spans']:
                bounds=fitz.Rect(span['bbox'])
                if (bounds&rect).get_area()<=.1:continue
                if not (rect+(-.01,-.01,.01,.01)).contains(bounds):raise DocumentError('La región corta un fragmento de texto. Amplía sus bordes para contenerlo completo.')
                if tuple(line['dir'])!=(1.,0.) or span.get('alpha',255)!=255:raise DocumentError('El bloque contiene texto inclinado o transparente no compatible.')
                selected.append(span['text'])
            if selected:lines.append(''.join(selected))
    if not lines:raise DocumentError('No hay texto digital completo en esta región.')
    text='\n'.join(lines)
    if len(text)>4000:raise DocumentError('El bloque supera 4000 caracteres. Divide la edición en regiones menores.')
    return rect,text


def inspect_paragraph(base,operations,number,box):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        page,rotation=prepare_text_page(doc,number)
        rect,text=region_model(doc,number,box);return {'text':text,'rect':list(rect),'rotation':rotation,'format':paragraph_format(page,rect)}


def replace_paragraph(base,operations,number,box,text,size=12,color=None,align=0,family='sans',style='regular',line_height=1.2,auto_fit=False,min_size=6,return_report=False):
    if not isinstance(text,str) or len(text)>4000 or any((ord(c)<32 and c!='\n') or ord(c)==127 for c in text):raise DocumentError('Usa hasta 4000 caracteres, con saltos de línea y sin controles.')
    if not finite(size) or not 6<=size<=72 or type(align) is not int or align not in [0,1,2,3]:raise DocumentError('Tamaño o alineación de párrafo no válidos.')
    color=text_color([0,0,0] if color is None else color);font=paragraph_font(family,style)
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        page,rotation=prepare_text_page(doc,number)
        rect,_=region_model(doc,number,box)
        if any(c!='\n' and not font.has_glyph(ord(c),fallback=0) for c in text):raise DocumentError('La fuente elegida no cubre alguno de los caracteres indicados.')
        writer,report=paragraph_layout(page,rect,text,font,size,align,line_height,auto_fit,min_size)
        # Native redaction cleans font resources: detach shared dictionaries first.
        from .styled_text import clone_resources
        clone_resources(doc,page)
        page.add_redact_annot(rect,fill=False,cross_out=False);page.apply_redactions(images=0,graphics=0,text=0)
        page.wrap_contents()
        if text:writer.write_text(page,color=color)
        doc.subset_fonts()
        page.set_rotation(rotation)
        data=doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        return (data,report) if return_report else data
