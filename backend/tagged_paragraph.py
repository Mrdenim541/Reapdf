"""Page-scoped paragraph ownership and coordinated continuation of native text.

Associations come from MCIDs, ParentTree and K order, never from rectangles.
Only existing paragraph/heading/cell containers and Span descendants are used.
"""
import math
from bisect import bisect_left
import pymupdf as f
from .engine import DocumentError
from .tagged_image_integrity import context,attribute_items
from .tagged_text_integrity import snapshot


def fail():
    raise DocumentError('El párrafo etiquetado necesita marcadores, padres y orden de lectura únicos; las alternativas, Forms y asociaciones mixtas requieren otra edición.')


def role(ctx,obj):
    n=f.mupdf;value=n.pdf_to_name(n.pdf_dict_gets(obj,'S'));mapping=n.pdf_dict_gets(ctx['root'],'RoleMap');seen=set()
    while not n.pdf_is_null(n.pdf_dict_gets(mapping,value)):
        if value in seen or len(seen)>=16:fail()
        seen.add(value);mapped=n.pdf_dict_gets(mapping,value)
        if not n.pdf_is_name(mapped):fail()
        value=n.pdf_to_name(mapped)
    return value


class Paragraph:
    def __init__(self,doc,number,all_rows,anchor):
        snapshot(doc,number) # ActualText/Stm remain protected, including ancestors.
        self.doc=doc;self.number=number;self.n=n=f.mupdf
        try:self.ctx=ctx=context(doc,number)
        except DocumentError as exc:raise DocumentError('No se pudo asociar el párrafo etiquetado: '+str(exc)) from exc
        if ctx['has_refs'] or any(r['_native_path'] for r in [anchor]):fail()
        owners={};row_codes={}
        from .pdf_content import operations
        def visible(token):
            return bool(token.value) if token.kind=='string' else any(visible(v) for v in token.value) if token.kind=='array' else False
        nonempty={args[0].start for op,args,_ in operations(doc[number].read_contents()) if op in {'Tj','TJ',"'",'"'} and args and any(visible(a) for a in args)}
        direct=sorted((r for r in all_rows if not r['_native_path'] and r.get('_native')),key=lambda r:r['_native'][0]);starts=[r['_native'][0] for r in direct]
        for code,scope in ctx['scopes'].items():
            if scope['unsafe']:continue
            arr=ctx['parent_row'][3]
            if code>=n.pdf_array_len(arr):continue
            identity=n.pdf_to_num(n.pdf_array_get(arr,code));record=ctx['records'].get(identity)
            if not record or ctx['owners'].get((doc[number].xref,code))!=1:continue
            owners[code]=identity
            for row in direct[bisect_left(starts,scope['open_end']):bisect_left(starts,scope['close_start'])]:
                native=row['_native']
                if scope['open_end']<=native[0]<native[1]<=scope['close_start']:
                    row_codes.setdefault(row['id'],[]).append(code)
        codes=row_codes.get(anchor['id'],[])
        if len(codes)!=1 or codes[0] not in owners:fail()
        leaf=ctx['records'][owners[codes[0]]]
        chain=leaf['ancestors']+[leaf['object']]
        containers={'P','H','H1','H2','H3','H4','H5','H6','TH','TD'}
        groups=[v for v in chain if role(ctx,v) in containers]
        if not groups:fail()
        self.group=groups[-1];self.references=[];visited=set()
        def walk(value,pg,parent,depth=0):
            if depth>64:fail()
            if n.pdf_is_array(value):
                for i in range(n.pdf_array_len(value)):walk(n.pdf_array_get(value,i),pg,parent,depth+1)
            elif n.pdf_is_int(value):self.references.append((pg,n.pdf_to_int(value),parent))
            elif n.pdf_is_dict(value) and n.pdf_to_name(n.pdf_dict_gets(value,'Type'))=='MCR':
                keys={n.pdf_to_name(n.pdf_dict_get_key(value,i)) for i in range(n.pdf_dict_len(value))}
                mcid=n.pdf_dict_gets(value,'MCID')
                if not keys<={'Type','Pg','MCID'} or not n.pdf_is_int(mcid):fail()
                self.references.append((n.pdf_to_num(n.pdf_dict_gets(value,'Pg')) or pg,n.pdf_to_int(mcid),parent))
            elif n.pdf_is_dict(value) and n.pdf_to_name(n.pdf_dict_gets(value,'S')):
                identity=n.pdf_to_num(value)
                if not identity or identity in visited or (value is not self.group and role(ctx,value)!='Span'):fail()
                visited.add(identity)
                if n.pdf_to_num(n.pdf_dict_gets(value,'P'))!=parent:fail()
                self._attributes(value)
                pg=n.pdf_to_num(n.pdf_dict_gets(value,'Pg')) or pg
                walk(n.pdf_dict_gets(value,'K'),pg,identity,depth+1)
            else:fail()
        # The group can inherit Pg from any ancestor.
        group_id=n.pdf_to_num(self.group);record=ctx['records'].get(group_id)
        if not record:fail()
        self._attributes(self.group)
        for ancestor in record['ancestors']:self._attributes(ancestor)
        walk(n.pdf_dict_gets(self.group,'K'),record['page'],group_id)
        refs=[(code,identity) for pg,code,identity in self.references if pg==doc[number].xref]
        if not refs or len({c for c,_ in refs})!=len(refs):fail()
        self.rows=[];self.code_by_id={};self.owner_by_code=dict(refs)
        for code,identity in refs:
            scope=ctx['scopes'].get(code)
            if owners.get(code)!=identity or not scope or scope['unsafe'] or any(op not in {'Tj','TJ',"'",'"'} for op,_,_ in scope['paint']):fail()
            selected=sorted([r for r in all_rows if row_codes.get(r['id'])==[code]],key=lambda r:r['_native'][0])
            if any(not r['editable'] for r in selected):fail()
            # Every rendered show must belong to a selected, fully verified row.
            if any(not any(r['_native'][0]<=start<end<=r['_native'][1]+4 for r in selected) for _,start,end in scope['paint'] if start in nonempty):fail()
            self.rows.extend(selected)
            self.code_by_id.update({r['id']:code for r in selected})
        if not self.rows or anchor['id'] not in self.code_by_id:fail()

    def _attributes(self,obj):
        n=self.n
        if any(not n.pdf_is_null(n.pdf_dict_gets(obj,k)) for k in ['ActualText','Alt','C','NS','AF','Ref']):fail()
        # Geometric/placement attributes would become stale on reflow. Table
        # semantics such as Scope/RowSpan/ColSpan are preserved unchanged.
        for attrs in attribute_items(n.pdf_dict_gets(obj,'A')):
            owner=n.pdf_to_name(n.pdf_dict_gets(attrs,'O'))
            keys={n.pdf_to_name(n.pdf_dict_get_key(attrs,i)) for i in range(n.pdf_dict_len(attrs))}
            if owner=='Table' and keys<={'O','Scope','RowSpan','ColSpan','Headers'}:continue
            if owner=='Layout' and keys<={'O','Color'}:continue
            fail()

    def validate(self,rows):
        if [r['id'] for r in rows]!=[r['id'] for r in self.rows]:
            raise DocumentError('Selecciona el párrafo etiquetado completo en su orden de lectura, sin mezclar otras etiquetas.')

    def extend(self,draws):
        """Add MCRs after the corresponding source reference and ParentTree rows."""
        if not draws:return
        n=self.n;doc=self.doc;pdf=f._as_pdf_document(doc);ctx=self.ctx
        if n.pdf_to_num(ctx['root'])<=0:fail()
        tree=n.pdf_dict_gets(ctx['root'],'ParentTree');entries={};seen=set()
        def collect(obj,depth=0):
            identity=n.pdf_to_num(obj)
            if depth>32 or identity and identity in seen or len(entries)>10000:fail()
            if identity:seen.add(identity)
            if not n.pdf_is_dict(obj):fail()
            nums=n.pdf_dict_gets(obj,'Nums');kids=n.pdf_dict_gets(obj,'Kids')
            if not n.pdf_is_null(nums):
                if not n.pdf_is_array(nums) or n.pdf_array_len(nums)%2:fail()
                for i in range(0,n.pdf_array_len(nums),2):
                    key=n.pdf_array_get(nums,i)
                    if not n.pdf_is_int(key):fail()
                    key=n.pdf_to_int(key)
                    if key<0 or key in entries:fail()
                    entries[key]=n.pdf_array_get(nums,i+1)
            if not n.pdf_is_null(kids) and not n.pdf_is_array(kids):fail()
            for i in range(n.pdf_array_len(kids)):collect(n.pdf_array_get(kids,i),depth+1)
        collect(tree)
        reserved=[int(v[1]) for p in doc for v in [doc.xref_get_key(p.xref,'StructParents')] if v[0]=='int']
        declared=n.pdf_dict_gets(ctx['root'],'ParentTreeNextKey')
        next_key=max(max([*entries,*reserved],default=-1)+1,n.pdf_to_int(declared) if n.pdf_is_int(declared) else 0)
        if not 0<=next_key<2_147_483_600:fail()
        page_keys={};new_refs={};by_scope={};used_codes={}
        from .pdf_content import operations
        for number,_,_,_ in draws:
            if number in used_codes:continue
            used_codes[number]=set()
            for op,args,_ in operations(doc[number].read_contents()):
                if op=='BDC':
                    if len(args)!=2 or args[1].kind!='dict':fail()
                    values=args[1].value
                    for i in range(0,len(values),2):
                        if values[i].value=='MCID':
                            if values[i+1].kind!='number' or not math.isfinite(values[i+1].value) or values[i+1].value!=int(values[i+1].value) or not 0<=values[i+1].value<=10000:fail()
                            used_codes[number].add(int(values[i+1].value))
        for number,row,geometry,text in draws:
            source=self.code_by_id[row['id']];owner=self.owner_by_code[source]
            key=(number,source)
            if key not in by_scope:
                page=doc[number]
                if number not in page_keys:
                    old=doc.xref_get_key(page.xref,'StructParents')
                    if old[0]=='null':
                        page_keys[number]=next_key;next_key+=1
                        doc.xref_set_key(page.xref,'StructParents',str(page_keys[number]));entries[page_keys[number]]=n.pdf_new_array(pdf,0)
                    elif old[0]=='int':
                        k=int(old[1])
                        if k not in entries or not n.pdf_is_array(entries[k]) or sum(doc.xref_get_key(p.xref,'StructParents')==old for p in doc)!=1:fail()
                        original=entries[k];copy=n.pdf_new_array(pdf,n.pdf_array_len(original))
                        for i in range(n.pdf_array_len(original)):n.pdf_array_push(copy,n.pdf_array_get(original,i))
                        entries[k]=copy;page_keys[number]=k
                    else:fail()
                arr=entries[page_keys[number]];code=n.pdf_array_len(arr)
                if code>10000:fail()
                # Existing sparse content cannot collide with the next index.
                if code in used_codes[number]:fail()
                n.pdf_array_push(arr,n.pdf_new_indirect(pdf,owner,0));by_scope[key]=code
                new_refs.setdefault(owner,{}).setdefault(source,[]).append((page.xref,code))
            row['_continuation_mcid']=by_scope[key]
        page_numbers={page.xref:page.number for page in doc}
        copied=set(page_keys.values())
        def span(pg,code,owner):
            number=page_numbers.get(pg)
            if number is None:fail()
            value=doc.xref_get_key(pg,'StructParents')
            if value[0]!='int':fail()
            key=int(value[1]);arr=entries.get(key)
            if arr is None or not n.pdf_is_array(arr) or not 0<=code<n.pdf_array_len(arr) or n.pdf_to_num(n.pdf_array_get(arr,code))!=owner:fail()
            if key not in copied:
                copy=n.pdf_new_array(pdf,n.pdf_array_len(arr))
                for i in range(n.pdf_array_len(arr)):n.pdf_array_push(copy,n.pdf_array_get(arr,i))
                arr=entries[key]=copy;copied.add(key)
            identity=doc.get_new_xref()
            doc.update_object(identity,f'<< /Type/StructElem /S/Span /P {owner} 0 R /Pg {pg} 0 R /K {code} >>')
            n.pdf_array_put(arr,code,n.pdf_new_indirect(pdf,identity,0))
            return f'{identity} 0 R'
        # Use page-local Span leaves under the original semantic container.
        # Readers can resolve integer MCIDs on each page independently while
        # the existing P/heading/cell retains its logical identity and order.
        spanning=set(new_refs)
        for owner in list(spanning):
            spanning.update(n.pdf_to_num(a) for a in ctx['records'][owner]['ancestors'] if n.pdf_to_num(a) in ctx['records'])
        for identity in spanning:
            record=ctx['records'][identity];obj=record['object'];pg=record['page'];additions=new_refs.get(identity,{})
            for child_id,child in ctx['records'].items():
                if child['parent']==identity and child['page'] and n.pdf_is_null(n.pdf_dict_gets(child['object'],'Pg')):
                    doc.xref_set_key(child_id,'Pg',f"{child['page']} 0 R")
            def normalize(part):
                if n.pdf_is_array(part):return '['+' '.join(normalize(n.pdf_array_get(part,i)) for i in range(n.pdf_array_len(part)))+']'
                code=n.pdf_to_int(part) if n.pdf_is_int(part) else n.pdf_to_int(n.pdf_dict_gets(part,'MCID')) if n.pdf_is_dict(part) and n.pdf_to_name(n.pdf_dict_gets(part,'Type'))=='MCR' else None
                if code is None:return f.JM_UnicodeFromBuffer(f.JM_object_to_buffer(part,1,0))
                target=n.pdf_to_num(n.pdf_dict_gets(part,'Pg')) if n.pdf_is_dict(part) else 0
                target=target or pg
                if not target:fail()
                out=[span(target,code,identity)]
                if target==doc[self.number].xref and code in additions:
                    out.extend(span(page,mcid,identity) for page,mcid in additions.pop(code))
                return ' '.join(out)
            k=n.pdf_dict_gets(obj,'K');normalized=normalize(k)
            if additions:fail()
            doc.xref_set_key(identity,'K',normalized if normalized.startswith('[') else '['+normalized+']')
        # Clear after materializing all children; iteration order must not
        # restrict an explicitly spanning child to its former source page.
        for identity in spanning:doc.xref_set_key(identity,'Pg','null')
        # Replace only the number-tree container, keeping all previous values.
        flat=n.pdf_new_dict(pdf,1);nums=n.pdf_new_array(pdf,len(entries)*2)
        for key,value in sorted(entries.items()):n.pdf_array_push(nums,n.pdf_new_int(key));n.pdf_array_push(nums,value)
        n.pdf_dict_puts(flat,'Nums',nums);n.pdf_dict_puts(ctx['root'],'ParentTree',flat)
        old_next=n.pdf_dict_gets(ctx['root'],'ParentTreeNextKey')
        n.pdf_dict_puts(ctx['root'],'ParentTreeNextKey',n.pdf_new_int(max(next_key,n.pdf_to_int(old_next) if n.pdf_is_int(old_next) else 0)))
