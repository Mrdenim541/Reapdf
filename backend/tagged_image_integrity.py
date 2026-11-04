"""Coordinate a single page-scoped Figure with its image invocation.

Never infer associations from similar rectangles or descriptions. Forms with
stream-bound tags, mixed marked content and shared semantic owners stay protected.
"""
import math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations
from .tagged_text_integrity import snapshot
from .form_structure import pdf_string


def fail(message='Asociación entre figura e imagen no verificable.'):
    raise DocumentError(message)


def context(doc,number):
    snapshot(doc,number,allow_actual_text=True)
    n=f.mupdf;pdf=f._as_pdf_document(doc);root=n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_trailer(pdf),'Root'),'StructTreeRoot');page=doc[number]
    key=doc.xref_get_key(page.xref,'StructParents')
    if key[0]!='int':fail('La página no tiene un índice de etiquetas verificable.')
    key=int(key[1])
    if sum(doc.xref_get_key(p.xref,'StructParents')==('int',str(key)) for p in doc)!=1:fail('Varias páginas comparten el índice semántico.')
    rows=[];seen=set()
    def lookup(tree,depth=0):
        identity=n.pdf_to_num(tree)
        if depth>32 or identity and identity in seen:fail()
        if identity:seen.add(identity)
        if len(seen)>10000 or not n.pdf_is_dict(tree):fail()
        nums=n.pdf_dict_gets(tree,'Nums');kids=n.pdf_dict_gets(tree,'Kids')
        if not n.pdf_is_null(nums):
            if not n.pdf_is_array(nums) or n.pdf_array_len(nums)>20000 or n.pdf_array_len(nums)%2:fail()
            for i in range(0,n.pdf_array_len(nums),2):
                k=n.pdf_array_get(nums,i)
                if not n.pdf_is_int(k):fail()
                if n.pdf_to_int(k)==key:rows.append((tree,nums,i+1,n.pdf_array_get(nums,i+1)))
        for i in range(n.pdf_array_len(kids)):lookup(n.pdf_array_get(kids,i),depth+1)
    lookup(n.pdf_dict_gets(root,'ParentTree'))
    if len(rows)!=1 or not n.pdf_is_array(rows[0][3]):fail('El árbol de padres no contiene una asociación única para la página.')
    records={};seen=set();has_refs=False
    def walk(value,parent,pg,ancestors,depth=0):
        nonlocal has_refs
        if depth>64 or len(seen)>100000:fail()
        if n.pdf_is_array(value):
            for i in range(n.pdf_array_len(value)):walk(n.pdf_array_get(value,i),parent,pg,ancestors,depth+1)
        elif n.pdf_is_dict(value) and n.pdf_to_name(n.pdf_dict_gets(value,'S')):
            x=n.pdf_to_num(value)
            if not x or x in seen or n.pdf_to_num(n.pdf_dict_gets(value,'P'))!=parent:fail('Padres o identidades semánticas no verificables.')
            seen.add(x);explicit=n.pdf_to_num(n.pdf_dict_gets(value,'Pg'));pg=explicit or pg
            if not n.pdf_is_null(n.pdf_dict_gets(value,'Ref')):has_refs=True
            records[x]={'object':value,'page':pg,'parent':parent,'ancestors':ancestors}
            walk(n.pdf_dict_gets(value,'K'),x,pg,ancestors+[value],depth+1)
    walk(n.pdf_dict_gets(root,'K'),n.pdf_to_num(root),None,[root])
    def references(value,pg):
        if n.pdf_is_int(value):return [(pg,n.pdf_to_int(value))]
        if n.pdf_is_array(value):return [r for i in range(n.pdf_array_len(value)) for r in references(n.pdf_array_get(value,i),pg)]
        if n.pdf_is_dict(value) and n.pdf_to_name(n.pdf_dict_gets(value,'Type'))=='MCR':return references(n.pdf_dict_gets(value,'MCID'),n.pdf_to_num(n.pdf_dict_gets(value,'Pg')) or pg)
        return []
    owners={}
    for record in records.values():
        for reference in references(n.pdf_dict_gets(record['object'],'K'),record['page']):owners[reference]=owners.get(reference,0)+1
    scopes={};stack=[];paint={'Do','Tj','TJ',"'",'"','S','s','f','F','f*','B','B*','b','b*','sh'}
    for op,args,token in operations(page.read_contents()):
        if op in ['BDC','BMC']:
            props={};code=None
            if op=='BDC':
                if len(args)!=2 or args[1].kind!='dict' or len(args[1].value)%2:fail('Propiedades de contenido marcado no compatibles.')
                values=args[1].value
                for i in range(0,len(values),2):
                    if values[i].kind!='name' or values[i].value in props:fail()
                    props[values[i].value]=values[i+1]
                if 'MCID' in props:
                    v=props['MCID']
                    if v.kind!='number' or not math.isfinite(v.value) or v.value!=int(v.value) or not 0<=v.value<=10000:fail()
                    code=int(v.value)
            if not args or args[0].kind!='name':fail()
            if len(stack)>=64:fail()
            stack.append({'code':code,'start':args[0].start,'open_end':token.end,'paint':[],'unsafe':bool(set(props)-{'MCID'}),'artifact':args[0].value=='Artifact'})
        elif op=='EMC':
            if not stack:fail('Contenido marcado desequilibrado.')
            scope=stack.pop();scope['close_start']=token.start;scope['end']=token.end
            if scope['code'] is not None:
                if scope['code'] in scopes:fail('MCID repetido en la página.')
                scopes[scope['code']]=scope
        elif op in paint:
            for scope in stack:
                if scope['code'] is not None:
                    scope['paint'].append((op,args[0].start if args else token.start,token.end))
                    if any(v['unsafe'] or v['artifact'] for v in stack):scope['unsafe']=True
    if stack:fail('Contenido marcado sin cierre.')
    return {'root':root,'records':records,'parent_row':rows[0],'scopes':scopes,'has_refs':has_refs,'owners':owners}


def attribute_items(value):
    n=f.mupdf
    if n.pdf_is_null(value):return []
    if n.pdf_is_dict(value):return [value]
    if not n.pdf_is_array(value) or n.pdf_array_len(value)>64:fail('Atributos de figura no compatibles.')
    out=[];previous=False
    for i in range(n.pdf_array_len(value)):
        v=n.pdf_array_get(value,i)
        if n.pdf_is_int(v):
            if not previous or not 0<=n.pdf_to_int(v)<=65535:fail()
            previous=False
        elif n.pdf_is_dict(v):out.append(v);previous=True
        else:fail()
    return out


def probe(doc,number,invocation,ctx):
    n=f.mupdf
    if invocation['_native_path']:fail('Las figuras dentro de Forms necesitan una asociación de stream coordinada.')
    matches=[(code,s) for code,s in ctx['scopes'].items() if s['paint']==[('Do',invocation['_native'][0],invocation['_native'][1])]]
    if len(matches)!=1 or matches[0][1]['unsafe']:fail('La imagen comparte contenido marcado o alternativas no verificables.')
    code,scope=matches[0];row=ctx['parent_row'][3]
    if code>=n.pdf_array_len(row):fail()
    identity=n.pdf_to_num(n.pdf_array_get(row,code));record=ctx['records'].get(identity)
    if not record or record['page']!=doc[number].xref:fail()
    node=record['object'];role=n.pdf_to_name(n.pdf_dict_gets(node,'S'));roles=n.pdf_dict_gets(ctx['root'],'RoleMap');visited=set()
    while not n.pdf_is_null(n.pdf_dict_gets(roles,role)):
        if role in visited or len(visited)>16:fail()
        visited.add(role);mapped=n.pdf_dict_gets(roles,role)
        if not n.pdf_is_name(mapped):fail()
        role=n.pdf_to_name(mapped)
    if role!='Figure':fail('La imagen no está asociada a una figura independiente.')
    child=n.pdf_dict_gets(node,'K')
    if n.pdf_is_array(child):
        if n.pdf_array_len(child)!=1:fail()
        child=n.pdf_array_get(child,0)
    if n.pdf_is_dict(child):
        keys={n.pdf_to_name(n.pdf_dict_get_key(child,i)) for i in range(n.pdf_dict_len(child))}
        if not keys<={'Type','Pg','MCID'} or n.pdf_to_name(n.pdf_dict_gets(child,'Type'))!='MCR':fail()
        pg=n.pdf_to_num(n.pdf_dict_gets(child,'Pg'))
        if pg and pg!=doc[number].xref:fail()
        child=n.pdf_dict_gets(child,'MCID')
    if not n.pdf_is_int(child) or n.pdf_to_int(child)!=code:fail('La figura incluye otros contenidos.')
    # Exactly one semantic owner for this page/MCID; never match by geometry.
    if ctx['owners'].get((doc[number].xref,code))!=1:fail('Hay varias referencias a la misma figura.')
    for ancestor in record['ancestors']+[node]:
        if any(not n.pdf_is_null(n.pdf_dict_gets(ancestor,k)) for k in ['ActualText','C','NS','AF']):fail('La figura usa alternativas o clases que requieren coordinación adicional.')
        for attrs in attribute_items(n.pdf_dict_gets(ancestor,'A')):
            keys={n.pdf_to_name(n.pdf_dict_get_key(attrs,i)) for i in range(n.pdf_dict_len(attrs))}
            if n.pdf_to_name(n.pdf_dict_gets(attrs,'O'))!='Layout' or not keys<={'O','BBox','Placement','Width','Height','Color'}:fail('Atributos de figura fuera del perfil de edición.')
            if ancestor is not node and keys&{'BBox','Width','Height'}:fail('Una caja de antecesor depende de la figura.')
    # Object references attached to the XObject would be another semantic owner.
    if any(doc.xref_get_key(invocation['xref'],k)[0]!='null' for k in ['StructParent','StructParents']):fail()
    alt=n.pdf_dict_gets(node,'Alt')
    actions=['move','replace']
    if not ctx['has_refs'] and n.pdf_is_null(n.pdf_dict_gets(ctx['root'],'IDTree')) and n.pdf_is_null(n.pdf_dict_gets(node,'ID')):actions.append('delete')
    return {'id':identity,'code':code,'scope':scope,'record':record,'alt':n.pdf_to_text_string(alt) if n.pdf_is_string(alt) else '', 'actions':actions}


def update(doc,number,ctx,selection,action,rect,alt):
    n=f.mupdf;pdf=f._as_pdf_document(doc);node=selection['record']['object']
    def copy_dict(obj):
        out=n.pdf_new_dict(pdf,n.pdf_dict_len(obj))
        for i in range(n.pdf_dict_len(obj)):n.pdf_dict_put(out,n.pdf_dict_get_key(obj,i),n.pdf_dict_get_val(obj,i))
        return out
    def copy_array(obj):
        out=n.pdf_new_array(pdf,n.pdf_array_len(obj))
        for i in range(n.pdf_array_len(obj)):n.pdf_array_push(out,n.pdf_array_get(obj,i))
        return out
    extra=[]
    if action not in selection['actions']:fail('Esta figura tiene referencias que impiden eliminar su etiqueta de forma segura.')
    if action=='delete':
        parent=n.pdf_new_indirect(pdf,selection['record']['parent'],0);k=n.pdf_dict_gets(parent,'K')
        if n.pdf_is_array(k):
            out=n.pdf_new_array(pdf,n.pdf_array_len(k))
            for i in range(n.pdf_array_len(k)):
                v=n.pdf_array_get(k,i)
                if n.pdf_to_num(v)!=selection['id']:n.pdf_array_push(out,v)
            n.pdf_dict_puts(parent,'K',out)
        elif n.pdf_to_num(k)==selection['id']:n.pdf_dict_puts(parent,'K',n.pdf_new_array(pdf,0))
        else:fail()
        tree,nums,index,row=ctx['parent_row'];new_row=copy_array(row);n.pdf_array_put(new_row,selection['code'],n.PdfObj());new_nums=copy_array(nums);n.pdf_array_put(new_nums,index,new_row);n.pdf_dict_puts(tree,'Nums',new_nums)
        s=selection['scope'];extra=[(s['start'],s['open_end']),(s['close_start'],s['end'])]
    else:
        if action=='replace':
            if not isinstance(alt,str) or not 1<=len(alt.strip())<=2000 or any(ord(c)<32 and c not in '\n\t' for c in alt):fail('Revisa la descripción de la imagen de reemplazo (1–2000 caracteres).')
            doc.xref_set_key(selection['id'],'Alt',pdf_string(alt.strip()))
        # Clone local attributes: the input can reuse the same A dictionary.
        from .image_editing import _page_matrix
        native=rect*~(_page_matrix(doc[number])*doc[number].rotation_matrix)
        def changed(value):
            if not n.pdf_is_dict(value):return value
            result=copy_dict(value)
            for key in ['BBox','Width','Height']:
                old=n.pdf_dict_gets(value,key)
                if n.pdf_is_null(old):continue
                if key=='BBox':
                    array=n.pdf_new_array(pdf,4)
                    for v in native:n.pdf_array_push(array,n.pdf_new_real(v))
                    n.pdf_dict_puts(result,key,array)
                elif not (n.pdf_is_name(old) and n.pdf_to_name(old)=='Auto'):n.pdf_dict_puts(result,key,n.pdf_new_real(native.width if key=='Width' else native.height))
            return result
        attrs=n.pdf_dict_gets(node,'A')
        if n.pdf_is_array(attrs):
            new=n.pdf_new_array(pdf,n.pdf_array_len(attrs))
            for i in range(n.pdf_array_len(attrs)):n.pdf_array_push(new,changed(n.pdf_array_get(attrs,i)))
            n.pdf_dict_puts(node,'A',new)
        elif not n.pdf_is_null(attrs):n.pdf_dict_puts(node,'A',changed(attrs))
    return extra
