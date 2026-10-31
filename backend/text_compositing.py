"""Bounded normal-alpha, standard blend text and RGB/Gray transparency groups.

Only inspect original dictionaries; edits never flatten or recreate appearances.
"""
import math
import pymupdf as f
from .engine import DocumentError
from .pdf_content import operations

BLENDS={'Normal','Compatible','Multiply','Screen','Overlay','Darken','Lighten','ColorDodge','ColorBurn','HardLight','SoftLight','Difference','Exclusion','Hue','Saturation','Color','Luminosity'}


def group(doc,xref):
    n=f.mupdf;obj=n.pdf_load_object(f._as_pdf_document(doc),xref);value=n.pdf_dict_gets(obj,'Group')
    if n.pdf_is_null(value):return True
    if not n.pdf_is_dict(value):return False
    keys={n.pdf_to_name(n.pdf_dict_get_key(value,i)) for i in range(n.pdf_dict_len(value))}
    if not keys<={'S','I','K','CS'} or n.pdf_to_name(n.pdf_dict_gets(value,'S'))!='Transparency':return False
    isolate=n.pdf_dict_gets(value,'I');knockout=n.pdf_dict_gets(value,'K');space=n.pdf_dict_gets(value,'CS')
    return (bool(n.pdf_is_null(isolate) or n.pdf_is_bool(isolate))
            and (n.pdf_is_null(knockout) or n.pdf_is_bool(knockout) and not n.pdf_to_bool(knockout))
            and (n.pdf_is_null(space) or n.pdf_is_name(space) and n.pdf_to_name(space) in ['DeviceRGB','DeviceGray']))


def graphics(doc,owner,data):
    """Refuse used masks/unknown blends/hidden font changes; absent unused states are fine."""
    n=f.mupdf;obj=n.pdf_load_object(f._as_pdf_document(doc),owner);resources=n.pdf_dict_gets(obj,'Resources')
    # Page resources may be inherited, unlike Form resources.
    for _ in range(20):
        if not n.pdf_is_null(resources):break
        obj=n.pdf_dict_gets(obj,'Parent')
        if n.pdf_is_null(obj):break
        resources=n.pdf_dict_gets(obj,'Resources')
    checked=set();original=False
    for op,args,_ in operations(data):
        if op!='gs':continue
        if len(args)!=1 or args[0].kind!='name':raise DocumentError('Estado gráfico de texto no válido.')
        name=args[0].value
        if name in checked:continue
        checked.add(name)
        if len(checked)>100:raise DocumentError('Demasiados estados gráficos para editar el texto.')
        states=n.pdf_dict_gets(resources,'ExtGState');state=n.pdf_dict_gets(states,name)
        if not n.pdf_is_dict(state):raise DocumentError('No se encontró el estado gráfico del texto.')
        keys={n.pdf_to_name(n.pdf_dict_get_key(state,i)) for i in range(n.pdf_dict_len(state))}
        if not keys<={'Type','ca','CA','BM','SMask'}:raise DocumentError('Este estado gráfico necesita revisión antes de editar el texto.')
        for key in ['ca','CA']:
            value=n.pdf_dict_gets(state,key)
            if n.pdf_is_null(value):continue
            if not n.pdf_is_number(value) or not math.isfinite(n.pdf_to_real(value)) or not 0<n.pdf_to_real(value)<=1:raise DocumentError('La opacidad del texto no es verificable o el texto es invisible.')
        blend=n.pdf_dict_gets(state,'BM');mask=n.pdf_dict_gets(state,'SMask')
        if not (n.pdf_is_null(blend) or n.pdf_is_name(blend) and n.pdf_to_name(blend) in BLENDS):raise DocumentError('El modo de mezcla no es estándar o necesita otra edición.')
        original=original or not n.pdf_is_null(blend) and n.pdf_to_name(blend) not in ['Normal','Compatible']
        if not (n.pdf_is_null(mask) or n.pdf_is_name(mask) and n.pdf_to_name(mask)=='None'):
            from .soft_masks import verify
            verify(doc,mask);original=True

    return original


def original_only(doc,obj):
    return bool(obj.get('composition_original')) or any(doc.xref_get_key(step['target'],'Group')[0]!='null' for step in obj.get('path',[]))
