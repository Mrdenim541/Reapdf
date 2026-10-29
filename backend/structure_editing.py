"""Edit existing Figure alternatives and sibling reading order, without inventing tags."""
import pymupdf as f
from .engine import open_pdf,export_pdf,DocumentError
from .document_tools import editable
from .form_structure import pdf_string


def model(base,ops):
    with open_pdf(export_pdf(base,ops)) as doc:
        n=f.mupdf;native=f._as_pdf_document(doc);catalog=n.pdf_dict_gets(n.pdf_trailer(native),'Root');root=n.pdf_dict_gets(catalog,'StructTreeRoot');root_id=n.pdf_to_num(root)
        if n.pdf_is_null(root):return {'present':False,'nodes':[],'root':None}
        if not n.pdf_is_dict(root) or not root_id:raise DocumentError('El árbol necesita una raíz indirecta compatible.')
        pages={p.xref:p.number for p in doc};roles=n.pdf_dict_gets(root,'RoleMap');seen=set();rows=[]
        def role(obj):
            value=n.pdf_to_name(n.pdf_dict_gets(obj,'S'));visited=set()
            while value and value not in visited and len(visited)<16:
                visited.add(value);mapped=n.pdf_dict_gets(roles,value)
                if n.pdf_is_null(mapped):break
                value=n.pdf_to_name(mapped)
            return value
        def children(obj):
            k=n.pdf_dict_gets(obj,'K');parts=[n.pdf_array_get(k,i) for i in range(n.pdf_array_len(k))] if n.pdf_is_array(k) else [] if n.pdf_is_null(k) else [k]
            valid=all(n.pdf_is_dict(p) and n.pdf_to_num(p)>0 and n.pdf_to_name(n.pdf_dict_gets(p,'S')) for p in parts)
            return parts,[n.pdf_to_num(p) for p in parts] if valid else None
        def walk(obj,parent,depth,inherited_page):
            if depth>32 or len(rows)>=2000:raise DocumentError('Hasta 2000 etiquetas y 32 niveles de estructura.')
            identity=n.pdf_to_num(obj)
            if not n.pdf_is_dict(obj) or not n.pdf_to_name(n.pdf_dict_gets(obj,'S')):return
            if identity in seen and identity:raise DocumentError('La estructura contiene referencias repetidas o ciclos.')
            if identity:seen.add(identity)
            actual_parent=n.pdf_to_num(n.pdf_dict_gets(obj,'P'))
            page=pages.get(n.pdf_to_num(n.pdf_dict_gets(obj,'Pg')),inherited_page);name=role(obj)
            parts,order=children(obj);alt=n.pdf_dict_gets(obj,'Alt');actual=n.pdf_dict_gets(obj,'ActualText')
            rows.append({'id':identity,'parent':parent,'parent_valid':actual_parent==parent,'role':name,'depth':depth,'page':page,'alt':n.pdf_to_text_string(alt) if n.pdf_is_string(alt) else '', 'title':n.pdf_to_text_string(n.pdf_dict_gets(obj,'T'))[:200], 'can_alt':bool(identity and name=='Figure' and actual_parent==parent and n.pdf_is_null(actual)), 'children':order if actual_parent==parent else None})
            for child in parts:walk(child,identity,depth+1,page)
        parts,order=children(root)
        for part in parts:walk(part,root_id,0,None)
        return {'present':True,'root':root_id,'root_children':order,'nodes':rows}


def edit(base,ops,identity,alt=None,order=None):
    if type(identity) is not int or (alt is None)==(order is None):raise DocumentError('Selecciona una etiqueta y un único tipo de cambio.')
    with open_pdf(base) as source:editable(source)
    info=model(base,ops);rows={r['id']:r for r in info['nodes'] if r['id']}
    if identity!=info['root'] and identity not in rows:raise DocumentError('La etiqueta ya no existe en esta versión.')
    if alt is not None:
        if identity not in rows or not rows[identity]['can_alt']:raise DocumentError('Solo se cambian alternativas de figuras existentes sin ActualText especial.')
        if not isinstance(alt,str) or not 1<=len(alt.strip())<=2000 or any(ord(c)<32 and c not in '\n\t' for c in alt):raise DocumentError('Escribe una alternativa de 1 a 2000 caracteres.')
    else:
        expected=info['root_children'] if identity==info['root'] else rows[identity]['children']
        if not expected or not isinstance(order,list) or any(type(i) is not int for i in order) or len(order)!=len(set(order)) or sorted(order)!=sorted(expected):raise DocumentError('El orden debe contener exactamente las etiquetas hermanas compatibles.')
        if len(order)<2:raise DocumentError('Se necesitan al menos dos etiquetas para ordenar.')
        if any(i not in rows or rows[i]['parent']!=identity or not rows[i]['parent_valid'] for i in order):raise DocumentError('Los padres de estas etiquetas no coinciden con el grupo.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if alt is not None:doc.xref_set_key(identity,'Alt',pdf_string(alt.strip()))
        else:doc.xref_set_key(identity,'K','['+' '.join(f'{i} 0 R' for i in order)+']')
        result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    # Re-parse the saved structure; malformed parent relations never become a
    # successful edit. Full PDF/UA and screen-reader acceptance remain separate.
    model(result,[])
    return result
