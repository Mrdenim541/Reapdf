"""Bounded native print/export usage rules, preserving page streams and View state."""
import pymupdf as f
from .engine import DocumentError


def supported(doc,config):
    n=f.mupdf;rules=n.pdf_dict_gets(config,'AS');known=set(doc.get_ocgs())
    if n.pdf_is_null(rules):return True
    view_seen=set()
    if not n.pdf_is_array(rules) or n.pdf_array_len(rules)>20:return False
    for i in range(n.pdf_array_len(rules)):
        rule=n.pdf_array_get(rules,i);keys={n.pdf_to_name(n.pdf_dict_get_key(rule,j)) for j in range(n.pdf_dict_len(rule))}
        event=n.pdf_to_name(n.pdf_dict_gets(rule,'Event'));category=n.pdf_dict_gets(rule,'Category');refs=n.pdf_dict_gets(rule,'OCGs')
        if not n.pdf_is_dict(rule) or not keys<={'Event','Category','OCGs'} or event not in ['Print','Export','View'] or not n.pdf_is_array(category) or not 1<=n.pdf_array_len(category)<=3:return False
        cats=[n.pdf_to_name(n.pdf_array_get(category,j)) for j in range(n.pdf_array_len(category))]
        if len(set(cats))!=len(cats) or not set(cats)<=({'View','Zoom','Language'} if event=='View' else {event}):return False
        if not n.pdf_is_null(refs) and (not n.pdf_is_array(refs) or n.pdf_array_len(refs)>200 or any(not n.pdf_is_indirect(n.pdf_array_get(refs,j)) or n.pdf_to_num(n.pdf_array_get(refs,j)) not in known for j in range(n.pdf_array_len(refs))) or len({n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs))})!=n.pdf_array_len(refs)):return False
        if event=='View':
            ids={n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs))}
            if ids&view_seen:return False
            view_seen.update(ids)
    return True


def model(doc):
    n=f.mupdf;pdf=f._as_pdf_document(doc);config=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/OCProperties/D');rows=[]
    enabled=supported(doc,config)
    for identity in doc.get_ocgs():
        group=n.pdf_load_object(pdf,identity);values={}
        for event in ['Print','Export']:
            raw=n.pdf_dict_getp(group,'Usage/'+event+'/'+event+'State')
            value=n.pdf_to_name(raw) if n.pdf_is_name(raw) else None
            if not n.pdf_is_null(raw) and value not in ['ON','OFF']:enabled=False
            values[event.lower()]=value
        rows.append({'id':identity,**values})
    return {'supported':enabled,'layers':rows,'reason':'' if enabled else 'Las reglas automáticas de estas capas requieren revisión especializada.'}


def apply(doc,values):
    current=model(doc);known={r['id'] for r in current['layers']}
    if not current['supported']:raise DocumentError(current['reason'])
    if not isinstance(values,list) or len(values)!=len(known) or any(not isinstance(row,dict) or set(row)!={'id','print','export'} or type(row['id']) is not int or row['id'] not in known or any(row[k] not in ['ON','OFF',None] for k in ['print','export']) for row in values) or len({r['id'] for r in values})!=len(known):raise DocumentError('Revisa impresión y exportación de todas las capas, sin repetirlas.')
    n=f.mupdf;pdf=f._as_pdf_document(doc);root=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/OCProperties');config=n.pdf_dict_gets(root,'D')
    config=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(config)) if n.pdf_is_dict(config) else n.pdf_new_dict(pdf,4)
    old_rules=n.pdf_dict_gets(config,'AS');rules=n.pdf_new_array(pdf,5)
    for i in range(n.pdf_array_len(old_rules)):
        rule=n.pdf_array_get(old_rules,i)
        if n.pdf_to_name(n.pdf_dict_gets(rule,'Event'))=='View':n.pdf_array_push(rules,rule)
    for event in ['Print','Export']:
        refs=n.pdf_new_array(pdf,len(values))
        for row in values:
            group=n.pdf_load_object(pdf,row['id']);usage=n.pdf_dict_gets(group,'Usage');usage=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(usage)) if n.pdf_is_dict(usage) else n.pdf_new_dict(pdf,2)
            old=n.pdf_dict_gets(usage,event);state=n.pdf_deep_copy_obj(n.pdf_resolve_indirect(old)) if n.pdf_is_dict(old) else n.pdf_new_dict(pdf,1)
            if row[event.lower()] is None:n.pdf_dict_dels(state,event+'State')
            else:n.pdf_dict_puts(state,event+'State',n.pdf_new_name(row[event.lower()]));n.pdf_array_push(refs,n.pdf_new_indirect(pdf,row['id'],0))
            n.pdf_dict_puts(usage,event,state);n.pdf_dict_puts(group,'Usage',usage)
        if n.pdf_array_len(refs):
            rule=n.pdf_new_dict(pdf,3);category=n.pdf_new_array(pdf,1);n.pdf_array_push(category,n.pdf_new_name(event));n.pdf_dict_puts(rule,'Event',n.pdf_new_name(event));n.pdf_dict_puts(rule,'Category',category);n.pdf_dict_puts(rule,'OCGs',refs);n.pdf_array_push(rules,rule)
    if n.pdf_array_len(rules)>20:raise DocumentError('Hasta 20 reglas automáticas de capas.')
    if n.pdf_array_len(rules):n.pdf_dict_puts(config,'AS',rules)
    else:n.pdf_dict_dels(config,'AS')
    n.pdf_dict_puts(root,'D',config)


def for_print(data):
    """Produce a temporary print snapshot; the editable source is never changed."""
    from .engine import open_pdf
    with open_pdf(data) as doc:
        if not doc.get_ocgs():return data
        n=f.mupdf;pdf=f._as_pdf_document(doc);config=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/OCProperties/D');rules=n.pdf_dict_gets(config,'AS')
        if n.pdf_is_null(rules):return data
        if not supported(doc,config):raise DocumentError('Las reglas automáticas de impresión de estas capas requieren un tratamiento no compatible.')
        known=set(doc.get_ocgs());layer=doc.get_layer(-1);on=set(layer.get('on',[]))|(known-set(layer.get('off',[])) if layer.get('basestate','ON')!='OFF' else set())
        changed=False
        for i in range(n.pdf_array_len(rules)):
            rule=n.pdf_array_get(rules,i)
            if n.pdf_to_name(n.pdf_dict_gets(rule,'Event'))!='Print':continue
            refs=n.pdf_dict_gets(rule,'OCGs');ids={n.pdf_to_num(n.pdf_array_get(refs,j)) for j in range(n.pdf_array_len(refs))}
            for identity in ids:
                group=n.pdf_load_object(pdf,identity);state=n.pdf_to_name(n.pdf_dict_getp(group,'Usage/Print/PrintState'))
                if state not in ['ON','OFF']:continue
                if state=='ON':on.add(identity)
                else:on.discard(identity)
                changed=True
        if not changed:return data
        doc.set_layer(-1,on=sorted(on),off=sorted(known-on));doc.xref_set_key(doc.pdf_catalog(),'OCProperties/D/AS','null')
        # Render this transient PDF in View mode using the resolved print state.
        for identity in known:doc.xref_set_key(identity,'Usage/View','null')
        return doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,deflate=True)
