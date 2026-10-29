"""Bounded mixed-style flow using explicit, editable runs and bundled fonts."""
import math,re,unicodedata
import pymupdf as f
from .engine import DocumentError,finite
from .paragraphs import paragraph_font
from .content_tools import text_color

KEYS={'text','family','style','size','color'}

def validate_runs(runs,text):
    if not isinstance(text,str) or not text.strip() or len(text)>12000:raise DocumentError('El flujo mixto admite hasta 12000 caracteres de texto.')
    if not isinstance(runs,list) or not 1<=len(runs)<=200:raise DocumentError('El formato mixto admite de 1 a 200 fragmentos.')
    result=[];fonts={}
    for row in runs:
        if not isinstance(row,dict) or set(row)!=KEYS or not isinstance(row['text'],str) or not row['text'] or len(row['text'])>12000:raise DocumentError('Cada fragmento necesita texto, familia, estilo, tamaño y color compatibles.')
        if not finite(row['size']) or not 6<=row['size']<=72:raise DocumentError('Los tamaños de fragmento deben estar entre 6 y 72 pt.')
        family,style=row['family'],row['style']
        # Validate before building a tuple so malicious arrays do not raise TypeError.
        if not isinstance(family,str) or not isinstance(style,str):raise DocumentError('Familia o estilo del fragmento no válidos.')
        key=family,style
        if key not in fonts:fonts[key]=paragraph_font(family,style)
        font=fonts[key]
        if any((ord(c)<32 and c!='\n') or ord(c)==127 or unicodedata.bidirectional(c) in {'R','AL','AN'} or (c!='\n' and not font.has_glyph(ord(c),fallback=0)) for c in row['text']):raise DocumentError('Un fragmento contiene controles, escritura de derecha a izquierda o caracteres sin glifo compatible.')
        color=text_color(row['color'])
        result.append({**row,'color':color,'font':font})
    if ''.join(row['text'] for row in result)!=text:raise DocumentError('El texto completo y los fragmentos no coinciden. Reúne o revisa el formato antes de comparar.')
    return result


def inspect_runs(doc,rows):
    result=[];original_fonts=set()
    def add(text,style):
        if not text:return
        if result and all(result[-1][k]==style[k] for k in KEYS-{'text'}):result[-1]['text']+=text
        else:result.append({'text':text,**style})
    for row in rows:
        if not row['replace']:continue
        lines=[]
        for block in doc[row['page']].get_text('dict',flags=f.TEXTFLAGS_TEXT,sort=True)['blocks']:
            for line in block.get('lines',[]):
                spans=[s for s in line['spans'] if (row['rect']+(-.01,-.01,.01,.01)).contains(f.Rect(s['bbox'])) and s['text']]
                if spans:lines.append(spans)
        if result:add('\n\n',{k:v for k,v in result[-1].items() if k!='text'})
        for index,spans in enumerate(lines):
            if index:add('\n',{k:v for k,v in result[-1].items() if k!='text'})
            for span in spans:
                flags=span['flags'];bold=bool(flags&16);italic=bool(flags&2);color=span['color']
                name=span['font'].lower()
                family='mono' if flags&8 or 'mono' in name or 'courier' in name else 'sans' if 'sans' in name or 'arial' in name or 'helvetica' in name else 'serif' if flags&4 or 'times' in name else 'sans'
                style={'family':family,
                       'style':'bold-italic' if bold and italic else 'bold' if bold else 'italic' if italic else 'regular',
                       'size':round(span['size'],4),'color':[((color>>shift)&255)/255 for shift in [16,8,0]]}
                original_fonts.add(span['font']);add(span['text'],style)
    text='\n\n'.join(r['text'] for r in rows if r['replace'])
    try:validate_runs(result,text)
    except DocumentError as exc:return {'runs':[],'mixed_supported':False,'mixed_reason':str(exc),'source_fonts':sorted(original_fonts)}
    return {'runs':result,'mixed_supported':True,'mixed_reason':'','source_fonts':sorted(original_fonts),
            'font_notice':'Las familias originales se sustituyen por Sans, Serif o Monoespaciada de Reapdf. Se conservan estilos compatibles, tamaños y colores; no la fuente exacta.'}


def layout_mixed(doc,rows,text,runs,scale,align,line_height,next_line):
    prefix=[0.];styles=[]
    for run in runs:
        size=run['size']*scale
        lengths=run['font'].char_lengths(run['text'],fontsize=size)
        for char,length in zip(run['text'],lengths):
            prefix.append(prefix[-1]+(0 if char=='\n' else length));styles.append(run)
    cursor=0;draws=[];details=[]
    for row in rows:
        rect=row['rect']+(3,3,-3,-3);top=rect.y0;start=cursor;lines=0
        while cursor<len(text):
            before=cursor;line,after,last=next_line(text,cursor,rect.width,prefix)
            line_styles=styles[before:before+max(1,len(line))]
            ascent=max(r['font'].ascender*r['size']*scale for r in line_styles)
            descent=max(-r['font'].descender*r['size']*scale for r in line_styles)
            max_size=max(r['size']*scale for r in line_styles)
            if top+ascent+descent>rect.y1+.001:break
            baseline=top+ascent;length=prefix[before+len(line)]-prefix[before]
            justify=align==3 and not last and ' ' in line.strip(' ')
            gap=(rect.width-length)/line.count(' ') if justify else 0
            x=rect.x0+(rect.width-length)*({0:0,1:.5,2:1,3:0}[align]);offset=0
            while offset<len(line):
                run=styles[before+offset];end=offset+1
                while end<len(line) and styles[before+end] is run and not(justify and line[end-1]==' '):end+=1
                fragment=line[offset:end];size=run['size']*scale
                if fragment.strip():draws.append({'page':row['page'],'origin':(x,baseline),'text':fragment,'font':run['font'],'size':size,'color':run['color']})
                x+=prefix[before+end]-prefix[before+offset]+gap*fragment.count(' ');offset=end
            cursor=after;lines+=1;top+=max(ascent+descent,max_size*line_height)
        details.append({'page':row['page'],'characters':cursor-start,'lines':lines,'replaces_original':row['replace']})
    return draws,details,cursor


def plan_mixed(doc,rows,text,runs,align,line_height,auto_fit,min_size,next_line):
    parsed=validate_runs(runs,text);smallest=min(r['size'] for r in parsed);largest=max(r['size'] for r in parsed)
    if auto_fit and min_size>smallest:raise DocumentError('El mínimo del ajuste no puede superar el menor tamaño de los fragmentos.')
    minimum=max(6,min_size)/smallest
    scales=[1.]
    if auto_fit:
        scales += [round(1-i*.025,6) for i in range(1,math.floor((1-minimum)/.025)+1)]+[minimum]
    for scale in dict.fromkeys(scales):
        try:draws,details,consumed=layout_mixed(doc,rows,text,parsed,scale,align,line_height,next_line)
        except DocumentError:
            if auto_fit:continue
            raise
        if consumed==len(text):return draws,details,{'scale':scale,'adjusted':scale!=1,'min_size':smallest*scale,'max_size':largest*scale,'fragments':len(runs)}
    raise DocumentError('El texto con formato mixto no cabe completo. Añade regiones, reduce tamaños o activa el ajuste proporcional; no se aplica parcialmente.')


def draw_mixed(doc,draws):
    # Keep native content in reading order, including differently colored runs.
    for item in draws:
        writer=f.TextWriter(doc[item['page']].rect)
        writer.append(item['origin'],item['text'],font=item['font'],fontsize=item['size'])
        writer.write_text(doc[item['page']],color=item['color'])


def verify_mixed(data,rows,text):
    def clean(value):return re.sub(r'\s+','',unicodedata.normalize('NFKC',value))
    with f.open(stream=data) as doc:
        for page in doc:page.set_rotation(0)
        actual=''
        for row in rows:
            page=doc[row['page']];actual+=page.get_text(clip=row['rect'],sort=False)
            for block in page.get_text('dict',clip=row['rect'])['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if not (row['rect']+(-.02,-.02,.02,.02)).contains(f.Rect(span['bbox'])):raise DocumentError('El formato mixto excede una región. No se entrega un flujo recortado.')
    if clean(actual)!=clean(text):raise DocumentError('La comprobación de texto del flujo mixto detectó diferencias; no se aplicó el cambio.')
