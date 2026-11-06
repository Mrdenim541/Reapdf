"""Bounded, isolated rewrites of declared text typography and shared classes."""
import math
from collections import defaultdict
import pymupdf as f
from .engine import DocumentError
TYPO={'FontFamily','FontSize','FontWeight','FontStyle'}


def syntax(obj):return f.JM_UnicodeFromBuffer(f.JM_object_to_buffer(obj,1,0))
def name(value):return '/'+''.join(chr(c) if 33<=c<=126 and chr(c) not in '#/%()<>[]{}' else f'#{c:02X}' for c in value.encode('latin-1'))
def fail():raise DocumentError('La tipografía declarada o sus clases no tienen una asociación verificable.')


def items(value):
    n=f.mupdf
    if n.pdf_is_null(value):return []
    if n.pdf_is_array(value) and n.pdf_array_len(value)>128:fail()
    result=[n.pdf_array_get(value,i) for i in range(n.pdf_array_len(value))] if n.pdf_is_array(value) else [value]
    if len(result)>128:fail()
    for obj in result:
        if n.pdf_is_int(obj):
            if n.pdf_to_int64(obj)<0:fail()
        elif not n.pdf_is_dict(obj) or n.pdf_dict_len(obj)>64:fail()
    return result


def declarations(doc,obj):
    n=f.mupdf;result=[('A',i,None,a) for i,a in enumerate(items(n.pdf_dict_gets(obj,'A'))) if n.pdf_is_dict(a)]
    c=n.pdf_dict_gets(obj,'C')
    if n.pdf_is_null(c):return result
    if n.pdf_is_array(c) and n.pdf_array_len(c)>128:fail()
    classes=[n.pdf_array_get(c,i) for i in range(n.pdf_array_len(c))] if n.pdf_is_array(c) else [c]
    if len(classes)>128:fail()
    from .semantic_text import tree
    root=tree(doc).root;mapping=n.pdf_dict_gets(root,'ClassMap')
    if not n.pdf_is_dict(mapping) or not n.pdf_to_num(root):fail()
    for i,key in enumerate(classes):
        if n.pdf_is_int(key):
            if n.pdf_to_int64(key)<0:fail()
            continue
        if not n.pdf_is_name(key):fail()
        label=n.pdf_to_name(key)
        if len(label)>200:fail()
        attrs=n.pdf_dict_gets(mapping,label)
        if n.pdf_is_null(attrs):fail()
        for j,a in enumerate(items(attrs)):
            if n.pdf_is_dict(a):result.append(('C',i,(label,j),a))
    return result


def validate(attr):
    n=f.mupdf
    for key in TYPO:
        value=n.pdf_dict_gets(attr,key)
        if n.pdf_is_null(value):continue
        if key=='FontFamily':
            if not (n.pdf_is_string(value) or n.pdf_is_name(value)):fail()
            text=n.pdf_to_text_string(value) if n.pdf_is_string(value) else n.pdf_to_name(value)
            if not text or len(text)>200 or any(ord(c)<32 for c in text):fail()
        elif key=='FontSize':
            if not n.pdf_is_number(value) or not math.isfinite(n.pdf_to_real(value)) or not 0<n.pdf_to_real(value)<=1000:fail()
        elif key=='FontWeight':
            if not n.pdf_is_number(value) or n.pdf_to_real(value) not in range(100,901,100):fail()
        else:
            if not (n.pdf_is_name(value) or n.pdf_is_string(value)):fail()
            text=n.pdf_to_name(value) if n.pdf_is_name(value) else n.pdf_to_text_string(value)
            if text.lower() not in ['normal','regular','italic','oblique']:fail()


def requested(row,attr):
    n=f.mupdf;options=row['_format_options'];result={};original=options['family']=='original'
    for key in TYPO:
        old=n.pdf_dict_gets(attr,key)
        if n.pdf_is_null(old) or original and key!='FontSize':continue
        if key=='FontFamily':result[key]=f.get_pdf_str({'sans':'DejaVu Sans','serif':'DejaVu Serif','mono':'DejaVu Sans Mono'}[options['family']])
        elif key=='FontSize':
            if abs(row['_geometry']['factor']-1)>1e-5:raise DocumentError('La unidad de tamaño declarada requiere una transformación coordinada adicional.')
            result[key]=f'{row["size"]:.8f}'
        elif key=='FontWeight':result[key]='700' if 'bold' in options['style'] else '400'
        else:
            oldtext=n.pdf_to_name(old) if n.pdf_is_name(old) else n.pdf_to_text_string(old)
            new='italic' if 'italic' in options['style'] else 'normal';new=new if oldtext.islower() else new.title()
            result[key]=name(new) if n.pdf_is_name(old) else f.get_pdf_str(new)
    return result


def prove_complete(doc,node,rows):
    """Every paint in each affected MCID must belong to the edited selection."""
    from .semantic_text import tree,scopes
    from .form_text import structure
    index=tree(doc);n=f.mupdf;refs=set(index.refs[node]);selected=[]
    for row in rows:
        old=row.get('_source_format_row',row);identity=old.get('_semantic_identity')
        if identity is not None and node in index.records[identity]['chain']+[identity]:selected.append(old)
    for pg,stream,code in refs:
        page=next((p for p in doc if p.xref==pg),None)
        if page is None:fail()
        owner=stream or pg;data=doc.xref_stream(stream) if stream else page.read_contents();scope=next((s for s in scopes(data) if s['code']==code),None)
        if scope is None or scope['bad']:fail()
        from .pdf_content import operations
        def visible(t):return bool(t.value) if t.kind=='string' else any(visible(v) for v in t.value) if t.kind=='array' else False
        empty={args[0].start for op,args,_ in operations(data) if op in ['Tj','TJ'] and args and not visible(args[0])}
        for op,start,end in scope['paint']:
            if op in ['Tj','TJ'] and start in empty:continue
            covered=[]
            for row in selected:
                path=row['_native_path'];levels=[(pg,path[0]['start'],path[0]['end'])] if path else []
                levels +=[(s['target'],path[i+1]['start'],path[i+1]['end']) for i,s in enumerate(path[:-1])]
                levels.append((path[-1]['target'] if path else pg,row['_native'][0],row['_native'][1]+4))
                if any(o==owner and a<=start<end<=b for o,a,b in levels):covered.append(row)
            if op not in ['Tj','TJ','Do'] or not covered:raise DocumentError('La tipografía también describe contenido no seleccionado; selecciona el elemento completo.')
            if op=='Do':
                objects=structure(doc,page);keys=lambda path:tuple((s['owner'],s['target'],s['start'],s['end']) for s in path)
                chosen={(keys(r['_native_path']),r['_native'][0],r['_native'][1]) for r in covered}
                for obj in objects:
                    if any(s['owner']==owner and s['start']==start and s['end']==end for s in obj['path']):
                        if (keys(obj['path']),obj['shows'][0].start,obj['shows'][0].end) not in chosen:fail()


def apply(doc,prepared):
    n=f.mupdf;rows=[r for group in prepared.values() for r,_ in group if r.get('_formatted')];updates={};origins={}
    if not rows:return
    from .semantic_text import tree
    index=tree(doc)
    if not index.records:return
    for row in rows:
        identity=row.get('_semantic_identity')
        if identity is None:continue
        for owner in index.records[identity]['chain']+[identity]:
            for kind,at,cls,attr in declarations(doc,index.records[owner]['object']):
                change=requested(row,attr)
                if not change:continue
                key=(owner,kind,at,cls)
                if key in updates and updates[key]!=change:raise DocumentError('La declaración común no admite distintos tamaños o estilos; elige un formato uniforme o conserva esa declaración.')
                updates[key]=change;origins[key]=attr
                if len(updates)>1024:raise DocumentError('La actualización tipográfica supera 1024 declaraciones; divide la selección.')
    for owner in {key[0] for key in updates}:prove_complete(doc,owner,rows)
    apply_changes(doc,index,updates)


def apply_changes(doc,index,updates):
    """Isolate A dictionaries and C classes without changing other users."""
    n=f.mupdf
    def clone(attr,change):
        x=doc.get_new_xref();doc.update_object(x,syntax(n.pdf_resolve_indirect(attr)))
        for key,value in change.items():doc.xref_set_key(x,key,value)
        return f'{x} 0 R'
    grouped=defaultdict(list)
    for key in updates:grouped[(key[0],key[1])].append(key)
    classmap=None;root=n.pdf_to_num(index.root)
    for (owner,kind),keys in grouped.items():
        obj=index.records[owner]['object']
        if kind=='A':
            old=n.pdf_dict_gets(obj,'A');parts=items(old);changes={key[2]:key for key in keys}
            values=[clone(a,updates[changes[i]]) if i in changes else syntax(a) for i,a in enumerate(parts)]
            doc.xref_set_key(owner,'A','['+' '.join(values)+']' if n.pdf_is_array(old) else values[0])
        else:
            if classmap is None:
                from .form_text import clone_dictionary
                classmap=clone_dictionary(doc,root,'ClassMap')
            old=n.pdf_dict_gets(obj,'C');parts=[n.pdf_array_get(old,i) for i in range(n.pdf_array_len(old))] if n.pdf_is_array(old) else [old];changes=defaultdict(dict)
            for key in keys:changes[key[2]][key[3][1]]=key
            for at,indices in changes.items():
                label=n.pdf_to_name(parts[at]);mapping=n.pdf_dict_gets(index.root,'ClassMap');oldattr=n.pdf_dict_gets(mapping,label);attrs=items(oldattr)
                values=[clone(a,updates[indices[i]]) if i in indices else syntax(a) for i,a in enumerate(attrs)]
                alias='ReapdfStyle';counter=0
                while doc.xref_get_key(classmap,alias)[0]!='null':
                    counter+=1;alias=f'ReapdfStyle{counter}'
                    if counter>10000:fail()
                doc.xref_set_key(classmap,alias,'['+' '.join(values)+']' if n.pdf_is_array(oldattr) else values[0]);parts[at]=n.pdf_new_name(alias)
            doc.xref_set_key(owner,'C','['+' '.join(syntax(a) for a in parts)+']' if n.pdf_is_array(old) else syntax(parts[0]))
