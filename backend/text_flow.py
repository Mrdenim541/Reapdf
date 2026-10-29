"""Explicit, atomic text flow through user-selected regions on existing pages."""
import math
from bisect import bisect_right
import unicodedata
import pymupdf as f
from .engine import DocumentError,open_pdf,export_pdf,finite
from .document_tools import editable
from .paragraphs import paragraph_font,prepare_text_page,region_model
from .content_tools import text_color


def regions_model(doc,regions):
    if not isinstance(regions,list) or not 1<=len(regions)<=8:raise DocumentError('Elige entre 1 y 8 regiones para el flujo.')
    if not any(isinstance(r,dict) and r.get('replace') is True for r in regions):raise DocumentError('El flujo necesita al menos un bloque original que reemplazar.')
    if doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':raise DocumentError('El flujo todavía no conserva etiquetas semánticas; este documento se mantiene sin modificar.')
    if doc.get_ocgs():raise DocumentError('El flujo todavía no admite documentos con capas.')
    result=[];rotations={};links={}
    for index,row in enumerate(regions,1):
        if not isinstance(row,dict) or set(row)!={'page','box','replace'} or type(row['replace']) is not bool:raise DocumentError('Región de flujo no válida.')
        number=row['page']
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página de flujo no válida.')
        page=doc[number]
        if number not in rotations:
            matrix=page.derotation_matrix;links[number]=[f.Rect(link['from'])*matrix for link in page.get_links()]
            rotations[number]=page.rotation;page.set_rotation(0)
        box=row['box']
        if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box):raise DocumentError('Coordenadas de flujo no válidas.')
        x,y,w,h=box;rect=f.Rect(x,y,x+w,y+h)
        if min(w,h)<10 or not page.rect.contains(rect):raise DocumentError(f'Región {index}: debe quedar dentro de la página y medir al menos 10 × 10 pt.')
        if page.get_xobjects():raise DocumentError(f'Región {index}: la página contiene Form XObjects no compatibles con este flujo.')
        if any(old['page']==number and (old['rect']&rect).get_area()>.01 for old in result):raise DocumentError('Las regiones del flujo no pueden solaparse.')
        if any(((f.Rect(d['rect'])+tuple(sign*max(.5,(d.get('width') or 0)/2) for sign in [-1,-1,1,1]))&rect).get_area()>.1 for d in page.get_drawings()):raise DocumentError(f'Región {index}: cruza gráficos vectoriales; elige un área de texto libre.')
        if row['replace']:
            _,text=region_model(doc,number,box)
        else:
            text=''
            if (any((f.Rect(b[:4])&rect).get_area()>.1 for b in page.get_text('blocks',flags=f.TEXTFLAGS_TEXT))
                or any((f.Rect(i['bbox'])&rect).get_area()>.1 for i in page.get_image_info())
                or any((a.rect&rect).get_area()>.1 for a in page.annots() or [])
                or any((w.rect&rect).get_area()>.1 for w in page.widgets() or [])
                or any(a.type[0]==f.PDF_ANNOT_REDACT for a in page.annots() or [])):
                raise DocumentError(f'Región {index}: la continuación debe estar vacía, sin texto, imágenes, campos ni anotaciones.')
        # Link rectangles are not native annotations in the high-level iterator.
        if any((bounds&rect).get_area()>.1 for bounds in links[number]):raise DocumentError(f'Región {index}: cruza un enlace; no se reemplazará.')
        result.append({'page':number,'rect':rect,'replace':row['replace'],'text':text})
    return result,rotations


def inspect_flow(base,operations,regions):
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        rows,_=regions_model(doc,regions)
        from .mixed_flow import inspect_runs
        from .original_flow import inspect_original
        return {'text':'\n\n'.join(r['text'] for r in rows if r['replace']),
                'regions':[{'page':r['page'],'text':r['text']} for r in rows],**inspect_runs(doc,rows),**inspect_original(doc,rows)}


def next_line(text,cursor,width,prefix):
    end=text.find('\n',cursor)
    if end<0:end=len(text)
    if end==cursor:return '',cursor+1,True
    if prefix[end]-prefix[cursor]<=width:return text[cursor:end],end+int(end<len(text)),True
    stop=bisect_right(prefix,prefix[cursor]+width,lo=cursor+1,hi=end+1)-1
    if stop<=cursor:raise DocumentError('Una región es demasiado estrecha para el tamaño de texto elegido.')
    space=text.rfind(' ',cursor,stop+1)
    if space>cursor:stop=space
    consumed=stop
    while consumed<end and text[consumed]==' ':consumed+=1
    return text[cursor:stop].rstrip(' '),consumed,False


def layout_flow(doc,rows,text,font,size,align,line_height):
    cursor=0;writers=[];report=[];prefix=[0.]
    for length in font.char_lengths(text,fontsize=size):prefix.append(prefix[-1]+length)
    for row in rows:
        page=doc[row['page']];rect=row['rect']+(3,3,-3,-3);writer=f.TextWriter(page.rect)
        baseline=rect.y0+font.ascender*size;lines=0;start=cursor
        while cursor<len(text) and baseline-font.descender*size<=rect.y1+.001:
            line,cursor,last=next_line(text,cursor,rect.width,prefix)
            length=font.text_length(line,fontsize=size)
            if line:
                if align==3 and not last and len(line.split())>1:
                    words=line.split();gap=(rect.width-sum(font.text_length(w,fontsize=size) for w in words))/(len(words)-1);x=rect.x0
                    for word in words:writer.append((x,baseline),word,font=font,fontsize=size);x+=font.text_length(word,fontsize=size)+gap
                else:
                    x=rect.x0+(rect.width-length)*({0:0,1:.5,2:1,3:0}[align]);writer.append((x,baseline),line,font=font,fontsize=size)
            lines+=1;baseline+=size*line_height
        writers.append(writer);report.append({'page':row['page'],'characters':cursor-start,'lines':lines,'replaces_original':row['replace']})
    return writers,report,cursor


def flow_text(base,operations,regions,text,size=12,family='sans',style='regular',color=None,align=0,line_height=1.2,auto_fit=False,min_size=8,runs=None,original_runs=None):
    if original_runs is not None:
        if runs is not None:raise DocumentError('Elige un solo modo de fuentes para el flujo.')
        from .original_flow import flow
        return flow(base,operations,regions,text,original_runs,align,line_height,auto_fit,min_size)
    if not isinstance(text,str) or not text.strip() or len(text)>12000 or any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} for c in text):raise DocumentError('Usa entre 1 y 12000 caracteres, sin controles ni escritura de derecha a izquierda.')
    if not finite(size) or not 6<=size<=72 or not finite(min_size) or not 6<=min_size<=(size if runs is None else 72) or type(auto_fit) is not bool or type(align) is not int or align not in [0,1,2,3] or not finite(line_height) or not 1<=line_height<=2.5:raise DocumentError('Formato de flujo no válido: tamaño 6–72 pt e interlineado 1–2,5.')
    color=text_color([0,0,0] if color is None else color);font=paragraph_font(family,style)
    if runs is None and any(c!='\n' and not font.has_glyph(ord(c),fallback=0) for c in text):raise DocumentError('La fuente elegida no cubre alguno de los caracteres.')
    with open_pdf(base) as source:editable(source)
    with open_pdf(export_pdf(base,operations)) as doc:
        rows,rotations=regions_model(doc,regions);chosen=size
        mixed_report=None
        if runs is not None:
            from .mixed_flow import plan_mixed
            draws,details,mixed_report=plan_mixed(doc,rows,text,runs,align,line_height,auto_fit,min_size,next_line)
            consumed=len(text);writers=[]
        else:
            sizes=[size]+([round(size-i*.5,4) for i in range(1,math.floor((size-min_size)/.5)+1)]+[min_size] if auto_fit else [])
            for chosen in dict.fromkeys(sizes):
                try:writers,details,consumed=layout_flow(doc,rows,text,font,chosen,align,line_height)
                except DocumentError:
                    if auto_fit:continue
                    raise
                if consumed==len(text):break
            else:
                raise DocumentError('El texto no cabe en las regiones elegidas. Añade espacio o reduce el tamaño; no se aplica un flujo incompleto.')
        # Complete every plan before changing any page. Redaction must run once
        # per page, with shared resource dictionaries detached first.
        from .styled_text import clone_resources
        for number in rotations:
            page=doc[number];replaced=[r for r in rows if r['page']==number and r['replace']]
            if replaced:
                clone_resources(doc,page)
                for row in replaced:page.add_redact_annot(row['rect'],fill=False,cross_out=False)
                page.apply_redactions(images=0,graphics=0,text=0);page.wrap_contents()
        for row,writer,detail in zip(rows,writers,details):
            if not writer.text_rect.is_empty:writer.write_text(doc[row['page']],color=color)
        if runs is not None:
            from .mixed_flow import draw_mixed
            draw_mixed(doc,draws)
        doc.subset_fonts()
        for number,rotation in rotations.items():doc[number].set_rotation(rotation)
        data=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
        if runs is not None:
            from .mixed_flow import verify_mixed
            verify_mixed(data,rows,text)
        return data,{'mode':'mixed' if runs is not None else 'uniform',**({'mixed':mixed_report,'text_verified':True} if mixed_report else {}),'size':None if mixed_report else chosen,'requested_size':None if mixed_report else size,'adjusted':mixed_report['adjusted'] if mixed_report else chosen!=size,'characters':consumed,'regions':details,'pages':sorted(rotations),'complete':True}
