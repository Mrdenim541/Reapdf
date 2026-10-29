"""Bounded embedded-file name tree normalization for the pinned flat-tree API."""
import pymupdf as f
from .engine import DocumentError


def normalize(doc):
    n=f.mupdf;pdf=f._as_pdf_document(doc);tree=n.pdf_dict_getp(n.pdf_trailer(pdf),'Root/Names/EmbeddedFiles');entries=[];seen=set();budget=[0]
    if n.pdf_is_null(tree):return []
    def walk(node,depth,ancestors):
        budget[0]+=1;ref=n.pdf_to_num(node)
        if depth>8 or budget[0]>200 or ref and ref in ancestors:raise DocumentError('El árbol de adjuntos supera los límites o contiene ciclos.')
        if not n.pdf_is_dict(node):raise DocumentError('Árbol de adjuntos no válido.')
        names=n.pdf_dict_gets(node,'Names');kids=n.pdf_dict_gets(node,'Kids')
        if not n.pdf_is_null(names) and not n.pdf_is_null(kids):raise DocumentError('Nodo de adjuntos ambiguo.')
        if not n.pdf_is_null(names):
            if not n.pdf_is_array(names) or n.pdf_array_len(names)%2:raise DocumentError('Nombres de adjuntos no válidos.')
            if n.pdf_array_len(names)>200:raise DocumentError('Hasta 100 adjuntos por documento.')
            for i in range(0,n.pdf_array_len(names),2):
                key=n.pdf_array_get(names,i);spec=n.pdf_array_get(names,i+1)
                if not n.pdf_is_string(key) or not n.pdf_is_dict(spec):raise DocumentError('Identificador de adjunto no válido.')
                name=n.pdf_to_text_string(key)
                if not name or len(name)>255 or name in seen:raise DocumentError('Nombre de adjunto repetido o demasiado largo.')
                seen.add(name);entries.append((name,key,spec))
                if len(entries)>100:raise DocumentError('Hasta 100 adjuntos por documento.')
        elif not n.pdf_is_null(kids):
            if not n.pdf_is_array(kids) or n.pdf_array_len(kids)>100:raise DocumentError('Árbol de adjuntos no válido.')
            for i in range(n.pdf_array_len(kids)):walk(n.pdf_array_get(kids,i),depth+1,ancestors|({ref} if ref else set()))
    walk(tree,0,set())
    if not n.pdf_is_null(n.pdf_dict_gets(tree,'Kids')):
        array=n.pdf_new_array(pdf,len(entries)*2)
        for _,key,spec in entries:n.pdf_array_push(array,key);n.pdf_array_push(array,spec)
        n.pdf_dict_puts(tree,'Names',array);n.pdf_dict_dels(tree,'Kids');n.pdf_dict_dels(tree,'Limits')
    return [(name,spec) for name,_,spec in entries]
