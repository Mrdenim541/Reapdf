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
            rows.append({'id':identity,'parent':parent,'parent_valid':actual_parent==parent,'role':name,'raw_role':n.pdf_to_name(n.pdf_dict_gets(obj,'S')),'language':n.pdf_to_text_string(n.pdf_dict_gets(obj,'Lang')) if n.pdf_is_string(n.pdf_dict_gets(obj,'Lang')) else '', 'depth':depth,'page':page,'alt':n.pdf_to_text_string(alt) if n.pdf_is_string(alt) else '', 'title':n.pdf_to_text_string(n.pdf_dict_gets(obj,'T'))[:200], 'can_alt':bool(identity and name=='Figure' and actual_parent==parent and n.pdf_is_null(actual)), 'children':order if actual_parent==parent else None})
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


def reading_preview(base,ops,number):
    """Renderer-derived page reading flow, without fabricating MCID associations."""
    with open_pdf(export_pdf(base,ops)) as doc:
        if not doc.permissions&f.PDF_PERM_COPY:raise DocumentError('El documento no permite extraer contenido para revisar la lectura.')
        if type(number) is not int or not 0<=number<len(doc):raise DocumentError('Página de lectura no válida.')
        page=doc[number];rows=[];characters=0
        # Exclude binary images. Structure paths come from MuPDF's marked-content
        # interpretation, not from guessed visual position or xref matching.
        blocks=page.get_text('dict',flags=f.TEXT_COLLECT_STRUCTURE|f.TEXT_PRESERVE_WHITESPACE)['blocks']
        def walk(items,path,depth):
            nonlocal characters
            if depth>32:raise DocumentError('La vista de lectura supera 32 niveles.')
            tagged=iter(sorted((b for b in items if b['type']==2),key=lambda b:b.get('index',0)))
            for original in items:
                block=next(tagged) if original['type']==2 else original
                if block['type']==2:
                    walk(block.get('blocks',[]),path+[block.get('std') or block.get('raw') or 'Sin rol'],depth+1)
                elif block['type']==0:
                    text='\n'.join(''.join(s['text'] for s in line['spans']) for line in block['lines'])
                    if not text.strip():continue
                    characters+=len(text)
                    if len(rows)>=500 or characters>100000:raise DocumentError('Hasta 500 bloques y 100000 caracteres por página de revisión.')
                    rect=f.Rect(block['bbox'])*page.rotation_matrix
                    rows.append({'number':len(rows)+1,'text':text,'roles':path,'box':[rect.x0,rect.y0,rect.width,rect.height],'tagged':bool(path)})
        walk(blocks,[],0)
        return {'page':number,'width':page.rect.width,'height':page.rect.height,'blocks':rows,'untagged_blocks':sum(not r['tagged'] for r in rows),'scope':'Texto interpretado por MuPDF, ordenado por índices de etiquetas hermanas; los bloques sin etiqueta conservan su posición de flujo. Las mezclas de contenido etiquetado y sin etiquetar requieren revisión. No asigna xrefs por semejanza ni valida PDF/UA; figuras sin texto y aceptación con lector de pantalla requieren revisión aparte.'}


def properties(base,ops,identity,role=None,language=None):
    from .accessibility import LANGUAGE
    if type(identity) is not int or (role is None)==(language is None):raise DocumentError('Elige una etiqueta y cambia su rol o idioma por separado.')
    with open_pdf(base) as source:editable(source)
    info=model(base,ops);row=next((r for r in info['nodes'] if r['id']==identity),None)
    if not row or not row['parent_valid']:raise DocumentError('La etiqueta necesita identidad y padre verificables.')
    if role is not None:
        allowed={'P','H','H1','H2','H3','H4','H5','H6'}
        if row['role'] not in allowed or row['raw_role']!=row['role'] or not isinstance(role,str) or role not in allowed:raise DocumentError('Solo se convierten párrafos y encabezados estándar compatibles.')
    if language is not None and (not isinstance(language,str) or len(language)>63 or not LANGUAGE.fullmatch(language)):raise DocumentError('Usa un idioma básico BCP 47, como es o en-US.')
    with open_pdf(export_pdf(base,ops)) as doc:
        if doc.xref_get_key(identity,'NS')[0]!='null':raise DocumentError('Los espacios de nombres PDF 2 requieren revisión especializada.')
        if role is not None:doc.xref_set_key(identity,'S','/'+role)
        else:doc.xref_set_key(identity,'Lang',pdf_string(language))
        result=doc.tobytes(encryption=f.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
    model(result,[])
    return result
