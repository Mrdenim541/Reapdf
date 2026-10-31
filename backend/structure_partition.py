"""Prune bounded tag trees and rebuild page/annotation parent keys for PDF parts."""
import pymupdf as f
from .engine import DocumentError


def partition(doc,kept):
    n=f.mupdf;native=f._as_pdf_document(doc);catalog=n.pdf_dict_gets(n.pdf_trailer(native),'Root');root=n.pdf_dict_gets(catalog,'StructTreeRoot')
    if n.pdf_is_null(root):return
    def fail():raise DocumentError('La estructura etiquetada no admite una división verificada. Conserva el original y usa una copia preparada para extraer páginas.')
    if not n.pdf_is_dict(root) or not n.pdf_to_num(root):fail()
    def keys(obj):return {n.pdf_to_name(n.pdf_dict_get_key(obj,i)) for i in range(n.pdf_dict_len(obj))}
    if not keys(root)<={'Type','K','ParentTree','ParentTreeNextKey','RoleMap'}:fail()
    if any(not n.pdf_is_null(n.pdf_dict_gets(root,key)) for key in ['IDTree','Namespaces','ClassMap','AF']):fail()
    roles=n.pdf_dict_gets(root,'RoleMap')
    if not n.pdf_is_null(roles) and (not n.pdf_is_dict(roles) or any(not n.pdf_is_name(n.pdf_dict_get_val(roles,i)) for i in range(n.pdf_dict_len(roles)))):fail()
    pages={p.xref:p.number for p in doc};keep=set(kept);mcids={x:{} for x in kept};annotations={};owners={};seen=set();budget=0
    def ref(x):return n.pdf_new_indirect(native,x,0)
    for page in doc:
        items=n.pdf_dict_gets(ref(page.xref),'Annots')
        for i in range(n.pdf_array_len(items)):
            x=n.pdf_to_num(n.pdf_array_get(items,i))
            if not x or x in annotations:fail()
            annotations[x]=page.xref
    def children(value,parent,page,depth):
        nonlocal budget
        budget+=1
        if depth>32 or budget>10000:fail()
        if n.pdf_is_null(value):return None
        if n.pdf_is_array(value):
            result=n.pdf_new_array(native,n.pdf_array_len(value))
            for i in range(n.pdf_array_len(value)):
                child=children(n.pdf_array_get(value,i),parent,page,depth+1)
                if child is not None:n.pdf_array_push(result,child)
            return result if n.pdf_array_len(result) else None
        if n.pdf_is_int(value):
            number=n.pdf_to_int(value)
            if page not in pages or not 0<=number<=10000:fail()
            if page not in keep:return None
            if number in mcids[page]:fail()
            mcids[page][number]=parent;return value
        if not n.pdf_is_dict(value):fail()
        kind=n.pdf_to_name(n.pdf_dict_gets(value,'Type'))
        explicit=n.pdf_to_num(n.pdf_dict_gets(value,'Pg'));page=explicit or page
        if explicit and explicit not in pages:fail()
        if kind=='OBJR':
            if not keys(value)<={'Type','Pg','Obj'}:fail()
            target=n.pdf_to_num(n.pdf_dict_gets(value,'Obj'))
            if target not in annotations or page not in pages or annotations[target]!=page:fail()
            if page not in keep:return None
            if target in owners:fail()
            owners[target]=parent;return value
        if kind=='MCR':
            if not keys(value)<={'Type','Pg','MCID'}:fail()
            if not n.pdf_is_null(n.pdf_dict_gets(value,'Stm')):fail()
            result=children(n.pdf_dict_gets(value,'MCID'),parent,page,depth+1)
            return value if result is not None else None
        identity=n.pdf_to_num(value)
        if not identity or identity in seen or len(seen)>=2000 or not n.pdf_to_name(n.pdf_dict_gets(value,'S')) or n.pdf_to_num(n.pdf_dict_gets(value,'P'))!=parent:fail()
        seen.add(identity)
        if not keys(value)<={'Type','S','P','Pg','K','Alt','T','Lang','ID','E','A'}:fail()
        if any(not n.pdf_is_null(n.pdf_dict_gets(value,key)) and not n.pdf_is_string(n.pdf_dict_gets(value,key)) for key in ['Alt','ActualText','T','Lang','ID','E']):fail()
        if any(not n.pdf_is_null(n.pdf_dict_gets(value,key)) for key in ['Ref','AF','NS']):fail()
        attrs=n.pdf_dict_gets(value,'A')
        if not n.pdf_is_null(attrs):
            if n.pdf_to_name(n.pdf_dict_gets(value,'S')) not in ['TH','TD'] or not n.pdf_is_dict(attrs) or not keys(attrs)<={'O','RowSpan','ColSpan','Scope'} or n.pdf_to_name(n.pdf_dict_gets(attrs,'O'))!='Table':fail()
            for key in ['RowSpan','ColSpan']:
                v=n.pdf_dict_gets(attrs,key)
                if not n.pdf_is_null(v) and (not n.pdf_is_int(v) or not 1<=n.pdf_to_int(v)<=100):fail()
            scope=n.pdf_dict_gets(attrs,'Scope')
            if not n.pdf_is_null(scope) and (not n.pdf_is_name(scope) or n.pdf_to_name(scope) not in ['Row','Column','Both']):fail()
        child=children(n.pdf_dict_gets(value,'K'),identity,page,depth+1)
        if child is None:
            if page in keep and n.pdf_to_name(n.pdf_dict_gets(value,'S'))=='TR' and n.pdf_is_array(n.pdf_dict_gets(value,'K')) and n.pdf_array_len(n.pdf_dict_gets(value,'K'))==0:return value
            return None
        n.pdf_dict_puts(value,'K',child)
        if page in keep:n.pdf_dict_puts(value,'Pg',ref(page))
        elif explicit:n.pdf_dict_dels(value,'Pg')
        return value
    child=children(n.pdf_dict_gets(root,'K'),n.pdf_to_num(root),None,0)
    if child is None:
        n.pdf_dict_dels(catalog,'StructTreeRoot');n.pdf_dict_dels(catalog,'MarkInfo')
        for x in kept:
            n.pdf_dict_dels(ref(x),'StructParents')
            if n.pdf_to_name(n.pdf_dict_gets(ref(x),'Tabs'))=='S':n.pdf_dict_dels(ref(x),'Tabs')
        for x,page in annotations.items():
            if page in keep:doc.xref_set_key(x,'StructParent','null')
        return
    n.pdf_dict_puts(root,'K',child)
    # Use explicit new keys; old ParentTree arrays must not keep off-part nodes.
    pairs=[]
    for key,page in enumerate(kept):
        row=mcids[page];maximum=max(row,default=-1)
        pairs.append(str(key)+' ['+' '.join(f'{row[i]} 0 R' if i in row else 'null' for i in range(maximum+1))+']')
        doc.xref_set_key(page,'StructParents',str(key))
    next_key=len(kept)
    for annotation,parent in owners.items():
        doc.xref_set_key(annotation,'StructParent',str(next_key));pairs.append(str(next_key)+f' {parent} 0 R');next_key+=1
    for annotation,page in annotations.items():
        if page in keep and annotation not in owners:doc.xref_set_key(annotation,'StructParent','null')
    tree=doc.get_new_xref();doc.update_object(tree,'<< /Nums ['+' '.join(pairs)+'] >>');doc.xref_set_key(n.pdf_to_num(root),'ParentTree',f'{tree} 0 R');doc.xref_set_key(n.pdf_to_num(root),'ParentTreeNextKey',str(next_key))
