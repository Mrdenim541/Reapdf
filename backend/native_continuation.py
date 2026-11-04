"""Empty-page regions and original-font output for native affine paragraphs."""
import pymupdf as f
from .engine import DocumentError,finite
from .affine_text import bounds
from .form_text import clone_dictionary
from .mixed_spacing import operand


def regions(doc,source,values,matrix):
    if values is None:return [],{}
    if not isinstance(values,list) or not 1<=len(values)<=7:raise DocumentError('Elige de 1 a 7 áreas de continuación en otras páginas.')
    if doc.get_ocgs():raise DocumentError('La continuación entre páginas con capas necesita comprobar su visibilidad.')
    result=[];rotations={};a,b,c,d=matrix[:4]
    for i,row in enumerate(values,1):
        if not isinstance(row,dict) or set(row)!={'page','box'} or type(row['page']) is not int or not 0<=row['page']<len(doc) or row['page']==source:raise DocumentError('Cada continuación necesita un área de otra página existente.')
        number=row['page'];page=doc[number]
        if number not in rotations:rotations[number]=page.rotation;page.set_rotation(0)
        box=row['box']
        if not isinstance(box,list) or len(box)!=4 or any(not finite(v) for v in box) or min(box[2:])<10:raise DocumentError('La continuación debe medir al menos 10 × 10 pt.')
        rect=f.Rect(box[0],box[1],box[0]+box[2],box[1]+box[3])
        if not page.rect.contains(rect):raise DocumentError('La continuación sale de su página.')
        if any(old['page']==number and (old['rect']&rect).get_area()>.01 for old in result):raise DocumentError('Las continuaciones no pueden solaparse.')
        blocked=[f.Rect(v[:4]) for v in page.get_text('blocks',flags=f.TEXTFLAGS_TEXT)]
        # ActualText may suppress extraction while glyphs remain visible.
        blocked += [f.Rect(v['bbox']) for v in page.get_texttrace()]
        blocked += [f.Rect(v['bbox']) for v in page.get_image_info()]+[f.Rect(v['from']) for v in page.get_links()]
        blocked += [v.rect for v in page.annots() or []]+[v.rect for v in page.widgets() or []]
        blocked += [f.Rect(v['rect'])+tuple(sign*max(.5,(v.get('width') or 0)/2) for sign in [-1,-1,1,1]) for v in page.get_drawings()]
        if any(v.type[0]==f.PDF_ANNOT_REDACT for v in page.annots() or []) or any((v&rect).get_area()>.1 for v in blocked):raise DocumentError(f'Continuación {i}: el área debe estar vacía, sin texto, dibujos, imágenes, campos, enlaces ni anotaciones.')
        inner=rect+(3,3,-3,-3);w,h=inner.width,inner.height
        scale=min(w/(abs(a)*w+abs(c)*h),h/(abs(b)*w+abs(d)*h));w*=scale;h*=scale
        frame=f.Matrix(a,b,c,d,0,0);corners=[list(f.Point(p)*frame) for p in [(0,0),(w,0),(w,-h),(0,-h)]];box=bounds(corners)
        frame[4]=inner.x0-box.x0;frame[5]=inner.y0-box.y0
        result.append({'page':number,'rect':rect,'width':w,'height':h,'frame':frame})
    return result,rotations


def append(doc,draws):
    fonts={};aliases={};parts={}
    for number,row,geometry,text in draws:
        page=doc[number];font=row['_font'];key=(number,font.xref)
        if number not in fonts:
            resource=clone_dictionary(doc,page.xref,'Resources');fonts[number]=clone_dictionary(doc,resource,'Font')
        if key not in aliases:
            alias='ReapdfContinue'+str(len(aliases)+1)
            while doc.xref_get_key(fonts[number],alias)[0]!='null':alias+='x'
            doc.xref_set_key(fonts[number],alias,f'{font.xref} 0 R');aliases[key]=alias
        matrix=f.Matrix(*geometry['matrix'])*~page.transformation_matrix
        encoded=operand(font,text,row.get('_replacement_kern',[])).decode('ascii');state=row['_spacing']['state'];color=[((row['color']>>v)&255)/255 for v in [16,8,0]]
        command=f"q BT {state['char']:.8f} Tc {state['word']:.8f} Tw {state['scale']:.8f} Tz 0 Ts 0 Tr /{aliases[key]} {row['size']:.8f} Tf {' '.join(str(v) for v in color)} rg {' '.join(f'{v:.8f}' for v in matrix)} Tm {encoded} ET Q"
        parts.setdefault(number,[]).append(command)
    for number,commands in parts.items():
        page=doc[number];page.wrap_contents();xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,'\n'.join(commands).encode());doc.xref_set_key(page.xref,'Contents','['+' '.join(f'{x} 0 R' for x in page.get_contents()+[xref])+']')
