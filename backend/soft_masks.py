"""Bounded vector Alpha/Luminosity masks; original streams are never rewritten."""
import math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations,tokens,numbers


def verify(doc,mask):
    n=f.mupdf
    def fail():raise DocumentError('La máscara no pertenece al subconjunto vectorial verificable Alpha/Luminosity.')
    def keys(obj):return {n.pdf_to_name(n.pdf_dict_get_key(obj,i)) for i in range(n.pdf_dict_len(obj))}
    if not n.pdf_is_dict(mask) or not keys(mask)<={'Type','S','G','BC','TR'} or n.pdf_to_name(n.pdf_dict_gets(mask,'S')) not in ['Alpha','Luminosity']:fail()
    type_=n.pdf_dict_gets(mask,'Type')
    if not n.pdf_is_null(type_) and (not n.pdf_is_name(type_) or n.pdf_to_name(type_)!='Mask'):fail()
    transfer=n.pdf_dict_gets(mask,'TR')
    if not (n.pdf_is_null(transfer) or n.pdf_is_name(transfer) and n.pdf_to_name(transfer)=='Identity'):fail()
    group=n.pdf_dict_gets(mask,'G');target=n.pdf_to_num(group)
    if not target or not n.pdf_is_stream(group):fail()
    color=n.pdf_to_name(n.pdf_dict_getp(group,'Group/CS'));mode=n.pdf_to_name(n.pdf_dict_gets(mask,'S'));backdrop=n.pdf_dict_gets(mask,'BC')
    if mode=='Luminosity' and color not in ['DeviceGray','DeviceRGB']:fail()
    if not n.pdf_is_null(backdrop):
        if color not in ['DeviceGray','DeviceRGB'] or not n.pdf_is_array(backdrop) or n.pdf_array_len(backdrop)!=(1 if color=='DeviceGray' else 3):fail()
        for i in range(n.pdf_array_len(backdrop)):
            v=n.pdf_array_get(backdrop,i)
            if not n.pdf_is_number(v) or not math.isfinite(n.pdf_to_real(v)) or not 0<=n.pdf_to_real(v)<=1:fail()
    budget={'bytes':0,'nodes':0,'ops':0}
    def walk(x,path=(),root=False):
        from .styled_text import stream
        from .text_compositing import group as compatible_group
        if x in path or len(path)>=8:fail()
        budget['nodes']+=1
        if budget['nodes']>100:fail()
        if doc.xref_get_key(x,'Subtype')!=('name','/Form') or not compatible_group(doc,x):fail()
        if root and doc.xref_get_key(x,'Group/S')!=('name','/Transparency'):fail()
        if any(doc.xref_get_key(x,k)[0]!='null' for k in ['OC','Ref','StructParents','StructParent']):fail()
        from .form_text import array,SAFE
        box=array(doc,x,'BBox',4);matrix=array(doc,x,'Matrix',6,[1,0,0,1,0,0])
        if not all(math.isfinite(v) and abs(v)<=10000 for v in box+matrix) or box[0]>=box[2] or box[1]>=box[3] or abs(matrix[0]*matrix[3]-matrix[1]*matrix[2])<1e-8:fail()
        data=stream(doc,x,2*1024*1024);budget['bytes']+=len(data)
        if budget['bytes']>8*1024*1024:fail()
        depth=0
        arities={'q':0,'Q':0,'cm':6,'m':2,'l':2,'c':6,'v':4,'y':4,'re':4,'h':0,'W':0,'W*':0,'f':0,'F':0,'f*':0,'S':0,'s':0,'B':0,'B*':0,'b':0,'b*':0,'n':0,'g':1,'G':1,'rg':3,'RG':3,'w':1,'J':1,'j':1,'M':1}
        for op,args,_ in operations(data):
            budget['ops']+=1
            if budget['ops']>10000:fail()
            if op=='gs':
                if len(args)!=1 or args[0].kind!='name' or not SAFE.fullmatch(args[0].value):fail()
                native=n.pdf_load_object(f._as_pdf_document(doc),x);state=n.pdf_dict_getp(native,'Resources/ExtGState/'+args[0].value)
                if not n.pdf_is_dict(state) or not keys(state)<={'Type','ca','CA','BM'}:fail()
                blend=n.pdf_dict_gets(state,'BM')
                if not n.pdf_is_null(blend) and (not n.pdf_is_name(blend) or n.pdf_to_name(blend) not in ['Normal','Compatible']):fail()
                for key in ['ca','CA']:
                    v=n.pdf_dict_gets(state,key)
                    if not n.pdf_is_null(v) and (not n.pdf_is_number(v) or not math.isfinite(n.pdf_to_real(v)) or not 0<=n.pdf_to_real(v)<=1):fail()
                continue
            if op=='Do':
                if len(args)!=1 or args[0].kind!='name' or not SAFE.fullmatch(args[0].value):fail()
                kind,value=doc.xref_get_key(x,'Resources/XObject/'+args[0].value)
                if kind!='xref':fail()
                walk(int(value.split()[0]),(*path,x));continue
            if op=='d':
                if len(args)!=2 or args[0].kind!='array' or args[1].kind!='number' or len(args[0].value)>16:fail()
                values=numbers(args[0].value,len(args[0].value));phase=args[1].value
                if any(not 0<=v<=1000 for v in values) or values and not any(v>0 for v in values) or not math.isfinite(phase) or not 0<=phase<=10000:fail()
                continue
            if op not in arities:fail()
            values=numbers(args,arities[op])
            if any(abs(v)>10000 for v in values):fail()
            if op in ['g','G','rg','RG'] and any(not 0<=v<=1 for v in values):fail()
            if op=='w' and not 0<=values[0]<=1000 or op in ['J','j'] and values[0] not in [0,1,2] or op=='M' and not 1<=values[0]<=100:fail()
            if op=='cm' and abs(values[0]*values[3]-values[1]*values[2])<1e-8:fail()
            if op=='q':depth+=1
            if op=='Q':depth-=1
            if not 0<=depth<=32:fail()
        if depth:fail()
    walk(target,root=True)
