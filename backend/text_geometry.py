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
    n=f.mupdf;index=tree(doc);updates={};affected={}
    for row in source:
        identity=row.get('_semantic_identity')
        if identity is None:continue
        for owner in index.records[identity]['chain']+[identity]:
            for kind,at,cls,attr in declarations(doc,index.records[owner]['object']):
                if n.pdf_to_name(n.pdf_dict_gets(attr,'O'))!='Layout':continue
                old=validate(attr)
                if old is not None:affected[(owner,kind,at,cls)]=(attr,old)
    if not affected:return
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
        if not fragments or any(page!=number for page,_ in fragments):
            raise DocumentError('Este párrafo tiene una caja declarada de una sola página. Ajusta el contenido en ella; la continuación necesita cajas por página.')
        rect=f.Rect()
        for _,row in fragments:rect|=bounds(polygon(row['_geometry'],row['_replacement_width']))*inverse
        if rect.is_empty or rect.is_infinite:fail()
        change={'BBox':'['+' '.join(f'{v:.8f}' for v in rect)+']'}
        for name,value in [('Width',rect.width),('Height',rect.height)]:
            oldvalue=n.pdf_dict_gets(attr,name)
            if n.pdf_is_number(oldvalue):change[name]=f'{value:.8f}'
        updates[key]=change
    apply_changes(doc,index,updates)
