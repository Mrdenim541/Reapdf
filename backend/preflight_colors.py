"""Declared color spaces and applied overprint states, including bounded Forms.

This diagnoses declarations; it does not evaluate tint functions or certify PDF/X.
"""
import pymupdf as f
from .pdf_content import operations
from .styled_text import stream
from .engine import DocumentError


def inspect(doc,page):
    n=f.mupdf;pdf=f._as_pdf_document(doc);colors=set();spots=set();overprint=[];reasons=[];budget={'bytes':0,'nodes':0};visited=set()
    def resources(owner,fallback=None):
        seen=set()
        while owner and owner not in seen and len(seen)<32:
            seen.add(owner);obj=n.pdf_load_object(pdf,owner);res=n.pdf_dict_gets(obj,'Resources')
            if n.pdf_is_dict(res):return res
            owner=n.pdf_to_num(n.pdf_dict_gets(obj,'Parent'))
        return fallback if fallback is not None else n.pdf_new_dict(pdf,0)
    def space(value,res,depth=0):
        if depth>16:raise DocumentError("Los espacios de color anidados superan el límite.")
        if value in ['DeviceRGB','DeviceCMYK','DeviceGray']:colors.add({'DeviceRGB':'RGB','DeviceCMYK':'CMYK','DeviceGray':'Gray'}[value]);return
        obj=n.pdf_dict_gets(n.pdf_dict_gets(res,'ColorSpace'),value)
        if n.pdf_is_name(obj):return space(n.pdf_to_name(obj),None) if n.pdf_to_name(obj) in ['DeviceRGB','DeviceCMYK','DeviceGray'] else colors.add('Otro')
        if not n.pdf_is_array(obj) or n.pdf_array_len(obj)<2:colors.add('Otro');return
        kind=n.pdf_to_name(n.pdf_array_get(obj,0));colors.add(kind or 'Otro')
        if kind=='ICCBased':
            count=n.pdf_dict_gets(n.pdf_array_get(obj,1),'N')
            if n.pdf_is_int(count) and n.pdf_to_int(count) in [1,3,4]:colors.add('ICCBased'+str(n.pdf_to_int(count)))
        if kind in ['Indexed','Separation','DeviceN']:
            at=1 if kind=='Indexed' else 2
            alternate=n.pdf_array_get(obj,at)
            if n.pdf_is_name(alternate):space(n.pdf_to_name(alternate),res,depth+1)
            elif n.pdf_is_array(alternate) and n.pdf_array_len(alternate)>0:
                base=n.pdf_to_name(n.pdf_array_get(alternate,0));colors.add(base or 'Otro')
                if base=='ICCBased':
                    count=n.pdf_dict_gets(n.pdf_array_get(alternate,1),'N')
                    if n.pdf_is_int(count):colors.add('ICCBased'+str(n.pdf_to_int(count)))
        if kind=='Separation':
            name=n.pdf_array_get(obj,1)
            if not n.pdf_is_name(name):raise DocumentError('Nombre de colorante Separation no válido.')
            spots.add(n.pdf_to_name(name))
        elif kind=='DeviceN':
            names=n.pdf_array_get(obj,1)
            if not n.pdf_is_array(names) or n.pdf_array_len(names)>32:raise DocumentError('Demasiados colorantes DeviceN.')
            for i in range(n.pdf_array_len(names)):
                name=n.pdf_array_get(names,i)
                if not n.pdf_is_name(name):raise DocumentError('Colorante DeviceN no válido.')
                spots.add(n.pdf_to_name(name))
    def walk(owner,data,fallback,ancestors):
        budget['nodes']+=1;budget['bytes']+=len(data)
        if budget['nodes']>200 or budget['bytes']>32*1024*1024 or len(ancestors)>8:raise DocumentError('Se alcanzó el límite de análisis de color de Forms.')
        res=resources(owner,fallback)
        for op,args,_ in operations(data):
            if op in ['rg','RG']:colors.add('RGB')
            elif op in ['k','K']:colors.add('CMYK')
            elif op in ['g','G']:colors.add('Gray')
            elif op in ['cs','CS']:
                if len(args)!=1 or args[0].kind!='name':raise DocumentError('Espacio de color no compatible.')
                space(args[0].value,res)
            elif op=='gs' and len(args)==1 and args[0].kind=='name':
                state=n.pdf_dict_gets(n.pdf_dict_gets(res,'ExtGState'),args[0].value)
                if not n.pdf_is_dict(state):raise DocumentError('Estado gráfico de color no válido.')
                stroke=n.pdf_dict_gets(state,'OP');fill=n.pdf_dict_gets(state,'op');mode=n.pdf_dict_gets(state,'OPM')
                if any(not n.pdf_is_null(v) and not n.pdf_is_bool(v) for v in [stroke,fill]) or not n.pdf_is_null(mode) and (not n.pdf_is_int(mode) or n.pdf_to_int(mode) not in [0,1]):raise DocumentError('Estado de sobreimpresión no compatible.')
                s=n.pdf_to_bool(stroke) if n.pdf_is_bool(stroke) else False;t=n.pdf_to_bool(fill) if n.pdf_is_bool(fill) else s
                if s or t:overprint.append({'resource':args[0].value,'owner':owner,'stroke':s,'fill':t,'mode':n.pdf_to_int(mode) if n.pdf_is_int(mode) else 0})
            elif op=='Do' and len(args)==1 and args[0].kind=='name':
                child=n.pdf_dict_gets(n.pdf_dict_gets(res,'XObject'),args[0].value);target=n.pdf_to_num(child)
                if n.pdf_to_name(n.pdf_dict_gets(child,'Subtype'))!='Form':continue
                if not target or target in ancestors:raise DocumentError('Invocación Form cíclica o sin identidad.')
                # Each invocation may inherit a different resource dictionary.
                key=(target,n.pdf_to_num(res),owner)
                if key in visited:continue
                visited.add(key);walk(target,stream(doc,target,16*1024*1024),res,(*ancestors,target))
    try:walk(page.xref,page.read_contents(),None,())
    except DocumentError as e:reasons.append(str(e))
    return {'colors':sorted(colors),'spot_colorants':sorted(spots),'overprint_states':overprint[:200],'limited':bool(reasons) or len(overprint)>200,'reasons':reasons,'form_nodes':max(0,budget['nodes']-1)}
