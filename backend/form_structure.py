"""Bounded validation of AcroForm ownership and inherited field properties."""
import re
from collections import defaultdict
import pymupdf as fitz
from .engine import DocumentError
from .form_fields import _references


def reference(doc,xref,key):
    kind,value=doc.xref_get_key(xref,key)
    if kind=='null':return None
    if kind!='xref':raise DocumentError('La estructura del formulario contiene una referencia no compatible.')
    return int(value.split()[0])


def field_structure(doc):
    placed=[(xref,page.number) for page in doc for xref,kind,_ in page.annot_xrefs() if kind==fitz.PDF_ANNOT_WIDGET]
    widgets=dict(placed)
    if len(placed)!=len(widgets):raise DocumentError('La estructura reutiliza el mismo Widget en más de una página o posición.')
    if len(widgets)>500:raise DocumentError('Este editor admite hasta 500 campos por documento.')
    # Check parent cycles before asking MuPDF for a fully qualified Widget name.
    for xref in widgets:
        visited=set();node=xref
        while node is not None:
            if node in visited or len(visited)>16:raise DocumentError('La estructura del formulario contiene un ciclo o supera 16 niveles.')
            visited.add(node);node=reference(doc,node,'Parent')
    ownership={};groups=defaultdict(list);seen=set();reason=''
    try:
        roots=_references(doc,doc.pdf_catalog(),'AcroForm/Fields')
        def unique_names(refs):
            names=[doc.xref_get_key(x,'T')[1] for x,_ in refs if doc.xref_get_key(x,'T')[0]=='string']
            if len(names)!=len(set(names)):raise DocumentError('Hay nombres parciales repetidos entre campos hermanos.')
        unique_names(roots)
        def walk(xref,parent,chain):
            if len(chain)>=16:raise DocumentError('El árbol supera 16 niveles.')
            if xref in seen or len(seen)>=2000:raise DocumentError('El árbol contiene referencias repetidas o supera 2000 nodos.')
            seen.add(xref)
            if reference(doc,xref,'Parent')!=parent:raise DocumentError('El árbol y las referencias Parent no coinciden.')
            chain=[*chain,xref]
            kids=_references(doc,xref,'Kids')
            if xref in widgets:
                p=reference(doc,xref,'P')
                if p is not None and p!=doc[widgets[xref]].xref:raise DocumentError('El Widget referencia una página distinta de su ubicación.')
                if kids:raise DocumentError('Un Widget con hijos todavía no es compatible.')
                name=doc.xref_get_key(xref,'T')
                owner=xref if name[0]=='string' and name[1] else parent
                if owner is None:raise DocumentError('El campo no tiene un propietario lógico con nombre.')
                names=[doc.xref_get_key(node,'T') for node in chain]
                if any(kind not in ['null','string'] for kind,_ in names):raise DocumentError('Los nombres del árbol no son cadenas PDF.')
                full='.'.join(value for kind,value in names if kind=='string' and value)
                if not full or len(full)>1000:raise DocumentError('Nombre de campo vacío o demasiado largo.')
                ownership[xref]={'owner':owner,'chain':chain,'name':full,'page':widgets[xref]};groups[owner].append(xref)
            else:
                if not kids:raise DocumentError('El árbol contiene campos sin Widget ni hijos compatibles.')
                if doc.xref_get_key(xref,'T')[0]!='string':raise DocumentError('Los nodos de campo necesitan un nombre parcial.')
                unique_names(kids)
                for child,_ in kids:walk(child,xref,chain)
        for root,_ in roots:walk(root,None,[])
        if set(ownership)!=set(widgets):raise DocumentError('Hay Widgets fuera del árbol de campos.')
        # Bare widget siblings must belong directly to one terminal field.
        for owner,members in groups.items():
            if owner not in widgets:
                if {n for n,_ in _references(doc,owner,'Kids')}!=set(members):raise DocumentError('Un campo compartido mezcla Widgets y nodos de campo.')
    except DocumentError as exc:reason='Estructura de formulario no compatible: '+str(exc)
    return widgets,ownership,dict(groups),reason


def button_states(doc,xref):
    """Only accept Off and one simple name, each backed by an appearance stream."""
    native=fitz.mupdf;obj=native.pdf_load_object(fitz._as_pdf_document(doc),xref)
    normal=native.pdf_dict_getp(obj,'AP/N')
    if not native.pdf_is_dict(normal):return None
    result=[]
    for i in range(native.pdf_dict_len(normal)):
        key=native.pdf_to_name(native.pdf_dict_get_key(normal,i));value=native.pdf_dict_get_val(normal,i)
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',key) or not native.pdf_is_stream(value):return None
        result.append(key)
    if len(result)!=2 or 'Off' not in result:return None
    down=native.pdf_dict_getp(obj,'AP/D')
    if not native.pdf_is_null(down):
        if not native.pdf_is_dict(down) or native.pdf_dict_len(down)!=2:return None
        for i in range(2):
            if native.pdf_to_name(native.pdf_dict_get_key(down,i)) not in result or not native.pdf_is_stream(native.pdf_dict_get_val(down,i)):return None
    return next(n for n in result if n!='Off')


def expand_values(rows,values):
    if not isinstance(values,list) or not 1<=len(values)<=500:raise DocumentError('Indica de 1 a 500 valores de formulario.')
    model={(r['page'],r['xref']):r for r in rows};seen=set();chosen={}
    for entry in values:
        if not isinstance(entry,dict) or type(entry.get('page')) is not int or type(entry.get('xref')) is not int:raise DocumentError('Identificador de campo no válido.')
        key=entry['page'],entry['xref'];row=model.get(key)
        if key in seen or not row:raise DocumentError('Campo inexistente o repetido.')
        seen.add(key)
        if not row['editable']:raise DocumentError(row['reason'])
        group=row['group'];value=entry.get('value')
        if group in chosen and (type(value) is not type(chosen[group]) or value!=chosen[group]):raise DocumentError('El mismo campo compartido tiene valores contradictorios.')
        chosen[group]=value
    return [{'page':r['page'],'xref':r['xref'],'value':chosen[r['group']]} for r in rows if r['group'] in chosen]


def pdf_string(value):
    return fitz.get_pdf_str(value) if value.isascii() else '<FEFF'+value.encode('utf-16-be').hex().upper()+'>'


def raw_key(doc,xref,key):
    kind,value=doc.xref_get_key(xref,key)
    return pdf_string(value) if kind=='string' else value
