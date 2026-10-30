"""Bounded lexical locations in direct PDF content, without rewriting operators.

Inline images are deliberately refused: their arbitrary bytes require a separate
parser. Arrays/dictionaries/strings are single operands, so operator-like bytes
inside them never become instructions.
"""
from dataclasses import dataclass
import re
import pymupdf as f
from .engine import DocumentError

SPACE=b'\x00\t\n\f\r '
DELIM=b'()<>[]{}/%'
NUMBER=re.compile(rb'[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z')

@dataclass
class Token:
    kind:str
    value:object
    start:int
    end:int


def tokens(data):
    if not isinstance(data,bytes) or len(data)>16*1024*1024:raise DocumentError('El contenido directo supera 16 MB.')
    count=0
    def skip(i):
        while i<len(data):
            if data[i] in SPACE:i+=1
            elif data[i]==37:
                while i<len(data) and data[i] not in b'\r\n':i+=1
            else:break
        return i
    def read(i,depth=0):
        nonlocal count
        count+=1
        if count>500000 or depth>20:raise DocumentError('Contenido PDF demasiado complejo para edición directa.')
        i=skip(i);start=i
        if i>=len(data):raise DocumentError('Operando PDF incompleto.')
        c=data[i]
        if c==40:
            out=bytearray();i+=1;level=1
            while i<len(data):
                c=data[i];i+=1
                if c==92:
                    if i>=len(data):break
                    c=data[i];i+=1
                    if c in b'\r\n':
                        if c==13 and i<len(data) and data[i]==10:i+=1
                    elif 48<=c<=55:
                        digits=bytes([c])
                        for _ in range(2):
                            if i<len(data) and 48<=data[i]<=55:digits+=data[i:i+1];i+=1
                            else:break
                        out.append(int(digits,8)&255)
                    else:out.extend({110:b'\n',114:b'\r',116:b'\t',98:b'\b',102:b'\f'}.get(c,bytes([c])))
                elif c==40:level+=1;out.append(c)
                elif c==41:
                    level-=1
                    if not level:return Token('string',bytes(out),start,i),i
                    out.append(c)
                elif c==13:
                    if i<len(data) and data[i]==10:i+=1
                    out.append(10)
                else:out.append(c)
            raise DocumentError('Cadena PDF sin terminar.')
        if c==60 and data[i:i+2]!=b'<<':
            end=data.find(b'>',i+1)
            if end<0:raise DocumentError('Cadena hexadecimal PDF incompleta.')
            raw=re.sub(rb'\s',b'',data[i+1:end])
            try:value=bytes.fromhex((raw+b'0'*(len(raw)%2)).decode('ascii'))
            except ValueError as exc:raise DocumentError('Cadena hexadecimal no válida.') from exc
            return Token('string',value,start,end+1),end+1
        if c==91 or data[i:i+2]==b'<<':
            dictionary=c==60;i+=2 if dictionary else 1;values=[];ending=b'>>' if dictionary else b']'
            while True:
                i=skip(i)
                if data[i:i+len(ending)]==ending:
                    i+=len(ending);return Token('dict' if dictionary else 'array',values,start,i),i
                token,i=read(i,depth+1);values.append(token)
        if c==47:
            i+=1
            while i<len(data) and data[i] not in SPACE+DELIM:i+=1
            raw=data[start+1:i]
            try:raw=re.sub(rb'#([0-9a-fA-F]{2})',lambda m:bytes([int(m[1],16)]),raw).decode('latin1')
            except ValueError as exc:raise DocumentError('Nombre de recurso no válido.') from exc
            return Token('name',raw,start,i),i
        while i<len(data) and data[i] not in SPACE+DELIM:i+=1
        if i==start:raise DocumentError('Delimitador PDF inesperado.')
        raw=data[start:i]
        return Token('number' if NUMBER.fullmatch(raw) else 'word',float(raw) if NUMBER.fullmatch(raw) else raw.decode('latin1'),start,i),i
    i=0
    while True:
        i=skip(i)
        if i>=len(data):return
        token,i=read(i);yield token


def operations(data):
    args=[]
    for token in tokens(data):
        if token.kind=='word' and token.value not in ['true','false','null']:
            if token.value in ['BI','ID','EI']:raise DocumentError('Las imágenes inline requieren otra edición; no se reinterpretan sus bytes.')
            yield token.value,args,token
            args=[]
        else:args.append(token)
    if args:raise DocumentError('Contenido PDF con operandos sin operador.')


def names(data):
    def visit(token):
        if token.kind=='name':yield token.value
        elif token.kind in ['array','dict']:
            for child in token.value:yield from visit(child)
    for token in tokens(data):yield from visit(token)


def numbers(args,count):
    if len(args)!=count or any(t.kind!='number' for t in args):raise DocumentError('Operandos numéricos PDF no compatibles.')
    values=[t.value for t in args]
    if any(abs(v)>1e9 for v in values):raise DocumentError('Transformación PDF fuera de límites.')
    return values


def placements(data):
    """Locate direct invocations and bounded single-show text, including spacing."""
    matrix=f.Matrix(1,1);stack=[];images=[];texts=[];text=None;font=None;size=0
    state={'char':0.,'word':0.,'scale':100.,'render':0.,'rise':0.}
    parameter={'Tc':'char','Tw':'word','Tz':'scale','Tr':'render','Ts':'rise'}
    for op,args,token in operations(data):
        if text is not None and op not in ['BT','ET','Tf','Td','Tm','Tj','TJ','Tc','Tw','Tz','Tr','Ts'] and not (not text['shows'] and op in ['q','Q','rg','RG','g','G','k','K','cs','CS','sc','SC','scn','SCN','gs','TL']):
            text['simple']=False
        if op=='q':
            stack.append((f.Matrix(matrix),dict(state),font,size))
            if len(stack)>100:raise DocumentError('Demasiados estados gráficos anidados.')
        elif op=='Q':
            if not stack:raise DocumentError('Estado gráfico PDF desequilibrado.')
            matrix,state,font,size=stack.pop()
            if text is not None:
                if text['shows']:text['simple']=False
                else:text['font']=font;text['size']=size
        elif op=='cm':matrix=f.Matrix(*numbers(args,6))*matrix
        elif op in parameter:
            value=numbers(args,1)[0];state[parameter[op]]=value
            if text is not None and text['shows']:text['simple']=False
        elif op=='BT':
            if text is not None:raise DocumentError('Objetos de texto anidados.')
            text={'origin':f.Point(0,0),'matrix':f.Matrix(matrix),'font':font,'size':size,'shows':[],'parts':[],'show_ends':[],'simple':True}
        elif op=='ET' and text is not None:
            if text['simple'] and text['shows'] and text['font']:
                if len(text['shows'])>1:
                    shows=text['shows'];text['shows']=[Token('operator-array',b''.join(s.value for s in shows),shows[0].start,text['show_ends'][-1])]
                texts.append(text)
            text=None
        elif op=='Do':
            if len(args)!=1 or args[0].kind!='name':raise DocumentError('Invocación de objeto no válida.')
            images.append({'resource':args[0].value,'matrix':f.Matrix(matrix),'start':args[0].start,'end':token.end})
        elif text is not None:
            if op=='Tf' and len(args)==2 and args[0].kind=='name' and args[1].kind=='number':
                if text['shows']:text['simple']=False
                font=args[0].value;size=args[1].value
                text['font']=font;text['size']=size
            elif op=='Td' and not text['shows']:
                x,y=numbers(args,2);text['origin']+=f.Point(x,y)
            elif op=='Tm' and not text['shows']:
                a,b,c,d,e,g=numbers(args,6)
                linear=f.Matrix(a,b,c,d,0,0)
                if abs(a*d-b*c)<1e-8:text['simple']=False
                text['origin']=f.Point(e,g)*~linear;text['matrix']=linear*matrix
            elif op in ['Tj','TJ']:
                show=None;parts=[]
                if op=='Tj' and len(args)==1 and args[0].kind=='string':show=args[0];parts=[show]
                elif op=='TJ' and len(args)==1 and args[0].kind=='array':
                    parts=args[0].value
                    if all(t.kind in ['string','number'] for t in parts):show=Token('array-string',b''.join(t.value for t in parts if t.kind=='string'),args[0].start,args[0].end)
                if show is None:text['simple']=False
                else:
                    text['shows'].append(show);text['parts'].extend(parts);text['show_ends'].append(token.end);text['spacing']=dict(state)
                    if not 10<=state['scale']<=400 or state['render']!=0 or state['rise']!=0 or max(abs(state['char']),abs(state['word']))>1000:text['simple']=False
            elif op in ["'",'"','TD','T*','Td','Tm']:text['simple']=False
    if stack or text is not None:raise DocumentError('Contenido PDF sin cierre gráfico o de texto.')
    return {'images':images,'texts':texts}


def patch(data,edits):
    """Non-overlapping exact byte replacements, preserving every other byte."""
    result=data;end=len(data)
    for start,stop,value in sorted(edits,reverse=True):
        if not 0<=start<stop<=end:raise DocumentError('Cambios directos superpuestos o fuera de rango.')
        result=result[:start]+value+result[stop:];end=start
    return result


def set_content(doc,page,data):
    xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,data);page.set_contents(xref)
