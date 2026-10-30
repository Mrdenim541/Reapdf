"""Bounded Form traversal and copy-on-write of one selected invocation path."""
import re
import pymupdf as f
from .engine import DocumentError
from .pdf_content import placements,patch,set_content,tokens,numbers,names
SAFE=re.compile(r'[A-Za-z0-9_.-]+\Z')


def array(doc,xref,key,count,default=None):
    kind,value=doc.xref_get_key(xref,key)
    if kind=='null' and default is not None:return default
    if kind!='array':raise DocumentError('La geometría del objeto Form no es compatible.')
    parsed=list(tokens(value.encode('ascii')))
    if len(parsed)!=1 or parsed[0].kind!='array':raise DocumentError('Geometría Form no válida.')
    return numbers(parsed[0].value,count)


def structure(doc,page):
    result=[];budget={'bytes':0,'nodes':0};page_matrix=page.transformation_matrix
    def walk(owner,data,parent,path,ancestors,clips):
        budget['bytes']+=len(data);budget['nodes']+=1
        if budget['bytes']>32*1024*1024 or budget['nodes']>200 or len(path)>8:raise DocumentError('La página supera los límites de objetos Form para edición.')
        if doc.xref_get_key(owner,'Resources/Properties')[0]!='null':
            if not path:raise DocumentError('Las propiedades de marcado necesitan revisión de alternativas antes de editar.')
            return
        if 'ActualText' in names(data):return
        from .text_compositing import graphics
        graphics(doc,owner,data)
        parsed=placements(data)
        for obj in parsed['texts']:
            combined=obj['matrix']*parent
            from .affine_text import frame
            try:values=frame(combined,f.Point(0,0))
            except DocumentError:continue
            result.append({**obj,'matrix':combined,'scope':owner if path else 0,'path':path,'clips':clips,'factor':values['factor'],'horizontal_factor':values['horizontal']})
            if len(result)>5000:raise DocumentError('Hasta 5000 grupos de texto por página.')
        for invocation in parsed['images']:
            name=invocation['resource']
            if not SAFE.fullmatch(name):continue
            kind,value=doc.xref_get_key(owner,'Resources/XObject/'+name)
            if kind!='xref':continue
            target=int(value.split()[0])
            if doc.xref_get_key(target,'Subtype')!=('name','/Form'):continue
            if target in ancestors:continue
            from .text_compositing import group
            if not group(doc,target):continue
            if any(doc.xref_get_key(target,k)[0]!='null' for k in ['OC','Ref','StructParent','StructParents']):continue
            if doc.xref_get_key(doc.pdf_catalog(),'StructTreeRoot')[0]!='null':continue
            if doc.xref_get_key(target,'Resources')[0] not in ['dict','xref']:continue
            try:
                matrix=f.Matrix(*array(doc,target,'Matrix',6,[1,0,0,1,0,0]))*invocation['matrix']*parent
                from .affine_text import rectangle
                box=f.Rect(array(doc,target,'BBox',4))
                if box.is_empty:raise DocumentError('El recorte Form está vacío o invertido.')
                bounds=[list(f.Point(p)*matrix*page_matrix) for p in rectangle(box)]
                from .styled_text import stream
                child=stream(doc,target,16*1024*1024)
                entry={'owner':owner,'target':target,'start':invocation['start'],'end':invocation['end']}
                walk(target,child,matrix,path+[entry],ancestors|{target},clips+[bounds])
            except DocumentError as exc:
                # Structural limits are hard page bounds; incompatible local
                # geometry can remain read-only without blocking direct text.
                if 'límites' in str(exc) or '5000' in str(exc):raise
    walk(page.xref,page.read_contents(),f.Matrix(1,1),[],set(),[])
    return result


def clone_dictionary(doc,owner,key):
    kind,value=doc.xref_get_key(owner,key);xref=doc.get_new_xref()
    doc.update_object(xref,doc.xref_object(int(value.split()[0])) if kind=='xref' else value if kind=='dict' else '<<>>')
    doc.xref_set_key(owner,key,f'{xref} 0 R');return xref


def write(doc,page,prepared):
    root={'owner':page.xref,'edits':[],'children':{}}
    for row,encoded in prepared:
        node=root
        for step in row.get('_native_path',[]):
            key=(step['start'],step['end'])
            if key not in node['children']:node['children'][key]={'owner':step['target'],'edits':[],'children':{}}
            node=node['children'][key]
        start,end,_=row['_native'];node['edits'].append((start,end,encoded))
    def reserve(node,is_root=False):
        node['data']=page.read_contents() if is_root else doc.xref_stream(node['owner'])
        return len(node['data'])+sum(len(value) for _,_,value in node['edits'])+sum(reserve(child) for child in node['children'].values())
    budget=getattr(doc,'_reapdf_form_write_bytes',0)+reserve(root,True)
    if budget>64*1024*1024:raise DocumentError('La edición requiere más de 64 MB de contenido independiente. Divide el lote.')
    doc._reapdf_form_write_bytes=budget
    def apply(node,is_root=False):
        original=node['owner'];owner=original
        if not is_root:
            owner=doc.get_new_xref();doc.update_object(owner,doc.xref_object(original))
        content=node['data'];edits=list(node['edits'])
        if node['children']:
            resources=clone_dictionary(doc,owner,'Resources');objects=clone_dictionary(doc,resources,'XObject')
            for (start,end),child in node['children'].items():
                target=apply(child);alias='ReapdfForm'
                while doc.xref_get_key(objects,alias)[0]!='null':alias+='x'
                doc.xref_set_key(objects,alias,f'{target} 0 R');edits.append((start,end,('/'+alias+' Do').encode()))
        changed=patch(content,edits)
        if is_root:set_content(doc,page,changed)
        else:doc.update_stream(owner,changed)
        return owner
    apply(root,True)
