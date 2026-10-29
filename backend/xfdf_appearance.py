"""Explicit plain annotation appearance fields; no rich text or resource fetching."""
import re
from .engine import DocumentError
from .pdf_content import operations,numbers
FONTS={'Helv':'Helvetica','TiRo':'Times-Roman','Cour':'Courier','Helvetica':'Helvetica','Times-Roman':'Times-Roman','Courier':'Courier'}
FLAGS={'invisible':1,'hidden':2,'print':4,'nozoom':8,'norotate':16,'noview':32,'readonly':64,'locked':128,'togglenoview':256,'lockedcontents':512}
ICONS={'Comment','Key','Note','Help','NewParagraph','Paragraph','Insert','Circle','Cross','Check','Star','RightArrow','RightPointer','UpArrow','UpLeftArrow'}


def rgb(text):
    if not isinstance(text,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',text):raise DocumentError('Color XFDF no compatible.')
    return [int(text[i:i+2],16)/255 for i in [1,3,5]]


def hex_color(value):
    from .existing_annotations import display_rgb
    return '#'+''.join(f'{round(v*255):02X}' for v in display_rgb(value))


def free_text(doc,a):
    if doc.xref_get_key(a.xref,'IT') not in [('null','null'),('name','/FreeText'),('name','/FreeTextTypeWriter')] or any(doc.xref_get_key(a.xref,k)[0]!='null' for k in ['RC','DS']):raise DocumentError('Solo se intercambia texto libre sencillo, sin llamadas ni estilos enriquecidos.')
    kind,da=doc.xref_get_key(a.xref,'DA')
    if kind!='string' or len(da)>2000:raise DocumentError('Apariencia de texto libre no compatible.')
    font=None;size=None;color=[0,0,0]
    for op,args,_ in operations(da.encode('utf-8')):
        if op=='Tf' and len(args)==2 and args[0].kind=='name' and args[1].kind=='number':font=args[0].value;size=args[1].value
        elif op=='rg':color=numbers(args,3)
        elif op=='g':color=numbers(args,1)*3
        else:raise DocumentError('Apariencia de texto libre no compatible.')
    if font not in FONTS or size is None or not 3<=size<=72 or any(not 0<=c<=1 for c in color):raise DocumentError('Fuente o color de texto libre fuera del subconjunto compatible.')
    # The same alias may refer to a different embedded font. Never silently
    # substitute it merely because its resource name resembles a base font.
    for key in ['Resources/Font/'+font,'AP/N/Resources/Font/'+font]:
        kind,value=doc.xref_get_key(a.xref,key)
        if kind=='xref':
            ref=int(value.split()[0]);base=doc.xref_get_key(ref,'BaseFont')
            if base!=('name','/'+FONTS[font]) or any(doc.xref_get_key(ref,'FontDescriptor/'+k)[0]!='null' for k in ['FontFile','FontFile2','FontFile3']):raise DocumentError('La fuente incrustada de texto libre necesita otra conversión.')
    kind,q=doc.xref_get_key(a.xref,'Q');align=int(q) if kind=='int' else 0;rotation=a.rotation
    if align not in [0,1,2] or rotation not in [-1,0,90,180,270]:raise DocumentError('Alineación o giro de texto libre no compatible.')
    return {'font':FONTS[font],'size':str(size),'justification':str(align),'rotation':str(max(0,rotation)),'text-color':hex_color(color)}


def export_attributes(doc,a,kind):
    from .xfdf import clean,number
    result={};flags=a.flags
    if flags&~1023:raise DocumentError('Indicadores de anotación no compatibles.')
    result['flags']=','.join(name for name,mask in FLAGS.items() if flags&mask)
    for key,label in [('subject','subject'),('creationDate','creationdate'),('modDate','date')]:
        if a.info.get(key):result[label]=clean(a.info[key],200)
    border=a.border;style=border.get('style')
    if style not in [None,'S','D'] or border.get('clouds',-1)>0:raise DocumentError('Borde de anotación no compatible.')
    from .xfdf import values
    dash_kind,dash_value=doc.xref_get_key(a.xref,'BS/D');dashes=values(dash_value.strip('[]')) if dash_kind=='array' else border.get('dashes') or []
    if dashes:result['dashes']=','.join(number(v) for v in validate_dashes(dashes))
    if kind in ['square','circle']:
        from .xfdf import values
        width=max(.25,a.border.get('width',1));rd_kind,rd=doc.xref_get_key(a.xref,'RD');fringe=values(rd.strip('[]'),4) if rd_kind=='array' else [max(1,width/2)]*4
        if any(abs(v-max(1,width/2))>.001 for v in fringe):raise DocumentError('Los márgenes de la figura necesitan otro tratamiento.')
        result['fringe']=','.join(number(v) for v in fringe)
    if kind=='freetext':
        result.update(free_text(doc,a));fill=a.colors.get('stroke')
        if fill:result['interior-color']=hex_color(fill)
        result['width']=number(max(0,a.border.get('width',0)))
    elif kind in ['square','circle','polygon','line','polyline'] and a.colors.get('fill'):result['interior-color']=hex_color(a.colors['fill'])
    if kind=='text':
        name=a.info.get('name') or 'Note'
        if name not in ICONS:raise DocumentError('Icono de nota no compatible.')
        result['icon']=name;result['open']='yes' if doc.xref_get_key(a.xref,'Open')==('bool','true') else 'no'
    return result


def validate_dashes(values):
    from .engine import finite
    if not isinstance(values,(list,tuple)) or not 1<=len(values)<=8 or any(not finite(v) or not 0<=v<=100 for v in values) or not any(v>0 for v in values):raise DocumentError('Patrón de borde XFDF no compatible.')
    return list(values)


def parse_attributes(node,kind):
    from .xfdf import clean,values
    unsupported=['callout','richtext','intent','style','appearance','href']
    if any(node.get(k) is not None for k in unsupported):raise DocumentError('La apariencia XFDF necesita una importación adicional; no se descarta silenciosamente.')
    flags=0
    if 'flags' in node.attrib:
        raw=node.get('flags','')
        if len(raw)>200:raise DocumentError('Indicadores XFDF fuera de límites.')
        for name in [p.strip().lower() for p in raw.split(',') if p.strip()]:
            if name not in FLAGS:raise DocumentError('Indicador XFDF no compatible.')
            flags|=FLAGS[name]
    else:flags=4
    result={'flags':flags,'fill':rgb(node.get('interior-color')) if node.get('interior-color') is not None else None,'dashes':validate_dashes(values(node.get('dashes'))) if node.get('dashes') is not None else [],'info':{label:clean(node.get(key),200) for key,label in [('subject','subject'),('creationdate','creationDate'),('date','modDate')] if node.get(key) is not None}}
    if node.get('fringe') is not None:
        if kind not in ['square','circle']:raise DocumentError('Margen XFDF no compatible para este tipo.')
        fringe=values(node.get('fringe'),4);width=values(node.get('width','1'),1)[0]
        if any(v<0 or abs(v-max(1,width/2))>.001 for v in fringe):raise DocumentError('Los márgenes de la figura necesitan otro tratamiento.')
        result['fringe']=fringe
    if kind=='text':
        result['icon']=node.get('icon','Note');result['open']=node.get('open','no')
        if result['icon'] not in ICONS or result['open'] not in ['yes','no']:raise DocumentError('Icono o apertura de nota no compatible.')
    if kind=='freetext':
        font=node.get('font','Helvetica');size=values(node.get('size','12'),1)[0]
        try:align=int(node.get('justification','0'));rotation=int(node.get('rotation','0'))
        except ValueError as exc:raise DocumentError('Alineación o giro XFDF no válido.') from exc
        if font not in FONTS or not 3<=size<=72 or align not in [0,1,2] or rotation not in [0,90,180,270]:raise DocumentError('Fuente, tamaño o giro de texto libre no compatible.')
        result.update(font=FONTS[font],size=size,align=align,rotation=rotation,text_color=rgb(node.get('text-color',node.get('color','#000000'))))
    elif node.get('rotation') not in [None,'0']:raise DocumentError('Este giro de anotación XFDF no se conserva.')
    if result['fill'] is not None and kind not in ['freetext','square','circle','polygon','line','polyline']:raise DocumentError('Este tipo no admite relleno XFDF.')
    return result


def apply_border(doc,annot,width,dashes):
    import pymupdf as f
    if annot.type[0] not in [f.PDF_ANNOT_CIRCLE,f.PDF_ANNOT_FREE_TEXT,f.PDF_ANNOT_INK,f.PDF_ANNOT_LINE,f.PDF_ANNOT_POLY_LINE,f.PDF_ANNOT_POLYGON,f.PDF_ANNOT_SQUARE]:
        if dashes:raise DocumentError('Este tipo de anotación no admite borde discontinuo.')
        return
    annot.set_border(width=width,style='D' if dashes else 'S')
    if dashes:
        n=f.mupdf;pdf=f._as_pdf_document(doc);array=n.pdf_new_array(pdf,len(dashes))
        for value in dashes:n.pdf_array_push(array,n.pdf_new_real(value))
        border=n.pdf_dict_gets(n.pdf_annot_obj(annot.this),'BS');n.pdf_dict_puts(border,'D',array)
