"""Coordinated native line edits for ActualText and page/stream MCID owners.

Never remove alternatives to make an edit succeed. Stream-owned Forms retain
identity and are writable only when invoked once in the entire document.
"""
import hashlib,json,math
from collections import Counter,defaultdict
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations,placements,patch,names
from .tagged_text_integrity import snapshot,marker_signature


def fail(message='La asociación semántica del texto no es única o requiere editar varios contenidos juntos.'):
    raise DocumentError(message)


def has_alternatives(doc,page):
    from .form_text import resource_owner
    if doc.xref_get_key(resource_owner(doc,page.xref),'Resources/Properties')[0]!='null':return True
    objects=list(dict.fromkeys(item[0] for item in page.get_xobjects()))
    if len(objects)>200:return True
    total=0
    for identity in [None,*objects]:
        if identity is not None and doc.xref_get_key(resource_owner(doc,identity),'Resources/Properties')[0]!='null':return True
        data=page.read_contents() if identity is None else doc.xref_stream(identity);total+=len(data)
        if total>32*1024*1024:return True
        try:
            if 'ActualText' in names(data):return True
        except DocumentError:return True
    return False


def value_text(value):
    if not isinstance(value,str) or len(value)>4000 or any(ord(c)<32 and c not in '\n\t' or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in value):fail('El texto de lectura accesible admite hasta 4000 caracteres Unicode, sin controles incompatibles.')
    return value


def decode(raw):
    if raw.startswith((b'\xfe\xff',b'\xff\xfe')):
        try:return value_text(raw.decode('utf-16'))
        except UnicodeError:fail('ActualText contiene Unicode dañado.')
    if raw.startswith(b'\xef\xbb\xbf'):
        try:return value_text(raw.decode('utf-8-sig'))
        except UnicodeError:fail('ActualText contiene Unicode dañado.')
    with f.open() as temporary:
        x=temporary.get_new_xref();temporary.update_object(x,'<< /Value <'+raw.hex()+'> >>');kind,text=temporary.xref_get_key(x,'Value')
        if kind!='string':fail()
        return value_text(text)


def scopes(data):
    result=[];stack=[]
    for op,args,token in operations(data):
        if op in ['BDC','BMC']:
            if not args or args[0].kind!='name' or len(stack)>=64:fail()
            props={};bad=False
            if op=='BDC':
                if len(args)!=2 or args[1].kind!='dict':bad=True
                else:
                    values=args[1].value
                    if len(values)%2:fail()
                    for i in range(0,len(values),2):
                        if values[i].kind!='name' or values[i].value in props:fail()
                        props[values[i].value]=values[i+1]
            code=props.get('MCID');actual=props.get('ActualText')
            if code is not None and (code.kind!='number' or not math.isfinite(code.value) or code.value!=int(code.value) or not 0<=code.value<=10000):fail()
            if actual is not None and actual.kind!='string':fail()
            stack.append({'open':token.end,'close':None,'code':int(code.value) if code else None,'actual':actual,'text':decode(actual.value) if actual else None,'bad':bad or bool(set(props)-{'MCID','ActualText','Lang'}) or args[0].value=='Artifact','paint':[]})
        elif op=='EMC':
            if not stack:fail()
            scope=stack.pop();scope['close']=token.start;result.append(scope)
        elif op in ['Tj','TJ',"'",'"','Do','S','s','f','F','f*','B','B*','b','b*','sh']:
            for scope in stack:scope['paint'].append((op,args[0].start if args else token.start,token.end))
    if stack:fail()
    codes=[s['code'] for s in result if s['code'] is not None]
    if len(codes)!=len(set(codes)):fail('MCID repetido en el mismo contenido.')
    return result


def resources(doc,owner,name):
    for _ in range(32):
        kind,value=doc.xref_get_key(owner,'Resources/XObject/'+name)
        if kind=='xref':return int(value.split()[0])
        if doc.xref_get_key(owner,'Resources')[0]!='null':return None
        kind,value=doc.xref_get_key(owner,'Parent')
        if kind!='xref':return None
        owner=int(value.split()[0])
    fail()


def occurrences(doc):
    cached=getattr(doc,'_reapdf_semantic_occurrences',None)
    if cached is not None:return cached
    counts=Counter();pages=defaultdict(set);budget=[0,0]
    def walk(owner,data,number,ancestors):
        budget[0]+=1;budget[1]+=len(data)
        if budget[0]>4000 or budget[1]>64*1024*1024 or len(ancestors)>8:fail('El documento supera el presupuesto de apariciones Form etiquetadas.')
        for op,args,_ in operations(data):
            if op!='Do' or len(args)!=1 or args[0].kind!='name':continue
            target=resources(doc,owner,args[0].value)
            if not target or doc.xref_get_key(target,'Subtype')!=('name','/Form'):continue
            if target in ancestors:fail('Ciclo de apariciones Form.')
            counts[target]+=1;pages[target].add(number);walk(target,doc.xref_stream(target),number,ancestors|{target})
    for page in doc:walk(page.xref,page.read_contents(),page.number,set())
    doc._reapdf_semantic_occurrences=(counts,pages);return counts,pages


class Tree:
    def __init__(self,doc):
        self.doc=doc;self.n=n=f.mupdf;pdf=f._as_pdf_document(doc);self.root=n.pdf_dict_gets(n.pdf_dict_gets(n.pdf_trailer(pdf),'Root'),'StructTreeRoot');self.records={};self.owners=defaultdict(list);self.parents={};self.refs=defaultdict(list);self.indices=Counter()
        if n.pdf_is_null(self.root):return
        containers=[p.xref for p in doc]+[x for x in range(1,doc.xref_length()) if doc.xref_get_key(x,'Subtype')==('name','/Form')]
        self.indices.update(int(v[1]) for x in containers for v in [doc.xref_get_key(x,'StructParents')] if v[0]=='int')
        def numbers(obj,depth=0,seen=None):
            seen=set() if seen is None else seen;identity=n.pdf_to_num(obj)
            if depth>32 or identity and identity in seen or len(self.parents)>10000:fail()
            if identity:seen.add(identity)
            if not n.pdf_is_dict(obj):fail()
            nums=n.pdf_dict_gets(obj,'Nums');kids=n.pdf_dict_gets(obj,'Kids')
            if not n.pdf_is_null(nums):
                if not n.pdf_is_array(nums) or n.pdf_array_len(nums)%2:fail()
                for i in range(0,n.pdf_array_len(nums),2):
                    key=n.pdf_array_get(nums,i)
                    if not n.pdf_is_int(key):fail()
                    key=n.pdf_to_int64(key)
                    if key<0 or key in self.parents:fail()
                    self.parents[key]=n.pdf_array_get(nums,i+1)
            for i in range(n.pdf_array_len(kids)):numbers(n.pdf_array_get(kids,i),depth+1,seen)
        numbers(n.pdf_dict_gets(self.root,'ParentTree'))
        def walk(value,parent,pg,chain,depth=0):
            if depth>64 or len(self.records)>100000:fail()
            if n.pdf_is_array(value):
                for i in range(n.pdf_array_len(value)):walk(n.pdf_array_get(value,i),parent,pg,chain,depth+1)
            elif n.pdf_is_int(value):self.add(pg,0,n.pdf_to_int64(value),parent,chain)
            elif n.pdf_is_dict(value):
                role=n.pdf_to_name(n.pdf_dict_gets(value,'S'));kind=n.pdf_to_name(n.pdf_dict_gets(value,'Type'))
                if role:
                    identity=n.pdf_to_num(value)
                    if not identity or identity in self.records or n.pdf_to_num(n.pdf_dict_gets(value,'P'))!=parent:fail()
                    self.records[identity]={'object':value,'chain':chain,'pg':n.pdf_to_num(n.pdf_dict_gets(value,'Pg')) or pg}
                    walk(n.pdf_dict_gets(value,'K'),identity,self.records[identity]['pg'],chain+[identity],depth+1)
                elif kind=='MCR':
                    keys={n.pdf_to_name(n.pdf_dict_get_key(value,i)) for i in range(n.pdf_dict_len(value))};code=n.pdf_dict_gets(value,'MCID')
                    if not keys<={'Type','Pg','Stm','MCID'} or not n.pdf_is_int(code):fail()
                    self.add(n.pdf_to_num(n.pdf_dict_gets(value,'Pg')) or pg,n.pdf_to_num(n.pdf_dict_gets(value,'Stm')),n.pdf_to_int64(code),parent,chain)
                elif kind!='OBJR':fail()
            elif not n.pdf_is_null(value):fail()
        walk(n.pdf_dict_gets(self.root,'K'),n.pdf_to_num(self.root),None,[])

    def add(self,pg,stream,code,parent,chain):
        if code<0 or code>10000:fail()
        ref=(pg,stream,code);self.owners[ref].append(parent)
        for identity in chain:self.refs[identity].append(ref)

    def owner(self,page,stream,code):
        n=self.n;doc=self.doc;ref=(doc[page].xref,stream,code);owners=self.owners.get(ref,[])
        if len(owners)!=1:fail()
        container=stream or doc[page].xref;kind,key=doc.xref_get_key(container,'StructParents')
        if kind!='int':fail()
        key=int(key);row=self.parents.get(key)
        if row is None or not n.pdf_is_array(row) or code>=n.pdf_array_len(row) or n.pdf_to_num(n.pdf_array_get(row,code))!=owners[0]:fail('ParentTree no coincide con el propietario del texto.')
        # Page and stream indices live in the same number-tree namespace.
        if self.indices[key]!=1:fail('Índice ParentTree compartido o ambiguo.')
        return owners[0],ref


def tree(doc):
    cached=getattr(doc,'_reapdf_semantic_tree',None)
    if cached is None:cached=Tree(doc);doc._reapdf_semantic_tree=cached
    return cached


def stream_editable(doc,number,target):
    if doc.xref_get_key(target,'StructParents')[0]!='int':return False
    counts,pages=occurrences(doc)
    if counts[target]!=1 or pages[target]!={number}:return False
    index=tree(doc);found=False
    for scope in scopes(doc.xref_stream(target)):
        if scope['code'] is None:continue
        index.owner(number,target,scope['code']);found=True
    return found


def text_only_form(doc,target,ancestors=None,budget=None):
    ancestors=set() if ancestors is None else ancestors;budget=[0,0] if budget is None else budget
    if target in ancestors or len(ancestors)>8:return False
    data=doc.xref_stream(target);budget[0]+=1;budget[1]+=len(data)
    if budget[0]>200 or budget[1]>32*1024*1024:return False
    parsed=placements(data)['texts']
    for op,args,token in operations(data):
        if op in ['Tj','TJ']:
            if not args:return False
            if not any(obj['shows'][0].start<=args[0].start<token.end<=obj['shows'][0].end+4 for obj in parsed):return False
        elif op=='Do':
            if len(args)!=1 or args[0].kind!='name':return False
            child=resources(doc,target,args[0].value)
            if not child or doc.xref_get_key(child,'Subtype')!=('name','/Form') or not text_only_form(doc,child,ancestors|{target},budget):return False
        elif op in ["'",'"','S','s','f','F','f*','B','B*','b','b*','sh']:return False
    return True


class Index:
    def __init__(self,doc,number,objects):
        self.doc=doc;self.number=number;self.objects=objects;self.data={doc[number].xref:doc[number].read_contents()};self.parsed={};self.structure=None
        for obj in objects:
            for step in obj['path']:
                if step['target'] not in self.data:self.data[step['target']]=doc.xref_stream(step['target'])
        self.has_root=doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null'
        self.alternative_owners={owner for owner,data in self.data.items() if 'ActualText' in names(data)}

    def scopes(self,owner):
        if owner not in self.parsed:self.parsed[owner]=scopes(self.data[owner])
        return self.parsed[owner]

    def probe(self,row):
        if not self.has_root and not self.alternative_owners:return row
        doc=self.doc;path=row['_native_path'];levels=[(doc[self.number].xref,path[0]['start'],path[0]['end'])] if path else []
        levels += [(step['target'],path[i+1]['start'],path[i+1]['end']) for i,step in enumerate(path[:-1])]
        owner=path[-1]['target'] if path else doc[self.number].xref;levels.append((owner,row['_native'][0],row['_native'][1]))
        if any(level in self.alternative_owners for level,_,_ in levels):row['semantic_protected']=True
        if path and doc.xref_get_key(owner,'StructParents')[0]!='null':row.update(stream_tagged=True,semantic_protected=True)
        alternatives=[];references=[]
        for level,start,end in levels:
            for scope in self.scopes(level):
                if not scope['open']<=start<end<=scope['close']:continue
                if scope['bad'] and (scope['actual'] or scope['code'] is not None):fail()
                if scope['actual']:
                    alternatives.append({'kind':'inline','owner':level,'token':scope['actual'],'value':scope['text'],'scope':scope})
                if scope['code'] is not None:
                    stream=level if doc.xref_get_key(level,'Subtype')==('name','/Form') and doc.xref_get_key(level,'StructParents')[0]!='null' else 0
                    if stream or doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':references.append((level,scope,stream))
        if references:
            if len(references)!=1:fail()
            level,scope,stream=references[0];index=tree(doc);identity,ref=index.owner(self.number,stream,scope['code']);row['_semantic_identity']=identity;n=f.mupdf
            for node_id in index.records[identity]['chain']+[identity]:
                obj=index.records[node_id]['object'];actual=n.pdf_dict_gets(obj,'ActualText')
                if not n.pdf_is_null(actual):
                    row['semantic_protected']=True
                    if not n.pdf_is_string(actual) or index.refs[node_id]!=[ref]:fail('ActualText abarca más de un contenido; no se modifica parcialmente.')
                    alternatives.append({'kind':'node','owner':node_id,'value':value_text(n.pdf_to_text_string(actual)),'scope':scope,'scope_owner':level})
            row['_semantic_stream']=stream
            if stream:row.update(stream_tagged=True,semantic_protected=True)
        if alternatives:
            if len({a['value'] for a in alternatives})!=1:fail('Hay alternativas de lectura diferentes sobre el mismo texto.')
            for alt in alternatives:
                scope=alt['scope'];scope_owner=alt.get('scope_owner',alt['owner'])
                selected=[]
                for obj in self.objects:
                    steps=obj['path'];positions=[(doc[self.number].xref,steps[0]['start'],steps[0]['end'])] if steps else []
                    positions += [(step['target'],steps[i+1]['start'],steps[i+1]['end']) for i,step in enumerate(steps[:-1])]
                    positions.append((steps[-1]['target'] if steps else doc[self.number].xref,obj['shows'][0].start,obj['shows'][0].end))
                    if any(level==scope_owner and scope['open']<=start<end<=scope['close'] for level,start,end in positions):selected.append(obj)
                if len(selected)!=1:fail('ActualText abarca varios fragmentos; se necesita una edición conjunta de su alternativa.')
                location=next((a,b) for level,a,b in levels if level==scope_owner)
                if any(op not in ['Tj','TJ','Do'] or not location[0]<=start<end<=location[1]+4 for op,start,end in scope['paint']):fail('ActualText contiene otras figuras o instrucciones que no se pueden actualizar como una línea.')
            row['_alternatives']=alternatives;row['has_actual_text']=True;row['accessible_text']=alternatives[0]['value'];row['alternative_follows_text']=alternatives[0]['value']==row['text']
        return row


def form_markers(doc,number,overrides=None):
    overrides={} if overrides is None else overrides;result=[];budget=[0,0]
    def walk(owner,data,key,ancestors,path):
        budget[0]+=1;budget[1]+=len(data)
        if budget[0]>200 or budget[1]>32*1024*1024 or len(ancestors)>8:fail()
        edits=overrides.get(tuple(path),[]);result.append((key,marker_signature(patch(data,edits) if edits else data)))
        count=0
        for op,args,token in operations(data):
            if op!='Do' or len(args)!=1 or args[0].kind!='name':continue
            target=resources(doc,owner,args[0].value)
            if not target or doc.xref_get_key(target,'Subtype')!=('name','/Form'):continue
            if target in ancestors:fail()
            walk(target,doc.xref_stream(target),key+[count],ancestors|{target},path+[(owner,target,args[0].start,token.end)]);count+=1
    walk(doc[number].xref,doc[number].read_contents(),[],set(),[])
    return result


def capture(doc,number,overrides=None):
    semantic=snapshot(doc,number,allow_actual_text=True,allow_streams=True)
    markers=form_markers(doc,number,overrides)
    if semantic is not None:semantic['markers']=markers[0][1]
    return {'graph':semantic,'markers':markers}


def plan(doc,prepared):
    """Declare all alternative updates before writes, for atomic multi-page edits."""
    from .text_typography import apply as update_typography
    update_typography(doc,prepared)
    for number,items in prepared.items():
        for row,_ in items:
            for alt in row.get('_alternatives',[]):
                if alt['kind']=='node':doc.xref_set_key(alt['owner'],'ActualText',f.get_pdf_str(row['_accessible_replacement']))
    for number,items in prepared.items():
        if not all('_native' in r for r,_ in items):continue
        overrides=defaultdict(list);seen={}
        for row,_ in items:
            row['_alternative_patches']=[]
            for alt in row.get('_alternatives',[]):
                if alt['kind']!='inline':continue
                # Locate the alternative's owner on this occurrence path.
                path=row['_native_path'];depth=next((i+1 for i,s in enumerate(path) if s['target']==alt['owner']),0)
                target_path=path[:depth];token=alt['token'];location=(tuple((s['owner'],s['target'],s['start'],s['end']) for s in target_path),token.start,token.end)
                replacement=f.get_pdf_str(row['_accessible_replacement']).encode('ascii')
                if location in seen and seen[location]!=replacement:fail('Alternativas de lectura contradictorias en el lote.')
                if location in seen:continue
                seen[location]=replacement;overrides[location[0]].append((token.start,token.end,replacement));row['_alternative_patches'].append((target_path,token.start,token.end,replacement))
        items[0][0]['_extended_snapshot']=capture(doc,number,overrides)


def verify(doc,number,expected):
    if capture(doc,number)!=expected:fail('El texto guardado cambió las alternativas, etiquetas o marcadores esperados. No se publica el PDF.')
