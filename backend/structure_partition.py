"""Partition bounded page tag trees while preserving portable semantic attributes."""
import math
import pymupdf as f
from .engine import DocumentError


def partition(doc,kept):
    n=f.mupdf;native=f._as_pdf_document(doc);catalog=n.pdf_dict_gets(n.pdf_trailer(native),'Root');root=n.pdf_dict_gets(catalog,'StructTreeRoot')
    if n.pdf_is_null(root):return {'nodes':0,'atomic_page_groups':[]}
    def fail(detail=''):
        raise DocumentError('La estructura etiquetada no admite una división verificada. '+(detail+' ' if detail else '')+'Conserva el original o elige explícitamente partes sin etiquetas.')
    if not n.pdf_is_dict(root) or not n.pdf_to_num(root):fail()
    def keys(obj):return {n.pdf_to_name(n.pdf_dict_get_key(obj,i)) for i in range(n.pdf_dict_len(obj))}
    if not keys(root)<={'Type','K','ParentTree','ParentTreeNextKey','RoleMap'}:fail()
    roles=n.pdf_dict_gets(root,'RoleMap')
    if not n.pdf_is_null(roles) and (not n.pdf_is_dict(roles) or n.pdf_dict_len(roles)>2000 or any(not n.pdf_is_name(n.pdf_dict_get_val(roles,i)) for i in range(n.pdf_dict_len(roles)))):fail()
    pages={p.xref:p.number for p in doc};keep=set(kept);mcids={x:{} for x in kept};annotations={};owners={};seen=set();budget=0;characters=0;members={};atomic=set()
    def ref(x):return n.pdf_new_indirect(native,x,0)
    def number(obj,positive=False):
        if not (n.pdf_is_int(obj) or n.pdf_is_real(obj)):fail('Un atributo numérico no es válido.')
        v=n.pdf_to_real(obj)
        if not math.isfinite(v) or abs(v)>1_000_000 or positive and v<0:fail('Un atributo numérico está fuera de los límites.')
        return v
    def attributes(value,role):
        if n.pdf_is_null(value):return False
        values=[]
        if n.pdf_is_array(value):
            if n.pdf_array_len(value)>64:fail('Hay demasiados atributos de estructura.')
            previous=False
            for i in range(n.pdf_array_len(value)):
                item=n.pdf_array_get(value,i)
                if n.pdf_is_int(item):
                    if not previous or not 0<=n.pdf_to_int(item)<=65535:fail('Revisión de atributo no válida.')
                    previous=False
                else:values.append(item);previous=True
        else:values=[value]
        bound=False
        for item in values:
            if not n.pdf_is_dict(item):fail('Atributos de estructura no compatibles.')
            owner=n.pdf_to_name(n.pdf_dict_gets(item,'O'));names=keys(item)
            if owner=='Table':
                if role not in ['TH','TD'] or not names<={'O','RowSpan','ColSpan','Scope'}:fail()
                for key in ['RowSpan','ColSpan']:
                    v=n.pdf_dict_gets(item,key)
                    if not n.pdf_is_null(v) and (not n.pdf_is_int(v) or not 1<=n.pdf_to_int(v)<=100):fail()
                scope=n.pdf_dict_gets(item,'Scope')
                if not n.pdf_is_null(scope) and (not n.pdf_is_name(scope) or n.pdf_to_name(scope) not in ['Row','Column','Both']):fail()
            elif owner=='Layout':
                enums={'Placement':{'Block','Inline','Before','Start','End'},'WritingMode':{'LrTb','RlTb','TbRl'},'TextAlign':{'Start','Center','End','Justify'},'BlockAlign':{'Before','Middle','After','Justify'},'InlineAlign':{'Start','Center','End'}}
                lengths={'SpaceBefore','SpaceAfter','StartIndent','EndIndent','TextIndent'}
                if not names<={'O','BBox','Width','Height','Color'}|lengths|set(enums):fail('Hay atributos de maquetación que aún no se pueden conservar.')
                for key in names-{'O'}:
                    v=n.pdf_dict_gets(item,key)
                    if key in enums:
                        if not n.pdf_is_name(v) or n.pdf_to_name(v) not in enums[key]:fail()
                    elif key in ['BBox','Color']:
                        count=4 if key=='BBox' else 3
                        if not n.pdf_is_array(v) or n.pdf_array_len(v)!=count:fail()
                        nums=[number(n.pdf_array_get(v,i)) for i in range(count)]
                        if key=='BBox':
                            if nums[2]<nums[0] or nums[3]<nums[1]:fail()
                            bound=True
                        elif any(not 0<=a<=1 for a in nums):fail()
                    elif key in ['Width','Height']:
                        if not (n.pdf_is_name(v) and n.pdf_to_name(v)=='Auto'):number(v,True)
                        bound=True
                    else:number(v)
            else:fail('Propietario de atributos de estructura no compatible.')
        return bound
    def associate(page,chain):
        for x in chain:members.setdefault(x,set()).add(page)
    for page in doc:
        items=n.pdf_dict_gets(ref(page.xref),'Annots')
        for i in range(n.pdf_array_len(items)):
            x=n.pdf_to_num(n.pdf_array_get(items,i))
            if not x or x in annotations:fail()
            annotations[x]=page.xref
    def children(value,parent,page,depth,chain=()):
        nonlocal budget,characters
        budget+=1
        if depth>64 or budget>500000:fail('Se superó el presupuesto de estructura.')
        if n.pdf_is_null(value):return None
        if n.pdf_is_array(value):
            if n.pdf_array_len(value)>100000:fail('Se superó el presupuesto de estructura.')
            result=n.pdf_new_array(native,n.pdf_array_len(value))
            for i in range(n.pdf_array_len(value)):
                child=children(n.pdf_array_get(value,i),parent,page,depth+1,chain)
                if child is not None:n.pdf_array_push(result,child)
            return result if n.pdf_array_len(result) else None
        if n.pdf_is_int(value):
            code=n.pdf_to_int(value)
            if page not in pages or not 0<=code<=10000:fail()
            associate(page,chain)
            if page not in keep:return None
            if code in mcids[page]:fail()
            mcids[page][code]=parent;return value
        if not n.pdf_is_dict(value):fail()
        kind=n.pdf_to_name(n.pdf_dict_gets(value,'Type'));explicit=n.pdf_to_num(n.pdf_dict_gets(value,'Pg'));page=explicit or page
        if explicit and explicit not in pages:fail()
        if kind=='OBJR':
            if not keys(value)<={'Type','Pg','Obj'}:fail()
            target=n.pdf_to_num(n.pdf_dict_gets(value,'Obj'))
            if target not in annotations or page not in pages or annotations[target]!=page:fail()
            associate(page,chain)
            if page not in keep:return None
            if target in owners:fail()
            owners[target]=parent;return value
        if kind=='MCR':
            if not keys(value)<={'Type','Pg','MCID'}:fail()
            result=children(n.pdf_dict_gets(value,'MCID'),parent,page,depth+1,chain)
            return value if result is not None else None
        identity=n.pdf_to_num(value);role=n.pdf_to_name(n.pdf_dict_gets(value,'S'))
        if not identity or identity in seen or len(seen)>=100000 or not role or n.pdf_to_num(n.pdf_dict_gets(value,'P'))!=parent:fail()
        seen.add(identity)
        if not keys(value)<={'Type','S','P','Pg','K','Alt','ActualText','T','Lang','ID','E','A'}:fail()
        for key in ['Alt','ActualText','T','Lang','ID','E']:
            v=n.pdf_dict_gets(value,key)
            if not n.pdf_is_null(v):
                if not n.pdf_is_string(v):fail()
                size=len(n.pdf_to_text_string(v));characters+=size
                if size>65536 or characters>2_000_000:fail('Los textos de estructura superan el límite.')
        bound=attributes(n.pdf_dict_gets(value,'A'),role)
        if not n.pdf_is_null(n.pdf_dict_gets(value,'ActualText')) or bound:atomic.add(identity)
        child=children(n.pdf_dict_gets(value,'K'),identity,page,depth+1,chain+(identity,))
        if child is None:
            if page in pages and role in ['TR','TH','TD'] and n.pdf_is_array(n.pdf_dict_gets(value,'K')) and n.pdf_array_len(n.pdf_dict_gets(value,'K'))==0:
                associate(page,chain+(identity,))
                if page in keep:return value
            return None
        n.pdf_dict_puts(value,'K',child)
        if page in keep:n.pdf_dict_puts(value,'Pg',ref(page))
        elif explicit:n.pdf_dict_dels(value,'Pg')
        return value
    child=children(n.pdf_dict_gets(root,'K'),n.pdf_to_num(root),None,0)
    groups={tuple(sorted(pages[p] for p in members.get(x,set()))) for x in atomic if len(members.get(x,set()))>1}
    for x in atomic:
        used=members.get(x,set())
        if used&keep and not used<=keep:fail('Un texto alternativo o una caja de maquetación abarca páginas de distintas partes.')
    report={'nodes':len(seen),'atomic_page_groups':[list(g) for g in sorted(groups)]}
    if child is None:
        n.pdf_dict_dels(catalog,'StructTreeRoot');n.pdf_dict_dels(catalog,'MarkInfo')
        for x in kept:
            n.pdf_dict_dels(ref(x),'StructParents')
            if n.pdf_to_name(n.pdf_dict_gets(ref(x),'Tabs'))=='S':n.pdf_dict_dels(ref(x),'Tabs')
        for x,page in annotations.items():
            if page in keep:doc.xref_set_key(x,'StructParent','null')
        return report
    n.pdf_dict_puts(root,'K',child);pairs=[]
    for key,page in enumerate(kept):
        row=mcids[page];maximum=max(row,default=-1)
        pairs.append(str(key)+' ['+' '.join(f'{row[i]} 0 R' if i in row else 'null' for i in range(maximum+1))+']');doc.xref_set_key(page,'StructParents',str(key))
    next_key=len(kept)
    for annotation,parent in owners.items():
        doc.xref_set_key(annotation,'StructParent',str(next_key));pairs.append(str(next_key)+f' {parent} 0 R');next_key+=1
    for annotation,page in annotations.items():
        if page in keep and annotation not in owners:doc.xref_set_key(annotation,'StructParent','null')
    tree=doc.get_new_xref();doc.update_object(tree,'<< /Nums ['+' '.join(pairs)+'] >>');doc.xref_set_key(n.pdf_to_num(root),'ParentTree',f'{tree} 0 R');doc.xref_set_key(n.pdf_to_num(root),'ParentTreeNextKey',str(next_key))
    return report
