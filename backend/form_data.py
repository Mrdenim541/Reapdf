"""Datos vinculados al PDF base y aplanado explícito de campos con apariencia."""
from hashlib import sha256
import pymupdf as fitz
from .engine import open_pdf, export_pdf, DocumentError
from .forms import form_model, prepare_fill
from .form_structure import expand_values


def export_form_data(base,operations):
    export_pdf(base,operations)
    with open_pdf(base) as doc:
        if not doc.permissions & fitz.PDF_PERM_COPY:raise DocumentError('El documento no permite exportar datos.')
        rows=form_model(doc)['fields']
        if not any(r['editable'] for r in rows):raise DocumentError('No hay campos compatibles para exportar datos.')
    from .form_rules import resolve_rules
    effective=resolve_rules(base,operations)[0]
    values=[v for op in effective if op.get('type')=='form_fill' for v in op['values']]
    patches={(v['page'],v['xref']):v['value'] for v in expand_values(rows,values)} if values else {}
    return {'format':'reapdf-form-data','version':1,'source_sha256':sha256(base).hexdigest(),
            'fields':[{key:r[key] for key in ['page','xref','name','kind']}|{'value':patches.get((r['page'],r['xref']),r['value'])} for r in rows if r['editable']]}


def import_form_data(base,operations,payload):
    export_pdf(base,operations)
    if not isinstance(payload,dict) or payload.get('format')!='reapdf-form-data' or type(payload.get('version')) is not int or payload['version']!=1 or payload.get('source_sha256')!=sha256(base).hexdigest():
        raise DocumentError('Los datos no corresponden a este PDF base. Usa el mismo documento o proyecto de origen.')
    values=payload.get('fields')
    if not isinstance(values,list) or not 1<=len(values)<=500:raise DocumentError('El archivo debe incluir de 1 a 500 campos.')
    with open_pdf(base) as doc:
        rows={(r['page'],r['xref']):r for r in form_model(doc)['fields']}
        incoming=[]
        for entry in values:
            if not isinstance(entry,dict) or type(entry.get('page')) is not int or type(entry.get('xref')) is not int:raise DocumentError('Identificador de campo no válido.')
            row=rows.get((entry['page'],entry['xref']))
            if not row or any(entry.get(k)!=row[k] for k in ['name','kind']):raise DocumentError('La identidad o tipo de un campo no coincide.')
            incoming.append({k:entry.get(k) for k in ['page','xref','value']})
        incoming=expand_values(list(rows.values()),incoming)
        prepare_fill(doc,incoming)
        previous=[v for op in operations if op.get('type')=='form_fill' for v in op['values']]
        merged={(v['page'],v['xref']):v for v in expand_values(list(rows.values()),previous)} if previous else {}
        for entry in incoming:merged[(entry['page'],entry['xref'])]=entry
        result=[v for key,v in merged.items() if v['value']!=rows[key]['value']]
    next_ops=[op for op in operations if op.get('type')!='form_fill']
    if result:next_ops.append({'type':'form_fill','page':0,'values':result})
    export_pdf(base,next_ops)
    return next_ops


def flatten_form(base,operations):
    with open_pdf(base) as source:
        if source.get_sigflags()>0 or not source.permissions & fitz.PDF_PERM_MODIFY:raise DocumentError('El documento no permite aplanar formularios o está firmado.')
        rows=form_model(source)['fields']
        if not rows:raise DocumentError('El documento no contiene campos para aplanar.')
        if any(not r['editable'] and r['reason']!='Campo de solo lectura.' for r in rows):raise DocumentError('El formulario contiene estructuras no compatibles. No se aplanará parcialmente.')
    with open_pdf(export_pdf(base,operations)) as doc:
        for page in doc:
            for widget in page.widgets() or []:
                if doc.xref_get_key(widget.xref,'AP/N')[0]=='null':raise DocumentError('Un campo carece de apariencia. Rellénalo o genera su apariencia antes de aplanar.')
        doc.bake(annots=False,widgets=True)
        if any(list(p.widgets() or []) for p in doc):raise DocumentError('No se pudieron aplanar todos los campos.')
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP,garbage=4,deflate=True)
