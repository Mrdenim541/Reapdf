"""Coordinate page-local Layout bounds with verified paragraph fragments.

No box is guessed from nearby text: owners come from the semantic tree and
every affected marked-content scope must be wholly included in the edit.
"""
import math
import pymupdf as f
from .engine import DocumentError
from .text_typography import declarations,prove_complete,apply_changes

GEOMETRY={'BBox','Width','Height'}


def fail():raise DocumentError('La caja geométrica declarada necesita una asociación completa y verificable en una página.')


def validate(attr):
    n=f.mupdf;box=n.pdf_dict_gets(attr,'BBox')
    if n.pdf_is_null(box):
        if any(not n.pdf_is_null(n.pdf_dict_gets(attr,k)) for k in ['Width','Height']):fail()
        return None
    if not n.pdf_is_array(box) or n.pdf_array_len(box)!=4:fail()
    values=[n.pdf_array_get(box,i) for i in range(4)]
    if any(not n.pdf_is_number(v) for v in values):fail()
    values=[n.pdf_to_real(v) for v in values]
    if not all(math.isfinite(v) and abs(v)<=1e7 for v in values) or values[2]<=values[0] or values[3]<=values[1]:fail()
    for key in ['Width','Height']:
        value=n.pdf_dict_gets(attr,key)
        if n.pdf_is_null(value) or n.pdf_is_name(value) and n.pdf_to_name(value)=='Auto':continue
        if not n.pdf_is_number(value) or not math.isfinite(n.pdf_to_real(value)) or not 0<n.pdf_to_real(value)<=1e7:fail()
    return f.Rect(values)


def apply(doc,number,source,prepared):
    from .semantic_text import tree
    from .affine_text import polygon,bounds
    n=f.mupdf;index=tree(doc);updates={};affected={};migrations=[]
    for row in source:
        identity=row.get('_semantic_identity')
        if identity is None:continue
        for owner in index.records[identity]['chain']+[identity]:
            for kind,at,cls,attr in declarations(doc,index.records[owner]['object']):
                if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))!='Layout':continue
                old=validate(attr)
                if old is not None:affected[(owner,kind,at,cls)]=(attr,old)
    if not affected:return []
    if len(affected)>1024:fail()
    # BBox belongs to one default user space. Spanning nodes need per-page
    # declarations, not a union of coordinates from unrelated pages.
    for owner in {k[0] for k in affected}:
        if any(pg!=doc[number].xref or stream for pg,stream,_ in index.refs[owner]):fail()
        prove_complete(doc,owner,source)
    def belongs(row,owner):
        identity=row.get('_semantic_identity')
        return identity is not None and owner in index.records[identity]['chain']+[identity]
    inverse=~doc[number].transformation_matrix
    for key,(attr,old) in affected.items():
        owner=key[0];original=[r.get('_source_format_row',r) for r in source if belongs(r,owner)]
        if not original:fail()
        for row in original:
            cell=bounds(polygon(row['_geometry']))*inverse
            if not (old+(-.05,-.05,.05,.05)).contains(cell):fail()
        fragments=[(page,row) for page,(row,_) in prepared if belongs(row,owner)]
        if not fragments:
            # The user may erase one complete styled scope while keeping the
            # rest of the paragraph. An empty scope has no spatial extent.
            updates[key]={name:'null' for name in GEOMETRY}
            continue
        if any(page!=number for page,_ in fragments):
            # A spanning container keeps its logical role and typography. Its
            # spatial declarations move to the page-local Span leaves created
            # by Paragraph.extend; null values are absent PDF attributes.
            fields={name:('Auto' if n.pdf_is_name(n.pdf_dict_gets(attr,name)) else 'number') for name in ['Width','Height'] if not n.pdf_is_null(n.pdf_dict_gets(attr,name))}
            selected={r['id'] for _,r in fragments}
            migrations.append({'ids':selected,'fields':fields})
            updates[key]={name:'null' for name in GEOMETRY}
            continue
        rect=f.Rect()
        for _,row in fragments:rect|=bounds(polygon(row['_geometry'],row['_replacement_width']))*inverse
        if rect.is_empty or rect.is_infinite:fail()
        change={'BBox':'['+' '.join(f'{v:.8f}' for v in rect)+']'}
        for name,value in [('Width',rect.width),('Height',rect.height)]:
            oldvalue=n.pdf_dict_gets(attr,name)
            if n.pdf_is_number(oldvalue):change[name]=f'{value:.8f}'
        updates[key]=change
    apply_changes(doc,index,updates)
    return migrations


def materialize(doc,number,paragraph,prepared,draws,migrations):
    """Put migrated geometry only on uniquely owned, page-local Span leaves.

    The original P/Span identity, reading order, non-spatial attributes and
    shared classes survive. MCIDs come from the actual continuation allocator.
    """
    if not migrations:return []
    from .semantic_text import Tree
    from .affine_text import polygon,bounds
    from .text_typography import syntax,items
    n=f.mupdf;index=Tree(doc);codes={}
    for page,row,_,_ in draws:
        key=(page,paragraph.code_by_id[row['id']]);value=row['_continuation_mcid']
        if key in codes and codes[key]!=value:fail()
        codes[key]=value
    result=[];added=0
    for migration in migrations:
        boxes={}
        for page,(row,_) in prepared:
            if row['id'] not in migration['ids']:continue
            source_code=paragraph.code_by_id[row['id']]
            code=source_code if page==number else codes.get((page,source_code))
            if code is None:fail()
            owner,_=index.owner(page,0,code)
            refs=set(index.refs[owner])
            if refs!={(doc[page].xref,0,code)}:fail()
            if n.pdf_to_name(n.pdf_dict_gets(index.records[owner]['object'],'S'))!='Span':fail()
            rect=bounds(polygon(row['_geometry'],row['_replacement_width']))*~doc[page].transformation_matrix
            if rect.is_empty or rect.is_infinite:fail()
            key=(page,code,owner)
            if key not in boxes:boxes[key]=f.Rect(rect)
            else:boxes[key]|=rect
        if not boxes:fail()
        for (page,code,owner),rect in boxes.items():
            added+=1
            if added>2048:raise DocumentError('La geometría continuada supera 2048 declaraciones; divide el párrafo.')
            values={'BBox':'['+' '.join(f'{v:.8f}' for v in rect)+']'}
            for name,kind in migration['fields'].items():values[name]='/Auto' if kind=='Auto' else f'{getattr(rect,name.lower()):.8f}'
            attr=doc.get_new_xref();doc.update_object(attr,'<< /O/Layout '+' '.join('/'+key+' '+value for key,value in values.items())+' >>')
            # New continuation leaves are independent; never mutate a shared A.
            obj=n.pdf_load_object(f._as_pdf_document(doc),owner);old=n.pdf_dict_gets(obj,'A');attrs=items(old)
            for previous in attrs:
                if n.pdf_to_name(n.pdf_dict_gets(previous,'O'))!='Layout' or n.pdf_is_null(n.pdf_dict_gets(previous,'BBox')):continue
                for key in ['Width','Height']:
                    before=n.pdf_dict_gets(previous,key)
                    if key in values and not n.pdf_is_null(before) and (values[key]=='/Auto')!=bool(n.pdf_is_name(before)):
                        raise DocumentError('Las cajas superpuestas declaran dimensiones incompatibles; conserva el contenido en su página o revisa esa estructura.')
            doc.xref_set_key(owner,'A','['+' '.join([*(syntax(a) for a in attrs),f'{attr} 0 R'])+']')
            result.append({'page':page,'code':code,'values':values})
    # Consumers following extension must not reuse the pre-extension tree.
    doc._reapdf_semantic_tree=index
    return result


def verify(doc,expected):
    if not expected:return
    from .semantic_text import Tree
    n=f.mupdf;index=Tree(doc)
    for item in expected:
        owner,_=index.owner(item['page'],0,item['code']);obj=index.records[owner]['object']
        candidates=[attr for _,_,_,attr in declarations(doc,obj) if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))=='Layout']
        def matches(attr):
            actual=validate(attr)
            if actual is None:return False
            wanted=f.Rect([float(v) for v in item['values']['BBox'][1:-1].split()])
            if any(abs(a-b)>.0001 for a,b in zip(actual,wanted)):return False
            for key,value in item['values'].items():
                if key=='BBox':continue
                old=n.pdf_dict_gets(attr,key)
                if value=='/Auto':
                    if not n.pdf_is_name(old) or n.pdf_to_name(old)!='Auto':return False
                elif not n.pdf_is_number(old) or abs(n.pdf_to_real(old)-float(value))>.0001:return False
            return True
        if not any(matches(attr) for attr in candidates):raise DocumentError('El PDF guardado perdió una caja de continuación; no se publica el resultado.')
