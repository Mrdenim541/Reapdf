"""Preserve an existing tag graph and marked-content scopes during native edits.

This does not create/repair tags or certify PDF/UA. ActualText and stream-bound
MCRs need a coordinated semantic rewrite and remain protected.
"""
import hashlib,json,math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations


def snapshot(doc,number,*,allow_actual_text=False):
    n=f.mupdf;pdf=f._as_pdf_document(doc);catalog=n.pdf_dict_gets(n.pdf_trailer(pdf),'Root');root=n.pdf_dict_gets(catalog,'StructTreeRoot')
    if n.pdf_is_null(root):return None
    pages={p.xref:p.number for p in doc};seen={};budget=[0];characters=[0]
    def fail():raise DocumentError('La estructura etiquetada contiene alternativas, referencias a streams o variantes fuera del límite verificable de esta edición.')
    def walk(obj,depth=0):
        budget[0]+=1
        if budget[0]>(1_000_000 if allow_actual_text else 30000) or depth>64:fail()
        identity=n.pdf_to_num(obj)
        if identity in pages:return ['page',pages[identity]]
        if identity:
            if identity in seen:return ['ref',seen[identity]]
            if n.pdf_is_stream(obj):fail()
            index=len(seen);seen[identity]=index
            return ['object',index,walk(n.pdf_resolve_indirect(obj),depth+1)]
        if n.pdf_is_null(obj):return None
        if n.pdf_is_bool(obj):return ['bool',bool(n.pdf_to_bool(obj))]
        if n.pdf_is_int(obj):return ['number',n.pdf_to_int64(obj)]
        if n.pdf_is_real(obj):
            value=n.pdf_to_real(obj)
            if not math.isfinite(value):fail()
            return ['number',int(value) if value.is_integer() else value]
        if n.pdf_is_name(obj):return ['name',n.pdf_to_name(obj)]
        if n.pdf_is_string(obj):
            text=n.pdf_to_text_string(obj);characters[0]+=len(text)
            if characters[0]>2_000_000:fail()
            return ['string',text]
        if n.pdf_is_array(obj):
            if n.pdf_array_len(obj)>10000:fail()
            return ['array',[walk(n.pdf_array_get(obj,i),depth+1) for i in range(n.pdf_array_len(obj))]]
        if n.pdf_is_dict(obj):
            if n.pdf_dict_len(obj)>10000:fail()
            pairs={n.pdf_to_name(n.pdf_dict_get_key(obj,i)):n.pdf_dict_get_val(obj,i) for i in range(n.pdf_dict_len(obj))}
            if any(key in pairs and not n.pdf_is_null(pairs[key]) for key in (['Stm'] if allow_actual_text else ['ActualText','Stm'])):fail()
            return ['dict',[[key,walk(pairs[key],depth+1)] for key in sorted(pairs)]]
        fail()
    graph=[walk(root),walk(n.pdf_dict_gets(catalog,'MarkInfo'))]
    markers=marker_signature(doc[number].read_contents())
    digest=lambda value:hashlib.sha256(json.dumps(value,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()
    return {'graph':digest(graph),'markers':markers,'nodes':len(seen),'pages':len(doc)}


def verify(doc,number,expected):
    if snapshot(doc,number)!=expected:raise DocumentError('La edición cambió la estructura o los marcadores semánticos. No se publica el PDF.')


def marker_signature(content):
    if len(content)>32*1024*1024:raise DocumentError('El contenido marcado supera el límite verificable.')
    markers=[]
    for op,args,token in operations(content):
        if op in ['BDC','BMC','EMC']:
            markers.append(content[args[0].start if args else token.start:token.end].hex())
            if len(markers)>20000:raise DocumentError('Demasiados marcadores semánticos.')
    return hashlib.sha256(json.dumps(markers,separators=(',',':')).encode()).hexdigest()
