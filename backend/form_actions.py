"""A bounded whitelist of Acrobat formatting helpers, interpreted as data.

Never execute JavaScript. Complete call syntax only; unknown actions stay read-only.
"""
import json,re
from datetime import datetime
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP,localcontext
import pymupdf as f
from .engine import DocumentError

DATES={'dd/mm/yyyy':'%d/%m/%Y','mm/dd/yyyy':'%m/%d/%Y','yyyy-mm-dd':'%Y-%m-%d','dd.mm.yyyy':'%d.%m.%Y'}
TOKEN=re.compile(r'\s*("(?:[^"\\\x00-\x1f]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"|\'(?:[^\'\\\x00-\x1f]|\\[\'\\])*\'|true\b|false\b|[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*')


def call(code):
    if not isinstance(code,str) or len(code)>2000:raise DocumentError('Acción de formulario demasiado larga.')
    match=re.fullmatch(r'\s*([A-Za-z_][A-Za-z_0-9]*)\s*\((.*?)\)\s*;?\s*',code,re.S)
    if not match:raise DocumentError('La acción no es una llamada estándar compatible.')
    args=[];at=0;body=match[2]
    while at<len(body):
        m=TOKEN.match(body,at)
        if not m:raise DocumentError('La acción contiene expresiones no compatibles.')
        token=m[1]
        if token.startswith('"'):
            try:value=json.loads(token)
            except (ValueError,UnicodeError) as exc:raise DocumentError('Cadena de acción no válida.') from exc
        elif token.startswith("'"):value=re.sub(r"\\(['\\])",r'\1',token[1:-1])
        elif token in ['true','false']:value=token=='true'
        else:value=Decimal(token)
        args.append(value);at=m.end()
        if len(args)>6:raise DocumentError('Demasiados argumentos de formato.')
        if at==len(body):break
        if body[at]!=',':raise DocumentError('La acción contiene instrucciones adicionales.')
        at+=1
        if not body[at:].strip():raise DocumentError('La acción tiene un argumento vacío.')
    return match[1],args


def integer(value,low,high):
    if not isinstance(value,Decimal) or not value.is_finite() or value!=int(value) or not low<=value<=high:raise DocumentError('Parámetro de formato fuera de límites.')
    return int(value)


def policy(doc,chain):
    n=f.mupdf;events={}
    for xref in chain:
        obj=n.pdf_load_object(f._as_pdf_document(doc),xref);aa=n.pdf_dict_gets(obj,'AA')
        if n.pdf_is_null(aa):continue
        if not n.pdf_is_dict(aa) or n.pdf_dict_len(aa)>3:raise DocumentError('Las acciones de este campo necesitan otro tratamiento.')
        for i in range(n.pdf_dict_len(aa)):
            event=n.pdf_to_name(n.pdf_dict_get_key(aa,i));action=n.pdf_dict_get_val(aa,i)
            if event not in ['F','K','V'] or event in events or not n.pdf_is_dict(action):raise DocumentError('El campo tiene acciones adicionales o ambiguas.')
            keys={n.pdf_to_name(n.pdf_dict_get_key(action,j)) for j in range(n.pdf_dict_len(action))}
            code=n.pdf_dict_gets(action,'JS')
            if keys!={'S','JS'} or n.pdf_to_name(n.pdf_dict_gets(action,'S'))!='JavaScript' or not n.pdf_is_string(code):raise DocumentError('Solo se interpretan ayudantes estándar explícitos; no se ejecutan scripts.')
            events[event]=call(n.pdf_to_text_string(code))
    if not events:return None
    result={};fmt=events.get('F');stroke=events.get('K');validation=events.get('V')
    if fmt:
        name,args=fmt
        if name=='AFNumber_Format' and len(args)==6:
            places=integer(args[0],0,6);separator=integer(args[1],0,3);negative=integer(args[2],0,3)
            if negative not in [0,2] or integer(args[3],0,0)!=0 or not isinstance(args[4],str) or len(args[4])>12 or any(ord(c)<32 or ord(c)>255 for c in args[4]) or type(args[5]) is not bool:raise DocumentError('El formato de moneda/color requiere otro tratamiento.')
            result={'kind':'number','places':places,'separator':separator,'negative':negative,'currency':args[4],'prepend':args[5]}
        elif name=='AFPercent_Format' and len(args)==2:result={'kind':'percent','places':integer(args[0],0,6),'separator':integer(args[1],0,3),'negative':0,'currency':'','prepend':False}
        elif name=='AFDate_FormatEx' and len(args)==1 and args[0] in DATES:result={'kind':'date','pattern':args[0]}
        else:raise DocumentError('El formato de este campo todavía no está admitido.')
    if stroke:
        name,args=stroke
        expected={'number':'AFNumber_Keystroke','percent':'AFPercent_Keystroke','date':'AFDate_KeystrokeEx'}.get(result.get('kind'))
        if name!=expected or (result['kind']=='date' and args!=[result['pattern']]) or (result['kind']!='date' and (len(args)!=2 or integer(args[0],0,6)!=result['places'] or integer(args[1],0,3)!=result['separator'])):raise DocumentError('El filtro de entrada no coincide con su formato.')
    if validation:
        name,args=validation
        if name!='AFRange_Validate' or len(args)!=4 or type(args[0]) is not bool or type(args[2]) is not bool or any(not isinstance(v,Decimal) or not v.is_finite() or abs(v)>Decimal('1e12') for v in [args[1],args[3]]) or result.get('kind')=='date':raise DocumentError('La validación de este campo requiere otro tratamiento.')
        low=str(args[1]) if args[0] else None;high=str(args[3]) if args[2] else None
        if low is not None and high is not None and Decimal(low)>Decimal(high):raise DocumentError('El rango de validación está invertido.')
        result.update(minimum=low,maximum=high)
        if not result.get('kind'):result['kind']='number';result['plain']=True
    if not result:raise DocumentError('La acción del campo no está admitida.')
    return result


def number(value,separator=1,stored=False):
    if not isinstance(value,str) or len(value)>80:raise DocumentError('El campo necesita un número de hasta 80 caracteres.')
    raw=value.strip()
    if stored:
        pattern=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
    else:
        decimal=',' if separator in [2,3] else '.';group='.' if decimal==',' else ','
        pattern=r'[+-]?(?:\d+(?:'+re.escape(decimal)+r'\d*)?|'+re.escape(decimal)+r'\d+)'
        if separator in [0,2] and group in raw:
            if not re.fullmatch(r'[+-]?\d{1,3}(?:'+re.escape(group)+r'\d{3})+(?:'+re.escape(decimal)+r'\d*)?',raw,flags=re.ASCII):raise DocumentError('La agrupación de miles no coincide con el formato del campo.')
            raw=raw.replace(group,'')
        if decimal==',':
            if not re.fullmatch(pattern,raw,flags=re.ASCII):raise DocumentError('Usa coma como separador decimal en este campo.')
            raw=raw.replace(',','.');pattern=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
    if not re.fullmatch(pattern,raw,flags=re.ASCII):raise DocumentError('El valor no coincide con el formato numérico del campo.')
    result=Decimal(raw)
    if not result.is_finite() or abs(result)>Decimal('1e12'):raise DocumentError('El valor numérico supera 10¹².')
    return result


def value(policy,text,stored=False):
    if not policy:return text,text
    if not text.strip():return '',''
    if policy['kind']=='date':
        try:
            parsed=datetime.strptime(text,DATES[policy['pattern']]);display=parsed.strftime(DATES[policy['pattern']])
            if display!=text or not 1000<=parsed.year<=9999:raise ValueError()
        except (ValueError,TypeError) as exc:raise DocumentError('La fecha no es válida. Usa '+policy['pattern']+'.') from exc
        return display,display
    amount=number(text,policy.get('separator',1),stored)
    if policy.get('minimum') is not None and amount<Decimal(policy['minimum']) or policy.get('maximum') is not None and amount>Decimal(policy['maximum']):raise DocumentError('El número queda fuera del rango permitido por el campo.')
    canonical=format(amount,'f')
    if amount==0:canonical=format(abs(amount),'f')
    if policy.get('plain'):return canonical,canonical
    with localcontext() as ctx:
        ctx.prec=100;shown=amount*(100 if policy['kind']=='percent' else 1);shown=shown.quantize(Decimal(1).scaleb(-policy['places']),rounding=ROUND_HALF_UP)
    negative=shown<0;shown=abs(shown);display=format(shown,(',' if policy['separator'] in [0,2] else '')+'.'+str(policy['places'])+'f')
    if policy['separator'] in [2,3]:display=display.replace(',','X').replace('.',',').replace('X','.')
    currency=policy['currency'];display=currency+display if policy['prepend'] else display+currency
    if negative:display='('+display+')' if policy['negative']==2 else '-'+display
    if policy['kind']=='percent':display+='%'
    return canonical,display


def edit_value(policy,text):
    # PDF /V uses an unformatted decimal; the editable input uses its locale.
    canonical,_=value(policy,text,stored=True)
    return canonical.replace('.',',') if policy.get('kind') in ['number','percent'] and policy.get('separator',1) in [2,3] else canonical
