"""Bounded changes to field partial names and single-choice export/display pairs."""
import pymupdf as f
from .engine import DocumentError
from .form_structure import field_structure,pdf_string,reference
from .form_fields import _references
from .forms import special_form


def rename_field(doc,selected,name):
    if not isinstance(name,str) or not 1<=len(name)<=100 or name!=name.strip() or any(ord(c)<32 or ord(c)==127 or c=='.' or 0xd800<=ord(c)<=0xdfff for c in name):
        raise DocumentError('El nombre parcial admite 1–100 caracteres, sin puntos, controles ni espacios en los extremos.')
    _,structure,_,reason=field_structure(doc)
    if reason:raise DocumentError(reason)
    # References in scripts or calculations must never be silently broken.
    if special_form(doc) or any(doc.xref_get_key(n,key)[0]!='null' for info in structure.values() for n in info['chain'] for key in ['A','AA']):
        raise DocumentError('No se renombran campos en formularios con acciones o cálculos.')
    owner=selected['group'];parent=reference(doc,owner,'Parent')
    siblings=_references(doc,parent,'Kids') if parent else _references(doc,doc.pdf_catalog(),'AcroForm/Fields')
    if any(ref!=owner and doc.xref_get_key(ref,'T')==('string',name) for ref,_ in siblings):
        raise DocumentError('Ya existe un campo o contenedor hermano con ese nombre.')
    chain=structure[selected['xref']]['chain'];ancestors=chain[:chain.index(owner)]
    prefix='.'.join(doc.xref_get_key(n,'T')[1] for n in ancestors if doc.xref_get_key(n,'T')[0]=='string' and doc.xref_get_key(n,'T')[1])
    full=(prefix+'.' if prefix else '')+name
    if len(full)>1000:raise DocumentError('El nombre completo supera 1000 caracteres.')
    doc.xref_set_key(owner,'T',pdf_string(name))
    return full


def change_choices(doc,selected,options):
    if selected['kind']!='choice' or selected['group_size']!=1:raise DocumentError('Solo se cambian opciones de listas de selección única con una posición.')
    if not isinstance(options,list) or not 1<=len(options)<=500:raise DocumentError('La lista necesita de 1 a 500 opciones.')
    for option in options:
        if not isinstance(option,dict) or set(option)!={'value','label'}:raise DocumentError('Cada opción necesita valor y etiqueta.')
        value,label=option['value'],option['label']
        if not isinstance(value,str) or not value or len(value)>2000 or any(ord(c)<32 or ord(c)==127 or 0xd800<=ord(c)<=0xdfff for c in value):raise DocumentError('Usa valores de opción no vacíos, sin controles y de hasta 2000 caracteres.')
        if not isinstance(label,str) or not label.strip() or len(label)>300 or any(ord(c)<32 or ord(c)>255 or ord(c)==127 for c in label):raise DocumentError('Las etiquetas necesitan 1–300 caracteres latinos sin controles.')
    values=[o['value'] for o in options]
    if len(values)!=len(set(values)):raise DocumentError('Los valores de las opciones no pueden repetirse.')
    if selected['value'] and selected['value'] not in values:raise DocumentError('Conserva la opción del valor actual; rellena otro valor antes de retirarla.')
    owner=selected['group'];default=doc.xref_get_key(owner,'DV')
    # Preserve reset semantics, including inherited defaults.
    _,structure,_,_=field_structure(doc)
    for node in reversed(structure[selected['xref']]['chain']):
        default=doc.xref_get_key(node,'DV')
        if default[0]!='null':break
    if default[0]!='null' and (default[0]!='string' or default[1] and default[1] not in values):
        raise DocumentError('Conserva la opción del valor de restablecimiento del campo.')
    doc.xref_set_key(owner,'Opt','['+' '.join('['+pdf_string(o['value'])+' '+pdf_string(o['label'])+']' for o in options)+']')
    doc.xref_set_key(owner,'I','null');doc.xref_set_key(owner,'TI','0')
