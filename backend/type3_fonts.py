"""Verified uncoloured or explicitly coloured vector Type3 glyphs; resources and programs stay intact."""
import math
import re
import zlib
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations


def load(font,doc):
    from .styled_text import native_font,stream,unicode_cmap
    n=f.mupdf;obj=native_font(doc,font.xref)
    def fail(message):raise DocumentError('Type3: '+message)
    def array(key,count=None):
        value=n.pdf_dict_gets(obj,key);length=n.pdf_array_len(value)
        if not n.pdf_is_array(value) or count is not None and length!=count:fail('tabla '+key+' no válida.')
        values=[]
        for i in range(length):
            item=n.pdf_array_get(value,i)
            if not n.pdf_is_number(item):fail('tabla '+key+' no numérica.')
            v=n.pdf_to_real(item)
            if not math.isfinite(v):fail('tabla '+key+' fuera de límites.')
            values.append(v)
        return values
    matrix=array('FontMatrix',6)
    if not (1e-6<=matrix[0]<=1 and 1e-6<=matrix[3]<=1 and matrix[1]==matrix[2]==0 and abs(matrix[4])<=10 and abs(matrix[5])<=10):fail('la matriz del glifo requiere otro tratamiento.')
    bbox=array('FontBBox',4)
    if not (-10000<=bbox[0]<bbox[2]<=10000 and -10000<=bbox[1]<bbox[3]<=10000):fail('caja de fuente no válida.')
    for key in ['Resources','CharProcs','Encoding']:
        value=n.pdf_dict_gets(obj,key)
        if not n.pdf_is_dict(value):fail('falta el diccionario '+key+'.')
    resources=n.pdf_dict_gets(obj,'Resources')
    images=image_resources(doc,resources,fail)
    first=n.pdf_dict_gets(obj,'FirstChar');last=n.pdf_dict_gets(obj,'LastChar')
    if not n.pdf_is_int(first) or not n.pdf_is_int(last):fail('rango de caracteres no válido.')
    first,last=n.pdf_to_int(first),n.pdf_to_int(last)
    if not 0<=first<=last<=255:fail('rango de caracteres fuera de límites.')
    widths=array('Widths',last-first+1)
    encoding=n.pdf_dict_gets(obj,'Encoding')
    if not n.pdf_is_null(n.pdf_dict_gets(encoding,'BaseEncoding')):fail('la codificación debe estar definida completamente por Differences.')
    differences=n.pdf_dict_gets(encoding,'Differences');mapping={};code=None
    if not n.pdf_is_array(differences) or n.pdf_array_len(differences)>512:fail('Differences no válido.')
    for i in range(n.pdf_array_len(differences)):
        item=n.pdf_array_get(differences,i)
        if n.pdf_is_int(item):
            code=n.pdf_to_int(item)
            if not 0<=code<=255:fail('código de Differences fuera de rango.')
        elif n.pdf_is_name(item) and code is not None and 0<=code<=255:
            name=n.pdf_to_name(item)
            if code in mapping or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',name):fail('Differences repetido o ambiguo.')
            mapping[code]=name;code+=1
        else:fail('Differences incompleto.')
    uni=n.pdf_dict_gets(obj,'ToUnicode')
    if not n.pdf_is_stream(uni):fail('se necesita un mapa ToUnicode explícito.')
    unicode=unicode_cmap(stream(doc,n.pdf_to_num(uni),2*1024*1024),1)
    procs=n.pdf_dict_gets(obj,'CharProcs')
    if not 1<=n.pdf_dict_len(procs)<=256:fail('número de glifos fuera de límites.')
    cache={};font.code_bytes=1;font.trace_cid=True;font.restricted=True
    for code,char in unicode.items():
        if not first<=code<=last or code not in mapping:continue
        name=mapping[code];proc=n.pdf_dict_gets(procs,name);xref=n.pdf_to_num(proc);width=widths[code-first]
        if not n.pdf_is_stream(proc) or not xref or not 0<width<=10000:fail('glifo o anchura no válido.')
        if xref not in cache:
            data=stream(doc,xref,64*1024);font.program_bytes+=len(data)
            if font.program_bytes>2*1024*1024:fail('los glifos superan 2 MB.')
            cache[xref]=validate(data,bbox,images)
        advance,paint=cache[xref]
        if abs(advance-width)>.01:fail('la anchura del glifo contradice Widths.')
        if paint or char in [' ','\u00a0']:font.options[char].append((code,width*matrix[0],code))


def image_resources(doc,resources,fail):
    n=f.mupdf
    if not n.pdf_dict_len(resources):return {}
    if n.pdf_dict_len(resources)!=1 or not n.pdf_is_dict(n.pdf_dict_gets(resources,'XObject')):fail('solo se admiten recursos de imagen verificados.')
    objects=n.pdf_dict_gets(resources,'XObject');result={};total=0;decoded_total=0
    if not 1<=n.pdf_dict_len(objects)<=16:fail('número de imágenes fuera de límites.')
    for i in range(n.pdf_dict_len(objects)):
        name=n.pdf_to_name(n.pdf_dict_get_key(objects,i));image=n.pdf_dict_get_val(objects,i);xref=n.pdf_to_num(image)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',name) or not xref or not n.pdf_is_stream(image) or n.pdf_to_name(n.pdf_dict_gets(image,'Subtype'))!='Image':fail('el recurso no es una imagen indirecta compatible.')
        for key in ['SMask','Mask','Alternates','OPI','F','FFilter','FDecodeParms','DecodeParms']:
            if not n.pdf_is_null(n.pdf_dict_gets(image,key)):fail('la imagen utiliza máscaras, recursos externos o parámetros no verificados.')
        width=n.pdf_dict_gets(image,'Width');height=n.pdf_dict_gets(image,'Height')
        if not n.pdf_is_int(width) or not n.pdf_is_int(height):fail('dimensiones de imagen no verificables.')
        width,height=n.pdf_to_int(width),n.pdf_to_int(height)
        if not 0<width<=8192 or not 0<height<=8192 or width*height>16_000_000:fail('imagen demasiado grande.')
        mask=n.pdf_dict_gets(image,'ImageMask')
        if not n.pdf_is_null(mask) and not n.pdf_is_bool(mask):fail('ImageMask no válido.')
        mask=bool(n.pdf_to_bool(mask)) if not n.pdf_is_null(mask) else False
        bits=n.pdf_dict_gets(image,'BitsPerComponent');bits=n.pdf_to_int(bits) if n.pdf_is_int(bits) else 1 if mask and n.pdf_is_null(bits) else 0
        if bits not in ([1] if mask else [1,2,4,8,16]):fail('profundidad de imagen no verificada.')
        color=n.pdf_dict_gets(image,'ColorSpace')
        if mask and not n.pdf_is_null(color) or not mask and n.pdf_to_name(color) not in ['DeviceGray','DeviceRGB','DeviceCMYK']:fail('espacio de color de imagen no verificado.')
        filt=n.pdf_dict_gets(image,'Filter')
        if not n.pdf_is_null(filt) and (not n.pdf_is_name(filt) or n.pdf_to_name(filt) not in ['FlateDecode']):fail('filtro de imagen no verificado.')
        raw=doc.xref_stream_raw(xref);total+=len(raw)
        if not raw or total>8*1024*1024:fail('las imágenes superan 8 MB.')
        channels=1 if mask or n.pdf_to_name(color)=='DeviceGray' else 3 if n.pdf_to_name(color)=='DeviceRGB' else 4
        expected=((width*bits*channels+7)//8)*height;decoded_total+=expected
        if decoded_total>16*1024*1024:fail('las imágenes decodificadas superan 16 MB.')
        decoded=raw
        if not n.pdf_is_null(filt):
            try:
                decoder=zlib.decompressobj();decoded=decoder.decompress(raw,expected+1)
                if decoder.unconsumed_tail or decoder.unused_data or not decoder.eof:raise ValueError()
            except (zlib.error,ValueError):fail('los datos de imagen no coinciden con su compresión o dimensiones.')
        if len(decoded)!=expected:fail('los datos de imagen no coinciden con sus dimensiones.')
        decode=n.pdf_dict_gets(image,'Decode')
        if not n.pdf_is_null(decode):
            count=2 if mask or n.pdf_to_name(color)=='DeviceGray' else 6 if n.pdf_to_name(color)=='DeviceRGB' else 8
            if not n.pdf_is_array(decode) or n.pdf_array_len(decode)!=count:fail('Decode de imagen no verificado.')
            for j in range(count):
                value=n.pdf_array_get(decode,j)
                if not n.pdf_is_number(value) or n.pdf_to_real(value) not in [0,1]:fail('Decode de imagen no verificado.')
        result[name]=mask
    return result


def validate(data,fontbox,images=None):
    def fail():raise DocumentError('Type3: el glifo usa un programa vectorial, color o estado fuera del subconjunto verificado.')
    ops=list(operations(data))
    if not ops or len(ops)>2000:fail()
    op,args,_=ops[0]
    colored=op=='d0'
    if op not in ['d0','d1'] or len(args)!=(2 if colored else 6) or any(t.kind!='number' for t in args):fail()
    width,vertical,*box=[t.value for t in args]
    if colored:box=list(fontbox)
    if not all(math.isfinite(v) and abs(v)<=10000 for v in [width,vertical,*box]) or vertical!=0 or width<=0:fail()
    if box[0]>box[2] or box[1]>box[3] or any(box[i]<fontbox[i]-.01 for i in [0,1]) or any(box[i]>fontbox[i]+.01 for i in [2,3]):fail()
    path=False;paint=False;stack=[];points=[];pending_clip=False
    state={'matrix':f.Matrix(1,1),'fill':False,'stroke':False,'width':None,'cap':None,'join':None,'miter':None}
    arities={'m':2,'l':2,'c':6,'v':4,'y':4,'re':4,'h':0,'f':0,'f*':0,'n':0,'S':0,'s':0,'B':0,'B*':0,'b':0,'b*':0}
    for op,args,_ in ops[1:]:
        if op=='Do':
            if path or pending_clip or len(args)!=1 or args[0].kind!='name' or args[0].value not in (images or {}):fail()
            mask=images[args[0].value]
            if not colored and not mask or colored and mask and not state['fill']:fail()
            corners=[f.Point(p)*state['matrix'] for p in [(0,0),(1,0),(1,1),(0,1)]]
            if any(not box[0]-.01<=p.x<=box[2]+.01 or not box[1]-.01<=p.y<=box[3]+.01 for p in corners):fail()
            paint=True;continue
        if op=='d':
            if len(args)!=2 or args[0].kind!='array' or args[1].kind!='number' or len(args[0].value)>16:fail()
            dash=args[0].value;phase=args[1].value
            if any(t.kind!='number' or not math.isfinite(t.value) or not 0<=t.value<=1000 for t in dash) or not math.isfinite(phase) or not 0<=phase<=10000 or dash and not any(t.value>0 for t in dash):fail()
            continue
        if op in ['W','W*']:
            if args or not path or pending_clip:fail()
            pending_clip=True;continue
        if pending_clip and op not in ['n','f','f*','S','s','B','B*','b','b*']:fail()
        values=[t.value for t in args if t.kind=='number']
        if len(values)!=len(args) or any(not math.isfinite(v) or abs(v)>10000 for v in values):fail()
        if op in ['q','Q']:
            if args or path:fail()
            if op=='q':
                if len(stack)>=16:fail()
                stack.append(dict(state))
            else:
                if not stack:fail()
                state=stack.pop()
            continue
        if op=='cm':
            if path or len(values)!=6:fail()
            matrix=f.Matrix(*values)*state['matrix'];det=matrix.a*matrix.d-matrix.b*matrix.c
            if not 1e-8<=abs(det)<=1e8 or max(abs(v) for v in matrix)>10000:fail()
            state['matrix']=matrix;continue
        if op in ['w','J','j','M']:
            if len(values)!=1:fail()
            value=values[0]
            if op=='w':
                if not 0<value<=1000:fail()
                state['width']=value
            elif op in ['J','j']:
                if value not in [0,1,2]:fail()
                state['cap' if op=='J' else 'join']=value
            else:
                if not 1<=value<=100:fail()
                state['miter']=value
            continue
        if op in ['g','rg','k','G','RG','K']:
            if not colored or len(values)!={'g':1,'rg':3,'k':4,'G':1,'RG':3,'K':4}[op] or any(not 0<=v<=1 for v in values):fail()
            state['stroke' if op[0].isupper() else 'fill']=True;continue
        if op not in arities or len(values)!=arities[op]:fail()
        if op=='re':
            x,y,w,h=values;current=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
        else:current=list(zip(values[::2],values[1::2]))
        transformed=[f.Point(p)*state['matrix'] for p in current]
        if any(not box[0]-.01<=p.x<=box[2]+.01 or not box[1]-.01<=p.y<=box[3]+.01 for p in transformed):fail()
        points.extend(transformed)
        if op in ['m','re']:path=True
        elif op in ['l','c','v','y','h'] and not path:fail()
        elif op in ['f','f*','n','S','s','B','B*','b','b*']:
            if not path:fail()
            stroke=op in ['S','s','B','B*','b','b*'];fill=op in ['f','f*','B','B*','b','b*']
            if colored and (stroke and not state['stroke'] or fill and not state['fill']):fail()
            if stroke:
                if any(state[k] is None for k in ['width','cap','join']) or state['join']==0 and state['miter'] is None:fail()
                # Frobenius norm bounds any transformed pen radius. Include
                # miter extension explicitly; no guessed inherited pen state.
                matrix=state['matrix'];radius=state['width']/2*math.sqrt(sum(v*v for v in [matrix.a,matrix.b,matrix.c,matrix.d]))
                if state['join']==0:radius*=state['miter']
                if state['cap']==2:radius*=math.sqrt(2)
                if not points or any(p.x-radius<box[0]-.01 or p.x+radius>box[2]+.01 or p.y-radius<box[1]-.01 or p.y+radius>box[3]+.01 for p in points):fail()
            paint=paint or op!='n';path=False;points=[];pending_clip=False
    if path or stack or pending_clip:fail()
    return width,paint
