"""Font substitution inside a verified native text group, retaining its owners."""
import copy,math,unicodedata
import pymupdf as f
from .engine import DocumentError,finite


def availability(doc,row):
    if not row.get('editable') or not row.get('_native'):return row.get('reason') or 'Este fragmento no tiene un grupo nativo verificable.'
    if row.get('original_only'):return 'Esta composición necesita conservar su fuente y tamaño originales.'
    boxes=[]
    if row.get('_semantic_identity') is not None:
        from .semantic_text import tree
        from .affine_text import rectangle,contains,polygon
        n=f.mupdf;index=tree(doc);identity=row['_semantic_identity'];allowed={'Color','O','BBox','Width','Height','Placement','WritingMode','TextAlign','SpaceBefore','SpaceAfter','StartIndent','EndIndent','TextIndent','BlockAlign','InlineAlign','BorderStyle','BorderColor','BorderThickness','Padding','ColumnCount','ColumnGap','ColumnWidths'}
        for key in index.records[identity]['chain']+[identity]:
            obj=index.records[key]['object']

            from .text_typography import declarations,validate,TYPO
            try:attrs=[a for _,_,_,a in declarations(doc,obj)]
            except DocumentError as exc:return str(exc)
            for attr in attrs:
                try:validate(attr)
                except DocumentError as exc:return str(exc)
                owner=n.pdf_to_name(n.pdf_dict_gets(attr,'O'))
                if n.pdf_dict_len(attr)>64:return 'Demasiados atributos para cambiar formato con seguridad.'
                keys={n.pdf_to_name(n.pdf_dict_get_key(attr,i)) for i in range(n.pdf_dict_len(attr))}
                from .css_typography import OWNERS
                if owner in OWNERS:continue # validate() already checked every CSS property.
                if owner in ['Table','List']:
                    permitted={'O','RowSpan','ColSpan','Headers','Scope','Summary'} if owner=='Table' else {'O','ListNumbering'}
                    if keys-permitted:return 'Los atributos de tabla o lista no son compatibles con el cambio de formato.'
                    continue
                if owner!='Layout' or keys-allowed-TYPO:return 'Los atributos de tipografía necesitan una actualización coordinada antes de cambiar la fuente.'
                bbox=n.pdf_dict_gets(attr,'BBox')
                if n.pdf_is_null(bbox) and keys&{'Width','Height'}:return 'Los atributos de dimensiones necesitan una caja verificable.'
                if not n.pdf_is_null(bbox):
                    if not n.pdf_is_array(bbox) or n.pdf_array_len(bbox)!=4:return 'Los atributos de caja no son verificables.'
                    values=[n.pdf_array_get(bbox,i) for i in range(4)]
                    if any(not n.pdf_is_number(v) for v in values):return 'Los atributos de caja no son numéricos.'
                    values=[n.pdf_to_real(v) for v in values]
                    if not all(math.isfinite(v) for v in values) or values[2]<=values[0] or values[3]<=values[1]:return 'Los atributos de caja están fuera de límites.'
                    cell=rectangle(f.Rect(values)*doc[row.get('_format_page',0)].transformation_matrix)
                    if not contains(cell,polygon(row['_geometry'])):return 'Los atributos de caja no coinciden con el texto seleccionado.'
                    boxes.append(cell)
    row['_format_tag_boxes']=boxes
    return ''



def prepare(doc,number,row,text,options,*,coordinated_geometry=False):
    from .paragraphs import paragraph_font,FAMILIES
    from .styled_text import OriginalFont,clone_resources
    from .text_spacing import layout,retained_kern
    from .pdf_content import operations
    if not isinstance(options,dict) or set(options)!={'family','style','size'}:raise DocumentError('Indica familia, estilo y tamaño de la fuente.')
    family,style,size=(options[k] for k in ['family','style','size'])
    if not finite(size) or isinstance(size,bool) or not 6<=size<=144:raise DocumentError('El tamaño debe estar entre 6 y 144 pt.')
    original=family=='original'
    if original and style!='original':raise DocumentError('Con la fuente original utiliza su estilo original.')
    font=None if original else paragraph_font(family,style)
    row['_format_page']=number
    reason=availability(doc,row)
    if reason:raise DocumentError(reason)
    if any(unicodedata.bidirectional(c) in {'R','AL','AN'} or unicodedata.combining(c) or unicodedata.category(c) in {'Cs','Cf'} or font is not None and not font.has_glyph(ord(c),fallback=0) for c in text):raise DocumentError('La fuente incluida o la composición de uno de los caracteres no es compatible con esta línea.')
    page=doc[number];cache=getattr(doc,'_reapdf_format_fonts',{});key=(number,family,style)
    if not original and key not in cache:
        used={item[4] for item in page.get_fonts(full=True)};alias='ReapdfFormat'
        while alias in used:alias+='x'
        if len(page.get_fonts(full=True))>=20:raise DocumentError('No hay presupuesto para añadir otra fuente en esta página.')
        clone_resources(doc,page);xref=page.insert_font(fontname=alias,fontbuffer=font.buffer)
        italic='Italic' if family=='serif' else 'Oblique';suffix={'regular':'','bold':'-Bold','italic':'-'+italic,'bold-italic':'-Bold'+italic}[style]
        name=FAMILIES[family]+suffix;face=OriginalFont(doc,(xref,'ttf','Type0',name,alias,'',0))
        if name not in face.aliases:raise DocumentError('El nombre de la fuente incluida no coincide con su programa.')
        cache[key]=(alias,xref,face,name);doc._reapdf_format_fonts=cache
    alias,xref,face,name=(row.get('_font_resource',row['_font'].resource),row['_font'].xref,row['_font'],row['font']) if original else cache[key]
    g=copy.deepcopy(row['_geometry']);g.update(size=size,ascent=g['ascent']*size/row['size'] if original else font.ascender*size,descent=g['descent']*size/row['size'] if original else font.descender*size)
    kern=retained_kern(row,text);state=dict(row['_spacing']['state'])
    # CID fonts do not apply Tw to their two-byte space. Preserve that extra gap
    # explicitly in TJ, without changing the inherited state for later groups.
    for i,c in enumerate(text[:-1]):
        if c==' ' and state['word'] and face.encode(' ',size)[0]!=b' ':
            try:old_space=row['_font'].encode(' ',row['size'])[0]
            except DocumentError:old_space=b''
            if old_space==b' ':kern[i]-=state['word']/size*1000
    width,origins=layout(face,text,size,state,kern)
    if any(b<=a for a,b in zip(origins,origins[1:])):raise DocumentError('El nuevo espaciado superpondría los caracteres.')
    chunks=[]
    for i,c in enumerate(text):
        chunks.append(b'<'+face.encode(c,size)[0].hex().encode()+b'>')
        if i<len(kern) and kern[i]:chunks.append(f'{kern[i]:.8f}'.encode())
    owner=row['_native_path'][-1]['target'] if row['_native_path'] else page.xref
    data=doc.xref_stream(owner) if row['_native_path'] else page.read_contents();start,end,kind=row['_native']
    stops=[token.end for op,args,token in operations(data) if op in ['Tj','TJ'] and args and args[0].start<=end<=token.end and token.end-end<=4]
    if len(stops)!=1:raise DocumentError('El operador original no se identifica de forma única.')
    def pdfname(value):return '/'+''.join(chr(c) if 33<=c<=126 and chr(c) not in '#/%()<>[]{}' else f'#{c:02X}' for c in value.encode('latin-1'))
    tm=' '.join(f'{v:.8f}' for v in row['_line_matrix'])
    command=(f'{pdfname(alias)} {size/g["factor"]:.8f} Tf ['.encode()+b' '.join(chunks)+f'] TJ {tm} Tm {pdfname(row.get("_font_resource",row["_font"].resource))} {row["size"]/g["factor"]:.8f} Tf'.encode())
    g['width']=width
    from .affine_text import contains,polygon
    if not coordinated_geometry and any(not contains(cell,polygon(g)) for cell in row.get('_format_tag_boxes',[])):raise DocumentError('El formato nuevo sale de la caja declarada en sus etiquetas; reduce tamaño o contenido.')
    return {**row,'font':name,'size':size,'display_size':size*math.sqrt(state['scale']/100),'_font':face,'_geometry':g,'_native':[start,stops[0],'operator-array'],'_native_fonts':{} if original else {alias:xref},'_format_origins':[[row['origin'][j]+g['direction'][j]*v for j in [0,1]] for v in origins],'_format_options':dict(options),'_formatted':True,'_source_format_row':row,'_spacing':{'state':state,'kern':kern}},command,width


def protect_edges(page,source,target):
    """Conservative line/curve/link collision checks for footprint expansion."""
    from .affine_text import contains,rectangle,overlap
    if contains(source,target):return
    obstacles=[rectangle(link['from']) for link in page.get_links()]
    for path in page.get_drawings():
        if path.get('fill') is not None:
            cell=rectangle(f.Rect(path['rect']))
            if not (contains(cell,source) and contains(cell,target)):obstacles.append(cell)
        if path.get('color') is None:continue
        padding=max(.25,(path.get('width') or 0)/2)
        for item in path['items']:
            if item[0]=='l':pairs=[item[1:]]
            elif item[0]=='re':
                r=item[1];pairs=[(r.tl,r.tr),(r.tr,r.br),(r.br,r.bl),(r.bl,r.tl)]
            elif item[0]=='qu':
                q=item[1];pairs=[(q.ul,q.ur),(q.ur,q.lr),(q.lr,q.ll),(q.ll,q.ul)]
            else:pairs=[item[1:]]
            for points in pairs:
                xs=[p.x for p in points if hasattr(p,'x')];ys=[p.y for p in points if hasattr(p,'y')]
                if xs:obstacles.append(rectangle(f.Rect(min(xs)-padding,min(ys)-padding,max(xs)+padding,max(ys)+padding)))
            if len(obstacles)>10000:raise DocumentError('Demasiados bordes para ampliar el formato del texto con seguridad.')
    if any(overlap(target,cell)>.1 for cell in obstacles):raise DocumentError('El nuevo formato cruza un borde, trazado o enlace. Reduce el tamaño o el contenido.')
