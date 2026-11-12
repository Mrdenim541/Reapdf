"""Native screen usage preferences and an explicit, non-destructive context preview."""
import math
import re
import pymupdf as f
from .engine import DocumentError

LANG=re.compile(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z')
CATEGORIES={'View','Zoom','Language'}


def config(doc):
    n=f.mupdf;pdf=f._as_pdf_document(doc)
    return n,pdf,n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/OCProperties/D')


def keys(n,value):return {n.pdf_to_name(n.pdf_dict_get_key(value,i)) for i in range(n.pdf_dict_len(value))}
def number(value):return type(value) in (int,float) and math.isfinite(value)


def model(doc):
    from .layer_usage import supported
    n,pdf,cfg=config(doc);enabled=supported(doc,cfg);rows=[]
    for identity in doc.get_ocgs():
        group=n.pdf_load_object(pdf,identity);usage=n.pdf_dict_gets(group,'Usage')
        if not n.pdf_is_null(usage) and not n.pdf_is_dict(usage):enabled=False
        row={'id':identity,'view':None,'zoom':None,'language':None}
        for name,allowed in [('View',{'ViewState'}),('Zoom',{'min','max'}),('Language',{'Lang','Preferred'})]:
            value=n.pdf_dict_getp(group,'Usage/'+name)
            if n.pdf_is_null(value):continue
            if not n.pdf_is_dict(value) or not keys(n,value)<=allowed:enabled=False;continue
            if name=='View':
                state=n.pdf_dict_gets(value,'ViewState');row['view']=n.pdf_to_name(state)
                if not n.pdf_is_name(state) or row['view'] not in ['ON','OFF']:enabled=False
            elif name=='Zoom':
                bounds={}
                for key in ['min','max']:
                    raw=n.pdf_dict_gets(value,key)
                    bounds[key]=None if n.pdf_is_null(raw) else float(doc.xref_get_key(identity,'Usage/Zoom/'+key)[1]) if n.pdf_is_number(raw) else None
                    if not n.pdf_is_null(raw) and not n.pdf_is_number(raw):enabled=False
                row['zoom']=bounds
                if not valid_zoom(bounds):enabled=False
            else:
                lang=n.pdf_dict_gets(value,'Lang');preferred=n.pdf_dict_gets(value,'Preferred');state=n.pdf_to_name(preferred) if not n.pdf_is_null(preferred) else 'OFF'
                row['language']={'lang':n.pdf_to_text_string(lang),'preferred':state=='ON'}
                if not n.pdf_is_string(lang) or not valid_language(row['language']) or state not in ['ON','OFF'] or not n.pdf_is_null(preferred) and not n.pdf_is_name(preferred):enabled=False
        rows.append(row)
    return {'supported':bool(enabled),'layers':rows,'reason':'' if enabled else 'Las condiciones de pantalla contienen reglas o valores no compatibles; se conservan sin reemplazar.'}


def valid_zoom(value):
    return isinstance(value,dict) and set(value)=={'min','max'} and any(v is not None for v in value.values()) and all(v is None or number(v) and 0<=v<=1_000_000 for v in value.values()) and (value['max'] is None or value['max']>(value['min'] or 0))


def valid_language(value):
    return isinstance(value,dict) and set(value)=={'lang','preferred'} and isinstance(value['lang'],str) and len(value['lang'])<=63 and LANG.fullmatch(value['lang']) is not None and type(value['preferred']) is bool


def apply(doc,values):
    current=model(doc);original={r['id']:r for r in current['layers']}
    if not current['supported']:raise DocumentError(current['reason'])
    if not isinstance(values,list) or len(values)!=len(original):raise DocumentError('Revisa las condiciones de pantalla de todas las capas.')
    for row in values:
        if not isinstance(row,dict) or set(row)!={'id','view','zoom','language'} or type(row['id']) is not int or row['id'] not in original or row['view'] not in ['ON','OFF',None] or row['zoom'] is not None and not valid_zoom(row['zoom']) or row['language'] is not None and not valid_language(row['language']):raise DocumentError('Revisa visibilidad, intervalo de zoom e idioma de cada capa.')
    if len({r['id'] for r in values})!=len(original):raise DocumentError('No repitas capas en las condiciones de pantalla.')
    changed={r['id'] for r in values if r!=original[r['id']]}
    locked=set(doc.get_layer(-1).get('locked',[]))
    if changed&locked:raise DocumentError('No se pueden cambiar las preferencias de una capa bloqueada.')
    if not changed:return
    n,pdf,cfg=config(doc);cfg=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(cfg));old=n.pdf_dict_gets(cfg,'AS');rules=n.pdf_new_array(pdf,8)
    for i in range(n.pdf_array_len(old)):
        rule=n.pdf_array_get(old,i)
        if n.pdf_to_name(n.pdf_dict_gets(rule,'Event'))!='View':n.pdf_array_push(rules,rule);continue
        refs=n.pdf_dict_gets(rule,'OCGs');kept=[n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs)) if n.pdf_to_num(n.pdf_array_get(refs,j)) not in changed]
        if not kept:continue
        copy=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(rule));array=n.pdf_new_array(pdf,len(kept))
        for identity in kept:n.pdf_array_push(array,n.pdf_new_indirect(pdf,identity,0))
        n.pdf_dict_puts(copy,'OCGs',array);n.pdf_array_push(rules,copy)
    for row in values:
        if row['id'] not in changed:continue
        group=n.pdf_load_object(pdf,row['id']);usage=n.pdf_dict_gets(group,'Usage');usage=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(usage)) if n.pdf_is_dict(usage) else n.pdf_new_dict(pdf,3)
        for name in ['View','Zoom','Language']:
            value=row[name.lower()];n.pdf_dict_dels(usage,name)
            if value is None:continue
            raw=n.pdf_new_dict(pdf,2)
            if name=='View':n.pdf_dict_puts(raw,'ViewState',n.pdf_new_name(value))
            elif name=='Zoom':
                for bound,v in value.items():
                    if v is not None:n.pdf_dict_puts(raw,bound,n.pdf_new_real(v))
            else:
                n.pdf_dict_puts(raw,'Lang',n.pdf_new_text_string(value['lang']));n.pdf_dict_puts(raw,'Preferred',n.pdf_new_name('ON' if value['preferred'] else 'OFF'))
            n.pdf_dict_puts(usage,name,raw)
        n.pdf_dict_puts(group,'Usage',usage)
    grouped={}
    for row in values:
        if row['id'] not in changed:continue
        categories=tuple(c for c in ['View','Zoom','Language'] if row[c.lower()] is not None)
        if categories:grouped.setdefault(categories,[]).append(row['id'])
    for categories,identities in grouped.items():
        refs=n.pdf_new_array(pdf,len(identities));cats=n.pdf_new_array(pdf,len(categories));rule=n.pdf_new_dict(pdf,3)
        for identity in identities:n.pdf_array_push(refs,n.pdf_new_indirect(pdf,identity,0))
        for category in categories:n.pdf_array_push(cats,n.pdf_new_name(category))
        n.pdf_dict_puts(rule,'Event',n.pdf_new_name('View'));n.pdf_dict_puts(rule,'Category',cats);n.pdf_dict_puts(rule,'OCGs',refs);n.pdf_array_push(rules,rule)
    if n.pdf_array_len(rules)>20:raise DocumentError('Las condiciones superan el límite de 20 reglas automáticas.')
    n.pdf_dict_puts(cfg,'AS',rules);n.pdf_dict_putp(n.pdf_trailer(pdf),'Root/OCProperties/D',cfg)


def resolve(data,context):
    """Temporary snapshot for the layer panel; not a saved zoom-dependent edit."""
    if not isinstance(context,dict) or set(context)!={'zoom','language'} or not number(context['zoom']) or not .05<=context['zoom']<=16 or not isinstance(context['language'],str) or len(context['language'])>63 or not LANG.fullmatch(context['language']):raise DocumentError('Usa zoom entre 5 y 1600 % y un idioma como es o es-MX.')
    with f.open(stream=data,filetype='pdf') as doc:
        info=model(doc)
        if not info['supported']:raise DocumentError(info['reason'])
        rows={r['id']:r for r in info['layers']};n,pdf,cfg=config(doc);rules=n.pdf_dict_gets(cfg,'AS');tests={}
        language_ids=set()
        for i in range(n.pdf_array_len(rules)):
            rule=n.pdf_array_get(rules,i);cats=n.pdf_dict_gets(rule,'Category');refs=n.pdf_dict_gets(rule,'OCGs')
            if n.pdf_to_name(n.pdf_dict_gets(rule,'Event'))=='View' and any(n.pdf_to_name(n.pdf_array_get(cats,j))=='Language' for j in range(n.pdf_array_len(cats))):language_ids.update(n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs)))
        candidates=[rows[k]['language'] for k in language_ids if rows[k]['language'] is not None]
        exact=any(v['lang'].lower()==context['language'].lower() for v in candidates)
        partial=[v for v in candidates if v['lang'].split('-')[0].lower()==context['language'].split('-')[0].lower()]
        if not exact and partial and len({v['lang'].lower() for v in partial if v['preferred']})!=1:raise DocumentError('Para este grupo elige un idioma exacto o una única alternativa preferida; la coincidencia parcial es ambigua.')
        for i in range(n.pdf_array_len(rules)):
            rule=n.pdf_array_get(rules,i)
            if n.pdf_to_name(n.pdf_dict_gets(rule,'Event'))!='View':continue
            refs=n.pdf_dict_gets(rule,'OCGs');ids=[n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs))];cats=n.pdf_dict_gets(rule,'Category')
            for j in range(n.pdf_array_len(cats)):
                category=n.pdf_to_name(n.pdf_array_get(cats,j))
                for identity in ids:
                    row=rows[identity];value=row[category.lower()]
                    if value is None:continue
                    if category=='View':state=value=='ON'
                    elif category=='Zoom':state=(value['min'] or 0)<=context['zoom'] and (value['max'] is None or context['zoom']<value['max'])
                    else:state=value['lang'].lower()==context['language'].lower() if exact else value in partial and value['preferred']
                    tests.setdefault(identity,[]).append(state)
        layer=doc.get_layer(-1);known=set(rows);on=set(layer.get('on',[]))|(known-set(layer.get('off',[])) if layer.get('basestate','ON')!='OFF' else set())
        for identity,states in tests.items():
            if all(states):on.add(identity)
            else:on.discard(identity)
        for group in layer.get('rbgroups',[]):
            if len(on.intersection(group))>1:raise DocumentError('Las condiciones activarían varias capas del mismo grupo exclusivo; revisa las preferencias.')
        doc.set_layer(-1,on=sorted(on),off=sorted(known-on))
        # MuPDF consults ViewState even without AS. Strip only in this temporary
        # snapshot so its implicit behavior cannot override the resolved state.
        for identity in known:doc.xref_set_key(identity,'Usage/View','null')
        doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS','null')
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,deflate=True)
