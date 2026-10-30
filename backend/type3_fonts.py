"""Verified, uncoloured vector Type3 glyphs; resources and programs stay intact."""
import math
import re
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
    if max(abs(a-b) for a,b in zip(matrix,[.001,0,0,.001,0,0]))>1e-9:fail('la matriz del glifo requiere otro tratamiento.')
    bbox=array('FontBBox',4)
    if not (-10000<=bbox[0]<bbox[2]<=10000 and -10000<=bbox[1]<bbox[3]<=10000):fail('caja de fuente no válida.')
    for key in ['Resources','CharProcs','Encoding']:
        value=n.pdf_dict_gets(obj,key)
        if not n.pdf_is_dict(value):fail('falta el diccionario '+key+'.')
    resources=n.pdf_dict_gets(obj,'Resources')
    if n.pdf_dict_len(resources):fail('los recursos internos de los glifos requieren otro tratamiento.')
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
            cache[xref]=validate(data,bbox)
        advance,paint=cache[xref]
        if abs(advance-width)>.01:fail('la anchura del glifo contradice Widths.')
        if paint or char in [' ','\u00a0']:font.options[char].append((code,width/1000,code))


def validate(data,fontbox):
    def fail():raise DocumentError('Type3: el glifo necesita vectores simples sin color, imágenes, texto ni estados externos.')
    ops=list(operations(data))
    if not ops or len(ops)>2000:fail()
    op,args,_=ops[0]
    if op!='d1' or len(args)!=6 or any(t.kind!='number' for t in args):fail()
    width,vertical,*box=[t.value for t in args]
    if not all(math.isfinite(v) and abs(v)<=10000 for v in [width,vertical,*box]) or vertical!=0 or width<=0:fail()
    if box[0]>box[2] or box[1]>box[3] or any(box[i]<fontbox[i]-.01 for i in [0,1]) or any(box[i]>fontbox[i]+.01 for i in [2,3]):fail()
    path=False;paint=False
    arities={'m':2,'l':2,'c':6,'v':4,'y':4,'re':4,'h':0,'f':0,'f*':0,'n':0}
    for op,args,_ in ops[1:]:
        if op not in arities or len(args)!=arities[op] or any(t.kind!='number' for t in args):fail()
        values=[t.value for t in args]
        if any(not math.isfinite(v) or abs(v)>10000 for v in values):fail()
        if op=='re':
            x,y,w,h=values;points=[(x,y),(x+w,y+h)]
        else:points=list(zip(values[::2],values[1::2]))
        if any(not box[0]-.01<=x<=box[2]+.01 or not box[1]-.01<=y<=box[3]+.01 for x,y in points):fail()
        if op in ['m','re']:path=True
        elif op in ['l','c','v','y','h'] and not path:fail()
        elif op in ['f','f*','n']:
            if not path:fail()
            paint=paint or op!='n';path=False
    if path:fail()
    return width,paint
